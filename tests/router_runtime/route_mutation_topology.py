from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationTopologyRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
