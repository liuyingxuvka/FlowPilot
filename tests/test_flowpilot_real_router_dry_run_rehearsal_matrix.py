from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_real_router_dry_run_rehearsal_matrix as matrix  # noqa: E402


class FlowPilotRealRouterDryRunRehearsalMatrixTests(unittest.TestCase):
    def test_matrix_has_required_real_router_rehearsal_rows(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report["findings"])
        rows = {row["rehearsal_id"]: row for row in report["rows"]}
        self.assertEqual(set(rows), matrix.REQUIRED_REHEARSAL_IDS)
        self.assertIn("prepared fake AI packages", report["coverage_boundary"])
        self.assertIn("do not prove live AI semantic quality", report["coverage_boundary"])
        for rehearsal_id, row in rows.items():
            with self.subTest(rehearsal_id=rehearsal_id):
                self.assertTrue(row["phase_sequence"])
                self.assertTrue(row["fake_ai_artifacts"])
                self.assertTrue(row["router_entrypoints"])
                self.assertTrue(row["required_ack_or_receipt_gates"])
                self.assertTrue(row["allowed_event_boundary"])
                self.assertIn("direct_state_mutation", row["forbidden_shortcuts"])
                self.assertTrue(row["expected_standard_state"])
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], "primary_real_router_rehearsal")
                self.assertFalse(row["live_ai_semantic_quality_proven"])

    def test_required_entrypoints_include_cli_and_runtime_boundaries(self) -> None:
        report = matrix.build_report()
        entrypoints = report["rows_by_entrypoint"]

        for expected in (
            "router_cli.start",
            "router_cli.next",
            "router_cli.apply",
            "router_cli.record_event",
            "router_cli.run_until_wait",
            "card_runtime.open_card",
            "card_runtime.submit_card_ack",
            "packet_runtime.active_holder_submit_result",
            "background_artifact_classifier",
            "router_lifecycle_terminal",
        ):
            with self.subTest(entrypoint=expected):
                self.assertIn(expected, entrypoints)

    def test_known_bad_rows_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                codes = {
                    finding["code"]
                    for finding in matrix.validate_rows(case["rows"])
                }
                for expected in case["expected_codes"]:
                    self.assertIn(expected, codes)

    def test_producer_proof_repair_row_forbids_stale_evidence_shortcut(self) -> None:
        rows = {row["rehearsal_id"]: row for row in matrix.build_rows()}
        row = rows["real_router.repair.producer_proof_recovery"]

        self.assertIn("pm_no_producer_repair_decision", row["fake_ai_artifacts"])
        self.assertIn("repair_packet_generation", row["fake_ai_artifacts"])
        self.assertIn("producer_evidence_on_followup_wait", row["required_ack_or_receipt_gates"])
        self.assertIn("stale_worker_result_flag_as_fresh_producer", row["forbidden_shortcuts"])
        self.assertIn("test_real_router_repair_rehearsal_rejects_no_producer", row["evidence_test"])

    def test_matrix_cli_writes_json_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-real-router-matrix-") as tmp_name:
            output_path = Path(tmp_name) / "report.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "simulations/flowpilot_real_router_dry_run_rehearsal_matrix.py",
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
            self.assertEqual(report["row_count"], len(matrix.REQUIRED_REHEARSAL_IDS))


if __name__ == "__main__":
    unittest.main()
