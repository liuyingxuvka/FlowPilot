from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from flowpilot_cockpit.state_reader import FlowPilotStateReader


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotCockpitStateReaderTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-cockpit-"))
        fp = root / ".flowpilot"
        run_a = fp / "runs" / "run-a"
        run_b = fp / "runs" / "run-b"
        _write_json(fp / "current.json", {"active_run_id": "run-a", "active_route_id": "route-001"})
        _write_json(
            fp / "index.json",
            {
                "runs": [
                    {"run_id": "run-a", "title": "Run A", "status": "active", "active_route_id": "route-001"},
                    {"run_id": "run-b", "title": "Run B", "status": "controlled_stop", "active_route_id": "route-002"},
                ]
            },
        )
        for run_root, run_id, route_id, active_node in [
            (run_a, "run-a", "route-001", "node-002-work"),
            (run_b, "run-b", "route-002", "node-001-start"),
        ]:
            _write_json(run_root / "run.json", {"run_id": run_id, "title": run_id, "status": "active"})
            _write_json(run_root / "state.json", {"route_id": route_id, "active_node_id": active_node, "status": "active"})
            _write_json(run_root / "execution_frontier.json", {"route_id": route_id, "active_node": active_node})
            _write_json(
                run_root / "routes" / route_id / "flow.json",
                {
                    "route_id": route_id,
                    "version": 1,
                    "status": "active",
                    "nodes": [
                        {"id": "node-001-start", "title": "Start", "status": "complete", "required_gates": ["startup"]},
                        {"id": "node-002-work", "title": "Work", "status": "running", "required_gates": ["implementation"]},
                    ],
                },
            )
            _write_json(
                run_root / "evidence" / "evidence_ledger.json",
                {"entries": [{"id": "startup", "path": "startup_review/latest.json", "classification": "current"}]},
            )
        _write_json(fp / "state.json", {"active_route": "legacy-route"})
        return root

    def test_active_run_pointer_drives_snapshot_not_legacy_state(self) -> None:
        root = self.make_project()
        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.selected_run_id, "run-a")
        self.assertEqual(snapshot.selected_route_id, "route-001")
        self.assertEqual(snapshot.active_node_id, "node-002-work")
        self.assertEqual(len(snapshot.runs), 2)
        self.assertEqual([node.status for node in snapshot.nodes], ["complete", "running"])
        self.assertEqual(snapshot.source_health, "ok")

    def test_selected_run_switches_tabs_inside_same_snapshot_reader(self) -> None:
        root = self.make_project()
        snapshot = FlowPilotStateReader(root).read_project(selected_run_id="run-b")

        self.assertEqual(snapshot.selected_run_id, "run-b")
        self.assertEqual(snapshot.selected_route_id, "route-002")
        self.assertEqual(snapshot.active_node_id, "node-001-start")

    def test_missing_current_run_degrades_instead_of_falling_back_to_legacy(self) -> None:
        root = self.make_project()
        _write_json(root / ".flowpilot" / "current.json", {"active_run_id": "missing-run", "active_route_id": "route-999"})

        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.source_health, "degraded")
        self.assertIn("Selected run is not in the run catalog", " ".join(snapshot.source_findings))
        self.assertNotEqual(snapshot.selected_route_id, "legacy-route")

    def test_reader_reflects_changed_route_file_without_manual_state_cache(self) -> None:
        root = self.make_project()
        reader = FlowPilotStateReader(root)
        first = reader.read_project()
        route_path = root / ".flowpilot" / "runs" / "run-a" / "routes" / "route-001" / "flow.json"
        payload = json.loads(route_path.read_text(encoding="utf-8"))
        payload["nodes"][1]["status"] = "complete"
        _write_json(route_path, payload)

        second = reader.read_project()

        self.assertEqual(first.nodes[1].status, "running")
        self.assertEqual(second.nodes[1].status, "complete")


if __name__ == "__main__":
    unittest.main()
