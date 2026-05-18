"""Invariant definitions for the packet control-plane FlowGuard model."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult
from packet_control_plane_model_state import State

def no_advance_from_controller_artifact(state: State, trace) -> InvariantResult:
    del trace
    bad = set(state.controller_artifacts) & set(state.advances)
    if bad:
        return InvariantResult.fail(f"controller-origin evidence advanced: {sorted(bad)!r}")
    return InvariantResult.pass_()

def advance_requires_review_pass(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.advances) - set(state.review_passes)
    if missing:
        return InvariantResult.fail(f"advance without review pass: {sorted(missing)!r}")
    return InvariantResult.pass_()

def review_pass_requires_role_origin_audit(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.review_passes) - set(state.role_origin_audits)
    if missing:
        return InvariantResult.fail(f"review pass without role-origin audit: {sorted(missing)!r}")
    return InvariantResult.pass_()

def review_pass_requires_mail_chain_audit(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.review_passes) - set(state.mail_chain_audits)
    if missing:
        return InvariantResult.fail(f"review pass without packet mail-chain audit: {sorted(missing)!r}")
    return InvariantResult.pass_()

def recipient_body_open_requires_controller_relay_signature(state: State, trace) -> InvariantResult:
    del trace
    packet_missing = set(state.packet_body_open_events) - set(state.controller_relay_signatures)
    if packet_missing:
        return InvariantResult.fail(f"packet body opened without controller relay signature: {sorted(packet_missing)!r}")
    result_missing = set(state.result_body_open_events) - set(state.result_controller_relay_signatures)
    if result_missing:
        return InvariantResult.fail(f"result body opened without controller relay signature: {sorted(result_missing)!r}")
    return InvariantResult.pass_()

def missing_or_unopened_mail_requires_pm_restart_or_repair(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.unopened_packet_blocks) | set(state.unopened_result_blocks) | set(state.private_delivery_blocks)
    missing = blocked - set(state.pm_repair_requirements)
    if missing:
        return InvariantResult.fail(f"mail-chain blocker lacked PM restart/repair requirement: {sorted(missing)!r}")
    return InvariantResult.pass_()

def invalid_origin_block_requires_warning(state: State, trace) -> InvariantResult:
    del trace
    invalid = (set(state.review_blocks) & set(state.controller_artifacts)) | set(state.wrong_role_completion_blocks)
    missing_warning = invalid - set(state.controller_warnings)
    if missing_warning:
        return InvariantResult.fail(
            f"invalid role-origin block without controller warning: {sorted(missing_warning)!r}"
        )
    missing_repair = invalid - set(state.pm_repair_requirements)
    if missing_repair:
        return InvariantResult.fail(
            f"invalid role-origin block without PM repair requirement: {sorted(missing_repair)!r}"
        )
    return InvariantResult.pass_()

def controller_body_boundary_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.controller_body_access_blocks) | set(state.controller_body_execution_blocks)
    unsafe = blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if unsafe:
        return InvariantResult.fail(f"controller body boundary violation advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def controller_handoff_body_leak_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.controller_handoff_body_leak_blocks)
    unsafe = blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if unsafe:
        return InvariantResult.fail(f"controller handoff body leak advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def missing_mutual_role_reminder_never_advances(state: State, trace) -> InvariantResult:
    del trace
    packet_blocked = set(state.mutual_role_reminder_blocks)
    packet_unsafe = packet_blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if packet_unsafe:
        return InvariantResult.fail(f"missing packet mutual-role reminder advanced: {sorted(packet_unsafe)!r}")

    result_blocked = set(state.result_mutual_role_reminder_blocks)
    result_unsafe = result_blocked & (
        set(state.result_body_open_events)
        | set(state.review_passes)
        | set(state.advances)
    )
    if result_unsafe:
        return InvariantResult.fail(f"missing result mutual-role reminder advanced: {sorted(result_unsafe)!r}")
    return InvariantResult.pass_()

def controller_relay_requires_physical_files_and_envelope_only_handoff(state: State, trace) -> InvariantResult:
    del trace
    relayed = set(state.controller_envelope_reads)
    missing_files = relayed - set(state.physical_packet_files)
    if missing_files:
        return InvariantResult.fail(f"controller relayed without physical packet files: {sorted(missing_files)!r}")
    missing_handoff = relayed - set(state.controller_handoff_envelope_only)
    if missing_handoff:
        return InvariantResult.fail(f"controller relayed without envelope-only handoff: {sorted(missing_handoff)!r}")
    missing_mutual_reminder = relayed - set(state.controller_handoff_mutual_role_reminders)
    if missing_mutual_reminder:
        return InvariantResult.fail(
            f"controller relayed without visible mutual-role reminder: {sorted(missing_mutual_reminder)!r}"
        )
    result_relayed = set(state.result_controller_relay_signatures)
    missing_result_mutual_reminder = result_relayed - set(state.result_mutual_role_reminders)
    if missing_result_mutual_reminder:
        return InvariantResult.fail(
            f"controller relayed result without visible mutual-role reminder: {sorted(missing_result_mutual_reminder)!r}"
        )
    return InvariantResult.pass_()

def holder_change_requires_user_status_update(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.holder_changes) - set(state.holder_status_updates)
    if missing:
        return InvariantResult.fail(f"holder changed without user status update: {sorted(missing)!r}")
    return InvariantResult.pass_()

def cockpit_missing_major_node_requires_chat_mermaid(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.cockpit_missing_major_nodes) - set(state.chat_mermaid_displays)
    if missing:
        return InvariantResult.fail(f"major node entered without chat Mermaid when Cockpit missing: {sorted(missing)!r}")
    return InvariantResult.pass_()

def dispatch_requires_packet_envelope_and_hash_checks(state: State, trace) -> InvariantResult:
    del trace
    missing_envelope = set(state.dispatches) - set(state.packet_envelope_checks)
    if missing_envelope:
        return InvariantResult.fail(f"dispatch without packet envelope check: {sorted(missing_envelope)!r}")
    missing_hash = set(state.dispatches) - set(state.packet_body_hash_checks)
    if missing_hash:
        return InvariantResult.fail(f"dispatch without packet body hash check: {sorted(missing_hash)!r}")
    return InvariantResult.pass_()

def dispatch_requires_output_contract_and_run_scoped_result_paths(state: State, trace) -> InvariantResult:
    del trace
    missing_contract = set(state.dispatches) - set(state.output_contract_checks)
    if missing_contract:
        return InvariantResult.fail(f"dispatch without output contract check: {sorted(missing_contract)!r}")
    missing_result_path_scope = set(state.dispatches) - set(state.result_path_scope_checks)
    if missing_result_path_scope:
        return InvariantResult.fail(f"dispatch without run-scoped result path check: {sorted(missing_result_path_scope)!r}")
    return InvariantResult.pass_()

def packet_integrity_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    missing_files = set(state.packets) - set(state.physical_packet_files)
    blocked = (
        set(state.wrong_delivery_blocks)
        | set(state.packet_body_hash_blocks)
        | set(state.packet_body_hash_identity_blocks)
        | set(state.stale_packet_body_blocks)
        | set(state.output_contract_blocks)
        | set(state.result_path_scope_blocks)
        | missing_files
    )
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"invalid packet envelope/body advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def review_pass_requires_result_envelope_body_and_agent_checks(state: State, trace) -> InvariantResult:
    del trace
    passed = set(state.review_passes)
    missing_envelope = passed - set(state.result_envelope_checks)
    if missing_envelope:
        return InvariantResult.fail(f"review pass without result envelope check: {sorted(missing_envelope)!r}")
    missing_hash = passed - set(state.result_body_hash_checks)
    if missing_hash:
        return InvariantResult.fail(f"review pass without result body hash check: {sorted(missing_hash)!r}")
    missing_agent = passed - set(state.completed_agent_role_checks)
    if missing_agent:
        return InvariantResult.fail(f"review pass without completed agent role check: {sorted(missing_agent)!r}")
    missing_packet_open_envelope = passed - set(state.packet_body_open_envelope_records)
    if missing_packet_open_envelope:
        return InvariantResult.fail(
            f"review pass without packet body-open envelope receipt: {sorted(missing_packet_open_envelope)!r}"
        )
    missing_packet_open_ledger = passed - set(state.packet_body_open_ledger_records)
    if missing_packet_open_ledger:
        return InvariantResult.fail(f"review pass without packet body-open ledger receipt: {sorted(missing_packet_open_ledger)!r}")
    missing_result_ledger = passed - set(state.result_ledger_records)
    if missing_result_ledger:
        return InvariantResult.fail(f"review pass without result ledger absorption: {sorted(missing_result_ledger)!r}")
    missing_result_open_envelope = passed - set(state.result_body_open_envelope_records)
    if missing_result_open_envelope:
        return InvariantResult.fail(
            f"review pass without result body-open envelope receipt: {sorted(missing_result_open_envelope)!r}"
        )
    missing_result_open_ledger = passed - set(state.result_body_open_ledger_records)
    if missing_result_open_ledger:
        return InvariantResult.fail(f"review pass without result body-open ledger receipt: {sorted(missing_result_open_ledger)!r}")
    blocked_agent_ids = passed & set(state.completed_agent_id_blocks)
    if blocked_agent_ids:
        return InvariantResult.fail(f"review pass with invalid completed agent id mapping: {sorted(blocked_agent_ids)!r}")
    return InvariantResult.pass_()

def result_body_integrity_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.result_body_hash_blocks) | set(state.stale_result_body_blocks) | set(state.result_ledger_blocks)
    unsafe = blocked & (set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"invalid result body advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def result_relay_requires_packet_open_and_result_ledger(state: State, trace) -> InvariantResult:
    del trace
    relayed = set(state.result_controller_relay_signatures)
    missing_packet_open_envelope = relayed - set(state.packet_body_open_envelope_records)
    if missing_packet_open_envelope:
        return InvariantResult.fail(
            f"result relayed without packet body-open envelope receipt: {sorted(missing_packet_open_envelope)!r}"
        )
    missing_packet_open_ledger = relayed - set(state.packet_body_open_ledger_records)
    if missing_packet_open_ledger:
        return InvariantResult.fail(f"result relayed without packet body-open ledger receipt: {sorted(missing_packet_open_ledger)!r}")
    missing_result_ledger = relayed - set(state.result_ledger_records)
    if missing_result_ledger:
        return InvariantResult.fail(f"result relayed without result ledger absorption: {sorted(missing_result_ledger)!r}")
    return InvariantResult.pass_()

def wrong_role_completion_never_advances(state: State, trace) -> InvariantResult:
    del trace
    unsafe = set(state.wrong_role_completion_blocks) & set(state.advances)
    if unsafe:
        return InvariantResult.fail(f"wrong-role completion advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def result_requires_dispatch(state: State, trace) -> InvariantResult:
    del trace
    result_ids = set(state.worker_results) | set(state.controller_artifacts)
    missing = result_ids - set(state.dispatches)
    if missing:
        return InvariantResult.fail(f"result without router direct dispatch: {sorted(missing)!r}")
    return InvariantResult.pass_()

def dispatch_requires_controller_reminder(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.dispatches) - set(state.reminder_checked)
    if missing:
        return InvariantResult.fail(f"dispatch without controller reminder check: {sorted(missing)!r}")
    return InvariantResult.pass_()

def packet_open_blocks_never_produce_result_or_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.unopened_packet_blocks)
    unsafe = blocked & (set(state.worker_results) | set(state.controller_artifacts) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"packet open blocker produced result or advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def heartbeat_resume_packet_requires_pm_request(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.pm_resume_requests)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without PM request: {sorted(missing)!r}")
    return InvariantResult.pass_()

def heartbeat_resume_packet_requires_loaded_state(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.heartbeat_loads)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without loaded state: {sorted(missing)!r}")
    return InvariantResult.pass_()

def ambiguous_worker_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_ambiguous_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"ambiguous worker state advanced or dispatched: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

def missing_heartbeat_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_state_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"missing heartbeat state advanced or dispatched: {sorted(unsafe)!r}")
    return InvariantResult.pass_()

INVARIANTS = (
    Invariant(
        "no_advance_from_controller_artifact",
        "Controller-origin implementation evidence cannot advance a route.",
        no_advance_from_controller_artifact,
    ),
    Invariant(
        "advance_requires_review_pass",
        "PM advancement requires reviewer pass.",
        advance_requires_review_pass,
    ),
    Invariant(
        "review_pass_requires_role_origin_audit",
        "Reviewer pass requires a per-packet role-origin audit.",
        review_pass_requires_role_origin_audit,
    ),
    Invariant(
        "review_pass_requires_mail_chain_audit",
        "Reviewer pass requires a full packet/result mail-chain audit.",
        review_pass_requires_mail_chain_audit,
    ),
    Invariant(
        "recipient_body_open_requires_controller_relay_signature",
        "Recipients may open packet/result bodies only after validating a controller relay signature.",
        recipient_body_open_requires_controller_relay_signature,
    ),
    Invariant(
        "missing_or_unopened_mail_requires_pm_restart_or_repair",
        "Unopened, private, or missing-relay mail is sent to PM for restart, repair node, or sender reissue.",
        missing_or_unopened_mail_requires_pm_restart_or_repair,
    ),
    Invariant(
        "invalid_origin_block_requires_warning",
        "Invalid role origin requires a controller warning and PM repair/reissue requirement.",
        invalid_origin_block_requires_warning,
    ),
    Invariant(
        "controller_body_boundary_blocks_never_advance",
        "Controller body reads or execution attempts cannot dispatch, review, or advance.",
        controller_body_boundary_blocks_never_advance,
    ),
    Invariant(
        "controller_handoff_body_leak_never_advances",
        "Controller handoff containing packet body content cannot dispatch, review, or advance.",
        controller_handoff_body_leak_never_advances,
    ),
    Invariant(
        "missing_mutual_role_reminder_never_advances",
        "Controller-visible packet/result handoffs without mutual role reminders cannot dispatch, review, or advance.",
        missing_mutual_role_reminder_never_advances,
    ),
    Invariant(
        "controller_relay_requires_physical_files_and_envelope_only_handoff",
        "Controller relay requires physical packet files, envelope-only handoff, and visible mutual role reminders.",
        controller_relay_requires_physical_files_and_envelope_only_handoff,
    ),
    Invariant(
        "holder_change_requires_user_status_update",
        "Every packet holder change requires a user-visible status update.",
        holder_change_requires_user_status_update,
    ),
    Invariant(
        "cockpit_missing_major_node_requires_chat_mermaid",
        "Entering a major node while Cockpit is missing requires a chat Mermaid route sign.",
        cockpit_missing_major_node_requires_chat_mermaid,
    ),
    Invariant(
        "dispatch_requires_packet_envelope_and_hash_checks",
        "Router direct dispatch requires packet envelope and packet body hash checks.",
        dispatch_requires_packet_envelope_and_hash_checks,
    ),
    Invariant(
        "dispatch_requires_output_contract_and_run_scoped_result_paths",
        "Router direct dispatch requires an output contract and run-scoped result paths.",
        dispatch_requires_output_contract_and_run_scoped_result_paths,
    ),
    Invariant(
        "packet_integrity_blocks_never_advance",
        "Wrong delivery, packet body hash mismatch, stale body, bad contract, or unsafe result path cannot advance.",
        packet_integrity_blocks_never_advance,
    ),
    Invariant(
        "review_pass_requires_result_envelope_body_and_agent_checks",
        "Reviewer pass requires result envelope, result body hash, and completed-agent role checks.",
        review_pass_requires_result_envelope_body_and_agent_checks,
    ),
    Invariant(
        "result_body_integrity_blocks_never_advance",
        "Result body hash mismatch or stale result body cannot advance.",
        result_body_integrity_blocks_never_advance,
    ),
    Invariant(
        "result_relay_requires_packet_open_and_result_ledger",
        "Controller may relay a result only after packet open receipts and result ledger absorption exist.",
        result_relay_requires_packet_open_and_result_ledger,
    ),
    Invariant(
        "wrong_role_completion_never_advances",
        "Wrong-role completion cannot be cosigned, relabelled, or advanced.",
        wrong_role_completion_never_advances,
    ),
    Invariant(
        "result_requires_dispatch",
        "No role result exists without router direct dispatch approval.",
        result_requires_dispatch,
    ),
    Invariant(
        "dispatch_requires_controller_reminder",
        "Router direct dispatch cannot occur unless the PM reminder to the controller is present.",
        dispatch_requires_controller_reminder,
    ),
    Invariant(
        "packet_open_blocks_never_produce_result_or_advance",
        "Packet-open failures cannot produce a result or advance.",
        packet_open_blocks_never_produce_result_or_advance,
    ),
    Invariant(
        "heartbeat_resume_packet_requires_pm_request",
        "Heartbeat cannot mint a resume packet without first asking PM.",
        heartbeat_resume_packet_requires_pm_request,
    ),
    Invariant(
        "heartbeat_resume_packet_requires_loaded_state",
        "Heartbeat resume packets require loaded current-run state.",
        heartbeat_resume_packet_requires_loaded_state,
    ),
    Invariant(
        "ambiguous_worker_state_never_advances",
        "Ambiguous worker state blocks controller execution.",
        ambiguous_worker_state_never_advances,
    ),
    Invariant(
        "missing_heartbeat_state_never_advances",
        "Missing current-run state blocks heartbeat execution.",
        missing_heartbeat_state_never_advances,
    ),
)

__all__ = [
    "no_advance_from_controller_artifact",
    "advance_requires_review_pass",
    "review_pass_requires_role_origin_audit",
    "review_pass_requires_mail_chain_audit",
    "recipient_body_open_requires_controller_relay_signature",
    "missing_or_unopened_mail_requires_pm_restart_or_repair",
    "invalid_origin_block_requires_warning",
    "controller_body_boundary_blocks_never_advance",
    "controller_handoff_body_leak_never_advances",
    "missing_mutual_role_reminder_never_advances",
    "controller_relay_requires_physical_files_and_envelope_only_handoff",
    "holder_change_requires_user_status_update",
    "cockpit_missing_major_node_requires_chat_mermaid",
    "dispatch_requires_packet_envelope_and_hash_checks",
    "dispatch_requires_output_contract_and_run_scoped_result_paths",
    "packet_integrity_blocks_never_advance",
    "review_pass_requires_result_envelope_body_and_agent_checks",
    "result_body_integrity_blocks_never_advance",
    "result_relay_requires_packet_open_and_result_ledger",
    "wrong_role_completion_never_advances",
    "result_requires_dispatch",
    "dispatch_requires_controller_reminder",
    "packet_open_blocks_never_produce_result_or_advance",
    "heartbeat_resume_packet_requires_pm_request",
    "heartbeat_resume_packet_requires_loaded_state",
    "ambiguous_worker_state_never_advances",
    "missing_heartbeat_state_never_advances",
    "INVARIANTS",
]
