"""Run FlowGuard checks for the flowpilot capability-routing model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import capability_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "capability_results.json"
GRAPH_STATE_LIMIT = 900_000
CHECK_STATE_LIMIT = 900_000

REQUIRED_LABELS = (
    "classified_backend_task",
    "classified_ui_task",
    "startup_four_questions_asked",
    "startup_dialog_stopped_for_user_answers",
    "startup_display_surface_answered",
    "startup_display_entry_action_done",
    "mode_choice_offered",
    "mode_selected_by_user",
    "explicit_full_auto_mode_selected",
    "startup_background_agents_answered",
    "startup_scheduled_continuation_answered",
    "run_directory_created",
    "current_pointer_written",
    "run_index_updated",
    "new_task_no_prior_import",
    "continue_previous_work_selected",
    "prior_work_import_packet_written",
    "control_state_written_under_run_root",
    "top_level_control_state_absent_or_quarantined",
    "showcase_floor_committed",
    "visible_self_interrogation_completed",
    "contract_frozen",
    "six_agent_crew_policy_written",
    "project_manager_spawned_fresh_for_task",
    "human_like_reviewer_spawned_fresh_for_task",
    "process_flowguard_officer_spawned_fresh_for_task",
    "product_flowguard_officer_spawned_fresh_for_task",
    "worker_a_spawned_fresh_for_task",
    "worker_b_spawned_fresh_for_task",
    "crew_ledger_written",
    "role_identity_protocol_recorded",
    "pm_flowguard_delegation_policy_recorded",
    "officer_owned_async_modeling_policy_recorded",
    "officer_model_report_provenance_policy_recorded",
    "controller_coordination_boundary_recorded",
    "independent_approval_protocol_recorded",
    "crew_memory_packets_written",
    "generated_resource_ledger_initialized",
    "activity_stream_initialized",
    "self_interrogation_pm_ratified",
    "material_sources_scanned",
    "material_source_summaries_written",
    "material_source_quality_classified",
    "local_skill_inventory_written",
    "local_skill_inventory_candidate_classified",
    "material_intake_packet_written",
    "material_reviewer_direct_source_probe_done",
    "material_reviewer_sufficiency_checked",
    "material_reviewer_sufficiency_approved",
    "pm_material_understanding_memo_written",
    "pm_material_complexity_classified",
    "pm_material_discovery_decision_recorded",
    "pm_material_research_decision_not_required",
    "pm_material_research_decision_requires_package",
    "pm_research_package_written",
    "research_tool_capability_decision_recorded",
    "research_worker_report_returned",
    "research_reviewer_direct_source_check_done",
    "research_reviewer_rework_required",
    "research_worker_rework_completed",
    "research_reviewer_recheck_done",
    "research_reviewer_sufficiency_passed",
    "pm_research_result_absorbed_or_route_mutated",
    "material_research_gap_closed",
    "product_function_architecture_pm_synthesized",
    "product_function_high_standard_posture_written",
    "product_function_target_and_failure_bar_written",
    "product_function_semantic_fidelity_policy_written",
    "product_function_user_task_map_written",
    "product_function_capability_map_written",
    "product_function_feature_decisions_written",
    "product_function_display_rationale_written",
    "product_function_missing_feature_review_done",
    "product_function_negative_scope_written",
    "product_function_acceptance_matrix_written",
    "root_acceptance_thresholds_defined",
    "root_acceptance_proof_matrix_written",
    "standard_scenario_pack_selected",
    "product_architecture_officer_adversarial_probe_done",
    "product_function_architecture_product_officer_approved",
    "product_architecture_reviewer_adversarial_probe_done",
    "product_function_architecture_reviewer_challenged",
    "capabilities_manifest_written",
    "pm_child_skill_selection_manifest_written",
    "pm_child_skill_selection_scope_decisions_recorded",
    "child_skill_route_design_discovery_started",
    "child_skill_initial_gate_manifest_extracted",
    "child_skill_gate_approvers_assigned",
    "child_skill_manifest_independent_validation_done",
    "child_skill_manifest_reviewer_reviewed",
    "child_skill_manifest_process_officer_approved",
    "child_skill_manifest_product_officer_approved",
    "child_skill_manifest_pm_approved_for_route",
    "child_skill_focused_interrogation_completed",
    "child_skill_contracts_loaded",
    "child_skill_exact_source_verified",
    "child_skill_substitutes_rejected",
    "flowpilot_invocation_policy_mapped",
    "child_skill_requirements_mapped",
    "child_skill_evidence_plan_written",
    "child_skill_subroute_projected",
    "current_node_high_standard_recheck_written",
    "node_acceptance_plan_written",
    "node_acceptance_risk_experiments_mapped",
    "child_skill_conformance_model_checked",
    "strict_gate_obligation_review_model_checked",
    "flowguard_dependency_checked",
    "dependency_plan_recorded",
    "host_continuation_capability_supported",
    "host_continuation_capability_unsupported_manual_resume",
    "heartbeat_schedule_created",
    "pm_initial_capability_decision_recorded",
    "flowguard_process_designed",
    "flowguard_officer_model_adversarial_probe_done",
    "meta_route_checked",
    "capability_route_checked",
    "parent_backward_structural_trigger_rule_recorded",
    "parent_backward_review_targets_enumerated",
    "capability_product_function_model_checked",
    "capability_evidence_synced",
    "execution_frontier_written",
    "codex_plan_synced",
    "capability_user_flow_diagram_refreshed",
    "capability_user_flow_diagram_emitted",
    "live_subagent_start_authorized",
    "fresh_six_live_subagents_started",
    "startup_preflight_reviewer_fact_report_blocked",
    "pm_returns_startup_blockers_to_worker",
    "startup_worker_remediation_completed",
    "startup_preflight_reviewer_fact_report_clean",
    "startup_pm_independent_gate_audit_done",
    "pm_start_gate_opened_from_fact_report",
    "heartbeat_loaded_state",
    "heartbeat_loaded_execution_frontier",
    "heartbeat_loaded_packet_ledger",
    "heartbeat_loaded_crew_memory",
    "heartbeat_restored_six_agent_crew",
    "heartbeat_rehydrated_six_agent_crew",
    "crew_rehydration_report_written",
    "heartbeat_asked_project_manager",
    "heartbeat_pm_controller_reminder_checked",
    "heartbeat_reviewer_dispatch_policy_checked",
    "pm_resume_completion_runway_recorded",
    "pm_runway_synced_to_visible_plan",
    "continuation_resume_ready_checked",
    "pm_capability_work_decision_recorded",
    "child_skill_node_gate_manifest_refined",
    "child_skill_gate_authority_records_written",
    "child_node_sidecar_scan_no_need",
    "child_node_sidecar_scan_need_found_no_pool",
    "child_node_sidecar_scan_need_found_existing_idle",
    "sidecar_scope_checked",
    "idle_subagent_reused",
    "subagent_spawned_on_demand",
    "sidecar_report_returned",
    "authorized_integration_review_packet_completed",
    "pm_review_hold_instruction_written",
    "quality_package_passed_no_raise",
    "quality_package_small_raise_in_current_node",
    "quality_package_route_raise_needed",
    "non_ui_implemented",
    "ui_autonomous_pipeline_selected",
    "ui_inspected",
    "ui_concept_done",
    "ui_concept_target_ready",
    "ui_concept_target_visible",
    "ui_concept_personal_visual_review_done",
    "ui_concept_design_recommendations_recorded",
    "ui_concept_aesthetic_review_passed",
    "ui_concept_aesthetic_review_failed",
    "ui_frontend_design_plan_done",
    "visual_asset_not_required",
    "visual_asset_required",
    "visual_asset_style_review_done",
    "visual_asset_personal_visual_review_done",
    "visual_asset_design_recommendations_recorded",
    "visual_asset_aesthetic_review_passed",
    "visual_asset_aesthetic_review_failed",
    "ui_implemented",
    "ui_screenshot_qa_done",
    "ui_geometry_qa_done",
    "ui_reviewer_personal_walkthrough_done",
    "ui_interaction_reachability_checked",
    "ui_layout_overlap_density_checked",
    "ui_reviewer_design_recommendations_recorded",
    "ui_implementation_aesthetic_review_passed",
    "ui_implementation_aesthetic_review_failed",
    "ui_divergence_review_done",
    "ui_visual_iteration_needed",
    "ui_visual_iteration_loop_closed",
    "child_skill_execution_evidence_audited",
    "child_skill_evidence_matches_outputs",
    "child_skill_domain_quality_checked",
    "child_skill_iteration_loop_closed",
    "skill_improvement_observation_check_no_issue",
    "skill_improvement_observation_logged",
    "current_child_skill_gate_independent_validation_done",
    "child_skill_current_gates_role_approved",
    "role_memory_packets_refreshed_after_capability_work",
    "final_verification_done",
    "anti_rough_finish_passed",
    "anti_rough_finish_found_rework",
    "worker_output_ready_for_review",
    "pm_review_release_order_written",
    "pm_released_reviewer_for_current_gate",
    "implementation_human_review_context_loaded",
    "implementation_human_neutral_observation_written",
    "implementation_human_manual_experiments_run",
    "implementation_reviewer_independent_probe_done",
    "implementation_human_inspection_passed",
    "capability_backward_context_loaded",
    "capability_child_evidence_replayed",
    "capability_backward_neutral_observation_written",
    "capability_structure_decision_recorded",
    "capability_backward_reviewer_independent_probe_done",
    "capability_backward_review_found_existing_child_gap",
    "capability_backward_review_found_missing_sibling",
    "capability_backward_review_found_subtree_mismatch",
    "capability_backward_issue_grilled",
    "pm_repair_decision_interrogated",
    "capability_route_updated_to_rework_child_node",
    "capability_route_updated_to_add_sibling_child_node",
    "capability_route_updated_to_rebuild_child_subtree",
    "capability_backward_review_passed",
    "capability_backward_pm_segment_decision_recorded",
    "child_skill_completion_verified",
    "completion_visible_user_flow_diagram_emitted",
    "final_feature_matrix_reviewed",
    "final_acceptance_matrix_reviewed",
    "final_standard_scenario_pack_replayed",
    "final_quality_candidate_reviewed",
    "final_product_model_officer_adversarial_probe_done",
    "final_product_function_model_replayed",
    "final_human_review_context_loaded",
    "final_human_neutral_observation_written",
    "final_human_manual_experiments_run",
    "final_human_reviewer_independent_probe_done",
    "final_human_inspection_passed",
    "completion_self_interrogation_completed",
    "high_value_capability_gap_found",
    "no_obvious_high_value_work_remaining",
    "final_route_wide_gate_ledger_current_route_scanned",
    "final_route_wide_gate_ledger_effective_nodes_resolved",
    "final_route_wide_gate_ledger_child_skill_gates_collected",
    "final_route_wide_gate_ledger_human_review_gates_collected",
    "final_route_wide_gate_ledger_parent_backward_replays_collected",
    "final_route_wide_gate_ledger_product_process_gates_collected",
    "final_route_wide_gate_ledger_resource_lineage_resolved",
    "final_route_wide_gate_ledger_stale_evidence_checked",
    "final_route_wide_gate_ledger_superseded_nodes_explained",
    "final_route_wide_gate_ledger_unresolved_count_zero",
    "final_residual_risk_triage_done",
    "final_residual_risk_unresolved_count_zero",
    "final_route_wide_gate_ledger_pm_built",
    "terminal_human_backward_review_map_built",
    "terminal_human_backward_replay_started_from_delivered_product",
    "terminal_human_backward_root_acceptance_reviewed",
    "terminal_human_backward_parent_nodes_reviewed",
    "terminal_human_backward_leaf_nodes_reviewed",
    "terminal_human_backward_pm_segment_decisions_recorded",
    "terminal_human_backward_repair_restart_policy_recorded",
    "final_route_wide_gate_ledger_reviewer_backward_checked",
    "final_ledger_pm_independent_audit_done",
    "final_route_wide_gate_ledger_pm_completion_approved",
    "terminal_closure_suite_run",
    "terminal_state_and_evidence_refreshed",
    "lifecycle_reconciliation_completed",
    "terminal_lifecycle_frontier_written",
    "crew_memory_archived_at_terminal",
    "crew_archived_at_terminal",
    "flowpilot_skill_improvement_report_written",
    "pm_completion_decision_recorded",
    "completed",
)


def _state_id(state: model.State) -> str:
    return (
        f"{state.status}|kind={state.task_kind}|enabled={state.flowpilot_enabled}|"
        f"mode_offer={state.mode_choice_offered}|showcase={state.showcase_floor_committed}|"
        f"run={state.run_directory_created},{state.current_pointer_written},"
        f"{state.run_index_updated},{state.prior_work_mode},"
        f"{state.prior_work_import_packet_written},"
        f"{state.control_state_written_under_run_root},"
        f"{state.top_level_control_state_absent_or_quarantined},"
        f"{state.old_control_state_reused_as_current}|"
        f"self={state.self_interrogation_done},{state.visible_self_interrogation_done},"
        f"{state.self_interrogation_questions},{state.self_interrogation_layer_count},"
        f"{state.self_interrogation_questions_per_layer},{state.self_interrogation_layers},"
        f"{state.self_interrogation_pm_ratified}|"
        f"quality_seed={state.quality_candidate_pool_seeded},"
        f"{state.validation_strategy_seeded}|"
        f"material={state.material_sources_scanned},"
        f"{state.material_source_summaries_written},"
        f"{state.material_source_quality_classified},"
        f"{state.material_intake_packet_written},"
        f"{state.material_reviewer_direct_source_probe_done},"
        f"{state.material_reviewer_sufficiency_checked},"
        f"{state.material_reviewer_sufficiency_approved},"
        f"{state.pm_material_understanding_memo_written},"
        f"{state.pm_material_complexity_classified},"
        f"{state.pm_material_discovery_decision_recorded},"
        f"{state.pm_material_research_decision_recorded},"
        f"{state.material_research_need},"
        f"{state.pm_research_package_written},"
        f"{state.research_tool_capability_decision_recorded},"
        f"{state.research_worker_report_returned},"
        f"{state.research_reviewer_direct_source_check_done},"
        f"{state.research_reviewer_rework_required},"
        f"{state.research_worker_rework_completed},"
        f"{state.research_reviewer_recheck_done},"
        f"{state.research_reviewer_sufficiency_passed},"
        f"{state.pm_research_result_absorbed_or_route_mutated}|"
        f"product_function_architecture="
        f"{state.product_function_architecture_pm_synthesized},"
        f"{state.product_function_high_standard_posture_written},"
        f"{state.product_function_target_and_failure_bar_written},"
        f"{state.product_function_semantic_fidelity_policy_written},"
        f"{state.product_function_user_task_map_written},"
        f"{state.product_function_capability_map_written},"
        f"{state.product_function_feature_decisions_written},"
        f"{state.product_function_display_rationale_written},"
        f"{state.product_function_gap_review_done},"
        f"{state.product_function_negative_scope_written},"
        f"{state.product_function_acceptance_matrix_written},"
        f"{state.root_acceptance_thresholds_defined},"
        f"{state.root_acceptance_proof_matrix_written},"
        f"{state.standard_scenario_pack_selected},"
        f"{state.product_architecture_officer_adversarial_probe_done},"
        f"{state.product_function_architecture_product_officer_approved},"
        f"{state.product_architecture_reviewer_adversarial_probe_done},"
        f"{state.product_function_architecture_reviewer_challenged}|"
        f"crew={state.crew_policy_written},{state.crew_count},"
        f"{state.project_manager_ready},{state.reviewer_ready},"
        f"{state.process_flowguard_officer_ready},"
        f"{state.product_flowguard_officer_ready},"
        f"{state.worker_a_ready},{state.worker_b_ready},"
        f"{state.crew_ledger_written},"
        f"{state.crew_memory_policy_written},"
        f"{state.crew_memory_packets_written},"
        f"{state.pm_initial_capability_decision_recorded},"
        f"{state.crew_memory_archived},{state.crew_archived}|"
        f"officer_async={state.pm_flowguard_delegation_policy_recorded},"
        f"{state.officer_owned_async_modeling_policy_recorded},"
        f"{state.officer_model_report_provenance_policy_recorded},"
        f"{state.controller_coordination_boundary_recorded},"
        f"{state.independent_approval_protocol_recorded}|"
        f"contract={state.contract_frozen}|"
        f"child_manifest={state.child_skill_route_design_discovery_started},"
        f"{state.child_skill_initial_gate_manifest_extracted},"
        f"{state.child_skill_gate_approvers_assigned},"
        f"{state.child_skill_manifest_independent_validation_done},"
        f"{state.child_skill_manifest_reviewer_reviewed},"
        f"{state.child_skill_manifest_process_officer_approved},"
        f"{state.child_skill_manifest_product_officer_approved},"
        f"{state.child_skill_manifest_pm_approved_for_route},"
        f"{state.child_skill_node_gate_manifest_refined},"
        f"{state.child_skill_gate_authority_records_written},"
        f"{state.child_skill_current_gates_role_approved}|"
        f"child_skill_focused={state.child_skill_focused_interrogation_done},"
        f"{state.child_skill_focused_interrogation_questions},"
        f"{state.child_skill_focused_interrogation_scope_id}|"
        f"child_skill={state.child_skill_contracts_loaded},"
        f"{state.child_skill_exact_source_verified},"
        f"{state.child_skill_substitutes_rejected},"
        f"{state.flowpilot_invocation_policy_mapped},"
        f"{state.child_skill_requirements_mapped},"
        f"{state.child_skill_evidence_plan_written},"
        f"{state.child_skill_subroute_projected},"
        f"node_acceptance={state.current_node_high_standard_recheck_written},"
        f"{state.node_acceptance_plan_written},"
        f"{state.node_acceptance_risk_experiments_mapped},"
        f"{state.child_skill_conformance_model_checked},"
        f"{state.child_skill_conformance_model_process_officer_approved},"
        f"strict_gate={state.strict_gate_obligation_review_model_checked},"
        f"{state.child_skill_execution_evidence_audited},"
        f"{state.child_skill_evidence_matches_outputs},"
        f"{state.child_skill_domain_quality_checked},"
        f"{state.child_skill_iteration_loop_closed},"
        f"{state.current_child_skill_gate_independent_validation_done},"
        f"{state.child_skill_completion_verified}|"
        f"fg={state.flowguard_dependency_checked}|"
        f"continuation={state.continuation_probe_done},"
        f"{state.host_continuation_supported},"
        f"{state.manual_resume_mode_recorded},"
        f"{state.continuation_host_kind_recorded},"
        f"{state.continuation_evidence_written}|"
        f"heartbeat={state.heartbeat_schedule_created},"
        f"{state.stable_heartbeat_launcher_recorded},"
        f"{state.heartbeat_loaded_state},"
        f"{state.heartbeat_loaded_frontier},"
        f"{state.heartbeat_loaded_crew_memory},"
        f"{state.heartbeat_restored_crew},"
        f"{state.heartbeat_rehydrated_crew},"
        f"{state.crew_rehydration_report_written},"
        f"{state.replacement_roles_seeded_from_memory},"
        f"{state.heartbeat_pm_decision_requested},"
        f"{state.pm_resume_decision_recorded},"
        f"{state.pm_completion_runway_recorded},"
        f"{state.pm_runway_hard_stops_recorded},"
        f"{state.pm_runway_checkpoint_cadence_recorded},"
        f"{state.pm_runway_synced_to_plan},"
        f"{state.plan_sync_method_recorded},"
        f"{state.visible_plan_has_runway_depth},"
        f"continuation_ready={state.heartbeat_health_checked},"
        f"{state.pm_capability_work_decision_recorded}|"
        f"continuation_lifecycle={state.heartbeat_schedule_created},"
        f"{state.route_heartbeat_interval_minutes},"
        f"{state.manual_resume_mode_recorded},"
        f"{state.lifecycle_reconciliation_done},"
        f"{state.terminal_lifecycle_frontier_written}|"
        f"fg_design={state.flowguard_process_design_done},"
        f"{state.flowguard_officer_model_adversarial_probe_done}|"
        f"deps={state.dependency_plan_recorded},{state.future_installs_deferred}|"
        f"meta={state.meta_route_checked},{state.meta_route_process_officer_approved}|"
        f"cap={state.capability_route_checked},"
        f"{state.capability_route_process_officer_approved},"
        f"{state.capability_product_function_model_checked},"
        f"{state.capability_product_function_model_product_officer_approved}|"
        f"parent_backward_targets={state.parent_backward_structural_trigger_rule_recorded},"
        f"{state.parent_backward_review_targets_enumerated},"
        f"{state.parent_backward_review_targets_route_version},"
        f"{state.parent_backward_targets_count}|"
        f"evidence={state.capability_evidence_synced}|"
        f"frontier={state.execution_frontier_written}:{state.frontier_version}|"
        f"plan={state.codex_plan_synced}:{state.plan_version}|"
        f"resource_ledgers={state.generated_resource_ledger_initialized},"
        f"{state.activity_stream_initialized},"
        f"{state.activity_stream_latest_event_written}|"
        f"user_flow={state.capability_user_flow_diagram_emitted}|"
        f"live_subagents={state.live_subagent_decision_recorded},"
        f"{state.live_subagents_started},"
        f"{state.live_subagents_current_task_fresh},"
        f"{state.historical_agent_ids_compared},"
        f"{state.reused_historical_agent_ids},"
        f"{state.single_agent_role_continuity_authorized}|"
        f"startup_review_run={state.startup_reviewer_checked_run_isolation},"
        f"{state.startup_reviewer_checked_prior_work_boundary},"
        f"{state.startup_pm_independent_gate_audit_done}|"
        f"work_beyond_startup={state.work_beyond_startup_allowed}|"
        f"sidecar={state.child_node_sidecar_scan_done},"
        f"{state.sidecar_need},{state.subagent_pool_exists},"
        f"{state.subagent_idle_available},{state.subagent_scope_checked}|"
        f"sub={state.subagent_status}|"
        f"pm_review={state.pm_review_hold_instruction_written},"
        f"{state.worker_output_ready_for_review},"
        f"{state.pm_review_release_order_written},"
        f"{state.pm_released_reviewer_for_current_gate}|"
        f"quality={state.quality_package_done},"
        f"{state.quality_candidate_registry_checked},"
        f"{state.quality_raise_decision_recorded},"
        f"{state.validation_matrix_defined},"
        f"{state.anti_rough_finish_done},"
        f"role_memory_refresh={state.role_memory_refreshed_after_work},"
        f"impl_human={state.implementation_human_review_context_loaded},"
        f"{state.implementation_human_neutral_observation_written},"
        f"{state.implementation_human_manual_experiments_run},"
        f"{state.implementation_reviewer_independent_probe_done},"
        f"{state.implementation_human_inspection_passed},"
        f"{state.implementation_human_review_reviewer_approved},"
        f"cap_backward={state.capability_backward_context_loaded},"
        f"{state.capability_child_evidence_replayed},"
        f"{state.capability_backward_neutral_observation_written},"
        f"{state.capability_structure_decision_recorded},"
        f"{state.capability_backward_reviewer_independent_probe_done},"
        f"{state.capability_backward_human_review_passed},"
        f"{state.capability_backward_review_reviewer_approved},"
        f"pm_segment={state.capability_backward_pm_segment_decision_recorded},"
        f"{state.capability_backward_pm_segment_decisions_recorded},"
        f"cap_issue={state.capability_backward_issue_grilled},"
        f"{state.capability_backward_issue_strategy},"
        f"pm_repair_grills={state.pm_repair_decision_interrogations},"
        f"skill_improvement={state.current_node_skill_improvement_check_done},"
        f"{state.flowpilot_skill_improvement_report_written},"
        f"structural_repairs={state.capability_structural_route_repairs},"
        f"siblings={state.capability_new_sibling_nodes},"
        f"subtree_rebuilds={state.capability_subtree_rebuilds},"
        f"raises={state.quality_route_raises},"
        f"reworks={state.quality_reworks}|"
        f"ui={state.ui_autonomous_pipeline_selected},{state.ui_inspected},"
        f"{state.ui_concept_done},{state.ui_concept_target_ready},"
        f"{state.ui_concept_target_visible},"
        f"{state.ui_concept_personal_visual_review_done},"
        f"{state.ui_concept_design_recommendations_recorded},"
        f"{state.ui_concept_aesthetic_review_done},"
        f"{state.ui_concept_aesthetic_reasons_recorded},"
        f"{state.ui_frontend_design_plan_done},"
        f"asset={state.visual_asset_scope},{state.visual_asset_style_review_done},"
        f"{state.visual_asset_personal_visual_review_done},"
        f"{state.visual_asset_design_recommendations_recorded},"
        f"{state.visual_asset_aesthetic_review_done},"
        f"{state.visual_asset_aesthetic_reasons_recorded},"
        f"{state.ui_implemented},{state.ui_screenshot_qa_done},"
        f"{state.ui_geometry_qa_done},"
        f"{state.ui_reviewer_personal_walkthrough_done},"
        f"{state.ui_interaction_reachability_checked},"
        f"{state.ui_layout_overlap_density_checked},"
        f"{state.ui_reviewer_design_recommendations_recorded},"
        f"{state.ui_implementation_aesthetic_review_done},"
        f"{state.ui_implementation_aesthetic_reasons_recorded},"
        f"{state.ui_divergence_review_done},"
        f"{state.ui_visual_iteration_loop_closed},{state.ui_visual_iterations}|"
        f"nonui={state.non_ui_implemented}|final={state.final_verification_done}|"
        f"complete_user_flow={state.completion_visible_user_flow_diagram_emitted}|"
        f"final_reviews={state.final_feature_matrix_review_done},"
        f"{state.final_acceptance_matrix_review_done},"
        f"{state.final_standard_scenario_pack_replayed},"
        f"{state.final_quality_candidate_review_done},"
        f"{state.final_product_model_officer_adversarial_probe_done},"
        f"{state.final_product_function_model_replayed},"
        f"{state.final_product_function_model_product_officer_approved},"
        f"{state.final_human_review_context_loaded},"
        f"{state.final_human_neutral_observation_written},"
        f"{state.final_human_manual_experiments_run},"
        f"{state.final_human_reviewer_independent_probe_done},"
        f"{state.final_human_inspection_passed},"
        f"{state.final_human_review_reviewer_approved},"
        f"{state.pm_completion_decision_recorded}|"
        f"final_ledger={state.final_route_wide_gate_ledger_current_route_scanned},"
        f"{state.final_route_wide_gate_ledger_effective_nodes_resolved},"
        f"{state.final_route_wide_gate_ledger_child_skill_gates_collected},"
        f"{state.final_route_wide_gate_ledger_human_review_gates_collected},"
        f"{state.final_route_wide_gate_ledger_parent_backward_replays_collected},"
        f"{state.final_route_wide_gate_ledger_product_process_gates_collected},"
        f"{state.final_route_wide_gate_ledger_resource_lineage_resolved},"
        f"{state.final_route_wide_gate_ledger_stale_evidence_checked},"
        f"{state.final_route_wide_gate_ledger_superseded_nodes_explained},"
        f"{state.final_route_wide_gate_ledger_unresolved_count_zero},"
        f"{state.final_residual_risk_triage_done},"
        f"{state.final_residual_risk_unresolved_count_zero},"
        f"{state.final_route_wide_gate_ledger_pm_built},"
        f"{state.terminal_human_backward_review_map_built},"
        f"{state.terminal_human_backward_replay_started_from_delivered_product},"
        f"{state.terminal_human_backward_root_acceptance_reviewed},"
        f"{state.terminal_human_backward_parent_nodes_reviewed},"
        f"{state.terminal_human_backward_leaf_nodes_reviewed},"
        f"{state.terminal_human_backward_pm_segment_decisions_recorded},"
        f"{state.terminal_human_backward_repair_restart_policy_recorded},"
        f"{state.final_route_wide_gate_ledger_reviewer_backward_checked},"
        f"{state.final_ledger_pm_independent_audit_done},"
        f"{state.final_route_wide_gate_ledger_pm_completion_approved}|"
        f"terminal_closure={state.terminal_closure_suite_run},"
        f"{state.terminal_state_and_evidence_refreshed}|"
        f"stop_notice={state.controlled_stop_notice_recorded},"
        f"{state.terminal_completion_notice_recorded}|"
        f"complete_self={state.completion_self_interrogation_done},"
        f"{state.completion_self_interrogation_questions},"
        f"{state.completion_self_interrogation_layer_count},"
        f"{state.completion_self_interrogation_questions_per_layer},"
        f"{state.completion_self_interrogation_layers}|"
        f"high_value={state.high_value_work_review}|standards={state.standard_expansions}"
    )


def _build_reachable_graph(max_states: int = 5000) -> dict:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial: 0}
    states = [initial]
    edges: list[list[tuple[str, int]]] = [[]]
    labels: set[str] = set()
    edge_count = 0
    invariant_failures: list[dict] = []
    terminal_counts = {"complete": 0, "blocked": 0}

    while queue:
        state = queue.popleft()
        state_index = seen[state]
        if state.status in terminal_counts:
            terminal_counts[state.status] += 1
        for invariant in model.INVARIANTS:
            result = invariant.predicate(state, None)
            if not result.ok:
                invariant_failures.append(
                    {
                        "invariant": invariant.name,
                        "state": _state_id(state),
                        "reason": result.message,
                    }
                )

        for label, next_state in model.next_states(state):
            labels.add(label)
            edge_count += 1
            if next_state not in seen:
                seen[next_state] = len(states)
                states.append(next_state)
                edges.append([])
                if len(states) > max_states:
                    raise RuntimeError(f"state graph exceeded {max_states} states")
                queue.append(next_state)
            edges[state_index].append((label, seen[next_state]))

    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": edge_count,
        "invariant_failures": invariant_failures,
        "terminal_counts": terminal_counts,
    }


def _graph_report_from_graph(graph: dict) -> dict:
    labels = graph["labels"]
    invariant_failures = graph["invariant_failures"]

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not invariant_failures and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
        "terminal_counts": graph["terminal_counts"],
    }


def explore_state_graph(max_states: int = 5000) -> dict:
    graph = _build_reachable_graph(max_states=max_states)
    return _graph_report_from_graph(graph)


def _reverse_reachable(edges: list[list[tuple[str, int]]], starts: set[int]) -> set[int]:
    reverse: list[list[int]] = [[] for _ in edges]
    for source, outgoing in enumerate(edges):
        for _label, target in outgoing:
            reverse[target].append(source)
    reachable = set(starts)
    queue: deque[int] = deque(starts)
    while queue:
        target = queue.popleft()
        for source in reverse[target]:
            if source not in reachable:
                reachable.add(source)
                queue.append(source)
    return reachable


def _check_progress(graph: dict) -> dict:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    success = {index for index, state in enumerate(states) if model.is_success(state)}
    terminal = {index for index, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = _reverse_reachable(edges, terminal)
    no_terminal_path = [
        _state_id(states[index])
        for index, state in enumerate(states)
        if not model.is_terminal(state) and index not in can_reach_terminal
    ]
    return {
        "ok": bool(success) and not no_terminal_path,
        "status": "OK" if bool(success) and not no_terminal_path else "VIOLATION",
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "success_state_count": len(success),
        "nonterminal_without_terminal_path_count": len(no_terminal_path),
        "nonterminal_without_terminal_path_samples": no_terminal_path[:20],
    }


def _tarjan_scc(edges: list[list[tuple[str, int]]]) -> list[list[int]]:
    index = 0
    stack: list[int] = []
    on_stack: set[int] = set()
    indices: dict[int, int] = {}
    lowlinks: dict[int, int] = {}
    components: list[list[int]] = []

    def strongconnect(node: int) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for _label, target in edges[node]:
            if target not in indices:
                strongconnect(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[int] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            components.append(component)

    for node in range(len(edges)):
        if node not in indices:
            strongconnect(node)
    return components


def _check_loops(graph: dict) -> dict:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    stuck = [
        _state_id(states[index])
        for index, outgoing in enumerate(edges)
        if not model.is_terminal(states[index]) and not outgoing
    ]
    closed_nonterminal_components: list[list[str]] = []
    for component in _tarjan_scc(edges):
        members = set(component)
        if any(model.is_terminal(states[index]) for index in members):
            continue
        has_outgoing_to_other_component = any(
            target not in members
            for index in members
            for _label, target in edges[index]
        )
        if not has_outgoing_to_other_component:
            closed_nonterminal_components.append(
                [_state_id(states[index]) for index in component[:5]]
            )
    ok = not stuck and not closed_nonterminal_components
    return {
        "ok": ok,
        "status": "OK" if ok else "VIOLATION",
        "state_count": len(states),
        "edge_count": graph["edge_count"],
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:20],
        "nonterminating_component_count": len(closed_nonterminal_components),
        "nonterminating_component_samples": closed_nonterminal_components[:20],
        "unreachable_success": not any(model.is_success(state) for state in states),
    }


def main() -> int:
    graph = _build_reachable_graph(max_states=GRAPH_STATE_LIMIT)
    graph_report = _graph_report_from_graph(graph)
    progress_report = _check_progress(graph)
    loop_report = _check_loops(graph)

    payload = {
        "graph": graph_report,
        "progress": progress_report,
        "loop": loop_report,
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    print("=== Capability State Graph ===")
    print(json.dumps(graph_report, indent=2, sort_keys=True))
    print()
    print("=== Progress Review ===")
    print(json.dumps(progress_report, indent=2, sort_keys=True))
    print()
    print("=== Loop/Stuck Review ===")
    print(json.dumps(loop_report, indent=2, sort_keys=True))

    return 0 if graph_report["ok"] and progress_report["ok"] and loop_report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
