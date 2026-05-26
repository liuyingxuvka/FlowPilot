from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "simulations" / "flowpilot_shadow_launcher_chaos_matrix.py"


def load_matrix_module():
    spec = importlib.util.spec_from_file_location("flowpilot_shadow_launcher_chaos_matrix", MATRIX_PATH)
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


class FlowPilotShadowLauncherChaosMatrixTests(unittest.TestCase):
    def test_shadow_launcher_chaos_rows_cover_required_surfaces(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report)
        self.assertEqual({row["rehearsal_id"] for row in report["rows"]}, matrix.REQUIRED_REHEARSAL_IDS)
        self.assertEqual(set(report["rows_by_surface"]), matrix.REQUIRED_SURFACES)
        self.assertEqual(report["row_count"], report["required_rehearsal_count"])
        self.assertIn("installed launcher", report["coverage_boundary"])
        self.assertIn("live AI semantic quality", report["coverage_boundary"])

    def test_shadow_launcher_chaos_rows_bind_to_current_primary_evidence(self) -> None:
        for row in matrix.build_rows():
            with self.subTest(rehearsal_id=row["rehearsal_id"]):
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], "primary_shadow_rehearsal")
                self.assertFalse(row["destructive_live_state_mutation"])
                self.assertFalse(row["live_ai_semantic_quality_proven"])
                self.assertTrue(row["protected_state_invariant"])
                self.assertTrue(row["expected_standard_state"])
                self.assertTrue(row["required_evidence"])
                self.assertTrue(row["confidence_boundary"])

    def test_malformed_package_row_uses_finite_required_bad_classes(self) -> None:
        row = next(item for item in matrix.build_rows() if item["surface"] == "malformed_packages")

        self.assertEqual(set(row["finite_package_classes"]), set(matrix.MALFORMED_PACKAGE_CLASSES))
        self.assertGreaterEqual(len(row["finite_package_classes"]), 5)
        self.assertNotIn("random_unbounded_fuzz", row["finite_package_classes"])

    def test_shadow_launcher_chaos_known_bad_cases_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = matrix.validate_rows(case["rows"])
                codes = {finding["code"] for finding in findings}
                for expected_code in case["expected_codes"]:
                    self.assertIn(expected_code, codes)


if __name__ == "__main__":
    unittest.main()
