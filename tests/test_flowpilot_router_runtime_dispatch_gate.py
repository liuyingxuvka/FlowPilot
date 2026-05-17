from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_dispatch_recipient_gate_blocks_busy_packet_holder",
    "test_dispatch_recipient_gate_allows_system_card_for_active_holder",
    "test_dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending",
    "test_dispatch_recipient_gate_allows_pm_after_user_intake_first_output",
    "test_dispatch_recipient_gate_blocks_followup_when_role_wait_is_active",
    "test_dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition",
    "test_dispatch_recipient_gate_allows_same_role_system_card_bundle",
    "test_dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending",
    "test_user_intake_mail_declares_first_pm_output_obligation",
    "test_current_node_parallel_batch_waits_for_all_results_before_review",
    "test_current_node_pre_review_reconciliation_blocks_reviewer_card",
    "test_startup_reconciliation_wait_does_not_hide_router_local_obligation",
    "test_startup_reconciliation_wait_does_not_block_itself",
    "test_current_node_reviewer_pass_event_waits_for_local_reconciliation",
    "test_future_node_pending_return_does_not_block_current_node_review",
    "test_current_node_completion_waits_for_review_created_local_obligations",
    "test_no_legal_next_action_materializes_pm_decision_control_blocker",
    "test_router_hard_rejection_returns_control_plane_reissue_action",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
