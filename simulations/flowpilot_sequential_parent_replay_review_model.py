"""FlowGuard model for single parent backward review closure.

Risk purpose:
- Parent/module backward replay is a Reviewer result family, not a task result.
- The accepted ``review.parent_backward_replay`` result is the closure evidence
  PM absorbs; there is no second reviewer packet over that result.
- If more than one parent/module review gap reaches final closure, or any
  parent/module review gap appears only at final closure, the control plane is
  corrupt and must hard-block instead of dispatching late repair reviews.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SINGLE_PARENT_BACKWARD_REVIEW = "valid_single_parent_backward_review"
VALID_ACTIVE_PARENT_REVIEW_ISSUED = "valid_active_parent_review_issued"

OLD_TASK_PARENT_BACKWARD_ACCEPTED = "old_task_parent_backward_accepted"
PM_SEGMENT_BEFORE_PARENT_REVIEW = "pm_segment_before_parent_review"
TERMINAL_REPLAY_BEFORE_PARENT_REVIEW = "terminal_replay_before_parent_review"
MULTIPLE_FINAL_PARENT_GAPS_DISPATCH_REPAIR = "multiple_final_parent_gaps_dispatch_repair"
FINAL_PARENT_GAP_NOT_HARD_BLOCKED = "final_parent_gap_not_hard_blocked"
OLD_STATE_TRANSLATED_AS_CURRENT = "old_state_translated_as_current"

VALID_SCENARIOS = (
    VALID_SINGLE_PARENT_BACKWARD_REVIEW,
    VALID_ACTIVE_PARENT_REVIEW_ISSUED,
)
NEGATIVE_SCENARIOS = (
    OLD_TASK_PARENT_BACKWARD_ACCEPTED,
    PM_SEGMENT_BEFORE_PARENT_REVIEW,
    TERMINAL_REPLAY_BEFORE_PARENT_REVIEW,
    MULTIPLE_FINAL_PARENT_GAPS_DISPATCH_REPAIR,
    FINAL_PARENT_GAP_NOT_HARD_BLOCKED,
    OLD_STATE_TRANSLATED_AS_CURRENT,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One parent backward review ordering evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = "unset"

    child_chain_closed_current: bool = True
    parent_review_packet_current: bool = False
    parent_review_result_accepted: bool = False
    old_task_parent_replay_result_accepted: bool = False
    parent_closure_recorded: bool = False
    pm_segment_decision_offered: bool = False
    pm_parent_completion_offered: bool = False
    terminal_replay_offered: bool = False

    current_parent_review_gap_count: int = 0
    final_gate_ready: bool = False
    ordinary_late_parent_review_dispatched: bool = False
    control_plane_blocker_offered: bool = False
    fallback_or_compatibility_path_used: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class SingleParentBackwardReviewStep:
    """One transition for parent backward review ordering.

    Input x State -> Set(Output x State)
    reads: current parent review packet/result, route topology, final route-wide
      gate ledger, router next-action projection
    writes: one accepted/rejected parent review ordering decision
    idempotency: pure classification for one current route/frontier version.
    """

    name = "SingleParentBackwardReviewStep"
    input_description = "FlowPilot parent backward review ordering tick"
    output_description = "one parent-review ordering transition"
    reads = (
        "review.parent_backward_replay",
        "route_topology",
        "final_route_wide_gate_ledger",
        "router_next_action_projection",
    )
    writes = ("parent_backward_review_ordering_decision",)
    idempotency = "pure current-route classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _valid_closed_state() -> State:
    return State(
        status="running",
        scenario=VALID_SINGLE_PARENT_BACKWARD_REVIEW,
        child_chain_closed_current=True,
        parent_review_packet_current=True,
        parent_review_result_accepted=True,
        parent_closure_recorded=True,
        pm_segment_decision_offered=True,
        pm_parent_completion_offered=True,
        terminal_replay_offered=True,
        current_parent_review_gap_count=0,
    )


def _valid_active_parent_review_state() -> State:
    return State(
        status="running",
        scenario=VALID_ACTIVE_PARENT_REVIEW_ISSUED,
        child_chain_closed_current=True,
        parent_review_packet_current=True,
        parent_review_result_accepted=False,
        parent_closure_recorded=False,
        pm_segment_decision_offered=False,
        pm_parent_completion_offered=False,
        terminal_replay_offered=False,
        current_parent_review_gap_count=1,
        final_gate_ready=False,
        ordinary_late_parent_review_dispatched=False,
        control_plane_blocker_offered=False,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_SINGLE_PARENT_BACKWARD_REVIEW:
        return _valid_closed_state()
    if scenario == VALID_ACTIVE_PARENT_REVIEW_ISSUED:
        return _valid_active_parent_review_state()
    state = _valid_closed_state()
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == OLD_TASK_PARENT_BACKWARD_ACCEPTED:
        updates.update(
            parent_review_packet_current=False,
            parent_review_result_accepted=False,
            old_task_parent_replay_result_accepted=True,
            parent_closure_recorded=True,
        )
    elif scenario == PM_SEGMENT_BEFORE_PARENT_REVIEW:
        updates.update(
            parent_review_result_accepted=False,
            parent_closure_recorded=False,
            pm_segment_decision_offered=True,
            pm_parent_completion_offered=False,
            terminal_replay_offered=False,
        )
    elif scenario == TERMINAL_REPLAY_BEFORE_PARENT_REVIEW:
        updates.update(
            parent_review_result_accepted=False,
            parent_closure_recorded=False,
            pm_segment_decision_offered=False,
            pm_parent_completion_offered=False,
            terminal_replay_offered=True,
        )
    elif scenario == MULTIPLE_FINAL_PARENT_GAPS_DISPATCH_REPAIR:
        updates.update(
            parent_review_packet_current=False,
            parent_review_result_accepted=False,
            parent_closure_recorded=False,
            pm_segment_decision_offered=False,
            pm_parent_completion_offered=False,
            terminal_replay_offered=False,
            current_parent_review_gap_count=2,
            final_gate_ready=True,
            ordinary_late_parent_review_dispatched=True,
            control_plane_blocker_offered=False,
        )
    elif scenario == FINAL_PARENT_GAP_NOT_HARD_BLOCKED:
        updates.update(
            parent_review_packet_current=False,
            parent_review_result_accepted=False,
            parent_closure_recorded=False,
            pm_segment_decision_offered=False,
            pm_parent_completion_offered=False,
            terminal_replay_offered=True,
            current_parent_review_gap_count=1,
            final_gate_ready=True,
            ordinary_late_parent_review_dispatched=False,
            control_plane_blocker_offered=False,
        )
    elif scenario == OLD_STATE_TRANSLATED_AS_CURRENT:
        updates.update(
            parent_review_packet_current=False,
            parent_review_result_accepted=True,
            old_task_parent_replay_result_accepted=True,
            fallback_or_compatibility_path_used=True,
        )
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return replace(state, **updates)


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if is_terminal(state):
        return ()
    if state.status == "new":
        return tuple(Transition(f"select_{scenario}", _scenario_state(scenario)) for scenario in SCENARIOS)
    failures = parent_review_failures(state)
    if failures:
        return (Transition(f"reject_{state.scenario}", replace(state, status="rejected", terminal_reason=failures[0])),)
    return (Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="single_parent_review_passed")),)


def parent_review_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.fallback_or_compatibility_path_used:
        failures.append("fallback or old-state compatibility path was used for parent backward review")
    if state.old_task_parent_replay_result_accepted:
        failures.append("old task.parent_backward_replay result counted as current parent review")
    if state.parent_review_packet_current and not state.child_chain_closed_current:
        failures.append("parent backward review packet was issued before current child chain closed")
    if state.parent_closure_recorded and not state.parent_review_result_accepted:
        failures.append("parent closure recorded before review.parent_backward_replay accepted")
    if state.pm_segment_decision_offered and not state.parent_review_result_accepted:
        failures.append("PM parent segment decision offered before parent backward review")
    if state.pm_parent_completion_offered and not state.parent_review_result_accepted:
        failures.append("parent completion offered before parent backward review")
    if state.terminal_replay_offered and not state.parent_review_result_accepted:
        failures.append("terminal backward replay offered before required parent backward review")
    if state.final_gate_ready and state.current_parent_review_gap_count > 0:
        if state.ordinary_late_parent_review_dispatched:
            failures.append("final gate dispatched an ordinary late parent review instead of hard blocking")
        if not state.control_plane_blocker_offered:
            failures.append("final gate parent review gap was not hard-blocked as control-plane corruption")
    if state.current_parent_review_gap_count > 1 and state.final_gate_ready:
        failures.append("multiple parent review gaps reached final gate")
    return failures


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted":
        failures.extend(parent_review_failures(state))
        if state.scenario not in VALID_SCENARIOS:
            failures.append(f"negative scenario was accepted: {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid single parent backward review route was rejected")
    return failures


def _invariant(name: str, description: str) -> Invariant:
    def _predicate(state: State, _trace):
        failures = invariant_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
        return InvariantResult.pass_()

    return Invariant(name=name, description=description, predicate=_predicate)


INVARIANTS = (
    _invariant(
        "parent_closes_only_after_single_review_parent_packet",
        "Parent closure, PM decisions, and terminal replay require accepted review.parent_backward_replay.",
    ),
    _invariant(
        "final_parent_review_gap_is_corruption_not_repair",
        "Parent review gaps discovered at final gate hard-block as control-plane corruption.",
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((SingleParentBackwardReviewStep(),), name="flowpilot_single_parent_backward_review")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def intended_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in VALID_SCENARIOS}
