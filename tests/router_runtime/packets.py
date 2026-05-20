from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class PacketsRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_material_work_packet_records_target_ack_preflight_passed(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.apply_next_non_card_action(root)
        action = router.next_action(root)
        self.assertEqual(action["card_id"], "pm.material_scan")
        self.ack_system_card_action(root, action)
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "relay_material_scan_packets")
        preflight = action["formal_work_packet_ack_preflight"]
        self.assertTrue(preflight["passed"])
        self.assertEqual(preflight["target_roles"], ["worker_a", "worker_b"])
        self.assertEqual(preflight["pending_return_count"], 0)
        self.assertTrue(action["ack_is_read_receipt_only"])
        self.assertTrue(action["target_work_completion_evidence_required_separately"])
    def test_material_scan_accepts_file_backed_packet_body_and_updates_frontier(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            self.material_scan_file_backed_payload(root),
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "material_scan")
        self.assertIsNone(frontier["active_node_id"])
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        packet = packet_runtime.load_envelope(root, material_index["packets"][0]["packet_envelope_path"])
        self.assertEqual(packet["packet_type"], "material_scan")
        self.assertFalse(packet["is_current_node"])
        self.assertEqual(packet["expected_result_body_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["write_target_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["result_write_target"]["result_body_path"], material_index["packets"][0]["result_body_path"])
        self.assertEqual(packet["output_contract"]["expected_result_body_path"], material_index["packets"][0]["result_body_path"])
        packet_body = (root / packet["body_path"]).read_text(encoding="utf-8")
        self.assertIn(material_index["packets"][0]["result_body_path"], packet_body)
    def test_record_event_accepts_material_scan_envelope_ref_with_packets(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        envelope, envelope_path, envelope_hash = self.material_scan_event_envelope(root)

        result = router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {"event_envelope_ref": {"path": envelope_path, "hash": envelope_hash}},
        )

        self.assertTrue(result["ok"])
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        self.assertEqual(material_index["written_by_role"], "project_manager")
        self.assertEqual(material_index["packets"][0]["packet_id"], envelope["packets"][0]["packet_id"])
        self.assertTrue((root / material_index["packets"][0]["packet_envelope_path"]).exists())
    def test_record_event_rejects_manual_material_scan_payload_with_hidden_packets(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.deliver_expected_card(root, "pm.material_scan")
        payload = {"event_envelope": self.material_scan_event_envelope(root)[0]}

        with self.assertRaisesRegex(router.RouterError, "payload\\.packets"):
            router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", payload)
    def test_material_scan_packet_and_result_relays_combine_ledger_check(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())

        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_material_scan_packets")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])

        router.apply_action(root, "relay_material_scan_packets")

        state_after_packets = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_packets["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after_packets["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after_packets.get("ledger_check_requested"))
        self.assertTrue(state_after_packets["flags"]["material_scan_packets_relayed"])

        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path, result_text="material scan result")
        router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        router.record_external_event(root, "worker_scan_results_returned")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])

        router.apply_action(root, "relay_material_scan_results_to_pm")

        state_after_results = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after_results["ledger_checks"], ledger_checks_before + 2)
        self.assertEqual(state_after_results["ledger_check_requests"], ledger_requests_before + 2)
        self.assertFalse(state_after_results.get("ledger_check_requested"))
        self.assertTrue(state_after_results["flags"]["material_scan_results_relayed_to_pm"])

        index = read_json(material_index_path)
        relayed_result = packet_runtime.load_envelope(root, index["packets"][0]["result_envelope_path"])
        self.assertEqual(relayed_result["controller_relay"]["relayed_to_role"], "project_manager")
        self.assertFalse(relayed_result["controller_relay"]["body_was_read_by_controller"])
    def test_material_scan_packet_body_event_requires_packet_ledger_open_receipt(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(root, "pm_issues_material_and_capability_scan_packets", self.material_scan_payload())
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        index = read_json(material_index_path)
        envelope = packet_runtime.load_envelope(root, index["packets"][0]["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])

        ledger_path = run_root / "packet_ledger.json"
        ledger = read_json(ledger_path)
        packet_record = next(record for record in ledger["packets"] if record.get("packet_id") == envelope["packet_id"])
        packet_record.pop("packet_body_opened_by_role", None)
        packet_record["packet_body_opened_after_controller_relay_check"] = False
        router.write_json(ledger_path, ledger)

        with self.assertRaisesRegex(router.RouterError, "ledger open receipt") as raised:
            router.record_external_event(root, "worker_scan_packet_bodies_delivered_after_dispatch")
        blocker = raised.exception.control_blocker
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "worker_a")
        self.assertEqual(blocker["responsible_role_for_reissue"], "worker_a")
        self.assertFalse(blocker["pm_decision_required"])
    def test_current_node_direct_relay_blocks_missing_output_contract(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-dispatch-block",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-dispatch-block", "packet_envelope_path": packet_path},
        )
        envelope_path = root / packet_path
        envelope = read_json(envelope_path)
        envelope.pop("output_contract", None)
        envelope.pop("output_contract_id", None)
        router.write_json(envelope_path, envelope)

        with self.assertRaisesRegex(router.RouterError, "missing_output_contract"):
            self.apply_until_action(root, "relay_current_node_packet")
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["current_node_packet_relayed"])
    def test_formal_work_packet_ack_preflight_blocks_target_pending_card_ack(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        pending_return = {
            "card_return_event": "worker_card_ack",
            "status": "pending",
            "card_id": "worker.test",
            "delivery_id": "worker-test-delivery",
            "delivery_attempt_id": "worker-test-delivery-attempt",
            "target_role": "worker_a",
            "target_agent_id": "agent-worker-a",
            "card_envelope_path": f"{run_root.relative_to(root).as_posix()}/mailbox/system_cards/worker-test.json",
            "card_envelope_hash": "0" * 64,
            "expected_receipt_path": f"{run_root.relative_to(root).as_posix()}/runtime_receipts/card_reads/worker-test.receipt.json",
            "expected_return_path": f"{run_root.relative_to(root).as_posix()}/mailbox/outbox/card_acks/worker-test.ack.json",
            "ack_clearance_scope": {
                "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
                "target_role": "worker_a",
                "required_before": [
                    "gate_or_node_boundary_transition",
                    "formal_work_packet_relay_to_target_role",
                ],
                "ack_is_read_receipt_only": True,
                "target_work_completion_evidence_required_separately": True,
            },
        }
        ledger_path = run_root / "return_event_ledger.json"
        ledger = read_json(ledger_path) if ledger_path.exists() else {"pending_returns": [], "completed_returns": []}
        ledger.setdefault("pending_returns", []).append(pending_return)
        router.write_json(ledger_path, ledger)
        packet_action = router.make_action(
            action_type="relay_material_scan_packets",
            actor="controller",
            label="test_material_packet_relay",
            summary="Relay test material packet.",
            to_role="worker_a",
            extra={"postcondition": "material_scan_packets_relayed"},
        )

        blocked = router._apply_formal_work_packet_ack_preflight(root, state, run_root, packet_action)

        self.assertEqual(blocked["action_type"], "await_card_return_event")
        self.assertEqual(blocked["ack_clearance_reason"], "formal_work_packet_preflight")
        self.assertEqual(blocked["blocked_formal_work_packet"]["action_type"], "relay_material_scan_packets")
        self.assertFalse(blocked["formal_work_packet_ack_preflight"]["passed"])
        self.assertEqual(blocked["formal_work_packet_ack_preflight"]["pending_return_count"], 1)
        self.assertEqual(blocked["missing_ack_recovery"], "confirm_or_reissue_controller_delivery_before_target_ack_reminder")
        self.assertFalse(blocked["target_role_ack_reminder_allowed"])
        self.assertEqual(blocked["controller_delivery_fact"]["controller_delivery_fact_status"], "committed_artifact_missing_or_invalid")
        self.assertFalse(blocked["duplicate_system_card_delivery_allowed"])
    def test_mail_delivery_receipt_waits_for_active_packet_ledger_writer(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        state = read_json(router.run_state_path(run_root))
        state["ledger_check_requested"] = True
        action = {
            "action_type": "deliver_mail",
            "mail_id": "user_intake",
            "to_role": "project_manager",
            "allowed_reads": [self.rel(root, run_root / "mailbox" / "outbox" / "user_intake.json")],
        }
        payload = {
            "mail_id": "user_intake",
            "packet_id": "user_intake",
            "packet_envelope_path": str(action["allowed_reads"][0]),
            "delivered_to_role": "project_manager",
            "delivery_confirmed": True,
        }
        lock_path = run_root / "packet_ledger.json.write.lock"
        lock_path.write_text(json.dumps({"created_at": router.utc_now()}, sort_keys=True), encoding="utf-8")

        with self.assertRaises(router.RouterLedgerWriteInProgress):
            router._fold_mail_delivery_postcondition(  # type: ignore[attr-defined]
                root,
                run_root,
                state,
                action,
                payload,
                source="test_active_writer",
            )

        self.assertIsNone(state.get("active_control_blocker"))
        self.assertFalse(state["flags"].get("user_intake_delivered_to_pm", False))
    def test_current_node_packet_relay_uses_router_direct_dispatch(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-without-plan",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        with self.assertRaises(router.RouterError):
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {
                    "packet_id": "node-packet-without-plan",
                    "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json"),
                },
            )

        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-001",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-001", "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json")},
        )
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(self.run_root_for(root))
        self.assertEqual(resume_next["controller_next_action"], "relay_packet_envelope_to_recorded_recipient")
        self.assertEqual(resume_next["next_recipient_role"], "worker_a")

        run_root = self.run_root_for(root)
        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_current_node_packet")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        router.apply_action(root, "relay_current_node_packet")

        state_after = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after.get("ledger_check_requested"))
        envelope = read_json(root / packet["body_path"].replace("packet_body.md", "packet_envelope.json"))
        self.assertEqual(envelope["controller_relay"]["relayed_to_role"], "worker_a")
        self.assertFalse(envelope["controller_relay"]["body_was_read_by_controller"])
        lease = self.active_holder_lease_for_packet(root, "node-packet-001")
        self.assertEqual(lease["holder_role"], "worker_a")
        self.assertEqual(lease["holder_agent_id"], f"agent-{run_root.name}-worker_a")
        self.assertEqual(lease["route_version"], 1)
        self.assertEqual(lease["frontier_version"], 1)
    def test_current_node_worker_packet_requires_active_child_skill_binding_projection(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)

        active_bindings = [
            {
                "binding_id": "frontend-design:node-001:implementation",
                "source_skill": "frontend-design",
                "source_path": "skills/frontend-design/SKILL.md",
                "referenced_paths": ["skills/frontend-design/references/ui.md"],
                "applies_to_this_node": True,
                "node_slice_scope": "current node UI implementation",
                "applies_to_packet_ids": ["node-packet-bound"],
                "must_open_source_skill": True,
                "selected_standard_ids": ["frontend-design.verify.rendered-qa"],
                "stricter_than_pm_packet": True,
                "precedence_rule": "PM packet is the minimum floor; stricter child-skill requirements apply.",
                "result_evidence_required": True,
                "reviewer_check_required": True,
            }
        ]
        self.deliver_current_node_cards(root, active_child_skill_bindings=active_bindings)
        run_root = self.run_root_for(root)
        plan = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json")
        self.assertEqual(plan["active_child_skill_bindings"], active_bindings)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-missing-binding",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        with self.assertRaisesRegex(router.RouterError, "active child skill bindings"):
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {"packet_id": "node-packet-missing-binding", "packet_envelope_path": packet_path},
            )

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-bound",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={
                "route_version": 1,
                "active_child_skill_bindings": active_bindings,
                "child_skill_use_instruction_written": True,
                "active_child_skill_source_paths_allowed": [
                    "skills/frontend-design/SKILL.md",
                    "skills/frontend-design/references/ui.md",
                ],
            },
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {"packet_id": "node-packet-bound", "packet_envelope_path": packet_path},
        )
        grant = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_write_grant.json")
        self.assertTrue(grant["active_child_skill_bindings_declared"])
        self.assertEqual(
            grant["active_child_skill_source_paths"],
            [
                "skills/frontend-design/SKILL.md",
                "skills/frontend-design/references/ui.md",
            ],
        )
    def test_current_node_completion_requires_reviewer_passed_packet_audit(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-002",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-002", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")

        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-002",
            result_body_text="reviewable result",
        )

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-002", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_agent_a_1",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker_a"},
                },
            ),
        )
        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")

        current = read_json(root / ".flowpilot" / "current.json")
        run_root = root / current["current_run_root"]
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "node_completed_by_pm")
        self.assertIn("node-001", frontier["completed_nodes"])

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")
    def test_unready_leaf_cannot_receive_current_node_packet(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "leaf-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "leaf-001",
                    "nodes": [
                        {
                            "node_id": "leaf-001",
                            "node_kind": "leaf",
                            "status": "active",
                            "title": "Unready leaf",
                        }
                    ],
                },
            },
        )
        self.deliver_current_node_cards(
            root,
            leaf_readiness_gate={
                "status": "fail",
                "single_outcome": False,
                "worker_executable_without_replanning": False,
                "proof_defined": False,
                "dependency_boundary_defined": True,
                "failure_isolation_defined": True,
                "over_decomposition_checked": True,
            },
        )
        packet = packet_runtime.create_packet(
            root,
            packet_id="unready-leaf-packet",
            from_role="project_manager",
            to_role="worker_a",
            node_id="leaf-001",
            body_text="unready leaf work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "unready-leaf-packet", "packet_envelope_path": packet_path})
    def test_current_node_result_relay_combines_ledger_check_with_relay(self) -> None:
        root = self.make_project()
        run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-combined-result-relay",
            deliver_review_card=False,
            record_result_return=False,
        )
        state_before = read_json(router.run_state_path(run_root))
        ledger_checks_before = int(state_before.get("ledger_checks", 0))
        ledger_requests_before = int(state_before.get("ledger_check_requests", 0))

        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {
                "packet_id": "node-packet-combined-result-relay",
                "result_envelope_path": result_path,
            },
        )
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        self.assertTrue(action["combined_ledger_check_and_relay"])
        self.assertTrue(action["ledger_check_receipt_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        self.assertTrue(any(path.endswith("packet_ledger.json") for path in action["allowed_reads"]))
        self.assertTrue(any(path.endswith("packet_ledger.json") for path in action["allowed_writes"]))

        router.apply_action(root, "relay_current_node_result_to_pm")

        state_after = read_json(router.run_state_path(run_root))
        self.assertEqual(state_after["ledger_checks"], ledger_checks_before + 1)
        self.assertEqual(state_after["ledger_check_requests"], ledger_requests_before + 1)
        self.assertFalse(state_after.get("ledger_check_requested"))
        self.assertTrue(state_after["flags"]["current_node_result_relayed_to_pm"])

        relayed_result = packet_runtime.load_envelope(root, result_path)
        self.assertEqual(relayed_result["controller_relay"]["relayed_to_role"], "project_manager")
        self.assertFalse(relayed_result["controller_relay"]["body_was_read_by_controller"])
    def test_current_node_packet_and_result_accept_safe_envelope_aliases(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-aliases",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        packet_file = root / packet_path
        packet_envelope = read_json(packet_file)
        packet_envelope["packet_body_path"] = packet_envelope.pop("body_path")
        packet_envelope["packet_body_hash"] = packet_envelope.pop("body_hash")
        packet_file.write_text(json.dumps(packet_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-aliases", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        relayed_packet = packet_runtime.load_envelope(root, packet_path)
        self.assertIn("body_path", relayed_packet)
        agent_id, result_path = self.submit_current_node_result_via_active_holder(
            root,
            result_body_text="reviewable result",
            packet_id="node-packet-aliases",
        )
        result_file = root / result_path
        result_envelope = read_json(result_file)
        result_envelope["body_path"] = result_envelope.pop("result_body_path")
        result_envelope["body_hash"] = result_envelope.pop("result_body_hash")
        result_envelope["to_role"] = result_envelope.pop("next_recipient")
        result_file.write_text(json.dumps(result_envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-aliases", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        relayed_result = packet_runtime.load_envelope(root, result_path)
        self.assertIn("result_body_path", relayed_result)
        self.assertEqual(relayed_result["next_recipient"], "project_manager")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_aliases",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_id: "worker_a"},
                },
            ),
        )
    def test_current_node_result_decision_requires_review_card_after_result_relay(self) -> None:
        root = self.make_project()
        _, _, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-review-card-required",
            deliver_review_card=False,
        )

        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_before_card",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "passed": True,
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )
        with self.assertRaisesRegex(router.RouterError, "reviewer_worker_result_card_delivered"):
            router.record_external_event(root, "current_node_reviewer_blocks_result")

        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_after_card",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )
    def test_router_packet_audit_rejection_routes_pm_repair_decision(self) -> None:
        root = self.make_project()
        _run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-wrong-role",
            completed_by_role="worker_b",
            completed_by_agent_id="agent-worker-b",
            record_result_return=False,
        )

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "worker_current_node_result_returned",
                {"packet_id": "node-packet-wrong-role", "result_envelope_path": result_path},
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "pm_repair_decision_required")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertTrue(blocker["pm_decision_required"])
        saved = read_json(self.control_blocker_path(root, blocker))
        self.assertIn("project_manager", saved["controller_instruction"])
        self.assertIn("contact the worker directly", " ".join(saved["controller_forbidden_actions"]))
        self.assertNotIn("error_message", saved)
        self.assertTrue((root / saved["sealed_repair_packet_path"]).exists())

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["handling_lane"], "pm_repair_decision_required")
        self.assertNotIn("controller_delivery_body", action)
        router.apply_action(root, "handle_control_blocker")

        router.record_external_event(
            root,
            "pm_records_control_blocker_repair_decision",
            self.role_decision_envelope(
                root,
                "control_blocks/wrong_role_pm_repair_decision",
                self.pm_control_blocker_decision_body(blocker["blocker_id"], rerun_target="worker_current_node_result_returned"),
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertEqual(state["active_control_blocker"]["blocker_id"], blocker["blocker_id"])
        self.assertEqual(state["active_control_blocker"]["pm_repair_decision_status"], "recorded")
        self.assertIn("worker_current_node_result_returned", state["active_control_blocker"]["allowed_resolution_events"])
        self.assertIn("repair_transaction_id", state["active_control_blocker"])
        self.assertEqual(
            set(state["active_control_blocker"]["repair_outcome_table"]),
            {"success", "blocker", "protocol_blocker"},
        )
        self.assertTrue((self.run_root_for(root) / "control_blocks" / f"{blocker['blocker_id']}.pm_repair_decision.json").exists())
        transaction_path = root / state["active_control_blocker"]["repair_transaction_path"]
        self.assertTrue(transaction_path.exists())
        transaction = read_json(transaction_path)
        self.assertEqual(transaction["status"], "committed")
        self.assertEqual(transaction["plan_kind"], "role_reissue")
    def test_pm_repair_decision_rejects_parent_repair_targeting_current_node_packet(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {
                "route_id": "route-001",
                "active_node_id": "parent-001",
                "route_version": 1,
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "parent-001",
                    "nodes": [
                        {
                            "node_id": "parent-001",
                            "status": "active",
                            "title": "Parent node",
                            "child_node_ids": ["child-001"],
                        },
                        {"node_id": "child-001", "status": "planned", "title": "Child node"},
                    ],
                },
            },
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["node_acceptance_plan_reviewer_passed"] = True
        router.save_run_state(run_root, state)
        blocker = router._write_control_blocker(  # type: ignore[attr-defined]
            root,
            run_root,
            state,
            source="test",
            error_message="parent backward replay repair cannot jump to leaf current-node packet registration",
            event="pm_records_parent_segment_decision",
            payload={"decision_path": ".flowpilot/runs/test/decisions/parent.json"},
        )
        self.assertTrue(self.handle_pending_control_blocker(root))

        with self.assertRaisesRegex(router.RouterError, "pm_registers_current_node_packet: event is incompatible with parent/module active node"):
            router.record_external_event(
                root,
                "pm_records_control_blocker_repair_decision",
                self.role_decision_envelope(
                    root,
                    "control_blocks/parent_bad_rerun_pm_repair_decision",
                    self.pm_control_blocker_decision_body(
                        blocker["blocker_id"],
                        rerun_target="pm_registers_current_node_packet",
                    ),
                ),
            )

        original = read_json(self.control_blocker_path(root, blocker))
        self.assertNotIn("pm_repair_rerun_target", original)
    def test_material_scan_existing_results_reconcile_before_stale_wait(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-scan-reconcile-a",
                        "to_role": "worker_a",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-scan-reconcile-b",
                        "to_role": "worker_b",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        lease_a = self.active_holder_lease_for_packet(root, "material-scan-reconcile-a")
        lease_b = self.active_holder_lease_for_packet(root, "material-scan-reconcile-b")
        self.assertEqual(lease_a["holder_role"], "worker_a")
        self.assertEqual(lease_b["holder_role"], "worker_b")
        material_index_path = run_root / "material" / "material_scan_packets.json"
        self.open_packets_and_write_results(root, material_index_path)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_material_scan_results_to_pm")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["worker_packets_delivered"])
        self.assertTrue(state["flags"]["worker_scan_results_returned"])
        self.assertTrue(
            any(
                item.get("event") == "worker_scan_results_returned"
                and item.get("reconciled_by_router") is True
                for item in state["events"]
                if isinstance(item, dict)
            )
        )
    def test_material_scan_partial_batch_status_names_missing_role(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-scan-partial-a",
                        "to_role": "worker_a",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-scan-partial-b",
                        "to_role": "worker_b",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")
        material_index = read_json(run_root / "material" / "material_scan_packets.json")
        for record in material_index["packets"]:
            envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
            packet_runtime.read_packet_body_for_role(root, envelope, role=envelope["to_role"])
            if envelope["to_role"] == "worker_a":
                packet_runtime.write_result(
                    root,
                    packet_envelope=envelope,
                    completed_by_role="worker_a",
                    completed_by_agent_id="worker-a-agent",
                    result_body_text="worker A material scan result",
                    next_recipient="project_manager",
                )

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["label"], "controller_waits_for_remaining_material_scan_batch_results")
        self.assertEqual(action["to_role"], "worker_b")
        self.assertEqual(action["allowed_external_events"], ["worker_scan_results_returned"])

        batch_ref = read_json(run_root / "packet_batches" / "active_material_scan.json")
        batch = read_json(root / batch_ref["batch_path"])
        self.assertEqual(batch["counts"]["results_returned"], 1)
        self.assertEqual(batch["member_status"]["returned_roles"], ["worker_a"])
        self.assertEqual(batch["member_status"]["missing_roles"], ["worker_b"])
        status = read_json(run_root / "display" / "current_status_summary.json")
        partial = status["packet"]["active_batch"]["active_partial_batches"][0]
        self.assertEqual(partial["missing_roles"], ["worker_b"])
        self.assertEqual(partial["returned_roles"], ["worker_a"])
        self.assertEqual(status["current_work"]["source"], "packet_batch_member_status")
        self.assertEqual(status["current_work"]["owner_key"], "worker_b")
        self.assertEqual(status["current_work"]["diagnostics"]["missing_roles"], ["worker_b"])

    def test_material_scan_full_batch_wait_current_work_names_all_missing_roles(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)

        self.deliver_expected_card(root, "pm.material_scan")
        router.record_external_event(
            root,
            "pm_issues_material_and_capability_scan_packets",
            {
                "packets": [
                    {
                        "packet_id": "material-scan-wait-all-a",
                        "to_role": "worker_a",
                        "body_text": "Inspect local materials.",
                    },
                    {
                        "packet_id": "material-scan-wait-all-b",
                        "to_role": "worker_b",
                        "body_text": "Inspect repository state.",
                    },
                ]
            },
        )
        self.apply_next_packet_action(root, "relay_material_scan_packets")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        status = read_json(run_root / "display" / "current_status_summary.json")
        batch = status["packet"]["active_batch"]["batches"][0]
        self.assertEqual(batch["missing_roles"], ["worker_a", "worker_b"])
        self.assertEqual(batch["returned_roles"], [])
        self.assertEqual(status["current_work"]["source"], "packet_batch_member_status")
        self.assertEqual(status["current_work"]["owner_key"], "worker_a,worker_b")
        self.assertEqual(status["current_work"]["diagnostics"]["missing_roles"], ["worker_a", "worker_b"])

    def test_current_node_result_requires_write_grant(self) -> None:
        root = self.make_project()
        run_root, _packet_path, result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-write-grant-required",
            record_result_return=False,
        )
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        state["flags"]["current_node_write_grant_issued"] = False
        grant_path = run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_write_grant.json"
        self.assertTrue(grant_path.exists())
        grant_path.unlink()
        router.write_json(state_path, state)

        with self.assertRaisesRegex(router.RouterError, "current-node write grant"):
            router.record_external_event(
                root,
                "worker_current_node_result_returned",
                {
                    "packet_id": "node-packet-write-grant-required",
                    "result_envelope_path": result_path,
                },
            )
    def test_current_node_packet_rejects_unresolved_node_entry_self_interrogation(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)
        run_root = self.run_root_for(root)
        self.write_self_interrogation_record(
            root,
            "node_entry",
            clean=False,
            node_id="node-001",
            source_path=run_root / "routes" / "route-001" / "nodes" / "node-001" / "node_acceptance_plan.json",
        )
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-dirty-self-interrogation",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )

        with self.assertRaisesRegex(router.RouterError, "current-node packet registration requires clean self-interrogation records") as raised:
            router.record_external_event(
                root,
                "pm_registers_current_node_packet",
                {
                    "packet_id": "node-packet-dirty-self-interrogation",
                    "packet_envelope_path": packet["body_path"].replace("packet_body.md", "packet_envelope.json"),
                },
            )
        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["policy_row_id"], "self_interrogation_repair")
        self.assertEqual(blocker["target_role"], "project_manager")
        self.assertIn("rerun_self_interrogation", blocker["pm_recovery_options"])
        self.assertEqual(blocker["return_policy"]["default_return_gate"], "blocked_self_interrogation_gate")
