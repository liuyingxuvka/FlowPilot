from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402
import run_flowguard_coverage_sweep as coverage_sweep  # noqa: E402


def _current_runner_keys() -> set[str]:
    return {
        coverage_sweep._runner_key(path)
        for path in sorted((ROOT / "simulations").glob("run_*_checks.py"))
    }


class FlowPilotFullModelCoverageInventoryTests(unittest.TestCase):
    def test_inventory_classifies_all_current_flowguard_runners(self) -> None:
        report = inventory.build_inventory()

        runner_count = len(_current_runner_keys())
        self.assertEqual(report["runner_count"], runner_count)
        self.assertGreaterEqual(report["runner_count"], 90)
        self.assertEqual(
            report["gap_class_counts"].get("runner_not_ok", 0),
            0,
            "read-only runner failures should be fixed or classified as live-state evidence",
        )
        self.assertEqual(
            report["gap_class_counts"].get("live_runtime_or_state_findings", 0),
            0,
            "current-run blockers must be repaired or explicitly disposed before coverage can claim green",
        )
        self.assertNotIn("source_or_code_findings", report["gap_class_counts"])
        self.assertNotIn("missing_or_scoped_replay_adapter", report["gap_class_counts"])
        self.assertNotIn("skipped_or_scoped_evidence", report["gap_class_counts"])
        self.assertNotIn(
            "abstract_without_detected_ordinary_test_reference",
            report["gap_class_counts"],
        )
        self.assertNotIn("unclassified_model_tier", report["gap_class_counts"])
        self.assertTrue(report["sweep_ok"])
        self.assertTrue(report["alignment_ok"])
        self.assertTrue(report["release_convergence_ok"])
        self.assertEqual(report["unresolved_non_deferred_gap_count"], 0)
        if not report["full_coverage_ok"]:
            self.assertGreater(report["deferred_structure_split_count"], 0)
        self.assertIn("replay evidence manifest", report["claim_boundary"])

        records = {record["runner"]: record for record in report["records"]}
        self.assertEqual(records["flowpilot_contract_exhaustion_mesh"]["coverage_tier"], "coverage_strong")
        self.assertEqual(records["flowpilot_cartesian_control_plane_exhaustion"]["coverage_tier"], "coverage_strong")
        self.assertEqual(records["flowpilot_executable_matrix_coverage"]["coverage_tier"], "coverage_strong")
        self.assertEqual(records["flowpilot_fake_ai_runtime_replay"]["coverage_tier"], "coverage_strong")
        self.assertEqual(records["flowpilot_real_issue_backfeed"]["coverage_tier"], "supporting_model_owned")
        self.assertNotIn("runner_not_ok", records["flowpilot_executable_matrix_coverage"]["gap_classes"])
        self.assertNotIn(
            "runner_unparsed_or_unavailable",
            records["flowpilot_executable_matrix_coverage"]["gap_classes"],
        )
        self.assertIn(
            "currently_consumable_inventory_evidence",
            records["flowpilot_contract_exhaustion_mesh"]["gap_classes"],
        )
        self.assertIn(
            "currently_consumable_inventory_evidence",
            records["flowpilot_cartesian_control_plane_exhaustion"]["gap_classes"],
        )
        self.assertNotIn("runner_not_ok", records["flowpilot_final_confidence_gate"]["gap_classes"])
        self.assertNotIn("live_runtime_or_state_findings", records["flowpilot_process_liveness"]["gap_classes"])
        self.assertNotIn(
            "modeled_current_live_hit_fix_runtime_or_current_state",
            records["flowpilot_model_mesh"]["finding_counts"],
        )
        self.assertNotIn(
            "modeled_current_live_hit_fix_runtime_or_current_state",
            records["flowpilot_process_liveness"]["finding_counts"],
        )

    def test_inventory_marks_source_audited_and_scoped_replay_boundaries(self) -> None:
        report = inventory.build_inventory()
        records = {record["runner"]: record for record in report["records"]}

        self.assertEqual(
            records["flowpilot_model_test_alignment"]["ordinary_test_reference_strength"],
            "source_audited_alignment",
        )
        self.assertNotIn("missing_or_scoped_replay_adapter", records["flowpilot_resume"]["gap_classes"])
        self.assertIn("conformance_replay", records["flowpilot_resume"]["covered_skipped_checks"])
        self.assertTrue(records["flowpilot_resume"]["replay_evidence"]["evidence"])
        self.assertTrue(records["flowpilot_process_liveness"]["parsed"])
        self.assertNotIn(
            "runner_unparsed_or_unavailable",
            records["flowpilot_process_liveness"]["gap_classes"],
        )
        self.assertNotIn("runner_not_ok", records["meta"]["gap_classes"])
        self.assertIn("currently_consumable_inventory_evidence", records["meta"]["gap_classes"])

    def test_inventory_accepts_repository_relative_evidence_paths(self) -> None:
        report = inventory.build_inventory(
            sweep_path=Path("simulations/flowpilot_full_model_coverage_sweep_results.json"),
            alignment_path=Path("simulations/flowpilot_model_test_alignment_results.json"),
            replay_evidence_path=Path("simulations/flowpilot_full_model_replay_evidence.json"),
        )

        self.assertEqual(report["sweep_path"], "simulations/flowpilot_full_model_coverage_sweep_results.json")
        self.assertEqual(report["alignment_path"], "simulations/flowpilot_model_test_alignment_results.json")
        self.assertEqual(report["replay_evidence_path"], "simulations/flowpilot_full_model_replay_evidence.json")
        self.assertTrue(report["sweep_ok"])
        self.assertTrue(report["alignment_ok"])

    def test_persisted_sweep_enumerates_all_current_flowguard_runners(self) -> None:
        sweep = json.loads(inventory.DEFAULT_SWEEP_PATH.read_text(encoding="utf-8"))
        current = _current_runner_keys()
        persisted = {record["runner"] for record in sweep["runners"]}

        self.assertEqual(sweep["runner_count"], len(current))
        self.assertEqual(persisted, current)
        self.assertIn("flowpilot_fake_ai_runtime_replay", persisted)
        self.assertIn("flowpilot_real_issue_backfeed", persisted)

    def test_persisted_inventory_enumerates_all_current_flowguard_runners(self) -> None:
        persisted_inventory = json.loads(inventory.DEFAULT_JSON_OUT.read_text(encoding="utf-8"))
        current = _current_runner_keys()
        persisted = {record["runner"] for record in persisted_inventory["records"]}

        self.assertEqual(persisted_inventory["runner_count"], len(current))
        self.assertEqual(persisted, current)
        self.assertIn("flowpilot_fake_ai_runtime_replay", persisted)
        self.assertIn("flowpilot_real_issue_backfeed", persisted)


if __name__ == "__main__":
    unittest.main()
