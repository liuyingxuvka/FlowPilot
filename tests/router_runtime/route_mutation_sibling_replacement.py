from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationSiblingReplacementRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
                to_role="worker",
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
