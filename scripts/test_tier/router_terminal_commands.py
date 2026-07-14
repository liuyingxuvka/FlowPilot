"""Router terminal, PM role-work, quality, and material commands."""

from __future__ import annotations

from .command_builders import _unittest, _unittest_k

ROUTER_TERMINAL_CORE_COMMANDS = (
    _unittest_k(
        "router_terminal_final_ledger",
        "tests.router_runtime.terminal",
        patterns=(
            "test_final_ledger_records_frozen_contract_replay_source_paths",
            "test_final_ledger_links_explicit_existing_optional_map_without_using_it_as_acceptance_evidence",
            "test_final_ledger_rejects_progress_only_terminal_flowguard_report",
            "test_final_ledger_rejects_dirty_pm_suggestion_ledger",
            "test_final_ledger_rejects_dirty_self_interrogation_index",
            "test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
            "test_final_ledger_requires_pm_accepted_terminal_flowguard_coverage",
        ),
        description="Terminal final-ledger validation slice.",
    ),
    _unittest_k(
        "router_terminal_replay_summary",
        "tests.router_runtime.terminal",
        patterns=(
            "test_reconcile_recovers_prior_terminal_closure_state",
            "test_reconcile_run_recovers_terminal_status_from_current_pointer",
            "test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions",
            "test_terminal_summary_payload_requires_attribution_display_and_run_root_sources",
        ),
        description="Terminal replay, reconciliation, and summary slice.",
    ),
    _unittest_k(
        "router_terminal_node_stop",
        "tests.router_runtime.terminal",
        patterns=(
            "test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress",
            "test_terminal_pending_legacy_heartbeat_action_is_rejected",
            "test_user_stop_writes_immediate_daemon_terminal_fence_and_clears_current_work",
            "test_user_stop_writes_terminal_fence_before_best_effort_scheduler_cleanup",
            "test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work",
            "test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts",
        ),
        description="Terminal node-completion and user-stop slice.",
    ),
    _unittest_k(
        "router_closure_dirty_ledgers",
        "tests.router_runtime.closure",
        patterns=(
            "test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay",
            "test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card",
            "test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay",
        ),
        description="Terminal closure dirty-ledger guard slice.",
    ),
    _unittest_k(
        "router_closure_pm_role_work",
        "tests.router_runtime.closure",
        patterns=(
            "test_flowguard_operator_role_work_writes_authorized_lifecycle_index",
            "test_pm_terminal_closure_uses_file_backed_contract_and_prior_context",
        ),
        description="Terminal closure PM role-work and file-backed contract slice.",
    ),
    _unittest_k(
        "router_resume_reentry",
        "tests.router_runtime.resume",
        patterns=(
            "test_manual_resume_alive_status_enters_router_resume_path",
            "test_load_resume_state_controller_receipt_replays_router_state_handler",
            "test_pm_resume_break_glass_routes_control_blocker_without_resume_success",
            "test_resume_reentry_attaches_to_live_owner_after_delayed_daemon_patrol",
            "test_resume_reentry_attaches_to_live_router_daemon_and_ledger",
            "test_resume_reentry_loads_state_before_resume_cards",
            "test_resume_reentry_marks_dead_daemon_for_restart_after_liveness_check",
            "test_resume_reentry_preempts_active_control_blocker_until_replay_or_pm_decision",
            "test_legacy_heartbeat_resume_event_is_rejected",
        ),
        description="Resume reentry, daemon, liveness, and control-blocker preemption slice.",
    ),
    _unittest_k(
        "router_resume_rehydration",
        "tests.router_runtime.resume",
        patterns=(
            "test_done_rehydrate_receipt_reclaims_existing_current_run_report_before_blocker",
            "test_incomplete_stateful_rehydrate_receipt_becomes_control_blocker",
            "test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
            "test_manual_resume_rehydration_does_not_reissue_missing_obligations_without_role_recovery",
            "test_manual_resume_rehydration_keeps_existing_waits_outside_role_recovery",
        ),
        description="Resume rehydration and ambiguous-state slice.",
    ),
    _unittest_k(
        "router_resume_role_recovery",
        "tests.router_runtime.resume",
        patterns=(
            "test_load_resume_state_does_not_downgrade_existing_role_recovery_report",
            "test_role_recovery_reissues_missing_obligations_in_original_order",
            "test_role_recovery_settles_existing_ack_without_replay_or_pm",
            "test_role_recovery_settles_existing_output_without_replay_or_pm",
            "test_stale_role_recovery_report_is_not_reclaimed_for_new_transaction",
        ),
        description="Resume role-recovery settlement slice.",
    ),
    _unittest_k(
        "router_resume_liveness_faults",
        "tests.router_runtime.resume",
        patterns=(
            "test_active_agent_lookup_rejects_unaddressable_recovered_binding",
            "test_blocked_role_recovery_receipt_reclaims_existing_report",
            "test_no_output_event_reissues_same_work_not_recovery",
            "test_mid_run_role_liveness_fault_uses_unified_recovery_before_normal_work",
            "test_role_no_output_escalates_to_pm_after_two_reissues",
            "test_role_no_output_report_reissues_same_work_before_role_recovery",
        ),
        description="Resume liveness-fault and no-output recovery slice.",
    ),
    _unittest_k(
        "router_control_blockers_recorded_events",
        "tests.router_runtime.control_blockers",
        patterns=(
            "test_already_recorded_event_can_resolve_delivered_control_blocker",
            "test_already_recorded_event_does_not_resolve_pm_required_control_blocker",
            "test_already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision",
        ),
        description="Control-blocker already-recorded event resolution slice.",
    ),
    _unittest_k(
        "router_control_blockers_reissue_retry",
        "tests.router_runtime.control_blockers",
        patterns=(
            "test_control_plane_reissue_retry_budget_escalates_to_pm",
            "test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue",
            "test_pm_semantic_control_blocker_zero_retry_budget_is_exhausted",
        ),
        description="Control-blocker reissue and retry-budget slice.",
    ),
    _unittest_k(
        "router_control_blockers_pm_repair_decisions",
        "tests.router_runtime.control_blockers",
        patterns=(
            "test_distinct_pm_control_blocker_causes_create_distinct_families",
            "test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it",
            "test_pm_repair_decision_state_persists_before_followup_wait_is_exposed",
            "test_pm_repair_decision_can_repeat_for_new_control_blocker",
            "test_pm_repair_decision_rejects_unsupported_event_replay_plan_kind",
            "test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target",
            "test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write",
            "test_protocol_dead_end_terminal_family_suppresses_reopened_blocker",
            "test_same_family_delivered_pm_control_blocker_reuses_existing_artifact",
            "test_same_family_pending_pm_control_blocker_reuses_existing_artifact",
        ),
        description="Control-blocker PM repair-decision and PM blocker-family validation slice.",
    ),
    _unittest_k(
        "router_control_blockers_protocol_transactions",
        "tests.router_runtime.control_blockers",
        patterns=(
            "test_delivered_control_blocker_with_empty_repair_transaction_requires_pm_repair_decision",
            "test_operation_replay_repair_transaction_queues_replay_action",
            "test_repair_transaction_recheck_blocker_registers_followup_blocker",
            "test_repair_transaction_protocol_blocker_registers_followup_blocker",
        ),
        description="Control-blocker repair transaction protocol slice.",
    ),
    _unittest_k(
        "router_control_blockers_followup_fatal",
        "tests.router_runtime.control_blockers",
        patterns=(
            "test_control_blocker_reviewer_followup_rejects_pm_origin",
            "test_delivered_control_blocker_with_unsupported_invalid_wait_requires_pm_repair_resubmission",
            "test_fatal_control_blocker_rejects_pm_ordinary_waiver",
        ),
        description="Control-blocker reviewer follow-up and fatal-blocker slice.",
    ),
)

