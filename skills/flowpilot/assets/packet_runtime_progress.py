"""Packet runtime progress helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import barrier_bundle
from controller_process_aside import (
    build_controller_aside,
    controller_process_aside_contract,
)
from packet_runtime_active_holder import (
    _load_active_holder_lease,
    _require_concrete_agent_id,
    active_holder_ack,
    active_holder_progress,
    active_holder_submit_existing_result,
    active_holder_submit_result,
    issue_active_holder_lease,
)
from packet_runtime_contracts import (
    contract_self_check_metadata,
    default_output_contract,
    ensure_packet_identity_boundary,
    ensure_packet_output_contract_section,
    ensure_result_identity_boundary,
    mutual_role_reminder,
    normalize_output_contract,
    output_contract_id,
    packet_open_work_authority,
    validate_packet_identity_boundary,
    validate_result_identity_boundary,
)
from packet_runtime_ledger import (
    _empty_packet_ledger,
    _packet_ledger_record,
    _update_packet_record,
    _upsert_barrier_bundle_record,
    _upsert_packet_record,
    packet_ledger_record_for_envelope,
)
from packet_runtime_paths import (
    active_run_root,
    load_envelope,
    normalize_envelope_aliases,
    packet_paths,
    packet_paths_from_any_envelope,
    packet_paths_from_envelope,
    packet_paths_from_result_envelope,
    project_relative,
    read_json,
    read_json_if_exists,
    resolve_project_path,
    verify_body_hash,
)
from packet_runtime_relay import (
    _completed_agent_id_is_role_key,
    _same_project_path,
    controller_relay_envelope,
    mark_controller_contamination,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_reviewer_relay,
    verify_controller_relay,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    BARRIER_BUNDLE_SCHEMA,
    CHAIN_AUDIT_SCHEMA,
    CONTROLLER_HANDOFF_SCHEMA,
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
    CONTROLLER_RELAY_SCHEMA,
    DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
    DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
    DIRECT_DISPATCH_FORBIDDEN_ALLOWED_ACTIONS,
    DIRECT_DISPATCH_PACKET_REQUIRED_FIELDS,
    DIRECT_DISPATCH_REQUIRED_FORBIDDEN_ACTIONS,
    OUTPUT_CONTRACT_FORBIDDEN_ENVELOPE_BODY_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_ENVELOPE_FIELDS,
    OUTPUT_CONTRACT_REQUIRED_RESULT_SECTIONS,
    OUTPUT_CONTRACT_SCHEMA,
    PACKET_ENVELOPE_SCHEMA,
    PACKET_IDENTITY_MARKER,
    PACKET_LEDGER_SCHEMA,
    PROGRESS_MESSAGE_FORBIDDEN_TERMS,
    PROGRESS_MESSAGE_MAX_LEN,
    RESULT_CONTROLLER_ALLOWED_ACTIONS,
    RESULT_CONTROLLER_FORBIDDEN_ACTIONS,
    RESULT_ENVELOPE_SCHEMA,
    RESULT_IDENTITY_MARKER,
    RESULT_REVIEW_SESSION_SCHEMA,
    ROLE_KEYS,
    ROLE_PACKET_SESSION_SCHEMA,
    ROUTER_STARTUP_RELEASE_SCHEMA,
    SEALED_BODY_VISIBILITY,
    USER_INTAKE_BODY_VISIBILITY,
    PacketRuntimeError,
    envelope_hash,
    sha256_file,
    stable_json_hash,
    utc_now,
    validate_packet_id,
    write_json_atomic,
    write_text_atomic,
)
from packet_runtime_sessions import (
    _load_role_packet_session,
    begin_result_review_session,
    begin_role_packet_session,
    complete_role_packet_session,
    run_role_packet_session,
)





















def _validate_progress_value(progress: int) -> int:
    if isinstance(progress, bool) or not isinstance(progress, int) or progress < 0:
        raise PacketRuntimeError("progress must be a nonnegative integer")
    return progress

def _validate_progress_message(message: str) -> str:
    text = str(message or "").strip()
    if not text:
        raise PacketRuntimeError("progress message must be non-empty")
    if len(text) > PROGRESS_MESSAGE_MAX_LEN:
        raise PacketRuntimeError(f"progress message must be {PROGRESS_MESSAGE_MAX_LEN} characters or fewer")
    lowered = text.lower()
    for term in PROGRESS_MESSAGE_FORBIDDEN_TERMS:
        if term in lowered:
            raise PacketRuntimeError("progress message must not include sealed body details")
    return text


def _controller_aside_or_error(
    text: str | None,
    *,
    from_role: str,
    source: str,
) -> dict[str, Any] | None:
    try:
        return build_controller_aside(text, from_role=from_role, source=source)
    except ValueError as exc:
        raise PacketRuntimeError(str(exc)) from exc

def write_controller_status_packet(
    project_root: Path,
    envelope: dict[str, Any],
    *,
    holder: str,
    status: str,
    message: str,
    user_status_update_written: bool = True,
    progress: int | None = None,
    progress_updated_by_role: str | None = None,
    progress_updated_by_agent_id: str | None = None,
    work_authority: dict[str, Any] | None = None,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    status_path = resolve_project_path(project_root, envelope["controller_status_packet_path"])
    if progress is not None:
        progress = _validate_progress_value(progress)
    payload = {
        "schema_version": "flowpilot.controller_status_packet.v1",
        "packet_id": envelope["packet_id"],
        "node_id": envelope["node_id"],
        "holder": holder,
        "status": status,
        "message": message,
        "updated_at": utc_now(),
        "user_status_update_written": user_status_update_written,
        "next_expected_event": "role_return_envelope",
        "controller_allowed_actions": DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "controller_visibility": "packet_and_result_envelopes_only",
        "controller_process_aside_contract": controller_process_aside_contract(),
    }
    aside = _controller_aside_or_error(
        controller_aside,
        from_role=progress_updated_by_role or holder,
        source="packet_runtime.controller_status_packet",
    )
    if aside is not None:
        payload["controller_aside"] = aside
    if progress is not None:
        payload["progress"] = progress
        payload["progress_written_by_runtime"] = True
    if progress_updated_by_role:
        payload["progress_updated_by_role"] = progress_updated_by_role
    if progress_updated_by_agent_id:
        payload["progress_updated_by_agent_id"] = progress_updated_by_agent_id
    if work_authority is not None:
        payload["work_authority"] = work_authority
    write_json_atomic(status_path, payload)
    return payload

def update_controller_progress(
    project_root: Path,
    *,
    envelope_path: str | Path,
    role: str,
    agent_id: str,
    progress: int,
    message: str,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    resolved_agent_id = _require_concrete_agent_id(agent_id, role=role)
    envelope = normalize_envelope_aliases(load_envelope(project_root, str(envelope_path)))
    if role != envelope.get("to_role"):
        raise PacketRuntimeError(f"progress may only be updated by to_role={envelope.get('to_role')!r}, not {role!r}")
    return write_controller_status_packet(
        project_root,
        envelope,
        holder=role,
        status="working",
        message=_validate_progress_message(message),
        progress=_validate_progress_value(progress),
        progress_updated_by_role=role,
        progress_updated_by_agent_id=resolved_agent_id,
        controller_aside=controller_aside,
    )
