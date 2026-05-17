from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_action_handlers as action_handlers  # noqa: E402
import flowpilot_router_action_providers as action_providers  # noqa: E402
import flowpilot_router_card_settlement as card_settlement  # noqa: E402
import flowpilot_router_controller_boundary as controller_boundary  # noqa: E402
import flowpilot_router_controller_reconciliation as controller_reconciliation  # noqa: E402
import flowpilot_router_dispatch_gate as dispatch_gate  # noqa: E402
import flowpilot_router_events as router_events  # noqa: E402
import flowpilot_router_errors as router_errors  # noqa: E402
import flowpilot_router_io as router_io  # noqa: E402
import flowpilot_router_protocol_tables as protocol_tables  # noqa: E402
import flowpilot_router_resume as router_resume  # noqa: E402
import flowpilot_router_route as router_route  # noqa: E402
import flowpilot_router_startup_daemon as startup_daemon  # noqa: E402
import flowpilot_router_terminal as terminal_helpers  # noqa: E402


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

    def test_card_settlement_ack_helpers_stay_reexported_by_router(self) -> None:
        self.assertIs(router._card_ack_clearance_scope, card_settlement._card_ack_clearance_scope)
        self.assertIs(router._pending_action_matches_card_return, card_settlement._pending_action_matches_card_return)
        self.assertIs(router._original_card_ack_reminder_policy, card_settlement._original_card_ack_reminder_policy)
        scope = router._card_ack_clearance_scope(
            {"current_stage": {"current_node_id": "node-1", "current_phase": "work"}},
            card_id="pm.current_node_loop",
            target_role="project_manager",
        )
        self.assertEqual(scope["boundary_kind"], "node")
        self.assertTrue(scope["ack_is_read_receipt_only"])
        self.assertTrue(
            router._pending_action_matches_card_return(
                {"delivery_attempt_id": "attempt-1"},
                {"delivery_attempt_id": "attempt-1"},
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

    def test_controller_reconciliation_helpers_stay_reexported_by_router(self) -> None:
        self.assertIs(router._action_is_passive_wait_status, controller_reconciliation._action_is_passive_wait_status)
        self.assertIs(router._controller_action_counts, controller_reconciliation._controller_action_counts)
        self.assertIs(router._controller_action_summary, controller_reconciliation._controller_action_summary)
        self.assertIs(router._router_scheduler_row_counts, controller_reconciliation._router_scheduler_row_counts)
        self.assertEqual(
            router._controller_action_projection_kind({"action_type": "await_role_decision"}),
            "passive_wait_status",
        )
        self.assertEqual(router._controller_action_initial_status({"action_type": "deliver_mail"}), "pending")

    def test_protocol_tables_stay_reexported_by_router(self) -> None:
        self.assertIs(router.MAIL_SEQUENCE, protocol_tables.MAIL_SEQUENCE)
        self.assertIs(router.RUN_TERMINAL_STATUSES, protocol_tables.RUN_TERMINAL_STATUSES)
        self.assertEqual(router._mail_sequence_entry("user_intake")["to_role"], "project_manager")
        self.assertIn("completed", router.RUN_TERMINAL_STATUSES)

    def test_startup_daemon_helpers_stay_reexported_by_router(self) -> None:
        self.assertIs(router._router_daemon_lock_liveness, startup_daemon._router_daemon_lock_liveness)
        self.assertIs(router._router_daemon_heartbeat_monitor, startup_daemon._router_daemon_heartbeat_monitor)
        self.assertEqual(router.ROUTER_DAEMON_LOCK_SCHEMA, startup_daemon.ROUTER_DAEMON_LOCK_SCHEMA)
        monitor = router._router_daemon_heartbeat_monitor(
            {"status": "active"},
            {"schema_ok": True, "status_active": True, "process_live": True, "age_seconds": 0},
            status_exists=True,
            status_ok=True,
        )
        self.assertEqual(monitor["status"], "ok")
        self.assertFalse(monitor["controller_liveness_check_required"])

    def test_dispatch_gate_helpers_stay_reexported_by_router(self) -> None:
        self.assertIs(router._dispatch_gate_target_roles, dispatch_gate._dispatch_gate_target_roles)
        self.assertIs(router._dispatch_gate_candidate_packet_ids, dispatch_gate._dispatch_gate_candidate_packet_ids)
        self.assertIs(
            router._dispatch_gate_wait_events_for_packet_record,
            dispatch_gate._dispatch_gate_wait_events_for_packet_record,
        )
        self.assertEqual(
            router._dispatch_gate_target_roles({"to_role": "worker_a, project_manager"}),
            {"worker_a", "project_manager"},
        )
        self.assertEqual(
            router._dispatch_gate_wait_events_for_packet_record(
                {"active_packet_holder": "project_manager", "packet_id": "user_intake"}
            ),
            ["pm_issues_material_and_capability_scan_packets"],
        )

    def test_event_boundary_registry_covers_first_migrated_events(self) -> None:
        self.assertEqual(
            set(router_events.PRECHECK_EVENT_HANDLERS),
            {"heartbeat_or_manual_resume_requested"},
        )
        self.assertEqual(
            set(router_events.SIDE_EFFECT_EVENT_HANDLERS),
            {
                "host_records_heartbeat_binding",
                "pm_activates_reviewed_route",
                "user_requests_run_cancel",
                "user_requests_run_stop",
            },
        )
        for event_name in set(router_events.PRECHECK_EVENT_HANDLERS) | set(router_events.SIDE_EFFECT_EVENT_HANDLERS):
            self.assertIn(event_name, router.EXTERNAL_EVENTS)

    def test_controller_action_provider_order_is_stable(self) -> None:
        self.assertEqual(
            action_providers.PROVIDER_ORDER,
            (
                "lifecycle",
                "pending_action",
                "role_recovery",
                "resume",
                "control_blocker",
                "startup_heartbeat",
                "display_plan",
                "controller_boundary",
                "startup_mechanical_audit",
                "startup_display",
                "pending_card_return",
                "system_card_bundle",
                "system_card",
                "resume_wait",
                "mail",
                "material_packet",
                "research_packet",
                "parent_child_entry",
                "current_node_packet",
                "pm_role_work_request",
                "model_miss_followup",
                "model_miss_controlled_stop",
                "expected_role_decision_wait",
                "no_legal_next_action_blocker",
            ),
        )

    def test_controller_action_handler_registry_covers_first_migrated_actions(self) -> None:
        self.assertEqual(
            action_handlers.PASSIVE_WAIT_HANDLER_ACTION_TYPES,
            (
                "await_role_decision",
                "await_card_return_event",
                "await_card_bundle_return_event",
                "await_user_after_model_miss_stop",
            ),
        )
        for action_type in (
            "sync_display_plan",
            "write_terminal_summary",
            "deliver_system_card",
            "deliver_system_card_bundle",
            "run_lifecycle_terminal",
            *action_handlers.PASSIVE_WAIT_HANDLER_ACTION_TYPES,
        ):
            self.assertIn(action_type, action_handlers.ACTION_HANDLERS)

    def test_system_card_auto_commit_helpers_are_thin_router_delegates(self) -> None:
        self.assertTrue(callable(action_handlers.auto_commit_system_card_delivery_action))
        self.assertTrue(callable(action_handlers.auto_commit_system_card_bundle_delivery_action))

    def test_route_domain_helpers_are_available_behind_router_facade(self) -> None:
        self.assertTrue(callable(router_route.route_payload_from_reviewed_draft))
        self.assertTrue(callable(router_route.write_route_activation))
        self.assertTrue(callable(router_route.write_route_mutation))
        self.assertTrue(callable(router._write_route_activation))
        self.assertTrue(callable(router._write_route_mutation))

    def test_resume_domain_helpers_are_available_behind_router_facade(self) -> None:
        self.assertTrue(callable(router_resume.write_host_heartbeat_binding))
        self.assertTrue(callable(router_resume.append_heartbeat_tick))
        self.assertTrue(callable(router_resume.reset_resume_cycle_for_wakeup))
        self.assertTrue(callable(router._write_host_heartbeat_binding))
        self.assertTrue(callable(router._append_heartbeat_tick))
        self.assertTrue(callable(router._reset_resume_cycle_for_wakeup))

    def test_terminal_helpers_stay_reexported_by_router(self) -> None:
        self.assertIs(router._terminal_lifecycle_mode, terminal_helpers._terminal_lifecycle_mode)
        self.assertIs(router._terminal_summary_hash, terminal_helpers._terminal_summary_hash)
        self.assertEqual(router.TERMINAL_SUMMARY_SCHEMA, terminal_helpers.TERMINAL_SUMMARY_SCHEMA)
        self.assertEqual(
            router._terminal_lifecycle_mode({"status": "running", "flags": {"run_cancelled_by_user": True}}),
            "cancelled_by_user",
        )
        self.assertEqual(
            router._terminal_summary_markdown_path(Path("run-root")),
            Path("run-root") / "final_summary.md",
        )


if __name__ == "__main__":
    unittest.main()
