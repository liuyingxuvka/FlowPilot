from __future__ import annotations

import importlib
import unittest


fake_project_runner = importlib.import_module("simulations.run_flowpilot_fake_project_rehearsal_checks")


class FlowPilotFakeProjectRehearsalTests(unittest.TestCase):
    def test_blackbox_fake_project_rehearsal_covers_normal_and_error_flows(self) -> None:
        result = fake_project_runner.run_checks()

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["black_box_contract"]["uses_public_cli_subprocesses"])
        self.assertTrue(result["black_box_contract"]["uses_startup_ui_script"])
        self.assertFalse(result["black_box_contract"]["uses_internal_e2e_helper"])
        scenario_names = {scenario["name"] for scenario in result["scenarios"]}
        self.assertEqual(
            scenario_names,
            {
                "normal_full_path",
                "wrong_role_recovery",
                "missing_ack_block",
                "ack_only_wait",
                "retired_side_command",
            },
        )
        self.assertIn("wrong_role_lease_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("missing_ack_result_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("side_command_surface_available", result["hazard_detection"]["hazards"])


if __name__ == "__main__":
    unittest.main()
