from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class AckReturnRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_router_daemon_tick_consumes_card_ack_without_manual_next(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        while True:
            action = self.next_after_display_sync(root)
            if action["action_type"] in {
                "confirm_controller_core_boundary",
                "check_prompt_manifest",
                "inject_role_io_protocol",
                "open_current_role_agent",
                "write_startup_mechanical_audit",
                "write_display_surface_status",
            }:
                router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
                continue
            self.assertIn(action["action_type"], {"deliver_system_card", "deliver_system_card_bundle"})
            break

        self.submit_system_card_ack_without_router_next(root, action)
        before = read_json(router.run_state_path(run_root))
        self.assertEqual(before["pending_action"]["action_type"], action["action_type"])

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["tick_count"], 1)
        after = read_json(router.run_state_path(run_root))
        labels = [item["label"] for item in after["history"] if isinstance(item, dict)]
        self.assertTrue(
            {
                "router_auto_consumed_card_return_ack",
                "router_return_settlement_cleared_pending_card_bundle_wait",
            }
            & set(labels)
        )
        self.assertNotEqual((after.get("pending_action") or {}).get("action_id"), action.get("action_id"))
    def test_router_daemon_incomplete_bundle_ack_waits_without_advancing(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.release_startup_daemon_for_explicit_daemon_test(root)
        self.assert_no_startup_heartbeat_action(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "inject_role_io_protocol",
            "open_current_role_agent",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")

        role = str(action["to_role"])
        agent_id = str(action["target_agent_id"])
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
        )
        envelope = read_json(root / action["card_bundle_envelope_path"])
        receipt_refs = []
        for receipt_path in opened["read_receipt_paths"][:-1]:
            receipt = read_json(root / receipt_path)
            receipt_refs.append(
                {
                    "receipt_path": receipt_path,
                    "receipt_hash": receipt["receipt_hash"],
                    "card_id": receipt["card_id"],
                    "delivery_id": receipt["delivery_id"],
                    "delivery_attempt_id": receipt["delivery_attempt_id"],
                    "card_hash": receipt["card_hash"],
                    "opened_at": receipt["opened_at"],
                }
            )
        incomplete_ack = {
            "schema_version": card_runtime.CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
            "run_id": envelope["run_id"],
            "resume_tick_id": envelope["resume_tick_id"],
            "role_key": role,
            "agent_id": agent_id,
            "card_return_event": envelope["card_return_event"],
            "status": "acknowledged",
            "card_bundle_id": envelope["bundle_id"],
            "card_bundle_envelope_path": action["card_bundle_envelope_path"],
            "card_bundle_envelope_hash": card_runtime.stable_json_hash(envelope),
            "ack_delivery_mode": "direct_to_router",
            "submitted_to": "router",
            "controller_ack_handoff_used": False,
            "direct_router_ack_token": envelope["direct_router_ack_token"],
            "direct_router_ack_token_hash": envelope["direct_router_ack_token_hash"],
            "acknowledged_bundle": envelope["bundle_id"],
            "acknowledged_envelopes": [envelope["bundle_id"]],
            "member_card_ids": envelope["card_ids"][:-1],
            "receipt_refs": receipt_refs,
            "body_visibility": "ack_envelope_only",
            "contains_card_body": False,
            "runtime_validates_mechanics_only": True,
            "semantic_understanding_validated": False,
            "returned_at": card_runtime.utc_now(),
        }
        incomplete_ack["ack_hash"] = card_runtime.stable_json_hash(incomplete_ack)
        router.write_json(root / action["expected_return_path"], incomplete_ack)

        result = router.run_router_daemon(root, max_ticks=1, release_lock_on_exit=True)

        self.assertEqual(result["ticks"][0]["action_type"], "await_card_bundle_return_event")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["pending_action"]["action_type"], "await_card_bundle_return_event")
        self.assertTrue(state["pending_action"]["bundle_ack_incomplete"])
        self.assertEqual(state["pending_action"]["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item
            for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")
    def test_dispatch_recipient_gate_classifies_ack_only_card_as_prompt(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-ack-only-card")
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_core_card_delivered",
            summary="Deliver an ACK-only PM core card.",
            card_id="pm.core",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "deliver_system_card")
        gate = gated["dispatch_recipient_gate"]
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["work_package_class"], "ack_only_prompt")
        self.assertEqual(gate["output_events"], [])
    def test_dispatch_recipient_gate_allows_work_after_resolved_ack_only_card_wait(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-resolved-ack-only-wait")
        state = read_json(router.run_state_path(run_root))
        wait_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_core_card_ack",
            summary="Controller waits for PM core card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "delivery_attempt_id": "pm-core-attempt",
                "card_id": "pm.core",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_core.ack.json",
            },
        )
        wait_entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        wait_entry["status"] = "resolved"
        wait_entry["completed_at"] = router.utc_now()
        wait_entry["router_reconciliation_status"] = "reconciled"
        wait_entry["router_reconciliation"] = {"clearance_kind": "ack_wait_only"}
        router.write_json(root / wait_entry["action_path"], wait_entry)
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]

        action = router.make_action(
            action_type="deliver_mail",
            actor="controller",
            label="deliver_pm_mail_after_ack_only_wait",
            summary="Deliver PM mail after ACK-only card wait resolved.",
            mail_id="new-pm-mail",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)  # type: ignore[attr-defined]

        self.assertEqual(gated["action_type"], "deliver_mail")
        self.assertTrue(gated["dispatch_recipient_gate"]["passed"])
        self.assertEqual(gated["dispatch_recipient_gate"]["target_roles"], ["project_manager"])
    def test_dispatch_recipient_gate_keeps_output_work_busy_after_card_ack_only(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-output-card-ack-only")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["node_review_blocked"] = True
        state["flags"]["pm_model_miss_triage_card_delivered"] = True
        router.write_json(router.run_state_path(run_root), state)
        wait_action = router.make_action(
            action_type="await_card_return_event",
            actor="controller",
            label="controller_waits_for_pm_model_miss_triage_card_ack",
            summary="Controller waits for PM model-miss triage card ACK.",
            to_role="project_manager",
            extra={
                "waiting_for_role": "project_manager",
                "delivery_attempt_id": "pm-model-miss-triage-attempt",
                "card_id": "pm.model_miss_triage",
                "card_return_event": "pm_card_ack",
                "expected_return_path": "mailbox/outbox/card_acks/pm_model_miss_triage.ack.json",
            },
        )
        wait_entry = router._write_controller_action_entry(root, run_root, state, wait_action)  # type: ignore[attr-defined]
        wait_entry["status"] = "resolved"
        wait_entry["completed_at"] = router.utc_now()
        wait_entry["router_reconciliation_status"] = "reconciled"
        wait_entry["router_reconciliation"] = {
            "clearance_kind": "ack_wait_only",
            "ack_does_not_complete_output_bearing_work": True,
        }
        router.write_json(root / wait_entry["action_path"], wait_entry)
        router._rebuild_controller_action_ledger(root, run_root, state)  # type: ignore[attr-defined]

        route_action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_route_skeleton_phase_card_delivered",
            summary="Deliver an independent PM route card.",
            card_id="pm.route_skeleton",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, route_action)  # type: ignore[attr-defined]

        self.assertEqual(gated["action_type"], "await_role_decision")
        self.assertEqual(gated["to_role"], "project_manager")
        self.assertEqual(gated["allowed_external_events"], ["pm_records_model_miss_triage_decision"])
        gate = gated["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "pending_expected_output")
        self.assertEqual(gate["busy_reason"], "target_role_output_obligation_already_pending")
        self.assertEqual(gate["blocked_work_package_class"], "output_bearing_work_package")
