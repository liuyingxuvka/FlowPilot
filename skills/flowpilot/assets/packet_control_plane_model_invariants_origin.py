"""Packet control-plane invariant group."""

from __future__ import annotations

from flowguard import InvariantResult
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

__all__ = (
    'no_advance_from_controller_artifact',
    'advance_requires_review_pass',
    'review_pass_requires_role_origin_audit',
    'review_pass_requires_mail_chain_audit',
    'recipient_body_open_requires_controller_relay_signature',
    'missing_or_unopened_mail_requires_pm_restart_or_repair',
    'invalid_origin_block_requires_warning',
)
