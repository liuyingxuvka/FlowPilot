"""FlowGuard model for FlowPilot route replanning versus repair policy.

Risk intent brief:
- Validate the route-control repair before FlowPilot router, PM cards, or
  runtime templates are changed.
- Protected harms: planning-phase gaps being converted into executable repair
  nodes, missing product/process model gates after capability or route changes,
  active nodes that cannot be executed, stale approvals after route mutation,
  and Controller compensation by direct product implementation.
- Modeled state and side effects: root planning, node-entry replanning,
  in-progress replanning, review-failure repair, Product FlowGuard checks,
  Process FlowGuard checks, Reviewer approval, stale evidence handling, and
  route activation/use.
- Hard invariants: planning issues are fixed by route rewrites or ordinary node
  additions; repair nodes require reviewed failure evidence; product capability
  changes run Product FlowGuard before Process FlowGuard; every structure change
  runs Process FlowGuard; every changed route is reviewed before use; every
  active node is executable before entry; Controller never substitutes for route
  gates by doing product work.
- Blindspot: this model checks the abstract policy. Production router/card
  code and ProjectRadar replay evidence must still validate implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_PLANNING_REPLAN = "valid_planning_replan"
VALID_PLANNING_CAPABILITY_EXPANSION = "valid_planning_capability_expansion"
VALID_NODE_ENTRY_REPLAN = "valid_node_entry_replan"
VALID_IN_PROGRESS_REPLAN = "valid_in_progress_replan"
VALID_REVIEW_FAILURE_REPAIR = "valid_review_failure_repair"
VALID_REVIEW_FAILURE_LOCAL_PATCH = "valid_review_failure_local_patch"

PLANNING_REPAIR_NODE_CREATED = "planning_repair_node_created"
ROOT_REPAIR_BEFORE_CHILD_EXECUTION = "root_repair_before_child_execution"
ORDINARY_NODE_MISSING_FIELDS = "ordinary_node_missing_fields"
CAPABILITY_CHANGE_WITHOUT_PRODUCT_CHECK = "capability_change_without_product_check"
PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE = "process_before_product_for_capability_change"
STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK = "structure_change_without_process_check"
CHANGED_ROUTE_WITHOUT_REVIEWER = "changed_route_without_reviewer"
NODE_ENTRY_REPAIR_BEFORE_WORK = "node_entry_repair_before_work"
IN_PROGRESS_REPAIR_BEFORE_REVIEW_FAILURE = "in_progress_repair_before_review_failure"
REPAIR_NODE_MISSING_FIELDS = "repair_node_missing_fields"
REPAIR_WITHOUT_STALE_RESET = "repair_without_stale_reset"
REPAIR_WITHOUT_MAINLINE_RETURN = "repair_without_mainline_return"
ACTIVE_NODE_NOT_EXECUTABLE = "active_node_not_executable"
CONTROLLER_DIRECT_IMPLEMENTATION = "controller_direct_implementation"
STALE_APPROVAL_REUSED_AFTER_CHANGE = "stale_approval_reused_after_change"

VALID_SCENARIOS = (
    VALID_PLANNING_REPLAN,
    VALID_PLANNING_CAPABILITY_EXPANSION,
    VALID_NODE_ENTRY_REPLAN,
    VALID_IN_PROGRESS_REPLAN,
    VALID_REVIEW_FAILURE_REPAIR,
    VALID_REVIEW_FAILURE_LOCAL_PATCH,
)
NEGATIVE_SCENARIOS = (
    PLANNING_REPAIR_NODE_CREATED,
    ROOT_REPAIR_BEFORE_CHILD_EXECUTION,
    ORDINARY_NODE_MISSING_FIELDS,
    CAPABILITY_CHANGE_WITHOUT_PRODUCT_CHECK,
    PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE,
    STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK,
    CHANGED_ROUTE_WITHOUT_REVIEWER,
    NODE_ENTRY_REPAIR_BEFORE_WORK,
    IN_PROGRESS_REPAIR_BEFORE_REVIEW_FAILURE,
    REPAIR_NODE_MISSING_FIELDS,
    REPAIR_WITHOUT_STALE_RESET,
    REPAIR_WITHOUT_MAINLINE_RETURN,
    ACTIVE_NODE_NOT_EXECUTABLE,
    CONTROLLER_DIRECT_IMPLEMENTATION,
    STALE_APPROVAL_REUSED_AFTER_CHANGE,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS

STRUCTURE_CHANGES = {
    "route_rewrite",
    "add_normal_node",
    "add_parallel_node",
    "add_child_node",
    "node_internal_replan",
    "repair_node",
}
PLANNING_CHANGES = {"route_rewrite", "add_normal_node", "add_parallel_node", "add_child_node"}


@dataclass(frozen=True)
class Tick:
    """One abstract route-policy evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    phase: str = "unset"  # planning | node_entry | node_in_progress | review_failure
    issue_kind: str = "none"  # planning_gap | capability_gap | structure_gap | review_failure
    route_started: bool = False
    completed_nodes: int = 0
    current_node_kind: str = "none"  # root | parent | module | leaf | repair
    target_node_started: bool = False
    target_node_result_submitted: bool = False
    reviewer_failure_recorded: bool = False

    change_kind: str = "none"  # route_rewrite | add_normal_node | add_parallel_node | add_child_node | node_internal_replan | repair_node | local_patch
    repair_node_created: bool = False
    ordinary_node_added: bool = False
    added_node_fields_complete: bool = False
    repair_fields_complete: bool = False
    stale_evidence_reset: bool = False
    mainline_return_defined: bool = False
    rerun_obligations_defined: bool = False

    product_capability_changed: bool = False
    product_flowguard_checked: bool = False
    product_flowguard_before_process: bool = False
    process_flowguard_checked: bool = False
    reviewer_approved_changed_route: bool = False
    old_approval_reused_after_change: bool = False

    active_node_executable: bool = False
    pm_activated_or_used_route: bool = False
    controller_direct_product_work: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RouteReplanningPolicyStep:
    """Model one FlowPilot route replanning decision.

    Input x State -> Set(Output x State)
    reads: phase, issue kind, route started/completed state, change kind,
    product/process/reviewer gates, active-node executability, repair metadata
    writes: terminal policy decision
    idempotency: scenario facts are monotonic; terminal decisions do not change
    on repeated ticks.
    """

    name = "RouteReplanningPolicyStep"
    input_description = "FlowPilot route replanning policy tick"
    output_description = "one route-policy transition"
    reads = (
        "phase",
        "issue_kind",
        "route_started",
        "completed_nodes",
        "change_kind",
        "product_flowguard_checked",
        "process_flowguard_checked",
        "reviewer_approved_changed_route",
        "active_node_executable",
        "repair_fields_complete",
    )
    writes = ("terminal_route_policy_decision",)
    idempotency = "monotonic route policy evaluation"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def initial_state() -> State:
    return State()


