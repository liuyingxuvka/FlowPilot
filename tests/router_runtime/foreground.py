from __future__ import annotations

from tests.router_runtime.common import *  # noqa: F403
from tests.router_runtime.common import FlowPilotRouterRuntimeTestBase


class ForegroundRuntimeTests(FlowPilotRouterRuntimeTestBase):
    def test_run_until_wait_folds_nonblocking_display_sync(self) -> None:
        root = self.make_project()
        run_root = self.boot_to_controller(root)

        first = router.next_action(root)
        self.assertEqual(first["action_type"], "sync_display_plan")
        self.assertFalse(first["requires_user_dialog_display_confirmation"])
        self.assertIsNone(first.get("postcondition"))

        result = router.run_until_wait(root, max_steps=3)

        self.assertEqual(result["folded_command"], "run-until-wait")
        self.assertGreaterEqual(result["folded_applied_count"], 1)
        self.assertEqual(result["folded_applied_actions"][0]["action_type"], "sync_display_plan")
        state = read_json(router.run_state_path(run_root))
        self.assertTrue(state["flags"]["visible_plan_synced"])
        self.assertIn("visible_plan_sync", state)
    def test_progress_summary_counts_nested_active_path(self) -> None:
        root = self.make_project()
        run_root = root / ".flowpilot" / "runs" / "run-progress"
        run_root.mkdir(parents=True)
        route = {
            "route_id": "route-progress",
            "nodes": [
                {
                    "node_id": "route-root",
                    "node_kind": "root",
                    "depth": 0,
                    "child_node_ids": ["parent-done", "parent-current"],
                },
                {"node_id": "parent-done", "title": "Finished parent", "status": "completed"},
                {
                    "node_id": "parent-current",
                    "title": "Current parent",
                    "child_node_ids": ["child-done", "child-current"],
                },
                {
                    "node_id": "child-done",
                    "parent_node_id": "parent-current",
                    "title": "Finished child",
                    "status": "completed",
                },
                {
                    "node_id": "child-current",
                    "parent_node_id": "parent-current",
                    "title": "Current child",
                    "child_node_ids": ["leaf-done", "leaf-current"],
                },
                {
                    "node_id": "leaf-done",
                    "parent_node_id": "child-current",
                    "title": "Finished leaf",
                    "status": "completed",
                },
                {"node_id": "leaf-current", "parent_node_id": "child-current", "title": "Current leaf"},
            ],
        }
        progress = router._build_progress_summary(  # type: ignore[attr-defined]
            run_root,
            {"run_id": "run-progress"},
            route=route,
            frontier={"completed_nodes": ["parent-done", "child-done", "leaf-done"]},
            active_node_id="leaf-current",
            state_kind="running",
        )

        self.assertEqual(progress["level_count"], 3)
        self.assertEqual(progress["overall_total_nodes"], 6)
        self.assertEqual(progress["overall_completed_nodes"], 3)
        self.assertEqual([level["current_index"] for level in progress["levels"]], [2, 2, 2])
        self.assertEqual([level["total_nodes"] for level in progress["levels"]], [2, 2, 2])
        self.assertEqual([level["completed_nodes"] for level in progress["levels"]], [1, 1, 1])
        self.assertEqual([level["current_label"] for level in progress["levels"]], [
            "Current parent",
            "Current child",
            "Current leaf",
        ])
        self.assertIsNone(progress["elapsed_seconds"])
        self.assertTrue(progress["metadata_only"])
        self.assertTrue(progress["sealed_body_fields_excluded"])
        self.assertTrue(progress["diagnostic_paths_excluded"])
