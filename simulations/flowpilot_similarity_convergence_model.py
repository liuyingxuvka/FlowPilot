"""FlowGuard similarity-convergence model for FlowPilot maintenance.

This model is a maintenance control layer. It does not change FlowPilot
runtime behavior; it records which modeled branches must be maintained as a
family, which branches are safe only as shared-kernel candidates, and which
similar-looking branches are false friends that must remain separate.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace
from typing import Any, Iterable, Sequence

from flowguard import (
    ArchitectureReductionCandidate,
    ArchitectureReductionPlan,
    ArchitectureReductionTrigger,
    DuplicateBoundaryRisk,
    ExistingModelPreflight,
    ExistingOwnershipSnapshot,
    ModelContextHit,
    ModelSignature,
    ModelSimilarityEvidence,
    ModelSimilarityPlan,
    ObservableArchitectureContract,
    PlanDetail,
    PlanDetailEvidence,
    PlanDetailFailureBranch,
    PlanDetailFreshnessRule,
    PlanDetailSideEffect,
    PlanDetailSource,
    PlanDetailStateSurface,
    PlanDetailStep,
    PlanDetailSurface,
    PlanDetailValidation,
    ProcessArtifact,
    SimilarityHandoff,
    review_architecture_reduction,
    review_existing_model_preflight,
    review_model_similarity_consolidation,
    review_plan_detail,
)


RESULT_TYPE = "flowpilot_similarity_convergence"
RESULTS_PATH = "simulations/flowpilot_similarity_convergence_results.json"

MODEL_COMMAND = (
    "python simulations/run_flowpilot_similarity_convergence_checks.py "
    "--json-out simulations/flowpilot_similarity_convergence_results.json"
)


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(child) for key, child in value.items()}
    return value


def _packet_result_signature(
    variant: str,
    *,
    state_id: str,
    output_event: str,
    code_paths: tuple[str, ...],
    test_paths: tuple[str, ...],
) -> ModelSignature:
    return ModelSignature(
        model_id=f"packet_result_{variant}",
        model_path="simulations/flowpilot_packet_result_family_parity_model.py",
        workflow_family="packet_result_return_reconciliation",
        variant_id=variant,
        function_blocks=(
            "fold_durable_result_envelope",
            "project_partial_member_wait",
            "suppress_stale_result_reminder",
            "reject_wrong_recipient_result",
            "preserve_sealed_body_boundary",
        ),
        inputs=("durable_result_envelope", "router_wait_state", "packet_result_ledger"),
        outputs=(output_event, "missing_role_wait_projection"),
        state_owned=(state_id,),
        state_read=("packet_result_ledger", "active_wait_state"),
        side_effects_owned=("write_router_result_event", "update_packet_result_status"),
        invariants=(
            "durable_result_envelope_folds_before_wait",
            "partial_batch_wait_names_only_missing_roles",
            "sealed_bodies_remain_unopened_by_router",
        ),
        failure_modes=(
            "durable_result_joined_but_router_event_absent",
            "wrong_recipient_result_satisfies_wait",
            "sealed_body_text_leaks_into_controller_context",
        ),
        contracts_in=("packet_result_envelope", "current_router_wait"),
        contracts_out=(output_event,),
        code_paths=code_paths,
        test_paths=test_paths,
        owned_public_behaviors=(
            "durable packet results are folded before stale waits",
            "partial result batches keep sibling member gaps visible",
        ),
        shared_kernel_id="packet_result_return_family",
        adapter_ids=(f"packet_result_{variant}_adapter",),
        maintenance_tags=("analogous_defect_scan", "sibling_parity"),
        evidence_ids=("flowpilot_packet_result_family_parity_results",),
    )


def _ack_signature(
    model_id: str,
    variant: str,
    *,
    output_event: str,
    state_id: str,
    code_paths: tuple[str, ...],
    test_paths: tuple[str, ...],
) -> ModelSignature:
    return ModelSignature(
        model_id=model_id,
        model_path="simulations/flowpilot_card_envelope_model.py",
        workflow_family="ack_return_reconciliation",
        variant_id=variant,
        function_blocks=(
            "verify_ack_identity",
            "preconsume_return_ack",
            "merge_terminal_return_monotonically",
            "project_incomplete_ack_wait",
        ),
        inputs=("ack_payload", "pending_return_record", "completed_return_ledger"),
        outputs=(output_event, "ack_wait_projection"),
        state_owned=(state_id,),
        state_read=("pending_return_record", "completed_return_ledger"),
        side_effects_owned=("write_completed_return", "update_pending_return_status"),
        invariants=(
            "duplicate_ack_does_not_reopen_resolved_return",
            "incomplete_ack_does_not_advance_wait",
        ),
        failure_modes=(
            "duplicate_ack_reopens_resolved_return",
            "incomplete_bundle_ack_advances_wait",
        ),
        contracts_in=("card_ack_contract",),
        contracts_out=(output_event,),
        code_paths=code_paths,
        test_paths=test_paths,
        owned_public_behaviors=("ack returns are monotonic and idempotent",),
        shared_kernel_id="ack_return_settlement",
        adapter_ids=(f"ack_{variant}_adapter",),
        maintenance_tags=("ack_idempotency", "terminal_monotonicity"),
        evidence_ids=(
            "flowpilot_card_envelope_results",
            "flowpilot_terminal_state_monotonicity_results",
        ),
    )


def _route_mutation_signature(
    model_id: str,
    variant: str,
    *,
    state_id: str,
    code_paths: tuple[str, ...],
    test_paths: tuple[str, ...],
) -> ModelSignature:
    return ModelSignature(
        model_id=model_id,
        model_path="simulations/flowpilot_route_mutation_activation_model.py",
        workflow_family="route_mutation_replacement",
        variant_id=variant,
        function_blocks=(
            "record_route_mutation",
            "invalidate_stale_route_evidence",
            "supersede_old_current_node_packet",
            "project_replay_scope",
        ),
        inputs=("route_mutation_request", "current_frontier", "prior_route_evidence"),
        outputs=("mutated_route_draft", "pending_route_mutation", "replay_scope"),
        state_owned=(state_id,),
        state_read=("route_draft", "execution_frontier", "packet_ledger"),
        side_effects_owned=("write_route_draft", "write_execution_frontier"),
        invariants=(
            "old_current_node_packet_is_superseded",
            "stale_evidence_blocks_final_ledger",
            "replacement_declares_replay_scope",
        ),
        failure_modes=(
            "old_packet_survives_replacement",
            "stale_sibling_evidence_used_for_completion",
        ),
        contracts_in=("route_mutation_contract",),
        contracts_out=("route_mutation_activation_record",),
        code_paths=code_paths,
        test_paths=test_paths,
        owned_public_behaviors=("route replacement invalidates stale proof before replay",),
        shared_kernel_id="route_mutation_replacement_family",
        adapter_ids=(f"route_mutation_{variant}_adapter",),
        maintenance_tags=("route_repair", "sibling_replay"),
        evidence_ids=("flowpilot_route_mutation_activation_results",),
    )


def _reconciliation_signature(
    model_id: str,
    variant: str,
    *,
    surface: str,
    output: str,
    state_id: str,
    code_paths: tuple[str, ...],
    test_paths: tuple[str, ...],
) -> ModelSignature:
    return ModelSignature(
        model_id=model_id,
        model_path="simulations/flowpilot_router_reconciliation_branch_pruning_model.py",
        workflow_family="router_reconciliation_result_cases",
        variant_id=variant,
        function_blocks=(
            "classify_reconciliation_input",
            "map_to_result_case_vocabulary",
            "apply_state_writing_effects",
        ),
        inputs=(surface, "router_state"),
        outputs=(output,),
        state_owned=(state_id,),
        state_read=("router_state", "control_blocker_index"),
        side_effects_owned=("write_reconciliation_effect",),
        invariants=(
            "state_writing_branch_requires_replay_evidence",
            "result_case_vocabulary_is_complete",
        ),
        failure_modes=(
            "branch_equivalence_overclaimed_without_replay",
            "progress_only_background_claimed_as_pass",
        ),
        contracts_in=(surface,),
        contracts_out=(output,),
        code_paths=code_paths,
        test_paths=test_paths,
        owned_public_behaviors=("reconciliation branches expose a small result-case vocabulary",),
        shared_kernel_id="router_reconciliation_result_case_vocabulary",
        adapter_ids=(f"reconciliation_{variant}_adapter",),
        maintenance_tags=("branch_pruning", "shared_result_cases"),
        evidence_ids=("flowpilot_router_reconciliation_branch_pruning_results",),
    )


def build_model_signatures() -> tuple[ModelSignature, ...]:
    return (
        _packet_result_signature(
            "material_scan",
            state_id="material_scan_result_wait",
            output_event="worker_scan_results_returned",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_work_packets_material.py",
                "skills/flowpilot/assets/packet_runtime_results.py",
            ),
            test_paths=(
                "tests/router_runtime/packets.py",
                "tests/router_runtime/material_modeling.py",
            ),
        ),
        _packet_result_signature(
            "research",
            state_id="research_result_wait",
            output_event="worker_research_report_returned",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_work_packets_material.py",
                "skills/flowpilot/assets/packet_runtime_results.py",
            ),
            test_paths=("tests/router_runtime/packet_result_family.py",),
        ),
        _packet_result_signature(
            "current_node",
            state_id="current_node_result_wait",
            output_event="worker_current_node_result_returned",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_work_packets_current_node.py",
                "skills/flowpilot/assets/packet_runtime_results.py",
            ),
            test_paths=(
                "tests/router_runtime/packet_result_family.py",
                "tests/router_runtime/packets.py",
            ),
        ),
        _packet_result_signature(
            "pm_role_work",
            state_id="pm_role_work_result_wait",
            output_event="role_work_result_returned",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_work_packets_pm_role.py",
                "skills/flowpilot/assets/packet_runtime_results.py",
            ),
            test_paths=(
                "tests/router_runtime/packet_result_family.py",
                "tests/router_runtime/pm_role_work.py",
            ),
        ),
        _ack_signature(
            "ack_single_card_return",
            "single_card",
            output_event="card_return_acknowledged",
            state_id="single_card_pending_return",
            code_paths=(
                "skills/flowpilot/assets/card_runtime_ack.py",
                "skills/flowpilot/assets/flowpilot_router_card_returns.py",
            ),
            test_paths=(
                "tests/test_flowpilot_card_runtime.py",
                "tests/router_runtime/ack_return.py",
            ),
        ),
        _ack_signature(
            "ack_bundle_card_return",
            "bundle_card",
            output_event="bundle_return_acknowledged",
            state_id="bundle_card_pending_return",
            code_paths=(
                "skills/flowpilot/assets/card_runtime_bundle.py",
                "skills/flowpilot/assets/flowpilot_router_card_returns.py",
            ),
            test_paths=(
                "tests/test_flowpilot_card_runtime.py",
                "tests/router_runtime/ack_return.py",
            ),
        ),
        _ack_signature(
            "ack_system_card_return",
            "system_card",
            output_event="system_card_return_acknowledged",
            state_id="system_card_pending_return",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_system_cards.py",
                "skills/flowpilot/assets/flowpilot_router_card_returns.py",
            ),
            test_paths=(
                "tests/router_runtime/cards.py",
                "tests/router_runtime/ack_return.py",
            ),
        ),
        _route_mutation_signature(
            "route_mutation_supersede",
            "supersede",
            state_id="supersede_replacement_frontier",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_route.py",
                "skills/flowpilot/assets/flowpilot_router_route_frontier.py",
            ),
            test_paths=(
                "tests/router_runtime/route_mutation.py",
                "tests/flowpilot_route_mutation_contracts.py",
            ),
        ),
        _route_mutation_signature(
            "route_mutation_sibling_branch",
            "sibling_branch_replacement",
            state_id="sibling_replacement_frontier",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_route.py",
                "skills/flowpilot/assets/flowpilot_router_route_frontier.py",
            ),
            test_paths=(
                "tests/router_runtime/route_mutation_sibling_replacement.py",
                "tests/test_flowpilot_user_flow_diagram.py",
            ),
        ),
        _reconciliation_signature(
            "router_reconciliation_scheduled_receipt",
            "scheduled_controller_receipt",
            surface="scheduled_controller_receipt",
            output="reconciled_controller_receipt",
            state_id="controller_action_row",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts.py",
                "skills/flowpilot/assets/flowpilot_router_controller_reconciliation.py",
            ),
            test_paths=("tests/router_runtime/controller.py",),
        ),
        _reconciliation_signature(
            "router_reconciliation_role_output_event",
            "role_output_event",
            surface="role_output_event",
            output="reconciled_external_role_event",
            state_id="external_event_ledger",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_role_output_bridge_events.py",
                "skills/flowpilot/assets/role_output_runtime.py",
            ),
            test_paths=(
                "tests/test_flowpilot_role_output_bridge_events.py",
                "tests/router_runtime/dispatch_gate.py",
            ),
        ),
        _reconciliation_signature(
            "router_reconciliation_runtime_resume",
            "runtime_state_resume",
            surface="runtime_state_resume",
            output="resume_next_recipient_projection",
            state_id="resume_projection_state",
            code_paths=(
                "skills/flowpilot/assets/flowpilot_router_resume.py",
                "skills/flowpilot/assets/flowpilot_router_runtime_state.py",
            ),
            test_paths=("tests/router_runtime/resume.py",),
        ),
        ModelSignature(
            model_id="route_display_refresh",
            model_path="simulations/flowpilot_route_display_model.py",
            workflow_family="route_mutation_replacement",
            variant_id="display_projection",
            function_blocks=("project_route_sign", "refresh_current_node_display"),
            inputs=("route_draft", "execution_frontier"),
            outputs=("route_sign_markdown", "user_flow_diagram"),
            state_owned=("route_display_projection",),
            state_read=("route_draft", "execution_frontier"),
            side_effects_owned=("write_route_display_artifacts",),
            invariants=("display_must_match_current_route",),
            failure_modes=("route_display_reuses_stale_sibling_evidence",),
            contracts_in=("current_route_state",),
            contracts_out=("display_only_route_sign",),
            code_paths=(
                "skills/flowpilot/assets/flowpilot_user_flow_diagram.py",
                "skills/flowpilot/assets/flowpilot_user_flow_tree.py",
            ),
            test_paths=("tests/test_flowpilot_user_flow_diagram.py",),
            owned_public_behaviors=("route display is derived evidence, not route mutation authority",),
            maintenance_tags=("false_friend", "display_projection"),
            false_friend_model_ids=("route_mutation_sibling_branch",),
            evidence_ids=("user_flow_diagram_results",),
            known_blindspots=(
                "Display projection may look like route mutation because both mention sibling replacement, but it does not own route state writes.",
            ),
        ),
    )


COMPARISON_PAIRS: tuple[tuple[str, str], ...] = (
    ("packet_result_material_scan", "packet_result_research"),
    ("packet_result_research", "packet_result_current_node"),
    ("packet_result_research", "packet_result_pm_role_work"),
    ("ack_single_card_return", "ack_bundle_card_return"),
    ("ack_single_card_return", "ack_system_card_return"),
    ("route_mutation_supersede", "route_mutation_sibling_branch"),
    ("router_reconciliation_scheduled_receipt", "router_reconciliation_role_output_event"),
    ("router_reconciliation_scheduled_receipt", "router_reconciliation_runtime_resume"),
    ("route_mutation_sibling_branch", "route_display_refresh"),
)


def _relation_evidence(
    signatures: Sequence[ModelSignature],
    pairs: Sequence[tuple[str, str]],
) -> tuple[ModelSimilarityEvidence, ...]:
    probe = review_model_similarity_consolidation(
        ModelSimilarityPlan(
            plan_id="flowpilot_similarity_convergence_probe",
            signatures=tuple(signatures),
            comparison_pairs=tuple(pairs),
            require_current_evidence=False,
            require_maintenance_test_paths=False,
            rationale="Probe relation ids before attaching current evidence rows.",
        )
    )
    evidence: list[ModelSimilarityEvidence] = []
    for relation in probe.relations:
        if relation.required_evidence:
            evidence.append(
                ModelSimilarityEvidence(
                    evidence_id=f"{relation.relation_id}:current_review",
                    relation_id=relation.relation_id,
                    evidence_type="flowguard_similarity_review",
                    result_status="passed",
                    current=True,
                    summary=(
                        "Current FlowPilot maintenance inventory reviewed this "
                        f"{relation.relation_type} relation."
                    ),
                )
            )
    return tuple(evidence)


def build_similarity_plan() -> ModelSimilarityPlan:
    signatures = build_model_signatures()
    return ModelSimilarityPlan(
        plan_id="flowpilot_similarity_convergence",
        signatures=signatures,
        comparison_pairs=COMPARISON_PAIRS,
        evidence=_relation_evidence(signatures, COMPARISON_PAIRS),
        changed_model_ids=(
            "packet_result_research",
            "route_mutation_sibling_branch",
            "router_reconciliation_scheduled_receipt",
        ),
        changed_code_paths=(
            "skills/flowpilot/assets/flowpilot_router_work_packets_material.py",
            "skills/flowpilot/assets/flowpilot_router_route.py",
            "skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts.py",
        ),
        require_current_evidence=True,
        require_maintenance_test_paths=True,
        rationale=(
            "A FlowPilot maintenance pass needs sibling-impact review before "
            "folding similar branches or claiming a defect repair is family-wide."
        ),
    )


def build_similarity_handoff() -> SimilarityHandoff:
    report = review_model_similarity_consolidation(build_similarity_plan())
    return SimilarityHandoff(
        relation_ids=tuple(relation.relation_id for relation in report.relations),
        maintenance_group_ids=tuple(group.group_id for group in report.maintenance_groups),
        change_impact_ids=tuple(impact.impact_id for impact in report.change_impacts),
        impacted_model_ids=tuple(
            sorted({model_id for impact in report.change_impacts for model_id in impact.impacted_model_ids})
        ),
        test_obligation_ids=tuple(item.obligation_id for item in report.test_obligations),
        code_obligation_ids=tuple(item.obligation_id for item in report.code_obligations),
        same_family_relation_ids=tuple(
            relation.relation_id
            for relation in report.relations
            if relation.relation_type == "same_family_variant"
        ),
        evidence_duplicate_relation_ids=tuple(
            relation.relation_id
            for relation in report.relations
            if relation.relation_type == "evidence_duplicate"
        ),
        false_friend_rationales=tuple(
            f"{relation.relation_id}: {relation.rationale}"
            for relation in report.relations
            if relation.relation_type == "false_friend"
        ),
        unresolved_gaps=tuple(
            finding.code for finding in report.findings if finding.severity == "blocker"
        ),
        recommended_next_routes=report.recommended_next_routes,
        evidence_current=report.ok,
        source_report_id=RESULT_TYPE,
    )


def build_plan_detail() -> PlanDetail:
    return PlanDetail(
        plan_id="flowpilot_similarity_convergence_maintenance_plan",
        task_summary="Run a FlowGuard-backed FlowPilot similarity convergence maintenance pass.",
        goal=(
            "Make similar FlowPilot model branches explicit enough that bug "
            "repairs, branch folding, and false-friend separation have visible "
            "sibling-impact evidence."
        ),
        assumptions=(
            "FlowGuard 0.39.0 is importable and exposes model similarity plus plan-detail APIs.",
            "This pass adds maintenance checks and docs without changing runtime protocol behavior.",
            "Existing packet-result parity and branch-pruning checks are current baseline evidence.",
        ),
        sources=(
            PlanDetailSource(
                "handoff_current_maintenance_gate",
                source_kind="repo_doc",
                supports_surface_ids=("existing_model_ownership", "validation_boundary"),
                summary="HANDOFF.md lists current FlowPilot maintenance gates and validation commands.",
            ),
            PlanDetailSource(
                "openspec_existing_specs",
                source_kind="openspec",
                supports_surface_ids=("scope_boundary", "false_friend_boundary"),
                summary="Existing specs cover structure convergence, defect-family gates, branch pruning, and model-test alignment.",
            ),
            PlanDetailSource(
                "flowguard_039_similarity_api",
                source_kind="toolchain",
                supports_surface_ids=("similarity_modeling",),
                summary="FlowGuard 0.39.0 provides ModelSimilarityPlan, SimilarityHandoff, and PlanDetail.",
            ),
            PlanDetailSource(
                "baseline_check_results",
                source_kind="executable_check",
                supports_surface_ids=("current_evidence",),
                summary="Existing packet-result parity, branch-pruning, structure-maintenance, and model-test-alignment checks passed before edits.",
            ),
        ),
        surfaces=(
            PlanDetailSurface(
                "similarity_modeling",
                "modeling",
                "Similar packet, ACK, route mutation, and reconciliation families need explicit relation groups.",
                source_ids=("flowguard_039_similarity_api",),
                evidence_ids=("similarity_convergence_result",),
                recurring=True,
                high_risk=True,
            ),
            PlanDetailSurface(
                "false_friend_boundary",
                "architecture",
                "Route display can resemble route mutation but must not gain route-write authority.",
                source_ids=("openspec_existing_specs",),
                evidence_ids=("similarity_convergence_result",),
                high_risk=True,
            ),
            PlanDetailSurface(
                "current_evidence",
                "validation",
                "Similarity conclusions require current model/test evidence and known-bad rejection.",
                source_ids=("baseline_check_results",),
                evidence_ids=("baseline_existing_checks", "similarity_convergence_result"),
                high_risk=True,
            ),
            PlanDetailSurface(
                "scope_boundary",
                "process",
                "This pass must not silently refactor runtime code or weaken public entrypoints.",
                source_ids=("handoff_current_maintenance_gate", "openspec_existing_specs"),
                evidence_ids=("architecture_reduction_result",),
                high_risk=True,
            ),
            PlanDetailSurface(
                "validation_boundary",
                "release",
                "Install self-check and model-test alignment should recognize the new maintenance gate.",
                source_ids=("handoff_current_maintenance_gate",),
                evidence_ids=("install_check_result", "model_test_alignment_result"),
            ),
        ),
        artifacts=(
            ProcessArtifact(
                "similarity_model",
                "flowguard_model",
                path="simulations/flowpilot_similarity_convergence_model.py",
                owner="FlowGuard similarity convergence gate",
            ),
            ProcessArtifact(
                "similarity_runner",
                "check_runner",
                path="simulations/run_flowpilot_similarity_convergence_checks.py",
                owner="FlowGuard similarity convergence gate",
                upstream_artifact_ids=("similarity_model",),
            ),
            ProcessArtifact(
                "similarity_result",
                "json_result",
                path=RESULTS_PATH,
                owner="FlowGuard similarity convergence gate",
                upstream_artifact_ids=("similarity_runner",),
            ),
            ProcessArtifact(
                "model_test_alignment_runner",
                "check_runner",
                path="simulations/run_flowpilot_model_test_alignment_checks.py",
                owner="FlowGuard model-test alignment",
            ),
            ProcessArtifact(
                "install_check_manifest",
                "install_check",
                path="scripts/install_checks/common.py",
                owner="FlowPilot install self-check",
            ),
            ProcessArtifact(
                "handoff_docs",
                "documentation",
                path="HANDOFF.md",
                owner="FlowPilot handoff",
            ),
            ProcessArtifact(
                "similarity_docs",
                "documentation",
                path="docs/flowpilot_similarity_convergence.md",
                owner="FlowPilot maintenance docs",
            ),
        ),
        state_surfaces=(
            PlanDetailStateSurface(
                "similarity_maintenance_groups",
                owner="ModelSimilarityPlan",
                read_by_step_ids=("model_similarity_review", "architecture_review"),
                written_by_step_ids=("model_similarity_review",),
                description="Groups of models that must be maintained together.",
            ),
            PlanDetailStateSurface(
                "similarity_change_impacts",
                owner="ModelSimilarityPlan",
                read_by_step_ids=("model_similarity_review", "validation"),
                written_by_step_ids=("model_similarity_review",),
                description="Sibling model, code, and test paths impacted by a changed member.",
            ),
            PlanDetailStateSurface(
                "reduction_candidates",
                owner="ArchitectureReductionPlan",
                read_by_step_ids=("architecture_review", "validation"),
                written_by_step_ids=("architecture_review",),
                description="Candidates that may be folded only after route-specific proof.",
            ),
        ),
        side_effects=(
            PlanDetailSideEffect(
                "write_similarity_result_json",
                step_id="validation",
                effect_kind="repo_file_write",
                required_evidence_ids=("similarity_convergence_result",),
                reversible=True,
                description="Writes the similarity convergence JSON report.",
            ),
            PlanDetailSideEffect(
                "update_install_manifest",
                step_id="wire_gate",
                effect_kind="repo_file_write",
                required_evidence_ids=("install_check_result",),
                reversible=True,
                description="Adds the new maintenance gate to install self-check inventories.",
            ),
        ),
        steps=(
            PlanDetailStep(
                "inventory",
                action="Inventory current FlowPilot maintenance models, tests, docs, OpenSpec specs, and installed FlowGuard capabilities.",
                skill_name="flowguard-existing-model-preflight",
                produces_receipts=("inventory_current",),
                reads_artifacts=("handoff_docs",),
            ),
            PlanDetailStep(
                "baseline",
                action="Run current packet-result parity, branch-pruning, structure-maintenance, and model-test-alignment checks.",
                skill_name="flowguard-development-process-flow",
                order_after=("inventory",),
                requires_receipts=("inventory_current",),
                produces_receipts=("baseline_green",),
                produced_evidence_ids=("baseline_existing_checks",),
                validation_required=True,
                continue_evidence_ids=("baseline_existing_checks",),
                rework_step_id="inventory",
            ),
            PlanDetailStep(
                "model_similarity_review",
                action="Build model signatures, relation evidence, maintenance groups, change impacts, and test/code obligations.",
                skill_name="flowguard-plan-detailing-compiler",
                order_after=("baseline",),
                requires_receipts=("baseline_green",),
                produces_receipts=("similarity_handoff_ready",),
                writes_artifacts=("similarity_model",),
                produced_evidence_ids=("similarity_convergence_result",),
            ),
            PlanDetailStep(
                "architecture_review",
                action="Classify fold candidates as keep, manual review, shared-kernel candidate, or future StructureMesh/ModelTestAlignment work.",
                skill_name="flowguard-architecture-reduction",
                order_after=("model_similarity_review",),
                requires_receipts=("similarity_handoff_ready",),
                produces_receipts=("reduction_candidates_classified",),
                produced_evidence_ids=("architecture_reduction_result",),
                reads_artifacts=("similarity_model",),
            ),
            PlanDetailStep(
                "wire_gate",
                action="Wire the new gate into docs, model-test alignment summary, install check inventories, and tests.",
                skill_name="flowguard-model-test-alignment",
                order_after=("architecture_review",),
                requires_receipts=("reduction_candidates_classified",),
                produces_receipts=("gate_wired",),
                writes_artifacts=(
                    "similarity_runner",
                    "model_test_alignment_runner",
                    "install_check_manifest",
                    "handoff_docs",
                    "similarity_docs",
                ),
                invalidates_artifacts=("similarity_result",),
            ),
            PlanDetailStep(
                "validation",
                action="Run focused similarity convergence checks, targeted tests, model-test alignment, install self-check, and smoke checks.",
                skill_name="flowguard-development-process-flow",
                order_after=("wire_gate",),
                requires_receipts=("gate_wired",),
                produces_receipts=("validated_similarity_gate",),
                writes_artifacts=("similarity_result",),
                produced_evidence_ids=(
                    "similarity_convergence_result",
                    "model_test_alignment_result",
                    "install_check_result",
                ),
                validation_required=True,
                continue_evidence_ids=(
                    "similarity_convergence_result",
                    "model_test_alignment_result",
                    "install_check_result",
                ),
                rework_step_id="wire_gate",
                claim_labels=("maintenance_done",),
            ),
        ),
        validations=(
            PlanDetailValidation(
                "similarity_convergence_validation",
                required_artifact_ids=("similarity_model", "similarity_runner", "similarity_result"),
                required_evidence_kinds=("flowguard_model_check", "known_bad_rejection"),
                evidence_ids=("similarity_convergence_result",),
                command=MODEL_COMMAND,
                scope="routine",
            ),
            PlanDetailValidation(
                "alignment_validation",
                required_artifact_ids=("model_test_alignment_runner", "similarity_result"),
                required_evidence_kinds=("model_test_alignment",),
                evidence_ids=("model_test_alignment_result",),
                command="python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json",
                scope="routine",
            ),
            PlanDetailValidation(
                "install_validation",
                required_artifact_ids=("install_check_manifest", "similarity_result"),
                required_evidence_kinds=("install_self_check",),
                evidence_ids=("install_check_result",),
                command="python scripts/check_install.py",
                scope="routine",
            ),
        ),
        evidence=(
            PlanDetailEvidence(
                "baseline_existing_checks",
                evidence_kind="flowguard_model_check",
                status="passed",
                produced_by_step_id="baseline",
                covers_artifacts=("similarity_model",),
                command=(
                    "packet result parity, branch pruning, structure maintenance, "
                    "and model-test alignment baseline checks"
                ),
                description="Existing FlowPilot maintenance gates passed before the new similarity gate was added.",
            ),
            PlanDetailEvidence(
                "similarity_convergence_result",
                evidence_kind="flowguard_model_check",
                status="not_run",
                produced_by_step_id="validation",
                covers_artifacts=("similarity_model", "similarity_runner", "similarity_result"),
                validation_ids=("similarity_convergence_validation",),
                command=MODEL_COMMAND,
                result_path=RESULTS_PATH,
                description="FlowGuard similarity convergence report and known-bad rejections.",
            ),
            PlanDetailEvidence(
                "architecture_reduction_result",
                evidence_kind="flowguard_architecture_reduction_review",
                status="not_run",
                produced_by_step_id="architecture_review",
                covers_artifacts=("similarity_model",),
                description="ArchitectureReductionPlan classification for fold candidates.",
            ),
            PlanDetailEvidence(
                "model_test_alignment_result",
                evidence_kind="flowguard_model_test_alignment",
                status="not_run",
                produced_by_step_id="validation",
                covers_artifacts=("model_test_alignment_runner", "similarity_result"),
                validation_ids=("alignment_validation",),
                command="python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json",
                result_path="simulations/flowpilot_model_test_alignment_results.json",
            ),
            PlanDetailEvidence(
                "install_check_result",
                evidence_kind="install_self_check",
                status="not_run",
                produced_by_step_id="validation",
                covers_artifacts=("install_check_manifest", "similarity_result"),
                validation_ids=("install_validation",),
                command="python scripts/check_install.py",
            ),
        ),
        failure_branches=(
            PlanDetailFailureBranch(
                "similarity_missing_sibling_evidence",
                trigger="A member of a similarity group has no current test path or no current relation evidence.",
                step_id="model_similarity_review",
                rework_step_id="wire_gate",
                expected_resolution="Add sibling evidence or downgrade the claim to a visible scoped gap.",
                evidence_ids=("similarity_convergence_result",),
            ),
            PlanDetailFailureBranch(
                "false_friend_fold_attempt",
                trigger="A display or derived-view model is treated as equivalent to a state-writing route mutation model.",
                step_id="architecture_review",
                rework_step_id="model_similarity_review",
                expected_resolution="Keep the false-friend rationale and route any contraction through StructureMesh or manual review.",
                evidence_ids=("architecture_reduction_result",),
            ),
            PlanDetailFailureBranch(
                "install_manifest_drift",
                trigger="Install self-check or model-test alignment does not recognize the new maintenance gate.",
                step_id="validation",
                rework_step_id="wire_gate",
                expected_resolution="Update install inventories, docs, and alignment summary before claiming the gate is live.",
                evidence_ids=("install_check_result", "model_test_alignment_result"),
            ),
        ),
        freshness_rules=(
            PlanDetailFreshnessRule(
                "similarity_model_invalidates_results",
                upstream_artifact_id="similarity_model",
                invalidates_artifact_ids=("similarity_result",),
                invalidates_evidence_kinds=("flowguard_model_check", "model_test_alignment"),
                description="Changing the similarity model invalidates its JSON report and alignment summary.",
            ),
            PlanDetailFreshnessRule(
                "install_manifest_invalidates_install_check",
                upstream_artifact_id="install_check_manifest",
                invalidates_evidence_kinds=("install_self_check",),
                description="Changing install inventories requires rerunning install self-check.",
            ),
        ),
        final_claim="scoped",
        final_evidence_ids=(
            "similarity_convergence_result",
            "model_test_alignment_result",
            "install_check_result",
        ),
        claim_labels=("maintenance_done",),
    )


def build_existing_model_preflight(handoff: SimilarityHandoff | None = None) -> ExistingModelPreflight:
    handoff = handoff or build_similarity_handoff()
    return ExistingModelPreflight(
        preflight_id="flowpilot_similarity_convergence_existing_model_preflight",
        task_summary=(
            "Ground FlowPilot similarity maintenance in existing packet-result, "
            "ACK, route mutation, branch pruning, model-test alignment, and "
            "StructureMesh models."
        ),
        mode="full",
        existing_modeled_system=True,
        model_search_performed=True,
        search_paths=(
            "simulations",
            "tests",
            "docs",
            "openspec/specs",
            "skills/flowpilot/assets",
        ),
        relevant_models=(
            ModelContextHit(
                model_id="flowpilot_packet_result_family_parity",
                model_path="simulations/flowpilot_packet_result_family_parity_model.py",
                evidence_id="flowpilot_packet_result_family_parity_results",
                evidence_tier="conformance_green",
                evidence_current=True,
                responsibilities=("packet-result sibling parity", "analogous defect scan"),
                function_blocks=("fold durable result envelopes", "project partial waits"),
                state_owned=("packet_result_waits",),
                side_effects_owned=("worker result-return events",),
                parent_model_id="flowpilot_model_test_alignment",
                layered_proof_evidence_id="flowpilot_model_test_alignment_results",
                parent_coverage_status="covered",
                child_disjointness_status="member variants disjoint by packet family",
                child_reattachment_status="attached through model-test alignment runner",
                leaf_boundary_matrix_status="covered by packet-result family parity matrix",
                validation_evidence=("python simulations/run_flowpilot_packet_result_family_parity_checks.py",),
            ),
            ModelContextHit(
                model_id="flowpilot_router_reconciliation_branch_pruning",
                model_path="simulations/flowpilot_router_reconciliation_branch_pruning_model.py",
                evidence_id="flowpilot_router_reconciliation_branch_pruning_results",
                evidence_tier="abstract_green",
                evidence_current=True,
                responsibilities=("reconciliation result-case vocabulary", "branch contraction guard"),
                function_blocks=("classify reconciliation inputs", "map result cases"),
                state_owned=("reconciliation state writes",),
                side_effects_owned=("controller receipt and role-event effects",),
                parent_model_id="flowpilot_structure_maintenance",
                layered_proof_evidence_id="flowpilot_structure_maintenance_results",
                parent_coverage_status="child model covered",
                child_disjointness_status="surface variants are separated by authority",
                child_reattachment_status="attached as branch-pruning child",
                leaf_boundary_matrix_status="accepted and rejected scenario matrix current",
                validation_evidence=("python simulations/run_flowpilot_router_reconciliation_branch_pruning_checks.py",),
            ),
            ModelContextHit(
                model_id="flowpilot_route_mutation_activation",
                model_path="simulations/flowpilot_route_mutation_activation_model.py",
                evidence_id="flowpilot_route_mutation_activation_results",
                evidence_tier="conformance_green",
                evidence_current=True,
                responsibilities=("route replacement", "sibling branch replacement", "stale evidence invalidation"),
                function_blocks=("record route mutation", "supersede packet", "project replay scope"),
                state_owned=("route draft", "execution frontier"),
                side_effects_owned=("route draft writes", "frontier writes"),
                parent_model_id="flowpilot_model_test_alignment",
                layered_proof_evidence_id="flowpilot_model_test_alignment_results",
                parent_coverage_status="covered",
                child_disjointness_status="route mutation variants separated by topology",
                child_reattachment_status="attached through route mutation alignment family",
                leaf_boundary_matrix_status="runtime route mutation child suites current",
                validation_evidence=("python simulations/run_flowpilot_route_mutation_activation_checks.py",),
            ),
            ModelContextHit(
                model_id="flowpilot_structure_maintenance",
                model_path="simulations/flowpilot_structure_maintenance_model.py",
                evidence_id="flowpilot_structure_maintenance_results",
                evidence_tier="conformance_green",
                evidence_current=True,
                responsibilities=("StructureMesh", "TestMesh", "public facade preservation"),
                function_blocks=("router target structure", "model script target structure", "router test split"),
                state_owned=("structure partition records",),
                side_effects_owned=("none_runtime_only_model_review",),
                layered_proof_evidence_id="flowpilot_structure_maintenance_results",
                parent_coverage_status="release green",
                child_disjointness_status="router and model partitions disjoint",
                child_reattachment_status="target structures attached",
                leaf_boundary_matrix_status="hazard matrix current",
                validation_evidence=("python simulations/run_flowpilot_structure_maintenance_checks.py",),
            ),
            ModelContextHit(
                model_id="flowpilot_model_test_alignment",
                model_path="simulations/run_flowpilot_model_test_alignment_checks.py",
                evidence_id="flowpilot_model_test_alignment_results",
                evidence_tier="alignment_green",
                evidence_current=True,
                responsibilities=("model obligation to ordinary test evidence", "source contract audit"),
                function_blocks=("alignment plans", "known bad sanity checks", "full diagnostics"),
                state_owned=("alignment result report",),
                side_effects_owned=("alignment JSON result write",),
                layered_proof_evidence_id="flowpilot_model_test_alignment_results",
                parent_coverage_status="alignment green",
                child_disjointness_status="family plans separate by model id",
                child_reattachment_status="source contracts and diagnostics attached",
                leaf_boundary_matrix_status="known-bad matrix current",
                validation_evidence=("python simulations/run_flowpilot_model_test_alignment_checks.py",),
            ),
        ),
        ownership_snapshot=ExistingOwnershipSnapshot(
            function_block_owners=(
                ("packet result durable fold", "flowpilot_packet_result_family_parity"),
                ("ack return monotonic settlement", "flowpilot_card_envelope_model"),
                ("route mutation replacement", "flowpilot_route_mutation_activation"),
                ("router reconciliation branch pruning", "flowpilot_router_reconciliation_branch_pruning"),
                ("similarity maintenance grouping", "flowpilot_similarity_convergence"),
            ),
            state_owners=(
                ("packet_result_waits", "packet_result_family variants"),
                ("pending_return_records", "ack return runtime"),
                ("route_draft/execution_frontier", "route mutation runtime"),
                ("route_display_projection", "route display derived view"),
            ),
            side_effect_owners=(
                ("worker result-return events", "packet result family runtime"),
                ("completed return writes", "ack return runtime"),
                ("route/frontier writes", "route mutation runtime"),
                ("display artifact writes", "route display runtime"),
            ),
            public_entrypoint_owners=(
                ("run_flowpilot_similarity_convergence_checks.py", "similarity convergence gate"),
                ("run_flowpilot_model_test_alignment_checks.py", "model-test alignment gate"),
                ("flowpilot_router.py", "router public facade"),
            ),
            responsibility_owners=(
                ("sibling-impact review", "similarity convergence gate"),
                ("runtime behavior proof", "focused model/test runners"),
                ("public facade parity", "StructureMesh"),
            ),
        ),
        reuse_decision="extend_existing",
        downstream_routes=(
            "model_mesh",
            "model_test_alignment",
            "architecture_reduction",
            "development_process_flow",
        ),
        rationale=(
            "The existing models already own packet results, ACK returns, route "
            "mutation, branch pruning, StructureMesh, and test alignment. The "
            "new gate extends them with a reusable similarity handoff instead "
            "of creating a parallel runtime owner."
        ),
        duplicate_risks=(
            DuplicateBoundaryRisk(
                item_type="responsibility",
                item_id="packet_result_sibling_review",
                existing_owner_id="flowpilot_packet_result_family_parity",
                proposed_owner_id="flowpilot_similarity_convergence",
                resolution="similarity gate references the existing family parity owner instead of replacing it",
                rationale="Packet-result parity remains the concrete family proof.",
                resolved=True,
            ),
            DuplicateBoundaryRisk(
                item_type="state",
                item_id="route_draft_writes",
                existing_owner_id="flowpilot_route_mutation_activation",
                proposed_owner_id="flowpilot_similarity_convergence",
                resolution="similarity gate records false-friend rationale and owns no route state writes",
                rationale="Route display similarity is derived evidence only.",
                resolved=True,
            ),
        ),
        similarity_review_required=True,
        similarity_handoff=handoff,
    )


def build_architecture_reduction_plan(
    handoff: SimilarityHandoff | None = None,
) -> ArchitectureReductionPlan:
    handoff = handoff or build_similarity_handoff()
    return ArchitectureReductionPlan(
        reduction_id="flowpilot_similarity_convergence_reduction_review",
        observable_contract=ObservableArchitectureContract(
            source_model_id="flowpilot_similarity_convergence",
            source_code_boundary_id="flowpilot_similarity_maintenance_pass",
            public_entrypoints=("simulations/run_flowpilot_similarity_convergence_checks.py",),
            observable_outputs=(
                "similarity maintenance groups",
                "sibling change impacts",
                "test and code obligations",
                "fold candidate dispositions",
                "known-bad rejection results",
            ),
            observable_state=(RESULTS_PATH,),
            observable_side_effects=("write similarity convergence result JSON",),
            validation_boundaries=(
                MODEL_COMMAND,
                "python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json",
                "python scripts/check_install.py",
            ),
            rationale=(
                "The maintenance pass may recommend future branch folding, but "
                "the current observable contract is only the model/check output."
            ),
        ),
        companion_route_triggers=(
            ArchitectureReductionTrigger(
                "existing_model_preflight",
                trigger_reason="Reuse current packet, ACK, route, and branch-pruning owners before adding the similarity gate.",
                complexity_signal="many existing FlowPilot models with overlapping maintenance vocabulary",
                recommended_timing="before adding or changing branch-fold checks",
                required=True,
            ),
            ArchitectureReductionTrigger(
                "model_test_alignment",
                trigger_reason="Similarity groups produce shared and variant test obligations.",
                complexity_signal="bug fixed in one member can drift from sibling members",
                recommended_timing="after similarity report is generated",
                required=True,
            ),
            ArchitectureReductionTrigger(
                "structure_mesh",
                trigger_reason="Any public-entrypoint or state-writing contraction must preserve facades.",
                complexity_signal="router, packet, role-output, and route display facades are current contracts",
                recommended_timing="before production code movement",
                required=False,
            ),
        ),
        candidates=(
            ArchitectureReductionCandidate(
                candidate_id="packet_result_family_shared_kernel_candidate",
                candidate_type="merge_handlers",
                code_node_id="packet_result_return_family",
                source_model_element="maintenance:packet_result variants",
                target_action="manual_review",
                proof_status="risky_keep",
                required_next_route="model_test_alignment",
                rationale=(
                    "Packet-result members share durable-result fold mechanics, "
                    "but member-specific events and sealed-body boundaries stay "
                    "separate until runtime conformance proves a shared handler."
                ),
                affected_state=("packet_result_waits",),
                affected_side_effects=("write_router_result_event",),
                evidence_refs=("flowpilot_packet_result_family_parity_results",),
                similarity_handoff=handoff,
            ),
            ArchitectureReductionCandidate(
                candidate_id="router_reconciliation_result_case_candidate",
                candidate_type="remove_branch",
                code_node_id="router_reconciliation_result_case_vocabulary",
                source_model_element="flowpilot_router_reconciliation_branch_pruning",
                target_action="manual_review",
                proof_status="risky_keep",
                required_next_route="conformance_replay",
                rationale=(
                    "The branch-pruning model exposes a shared result-case "
                    "vocabulary, but state-writing effects still require replay "
                    "before any production branch is collapsed."
                ),
                affected_state=("controller_action_row", "external_event_ledger", "resume_projection_state"),
                affected_side_effects=("write_reconciliation_effect",),
                evidence_refs=("flowpilot_router_reconciliation_branch_pruning_results",),
                similarity_handoff=handoff,
            ),
            ArchitectureReductionCandidate(
                candidate_id="route_display_false_friend_quarantine",
                candidate_type="keep_public_facade",
                code_node_id="route_display_refresh",
                source_model_element="route_display_refresh:false_friend",
                target_action="keep_facade",
                proof_status="safe_by_public_facade",
                required_next_route="model_mesh",
                rationale=(
                    "Route display and route mutation mention sibling replacement, "
                    "but display is derived evidence and must not own route state writes."
                ),
                affected_side_effects=("write_route_display_artifacts",),
                evidence_refs=("user_flow_diagram_results",),
                similarity_handoff=handoff,
            ),
        ),
        rationale=(
            "Use similarity convergence to decide what can be folded later; "
            "this pass keeps behavior unchanged and classifies candidates."
        ),
    )


def _finding_codes(report: Any) -> list[str]:
    return sorted({finding.code for finding in getattr(report, "findings", ())})


def _similarity_known_bad_cases() -> list[dict[str, Any]]:
    base = build_model_signatures()
    cases: list[dict[str, Any]] = []

    missing_test_signatures = tuple(
        replace(signature, test_paths=())
        if signature.model_id == "packet_result_pm_role_work"
        else signature
        for signature in base
        if signature.model_id in {"packet_result_research", "packet_result_pm_role_work"}
    )
    missing_test_plan = ModelSimilarityPlan(
        plan_id="known_bad_missing_similarity_test_path",
        signatures=missing_test_signatures,
        comparison_pairs=(("packet_result_research", "packet_result_pm_role_work"),),
        evidence=_relation_evidence(
            missing_test_signatures,
            (("packet_result_research", "packet_result_pm_role_work"),),
        ),
        require_current_evidence=True,
        require_maintenance_test_paths=True,
    )
    missing_test_report = review_model_similarity_consolidation(missing_test_plan)
    cases.append(
        {
            "name": "missing_maintenance_test_path",
            "ok": (not missing_test_report.ok)
            and "missing_maintenance_test_path" in _finding_codes(missing_test_report),
            "expected_codes": ["missing_maintenance_test_path"],
            "finding_codes": _finding_codes(missing_test_report),
            "report": _jsonable(missing_test_report),
        }
    )

    stale_signatures = tuple(
        replace(signature, evidence_current=False)
        if signature.model_id == "packet_result_research"
        else signature
        for signature in base
        if signature.model_id in {"packet_result_research", "packet_result_current_node"}
    )
    stale_plan = ModelSimilarityPlan(
        plan_id="known_bad_stale_similarity_evidence",
        signatures=stale_signatures,
        comparison_pairs=(("packet_result_research", "packet_result_current_node"),),
        evidence=_relation_evidence(
            stale_signatures,
            (("packet_result_research", "packet_result_current_node"),),
        ),
        require_current_evidence=True,
        require_maintenance_test_paths=True,
    )
    stale_report = review_model_similarity_consolidation(stale_plan)
    cases.append(
        {
            "name": "stale_model_signature_evidence",
            "ok": (not stale_report.ok)
            and "stale_model_signature_evidence" in _finding_codes(stale_report),
            "expected_codes": ["stale_model_signature_evidence"],
            "finding_codes": _finding_codes(stale_report),
            "report": _jsonable(stale_report),
        }
    )

    no_relation_evidence_signatures = tuple(
        signature
        for signature in base
        if signature.model_id in {"ack_single_card_return", "ack_bundle_card_return"}
    )
    no_relation_evidence_plan = ModelSimilarityPlan(
        plan_id="known_bad_missing_current_similarity_evidence",
        signatures=no_relation_evidence_signatures,
        comparison_pairs=(("ack_single_card_return", "ack_bundle_card_return"),),
        evidence=(),
        require_current_evidence=True,
        require_maintenance_test_paths=True,
    )
    no_relation_evidence_report = review_model_similarity_consolidation(
        no_relation_evidence_plan
    )
    cases.append(
        {
            "name": "missing_current_similarity_evidence",
            "ok": (not no_relation_evidence_report.ok)
            and "missing_current_similarity_evidence" in _finding_codes(no_relation_evidence_report),
            "expected_codes": ["missing_current_similarity_evidence"],
            "finding_codes": _finding_codes(no_relation_evidence_report),
            "report": _jsonable(no_relation_evidence_report),
        }
    )

    bad_reduction = replace(
        build_architecture_reduction_plan(),
        candidates=(
            ArchitectureReductionCandidate(
                candidate_id="unsafe_branch_fold_without_replay",
                candidate_type="remove_branch",
                code_node_id="router_reconciliation_result_case_vocabulary",
                source_model_element="flowpilot_router_reconciliation_branch_pruning",
                target_action="collapse",
                proof_status="needs_conformance_replay",
                required_next_route="conformance_replay",
                rationale="Synthetic bad case: a state-writing branch fold lacks replay evidence.",
                affected_state=("controller_action_row",),
                affected_side_effects=("write_reconciliation_effect",),
                similarity_handoff=build_similarity_handoff(),
            ),
        ),
    )
    bad_reduction_report = review_architecture_reduction(bad_reduction)
    cases.append(
        {
            "name": "unsafe_branch_fold_without_replay",
            "ok": (not bad_reduction_report.ok)
            and "conformance_replay_required" in _finding_codes(bad_reduction_report),
            "expected_codes": ["conformance_replay_required"],
            "finding_codes": _finding_codes(bad_reduction_report),
            "report": _jsonable(bad_reduction_report),
        }
    )
    return cases


def build_report() -> dict[str, Any]:
    plan_detail_report = review_plan_detail(build_plan_detail())
    similarity_report = review_model_similarity_consolidation(build_similarity_plan())
    handoff = build_similarity_handoff()
    preflight_report = review_existing_model_preflight(build_existing_model_preflight(handoff))
    reduction_report = review_architecture_reduction(build_architecture_reduction_plan(handoff))
    known_bad_cases = _similarity_known_bad_cases()
    known_bad_ok = all(case["ok"] for case in known_bad_cases)
    plan_detail_ok = plan_detail_report.status in {"pass", "scoped"}
    return {
        "ok": (
            plan_detail_ok
            and similarity_report.ok
            and preflight_report.ok
            and reduction_report.ok
            and known_bad_ok
        ),
        "result_type": RESULT_TYPE,
        "model_command": MODEL_COMMAND,
        "plan_detail_ok": plan_detail_ok,
        "similarity_ok": similarity_report.ok,
        "existing_model_preflight_ok": preflight_report.ok,
        "architecture_reduction_ok": reduction_report.ok,
        "known_bad_ok": known_bad_ok,
        "summary": {
            "maintenance_group_count": len(similarity_report.maintenance_groups),
            "relation_count": len(similarity_report.relations),
            "change_impact_count": len(similarity_report.change_impacts),
            "test_obligation_count": len(similarity_report.test_obligations),
            "code_obligation_count": len(similarity_report.code_obligations),
            "recommended_next_routes": list(similarity_report.recommended_next_routes),
        },
        "plan_detail_review": _jsonable(plan_detail_report),
        "similarity_review": _jsonable(similarity_report),
        "similarity_handoff": _jsonable(handoff),
        "existing_model_preflight": _jsonable(preflight_report),
        "architecture_reduction": _jsonable(reduction_report),
        "known_bad_sanity_checks": known_bad_cases,
    }


__all__ = [
    "MODEL_COMMAND",
    "RESULTS_PATH",
    "RESULT_TYPE",
    "build_architecture_reduction_plan",
    "build_existing_model_preflight",
    "build_model_signatures",
    "build_plan_detail",
    "build_report",
    "build_similarity_handoff",
    "build_similarity_plan",
]
