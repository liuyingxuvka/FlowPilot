"""FlowGuard model for current-run role packet access.

This focused model covers the live failure where a role ACKed a packet but
stopped because Controller had not provided body text. The safe path is:
generated role handoff -> ACK -> role-scoped open-packet -> submit-result.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One role packet access transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    handoff_generated: bool = False
    handoff_names_ack: bool = False
    handoff_names_open_packet: bool = False
    handoff_names_submit_result: bool = False
    handoff_body_free: bool = True
    handoff_role_generic: bool = True
    handoff_ad_hoc_waits_for_ack_body: bool = False
    lease_active: bool = False
    packet_assigned_to_lease: bool = False
    responsibility_matches: bool = False
    ack_received: bool = False
    packet_unaccepted: bool = True
    body_hash_matches: bool = True
    body_returned_to_role: bool = False
    controller_saw_body: bool = False
    sealed_open_event_recorded: bool = False
    result_submitted: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class RolePacketAccessStep:
    """Model one role packet access step.

    Input x State -> Set(Output x State)
    reads: current packet assignment, lease, ACK, responsibility, body hash
    writes: generated handoff, sealed-open receipt, result submission
    """

    name = "RolePacketAccessStep"
    input_description = "role packet access tick"
    output_description = "one safe packet access transition"
    reads = ("handoff", "lease", "packet", "ack", "body_hash")
    writes = ("handoff_text", "sealed_open_event", "result_submission")
    idempotency = "current packet open is bound to the assigned lease and records an audit event"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return
    if not state.handoff_generated:
        yield Transition(
            "runtime_generates_body_free_role_handoff",
            replace(
                state,
                status="running",
                handoff_generated=True,
                handoff_names_ack=True,
                handoff_names_open_packet=True,
                handoff_names_submit_result=True,
                handoff_body_free=True,
                handoff_role_generic=True,
                handoff_ad_hoc_waits_for_ack_body=False,
            ),
        )
        return
    if not state.ack_received:
        yield Transition(
            "assigned_role_acks_current_packet",
            replace(
                state,
                lease_active=True,
                packet_assigned_to_lease=True,
                responsibility_matches=True,
                ack_received=True,
                packet_unaccepted=True,
                body_hash_matches=True,
            ),
        )
        return
    if not state.body_returned_to_role:
        yield Transition(
            "role_opens_packet_after_ack_with_current_authority",
            replace(
                state,
                body_returned_to_role=True,
                controller_saw_body=False,
                sealed_open_event_recorded=True,
            ),
        )
        return
    if not state.result_submitted:
        yield Transition("role_submits_result_after_formal_open", replace(state, result_submitted=True))
        return
    yield Transition("role_packet_access_complete", replace(state, status="complete"))


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.handoff_generated:
        if not (state.handoff_names_ack and state.handoff_names_open_packet and state.handoff_names_submit_result):
            failures.append("generated handoff omitted ACK, open-packet, or submit-result command")
        if not state.handoff_body_free:
            failures.append("generated handoff leaked sealed body content")
        if not state.handoff_role_generic:
            failures.append("generated handoff used role-specific wording outside the requested responsibility")
        if state.handoff_ad_hoc_waits_for_ack_body:
            failures.append("generated handoff told role to wait for ACK/runtime body exposure")
    if state.body_returned_to_role:
        if not state.lease_active:
            failures.append("open-packet returned body for inactive lease")
        if not state.packet_assigned_to_lease:
            failures.append("open-packet returned body for wrong lease or unassigned packet")
        if not state.responsibility_matches:
            failures.append("open-packet returned body for mismatched responsibility")
        if not state.ack_received:
            failures.append("open-packet returned body before ACK")
        if not state.packet_unaccepted:
            failures.append("open-packet returned body for accepted or stale packet")
        if not state.body_hash_matches:
            failures.append("open-packet returned body after body hash mismatch")
        if state.controller_saw_body:
            failures.append("Controller saw sealed body during role packet open")
        if not state.sealed_open_event_recorded:
            failures.append("open-packet returned body without sealed open audit event")
    if state.result_submitted and not state.body_returned_to_role:
        failures.append("role result submitted without formal packet open evidence")
    if state.status == "complete" and not state.result_submitted:
        failures.append("role packet access completed without result submission")
    return failures


def hazard_states() -> dict[str, State]:
    safe_open = State(
        status="running",
        handoff_generated=True,
        handoff_names_ack=True,
        handoff_names_open_packet=True,
        handoff_names_submit_result=True,
        lease_active=True,
        packet_assigned_to_lease=True,
        responsibility_matches=True,
        ack_received=True,
        body_returned_to_role=True,
        sealed_open_event_recorded=True,
    )
    return {
        "ad_hoc_waits_for_runtime_body": replace(safe_open, body_returned_to_role=False, handoff_ad_hoc_waits_for_ack_body=True),
        "handoff_leaks_body": replace(safe_open, handoff_body_free=False),
        "handoff_pm_only_for_other_role": replace(safe_open, handoff_role_generic=False),
        "open_without_ack": replace(safe_open, ack_received=False),
        "open_wrong_lease": replace(safe_open, packet_assigned_to_lease=False),
        "open_wrong_role": replace(safe_open, responsibility_matches=False),
        "open_inactive_lease": replace(safe_open, lease_active=False),
        "open_accepted_packet": replace(safe_open, packet_unaccepted=False),
        "open_hash_mismatch": replace(safe_open, body_hash_matches=False),
        "controller_body_leak": replace(safe_open, controller_saw_body=True),
        "missing_open_event": replace(safe_open, sealed_open_event_recorded=False),
        "result_without_open": replace(safe_open, body_returned_to_role=False, result_submitted=True),
    }


def build_workflow() -> Workflow:
    return Workflow((RolePacketAccessStep(),), name="flowpilot_role_packet_access")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


def invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="role_packet_access_invariants",
        description=(
            "Role packet access must use a body-free generated handoff, require "
            "ACK before open-packet, keep Controller away from sealed body text, "
            "and record a sealed-open event before result submission."
        ),
        predicate=invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "RolePacketAccessStep",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
