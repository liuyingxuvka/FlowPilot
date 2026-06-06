from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_router_daemon_tick_consumes_card_ack_without_manual_next",
    "test_router_daemon_incomplete_bundle_ack_waits_without_advancing",
    "test_dispatch_recipient_gate_classifies_ack_only_card_as_prompt",
    "test_dispatch_recipient_gate_allows_work_after_resolved_ack_only_card_wait",
    "test_dispatch_recipient_gate_keeps_output_work_busy_after_card_ack_only",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
