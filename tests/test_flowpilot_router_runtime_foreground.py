from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_foreground_next_waits_on_stale_lock_when_owner_process_is_live",
    "test_foreground_controller_standby_waits_on_live_daemon_role_wait",
    "test_foreground_controller_standby_materializes_report_reminder_with_liveness_probe",
    "test_foreground_controller_standby_default_waits_past_timeout_until_action",
    "test_foreground_controller_standby_returns_no_output_reissue_required",
    "test_foreground_controller_standby_returns_lost_role_blocker_required",
    "test_foreground_controller_standby_returns_ack_reminder_and_blocker_due",
    "test_foreground_controller_standby_self_audits_controller_local_wait",
    "test_foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action",
    "test_controller_patrol_timer_continue_patrol_restarts_and_waits",
    "test_controller_patrol_timer_continues_for_daemon_heartbeat_inside_thirty_second_window",
    "test_controller_patrol_timer_requests_liveness_check_after_delayed_daemon_heartbeat",
    "test_foreground_controller_standby_requests_liveness_check_on_stale_or_missing_daemon",
    "test_foreground_controller_standby_does_not_compute_router_next",
    "test_run_until_wait_folds_nonblocking_display_sync",
    "test_progress_summary_counts_nested_active_path",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
