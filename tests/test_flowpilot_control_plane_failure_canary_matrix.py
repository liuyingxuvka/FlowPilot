from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "simulations" / "flowpilot_control_plane_failure_canary_matrix.py"


def load_matrix_module():
    spec = importlib.util.spec_from_file_location("flowpilot_control_plane_failure_canary_matrix", MATRIX_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(MATRIX_PATH.parent))
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
    return module


matrix = load_matrix_module()


class FlowPilotControlPlaneFailureCanaryMatrixTests(unittest.TestCase):
    def test_control_plane_canary_rows_cover_required_surfaces(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report)
        rows = report["rows"]
        ids = {row["canary_id"] for row in rows}
        self.assertEqual(ids, matrix.REQUIRED_CANARY_IDS)
        self.assertEqual(report["row_count"], report["required_canary_count"])
        for surface in (
            "runtime_json_lock",
            "runtime_persistence",
            "daemon_liveness",
            "manual_resume",
            "run_authority",
            "background_evidence",
            "terminal_fence",
        ):
            self.assertIn(surface, report["rows_by_surface"])
        self.assertIn("They do not prove every OS", report["coverage_boundary"])

    def test_control_plane_canary_rows_bind_to_current_primary_evidence(self) -> None:
        for row in matrix.build_rows():
            with self.subTest(canary_id=row["canary_id"]):
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], "primary_canary")
                self.assertFalse(row["destructive_live_state_mutation"])
                self.assertTrue(row["protected_state_invariant"])
                self.assertTrue(row["recovery_route"])
                self.assertTrue(row["standard_final_state"])
                self.assertTrue(row["unmodeled_failure_boundary"])

    def test_control_plane_canary_known_bad_cases_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = matrix.validate_rows(case["rows"])
                codes = {finding["code"] for finding in findings}
                for expected_code in case["expected_codes"]:
                    self.assertIn(expected_code, codes)


if __name__ == "__main__":
    unittest.main()
