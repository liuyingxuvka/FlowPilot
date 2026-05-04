"""Run FlowGuard checks for the flowpilot meta-process simulation."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import meta_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "results.json"
GRAPH_STATE_LIMIT = 900_000
CHECK_STATE_LIMIT = 900_000


REQUIRED_LABELS = (
    "startup_four_questions_asked",
    "startup_dialog_stopped_for_user_answers",
    "startup_display_surface_answered",
    "startup_display_entry_action_done",
    "startup_banner_emitted",
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
    "main_executor_parallel_prep_boundary_recorded",
    "independent_approval_protocol_recorded",
    "crew_memory_packets_written",
    "generated_resource_ledger_initialized",
    "activity_stream_initialized",
    "startup_self_interrogation_pm_ratified",
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
    "dependency_plan_recorded",
    "host_continuation_capability_supported",
    "host_continuation_capability_unsupported_manual_resume",
    "heartbeat_schedule_created",
    "pm_initial_route_decision_recorded",
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
    "flowguard_process_designed",
    "flowguard_officer_model_adversarial_probe_done",
    "candidate_route_tree_generated",
    "root_route_model_checked",
    "root_product_function_model_checked",
    "strict_gate_obligation_review_model_checked",
    "route_model_checked",
    "parent_backward_structural_trigger_rule_recorded",
    "parent_backward_review_targets_enumerated",
    "markdown_summary_synced",
    "execution_frontier_written",
    "codex_plan_synced",
    "user_flow_diagram_refreshed",
    "visible_user_flow_diagram_emitted",
    "user_flow_diagram_reviewer_display_checked",
    "live_subagent_start_authorized",
    "fresh_six_live_subagents_started",
    "startup_preflight_reviewer_fact_report_blocked",
    "pm_returns_startup_blockers_to_worker",
    "startup_worker_remediation_completed",
    "startup_preflight_reviewer_fact_report_clean",
    "startup_pm_independent_gate_audit_done",
    "pm_start_gate_opened_from_fact_report",
    "continuation_resume_ready_checked",
    "heartbeat_loaded_state",
    "heartbeat_loaded_execution_frontier",
    "heartbeat_loaded_crew_memory",
    "heartbeat_restored_six_agent_crew",
    "heartbeat_rehydrated_six_agent_crew",
    "crew_rehydration_report_written",
    "heartbeat_asked_project_manager",
    "pm_resume_completion_runway_recorded",
    "pm_runway_synced_to_visible_plan",
    "pm_node_work_decision_recorded",
    "unfinished_current_node_recovery_checked",
    "parent_subtree_review_checked",
    "parent_product_function_model_checked",
    "node_visible_roadmap_emitted",
    "parent_focused_interrogation_completed",
    "node_focused_interrogation_completed",
    "node_product_function_model_checked",
    "current_node_high_standard_recheck_written",
    "node_acceptance_plan_written",
    "node_acceptance_risk_experiments_mapped",
    "pm_review_hold_instruction_written",
    "lightweight_self_check_completed",
    "quality_package_passed_no_raise",
    "quality_package_small_raise_in_current_node",
    "quality_package_route_raise_needed",
    "chunk_verification_passed",
    "anti_rough_finish_passed",
    "anti_rough_finish_found_rework",
    "worker_output_ready_for_review",
    "pm_review_release_order_written",
    "pm_released_reviewer_for_current_gate",
    "node_human_inspection_context_loaded",
    "node_human_neutral_observation_written",
    "node_human_manual_experiments_run",
    "node_reviewer_independent_probe_done",
    "human_inspection_found_blocking_issue",
    "human_inspection_issue_grilled",
    "pm_repair_decision_interrogated",
    "route_updated_after_human_inspection_failure",
    "node_human_inspection_passed",
    "chunk_verified",
    "composite_backward_context_loaded",
    "composite_child_evidence_replayed",
    "composite_backward_neutral_observation_written",
    "composite_structure_decision_recorded",
    "composite_reviewer_independent_probe_done",
    "composite_backward_review_found_existing_child_gap",
    "composite_backward_review_found_missing_sibling",
    "composite_backward_review_found_subtree_mismatch",
    "composite_backward_issue_grilled",
    "route_updated_to_rework_composite_child",
    "route_updated_to_add_composite_sibling",
    "route_updated_to_rebuild_composite_subtree",
    "composite_backward_review_passed",
    "composite_backward_pm_segment_decision_recorded",
    "skill_improvement_observation_check_no_issue",
    "skill_improvement_observation_logged",
    "role_memory_packets_refreshed_after_work",
    "checkpoint_written",
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
    "high_value_work_found_and_route_expanded",
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
    "terminal_human_backward_replay_found_repair_issue",
    "terminal_human_backward_pm_repair_decision_interrogated",
    "route_updated_after_terminal_human_backward_replay_failure",
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
    "final_report_emitted",
    "verification_found_model_gap",
    "route_updated_after_model_gap",
    "verification_found_impl_failure",
    "implementation_fixed_for_retry",
    "experiment_found_new_path",
    "child_node_sidecar_scan_no_need",
    "child_node_sidecar_scan_need_found_no_pool",
    "child_node_sidecar_scan_need_found_existing_idle",
    "sidecar_scope_checked",
    "idle_subagent_reused",
    "subagent_spawned_on_demand",
    "sidecar_report_returned",
    "main_agent_merged_sidecar_report",
    "high_risk_gate_requested",
    "high_risk_gate_approved",
    "blocked_after_model_gap_budget",
)


def _state_id(state: model.State) -> str:
    return (
        f"{state.status}|node={state.active_node}|route={state.route_version}|"
        f"enabled={state.flowpilot_enabled}|mode_offer={state.mode_choice_offered}|"
        f"startup_banner={state.startup_banner_emitted}|"
        f"mode={state.mode_selected}|deps={state.dependency_plan_recorded},"
        f"{state.future_installs_deferred}|contract={state.contract_frozen}|"
        f"run={state.run_directory_created},{state.current_pointer_written},"
        f"{state.run_index_updated},{state.prior_work_mode},"
        f"{state.prior_work_import_packet_written},"
        f"{state.control_state_written_under_run_root},"
        f"{state.top_level_control_state_absent_or_quarantined},"
        f"{state.old_control_state_reused_as_current}|"
        f"showcase={state.showcase_floor_committed}|"
        f"visible_self_q={state.visible_self_interrogation_done},"
        f"{state.startup_self_interrogation_questions},"
        f"{state.startup_self_interrogation_layer_count},"
        f"{state.startup_self_interrogation_questions_per_layer},"
        f"{state.startup_self_interrogation_layers},"
        f"{state.startup_self_interrogation_pm_ratified}|"
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
        f"user_flow={state.visible_user_flow_diagram_emitted}|"
        f"crew={state.crew_policy_written},{state.crew_count},"
        f"{state.project_manager_ready},{state.reviewer_ready},"
        f"{state.process_flowguard_officer_ready},"
        f"{state.product_flowguard_officer_ready},"
        f"{state.worker_a_ready},{state.worker_b_ready},"
        f"{state.crew_ledger_written},{state.crew_memory_policy_written},"
        f"{state.crew_memory_packets_written},"
        f"{state.pm_initial_route_decision_recorded},"
        f"{state.crew_archived},{state.crew_memory_archived}|"
        f"officer_async={state.pm_flowguard_delegation_policy_recorded},"
        f"{state.officer_owned_async_modeling_policy_recorded},"
        f"{state.officer_model_report_provenance_policy_recorded},"
        f"{state.main_executor_parallel_prep_boundary_recorded},"
        f"{state.independent_approval_protocol_recorded}|"
        f"child_manifest={state.child_skill_route_design_discovery_started},"
        f"{state.child_skill_initial_gate_manifest_extracted},"
        f"{state.child_skill_gate_approvers_assigned},"
        f"{state.child_skill_manifest_independent_validation_done},"
        f"{state.child_skill_manifest_reviewer_reviewed},"
        f"{state.child_skill_manifest_process_officer_approved},"
        f"{state.child_skill_manifest_product_officer_approved},"
        f"{state.child_skill_manifest_pm_approved_for_route}|"
        f"continuation={state.continuation_probe_done},"
        f"{state.host_continuation_supported},"
        f"{state.manual_resume_mode_recorded},"
        f"{state.continuation_host_kind_recorded},"
        f"{state.continuation_evidence_written}|"
        f"heartbeat_schedule={state.heartbeat_schedule_created}|"
        f"heartbeat_recovery={state.heartbeat_loaded_state},"
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
        f"{state.pm_node_decision_recorded}|"
        f"stable_heartbeat={state.stable_heartbeat_launcher_recorded}|"
        f"continuation_ready={state.heartbeat_health_checked}|"
        f"continuation_lifecycle={state.heartbeat_schedule_created},"
        f"{state.route_heartbeat_interval_minutes},"
        f"{state.manual_resume_mode_recorded},"
        f"{state.lifecycle_reconciliation_done},"
        f"{state.terminal_lifecycle_frontier_written}|"
        f"fg_design={state.flowguard_process_design_done},"
        f"{state.flowguard_officer_model_adversarial_probe_done}|"
        f"candidate_tree={state.candidate_route_tree_generated}|"
        f"root_model={state.root_route_model_checked},"
        f"{state.root_route_model_process_officer_approved},"
        f"{state.root_product_function_model_checked},"
        f"{state.root_product_function_model_product_officer_approved},"
        f"strict_gate={state.strict_gate_obligation_review_model_checked}|"
        f"checked={state.route_checked}|md={state.markdown_synced}|"
        f"frontier={state.execution_frontier_written}:{state.frontier_version}|"
        f"plan={state.codex_plan_synced}:{state.plan_version}|"
        f"resource_ledgers={state.generated_resource_ledger_initialized},"
        f"{state.activity_stream_initialized},"
        f"{state.activity_stream_latest_event_written}|"
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
        f"unfinished_recovery={state.unfinished_current_node_recovery_checked}|"
        f"parent_subtree={state.parent_subtree_review_checked},"
        f"{state.parent_product_function_model_checked},"
        f"{state.parent_product_function_model_product_officer_approved}|"
        f"parent_backward_targets={state.parent_backward_structural_trigger_rule_recorded},"
        f"{state.parent_backward_review_targets_enumerated}|"
        f"chunk={state.chunk_state}|done={state.completed_chunks}/{state.required_chunks}|"
        f"node_map={state.node_visible_roadmap_emitted}|"
        f"parent_focused={state.parent_focused_interrogation_done},"
        f"{state.parent_focused_interrogation_questions},"
        f"{state.parent_focused_interrogation_scope_id}|"
        f"node_focused={state.node_focused_interrogation_done},"
        f"{state.node_focused_interrogation_questions},"
        f"{state.node_focused_interrogation_scope_id}|"
        f"node_product={state.node_product_function_model_checked},"
        f"{state.node_product_function_model_product_officer_approved}|"
        f"node_acceptance={state.current_node_high_standard_recheck_written},"
        f"{state.node_acceptance_plan_written},"
        f"{state.node_acceptance_risk_experiments_mapped},"
        f"{state.pm_review_hold_instruction_written}|"
        f"micro_self={state.lightweight_self_check_done},"
        f"{state.lightweight_self_check_questions},"
        f"{state.lightweight_self_check_scope_id}|"
        f"quality={state.quality_package_done},"
        f"{state.quality_candidate_registry_checked},"
        f"{state.quality_raise_decision_recorded},"
        f"{state.validation_matrix_defined},"
        f"{state.anti_rough_finish_done},"
        f"{state.worker_output_ready_for_review},"
        f"{state.pm_review_release_order_written},"
        f"{state.pm_released_reviewer_for_current_gate},"
        f"role_memory_refresh={state.role_memory_refreshed_after_work},"
        f"human_review={state.node_human_review_context_loaded},"
        f"{state.node_human_neutral_observation_written},"
        f"{state.node_human_manual_experiments_run},"
        f"{state.node_reviewer_independent_probe_done},"
        f"{state.node_human_inspection_passed},"
        f"{state.node_human_review_reviewer_approved},"
        f"node_review_count={state.node_human_inspections_passed},"
        f"{state.inspection_issue_grilled},"
        f"pm_repair_grills={state.pm_repair_decision_interrogations},"
        f"inspection_repairs={state.human_inspection_repairs},"
        f"composite_review={state.composite_backward_context_loaded},"
        f"{state.composite_child_evidence_replayed},"
        f"{state.composite_backward_neutral_observation_written},"
        f"{state.composite_structure_decision_recorded},"
        f"{state.composite_reviewer_independent_probe_done},"
        f"{state.composite_backward_human_review_passed},"
        f"{state.composite_backward_review_reviewer_approved},"
        f"composite_review_count={state.composite_backward_reviews_passed},"
        f"pm_segment={state.composite_backward_pm_segment_decision_recorded},"
        f"{state.composite_backward_pm_segment_decisions_recorded},"
        f"composite_issue={state.composite_issue_grilled},"
        f"{state.composite_issue_strategy},"
        f"structural_repairs={state.composite_structural_route_repairs},"
        f"siblings={state.composite_new_sibling_nodes},"
        f"subtree_rebuilds={state.composite_subtree_rebuilds},"
        f"skill_improvement={state.current_node_skill_improvement_check_done},"
        f"{state.flowpilot_skill_improvement_report_written},"
        f"raises={state.quality_route_raises},"
        f"reworks={state.quality_reworks}|"
        f"complete_map={state.completion_visible_roadmap_emitted}|"
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
        f"{state.terminal_human_backward_replay_repairs},"
        f"{state.final_route_wide_gate_ledger_reviewer_backward_checked},"
        f"{state.final_ledger_pm_independent_audit_done},"
        f"{state.final_route_wide_gate_ledger_pm_completion_approved}|"
        f"terminal_closure={state.terminal_closure_suite_run},"
        f"{state.terminal_state_and_evidence_refreshed}|"
        f"stop_notice={state.controlled_stop_notice_recorded},"
        f"{state.terminal_completion_notice_recorded}|"
        f"complete_self_q={state.completion_self_interrogation_done},"
        f"{state.completion_self_interrogation_questions},"
        f"{state.completion_self_interrogation_layer_count},"
        f"{state.completion_self_interrogation_questions_per_layer},"
        f"{state.completion_self_interrogation_layers}|"
        f"high_value={state.high_value_work_review}|standards={state.standard_expansions}|"
        f"issue={state.issue}|sidecar={state.child_node_sidecar_scan_done},"
        f"{state.sidecar_need},{state.subagent_pool_exists},"
        f"{state.subagent_idle_available},{state.subagent_scope_checked}|"
        f"sub={state.subagent_status}|gate={state.high_risk_gate}|"
        f"rev={state.route_revisions}|retry={state.impl_retries}|exp={state.experiments}"
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

    print("=== State Graph ===")
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
