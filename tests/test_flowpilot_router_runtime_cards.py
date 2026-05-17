from __future__ import annotations

import unittest

from tests.flowpilot_router_runtime_suite import load_named_runtime_tests


TEST_NAMES = (
    "test_phase_card_delivery_context_includes_required_upstream_sources",
    "test_system_card_delivery_uses_router_internal_manifest_check",
    "test_committed_system_card_relay_can_resolve_without_apply_roundtrip",
    "test_record_external_event_preconsumes_valid_card_ack_before_blocking",
    "test_record_external_event_quarantines_invalid_same_role_card_ack_report",
    "test_initial_pm_system_cards_are_delivered_as_same_role_bundle",
    "test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers",
    "test_pm_card_bundle_ack_keeps_router_owned_user_intake_sealed_until_activation",
    "test_missing_system_card_ack_wait_reminds_original_envelope_without_duplicate_delivery",
    "test_missing_system_card_ack_wait_confirms_controller_delivery_before_target_reminder",
    "test_missing_system_card_ack_after_controller_delivery_done_reminds_target_role",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    return load_named_runtime_tests(loader, tests, pattern, TEST_NAMES)


if __name__ == "__main__":
    unittest.main()
