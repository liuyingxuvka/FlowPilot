"""Packet runtime creation helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

import barrier_bundle
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

def router_release_startup_user_intake(
    project_root: Path,
    *,
    envelope: dict[str, Any],
    envelope_path: str | Path,
    released_to_role: str = "project_manager",
    source: str = "router_return_settlement_finalizer",
) -> dict[str, Any]:
    envelope.update(normalize_envelope_aliases(envelope))
    if envelope.get("packet_type") != "user_intake":
        raise PacketRuntimeError("router startup release is only valid for user_intake packets")
    if envelope.get("to_role") != released_to_role:
        raise PacketRuntimeError("router startup release target does not match user_intake target role")
    if envelope.get("body_visibility") == USER_INTAKE_BODY_VISIBILITY:
        raise PacketRuntimeError("router startup release requires sealed startup intake body visibility")

    paths = packet_paths_from_any_envelope(project_root, envelope)
    resolved_envelope_path = resolve_project_path(project_root, str(envelope_path))
    ledger_record = _packet_ledger_record(paths["packet_ledger"], str(envelope.get("packet_id") or ""))
    holder_before = (
        str(ledger_record.get("active_packet_holder") or "")
        if isinstance(ledger_record, dict)
        else str(envelope.get("from_role") or "router")
    )
    existing_release = envelope.get("router_startup_release")
    if (
        isinstance(existing_release, dict)
        and existing_release.get("schema_version") == ROUTER_STARTUP_RELEASE_SCHEMA
        and existing_release.get("delivered_by_router") is True
        and existing_release.get("relayed_to_role") == released_to_role
    ):
        return envelope

    release = {
        "schema_version": ROUTER_STARTUP_RELEASE_SCHEMA,
        "delivered_by_router": True,
        "source": source,
        "released_at": utc_now(),
        "received_from_role": "user",
        "relayed_to_role": released_to_role,
        "holder_before": holder_before or "router",
        "holder_after": released_to_role,
        "body_was_read_by_router": False,
        "body_was_executed_by_router": False,
        "body_visibility": envelope.get("body_visibility", SEALED_BODY_VISIBILITY),
        "startup_release_condition": "legacy_startup_router_release_only",
        "recipient_must_verify_before_body_open": True,
        "controller_bypass_scope": "startup_user_intake_only",
        "normal_role_packet_relay_unchanged": True,
        "deprecated_for_open_authority": True,
        "recipient_open_authority": "controller_relay_required",
        "envelope_hash": envelope_hash(envelope),
    }
    envelope["router_startup_release"] = release
    history = list(envelope.get("router_startup_release_history") or [])
    history.append(release)
    envelope["router_startup_release_history"] = history
    write_json_atomic(resolved_envelope_path, envelope)

    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "packet_router_release": release,
            "router_startup_release_history": release,
            "router_owned_startup_material": True,
            "router_direct_dispatch_decision": "released_by_router_startup_finalizer",
            "recipient_must_verify_router_startup_release_before_body_open": True,
            "active_packet_status": "envelope-relayed",
            "active_packet_holder": released_to_role,
            "holder_history": {
                "holder": released_to_role,
                "status": "envelope-relayed",
                "changed_at": release["released_at"],
                "user_status_update_written": True,
                "controller_status_packet_path": envelope.get("controller_status_packet_path"),
                "source": source,
            },
        },
    )
    write_controller_status_packet(
        project_root,
        envelope,
        holder=released_to_role,
        status="envelope-relayed",
        message=f"Legacy Router startup release recorded for {released_to_role}; Controller relay remains required before body open.",
        progress=0,
    )
    return envelope

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

def create_user_intake_packet(
    project_root: Path,
    *,
    packet_id: str,
    node_id: str,
    body_text: str,
    run_id: str | None = None,
    startup_options: dict[str, Any] | None = None,
    source: str = "user_chat_prompt",
    body_visibility: str | None = None,
    startup_intake_ref: dict[str, Any] | None = None,
    router_owned_startup_material: bool = False,
) -> dict[str, Any]:
    """Preserve the user's initial prompt as the first PM-bound physical packet."""

    resolved_body_visibility = body_visibility or USER_INTAKE_BODY_VISIBILITY
    metadata = {
        "source": source,
        "controller_bootstrap_scope": startup_options or {},
        "controller_may_bootstrap_roles_heartbeat_and_ui": True,
        "controller_may_read_user_intake_body": resolved_body_visibility == USER_INTAKE_BODY_VISIBILITY,
        "controller_must_not_make_pm_route_or_gate_decision": True,
        "pm_must_request_startup_reviewer_gate_before_opening_start_gate": True,
        "startup_gate_status": "not_open_until_pm_decision_after_reviewer_audit",
        "router_owned_startup_material": router_owned_startup_material,
    }
    if startup_intake_ref is not None:
        metadata.update(
            {
                "startup_intake_ref": startup_intake_ref,
                "controller_may_read_user_intake_body": False,
                "reviewer_live_review_source": "startup_intake_record",
                "reviewer_must_not_use_chat_history": True,
            }
        )
    return create_packet(
        project_root,
        run_id=run_id,
        packet_id=packet_id,
        from_role="user",
        to_role="project_manager",
        node_id=node_id,
        body_text=body_text,
        packet_type="user_intake",
        body_visibility=resolved_body_visibility,
        metadata=metadata,
        next_holder="project_manager",
        return_to="router" if router_owned_startup_material else "controller",
        initial_holder="router" if router_owned_startup_material else "controller",
        initial_ledger_status="router-held-startup-material" if router_owned_startup_material else "packet-with-controller",
        initial_status_packet_status="router-held-startup-material" if router_owned_startup_material else "envelope-created",
        router_owned_startup_material=router_owned_startup_material,
    )

