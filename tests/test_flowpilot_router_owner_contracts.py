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
import flowpilot_router_action_handlers_roles as action_handlers_roles  # noqa: E402
import flowpilot_router_artifact_validation as artifact_validation  # noqa: E402
import flowpilot_router_card_delivery as card_delivery  # noqa: E402
import flowpilot_router_child_skill_capability as child_skill_capability  # noqa: E402
import flowpilot_router_controller_ledger as controller_ledger  # noqa: E402
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

    def test_action_factory_and_dispatch_gate_external_contracts(self) -> None:
        state: dict[str, object] = {}
        action_factory_envelope.append_history(state, "router_owner_contract", {"ok": True})

        action = action_factory_envelope.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="deliver_reviewer_startup_fact",
            summary="Deliver reviewer startup fact card.",
            card_id="reviewer.startup_fact_check",
            to_role="human_like_reviewer",
        )

        with tempfile.TemporaryDirectory(prefix="flowpilot-dispatch-owner-") as tmp:
            project_root = Path(tmp)
            run_root = project_root / ".flowpilot" / "runs" / "run-test"
            run_root.mkdir(parents=True)
            run_state = {"run_id": "run-test", "flags": {}, "events": []}
            gated = action_factory_dispatch._apply_dispatch_recipient_gate(
                project_root,
                run_state,
                run_root,
                action,
            )

        gate = gated["dispatch_recipient_gate"]
        self.assertEqual(state["history"][0]["label"], "router_owner_contract")
        self.assertEqual(action["schema_version"], router.SCHEMA_VERSION)
        self.assertEqual(action["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertFalse(action["next_step_contract"]["sealed_body_reads_allowed"])
        self.assertTrue(action["controller_user_reporting_policy"]["plain_language_required"])
        self.assertTrue(action["controller_user_reporting_policy"]["speak_only_when_user_value"])
        self.assertIn(
            "quiet_patrol_continue",
            action["controller_user_reporting_policy"]["silent_by_default_for"],
        )
        self.assertEqual(
            action_factory_dispatch._dispatch_gate_output_events_for_card_id("reviewer.startup_fact_check"),
            ["reviewer_reports_startup_facts"],
        )
        self.assertFalse(
            action_factory_dispatch._dispatch_gate_action_is_ack_only_prompt(
                {"action_type": "deliver_system_card", "card_id": "reviewer.startup_fact_check"}
            )
        )
        self.assertEqual(
            action_factory_dispatch._dispatch_gate_action_work_class(
                {"action_type": "deliver_system_card", "card_id": "pm.post_ack_policy"}
            ),
            "ack_only_prompt",
        )
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["target_roles"], ["human_like_reviewer"])
        self.assertEqual(gate["work_package_class"], "output_bearing_work_package")
        self.assertEqual(gate["output_events"], ["reviewer_reports_startup_facts"])
        self.assertFalse(gate["sealed_body_reads_allowed"])
        self.assertEqual(gated["next_step_contract"]["dispatch_recipient_gate"], gate)

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
            repair_outcome = action_handlers_roles._apply_controller_repair_work_packet(
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
            action_handlers_roles._apply_controller_repair_work_packet(
                router,
                Path("."),
                Path(".flowpilot/runs/run-test"),
                {},
                {"controller_may_approve_gate": True},
                None,
            )

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
