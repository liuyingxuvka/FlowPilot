from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402
import flowpilot_layered_boundary_proof as layered  # noqa: E402
from flowguard import review_layered_boundary_proof  # noqa: E402


class FlowPilotLayeredBoundaryProofTests(unittest.TestCase):
    def test_current_inventory_has_green_layered_accounting_proof(self) -> None:
        inv, alignment = layered.load_inputs(
            layered.DEFAULT_INVENTORY_PATH,
            layered.DEFAULT_ALIGNMENT_PATH,
        )
        report = layered.build_report(inv, alignment)

        self.assertTrue(report["layered_accounting_ok"])
        self.assertEqual(report["accounting_decision"], "layered_boundary_proof_green")
        self.assertIn("full_leaf_cartesian_ok is stricter", report["claim_boundary"])

    def test_full_leaf_cartesian_claim_is_blocked_by_current_scoped_or_split_backlog(self) -> None:
        inv, alignment = layered.load_inputs(
            layered.DEFAULT_INVENTORY_PATH,
            layered.DEFAULT_ALIGNMENT_PATH,
        )
        report = layered.build_report(inv, alignment)
        blockers = report["requirement_blockers"]
        has_blocker = bool(blockers["blocking_gap_counts"]) or bool(
            blockers["deferred_structure_split_count"]
        ) or not blockers["alignment_full_coverage_ok"]

        self.assertEqual(report["full_leaf_cartesian_ok"], not has_blocker)
        if has_blocker:
            self.assertFalse(report["full_leaf_cartesian_ok"])
            self.assertIn(
                report["requirement_decision"],
                {
                    "child_evidence_not_current",
                    "leaf_split_required",
                    "leaf_evidence_not_current",
                    "leaf_boundary_overflow",
                },
            )

    def test_all_inventory_gap_classes_have_leaf_matrix_cells(self) -> None:
        inv = inventory.build_inventory()
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        plan = layered.build_accounting_plan(inv, alignment)
        matrix = plan.leaf_matrices[0]
        cell_ids = {cell.cell_id for cell in matrix.cells}

        for gap_class in layered.GAP_CLASS_STRATEGY:
            self.assertIn(f"gap_class:{gap_class}", cell_ids)
        self.assertEqual(set(matrix.expected_cell_ids), cell_ids)

    def test_unknown_gap_class_blocks_accounting_proof(self) -> None:
        inv = inventory.build_inventory()
        inv["gap_class_counts"] = dict(inv["gap_class_counts"], hidden_new_gap=1)
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        report = layered.build_report(inv, alignment)
        codes = {finding["code"] for finding in report["accounting_report"]["findings"]}

        self.assertFalse(report["layered_accounting_ok"])
        self.assertIn("child_evidence_not_current_pass", codes)

    def test_leaf_matrix_detects_unexpected_output_overflow(self) -> None:
        inv = inventory.build_inventory()
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        plan = layered.build_accounting_plan(inv, alignment)
        matrix = plan.leaf_matrices[0]
        cells = list(matrix.cells)
        cells[0] = replace(cells[0], observed_outputs=cells[0].observed_outputs + ("unexpected",))
        broken = replace(plan, leaf_matrices=(replace(matrix, cells=tuple(cells)),))
        report = review_layered_boundary_proof(broken)
        codes = {finding.code for finding in report.findings}

        self.assertFalse(report.ok)
        self.assertIn("leaf_cell_extra_output", codes)

    def test_synthetic_clean_inputs_make_full_leaf_requirement_green(self) -> None:
        inv = inventory.build_inventory()
        inv["gap_class_counts"] = {}
        inv["full_coverage_ok"] = True
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        alignment["full_coverage_ok"] = True
        diagnostic = dict(alignment["full_model_test_code_diagnostic"])
        diagnostic["actionable_findings"] = []
        diagnostic["deferred_structure_split_count"] = 0
        diagnostic["gap_counts"] = {}
        alignment["full_model_test_code_diagnostic"] = diagnostic
        report = layered.build_report(inv, alignment)

        self.assertTrue(report["full_leaf_cartesian_ok"])
        self.assertEqual(report["requirement_decision"], "layered_boundary_proof_green")


if __name__ == "__main__":
    unittest.main()
