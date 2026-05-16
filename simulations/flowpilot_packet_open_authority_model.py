"""FlowGuard model for FlowPilot packet-open authority and formal exits.

Risk purpose: this FlowGuard model (https://github.com/liuyingxuvka/FlowGuard)
reviews the packet-open handoff where a role has successfully opened an
addressed packet through FlowPilot runtime checks. It guards against the PM
standing by for an extra relay after a verified open, PM routing a blocker back
to itself, PM inventing a parallel repair flow, or ordinary roles silently
waiting instead of submitting a result or formal blocker. Future agents should
run this model whenever packet runtime authority metadata, role packet prompts,
or PM recovery-exit guidance changes. Companion command:
`python simulations/run_flowpilot_packet_open_authority_checks.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One packet-open authority step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    lifecycle: str = "delivered"  # delivered | opened | terminal
    role_kind: str = "unknown"  # unknown | pm | ordinary
    pm_context: str = "none"  # none | startup | control_blocker
    open_verified: bool = False
    authority_recorded: bool = False
    formal_exit: str = "none"  # none | result | ordinary_blocker | pm_startup_repair | pm_protocol_dead_end | pm_control_repair | wait_for_relay | pm_self_blocker | custom_pm_exit


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


class PacketOpenAuthorityStep:
    """Input x State -> Set(Output x State) for packet-open continuation."""

    name = "PacketOpenAuthorityStep"
    input_description = "one packet-open or formal-exit transition"
    output_description = "verified open metadata, packet result, or existing formal blocker/recovery exit"
    reads = ("packet envelope", "packet ledger", "role card", "PM recovery policy")
    writes = ("packet-open session", "packet ledger", "formal packet result or existing repair/blocker output")
    idempotency = "A verified open is a read receipt; exactly one result or formal exit completes the packet obligation."

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for label, new_state in next_states(state):
            yield FunctionResult(output=Action(label), new_state=new_state, label=label)


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    if state.lifecycle == "terminal":
        return ()

    if state.lifecycle == "delivered":
        return (
            (
                "pm_startup_packet_open_verified_and_authorized",
                _step(
                    state,
                    lifecycle="opened",
                    role_kind="pm",
                    pm_context="startup",
                    open_verified=True,
                    authority_recorded=True,
                ),
            ),
            (
                "pm_control_blocker_packet_open_verified_and_authorized",
                _step(
                    state,
                    lifecycle="opened",
                    role_kind="pm",
                    pm_context="control_blocker",
                    open_verified=True,
                    authority_recorded=True,
                ),
            ),
            (
                "ordinary_role_packet_open_verified_and_authorized",
                _step(
                    state,
                    lifecycle="opened",
                    role_kind="ordinary",
                    open_verified=True,
                    authority_recorded=True,
                ),
            ),
        )

    if state.lifecycle == "opened" and state.open_verified:
        if state.role_kind == "pm" and state.pm_context == "startup":
            return (
                (
                    "pm_completes_opened_packet_work",
                    _step(state, lifecycle="terminal", formal_exit="result"),
                ),
                (
                    "pm_requests_existing_startup_repair",
                    _step(state, lifecycle="terminal", formal_exit="pm_startup_repair"),
                ),
                (
                    "pm_declares_existing_startup_protocol_dead_end",
                    _step(state, lifecycle="terminal", formal_exit="pm_protocol_dead_end"),
                ),
            )
        if state.role_kind == "pm" and state.pm_context == "control_blocker":
            return (
                (
                    "pm_records_existing_control_blocker_repair_decision",
                    _step(state, lifecycle="terminal", formal_exit="pm_control_repair"),
                ),
            )
        if state.role_kind == "ordinary":
            return (
                (
                    "ordinary_role_submits_packet_result",
                    _step(state, lifecycle="terminal", formal_exit="result"),
                ),
                (
                    "ordinary_role_submits_existing_formal_blocker",
                    _step(state, lifecycle="terminal", formal_exit="ordinary_blocker"),
                ),
            )

    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    verified_open = state.lifecycle in {"opened", "terminal"} and state.open_verified

    if verified_open and not state.authority_recorded:
        failures.append("verified open did not record work authority")
    if verified_open and state.formal_exit == "wait_for_relay":
        failures.append("verified open waited for additional relay")
    if state.role_kind == "pm" and state.formal_exit == "ordinary_blocker":
        failures.append("PM routed inability through an ordinary blocker")
    if state.role_kind == "pm" and state.formal_exit == "pm_self_blocker":
        failures.append("PM routed a blocker back to PM")
    if state.role_kind == "pm" and state.formal_exit == "custom_pm_exit":
        failures.append("PM invented a custom recovery flow")
    if state.role_kind == "ordinary" and verified_open and state.formal_exit == "none" and state.lifecycle == "terminal":
        failures.append("ordinary role ended without result or formal blocker")

    return failures


def _invariant(name: str, expected: str) -> Invariant:
    def check(state: State, trace) -> InvariantResult:
        del trace
        failures = invariant_failures(state)
        if expected in failures:
            return InvariantResult.fail(expected)
        return InvariantResult.pass_()

    return Invariant(name=name, description=expected, predicate=check)


INVARIANTS = (
    _invariant("verified_open_records_authority", "verified open did not record work authority"),
    _invariant("verified_open_does_not_wait_for_extra_relay", "verified open waited for additional relay"),
    _invariant("pm_does_not_use_ordinary_blocker", "PM routed inability through an ordinary blocker"),
    _invariant("pm_does_not_self_block", "PM routed a blocker back to PM"),
    _invariant("pm_does_not_invent_custom_exit", "PM invented a custom recovery flow"),
    _invariant("ordinary_role_uses_result_or_blocker", "ordinary role ended without result or formal blocker"),
)


HAZARD_STATES = {
    "verified_open_without_authority": replace(
        initial_state(),
        lifecycle="opened",
        role_kind="pm",
        pm_context="startup",
        open_verified=True,
        authority_recorded=False,
    ),
    "pm_waits_for_extra_relay_after_verified_open": replace(
        initial_state(),
        lifecycle="terminal",
        role_kind="pm",
        pm_context="startup",
        open_verified=True,
        authority_recorded=True,
        formal_exit="wait_for_relay",
    ),
    "pm_self_blocker_loop": replace(
        initial_state(),
        lifecycle="terminal",
        role_kind="pm",
        pm_context="startup",
        open_verified=True,
        authority_recorded=True,
        formal_exit="pm_self_blocker",
    ),
    "pm_custom_repair_flow": replace(
        initial_state(),
        lifecycle="terminal",
        role_kind="pm",
        pm_context="control_blocker",
        open_verified=True,
        authority_recorded=True,
        formal_exit="custom_pm_exit",
    ),
    "ordinary_role_silent_terminal_wait": replace(
        initial_state(),
        lifecycle="terminal",
        role_kind="ordinary",
        open_verified=True,
        authority_recorded=True,
        formal_exit="none",
    ),
}


def build_workflow() -> Workflow:
    return Workflow((PacketOpenAuthorityStep(),), name="flowpilot_packet_open_authority")


def is_terminal(state: State) -> bool:
    return state.lifecycle == "terminal"


def is_success(state: State) -> bool:
    return state.lifecycle == "terminal"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


__all__ = [
    "EXTERNAL_INPUTS",
    "HAZARD_STATES",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