def build_controller_handoff(envelope: dict[str, Any], *, envelope_path: str) -> dict[str, Any]:
    body_keys = {"body_content", "body_text", "packet_body", "result_body"}
    leaked_keys = sorted(body_keys & set(envelope))
    if leaked_keys:
        raise PacketRuntimeError(f"packet envelope contains forbidden body content keys: {leaked_keys!r}")
    is_result_envelope = (
        envelope.get("schema_version") == RESULT_ENVELOPE_SCHEMA
        or ("completed_by_role" in envelope and "result_body_hash" in envelope)
    )
    if is_result_envelope:
        from_role = envelope.get("completed_by_role")
        to_role = envelope.get("next_recipient")
        body_path = envelope["result_body_path"]
        body_hash = envelope["result_body_hash"]
        envelope_kind = "result_envelope"
        forbidden_actions = envelope.get("controller_forbidden_actions", RESULT_CONTROLLER_FORBIDDEN_ACTIONS)
        allowed_actions = envelope.get("controller_allowed_actions", RESULT_CONTROLLER_ALLOWED_ACTIONS)
    else:
        from_role = envelope["from_role"]
        to_role = envelope["to_role"]
        body_path = envelope["body_path"]
        body_hash = envelope["body_hash"]
        envelope_kind = "packet_envelope"
        forbidden_actions = envelope["controller_forbidden_actions"]
        allowed_actions = envelope["controller_allowed_actions"]
    output_contract = envelope.get("output_contract") if isinstance(envelope.get("output_contract"), dict) else None
    mutual_reminder = mutual_role_reminder(
        source_role=str(from_role),
        target_role=str(to_role),
        envelope_kind=envelope_kind,
    )
    return {
        "schema_version": CONTROLLER_HANDOFF_SCHEMA,
        "controller_visibility": "result_envelope_only" if is_result_envelope else "packet_envelope_only",
        "envelope_kind": envelope_kind,
        "envelope_path": envelope_path,
        "packet_envelope_path": envelope_path if not is_result_envelope else envelope.get("source_packet_envelope_path", ""),
        "result_envelope_path": envelope_path if is_result_envelope else "",
        "packet_id": envelope["packet_id"],
        "packet_type": envelope.get("packet_type", "work_packet"),
        "from_role": from_role,
        "to_role": to_role,
        "node_id": envelope["node_id"],
        "is_current_node": envelope["is_current_node"],
        "body_path": body_path,
        "body_hash": body_hash,
        "body_visibility": envelope.get("body_visibility", SEALED_BODY_VISIBILITY),
        "source_output_contract_id": envelope.get("source_output_contract_id") or output_contract_id(output_contract),
        "output_contract": output_contract,
        "controller_relay_signature_required": True,
        "recipient_must_verify_controller_relay_before_body_open": True,
        "return_to": envelope.get("return_to", "controller"),
        "next_holder": envelope.get("next_holder", to_role),
        "controller_allowed_actions": allowed_actions,
        "controller_forbidden_actions": forbidden_actions,
        "instruction": "Relay this envelope only. Do not read, summarize, execute, edit, or quote the sealed body.",
        "mutual_role_reminder": mutual_reminder,
        "controller_identity": mutual_reminder["controller_reminder"],
        "recipient_identity_required": mutual_reminder["recipient_reminder"],
        "sender_identity_required": mutual_reminder["sender_reminder"],
        "reply_continuation_reminder": mutual_reminder["reply_continuation_reminder"],
        "direct_controller_text_authoritative": False,
        "recipient_role_reminder": f"This mail is for `{to_role}` only.",
        "mail_only_reminder": "The recipient must answer through a file-backed packet/result/report body and submit the runtime envelope to Router; Controller sees only Router-authorized metadata.",
        "chat_response_body_allowed": False,
    }

