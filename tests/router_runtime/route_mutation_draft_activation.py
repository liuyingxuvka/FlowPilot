from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class RouteMutationDraftActivationRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_pm_route_draft_preserves_role_authored_repair_policy_fields(self) -> None:
            root = self.make_project()
            run_root = self.boot_to_controller(root)
            self.complete_startup_runtime_entry(root)
            self.complete_root_contract_before_child_skill_gates(root)
            self.complete_child_skill_gates(root)
            self.complete_implementation_intent_bridge(root)

            self.deliver_expected_card(root, "pm.prior_path_context")
            self.deliver_expected_card(root, "pm.route_skeleton")

            nodes = [{"node_id": "node-001"}]
            repair_policy = {
                "policy_id": "route-001-repair-return-policy-test",
                "branch_table": [
                    {
                        "trigger": "reviewer_block",
                        "rejoin_target": "node-001",
                        "rerun_checks": ["flowguard_operator_route_scope_route_process_check"],
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