ROUTER_PM_ROLE_WORK_COMMANDS = (
    _unittest_k(
        "router_pm_role_work_requests",
        "tests.router_runtime.pm_role_work",
        patterns=(
            "test_pm_role_work_request_requires_valid_recipient_and_contract",
            "test_pm_role_work_request_rejects_current_node_contract_family",
            "test_pm_role_work_request_supersedes_unrelayed_old_request",
            "test_advisory_pm_role_work_wait_is_marked_nonblocking",
        ),
        description="PM role-work request validation and advisory wait slice.",
    ),
    _unittest_k(
        "router_pm_role_work_results",
        "tests.router_runtime.pm_role_work",
        patterns=(
            "test_gate_targeted_pm_role_work_result_requires_mapped_gate_event",
            "test_strict_pm_role_work_result_rejects_wrong_next_recipient",
            "test_pm_role_work_existing_result_reconciles_before_wait",
        ),
        description="PM role-work result mapping and recipient contract slice.",
    ),
    _unittest_k(
        "router_pm_role_work_waits",
        "tests.router_runtime.pm_role_work",
        patterns=(
            "test_pm_role_work_batch_waits_for_all_distinct_role_results_before_pm_relay",
            "test_wait_event_producer_binding_rejects_wrong_target_role",
        ),
        description="PM role-work wait, batch, and producer binding slice.",
    ),
)

