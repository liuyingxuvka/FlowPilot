from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class CardsRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_phase_card_delivery_context_includes_required_upstream_sources(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "pm.product_architecture")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        source_values = set(context["source_paths"].values())
        self.assertIn(f"{run_root.relative_to(root).as_posix()}/pm_material_understanding.json", source_values)
        self.assertIn(f"{run_root.relative_to(root).as_posix()}/material/pm_material_understanding_payload.json", source_values)

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
        self.assertEqual(action["card_id"], "product_officer.product_architecture_modelability")
        context = action["delivery_context"]
        self.assertEqual(context["current_stage"]["current_phase"], "product_architecture")
        self.assertIn(
            f"{run_root.relative_to(root).as_posix()}/product_function_architecture.json",
            set(context["source_paths"].values()),
        )
    def test_system_card_delivery_uses_router_internal_manifest_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = self.next_after_display_sync(root)
        self.assertEqual(first["action_type"], "write_display_surface_status")
        self.assertEqual(first["next_step_contract"]["recipient_role"], "controller")
        startup_state = read_json(run_root / "router_state.json")
        self.assertTrue(startup_state["flags"]["startup_mechanical_audit_written"])
        self.assertIn(
            "write_startup_mechanical_audit",
            [item["action_type"] for item in startup_state.get("router_internal_mechanical_events", [])],
        )
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(first))

        self.complete_startup_pre_review_join(root)
        pre_reviewer_state = read_json(run_root / "router_state.json")
        pre_reviewer_delivery_count = int(pre_reviewer_state["prompt_deliveries"])
        pre_reviewer_manifest_checks = int(pre_reviewer_state["manifest_checks"])
        self.assertIn(
            "check_prompt_manifest",
            [item["action_type"] for item in pre_reviewer_state.get("router_internal_mechanical_events", [])],
        )

        second = self.next_after_display_sync(root)
        self.assertEqual(second["action_type"], "deliver_system_card")
        self.assertEqual(second["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(second["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertEqual(second["from"], "system")
        self.assertEqual(second["issued_by"], "router")
        self.assertEqual(second["delivered_by"], "controller")
        self.assertEqual(second["resource_lifecycle"], "committed_artifact")
        self.assertTrue(second["artifact_committed"])
        self.assertTrue(second["artifact_exists"])
        self.assertTrue(second["artifact_hash_verified"])
        self.assertTrue(second["ledger_recorded"])
        self.assertTrue(second["return_wait_recorded"])
        self.assertTrue(second["relay_allowed"])
        self.assertFalse(second["apply_required"])
        self.assertEqual(second["card_return_event"], "reviewer_card_ack")
        self.assertNotIn("return_event", second)
        self.assertEqual(second["card_checkin_instruction"]["command_name"], "receive-card")
        self.assertEqual(second["card_checkin_instruction"]["card_return_event"], "reviewer_card_ack")
        self.assertEqual(second["card_checkin_instruction"]["ack_submission_mode"], "direct_to_router")
        self.assertFalse(second["card_checkin_instruction"]["controller_ack_handoff_allowed"])
        self.assertEqual(second["ack_submission_mode"], "direct_to_router")
        self.assertFalse(second["controller_ack_handoff_allowed"])
        self.assertTrue(second["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertFalse(second["controller_after_relay_policy"]["foreground_wait_agent_allowed"])
        self.assertFalse(second["controller_after_relay_policy"]["foreground_role_chat_wait_allowed"])
        self.assertTrue(second["next_step_contract"]["router_ready_preempts_foreground_wait"])
        self.assertTrue(second["next_step_contract"]["controller_must_scan_daemon_before_foreground_role_wait"])
        self.assertEqual(second["next_step_contract"]["normal_router_progress_source"], "router_daemon_status_and_controller_action_ledger")
        self.assertFalse(second["next_step_contract"]["foreground_wait_agent_allowed"])
        self.assertTrue(second["direct_router_ack_token_hash"])
        self.assertTrue(second["card_checkin_instruction"]["do_not_handwrite_ack"])
        self.assertIn("--envelope-path", second["card_checkin_instruction"]["command"])
        self.assertTrue(second["auto_committed_by_router"])
        self.assertEqual(second["next_step_contract"]["resource_lifecycle"], "committed_artifact")
        self.assertTrue(second["next_step_contract"]["artifact_committed"])
        self.assertTrue(second["next_step_contract"]["relay_allowed"])
        self.assertFalse(second["next_step_contract"]["apply_required"])
        self.assertTrue((root / second["card_envelope_path"]).exists())
        envelope = read_json(root / second["card_envelope_path"])
        self.assertEqual(envelope["card_return_event"], "reviewer_card_ack")
        self.assertEqual(envelope["card_checkin_instruction"]["command_name"], "receive-card")
        self.assertEqual(envelope["direct_router_ack_token"]["submission_mode"], "direct_to_router")
        self.assertFalse(envelope["direct_router_ack_token"]["controller_ack_handoff_allowed"])
        self.assertNotIn("return_event", envelope)
        pre_apply_state = read_json(run_root / "router_state.json")
        pre_apply_prompt_ledger = read_json(run_root / "prompt_delivery_ledger.json")
        self.assertEqual(pre_apply_state["prompt_deliveries"], pre_reviewer_delivery_count)
        self.assertEqual(pre_apply_prompt_ledger["deliveries"][-1]["card_id"], "reviewer.startup_fact_check")
        context = second["delivery_context"]
        self.assertEqual(context["schema_version"], "flowpilot.live_card_context.v1")
        self.assertEqual(context["run_id"], run_root.name)
        self.assertEqual(context["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(context["to_role"], "human_like_reviewer")
        self.assertEqual(context["current_task"]["user_request_path"], f"{run_root.relative_to(root).as_posix()}/user_request.json")
        self.assertEqual(
            context["current_task"]["startup_intake_record_path"],
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
        )
        self.assertEqual(context["current_task"]["reviewer_live_review_source"], "startup_intake_record")
        self.assertFalse(context["current_task"]["controller_summary_is_task_authority"])
        self.assertIn("current_phase", context["current_stage"])
        self.assertIn("current_node_id", context["current_stage"])
        self.assertEqual(context["source_paths"]["execution_frontier"], f"{run_root.relative_to(root).as_posix()}/execution_frontier.json")
        self.assertEqual(context["source_paths"]["prompt_delivery_ledger"], f"{run_root.relative_to(root).as_posix()}/prompt_delivery_ledger.json")
        self.assertEqual(context["source_paths"]["display_surface"], f"{run_root.relative_to(root).as_posix()}/display/display_surface.json")
        self.assertEqual(
            context["source_paths"]["startup_intake_record_path"],
            f"{run_root.relative_to(root).as_posix()}/startup_intake/startup_intake_record.json",
        )
        self.assertTrue(second["reviewer_has_direct_display_evidence"])

        state = read_json(run_root / "router_state.json")
        prompt_ledger = read_json(run_root / "prompt_delivery_ledger.json")
        self.assertTrue(state["flags"]["reviewer_startup_fact_check_card_delivered"])
        self.assertEqual(state["manifest_checks"], pre_reviewer_manifest_checks)
        self.assertEqual(state["prompt_deliveries"], pre_reviewer_delivery_count)
        action_dir = run_root / "runtime" / "controller_actions"
        controller_action_types = [
            read_json(path).get("action_type")
            for path in sorted(action_dir.glob("*.json"))
        ] if action_dir.exists() else []
        self.assertNotIn("check_prompt_manifest", controller_action_types)
        self.assertNotIn("write_startup_mechanical_audit", controller_action_types)
        self.assertEqual(state["delivered_cards"][-1]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(state["delivered_cards"][-1]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(prompt_ledger["deliveries"][-1]["delivery_context"]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(second["delivery_mode"], "envelope_only_v2")
        self.assertEqual(second["controller_visibility"], "system_card_envelope_only")
        self.assertFalse(second["sealed_body_reads_allowed"])
        self.assertNotIn(second["body_path"], second["allowed_reads"])
        self.assertEqual(second["role_io_protocol_hash"], read_json(run_root / "role_io_protocol_ledger.json")["protocol_hash"])
        self.assertTrue((root / second["role_io_protocol_receipt_path"]).exists())
        self.assertTrue((root / second["card_envelope_path"]).exists())
        card_ledger = read_json(run_root / "card_ledger.json")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertEqual(card_ledger["deliveries"][-1]["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(card_ledger["deliveries"][-1]["role_io_protocol_receipt_hash"], second["role_io_protocol_receipt_hash"])
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == second.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["card_return_event"], "reviewer_card_ack")
        self.assertNotIn("return_event", reviewer_pending)

        with self.assertRaisesRegex(router.RouterError, "relay-only"):
            router.apply_action(root, "deliver_system_card")
        relay_action = self.next_after_display_sync(root)
        self.assertEqual(relay_action["action_type"], "deliver_system_card")
        self.assertEqual(relay_action["card_envelope_path"], second["card_envelope_path"])
        self.assertTrue(relay_action["relay_allowed"])
        self.assertTrue(relay_action["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertFalse(relay_action["controller_after_relay_policy"]["foreground_role_chat_wait_allowed"])
        blocked_report = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_before_card_ack",
                self.startup_fact_report_body(root),
            ),
        )
        self.assertFalse(blocked_report["ok"])
        self.assertTrue(blocked_report["report_quarantined"])
        self.assertTrue(blocked_report["recoverable"])
        with self.assertRaisesRegex(router.RouterError, "retired record-event ACK path is disabled"):
            router.record_external_event(root, "reviewer_card_ack")

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(second["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(second["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(second["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(second["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        with self.assertRaisesRegex(router.RouterError, "retired record-event ACK path is disabled"):
            router.record_external_event(root, "reviewer_card_ack")
        next_action = self.next_after_display_sync(root)
        self.assertNotEqual(next_action["action_type"], "check_card_return_event")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == second.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")
    def test_committed_system_card_relay_can_resolve_without_apply_roundtrip(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "write_display_surface_status")
        self.assertIn("write_startup_mechanical_audit", self.router_internal_action_types(root))
        router.apply_action(root, "write_display_surface_status", self.payload_for_action(action))

        self.complete_startup_pre_review_join(root)

        action = self.next_after_display_sync(root)
        self.assertIn("check_prompt_manifest", self.router_internal_action_types(root))
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        self.assertTrue(action["artifact_committed"])
        self.assertTrue(action["relay_allowed"])
        self.assertTrue(action["controller_after_relay_policy"]["router_ready_preempts_foreground_wait"])
        self.assertEqual(action["controller_after_relay_policy"]["allowed_router_reentry_commands"], [])
        self.assertEqual(action["controller_after_relay_policy"]["diagnostic_router_reentry_commands"], ["next", "run-until-wait"])
        self.assertFalse(action["apply_required"])
        self.assertEqual(action["card_return_event"], "reviewer_card_ack")

        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )

        next_action = self.next_after_display_sync(root)
        return_ledger = read_json(run_root / "return_event_ledger.json")
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")
        self.assertNotEqual(next_action["action_type"], "check_card_return_event")

        duplicate_open = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role="human_like_reviewer",
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(duplicate_open["read_receipt_path"])],
        )
        return_ledger = read_json(run_root / "return_event_ledger.json")
        reviewer_pending = [
            item
            for item in return_ledger["pending_returns"]
            if item.get("delivery_attempt_id") == action.get("delivery_attempt_id")
        ][0]
        self.assertEqual(reviewer_pending["status"], "resolved")
        self.assertEqual(reviewer_pending["terminal_replay_ack"]["count"], 1)
        self.assertIsNone(
            router._pending_card_return_blocker_for_event(
                run_root,
                run_root.name,
                "pm_issues_material_and_capability_scan_packets",
                read_json(router.run_state_path(run_root)),
            )
        )
    def test_record_external_event_quarantines_invalid_same_role_card_ack_report(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        open_result = card_runtime.open_card(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
        )
        card_runtime.submit_card_ack(
            root,
            envelope_path=str(action["card_envelope_path"]),
            role=str(action["to_role"]),
            agent_id=str(action["target_agent_id"]),
            receipt_paths=[str(open_result["read_receipt_path"])],
        )
        ack_path = root / action["expected_return_path"]
        ack = read_json(ack_path)
        ack["role_key"] = "project_manager"
        ack["ack_hash"] = card_runtime.stable_json_hash(ack)
        router.write_json(ack_path, ack)

        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["report_quarantined"])
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["startup_fact_reported"])
        self.assertEqual(state["pending_action"]["action_type"], "check_card_return_event")
        return_ledger = read_json(run_root / "return_event_ledger.json")
        self.assertNotEqual(return_ledger["pending_returns"][0].get("status"), "resolved")
    def test_initial_pm_system_cards_are_delivered_as_same_role_bundle(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
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
        self.assertEqual(next_action["action_type"], "deliver_system_card")
        self.assertEqual(next_action["card_id"], "reviewer.startup_fact_check")
    def test_incomplete_system_card_bundle_ack_waits_for_missing_receipts_then_recovers(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        self.apply_startup_heartbeat_if_requested(root)
        action = self.next_after_display_sync(root)
        while action["action_type"] in {
            "confirm_controller_core_boundary",
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
        first_three_receipts = opened["read_receipt_paths"][:-1]
        receipt_refs = []
        for receipt_path in first_three_receipts:
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
        self.assertEqual(next_action["action_type"], "deliver_system_card")
        self.assertEqual(next_action["card_id"], "reviewer.startup_fact_check")
    def test_pm_card_bundle_ack_keeps_router_owned_user_intake_sealed_until_activation(self) -> None:
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
        self.assertNotIn("deliver_mail", controller_action_types)
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
        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.startup_fact_check")
        self.assertEqual(packet_ledger["schema_version"], packet_runtime.PACKET_LEDGER_SCHEMA)
    def test_missing_system_card_ack_wait_reminds_original_envelope_without_duplicate_delivery(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        action = self.deliver_startup_fact_check_card_without_ack(root)
        result = router.record_external_event(
            root,
            "reviewer_reports_startup_facts",
            self.role_report_envelope(
                root,
                "startup/reviewer_startup_fact_report_pre_ack_reminder",
                self.startup_fact_report_body(root),
            ),
        )

        self.assertFalse(result["ok"])
        state = read_json(router.run_state_path(run_root))
        wait = state["pending_action"]
        self.assertEqual(wait["action_type"], "await_card_return_event")
        self.assertEqual(wait["missing_ack_recovery"], "remind_target_role_to_ack_original_committed_card")
        self.assertEqual(wait["reminder_target"], "original_committed_card")
        self.assertFalse(wait["duplicate_system_card_delivery_allowed"])
        self.assertTrue(wait["reissue_allowed_only_if_original_invalid_lost_stale_or_role_replaced"])
        self.assertEqual(wait["original_envelope_path"], action["card_envelope_path"])
        self.assertEqual(wait["original_expected_return_path"], action["expected_return_path"])
        self.assertTrue(wait["target_role_ack_reminder_allowed"])
        self.assertEqual(wait["controller_delivery_fact"]["controller_delivery_fact_status"], "controller_delivery_fact_unrecorded")
        self.assertTrue(wait["ack_is_read_receipt_only"])
        self.assertTrue(wait["target_work_completion_evidence_required_separately"])
        return_ledger = read_json(run_root / "return_event_ledger.json")
        scope = return_ledger["pending_returns"][0]["ack_clearance_scope"]
        self.assertIn("gate_or_node_boundary_transition", scope["required_before"])
        self.assertIn("formal_work_packet_relay_to_target_role", scope["required_before"])
