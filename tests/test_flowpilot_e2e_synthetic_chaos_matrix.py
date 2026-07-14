from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_e2e_synthetic_chaos_matrix as matrix  # noqa: E402


class FlowPilotEndToEndSyntheticChaosMatrixTests(unittest.TestCase):
    def test_matrix_has_required_full_flow_rows(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report["findings"])
        rows = {row["flow_id"]: row for row in report["rows"]}
        self.assertEqual(set(rows), matrix.REQUIRED_FLOW_IDS)
        self.assertIn("fake-package protocol", report["coverage_boundary"])
        self.assertIn("do not prove live AI semantic quality", report["coverage_boundary"])
        for flow_id, row in rows.items():
            with self.subTest(flow_id=flow_id):
                self.assertTrue(row["phase_sequence"])
                self.assertTrue(row["expected_outcome"])
                self.assertTrue(row["protected_state_invariant"])
                self.assertTrue(row["recovery_route"])
                self.assertTrue(row["final_state"])
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], "primary_full_flow")
                self.assertFalse(row["live_ai_semantic_quality_proven"])
                self.assertTrue(
                    row["evidence_test"].startswith("FlowPilotEndToEndSyntheticChaosReplayTests.")
                )

    def test_known_bad_rows_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                codes = {
                    finding["code"]
                    for finding in matrix.validate_rows(case["rows"])
                }
                for expected in case["expected_codes"]:
                    self.assertIn(expected, codes)

    def test_retired_material_repair_story_is_not_current_matrix_evidence(self) -> None:
        flow_ids = {row["flow_id"] for row in matrix.build_rows()}
        self.assertNotIn("e2e.pm_repair.no_producer_then_packet_reissue", flow_ids)
        self.assertNotIn("material_scan_dispatch", json.dumps(matrix.build_rows(), sort_keys=True))

    def test_matrix_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-e2e-chaos-matrix-") as tmp_name:
            output_path = Path(tmp_name) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "simulations/flowpilot_e2e_synthetic_chaos_matrix.py",
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
            self.assertEqual(report["row_count"], len(matrix.REQUIRED_FLOW_IDS))


if __name__ == "__main__":
    unittest.main()
