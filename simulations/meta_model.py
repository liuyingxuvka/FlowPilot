"""FlowGuard model for the FlowPilot meta workflow.

This model treats FlowGuard as both process designer and checker. FlowPilot
must start with a showcase-grade floor, make self-interrogation visible, create
real heartbeat continuity, design the route through FlowGuard before execution,
and avoid completion while obvious high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TARGET_CHUNKS = 2
TARGET_PARENT_NODES = 2
CREW_SIZE = 6
MAX_ROUTE_REVISIONS = 2
MAX_IMPL_RETRIES = 1
MAX_EXPERIMENTS = 1
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
MAX_COMPOSITE_STRUCTURAL_REPAIRS = 1
MAX_TERMINAL_BACKWARD_REPLAY_REPAIRS = 1
MIN_FULL_GRILLME_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_GRILLME_QUESTIONS = 20
MAX_FOCUSED_GRILLME_QUESTIONS = 50
DEFAULT_FOCUSED_GRILLME_QUESTIONS = 30
MIN_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 5
MAX_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 10
DEFAULT_LIGHTWEIGHT_SELF_CHECK_QUESTIONS = 7
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
    """One heartbeat/autopilot decision step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    flowpilot_enabled: bool = False
    run_scoped_startup_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_questions_asked: bool = False
    startup_dialog_stopped_for_answers: bool = False
    startup_banner_emitted: bool = False
    startup_banner_user_dialog_confirmed: bool = False
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
    preflow_visible_plan_cleared: bool = False
    old_control_state_reused_as_current: bool = False
    showcase_floor_committed: bool = False
    visible_self_interrogation_done: bool = False
    startup_self_interrogation_questions: int = 0
    startup_self_interrogation_layer_count: int = 0
    startup_self_interrogation_questions_per_layer: int = 0
    startup_self_interrogation_layers: int = 0
    startup_self_interrogation_pm_ratified: bool = False
    startup_self_interrogation_record_written: bool = False
    startup_self_interrogation_findings_dispositioned: bool = False
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
    visible_user_flow_diagram_emitted: bool = False
    user_flow_diagram_refreshed: bool = False
    user_flow_diagram_chat_display_required: bool = False
    user_flow_diagram_chat_displayed: bool = False
    user_flow_diagram_return_edge_required: bool = False
    user_flow_diagram_return_edge_present: bool = False
    user_flow_diagram_reviewer_display_checked: bool = False
    user_flow_diagram_reviewer_route_match_checked: bool = False
    user_flow_diagram_fresh_for_current_node: bool = False
    raw_flowguard_mermaid_used_as_user_flow: bool = False
    dependency_plan_recorded: bool = False
    future_installs_deferred: bool = False
    contract_frozen: bool = False
    contract_revision: int = 0
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
    controller_core_loaded: bool = False
    pm_initial_route_decision_recorded: bool = False
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
    heartbeat_loaded_state: bool = False
    heartbeat_loaded_frontier: bool = False
    heartbeat_loaded_packet_ledger: bool = False
    heartbeat_loaded_crew_memory: bool = False
    heartbeat_host_rehydrate_requested: bool = False
    heartbeat_restored_crew: bool = False
    heartbeat_rehydrated_crew: bool = False
    heartbeat_injected_current_run_memory_into_roles: bool = False
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
    pm_node_decision_recorded: bool = False
    crew_archived: bool = False
    crew_memory_archived: bool = False
    continuation_probe_done: bool = False
    continuation_host_kind_recorded: bool = False
    continuation_evidence_written: bool = False
    host_continuation_supported: bool = False
    manual_resume_mode_recorded: bool = False
    heartbeat_active: bool = False
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
    defect_event_logged_for_blocker: bool = False
    pm_defect_triage_done: bool = False
    blocking_defect_open: bool = False
    blocking_defect_fixed_pending_recheck: bool = False
    defect_same_class_recheck_done: bool = False
    defect_ledger_zero_blocking: bool = False
    evidence_credibility_triage_done: bool = False
    invalid_evidence_recorded: bool = False
    flowpilot_improvement_live_report_updated: bool = False
    pause_snapshot_written: bool = False

    route_version: int = 0
    route_checked: bool = False
    markdown_synced: bool = False
    execution_frontier_written: bool = False
    codex_plan_synced: bool = False
    frontier_version: int = 0
    plan_version: int = 0
    flowguard_process_design_done: bool = False
    flowguard_officer_model_adversarial_probe_done: bool = False
    flowguard_model_report_risk_tiers_done: bool = False
    flowguard_model_report_pm_review_agenda_done: bool = False
    flowguard_model_report_toolchain_recommendations_done: bool = False
    flowguard_model_report_confidence_boundary_done: bool = False
    candidate_route_tree_generated: bool = False
    recursive_route_decomposition_policy_written: bool = False
    route_leaf_readiness_gates_defined: bool = False
    route_reviewer_depth_review_required: bool = False
    router_leaf_only_dispatch_policy_checked: bool = False
    user_flow_diagram_shallow_projection_policy_recorded: bool = False
    root_route_model_checked: bool = False
    root_route_model_process_officer_approved: bool = False
    root_product_function_model_checked: bool = False
    root_product_function_model_product_officer_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
    parent_subtree_review_checked: bool = False
    parent_product_function_model_checked: bool = False
    parent_product_function_model_product_officer_approved: bool = False
    parent_focused_interrogation_done: bool = False
    parent_focused_interrogation_questions: int = 0
    parent_focused_interrogation_scope_id: str = ""
    parent_backward_structural_trigger_rule_recorded: bool = False
    parent_backward_review_targets_enumerated: bool = False
    unfinished_current_node_recovery_checked: bool = False
    active_node: str = "new"

    chunk_state: str = "none"  # none | ready | executed | verified | checkpoint_pending
    node_focused_interrogation_done: bool = False
    node_focused_interrogation_questions: int = 0
    node_focused_interrogation_scope_id: str = ""
    node_self_interrogation_record_written: bool = False
    node_self_interrogation_findings_dispositioned: bool = False
    node_product_function_model_checked: bool = False
    node_product_function_model_product_officer_approved: bool = False
    current_node_high_standard_recheck_written: bool = False
    current_node_minimum_sufficient_complexity_review_written: bool = False
    node_acceptance_plan_written: bool = False
    active_node_leaf_readiness_gate_passed: bool = False
    active_node_parent_dispatch_blocked: bool = False
    active_child_skill_bindings_written: bool = False
    active_child_skill_binding_scope_limited: bool = False
    child_skill_stricter_standard_precedence_bound: bool = False
    node_acceptance_risk_experiments_mapped: bool = False
    worker_packet_child_skill_use_instruction_written: bool = False
    active_child_skill_source_paths_allowed: bool = False
    lightweight_self_check_done: bool = False
    lightweight_self_check_questions: int = 0
    lightweight_self_check_scope_id: str = ""
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
    worker_child_skill_use_evidence_returned: bool = False
    reviewer_child_skill_use_evidence_checked: bool = False
    node_human_review_context_loaded: bool = False
    node_human_neutral_observation_written: bool = False
    node_human_manual_experiments_run: bool = False
    node_reviewer_independent_probe_done: bool = False
    node_human_inspection_passed: bool = False
    node_human_review_reviewer_approved: bool = False
    current_node_skill_improvement_check_done: bool = False
    node_human_inspections_passed: int = 0
    inspection_issue_grilled: bool = False
    pm_repair_decision_interrogations: int = 0
    human_inspection_repairs: int = 0
    composite_backward_context_loaded: bool = False
    composite_child_evidence_replayed: bool = False
    composite_backward_neutral_observation_written: bool = False
    composite_structure_decision_recorded: bool = False
    composite_reviewer_independent_probe_done: bool = False
    composite_backward_human_review_passed: bool = False
    composite_backward_review_reviewer_approved: bool = False
    composite_backward_reviews_passed: int = 0
    composite_backward_pm_segment_decision_recorded: bool = False
    composite_backward_pm_segment_decisions_recorded: int = 0
    composite_issue_grilled: bool = False
    composite_issue_strategy: str = "none"
    composite_structural_route_repairs: int = 0
    composite_new_sibling_nodes: int = 0
    composite_subtree_rebuilds: int = 0
    quality_route_raises: int = 0
    quality_reworks: int = 0
    node_visible_roadmap_emitted: bool = False
    verification_defined: bool = False
    required_chunks: int = TARGET_CHUNKS
    completed_chunks: int = 0
    checkpoint_written: bool = False
    role_memory_refreshed_after_work: bool = False

    issue: str = "none"  # none | model_gap | inspection_failure | composite_backward_failure | terminal_backward_review_failure | impl_failure | unknown_failure | no_progress
    route_revisions: int = 0
    impl_retries: int = 0
    experiments: int = 0

    child_node_sidecar_scan_done: bool = False
    sidecar_need: str = "unknown"  # unknown | none | needed
    subagent_pool_exists: bool = False
    subagent_idle_available: bool = False
    subagent_scope_checked: bool = False
    subagent_status: str = "none"  # none | idle | pending | returned | merged
    high_risk_gate: str = "none"  # none | pending | approved | denied

    completion_self_interrogation_done: bool = False
    completion_self_interrogation_questions: int = 0
    completion_self_interrogation_layer_count: int = 0
    completion_self_interrogation_questions_per_layer: int = 0
    completion_self_interrogation_layers: int = 0
    completion_self_interrogation_record_written: bool = False
    completion_self_interrogation_findings_dispositioned: bool = False
    completion_visible_roadmap_emitted: bool = False
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
    final_route_wide_gate_ledger_deep_leaf_coverage_collected: bool = False
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
    terminal_human_backward_replay_repairs: int = 0
    final_route_wide_gate_ledger_reviewer_backward_checked: bool = False
    final_ledger_pm_independent_audit_done: bool = False
    final_route_wide_gate_ledger_pm_completion_approved: bool = False
    high_value_work_review: str = "unknown"  # unknown | exhausted
    standard_expansions: int = 0
    terminal_closure_suite_run: bool = False
    terminal_state_and_evidence_refreshed: bool = False
    flowpilot_skill_improvement_report_written: bool = False
    final_report_emitted: bool = False
    pm_completion_decision_recorded: bool = False
    heartbeat_records: int = 0


