from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationPreconditionRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
            self.assertFalse(state["flags"].get("flowguard_operator_route_scope_route_check_passed", False))
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
                to_role="worker",
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
            run_root = root / current["run_root"]
            frontier = read_json(root / current["run_root"] / "execution_frontier.json")
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
            frontier = read_json(root / current["run_root"] / "execution_frontier.json")
            self.assertEqual(frontier["status"], "current_node_loop")
            self.assertEqual(frontier["active_node_id"], "node-001-repair")
            self.assertEqual(frontier["route_version"], 2)

            with self.assertRaises(router.RouterError):
                router.record_external_event(root, "reviewer_final_backward_replay_passed")