ROUTER_QUALITY_GATE_COMMANDS = (
    _unittest_k(
        "router_quality_gates_background_manifest",
        "tests.router_runtime.quality_gates",
        patterns=(
            "test_startup_no_longer_schedules_legacy_role_slots",
            "test_child_skill_gate_manifest_block_records_repair_without_approval",
            "test_child_skill_gate_manifest_repair_pass_clears_active_gate_block",
            "test_manifest_references_existing_system_cards",
        ),
        description="Quality-gate runtime role and manifest slice.",
    ),
    _unittest_k(
        "router_quality_gates_decisions",
        "tests.router_runtime.quality_gates",
        patterns=(
            "test_gate_decision_event_records_ledger_and_state",
            "test_gate_decision_rejects_mechanical_contradictions",
            "test_gate_decision_same_identity_replay_is_already_recorded",
            "test_gate_outcome_block_specs_are_registered_and_reset_stale_passes",
            "test_reviewer_and_flowguard_operator_gate_event_groups_have_non_pass_outcomes",
            "test_reviewer_block_events_are_registered_in_external_taxonomy",
        ),
        description="Quality-gate decision and reviewer/FlowGuard operator event slice.",
    ),
    _unittest_k(
        "router_quality_gates_evidence_package",
        "tests.router_runtime.quality_gates",
        patterns=("test_evidence_quality_package_blocks_stale_and_missing_visual_evidence",),
        description="Quality-gate evidence package slice.",
    ),
    _unittest_k(
        "router_quality_gates_route_check_reports",
        "tests.router_runtime.quality_gates",
        patterns=("test_route_check_reports_require_hard_gate_verdict_fields",),
        description="Quality-gate route-check report verdict slice.",
    ),
    _unittest_k(
        "router_quality_gates_route_check_delivery",
        "tests.router_runtime.quality_gates",
        patterns=("test_route_check_results_require_router_delivered_check_cards",),
        description="Quality-gate route-check card delivery slice.",
    ),
    _unittest_k(
        "router_quality_gates_router_owned_proof",
        "tests.router_runtime.quality_gates",
        patterns=("test_router_owned_check_proof_rejects_self_attested_and_stale_audit",),
        description="Quality-gate router-owned proof slice.",
    ),
    _unittest_k(
        "router_quality_gates_artifact_validation",
        "tests.router_runtime.quality_gates",
        patterns=(
            "test_validate_artifact_reports_gate_decision_issues_together",
            "test_validate_artifact_reports_node_acceptance_missing_fields_together",
        ),
        description="Quality-gate artifact validation slice.",
    ),
    _unittest_k(
        "router_quality_gates_model_miss_sync",
        "tests.router_runtime.quality_gates",
        patterns=("test_model_miss_review_block_flags_stay_in_sync",),
        description="Quality-gate model-miss synchronization slice.",
    ),
    _unittest_k(
        "router_quality_gates_node_acceptance_plan",
        "tests.router_runtime.quality_gates",
        patterns=("test_node_acceptance_plan_requires_pm_high_standard_recheck",),
        description="Quality-gate node acceptance high-standard recheck slice.",
    ),
    _unittest_k(
        "router_quality_gates_route_repair_reopens_draft",
        "tests.router_runtime.quality_gates",
        patterns=("test_process_route_repair_required_blocks_activation_and_reopens_pm_route_draft",),
        description="Quality-gate route repair draft-reopen slice.",
    ),
    _unittest_k(
        "router_quality_gates_root_contract",
        "tests.router_runtime.quality_gates",
        patterns=("test_root_contract_freeze_requires_clean_self_interrogation_records",),
        description="Quality-gate root contract self-interrogation slice.",
    ),
    _unittest_k(
        "router_quality_gates_route_draft_product_model",
        "tests.router_runtime.quality_gates",
        patterns=("test_route_draft_requires_product_behavior_model_report",),
        description="Quality-gate route draft product-model report slice.",
    ),
    _unittest_k(
        "router_quality_gates_node_contracts",
        "tests.router_runtime.quality_gates",
        patterns=(
            "test_next_effective_node_returns_parent_before_sibling_module_after_last_child",
            "test_node_completion_idempotency_is_scoped_to_active_node",
            "test_role_output_envelope_hash_survives_same_path_envelope_rewrite",
            "test_single_agent_startup_answer_is_rejected_as_legacy_option",
        ),
        description="Quality-gate node completion and role-output contract slice.",
    ),
)

ROUTER_TERMINAL_COMMANDS = (
    *ROUTER_PM_ROLE_WORK_COMMANDS,
    *ROUTER_QUALITY_GATE_COMMANDS,
    *ROUTER_TERMINAL_CORE_COMMANDS,
)

