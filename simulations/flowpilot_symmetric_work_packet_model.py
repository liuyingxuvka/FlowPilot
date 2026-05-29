"""FlowGuard model for symmetric new FlowPilot work packets."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_symmetric_work_packet_lifecycle"
MAX_SEQUENCE_LENGTH = 24


@dataclass(frozen=True)
class State:
    status: str = "new"
    startup_recorded: bool = False
    route_created: bool = False
    pm_packet_issued: bool = False
    pm_leased: bool = False
    pm_ack: bool = False
    pm_result: bool = False
    flowguard_packet_issued: bool = False
    flowguard_leased: bool = False
    flowguard_ack: bool = False
    flowguard_result: bool = False
    flowguard_order_recorded: bool = False
    reviewer_packet_issued: bool = False
    reviewer_leased: bool = False
    reviewer_ack: bool = False
    reviewer_result: bool = False
    review_recorded: bool = False
    validation_packet_issued: bool = False
    validation_leased: bool = False
    validation_ack: bool = False
    validation_result: bool = False
    validation_recorded: bool = False
    closure_packet_issued: bool = False
    closure_leased: bool = False
    closure_ack: bool = False
    closure_result: bool = False
    final_closure_complete: bool = False
    nonpacket_role_lease: bool = False
    side_command_flowguard: bool = False
    side_command_review: bool = False
    side_command_validation: bool = False
    side_command_closure: bool = False
    dirty_reviewer_projection: bool = False
    dirty_flowguard_projection: bool = False
    ack_only_completed: bool = False
    pm_only_terminal: bool = False
    lingering_active_lease_after_completion: bool = False


@dataclass(frozen=True)
class Tick:
    """One symmetric work-packet lifecycle transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_startup_and_route",
    "issue_pm_packet",
    "lease_pm_packet",
    "ack_pm_packet",
    "submit_pm_result",
    "issue_flowguard_packet",
    "lease_flowguard_packet",
    "ack_flowguard_packet",
    "submit_flowguard_result",
    "record_flowguard_order_from_packet",
    "issue_reviewer_packet",
    "lease_reviewer_packet",
    "ack_reviewer_packet",
    "submit_reviewer_result",
    "record_review_from_packet",
    "issue_validation_packet",
    "lease_validation_packet",
    "ack_validation_packet",
    "submit_validation_result",
    "record_validation_from_packet",
    "issue_closure_packet",
    "lease_closure_packet",
    "ack_closure_packet",
    "submit_closure_result_and_close",
)


def initial_state() -> State:
    return State()


