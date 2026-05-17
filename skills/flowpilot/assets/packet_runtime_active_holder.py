"""Active-holder lease and fast-lane submission helpers for packet runtime."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from packet_runtime_ledger import _packet_ledger_record, _update_packet_record
from packet_runtime_paths import (
    load_envelope,
    normalize_envelope_aliases,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    resolve_project_path,
)
from packet_runtime_relay import (
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_reviewer_relay,
    verify_controller_relay,
)
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
    ROLE_KEYS,
    PacketRuntimeError,
    envelope_hash,
    utc_now,
    write_json_atomic,
)


def write_controller_status_packet(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import packet_runtime

    return packet_runtime.write_controller_status_packet(*args, **kwargs)


def update_controller_progress(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import packet_runtime

    return packet_runtime.update_controller_progress(*args, **kwargs)


def _validate_progress_value(*args: Any, **kwargs: Any) -> int:
    import packet_runtime

    return packet_runtime._validate_progress_value(*args, **kwargs)


def write_result(*args: Any, **kwargs: Any) -> dict[str, Any]:
    import packet_runtime

    return packet_runtime.write_result(*args, **kwargs)


def _require_concrete_agent_id(agent_id: str, *, role: str) -> str:
    resolved = str(agent_id or "").strip()
    if not resolved:
        raise PacketRuntimeError(f"{role} runtime session requires a concrete agent_id")
    if resolved in ROLE_KEYS:
        raise PacketRuntimeError("agent_id must be a concrete agent id, not a role key")
    return resolved

def _active_holder_lease_path(project_root: Path, envelope: dict[str, Any]) -> Path:
    paths = packet_paths_from_envelope(project_root, envelope)
    return paths["packet_dir"] / "active_holder_lease.json"

def _active_holder_events_path(project_root: Path, envelope: dict[str, Any]) -> Path:
    paths = packet_paths_from_envelope(project_root, envelope)
    return paths["packet_dir"] / "active_holder_events.jsonl"

def _append_active_holder_event(
    project_root: Path,
    envelope: dict[str, Any],
    event: dict[str, Any],
) -> dict[str, Any]:
    event = dict(event)
    event.setdefault("schema_version", ACTIVE_HOLDER_EVENT_SCHEMA)
    event.setdefault("created_at", utc_now())
    event_path = _active_holder_events_path(project_root, envelope)
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")
    return event

def _load_active_holder_lease(project_root: Path, lease_path: str | Path) -> dict[str, Any]:
    path = resolve_project_path(project_root, str(lease_path))
    lease = read_json(path)
    if lease.get("schema_version") != ACTIVE_HOLDER_LEASE_SCHEMA:
        raise PacketRuntimeError("active-holder lease has unsupported schema_version")
    if lease.get("lease_path") and resolve_project_path(project_root, str(lease["lease_path"])) != path:
        raise PacketRuntimeError("active-holder lease path does not match lease record")
    return lease

def issue_active_holder_lease(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    holder_role: str,
    holder_agent_id: str,
    route_version: int,
    frontier_version: int,
    allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    """Create a short-lived Router-authorized lease for the current packet holder."""

    packet_envelope = normalize_envelope_aliases(packet_envelope)
    resolved_agent_id = _require_concrete_agent_id(holder_agent_id, role=holder_role)
    if holder_role != packet_envelope.get("to_role"):
        raise PacketRuntimeError("active-holder lease may only be issued to the packet to_role")
    verify_controller_relay(packet_envelope, recipient_role=holder_role)
    audit = validate_packet_ready_for_direct_relay(
        project_root,
        packet_envelope=packet_envelope,
        envelope_path=packet_paths_from_envelope(project_root, packet_envelope)["packet_envelope"],
        allowed_target_roles={holder_role},
    )
    if not audit.get("passed"):
        raise PacketRuntimeError(f"packet is not ready for active-holder lease: {audit.get('blockers')}")
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    lease_path = _active_holder_lease_path(project_root, packet_envelope)
    lease = {
        "schema_version": ACTIVE_HOLDER_LEASE_SCHEMA,
        "lease_id": f"active-holder-{packet_envelope['packet_id']}-{uuid.uuid4().hex}",
        "lease_path": project_relative(project_root, lease_path),
        "run_id": packet_envelope.get("run_id", str(paths["run_id"])),
        "packet_id": packet_envelope["packet_id"],
        "node_id": packet_envelope.get("node_id"),
        "holder_role": holder_role,
        "holder_agent_id": resolved_agent_id,
        "route_version": int(route_version),
        "frontier_version": int(frontier_version),
        "allowed_actions": allowed_actions
        or ["ack", "progress", "submit_result", "resubmit_result"],
        "packet_envelope_path": project_relative(project_root, paths["packet_envelope"]),
        "packet_body_path": packet_envelope.get("body_path"),
        "packet_body_hash": packet_envelope.get("body_hash"),
        "result_envelope_path": packet_envelope.get("result_envelope_path"),
        "result_body_path": packet_envelope.get("result_body_path"),
        "body_visibility": packet_envelope.get("body_visibility"),
        "controller_visibility": "lease_metadata_only",
        "controller_may_read_body": False,
        "status": "active",
        "issued_at": utc_now(),
        "router_authored": True,
    }
    write_json_atomic(lease_path, lease)
    event = _append_active_holder_event(
        project_root,
        packet_envelope,
        {
            "event": "active_holder_lease_issued",
            "lease_id": lease["lease_id"],
            "packet_id": packet_envelope["packet_id"],
            "holder_role": holder_role,
            "holder_agent_id": resolved_agent_id,
        },
    )
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        packet_envelope["packet_id"],
        {
            "active_holder_lease_issued": True,
            "active_holder_lease_path": lease["lease_path"],
            "active_holder_lease_id": lease["lease_id"],
            "active_holder_role": holder_role,
            "active_holder_agent_id": resolved_agent_id,
            "active_holder_route_version": int(route_version),
            "active_holder_frontier_version": int(frontier_version),
            "active_packet_status": "active-holder-lease-issued",
            "active_packet_holder": holder_role,
            "holder_history": {
                "holder": holder_role,
                "status": "active-holder-lease-issued",
                "changed_at": event["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": packet_envelope.get("controller_status_packet_path"),
            },
        },
    )
    return lease

def _validate_active_holder_contact(
    project_root: Path,
    *,
    lease: dict[str, Any],
    role: str,
    agent_id: str,
    action: str,
    route_version: int | None = None,
    frontier_version: int | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    blockers: list[str] = []
    if lease.get("status") != "active":
        blockers.append("active_holder_lease_not_active")
    if role != lease.get("holder_role"):
        blockers.append("active_holder_contact_by_wrong_role")
    if resolved_agent_id != lease.get("holder_agent_id"):
        blockers.append("active_holder_contact_by_wrong_agent")
    if action not in set(lease.get("allowed_actions") or []):
        blockers.append("active_holder_action_not_allowed")
    if route_version is not None and int(route_version) != int(lease.get("route_version", -1)):
        blockers.append("active_holder_route_version_stale")
    if frontier_version is not None and int(frontier_version) != int(lease.get("frontier_version", -1)):
        blockers.append("active_holder_frontier_version_stale")
    envelope = load_envelope(project_root, str(lease["packet_envelope_path"]))
    if envelope.get("packet_id") != lease.get("packet_id"):
        blockers.append("active_holder_packet_id_mismatch")
    if envelope.get("to_role") != lease.get("holder_role"):
        blockers.append("active_holder_packet_role_mismatch")
    if envelope.get("body_hash") != lease.get("packet_body_hash"):
        blockers.append("active_holder_packet_body_hash_changed")
    paths = packet_paths_from_envelope(project_root, envelope)
    record = _packet_ledger_record(paths["packet_ledger"], str(lease.get("packet_id") or ""))
    if not isinstance(record, dict):
        blockers.append("active_holder_packet_ledger_record_missing")
    else:
        if record.get("active_holder_lease_id") not in {None, lease.get("lease_id")}:
            blockers.append("active_holder_lease_not_current")
        if record.get("packet_body_hash") != lease.get("packet_body_hash"):
            blockers.append("active_holder_ledger_body_hash_mismatch")
    if blockers:
        raise PacketRuntimeError(f"active-holder contact rejected: {blockers}")
    return envelope

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
    )
    event = _append_active_holder_event(
        project_root,
        envelope,
        {
            "event": "active_holder_progress",
            "lease_id": lease["lease_id"],
            "packet_id": envelope["packet_id"],
            "holder_role": role,
            "holder_agent_id": _require_concrete_agent_id(agent_id, role=role),
            "progress": _validate_progress_value(progress),
            "message": status["message"],
        },
    )
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
    audit = validate_result_ready_for_reviewer_relay(
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
