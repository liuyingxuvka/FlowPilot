from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import flowpilot_user_flow_diagram as route_sign  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotUserFlowDiagramTests(unittest.TestCase):
    def make_project(self, *, active_node: str, route_mutation: dict | None = None) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-route-sign-"))
        run_root = root / ".flowpilot" / "runs" / "run-test"
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        _write_json(run_root / "state.json", {"active_route": "route-001"})
        nodes = [
            ("node-001-startup", "complete"),
            ("node-002-product-function-strategy", "complete"),
            ("node-003-design-language-concepts", "complete"),
            ("node-004-desktop-implementation", "running" if active_node.endswith("implementation") else "complete"),
            ("node-005-screenshot-interaction-qa", "complete"),
            ("node-006-final-verification", "running" if active_node.endswith("verification") else "pending"),
        ]
        _write_json(
            run_root / "routes" / "route-001" / "flow.json",
            {
                "route_id": "route-001",
                "route_version": 3,
                "status": "active",
                "nodes": [
                    {
                        "id": node_id,
                        "status": status,
                        "summary": node_id,
                        "allowed_next": [],
                    }
                    for node_id, status in nodes
                ],
            },
        )
        _write_json(
            run_root / "execution_frontier.json",
            {
                "active_route": "route-001",
                "route_version": 3,
                "frontier_version": 5,
                "active_node": active_node,
                "current_subnode": "complete" if active_node.endswith("verification") else "repair",
                "next_gate": "FlowGuard route checks" if active_node.endswith("verification") else "human review repair",
                "current_mainline": [node_id for node_id, _ in nodes],
                "next_node": "complete" if active_node.endswith("verification") else "node-005-screenshot-interaction-qa",
                "route_mutation": route_mutation or {"pending": False, "failed_review": {"blocking": False}},
            },
        )
        return root

    def test_final_verification_classifies_as_verification_not_modeling(self) -> None:
        root = self.make_project(active_node="node-006-final-verification")
        payload = route_sign.generate(
            root,
            write=False,
            trigger="key_node_change",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
        )

        self.assertEqual(payload["current_stage"], "verification")
        self.assertIn("FlowPilot Route Sign", payload["markdown"])
        self.assertIn("Now: node-006-final-verification", payload["mermaid"])
        self.assertNotIn("FlowGuard Model<br/>Now", payload["mermaid"])

    def test_major_node_entry_requires_chat_route_sign(self) -> None:
        root = self.make_project(active_node="node-004-desktop-implementation")
        payload = route_sign.generate(
            root,
            write=False,
            trigger="major_node_entry",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
        )

        self.assertTrue(payload["chat_display_required"])
        self.assertIn("Trigger: `major_node_entry`", payload["markdown"])
        self.assertIn("mark displayed only after this exact Mermaid block appears", payload["markdown"])

    def test_active_run_and_current_node_aliases_resolve_current_route(self) -> None:
        root = self.make_project(active_node="node-004-desktop-implementation")
        current_path = root / ".flowpilot" / "current.json"
        current_path.write_text(
            json.dumps(
                {
                    "active_run_id": "run-test",
                    "active_route_id": "route-001",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        frontier_path = root / ".flowpilot" / "runs" / "run-test" / "execution_frontier.json"
        frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
        frontier["route_id"] = frontier.pop("active_route")
        frontier["current_node"] = frontier.pop("active_node")
        frontier_path.write_text(json.dumps(frontier, indent=2), encoding="utf-8")
        payload = route_sign.generate(
            root,
            write=False,
            trigger="major_node_entry",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
        )

        self.assertEqual(payload["run_id"], "run-test")
        self.assertEqual(payload["active_route"], "route-001")
        self.assertEqual(payload["active_node"], "node-004-desktop-implementation")
        self.assertIn("node-004-desktop-implementation", payload["mermaid"])

    def test_review_failure_shows_return_edge_and_passes_when_chat_displayed(self) -> None:
        root = self.make_project(
            active_node="node-004-desktop-implementation",
            route_mutation={
                "pending": True,
                "reason": "human review failed",
                "failed_review": {
                    "blocking": True,
                    "failed_child": "node-005-screenshot-interaction-qa",
                    "repair_target": "node-004-desktop-implementation",
                },
            },
        )
        payload = route_sign.generate(
            root,
            write=False,
            trigger="review_failure",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=True,
            mark_ui_displayed=False,
            reviewer_check=True,
        )

        self.assertTrue(payload["ok"])
        self.assertTrue(payload["return_or_repair"]["edge_present"])
        self.assertIn('returns for repair', payload["mermaid"])
        self.assertIn("node-004-desktop-implementation", payload["markdown"])

    def test_reviewer_blocks_closed_cockpit_without_chat_display(self) -> None:
        root = self.make_project(active_node="node-006-final-verification")
        payload = route_sign.generate(
            root,
            write=False,
            trigger="key_node_change",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=True,
        )

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["review"]["status"], "blocked")
        self.assertIn("not confirmed in chat", " ".join(payload["review"]["blocking_findings"]))

    def test_write_records_display_packet_and_review_evidence(self) -> None:
        root = self.make_project(active_node="node-006-final-verification")
        payload = route_sign.generate(
            root,
            write=True,
            trigger="user_request",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=True,
            mark_ui_displayed=False,
            reviewer_check=True,
        )

        display_packet = json.loads(Path(payload["display_packet_path"]).read_text(encoding="utf-8"))
        review = json.loads(Path(payload["review_path"]).read_text(encoding="utf-8"))
        self.assertEqual(display_packet["diagram_kind"], "flowpilot_realtime_route_sign")
        self.assertTrue(display_packet["chat_display_required"])
        self.assertEqual(review["status"], "pass")


if __name__ == "__main__":
    unittest.main()