def _valid_planning_replan() -> State:
    return State(
        status="running",
        scenario=VALID_PLANNING_REPLAN,
        phase="planning",
        issue_kind="planning_gap",
        route_started=False,
        completed_nodes=0,
        current_node_kind="root",
        change_kind="route_rewrite",
        added_node_fields_complete=True,
        process_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_planning_capability_expansion() -> State:
    return State(
        status="running",
        scenario=VALID_PLANNING_CAPABILITY_EXPANSION,
        phase="planning",
        issue_kind="capability_gap",
        route_started=False,
        completed_nodes=0,
        current_node_kind="root",
        change_kind="add_child_node",
        ordinary_node_added=True,
        added_node_fields_complete=True,
        product_capability_changed=True,
        product_flowguard_checked=True,
        product_flowguard_before_process=True,
        process_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_node_entry_replan() -> State:
    return State(
        status="running",
        scenario=VALID_NODE_ENTRY_REPLAN,
        phase="node_entry",
        issue_kind="capability_gap",
        route_started=True,
        completed_nodes=0,
        current_node_kind="module",
        target_node_started=False,
        change_kind="add_child_node",
        ordinary_node_added=True,
        added_node_fields_complete=True,
        product_capability_changed=True,
        product_flowguard_checked=True,
        product_flowguard_before_process=True,
        process_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_in_progress_replan() -> State:
    return State(
        status="running",
        scenario=VALID_IN_PROGRESS_REPLAN,
        phase="node_in_progress",
        issue_kind="capability_gap",
        route_started=True,
        completed_nodes=0,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=False,
        change_kind="node_internal_replan",
        added_node_fields_complete=True,
        process_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_review_failure_repair() -> State:
    return State(
        status="running",
        scenario=VALID_REVIEW_FAILURE_REPAIR,
        phase="review_failure",
        issue_kind="review_failure",
        route_started=True,
        completed_nodes=0,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=True,
        reviewer_failure_recorded=True,
        change_kind="repair_node",
        repair_node_created=True,
        repair_fields_complete=True,
        stale_evidence_reset=True,
        mainline_return_defined=True,
        rerun_obligations_defined=True,
        process_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_review_failure_local_patch() -> State:
    return State(
        status="running",
        scenario=VALID_REVIEW_FAILURE_LOCAL_PATCH,
        phase="review_failure",
        issue_kind="review_failure",
        route_started=True,
        completed_nodes=0,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=True,
        reviewer_failure_recorded=True,
        change_kind="local_patch",
        stale_evidence_reset=True,
        mainline_return_defined=True,
        rerun_obligations_defined=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _scenario_state(scenario: str) -> State:
    if scenario == VALID_PLANNING_REPLAN:
        return _valid_planning_replan()
    if scenario == VALID_PLANNING_CAPABILITY_EXPANSION:
        return _valid_planning_capability_expansion()
    if scenario == VALID_NODE_ENTRY_REPLAN:
        return _valid_node_entry_replan()
    if scenario == VALID_IN_PROGRESS_REPLAN:
        return _valid_in_progress_replan()
    if scenario == VALID_REVIEW_FAILURE_REPAIR:
        return _valid_review_failure_repair()
    if scenario == VALID_REVIEW_FAILURE_LOCAL_PATCH:
        return _valid_review_failure_local_patch()

    state = _valid_planning_capability_expansion()
    if scenario == PLANNING_REPAIR_NODE_CREATED:
        return replace(
            _valid_planning_replan(),
            scenario=scenario,
            change_kind="repair_node",
            repair_node_created=True,
            repair_fields_complete=True,
            mainline_return_defined=True,
            stale_evidence_reset=True,
        )
    if scenario == ROOT_REPAIR_BEFORE_CHILD_EXECUTION:
        return replace(
            _valid_planning_replan(),
            scenario=scenario,
            current_node_kind="root",
            completed_nodes=0,
            repair_node_created=True,
            change_kind="repair_node",
        )
    if scenario == ORDINARY_NODE_MISSING_FIELDS:
        return replace(state, scenario=scenario, added_node_fields_complete=False)
    if scenario == CAPABILITY_CHANGE_WITHOUT_PRODUCT_CHECK:
        return replace(state, scenario=scenario, product_flowguard_checked=False)
    if scenario == PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE:
        return replace(state, scenario=scenario, product_flowguard_before_process=False)
    if scenario == STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK:
        return replace(state, scenario=scenario, process_flowguard_checked=False)
    if scenario == CHANGED_ROUTE_WITHOUT_REVIEWER:
        return replace(state, scenario=scenario, reviewer_approved_changed_route=False)
    if scenario == NODE_ENTRY_REPAIR_BEFORE_WORK:
        return replace(
            _valid_node_entry_replan(),
            scenario=scenario,
            change_kind="repair_node",
            repair_node_created=True,
            repair_fields_complete=True,
        )
    if scenario == IN_PROGRESS_REPAIR_BEFORE_REVIEW_FAILURE:
        return replace(
            _valid_in_progress_replan(),
            scenario=scenario,
            change_kind="repair_node",
            repair_node_created=True,
            repair_fields_complete=True,
            reviewer_failure_recorded=False,
        )
    if scenario == REPAIR_NODE_MISSING_FIELDS:
        return replace(_valid_review_failure_repair(), scenario=scenario, repair_fields_complete=False)
    if scenario == REPAIR_WITHOUT_STALE_RESET:
        return replace(_valid_review_failure_repair(), scenario=scenario, stale_evidence_reset=False)
    if scenario == REPAIR_WITHOUT_MAINLINE_RETURN:
        return replace(_valid_review_failure_repair(), scenario=scenario, mainline_return_defined=False)
    if scenario == ACTIVE_NODE_NOT_EXECUTABLE:
        return replace(state, scenario=scenario, active_node_executable=False)
    if scenario == CONTROLLER_DIRECT_IMPLEMENTATION:
        return replace(state, scenario=scenario, controller_direct_product_work=True)
    if scenario == STALE_APPROVAL_REUSED_AFTER_CHANGE:
        return replace(state, scenario=scenario, old_approval_reused_after_change=True)
    return state


def _route_structure_changed(state: State) -> bool:
    return state.change_kind in STRUCTURE_CHANGES


def _changed_route_or_node(state: State) -> bool:
    return state.change_kind != "none" or state.product_capability_changed


def policy_failures(state: State) -> list[str]:
    failures: list[str] = []

    if (
        state.phase == "planning"
        and not state.route_started
        and state.issue_kind in {"planning_gap", "capability_gap", "structure_gap"}
        and state.repair_node_created
    ):
        failures.append("planning-phase issue used a repair node instead of route draft rewrite or ordinary node expansion")
    if (
        state.phase == "planning"
        and state.current_node_kind == "root"
        and state.completed_nodes == 0
        and state.repair_node_created
    ):
        failures.append("root planning created a repair node before any child execution")
    if (
        state.ordinary_node_added or state.change_kind in PLANNING_CHANGES
    ) and not state.added_node_fields_complete:
        failures.append("added ordinary node lacks owner input output evidence or acceptance fields")
    if state.product_capability_changed and not state.product_flowguard_checked:
        failures.append("product capability change lacks Product FlowGuard check")
    if (
        state.product_capability_changed
        and state.process_flowguard_checked
        and not state.product_flowguard_before_process
    ):
        failures.append("Process FlowGuard ran before Product FlowGuard for a product capability change")
    if _route_structure_changed(state) and not state.process_flowguard_checked:
        failures.append("route structure change lacks Process FlowGuard check")
    if _changed_route_or_node(state) and state.pm_activated_or_used_route and not state.reviewer_approved_changed_route:
        failures.append("changed route was used before Reviewer approval")
    if (
        state.phase == "node_entry"
        and not state.target_node_started
        and state.repair_node_created
    ):
        failures.append("node-entry capability gap used a repair node before node work started")
    if (
        state.phase == "node_in_progress"
        and state.repair_node_created
        and not state.reviewer_failure_recorded
    ):
        failures.append("in-progress capability gap used a repair node before reviewed failure")
    if state.repair_node_created:
        if not (state.reviewer_failure_recorded and state.phase == "review_failure"):
            failures.append("repair node lacks reviewed failure trigger")
        if not state.repair_fields_complete:
            failures.append("repair node lacks target reason input output evidence return or recheck fields")
        if not state.stale_evidence_reset:
            failures.append("repair node lacks stale evidence reset")
        if not state.mainline_return_defined:
            failures.append("repair node lacks mainline return")
        if not state.rerun_obligations_defined:
            failures.append("repair node lacks rerun obligations")
    if state.pm_activated_or_used_route and not state.active_node_executable:
        failures.append("active node is not executable before route use")
    if state.controller_direct_product_work:
        failures.append("Controller performed product work before route gate")
    if state.old_approval_reused_after_change and _changed_route_or_node(state):
        failures.append("old approval was reused after route or product change")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = policy_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="route_replanning_policy_ok"),
        )


def accepts_only_valid_route_policies(state: State, trace) -> InvariantResult:
    del trace
    failures = policy_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid route replanning policy was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid route replanning policy was rejected")
    return InvariantResult.pass_()


def planning_gaps_do_not_create_repairs(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in policy_failures(state):
        if "planning" in failure or "before any child execution" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def model_gates_cover_changed_routes(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in policy_failures(state):
        if "FlowGuard" in failure or "Reviewer" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def repair_nodes_are_post_failure_and_complete(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in policy_failures(state):
        if "repair node" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def route_use_requires_executable_active_node(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.pm_activated_or_used_route and not state.active_node_executable:
        return InvariantResult.fail("active node is not executable before route use")
    return InvariantResult.pass_()


def controller_remains_relay_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted" and state.controller_direct_product_work:
        return InvariantResult.fail("Controller performed product work before route gate")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_route_policies",
        description="Only route changes with the right replanning/repair classification and gates are accepted.",
        predicate=accepts_only_valid_route_policies,
    ),
    Invariant(
        name="planning_gaps_do_not_create_repairs",
        description="Planning-phase gaps rewrite route drafts or add ordinary nodes instead of creating repair nodes.",
        predicate=planning_gaps_do_not_create_repairs,
    ),
    Invariant(
        name="model_gates_cover_changed_routes",
        description="Product capability and route-structure changes run Product/Process FlowGuard and Reviewer gates before use.",
        predicate=model_gates_cover_changed_routes,
    ),
    Invariant(
        name="repair_nodes_are_post_failure_and_complete",
        description="Repair nodes require reviewed failure evidence and complete repair metadata.",
        predicate=repair_nodes_are_post_failure_and_complete,
    ),
    Invariant(
        name="route_use_requires_executable_active_node",
        description="Changed routes cannot be used until the active node is executable.",
        predicate=route_use_requires_executable_active_node,
    ),
    Invariant(
        name="controller_remains_relay_only",
        description="Controller cannot compensate for route gate problems by doing product work.",
        predicate=controller_remains_relay_only,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((RouteReplanningPolicyStep(),), name="flowpilot_route_replanning_policy")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not policy_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "policy_failures",
]
