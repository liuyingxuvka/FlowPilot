"""FlowGuard model for FlowPilot legal next-action policy.

Risk purpose:
- This FlowGuard model reviews the FlowPilot Router boundary that computes
  legal route actions before PM decisions, validates PM submissions, and
  validates route/frontier commits.
- It guards against PM seeing or selecting parent closure, route jump, route
  mutation, or terminal closure actions before the current route/frontier/ledger
  state permits them.
- Future agents should run
  `python simulations/run_flowpilot_legal_next_action_checks.py` before changing
  Router PM decision waits, legal route-action policy rows, parent closure,
  route mutation, terminal closure, or model-mesh continuation claims.
- This model complements, rather than replaces, the parent/child lifecycle and
  control transaction registry models.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_CONTINUE_CHILD = "valid_continue_child"
VALID_PARENT_COMPLETION = "valid_parent_completion"
VALID_ROUTE_MUTATION = "valid_route_mutation"
VALID_TERMINAL_CLOSURE = "valid_terminal_closure"

PM_DECISION_WITHOUT_LEGAL_ACTIONS = "pm_decision_requested_without_legal_actions"
PARENT_CLOSURE_OFFERED_BEFORE_CHILD_CHAIN_CLOSED = "parent_closure_offered_before_child_chain_closed"
SEGMENT_DECISION_OFFERED_BEFORE_PARENT_REPLAY_PASS = "segment_decision_offered_before_parent_replay_pass"
DIRECT_CHILD_DONE_USED_AS_SUBTREE_DONE = "direct_child_done_used_as_subtree_done"
STALE_CHILD_COMPLETION_AUTHORITY = "stale_child_completion_authority"
PM_SELECTED_ACTION_OUTSIDE_LEGAL_SET = "pm_selected_action_outside_legal_set"
EVENT_REGISTERED_BUT_ACTION_ILLEGAL = "event_registered_but_action_illegal"
STALE_LEGAL_ACTION_SNAPSHOT_COMMITTED = "stale_legal_action_snapshot_committed"
POLICY_REGISTRY_REFERENCE_MISSING = "policy_registry_reference_missing"
ACTION_NODE_KIND_MISMATCH = "action_node_kind_mismatch"
ROUTE_MUTATION_WITHOUT_STALE_EVIDENCE_POLICY = "route_mutation_without_stale_evidence_policy"
TERMINAL_CLOSURE_OFFERED_WITH_OPEN_ROUTE_WORK = "terminal_closure_offered_with_open_route_work"
PM_WORK_REQUEST_BYPASSES_ROUTE_ACTION_POLICY = "pm_work_request_bypasses_route_action_policy"
LEGAL_ACTION_PARTIAL_COMMIT = "legal_action_partial_commit"
MESH_GREEN_WITHOUT_LEGAL_ACTION_PROJECTION = "mesh_green_without_legal_action_projection"

VALID_SCENARIOS = (
    VALID_CONTINUE_CHILD,
    VALID_PARENT_COMPLETION,
    VALID_ROUTE_MUTATION,
    VALID_TERMINAL_CLOSURE,
)
NEGATIVE_SCENARIOS = (
    PM_DECISION_WITHOUT_LEGAL_ACTIONS,
    PARENT_CLOSURE_OFFERED_BEFORE_CHILD_CHAIN_CLOSED,
    SEGMENT_DECISION_OFFERED_BEFORE_PARENT_REPLAY_PASS,
    DIRECT_CHILD_DONE_USED_AS_SUBTREE_DONE,
    STALE_CHILD_COMPLETION_AUTHORITY,
    PM_SELECTED_ACTION_OUTSIDE_LEGAL_SET,
    EVENT_REGISTERED_BUT_ACTION_ILLEGAL,
    STALE_LEGAL_ACTION_SNAPSHOT_COMMITTED,
    POLICY_REGISTRY_REFERENCE_MISSING,
    ACTION_NODE_KIND_MISMATCH,
    ROUTE_MUTATION_WITHOUT_STALE_EVIDENCE_POLICY,
    TERMINAL_CLOSURE_OFFERED_WITH_OPEN_ROUTE_WORK,
    PM_WORK_REQUEST_BYPASSES_ROUTE_ACTION_POLICY,
    LEGAL_ACTION_PARTIAL_COMMIT,
    MESH_GREEN_WITHOUT_LEGAL_ACTION_PROJECTION,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

PARENT_CLOSURE_ACTIONS = frozenset(
    {
        "build_parent_backward_targets",
        "review_parent_backward_replay",
        "record_parent_segment_decision",
        "complete_parent_node",
    }
)
ROUTE_MOVEMENT_ACTIONS = frozenset(
    {
        "continue_current_child",
        "enter_next_child",
        "wait_for_child_result",
        "request_child_repair",
        "build_parent_backward_targets",
        "record_parent_segment_decision",
        "complete_parent_node",
        "mutate_route",
        "terminal_closure",
    }
)


@dataclass(frozen=True)
class Tick:
    """One legal-next-action policy evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | selected | accepted | rejected
    scenario: str = "unset"

    legal_actions_computed: bool = False
    legal_actions_bound_to_route_frontier: bool = True
    legal_action_snapshot_current: bool = True
    legal_actions_include_selected: bool = True
    pm_decision_requested: bool = False
    pm_selected_action: str = "none"
    pm_work_request_channel_used: bool = False
    pm_work_request_route_action_guarded: bool = True

    policy_row_present: bool = True
    policy_references_exist: bool = True
    event_registered: bool = True
    output_contract_registered: bool = True
    control_transaction_registered: bool = True
    event_currently_allowed: bool = True
    action_predicate_true: bool = True

    active_node_kind: str = "leaf"  # leaf | repair | parent | module | terminal
    action_node_kind_ok: bool = True
    active_child_exists: bool = True
    child_frontier_entered: bool = True
    child_leaf_executed: bool = True
    direct_child_completed: bool = True
    descendant_leaves_completed: bool = True
    effective_children_all_completed: bool = True
    child_completion_ledger_current: bool = True
    stale_route_status_used: bool = False
    parent_backward_replay_passed: bool = True
    parent_segment_decision_continue: bool = True

    route_mutation_requested: bool = False
    stale_evidence_policy_applied: bool = True
    affected_parent_replay_rerun_required: bool = True

    open_route_nodes: bool = False
    active_blocker_present: bool = False
    stale_evidence_present: bool = False

    commit_attempted: bool = True
    commit_targets_complete: bool = True
    route_frontier_ledger_versions_match_at_commit: bool = True

    legal_action_projection_available_to_mesh: bool = True
    mesh_green_claimed: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class LegalNextActionStep:
    """Classify one legal route-action policy scenario.

    Input x State -> Set(Output x State)
    reads: route, execution frontier, completion ledger, pending Router action,
    policy registry rows, output contracts, event capability, transaction rows
    writes: legal action decision and accepted/rejected policy result
    idempotency: classification is pure for a route/frontier/ledger version.
    """

    name = "LegalNextActionStep"
    input_description = "FlowPilot legal next-action policy tick"
    output_description = "one accepted or rejected legal-action policy state"
    reads = (
        "route_action_policy_registry",
        "execution_frontier",
        "route_flow",
        "node_completion_ledger",
        "router_pending_action",
        "contract_registry",
        "event_capability_registry",
        "control_transaction_registry",
    )
    writes = ("legal_next_action_decision",)
    idempotency = "pure classification by route id/version, frontier version, and selected action"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _valid_continue_child() -> State:
    return State(
        status="selected",
        scenario=VALID_CONTINUE_CHILD,
        legal_actions_computed=True,
        pm_decision_requested=True,
        pm_selected_action="continue_current_child",
        active_node_kind="leaf",
        active_child_exists=True,
        child_frontier_entered=True,
        child_leaf_executed=True,
        direct_child_completed=False,
        descendant_leaves_completed=False,
        effective_children_all_completed=False,
        child_completion_ledger_current=True,
        commit_attempted=False,
    )


