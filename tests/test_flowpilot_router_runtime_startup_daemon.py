from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_bootloader_action_requires_pending_router_action",
    "test_run_until_wait_applies_only_safe_startup_action",
    "test_run_until_wait_folds_only_internal_bootloader_actions_after_banner",
    "test_run_until_wait_folds_user_intake_then_stops_before_role_boundary",
    "test_manual_startup_writes_current_resume_binding_after_controller_core",
    "test_manual_startup_records_current_resume_binding_for_resume_reentry",
    "test_formal_startup_starts_router_daemon_before_controller_core",
    "test_startup_daemon_defers_banner_and_queues_next_boot_row",
    "test_deterministic_bootstrap_seed_failure_does_not_create_pm_blocker",
    "test_deterministic_bootstrap_seed_replay_uses_existing_evidence",
    "test_reconciled_scheduler_row_receipt_replay_does_not_create_pm_blocker",
    "test_startup_daemon_bootloader_completion_uses_receipt_owner",
    "test_load_controller_core_receipt_reconciles_startup_postcondition",
    "test_startup_reconciliation_resolves_stale_blocker_and_supersedes_pm_row",
    "test_startup_missing_router_postcondition_retries_before_pm_blocker",
    "test_startup_daemon_queues_controller_core_without_legacy_role_or_automation_wait",
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
    "test_runtime_json_self_owned_stale_write_lock_is_safely_recovered",
    "test_runtime_json_fresh_self_owned_write_lock_is_not_stolen",
    "test_runtime_json_self_owned_stale_lock_with_temp_artifact_is_not_cleared",
    "test_runtime_json_lock_cleanup_failure_is_recorded",
    "test_router_daemon_corrupted_scheduler_ledger_writes_error_status",
    "test_router_daemon_waits_on_fresh_scheduler_write_lock_before_error",
    "test_atomic_replace_permission_error_becomes_runtime_write_wait",
    "test_router_daemon_nested_state_write_lock_wait_does_not_exit",
    "test_terminal_startup_daemon_schedule_does_not_append_boot_rows",
    "test_router_daemon_status_not_active_after_error_lock_or_missing_pid",
    "test_startup_rejects_legacy_reviewer_event_before_pm_work",
    "test_startup_rejects_legacy_startup_fact_role_output_ledger",
    "test_startup_waits_for_answers_before_banner_or_controller",
    "test_startup_intake_rejects_body_hash_mismatch",
    "test_startup_intake_rejects_body_text_in_controller_payload",
    "test_startup_intake_rejects_headless_confirmed_result",
    "test_startup_sequence_creates_prompt_isolated_run",
    "test_startup_banner_action_and_result_are_user_visible",
    "test_user_intake_from_startup_ui_is_router_owned_and_sealed_from_controller",
    "test_daemon_ignores_old_startup_role_flags_from_bootstrap",
    "test_partial_old_startup_role_flags_are_ignored_without_settlement_wait",
    "test_startup_current_path_releases_user_intake_without_startup_role_gate",
    "test_startup_old_role_gate_events_are_unsupported",
    "test_cockpit_startup_answer_is_rejected_as_legacy_option",
    "test_old_startup_role_output_contracts_are_absent",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()

