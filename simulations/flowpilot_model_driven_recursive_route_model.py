"""FlowGuard model for FlowPilot model-driven recursive route governance.

Risk purpose:
- This FlowGuard model reviews the planned FlowPilot upgrade where Product and
  Process FlowGuard Officers produce first-class models before PM route
  activation and before entering every non-leaf node.
- It guards against route drafting before product modeling, skipped reviewer
  challenges, non-serial execution routes, oversized leaves, stale approvals
  after leaf promotion, missing parent/root backward coverage, final closure
  before all major nodes are reviewed, and route displays that keep placeholders
  or lose Mermaid visuals.
- Future agents should run
  `python simulations/run_flowpilot_model_driven_recursive_route_checks.py`
  before changing FlowPilot route governance, recursive decomposition, terminal
  closure, or route-display behavior.
- This model is intentionally protocol-level; prompt cards, Router runtime,
  templates, and unit tests remain required production-facing checks.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


INTENDED_MODEL_DRIVEN_RECURSIVE_ROUTE = "intended_model_driven_recursive_route"

ROUTE_DRAFTED_BEFORE_PRODUCT_MODEL = "route_drafted_before_product_model"
PRODUCT_MODEL_PM_DECISION_SKIPPED = "product_model_pm_decision_skipped"
PRODUCT_REVIEW_SKIPPED_BEFORE_ROUTE = "product_review_skipped_before_route"
PROCESS_MODEL_MISSING_BEFORE_ACTIVATION = "process_model_missing_before_activation"
PROCESS_MODEL_NOT_SERIAL = "process_model_not_serial"
HIDDEN_PARALLEL_LEAF_MARKED_READY = "hidden_parallel_leaf_marked_ready"
LEAF_TOO_LARGE_NOT_PROMOTED = "leaf_too_large_not_promoted"
PROMOTED_LEAF_KEEPS_OLD_APPROVALS = "promoted_leaf_keeps_old_approvals"
NON_LEAF_ENTRY_PRODUCT_LOOP_SKIPPED = "non_leaf_entry_product_loop_skipped"
NON_LEAF_ENTRY_PROCESS_LOOP_SKIPPED = "non_leaf_entry_process_loop_skipped"
PARENT_COMPLETION_OMITS_CHILD_COVERAGE = "parent_completion_omits_child_coverage"
PARENT_OMISSION_PATCHED_WITHOUT_MODEL_MISS = "parent_omission_patched_without_model_miss"
SAME_CLASS_OMISSIONS_NOT_SEARCHED = "same_class_omissions_not_searched"
FINAL_CLOSURE_OMITS_MAJOR_NODE_REVIEW = "final_closure_omits_major_node_review"
FINAL_MODEL_MISS_NOT_UPGRADED = "final_model_miss_not_upgraded"
PLACEHOLDER_KEPT_AFTER_REAL_ROUTE = "placeholder_kept_after_real_route"
REAL_ROUTE_WITHOUT_MERMAID = "real_route_without_mermaid"
REAL_ROUTE_USES_PROTOCOL_STAGES = "real_route_uses_protocol_stages"
COCKPIT_HIDES_DEEP_TREE = "cockpit_hides_deep_tree"

VALID_SCENARIOS = (INTENDED_MODEL_DRIVEN_RECURSIVE_ROUTE,)
NEGATIVE_SCENARIOS = (
    ROUTE_DRAFTED_BEFORE_PRODUCT_MODEL,
    PRODUCT_MODEL_PM_DECISION_SKIPPED,
    PRODUCT_REVIEW_SKIPPED_BEFORE_ROUTE,
    PROCESS_MODEL_MISSING_BEFORE_ACTIVATION,
    PROCESS_MODEL_NOT_SERIAL,
    HIDDEN_PARALLEL_LEAF_MARKED_READY,
    LEAF_TOO_LARGE_NOT_PROMOTED,
    PROMOTED_LEAF_KEEPS_OLD_APPROVALS,
    NON_LEAF_ENTRY_PRODUCT_LOOP_SKIPPED,
    NON_LEAF_ENTRY_PROCESS_LOOP_SKIPPED,
    PARENT_COMPLETION_OMITS_CHILD_COVERAGE,
    PARENT_OMISSION_PATCHED_WITHOUT_MODEL_MISS,
    SAME_CLASS_OMISSIONS_NOT_SEARCHED,
    FINAL_CLOSURE_OMITS_MAJOR_NODE_REVIEW,
    FINAL_MODEL_MISS_NOT_UPGRADED,
    PLACEHOLDER_KEPT_AFTER_REAL_ROUTE,
    REAL_ROUTE_WITHOUT_MERMAID,
    REAL_ROUTE_USES_PROTOCOL_STAGES,
    COCKPIT_HIDES_DEEP_TREE,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One model-driven recursive route governance evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"

    pm_product_goal_written: bool = False
    product_behavior_model_written: bool = False
    pm_product_model_decision: bool = False
    reviewer_product_model_challenge_passed: bool = False

    pm_route_draft_written: bool = False
    process_route_execution_model_written: bool = False
    process_route_execution_model_serial: bool = False
    leaf_decomposition_audit_written: bool = False
    all_leaves_worker_ready: bool = False
    leaves_have_no_hidden_parallel_work: bool = False
    pm_process_model_decision: bool = False
    reviewer_route_challenge_passed: bool = False
    route_activated: bool = False

    non_leaf_node_entry: bool = False
    node_product_model_written: bool = False
    pm_node_product_model_decision: bool = False
    reviewer_node_product_challenge_passed: bool = False
    node_process_execution_model_written: bool = False
    node_process_execution_model_serial: bool = False
    pm_node_process_model_decision: bool = False
    reviewer_node_route_challenge_passed: bool = False
    child_execution_started: bool = False

    leaf_entry_reviewed_by_pm: bool = False
    leaf_too_large: bool = False
    leaf_promoted_to_parent: bool = False
    promoted_leaf_children_added: bool = False
    stale_leaf_approvals_invalidated: bool = False

    parent_children_all_accounted_for: bool = False
    parent_backward_review_passed: bool = False
    parent_omission_found: bool = False
    parent_model_miss_triaged: bool = False
    parent_process_model_upgraded: bool = False
    same_class_omissions_searched: bool = False
    supplemental_or_repair_nodes_run: bool = False
    parent_completed: bool = False

    final_all_major_nodes_reviewed: bool = False
    final_all_subtrees_reviewed: bool = False
    final_omission_found: bool = False
    final_model_miss_triaged: bool = False
    final_process_model_upgraded: bool = False
    final_supplemental_or_repair_nodes_run: bool = False
    project_completed: bool = False

    placeholder_displayed_before_route: bool = False
    placeholder_marked_temporary: bool = False
    real_route_available: bool = False
    placeholder_replaced_by_real_route: bool = False
    real_route_mermaid_displayed_in_chat: bool = False
    real_route_uses_serial_execution_model: bool = False
    status_summary_displayed_in_chat: bool = False
    cockpit_full_tree_visible: bool = False
    cockpit_current_path_visible: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class ModelDrivenRecursiveRouteStep:
    """One transition for model-driven recursive route governance.

    Input x State -> Set(Output x State)
    reads: PM product goal, officer product model, reviewer product challenge,
      PM route draft, officer process model, node-local model artifacts, parent
      and final backward reviews, and route-display metadata
    writes: accepted/rejected protocol decision
    idempotency: scenario facts are monotonic; terminal states remain terminal.
    """

    name = "ModelDrivenRecursiveRouteStep"
    input_description = "FlowPilot recursive route governance tick"
    output_description = "one protocol transition"
    reads = (
        "product_model_artifacts",
        "route_model_artifacts",
        "node_local_model_artifacts",
        "parent_backward_review",
        "final_backward_review",
        "route_display_packet",
    )
    writes = ("terminal_model_driven_route_decision",)
    idempotency = "monotonic scenario evaluation"

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


def _valid_state() -> State:
    return State(
        status="running",
        scenario=INTENDED_MODEL_DRIVEN_RECURSIVE_ROUTE,
        pm_product_goal_written=True,
        product_behavior_model_written=True,
        pm_product_model_decision=True,
        reviewer_product_model_challenge_passed=True,
        pm_route_draft_written=True,
        process_route_execution_model_written=True,
        process_route_execution_model_serial=True,
        leaf_decomposition_audit_written=True,
        all_leaves_worker_ready=True,
        leaves_have_no_hidden_parallel_work=True,
        pm_process_model_decision=True,
        reviewer_route_challenge_passed=True,
        route_activated=True,
        non_leaf_node_entry=True,
        node_product_model_written=True,
        pm_node_product_model_decision=True,
        reviewer_node_product_challenge_passed=True,
        node_process_execution_model_written=True,
        node_process_execution_model_serial=True,
        pm_node_process_model_decision=True,
        reviewer_node_route_challenge_passed=True,
        child_execution_started=True,
        leaf_entry_reviewed_by_pm=True,
        leaf_too_large=True,
        leaf_promoted_to_parent=True,
        promoted_leaf_children_added=True,
        stale_leaf_approvals_invalidated=True,
        parent_children_all_accounted_for=True,
        parent_backward_review_passed=True,
        parent_omission_found=True,
        parent_model_miss_triaged=True,
        parent_process_model_upgraded=True,
        same_class_omissions_searched=True,
        supplemental_or_repair_nodes_run=True,
        parent_completed=True,
        final_all_major_nodes_reviewed=True,
        final_all_subtrees_reviewed=True,
        final_omission_found=True,
        final_model_miss_triaged=True,
        final_process_model_upgraded=True,
        final_supplemental_or_repair_nodes_run=True,
        project_completed=True,
        placeholder_displayed_before_route=True,
        placeholder_marked_temporary=True,
        real_route_available=True,
        placeholder_replaced_by_real_route=True,
        real_route_mermaid_displayed_in_chat=True,
        real_route_uses_serial_execution_model=True,
        status_summary_displayed_in_chat=True,
        cockpit_full_tree_visible=True,
        cockpit_current_path_visible=True,
    )


def _scenario_state(scenario: str) -> State:
    state = _valid_state()
    if scenario == INTENDED_MODEL_DRIVEN_RECURSIVE_ROUTE:
        return state
    updates: dict[str, object] = {"scenario": scenario}
    if scenario == ROUTE_DRAFTED_BEFORE_PRODUCT_MODEL:
        updates["product_behavior_model_written"] = False
    elif scenario == PRODUCT_MODEL_PM_DECISION_SKIPPED:
        updates["pm_product_model_decision"] = False
    elif scenario == PRODUCT_REVIEW_SKIPPED_BEFORE_ROUTE:
        updates["reviewer_product_model_challenge_passed"] = False
    elif scenario == PROCESS_MODEL_MISSING_BEFORE_ACTIVATION:
        updates["process_route_execution_model_written"] = False
    elif scenario == PROCESS_MODEL_NOT_SERIAL:
        updates["process_route_execution_model_serial"] = False
    elif scenario == HIDDEN_PARALLEL_LEAF_MARKED_READY:
        updates["leaves_have_no_hidden_parallel_work"] = False
    elif scenario == LEAF_TOO_LARGE_NOT_PROMOTED:
        updates["leaf_promoted_to_parent"] = False
        updates["promoted_leaf_children_added"] = False
    elif scenario == PROMOTED_LEAF_KEEPS_OLD_APPROVALS:
        updates["stale_leaf_approvals_invalidated"] = False
    elif scenario == NON_LEAF_ENTRY_PRODUCT_LOOP_SKIPPED:
        updates["node_product_model_written"] = False
        updates["reviewer_node_product_challenge_passed"] = False
    elif scenario == NON_LEAF_ENTRY_PROCESS_LOOP_SKIPPED:
        updates["node_process_execution_model_written"] = False
        updates["reviewer_node_route_challenge_passed"] = False
    elif scenario == PARENT_COMPLETION_OMITS_CHILD_COVERAGE:
        updates["parent_children_all_accounted_for"] = False
    elif scenario == PARENT_OMISSION_PATCHED_WITHOUT_MODEL_MISS:
        updates["parent_model_miss_triaged"] = False
        updates["parent_process_model_upgraded"] = False
    elif scenario == SAME_CLASS_OMISSIONS_NOT_SEARCHED:
        updates["same_class_omissions_searched"] = False
    elif scenario == FINAL_CLOSURE_OMITS_MAJOR_NODE_REVIEW:
        updates["final_all_major_nodes_reviewed"] = False
    elif scenario == FINAL_MODEL_MISS_NOT_UPGRADED:
        updates["final_model_miss_triaged"] = False
        updates["final_process_model_upgraded"] = False
    elif scenario == PLACEHOLDER_KEPT_AFTER_REAL_ROUTE:
        updates["placeholder_replaced_by_real_route"] = False
    elif scenario == REAL_ROUTE_WITHOUT_MERMAID:
        updates["real_route_mermaid_displayed_in_chat"] = False
    elif scenario == REAL_ROUTE_USES_PROTOCOL_STAGES:
        updates["real_route_uses_serial_execution_model"] = False
    elif scenario == COCKPIT_HIDES_DEEP_TREE:
        updates["cockpit_full_tree_visible"] = False
        updates["cockpit_current_path_visible"] = False
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return replace(state, **updates)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if is_terminal(state):
        return ()
    if state.status == "new":
        return tuple(
            Transition(f"select_{scenario}", _scenario_state(scenario))
            for scenario in SCENARIOS
        )
    failures = protocol_failures(state)
    if failures:
        return (Transition(f"reject_{state.scenario}", replace(state, status="rejected", terminal_reason=failures[0])),)
    return (Transition(f"accept_{state.scenario}", replace(state, status="accepted", terminal_reason="protocol_passed")),)


def protocol_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_route_draft_written and not state.product_behavior_model_written:
        failures.append("route drafted before Product Officer wrote product behavior model")
    if state.pm_route_draft_written and not state.pm_product_model_decision:
        failures.append("route drafted before PM accepted product behavior model")
    if state.pm_route_draft_written and not state.reviewer_product_model_challenge_passed:
        failures.append("route drafted before reviewer challenged product model")
    if state.route_activated and not state.process_route_execution_model_written:
        failures.append("route activated without Process Officer serial execution model")
    if state.route_activated and not state.process_route_execution_model_serial:
        failures.append("process route execution model is not serial")
    if state.route_activated and not state.leaf_decomposition_audit_written:
        failures.append("route activated without leaf decomposition audit")
    if state.route_activated and not state.all_leaves_worker_ready:
        failures.append("route activated with leaves that are not worker-ready")
    if state.route_activated and not state.leaves_have_no_hidden_parallel_work:
        failures.append("leaf readiness accepted hidden parallel or multi-worker work")
    if state.route_activated and not state.pm_process_model_decision:
        failures.append("route activated before PM accepted process execution model")
    if state.route_activated and not state.reviewer_route_challenge_passed:
        failures.append("route activated before reviewer route challenge")
    if state.child_execution_started:
        if not (state.node_product_model_written and state.pm_node_product_model_decision and state.reviewer_node_product_challenge_passed):
            failures.append("non-leaf node entered children before local product model PM decision and reviewer challenge")
        if not (state.node_process_execution_model_written and state.node_process_execution_model_serial and state.pm_node_process_model_decision and state.reviewer_node_route_challenge_passed):
            failures.append("non-leaf node entered children before local serial process model PM decision and reviewer challenge")
    if state.leaf_too_large:
        if not (state.leaf_promoted_to_parent and state.promoted_leaf_children_added):
            failures.append("oversized leaf was not promoted to a parent with child nodes")
        if state.leaf_promoted_to_parent and not state.stale_leaf_approvals_invalidated:
            failures.append("promoted leaf kept stale approvals instead of rerunning local gates")
    if state.parent_completed:
        if not state.parent_children_all_accounted_for:
            failures.append("parent completed before all child nodes were accounted for")
        if not state.parent_backward_review_passed:
            failures.append("parent completed before parent backward review passed")
    if state.parent_omission_found:
        if not (state.parent_model_miss_triaged and state.parent_process_model_upgraded):
            failures.append("parent omission patched without Process/FlowGuard model-miss triage and model upgrade")
        if not state.same_class_omissions_searched:
            failures.append("parent model miss did not search same-class omissions")
        if not state.supplemental_or_repair_nodes_run:
            failures.append("parent omission did not run supplemental or repair nodes")
    if state.project_completed:
        if not (state.final_all_major_nodes_reviewed and state.final_all_subtrees_reviewed):
            failures.append("project completed before final review covered all major nodes and subtrees")
        if state.final_omission_found and not (state.final_model_miss_triaged and state.final_process_model_upgraded):
            failures.append("final omission closed without Process/FlowGuard model-miss upgrade")
        if state.final_omission_found and not state.final_supplemental_or_repair_nodes_run:
            failures.append("final omission did not run supplemental or repair nodes")
    if state.real_route_available:
        if not state.placeholder_replaced_by_real_route:
            failures.append("real route available but startup placeholder remained active")
        if not state.real_route_mermaid_displayed_in_chat:
            failures.append("real route display omitted Mermaid graph in chat")
        if not state.real_route_uses_serial_execution_model:
            failures.append("real route Mermaid did not use canonical serial execution model")
        if not state.status_summary_displayed_in_chat:
            failures.append("real route display omitted current status summary")
    if state.real_route_available and not (state.cockpit_full_tree_visible and state.cockpit_current_path_visible):
        failures.append("Cockpit display hid full route tree or current path")
    if state.placeholder_displayed_before_route and not state.placeholder_marked_temporary:
        failures.append("startup placeholder lacked temporary placeholder identity")
    return failures


def invariant_failures(state: State) -> list[str]:
    failures = []
    if state.status == "accepted":
        failures.extend(protocol_failures(state))
        if state.scenario not in VALID_SCENARIOS:
            failures.append(f"negative scenario was accepted: {state.scenario}")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("intended model-driven recursive route was rejected")
    return failures


def _invariant(name: str, description: str):
    def _predicate(state: State, _trace):
        failures = invariant_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
        return InvariantResult.pass_()

    return Invariant(name=name, description=description, predicate=_predicate)


INVARIANTS = (
    _invariant(
        "model_driven_recursive_route_accepts_only_safe_protocols",
        "Only fully model-driven recursive serial route protocols can be accepted.",
    ),
)
EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow(
        (ModelDrivenRecursiveRouteStep(),),
        name="flowpilot_model_driven_recursive_route",
    )


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def intended_plan_state() -> State:
    return _scenario_state(INTENDED_MODEL_DRIVEN_RECURSIVE_ROUTE)


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
