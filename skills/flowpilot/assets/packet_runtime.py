"""Create and validate physical FlowPilot packet envelope/body handoffs."""

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
    }
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
    )


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


def write_result(
    project_root: Path,
    *,
    packet_envelope: dict[str, Any],
    completed_by_role: str,
    completed_by_agent_id: str,
    result_body_text: str,
    next_recipient: str,
    strict_role: bool = True,
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
        },
    }
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




















def _load_ledger(project_root: Path, run_id: str | None = None) -> tuple[dict[str, Any], Path, str]:
    resolved_run_id, run_root = active_run_root(project_root, run_id)
    ledger_path = run_root / "packet_ledger.json"
    if not ledger_path.exists():
        raise PacketRuntimeError(f"packet ledger does not exist: {ledger_path}")
    return read_json(ledger_path), ledger_path, resolved_run_id


def audit_barrier_bundles(
    project_root: Path,
    *,
    run_id: str | None = None,
    node_id: str | None = None,
    bundle_id: str | None = None,
) -> dict[str, Any]:
    try:
        ledger, ledger_path, resolved_run_id = _load_ledger(project_root, run_id)
    except PacketRuntimeError:
        return {
            "schema_version": "flowpilot.barrier_bundle_audit.v1",
            "run_id": run_id,
            "node_id": node_id,
            "bundle_id": bundle_id,
            "ledger_missing": True,
            "checked_bundle_count": 0,
            "blockers": [],
            "passed": True,
            "created_at": utc_now(),
        }

    records = [item for item in ledger.get("packets", []) if isinstance(item, dict)]
    packet_node = {
        str(record.get("packet_id")): record.get("node_id")
        for record in records
        if record.get("packet_id")
    }
    bundles: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_bundle(raw: Any) -> None:
        if not isinstance(raw, dict):
            return
        key = str(raw.get("bundle_id") or f"{raw.get('barrier_id', 'unknown')}:{len(seen)}")
        if key in seen:
            return
        seen.add(key)
        bundles.append(raw)

    for raw_bundle in ledger.get("barrier_bundles", []):
        add_bundle(raw_bundle)
    for record in records:
        add_bundle(record.get("barrier_bundle"))

    scoped_bundles: list[dict[str, Any]] = []
    for raw_bundle in bundles:
        if bundle_id and raw_bundle.get("bundle_id") != bundle_id:
            continue
        if node_id:
            bundle_node = raw_bundle.get("node_id")
            member_nodes = {
                packet_node.get(str(packet_id))
                for packet_id in raw_bundle.get("member_packet_ids", [])
            }
            if bundle_node != node_id and node_id not in member_nodes:
                continue
        scoped_bundles.append(raw_bundle)

    blockers: list[dict[str, Any]] = []
    cumulative_obligations: list[str] = []
    for raw_bundle in scoped_bundles:
        report = barrier_bundle.validate_barrier_bundle(
            raw_bundle,
            cumulative_obligations=cumulative_obligations,
        )
        if report["ok"]:
            cumulative_obligations.extend(barrier_bundle.passed_obligation_ids(raw_bundle))
            continue
        blockers.append(
            {
                "bundle_id": raw_bundle.get("bundle_id"),
                "barrier_id": raw_bundle.get("barrier_id"),
                "node_id": raw_bundle.get("node_id"),
                "member_packet_ids": list(raw_bundle.get("member_packet_ids") or []),
                "code": "barrier_bundle_invalid",
                "failures": report["failures"],
                "missing_obligations": report["missing_obligations"],
                "missing_role_slices": report["missing_role_slices"],
            }
        )

    audit = {
        "schema_version": "flowpilot.barrier_bundle_audit.v1",
        "run_id": resolved_run_id,
        "node_id": node_id,
        "bundle_id": bundle_id,
        "ledger_path": project_relative(project_root, ledger_path),
        "checked_bundle_count": len(scoped_bundles),
        "blockers": blockers,
        "passed": not blockers,
        "created_at": utc_now(),
    }
    audit_path = ledger_path.with_name("barrier_bundle_audit.json")
    write_json_atomic(audit_path, audit)
    ledger["latest_barrier_bundle_audit_path"] = project_relative(project_root, audit_path)
    ledger["latest_barrier_bundle_audit_passed"] = audit["passed"]
    ledger["latest_barrier_bundle_audit_at"] = audit["created_at"]
    write_json_atomic(ledger_path, ledger)
    return audit


