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
        run_c = fp / "runs" / "run-c"
        _write_json(fp / "current.json", {"active_run_id": "run-a", "active_route_id": "route-001"})
        _write_json(
            fp / "index.json",
            {
                "runs": [
                    {"run_id": "run-a", "title": "Run A", "status": "active", "active_route_id": "route-001"},
                    {"run_id": "run-b", "title": "Run B", "status": "controlled_stop", "active_route_id": "route-002"},
                    {"run_id": "run-c", "title": "A Very Long Current Cockpit Run Title", "status": "running", "active_route_id": "route-003"},
                ]
            },
        )
        for run_root, run_id, route_id, active_node in [
            (run_a, "run-a", "route-001", "node-002-work"),
            (run_b, "run-b", "route-002", "node-001-start"),
            (run_c, "run-c", "route-003", "node-001-start"),
        ]:
            status = "controlled_stop" if run_id == "run-b" else "active"
            _write_json(run_root / "run.json", {"run_id": run_id, "title": run_id, "status": status})
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
        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a", "run-c"])
        self.assertTrue(all(run.status in {"active", "running", "in_progress"} for run in snapshot.runs))
        self.assertTrue(snapshot.runs[1].tab_title)
        self.assertLessEqual(len(snapshot.runs[1].tab_title or ""), 24)
        self.assertEqual([node.status for node in snapshot.nodes], ["complete", "running"])
        self.assertEqual(snapshot.source_health, "ok")

    def test_selected_active_run_switches_tabs_inside_same_snapshot_reader(self) -> None:
        root = self.make_project()
        snapshot = FlowPilotStateReader(root).read_project(selected_run_id="run-c")

        self.assertEqual(snapshot.selected_run_id, "run-c")
        self.assertEqual(snapshot.selected_route_id, "route-003")
        self.assertEqual(snapshot.active_node_id, "node-001-start")

    def test_selected_inactive_run_is_not_shown_and_falls_back_to_active(self) -> None:
        root = self.make_project()

        snapshot = FlowPilotStateReader(root).read_project(selected_run_id="run-b")

        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a", "run-c"])
        self.assertEqual(snapshot.selected_run_id, "run-a")
        self.assertEqual(snapshot.source_health, "ok")
        self.assertNotIn("run-b", [run.run_id for run in snapshot.runs])

    def test_hidden_selected_active_run_falls_back_without_status_change(self) -> None:
        root = self.make_project()

        snapshot = FlowPilotStateReader(root).read_project(selected_run_id="run-c", hidden_run_ids={"run-c"})

        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a"])
        self.assertEqual(snapshot.selected_run_id, "run-a")
        self.assertEqual(snapshot.source_health, "ok")
        run_c_payload = json.loads(
            (root / ".flowpilot" / "runs" / "run-c" / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual(run_c_payload["status"], "active")

    def test_missing_current_run_degrades_instead_of_falling_back_to_legacy(self) -> None:
        root = self.make_project()
        _write_json(root / ".flowpilot" / "current.json", {"active_run_id": "missing-run", "active_route_id": "route-999"})

        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.source_health, "degraded")
        self.assertIn("Active/current run pointer is invalid", " ".join(snapshot.source_findings))
        self.assertNotEqual(snapshot.selected_route_id, "legacy-route")

    def test_current_pointer_to_inactive_run_degrades_but_filtered_history_does_not(self) -> None:
        root = self.make_project()
        _write_json(root / ".flowpilot" / "current.json", {"active_run_id": "run-b", "active_route_id": "route-002"})

        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.source_health, "degraded")
        self.assertIn("Active/current run pointer is not a live or completed current run", " ".join(snapshot.source_findings))
        self.assertEqual(snapshot.selected_run_id, "run-a")
        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a", "run-c"])

    def test_completed_current_run_remains_visible_for_handoff(self) -> None:
        root = self.make_project()
        fp = root / ".flowpilot"
        index = json.loads((fp / "index.json").read_text(encoding="utf-8"))
        index["runs"][0]["status"] = "complete"
        _write_json(fp / "index.json", index)
        _write_json(fp / "current.json", {"active_run_id": "run-a", "active_route_id": "route-001", "status": "complete"})
        _write_json(fp / "runs" / "run-a" / "run.json", {"run_id": "run-a", "title": "Run A", "status": "complete"})
        _write_json(
            fp / "runs" / "run-a" / "state.json",
            {"route_id": "route-001", "active_node_id": "node-002-work", "status": "complete"},
        )
        _write_json(
            fp / "runs" / "run-a" / "execution_frontier.json",
            {"route_id": "route-001", "active_node": "node-002-work", "status": "complete"},
        )
        route_path = fp / "runs" / "run-a" / "routes" / "route-001" / "flow.json"
        route = json.loads(route_path.read_text(encoding="utf-8"))
        route["status"] = "complete"
        route["nodes"][1]["status"] = "complete"
        _write_json(route_path, route)

        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.source_health, "ok")
        self.assertEqual(snapshot.selected_run_id, "run-a")
        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a", "run-c"])
        self.assertEqual(snapshot.route_status, "complete")
        self.assertEqual([node.status for node in snapshot.nodes], ["complete", "complete"])
        self.assertIsNone(snapshot.active_node_id)

    def test_completed_historical_run_stays_hidden_by_default(self) -> None:
        root = self.make_project()
        fp = root / ".flowpilot"
        index = json.loads((fp / "index.json").read_text(encoding="utf-8"))
        index["runs"][1]["status"] = "complete"
        _write_json(fp / "index.json", index)
        _write_json(fp / "runs" / "run-b" / "run.json", {"run_id": "run-b", "title": "Run B", "status": "complete"})

        snapshot = FlowPilotStateReader(root).read_project()

        self.assertEqual(snapshot.source_health, "ok")
        self.assertEqual([run.run_id for run in snapshot.runs], ["run-a", "run-c"])
        self.assertNotIn("run-b", [run.run_id for run in snapshot.runs])

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
