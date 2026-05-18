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
import flowpilot_router_controller_repair as controller_repair  # noqa: E402
import flowpilot_router_controller_scheduler as controller_scheduler  # noqa: E402
import flowpilot_router_controller_scheduler_receipts as controller_scheduler_receipts  # noqa: E402
import flowpilot_router_dispatch_gate as dispatch_gate  # noqa: E402
import flowpilot_router_event_dispatcher as event_dispatcher  # noqa: E402
import flowpilot_router_events as router_events  # noqa: E402
import flowpilot_router_errors as router_errors  # noqa: E402
import flowpilot_router_io as router_io  # noqa: E402
import flowpilot_router_protocol_card_metadata as card_metadata  # noqa: E402
import flowpilot_router_protocol_startup_catalog as startup_catalog  # noqa: E402
import flowpilot_router_protocol_catalog as protocol_catalog  # noqa: E402
import flowpilot_router_protocol_planning_cards as planning_cards  # noqa: E402
import flowpilot_router_protocol_runtime_cards as runtime_cards  # noqa: E402
import flowpilot_router_protocol_tables as protocol_tables  # noqa: E402
import flowpilot_router_resume as router_resume  # noqa: E402
import flowpilot_router_route as router_route  # noqa: E402
import flowpilot_router_runtime_state as runtime_state  # noqa: E402
import flowpilot_router_startup_daemon as startup_daemon  # noqa: E402
import flowpilot_router_terminal as terminal_helpers  # noqa: E402
import flowpilot_router_terminal_ledger as terminal_ledger  # noqa: E402
import flowpilot_router_work_packets as work_packets  # noqa: E402
import flowpilot_router_work_packets_pm_role as work_packets_pm_role  # noqa: E402
import flowpilot_runtime_closure as runtime_closure  # noqa: E402
import packet_runtime  # noqa: E402
import packet_runtime_paths  # noqa: E402
import packet_runtime_relay  # noqa: E402
import packet_runtime_schema  # noqa: E402


