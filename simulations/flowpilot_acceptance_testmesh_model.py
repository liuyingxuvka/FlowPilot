"""FlowGuard TestMesh model for FlowPilot acceptance-item registry coverage.

Risk Purpose Header:
This model turns the acceptance-item registry validation claim into a parent
TestMesh. It guards against broad green reports that hide missing fake AI
payload cells, slow foreground timeouts, route-mutation item-disposition gaps,
or terminal replay target drift.

Companion command:
python simulations/run_flowpilot_acceptance_testmesh_checks.py --json-out simulations/flowpilot_acceptance_testmesh_results.json
"""

from __future__ import annotations

from typing import Any, Mapping

from flowguard import (
    TestMeshPlan,
    TestPartitionItem,
    TestSuiteEvidence,
    TestTargetSplitDerivation,
)


TESTMESH_ID = "flowpilot_acceptance_registry_testmesh"

PAYLOAD_CELLS = (
    "registry_missing",
    "registry_orphan_item",
    "route_owner_missing",
    "node_plan_missing_item_projection",
    "worker_result_missing_item_matrix",
    "pm_disposition_missing_item_closure",
    "stale_route_item_used",
    "terminal_segment_missing",
    "terminal_segment_duplicate",
    "terminal_segment_unexpected",
    "terminal_segment_corrected_recovery",
    "terminal_replay_reject_repair_rerun_closure",
    "terminal_supplemental_contract_missing",
    "terminal_supplemental_contract_corrected_recovery",
    "terminal_supplemental_fake_ai_current_body_recovery",
    "terminal_supplemental_final_ledger_projection",
    "terminal_supplemental_round_cap_exhaustion",
    "terminal_hygiene_review_required",
    "terminal_hygiene_required_gap_blocks",
    "terminal_hygiene_supplemental_contract",
    "terminal_hygiene_final_ledger_projection",
    "route_mutation_item_disposition_recovery",
    "ai_contract_semantic_recheck_profile_projection",
    "ai_contract_semantic_recheck_allowed_options_projection",
    "ai_contract_semantic_recheck_forbidden_alias_feedback",
    "ai_contract_semantic_recheck_wrong_value_corrected_retry",
    "ai_contract_all_result_allowed_options_projection",
    "ai_contract_all_result_allowed_options_wrong_value",
    "ai_contract_profile_required_fields_and_types_projection",
    "ai_contract_profile_forbidden_alias_feedback",
)

FORMAL_EXIT_RELEASE_CELLS = (
    "formal_exit_terminal_return_missing",
    "formal_exit_startup_intake_blocks",
)

CHILD_SUITE_IDS = (
    "acceptance_contract_runtime_tests",
    "acceptance_planning_quality_model",
    "acceptance_fake_ai_payload_chaos",
    "acceptance_route_mutation_recovery",
    "acceptance_terminal_replay_payloads",
    "acceptance_terminal_supplemental_repair",
    "acceptance_field_contract_mesh",
    "acceptance_model_test_alignment",
    "acceptance_router_quality_gate_children",
    "acceptance_router_packet_tier",
    "acceptance_router_route_tier",
    "acceptance_router_terminal_tier",
    "acceptance_router_release_tiers",
)

ROUTER_TIER_MAPPINGS = (
    {
        "tier": "router-quality-gates",
        "risk": "slow quality-gate child evidence for acceptance registry, terminal replay, and closure blockers",
        "scope": "routine",
        "evidence_mode": "slow-child",
        "background_recommended": False,
        "deferred_in_routine": False,
    },
    {
        "tier": "router-packets",
        "risk": "current packet/result ownership for acceptance item projection and reissue",
        "scope": "routine",
        "evidence_mode": "child-suite",
        "background_recommended": True,
        "deferred_in_routine": False,
    },
    {
        "tier": "router-route",
        "risk": "route mutation preserves or dispositions active acceptance items",
        "scope": "routine",
        "evidence_mode": "child-suite",
        "background_recommended": True,
        "deferred_in_routine": False,
    },
    {
        "tier": "router-terminal",
        "risk": "terminal replay segment targets and final-review repair-return loop",
        "scope": "routine",
        "evidence_mode": "child-suite",
        "background_recommended": True,
        "deferred_in_routine": False,
    },
    {
        "tier": "integration",
        "risk": "public CLI and fake AI package route through current packet bodies",
        "scope": "release",
        "evidence_mode": "release-child",
        "background_recommended": True,
        "deferred_in_routine": True,
    },
    {
        "tier": "release",
        "risk": "install/sync and broad regression evidence for acceptance-registry release confidence",
        "scope": "release",
        "evidence_mode": "release-child",
        "background_recommended": True,
        "deferred_in_routine": True,
    },
    {
        "tier": "final-confidence",
        "risk": "final done claim consumes current release evidence and formal terminal-return authority rather than progress-only output",
        "scope": "release",
        "evidence_mode": "release-child",
        "background_recommended": True,
        "deferred_in_routine": True,
    },
)


