from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "flowpilot" / "assets"))

import flowpilot_router as router  # noqa: E402


class FlowPilotRouteAuthoritySingularityTests(unittest.TestCase):
    def _make_project(self) -> tuple[Path, Path]:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-route-authority-"))
        run_root = root / ".flowpilot" / "runs" / "run-test"
        run_root.mkdir(parents=True)
        runtime_kit = run_root / "runtime_kit"
        runtime_kit.mkdir()
        (runtime_kit / "route_action_policy_registry.json").write_text("{}\n", encoding="utf-8")
        return root, run_root

    def test_route_authority_snapshot_marks_missing_owner(self) -> None:
        root, run_root = self._make_project()

        snapshot = router._route_authority_snapshot(
            root,
            run_root,
            policy_by_id={
                "record_parent_segment_decision": {
                    "action_id": "record_parent_segment_decision",
                    "actor_roles": [],
                    "required_repair_command": "submit_pm_parent_segment_decision",
                    "router_events": ["pm_records_parent_segment_decision"],
                    "transaction_type": "route_progression",
                    "commit_targets": ["run_state"],
                }
            },
            frontier={"active_route_id": "route-001", "route_version": 1, "active_node_id": "parent-001"},
            active_node_kind="parent",
            legal_ids=["record_parent_segment_decision"],
            blocking_reasons=[],
        )

        self.assertEqual(snapshot["current_owner"], "owner_missing")
        self.assertFalse(snapshot["single_authority"])

    def test_route_authority_snapshot_marks_owner_conflict(self) -> None:
        root, run_root = self._make_project()

        snapshot = router._route_authority_snapshot(
            root,
            run_root,
            policy_by_id={
                "record_parent_segment_decision": {
                    "action_id": "record_parent_segment_decision",
                    "actor_roles": ["project_manager"],
                    "owner_role": "project_manager",
                    "required_repair_command": "submit_pm_parent_segment_decision",
                    "router_events": ["pm_records_parent_segment_decision"],
                    "transaction_type": "route_progression",
                    "commit_targets": ["run_state"],
                },
                "review_parent_backward_replay": {
                    "action_id": "review_parent_backward_replay",
                    "actor_roles": ["human_like_reviewer"],
                    "owner_role": "human_like_reviewer",
                    "required_repair_command": "submit_parent_backward_replay_review",
                    "router_events": ["reviewer_passes_parent_backward_replay"],
                    "transaction_type": "reviewer_gate_result",
                    "commit_targets": ["run_state"],
                },
            },
            frontier={"active_route_id": "route-001", "route_version": 1, "active_node_id": "parent-001"},
            active_node_kind="parent",
            legal_ids=["record_parent_segment_decision", "review_parent_backward_replay"],
            blocking_reasons=[],
        )

        self.assertEqual(snapshot["current_owner"], "owner_conflict")
        self.assertFalse(snapshot["single_authority"])
        self.assertEqual(snapshot["required_repair_command"], "choose_one_legal_action_by_id")


if __name__ == "__main__":
    unittest.main()