class FlowPilotRouterBoundaryTests(unittest.TestCase):
    def test_router_skeleton_public_api_allowlist_is_available(self) -> None:
        self.assertIs(router.RouterError, router_errors.RouterError)
        self.assertIs(router.RouterLedgerWriteInProgress, router_errors.RouterLedgerWriteInProgress)
        for name in (
            "main",
            "parse_args",
            "next_action",
            "apply_action",
            "record_external_event",
            "run_until_wait",
            "run_router_daemon",
            "stop_router_daemon",
            "foreground_controller_standby",
            "controller_patrol_timer",
            "record_controller_action_receipt",
            "reconcile_current_run",
            "validate_artifact",
            "write_role_output_envelope",
        ):
            self.assertTrue(callable(getattr(router, name)), name)

    def test_runtime_json_helpers_round_trip_through_io_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.json"
            payload = {"schema_version": "test.v1", "value": 1}

            router_io.write_json(path, payload)

            self.assertEqual(router_io.read_json(path), payload)
            self.assertFalse(router_io._json_write_lock_path(path).exists())
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

    def test_card_settlement_ack_helpers_belong_to_owner_module(self) -> None:
        scope = card_settlement._card_ack_clearance_scope(
            {"current_stage": {"current_node_id": "node-1", "current_phase": "work"}},
            card_id="pm.current_node_loop",
            target_role="project_manager",
        )
        self.assertEqual(scope["boundary_kind"], "node")
        self.assertTrue(scope["ack_is_read_receipt_only"])
        self.assertTrue(
            card_settlement._pending_action_matches_card_return(
                {"delivery_attempt_id": "attempt-1"},
                {"delivery_attempt_id": "attempt-1"},
            )
        )

    def test_controller_boundary_helpers_belong_to_owner_module(self) -> None:
        self.assertIn("done", controller_boundary.CONTROLLER_ACTION_CLOSED_STATUSES)
        self.assertIn("await_role_decision", controller_boundary.PASSIVE_WAIT_STATUS_ACTION_TYPES)
        self.assertEqual(controller_boundary._format_seconds_for_command(10.0), "10")
        self.assertEqual(controller_boundary._format_seconds_for_command(0.5), "0.5")
        self.assertEqual(
            controller_boundary._controller_patrol_timer_command(2.5),
            "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json controller-patrol-timer --seconds 2.5",
        )

    def test_controller_reconciliation_helpers_belong_to_owner_module(self) -> None:
        self.assertEqual(
            controller_reconciliation._controller_action_projection_kind({"action_type": "await_role_decision"}),
            "passive_wait_status",
        )
        self.assertEqual(controller_reconciliation._controller_action_initial_status({"action_type": "deliver_mail"}), "pending")

    def test_protocol_tables_and_mail_lookup_belong_to_owner_modules(self) -> None:
        controller_repair._bind_router(router)
        self.assertEqual(controller_repair._mail_sequence_entry("user_intake")["to_role"], "project_manager")
        self.assertEqual(protocol_tables.mail_sequence_entry("user_intake")["to_role"], "project_manager")
        self.assertIn("completed", protocol_tables.RUN_TERMINAL_STATUSES)
        self.assertIn("completed", protocol_tables.terminal_statuses())

    def test_startup_boot_catalog_split_preserves_protocol_owner_boundary(self) -> None:
        catalog = startup_catalog.startup_boot_catalog()
        system_catalog = protocol_catalog.system_card_catalog()
        planning_catalog = planning_cards.planning_system_card_catalog()
        runtime_catalog = runtime_cards.runtime_system_card_catalog()
        metadata_catalog = card_metadata.system_card_metadata_catalog()

        self.assertEqual(
            catalog["startup_question_ids"],
            tuple(question["id"] for question in startup_catalog.STARTUP_QUESTIONS),
        )
        self.assertIn("record_startup_answers", catalog["boot_action_types"])
        self.assertEqual(router.BOOT_ACTIONS, startup_catalog.BOOT_ACTIONS)
        self.assertEqual(protocol_catalog.BOOT_ACTIONS, startup_catalog.BOOT_ACTIONS)
        self.assertIn("pm.route_skeleton", startup_catalog.PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS)
        self.assertEqual(
            protocol_catalog.SYSTEM_CARD_SEQUENCE,
            planning_cards.PLANNING_SYSTEM_CARD_SEQUENCE + runtime_cards.RUNTIME_SYSTEM_CARD_SEQUENCE,
        )
        self.assertEqual(system_catalog["card_count"], len(protocol_catalog.SYSTEM_CARD_SEQUENCE))
        self.assertEqual(
            system_catalog["planning_card_count"] + system_catalog["runtime_card_count"],
            system_catalog["card_count"],
        )
        self.assertEqual(planning_catalog["card_ids"][0], "reviewer.startup_fact_check")
        self.assertEqual(runtime_catalog["card_ids"][-1], "pm.closure")
        self.assertIn("pm.route_skeleton", metadata_catalog["phase_card_ids"])
        self.assertIn("reviewer.startup_fact_check", metadata_catalog["source_path_card_ids"])

    def test_startup_daemon_helpers_belong_to_owner_module(self) -> None:
        self.assertEqual(startup_daemon.ROUTER_DAEMON_LOCK_SCHEMA, "flowpilot.router_daemon_lock.v1")
        liveness = startup_daemon._router_daemon_lock_liveness(
            {
                "schema_version": startup_daemon.ROUTER_DAEMON_LOCK_SCHEMA,
                "status": "active",
                "last_tick_at": "2026-05-18T00:00:00Z",
                "stale_after_seconds": 60,
                "owner": {"pid": 0, "process_name": "boundary-test"},
            }
        )
        self.assertFalse(startup_daemon._router_daemon_lock_is_live({}))
        self.assertIn("owner_process_not_live", liveness["reasons"])
        monitor = startup_daemon._router_daemon_heartbeat_monitor(
            {"status": "active"},
            {"schema_ok": True, "status_active": True, "process_live": True, "age_seconds": 0},
            status_exists=True,
            status_ok=True,
        )
        self.assertEqual(monitor["status"], "ok")
        self.assertFalse(monitor["controller_liveness_check_required"])

    def test_dispatch_gate_helpers_belong_to_owner_module(self) -> None:
        self.assertEqual(
            dispatch_gate._dispatch_gate_target_roles({"to_role": "worker_a, project_manager"}),
            {"worker_a", "project_manager"},
        )
        self.assertEqual(
            dispatch_gate._dispatch_gate_wait_events_for_packet_record(
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
            self.assertIn(event_name, protocol_catalog.EXTERNAL_EVENTS)
        self.assertIsNone(
            router_events.handle_precheck_event(
                router,
                Path("."),
                Path("."),
                {"flags": {}, "events": []},
                "unknown_event",
                {"summary": "unknown"},
                {},
            )
        )
        self.assertFalse(
            router_events.apply_migrated_event_side_effect(
                router,
                Path("."),
                Path("."),
                {"flags": {}, "events": []},
                "unknown_event",
                {},
            )
        )

    def test_event_dispatcher_passes_router_facade_to_event_helpers(self) -> None:
        calls: list[object] = []

        def fake_precheck(received_router: object, *args: object, **kwargs: object) -> dict[str, object]:
            calls.append(received_router)
            return {"ok": True, "event": "heartbeat_or_manual_resume_requested"}

        original = router_events.handle_precheck_event
        router_events.handle_precheck_event = fake_precheck
        try:
            result = event_dispatcher._record_external_event_unchecked(
                router,
                Path("."),
                "heartbeat_or_manual_resume_requested",
                {},
            )
        finally:
            router_events.handle_precheck_event = original

        self.assertEqual(result["event"], "heartbeat_or_manual_resume_requested")
        self.assertEqual(calls, [router])

    def test_coarse_owner_bind_router_refreshes_facade_globals_without_overwriting_owner_locals(self) -> None:
        sentinel = object()
        marker_name = "_boundary_test_dynamic_marker"
        original_router_marker = getattr(router, marker_name, sentinel)
        original_owner_marker = getattr(runtime_state, marker_name, sentinel)
        original_owner_function = runtime_state.new_bootstrap_state

        try:
            setattr(router, marker_name, "first")
            runtime_state._bind_router(router)
            self.assertEqual(getattr(runtime_state, marker_name), "first")

            setattr(router, marker_name, "second")
            runtime_state._bind_router(router)
            self.assertEqual(getattr(runtime_state, marker_name), "second")
            self.assertIs(runtime_state.new_bootstrap_state, original_owner_function)
        finally:
            if original_router_marker is sentinel:
                delattr(router, marker_name)
            else:
                setattr(router, marker_name, original_router_marker)
            if original_owner_marker is sentinel:
                if hasattr(runtime_state, marker_name):
                    delattr(runtime_state, marker_name)
            else:
                setattr(runtime_state, marker_name, original_owner_marker)

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

    def test_controller_receipts_facade_exports_child_owner_symbols(self) -> None:
        for name in controller_scheduler_receipts.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(controller_scheduler_receipts, name), name)
                self.assertIs(
                    getattr(controller_scheduler, name),
                    getattr(controller_scheduler_receipts, name),
                )

    def test_packet_runtime_facade_exports_child_owner_contract_symbols(self) -> None:
        expected_owner_by_export = {
            "PacketRuntimeError": packet_runtime_schema,
            "PACKET_IDENTITY_MARKER": packet_runtime_schema,
            "RESULT_IDENTITY_MARKER": packet_runtime_schema,
            "ROLE_PACKET_SESSION_SCHEMA": packet_runtime_schema,
            "RESULT_REVIEW_SESSION_SCHEMA": packet_runtime_schema,
            "CONTROLLER_NEXT_ACTION_NOTICE_SCHEMA": packet_runtime_schema,
            "load_envelope": packet_runtime_paths,
            "validate_packet_ready_for_direct_relay": packet_runtime_relay,
            "validate_result_ready_for_reviewer_relay": packet_runtime_relay,
            "verify_controller_relay": packet_runtime_relay,
            "verify_packet_open_receipt": packet_runtime_relay,
            "verify_router_startup_release": packet_runtime_relay,
        }

        for name, owner_module in expected_owner_by_export.items():
            with self.subTest(name=name):
                self.assertIn(name, packet_runtime.__all__)
                self.assertIs(getattr(packet_runtime, name), getattr(owner_module, name))

    def test_pm_role_work_facade_exports_child_owner_symbols(self) -> None:
        for name in work_packets_pm_role.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(work_packets_pm_role, name), name)
                self.assertIs(
                    getattr(work_packets, name),
                    getattr(work_packets_pm_role, name),
                )

    def test_terminal_ledger_facade_exports_router_symbols(self) -> None:
        for name in terminal_ledger.__all__:
            with self.subTest(name=name):
                self.assertTrue(hasattr(terminal_ledger, name), name)
                self.assertTrue(callable(getattr(router, name)), name)
                self.assertTrue(callable(getattr(terminal_ledger, name)), name)

    def test_runtime_closure_external_record_contracts_are_self_validating(self) -> None:
        officer_request = {
            "request_id": "officer-1",
            "packet_id": "packet-1",
            "requested_by_role": "project_manager",
            "to_role": "process_flowguard_officer",
            "process_kind": "officer_model_report",
            "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
            "packet_type": "officer_request",
            "status": "registered",
            "strict_process_contract_binding": True,
            "required_result_next_recipient": "project_manager",
            "controller_may_read_packet_body": False,
            "process_contract_binding": {
                "process_kind": "officer_model_report",
                "packet_type": "officer_request",
                "required_result_next_recipient": "project_manager",
            },
            "packet_envelope_path": "packets/officer-1.envelope.json",
            "packet_body_path": "packets/officer-1.body.md",
            "packet_body_hash": "body-hash",
            "result_envelope_path": "results/officer-1.result.json",
            "result_body_path": "results/officer-1.result.md",
        }
        officer_result = {
            "packet_id": "packet-1",
            "completed_by_role": "process_flowguard_officer",
            "next_recipient": "project_manager",
            "result_body_path": "results/officer-1.result.md",
            "result_body_hash": "result-hash",
        }

        self.assertEqual(runtime_closure.validate_officer_request_record(officer_request), [])
        self.assertEqual(runtime_closure.validate_officer_result_record(officer_request, officer_result), [])
        lifecycle_entry = runtime_closure.officer_lifecycle_entry_from_request(
            officer_request,
            now="2026-05-18T00:00:00Z",
        )
        self.assertTrue(lifecycle_entry["validation_passed"])
        self.assertFalse(lifecycle_entry["controller_may_read_packet_body"])

        quarantine = runtime_closure.continuation_quarantine_record(
            run_id="run-current",
            run_root=".flowpilot/runs/run-current",
            current_pointer={
                "current_run_id": "run-current",
                "current_run_root": ".flowpilot/runs/run-current",
            },
            run_index={
                "runs": [
                    {
                        "run_id": "run-old",
                        "run_root": ".flowpilot/runs/run-old",
                        "status": "closed",
                    }
                ]
            },
            created_at="2026-05-18T00:00:00Z",
        )
        self.assertEqual(runtime_closure.validate_continuation_quarantine_record(quarantine), [])
        self.assertFalse(quarantine["prior_run_files_are_evidence_by_default"])

        final_report = runtime_closure.final_user_report_record(
            run_id="run-current",
            lifecycle_status="closed",
            summary_path="final_summary.md",
            summary_json_path="final_summary.json",
            summary_sha256="abc",
            displayed_to_user=True,
            written_at="2026-05-18T00:00:00Z",
        )
        self.assertEqual(runtime_closure.validate_final_user_report_record(final_report), [])
        self.assertFalse(final_report["controller_may_continue_route_work"])

        route_refresh = runtime_closure.route_display_refresh_record(
            run_id="run-current",
            display_plan_path="display_plan.json",
            route_state_snapshot_path="route_state_snapshot.json",
            route_state_snapshot_hash="snapshot-hash",
            projection_hash="projection-hash",
            route_sign_markdown_path="route_sign.md",
            route_sign_mermaid_sha256="mermaid-hash",
            display_kind="chat",
            refreshed_at="2026-05-18T00:00:00Z",
        )
        self.assertEqual(runtime_closure.validate_route_display_refresh_record(route_refresh), [])
        self.assertFalse(route_refresh["display_is_route_authority"])

    def test_route_domain_helpers_are_available_in_route_owner(self) -> None:
        self.assertTrue(callable(router_route.route_payload_from_reviewed_draft))
        self.assertTrue(callable(router_route.write_route_activation))
        self.assertTrue(callable(router_route.write_route_mutation))
        with tempfile.TemporaryDirectory(prefix="flowpilot-route-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            draft_path = run_root / "routes" / "route-001" / "flow.draft.json"
            draft_path.parent.mkdir(parents=True)
            draft_payload = {
                "route_id": "route-001",
                "nodes": [{"node_id": "node-001", "kind": "leaf"}],
            }
            draft_path.write_text(json.dumps(draft_payload), encoding="utf-8")

            class FakeRouter:
                @staticmethod
                def _current_route_draft_path(run_root_arg: Path) -> Path:
                    return run_root_arg / "routes" / "route-001" / "flow.draft.json"

                @staticmethod
                def read_json(path: Path) -> dict:
                    return json.loads(path.read_text(encoding="utf-8"))

                @staticmethod
                def project_relative(root: Path, path: Path) -> str:
                    return path.resolve().relative_to(root.resolve()).as_posix()

            route_payload, returned_draft = router_route.route_payload_from_reviewed_draft(
                FakeRouter(),
                project_root,
                run_root,
                {},
            )

            self.assertEqual(returned_draft, draft_path)
            self.assertEqual(route_payload["schema_version"], "flowpilot.route.v1")
            self.assertEqual(route_payload["reviewed_route_activation_source"], "flow.draft.json")
            self.assertEqual(route_payload["activated_from_draft_path"], ".flowpilot/runs/run-test/routes/route-001/flow.draft.json")

    def test_resume_domain_helpers_are_available_in_resume_owner(self) -> None:
        self.assertTrue(callable(router_resume.write_host_heartbeat_binding))
        self.assertTrue(callable(router_resume.append_heartbeat_tick))
        self.assertTrue(callable(router_resume.reset_resume_cycle_for_wakeup))
        flags = {
            "resume_reentry_requested": True,
            "resume_state_loaded": True,
            "role_recovery_pm_escalation_required": True,
        }
        run_state = {"flags": flags}

        router_resume.reset_resume_cycle_for_wakeup(router, run_state)

        self.assertFalse(flags["resume_reentry_requested"])
        self.assertFalse(flags["resume_state_loaded"])
        self.assertFalse(flags["role_recovery_pm_escalation_required"])

    def test_terminal_helpers_belong_to_owner_module(self) -> None:
        self.assertEqual(terminal_helpers.TERMINAL_SUMMARY_SCHEMA, "flowpilot.final_summary.v1")
        self.assertEqual(
            terminal_helpers._terminal_lifecycle_mode({"status": "running", "flags": {"run_cancelled_by_user": True}}),
            "cancelled_by_user",
        )
        self.assertEqual(
            terminal_helpers._terminal_summary_markdown_path(Path("run-root")),
            Path("run-root") / "final_summary.md",
        )


if __name__ == "__main__":
    unittest.main()
