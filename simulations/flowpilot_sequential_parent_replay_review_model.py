"""FlowGuard model for sequential parent replay review closure.

Risk purpose:
- Parent/module backward replay execution is a task result, not the independent
  review signature for that result.
- A parent/module node, parent segment decision, and terminal backward replay
  may progress only after the replay result has an accepted independent review.
- When multiple current parent replay results are missing review, Router must
  select one current review packet in topology order: deepest first, then route
  order. It must not issue parallel parent replay reviews.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SEQUENTIAL_PARENT_REPLAY_REVIEW = "valid_sequential_parent_replay_review"
VALID_DEEPEST_GAP_SELECTED_FIRST = "valid_deepest_gap_selected_first"

RAW_REPLAY_CLOSES_PARENT = "raw_replay_closes_parent"
SEGMENT_DECISION_BEFORE_REVIEW = "segment_decision_before_review"
TERMINAL_REPLAY_BEFORE_PARENT_REVIEW = "terminal_replay_before_parent_review"
PARALLEL_PARENT_REPLAY_REVIEWS = "parallel_parent_replay_reviews"
ROOT_GAP_SELECTED_BEFORE_CHILD_GAP = "root_gap_selected_before_child_gap"
OLD_STATE_COUNTS_RAW_REPLAY_AS_COMPLETE = "old_state_counts_raw_replay_as_complete"

VALID_SCENARIOS = (
    VALID_SEQUENTIAL_PARENT_REPLAY_REVIEW,
    VALID_DEEPEST_GAP_SELECTED_FIRST,
)
NEGATIVE_SCENARIOS = (
    RAW_REPLAY_CLOSES_PARENT,
    SEGMENT_DECISION_BEFORE_REVIEW,
    TERMINAL_REPLAY_BEFORE_PARENT_REVIEW,
    PARALLEL_PARENT_REPLAY_REVIEWS,
    ROOT_GAP_SELECTED_BEFORE_CHILD_GAP,
    OLD_STATE_COUNTS_RAW_REPLAY_AS_COMPLETE,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One parent replay review ordering evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = "unset"

    child_chain_closed_current: bool = True
    parent_replay_result_accepted: bool = False
    independent_replay_review_accepted: bool = False
    parent_replay_closure_recorded: bool = False
    pm_segment_decision_offered: bool = False
    pm_parent_completion_offered: bool = False
    terminal_replay_offered: bool = False

    current_missing_review_gap_count: int = 0
    review_packets_issued_this_tick: int = 0
    selected_gap_depth: int = 0
    deepest_missing_gap_depth: int = 0
    selected_gap_route_order_index: int = 0
    earliest_deepest_gap_route_order_index: int = 0

    old_state_raw_replay_claimed_complete: bool = False
    fallback_or_compatibility_path_used: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class SequentialParentReplayReviewStep:
    """One transition for parent replay review ordering.

    Input x State -> Set(Output x State)
    reads: parent replay task result, independent review result, route topology,
    final route-wide gate ledger, router next-action projection
    writes: one accepted/rejected parent replay review ordering decision
    idempotency: pure classification for one current route/frontier version.
    """

    name = "SequentialParentReplayReviewStep"
    input_description = "FlowPilot parent replay review ordering tick"
    output_description = "one replay-review ordering transition"
    reads = (
        "parent_backward_replay_result",
        "review.any_current_subject",
        "route_topology",
        "final_route_wide_gate_ledger",
        "router_next_action_projection",
    )
    writes = ("parent_replay_review_ordering_decision",)
    idempotency = "pure current-route classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _valid_sequence_state() -> State:
    return State(
        status="running",
        scenario=VALID_SEQUENTIAL_PARENT_REPLAY_REVIEW,
        child_chain_closed_current=True,
        parent_replay_result_accepted=True,
        independent_replay_review_accepted=True,
        parent_replay_closure_recorded=True,
        pm_segment_decision_offered=True,
        pm_parent_completion_offered=True,
        terminal_replay_offered=True,
        current_missing_review_gap_count=0,
        review_packets_issued_this_tick=0,
    )


def _valid_deepest_gap_state() -> State:
    return State(
        status="running",
        scenario=VALID_DEEPEST_GAP_SELECTED_FIRST,
        child_chain_closed_current=True,
        parent_replay_result_accepted=True,
        independent_replay_review_accepted=False,
        parent_replay_closure_recorded=False,
        pm_segment_decision_offered=False,
        pm_parent_completion_offered=False,
        terminal_replay_offered=False,
        current_missing_review_gap_count=2,
        review_packets_issued_this_tick=1,
        selected_gap_depth=2,
        deepest_missing_gap_depth=2,
        selected_gap_route_order_index=3,
        earliest_deepest_gap_route_order_index=3,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_SEQUENTIAL_PARENT_REPLAY_REVIEW:
        return _valid_sequence_state()
    if scenario == VALID_DEEPEST_GAP_SELECTED_FIRST:
        return _valid_deepest_gap_state()
    state = _valid_sequence_state()
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == RAW_REPLAY_CLOSES_PARENT:
        updates.update(
            independent_replay_review_accepted=False,
            parent_replay_closure_recorded=True,
            pm_segment_decision_offered=False,
            pm_parent_completion_offered=False,
            terminal_replay_offered=False,
        )
    elif scenario == SEGMENT_DECISION_BEFORE_REVIEW:
        updates.update(
            independent_replay_review_accepted=False,
            parent_replay_closure_recorded=False,
            pm_segment_decision_offered=True,
            pm_parent_completion_offered=False,
            terminal_replay_offered=False,
        )
    elif scenario == TERMINAL_REPLAY_BEFORE_PARENT_REVIEW:
        updates.update(
            independent_replay_review_accepted=False,
            parent_replay_closure_recorded=False,
            pm_segment_decision_offered=False,
            pm_parent_completion_offered=False,
            terminal_replay_offered=True,
        )
    elif scenario == PARALLEL_PARENT_REPLAY_REVIEWS:
        state = _valid_deepest_gap_state()
        updates.update(review_packets_issued_this_tick=2)
    elif scenario == ROOT_GAP_SELECTED_BEFORE_CHILD_GAP:
        state = _valid_deepest_gap_state()
        updates.update(selected_gap_depth=0, deepest_missing_gap_depth=2)
    elif scenario == OLD_STATE_COUNTS_RAW_REPLAY_AS_COMPLETE:
        updates.update(
            independent_replay_review_accepted=False,
            parent_replay_closure_recorded=True,
            pm_segment_decision_offered=True,
            pm_parent_completion_offered=True,
            terminal_replay_offered=True,
            old_state_raw_replay_claimed_complete=True,
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
    failures = replay_review_failures(state)
    if failures:
        return (Transition(f"reject_{state.scenario}", replace(state, status="rejected", terminal_reason=failures[0])),)
    return (Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="sequential_replay_review_passed")),)


def replay_review_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.fallback_or_compatibility_path_used:
        failures.append("fallback or old-state compatibility path was used for parent replay review")
    if state.parent_replay_result_accepted and not state.child_chain_closed_current:
        failures.append("parent replay result was accepted before current child chain closed")
    if state.parent_replay_closure_recorded and not state.independent_replay_review_accepted:
        failures.append("parent replay closure recorded before independent review accepted")
    if state.pm_segment_decision_offered and not state.independent_replay_review_accepted:
        failures.append("PM parent segment decision offered before independent parent replay review")
    if state.pm_parent_completion_offered and not state.independent_replay_review_accepted:
        failures.append("parent completion offered before independent parent replay review")
    if state.terminal_replay_offered and not state.independent_replay_review_accepted:
        failures.append("terminal backward replay offered before required parent replay review")
    if state.current_missing_review_gap_count > 0:
        if state.review_packets_issued_this_tick != 1:
            failures.append("Router did not issue exactly one current parent replay review packet for missing-review gaps")
        if state.selected_gap_depth < state.deepest_missing_gap_depth:
            failures.append("Router selected a shallower parent replay review gap before the deepest current gap")
        if (
            state.selected_gap_depth == state.deepest_missing_gap_depth
            and state.selected_gap_route_order_index > state.earliest_deepest_gap_route_order_index
        ):
            failures.append("Router skipped the earliest route-order parent replay review gap at the deepest level")
    if state.old_state_raw_replay_claimed_complete and not state.independent_replay_review_accepted:
        failures.append("old raw parent replay completion claim counted as current closure without review")
    return failures


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted":
        failures.extend(replay_review_failures(state))
        if state.scenario not in VALID_SCENARIOS:
            failures.append(f"negative scenario was accepted: {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid sequential parent replay review route was rejected")
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
        "parent_replay_closes_only_after_independent_review",
        "Parent replay closure, PM segment decisions, and terminal replay require an accepted independent review.",
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((SequentialParentReplayReviewStep(),), name="flowpilot_sequential_parent_replay_review")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def intended_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in VALID_SCENARIOS}
