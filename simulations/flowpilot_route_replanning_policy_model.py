"""FlowGuard model for FlowPilot route replanning versus repair policy.

Risk intent brief:
- Validate the route-control repair before FlowPilot router, PM cards, or
  runtime templates are changed.
- Protected harms: planning-phase gaps being converted into executable repair
  nodes, missing product/process model gates after capability or route changes,
  active nodes that cannot be executed, stale approvals after route mutation,
  and Controller compensation by direct product implementation.
- Modeled state and side effects: root planning, node-entry replanning,
  in-progress replanning, direct PM historical-defect repair,
  review-failure repair, product-scope FlowGuard checks, route-scope FlowGuard
  checks, Reviewer approval, stale evidence handling, and route activation/use.
- Hard invariants: planning issues are fixed by route rewrites or ordinary node
  additions; post-work repair nodes require either a current reviewed failure
  or a structured PM historical-defect observation, and PM historical repair
  never fabricates a blocker; product capability changes run product-scope
  FlowGuard before route-scope FlowGuard; every structure change runs
  route-scope FlowGuard; every changed route is reviewed before use; every
  active node is executable before entry; Controller never substitutes for
  route gates by doing product work.
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
VALID_PM_HISTORICAL_DEFECT_REPAIR = "valid_pm_historical_defect_repair"
VALID_REVIEW_FAILURE_REPAIR = "valid_review_failure_repair"
VALID_REVIEW_FAILURE_LOCAL_PATCH = "valid_review_failure_local_patch"
VALID_MILESTONE_UNCHANGED_PLAN_RENEWAL = "valid_milestone_unchanged_plan_renewal"
VALID_MILESTONE_CHANGED_SUFFIX_RENEWAL = "valid_milestone_changed_suffix_renewal"
VALID_NESTED_CHILD_LOCAL_CLOSURE = "valid_nested_child_local_closure"
VALID_TERMINAL_EMPTY_PLAN_RENEWAL = "valid_terminal_empty_plan_renewal"
VALID_RESUME_CURRENT_MILESTONE_GATE = "valid_resume_current_milestone_gate"
VALID_MILESTONE_REVIEW_BLOCK_HOLDS_FRONTIER = "valid_milestone_review_block_holds_frontier"

PLANNING_REPAIR_NODE_CREATED = "planning_repair_node_created"
ROOT_REPAIR_BEFORE_CHILD_EXECUTION = "root_repair_before_child_execution"
ORDINARY_NODE_MISSING_FIELDS = "ordinary_node_missing_fields"
CAPABILITY_CHANGE_WITHOUT_PRODUCT_CHECK = "capability_change_without_product_check"
PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE = "process_before_product_for_capability_change"
STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK = "structure_change_without_process_check"
CHANGED_ROUTE_WITHOUT_REVIEWER = "changed_route_without_reviewer"
NODE_ENTRY_REPAIR_BEFORE_WORK = "node_entry_repair_before_work"
IN_PROGRESS_REPAIR_BEFORE_REVIEW_FAILURE = "in_progress_repair_before_review_failure"
PM_HISTORICAL_DEFECT_FORCED_THROUGH_BLOCKER = "pm_historical_defect_forced_through_blocker"
PM_HISTORICAL_DEFECT_WITHOUT_OBSERVATION = "pm_historical_defect_without_observation"
REPAIR_NODE_MISSING_FIELDS = "repair_node_missing_fields"
REPAIR_WITHOUT_STALE_RESET = "repair_without_stale_reset"
REPAIR_WITHOUT_MAINLINE_RETURN = "repair_without_mainline_return"
ACTIVE_NODE_NOT_EXECUTABLE = "active_node_not_executable"
CONTROLLER_DIRECT_IMPLEMENTATION = "controller_direct_implementation"
STALE_APPROVAL_REUSED_AFTER_CHANGE = "stale_approval_reused_after_change"
MILESTONE_ADVANCED_WITHOUT_RENEWAL = "milestone_advanced_without_renewal"
MILESTONE_AUDIT_MISSING = "milestone_audit_missing"
MILESTONE_REMAINING_PLAN_INCOMPLETE = "milestone_remaining_plan_incomplete"
MILESTONE_REMAINING_OBLIGATION_UNOWNED = "milestone_remaining_obligation_unowned"
MILESTONE_AUDIT_CONTRACT_HASH_MISSING = "milestone_audit_contract_hash_missing"
MILESTONE_COMPLETED_PREFIX_UNBOUND = "milestone_completed_prefix_unbound"
MILESTONE_REMAINING_OWNER_NODE_UNBOUND = "milestone_remaining_owner_node_unbound"
MILESTONE_CHECKER_IDENTITY_REUSED = "milestone_checker_identity_reused"
MILESTONE_FLOWGUARD_BYPASSED = "milestone_flowguard_bypassed"
MILESTONE_PM_ABSORPTION_BYPASSED = "milestone_pm_absorption_bypassed"
MILESTONE_REVIEWER_BYPASSED = "milestone_reviewer_bypassed"
MILESTONE_SYSTEM_VALIDATION_BYPASSED = "milestone_system_validation_bypassed"
MILESTONE_LOWEST_ACCEPTANCE_BYPASSED_GATE = "milestone_lowest_acceptance_bypassed_gate"
TERMINAL_EMPTY_PLAN_BYPASSED_CHALLENGE = "terminal_empty_plan_bypassed_challenge"
MILESTONE_CURRENTNESS_RECOVERY_USED_TEXT_MATCH = "milestone_currentness_recovery_used_text_match"
UNCHANGED_PLAN_BUMPED_ROUTE_VERSION = "unchanged_plan_bumped_route_version"
CHANGED_PLAN_KEPT_OLD_ROUTE_VERSION = "changed_plan_kept_old_route_version"
CHANGED_PLAN_LOST_COMPLETED_PREFIX = "changed_plan_lost_completed_prefix"
PREMATURE_TERMINAL_EMPTY_PLAN = "premature_terminal_empty_plan"
RESUME_REUSED_HISTORICAL_MILESTONE_REVIEW = "resume_reused_historical_milestone_review"
NESTED_CHILD_FORCED_GLOBAL_RENEWAL = "nested_child_forced_global_renewal"
MILESTONE_REUSED_OLD_PLAN_WITHOUT_FRESH_WRITE = "milestone_reused_old_plan_without_fresh_write"
REVIEWER_BLOCKED_MILESTONE_ADVANCED = "reviewer_blocked_milestone_advanced"

VALID_SCENARIOS = (
    VALID_PLANNING_REPLAN,
    VALID_PLANNING_CAPABILITY_EXPANSION,
    VALID_NODE_ENTRY_REPLAN,
    VALID_IN_PROGRESS_REPLAN,
    VALID_PM_HISTORICAL_DEFECT_REPAIR,
    VALID_REVIEW_FAILURE_REPAIR,
    VALID_REVIEW_FAILURE_LOCAL_PATCH,
    VALID_MILESTONE_UNCHANGED_PLAN_RENEWAL,
    VALID_MILESTONE_CHANGED_SUFFIX_RENEWAL,
    VALID_NESTED_CHILD_LOCAL_CLOSURE,
    VALID_TERMINAL_EMPTY_PLAN_RENEWAL,
    VALID_RESUME_CURRENT_MILESTONE_GATE,
    VALID_MILESTONE_REVIEW_BLOCK_HOLDS_FRONTIER,
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
    PM_HISTORICAL_DEFECT_FORCED_THROUGH_BLOCKER,
    PM_HISTORICAL_DEFECT_WITHOUT_OBSERVATION,
    REPAIR_NODE_MISSING_FIELDS,
    REPAIR_WITHOUT_STALE_RESET,
    REPAIR_WITHOUT_MAINLINE_RETURN,
    ACTIVE_NODE_NOT_EXECUTABLE,
    CONTROLLER_DIRECT_IMPLEMENTATION,
    STALE_APPROVAL_REUSED_AFTER_CHANGE,
    MILESTONE_ADVANCED_WITHOUT_RENEWAL,
    MILESTONE_AUDIT_MISSING,
    MILESTONE_REMAINING_PLAN_INCOMPLETE,
    MILESTONE_REMAINING_OBLIGATION_UNOWNED,
    MILESTONE_AUDIT_CONTRACT_HASH_MISSING,
    MILESTONE_COMPLETED_PREFIX_UNBOUND,
    MILESTONE_REMAINING_OWNER_NODE_UNBOUND,
    MILESTONE_CHECKER_IDENTITY_REUSED,
    MILESTONE_FLOWGUARD_BYPASSED,
    MILESTONE_PM_ABSORPTION_BYPASSED,
    MILESTONE_REVIEWER_BYPASSED,
    MILESTONE_SYSTEM_VALIDATION_BYPASSED,
    MILESTONE_LOWEST_ACCEPTANCE_BYPASSED_GATE,
    TERMINAL_EMPTY_PLAN_BYPASSED_CHALLENGE,
    MILESTONE_CURRENTNESS_RECOVERY_USED_TEXT_MATCH,
    UNCHANGED_PLAN_BUMPED_ROUTE_VERSION,
    CHANGED_PLAN_KEPT_OLD_ROUTE_VERSION,
    CHANGED_PLAN_LOST_COMPLETED_PREFIX,
    PREMATURE_TERMINAL_EMPTY_PLAN,
    RESUME_REUSED_HISTORICAL_MILESTONE_REVIEW,
    NESTED_CHILD_FORCED_GLOBAL_RENEWAL,
    MILESTONE_REUSED_OLD_PLAN_WITHOUT_FRESH_WRITE,
    REVIEWER_BLOCKED_MILESTONE_ADVANCED,
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
    phase: str = "unset"  # planning | node_entry | node_in_progress | milestone_renewal | historical_repair | review_failure
    issue_kind: str = "none"  # planning_gap | capability_gap | structure_gap | historical_defect | review_failure
    repair_trigger_origin: str = "none"  # none | pm_historical_defect | reviewer_failure
    structured_defect_observation_recorded: bool = False
    blocker_prerequisite_required: bool = False
    pre_work_decomposition: bool = False
    post_work_repair: bool = False
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
    product_scope_flowguard_checked: bool = False
    product_scope_flowguard_before_process: bool = False
    route_scope_flowguard_checked: bool = False
    reviewer_approved_changed_route: bool = False
    old_approval_reused_after_change: bool = False

    active_node_executable: bool = False
    pm_activated_or_used_route: bool = False
    controller_direct_product_work: bool = False
    top_level_milestone: bool = False
    milestone_result_current: bool = False
    milestone_audit_complete: bool = False
    prior_plan_assessed: bool = False
    remaining_plan_complete: bool = False
    fresh_remaining_plan_written: bool = False
    remaining_obligations_owned: bool = False
    milestone_contract_current: bool = False
    completed_prefix_bound: bool = False
    remaining_owner_nodes_bound: bool = False
    checker_identities_independent: bool = True
    remaining_plan_changed: bool = False
    milestone_flowguard_checked: bool = False
    milestone_pm_absorbed_flowguard: bool = False
    milestone_reviewer_approved: bool = False
    milestone_reviewer_blocked: bool = False
    milestone_system_validation_passed: bool = False
    milestone_commit_owned_by_current_gate: bool = False
    typed_currentness_recovery_only: bool = False
    route_version_changed: bool = False
    completed_prefix_preserved: bool = True
    empty_remaining_plan: bool = False
    all_hard_obligations_closed: bool = False
    frontier_advanced: bool = False
    global_milestone_renewal_started: bool = False
    resume_current_gate: bool = False
    historical_milestone_review_reused: bool = False
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
        "product_scope_flowguard_checked",
        "route_scope_flowguard_checked",
        "reviewer_approved_changed_route",
        "active_node_executable",
        "repair_fields_complete",
        "milestone_contract_current",
        "completed_prefix_bound",
        "remaining_owner_nodes_bound",
        "checker_identities_independent",
        "milestone_commit_owned_by_current_gate",
        "typed_currentness_recovery_only",
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
        pre_work_decomposition=True,
        route_started=False,
        completed_nodes=0,
        current_node_kind="root",
        change_kind="route_rewrite",
        added_node_fields_complete=True,
        route_scope_flowguard_checked=True,
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
        pre_work_decomposition=True,
        route_started=False,
        completed_nodes=0,
        current_node_kind="root",
        change_kind="add_child_node",
        ordinary_node_added=True,
        added_node_fields_complete=True,
        product_capability_changed=True,
        product_scope_flowguard_checked=True,
        product_scope_flowguard_before_process=True,
        route_scope_flowguard_checked=True,
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
        pre_work_decomposition=True,
        route_started=True,
        completed_nodes=0,
        current_node_kind="module",
        target_node_started=False,
        change_kind="add_child_node",
        ordinary_node_added=True,
        added_node_fields_complete=True,
        product_capability_changed=True,
        product_scope_flowguard_checked=True,
        product_scope_flowguard_before_process=True,
        route_scope_flowguard_checked=True,
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
        pre_work_decomposition=True,
        route_started=True,
        completed_nodes=0,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=False,
        change_kind="node_internal_replan",
        added_node_fields_complete=True,
        route_scope_flowguard_checked=True,
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
        repair_trigger_origin="reviewer_failure",
        structured_defect_observation_recorded=True,
        post_work_repair=True,
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
        route_scope_flowguard_checked=True,
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
        repair_trigger_origin="reviewer_failure",
        structured_defect_observation_recorded=True,
        post_work_repair=True,
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


def _valid_pm_historical_defect_repair() -> State:
    return State(
        status="running",
        scenario=VALID_PM_HISTORICAL_DEFECT_REPAIR,
        phase="historical_repair",
        issue_kind="historical_defect",
        repair_trigger_origin="pm_historical_defect",
        structured_defect_observation_recorded=True,
        blocker_prerequisite_required=False,
        pre_work_decomposition=False,
        post_work_repair=True,
        route_started=True,
        completed_nodes=1,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=True,
        reviewer_failure_recorded=False,
        change_kind="repair_node",
        repair_node_created=True,
        repair_fields_complete=True,
        stale_evidence_reset=True,
        mainline_return_defined=True,
        rerun_obligations_defined=True,
        route_scope_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
    )


def _valid_milestone_unchanged_plan_renewal() -> State:
    return State(
        status="running",
        scenario=VALID_MILESTONE_UNCHANGED_PLAN_RENEWAL,
        phase="milestone_renewal",
        issue_kind="none",
        route_started=True,
        completed_nodes=1,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=True,
        change_kind="none",
        active_node_executable=True,
        pm_activated_or_used_route=True,
        top_level_milestone=True,
        milestone_result_current=True,
        milestone_audit_complete=True,
        prior_plan_assessed=True,
        remaining_plan_complete=True,
        fresh_remaining_plan_written=True,
        remaining_obligations_owned=True,
        milestone_contract_current=True,
        completed_prefix_bound=True,
        remaining_owner_nodes_bound=True,
        checker_identities_independent=True,
        remaining_plan_changed=False,
        milestone_flowguard_checked=True,
        milestone_pm_absorbed_flowguard=True,
        milestone_reviewer_approved=True,
        milestone_system_validation_passed=True,
        milestone_commit_owned_by_current_gate=True,
        typed_currentness_recovery_only=True,
        route_version_changed=False,
        completed_prefix_preserved=True,
        empty_remaining_plan=False,
        all_hard_obligations_closed=False,
        frontier_advanced=True,
        global_milestone_renewal_started=True,
    )


def _valid_milestone_changed_suffix_renewal() -> State:
    return replace(
        _valid_milestone_unchanged_plan_renewal(),
        scenario=VALID_MILESTONE_CHANGED_SUFFIX_RENEWAL,
        change_kind="route_rewrite",
        added_node_fields_complete=True,
        remaining_plan_changed=True,
        route_scope_flowguard_checked=True,
        reviewer_approved_changed_route=True,
        route_version_changed=True,
    )


def _valid_nested_child_local_closure() -> State:
    return State(
        status="running",
        scenario=VALID_NESTED_CHILD_LOCAL_CLOSURE,
        phase="node_in_progress",
        issue_kind="none",
        route_started=True,
        completed_nodes=1,
        current_node_kind="leaf",
        target_node_started=True,
        target_node_result_submitted=True,
        active_node_executable=True,
        pm_activated_or_used_route=True,
        top_level_milestone=False,
        frontier_advanced=True,
        global_milestone_renewal_started=False,
    )


def _valid_terminal_empty_plan_renewal() -> State:
    return replace(
        _valid_milestone_unchanged_plan_renewal(),
        scenario=VALID_TERMINAL_EMPTY_PLAN_RENEWAL,
        remaining_obligations_owned=True,
        empty_remaining_plan=True,
        all_hard_obligations_closed=True,
    )


def _valid_resume_current_milestone_gate() -> State:
    return replace(
        _valid_milestone_unchanged_plan_renewal(),
        scenario=VALID_RESUME_CURRENT_MILESTONE_GATE,
        pm_activated_or_used_route=False,
        milestone_reviewer_approved=False,
        milestone_system_validation_passed=False,
        frontier_advanced=False,
        resume_current_gate=True,
    )


def _valid_milestone_review_block_holds_frontier() -> State:
    return replace(
        _valid_milestone_unchanged_plan_renewal(),
        scenario=VALID_MILESTONE_REVIEW_BLOCK_HOLDS_FRONTIER,
        pm_activated_or_used_route=False,
        milestone_reviewer_approved=False,
        milestone_reviewer_blocked=True,
        milestone_system_validation_passed=False,
        frontier_advanced=False,
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
    if scenario == VALID_PM_HISTORICAL_DEFECT_REPAIR:
        return _valid_pm_historical_defect_repair()
    if scenario == VALID_REVIEW_FAILURE_REPAIR:
        return _valid_review_failure_repair()
    if scenario == VALID_REVIEW_FAILURE_LOCAL_PATCH:
        return _valid_review_failure_local_patch()
    if scenario == VALID_MILESTONE_UNCHANGED_PLAN_RENEWAL:
        return _valid_milestone_unchanged_plan_renewal()
    if scenario == VALID_MILESTONE_CHANGED_SUFFIX_RENEWAL:
        return _valid_milestone_changed_suffix_renewal()
    if scenario == VALID_NESTED_CHILD_LOCAL_CLOSURE:
        return _valid_nested_child_local_closure()
    if scenario == VALID_TERMINAL_EMPTY_PLAN_RENEWAL:
        return _valid_terminal_empty_plan_renewal()
    if scenario == VALID_RESUME_CURRENT_MILESTONE_GATE:
        return _valid_resume_current_milestone_gate()
    if scenario == VALID_MILESTONE_REVIEW_BLOCK_HOLDS_FRONTIER:
        return _valid_milestone_review_block_holds_frontier()

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
        return replace(state, scenario=scenario, product_scope_flowguard_checked=False)
    if scenario == PROCESS_BEFORE_PRODUCT_FOR_CAPABILITY_CHANGE:
        return replace(state, scenario=scenario, product_scope_flowguard_before_process=False)
    if scenario == STRUCTURE_CHANGE_WITHOUT_PROCESS_CHECK:
        return replace(state, scenario=scenario, route_scope_flowguard_checked=False)
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
    if scenario == PM_HISTORICAL_DEFECT_FORCED_THROUGH_BLOCKER:
        return replace(
            _valid_pm_historical_defect_repair(),
            scenario=scenario,
            blocker_prerequisite_required=True,
            reviewer_failure_recorded=True,
        )
    if scenario == PM_HISTORICAL_DEFECT_WITHOUT_OBSERVATION:
        return replace(
            _valid_pm_historical_defect_repair(),
            scenario=scenario,
            structured_defect_observation_recorded=False,
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
    if scenario == MILESTONE_ADVANCED_WITHOUT_RENEWAL:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_audit_complete=False,
            prior_plan_assessed=False,
            remaining_plan_complete=False,
            global_milestone_renewal_started=False,
        )
    if scenario == MILESTONE_AUDIT_MISSING:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_audit_complete=False,
        )
    if scenario == MILESTONE_REMAINING_PLAN_INCOMPLETE:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            remaining_plan_complete=False,
        )
    if scenario == MILESTONE_REMAINING_OBLIGATION_UNOWNED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            remaining_obligations_owned=False,
        )
    if scenario == MILESTONE_AUDIT_CONTRACT_HASH_MISSING:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_contract_current=False,
        )
    if scenario == MILESTONE_COMPLETED_PREFIX_UNBOUND:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            completed_prefix_bound=False,
        )
    if scenario == MILESTONE_REMAINING_OWNER_NODE_UNBOUND:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            remaining_owner_nodes_bound=False,
        )
    if scenario == MILESTONE_CHECKER_IDENTITY_REUSED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            checker_identities_independent=False,
        )
    if scenario == MILESTONE_FLOWGUARD_BYPASSED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_flowguard_checked=False,
        )
    if scenario == MILESTONE_PM_ABSORPTION_BYPASSED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_pm_absorbed_flowguard=False,
        )
    if scenario == MILESTONE_REVIEWER_BYPASSED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_reviewer_approved=False,
        )
    if scenario == MILESTONE_SYSTEM_VALIDATION_BYPASSED:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_system_validation_passed=False,
        )
    if scenario == MILESTONE_LOWEST_ACCEPTANCE_BYPASSED_GATE:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            milestone_commit_owned_by_current_gate=False,
        )
    if scenario == TERMINAL_EMPTY_PLAN_BYPASSED_CHALLENGE:
        return replace(
            _valid_terminal_empty_plan_renewal(),
            scenario=scenario,
            milestone_pm_absorbed_flowguard=False,
        )
    if scenario == MILESTONE_CURRENTNESS_RECOVERY_USED_TEXT_MATCH:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            typed_currentness_recovery_only=False,
        )
    if scenario == UNCHANGED_PLAN_BUMPED_ROUTE_VERSION:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            route_version_changed=True,
        )
    if scenario == CHANGED_PLAN_KEPT_OLD_ROUTE_VERSION:
        return replace(
            _valid_milestone_changed_suffix_renewal(),
            scenario=scenario,
            route_version_changed=False,
        )
    if scenario == CHANGED_PLAN_LOST_COMPLETED_PREFIX:
        return replace(
            _valid_milestone_changed_suffix_renewal(),
            scenario=scenario,
            completed_prefix_preserved=False,
        )
    if scenario == PREMATURE_TERMINAL_EMPTY_PLAN:
        return replace(
            _valid_terminal_empty_plan_renewal(),
            scenario=scenario,
            all_hard_obligations_closed=False,
        )
    if scenario == RESUME_REUSED_HISTORICAL_MILESTONE_REVIEW:
        return replace(
            _valid_resume_current_milestone_gate(),
            scenario=scenario,
            historical_milestone_review_reused=True,
            milestone_reviewer_approved=True,
            milestone_system_validation_passed=True,
            frontier_advanced=True,
        )
    if scenario == NESTED_CHILD_FORCED_GLOBAL_RENEWAL:
        return replace(
            _valid_nested_child_local_closure(),
            scenario=scenario,
            global_milestone_renewal_started=True,
        )
    if scenario == MILESTONE_REUSED_OLD_PLAN_WITHOUT_FRESH_WRITE:
        return replace(
            _valid_milestone_unchanged_plan_renewal(),
            scenario=scenario,
            fresh_remaining_plan_written=False,
        )
    if scenario == REVIEWER_BLOCKED_MILESTONE_ADVANCED:
        return replace(
            _valid_milestone_review_block_holds_frontier(),
            scenario=scenario,
            frontier_advanced=True,
            pm_activated_or_used_route=True,
        )
    return state


def _route_structure_changed(state: State) -> bool:
    return state.change_kind in STRUCTURE_CHANGES


def _changed_route_or_node(state: State) -> bool:
    return state.change_kind != "none" or state.product_capability_changed


def _valid_post_work_repair_trigger(state: State) -> bool:
    if not state.post_work_repair:
        return False
    if state.repair_trigger_origin == "reviewer_failure":
        return state.phase == "review_failure" and state.reviewer_failure_recorded
    if state.repair_trigger_origin == "pm_historical_defect":
        return (
            state.phase == "historical_repair"
            and state.issue_kind == "historical_defect"
            and state.structured_defect_observation_recorded
            and not state.blocker_prerequisite_required
        )
    return False


def _milestone_route_is_used(state: State) -> bool:
    return (
        state.phase == "milestone_renewal"
        and state.top_level_milestone
        and state.frontier_advanced
    )


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
    if state.product_capability_changed and not state.product_scope_flowguard_checked:
        failures.append("product capability change lacks product-scope FlowGuard check")
    if (
        state.product_capability_changed
        and state.route_scope_flowguard_checked
        and not state.product_scope_flowguard_before_process
    ):
        failures.append("route-scope FlowGuard ran before product-scope FlowGuard for a product capability change")
    if _route_structure_changed(state) and not state.route_scope_flowguard_checked:
        failures.append("route structure change lacks route-scope FlowGuard check")
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
    if (
        state.repair_trigger_origin == "pm_historical_defect"
        and state.blocker_prerequisite_required
    ):
        failures.append(
            "PM historical defect was forced through a fabricated blocker prerequisite"
        )
    if (
        state.repair_trigger_origin == "pm_historical_defect"
        and not state.structured_defect_observation_recorded
    ):
        failures.append(
            "PM historical defect repair lacks a structured defect observation"
        )
    if state.repair_node_created:
        if not _valid_post_work_repair_trigger(state):
            failures.append(
                "repair node lacks a valid reviewed-failure or PM historical-defect trigger"
            )
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
    if _milestone_route_is_used(state):
        if not state.global_milestone_renewal_started:
            failures.append("top-level milestone advanced without mandatory plan renewal")
        if not state.milestone_result_current:
            failures.append("top-level milestone renewal used a noncurrent milestone result")
        if not state.milestone_audit_complete:
            failures.append("top-level milestone renewal lacks a complete current audit")
        if not state.prior_plan_assessed:
            failures.append("top-level milestone renewal did not assess the prior remaining plan")
        if not state.remaining_plan_complete:
            failures.append("top-level milestone renewal lacks a complete route to the final goal")
        if not state.fresh_remaining_plan_written:
            failures.append("top-level milestone renewal reused the old plan without freshly writing the complete remainder")
        if not state.remaining_obligations_owned:
            failures.append("top-level milestone renewal leaves a remaining hard obligation without an owner")
        if not state.milestone_contract_current:
            failures.append("top-level milestone renewal is not bound to the frozen final-goal contract")
        if not state.completed_prefix_bound:
            failures.append("top-level milestone renewal does not bind the cumulative completed prefix")
        if not state.remaining_owner_nodes_bound:
            failures.append("top-level milestone renewal leaves a remaining gap without a submitted owner node")
        if not state.checker_identities_independent:
            failures.append("top-level milestone renewal reuses a checker identity for required evidence")
        if not state.milestone_flowguard_checked:
            failures.append("top-level milestone renewal bypassed current FlowGuard review")
        if not state.milestone_pm_absorbed_flowguard:
            failures.append("top-level milestone renewal bypassed PM absorption of FlowGuard")
        if not state.milestone_reviewer_approved:
            failures.append("top-level milestone renewal bypassed independent Reviewer approval")
        if not state.milestone_system_validation_passed:
            failures.append("top-level milestone renewal bypassed system validation")
        if not state.milestone_commit_owned_by_current_gate:
            failures.append("top-level milestone acceptance bypassed the current staged gate commit owner")
        if not state.typed_currentness_recovery_only:
            failures.append("top-level milestone recovery relied on error text instead of typed currentness drift")
    if (
        state.phase == "milestone_renewal"
        and state.top_level_milestone
        and not state.remaining_plan_changed
        and state.route_version_changed
    ):
        failures.append("unchanged remaining plan created a gratuitous route version")
    if (
        state.phase == "milestone_renewal"
        and state.top_level_milestone
        and state.remaining_plan_changed
        and state.pm_activated_or_used_route
        and not state.route_version_changed
    ):
        failures.append("changed remaining plan kept the old active route version")
    if (
        state.phase == "milestone_renewal"
        and state.top_level_milestone
        and state.remaining_plan_changed
        and not state.completed_prefix_preserved
    ):
        failures.append("changed remaining plan discarded accepted milestone history")
    if state.empty_remaining_plan and not state.all_hard_obligations_closed:
        failures.append("empty remaining plan was accepted before every hard obligation closed")
    if state.resume_current_gate and state.historical_milestone_review_reused:
        failures.append("resume reused a historical milestone review for the current gate")
    if state.milestone_reviewer_blocked and state.frontier_advanced:
        failures.append("Reviewer-blocked milestone renewal advanced the frontier")
    if (
        not state.top_level_milestone
        and state.global_milestone_renewal_started
    ):
        failures.append("nested child closure started an unnecessary global milestone renewal")
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


def historical_repairs_do_not_fabricate_blockers(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.status == "accepted"
        and state.repair_trigger_origin == "pm_historical_defect"
        and (
            state.blocker_prerequisite_required
            or not state.structured_defect_observation_recorded
        )
    ):
        return InvariantResult.fail(
            "PM historical repair fabricated a blocker or omitted its defect observation"
        )
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


def milestone_renewal_gates_route_use(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    milestone_failures = [
        failure
        for failure in policy_failures(state)
        if "milestone renewal" in failure
        or "remaining plan" in failure
        or "historical milestone review" in failure
    ]
    if milestone_failures:
        return InvariantResult.fail("; ".join(milestone_failures))
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
        description="Product capability and route-structure changes run Product/route-scope FlowGuard and Reviewer gates before use.",
        predicate=model_gates_cover_changed_routes,
    ),
    Invariant(
        name="repair_nodes_are_post_failure_and_complete",
        description="Repair nodes require a valid post-work reviewed-failure or PM historical-defect trigger and complete metadata.",
        predicate=repair_nodes_are_post_failure_and_complete,
    ),
    Invariant(
        name="historical_repairs_do_not_fabricate_blockers",
        description="Direct PM historical-defect repair uses a structured observation and never manufactures a blocker prerequisite.",
        predicate=historical_repairs_do_not_fabricate_blockers,
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
    Invariant(
        name="milestone_renewal_gates_route_use",
        description=(
            "Every top-level milestone uses one current audit, complete remaining plan, "
            "FlowGuard/PM/Reviewer/validation chain, equality-aware versioning, and preserved completed history."
        ),
        predicate=milestone_renewal_gates_route_use,
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
