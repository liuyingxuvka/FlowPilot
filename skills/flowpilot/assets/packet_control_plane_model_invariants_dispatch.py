"""Packet control-plane invariant group."""

from __future__ import annotations

from flowguard import InvariantResult
from packet_control_plane_model_state import State

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

__all__ = (
    'dispatch_requires_packet_envelope_and_hash_checks',
    'dispatch_requires_output_contract_and_run_scoped_result_paths',
    'packet_integrity_blocks_never_advance',
    'review_pass_requires_result_envelope_body_and_agent_checks',
    'result_body_integrity_blocks_never_advance',
    'result_relay_requires_packet_open_and_result_ledger',
    'wrong_role_completion_never_advances',
    'result_requires_dispatch',
    'dispatch_requires_controller_reminder',
    'packet_open_blocks_never_produce_result_or_advance',
)
