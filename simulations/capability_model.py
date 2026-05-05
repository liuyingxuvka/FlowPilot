"""FlowGuard model for flowpilot capability routing.

This model checks the planned skill-composition layer for FlowPilot. FlowPilot
starts only at showcase-grade scope, exposes its grill-me style
self-interrogation, creates heartbeat continuity, uses FlowGuard as process
designer before routing capabilities, and refuses completion while obvious
high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


CREW_SIZE = 6
TARGET_PARENT_NODES = 1
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
DEFAULT_UI_CHILD_SKILL_ITERATION_ROUNDS = 10
MAX_UI_CHILD_SKILL_ITERATION_ROUNDS = 20
# State-space bound for exploring repeat UI loop branches. This is not a
# runtime limit; the child UI skill owns the actual iteration standard.
MAX_UI_VISUAL_ITERATIONS = 2
MIN_FULL_GRILLME_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_GRILLME_QUESTIONS = 20
MAX_FOCUSED_GRILLME_QUESTIONS = 50
DEFAULT_FOCUSED_GRILLME_QUESTIONS = 30
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


@dataclass(frozen=True)
class Tick:
    """One capability-routing decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    task_kind: str = "unknown"  # unknown | backend | ui
    flowpilot_enabled: bool = False
    run_scoped_startup_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_questions_asked: bool = False
    startup_dialog_stopped_for_answers: bool = False
    startup_background_agents_answered: bool = False
    startup_scheduled_continuation_answered: bool = False
    startup_display_surface_answered: bool = False
    startup_answer_values_valid: bool = False
    startup_answer_provenance: str = "none"  # none | explicit_user_reply | inferred | default | naked
    startup_display_entry_action_done: bool = False
    run_directory_created: bool = False
    current_pointer_written: bool = False
    run_index_updated: bool = False
    prior_work_mode: str = "unknown"  # unknown | new | continue
    prior_work_import_packet_written: bool = False
    control_state_written_under_run_root: bool = False
    top_level_control_state_absent_or_quarantined: bool = False
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
    contract_frozen: bool = False
    crew_policy_written: bool = False
    crew_count: int = 0
    project_manager_ready: bool = False
    reviewer_ready: bool = False
    process_flowguard_officer_ready: bool = False
    product_flowguard_officer_ready: bool = False
    worker_a_ready: bool = False
    worker_b_ready: bool = False
    crew_ledger_written: bool = False
    role_identity_protocol_recorded: bool = False
    pm_flowguard_delegation_policy_recorded: bool = False
    officer_owned_async_modeling_policy_recorded: bool = False
    officer_model_report_provenance_policy_recorded: bool = False
    controller_coordination_boundary_recorded: bool = False
    independent_approval_protocol_recorded: bool = False
    crew_memory_policy_written: bool = False
    crew_memory_packets_written: int = 0
    pm_initial_capability_decision_recorded: bool = False
    heartbeat_loaded_state: bool = False
    heartbeat_loaded_frontier: bool = False
    heartbeat_loaded_packet_ledger: bool = False
    heartbeat_loaded_crew_memory: bool = False
    heartbeat_restored_crew: bool = False
    heartbeat_rehydrated_crew: bool = False
    crew_rehydration_report_written: bool = False
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
    crew_archived: bool = False
    crew_memory_archived: bool = False
    continuation_probe_done: bool = False
    continuation_host_kind_recorded: bool = False
    continuation_evidence_written: bool = False
    host_continuation_supported: bool = False
    manual_resume_mode_recorded: bool = False

    capabilities_manifest_written: bool = False
    pm_child_skill_selection_manifest_written: bool = False
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
    child_skill_contracts_loaded: bool = False
    child_skill_exact_source_verified: bool = False
    child_skill_substitutes_rejected: bool = False
    flowpilot_invocation_policy_mapped: bool = False
    child_skill_requirements_mapped: bool = False
    child_skill_evidence_plan_written: bool = False
    child_skill_subroute_projected: bool = False
    current_node_high_standard_recheck_written: bool = False
    node_acceptance_plan_written: bool = False
    node_acceptance_risk_experiments_mapped: bool = False
    child_skill_node_gate_manifest_refined: bool = False
    child_skill_gate_authority_records_written: bool = False
    child_skill_conformance_model_checked: bool = False
    child_skill_conformance_model_process_officer_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
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
    live_subagent_decision_recorded: bool = False
    live_subagents_started: bool = False
    live_subagents_current_task_fresh: bool = False
    fresh_agents_spawned_after_startup_answers: bool = False
    fresh_agents_spawned_after_route_allocation: bool = False
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
    ui_frontend_design_plan_done: bool = False
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
    ui_interaction_reachability_checked: bool = False
    ui_layout_overlap_density_checked: bool = False
    ui_reviewer_design_recommendations_recorded: bool = False
    ui_implementation_aesthetic_review_done: bool = False
    ui_implementation_aesthetic_reasons_recorded: bool = False
    ui_divergence_review_done: bool = False
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
    capability_backward_issue_grilled: bool = False
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
    pm_review_release_order_written: bool = False
    pm_released_reviewer_for_current_gate: bool = False
    packet_runtime_physical_files_written: bool = False
    controller_context_body_exclusion_verified: bool = False
    controller_relay_signature_audit_done: bool = False
    recipient_pre_open_relay_check_done: bool = False
    packet_mail_chain_audit_done: bool = False
    unopened_mail_pm_recovery_policy_recorded: bool = False
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
    subagent_pool_exists: bool = False
    subagent_idle_available: bool = False
    subagent_status: str = "none"  # none | idle | pending | returned | merged
    subagent_scope_checked: bool = False
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
        "capability_backward_issue_grilled": False,
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
            "heartbeat_loaded_crew_memory": False,
            "heartbeat_restored_crew": False,
            "heartbeat_rehydrated_crew": False,
            "crew_rehydration_report_written": False,
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
            "node_acceptance_plan_written": False,
            "node_acceptance_risk_experiments_mapped": False,
            "child_skill_node_gate_manifest_refined": False,
            "child_skill_gate_authority_records_written": False,
            "current_child_skill_gate_independent_validation_done": False,
            "child_skill_current_gates_role_approved": False,
            "child_node_sidecar_scan_done": False,
            "sidecar_need": "unknown",
            "subagent_scope_checked": False,
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
        "child_skill_exact_source_verified": False,
        "child_skill_substitutes_rejected": False,
        "flowpilot_invocation_policy_mapped": False,
        "child_skill_requirements_mapped": False,
        "child_skill_evidence_plan_written": False,
        "child_skill_subroute_projected": False,
        "non_ui_implemented": False,
        "ui_concept_target_ready": False,
        "ui_concept_target_visible": False,
        "ui_concept_personal_visual_review_done": False,
        "ui_concept_design_recommendations_recorded": False,
        "ui_frontend_design_plan_done": False,
        "visual_asset_scope": "unknown",
        "visual_asset_style_review_done": False,
        "visual_asset_personal_visual_review_done": False,
        "visual_asset_design_recommendations_recorded": False,
        "ui_implemented": False,
        "ui_screenshot_qa_done": False,
        "ui_geometry_qa_done": False,
        "ui_reviewer_personal_walkthrough_done": False,
        "ui_interaction_reachability_checked": False,
        "ui_layout_overlap_density_checked": False,
        "ui_reviewer_design_recommendations_recorded": False,
        "ui_implementation_aesthetic_review_done": False,
        "ui_implementation_aesthetic_reasons_recorded": False,
        "ui_divergence_review_done": False,
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
        "subagent_status": "none",
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
        and questions_per_layer >= MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
        and total_questions >= layer_count * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
        and _covers_required_risk_families(risk_family_mask)
    )


def _focused_interrogation_ready(*, total_questions: int, scope_id: str) -> bool:
    return (
        bool(scope_id)
        and MIN_FOCUSED_GRILLME_QUESTIONS
        <= total_questions
        <= MAX_FOCUSED_GRILLME_QUESTIONS
    )


def _product_function_architecture_ready(state: State) -> bool:
    return (
        _material_handoff_ready(state)
        and state.product_function_architecture_pm_synthesized
        and state.product_function_high_standard_posture_written
        and state.product_function_target_and_failure_bar_written
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
        state.crew_policy_written
        and state.crew_count == CREW_SIZE
        and state.project_manager_ready
        and state.reviewer_ready
        and state.process_flowguard_officer_ready
        and state.product_flowguard_officer_ready
        and state.worker_a_ready
        and state.worker_b_ready
        and state.crew_ledger_written
        and state.role_identity_protocol_recorded
        and state.pm_flowguard_delegation_policy_recorded
        and state.officer_owned_async_modeling_policy_recorded
        and state.officer_model_report_provenance_policy_recorded
        and state.controller_coordination_boundary_recorded
        and state.independent_approval_protocol_recorded
        and state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
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
        and state.top_level_control_state_absent_or_quarantined
        and not state.old_control_state_reused_as_current
    )


def _live_subagent_startup_resolved(state: State) -> bool:
    return (
        state.live_subagent_decision_recorded
        and (
            (
                state.live_subagents_started
                and state.live_subagents_current_task_fresh
                and state.fresh_agents_spawned_after_startup_answers
                and state.fresh_agents_spawned_after_route_allocation
                and state.historical_agent_ids_compared
                and not state.reused_historical_agent_ids
            )
            or state.single_agent_role_continuity_authorized
        )
    )


def _startup_questions_complete(state: State) -> bool:
    return (
        state.startup_questions_asked
        and state.startup_dialog_stopped_for_answers
        and state.startup_background_agents_answered
        and state.startup_scheduled_continuation_answered
        and state.startup_display_surface_answered
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
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
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
        and _live_subagent_startup_resolved(state)
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
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
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
        and _live_subagent_startup_resolved(state)
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
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
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
        and _live_subagent_startup_resolved(state)
        and _startup_pm_gate_ready(state)
        and state.work_beyond_startup_allowed
    )


