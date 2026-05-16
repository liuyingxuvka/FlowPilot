from __future__ import annotations

import unittest

from tests.test_flowpilot_router_runtime import FlowPilotRouterRuntimeTests


TEST_NAMES = (
    "test_current_node_packet_relay_uses_router_direct_dispatch",
    "test_dispatch_recipient_gate_blocks_busy_packet_holder",
    "test_dispatch_recipient_gate_allows_system_card_for_active_holder",
    "test_dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending",
    "test_dispatch_recipient_gate_allows_pm_after_user_intake_first_output",
    "test_dispatch_recipient_gate_blocks_followup_when_role_wait_is_active",
    "test_dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition",
    "test_dispatch_recipient_gate_allows_same_role_system_card_bundle",
    "test_dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending",
    "test_current_node_parallel_batch_waits_for_all_results_before_review",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del loader, tests, pattern
    suite = unittest.TestSuite()
    for name in TEST_NAMES:
        suite.addTest(FlowPilotRouterRuntimeTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
