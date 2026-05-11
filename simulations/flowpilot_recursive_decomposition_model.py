"""FlowGuard model for FlowPilot recursive route decomposition.

Risk intent brief:
- Validate the recursive-decomposition upgrade before prompt cards, router
  traversal, display projection, or templates are changed.
- Protected harms: complex work being accepted as a two-layer route, workers
  receiving parent nodes or coarse leaves, over-splitting operational steps
  into route nodes, reviewer depth checks being skipped, parent composition
  review being skipped, route mutation leaving the frontier stale, deep work
  being hidden from final closure, user display leaking the whole tree or
  hiding the active path, and PM route memory losing split/stop rationale.
- Modeled state and side effects: PM full route tree, leaf-readiness gates,
  reviewer depth review, router dispatch gate, parent backward replay,
  mutation/frontier reset, user display projection, route memory, and final
  route-wide ledger.
- Hard invariants: only worker-ready leaves may be dispatched; every parent
  with children needs backward replay before completion; reviewer must check
  both under-decomposition and over-decomposition; shallow display must not
  replace the full canonical tree; route memory and final ledger must cover
  every effective deep leaf.
- Blindspot: this model validates the protocol shape. Runtime helpers, prompt
  cards, templates, and conformance tests must still be updated after the
  model passes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


INTENDED_RECURSIVE_ROUTE = "intended_recursive_route"

FIXED_TWO_LAYER_COMPLEX_ROUTE = "fixed_two_layer_complex_route"
COARSE_LEAF_MARKED_READY = "coarse_leaf_marked_ready"
OVER_SPLIT_LEAF_STEPS = "over_split_leaf_steps"
REVIEWER_SKIPS_DEPTH_REVIEW = "reviewer_skips_depth_review"
PARENT_DISPATCHED_TO_WORKER = "parent_dispatched_to_worker"
UNREADY_LEAF_DISPATCHED = "unready_leaf_dispatched"
PARENT_REVIEW_SKIPPED = "parent_review_skipped"
PARENT_FAILURE_ADVANCES = "parent_failure_advances"
MUTATION_FRONTIER_NOT_RESET = "mutation_frontier_not_reset"
DISPLAY_LEAKS_DEEP_TREE = "display_leaks_deep_tree"
DISPLAY_HIDES_ACTIVE_PATH = "display_hides_active_path"
FINAL_LEDGER_OMITS_DEEP_LEAF = "final_ledger_omits_deep_leaf"
MISSING_DECOMPOSITION_MEMORY = "missing_decomposition_memory"

VALID_SCENARIOS = (INTENDED_RECURSIVE_ROUTE,)
NEGATIVE_SCENARIOS = (
    FIXED_TWO_LAYER_COMPLEX_ROUTE,
    COARSE_LEAF_MARKED_READY,
    OVER_SPLIT_LEAF_STEPS,
    REVIEWER_SKIPS_DEPTH_REVIEW,
    PARENT_DISPATCHED_TO_WORKER,
    UNREADY_LEAF_DISPATCHED,
    PARENT_REVIEW_SKIPPED,
    PARENT_FAILURE_ADVANCES,
    MUTATION_FRONTIER_NOT_RESET,
    DISPLAY_LEAKS_DEEP_TREE,
    DISPLAY_HIDES_ACTIVE_PATH,
    FINAL_LEDGER_OMITS_DEEP_LEAF,
    MISSING_DECOMPOSITION_MEMORY,
)
SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One recursive-decomposition protocol evaluation tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | accepted | rejected
    scenario: str = "unset"
    task_complexity: str = "complex"  # simple | complex

    pm_full_route_tree_written: bool = False
    canonical_tree_depth: int = 0
    route_has_parent_nodes: bool = False
    route_has_module_nodes: bool = False
    route_has_leaf_nodes: bool = False
    non_leaf_nodes_have_children: bool = False

    leaf_readiness_gate_defined: bool = False
    all_dispatchable_leaves_ready: bool = False
    leaf_single_outcome: bool = False
    leaf_worker_executable_without_replanning: bool = False
    leaf_proof_defined: bool = False
    leaf_dependency_boundary_defined: bool = False
    leaf_failure_isolation_defined: bool = False
    over_split_operational_steps: bool = False
    over_split_independent_acceptance_value: bool = True

    reviewer_checked_under_decomposition: bool = False
    reviewer_checked_over_decomposition: bool = False
    reviewer_blocks_bad_depth: bool = False

    router_knows_active_path: bool = False
    router_dispatches_only_leaf_nodes: bool = False
    active_node_has_children: bool = False
    worker_packet_registered: bool = False
    dispatched_node_kind: str = "none"  # none | parent | module | leaf
    dispatched_leaf_readiness_status: str = "none"  # none | pass | fail | missing

    parent_children_completed: bool = False
    parent_backward_review_required: bool = False
    parent_backward_review_passed: bool = False
    parent_backward_review_failed: bool = False
    parent_failure_causes_mutation_or_rework: bool = False
    parent_marked_complete: bool = False

    route_mutation_split_node: bool = False
    stale_frontier_reset_to_mutated_subtree: bool = False

    display_depth: int = 0
    user_display_uses_shallow_projection: bool = False
    user_display_leaks_deep_tree: bool = False
    active_path_breadcrumb_visible: bool = False
    hidden_leaf_progress_visible: bool = False

    pmk_decomposition_memory_written: bool = False
    pmk_split_stop_merge_rationale_written: bool = False
    final_ledger_covers_deep_leaves: bool = False
    final_ledger_covers_parent_reviews: bool = False

    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


class RecursiveDecompositionStep:
    """One FlowPilot recursive-decomposition transition.

    Input x State -> Set(Output x State)
    reads: route tree, active frontier, node kind, leaf readiness, reviewer
      depth report, parent review evidence, display projection, route memory,
      final ledger
    writes: terminal protocol acceptance or rejection
    idempotency: scenario facts are monotonic; accepted/rejected states do not
      change on later ticks.
    """

    name = "RecursiveDecompositionStep"
    input_description = "FlowPilot recursive decomposition tick"
    output_description = "one recursive decomposition transition"
    reads = (
        "route_tree",
        "execution_frontier",
        "leaf_readiness_gate",
        "reviewer_depth_report",
        "parent_backward_review",
        "display_projection",
        "route_memory",
        "final_route_wide_ledger",
    )
    writes = ("terminal_recursive_decomposition_decision",)
    idempotency = "monotonic recursive decomposition facts"

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


def _valid_recursive_state() -> State:
    return State(
        status="running",
        scenario=INTENDED_RECURSIVE_ROUTE,
        task_complexity="complex",
        pm_full_route_tree_written=True,
        canonical_tree_depth=4,
        route_has_parent_nodes=True,
        route_has_module_nodes=True,
        route_has_leaf_nodes=True,
        non_leaf_nodes_have_children=True,
        leaf_readiness_gate_defined=True,
        all_dispatchable_leaves_ready=True,
        leaf_single_outcome=True,
        leaf_worker_executable_without_replanning=True,
        leaf_proof_defined=True,
        leaf_dependency_boundary_defined=True,
        leaf_failure_isolation_defined=True,
        over_split_operational_steps=False,
        over_split_independent_acceptance_value=True,
        reviewer_checked_under_decomposition=True,
        reviewer_checked_over_decomposition=True,
        reviewer_blocks_bad_depth=True,
        router_knows_active_path=True,
        router_dispatches_only_leaf_nodes=True,
        active_node_has_children=False,
        worker_packet_registered=True,
        dispatched_node_kind="leaf",
        dispatched_leaf_readiness_status="pass",
        parent_children_completed=True,
        parent_backward_review_required=True,
        parent_backward_review_passed=True,
        parent_failure_causes_mutation_or_rework=True,
        parent_marked_complete=True,
        route_mutation_split_node=True,
        stale_frontier_reset_to_mutated_subtree=True,
        display_depth=2,
        user_display_uses_shallow_projection=True,
        user_display_leaks_deep_tree=False,
        active_path_breadcrumb_visible=True,
        hidden_leaf_progress_visible=True,
        pmk_decomposition_memory_written=True,
        pmk_split_stop_merge_rationale_written=True,
        final_ledger_covers_deep_leaves=True,
        final_ledger_covers_parent_reviews=True,
    )


def _scenario_state(scenario: str) -> State:
    state = _valid_recursive_state()
    if scenario == INTENDED_RECURSIVE_ROUTE:
        return state
    if scenario == FIXED_TWO_LAYER_COMPLEX_ROUTE:
        return replace(
            state,
            scenario=scenario,
            canonical_tree_depth=2,
            route_has_module_nodes=False,
            non_leaf_nodes_have_children=False,
        )
    if scenario == COARSE_LEAF_MARKED_READY:
        return replace(
            state,
            scenario=scenario,
            leaf_worker_executable_without_replanning=False,
            leaf_single_outcome=False,
        )
    if scenario == OVER_SPLIT_LEAF_STEPS:
        return replace(
            state,
            scenario=scenario,
            over_split_operational_steps=True,
            over_split_independent_acceptance_value=False,
        )
    if scenario == REVIEWER_SKIPS_DEPTH_REVIEW:
        return replace(
            state,
            scenario=scenario,
            reviewer_checked_under_decomposition=False,
            reviewer_checked_over_decomposition=False,
            reviewer_blocks_bad_depth=False,
        )
    if scenario == PARENT_DISPATCHED_TO_WORKER:
        return replace(
            state,
            scenario=scenario,
            active_node_has_children=True,
            dispatched_node_kind="parent",
            router_dispatches_only_leaf_nodes=False,
        )
    if scenario == UNREADY_LEAF_DISPATCHED:
        return replace(
            state,
            scenario=scenario,
            all_dispatchable_leaves_ready=False,
            dispatched_leaf_readiness_status="fail",
        )
    if scenario == PARENT_REVIEW_SKIPPED:
        return replace(
            state,
            scenario=scenario,
            parent_children_completed=True,
            parent_backward_review_required=True,
            parent_backward_review_passed=False,
            parent_marked_complete=True,
        )
    if scenario == PARENT_FAILURE_ADVANCES:
        return replace(
            state,
            scenario=scenario,
            parent_backward_review_passed=False,
            parent_backward_review_failed=True,
            parent_failure_causes_mutation_or_rework=False,
            parent_marked_complete=True,
        )
    if scenario == MUTATION_FRONTIER_NOT_RESET:
        return replace(
            state,
            scenario=scenario,
            route_mutation_split_node=True,
            stale_frontier_reset_to_mutated_subtree=False,
        )
    if scenario == DISPLAY_LEAKS_DEEP_TREE:
        return replace(
            state,
            scenario=scenario,
            display_depth=4,
            user_display_uses_shallow_projection=False,
            user_display_leaks_deep_tree=True,
        )
    if scenario == DISPLAY_HIDES_ACTIVE_PATH:
        return replace(
            state,
            scenario=scenario,
            active_path_breadcrumb_visible=False,
            hidden_leaf_progress_visible=False,
        )
    if scenario == FINAL_LEDGER_OMITS_DEEP_LEAF:
        return replace(
            state,
            scenario=scenario,
            final_ledger_covers_deep_leaves=False,
        )
    if scenario == MISSING_DECOMPOSITION_MEMORY:
        return replace(
            state,
            scenario=scenario,
            pmk_decomposition_memory_written=False,
            pmk_split_stop_merge_rationale_written=False,
        )
    return replace(state, scenario=scenario)


def protocol_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.task_complexity == "complex":
        if not state.pm_full_route_tree_written:
            failures.append("PM did not write the canonical full route tree")
        if state.canonical_tree_depth <= 2:
            failures.append("complex route was accepted with fixed two-layer depth")
        if not (state.route_has_parent_nodes and state.route_has_leaf_nodes and state.non_leaf_nodes_have_children):
            failures.append("recursive route tree lacks parent-to-leaf structure")

    if not state.leaf_readiness_gate_defined:
        failures.append("leaf readiness gate is missing")
    if not state.all_dispatchable_leaves_ready:
        failures.append("dispatchable leaf lacks passing leaf-readiness gate")
    if not (
        state.leaf_single_outcome
        and state.leaf_worker_executable_without_replanning
        and state.leaf_proof_defined
        and state.leaf_dependency_boundary_defined
        and state.leaf_failure_isolation_defined
    ):
        failures.append("leaf is too coarse for direct worker execution")
    if state.over_split_operational_steps and not state.over_split_independent_acceptance_value:
        failures.append("route over-split operational steps without independent acceptance value")

    if not (
        state.reviewer_checked_under_decomposition
        and state.reviewer_checked_over_decomposition
        and state.reviewer_blocks_bad_depth
    ):
        failures.append("reviewer did not check both insufficient depth and over-decomposition")

    if not state.router_knows_active_path:
        failures.append("router lacks active-path state for recursive route")
    if state.worker_packet_registered:
        if state.active_node_has_children or state.dispatched_node_kind != "leaf":
            failures.append("router dispatched a parent or module node to a worker")
        if not state.router_dispatches_only_leaf_nodes:
            failures.append("router dispatch policy is not leaf-only")
        if state.dispatched_leaf_readiness_status != "pass":
            failures.append("router dispatched a leaf without a passed readiness gate")

    if state.parent_children_completed and state.parent_backward_review_required:
        if state.parent_marked_complete and not state.parent_backward_review_passed:
            failures.append("parent completed without passing backward composition review")
    if state.parent_backward_review_failed and not state.parent_failure_causes_mutation_or_rework:
        failures.append("parent review failure advanced without route mutation or child rework")

    if state.route_mutation_split_node and not state.stale_frontier_reset_to_mutated_subtree:
        failures.append("route mutation split node without resetting stale frontier")

    if state.user_display_leaks_deep_tree or state.display_depth > 2 or not state.user_display_uses_shallow_projection:
        failures.append("user display leaked the deep internal route tree")
    if not (state.active_path_breadcrumb_visible and state.hidden_leaf_progress_visible):
        failures.append("user display hides active deep path or hidden leaf progress")

    if not (state.pmk_decomposition_memory_written and state.pmk_split_stop_merge_rationale_written):
        failures.append("PMK route memory lacks decomposition rationale")
    if not state.final_ledger_covers_deep_leaves:
        failures.append("final route-wide ledger omits deep leaf nodes")
    if not state.final_ledger_covers_parent_reviews:
        failures.append("final route-wide ledger omits parent backward reviews")

    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _scenario_state(scenario))
        return

    failures = protocol_failures(state)
    if failures:
        yield Transition(
            f"reject_{state.scenario}",
            replace(state, status="rejected", terminal_reason="; ".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{state.scenario}",
            replace(state, status="accepted", terminal_reason="recursive_decomposition_contract_ok"),
        )


def accepts_only_valid_recursive_routes(state: State, trace) -> InvariantResult:
    del trace
    failures = protocol_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("invalid recursive decomposition route was accepted")
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("valid recursive decomposition route was rejected")
    return InvariantResult.pass_()


def worker_dispatch_is_leaf_only(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in protocol_failures(state):
        if "dispatched" in failure or "leaf-only" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def reviewer_depth_gate_is_required(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in protocol_failures(state):
        if "reviewer did not check" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def parent_review_composes_children(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in protocol_failures(state):
        if "parent" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def display_projection_stays_shallow_but_locatable(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in protocol_failures(state):
        if "display" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


def route_memory_and_ledger_cover_deep_tree(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "accepted":
        return InvariantResult.pass_()
    for failure in protocol_failures(state):
        if "PMK" in failure or "ledger" in failure:
            return InvariantResult.fail(failure)
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="accepts_only_valid_recursive_routes",
        description="Only the full recursive route protocol can be accepted.",
        predicate=accepts_only_valid_recursive_routes,
    ),
    Invariant(
        name="worker_dispatch_is_leaf_only",
        description="Worker packets may target only ready leaf nodes.",
        predicate=worker_dispatch_is_leaf_only,
    ),
    Invariant(
        name="reviewer_depth_gate_is_required",
        description="Reviewer must check both insufficient and excessive decomposition.",
        predicate=reviewer_depth_gate_is_required,
    ),
    Invariant(
        name="parent_review_composes_children",
        description="Parent nodes must pass backward composition review before completion.",
        predicate=parent_review_composes_children,
    ),
    Invariant(
        name="display_projection_stays_shallow_but_locatable",
        description="User display stays shallow while exposing active deep path and progress.",
        predicate=display_projection_stays_shallow_but_locatable,
    ),
    Invariant(
        name="route_memory_and_ledger_cover_deep_tree",
        description="PMK route memory and final ledger cover decomposition and deep leaves.",
        predicate=route_memory_and_ledger_cover_deep_tree,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


def build_workflow() -> Workflow:
    return Workflow((RecursiveDecompositionStep(),), name="flowpilot_recursive_decomposition")


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and not protocol_failures(state)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def hazard_states() -> dict[str, State]:
    return {scenario: _scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


def intended_plan_state() -> State:
    return _scenario_state(INTENDED_RECURSIVE_ROUTE)