def _gates_ready(state: State) -> bool:
    return _route_scaffold_ready(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _gates_lifecycle_valid(state: State) -> bool:
    return _route_scaffold_lifecycle_valid(state) and state.heartbeat_health_checked


def _subagent_clear(state: State) -> bool:
    return state.subagent_status in {"none", "idle", "merged"}


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
        "startup_questions_asked",
        "startup_dialog_stopped_for_answers",
        "startup_background_agents_answered",
        "startup_scheduled_continuation_answered",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "top_level_control_state_absent_or_quarantined",
        "old_control_state_reused_as_current",
        "showcase_floor_committed",
        "self_interrogation_done",
        "self_interrogation_questions",
        "self_interrogation_layer_count",
        "self_interrogation_questions_per_layer",
        "self_interrogation_layers",
        "self_interrogation_pm_ratified",
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
        "visible_self_interrogation_done",
        "contract_frozen",
        "crew_policy_written",
        "crew_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "crew_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "officer_owned_async_modeling_policy_recorded",
        "officer_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "crew_memory_policy_written",
        "crew_memory_packets_written",
        "pm_initial_capability_decision_recorded",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_crew_memory",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "crew_rehydration_report_written",
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
        "crew_archived",
        "crew_memory_archived",
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
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
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
        "live_subagent_decision_recorded",
        "live_subagents_started",
        "live_subagents_current_task_fresh",
        "fresh_agents_spawned_after_startup_answers",
        "fresh_agents_spawned_after_route_allocation",
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
        "visual_asset_scope",
        "visual_asset_style_review_done",
        "visual_asset_personal_visual_review_done",
        "visual_asset_design_recommendations_recorded",
        "visual_asset_aesthetic_review_done",
        "visual_asset_aesthetic_reasons_recorded",
        "ui_screenshot_qa_done",
        "ui_geometry_qa_done",
        "ui_reviewer_personal_walkthrough_done",
        "ui_interaction_reachability_checked",
        "ui_layout_overlap_density_checked",
        "ui_reviewer_design_recommendations_recorded",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_visual_iteration_loop_closed",
        "ui_visual_iterations",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "pm_review_hold_instruction_written",
        "worker_output_ready_for_review",
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
        "capability_backward_issue_grilled",
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
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_status",
    )
    writes = (
        "status",
        "task_kind",
        "flowpilot_enabled",
        "startup_questions_asked",
        "startup_dialog_stopped_for_answers",
        "startup_background_agents_answered",
        "startup_scheduled_continuation_answered",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "top_level_control_state_absent_or_quarantined",
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
        "contract_frozen",
        "crew_policy_written",
        "crew_count",
        "project_manager_ready",
        "reviewer_ready",
        "process_flowguard_officer_ready",
        "product_flowguard_officer_ready",
        "worker_a_ready",
        "worker_b_ready",
        "crew_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "officer_owned_async_modeling_policy_recorded",
        "officer_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "crew_memory_policy_written",
        "crew_memory_packets_written",
        "pm_initial_capability_decision_recorded",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_crew_memory",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "crew_rehydration_report_written",
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
        "crew_archived",
        "crew_memory_archived",
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
        "child_skill_node_gate_manifest_refined",
        "child_skill_gate_authority_records_written",
        "child_skill_conformance_model_checked",
        "child_skill_conformance_model_process_officer_approved",
        "strict_gate_obligation_review_model_checked",
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
        "live_subagent_decision_recorded",
        "live_subagents_started",
        "live_subagents_current_task_fresh",
        "fresh_agents_spawned_after_startup_answers",
        "fresh_agents_spawned_after_route_allocation",
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
        "ui_frontend_design_plan_done",
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
        "ui_interaction_reachability_checked",
        "ui_layout_overlap_density_checked",
        "ui_reviewer_design_recommendations_recorded",
        "ui_implementation_aesthetic_review_done",
        "ui_implementation_aesthetic_reasons_recorded",
        "ui_divergence_review_done",
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
        "capability_backward_issue_grilled",
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
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_status",
        "subagent_scope_checked",
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
    input_description = "one autopilot capability-routing decision"
    output_description = "next allowed capability gate or implementation action"
    idempotency = (
        "Capability routing records evidence for each invoked child skill and "
        "does not let dependent work proceed before the required gate is done."
    )

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        if state.status == "new":
            yield _step(
                state,
                label="autopilot_started",
                action="start capability router",
                status="running",
                flowpilot_enabled=True,
                run_scoped_startup_bootstrap_created=True,
            )
            return

        if not state.startup_questions_asked:
            yield _step(
                state,
                label="startup_three_questions_asked",
                action="ask background-agent permission, scheduled-continuation permission, and whether to open Cockpit UI before capability startup",
                startup_questions_asked=True,
            )
            return

        if not state.startup_dialog_stopped_for_answers:
            yield _step(
                state,
                label="startup_dialog_stopped_for_user_answers",
                action="end the assistant response after asking startup questions and wait for the user's reply",
                startup_dialog_stopped_for_answers=True,
            )
            return

        if not state.startup_background_agents_answered:
            yield _step(
                state,
                label="startup_background_agents_answered",
                action="record explicit user answer for live background agents versus single-agent continuity",
                startup_background_agents_answered=True,
            )
            return

        if not state.startup_scheduled_continuation_answered:
            yield _step(
                state,
                label="startup_scheduled_continuation_answered",
                action="record explicit user answer for heartbeat/automation versus manual resume",
                startup_scheduled_continuation_answered=True,
            )
            return

        if not state.startup_display_surface_answered:
            yield _step(
                state,
                label="startup_display_surface_answered",
                action="record explicit user answer for opening Cockpit UI immediately versus using chat route signs",
                startup_display_surface_answered=True,
                startup_answer_values_valid=True,
                startup_answer_provenance="explicit_user_reply",
            )
            return

        if not state.run_directory_created:
            yield _step(
                state,
                label="run_directory_created",
                action="create a fresh .flowpilot/runs/<run-id>/ directory for this formal FlowPilot invocation",
                run_directory_created=True,
            )
            return

        if not state.current_pointer_written:
            yield _step(
                state,
                label="current_pointer_written",
                action="write .flowpilot/current.json to point at the current run directory",
                current_pointer_written=True,
            )
            return

        if not state.run_index_updated:
            yield _step(
                state,
                label="run_index_updated",
                action="update .flowpilot/index.json with the new run identity and creation metadata",
                run_index_updated=True,
            )
            return

        if not state.startup_display_entry_action_done:
            yield _step(
                state,
                label="startup_display_entry_action_done",
                action="open Cockpit UI immediately when requested, or display the chat route sign when the user chose chat",
                startup_display_entry_action_done=True,
            )
            return

        if not state.defect_ledger_initialized:
            yield _step(
                state,
                label="defect_ledger_initialized",
                action="create the run-level defect ledger before capability reviews, repairs, pauses, or completion can record findings",
                defect_ledger_initialized=True,
            )
            return

        if not state.evidence_ledger_initialized:
            yield _step(
                state,
                label="evidence_ledger_initialized",
                action="create the run-level evidence credibility ledger before capability evidence can close gates",
                evidence_ledger_initialized=True,
            )
            return

        if not state.generated_resource_ledger_initialized:
            yield _step(
                state,
                label="generated_resource_ledger_initialized",
                action="create the run-level generated-resource ledger before concepts, UI assets, screenshots, route diagrams, or model reports are produced or discarded",
                generated_resource_ledger_initialized=True,
            )
            return

        if not state.activity_stream_initialized:
            yield _step(
                state,
                label="activity_stream_initialized",
                action="create the run-level activity stream so PM, reviewer, officer, worker, route, heartbeat, and user-visible progress events can be displayed without manual refresh",
                activity_stream_initialized=True,
                activity_stream_latest_event_written=True,
            )
            return

        if not state.flowpilot_improvement_live_report_initialized:
            yield _step(
                state,
                label="flowpilot_improvement_live_report_initialized",
                action="initialize the live FlowPilot improvement report before capability work can expose skill or process defects",
                flowpilot_improvement_live_report_initialized=True,
            )
            return

        if state.prior_work_mode == "unknown":
            yield _step(
                state,
                label="new_task_no_prior_import",
                action="record that this capability run starts without importing prior FlowPilot control state",
                prior_work_mode="new",
            )
            yield _step(
                state,
                label="continue_previous_work_selected",
                action="record that this capability run continues prior work but imports prior outputs as read-only evidence",
                prior_work_mode="continue",
            )
            return

        if state.prior_work_mode == "continue" and not state.prior_work_import_packet_written:
            yield _step(
                state,
                label="prior_work_import_packet_written",
                action="write a prior-work import packet under the new run without making old state current",
                prior_work_import_packet_written=True,
            )
            return

        if not state.control_state_written_under_run_root:
            yield _step(
                state,
                label="control_state_written_under_run_root",
                action="write state, frontier, capability evidence, crew, and review control artifacts only under the current run directory",
                control_state_written_under_run_root=True,
            )
            return

        if not state.top_level_control_state_absent_or_quarantined:
            yield _step(
                state,
                label="top_level_control_state_absent_or_quarantined",
                action="verify legacy top-level control state is absent, legacy-only, or quarantined before capability work continues",
                top_level_control_state_absent_or_quarantined=True,
            )
            return

        if not state.showcase_floor_committed:
            yield _step(
                state,
                label="showcase_floor_committed",
                action="commit capability routing to showcase-grade long-horizon scope",
                showcase_floor_committed=True,
            )
            return

        if not state.self_interrogation_done:
            yield _step(
                state,
                label="visible_self_interrogation_completed",
                action="derive dynamic layers, expose at least 100 grill-me questions per active layer, seed the improvement candidate pool, and seed initial validation direction",
                self_interrogation_done=True,
                self_interrogation_evidence=True,
                visible_self_interrogation_done=True,
                self_interrogation_questions=(
                    MODEL_DYNAMIC_LAYER_COUNT
                    * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                ),
                self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                quality_candidate_pool_seeded=True,
                validation_strategy_seeded=True,
            )
            return

        if not state.crew_policy_written:
            yield _step(
                state,
                label="six_agent_crew_policy_written",
                action="write fixed six-agent crew policy for capability routing",
                crew_policy_written=True,
            )
            return

        if state.crew_count == 0:
            yield _step(
                state,
                label="project_manager_spawned_fresh_for_task",
                action="spawn a fresh project manager for the new formal FlowPilot task before capability routing",
                crew_count=1,
                project_manager_ready=True,
            )
            return

        if state.crew_count == 1:
            yield _step(
                state,
                label="human_like_reviewer_spawned_fresh_for_task",
                action="spawn a fresh reviewer for the new formal FlowPilot task before capability routing",
                crew_count=2,
                reviewer_ready=True,
            )
            return

        if state.crew_count == 2:
            yield _step(
                state,
                label="process_flowguard_officer_spawned_fresh_for_task",
                action="spawn a fresh process FlowGuard officer for the new formal FlowPilot task before capability routing",
                crew_count=3,
                process_flowguard_officer_ready=True,
            )
            return

        if state.crew_count == 3:
            yield _step(
                state,
                label="product_flowguard_officer_spawned_fresh_for_task",
                action="spawn a fresh product FlowGuard officer for the new formal FlowPilot task before capability routing",
                crew_count=4,
                product_flowguard_officer_ready=True,
            )
            return

        if state.crew_count == 4:
            yield _step(
                state,
                label="worker_a_spawned_fresh_for_task",
                action="spawn a fresh worker A for bounded capability sidecar work in the new formal FlowPilot task",
                crew_count=5,
                worker_a_ready=True,
            )
            return

        if state.crew_count == 5:
            yield _step(
                state,
                label="worker_b_spawned_fresh_for_task",
                action="spawn a fresh worker B for bounded capability sidecar work in the new formal FlowPilot task",
                crew_count=CREW_SIZE,
                worker_b_ready=True,
            )
            return

        if not state.crew_ledger_written:
            yield _step(
                state,
                label="crew_ledger_written",
                action="persist crew names, role authority, agent ids, status, and recovery rules before capability work",
                crew_ledger_written=True,
            )
            return

        if not state.role_identity_protocol_recorded:
            yield _step(
                state,
                label="role_identity_protocol_recorded",
                action="record distinct role_key, display_name, and diagnostic-only agent_id fields before capability work",
                role_identity_protocol_recorded=True,
            )
            return

        if not state.pm_flowguard_delegation_policy_recorded:
            yield _step(
                state,
                label="pm_flowguard_delegation_policy_recorded",
                action="record that the project manager creates structured FlowGuard modeling requests for uncertain capability, process, product, object/reference-system, migration-equivalence, experiment-derived behavior, or validation decisions and assigns them to the process or product FlowGuard officer",
                pm_flowguard_delegation_policy_recorded=True,
            )
            return

        if not state.officer_owned_async_modeling_policy_recorded:
            yield _step(
                state,
                label="officer_owned_async_modeling_policy_recorded",
                action="record that capability FlowGuard model gates dispatch to officer-owned run directories while the controller may relay only non-dependent coordination",
                officer_owned_async_modeling_policy_recorded=True,
            )
            return

        if not state.officer_model_report_provenance_policy_recorded:
            yield _step(
                state,
                label="officer_model_report_provenance_policy_recorded",
                action="require capability officer model reports to prove model author, runner, interpreter, commands, input snapshots, state counts, counterexample inspection, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, blindspots, and decision",
                officer_model_report_provenance_policy_recorded=True,
            )
            return

        if not state.controller_coordination_boundary_recorded:
            yield _step(
                state,
                label="controller_coordination_boundary_recorded",
                action="record that controller coordination during capability officer modeling cannot satisfy route checks, implementation, checkpoint, completion, or protected model gates",
                controller_coordination_boundary_recorded=True,
            )
            return

        if not state.independent_approval_protocol_recorded:
            yield _step(
                state,
                label="independent_approval_protocol_recorded",
                action="record that every PM, reviewer, and FlowGuard officer approval requires independent adversarial validation evidence and cannot be completion-report-only",
                independent_approval_protocol_recorded=True,
            )
            return

        if not state.crew_memory_policy_written:
            yield _step(
                state,
                label="crew_memory_packets_written",
                action="write compact role memory packets for all six capability-routing roles before PM ratification",
                crew_memory_policy_written=True,
                crew_memory_packets_written=CREW_SIZE,
            )
            return

        if not state.self_interrogation_pm_ratified:
            yield _step(
                state,
                label="self_interrogation_pm_ratified",
                action="project manager ratifies capability startup self-interrogation scope, risk layers, question count, and decision set",
                self_interrogation_pm_ratified=True,
            )
            return

        if not state.material_sources_scanned:
            yield _step(
                state,
                label="material_sources_scanned",
                action="authorized worker scans user-provided and repository-local materials before capability route design",
                material_sources_scanned=True,
            )
            return

        if not state.material_source_summaries_written:
            yield _step(
                state,
                label="material_source_summaries_written",
                action="authorized worker writes purpose, contents, and current-state summaries for capability-relevant materials",
                material_source_summaries_written=True,
            )
            return

        if not state.material_source_quality_classified:
            yield _step(
                state,
                label="material_source_quality_classified",
                action="authorized worker classifies source authority, freshness, contradictions, missing context, and readiness",
                material_source_quality_classified=True,
            )
            return

        if not state.local_skill_inventory_written:
            yield _step(
                state,
                label="local_skill_inventory_written",
                action="authorized worker inventories locally available skills and host capabilities as candidate resources before the material packet is finalized",
                local_skill_inventory_written=True,
            )
            return

        if not state.local_skill_inventory_candidate_classified:
            yield _step(
                state,
                label="local_skill_inventory_candidate_classified",
                action="authorized worker classifies local skills as candidate-only resources without treating availability as PM approval to use them",
                local_skill_inventory_candidate_classified=True,
            )
            return

        if not state.material_intake_packet_written:
            yield _step(
                state,
                label="material_intake_packet_written",
                action="authorized worker writes the Material Intake Packet, including local skill inventory, before PM capability planning",
                material_intake_packet_written=True,
            )
            return

        if not state.material_reviewer_direct_source_probe_done:
            yield _step(
                state,
                label="material_reviewer_direct_source_probe_done",
                action="human-like reviewer opens or samples actual materials and tests whether the packet could be summary-only before sufficiency approval",
                material_reviewer_direct_source_probe_done=True,
            )
            return

        if not state.material_reviewer_sufficiency_checked:
            yield _step(
                state,
                label="material_reviewer_sufficiency_checked",
                action="human-like reviewer checks whether the material packet is clear and complete enough for PM capability planning",
                material_reviewer_sufficiency_checked=True,
            )
            return

        if not state.material_reviewer_sufficiency_approved:
            yield _step(
                state,
                label="material_reviewer_sufficiency_approved",
                action="human-like reviewer approves that the Material Intake Packet is PM-ready or blocks capability planning",
                material_reviewer_sufficiency_approved=True,
            )
            return

        if not state.pm_material_understanding_memo_written:
            yield _step(
                state,
                label="pm_material_understanding_memo_written",
                action="project manager writes a material understanding memo with source-claim matrix, open questions, and capability implications",
                pm_material_understanding_memo_written=True,
            )
            return

        if not state.pm_material_complexity_classified:
            yield _step(
                state,
                label="pm_material_complexity_classified",
                action="project manager classifies material complexity as simple, normal, or messy/raw before capability planning",
                pm_material_complexity_classified=True,
            )
            return

        if not state.pm_material_discovery_decision_recorded:
            yield _step(
                state,
                label="pm_material_discovery_decision_recorded",
                action="project manager records whether materials can feed capability routing directly or require a formal discovery, cleanup, modeling, or validation subtree",
                pm_material_discovery_decision_recorded=True,
            )
            return

        if not state.pm_material_research_decision_recorded:
            yield _step(
                state,
                label="pm_material_research_decision_not_required",
                action="project manager records that reviewed materials are sufficient and no formal research package is required before capability architecture",
                pm_material_research_decision_recorded=True,
                material_research_need="not_required",
            )
            yield _step(
                state,
                label="pm_material_research_decision_requires_package",
                action="project manager records a material gap that must become a formal research, mechanism-discovery, evidence-collection, or experiment package before capability architecture",
                pm_material_research_decision_recorded=True,
                material_research_need="required",
            )
            return

        if state.material_research_need == "required":
            if not state.pm_research_package_written:
                yield _step(
                    state,
                    label="pm_research_package_written",
                    action="project manager writes a bounded research package with question, route impact, allowed sources, worker owner, evidence standard, reviewer checks, and stop conditions",
                    pm_research_package_written=True,
                )
                return

            if not state.research_tool_capability_decision_recorded:
                yield _step(
                    state,
                    label="research_tool_capability_decision_recorded",
                    action="project manager records whether local, browser, web search, account, or user-provided sources are available and routes missing capabilities to user clarification, fallback, or block",
                    research_tool_capability_decision_recorded=True,
                )
                return

            if not state.research_worker_report_returned:
                yield _step(
                    state,
                    label="research_worker_report_returned",
                    action="assigned worker searches, inspects, experiments, or reconciles sources and returns a research package report with raw evidence pointers and limitations",
                    research_worker_report_returned=True,
                )
                return

            if not state.research_reviewer_direct_source_check_done:
                yield _step(
                    state,
                    label="research_reviewer_direct_source_check_done",
                    action="human-like reviewer directly checks original sources, search results, logs, screenshots, or experiment outputs instead of trusting the worker summary",
                    research_reviewer_direct_source_check_done=True,
                )
                return

            if not state.research_reviewer_sufficiency_passed:
                if not state.research_reviewer_rework_required:
                    yield _step(
                        state,
                        label="research_reviewer_sufficiency_passed",
                        action="human-like reviewer approves the research package as sufficient for PM capability decisions after direct source checks",
                        research_reviewer_sufficiency_passed=True,
                    )
                    yield _step(
                        state,
                        label="research_reviewer_rework_required",
                        action="human-like reviewer rejects the worker research output as shallow, unsupported, stale, contradictory, or missing required source checks",
                        research_reviewer_rework_required=True,
                    )
                    return

                if not state.research_worker_rework_completed:
                    yield _step(
                        state,
                        label="research_worker_rework_completed",
                        action="assigned worker reruns or expands the research package according to reviewer blockers and returns corrected evidence",
                        research_worker_rework_completed=True,
                    )
                    return

                if not state.research_reviewer_recheck_done:
                    yield _step(
                        state,
                        label="research_reviewer_recheck_done",
                        action="human-like reviewer rechecks the corrected research output against the original package and prior blockers",
                        research_reviewer_recheck_done=True,
                    )
                    return

                yield _step(
                    state,
                    label="research_reviewer_sufficiency_passed",
                    action="human-like reviewer approves the reworked research package after direct source recheck",
                    research_reviewer_sufficiency_passed=True,
                    research_reviewer_rework_required=False,
                    research_worker_rework_completed=False,
                    research_reviewer_recheck_done=False,
                )
                return

            if not state.pm_research_result_absorbed_or_route_mutated:
                yield _step(
                    state,
                    label="pm_research_result_absorbed_or_route_mutated",
                    action="project manager absorbs approved research into material understanding, capability architecture inputs, route mutation, or a blocked/user-clarification decision",
                    pm_research_result_absorbed_or_route_mutated=True,
                )
                return

            yield _step(
                state,
                label="material_research_gap_closed",
                action="project manager marks the approved research gap closed after preserving absorption or route-mutation evidence so downstream planning no longer branches on stale research state",
                material_research_need="not_required",
                pm_research_package_written=False,
                research_tool_capability_decision_recorded=False,
                research_worker_report_returned=False,
                research_reviewer_direct_source_check_done=False,
                research_reviewer_rework_required=False,
                research_worker_rework_completed=False,
                research_reviewer_recheck_done=False,
                research_reviewer_sufficiency_passed=False,
                pm_research_result_absorbed_or_route_mutated=False,
            )
            return

        if not state.product_function_architecture_pm_synthesized:
            yield _step(
                state,
                label="product_function_architecture_pm_synthesized",
                action="project manager synthesizes grilled capability ideas into a product-function architecture decision package before contract freeze",
                product_function_architecture_pm_synthesized=True,
            )
            return

        if not state.product_function_high_standard_posture_written:
            yield _step(
                state,
                label="product_function_high_standard_posture_written",
                action="project manager records that a FlowPilot invocation means an important project and sets the highest reasonably achievable worker standard, not the lowest viable route or a self-effort estimate",
                product_function_high_standard_posture_written=True,
            )
            return

        if not state.product_function_target_and_failure_bar_written:
            yield _step(
                state,
                label="product_function_target_and_failure_bar_written",
                action="project manager describes the strongest feasible product target and the rough, embarrassing, or placeholder results that must be rejected before completion",
                product_function_target_and_failure_bar_written=True,
            )
            return

        if not state.product_function_semantic_fidelity_policy_written:
            yield _step(
                state,
                label="product_function_semantic_fidelity_policy_written",
                action="project manager maps user goals to material evidence and records that source gaps require discovery, staged delivery, or user clarification instead of silent semantic downgrade",
                product_function_semantic_fidelity_policy_written=True,
            )
            return

        if not state.product_function_user_task_map_written:
            yield _step(
                state,
                label="product_function_user_task_map_written",
                action="write target users, situations, jobs-to-be-done, and decision points before capability routing",
                product_function_user_task_map_written=True,
            )
            return

        if not state.product_function_capability_map_written:
            yield _step(
                state,
                label="product_function_capability_map_written",
                action="write must, should, optional, and rejected capability decisions before child-skill route discovery",
                product_function_capability_map_written=True,
            )
            return

        if not state.product_function_feature_decisions_written:
            yield _step(
                state,
                label="product_function_feature_decisions_written",
                action="bind each accepted capability to a user task and reject feature ideas that do not earn their place",
                product_function_feature_decisions_written=True,
            )
            return

        if not state.product_function_display_rationale_written:
            yield _step(
                state,
                label="product_function_display_rationale_written",
                action="record why each visible text, state, control, or status belongs in the product and what user decision it changes",
                product_function_display_rationale_written=True,
            )
            return

        if not state.product_function_gap_review_done:
            yield _step(
                state,
                label="product_function_missing_feature_review_done",
                action="review likely missing high-value capabilities before the route turns them into local implementation tasks",
                product_function_gap_review_done=True,
            )
            return

        if not state.product_function_negative_scope_written:
            yield _step(
                state,
                label="product_function_negative_scope_written",
                action="write non-goals and rejected displays to keep capability routing from adding accidental work",
                product_function_negative_scope_written=True,
            )
            return

        if not state.product_function_acceptance_matrix_written:
            yield _step(
                state,
                label="product_function_acceptance_matrix_written",
                action="write functional acceptance matrix with inputs, outputs, states, failure cases, and evidence for each core capability",
                product_function_acceptance_matrix_written=True,
            )
            return

        if not state.root_acceptance_thresholds_defined:
            yield _step(
                state,
                label="root_acceptance_thresholds_defined",
                action="project manager defines early hard acceptance thresholds for important capability requirements before contract freeze",
                root_acceptance_thresholds_defined=True,
            )
            return

        if not state.root_acceptance_proof_matrix_written:
            yield _step(
                state,
                label="root_acceptance_proof_matrix_written",
                action="project manager writes the root proof matrix mapping hard capability requirements to experiments, inspections, evidence, owners, and approvers",
                root_acceptance_proof_matrix_written=True,
            )
            return

        if not state.standard_scenario_pack_selected:
            yield _step(
                state,
                label="standard_scenario_pack_selected",
                action="project manager selects the standard scenario pack for terminal replay of happy paths, edge cases, regressions, lifecycle, and PM-risk scenarios",
                standard_scenario_pack_selected=True,
            )
            return

        if not state.product_architecture_officer_adversarial_probe_done:
            yield _step(
                state,
                label="product_architecture_officer_adversarial_probe_done",
                action="product FlowGuard officer checks modelability, missing state fields, unsupported claims, and failure paths before approving the PM architecture",
                product_architecture_officer_adversarial_probe_done=True,
            )
            return

        if not state.product_function_architecture_product_officer_approved:
            yield _step(
                state,
                label="product_function_architecture_product_officer_approved",
                action="product FlowGuard officer approves that the PM product-function architecture can drive capability and child-skill routing",
                product_function_architecture_product_officer_approved=True,
            )
            return

        if not state.product_function_architecture_reviewer_challenged:
            if not state.product_architecture_reviewer_adversarial_probe_done:
                yield _step(
                    state,
                    label="product_architecture_reviewer_adversarial_probe_done",
                    action="human-like reviewer attacks the PM product architecture against user tasks, inspected materials, missing features, unnecessary visible text, and weak failure states",
                    product_architecture_reviewer_adversarial_probe_done=True,
                )
                return
            yield _step(
                state,
                label="product_function_architecture_reviewer_challenged",
                action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
                product_function_architecture_reviewer_challenged=True,
            )
            return

        if not state.contract_frozen:
            yield _step(
                state,
                label="contract_frozen",
                action="freeze acceptance contract from the PM product-function architecture",
                contract_frozen=True,
            )
            return

        if state.task_kind == "unknown":
            yield _step(
                state,
                label="classified_backend_task",
                action="classify task as non-UI software project",
                task_kind="backend",
            )
            yield _step(
                state,
                label="classified_ui_task",
                action="classify task as substantial user-facing UI project",
                task_kind="ui",
            )
            return

        if not state.capabilities_manifest_written:
            yield _step(
                state,
                label="capabilities_manifest_written",
                action="write capabilities manifest for required and conditional skills",
                capabilities_manifest_written=True,
            )
            return

        if not state.pm_child_skill_selection_manifest_written:
            yield _step(
                state,
                label="pm_child_skill_selection_manifest_written",
                action="project manager writes a child-skill selection manifest from the product architecture, capability map, and local skill inventory",
                pm_child_skill_selection_manifest_written=True,
            )
            return

        if not state.pm_child_skill_selection_scope_decisions_recorded:
            yield _step(
                state,
                label="pm_child_skill_selection_scope_decisions_recorded",
                action="project manager classifies candidate skills as required, conditional, deferred, or rejected before child-skill route discovery",
                pm_child_skill_selection_scope_decisions_recorded=True,
            )
            return

        if not state.child_skill_route_design_discovery_started:
            yield _step(
                state,
                label="child_skill_route_design_discovery_started",
                action="project manager starts route-design discovery only from PM-selected child skills, not from raw local skill availability",
                child_skill_route_design_discovery_started=True,
            )
            return

        if not state.child_skill_initial_gate_manifest_extracted:
            yield _step(
                state,
                label="child_skill_initial_gate_manifest_extracted",
                action="extract child-skill stages, checks, standards, evidence needs, and skipped-reference reasons into an initial gate manifest before route modeling",
                child_skill_initial_gate_manifest_extracted=True,
            )
            return

        if not state.child_skill_gate_approvers_assigned:
            yield _step(
                state,
                label="child_skill_gate_approvers_assigned",
                action="assign required approver roles for every child-skill gate and forbid controller or worker self-approval",
                child_skill_gate_approvers_assigned=True,
            )
            return

        if not state.child_skill_manifest_independent_validation_done:
            yield _step(
                state,
                label="child_skill_manifest_independent_validation_done",
                action="reviewer, process officer, product officer, and PM independently probe the child-skill manifest slices instead of accepting the extraction report",
                child_skill_manifest_independent_validation_done=True,
            )
            return

        if not state.child_skill_manifest_reviewer_reviewed:
            yield _step(
                state,
                label="child_skill_manifest_reviewer_reviewed",
                action="human-like reviewer reviews human/product/visual/interaction child-skill gates before they enter the route",
                child_skill_manifest_reviewer_reviewed=True,
            )
            return

        if not state.child_skill_manifest_process_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_process_officer_approved",
                action="process FlowGuard officer approves child-skill process and conformance gates before route modeling",
                child_skill_manifest_process_officer_approved=True,
            )
            return

        if not state.child_skill_manifest_product_officer_approved:
            yield _step(
                state,
                label="child_skill_manifest_product_officer_approved",
                action="product FlowGuard officer approves product-function impact gates derived from child skills",
                child_skill_manifest_product_officer_approved=True,
            )
            return

        if not state.child_skill_manifest_pm_approved_for_route:
            yield _step(
                state,
                label="child_skill_manifest_pm_approved_for_route",
                action="project manager approves the child-skill gate manifest for inclusion in the initial route, PM runway, and visible plan",
                child_skill_manifest_pm_approved_for_route=True,
            )
            return

        if not state.child_skill_focused_interrogation_done:
            yield _step(
                state,
                label="child_skill_focused_interrogation_completed",
                action="run 20-50 focused grill-me questions for invoked child-skill boundaries",
                child_skill_focused_interrogation_done=True,
                child_skill_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                child_skill_focused_interrogation_scope_id="invoked-child-skills",
            )
            return

        if not state.child_skill_contracts_loaded:
            yield _step(
                state,
                label="child_skill_contracts_loaded",
                action="read each invoked source skill's SKILL.md and relevant references",
                child_skill_contracts_loaded=True,
            )
            return

        if not state.child_skill_exact_source_verified:
            yield _step(
                state,
                label="child_skill_exact_source_verified",
                action="verify the exact source skill was loaded instead of a similar local substitute",
                child_skill_exact_source_verified=True,
            )
            return

        if not state.child_skill_substitutes_rejected:
            yield _step(
                state,
                label="child_skill_substitutes_rejected",
                action="record that ad hoc concept substitutes cannot satisfy child-skill gates",
                child_skill_substitutes_rejected=True,
            )
            return

        if not state.flowpilot_invocation_policy_mapped:
            yield _step(
                state,
                label="flowpilot_invocation_policy_mapped",
                action="map FlowPilot-owned formal invocation policy for general-purpose child skills",
                flowpilot_invocation_policy_mapped=True,
            )
            return

        if not state.child_skill_requirements_mapped:
            yield _step(
                state,
                label="child_skill_requirements_mapped",
                action="map child skill workflow, hard gates, and completion standard into route gates",
                child_skill_requirements_mapped=True,
            )
            return

        if not state.child_skill_evidence_plan_written:
            yield _step(
                state,
                label="child_skill_evidence_plan_written",
                action="write evidence checklist for each invoked child skill",
                child_skill_evidence_plan_written=True,
            )
            return

        if not state.child_skill_subroute_projected:
            yield _step(
                state,
                label="child_skill_subroute_projected",
                action="project each invoked child skill into a visible mini-route of key milestones, not copied prompt details",
                child_skill_subroute_projected=True,
            )
            return

        if not state.child_skill_conformance_model_checked:
            yield _step(
                state,
                label="child_skill_conformance_model_checked",
                action="process FlowGuard officer models and approves child-skill contract conformance before capability work",
                child_skill_conformance_model_checked=True,
                child_skill_conformance_model_process_officer_approved=True,
            )
            return

        if not state.strict_gate_obligation_review_model_checked:
            yield _step(
                state,
                label="strict_gate_obligation_review_model_checked",
                action="process FlowGuard officer runs the strict gate-obligation model so child-skill review caveats cannot close the active gate",
                strict_gate_obligation_review_model_checked=True,
            )
            return

        if not state.flowguard_dependency_checked:
            yield _step(
                state,
                label="flowguard_dependency_checked",
                action="verify real FlowGuard package and model-first skill",
                flowguard_dependency_checked=True,
            )
            return

        if not state.dependency_plan_recorded:
            yield _step(
                state,
                label="dependency_plan_recorded",
                action="record dependency inventory and defer non-current installs",
                dependency_plan_recorded=True,
                future_installs_deferred=True,
            )
            return

        if not state.continuation_probe_done:
            yield _step(
                state,
                label="host_continuation_capability_supported",
                action="probe host automation capability, record host-kind continuation evidence, and confirm real heartbeat setup is supported",
                continuation_probe_done=True,
                continuation_host_kind_recorded=True,
                continuation_evidence_written=True,
                host_continuation_supported=True,
            )
            yield _step(
                state,
                label="host_continuation_capability_unsupported_manual_resume",
                action="probe host automation capability, record host-kind evidence, find no real wakeup support, and record manual-resume mode without creating heartbeat automation",
                continuation_probe_done=True,
                continuation_host_kind_recorded=True,
                continuation_evidence_written=True,
                host_continuation_supported=False,
                manual_resume_mode_recorded=True,
            )
            return

        if state.host_continuation_supported and not state.heartbeat_schedule_created:
            yield _step(
                state,
                label="heartbeat_schedule_created",
                action="create one-minute route heartbeat as a stable launcher that reads state and execution frontier",
                heartbeat_schedule_created=True,
                route_heartbeat_interval_minutes=1,
                stable_heartbeat_launcher_recorded=True,
                heartbeat_bound_to_current_run=True,
                heartbeat_same_name_only_checked=False,
            )
            return

        if not state.pm_initial_capability_decision_recorded:
            yield _step(
                state,
                label="pm_initial_capability_decision_recorded",
                action="ask the project manager to choose the capability-route direction from the contract, child-skill map, dependency plan, and crew reports",
                pm_initial_capability_decision_recorded=True,
            )
            return

        if not state.flowguard_process_design_done:
            yield _step(
                state,
                label="flowguard_process_designed",
                action="process FlowGuard officer uses FlowGuard as the capability-route process designer",
                flowguard_process_design_done=True,
            )
            return

        if not state.flowguard_officer_model_adversarial_probe_done:
            yield _step(
                state,
                label="flowguard_officer_model_adversarial_probe_done",
                action="FlowGuard officers run or validate model checks, inspect counterexamples, cite state fields, labels, counts, commands, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, and blindspots before model approvals",
                flowguard_officer_model_adversarial_probe_done=True,
                flowguard_model_report_risk_tiers_done=True,
                flowguard_model_report_pm_review_agenda_done=True,
                flowguard_model_report_toolchain_recommendations_done=True,
                flowguard_model_report_confidence_boundary_done=True,
            )
            return

        if not state.meta_route_checked:
            yield _step(
                state,
                label="meta_route_checked",
                action="process FlowGuard officer approves meta-route checks from officer-owned adversarial model evidence",
                meta_route_checked=True,
                meta_route_process_officer_approved=True,
            )
            return

        if not state.capability_route_checked:
            yield _step(
                state,
                label="capability_route_checked",
                action="process FlowGuard officer approves capability-route checks from officer-owned adversarial model evidence",
                capability_route_version=state.capability_route_version or 1,
                capability_route_checked=True,
                capability_route_process_officer_approved=True,
            )
            return

        if not state.parent_backward_structural_trigger_rule_recorded:
            yield _step(
                state,
                label="parent_backward_structural_trigger_rule_recorded",
                action="project manager records that every effective capability route node with children requires local parent backward replay without semantic importance guessing",
                parent_backward_structural_trigger_rule_recorded=True,
            )
            return

        if (
            not state.parent_backward_review_targets_enumerated
            or state.parent_backward_review_targets_route_version
            != state.capability_route_version
        ):
            yield _step(
                state,
                label="parent_backward_review_targets_enumerated",
                action="project manager enumerates all effective capability parent/composite nodes directly from the current route structure",
                parent_backward_review_targets_enumerated=True,
                parent_backward_review_targets_route_version=state.capability_route_version,
                parent_backward_targets_count=TARGET_PARENT_NODES,
            )
            return

        if not state.capability_product_function_model_checked:
            yield _step(
                state,
                label="capability_product_function_model_checked",
                action="product FlowGuard officer approves the capability product-function model from officer-owned adversarial model evidence",
                capability_product_function_model_checked=True,
                capability_product_function_model_product_officer_approved=True,
            )
            return

        if not state.capability_evidence_synced:
            yield _step(
                state,
                label="capability_evidence_synced",
                action="sync capability evidence JSON and English summary",
                capability_evidence_synced=True,
            )
            return

        if not state.execution_frontier_written:
            yield _step(
                state,
                label="execution_frontier_written",
                action="write capability execution frontier from checked route, active gate, next gate, and current mainline",
                execution_frontier_written=True,
                frontier_version=state.capability_route_version,
            )
            return

        if not state.codex_plan_synced:
            yield _step(
                state,
                label="codex_plan_synced",
                action="sync visible Codex plan from capability execution frontier without changing heartbeat automation prompt",
                codex_plan_synced=True,
                plan_version=state.frontier_version,
            )
            return

        if not state.capability_user_flow_diagram_refreshed:
            yield _step(
                state,
                label="capability_user_flow_diagram_refreshed",
                action="refresh single user flow diagram from checked capability route and execution frontier before chat or UI display",
                capability_user_flow_diagram_refreshed=True,
            )
            return

        if (
            state.capability_route_checked
            and state.capability_product_function_model_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and not state.capability_user_flow_diagram_emitted
        ):
            yield _step(
                state,
                label="capability_user_flow_diagram_emitted",
                action="emit visible capability user flow diagram with next gates, checks, and fallback branches",
                capability_user_flow_diagram_emitted=True,
            )
            return

        if (
            state.capability_route_checked
            and state.capability_product_function_model_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and state.capability_user_flow_diagram_emitted
            and not state.live_subagent_decision_recorded
        ):
            yield _step(
                state,
                label="live_subagent_start_authorized",
                action="ask for and record user authorization to start the six live FlowPilot background agents",
                live_subagent_decision_recorded=True,
            )
            return

        if (
            state.capability_route_checked
            and state.capability_product_function_model_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and state.capability_user_flow_diagram_emitted
            and state.live_subagent_decision_recorded
            and not state.live_subagents_started
            and not state.single_agent_role_continuity_authorized
        ):
            yield _step(
                state,
                label="fresh_six_live_subagents_started",
                action="start all six live FlowPilot background agents as fresh current-task subagents and record nonreuse evidence",
                live_subagents_started=True,
                live_subagents_current_task_fresh=True,
                fresh_agents_spawned_after_startup_answers=True,
                fresh_agents_spawned_after_route_allocation=True,
                historical_agent_ids_compared=True,
                reused_historical_agent_ids=False,
            )
            return

        if (
            state.capability_route_checked
            and state.capability_product_function_model_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and state.capability_user_flow_diagram_emitted
            and _live_subagent_startup_resolved(state)
            and not state.startup_preflight_review_report_written
            and not state.startup_worker_remediation_completed
        ):
            yield _step(
                state,
                label="startup_preflight_reviewer_fact_report_blocked",
                action="human-like reviewer independently checks startup facts including run isolation, prior-work boundary, and current-task live-agent freshness, then reports blockers to PM without opening the start gate",
                startup_preflight_review_report_written=True,
                startup_preflight_review_blocking_findings=True,
                startup_reviewer_fact_evidence_checked=True,
                startup_reviewer_checked_run_isolation=True,
                startup_reviewer_checked_prior_work_boundary=True,
                startup_reviewer_checked_live_agent_freshness=True,
                startup_reviewer_checked_no_historical_agent_reuse=True,
                startup_reviewer_checked_capability_resolution=True,
                startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
            )
            return

        if (
            state.startup_preflight_review_report_written
            and state.startup_preflight_review_blocking_findings
            and not state.pm_returned_startup_blockers
            and not state.startup_worker_remediation_completed
            and not state.pm_start_gate_opened
        ):
            yield _step(
                state,
                label="pm_returns_startup_blockers_to_worker",
                action="project manager reads reviewer startup report and returns concrete blockers to workers for remediation",
                pm_returned_startup_blockers=True,
            )
            return

        if (
            state.startup_preflight_review_report_written
            and state.startup_preflight_review_blocking_findings
            and state.pm_returned_startup_blockers
            and not state.startup_worker_remediation_completed
            and not state.pm_start_gate_opened
        ):
            yield _step(
                state,
                label="startup_worker_remediation_completed",
                action="workers remediate startup blockers and invalidate the old reviewer report for recheck",
                startup_worker_remediation_completed=True,
                pm_returned_startup_blockers=False,
                startup_preflight_review_report_written=False,
                startup_preflight_review_blocking_findings=False,
                startup_reviewer_fact_evidence_checked=False,
                startup_reviewer_checked_run_isolation=False,
                startup_reviewer_checked_prior_work_boundary=False,
                startup_reviewer_checked_live_agent_freshness=False,
                startup_reviewer_checked_no_historical_agent_reuse=False,
                startup_reviewer_checked_capability_resolution=False,
                startup_reviewer_checked_current_run_heartbeat_binding=False,
                startup_pm_independent_gate_audit_done=False,
                startup_pm_capability_resolution_recorded=False,
            )
            return

        if (
            state.capability_route_checked
            and state.capability_product_function_model_checked
            and state.capability_evidence_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.capability_route_version
            and state.plan_version == state.frontier_version
            and state.capability_user_flow_diagram_refreshed
            and state.capability_user_flow_diagram_emitted
            and _live_subagent_startup_resolved(state)
            and not state.startup_preflight_review_report_written
            and state.startup_worker_remediation_completed
        ):
            yield _step(
                state,
                label="startup_preflight_reviewer_fact_report_clean",
                action="human-like reviewer independently checks user answers, current run directory, current/index pointers, prior-work import boundary, real route state, continuation mode, cleanup boundary, current-task fresh crew evidence, and writes a clean fact report for PM",
                startup_preflight_review_report_written=True,
                startup_preflight_review_blocking_findings=False,
                startup_reviewer_fact_evidence_checked=True,
                startup_reviewer_checked_run_isolation=True,
                startup_reviewer_checked_prior_work_boundary=True,
                startup_reviewer_checked_live_agent_freshness=True,
                startup_reviewer_checked_no_historical_agent_reuse=True,
                startup_reviewer_checked_capability_resolution=True,
                startup_reviewer_checked_current_run_heartbeat_binding=not state.manual_resume_mode_recorded,
            )
            return

        if (
            state.startup_preflight_review_report_written
            and not state.startup_preflight_review_blocking_findings
            and not state.startup_pm_independent_gate_audit_done
            and not state.pm_start_gate_opened
        ):
            yield _step(
                state,
                label="startup_pm_independent_gate_audit_done",
                action="PM independently audits capability startup run isolation, prior-work boundary, live-agent freshness or authorized continuity, reviewer evidence paths, and report-only failure hypotheses before opening the start gate",
                startup_pm_independent_gate_audit_done=True,
                startup_pm_capability_resolution_recorded=True,
            )
            return

        if (
            state.startup_preflight_review_report_written
            and not state.startup_preflight_review_blocking_findings
            and state.startup_pm_independent_gate_audit_done
            and not state.pm_start_gate_opened
        ):
            yield _step(
                state,
                label="pm_start_gate_opened_from_fact_report",
                action="project manager opens startup and allows work beyond startup from the current clean factual reviewer report",
                pm_start_gate_opened=True,
                work_beyond_startup_allowed=True,
            )
            return

        if state.capability_backward_issue_strategy != "none":
            if not state.capability_backward_issue_grilled:
                yield _step(
                    state,
                    label="capability_backward_issue_grilled",
                    action="grill the failed capability backward review into an affected child, sibling gap, or subtree rebuild target",
                    capability_backward_issue_grilled=True,
                )
                return
            if (
                state.pm_repair_decision_interrogations
                <= state.capability_structural_route_repairs
            ):
                yield _step(
                    state,
                    label="pm_repair_decision_interrogated",
                    action="grill the project manager on capability repair strategy before choosing child rework, sibling insertion, or subtree rebuild",
                    pm_repair_decision_interrogations=(
                        state.pm_repair_decision_interrogations + 1
                    ),
                )
                return

            reset_changes = _reset_execution_quality_gates()
            route_changes = _capability_structural_repair_changes(state)
            if state.capability_backward_issue_strategy == "existing_child":
                yield _step(
                    state,
                    label="capability_route_updated_to_rework_child_node",
                    action="mutate the capability route back to the affected existing child node and invalidate the parent rollup",
                    **route_changes,
                    **reset_changes,
                )
                return
            if state.capability_backward_issue_strategy == "add_sibling":
                yield _step(
                    state,
                    label="capability_route_updated_to_add_sibling_child_node",
                    action="mutate the capability route to add an adjacent sibling child node before parent closure",
                    capability_new_sibling_nodes=state.capability_new_sibling_nodes + 1,
                    **route_changes,
                    **reset_changes,
                )
                return
            yield _step(
                state,
                label="capability_route_updated_to_rebuild_child_subtree",
                action="mutate the capability route to rebuild the child subtree from the capability product model",
                capability_subtree_rebuilds=state.capability_subtree_rebuilds + 1,
                **route_changes,
                **reset_changes,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_state:
            yield _step(
                state,
                label="heartbeat_loaded_state",
                action="continuation turn loads local state, active route, capability evidence, latest heartbeat or manual-resume evidence, lifecycle evidence, and crew ledger",
                heartbeat_loaded_state=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_frontier:
            yield _step(
                state,
                label="heartbeat_loaded_execution_frontier",
                action="continuation turn loads execution_frontier.json before selecting capability work",
                heartbeat_loaded_frontier=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_packet_ledger:
            yield _step(
                state,
                label="heartbeat_loaded_packet_ledger",
                action="continuation turn loads packet_ledger.json before asking PM or dispatching capability work",
                heartbeat_loaded_packet_ledger=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_loaded_crew_memory:
            yield _step(
                state,
                label="heartbeat_loaded_crew_memory",
                action="continuation turn loads all six compact role memory packets before restoring or replacing crew roles",
                heartbeat_loaded_crew_memory=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_restored_crew:
            yield _step(
                state,
                label="heartbeat_restored_six_agent_crew",
                action="continuation turn restores live crew roles when available and prepares memory-seeded replacements otherwise",
                heartbeat_restored_crew=True,
                replacement_roles_seeded_from_memory=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_rehydrated_crew:
            yield _step(
                state,
                label="heartbeat_rehydrated_six_agent_crew",
                action="rehydrate the six FlowPilot roles from role memory packets before asking the project manager for the next capability runway",
                heartbeat_rehydrated_crew=True,
            )
            return

        if _route_scaffold_ready(state) and not state.crew_rehydration_report_written:
            yield _step(
                state,
                label="crew_rehydration_report_written",
                action="write the six-role rehydration report with restored, replaced, blocked, and memory-seeded role status before any PM resume decision",
                crew_rehydration_report_written=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_pm_decision_requested:
            yield _step(
                state,
                label="heartbeat_asked_project_manager",
                action="continuation turn asks the project manager for PM_DECISION from the current frontier and packet ledger",
                heartbeat_pm_decision_requested=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_pm_controller_reminder_checked:
            yield _step(
                state,
                label="heartbeat_pm_controller_reminder_checked",
                action="controller requires PM_DECISION to include controller_reminder before dispatching any capability packet",
                heartbeat_pm_controller_reminder_checked=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_reviewer_dispatch_policy_checked:
            yield _step(
                state,
                label="heartbeat_reviewer_dispatch_policy_checked",
                action="controller confirms NODE_PACKET dispatch requires reviewer approval and ambiguous worker state blocks controller execution",
                heartbeat_reviewer_dispatch_policy_checked=True,
            )
            return

        if _route_scaffold_ready(state) and not state.pm_resume_decision_recorded:
            yield _step(
                state,
                label="pm_resume_completion_runway_recorded",
                action="project manager records a completion-oriented capability runway from the current gate toward completion, including hard stops and checkpoint cadence",
                pm_resume_decision_recorded=True,
                pm_completion_runway_recorded=True,
                pm_runway_hard_stops_recorded=True,
                pm_runway_checkpoint_cadence_recorded=True,
            )
            return

        if _route_scaffold_ready(state) and not state.pm_runway_synced_to_plan:
            yield _step(
                state,
                label="pm_runway_synced_to_visible_plan",
                action="controller calls the host native plan tool when available, or records the fallback method, and replaces the visible capability plan with a downstream PM runway projection",
                pm_runway_synced_to_plan=True,
                plan_sync_method_recorded=True,
                visible_plan_has_runway_depth=True,
            )
            return

        if _route_scaffold_ready(state) and not state.heartbeat_health_checked:
            yield _step(
                state,
                label="continuation_resume_ready_checked",
                action="check automated heartbeat health when supported, or check manual-resume state/frontier/crew-memory readiness when no real wakeup exists",
                heartbeat_health_checked=True,
            )
            return

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
                action="enter the current child node and find a bounded sidecar task with no existing idle subagent",
                child_node_sidecar_scan_done=True,
                sidecar_need="needed",
                subagent_pool_exists=False,
                subagent_idle_available=False,
            )
            yield _step(
                state,
                label="child_node_sidecar_scan_need_found_existing_idle",
                action="enter the current child node and find a bounded sidecar task plus an existing idle subagent",
                child_node_sidecar_scan_done=True,
                sidecar_need="needed",
                subagent_pool_exists=True,
                subagent_idle_available=True,
                subagent_status="idle",
            )
            return

        if (
            _base_ready(state)
            and state.sidecar_need == "needed"
            and not state.subagent_scope_checked
        ):
            yield _step(
                state,
                label="sidecar_scope_checked",
                action="confirm the sidecar task is bounded, non-blocking, and disjoint from node ownership and route advancement",
                subagent_scope_checked=True,
            )
            return

        if (
            _base_ready(state)
            and state.sidecar_need == "needed"
            and state.subagent_scope_checked
            and state.subagent_status in {"none", "idle"}
        ):
            if state.subagent_pool_exists and state.subagent_idle_available:
                yield _step(
                    state,
                    label="idle_subagent_reused",
                    action="reuse an existing idle subagent for the child-node sidecar task",
                    subagent_status="pending",
                    subagent_idle_available=False,
                )
            else:
                yield _step(
                    state,
                    label="subagent_spawned_on_demand",
                    action="spawn a subagent only after the current child node has a bounded sidecar task and no suitable idle subagent exists",
                    subagent_pool_exists=True,
                    subagent_status="pending",
                )
            return

        if state.subagent_status == "pending":
            yield _step(
                state,
                label="sidecar_report_returned",
                action="sidecar subagent returns findings, evidence, changed paths if any, risks, and suggestions",
                subagent_status="returned",
            )
            return

        if state.subagent_status == "returned":
            yield _step(
                state,
                label="authorized_integration_review_packet_completed",
                action="authorized integration/review packet verifies the sidecar result while PM keeps node ownership",
                sidecar_need="none",
                subagent_status="idle",
                subagent_idle_available=True,
            )
            return

        if not _base_ready(state) or not _subagent_clear(state):
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
                    capability_route_process_officer_approved=False,
                    capability_product_function_model_checked=False,
                    capability_product_function_model_product_officer_approved=False,
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
                    child_skill_manifest_process_officer_approved=False,
                    child_skill_manifest_product_officer_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    child_skill_contracts_loaded=False,
                    child_skill_focused_interrogation_done=False,
                    child_skill_focused_interrogation_questions=0,
                    child_skill_focused_interrogation_scope_id="",
                    child_skill_exact_source_verified=False,
                    child_skill_substitutes_rejected=False,
                    flowpilot_invocation_policy_mapped=False,
                    child_skill_requirements_mapped=False,
                    child_skill_evidence_plan_written=False,
                    child_skill_subroute_projected=False,
                    child_skill_conformance_model_checked=False,
                    child_skill_conformance_model_process_officer_approved=False,
                    strict_gate_obligation_review_model_checked=False,
                    flowguard_dependency_checked=False,
                    dependency_plan_recorded=False,
                    future_installs_deferred=False,
                    flowguard_process_design_done=False,
                    flowguard_officer_model_adversarial_probe_done=False,
                    flowguard_model_report_risk_tiers_done=False,
                    flowguard_model_report_pm_review_agenda_done=False,
                    flowguard_model_report_toolchain_recommendations_done=False,
                    flowguard_model_report_confidence_boundary_done=False,
                    meta_route_checked=False,
                    meta_route_process_officer_approved=False,
                    subagent_status="none",
                    heartbeat_health_checked=False,
                    quality_route_raises=state.quality_route_raises + 1,
                    **_reset_execution_quality_gates(),
                )
            return

        if state.task_kind == "backend":
            if not state.non_ui_implemented:
                yield _step(
                    state,
                    label="non_ui_implemented",
                    action="implement non-UI project chunk",
                    non_ui_implemented=True,
                    role_memory_refreshed_after_work=False,
                )
                return
            if not state.child_skill_execution_evidence_audited:
                yield _step(
                    state,
                    label="child_skill_execution_evidence_audited",
                    action="audit child-skill step evidence against mapped requirements",
                    child_skill_execution_evidence_audited=True,
                )
                return
            if not state.child_skill_evidence_matches_outputs:
                yield _step(
                    state,
                    label="child_skill_evidence_matches_outputs",
                    action="confirm child-skill evidence matches actual outputs",
                    child_skill_evidence_matches_outputs=True,
                )
                return
            if not state.child_skill_domain_quality_checked:
                yield _step(
                    state,
                    label="child_skill_domain_quality_checked",
                    action="check child-skill output quality against parent node goal",
                    child_skill_domain_quality_checked=True,
                )
                return
            if not state.child_skill_iteration_loop_closed:
                yield _step(
                    state,
                    label="child_skill_iteration_loop_closed",
                    action="close child-skill iteration loop before final verification",
                    child_skill_iteration_loop_closed=True,
                )
                return
            if not state.current_node_skill_improvement_check_done:
                yield _step(
                    state,
                    label="skill_improvement_observation_check_no_issue",
                    action="PM asks the backend capability roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found",
                    current_node_skill_improvement_check_done=True,
                )
                yield _step(
                    state,
                    label="skill_improvement_observation_logged",
                    action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance while continuing the backend project",
                    current_node_skill_improvement_check_done=True,
                    flowpilot_improvement_live_report_updated=True,
                )
                return
            if not state.role_memory_refreshed_after_work:
                yield _step(
                    state,
                    label="role_memory_packets_refreshed_after_capability_work",
                    action="refresh compact role memory packets after backend implementation evidence and before final verification",
                    role_memory_refreshed_after_work=True,
                )
                return
            if not state.final_verification_done:
                yield _step(
                    state,
                    label="final_verification_done",
                    action="run final verification",
                    final_verification_done=True,
                )
                return
            if not state.anti_rough_finish_done:
                yield _step(
                    state,
                    label="anti_rough_finish_passed",
                    action="review the verified backend result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                    anti_rough_finish_done=True,
                )
                if (
                    state.quality_reworks < MAX_QUALITY_REWORKS
                    and state.standard_expansions == 0
                ):
                    yield _step(
                        state,
                        label="anti_rough_finish_found_rework",
                        action="record bounded backend rework because the route is still too thin or weakly evidenced",
                        non_ui_implemented=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        final_verification_done=False,
                        heartbeat_health_checked=False,
                        quality_reworks=state.quality_reworks + 1,
                        **_reset_execution_quality_gates(),
                    )
                return
            if not state.worker_output_ready_for_review:
                yield _step(
                    state,
                    label="worker_output_ready_for_review",
                    action="record that backend worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                    worker_output_ready_for_review=True,
                )
                return
            if not state.pm_review_release_order_written:
                yield _step(
                    state,
                    label="pm_review_release_order_written",
                    action="project manager writes the backend review release order naming the gate, evidence paths, reviewer scope, and required inspections",
                    pm_review_release_order_written=True,
                )
                return
            if not state.pm_released_reviewer_for_current_gate:
                yield _step(
                    state,
                    label="pm_released_reviewer_for_current_gate",
                    action="project manager explicitly releases the reviewer to start backend inspection after worker output is ready",
                    pm_released_reviewer_for_current_gate=True,
                )
                return
            if not state.packet_runtime_physical_files_written:
                yield _step(
                    state,
                    label="packet_runtime_physical_isolation_verified",
                    action="packet runtime writes backend physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                    packet_runtime_physical_files_written=True,
                    controller_context_body_exclusion_verified=True,
                )
                return
            if not state.packet_mail_chain_audit_done:
                yield _step(
                    state,
                    label="controller_mail_relay_chain_audit_done",
                    action="reviewer verifies backend packet/result controller relay signatures, recipient pre-open checks, no private role-to-role mail, and PM restart/repair/reissue handling for unopened or contaminated mail",
                    controller_relay_signature_audit_done=True,
                    recipient_pre_open_relay_check_done=True,
                    packet_mail_chain_audit_done=True,
                    unopened_mail_pm_recovery_policy_recorded=True,
                )
                return
            if not state.packet_envelope_body_audit_done:
                yield _step(
                    state,
                    label="packet_envelope_body_audit_done",
                    action="human-like reviewer checks backend packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content inspection",
                    packet_envelope_body_audit_done=True,
                    packet_envelope_to_role_checked=True,
                    packet_body_hash_verified=True,
                    result_envelope_checked=True,
                    result_body_hash_verified=True,
                    completed_agent_id_role_verified=True,
                    controller_body_boundary_verified=True,
                    wrong_role_relabel_forbidden_verified=True,
                )
                return
            if not state.packet_role_origin_audit_done:
                yield _step(
                    state,
                    label="packet_role_origin_audit_done",
                    action="human-like reviewer verifies every backend packet's PM author, reviewer dispatch, assigned worker, and actual result author after envelope/body integrity passes",
                    packet_role_origin_audit_done=True,
                    packet_result_author_verified=True,
                    packet_result_author_matches_assignment=True,
                )
                return
            if not state.implementation_human_review_context_loaded:
                yield _step(
                    state,
                    label="implementation_human_review_context_loaded",
                    action="load backend product model, outputs, logs, evidence, and acceptance context for human-like inspection",
                    implementation_human_review_context_loaded=True,
                )
                return
            if not state.implementation_human_neutral_observation_written:
                yield _step(
                    state,
                    label="implementation_human_neutral_observation_written",
                    action="write a neutral observation of backend outputs and behavior before pass/fail inspection judgement",
                    implementation_human_neutral_observation_written=True,
                )
                return
            if not state.implementation_human_manual_experiments_run:
                yield _step(
                    state,
                    label="implementation_human_manual_experiments_run",
                    action="exercise the backend behavior or inspect representative data like a human reviewer",
                    implementation_human_manual_experiments_run=True,
                )
                return
            if not state.implementation_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="implementation_reviewer_independent_probe_done",
                    action="human-like reviewer attacks backend evidence with direct probes, checked state/log references, and report-only failure hypotheses before approval",
                    implementation_reviewer_independent_probe_done=True,
                )
                return
            if not state.implementation_human_inspection_passed:
                yield _step(
                    state,
                    label="implementation_human_inspection_passed",
                    action="human-like reviewer accepts the backend product behavior from independent adversarial inspection evidence",
                    implementation_human_inspection_passed=True,
                    implementation_human_review_reviewer_approved=True,
                )
                return
            capability_backward_steps = tuple(
                _capability_backward_review_steps(state, domain="backend")
            )
            if capability_backward_steps:
                yield from capability_backward_steps
                return
            if not state.child_skill_current_gates_role_approved:
                if not state.current_child_skill_gate_independent_validation_done:
                    yield _step(
                        state,
                        label="current_child_skill_gate_independent_validation_done",
                        action="required child-skill approvers run independent probes and cite concrete evidence before closing current backend child-skill gates",
                        current_child_skill_gate_independent_validation_done=True,
                    )
                    return
                yield _step(
                    state,
                    label="child_skill_current_gates_role_approved",
                    action="required reviewer, process officer, product officer, or PM approvals close the current child-skill gates; controller drafts are not approvals",
                    child_skill_current_gates_role_approved=True,
                )
                return
            if not state.child_skill_completion_verified:
                yield _step(
                    state,
                    label="child_skill_completion_verified",
                    action="verify invoked child skills met their own completion standards",
                    child_skill_completion_verified=True,
                )
                return
            if not state.completion_visible_user_flow_diagram_emitted:
                yield _step(
                    state,
                    label="completion_visible_user_flow_diagram_emitted",
                    action="emit visible completion user flow diagram before backend route close",
                    completion_visible_user_flow_diagram_emitted=True,
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review backend feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review backend acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                )
                return
            if not state.final_standard_scenario_pack_replayed:
                yield _step(
                    state,
                    label="final_standard_scenario_pack_replayed",
                    action="replay the standard scenario pack and backend node-risk scenarios against the final product before completion closure",
                    final_standard_scenario_pack_replayed=True,
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize backend quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                )
                return
            if not state.final_product_model_officer_adversarial_probe_done:
                yield _step(
                    state,
                    label="final_product_model_officer_adversarial_probe_done",
                    action="product FlowGuard officer adversarially rechecks final backend product model replay, state fields, counterexamples, counts, and blindspots before approval",
                    final_product_model_officer_adversarial_probe_done=True,
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer approves backend final behavior from adversarial model replay evidence",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final backend output, evidence, acceptance, and product model for completion inspection",
                    final_human_review_context_loaded=True,
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of final backend artifacts before completion judgement",
                    final_human_neutral_observation_written=True,
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="run final human-like backend experiments before completion grill-me",
                    final_human_manual_experiments_run=True,
                )
                return
            if not state.final_human_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="final_human_reviewer_independent_probe_done",
                    action="final human-like reviewer attacks backend completion with direct probes, state/log references, missing-gate hypotheses, and report-only checks",
                    final_human_reviewer_independent_probe_done=True,
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts backend product completeness from independent adversarial inspection evidence",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer before backend route close",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_capability_gap_found",
                        action="raise backend capability standard and recheck route",
                        capability_route_version=state.capability_route_version + 1,
                        capability_route_checked=False,
                        capability_route_process_officer_approved=False,
                        capability_product_function_model_checked=False,
                        capability_product_function_model_product_officer_approved=False,
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
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        child_skill_contracts_loaded=False,
                        child_skill_focused_interrogation_done=False,
                        child_skill_focused_interrogation_questions=0,
                        child_skill_focused_interrogation_scope_id="",
                        child_skill_exact_source_verified=False,
                        child_skill_substitutes_rejected=False,
                        flowpilot_invocation_policy_mapped=False,
                        child_skill_requirements_mapped=False,
                        child_skill_evidence_plan_written=False,
                        child_skill_subroute_projected=False,
                        child_skill_conformance_model_checked=False,
                        child_skill_conformance_model_process_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        flowguard_dependency_checked=False,
                        dependency_plan_recorded=False,
                        future_installs_deferred=False,
                        flowguard_process_design_done=False,
                        flowguard_officer_model_adversarial_probe_done=False,
                        flowguard_model_report_risk_tiers_done=False,
                        flowguard_model_report_pm_review_agenda_done=False,
                        flowguard_model_report_toolchain_recommendations_done=False,
                        flowguard_model_report_confidence_boundary_done=False,
                        meta_route_checked=False,
                        meta_route_process_officer_approved=False,
                        subagent_status="none",
                        non_ui_implemented=False,
                        final_verification_done=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_visible_user_flow_diagram_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_quality_candidate_review_done=False,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        terminal_lifecycle_frontier_written=False,
                        standard_expansions=state.standard_expansions + 1,
                        **_reset_execution_quality_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                )
                return
            final_ledger_steps = tuple(
                _final_route_wide_gate_ledger_steps(state, domain="backend")
            )
            if final_ledger_steps:
                yield from final_ledger_steps
                return
            if not state.terminal_closure_suite_run:
                yield _step(
                    state,
                    label="terminal_closure_suite_run",
                    action="run terminal closure suite after backend final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                    terminal_closure_suite_run=True,
                )
                return
            if not state.terminal_state_and_evidence_refreshed:
                yield _step(
                    state,
                    label="terminal_state_and_evidence_refreshed",
                    action="refresh backend terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route close",
                    terminal_state_and_evidence_refreshed=True,
                )
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex heartbeat automations, local state, and execution frontier before backend route close",
                    lifecycle_reconciliation_done=True,
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write terminal heartbeat lifecycle back to execution frontier before route close",
                    terminal_lifecycle_frontier_written=True,
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive compact role memory packets with final capability statuses before backend route close",
                    crew_memory_archived=True,
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger after role memory and backend lifecycle reconciliation",
                    crew_archived=True,
                )
                return
            if not state.flowpilot_skill_improvement_report_written:
                yield _step(
                    state,
                    label="flowpilot_skill_improvement_report_written",
                    action="PM writes a nonblocking FlowPilot skill improvement report from backend capability observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                    flowpilot_skill_improvement_report_written=True,
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves backend completion after final reviews and lifecycle cleanup",
                    pm_completion_decision_recorded=True,
                )
                return
            yield _step(
                state,
                label="completed",
                action="complete backend project route and emit terminal completion notice",
                status="complete",
                terminal_completion_notice_recorded=True,
            )
            return

        if state.task_kind == "ui":
            if not state.ui_autonomous_pipeline_selected:
                yield _step(
                    state,
                    label="ui_autonomous_pipeline_selected",
                    action="PM selects autonomous-concept-ui-redesign as the default UI child-skill orchestrator",
                    ui_autonomous_pipeline_selected=True,
                )
                return
            if not state.ui_inspected:
                yield _step(
                    state,
                    label="ui_inspected",
                    action="autonomous UI pipeline inspects current UI/product before concept or implementation work",
                    ui_inspected=True,
                )
                return
            if not state.ui_concept_done:
                yield _step(
                    state,
                    label="ui_concept_done",
                    action="run autonomous UI pipeline product framing and concept-led design contract gate",
                    ui_concept_done=True,
                )
                return
            if not state.ui_concept_target_ready:
                yield _step(
                    state,
                    label="ui_concept_target_ready",
                    action="record the source UI skill's pre-implementation concept-target or reference decision",
                    ui_concept_target_ready=True,
                )
                return
            if not state.ui_concept_target_visible:
                yield _step(
                    state,
                    label="ui_concept_target_visible",
                    action="show the source UI skill's target/reference decision or record its waiver before implementation planning",
                    ui_concept_target_visible=True,
                )
                return
            if not state.ui_concept_personal_visual_review_done:
                yield _step(
                    state,
                    label="ui_concept_personal_visual_review_done",
                    action="human-like reviewer personally inspects the concept image instead of relying on a worker summary",
                    ui_concept_personal_visual_review_done=True,
                )
                return
            if not state.ui_concept_design_recommendations_recorded:
                yield _step(
                    state,
                    label="ui_concept_design_recommendations_recorded",
                    action="human-like reviewer records concrete concept improvement ideas or states why no concept repair is needed",
                    ui_concept_design_recommendations_recorded=True,
                )
                return
            if not state.ui_concept_aesthetic_review_done:
                yield _step(
                    state,
                    label="ui_concept_aesthetic_review_passed",
                    action="human-like reviewer records aesthetic verdict and concrete reasons for concept beauty, weakness, or polish before implementation planning",
                    ui_concept_aesthetic_review_done=True,
                    ui_concept_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_concept_aesthetic_review_failed",
                        action="human-like reviewer rejects the concept aesthetics with concrete ugly/weak reasons and sends it back for concept regeneration",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_personal_visual_review_done=False,
                        ui_concept_design_recommendations_recorded=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_personal_visual_review_done=False,
                        visual_asset_design_recommendations_recorded=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_frontend_design_plan_done:
                yield _step(
                    state,
                    label="ui_frontend_design_plan_done",
                    action="autonomous UI pipeline briefs frontend-design for implementation planning",
                    ui_frontend_design_plan_done=True,
                )
                return
            if state.visual_asset_scope == "unknown":
                yield _step(
                    state,
                    label="visual_asset_not_required",
                    action="record that this UI route has no app icon or product imagery changes",
                    visual_asset_scope="none",
                )
                yield _step(
                    state,
                    label="visual_asset_required",
                    action="record that this UI route creates app icons or product imagery",
                    visual_asset_scope="required",
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_style_review_done
            ):
                yield _step(
                    state,
                    label="visual_asset_style_review_done",
                    action="record source UI skill evidence for in-scope product-facing visual assets",
                    visual_asset_style_review_done=True,
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_personal_visual_review_done
            ):
                yield _step(
                    state,
                    label="visual_asset_personal_visual_review_done",
                    action="human-like reviewer personally inspects product-facing visual assets instead of relying on an asset report",
                    visual_asset_personal_visual_review_done=True,
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_design_recommendations_recorded
            ):
                yield _step(
                    state,
                    label="visual_asset_design_recommendations_recorded",
                    action="human-like reviewer records concrete visual-asset improvement ideas or states why no asset repair is needed",
                    visual_asset_design_recommendations_recorded=True,
                )
                return
            if (
                state.visual_asset_scope == "required"
                and not state.visual_asset_aesthetic_review_done
            ):
                yield _step(
                    state,
                    label="visual_asset_aesthetic_review_passed",
                    action="human-like reviewer records app-icon or visual-asset aesthetic verdict with concrete reasons before UI implementation",
                    visual_asset_aesthetic_review_done=True,
                    visual_asset_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="visual_asset_aesthetic_review_failed",
                        action="human-like reviewer rejects app-icon or visual-asset aesthetics with concrete ugly/weak reasons and sends it back for regeneration",
                        visual_asset_style_review_done=False,
                        visual_asset_personal_visual_review_done=False,
                        visual_asset_design_recommendations_recorded=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_implemented:
                yield _step(
                    state,
                    label="ui_implemented",
                    action="implement UI using local architecture",
                    ui_implemented=True,
                    role_memory_refreshed_after_work=False,
                )
                return
            if not state.ui_screenshot_qa_done:
                yield _step(
                    state,
                    label="ui_screenshot_qa_done",
                    action="run rendered screenshot QA after autonomous UI implementation",
                    ui_screenshot_qa_done=True,
                )
                return
            if not state.ui_geometry_qa_done:
                yield _step(
                    state,
                    label="ui_geometry_qa_done",
                    action="run autonomous UI geometry QA for text overflow, overlap, viewport fit, and high-DPI/window-size risks",
                    ui_geometry_qa_done=True,
                )
                return
            if not state.ui_reviewer_personal_walkthrough_done:
                yield _step(
                    state,
                    label="ui_reviewer_personal_walkthrough_done",
                    action="human-like reviewer personally launches or opens the UI and walks through rendered states instead of reading the QA report only",
                    ui_reviewer_personal_walkthrough_done=True,
                )
                return
            if not state.ui_interaction_reachability_checked:
                yield _step(
                    state,
                    label="ui_interaction_reachability_checked",
                    action="human-like reviewer personally checks clicks, tabs, language switching, settings, support, tray lifecycle, and required interactive reachability",
                    ui_interaction_reachability_checked=True,
                )
                return
            if not state.ui_layout_overlap_density_checked:
                yield _step(
                    state,
                    label="ui_layout_overlap_density_checked",
                    action="human-like reviewer personally checks text overlap, clipping, whitespace, density, crowded controls, hierarchy, and responsive layout fit",
                    ui_layout_overlap_density_checked=True,
                )
                return
            if not state.ui_reviewer_design_recommendations_recorded:
                yield _step(
                    state,
                    label="ui_reviewer_design_recommendations_recorded",
                    action="human-like reviewer records concrete UI repair or enhancement suggestions before passing aesthetic/divergence closure",
                    ui_reviewer_design_recommendations_recorded=True,
                )
                return
            if not state.ui_implementation_aesthetic_review_done:
                yield _step(
                    state,
                    label="ui_implementation_aesthetic_review_passed",
                    action="human-like reviewer records rendered UI aesthetic verdict with concrete reasons before divergence closure",
                    ui_implementation_aesthetic_review_done=True,
                    ui_implementation_aesthetic_reasons_recorded=True,
                )
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_implementation_aesthetic_review_failed",
                        action="human-like reviewer rejects rendered UI aesthetics with concrete ugly/weak reasons and sends it back for UI repair",
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_geometry_qa_done=False,
                        ui_reviewer_personal_walkthrough_done=False,
                        ui_interaction_reachability_checked=False,
                        ui_layout_overlap_density_checked=False,
                        ui_reviewer_design_recommendations_recorded=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                return
            if not state.ui_divergence_review_done:
                yield _step(
                    state,
                    label="ui_divergence_review_done",
                    action="record the source UI skill's divergence or comparison decision",
                    ui_divergence_review_done=True,
                )
                return
            if not state.ui_visual_iteration_loop_closed:
                if state.ui_visual_iterations < MAX_UI_VISUAL_ITERATIONS:
                    yield _step(
                        state,
                        label="ui_visual_iteration_needed",
                        action="rerun UI child-skill work after its loop decision changes required evidence",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_personal_visual_review_done=False,
                        ui_concept_design_recommendations_recorded=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_personal_visual_review_done=False,
                        visual_asset_design_recommendations_recorded=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_geometry_qa_done=False,
                        ui_reviewer_personal_walkthrough_done=False,
                        ui_interaction_reachability_checked=False,
                        ui_layout_overlap_density_checked=False,
                        ui_reviewer_design_recommendations_recorded=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        ui_visual_iterations=state.ui_visual_iterations + 1,
                    )
                yield _step(
                    state,
                    label="ui_visual_iteration_loop_closed",
                    action="record the source UI skill's loop-closure decision",
                    ui_visual_iteration_loop_closed=True,
                )
                return
            if not state.child_skill_execution_evidence_audited:
                yield _step(
                    state,
                    label="child_skill_execution_evidence_audited",
                    action="audit UI child-skill step evidence against mapped requirements",
                    child_skill_execution_evidence_audited=True,
                )
                return
            if not state.child_skill_evidence_matches_outputs:
                yield _step(
                    state,
                    label="child_skill_evidence_matches_outputs",
                    action="confirm UI child-skill evidence matches actual rendered outputs",
                    child_skill_evidence_matches_outputs=True,
                )
                return
            if not state.child_skill_domain_quality_checked:
                yield _step(
                    state,
                    label="child_skill_domain_quality_checked",
                    action="check UI child-skill output quality against parent node goal",
                    child_skill_domain_quality_checked=True,
                )
                return
            if not state.child_skill_iteration_loop_closed:
                yield _step(
                    state,
                    label="child_skill_iteration_loop_closed",
                    action="close UI child-skill conformance loop before final verification",
                    child_skill_iteration_loop_closed=True,
                )
                return
            if not state.current_node_skill_improvement_check_done:
                yield _step(
                    state,
                    label="skill_improvement_observation_check_no_issue",
                    action="PM asks the UI capability roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found",
                    current_node_skill_improvement_check_done=True,
                )
                yield _step(
                    state,
                    label="skill_improvement_observation_logged",
                    action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance while continuing the UI project",
                    current_node_skill_improvement_check_done=True,
                    flowpilot_improvement_live_report_updated=True,
                )
                return
            if not state.role_memory_refreshed_after_work:
                yield _step(
                    state,
                    label="role_memory_packets_refreshed_after_capability_work",
                    action="refresh compact role memory packets after UI implementation evidence and before final verification",
                    role_memory_refreshed_after_work=True,
                )
                return
            if not state.final_verification_done:
                yield _step(
                    state,
                    label="final_verification_done",
                    action="run final functional and visual verification",
                    final_verification_done=True,
                )
                return
            if not state.anti_rough_finish_done:
                yield _step(
                    state,
                    label="anti_rough_finish_passed",
                    action="review the verified UI result for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                    anti_rough_finish_done=True,
                )
                if (
                    state.quality_reworks < MAX_QUALITY_REWORKS
                    and state.standard_expansions == 0
                ):
                    yield _step(
                        state,
                        label="anti_rough_finish_found_rework",
                        action="record bounded UI rework because the route is still too thin or weakly evidenced",
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_geometry_qa_done=False,
                        ui_reviewer_personal_walkthrough_done=False,
                        ui_interaction_reachability_checked=False,
                        ui_layout_overlap_density_checked=False,
                        ui_reviewer_design_recommendations_recorded=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        ui_visual_iteration_loop_closed=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        final_verification_done=False,
                        heartbeat_health_checked=False,
                        quality_reworks=state.quality_reworks + 1,
                        **_reset_execution_quality_gates(),
                    )
                return
            if not state.worker_output_ready_for_review:
                yield _step(
                    state,
                    label="worker_output_ready_for_review",
                    action="record that UI worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                    worker_output_ready_for_review=True,
                )
                return
            if not state.pm_review_release_order_written:
                yield _step(
                    state,
                    label="pm_review_release_order_written",
                    action="project manager writes the UI review release order naming the gate, evidence paths, reviewer scope, and required inspections",
                    pm_review_release_order_written=True,
                )
                return
            if not state.pm_released_reviewer_for_current_gate:
                yield _step(
                    state,
                    label="pm_released_reviewer_for_current_gate",
                    action="project manager explicitly releases the reviewer to start UI inspection after worker output is ready",
                    pm_released_reviewer_for_current_gate=True,
                )
                return
            if not state.packet_runtime_physical_files_written:
                yield _step(
                    state,
                    label="packet_runtime_physical_isolation_verified",
                    action="packet runtime writes UI physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                    packet_runtime_physical_files_written=True,
                    controller_context_body_exclusion_verified=True,
                )
                return
            if not state.packet_mail_chain_audit_done:
                yield _step(
                    state,
                    label="controller_mail_relay_chain_audit_done",
                    action="reviewer verifies UI packet/result controller relay signatures, recipient pre-open checks, no private role-to-role mail, and PM restart/repair/reissue handling for unopened or contaminated mail",
                    controller_relay_signature_audit_done=True,
                    recipient_pre_open_relay_check_done=True,
                    packet_mail_chain_audit_done=True,
                    unopened_mail_pm_recovery_policy_recorded=True,
                )
                return
            if not state.packet_envelope_body_audit_done:
                yield _step(
                    state,
                    label="packet_envelope_body_audit_done",
                    action="human-like reviewer checks UI packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content inspection",
                    packet_envelope_body_audit_done=True,
                    packet_envelope_to_role_checked=True,
                    packet_body_hash_verified=True,
                    result_envelope_checked=True,
                    result_body_hash_verified=True,
                    completed_agent_id_role_verified=True,
                    controller_body_boundary_verified=True,
                    wrong_role_relabel_forbidden_verified=True,
                )
                return
            if not state.packet_role_origin_audit_done:
                yield _step(
                    state,
                    label="packet_role_origin_audit_done",
                    action="human-like reviewer verifies every UI packet's PM author, reviewer dispatch, assigned worker, and actual result author after envelope/body integrity passes",
                    packet_role_origin_audit_done=True,
                    packet_result_author_verified=True,
                    packet_result_author_matches_assignment=True,
                )
                return
            if not state.implementation_human_review_context_loaded:
                yield _step(
                    state,
                    label="implementation_human_review_context_loaded",
                    action="load UI product model, screenshots, concept target, interaction evidence, and acceptance context for human-like inspection",
                    implementation_human_review_context_loaded=True,
                )
                return
            if not state.implementation_human_neutral_observation_written:
                yield _step(
                    state,
                    label="implementation_human_neutral_observation_written",
                    action="write a neutral observation of the UI screenshot and exercised states before pass/fail inspection judgement",
                    implementation_human_neutral_observation_written=True,
                )
                return
            if not state.implementation_human_manual_experiments_run:
                yield _step(
                    state,
                    label="implementation_human_manual_experiments_run",
                    action="operate the UI like a human reviewer before accepting UI evidence",
                    implementation_human_manual_experiments_run=True,
                )
                return
            if not state.implementation_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="implementation_reviewer_independent_probe_done",
                    action="human-like reviewer attacks UI evidence with direct operation, screenshots, state references, reachability, layout, aesthetics, and report-only failure hypotheses before approval",
                    implementation_reviewer_independent_probe_done=True,
                )
                return
            if not state.implementation_human_inspection_passed:
                yield _step(
                    state,
                    label="implementation_human_inspection_passed",
                    action="human-like reviewer accepts the UI product behavior, visual quality, and evidence from independent adversarial inspection evidence",
                    implementation_human_inspection_passed=True,
                    implementation_human_review_reviewer_approved=True,
                )
                return
            capability_backward_steps = tuple(
                _capability_backward_review_steps(state, domain="UI")
            )
            if capability_backward_steps:
                yield from capability_backward_steps
                return
            if not state.child_skill_current_gates_role_approved:
                if not state.current_child_skill_gate_independent_validation_done:
                    yield _step(
                        state,
                        label="current_child_skill_gate_independent_validation_done",
                        action="required child-skill approvers run independent probes and cite concrete evidence before closing current UI child-skill gates",
                        current_child_skill_gate_independent_validation_done=True,
                    )
                    return
                yield _step(
                    state,
                    label="child_skill_current_gates_role_approved",
                    action="required reviewer, process officer, product officer, or PM approvals close the current UI child-skill gates; controller drafts are not approvals",
                    child_skill_current_gates_role_approved=True,
                )
                return
            if not state.child_skill_completion_verified:
                yield _step(
                    state,
                    label="child_skill_completion_verified",
                    action="verify invoked child skills met their own completion standards",
                    child_skill_completion_verified=True,
                )
                return
            if not state.completion_visible_user_flow_diagram_emitted:
                yield _step(
                    state,
                    label="completion_visible_user_flow_diagram_emitted",
                    action="emit visible completion user flow diagram before UI route close",
                    completion_visible_user_flow_diagram_emitted=True,
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review UI feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review UI acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                )
                return
            if not state.final_standard_scenario_pack_replayed:
                yield _step(
                    state,
                    label="final_standard_scenario_pack_replayed",
                    action="replay the standard scenario pack and UI node-risk scenarios against the final product before completion closure",
                    final_standard_scenario_pack_replayed=True,
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize UI quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                )
                return
            if not state.final_product_model_officer_adversarial_probe_done:
                yield _step(
                    state,
                    label="final_product_model_officer_adversarial_probe_done",
                    action="product FlowGuard officer adversarially rechecks final UI product model replay, state fields, counterexamples, counts, and blindspots before approval",
                    final_product_model_officer_adversarial_probe_done=True,
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer approves UI final behavior from adversarial model replay evidence",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final UI screenshot, interaction evidence, concept target, acceptance, and product model for completion inspection",
                    final_human_review_context_loaded=True,
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of final UI artifacts and exercised states before completion judgement",
                    final_human_neutral_observation_written=True,
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="operate the final UI like a human reviewer before completion grill-me",
                    final_human_manual_experiments_run=True,
                )
                return
            if not state.final_human_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="final_human_reviewer_independent_probe_done",
                    action="final human-like reviewer attacks UI completion with direct operation, screenshots, reachability, layout, aesthetics, missing-gate hypotheses, and report-only checks",
                    final_human_reviewer_independent_probe_done=True,
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts UI product completeness and visual quality from independent adversarial inspection evidence",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer before UI route close",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_capability_gap_found",
                        action="raise UI capability standard and recheck route",
                        capability_route_version=state.capability_route_version + 1,
                        capability_route_checked=False,
                        capability_route_process_officer_approved=False,
                        capability_product_function_model_checked=False,
                        capability_product_function_model_product_officer_approved=False,
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
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        child_skill_contracts_loaded=False,
                        child_skill_focused_interrogation_done=False,
                        child_skill_focused_interrogation_questions=0,
                        child_skill_focused_interrogation_scope_id="",
                        child_skill_exact_source_verified=False,
                        child_skill_substitutes_rejected=False,
                        flowpilot_invocation_policy_mapped=False,
                        child_skill_requirements_mapped=False,
                        child_skill_evidence_plan_written=False,
                        child_skill_subroute_projected=False,
                        child_skill_conformance_model_checked=False,
                        child_skill_conformance_model_process_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        child_skill_execution_evidence_audited=False,
                        child_skill_evidence_matches_outputs=False,
                        child_skill_domain_quality_checked=False,
                        child_skill_iteration_loop_closed=False,
                        child_skill_completion_verified=False,
                        flowguard_dependency_checked=False,
                        dependency_plan_recorded=False,
                        future_installs_deferred=False,
                        flowguard_process_design_done=False,
                        flowguard_officer_model_adversarial_probe_done=False,
                        flowguard_model_report_risk_tiers_done=False,
                        flowguard_model_report_pm_review_agenda_done=False,
                        flowguard_model_report_toolchain_recommendations_done=False,
                        flowguard_model_report_confidence_boundary_done=False,
                        meta_route_checked=False,
                        meta_route_process_officer_approved=False,
                        subagent_status="none",
                        ui_concept_target_ready=False,
                        ui_concept_target_visible=False,
                        ui_concept_personal_visual_review_done=False,
                        ui_concept_design_recommendations_recorded=False,
                        ui_concept_aesthetic_review_done=False,
                        ui_concept_aesthetic_reasons_recorded=False,
                        ui_frontend_design_plan_done=False,
                        visual_asset_scope="unknown",
                        visual_asset_style_review_done=False,
                        visual_asset_personal_visual_review_done=False,
                        visual_asset_design_recommendations_recorded=False,
                        visual_asset_aesthetic_review_done=False,
                        visual_asset_aesthetic_reasons_recorded=False,
                        ui_implemented=False,
                        ui_screenshot_qa_done=False,
                        ui_geometry_qa_done=False,
                        ui_reviewer_personal_walkthrough_done=False,
                        ui_interaction_reachability_checked=False,
                        ui_layout_overlap_density_checked=False,
                        ui_reviewer_design_recommendations_recorded=False,
                        ui_implementation_aesthetic_review_done=False,
                        ui_implementation_aesthetic_reasons_recorded=False,
                        ui_divergence_review_done=False,
                        ui_visual_iteration_loop_closed=False,
                        ui_visual_iterations=0,
                        final_verification_done=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_visible_user_flow_diagram_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_quality_candidate_review_done=False,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        terminal_lifecycle_frontier_written=False,
                        standard_expansions=state.standard_expansions + 1,
                        **_reset_execution_quality_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                )
                return
            final_ledger_steps = tuple(
                _final_route_wide_gate_ledger_steps(state, domain="UI")
            )
            if final_ledger_steps:
                yield from final_ledger_steps
                return
            if not state.terminal_closure_suite_run:
                yield _step(
                    state,
                    label="terminal_closure_suite_run",
                    action="run terminal closure suite after UI final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                    terminal_closure_suite_run=True,
                )
                return
            if not state.terminal_state_and_evidence_refreshed:
                yield _step(
                    state,
                    label="terminal_state_and_evidence_refreshed",
                    action="refresh UI terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route close",
                    terminal_state_and_evidence_refreshed=True,
                )
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex heartbeat automations, local state, and execution frontier before UI route close",
                    lifecycle_reconciliation_done=True,
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write terminal heartbeat lifecycle back to execution frontier before route close",
                    terminal_lifecycle_frontier_written=True,
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive compact role memory packets with final capability statuses before UI route close",
                    crew_memory_archived=True,
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger after role memory and UI lifecycle reconciliation",
                    crew_archived=True,
                )
                return
            if not state.flowpilot_skill_improvement_report_written:
                yield _step(
                    state,
                    label="flowpilot_skill_improvement_report_written",
                    action="PM writes a nonblocking FlowPilot skill improvement report from UI capability observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                    flowpilot_skill_improvement_report_written=True,
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves UI completion after final reviews and lifecycle cleanup",
                    pm_completion_decision_recorded=True,
                )
                return
            yield _step(
                state,
                label="completed",
                action="complete UI project route and emit terminal completion notice",
                status="complete",
                terminal_completion_notice_recorded=True,
            )
            return

        yield _step(
            state,
            label="blocked_unknown_task_kind",
            action="block because task kind is unknown and emit a nonterminal resume notice",
            status="blocked",
            controlled_stop_notice_recorded=True,
            pause_snapshot_written=True,
        )


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
        and _full_interrogation_ready(
            total_questions=state.self_interrogation_questions,
            layer_count=state.self_interrogation_layer_count,
            questions_per_layer=state.self_interrogation_questions_per_layer,
            risk_family_mask=state.self_interrogation_layers,
        )
        and _crew_ready(state)
        and _product_function_architecture_ready(state)
    ):
        return InvariantResult.fail("contract frozen before fresh run isolation, showcase floor, dynamic per-layer visible self-interrogation evidence, crew recovery, PM product-function architecture, candidate pool, and validation direction")
    return InvariantResult.pass_()


def mode_choice_before_showcase_and_self_interrogation(state: State, trace) -> InvariantResult:
    del trace
    if (
        not state.startup_dialog_stopped_for_answers
        and (
            state.startup_background_agents_answered
            or state.startup_scheduled_continuation_answered
            or state.startup_display_surface_answered
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
        state.startup_background_agents_answered
        and state.startup_scheduled_continuation_answered
        and state.startup_display_surface_answered
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
            and state.heartbeat_loaded_crew_memory
            and state.heartbeat_restored_crew
            and state.heartbeat_rehydrated_crew
            and state.crew_rehydration_report_written
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
                "implementation started before continuation loaded packet ledger, rehydrated roles, checked PM controller reminder/reviewer dispatch policy, synced the PM runway, wrote node acceptance plan/risk experiments, and wrote node-level child-skill gate authority records"
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
            "capability route or implementation started before six-agent crew, fresh run isolation, PM capability decision, product-function architecture, frozen contract, dependency plan, host continuation decision, and FlowGuard process design"
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
        and state.live_subagents_started
        and not (
            state.startup_reviewer_checked_live_agent_freshness
            and state.startup_reviewer_checked_no_historical_agent_reuse
        )
    ):
        return InvariantResult.fail(
            "capability startup reviewer report counted live subagents without checking current-task freshness and historical id reuse"
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
    if state.work_beyond_startup_allowed and not _live_subagent_startup_resolved(state):
        return InvariantResult.fail(
            "PM allowed capability work before fresh current-task live subagents or explicit single-agent fallback were resolved"
        )
    if state.work_beyond_startup_allowed and state.reused_historical_agent_ids:
        return InvariantResult.fail(
            "PM allowed capability work while live-agent evidence reused historical agent ids"
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
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
        and state.child_skill_manifest_pm_approved_for_route
        and state.child_skill_focused_interrogation_done
        and _focused_interrogation_ready(
            total_questions=state.child_skill_focused_interrogation_questions,
            scope_id=state.child_skill_focused_interrogation_scope_id,
        )
        and state.child_skill_contracts_loaded
        and state.child_skill_exact_source_verified
        and state.child_skill_substitutes_rejected
        and state.flowpilot_invocation_policy_mapped
        and state.child_skill_requirements_mapped
        and state.child_skill_evidence_plan_written
        and state.child_skill_subroute_projected
        and state.child_skill_conformance_model_checked
        and state.strict_gate_obligation_review_model_checked
    ):
        return InvariantResult.fail(
            "capability work started before PM-owned child-skill gate manifest extraction, approver assignment, reviewer/officer/PM approvals, focused child-skill grill-me, exact source, substitute rejection, invocation policy, requirement mapping, evidence plan, visible child-skill mini-route, conformance model, and strict gate-obligation review model"
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
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
        and state.child_skill_current_gates_role_approved
    ):
        return InvariantResult.fail(
            "child skill completion verified before evidence audit, output match, domain quality, iteration closure, and required role approvals for current child-skill gates"
        )
    if state.final_verification_done and not (
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "final verification started before child-skill evidence audit, output match, domain quality, and iteration closure"
        )
    if state.final_verification_done and not state.validation_matrix_defined:
        return InvariantResult.fail("final verification started before validation matrix")
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
        and state.ui_frontend_design_plan_done
    ):
        return InvariantResult.fail(
            "UI implemented before inspect/concept target visibility/aesthetic/frontend design gates"
        )
    if state.ui_frontend_design_plan_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "frontend design planning started before concept aesthetic verdict and reasons"
        )
    if state.ui_concept_aesthetic_review_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "concept aesthetic review completed without reviewer personal visual review, recommendations, and concrete reasons"
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
    if state.ui_implementation_aesthetic_review_done and not (
        state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "rendered UI aesthetic review completed without reviewer personal walkthrough, reachability, layout/density checks, recommendations, screenshot QA, and concrete reasons"
        )
    if state.ui_divergence_review_done and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
    ):
        return InvariantResult.fail(
            "UI child-skill comparison reviewed before pre-implementation UI evidence, rendered QA, and aesthetic verdict"
        )
    if state.ui_visual_iteration_loop_closed and not (
        state.ui_concept_target_ready
        and state.ui_concept_target_visible
        and state.ui_screenshot_qa_done
        and state.ui_geometry_qa_done
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_divergence_review_done
    ):
        return InvariantResult.fail(
            "UI child-skill loop closed before pre-implementation UI evidence, rendered QA, aesthetic verdict, and comparison evidence"
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
        and state.ui_concept_personal_visual_review_done
        and state.ui_concept_design_recommendations_recorded
        and state.ui_concept_aesthetic_review_done
        and state.ui_concept_aesthetic_reasons_recorded
        and state.ui_reviewer_personal_walkthrough_done
        and state.ui_interaction_reachability_checked
        and state.ui_layout_overlap_density_checked
        and state.ui_reviewer_design_recommendations_recorded
        and state.ui_implementation_aesthetic_review_done
        and state.ui_implementation_aesthetic_reasons_recorded
        and state.ui_divergence_review_done
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI final verification before aesthetic/screenshot/divergence/iteration-loop gates")
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
        or state.ui_frontend_design_plan_done
        or state.visual_asset_scope == "required"
        or state.visual_asset_style_review_done
        or state.ui_implemented
        or state.ui_screenshot_qa_done
        or state.ui_divergence_review_done
        or state.ui_visual_iteration_loop_closed
        or state.ui_visual_iterations > 0
    ):
        return InvariantResult.fail("backend route invoked UI-only gates")
    return InvariantResult.pass_()


def subagent_result_must_merge_before_implementation_or_completion(
    state: State, trace
) -> InvariantResult:
    del trace
    if state.subagent_status in {"pending", "returned"}:
        if state.non_ui_implemented or state.ui_implemented or state.status == "complete":
            return InvariantResult.fail(
                "implementation/completion proceeded before subagent merge"
            )
    if state.subagent_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("subagent used before child-node sidecar scan")
    if state.subagent_status == "pending" and not state.subagent_scope_checked:
        return InvariantResult.fail("sidecar subagent assigned before disjoint scope check")
    if state.subagent_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("subagent assigned without a bounded sidecar need")
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
        and state.pm_review_release_order_written
        and state.pm_released_reviewer_for_current_gate
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
            "capability reviewer started current-gate review before PM release order, physical packet isolation, controller mail-chain audit, envelope/body audit, and per-packet role-origin audit"
        )
    if state.pm_review_release_order_written and not state.worker_output_ready_for_review:
        return InvariantResult.fail(
            "PM wrote a capability review release before worker output was ready"
        )
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
        and state.crew_memory_archived
        and state.crew_archived
    ):
        return InvariantResult.fail(
            "completed before six-agent crew, PM decisions, role memory archive, and terminal crew archive"
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
        state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail("completed before child-skill conformance audit and quality loop closure")
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
        return InvariantResult.fail("completed before completion grill-me exhausted obvious high-value work")
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
        and state.ui_screenshot_qa_done
        and state.ui_divergence_review_done
        and state.ui_visual_iteration_loop_closed
    ):
        return InvariantResult.fail("UI route completed before visual verification gates")
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
        and state.product_function_capability_map_written
        and state.local_skill_inventory_candidate_classified
    ):
        return InvariantResult.fail(
            "PM child-skill selection decisions were recorded before the PM manifest, product capability map, and local skill candidate classification"
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
            "capability startup self-interrogation was ratified before six-agent crew readiness"
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
            "capability product-function architecture was synthesized before crew recovery and reviewed material handoff"
        )
    product_architecture_inputs_ready = (
        state.product_function_architecture_pm_synthesized
        and state.product_function_high_standard_posture_written
        and state.product_function_target_and_failure_bar_written
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
    if state.node_acceptance_plan_written and not state.current_node_high_standard_recheck_written:
        return InvariantResult.fail(
            "capability node acceptance plan was written before PM current-node high-standard recheck"
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
        and state.pm_child_skill_selection_scope_decisions_recorded
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_process_officer_approved
        and state.child_skill_manifest_product_officer_approved
    ):
        return InvariantResult.fail(
            "PM approved child-skill gate manifest before PM skill selection, discovery, extraction, approver assignment, and reviewer/officer approvals"
        )
    if state.child_skill_manifest_process_officer_approved and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
    ):
        return InvariantResult.fail(
            "process FlowGuard officer approved child-skill process gates before manifest extraction and approver assignment"
        )
    if state.child_skill_manifest_product_officer_approved and not (
        state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
    ):
        return InvariantResult.fail(
            "product FlowGuard officer approved child-skill product gates before manifest extraction and approver assignment"
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
        and state.child_skill_execution_evidence_audited
        and state.child_skill_evidence_matches_outputs
        and state.child_skill_domain_quality_checked
        and state.child_skill_iteration_loop_closed
    ):
        return InvariantResult.fail(
            "current child-skill gates were role-approved before authority records, evidence audit, output match, domain quality, and loop closure"
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
        and state.final_residual_risk_triage_done
        and state.final_residual_risk_unresolved_count_zero
    ):
        return InvariantResult.fail(
            "PM built final route-wide capability gate ledger before current route scan, gate collection, generated-resource lineage, stale-evidence check, superseded explanations, zero unresolved count, and zero unresolved residual risks"
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
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew ledger archived before compact role memory archive")
    if state.pm_completion_decision_recorded and not state.crew_archived:
        return InvariantResult.fail("PM completion decision recorded before crew archive")
    if state.status == "complete" and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("capability route completed before PM completion approval")
    return InvariantResult.pass_()


def crew_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.self_interrogation_pm_ratified and not (
        state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
    ):
        return InvariantResult.fail(
            "PM ratified capability startup before six compact role memory packets existed"
        )
    if state.heartbeat_pm_decision_requested and not (
        state.heartbeat_loaded_state
        and state.heartbeat_loaded_frontier
        and state.heartbeat_loaded_packet_ledger
        and state.heartbeat_loaded_crew_memory
        and state.heartbeat_restored_crew
        and state.heartbeat_rehydrated_crew
        and state.crew_rehydration_report_written
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "heartbeat asked PM for capability work before current-run state, packet ledger, and crew role memory were loaded and rehydrated"
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
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew archive written before role memory archive")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="self_interrogation_before_contract",
        description="Freeze the contract only after showcase floor and visible grill-me style self-review evidence exist.",
        predicate=self_interrogation_before_contract,
    ),
    Invariant(
        name="startup_answers_before_showcase_and_self_interrogation",
        description="FlowPilot asks only the three startup questions and waits for explicit answers before showcase commitment and self-interrogation.",
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
        name="subagent_result_must_merge_before_implementation_or_completion",
        description="Subagent work must be scope-checked, returned, and merged before dependent implementation or completion.",
        predicate=subagent_result_must_merge_before_implementation_or_completion,
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
        name="crew_memory_rehydration_required",
        description="Heartbeat recovery must load compact role memory, rehydrate or seed replacements, refresh memory after work, and archive it before crew closure.",
        predicate=crew_memory_rehydration_required,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 140


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
