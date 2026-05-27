"""Active-holder lease issue helpers for packet runtime."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from packet_runtime_active_holder_core import (
    _active_holder_lease_path,
    _append_active_holder_event,
    _require_concrete_agent_id,
)
from packet_runtime_ledger import _update_packet_record
from packet_runtime_paths import (
    normalize_envelope_aliases,
    packet_paths_from_envelope,
    project_relative,
    read_json_if_exists,
)
from packet_runtime_relay import (
    validate_packet_ready_for_direct_relay,
    verify_controller_relay,
)


LIVE_CREW_SLOT_STATUSES = {
    "live_agent_started",
    "live_agent_rehydrated",
    "live_agent_recovered",
    "live_agent_recycled",
}


def _active_holder_liveness_evidence(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    holder_role: str,
    holder_agent_id: str,
) -> dict[str, Any]:
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    crew_path = paths["run_root"] / "crew_ledger.json"
    crew = read_json_if_exists(crew_path)
    slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        if str(slot.get("role_key") or "") != holder_role:
            continue
        if str(slot.get("agent_id") or "") != holder_agent_id:
            raise PacketRuntimeError("active-holder lease agent does not match current live role slot")
        status = str(slot.get("status") or "")
        if status not in LIVE_CREW_SLOT_STATUSES:
            raise PacketRuntimeError(f"active-holder lease requires live host liveness proof for {holder_role}")
        liveness_status = str(slot.get("host_liveness_status") or "")
        liveness_decision = str(slot.get("liveness_decision") or "")
        if liveness_status in {"missing", "cancelled", "unknown", "timeout_unknown", "completed"}:
            raise PacketRuntimeError(f"active-holder lease requires active host liveness proof for {holder_role}")
        if status == "live_agent_started":
            host_liveness_proven = liveness_status in {"", "active"}
        elif status == "live_agent_rehydrated":
            host_liveness_proven = liveness_status == "active" and liveness_decision == "confirmed_existing_agent"
        else:
            host_liveness_proven = liveness_status == "active" and liveness_decision in {
                "confirmed_existing_agent",
                "spawned_replacement_from_current_run_memory",
            }
        if not host_liveness_proven:
            raise PacketRuntimeError(f"active-holder lease requires active host liveness proof for {holder_role}")
        return {
            "schema_version": "flowpilot.active_holder_liveness_evidence.v1",
            "source": "crew_ledger",
            "crew_ledger_path": project_relative(project_root, crew_path),
            "run_id": paths["run_id"],
            "role_key": holder_role,
            "agent_id": holder_agent_id,
            "role_slot_status": status,
            "host_liveness_status": slot.get("host_liveness_status"),
            "liveness_decision": slot.get("liveness_decision"),
            "spawn_result": slot.get("spawn_result"),
            "recovery_result": slot.get("last_role_recovery_result") or slot.get("recovery_result"),
            "crew_generation": slot.get("crew_generation"),
            "role_binding_epoch": slot.get("role_binding_epoch"),
            "host_liveness_proven": host_liveness_proven,
        }
    raise PacketRuntimeError(f"active-holder lease requires current live role slot for {holder_role}")
from packet_runtime_schema import (
    ACTIVE_HOLDER_LEASE_SCHEMA,
    PacketRuntimeError,
    utc_now,
    write_json_atomic,
)


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
    holder_liveness = _active_holder_liveness_evidence(
        project_root,
        packet_envelope=packet_envelope,
        holder_role=holder_role,
        holder_agent_id=resolved_agent_id,
    )
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
        "holder_liveness": holder_liveness,
        "host_liveness_proof_required": True,
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
            "active_holder_liveness": holder_liveness,
            "active_holder_liveness_proven": True,
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