def _replacement_exists(records: list[dict[str, Any]], packet_id: str) -> bool:
    for record in records:
        if record.get("replacement_for") == packet_id:
            return True
        supersedes = record.get("supersedes")
        if isinstance(supersedes, list) and packet_id in supersedes:
            return True
        if record.get("packet_envelope", {}).get("replacement_for") == packet_id:
            return True
    return False


def audit_packet_chain(project_root: Path, *, run_id: str | None = None, node_id: str | None = None) -> dict[str, Any]:
    ledger, ledger_path, resolved_run_id = _load_ledger(project_root, run_id)
    raw_records = ledger.get("packets") or []
    if not isinstance(raw_records, list):
        raise PacketRuntimeError("packet_ledger.packets must be a list")
    records = [item for item in raw_records if isinstance(item, dict)]
    scoped_records = [item for item in records if node_id is None or item.get("node_id") == node_id]
    blockers: list[dict[str, Any]] = []

    def add_blocker(record: dict[str, Any], code: str, detail: str) -> None:
        blockers.append(
            {
                "packet_id": record.get("packet_id"),
                "node_id": record.get("node_id"),
                "code": code,
                "detail": detail,
            }
        )

    for record in scoped_records:
        packet_id = str(record.get("packet_id") or "")
        replaced = bool(record.get("replaced_by")) or _replacement_exists(records, packet_id)
        contaminated = bool(record.get("controller_return_to_sender") or record.get("controller_packet_body_access_detected"))
        if contaminated:
            if not replaced:
                add_blocker(record, "contaminated_packet_without_replacement", "controller-contaminated mail needs a new sender-issued replacement packet")
            continue
        if record.get("private_role_to_role_delivery_detected"):
            add_blocker(record, "private_delivery_detected", "formal packet/result did not route through controller")
        if not record.get("packet_controller_relay"):
            add_blocker(record, "missing_packet_controller_relay", "packet envelope was not signed and relayed by controller")
        if not record.get("packet_body_opened_by_role"):
            add_blocker(record, "packet_body_unopened_by_recipient", "target role did not record a post-relay packet body open")

        result_exists = bool(record.get("result_body_hash")) or bool(record.get("result_envelope", {}).get("completed_by_role"))
        result_path = record.get("result_envelope_path")
        if result_path:
            result_exists = result_exists or resolve_project_path(project_root, str(result_path)).exists()
        if result_exists:
            if not record.get("result_controller_relay"):
                add_blocker(record, "missing_result_controller_relay", "result envelope was not signed and relayed by controller")
            if not record.get("result_body_opened_by_role"):
                add_blocker(record, "result_body_unopened_by_recipient", "reviewer or PM did not record a post-relay result body open")

    audit = {
        "schema_version": CHAIN_AUDIT_SCHEMA,
        "run_id": resolved_run_id,
        "node_id": node_id,
        "ledger_path": project_relative(project_root, ledger_path),
        "checked_packet_count": len(scoped_records),
        "all_formal_mail_must_route_through_controller": True,
        "controller_no_body_read_signature_required": True,
        "recipient_pre_open_relay_check_required": True,
        "contaminated_or_private_mail_requires_sender_reissue": True,
        "unopened_or_missing_mail_sent_to_pm": bool(blockers),
        "pm_decision_required": bool(blockers),
        "pm_options": ["restart_node", "create_repair_node", "request_sender_reissue"],
        "blockers": blockers,
        "passed": not blockers,
        "reviewer_instruction": "If blockers exist, send this unopened/missing-mail audit to PM; PM chooses restart node, repair node, or sender reissue.",
        "created_at": utc_now(),
    }
    audit_path = ledger_path.with_name("packet_chain_audit.json")
    write_json_atomic(audit_path, audit)
    ledger["latest_packet_chain_audit_path"] = project_relative(project_root, audit_path)
    ledger["latest_packet_chain_audit_passed"] = audit["passed"]
    ledger["latest_packet_chain_audit_at"] = audit["created_at"]
    write_json_atomic(ledger_path, ledger)
    return audit


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create and validate physical FlowPilot packet envelope/body files.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue = subparsers.add_parser("issue", help="Write packet_envelope.json and packet_body.md")
    issue.add_argument("--run-id", default="")
    issue.add_argument("--packet-id", required=True)
    issue.add_argument("--from-role", required=True)
    issue.add_argument("--to-role", required=True)
    issue.add_argument("--node-id", required=True)
    issue.add_argument("--body-text", default="")
    issue.add_argument("--body-file", default="")
    issue.add_argument("--return-to", default="controller")
    issue.add_argument("--next-holder", default="")
    issue.add_argument("--replacement-for", default="")

    intake = subparsers.add_parser("user-intake", help="Write the first user prompt packet for PM")
    intake.add_argument("--run-id", default="")
    intake.add_argument("--packet-id", required=True)
    intake.add_argument("--node-id", required=True)
    intake.add_argument("--body-text", default="")
    intake.add_argument("--body-file", default="")
    intake.add_argument("--startup-options-json", default="")
    intake.add_argument("--background-agents-authorized", action="store_true")
    intake.add_argument("--heartbeat-requested", action="store_true")
    intake.add_argument("--display-surface", default="")

    handoff = subparsers.add_parser("handoff", help="Print controller-visible envelope handoff only")
    handoff.add_argument("--envelope-path", required=True)

    relay = subparsers.add_parser("relay", help="Controller signs and relays an envelope without opening body")
    relay.add_argument("--envelope-path", required=True)
    relay.add_argument("--controller-agent-id", default="controller")
    relay.add_argument("--received-from-role", default="")
    relay.add_argument("--relayed-to-role", default="")
    relay.add_argument("--holder-before", default="")
    relay.add_argument("--holder-after", default="")
    relay.add_argument("--body-was-read-by-controller", action="store_true")
    relay.add_argument("--body-was-executed-by-controller", action="store_true")
    relay.add_argument("--private-role-to-role-delivery-detected", action="store_true")

    read_packet = subparsers.add_parser("read-packet", help="Target role verifies relay and opens packet body")
    read_packet.add_argument("--envelope-path", required=True)
    read_packet.add_argument("--role", required=True)

    open_packet_session = subparsers.add_parser(
        "open-packet-session",
        help="Target role opens a packet through the runtime session entrypoint",
    )
    open_packet_session.add_argument("--envelope-path", required=True)
    open_packet_session.add_argument("--role", required=True)
    open_packet_session.add_argument("--agent-id", required=True)

    complete_packet_session = subparsers.add_parser(
        "complete-packet-session",
        help="Complete a previously opened role packet session and generate the result envelope",
    )
    complete_packet_session.add_argument("--session-path", required=True)
    complete_packet_session.add_argument("--result-body-text", default="")
    complete_packet_session.add_argument("--result-body-file", default="")
    complete_packet_session.add_argument("--next-recipient", required=True)

    run_packet_session = subparsers.add_parser(
        "run-packet-session",
        help="Open a packet session and complete it in one runtime call",
    )
    run_packet_session.add_argument("--envelope-path", required=True)
    run_packet_session.add_argument("--role", required=True)
    run_packet_session.add_argument("--agent-id", required=True)
    run_packet_session.add_argument("--result-body-text", default="")
    run_packet_session.add_argument("--result-body-file", default="")
    run_packet_session.add_argument("--next-recipient", required=True)

    progress = subparsers.add_parser("progress", help="Target role updates Controller-visible packet progress")
    progress.add_argument("--envelope-path", required=True)
    progress.add_argument("--role", required=True)
    progress.add_argument("--agent-id", required=True)
    progress.add_argument("--progress", required=True, type=int)
    progress.add_argument("--message", required=True)

    issue_active = subparsers.add_parser(
        "issue-active-holder-lease",
        help="Router issues a scoped fast-lane lease to the current packet holder",
    )
    issue_active.add_argument("--envelope-path", required=True)
    issue_active.add_argument("--holder-role", required=True)
    issue_active.add_argument("--holder-agent-id", required=True)
    issue_active.add_argument("--route-version", required=True, type=int)
    issue_active.add_argument("--frontier-version", required=True, type=int)
    issue_active.add_argument("--allowed-action", action="append", default=[])

    active_ack = subparsers.add_parser("active-holder-ack", help="Current holder acknowledges a fast-lane packet lease")
    active_ack.add_argument("--lease-path", required=True)
    active_ack.add_argument("--role", required=True)
    active_ack.add_argument("--agent-id", required=True)
    active_ack.add_argument("--route-version", type=int, default=None)
    active_ack.add_argument("--frontier-version", type=int, default=None)

    active_progress = subparsers.add_parser(
        "active-holder-progress",
        help="Current holder writes controller-safe fast-lane packet progress",
    )
    active_progress.add_argument("--lease-path", required=True)
    active_progress.add_argument("--role", required=True)
    active_progress.add_argument("--agent-id", required=True)
    active_progress.add_argument("--progress", required=True, type=int)
    active_progress.add_argument("--message", required=True)
    active_progress.add_argument("--route-version", type=int, default=None)
    active_progress.add_argument("--frontier-version", type=int, default=None)

    active_submit = subparsers.add_parser(
        "active-holder-submit-result",
        help="Current holder submits a result through the fast lane and writes a Controller next-action notice",
    )
    active_submit.add_argument("--lease-path", required=True)
    active_submit.add_argument("--role", required=True)
    active_submit.add_argument("--agent-id", required=True)
    active_submit.add_argument("--result-body-text", default="")
    active_submit.add_argument("--result-body-file", default="")
    active_submit.add_argument("--next-recipient", required=True)
    active_submit.add_argument("--route-version", type=int, default=None)
    active_submit.add_argument("--frontier-version", type=int, default=None)

    active_submit_existing = subparsers.add_parser(
        "active-holder-submit-existing-result",
        help="Current holder submits an existing result envelope through the fast lane",
    )
    active_submit_existing.add_argument("--lease-path", required=True)
    active_submit_existing.add_argument("--role", required=True)
    active_submit_existing.add_argument("--agent-id", required=True)
    active_submit_existing.add_argument("--result-envelope-path", required=True)
    active_submit_existing.add_argument("--route-version", type=int, default=None)
    active_submit_existing.add_argument("--frontier-version", type=int, default=None)

    complete = subparsers.add_parser("complete", help="Write result_envelope.json and result_body.md")
    complete.add_argument("--envelope-path", required=True)
    complete.add_argument("--completed-by-role", required=True)
    complete.add_argument("--completed-by-agent-id", required=True)
    complete.add_argument("--result-body-text", default="")
    complete.add_argument("--result-body-file", default="")
    complete.add_argument("--next-recipient", required=True)
    complete.add_argument("--allow-wrong-role-for-audit", action="store_true")

    review = subparsers.add_parser("review", help="Validate packet/result envelope, hashes, and role origin")
    review.add_argument("--envelope-path", required=True)
    review.add_argument("--result-envelope-path", required=True)
    review.add_argument("--agent-role-map-json", default="")

    read_result = subparsers.add_parser("read-result", help="Reviewer/PM verifies relay and opens result body")
    read_result.add_argument("--result-envelope-path", required=True)
    read_result.add_argument("--role", required=True)

    open_result_session = subparsers.add_parser(
        "open-result-session",
        help="Reviewer/PM opens a result body through the runtime session entrypoint",
    )
    open_result_session.add_argument("--result-envelope-path", required=True)
    open_result_session.add_argument("--role", required=True)
    open_result_session.add_argument("--agent-id", required=True)

    audit_chain = subparsers.add_parser("audit-chain", help="Reviewer audits packet mail chain for a run or node")
    audit_chain.add_argument("--run-id", default="")
    audit_chain.add_argument("--node-id", default="")

    return parser.parse_args(argv)