def _valid_parent_completion() -> State:
    return State(
        status="selected",
        scenario=VALID_PARENT_COMPLETION,
        legal_actions_computed=True,
        pm_decision_requested=True,
        pm_selected_action="complete_parent_node",
        active_node_kind="parent",
        active_child_exists=True,
        child_frontier_entered=True,
        child_leaf_executed=True,
        direct_child_completed=True,
        descendant_leaves_completed=True,
        effective_children_all_completed=True,
        child_completion_ledger_current=True,
        parent_backward_replay_passed=True,
        parent_segment_decision_continue=True,
        commit_attempted=True,
    )


def _valid_route_mutation() -> State:
    return State(
        status="selected",
        scenario=VALID_ROUTE_MUTATION,
        legal_actions_computed=True,
        pm_decision_requested=True,
        pm_selected_action="mutate_route",
        active_node_kind="parent",
        route_mutation_requested=True,
        stale_evidence_policy_applied=True,
        affected_parent_replay_rerun_required=True,
        commit_attempted=True,
    )


def _valid_terminal_closure() -> State:
    return State(
        status="selected",
        scenario=VALID_TERMINAL_CLOSURE,
        legal_actions_computed=True,
        pm_decision_requested=True,
        pm_selected_action="terminal_closure",
        active_node_kind="terminal",
        active_child_exists=False,
        open_route_nodes=False,
        active_blocker_present=False,
        stale_evidence_present=False,
        commit_attempted=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_CONTINUE_CHILD:
        return _valid_continue_child()
    if scenario == VALID_PARENT_COMPLETION:
        return _valid_parent_completion()
    if scenario == VALID_ROUTE_MUTATION:
        return _valid_route_mutation()
    if scenario == VALID_TERMINAL_CLOSURE:
        return _valid_terminal_closure()

    state = _valid_parent_completion()
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == PM_DECISION_WITHOUT_LEGAL_ACTIONS:
        updates.update(legal_actions_computed=False, pm_decision_requested=True)
    elif scenario == PARENT_CLOSURE_OFFERED_BEFORE_CHILD_CHAIN_CLOSED:
        updates.update(
            pm_selected_action="complete_parent_node",
            child_frontier_entered=True,
            child_leaf_executed=True,
            direct_child_completed=False,
            descendant_leaves_completed=False,
            effective_children_all_completed=False,
            child_completion_ledger_current=False,
        )
    elif scenario == SEGMENT_DECISION_OFFERED_BEFORE_PARENT_REPLAY_PASS:
        updates.update(pm_selected_action="record_parent_segment_decision", parent_backward_replay_passed=False)
    elif scenario == DIRECT_CHILD_DONE_USED_AS_SUBTREE_DONE:
        updates.update(
            pm_selected_action="complete_parent_node",
            direct_child_completed=True,
            descendant_leaves_completed=False,
            effective_children_all_completed=True,
        )
    elif scenario == STALE_CHILD_COMPLETION_AUTHORITY:
        updates.update(
            pm_selected_action="complete_parent_node",
            child_completion_ledger_current=False,
            stale_route_status_used=True,
        )
    elif scenario == PM_SELECTED_ACTION_OUTSIDE_LEGAL_SET:
        updates.update(pm_selected_action="complete_parent_node", legal_actions_include_selected=False)
    elif scenario == EVENT_REGISTERED_BUT_ACTION_ILLEGAL:
        updates.update(
            pm_selected_action="complete_parent_node",
            event_registered=True,
            event_currently_allowed=True,
            action_predicate_true=False,
        )
    elif scenario == STALE_LEGAL_ACTION_SNAPSHOT_COMMITTED:
        updates.update(
            pm_selected_action="complete_parent_node",
            legal_action_snapshot_current=False,
            route_frontier_ledger_versions_match_at_commit=False,
        )
    elif scenario == POLICY_REGISTRY_REFERENCE_MISSING:
        updates.update(
            policy_row_present=True,
            policy_references_exist=False,
            output_contract_registered=False,
            control_transaction_registered=False,
        )
    elif scenario == ACTION_NODE_KIND_MISMATCH:
        updates.update(pm_selected_action="complete_parent_node", active_node_kind="leaf", action_node_kind_ok=False)
    elif scenario == ROUTE_MUTATION_WITHOUT_STALE_EVIDENCE_POLICY:
        updates.update(
            pm_selected_action="mutate_route",
            route_mutation_requested=True,
            stale_evidence_policy_applied=False,
            affected_parent_replay_rerun_required=False,
        )
    elif scenario == TERMINAL_CLOSURE_OFFERED_WITH_OPEN_ROUTE_WORK:
        updates.update(
            pm_selected_action="terminal_closure",
            active_node_kind="terminal",
            open_route_nodes=True,
            active_blocker_present=True,
            stale_evidence_present=True,
        )
    elif scenario == PM_WORK_REQUEST_BYPASSES_ROUTE_ACTION_POLICY:
        updates.update(
            pm_selected_action="complete_parent_node",
            pm_work_request_channel_used=True,
            pm_work_request_route_action_guarded=False,
        )
    elif scenario == LEGAL_ACTION_PARTIAL_COMMIT:
        updates.update(pm_selected_action="complete_parent_node", commit_targets_complete=False)
    elif scenario == MESH_GREEN_WITHOUT_LEGAL_ACTION_PROJECTION:
        updates.update(legal_action_projection_available_to_mesh=False, mesh_green_claimed=True)
    else:
        raise KeyError(f"unknown scenario: {scenario}")
    return replace(state, **updates)


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"accepted", "rejected"}:
        return ()
    if state.status == "new":
        return tuple(
            Transition(
                label=f"select_{scenario}",
                state=_scenario_state(scenario),
            )
            for scenario in SCENARIOS
        )
    failures = legal_action_failures(state)
    if failures:
        return (
            Transition(
                label=f"reject_{state.scenario}",
                state=replace(state, status="rejected", terminal_reason="; ".join(failures)),
            ),
        )
    return (
        Transition(
            label=f"accept_{state.scenario}",
            state=replace(state, status="accepted", terminal_reason="legal_action_policy_valid"),
        ),
    )


