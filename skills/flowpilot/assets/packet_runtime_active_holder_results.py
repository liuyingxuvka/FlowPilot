"""Active-holder result submission helpers for packet runtime."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from packet_runtime_active_holder_core import (
    _append_active_holder_event,
    _load_active_holder_lease,
    _require_concrete_agent_id,
    _validate_active_holder_contact,
    write_controller_status_packet,
    write_result,
)
from packet_runtime_ledger import _update_packet_record
from packet_runtime_paths import (
    load_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    resolve_project_path,
)
from packet_runtime_relay import validate_result_ready_for_recipient_relay
from packet_runtime_schema import (
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
    envelope_hash,
    utc_now,
    write_json_atomic,
)


def _write_controller_next_action_notice(
    project_root: Path,
    *,
    lease: dict[str, Any],
    packet_envelope: dict[str, Any],
    result_envelope: dict[str, Any],
    next_action: str,
) -> dict[str, Any]:
    paths = packet_paths_from_result_envelope(project_root, result_envelope)
    notice_path = paths["packet_dir"] / "controller_next_action_notice.json"
    notice = {
        "schema_version": CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
        "notice_id": f"controller-next-{packet_envelope['packet_id']}-{uuid.uuid4().hex}",
        "notice_path": project_relative(project_root, notice_path),
        "run_id": result_envelope.get("run_id", str(paths["run_id"])),
        "packet_id": packet_envelope["packet_id"],
        "node_id": packet_envelope.get("node_id"),
        "from": "router",
        "to": "controller",
        "router_authored": True,
        "next_action": next_action,
        "next_holder": "controller",
        "next_recipient": result_envelope.get("next_recipient"),
        "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
        "result_envelope_hash": envelope_hash(result_envelope),
        "result_body_path": result_envelope.get("result_body_path"),
        "result_body_hash": result_envelope.get("result_body_hash"),
        "controller_visibility": "next_action_metadata_only",
        "controller_may_read_result_body": False,
        "lease_id": lease.get("lease_id"),
        "created_at": utc_now(),
    }
    write_json_atomic(notice_path, notice)
    event = _append_active_holder_event(
        project_root,
        packet_envelope,
        {
            "event": "router_controller_next_action_notice",
            "lease_id": lease["lease_id"],
            "packet_id": packet_envelope["packet_id"],
            "notice_path": project_relative(project_root, notice_path),
            "next_action": next_action,
        },
    )
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        packet_envelope["packet_id"],
        {
            "fast_lane_controller_notice_written": True,
            "router_next_action_notice_path": project_relative(project_root, notice_path),
            "router_next_action_notice": notice,
            "active_packet_status": "router-next-action-ready-for-controller",
            "active_packet_holder": "controller",
            "holder_history": {
                "holder": "controller",
                "status": "router-next-action-ready-for-controller",
                "changed_at": event["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": packet_envelope.get("controller_status_packet_path"),
            },
        },
    )
    write_controller_status_packet(
        project_root,
        packet_envelope,
        holder="controller",
        status="router-next-action-ready-for-controller",
        message=f"Router accepted packet {packet_envelope['packet_id']} result mechanics; Controller should deliver result to {result_envelope.get('next_recipient')}.",
        progress=999,
        progress_updated_by_role=str(result_envelope.get("completed_by_role") or ""),
        progress_updated_by_agent_id=str(result_envelope.get("completed_by_agent_id") or ""),
    )
    return notice


def _controller_next_action_for_result_recipient(next_recipient: object) -> str:
    recipient = str(next_recipient or "").strip()
    if recipient == "project_manager":
        return "deliver_result_to_pm_for_disposition"
    if recipient == "human_like_reviewer":
        return "deliver_result_to_reviewer"
    return "deliver_result_to_recorded_next_recipient"


def active_holder_submit_existing_result(
    project_root: Path,
    *,
    lease_path: str | Path,
    role: str,
    agent_id: str,
    result_envelope_path: str | Path,
    route_version: int | None = None,
    frontier_version: int | None = None,
) -> dict[str, Any]:
    lease = _load_active_holder_lease(project_root, lease_path)
    packet_envelope = _validate_active_holder_contact(
        project_root,
        lease=lease,
        role=role,
        agent_id=agent_id,
        action="submit_result",
        route_version=route_version,
        frontier_version=frontier_version,
    )
    result_envelope = load_envelope(project_root, str(result_envelope_path))
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    audit = validate_result_ready_for_recipient_relay(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result_envelope,
        agent_role_map={_require_concrete_agent_id(agent_id, role=role): role},
    )
    extra_blockers: list[str] = []
    if result_envelope.get("completed_by_role") != role:
        extra_blockers.append("active_holder_result_completed_by_wrong_role")
    if result_envelope.get("completed_by_agent_id") != lease.get("holder_agent_id"):
        extra_blockers.append("active_holder_result_completed_by_wrong_agent")
    if extra_blockers:
        audit = dict(audit)
        audit["blockers"] = list(audit.get("blockers") or []) + extra_blockers
        audit["passed"] = False
    event_name = "active_holder_result_mechanics_passed" if audit["passed"] else "active_holder_result_mechanically_rejected"
    event = _append_active_holder_event(
        project_root,
        packet_envelope,
        {
            "event": event_name,
            "lease_id": lease["lease_id"],
            "packet_id": packet_envelope["packet_id"],
            "holder_role": role,
            "holder_agent_id": _require_concrete_agent_id(agent_id, role=role),
            "result_envelope_path": project_relative(project_root, resolve_project_path(project_root, str(result_envelope_path))),
            "blockers": audit["blockers"],
        },
    )
    if not audit["passed"]:
        _update_packet_record(
            project_root,
            paths["packet_ledger"],
            packet_envelope["packet_id"],
            {
                "fast_lane_mechanical_reject_recorded": True,
                "active_holder_latest_mechanical_reject": event,
                "active_packet_status": "active-holder-mechanical-reject",
                "active_packet_holder": role,
                "holder_history": {
                    "holder": role,
                    "status": "active-holder-mechanical-reject",
                    "changed_at": event["created_at"],
                    "user_status_update_written": True,
                    "controller_status_packet_path": packet_envelope.get("controller_status_packet_path"),
                },
            },
        )
        return {"passed": False, "audit": audit, "event": event}

    notice = _write_controller_next_action_notice(
        project_root,
        lease=lease,
        packet_envelope=packet_envelope,
        result_envelope=result_envelope,
        next_action=_controller_next_action_for_result_recipient(result_envelope.get("next_recipient")),
    )
    lease["status"] = "closed"
    lease["closed_at"] = utc_now()
    lease["closed_by_event"] = event["event"]
    lease["controller_next_action_notice_path"] = notice["notice_path"]
    write_json_atomic(resolve_project_path(project_root, str(lease["lease_path"])), lease)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        packet_envelope["packet_id"],
        {
            "fast_lane_result_mechanics_passed": True,
            "active_holder_lease_status": "closed",
            "active_holder_lease_closed_at": lease["closed_at"],
        },
    )
    return {"passed": True, "audit": audit, "event": event, "controller_next_action_notice": notice}


def active_holder_submit_result(
    project_root: Path,
    *,
    lease_path: str | Path,
    role: str,
    agent_id: str,
    result_body_text: str,
    next_recipient: str,
    route_version: int | None = None,
    frontier_version: int | None = None,
) -> dict[str, Any]:
    lease = _load_active_holder_lease(project_root, lease_path)
    packet_envelope = _validate_active_holder_contact(
        project_root,
        lease=lease,
        role=role,
        agent_id=agent_id,
        action="submit_result",
        route_version=route_version,
        frontier_version=frontier_version,
    )
    result = write_result(
        project_root,
        packet_envelope=packet_envelope,
        completed_by_role=role,
        completed_by_agent_id=agent_id,
        result_body_text=result_body_text,
        next_recipient=next_recipient,
        strict_role=True,
    )
    return active_holder_submit_existing_result(
        project_root,
        lease_path=lease_path,
        role=role,
        agent_id=agent_id,
        result_envelope_path=result["result_body_path"].rsplit("/", 1)[0] + "/result_envelope.json",
        route_version=route_version,
        frontier_version=frontier_version,
    )