def _step(state: State, *, label: str, action: str, **changes) -> FunctionResult:
    return FunctionResult(
        output=Action(action),
        new_state=replace(
            state,
            heartbeat_records=1,
            **changes,
        ),
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


def _reset_dual_layer_scope_gates() -> dict[str, object]:
    return {
        "parent_product_function_model_checked": False,
        "parent_product_function_model_product_officer_approved": False,
        "node_product_function_model_checked": False,
        "node_product_function_model_product_officer_approved": False,
        "node_human_review_context_loaded": False,
        "node_human_neutral_observation_written": False,
        "node_human_manual_experiments_run": False,
        "node_reviewer_independent_probe_done": False,
        "node_human_inspection_passed": False,
        "node_human_review_reviewer_approved": False,
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
        "worker_child_skill_use_evidence_returned": False,
        "reviewer_child_skill_use_evidence_checked": False,
        "inspection_issue_grilled": False,
        "composite_backward_context_loaded": False,
        "composite_child_evidence_replayed": False,
        "composite_backward_neutral_observation_written": False,
        "composite_structure_decision_recorded": False,
        "composite_reviewer_independent_probe_done": False,
        "composite_backward_human_review_passed": False,
        "composite_backward_review_reviewer_approved": False,
        "composite_backward_pm_segment_decision_recorded": False,
        "composite_issue_grilled": False,
        "composite_issue_strategy": "none",
    }


def _reset_user_flow_diagram_gate() -> dict[str, object]:
    return {
        "visible_user_flow_diagram_emitted": False,
        "user_flow_diagram_refreshed": False,
        "user_flow_diagram_shallow_projection_policy_recorded": False,
        "user_flow_diagram_chat_display_required": False,
        "user_flow_diagram_chat_displayed": False,
        "user_flow_diagram_return_edge_required": False,
        "user_flow_diagram_return_edge_present": False,
        "user_flow_diagram_reviewer_display_checked": False,
        "user_flow_diagram_reviewer_route_match_checked": False,
        "user_flow_diagram_fresh_for_current_node": False,
        "raw_flowguard_mermaid_used_as_user_flow": False,
    }


def _reset_execution_scope_gates() -> dict[str, object]:
    gates = _reset_quality_gates()
    gates.update(_reset_dual_layer_scope_gates())
    gates.update(_reset_final_route_wide_gate_ledger())
    gates.update(
        {
            "heartbeat_loaded_state": False,
            "heartbeat_loaded_frontier": False,
            "heartbeat_loaded_packet_ledger": False,
            "heartbeat_loaded_crew_memory": False,
            "heartbeat_host_rehydrate_requested": False,
            "heartbeat_restored_crew": False,
            "heartbeat_rehydrated_crew": False,
            "heartbeat_injected_current_run_memory_into_roles": False,
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
            "pm_node_decision_recorded": False,
            "current_node_high_standard_recheck_written": False,
            "current_node_minimum_sufficient_complexity_review_written": False,
            "node_acceptance_plan_written": False,
            "active_node_leaf_readiness_gate_passed": False,
            "active_node_parent_dispatch_blocked": False,
            "node_self_interrogation_record_written": False,
            "node_self_interrogation_findings_dispositioned": False,
            "active_child_skill_bindings_written": False,
            "active_child_skill_binding_scope_limited": False,
            "child_skill_stricter_standard_precedence_bound": False,
            "node_acceptance_risk_experiments_mapped": False,
            "worker_packet_child_skill_use_instruction_written": False,
            "active_child_skill_source_paths_allowed": False,
        }
    )
    return gates


def _reset_final_route_wide_gate_ledger() -> dict[str, object]:
    return {
        "final_route_wide_gate_ledger_current_route_scanned": False,
        "final_route_wide_gate_ledger_effective_nodes_resolved": False,
        "final_route_wide_gate_ledger_child_skill_gates_collected": False,
        "final_route_wide_gate_ledger_human_review_gates_collected": False,
        "final_route_wide_gate_ledger_parent_backward_replays_collected": False,
        "final_route_wide_gate_ledger_deep_leaf_coverage_collected": False,
        "final_route_wide_gate_ledger_product_process_gates_collected": False,
        "final_route_wide_gate_ledger_resource_lineage_resolved": False,
        "final_route_wide_gate_ledger_stale_evidence_checked": False,
        "final_route_wide_gate_ledger_superseded_nodes_explained": False,
        "evidence_credibility_triage_done": False,
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


def _startup_self_interrogation_disposition_ready(state: State) -> bool:
    return (
        state.visible_self_interrogation_done
        and _full_interrogation_ready(
            total_questions=state.startup_self_interrogation_questions,
            layer_count=state.startup_self_interrogation_layer_count,
            questions_per_layer=state.startup_self_interrogation_questions_per_layer,
            risk_family_mask=state.startup_self_interrogation_layers,
        )
        and state.startup_self_interrogation_record_written
        and state.startup_self_interrogation_pm_ratified
        and state.startup_self_interrogation_findings_dispositioned
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
        and MIN_FOCUSED_GRILLME_QUESTIONS
        <= total_questions
        <= MAX_FOCUSED_GRILLME_QUESTIONS
    )


def _node_self_interrogation_gate_ready(state: State) -> bool:
    return (
        state.node_focused_interrogation_done
        and _focused_interrogation_ready(
            total_questions=state.node_focused_interrogation_questions,
            scope_id=state.node_focused_interrogation_scope_id,
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


def _lightweight_self_check_ready(*, total_questions: int, scope_id: str) -> bool:
    return (
        bool(scope_id)
        and MIN_LIGHTWEIGHT_SELF_CHECK_QUESTIONS
        <= total_questions
        <= MAX_LIGHTWEIGHT_SELF_CHECK_QUESTIONS
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
        state.startup_self_interrogation_pm_ratified
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


def _user_flow_display_gate_passed(state: State) -> bool:
    return (
        state.user_flow_diagram_refreshed
        and state.visible_user_flow_diagram_emitted
        and not state.raw_flowguard_mermaid_used_as_user_flow
        and (
            not state.user_flow_diagram_chat_display_required
            or state.user_flow_diagram_chat_displayed
        )
        and (
            not state.user_flow_diagram_return_edge_required
            or state.user_flow_diagram_return_edge_present
        )
        and state.user_flow_diagram_reviewer_display_checked
        and state.user_flow_diagram_reviewer_route_match_checked
        and state.user_flow_diagram_fresh_for_current_node
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
        and state.final_route_wide_gate_ledger_deep_leaf_coverage_collected
        and state.final_route_wide_gate_ledger_product_process_gates_collected
        and state.final_route_wide_gate_ledger_resource_lineage_resolved
        and state.final_route_wide_gate_ledger_stale_evidence_checked
        and state.final_route_wide_gate_ledger_superseded_nodes_explained
        and state.evidence_credibility_triage_done
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


def _route_ready(state: State) -> bool:
    return (
        state.status == "running"
        and state.flowpilot_enabled
        and state.startup_banner_emitted
        and state.defect_ledger_initialized
        and state.evidence_ledger_initialized
        and state.generated_resource_ledger_initialized
        and state.activity_stream_initialized
        and state.activity_stream_latest_event_written
        and state.flowpilot_improvement_live_report_initialized
        and state.preflow_visible_plan_cleared
        and state.showcase_floor_committed
        and state.visible_self_interrogation_done
        and state.startup_self_interrogation_pm_ratified
        and state.quality_candidate_pool_seeded
        and state.validation_strategy_seeded
        and _product_function_architecture_ready(state)
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and state.contract_frozen
        and _crew_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and _continuation_ready(state)
        and state.flowguard_process_design_done
        and state.flowguard_officer_model_adversarial_probe_done
        and state.route_version > 0
        and state.route_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
        and state.parent_backward_structural_trigger_rule_recorded
        and state.parent_backward_review_targets_enumerated
        and state.markdown_synced
        and state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.route_version
        and state.plan_version == state.frontier_version
        and _user_flow_display_gate_passed(state)
        and _live_subagent_startup_resolved(state)
        and _startup_pm_gate_ready(state)
        and state.work_beyond_startup_allowed
        and state.issue == "none"
        and state.high_risk_gate != "pending"
        and state.chunk_state == "none"
    )


class AutopilotStep:
    name = "AutopilotStep"
    reads = (
        "status",
        "flowpilot_enabled",
        "startup_questions_asked",
        "startup_dialog_stopped_for_answers",
        "startup_banner_emitted",
        "startup_background_agents_answered",
        "startup_scheduled_continuation_answered",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "top_level_control_state_absent_or_quarantined",
        "preflow_visible_plan_cleared",
        "old_control_state_reused_as_current",
        "showcase_floor_committed",
        "visible_self_interrogation_done",
        "startup_self_interrogation_questions",
        "startup_self_interrogation_layer_count",
        "startup_self_interrogation_questions_per_layer",
        "startup_self_interrogation_layers",
        "startup_self_interrogation_pm_ratified",
        "startup_self_interrogation_record_written",
        "startup_self_interrogation_findings_dispositioned",
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
        "visible_user_flow_diagram_emitted",
        "user_flow_diagram_refreshed",
        "user_flow_diagram_shallow_projection_policy_recorded",
        "user_flow_diagram_chat_display_required",
        "user_flow_diagram_chat_displayed",
        "user_flow_diagram_return_edge_required",
        "user_flow_diagram_return_edge_present",
        "user_flow_diagram_reviewer_display_checked",
        "user_flow_diagram_reviewer_route_match_checked",
        "user_flow_diagram_fresh_for_current_node",
        "raw_flowguard_mermaid_used_as_user_flow",
        "dependency_plan_recorded",
        "future_installs_deferred",
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
        "controller_core_loaded",
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_pm_approved_for_route",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_crew_memory",
        "heartbeat_host_rehydrate_requested",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "heartbeat_injected_current_run_memory_into_roles",
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
        "pm_node_decision_recorded",
        "crew_archived",
        "crew_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
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
        "flowguard_process_design_done",
        "flowguard_officer_model_adversarial_probe_done",
        "candidate_route_tree_generated",
        "recursive_route_decomposition_policy_written",
        "route_leaf_readiness_gates_defined",
        "route_reviewer_depth_review_required",
        "router_leaf_only_dispatch_policy_checked",
        "root_route_model_checked",
        "root_route_model_process_officer_approved",
        "root_product_function_model_checked",
        "root_product_function_model_product_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_product_officer_approved",
        "parent_focused_interrogation_done",
        "parent_focused_interrogation_questions",
        "parent_focused_interrogation_scope_id",
        "parent_backward_structural_trigger_rule_recorded",
        "parent_backward_review_targets_enumerated",
        "unfinished_current_node_recovery_checked",
        "route_checked",
        "markdown_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "chunk_state",
        "node_focused_interrogation_done",
        "node_focused_interrogation_questions",
        "node_focused_interrogation_scope_id",
        "node_self_interrogation_record_written",
        "node_self_interrogation_findings_dispositioned",
        "node_product_function_model_checked",
        "node_product_function_model_product_officer_approved",
        "current_node_high_standard_recheck_written",
        "current_node_minimum_sufficient_complexity_review_written",
        "node_acceptance_plan_written",
        "active_node_leaf_readiness_gate_passed",
        "active_node_parent_dispatch_blocked",
        "active_child_skill_bindings_written",
        "active_child_skill_binding_scope_limited",
        "child_skill_stricter_standard_precedence_bound",
        "node_acceptance_risk_experiments_mapped",
        "worker_packet_child_skill_use_instruction_written",
        "active_child_skill_source_paths_allowed",
        "lightweight_self_check_done",
        "lightweight_self_check_questions",
        "lightweight_self_check_scope_id",
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
        "worker_child_skill_use_evidence_returned",
        "reviewer_child_skill_use_evidence_checked",
        "node_human_review_context_loaded",
        "node_human_neutral_observation_written",
        "node_human_manual_experiments_run",
        "node_reviewer_independent_probe_done",
        "node_human_inspection_passed",
        "node_human_review_reviewer_approved",
        "current_node_skill_improvement_check_done",
        "node_human_inspections_passed",
        "inspection_issue_grilled",
        "human_inspection_repairs",
        "composite_backward_context_loaded",
        "composite_child_evidence_replayed",
        "composite_backward_neutral_observation_written",
        "composite_structure_decision_recorded",
        "composite_reviewer_independent_probe_done",
        "composite_backward_human_review_passed",
        "composite_backward_review_reviewer_approved",
        "composite_backward_reviews_passed",
        "composite_backward_pm_segment_decision_recorded",
        "composite_backward_pm_segment_decisions_recorded",
        "composite_issue_grilled",
        "composite_issue_strategy",
        "composite_structural_route_repairs",
        "composite_new_sibling_nodes",
        "composite_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "node_visible_roadmap_emitted",
        "issue",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_scope_checked",
        "subagent_status",
        "high_risk_gate",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_self_interrogation_record_written",
        "completion_self_interrogation_findings_dispositioned",
        "completion_visible_roadmap_emitted",
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
        "final_route_wide_gate_ledger_deep_leaf_coverage_collected",
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
        "terminal_human_backward_replay_repairs",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_ledger_pm_independent_audit_done",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "terminal_closure_suite_run",
        "terminal_state_and_evidence_refreshed",
        "flowpilot_skill_improvement_report_written",
        "pm_completion_decision_recorded",
    )
    writes = (
        "status",
        "flowpilot_enabled",
        "startup_questions_asked",
        "startup_dialog_stopped_for_answers",
        "startup_banner_emitted",
        "startup_background_agents_answered",
        "startup_scheduled_continuation_answered",
        "run_directory_created",
        "current_pointer_written",
        "run_index_updated",
        "prior_work_mode",
        "prior_work_import_packet_written",
        "control_state_written_under_run_root",
        "top_level_control_state_absent_or_quarantined",
        "preflow_visible_plan_cleared",
        "old_control_state_reused_as_current",
        "showcase_floor_committed",
        "visible_self_interrogation_done",
        "startup_self_interrogation_questions",
        "startup_self_interrogation_layer_count",
        "startup_self_interrogation_questions_per_layer",
        "startup_self_interrogation_layers",
        "startup_self_interrogation_pm_ratified",
        "startup_self_interrogation_record_written",
        "startup_self_interrogation_findings_dispositioned",
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
        "visible_user_flow_diagram_emitted",
        "user_flow_diagram_refreshed",
        "user_flow_diagram_chat_display_required",
        "user_flow_diagram_chat_displayed",
        "user_flow_diagram_return_edge_required",
        "user_flow_diagram_return_edge_present",
        "user_flow_diagram_reviewer_display_checked",
        "user_flow_diagram_reviewer_route_match_checked",
        "user_flow_diagram_fresh_for_current_node",
        "raw_flowguard_mermaid_used_as_user_flow",
        "dependency_plan_recorded",
        "future_installs_deferred",
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
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_pm_approved_for_route",
        "heartbeat_loaded_state",
        "heartbeat_loaded_frontier",
        "heartbeat_loaded_packet_ledger",
        "heartbeat_loaded_crew_memory",
        "heartbeat_host_rehydrate_requested",
        "heartbeat_restored_crew",
        "heartbeat_rehydrated_crew",
        "heartbeat_injected_current_run_memory_into_roles",
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
        "pm_node_decision_recorded",
        "crew_archived",
        "crew_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "host_continuation_supported",
        "manual_resume_mode_recorded",
        "heartbeat_active",
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
        "defect_event_logged_for_blocker",
        "pm_defect_triage_done",
        "blocking_defect_open",
        "blocking_defect_fixed_pending_recheck",
        "defect_same_class_recheck_done",
        "defect_ledger_zero_blocking",
        "evidence_credibility_triage_done",
        "invalid_evidence_recorded",
        "flowpilot_improvement_live_report_updated",
        "pause_snapshot_written",
        "route_version",
        "route_checked",
        "markdown_synced",
        "execution_frontier_written",
        "codex_plan_synced",
        "frontier_version",
        "plan_version",
        "flowguard_process_design_done",
        "flowguard_officer_model_adversarial_probe_done",
        "candidate_route_tree_generated",
        "root_route_model_checked",
        "root_route_model_process_officer_approved",
        "root_product_function_model_checked",
        "root_product_function_model_product_officer_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_product_officer_approved",
        "parent_focused_interrogation_done",
        "parent_focused_interrogation_questions",
        "parent_focused_interrogation_scope_id",
        "parent_backward_structural_trigger_rule_recorded",
        "parent_backward_review_targets_enumerated",
        "unfinished_current_node_recovery_checked",
        "active_node",
        "chunk_state",
        "node_focused_interrogation_done",
        "node_focused_interrogation_questions",
        "node_focused_interrogation_scope_id",
        "node_self_interrogation_record_written",
        "node_self_interrogation_findings_dispositioned",
        "node_product_function_model_checked",
        "node_product_function_model_product_officer_approved",
        "current_node_high_standard_recheck_written",
        "current_node_minimum_sufficient_complexity_review_written",
        "node_acceptance_plan_written",
        "active_child_skill_bindings_written",
        "active_child_skill_binding_scope_limited",
        "child_skill_stricter_standard_precedence_bound",
        "node_acceptance_risk_experiments_mapped",
        "worker_packet_child_skill_use_instruction_written",
        "active_child_skill_source_paths_allowed",
        "lightweight_self_check_done",
        "lightweight_self_check_questions",
        "lightweight_self_check_scope_id",
        "quality_package_done",
        "quality_candidate_registry_checked",
        "quality_raise_decision_recorded",
        "validation_matrix_defined",
        "anti_rough_finish_done",
        "pm_review_hold_instruction_written",
        "worker_output_ready_for_review",
        "pm_review_release_order_written",
        "pm_released_reviewer_for_current_gate",
        "worker_child_skill_use_evidence_returned",
        "reviewer_child_skill_use_evidence_checked",
        "node_human_review_context_loaded",
        "node_human_neutral_observation_written",
        "node_human_manual_experiments_run",
        "node_reviewer_independent_probe_done",
        "node_human_inspection_passed",
        "node_human_review_reviewer_approved",
        "current_node_skill_improvement_check_done",
        "node_human_inspections_passed",
        "inspection_issue_grilled",
        "human_inspection_repairs",
        "composite_backward_context_loaded",
        "composite_child_evidence_replayed",
        "composite_backward_neutral_observation_written",
        "composite_structure_decision_recorded",
        "composite_reviewer_independent_probe_done",
        "composite_backward_human_review_passed",
        "composite_backward_review_reviewer_approved",
        "composite_backward_reviews_passed",
        "composite_backward_pm_segment_decision_recorded",
        "composite_backward_pm_segment_decisions_recorded",
        "composite_issue_grilled",
        "composite_issue_strategy",
        "composite_structural_route_repairs",
        "composite_new_sibling_nodes",
        "composite_subtree_rebuilds",
        "quality_route_raises",
        "quality_reworks",
        "node_visible_roadmap_emitted",
        "verification_defined",
        "required_chunks",
        "completed_chunks",
        "checkpoint_written",
        "role_memory_refreshed_after_work",
        "issue",
        "route_revisions",
        "impl_retries",
        "experiments",
        "child_node_sidecar_scan_done",
        "sidecar_need",
        "subagent_pool_exists",
        "subagent_idle_available",
        "subagent_scope_checked",
        "subagent_status",
        "high_risk_gate",
        "completion_self_interrogation_done",
        "completion_self_interrogation_questions",
        "completion_self_interrogation_layer_count",
        "completion_self_interrogation_questions_per_layer",
        "completion_self_interrogation_layers",
        "completion_self_interrogation_record_written",
        "completion_self_interrogation_findings_dispositioned",
        "completion_visible_roadmap_emitted",
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
        "terminal_human_backward_replay_repairs",
        "final_route_wide_gate_ledger_reviewer_backward_checked",
        "final_ledger_pm_independent_audit_done",
        "final_route_wide_gate_ledger_pm_completion_approved",
        "high_value_work_review",
        "standard_expansions",
        "terminal_closure_suite_run",
        "terminal_state_and_evidence_refreshed",
        "flowpilot_skill_improvement_report_written",
        "final_report_emitted",
        "pm_completion_decision_recorded",
        "controlled_stop_notice_recorded",
        "terminal_completion_notice_recorded",
        "defect_ledger_initialized",
        "evidence_ledger_initialized",
        "generated_resource_ledger_initialized",
        "activity_stream_initialized",
        "activity_stream_latest_event_written",
        "flowpilot_improvement_live_report_initialized",
        "defect_event_logged_for_blocker",
        "pm_defect_triage_done",
        "blocking_defect_open",
        "blocking_defect_fixed_pending_recheck",
        "defect_same_class_recheck_done",
        "defect_ledger_zero_blocking",
        "evidence_credibility_triage_done",
        "invalid_evidence_recorded",
        "flowpilot_improvement_live_report_updated",
        "pause_snapshot_written",
        "heartbeat_records",
    )
    accepted_input_type = Tick
    input_description = "one continuation/autopilot control decision"
    output_description = "next allowed control action"
    idempotency = (
        "Repeated heartbeat decisions do not lower the frozen contract, do not "
        "complete early, and must either advance, recover, update the model, or block."
    )

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        if state.status == "new":
            yield _step(
                state,
                label="autopilot_started",
                action="start the FlowPilot control loop",
                status="running",
                flowpilot_enabled=True,
                run_scoped_startup_bootstrap_created=True,
                heartbeat_active=True,
                active_node="ask_startup_questions",
            )
            return

        if not state.startup_questions_asked:
            yield _step(
                state,
                label="startup_three_questions_asked",
                action="ask background-agent permission, scheduled-continuation permission, and whether to open Cockpit UI before banner",
                startup_questions_asked=True,
                active_node="stop_for_startup_answers",
            )
            return

        if not state.startup_dialog_stopped_for_answers:
            yield _step(
                state,
                label="startup_dialog_stopped_for_user_answers",
                action="end the assistant response after asking startup questions and wait for the user's reply",
                startup_dialog_stopped_for_answers=True,
                active_node="await_background_agent_answer",
            )
            return

        if not state.startup_background_agents_answered:
            yield _step(
                state,
                label="startup_background_agents_answered",
                action="record explicit user answer for six background subagents versus single-agent continuity",
                startup_background_agents_answered=True,
                active_node="await_scheduled_continuation_answer",
            )
            return

        if not state.startup_scheduled_continuation_answered:
            yield _step(
                state,
                label="startup_scheduled_continuation_answered",
                action="record explicit user answer for heartbeat/automation versus manual resume",
                startup_scheduled_continuation_answered=True,
                active_node="await_display_surface_answer",
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
                active_node="emit_startup_banner",
            )
            return

        if not state.startup_banner_emitted:
            yield _step(
                state,
                label="startup_banner_emitted",
                action="emit the FlowPilot startup banner in the user dialog only after the three startup answers",
                startup_banner_emitted=True,
                startup_banner_user_dialog_confirmed=True,
                active_node="create_run_directory",
            )
            return

        if not state.run_directory_created:
            yield _step(
                state,
                label="run_directory_created",
                action="create a fresh .flowpilot/runs/<run-id>/ directory for this formal FlowPilot invocation",
                run_directory_created=True,
                active_node="write_current_pointer",
            )
            return

        if not state.current_pointer_written:
            yield _step(
                state,
                label="current_pointer_written",
                action="write .flowpilot/current.json to point at the current run directory",
                current_pointer_written=True,
                active_node="update_run_index",
            )
            return

        if not state.run_index_updated:
            yield _step(
                state,
                label="run_index_updated",
                action="update .flowpilot/index.json with the new run identity and creation metadata",
                run_index_updated=True,
                active_node="initialize_defect_ledger",
            )
            return

        if not state.defect_ledger_initialized:
            yield _step(
                state,
                label="defect_ledger_initialized",
                action="create the run-level defect ledger and event log before any review, repair, pause, or completion gate can record findings",
                defect_ledger_initialized=True,
                active_node="initialize_evidence_ledger",
            )
            return

        if not state.evidence_ledger_initialized:
            yield _step(
                state,
                label="evidence_ledger_initialized",
                action="create the run-level evidence credibility ledger before screenshots, fixture reports, generated assets, or model outputs can close gates",
                evidence_ledger_initialized=True,
                active_node="initialize_generated_resource_ledger",
            )
            return

        if not state.generated_resource_ledger_initialized:
            yield _step(
                state,
                label="generated_resource_ledger_initialized",
                action="create the run-level generated-resource ledger before imagegen concepts, visual assets, screenshots, diagrams, or model reports are produced or discarded",
                generated_resource_ledger_initialized=True,
                active_node="initialize_activity_stream",
            )
            return

        if not state.activity_stream_initialized:
            yield _step(
                state,
                label="activity_stream_initialized",
                action="create the run-level activity stream so PM, reviewer, officer, worker, route, heartbeat, and user-visible progress events can be displayed without manual refresh",
                activity_stream_initialized=True,
                activity_stream_latest_event_written=True,
                active_node="initialize_flowpilot_improvement_report",
            )
            return

        if not state.flowpilot_improvement_live_report_initialized:
            yield _step(
                state,
                label="flowpilot_improvement_live_report_initialized",
                action="initialize the live FlowPilot improvement report so skill or process defects are captured even if the run pauses before terminal closure",
                flowpilot_improvement_live_report_initialized=True,
                active_node="resolve_prior_work_boundary",
            )
            return

        if state.prior_work_mode == "unknown":
            yield _step(
                state,
                label="new_task_no_prior_import",
                action="record that this run starts without importing prior FlowPilot control state",
                prior_work_mode="new",
                active_node="write_run_scoped_control_state",
            )
            yield _step(
                state,
                label="continue_previous_work_selected",
                action="record that this run continues prior work but must import prior outputs as read-only evidence",
                prior_work_mode="continue",
                active_node="write_prior_work_import_packet",
            )
            return

        if state.prior_work_mode == "continue" and not state.prior_work_import_packet_written:
            yield _step(
                state,
                label="prior_work_import_packet_written",
                action="write a prior-work import packet under the new run without making old state current",
                prior_work_import_packet_written=True,
                active_node="write_run_scoped_control_state",
            )
            return

        if not state.control_state_written_under_run_root:
            yield _step(
                state,
                label="control_state_written_under_run_root",
                action="write state, frontier, route, crew, and review control artifacts only under the current run directory",
                control_state_written_under_run_root=True,
                active_node="quarantine_legacy_top_level_control_state",
            )
            return

        if not state.top_level_control_state_absent_or_quarantined:
            yield _step(
                state,
                label="top_level_control_state_absent_or_quarantined",
                action="verify legacy top-level control state is absent, legacy-only, or quarantined before current work continues",
                top_level_control_state_absent_or_quarantined=True,
                active_node="clear_preflow_visible_plan",
            )
            return

        if not state.preflow_visible_plan_cleared:
            yield _step(
                state,
                label="preflow_visible_plan_cleared",
                action="controller replaces any ordinary pre-FlowPilot Codex plan with the waiting-for-PM display projection before PM route work",
                preflow_visible_plan_cleared=True,
                active_node="resolve_startup_display_surface",
            )
            return

        if not state.startup_display_entry_action_done:
            yield _step(
                state,
                label="startup_display_entry_action_done",
                action="open Cockpit UI immediately when requested, or display the chat route sign when the user chose chat",
                startup_display_entry_action_done=True,
                active_node="freeze_contract",
            )
            return

        if not state.showcase_floor_committed:
            yield _step(
                state,
                label="showcase_floor_committed",
                action="commit to showcase-grade long-horizon FlowPilot scope",
                showcase_floor_committed=True,
                active_node="visible_self_interrogation",
            )
            return

        if not state.visible_self_interrogation_done:
            yield _step(
                state,
                label="visible_self_interrogation_completed",
                action="derive dynamic layers, expose at least 100 grill-me questions per active layer, seed the improvement candidate pool, and seed initial validation direction before contract freeze",
                visible_self_interrogation_done=True,
                startup_self_interrogation_questions=(
                    MODEL_DYNAMIC_LAYER_COUNT
                    * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                ),
                startup_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                startup_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                startup_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                quality_candidate_pool_seeded=True,
                validation_strategy_seeded=True,
                active_node="establish_six_agent_crew",
            )
            return

        if not state.startup_self_interrogation_record_written:
            yield _step(
                state,
                label="startup_self_interrogation_record_written",
                action="write a durable startup self-interrogation record with findings, source event, scope, and PM disposition slots before later route gates can use it",
                startup_self_interrogation_record_written=True,
                active_node="establish_six_agent_crew",
            )
            return

        if not state.crew_policy_written:
            yield _step(
                state,
                label="six_agent_crew_policy_written",
                action="write fixed six-agent crew policy: project manager, reviewer, process FlowGuard officer, product FlowGuard officer, worker A, worker B",
                crew_policy_written=True,
                active_node="spawn_project_manager",
            )
            return

        if state.crew_count == 0:
            yield _step(
                state,
                label="project_manager_spawned_fresh_for_task",
                action="spawn a fresh project manager for the new formal FlowPilot task before route work",
                crew_count=1,
                project_manager_ready=True,
                active_node="spawn_reviewer",
            )
            return

        if state.crew_count == 1:
            yield _step(
                state,
                label="human_like_reviewer_spawned_fresh_for_task",
                action="spawn a fresh human-like reviewer for the new formal FlowPilot task before route work",
                crew_count=2,
                reviewer_ready=True,
                active_node="spawn_process_flowguard_officer",
            )
            return

        if state.crew_count == 2:
            yield _step(
                state,
                label="process_flowguard_officer_spawned_fresh_for_task",
                action="spawn a fresh process FlowGuard officer for the new formal FlowPilot task before route work",
                crew_count=3,
                process_flowguard_officer_ready=True,
                active_node="spawn_product_flowguard_officer",
            )
            return

        if state.crew_count == 3:
            yield _step(
                state,
                label="product_flowguard_officer_spawned_fresh_for_task",
                action="spawn a fresh product FlowGuard officer for the new formal FlowPilot task before route work",
                crew_count=4,
                product_flowguard_officer_ready=True,
                active_node="spawn_worker_a",
            )
            return

        if state.crew_count == 4:
            yield _step(
                state,
                label="worker_a_spawned_fresh_for_task",
                action="spawn a fresh worker A for bounded sidecar work in the new formal FlowPilot task",
                crew_count=5,
                worker_a_ready=True,
                active_node="spawn_worker_b",
            )
            return

        if state.crew_count == 5:
            yield _step(
                state,
                label="worker_b_spawned_fresh_for_task",
                action="spawn a fresh worker B for bounded sidecar work in the new formal FlowPilot task",
                crew_count=CREW_SIZE,
                worker_b_ready=True,
                active_node="write_crew_ledger",
            )
            return

        if not state.crew_ledger_written:
            yield _step(
                state,
                label="crew_ledger_written",
                action="persist crew names, role authority, agent ids, status, and recovery rules before route work",
                crew_ledger_written=True,
                active_node="record_role_identity_protocol",
            )
            return

        if not state.role_identity_protocol_recorded:
            yield _step(
                state,
                label="role_identity_protocol_recorded",
                action="record distinct role_key, display_name, and diagnostic-only agent_id fields before crew memory is authoritative",
                role_identity_protocol_recorded=True,
                active_node="record_pm_flowguard_delegation_policy",
            )
            return

        if not state.pm_flowguard_delegation_policy_recorded:
            yield _step(
                state,
                label="pm_flowguard_delegation_policy_recorded",
                action="record that the project manager creates structured FlowGuard modeling requests for uncertain process, product, reference-system, migration-equivalence, experiment-derived behavior, or validation decisions and assigns them to the process or product FlowGuard officer",
                pm_flowguard_delegation_policy_recorded=True,
                active_node="record_officer_owned_async_modeling_policy",
            )
            return

        if not state.officer_owned_async_modeling_policy_recorded:
            yield _step(
                state,
                label="officer_owned_async_modeling_policy_recorded",
                action="record that FlowGuard model gates dispatch to officer-owned run directories while the controller may relay only non-dependent coordination",
                officer_owned_async_modeling_policy_recorded=True,
                active_node="record_officer_model_report_provenance_policy",
            )
            return

        if not state.officer_model_report_provenance_policy_recorded:
            yield _step(
                state,
                label="officer_model_report_provenance_policy_recorded",
                action="require officer model reports to prove model author, runner, interpreter, commands, input snapshots, state counts, counterexample inspection, risk tiers, PM review agenda, toolchain recommendations, confidence boundary, blindspots, and decision",
                officer_model_report_provenance_policy_recorded=True,
                active_node="record_controller_coordination_boundary",
            )
            return

        if not state.controller_coordination_boundary_recorded:
            yield _step(
                state,
                label="controller_coordination_boundary_recorded",
                action="record that controller coordination during officer modeling cannot satisfy route freeze, implementation, checkpoint, completion, or protected model gates",
                controller_coordination_boundary_recorded=True,
                active_node="record_independent_approval_protocol",
            )
            return

        if not state.independent_approval_protocol_recorded:
            yield _step(
                state,
                label="independent_approval_protocol_recorded",
                action="record that every PM, reviewer, and FlowGuard officer approval requires independent adversarial validation evidence and cannot be completion-report-only",
                independent_approval_protocol_recorded=True,
                active_node="write_crew_memory_packets",
            )
            return

        if not state.crew_memory_policy_written:
            yield _step(
                state,
                label="crew_memory_packets_written",
                action="write compact role memory packets for all six roles before route work",
                crew_memory_policy_written=True,
                crew_memory_packets_written=CREW_SIZE,
                active_node="bootstrap_continuation",
            )
            return

        if not state.continuation_probe_done:
            yield _step(
                state,
                label="host_continuation_capability_supported",
                action="during startup bootstrap, probe host automation capability, record host-kind continuation evidence, and confirm real heartbeat setup is supported before Controller core loads",
                continuation_probe_done=True,
                continuation_host_kind_recorded=True,
                continuation_evidence_written=True,
                host_continuation_supported=True,
                active_node="create_startup_heartbeat_before_controller_core",
            )
            yield _step(
                state,
                label="host_continuation_capability_unsupported_manual_resume",
                action="during startup bootstrap, record manual-resume mode when host automation is unavailable or not requested, without creating heartbeat automation before Controller core loads",
                continuation_probe_done=True,
                continuation_host_kind_recorded=True,
                continuation_evidence_written=True,
                host_continuation_supported=False,
                manual_resume_mode_recorded=True,
                active_node="load_controller_core",
            )
            return

        if state.host_continuation_supported and not state.heartbeat_schedule_created:
            yield _step(
                state,
                label="heartbeat_schedule_created",
                action="create one-minute route heartbeat as a stable launcher bound to the current run before loading Controller core",
                heartbeat_schedule_created=True,
                route_heartbeat_interval_minutes=1,
                stable_heartbeat_launcher_recorded=True,
                heartbeat_bound_to_current_run=True,
                heartbeat_same_name_only_checked=False,
                active_node="load_controller_core",
            )
            return

        if not state.controller_core_loaded:
            yield _step(
                state,
                label="controller_core_loaded_after_startup_continuation_bootstrap",
                action="load Controller core only after startup continuation is either a bound heartbeat or recorded manual-resume mode",
                controller_core_loaded=True,
                active_node="pm_ratify_startup_self_interrogation",
            )
            return

        if not state.startup_self_interrogation_pm_ratified:
            yield _step(
                state,
                label="startup_self_interrogation_pm_ratified",
                action="project manager ratifies startup self-interrogation scope, risk layers, question count, decision set, and PM disposition of durable findings before route/model gates",
                startup_self_interrogation_pm_ratified=True,
                startup_self_interrogation_findings_dispositioned=True,
                active_node="material_intake",
            )
            return

        if not state.material_sources_scanned:
            yield _step(
                state,
                label="material_sources_scanned",
                action="authorized worker scans user-provided and repository-local materials before PM route design",
                material_sources_scanned=True,
                active_node="summarize_material_sources",
            )
            return

        if not state.material_source_summaries_written:
            yield _step(
                state,
                label="material_source_summaries_written",
                action="authorized worker writes purpose, contents, and current-state summaries for every relevant material source",
                material_source_summaries_written=True,
                active_node="classify_material_source_quality",
            )
            return

        if not state.material_source_quality_classified:
            yield _step(
                state,
                label="material_source_quality_classified",
                action="authorized worker classifies source authority, freshness, contradictions, missing context, and readiness",
                material_source_quality_classified=True,
                active_node="write_material_intake_packet",
            )
            return

        if not state.local_skill_inventory_written:
            yield _step(
                state,
                label="local_skill_inventory_written",
                action="authorized worker inventories locally available skills and host capabilities as candidate resources before the material packet is finalized",
                local_skill_inventory_written=True,
                active_node="classify_local_skill_candidates",
            )
            return

        if not state.local_skill_inventory_candidate_classified:
            yield _step(
                state,
                label="local_skill_inventory_candidate_classified",
                action="authorized worker classifies local skills as candidate-only resources without treating availability as PM approval to use them",
                local_skill_inventory_candidate_classified=True,
                active_node="write_material_intake_packet",
            )
            return

        if not state.material_intake_packet_written:
            yield _step(
                state,
                label="material_intake_packet_written",
                action="authorized worker writes the Material Intake Packet, including local skill inventory, as packet-controlled startup evidence",
                material_intake_packet_written=True,
                active_node="probe_material_intake_sources",
            )
            return

        if not state.material_reviewer_direct_source_probe_done:
            yield _step(
                state,
                label="material_reviewer_direct_source_probe_done",
                action="human-like reviewer opens or samples actual materials and tests whether the packet could be summary-only before sufficiency approval",
                material_reviewer_direct_source_probe_done=True,
                active_node="review_material_intake_packet",
            )
            return

        if not state.material_reviewer_sufficiency_checked:
            yield _step(
                state,
                label="material_reviewer_sufficiency_checked",
                action="human-like reviewer checks whether the material packet is clear and complete enough for PM planning",
                material_reviewer_sufficiency_checked=True,
                active_node="approve_material_intake_packet",
            )
            return

        if not state.material_reviewer_sufficiency_approved:
            yield _step(
                state,
                label="material_reviewer_sufficiency_approved",
                action="human-like reviewer approves that the Material Intake Packet is PM-ready or records blockers before PM receives it",
                material_reviewer_sufficiency_approved=True,
                active_node="write_pm_material_understanding_memo",
            )
            return

        if not state.pm_material_understanding_memo_written:
            yield _step(
                state,
                label="pm_material_understanding_memo_written",
                action="project manager writes a material understanding memo with source-claim matrix, open questions, and route implications",
                pm_material_understanding_memo_written=True,
                active_node="classify_material_complexity",
            )
            return

        if not state.pm_material_complexity_classified:
            yield _step(
                state,
                label="pm_material_complexity_classified",
                action="project manager classifies material complexity as simple, normal, or messy/raw before route planning",
                pm_material_complexity_classified=True,
                active_node="record_material_discovery_decision",
            )
            return

        if not state.pm_material_discovery_decision_recorded:
            yield _step(
                state,
                label="pm_material_discovery_decision_recorded",
                action="project manager records whether materials can feed route design directly or require a formal discovery, cleanup, modeling, or validation subtree",
                pm_material_discovery_decision_recorded=True,
                active_node="decide_material_research_package_need",
            )
            return

        if not state.pm_material_research_decision_recorded:
            yield _step(
                state,
                label="pm_material_research_decision_not_required",
                action="project manager records that reviewed materials are sufficient and no formal research package is required before product architecture",
                pm_material_research_decision_recorded=True,
                material_research_need="not_required",
                active_node="product_function_architecture",
            )
            yield _step(
                state,
                label="pm_material_research_decision_requires_package",
                action="project manager records a material gap that must become a formal research, mechanism-discovery, evidence-collection, or experiment package before product architecture",
                pm_material_research_decision_recorded=True,
                material_research_need="required",
                active_node="write_pm_research_package",
            )
            return

        if state.material_research_need == "required":
            if not state.pm_research_package_written:
                yield _step(
                    state,
                    label="pm_research_package_written",
                    action="project manager writes a bounded research package with question, route impact, allowed sources, worker owner, evidence standard, reviewer checks, and stop conditions",
                    pm_research_package_written=True,
                    active_node="record_research_tool_capability_decision",
                )
                return

            if not state.research_tool_capability_decision_recorded:
                yield _step(
                    state,
                    label="research_tool_capability_decision_recorded",
                    action="project manager records whether local, browser, web search, account, or user-provided sources are available and routes missing capabilities to user clarification, fallback, or block",
                    research_tool_capability_decision_recorded=True,
                    active_node="worker_runs_research_package",
                )
                return

            if not state.research_worker_report_returned:
                yield _step(
                    state,
                    label="research_worker_report_returned",
                    action="assigned worker searches, inspects, experiments, or reconciles sources and returns a research package report with raw evidence pointers and limitations",
                    research_worker_report_returned=True,
                    active_node="review_research_evidence_sources",
                )
                return

            if not state.research_reviewer_direct_source_check_done:
                yield _step(
                    state,
                    label="research_reviewer_direct_source_check_done",
                    action="human-like reviewer directly checks original sources, search results, logs, screenshots, or experiment outputs instead of trusting the worker summary",
                    research_reviewer_direct_source_check_done=True,
                    active_node="decide_research_sufficiency",
                )
                return

            if not state.research_reviewer_sufficiency_passed:
                if not state.research_reviewer_rework_required:
                    yield _step(
                        state,
                        label="research_reviewer_sufficiency_passed",
                        action="human-like reviewer approves the research package as sufficient for PM route or product decisions after direct source checks",
                        research_reviewer_sufficiency_passed=True,
                        active_node="absorb_research_result",
                    )
                    yield _step(
                        state,
                        label="research_reviewer_rework_required",
                        action="human-like reviewer rejects the worker research output as shallow, unsupported, stale, contradictory, or missing required source checks",
                        research_reviewer_rework_required=True,
                        active_node="worker_reworks_research_package",
                    )
                    return

                if not state.research_worker_rework_completed:
                    yield _step(
                        state,
                        label="research_worker_rework_completed",
                        action="assigned worker reruns or expands the research package according to reviewer blockers and returns corrected evidence",
                        research_worker_rework_completed=True,
                        active_node="review_reworked_research_evidence",
                    )
                    return

                if not state.research_reviewer_recheck_done:
                    yield _step(
                        state,
                        label="research_reviewer_recheck_done",
                        action="human-like reviewer rechecks the corrected research output against the original package and prior blockers",
                        research_reviewer_recheck_done=True,
                        active_node="approve_reworked_research_package",
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
                    active_node="absorb_research_result",
                )
                return

            if not state.pm_research_result_absorbed_or_route_mutated:
                yield _step(
                    state,
                    label="pm_research_result_absorbed_or_route_mutated",
                    action="project manager absorbs approved research into material understanding, product architecture inputs, route mutation, or a blocked/user-clarification decision",
                    pm_research_result_absorbed_or_route_mutated=True,
                    active_node="close_material_research_gap",
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
                active_node="product_function_architecture",
            )
            return

        if not state.product_function_architecture_pm_synthesized:
            yield _step(
                state,
                label="product_function_architecture_pm_synthesized",
                action="project manager synthesizes grilled ideas into a product-function architecture decision package before contract freeze",
                product_function_architecture_pm_synthesized=True,
                active_node="write_product_function_high_standard_posture",
            )
            return

        if not state.product_function_high_standard_posture_written:
            yield _step(
                state,
                label="product_function_high_standard_posture_written",
                action="project manager records that a FlowPilot invocation means an important project and sets the highest reasonably achievable worker standard, not the lowest viable route or a self-effort estimate",
                product_function_high_standard_posture_written=True,
                active_node="write_product_function_target_and_failure_bar",
            )
            return

        if not state.product_function_target_and_failure_bar_written:
            yield _step(
                state,
                label="product_function_target_and_failure_bar_written",
                action="project manager describes the strongest feasible product target and the rough, embarrassing, or placeholder results that must be rejected before completion",
                product_function_target_and_failure_bar_written=True,
                active_node="write_product_function_minimum_sufficient_complexity_review",
            )
            return

        if not state.product_function_minimum_sufficient_complexity_review_written:
            yield _step(
                state,
                label="product_function_minimum_sufficient_complexity_review_written",
                action="project manager records the minimum sufficient complexity review, rejecting features, surfaces, dependencies, or artifacts that do not change user outcome or proof strength",
                product_function_minimum_sufficient_complexity_review_written=True,
                active_node="write_product_function_semantic_fidelity_policy",
            )
            return

        if not state.product_function_semantic_fidelity_policy_written:
            yield _step(
                state,
                label="product_function_semantic_fidelity_policy_written",
                action="project manager maps user goals to material evidence and records that source gaps require discovery, staged delivery, or user clarification instead of silent semantic downgrade",
                product_function_semantic_fidelity_policy_written=True,
                active_node="write_product_function_user_task_map",
            )
            return

        if not state.product_function_user_task_map_written:
            yield _step(
                state,
                label="product_function_user_task_map_written",
                action="write the target users, situations, jobs-to-be-done, and decision points that the product must serve",
                product_function_user_task_map_written=True,
                active_node="write_product_function_capability_map",
            )
            return

        if not state.product_function_capability_map_written:
            yield _step(
                state,
                label="product_function_capability_map_written",
                action="write the must, should, optional, and rejected product capabilities before route generation",
                product_function_capability_map_written=True,
                active_node="write_product_function_feature_decisions",
            )
            return

        if not state.product_function_feature_decisions_written:
            yield _step(
                state,
                label="product_function_feature_decisions_written",
                action="record feature necessity decisions that bind each accepted feature to a user task and reject features without product value",
                product_function_feature_decisions_written=True,
                active_node="write_product_function_display_rationale",
            )
            return

        if not state.product_function_display_rationale_written:
            yield _step(
                state,
                label="product_function_display_rationale_written",
                action="record why each visible text, state, control, card, or status should be shown and what user decision it changes",
                product_function_display_rationale_written=True,
                active_node="review_product_function_gaps",
            )
            return

        if not state.product_function_gap_review_done:
            yield _step(
                state,
                label="product_function_missing_feature_review_done",
                action="review likely missing high-value functions before implementation turns the route into local tasks",
                product_function_gap_review_done=True,
                active_node="write_product_function_negative_scope",
            )
            return

        if not state.product_function_negative_scope_written:
            yield _step(
                state,
                label="product_function_negative_scope_written",
                action="write explicit non-goals and rejected displays so the route does not grow accidental features",
                product_function_negative_scope_written=True,
                active_node="write_product_function_acceptance_matrix",
            )
            return

        if not state.product_function_acceptance_matrix_written:
            yield _step(
                state,
                label="product_function_acceptance_matrix_written",
                action="write a functional acceptance matrix covering inputs, outputs, states, failure cases, and required evidence for each core capability",
                product_function_acceptance_matrix_written=True,
                active_node="define_root_acceptance_thresholds",
            )
            return

        if not state.root_acceptance_thresholds_defined:
            yield _step(
                state,
                label="root_acceptance_thresholds_defined",
                action="project manager defines early hard acceptance thresholds for the important root requirements before contract freeze",
                root_acceptance_thresholds_defined=True,
                active_node="write_root_acceptance_proof_matrix",
            )
            return

        if not state.root_acceptance_proof_matrix_written:
            yield _step(
                state,
                label="root_acceptance_proof_matrix_written",
                action="project manager writes the root proof matrix mapping each hard requirement to minimum experiment, inspection, evidence, owner, and approver",
                root_acceptance_proof_matrix_written=True,
                active_node="select_standard_scenario_pack",
            )
            return

        if not state.standard_scenario_pack_selected:
            yield _step(
                state,
                label="standard_scenario_pack_selected",
                action="project manager selects the standard scenario pack for terminal replay of happy paths, edge cases, regressions, lifecycle, and PM-risk scenarios",
                standard_scenario_pack_selected=True,
                active_node="product_officer_probe_product_function_architecture",
            )
            return

        if not state.product_architecture_officer_adversarial_probe_done:
            yield _step(
                state,
                label="product_architecture_officer_adversarial_probe_done",
                action="product FlowGuard officer checks modelability, missing state fields, unsupported claims, and failure paths before approving the PM architecture",
                product_architecture_officer_adversarial_probe_done=True,
                active_node="approve_product_function_architecture",
            )
            return

        if not state.product_function_architecture_product_officer_approved:
            yield _step(
                state,
                label="product_function_architecture_product_officer_approved",
                action="product FlowGuard officer approves that the PM product-function architecture is modelable and strong enough to freeze the contract from",
                product_function_architecture_product_officer_approved=True,
                active_node="reviewer_probe_product_function_architecture",
            )
            return

        if not state.product_architecture_reviewer_adversarial_probe_done:
            yield _step(
                state,
                label="product_architecture_reviewer_adversarial_probe_done",
                action="human-like reviewer attacks the PM product architecture against user tasks, inspected materials, missing features, unnecessary visible text, and weak failure states",
                product_architecture_reviewer_adversarial_probe_done=True,
                active_node="challenge_product_function_architecture",
            )
            return

        if not state.product_function_architecture_reviewer_challenged:
            yield _step(
                state,
                label="product_function_architecture_reviewer_challenged",
                action="human-like reviewer challenges the pre-implementation product-function architecture for usefulness, missing expected functions, and unnecessary visible text",
                product_function_architecture_reviewer_challenged=True,
                active_node="freeze_contract",
            )
            return

        if not state.product_architecture_self_interrogation_record_written:
            yield _step(
                state,
                label="product_architecture_self_interrogation_record_written",
                action="PM writes a durable product-architecture self-interrogation record after officer and reviewer challenge so architecture doubts have a downstream destination",
                product_architecture_self_interrogation_record_written=True,
                active_node="freeze_contract",
            )
            return

        if not state.product_architecture_self_interrogation_findings_dispositioned:
            yield _step(
                state,
                label="product_architecture_self_interrogation_findings_dispositioned",
                action="PM incorporates, defers, ledgers, rejects, or waives product-architecture self-interrogation findings before root contract freeze",
                product_architecture_self_interrogation_findings_dispositioned=True,
                active_node="freeze_contract",
            )
            return

        if not state.contract_frozen:
            yield _step(
                state,
                label="contract_frozen",
                action="freeze high-ambition acceptance floor from the PM product-function architecture after startup and product-architecture self-interrogation findings are durably dispositioned",
                contract_frozen=True,
                active_node="record_dependency_plan",
            )
            return

        if not state.dependency_plan_recorded:
            yield _step(
                state,
                label="dependency_plan_recorded",
                action="record dependency inventory and defer non-current installs",
                dependency_plan_recorded=True,
                future_installs_deferred=True,
                active_node="create_initial_route",
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
                active_node="create_heartbeat_schedule",
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
                active_node="design_flowguard_route",
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
                active_node="design_flowguard_route",
            )
            return

        if not state.pm_initial_route_decision_recorded:
            yield _step(
                state,
                label="pm_initial_route_decision_recorded",
                action="ask the project manager to choose the initial route-design direction from the contract, self-interrogation, dependencies, and crew reports",
                pm_initial_route_decision_recorded=True,
                active_node="select_child_skills",
            )
            return

        if not state.pm_child_skill_selection_manifest_written:
            yield _step(
                state,
                label="pm_child_skill_selection_manifest_written",
                action="project manager writes a child-skill selection manifest from the product architecture, route direction, and local skill inventory",
                pm_child_skill_selection_manifest_written=True,
                active_node="record_child_skill_minimum_sufficient_complexity",
            )
            return

        if not state.pm_child_skill_minimum_sufficient_complexity_review_written:
            yield _step(
                state,
                label="pm_child_skill_minimum_sufficient_complexity_review_written",
                action="project manager records simpler-path review for selected child skills and requires each required skill to justify its added handoffs, gates, references, or artifacts",
                pm_child_skill_minimum_sufficient_complexity_review_written=True,
                active_node="classify_child_skill_selection_scope",
            )
            return

        if not state.pm_child_skill_selection_scope_decisions_recorded:
            yield _step(
                state,
                label="pm_child_skill_selection_scope_decisions_recorded",
                action="project manager classifies candidate skills as required, conditional, deferred, or rejected before child-skill gate discovery",
                pm_child_skill_selection_scope_decisions_recorded=True,
                active_node="discover_child_skill_gates",
            )
            return

        if not state.child_skill_route_design_discovery_started:
            yield _step(
                state,
                label="child_skill_route_design_discovery_started",
                action="project manager discovers gate surfaces only from PM-selected child skills, not from raw local skill availability",
                child_skill_route_design_discovery_started=True,
                active_node="extract_child_skill_gate_manifest",
            )
            return

        if not state.child_skill_initial_gate_manifest_extracted:
            yield _step(
                state,
                label="child_skill_initial_gate_manifest_extracted",
                action="project manager extracts child-skill stages, standards, checks, evidence needs, and skipped references into an initial gate manifest",
                child_skill_initial_gate_manifest_extracted=True,
                active_node="assign_child_skill_gate_approvers",
            )
            return

        if not state.child_skill_gate_approvers_assigned:
            yield _step(
                state,
                label="child_skill_gate_approvers_assigned",
                action="project manager assigns required approver roles for every child-skill gate and forbids controller or worker self-approval",
                child_skill_gate_approvers_assigned=True,
                active_node="probe_child_skill_gate_manifest",
            )
            return

        if not state.child_skill_manifest_independent_validation_done:
            yield _step(
                state,
                label="child_skill_manifest_independent_validation_done",
                action="PM and human-like reviewer independently probe child-skill manifest slices instead of accepting the extraction report",
                child_skill_manifest_independent_validation_done=True,
                active_node="review_child_skill_gate_manifest",
            )
            return

        if not state.child_skill_manifest_reviewer_reviewed:
            yield _step(
                state,
                label="child_skill_manifest_reviewer_reviewed",
                action="human-like reviewer reviews product, visual, interaction, and real-use child-skill gates before route freeze",
                child_skill_manifest_reviewer_reviewed=True,
                active_node="pm_approve_child_skill_manifest",
            )
            return

        if not state.child_skill_manifest_pm_approved_for_route:
            yield _step(
                state,
                label="child_skill_manifest_pm_approved_for_route",
                action="project manager approves the child-skill gate manifest for inclusion in route modeling, the execution frontier, and the PM runway",
                child_skill_manifest_pm_approved_for_route=True,
                active_node="design_flowguard_route",
            )
            return

        if not state.flowguard_process_design_done:
            yield _step(
                state,
                label="flowguard_process_designed",
                action="process FlowGuard officer uses FlowGuard to design the route before implementation",
                flowguard_process_design_done=True,
                active_node="generate_candidate_route_tree",
            )
            return

        if not state.candidate_route_tree_generated:
            yield _step(
                state,
                label="candidate_route_tree_generated",
                action="generate candidate route tree from the frozen contract",
                candidate_route_tree_generated=True,
                active_node="write_recursive_decomposition_policy",
            )
            return

        if not state.recursive_route_decomposition_policy_written:
            yield _step(
                state,
                label="recursive_route_decomposition_policy_written",
                action="project manager records arbitrary-depth route decomposition, shallow display projection, PMK route memory, and split/merge stop rules before route checks",
                recursive_route_decomposition_policy_written=True,
                route_reviewer_depth_review_required=True,
                active_node="define_leaf_readiness_gates",
            )
            return

        if not state.route_leaf_readiness_gates_defined:
            yield _step(
                state,
                label="route_leaf_readiness_gates_defined",
                action="project manager defines leaf-readiness gates for dispatchable leaves and marks parent/module nodes as non-worker-dispatchable",
                route_leaf_readiness_gates_defined=True,
                active_node="check_root_route_model",
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
                active_node="check_root_route_model",
            )
            return

        if not state.root_route_model_checked:
            yield _step(
                state,
                label="root_route_model_checked",
                action="process FlowGuard officer approves checks against the candidate route tree from officer-owned adversarial model evidence",
                root_route_model_checked=True,
                root_route_model_process_officer_approved=True,
                active_node="check_root_product_function_model",
            )
            return

        if not state.root_product_function_model_checked:
            yield _step(
                state,
                label="root_product_function_model_checked",
                action="product FlowGuard officer approves checks against the root product-function model from officer-owned adversarial model evidence",
                root_product_function_model_checked=True,
                root_product_function_model_product_officer_approved=True,
                active_node="check_strict_gate_obligation_review_model",
            )
            return

        if not state.strict_gate_obligation_review_model_checked:
            yield _step(
                state,
                label="strict_gate_obligation_review_model_checked",
                action="process FlowGuard officer runs the strict gate-obligation model so current-scope caveats cannot close a review gate",
                strict_gate_obligation_review_model_checked=True,
                active_node="create_initial_route",
            )
            return

        if state.route_version == 0:
            yield _step(
                state,
                label="route_created",
                action="freeze checked candidate tree as canonical flow.json route",
                route_version=1,
                route_checked=False,
                markdown_synced=False,
                execution_frontier_written=False,
                codex_plan_synced=False,
                frontier_version=0,
                plan_version=0,
                active_node="run_meta_model_checks",
            )
            return

        if not state.route_checked:
            if state.route_revisions > MAX_ROUTE_REVISIONS:
                yield _step(
                    state,
                    label="blocked_after_repeated_route_failures",
                    action="block because route model cannot be stabilized and emit a nonterminal resume notice",
                    status="blocked",
                    heartbeat_active=False,
                    controlled_stop_notice_recorded=True,
                    pause_snapshot_written=True,
                    active_node="blocked",
                )
                return
            yield _step(
                state,
                label="route_model_checked",
                action="run FlowGuard checks for active route",
                route_checked=True,
                active_node="check_router_leaf_only_dispatch_policy",
            )
            return

        if not state.router_leaf_only_dispatch_policy_checked:
            yield _step(
                state,
                label="router_leaf_only_dispatch_policy_checked",
                action="process model verifies Router can traverse the full route tree, dispatch only ready leaf/repair nodes, and send parent/module nodes to child subtree or backward replay",
                router_leaf_only_dispatch_policy_checked=True,
                active_node="record_parent_backward_trigger_rule",
            )
            return

        if not state.parent_backward_structural_trigger_rule_recorded:
            yield _step(
                state,
                label="parent_backward_structural_trigger_rule_recorded",
                action="project manager records the structural trigger: every effective route node with children requires local parent backward replay, without semantic importance guessing",
                parent_backward_structural_trigger_rule_recorded=True,
                active_node="enumerate_parent_backward_targets",
            )
            return

        if not state.parent_backward_review_targets_enumerated:
            yield _step(
                state,
                label="parent_backward_review_targets_enumerated",
                action="project manager enumerates all effective parent/composite nodes directly from flow.json before route execution or after route mutation",
                parent_backward_review_targets_enumerated=True,
                active_node="record_user_flow_shallow_projection_policy",
            )
            return

        if not state.user_flow_diagram_shallow_projection_policy_recorded:
            yield _step(
                state,
                label="user_flow_diagram_shallow_projection_policy_recorded",
                action="record that user-visible route signs render only the shallow route projection while showing the active deep path and hidden leaf progress",
                user_flow_diagram_shallow_projection_policy_recorded=True,
                active_node="sync_markdown_summary",
            )
            return

        if not state.markdown_synced:
            yield _step(
                state,
                label="markdown_summary_synced",
                action="sync English Markdown summary from canonical JSON",
                markdown_synced=True,
                active_node="write_execution_frontier",
            )
            return

        if not state.execution_frontier_written:
            yield _step(
                state,
                label="execution_frontier_written",
                action="write execution_frontier.json from checked route, active node, next node, and current mainline",
                execution_frontier_written=True,
                frontier_version=state.route_version,
                active_node="sync_codex_plan",
            )
            return

        if not state.codex_plan_synced:
            yield _step(
                state,
                label="codex_plan_synced",
                action="sync current visible Codex plan from execution frontier without changing heartbeat automation prompt",
                codex_plan_synced=True,
                plan_version=state.frontier_version,
                active_node="refresh_user_flow_diagram",
            )
            return

        if not state.user_flow_diagram_refreshed:
            yield _step(
                state,
                label="user_flow_diagram_refreshed",
                action="refresh single user flow diagram from checked flow.json and execution_frontier.json before chat or UI display",
                user_flow_diagram_refreshed=True,
                active_node="emit_user_flow_diagram",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and not state.visible_user_flow_diagram_emitted
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="visible_user_flow_diagram_emitted",
                action="emit simplified English FlowPilot Route Sign Mermaid in chat when Cockpit UI is not open, with current node, next jumps, checks, fallback branches, and simulated path",
                visible_user_flow_diagram_emitted=True,
                user_flow_diagram_chat_display_required=True,
                user_flow_diagram_chat_displayed=True,
                user_flow_diagram_return_edge_present=state.user_flow_diagram_return_edge_required,
                user_flow_diagram_reviewer_display_checked=False,
                user_flow_diagram_reviewer_route_match_checked=False,
                user_flow_diagram_fresh_for_current_node=False,
                active_node="resolve_live_subagent_startup",
            )
            return

        if (
            state.visible_user_flow_diagram_emitted
            and state.user_flow_diagram_refreshed
            and not state.user_flow_diagram_reviewer_display_checked
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="user_flow_diagram_reviewer_display_checked",
                action="human-like reviewer checks the visible chat Mermaid route sign, active route/node match, and return-for-repair edge before route progress",
                user_flow_diagram_reviewer_display_checked=True,
                user_flow_diagram_reviewer_route_match_checked=True,
                user_flow_diagram_fresh_for_current_node=True,
                active_node="resolve_live_subagent_startup",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.user_flow_diagram_refreshed
            and _user_flow_display_gate_passed(state)
            and not state.live_subagent_decision_recorded
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="live_subagent_start_authorized",
                action="ask for and record user authorization to start the six live FlowPilot background agents",
                live_subagent_decision_recorded=True,
                active_node="start_live_subagents",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.user_flow_diagram_refreshed
            and _user_flow_display_gate_passed(state)
            and state.live_subagent_decision_recorded
            and not state.live_subagents_started
            and not state.single_agent_role_continuity_authorized
            and state.issue == "none"
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
                active_node="startup_preflight_review",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.user_flow_diagram_refreshed
            and _user_flow_display_gate_passed(state)
            and _live_subagent_startup_resolved(state)
            and not state.startup_preflight_review_report_written
            and not state.startup_worker_remediation_completed
            and state.issue == "none"
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
                active_node="pm_interprets_startup_review",
            )
            return

        if (
            state.startup_preflight_review_report_written
            and state.startup_preflight_review_blocking_findings
            and not state.pm_returned_startup_blockers
            and not state.startup_worker_remediation_completed
            and not state.pm_start_gate_opened
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="pm_returns_startup_blockers_to_worker",
                action="project manager reads reviewer startup report and returns concrete blockers to workers for remediation",
                pm_returned_startup_blockers=True,
                active_node="startup_worker_remediation",
            )
            return

        if (
            state.startup_preflight_review_report_written
            and state.startup_preflight_review_blocking_findings
            and state.pm_returned_startup_blockers
            and not state.startup_worker_remediation_completed
            and not state.pm_start_gate_opened
            and state.issue == "none"
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
                active_node="startup_preflight_review",
            )
            return

        if (
            state.route_version > 0
            and state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.user_flow_diagram_refreshed
            and _user_flow_display_gate_passed(state)
            and _live_subagent_startup_resolved(state)
            and not state.startup_preflight_review_report_written
            and state.startup_worker_remediation_completed
            and state.issue == "none"
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
                active_node="pm_interprets_startup_review",
            )
            return

        if (
            state.startup_preflight_review_report_written
            and not state.startup_preflight_review_blocking_findings
            and not state.startup_pm_independent_gate_audit_done
            and not state.pm_start_gate_opened
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="startup_pm_independent_gate_audit_done",
                action="PM independently audits startup run isolation, prior-work boundary, live-agent freshness or authorized continuity, reviewer evidence paths, and report-only failure hypotheses before opening the start gate",
                startup_pm_independent_gate_audit_done=True,
                startup_pm_capability_resolution_recorded=True,
                active_node="pm_start_gate_decision",
            )
            return

        if (
            state.startup_preflight_review_report_written
            and not state.startup_preflight_review_blocking_findings
            and state.startup_pm_independent_gate_audit_done
            and not state.pm_start_gate_opened
            and state.issue == "none"
        ):
            yield _step(
                state,
                label="pm_start_gate_opened_from_fact_report",
                action="project manager opens startup and allows work beyond startup from the current clean factual reviewer report",
                pm_start_gate_opened=True,
                work_beyond_startup_allowed=True,
                active_node="ready_for_chunk",
            )
            return

        if state.high_risk_gate == "pending":
            yield _step(
                state,
                label="high_risk_gate_approved",
                action="user approves hard safety gate",
                high_risk_gate="approved",
                active_node="ready_for_chunk",
            )
            yield _step(
                state,
                label="blocked_by_high_risk_denial",
                action="block because high-risk gate was denied and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                high_risk_gate="denied",
                active_node="blocked",
            )
            return

        if state.issue == "terminal_backward_review_failure":
            if (
                state.pm_repair_decision_interrogations
                <= state.human_inspection_repairs
                + state.composite_structural_route_repairs
                + state.terminal_human_backward_replay_repairs
            ):
                yield _step(
                    state,
                    label="terminal_human_backward_pm_repair_decision_interrogated",
                    action="PM decides the terminal backward replay repair target, affected downstream nodes, stale evidence, and whether the restarted final review begins at the delivered product or an impacted ancestor",
                    pm_repair_decision_interrogations=(
                        state.pm_repair_decision_interrogations + 1
                    ),
                    active_node="pm_terminal_backward_replay_repair_strategy",
                )
                return
            yield _step(
                state,
                label="route_updated_after_terminal_human_backward_replay_failure",
                action="mutate the route to repair a terminal human backward replay finding, invalidate affected downstream evidence, and require a rebuilt ledger plus restarted final review",
                route_version=state.route_version + 1,
                route_checked=False,
                markdown_synced=False,
                execution_frontier_written=False,
                codex_plan_synced=False,
                frontier_version=0,
                plan_version=0,
                visible_user_flow_diagram_emitted=False,
                user_flow_diagram_refreshed=False,
                user_flow_diagram_reviewer_display_checked=False,
                user_flow_diagram_reviewer_route_match_checked=False,
                flowguard_process_design_done=False,
                flowguard_officer_model_adversarial_probe_done=False,
                flowguard_model_report_risk_tiers_done=False,
                flowguard_model_report_pm_review_agenda_done=False,
                flowguard_model_report_toolchain_recommendations_done=False,
                flowguard_model_report_confidence_boundary_done=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
                child_skill_manifest_independent_validation_done=False,
                child_skill_manifest_reviewer_reviewed=False,
                child_skill_manifest_process_officer_approved=False,
                child_skill_manifest_product_officer_approved=False,
                child_skill_manifest_pm_approved_for_route=False,
                candidate_route_tree_generated=False,
                root_route_model_checked=False,
                root_route_model_process_officer_approved=False,
                root_product_function_model_checked=False,
                root_product_function_model_product_officer_approved=False,
                strict_gate_obligation_review_model_checked=False,
                parent_backward_review_targets_enumerated=False,
                parent_subtree_review_checked=False,
                issue="none",
                terminal_human_backward_replay_repairs=(
                    state.terminal_human_backward_replay_repairs + 1
                ),
                required_chunks=state.required_chunks,
                completed_chunks=max(0, state.completed_chunks - 1),
                node_human_inspections_passed=max(
                    0, state.node_human_inspections_passed - 1
                ),
                composite_backward_reviews_passed=max(
                    0, state.composite_backward_reviews_passed - 1
                ),
                composite_backward_pm_segment_decisions_recorded=max(
                    0, state.composite_backward_pm_segment_decisions_recorded - 1
                ),
                chunk_state="none",
                verification_defined=False,
                checkpoint_written=False,
                parent_focused_interrogation_done=False,
                parent_focused_interrogation_questions=0,
                parent_focused_interrogation_scope_id="",
                unfinished_current_node_recovery_checked=False,
                node_focused_interrogation_done=False,
                node_focused_interrogation_questions=0,
                node_focused_interrogation_scope_id="",
                lightweight_self_check_done=False,
                lightweight_self_check_questions=0,
                lightweight_self_check_scope_id="",
                node_visible_roadmap_emitted=False,
                completion_self_interrogation_done=False,
                completion_self_interrogation_questions=0,
                completion_self_interrogation_layer_count=0,
                completion_self_interrogation_questions_per_layer=0,
                completion_self_interrogation_layers=0,
                completion_self_interrogation_record_written=False,
                completion_self_interrogation_findings_dispositioned=False,
                completion_visible_roadmap_emitted=False,
                high_value_work_review="unknown",
                final_feature_matrix_review_done=False,
                final_acceptance_matrix_review_done=False,
                final_standard_scenario_pack_replayed=False,
                final_quality_candidate_review_done=False,
                final_product_function_model_replayed=False,
                final_product_model_officer_adversarial_probe_done=False,
                final_product_function_model_product_officer_approved=False,
                final_human_review_context_loaded=False,
                final_human_neutral_observation_written=False,
                final_human_manual_experiments_run=False,
                final_human_reviewer_independent_probe_done=False,
                final_human_inspection_passed=False,
                final_human_review_reviewer_approved=False,
                pm_completion_decision_recorded=False,
                active_node="run_terminal_backward_replay_repair_route_checks",
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue == "model_gap":
            if state.route_revisions >= MAX_ROUTE_REVISIONS:
                yield _step(
                    state,
                    label="blocked_after_model_gap_budget",
                    action="block after exhausting model update budget and emit a nonterminal resume notice",
                    status="blocked",
                    heartbeat_active=False,
                    controlled_stop_notice_recorded=True,
                    pause_snapshot_written=True,
                    active_node="blocked",
                )
                return
            yield _step(
                state,
                label="route_updated_after_model_gap",
                action="create new route version from refined model",
                route_version=state.route_version + 1,
                route_checked=False,
                markdown_synced=False,
                execution_frontier_written=False,
                codex_plan_synced=False,
                frontier_version=0,
                plan_version=0,
                visible_user_flow_diagram_emitted=False,
                user_flow_diagram_refreshed=False,
                user_flow_diagram_reviewer_display_checked=False,
                user_flow_diagram_reviewer_route_match_checked=False,
                flowguard_process_design_done=False,
                flowguard_officer_model_adversarial_probe_done=False,
                flowguard_model_report_risk_tiers_done=False,
                flowguard_model_report_pm_review_agenda_done=False,
                flowguard_model_report_toolchain_recommendations_done=False,
                flowguard_model_report_confidence_boundary_done=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
                child_skill_manifest_independent_validation_done=False,
                child_skill_manifest_reviewer_reviewed=False,
                child_skill_manifest_process_officer_approved=False,
                child_skill_manifest_product_officer_approved=False,
                child_skill_manifest_pm_approved_for_route=False,
                candidate_route_tree_generated=False,
                root_route_model_checked=False,
                root_route_model_process_officer_approved=False,
                root_product_function_model_checked=False,
                root_product_function_model_product_officer_approved=False,
                strict_gate_obligation_review_model_checked=False,
                parent_backward_review_targets_enumerated=False,
                parent_subtree_review_checked=False,
                parent_focused_interrogation_done=False,
                parent_focused_interrogation_questions=0,
                parent_focused_interrogation_scope_id="",
                unfinished_current_node_recovery_checked=False,
                issue="none",
                route_revisions=state.route_revisions + 1,
                chunk_state="none",
                verification_defined=False,
                checkpoint_written=False,
                node_focused_interrogation_done=False,
                node_focused_interrogation_questions=0,
                node_focused_interrogation_scope_id="",
                lightweight_self_check_done=False,
                lightweight_self_check_questions=0,
                lightweight_self_check_scope_id="",
                node_visible_roadmap_emitted=False,
                active_node="run_updated_meta_model_checks",
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue == "composite_backward_failure":
            if not state.composite_issue_grilled:
                yield _step(
                    state,
                    label="composite_backward_issue_grilled",
                    action="grill the failed composite backward review until it names the affected child, sibling gap, or subtree rebuild target",
                    composite_issue_grilled=True,
                    active_node="route_mutation_from_composite_backward_issue",
                )
                return
            if state.route_revisions >= MAX_ROUTE_REVISIONS:
                yield _step(
                    state,
                    label="blocked_after_composite_backward_repair_budget",
                    action="block after exhausting composite backward structural repair route budget and emit a nonterminal resume notice",
                    status="blocked",
                    heartbeat_active=False,
                    controlled_stop_notice_recorded=True,
                    pause_snapshot_written=True,
                    active_node="blocked",
                )
                return
            if (
                state.pm_repair_decision_interrogations
                <= state.human_inspection_repairs
                + state.composite_structural_route_repairs
            ):
                yield _step(
                    state,
                    label="pm_repair_decision_interrogated",
                    action="grill the project manager on composite repair strategy before choosing existing-child rework, sibling insertion, subtree rebuild, or parent impact bubbling",
                    pm_repair_decision_interrogations=(
                        state.pm_repair_decision_interrogations + 1
                    ),
                    active_node="pm_composite_repair_strategy_decision",
                )
                return

            common_changes = {
                "route_version": state.route_version + 1,
                "route_checked": False,
                "markdown_synced": False,
                "execution_frontier_written": False,
                "codex_plan_synced": False,
                "frontier_version": 0,
                "plan_version": 0,
                "visible_user_flow_diagram_emitted": False,
                "user_flow_diagram_refreshed": False,
                "user_flow_diagram_reviewer_display_checked": False,
                "user_flow_diagram_reviewer_route_match_checked": False,
                "candidate_route_tree_generated": False,
                "root_route_model_checked": False,
                "root_route_model_process_officer_approved": False,
                "root_product_function_model_checked": False,
                "root_product_function_model_product_officer_approved": False,
                "strict_gate_obligation_review_model_checked": False,
                "parent_backward_review_targets_enumerated": False,
                "parent_subtree_review_checked": False,
                "parent_focused_interrogation_done": False,
                "parent_focused_interrogation_questions": 0,
                "parent_focused_interrogation_scope_id": "",
                "unfinished_current_node_recovery_checked": False,
                "issue": "none",
                "route_revisions": state.route_revisions + 1,
                "chunk_state": "none",
                "verification_defined": False,
                "checkpoint_written": False,
                "node_focused_interrogation_done": False,
                "node_focused_interrogation_questions": 0,
                "node_focused_interrogation_scope_id": "",
                "lightweight_self_check_done": False,
                "lightweight_self_check_questions": 0,
                "lightweight_self_check_scope_id": "",
                "node_visible_roadmap_emitted": False,
                "composite_structural_route_repairs": state.composite_structural_route_repairs + 1,
                "active_node": "run_composite_backward_structural_route_checks",
            }

            if state.composite_issue_strategy == "existing_child":
                yield _step(
                    state,
                    label="route_updated_to_rework_composite_child",
                    action="mutate the route to jump back to the affected existing child node and invalidate its parent rollup",
                    completed_chunks=max(0, state.completed_chunks - 1),
                    node_human_inspections_passed=max(
                        0, state.node_human_inspections_passed - 1
                    ),
                    composite_backward_reviews_passed=max(
                        0, state.composite_backward_reviews_passed - 1
                    ),
                    composite_backward_pm_segment_decisions_recorded=max(
                        0, state.composite_backward_pm_segment_decisions_recorded - 1
                    ),
                    **common_changes,
                    **_reset_execution_scope_gates(),
                )
                return

            if state.composite_issue_strategy == "add_sibling":
                yield _step(
                    state,
                    label="route_updated_to_add_composite_sibling",
                    action="mutate the route to insert an adjacent sibling child before the parent can close",
                    required_chunks=state.required_chunks + 1,
                    completed_chunks=max(0, state.completed_chunks - 1),
                    node_human_inspections_passed=max(
                        0, state.node_human_inspections_passed - 1
                    ),
                    composite_backward_reviews_passed=max(
                        0, state.composite_backward_reviews_passed - 1
                    ),
                    composite_backward_pm_segment_decisions_recorded=max(
                        0, state.composite_backward_pm_segment_decisions_recorded - 1
                    ),
                    composite_new_sibling_nodes=state.composite_new_sibling_nodes + 1,
                    **common_changes,
                    **_reset_execution_scope_gates(),
                )
                return

            yield _step(
                state,
                label="route_updated_to_rebuild_composite_subtree",
                action="mutate the route to rebuild the whole child subtree from the parent model",
                required_chunks=TARGET_CHUNKS,
                completed_chunks=0,
                node_human_inspections_passed=0,
                composite_backward_reviews_passed=0,
                composite_backward_pm_segment_decisions_recorded=0,
                composite_subtree_rebuilds=state.composite_subtree_rebuilds + 1,
                **common_changes,
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue == "inspection_failure":
            if state.blocking_defect_open and not state.pm_defect_triage_done:
                yield _step(
                    state,
                    label="pm_triages_blocking_human_review_defect",
                    action="PM reads the defect ledger entry, assigns severity, owner, route impact, and same-class recheck condition before repair routing",
                    pm_defect_triage_done=True,
                    active_node="pm_inspection_repair_strategy_decision",
                )
                return
            if not state.inspection_issue_grilled:
                yield _step(
                    state,
                    label="human_inspection_issue_grilled",
                    action="grill the failed human-like inspection until it has evidence, severity, repair target, and recheck condition",
                    inspection_issue_grilled=True,
                    active_node="route_mutation_from_inspection_issue",
                )
                return
            if state.route_revisions >= MAX_ROUTE_REVISIONS:
                yield _step(
                    state,
                    label="blocked_after_inspection_repair_budget",
                    action="block after exhausting inspection-driven repair route budget and emit a nonterminal resume notice",
                    status="blocked",
                    heartbeat_active=False,
                    controlled_stop_notice_recorded=True,
                    pause_snapshot_written=True,
                    active_node="blocked",
                )
                return
            if (
                state.pm_repair_decision_interrogations
                <= state.human_inspection_repairs
                + state.composite_structural_route_repairs
            ):
                yield _step(
                    state,
                    label="pm_repair_decision_interrogated",
                    action="grill the project manager on inspection-failure repair strategy before route mutation: affected level, reset/add/split/rebuild choice, stale evidence, and recheck condition",
                    pm_repair_decision_interrogations=(
                        state.pm_repair_decision_interrogations + 1
                    ),
                    active_node="pm_inspection_repair_strategy_decision",
                )
                return
            yield _step(
                state,
                label="route_updated_after_human_inspection_failure",
                action="mutate the route with a repair node after human-like inspection rejects the current product evidence",
                route_version=state.route_version + 1,
                route_checked=False,
                markdown_synced=False,
                execution_frontier_written=False,
                codex_plan_synced=False,
                frontier_version=0,
                plan_version=0,
                visible_user_flow_diagram_emitted=False,
                user_flow_diagram_refreshed=False,
                user_flow_diagram_reviewer_display_checked=False,
                user_flow_diagram_reviewer_route_match_checked=False,
                flowguard_process_design_done=False,
                flowguard_officer_model_adversarial_probe_done=False,
                flowguard_model_report_risk_tiers_done=False,
                flowguard_model_report_pm_review_agenda_done=False,
                flowguard_model_report_toolchain_recommendations_done=False,
                flowguard_model_report_confidence_boundary_done=False,
                child_skill_route_design_discovery_started=False,
                child_skill_initial_gate_manifest_extracted=False,
                child_skill_gate_approvers_assigned=False,
                child_skill_manifest_independent_validation_done=False,
                child_skill_manifest_reviewer_reviewed=False,
                child_skill_manifest_process_officer_approved=False,
                child_skill_manifest_product_officer_approved=False,
                child_skill_manifest_pm_approved_for_route=False,
                candidate_route_tree_generated=False,
                root_route_model_checked=False,
                root_route_model_process_officer_approved=False,
                root_product_function_model_checked=False,
                root_product_function_model_product_officer_approved=False,
                strict_gate_obligation_review_model_checked=False,
                parent_backward_review_targets_enumerated=False,
                parent_subtree_review_checked=False,
                issue="none",
                route_revisions=state.route_revisions + 1,
                human_inspection_repairs=state.human_inspection_repairs + 1,
                blocking_defect_open=False,
                blocking_defect_fixed_pending_recheck=True,
                defect_same_class_recheck_done=False,
                chunk_state="none",
                verification_defined=False,
                checkpoint_written=False,
                node_focused_interrogation_done=False,
                node_focused_interrogation_questions=0,
                node_focused_interrogation_scope_id="",
                lightweight_self_check_done=False,
                lightweight_self_check_questions=0,
                lightweight_self_check_scope_id="",
                node_visible_roadmap_emitted=False,
                active_node="run_human_inspection_repair_model_checks",
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue == "impl_failure":
            if state.impl_retries < MAX_IMPL_RETRIES:
                yield _step(
                    state,
                    label="implementation_fixed_for_retry",
                    action="fix implementation and retry same verified chunk boundary",
                    issue="none",
                    impl_retries=state.impl_retries + 1,
                    chunk_state="ready",
                    verification_defined=True,
                    active_node="execute_chunk",
                )
                return
            yield _step(
                state,
                label="implementation_failure_to_experiment",
                action="switch repeated implementation failure into bounded experiment",
                issue="unknown_failure",
                chunk_state="none",
                verification_defined=False,
                active_node="bounded_experiment",
                **_reset_execution_scope_gates(),
            )
            return

        if state.issue in {"unknown_failure", "no_progress"}:
            if state.experiments < MAX_EXPERIMENTS:
                yield _step(
                    state,
                    label="experiment_found_new_path",
                    action="record bounded experiment and create revised route",
                    route_version=state.route_version + 1,
                    route_checked=False,
                    markdown_synced=False,
                    execution_frontier_written=False,
                    codex_plan_synced=False,
                    frontier_version=0,
                    plan_version=0,
                    visible_user_flow_diagram_emitted=False,
                    user_flow_diagram_refreshed=False,
                    user_flow_diagram_reviewer_display_checked=False,
                    user_flow_diagram_reviewer_route_match_checked=False,
                    flowguard_process_design_done=False,
                    flowguard_officer_model_adversarial_probe_done=False,
                    flowguard_model_report_risk_tiers_done=False,
                    flowguard_model_report_pm_review_agenda_done=False,
                    flowguard_model_report_toolchain_recommendations_done=False,
                    flowguard_model_report_confidence_boundary_done=False,
                    child_skill_route_design_discovery_started=False,
                    child_skill_initial_gate_manifest_extracted=False,
                    child_skill_gate_approvers_assigned=False,
                    child_skill_manifest_independent_validation_done=False,
                    child_skill_manifest_reviewer_reviewed=False,
                    child_skill_manifest_process_officer_approved=False,
                    child_skill_manifest_product_officer_approved=False,
                    child_skill_manifest_pm_approved_for_route=False,
                    candidate_route_tree_generated=False,
                    root_route_model_checked=False,
                    root_route_model_process_officer_approved=False,
                    root_product_function_model_checked=False,
                    root_product_function_model_product_officer_approved=False,
                    strict_gate_obligation_review_model_checked=False,
                    parent_backward_review_targets_enumerated=False,
                    parent_subtree_review_checked=False,
                    parent_focused_interrogation_done=False,
                    parent_focused_interrogation_questions=0,
                    parent_focused_interrogation_scope_id="",
                    unfinished_current_node_recovery_checked=False,
                    issue="none",
                    experiments=state.experiments + 1,
                    route_revisions=state.route_revisions + 1,
                    node_focused_interrogation_done=False,
                    node_focused_interrogation_questions=0,
                    node_focused_interrogation_scope_id="",
                    lightweight_self_check_done=False,
                    lightweight_self_check_questions=0,
                    lightweight_self_check_scope_id="",
                    node_visible_roadmap_emitted=False,
                    active_node="run_experiment_route_checks",
                    **_reset_execution_scope_gates(),
                )
                return
            yield _step(
                state,
                label="blocked_after_experiment_budget",
                action="block after bounded experiments fail to find a path and emit a nonterminal resume notice",
                status="blocked",
                heartbeat_active=False,
                controlled_stop_notice_recorded=True,
                pause_snapshot_written=True,
                active_node="blocked",
            )
            return

        if state.chunk_state == "checkpoint_pending":
            if not state.composite_backward_context_loaded:
                yield _step(
                    state,
                    label="composite_backward_context_loaded",
                    action="load child evidence, parent goal, product-function model, and route structure before composite closure",
                    composite_backward_context_loaded=True,
                    active_node="replay_composite_child_evidence",
                )
                return
            if not state.composite_child_evidence_replayed:
                yield _step(
                    state,
                    label="composite_child_evidence_replayed",
                    action="replay child evidence backward against the parent/composite product model",
                    composite_child_evidence_replayed=True,
                    active_node="observe_composite_rollup",
                )
                return
            if not state.composite_backward_neutral_observation_written:
                yield _step(
                    state,
                    label="composite_backward_neutral_observation_written",
                    action="write a neutral observation of what the child rollup actually shows before judging parent closure",
                    composite_backward_neutral_observation_written=True,
                    active_node="decide_composite_structure_fit",
                )
                return
            if not state.composite_structure_decision_recorded:
                yield _step(
                    state,
                    label="composite_structure_decision_recorded",
                    action="classify whether the parent can close, needs an existing child rework, needs a sibling child, or needs subtree rebuild",
                    composite_structure_decision_recorded=True,
                    active_node="composite_backward_human_review",
                )
                return
            if not state.composite_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="composite_reviewer_independent_probe_done",
                    action="composite backward reviewer independently probes child evidence, parent model fit, missing sibling paths, stale artifacts, and report-only failure hypotheses before approving closure",
                    composite_reviewer_independent_probe_done=True,
                    active_node="composite_backward_human_review",
                )
                return
            if not state.composite_backward_human_review_passed:
                if state.composite_structural_route_repairs < MAX_COMPOSITE_STRUCTURAL_REPAIRS:
                    yield _step(
                        state,
                        label="composite_backward_review_found_existing_child_gap",
                        action="composite backward reviewer rejects parent closure and targets an existing child for rework",
                        issue="composite_backward_failure",
                        composite_issue_strategy="existing_child",
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        active_node="grill_composite_backward_issue",
                    )
                    yield _step(
                        state,
                        label="composite_backward_review_found_missing_sibling",
                        action="composite backward reviewer rejects parent closure because an adjacent sibling child is missing",
                        issue="composite_backward_failure",
                        composite_issue_strategy="add_sibling",
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        active_node="grill_composite_backward_issue",
                    )
                    yield _step(
                        state,
                        label="composite_backward_review_found_subtree_mismatch",
                        action="composite backward reviewer rejects parent closure and requires child subtree rebuild",
                        issue="composite_backward_failure",
                        composite_issue_strategy="rebuild_subtree",
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        active_node="grill_composite_backward_issue",
                    )
                    return
                yield _step(
                    state,
                    label="composite_backward_review_passed",
                    action="human-like composite backward reviewer accepts the child rollup before PM decides the parent segment",
                    composite_backward_human_review_passed=True,
                    composite_backward_review_reviewer_approved=True,
                    composite_backward_reviews_passed=state.composite_backward_reviews_passed + 1,
                    active_node="record_parent_backward_pm_segment_decision",
                )
                return
            if not state.composite_backward_pm_segment_decision_recorded:
                yield _step(
                    state,
                    label="composite_backward_pm_segment_decision_recorded",
                    action="project manager records the parent backward replay segment decision before parent checkpoint closure",
                    composite_backward_pm_segment_decision_recorded=True,
                    composite_backward_pm_segment_decisions_recorded=state.composite_backward_pm_segment_decisions_recorded
                    + 1,
                    active_node="write_checkpoint",
                )
                return
            if not state.role_memory_refreshed_after_work:
                yield _step(
                    state,
                    label="role_memory_packets_refreshed_after_work",
                    action="refresh compact role memory packets after meaningful role work and before checkpoint",
                    role_memory_refreshed_after_work=True,
                    active_node="write_checkpoint",
                )
                return
            yield _step(
                state,
                label="checkpoint_written",
                action="write verified checkpoint; when another route node remains, invalidate old route-sign display evidence before the next node entry",
                checkpoint_written=True,
                chunk_state="none",
                heartbeat_health_checked=False,
                parent_focused_interrogation_done=False,
                parent_focused_interrogation_questions=0,
                parent_focused_interrogation_scope_id="",
                node_focused_interrogation_done=False,
                node_focused_interrogation_questions=0,
                node_focused_interrogation_scope_id="",
                lightweight_self_check_done=False,
                lightweight_self_check_questions=0,
                lightweight_self_check_scope_id="",
                node_visible_roadmap_emitted=False,
                parent_subtree_review_checked=False,
                unfinished_current_node_recovery_checked=False,
                active_node="refresh_user_flow_diagram"
                if state.completed_chunks < state.required_chunks
                else "ready_to_complete",
                **(
                    _reset_user_flow_diagram_gate()
                    if state.completed_chunks < state.required_chunks
                    else {}
                ),
                **_reset_execution_scope_gates(),
            )
            return

        if (
            state.completed_chunks >= state.required_chunks
            and state.checkpoint_written
            and _route_ready(state)
            and state.subagent_status not in {"pending", "returned"}
        ):
            if not state.completion_visible_roadmap_emitted:
                yield _step(
                    state,
                    label="completion_visible_user_flow_diagram_emitted",
                    action="emit visible completion user flow diagram before deciding whether any high-value work remains",
                    completion_visible_roadmap_emitted=True,
                    active_node="final_feature_matrix_review",
                )
                return
            if not state.final_feature_matrix_review_done:
                yield _step(
                    state,
                    label="final_feature_matrix_reviewed",
                    action="review implemented feature matrix and mark thin areas before completion grill-me",
                    final_feature_matrix_review_done=True,
                    active_node="final_acceptance_matrix_review",
                )
                return
            if not state.final_acceptance_matrix_review_done:
                yield _step(
                    state,
                    label="final_acceptance_matrix_reviewed",
                    action="review acceptance matrix and identify missing verification evidence before completion grill-me",
                    final_acceptance_matrix_review_done=True,
                    active_node="final_standard_scenario_pack_replay",
                )
                return
            if not state.final_standard_scenario_pack_replayed:
                yield _step(
                    state,
                    label="final_standard_scenario_pack_replayed",
                    action="replay the standard scenario pack and node-risk scenarios against the final product before quality-candidate and completion closure",
                    final_standard_scenario_pack_replayed=True,
                    active_node="final_quality_candidate_review",
                )
                return
            if not state.final_quality_candidate_review_done:
                yield _step(
                    state,
                    label="final_quality_candidate_reviewed",
                    action="summarize quality candidates as done, deferred with reason, waived with reason, or must-supplement before completion grill-me",
                    final_quality_candidate_review_done=True,
                    active_node="final_product_function_replay",
                )
                return
            if not state.final_product_model_officer_adversarial_probe_done:
                yield _step(
                    state,
                    label="final_product_model_officer_adversarial_probe_done",
                    action="product FlowGuard officer adversarially rechecks the final product model boundary, state fields, counterexamples, counts, and blindspots before approving final replay",
                    final_product_model_officer_adversarial_probe_done=True,
                    active_node="final_product_function_replay",
                )
                return
            if not state.final_product_function_model_replayed:
                yield _step(
                    state,
                    label="final_product_function_model_replayed",
                    action="product FlowGuard officer replays and approves final product behavior against the root product-function model before completion grill-me",
                    final_product_function_model_replayed=True,
                    final_product_function_model_product_officer_approved=True,
                    active_node="final_human_inspection_context",
                )
                return
            if not state.final_human_review_context_loaded:
                yield _step(
                    state,
                    label="final_human_review_context_loaded",
                    action="load final output, route evidence, product model, concept or acceptance evidence, and known repairs for final human-like review",
                    final_human_review_context_loaded=True,
                    active_node="final_human_neutral_observation",
                )
                return
            if not state.final_human_neutral_observation_written:
                yield _step(
                    state,
                    label="final_human_neutral_observation_written",
                    action="write a neutral observation of the final product artifacts before final pass/fail judgement",
                    final_human_neutral_observation_written=True,
                    active_node="final_human_manual_experiments",
                )
                return
            if not state.final_human_manual_experiments_run:
                yield _step(
                    state,
                    label="final_human_manual_experiments_run",
                    action="operate or inspect the final product as a human reviewer before completion grill-me",
                    final_human_manual_experiments_run=True,
                    active_node="final_human_inspection_decision",
                )
                return
            if not state.final_human_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="final_human_reviewer_independent_probe_done",
                    action="final human-like reviewer independently attacks the completed product with direct operation or inspection, concrete artifact references, missing-gate hypotheses, and report-only failure checks before approval",
                    final_human_reviewer_independent_probe_done=True,
                    active_node="final_human_inspection_decision",
                )
                return
            if not state.final_human_inspection_passed:
                yield _step(
                    state,
                    label="final_human_inspection_passed",
                    action="final human-like reviewer accepts the product as a complete showcase candidate",
                    final_human_inspection_passed=True,
                    final_human_review_reviewer_approved=True,
                    active_node="completion_self_interrogation",
                )
                return
            if not state.completion_self_interrogation_done:
                yield _step(
                    state,
                    label="completion_self_interrogation_completed",
                    action="derive completion layers and run at least 100 grill-me questions per active layer to find remaining high-value work",
                    completion_self_interrogation_done=True,
                    completion_self_interrogation_questions=(
                        MODEL_DYNAMIC_LAYER_COUNT
                        * MIN_FULL_GRILLME_QUESTIONS_PER_LAYER
                    ),
                    completion_self_interrogation_layer_count=MODEL_DYNAMIC_LAYER_COUNT,
                    completion_self_interrogation_questions_per_layer=MIN_FULL_GRILLME_QUESTIONS_PER_LAYER,
                    completion_self_interrogation_layers=REQUIRED_RISK_FAMILY_MASK,
                    active_node="review_high_value_work",
                )
                return
            if not state.completion_self_interrogation_record_written:
                yield _step(
                    state,
                    label="completion_self_interrogation_record_written",
                    action="write a durable completion self-interrogation record so final high-value-work decisions are traceable into the final ledger",
                    completion_self_interrogation_record_written=True,
                    active_node="review_high_value_work",
                )
                return
            if not state.completion_self_interrogation_findings_dispositioned:
                yield _step(
                    state,
                    label="completion_self_interrogation_findings_dispositioned",
                    action="PM dispositions completion self-interrogation findings as exhausted, routed to repair, entered into the suggestion ledger, rejected, or explicitly waived before final ledger work",
                    completion_self_interrogation_findings_dispositioned=True,
                    active_node="review_high_value_work",
                )
                return
            if state.high_value_work_review == "unknown":
                if state.standard_expansions < MAX_STANDARD_EXPANSIONS:
                    yield _step(
                        state,
                        label="high_value_work_found_and_route_expanded",
                        action="raise the standard and route another verified chunk",
                        route_version=state.route_version + 1,
                        route_checked=False,
                        markdown_synced=False,
                        execution_frontier_written=False,
                        codex_plan_synced=False,
                        frontier_version=0,
                        plan_version=0,
                        visible_user_flow_diagram_emitted=False,
                        user_flow_diagram_refreshed=False,
                        user_flow_diagram_reviewer_display_checked=False,
                        user_flow_diagram_reviewer_route_match_checked=False,
                        flowguard_process_design_done=False,
                        flowguard_officer_model_adversarial_probe_done=False,
                        flowguard_model_report_risk_tiers_done=False,
                        flowguard_model_report_pm_review_agenda_done=False,
                        flowguard_model_report_toolchain_recommendations_done=False,
                        flowguard_model_report_confidence_boundary_done=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
                        child_skill_manifest_independent_validation_done=False,
                        child_skill_manifest_reviewer_reviewed=False,
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        candidate_route_tree_generated=False,
                        root_route_model_checked=False,
                        root_route_model_process_officer_approved=False,
                        root_product_function_model_checked=False,
                        root_product_function_model_product_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        parent_backward_review_targets_enumerated=False,
                        parent_subtree_review_checked=False,
                        parent_focused_interrogation_done=False,
                        parent_focused_interrogation_questions=0,
                        parent_focused_interrogation_scope_id="",
                        unfinished_current_node_recovery_checked=False,
                        required_chunks=TARGET_CHUNKS,
                        completed_chunks=TARGET_CHUNKS - 1,
                        node_human_inspections_passed=TARGET_CHUNKS - 1,
                        composite_backward_reviews_passed=TARGET_CHUNKS - 1,
                        composite_backward_pm_segment_decisions_recorded=TARGET_PARENT_NODES
                        - 1,
                        checkpoint_written=False,
                        completion_self_interrogation_done=False,
                        completion_self_interrogation_questions=0,
                        completion_self_interrogation_layer_count=0,
                        completion_self_interrogation_questions_per_layer=0,
                        completion_self_interrogation_layers=0,
                        completion_self_interrogation_record_written=False,
                        completion_self_interrogation_findings_dispositioned=False,
                        completion_visible_roadmap_emitted=False,
                        high_value_work_review="unknown",
                        standard_expansions=state.standard_expansions + 1,
                        heartbeat_health_checked=False,
                        lifecycle_reconciliation_done=False,
                        terminal_lifecycle_frontier_written=False,
                        node_focused_interrogation_done=False,
                        node_focused_interrogation_questions=0,
                        node_focused_interrogation_scope_id="",
                        lightweight_self_check_done=False,
                        lightweight_self_check_questions=0,
                        lightweight_self_check_scope_id="",
                        node_visible_roadmap_emitted=False,
                        final_feature_matrix_review_done=False,
                        final_acceptance_matrix_review_done=False,
                        final_standard_scenario_pack_replayed=False,
                        final_quality_candidate_review_done=False,
                        final_product_function_model_replayed=False,
                        final_product_model_officer_adversarial_probe_done=False,
                        final_product_function_model_product_officer_approved=False,
                        final_human_review_context_loaded=False,
                        final_human_neutral_observation_written=False,
                        final_human_manual_experiments_run=False,
                        final_human_reviewer_independent_probe_done=False,
                        final_human_inspection_passed=False,
                        final_human_review_reviewer_approved=False,
                        pm_completion_decision_recorded=False,
                        active_node="run_expanded_route_checks",
                        **_reset_execution_scope_gates(),
                    )
                yield _step(
                    state,
                    label="no_obvious_high_value_work_remaining",
                    action="record that completion grill-me found no obvious high-value work",
                    high_value_work_review="exhausted",
                    active_node="ready_to_complete",
                )
                return
            if state.high_value_work_review != "exhausted":
                return
            if not state.final_route_wide_gate_ledger_current_route_scanned:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_current_route_scanned",
                    action="PM starts final route-wide gate ledger by scanning the current active route, execution frontier, and route mutation history",
                    final_route_wide_gate_ledger_current_route_scanned=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_effective_nodes_resolved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_effective_nodes_resolved",
                    action="PM resolves active, repaired, inserted, waived, and superseded nodes from the current route before completion approval",
                    final_route_wide_gate_ledger_effective_nodes_resolved=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_child_skill_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_child_skill_gates_collected",
                    action="PM collects every current child-skill gate, completion standard, evidence path, waiver, blocker, and role approval into the final ledger",
                    final_route_wide_gate_ledger_child_skill_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_human_review_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_human_review_gates_collected",
                    action="PM collects node, parent, final, strict-obligation, and same-inspector review gates into the final ledger",
                    final_route_wide_gate_ledger_human_review_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_parent_backward_replays_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_parent_backward_replays_collected",
                    action="PM collects every structurally required local parent backward replay and its PM segment decision into the final ledger",
                    final_route_wide_gate_ledger_parent_backward_replays_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_deep_leaf_coverage_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_deep_leaf_coverage_collected",
                    action="PM collects every effective deep leaf node, its acceptance plan, review evidence, and parent/module segment mapping into the final ledger",
                    final_route_wide_gate_ledger_deep_leaf_coverage_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_product_process_gates_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_product_process_gates_collected",
                    action="PM collects product-function and development-process model gates into the final ledger",
                    final_route_wide_gate_ledger_product_process_gates_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_resource_lineage_resolved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_resource_lineage_resolved",
                    action=(
                        "PM resolves generated-resource lineage into terminal dispositions: "
                        "consumed_by_implementation, included_in_final_output, "
                        "qa_evidence, flowguard_evidence, user_flow_diagram, "
                        "superseded, quarantined, or discarded_with_reason"
                    ),
                    final_route_wide_gate_ledger_resource_lineage_resolved=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.evidence_credibility_triage_done:
                yield _step(
                    state,
                    label="evidence_credibility_triage_done",
                    action="PM reconciles the evidence ledger, separating valid live-project evidence from invalid, stale, superseded, fixture-only, synthetic, historical, and generated-concept evidence before final ledger closure",
                    evidence_credibility_triage_done=True,
                    invalid_evidence_recorded=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_stale_evidence_checked:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_stale_evidence_checked",
                    action="PM checks that no stale or invalidated evidence is still closing a current route obligation",
                    final_route_wide_gate_ledger_stale_evidence_checked=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_superseded_nodes_explained:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_superseded_nodes_explained",
                    action="PM records replacement, waiver, or no-longer-effective explanations for every superseded node and gate",
                    final_route_wide_gate_ledger_superseded_nodes_explained=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_unresolved_count_zero:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_unresolved_count_zero",
                    action="PM records zero unresolved current-route obligations before final reviewer replay",
                    final_route_wide_gate_ledger_unresolved_count_zero=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_self_interrogation_collected:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_self_interrogation_collected",
                    action="PM cites the route self-interrogation index and collects startup, product-architecture, node, repair, role-result, and completion self-interrogation dispositions into the final ledger",
                    final_route_wide_gate_ledger_self_interrogation_collected=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.self_interrogation_index_clean:
                yield _step(
                    state,
                    label="self_interrogation_index_clean",
                    action="PM proves the self-interrogation index has no unresolved hard or current findings before final ledger build and terminal closure",
                    self_interrogation_index_clean=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_residual_risk_triage_done:
                yield _step(
                    state,
                    label="final_residual_risk_triage_done",
                    action="PM triages every remaining risk or blindspot as fixed, routed to repair, current-gate blocker, terminal replay scenario, non-risk note, or explicit exception",
                    final_residual_risk_triage_done=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_residual_risk_unresolved_count_zero:
                yield _step(
                    state,
                    label="final_residual_risk_unresolved_count_zero",
                    action="PM records zero unresolved residual risks before final ledger can be built",
                    final_residual_risk_unresolved_count_zero=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.defect_ledger_zero_blocking:
                yield _step(
                    state,
                    label="defect_ledger_zero_blocking",
                    action="PM checks the defect ledger and records zero open blocker defects and zero fixed-pending-recheck defects before final ledger can be built",
                    defect_ledger_zero_blocking=True,
                    active_node="final_route_wide_gate_ledger",
                )
                return
            if not state.final_route_wide_gate_ledger_pm_built:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_pm_built",
                    action="PM writes the final route-wide gate ledger from current route state and evidence, not from the startup checklist",
                    final_route_wide_gate_ledger_pm_built=True,
                    active_node="terminal_human_backward_review_map",
                )
                return
            if not state.terminal_human_backward_review_map_built:
                yield _step(
                    state,
                    label="terminal_human_backward_review_map_built",
                    action="PM converts the clean final ledger into an ordered human backward replay map from delivered product to root, parent, and leaf node obligations",
                    terminal_human_backward_review_map_built=True,
                    active_node="terminal_human_backward_replay",
                )
                return
            if not state.terminal_human_backward_replay_started_from_delivered_product:
                yield _step(
                    state,
                    label="terminal_human_backward_replay_started_from_delivered_product",
                    action="human-like reviewer starts terminal replay from the delivered product itself, not from ledger entries or worker reports",
                    terminal_human_backward_replay_started_from_delivered_product=True,
                    active_node="terminal_human_backward_root_review",
                )
                return
            if not state.terminal_human_backward_root_acceptance_reviewed:
                yield _step(
                    state,
                    label="terminal_human_backward_root_acceptance_reviewed",
                    action="human-like reviewer manually checks the final product against root acceptance and baseline functional obligations before drilling into nodes",
                    terminal_human_backward_root_acceptance_reviewed=True,
                    active_node="terminal_human_backward_parent_reviews",
                )
                return
            if not state.terminal_human_backward_parent_nodes_reviewed:
                yield _step(
                    state,
                    label="terminal_human_backward_parent_nodes_reviewed",
                    action="human-like reviewer walks backward through each effective parent or module node and checks whether child outcomes compose into the parent goal",
                    terminal_human_backward_parent_nodes_reviewed=True,
                    active_node="terminal_human_backward_leaf_reviews",
                )
                return
            if not state.terminal_human_backward_leaf_nodes_reviewed:
                yield _step(
                    state,
                    label="terminal_human_backward_leaf_nodes_reviewed",
                    action="human-like reviewer manually checks every effective leaf node against its node acceptance plan, experiments, and current product behavior",
                    terminal_human_backward_leaf_nodes_reviewed=True,
                    active_node="terminal_human_backward_pm_segment_decisions",
                )
                return
            if (
                state.terminal_human_backward_replay_repairs
                < MAX_TERMINAL_BACKWARD_REPLAY_REPAIRS
            ):
                yield _step(
                    state,
                    label="terminal_human_backward_replay_found_repair_issue",
                    action="terminal human backward replay finds a current product or node-detail issue that must return to PM repair routing instead of being parked in the report",
                    issue="terminal_backward_review_failure",
                    active_node="terminal_human_backward_replay_repair",
                )
                return
            if not state.terminal_human_backward_pm_segment_decisions_recorded:
                yield _step(
                    state,
                    label="terminal_human_backward_pm_segment_decisions_recorded",
                    action="PM reviews each reviewer segment result, records continue or repair decisions, and confirms no segment was accepted from report-only evidence",
                    terminal_human_backward_pm_segment_decisions_recorded=True,
                    active_node="terminal_human_backward_restart_policy",
                )
                return
            if not state.terminal_human_backward_repair_restart_policy_recorded:
                yield _step(
                    state,
                    label="terminal_human_backward_repair_restart_policy_recorded",
                    action="PM records that any terminal replay repair invalidates affected evidence and restarts final review from the delivered product unless a narrower impacted-ancestor restart is justified",
                    terminal_human_backward_repair_restart_policy_recorded=True,
                    active_node="final_route_wide_gate_ledger_reviewer_replay",
                )
                return
            if not state.final_route_wide_gate_ledger_reviewer_backward_checked:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_reviewer_backward_checked",
                    action="human-like reviewer completes the terminal human backward replay through every effective root, parent, and leaf-node obligation in the PM-built map",
                    final_route_wide_gate_ledger_reviewer_backward_checked=True,
                    active_node="final_route_wide_gate_ledger_pm_approval",
                )
                return
            if not state.final_ledger_pm_independent_audit_done:
                yield _step(
                    state,
                    label="final_ledger_pm_independent_audit_done",
                    action="PM independently audits route/frontier/ledger entries, stale evidence, waiver authority, unresolved counts, reviewer replay, and blindspots before completion approval",
                    final_ledger_pm_independent_audit_done=True,
                    active_node="final_route_wide_gate_ledger_pm_approval",
                )
                return
            if not state.final_route_wide_gate_ledger_pm_completion_approved:
                yield _step(
                    state,
                    label="final_route_wide_gate_ledger_pm_completion_approved",
                    action="project manager approves the clean route-wide gate ledger before lifecycle closure and final completion decision",
                    final_route_wide_gate_ledger_pm_completion_approved=True,
                    active_node="terminal_closure_suite",
                )
                return
            if not state.terminal_closure_suite_run:
                yield _step(
                    state,
                    label="terminal_closure_suite_run",
                    action="run terminal closure suite after final ledger approval to check final state, frontier, ledger, checkpoints, lifecycle evidence, role memory, and final report readiness",
                    terminal_closure_suite_run=True,
                    active_node="terminal_state_evidence_refresh",
                )
                return
            if not state.terminal_state_and_evidence_refreshed:
                yield _step(
                    state,
                    label="terminal_state_and_evidence_refreshed",
                    action="refresh terminal state, execution frontier, ledger pointers, role memory, lifecycle evidence, and completion notice readiness before route shutdown",
                    terminal_state_and_evidence_refreshed=True,
                    active_node="ready_to_complete",
                )
                return
            if not state.lifecycle_reconciliation_done:
                yield _step(
                    state,
                    label="lifecycle_reconciliation_completed",
                    action="scan Codex heartbeat automations, local state, and execution frontier before route shutdown",
                    lifecycle_reconciliation_done=True,
                    active_node="reconcile_lifecycle",
                )
                return
            if not state.terminal_lifecycle_frontier_written:
                yield _step(
                    state,
                    label="terminal_lifecycle_frontier_written",
                    action="write terminal heartbeat lifecycle back to execution frontier before stopping heartbeat",
                    terminal_lifecycle_frontier_written=True,
                    active_node="terminal_lifecycle_frontier_synced",
                )
                return
            if not state.crew_memory_archived:
                yield _step(
                    state,
                    label="crew_memory_archived_at_terminal",
                    action="archive final role memory packet statuses after lifecycle reconciliation and before crew ledger archive",
                    crew_memory_archived=True,
                    active_node="ready_to_archive_crew",
                )
                return
            if not state.crew_archived:
                yield _step(
                    state,
                    label="crew_archived_at_terminal",
                    action="archive persistent crew ledger and final role statuses after role memory archive and before final report",
                    crew_archived=True,
                    active_node="ready_to_emit_final_report",
                )
                return
            if not state.flowpilot_skill_improvement_report_written:
                yield _step(
                    state,
                    label="flowpilot_skill_improvement_report_written",
                    action="PM writes a nonblocking FlowPilot skill improvement report from node observations for later manual root-repo maintenance, without requiring those skill issues to be fixed before current project completion",
                    flowpilot_skill_improvement_report_written=True,
                    active_node="ready_to_emit_final_report",
                )
                return
            if not state.pm_completion_decision_recorded:
                yield _step(
                    state,
                    label="pm_completion_decision_recorded",
                    action="project manager approves completion after final product replay, final human review, high-value review, lifecycle cleanup, and crew archive",
                    pm_completion_decision_recorded=True,
                    active_node="ready_to_emit_final_report",
                )
                return
            yield _step(
                state,
                label="final_report_emitted",
                action="emit final report, emit terminal completion notice, and reconcile continuation lifecycle",
                status="complete",
                heartbeat_active=False,
                final_report_emitted=True,
                terminal_completion_notice_recorded=True,
                active_node="complete",
            )
            return

        if _route_ready(state) and state.completed_chunks < TARGET_CHUNKS:
            if not state.heartbeat_loaded_state:
                yield _step(
                    state,
                    label="heartbeat_loaded_state",
                    action="continuation turn loads local state, active route, latest heartbeat or manual-resume evidence, lifecycle evidence, and crew ledger",
                    heartbeat_loaded_state=True,
                    active_node="heartbeat_load_frontier",
                )
                return
            if not state.heartbeat_loaded_frontier:
                yield _step(
                    state,
                    label="heartbeat_loaded_execution_frontier",
                    action="continuation turn loads execution_frontier.json before selecting work",
                    heartbeat_loaded_frontier=True,
                    active_node="heartbeat_load_packet_ledger",
                )
                return
            if not state.heartbeat_loaded_packet_ledger:
                yield _step(
                    state,
                    label="heartbeat_loaded_packet_ledger",
                    action="continuation turn loads packet_ledger.json before asking PM or dispatching worker work",
                    heartbeat_loaded_packet_ledger=True,
                    active_node="heartbeat_load_crew_memory",
                )
                return
            if not state.heartbeat_loaded_crew_memory:
                yield _step(
                    state,
                    label="heartbeat_loaded_crew_memory",
                    action="continuation turn loads structured role memory packets before restoring or replacing roles",
                    heartbeat_loaded_crew_memory=True,
                    active_node="heartbeat_rehydrate_crew",
                )
                return
            if not state.heartbeat_host_rehydrate_requested:
                yield _step(
                    state,
                    label="heartbeat_host_spawn_or_rehydrate_six_roles",
                    action="router asks the host to restore or spawn all six live roles before PM resume",
                    heartbeat_host_rehydrate_requested=True,
                    active_node="heartbeat_rehydrate_crew",
                )
                return
            if not state.heartbeat_restored_crew:
                yield _step(
                    state,
                    label="heartbeat_restored_six_agent_crew",
                    action="continuation turn resumes available role agents or prepares replacements from role memory",
                    heartbeat_restored_crew=True,
                    replacement_roles_seeded_from_memory=True,
                    active_node="heartbeat_rehydrate_crew",
                )
                return
            if not state.heartbeat_rehydrated_crew:
                yield _step(
                    state,
                    label="heartbeat_rehydrated_six_agent_crew",
                    action="continuation turn records full six-role rehydration status before asking the PM",
                    heartbeat_rehydrated_crew=True,
                    active_node="write_crew_rehydration_report",
                )
                return
            if not state.heartbeat_injected_current_run_memory_into_roles:
                yield _step(
                    state,
                    label="heartbeat_injected_current_run_memory_into_roles",
                    action="host injects each role's current-run memory and PM resume context before PM runway",
                    heartbeat_injected_current_run_memory_into_roles=True,
                    active_node="write_crew_rehydration_report",
                )
                return
            if not state.crew_rehydration_report_written:
                yield _step(
                    state,
                    label="crew_rehydration_report_written",
                    action="write the six-role rehydration report with restored, replaced, blocked, and memory-seeded role status before any PM resume decision",
                    crew_rehydration_report_written=True,
                    active_node="heartbeat_ask_project_manager",
                )
                return
            if not state.heartbeat_pm_decision_requested:
                yield _step(
                    state,
                    label="heartbeat_asked_project_manager",
                    action="continuation turn asks the project manager for PM_DECISION from the current frontier and packet ledger",
                    heartbeat_pm_decision_requested=True,
                    active_node="check_pm_controller_reminder",
                )
                return
            if not state.heartbeat_pm_controller_reminder_checked:
                yield _step(
                    state,
                    label="heartbeat_pm_controller_reminder_checked",
                    action="controller requires PM_DECISION to include controller_reminder before dispatching any packet",
                    heartbeat_pm_controller_reminder_checked=True,
                    active_node="check_router_direct_dispatch_policy",
                )
                return
            if not state.heartbeat_reviewer_dispatch_policy_checked:
                yield _step(
                    state,
                    label="heartbeat_reviewer_dispatch_policy_checked",
                    action="controller confirms NODE_PACKET dispatch requires router direct-dispatch preflight and ambiguous worker state blocks controller execution",
                    heartbeat_reviewer_dispatch_policy_checked=True,
                    active_node="await_pm_resume_decision",
                )
                return
            if not state.pm_resume_decision_recorded:
                yield _step(
                    state,
                    label="pm_resume_completion_runway_recorded",
                    action="project manager records a completion-oriented runway from the current gate toward project completion, including hard stops and checkpoint cadence",
                    pm_resume_decision_recorded=True,
                    pm_completion_runway_recorded=True,
                    pm_runway_hard_stops_recorded=True,
                    pm_runway_checkpoint_cadence_recorded=True,
                    active_node="sync_pm_runway_to_plan",
                )
                return
            if not state.pm_runway_synced_to_plan:
                yield _step(
                    state,
                    label="pm_runway_synced_to_visible_plan",
                    action="controller calls the host native plan tool when available, or records the fallback method, and replaces the visible plan with a downstream PM runway projection",
                    pm_runway_synced_to_plan=True,
                    plan_sync_method_recorded=True,
                    visible_plan_has_runway_depth=True,
                    active_node="check_continuation_resume_ready",
                )
                return
            if not state.heartbeat_health_checked:
                yield _step(
                    state,
                    label="continuation_resume_ready_checked",
                    action="check automated heartbeat health when supported, or check manual-resume state/frontier/crew-memory readiness when no real wakeup exists",
                    heartbeat_health_checked=True,
                    active_node="check_unfinished_current_node",
                )
                return
            if not state.pm_node_decision_recorded:
                yield _step(
                    state,
                    label="pm_node_work_decision_recorded",
                    action="project manager assigns the current node work package before the controller dispatches authorized work",
                    pm_node_decision_recorded=True,
                    active_node="check_unfinished_current_node",
                )
                return
            if not state.unfinished_current_node_recovery_checked:
                yield _step(
                    state,
                    label="unfinished_current_node_recovery_checked",
                    action="confirm heartbeat should resume the current node or may advance",
                    unfinished_current_node_recovery_checked=True,
                    active_node="parent_focused_interrogation",
                )
                return
            if not state.parent_focused_interrogation_done:
                yield _step(
                    state,
                    label="parent_focused_interrogation_completed",
                    action="run 20-50 focused grill-me questions for the active parent scope before subtree FlowGuard review",
                    parent_focused_interrogation_done=True,
                    parent_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                    parent_focused_interrogation_scope_id="active-parent",
                    active_node="review_parent_subtree",
                )
                return
            if not state.parent_subtree_review_checked:
                yield _step(
                    state,
                    label="parent_subtree_review_checked",
                    action="rerun FlowGuard against the current parent child-subtree before child work",
                    parent_subtree_review_checked=True,
                    active_node="check_parent_product_function_model",
                )
                return
            if not state.parent_product_function_model_checked:
                yield _step(
                    state,
                    label="parent_product_function_model_checked",
                    action="product FlowGuard officer runs and approves the parent product-function model before entering the active child node",
                    parent_product_function_model_checked=True,
                    parent_product_function_model_product_officer_approved=True,
                    active_node="emit_node_visible_roadmap",
                )
                return
            if not state.node_visible_roadmap_emitted:
                yield _step(
                    state,
                    label="node_visible_roadmap_emitted",
                    action="emit visible node roadmap before defining implementation work",
                    node_visible_roadmap_emitted=True,
                    active_node="node_focused_interrogation",
                )
                return
            if not state.node_focused_interrogation_done:
                yield _step(
                    state,
                    label="node_focused_interrogation_completed",
                    action="run 20-50 focused grill-me questions for the active leaf node before defining implementation work",
                    node_focused_interrogation_done=True,
                    node_focused_interrogation_questions=DEFAULT_FOCUSED_GRILLME_QUESTIONS,
                    node_focused_interrogation_scope_id="active-leaf-node",
                    active_node="check_node_product_function_model",
                )
                return
            if not state.node_self_interrogation_record_written:
                yield _step(
                    state,
                    label="node_self_interrogation_record_written",
                    action="write a durable current-node self-interrogation record before node modeling, acceptance planning, or worker packet dispatch can rely on the grill-me result",
                    node_self_interrogation_record_written=True,
                    active_node="check_node_product_function_model",
                )
                return
            if not state.node_self_interrogation_findings_dispositioned:
                yield _step(
                    state,
                    label="node_self_interrogation_findings_dispositioned",
                    action="PM binds current-node self-interrogation findings into the node acceptance plan, a later gate, the suggestion ledger, a rejection, or an explicit waiver before packet dispatch",
                    node_self_interrogation_findings_dispositioned=True,
                    active_node="check_node_product_function_model",
                )
                return
            if not state.node_product_function_model_checked:
                yield _step(
                    state,
                    label="node_product_function_model_checked",
                    action="product FlowGuard officer runs and approves the active leaf's product-function model before defining implementation work",
                    node_product_function_model_checked=True,
                    node_product_function_model_product_officer_approved=True,
                    active_node="current_node_high_standard_recheck",
                )
                return
            if not state.current_node_high_standard_recheck_written:
                yield _step(
                    state,
                    label="current_node_high_standard_recheck_written",
                    action="project manager rechecks the current node against the highest achievable product target, unacceptable-result bar, semantic-fidelity policy, and likely local downgrade risks before writing node acceptance",
                    current_node_high_standard_recheck_written=True,
                    active_node="current_node_minimum_sufficient_complexity_review",
                )
                return
            if not state.current_node_minimum_sufficient_complexity_review_written:
                yield _step(
                    state,
                    label="current_node_minimum_sufficient_complexity_review_written",
                    action="project manager records why the current node packet, checks, handoffs, and evidence are the minimum sufficient structure for the node proof obligations",
                    current_node_minimum_sufficient_complexity_review_written=True,
                    active_node="write_node_acceptance_plan",
                )
                return
            if not state.node_acceptance_plan_written:
                yield _step(
                    state,
                    label="node_acceptance_plan_written",
                    action="project manager writes the current node acceptance plan with root mappings, local criteria, concrete experiments, evidence paths, and approver",
                    node_acceptance_plan_written=True,
                    current_node_skill_improvement_check_done=False,
                    checkpoint_written=False,
                    active_node="check_current_node_leaf_readiness",
                )
                return
            if not state.active_node_leaf_readiness_gate_passed:
                yield _step(
                    state,
                    label="active_node_leaf_readiness_gate_passed",
                    action="project manager and reviewer confirm a leaf/repair node has a passing readiness gate before worker dispatch",
                    active_node_leaf_readiness_gate_passed=True,
                    active_node="block_parent_node_direct_dispatch",
                )
                return
            if not state.active_node_parent_dispatch_blocked:
                yield _step(
                    state,
                    label="active_node_parent_dispatch_blocked",
                    action="Router/PM path confirms parent or module nodes cannot receive worker packets and must enter child subtree or parent backward replay",
                    active_node_parent_dispatch_blocked=True,
                    active_node="map_node_acceptance_risk_experiments",
                )
                return
            if not state.node_acceptance_risk_experiments_mapped:
                if not state.active_child_skill_bindings_written:
                    yield _step(
                        state,
                        label="active_child_skill_bindings_written",
                        action="project manager writes current-node active child-skill bindings with source skill paths, node-slice scope, selected standards, and stricter-than-PM precedence before worker dispatch",
                        active_child_skill_bindings_written=True,
                        active_child_skill_binding_scope_limited=True,
                        child_skill_stricter_standard_precedence_bound=True,
                        active_node="map_node_acceptance_risk_experiments",
                    )
                    return
                yield _step(
                    state,
                    label="node_acceptance_risk_experiments_mapped",
                    action="project manager maps current-node risk hypotheses to experiments and terminal replay scenarios before implementation starts",
                    node_acceptance_risk_experiments_mapped=True,
                    active_node="pm_review_hold_instruction",
                )
                return
            if not state.worker_packet_child_skill_use_instruction_written:
                yield _step(
                    state,
                    label="worker_packet_child_skill_binding_projected",
                    action="project active child-skill bindings into the current-node worker packet with direct use instructions and allowed source SKILL.md/reference paths",
                    worker_packet_child_skill_use_instruction_written=True,
                    active_child_skill_source_paths_allowed=True,
                    active_node="pm_review_hold_instruction",
                )
                return
            if not state.pm_review_hold_instruction_written:
                yield _step(
                    state,
                    label="pm_review_hold_instruction_written",
                    action="project manager tells the human-like reviewer to wait and not review current-node work until worker output and verification are ready for a PM release order",
                    pm_review_hold_instruction_written=True,
                    active_node="lightweight_self_check",
                )
                return
            if not state.lightweight_self_check_done:
                yield _step(
                    state,
                    label="lightweight_self_check_completed",
                    action="run 5-10 lightweight self-check questions for the current heartbeat micro-step",
                    lightweight_self_check_done=True,
                    lightweight_self_check_questions=DEFAULT_LIGHTWEIGHT_SELF_CHECK_QUESTIONS,
                    lightweight_self_check_scope_id="active-micro-step",
                    active_node="ready_for_chunk",
                )
                return
            if not state.quality_package_done:
                yield _step(
                    state,
                    label="quality_package_passed_no_raise",
                    action="run one quality package for feature thinness, worthwhile raises, child-skill visibility, validation strength, and rough-finish risk; record no scope raise",
                    quality_package_done=True,
                    quality_candidate_registry_checked=True,
                    quality_raise_decision_recorded=True,
                    validation_matrix_defined=True,
                    active_node="ready_for_chunk",
                )
                yield _step(
                    state,
                    label="quality_package_small_raise_in_current_node",
                    action="record a low-risk high-value improvement inside the current node without changing the route",
                    quality_package_done=True,
                    quality_candidate_registry_checked=True,
                    quality_raise_decision_recorded=True,
                    validation_matrix_defined=True,
                    active_node="ready_for_chunk",
                )
                if (
                    state.completed_chunks == 0
                    and state.quality_route_raises < MAX_QUALITY_ROUTE_RAISES
                ):
                    yield _step(
                        state,
                        label="quality_package_route_raise_needed",
                        action="classify a medium or large improvement as route mutation, not an unbounded immediate expansion",
                        route_version=state.route_version + 1,
                        route_checked=False,
                        markdown_synced=False,
                        execution_frontier_written=False,
                        codex_plan_synced=False,
                        frontier_version=0,
                        plan_version=0,
                        visible_user_flow_diagram_emitted=False,
                        user_flow_diagram_refreshed=False,
                        user_flow_diagram_reviewer_display_checked=False,
                        user_flow_diagram_reviewer_route_match_checked=False,
                        flowguard_process_design_done=False,
                        flowguard_officer_model_adversarial_probe_done=False,
                        flowguard_model_report_risk_tiers_done=False,
                        flowguard_model_report_pm_review_agenda_done=False,
                        flowguard_model_report_toolchain_recommendations_done=False,
                        flowguard_model_report_confidence_boundary_done=False,
                        child_skill_route_design_discovery_started=False,
                        child_skill_initial_gate_manifest_extracted=False,
                        child_skill_gate_approvers_assigned=False,
                        child_skill_manifest_independent_validation_done=False,
                        child_skill_manifest_reviewer_reviewed=False,
                        child_skill_manifest_process_officer_approved=False,
                        child_skill_manifest_product_officer_approved=False,
                        child_skill_manifest_pm_approved_for_route=False,
                        candidate_route_tree_generated=False,
                        root_route_model_checked=False,
                        root_route_model_process_officer_approved=False,
                        root_product_function_model_checked=False,
                        root_product_function_model_product_officer_approved=False,
                        strict_gate_obligation_review_model_checked=False,
                        parent_backward_review_targets_enumerated=False,
                        parent_subtree_review_checked=False,
                        parent_focused_interrogation_done=False,
                        parent_focused_interrogation_questions=0,
                        parent_focused_interrogation_scope_id="",
                        unfinished_current_node_recovery_checked=False,
                        node_focused_interrogation_done=False,
                        node_focused_interrogation_questions=0,
                        node_focused_interrogation_scope_id="",
                        lightweight_self_check_done=False,
                        lightweight_self_check_questions=0,
                        lightweight_self_check_scope_id="",
                        child_node_sidecar_scan_done=False,
                        sidecar_need="unknown",
                        subagent_scope_checked=False,
                        node_visible_roadmap_emitted=False,
                        quality_route_raises=state.quality_route_raises + 1,
                        active_node="run_quality_route_checks",
                        **_reset_execution_scope_gates(),
                    )
                return
            if state.high_risk_gate == "none":
                yield _step(
                    state,
                    label="high_risk_gate_requested",
                    action="pause for hard safety gate before risky operation",
                    high_risk_gate="pending",
                    active_node="await_high_risk_approval",
                )
            if not state.child_node_sidecar_scan_done:
                yield _step(
                    state,
                    label="child_node_sidecar_scan_no_need",
                    action="enter the current child node and find no useful bounded sidecar task",
                    child_node_sidecar_scan_done=True,
                    sidecar_need="none",
                    active_node="ready_for_chunk",
                )
                yield _step(
                    state,
                    label="child_node_sidecar_scan_need_found_no_pool",
                    action="enter the current child node and find a bounded sidecar task with no existing idle subagent",
                    child_node_sidecar_scan_done=True,
                    sidecar_need="needed",
                    subagent_pool_exists=False,
                    subagent_idle_available=False,
                    active_node="sidecar_scope_check",
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
                    active_node="sidecar_scope_check",
                )
                return
            if state.sidecar_need == "needed" and not state.subagent_scope_checked:
                yield _step(
                    state,
                    label="sidecar_scope_checked",
                    action="confirm the sidecar task is bounded, non-blocking, and cannot own the node, route, acceptance, or checkpoint",
                    subagent_scope_checked=True,
                    active_node="assign_sidecar",
                )
                return
            if (
                state.sidecar_need == "needed"
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
                        active_node="await_sidecar_report",
                    )
                else:
                    yield _step(
                        state,
                        label="subagent_spawned_on_demand",
                        action="spawn a subagent only after the current child node has a bounded sidecar task and no suitable idle subagent exists",
                        subagent_pool_exists=True,
                        subagent_status="pending",
                        active_node="await_sidecar_report",
                    )
                return
            if state.subagent_status == "pending":
                yield _step(
                    state,
                    label="sidecar_report_returned",
                    action="sidecar subagent returns findings, evidence, changed paths if any, risks, and suggestions",
                    subagent_status="returned",
                    active_node="merge_sidecar_report",
                )
                return
            if state.subagent_status == "returned":
                yield _step(
                    state,
                    label="authorized_integration_review_packet_completed",
                    action="authorized integration/review packet verifies the sidecar report while PM keeps node ownership",
                    sidecar_need="none",
                    subagent_status="idle",
                    subagent_idle_available=True,
                    active_node="ready_for_chunk",
                )
                return
            yield _step(
                state,
                label="chunk_verification_defined",
                action="define chunk-level verification before execution",
                chunk_state="ready",
                verification_defined=True,
                checkpoint_written=False,
                active_node="execute_chunk",
            )
            return

        if state.chunk_state == "ready" and state.verification_defined:
            yield _step(
                state,
                label="chunk_executed",
                action="execute bounded chunk",
                chunk_state="executed",
                role_memory_refreshed_after_work=False,
                active_node="verify_chunk",
            )
            return

        if state.chunk_state == "executed":
            if not state.worker_child_skill_use_evidence_returned:
                yield _step(
                    state,
                    label="worker_child_skill_use_evidence_returned",
                    action="worker returns Child Skill Use Evidence proving the bound child skill source was opened, applied to the current node slice, and any stricter child-skill standard was followed or explicitly waived",
                    worker_child_skill_use_evidence_returned=True,
                    active_node="verify_chunk",
                )
                return
            yield _step(
                state,
                label="chunk_verification_passed",
                action="real verification passes for chunk before anti-rough-finish review",
                chunk_state="verified",
                verification_defined=False,
                active_node="anti_rough_finish_review",
            )
            yield _step(
                state,
                label="verification_found_model_gap",
                action="real verification exposes model gap",
                issue="model_gap",
                chunk_state="none",
                verification_defined=False,
                checkpoint_written=False,
                active_node="update_model",
            )
            yield _step(
                state,
                label="verification_found_impl_failure",
                action="real verification exposes implementation failure",
                issue="impl_failure",
                chunk_state="none",
                verification_defined=False,
                checkpoint_written=False,
                active_node="recover_implementation",
            )
            return

        if state.chunk_state == "verified":
            if not state.anti_rough_finish_done:
                yield _step(
                    state,
                    label="anti_rough_finish_passed",
                    action="review the verified chunk for thin functionality, missing states, weak evidence, and rushed closure before human-like inspection",
                    anti_rough_finish_done=True,
                    active_node="mark_worker_output_ready_for_pm_review_release",
                )
                if (
                    state.completed_chunks == 0
                    and state.quality_reworks < MAX_QUALITY_REWORKS
                ):
                    yield _step(
                        state,
                        label="anti_rough_finish_found_rework",
                        action="record bounded rework because the verified chunk is still too thin or weakly evidenced",
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        heartbeat_health_checked=False,
                        parent_focused_interrogation_done=False,
                        parent_focused_interrogation_questions=0,
                        parent_focused_interrogation_scope_id="",
                        parent_subtree_review_checked=False,
                        unfinished_current_node_recovery_checked=False,
                        node_focused_interrogation_done=False,
                        node_focused_interrogation_questions=0,
                        node_focused_interrogation_scope_id="",
                        lightweight_self_check_done=False,
                        lightweight_self_check_questions=0,
                        lightweight_self_check_scope_id="",
                        node_visible_roadmap_emitted=False,
                        quality_reworks=state.quality_reworks + 1,
                        active_node="quality_rework",
                        **_reset_execution_scope_gates(),
                    )
                return
            if not state.worker_output_ready_for_review:
                yield _step(
                    state,
                    label="worker_output_ready_for_review",
                    action="record that current-node worker output, verification evidence, and anti-rough-finish result are ready for PM review-release decision",
                    worker_output_ready_for_review=True,
                    active_node="pm_review_release_order",
                )
                return
            if not state.pm_review_release_order_written:
                yield _step(
                    state,
                    label="pm_review_release_order_written",
                    action="project manager writes the review release order naming the gate, evidence paths, reviewer scope, and what the reviewer must inspect",
                    pm_review_release_order_written=True,
                    active_node="pm_release_reviewer_for_current_gate",
                )
                return
            if not state.pm_released_reviewer_for_current_gate:
                yield _step(
                    state,
                    label="pm_released_reviewer_for_current_gate",
                    action="project manager explicitly releases the reviewer to start current-gate review after worker output is ready",
                    pm_released_reviewer_for_current_gate=True,
                    active_node="review_packet_role_origin",
                )
                return
            if not state.packet_runtime_physical_files_written:
                yield _step(
                    state,
                    label="packet_runtime_physical_isolation_verified",
                    action="packet runtime writes physical packet/result envelope-body files and verifies controller context excludes body content before reviewer audit",
                    packet_runtime_physical_files_written=True,
                    controller_context_body_exclusion_verified=True,
                    active_node="review_packet_role_origin",
                )
                return
            if not state.packet_mail_chain_audit_done:
                yield _step(
                    state,
                    label="controller_mail_relay_chain_audit_done",
                    action="human-like reviewer verifies every packet/result envelope has controller relay signatures, recipients opened bodies only after relay checks, private role-to-role mail is absent, and unopened or contaminated mail is routed to PM for restart, repair node, or sender reissue",
                    controller_relay_signature_audit_done=True,
                    recipient_pre_open_relay_check_done=True,
                    packet_mail_chain_audit_done=True,
                    unopened_mail_pm_recovery_policy_recorded=True,
                    active_node="review_packet_role_origin",
                )
                return
            if not state.packet_envelope_body_audit_done:
                yield _step(
                    state,
                    label="packet_envelope_body_audit_done",
                    action="human-like reviewer checks packet envelope to_role, packet body hash, result envelope completed_by_role and completed_by_agent_id, result body hash, controller body-access boundary, and no wrong-role relabel before content review",
                    packet_envelope_body_audit_done=True,
                    packet_envelope_to_role_checked=True,
                    packet_body_hash_verified=True,
                    result_envelope_checked=True,
                    result_body_hash_verified=True,
                    completed_agent_id_role_verified=True,
                    controller_body_boundary_verified=True,
                    wrong_role_relabel_forbidden_verified=True,
                    active_node="review_packet_role_origin",
                )
                return
            if not state.packet_role_origin_audit_done:
                yield _step(
                    state,
                    label="packet_role_origin_audit_done",
                    action="human-like reviewer verifies every packet's PM author, router direct-dispatch evidence, assigned worker, and actual result author after envelope/body integrity passes",
                    packet_role_origin_audit_done=True,
                    packet_result_author_verified=True,
                    packet_result_author_matches_assignment=True,
                    active_node="load_human_inspection_context",
                )
                return
            if not state.blocker_repair_policy_snapshot_written:
                yield _step(
                    state,
                    label="blocker_repair_policy_snapshot_written",
                    action="write the run-visible blocker repair policy table before any router control blocker is materialized",
                    blocker_repair_policy_snapshot_written=True,
                    active_node="exercise_control_blocker_policy",
                )
                return
            if not state.router_hard_rejection_seen:
                yield _step(
                    state,
                    label="control_blocker_policy_row_attached",
                    action="router materializes a mechanical control blocker with policy row, first handler, retry budget, and return policy metadata",
                    router_hard_rejection_seen=True,
                    control_blocker_artifact_written=True,
                    blocker_policy_row_attached=True,
                    control_blocker_handling_lane="control_plane_reissue",
                    control_blocker_first_handler="responsible_role",
                    control_blocker_direct_retry_budget=2,
                    control_blocker_direct_retry_attempts=0,
                    active_node="deliver_control_blocker_first_handler",
                )
                return
            if (
                state.control_blocker_handling_lane == "control_plane_reissue"
                and not state.control_blocker_delivered_to_responsible_role
            ):
                yield _step(
                    state,
                    label="control_blocker_first_handler_delivered",
                    action="controller delivers the first mechanical blocker to the responsible role without opening sealed bodies or making a PM decision",
                    control_blocker_delivered_to_responsible_role=True,
                    active_node="retry_control_plane_reissue",
                )
                return
            if (
                state.control_blocker_delivered_to_responsible_role
                and not state.control_blocker_retry_budget_exhausted
            ):
                yield _step(
                    state,
                    label="control_blocker_retry_budget_escalated_to_pm",
                    action="after two failed direct reissue attempts, router escalates the same blocker family to PM instead of looping the responsible role",
                    control_blocker_handling_lane="pm_repair_decision_required",
                    control_blocker_direct_retry_attempts=2,
                    control_blocker_retry_budget_exhausted=True,
                    control_blocker_escalated_to_pm=True,
                    control_blocker_delivered_to_pm=True,
                    active_node="pm_control_blocker_recovery_decision",
                )
                return
            if state.control_blocker_escalated_to_pm and not state.pm_blocker_recovery_option_recorded:
                yield _step(
                    state,
                    label="pm_blocker_recovery_option_recorded",
                    action="PM chooses a policy-listed recovery option instead of silently passing the blocked gate",
                    pm_blocker_recovery_option_recorded=True,
                    pm_blocker_hard_stop_checked=True,
                    pm_blocker_silent_pass_forbidden=True,
                    active_node="pm_control_blocker_return_gate",
                )
                return
            if state.pm_blocker_recovery_option_recorded and not state.pm_blocker_return_gate_recorded:
                yield _step(
                    state,
                    label="pm_blocker_return_gate_recorded",
                    action="PM names the gate or terminal stop that follows the blocker recovery decision",
                    pm_blocker_return_gate_recorded=True,
                    active_node="load_human_inspection_context",
                )
                return
            if not state.reviewer_child_skill_use_evidence_checked:
                yield _step(
                    state,
                    label="reviewer_child_skill_use_evidence_checked",
                    action="human-like reviewer checks Child Skill Use Evidence, source-skill opening, current-node slice fit, and stricter child-skill standard precedence before content inspection",
                    reviewer_child_skill_use_evidence_checked=True,
                    active_node="load_human_inspection_context",
                )
                return
            if not state.node_human_review_context_loaded:
                yield _step(
                    state,
                    label="node_human_inspection_context_loaded",
                    action="load requirement, product model, evidence, screenshots or logs, and parent contract for human-like node inspection",
                    node_human_review_context_loaded=True,
                    active_node="write_node_human_neutral_observation",
                )
                return
            if not state.node_human_neutral_observation_written:
                yield _step(
                    state,
                    label="node_human_neutral_observation_written",
                    action="write a neutral observation of what the node artifact, output, or UI screenshot actually appears to be",
                    node_human_neutral_observation_written=True,
                    active_node="run_human_inspection_experiments",
                )
                return
            if not state.node_human_manual_experiments_run:
                yield _step(
                    state,
                    label="node_human_manual_experiments_run",
                    action="operate or inspect the product like a human reviewer before accepting node evidence",
                    node_human_manual_experiments_run=True,
                    active_node="human_inspection_decision",
                )
                return
            if not state.node_reviewer_independent_probe_done:
                yield _step(
                    state,
                    label="node_reviewer_independent_probe_done",
                    action="human-like reviewer independently attacks node evidence with direct probes, concrete artifact or state references, missing-path hypotheses, and report-only failure checks before approval",
                    node_reviewer_independent_probe_done=True,
                    active_node="human_inspection_decision",
                )
                return
            if not state.node_human_inspection_passed:
                if (
                    state.completed_chunks == 0
                    and state.human_inspection_repairs < 1
                ):
                    yield _step(
                        state,
                        label="human_inspection_found_blocking_issue",
                        action="human-like reviewer rejects the node evidence, writes a blocking defect event, and requires a route-mutating repair",
                        issue="inspection_failure",
                        defect_event_logged_for_blocker=True,
                        blocking_defect_open=True,
                        pm_defect_triage_done=False,
                        blocking_defect_fixed_pending_recheck=False,
                        defect_same_class_recheck_done=False,
                        defect_ledger_zero_blocking=False,
                        chunk_state="none",
                        verification_defined=False,
                        checkpoint_written=False,
                        active_node="grill_human_inspection_issue",
                    )
                    return
                yield _step(
                    state,
                    label="node_human_inspection_passed",
                    action="human-like reviewer accepts the repaired node evidence and product behavior, closing any fixed-pending same-class blocker",
                    node_human_inspection_passed=True,
                    node_human_review_reviewer_approved=True,
                    blocking_defect_fixed_pending_recheck=False,
                    defect_same_class_recheck_done=(
                        state.blocking_defect_fixed_pending_recheck
                        or state.defect_same_class_recheck_done
                    ),
                    defect_ledger_zero_blocking=True,
                    active_node="write_checkpoint",
                )
                return
            if not state.current_node_skill_improvement_check_done:
                yield _step(
                    state,
                    label="skill_improvement_observation_check_no_issue",
                    action="PM asks the roles whether this node exposed a FlowPilot skill issue and records that no obvious skill improvement observation was found before checkpoint path",
                    current_node_skill_improvement_check_done=True,
                    active_node="write_checkpoint",
                )
                yield _step(
                    state,
                    label="skill_improvement_observation_logged",
                    action="PM records a nonblocking FlowPilot skill improvement observation for later root-repo maintenance before checkpoint path",
                    current_node_skill_improvement_check_done=True,
                    flowpilot_improvement_live_report_updated=True,
                    active_node="write_checkpoint",
                )
                return
            yield _step(
                state,
                label="chunk_verified",
                action="accept the anti-rough-finish-reviewed chunk for checkpoint",
                completed_chunks=state.completed_chunks + 1,
                node_human_inspections_passed=state.node_human_inspections_passed + 1,
                chunk_state="checkpoint_pending",
                active_node="write_checkpoint",
            )
            return

        yield _step(
            state,
            label="blocked_unhandled_state",
            action="block because no valid transition exists and emit a nonterminal resume notice",
            status="blocked",
            heartbeat_active=False,
            controlled_stop_notice_recorded=True,
            pause_snapshot_written=True,
            active_node="blocked",
        )


def terminal_predicate(current_output, state: State, trace) -> bool:
    del current_output, trace
    return state.status in {"blocked", "complete"}


def no_completion_before_verified_contract(state: State, trace) -> InvariantResult:
    del trace
    if not state.final_report_emitted:
        return InvariantResult.pass_()
    if not state.flowpilot_enabled:
        return InvariantResult.fail("final report emitted before FlowPilot was enabled")
    if not _startup_questions_complete(state):
        return InvariantResult.fail("final report emitted before the three startup questions were answered")
    if not state.startup_banner_emitted:
        return InvariantResult.fail("final report emitted before FlowPilot startup banner was visible")
    if not (
        state.defect_ledger_initialized
        and state.evidence_ledger_initialized
        and state.generated_resource_ledger_initialized
        and state.activity_stream_initialized
        and state.activity_stream_latest_event_written
        and state.flowpilot_improvement_live_report_initialized
    ):
        return InvariantResult.fail(
            "final report emitted before run-level defect, evidence, generated-resource, activity stream, and live FlowPilot improvement ledgers were initialized"
        )
    if not (state.showcase_floor_committed and state.visible_self_interrogation_done):
        return InvariantResult.fail("final report emitted before showcase floor and visible self-interrogation")
    if not _full_interrogation_ready(
        total_questions=state.startup_self_interrogation_questions,
        layer_count=state.startup_self_interrogation_layer_count,
        questions_per_layer=state.startup_self_interrogation_questions_per_layer,
        risk_family_mask=state.startup_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "final report emitted before startup self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    if not (state.quality_candidate_pool_seeded and state.validation_strategy_seeded):
        return InvariantResult.fail(
            "final report emitted before startup grill-me seeded the improvement candidate pool and validation direction"
        )
    if not _root_self_interrogation_gate_ready(state):
        return InvariantResult.fail(
            "final report emitted before startup and product-architecture self-interrogation records were durably dispositioned"
        )
    if not _product_function_architecture_ready(state):
        return InvariantResult.fail(
            "final report emitted before PM-owned product-function architecture, product-officer approval, and reviewer challenge"
        )
    if not (state.dependency_plan_recorded and state.future_installs_deferred):
        return InvariantResult.fail("final report emitted before demand-driven dependency plan was recorded")
    if not state.contract_frozen:
        return InvariantResult.fail("final report emitted before contract was frozen")
    if not (
        _crew_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.crew_archived
    ):
        return InvariantResult.fail(
            "final report emitted before six-agent crew ledger, PM route decision, and terminal crew archive"
        )
    if not (state.heartbeat_active or state.status == "complete"):
        return InvariantResult.fail("final report emitted without heartbeat continuity")
    if not (
        _continuation_ready(state)
        and _terminal_continuation_reconciled(state)
        and state.flowguard_process_design_done
    ):
        return InvariantResult.fail("final report emitted before host continuation probe, lifecycle writeback, and FlowGuard process design")
    if not (
        state.candidate_route_tree_generated
        and state.root_route_model_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
        and state.root_route_model_process_officer_approved
        and state.root_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail("final report emitted before candidate route tree, root process model, root product-function model, and strict gate-obligation review model checks")
    if state.contract_revision != 0:
        return InvariantResult.fail("final report emitted after contract revision")
    if state.completed_chunks < state.required_chunks:
        return InvariantResult.fail("final report emitted before target chunks verified")
    if state.node_human_inspections_passed < state.completed_chunks:
        return InvariantResult.fail("final report emitted before every completed chunk passed human-like product inspection")
    if not (
        state.parent_backward_structural_trigger_rule_recorded
        and state.parent_backward_review_targets_enumerated
    ):
        return InvariantResult.fail(
            "final report emitted before parent backward replay targets were structurally enumerated from the current route"
        )
    if state.composite_backward_reviews_passed < TARGET_PARENT_NODES:
        return InvariantResult.fail(
            "final report emitted before every structurally enumerated parent/composite node passed backward human-like review"
        )
    if state.composite_backward_pm_segment_decisions_recorded < TARGET_PARENT_NODES:
        return InvariantResult.fail(
            "final report emitted before every parent backward replay had a PM segment decision"
        )
    if not state.checkpoint_written:
        return InvariantResult.fail("final report emitted without final checkpoint")
    if not state.route_checked:
        return InvariantResult.fail("final report emitted without checked active route")
    if not state.markdown_synced:
        return InvariantResult.fail("final report emitted before Markdown sync")
    if not (
        state.execution_frontier_written
        and state.codex_plan_synced
        and state.frontier_version == state.route_version
        and state.plan_version == state.frontier_version
    ):
        return InvariantResult.fail("final report emitted before execution frontier and Codex plan sync")
    if not _user_flow_display_gate_passed(state):
        return InvariantResult.fail(
            "final report emitted before visible FlowPilot Route Sign chat/reviewer gate passed"
        )
    if not state.work_beyond_startup_allowed:
        return InvariantResult.fail("final report emitted before PM opened work beyond startup from a factual reviewer report")
    if not (
        state.completion_self_interrogation_done
        and state.high_value_work_review == "exhausted"
    ):
        return InvariantResult.fail("final report emitted before completion grill-me exhausted obvious high-value work")
    if not _self_interrogation_index_final_ready(state):
        return InvariantResult.fail(
            "final report emitted before self-interrogation records were collected into a clean final index"
        )
    if not state.completion_visible_roadmap_emitted:
        return InvariantResult.fail("final report emitted before visible completion user flow diagram")
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
            "final report emitted before final feature, acceptance, quality-candidate, product-model replay, and human-like reviews"
        )
    if not _final_route_wide_gate_ledger_ready(state):
        return InvariantResult.fail(
            "final report emitted before PM-built dynamic route-wide gate ledger, reviewer backward replay, and PM ledger approval"
        )
    if state.blocking_defect_open or state.blocking_defect_fixed_pending_recheck:
        return InvariantResult.fail(
            "final report emitted with an open blocker or fixed-pending-recheck defect still in the defect ledger"
        )
    if not (state.defect_ledger_zero_blocking and state.evidence_credibility_triage_done):
        return InvariantResult.fail(
            "final report emitted before defect ledger zero-blocker check and evidence credibility triage"
        )
    if not _full_interrogation_ready(
        total_questions=state.completion_self_interrogation_questions,
        layer_count=state.completion_self_interrogation_layer_count,
        questions_per_layer=state.completion_self_interrogation_questions_per_layer,
        risk_family_mask=state.completion_self_interrogation_layers,
    ):
        return InvariantResult.fail(
            "final report emitted before completion self-interrogation used dynamic layers, 100 questions per active layer, and required risk-family coverage"
        )
    if not (
        state.terminal_closure_suite_run
        and state.terminal_state_and_evidence_refreshed
        and state.flowpilot_skill_improvement_report_written
    ):
        return InvariantResult.fail(
            "final report emitted before terminal closure suite refreshed state, evidence, lifecycle, role memory, and the PM-owned nonblocking FlowPilot skill improvement report"
        )
    return InvariantResult.pass_()


def frozen_contract_never_changes(state: State, trace) -> InvariantResult:
    del trace
    if state.contract_revision != 0:
        return InvariantResult.fail("frozen contract changed")
    return InvariantResult.pass_()


def startup_question_gate_before_heavy_startup(state: State, trace) -> InvariantResult:
    del trace
    if state.flowpilot_enabled and not state.run_scoped_startup_bootstrap_created:
        return InvariantResult.fail("new FlowPilot startup did not create a run-scoped bootstrap")
    if (
        not state.startup_dialog_stopped_for_answers
        and (
            state.startup_background_agents_answered
            or state.startup_scheduled_continuation_answered
            or state.startup_display_surface_answered
            or state.startup_display_entry_action_done
            or state.startup_banner_emitted
        )
    ):
        return InvariantResult.fail("startup continued after asking questions without stopping for the user's reply")
    if state.startup_banner_emitted and not _startup_questions_complete(state):
        return InvariantResult.fail("startup banner emitted before all three startup answers were recorded")
    if state.startup_banner_emitted and not state.startup_banner_user_dialog_confirmed:
        return InvariantResult.fail("startup banner emitted without confirmed user-dialog display")
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
        return InvariantResult.fail("stale top-level bootstrap was reused as current startup state")
    if state.old_control_state_reused_as_current:
        return InvariantResult.fail("old FlowPilot control state was reused as the current run state")
    if (state.contract_frozen or state.route_version > 0 or state.work_beyond_startup_allowed) and not _run_isolation_ready(state):
        return InvariantResult.fail("FlowPilot advanced before a fresh current run directory and control-state boundary were established")
    if (state.contract_frozen or state.route_version > 0 or state.work_beyond_startup_allowed) and not state.startup_display_entry_action_done:
        return InvariantResult.fail("FlowPilot advanced before resolving the user's startup display surface answer")
    if (state.contract_frozen or state.route_version > 0 or state.work_beyond_startup_allowed) and not state.preflow_visible_plan_cleared:
        return InvariantResult.fail("FlowPilot advanced before clearing the ordinary pre-FlowPilot visible plan")
    if state.contract_frozen and not _root_self_interrogation_gate_ready(state):
        return InvariantResult.fail(
            "contract was frozen before startup and product-architecture self-interrogation findings were durably dispositioned"
        )
    return InvariantResult.pass_()


def dependency_plan_before_route_or_work(state: State, trace) -> InvariantResult:
    del trace
    route_version_exists = state.route_version > 0
    formal_route_or_work_started = (
        state.route_checked
        or state.markdown_synced
        or state.execution_frontier_written
        or state.codex_plan_synced
        or state.visible_user_flow_diagram_emitted
        or state.current_node_high_standard_recheck_written
        or state.node_acceptance_plan_written
        or state.node_acceptance_risk_experiments_mapped
        or state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
        or state.final_report_emitted
    )
    formal_execution_started = (
        state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
        or state.final_report_emitted
    )
    if route_version_exists and not (
        _crew_ready(state)
        and _run_isolation_ready(state)
        and state.pm_initial_route_decision_recorded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and _continuation_lifecycle_valid(state)
    ):
        return InvariantResult.fail(
            "route version created before six-agent crew, fresh run isolation, PM route decision, product-function architecture, frozen contract, dependency plan, and host continuation decision"
        )
    if formal_route_or_work_started and not (
        state.flowguard_process_design_done
        and state.child_skill_manifest_pm_approved_for_route
        and state.candidate_route_tree_generated
        and state.recursive_route_decomposition_policy_written
        and state.route_leaf_readiness_gates_defined
        and state.route_reviewer_depth_review_required
        and state.root_route_model_checked
        and state.root_product_function_model_checked
        and state.strict_gate_obligation_review_model_checked
    ):
        return InvariantResult.fail(
            "formal route or work started before candidate tree, recursive decomposition policy, leaf-readiness gates, and root process/product/strict-review model checks"
        )
    if formal_execution_started and not state.work_beyond_startup_allowed:
        return InvariantResult.fail(
            "formal execution started before PM allowed work beyond startup from a factual reviewer report"
        )
    if state.execution_frontier_written and not state.router_leaf_only_dispatch_policy_checked:
        return InvariantResult.fail(
            "execution frontier was written without verifying Router leaf-only dispatch and parent/module review routing"
        )
    if state.user_flow_diagram_refreshed and not state.user_flow_diagram_shallow_projection_policy_recorded:
        return InvariantResult.fail(
            "user route diagram refreshed before shallow projection, active path, and hidden leaf progress policy was recorded"
        )
    if state.startup_preflight_review_report_written and not state.startup_reviewer_fact_evidence_checked:
        return InvariantResult.fail(
            "startup reviewer report was written without independent fact evidence checks"
        )
    if state.startup_preflight_review_report_written and not (
        state.startup_reviewer_checked_run_isolation
        and state.startup_reviewer_checked_prior_work_boundary
    ):
        return InvariantResult.fail(
            "startup reviewer report was written without checking current run isolation and prior-work import boundary"
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
            "startup reviewer report counted live subagents without checking current-task freshness and historical id reuse"
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
            "PM allowed work beyond startup before the three startup answers were recorded"
        )
    if state.work_beyond_startup_allowed and not _run_isolation_ready(state):
        return InvariantResult.fail(
            "PM allowed work beyond startup before fresh run isolation and prior-work boundary were resolved"
        )
    if state.work_beyond_startup_allowed and not _live_subagent_startup_resolved(state):
        return InvariantResult.fail(
            "PM allowed work beyond startup before fresh current-task live subagents or explicit single-agent fallback were resolved"
        )
    if state.work_beyond_startup_allowed and state.reused_historical_agent_ids:
        return InvariantResult.fail(
            "PM allowed work beyond startup while live-agent evidence reused historical agent ids"
        )
    if state.work_beyond_startup_allowed and not _startup_pm_gate_ready(state):
        return InvariantResult.fail(
            "work beyond startup was allowed before reviewer fact report and PM-owned start-gate opening"
        )
    if state.heartbeat_schedule_created and (
        not state.heartbeat_bound_to_current_run or state.heartbeat_same_name_only_checked
    ):
        return InvariantResult.fail(
            "startup heartbeat evidence did not bind the automation to the current run instead of a same-name record"
        )
    return InvariantResult.pass_()


def continuation_control_loop_until_terminal(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and not state.heartbeat_health_checked:
        return InvariantResult.fail("formal chunk started before continuation readiness check")
    if state.status == "running" and not state.heartbeat_active:
        return InvariantResult.fail("FlowPilot control loop inactive while task is running")
    if state.status in {"blocked", "complete"} and state.heartbeat_active:
        return InvariantResult.fail("FlowPilot control loop still active after terminal state")
    return InvariantResult.pass_()


def controlled_stop_notice_required(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "blocked" and not state.controlled_stop_notice_recorded:
        return InvariantResult.fail(
            "controlled nonterminal stop reached blocked state without a resume notice"
        )
    if state.status == "blocked" and not state.pause_snapshot_written:
        return InvariantResult.fail(
            "controlled nonterminal stop reached blocked state without a pause snapshot"
        )
    if state.status == "complete" and not state.terminal_completion_notice_recorded:
        return InvariantResult.fail(
            "terminal completion reached complete state without a completion notice"
        )
    if state.controlled_stop_notice_recorded and state.status == "complete":
        return InvariantResult.fail(
            "nonterminal resume notice was recorded on a completed route"
        )
    return InvariantResult.pass_()


def formal_chunk_requires_checked_route_and_verification(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if not state.contract_frozen:
            return InvariantResult.fail("chunk started before contract was frozen")
        if not state.route_checked:
            return InvariantResult.fail("chunk started before route model checks")
        if not state.strict_gate_obligation_review_model_checked:
            return InvariantResult.fail("chunk started before strict gate-obligation review model checks")
        if not state.markdown_synced:
            return InvariantResult.fail("chunk started before Markdown sync")
        if not (
            state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.route_version
            and state.plan_version == state.frontier_version
        ):
            return InvariantResult.fail("chunk started before execution frontier and Codex plan were synced")
        if not _user_flow_display_gate_passed(state):
            return InvariantResult.fail(
                "chunk started before visible FlowPilot Route Sign chat/reviewer gate passed"
            )
        if not _continuation_ready(state):
            return InvariantResult.fail("chunk started before host continuation capability was probed and recorded")
        if not (
            state.heartbeat_loaded_state
            and state.heartbeat_loaded_frontier
            and state.heartbeat_loaded_packet_ledger
            and state.heartbeat_loaded_crew_memory
            and state.heartbeat_host_rehydrate_requested
            and state.heartbeat_restored_crew
            and state.heartbeat_rehydrated_crew
            and state.heartbeat_injected_current_run_memory_into_roles
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
            and state.pm_node_decision_recorded
        ):
            return InvariantResult.fail(
                "chunk started before heartbeat loaded packet ledger, rehydrated roles, checked PM controller reminder/router direct-dispatch policy, and synced a sufficiently deep PM runway"
            )
        if not state.pm_review_hold_instruction_written:
            return InvariantResult.fail(
                "chunk started before PM told the reviewer to wait for a later release order"
            )
        if state.chunk_state in {"ready", "executed"} and not state.verification_defined:
            return InvariantResult.fail("chunk started without chunk-level verification")
        if state.chunk_state == "checkpoint_pending" and not state.anti_rough_finish_done:
            return InvariantResult.fail("chunk reached checkpoint path before anti-rough-finish review")
        if not state.node_visible_roadmap_emitted:
            return InvariantResult.fail("chunk started before visible node roadmap")
        if not state.unfinished_current_node_recovery_checked:
            return InvariantResult.fail("chunk started before unfinished-current-node recovery check")
        if not state.parent_focused_interrogation_done:
            return InvariantResult.fail("chunk started before focused parent-scope grill-me")
        if not _focused_interrogation_ready(
            total_questions=state.parent_focused_interrogation_questions,
            scope_id=state.parent_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before parent focused grill-me had 20-50 questions and a scope id"
            )
        if not state.parent_subtree_review_checked:
            return InvariantResult.fail("chunk started before parent-subtree FlowGuard review")
        if not state.parent_product_function_model_checked:
            return InvariantResult.fail("chunk started before parent product-function model check")
        if not state.node_focused_interrogation_done:
            return InvariantResult.fail("chunk started before focused node-level grill-me")
        if not _focused_interrogation_ready(
            total_questions=state.node_focused_interrogation_questions,
            scope_id=state.node_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before node focused grill-me had 20-50 questions and a scope id"
            )
        if not _node_self_interrogation_gate_ready(state):
            return InvariantResult.fail(
                "chunk started before current-node self-interrogation findings were durably dispositioned"
            )
        if not state.node_product_function_model_checked:
            return InvariantResult.fail("chunk started before active node product-function model check")
        if not state.current_node_high_standard_recheck_written:
            return InvariantResult.fail(
                "chunk started before PM current-node high-standard recheck against the product target and semantic fidelity policy"
            )
        if not (
            state.node_acceptance_plan_written
            and state.node_acceptance_risk_experiments_mapped
            and state.active_node_leaf_readiness_gate_passed
            and state.active_node_parent_dispatch_blocked
        ):
            return InvariantResult.fail(
                "chunk started before current node acceptance plan, leaf-readiness gate, parent-dispatch block, and risk experiment mapping"
            )
        if not state.lightweight_self_check_done:
            return InvariantResult.fail("chunk started before lightweight heartbeat self-check")
        if not _lightweight_self_check_ready(
            total_questions=state.lightweight_self_check_questions,
            scope_id=state.lightweight_self_check_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before lightweight self-check had 5-10 questions and a scope id"
            )
        if not (
            state.quality_package_done
            and state.quality_candidate_registry_checked
            and state.quality_raise_decision_recorded
            and state.validation_matrix_defined
        ):
            return InvariantResult.fail(
                "chunk started before quality package recorded thinness, raise decision, child-skill visibility, and validation matrix"
            )
    if state.chunk_state == "checkpoint_pending" and not (
        state.node_human_review_context_loaded
        and state.node_human_neutral_observation_written
        and state.node_human_manual_experiments_run
        and state.node_human_inspection_passed
    ):
        return InvariantResult.fail(
            "checkpoint path reached before human-like node inspection context, neutral observation, experiments, and pass decision"
        )
    return InvariantResult.pass_()


def active_child_skill_binding_required_for_chunk_execution(
    state: State, trace
) -> InvariantResult:
    del trace
    node_execution_binding_needed = (
        state.node_acceptance_risk_experiments_mapped
        or state.worker_packet_child_skill_use_instruction_written
        or state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
    )
    if node_execution_binding_needed and not state.active_child_skill_bindings_written:
        return InvariantResult.fail(
            "active child-skill bindings were missing before current-node chunk execution"
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
        state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}
        or state.worker_output_ready_for_review
    )
    if worker_packet_needed and not state.worker_packet_child_skill_use_instruction_written:
        return InvariantResult.fail(
            "worker packet lacked a direct child-skill use instruction"
        )
    if worker_packet_needed and not (
        state.active_node_leaf_readiness_gate_passed
        and state.active_node_parent_dispatch_blocked
        and state.router_leaf_only_dispatch_policy_checked
    ):
        return InvariantResult.fail(
            "worker packet was possible before leaf readiness and parent/module dispatch blocking were proven"
        )
    if worker_packet_needed and not state.active_child_skill_source_paths_allowed:
        return InvariantResult.fail(
            "worker packet lacked allowed source paths for active child-skill SKILL.md and references"
        )

    worker_result_needs_use_evidence = (
        state.chunk_state in {"verified", "checkpoint_pending"}
        or state.worker_output_ready_for_review
    )
    if worker_result_needs_use_evidence and not state.worker_child_skill_use_evidence_returned:
        return InvariantResult.fail(
            "worker result lacked Child Skill Use Evidence for active bindings"
        )

    reviewer_content_started = (
        state.node_human_review_context_loaded
        or state.node_human_neutral_observation_written
        or state.node_human_manual_experiments_run
        or state.node_reviewer_independent_probe_done
        or state.node_human_inspection_passed
    )
    if reviewer_content_started and not state.reviewer_child_skill_use_evidence_checked:
        return InvariantResult.fail(
            "reviewer child-skill use evidence check was missing before approval"
        )
    return InvariantResult.pass_()


def no_work_while_issue_or_gate_open(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and state.issue != "none":
        return InvariantResult.fail("formal chunk active while issue branch is open")
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and state.high_risk_gate == "pending":
        return InvariantResult.fail("formal chunk active while high-risk gate is pending")
    return InvariantResult.pass_()


def human_review_judgement_requires_neutral_observation(state: State, trace) -> InvariantResult:
    del trace
    if state.node_human_inspection_passed and not state.node_human_neutral_observation_written:
        return InvariantResult.fail("node human-like judgement passed without neutral observation")
    if state.composite_backward_human_review_passed and not state.composite_backward_neutral_observation_written:
        return InvariantResult.fail("composite backward judgement passed without neutral observation")
    if state.final_human_inspection_passed and not state.final_human_neutral_observation_written:
        return InvariantResult.fail("final human-like judgement passed without neutral observation")
    return InvariantResult.pass_()


def pm_review_release_controls_reviewer_start(state: State, trace) -> InvariantResult:
    del trace
    reviewer_started_current_node = (
        state.node_human_review_context_loaded
        or state.node_human_neutral_observation_written
        or state.node_human_manual_experiments_run
        or state.node_reviewer_independent_probe_done
        or state.node_human_inspection_passed
        or state.node_human_review_reviewer_approved
    )
    if reviewer_started_current_node and not (
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
            "human-like reviewer started current-node review before PM release order, physical packet isolation, controller mail-chain audit, envelope/body audit, and per-packet role-origin audit"
        )
    if state.pm_review_release_order_written and not state.worker_output_ready_for_review:
        return InvariantResult.fail(
            "PM wrote a current-gate review release before worker output was ready"
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
        and state.active_node != "deliver_control_blocker_first_handler"
    ):
        return InvariantResult.fail("control-plane reissue blocker was not routed back to the responsible role")
    if (
        state.control_blocker_handling_lane in {"pm_repair_decision_required", "fatal_protocol_violation"}
        and not state.control_blocker_delivered_to_pm
        and state.active_node != "pm_control_blocker_recovery_decision"
    ):
        return InvariantResult.fail("PM repair or fatal control blocker was not routed to Project Manager")
    if (
        state.control_blocker_first_handler == "responsible_role"
        and state.control_blocker_direct_retry_attempts >= state.control_blocker_direct_retry_budget
        and not (state.control_blocker_retry_budget_exhausted and state.control_blocker_escalated_to_pm)
    ):
        return InvariantResult.fail("exhausted direct blocker retries did not escalate to PM")
    if state.control_blocker_delivered_to_pm and state.active_node not in {
        "pm_control_blocker_recovery_decision",
        "pm_control_blocker_return_gate",
    } and not (
        state.pm_blocker_recovery_option_recorded
        and state.pm_blocker_return_gate_recorded
        and state.pm_blocker_silent_pass_forbidden
    ):
        return InvariantResult.fail("PM-handled blocker lacked recovery option, return gate, or silent-pass prohibition")
    return InvariantResult.pass_()


def subagent_must_merge_before_completion(state: State, trace) -> InvariantResult:
    del trace
    if state.final_report_emitted and state.subagent_status in {"pending", "returned"}:
        return InvariantResult.fail("completed while subagent work was not merged")
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if state.subagent_status in {"pending", "returned"}:
            return InvariantResult.fail("formal chunk active while sidecar work was not merged")
    if state.subagent_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("subagent used before child-node sidecar scan")
    if state.subagent_status == "pending" and not state.subagent_scope_checked:
        return InvariantResult.fail("sidecar subagent assigned before bounded/disjoint scope check")
    if state.subagent_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("subagent assigned without a bounded sidecar need")
    return InvariantResult.pass_()


def route_updates_force_recheck_and_resync(state: State, trace) -> InvariantResult:
    del trace
    if state.raw_flowguard_mermaid_used_as_user_flow:
        return InvariantResult.fail(
            "raw FlowGuard Mermaid was used as the user-facing FlowPilot route sign"
        )
    if state.visible_user_flow_diagram_emitted and not state.user_flow_diagram_refreshed:
        return InvariantResult.fail(
            "visible user flow diagram emitted before refreshing the current user flow diagram"
        )
    if state.visible_user_flow_diagram_emitted:
        if state.user_flow_diagram_chat_display_required and not state.user_flow_diagram_chat_displayed:
            return InvariantResult.fail(
                "Cockpit closed route sign was emitted without displaying Mermaid in chat"
            )
        if state.user_flow_diagram_return_edge_required and not state.user_flow_diagram_return_edge_present:
            return InvariantResult.fail(
                "route sign for repair or route mutation was emitted without a return edge"
            )
    if state.user_flow_diagram_reviewer_display_checked and not (
        state.visible_user_flow_diagram_emitted
        and state.user_flow_diagram_reviewer_route_match_checked
    ):
        return InvariantResult.fail(
            "reviewer checked user flow diagram without visible display and route/node match evidence"
        )
    if (
        state.human_inspection_repairs + state.composite_structural_route_repairs
        > state.pm_repair_decision_interrogations
    ):
        return InvariantResult.fail(
            "review-driven route repair written before PM repair strategy interrogation"
        )
    if state.route_version > 0 and state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if not (
            state.route_checked
            and state.markdown_synced
            and state.execution_frontier_written
            and state.codex_plan_synced
            and state.frontier_version == state.route_version
            and state.plan_version == state.frontier_version
            and state.user_flow_diagram_refreshed
            and _user_flow_display_gate_passed(state)
        ):
            return InvariantResult.fail("route update was not checked, summarized, frontier-synced, plan-synced, and visibly mapped before work")
    return InvariantResult.pass_()


def stable_heartbeat_prompt_not_route_state(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.route_version > 1
        and state.host_continuation_supported
        and not state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail("route changed without a stable heartbeat launcher that reads persisted state")
    if (
        state.route_version > 1
        and state.manual_resume_mode_recorded
        and state.stable_heartbeat_launcher_recorded
    ):
        return InvariantResult.fail("manual-resume route unexpectedly created a stable heartbeat launcher")
    return InvariantResult.pass_()


def startup_continuation_bootstraps_before_controller_core(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_core_loaded and not _continuation_ready(state):
        return InvariantResult.fail(
            "Controller core loaded before startup continuation was bound to heartbeat or manual resume"
        )
    if state.controller_core_loaded and state.host_continuation_supported and not _automated_continuation_configured(state):
        return InvariantResult.fail(
            "Controller core loaded before scheduled-continuation heartbeat was fully configured"
        )
    if state.controller_core_loaded and state.manual_resume_mode_recorded and state.heartbeat_schedule_created:
        return InvariantResult.fail(
            "Controller core loaded after manual-resume startup that still created heartbeat automation"
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
        state.route_checked
        or state.chunk_state != "none"
        or state.final_report_emitted
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


def material_handoff_before_pm_route_design(state: State, trace) -> InvariantResult:
    del trace
    if state.material_intake_packet_written and not (
        state.material_sources_scanned
        and state.material_source_summaries_written
        and state.material_source_quality_classified
        and state.local_skill_inventory_written
        and state.local_skill_inventory_candidate_classified
    ):
        return InvariantResult.fail(
            "Material Intake Packet was written before sources and local skills were scanned, summarized, quality-classified, and candidate-classified"
        )
    if state.material_reviewer_sufficiency_approved and not (
        state.material_intake_packet_written
        and state.material_reviewer_sufficiency_checked
    ):
        return InvariantResult.fail(
            "material packet was approved before reviewer sufficiency check"
        )
    if state.pm_material_understanding_memo_written and not (
        state.material_reviewer_sufficiency_approved
    ):
        return InvariantResult.fail(
            "PM material understanding memo was written before reviewer-approved intake evidence"
        )
    if state.pm_material_discovery_decision_recorded and not (
        state.pm_material_understanding_memo_written
        and state.pm_material_complexity_classified
    ):
        return InvariantResult.fail(
            "PM material discovery decision was recorded before understanding memo and complexity classification"
        )
    if state.pm_material_research_decision_recorded and not state.pm_material_discovery_decision_recorded:
        return InvariantResult.fail(
            "PM material research-package decision was recorded before the material discovery decision"
        )
    if (
        state.pm_material_research_decision_recorded
        and state.material_research_need not in {"not_required", "required"}
    ):
        return InvariantResult.fail("PM material research-package decision did not classify need")
    if state.pm_research_package_written and not (
        state.pm_material_research_decision_recorded
        and state.material_research_need == "required"
    ):
        return InvariantResult.fail(
            "PM research package was written without a recorded material gap requiring research"
        )
    if state.research_tool_capability_decision_recorded and not state.pm_research_package_written:
        return InvariantResult.fail(
            "research tool capability decision was recorded before the PM research package"
        )
    if state.research_worker_report_returned and not (
        state.pm_research_package_written
        and state.research_tool_capability_decision_recorded
    ):
        return InvariantResult.fail(
            "worker research report returned before PM package and tool capability decision"
        )
    if state.research_reviewer_direct_source_check_done and not state.research_worker_report_returned:
        return InvariantResult.fail(
            "research reviewer checked sources before a worker research report existed"
        )
    if state.research_reviewer_rework_required and not state.research_reviewer_direct_source_check_done:
        return InvariantResult.fail(
            "research reviewer required rework before direct source checks"
        )
    if state.research_worker_rework_completed and not state.research_reviewer_rework_required:
        return InvariantResult.fail(
            "research worker rework completed before reviewer requested rework"
        )
    if state.research_reviewer_recheck_done and not state.research_worker_rework_completed:
        return InvariantResult.fail(
            "research reviewer rechecked before worker completed research rework"
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
            "research reviewer sufficiency passed without direct source check and required rework/recheck evidence"
        )
    if state.pm_research_result_absorbed_or_route_mutated and not state.research_reviewer_sufficiency_passed:
        return InvariantResult.fail(
            "PM absorbed or routed research result before reviewer sufficiency pass"
        )
    if (
        state.product_function_architecture_pm_synthesized
        and state.material_research_need == "required"
        and not state.pm_research_result_absorbed_or_route_mutated
    ):
        return InvariantResult.fail(
            "product-function architecture started while required material research package was unresolved"
        )
    if state.pm_initial_route_decision_recorded and not _material_handoff_ready(state):
        return InvariantResult.fail(
            "PM route decision was recorded before reviewed material handoff"
        )
    if state.pm_child_skill_selection_manifest_written and not (
        _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.pm_initial_route_decision_recorded
    ):
        return InvariantResult.fail(
            "PM child-skill selection manifest was written before product architecture, frozen contract, and initial route direction were ready"
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
    any_role_approval = (
        state.startup_self_interrogation_pm_ratified
        or state.material_reviewer_sufficiency_approved
        or state.product_function_architecture_product_officer_approved
        or state.product_function_architecture_reviewer_challenged
        or state.child_skill_manifest_reviewer_reviewed
        or state.child_skill_manifest_process_officer_approved
        or state.child_skill_manifest_product_officer_approved
        or state.child_skill_manifest_pm_approved_for_route
        or state.root_route_model_process_officer_approved
        or state.root_product_function_model_product_officer_approved
        or state.parent_product_function_model_product_officer_approved
        or state.node_product_function_model_product_officer_approved
        or state.node_human_review_reviewer_approved
        or state.composite_backward_review_reviewer_approved
        or state.final_product_function_model_product_officer_approved
        or state.final_human_review_reviewer_approved
        or state.final_route_wide_gate_ledger_pm_completion_approved
        or state.pm_start_gate_opened
    )
    if any_role_approval and not state.independent_approval_protocol_recorded:
        return InvariantResult.fail(
            "role approval was recorded before the independent adversarial approval protocol existed"
        )
    if state.startup_self_interrogation_pm_ratified and not _crew_ready(state):
        return InvariantResult.fail(
            "startup self-interrogation was ratified before the six-agent crew was ready"
        )
    if (
        state.material_reviewer_sufficiency_approved
        and not state.material_reviewer_direct_source_probe_done
    ):
        return InvariantResult.fail(
            "material reviewer approved sufficiency before independently probing direct source material"
        )
    if state.product_function_architecture_pm_synthesized and not (
        _crew_ready(state) and _material_handoff_ready(state)
    ):
        return InvariantResult.fail(
            "PM product-function architecture was synthesized before crew recovery and reviewed material handoff"
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
    if (
        state.product_function_architecture_product_officer_approved
        and not product_architecture_inputs_ready
    ):
        return InvariantResult.fail(
            "product-function architecture approval was recorded before all PM product artifacts existed"
        )
    if (
        state.product_function_architecture_product_officer_approved
        and not state.product_architecture_officer_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "product officer approved product-function architecture before adversarial modelability and failure-path probe"
        )
    if state.product_function_architecture_reviewer_challenged and not (
        state.product_function_architecture_product_officer_approved
        and state.reviewer_ready
        and state.product_architecture_reviewer_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "human-like reviewer challenged the product-function architecture before product officer approval, reviewer recovery, or independent adversarial probe"
        )
    if state.flowguard_process_design_done and not (
        state.startup_self_interrogation_pm_ratified
        and _product_function_architecture_ready(state)
        and state.contract_frozen
    ):
        return InvariantResult.fail(
            "FlowGuard route design started before PM ratified startup self-interrogation, product-function architecture, and contract freeze"
        )
    if state.flowguard_process_design_done and not state.child_skill_manifest_pm_approved_for_route:
        return InvariantResult.fail(
            "FlowGuard route design started before the PM-approved child-skill gate manifest was ready"
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
            "PM approved child-skill gate manifest before PM skill selection, minimum sufficient complexity review, discovery, extraction, approver assignment, independent validation, and reviewer approval"
        )
    if (
        state.child_skill_manifest_reviewer_reviewed
    ) and not state.child_skill_manifest_independent_validation_done:
        return InvariantResult.fail(
            "child-skill manifest role approval was recorded before independent manifest validation"
        )
    if (
        state.root_route_model_process_officer_approved
        or state.root_product_function_model_product_officer_approved
        or state.parent_product_function_model_product_officer_approved
        or state.node_product_function_model_product_officer_approved
    ) and not state.flowguard_officer_model_adversarial_probe_done:
        return InvariantResult.fail(
            "FlowGuard officer model approval was recorded before adversarial model probe evidence"
        )
    if (
        state.root_route_model_process_officer_approved
        or state.root_product_function_model_product_officer_approved
        or state.parent_product_function_model_product_officer_approved
        or state.node_product_function_model_product_officer_approved
    ) and not (
        state.flowguard_model_report_risk_tiers_done
        and state.flowguard_model_report_pm_review_agenda_done
        and state.flowguard_model_report_toolchain_recommendations_done
        and state.flowguard_model_report_confidence_boundary_done
    ):
        return InvariantResult.fail(
            "FlowGuard officer model approval was recorded before the report extracted PM risk tiers, review agenda, toolchain recommendations, and confidence boundary"
        )
    if state.root_route_model_process_officer_approved and not state.root_route_model_checked:
        return InvariantResult.fail("root route approval is stale without a root route model check")
    if state.root_route_model_checked and not state.root_route_model_process_officer_approved:
        return InvariantResult.fail("root route model check lacks process FlowGuard officer approval")
    if (
        state.root_product_function_model_product_officer_approved
        and not state.root_product_function_model_checked
    ):
        return InvariantResult.fail(
            "root product-function approval is stale without a root product-function model check"
        )
    if (
        state.root_product_function_model_checked
        and not state.root_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "root product-function model check lacks product FlowGuard officer approval"
        )
    if (
        state.parent_product_function_model_product_officer_approved
        and not state.parent_product_function_model_checked
    ):
        return InvariantResult.fail(
            "parent product-function approval is stale without a parent product-function model check"
        )
    if (
        state.parent_product_function_model_checked
        and not state.parent_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "parent product-function model check lacks product FlowGuard officer approval"
        )
    if (
        state.node_product_function_model_product_officer_approved
        and not state.node_product_function_model_checked
    ):
        return InvariantResult.fail(
            "node product-function approval is stale without a node product-function model check"
        )
    if (
        state.node_product_function_model_checked
        and not state.node_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "node product-function model check lacks product FlowGuard officer approval"
        )
    if state.node_human_review_reviewer_approved and not (
        state.node_human_inspection_passed
        and state.node_reviewer_independent_probe_done
    ):
        return InvariantResult.fail("node reviewer approval is stale without a node human review pass and independent probe")
    if state.node_human_review_reviewer_approved and (
        state.blocking_defect_open or state.blocking_defect_fixed_pending_recheck
    ):
        return InvariantResult.fail(
            "node reviewer approval recorded while a blocker was open or fixed-pending-recheck in the defect ledger"
        )
    if state.pm_defect_triage_done and not state.defect_event_logged_for_blocker:
        return InvariantResult.fail("PM triaged a blocking defect before the discovering role logged a defect event")
    if state.node_human_inspection_passed and not state.node_human_review_reviewer_approved:
        return InvariantResult.fail("node human review pass lacks reviewer approval")
    if (
        state.composite_backward_review_reviewer_approved
        and not (
            state.composite_backward_human_review_passed
            and state.composite_reviewer_independent_probe_done
        )
    ):
        return InvariantResult.fail(
            "composite reviewer approval is stale without a composite backward review pass and independent probe"
        )
    if (
        state.composite_backward_human_review_passed
        and not state.composite_backward_review_reviewer_approved
    ):
        return InvariantResult.fail(
            "composite backward review pass lacks reviewer approval"
        )
    if (
        state.final_product_function_model_product_officer_approved
        and not (
            state.final_product_function_model_replayed
            and state.final_product_model_officer_adversarial_probe_done
        )
    ):
        return InvariantResult.fail(
            "final product-function approval is stale without final product replay and adversarial officer probe"
        )
    if (
        state.final_product_function_model_replayed
        and not state.final_product_function_model_product_officer_approved
    ):
        return InvariantResult.fail(
            "final product-function replay lacks product FlowGuard officer approval"
        )
    if state.final_human_review_reviewer_approved and not (
        state.final_human_inspection_passed
        and state.final_human_reviewer_independent_probe_done
    ):
        return InvariantResult.fail("final reviewer approval is stale without final human review pass and independent probe")
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
            "PM built final route-wide gate ledger before current route scan, deep leaf and parent review gate collection, generated-resource lineage, stale-evidence check, superseded explanations, clean self-interrogation index, zero unresolved count, and zero unresolved residual risks"
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
            "final route-wide gate ledger reviewer replay ran before PM-built clean ledger and terminal human backward review map, delivered-product replay, node-by-node checks, PM segment decisions, and repair restart policy"
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
            "PM approved final route-wide gate ledger before reviewer replay, zero unresolved count, zero unresolved residual risks, and independent PM audit"
        )
    if state.pm_completion_decision_recorded and not state.final_route_wide_gate_ledger_pm_completion_approved:
        return InvariantResult.fail(
            "PM completion decision recorded before final route-wide gate ledger approval"
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
            "PM completion decision recorded before terminal closure suite refreshed state and evidence"
        )
    if state.pm_completion_decision_recorded and not state.crew_archived:
        return InvariantResult.fail("PM completion decision recorded before crew archive")
    if state.final_report_emitted and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("final report emitted before PM completion approval")
    return InvariantResult.pass_()


def crew_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.startup_self_interrogation_pm_ratified and not (
        state.crew_memory_policy_written
        and state.crew_memory_packets_written == CREW_SIZE
    ):
        return InvariantResult.fail("startup was ratified before all role memory packets were written")
    if state.heartbeat_pm_decision_requested and not (
        state.heartbeat_loaded_state
        and state.heartbeat_loaded_frontier
        and state.heartbeat_loaded_packet_ledger
        and state.heartbeat_loaded_crew_memory
        and state.heartbeat_host_rehydrate_requested
        and state.heartbeat_restored_crew
        and state.heartbeat_rehydrated_crew
        and state.heartbeat_injected_current_run_memory_into_roles
        and state.crew_rehydration_report_written
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "PM resume was requested before current-run state, packet ledger, live six-role memory rehydration, and memory injection completed"
        )
    if state.pm_resume_decision_recorded and not (
        state.heartbeat_pm_controller_reminder_checked
        and state.heartbeat_reviewer_dispatch_policy_checked
    ):
        return InvariantResult.fail(
            "PM resume decision was accepted before controller reminder and reviewer-dispatch policy were checked"
        )
    if state.checkpoint_written and state.completed_chunks > 0 and not state.role_memory_refreshed_after_work:
        return InvariantResult.fail("checkpoint written before role memory refresh after meaningful role work")
    if state.crew_archived and not state.crew_memory_archived:
        return InvariantResult.fail("crew ledger archived before role memory archive")
    return InvariantResult.pass_()


def next_route_node_requires_fresh_route_sign(state: State, trace) -> InvariantResult:
    del trace
    if state.node_acceptance_plan_written and not (
        state.current_node_high_standard_recheck_written
        and state.current_node_minimum_sufficient_complexity_review_written
    ):
        return InvariantResult.fail(
            "node acceptance plan was written before PM current-node high-standard and minimum sufficient complexity rechecks"
        )
    if (
        state.node_acceptance_plan_written
        and 0 < state.completed_chunks < state.required_chunks
        and not state.user_flow_diagram_fresh_for_current_node
    ):
        return InvariantResult.fail(
            "next route-node acceptance plan reused stale FlowPilot Route Sign display evidence"
        )
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="no_completion_before_verified_contract",
        description="Final report requires frozen contract, checked route, synced summary, verified chunks, and checkpoint.",
        predicate=no_completion_before_verified_contract,
    ),
    Invariant(
        name="frozen_contract_never_changes",
        description="Autopilot may update routes and models, but not the frozen acceptance contract.",
        predicate=frozen_contract_never_changes,
    ),
    Invariant(
        name="startup_question_gate_before_heavy_startup",
        description="FlowPilot asks the three startup questions, stops for answers, and emits the banner only after all three answers exist.",
        predicate=startup_question_gate_before_heavy_startup,
    ),
    Invariant(
        name="dependency_plan_before_route_or_work",
        description="Route creation and formal work require demand-driven dependency planning first.",
        predicate=dependency_plan_before_route_or_work,
    ),
    Invariant(
        name="continuation_control_loop_until_terminal",
        description="FlowPilot keeps a control loop active while running; real heartbeat health is required only when automated continuation is supported.",
        predicate=continuation_control_loop_until_terminal,
    ),
    Invariant(
        name="controlled_stop_notice_required",
        description="Controlled nonterminal stops emit a manual/heartbeat resume notice, and terminal completion emits a completion notice.",
        predicate=controlled_stop_notice_required,
    ),
    Invariant(
        name="formal_chunk_requires_checked_route_and_verification",
        description="Formal execution chunks require a checked route, synced summary, and predeclared verification.",
        predicate=formal_chunk_requires_checked_route_and_verification,
    ),
    Invariant(
        name="active_child_skill_binding_required_for_chunk_execution",
        description="Current-node chunks require active child-skill bindings, packet use instructions, source paths, use evidence, and reviewer checks.",
        predicate=active_child_skill_binding_required_for_chunk_execution,
    ),
    Invariant(
        name="no_work_while_issue_or_gate_open",
        description="Open issues and hard safety gates block formal chunk execution.",
        predicate=no_work_while_issue_or_gate_open,
    ),
    Invariant(
        name="human_review_judgement_requires_neutral_observation",
        description="Human-like review records what was observed before pass/fail judgement.",
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
        name="subagent_must_merge_before_completion",
        description="Optional subagent results must return to the controller before completion.",
        predicate=subagent_must_merge_before_completion,
    ),
    Invariant(
        name="route_updates_force_recheck_and_resync",
        description="A changed route must be FlowGuard-checked and summarized before more work.",
        predicate=route_updates_force_recheck_and_resync,
    ),
    Invariant(
        name="next_route_node_requires_fresh_route_sign",
        description="A new route-node entry must refresh and visibly display its own FlowPilot Route Sign.",
        predicate=next_route_node_requires_fresh_route_sign,
    ),
    Invariant(
        name="stable_heartbeat_prompt_not_route_state",
        description="Heartbeat automation stays a stable launcher while persisted route/frontier state carries next-jump changes.",
        predicate=stable_heartbeat_prompt_not_route_state,
    ),
    Invariant(
        name="startup_continuation_bootstraps_before_controller_core",
        description="Startup establishes heartbeat or manual-resume continuation before Controller core handoff.",
        predicate=startup_continuation_bootstraps_before_controller_core,
    ),
    Invariant(
        name="heartbeat_continuation_is_lifecycle_state",
        description="Automated continuation uses only a stable heartbeat launcher; manual-resume routes must not create heartbeat automation.",
        predicate=heartbeat_continuation_is_lifecycle_state,
    ),
    Invariant(
        name="material_handoff_before_pm_route_design",
        description="Material intake, reviewer sufficiency, and PM understanding happen before PM route design.",
        predicate=material_handoff_before_pm_route_design,
    ),
    Invariant(
        name="actor_authority_gates_require_correct_role",
        description="Authority-sensitive gates require the PM, reviewer, or matching FlowGuard officer and reject stale approvals.",
        predicate=actor_authority_gates_require_correct_role,
    ),
    Invariant(
        name="crew_memory_rehydration_required",
        description="Six-role recovery uses persisted role memory before PM runway, checkpoint, or terminal archive.",
        predicate=crew_memory_rehydration_required,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 145


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((AutopilotStep(),), name="flowguard_project_autopilot_meta")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple(
        (result.label, result.new_state)
        for result in AutopilotStep().apply(Tick(), state)
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
