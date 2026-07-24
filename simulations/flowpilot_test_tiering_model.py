"""FlowGuard model for FlowPilot tiered test validation.

Risk Purpose Header:
This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to
review the FlowPilot test-tiering workflow. It guards against slow regressions
entering the fast loop, root pytest collection scanning backup tests, hidden
child-suite skips, stale evidence, release gates disappearing from routine
reports, and background progress being treated as completion. Run or update it
when changing pytest configuration, test tier ownership, background test
artifacts, or install-sync validation surfaces.

Companion command:
python simulations/run_flowpilot_test_tiering_checks.py --json-out simulations/flowpilot_test_tiering_results.json
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple, Sequence

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


BACKGROUND_ARTIFACTS = ("out", "err", "combined", "exit", "meta")


@dataclass(frozen=True, slots=True)
class State:
    scenario: str = "new"
    status: str = "new"  # new | selected | accepted | rejected
    tier_scope: str = "routine"  # routine | router | integration | release
    parent_tier_declared: bool = False
    child_suites_declared: bool = False
    child_owner_registered: bool = False
    duplicate_child_owner: bool = False
    hidden_skipped_tests: bool = False
    child_evidence_current: bool = True
    canonical_text_normalized: bool = True
    snapshot_is_provenance_only: bool = True
    impact_mapping_complete: bool = True
    impact_action: str = "execute"  # reuse | execute | blocked
    reuse_ticket_current: bool = True
    blanket_rerun_on_snapshot_mismatch: bool = False
    shared_input_selects_every_owner: bool = False
    blocked_falls_back_to_run_all: bool = False
    receipt_consumer_relaunches_heavy_owner: bool = False
    mta_supplements_after_upstream: bool = True
    pytest_scoped_to_tests: bool = True
    backup_tmp_excluded: bool = True
    fast_tier_foreground_safe: bool = True
    long_regression_in_fast_tier: bool = False
    public_release_in_fast_tier: bool = False
    coverage_sweep_blocks_fast_tier: bool = False
    router_slice_import_ok: bool = True
    router_slice_counted_green: bool = False
    router_child_commands_granular: bool = True
    router_k_shards_disjoint: bool = True
    router_k_patterns_current: bool = True
    slow_router_aggregate_command_present: bool = False
    background_requested: bool = False
    background_artifacts_declared: bool = False
    background_exit_artifact_present: bool = False
    background_exit_inspected: bool = False
    exit_published_before_terminal_meta: bool = False
    background_progress_claimed_as_pass: bool = False
    background_timeout_enforced: bool = True
    background_interpreter_bound_to_owner: bool = True
    background_interpreter_is_direct_process_owner: bool = True
    shared_runtime_resources_serialized: bool = True
    background_descendant_settlement_bounded: bool = True
    background_descendant_lineage_ordered: bool = True
    background_sibling_isolation_preserved: bool = True
    background_surviving_descendants_fail_closed: bool = True
    json_write_readback_bounded: bool = True
    release_obligation_visible: bool = True
    release_required: bool = False
    release_suite_run_or_backgrounded: bool = False
    release_public_check_after_model_proofs: bool = True
    release_embeds_final_confidence_consumer: bool = False
    testmesh_mta_final_confidence_cycle: bool = False
    install_check_after_topology_writers: bool = True
    install_sync_required: bool = False
    install_sync_planned: bool = False


@dataclass(frozen=True, slots=True)
class Tick:
    """One parent/child test-tier decision."""


@dataclass(frozen=True, slots=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_fast(name: str) -> State:
    return State(
        scenario=name,
        status="selected",
        tier_scope="routine",
        parent_tier_declared=True,
        child_suites_declared=True,
        child_owner_registered=True,
        fast_tier_foreground_safe=True,
        install_sync_required=True,
        install_sync_planned=True,
    )


def _valid_router(name: str) -> State:
    return replace(
        _valid_fast(name),
        tier_scope="router",
        router_slice_import_ok=True,
        router_slice_counted_green=True,
        router_child_commands_granular=True,
        router_k_shards_disjoint=True,
        slow_router_aggregate_command_present=False,
    )


def _valid_background(name: str, *, release: bool = False) -> State:
    return replace(
        _valid_fast(name),
        tier_scope="release" if release else "integration",
        background_requested=True,
        background_artifacts_declared=True,
        background_exit_artifact_present=True,
        background_exit_inspected=True,
        release_required=release,
        release_suite_run_or_backgrounded=release,
    )


SCENARIOS: dict[str, State] = {
    "valid_fast_tier": _valid_fast("valid_fast_tier"),
    "valid_router_child_tier": _valid_router("valid_router_child_tier"),
    "valid_background_integration_tier": _valid_background(
        "valid_background_integration_tier"
    ),
    "valid_release_background_tier": _valid_background(
        "valid_release_background_tier", release=True
    ),
    "root_pytest_scans_backup_tests": replace(
        _valid_fast("root_pytest_scans_backup_tests"),
        pytest_scoped_to_tests=False,
        backup_tmp_excluded=False,
    ),
    "foreground_full_regression": replace(
        _valid_fast("foreground_full_regression"),
        long_regression_in_fast_tier=True,
        fast_tier_foreground_safe=False,
    ),
    "public_release_in_fast_tier": replace(
        _valid_fast("public_release_in_fast_tier"),
        public_release_in_fast_tier=True,
        fast_tier_foreground_safe=False,
    ),
    "coverage_sweep_blocks_fast_tier": replace(
        _valid_fast("coverage_sweep_blocks_fast_tier"),
        coverage_sweep_blocks_fast_tier=True,
        fast_tier_foreground_safe=False,
    ),
    "missing_child_owner": replace(
        _valid_fast("missing_child_owner"),
        child_owner_registered=False,
    ),
    "duplicate_child_owner": replace(
        _valid_fast("duplicate_child_owner"),
        duplicate_child_owner=True,
    ),
    "hidden_skipped_tests": replace(
        _valid_fast("hidden_skipped_tests"),
        hidden_skipped_tests=True,
    ),
    "stale_child_evidence_used": replace(
        _valid_fast("stale_child_evidence_used"),
        child_evidence_current=False,
    ),
    "line_ending_transport_forces_execution": replace(
        _valid_fast("line_ending_transport_forces_execution"),
        canonical_text_normalized=False,
    ),
    "global_snapshot_mismatch_stales_every_owner": replace(
        _valid_fast("global_snapshot_mismatch_stales_every_owner"),
        snapshot_is_provenance_only=False,
        blanket_rerun_on_snapshot_mismatch=True,
    ),
    "shared_input_selects_every_owner": replace(
        _valid_fast("shared_input_selects_every_owner"),
        shared_input_selects_every_owner=True,
    ),
    "unmapped_change_falls_back_to_run_all": replace(
        _valid_fast("unmapped_change_falls_back_to_run_all"),
        impact_mapping_complete=False,
        impact_action="execute",
        blocked_falls_back_to_run_all=True,
    ),
    "reused_owner_has_no_current_ticket": replace(
        _valid_fast("reused_owner_has_no_current_ticket"),
        impact_action="reuse",
        reuse_ticket_current=False,
    ),
    "receipt_consumer_relaunches_heavy_owner": replace(
        _valid_fast("receipt_consumer_relaunches_heavy_owner"),
        receipt_consumer_relaunches_heavy_owner=True,
    ),
    "mta_supplement_runs_before_upstream_owner": replace(
        _valid_fast("mta_supplement_runs_before_upstream_owner"),
        mta_supplements_after_upstream=False,
    ),
    "router_slice_import_broken_counted_green": replace(
        _valid_router("router_slice_import_broken_counted_green"),
        router_slice_import_ok=False,
        router_slice_counted_green=True,
    ),
    "router_child_tier_keeps_slow_aggregate": replace(
        _valid_router("router_child_tier_keeps_slow_aggregate"),
        router_child_commands_granular=False,
        slow_router_aggregate_command_present=True,
    ),
    "router_child_tier_duplicates_k_shards": replace(
        _valid_router("router_child_tier_duplicates_k_shards"),
        router_k_shards_disjoint=False,
    ),
    "router_child_tier_stale_k_pattern": replace(
        _valid_router("router_child_tier_stale_k_pattern"),
        router_k_patterns_current=False,
    ),
    "background_progress_only_claimed_pass": replace(
        _valid_background("background_progress_only_claimed_pass"),
        background_exit_artifact_present=False,
        background_exit_inspected=False,
        background_progress_claimed_as_pass=True,
    ),
    "background_missing_artifact_set": replace(
        _valid_background("background_missing_artifact_set"),
        background_artifacts_declared=False,
    ),
    "background_exit_precedes_terminal_meta": replace(
        _valid_background("background_exit_precedes_terminal_meta"),
        exit_published_before_terminal_meta=True,
    ),
    "background_running_without_timeout_guard": replace(
        _valid_background("background_running_without_timeout_guard"),
        background_exit_artifact_present=False,
        background_exit_inspected=False,
        background_progress_claimed_as_pass=True,
        background_timeout_enforced=False,
    ),
    "background_inner_interpreter_follows_external_upgrade": replace(
        _valid_background("background_inner_interpreter_follows_external_upgrade"),
        background_interpreter_bound_to_owner=False,
    ),
    "background_windows_venv_shim_exits_before_process_owner": replace(
        _valid_background("background_windows_venv_shim_exits_before_process_owner"),
        background_interpreter_is_direct_process_owner=False,
    ),
    "background_shared_runtime_resource_race": replace(
        _valid_background("background_shared_runtime_resource_race"),
        shared_runtime_resources_serialized=False,
    ),
    "background_descendant_settlement_missing": replace(
        _valid_background("background_descendant_settlement_missing"),
        background_descendant_settlement_bounded=False,
    ),
    "background_predating_process_misclassified_as_descendant": replace(
        _valid_background("background_predating_process_misclassified_as_descendant"),
        background_descendant_lineage_ordered=False,
    ),
    "background_sibling_misclassified_through_reused_parent_pid": replace(
        _valid_background(
            "background_sibling_misclassified_through_reused_parent_pid"
        ),
        background_sibling_isolation_preserved=False,
    ),
    "background_surviving_descendant_promoted": replace(
        _valid_background("background_surviving_descendant_promoted"),
        background_surviving_descendants_fail_closed=False,
    ),
    "json_write_readback_can_hang_control_gate": replace(
        _valid_background("json_write_readback_can_hang_control_gate"),
        json_write_readback_bounded=False,
    ),
    "release_obligation_hidden": replace(
        _valid_fast("release_obligation_hidden"),
        release_obligation_visible=False,
        release_required=True,
        release_suite_run_or_backgrounded=False,
    ),
    "release_claim_without_release_suite": replace(
        _valid_fast("release_claim_without_release_suite"),
        tier_scope="release",
        release_required=True,
        release_suite_run_or_backgrounded=False,
    ),
    "release_public_check_races_model_proofs": replace(
        _valid_background("release_public_check_races_model_proofs", release=True),
        release_public_check_after_model_proofs=False,
    ),
    "release_embeds_final_confidence_consumer": replace(
        _valid_background("release_embeds_final_confidence_consumer", release=True),
        release_embeds_final_confidence_consumer=True,
    ),
    "testmesh_mta_final_confidence_dependency_cycle": replace(
        _valid_background("testmesh_mta_final_confidence_dependency_cycle", release=True),
        testmesh_mta_final_confidence_cycle=True,
    ),
    "install_check_races_topology_writers": replace(
        _valid_background("install_check_races_topology_writers"),
        install_check_after_topology_writers=False,
    ),
    "install_sync_skipped_after_tool_change": replace(
        _valid_fast("install_sync_skipped_after_tool_change"),
        install_sync_required=True,
        install_sync_planned=False,
    ),
}

VALID_SCENARIOS = {
    "valid_fast_tier",
    "valid_router_child_tier",
    "valid_background_integration_tier",
    "valid_release_background_tier",
}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def test_tier_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.parent_tier_declared:
        failures.append("parent_tier_missing")
    if not state.child_suites_declared:
        failures.append("child_suites_missing")
    if not state.child_owner_registered:
        failures.append("child_owner_missing")
    if state.duplicate_child_owner:
        failures.append("duplicate_child_owner")
    if state.hidden_skipped_tests:
        failures.append("hidden_skipped_tests")
    if not state.child_evidence_current:
        failures.append("child_evidence_stale")
    if not state.canonical_text_normalized:
        failures.append("controlled_text_not_canonicalized")
    if (
        not state.snapshot_is_provenance_only
        or state.blanket_rerun_on_snapshot_mismatch
    ):
        failures.append("global_snapshot_used_as_blanket_invalidation_authority")
    if state.shared_input_selects_every_owner:
        failures.append("shared_input_selected_blanket_tier_execution")
    if not state.impact_mapping_complete and state.impact_action != "blocked":
        failures.append("impact_mapping_missing_not_blocked")
    if state.blocked_falls_back_to_run_all:
        failures.append("blocked_impact_falls_back_to_run_all")
    if state.impact_action == "reuse" and not state.reuse_ticket_current:
        failures.append("reused_owner_missing_current_ticket")
    if state.receipt_consumer_relaunches_heavy_owner:
        failures.append("receipt_consumer_relaunches_heavy_owner")
    if not state.mta_supplements_after_upstream:
        failures.append("mta_supplement_precedes_upstream_owner")
    if not state.pytest_scoped_to_tests or not state.backup_tmp_excluded:
        failures.append("pytest_collection_not_scoped")
    if state.long_regression_in_fast_tier or not state.fast_tier_foreground_safe:
        failures.append("fast_tier_not_foreground_safe")
    if state.public_release_in_fast_tier:
        failures.append("public_release_check_in_fast_tier")
    if state.coverage_sweep_blocks_fast_tier:
        failures.append("coverage_sweep_blocks_fast_tier")
    if state.router_slice_counted_green and not state.router_slice_import_ok:
        failures.append("router_slice_import_failure_counted_green")
    if state.tier_scope == "router" and (
        not state.router_child_commands_granular or state.slow_router_aggregate_command_present
    ):
        failures.append("router_child_commands_not_granular")
    if state.tier_scope == "router" and not state.router_k_shards_disjoint:
        failures.append("router_child_shards_duplicate_test_selection")
    if state.tier_scope == "router" and not state.router_k_patterns_current:
        failures.append("router_child_shard_pattern_stale_or_empty")
    if state.background_requested and not state.background_artifacts_declared:
        failures.append("background_artifact_set_missing")
    if state.background_progress_claimed_as_pass and (
        not state.background_exit_artifact_present or not state.background_exit_inspected
    ):
        failures.append("background_progress_is_not_completion_evidence")
    if state.exit_published_before_terminal_meta:
        failures.append("background_exit_precedes_terminal_meta")
    if state.background_requested and not state.background_timeout_enforced:
        failures.append("background_timeout_not_enforced")
    if state.background_requested and not state.background_interpreter_bound_to_owner:
        failures.append("background_interpreter_not_bound_to_execution_owner")
    if state.background_requested and not state.background_interpreter_is_direct_process_owner:
        failures.append("background_interpreter_shim_not_direct_process_owner")
    if state.background_requested and not state.shared_runtime_resources_serialized:
        failures.append("background_shared_runtime_resource_not_serialized")
    if state.background_requested and not state.background_descendant_settlement_bounded:
        failures.append("background_descendant_settlement_not_bounded")
    if state.background_requested and not state.background_descendant_lineage_ordered:
        failures.append("background_descendant_lineage_not_ordered")
    if state.background_requested and not state.background_sibling_isolation_preserved:
        failures.append("background_sibling_isolation_not_preserved")
    if state.background_requested and not state.background_surviving_descendants_fail_closed:
        failures.append("background_surviving_descendants_not_fail_closed")
    if state.background_requested and not state.json_write_readback_bounded:
        failures.append("json_write_readback_not_bounded")
    if state.tier_scope == "release" and not state.release_suite_run_or_backgrounded:
        failures.append("release_scope_missing_release_suite")
    if (
        state.release_required
        and not state.release_suite_run_or_backgrounded
        and not state.release_obligation_visible
    ):
        failures.append("release_obligation_hidden")
    if (
        state.tier_scope == "release"
        and state.background_requested
        and not state.release_public_check_after_model_proofs
    ):
        failures.append("release_public_check_races_model_proofs")
    if state.release_embeds_final_confidence_consumer:
        failures.append("release_tier_embeds_terminal_consumer")
    if state.testmesh_mta_final_confidence_cycle:
        failures.append("testmesh_mta_final_confidence_dependency_cycle")
    if not state.install_check_after_topology_writers:
        failures.append("install_check_races_topology_writers")
    if state.install_sync_required and not state.install_sync_planned:
        failures.append("install_sync_not_planned")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        terminal = "rejected" if test_tier_failures(state) else "accepted"
        label = f"{terminal.removesuffix('ed')}_{state.scenario}"
        yield Transition(label, replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


class TestTierStep:
    """Model one tiering decision.

    Input x State -> Set(Output x State)
    reads: pytest config, tier command registry, child-suite ownership,
    background artifact metadata, release obligations, install sync plan
    writes: accepted or rejected tier confidence
    idempotency: pure classification keyed by tier name and evidence artifact
    """

    name = "TestTierStep"
    input_description = "test tier tick"
    output_description = "accepted or rejected test-tier confidence"
    reads = (
        "pytest_config",
        "tier_command_registry",
        "child_suite_ownership",
        "background_artifacts",
        "release_obligations",
        "testmesh_mta_final_confidence_dependency_graph",
        "background_stage_order",
        "background_exclusive_resource",
        "background_interpreter_launch_plan",
        "background_process_tree_identity",
        "background_process_tree_sibling_isolation",
        "install_sync_plan",
    )
    writes = ("tier_confidence", "deferred_release_obligation")
    idempotency = "pure classification of tier evidence"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: Sequence[object]) -> InvariantResult:
    if state.status == "accepted":
        failures = test_tier_failures(state)
        if failures:
            return InvariantResult.fail(f"accepted unsafe test tier: {failures}")
    if state.status == "rejected" and not test_tier_failures(state):
        return InvariantResult.fail("rejected a valid test tier")
    return InvariantResult.pass_()


def fast_tier_excludes_long_release_work(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if state.status == "accepted" and state.tier_scope == "routine":
        if state.long_regression_in_fast_tier or state.public_release_in_fast_tier:
            return InvariantResult.fail("accepted fast tier with long or release-only work")
    return InvariantResult.pass_()


def background_completion_requires_exit_evidence(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if (
        state.status == "accepted"
        and state.background_requested
        and (not state.background_exit_artifact_present or not state.background_exit_inspected)
    ):
        return InvariantResult.fail("accepted background tier without inspected exit evidence")
    if state.status == "accepted" and state.background_requested and not state.background_timeout_enforced:
        return InvariantResult.fail("accepted background tier without timeout guard")
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_interpreter_bound_to_owner
    ):
        return InvariantResult.fail(
            "accepted background tier whose inner interpreter can follow an external upgrade"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_interpreter_is_direct_process_owner
    ):
        return InvariantResult.fail(
            "accepted background tier whose short-lived interpreter shim is the process owner"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.shared_runtime_resources_serialized
    ):
        return InvariantResult.fail(
            "accepted background tier with overlapping shared runtime resources"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_descendant_settlement_bounded
    ):
        return InvariantResult.fail(
            "accepted background tier without bounded descendant settlement"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_descendant_lineage_ordered
    ):
        return InvariantResult.fail(
            "accepted background tier that could terminate a process predating its owner"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_sibling_isolation_preserved
    ):
        return InvariantResult.fail(
            "accepted background tier that could classify a sibling owner as a descendant"
        )
    if (
        state.status == "accepted"
        and state.background_requested
        and not state.background_surviving_descendants_fail_closed
    ):
        return InvariantResult.fail(
            "accepted background tier that promoted a surviving descendant"
        )
    if state.status == "accepted" and state.background_requested and not state.json_write_readback_bounded:
        return InvariantResult.fail("accepted background tier with unbounded JSON write readback")
    return InvariantResult.pass_()


def release_obligation_must_remain_visible(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if (
        state.status == "accepted"
        and state.release_required
        and not state.release_suite_run_or_backgrounded
        and not state.release_obligation_visible
    ):
        return InvariantResult.fail("accepted tier hid pending release obligation")
    return InvariantResult.pass_()


def final_confidence_dependency_must_be_acyclic(
    state: State, _trace: Sequence[object]
) -> InvariantResult:
    if state.status == "accepted" and (
        state.release_embeds_final_confidence_consumer
        or state.testmesh_mta_final_confidence_cycle
    ):
        return InvariantResult.fail(
            "accepted final-confidence consumer upstream of its own TestMesh/MTA evidence"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted tier decisions cannot contain known collection, ownership, freshness, or evidence failures.",
        accepted_states_are_safe,
    ),
    Invariant(
        "fast_tier_excludes_long_release_work",
        "Fast routine validation cannot include long model or release-only checks.",
        fast_tier_excludes_long_release_work,
    ),
    Invariant(
        "background_completion_requires_exit_evidence",
        "Background completion requires an inspected exit artifact, not progress alone.",
        background_completion_requires_exit_evidence,
    ),
    Invariant(
        "release_obligation_must_remain_visible",
        "Deferred release obligations must remain visible.",
        release_obligation_must_remain_visible,
    ),
    Invariant(
        "final_confidence_dependency_must_be_acyclic",
        "Final confidence is a terminal consumer after TestMesh and strict MTA, never a release-tier input.",
        final_confidence_dependency_must_be_acyclic,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


def build_workflow() -> Workflow:
    return Workflow((TestTierStep(),), name="flowpilot_test_tiering")


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
    return {name: test_tier_failures(state) for name, state in hazard_states().items()}
