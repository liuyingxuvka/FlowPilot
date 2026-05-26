from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "simulations" / "flowpilot_historical_live_run_replay_matrix.py"


def load_matrix_module():
    spec = importlib.util.spec_from_file_location("flowpilot_historical_live_run_replay_matrix", MATRIX_PATH)
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


class FlowPilotHistoricalLiveRunReplayMatrixTests(unittest.TestCase):
    def test_historical_live_run_rows_cover_required_surfaces(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report)
        self.assertEqual({row["replay_id"] for row in report["rows"]}, matrix.REQUIRED_REPLAY_IDS)
        self.assertEqual(set(report["rows_by_surface"]), matrix.REQUIRED_SURFACES)
        self.assertEqual(report["row_count"], report["required_replay_count"])
        self.assertEqual(report["rows_by_priority"]["P0"], 4)
        self.assertIn("historical live-run replay", report["coverage_boundary"])
        self.assertIn("live AI semantic", report["coverage_boundary"])

    def test_rows_bind_to_current_primary_evidence_and_safe_boundaries(self) -> None:
        for row in matrix.build_rows():
            with self.subTest(replay_id=row["replay_id"]):
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], "primary_historical_replay")
                self.assertFalse(row["destructive_live_state_mutation"])
                self.assertFalse(row["live_ai_semantic_quality_proven"])
                self.assertTrue(row["protected_state_invariant"])
                self.assertTrue(row["expected_standard_state"])
                self.assertTrue(row["required_evidence"])
                self.assertTrue(row["confidence_boundary"])
                self.assertGreaterEqual(len(row["forbidden_shortcuts"]), 2)

    def test_required_package_classes_are_finite_and_complete(self) -> None:
        observed: set[str] = set()
        for row in matrix.build_rows():
            observed.update(row["finite_package_classes"])

        self.assertEqual(observed, set(matrix.HISTORICAL_PACKAGE_CLASSES))
        self.assertIn("relay_done_without_runtime_mutation", observed)
        self.assertIn("windows_lock_partial_json", observed)
        self.assertNotIn("random_unbounded_fuzz", observed)

    def test_p0_rows_cover_historical_adapter_lifecycle_and_relay(self) -> None:
        p0_rows = {row["surface"]: row for row in matrix.build_rows() if row["priority"] == "P0"}

        self.assertEqual(
            set(p0_rows),
            {
                "historical_snapshot",
                "host_role_lifecycle",
                "production_replay_adapter",
                "relay_receipt_mechanics",
            },
        )
        self.assertTrue(p0_rows["historical_snapshot"]["historical_snapshot_required"])
        self.assertTrue(p0_rows["production_replay_adapter"]["production_replay_adapter_required"])
        self.assertFalse(p0_rows["production_replay_adapter"]["production_replay_adapter_present"])
        self.assertIn("adapter gap", p0_rows["production_replay_adapter"]["confidence_boundary"])
        self.assertIn("rehydrate_role_agents", p0_rows["host_role_lifecycle"]["entrypoints"])
        self.assertIn("packet_runtime", p0_rows["relay_receipt_mechanics"]["entrypoints"])

    def test_historical_live_run_known_bad_cases_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = matrix.validate_rows(case["rows"])
                codes = {finding["code"] for finding in findings}
                for expected_code in case["expected_codes"]:
                    self.assertIn(expected_code, codes)


if __name__ == "__main__":
    unittest.main()