def _is_parent_closure_action(action: str) -> bool:
    return action in PARENT_CLOSURE_ACTIONS


def legal_action_failures(state: State) -> list[str]:
    failures: list[str] = []
    action = state.pm_selected_action

    if state.pm_decision_requested and not state.legal_actions_computed:
        failures.append("PM decision was requested before legal next actions were computed")
    if state.legal_actions_computed and not state.legal_actions_bound_to_route_frontier:
        failures.append("legal next actions were not bound to current route and frontier")
    if state.pm_decision_requested and not state.legal_actions_include_selected:
        failures.append("PM selected an action outside the Router legal action set")
    if state.pm_work_request_channel_used and not state.pm_work_request_route_action_guarded:
        failures.append("PM work-request channel bypassed route-action policy")

    if not state.policy_row_present:
        failures.append("route action policy row is missing")
    if not state.policy_references_exist:
        failures.append("route action policy references missing contract, event, or transaction")
    if not state.event_registered or not state.output_contract_registered or not state.control_transaction_registered:
        failures.append("route action policy references missing contract, event, or transaction")
    if state.event_registered and state.event_currently_allowed and not state.action_predicate_true:
        failures.append("registered event was allowed while route action predicate was false")
    if not state.action_node_kind_ok:
        failures.append("route action is incompatible with active node kind")

    child_chain_closed = (
        state.child_frontier_entered
        and state.child_leaf_executed
        and state.direct_child_completed
        and state.descendant_leaves_completed
        and state.effective_children_all_completed
        and state.child_completion_ledger_current
        and not state.stale_route_status_used
    )
    if _is_parent_closure_action(action) and not child_chain_closed:
        failures.append("parent closure action was offered before child chain closed")
    if action == "record_parent_segment_decision" and not state.parent_backward_replay_passed:
        failures.append("parent segment decision was offered before parent backward replay passed")
    if (
        _is_parent_closure_action(action)
        and state.direct_child_completed
        and not state.descendant_leaves_completed
        and state.effective_children_all_completed
    ):
        failures.append("direct child completion was used as subtree completion")
    if _is_parent_closure_action(action) and (not state.child_completion_ledger_current or state.stale_route_status_used):
        failures.append("stale child completion authority was used")

    if state.commit_attempted:
        if not state.legal_action_snapshot_current or not state.route_frontier_ledger_versions_match_at_commit:
            failures.append("stale legal-action snapshot was committed")
        if not state.commit_targets_complete:
            failures.append("legal action commit targets are incomplete")

    if state.route_mutation_requested and (
        not state.stale_evidence_policy_applied or not state.affected_parent_replay_rerun_required
    ):
        failures.append("route mutation omitted stale-evidence policy or parent replay rerun")
    if action == "terminal_closure" and (
        state.open_route_nodes or state.active_blocker_present or state.stale_evidence_present or state.active_child_exists
    ):
        failures.append("terminal closure was offered with open route work")
    if state.mesh_green_claimed and not state.legal_action_projection_available_to_mesh:
        failures.append("mesh green claim lacked legal-action projection")

    return failures


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted" and legal_action_failures(state):
        failures.append("accepted illegal route action policy")
    if state.status == "accepted" and state.scenario not in VALID_SCENARIOS:
        failures.append("negative scenario was accepted")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("valid scenario was rejected")
    return failures


def _invariant(name: str, description: str) -> Invariant:
    def _predicate(state: State, _trace):
        failures = invariant_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
        return InvariantResult.pass_()

    return Invariant(name=name, description=description, predicate=_predicate)


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def terminal_predicate(_input_obj: object, state: State, _trace: object) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow([LegalNextActionStep()])


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def intended_plan_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in VALID_SCENARIOS}


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    _invariant(
        "legal_next_action_policy_accepts_only_current_router_options",
        "PM route decisions must be requested, accepted, and committed only from the current legal next-action set.",
    ),
)
MAX_SEQUENCE_LENGTH = 2
