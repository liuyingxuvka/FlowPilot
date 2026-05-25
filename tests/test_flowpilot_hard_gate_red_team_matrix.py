from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_hard_gate_red_team_matrix as matrix  # noqa: E402


class FlowPilotHardGateRedTeamMatrixTests(unittest.TestCase):
    def test_matrix_has_all_required_hard_gate_rows(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report["findings"])
        rows = {row["gate_id"]: row for row in report["rows"]}
        self.assertEqual(set(rows), matrix.REQUIRED_GATE_IDS)
        for gate_id, row in rows.items():
            with self.subTest(gate_id=gate_id):
                self.assertFalse(row["live_completion_allowed"])
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertTrue(row["protected_state_invariant"])
                self.assertTrue(row["recovery_route"])
                self.assertTrue(row["evidence_test"].startswith("FlowPilotHardGateRedTeamReplayTests."))

    def test_known_bad_rows_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                codes = {
                    finding["code"]
                    for finding in matrix.validate_red_team_rows(case["rows"])
                }
                for expected in case["expected_codes"]:
                    self.assertIn(expected, codes)

    def test_matrix_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-hard-gate-matrix-") as tmp_name:
            output_path = Path(tmp_name) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "simulations/flowpilot_hard_gate_red_team_matrix.py",
                    "--json-out",
                    str(output_path),
                ],
                cwd=ROOT,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertEqual(report["row_count"], len(matrix.REQUIRED_GATE_IDS))


if __name__ == "__main__":
    unittest.main()
