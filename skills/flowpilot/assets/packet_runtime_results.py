"""Packet runtime results helpers for FlowPilot packet runtime."""

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




















from packet_runtime_progress import write_controller_status_packet

def _controller_aside_or_error(text: str | None, *, from_role: str, source: str) -> dict[str, Any] | None:
    try:
        return build_controller_aside(text, from_role=from_role, source=source)
    except ValueError as exc:
        raise PacketRuntimeError(str(exc)) from exc


def write_result(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    completed_by_role: str,
    completed_by_agent_id: str,
    result_body_text: str,
    next_recipient: str,
    strict_role: bool = True,
    controller_aside: str | None = None,
) -> dict[str, Any]:
    packet_envelope = normalize_envelope_aliases(packet_envelope)
    if strict_role and completed_by_role != packet_envelope.get("to_role"):
        raise PacketRuntimeError(
            f"completed_by_role {completed_by_role!r} does not match packet to_role {packet_envelope.get('to_role')!r}"
        )
    if strict_role:
        verify_controller_relay(packet_envelope, recipient_role=completed_by_role)
        verify_packet_open_receipt(project_root, packet_envelope, role=completed_by_role)
    paths = packet_paths_from_envelope(project_root, packet_envelope)
    result_body_path = paths["result_body"]
    result_envelope_path = paths["result_envelope"]
    output_contract = packet_envelope.get("output_contract") if isinstance(packet_envelope.get("output_contract"), dict) else None
    result_body_text = ensure_result_identity_boundary(result_body_text, completed_by_role)
    validate_result_identity_boundary(result_body_text, completed_by_role)
    write_text_atomic(result_body_path, result_body_text)
    result_body_hash = sha256_file(result_body_path)
    contract_self_check = contract_self_check_metadata(result_body_text, output_contract)
    result_envelope = {
        "schema_version": RESULT_ENVELOPE_SCHEMA,
        "packet_id": packet_envelope["packet_id"],
        "packet_type": "result",
        "run_id": packet_envelope.get("run_id", str(paths["run_id"])),
        "node_id": packet_envelope.get("node_id"),
        "is_current_node": packet_envelope.get("is_current_node", True),
        "source_packet_envelope_path": project_relative(project_root, paths["packet_envelope"]),
        "completed_at": utc_now(),
        "completed_by_role": completed_by_role,
        "completed_by_agent_id": completed_by_agent_id,
        "expected_role_from_packet_envelope": packet_envelope["to_role"],
        "completed_role_matches_packet_to_role": completed_by_role == packet_envelope["to_role"],
        "result_body_path": project_relative(project_root, result_body_path),
        "result_body_hash": result_body_hash,
        "result_body_hash_algorithm": "sha256",
        "source_output_contract_id": output_contract_id(output_contract),
        "contract_self_check": contract_self_check,
        "next_recipient": next_recipient,
        "return_to": "controller",
        "next_holder": next_recipient,
        "body_visibility": SEALED_BODY_VISIBILITY,
        "controller_allowed_actions": RESULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": RESULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "controller_process_aside_contract": controller_process_aside_contract(),
        "created_at": utc_now(),
        "body_access": {
            "controller_can_read_body": False,
            "reviewer_or_pm_can_read_body": True,
            "result_body_hash_required": True,
            "result_body_hash_mismatch_blocks_review_pass": True,
            "recipient_must_verify_controller_relay_before_body_open": True,
        },
        "identity_boundary": {
            "schema_version": "flowpilot.result_identity_boundary.v1",
            "marker": RESULT_IDENTITY_MARKER,
            "completed_by_role": completed_by_role,
            "required": True,
        },
    }
    if output_contract is not None:
        result_envelope["output_contract"] = output_contract
    aside = _controller_aside_or_error(
        controller_aside,
        from_role=completed_by_role,
        source="packet_runtime.result_envelope",
    )
    if aside is not None:
        result_envelope["controller_aside"] = aside
    if isinstance(packet_envelope.get("barrier_bundle"), dict):
        result_envelope["barrier_bundle"] = packet_envelope["barrier_bundle"]
    write_json_atomic(result_envelope_path, result_envelope)

    write_controller_status_packet(
        project_root,
        packet_envelope,
        holder="controller",
        status="result-envelope-returned",
        message=f"Packet {packet_envelope['packet_id']} result envelope is ready for relay to {next_recipient}.",
        progress=999,
        progress_updated_by_role=completed_by_role,
        progress_updated_by_agent_id=completed_by_agent_id,
        controller_aside=controller_aside,
    )

    record = {
        "packet_id": packet_envelope["packet_id"],
        "active_packet_status": "worker-result-needs-review",
        "active_packet_holder": "controller",
        "result_envelope_path": project_relative(project_root, result_envelope_path),
        "result_body_path": result_envelope["result_body_path"],
        "result_body_hash": result_body_hash,
        "source_output_contract_id": output_contract_id(output_contract),
        "contract_self_check": contract_self_check,
        "result_body_hash_verified": False,
        "result_envelope": {
            "packet_type": "result",
            "completed_by_role": completed_by_role,
            "completed_by_agent_id": completed_by_agent_id,
            "expected_role_from_packet_envelope": packet_envelope["to_role"],
            "completed_role_matches_packet_to_role": completed_by_role == packet_envelope["to_role"],
            "completed_agent_id_belongs_to_role": False,
            "next_recipient": next_recipient,
            "source_output_contract_id": output_contract_id(output_contract),
            "contract_self_check": contract_self_check,
            "controller_relay_signature_required": True,
            "result_body_identity_boundary_required": True,
            "result_body_identity_boundary_marker": RESULT_IDENTITY_MARKER,
            "controller_process_aside_contract": result_envelope["controller_process_aside_contract"],
        },
    }
    if aside is not None:
        record["controller_aside"] = aside
        record["result_envelope"]["controller_aside"] = aside
    if isinstance(packet_envelope.get("barrier_bundle"), dict):
        record["barrier_bundle"] = packet_envelope["barrier_bundle"]
    if output_contract is not None:
        record["output_contract"] = output_contract
        record["result_envelope"]["output_contract"] = output_contract
    _upsert_packet_record(project_root, paths["packet_ledger"], str(paths["run_id"]), paths["run_root"], record)
    return result_envelope

