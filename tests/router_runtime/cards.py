from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class CardsRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_phase_card_delivery_context_includes_required_upstream_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_runtime_entry(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.product_architecture")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        source_values = set(context["source_paths"].values())
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
            source_values,
        )
        self.assertFalse(any("pm_material_understanding" in value for value in source_values))
        self.assertFalse(any("material_sufficiency" in value for value in source_values))

        self.ack_system_card_action(root, action)
        router.record_external_event(
            root,
            "pm_writes_product_function_architecture",
            {
                "user_task_map": [{"task_id": "task-001", "goal": "complete the requested project"}],
                "product_capability_map": [{"capability_id": "cap-001", "behavior": "complete requested work"}],
                "feature_decisions": [{"feature_id": "feature-001", "decision": "must"}],
                "highest_achievable_product_target": {"product_vision": "professional completion"},
                "semantic_fidelity_policy": {"silent_downgrade_forbidden": True},
                "functional_acceptance_matrix": [{"acceptance_id": "root-001"}],
            },
        )
        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "flowguard_operator.product_architecture_modelability")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/product_function_architecture.json",
            set(context["source_paths"].values()),
        )
    def test_committed_system_card_relay_can_resolve_without_apply_roundtrip(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))
        action = self.next_after_display_sync(root)
        while action["action_type"] in {"check_prompt_manifest", "open_current_role_agent"}:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.assertIn("pm.core", action["card_ids"])
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertTrue(action["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertEqual(action["controller_after_relay_policy"]["allowed_router_reentry_commands"], [])
        self.assertEqual(action["controller_after_relay_policy"]["diagnostic_router_reentry_commands"], ["next", "run-until-wait"])
        self.assertFalse(action["apply_required"])
        self.assertEqual(action["card_return_event"], "pm_card_bundle_ack")
        opened = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role="project_manager",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role="project_manager",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(path) for path in opened["read_receipt_paths"]],
        )
        next_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(bundle_pending["status"], "resolved")
        self.assertEqual(next_action["action_type"], "deliver_mail")
        self.assertEqual(next_action["mail_id"], "user_intake")
        duplicate_open = card_runtime.open_card_bundle(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role="project_manager",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role="project_manager",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(path) for path in duplicate_open["read_receipt_paths"]],
        )
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(bundle_pending["status"], "resolved")
        self.assertEqual(bundle_pending["terminal_replay_ack"]["count"], 1)
    def test_initial_pm_system_cards_are_delivered_as_same_role_bundle(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.assert_no_startup_heartbeat_action(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
            "open_current_role_agent",
            "write_startup_mechanical_audit",
            "write_display_surface_status",
        }:
            router.apply_action(root, str(action["action_type"]), self.payload_for_action(action))
            action = self.next_after_display_sync(root)
        expected_card_ids = [
            "pm.core",
            "pm.output_contract_catalog",
            "pm.role_work_request",
            "pm.phase_map",
            "pm.startup_intake",
        ]
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card_bundle")
        self.assertEqual(action["card_ids"], expected_card_ids)
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["controller_visibility"], "system_card_bundle_envelope_only")
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertFalse(action["apply_required"])
        self.assertEqual(action["card_checkin_instruction"]["command_name"], "receive-card-bundle")
        self.assertEqual(action["card_checkin_instruction"]["card_return_event"], "pm_card_bundle_ack")
        self.assertTrue((root / action["card_bundle_envelope_path"]).exists())
        envelope = read_json(root / action["card_bundle_envelope_path"])
        self.assertEqual(envelope["schema_version"], card_runtime.CARD_BUNDLE_ENVELOPE_SCHEMA)
        self.assertEqual(envelope["card_ids"], expected_card_ids)
        self.assertEqual(envelope["card_return_event"], "pm_card_bundle_ack")
        self.assertEqual(envelope["card_checkin_instruction"]["command_name"], "receive-card-bundle")
        self.assertEqual(len(envelope["cards"]), 5)
        self.ack_system_card_bundle_action(root, action)
        state = read_json(run_root / "router_state.json")
        for card_id in expected_card_ids:
            entry = next(entry for entry in router.SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id)
            self.assertTrue(state["flags"][entry["flag"]])
        self.assertGreaterEqual(state["prompt_deliveries"], 5)
        self.assertEqual([item["card_id"] for item in state["delivered_cards"][:5]], expected_card_ids)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_records = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ]
        self.assertEqual(bundle_records[0]["status"], "resolved")
        self.assert_startup_user_intake_held_by_router(root)
        next_action = self.next_after_display_sync(root)
        self.assertEqual(next_action["action_type"], "deliver_mail")
        self.assertEqual(next_action["mail_id"], "user_intake")
    def test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.assert_no_startup_heartbeat_action(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
            "check_prompt_manifest",
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
        envelope_path = root / action["card_bundle_envelope_path"]
        envelope = read_json(envelope_path)
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
        wait_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "bundle_ack_incomplete")
        self.assertEqual(bundle_pending["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        self.assertEqual(wait_action["action_type"], "await_card_bundle_return_event")
        self.assertTrue(wait_action["bundle_ack_incomplete"])
        self.assertEqual(wait_action["missing_card_ids"], [opened["cards"][-1]["card_id"]])
        card_runtime.submit_card_bundle_ack(
            root,
            envelope_path=str(action["card_bundle_envelope_path"]),
            role=role,
            agent_id=agent_id,
            receipt_paths=[str(path) for path in opened["read_receipt_paths"]],
        )
        next_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        bundle_pending = [
            item for item in return_ledger["pending_returns"]
            if isinstance(item, dict) and item.get("return_kind") == "system_card_bundle"
        ][0]
        self.assertEqual(bundle_pending["status"], "resolved")
        self.assert_startup_user_intake_held_by_router(root)
        self.assertEqual(next_action["action_type"], "deliver_mail")
        self.assertEqual(next_action["mail_id"], "user_intake")
    def test_pm_card_bundle_ack_keeps_router_owned_user_intake_sealed_until_runtime_mail_delivery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.deliver_expected_card(root, "pm.core")
        self.deliver_expected_card(root, "pm.output_contract_catalog")
        self.deliver_expected_card(root, "pm.role_work_request")
        self.deliver_expected_card(root, "pm.phase_map")
        self.deliver_expected_card(root, "pm.startup_intake")
        action = self.next_after_display_sync(root)
        state = read_json(run_root / "router_state.json")
        packet_ledger = read_json(run_root / "packet_ledger.json")
        action_dir = run_root / "runtime" / "controller_actions"
        controller_action_types = [
            read_json(path).get("action_type")
            for path in sorted(action_dir.glob("*.json"))
        ] if action_dir.exists() else []
        self.assertNotIn("check_packet_ledger", controller_action_types)
        self.assertFalse(state["flags"].get("user_intake_delivered_to_pm", False))
        self.assertEqual(state.get("mail_deliveries", 0), 0)
        self.assertFalse(packet_ledger.get("mail"))
        self.assertEqual(packet_ledger["active_packet_holder"], "router")
        self.assertEqual(packet_ledger["active_packet_status"], "router-held-startup-material")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_holder"], "router")
        self.assertEqual(packet_ledger["packets"][0]["active_packet_status"], "router-held-startup-material")
        self.assertNotIn("packet_router_release", packet_ledger["packets"][0])
        mail_envelope = read_json(run_root / "mailbox" / "outbox" / "user_intake.json")
        self.assertNotIn("router_startup_release", mail_envelope)
        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        self.assertEqual(packet_ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)

