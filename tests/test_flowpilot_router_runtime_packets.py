from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_current_node_direct_relay_blocks_missing_output_contract",
    "test_formal_work_packet_ack_preflight_blocks_target_pending_card_ack",
    "test_mail_delivery_receipt_waits_for_active_packet_ledger_writer",
    "test_current_node_packet_relay_uses_router_direct_dispatch",
    "test_current_node_worker_packet_requires_active_child_skill_binding_projection",
    "test_current_node_completion_requires_reviewer_passed_packet_audit",
    "test_unready_leaf_cannot_receive_current_node_packet",
    "test_current_node_result_relay_combines_ledger_check_with_relay",
    "test_current_node_packet_and_result_reject_envelope_aliases",
    "test_current_node_result_decision_requires_review_card_after_result_relay",
    "test_router_packet_audit_rejection_routes_pm_repair_decision",
    "test_controller_repair_work_packet_queues_bounded_controller_action",
    "test_pm_repair_decision_rejects_parent_repair_targeting_current_node_packet",
    "test_current_node_result_requires_write_grant",
    "test_current_node_packet_rejects_unresolved_node_entry_self_interrogation",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
