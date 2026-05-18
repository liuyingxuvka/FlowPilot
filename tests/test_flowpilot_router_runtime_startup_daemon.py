from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_bootloader_action_requires_pending_router_action",
    "test_run_until_wait_applies_only_safe_startup_action",
    "test_run_until_wait_folds_only_internal_bootloader_actions_after_banner",
    "test_run_until_wait_folds_user_intake_then_stops_before_role_boundary",
    "test_scheduled_startup_heartbeat_is_queued_after_controller_core",
    "test_manual_startup_skips_heartbeat_after_controller_core",
    "test_formal_startup_starts_router_daemon_before_controller_core",
    "test_startup_daemon_defers_banner_and_queues_next_boot_row",
    "test_deterministic_bootstrap_seed_failure_does_not_create_pm_blocker",
    "test_deterministic_bootstrap_seed_replay_uses_existing_evidence",
    "test_reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker",
    "test_startup_daemon_bootloader_completion_uses_receipt_owner",
    "test_legacy_startup_daemon_postcondition_owner_canonicalizes_to_receipt_owner",
    "test_load_controller_core_receipt_reconciles_startup_postcondition",
    "test_startup_reconciliation_resolves_stale_blocker_and_supersedes_pm_row",
    "test_startup_missing_router_postcondition_retries_before_pm_blocker",
    "test_startup_daemon_queues_role_heartbeat_and_controller_core_without_role_wait",
    "test_startup_async_receipts_update_bootstrap_flags_and_scheduler_rows",
    "test_formal_startup_daemon_failure_blocks_controller_core",
    "test_formal_startup_attaches_same_run_live_daemon_without_duplicate_spawn",
    "test_run_until_wait_reaches_card_boundary_after_router_internal_manifest_check",
    "test_router_daemon_observation_initializes_lock_status_and_ledger",
    "test_router_daemon_tick_stays_bound_when_current_focus_changes",
    "test_router_daemon_stop_targets_one_parallel_run",
    "test_router_daemon_refresh_does_not_reactivate_released_lock",
    "test_router_daemon_queues_visible_startup_rows_after_internal_audit",
    "test_router_daemon_immediately_continues_after_queue_budget_stop",
    "test_router_daemon_sleeps_after_real_queue_wait",
    "test_startup_obligations_are_not_global_scheduler_barriers",
    "test_true_barriers_still_stop_scheduler_queueing",
    "test_startup_bootloader_already_reconciled_backfills_scheduler_row",
    "test_startup_bootloader_receipt_updates_bootstrap_and_scheduler_row",
    "test_startup_intake_controller_receipt_folds_native_ui_result",
    "test_startup_review_join_checks_bootstrap_banner_and_role_flags",
    "test_runtime_ledgers_remain_valid_json_after_repeated_daemon_writes",
    "test_runtime_json_dead_owner_write_lock_is_replaced_with_takeover_record",
    "test_router_daemon_corrupted_scheduler_ledger_writes_error_status",
    "test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error",
    "test_atomic_replace_permission_error_becomes_runtime_write_wait",
    "test_router_daemon_nested_state_write_lock_wait_does_not_exit",
    "test_terminal_startup_daemon_schedule_does_not_append_boot_rows",
    "test_router_daemon_status_not_active_after_error_lock_or_missing_pid",
    "test_startup_reviewer_event_uses_current_scope_reconciliation",
    "test_startup_fact_role_output_ledger_is_reconciled_by_router_tick",
    "test_startup_fact_canonical_artifact_drift_syncs_flag_once",
    "test_startup_waits_for_answers_before_banner_or_controller",
    "test_startup_intake_rejects_body_hash_mismatch",
    "test_startup_intake_rejects_body_text_in_controller_payload",
    "test_startup_intake_rejects_headless_confirmed_result",
    "test_startup_sequence_creates_prompt_isolated_run",
    "test_startup_banner_action_and_result_are_user_visible",
    "test_user_intake_from_startup_ui_is_router_owned_and_sealed_from_controller",
    "test_legacy_startup_answer_boundary_records_answers",
    "test_record_startup_answers_rejects_naked_inferred_or_invalid_values",
    "test_record_startup_answers_accepts_ai_interpretation_with_reviewer_receipt",
    "test_daemon_folds_stable_startup_role_flags_from_bootstrap",
    "test_partial_startup_role_flags_wait_for_settlement",
    "test_startup_activation_requires_reviewer_facts_before_work",
    "test_reviewer_startup_findings_go_to_pm_without_control_blocker",
    "test_pm_can_approve_startup_findings_with_file_backed_decision",
    "test_pm_startup_repair_request_resets_fact_review_cycle",
    "test_pm_startup_repair_request_can_repeat_for_new_blocking_report",
    "test_cockpit_requested_startup_display_records_chat_fallback_mermaid",
    "test_startup_fact_report_accepts_file_backed_envelope_only_payload",
    "test_startup_fact_report_rejects_canonical_submission_alias",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
