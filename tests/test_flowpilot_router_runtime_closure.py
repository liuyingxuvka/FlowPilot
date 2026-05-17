from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_officer_role_work_writes_authorized_lifecycle_index",
    "test_display_plan_is_controller_synced_projection_from_pm_plan",
    "test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay",
    "test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay",
    "test_pm_terminal_closure_uses_file_backed_contract_and_prior_context",
    "test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
