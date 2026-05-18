"""Route source loading and display review evidence for FlowPilot's user route sign."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_user_flow_tree import _all_route_nodes, _route_display_depth, _snapshot_route


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}




def _route_source_summary(route: dict[str, Any]) -> dict[str, int]:
    nodes = _all_route_nodes(route)
    checklist_count = 0
    for node in nodes:
        checklist = node.get("checklist")
        if isinstance(checklist, list):
            checklist_count += len(checklist)
    return {
        "node_count": len(nodes),
        "checklist_item_count": checklist_count,
    }


def _route_source_candidates(
    routes_root: Path,
    active_route: str | None,
    snapshot_route_id: str | None,
    *,
    include_drafts: bool = False,
) -> list[Path]:
    route_ids: list[str] = []
    for raw in (active_route, snapshot_route_id, "route-001"):
        if raw and raw not in route_ids:
            route_ids.append(str(raw))
    candidates: list[Path] = []
    for route_id in route_ids:
        route_dir = routes_root / route_id
        candidates.append(route_dir / "flow.json")
        if include_drafts:
            candidates.append(route_dir / "flow.draft.json")
    if routes_root.exists():
        candidates.extend(sorted(routes_root.glob("*/flow.json")))
        if include_drafts:
            candidates.extend(sorted(routes_root.glob("*/flow.draft.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in candidates:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def _load_route_source(
    paths: dict[str, Any],
    *,
    active_route: str | None,
    snapshot: dict[str, Any],
    include_drafts: bool = False,
) -> tuple[dict[str, Any], Path, str]:
    routes_root = Path(paths["routes_root"])
    snapshot_path = Path(paths["run_root"]) / "route_state_snapshot.json"
    snapshot_route = _snapshot_route(snapshot)
    snapshot_route_id = str(snapshot_route.get("route_id") or "") or None
    for path in _route_source_candidates(
        routes_root,
        active_route,
        snapshot_route_id,
        include_drafts=include_drafts,
    ):
        route = _load_json(path)
        if route.get("nodes"):
            suffix = "flow_json" if path.name == "flow.json" else "flow_draft"
            return route, path, suffix
    committed_route_exists = any(
        path.exists()
        for path in _route_source_candidates(
            routes_root,
            active_route,
            snapshot_route_id,
            include_drafts=False,
        )
    )
    if snapshot_route.get("nodes") and committed_route_exists:
        return snapshot_route, snapshot_path, "route_state_snapshot"
    fallback_route_id = active_route or snapshot_route_id or "route-001"
    return {}, routes_root / fallback_route_id / "flow.json", "none"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _review_display(
    *,
    display_packet: dict[str, Any],
    mermaid: str,
    chat_displayed: bool,
    ui_displayed: bool,
) -> dict[str, Any]:
    findings: list[str] = []
    if display_packet["chat_display_required"] and not chat_displayed:
        findings.append("Cockpit UI is closed, but the Mermaid route sign was not confirmed in chat.")
    if not display_packet["simplified_flowpilot_english_mermaid"]:
        findings.append("The display artifact is not the simplified English FlowPilot route sign.")
    if display_packet["raw_flowguard_mermaid"]["enabled"]:
        findings.append("Raw FlowGuard Mermaid cannot satisfy the user route sign gate.")
    if display_packet["source_health"]["status"] != "ok":
        findings.extend(display_packet["source_health"]["findings"])
    if display_packet["return_or_repair"]["required"] and not display_packet["return_or_repair"]["edge_present"]:
        findings.append("A review/validation return or route mutation lacks a visible repair edge.")
    active_node = str(display_packet.get("active_node") or "")
    active_path_ids = {
        str(item.get("node_id") or item.get("id") or "")
        for item in display_packet.get("active_path", [])
        if isinstance(item, dict)
    }
    active_highlight = display_packet.get("active_highlight") if isinstance(display_packet.get("active_highlight"), dict) else {}
    visible_mermaid_id = str(active_highlight.get("visible_mermaid_id") or "")
    active_graph_highlighted = bool(
        visible_mermaid_id
        and re.search(rf"\bclass\s+[^;\n]*\b{re.escape(visible_mermaid_id)}\b[^;\n]*\sactive\s*;", mermaid)
    )
    active_node_visible = bool(active_node and (active_node in mermaid or active_node in active_path_ids))
    canonical_route = bool(display_packet.get("canonical_route_available"))
    if canonical_route and active_node and not active_graph_highlighted:
        findings.append("The route sign does not highlight the active node or its nearest visible route ancestor.")
    elif active_node and not active_node_visible:
        findings.append("The route sign does not include the active node in either the visible diagram or current path.")
    if not display_packet.get("graph_labels_surface_neutral", True):
        findings.append("The shared Mermaid route sign labels are not surface-neutral.")
    if not chat_displayed and not ui_displayed:
        findings.append("No visible display surface was confirmed.")
    return {
        "schema_version": "flowpilot.user_flow_diagram.review.v1",
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "reviewer_role": "human_like_reviewer",
        "status": "pass" if not findings else "blocked",
        "checked_chat_display": chat_displayed,
        "checked_cockpit_ui_display": ui_displayed,
        "checked_active_route_node_match": active_graph_highlighted if canonical_route and active_node else active_node_visible if active_node else False,
        "checked_active_graph_highlight": active_graph_highlighted,
        "checked_return_or_repair_edge": not display_packet["return_or_repair"]["required"]
        or display_packet["return_or_repair"]["edge_present"],
        "blocking_findings": findings,
    }
