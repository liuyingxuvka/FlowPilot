from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import flowpilot_defects  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class FlowPilotDefectLedgerTests(unittest.TestCase):
    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="flowpilot-defects-"))
        run_root = root / ".flowpilot" / "runs" / "run-test"
        _write_json(
            root / ".flowpilot" / "current.json",
            {
                "current_run_id": "run-test",
                "current_run_root": ".flowpilot/runs/run-test",
            },
        )
        _write_json(
            run_root / "state.json",
            {
                "run_id": "run-test",
                "active_route": "route-001",
                "route_version": 2,
                "active_node": "node-003",
            },
        )
        _write_json(
            run_root / "execution_frontier.json",
            {
                "active_route": "route-001",
                "route_version": 2,
                "active_node": "node-003",
                "next_gate": "human review",
            },
        )
        return root

    def test_blocker_requires_recheck_before_terminal_check_passes(self) -> None:
        root = self.make_project()
        self.assertEqual(flowpilot_defects.main(["--root", str(root), "init"]), 0)
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(root),
                    "add-defect",
                    "--defect-id",
                    "defect-ui-source-degraded",
                    "--title",
                    "Source error rendered as success",
                    "--description",
                    "Unreadable route source still looked successful.",
                    "--defect-type",
                    "target_product_defect",
                    "--severity",
                    "blocker",
                    "--role",
                    "human_like_reviewer",
                    "--affected-gate",
                    "rendered-ui-review",
                    "--owner-role",
                    "controller",
                    "--recheck-role-class",
                    "human_like_reviewer",
                    "--close-condition",
                    "same-class reviewer sees degraded state",
                ]
            ),
            0,
        )
        self.assertEqual(
            flowpilot_defects.main(["--root", str(root), "check", "--terminal"]),
            1,
        )
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(root),
                    "update-defect",
                    "--defect-id",
                    "defect-ui-source-degraded",
                    "--status",
                    "fixed_pending_recheck",
                    "--role",
                    "controller",
                    "--event-type",
                    "repair_recorded",
                    "--summary",
                    "Added degraded state.",
                    "--evidence",
                    "screenshots/degraded.png",
                ]
            ),
            0,
        )
        self.assertEqual(
            flowpilot_defects.main(["--root", str(root), "check", "--terminal"]),
            1,
        )
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(root),
                    "update-defect",
                    "--defect-id",
                    "defect-ui-source-degraded",
                    "--status",
                    "closed",
                    "--role",
                    "project_manager",
                    "--event-type",
                    "closed",
                    "--summary",
                    "Reviewer recheck passed.",
                    "--evidence",
                    "human_reviews/recheck.json",
                ]
            ),
            0,
        )
        self.assertEqual(
            flowpilot_defects.main(["--root", str(root), "check", "--terminal"]),
            0,
        )

    def test_pause_snapshot_carries_defect_and_evidence_boundary(self) -> None:
        root = self.make_project()
        flowpilot_defects.main(["--root", str(root), "init"])
        flowpilot_defects.main(
            [
                "--root",
                str(root),
                "add-evidence",
                "--evidence-id",
                "evidence-fixture-realtime",
                "--kind",
                "smoke_report",
                "--path",
                "qa-fixtures/multi-run/report.json",
                "--status",
                "valid",
                "--source-kind",
                "fixture",
                "--role",
                "worker_b",
                "--reason",
                "Fixture proves capability but not live project coverage.",
            ]
        )
        self.assertEqual(
            flowpilot_defects.main(
                [
                    "--root",
                    str(root),
                    "pause-snapshot",
                    "--reason",
                    "user_requested",
                    "--next-allowed-action",
                    "start_new_run",
                    "--automation-checked",
                    "--safe-to-delete",
                    "desktop_cockpit",
                    "--preserve",
                    "defect ledger lessons",
                    "--must-not-reuse",
                    "old screenshots",
                    "--summary",
                    "Paused before fresh restart.",
                ]
            ),
            0,
        )
        snapshot = json.loads(
            (root / ".flowpilot" / "runs" / "run-test" / "pause_snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(snapshot["pause_reason"], "user_requested")
        self.assertEqual(snapshot["next_allowed_action"], "start_new_run")
        self.assertEqual(
            snapshot["evidence_summary"]["fixture_only_evidence_to_disclose"],
            ["evidence-fixture-realtime"],
        )


if __name__ == "__main__":
    unittest.main()