def controller_handoff_text(handoff: dict[str, Any]) -> str:
    return json.dumps(handoff, indent=2, sort_keys=True)

def read_packet_body_for_role(project_root: Path, envelope: dict[str, Any], *, role: str) -> str:
    envelope.update(normalize_envelope_aliases(envelope))
    verify_controller_relay(envelope, recipient_role=role)
    open_source = "controller_relay"
    if role != envelope.get("to_role"):
        raise PacketRuntimeError(f"packet body may only be read by to_role={envelope.get('to_role')!r}, not {role!r}")
    output_contract = envelope.get("output_contract")
    if isinstance(output_contract, dict) and output_contract.get("recipient_role") != role:
        raise PacketRuntimeError("output_contract.recipient_role does not match packet reader role")
    body_path = resolve_project_path(project_root, envelope["body_path"])
    if sha256_file(body_path) != envelope["body_hash"]:
        raise PacketRuntimeError("packet body hash mismatch")
    body_text = body_path.read_text(encoding="utf-8")
    validate_packet_identity_boundary(body_text, role)
    work_authority = packet_open_work_authority(
        role=role,
        packet_type=str(envelope.get("packet_type", "work_packet")),
        source=open_source,
    )
    opened = {
        "role": role,
        "opened_at": utc_now(),
        "controller_relay_verified": True,
        "body_hash_verified": True,
        "work_authority": work_authority,
    }
    envelope["body_opened_by_role"] = opened
    envelope["packet_open_work_authority"] = work_authority
    paths = packet_paths_from_envelope(project_root, envelope)
    write_json_atomic(paths["packet_envelope"], envelope)
    _update_packet_record(
        project_root,
        paths["packet_ledger"],
        envelope["packet_id"],
        {
            "packet_body_opened_by_role": role,
            "packet_body_opened_after_controller_relay_check": True,
            "packet_body_open_record": opened,
            "packet_open_authorizes_work": True,
            "packet_open_work_authority": work_authority,
            "packet_open_required_exit": work_authority["required_exit"],
            "active_packet_status": "packet-body-opened-by-recipient",
            "active_packet_holder": role,
        },
    )
    write_controller_status_packet(
        project_root,
        envelope,
        holder=role,
        status="working",
        message=f"Packet {envelope['packet_id']} opened by {role}.",
        progress=1,
        progress_updated_by_role=role,
        work_authority=work_authority,
    )
    return body_text