class SymmetricPacketStep:
    name = "SymmetricPacketStep"
    reads = (
        "startup_recorded",
        "route_created",
        "packet_state",
        "lease_state",
        "result_state",
        "flowguard_state",
        "review_state",
        "validation_state",
        "closure_state",
    )
    writes = (
        "packets",
        "leases",
        "acks",
        "results",
        "flowguard_orders",
        "reviews",
        "validation",
        "closure",
    )
    input_description = "Input x State: one requested FlowPilot lifecycle transition"
    output_description = "Set(Output x State): next legal symmetric packet lifecycle state"
    idempotency = "each transition adds one role-packet fact and never uses side-command completion"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_symmetric_packet_invariant", replace(state, status="blocked")),)
    if not state.startup_recorded or not state.route_created:
        return (Transition("record_startup_and_route", replace(state, startup_recorded=True, route_created=True, status="running")),)
    if not state.pm_packet_issued:
        return (Transition("issue_pm_packet", replace(state, pm_packet_issued=True)),)
    if not state.pm_leased:
        return (Transition("lease_pm_packet", replace(state, pm_leased=True)),)
    if not state.pm_ack:
        return (Transition("ack_pm_packet", replace(state, pm_ack=True)),)
    if not state.pm_result:
        return (Transition("submit_pm_result", replace(state, pm_result=True)),)
    if not state.flowguard_packet_issued:
        return (Transition("issue_flowguard_packet", replace(state, flowguard_packet_issued=True)),)
    if not state.flowguard_leased:
        return (Transition("lease_flowguard_packet", replace(state, flowguard_leased=True)),)
    if not state.flowguard_ack:
        return (Transition("ack_flowguard_packet", replace(state, flowguard_ack=True)),)
    if not state.flowguard_result:
        return (Transition("submit_flowguard_result", replace(state, flowguard_result=True)),)
    if not state.flowguard_order_recorded:
        return (Transition("record_flowguard_order_from_packet", replace(state, flowguard_order_recorded=True)),)
    if not state.reviewer_packet_issued:
        return (Transition("issue_reviewer_packet", replace(state, reviewer_packet_issued=True)),)
    if not state.reviewer_leased:
        return (Transition("lease_reviewer_packet", replace(state, reviewer_leased=True)),)
    if not state.reviewer_ack:
        return (Transition("ack_reviewer_packet", replace(state, reviewer_ack=True)),)
    if not state.reviewer_result:
        return (Transition("submit_reviewer_result", replace(state, reviewer_result=True)),)
    if not state.review_recorded:
        return (Transition("record_review_from_packet", replace(state, review_recorded=True)),)
    if not state.validation_packet_issued:
        return (Transition("issue_validation_packet", replace(state, validation_packet_issued=True)),)
    if not state.validation_leased:
        return (Transition("lease_validation_packet", replace(state, validation_leased=True)),)
    if not state.validation_ack:
        return (Transition("ack_validation_packet", replace(state, validation_ack=True)),)
    if not state.validation_result:
        return (Transition("submit_validation_result", replace(state, validation_result=True)),)
    if not state.validation_recorded:
        return (Transition("record_validation_from_packet", replace(state, validation_recorded=True)),)
    if not state.closure_packet_issued:
        return (Transition("issue_closure_packet", replace(state, closure_packet_issued=True)),)
    if not state.closure_leased:
        return (Transition("lease_closure_packet", replace(state, closure_leased=True)),)
    if not state.closure_ack:
        return (Transition("ack_closure_packet", replace(state, closure_ack=True)),)
    if not state.closure_result or not state.final_closure_complete:
        return (
            Transition(
                "submit_closure_result_and_close",
                replace(state, closure_result=True, final_closure_complete=True, status="complete"),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_packet_issued and not (state.startup_recorded and state.route_created):
        failures.append("PM packet issued before startup route authority")
    if state.pm_leased and not state.pm_packet_issued:
        failures.append("PM leased without packet")
    if state.pm_ack and not state.pm_leased:
        failures.append("PM ACK without lease")
    if state.pm_result and not state.pm_ack:
        failures.append("PM result without ACK")
    if state.flowguard_packet_issued and not state.pm_result:
        failures.append("FlowGuard packet issued before PM result")
    if state.flowguard_leased and not state.flowguard_packet_issued:
        failures.append("FlowGuard operator leased without FlowGuard packet")
    if state.flowguard_ack and not state.flowguard_leased:
        failures.append("FlowGuard ACK without packet lease")
    if state.flowguard_result and not state.flowguard_ack:
        failures.append("FlowGuard result without ACK")
    if state.flowguard_order_recorded and not state.flowguard_result:
        failures.append("FlowGuard order recorded without FlowGuard packet result")
    if state.reviewer_packet_issued and not state.flowguard_order_recorded:
        failures.append("Reviewer packet issued before FlowGuard packet evidence")
    if state.reviewer_leased and not state.reviewer_packet_issued:
        failures.append("Reviewer leased without review packet")
    if state.reviewer_ack and not state.reviewer_leased:
        failures.append("Reviewer ACK without packet lease")
    if state.reviewer_result and not state.reviewer_ack:
        failures.append("Reviewer result without ACK")
    if state.review_recorded and not state.reviewer_result:
        failures.append("Review recorded without reviewer packet result")
    if state.validation_packet_issued and not state.review_recorded:
        failures.append("Validation packet issued before review packet result")
    if state.validation_result and not state.validation_ack:
        failures.append("Validation result without ACK")
    if state.validation_recorded and not state.validation_result:
        failures.append("Validation evidence recorded without validation packet result")
    if state.closure_packet_issued and not state.validation_recorded:
        failures.append("Closure packet issued before validation packet result")
    if state.closure_result and not state.closure_ack:
        failures.append("Closure result without ACK")
    if state.final_closure_complete and not state.closure_result:
        failures.append("Final closure completed without closure packet result")
    if state.nonpacket_role_lease:
        failures.append("non-PM role was leased without an issued packet")
    if state.side_command_flowguard:
        failures.append("FlowGuard was completed through a side command instead of a packet result")
    if state.side_command_review:
        failures.append("Review was completed through a side command instead of a reviewer packet result")
    if state.side_command_validation:
        failures.append("Validation was recorded through a side command instead of a validation packet result")
    if state.side_command_closure:
        failures.append("Closure was completed through a side command instead of a closure packet result")
    if state.dirty_reviewer_projection:
        failures.append("Reviewer lease projection remained active or missing packet ACK after review")
    if state.dirty_flowguard_projection:
        failures.append("FlowGuard lease projection remained active or missing packet ACK after evidence")
    if state.ack_only_completed:
        failures.append("ACK-only packet was treated as completed work")
    if state.pm_only_terminal:
        failures.append("PM-only result reached terminal closure without check/review/validation/closure packets")
    if state.lingering_active_lease_after_completion:
        failures.append("completed packet left an active lease projection")
    return failures


def is_success(state: State) -> bool:
    return state.status == "complete" and state.final_closure_complete and not invariant_failures(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def state_summary(state: State) -> dict[str, bool | str]:
    return dict(state.__dict__)


def target_state() -> State:
    state = initial_state()
    while True:
        transitions = next_safe_states(state)
        if not transitions:
            return state
        state = transitions[0].state


def hazard_states() -> dict[str, State]:
    target = target_state()
    return {
        "nonpacket_flowguard_lease": replace(target, nonpacket_role_lease=True),
        "flowguard_side_command_completion": replace(target, side_command_flowguard=True),
        "review_side_command_completion": replace(target, side_command_review=True),
        "validation_side_command_completion": replace(target, side_command_validation=True),
        "closure_side_command_completion": replace(target, side_command_closure=True),
        "dirty_reviewer_projection": replace(target, dirty_reviewer_projection=True),
        "dirty_flowguard_projection": replace(target, dirty_flowguard_projection=True),
        "ack_only_completion": replace(target, ack_only_completed=True),
        "pm_only_terminal": replace(target, pm_only_terminal=True),
        "lingering_active_lease_after_completion": replace(target, lingering_active_lease_after_completion=True),
        "review_without_packet": replace(target, reviewer_packet_issued=False, reviewer_leased=True, reviewer_ack=True, reviewer_result=True),
        "closure_before_validation_packet": replace(target, validation_packet_issued=False, validation_recorded=False, closure_packet_issued=True, closure_result=True, final_closure_complete=True),
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(SymmetricPacketStep(),), name=MODEL_ID)


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "symmetric_work_packet_lifecycle",
        "Every new FlowPilot backend role must be represented by an issued packet, packet lease, ACK, result, and packet-owned side effect.",
        _invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
