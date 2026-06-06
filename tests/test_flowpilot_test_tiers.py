from __future__ import annotations

import contextlib
import io
import importlib.util
import fnmatch
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


run_test_tier = load_module(
    "flowpilot_test_run_test_tier",
    ROOT / "scripts" / "run_test_tier.py",
)
run_tiering_checks = load_module(
    "flowpilot_test_run_tiering_checks",
    ROOT / "simulations" / "run_flowpilot_test_tiering_checks.py",
)
run_slow_contract_checks = load_module(
    "flowpilot_test_run_slow_contract_checks",
    ROOT / "simulations" / "run_flowpilot_slow_test_contract_checks.py",
)


def iter_test_cases(suite: unittest.TestSuite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from iter_test_cases(item)
        else:
            yield item


def ids_for_module(module_name: str) -> set[str]:
    return {case.id() for case in iter_test_cases(unittest.defaultTestLoader.loadTestsFromName(module_name))}


def unittest_k_matches(test_id: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(test_id, pattern) if "*" in pattern else pattern in test_id


class FlowPilotTestTierTests(unittest.TestCase):
    def command_text(self, tier: str) -> str:
        plan = run_test_tier.plan_for_tier(
            tier,
            background_dir=ROOT / "tmp" / "test_background",
        )
        return "\n".join(" ".join(command["command"]) for command in plan["commands"])

    def test_tier_command_names_are_unique_within_background_artifact_scope(self) -> None:
        for tier in run_test_tier.tier_names():
            with self.subTest(tier=tier):
                names = [command.name for command in run_test_tier.commands_for_tier(tier)]
                duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
                self.assertFalse(duplicates, f"{tier} has duplicate command names: {duplicates}")

    def test_collect_tier_scopes_pytest_to_tests_tree(self) -> None:
        commands = run_test_tier.commands_for_tier("collect")
        self.assertEqual(len(commands), 1)
        command = list(commands[0].command)
        self.assertIn("pytest", command)
        self.assertIn("tests", command)
        self.assertIn("--collect-only", command)
        self.assertNotIn("backups", command)
        self.assertNotIn("tmp", command)

    def test_main_list_tiers_json_uses_public_cli_contract(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            exit_code = run_test_tier.main(["--list-tiers", "--json"])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("fast", payload["tiers"])
        self.assertIn("release", payload["tiers"])
        self.assertIn("final-confidence", payload["tiers"])

    def test_main_release_dry_run_json_marks_release_only_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-cli-") as tmp_name:
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                exit_code = run_test_tier.main(
                    [
                        "--tier",
                        "release",
                        "--dry-run",
                        "--json",
                        "--background-dir",
                        tmp_name,
                    ]
                )

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["tier"], "release")
        self.assertTrue(any(command["release_only"] for command in payload["commands"]))
        self.assertFalse(payload["release_obligation_visible"])

    def test_all_tier_commands_have_external_command_contracts(self) -> None:
        # Diagnostic evidence literals: integration, smoke_flowpilot_fast, flowguard_coverage_sweep.
        tier_names = set(run_test_tier.tier_names())
        for tier in ("fast", "integration", "router", "release", "all"):
            with self.subTest(tier=tier):
                self.assertIn(tier, tier_names)
                self.assertTrue(run_test_tier.commands_for_tier(tier))

        for tier in run_test_tier.tier_names():
            for command in run_test_tier.commands_for_tier(tier):
                with self.subTest(tier=tier, command=command.name):
                    self.assertTrue(command.name)
                    self.assertTrue(command.command)
                    for token in command.command:
                        normalized = str(token).replace("\\", "/")
                        if normalized.endswith(".py"):
                            self.assertTrue((ROOT / normalized).exists(), normalized)
                        if normalized.startswith(("tests.", "simulations.")):
                            module_path = ROOT / (normalized.replace(".", "/") + ".py")
                            package_init = ROOT / normalized.replace(".", "/") / "__init__.py"
                            self.assertTrue(
                                module_path.exists() or package_init.exists(),
                                normalized,
                            )

        integration_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("integration")
        }
        self.assertIn("smoke_flowpilot_fast", integration_commands)
        self.assertIn("flowguard_coverage_sweep", integration_commands)
        self.assertTrue(integration_commands["smoke_flowpilot_fast"].background_recommended)
        self.assertTrue(integration_commands["flowguard_coverage_sweep"].background_recommended)
        self.assertEqual(
            list(integration_commands["flowguard_coverage_sweep"].command)[-2:],
            ["--timeout-seconds", "60"],
        )

        release_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("release")
        }
        self.assertIn("public_release_check", release_commands)
        self.assertTrue(release_commands["public_release_check"].release_only)
        self.assertTrue(release_commands["public_release_check"].background_recommended)

        final_confidence_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("final-confidence")
        }
        self.assertIn("flowpilot_final_confidence_gate", final_confidence_commands)
        self.assertIn(
            "run_flowpilot_final_confidence_gate_checks.py",
            " ".join(final_confidence_commands["flowpilot_final_confidence_gate"].command),
        )

    def test_background_artifact_classifier_distinguishes_final_evidence_states(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-bg-classifier-") as tmp_name:
            root = Path(tmp_name)

            def write_case(name: str, *, meta: dict[str, object] | None, exit_text: str | None, progress: str = ""):
                paths = run_test_tier.artifact_paths(root, name)
                if meta is not None:
                    paths["meta"].write_text(
                        "\ufeff" + json.dumps(meta, sort_keys=True),
                        encoding="utf-8",
                    )
                if exit_text is not None:
                    paths["exit"].write_text(exit_text, encoding="utf-8")
                if progress:
                    paths["combined"].write_text(progress, encoding="utf-8")

            write_case("passed", meta={"status": "passed"}, exit_text="0\n")
            write_case("failed", meta={"status": "failed"}, exit_text="1\n")
            write_case("running", meta={"status": "running"}, exit_text=None)
            write_case("exit_zero_meta_race", meta={"status": "running"}, exit_text="0\n")
            write_case("stale_failed", meta={"status": "running"}, exit_text="1\n")
            write_case("progress_only", meta=None, exit_text=None, progress="still running\n")
            write_case("incomplete", meta={"status": "passed"}, exit_text=None)
            write_case(
                "release_local",
                meta={"status": "passed", "command": ["python", "scripts/check_public_release.py", "--skip-url-check"]},
                exit_text="0\n",
            )

            self.assertEqual(run_test_tier.classify_background_artifact(root, "passed")["status"], "passed")
            self.assertEqual(run_test_tier.classify_background_artifact(root, "failed")["status"], "failed")
            self.assertEqual(run_test_tier.classify_background_artifact(root, "running")["status"], "running")
            meta_race = run_test_tier.classify_background_artifact(root, "exit_zero_meta_race")
            self.assertEqual(meta_race["status"], "passed")
            self.assertIn("exit_zero_won_meta_update_race", meta_race["reasons"])
            self.assertEqual(run_test_tier.classify_background_artifact(root, "stale_failed")["status"], "failed")
            self.assertEqual(
                run_test_tier.classify_background_artifact(root, "progress_only")["status"],
                "progress_only",
            )
            self.assertEqual(
                run_test_tier.classify_background_artifact(root, "incomplete")["status"],
                "incomplete",
            )
            local = run_test_tier.classify_background_artifact(root, "release_local")
            self.assertEqual(local["status"], "release_local_only")
            self.assertEqual(local["proof_scope"], "local_only")

    def test_fast_tier_excludes_release_coverage_and_full_regression(self) -> None:
        command_names = [command.name for command in run_test_tier.commands_for_tier("fast")]
        text = self.command_text("fast")
        self.assertIn("run_flowpilot_slow_test_contract_checks.py", text)
        self.assertIn("run_flowpilot_model_test_alignment_checks.py", text)
        self.assertIn("run_flowpilot_project_topology_orientation_checks.py", text)
        self.assertIn("scripts/flowguard_project_topology.py", text)
        self.assertIn("tests/test_flowguard_project_topology.py", text)
        self.assertIn("flowguard_project_topology_build", command_names)
        self.assertIn("flowguard_project_topology_check", command_names)
        self.assertIn("flowpilot_hard_gate_red_team_matrix.py", text)
        self.assertIn("flowpilot_e2e_synthetic_chaos_matrix.py", text)
        self.assertIn("flowpilot_real_router_dry_run_rehearsal_matrix.py", text)
        self.assertIn("flowpilot_control_plane_failure_canary_matrix.py", text)
        self.assertIn("flowpilot_shadow_launcher_chaos_matrix.py", text)
        self.assertIn("flowpilot_historical_live_run_replay_matrix.py", text)
        self.assertIn("flowpilot_known_friction_regression_matrix.py", text)
        self.assertIn("tests/test_flowpilot_model_test_alignment.py", text)
        self.assertIn("tests/test_flowpilot_hard_gate_red_team_matrix.py", text)
        self.assertIn("tests/test_flowpilot_hard_gate_red_team_replay.py", text)
        self.assertIn("tests/test_flowpilot_e2e_synthetic_chaos_matrix.py", text)
        self.assertIn("tests/test_flowpilot_e2e_synthetic_chaos_replay.py", text)
        self.assertIn("tests/test_flowpilot_real_router_dry_run_rehearsal_matrix.py", text)
        self.assertIn("tests/test_flowpilot_real_router_dry_run_rehearsal.py", text)
        self.assertIn("tests/test_flowpilot_control_plane_failure_canary_matrix.py", text)
        self.assertIn("tests/test_flowpilot_control_plane_failure_canary_replay.py", text)
        self.assertIn("tests/test_flowpilot_shadow_launcher_chaos_matrix.py", text)
        self.assertIn("tests/test_flowpilot_shadow_launcher_chaos_replay.py", text)
        self.assertIn("tests/test_flowpilot_historical_live_run_replay_matrix.py", text)
        self.assertIn("tests/test_flowpilot_historical_live_run_replay.py", text)
        self.assertIn("tests/test_flowpilot_known_friction_regression_matrix.py", text)
        self.assertIn("tests/test_flowpilot_cli_entrypoints.py", text)
        self.assertNotIn("check_public_release.py", text)
        self.assertNotIn("run_flowguard_coverage_sweep.py", text)
        self.assertNotIn("--full", text)

    def test_fast_tier_descriptions_name_multiround_repair_rehearsals(self) -> None:
        descriptions = {
            command.name: command.description
            for command in run_test_tier.commands_for_tier("fast")
        }

        self.assertIn("no-producer PM repair recovery", descriptions["e2e_synthetic_chaos_matrix"])
        self.assertIn("producer-proof repair waits", descriptions["real_router_dry_run_rehearsal_matrix"])
        self.assertIn("PM repair atomicity", descriptions["known_friction_regression_matrix"])
        self.assertIn("no-producer repair gate", descriptions["e2e_synthetic_chaos_no_producer_tests"])
        self.assertIn("repair producer proof", descriptions["real_router_dry_run_rehearsal_tests"])

    def test_fast_tier_splits_long_replay_tests_into_named_shards(self) -> None:
        commands = {
            command.name: list(command.command)
            for command in run_test_tier.commands_for_tier("fast")
        }

        self.assertNotIn("synthetic_agent_trace_replay_tests", commands)
        self.assertNotIn("e2e_synthetic_chaos_replay_tests", commands)
        self.assertNotIn("synthetic_agent_trace_repair_tests", commands)
        self.assertNotIn("synthetic_agent_trace_system_story_tests", commands)
        self.assertNotIn("e2e_synthetic_chaos_replay_repair_tests", commands)
        self.assertNotIn("e2e_synthetic_chaos_replay_proof_tests", commands)
        self.assertNotIn("shadow_launcher_chaos_replay_tests", commands)

        expected_shards = {
            "synthetic_agent_trace_core_tests",
            "synthetic_agent_trace_reissue_retry_tests",
            "synthetic_agent_trace_pm_repair_accept_tests",
            "synthetic_agent_trace_pm_repair_reject_tests",
            "synthetic_agent_trace_fatal_waiver_tests",
            "synthetic_agent_trace_resume_preempt_tests",
            "synthetic_agent_trace_stale_sibling_tests",
            "synthetic_agent_trace_envelope_authority_tests",
            "synthetic_agent_trace_controller_budget_tests",
            "synthetic_agent_trace_material_repair_tests",
            "synthetic_agent_trace_dirty_terminal_tests",
            "synthetic_agent_trace_bad_repair_envelope_tests",
            "synthetic_agent_trace_stacked_blockers_tests",
            "synthetic_agent_trace_failed_repair_loop_tests",
            "synthetic_agent_trace_stale_run_state_tests",
            "synthetic_agent_trace_parallel_stop_tests",
            "synthetic_agent_trace_terminal_total_gate_tests",
            "e2e_synthetic_chaos_golden_lifecycle_tests",
            "e2e_synthetic_chaos_worker_repair_tests",
            "e2e_synthetic_chaos_pm_repair_tests",
            "e2e_synthetic_chaos_no_producer_tests",
            "e2e_synthetic_chaos_background_proof_tests",
            "e2e_synthetic_chaos_parallel_stop_tests",
            "e2e_synthetic_chaos_terminal_retry_tests",
            "shadow_launcher_shadow_start_tests",
            "shadow_launcher_crash_recovery_tests",
            "shadow_launcher_peer_conflict_tests",
            "shadow_launcher_current_assets_tests",
            "shadow_launcher_malformed_package_tests",
            "shadow_launcher_bounded_soak_tests",
        }
        self.assertLessEqual(expected_shards, set(commands))

        for name in expected_shards:
            with self.subTest(name=name):
                command = commands[name]
                self.assertIn("-k", command)
                pattern = command[command.index("-k") + 1]
                self.assertIn("test_", pattern)
                self.assertNotEqual(pattern, "FlowPilotSyntheticAgentTraceReplayTests")
                self.assertNotEqual(pattern, "FlowPilotEndToEndSyntheticChaosReplayTests")

    def test_router_parent_composes_child_slice_commands(self) -> None:
        command_names = [command.name for command in run_test_tier.commands_for_tier("router")]
        self.assertIn("router_testmesh_parent", command_names)
        self.assertIn("router_startup_runtime_contracts", command_names)
        self.assertIn("router_bootstrap_cli", command_names)
        self.assertIn("router_startup_bootstrap_core", command_names)
        self.assertIn("router_startup_bootstrap_reconciliation", command_names)
        self.assertIn("router_startup_bootstrap_intake", command_names)
        self.assertIn("router_startup_bootstrap_review", command_names)
        self.assertIn("router_startup_bootstrap_fact_manual_resume", command_names)
        self.assertIn("router_startup_daemon", command_names)
        self.assertIn("router_foreground", command_names)
        self.assertIn("router_controller", command_names)
        self.assertIn("router_dispatch_gate_current_node_review", command_names)
        self.assertIn("router_dispatch_gate_recipient_policy", command_names)
        self.assertIn("router_dispatch_gate_user_pm_control", command_names)
        self.assertIn("router_foreground_controller_core", command_names)
        self.assertIn("router_foreground_controller_standby", command_names)
        self.assertIn("router_foreground_controller_receipts", command_names)
        self.assertIn("router_foreground_controller_boundary", command_names)
        self.assertIn("router_foreground_controller_repair", command_names)
        self.assertIn("router_packet_runtime", command_names)
        self.assertIn("router_packets_material", command_names)
        self.assertIn("router_packets_current_node_direct", command_names)
        self.assertIn("router_packets_current_node_dispatch", command_names)
        self.assertIn("router_packets_current_node_result_audit", command_names)
        self.assertIn("router_packets_current_node_result_decision", command_names)
        self.assertIn("router_packets_batch_and_grants", command_names)
        self.assertIn("router_packet_result_family", command_names)
        self.assertIn("router_cards", command_names)
        self.assertIn("router_ack_return", command_names)
        self.assertIn("router_boundaries", command_names)
        self.assertIn("router_route_mutation_draft_activation", command_names)
        self.assertIn("router_route_mutation_model_miss_triage", command_names)
        self.assertIn("router_route_mutation_acceptance_repair", command_names)
        self.assertIn("router_route_mutation_preconditions", command_names)
        self.assertIn("router_route_mutation_transactions", command_names)
        self.assertIn("router_route_mutation_topology", command_names)
        self.assertIn("router_route_mutation_sibling_replacement", command_names)
        self.assertIn("router_route_mutation_parent_backward", command_names)
        self.assertIn("router_route_mutation_contracts", command_names)
        self.assertIn("router_user_flow_diagram", command_names)
        self.assertIn("router_terminal_final_ledger", command_names)
        self.assertIn("router_terminal_replay_summary", command_names)
        self.assertIn("router_terminal_node_stop", command_names)
        self.assertIn("router_closure_dirty_ledgers", command_names)
        self.assertIn("router_closure_pm_role_work", command_names)
        self.assertIn("router_resume_reentry", command_names)
        self.assertIn("router_resume_rehydration", command_names)
        self.assertIn("router_resume_role_recovery", command_names)
        self.assertIn("router_resume_liveness_faults", command_names)
        self.assertIn("router_control_blockers_recorded_events", command_names)
        self.assertIn("router_control_blockers_reissue_retry", command_names)
        self.assertIn("router_control_blockers_pm_repair_decisions", command_names)
        self.assertIn("router_control_blockers_protocol_transactions", command_names)
        self.assertIn("router_control_blockers_followup_fatal", command_names)
        self.assertIn("router_pm_role_work_requests", command_names)
        self.assertIn("router_pm_role_work_results", command_names)
        self.assertIn("router_pm_role_work_waits", command_names)
        self.assertIn("router_quality_gates_background_manifest", command_names)
        self.assertIn("router_quality_gates_decisions", command_names)
        self.assertIn("router_quality_gates_evidence_artifacts", command_names)
        self.assertIn("router_quality_gates_route_model", command_names)
        self.assertIn("router_quality_gates_node_contracts", command_names)
        self.assertIn("router_material_modeling_intake", command_names)
        self.assertIn("router_material_modeling_scan_relay", command_names)
        self.assertIn("router_material_modeling_modelability", command_names)
        self.assertNotIn("router_packets_cards_ack", command_names)
        self.assertNotIn("router_startup_runtime", command_names)
        self.assertNotIn("router_dispatch_gate", command_names)
        self.assertNotIn("router_foreground_controller", command_names)
        self.assertNotIn("router_packets", command_names)
        self.assertNotIn("router_route_mutation", command_names)
        self.assertNotIn("router_route_mutation_core", command_names)
        self.assertNotIn("router_terminal", command_names)
        self.assertNotIn("router_closure", command_names)
        self.assertNotIn("router_resume", command_names)
        self.assertNotIn("router_control_blockers", command_names)
        self.assertNotIn("router_terminal_closure", command_names)
        self.assertNotIn("router_pm_role_work", command_names)
        self.assertNotIn("router_quality_gates", command_names)
        self.assertNotIn("router_material_modeling", command_names)
        self.assertNotIn("test_flowpilot_router_runtime.py", self.command_text("router"))

    def test_router_startup_and_foreground_tiers_are_granular_children(self) -> None:
        self.assertEqual(
            [command.name for command in run_test_tier.commands_for_tier("router-startup")],
            [
                "router_startup_runtime_contracts",
                "router_bootstrap_cli",
                "router_startup_bootstrap_core",
                "router_startup_bootstrap_reconciliation",
                "router_startup_bootstrap_intake",
                "router_startup_bootstrap_review",
                "router_startup_bootstrap_fact_manual_resume",
                "router_startup_daemon",
            ],
        )
        self.assertEqual(
            [command.name for command in run_test_tier.commands_for_tier("router-foreground")],
            [
                "router_foreground",
                "router_controller",
                "router_dispatch_gate_current_node_review",
                "router_dispatch_gate_recipient_policy",
                "router_dispatch_gate_user_pm_control",
                "router_foreground_controller_core",
                "router_foreground_controller_standby",
                "router_foreground_controller_receipts",
                "router_foreground_controller_boundary",
                "router_foreground_controller_repair",
            ],
        )

    def test_router_packet_tier_uses_small_stable_child_suites(self) -> None:
        commands = run_test_tier.commands_for_tier("router-packets")
        self.assertEqual(
            [command.name for command in commands],
            [
                "router_packet_runtime",
                "router_packets_material",
                "router_packets_current_node_direct",
                "router_packets_current_node_dispatch",
                "router_packets_current_node_result_audit",
                "router_packets_current_node_result_decision",
                "router_packets_batch_and_grants",
                "router_packet_result_family",
                "router_cards",
                "router_ack_return",
            ],
        )
        command_text = self.command_text("router-packets")
        self.assertIn("tests.test_flowpilot_packet_runtime", command_text)
        self.assertIn("tests.router_runtime.packets", command_text)
        self.assertIn("-k current_node_direct", command_text)
        self.assertIn("-k current_node_completion", command_text)
        self.assertIn("router_packets_current_node_result_audit", [command.name for command in commands])
        self.assertIn("router_packets_current_node_result_decision", [command.name for command in commands])
        self.assertIn("tests.router_runtime.cards", command_text)
        self.assertIn("tests.router_runtime.ack_return", command_text)

    def test_router_terminal_tier_splits_slow_tail_suites(self) -> None:
        commands = run_test_tier.commands_for_tier("router-terminal")
        self.assertEqual(
            [command.name for command in commands],
            [
                "router_pm_role_work_requests",
                "router_pm_role_work_results",
                "router_pm_role_work_waits",
                "router_quality_gates_background_manifest",
                "router_quality_gates_decisions",
                "router_quality_gates_evidence_artifacts",
                "router_quality_gates_route_model",
                "router_quality_gates_node_contracts",
                "router_material_modeling_intake",
                "router_material_modeling_scan_relay",
                "router_material_modeling_modelability",
                "router_terminal_final_ledger",
                "router_terminal_replay_summary",
                "router_terminal_node_stop",
                "router_closure_dirty_ledgers",
                "router_closure_pm_role_work",
                "router_resume_reentry",
                "router_resume_rehydration",
                "router_resume_role_recovery",
                "router_resume_liveness_faults",
                "router_control_blockers_recorded_events",
                "router_control_blockers_reissue_retry",
                "router_control_blockers_pm_repair_decisions",
                "router_control_blockers_protocol_transactions",
                "router_control_blockers_followup_fatal",
            ],
        )
        command_names = [command.name for command in commands]
        self.assertNotIn("router_terminal", command_names)
        self.assertNotIn("router_closure", command_names)
        self.assertNotIn("router_resume", command_names)
        self.assertNotIn("router_control_blockers", command_names)
        self.assertNotIn("router_pm_role_work", command_names)
        self.assertNotIn("router_quality_gates", command_names)
        self.assertNotIn("router_material_modeling", command_names)
        command_text = self.command_text("router-terminal")
        self.assertIn("-k test_final_ledger_records_frozen_contract_replay_source_paths", command_text)
        self.assertIn("-k test_resume_reentry_attaches_to_live_router_daemon_and_ledger", command_text)
        self.assertIn("-k test_pm_repair_decision_accepts_registered_rerun_target_and_waits_for_it", command_text)
        self.assertIn("-k test_pm_role_work_request_requires_valid_recipient_and_contract", command_text)
        self.assertIn("-k test_gate_decision_event_records_ledger_and_state", command_text)
        self.assertIn("-k test_material_scan_direct_relay_blocks_body_hash_mismatch", command_text)

    def test_router_k_pattern_child_suites_cover_their_modules(self) -> None:
        covered: dict[str, set[str]] = {}
        for tier in ("router-startup", "router-foreground", "router-packets", "router-terminal"):
            for command in run_test_tier.commands_for_tier(tier):
                parts = list(command.command)
                patterns: list[str] = []
                modules: list[str] = []
                index = 0
                while index < len(parts):
                    if parts[index] == "-k":
                        patterns.append(parts[index + 1])
                        index += 2
                        continue
                    if parts[index].startswith("tests."):
                        modules.append(parts[index])
                    index += 1
                if not patterns:
                    continue
                for module_name in modules:
                    module_ids = ids_for_module(module_name)
                    matched = {
                        test_id
                        for test_id in module_ids
                        if any(unittest_k_matches(test_id, pattern) for pattern in patterns)
                    }
                    self.assertTrue(matched, command.name)
                    already_covered = covered.setdefault(module_name, set())
                    duplicate_matches = already_covered & matched
                    self.assertFalse(
                        duplicate_matches,
                        f"{module_name} duplicate k-shard coverage in {command.name}: {sorted(duplicate_matches)}",
                    )
                    already_covered.update(matched)

        for module_name in (
            "tests.router_runtime.startup_bootstrap",
            "tests.router_runtime.dispatch_gate",
            "tests.router_runtime.foreground_controller",
            "tests.router_runtime.packets",
            "tests.router_runtime.terminal",
            "tests.router_runtime.closure",
            "tests.router_runtime.resume",
            "tests.router_runtime.control_blockers",
            "tests.router_runtime.pm_role_work",
            "tests.router_runtime.quality_gates",
            "tests.router_runtime.material_modeling",
        ):
            missing = ids_for_module(module_name) - covered.get(module_name, set())
            self.assertFalse(missing, f"{module_name} missing from k-shards: {sorted(missing)}")

    def test_router_route_tier_uses_small_stable_child_suites(self) -> None:
        commands = run_test_tier.commands_for_tier("router-route")
        self.assertEqual(
            [command.name for command in commands],
            [
                "router_boundaries",
                "router_route_mutation_draft_activation",
                "router_route_mutation_model_miss_triage",
                "router_route_mutation_acceptance_repair",
                "router_route_mutation_preconditions",
                "router_route_mutation_transactions",
                "router_route_mutation_topology",
                "router_route_mutation_sibling_replacement",
                "router_route_mutation_parent_backward",
                "router_route_mutation_contracts",
                "router_user_flow_diagram",
            ],
        )
        command_text = self.command_text("router-route")
        self.assertIn("tests.test_flowpilot_router_boundaries", command_text)
        self.assertIn("tests.router_runtime.route_mutation_draft_activation", command_text)
        self.assertIn("tests.router_runtime.route_mutation_model_miss_triage", command_text)
        self.assertIn("tests.router_runtime.route_mutation_acceptance_repair", command_text)
        self.assertIn("tests.router_runtime.route_mutation_preconditions", command_text)
        self.assertIn("tests.router_runtime.route_mutation_transactions", command_text)
        self.assertIn("tests.router_runtime.route_mutation_topology", command_text)
        self.assertIn("tests.router_runtime.route_mutation_sibling_replacement", command_text)
        self.assertIn("tests.router_runtime.route_mutation_parent_backward", command_text)
        self.assertNotIn("tests.router_runtime.route_mutation ", command_text)
        self.assertIn("tests.test_flowpilot_router_runtime_route_mutation", command_text)
        self.assertIn("tests.test_flowpilot_user_flow_diagram", command_text)

    def test_fast_and_router_tiers_do_not_contain_release_only_commands(self) -> None:
        for tier in (
            "fast",
            "router",
            "router-packets",
            "router-route",
            "router-pm-role-work",
            "router-quality-gates",
            "router-material-modeling",
            "router-terminal",
        ):
            with self.subTest(tier=tier):
                self.assertFalse(
                    [command.name for command in run_test_tier.commands_for_tier(tier) if command.release_only]
                )

    def test_background_artifact_contract_uses_stable_paths(self) -> None:
        paths = run_test_tier.artifact_paths(
            ROOT / "tmp" / "test_background",
            "meta full",
        )
        self.assertEqual(paths["out"].name, "meta_full.out.txt")
        self.assertEqual(paths["err"].name, "meta_full.err.txt")
        self.assertEqual(paths["combined"].name, "meta_full.combined.txt")
        self.assertEqual(paths["exit"].name, "meta_full.exit.txt")
        self.assertEqual(paths["meta"].name, "meta_full.meta.json")

    def test_background_launch_clears_stale_artifacts_before_rerun(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-artifacts-") as tmp_name:
            paths = run_test_tier.artifact_paths(Path(tmp_name), "router stale child")
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stale\n", encoding="utf-8")

            run_test_tier.clear_artifacts(paths)

            for path in paths.values():
                self.assertFalse(path.exists(), path)

    def test_background_child_launch_uses_run_test_tier_entrypoint(self) -> None:
        launch_globals = run_test_tier._launch_background.__globals__
        original_popen = launch_globals["subprocess"].Popen
        captured: dict[str, object] = {}

        class DummyProcess:
            pid = 12345

        def fake_popen(args, **kwargs):  # type: ignore[no-untyped-def]
            captured["args"] = list(args)
            captured["kwargs"] = dict(kwargs)
            return DummyProcess()

        try:
            with tempfile.TemporaryDirectory(prefix="flowpilot-tier-launch-") as tmp_name:
                launch_globals["subprocess"].Popen = fake_popen
                run_test_tier._launch_background(
                    run_test_tier.TierCommand(
                        name="child_entrypoint_fixture",
                        command=(sys.executable, "-c", "pass"),
                        description="child entrypoint fixture",
                    ),
                    log_root=Path(tmp_name),
                )
        finally:
            launch_globals["subprocess"].Popen = original_popen

        args = captured["args"]
        self.assertIsInstance(args, list)
        self.assertEqual(Path(args[1]).resolve(), ROOT / "scripts" / "run_test_tier.py")
        self.assertIn("--background-child", args)

    def test_background_supervisor_records_launch_failures(self) -> None:
        original_launch = run_test_tier._launch_background
        try:
            with tempfile.TemporaryDirectory(prefix="flowpilot-tier-supervisor-") as tmp_name:
                def fail_launch(command, *, log_root):  # type: ignore[no-untyped-def]
                    raise RuntimeError(f"artifact locked for {command.name}")

                run_test_tier._launch_background = fail_launch
                exit_code = run_test_tier.run_background_supervisor(
                    "router-route",
                    [
                        run_test_tier.TierCommand(
                            name="locked_child",
                            command=(sys.executable, "-c", "pass"),
                            description="locked child fixture",
                        )
                    ],
                    log_root=Path(tmp_name),
                    max_parallel=1,
                )

                paths = run_test_tier.artifact_paths(
                    Path(tmp_name),
                    run_test_tier.background_supervisor_name("router-route"),
                )
                meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

                self.assertEqual(exit_code, 1)
                self.assertEqual(paths["exit"].read_text(encoding="utf-8").strip(), "1")
                self.assertEqual(meta["status"], "failed")
                self.assertIn("artifact locked for locked_child", meta["error"])
                self.assertIn("artifact locked for locked_child", paths["err"].read_text(encoding="utf-8"))
        finally:
            run_test_tier._launch_background = original_launch

    def test_large_background_tiers_use_bounded_supervisor(self) -> None:
        router_count = len(run_test_tier.commands_for_tier("router"))
        self.assertGreater(router_count, run_test_tier.DEFAULT_BACKGROUND_MAX_PARALLEL)
        self.assertTrue(
            run_test_tier.should_use_background_supervisor(
                router_count,
                run_test_tier.DEFAULT_BACKGROUND_MAX_PARALLEL,
            )
        )
        self.assertEqual(
            run_test_tier.background_supervisor_name("router"),
            "router_background_supervisor",
        )

    def test_windows_background_processes_are_hidden(self) -> None:
        flags = run_test_tier._windows_hidden_process_flags()
        if os.name == "nt":
            self.assertTrue(flags & subprocess.CREATE_NO_WINDOW)
            self.assertNotEqual(run_test_tier._windows_hidden_startupinfo(), None)
        else:
            self.assertEqual(flags, 0)
            self.assertEqual(run_test_tier._hidden_process_kwargs(), {})

    def test_release_tier_marks_long_background_recommended_commands(self) -> None:
        release_commands = run_test_tier.commands_for_tier("release")
        release_long = [
            command.name
            for command in release_commands
            if command.long_running and command.background_recommended
        ]
        self.assertIn("public_release_check", release_long)
        self.assertIn("meta_full", release_long)
        self.assertIn("capability_full", release_long)
        release_stages = {command.name: command.background_stage for command in release_commands}
        self.assertEqual(release_stages["release_tooling"], 0)
        self.assertEqual(release_stages["meta_full"], 0)
        self.assertEqual(release_stages["capability_full"], 0)
        self.assertGreater(release_stages["public_release_check"], release_stages["meta_full"])

    def test_background_supervisor_respects_stage_barriers(self) -> None:
        pending = [
            run_test_tier.TierCommand(
                name="stage_1",
                command=(sys.executable, "-c", "pass"),
                description="later stage",
                background_stage=1,
            ),
            run_test_tier.TierCommand(
                name="stage_0",
                command=(sys.executable, "-c", "pass"),
                description="earlier stage",
                background_stage=0,
            ),
        ]
        self.assertEqual(run_test_tier.next_background_launch_index(pending, []), 1)
        self.assertEqual(run_test_tier.next_background_launch_index([pending[0]], [pending[1]]), None)

    def test_tiering_flowguard_model_rejects_known_bad_hazards(self) -> None:
        report = run_tiering_checks.build_report()
        self.assertTrue(report["ok"], report)
        rejected = set(report["scenario_review"]["hazard_scenarios_rejected"])
        self.assertIn("background_progress_only_claimed_pass", rejected)
        self.assertIn("root_pytest_scans_backup_tests", rejected)
        self.assertIn("router_slice_import_broken_counted_green", rejected)
        self.assertIn("router_child_tier_duplicates_k_shards", rejected)
        self.assertIn("release_public_check_races_model_proofs", rejected)
        self.assertEqual(report["background_artifact_contract"], ["out", "err", "combined", "exit", "meta"])

    def test_slow_test_contract_flowguard_model_rejects_parent_child_hazards(self) -> None:
        report = run_slow_contract_checks.build_report()
        self.assertTrue(report["ok"], report)
        rejected = set(report["scenario_review"]["hazard_scenarios_rejected"])
        self.assertIn("parent_replays_child_boot", rejected)
        self.assertIn("parent_replays_packet_worker_flow", rejected)
        self.assertIn("unbound_input_contract", rejected)
        self.assertIn("release_oracle_hidden", rejected)


if __name__ == "__main__":
    unittest.main()

