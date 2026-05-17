from __future__ import annotations

import json
from pathlib import Path
import unittest

from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase, read_json, router


ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA = "flowpilot.test.route_mutation_child_contract.v1"
FORBIDDEN_PARENT_FLOW_HELPERS = (
    "boot_to_controller",
    "complete_pre_route_gates",
    "complete_route_checks",
    "deliver_current_node_cards",
    "prepare_current_node_result_for_review",
    "close_model_miss_triage",
)


class RouteMutationContractHarness(FlowPilotRouterRuntimeTestBase):
    """Parent route-mutation tests consume a child contract, not child flow."""

    def boot_to_controller(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must not replay boot_to_controller")

    def complete_pre_route_gates(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must not replay pre-route gates")

    def complete_route_checks(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must not replay route checks")

    def deliver_current_node_cards(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must not deliver child node cards")

    def prepare_current_node_result_for_review(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must not replay packet/result/review setup")

    def close_model_miss_triage(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("parent route-mutation contract tests must consume closed triage contract state")

    def seed_route_mutation_child_contract(
        self,
        root: Path,
        *,
        route_shape: str = "leaf",
        active_node_id: str = "node-001",
        review_block_flag: str = "node_review_blocked",
        model_miss_closed: bool = True,
        packet_id: str | None = None,
    ) -> tuple[Path, dict]:
        run_root = self.write_minimal_run(root, "run-001", status="running")
        self.write_current_focus(root, run_root)
        self._write_route_action_policy_contract(run_root)

        route = self._route_for_shape(route_shape, active_node_id=active_node_id)
        route_id = str(route["route_id"])
        route_root = run_root / "routes" / route_id
        route_root.mkdir(parents=True, exist_ok=True)
        router.write_json(route_root / "flow.json", route)

        frontier = {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_root.name,
            "status": "current_node_loop",
            "active_route_id": route_id,
            "active_node_id": active_node_id,
            "active_path": self._active_path_for_shape(route_shape, active_node_id),
            "active_leaf_node_id": active_node_id if route_shape != "root_gap" else None,
            "route_version": 1,
            "updated_at": router.utc_now(),
            "source": ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA,
        }
        if route_shape == "root_gap":
            frontier["completed_nodes"] = []
        if packet_id:
            frontier["active_packet_id"] = packet_id
        router.write_json(run_root / "execution_frontier.json", frontier)
        if packet_id:
            self._write_active_packet_contract(run_root, packet_id=packet_id, node_id=active_node_id)

        state = read_json(router.run_state_path(run_root))
        state["status"] = "controller_ready"
        state["phase"] = "current_node_loop"
        state["holder"] = "controller"
        if packet_id:
            state["current_node_packet_id"] = packet_id
        flags = state.setdefault("flags", {})
        flags["controller_core_loaded"] = True
        flags["route_activated_by_pm"] = True
        flags[review_block_flag] = True
        flags["model_miss_triage_closed"] = model_miss_closed
        router.save_run_state(run_root, state)

        contract = {
            "schema_version": ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA,
            "contract_id": f"route-mutation-{route_shape}-{review_block_flag}",
            "child_suite_owner": "child.route_mutation_review_block_contract",
            "parent_suite_owner": "parent.route_mutation_event_contract",
            "route_shape": route_shape,
            "input_contract": {
                "run_root": router.project_relative(root, run_root),
                "active_route_id": route_id,
                "active_node_id": active_node_id,
                "review_block_flag": review_block_flag,
                "model_miss_triage_closed": model_miss_closed,
                "legal_route_action_state": True,
                "packet_id": packet_id,
            },
            "output_contract": {
                "parent_allowed_event": "pm_mutates_route_after_review_block",
                "parent_owned_outputs": [
                    "routes/route-001/mutations.json",
                    "routes/route-001/flow.draft.json",
                    "execution_frontier.json.pending_route_mutation",
                    "evidence/stale_evidence_ledger.json",
                    "packet_ledger.json.route_mutation_packet_disposition",
                ],
            },
            "forbidden_parent_helpers": list(FORBIDDEN_PARENT_FLOW_HELPERS),
        }
        contract_path = run_root / "test_contracts" / "route_mutation_child_contract.json"
        router.write_json(contract_path, contract)
        return run_root, contract

    def _write_route_action_policy_contract(self, run_root: Path) -> None:
        policy_root = run_root / "runtime_kit"
        policy_root.mkdir(parents=True, exist_ok=True)
        router.write_json(
            policy_root / "route_action_policy_registry.json",
            router.read_json(router.runtime_kit_source() / "route_action_policy_registry.json"),
        )

    def _route_for_shape(self, route_shape: str, *, active_node_id: str) -> dict:
        if route_shape == "sibling":
            return {
                "schema_version": "flowpilot.route.v1",
                "route_id": "route-001",
                "route_version": 1,
                "active_node_id": active_node_id,
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
            }
        if route_shape == "root_gap":
            return {
                "schema_version": "flowpilot.route.v1",
                "route_id": "route-001",
                "route_version": 1,
                "active_node_id": active_node_id,
                "nodes": [
                    {
                        "node_id": active_node_id,
                        "node_kind": "parent",
                        "title": "Route root",
                        "child_node_ids": ["node-001"],
                    },
                    {
                        "node_id": "node-001",
                        "node_kind": "leaf",
                        "parent_node_id": active_node_id,
                        "title": "Executable child",
                        "leaf_readiness_gate": {"status": "pass"},
                    },
                ],
            }
        return {
            "schema_version": "flowpilot.route.v1",
            "route_id": "route-001",
            "route_version": 1,
            "active_node_id": active_node_id,
            "nodes": [
                {
                    "node_id": active_node_id,
                    "node_kind": "leaf",
                    "title": "Current node",
                    "leaf_readiness_gate": {"status": "pass"},
                }
            ],
            "source": ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA,
        }

    def _active_path_for_shape(self, route_shape: str, active_node_id: str) -> list[str]:
        if route_shape == "sibling":
            return ["route-root", active_node_id]
        return [active_node_id]

    def _write_active_packet_contract(self, run_root: Path, *, packet_id: str, node_id: str) -> None:
        router.write_json(
            run_root / "packet_ledger.json",
            {
                "schema_version": "flowpilot.packet_ledger.v1",
                "run_id": run_root.name,
                "active_packet_id": packet_id,
                "active_packet_status": "active",
                "active_packet_holder": "worker_a",
                "packets": [
                    {
                        "packet_id": packet_id,
                        "node_id": node_id,
                        "status": "active",
                        "active_packet_status": "active",
                        "active_packet_holder": "worker_a",
                    }
                ],
            },
        )

    def write_delivered_control_blocker(self, root: Path, run_root: Path) -> dict:
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
        state = read_json(router.run_state_path(run_root))
        state["active_control_blocker"] = dict(blocker)
        state["latest_control_blocker_path"] = blocker_rel
        state["control_blockers"] = [dict(blocker)]
        state["flags"]["node_review_blocked"] = True
        state["flags"]["model_miss_triage_closed"] = True
        router.save_run_state(run_root, state)
        return blocker


class TestRouteMutationChildContractFixture(RouteMutationContractHarness):
    def test_child_contract_binds_parent_io_without_slow_setup(self) -> None:
        root = self.make_project()
        run_root, contract = self.seed_route_mutation_child_contract(
            root,
            packet_id="node-packet-contract",
        )

        self.assertEqual(contract["schema_version"], ROUTE_MUTATION_CHILD_CONTRACT_SCHEMA)
        self.assertEqual(contract["input_contract"]["active_node_id"], "node-001")
        self.assertEqual(contract["input_contract"]["review_block_flag"], "node_review_blocked")
        self.assertEqual(contract["output_contract"]["parent_allowed_event"], "pm_mutates_route_after_review_block")
        self.assertIn("prepare_current_node_result_for_review", contract["forbidden_parent_helpers"])

        state = read_json(router.run_state_path(run_root))
        legal_ids = router._legal_next_action_ids(root, run_root, state)
        self.assertIn("mutate_route", legal_ids)


class TestRouteMutationParentContracts(RouteMutationContractHarness):
    def test_parent_contract_review_block_route_mutation_requires_closed_model_miss_triage(self) -> None:
        root = self.make_project()
        self.seed_route_mutation_child_contract(root, model_miss_closed=False)

        with self.assertRaisesRegex(router.RouterError, "model[_-]miss"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "node-001-repair",
                    "repair_return_to_node_id": "node-001",
                    "reason": "reviewer_block",
                    **self.prior_path_context_review(root, "Parent contract rejects mutation before closed triage."),
                },
            )

    def test_parent_contract_route_mutation_new_transaction_is_not_swallowed_by_old_flag(self) -> None:
        root = self.make_project()
        run_root, _contract = self.seed_route_mutation_child_contract(root)

        first_payload = {
            "repair_node_id": "node-001-repair-v2",
            "repair_return_to_node_id": "node-001",
            "route_version": 2,
            "reason": "first_reviewer_block",
            "stale_evidence": ["node-packet-scoped-route-mutation"],
            **self.prior_path_context_review(root, "First parent contract mutation considered the review block."),
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

        self.write_delivered_control_blocker(root, run_root)
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
                **self.prior_path_context_review(root, "Second parent contract mutation considered a later blocker."),
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

    def test_parent_contract_route_mutation_supersede_strategy_does_not_require_return_to_original(self) -> None:
        root = self.make_project()
        run_root, _contract = self.seed_route_mutation_child_contract(root)

        router.record_external_event(
            root,
            "pm_mutates_route_after_review_block",
            {
                "repair_node_id": "node-001-v2",
                "topology_strategy": "supersede_original",
                "superseded_nodes": ["node-001"],
                "reason": "replace invalid original node",
                "stale_evidence": ["node-packet-supersede-route-mutation"],
                **self.prior_path_context_review(root, "Supersede parent contract considered the blocked node."),
            },
        )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["pending_route_mutation"]["topology_strategy"], "supersede_original")
        draft = read_json(run_root / "routes" / "route-001" / "flow.draft.json")
        old_node = next(node for node in draft["nodes"] if node.get("node_id") == "node-001")
        replacement = next(node for node in draft["nodes"] if node.get("node_id") == "node-001-v2")
        self.assertEqual(old_node["status"], "superseded")
        self.assertEqual(replacement["topology_strategy"], "supersede_original")
        self.assertIsNone(replacement["repair_return_to_node_id"])

    def test_parent_contract_route_root_entry_gap_requires_replanning_not_repair_node(self) -> None:
        root = self.make_project()
        run_root, _contract = self.seed_route_mutation_child_contract(
            root,
            route_shape="root_gap",
            active_node_id="route-root",
            review_block_flag="node_acceptance_plan_review_blocked",
        )

        with self.assertRaisesRegex(router.RouterError, "replanning.*not.*repair node"):
            router.record_external_event(
                root,
                "pm_mutates_route_after_review_block",
                {
                    "repair_node_id": "route-root-entry-repair",
                    "repair_return_to_node_id": "route-root",
                    "reason": "node_acceptance_plan_review_block",
                    **self.prior_path_context_review(root, "Root entry gaps require replanning."),
                },
            )

        frontier = read_json(run_root / "execution_frontier.json")
        self.assertEqual(frontier["status"], "current_node_loop")
        self.assertEqual(frontier["active_node_id"], "route-root")
        self.assertFalse((run_root / "routes" / "route-001" / "mutations.json").exists())

    def test_parent_contract_sibling_branch_replacement_blocks_old_sibling_proof(self) -> None:
        root = self.make_project()
        run_root, _contract = self.seed_route_mutation_child_contract(
            root,
            route_shape="sibling",
            packet_id="node-packet-sibling-replacement",
        )

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
                    **self.prior_path_context_review(root, "Invalid sibling contract lacks affected sibling list."),
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
                **self.prior_path_context_review(root, "Sibling parent contract considered stale sibling proof."),
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
        self.assertEqual(
            packet_ledger["route_mutation_packet_disposition"]["topology_strategy"],
            "sibling_branch_replacement",
        )


if __name__ == "__main__":
    unittest.main()
