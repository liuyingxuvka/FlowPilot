"""Controller handoff and packet body-open helpers for FlowPilot packet runtime."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

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
    _upsert_packet_record,
    packet_ledger_record_for_envelope,
)
from packet_runtime_paths import (
    active_run_root,
    load_envelope,
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
    mark_controller_contamination,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_reviewer_relay,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_schema import (
    ACTIVE_HOLDER_EVENT_SCHEMA,
    ACTIVE_HOLDER_LEASE_SCHEMA,
    CHAIN_AUDIT_SCHEMA,
    CONTROLLER_HANDOFF_SCHEMA,
    CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA,
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
        "return_to": envelope.get("return_to", "controller"),
        "next_holder": envelope.get("next_holder", to_role),
        "controller_allowed_actions": allowed_actions,
        "controller_forbidden_actions": forbidden_actions,
        "instruction": "Deliver this envelope metadata only. Do not read, summarize, execute, edit, or quote the sealed body.",
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
    if role != envelope.get("to_role"):
        raise PacketRuntimeError(f"packet body may only be read by to_role={envelope.get('to_role')!r}, not {role!r}")
    open_source = "current_assignment"
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
