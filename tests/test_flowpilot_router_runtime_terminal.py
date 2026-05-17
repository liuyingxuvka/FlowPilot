from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work",
    "test_reconcile_run_recovers_terminal_status_from_current_pointer",
    "test_terminal_summary_payload_requires_attribution_display_and_run_root_sources",
    "test_reconcile_recovers_legacy_terminal_closure_state",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
