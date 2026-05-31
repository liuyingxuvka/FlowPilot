"""Phase helper extracted from :mod:`capability_model`."""

from __future__ import annotations

from typing import Iterable

if __package__:
    from . import capability_model as _model
else:
    import capability_model as _model

_REQUIRED_MODEL_NAMES = (
    "FunctionResult",
    "Iterable",
    "MAX_QUALITY_ROUTE_RAISES",
    "State",
    "_base_ready",
    "_reset_execution_quality_gates",
    "_step",
    "_sidecar_role_clear",
)
for _name in _REQUIRED_MODEL_NAMES:
    globals()[_name] = getattr(_model, _name)
del _name

__all__ = ["apply_node_execution_phase"]


def apply_node_execution_phase(self, state: State) -> Iterable[FunctionResult]:
    if _base_ready(state) and not state.pm_capability_work_decision_recorded:
        yield _step(
            state,
            label="pm_capability_work_decision_recorded",
            action="project manager assigns the current capability work package before implementation or child-skill execution",
            pm_capability_work_decision_recorded=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and not state.current_node_high_standard_recheck_written
    ):
        yield _step(
            state,
            label="current_node_high_standard_recheck_written",
            action="project manager rechecks the current capability node against the highest achievable product target, unacceptable-result bar, semantic-fidelity policy, and likely local downgrade risks before writing node acceptance",
            current_node_high_standard_recheck_written=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and state.current_node_high_standard_recheck_written
        and not state.current_node_minimum_sufficient_complexity_review_written
    ):
        yield _step(
            state,
            label="current_node_minimum_sufficient_complexity_review_written",
            action="project manager records why the current capability node packet, checks, handoffs, and evidence are the minimum sufficient structure for the node proof obligations",
            current_node_minimum_sufficient_complexity_review_written=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and not state.node_acceptance_plan_written
    ):
        yield _step(
            state,
            label="node_acceptance_plan_written",
            action="project manager writes the current capability node acceptance plan with root mappings, local criteria, concrete experiments, evidence paths, and approver",
            node_acceptance_plan_written=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and not state.node_acceptance_risk_experiments_mapped
    ):
        if not state.active_child_skill_bindings_written:
            yield _step(
                state,
                label="active_child_skill_bindings_written",
                action="project manager writes current-node active child-skill bindings with source skill paths, node-slice scope, selected standards, and stricter-than-PM precedence before worker dispatch",
                active_child_skill_bindings_written=True,
                active_child_skill_binding_scope_limited=True,
                child_skill_stricter_standard_precedence_bound=True,
            )
            return
        yield _step(
            state,
            label="node_acceptance_risk_experiments_mapped",
            action="project manager maps current capability risk hypotheses to experiments and terminal replay scenarios before implementation starts",
            node_acceptance_risk_experiments_mapped=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and state.node_acceptance_risk_experiments_mapped
        and not state.pm_review_hold_instruction_written
    ):
        yield _step(
            state,
            label="pm_review_hold_instruction_written",
            action="project manager tells the human-like reviewer to wait and not review current capability work until worker output and verification are ready for a PM release order",
            pm_review_hold_instruction_written=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and not state.child_skill_node_gate_manifest_refined
    ):
        yield _step(
            state,
            label="child_skill_node_gate_manifest_refined",
            action="project manager refines the child-skill gate manifest for the current node context before sidecar work or implementation",
            child_skill_node_gate_manifest_refined=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and not state.child_skill_gate_authority_records_written
    ):
        yield _step(
            state,
            label="child_skill_gate_authority_records_written",
            action="write current child-skill gate authority records into the execution frontier before execution evidence is drafted",
            child_skill_gate_authority_records_written=True,
        )
        return

    if (
        _base_ready(state)
        and state.pm_capability_work_decision_recorded
        and state.child_skill_gate_authority_records_written
        and not state.worker_packet_child_skill_use_instruction_written
    ):
        yield _step(
            state,
            label="worker_packet_child_skill_binding_projected",
            action="project active child-skill bindings into the current-node worker packet with direct use instructions and allowed source SKILL.md/reference paths",
            worker_packet_child_skill_use_instruction_written=True,
            active_child_skill_source_paths_allowed=True,
        )
        return

    if _base_ready(state) and not state.child_node_sidecar_scan_done:
        yield _step(
            state,
            label="child_node_sidecar_scan_no_need",
            action="enter the current child node and find no useful bounded sidecar task",
            child_node_sidecar_scan_done=True,
            sidecar_need="none",
        )
        yield _step(
            state,
            label="child_node_sidecar_scan_need_found_no_pool",
            action="enter the current child node and find a bounded sidecar task with no existing idle sidecar role",
            child_node_sidecar_scan_done=True,
            sidecar_need="needed",
            sidecar_role_pool_exists=False,
            sidecar_role_idle_available=False,
        )
        yield _step(
            state,
            label="child_node_sidecar_scan_need_found_existing_idle",
            action="enter the current child node and find a bounded sidecar task plus an existing idle sidecar role",
            child_node_sidecar_scan_done=True,
            sidecar_need="needed",
            sidecar_role_pool_exists=True,
            sidecar_role_idle_available=True,
            sidecar_role_status="idle",
        )
        return

    if (
        _base_ready(state)
        and state.sidecar_need == "needed"
        and not state.sidecar_role_scope_checked
    ):
        yield _step(
            state,
            label="sidecar_scope_checked",
            action="confirm the sidecar task is bounded, non-blocking, and disjoint from node ownership and route advancement",
            sidecar_role_scope_checked=True,
        )
        return

    if (
        _base_ready(state)
        and state.sidecar_need == "needed"
        and state.sidecar_role_scope_checked
        and state.sidecar_role_status in {"none", "idle"}
    ):
        if state.sidecar_role_pool_exists and state.sidecar_role_idle_available:
            yield _step(
                state,
                label="idle_sidecar_role_reused",
                action="reuse an existing idle sidecar role for the child-node sidecar task",
                sidecar_role_status="pending",
                sidecar_role_idle_available=False,
            )
        else:
            yield _step(
                state,
                label="sidecar_role_opened_on_demand",
                action="open a sidecar role only after the current child node has a bounded sidecar task and no suitable idle sidecar role exists",
                sidecar_role_pool_exists=True,
                sidecar_role_status="pending",
            )
        return

    if state.sidecar_role_status == "pending":
        yield _step(
            state,
            label="sidecar_report_returned",
            action="sidecar role binding returns findings, evidence, changed paths if any, risks, and suggestions",
            sidecar_role_status="returned",
        )
        return

    if state.sidecar_role_status == "returned":
        yield _step(
            state,
            label="authorized_integration_review_packet_completed",
            action="authorized integration/review packet verifies the sidecar result while PM keeps node ownership",
            sidecar_need="none",
            sidecar_role_status="idle",
            sidecar_role_idle_available=True,
        )
        return

    if not _base_ready(state) or not _sidecar_role_clear(state):
        yield _step(
            state,
            label="blocked_unready_capability_state",
            action="block because capability state is not ready for implementation and emit a nonterminal resume notice",
            status="blocked",
            controlled_stop_notice_recorded=True,
            pause_snapshot_written=True,
        )
        return

    if not state.quality_package_done:
        yield _step(
            state,
            label="quality_package_passed_no_raise",
            action="run one quality package for feature thinness, worthwhile raises, child-skill mini-route visibility, validation strength, and rough-finish risk; record no scope raise",
            quality_package_done=True,
            quality_candidate_registry_checked=True,
            quality_raise_decision_recorded=True,
            validation_matrix_defined=True,
        )
        yield _step(
            state,
            label="quality_package_small_raise_in_current_node",
            action="record a low-risk high-value improvement inside the current capability node without changing the route",
            quality_package_done=True,
            quality_candidate_registry_checked=True,
            quality_raise_decision_recorded=True,
            validation_matrix_defined=True,
        )
        if (
            state.quality_route_raises < MAX_QUALITY_ROUTE_RAISES
            and not (state.non_ui_implemented or state.ui_implemented)
            and not state.final_verification_done
        ):
            yield _step(
                state,
                label="quality_package_route_raise_needed",
                action="classify a medium or large capability improvement as route mutation, not unbounded immediate expansion",
                capability_route_version=state.capability_route_version + 1,
                capability_route_checked=False,
                capability_route_flowguard_operator_route_scope_approved=False,
                capability_product_function_model_checked=False,
                capability_product_function_model_flowguard_operator_product_scope_approved=False,
                capability_evidence_synced=False,
                execution_frontier_written=False,
                codex_plan_synced=False,
                frontier_version=0,
                plan_version=0,
                capability_user_flow_diagram_refreshed=False,
                capability_user_flow_diagram_emitted=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
                child_skill_manifest_independent_validation_done=False,
                child_skill_manifest_reviewer_reviewed=False,
                child_skill_manifest_flowguard_operator_route_scope_approved=False,
                child_skill_manifest_flowguard_operator_product_scope_approved=False,
                child_skill_manifest_pm_approved_for_route=False,
                child_skill_contracts_loaded=False,
                child_skill_focused_interrogation_done=False,
                child_skill_focused_interrogation_questions=0,
                child_skill_focused_interrogation_scope_id="",
                child_skill_exact_source_verified=False,
                child_skill_substitutes_rejected=False,
                child_skill_original_standards_extracted=False,
                child_skill_standards_promoted_to_node_contract=False,
                child_skill_gate_evidence_obligations_bound=False,
                flowpilot_invocation_policy_mapped=False,
                child_skill_requirements_mapped=False,
                child_skill_evidence_plan_written=False,
                child_skill_subroute_projected=False,
                child_skill_conformance_model_checked=False,
                child_skill_conformance_model_flowguard_operator_route_scope_approved=False,
                strict_gate_obligation_review_model_checked=False,
                flowguard_dependency_checked=False,
                dependency_plan_recorded=False,
                future_installs_deferred=False,
                flowguard_process_design_done=False,
                flowguard_operator_model_adversarial_probe_done=False,
                flowguard_model_report_risk_tiers_done=False,
                flowguard_model_report_pm_review_agenda_done=False,
                flowguard_model_report_toolchain_recommendations_done=False,
                flowguard_model_report_confidence_boundary_done=False,
                meta_route_checked=False,
                meta_route_flowguard_operator_route_scope_approved=False,
                sidecar_role_status="none",
                heartbeat_health_checked=False,
                quality_route_raises=state.quality_route_raises + 1,
                **_reset_execution_quality_gates(),
            )
        return