def _partition_items() -> tuple[TestPartitionItem, ...]:
    return (
        TestPartitionItem(
            "registry_compilation",
            "contract",
            "acceptance_contract_runtime_tests",
            "child",
            "PM high-standard contract creates and normalizes acceptance_item_registry.",
            ("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
        ),
        TestPartitionItem(
            "route_item_ownership",
            "route",
            "acceptance_planning_quality_model",
            "child",
            "Every active acceptance item has a route-node owner.",
            ("simulations/flowpilot_planning_quality_model.py",),
        ),
        TestPartitionItem(
            "node_packet_projection",
            "packet",
            "acceptance_contract_runtime_tests",
            "child",
            "Node plans, worker packets, and result matrices carry acceptance item ids.",
            ("tests/test_flowpilot_high_standard_control_flow.py",),
        ),
        TestPartitionItem(
            "pm_disposition_item_closure",
            "workflow",
            "acceptance_fake_ai_payload_chaos",
            "child",
            "PM disposition closes node-owned items through accept/block/waive/supersede arrays.",
            ("simulations/flowpilot_fake_project_rehearsal_cli.py",),
        ),
        TestPartitionItem(
            "ai_contract_projection_and_retry",
            "packet",
            "acceptance_fake_ai_payload_chaos",
            "child",
            "AI-facing contracts expose every finite option, profile-bound field, forbidden alias, and corrected second-round recovery path.",
            (
                "tests/test_flowpilot_ai_contract_projection.py",
                "tests/test_flowpilot_contract_exhaustion_mesh.py",
            ),
        ),
        TestPartitionItem(
            "terminal_replay_segments",
            "closure",
            "acceptance_terminal_replay_payloads",
            "child",
            "Terminal replay uses runtime-issued segment_targets with no missing, duplicate, or unexpected ids.",
            ("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
        ),
        TestPartitionItem(
            "final_review_repair_return",
            "closure",
            "acceptance_terminal_replay_payloads",
            "child",
            "A blocking terminal backward replay returns through PM repair, Reviewer rerun, blocker clearing, and final closure.",
            ("tests/test_flowpilot_core_runtime.py", "tests/test_flowpilot_new_entrypoint.py"),
        ),
        TestPartitionItem(
            "terminal_supplemental_repair_tail",
            "closure",
            "acceptance_terminal_supplemental_repair",
            "child",
            "Terminal replay and final artifact hygiene gaps require PM supplemental repair contracts, projected repair items, existing FlowPilot gates, final ledger closure rows, and a hard three-round stop.",
            (
                "simulations/flowpilot_terminal_supplemental_repair_model.py",
                "tests/test_flowpilot_core_runtime.py",
                "tests/test_flowpilot_fake_project_rehearsal.py",
            ),
        ),
        TestPartitionItem(
            "route_mutation_recovery",
            "route",
            "acceptance_route_mutation_recovery",
            "child",
            "Route mutation preserves or dispositions every acceptance item before terminal closure.",
            ("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
        ),
        TestPartitionItem(
            "field_contract_binding",
            "field",
            "acceptance_field_contract_mesh",
            "child",
            "Acceptance registry and packet-result fields are cataloged and bound to code.",
            ("simulations/flowpilot_field_contract_model.py",),
        ),
        TestPartitionItem(
            "model_test_alignment",
            "alignment",
            "acceptance_model_test_alignment",
            "child",
            "Model obligations, code contracts, and test evidence remain aligned.",
            ("simulations/flowpilot_model_test_alignment_results.json",),
        ),
        TestPartitionItem(
            "slow_quality_gate_evidence",
            "slow-test",
            "acceptance_router_quality_gate_children",
            "child",
            "Slow quality-gate children expose pass/timeout status instead of hiding behind one parent command.",
            ("tests/router_runtime/quality_gates.py",),
        ),
        TestPartitionItem(
            "release_router_tiers",
            "release",
            "acceptance_router_release_tiers",
            "child",
            "Router packet, route, terminal, integration, release, final-confidence, and formal terminal-return evidence remain visible.",
            ("scripts/run_test_tier.py",),
        ),
        TestPartitionItem(
            "formal_exit_authority",
            "release",
            "acceptance_router_release_tiers",
            "child",
            "Formal FlowPilot exit claims require final-preflight terminal_return with controller_stop_allowed=true.",
            ("simulations/flowpilot_final_confidence_gate.py", "skills/flowpilot/assets/flowpilot_new.py"),
        ),
    )


def _tier_child(
    suite_id: str,
    *,
    command: str,
    not_run_reason: str,
    result_path: str = "",
    result_status: str = "not_run",
    evidence_current: bool = False,
    evidence_tier: str = "candidate_only",
    test_count: int = 0,
    exit_code: int | None = None,
    background: bool = False,
    has_exit_artifact: bool = False,
    has_result_artifact: bool = False,
    progress_only: bool = False,
    duration_seconds: float | None = None,
    timeout_seconds: float | None = None,
    stale_reasons: tuple[str, ...] = (),
    release_required: bool = False,
    owns_state: tuple[str, ...] = (),
    owns_side_effects: tuple[str, ...] = (),
) -> TestSuiteEvidence:
    return TestSuiteEvidence(
        suite_id,
        command=command,
        result_status=result_status,
        evidence_tier=evidence_tier,
        evidence_current=evidence_current,
        test_count=test_count if result_status == "passed" else 0,
        exit_code=exit_code,
        result_path=result_path,
        log_root=result_path,
        background=background,
        has_exit_artifact=has_exit_artifact,
        has_result_artifact=has_result_artifact,
        progress_only=progress_only,
        duration_seconds=duration_seconds,
        timeout_seconds=timeout_seconds,
        release_required=release_required,
        not_run_reason="" if result_status == "passed" else not_run_reason,
        stale_reasons=stale_reasons,
        owns_state=owns_state,
        owns_side_effects=owns_side_effects,
    )


def _with_override(defaults: dict[str, Any], overrides: Mapping[str, Any] | None) -> dict[str, Any]:
    merged = dict(defaults)
    if overrides:
        merged.update(dict(overrides))
    return merged


def _release_child(
    suite_id: str,
    *,
    command: str,
    result_path: str,
    release_evidence: bool,
    result_status: str | None = None,
    evidence_current: bool | None = None,
    exit_code: int | None = None,
    progress_only: bool = False,
    background: bool = False,
    has_exit_artifact: bool = True,
    has_result_artifact: bool = True,
    timeout_seconds: float | None = None,
    duration_seconds: float | None = None,
    stale_reasons: tuple[str, ...] = (),
    not_run_reason: str,
    test_count: int,
    owned_leaf_cell_ids: tuple[str, ...] = (),
) -> TestSuiteEvidence:
    status = result_status or ("passed" if release_evidence else "not_run")
    current = evidence_current if evidence_current is not None else release_evidence
    effective_exit_code = exit_code if exit_code is not None else (0 if release_evidence else None)
    return TestSuiteEvidence(
        suite_id,
        command=command,
        result_status=status,
        evidence_tier="external_contract" if release_evidence else "candidate_only",
        evidence_current=current,
        test_count=test_count if status == "passed" else 0,
        exit_code=effective_exit_code,
        result_path=result_path if status == "passed" or has_result_artifact else "",
        background=background,
        has_exit_artifact=has_exit_artifact,
        has_result_artifact=has_result_artifact,
        progress_only=progress_only,
        timeout_seconds=timeout_seconds,
        duration_seconds=duration_seconds,
        release_required=True,
        not_run_reason="" if status == "passed" else not_run_reason,
        stale_reasons=stale_reasons,
        owned_leaf_cell_ids=owned_leaf_cell_ids,
    )


def build_testmesh_plan(
    *,
    release_evidence: bool = False,
    release_result_status: str | None = None,
    release_evidence_current: bool | None = None,
    release_progress_only: bool = False,
    release_background: bool = False,
    release_has_exit_artifact: bool = True,
    release_has_result_artifact: bool = True,
    release_timeout_seconds: float | None = None,
    release_duration_seconds: float | None = None,
    release_stale_reasons: tuple[str, ...] = (),
    release_result_path: str = "tmp/test_background acceptance tier artifacts",
    router_tier_overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> TestMeshPlan:
    tier_overrides = router_tier_overrides or {}
    child_suites = (
        TestSuiteEvidence(
            "acceptance_contract_runtime_tests",
            command=(
                "python -m unittest -v tests.test_flowpilot_high_standard_control_flow "
                "tests.test_flowpilot_core_runtime tests.test_flowpilot_ai_contract_projection"
            ),
            result_status="passed",
            evidence_tier="external_contract",
            test_count=5,
            exit_code=0,
            result_path=(
                "tests/test_flowpilot_high_standard_control_flow.py; "
                "tests/test_flowpilot_core_runtime.py; tests/test_flowpilot_ai_contract_projection.py"
            ),
            owns_state=("accepted_contract", "route_nodes", "packets", "pm_dispositions"),
            owns_side_effects=("runtime_reissue", "final_matrix"),
            owned_leaf_cell_ids=(
                "registry_missing",
                "registry_orphan_item",
                "route_owner_missing",
                "node_plan_missing_item_projection",
                "worker_result_missing_item_matrix",
                "pm_disposition_missing_item_closure",
                "ai_contract_semantic_recheck_profile_projection",
                "ai_contract_semantic_recheck_allowed_options_projection",
                "ai_contract_all_result_allowed_options_projection",
                "ai_contract_profile_required_fields_and_types_projection",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_planning_quality_model",
            command="python simulations/run_flowpilot_planning_quality_checks.py --json-out simulations/flowpilot_planning_quality_results.json",
            result_status="passed",
            evidence_tier="executable_flowguard",
            test_count=62,
            exit_code=0,
            result_path="simulations/flowpilot_planning_quality_results.json",
            owns_state=("planning_quality_state",),
            owns_side_effects=("hazard_detection",),
            owned_leaf_cell_ids=(
                "registry_missing",
                "route_owner_missing",
                "node_plan_missing_item_projection",
                "worker_result_missing_item_matrix",
                "pm_disposition_missing_item_closure",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_fake_ai_payload_chaos",
            command=(
                "python -m unittest -v tests.test_flowpilot_fake_project_rehearsal "
                "tests.test_flowpilot_new_entrypoint tests.test_flowpilot_ai_contract_projection"
            ),
            result_status="passed",
            evidence_tier="external_contract",
            test_count=7,
            exit_code=0,
            result_path=(
                "tests/test_flowpilot_fake_project_rehearsal.py; "
                "tests/test_flowpilot_new_entrypoint.py; tests/test_flowpilot_ai_contract_projection.py"
            ),
            owns_state=("fake_ai_payloads", "opened_packet_body_projection"),
            owns_side_effects=("fake_ai_result_submission",),
            owned_leaf_cell_ids=(
                "pm_disposition_missing_item_closure",
                "terminal_segment_missing",
                "terminal_segment_duplicate",
                "terminal_segment_unexpected",
                "terminal_segment_corrected_recovery",
                "terminal_replay_reject_repair_rerun_closure",
                "terminal_supplemental_fake_ai_current_body_recovery",
                "ai_contract_semantic_recheck_forbidden_alias_feedback",
                "ai_contract_semantic_recheck_wrong_value_corrected_retry",
                "ai_contract_all_result_allowed_options_wrong_value",
                "ai_contract_profile_forbidden_alias_feedback",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_route_mutation_recovery",
            command="python simulations/run_flowpilot_fake_project_rehearsal_checks.py --scenario route_mutation_recovery",
            result_status="passed",
            evidence_tier="external_contract",
            test_count=1,
            exit_code=0,
            result_path="simulations/flowpilot_fake_project_rehearsal_results.json",
            owns_state=("route_frontier", "replacement_route_nodes"),
            owns_side_effects=("route_mutation", "frontier_rewrite"),
            owned_leaf_cell_ids=(
                "stale_route_item_used",
                "route_mutation_item_disposition_recovery",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_terminal_replay_payloads",
            command="python -m unittest -v tests.test_flowpilot_core_runtime terminal replay payload cases",
            result_status="passed",
            evidence_tier="external_contract",
            test_count=4,
            exit_code=0,
            result_path="tests/test_flowpilot_core_runtime.py",
            owns_state=("terminal_backward_replay", "segment_targets"),
            owns_side_effects=("terminal_replay_blocker", "terminal_replay_reissue"),
            owned_leaf_cell_ids=(
                "terminal_segment_missing",
                "terminal_segment_duplicate",
                "terminal_segment_unexpected",
                "terminal_segment_corrected_recovery",
                "terminal_replay_reject_repair_rerun_closure",
                "terminal_supplemental_final_ledger_projection",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_terminal_supplemental_repair",
            command=(
                "python simulations/run_flowpilot_terminal_supplemental_repair_checks.py; "
                "python -m unittest -v tests.test_flowpilot_core_runtime terminal supplemental repair and hygiene cases; "
                "python -m unittest -v tests.test_flowpilot_fake_project_rehearsal."
                "FlowPilotFakeProjectRehearsalTests.test_blackbox_terminal_supplemental_repair_uses_public_cli"
            ),
            result_status="passed",
            evidence_tier="executable_flowguard",
            test_count=10,
            exit_code=0,
            result_path=(
                "simulations/flowpilot_terminal_supplemental_repair_results.json; "
                "tests/test_flowpilot_core_runtime.py; tests/test_flowpilot_fake_project_rehearsal.py"
            ),
            owns_state=("terminal_supplemental_repair", "supplemental_repair_contracts"),
            owns_side_effects=(
                "terminal_supplemental_repair_contract_recorded",
                "terminal_supplemental_repair_exhausted",
            ),
            owned_leaf_cell_ids=(
                "terminal_supplemental_contract_missing",
                "terminal_supplemental_contract_corrected_recovery",
                "terminal_supplemental_fake_ai_current_body_recovery",
                "terminal_supplemental_final_ledger_projection",
                "terminal_supplemental_round_cap_exhaustion",
                "terminal_hygiene_review_required",
                "terminal_hygiene_required_gap_blocks",
                "terminal_hygiene_supplemental_contract",
                "terminal_hygiene_final_ledger_projection",
            ),
        ),
        TestSuiteEvidence(
            "acceptance_field_contract_mesh",
            command="python simulations/run_flowpilot_field_contract_checks.py; python simulations/run_flowpilot_field_mesh_checks.py",
            result_status="passed",
            evidence_tier="field_lifecycle_mesh",
            test_count=2,
            exit_code=0,
            result_path="simulations/flowpilot_field_contract_results.json; simulations/flowpilot_field_mesh_results.json",
            owns_state=("field_contract_catalog", "field_mesh"),
            owns_side_effects=("field_contract_result",),
        ),
        TestSuiteEvidence(
            "acceptance_model_test_alignment",
            command="python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json",
            result_status="passed",
            evidence_tier="model_test_alignment",
            test_count=1,
            exit_code=0,
            result_path="simulations/flowpilot_model_test_alignment_results.json",
            owns_state=("model_test_alignment",),
            owns_side_effects=("coverage_accounting",),
        ),
        _tier_child(
            **_with_override(
                {
                    "suite_id": "acceptance_router_quality_gate_children",
                    "command": "python scripts/run_test_tier.py --tier router-quality-gates --background",
                    "not_run_reason": "router-quality-gates background artifacts were not provided",
                    "owns_state": ("quality_gate_child_evidence",),
                    "owns_side_effects": ("gate_validation",),
                },
                tier_overrides.get("acceptance_router_quality_gate_children"),
            )
        ),
        _tier_child(
            **_with_override(
                {
                    "suite_id": "acceptance_router_packet_tier",
                    "command": "python scripts/run_test_tier.py --tier router-packets --background",
                    "not_run_reason": "router-packets background artifacts were not provided",
                    "owns_state": ("packet_tier_child_evidence",),
                    "owns_side_effects": ("packet_runtime_validation",),
                },
                tier_overrides.get("acceptance_router_packet_tier"),
            )
        ),
        _tier_child(
            **_with_override(
                {
                    "suite_id": "acceptance_router_route_tier",
                    "command": "python scripts/run_test_tier.py --tier router-route --background",
                    "not_run_reason": "router-route background artifacts were not provided",
                    "owns_state": ("route_tier_child_evidence",),
                    "owns_side_effects": ("route_mutation_validation",),
                },
                tier_overrides.get("acceptance_router_route_tier"),
            )
        ),
        _tier_child(
            **_with_override(
                {
                    "suite_id": "acceptance_router_terminal_tier",
                    "command": "python scripts/run_test_tier.py --tier router-terminal --background",
                    "not_run_reason": "router-terminal background artifacts were not provided",
                    "owns_state": ("terminal_tier_child_evidence",),
                    "owns_side_effects": ("terminal_replay_validation",),
                },
                tier_overrides.get("acceptance_router_terminal_tier"),
            )
        ),
        _release_child(
            "acceptance_router_release_tiers",
            command="python scripts/run_test_tier.py --tier router-packets/router-route/router-terminal/integration/release/final-confidence",
            result_path=release_result_path,
            release_evidence=release_evidence,
            result_status=release_result_status,
            evidence_current=release_evidence_current,
            progress_only=release_progress_only,
            background=release_background,
            has_exit_artifact=release_has_exit_artifact,
            has_result_artifact=release_has_result_artifact,
            timeout_seconds=release_timeout_seconds,
            duration_seconds=release_duration_seconds,
            stale_reasons=release_stale_reasons,
            not_run_reason="full release tier evidence is visible but not required for routine confidence",
            test_count=45,
            owned_leaf_cell_ids=(
                "formal_exit_terminal_return_missing",
                "formal_exit_startup_intake_blocks",
            ),
        ),
    )
    return TestMeshPlan(
        parent_suite_id=TESTMESH_ID,
        partition_items=_partition_items(),
        child_suites=child_suites,
        target_split_derivation=TestTargetSplitDerivation(
            source_model_id="flowpilot_acceptance_registry_projection",
            source_model_path="simulations/flowpilot_planning_quality_model.py",
            target_suite_ids=CHILD_SUITE_IDS,
            covered_partition_item_ids=tuple(item.item_id for item in _partition_items()),
            state_owner_fields=(
                "acceptance_item_registry",
                "route_nodes.acceptance_item_ids",
                "node_context_package.acceptance_item_projection",
                "pm_disposition.accepted_acceptance_item_ids",
                "terminal_backward_replay.segment_targets",
                "terminal_backward_replay.repair_return",
                "terminal_supplemental_repair.current_round",
                "final_artifact_hygiene_review",
                "final_artifact_hygiene_closure",
                "supplemental_repair_contracts.repair_items",
            ),
            side_effect_owner_fields=(
                "packet_reissue",
                "route_mutation",
                "final_route_wide_ledger",
                "fake_ai_result_submission",
                "terminal_supplemental_repair_contract_recorded",
                "final_artifact_hygiene_blocker_recorded",
                "terminal_supplemental_repair_exhausted",
                "formal_exit_terminal_return_missing",
                "formal_exit_startup_intake_blocks",
            ),
            rationale="Acceptance-registry validation is split by current-contract ownership, payload cell, route mutation, and release evidence boundary.",
            derived_from_flowguard_model=True,
        ),
        required_leaf_cell_ids=PAYLOAD_CELLS,
        required_evidence_tier="external_contract",
        decision_scope="routine",
        release_deferred_allowed=True,
    )


def payload_cell_owners(plan: TestMeshPlan) -> dict[str, tuple[str, ...]]:
    owners: dict[str, list[str]] = {cell_id: [] for cell_id in PAYLOAD_CELLS}
    for suite in plan.child_suites:
        for cell_id in suite.owned_leaf_cell_ids:
            if cell_id in owners:
                owners[cell_id].append(suite.suite_id)
    return {cell_id: tuple(suites) for cell_id, suites in owners.items()}


def formal_exit_release_cell_owners(plan: TestMeshPlan) -> dict[str, tuple[str, ...]]:
    owners: dict[str, list[str]] = {cell_id: [] for cell_id in FORMAL_EXIT_RELEASE_CELLS}
    for suite in plan.child_suites:
        for cell_id in suite.owned_leaf_cell_ids:
            if cell_id in owners:
                owners[cell_id].append(suite.suite_id)
    return {cell_id: tuple(suites) for cell_id, suites in owners.items()}
