"""Read live FlowPilot state from the repository-local .flowpilot tree."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import CockpitSnapshot, EventSummary, NodeSummary, RunSummary, normalize_status, status_health


def _read_json(path: Path, findings: list[str]) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        findings.append(f"Missing JSON source: {path}")
        return {}
    except OSError as exc:
        findings.append(f"Cannot read JSON source {path}: {exc}")
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        findings.append(f"Invalid JSON in {path}: {exc}")
        return {}
    if not isinstance(payload, dict):
        findings.append(f"JSON source is not an object: {path}")
        return {}
    return payload


def _path_from_raw(project_root: Path, flowpilot_root: Path, raw: object, default: Path) -> Path:
    if not raw:
        return default
    path = Path(str(raw))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == ".flowpilot":
        return project_root / path
    return flowpilot_root / path


def _mtime_label(path: Path) -> str:
    try:
        timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return ""
    return timestamp.strftime("%H:%M:%S")


def _safe_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _first_text(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


class FlowPilotStateReader:
    """Build a cockpit snapshot from current FlowPilot files.

    The reader treats `.flowpilot/current.json` and `.flowpilot/index.json` as
    catalog pointers, then reads each run from `.flowpilot/runs/<run-id>/`.
    If a current run pointer is broken, the snapshot is degraded instead of
    silently falling back to old legacy state.
    """

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.flowpilot_root = self.project_root / ".flowpilot"

    def read_project(self, selected_run_id: str | None = None) -> CockpitSnapshot:
        findings: list[str] = []
        watched: set[Path] = set()
        current_path = self.flowpilot_root / "current.json"
        index_path = self.flowpilot_root / "index.json"
        current = _read_json(current_path, findings)
        index = _read_json(index_path, findings)
        watched.update({current_path, index_path})

        active_run_id = _first_text(
            current.get("active_run_id"),
            current.get("current_run_id"),
            current.get("run_id"),
        )
        active_route_id = _first_text(
            current.get("active_route_id"),
            current.get("current_route_id"),
            current.get("route_id"),
        )

        runs = self._read_runs(index, current, active_run_id, selected_run_id, findings, watched)
        selected = selected_run_id or active_run_id or (runs[0].run_id if runs else None)
        if selected and not any(run.run_id == selected for run in runs):
            findings.append(f"Selected run is not in the run catalog: {selected}")
            selected = active_run_id if any(run.run_id == active_run_id for run in runs) else None

        selected_run = next((run for run in runs if run.run_id == selected), None)
        nodes: tuple[NodeSummary, ...] = ()
        events: list[EventSummary] = []
        evidence: list[EventSummary] = []
        route_status = "unknown"
        route_version: int | None = None
        selected_route_id = None
        active_node_id = None
        updated_at = None

        if selected_run is not None:
            run_findings: list[str] = []
            run_data, state, frontier, flow, evidence_payload = self._read_run_sources(
                selected_run,
                active_route_id,
                run_findings,
                watched,
            )
            findings.extend(run_findings)
            selected_route_id = _first_text(
                selected_run.active_route_id,
                active_route_id if selected_run.run_id == active_run_id else None,
                state.get("route_id"),
                state.get("active_route"),
                frontier.get("route_id"),
                frontier.get("active_route"),
                flow.get("route_id"),
            )
            active_node_id = _first_text(
                state.get("active_node_id"),
                state.get("active_node"),
                state.get("current_node"),
                frontier.get("active_node_id"),
                frontier.get("active_node"),
                frontier.get("current_node"),
            )
            route_status = normalize_status(flow.get("status") or state.get("status") or frontier.get("status"))
            route_version = _safe_int(flow.get("version") or flow.get("route_version") or frontier.get("route_version"))
            updated_at = _first_text(state.get("updated_at"), frontier.get("updated_at"), run_data.get("updated_at"))
            nodes = self._nodes_from_flow(flow, active_node_id)
            if active_node_id is None:
                active_node_id = self._derive_active_node(nodes)
            events = self._events_from_sources(selected_run, state, frontier, flow, evidence_payload)
            evidence = self._evidence_from_payload(selected_run, evidence_payload)

        statuses = [run.status for run in runs] + [node.status for node in nodes] + [route_status]
        health = status_health(statuses, findings)
        return CockpitSnapshot(
            workspace_root=self.project_root,
            flowpilot_root=self.flowpilot_root,
            active_run_id=active_run_id,
            active_route_id=active_route_id,
            selected_run_id=selected,
            selected_route_id=selected_route_id,
            active_node_id=active_node_id,
            route_status=route_status,
            route_version=route_version,
            updated_at=updated_at,
            runs=tuple(runs),
            nodes=nodes,
            events=tuple(events),
            evidence=tuple(evidence),
            source_health=health,
            source_findings=tuple(findings),
            watched_paths=tuple(sorted((path for path in watched if path.exists()), key=str)),
        )

    def _read_runs(
        self,
        index: dict[str, Any],
        current: dict[str, Any],
        active_run_id: str | None,
        selected_run_id: str | None,
        findings: list[str],
        watched: set[Path],
    ) -> list[RunSummary]:
        raw_runs = index.get("runs")
        catalog: list[dict[str, Any]]
        if isinstance(raw_runs, list):
            catalog = [run for run in raw_runs if isinstance(run, dict)]
        else:
            catalog = []
            if active_run_id:
                catalog.append({"run_id": active_run_id, "active_route_id": current.get("active_route_id")})
            if not catalog:
                findings.append("Run catalog is missing or empty.")

        seen: set[str] = set()
        runs: list[RunSummary] = []
        for item in catalog:
            run_id = _first_text(item.get("run_id"), item.get("id"))
            if not run_id or run_id in seen:
                continue
            seen.add(run_id)
            default_root = self.flowpilot_root / "runs" / run_id
            run_root = _path_from_raw(self.project_root, self.flowpilot_root, item.get("run_root"), default_root)
            run_findings: list[str] = []
            run_json = _read_json(run_root / "run.json", run_findings)
            watched.add(run_root / "run.json")
            status = normalize_status(_first_text(run_json.get("status"), item.get("status")), "unknown")
            title = _first_text(run_json.get("title"), item.get("title"), run_id) or run_id
            active_route = _first_text(
                item.get("active_route_id"),
                run_json.get("active_route_id"),
                current.get("active_route_id") if run_id == active_run_id else None,
            )
            runs.append(
                RunSummary(
                    run_id=run_id,
                    title=title,
                    status=status,
                    active_route_id=active_route,
                    run_root=run_root,
                    created_at=_first_text(run_json.get("created_at"), item.get("created_at")),
                    selected=run_id == (selected_run_id or active_run_id),
                    source_health=status_health([status], run_findings),
                    source_findings=tuple(run_findings),
                )
            )
        return runs

    def _read_run_sources(
        self,
        run: RunSummary,
        active_route_id: str | None,
        findings: list[str],
        watched: set[Path],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        run_json_path = run.run_root / "run.json"
        state_path = run.run_root / "state.json"
        frontier_path = run.run_root / "execution_frontier.json"
        run_json = _read_json(run_json_path, findings)
        state = _read_json(state_path, findings)
        frontier = _read_json(frontier_path, findings)
        route_id = _first_text(
            run.active_route_id,
            active_route_id,
            state.get("route_id"),
            state.get("active_route"),
            frontier.get("route_id"),
            frontier.get("active_route"),
        )
        if route_id:
            flow_path = run.run_root / "routes" / route_id / "flow.json"
        else:
            flow_path = run.run_root / "routes" / "route-001" / "flow.json"
            findings.append(f"Route id is missing for run {run.run_id}; trying route-001.")
        evidence_path = run.run_root / "evidence" / "evidence_ledger.json"
        flow = _read_json(flow_path, findings)
        evidence = _read_json(evidence_path, findings)
        watched.update({run_json_path, state_path, frontier_path, flow_path, evidence_path})
        return run_json, state, frontier, flow, evidence

    def _nodes_from_flow(self, flow: dict[str, Any], active_node_id: str | None) -> tuple[NodeSummary, ...]:
        raw_nodes = flow.get("nodes")
        if not isinstance(raw_nodes, list):
            return ()
        nodes: list[NodeSummary] = []
        for index, raw in enumerate(raw_nodes, start=1):
            if not isinstance(raw, dict):
                continue
            node_id = _first_text(raw.get("id"), raw.get("node_id"), f"node-{index:03d}") or f"node-{index:03d}"
            status = normalize_status(raw.get("status"))
            if node_id == active_node_id and status in {"pending", "unknown", "new"}:
                status = "running"
            gates = raw.get("required_gates")
            if not isinstance(gates, list):
                gates = []
            nodes.append(
                NodeSummary(
                    node_id=node_id,
                    title=_first_text(raw.get("title"), raw.get("summary"), node_id) or node_id,
                    status=status,
                    required_gates=tuple(str(gate) for gate in gates),
                    summary=_first_text(raw.get("summary"), "") or "",
                    updated_at=_first_text(raw.get("updated_at")),
                )
            )
        return tuple(nodes)

    def _derive_active_node(self, nodes: tuple[NodeSummary, ...]) -> str | None:
        for node in nodes:
            if node.status in {"running", "active", "in_progress"}:
                return node.node_id
        for node in nodes:
            if node.status in {"pending", "new", "unknown"}:
                return node.node_id
        return nodes[-1].node_id if nodes else None

    def _events_from_sources(
        self,
        run: RunSummary,
        state: dict[str, Any],
        frontier: dict[str, Any],
        flow: dict[str, Any],
        evidence: dict[str, Any],
    ) -> list[EventSummary]:
        events = [
            EventSummary(_mtime_label(run.run_root / "state.json"), "info", "state.json", "state_loaded", _first_text(state.get("status"), "") or ""),
            EventSummary(_mtime_label(run.run_root / "execution_frontier.json"), "info", "execution_frontier.json", "frontier_loaded", _first_text(frontier.get("active_node_id"), frontier.get("active_node"), "") or ""),
            EventSummary(_mtime_label(run.run_root / "routes" / (_first_text(flow.get("route_id"), run.active_route_id) or "route-001") / "flow.json"), "info", "flow.json", "flow_loaded", f"v{flow.get('version', flow.get('route_version', '?'))}"),
        ]
        entries = evidence.get("entries")
        if isinstance(entries, list):
            events.append(
                EventSummary(
                    _mtime_label(run.run_root / "evidence" / "evidence_ledger.json"),
                    "info",
                    "evidence_ledger.json",
                    "evidence_loaded",
                    f"{len(entries)} entries",
                )
            )
        return events

    def _evidence_from_payload(self, run: RunSummary, evidence: dict[str, Any]) -> list[EventSummary]:
        raw_entries = evidence.get("entries")
        if not isinstance(raw_entries, list):
            return []
        rows: list[EventSummary] = []
        for raw in raw_entries:
            if not isinstance(raw, dict):
                continue
            path = _first_text(raw.get("path"), "")
            rows.append(
                EventSummary(
                    _mtime_label(run.run_root / "evidence" / "evidence_ledger.json"),
                    normalize_status(raw.get("classification"), "current"),
                    _first_text(raw.get("id"), "evidence") or "evidence",
                    path or "",
                    _first_text(raw.get("classification"), "") or "",
                )
            )
        return rows
