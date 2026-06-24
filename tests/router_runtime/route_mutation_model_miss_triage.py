from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationModelMissTriageRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_reviewer_block_delivers_model_miss_triage_before_review_repair(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-gate")

            router.record_external_event(root, "current_node_reviewer_blocks_result")

            card_action = self.deliver_expected_card(root, "pm.model_miss_triage")
            self.assert_payload_contract_mentions(
                card_action["payload_contract"],
                "pm_model_miss_triage_decision_role_output",
                "proceed_with_model_backed_repair",
                "flowguard_operator_report_refs",
                "minimal_sufficient_repair_recommendation",
            )
            self.assertFalse(self.flag(root, "pm_review_repair_card_delivered"))
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")
            wait_action = router.next_action(root)
            self.assertEqual(wait_action["action_type"], "await_role_decision")
            self.assertIn("pm_records_model_miss_triage_decision", wait_action["allowed_external_events"])
            self.assertIn("pm_registers_role_work_request", wait_action["allowed_external_events"])
            self.assert_payload_contract_mentions(wait_action["payload_contract"], "same_class_findings_reviewed")


    def test_review_block_route_mutation_requires_closed_model_miss_triage(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-mutation")
            router.record_external_event(root, "current_node_reviewer_blocks_result")

            with self.assertRaisesRegex(router.RouterError, "model[_-]miss"):
                router.record_external_event(
                    root,
                    "pm_mutates_route_after_review_block",
                    {"repair_node_id": "node-001-repair", "reason": "reviewer_block"},
                )


    def test_stale_review_block_route_mutation_wait_is_recomputed_before_pm_triage(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-stale-wait")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            run_root = self.run_root_for(root)
            state = read_json(router.run_state_path(run_root))
            self.assertFalse(state["flags"].get("model_miss_triage_closed"))
            state["pending_action"] = {
                "schema_version": router.SCHEMA_VERSION,
                "action_id": "stale-route-mutation-wait",
                "action_type": "await_role_decision",
                "actor": "controller",
                "label": "controller_waits_for_expected_event_pm_mutates_route_after_review_block",
                "allowed_external_events": ["pm_mutates_route_after_review_block"],
                "allowed_reads": [self.rel(root, router.run_state_path(run_root))],
                "allowed_writes": [self.rel(root, router.run_state_path(run_root))],
            }
            router.save_run_state(run_root, state)

            action = self.deliver_expected_card(root, "pm.model_miss_triage")

            self.assertEqual(action["action_type"], "deliver_system_card")
            self.assertEqual(action["card_id"], "pm.model_miss_triage")
            repaired_state = read_json(router.run_state_path(run_root))
            labels = [entry["label"] for entry in repaired_state["history"]]
            self.assertIn("router_cleared_stale_pending_action", labels)
            pending = repaired_state["pending_action"]
            if pending is not None:
                self.assertNotEqual(pending.get("action_type"), "check_prompt_manifest")
                if pending.get("action_type") == "deliver_system_card":
                    self.assertEqual(pending["card_id"], "pm.event.reviewer_blocked")


    def test_model_backed_model_miss_triage_requires_flowguard_operator_report_refs(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-invalid")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")

            body = self.model_miss_triage_body(root, decision="proceed_with_model_backed_repair")
            body.pop("flowguard_operator_report_refs")
            with self.assertRaisesRegex(router.RouterError, "flowguard_operator_report_refs"):
                router.record_external_event(
                    root,
                    "pm_records_model_miss_triage_decision",
                    self.role_decision_envelope(root, "decisions/model_miss_invalid", body),
                )
            self.assertFalse(self.flag(root, "model_miss_triage_closed"))


    def test_non_authorizing_model_miss_decision_does_not_unlock_review_repair(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-request")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")

            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/model_miss_request",
                    self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
                ),
            )

            self.assertFalse(self.flag(root, "model_miss_triage_closed"))
            self.assertFalse(self.flag(root, "pm_review_repair_card_delivered"))
            state = read_json(router.run_state_path(self.run_root_for(root)))
            self.assertTrue(state["flags"]["model_miss_triage_followup_request_pending"])
            self.assertEqual(
                state["model_miss_triage_followup_request"]["required_output_contract_id"],
                "flowpilot.output_contract.flowguard_model_miss_report.v1",
            )
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")
            wait = self.next_after_display_sync(root)
            self.assertEqual(wait["action_type"], "await_role_decision")
            self.assertEqual(wait["allowed_external_events"], ["pm_registers_role_work_request"])

    def test_pm_model_miss_break_glass_routes_control_blocker_without_unlocking_repair(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-break-glass")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")

            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/model_miss_break_glass",
                    self.model_miss_triage_body(root, decision="break_glass"),
                ),
            )

            self.assertFalse(self.flag(root, "model_miss_triage_closed"))
            self.assertFalse(self.flag(root, "pm_review_repair_card_delivered"))
            state = read_json(router.run_state_path(self.run_root_for(root)))
            self.assertEqual(
                state["model_miss_triage_break_glass"]["status"],
                "control_plane_blocker_requested",
            )
            self.assertEqual(state["active_control_blocker"]["originating_event"], "pm_records_model_miss_triage_decision")
            self.assertEqual(state["active_control_blocker"]["originating_action_type"], "pm_model_miss_triage_decision")
            action = self.next_after_display_sync(root)
            self.assertEqual(action["action_type"], "handle_control_blocker")


    def test_pm_model_miss_followup_uses_generic_role_work_request_channel(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-role-work-request")
            run_root = self.run_root_for(root)
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")
            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/model_miss_role_work_request",
                    self.model_miss_triage_body(root, decision="request_flowguard_operator_model_miss_analysis"),
                ),
            )
            router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
            index = read_json(run_root / "pm_work_requests" / "index.json")
            self.assertEqual(index["active_request_id"], "model-miss-followup-001")
            self.assertEqual(index["requests"][0]["to_role"], "flowguard_operator")
            self.assertEqual(index["requests"][0]["status"], "open")

            action = self.next_after_display_sync(root)
            self.assertEqual(action["action_type"], "relay_pm_role_work_request_packet")
            self.assertEqual(action["request_id"], "model-miss-followup-001")
            router.apply_action(root, "relay_pm_role_work_request_packet")

            index = read_json(run_root / "pm_work_requests" / "index.json")
            self.assertEqual(index["requests"][0]["status"], "packet_relayed")
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

            action = self.next_after_display_sync(root)
            self.assertEqual(action["action_type"], "relay_pm_role_work_result_to_pm")
            router.apply_action(root, "relay_pm_role_work_result_to_pm")
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

            index = read_json(run_root / "pm_work_requests" / "index.json")
            self.assertEqual(index["requests"][0]["status"], "absorbed")
            self.assertIsNone(index["active_request_id"])


    def test_model_backed_model_miss_triage_unlocks_review_repair(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-valid")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")

            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/model_miss_valid",
                    self.model_miss_triage_body(root, decision="proceed_with_model_backed_repair"),
                ),
            )

            self.assertTrue(self.flag(root, "model_miss_triage_closed"))
            self.deliver_expected_card(root, "pm.review_repair")


    def test_out_of_scope_model_miss_triage_unlocks_review_repair_with_reason(self) -> None:
            root = self.make_project()
            self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-out-of-scope")
            router.record_external_event(root, "current_node_reviewer_blocks_result")
            self.deliver_expected_card(root, "pm.model_miss_triage")
            self.deliver_expected_card(root, "pm.event.reviewer_blocked")

            router.record_external_event(
                root,
                "pm_records_model_miss_triage_decision",
                self.role_decision_envelope(
                    root,
                    "decisions/model_miss_out_of_scope",
                    self.model_miss_triage_body(root, decision="out_of_scope_not_modelable"),
                ),
            )

            self.assertTrue(self.flag(root, "model_miss_triage_closed"))
            self.deliver_expected_card(root, "pm.review_repair")
