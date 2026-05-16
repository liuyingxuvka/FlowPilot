from __future__ import annotations

import unittest

from tests.test_flowpilot_router_runtime import FlowPilotRouterRuntimeTests


TEST_NAMES = (
    "test_officer_role_work_writes_authorized_lifecycle_index",
    "test_display_plan_is_controller_synced_projection_from_pm_plan",
    "test_terminal_summary_payload_requires_attribution_display_and_run_root_sources",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del loader, tests, pattern
    suite = unittest.TestSuite()
    for name in TEST_NAMES:
        suite.addTest(FlowPilotRouterRuntimeTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
