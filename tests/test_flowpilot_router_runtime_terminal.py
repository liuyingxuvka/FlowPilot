from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work",
    "test_user_stop_writes_immediate_daemon_terminal_fence_and_clears_current_work",
    "test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts",
    "test_user_stop_writes_terminal_fence_before_best_effort_scheduler_cleanup",
    "test_terminal_pending_heartbeat_action_is_noop",
    "test_reconcile_run_recovers_terminal_status_from_current_pointer",
    "test_terminal_summary_payload_requires_attribution_display_and_run_root_sources",
    "test_controller_patrol_timer_allows_terminal_return_only_when_stopped",
    "test_startup_intake_cancel_is_terminal_after_daemon_first_shell",
    "test_nonterminal_node_completion_does_not_show_completed_node_as_in_progress",
    "test_final_ledger_rejects_missing_source_of_truth_entries_and_contract_replay",
    "test_terminal_replay_requires_reviewed_segments_and_pm_segment_decisions",
    "test_final_ledger_records_frozen_contract_replay_source_paths",
    "test_final_ledger_rejects_dirty_self_interrogation_index",
    "test_final_ledger_rejects_dirty_pm_suggestion_ledger",
    "test_reconcile_recovers_legacy_terminal_closure_state",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
