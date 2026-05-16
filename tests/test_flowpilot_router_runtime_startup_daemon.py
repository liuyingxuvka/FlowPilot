from __future__ import annotations

import unittest

from tests.test_flowpilot_router_runtime import FlowPilotRouterRuntimeTests


TEST_NAMES = (
    "test_bootloader_action_requires_pending_router_action",
    "test_run_until_wait_applies_only_safe_startup_action",
    "test_run_until_wait_folds_only_internal_bootloader_actions_after_banner",
    "test_run_until_wait_folds_user_intake_then_stops_before_role_boundary",
    "test_scheduled_startup_heartbeat_is_queued_after_controller_core",
    "test_manual_startup_skips_heartbeat_after_controller_core",
    "test_formal_startup_starts_router_daemon_before_controller_core",
    "test_startup_daemon_defers_banner_and_queues_next_boot_row",
    "test_startup_daemon_bootloader_completion_uses_receipt_owner",
    "test_formal_startup_daemon_failure_blocks_controller_core",
    "test_formal_startup_attaches_same_run_live_daemon_without_duplicate_spawn",
    "test_startup_waits_for_answers_before_banner_or_controller",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del loader, tests, pattern
    suite = unittest.TestSuite()
    for name in TEST_NAMES:
        suite.addTest(FlowPilotRouterRuntimeTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
