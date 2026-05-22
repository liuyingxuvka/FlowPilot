from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402


class FlowPilotFullModelCoverageInventoryTests(unittest.TestCase):
    def test_inventory_classifies_all_current_flowguard_runners(self) -> None:
        report = inventory.build_inventory()

        runner_count = len(list((ROOT / "simulations").glob("run_*checks.py")))
        self.assertEqual(report["runner_count"], runner_count)
        self.assertGreaterEqual(report["runner_count"], 90)
        self.assertNotIn("runner_not_ok", report["gap_class_counts"])
        self.assertNotIn("live_runtime_or_state_findings", report["gap_class_counts"])
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
        self.assertTrue(report["full_coverage_ok"])
        self.assertIn("replay evidence manifest", report["claim_boundary"])

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


if __name__ == "__main__":
    unittest.main()
