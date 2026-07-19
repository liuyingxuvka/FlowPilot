from __future__ import annotations

import sys
import unittest
from pathlib import Path

from flowguard import review_structure_mesh


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_structure_maintenance_model as model  # noqa: E402
import run_flowpilot_structure_maintenance_checks as runner  # noqa: E402


class FlowPilotResourceFacadeStructureMeshTests(unittest.TestCase):
    def test_resource_facades_have_one_owner_and_current_release_parity(self) -> None:
        plan = model.resource_facade_structure_plan()
        report = review_structure_mesh(plan)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.decision, "structure_mesh_green_can_continue")
        owners = {item.item_id: item.owner_module_id for item in plan.partition_items}
        self.assertEqual(
            owners["task.discovery contract registration"],
            "discovery_family_facade",
        )
        self.assertEqual(
            owners["_discovery_result_violation"],
            "discovery_runtime_owner",
        )
        self.assertEqual(
            owners["optional_material_map_is_navigation_only"],
            "material_map_navigation_owner",
        )
        self.assertEqual(
            {entry.entrypoint_id for entry in plan.public_entrypoints},
            {"task.discovery", "material_artifact_map_navigation_status"},
        )

    def test_resource_facade_known_bad_variants_are_blocked(self) -> None:
        expected = {
            "missing_resource_facade": "facade_missing",
            "removed_resource_entrypoint": "entrypoint_removed",
            "duplicate_resource_state_owner": "duplicate_state_owner",
            "stale_resource_parity": "release_parity_not_current",
            "insufficient_resource_release_evidence": "insufficient_evidence_tier",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                report = review_structure_mesh(
                    model.resource_facade_structure_hazard_plan(name)
                )
                self.assertFalse(report.ok)
                self.assertIn(code, {finding.code for finding in report.findings})

    def test_structure_maintenance_runner_includes_resource_facade_mesh(self) -> None:
        report = runner.build_report()
        child = report["resource_facade_structure_mesh"]

        self.assertTrue(child["ok"], child)
        self.assertTrue(child["report"]["ok"])
        self.assertTrue(all(row["blocked"] for row in child["hazards"]))

    def test_test_tier_split_keeps_one_public_facade_and_single_child_owners(self) -> None:
        plan = model.test_tier_structure_plan()
        report = review_structure_mesh(plan)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(
            {entry.entrypoint_id for entry in plan.public_entrypoints},
            {"run_test_tier_cli", "run_test_tier_import_api"},
        )
        owners = {item.item_id: item.owner_module_id for item in plan.partition_items}
        self.assertEqual(
            owners["background_child_exact_process_tree"],
            "test_tier_background_child",
        )
        self.assertEqual(
            owners["background_supervisor_stage_scheduler"],
            "test_tier_background_supervisor",
        )

    def test_test_tier_split_known_bad_variants_are_blocked(self) -> None:
        expected = {
            "missing_test_tier_partition_owner": "coverage_gap",
            "duplicate_test_tier_state_owner": "duplicate_state_owner",
            "missing_test_tier_facade": "facade_missing",
            "removed_test_tier_entrypoint": "entrypoint_removed",
            "stale_test_tier_parity": "release_parity_not_current",
            "insufficient_test_tier_release_evidence": "insufficient_evidence_tier",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                report = review_structure_mesh(
                    model.test_tier_structure_hazard_plan(name)
                )
                self.assertFalse(report.ok)
                self.assertIn(code, {finding.code for finding in report.findings})


if __name__ == "__main__":
    unittest.main()
