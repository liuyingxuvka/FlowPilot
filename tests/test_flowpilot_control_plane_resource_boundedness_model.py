from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_control_plane_resource_boundedness_model as model  # noqa: E402
import run_flowpilot_control_plane_resource_boundedness_checks as runner  # noqa: E402


class FlowPilotControlPlaneResourceBoundednessModelTests(unittest.TestCase):
    def test_scenario_matrix_accepts_good_and_rejects_known_bad(self) -> None:
        report = runner._scenario_report()
        self.assertTrue(report["ok"], report)
        for scenario in model.VALID_SCENARIOS:
            self.assertEqual(report["rows"][scenario]["actual_status"], "accepted")
        for scenario in model.NEGATIVE_SCENARIOS:
            self.assertEqual(report["rows"][scenario]["actual_status"], "rejected")

    def test_flowguard_explorer_and_known_bad_detection_pass(self) -> None:
        explorer = runner._explorer_report()
        known_bad = runner._known_bad_report()
        self.assertTrue(explorer["ok"], explorer)
        self.assertTrue(known_bad["ok"], known_bad)

    def test_six_function_blocks_have_explicit_resource_contracts(self) -> None:
        blocks = model.build_workflow().blocks
        self.assertEqual(
            [block.name for block in blocks],
            ["Observe", "Reconcile", "Persist", "RecordProgress", "StoreEvidence", "Retain"],
        )
        for block in blocks:
            self.assertTrue(block.reads)
            self.assertTrue(block.writes)
            self.assertTrue(block.idempotency)

    def test_model_test_alignment_rows_have_one_code_and_test_owner(self) -> None:
        obligation_ids = {
            row["obligation_id"] for row in model.RESOURCE_OBLIGATION_ROWS
        }
        self.assertEqual(len(obligation_ids), len(model.RESOURCE_OBLIGATION_ROWS))
        for row in model.RESOURCE_OBLIGATION_ROWS:
            self.assertTrue((ROOT / row["primary_code_owner"]).is_file(), row)
            self.assertTrue((ROOT / row["ordinary_test_evidence"]).is_file(), row)
            self.assertIn(
                row["testmesh_owner_id"],
                {
                    "flowguard_control_plane_resource_boundedness",
                    "control_plane_resource_boundedness_contract_tests",
                },
            )

    def test_existing_owner_models_delegate_only_their_resource_obligation(self) -> None:
        module_names = (
            "flowpilot_control_plane_friction_model",
            "flowpilot_event_idempotency_model",
            "flowpilot_daemon_liveness_model",
            "flowpilot_progress_lifecycle_cartesian_model",
            "flowpilot_complete_workstream_orchestration_model",
            "flowpilot_validation_artifact_canonicalization_model",
            "flowpilot_acceptance_testmesh_model",
        )
        obligations: set[str] = set()
        for module_name in module_names:
            module = importlib.import_module(module_name)
            binding = module.RESOURCE_BOUNDEDNESS_CHILD_BINDING
            self.assertEqual(binding["model_id"], model.MODEL_ID)
            self.assertTrue(binding["claim_boundary"])
            self.assertNotIn(binding["owned_obligation"], obligations)
            obligations.add(binding["owned_obligation"])
        self.assertEqual(len(obligations), len(module_names))


if __name__ == "__main__":
    unittest.main()
