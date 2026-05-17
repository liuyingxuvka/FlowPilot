from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_material_work_packet_records_target_ack_preflight_passed",
    "test_material_scan_accepts_file_backed_packet_body_and_updates_frontier",
    "test_record_event_accepts_material_scan_envelope_ref_with_packets",
    "test_record_event_rejects_manual_material_scan_payload_with_hidden_packets",
    "test_material_scan_packet_and_result_relays_combine_ledger_check",
    "test_material_scan_packet_body_event_requires_packet_ledger_open_receipt",
    "test_current_node_packet_relay_uses_router_direct_dispatch",
    "test_current_node_worker_packet_requires_active_child_skill_binding_projection",
    "test_current_node_completion_requires_reviewer_passed_packet_audit",
    "test_current_node_packet_and_result_accept_safe_envelope_aliases",
    "test_current_node_result_decision_requires_review_card_after_result_relay",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
