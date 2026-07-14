from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
sys.path.insert(0, str(SIMULATIONS))
sys.path.insert(0, str(ASSETS))

import flowpilot_packet_result_family_parity_model as parity_model  # noqa: E402
import flowpilot_pm_package_absorption_model as pm_model  # noqa: E402
import flowpilot_role_output_runtime_checks_runner_source as role_source  # noqa: E402
import role_output_runtime  # noqa: E402
import run_flowpilot_controller_receipt_evidence_fold_checks as receipt_runner  # noqa: E402
import run_flowpilot_pm_package_absorption_checks as pm_runner  # noqa: E402


class FlowPilotPacketResultMaterialRetirementTests(unittest.TestCase):
    def test_pm_package_absorption_has_three_current_positive_owners(self) -> None:
        report = pm_runner.run_checks()

        self.assertTrue(report["ok"], report)
        absence = report["retired_material_surface_absence"]
        self.assertTrue(absence["ok"], absence)
        self.assertEqual(
            absence["observed_positive_package_kinds"],
            ["current_node", "pm_role_work", "research"],
        )
        self.assertIn(
            pm_model.RETIRED_MATERIAL_AUTHORITY_USED_AS_CURRENT,
            pm_model.NEGATIVE_SCENARIOS,
        )
        self.assertNotIn(
            pm_model.RETIRED_MATERIAL_AUTHORITY_USED_AS_CURRENT,
            pm_model.VALID_SCENARIOS,
        )
        hazard = report["hazard_checks"]["hazards"][
            pm_model.RETIRED_MATERIAL_AUTHORITY_USED_AS_CURRENT
        ]
        self.assertTrue(hazard["detected"], hazard)

    def test_controller_receipt_fold_has_no_retired_material_relay(self) -> None:
        report = receipt_runner.run_checks(include_source_audit=True)

        self.assertTrue(report["ok"], report)
        absence = report["retired_material_surface_absence"]
        self.assertTrue(absence["ok"], absence)
        self.assertEqual(absence["accepted_retired_actions"], [])
        self.assertEqual(absence["accepted_retired_postconditions"], [])
        self.assertEqual(absence["configured_retired_actions"], [])
        self.assertEqual(absence["source_retired_actions"], [])

    def test_packet_result_parity_excludes_retired_material_members(self) -> None:
        report = parity_model.build_report()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["members"], ["research", "current_node", "pm_role_work"])
        absence = report["retired_material_surface_absence"]
        self.assertTrue(absence["ok"], absence)
        self.assertEqual(absence["retired_family_members"], [])
        self.assertEqual(absence["retired_evidence_members"], [])
        self.assertEqual(absence["retired_obligation_ids"], [])

    def test_role_output_runtime_has_no_retired_material_binding(self) -> None:
        report = role_source._binding_source_report(ROOT, role_output_runtime)

        self.assertTrue(report["ok"], report)
        facts = report["facts"]
        self.assertTrue(facts["retired_material_surface_absent"], facts)
        self.assertEqual(facts["retired_material_router_events_present"], [])
        self.assertEqual(facts["retired_material_output_types_present"], [])


if __name__ == "__main__":
    unittest.main()
