from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationParentBackwardRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
                to_role="worker",
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
