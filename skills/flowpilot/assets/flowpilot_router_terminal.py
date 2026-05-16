"""Pure terminal lifecycle and summary helpers for FlowPilot router."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


FLOWPILOT_PROJECT_URL = "https://github.com/liuyingxuvka/FlowPilot"
TERMINAL_SUMMARY_SCHEMA = "flowpilot.final_summary.v1"
TERMINAL_SUMMARY_ATTRIBUTION = (
    f"Generated with [FlowPilot]({FLOWPILOT_PROJECT_URL}) - a project-control workflow for AI coding agents."
)
TERMINAL_SUMMARY_READ_SCOPE = "current_run_root_all_files"


def _terminal_lifecycle_mode(run_state: dict[str, Any]) -> str | None:
    status = str(run_state.get("status") or "")
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    if status == "cancelled_by_user" or flags.get("run_cancelled_by_user"):
        return "cancelled_by_user"
    if status == "stopped_by_user" or flags.get("run_stopped_by_user"):
        return "stopped_by_user"
    if status == "protocol_dead_end" or flags.get("startup_protocol_dead_end_declared"):
        return "protocol_dead_end"
    if status in {"closed", "completed"} or flags.get("terminal_closure_approved"):
        return "closed"
    return None


def _terminal_summary_markdown_path(run_root: Path) -> Path:
    return run_root / "final_summary.md"


def _terminal_summary_json_path(run_root: Path) -> Path:
    return run_root / "final_summary.json"


def _terminal_summary_hash(summary_markdown: str) -> str:
    return hashlib.sha256(summary_markdown.encode("utf-8")).hexdigest()


def _path_is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
