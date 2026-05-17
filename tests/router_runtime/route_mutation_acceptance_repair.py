from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationAcceptanceRepairRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
