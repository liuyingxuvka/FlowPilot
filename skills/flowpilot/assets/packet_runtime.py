"""Public facade for physical FlowPilot packet envelope/body handoffs."""

from __future__ import annotations

from packet_runtime_active_holder import (
    _load_active_holder_lease,
    _require_concrete_agent_id,
    active_holder_ack,
    active_holder_progress,
    active_holder_submit_existing_result,
    active_holder_submit_result,
    issue_active_holder_lease,
)
from packet_runtime_audit import _load_ledger, _replacement_exists, audit_packet_chain
from packet_runtime_cli import _read_text_arg, main, parse_args
from packet_runtime_creation import (
    build_controller_handoff,
    controller_handoff_text,
    create_packet,
    create_user_intake_packet,
    read_packet_body_for_role,
    router_release_startup_user_intake,
)
from packet_runtime_ledger import _update_packet_record, packet_ledger_record_for_envelope
from packet_runtime_contracts import (
    contract_self_check_metadata,
    default_output_contract,
    ensure_packet_identity_boundary,
    ensure_packet_output_contract_section,
    ensure_result_identity_boundary,
    mutual_role_reminder,
    normalize_output_contract,
    output_contract_id,
    output_contract_section,
    packet_identity_boundary,
    packet_open_work_authority,
    result_identity_boundary,
    validate_packet_identity_boundary,
    validate_result_identity_boundary,
)
from packet_runtime_progress import (
    _validate_progress_message,
    _validate_progress_value,
    update_controller_progress,
    write_controller_status_packet,
)
from packet_runtime_results import read_result_body_for_role, write_result
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
    controller_relay_envelope,
    mark_controller_contamination,
    validate_packet_ready_for_direct_relay,
    validate_result_ready_for_recipient_relay,
    validate_result_ready_for_reviewer_relay,
    verify_controller_relay,
    verify_packet_open_receipt,
    verify_router_startup_release,
)
from packet_runtime_reviewer import validate_for_reviewer
from packet_runtime_sessions import (
    _load_role_packet_session,
    begin_result_review_session,
    begin_role_packet_session,
    complete_role_packet_session,
    run_role_packet_session,
)
from packet_runtime_schema import *  # noqa: F403

__all__ = [
    "PacketRuntimeError",
    "PACKET_IDENTITY_MARKER",
    "RESULT_IDENTITY_MARKER",
    "ROLE_PACKET_SESSION_SCHEMA",
    "RESULT_REVIEW_SESSION_SCHEMA",
    "CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA",
    "router_release_startup_user_intake",
    "write_controller_status_packet",
    "update_controller_progress",
    "create_packet",
    "default_output_contract",
    "create_user_intake_packet",
    "build_controller_handoff",
    "controller_handoff_text",
    "read_packet_body_for_role",
    "load_envelope",
    "write_result",
    "read_result_body_for_role",
    "audit_packet_chain",
    "controller_relay_envelope",
    "validate_packet_ready_for_direct_relay",
    "validate_result_ready_for_recipient_relay",
    "validate_result_ready_for_reviewer_relay",
    "verify_controller_relay",
    "verify_packet_open_receipt",
    "verify_router_startup_release",
    "parse_args",
    "main",
    "validate_for_reviewer",
    "begin_role_packet_session",
    "complete_role_packet_session",
    "run_role_packet_session",
    "begin_result_review_session",
    "issue_active_holder_lease",
    "active_holder_ack",
    "active_holder_progress",
    "active_holder_submit_result",
    "active_holder_submit_existing_result",
    "_update_packet_record",
    "packet_ledger_record_for_envelope",
]


if __name__ == "__main__":
    raise SystemExit(main())
