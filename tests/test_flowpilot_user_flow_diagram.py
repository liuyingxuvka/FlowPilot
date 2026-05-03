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

    def write_legacy_layout(self, root: Path, *, active_route: str = "legacy-route") -> None:
        flowpilot_root = root / ".flowpilot"
        _write_json(flowpilot_root / "state.json", {"active_route": active_route})
        _write_json(
            flowpilot_root / "execution_frontier.json",
            {
                "active_route": active_route,
                "route_version": 1,
                "frontier_version": 1,
                "active_node": "legacy-node",
                "next_gate": "legacy execution",
                "current_mainline": ["legacy-node", "legacy-complete"],
            },
        )
        _write_json(
            flowpilot_root / "routes" / active_route / "flow.json",
            {
                "route_id": active_route,
                "route_version": 1,
                "status": "active",
                "nodes": [
                    {"id": "legacy-node", "status": "running", "summary": "legacy"},
                    {"id": "legacy-complete", "status": "pending", "summary": "legacy"},
                ],
            },
        )

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

    def test_active_run_pointer_is_authoritative_over_legacy_state(self) -> None:
        root = self.make_project(active_node="node-004-desktop-implementation")
        self.write_legacy_layout(root)

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

        self.assertEqual(payload["flowpilot_layout"], "run_scoped")
        self.assertEqual(payload["flowpilot_path_status"], "ok")
        self.assertEqual(payload["active_route"], "route-001")
        self.assertEqual(payload["active_node"], "node-004-desktop-implementation")
        self.assertIn(str(root / ".flowpilot" / "runs" / "run-test"), payload["source_frontier_path"])
        self.assertNotIn("legacy-node", payload["mermaid"])

    def test_missing_active_run_blocks_instead_of_falling_back_to_legacy_state(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-route-sign-missing-run-"))
        _write_json(root / ".flowpilot" / "current.json", {"active_run_id": "missing-run"})
        self.write_legacy_layout(root)

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

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["flowpilot_layout"], "run_scoped")
        self.assertEqual(payload["flowpilot_path_status"], "blocked")
        self.assertEqual(payload["display_gate_status"], "blocked_degraded_source")
        self.assertIn("Active FlowPilot run root is missing", " ".join(payload["flowpilot_path_findings"]))
        self.assertIn(str(root / ".flowpilot" / "runs" / "missing-run"), payload["source_frontier_path"])
        self.assertIsNone(payload["active_route"])
        self.assertNotIn("legacy-node", payload["mermaid"])

    def test_invalid_active_run_root_blocks_instead_of_falling_back_to_legacy_state(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-route-sign-invalid-run-"))
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "active_run_id": "bad-run",
                "active_run_root": ".flowpilot/current.json",
            },
        )
        self.write_legacy_layout(root)

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

        self.assertFalse(payload["ok"])
        self.assertEqual(payload["flowpilot_path_status"], "blocked")
        self.assertEqual(payload["display_gate_status"], "blocked_degraded_source")
        self.assertIn("outside .flowpilot/runs", " ".join(payload["flowpilot_path_findings"]))
        self.assertIsNone(payload["active_route"])
        self.assertNotIn("legacy-node", payload["mermaid"])

    def test_legacy_layout_is_used_only_without_active_run_pointer(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-route-sign-legacy-"))
        self.write_legacy_layout(root)

        payload = route_sign.generate(
            root,
            write=False,
            trigger="user_request",
            cockpit_open=False,
            display_surface="chat",
            mark_chat_displayed=False,
            mark_ui_displayed=False,
            reviewer_check=False,
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["flowpilot_layout"], "legacy")
        self.assertEqual(payload["flowpilot_path_status"], "ok")
        self.assertFalse(payload["current_declares_run"])
        self.assertEqual(payload["active_route"], "legacy-route")
        self.assertEqual(payload["active_node"], "legacy-node")

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
