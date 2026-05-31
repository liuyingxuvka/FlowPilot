from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ClosureRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_flowguard_operator_role_work_writes_authorized_lifecycle_index(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-FlowGuard operator-lifecycle")
        run_root = self.run_root_for(root)
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_records_model_miss_triage_decision",
            self.role_decision_envelope(
                root,
                "decisions/model_miss_flowguard_operator_lifecycle",
                self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
            ),
        )
        router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
        lifecycle_path = run_root / "pm_work_requests" / "flowguard_operator_request_lifecycle_index.json"
        lifecycle = read_json(lifecycle_path)
        self.assertEqual(lifecycle["schema_version"], router.FLOWGUARD_OPERATOR_REQUEST_LIFECYCLE_INDEX_SCHEMA)
        self.assertEqual(lifecycle["active_request_ids"], ["model-miss-followup-001"])
        entry = lifecycle["requests"][0]
        self.assertEqual(entry["lifecycle_status"], "request_registered")
        self.assertEqual(entry["request_authority"], "pm_role_work_request")
        self.assertFalse(entry["controller_may_read_packet_body"])
        self.assertFalse(entry["controller_may_read_result_body"])
        self.assertTrue(entry["validation_passed"])

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
        self.assertEqual(action["flowguard_operator_request_lifecycle_index"], self.rel(root, lifecycle_path))
        router.apply_action(root, "relay_pm_role_work_request_packet")
        lifecycle = read_json(lifecycle_path)
        self.assertEqual(lifecycle["requests"][0]["lifecycle_status"], "packet_relayed")

        result_path = self.open_role_work_packet_and_write_result(root)
        router.record_external_event(
            root,
            "role_work_result_returned",
            {
                "request_id": "model-miss-followup-001",
                "packet_id": "pm-role-work-model-miss-followup-001",
                "result_envelope_path": result_path,
            },
        )
        lifecycle = read_json(lifecycle_path)
        self.assertEqual(lifecycle["requests"][0]["lifecycle_status"], "result_returned")
        self.assertTrue(lifecycle["requests"][0]["router_result_event_seen"])
        self.assertEqual(lifecycle["requests"][0]["result_next_recipient"], "project_manager")

        action = self.next_after_display_sync(root)
        self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
        router.apply_action(root, "relay_pm_role_work_result_to_pm")
        lifecycle = read_json(lifecycle_path)
        self.assertEqual(lifecycle["requests"][0]["lifecycle_status"], "result_relayed_to_pm")

        router.record_external_event(
            root,
            "pm_records_role_work_result_decision",
            {
                "decided_by_role": "project_manager",
                "request_id": "model-miss-followup-001",
                "decision": "absorbed",
                "decision_reason": "PM reviewed the FlowGuard operator model-miss result.",
            },
        )
        lifecycle = read_json(lifecycle_path)
        self.assertEqual(lifecycle["requests"][0]["lifecycle_status"], "pm_absorbed")
        self.assertTrue(lifecycle["requests"][0]["closed_by_pm"])
        self.assertEqual(lifecycle["active_request_ids"], [])
    def test_closure_lifecycle_blocks_when_ledgers_are_dirty_after_terminal_replay(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-dirty-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)

        evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
        evidence_ledger = read_json(evidence_ledger_path)
        evidence_ledger["unresolved_count"] = 1
        evidence_ledger_path.write_text(json.dumps(evidence_ledger, indent=2, sort_keys=True), encoding="utf-8")

        action = router.next_action(root)
        card_id = action.get("next_card_id") or action.get("card_id")
        self.assertNotEqual(card_id, "pm.closure")
    def test_terminal_closure_blocks_dirty_defect_ledger_after_terminal_replay(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-dirty-defect")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)
        self.deliver_expected_card(root, "pm.closure")

        defect_ledger_path = run_root / "defects" / "defect_ledger.json"
        router.write_json(
            defect_ledger_path,
            {
                "schema_version": "flowpilot.defect_ledger.v1",
                "run_id": run_root.name,
                "route_id": "route-001",
                "route_version": 1,
                "pm_owned": True,
                "status": "active",
                "counts": {
                    "total": 1,
                    "open": 1,
                    "blocker_open": 1,
                    "fixed_pending_recheck": 0,
                    "closed": 0,
                    "deferred": 0,
                },
                "defects": [
                    {
                        "defect_id": "defect-open-terminal",
                        "severity": "blocker",
                        "status": "open",
                        "pm_triage": {"recheck_role_class": "human_like_reviewer"},
                        "recheck_paths": [],
                    }
                ],
            },
        )

        with self.assertRaisesRegex(router.RouterError, "defect_ledger"):
            router.record_external_event(
                root,
                "pm_approves_terminal_closure",
                self.role_decision_envelope(
                    root,
                    "closure/pm_terminal_closure_dirty_defect",
                    {
                        "approved_by_role": "project_manager",
                        "decision": "approve_terminal_closure",
                        **self.prior_path_context_review(root, "Terminal closure attempted with dirty defect ledger."),
                        "final_report": {"status": "complete"},
                    },
                ),
            )
    def test_pm_terminal_closure_uses_file_backed_contract_and_prior_context(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-terminal-closure")
        self.complete_evidence_quality_package(root)
        self.complete_final_ledger_and_terminal_replay(root)

        card_action = self.deliver_expected_card(root, "pm.closure")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
            "pm_terminal_closure_decision_role_output",
            "approved_by_role",
            "approve_terminal_closure",
            "prior_path_context_review.source_paths",
            "pm_prior_path_context.json",
            "route_history_index.json",
        )
        wait_action = router.next_action(root)
        self.assertEqual(wait_action["action_type"], "await_role_decision")
        self.assert_payload_contract_mentions(
            wait_action["payload_contract"],
            "pm_terminal_closure_decision_role_output",
            "current_ledgers_clean",
            "pm_suggestion_ledger_clean",
            "self_interrogation_index_clean",
            "prior_path_context_review.controller_summary_used_as_evidence",
        )

        result = router.record_external_event(
            root,
            "pm_approves_terminal_closure",
            self.role_decision_envelope(
                root,
                "closure/pm_terminal_closure_decision",
                {
                    "approved_by_role": "project_manager",
                    "decision": "approve_terminal_closure",
                    **self.prior_path_context_review(root, "Terminal closure considered clean final ledger and current route memory."),
                    "final_report": {"status": "complete"},
                },
            ),
        )
        self.assertTrue(result["ok"])
        closure = read_json(run_root / "closure" / "terminal_closure_suite.json")
        self.assertEqual(closure["decision"], "approve_terminal_closure")
        self.assertEqual(closure["prior_path_context_review"]["reviewed"], True)
        self.assertTrue(closure["self_interrogation_review"]["clean"])
        self.assertTrue(closure["terminal_closure_reconciliation"]["clean"])
        self.assertTrue(closure["terminal_closure_reconciliation"]["role_memory"]["clean"])
        self.assertTrue(closure["terminal_closure_reconciliation"]["continuation_quarantine"]["clean"])
        self.assertEqual(closure["status"], "closed")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "closed")
        state = read_json(router.run_state_path(run_root))
        self.assertEqual(state["status"], "closed")
        self.assertTrue(state["flags"]["terminal_closure_approved"])
        lifecycle = read_json(run_root / "lifecycle" / "run_lifecycle.json")
        self.assertEqual(lifecycle["status"], "closed")
        snapshot = read_json(run_root / "route_state_snapshot.json")
        completed_nodes = {node["id"]: node for node in snapshot["route"]["nodes"] if node["id"] in frontier["completed_nodes"]}
        self.assertTrue(completed_nodes)
        self.assertTrue(all(node["status"] == "completed" for node in completed_nodes.values()))
        self.assertTrue(
            all(
                item["status"] == "completed"
                for node in completed_nodes.values()
                for item in node["checklist"]
            )
        )
        self.assertEqual(snapshot["active_ui_task_catalog"]["active_tasks"], [])

        action = router.next_action(root)
        self.assertEqual(action["action_type"], "write_terminal_summary")
        self.assertEqual(action["run_lifecycle_status"], "closed")
        self.assertEqual(action["required_attribution_line"], router.TERMINAL_SUMMARY_ATTRIBUTION)
        self.apply_terminal_summary(root, action, run_root, note="PM approved terminal closure.")
        action = router.next_action(root)
        self.assertEqual(action["action_type"], "run_lifecycle_terminal")
        self.assertEqual(action["run_lifecycle_status"], "closed")
    def test_dirty_pm_suggestion_ledger_invalidates_terminal_closure_card(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.complete_leaf_node_with_reviewed_result(root, packet_id="node-packet-suggestion-closure")
        self.complete_evidence_quality_package(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=True)])
        self.complete_final_ledger_and_terminal_replay(root)
        self.write_pm_suggestion_ledger(root, [self.pm_suggestion_entry(root, clean=False)])

        action = router.next_action(root)
        card_id = action.get("next_card_id") or action.get("card_id")
        self.assertNotEqual(card_id, "pm.closure")
        self.assertEqual(card_id, "pm.evidence_quality_package")
