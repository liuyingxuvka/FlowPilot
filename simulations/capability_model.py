"""FlowGuard model for flowpilot capability routing.

This model checks the planned skill-composition layer for FlowPilot. FlowPilot
starts only at showcase-grade scope, exposes its self-interrogation style
self-interrogation, creates heartbeat continuity, uses FlowGuard as process
designer before routing capabilities, and refuses completion while obvious
high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


REQUIRED_ROLE_BINDING_COUNT = 6
TARGET_PARENT_NODES = 1
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS = 20
MAX_UI_CHILD_SKILL_ITERATION_ROUNDS = 40
# State-space bound for exploring repeat UI loop branches. This is not a
# runtime limit; the child UI skill owns the actual iteration standard.
MAX_UI_VISUAL_ITERATIONS = 2
MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_SELF_INTERROGATION_QUESTIONS = 20
MAX_FOCUSED_SELF_INTERROGATION_QUESTIONS = 50
DEFAULT_FOCUSED_SELF_INTERROGATION_QUESTIONS = 30
MODEL_DYNAMIC_LAYER_COUNT = 6
LAYER_GOAL_ACCEPTANCE = 1 << 0
LAYER_FUNCTIONAL_CAPABILITY = 1 << 1
LAYER_DATA_STATE = 1 << 2
LAYER_IMPLEMENTATION_STRATEGY = 1 << 3
LAYER_UI_EXPERIENCE = 1 << 4
LAYER_VALIDATION = 1 << 5
LAYER_RECOVERY_HEARTBEAT = 1 << 6
LAYER_DELIVERY_SHOWCASE = 1 << 7
REQUIRED_RISK_FAMILY_MASK = (
    LAYER_GOAL_ACCEPTANCE
    | LAYER_FUNCTIONAL_CAPABILITY
    | LAYER_DATA_STATE
    | LAYER_IMPLEMENTATION_STRATEGY
    | LAYER_UI_EXPERIENCE
    | LAYER_VALIDATION
    | LAYER_RECOVERY_HEARTBEAT
    | LAYER_DELIVERY_SHOWCASE
)


@dataclass(frozen=True, slots=True)
class Tick:
    """One capability-routing decision."""


@dataclass(frozen=True, slots=True)
class Action:
    name: str


@dataclass(frozen=True, slots=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    task_kind: str = "unknown"  # unknown | backend | ui
    flowpilot_enabled: bool = False
    run_scoped_startup_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_intake_ui_completed: bool = False
    startup_intake_result_recorded: bool = False
    startup_runtime_role_assistance_option_recorded: bool = False
    startup_continuation_option_recorded: bool = False
    startup_display_surface_option_recorded: bool = False
    startup_answer_values_valid: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    startup_display_entry_action_done: bool = False
    run_directory_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    prior_work_mode: str = "unknown"  # unknown | new | continue
    prior_work_import_packet_written: bool = False
    control_state_written_under_run_root: bool = False
    prior_control_state_quarantined: bool = False
    preflow_visible_plan_cleared: bool = False
    old_control_state_reused_as_current: bool = False
    showcase_floor_committed: bool = False
    self_interrogation_done: bool = False
    self_interrogation_evidence: bool = False
    visible_self_interrogation_done: bool = False
    self_interrogation_questions: int = 0
    self_interrogation_layer_count: int = 0
    self_interrogation_questions_per_layer: int = 0
    self_interrogation_layers: int = 0
    self_interrogation_pm_ratified: bool = False
    self_interrogation_record_written: bool = False
    self_interrogation_findings_dispositioned: bool = False
    quality_candidate_pool_seeded: bool = False
    validation_strategy_seeded: bool = False
    material_sources_scanned: bool = False
    material_source_summaries_written: bool = False
    material_source_quality_classified: bool = False
    local_skill_inventory_written: bool = False
    local_skill_inventory_candidate_classified: bool = False
    material_intake_packet_written: bool = False
    material_reviewer_direct_source_probe_done: bool = False
    material_reviewer_sufficiency_checked: bool = False
    material_reviewer_sufficiency_approved: bool = False
    pm_material_understanding_memo_written: bool = False
    pm_material_complexity_classified: bool = False
    pm_material_discovery_decision_recorded: bool = False
    pm_material_research_decision_recorded: bool = False
    material_research_need: str = "unknown"  # unknown | not_required | required
    pm_research_package_written: bool = False
    research_tool_capability_decision_recorded: bool = False
    research_worker_report_returned: bool = False
    research_reviewer_direct_source_check_done: bool = False
    research_reviewer_rework_required: bool = False
    research_worker_rework_completed: bool = False
    research_reviewer_recheck_done: bool = False
    research_reviewer_sufficiency_passed: bool = False
    pm_research_result_absorbed_or_route_mutated: bool = False
    product_function_architecture_pm_synthesized: bool = False
    product_function_high_standard_posture_written: bool = False
    product_function_target_and_failure_bar_written: bool = False
    product_function_minimum_sufficient_complexity_review_written: bool = False
    product_function_semantic_fidelity_policy_written: bool = False
    product_function_user_task_map_written: bool = False
    product_function_capability_map_written: bool = False
    product_function_feature_decisions_written: bool = False
    product_function_display_rationale_written: bool = False
    product_function_gap_review_done: bool = False
    product_function_negative_scope_written: bool = False
    product_function_acceptance_matrix_written: bool = False
    root_acceptance_thresholds_defined: bool = False
    root_acceptance_proof_matrix_written: bool = False
    standard_scenario_pack_selected: bool = False
    product_architecture_officer_adversarial_probe_done: bool = False
    product_function_architecture_product_officer_approved: bool = False
    product_architecture_reviewer_adversarial_probe_done: bool = False
    product_function_architecture_reviewer_challenged: bool = False
    product_architecture_self_interrogation_record_written: bool = False
    product_architecture_self_interrogation_findings_dispositioned: bool = False
    contract_frozen: bool = False
    role_binding_policy_written: bool = False
    role_binding_count: int = 0
    project_manager_ready: bool = False
    reviewer_ready: bool = False
    process_flowguard_officer_ready: bool = False
    product_flowguard_officer_ready: bool = False
    worker_a_ready: bool = False
    worker_b_ready: bool = False
    role_binding_ledger_written: bool = False
    role_identity_protocol_recorded: bool = False
    pm_flowguard_delegation_policy_recorded: bool = False
    officer_owned_async_modeling_policy_recorded: bool = False
    officer_model_report_provenance_policy_recorded: bool = False
    controller_coordination_boundary_recorded: bool = False
    independent_approval_protocol_recorded: bool = False
    role_binding_memory_policy_written: bool = False
    role_binding_memory_packets_written: int = 0
    controller_core_loaded: bool = False
    router_daemon_started: bool = False
    router_daemon_lock_acquired: bool = False
    router_daemon_tick_seconds: int = 0
    router_daemon_status_written: bool = False
    controller_action_ledger_initialized: bool = False
    controller_action_watch_active: bool = False
    router_daemon_recovered_on_resume: bool = False
    terminal_router_daemon_stopped: bool = False
    pm_initial_capability_decision_recorded: bool = False
    heartbeat_loaded_state: bool = False
    heartbeat_loaded_frontier: bool = False
    heartbeat_loaded_packet_ledger: bool = False
    heartbeat_loaded_role_binding_memory: bool = False
    heartbeat_host_rehydrate_requested: bool = False
    heartbeat_restored_crew: bool = False
    heartbeat_rehydrated_crew: bool = False
    heartbeat_injected_current_run_memory_into_roles: bool = False
    role_binding_recovery_report_written: bool = False
    replacement_roles_seeded_from_memory: bool = False
    heartbeat_pm_decision_requested: bool = False
    heartbeat_pm_controller_reminder_checked: bool = False
    heartbeat_reviewer_dispatch_policy_checked: bool = False
    pm_resume_decision_recorded: bool = False
    pm_completion_runway_recorded: bool = False
    pm_runway_hard_stops_recorded: bool = False
    pm_runway_checkpoint_cadence_recorded: bool = False
    pm_runway_synced_to_plan: bool = False
    plan_sync_method_recorded: bool = False
    visible_plan_has_runway_depth: bool = False
    pm_capability_work_decision_recorded: bool = False
    role_binding_ledger_archived: bool = False
    role_binding_memory_archived: bool = False
    continuation_probe_done: bool = False
    continuation_host_kind_recorded: bool = False
    continuation_evidence_written: bool = False
    host_continuation_supported: bool = False
    manual_resume_mode_recorded: bool = False

    capabilities_manifest_written: bool = False
    pm_child_skill_selection_manifest_written: bool = False
    pm_child_skill_minimum_sufficient_complexity_review_written: bool = False
    pm_child_skill_selection_scope_decisions_recorded: bool = False
    child_skill_route_design_discovery_started: bool = False
    child_skill_initial_gate_manifest_extracted: bool = False
    child_skill_gate_approvers_assigned: bool = False
    child_skill_manifest_independent_validation_done: bool = False
    child_skill_manifest_reviewer_reviewed: bool = False
    child_skill_manifest_process_officer_approved: bool = False
    child_skill_manifest_product_officer_approved: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    child_skill_focused_interrogation_done: bool = False
    child_skill_focused_interrogation_questions: int = 0
    child_skill_focused_interrogation_scope_id: str = ""
    node_self_interrogation_record_written: bool = False
    node_self_interrogation_findings_dispositioned: bool = False
    child_skill_contracts_loaded: bool = False
    child_skill_exact_source_verified: bool = False
    child_skill_substitutes_rejected: bool = False
    child_skill_original_standards_extracted: bool = False
    child_skill_standards_promoted_to_node_contract: bool = False
    child_skill_gate_evidence_obligations_bound: bool = False
    flowpilot_invocation_policy_mapped: bool = False
    child_skill_requirements_mapped: bool = False
    child_skill_evidence_plan_written: bool = False
    child_skill_subroute_projected: bool = False
    current_node_high_standard_recheck_written: bool = False
    current_node_minimum_sufficient_complexity_review_written: bool = False
    node_acceptance_plan_written: bool = False
    active_child_skill_bindings_written: bool = False
    active_child_skill_binding_scope_limited: bool = False
    child_skill_stricter_standard_precedence_bound: bool = False
    node_acceptance_risk_experiments_mapped: bool = False
    child_skill_node_gate_manifest_refined: bool = False
    child_skill_gate_authority_records_written: bool = False
    worker_packet_child_skill_use_instruction_written: bool = False
    active_child_skill_source_paths_allowed: bool = False
    child_skill_conformance_model_checked: bool = False
    child_skill_conformance_model_process_officer_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
    child_skill_manifest_only_evidence_rejected: bool = False
    child_skill_execution_reports_written: bool = False
    worker_child_skill_use_evidence_returned: bool = False
    reviewer_child_skill_use_evidence_checked: bool = False
    child_skill_execution_evidence_audited: bool = False
    child_skill_evidence_matches_outputs: bool = False
    child_skill_domain_quality_checked: bool = False
    child_skill_iteration_loop_closed: bool = False
    current_child_skill_gate_independent_validation_done: bool = False
    child_skill_current_gates_role_approved: bool = False
    child_skill_completion_verified: bool = False
    dependency_plan_recorded: bool = False
    future_installs_deferred: bool = False
    flowguard_dependency_checked: bool = False
    heartbeat_schedule_created: bool = False
    route_heartbeat_interval_minutes: int = 0
    stable_heartbeat_launcher_recorded: bool = False
    heartbeat_health_checked: bool = False
    runtime_role_assistance_decision_recorded: bool = False
    runtime_role_bindings_opened: bool = False
    runtime_role_bindings_current_task_ready: bool = False
    role_bindings_opened_after_startup_answers: bool = False
    role_bindings_opened_after_route_allocation: bool = False
    historical_agent_ids_compared: bool = False
    reused_historical_agent_ids: bool = False
    single_agent_role_continuity_authorized: bool = False
    startup_preflight_review_report_written: bool = False
    startup_preflight_review_blocking_findings: bool = False
    startup_reviewer_fact_evidence_checked: bool = False
    startup_reviewer_checked_run_isolation: bool = False
    startup_reviewer_checked_prior_work_boundary: bool = False
    startup_reviewer_checked_live_agent_freshness: bool = False
    startup_reviewer_checked_no_historical_agent_reuse: bool = False
    startup_reviewer_checked_capability_resolution: bool = False
    startup_reviewer_checked_current_run_heartbeat_binding: bool = False
    startup_pm_capability_resolution_recorded: bool = False
    heartbeat_bound_to_current_run: bool = False
    heartbeat_same_name_only_checked: bool = False
    pm_returned_startup_blockers: bool = False
    startup_worker_remediation_completed: bool = False
    startup_pm_independent_gate_audit_done: bool = False
    pm_start_gate_opened: bool = False
    work_beyond_startup_allowed: bool = False
    terminal_lifecycle_frontier_written: bool = False
    lifecycle_reconciliation_done: bool = False
    controlled_stop_notice_recorded: bool = False
    terminal_completion_notice_recorded: bool = False
    defect_ledger_initialized: bool = False
    evidence_ledger_initialized: bool = False
    generated_resource_ledger_initialized: bool = False
    activity_stream_initialized: bool = False
    activity_stream_latest_event_written: bool = False
    flowpilot_improvement_live_report_initialized: bool = False
    flowpilot_improvement_live_report_updated: bool = False
    defect_ledger_zero_blocking: bool = False
    evidence_credibility_triage_done: bool = False
    pause_snapshot_written: bool = False
    flowguard_process_design_done: bool = False
    flowguard_officer_model_adversarial_probe_done: bool = False
    flowguard_model_report_risk_tiers_done: bool = False
    flowguard_model_report_pm_review_agenda_done: bool = False
    flowguard_model_report_toolchain_recommendations_done: bool = False
    flowguard_model_report_confidence_boundary_done: bool = False
    meta_route_checked: bool = False
    meta_route_process_officer_approved: bool = False
    capability_route_process_officer_approved: bool = False
    capability_product_function_model_checked: bool = False
    capability_product_function_model_product_officer_approved: bool = False

    ui_autonomous_pipeline_selected: bool = False
    ui_inspected: bool = False
    ui_concept_done: bool = False
    ui_concept_target_ready: bool = False
    ui_concept_target_visible: bool = False
    ui_concept_personal_visual_review_done: bool = False
    ui_concept_design_recommendations_recorded: bool = False
    ui_concept_aesthetic_review_done: bool = False
    ui_concept_aesthetic_reasons_recorded: bool = False
    ui_palette_contract_written: bool = False
    ui_palette_default_or_override_rationale_recorded: bool = False
    ui_selected_concept_bound_to_review_packet: bool = False
    ui_frontend_design_plan_done: bool = False
    ui_frontend_design_execution_report_written: bool = False
    visual_asset_scope: str = "unknown"  # unknown | none | required
    visual_asset_style_review_done: bool = False
    visual_asset_personal_visual_review_done: bool = False
    visual_asset_design_recommendations_recorded: bool = False
    visual_asset_aesthetic_review_done: bool = False
    visual_asset_aesthetic_reasons_recorded: bool = False
    ui_implemented: bool = False
    ui_screenshot_qa_done: bool = False
    ui_geometry_qa_done: bool = False
    ui_reviewer_personal_walkthrough_done: bool = False
    ui_visible_affordance_interaction_matrix_written: bool = False
    ui_visible_affordance_interaction_matrix_complete: bool = False
    ui_interaction_reachability_checked: bool = False
    ui_layout_overlap_density_checked: bool = False
    ui_reviewer_design_recommendations_recorded: bool = False
    ui_implementation_aesthetic_review_done: bool = False
    ui_implementation_aesthetic_reasons_recorded: bool = False
    ui_concept_vs_implementation_deviation_table_written: bool = False
    ui_divergence_review_done: bool = False
    ui_iteration_budget_recorded: bool = False
    ui_iteration_rounds_required: int = 0
    ui_iteration_rounds_completed: int = 0
    ui_major_visual_deviation_triaged: bool = False
    ui_structural_redesign_route_considered: bool = False
    ui_visual_iteration_loop_closed: bool = False
    ui_visual_iterations: int = 0

    non_ui_implemented: bool = False
    implementation_human_review_context_loaded: bool = False
    implementation_human_neutral_observation_written: bool = False
    implementation_human_manual_experiments_run: bool = False
    implementation_reviewer_independent_probe_done: bool = False
    implementation_human_inspection_passed: bool = False
    implementation_human_review_reviewer_approved: bool = False
    capability_backward_context_loaded: bool = False
    capability_child_evidence_replayed: bool = False
    capability_backward_neutral_observation_written: bool = False
    capability_structure_decision_recorded: bool = False
    capability_backward_reviewer_independent_probe_done: bool = False
    capability_backward_human_review_passed: bool = False
    capability_backward_review_reviewer_approved: bool = False
    parent_backward_structural_trigger_rule_recorded: bool = False
    parent_backward_review_targets_enumerated: bool = False
    parent_backward_review_targets_route_version: int = 0
    parent_backward_targets_count: int = TARGET_PARENT_NODES
    capability_backward_pm_segment_decision_recorded: bool = False
    capability_backward_pm_segment_decisions_recorded: int = 0
    capability_backward_issue_interrogated: bool = False
    capability_backward_issue_strategy: str = "none"
    pm_repair_decision_interrogations: int = 0
    capability_structural_route_repairs: int = 0
    capability_new_sibling_nodes: int = 0
    capability_subtree_rebuilds: int = 0
    quality_package_done: bool = False
    quality_candidate_registry_checked: bool = False
    quality_raise_decision_recorded: bool = False
    validation_matrix_defined: bool = False
    anti_rough_finish_done: bool = False
    pm_review_hold_instruction_written: bool = False
    worker_output_ready_for_review: bool = False
    pm_package_result_disposition_recorded: bool = False
    pm_package_result_disposition_absorbed: bool = False
    pm_formal_gate_package_released: bool = False
    pm_formal_gate_package_identity_recorded: bool = False
    pm_review_release_order_written: bool = False
    pm_released_reviewer_for_current_gate: bool = False
    packet_runtime_physical_files_written: bool = False
    controller_context_body_exclusion_verified: bool = False
    controller_relay_signature_audit_done: bool = False
    recipient_pre_open_relay_check_done: bool = False
    packet_mail_chain_audit_done: bool = False
    unopened_mail_pm_recovery_policy_recorded: bool = False
    router_hard_rejection_seen: bool = False
    control_blocker_artifact_written: bool = False
    control_blocker_handling_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required | fatal_protocol_violation
    blocker_repair_policy_snapshot_written: bool = False
    blocker_policy_row_attached: bool = False
    control_blocker_first_handler: str = "none"  # none | responsible_role | project_manager
    control_blocker_direct_retry_budget: int = 0
    control_blocker_direct_retry_attempts: int = 0
    control_blocker_retry_budget_exhausted: bool = False
    control_blocker_escalated_to_pm: bool = False
    pm_blocker_recovery_option_recorded: bool = False
    pm_blocker_return_gate_recorded: bool = False
    pm_blocker_hard_stop_checked: bool = False
    pm_blocker_silent_pass_forbidden: bool = False
    control_blocker_delivered_to_responsible_role: bool = False
    control_blocker_delivered_to_pm: bool = False
    packet_envelope_body_audit_done: bool = False
    packet_envelope_to_role_checked: bool = False
    packet_body_hash_verified: bool = False
    result_envelope_checked: bool = False
    result_body_hash_verified: bool = False
    completed_agent_id_role_verified: bool = False
    controller_body_boundary_verified: bool = False
    wrong_role_relabel_forbidden_verified: bool = False
    packet_role_origin_audit_done: bool = False
    packet_result_author_verified: bool = False
    packet_result_author_matches_assignment: bool = False
    role_memory_refreshed_after_work: bool = False
    current_node_skill_improvement_check_done: bool = False
    quality_route_raises: int = 0
    quality_reworks: int = 0
    final_verification_done: bool = False
    completion_self_interrogation_done: bool = False
    completion_self_interrogation_questions: int = 0
    completion_self_interrogation_layer_count: int = 0
    completion_self_interrogation_questions_per_layer: int = 0
    completion_self_interrogation_layers: int = 0
    completion_self_interrogation_record_written: bool = False
    completion_self_interrogation_findings_dispositioned: bool = False
    completion_visible_user_flow_diagram_emitted: bool = False
    final_feature_matrix_review_done: bool = False
    final_acceptance_matrix_review_done: bool = False
    final_standard_scenario_pack_replayed: bool = False
    final_quality_candidate_review_done: bool = False
    final_product_function_model_replayed: bool = False
    final_product_model_officer_adversarial_probe_done: bool = False
    final_product_function_model_product_officer_approved: bool = False
    final_human_review_context_loaded: bool = False
    final_human_neutral_observation_written: bool = False
    final_human_manual_experiments_run: bool = False
    final_human_reviewer_independent_probe_done: bool = False
    final_human_inspection_passed: bool = False
    final_human_review_reviewer_approved: bool = False
    final_route_wide_gate_ledger_current_route_scanned: bool = False
    final_route_wide_gate_ledger_effective_nodes_resolved: bool = False
    final_route_wide_gate_ledger_child_skill_gates_collected: bool = False
    final_route_wide_gate_ledger_human_review_gates_collected: bool = False
    final_route_wide_gate_ledger_parent_backward_replays_collected: bool = False
    final_route_wide_gate_ledger_product_process_gates_collected: bool = False
    final_route_wide_gate_ledger_resource_lineage_resolved: bool = False
    final_route_wide_gate_ledger_stale_evidence_checked: bool = False
    final_route_wide_gate_ledger_superseded_nodes_explained: bool = False
    final_route_wide_gate_ledger_unresolved_count_zero: bool = False
    final_route_wide_gate_ledger_self_interrogation_collected: bool = False
    self_interrogation_index_clean: bool = False
    final_residual_risk_triage_done: bool = False
    final_residual_risk_unresolved_count_zero: bool = False
    final_route_wide_gate_ledger_pm_built: bool = False
    terminal_human_backward_review_map_built: bool = False
    terminal_human_backward_replay_started_from_delivered_product: bool = False
    terminal_human_backward_root_acceptance_reviewed: bool = False
    terminal_human_backward_parent_nodes_reviewed: bool = False
    terminal_human_backward_leaf_nodes_reviewed: bool = False
    terminal_human_backward_pm_segment_decisions_recorded: bool = False
    terminal_human_backward_repair_restart_policy_recorded: bool = False
    final_route_wide_gate_ledger_reviewer_backward_checked: bool = False
    final_ledger_pm_independent_audit_done: bool = False
    final_route_wide_gate_ledger_pm_completion_approved: bool = False
    high_value_work_review: str = "unknown"  # unknown | exhausted
    standard_expansions: int = 0
    terminal_closure_suite_run: bool = False
    terminal_state_and_evidence_refreshed: bool = False
    flowpilot_skill_improvement_report_written: bool = False
    pm_completion_decision_recorded: bool = False

    child_node_sidecar_scan_done: bool = False
    sidecar_need: str = "unknown"  # unknown | none | needed
    sidecar_role_pool_exists: bool = False
    sidecar_role_idle_available: bool = False
    sidecar_role_status: str = "none"  # none | idle | pending | returned | merged
    sidecar_role_scope_checked: bool = False
    critical_path_blocked: bool = False

    capability_route_version: int = 0
    capability_route_checked: bool = False
    capability_evidence_synced: bool = False
    execution_frontier_written: bool = False
    codex_plan_synced: bool = False
    frontier_version: int = 0
    plan_version: int = 0
    capability_user_flow_diagram_refreshed: bool = False
    capability_user_flow_diagram_emitted: bool = False


def _step(state: State, *, label: str, action: str, **changes) -> FunctionResult:
    return FunctionResult(
        output=Action(action),
        new_state=replace(state, **changes),
        label=label,
    )


def _merged_changes(*groups: dict[str, object]) -> dict[str, object]:
    merged: dict[str, object] = {}
    for group in groups:
        merged.update(group)
    return merged


def _reset_quality_gates() -> dict[str, object]:
    return {
        "quality_package_done": False,
        "quality_candidate_registry_checked": False,
        "quality_raise_decision_recorded": False,
        "validation_matrix_defined": False,
        "anti_rough_finish_done": False,
    }


def _reset_human_inspection_gates() -> dict[str, object]:
    gates = {
        "implementation_human_review_context_loaded": False,
        "implementation_human_neutral_observation_written": False,
        "implementation_human_manual_experiments_run": False,
        "implementation_reviewer_independent_probe_done": False,
        "implementation_human_inspection_passed": False,
        "implementation_human_review_reviewer_approved": False,
        "pm_review_hold_instruction_written": False,
        "worker_output_ready_for_review": False,
        "pm_package_result_disposition_recorded": False,
        "pm_package_result_disposition_absorbed": False,
        "pm_formal_gate_package_released": False,
        "pm_formal_gate_package_identity_recorded": False,
        "pm_review_release_order_written": False,
        "pm_released_reviewer_for_current_gate": False,
        "packet_runtime_physical_files_written": False,
        "controller_context_body_exclusion_verified": False,
        "controller_relay_signature_audit_done": False,
        "recipient_pre_open_relay_check_done": False,
        "packet_mail_chain_audit_done": False,
        "unopened_mail_pm_recovery_policy_recorded": False,
        "packet_envelope_body_audit_done": False,
        "packet_envelope_to_role_checked": False,
        "packet_body_hash_verified": False,
        "result_envelope_checked": False,
        "result_body_hash_verified": False,
        "completed_agent_id_role_verified": False,
        "controller_body_boundary_verified": False,
        "wrong_role_relabel_forbidden_verified": False,
        "packet_role_origin_audit_done": False,
        "packet_result_author_verified": False,
        "packet_result_author_matches_assignment": False,
        "capability_backward_context_loaded": False,
        "capability_child_evidence_replayed": False,
        "capability_backward_neutral_observation_written": False,
        "capability_structure_decision_recorded": False,
        "capability_backward_reviewer_independent_probe_done": False,
        "capability_backward_human_review_passed": False,
        "capability_backward_review_reviewer_approved": False,
        "capability_backward_pm_segment_decision_recorded": False,
        "capability_backward_issue_interrogated": False,
        "capability_backward_issue_strategy": "none",
        "final_product_function_model_replayed": False,
        "final_product_model_officer_adversarial_probe_done": False,
        "final_product_function_model_product_officer_approved": False,
        "final_standard_scenario_pack_replayed": False,
        "final_human_review_context_loaded": False,
        "final_human_neutral_observation_written": False,
        "final_human_manual_experiments_run": False,
        "final_human_reviewer_independent_probe_done": False,
        "final_human_inspection_passed": False,
        "final_human_review_reviewer_approved": False,
        "pm_completion_decision_recorded": False,
    }
    gates.update(_reset_final_route_wide_gate_ledger())
    return gates


def _reset_final_route_wide_gate_ledger() -> dict[str, object]:
    return {
        "final_route_wide_gate_ledger_current_route_scanned": False,
        "final_route_wide_gate_ledger_effective_nodes_resolved": False,
        "final_route_wide_gate_ledger_child_skill_gates_collected": False,
        "final_route_wide_gate_ledger_human_review_gates_collected": False,
        "final_route_wide_gate_ledger_parent_backward_replays_collected": False,
        "final_route_wide_gate_ledger_product_process_gates_collected": False,
        "final_route_wide_gate_ledger_resource_lineage_resolved": False,
        "evidence_credibility_triage_done": False,
        "final_route_wide_gate_ledger_stale_evidence_checked": False,
        "final_route_wide_gate_ledger_superseded_nodes_explained": False,
        "final_route_wide_gate_ledger_unresolved_count_zero": False,
        "final_route_wide_gate_ledger_self_interrogation_collected": False,
        "self_interrogation_index_clean": False,
        "final_residual_risk_triage_done": False,
        "final_residual_risk_unresolved_count_zero": False,
        "defect_ledger_zero_blocking": False,
        "final_route_wide_gate_ledger_pm_built": False,
        "terminal_human_backward_review_map_built": False,
        "terminal_human_backward_replay_started_from_delivered_product": False,
        "terminal_human_backward_root_acceptance_reviewed": False,
        "terminal_human_backward_parent_nodes_reviewed": False,
        "terminal_human_backward_leaf_nodes_reviewed": False,
        "terminal_human_backward_pm_segment_decisions_recorded": False,
        "terminal_human_backward_repair_restart_policy_recorded": False,
        "final_route_wide_gate_ledger_reviewer_backward_checked": False,
        "final_ledger_pm_independent_audit_done": False,
        "final_route_wide_gate_ledger_pm_completion_approved": False,
        "terminal_closure_suite_run": False,
        "terminal_state_and_evidence_refreshed": False,
        "flowpilot_skill_improvement_report_written": False,
    }


def _reset_execution_quality_gates() -> dict[str, object]:
    gates = _reset_quality_gates()
    gates.update(_reset_human_inspection_gates())
    gates.update(
        {
            "heartbeat_loaded_state": False,
            "heartbeat_loaded_frontier": False,
            "heartbeat_loaded_packet_ledger": False,
            "heartbeat_loaded_role_binding_memory": False,
            "heartbeat_host_rehydrate_requested": False,
            "heartbeat_restored_crew": False,
            "heartbeat_rehydrated_crew": False,
            "heartbeat_injected_current_run_memory_into_roles": False,
            "role_binding_recovery_report_written": False,
            "replacement_roles_seeded_from_memory": False,
            "heartbeat_pm_decision_requested": False,
            "heartbeat_pm_controller_reminder_checked": False,
            "heartbeat_reviewer_dispatch_policy_checked": False,
            "pm_resume_decision_recorded": False,
            "pm_completion_runway_recorded": False,
            "pm_runway_hard_stops_recorded": False,
            "pm_runway_checkpoint_cadence_recorded": False,
            "pm_runway_synced_to_plan": False,
            "plan_sync_method_recorded": False,
            "visible_plan_has_runway_depth": False,
            "pm_capability_work_decision_recorded": False,
            "current_node_high_standard_recheck_written": False,
            "current_node_minimum_sufficient_complexity_review_written": False,
            "node_acceptance_plan_written": False,
            "active_child_skill_bindings_written": False,
            "active_child_skill_binding_scope_limited": False,
            "child_skill_stricter_standard_precedence_bound": False,
            "node_acceptance_risk_experiments_mapped": False,
            "child_skill_node_gate_manifest_refined": False,
            "child_skill_gate_authority_records_written": False,
            "worker_packet_child_skill_use_instruction_written": False,
            "active_child_skill_source_paths_allowed": False,
            "child_skill_manifest_only_evidence_rejected": False,
            "child_skill_execution_reports_written": False,
            "worker_child_skill_use_evidence_returned": False,
            "reviewer_child_skill_use_evidence_checked": False,
            "current_child_skill_gate_independent_validation_done": False,
            "child_skill_current_gates_role_approved": False,
            "node_self_interrogation_record_written": False,
            "node_self_interrogation_findings_dispositioned": False,
            "child_node_sidecar_scan_done": False,
            "sidecar_need": "unknown",
            "sidecar_role_scope_checked": False,
            "role_memory_refreshed_after_work": False,
            "current_node_skill_improvement_check_done": False,
            "critical_path_blocked": False,
        }
    )
    return gates


def _capability_structural_repair_changes(state: State) -> dict[str, object]:
    return {
        "capability_route_version": state.capability_route_version + 1,
        "capability_route_checked": False,
        "capability_route_process_officer_approved": False,
        "capability_product_function_model_checked": False,
        "capability_product_function_model_product_officer_approved": False,
        "capability_evidence_synced": False,
        "execution_frontier_written": False,
        "codex_plan_synced": False,
        "frontier_version": 0,
        "plan_version": 0,
        "capability_user_flow_diagram_refreshed": False,
        "capability_user_flow_diagram_emitted": False,
        "heartbeat_health_checked": False,
        "final_verification_done": False,
        "child_skill_route_design_discovery_started": False,
        "child_skill_initial_gate_manifest_extracted": False,
        "child_skill_gate_approvers_assigned": False,
        "child_skill_manifest_independent_validation_done": False,
        "child_skill_manifest_reviewer_reviewed": False,
        "child_skill_manifest_process_officer_approved": False,
        "child_skill_manifest_product_officer_approved": False,
        "child_skill_manifest_pm_approved_for_route": False,
        "child_skill_contracts_loaded": False,
        "child_skill_focused_interrogation_done": False,
        "child_skill_focused_interrogation_questions": 0,
        "child_skill_focused_interrogation_scope_id": "",
        "node_self_interrogation_record_written": False,
        "node_self_interrogation_findings_dispositioned": False,
        "child_skill_exact_source_verified": False,
        "child_skill_substitutes_rejected": False,
        "child_skill_original_standards_extracted": False,
        "child_skill_standards_promoted_to_node_contract": False,
        "child_skill_gate_evidence_obligations_bound": False,
        "flowpilot_invocation_policy_mapped": False,
        "child_skill_requirements_mapped": False,
        "child_skill_evidence_plan_written": False,
        "child_skill_subroute_projected": False,
        "non_ui_implemented": False,
        "ui_palette_contract_written": False,
        "ui_palette_default_or_override_rationale_recorded": False,
        "ui_selected_concept_bound_to_review_packet": False,
        "ui_concept_target_ready": False,
        "ui_concept_target_visible": False,
        "ui_concept_personal_visual_review_done": False,
        "ui_concept_design_recommendations_recorded": False,
        "ui_frontend_design_plan_done": False,
        "ui_frontend_design_execution_report_written": False,
        "visual_asset_scope": "unknown",
        "visual_asset_style_review_done": False,
        "visual_asset_personal_visual_review_done": False,
        "visual_asset_design_recommendations_recorded": False,
        "ui_implemented": False,
        "ui_screenshot_qa_done": False,
        "ui_geometry_qa_done": False,
        "ui_reviewer_personal_walkthrough_done": False,
        "ui_visible_affordance_interaction_matrix_written": False,
        "ui_visible_affordance_interaction_matrix_complete": False,
        "ui_interaction_reachability_checked": False,
        "ui_layout_overlap_density_checked": False,
        "ui_reviewer_design_recommendations_recorded": False,
        "ui_implementation_aesthetic_review_done": False,
        "ui_implementation_aesthetic_reasons_recorded": False,
        "ui_concept_vs_implementation_deviation_table_written": False,
        "ui_divergence_review_done": False,
        "ui_iteration_budget_recorded": False,
        "ui_iteration_rounds_required": 0,
        "ui_iteration_rounds_completed": 0,
        "ui_major_visual_deviation_triaged": False,
        "ui_structural_redesign_route_considered": False,
        "ui_visual_iteration_loop_closed": False,
        "ui_concept_aesthetic_review_done": False,
        "ui_concept_aesthetic_reasons_recorded": False,
        "visual_asset_aesthetic_review_done": False,
        "visual_asset_aesthetic_reasons_recorded": False,
        "child_skill_completion_verified": False,
        "child_skill_conformance_model_checked": False,
        "child_skill_conformance_model_process_officer_approved": False,
        "strict_gate_obligation_review_model_checked": False,
        "child_skill_execution_evidence_audited": False,
        "child_skill_evidence_matches_outputs": False,
        "child_skill_domain_quality_checked": False,
        "child_skill_iteration_loop_closed": False,
        "flowguard_dependency_checked": False,
        "dependency_plan_recorded": False,
        "future_installs_deferred": False,
        "flowguard_process_design_done": False,
        "flowguard_officer_model_adversarial_probe_done": False,
        "meta_route_checked": False,
        "meta_route_process_officer_approved": False,
        "sidecar_role_status": "none",
        "capability_structural_route_repairs": state.capability_structural_route_repairs + 1,
    }


def _covers_required_risk_families(layer_mask: int) -> bool:
    return (layer_mask & REQUIRED_RISK_FAMILY_MASK) == REQUIRED_RISK_FAMILY_MASK


def _full_interrogation_ready(
    *,
    total_questions: int,
    layer_count: int,
    questions_per_layer: int,
    risk_family_mask: int,
) -> bool:
    return (
        layer_count > 0
        and questions_per_layer >= MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
        and total_questions >= layer_count * MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
        and _covers_required_risk_families(risk_family_mask)
    )


def _startup_self_interrogation_disposition_ready(state: State) -> bool:
    return (
        state.self_interrogation_done
        and state.visible_self_interrogation_done
        and state.self_interrogation_evidence
        and _full_interrogation_ready(
            total_questions=state.self_interrogation_questions,
            layer_count=state.self_interrogation_layer_count,
            questions_per_layer=state.self_interrogation_questions_per_layer,
            risk_family_mask=state.self_interrogation_layers,
        )
        and state.self_interrogation_record_written
        and state.self_interrogation_pm_ratified
        and state.self_interrogation_findings_dispositioned
    )


def _product_architecture_self_interrogation_disposition_ready(state: State) -> bool:
    return (
        state.product_architecture_self_interrogation_record_written
        and state.product_architecture_self_interrogation_findings_dispositioned
    )


def _root_self_interrogation_gate_ready(state: State) -> bool:
    return (
        _startup_self_interrogation_disposition_ready(state)
        and _product_architecture_self_interrogation_disposition_ready(state)
    )


def _focused_interrogation_ready(*, total_questions: int, scope_id: str) -> bool:
    return (
        bool(scope_id)
        and MIN_FOCUSED_SELF_INTERROGATION_QUESTIONS
        <= total_questions
        <= MAX_FOCUSED_SELF_INTERROGATION_QUESTIONS
    )


def _node_self_interrogation_gate_ready(state: State) -> bool:
    return (
        state.child_skill_focused_interrogation_done
        and _focused_interrogation_ready(
            total_questions=state.child_skill_focused_interrogation_questions,
            scope_id=state.child_skill_focused_interrogation_scope_id,
        )
        and state.node_self_interrogation_record_written
        and state.node_self_interrogation_findings_dispositioned
    )


def _completion_self_interrogation_gate_ready(state: State) -> bool:
    return (
        state.completion_self_interrogation_done
        and _full_interrogation_ready(
            total_questions=state.completion_self_interrogation_questions,
            layer_count=state.completion_self_interrogation_layer_count,
            questions_per_layer=state.completion_self_interrogation_questions_per_layer,
            risk_family_mask=state.completion_self_interrogation_layers,
        )
        and state.completion_self_interrogation_record_written
        and state.completion_self_interrogation_findings_dispositioned
    )


def _self_interrogation_index_final_ready(state: State) -> bool:
    return (
        _root_self_interrogation_gate_ready(state)
        and _completion_self_interrogation_gate_ready(state)
        and state.final_route_wide_gate_ledger_self_interrogation_collected
        and state.self_interrogation_index_clean
    )


def _product_function_architecture_ready(state: State) -> bool:
    return (
        _material_handoff_ready(state)
        and state.product_function_architecture_pm_synthesized
        and state.product_function_high_standard_posture_written
        and state.product_function_target_and_failure_bar_written
        and state.product_function_minimum_sufficient_complexity_review_written
        and state.product_function_semantic_fidelity_policy_written
        and state.product_function_user_task_map_written
        and state.product_function_capability_map_written
        and state.product_function_feature_decisions_written
        and state.product_function_display_rationale_written
        and state.product_function_gap_review_done
        and state.product_function_negative_scope_written
        and state.product_function_acceptance_matrix_written
        and state.root_acceptance_thresholds_defined
        and state.root_acceptance_proof_matrix_written
        and state.standard_scenario_pack_selected
        and state.product_architecture_officer_adversarial_probe_done
        and state.product_function_architecture_product_officer_approved
        and state.product_architecture_reviewer_adversarial_probe_done
        and state.product_function_architecture_reviewer_challenged
    )


def _material_handoff_ready(state: State) -> bool:
    return (
        state.self_interrogation_pm_ratified
        and state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
        and state.local_skill_inventory_written
        and state.local_skill_inventory_candidate_classified
        and state.material_intake_packet_written
        and state.material_reviewer_direct_source_probe_done
        and state.material_reviewer_sufficiency_checked
        and state.material_reviewer_sufficiency_approved
        and state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
        and state.pm_material_discovery_decision_recorded
        and state.pm_material_research_decision_recorded
        and (
            state.material_research_need == "not_required"
            or (
                state.material_research_need == "required"
                and state.pm_research_package_written
                and state.research_tool_capability_decision_recorded
                and state.research_worker_report_returned
                and state.research_reviewer_direct_source_check_done
                and state.research_reviewer_sufficiency_passed
                and state.pm_research_result_absorbed_or_route_mutated
            )
        )
    )


def _crew_ready(state: State) -> bool:
    return (
        state.role_binding_policy_written
        and state.role_binding_count == REQUIRED_ROLE_BINDING_COUNT
        and state.project_manager_ready
        and state.reviewer_ready
        and state.process_flowguard_officer_ready
        and state.product_flowguard_officer_ready
        and state.worker_a_ready
        and state.worker_b_ready
        and state.role_binding_ledger_written
        and state.role_identity_protocol_recorded
        and state.pm_flowguard_delegation_policy_recorded
        and state.officer_owned_async_modeling_policy_recorded
        and state.officer_model_report_provenance_policy_recorded
        and state.controller_coordination_boundary_recorded
        and state.independent_approval_protocol_recorded
        and state.role_binding_memory_policy_written
        and state.role_binding_memory_packets_written == REQUIRED_ROLE_BINDING_COUNT
    )


def _automated_continuation_configured(state: State) -> bool:
    return (
        state.continuation_probe_done
        and state.continuation_host_kind_recorded
        and state.continuation_evidence_written
        and state.host_continuation_supported
        and not state.manual_resume_mode_recorded
        and state.heartbeat_schedule_created
        and state.route_heartbeat_interval_minutes == 1
        and state.stable_heartbeat_launcher_recorded
        and state.heartbeat_bound_to_current_run
        and not state.heartbeat_same_name_only_checked
    )


def _automated_continuation_ready(state: State) -> bool:
    return _automated_continuation_configured(state)


def _manual_resume_ready(state: State) -> bool:
    return (
        state.continuation_probe_done
        and state.continuation_host_kind_recorded
        and state.continuation_evidence_written
        and not state.host_continuation_supported
        and state.manual_resume_mode_recorded
        and not state.heartbeat_schedule_created
        and state.route_heartbeat_interval_minutes == 0
        and not state.stable_heartbeat_launcher_recorded
    )


def _continuation_ready(state: State) -> bool:
    return _automated_continuation_ready(state) or _manual_resume_ready(state)


def _run_isolation_ready(state: State) -> bool:
    prior_work_resolved = state.prior_work_mode == "new" or (
        state.prior_work_mode == "continue"
        and state.prior_work_import_packet_written
    )
    return (
        state.run_directory_created
        and state.current_pointer_written
        and state.run_index_updated
        and state.defect_ledger_initialized
        and state.evidence_ledger_initialized
        and state.generated_resource_ledger_initialized
        and state.activity_stream_initialized
        and state.activity_stream_latest_event_written
        and state.flowpilot_improvement_live_report_initialized
        and prior_work_resolved
        and state.control_state_written_under_run_root
        and state.prior_control_state_quarantined
        and state.preflow_visible_plan_cleared
        and not state.old_control_state_reused_as_current
    )


def _runtime_role_binding_startup_resolved(state: State) -> bool:
    return (
        state.runtime_role_assistance_decision_recorded
        and (
            (
                state.runtime_role_bindings_opened
                and state.runtime_role_bindings_current_task_ready
                and state.role_bindings_opened_after_startup_answers
                and state.role_bindings_opened_after_route_allocation
                and state.historical_agent_ids_compared
                and not state.reused_historical_agent_ids
            )
            or state.single_agent_role_continuity_authorized
        )
    )


def _startup_questions_complete(state: State) -> bool:
    return (
        state.startup_intake_ui_completed
        and state.startup_intake_result_recorded
        and state.startup_runtime_role_assistance_option_recorded
        and state.startup_continuation_option_recorded
        and state.startup_display_surface_option_recorded
        and state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    )


def _continuation_lifecycle_valid(state: State) -> bool:
    return (
        _continuation_ready(state)
        or (
            _automated_continuation_configured(state)
            and state.lifecycle_reconciliation_done
        )
    )


def _startup_pm_gate_ready(state: State) -> bool:
    return (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and state.startup_reviewer_fact_evidence_checked
        and _run_isolation_ready(state)
        and state.startup_reviewer_checked_run_isolation
        and state.startup_reviewer_checked_prior_work_boundary
        and (
            state.single_agent_role_continuity_authorized
            or (
                state.startup_reviewer_checked_live_agent_freshness
                and state.startup_reviewer_checked_no_historical_agent_reuse
            )
        )
        and state.startup_reviewer_checked_capability_resolution
        and (
            state.manual_resume_mode_recorded
            or (
                state.startup_reviewer_checked_current_run_heartbeat_binding
                and state.heartbeat_bound_to_current_run
                and not state.heartbeat_same_name_only_checked
            )
        )
        and state.startup_pm_independent_gate_audit_done
        and state.startup_pm_capability_resolution_recorded
        and state.pm_start_gate_opened
    )


def _terminal_continuation_reconciled(state: State) -> bool:
    if _automated_continuation_configured(state):
        return (
            state.lifecycle_reconciliation_done
            and state.terminal_lifecycle_frontier_written
        )
    if _manual_resume_ready(state):
        return (
            state.lifecycle_reconciliation_done
            and state.terminal_lifecycle_frontier_written
        )
    return False


def _final_route_wide_gate_ledger_ready(state: State) -> bool:
    return (
        state.final_route_wide_gate_ledger_current_route_scanned
        and state.final_route_wide_gate_ledger_effective_nodes_resolved
        and state.final_route_wide_gate_ledger_child_skill_gates_collected
        and state.final_route_wide_gate_ledger_human_review_gates_collected
        and state.final_route_wide_gate_ledger_parent_backward_replays_collected
        and state.final_route_wide_gate_ledger_product_process_gates_collected
        and state.final_route_wide_gate_ledger_resource_lineage_resolved
        and state.evidence_credibility_triage_done
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_self_interrogation_collected
        and state.self_interrogation_index_clean
        and state.final_residual_risk_triage_done
        and state.final_residual_risk_unresolved_count_zero
        and state.defect_ledger_zero_blocking
        and state.final_route_wide_gate_ledger_pm_built
        and state.terminal_human_backward_review_map_built
        and state.terminal_human_backward_replay_started_from_delivered_product
        and state.terminal_human_backward_root_acceptance_reviewed
        and state.terminal_human_backward_parent_nodes_reviewed
        and state.terminal_human_backward_leaf_nodes_reviewed
        and state.terminal_human_backward_pm_segment_decisions_recorded
        and state.terminal_human_backward_repair_restart_policy_recorded
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_ledger_pm_independent_audit_done
        and state.final_route_wide_gate_ledger_pm_completion_approved
    )


def _base_ready(state: State) -> bool:
    return (
        state.status == "running"
        and _gates_ready(state)
    )


def _route_scaffold_ready(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and _run_isolation_ready(state)
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_ready(state)
        and state.flowguard_process_design_done
        and state.flowguard_officer_model_adversarial_probe_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.parent_backward_structural_trigger_rule_recorded
        and state.parent_backward_review_targets_enumerated
        and state.parent_backward_review_targets_route_version
        == state.capability_route_version
        and state.parent_backward_targets_count > 0
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and _runtime_role_binding_startup_resolved(state)
        and _startup_pm_gate_ready(state)
        and state.work_beyond_startup_allowed
    )


def _route_scaffold_lifecycle_valid(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and _run_isolation_ready(state)
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
        and state.flowguard_officer_model_adversarial_probe_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and _runtime_role_binding_startup_resolved(state)
        and _startup_pm_gate_ready(state)
        and state.work_beyond_startup_allowed
    )


def _route_scaffold_lifecycle_valid(state: State) -> bool:
    return (
        state.task_kind in {"backend", "ui"}
        and state.flowpilot_enabled
        and state.showcase_floor_committed
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.capabilities_manifest_written
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.child_skill_conformance_model_process_officer_approved
        and state.strict_gate_obligation_review_model_checked
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.flowguard_dependency_checked
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
        and state.flowguard_officer_model_adversarial_probe_done
        and state.meta_route_checked
        and state.meta_route_process_officer_approved
        and state.capability_route_checked
        and state.capability_route_process_officer_approved
        and state.capability_product_function_model_checked
        and state.capability_product_function_model_product_officer_approved
        and state.capability_evidence_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.capability_route_version
        and state.plan_version == state.frontier_version
        and state.capability_user_flow_diagram_refreshed
        and state.capability_user_flow_diagram_emitted
        and _runtime_role_binding_startup_resolved(state)
        and _startup_pm_gate_ready(state)
        and state.work_beyond_startup_allowed
    )


def _gates_ready(state: State) -> bool:
    return _route_scaffold_ready(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _sidecar_role_clear(state: State) -> bool:
    return state.sidecar_role_status in {"none", "idle", "merged"}


def _capability_backward_review_steps(
    state: State, *, domain: str
) -> Iterable[FunctionResult]:
    if not state.capability_backward_context_loaded:
        yield _step(
            state,
            label="capability_backward_context_loaded",
            action=f"load {domain} child-skill evidence, parent node goal, product model, and route structure before capability closure",
            capability_backward_context_loaded=True,
        )
        return
    if not state.capability_child_evidence_replayed:
        yield _step(
            state,
            label="capability_child_evidence_replayed",
            action=f"replay {domain} child-skill evidence backward against the parent capability goal",
            capability_child_evidence_replayed=True,
        )
        return
    if not state.capability_backward_neutral_observation_written:
        yield _step(
            state,
            label="capability_backward_neutral_observation_written",
            action=f"write a neutral observation of what the {domain} child-skill rollup actually shows before judging capability closure",
            capability_backward_neutral_observation_written=True,
        )
        return
    if not state.capability_structure_decision_recorded:
        yield _step(
            state,
            label="capability_structure_decision_recorded",
            action=f"classify whether the {domain} capability can close, needs an existing child node rework, needs a sibling node, or needs subtree rebuild",
            capability_structure_decision_recorded=True,
        )
        return
    if not state.capability_backward_reviewer_independent_probe_done:
        yield _step(
            state,
            label="capability_backward_reviewer_independent_probe_done",
            action=f"human-like reviewer probes {domain} child evidence against parent obligations, stale rollups, missing siblings, and report-only closure before backward approval",
            capability_backward_reviewer_independent_probe_done=True,
        )
        return
    if not state.capability_backward_human_review_passed:
        if (
            state.capability_structural_route_repairs == 0
            and state.capability_backward_issue_strategy == "none"
        ):
            yield _step(
                state,
                label="capability_backward_review_found_existing_child_gap",
                action=f"{domain} composite reviewer rejects closure and targets an existing child node for rework",
                capability_backward_issue_strategy="existing_child",
            )
            yield _step(
                state,
                label="capability_backward_review_found_missing_sibling",
                action=f"{domain} composite reviewer rejects closure because an adjacent sibling child node is missing",
                capability_backward_issue_strategy="add_sibling",
            )
            yield _step(
                state,
                label="capability_backward_review_found_subtree_mismatch",
                action=f"{domain} composite reviewer rejects closure and requires child subtree rebuild",
                capability_backward_issue_strategy="rebuild_subtree",
            )
            return
        yield _step(
            state,
            label="capability_backward_review_passed",
            action=f"human-like backward reviewer accepts the {domain} capability rollup before PM records the parent segment decision",
            capability_backward_human_review_passed=True,
            capability_backward_review_reviewer_approved=True,
        )
        return
    if not state.capability_backward_pm_segment_decision_recorded:
        yield _step(
            state,
            label="capability_backward_pm_segment_decision_recorded",
            action=f"project manager records the {domain} parent backward replay segment decision before capability closure",
            capability_backward_pm_segment_decision_recorded=True,
            capability_backward_pm_segment_decisions_recorded=state.capability_backward_pm_segment_decisions_recorded
            + 1,
        )


def _final_route_wide_gate_ledger_steps(
    state: State, *, domain: str
) -> Iterable[FunctionResult]:
    if not state.final_route_wide_gate_ledger_current_route_scanned:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_current_route_scanned",
            action=f"PM scans the current {domain} route, execution frontier, and mutation history for final gate ledger replay",
            final_route_wide_gate_ledger_current_route_scanned=True,
        )
        return
    if not state.final_route_wide_gate_ledger_effective_nodes_resolved:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_effective_nodes_resolved",
            action=f"PM resolves current, repaired, inserted, waived, and superseded {domain} nodes before final approval",
            final_route_wide_gate_ledger_effective_nodes_resolved=True,
        )
        return
    if not state.final_route_wide_gate_ledger_child_skill_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_child_skill_gates_collected",
            action=f"PM collects every current {domain} child-skill gate, completion standard, evidence path, waiver, blocker, and role approval",
            final_route_wide_gate_ledger_child_skill_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_human_review_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_human_review_gates_collected",
            action=f"PM collects all {domain} human-review, parent-review, strict-obligation, and same-inspector gates",
            final_route_wide_gate_ledger_human_review_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_parent_backward_replays_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_parent_backward_replays_collected",
            action=f"PM collects every structurally required local {domain} parent backward replay and PM segment decision",
            final_route_wide_gate_ledger_parent_backward_replays_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_product_process_gates_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_product_process_gates_collected",
            action=f"PM collects all {domain} product-function and development-process model gates",
            final_route_wide_gate_ledger_product_process_gates_collected=True,
        )
        return
    if not state.final_route_wide_gate_ledger_resource_lineage_resolved:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_resource_lineage_resolved",
            action=(
                f"PM resolves generated-resource lineage for {domain} into terminal "
                "dispositions: consumed_by_implementation, included_in_final_output, "
                "qa_evidence, flowguard_evidence, user_flow_diagram, superseded, "
                "quarantined, or discarded_with_reason"
            ),
            final_route_wide_gate_ledger_resource_lineage_resolved=True,
        )
        return
    if not state.evidence_credibility_triage_done:
        yield _step(
            state,
            label="evidence_credibility_triage_done",
            action=f"PM reconciles {domain} evidence credibility: valid live-project evidence is separated from invalid, stale, superseded, fixture-only, synthetic, historical, and generated-concept evidence",
            evidence_credibility_triage_done=True,
        )
        return
    if not state.final_route_wide_gate_ledger_stale_evidence_checked:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_stale_evidence_checked",
            action=f"PM checks no stale {domain} evidence is closing a current route obligation",
            final_route_wide_gate_ledger_stale_evidence_checked=True,
        )
        return
    if not state.final_route_wide_gate_ledger_superseded_nodes_explained:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_superseded_nodes_explained",
            action=f"PM explains every superseded {domain} node or gate as replaced, waived, or no longer effective",
            final_route_wide_gate_ledger_superseded_nodes_explained=True,
        )
        return
    if not state.final_route_wide_gate_ledger_unresolved_count_zero:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_unresolved_count_zero",
            action=f"PM records zero unresolved current-route {domain} obligations before final reviewer replay",
            final_route_wide_gate_ledger_unresolved_count_zero=True,
        )
        return
    if not state.final_route_wide_gate_ledger_self_interrogation_collected:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_self_interrogation_collected",
            action=f"PM cites the route self-interrogation index and collects startup, product-architecture, node, role-result, and completion self-interrogation dispositions into the final {domain} ledger",
            final_route_wide_gate_ledger_self_interrogation_collected=True,
        )
        return
    if not state.self_interrogation_index_clean:
        yield _step(
            state,
            label="self_interrogation_index_clean",
            action=f"PM proves the self-interrogation index has no unresolved hard or current {domain} findings before final ledger build and terminal closure",
            self_interrogation_index_clean=True,
        )
        return
    if not state.final_residual_risk_triage_done:
        yield _step(
            state,
            label="final_residual_risk_triage_done",
            action=f"PM triages every remaining {domain} risk or blindspot as fixed, routed to repair, current-gate blocker, terminal replay scenario, non-risk note, or explicit exception",
            final_residual_risk_triage_done=True,
        )
        return
    if not state.final_residual_risk_unresolved_count_zero:
        yield _step(
            state,
            label="final_residual_risk_unresolved_count_zero",
            action=f"PM records zero unresolved residual {domain} risks before final ledger can be built",
            final_residual_risk_unresolved_count_zero=True,
        )
        return
    if not state.defect_ledger_zero_blocking:
        yield _step(
            state,
            label="defect_ledger_zero_blocking",
            action=f"PM checks the {domain} defect ledger and records zero open blockers and zero fixed-pending-recheck defects before final ledger can be built",
            defect_ledger_zero_blocking=True,
        )
        return
    if not state.final_route_wide_gate_ledger_pm_built:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_pm_built",
            action=f"PM writes the final route-wide {domain} gate ledger from current route state and evidence",
            final_route_wide_gate_ledger_pm_built=True,
        )
        return
    if not state.terminal_human_backward_review_map_built:
        yield _step(
            state,
            label="terminal_human_backward_review_map_built",
            action=f"PM converts the final {domain} ledger into an ordered human backward replay map from delivered output to root, parent, and leaf obligations",
            terminal_human_backward_review_map_built=True,
        )
        return
    if not state.terminal_human_backward_replay_started_from_delivered_product:
        yield _step(
            state,
            label="terminal_human_backward_replay_started_from_delivered_product",
            action=f"human-like reviewer starts terminal {domain} replay from the delivered output itself rather than ledger entries or worker reports",
            terminal_human_backward_replay_started_from_delivered_product=True,
        )
        return
    if not state.terminal_human_backward_root_acceptance_reviewed:
        yield _step(
            state,
            label="terminal_human_backward_root_acceptance_reviewed",
            action=f"human-like reviewer manually checks final {domain} output against root acceptance and baseline functional obligations",
            terminal_human_backward_root_acceptance_reviewed=True,
        )
        return
    if not state.terminal_human_backward_parent_nodes_reviewed:
        yield _step(
            state,
            label="terminal_human_backward_parent_nodes_reviewed",
            action=f"human-like reviewer walks backward through effective parent {domain} nodes and checks that child outcomes compose into parent goals",
            terminal_human_backward_parent_nodes_reviewed=True,
        )
        return
    if not state.terminal_human_backward_leaf_nodes_reviewed:
        yield _step(
            state,
            label="terminal_human_backward_leaf_nodes_reviewed",
            action=f"human-like reviewer manually checks every effective leaf {domain} node against its node acceptance plan, experiments, and current output behavior",
            terminal_human_backward_leaf_nodes_reviewed=True,
        )
        return
    if not state.terminal_human_backward_pm_segment_decisions_recorded:
        yield _step(
            state,
            label="terminal_human_backward_pm_segment_decisions_recorded",
            action=f"PM records continue or repair decisions for every terminal {domain} backward replay segment",
            terminal_human_backward_pm_segment_decisions_recorded=True,
        )
        return
    if not state.terminal_human_backward_repair_restart_policy_recorded:
        yield _step(
            state,
            label="terminal_human_backward_repair_restart_policy_recorded",
            action=f"PM records that any terminal {domain} replay repair invalidates affected evidence and restarts final review from the delivered output unless a narrower impacted-ancestor restart is justified",
            terminal_human_backward_repair_restart_policy_recorded=True,
        )
        return
    if not state.final_route_wide_gate_ledger_reviewer_backward_checked:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_reviewer_backward_checked",
            action=f"human-like reviewer completes terminal {domain} backward replay through every effective root, parent, and leaf-node obligation in the PM-built map",
            final_route_wide_gate_ledger_reviewer_backward_checked=True,
        )
        return
    if not state.final_ledger_pm_independent_audit_done:
        yield _step(
            state,
            label="final_ledger_pm_independent_audit_done",
            action=f"PM independently audits {domain} route/frontier/ledger entries, stale evidence, waiver authority, unresolved counts, reviewer replay, and blindspots before completion approval",
            final_ledger_pm_independent_audit_done=True,
        )
        return
    if not state.final_route_wide_gate_ledger_pm_completion_approved:
        yield _step(
            state,
            label="final_route_wide_gate_ledger_pm_completion_approved",
            action=f"PM approves the clean route-wide {domain} gate ledger from independent adversarial audit evidence before lifecycle closure and final completion decision",
            final_route_wide_gate_ledger_pm_completion_approved=True,
        )


class CapabilityRouterStep:
    name = "CapabilityRouterStep"
    reads = (
        "status",
        "task_kind",
        "flowpilot_enabled",
        "startup_intake_ui_completed",
        "startup_intake_result_recorded",
        "startup_runtime_role_assistance_option_recorded",
        "startup_continuation_option_recorded",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "prior_control_state_quarantined",
        "preflow_visible_plan_cleared",
        "old_control_state_reused_as_current",
        "showcase_floor_committed",
        "self_interrogation_done",
        "self_interrogation_questions",
        "self_interrogation_layer_count",
        "self_interrogation_questions_per_layer",
        "self_interrogation_layers",
        "self_interrogation_pm_ratified",
        "self_interrogation_record_written",
        "self_interrogation_findings_dispositioned",
        "quality_candidate_pool_seeded",
        "validation_strategy_seeded",
        "material_sources_scanned",
        "material_source_summaries_written",
        "material_source_quality_classified",
        "material_intake_packet_written",
        "material_reviewer_direct_source_probe_done",
        "material_reviewer_sufficiency_checked",
        "material_reviewer_sufficiency_approved",
        "pm_material_understanding_memo_written",
        "pm_material_complexity_classified",
        "pm_material_discovery_decision_recorded",
        "pm_material_research_decision_recorded",
        "material_research_need",
        "pm_research_package_written",
        "research_tool_capability_decision_recorded",
        "research_worker_report_returned",
        "research_reviewer_direct_source_check_done",
        "research_reviewer_rework_required",
        "research_worker_rework_completed",
        "research_reviewer_recheck_done",
        "research_reviewer_sufficiency_passed",
        "pm_research_result_absorbed_or_route_mutated",
        "product_function_architecture_pm_synthesized",
        "product_function_high_standard_posture_written",
        "product_function_target_and_failure_bar_written",
        "product_function_minimum_sufficient_complexity_review_written",
        "product_function_semantic_fidelity_policy_written",
        "product_function_user_task_map_written",
        "product_function_capability_map_written",
        "product_function_feature_decisions_written",
        "product_function_display_rationale_written",
        "product_function_gap_review_done",
        "product_function_negative_scope_written",
        "product_function_acceptance_matrix_written",
        "root_acceptance_thresholds_defined",
        "root_acceptance_proof_matrix_written",
        "standard_scenario_pack_selected",
        "product_architecture_officer_adversarial_probe_done",
        "product_function_architecture_product_officer_approved",
        "product_architecture_reviewer_adversarial_probe_done",
        "product_function_architecture_reviewer_challenged",
        "product_architecture_self_interrogation_record_written",
        "product_architecture_self_interrogation_findings_dispositioned",
        "visible_self_interrogation_done",
        "contract_frozen",
        "role_binding_policy_written",
        "role_binding_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "role_binding_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "officer_owned_async_modeling_policy_recorded",
        "officer_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "role_binding_memory_policy_written",
        "role_binding_memory_packets_written",
        "controller_core_loaded",
        "pm_initial_capability_decision_recorded",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_role_binding_memory",
        "heartbeat_host_rehydrate_requested",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "heartbeat_injected_current_run_memory_into_roles",
        "role_binding_recovery_report_written",
        "replacement_roles_seeded_from_memory",
        "heartbeat_pm_decision_requested",
        "heartbeat_pm_controller_reminder_checked",
        "heartbeat_reviewer_dispatch_policy_checked",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_capability_work_decision_recorded",
        "role_binding_ledger_archived",
        "role_binding_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
        "capabilities_manifest_written",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "child_skill_focused_interrogation_done",
        "child_skill_focused_interrogation_questions",
        "child_skill_focused_interrogation_scope_id",
        "node_self_interrogation_record_written",
        "node_self_interrogation_findings_dispositioned",
        "child_skill_contracts_loaded",
        "child_skill_exact_source_verified",
        "child_skill_substitutes_rejected",
        "child_skill_original_standards_extracted",
        "child_skill_standards_promoted_to_node_contract",
        "child_skill_gate_evidence_obligations_bound",
        "flowpilot_invocation_policy_mapped",
        "child_skill_requirements_mapped",
        "child_skill_evidence_plan_written",
        "child_skill_subroute_projected",
        "current_node_high_standard_recheck_written",
        "current_node_minimum_sufficient_complexity_review_written",
        "node_acceptance_plan_written",
        "active_child_skill_bindings_written",
        "active_child_skill_binding_scope_limited",
        "child_skill_stricter_standard_precedence_bound",
        "node_acceptance_risk_experiments_mapped",
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "worker_packet_child_skill_use_instruction_written",
        "active_child_skill_source_paths_allowed",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "child_skill_manifest_only_evidence_rejected",
        "child_skill_execution_reports_written",
        "worker_child_skill_use_evidence_returned",
        "reviewer_child_skill_use_evidence_checked",
        "child_skill_execution_evidence_audited",
        "child_skill_evidence_matches_outputs",
        "child_skill_domain_quality_checked",
        "child_skill_iteration_loop_closed",
        "current_child_skill_gate_independent_validation_done",
        "child_skill_current_gates_role_approved",
        "child_skill_completion_verified",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "flowguard_dependency_checked",
        "heartbeat_schedule_created",
        "route_heartbeat_interval_minutes",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
        "runtime_role_assistance_decision_recorded",
        "runtime_role_bindings_opened",
        "runtime_role_bindings_current_task_ready",
        "role_bindings_opened_after_startup_answers",
        "role_bindings_opened_after_route_allocation",
        "historical_agent_ids_compared",
        "reused_historical_agent_ids",
        "single_agent_role_continuity_authorized",
        "startup_preflight_review_report_written",
        "startup_preflight_review_blocking_findings",
        "startup_reviewer_fact_evidence_checked",
        "startup_reviewer_checked_run_isolation",
        "startup_reviewer_checked_prior_work_boundary",
        "startup_reviewer_checked_live_agent_freshness",
        "startup_reviewer_checked_no_historical_agent_reuse",
        "pm_returned_startup_blockers",
        "startup_worker_remediation_completed",
        "startup_pm_independent_gate_audit_done",
        "pm_start_gate_opened",
        "work_beyond_startup_allowed",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "defect_ledger_initialized",
        "evidence_ledger_initialized",
        "generated_resource_ledger_initialized",
        "activity_stream_initialized",
        "activity_stream_latest_event_written",
        "flowpilot_improvement_live_report_initialized",
        "flowpilot_improvement_live_report_updated",
        "defect_ledger_zero_blocking",
        "evidence_credibility_triage_done",
        "pause_snapshot_written",
        "flowguard_process_design_done",
        "flowguard_officer_model_adversarial_probe_done",
        "meta_route_checked",
        "capability_route_checked",
        "meta_route_process_officer_approved",
        "capability_route_process_officer_approved",
        "capability_product_function_model_checked",
        "capability_product_function_model_product_officer_approved",
        "parent_backward_structural_trigger_rule_recorded",
        "parent_backward_review_targets_enumerated",
        "parent_backward_review_targets_route_version",
        "parent_backward_targets_count",
        "capability_evidence_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "capability_user_flow_diagram_refreshed",
        "capability_user_flow_diagram_emitted",
        "ui_autonomous_pipeline_selected",
        "ui_concept_done",
        "ui_concept_target_ready",
        "ui_concept_target_visible",
        "ui_concept_personal_visual_review_done",
        "ui_concept_design_recommendations_recorded",
        "ui_concept_aesthetic_review_done",
        "ui_concept_aesthetic_reasons_recorded",
        "ui_palette_contract_written",
        "ui_palette_default_or_override_rationale_recorded",
        "ui_selected_concept_bound_to_review_packet",
        "visual_asset_scope",
        "ui_frontend_design_execution_report_written",
        "visual_asset_style_review_done",
        "visual_asset_personal_visual_review_done",
        "visual_asset_design_recommendations_recorded",
        "visual_asset_aesthetic_review_done",
        "visual_asset_aesthetic_reasons_recorded",
        "ui_screenshot_qa_done",
        "ui_geometry_qa_done",
        "ui_reviewer_personal_walkthrough_done",
        "ui_visible_affordance_interaction_matrix_written",
        "ui_visible_affordance_interaction_matrix_complete",
        "ui_interaction_reachability_checked",
        "ui_layout_overlap_density_checked",
        "ui_reviewer_design_recommendations_recorded",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_concept_vs_implementation_deviation_table_written",
        "ui_iteration_budget_recorded",
        "ui_iteration_rounds_required",
        "ui_iteration_rounds_completed",
        "ui_major_visual_deviation_triaged",
        "ui_structural_redesign_route_considered",
        "ui_visual_iteration_loop_closed",
        "ui_visual_iterations",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "pm_review_hold_instruction_written",
        "worker_output_ready_for_review",
        "pm_package_result_disposition_recorded",
        "pm_package_result_disposition_absorbed",
        "pm_formal_gate_package_released",
        "pm_formal_gate_package_identity_recorded",
        "pm_review_release_order_written",
        "pm_released_reviewer_for_current_gate",
        "packet_runtime_physical_files_written",
        "controller_context_body_exclusion_verified",
        "controller_relay_signature_audit_done",
        "recipient_pre_open_relay_check_done",
        "packet_mail_chain_audit_done",
        "unopened_mail_pm_recovery_policy_recorded",
        "packet_envelope_body_audit_done",
        "packet_envelope_to_role_checked",
        "packet_body_hash_verified",
        "result_envelope_checked",
        "result_body_hash_verified",
        "completed_agent_id_role_verified",
        "controller_body_boundary_verified",
        "wrong_role_relabel_forbidden_verified",
        "packet_role_origin_audit_done",
        "packet_result_author_verified",
        "packet_result_author_matches_assignment",
        "role_memory_refreshed_after_work",
        "current_node_skill_improvement_check_done",
        "implementation_human_review_context_loaded",
        "implementation_human_neutral_observation_written",
        "implementation_human_manual_experiments_run",
        "implementation_reviewer_independent_probe_done",
        "implementation_human_inspection_passed",
        "implementation_human_review_reviewer_approved",
        "capability_backward_context_loaded",
        "capability_child_evidence_replayed",
        "capability_backward_neutral_observation_written",
        "capability_structure_decision_recorded",
        "capability_backward_reviewer_independent_probe_done",
        "capability_backward_human_review_passed",
        "capability_backward_review_reviewer_approved",
        "capability_backward_pm_segment_decision_recorded",
        "capability_backward_pm_segment_decisions_recorded",
        "capability_backward_issue_interrogated",
        "capability_backward_issue_strategy",
        "capability_structural_route_repairs",
        "capability_new_sibling_nodes",
        "capability_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_self_interrogation_record_written",
        "completion_self_interrogation_findings_dispositioned",
        "completion_visible_user_flow_diagram_emitted",
        "final_feature_matrix_review_done",
        "final_acceptance_matrix_review_done",
        "final_standard_scenario_pack_replayed",
        "final_quality_candidate_review_done",
        "final_product_function_model_replayed",
        "final_product_model_officer_adversarial_probe_done",
        "final_product_function_model_product_officer_approved",
        "final_human_review_context_loaded",
        "final_human_neutral_observation_written",
        "final_human_manual_experiments_run",
        "final_human_reviewer_independent_probe_done",
        "final_human_inspection_passed",
        "final_human_review_reviewer_approved",
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
        "final_route_wide_gate_ledger_self_interrogation_collected",
        "self_interrogation_index_clean",
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
        "flowpilot_skill_improvement_report_written",
        "pm_completion_decision_recorded",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "sidecar_role_pool_exists",
        "sidecar_role_idle_available",
        "sidecar_role_status",
    )
    writes = (
        "status",
        "task_kind",
        "flowpilot_enabled",
        "startup_intake_ui_completed",
        "startup_intake_result_recorded",
        "startup_runtime_role_assistance_option_recorded",
        "startup_continuation_option_recorded",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "prior_control_state_quarantined",
        "preflow_visible_plan_cleared",
        "old_control_state_reused_as_current",
        "showcase_floor_committed",
        "self_interrogation_done",
        "self_interrogation_evidence",
        "visible_self_interrogation_done",
        "self_interrogation_questions",
        "self_interrogation_layer_count",
        "self_interrogation_questions_per_layer",
        "self_interrogation_layers",
        "self_interrogation_pm_ratified",
        "self_interrogation_record_written",
        "self_interrogation_findings_dispositioned",
        "quality_candidate_pool_seeded",
        "validation_strategy_seeded",
        "material_sources_scanned",
        "material_source_summaries_written",
        "material_source_quality_classified",
        "material_intake_packet_written",
        "material_reviewer_direct_source_probe_done",
        "material_reviewer_sufficiency_checked",
        "material_reviewer_sufficiency_approved",
        "pm_material_understanding_memo_written",
        "pm_material_complexity_classified",
        "pm_material_discovery_decision_recorded",
        "pm_material_research_decision_recorded",
        "material_research_need",
        "pm_research_package_written",
        "research_tool_capability_decision_recorded",
        "research_worker_report_returned",
        "research_reviewer_direct_source_check_done",
        "research_reviewer_rework_required",
        "research_worker_rework_completed",
        "research_reviewer_recheck_done",
        "research_reviewer_sufficiency_passed",
        "pm_research_result_absorbed_or_route_mutated",
        "product_function_architecture_pm_synthesized",
        "product_function_high_standard_posture_written",
        "product_function_target_and_failure_bar_written",
        "product_function_minimum_sufficient_complexity_review_written",
        "product_function_semantic_fidelity_policy_written",
        "product_function_user_task_map_written",
        "product_function_capability_map_written",
        "product_function_feature_decisions_written",
        "product_function_display_rationale_written",
        "product_function_gap_review_done",
        "product_function_negative_scope_written",
        "product_function_acceptance_matrix_written",
        "root_acceptance_thresholds_defined",
        "root_acceptance_proof_matrix_written",
        "standard_scenario_pack_selected",
        "product_architecture_officer_adversarial_probe_done",
        "product_function_architecture_product_officer_approved",
        "product_architecture_reviewer_adversarial_probe_done",
        "product_function_architecture_reviewer_challenged",
        "product_architecture_self_interrogation_record_written",
        "product_architecture_self_interrogation_findings_dispositioned",
        "contract_frozen",
        "role_binding_policy_written",
        "role_binding_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "role_binding_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "officer_owned_async_modeling_policy_recorded",
        "officer_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "role_binding_memory_policy_written",
        "role_binding_memory_packets_written",
        "controller_core_loaded",
        "pm_initial_capability_decision_recorded",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_role_binding_memory",
        "heartbeat_host_rehydrate_requested",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "heartbeat_injected_current_run_memory_into_roles",
        "role_binding_recovery_report_written",
        "replacement_roles_seeded_from_memory",
        "heartbeat_pm_decision_requested",
        "heartbeat_pm_controller_reminder_checked",
        "heartbeat_reviewer_dispatch_policy_checked",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_capability_work_decision_recorded",
        "role_binding_ledger_archived",
        "role_binding_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
        "capabilities_manifest_written",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_process_officer_approved",
        "child_skill_manifest_product_officer_approved",
        "child_skill_manifest_pm_approved_for_route",
        "child_skill_focused_interrogation_done",
        "child_skill_focused_interrogation_questions",
        "child_skill_focused_interrogation_scope_id",
        "node_self_interrogation_record_written",
        "node_self_interrogation_findings_dispositioned",
        "child_skill_contracts_loaded",
        "child_skill_exact_source_verified",
        "child_skill_substitutes_rejected",
        "child_skill_original_standards_extracted",
        "child_skill_standards_promoted_to_node_contract",
        "child_skill_gate_evidence_obligations_bound",
        "flowpilot_invocation_policy_mapped",
        "child_skill_requirements_mapped",
        "child_skill_evidence_plan_written",
        "child_skill_subroute_projected",
        "current_node_high_standard_recheck_written",
        "current_node_minimum_sufficient_complexity_review_written",
        "node_acceptance_plan_written",
        "active_child_skill_bindings_written",
        "active_child_skill_binding_scope_limited",
        "child_skill_stricter_standard_precedence_bound",
        "node_acceptance_risk_experiments_mapped",
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "worker_packet_child_skill_use_instruction_written",
        "active_child_skill_source_paths_allowed",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "child_skill_manifest_only_evidence_rejected",
        "child_skill_execution_reports_written",
        "worker_child_skill_use_evidence_returned",
        "reviewer_child_skill_use_evidence_checked",
        "child_skill_execution_evidence_audited",
        "child_skill_evidence_matches_outputs",
        "child_skill_domain_quality_checked",
        "child_skill_iteration_loop_closed",
        "current_child_skill_gate_independent_validation_done",
        "child_skill_current_gates_role_approved",
        "child_skill_completion_verified",
        "dependency_plan_recorded",
        "future_installs_deferred",
        "flowguard_dependency_checked",
        "heartbeat_schedule_created",
        "route_heartbeat_interval_minutes",
        "stable_heartbeat_launcher_recorded",
        "heartbeat_health_checked",
        "runtime_role_assistance_decision_recorded",
        "runtime_role_bindings_opened",
        "runtime_role_bindings_current_task_ready",
        "role_bindings_opened_after_startup_answers",
        "role_bindings_opened_after_route_allocation",
        "historical_agent_ids_compared",
        "reused_historical_agent_ids",
        "single_agent_role_continuity_authorized",
        "startup_preflight_review_report_written",
        "startup_preflight_review_blocking_findings",
        "startup_reviewer_fact_evidence_checked",
        "startup_reviewer_checked_run_isolation",
        "startup_reviewer_checked_prior_work_boundary",
        "startup_reviewer_checked_live_agent_freshness",
        "startup_reviewer_checked_no_historical_agent_reuse",
        "pm_returned_startup_blockers",
        "startup_worker_remediation_completed",
        "startup_pm_independent_gate_audit_done",
        "pm_start_gate_opened",
        "work_beyond_startup_allowed",
        "terminal_lifecycle_frontier_written",
        "lifecycle_reconciliation_done",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "defect_ledger_initialized",
        "evidence_ledger_initialized",
        "generated_resource_ledger_initialized",
        "activity_stream_initialized",
        "activity_stream_latest_event_written",
        "flowpilot_improvement_live_report_initialized",
        "flowpilot_improvement_live_report_updated",
        "defect_ledger_zero_blocking",
        "evidence_credibility_triage_done",
        "pause_snapshot_written",
        "flowguard_process_design_done",
        "flowguard_officer_model_adversarial_probe_done",
        "meta_route_checked",
        "meta_route_process_officer_approved",
        "capability_route_process_officer_approved",
        "capability_product_function_model_checked",
        "capability_product_function_model_product_officer_approved",
        "parent_backward_structural_trigger_rule_recorded",
        "parent_backward_review_targets_enumerated",
        "parent_backward_review_targets_route_version",
        "parent_backward_targets_count",
        "ui_autonomous_pipeline_selected",
        "ui_inspected",
        "ui_concept_done",
        "ui_concept_target_ready",
        "ui_concept_target_visible",
        "ui_concept_personal_visual_review_done",
        "ui_concept_design_recommendations_recorded",
        "ui_concept_aesthetic_review_done",
        "ui_concept_aesthetic_reasons_recorded",
        "ui_palette_contract_written",
        "ui_palette_default_or_override_rationale_recorded",
        "ui_selected_concept_bound_to_review_packet",
        "ui_frontend_design_plan_done",
        "ui_frontend_design_execution_report_written",
        "visual_asset_scope",
        "visual_asset_style_review_done",
        "visual_asset_personal_visual_review_done",
        "visual_asset_design_recommendations_recorded",
        "visual_asset_aesthetic_review_done",
        "visual_asset_aesthetic_reasons_recorded",
        "ui_implemented",
        "ui_screenshot_qa_done",
        "ui_geometry_qa_done",
        "ui_reviewer_personal_walkthrough_done",
        "ui_visible_affordance_interaction_matrix_written",
        "ui_visible_affordance_interaction_matrix_complete",
        "ui_interaction_reachability_checked",
        "ui_layout_overlap_density_checked",
        "ui_reviewer_design_recommendations_recorded",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_concept_vs_implementation_deviation_table_written",
        "ui_divergence_review_done",
        "ui_iteration_budget_recorded",
        "ui_iteration_rounds_required",
        "ui_iteration_rounds_completed",
        "ui_major_visual_deviation_triaged",
        "ui_structural_redesign_route_considered",
        "ui_visual_iteration_loop_closed",
        "ui_visual_iterations",
        "non_ui_implemented",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "pm_review_hold_instruction_written",
        "worker_output_ready_for_review",
        "pm_package_result_disposition_recorded",
        "pm_package_result_disposition_absorbed",
        "pm_formal_gate_package_released",
        "pm_formal_gate_package_identity_recorded",
        "pm_review_release_order_written",
        "pm_released_reviewer_for_current_gate",
        "packet_runtime_physical_files_written",
        "controller_context_body_exclusion_verified",
        "controller_relay_signature_audit_done",
        "recipient_pre_open_relay_check_done",
        "packet_mail_chain_audit_done",
        "unopened_mail_pm_recovery_policy_recorded",
        "packet_envelope_body_audit_done",
        "packet_envelope_to_role_checked",
        "packet_body_hash_verified",
        "result_envelope_checked",
        "result_body_hash_verified",
        "completed_agent_id_role_verified",
        "controller_body_boundary_verified",
        "wrong_role_relabel_forbidden_verified",
        "packet_role_origin_audit_done",
        "packet_result_author_verified",
        "packet_result_author_matches_assignment",
        "role_memory_refreshed_after_work",
        "current_node_skill_improvement_check_done",
        "implementation_human_review_context_loaded",
        "implementation_human_neutral_observation_written",
        "implementation_human_manual_experiments_run",
        "implementation_reviewer_independent_probe_done",
        "implementation_human_inspection_passed",
        "implementation_human_review_reviewer_approved",
        "capability_backward_context_loaded",
        "capability_child_evidence_replayed",
        "capability_backward_neutral_observation_written",
        "capability_structure_decision_recorded",
        "capability_backward_reviewer_independent_probe_done",
        "capability_backward_human_review_passed",
        "capability_backward_review_reviewer_approved",
        "capability_backward_pm_segment_decision_recorded",
        "capability_backward_pm_segment_decisions_recorded",
        "capability_backward_issue_interrogated",
        "capability_backward_issue_strategy",
        "capability_structural_route_repairs",
        "capability_new_sibling_nodes",
        "capability_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "final_verification_done",
        "completion_self_interrogation_done",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_self_interrogation_record_written",
        "completion_self_interrogation_findings_dispositioned",
        "completion_visible_user_flow_diagram_emitted",
        "final_feature_matrix_review_done",
        "final_acceptance_matrix_review_done",
        "final_standard_scenario_pack_replayed",
        "final_quality_candidate_review_done",
        "final_product_function_model_replayed",
        "final_product_model_officer_adversarial_probe_done",
        "final_product_function_model_product_officer_approved",
        "final_human_review_context_loaded",
        "final_human_neutral_observation_written",
        "final_human_manual_experiments_run",
        "final_human_reviewer_independent_probe_done",
        "final_human_inspection_passed",
        "final_human_review_reviewer_approved",
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
        "final_route_wide_gate_ledger_self_interrogation_collected",
        "self_interrogation_index_clean",
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
        "high_value_work_review",
        "standard_expansions",
        "terminal_closure_suite_run",
        "terminal_state_and_evidence_refreshed",
        "flowpilot_skill_improvement_report_written",
        "pm_completion_decision_recorded",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "defect_ledger_initialized",
        "evidence_ledger_initialized",
        "generated_resource_ledger_initialized",
        "activity_stream_initialized",
        "activity_stream_latest_event_written",
        "flowpilot_improvement_live_report_initialized",
        "flowpilot_improvement_live_report_updated",
        "defect_ledger_zero_blocking",
        "evidence_credibility_triage_done",
        "pause_snapshot_written",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "sidecar_role_pool_exists",
        "sidecar_role_idle_available",
        "sidecar_role_status",
        "sidecar_role_scope_checked",
        "capability_route_version",
        "capability_route_checked",
        "capability_evidence_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "capability_user_flow_diagram_refreshed",
        "capability_user_flow_diagram_emitted",
    )
    accepted_input_type = Tick
    input_description = "one FlowPilot capability-routing decision"
    output_description = "next allowed capability gate or implementation action"
    idempotency = (
        "Capability routing records evidence for each invoked child skill and "
        "does not let dependent work proceed before the required gate is done."
    )

    def _apply_startup_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_startup_phase import apply_startup_phase
        else:
            from capability_model_startup_phase import apply_startup_phase

        yield from apply_startup_phase(self, state)


    def _apply_material_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_material_phase import apply_material_phase
        else:
            from capability_model_material_phase import apply_material_phase

        yield from apply_material_phase(self, state)


    def _apply_route_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_route_phase import apply_route_phase
        else:
            from capability_model_route_phase import apply_route_phase

        yield from apply_route_phase(self, state)


    def _apply_resume_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_resume_phase import apply_resume_phase
        else:
            from capability_model_resume_phase import apply_resume_phase

        yield from apply_resume_phase(self, state)


    def _apply_node_execution_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_node_execution_phase import apply_node_execution_phase
        else:
            from capability_model_node_execution_phase import apply_node_execution_phase

        yield from apply_node_execution_phase(self, state)


    def _apply_backend_execution_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_backend_execution_phase import apply_backend_execution_phase
        else:
            from capability_model_backend_execution_phase import apply_backend_execution_phase

        yield from apply_backend_execution_phase(self, state)


    def _apply_ui_execution_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_ui_execution_phase import apply_ui_execution_phase
        else:
            from capability_model_ui_execution_phase import apply_ui_execution_phase

        yield from apply_ui_execution_phase(self, state)


    def _apply_closure_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .capability_model_closure_phase import apply_closure_phase
        else:
            from capability_model_closure_phase import apply_closure_phase

        yield from apply_closure_phase(self, state)


    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        yield from self._apply_startup_phase(state)
        yield from self._apply_material_phase(state)
        yield from self._apply_route_phase(state)
        yield from self._apply_resume_phase(state)
        yield from self._apply_node_execution_phase(state)
        yield from self._apply_backend_execution_phase(state)
        yield from self._apply_ui_execution_phase(state)
        yield from self._apply_closure_phase(state)


def terminal_predicate(current_output, state: State, trace) -> bool:
    del current_output, trace
    return state.status in {"blocked", "complete"}


def self_interrogation_before_contract(state: State, trace) -> InvariantResult:
    del trace
    if state.contract_frozen and not (
        state.showcase_floor_committed
        and _run_isolation_ready(state)
        and state.self_interrogation_done
        and state.self_interrogation_evidence
        and state.visible_self_interrogation_done
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _root_self_interrogation_gate_ready(state)
        and _full_interrogation_ready(
            total_questions=state.self_interrogation_questions,
            layer_count=state.self_interrogation_layer_count,
            questions_per_layer=state.self_interrogation_questions_per_layer,
            risk_family_mask=state.self_interrogation_layers,
        )
        and _crew_ready(state)
        and _product_function_architecture_ready(state)
    ):
        return InvariantResult.fail("contract frozen before fresh run isolation, showcase floor, dynamic per-layer visible self-interrogation evidence, durable self-interrogation disposition, role binding recovery, PM product-function architecture, candidate pool, and validation direction")
    return InvariantResult.pass_()


def mode_choice_before_showcase_and_self_interrogation(state: State, trace) -> InvariantResult:
    del trace
    if (
        not state.startup_intake_result_recorded
        and (
            state.startup_runtime_role_assistance_option_recorded
            or state.startup_continuation_option_recorded
            or state.startup_display_surface_option_recorded
            or state.startup_display_entry_action_done
        )
    ):
        return InvariantResult.fail("capability startup continued after asking questions without stopping for the user's reply")
    if (
        state.showcase_floor_committed
        or state.self_interrogation_done
        or state.visible_self_interrogation_done
    ) and not (state.flowpilot_enabled and _startup_questions_complete(state)):
        return InvariantResult.fail("showcase/self-interrogation ran before the three-question startup gate")
    if state.flowpilot_enabled and not state.run_scoped_startup_bootstrap_created:
        return InvariantResult.fail("new capability startup did not create a run-scoped bootstrap")
    if (
        state.startup_runtime_role_assistance_option_recorded
        and state.startup_continuation_option_recorded
        and state.startup_display_surface_option_recorded
    ) and not (
        state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    ):
        return InvariantResult.fail("startup answers were recorded without legal values and explicit_user_reply provenance")
    if state.stale_top_level_bootstrap_reused:
        return InvariantResult.fail("stale top-level bootstrap was reused as current capability startup state")
    if state.old_control_state_reused_as_current:
        return InvariantResult.fail("old FlowPilot control state was reused as the current capability run state")
    if (state.contract_frozen or state.meta_route_checked or state.work_beyond_startup_allowed) and not _run_isolation_ready(state):
        return InvariantResult.fail("capability routing advanced before a fresh current run directory and control-state boundary were established")
    if (state.contract_frozen or state.meta_route_checked or state.work_beyond_startup_allowed) and not state.startup_display_entry_action_done:
        return InvariantResult.fail("capability routing advanced before resolving the user's startup display surface answer")
    if (state.contract_frozen or state.meta_route_checked or state.work_beyond_startup_allowed) and not state.preflow_visible_plan_cleared:
        return InvariantResult.fail("capability routing advanced before clearing the ordinary pre-FlowPilot visible plan")
    if state.contract_frozen and not _root_self_interrogation_gate_ready(state):
        return InvariantResult.fail(
            "contract was frozen before startup and product-architecture self-interrogation findings were durably dispositioned"
        )
    return InvariantResult.pass_()


def implementation_requires_flowguard_gates(state: State, trace) -> InvariantResult:
    del trace
    if state.non_ui_implemented or state.ui_implemented:
        if not _gates_lifecycle_valid(state):
            return InvariantResult.fail("implementation started before capability route was ready")
        if not (
            state.heartbeat_loaded_state
            and state.heartbeat_loaded_frontier
            and state.heartbeat_loaded_packet_ledger
            and state.heartbeat_loaded_role_binding_memory
            and state.heartbeat_host_rehydrate_requested
            and state.heartbeat_restored_crew
            and state.heartbeat_rehydrated_crew
            and state.heartbeat_injected_current_run_memory_into_roles
            and state.role_binding_recovery_report_written
            and state.replacement_roles_seeded_from_memory
            and state.heartbeat_pm_decision_requested
            and state.heartbeat_pm_controller_reminder_checked
            and state.heartbeat_reviewer_dispatch_policy_checked
            and state.pm_resume_decision_recorded
            and state.pm_completion_runway_recorded
            and state.pm_runway_hard_stops_recorded
            and state.pm_runway_checkpoint_cadence_recorded
            and state.pm_runway_synced_to_plan
            and state.plan_sync_method_recorded
            and state.visible_plan_has_runway_depth
            and state.pm_capability_work_decision_recorded
            and state.current_node_high_standard_recheck_written
            and state.node_acceptance_plan_written
            and state.node_acceptance_risk_experiments_mapped
            and state.pm_review_hold_instruction_written
            and state.child_skill_node_gate_manifest_refined
            and state.child_skill_gate_authority_records_written
        ):
            return InvariantResult.fail(
                "implementation started before continuation loaded packet ledger, rehydrated roles, checked PM controller reminder/router direct-dispatch policy, synced the PM runway, wrote node acceptance plan/risk experiments, and wrote node-level child-skill gate authority records"
            )
        if not _node_self_interrogation_gate_ready(state):
            return InvariantResult.fail(
                "implementation started before current-node self-interrogation findings were durably dispositioned"
            )
        if not (
            state.quality_package_done
            and state.quality_candidate_registry_checked
            and state.quality_raise_decision_recorded
            and state.validation_matrix_defined
        ):
            return InvariantResult.fail(
                "implementation started before quality package recorded thinness, raise decision, child-skill mini-route visibility, and validation matrix"
            )
    return InvariantResult.pass_()


def controlled_stop_notice_required(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "blocked" and not state.controlled_stop_notice_recorded:
        return InvariantResult.fail(
            "controlled nonterminal capability stop reached blocked state without a resume notice"
        )
    if state.status == "blocked" and not state.pause_snapshot_written:
        return InvariantResult.fail(
            "controlled nonterminal capability stop reached blocked state without a pause snapshot"
        )
    if state.status == "complete" and not state.terminal_completion_notice_recorded:
        return InvariantResult.fail(
            "terminal capability completion reached complete state without a completion notice"
        )
    if state.controlled_stop_notice_recorded and state.status == "complete":
        return InvariantResult.fail(
            "nonterminal resume notice was recorded on a completed capability route"
        )
    return InvariantResult.pass_()


def dependency_plan_before_route_or_implementation(
    state: State, trace
) -> InvariantResult:
    del trace
    route_or_work_started = (
        state.meta_route_checked
        or state.capability_route_checked
        or state.capability_evidence_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.capability_user_flow_diagram_emitted
        or state.current_node_high_standard_recheck_written
        or state.node_acceptance_plan_written
        or state.node_acceptance_risk_experiments_mapped
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.completion_visible_user_flow_diagram_emitted
        or state.final_feature_matrix_review_done
        or state.final_acceptance_matrix_review_done
        or state.final_standard_scenario_pack_replayed
        or state.final_quality_candidate_review_done
        or state.terminal_closure_suite_run
        or state.status == "complete"
    )
    work_beyond_startup_started = (
        state.current_node_high_standard_recheck_written
        or state.node_acceptance_plan_written
        or state.node_acceptance_risk_experiments_mapped
        or state.child_skill_node_gate_manifest_refined
        or state.child_skill_gate_authority_records_written
        or state.child_node_sidecar_scan_done
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.completion_visible_user_flow_diagram_emitted
        or state.status == "complete"
    )
    if route_or_work_started and not (
        _crew_ready(state)
        and _run_isolation_ready(state)
        and state.pm_initial_capability_decision_recorded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.dependency_plan_recorded and state.future_installs_deferred
        and _continuation_lifecycle_valid(state)
        and state.flowguard_process_design_done
    ):
        return InvariantResult.fail(
            "capability route or implementation started before runtime role-binding authority, fresh run isolation, PM capability decision, product-function architecture, frozen contract, dependency plan, host continuation decision, and FlowGuard process design"
        )
    if work_beyond_startup_started and not state.work_beyond_startup_allowed:
        return InvariantResult.fail(
            "capability work beyond startup started before PM allowed work from a factual reviewer report"
        )
    if state.startup_preflight_review_report_written and not state.startup_reviewer_fact_evidence_checked:
        return InvariantResult.fail(
            "capability startup reviewer report was written without independent fact evidence checks"
        )
    if state.startup_preflight_review_report_written and not (
        state.startup_reviewer_checked_run_isolation
        and state.startup_reviewer_checked_prior_work_boundary
    ):
        return InvariantResult.fail(
            "capability startup reviewer report was written without checking current run isolation and prior-work import boundary"
        )
    if (
        state.startup_preflight_review_report_written
        and state.runtime_role_bindings_opened
        and not (
            state.startup_reviewer_checked_live_agent_freshness
            and state.startup_reviewer_checked_no_historical_agent_reuse
        )
    ):
        return InvariantResult.fail(
            "capability startup reviewer report counted live role bindings without checking current-task freshness and historical id reuse"
        )
    if state.pm_start_gate_opened and not (
        state.startup_preflight_review_report_written
        and not state.startup_preflight_review_blocking_findings
        and state.startup_reviewer_fact_evidence_checked
        and _run_isolation_ready(state)
        and state.startup_reviewer_checked_run_isolation
        and state.startup_reviewer_checked_prior_work_boundary
        and (
            state.single_agent_role_continuity_authorized
            or (
                state.startup_reviewer_checked_live_agent_freshness
                and state.startup_reviewer_checked_no_historical_agent_reuse
            )
        )
        and state.startup_reviewer_checked_capability_resolution
        and (
            state.manual_resume_mode_recorded
            or (
                state.startup_reviewer_checked_current_run_heartbeat_binding
                and state.heartbeat_bound_to_current_run
                and not state.heartbeat_same_name_only_checked
            )
        )
        and state.startup_pm_independent_gate_audit_done
        and state.startup_pm_capability_resolution_recorded
    ):
        return InvariantResult.fail(
            "PM start gate opened before a clean factual reviewer startup report and independent PM gate audit"
        )
    if state.pm_start_gate_opened and state.pm_returned_startup_blockers:
        return InvariantResult.fail(
            "PM start gate opened while startup blockers were still assigned for worker remediation"
        )
    if (
        state.startup_worker_remediation_completed
        and state.pm_start_gate_opened
        and not (
            state.startup_preflight_review_report_written
            and not state.startup_preflight_review_blocking_findings
            and state.startup_reviewer_fact_evidence_checked
        )
    ):
        return InvariantResult.fail(
            "startup worker remediation was not rechecked by reviewer before PM gate opening"
        )
    if state.work_beyond_startup_allowed and not _startup_questions_complete(state):
        return InvariantResult.fail(
            "PM allowed capability work before the three startup answers were recorded"
        )
    if state.work_beyond_startup_allowed and not _run_isolation_ready(state):
        return InvariantResult.fail(
            "PM allowed capability work before fresh run isolation and prior-work boundary were resolved"
        )
    if state.work_beyond_startup_allowed and not _runtime_role_binding_startup_resolved(state):
        return InvariantResult.fail(
            "PM allowed capability work before fresh current-task role bindings or explicit single-agent fallback were resolved"
        )
    if state.work_beyond_startup_allowed and state.reused_historical_agent_ids:
        return InvariantResult.fail(
            "PM allowed capability work while role-binding evidence reused historical agent ids"
        )
    if state.work_beyond_startup_allowed and not _startup_pm_gate_ready(state):
        return InvariantResult.fail(
            "capability work was allowed before reviewer fact report and PM-owned start-gate opening"
        )
    if state.heartbeat_schedule_created and (
        not state.heartbeat_bound_to_current_run or state.heartbeat_same_name_only_checked
    ):
        return InvariantResult.fail(
            "startup heartbeat evidence did not bind the automation to the current run instead of a same-name record"
        )
    return InvariantResult.pass_()


def child_skill_fidelity_before_capability_work(
    state: State, trace
) -> InvariantResult:
    del trace
    dependent_work_started = (
        state.flowguard_dependency_checked
        or state.dependency_plan_recorded
        or state.flowguard_process_design_done
        or state.meta_route_checked
        or state.capability_route_checked
        or state.capability_evidence_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.capability_user_flow_diagram_emitted
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.completion_visible_user_flow_diagram_emitted
        or state.completion_self_interrogation_done
        or state.high_value_work_review == "exhausted"
        or state.status == "complete"
    )
    if dependent_work_started and not (
        state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and _focused_interrogation_ready(
            total_questions=state.child_skill_focused_interrogation_questions,
            scope_id=state.child_skill_focused_interrogation_scope_id,
        )
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.strict_gate_obligation_review_model_checked
    ):
        return InvariantResult.fail(
            "capability work started before PM-owned child-skill gate manifest extraction, approver assignment, reviewer/officer/PM approvals, focused child-skill self-interrogation, exact source, substitute rejection, original standard extraction, standard promotion into node contract, evidence-obligation binding, invocation policy, requirement mapping, evidence plan, visible child-skill mini-route, conformance model, and strict gate-obligation review model"
        )
    node_child_skill_work_started = (
        state.child_node_sidecar_scan_done
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.child_skill_execution_evidence_audited
        or state.final_verification_done
        or state.completion_visible_user_flow_diagram_emitted
        or state.status == "complete"
    )
    if node_child_skill_work_started and not (
        state.child_skill_node_gate_manifest_refined
        and state.child_skill_gate_authority_records_written
    ):
        return InvariantResult.fail(
            "node child-skill work started before PM node-level gate-manifest refinement and execution-frontier authority records"
        )
    completion_closure_started = (
        state.completion_visible_user_flow_diagram_emitted
        or state.completion_self_interrogation_done
        or state.high_value_work_review == "exhausted"
        or state.status == "complete"
    )
    if completion_closure_started and not state.child_skill_completion_verified:
        return InvariantResult.fail(
            "completion closure started before child skill completion standards were verified"
        )
    if completion_closure_started and not state.anti_rough_finish_done:
        return InvariantResult.fail(
            "completion closure started before anti-rough-finish review"
        )
    if completion_closure_started and not (
        state.implementation_human_review_context_loaded
        and state.implementation_human_neutral_observation_written
        and state.implementation_human_manual_experiments_run
        and state.implementation_human_inspection_passed
    ):
        return InvariantResult.fail(
            "completion closure started before human-like implementation inspection with neutral observation"
        )
    if completion_closure_started and not (
        state.capability_backward_context_loaded
        and state.capability_child_evidence_replayed
        and state.capability_backward_neutral_observation_written
        and state.capability_structure_decision_recorded
        and state.capability_backward_human_review_passed
        and state.capability_backward_pm_segment_decision_recorded
    ):
        return InvariantResult.fail(
            "completion closure started before capability backward composite review with neutral observation and PM segment decision"
        )
    if state.child_skill_completion_verified and not (
        state.child_skill_manifest_only_evidence_rejected
        and state.child_skill_execution_reports_written
        and state.child_skill_gate_evidence_obligations_bound
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_original_standards_extracted
        and
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
        and state.child_skill_current_gates_role_approved
    ):
        return InvariantResult.fail(
            "child skill completion verified before original skill standards were promoted, manifest-only evidence was rejected, execution reports were written, evidence audit, output match, domain quality, iteration closure, and required role approvals for current child-skill gates"
        )
    if state.final_verification_done and not (
        state.child_skill_manifest_only_evidence_rejected
        and state.child_skill_execution_reports_written
        and state.child_skill_gate_evidence_obligations_bound
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_original_standards_extracted
        and
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "final verification started before child-skill standard inheritance, execution reports, manifest-only evidence rejection, evidence audit, output match, domain quality, and iteration closure"
        )
    if state.final_verification_done and not state.validation_matrix_defined:
        return InvariantResult.fail("final verification started before validation matrix")
    return InvariantResult.pass_()


def active_child_skill_binding_required_for_execution(
    state: State, trace
) -> InvariantResult:
    del trace
    node_execution_binding_needed = (
        state.node_acceptance_risk_experiments_mapped
        or state.child_skill_node_gate_manifest_refined
        or state.child_skill_gate_authority_records_written
        or state.child_node_sidecar_scan_done
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.final_verification_done
        or state.child_skill_completion_verified
        or state.status == "complete"
    )
    if node_execution_binding_needed and not state.active_child_skill_bindings_written:
        return InvariantResult.fail(
            "active child-skill bindings were missing before current-node execution"
        )
    if node_execution_binding_needed and not state.active_child_skill_binding_scope_limited:
        return InvariantResult.fail(
            "active child-skill binding was not limited to the current-node child-skill slice"
        )
    if node_execution_binding_needed and not state.child_skill_stricter_standard_precedence_bound:
        return InvariantResult.fail(
            "stricter child-skill standard precedence was not bound above the PM packet floor"
        )

    worker_packet_needed = (
        state.child_node_sidecar_scan_done
        or state.quality_package_done
        or state.non_ui_implemented
        or state.ui_implemented
        or state.worker_output_ready_for_review
        or state.final_verification_done
        or state.child_skill_completion_verified
        or state.status == "complete"
    )
    if worker_packet_needed and not state.worker_packet_child_skill_use_instruction_written:
        return InvariantResult.fail(
            "worker packet lacked a direct child-skill use instruction"
        )
    if worker_packet_needed and not state.active_child_skill_source_paths_allowed:
        return InvariantResult.fail(
            "worker packet lacked allowed source paths for active child-skill SKILL.md and references"
        )

    worker_result_needs_use_evidence = (
        state.child_skill_manifest_only_evidence_rejected
        or state.child_skill_execution_reports_written
        or state.child_skill_execution_evidence_audited
        or state.worker_output_ready_for_review
        or state.final_verification_done
        or state.child_skill_completion_verified
        or state.status == "complete"
    )
    if worker_result_needs_use_evidence and not state.worker_child_skill_use_evidence_returned:
        return InvariantResult.fail(
            "worker result lacked Child Skill Use Evidence for active bindings"
        )

    reviewer_content_started = (
        state.implementation_human_review_context_loaded
        or state.implementation_human_neutral_observation_written
        or state.implementation_human_manual_experiments_run
        or state.implementation_reviewer_independent_probe_done
        or state.implementation_human_inspection_passed
        or state.child_skill_current_gates_role_approved
        or state.child_skill_completion_verified
        or state.status == "complete"
    )
    if reviewer_content_started and not state.reviewer_child_skill_use_evidence_checked:
        return InvariantResult.fail(
            "reviewer child-skill use evidence check was missing before approval"
        )
    return InvariantResult.pass_()


def ui_route_requires_ui_capabilities(state: State, trace) -> InvariantResult:
    del trace
    if state.task_kind != "ui":
        return InvariantResult.pass_()
    if (
        state.ui_inspected
        or state.ui_concept_done
        or state.ui_frontend_design_plan_done
        or state.ui_implemented
    ) and not state.ui_autonomous_pipeline_selected:
        return InvariantResult.fail(
            "UI work started before PM selected autonomous-concept-ui-redesign"
        )
    if state.ui_implemented and not (
        state.ui_autonomous_pipeline_selected
        and state.ui_inspected
        and state.ui_concept_done
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_frontend_design_plan_done
        and state.ui_frontend_design_execution_report_written
        and state.ui_iteration_budget_recorded
    ):
        return InvariantResult.fail(
            "UI implemented before inspect, concept target visibility, palette contract/default-or-override rationale, selected-concept binding, aesthetic review, frontend design report, and iteration budget gates"
        )
    if state.ui_frontend_design_plan_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_selected_concept_bound_to_review_packet
    ):
        return InvariantResult.fail(
            "frontend design planning started before concept aesthetic verdict, selected-concept binding, palette contract, default-or-override rationale, and reasons"
        )
    if state.ui_concept_aesthetic_review_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "concept aesthetic review completed without palette contract, default-or-override rationale, selected-concept binding, reviewer personal visual review, recommendations, and concrete reasons"
        )
    if state.ui_palette_default_or_override_rationale_recorded and not state.ui_palette_contract_written:
        return InvariantResult.fail(
            "UI palette/default-or-override rationale was recorded before the source skill palette contract"
        )
    if state.ui_implemented and state.visual_asset_scope == "unknown":
        return InvariantResult.fail("UI implemented before visual asset scope decision")
    if state.ui_implemented and state.visual_asset_scope == "required":
        if not (
            state.visual_asset_style_review_done
            and state.visual_asset_personal_visual_review_done
            and state.visual_asset_design_recommendations_recorded
            and state.visual_asset_aesthetic_review_done
            and state.visual_asset_aesthetic_reasons_recorded
        ):
            return InvariantResult.fail(
                "UI implemented before required visual asset personal review, design recommendations, and aesthetic review"
            )
    if state.visual_asset_style_review_done and not (
        state.ui_inspected
        and state.ui_concept_done
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_frontend_design_plan_done
        and state.ui_frontend_design_execution_report_written
    ):
        return InvariantResult.fail("visual asset style review ran before UI style and concept aesthetic gates")
    if state.visual_asset_aesthetic_review_done and not (
        state.visual_asset_scope == "required"
        and state.visual_asset_style_review_done
        and state.visual_asset_personal_visual_review_done
        and state.visual_asset_design_recommendations_recorded
        and state.visual_asset_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "visual asset aesthetic review completed without required scope, personal review, recommendations, style review, and reasons"
        )
    if state.ui_screenshot_qa_done and not (
        state.ui_concept_target_ready and state.ui_concept_target_visible
    ):
        return InvariantResult.fail("rendered QA ran before the source UI skill's pre-implementation decision was ready and visible or waived")
    if state.ui_geometry_qa_done and not (
        state.ui_implemented and state.ui_screenshot_qa_done
    ):
        return InvariantResult.fail(
            "geometry QA ran before UI implementation and screenshot QA evidence"
        )
    if state.ui_interaction_reachability_checked and not (
        state.ui_reviewer_personal_walkthrough_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
    ):
        return InvariantResult.fail(
            "interaction reachability passed before every visible affordance had a complete tested interaction matrix"
        )
    if state.ui_implementation_aesthetic_review_done and not (
        state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "rendered UI aesthetic review completed without reviewer personal walkthrough, complete visible-affordance interaction matrix, reachability, layout/density checks, recommendations, screenshot QA, and concrete reasons"
        )
    if state.ui_divergence_review_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_concept_vs_implementation_deviation_table_written
    ):
        return InvariantResult.fail(
            "UI child-skill comparison reviewed before selected concept binding, palette rationale, pre-implementation UI evidence, rendered QA, complete interaction matrix, aesthetic verdict, and concept-vs-implementation deviation table"
        )
    if state.ui_visual_iteration_loop_closed and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_frontend_design_execution_report_written
        and state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_concept_vs_implementation_deviation_table_written
        and state.ui_divergence_review_done
        and state.ui_iteration_budget_recorded
        and DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS
        <= state.ui_iteration_rounds_required
        <= MAX_UI_CHILD_SKILL_ITERATION_ROUNDS
        and state.ui_iteration_rounds_completed >= state.ui_iteration_rounds_required
        and state.ui_major_visual_deviation_triaged
        and state.ui_structural_redesign_route_considered
    ):
        return InvariantResult.fail(
            "UI child-skill loop closed before source skill standards, palette rationale, selected concept binding, frontend-design execution report, complete interaction matrix, deviation table, required iteration budget, major-deviation triage, structural redesign consideration, rendered QA, aesthetic verdict, and comparison evidence"
        )
    if state.final_verification_done and not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail("final verification ran before child-skill conformance audit and quality loop closure")
    if state.final_verification_done and state.task_kind == "ui" and not (
        state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_frontend_design_execution_report_written
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_concept_vs_implementation_deviation_table_written
        and state.ui_divergence_review_done
        and state.ui_iteration_budget_recorded
        and DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS
        <= state.ui_iteration_rounds_required
        <= MAX_UI_CHILD_SKILL_ITERATION_ROUNDS
        and state.ui_iteration_rounds_completed >= state.ui_iteration_rounds_required
        and state.ui_major_visual_deviation_triaged
        and state.ui_structural_redesign_route_considered
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI final verification before palette/selected-concept/frontend report, complete interaction matrix, deviation table, required iteration budget, major-deviation triage, structural redesign consideration, aesthetic/screenshot/divergence/iteration-loop gates")
    if state.final_verification_done and state.visual_asset_scope == "required":
        if not (
            state.visual_asset_style_review_done
            and state.visual_asset_personal_visual_review_done
            and state.visual_asset_design_recommendations_recorded
            and state.visual_asset_aesthetic_review_done
            and state.visual_asset_aesthetic_reasons_recorded
        ):
            return InvariantResult.fail(
                "UI final verification before required visual asset personal review, recommendations, and aesthetic review"
            )
    return InvariantResult.pass_()


def capability_route_updates_force_recheck_and_resync(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.capability_user_flow_diagram_emitted and not state.capability_user_flow_diagram_refreshed:
        return InvariantResult.fail(
            "capability user flow diagram emitted before refreshing the current user flow diagram"
        )
    if state.capability_structural_route_repairs > state.pm_repair_decision_interrogations:
        return InvariantResult.fail(
            "capability structural route repair written before PM repair strategy interrogation"
        )
    if state.non_ui_implemented or state.ui_implemented or state.final_verification_done:
        if not (
            state.capability_route_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and state.capability_user_flow_diagram_emitted
        ):
            return InvariantResult.fail(
                "capability route update was not checked, product-modeled, evidence-synced, frontier-synced, plan-synced, and visibly mapped before work"
            )
    return InvariantResult.pass_()


def stable_heartbeat_prompt_not_capability_route_state(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.capability_route_version > 1
        and state.host_continuation_supported
        and not state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail(
            "capability route changed without a stable heartbeat launcher that reads persisted state"
        )
    if (
        state.capability_route_version > 1
        and state.manual_resume_mode_recorded
        and state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail(
            "manual-resume capability route unexpectedly created a stable heartbeat launcher"
        )
    return InvariantResult.pass_()


def startup_continuation_gates_work_beyond_startup(state: State, trace) -> InvariantResult:
    del trace
    if state.terminal_router_daemon_stopped:
        if (
            state.router_daemon_started
            or state.router_daemon_lock_acquired
            or state.controller_action_watch_active
        ):
            return InvariantResult.fail("terminal Router daemon stop left daemon, lock, or Controller watch active")
        return InvariantResult.pass_()
    if state.controller_core_loaded and not state.terminal_router_daemon_stopped and not (
        state.router_daemon_started
        and state.router_daemon_lock_acquired
        and state.router_daemon_tick_seconds == 1
        and state.router_daemon_status_written
        and state.controller_action_ledger_initialized
        and state.controller_action_watch_active
    ):
        return InvariantResult.fail(
            "Controller core loaded before persistent Router daemon and Controller action ledger were ready"
        )
    if state.router_daemon_started and state.router_daemon_tick_seconds != 1:
        return InvariantResult.fail("persistent Router daemon did not use a fixed one-second tick")
    startup_or_capability_work_started = (
        state.startup_preflight_review_report_written
        or state.pm_start_gate_opened
        or state.work_beyond_startup_allowed
        or state.meta_route_checked
        or state.capability_route_checked
        or state.non_ui_implemented
        or state.ui_implemented
        or state.status == "complete"
    )
    if startup_or_capability_work_started and not _continuation_ready(state):
        return InvariantResult.fail(
            "startup review or capability work started before continuation was bound to heartbeat or manual resume"
        )
    if startup_or_capability_work_started and state.host_continuation_supported and not _automated_continuation_configured(state):
        return InvariantResult.fail(
            "startup review or capability work started before scheduled-continuation heartbeat was fully configured"
        )
    if startup_or_capability_work_started and state.manual_resume_mode_recorded and state.heartbeat_schedule_created:
        return InvariantResult.fail(
            "startup review or capability work started after manual-resume startup that still created heartbeat automation"
        )
    return InvariantResult.pass_()


def heartbeat_continuation_is_lifecycle_state(state: State, trace) -> InvariantResult:
    del trace
    automation_bits = (
        state.heartbeat_schedule_created
        or state.route_heartbeat_interval_minutes != 0
        or state.stable_heartbeat_launcher_recorded
    )
    if state.manual_resume_mode_recorded and automation_bits:
        return InvariantResult.fail(
            "manual-resume mode recorded but heartbeat automation state was still created"
        )
    formal_started = (
        state.capability_route_checked
        or state.non_ui_implemented
        or state.ui_implemented
        or state.status == "complete"
    )
    if formal_started and state.host_continuation_supported and (
        state.heartbeat_schedule_created
        or state.route_heartbeat_interval_minutes != 0
    ) and not _continuation_lifecycle_valid(state):
        return InvariantResult.fail(
            "host continuation support produced a partial heartbeat setup"
        )
    if state.host_continuation_supported and state.heartbeat_schedule_created and (
        state.route_heartbeat_interval_minutes != 1
        or not state.stable_heartbeat_launcher_recorded
        or not state.heartbeat_bound_to_current_run
        or state.heartbeat_same_name_only_checked
    ):
        return InvariantResult.fail(
            "automated continuation must use a stable one-minute heartbeat launcher bound to the current run"
        )
    return InvariantResult.pass_()


def backend_route_does_not_run_ui_gates(state: State, trace) -> InvariantResult:
    del trace
    if state.task_kind != "backend":
        return InvariantResult.pass_()
    if (
        state.ui_inspected
        or state.ui_concept_done
        or state.ui_concept_target_ready
        or state.ui_concept_target_visible
        or state.ui_palette_contract_written
        or state.ui_palette_default_or_override_rationale_recorded
        or state.ui_selected_concept_bound_to_review_packet
        or state.ui_frontend_design_plan_done
        or state.ui_frontend_design_execution_report_written
        or state.visual_asset_scope == "required"
        or state.visual_asset_style_review_done
        or state.ui_implemented
        or state.ui_screenshot_qa_done
        or state.ui_visible_affordance_interaction_matrix_written
        or state.ui_visible_affordance_interaction_matrix_complete
        or state.ui_concept_vs_implementation_deviation_table_written
        or state.ui_divergence_review_done
        or state.ui_iteration_budget_recorded
        or state.ui_iteration_rounds_required > 0
        or state.ui_iteration_rounds_completed > 0
        or state.ui_major_visual_deviation_triaged
        or state.ui_structural_redesign_route_considered
        or state.ui_visual_iteration_loop_closed
        or state.ui_visual_iterations > 0
    ):
        return InvariantResult.fail("backend route invoked UI-only gates")
    return InvariantResult.pass_()


def sidecar_role_result_must_merge_before_implementation_or_completion(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.sidecar_role_status in {"pending", "returned"}:
        if state.non_ui_implemented or state.ui_implemented or state.status == "complete":
            return InvariantResult.fail(
                "implementation/completion proceeded before sidecar role merge"
            )
    if state.sidecar_role_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("sidecar role used before child-node sidecar scan")
    if state.sidecar_role_status == "pending" and not state.sidecar_role_scope_checked:
        return InvariantResult.fail("sidecar role binding assigned before disjoint scope check")
    if state.sidecar_role_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("sidecar role assigned without a bounded sidecar need")
    return InvariantResult.pass_()


def human_review_judgement_requires_neutral_observation(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.implementation_human_inspection_passed
        and not state.implementation_human_neutral_observation_written
    ):
        return InvariantResult.fail("implementation inspection passed without neutral observation")
    if (
        state.capability_backward_human_review_passed
        and not state.capability_backward_neutral_observation_written
    ):
        return InvariantResult.fail("capability backward review passed without neutral observation")
    if state.final_human_inspection_passed and not state.final_human_neutral_observation_written:
        return InvariantResult.fail("final inspection passed without neutral observation")
    return InvariantResult.pass_()


def pm_review_release_controls_reviewer_start(
    state: State, trace
) -> InvariantResult:
    del trace
    formal_package_identity_ready = state.pm_formal_gate_package_identity_recorded
    explicit_pm_release_ready = (
        state.pm_review_release_order_written
        and state.pm_released_reviewer_for_current_gate
    )
    disposition_pm_release_ready = (
        state.pm_package_result_disposition_recorded
        and state.pm_package_result_disposition_absorbed
        and state.pm_formal_gate_package_released
        and formal_package_identity_ready
    )
    reviewer_started_current_gate = (
        state.implementation_human_review_context_loaded
        or state.implementation_human_neutral_observation_written
        or state.implementation_human_manual_experiments_run
        or state.implementation_reviewer_independent_probe_done
        or state.implementation_human_inspection_passed
        or state.implementation_human_review_reviewer_approved
    )
    if reviewer_started_current_gate and not (
        state.pm_review_hold_instruction_written
        and state.worker_output_ready_for_review
        and (explicit_pm_release_ready or disposition_pm_release_ready)
        and state.packet_runtime_physical_files_written
        and state.controller_context_body_exclusion_verified
        and state.controller_relay_signature_audit_done
        and state.recipient_pre_open_relay_check_done
        and state.packet_mail_chain_audit_done
        and state.unopened_mail_pm_recovery_policy_recorded
        and state.packet_envelope_body_audit_done
        and state.packet_envelope_to_role_checked
        and state.packet_body_hash_verified
        and state.result_envelope_checked
        and state.result_body_hash_verified
        and state.completed_agent_id_role_verified
        and state.controller_body_boundary_verified
        and state.wrong_role_relabel_forbidden_verified
        and state.packet_role_origin_audit_done
        and state.packet_result_author_verified
        and state.packet_result_author_matches_assignment
    ):
        return InvariantResult.fail(
            "capability reviewer started current-gate review before PM release evidence, physical packet isolation, controller mail-chain audit, envelope/body audit, and per-packet role-origin audit"
        )
    if state.pm_review_release_order_written and not state.worker_output_ready_for_review:
        return InvariantResult.fail(
            "PM wrote a capability review release before worker output was ready"
        )
    if state.pm_package_result_disposition_absorbed and not state.pm_package_result_disposition_recorded:
        return InvariantResult.fail(
            "PM absorbed package-result disposition lacks a recorded disposition"
        )
    if state.pm_formal_gate_package_released and not (
        state.worker_output_ready_for_review
        and state.pm_package_result_disposition_recorded
        and state.pm_package_result_disposition_absorbed
        and formal_package_identity_ready
    ):
        return InvariantResult.fail(
            "PM formal gate package release lacks absorbed disposition, worker-output readiness, or package path/hash plus source packet/output-contract identity"
        )
    return InvariantResult.pass_()


def router_hard_rejection_requires_control_blocker_lane(state: State, trace) -> InvariantResult:
    del trace
    if not state.router_hard_rejection_seen:
        return InvariantResult.pass_()
    lanes = {"control_plane_reissue", "pm_repair_decision_required", "fatal_protocol_violation"}
    if not state.control_blocker_artifact_written:
        return InvariantResult.fail("router hard rejection did not write a run-scoped control blocker artifact")
    if not (state.blocker_repair_policy_snapshot_written and state.blocker_policy_row_attached):
        return InvariantResult.fail("router hard rejection did not attach a blocker repair policy row and run-visible policy snapshot")
    if state.control_blocker_handling_lane not in lanes:
        return InvariantResult.fail("router hard rejection lacked a valid control blocker handling lane")
    if (
        state.control_blocker_handling_lane == "control_plane_reissue"
        and not state.control_blocker_delivered_to_responsible_role
        and state.control_blocker_first_handler != "responsible_role"
    ):
        return InvariantResult.fail("control-plane reissue blocker was not routed back to the responsible role")
    if state.control_blocker_handling_lane in {"pm_repair_decision_required", "fatal_protocol_violation"} and not state.control_blocker_delivered_to_pm:
        return InvariantResult.fail("PM repair or fatal control blocker was not routed to Project Manager")
    if (
        state.control_blocker_first_handler == "responsible_role"
        and state.control_blocker_direct_retry_attempts >= state.control_blocker_direct_retry_budget
        and not (state.control_blocker_retry_budget_exhausted and state.control_blocker_escalated_to_pm)
    ):
        return InvariantResult.fail("exhausted direct blocker retries did not escalate to PM")
    if state.control_blocker_delivered_to_pm and not (
        state.pm_blocker_recovery_option_recorded
        and state.pm_blocker_return_gate_recorded
        and state.pm_blocker_silent_pass_forbidden
    ) and not (
        state.control_blocker_escalated_to_pm
        and not state.pm_blocker_return_gate_recorded
    ):
        return InvariantResult.fail("PM-handled blocker lacked recovery option, return gate, or silent-pass prohibition")
    return InvariantResult.pass_()


def final_completion_requires_right_verification(state: State, trace) -> InvariantResult:
    del trace
    if state.status != "complete":
        return InvariantResult.pass_()
    if not _gates_lifecycle_valid(state):
        return InvariantResult.fail("completed before showcase, heartbeat, and FlowGuard capability gates")
    if not (
        state.defect_ledger_initialized
        and state.evidence_ledger_initialized
        and state.generated_resource_ledger_initialized
        and state.activity_stream_initialized
        and state.activity_stream_latest_event_written
        and state.flowpilot_improvement_live_report_initialized
    ):
        return InvariantResult.fail(
            "completed before run-level defect, evidence, generated-resource, activity stream, and live FlowPilot improvement ledgers were initialized"
        )
    if not (
        _crew_ready(state)
        and state.pm_initial_capability_decision_recorded
        and state.pm_resume_decision_recorded
        and state.pm_capability_work_decision_recorded
        and state.role_binding_memory_archived
        and state.role_binding_ledger_archived
    ):
        return InvariantResult.fail(
            "completed before runtime role-binding authority, PM decisions, role memory archive, and terminal role archive"
        )
    if not state.final_verification_done:
        return InvariantResult.fail("completed before final verification")
    if not state.child_skill_completion_verified:
        return InvariantResult.fail("completed before child skill completion standards were verified")
    if not state.child_skill_current_gates_role_approved:
        return InvariantResult.fail(
            "completed before required roles approved the current child-skill gates"
        )
    if not _terminal_continuation_reconciled(state):
        return InvariantResult.fail(
            "completed before continuation lifecycle state was written back to execution frontier"
        )
    if not (
        state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.child_skill_manifest_only_evidence_rejected
        and state.child_skill_execution_reports_written
        and state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail("completed before child-skill standard inheritance, execution reports, manifest-only evidence rejection, conformance audit, and quality loop closure")
    if not (
        state.quality_package_done
        and state.quality_candidate_registry_checked
        and state.quality_raise_decision_recorded
        and state.validation_matrix_defined
        and state.anti_rough_finish_done
    ):
        return InvariantResult.fail("completed before quality package and anti-rough-finish review")
    if not (
        state.final_feature_matrix_review_done
        and state.final_acceptance_matrix_review_done
        and state.final_standard_scenario_pack_replayed
        and state.final_quality_candidate_review_done
        and state.final_product_function_model_replayed
        and state.final_human_review_context_loaded
        and state.final_human_neutral_observation_written
        and state.final_human_manual_experiments_run
        and state.final_human_inspection_passed
    ):
        return InvariantResult.fail(
            "completed before final feature, acceptance, quality-candidate, product-model replay, and human-like reviews"
        )
    if not _final_route_wide_gate_ledger_ready(state):
        return InvariantResult.fail(
            "completed before PM-built dynamic route-wide gate ledger, reviewer backward replay, and PM ledger approval"
        )
    if not (state.defect_ledger_zero_blocking and state.evidence_credibility_triage_done):
        return InvariantResult.fail(
            "completed before defect ledger zero-blocker check and evidence credibility triage"
        )
    if not (
        state.capability_product_function_model_checked
        and state.implementation_human_review_context_loaded
        and state.implementation_human_neutral_observation_written
        and state.implementation_human_manual_experiments_run
        and state.implementation_human_inspection_passed
        and state.capability_backward_context_loaded
        and state.capability_child_evidence_replayed
        and state.capability_backward_neutral_observation_written
        and state.capability_structure_decision_recorded
        and state.capability_backward_human_review_passed
        and state.capability_backward_pm_segment_decision_recorded
    ):
        return InvariantResult.fail(
            "completed before capability product-function model, implementation inspection, backward composite review, and PM segment decision"
        )
    if not (
        state.completion_self_interrogation_done
        and state.high_value_work_review == "exhausted"
    ):
        return InvariantResult.fail("completed before completion self-interrogation exhausted obvious high-value work")
    if not _self_interrogation_index_final_ready(state):
        return InvariantResult.fail(
            "completed before self-interrogation records were collected into a clean final index"
        )
    if not state.completion_visible_user_flow_diagram_emitted:
        return InvariantResult.fail("completed before visible completion user flow diagram")
    if not _full_interrogation_ready(
        total_questions=state.completion_self_interrogation_questions,
        layer_count=state.completion_self_interrogation_layer_count,
        questions_per_layer=state.completion_self_interrogation_questions_per_layer,
        risk_family_mask=state.completion_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "completed before completion self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    if not (
        state.terminal_closure_suite_run
        and state.terminal_state_and_evidence_refreshed
        and state.flowpilot_skill_improvement_report_written
    ):
        return InvariantResult.fail(
            "completed before terminal closure suite refreshed state, evidence, lifecycle, role memory, and the PM-owned nonblocking FlowPilot skill improvement report"
        )
    if state.task_kind == "backend" and not state.non_ui_implemented:
        return InvariantResult.fail("backend route completed before implementation")
    if state.task_kind == "ui" and not (
        state.ui_implemented
        and state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_palette_contract_written
        and state.ui_palette_default_or_override_rationale_recorded
        and state.ui_selected_concept_bound_to_review_packet
        and state.ui_frontend_design_execution_report_written
        and state.ui_screenshot_qa_done
        and state.ui_visible_affordance_interaction_matrix_written
        and state.ui_visible_affordance_interaction_matrix_complete
        and state.ui_concept_vs_implementation_deviation_table_written
        and state.ui_divergence_review_done
        and state.ui_iteration_budget_recorded
        and DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS
        <= state.ui_iteration_rounds_required
        <= MAX_UI_CHILD_SKILL_ITERATION_ROUNDS
        and state.ui_iteration_rounds_completed >= state.ui_iteration_rounds_required
        and state.ui_major_visual_deviation_triaged
        and state.ui_structural_redesign_route_considered
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI route completed before visual skill-standard verification gates")
    if state.task_kind == "ui" and state.visual_asset_scope == "required":
        if not state.visual_asset_style_review_done:
            return InvariantResult.fail(
                "UI route completed before required visual asset style review"
            )
    return InvariantResult.pass_()


def material_handoff_before_capability_route_design(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.material_intake_packet_written and not (
        state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
        and state.local_skill_inventory_written
        and state.local_skill_inventory_candidate_classified
    ):
        return InvariantResult.fail(
            "capability Material Intake Packet was written before sources and local skills were scanned, summarized, quality-classified, and candidate-classified"
        )
    if state.material_reviewer_sufficiency_approved and not (
        state.material_intake_packet_written
        and state.material_reviewer_sufficiency_checked
    ):
        return InvariantResult.fail(
            "capability material packet was approved before reviewer sufficiency check"
        )
    if state.pm_material_understanding_memo_written and not (
        state.material_reviewer_sufficiency_approved
    ):
        return InvariantResult.fail(
            "PM capability material understanding memo was written before reviewer-approved intake evidence"
        )
    if state.pm_material_discovery_decision_recorded and not (
        state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
    ):
        return InvariantResult.fail(
            "PM capability material discovery decision was recorded before understanding memo and complexity classification"
        )
    if state.pm_material_research_decision_recorded and not state.pm_material_discovery_decision_recorded:
        return InvariantResult.fail(
            "PM capability material research-package decision was recorded before the material discovery decision"
        )
    if (
        state.pm_material_research_decision_recorded
        and state.material_research_need not in {"not_required", "required"}
    ):
        return InvariantResult.fail(
            "PM capability material research-package decision did not classify need"
        )
    if state.pm_research_package_written and not (
        state.pm_material_research_decision_recorded
        and state.material_research_need == "required"
    ):
        return InvariantResult.fail(
            "PM capability research package was written without a recorded material gap requiring research"
        )
    if state.research_tool_capability_decision_recorded and not state.pm_research_package_written:
        return InvariantResult.fail(
            "capability research tool decision was recorded before the PM research package"
        )
    if state.research_worker_report_returned and not (
        state.pm_research_package_written
        and state.research_tool_capability_decision_recorded
    ):
        return InvariantResult.fail(
            "capability worker research report returned before PM package and tool capability decision"
        )
    if state.research_reviewer_direct_source_check_done and not state.research_worker_report_returned:
        return InvariantResult.fail(
            "capability research reviewer checked sources before a worker research report existed"
        )
    if state.research_reviewer_rework_required and not state.research_reviewer_direct_source_check_done:
        return InvariantResult.fail(
            "capability research reviewer required rework before direct source checks"
        )
    if state.research_worker_rework_completed and not state.research_reviewer_rework_required:
        return InvariantResult.fail(
            "capability research worker rework completed before reviewer requested rework"
        )
    if state.research_reviewer_recheck_done and not state.research_worker_rework_completed:
        return InvariantResult.fail(
            "capability research reviewer rechecked before worker completed research rework"
        )
    if state.research_reviewer_sufficiency_passed and not (
        state.research_reviewer_direct_source_check_done
        and (
            not state.research_reviewer_rework_required
            or (
                state.research_worker_rework_completed
                and state.research_reviewer_recheck_done
            )
        )
    ):
        return InvariantResult.fail(
            "capability research reviewer sufficiency passed without direct source check and required rework/recheck evidence"
        )
    if state.pm_research_result_absorbed_or_route_mutated and not state.research_reviewer_sufficiency_passed:
        return InvariantResult.fail(
            "PM absorbed or routed capability research result before reviewer sufficiency pass"
        )
    if (
        state.product_function_architecture_pm_synthesized
        and state.material_research_need == "required"
        and not state.pm_research_result_absorbed_or_route_mutated
    ):
        return InvariantResult.fail(
            "capability product-function architecture started while required material research package was unresolved"
        )
    if state.pm_initial_capability_decision_recorded and not _material_handoff_ready(state):
        return InvariantResult.fail(
            "PM capability route decision was recorded before reviewed material handoff"
        )
    if state.pm_child_skill_selection_manifest_written and not (
        _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.capabilities_manifest_written
    ):
        return InvariantResult.fail(
            "PM child-skill selection manifest was written before product architecture, frozen contract, and capabilities manifest were ready"
        )
    if state.pm_child_skill_selection_scope_decisions_recorded and not (
        state.pm_child_skill_selection_manifest_written
        and state.pm_child_skill_minimum_sufficient_complexity_review_written
        and state.product_function_capability_map_written
        and state.local_skill_inventory_candidate_classified
    ):
        return InvariantResult.fail(
            "PM child-skill selection decisions were recorded before the PM manifest, minimum sufficient complexity review, product capability map, and local skill candidate classification"
        )
    if state.child_skill_route_design_discovery_started and not (
        state.pm_child_skill_selection_manifest_written
        and state.pm_child_skill_selection_scope_decisions_recorded
    ):
        return InvariantResult.fail(
            "child-skill route discovery started from raw local skill availability instead of the PM selection manifest"
        )
    return InvariantResult.pass_()


def actor_authority_gates_require_correct_role(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.self_interrogation_pm_ratified and not _crew_ready(state):
        return InvariantResult.fail(
            "capability startup self-interrogation was ratified before runtime role-binding readiness"
        )
    any_role_approval = (
        state.self_interrogation_pm_ratified
        or state.material_reviewer_sufficiency_approved
        or state.product_function_architecture_product_officer_approved
        or state.product_function_architecture_reviewer_challenged
        or state.child_skill_manifest_reviewer_reviewed
        or state.child_skill_manifest_process_officer_approved
        or state.child_skill_manifest_product_officer_approved
        or state.child_skill_manifest_pm_approved_for_route
        or state.child_skill_conformance_model_process_officer_approved
        or state.meta_route_process_officer_approved
        or state.capability_route_process_officer_approved
        or state.capability_product_function_model_product_officer_approved
        or state.implementation_human_review_reviewer_approved
        or state.capability_backward_review_reviewer_approved
        or state.final_product_function_model_product_officer_approved
        or state.final_human_review_reviewer_approved
        or state.final_route_wide_gate_ledger_pm_completion_approved
        or state.pm_start_gate_opened
    )
    if any_role_approval and not state.independent_approval_protocol_recorded:
        return InvariantResult.fail(
            "role approval was recorded before the independent adversarial approval protocol existed"
        )
    if state.product_function_architecture_pm_synthesized and not (
        _crew_ready(state) and _material_handoff_ready(state)
    ):
        return InvariantResult.fail(
            "capability product-function architecture was synthesized before role binding recovery and reviewed material handoff"
        )
    product_architecture_inputs_ready = (
        state.product_function_architecture_pm_synthesized
        and state.product_function_high_standard_posture_written
        and state.product_function_target_and_failure_bar_written
        and state.product_function_minimum_sufficient_complexity_review_written
        and state.product_function_semantic_fidelity_policy_written
        and state.product_function_user_task_map_written
        and state.product_function_capability_map_written
        and state.product_function_feature_decisions_written
        and state.product_function_display_rationale_written
        and state.product_function_gap_review_done
        and state.product_function_negative_scope_written
        and state.product_function_acceptance_matrix_written
        and state.root_acceptance_thresholds_defined
        and state.root_acceptance_proof_matrix_written
        and state.standard_scenario_pack_selected
    )
    if state.material_reviewer_sufficiency_approved and not (
        state.material_reviewer_direct_source_probe_done
        and state.material_reviewer_sufficiency_checked
    ):
        return InvariantResult.fail(
            "capability material approval was recorded before reviewer direct source probes"
        )
    if state.product_function_architecture_product_officer_approved and not (
        product_architecture_inputs_ready
        and state.product_architecture_officer_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "capability product-function architecture approval was recorded before all PM product artifacts and officer adversarial probes existed"
        )
    if state.product_function_architecture_reviewer_challenged and not (
        state.product_function_architecture_product_officer_approved
        and state.product_architecture_reviewer_adversarial_probe_done
        and state.reviewer_ready
    ):
        return InvariantResult.fail(
            "capability product-function architecture reviewer challenge ran before product officer approval, reviewer recovery, or reviewer adversarial probes"
        )
    if state.node_acceptance_plan_written and not (
        state.current_node_high_standard_recheck_written
        and state.current_node_minimum_sufficient_complexity_review_written
    ):
        return InvariantResult.fail(
            "capability node acceptance plan was written before PM current-node high-standard and minimum sufficient complexity rechecks"
        )
    if state.flowguard_process_design_done and not (
        state.self_interrogation_pm_ratified
        and _product_function_architecture_ready(state)
        and state.contract_frozen
    ):
        return InvariantResult.fail(
            "capability FlowGuard process design started before PM startup ratification, product-function architecture, and contract freeze"
        )
    if state.child_skill_manifest_pm_approved_for_route and not (
        state.child_skill_route_design_discovery_started
        and state.pm_child_skill_selection_manifest_written
        and state.pm_child_skill_minimum_sufficient_complexity_review_written
        and state.pm_child_skill_selection_scope_decisions_recorded
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
    ):
        return InvariantResult.fail(
            "PM approved child-skill gate manifest before PM skill selection, minimum sufficient complexity review, discovery, extraction, approver assignment, and reviewer approval"
        )
    if state.child_skill_manifest_reviewer_reviewed and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
    ):
        return InvariantResult.fail(
            "human-like reviewer reviewed child-skill gates before manifest extraction and approver assignment"
        )
    if state.child_skill_gate_authority_records_written and not (
        state.child_skill_node_gate_manifest_refined
        and state.child_skill_manifest_pm_approved_for_route
        and state.current_node_high_standard_recheck_written
        and state.node_acceptance_plan_written
        and state.node_acceptance_risk_experiments_mapped
    ):
        return InvariantResult.fail(
            "current child-skill gate authority records were written before PM-approved route manifest, current-node high-standard recheck, node acceptance plan, risk experiment mapping, and node-level refinement"
        )
    if state.child_skill_current_gates_role_approved and not (
        state.child_skill_gate_authority_records_written
        and state.current_child_skill_gate_independent_validation_done
        and state.child_skill_original_standards_extracted
        and state.child_skill_standards_promoted_to_node_contract
        and state.child_skill_gate_evidence_obligations_bound
        and state.child_skill_manifest_only_evidence_rejected
        and state.child_skill_execution_reports_written
        and state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "current child-skill gates were role-approved before authority records, original standard inheritance, non-manifest evidence obligations, execution reports, evidence audit, output match, domain quality, and loop closure"
        )
    if (
        state.child_skill_conformance_model_process_officer_approved
        and not state.child_skill_conformance_model_checked
    ):
        return InvariantResult.fail(
            "child-skill conformance approval is stale without conformance model check"
        )
    if (
        state.child_skill_conformance_model_checked
        and not state.child_skill_conformance_model_process_officer_approved
    ):
        return InvariantResult.fail(
            "child-skill conformance model lacks process FlowGuard officer approval"
        )
    if state.meta_route_process_officer_approved and not (
        state.meta_route_checked and state.flowguard_officer_model_adversarial_probe_done
    ):
        return InvariantResult.fail("meta-route approval is stale without meta-route check")
    if (
        state.meta_route_process_officer_approved
        or state.capability_route_process_officer_approved
        or state.capability_product_function_model_product_officer_approved
    ) and not (
        state.flowguard_model_report_risk_tiers_done
        and state.flowguard_model_report_pm_review_agenda_done
        and state.flowguard_model_report_toolchain_recommendations_done
        and state.flowguard_model_report_confidence_boundary_done
    ):
        return InvariantResult.fail(
            "FlowGuard capability model approval was recorded before the report extracted PM risk tiers, review agenda, toolchain recommendations, and confidence boundary"
        )
    if state.meta_route_checked and not state.meta_route_process_officer_approved:
        return InvariantResult.fail("meta-route check lacks process FlowGuard officer approval")
    if state.capability_route_process_officer_approved and not (
        state.capability_route_checked
        and state.flowguard_officer_model_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "capability-route approval is stale without capability-route check"
        )
    if state.capability_route_checked and not state.capability_route_process_officer_approved:
        return InvariantResult.fail(
            "capability-route check lacks process FlowGuard officer approval"
        )
    if (
        state.capability_product_function_model_product_officer_approved
        and not (
            state.capability_product_function_model_checked
            and state.flowguard_officer_model_adversarial_probe_done
        )
    ):
        return InvariantResult.fail(
            "capability product-function approval is stale without product-function model check"
        )
    if (
        state.capability_product_function_model_checked
        and not state.capability_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "capability product-function model lacks product FlowGuard officer approval"
        )
    if (
        state.implementation_human_review_reviewer_approved
        and not (
            state.implementation_human_inspection_passed
            and state.implementation_reviewer_independent_probe_done
        )
    ):
        return InvariantResult.fail(
            "implementation reviewer approval is stale without implementation human review pass"
        )
    if (
        state.implementation_human_inspection_passed
        and not state.implementation_human_review_reviewer_approved
    ):
        return InvariantResult.fail("implementation human review pass lacks reviewer approval")
    if (
        state.capability_backward_review_reviewer_approved
        and not (
            state.capability_backward_human_review_passed
            and state.capability_backward_reviewer_independent_probe_done
        )
    ):
        return InvariantResult.fail(
            "capability backward reviewer approval is stale without backward review pass"
        )
    if (
        state.capability_backward_human_review_passed
        and not state.capability_backward_review_reviewer_approved
    ):
        return InvariantResult.fail("capability backward review pass lacks reviewer approval")
    if (
        state.final_product_function_model_product_officer_approved
        and not (
            state.final_product_function_model_replayed
            and state.final_product_model_officer_adversarial_probe_done
        )
    ):
        return InvariantResult.fail(
            "final product replay approval is stale without final product replay"
        )
    if (
        state.final_product_function_model_replayed
        and not state.final_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "final product replay lacks product FlowGuard officer approval"
        )
    if state.final_human_review_reviewer_approved and not (
        state.final_human_inspection_passed
        and state.final_human_reviewer_independent_probe_done
    ):
        return InvariantResult.fail("final reviewer approval is stale without final human review pass")
    if state.final_human_inspection_passed and not state.final_human_review_reviewer_approved:
        return InvariantResult.fail("final human review pass lacks reviewer approval")
    if state.final_route_wide_gate_ledger_pm_built and not (
        state.final_route_wide_gate_ledger_current_route_scanned
        and state.final_route_wide_gate_ledger_effective_nodes_resolved
        and state.final_route_wide_gate_ledger_child_skill_gates_collected
        and state.final_route_wide_gate_ledger_human_review_gates_collected
        and state.final_route_wide_gate_ledger_parent_backward_replays_collected
        and state.final_route_wide_gate_ledger_product_process_gates_collected
        and state.final_route_wide_gate_ledger_resource_lineage_resolved
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_self_interrogation_collected
        and state.self_interrogation_index_clean
        and state.final_residual_risk_triage_done
        and state.final_residual_risk_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM built final route-wide capability gate ledger before current route scan, gate collection, generated-resource lineage, stale-evidence check, superseded explanations, clean self-interrogation index, zero unresolved count, and zero unresolved residual risks"
        )
    if state.final_route_wide_gate_ledger_reviewer_backward_checked and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.terminal_human_backward_review_map_built
        and state.terminal_human_backward_replay_started_from_delivered_product
        and state.terminal_human_backward_root_acceptance_reviewed
        and state.terminal_human_backward_parent_nodes_reviewed
        and state.terminal_human_backward_leaf_nodes_reviewed
        and state.terminal_human_backward_pm_segment_decisions_recorded
        and state.terminal_human_backward_repair_restart_policy_recorded
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_self_interrogation_collected
        and state.self_interrogation_index_clean
        and state.final_residual_risk_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "final route-wide capability ledger reviewer replay ran before PM-built clean ledger and terminal human backward review map, delivered-output replay, node-by-node checks, PM segment decisions, and repair restart policy"
        )
    if state.final_route_wide_gate_ledger_pm_completion_approved and not (
        state.final_route_wide_gate_ledger_pm_built
        and state.terminal_human_backward_review_map_built
        and state.terminal_human_backward_pm_segment_decisions_recorded
        and state.terminal_human_backward_repair_restart_policy_recorded
        and state.final_route_wide_gate_ledger_reviewer_backward_checked
        and state.final_route_wide_gate_ledger_unresolved_count_zero
        and state.final_route_wide_gate_ledger_self_interrogation_collected
        and state.self_interrogation_index_clean
        and state.final_residual_risk_triage_done
        and state.final_residual_risk_unresolved_count_zero
        and state.final_ledger_pm_independent_audit_done
    ):
        return InvariantResult.fail(
            "PM approved final route-wide capability ledger before reviewer replay, zero unresolved count, zero unresolved residual risks, and independent PM audit"
        )
    if state.pm_completion_decision_recorded and not state.final_route_wide_gate_ledger_pm_completion_approved:
        return InvariantResult.fail(
            "PM completion decision recorded before final route-wide capability gate ledger approval"
        )
    if state.pm_completion_decision_recorded and not state.flowpilot_skill_improvement_report_written:
        return InvariantResult.fail(
            "PM completion decision recorded before the nonblocking FlowPilot skill improvement report was written"
        )
    if state.pm_completion_decision_recorded and not (
        state.terminal_closure_suite_run
        and state.terminal_state_and_evidence_refreshed
    ):
        return InvariantResult.fail(
            "PM completion decision recorded before terminal closure suite refreshed capability state and evidence"
        )
    if state.role_binding_ledger_archived and not state.role_binding_memory_archived:
        return InvariantResult.fail("role-binding ledger archived before compact role memory archive")
    if state.pm_completion_decision_recorded and not state.role_binding_ledger_archived:
        return InvariantResult.fail("PM completion decision recorded before role binding archive")
    if state.status == "complete" and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("capability route completed before PM completion approval")
    if state.status == "complete" and not state.terminal_router_daemon_stopped:
        return InvariantResult.fail("capability route completed before stopping the persistent Router daemon")
    return InvariantResult.pass_()


def role_binding_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.self_interrogation_pm_ratified and not (
        state.role_binding_memory_policy_written
        and state.role_binding_memory_packets_written == REQUIRED_ROLE_BINDING_COUNT
    ):
        return InvariantResult.fail(
            "PM ratified capability startup before six compact role memory packets existed"
        )
    if state.heartbeat_pm_decision_requested and not state.terminal_router_daemon_stopped and not (
        state.heartbeat_loaded_state
        and state.heartbeat_loaded_frontier
        and state.heartbeat_loaded_packet_ledger
        and state.router_daemon_recovered_on_resume
        and state.router_daemon_started
        and state.controller_action_watch_active
        and state.heartbeat_loaded_role_binding_memory
        and state.heartbeat_host_rehydrate_requested
        and state.heartbeat_restored_crew
        and state.heartbeat_rehydrated_crew
        and state.heartbeat_injected_current_run_memory_into_roles
        and state.role_binding_recovery_report_written
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "heartbeat asked PM for capability work before current-run state, packet ledger, live role binding recovery, and role memory injection completed"
        )
    if state.pm_resume_decision_recorded and not (
        state.heartbeat_pm_controller_reminder_checked
        and state.heartbeat_reviewer_dispatch_policy_checked
    ):
        return InvariantResult.fail(
            "PM capability resume decision was accepted before controller reminder and reviewer-dispatch policy were checked"
        )
    if state.final_verification_done and (
        state.non_ui_implemented or state.ui_implemented
    ) and not state.role_memory_refreshed_after_work:
        return InvariantResult.fail(
            "final verification started before role memory packets were refreshed after implementation work"
        )
    if state.final_verification_done and (
        state.non_ui_implemented or state.ui_implemented
    ) and not state.current_node_skill_improvement_check_done:
        return InvariantResult.fail(
            "final verification started before PM checked whether the capability node exposed a nonblocking FlowPilot skill improvement observation"
        )
    if state.role_binding_ledger_archived and not state.role_binding_memory_archived:
        return InvariantResult.fail("role binding archive written before role memory archive")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="self_interrogation_before_contract",
        description="Freeze the contract only after showcase floor and visible self-interrogation style self-review evidence exist.",
        predicate=self_interrogation_before_contract,
    ),
    Invariant(
        name="startup_answers_before_showcase_and_self_interrogation",
        description="FlowPilot asks only the native startup intake options and waits for explicit answers before showcase commitment and self-interrogation.",
        predicate=mode_choice_before_showcase_and_self_interrogation,
    ),
    Invariant(
        name="implementation_requires_flowguard_gates",
        description="Formal implementation requires FlowGuard dependency, continuation readiness, meta-route, and capability-route checks.",
        predicate=implementation_requires_flowguard_gates,
    ),
    Invariant(
        name="dependency_plan_before_route_or_implementation",
        description="Capability route checks and implementation require demand-driven dependency planning, continuation readiness, and FlowGuard design first.",
        predicate=dependency_plan_before_route_or_implementation,
    ),
    Invariant(
        name="controlled_stop_notice_required",
        description="Controlled nonterminal capability stops emit a manual/heartbeat resume notice, and terminal completion emits a completion notice.",
        predicate=controlled_stop_notice_required,
    ),
    Invariant(
        name="child_skill_fidelity_before_capability_work",
        description="Child skill contracts, mapped requirements, evidence plan, and completion verification gate capability work and closure.",
        predicate=child_skill_fidelity_before_capability_work,
    ),
    Invariant(
        name="active_child_skill_binding_required_for_execution",
        description="Current-node execution requires active child-skill bindings, packet use instructions, source paths, use evidence, and reviewer checks.",
        predicate=active_child_skill_binding_required_for_execution,
    ),
    Invariant(
        name="ui_route_requires_ui_capabilities",
        description="UI implementation requires the autonomous UI child-skill route, child-skill-routed UI evidence before implementation, geometry/rendered QA after implementation, and source-skill loop closure before completion.",
        predicate=ui_route_requires_ui_capabilities,
    ),
    Invariant(
        name="capability_route_updates_force_recheck_and_resync",
        description="Capability route changes force recheck, evidence sync, execution-frontier sync, plan sync, and visible remapping before more work.",
        predicate=capability_route_updates_force_recheck_and_resync,
    ),
    Invariant(
        name="stable_heartbeat_prompt_not_capability_route_state",
        description="Heartbeat automation stays a stable launcher while persisted capability route/frontier state carries next-gate changes.",
        predicate=stable_heartbeat_prompt_not_capability_route_state,
    ),
    Invariant(
        name="startup_continuation_gates_work_beyond_startup",
        description="Startup loads Controller core before Controller-ledger obligations, then establishes heartbeat or manual-resume continuation before startup review and capability work.",
        predicate=startup_continuation_gates_work_beyond_startup,
    ),
    Invariant(
        name="heartbeat_continuation_is_lifecycle_state",
        description="Automated continuation uses only a stable heartbeat launcher; manual-resume routes must not create heartbeat automation.",
        predicate=heartbeat_continuation_is_lifecycle_state,
    ),
    Invariant(
        name="backend_route_does_not_run_ui_gates",
        description="Non-UI routes must not invoke UI-only gates.",
        predicate=backend_route_does_not_run_ui_gates,
    ),
    Invariant(
        name="sidecar_role_result_must_merge_before_implementation_or_completion",
        description="Sidecar role work must be scope-checked, returned, and merged before dependent implementation or completion.",
        predicate=sidecar_role_result_must_merge_before_implementation_or_completion,
    ),
    Invariant(
        name="human_review_judgement_requires_neutral_observation",
        description="Human-like implementation, backward, and final reviews observe before judging.",
        predicate=human_review_judgement_requires_neutral_observation,
    ),
    Invariant(
        name="pm_review_release_controls_reviewer_start",
        description="PM holds the reviewer until worker output is ready, then writes an explicit release order.",
        predicate=pm_review_release_controls_reviewer_start,
    ),
    Invariant(
        name="router_hard_rejection_requires_control_blocker_lane",
        description="Router hard rejections write a control blocker artifact and route it by lane.",
        predicate=router_hard_rejection_requires_control_blocker_lane,
    ),
    Invariant(
        name="final_completion_requires_right_verification",
        description="Completion requires route-appropriate implementation and verification evidence.",
        predicate=final_completion_requires_right_verification,
    ),
    Invariant(
        name="material_handoff_before_capability_route_design",
        description="Material intake, reviewer sufficiency, and PM understanding happen before capability route design.",
        predicate=material_handoff_before_capability_route_design,
    ),
    Invariant(
        name="actor_authority_gates_require_correct_role",
        description="Authority-sensitive capability gates require PM, reviewer, or matching FlowGuard officer approval and reject stale approvals.",
        predicate=actor_authority_gates_require_correct_role,
    ),
    Invariant(
        name="role_binding_memory_rehydration_required",
        description="Heartbeat recovery must load compact role memory, rehydrate or seed replacements, refresh memory after work, and archive it before role binding closure.",
        predicate=role_binding_memory_rehydration_required,
    ),
)


HAZARD_CASES = (
    (
        "child_skill_standards_not_promoted",
        {"child_skill_standards_promoted_to_node_contract": False},
        "standard inheritance",
    ),
    (
        "active_child_skill_binding_missing",
        {"active_child_skill_bindings_written": False},
        "active child-skill bindings",
    ),
    (
        "active_child_skill_binding_not_node_scoped",
        {"active_child_skill_binding_scope_limited": False},
        "current-node child-skill slice",
    ),
    (
        "child_skill_stricter_standard_downgraded",
        {"child_skill_stricter_standard_precedence_bound": False},
        "stricter child-skill standard precedence",
    ),
    (
        "worker_packet_missing_child_skill_use_instruction",
        {"worker_packet_child_skill_use_instruction_written": False},
        "direct child-skill use instruction",
    ),
    (
        "worker_packet_missing_child_skill_source_paths",
        {"active_child_skill_source_paths_allowed": False},
        "source paths",
    ),
    (
        "manifest_only_child_skill_gate_evidence",
        {"child_skill_manifest_only_evidence_rejected": False},
        "manifest-only evidence",
    ),
    (
        "missing_child_skill_execution_reports",
        {"child_skill_execution_reports_written": False},
        "execution reports",
    ),
    (
        "worker_missing_child_skill_use_evidence",
        {"worker_child_skill_use_evidence_returned": False},
        "Child Skill Use Evidence",
    ),
    (
        "reviewer_missing_child_skill_use_evidence_check",
        {"reviewer_child_skill_use_evidence_checked": False},
        "reviewer child-skill use evidence check",
    ),
    (
        "ui_palette_override_not_rationalized",
        {"ui_palette_default_or_override_rationale_recorded": False},
        "palette",
    ),
    (
        "ui_selected_concept_not_bound_to_review",
        {"ui_selected_concept_bound_to_review_packet": False},
        "selected-concept",
    ),
    (
        "ui_interaction_matrix_incomplete",
        {"ui_visible_affordance_interaction_matrix_complete": False},
        "interaction matrix",
    ),
    (
        "ui_concept_deviation_table_missing",
        {"ui_concept_vs_implementation_deviation_table_written": False},
        "deviation table",
    ),
    (
        "ui_iteration_budget_underfilled",
        {"ui_iteration_rounds_completed": DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS - 1},
        "iteration budget",
    ),
    (
        "ui_structural_redesign_not_considered",
        {"ui_structural_redesign_route_considered": False},
        "structural redesign",
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 145


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((CapabilityRouterStep(),), name="flowpilot_capability_router")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple(
        (result.label, result.new_state)
        for result in CapabilityRouterStep().apply(Tick(), state)
    )


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


__all__ = [
    "EXTERNAL_INPUTS",
    "HAZARD_CASES",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "initial_state",
    "is_success",
    "is_terminal",
    "next_states",
    "terminal_predicate",
]
