"""FlowGuard model for the FlowPilot meta workflow.

This model treats FlowGuard as both process designer and checker. FlowPilot
must start with a showcase-grade floor, make self-interrogation visible, create
real manual resume binding continuity, design the route through FlowGuard before execution,
and avoid completion while obvious high-value work remains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


TARGET_CHUNKS = 2
TARGET_PARENT_NODES = 2
MIN_CURRENT_BACKGROUND_AGENT_COUNT = 1
MAX_ROUTE_REVISIONS = 2
MAX_IMPL_RETRIES = 1
MAX_EXPERIMENTS = 1
MAX_STANDARD_EXPANSIONS = 1
MAX_QUALITY_ROUTE_RAISES = 1
MAX_QUALITY_REWORKS = 1
MAX_COMPOSITE_STRUCTURAL_REPAIRS = 1
MAX_TERMINAL_BACKWARD_REPLAY_REPAIRS = 1
MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER = 100
MIN_FOCUSED_SELF_INTERROGATION_QUESTIONS = 20
MAX_FOCUSED_SELF_INTERROGATION_QUESTIONS = 50
DEFAULT_FOCUSED_SELF_INTERROGATION_QUESTIONS = 30
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
LAYER_RECOVERY_LIFECYCLE = 1 << 6
LAYER_DELIVERY_SHOWCASE = 1 << 7
REQUIRED_RISK_FAMILY_MASK = (
    LAYER_GOAL_ACCEPTANCE
    | LAYER_FUNCTIONAL_CAPABILITY
    | LAYER_DATA_STATE
    | LAYER_IMPLEMENTATION_STRATEGY
    | LAYER_UI_EXPERIENCE
    | LAYER_VALIDATION
    | LAYER_RECOVERY_LIFECYCLE
    | LAYER_DELIVERY_SHOWCASE
)


@dataclass(frozen=True, slots=True)
class Tick:
    """One manual resume binding/FlowPilot runtime decision step."""


@dataclass(frozen=True, slots=True)
class Action:
    name: str


@dataclass(frozen=True, slots=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    flowpilot_enabled: bool = False
    run_scoped_startup_bootstrap_created: bool = False
    stale_top_level_bootstrap_reused: bool = False
    startup_intake_ui_completed: bool = False
    startup_intake_result_recorded: bool = False
    startup_banner_emitted: bool = False
    startup_banner_user_dialog_confirmed: bool = False
    startup_background_collaboration_ack_recorded: bool = False
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
    ordinary_resource_discovery_child_registered: bool = False
    ordinary_resource_discovery_child_passed: bool = False
    ordinary_resource_discovery_evidence_current: bool = False
    control_plane_resource_boundedness_child_registered: bool = False
    control_plane_resource_boundedness_child_passed: bool = False
    control_plane_resource_boundedness_evidence_current: bool = False
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
    product_architecture_flowguard_operator_adversarial_probe_done: bool = False
    product_function_architecture_flowguard_operator_product_scope_approved: bool = False
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
    role_binding_policy_written: bool = False
    role_binding_count: int = 0
    project_manager_ready: bool = False
    reviewer_ready: bool = False
    flowguard_operator_route_scope_ready: bool = False
    flowguard_operator_product_scope_ready: bool = False
    worker_ready: bool = False
    role_binding_ledger_written: bool = False
    role_identity_protocol_recorded: bool = False
    pm_flowguard_delegation_policy_recorded: bool = False
    flowguard_operator_owned_async_modeling_policy_recorded: bool = False
    flowguard_operator_model_report_provenance_policy_recorded: bool = False
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
    pm_initial_route_decision_recorded: bool = False
    pm_child_skill_selection_manifest_written: bool = False
    pm_child_skill_minimum_sufficient_complexity_review_written: bool = False
    pm_child_skill_selection_scope_decisions_recorded: bool = False
    child_skill_route_design_discovery_started: bool = False
    child_skill_initial_gate_manifest_extracted: bool = False
    child_skill_gate_approvers_assigned: bool = False
    child_skill_manifest_independent_validation_done: bool = False
    child_skill_manifest_reviewer_reviewed: bool = False
    child_skill_manifest_flowguard_operator_route_scope_approved: bool = False
    child_skill_manifest_flowguard_operator_product_scope_approved: bool = False
    child_skill_manifest_pm_approved_for_route: bool = False
    resume_loaded_state: bool = False
    resume_loaded_frontier: bool = False
    resume_loaded_packet_ledger: bool = False
    resume_loaded_role_binding_memory: bool = False
    resume_host_rehydrate_requested: bool = False
    resume_restored_runtime_roles: bool = False
    resume_rehydrated_runtime_roles: bool = False
    resume_injected_current_run_memory_into_roles: bool = False
    role_binding_recovery_report_written: bool = False
    replacement_roles_seeded_from_memory: bool = False
    resume_pm_decision_requested: bool = False
    resume_pm_controller_reminder_checked: bool = False
    resume_reviewer_dispatch_policy_checked: bool = False
    pm_resume_decision_recorded: bool = False
    pm_completion_runway_recorded: bool = False
    pm_runway_hard_stops_recorded: bool = False
    pm_runway_checkpoint_cadence_recorded: bool = False
    pm_runway_synced_to_plan: bool = False
    plan_sync_method_recorded: bool = False
    visible_plan_has_runway_depth: bool = False
    pm_node_decision_recorded: bool = False
    role_binding_ledger_archived: bool = False
    role_binding_memory_archived: bool = False
    continuation_probe_done: bool = False
    continuation_host_kind_recorded: bool = False
    continuation_evidence_written: bool = False
    manual_resume_binding_supported: bool = False
    manual_resume_boundary_recorded: bool = False
    foreground_control_loop_active: bool = False
    manual_resume_binding_configured: bool = False
    manual_resume_binding_interval_seconds: int = 0
    stable_manual_resume_launcher_recorded: bool = False
    manual_resume_binding_health_checked: bool = False
    background_collaboration_start_decision_recorded: bool = False
    runtime_role_bindings_opened: bool = False
    runtime_role_bindings_current_task_ready: bool = False
    role_bindings_opened_after_startup_answers: bool = False
    role_bindings_opened_after_route_allocation: bool = False
    historical_agent_ids_compared: bool = False
    reused_historical_agent_ids: bool = False
    startup_runtime_mechanical_audit_written: bool = False
    startup_runtime_mechanical_blocking_findings: bool = False
    startup_runtime_mechanical_evidence_checked: bool = False
    startup_runtime_checked_run_identity: bool = False
    startup_runtime_checked_prior_work_boundary: bool = False
    startup_runtime_checked_role_binding_freshness: bool = False
    startup_runtime_checked_no_historical_agent_reuse: bool = False
    startup_runtime_checked_capability_resolution: bool = False
    startup_pm_checked_manual_resume_binding: bool = False
    startup_pm_capability_resolution_recorded: bool = False
    manual_resume_binding_bound_to_current_run: bool = False
    manual_resume_binding_name_only_checked: bool = False
    pm_returned_startup_blockers: bool = False
    startup_worker_remediation_completed: bool = False
    pm_startup_intake_node_package_decision_recorded: bool = False
    pm_startup_intake_released_to_route: bool = False
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
    flowguard_operator_model_adversarial_probe_done: bool = False
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
    root_route_model_flowguard_operator_route_scope_approved: bool = False
    root_product_function_model_checked: bool = False
    root_product_function_model_flowguard_operator_product_scope_approved: bool = False
    strict_gate_obligation_review_model_checked: bool = False
    parent_subtree_review_checked: bool = False
    parent_product_function_model_checked: bool = False
    parent_product_function_model_flowguard_operator_product_scope_approved: bool = False
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
    node_product_function_model_flowguard_operator_product_scope_approved: bool = False
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
    pm_package_result_disposition_recorded: bool = False
    pm_package_result_disposition_absorbed: bool = False
    pm_formal_gate_package_released: bool = False
    pm_formal_gate_package_identity_recorded: bool = False
    pm_review_release_order_written: bool = False
    pm_released_reviewer_for_current_gate: bool = False
    packet_runtime_physical_files_written: bool = False
    controller_context_body_exclusion_verified: bool = False
    current_assignment_audit_done: bool = False
    recipient_pre_open_current_assignment_check_done: bool = False
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
    inspection_issue_interrogated: bool = False
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
    composite_issue_interrogated: bool = False
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
    sidecar_role_pool_exists: bool = False
    sidecar_role_idle_available: bool = False
    sidecar_role_scope_checked: bool = False
    sidecar_role_status: str = "none"  # none | idle | pending | returned | merged
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
    final_product_model_flowguard_operator_adversarial_probe_done: bool = False
    final_product_function_model_flowguard_operator_product_scope_approved: bool = False
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
    resume_decision_records: int = 0


def _step(state: State, *, label: str, action: str, **changes) -> FunctionResult:
    return FunctionResult(
        output=Action(action),
        new_state=replace(
            state,
            resume_decision_records=1,
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
        "parent_product_function_model_flowguard_operator_product_scope_approved": False,
        "node_product_function_model_checked": False,
        "node_product_function_model_flowguard_operator_product_scope_approved": False,
        "node_human_review_context_loaded": False,
        "node_human_neutral_observation_written": False,
        "node_human_manual_experiments_run": False,
        "node_reviewer_independent_probe_done": False,
        "node_human_inspection_passed": False,
        "node_human_review_reviewer_approved": False,
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
        "current_assignment_audit_done": False,
        "recipient_pre_open_current_assignment_check_done": False,
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
        "inspection_issue_interrogated": False,
        "composite_backward_context_loaded": False,
        "composite_child_evidence_replayed": False,
        "composite_backward_neutral_observation_written": False,
        "composite_structure_decision_recorded": False,
        "composite_reviewer_independent_probe_done": False,
        "composite_backward_human_review_passed": False,
        "composite_backward_review_reviewer_approved": False,
        "composite_backward_pm_segment_decision_recorded": False,
        "composite_issue_interrogated": False,
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
            "resume_loaded_state": False,
            "resume_loaded_frontier": False,
            "resume_loaded_packet_ledger": False,
            "resume_loaded_role_binding_memory": False,
            "resume_host_rehydrate_requested": False,
            "resume_restored_runtime_roles": False,
            "resume_rehydrated_runtime_roles": False,
            "resume_injected_current_run_memory_into_roles": False,
            "role_binding_recovery_report_written": False,
            "replacement_roles_seeded_from_memory": False,
            "resume_pm_decision_requested": False,
            "resume_pm_controller_reminder_checked": False,
            "resume_reviewer_dispatch_policy_checked": False,
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
        and questions_per_layer >= MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
        and total_questions >= layer_count * MIN_FULL_SELF_INTERROGATION_QUESTIONS_PER_LAYER
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
        and MIN_FOCUSED_SELF_INTERROGATION_QUESTIONS
        <= total_questions
        <= MAX_FOCUSED_SELF_INTERROGATION_QUESTIONS
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
        state.startup_intake_ui_completed
        and state.startup_intake_result_recorded
        and state.startup_background_collaboration_ack_recorded
        and state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    )


def _product_function_architecture_ready(state: State) -> bool:
    return (
        _ordinary_resource_discovery_child_ready(state)
        and _control_plane_resource_boundedness_child_ready(state)
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
        and state.product_architecture_flowguard_operator_adversarial_probe_done
        and state.product_function_architecture_flowguard_operator_product_scope_approved
        and state.product_architecture_reviewer_adversarial_probe_done
        and state.product_function_architecture_reviewer_challenged
    )


def _ordinary_resource_discovery_child_ready(state: State) -> bool:
    return (
        state.startup_self_interrogation_pm_ratified
        and state.ordinary_resource_discovery_child_registered
        and state.ordinary_resource_discovery_child_passed
        and state.ordinary_resource_discovery_evidence_current
    )


def _control_plane_resource_boundedness_child_ready(state: State) -> bool:
    return (
        state.control_plane_resource_boundedness_child_registered
        and state.control_plane_resource_boundedness_child_passed
        and state.control_plane_resource_boundedness_evidence_current
    )


def _runtime_roles_ready(state: State) -> bool:
    return (
        state.role_binding_policy_written
        and state.role_binding_ledger_written
        and state.role_identity_protocol_recorded
        and state.pm_flowguard_delegation_policy_recorded
        and state.flowguard_operator_owned_async_modeling_policy_recorded
        and state.flowguard_operator_model_report_provenance_policy_recorded
        and state.controller_coordination_boundary_recorded
        and state.independent_approval_protocol_recorded
        and state.role_binding_memory_policy_written
        and state.role_binding_memory_packets_written >= MIN_CURRENT_BACKGROUND_AGENT_COUNT
    )


def _manual_resume_binding_configured(state: State) -> bool:
    return (
        state.continuation_probe_done
        and state.continuation_host_kind_recorded
        and state.continuation_evidence_written
        and state.manual_resume_binding_supported
        and not state.manual_resume_boundary_recorded
        and state.manual_resume_binding_configured
        and state.manual_resume_binding_interval_seconds == 1
        and state.stable_manual_resume_launcher_recorded
        and state.manual_resume_binding_bound_to_current_run
        and not state.manual_resume_binding_name_only_checked
    )


def _manual_resume_binding_ready(state: State) -> bool:
    return _manual_resume_binding_configured(state)


def _manual_resume_ready(state: State) -> bool:
    return (
        state.continuation_probe_done
        and state.continuation_host_kind_recorded
        and state.continuation_evidence_written
        and not state.manual_resume_binding_supported
        and state.manual_resume_boundary_recorded
        and not state.manual_resume_binding_configured
        and state.manual_resume_binding_interval_seconds == 0
        and not state.stable_manual_resume_launcher_recorded
    )


def _continuation_ready(state: State) -> bool:
    return _manual_resume_binding_ready(state) or _manual_resume_ready(state)


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
        and state.prior_control_state_quarantined
        and not state.old_control_state_reused_as_current
    )


def _runtime_role_binding_startup_resolved(state: State) -> bool:
    return (
        state.background_collaboration_start_decision_recorded
        and state.runtime_role_bindings_opened
        and state.runtime_role_bindings_current_task_ready
        and state.role_bindings_opened_after_startup_answers
        and state.role_bindings_opened_after_route_allocation
        and state.historical_agent_ids_compared
        and not state.reused_historical_agent_ids
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
            _manual_resume_binding_configured(state)
            and state.lifecycle_reconciliation_done
        )
    )


def _startup_intake_release_ready(state: State) -> bool:
    return (
        state.startup_runtime_mechanical_audit_written
        and not state.startup_runtime_mechanical_blocking_findings
        and state.startup_runtime_mechanical_evidence_checked
        and _run_isolation_ready(state)
        and state.startup_runtime_checked_run_identity
        and state.startup_runtime_checked_prior_work_boundary
        and state.startup_runtime_checked_role_binding_freshness
        and state.startup_runtime_checked_no_historical_agent_reuse
        and state.startup_runtime_checked_capability_resolution
        and (
            state.manual_resume_boundary_recorded
            or (
                state.startup_pm_checked_manual_resume_binding
                and state.manual_resume_binding_bound_to_current_run
                and not state.manual_resume_binding_name_only_checked
            )
        )
        and state.pm_startup_intake_node_package_decision_recorded
        and state.startup_pm_capability_resolution_recorded
        and state.pm_startup_intake_released_to_route
    )


def _terminal_continuation_reconciled(state: State) -> bool:
    if _manual_resume_binding_configured(state):
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
        and _runtime_roles_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.child_skill_route_design_discovery_started
        and state.child_skill_initial_gate_manifest_extracted
        and state.child_skill_gate_approvers_assigned
        and state.child_skill_manifest_independent_validation_done
        and state.child_skill_manifest_reviewer_reviewed
        and state.child_skill_manifest_pm_approved_for_route
        and _continuation_ready(state)
        and state.flowguard_process_design_done
        and state.flowguard_operator_model_adversarial_probe_done
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
        and _runtime_role_binding_startup_resolved(state)
        and _startup_intake_release_ready(state)
        and state.work_beyond_startup_allowed
        and state.issue == "none"
        and state.high_risk_gate != "pending"
        and state.chunk_state == "none"
    )


class FlowPilotControlStep:
    name = "FlowPilotControlStep"
    reads = (
        "status",
        "flowpilot_enabled",
        "startup_intake_ui_completed",
        "startup_intake_result_recorded",
        "startup_banner_emitted",
        "startup_background_collaboration_ack_recorded",
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
        "ordinary_resource_discovery_child_registered",
        "ordinary_resource_discovery_child_passed",
        "ordinary_resource_discovery_evidence_current",
        "control_plane_resource_boundedness_child_registered",
        "control_plane_resource_boundedness_child_passed",
        "control_plane_resource_boundedness_evidence_current",
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
        "product_architecture_flowguard_operator_adversarial_probe_done",
        "product_function_architecture_flowguard_operator_product_scope_approved",
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
        "role_binding_policy_written",
        "role_binding_count",
        "project_manager_ready",
        "reviewer_ready",
        "flowguard_operator_route_scope_ready",
        "flowguard_operator_product_scope_ready",
        "worker_ready",
        "role_binding_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "flowguard_operator_owned_async_modeling_policy_recorded",
        "flowguard_operator_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "role_binding_memory_policy_written",
        "role_binding_memory_packets_written",
        "controller_core_loaded",
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_pm_approved_for_route",
        "resume_loaded_state",
        "resume_loaded_frontier",
        "resume_loaded_packet_ledger",
        "resume_loaded_role_binding_memory",
        "resume_host_rehydrate_requested",
        "resume_restored_runtime_roles",
        "resume_rehydrated_runtime_roles",
        "resume_injected_current_run_memory_into_roles",
        "role_binding_recovery_report_written",
        "replacement_roles_seeded_from_memory",
        "resume_pm_decision_requested",
        "resume_pm_controller_reminder_checked",
        "resume_reviewer_dispatch_policy_checked",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_node_decision_recorded",
        "role_binding_ledger_archived",
        "role_binding_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "manual_resume_binding_supported",
        "manual_resume_boundary_recorded",
        "manual_resume_binding_configured",
        "manual_resume_binding_interval_seconds",
        "stable_manual_resume_launcher_recorded",
        "manual_resume_binding_health_checked",
        "background_collaboration_start_decision_recorded",
        "runtime_role_bindings_opened",
        "runtime_role_bindings_current_task_ready",
        "role_bindings_opened_after_startup_answers",
        "role_bindings_opened_after_route_allocation",
        "historical_agent_ids_compared",
        "reused_historical_agent_ids",
        "startup_runtime_mechanical_audit_written",
        "startup_runtime_mechanical_blocking_findings",
        "startup_runtime_mechanical_evidence_checked",
        "startup_runtime_checked_run_identity",
        "startup_runtime_checked_prior_work_boundary",
        "startup_runtime_checked_role_binding_freshness",
        "startup_runtime_checked_no_historical_agent_reuse",
        "pm_returned_startup_blockers",
        "startup_worker_remediation_completed",
        "pm_startup_intake_node_package_decision_recorded",
        "pm_startup_intake_released_to_route",
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
        "flowguard_operator_model_adversarial_probe_done",
        "candidate_route_tree_generated",
        "recursive_route_decomposition_policy_written",
        "route_leaf_readiness_gates_defined",
        "route_reviewer_depth_review_required",
        "router_leaf_only_dispatch_policy_checked",
        "root_route_model_checked",
        "root_route_model_flowguard_operator_route_scope_approved",
        "root_product_function_model_checked",
        "root_product_function_model_flowguard_operator_product_scope_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_flowguard_operator_product_scope_approved",
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
        "node_product_function_model_flowguard_operator_product_scope_approved",
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
        "pm_package_result_disposition_recorded",
        "pm_package_result_disposition_absorbed",
        "pm_formal_gate_package_released",
        "pm_formal_gate_package_identity_recorded",
        "pm_review_release_order_written",
        "pm_released_reviewer_for_current_gate",
        "packet_runtime_physical_files_written",
        "controller_context_body_exclusion_verified",
        "current_assignment_audit_done",
        "recipient_pre_open_current_assignment_check_done",
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
        "inspection_issue_interrogated",
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
        "composite_issue_interrogated",
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
        "sidecar_role_pool_exists",
        "sidecar_role_idle_available",
        "sidecar_role_scope_checked",
        "sidecar_role_status",
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
        "final_product_model_flowguard_operator_adversarial_probe_done",
        "final_product_function_model_flowguard_operator_product_scope_approved",
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
        "startup_intake_ui_completed",
        "startup_intake_result_recorded",
        "startup_banner_emitted",
        "startup_background_collaboration_ack_recorded",
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
        "ordinary_resource_discovery_child_registered",
        "ordinary_resource_discovery_child_passed",
        "ordinary_resource_discovery_evidence_current",
        "control_plane_resource_boundedness_child_registered",
        "control_plane_resource_boundedness_child_passed",
        "control_plane_resource_boundedness_evidence_current",
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
        "product_architecture_flowguard_operator_adversarial_probe_done",
        "product_function_architecture_flowguard_operator_product_scope_approved",
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
        "role_binding_policy_written",
        "role_binding_count",
        "project_manager_ready",
        "reviewer_ready",
        "flowguard_operator_route_scope_ready",
        "flowguard_operator_product_scope_ready",
        "worker_ready",
        "role_binding_ledger_written",
        "role_identity_protocol_recorded",
        "pm_flowguard_delegation_policy_recorded",
        "flowguard_operator_owned_async_modeling_policy_recorded",
        "flowguard_operator_model_report_provenance_policy_recorded",
        "controller_coordination_boundary_recorded",
        "independent_approval_protocol_recorded",
        "pm_initial_route_decision_recorded",
        "child_skill_route_design_discovery_started",
        "child_skill_initial_gate_manifest_extracted",
        "child_skill_gate_approvers_assigned",
        "child_skill_manifest_independent_validation_done",
        "child_skill_manifest_reviewer_reviewed",
        "child_skill_manifest_pm_approved_for_route",
        "resume_loaded_state",
        "resume_loaded_frontier",
        "resume_loaded_packet_ledger",
        "resume_loaded_role_binding_memory",
        "resume_host_rehydrate_requested",
        "resume_restored_runtime_roles",
        "resume_rehydrated_runtime_roles",
        "resume_injected_current_run_memory_into_roles",
        "role_binding_recovery_report_written",
        "replacement_roles_seeded_from_memory",
        "resume_pm_decision_requested",
        "resume_pm_controller_reminder_checked",
        "resume_reviewer_dispatch_policy_checked",
        "pm_resume_decision_recorded",
        "pm_completion_runway_recorded",
        "pm_runway_hard_stops_recorded",
        "pm_runway_checkpoint_cadence_recorded",
        "pm_runway_synced_to_plan",
        "pm_node_decision_recorded",
        "role_binding_ledger_archived",
        "role_binding_memory_archived",
        "continuation_probe_done",
        "continuation_host_kind_recorded",
        "continuation_evidence_written",
        "manual_resume_binding_supported",
        "manual_resume_boundary_recorded",
        "foreground_control_loop_active",
        "manual_resume_binding_configured",
        "manual_resume_binding_interval_seconds",
        "stable_manual_resume_launcher_recorded",
        "manual_resume_binding_health_checked",
        "background_collaboration_start_decision_recorded",
        "runtime_role_bindings_opened",
        "runtime_role_bindings_current_task_ready",
        "role_bindings_opened_after_startup_answers",
        "role_bindings_opened_after_route_allocation",
        "historical_agent_ids_compared",
        "reused_historical_agent_ids",
        "startup_runtime_mechanical_audit_written",
        "startup_runtime_mechanical_blocking_findings",
        "startup_runtime_mechanical_evidence_checked",
        "startup_runtime_checked_run_identity",
        "startup_runtime_checked_prior_work_boundary",
        "startup_runtime_checked_role_binding_freshness",
        "startup_runtime_checked_no_historical_agent_reuse",
        "pm_returned_startup_blockers",
        "startup_worker_remediation_completed",
        "pm_startup_intake_node_package_decision_recorded",
        "pm_startup_intake_released_to_route",
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
        "flowguard_operator_model_adversarial_probe_done",
        "candidate_route_tree_generated",
        "root_route_model_checked",
        "root_route_model_flowguard_operator_route_scope_approved",
        "root_product_function_model_checked",
        "root_product_function_model_flowguard_operator_product_scope_approved",
        "strict_gate_obligation_review_model_checked",
        "parent_subtree_review_checked",
        "parent_product_function_model_checked",
        "parent_product_function_model_flowguard_operator_product_scope_approved",
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
        "node_product_function_model_flowguard_operator_product_scope_approved",
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
        "pm_package_result_disposition_recorded",
        "pm_package_result_disposition_absorbed",
        "pm_formal_gate_package_released",
        "pm_formal_gate_package_identity_recorded",
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
        "inspection_issue_interrogated",
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
        "composite_issue_interrogated",
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
        "sidecar_role_pool_exists",
        "sidecar_role_idle_available",
        "sidecar_role_scope_checked",
        "sidecar_role_status",
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
        "final_product_model_flowguard_operator_adversarial_probe_done",
        "final_product_function_model_flowguard_operator_product_scope_approved",
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
        "resume_decision_records",
    )
    accepted_input_type = Tick
    input_description = "one continuation/FlowPilot control decision"
    output_description = "next allowed control action"
    idempotency = (
        "Repeated manual resume binding decisions do not lower the frozen contract, do not "
        "complete early, and must either advance, recover, update the model, or block."
    )

    def _apply_startup_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_startup_phase import apply_startup_phase
        else:
            from meta_model_startup_phase import apply_startup_phase

        yield from apply_startup_phase(self, state)


    def _apply_resource_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_resource_phase import apply_resource_phase
        else:
            from meta_model_resource_phase import apply_resource_phase

        yield from apply_resource_phase(self, state)


    def _apply_route_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_route_phase import apply_route_phase
        else:
            from meta_model_route_phase import apply_route_phase

        yield from apply_route_phase(self, state)


    def _apply_repair_mutation_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_repair_mutation_phase import apply_repair_mutation_phase
        else:
            from meta_model_repair_mutation_phase import apply_repair_mutation_phase

        yield from apply_repair_mutation_phase(self, state)


    def _apply_closure_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_closure_phase import apply_closure_phase
        else:
            from meta_model_closure_phase import apply_closure_phase

        yield from apply_closure_phase(self, state)


    def _apply_node_execution_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_node_execution_phase import apply_node_execution_phase
        else:
            from meta_model_node_execution_phase import apply_node_execution_phase

        yield from apply_node_execution_phase(self, state)


    def _apply_terminal_blocker_phase(self, state: State) -> Iterable[FunctionResult]:
        if __package__:
            from .meta_model_terminal_blocker_phase import apply_terminal_blocker_phase
        else:
            from meta_model_terminal_blocker_phase import apply_terminal_blocker_phase

        yield from apply_terminal_blocker_phase(self, state)


    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj

        if state.status in {"blocked", "complete"}:
            return

        yield from self._apply_startup_phase(state)
        yield from self._apply_resource_phase(state)
        yield from self._apply_route_phase(state)
        yield from self._apply_repair_mutation_phase(state)
        yield from self._apply_closure_phase(state)
        yield from self._apply_node_execution_phase(state)
        yield from self._apply_terminal_blocker_phase(state)


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
        return InvariantResult.fail("final report emitted before the native startup intake options were answered")
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
            "final report emitted before startup self-interrogation seeded the improvement candidate pool and validation direction"
        )
    if not _root_self_interrogation_gate_ready(state):
        return InvariantResult.fail(
            "final report emitted before startup and product-architecture self-interrogation records were durably dispositioned"
        )
    if not _product_function_architecture_ready(state):
        return InvariantResult.fail(
            "final report emitted before PM-owned product-function architecture, FlowGuard operator product-function approval, and reviewer challenge"
        )
    if not (state.dependency_plan_recorded and state.future_installs_deferred):
        return InvariantResult.fail("final report emitted before demand-driven dependency plan was recorded")
    if not state.contract_frozen:
        return InvariantResult.fail("final report emitted before contract was frozen")
    if not (
        _runtime_roles_ready(state)
        and state.pm_initial_route_decision_recorded
        and state.role_binding_ledger_archived
    ):
        return InvariantResult.fail(
            "final report emitted before runtime role-binding ledger, PM route decision, and terminal role archive"
        )
    if not (state.foreground_control_loop_active or state.status == "complete"):
        return InvariantResult.fail("final report emitted without manual resume binding continuity")
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
        and state.root_route_model_flowguard_operator_route_scope_approved
        and state.root_product_function_model_flowguard_operator_product_scope_approved
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
        return InvariantResult.fail(
            "final report emitted before PM released startup intake from the runtime mechanical audit"
        )
    if not (
        state.completion_self_interrogation_done
        and state.high_value_work_review == "exhausted"
    ):
        return InvariantResult.fail("final report emitted before completion self-interrogation exhausted obvious high-value work")
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


def core_deliverable_non_downgrade_gates_required(
    state: State, trace
) -> InvariantResult:
    del trace
    route_or_later = (
        state.flowguard_process_design_done
        or state.node_acceptance_plan_written
        or state.final_route_wide_gate_ledger_pm_built
        or state.pm_completion_decision_recorded
        or state.final_report_emitted
        or state.status == "complete"
    )
    if route_or_later and not (
        state.product_function_target_and_failure_bar_written
        and state.product_function_semantic_fidelity_policy_written
        and state.product_function_acceptance_matrix_written
        and state.root_acceptance_thresholds_defined
        and state.root_acceptance_proof_matrix_written
    ):
        return InvariantResult.fail(
            "core deliverable non-downgrade gates were missing product target/failure bar, semantic fidelity, acceptance matrix, or root proof matrix"
        )

    terminal_or_later = (
        state.final_route_wide_gate_ledger_pm_completion_approved
        or state.pm_completion_decision_recorded
        or state.final_report_emitted
        or state.status == "complete"
    )
    if terminal_or_later and not (
        state.final_feature_matrix_review_done
        and state.final_acceptance_matrix_review_done
        and state.final_product_function_model_replayed
        and state.final_human_inspection_passed
        and _final_route_wide_gate_ledger_ready(state)
        and state.terminal_human_backward_replay_started_from_delivered_product
    ):
        return InvariantResult.fail(
            "core deliverable non-downgrade terminal gates were missing final acceptance review, product-model replay, delivered-output backward replay, or the route-wide gate ledger"
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
        not state.startup_intake_result_recorded
        and (
            state.startup_background_collaboration_ack_recorded
            or state.startup_display_entry_action_done
            or state.startup_banner_emitted
        )
    ):
        return InvariantResult.fail("startup continued after asking questions without stopping for the user's reply")
    if state.startup_banner_emitted and not _startup_questions_complete(state):
        return InvariantResult.fail("startup banner emitted before startup intake background collaboration acknowledgement was recorded")
    if state.startup_banner_emitted and not state.startup_banner_user_dialog_confirmed:
        return InvariantResult.fail("startup banner emitted without confirmed user-dialog display")
    if state.startup_banner_emitted and not state.controller_core_loaded:
        return InvariantResult.fail("startup banner emitted before Controller core was loaded")
    if state.startup_background_collaboration_ack_recorded and not (
        state.startup_answer_values_valid
        and state.startup_answer_provenance == "explicit_user_reply"
    ):
        return InvariantResult.fail("startup background collaboration authorization was recorded without legal values and explicit_user_reply provenance")
    if state.stale_top_level_bootstrap_reused:
        return InvariantResult.fail("stale top-level bootstrap was reused as current startup state")
    if state.old_control_state_reused_as_current:
        return InvariantResult.fail("old FlowPilot control state was reused as the current run state")
    if (state.contract_frozen or state.route_version > 0 or state.work_beyond_startup_allowed) and not _run_isolation_ready(state):
        return InvariantResult.fail("FlowPilot advanced before a fresh current run directory and control-state boundary were established")
    if (state.contract_frozen or state.route_version > 0 or state.work_beyond_startup_allowed) and not state.startup_display_entry_action_done:
        return InvariantResult.fail("FlowPilot advanced before recording the fixed startup display surface default")
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
        _runtime_roles_ready(state)
        and _run_isolation_ready(state)
        and state.pm_initial_route_decision_recorded
        and _product_function_architecture_ready(state)
        and state.contract_frozen
        and state.dependency_plan_recorded
        and state.future_installs_deferred
        and _continuation_lifecycle_valid(state)
    ):
        return InvariantResult.fail(
            "route version created before runtime role-binding authority, fresh run isolation, PM route decision, product-function architecture, frozen contract, dependency plan, and host continuation decision"
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
            "formal execution started before PM released startup intake from the runtime mechanical audit"
        )
    if state.execution_frontier_written and not state.router_leaf_only_dispatch_policy_checked:
        return InvariantResult.fail(
            "execution frontier was written without verifying Router leaf-only dispatch and parent/module review routing"
        )
    if state.user_flow_diagram_refreshed and not state.user_flow_diagram_shallow_projection_policy_recorded:
        return InvariantResult.fail(
            "user route diagram refreshed before shallow projection, active path, and hidden leaf progress policy was recorded"
        )
    if state.startup_runtime_mechanical_audit_written and not state.startup_runtime_mechanical_evidence_checked:
        return InvariantResult.fail(
            "startup runtime mechanical audit was written without checking current sealed intake, paths, hashes, display status, and current run evidence"
        )
    if state.startup_runtime_mechanical_audit_written and not (
        state.startup_runtime_checked_run_identity
        and state.startup_runtime_checked_prior_work_boundary
    ):
        return InvariantResult.fail(
            "startup runtime mechanical audit was written without checking current run identity and prior-work import boundary"
        )
    if (
        state.startup_runtime_mechanical_audit_written
        and state.runtime_role_bindings_opened
        and not (
            state.startup_runtime_checked_role_binding_freshness
            and state.startup_runtime_checked_no_historical_agent_reuse
        )
    ):
        return InvariantResult.fail(
            "startup runtime mechanical audit counted live role bindings without checking requested-responsibility freshness and historical id reuse"
        )
    if state.pm_startup_intake_released_to_route and not (
        state.startup_runtime_mechanical_audit_written
        and not state.startup_runtime_mechanical_blocking_findings
        and state.startup_runtime_mechanical_evidence_checked
        and _run_isolation_ready(state)
        and state.startup_runtime_checked_run_identity
        and state.startup_runtime_checked_prior_work_boundary
        and state.startup_runtime_checked_role_binding_freshness
        and state.startup_runtime_checked_no_historical_agent_reuse
        and state.startup_runtime_checked_capability_resolution
        and (
            state.manual_resume_boundary_recorded
            or (
                state.startup_pm_checked_manual_resume_binding
                and state.manual_resume_binding_bound_to_current_run
                and not state.manual_resume_binding_name_only_checked
            )
        )
        and state.pm_startup_intake_node_package_decision_recorded
        and state.startup_pm_capability_resolution_recorded
    ):
        return InvariantResult.fail(
            "PM released startup intake to route work before a clean runtime mechanical audit and PM node/work-package decision"
        )
    if state.pm_startup_intake_released_to_route and state.pm_returned_startup_blockers:
        return InvariantResult.fail(
            "PM released startup intake while startup mechanical blockers were still assigned for worker remediation"
        )
    if (
        state.startup_worker_remediation_completed
        and state.pm_startup_intake_released_to_route
        and not (
            state.startup_runtime_mechanical_audit_written
            and not state.startup_runtime_mechanical_blocking_findings
            and state.startup_runtime_mechanical_evidence_checked
        )
    ):
        return InvariantResult.fail(
            "startup worker remediation was not rechecked by runtime mechanics before PM intake release"
        )
    if state.work_beyond_startup_allowed and not _startup_questions_complete(state):
        return InvariantResult.fail(
            "PM allowed work beyond startup before the three startup answers were recorded"
        )
    if state.work_beyond_startup_allowed and not _run_isolation_ready(state):
        return InvariantResult.fail(
            "PM allowed work beyond startup before fresh run isolation and prior-work boundary were resolved"
        )
    if state.work_beyond_startup_allowed and not _runtime_role_binding_startup_resolved(state):
        return InvariantResult.fail(
            "PM allowed work beyond startup before fresh current-task role bindings were resolved or the run was blocked"
        )
    if state.work_beyond_startup_allowed and state.reused_historical_agent_ids:
        return InvariantResult.fail(
            "PM allowed work beyond startup while role-binding evidence reused historical agent ids"
        )
    if state.work_beyond_startup_allowed and not _startup_intake_release_ready(state):
        return InvariantResult.fail(
            "work beyond startup was allowed before runtime mechanical audit and PM-owned startup intake release"
        )
    if state.manual_resume_binding_configured and (
        not state.manual_resume_binding_bound_to_current_run or state.manual_resume_binding_name_only_checked
    ):
        return InvariantResult.fail(
            "startup manual resume binding evidence did not bind the automation to the current run instead of a same-name record"
        )
    return InvariantResult.pass_()


def continuation_control_loop_until_terminal(state: State, trace) -> InvariantResult:
    del trace
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"} and not state.manual_resume_binding_health_checked:
        return InvariantResult.fail("formal chunk started before continuation readiness check")
    if state.status == "running" and not state.foreground_control_loop_active:
        return InvariantResult.fail("FlowPilot control loop inactive while task is running")
    if state.status in {"blocked", "complete"} and state.foreground_control_loop_active:
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
            state.resume_loaded_state
            and state.resume_loaded_frontier
            and state.resume_loaded_packet_ledger
            and state.resume_loaded_role_binding_memory
            and state.resume_host_rehydrate_requested
            and state.resume_restored_runtime_roles
            and state.resume_rehydrated_runtime_roles
            and state.resume_injected_current_run_memory_into_roles
            and state.role_binding_recovery_report_written
            and state.replacement_roles_seeded_from_memory
            and state.resume_pm_decision_requested
            and state.resume_pm_controller_reminder_checked
            and state.resume_reviewer_dispatch_policy_checked
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
                "chunk started before resume loaded packet ledger, rehydrated roles, checked PM controller reminder/router direct-dispatch policy, and synced a sufficiently deep PM runway"
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
            return InvariantResult.fail("chunk started before focused parent-scope self-interrogation")
        if not _focused_interrogation_ready(
            total_questions=state.parent_focused_interrogation_questions,
            scope_id=state.parent_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before parent focused self-interrogation had 20-50 questions and a scope id"
            )
        if not state.parent_subtree_review_checked:
            return InvariantResult.fail("chunk started before parent-subtree FlowGuard review")
        if not state.parent_product_function_model_checked:
            return InvariantResult.fail("chunk started before parent product-function model check")
        if not state.node_focused_interrogation_done:
            return InvariantResult.fail("chunk started before focused node-level self-interrogation")
        if not _focused_interrogation_ready(
            total_questions=state.node_focused_interrogation_questions,
            scope_id=state.node_focused_interrogation_scope_id,
        ):
            return InvariantResult.fail(
                "chunk started before node focused self-interrogation had 20-50 questions and a scope id"
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
            return InvariantResult.fail("chunk started before lightweight foreground-duty self-check")
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
        and (explicit_pm_release_ready or disposition_pm_release_ready)
        and state.packet_runtime_physical_files_written
        and state.controller_context_body_exclusion_verified
        and state.current_assignment_audit_done
        and state.recipient_pre_open_current_assignment_check_done
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
            "human-like reviewer started current-node review before PM release evidence, physical packet isolation, controller mail-chain audit, envelope/body audit, and per-packet role-origin audit"
        )
    if state.pm_review_release_order_written and not state.worker_output_ready_for_review:
        return InvariantResult.fail(
            "PM wrote a current-gate review release before worker output was ready"
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


def sidecar_role_must_merge_before_completion(state: State, trace) -> InvariantResult:
    del trace
    if state.final_report_emitted and state.sidecar_role_status in {"pending", "returned"}:
        return InvariantResult.fail("completed while sidecar role work was not merged")
    if state.chunk_state in {"ready", "executed", "verified", "checkpoint_pending"}:
        if state.sidecar_role_status in {"pending", "returned"}:
            return InvariantResult.fail("formal chunk active while sidecar work was not merged")
    if state.sidecar_role_status in {"pending", "returned"}:
        if not state.child_node_sidecar_scan_done:
            return InvariantResult.fail("sidecar role used before child-node sidecar scan")
    if state.sidecar_role_status == "pending" and not state.sidecar_role_scope_checked:
        return InvariantResult.fail("sidecar role binding assigned before bounded/disjoint scope check")
    if state.sidecar_role_status == "pending" and state.sidecar_need != "needed":
        return InvariantResult.fail("sidecar role assigned without a bounded sidecar need")
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


def stable_manual_resume_binding_not_route_state(state: State, trace) -> InvariantResult:
    del trace
    if (
        state.route_version > 1
        and state.manual_resume_binding_supported
        and not state.stable_manual_resume_launcher_recorded
    ):
        return InvariantResult.fail("route changed without a stable manual resume binding launcher that reads persisted state")
    if (
        state.route_version > 1
        and state.manual_resume_boundary_recorded
        and state.stable_manual_resume_launcher_recorded
    ):
        return InvariantResult.fail("manual-resume route unexpectedly created a stable manual resume binding launcher")
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
    startup_or_route_work_started = (
        state.startup_runtime_mechanical_audit_written
        or state.pm_startup_intake_released_to_route
        or state.work_beyond_startup_allowed
        or state.route_checked
        or state.chunk_state != "none"
        or state.final_report_emitted
    )
    if startup_or_route_work_started and not _continuation_ready(state):
        return InvariantResult.fail(
            "startup mechanical audit or route work started before continuation was bound to manual resume binding or manual resume"
        )
    if startup_or_route_work_started and state.manual_resume_binding_supported and not _manual_resume_binding_configured(state):
        return InvariantResult.fail(
            "startup mechanical audit or route work started before current manual resume binding was fully configured"
        )
    if startup_or_route_work_started and state.manual_resume_boundary_recorded and state.manual_resume_binding_configured:
        return InvariantResult.fail(
            "startup mechanical audit or route work started after manual-resume startup that still created manual resume binding"
        )
    return InvariantResult.pass_()


def manual_resume_binding_continuation_is_lifecycle_state(state: State, trace) -> InvariantResult:
    del trace
    automation_bits = (
        state.manual_resume_binding_configured
        or state.manual_resume_binding_interval_seconds != 0
        or state.stable_manual_resume_launcher_recorded
    )
    if state.manual_resume_boundary_recorded and automation_bits:
        return InvariantResult.fail(
            "manual-resume mode recorded but manual resume binding state was still created"
        )
    formal_started = (
        state.route_checked
        or state.chunk_state != "none"
        or state.final_report_emitted
    )
    if formal_started and state.manual_resume_binding_supported and (
        state.manual_resume_binding_configured
        or state.manual_resume_binding_interval_seconds != 0
    ) and not _continuation_lifecycle_valid(state):
        return InvariantResult.fail(
            "host continuation support produced a partial manual resume binding setup"
        )
    if state.manual_resume_binding_supported and state.manual_resume_binding_configured and (
        state.manual_resume_binding_interval_seconds != 1
        or not state.stable_manual_resume_launcher_recorded
        or not state.manual_resume_binding_bound_to_current_run
        or state.manual_resume_binding_name_only_checked
    ):
        return InvariantResult.fail(
            "automated continuation must use a stable one-minute manual resume binding launcher bound to the current run"
        )
    return InvariantResult.pass_()


def ordinary_resource_discovery_child_before_pm_route_design(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.ordinary_resource_discovery_child_passed
        and not state.ordinary_resource_discovery_child_registered
    ):
        return InvariantResult.fail(
            "ordinary-resource-discovery child passed without current parent registration"
        )
    if (
        state.ordinary_resource_discovery_evidence_current
        and not state.ordinary_resource_discovery_child_passed
    ):
        return InvariantResult.fail(
            "ordinary-resource-discovery evidence was marked current before the child passed"
        )
    if (
        state.product_function_architecture_pm_synthesized
        or state.pm_initial_route_decision_recorded
    ) and not _ordinary_resource_discovery_child_ready(state):
        return InvariantResult.fail(
            "PM route design advanced without the current ordinary-resource-discovery child result"
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
        and _ordinary_resource_discovery_child_ready(state)
    ):
        return InvariantResult.fail(
            "PM child-skill selection decisions were recorded before the PM manifest, minimum sufficient complexity review, product capability map, and current PM-selected local-skill discovery evidence"
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
        or state.product_function_architecture_flowguard_operator_product_scope_approved
        or state.product_function_architecture_reviewer_challenged
        or state.child_skill_manifest_reviewer_reviewed
        or state.child_skill_manifest_flowguard_operator_route_scope_approved
        or state.child_skill_manifest_flowguard_operator_product_scope_approved
        or state.child_skill_manifest_pm_approved_for_route
        or state.root_route_model_flowguard_operator_route_scope_approved
        or state.root_product_function_model_flowguard_operator_product_scope_approved
        or state.parent_product_function_model_flowguard_operator_product_scope_approved
        or state.node_product_function_model_flowguard_operator_product_scope_approved
        or state.node_human_review_reviewer_approved
        or state.composite_backward_review_reviewer_approved
        or state.final_product_function_model_flowguard_operator_product_scope_approved
        or state.final_human_review_reviewer_approved
        or state.final_route_wide_gate_ledger_pm_completion_approved
        or state.pm_startup_intake_released_to_route
    )
    if any_role_approval and not state.independent_approval_protocol_recorded:
        return InvariantResult.fail(
            "role approval was recorded before the independent adversarial approval protocol existed"
        )
    if state.startup_self_interrogation_pm_ratified and not _runtime_roles_ready(state):
        return InvariantResult.fail(
            "startup self-interrogation was ratified before runtime role-binding authority was ready"
        )
    if state.product_function_architecture_pm_synthesized and not (
        _runtime_roles_ready(state) and _ordinary_resource_discovery_child_ready(state)
    ):
        return InvariantResult.fail(
            "PM product-function architecture was synthesized before role binding recovery and current ordinary-resource-discovery child evidence"
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
        state.product_function_architecture_flowguard_operator_product_scope_approved
        and not product_architecture_inputs_ready
    ):
        return InvariantResult.fail(
            "product-function architecture approval was recorded before all PM product artifacts existed"
        )
    if (
        state.product_function_architecture_flowguard_operator_product_scope_approved
        and not state.product_architecture_flowguard_operator_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "product-scope FlowGuard operator approved product-function architecture before adversarial modelability and failure-path probe"
        )
    if state.product_function_architecture_reviewer_challenged and not (
        state.product_function_architecture_flowguard_operator_product_scope_approved
        and state.product_architecture_reviewer_adversarial_probe_done
    ):
        return InvariantResult.fail(
            "human-like reviewer challenged the product-function architecture before FlowGuard operator product-function approval, reviewer recovery, or independent adversarial probe"
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
        state.root_route_model_flowguard_operator_route_scope_approved
        or state.root_product_function_model_flowguard_operator_product_scope_approved
        or state.parent_product_function_model_flowguard_operator_product_scope_approved
        or state.node_product_function_model_flowguard_operator_product_scope_approved
    ) and not state.flowguard_operator_model_adversarial_probe_done:
        return InvariantResult.fail(
            "FlowGuard operator model approval was recorded before adversarial model probe evidence"
        )
    if (
        state.root_route_model_flowguard_operator_route_scope_approved
        or state.root_product_function_model_flowguard_operator_product_scope_approved
        or state.parent_product_function_model_flowguard_operator_product_scope_approved
        or state.node_product_function_model_flowguard_operator_product_scope_approved
    ) and not (
        state.flowguard_model_report_risk_tiers_done
        and state.flowguard_model_report_pm_review_agenda_done
        and state.flowguard_model_report_toolchain_recommendations_done
        and state.flowguard_model_report_confidence_boundary_done
    ):
        return InvariantResult.fail(
            "FlowGuard operator model approval was recorded before the report extracted PM risk tiers, review agenda, toolchain recommendations, and confidence boundary"
        )
    if state.root_route_model_flowguard_operator_route_scope_approved and not state.root_route_model_checked:
        return InvariantResult.fail("root route approval is stale without a root route model check")
    if state.root_route_model_checked and not state.root_route_model_flowguard_operator_route_scope_approved:
        return InvariantResult.fail("root route model check lacks FlowGuard operator process-model approval")
    if (
        state.root_product_function_model_flowguard_operator_product_scope_approved
        and not state.root_product_function_model_checked
    ):
        return InvariantResult.fail(
            "root product-function approval is stale without a root product-function model check"
        )
    if (
        state.root_product_function_model_checked
        and not state.root_product_function_model_flowguard_operator_product_scope_approved
    ):
        return InvariantResult.fail(
            "root product-function model check lacks FlowGuard operator product-function approval"
        )
    if (
        state.parent_product_function_model_flowguard_operator_product_scope_approved
        and not state.parent_product_function_model_checked
    ):
        return InvariantResult.fail(
            "parent product-function approval is stale without a parent product-function model check"
        )
    if (
        state.parent_product_function_model_checked
        and not state.parent_product_function_model_flowguard_operator_product_scope_approved
    ):
        return InvariantResult.fail(
            "parent product-function model check lacks FlowGuard operator product-function approval"
        )
    if (
        state.node_product_function_model_flowguard_operator_product_scope_approved
        and not state.node_product_function_model_checked
    ):
        return InvariantResult.fail(
            "node product-function approval is stale without a node product-function model check"
        )
    if (
        state.node_product_function_model_checked
        and not state.node_product_function_model_flowguard_operator_product_scope_approved
    ):
        return InvariantResult.fail(
            "node product-function model check lacks FlowGuard operator product-function approval"
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
        state.final_product_function_model_flowguard_operator_product_scope_approved
        and not (
            state.final_product_function_model_replayed
            and state.final_product_model_flowguard_operator_adversarial_probe_done
        )
    ):
        return InvariantResult.fail(
            "final product-function approval is stale without final product replay and adversarial FlowGuard operator probe"
        )
    if (
        state.final_product_function_model_replayed
        and not state.final_product_function_model_flowguard_operator_product_scope_approved
    ):
        return InvariantResult.fail(
            "final product-function replay lacks FlowGuard operator product-function approval"
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
    if state.pm_completion_decision_recorded and not state.role_binding_ledger_archived:
        return InvariantResult.fail("PM completion decision recorded before role binding archive")
    if state.final_report_emitted and not state.pm_completion_decision_recorded:
        return InvariantResult.fail("final report emitted before PM completion approval")
    return InvariantResult.pass_()


def control_plane_resource_boundedness_child_before_pm_route_design(
    state: State, trace
) -> InvariantResult:
    del trace
    if (
        state.control_plane_resource_boundedness_child_passed
        and not state.control_plane_resource_boundedness_child_registered
    ):
        return InvariantResult.fail(
            "control-plane resource-boundedness child passed without parent registration"
        )
    if (
        state.control_plane_resource_boundedness_evidence_current
        and not state.control_plane_resource_boundedness_child_passed
    ):
        return InvariantResult.fail(
            "control-plane resource-boundedness evidence became current before the child passed"
        )
    if (
        state.product_function_architecture_pm_synthesized
        or state.pm_initial_route_decision_recorded
    ) and not _control_plane_resource_boundedness_child_ready(state):
        return InvariantResult.fail(
            "PM route design advanced without current control-plane resource-boundedness evidence"
        )
    return InvariantResult.pass_()


def role_binding_memory_rehydration_required(state: State, trace) -> InvariantResult:
    del trace
    if state.startup_self_interrogation_pm_ratified and not (
        state.role_binding_memory_policy_written
        and state.role_binding_memory_packets_written >= MIN_CURRENT_BACKGROUND_AGENT_COUNT
    ):
        return InvariantResult.fail("startup was ratified before current background-collaboration memory policy was written")
    if state.resume_pm_decision_requested and not state.terminal_router_daemon_stopped and not (
        state.resume_loaded_state
        and state.resume_loaded_frontier
        and state.resume_loaded_packet_ledger
        and state.router_daemon_recovered_on_resume
        and state.router_daemon_started
        and state.controller_action_watch_active
        and state.resume_loaded_role_binding_memory
        and state.resume_host_rehydrate_requested
        and state.resume_restored_runtime_roles
        and state.resume_rehydrated_runtime_roles
        and state.resume_injected_current_run_memory_into_roles
        and state.role_binding_recovery_report_written
        and state.replacement_roles_seeded_from_memory
    ):
        return InvariantResult.fail(
            "PM resume was requested before current-run state, packet ledger, live role-binding memory rehydration, and memory injection completed"
        )
    if state.pm_resume_decision_recorded and not (
        state.resume_pm_controller_reminder_checked
        and state.resume_reviewer_dispatch_policy_checked
    ):
        return InvariantResult.fail(
            "PM resume decision was accepted before controller reminder and reviewer-dispatch policy were checked"
        )
    if state.checkpoint_written and state.completed_chunks > 0 and not state.role_memory_refreshed_after_work:
        return InvariantResult.fail("checkpoint written before role memory refresh after meaningful role work")
    if state.role_binding_ledger_archived and not state.role_binding_memory_archived:
        return InvariantResult.fail("role-binding ledger archived before role memory archive")
    if state.status == "complete" and not state.terminal_router_daemon_stopped:
        return InvariantResult.fail("route completed before stopping the persistent Router daemon")
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
        name="core_deliverable_non_downgrade_gates_required",
        description="Completion path preserves the PM source intent through semantic fidelity, root acceptance, final replay, and route-wide ledger gates.",
        predicate=core_deliverable_non_downgrade_gates_required,
    ),
    Invariant(
        name="frozen_contract_never_changes",
        description="Autopilot may update routes and models, but not the frozen acceptance contract.",
        predicate=frozen_contract_never_changes,
    ),
    Invariant(
        name="startup_question_gate_before_heavy_startup",
        description="FlowPilot asks the native startup intake question, stops for answers, and emits the banner only after the user answer and fixed defaults exist.",
        predicate=startup_question_gate_before_heavy_startup,
    ),
    Invariant(
        name="dependency_plan_before_route_or_work",
        description="Route creation and formal work require demand-driven dependency planning first.",
        predicate=dependency_plan_before_route_or_work,
    ),
    Invariant(
        name="continuation_control_loop_until_terminal",
        description="FlowPilot keeps a control loop active while running; real manual resume binding health is required only when automated continuation is supported.",
        predicate=continuation_control_loop_until_terminal,
    ),
    Invariant(
        name="controlled_stop_notice_required",
        description="Controlled nonterminal stops emit a manual-resume or foreground-duty notice, and terminal completion emits a completion notice.",
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
        name="sidecar_role_must_merge_before_completion",
        description="Optional sidecar role results must return to the controller before completion.",
        predicate=sidecar_role_must_merge_before_completion,
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
        name="stable_manual_resume_binding_not_route_state",
        description="Heartbeat automation stays a stable launcher while persisted route/frontier state carries next-jump changes.",
        predicate=stable_manual_resume_binding_not_route_state,
    ),
    Invariant(
        name="startup_continuation_gates_work_beyond_startup",
        description="Startup loads Controller core before Controller-ledger obligations, then establishes manual resume binding or manual-resume continuation before runtime mechanical audit and route work.",
        predicate=startup_continuation_gates_work_beyond_startup,
    ),
    Invariant(
        name="manual_resume_binding_continuation_is_lifecycle_state",
        description="Automated continuation uses only a stable manual resume binding launcher; manual-resume routes must not create manual resume binding.",
        predicate=manual_resume_binding_continuation_is_lifecycle_state,
    ),
    Invariant(
        name="ordinary_resource_discovery_child_before_pm_route_design",
        description="The current focused resource-discovery child proves shallow skill inventory, PM selection, ordinary evidence work, and optional-map behavior before PM route design.",
        predicate=ordinary_resource_discovery_child_before_pm_route_design,
    ),
    Invariant(
        name="control_plane_resource_boundedness_child_before_pm_route_design",
        description="The focused resource-boundedness child proves no-change, idempotency, bounded evidence, and fail-closed retention before PM route design.",
        predicate=control_plane_resource_boundedness_child_before_pm_route_design,
    ),
    Invariant(
        name="actor_authority_gates_require_correct_role",
        description="Authority-sensitive gates require the PM, reviewer, or matching FlowGuard operator and reject stale approvals.",
        predicate=actor_authority_gates_require_correct_role,
    ),
    Invariant(
        name="role_binding_memory_rehydration_required",
        description="Exact current-obligation role recovery uses current-run memory and route delta before PM runway, checkpoint, or terminal archive; idle and historical roles remain audit-only.",
        predicate=role_binding_memory_rehydration_required,
    ),
)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 145


def initial_state() -> State:
    return State()


def build_workflow() -> Workflow:
    return Workflow((FlowPilotControlStep(),), name="flowguard_project_FlowPilot runtime_meta")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple(
        (result.label, result.new_state)
        for result in FlowPilotControlStep().apply(Tick(), state)
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

