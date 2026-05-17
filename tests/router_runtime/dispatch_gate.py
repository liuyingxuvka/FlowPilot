from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class DispatchGateRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_dispatch_recipient_gate_blocks_busy_packet_holder(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-busy-holder")
        state = read_json(router.run_state_path(run_root))
        ledger = router._create_empty_packet_ledger(root, state["run_id"], run_root)
        ledger["active_packet_id"] = "prior-node-packet"
        ledger["active_packet_holder"] = "worker_a"
        ledger["active_packet_status"] = "active-holder-lease-issued"
        ledger["packets"].append(
            {
                "packet_id": "prior-node-packet",
                "packet_family": "current_node",
                "active_packet_holder": "worker_a",
                "active_packet_status": "active-holder-lease-issued",
            }
        )
        router.write_json(run_root / "packet_ledger.json", ledger)

        action = router.make_action(
            action_type="relay_current_node_packet",
            actor="controller",
            label="relay_new_node_packet_to_worker_a",
            summary="Relay a new current-node packet to worker_a.",
            to_role="worker_a",
            extra={"packet_id": "new-node-packet", "packet_ids": ["new-node-packet"]},
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "await_role_decision")
        self.assertEqual(gated["to_role"], "worker_a")
        self.assertIn("worker_current_node_result_returned", gated["allowed_external_events"])
        gate = gated["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "packet_ledger")
        self.assertEqual(gate["busy_reason"], "target_role_holds_unfinished_packet")
        self.assertEqual(gate["packet_id"], "prior-node-packet")
        self.assertEqual(gate["blocked_action_type"], "relay_current_node_packet")
        self.assertFalse(gate["sealed_body_reads_allowed"])
    def test_dispatch_recipient_gate_allows_system_card_for_active_holder(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-active-holder-card")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["user_intake_delivered_to_pm"] = True
        router.write_json(router.run_state_path(run_root), state)
        ledger = router._create_empty_packet_ledger(root, state["run_id"], run_root)
        ledger["active_packet_id"] = "user_intake"
        ledger["active_packet_holder"] = "project_manager"
        ledger["active_packet_status"] = "envelope-relayed"
        ledger["packets"].append(
            {
                "packet_id": "user_intake",
                "packet_family": "startup_user_intake",
                "active_packet_holder": "project_manager",
                "active_packet_status": "envelope-relayed",
            }
        )
        router.write_json(run_root / "packet_ledger.json", ledger)

        action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_material_scan_card_delivered",
            summary="Deliver the PM material scan instruction card.",
            card_id="pm.material_scan",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "deliver_system_card")
        gate = gated["dispatch_recipient_gate"]
        self.assertTrue(gate["passed"])
        self.assertEqual(gate["target_roles"], ["project_manager"])
        self.assertEqual(gate["same_obligation_instruction"]["packet_id"], "user_intake")
        self.assertEqual(gate["same_obligation_instruction"]["instruction_card_id"], "pm.material_scan")
        self.assertEqual(
            gate["same_obligation_instruction"]["expected_first_output_event"],
            "pm_issues_material_and_capability_scan_packets",
        )
        self.assertFalse(gate["sealed_body_reads_allowed"])
    def test_dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-user-intake-busy")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["user_intake_delivered_to_pm"] = True
        router.write_json(router.run_state_path(run_root), state)
        ledger = router._create_empty_packet_ledger(root, state["run_id"], run_root)
        ledger["active_packet_id"] = "user_intake"
        ledger["active_packet_holder"] = "project_manager"
        ledger["active_packet_status"] = "envelope-relayed"
        ledger["packets"].append(
            {
                "packet_id": "user_intake",
                "packet_family": "startup_user_intake",
                "active_packet_holder": "project_manager",
                "active_packet_status": "envelope-relayed",
            }
        )
        router.write_json(run_root / "packet_ledger.json", ledger)

        action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_route_skeleton_phase_card_delivered",
            summary="Deliver an independent PM route card.",
            card_id="pm.route_skeleton",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "await_role_decision")
        self.assertEqual(gated["to_role"], "project_manager")
        self.assertEqual(gated["allowed_external_events"], ["pm_issues_material_and_capability_scan_packets"])
        gate = gated["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "packet_ledger")
        self.assertEqual(gate["busy_reason"], "target_role_holds_unfinished_packet")
        self.assertEqual(gate["packet_id"], "user_intake")
        self.assertEqual(gate["blocked_action_type"], "deliver_system_card")
    def test_dispatch_recipient_gate_allows_pm_after_user_intake_first_output(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-user-intake-done")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["user_intake_delivered_to_pm"] = True
        state["flags"]["pm_material_packets_issued"] = True
        router.write_json(router.run_state_path(run_root), state)
        ledger = router._create_empty_packet_ledger(root, state["run_id"], run_root)
        ledger["active_packet_id"] = "user_intake"
        ledger["active_packet_holder"] = "project_manager"
        ledger["active_packet_status"] = "envelope-relayed"
        ledger["packets"].append(
            {
                "packet_id": "user_intake",
                "packet_family": "startup_user_intake",
                "active_packet_holder": "project_manager",
                "active_packet_status": "envelope-relayed",
            }
        )
        router.write_json(run_root / "packet_ledger.json", ledger)

        action = router.make_action(
            action_type="deliver_mail",
            actor="controller",
            label="deliver_followup_mail_to_pm",
            summary="Deliver follow-up mail after PM produced the first user-intake output.",
            mail_id="followup_pm_mail",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "deliver_mail")
        self.assertTrue(gated["dispatch_recipient_gate"]["passed"])
        self.assertEqual(gated["dispatch_recipient_gate"]["target_roles"], ["project_manager"])
    def test_dispatch_recipient_gate_blocks_followup_when_role_wait_is_active(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-passive-wait")
        state = read_json(router.run_state_path(run_root))
        wait_action = router.make_action(
            action_type="await_role_decision",
            actor="controller",
            label="controller_waits_for_pm_material_scan_packets",
            summary="Controller waits for PM to issue material scan packets.",
            to_role="project_manager",
            extra={"allowed_external_events": ["pm_issues_material_and_capability_scan_packets"]},
        )
        router._write_controller_action_entry(root, run_root, state, wait_action)

        action = router.make_action(
            action_type="deliver_mail",
            actor="controller",
            label="deliver_independent_mail_to_pm",
            summary="Deliver independent mail to PM.",
            mail_id="new-pm-mail",
            to_role="project_manager",
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "await_role_decision")
        self.assertEqual(gated["to_role"], "project_manager")
        gate = gated["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "controller_action_ledger.passive_waits")
        self.assertEqual(gate["busy_reason"], "target_role_wait_already_active")
        self.assertEqual(gate["blocked_action_type"], "deliver_mail")
    def test_dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-pm-role-work")
        state = read_json(router.run_state_path(run_root))
        index = router._empty_pm_role_work_request_index(state)
        index["active_request_id"] = "prior-role-work"
        index["requests"].append(
            {
                "request_id": "prior-role-work",
                "packet_id": "pm-role-work-prior-role-work",
                "to_role": "worker_b",
                "status": "result_returned",
            }
        )
        router.write_json(run_root / "pm_work_requests" / "index.json", index)

        worker_action = router.make_action(
            action_type="relay_pm_role_work_request_packet",
            actor="controller",
            label="relay_new_role_work_to_worker_b",
            summary="Relay a new PM role-work packet to worker_b.",
            to_role="worker_b",
            extra={"request_id": "new-role-work", "packet_id": "pm-role-work-new-role-work"},
        )
        gated_worker = router._apply_dispatch_recipient_gate(root, state, run_root, worker_action)
        self.assertEqual(gated_worker["action_type"], "relay_pm_role_work_request_packet")
        self.assertTrue(gated_worker["dispatch_recipient_gate"]["passed"])
        self.assertEqual(gated_worker["dispatch_recipient_gate"]["target_roles"], ["worker_b"])

        pm_action = router.make_action(
            action_type="deliver_mail",
            actor="controller",
            label="deliver_new_mail_to_pm",
            summary="Deliver new mail to PM.",
            mail_id="new-pm-mail",
            to_role="project_manager",
        )
        gated_pm = router._apply_dispatch_recipient_gate(root, state, run_root, pm_action)

        self.assertEqual(gated_pm["action_type"], "await_role_decision")
        self.assertEqual(gated_pm["to_role"], "project_manager")
        self.assertEqual(gated_pm["allowed_external_events"], ["pm_records_role_work_result_decision"])
        gate = gated_pm["dispatch_recipient_gate"]
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["busy_source"], "pm_role_work_index")
        self.assertEqual(gate["busy_reason"], "pm_role_work_result_disposition_pending")
        self.assertEqual(gate["request_id"], "prior-role-work")
    def test_dispatch_recipient_gate_allows_same_role_system_card_bundle(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-card-bundle")
        state = read_json(router.run_state_path(run_root))
        action = router.make_action(
            action_type="deliver_system_card_bundle",
            actor="controller",
            label="deliver_pm_startup_card_bundle",
            summary="Deliver the PM startup system-card bundle.",
            to_role="project_manager",
            extra={
                "bundle_id": "pm-startup-bundle",
                "card_ids": ["pm.startup.scope", "pm.startup.route"],
                "same_role_delivery_group": True,
            },
        )

        gated = router._apply_dispatch_recipient_gate(root, state, run_root, action)

        self.assertEqual(gated["action_type"], "deliver_system_card_bundle")
        gate = gated["dispatch_recipient_gate"]
        self.assertTrue(gate["passed"])
        self.assertTrue(gate["grouped_delivery"])
        self.assertEqual(gate["target_roles"], ["project_manager"])
        self.assertFalse(gate["sealed_body_reads_allowed"])
    def test_dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-pending-output")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["node_review_blocked"] = True
        state["flags"]["pm_model_miss_triage_card_delivered"] = True
        router.write_json(router.run_state_path(run_root), state)

        route_action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_route_skeleton_phase_card_delivered",
            summary="Deliver an independent PM output-bearing card.",
            card_id="pm.route_skeleton",
            to_role="project_manager",
        )

        gated_route = router._apply_dispatch_recipient_gate(root, state, run_root, route_action)

        self.assertEqual(gated_route["action_type"], "await_role_decision")
        self.assertEqual(gated_route["to_role"], "project_manager")
        self.assertEqual(gated_route["allowed_external_events"], ["pm_records_model_miss_triage_decision"])
        route_gate = gated_route["dispatch_recipient_gate"]
        self.assertFalse(route_gate["passed"])
        self.assertEqual(route_gate["busy_source"], "pending_expected_output")
        self.assertEqual(route_gate["busy_reason"], "target_role_output_obligation_already_pending")
        self.assertEqual(route_gate["blocked_work_package_class"], "output_bearing_work_package")
        self.assertIn("pm_writes_route_draft", route_gate["blocked_output_events"])

        event_action = router.make_action(
            action_type="deliver_system_card",
            actor="controller",
            label="pm_reviewer_blocked_event_card_delivered",
            summary="Deliver the reviewer-block event card for the active PM model-miss obligation.",
            card_id="pm.event.reviewer_blocked",
            to_role="project_manager",
        )

        gated_event = router._apply_dispatch_recipient_gate(root, state, run_root, event_action)

        self.assertEqual(gated_event["action_type"], "deliver_system_card")
        event_gate = gated_event["dispatch_recipient_gate"]
        self.assertTrue(event_gate["passed"])
        self.assertEqual(event_gate["work_package_class"], "output_bearing_work_package")
        self.assertIn("pm_records_model_miss_triage_decision", event_gate["output_events"])
    def test_user_intake_mail_declares_first_pm_output_obligation(self) -> None:
        root = self.make_project()
        run_root = self.write_minimal_run(root, "run-dispatch-gate-user-intake-contract")
        state = read_json(router.run_state_path(run_root))
        state["flags"]["startup_activation_approved"] = True
        state["ledger_check_requested"] = True
        router.write_json(router.run_state_path(run_root), state)
        packet_ledger = router._create_empty_packet_ledger(root, state["run_id"], run_root)
        packet_ledger["packets"].append(
            {
                "packet_id": "user_intake",
                "packet_envelope_path": ".flowpilot/runs/run-dispatch-gate-user-intake-contract/mailbox/outbox/user_intake.json",
                "active_packet_holder": "router",
                "active_packet_status": "router-held-startup-material",
            }
        )
        router.write_json(run_root / "packet_ledger.json", packet_ledger)

        action = router._next_mail_action(root, state, run_root)

        self.assertEqual(action["action_type"], "deliver_mail")
        self.assertEqual(action["mail_id"], "user_intake")
        obligation = action["mail_role_obligation"]
        self.assertTrue(obligation["mail_is_formal_work_material"])
        self.assertEqual(obligation["first_output_instruction_card_id"], "pm.material_scan")
        self.assertEqual(obligation["first_expected_output_event"], "pm_issues_material_and_capability_scan_packets")
        self.assertEqual(action["next_step_contract"]["mail_role_obligation"], obligation)
    def test_current_node_parallel_batch_waits_for_all_results_before_review(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.deliver_current_node_cards(root)

        packet_paths: dict[str, str] = {}
        for packet_id, role in (("node-batch-worker-a", "worker_a"), ("node-batch-worker-b", "worker_b")):
            packet = packet_runtime.create_packet(
                root,
                packet_id=packet_id,
                from_role="project_manager",
                to_role=role,
                node_id="node-001",
                body_text=f"current node work for {role}",
                metadata={"route_version": 1},
            )
            packet_paths[packet_id] = packet["body_path"].replace("packet_body.md", "packet_envelope.json")

        router.record_external_event(
            root,
            "pm_registers_current_node_packet",
            {
                "batch_id": "node-parallel-batch-001",
                "packets": [
                    {"packet_id": packet_id, "packet_envelope_path": packet_path}
                    for packet_id, packet_path in packet_paths.items()
                ],
            },
        )
        run_root = self.run_root_for(root)
        batch_index = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "current_node_packet_batch.json")
        self.assertEqual(batch_index["batch_id"], "node-parallel-batch-001")
        self.assertEqual(len(batch_index["packets"]), 2)

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_current_node_packet")
        self.assertEqual(sorted(action["packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])
        router.apply_action(root, "relay_current_node_packet")

        results: dict[str, str] = {}
        agent_a, result_a_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-batch-worker-a",
            result_body_text="worker a result",
        )
        self.assertEqual(agent_a, f"agent-{run_root.name}-worker_a")
        results["node-batch-worker-a"] = result_a_path
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "node-batch-worker-a", "result_envelope_path": results["node-batch-worker-a"]},
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "await_role_decision")
        self.assertEqual(action["allowed_external_events"], ["worker_current_node_result_returned"])
        self.assertIn("worker_b", action["to_role"])

        agent_b, result_b_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-batch-worker-b",
            result_body_text="worker b result",
        )
        self.assertEqual(agent_b, f"agent-{run_root.name}-worker_b")
        results["node-batch-worker-b"] = result_b_path
        router.record_external_event(
            root,
            "worker_current_node_result_returned",
            {"packet_id": "node-batch-worker-b", "result_envelope_path": results["node-batch-worker-b"]},
        )
        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_current_node_result_to_pm")
        self.assertEqual(sorted(action["packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])
        router.apply_action(root, "relay_current_node_result_to_pm")

        for result_path in results.values():
            packet_runtime.read_result_body_for_role(root, read_json(root / result_path), role="project_manager")
        router.record_external_event(
            root,
            "pm_records_current_node_result_disposition",
            {
                "decided_by_role": "project_manager",
                "decision": "absorbed",
                "decision_reason": "PM absorbed parallel worker results for the formal node-completion gate.",
            },
        )
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_parallel_result",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {agent_a: "worker_a", agent_b: "worker_b"},
                },
            ),
        )
        runtime_audit = read_json(
            run_root / "routes" / "route-001" / "nodes" / "node-001" / "reviews" / "current_node_packet_runtime_audit.json"
        )
        self.assertTrue(runtime_audit["passed"])
        self.assertEqual(runtime_audit["batch_id"], "node-parallel-batch-001")
        self.assertEqual(runtime_audit["packet_count"], 2)
        self.assertEqual(sorted(runtime_audit["reviewed_packet_ids"]), ["node-batch-worker-a", "node-batch-worker-b"])
    def test_current_node_pre_review_reconciliation_blocks_reviewer_card(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-card",
            deliver_review_card=False,
        )
        self.set_active_current_node_batch_status(root, "results_relayed_to_pm")

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "await_current_scope_reconciliation")
        self.assertEqual(action["scope_kind"], "current_node")
        self.assertTrue(action["local_scope_only"])
        self.assertFalse(action["future_or_sibling_scopes_touched"])
        self.assertEqual(action["review_trigger"], "reviewer.worker_result_review")
        self.assertTrue(any(blocker["kind"] == "current_node_batch_not_absorbed" for blocker in action["blockers"]))
    def test_current_node_reviewer_pass_event_waits_for_local_reconciliation(self) -> None:
        root = self.make_project()
        _run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-event",
            deliver_review_card=True,
        )
        self.set_active_current_node_batch_status(root, "results_relayed_to_pm")

        result = router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_waits_for_local_reconciliation",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {f"agent-{self.run_root_for(root).name}-worker_a": "worker_a"},
                },
            ),
        )

        self.assertFalse(result["ok"])
        self.assertTrue(result["current_scope_reconciliation_blocked"])
        self.assertEqual(result["next_required_action"]["action_type"], "await_current_scope_reconciliation")
        state = read_json(router.run_state_path(self.run_root_for(root)))
        self.assertFalse(state["flags"]["node_reviewer_passed_result"])
    def test_future_node_pending_return_does_not_block_current_node_review(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-future-return-not-local",
            deliver_review_card=False,
        )
        self.add_current_node_pending_card_return(root, node_id="node-999")

        action = self.next_after_display_sync(root)
        if action["action_type"] == "check_prompt_manifest":
            self.assertEqual(action["next_card_id"], "reviewer.worker_result_review")
            router.apply_action(root, "check_prompt_manifest")
            action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "deliver_system_card")
        self.assertEqual(action["card_id"], "reviewer.worker_result_review")
    def test_current_node_completion_waits_for_review_created_local_obligations(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-local-reconciliation-exit",
            deliver_review_card=True,
        )
        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_exit_waits_for_local_reconciliation",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {f"agent-{run_root.name}-worker_a": "worker_a"},
                },
            ),
        )
        self.set_active_current_node_batch_status(root, "pm_absorbed")

        with self.assertRaisesRegex(router.RouterError, "local current-scope reconciliation"):
            router.record_external_event(root, "pm_completes_current_node_from_reviewed_result")
    def test_no_legal_next_action_materializes_pm_decision_control_blocker(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)

        for flag in list(state["flags"]):
            state["flags"][flag] = True
        for terminal_flag in (
            "run_cancelled_by_user",
            "run_stopped_by_user",
            "startup_protocol_dead_end_declared",
            "resume_reentry_requested",
        ):
            state["flags"][terminal_flag] = False
        state["status"] = "controller_ready"
        state["phase"] = "route_loop"
        state["pending_action"] = None
        state["active_control_blocker"] = None
        state["latest_control_blocker_path"] = None
        state["control_blockers"] = []
        state["resolved_control_blockers"] = []
        route_memory = run_root / "route_memory"
        route_memory.mkdir(parents=True, exist_ok=True)
        router.write_json(route_memory / "route_history_index.json", {"schema_version": "test", "routes": []})
        router.write_json(route_memory / "pm_prior_path_context.json", {"schema_version": "test", "reviewed": True})
        router._write_startup_mechanical_audit(root, run_root, state, {})  # type: ignore[attr-defined]
        router.write_json(state_path, state)

        action = self.next_after_display_sync(root)

        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "project_manager")
        self.assertEqual(action["handling_lane"], "pm_repair_decision_required")
        self.assertTrue(action["pm_decision_required"])
        self.assertFalse(action["sealed_body_reads_allowed"])
        state = read_json(state_path)
        blocker = state["active_control_blocker"]
        self.assertEqual(blocker["delivery_status"], "pending")
        blocker_path = self.control_blocker_path(root, blocker)
        self.assertTrue(blocker_path.exists())
        saved = read_json(blocker_path)
        self.assertEqual(saved["source"], "router_no_legal_next_action")
        self.assertEqual(saved["originating_action_type"], "controller_no_legal_next_action")
        self.assertEqual(saved["target_role"], "project_manager")
        self.assertTrue(saved["pm_decision_required"])
        self.assertEqual(saved["allowed_resolution_events"], ["pm_records_control_blocker_repair_decision"])
        self.assertIn("advance route state", " ".join(saved["controller_forbidden_actions"]))
        self.assertTrue((root / saved["sealed_repair_packet_path"]).exists())
    def test_router_hard_rejection_returns_control_plane_reissue_action(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-control-reissue")

        with self.assertRaises(router.RouterError) as raised:
            router.record_external_event(
                root,
                "current_node_reviewer_passes_result",
                self.role_report_envelope(
                    root,
                    "reviews/current_node_result_missing_passed",
                    {
                        "reviewed_by_role": "human_like_reviewer",
                        "agent_role_map": {"agent-worker-a": "worker_a"},
                    },
                ),
            )

        blocker = raised.exception.control_blocker
        self.assertIsInstance(blocker, dict)
        self.assertEqual(blocker["handling_lane"], "control_plane_reissue")
        self.assertEqual(blocker["target_role"], "human_like_reviewer")
        blocker_path = self.control_blocker_path(root, blocker)
        self.assertTrue(blocker_path.exists())
        saved = read_json(blocker_path)
        self.assertIn("same-role reissue", saved["controller_instruction"])
        self.assertNotIn("error_message", saved)
        self.assertNotIn("source_paths", saved)
        sealed_packet = root / saved["sealed_repair_packet_path"]
        self.assertTrue(sealed_packet.exists())
        self.assertEqual(read_json(sealed_packet)["target_role"], "human_like_reviewer")
        self.assertFalse(saved["pm_decision_required"])
        self.assertEqual(saved["skill_observation_reminder"]["suggested_kind"], "controller_compensation")

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "handle_control_blocker")
        self.assertEqual(action["to_role"], "human_like_reviewer")
        self.assertEqual(action["next_step_contract"]["recipient_role"], "human_like_reviewer")
        self.assertFalse(action["next_step_contract"]["sealed_body_reads_allowed"])
        self.assertEqual(action["handling_lane"], "control_plane_reissue")
        self.assertIn("sealed_repair_packet_path", action)
        self.assertNotIn("controller_delivery_body", action)
        self.assertIn("sealed", " ".join(action["controller_forbidden_actions"]))
        self.assertTrue(action["skill_observation_reminder"]["should_consider_recording"])
        router.apply_action(root, "handle_control_blocker")

        delivered = read_json(blocker_path)
        self.assertEqual(delivered["delivery_status"], "delivered")
        self.assertEqual(delivered["delivered_to_role"], "human_like_reviewer")

        router.record_external_event(
            root,
            "current_node_reviewer_passes_result",
            self.role_report_envelope(
                root,
                "reviews/current_node_result_reissued",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": True,
                    "agent_role_map": {"agent-worker-a": "worker_a"},
                },
            ),
        )
        state = read_json(router.run_state_path(router.active_run_root(root)))  # type: ignore[arg-type]
        self.assertIsNone(state["active_control_blocker"])