def read_result_body_for_role(project_root: Path, result_envelope: dict[str, Any], *, role: str) -> str:
    result_envelope.update(normalize_envelope_aliases(result_envelope))
    verify_controller_relay(result_envelope, recipient_role=role)
    allowed = {result_envelope.get("next_recipient"), "human_like_reviewer", "project_manager"}
    if role not in allowed:
        raise PacketRuntimeError(f"result body may only be read by {sorted(value for value in allowed if value)}, not {role!r}")
    body_path = resolve_project_path(project_root, result_envelope["result_body_path"])
    if sha256_file(body_path) != result_envelope["result_body_hash"]:
        raise PacketRuntimeError("result body hash mismatch")
    body_text = body_path.read_text(encoding="utf-8")
    validate_result_identity_boundary(body_text, str(result_envelope.get("completed_by_role") or ""))
    opened = {
        "role": role,
        "opened_at": utc_now(),
        "controller_relay_verified": True,
        "body_hash_verified": True,
    }
    result_envelope["result_body_opened_by_role"] = opened
    paths = packet_paths_from_result_envelope(project_root, result_envelope)
    write_json_atomic(paths["result_envelope"], result_envelope)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        result_envelope["packet_id"],
        {
            "result_body_opened_by_role": role,
            "result_body_opened_after_controller_relay_check": True,
            "result_body_open_record": opened,
            "active_packet_status": "result-body-opened-by-recipient",
            "active_packet_holder": role,
        },
    )
    return body_text
