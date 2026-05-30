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
                "planning_chain_does_not_terminal",
                "route_mutation_recovery",
                "missing_ack_block",
                "ack_only_wait",
                "lifecycle_guard_resume_and_patrol",
                "retired_side_command",
            },
        )
        self.assertIn("wrong_role_lease_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("missing_ack_result_accepted", result["hazard_detection"]["hazards"])
        self.assertIn("planning_chain_terminal", result["hazard_detection"]["hazards"])
        self.assertIn("terminal_missing_route_node", result["hazard_detection"]["hazards"])
        self.assertIn("route_mutation_without_frontier_rewrite", result["hazard_detection"]["hazards"])
        self.assertIn("side_command_surface_available", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_resume_from_chat", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_patrol_allows_nonterminal_stop", result["hazard_detection"]["hazards"])
        self.assertIn("lifecycle_repeated_wait_not_recovered", result["hazard_detection"]["hazards"])
        recursive_hazards = result["recursive_route_hazard_detection"]["hazards"]
        self.assertIn("missing_node_terminal_complete", recursive_hazards)
        self.assertIn("wrong_flowguard_target_accepted", recursive_hazards)
        self.assertIn("stale_node_evidence_accepted", recursive_hazards)
        self.assertIn("dead_lease_advances_node", recursive_hazards)
        self.assertIn("mutation_without_frontier_rewrite", recursive_hazards)


if __name__ == "__main__":
    unittest.main()
