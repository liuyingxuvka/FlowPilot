from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_resume_reentry_loads_state_before_resume_cards",
    "test_resume_reentry_attaches_to_live_router_daemon_and_ledger",
    "test_resume_reentry_attaches_to_live_owner_after_delayed_heartbeat",
    "test_resume_reentry_marks_dead_daemon_for_restart_after_liveness_check",
    "test_resume_reentry_preempts_active_control_blocker_until_replay_or_pm_decision",
    "test_load_resume_state_does_not_downgrade_existing_role_recovery_report",
    "test_resume_rehydration_settles_existing_output_without_pm",
    "test_resume_rehydration_reissues_missing_obligations_before_pm",
    "test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
    "test_heartbeat_alive_status_still_enters_router_resume_path",
    "test_heartbeat_startup_records_one_minute_active_binding_for_resume_reentry",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
