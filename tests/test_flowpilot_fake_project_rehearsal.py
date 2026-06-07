from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock


fake_project_cli = importlib.import_module("simulations.flowpilot_fake_project_rehearsal_cli")
fake_project_runner = importlib.import_module("simulations.run_flowpilot_fake_project_rehearsal_checks")
CORE_RUNTIME = fake_project_cli.ASSETS / "flowpilot_core_runtime"
if str(CORE_RUNTIME) not in sys.path:
    sys.path.insert(0, str(CORE_RUNTIME))
packet_result_contracts = importlib.import_module("packet_result_contracts")


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

    def test_fake_rehearsal_high_standard_contract_matches_packet_contract(self) -> None:
        high_standard_body = json.loads(fake_project_cli._high_standard_contract_body())
        self.assertIn("requirements", high_standard_body)
        self.assertNotIn("decision", high_standard_body)
        self.assertNotIn("pm_visible_summary", high_standard_body)

        skill_standard_body = json.loads(fake_project_cli._skill_standard_body())
        self.assertIn("obligations", skill_standard_body)
        self.assertNotIn("selected_skills", skill_standard_body)

    def test_fake_project_success_bodies_use_declared_contract_fields(self) -> None:
        packets = [
            {"packet_id": "packet-hs", "packet_kind": "task", "route_scope": "high_standard_contract"},
            {"packet_id": "packet-discovery", "packet_kind": "task", "route_scope": "discovery"},
            {"packet_id": "packet-skill", "packet_kind": "task", "route_scope": "skill_standard"},
            {"packet_id": "packet-plan", "packet_kind": "task", "route_scope": "planning"},
            {
                "packet_id": "packet-context",
                "packet_kind": "task",
                "route_scope": "node_acceptance_plan",
                "route_node_id": "node-001",
            },
            {"packet_id": "packet-node", "packet_kind": "task", "route_scope": "node"},
            {"packet_id": "packet-flowguard", "packet_kind": "flowguard_check", "route_scope": "node"},
            {"packet_id": "packet-review", "packet_kind": "review", "route_scope": "node"},
            {"packet_id": "packet-pm", "packet_kind": "pm_disposition", "route_scope": "node_pm_disposition"},
        ]

        for packet in packets:
            with self.subTest(packet=packet["packet_id"]):
                family_id = packet_result_contracts.packet_result_family_id(packet)
                body = json.loads(fake_project_cli.current_contract_body_for_packet(packet))
                self.assertFalse(
                    packet_result_contracts.undeclared_success_fields_for_family(family_id, body),
                    (family_id, body),
                )
                self.assertFalse(
                    packet_result_contracts.forbidden_success_fields_for_family(family_id, body),
                    (family_id, body),
                )

    def test_open_current_packet_inputs_uses_authorized_reads_from_sealed_packet(self) -> None:
        calls: list[tuple[str, ...]] = []

        def fake_run_cli(_root: Path, _command_log: list[dict[str, object]], *args: str, **_kwargs: object) -> dict[str, object]:
            calls.append(args)
            if args[0] == "open-packet":
                return {
                    "ok": True,
                    "authorized_input_materials_delivered": True,
                    "authorized_input_materials": [{"result_id": "result-authorized"}],
                }
            raise AssertionError(f"unexpected CLI command: {args}")

        with mock.patch.object(fake_project_cli, "run_cli", side_effect=fake_run_cli):
            fake_project_cli.open_current_packet_inputs(
                Path("fake-root"),
                [],
                lease_id="lease-001",
                packet={"packet_id": "packet-001", "target_result_id": "result-public-projection"},
            )

        self.assertIn(("open-packet", "--lease-id", "lease-001", "--packet-id", "packet-001"), calls)
        self.assertFalse(any(call and call[0] == "open-result" for call in calls))
        self.assertNotIn("result-public-projection", {part for call in calls for part in call})


if __name__ == "__main__":
    unittest.main()
