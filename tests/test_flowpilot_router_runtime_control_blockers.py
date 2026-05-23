from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_runtime_write_lock_exception_does_not_materialize_pm_semantic_blocker",
    "test_control_blocker_reviewer_followup_rejects_pm_origin",
    "test_control_plane_reissue_retry_budget_escalates_to_pm",
    "test_pm_semantic_control_blocker_zero_retry_budget_is_exhausted",
    "test_already_recorded_event_can_resolve_delivered_control_blocker",
    "test_already_recorded_event_does_not_resolve_pm_required_control_blocker",
    "test_already_recorded_event_resolves_fatal_control_blocker_after_pm_repair_decision",
    "test_fatal_control_blocker_rejects_pm_ordinary_waiver",
    "test_repair_transaction_recheck_blocker_registers_followup_blocker",
    "test_repair_transaction_protocol_blocker_registers_followup_blocker",
    "test_pm_repair_decision_rejects_unregistered_rerun_target_before_wait_write",
    "test_delivered_control_blocker_with_legacy_invalid_wait_falls_back_to_pm_repair_decision",
    "test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it",
    "test_pm_repair_decision_rejects_legacy_event_replay_without_existing_producer",
    "test_operation_replay_repair_transaction_queues_replay_action",
    "test_material_operation_replay_uses_current_generation_action",
    "test_pm_repair_decision_rejects_registered_but_not_receivable_rerun_target",
    "test_pm_repair_decision_can_repeat_for_new_control_blocker",
    "test_missing_open_receipt_control_blocker_routes_to_same_reviewer_reissue",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
