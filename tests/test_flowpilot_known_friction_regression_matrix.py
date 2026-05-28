from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

from flowguard import DEFECT_FAMILY_DECISION_FULL, RISK_CONFIDENCE_FULL


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "simulations" / "flowpilot_known_friction_regression_matrix.py"


def load_matrix_module():
    spec = importlib.util.spec_from_file_location("flowpilot_known_friction_regression_matrix", MATRIX_PATH)
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


class FlowPilotKnownFrictionRegressionMatrixTests(unittest.TestCase):
    def test_known_friction_rows_cover_required_historical_failures(self) -> None:
        report = matrix.build_report()

        self.assertTrue(report["ok"], report["findings"])
        self.assertEqual({row["friction_id"] for row in report["rows"]}, matrix.REQUIRED_FRICTION_IDS)
        self.assertEqual({row["source_class"] for row in report["rows"]}, matrix.REQUIRED_SOURCE_CLASSES)
        self.assertEqual(report["row_count"], report["required_friction_count"])
        self.assertEqual(report["rows_by_priority"]["P0"], 11)
        self.assertIn("historically recurring FlowPilot", report["coverage_boundary"])
        self.assertIn("defect-family gate", report["coverage_boundary"])
        self.assertIn("do not prove arbitrary live AI semantic quality", report["coverage_boundary"])
        self.assertTrue(report["defect_family_gate_ok"], report["defect_family_gate_report"])

    def test_known_friction_rows_cover_current_audit_surfaces(self) -> None:
        self.test_known_friction_rows_cover_required_historical_failures()

    def test_rows_bind_child_evidence_to_real_runtime_surfaces(self) -> None:
        for row in matrix.build_rows():
            with self.subTest(friction_id=row["friction_id"]):
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_role"], matrix.PRIMARY_ROLE)
                self.assertTrue(row["defect_family_gate_required"])
                self.assertTrue(row["defect_family_promoted"])
                self.assertGreaterEqual(row["defect_family_recurrence_count"], 2)
                self.assertTrue(row["defect_family_id"].startswith("defect_family:"))
                self.assertTrue(row["defect_family_authority_boundary"])
                self.assertIn("historical_live_run_replay_matrix", row["child_evidence_ids"])
                self.assertIn("scoped_confidence_disclosure", row["global_gates"])
                self.assertTrue(row["model_obligation"])
                self.assertTrue(row["model_check"].startswith("python simulations/"))
                self.assertTrue(row["runtime_test"].startswith("tests."))
                self.assertGreaterEqual(len(row["forbidden_shortcuts"]), 2)
                self.assertFalse(row["live_ai_semantic_quality_proven"])
                self.assertIn("does not", row["full_confidence_boundary"].lower())

    def test_global_gate_set_requires_install_runtime_and_background_boundaries(self) -> None:
        report = matrix.build_report()

        self.assertEqual(set(report["required_global_gates"]), matrix.REQUIRED_GLOBAL_GATES)
        self.assertEqual(report["missing_global_gates"], [])
        for gate in (
            "repo_source_to_installed_skill_sync",
            "copied_runtime_kit_freshness",
            "background_final_artifact_contract",
            "current_transcript_regression",
        ):
            with self.subTest(gate=gate):
                self.assertIn(gate, report["observed_global_gates"])

    def test_p0_rows_require_current_transcript_regression(self) -> None:
        p0_rows = [row for row in matrix.build_rows() if row["priority"] == "P0"]

        self.assertEqual(len(p0_rows), 11)
        for row in p0_rows:
            with self.subTest(friction_id=row["friction_id"]):
                self.assertIn("current_transcript_regression", row["global_gates"])

    def test_current_audit_rows_are_promoted_to_parent_gate(self) -> None:
        rows = {row["friction_id"]: row for row in matrix.build_rows()}
        current_audit_ids = {
            "known_friction.local_fixed_router_event_receipt_only",
            "known_friction.resume_rehydration_postcondition_replay_miss",
            "known_friction.control_blocker_same_family_storm",
            "known_friction.protocol_dead_end_reopened_by_resume",
            "known_friction.break_glass_patch_limbo",
            "known_friction.heartbeat_diagnostic_only_resume",
        }

        self.assertLessEqual(current_audit_ids, set(rows))
        for friction_id in current_audit_ids:
            row = rows[friction_id]
            with self.subTest(friction_id=friction_id):
                self.assertIn("run-20260527-212331", row["historical_bad_case"])
                self.assertIn("current_transcript_regression", row["global_gates"])
                self.assertIn("historical_live_run_replay_matrix", row["child_evidence_ids"])
                self.assertTrue(row["defect_family_promoted"])

    def test_known_bad_cases_are_rejected(self) -> None:
        for case in matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = matrix.validate_rows(case["rows"])
                codes = {finding["code"] for finding in findings}
                for expected_code in case["expected_codes"]:
                    self.assertIn(expected_code, codes)

    def test_known_friction_known_bad_cases_are_rejected(self) -> None:
        self.test_known_bad_cases_are_rejected()

    def test_recurring_defect_family_gate_consumes_known_friction_rows(self) -> None:
        report = matrix.build_report()
        family_report = report["defect_family_gate_report"]

        self.assertTrue(family_report["ok"], family_report)
        self.assertEqual(family_report["gate_plan"]["gate_count"], len(matrix.REQUIRED_FRICTION_IDS))
        self.assertEqual(family_report["risk_ledger_plan"]["row_count"], len(matrix.REQUIRED_FRICTION_IDS))
        self.assertEqual(
            set(family_report["defect_family_ids"]),
            {row["defect_family_id"] for row in matrix.build_rows()},
        )
        self.assertEqual(family_report["gate_report"]["decision"], DEFECT_FAMILY_DECISION_FULL)
        self.assertEqual(family_report["risk_ledger_report"]["confidence"], RISK_CONFIDENCE_FULL)
        self.assertEqual(family_report["gate_report"]["findings"], [])
        self.assertEqual(family_report["risk_ledger_report"]["findings"], [])

    def test_defect_family_gate_requires_artifact_backed_evidence(self) -> None:
        row = matrix.build_rows()[0]
        report = matrix.build_defect_family_report((row,), include_proof_artifacts=False)
        gate_codes = {
            finding["code"]
            for finding in report["gate_report"]["findings"]
        }
        ledger_codes = {
            finding["code"]
            for finding in report["risk_ledger_report"]["findings"]
        }

        self.assertFalse(report["ok"])
        self.assertIn("missing_defect_family_proof_artifact", gate_codes)
        self.assertIn("legacy_path_missing_proof_artifact", gate_codes)
        self.assertIn("missing_proof_evidence_artifact", ledger_codes)

    def test_proof_artifacts_bind_to_current_result_files(self) -> None:
        gate_plan = matrix.build_defect_family_gate_plan()

        self.assertTrue(gate_plan.require_proof_artifacts)
        self.assertTrue(gate_plan.require_legacy_path_dispositions)
        for evidence in gate_plan.proof_evidence:
            with self.subTest(evidence_id=evidence.evidence_id):
                artifact = evidence.proof_artifact
                self.assertIsNotNone(artifact)
                self.assertEqual(artifact.result_status, "passed")
                self.assertEqual(artifact.exit_code, 0)
                self.assertTrue(artifact.result_path)
                self.assertTrue(artifact.artifact_fingerprints)
                for result_path, fingerprint in artifact.artifact_fingerprints.items():
                    self.assertTrue((matrix.ROOT / result_path).exists(), result_path)
                    self.assertTrue(fingerprint.startswith("sha256:"))
                self.assertIn(evidence.evidence_id, artifact.covered_obligation_ids)

    def test_defect_family_known_bad_cases_are_rejected(self) -> None:
        checks = {case["name"]: case for case in matrix.defect_family_known_bad_cases()}

        for name, case in checks.items():
            with self.subTest(name=name):
                row_codes = {finding["code"] for finding in case["row_findings"]}
                if name == "internal_only_defect_family_proof":
                    finding_codes = {finding["code"] for finding in case["report"]["findings"]}
                else:
                    gate_codes = {
                        finding["code"]
                        for finding in case["report"]["gate_report"]["findings"]
                    }
                    ledger_codes = {
                        finding["code"]
                        for finding in case["report"]["risk_ledger_report"]["findings"]
                    }
                    finding_codes = row_codes | gate_codes | ledger_codes
                self.assertTrue(
                    row_codes or not case["report"].get("ok", False),
                    f"{name} unexpectedly passed",
                )
                self.assertLessEqual(set(case["expected_codes"]), finding_codes)


if __name__ == "__main__":
    unittest.main()
