"""Shared active-holder lease validation helpers for packet runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packet_runtime_ledger import _packet_ledger_record
from packet_runtime_paths import (
    load_envelope,
    packet_paths_from_envelope,
    read_json,
    resolve_project_path,
)
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    ROLE_KEYS,
    PacketRuntimeError,
    utc_now,
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
