"""FlowGuard model for FlowPilot parent/child model hierarchy.

This model reviews the hierarchy used to keep FlowPilot's heavyweight
FlowGuard parents inspectable. It does not expand child state graphs. It
checks that oversized parents, focused child models, partition ownership,
freshness, overlap, and heavyweight-regression obligations stay explicit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple, Sequence

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


HEAVYWEIGHT_STATE_THRESHOLD = 10_000

PARENT_MODELS = ("meta", "capability")

PARTITION_ITEMS = (
    "startup",
    "material_intake",
    "product_architecture",
    "crew_and_heartbeat",
    "router_daemon_resume",
    "packet_and_role_authority",
    "child_skill_capability",
    "terminal_ledger",
    "evidence_mesh_and_install_sync",
)


@dataclass(frozen=True, slots=True)
class State:
    scenario: str = "new"
    status: str = "new"  # new | selected | accepted | rejected
    decision: str = "none"
    heavyweight_parent_registered: bool = False
    parent_exceeds_threshold: bool = False
    split_review_required: bool = False
    partition_map_written: bool = False
    partition_coverage_complete: bool = False
    partition_out_of_scope_explicit: bool = True
    shared_kernel_declared: bool = True
    sibling_ownership_overlap: bool = False
    child_inventory_complete: bool = False
    child_evidence_registered: bool = False
    child_evidence_current: bool = True
    child_skipped_required_checks_hidden: bool = False
    child_expands_parent_graph: bool = False
    authority_mesh_used_as_partition_model: bool = False
    heavy_full_regression_current: bool = False
    hierarchy_claims_release_green: bool = False
    background_run_has_exit_artifact: bool = True
    background_run_has_valid_result_or_proof: bool = True
    background_progress_claimed_as_pass: bool = False


@dataclass(frozen=True, slots=True)
class Tick:
    """One hierarchy decision step."""


@dataclass(frozen=True, slots=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_hierarchy(name: str) -> State:
    return State(
        scenario=name,
        status="selected",
        decision="hierarchy_green_background_regression_required",
        heavyweight_parent_registered=True,
        parent_exceeds_threshold=True,
        split_review_required=True,
        partition_map_written=True,
        partition_coverage_complete=True,
        shared_kernel_declared=True,
        child_inventory_complete=True,
        child_evidence_registered=True,
        child_evidence_current=True,
        heavy_full_regression_current=False,
        hierarchy_claims_release_green=False,
    )


SCENARIOS: dict[str, State] = {
    "valid_hierarchy_with_background_obligation": _valid_hierarchy(
        "valid_hierarchy_with_background_obligation"
    ),
    "valid_release_hierarchy_with_current_heavy_proof": replace(
        _valid_hierarchy("valid_release_hierarchy_with_current_heavy_proof"),
        decision="hierarchy_green_release_candidate",
        heavy_full_regression_current=True,
        hierarchy_claims_release_green=True,
    ),
    "heavy_parent_without_split_review": replace(
        _valid_hierarchy("heavy_parent_without_split_review"),
        split_review_required=False,
    ),
    "parent_partition_gap": replace(
        _valid_hierarchy("parent_partition_gap"),
        partition_coverage_complete=False,
        partition_out_of_scope_explicit=False,
    ),
    "sibling_ownership_overlap": replace(
        _valid_hierarchy("sibling_ownership_overlap"),
        sibling_ownership_overlap=True,
    ),
    "stale_child_evidence_used": replace(
        _valid_hierarchy("stale_child_evidence_used"),
        child_evidence_current=False,
    ),
    "hidden_child_skipped_checks": replace(
        _valid_hierarchy("hidden_child_skipped_checks"),
        child_skipped_required_checks_hidden=True,
    ),
    "release_green_without_heavy_parent_proof": replace(
        _valid_hierarchy("release_green_without_heavy_parent_proof"),
        hierarchy_claims_release_green=True,
        heavy_full_regression_current=False,
        decision="hierarchy_green_release_candidate",
    ),
    "background_progress_only_claimed_pass": replace(
        _valid_hierarchy("background_progress_only_claimed_pass"),
        background_run_has_exit_artifact=False,
        background_run_has_valid_result_or_proof=False,
        background_progress_claimed_as_pass=True,
    ),
    "child_model_inlines_parent_graph": replace(
        _valid_hierarchy("child_model_inlines_parent_graph"),
        child_expands_parent_graph=True,
    ),
    "authority_mesh_confused_with_partition": replace(
        _valid_hierarchy("authority_mesh_confused_with_partition"),
        authority_mesh_used_as_partition_model=True,
    ),
    "missing_child_inventory": replace(
        _valid_hierarchy("missing_child_inventory"),
        child_inventory_complete=False,
        child_evidence_registered=False,
    ),
}

VALID_SCENARIOS = {
    "valid_hierarchy_with_background_obligation",
    "valid_release_hierarchy_with_current_heavy_proof",
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def hierarchy_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.parent_exceeds_threshold and not state.heavyweight_parent_registered:
        failures.append("heavy_parent_not_registered")
    if state.parent_exceeds_threshold and not state.split_review_required:
        failures.append("heavy_parent_split_review_missing")
    if not state.partition_map_written:
        failures.append("parent_partition_map_missing")
    if not state.partition_coverage_complete and not state.partition_out_of_scope_explicit:
        failures.append("parent_partition_coverage_gap")
    if state.sibling_ownership_overlap and not state.shared_kernel_declared:
        failures.append("unsafe_sibling_ownership_overlap")
    if state.sibling_ownership_overlap:
        failures.append("sibling_overlap_requires_explicit_shared_kernel_or_refactor")
    if not state.child_inventory_complete or not state.child_evidence_registered:
        failures.append("child_model_inventory_incomplete")
    if not state.child_evidence_current:
        failures.append("child_evidence_stale_or_foreign")
    if state.child_skipped_required_checks_hidden:
        failures.append("child_skipped_required_checks_hidden")
    if state.child_expands_parent_graph:
        failures.append("child_model_must_not_inline_parent_state_graph")
    if state.authority_mesh_used_as_partition_model:
        failures.append("authority_mesh_cannot_substitute_for_partition_map")
    if state.hierarchy_claims_release_green and not state.heavy_full_regression_current:
        failures.append("release_claim_requires_current_heavy_parent_regression")
    if state.background_progress_claimed_as_pass and (
        not state.background_run_has_exit_artifact
        or not state.background_run_has_valid_result_or_proof
    ):
        failures.append("background_progress_is_not_completion_evidence")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        terminal = "rejected" if hierarchy_failures(state) else "accepted"
        label = f"{terminal.removesuffix('ed')}_{state.scenario}"
        yield Transition(label, replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


class ModelHierarchyStep:
    """Model one FlowPilot model hierarchy decision.

    Input x State -> Set(Output x State)
    reads: model inventory, child result metadata, parent result/proof metadata,
    partition ownership, background run artifacts
    writes: hierarchy decision and heavyweight-regression obligation
    idempotency: pure classification of model evidence and partition metadata
    """

    name = "ModelHierarchyStep"
    input_description = "model hierarchy tick"
    output_description = "accepted or rejected hierarchy classification"
    reads = (
        "model_inventory",
        "child_result_metadata",
        "parent_result_proof_metadata",
        "partition_map",
        "background_regression_artifacts",
    )
    writes = ("hierarchy_decision", "heavy_parent_regression_obligation")
    idempotency = "pure evidence classification keyed by model id and source fingerprint"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: Sequence[object]) -> InvariantResult:
    if state.status == "accepted":
        failures = hierarchy_failures(state)
        if failures:
            return InvariantResult.fail(f"accepted unsafe hierarchy: {failures}")
    if state.status == "rejected" and not hierarchy_failures(state):
        return InvariantResult.fail("rejected a valid hierarchy")
    return InvariantResult.pass_()


def heavy_parent_requires_split_review(state: State, _trace: Sequence[object]) -> InvariantResult:
    if state.status == "accepted" and state.parent_exceeds_threshold and not state.split_review_required:
        return InvariantResult.fail("heavy parent accepted without split review")
    return InvariantResult.pass_()


def parent_partitions_must_be_covered(state: State, _trace: Sequence[object]) -> InvariantResult:
    if state.status == "accepted" and not state.partition_coverage_complete:
        return InvariantResult.fail("accepted hierarchy with uncovered parent partition")
    return InvariantResult.pass_()


def release_claim_requires_full_regression(state: State, _trace: Sequence[object]) -> InvariantResult:
    if (
        state.status == "accepted"
        and state.hierarchy_claims_release_green
        and not state.heavy_full_regression_current
    ):
        return InvariantResult.fail("release hierarchy accepted without current heavy parent regression")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted hierarchy decisions cannot contain known split, coverage, freshness, or regression failures.",
        accepted_states_are_safe,
    ),
    Invariant(
        "heavy_parent_requires_split_review",
        "Oversized parent models require explicit split review before hierarchy acceptance.",
        heavy_parent_requires_split_review,
    ),
    Invariant(
        "parent_partitions_must_be_covered",
        "Parent-space items must be covered or explicitly out of scope.",
        parent_partitions_must_be_covered,
    ),
    Invariant(
        "release_claim_requires_full_regression",
        "Release-level hierarchy claims require current heavyweight parent regression evidence.",
        release_claim_requires_full_regression,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


def build_workflow() -> Workflow:
    return Workflow((ModelHierarchyStep(),), name="flowpilot_model_hierarchy")


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: hierarchy_failures(state) for name, state in hazard_states().items()}
