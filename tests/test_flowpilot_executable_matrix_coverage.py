from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


model = load_module(
    "flowpilot_executable_matrix_coverage_model",
    ROOT / "simulations" / "flowpilot_executable_matrix_coverage_model.py",
)
runner = load_module(
    "run_flowpilot_executable_matrix_coverage_checks",
    ROOT / "simulations" / "run_flowpilot_executable_matrix_coverage_checks.py",
)


class FlowPilotExecutableMatrixCoverageTests(unittest.TestCase):
    def test_bridge_rows_cover_required_miss_families_without_live_claims(self) -> None:
        report = model.build_report()

        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual(report["missing_miss_families"], [])
        self.assertEqual(
            set(report["required_miss_families"]),
            {row["miss_family_id"] for row in report["rows"]},
        )
        self.assertGreaterEqual(report["row_count"], len(model.REQUIRED_MISS_FAMILIES))
        self.assertFalse(report["live_ai_semantic_quality_proven"])
        self.assertFalse(report["product_completion_proven"])
        for row in report["rows"]:
            with self.subTest(bridge_case_id=row["bridge_case_id"]):
                self.assertLessEqual(set(model.REQUIRED_BRIDGE_FIELDS), set(row))
                self.assertTrue(row["model_cell_id"] or row["coverage_shard_id"])
                self.assertNotEqual(row["evidence_level"], "model_only")
                self.assertFalse(row["live_ai_semantic_quality_proven"])
                self.assertFalse(row["product_completion_proven"])
                self.assertTrue(row["freshness_receipt"]["current"], row["freshness_receipt"])

    def test_normal_recovery_forbids_glassbreak_but_fifth_repeat_requires_it(self) -> None:
        rows = {row["bridge_case_id"]: row for row in model.BRIDGE_ROWS}
        ordinary = rows["same_class_repeats_one_to_four_do_not_glassbreak"]
        threshold = rows["same_class_repeat_five_triggers_glassbreak"]

        self.assertEqual(ordinary["attempt_count"], model.BREAK_GLASS_THRESHOLD - 1)
        self.assertTrue(ordinary["same_failure_class_no_progress"])
        self.assertFalse(ordinary["break_glass_triggered"])
        self.assertEqual(ordinary["break_glass_expectation"], "forbidden")
        self.assertEqual(model.bridge_row_failures(ordinary), [])

        self.assertEqual(threshold["attempt_count"], model.BREAK_GLASS_THRESHOLD)
        self.assertTrue(threshold["same_failure_class_no_progress"])
        self.assertTrue(threshold["break_glass_triggered"])
        self.assertEqual(threshold["break_glass_expectation"], "required_at_fifth_repeat")
        self.assertEqual(model.bridge_row_failures(threshold), [])

    def test_ai_contract_projection_rows_are_executable_bridge_cases(self) -> None:
        rows = {row["bridge_case_id"]: row for row in model.BRIDGE_ROWS}
        expected = {
            "ai_facing_semantic_recheck_contract_projection": (
                "ai_facing_semantic_recheck_contract_projection",
                "test_semantic_recheck_contract_projects_ai_facing_fields_and_options",
            ),
            "ai_facing_semantic_recheck_near_synonym_feedback": (
                "ai_facing_semantic_recheck_near_synonym_feedback",
                "test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape",
            ),
            "ai_facing_semantic_recheck_wrong_value_then_corrected_retry": (
                "ai_facing_semantic_recheck_corrected_retry",
                "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path",
            ),
            "ai_facing_contract_driven_fake_ai_cartesian_retry": (
                "ai_facing_contract_driven_fake_ai_cartesian_retry",
                "test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option",
            ),
        }

        for row_id, (miss_family, test_name) in expected.items():
            with self.subTest(row_id=row_id):
                self.assertIn(row_id, rows)
                self.assertEqual(rows[row_id]["miss_family_id"], miss_family)
                self.assertEqual(rows[row_id]["evidence_test_name"], test_name)
                self.assertEqual(rows[row_id]["evidence_path"], "tests/test_flowpilot_ai_contract_projection.py")
                self.assertEqual(
                    rows[row_id]["evidence_command"],
                    "python -m unittest -v tests.test_flowpilot_ai_contract_projection",
                )

    def test_known_bad_rows_catch_model_only_early_glassbreak_and_missing_threshold_glassbreak(self) -> None:
        for case in model.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = model.validate_bridge_rows(case["rows"])
                codes = {finding["code"] for finding in findings}
                self.assertLessEqual(set(case["expected_codes"]), codes)

    def test_freshness_receipt_detects_result_older_than_source(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-exec-matrix-") as tmp:
            root = Path(tmp)
            source = root / "source.py"
            result = root / "result.json"
            source.write_text("new source\n", encoding="utf-8")
            result.write_text("{}\n", encoding="utf-8")
            now = time.time()
            os.utime(result, (now - 10, now - 10))
            os.utime(source, (now, now))

            row = {
                **model.BRIDGE_ROWS[0],
                "source_paths": ("source.py",),
                "result_artifact_path": "result.json",
            }

            receipt = model.build_freshness_receipt(row, project_root=root)

            self.assertFalse(receipt["current"])
            self.assertTrue(receipt["stale_against_sources"])

    def test_runner_writes_result_and_keeps_flowguard_green(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-exec-matrix-result-") as tmp:
            output = Path(tmp) / "result.json"
            exit_code = runner.main(["--json-out", str(output)])

            self.assertEqual(exit_code, 0)
            payload = output.read_text(encoding="utf-8")
            self.assertIn(model.MODEL_ID, payload)
            report = runner.run_checks()
            self.assertTrue(report["ok"], report)
            self.assertTrue(report["flowguard"]["ok"], report["flowguard"])
            self.assertTrue(report["known_bad"]["ok"], report["known_bad"])


if __name__ == "__main__":
    unittest.main()
