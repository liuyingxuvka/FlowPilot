from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class PmRoleWorkRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_pm_role_work_existing_result_reconciles_before_wait(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-reconcile")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_reconcile",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")
        index_after_relay = read_json(run_root / "pm_work_requests" / "index.json")
        packet_id = index_after_relay["requests"][0]["packet_id"]
        lease = self.active_holder_lease_for_packet(root, packet_id)
        self.assertEqual(lease["holder_role"], "flowguard_operator")

        self.open_role_work_packet_and_write_result(root)
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["pm_role_work_result_returned"])
        self.assertTrue(
            any(
                item.get("event") == "role_work_result_returned"
                and item.get("reconciled_by_router") is True
                for item in state["events"]
                if isinstance(item, dict)
            )
        )
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["status"], "result_returned")
    def test_advisory_pm_role_work_wait_is_marked_nonblocking(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-advisory")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_advisory",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="model-miss-advisory-001",
                request_mode="advisory",
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["role_work_result_returned"])
        self.assertTrue(action["nonblocking_wait"])
        self.assertEqual(action["dependency_class"], "advisory")
    def test_gate_targeted_pm_role_work_result_requires_mapped_gate_event(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-gate-targeted-role-work")
        run_root = self.run_root_for(root)
        state_path = router.run_state_path(run_root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/gate_targeted_model_miss_role_work",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        request = self.pm_role_work_request_payload(
            root,
            request_id="gate-modelability-followup-001",
            body_text="Assess product architecture modelability and return the result to PM.",
        )
        request["target_gate_id"] = "product_behavior_model"
        router.record_external_event(root, "pm_registers_role_work_request", request)
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["requests"][0]["target_gate_contract"]["gate_id"], "product_behavior_model")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        result_path = self.open_role_work_packet_and_write_result(root, request_id="gate-modelability-followup-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "gate-modelability-followup-001",
                "packet_id": "pm-role-work-gate-modelability-followup-001",
                "result_envelope_path": result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        wait = self.next_after_display_sync(root)
        self.assertIn("mapped_gate_event", wait["payload_contract"]["required_fields"])

        with self.assertRaisesRegex(router.RouterError, "mapped_gate_event"):
            router.record_external_event(
                root,
                "pm_records_role_work_result_decision",
                {
                    "decided_by_role": "project_manager",
                    "request_id": "gate-modelability-followup-001",
                    "decision": "absorbed",
                    "decision_reason": "PM reviewed the FlowGuard operator result.",
                },
            )
        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "request_id": "gate-modelability-followup-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the FlowGuard operator result and maps it to the gate pass event.",
                "mapped_gate_event": "flowguard_operator_submits_product_behavior_model",
            },
        )

        state = read_json(state_path)
        self.assertTrue(state["flags"]["product_behavior_model_submitted"])
        self.assertTrue((run_root / "flowguard" / "product_behavior_model.json").exists())
        self.assertFalse((run_root / "flowguard" / "product_architecture_modelability.json").exists())
        self.assertTrue(
            any(
                item.get("event") == "flowguard_operator_submits_product_behavior_model"
                and item.get("payload", {}).get("mapped_from_event") == "pm_records_role_work_result_decision"
                for item in state["events"]
                if isinstance(item, dict)
            )
        )
    def test_pm_role_work_batch_waits_for_all_distinct_role_results_before_pm_relay(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-batch")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_batch",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            {
                "requested_by_role": "project_manager",
                "batch_id": "pm-model-miss-batch-001",
                "requests": [
                    self.pm_role_work_request_payload(
                        root,
                        request_id="model-miss-product-001",
                        to_role="flowguard_operator",
                    ),
                    self.pm_role_work_request_payload(
                        root,
                        request_id="model-miss-process-001",
                        to_role="worker",
                        request_kind="implementation",
                        output_contract_id="flowpilot.output_contract.pm_role_work_result.v1",
                        body_text="Analyze the missed process invariant and recommend a minimal model repair.",
                    ),
                ],
            },
        )
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["active_batch_id"], "pm-model-miss-batch-001")
        self.assertEqual(index["active_request_ids"], ["model-miss-product-001", "model-miss-process-001"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        self.assertEqual(sorted(action["packet_ids"]), ["pm-role-work-model-miss-process-001", "pm-role-work-model-miss-product-001"])
        router.apply_action(root, "relay_pm_role_work_request_packet")

        product_result_path = self.open_role_work_packet_and_write_result(root, request_id="model-miss-product-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-product-001",
                "packet_id": "pm-role-work-model-miss-product-001",
                "result_envelope_path": product_result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["role_work_result_returned"])
        self.assertEqual(action["to_role"], "worker")

        process_result_path = self.open_role_work_packet_and_write_result(root, request_id="model-miss-process-001")
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-process-001",
                "packet_id": "pm-role-work-model-miss-process-001",
                "result_envelope_path": process_result_path,
            },
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        self.assertEqual(sorted(action["packet_ids"]), ["pm-role-work-model-miss-process-001", "pm-role-work-model-miss-product-001"])
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "batch_id": "pm-model-miss-batch-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the complete FlowGuard operator batch.",
            },
        )

        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertIsNone(index["active_batch_id"])
        self.assertTrue(all(record["status"] == "absorbed" for record in index["requests"]))
    def test_pm_role_work_request_requires_valid_recipient_and_contract(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-invalid")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_invalid",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )

        bad_contract = self.pm_role_work_request_payload(root, request_id="bad-contract")
        bad_contract.pop("output_contract_id")
        with self.assertRaisesRegex(router.RouterError, "output_contract_id"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_contract)

        bad_role = self.pm_role_work_request_payload(root, request_id="bad-role", to_role="controller")
        with self.assertRaisesRegex(router.RouterError, "other than PM or Controller"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_role)
    def test_pm_role_work_request_supersedes_unrelayed_old_request(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-supersede")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_role_work_supersede",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="model-miss-process-001",
                to_role="flowguard_operator",
                body_text="Analyze the process invariant miss.",
            ),
        )
        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="model-miss-process-002",
                to_role="flowguard_operator",
                body_text="Replacement analysis with clarified process invariant scope.",
                supersedes_request_id="model-miss-process-001",
            ),
        )

        index = read_json(run_root / "pm_work_requests" / "index.json")
        old_record = next(record for record in index["requests"] if record["request_id"] == "model-miss-process-001")
        new_record = next(record for record in index["requests"] if record["request_id"] == "model-miss-process-002")
        self.assertEqual(old_record["status"], "superseded")
        self.assertEqual(old_record["superseded_by_request_id"], "model-miss-process-002")
        self.assertEqual(index["active_request_id"], "model-miss-process-002")
        self.assertEqual(index["active_request_ids"], ["model-miss-process-002"])
        self.assertEqual(new_record["status"], "open")
        self.assertEqual(new_record["supersedes_request_ids"], ["model-miss-process-001"])
        self.assertEqual(new_record["replacement_for_packet_id"], "pm-role-work-model-miss-process-001")

        lifecycle = read_json(run_root / "pm_work_requests" / "flowguard_operator_request_lifecycle_index.json")
        old_lifecycle = next(record for record in lifecycle["requests"] if record["request_id"] == "model-miss-process-001")
        self.assertEqual(old_lifecycle["lifecycle_status"], "superseded")
        self.assertEqual(lifecycle["active_request_ids"], ["model-miss-process-002"])

        ledger = read_json(run_root / "packet_ledger.json")
        old_packet = next(record for record in ledger["packets"] if record["packet_id"] == "pm-role-work-model-miss-process-001")
        self.assertEqual(old_packet["replaced_by"], "pm-role-work-model-miss-process-002")
        self.assertEqual(old_packet["replacement_packet_id"], "pm-role-work-model-miss-process-002")
        new_envelope = packet_runtime.load_envelope(root, new_record["packet_envelope_path"])
        self.assertEqual(new_envelope["replacement_for"], "pm-role-work-model-miss-process-001")
        self.assertEqual(new_envelope["supersedes"], ["pm-role-work-model-miss-process-001"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        self.assertEqual(action["request_id"], "model-miss-process-002")
    def test_pm_role_work_request_rejects_current_node_contract_family(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state = read_json(router.run_state_path(run_root))
        state["pending_action"] = {
            "action_type": "await_role_decision",
            "to_role": "project_manager",
            "allowed_external_events": ["pm_registers_role_work_request"],
        }
        router.write_json(router.run_state_path(run_root), state)

        bad_contract = self.pm_role_work_request_payload(
            root,
            request_id="bad-current-node-contract",
            to_role="worker",
            request_kind="implementation",
            output_contract_id="flowpilot.output_contract.worker_current_node_result.v1",
            body_text="Do a delegated PM repair task.",
        )
        with self.assertRaisesRegex(router.RouterError, "does not match PM role-work process"):
            router.record_external_event(root, "pm_registers_role_work_request", bad_contract)
    def test_strict_pm_role_work_result_rejects_wrong_next_recipient(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-strict-role-work")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        run_root = self.run_root_for(root)

        router.record_external_event(
            root,
            "pm_registers_role_work_request",
            self.pm_role_work_request_payload(
                root,
                request_id="strict-role-work-001",
                to_role="worker",
                request_kind="implementation",
                output_contract_id="flowpilot.output_contract.pm_role_work_result.v1",
                body_text="Do a delegated PM repair task.",
            ),
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        router.apply_action(root, "relay_pm_role_work_request_packet")

        index = read_json(run_root / "pm_work_requests" / "index.json")
        record = index["requests"][0]
        envelope = packet_runtime.load_envelope(root, record["packet_envelope_path"])
        packet_runtime.read_packet_body_for_role(root, envelope, role="worker")
        result = packet_runtime.write_result(
            root,
            packet_envelope=envelope,
            completed_by_role="worker",
            completed_by_agent_id="worker-1-agent",
            result_body_text="Status\n\nComplete\n\nContract Self-Check\n\nPassed.",
            next_recipient="human_like_reviewer",
        )
        result_path = result["result_body_path"].replace("result_body.md", "result_envelope.json")
        with self.assertRaisesRegex(router.RouterError, "next_recipient must match process binding"):
            router.record_external_event(
                root,
                "role_work_result_returned",
                {
                    "request_id": "strict-role-work-001",
                    "packet_id": "pm-role-work-strict-role-work-001",
                    "result_envelope_path": result_path,
                },
            )
    def test_wait_event_producer_binding_rejects_wrong_target_role(self) -> None:
        with self.assertRaisesRegex(router.RouterError, "event producer role"):
            router._validate_wait_event_producer_binding(
                ["current_node_reviewer_passes_result"],
                to_role="project_manager",
                context="test wait",
            )
        router._validate_wait_event_producer_binding(
            ["current_node_reviewer_passes_result"],
            to_role="human_like_reviewer",
            context="test wait",
        )
        self.assertEqual(
            router._control_blocker_followup_target_role(
                ["current_node_reviewer_passes_result"],
                "project_manager",
            ),
            "human_like_reviewer",
        )
