from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_new_invocation_creates_fresh_run_scoped_bootstrap_over_stale_state",
    "test_start_command_creates_fresh_run_when_current_is_running",
    "test_new_invocation_preserves_multiple_parallel_running_runs",
    "test_cli_accepts_json_after_subcommand",
    "test_unsupported_high_risk_fold_commands_are_not_cli_commands",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
