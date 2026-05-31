"""Packet control-plane invariant group."""

from __future__ import annotations

from flowguard import InvariantResult
from packet_control_plane_model_state import State

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

def current_assignment_requires_physical_files_and_envelope_only_handoff(state: State, trace) -> InvariantResult:
    del trace
    relayed = set(state.controller_envelope_reads)
    missing_files = relayed - set(state.physical_packet_files)
    if missing_files:
        return InvariantResult.fail(f"current assignmented without physical packet files: {sorted(missing_files)!r}")
    missing_handoff = relayed - set(state.controller_handoff_envelope_only)
    if missing_handoff:
        return InvariantResult.fail(f"current assignmented without envelope-only handoff: {sorted(missing_handoff)!r}")
    missing_mutual_reminder = relayed - set(state.controller_handoff_mutual_role_reminders)
    if missing_mutual_reminder:
        return InvariantResult.fail(
            f"current assignmented without visible mutual-role reminder: {sorted(missing_mutual_reminder)!r}"
        )
    result_relayed = set(state.result_current_assignments)
    missing_result_mutual_reminder = result_relayed - set(state.result_mutual_role_reminders)
    if missing_result_mutual_reminder:
        return InvariantResult.fail(
            f"current assignmented result without visible mutual-role reminder: {sorted(missing_result_mutual_reminder)!r}"
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

__all__ = (
    'controller_body_boundary_blocks_never_advance',
    'controller_handoff_body_leak_never_advances',
    'missing_mutual_role_reminder_never_advances',
    'current_assignment_requires_physical_files_and_envelope_only_handoff',
    'holder_change_requires_user_status_update',
    'cockpit_missing_major_node_requires_chat_mermaid',
)
