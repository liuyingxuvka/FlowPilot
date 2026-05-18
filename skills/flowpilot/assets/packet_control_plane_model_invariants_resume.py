"""Packet control-plane invariant group."""

from __future__ import annotations

from flowguard import InvariantResult
from packet_control_plane_model_state import State

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

__all__ = (
    'heartbeat_resume_packet_requires_pm_request',
    'heartbeat_resume_packet_requires_loaded_state',
    'ambiguous_worker_state_never_advances',
    'missing_heartbeat_state_never_advances',
)
