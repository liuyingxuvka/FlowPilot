from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationTransactionRuntimeTests(FlowPilotRouterRuntimeTestBase):
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
