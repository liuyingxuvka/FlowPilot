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
    def test_current_inventory_accounting_matches_current_artifact_readiness(self) -> None:
        inv, alignment = layered.load_inputs(
            layered.DEFAULT_INVENTORY_PATH,
            layered.DEFAULT_ALIGNMENT_PATH,
        )
        report = layered.build_report(inv, alignment)
        expected = (
            layered._coverage_inventory_passes(inv)
            and layered._test_gap_closure_passes(inv)
            and layered._alignment_accounting_passes(alignment)
            and layered._contract_exhaustion_artifact_passes(layered._contract_exhaustion_result())
            and layered._cartesian_exhaustion_artifact_passes(layered._cartesian_exhaustion_result())
        )

        self.assertEqual(report["layered_accounting_ok"], expected)
        if expected:
            self.assertEqual(report["accounting_decision"], "layered_boundary_proof_green")
        else:
            self.assertNotEqual(report["accounting_decision"], "layered_boundary_proof_green")
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
            1 + len(layered._contract_exhaustion_expected_owners()),
        )
        self.assertEqual(set(matrix.expected_cell_ids), cell_ids)
        self.assertIn(
            "contract_exhaustion:declared_inventory",
            cell_ids,
        )
        self.assertIn(
            "contract_exhaustion:child_suite:contract_exhaustion_runtime_matrix",
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
        self.assertIn("structural_cell_and_shard_fingerprints", child_contract.outputs_emitted)
        self.assertIn("historical_failure_bridge_cells", reattachment.expected_inputs)
        self.assertIn("skipped_cartesian_cells", reattachment.expected_outputs)
        self.assertEqual(len(matrix.expected_cell_ids), 1)
        self.assertEqual(set(matrix.expected_cell_ids), cell_ids)
        self.assertEqual(cell_ids, {"cartesian_exhaustion:declared_inventory"})

    def test_contract_exhaustion_observations_come_from_child_proof_artifacts(self) -> None:
        owners = layered._contract_exhaustion_expected_owners()
        report = {
            "ok": True,
            "required_cell_count": len(
                layered.contract_exhaustion_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            ),
            "required_child_suite_owners": list(owners),
            "child_suites": {
                owner: {
                    "result_status": "passed",
                    "evidence_current": True,
                    "executed_count": 1,
                    "proof_artifact": {"artifact_id": f"proof.{owner}"},
                }
                for owner in owners
            },
        }

        self.assertTrue(layered._contract_exhaustion_artifact_passes(report))
        broken = dict(report)
        broken["child_suites"] = dict(report["child_suites"])
        first_owner = owners[0]
        broken["child_suites"][first_owner] = {
            **broken["child_suites"][first_owner],
            "result_status": "not_run",
            "evidence_current": False,
            "executed_count": 0,
            "proof_artifact": None,
        }
        self.assertFalse(layered._contract_exhaustion_artifact_passes(broken))
        failed_cell = next(
            cell
            for cell in layered._contract_exhaustion_cells(broken)
            if cell.cell_id == f"contract_exhaustion:child_suite:{first_owner}"
        )
        self.assertNotEqual(failed_cell.expected_outputs, failed_cell.observed_outputs)
        self.assertIn("observation_source", failed_cell.metadata)

    def test_alignment_observed_status_is_not_copied_into_expected_status(self) -> None:
        alignment = {
            "alignment_ok": False,
            "source_audit_ok": True,
            "full_diagnostic_ok": True,
            "release_convergence_ok": False,
            "full_model_test_code_diagnostic": {
                "unresolved_non_deferred_gap_count": 2,
            },
        }
        cells = layered._alignment_cells(alignment)

        self.assertTrue(all(cell.expected_outputs == ("passed",) for cell in cells))
        self.assertTrue(any(cell.observed_outputs == ("failed",) for cell in cells))
        self.assertTrue(
            all("observation_source" in cell.metadata for cell in cells)
        )

    def test_cartesian_structural_observation_detects_result_cell_tampering(self) -> None:
        report = layered._cartesian_exhaustion_result()
        self.assertTrue(layered._cartesian_exhaustion_artifact_passes(report))
        broken = dict(report)
        broken_matrix = dict(report["matrix"])
        broken_cells = list(broken_matrix["required_cells"])
        broken_cells[0] = {**broken_cells[0], "cell_id": "tampered-cell-id"}
        broken_matrix["required_cells"] = broken_cells
        broken["matrix"] = broken_matrix

        self.assertFalse(layered._cartesian_exhaustion_artifact_passes(broken))
        cell = layered._cartesian_exhaustion_cells(broken)[0]
        self.assertNotEqual(cell.expected_outputs, cell.observed_outputs)
        self.assertEqual(cell.metadata["claim_boundary"], "structural_declaration_only")

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
