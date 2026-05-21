"""Packet creation core helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import barrier_bundle
from controller_process_aside import controller_process_aside_contract
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



def create_packet(
    project_root: Path,
    *,
    packet_id: str,
    from_role: str,
    to_role: str,
    node_id: str,
    body_text: str,
    run_id: str | None = None,
    is_current_node: bool = True,
    return_to: str = "controller",
    next_holder: str | None = None,
    controller_allowed_actions: list[str] | None = None,
    controller_forbidden_actions: list[str] | None = None,
    packet_type: str = "work_packet",
    body_visibility: str = SEALED_BODY_VISIBILITY,
    replacement_for: str | None = None,
    supersedes: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    barrier_bundle: dict[str, Any] | None = None,
    output_contract: dict[str, Any] | None = None,
    initial_holder: str = "controller",
    initial_ledger_status: str = "packet-with-controller",
    initial_status_packet_status: str = "envelope-created",
    router_owned_startup_material: bool = False,
) -> dict[str, Any]:
    paths = packet_paths(project_root, packet_id, run_id)
    resolved_run_id = str(paths["run_id"])
    run_root = paths["run_root"]
    packet_body_path = paths["packet_body"]
    packet_envelope_path = paths["packet_envelope"]
    controller_status_path = paths["controller_status_packet"]
    result_envelope_rel = project_relative(project_root, paths["result_envelope"])
    result_body_rel = project_relative(project_root, paths["result_body"])
    output_contract = normalize_output_contract(
        output_contract,
        packet_type=packet_type,
        from_role=from_role,
        to_role=to_role,
        node_id=node_id,
    )
    if output_contract is not None:
        output_contract = dict(output_contract)
        output_contract.setdefault("expected_result_envelope_path", result_envelope_rel)
        output_contract.setdefault("expected_result_body_path", result_body_rel)
        output_contract.setdefault("write_target_path", result_body_rel)
    body_text = ensure_packet_identity_boundary(body_text, to_role)
    body_text = ensure_packet_output_contract_section(body_text, output_contract)
    validate_packet_identity_boundary(body_text, to_role)
    write_text_atomic(packet_body_path, body_text)
    body_hash = sha256_file(packet_body_path)

    envelope = {
        "schema_version": PACKET_ENVELOPE_SCHEMA,
        "packet_id": packet_id,
        "packet_type": packet_type,
        "from_role": from_role,
        "to_role": to_role,
        "node_id": node_id,
        "is_current_node": is_current_node,
        "body_path": project_relative(project_root, packet_body_path),
        "body_hash": body_hash,
        "body_hash_algorithm": "sha256",
        "result_envelope_path": result_envelope_rel,
        "result_body_path": result_body_rel,
        "expected_result_envelope_path": result_envelope_rel,
        "expected_result_body_path": result_body_rel,
        "write_target_path": result_body_rel,
        "result_write_target": {
            "result_envelope_path": result_envelope_rel,
            "result_body_path": result_body_rel,
        },
        "body_visibility": body_visibility,
        "replacement_for": replacement_for,
        "supersedes": supersedes or ([] if replacement_for is None else [replacement_for]),
        "return_to": return_to,
        "next_holder": next_holder or to_role,
        "controller_allowed_actions": controller_allowed_actions or DEFAULT_CONTROLLER_ALLOWED_ACTIONS,
        "controller_forbidden_actions": controller_forbidden_actions or DEFAULT_CONTROLLER_FORBIDDEN_ACTIONS,
        "controller_status_packet_path": project_relative(project_root, controller_status_path),
        "controller_process_aside_contract": controller_process_aside_contract(),
        "body_access": {
            "controller_can_read_body": False,
            "controller_can_execute_body": False,
            "target_role_can_read_body": True,
            "body_hash_required": True,
            "body_hash_mismatch_blocks_dispatch": True,
            "recipient_must_verify_controller_relay_before_body_open": True,
        },
        "identity_boundary": {
            "schema_version": "flowpilot.packet_identity_boundary.v1",
            "marker": PACKET_IDENTITY_MARKER,
            "recipient_role": to_role,
            "required": True,
        },
        "metadata": metadata or {},
        "created_at": utc_now(),
    }
    if output_contract is not None:
        envelope["output_contract"] = output_contract
        envelope["output_contract_id"] = output_contract_id(output_contract)
        envelope["metadata"] = {
            **envelope["metadata"],
            "output_contract_id": output_contract_id(output_contract),
        }
    if barrier_bundle is not None:
        envelope["barrier_bundle"] = barrier_bundle
    write_json_atomic(packet_envelope_path, envelope)

    write_controller_status_packet(
        project_root,
        envelope,
        holder=initial_holder,
        status=initial_status_packet_status,
        message=(
            f"Packet {packet_id} is held by Router as startup material for {to_role}."
            if router_owned_startup_material
            else f"Packet {packet_id} envelope is ready for relay to {to_role}."
        ),
        progress=0,
    )
    record = {
        "packet_id": packet_id,
        "packet_type": packet_type,
        "node_id": node_id,
        "created_by_role": from_role,
        "created_at": envelope["created_at"],
        "body_visibility": body_visibility,
        "replacement_for": replacement_for,
        "supersedes": supersedes or ([] if replacement_for is None else [replacement_for]),
        "packet_envelope_path": project_relative(project_root, packet_envelope_path),
        "packet_body_path": envelope["body_path"],
        "physical_packet_files_written": True,
        "controller_context_body_exclusion_verified": True,
        "packet_body_hash": body_hash,
        "output_contract_id": output_contract_id(output_contract),
        "packet_body_hash_verified": False,
        "controller_packet_body_access_detected": False,
        "controller_packet_body_execution_detected": False,
        "controller_relay_signature_required": True,
        "recipient_must_verify_controller_relay_before_body_open": True,
        "packet_body_identity_boundary_required": True,
        "packet_body_identity_boundary_marker": PACKET_IDENTITY_MARKER,
        "packet_envelope": {
            "packet_type": packet_type,
            "from_role": from_role,
            "to_role": to_role,
            "node_id": node_id,
            "is_current_node": is_current_node,
            "return_to": return_to,
            "next_holder": next_holder or to_role,
            "body_visibility": body_visibility,
            "replacement_for": replacement_for,
            "result_envelope_path": result_envelope_rel,
            "result_body_path": result_body_rel,
            "expected_result_envelope_path": result_envelope_rel,
            "expected_result_body_path": result_body_rel,
            "write_target_path": result_body_rel,
            "result_write_target": {
                "result_envelope_path": result_envelope_rel,
                "result_body_path": result_body_rel,
            },
            "controller_allowed_actions": envelope["controller_allowed_actions"],
            "controller_forbidden_actions": envelope["controller_forbidden_actions"],
            "controller_process_aside_contract": envelope["controller_process_aside_contract"],
            "output_contract_id": output_contract_id(output_contract),
        },
        "holder_history": [
            {
                "holder": initial_holder,
                "status": initial_status_packet_status,
                "changed_at": envelope["created_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope["controller_status_packet_path"],
            }
        ],
        "active_packet_status": initial_ledger_status,
        "active_packet_holder": initial_holder,
        "router_direct_dispatch_decision": "pending",
        "router_owned_startup_material": router_owned_startup_material,
        "reviewer_dispatch_decision": "not_required",
        "assigned_worker_role": to_role,
        "result_envelope_path": result_envelope_rel,
        "result_body_path": result_body_rel,
        "expected_result_envelope_path": result_envelope_rel,
        "expected_result_body_path": result_body_rel,
        "write_target_path": result_body_rel,
        "result_write_target": {
            "result_envelope_path": result_envelope_rel,
            "result_body_path": result_body_rel,
        },
        "result_body_hash": None,
        "result_body_hash_verified": False,
        "role_origin_audit": {
            "required_for_every_packet": True,
            "reviewer_must_check_before_pass": True,
            "packet_envelope_checked": False,
            "packet_runtime_physical_files_checked": False,
            "controller_context_body_exclusion_checked": False,
            "packet_envelope_to_role_checked": False,
            "packet_body_hash_checked": False,
            "result_envelope_checked": False,
            "result_envelope_completed_by_role_checked": False,
            "result_envelope_completed_by_agent_id_checked": False,
            "result_body_hash_checked": False,
            "expected_executor_role": to_role,
            "actual_result_author_role": "unknown",
            "controller_origin_evidence_detected": False,
            "wrong_role_completion_detected": False,
            "wrong_role_completion_cosign_or_relabel_forbidden": True,
            "body_hash_mismatch_detected": False,
            "stale_body_reuse_detected": False,
            "invalid_role_origin_blocked": False,
            "controller_boundary_warning_issued": False,
            "pm_reissue_or_repair_required": False,
            "contaminated_evidence_disposition": "none",
        },
        "controller_origin_evidence_allowed": False,
    }
    if barrier_bundle is not None:
        record["barrier_bundle"] = barrier_bundle
    if output_contract is not None:
        record["output_contract"] = output_contract
        record["packet_envelope"]["output_contract"] = output_contract
    _upsert_packet_record(project_root, paths["packet_ledger"], resolved_run_id, run_root, record)
    for superseded_id in record["supersedes"]:
        _update_packet_record(
            project_root,
            paths["packet_ledger"],
            superseded_id,
            {
                "replaced_by": packet_id,
                "replacement_packet_id": packet_id,
                "active_packet_status": "superseded-by-replacement",
            },
        )
    return envelope
