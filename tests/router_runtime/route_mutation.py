from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_pm_route_draft_preserves_role_authored_repair_policy_fields(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_startup_activation(root)
        self.complete_material_flow(root)
        self.complete_root_contract_before_child_skill_gates(root)
        self.complete_child_skill_gates(root)

        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")

        nodes = [{"node_id": "node-001"}]
        repair_policy = {
            "policy_id": "route-001-repair-return-policy-test",
            "branch_table": [
                {
                    "trigger": "reviewer_block",
                    "rejoin_target": "node-001",
                    "rerun_checks": ["process_officer_route_process_check"],
                }
            ],
        }
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "schema_version": "flowpilot.pm_route_draft_payload.v1",
                "route_id": "route-001",
                "route_version": 4,
                "nodes": nodes,
                "route": {
                    "route_id": "route-001",
                    "route_version": 4,
                    "nodes": nodes,
                    "repair_return_policy": repair_policy,
                },
                "route_repair_return_policy": repair_policy,
                **self.prior_path_context_review(
                    root,
                    "Route draft preserves PM-authored repair-return policy fields.",
                ),
            },
        )

        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["schema_version"], "flowpilot.route_draft.v1")
        self.assertEqual(draft["pm_authored_payload_schema_version"], "flowpilot.pm_route_draft_payload.v1")
        self.assertEqual(draft["route_repair_return_policy"], repair_policy)
        self.assertEqual(draft["route"]["repair_return_policy"], repair_policy)
        self.assertFalse(draft["router_preservation"]["whitelist_rebuild_used"])
        self.assertTrue(draft["router_preservation"]["role_authored_fields_preserved"])
    def test_reviewer_block_delivers_model_miss_triage_before_review_repair(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-gate")

        router.record_external_event(root, "current_node_reviewer_blocks_result")

        card_action = self.deliver_expected_card(root, "pm.model_miss_triage")
        self.assert_payload_contract_mentions(
            card_action["payload_contract"],
            "pm_model_miss_triage_decision_role_output",
            "proceed_with_model_backed_repair",
            "officer_report_refs",
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
    def test_node_acceptance_plan_block_enters_model_miss_repair_path(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")

        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blockers": ["acceptance evidence path is not router-authorized"],
                },
            ),
        )

        self.assertTrue(self.flag(root, "node_acceptance_plan_review_blocked"))
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.close_model_miss_triage(root, output_name="decisions/node_acceptance_model_miss_valid")
        self.deliver_expected_card(root, "pm.review_repair")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-acceptance-repair",
                "repair_return_to_node_id": "node-001",
                "reason": "node_acceptance_plan_review_block",
                **self.prior_path_context_review(root, "Route mutation considered the node acceptance-plan reviewer block."),
            },
        )

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["node_acceptance_plan_review_blocked"])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-acceptance-repair")
    def test_node_acceptance_plan_block_can_be_revised_on_same_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.activate_route(root)
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")

        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_block_same_node",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["work_packet_projection is missing a required inherited gate row"],
                    "recommended_resolution": "PM should revise the same node acceptance plan and resubmit it for review.",
                },
            ),
        )
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.close_model_miss_triage(root, output_name="decisions/node_acceptance_same_node_repair_triage")
        self.deliver_expected_card(root, "pm.review_repair")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")
        wait_action = router.next_action(root)
        self.assertIn("pm_revises_node_acceptance_plan", wait_action["allowed_external_events"])
        self.assertIn("pm_mutates_route_after_review_block", wait_action["allowed_external_events"])

        router.record_external_event(
            root,
            "pm_revises_node_acceptance_plan",
            {
                **self.prior_path_context_review(root, "PM chose same-node plan repair because the current node can contain the missing gate row."),
                "high_standard_recheck": {
                    "ideal_outcome": "complete the current node at the highest practical standard",
                    "unacceptable_outcomes": ["partial work", "unverified closure", "controller downgrade"],
                    "higher_standard_opportunities": ["tighten inherited gate rows before dispatch"],
                    "semantic_downgrade_risks": ["treating a plan wording repair as a route-level defect"],
                    "decision": "proceed",
                    "why_current_plan_meets_highest_reasonable_standard": "PM revised the current node plan with the missing inherited gate row and kept route structure unchanged.",
                },
                "node_requirements": [
                    {
                        "requirement_id": "node-001-req",
                        "acceptance_statement": "current node work is complete with inherited gate coverage",
                        "proof_required": "mixed",
                    }
                ],
                "experiment_plan": [],
            },
        )

        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["node_acceptance_plan_review_blocked"])
        self.assertTrue(state["flags"]["node_acceptance_plan_revised_by_pm"])
        self.assertFalse(state["flags"]["reviewer_node_acceptance_plan_card_delivered"])
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_passes_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/node_acceptance_plan_review_recheck",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )

        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["node_acceptance_plan_reviewer_passed"])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "current_node_loop")
        self.assertFalse(state["flags"].get("route_mutated_by_pm"))
        display_plan = read_json(run_root / "display_plan.json")
        self.assertEqual(display_plan["source_event"], "pm_revises_node_acceptance_plan")
        repair_record = read_json(run_root / "routes" / "route-001" / "nodes" / "node-001" / "repairs" / "node_acceptance_plan_revision.json")
        self.assertTrue(repair_record["stale_blocked_plan_is_context_only"])
    def test_model_backed_model_miss_triage_requires_officer_report_refs(self) -> None:
        root = self.make_project()
        self.prepare_current_node_result_for_review(root, packet_id="node-packet-model-miss-invalid")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.deliver_expected_card(root, "pm.model_miss_triage")
        self.deliver_expected_card(root, "pm.event.reviewer_blocked")

        body = self.model_miss_triage_body(root, decision="proceed_with_model_backed_repair")
        body.pop("officer_report_refs")
        with self.assertRaisesRegex(router.RouterError, "officer_report_refs"):
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
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
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
                self.model_miss_triage_body(root, decision="request_officer_model_miss_analysis"),
            ),
        )
        router.record_external_event(root, "pm_registers_role_work_request", self.pm_role_work_request_payload(root))
        index = read_json(run_root / "pm_work_requests" / "index.json")
        self.assertEqual(index["active_request_id"], "model-miss-followup-001")
        self.assertEqual(index["requests"][0]["to_role"], "product_flowguard_officer")
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
                "decision_reason": "PM reviewed the officer model-miss result.",
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
    def test_route_root_node_entry_gap_requires_replanning_not_repair_node(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "route": {
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "route_root",
                    "nodes": [
                        {
                            "node_id": "route_root",
                            "node_kind": "parent",
                            "title": "Route root",
                            "child_node_ids": ["child-001"],
                        },
                        {
                            "node_id": "child-001",
                            "node_kind": "leaf",
                            "parent_node_id": "route_root",
                            "leaf_readiness_gate": {"status": "pass"},
                        },
                    ],
                },
                **self.prior_path_context_review(root, "Parent route draft considered route memory before activation."),
            },
        )
        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "route_root"})
        self.write_current_node_acceptance_plan(root)
        self.deliver_expected_card(root, "reviewer.node_acceptance_plan_review")
        router.record_external_event(
            root,
            "reviewer_blocks_node_acceptance_plan",
            self.role_report_envelope(
                root,
                "reviews/root_node_acceptance_plan_block",
                {
                    "reviewed_by_role": "human_like_reviewer",
                    "passed": False,
                    "blocking_findings": ["route root is still a planning boundary and lacks executable child expansion"],
                },
            ),
        )
        self.close_model_miss_triage(root, output_name="decisions/root_node_entry_gap_triage")

        with self.assertRaisesRegex(router.RouterError, "replanning.*not.*repair node"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "route_root-repair",
                    "repair_return_to_node_id": "route_root",
                    "reason": "root_node_acceptance_plan_review_block",
                    **self.prior_path_context_review(root, "Root planning gap must be replanned before repair is available."),
                },
            )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "route_root")
        self.assertNotEqual(frontier.get("status"), "route_mutation_pending_recheck")
    def test_reviewed_route_activation_uses_pm_draft_without_dummy_fallback(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        self.activate_route(root)

        flow = read_json(run_root / "routes" / "route-001" / "flow.json")
        self.assertEqual(flow["schema_version"], "flowpilot.route.v1")
        self.assertEqual(flow["source"], "pm_activates_reviewed_route")
        self.assertEqual([node["node_id"] for node in flow["nodes"]], ["node-001"])
        self.assertIn("flow.draft.json", flow["activated_from_draft_path"])
        self.assertTrue(flow["activated_from_draft_hash"])
        self.assertNotEqual(flow["nodes"][0].get("title"), "Current node")
    def test_route_activation_rejects_active_node_missing_from_reviewed_route(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "nodes": [{"node_id": "node-001"}],
                **self.prior_path_context_review(root, "Route draft considered prior path context before activation."),
            },
        )
        self.complete_route_checks(root)

        with self.assertRaisesRegex(router.RouterError, "active route node is missing"):
            router.record_external_event(root, "pm_activates_reviewed_route", {"active_node_id": "missing-node"})
    def test_route_mutation_requires_topology_and_resets_route_hard_gates(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-route-hard-gate-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/route_hard_gate_mutation_triage")
        with self.assertRaisesRegex(router.RouterError, "topology_strategy"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "node-001-repair-hard-gate",
                    "reason": "missing_return_target",
                    "stale_evidence": ["node-packet-route-hard-gate-mutation"],
                    **self.prior_path_context_review(root, "Mutation intentionally lacks return target."),
                },
            )

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-repair-hard-gate",
                "repair_return_to_node_id": "node-001",
                "reason": "reviewer_block",
                "stale_evidence": ["node-packet-route-hard-gate-mutation"],
                **self.prior_path_context_review(root, "Mutation includes mainline return target."),
            },
        )
        state = read_json(router.run_state_path(run_root))
        self.assertFalse(state["flags"]["route_activated_by_pm"])
        self.assertTrue(state["flags"]["route_draft_written_by_pm"])
        self.assertFalse(state["flags"]["process_officer_route_check_passed"])
        mutation = read_json(run_root / "routes" / "route-001" / "mutations.json")["items"][-1]
        self.assertEqual(mutation["repair_return_policy"]["repair_return_to_node_id"], "node-001")
        self.assertEqual(mutation["route_topology"]["topology_strategy"], "return_to_original")
    def test_route_mutation_and_final_ledger_have_required_preconditions(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
        self.complete_pre_route_gates(root)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_mutates_route_after_review_block")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_records_final_route_wide_ledger_clean")

        self.activate_route(root)
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-003",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-003", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        _, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-003",
            result_body_text="blocked result",
        )
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-003", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/route_mutation_model_miss_valid")
        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-repair",
                "repair_return_to_node_id": "node-001",
                "reason": "reviewer_block",
                "stale_evidence": ["node-packet-003"],
                **self.prior_path_context_review(root, "Route mutation considered blocked node result and stale evidence."),
            },
        )

        current = read_json(root / ".flowpilot" / "current.json")
        run_root = root / current["current_run_root"]
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-repair")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_route_version"], 2)
        self.assertEqual(read_json(run_root / "routes" / "route-001" / "flow.json")["active_node_id"], "node-001")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        self.assertEqual(draft["candidate_activation_status"], "pending_route_recheck")
        self.assertEqual(draft["route_topology"]["topology_strategy"], "return_to_original")
        self.assertIn("node-001-repair", {node.get("node_id") for node in draft["nodes"]})
        self.assertTrue(self.flag(root, "route_draft_written_by_pm"))

        self.complete_route_checks(root)
        router.record_external_event(
            root,
            "pm_activates_reviewed_route",
            {"route_id": "route-001", "active_node_id": "node-001-repair"},
        )
        frontier = read_json(root / current["current_run_root"] / "execution_frontier.json")
        self.assertEqual(frontier["status"], "current_node_loop")
        self.assertEqual(frontier["active_node_id"], "node-001-repair")
        self.assertEqual(frontier["route_version"], 2)

        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "reviewer_final_backward_replay_passed")
    def test_route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-scoped-route-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/scoped_route_mutation_first_triage")
        first_payload = {
            "repair_node_id": "node-001-repair-v2",
            "repair_return_to_node_id": "node-001",
            "route_version": 2,
            "reason": "first_reviewer_block",
            "stale_evidence": ["node-packet-scoped-route-mutation"],
            **self.prior_path_context_review(root, "First route mutation considered the reviewer block."),
        }
        first = router.record_external_event(root, "pm_mutates_route_after_review_block", first_payload)
        self.assertNotIn("already_recorded", first)
        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        self.assertTrue(state["flags"]["route_mutated_by_pm"])
        self.assertFalse(state["flags"]["node_review_blocked"])
        first_replay = router.record_external_event(root, "pm_mutates_route_after_review_block", first_payload)
        self.assertTrue(first_replay["already_recorded"])
        mutations = read_json(run_root / "routes" / "route-001" / "mutations.json")
        self.assertEqual([item["route_version"] for item in mutations["items"]], [2])

        blocker_path = run_root / "control_blocks" / "control-blocker-scoped-route-mutation.json"
        blocker_rel = self.rel(root, blocker_path)
        blocker = {
            "schema_version": router.CONTROL_BLOCKER_SCHEMA,
            "blocker_id": "control-blocker-scoped-route-mutation",
            "run_id": run_root.name,
            "handling_lane": "pm_repair_decision_required",
            "delivery_status": "delivered",
            "blocker_artifact_path": blocker_rel,
            "target_role": "project_manager",
            "pm_decision_required": True,
            "pm_repair_decision_status": "recorded",
            "repair_transaction_id": "repair-tx-scoped-route-mutation",
            "allowed_resolution_events": ["pm_mutates_route_after_review_block"],
            "created_at": "2026-05-10T00:00:00Z",
        }
        blocker_path.parent.mkdir(parents=True, exist_ok=True)
        blocker_path.write_text(json.dumps(blocker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        state["active_control_blocker"] = dict(blocker)
        state["latest_control_blocker_path"] = blocker_rel
        state["control_blockers"] = [dict(blocker)]
        state["flags"]["node_review_blocked"] = True
        state["flags"]["model_miss_triage_closed"] = True
        router.save_run_state(run_root, state)

        second = router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "control_blocker_id": "control-blocker-scoped-route-mutation",
                "repair_transaction_id": "repair-tx-scoped-route-mutation",
                "repair_node_id": "node-001-repair-v3",
                "repair_return_to_node_id": "node-001-repair-v2",
                "route_version": 3,
                "reason": "second_control_blocker_repair",
                "stale_evidence": ["node-packet-scoped-route-mutation-v2"],
                **self.prior_path_context_review(root, "Second route mutation considered a later control blocker."),
            },
        )

        self.assertNotIn("already_recorded", second)
        state = read_json(state_path)
        self.assertIsNone(state["active_control_blocker"])
        mutations = read_json(run_root / "routes" / "route-001" / "mutations.json")
        self.assertEqual([item["route_version"] for item in mutations["items"]], [2, 3])
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["route_version"], 1)
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-repair-v3")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_route_version"], 3)
        processed = state["external_event_idempotency"]["processed"]["pm_mutates_route_after_review_block"]
        self.assertEqual(len(processed), 2)
    def test_route_mutation_supersede_strategy_does_not_require_return_to_original(self) -> None:
        root = self.make_project()
        run_root, _packet_path, _result_path = self.prepare_current_node_result_for_review(
            root,
            packet_id="node-packet-supersede-route-mutation",
        )
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/supersede_route_mutation_triage")

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-v2",
                "topology_strategy": "supersede_original",
                "superseded_nodes": ["node-001"],
                "reason": "replace invalid original node",
                "stale_evidence": ["node-packet-supersede-route-mutation"],
                **self.prior_path_context_review(root, "Supersede route mutation considered the blocked original node."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "node-001")
        self.assertEqual(frontier["pending_route_mutation"]["candidate_node_id"], "node-001-v2")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        old_node = next(node for node in draft["nodes"] if node.get("node_id") == "node-001")
        replacement = next(node for node in draft["nodes"] if node.get("node_id") == "node-001-v2")
        self.assertEqual(old_node["status"], "superseded")
        self.assertEqual(replacement["topology_strategy"], "supersede_original")
        self.assertIsNone(replacement["repair_return_to_node_id"])

        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "node-001-v2"})
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["active_node_id"], "node-001-v2")
        self.assertEqual(frontier["route_version"], 2)
        active_route = read_json(run_root / "routes" / "route-001" / "flow.json")
        active_old_node = next(node for node in active_route["nodes"] if node.get("node_id") == "node-001")
        self.assertEqual(active_old_node["status"], "superseded")
    def test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)
        self.complete_pre_route_gates(root)
        self.deliver_expected_card(root, "pm.prior_path_context")
        self.deliver_expected_card(root, "pm.route_skeleton")
        router.record_external_event(
            root,
            "pm_writes_route_draft",
            {
                "route": {
                    "schema_version": "flowpilot.route.v1",
                    "route_id": "route-001",
                    "route_version": 1,
                    "active_node_id": "node-001",
                    "nodes": [
                        {
                            "node_id": "route-root",
                            "node_kind": "parent",
                            "title": "Route root",
                            "child_node_ids": ["node-001", "node-002"],
                        },
                        {
                            "node_id": "node-001",
                            "node_kind": "leaf",
                            "parent_node_id": "route-root",
                            "title": "First branch",
                            "leaf_readiness_gate": {"status": "pass"},
                        },
                        {
                            "node_id": "node-002",
                            "node_kind": "leaf",
                            "parent_node_id": "route-root",
                            "title": "Sibling branch",
                            "leaf_readiness_gate": {"status": "pass"},
                        },
                    ],
                },
                **self.prior_path_context_review(root, "Route draft includes sibling branches for replacement policy."),
            },
        )
        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "node-001"})
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="node-packet-sibling-replacement",
            from_role="project_manager",
            to_role="worker_a",
            node_id="node-001",
            body_text="current node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "node-packet-sibling-replacement", "packet_envelope_path": packet_path})
        self.apply_until_action(root, "relay_current_node_packet")
        _, result_path = self.submit_current_node_result_via_active_holder(
            root,
            packet_id="node-packet-sibling-replacement",
            result_body_text="reviewable result",
        )
        router.record_external_event(root, "worker_current_node_result_returned", {"packet_id": "node-packet-sibling-replacement", "result_envelope_path": result_path})
        self.absorb_current_node_results_with_pm(root, [result_path])
        self.deliver_expected_card(root, "reviewer.worker_result_review")
        router.record_external_event(root, "current_node_reviewer_blocks_result")
        self.close_model_miss_triage(root, output_name="decisions/sibling_branch_replacement_triage")

        with self.assertRaisesRegex(router.RouterError, "affected_sibling_nodes"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "node-002-v2",
                    "topology_strategy": "sibling_branch_replacement",
                    "repair_of_node_id": "node-002",
                    "replay_scope_node_id": "route-root",
                    "stale_evidence": ["node-002-old-proof"],
                    **self.prior_path_context_review(root, "Invalid sibling replacement intentionally lacks affected sibling list."),
                },
            )

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-002-v2",
                "topology_strategy": "sibling_branch_replacement",
                "repair_of_node_id": "node-002",
                "affected_sibling_nodes": ["node-002"],
                "replay_scope_node_id": "route-root",
                "reason": "replace invalid sibling branch",
                "stale_evidence": ["node-002-old-proof"],
                **self.prior_path_context_review(root, "Sibling branch replacement considered stale sibling proof and replay scope."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["pending_route_mutation"]["topology_strategy"], "sibling_branch_replacement")
        self.assertEqual(frontier["pending_route_mutation"]["affected_sibling_nodes"], ["node-002"])
        self.assertEqual(frontier["pending_route_mutation"]["replay_scope_node_id"], "route-root")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        old_sibling = next(node for node in draft["nodes"] if node.get("node_id") == "node-002")
        replacement = next(node for node in draft["nodes"] if node.get("node_id") == "node-002-v2")
        self.assertEqual(old_sibling["status"], "superseded")
        self.assertEqual(replacement["topology_strategy"], "sibling_branch_replacement")
        self.assertEqual(replacement["affected_sibling_nodes"], ["node-002"])
        self.assertEqual(replacement["replay_scope_node_id"], "route-root")
        stale_ledger = read_json(run_root / "evidence" / "stale_evidence_ledger.json")
        self.assertIn("node-002-old-proof", {item["evidence_id"] for item in stale_ledger["items"]})
        packet_ledger = read_json(run_root / "packet_ledger.json")
        self.assertEqual(packet_ledger["active_packet_status"], "superseded")
        self.assertEqual(packet_ledger["route_mutation_packet_disposition"]["topology_strategy"], "sibling_branch_replacement")

        state_path = router.run_state_path(run_root)
        state = read_json(state_path)
        original_state = json.loads(json.dumps(state))
        state.setdefault("flags", {})["pm_final_ledger_card_delivered"] = True
        router.save_run_state(run_root, state)
        try:
            with self.assertRaisesRegex(router.RouterError, "route mutation pending recheck"):
                router.record_external_event(root, "pm_records_final_route_wide_ledger_clean", self.final_ledger_payload(root))
        finally:
            router.save_run_state(run_root, original_state)

        self.complete_route_checks(root)
        router.record_external_event(root, "pm_activates_reviewed_route", {"route_id": "route-001", "active_node_id": "node-002-v2"})
        active_route = read_json(run_root / "routes" / "route-001" / "flow.json")
        active_old_sibling = next(node for node in active_route["nodes"] if node.get("node_id") == "node-002")
        self.assertEqual(active_old_sibling["status"], "superseded")
        effective_ids = {
            str(node.get("node_id"))
            for node in router._effective_route_nodes(
                active_route,
                read_json(run_root / "routes" / "route-001" / "mutations.json"),
            )
        }
        self.assertIn("node-002-v2", effective_ids)
        self.assertNotIn("node-002", effective_ids)
    def test_parent_backward_targets_require_current_child_completion_ledgers(self) -> None:
        root = self.make_project()
        self.boot_to_controller(root)
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
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.deliver_current_node_cards(root)
        state_path = router.run_state_path(self.run_root_for(root))
        state = read_json(state_path)
        state["flags"]["pm_parent_backward_targets_card_delivered"] = True
        router.save_run_state(self.run_root_for(root), state)
        with self.assertRaisesRegex(router.RouterError, "requires legal route action build_parent_backward_targets"):
            router.record_external_event(root, "pm_builds_parent_backward_targets")
    def test_parent_node_requires_backward_replay_before_completion(self) -> None:
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
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.seed_child_completion_ledger(root, "child-001")
        self.deliver_current_node_cards(root)
        packet = packet_runtime.create_packet(
            root,
            packet_id="parent-node-packet",
            from_role="project_manager",
            to_role="worker_a",
            node_id="parent-001",
            body_text="parent node work",
            metadata={"route_version": 1},
        )
        packet_path = packet["body_path"].replace("packet_body.md", "packet_envelope.json")
        with self.assertRaises(router.RouterError):
            router.record_external_event(root, "pm_registers_current_node_packet", {"packet_id": "parent-node-packet", "packet_envelope_path": packet_path})

        self.complete_parent_backward_replay_if_due(root)
        router.record_external_event(root, "pm_completes_parent_node_from_backward_replay")
        frontier = read_json(run_root / "execution_frontier.json")
        self.assertIn("parent-001", frontier["completed_nodes"])
        self.assertTrue((run_root / "routes" / "route-001" / "nodes" / "parent-001" / "parent_backward_replay.json").exists())
    def test_parent_backward_non_continue_decision_mutates_route_and_requires_rerun(self) -> None:
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
                        {"node_id": "child-001", "status": "completed", "title": "Child node"},
                    ],
                },
            },
        )
        self.seed_child_completion_ledger(root, "child-001")
        self.deliver_current_node_cards(root)
        self.deliver_expected_card(root, "pm.parent_backward_targets")
        router.record_external_event(root, "pm_builds_parent_backward_targets")
        self.deliver_expected_card(root, "reviewer.parent_backward_replay")
        router.record_external_event(
            root,
            "reviewer_passes_parent_backward_replay",
            self.role_report_envelope(
                root,
                "reviews/parent_backward_replay_noncontinue",
                {"reviewed_by_role": "human_like_reviewer", "passed": True},
            ),
        )
        self.deliver_expected_card(root, "pm.parent_segment_decision")
        router.record_external_event(
            root,
            "pm_records_parent_segment_decision",
            self.role_decision_envelope(
                root,
                "decisions/parent_segment_repair_decision",
                {
                    "decision_owner": "project_manager",
                    "decision": "repair_existing_child",
                    "repair_return_to_node_id": "parent-001",
                    **self.prior_path_context_review(root, "Parent segment repair decision considered prior route memory and replay evidence."),
                },
            ),
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "route_mutation_pending_recheck")
        self.assertEqual(frontier["active_node_id"], "parent-001")
        self.assertNotEqual(frontier["pending_route_mutation"]["candidate_node_id"], "parent-001")
        decision = read_json(run_root / "routes" / "route-001" / "nodes" / "parent-001" / "pm_parent_segment_decision.json")
        self.assertTrue(decision["same_parent_replay_rerun_required"])
