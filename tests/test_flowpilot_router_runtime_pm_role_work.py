from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_pm_role_work_existing_result_reconciles_before_wait",
    "test_advisory_pm_role_work_wait_is_marked_nonblocking",
    "test_gate_targeted_pm_role_work_result_requires_mapped_gate_event",
    "test_pm_role_work_batch_waits_for_all_officer_results_before_pm_relay",
    "test_pm_role_work_request_requires_valid_recipient_and_contract",
    "test_pm_role_work_request_rejects_current_node_contract_family",
    "test_strict_pm_role_work_result_rejects_wrong_next_recipient",
    "test_wait_event_producer_binding_rejects_wrong_target_role",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
