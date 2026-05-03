"""Resolve FlowPilot project paths across legacy and run-scoped layouts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_if_exists(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_under_project(project_root: Path, flowpilot_root: Path, value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == ".flowpilot":
        return project_root / path
    return flowpilot_root / path


def resolve_flowpilot_paths(project_root: Path) -> dict[str, Any]:
    """Return canonical paths for the active FlowPilot run.

    New FlowPilot runs are stored below `.flowpilot/runs/<run-id>/`. Legacy
    projects without `.flowpilot/current.json` still resolve to the old
    `.flowpilot/` root so existing evidence can be inspected and migrated.
    """

    root = project_root.resolve()
    flowpilot_root = root / ".flowpilot"
    current_path = flowpilot_root / "current.json"
    index_path = flowpilot_root / "index.json"
    current = read_json_if_exists(current_path)

    run_id = current.get("current_run_id") or current.get("active_run_id") or current.get("run_id")
    run_root = _resolve_under_project(
        root,
        flowpilot_root,
        current.get("current_run_root") or current.get("active_run_root") or current.get("run_root"),
    )
    if run_root is None and run_id:
        run_root = flowpilot_root / "runs" / str(run_id)

    layout = "run_scoped" if run_root is not None else "legacy"
    active_root = run_root or flowpilot_root

    return {
        "project_root": root,
        "flowpilot_root": flowpilot_root,
        "current_path": current_path,
        "index_path": index_path,
        "current": current,
        "layout": layout,
        "run_id": run_id,
        "run_root": active_root,
        "state_path": active_root / "state.json",
        "frontier_path": active_root / "execution_frontier.json",
        "routes_root": active_root / "routes",
        "crew_ledger_path": active_root / "crew_ledger.json",
        "crew_memory_root": active_root / "crew_memory",
        "lifecycle_dir": active_root / "lifecycle",
        "diagrams_dir": active_root / "diagrams",
    }


def resolve_project_relative_path(project_root: Path, raw: str, *, default_key: str) -> Path:
    paths = resolve_flowpilot_paths(project_root)
    if default_key in paths and raw == str(paths[default_key]):
        return Path(paths[default_key])
    path = Path(raw)
    return path if path.is_absolute() else project_root.resolve() / path
