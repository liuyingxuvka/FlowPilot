"""Packet runtime audit helpers for FlowPilot packet runtime."""

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





















def _load_ledger(project_root: Path, run_id: str | None = None) -> tuple[dict[str, Any], Path, str]:
    resolved_run_id, run_root = active_run_root(project_root, run_id)
    ledger_path = run_root / "packet_ledger.json"
    if not ledger_path.exists():
        raise PacketRuntimeError(f"packet ledger does not exist: {ledger_path}")
    return read_json(ledger_path), ledger_path, resolved_run_id

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
