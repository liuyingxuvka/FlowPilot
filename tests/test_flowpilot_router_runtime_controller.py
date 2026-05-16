from __future__ import annotations

import unittest

from tests.test_flowpilot_router_runtime import FlowPilotRouterRuntimeTests


TEST_NAMES = (
    "test_controller_action_summary_separates_done_history_from_active_work",
    "test_passive_wait_projection_is_not_ordinary_controller_work",
    "test_all_passive_wait_types_are_status_projections_not_work_rows",
    "test_current_work_uses_packet_holder_when_pending_wait_is_empty",
    "test_current_work_uses_passive_reconciliation_owner_when_pending_wait_is_empty",
    "test_router_daemon_tick_writes_controller_action_ledger_and_receipt_reconciles",
    "test_reconciled_scheduler_row_is_not_downgraded_by_later_receipt_sync",
    "test_completed_pending_controller_action_receipt_is_not_returned_again",
    "test_controller_boundary_done_receipt_reclaims_router_postcondition",
    "test_controller_boundary_projection_reclaims_stale_flags_without_pending_action",
    "test_controller_boundary_done_receipt_missing_deliverable_schedules_repair",
    "test_controller_boundary_valid_artifact_reclaims_before_repair",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    del loader, tests, pattern
    suite = unittest.TestSuite()
    for name in TEST_NAMES:
        suite.addTest(FlowPilotRouterRuntimeTests(name))
    return suite


if __name__ == "__main__":
    unittest.main()
