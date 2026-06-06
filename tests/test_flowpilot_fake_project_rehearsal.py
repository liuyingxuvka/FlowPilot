from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from unittest import mock


fake_project_cli = importlib.import_module("simulations.flowpilot_fake_project_rehearsal_cli")
fake_project_runner = importlib.import_module("simulations.run_flowpilot_fake_project_rehearsal_checks")


class FlowPilotFakeProjectRehearsalTests(unittest.TestCase):
    def test_fake_project_rehearsal_declares_all_required_scenarios(self) -> None:
        scenario_names = {name for name, _fn in fake_project_runner.rehearsal_scenarios.SCENARIOS}

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
                "missing_current_result_fields_reissue",
                "slow_reviewer_progress_preserved",
                "accepted_packet_reassignment_rejected",
                "stop_terminal_fence",
                "host_liveness_bridge_recovery",
                "orphan_runner_summary_recovery",
                "unsupported_side_command",
            },
        )

    def test_blackbox_fake_project_rehearsal_smoke_uses_public_cli(self) -> None:
        result = fake_project_runner.run_checks(
            scenario_names={
                "unsupported_side_command",
            }
        )

        self.assertTrue(result["ok"], result)
        self.assertTrue(result["black_box_contract"]["uses_public_cli_subprocesses"])
        self.assertTrue(result["black_box_contract"]["uses_startup_ui_script"])
        self.assertFalse(result["black_box_contract"]["uses_internal_e2e_helper"])
        scenario_names = {scenario["name"] for scenario in result["scenarios"]}
        self.assertEqual(
            scenario_names,
            {
                "unsupported_side_command",
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
        self.assertIn("slow_live_reviewer_replaced", result["hazard_detection"]["hazards"])
        self.assertIn("accepted_packet_reassignment_allowed", result["hazard_detection"]["hazards"])
        self.assertIn("foreground_final_preflight_missing", result["hazard_detection"]["hazards"])
        self.assertIn("passive_wait_completed", result["hazard_detection"]["hazards"])
        self.assertIn("scoped_closure_final_return_allowed", result["hazard_detection"]["hazards"])
        recursive_hazards = result["recursive_route_hazard_detection"]["hazards"]
        self.assertIn("missing_node_terminal_complete", recursive_hazards)
        self.assertIn("wrong_flowguard_target_accepted", recursive_hazards)
        self.assertIn("stale_node_evidence_accepted", recursive_hazards)
        self.assertIn("dead_lease_advances_node", recursive_hazards)
        self.assertIn("mutation_without_frontier_rewrite", recursive_hazards)

    def test_open_current_packet_inputs_uses_authorized_reads_from_sealed_packet(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_run_cli(_root: Path, _command_log: list[dict[str, object]], *args: str, **_kwargs: object) -> dict[str, object]:
            calls.append(args)
            if args[0] == "open-packet":
                return {
                    "ok": True,
                    "sealed_packet_body": json.dumps(
                        {"authorized_result_reads": [{"result_id": "result-authorized"}]}
                    ),
                }
            if args[0] == "open-result":
                return {"ok": True}
            raise AssertionError(f"unexpected CLI command: {args}")

        with mock.patch.object(fake_project_cli, "run_cli", side_effect=fake_run_cli):
            fake_project_cli.open_current_packet_inputs(
                Path("fake-root"),
                [],
                lease_id="lease-001",
                packet={"packet_id": "packet-001", "target_result_id": "result-public-projection"},
            )

        self.assertIn(
            (
                "open-result",
                "--lease-id",
                "lease-001",
                "--packet-id",
                "packet-001",
                "--result-id",
                "result-authorized",
            ),
            calls,
        )
        self.assertNotIn("result-public-projection", {part for call in calls for part in call})


if __name__ == "__main__":
    unittest.main()