def _read_text_arg(text_value: str, file_value: str) -> str:
    if file_value:
        return Path(file_value).read_text(encoding="utf-8")
    return text_value


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    if args.command == "issue":
        envelope = create_packet(
            root,
            run_id=args.run_id or None,
            packet_id=args.packet_id,
            from_role=args.from_role,
            to_role=args.to_role,
            node_id=args.node_id,
            body_text=_read_text_arg(args.body_text, args.body_file),
            return_to=args.return_to,
            next_holder=args.next_holder or None,
            replacement_for=args.replacement_for or None,
        )
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0
    if args.command == "user-intake":
        startup_options = json.loads(args.startup_options_json) if args.startup_options_json else {}
        startup_options.update(
            {
                "background_agents_authorized": bool(args.background_agents_authorized),
                "heartbeat_requested": bool(args.heartbeat_requested),
                "display_surface": args.display_surface or "unspecified",
            }
        )
        envelope = create_user_intake_packet(
            root,
            run_id=args.run_id or None,
            packet_id=args.packet_id,
            node_id=args.node_id,
            body_text=_read_text_arg(args.body_text, args.body_file),
            startup_options=startup_options,
        )
        print(json.dumps(envelope, indent=2, sort_keys=True))
        return 0
    if args.command == "handoff":
        envelope = load_envelope(root, args.envelope_path)
        handoff = build_controller_handoff(envelope, envelope_path=args.envelope_path)
        print(controller_handoff_text(handoff))
        return 0
    if args.command == "relay":
        envelope = load_envelope(root, args.envelope_path)
        relayed = controller_relay_envelope(
            root,
            envelope=envelope,
            envelope_path=args.envelope_path,
            controller_agent_id=args.controller_agent_id,
            received_from_role=args.received_from_role or None,
            relayed_to_role=args.relayed_to_role or None,
            holder_before=args.holder_before or None,
            holder_after=args.holder_after or None,
            body_was_read_by_controller=bool(args.body_was_read_by_controller),
            body_was_executed_by_controller=bool(args.body_was_executed_by_controller),
            private_role_to_role_delivery_detected=bool(args.private_role_to_role_delivery_detected),
        )
        print(json.dumps(relayed, indent=2, sort_keys=True))
        return 0
    if args.command == "read-packet":
        envelope = load_envelope(root, args.envelope_path)
        print(read_packet_body_for_role(root, envelope, role=args.role))
        return 0
    if args.command == "open-packet-session":
        session = begin_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
        print(json.dumps(session, indent=2, sort_keys=True))
        return 0
    if args.command == "complete-packet-session":
        result = complete_role_packet_session(
            root,
            session_path=args.session_path,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "run-packet-session":
        output = run_role_packet_session(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
        )
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    if args.command == "progress":
        status = update_controller_progress(
            root,
            envelope_path=args.envelope_path,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
        )
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    if args.command == "issue-active-holder-lease":
        envelope = load_envelope(root, args.envelope_path)
        lease = issue_active_holder_lease(
            root,
            packet_envelope=envelope,
            holder_role=args.holder_role,
            holder_agent_id=args.holder_agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
            allowed_actions=args.allowed_action or None,
        )
        print(json.dumps(lease, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-ack":
        event = active_holder_ack(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(event, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-progress":
        status = active_holder_progress(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            progress=args.progress,
            message=args.message,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0
    if args.command == "active-holder-submit-result":
        submission = active_holder_submit_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(submission, indent=2, sort_keys=True))
        return 0 if submission["passed"] else 2
    if args.command == "active-holder-submit-existing-result":
        submission = active_holder_submit_existing_result(
            root,
            lease_path=args.lease_path,
            role=args.role,
            agent_id=args.agent_id,
            result_envelope_path=args.result_envelope_path,
            route_version=args.route_version,
            frontier_version=args.frontier_version,
        )
        print(json.dumps(submission, indent=2, sort_keys=True))
        return 0 if submission["passed"] else 2
    if args.command == "complete":
        envelope = load_envelope(root, args.envelope_path)
        result = write_result(
            root,
            packet_envelope=envelope,
            completed_by_role=args.completed_by_role,
            completed_by_agent_id=args.completed_by_agent_id,
            result_body_text=_read_text_arg(args.result_body_text, args.result_body_file),
            next_recipient=args.next_recipient,
            strict_role=not args.allow_wrong_role_for_audit,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if args.command == "review":
        envelope = load_envelope(root, args.envelope_path)
        result = load_envelope(root, args.result_envelope_path)
        agent_role_map = json.loads(args.agent_role_map_json) if args.agent_role_map_json else None
        audit = validate_for_reviewer(root, packet_envelope=envelope, result_envelope=result, agent_role_map=agent_role_map)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["passed"] else 2
    if args.command == "read-result":
        result = load_envelope(root, args.result_envelope_path)
        print(read_result_body_for_role(root, result, role=args.role))
        return 0
    if args.command == "open-result-session":
        session = begin_result_review_session(
            root,
            result_envelope_path=args.result_envelope_path,
            role=args.role,
            agent_id=args.agent_id,
        )
        print(json.dumps(session, indent=2, sort_keys=True))
        return 0
    if args.command == "audit-chain":
        audit = audit_packet_chain(root, run_id=args.run_id or None, node_id=args.node_id or None)
        print(json.dumps(audit, indent=2, sort_keys=True))
        return 0 if audit["passed"] else 2
    raise PacketRuntimeError(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
