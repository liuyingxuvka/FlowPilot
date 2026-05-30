"""Planning-stage system-card delivery sequence for FlowPilot protocol boot cards."""

from __future__ import annotations

from typing import Any


PLANNING_SYSTEM_CARD_SEQUENCE: tuple[dict[str, Any], ...] = (
    {
        "flag": "reviewer_startup_fact_check_card_delivered",
        "label": "reviewer_startup_fact_check_card_delivered",
        "card_id": "reviewer.startup_fact_check",
        "requires_all_flags": ["startup_mechanical_audit_written", "startup_display_status_written"],
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_core_delivered",
        "label": "pm_core_card_delivered",
        "card_id": "pm.core",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_output_contract_catalog_delivered",
        "label": "pm_output_contract_catalog_card_delivered",
        "card_id": "pm.output_contract_catalog",
        "requires_flag": "pm_core_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_role_work_request_card_delivered",
        "label": "pm_role_work_request_card_delivered",
        "card_id": "pm.role_work_request",
        "requires_flag": "pm_output_contract_catalog_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_controller_reset_card_delivered",
        "label": "pm_controller_reset_recovery_card_delivered",
        "card_id": "pm.controller_reset_duty",
        "requires_flag": "controller_boundary_recovery_requested",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_phase_map_delivered",
        "label": "pm_phase_map_card_delivered",
        "card_id": "pm.phase_map",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_startup_intake_card_delivered",
        "label": "pm_startup_intake_phase_card_delivered",
        "card_id": "pm.startup_intake",
        "to_role": "project_manager",
    },
    {
        "flag": "controller_resume_card_delivered",
        "label": "controller_resume_reentry_card_delivered",
        "card_id": "controller.resume_reentry",
        "requires_flag": "resume_state_loaded",
        "to_role": "controller",
    },
    {
        "flag": "pm_role_binding_recovery_freshness_card_delivered",
        "label": "pm_role_binding_recovery_freshness_card_delivered",
        "card_id": "pm.role_binding_recovery_freshness",
        "requires_flag": "resume_roles_restored",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_resume_decision_card_delivered",
        "label": "pm_resume_decision_card_delivered",
        "card_id": "pm.resume_decision",
        "requires_flag": "pm_role_binding_recovery_freshness_card_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_startup_activation_card_delivered",
        "label": "pm_startup_activation_card_delivered",
        "card_id": "pm.startup_activation",
        "requires_flag": "startup_fact_reported",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_scan_card_delivered",
        "label": "pm_material_scan_card_delivered",
        "card_id": "pm.material_scan",
        "requires_flag": "user_intake_delivered_to_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_material_sufficiency_card_delivered",
        "label": "reviewer_material_sufficiency_card_delivered",
        "card_id": "reviewer.material_sufficiency",
        "requires_flag": "material_scan_results_absorbed_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_reviewer_report_event_delivered",
        "label": "pm_reviewer_report_event_card_delivered",
        "card_id": "pm.event.reviewer_report",
        "requires_any_flag": ["material_review_sufficient", "material_review_insufficient"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_absorb_or_research_card_delivered",
        "label": "pm_material_absorb_or_research_card_delivered",
        "card_id": "pm.material_absorb_or_research",
        "requires_flag": "pm_reviewer_report_event_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_research_package_card_delivered",
        "label": "pm_research_package_phase_card_delivered",
        "card_id": "pm.research_package",
        "requires_flag": "pm_research_requested",
        "to_role": "project_manager",
    },
    {
        "flag": "worker_research_report_card_delivered",
        "label": "worker_research_report_duty_card_delivered",
        "card_id": "worker.research_report",
        "requires_flag": "research_capability_decision_recorded",
        "to_role": "worker_a",
    },
    {
        "flag": "reviewer_research_check_card_delivered",
        "label": "reviewer_research_direct_source_check_card_delivered",
        "card_id": "reviewer.research_direct_source_check",
        "requires_flag": "research_result_absorbed_for_review_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_research_absorb_or_mutate_card_delivered",
        "label": "pm_research_absorb_or_mutate_phase_card_delivered",
        "card_id": "pm.research_absorb_or_mutate",
        "requires_flag": "research_review_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_understanding_card_delivered",
        "label": "pm_material_understanding_phase_card_delivered",
        "card_id": "pm.material_understanding",
        "requires_flag": "material_accepted_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_worker_result_card_delivered",
        "label": "reviewer_worker_result_review_card_delivered",
        "card_id": "reviewer.worker_result_review",
        "requires_flag": "current_node_result_absorbed_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_product_architecture_card_delivered",
        "label": "pm_product_architecture_phase_card_delivered",
        "card_id": "pm.product_architecture",
        "requires_flag": "material_understanding_written_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "product_officer_product_architecture_card_delivered",
        "label": "product_officer_product_architecture_modelability_card_delivered",
        "card_id": "product_officer.product_architecture_modelability",
        "requires_flag": "product_architecture_written_by_pm",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "pm_product_behavior_model_decision_card_delivered",
        "label": "pm_product_behavior_model_decision_card_delivered",
        "card_id": "pm.product_behavior_model_decision",
        "requires_flag": "product_behavior_model_submitted",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_product_architecture_card_delivered",
        "label": "reviewer_product_architecture_challenge_card_delivered",
        "card_id": "reviewer.product_architecture_challenge",
        "requires_flag": "pm_product_behavior_model_accepted",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_root_contract_card_delivered",
        "label": "pm_root_contract_phase_card_delivered",
        "card_id": "pm.root_contract",
        "requires_flag": "product_architecture_reviewer_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_root_contract_card_delivered",
        "label": "reviewer_root_contract_challenge_card_delivered",
        "card_id": "reviewer.root_contract_challenge",
        "requires_flag": "root_contract_written_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_dependency_policy_card_delivered",
        "label": "pm_dependency_policy_phase_card_delivered",
        "card_id": "pm.dependency_policy",
        "requires_flag": "root_contract_frozen_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_selection_card_delivered",
        "label": "pm_child_skill_selection_phase_card_delivered",
        "card_id": "pm.child_skill_selection",
        "requires_flag": "capabilities_manifest_written",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_gate_manifest_card_delivered",
        "label": "pm_child_skill_gate_manifest_phase_card_delivered",
        "card_id": "pm.child_skill_gate_manifest",
        "requires_flag": "pm_child_skill_selection_written",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "label": "reviewer_child_skill_gate_manifest_review_card_delivered",
        "card_id": "reviewer.child_skill_gate_manifest_review",
        "requires_flag": "child_skill_gate_manifest_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_prior_path_context_card_delivered",
        "label": "pm_prior_path_context_phase_card_delivered",
        "card_id": "pm.prior_path_context",
        "requires_flag": "capability_evidence_synced",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_route_skeleton_card_delivered",
        "label": "pm_route_skeleton_phase_card_delivered",
        "card_id": "pm.route_skeleton",
        "requires_flag": "pm_prior_path_context_card_delivered",
        "to_role": "project_manager",
    },
)


def planning_system_card_catalog() -> dict[str, object]:
    """Return externally visible planning-card sequence metadata."""

    return {
        "card_count": len(PLANNING_SYSTEM_CARD_SEQUENCE),
        "card_ids": tuple(card["card_id"] for card in PLANNING_SYSTEM_CARD_SEQUENCE),
        "flags": tuple(card["flag"] for card in PLANNING_SYSTEM_CARD_SEQUENCE),
    }


__all__ = (
    "PLANNING_SYSTEM_CARD_SEQUENCE",
    "planning_system_card_catalog",
)
