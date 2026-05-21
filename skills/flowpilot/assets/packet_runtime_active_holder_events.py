"""Active-holder ACK and progress helpers for packet runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from packet_runtime_active_holder_core import (
    _append_active_holder_event,
    _load_active_holder_lease,
    _require_concrete_agent_id,
    _validate_active_holder_contact,
    _validate_progress_value,
    update_controller_progress,
)
from packet_runtime_ledger import _update_packet_record
from packet_runtime_paths import packet_paths_from_envelope


def active_holder_ack(
    project_root: Path,
    *,
    lease_path: str | Path,
    role: str,
    agent_id: str,
    route_version: int | None = None,
    frontier_version: int | None = None,
) -> dict[str, Any]:
    lease = _load_active_holder_lease(project_root, lease_path)
    envelope = _validate_active_holder_contact(
        project_root,
        lease=lease,
        role=role,
        agent_id=agent_id,
        action="ack",
        route_version=route_version,
        frontier_version=frontier_version,
    )
    paths = packet_paths_from_envelope(project_root, envelope)
    event = _append_active_holder_event(
        project_root,
        envelope,
        {
            "event": "active_holder_ack",
            "lease_id": lease["lease_id"],
            "packet_id": envelope["packet_id"],
            "holder_role": role,
            "holder_agent_id": _require_concrete_agent_id(agent_id, role=role),
        },
    )
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "active_holder_ack_recorded": True,
            "active_packet_status": "active-holder-acknowledged",
            "active_packet_holder": role,
            "holder_history": {
                "holder": role,
                "status": "active-holder-acknowledged",
                "changed_at": event["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope.get("controller_status_packet_path"),
            },
        },
    )
    return event


def active_holder_progress(
    project_root: Path,
    *,
    lease_path: str | Path,
    role: str,
    agent_id: str,
    progress: int,
    message: str,
    controller_aside: str | None = None,
    route_version: int | None = None,
    frontier_version: int | None = None,
) -> dict[str, Any]:
    lease = _load_active_holder_lease(project_root, lease_path)
    envelope = _validate_active_holder_contact(
        project_root,
        lease=lease,
        role=role,
        agent_id=agent_id,
        action="progress",
        route_version=route_version,
        frontier_version=frontier_version,
    )
    status = update_controller_progress(
        project_root,
        envelope_path=lease["packet_envelope_path"],
        role=role,
        agent_id=agent_id,
        progress=progress,
        message=message,
        controller_aside=controller_aside,
    )
    event_payload = {
        "event": "active_holder_progress",
        "lease_id": lease["lease_id"],
        "packet_id": envelope["packet_id"],
        "holder_role": role,
        "holder_agent_id": _require_concrete_agent_id(agent_id, role=role),
        "progress": _validate_progress_value(progress),
        "message": status["message"],
    }
    if "controller_aside" in status:
        event_payload["controller_aside"] = status["controller_aside"]
    event = _append_active_holder_event(project_root, envelope, event_payload)
    paths = packet_paths_from_envelope(project_root, envelope)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "active_holder_progress_recorded": True,
            "active_holder_latest_progress_event": event,
        },
    )
    return status
