from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_card_settlement as card_settlement  # noqa: E402
import flowpilot_router_controller_boundary as controller_boundary  # noqa: E402
import flowpilot_router_errors as router_errors  # noqa: E402
import flowpilot_router_io as router_io  # noqa: E402
import flowpilot_router_protocol_tables as protocol_tables  # noqa: E402


class FlowPilotRouterBoundaryTests(unittest.TestCase):
    def test_router_facade_reexports_error_and_io_helpers(self) -> None:
        self.assertIs(router.RouterError, router_errors.RouterError)
        self.assertIs(router.RouterLedgerWriteInProgress, router_errors.RouterLedgerWriteInProgress)
        self.assertIs(router.write_json, router_io.write_json)
        self.assertIs(router.read_json, router_io.read_json)
        self.assertIs(router.project_relative, router_io.project_relative)
        self.assertIs(router._json_write_lock_path, router_io._json_write_lock_path)

    def test_runtime_json_helpers_round_trip_through_router_facade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            payload = {"schema_version": "test.v1", "value": 1}

            router.write_json(path, payload)

            self.assertEqual(router.read_json(path), payload)
            self.assertFalse(router._json_write_lock_path(path).exists())
            written = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(written, payload)

    def test_card_settlement_identity_helpers_match_nested_records(self) -> None:
        record = {
            "action": {
                "delivery_attempt_id": "attempt-1",
                "expected_return_path": "acks/card.ack.json",
                "card_return_event": "pm_card_ack",
                "card_id": "pm.model_miss_triage",
            }
        }

        self.assertTrue(
            card_settlement._record_matches_card_identity(
                record,
                delivery_attempt_id="attempt-1",
                expected_return_path="",
                card_return_event="",
                card_id="",
            )
        )
        self.assertTrue(
            card_settlement._record_matches_card_identity(
                record,
                delivery_attempt_id="",
                expected_return_path="",
                card_return_event="pm_card_ack",
                card_id="pm.model_miss_triage",
            )
        )

    def test_card_bundle_identity_requires_anchor_for_event_only_match(self) -> None:
        self.assertFalse(
            card_settlement._record_matches_card_bundle_identity(
                {"card_return_event": "pm_card_bundle_ack"},
                bundle_id="",
                expected_return_path="",
                card_return_event="pm_card_bundle_ack",
            )
        )
        self.assertTrue(
            card_settlement._record_matches_card_bundle_identity(
                {"card_bundle_id": "bundle-1", "card_return_event": "pm_card_bundle_ack"},
                bundle_id="",
                expected_return_path="",
                card_return_event="pm_card_bundle_ack",
            )
        )

    def test_startup_pm_bundle_ack_predicate_uses_supplied_startup_ids(self) -> None:
        record = {"target_role": "project_manager", "member_card_ids": ["pm.core"]}

        self.assertTrue(
            card_settlement.is_startup_pm_card_bundle_ack_record(
                record,
                pre_review_startup_card_ids={"pm.core"},
            )
        )
        self.assertFalse(
            card_settlement.is_startup_pm_card_bundle_ack_record(
                record,
                pre_review_startup_card_ids={"reviewer.startup_fact_check"},
            )
        )

    def test_controller_boundary_constants_stay_reexported_by_router(self) -> None:
        self.assertIs(router.CONTROLLER_ACTION_CLOSED_STATUSES, controller_boundary.CONTROLLER_ACTION_CLOSED_STATUSES)
        self.assertIs(router.PASSIVE_WAIT_STATUS_ACTION_TYPES, controller_boundary.PASSIVE_WAIT_STATUS_ACTION_TYPES)
        self.assertEqual(router._format_seconds_for_command(10.0), "10")
        self.assertEqual(router._format_seconds_for_command(0.5), "0.5")
        self.assertEqual(
            router._controller_patrol_timer_command(2.5),
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 2.5",
        )

    def test_protocol_tables_stay_reexported_by_router(self) -> None:
        self.assertIs(router.MAIL_SEQUENCE, protocol_tables.MAIL_SEQUENCE)
        self.assertIs(router.RUN_TERMINAL_STATUSES, protocol_tables.RUN_TERMINAL_STATUSES)
        self.assertEqual(router._mail_sequence_entry("user_intake")["to_role"], "project_manager")
        self.assertIn("completed", router.RUN_TERMINAL_STATUSES)


if __name__ == "__main__":
    unittest.main()
