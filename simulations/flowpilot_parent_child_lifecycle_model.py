"""FlowGuard model for FlowPilot parent/child node lifecycle conformance.

Risk purpose:
- This FlowGuard model reviews the FlowPilot router boundary between non-leaf
  node entry, child execution, and non-leaf closure.
- It guards against the model miss where a live Router action triggers parent
  backward replay before entering or completing child nodes, plus same-class
  variants caused by stale route status, descendant omissions, route-version
  drift, and leaked current-node flags.
- Future agents should run
  `python simulations/run_flowpilot_parent_child_lifecycle_checks.py` before
  changing Router current-node scheduling, recursive route traversal, parent
  backward replay, node completion ledgers, or model-mesh conformance claims.
- This is a protocol-level model. Router runtime tests and live next-action
  conformance replay remain required before production fixes are trusted.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_PARENT_CHILD_LIFECYCLE = "valid_parent_child_lifecycle"
VALID_LEAF_LIFECYCLE = "valid_leaf_lifecycle"

PARENT_TARGETS_BEFORE_CHILD_ENTRY = "parent_targets_before_child_entry"
PARENT_REPLAY_BEFORE_CHILD_ENTRY = "parent_replay_before_child_entry"
PARENT_SEGMENT_BEFORE_CHILD_COMPLETION = "parent_segment_before_child_completion"
PARENT_COMPLETE_BEFORE_CHILD_COMPLETION = "parent_complete_before_child_completion"
NON_LEAF_ACCEPTANCE_STUCK_ON_PARENT = "non_leaf_acceptance_stuck_on_parent"
PARENT_DISPATCHES_WORKER_PACKET = "parent_dispatches_worker_packet"
DIRECT_CHILD_DONE_DESCENDANT_PENDING = "direct_child_done_descendant_pending"
STALE_ROUTE_STATUS_COUNTS_AS_CHILD_DONE = "stale_route_status_counts_as_child_done"
CHILD_COMPLETION_FROM_OLD_ROUTE_VERSION = "child_completion_from_old_route_version"
PARENT_FLAGS_LEAK_TO_CHILD = "parent_flags_leak_to_child"
ABSTRACT_GREEN_WITHOUT_LIVE_ACTION_REPLAY = "abstract_green_without_live_action_replay"
LIVE_ROUTER_ACTION_NOT_IN_MODEL = "live_router_action_not_in_model"

VALID_SCENARIOS = (
    VALID_PARENT_CHILD_LIFECYCLE,
    VALID_LEAF_LIFECYCLE,
)
NEGATIVE_SCENARIOS = (
    PARENT_TARGETS_BEFORE_CHILD_ENTRY,
    PARENT_REPLAY_BEFORE_CHILD_ENTRY,
    PARENT_SEGMENT_BEFORE_CHILD_COMPLETION,
    PARENT_COMPLETE_BEFORE_CHILD_COMPLETION,
    NON_LEAF_ACCEPTANCE_STUCK_ON_PARENT,
    PARENT_DISPATCHES_WORKER_PACKET,
    DIRECT_CHILD_DONE_DESCENDANT_PENDING,
    STALE_ROUTE_STATUS_COUNTS_AS_CHILD_DONE,
    CHILD_COMPLETION_FROM_OLD_ROUTE_VERSION,
    PARENT_FLAGS_LEAK_TO_CHILD,
    ABSTRACT_GREEN_WITHOUT_LIVE_ACTION_REPLAY,
    LIVE_ROUTER_ACTION_NOT_IN_MODEL,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One parent/child lifecycle evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    active_node_kind: str = "parent"  # parent | module | leaf | repair
    route_activated: bool = False
    active_route_version: int = 1
    child_completion_route_version: int = 1

    non_leaf_acceptance_plan_passed: bool = False
    child_frontier_entered: bool = False
    child_cycle_flags_reset: bool = False
    current_node_packet_registered: bool = False
    worker_leaf_execution_started: bool = False

    direct_children_completed: bool = False
    descendant_leaves_completed: bool = False
    effective_children_all_completed: bool = False
    child_completion_ledger_current: bool = False
    stale_route_status_used_for_completion: bool = False

    parent_backward_targets_requested: bool = False
    parent_backward_replay_requested: bool = False
    parent_backward_replay_passed: bool = False
    parent_segment_decision_requested: bool = False
    parent_segment_decision_recorded: bool = False
    parent_completed: bool = False

    parent_cycle_flags_visible_after_child_entry: bool = False
    live_router_next_action_replayed: bool = True
    live_router_next_action_known_to_model: bool = True
    abstract_model_green_used_to_continue: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ParentChildLifecycleStep:
    """One transition for parent/child lifecycle conformance.

    Input x State -> Set(Output x State)
    reads: active node kind, execution frontier, route topology, child
    completion ledger, live Router next-action projection, and current-node
    cycle flags
    writes: one accepted/rejected lifecycle conformance decision
    idempotency: scenario facts are immutable; terminal states remain terminal.
    """

    name = "ParentChildLifecycleStep"
    input_description = "FlowPilot parent/child lifecycle tick"
    output_description = "one lifecycle conformance transition"
    reads = (
        "execution_frontier",
        "route_flow",
        "node_completion_ledger",
        "router_next_action_projection",
        "current_node_cycle_flags",
    )
    writes = ("parent_child_lifecycle_decision",)
    idempotency = "pure lifecycle classification keyed by route version and active node"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _valid_parent_state() -> State:
    return State(
        status="running",
        scenario=VALID_PARENT_CHILD_LIFECYCLE,
        active_node_kind="parent",
        route_activated=True,
        non_leaf_acceptance_plan_passed=True,
        child_frontier_entered=True,
        child_cycle_flags_reset=True,
        worker_leaf_execution_started=True,
        direct_children_completed=True,
        descendant_leaves_completed=True,
        effective_children_all_completed=True,
        child_completion_ledger_current=True,
        parent_backward_targets_requested=True,
        parent_backward_replay_requested=True,
        parent_backward_replay_passed=True,
        parent_segment_decision_requested=True,
        parent_segment_decision_recorded=True,
        parent_completed=True,
        live_router_next_action_replayed=True,
        live_router_next_action_known_to_model=True,
    )


def _valid_leaf_state() -> State:
    return State(
        status="running",
        scenario=VALID_LEAF_LIFECYCLE,
        active_node_kind="leaf",
        route_activated=True,
        non_leaf_acceptance_plan_passed=False,
        current_node_packet_registered=True,
        worker_leaf_execution_started=True,
        direct_children_completed=False,
        descendant_leaves_completed=False,
        effective_children_all_completed=False,
        child_completion_ledger_current=True,
        live_router_next_action_replayed=True,
        live_router_next_action_known_to_model=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_PARENT_CHILD_LIFECYCLE:
        return _valid_parent_state()
    if scenario == VALID_LEAF_LIFECYCLE:
        return _valid_leaf_state()

    state = _valid_parent_state()
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == PARENT_TARGETS_BEFORE_CHILD_ENTRY:
        updates.update(
            child_frontier_entered=False,
            worker_leaf_execution_started=False,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_backward_targets_requested=True,
            parent_backward_replay_requested=False,
            parent_backward_replay_passed=False,
            parent_segment_decision_requested=False,
            parent_segment_decision_recorded=False,
            parent_completed=False,
        )
    elif scenario == PARENT_REPLAY_BEFORE_CHILD_ENTRY:
        updates.update(
            child_frontier_entered=False,
            worker_leaf_execution_started=False,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_backward_targets_requested=True,
            parent_backward_replay_requested=True,
            parent_backward_replay_passed=True,
            parent_segment_decision_requested=False,
            parent_segment_decision_recorded=False,
            parent_completed=False,
        )
    elif scenario == PARENT_SEGMENT_BEFORE_CHILD_COMPLETION:
        updates.update(
            child_frontier_entered=True,
            worker_leaf_execution_started=True,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_segment_decision_requested=True,
            parent_segment_decision_recorded=True,
            parent_completed=False,
        )
    elif scenario == PARENT_COMPLETE_BEFORE_CHILD_COMPLETION:
        updates.update(
            child_frontier_entered=True,
            worker_leaf_execution_started=True,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_completed=True,
        )
    elif scenario == NON_LEAF_ACCEPTANCE_STUCK_ON_PARENT:
        updates.update(
            non_leaf_acceptance_plan_passed=True,
            child_frontier_entered=False,
            worker_leaf_execution_started=False,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_backward_targets_requested=False,
            parent_backward_replay_requested=False,
            parent_backward_replay_passed=False,
            parent_segment_decision_requested=False,
            parent_segment_decision_recorded=False,
            parent_completed=False,
        )
    elif scenario == PARENT_DISPATCHES_WORKER_PACKET:
        updates.update(
            current_node_packet_registered=True,
            child_frontier_entered=False,
            worker_leaf_execution_started=False,
            direct_children_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
            parent_backward_targets_requested=False,
            parent_backward_replay_requested=False,
            parent_backward_replay_passed=False,
            parent_segment_decision_requested=False,
            parent_segment_decision_recorded=False,
            parent_completed=False,
        )
    elif scenario == DIRECT_CHILD_DONE_DESCENDANT_PENDING:
        updates.update(
            direct_children_completed=True,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
        )
    elif scenario == STALE_ROUTE_STATUS_COUNTS_AS_CHILD_DONE:
        updates.update(
            stale_route_status_used_for_completion=True,
            direct_children_completed=True,
            descendant_leaves_completed=True,
            effective_children_all_completed=True,
            child_completion_ledger_current=False,
        )
    elif scenario == CHILD_COMPLETION_FROM_OLD_ROUTE_VERSION:
        updates.update(
            child_completion_route_version=0,
            child_completion_ledger_current=False,
        )
    elif scenario == PARENT_FLAGS_LEAK_TO_CHILD:
        updates.update(
            child_frontier_entered=True,
            child_cycle_flags_reset=False,
            parent_cycle_flags_visible_after_child_entry=True,
            parent_backward_targets_requested=False,
            parent_backward_replay_requested=False,
            parent_backward_replay_passed=False,
            parent_segment_decision_requested=False,
            parent_segment_decision_recorded=False,
            parent_completed=False,
        )
    elif scenario == ABSTRACT_GREEN_WITHOUT_LIVE_ACTION_REPLAY:
        updates.update(
            live_router_next_action_replayed=False,
            abstract_model_green_used_to_continue=True,
        )
    elif scenario == LIVE_ROUTER_ACTION_NOT_IN_MODEL:
        updates.update(
            live_router_next_action_replayed=True,
            live_router_next_action_known_to_model=False,
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
        return tuple(
            Transition(f"select_{scenario}", _scenario_state(scenario))
            for scenario in SCENARIOS
        )
    failures = lifecycle_failures(state)
    if failures:
        return (Transition(f"reject_{state.scenario}", replace(state, status="rejected", terminal_reason=failures[0])),)
    return (Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="lifecycle_passed")),)


def _is_non_leaf(state: State) -> bool:
    return state.active_node_kind in {"parent", "module"}


def _parent_closure_requested(state: State) -> bool:
    return any(
        (
            state.parent_backward_targets_requested,
            state.parent_backward_replay_requested,
            state.parent_backward_replay_passed,
            state.parent_segment_decision_requested,
            state.parent_segment_decision_recorded,
            state.parent_completed,
        )
    )


def lifecycle_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.active_node_kind not in {"parent", "module", "leaf", "repair"}:
        failures.append("active node kind is outside the parent-child lifecycle model")
    if state.route_activated and state.abstract_model_green_used_to_continue and not state.live_router_next_action_replayed:
        failures.append("abstract model green was used without live Router next-action replay")
    if state.live_router_next_action_replayed and not state.live_router_next_action_known_to_model:
        failures.append("live Router next action was not covered by the conformance model")
    if _is_non_leaf(state) and state.current_node_packet_registered:
        failures.append("parent or module node attempted worker packet dispatch")
    if _is_non_leaf(state) and state.non_leaf_acceptance_plan_passed and not state.child_frontier_entered and not _parent_closure_requested(state):
        failures.append("non-leaf acceptance passed but Router did not enter a child subtree")
    if state.child_frontier_entered and not state.child_cycle_flags_reset:
        failures.append("child frontier entered without resetting parent current-node cycle flags")
    if state.parent_cycle_flags_visible_after_child_entry:
        failures.append("parent current-node flags leaked into child execution")
    if _parent_closure_requested(state):
        if not _is_non_leaf(state):
            failures.append("parent closure action requested for a leaf or repair node")
        if not state.child_frontier_entered:
            failures.append("parent closure action requested before child subtree entry")
        if not state.worker_leaf_execution_started:
            failures.append("parent closure action requested before child leaf execution")
        if not state.effective_children_all_completed:
            failures.append("parent closure action requested before all effective children completed")
        if state.direct_children_completed and not state.descendant_leaves_completed:
            failures.append("direct child completion was treated as subtree completion while descendants were pending")
        if state.stale_route_status_used_for_completion:
            failures.append("stale route status was used as child completion authority")
        if state.child_completion_route_version != state.active_route_version:
            failures.append("child completion ledger belongs to a stale route version")
        if not state.child_completion_ledger_current:
            failures.append("parent closure action requested before current child completion ledger")
    if state.parent_backward_replay_requested and not state.parent_backward_targets_requested:
        failures.append("parent backward replay requested before parent targets")
    if state.parent_backward_replay_passed and not state.parent_backward_replay_requested:
        failures.append("parent backward replay passed before replay request")
    if state.parent_segment_decision_requested and not state.parent_backward_replay_passed:
        failures.append("parent segment decision requested before parent backward replay passed")
    if state.parent_segment_decision_recorded and not state.parent_segment_decision_requested:
        failures.append("parent segment decision recorded before segment decision request")
    if state.parent_completed and not state.parent_segment_decision_recorded:
        failures.append("parent completed before PM parent segment decision")
    return failures


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted":
        failures.extend(lifecycle_failures(state))
        if state.scenario not in VALID_SCENARIOS:
            failures.append(f"negative scenario was accepted: {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid parent-child lifecycle was rejected")
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
        "parent_child_lifecycle_accepts_only_conformant_router_actions",
        "Parent/module entry, child execution, and parent closure must remain ordered and replay-backed.",
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow(
        (ParentChildLifecycleStep(),),
        name="flowpilot_parent_child_lifecycle",
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def intended_parent_state() -> State:
    return _valid_parent_state()


def intended_leaf_state() -> State:
    return _valid_leaf_state()


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}

