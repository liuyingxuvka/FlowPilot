from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402
import flowpilot_router_action_factory_dispatch as action_factory_dispatch  # noqa: E402
import flowpilot_router_action_factory_envelope as action_factory_envelope  # noqa: E402
import flowpilot_router_action_handlers_basic as action_handlers_basic  # noqa: E402
import flowpilot_router_action_handlers_role_binding as action_handlers_role_binding  # noqa: E402
import flowpilot_router_action_handlers_role_misc as action_handlers_role_misc  # noqa: E402
import flowpilot_router_action_handlers_resume as action_handlers_resume  # noqa: E402
import flowpilot_router_action_handlers_roles as action_handlers_roles  # noqa: E402
import flowpilot_router_artifact_validation as artifact_validation  # noqa: E402
import flowpilot_router_card_delivery as card_delivery  # noqa: E402
import flowpilot_router_child_skill_capability as child_skill_capability  # noqa: E402
import flowpilot_router_controller_runtime as controller_runtime  # noqa: E402
import flowpilot_router_controller_runtime_apply as controller_runtime_apply  # noqa: E402
import flowpilot_router_controller_runtime_loop as controller_runtime_loop  # noqa: E402
import flowpilot_router_controller_runtime_next as controller_runtime_next  # noqa: E402
import flowpilot_router_controller_ledger as controller_ledger  # noqa: E402
import flowpilot_router_lifecycle_requests_blockers as lifecycle_request_blockers  # noqa: E402
import flowpilot_router_lifecycle_requests_fence as lifecycle_request_fence  # noqa: E402
import flowpilot_router_lifecycle_requests_reconciliation as lifecycle_request_reconciliation  # noqa: E402
import flowpilot_router_lifecycle_requests_records as lifecycle_request_records  # noqa: E402
import flowpilot_router_lifecycle_support as lifecycle_support  # noqa: E402
import flowpilot_router_startup_support as startup_support  # noqa: E402
import flowpilot_router_system_cards_delivery_single as system_cards_delivery_single  # noqa: E402
import packet_runtime  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotRouterOwnerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        action_factory_dispatch._bind_router(router)
        action_factory_envelope._bind_router(router)
        artifact_validation._bind_router(router)
        child_skill_capability._bind_router(router)
        lifecycle_request_blockers._bind_router(router)
        lifecycle_request_fence._bind_router(router)
        lifecycle_request_reconciliation._bind_router(router)
        lifecycle_request_records._bind_router(router)
        lifecycle_support._bind_router(router)
        startup_support._bind_router(router)
        system_cards_delivery_single._bind_router(router)

    def test_controller_runtime_facade_binds_loop_owner(self) -> None:
        controller_runtime._bind_router(router)
        controller_runtime_loop._bind_router(router)
        self.assertIs(controller_runtime._bound_router(), router)
        self.assertIs(controller_runtime_loop._bound_router(), router)
        self.assertIs(controller_runtime_apply._bound_router(), router)
        self.assertIs(controller_runtime_next._bound_router(), router)
        self.assertIs(controller_runtime.next_action, controller_runtime_loop.next_action)
        self.assertIs(controller_runtime_loop.next_action, controller_runtime_next.next_action)
        self.assertIs(controller_runtime_loop.apply_action, controller_runtime_apply.apply_action)
        self.assertIs(controller_runtime_loop.run_until_wait, controller_runtime_apply.run_until_wait)

    def test_router_facade_next_mail_action_targets_next_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-next-mail-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {
                "run_id": "run-test",
                "flags": {
                    "startup_mechanical_audit_written": True,
                    "startup_display_status_written": True,
                },
                "history": [],
                "pending_action": None,
                "delivered_cards": [],
                "delivered_mail": [],
            }
            action = router._next_mail_action(project_root, run_state, run_root)

        self.assertIsNotNone(action)
        self.assertEqual(action["action_type"], "check_packet_ledger")
        self.assertIs(controller_runtime_next._bound_router(), router)

    def test_action_factory_and_dispatch_gate_external_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-action-factory-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {
                "run_id": "run-test",
                "flags": {},
                "history": [],
                "pending_action": None,
                "delivered_cards": [],
                "delivered_mail": [],
            }
            action = action_factory_envelope.make_action(
                action_type="deliver_system_card",
                actor="controller",
                label="pm_core_card_delivered",
                summary="Deliver the PM core system card.",
                card_id="pm.core",
                to_role="project_manager",
            )
            gated = action_factory_dispatch._apply_dispatch_recipient_gate(
                project_root,
                run_state,
                run_root,
                action,
            )

        self.assertEqual(gated["action_type"], "deliver_system_card")
        self.assertTrue(gated["dispatch_recipient_gate"]["passed"])
        self.assertEqual(gated["dispatch_recipient_gate"]["target_roles"], ["project_manager"])

    def test_card_delivery_and_controller_ledger_external_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-card-ledger-owner-") as tmp:
            run_root = Path(tmp) / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            write_json(
                card_delivery.card_ledger_path(run_root),
                {
                    "schema_version": card_delivery.CARD_LEDGER_SCHEMA,
                    "run_id": "run-test",
                    "deliveries": [{"card_id": "pm.core"}],
                    "read_receipts": [],
                    "ack_envelopes": [],
                },
            )

            card_ledger = card_delivery.read_card_ledger(run_root, "run-test")
            return_ledger = card_delivery.read_return_event_ledger(run_root, "run-test")
            delivery_id, attempt_id = card_delivery.next_card_delivery_attempt(
                run_root,
                "run-test",
                "pm.core",
            )

        self.assertEqual(card_delivery.safe_delivery_component("pm.core/card"), "pm_core_card")
        self.assertEqual(card_ledger["schema_version"], card_delivery.CARD_LEDGER_SCHEMA)
        self.assertEqual(return_ledger["schema_version"], card_delivery.RETURN_EVENT_LEDGER_SCHEMA)
        self.assertEqual(delivery_id, "pm_core-delivery-002")
        self.assertEqual(attempt_id, "pm_core-delivery-002-attempt-001")
        self.assertEqual(card_delivery.card_return_event_for_card("pm.route_skeleton"), "pm_card_ack")
        self.assertEqual(card_delivery.card_bundle_return_event_for_role("project_manager"), "pm_card_bundle_ack")
        self.assertTrue(card_delivery.is_card_return_event_name("pm_card_bundle_ack"))

        run_root = Path(".flowpilot") / "runs" / "run-test"
        action = {"action_type": "await_role_decision", "to_role": "project_manager"}
        scheduled = controller_ledger.prepare_router_scheduled_action(
            run_root,
            {"run_id": "run-test"},
            action,
            scope_for_action=lambda item, _run_root: ("role", str(item.get("to_role") or "")),
            progress_class_for_action=controller_ledger.router_scheduler_progress_class,
            barrier_kind_for_action=controller_ledger.router_scheduler_barrier_kind,
        )

        self.assertEqual(controller_ledger.controller_action_ledger_path(run_root), run_root / "runtime" / "controller_action_ledger.json")
        self.assertEqual(scheduled["scope_kind"], "role")
        self.assertEqual(scheduled["scope_id"], "project_manager")
        self.assertEqual(scheduled["router_scheduler_progress_class"], "true_barrier")
        self.assertEqual(scheduled["router_scheduler_barrier_kind"], "await_role_decision")
        self.assertEqual(scheduled["router_daemon_tick_seconds"], controller_ledger.ROUTER_DAEMON_TICK_SECONDS)
        self.assertEqual(scheduled["run_id"], "run-test")
        self.assertTrue(scheduled["idempotency_key"])
        self.assertTrue(scheduled["router_scheduler_row_id"])

    def test_action_handler_modules_return_outcomes_and_reject_forbidden_authority(self) -> None:
        run_state: dict[str, object] = {}
        outcome = action_handlers_basic._apply_check_packet_ledger(
            router,
            Path("."),
            Path(".flowpilot/runs/run-test"),
            run_state,
            {},
            None,
        )

        self.assertEqual(outcome.result_extra, {})
        self.assertIsNone(outcome.early_return)
        self.assertTrue(run_state["ledger_check_requested"])
        self.assertEqual(run_state["ledger_check_requests"], 1)
        self.assertEqual(run_state["ledger_checks"], 1)
        with self.assertRaisesRegex(router.RouterError, "relay-only"):
            action_handlers_basic._apply_relay_only_system_card(
                router,
                Path("."),
                Path(".flowpilot/runs/run-test"),
                {},
                {},
                None,
            )

        with tempfile.TemporaryDirectory(prefix="flowpilot-repair-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            transaction_path = router._repair_transaction_path(run_root, "repair-1")
            write_json(
                transaction_path,
                {
                    "schema_version": router.REPAIR_TRANSACTION_SCHEMA,
                    "transaction_id": "repair-1",
                    "status": "assigned",
                },
            )
            repair_outcome = action_handlers_role_misc._apply_controller_repair_work_packet(
                router,
                project_root,
                run_root,
                {"run_id": "run-test"},
                {"repair_transaction_id": "repair-1", "controller_action_id": "action-1"},
                {"status": "done", "evidence": {"path": "repair.md"}},
            )
            updated_transaction = json.loads(transaction_path.read_text(encoding="utf-8"))

        self.assertEqual(repair_outcome.result_extra["repair_transaction_id"], "repair-1")
        self.assertEqual(
            repair_outcome.result_extra["controller_repair_work_packet_result"]["status"],
            "done",
        )
        self.assertEqual(updated_transaction["status"], "awaiting_recheck")
        self.assertEqual(updated_transaction["controller_repair_work_packet_result"]["controller_action_id"], "action-1")
        with self.assertRaisesRegex(router.RouterError, "cannot grant gate approval"):
            action_handlers_role_misc._apply_controller_repair_work_packet(
                router,
                Path("."),
                Path(".flowpilot/runs/run-test"),
                {},
                {"controller_may_approve_gate": True},
                None,
            )

    def test_role_binding_child_module_records_current_agent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-role-binding-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            prompt_path = run_root / "runtime_kit" / "cards" / "roles" / "project_manager.md"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("Project manager role prompt.", encoding="utf-8")
            run_state = {
                "run_id": "run-test",
                "flags": {},
                "startup_answers": {"background_collaboration_authorized": True},
            }
            payload = {
                "runtime_role_assistance_capability_status": "available",
                "current_role_agent_binding": {
                    "role_key": "project_manager",
                    "agent_id": "live-agent-current-project_manager",
                    "model_policy": router.ROLE_BINDING_MODEL_POLICY,
                    "reasoning_effort_policy": router.ROLE_BINDING_REASONING_EFFORT_POLICY,
                    "binding_open_result": "opened_for_current_packet",
                    "opened_for_run_id": "run-test",
                    "role_surface_addressable": True,
                    "current_run_binding_decision": "existing_current_agent_reused",
                },
            }

            result = action_handlers_role_binding._write_current_role_agent_binding(
                router,
                project_root,
                run_root,
                run_state,
                "project_manager",
                payload,
            )

        self.assertEqual(result["role_key"], "project_manager")
        self.assertTrue(run_state["flags"]["current_role_agent_bound_project_manager"])
        self.assertTrue(run_state["flags"]["background_collaboration_authorized"])
        self.assertEqual(result["agent_id"], "live-agent-current-project_manager")

    def test_resume_action_handler_child_module_direct_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-resume-action-handler-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {
                "schema_version": "flowpilot.run_state.v1",
                "run_id": "run-test",
                "run_root": ".flowpilot/runs/run-test",
                "flags": {},
                "events": [],
                "history": [],
                "pending_action": None,
                "startup_answers": {"background_collaboration_authorized": True},
            }

            load_outcome = action_handlers_resume._apply_load_resume_state(
                router,
                project_root,
                run_root,
                run_state,
                {},
                None,
            )
            resume_record = json.loads((run_root / "continuation" / "resume_reentry.json").read_text(encoding="utf-8"))

            self.assertEqual(load_outcome.result_extra, {})
            self.assertTrue(run_state["flags"]["resume_state_loaded"])
            self.assertTrue(resume_record["controller_only"])

            original_rehydrate = router._write_resume_role_rehydration_report
            original_recover = router._write_role_recovery_report
            try:
                def fake_rehydrate(project_root_arg, run_root_arg, run_state_arg, payload_arg):
                    write_json(run_root_arg / "continuation" / "rehydrate_marker.json", {"payload": payload_arg})
                    run_state_arg["flags"]["resume_roles_restored"] = True

                def fake_recover(project_root_arg, run_root_arg, run_state_arg, payload_arg):
                    write_json(run_root_arg / "continuation" / "recover_marker.json", {"payload": payload_arg})
                    run_state_arg["flags"]["role_recovery_report_written"] = True

                router._write_resume_role_rehydration_report = fake_rehydrate
                router._write_role_recovery_report = fake_recover

                rehydrate_outcome = action_handlers_resume._apply_rehydrate_role_bindings(
                    router,
                    project_root,
                    run_root,
                    run_state,
                    {},
                    {"rehydrated_role_bindings": []},
                )
                run_state["flags"]["role_recovery_state_loaded"] = True
                recover_outcome = action_handlers_resume._apply_recover_role_bindings(
                    router,
                    project_root,
                    run_root,
                    run_state,
                    {},
                    {"recovered_role_bindings": []},
                )
            finally:
                router._write_resume_role_rehydration_report = original_rehydrate
                router._write_role_recovery_report = original_recover

            self.assertEqual(rehydrate_outcome.result_extra, {})
            self.assertEqual(recover_outcome.result_extra, {})
            self.assertTrue((run_root / "continuation" / "rehydrate_marker.json").exists())
            self.assertTrue((run_root / "continuation" / "recover_marker.json").exists())

    def test_lifecycle_startup_owner_helpers_execute_direct_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-owner-lifecycle-contracts-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {
                "schema_version": "flowpilot.run_state.v1",
                "run_id": "run-test",
                "run_root": ".flowpilot/runs/run-test",
                "flags": {},
                "events": [],
                "history": [],
                "pending_action": None,
                "daemon_mode_enabled": True,
            }

            terminal_fence = lifecycle_request_fence._write_terminal_lifecycle_fence(
                project_root,
                run_root,
                dict(run_state),
                mode="stopped_by_user",
                event="user_requests_run_stop",
            )
            clear_blocker = lifecycle_request_reconciliation._clear_active_control_blocker_for_terminal_lifecycle(
                project_root,
                run_root,
                dict(run_state),
                mode="stopped_by_user",
                event="user_requests_run_stop",
                cleared_at="2026-05-21T00:00:00Z",
            )
            lifecycle_state = dict(run_state)
            lifecycle_request_records._write_run_lifecycle_request(
                project_root,
                run_root,
                lifecycle_state,
                event="user_requests_run_stop",
                payload={"requested_by": "user", "reason": "contract test"},
            )
            dead_end_state = dict(run_state)
            lifecycle_request_records._write_protocol_dead_end_lifecycle(
                project_root,
                run_root,
                dead_end_state,
                dead_end_path=run_root / "protocol_dead_end.json",
                reason="contract test",
            )
            exception_blocker = lifecycle_request_blockers._try_write_control_blocker_for_exception(
                project_root,
                source="contract_test",
                error_message="contract test exception",
                event="contract_test_event",
                action_type="contract_test_action",
                payload={},
            )
            lifecycle_support._write_manual_resume_binding(
                project_root,
                run_root,
                dict(run_state),
                {"recorded_by": "contract_test"},
            )
            startup_state, startup_run_root = startup_support._ensure_startup_run_state(
                project_root,
                {
                    "run_id": "run-start",
                    "run_root": ".flowpilot/runs/run-start",
                    "startup_answers": {"background_collaboration_authorized": True},
                },
            )
            with self.assertRaisesRegex(router.RouterError, "manifest check"):
                system_cards_delivery_single._commit_system_card_delivery_artifact(
                    project_root,
                    {
                        "run_id": "run-test",
                        "flags": {},
                        "delivered_cards": [],
                        "manifest_check_requested": False,
                    },
                    run_root,
                    {"card_id": "pm.core", "to_role": "project_manager"},
                )

            self.assertEqual(terminal_fence["status"], "stopped_by_user")
            self.assertIsNone(clear_blocker)
            lifecycle_record = json.loads((run_root / "lifecycle" / "run_lifecycle.json").read_text(encoding="utf-8"))
            self.assertEqual(lifecycle_record["status"], "protocol_dead_end")
            self.assertTrue(exception_blocker is None or isinstance(exception_blocker, dict))
            self.assertTrue(router._continuation_binding_path(run_root).exists())
            self.assertEqual(startup_state["run_id"], "run-start")
            self.assertEqual(startup_run_root.name, "run-start")

    def test_artifact_validation_and_child_skill_capability_external_contracts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-artifact-owner-") as tmp:
            project_root = Path(tmp)
            body_path = project_root / "body.md"
            body_path.write_text("packet body", encoding="utf-8")
            write_json(
                project_root / "packet_envelope.json",
                {
                    "schema_version": packet_runtime.PACKET_ENVELOPE_SCHEMA,
                    "packet_id": "packet-1",
                    "from_role": "project_manager",
                    "to_role": "worker",
                    "node_id": "node-1",
                    "body_path": "body.md",
                    "body_hash": hashlib.sha256(b"different").hexdigest(),
                    "body_visibility": packet_runtime.SEALED_BODY_VISIBILITY,
                    "packet_type": "user_intake",
                },
            )

            validation = artifact_validation.validate_artifact(
                project_root,
                "packet_envelope",
                "packet_envelope.json",
            )

        self.assertFalse(validation["ok"])
        self.assertEqual(validation["artifact_type"], "packet_envelope")
        self.assertEqual(validation["artifact_path"], "packet_envelope.json")
        self.assertEqual(validation["issue_count"], 1)
        self.assertEqual(validation["errors"][0]["field"], "body_hash")
        self.assertEqual(validation["next_action"], "repair_packet_envelope")

        with tempfile.TemporaryDirectory(prefix="flowpilot-child-skill-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            write_json(
                run_root / "child_skill_gate_manifest.json",
                {
                    "schema_version": "flowpilot.child_skill_gate_manifest.v1",
                    "status": "reviewed",
                },
            )
            write_json(
                run_root / "reviews" / "child_skill_gate_manifest_review.json",
                {
                    "passed": True,
                    "reported_at": "2026-05-18T00:00:00Z",
                },
            )

            child_skill_capability._sync_child_skill_manifest_review_approval(project_root, run_root)
            child_skill_capability._approve_child_skill_manifest_for_route(
                project_root,
                run_root,
                {"run_id": "run-test"},
                {"approved_by_role": "project_manager"},
            )
            write_json(run_root / "capabilities.json", {"schema_version": "flowpilot.capabilities.v1"})
            child_skill_capability._sync_capability_evidence(
                project_root,
                run_root,
                {"run_id": "run-test"},
                {"synced_by": "controller"},
            )
            manifest = json.loads((run_root / "child_skill_gate_manifest.json").read_text(encoding="utf-8"))
            approval = json.loads((run_root / "child_skill_manifest_pm_approval.json").read_text(encoding="utf-8"))
            sync = json.loads((run_root / "capabilities" / "capability_sync.json").read_text(encoding="utf-8"))

            with self.assertRaisesRegex(router.RouterError, "must be by project_manager"):
                child_skill_capability._approve_child_skill_manifest_for_route(
                    project_root,
                    run_root,
                    {"run_id": "run-test"},
                    {"approved_by_role": "controller"},
                )

        self.assertEqual(manifest["status"], "approved")
        self.assertTrue(manifest["approval"]["reviewer_passed"])
        self.assertTrue(manifest["approval"]["pm_approved_for_route"])
        self.assertEqual(approval["approved_by_role"], "project_manager")
        self.assertEqual(approval["source_paths"][0], ".flowpilot/runs/run-test/child_skill_gate_manifest.json")
        self.assertTrue(sync["pm_approved_manifest"])
        self.assertEqual(sync["synced_by"], "controller")
        self.assertIn(".flowpilot/runs/run-test/capabilities.json", sync["source_paths"])


if __name__ == "__main__":
    unittest.main()
