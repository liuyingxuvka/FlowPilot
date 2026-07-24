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


class FlowPilotRuntimeRetentionStructureMeshTests(unittest.TestCase):
    def test_retention_split_has_one_owner_per_function_state_and_effect(self) -> None:
        plan = model.retention_structure_plan()
        report = review_structure_mesh(plan)

        self.assertTrue(report.ok, report.to_dict())
        self.assertEqual(report.decision, "structure_mesh_green_can_continue")
        modules = {module.module_id: module for module in plan.child_modules}
        self.assertEqual(
            modules["retention_cli_facade"].dependencies,
            ("retention_scan_owner", "retention_common_kernel"),
        )
        self.assertEqual(
            modules["retention_scan_owner"].dependencies,
            ("retention_common_kernel",),
        )
        owners = {item.item_id: item.owner_module_id for item in plan.partition_items}
        self.assertEqual(owners["build_report"], "retention_scan_owner")
        self.assertEqual(owners["apply_plan"], "retention_cli_facade")
        self.assertEqual(owners["_tree_fingerprint"], "retention_common_kernel")
        self.assertEqual(
            {entry.entrypoint_id for entry in plan.public_entrypoints},
            {
                "flowpilot_runtime_retention_cli",
                "flowpilot_runtime_retention_import_api",
            },
        )

    def test_retention_structure_known_bad_variants_are_blocked(self) -> None:
        expected = {
            "missing_retention_partition_owner": "coverage_gap",
            "duplicate_retention_state_owner": "duplicate_state_owner",
            "missing_retention_facade": "facade_missing",
            "removed_retention_entrypoint": "entrypoint_removed",
            "retention_dependency_cycle": "dependency_cycle",
            "stale_retention_parity": "release_parity_not_current",
            "insufficient_retention_release_evidence": "insufficient_evidence_tier",
        }
        for name, code in expected.items():
            with self.subTest(name=name):
                report = review_structure_mesh(
                    model.retention_structure_hazard_plan(name)
                )
                self.assertFalse(report.ok)
                self.assertIn(code, {finding.code for finding in report.findings})

    def test_structure_maintenance_runner_includes_retention_mesh(self) -> None:
        report = runner.build_report()
        child = report["retention_structure_mesh"]

        self.assertTrue(child["ok"], child)
        self.assertTrue(child["report"]["ok"])
        self.assertTrue(all(row["blocked"] for row in child["hazards"]))


if __name__ == "__main__":
    unittest.main()
