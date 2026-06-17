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

    def test_contract_exhaustion_cells_are_reattached_as_leaf_matrix(self) -> None:
        inv = inventory.build_inventory()
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        plan = layered.build_accounting_plan(inv, alignment)
        child_contract = next(
            item
            for item in plan.child_contracts
            if item.child_model_id == "contract_exhaustion_mesh"
        )
        reattachment = next(
            item
            for item in plan.reattachment_proofs
            if item.child_model_id == "contract_exhaustion_mesh"
        )
        matrix = next(
            item
            for item in plan.leaf_matrices
            if item.matrix_id == "flowpilot-contract-exhaustion-matrix"
        )
        cell_ids = {cell.cell_id for cell in matrix.cells}

        self.assertIn("historical_failure_families", child_contract.inputs_accepted)
        self.assertIn("required_child_suite_owners", child_contract.outputs_emitted)
        self.assertIn("historical_failure_families", reattachment.expected_inputs)
        self.assertIn("required_child_suite_owners", reattachment.expected_outputs)
        self.assertEqual(
            len(matrix.expected_cell_ids),
            len(layered.contract_exhaustion_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS),
        )
        self.assertGreater(len(matrix.expected_cell_ids), 500)
        self.assertEqual(set(matrix.expected_cell_ids), cell_ids)
        self.assertIn(
            "contract_exhaustion:control_plane.review_packet.empty_required_manifest.body_flowguard_evidence_manifest_entries_items_flowguard_result_id",
            cell_ids,
        )
        self.assertIn(
            "contract_exhaustion:control_plane.break_glass_loop.same_root_no_delta_retry.active_blocker_root_cause_loop_key",
            cell_ids,
        )

    def test_cartesian_control_plane_cells_are_reattached_as_leaf_matrix(self) -> None:
        inv = inventory.build_inventory()
        alignment = layered._read_json(layered.DEFAULT_ALIGNMENT_PATH)
        plan = layered.build_accounting_plan(inv, alignment)
        child_contract = next(
            item
            for item in plan.child_contracts
            if item.child_model_id == "cartesian_control_plane_exhaustion"
        )
        reattachment = next(
            item
            for item in plan.reattachment_proofs
            if item.child_model_id == "cartesian_control_plane_exhaustion"
        )
        matrix = next(
            item
            for item in plan.leaf_matrices
            if item.matrix_id == "flowpilot-cartesian-control-plane-matrix"
        )
        cell_ids = {cell.cell_id for cell in matrix.cells}

        self.assertIn("mutation_alphabet", child_contract.inputs_accepted)
        self.assertIn("required_cartesian_cells", child_contract.outputs_emitted)
        self.assertIn("historical_failure_bridge_cells", reattachment.expected_inputs)
        self.assertIn("skipped_cartesian_cells", reattachment.expected_outputs)
        self.assertEqual(
            len(matrix.expected_cell_ids),
            len(layered.cartesian_exhaustion_model.REQUIRED_CARTESIAN_CELLS),
        )
        self.assertGreater(len(matrix.expected_cell_ids), 7000)
        self.assertEqual(set(matrix.expected_cell_ids), cell_ids)
        self.assertIn(
            "cartesian_exhaustion:sealed_packet_body.missing_body.startup_intake.runtime_router",
            cell_ids,
        )
        self.assertIn(
            "cartesian_exhaustion:active_blocker_record.same_root_no_delta_retry.glassbreak_threshold_probe.glassbreak_controller",
            cell_ids,
        )

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
