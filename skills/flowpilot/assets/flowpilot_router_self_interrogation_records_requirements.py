"""Self-interrogation clean-record requirement helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from flowpilot_router_errors import RouterError
from flowpilot_router_self_interrogation_records import _self_interrogation_status

def _format_self_interrogation_status_issue(status: dict[str, Any]) -> str:
    issues = status.get("issues") if isinstance(status.get("issues"), list) else []
    if not issues:
        return "unknown issue"
    first = issues[0] if isinstance(issues[0], dict) else {"message": str(issues[0])}
    location = first.get("record_path") or status.get("path") or ""
    return f"{first.get('message', 'unknown issue')} ({location})" if location else str(first.get("message") or "unknown issue")
def _require_clean_self_interrogation(
    project_root: Path,
    run_root: Path,
    *,
    gate_name: str,
    scopes: Iterable[str] | None = None,
    node_id: str | None = None,
    route_version: int | None = None,
) -> dict[str, Any]:
    status = _self_interrogation_status(
        project_root,
        run_root,
        scopes=scopes,
        node_id=node_id,
        route_version=route_version,
    )
    if not status["clean"]:
        raise RouterError(f"{gate_name} requires clean self-interrogation records: {_format_self_interrogation_status_issue(status)}")
    return status
def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path

__all__ = (
    "_format_self_interrogation_status_issue",
    "_require_clean_self_interrogation",
    "resolve_project_path",
)
