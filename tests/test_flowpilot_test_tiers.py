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
from unittest import mock


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
source_fingerprint_module = load_module(
    "flowpilot_test_tier_source_fingerprint",
    ROOT / "scripts" / "test_tier" / "source_fingerprint.py",
)
process_liveness_module = load_module(
    "flowpilot_test_process_liveness",
    ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_process_liveness.py",
)
run_flowguard_background_module = load_module(
    "flowpilot_test_run_flowguard_background",
    ROOT / "scripts" / "run_flowguard_background.py",
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

    def test_covered_source_fingerprint_ignores_generated_results_but_tracks_source(self) -> None:
        original_root = source_fingerprint_module.ROOT
        try:
            with tempfile.TemporaryDirectory(prefix="flowpilot-source-fingerprint-") as tmp_name:
                root = Path(tmp_name)
                source_path = root / "skills" / "flowpilot" / "source.py"
                summary_path = root / "simulations" / "generated_summary.json"
                source_path.parent.mkdir(parents=True)
                summary_path.parent.mkdir(parents=True)
                source_path.write_text("VALUE = 1\n", encoding="utf-8")
                summary_path.write_text('{"status":"old"}\n', encoding="utf-8")
                source_fingerprint_module.ROOT = root
                first = source_fingerprint_module.source_fingerprint()
                summary_path.write_text('{"status":"new"}\n', encoding="utf-8")
                after_result_change = source_fingerprint_module.source_fingerprint()
                source_path.write_text("VALUE = 2\n", encoding="utf-8")
                after_source_change = source_fingerprint_module.source_fingerprint()

            self.assertEqual(first, after_result_change)
            self.assertNotEqual(first, after_source_change)
        finally:
            source_fingerprint_module.ROOT = original_root

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
        integration_order = [
            command.name for command in run_test_tier.commands_for_tier("integration")
        ]
        self.assertIn("refresh_flowguard_project_topology", integration_commands)
        self.assertLess(
            integration_order.index("refresh_flowguard_project_topology"),
            integration_order.index("check_install"),
        )
        self.assertLess(
            integration_commands["refresh_flowguard_project_topology"].background_stage,
            integration_commands["check_install"].background_stage,
        )
        all_commands_by_name = {
            command.name: command for command in run_test_tier.commands_for_tier("all")
        }
        all_topology_writers = [
            command
            for command in all_commands_by_name.values()
            if Path(command.command[-2]).name == "flowguard_project_topology.py"
            and command.command[-1] == "build"
        ]
        self.assertEqual(
            [command.name for command in all_topology_writers],
            ["flowguard_project_topology_build"],
        )
        self.assertLess(
            all_commands_by_name["flowguard_project_topology_build"].background_stage,
            all_commands_by_name["check_install"].background_stage,
        )
        cli_entrypoints = all_commands_by_name["cli_entrypoint_tests"]
        self.assertTrue(cli_entrypoints.long_running)
        self.assertTrue(cli_entrypoints.background_recommended)
        self.assertGreater(
            cli_entrypoints.background_stage,
            all_commands_by_name["check_install"].background_stage,
        )
        self.assertIn("smoke_flowpilot_fast", integration_commands)
        self.assertIn("flowguard_coverage_sweep", integration_commands)
        self.assertTrue(integration_commands["smoke_flowpilot_fast"].background_recommended)
        self.assertTrue(integration_commands["flowguard_coverage_sweep"].background_recommended)
        self.assertEqual(
            list(integration_commands["flowguard_coverage_sweep"].command)[-2:],
            ["--timeout-seconds", "300"],
        )

        release_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("release")
        }
        self.assertIn("acceptance_testmesh_contract_tests", release_commands)
        self.assertTrue(release_commands["acceptance_testmesh_contract_tests"].release_only)
        self.assertTrue(
            release_commands["acceptance_testmesh_contract_tests"].background_recommended
        )
        self.assertIn(
            "tests/test_flowpilot_acceptance_testmesh.py",
            release_commands["acceptance_testmesh_contract_tests"].command,
        )
        self.assertIn("public_release_check", release_commands)
        self.assertTrue(release_commands["public_release_check"].release_only)
        self.assertTrue(release_commands["public_release_check"].background_recommended)
        self.assertNotIn("router_testmesh_parent", release_commands)
        self.assertNotIn("smoke_flowpilot_fast", release_commands)
        self.assertNotIn("formal_ai_submit_fast_runner", release_commands)
        self.assertNotIn("formal_ai_submit_adversarial_runner", release_commands)
        self.assertNotIn("flowpilot_final_confidence_gate", release_commands)

        adversarial_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("formal-submit-adversarial")
        }
        all_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("all")
        }
        self.assertIn("formal_ai_submit_adversarial_runner", adversarial_commands)
        self.assertIn("fake_ai_runtime_replay_full", adversarial_commands)
        self.assertIn("current_contract_cartesian_declaration", adversarial_commands)
        declaration_command = list(
            adversarial_commands["current_contract_cartesian_declaration"].command
        )
        self.assertIn("--declaration-only", declaration_command)
        self.assertIn(
            "tmp/test_results/current_contract_cartesian_declaration.json",
            declaration_command,
        )
        self.assertNotIn(
            "simulations/flowpilot_current_contract_cartesian_matrix_results.json",
            declaration_command,
        )
        synthetic_declaration_command = list(
            all_commands["synthetic_agent_coverage_matrix"].command
        )
        self.assertIn("--declaration-only", synthetic_declaration_command)
        self.assertIn(
            "tmp/test_results/flowpilot_synthetic_agent_coverage_matrix_declaration.json",
            synthetic_declaration_command,
        )
        self.assertNotIn(
            "simulations/flowpilot_synthetic_agent_coverage_matrix_results.json",
            synthetic_declaration_command,
        )
        self.assertIn("flowpilot_skillguard_deep_contract", release_commands)

        final_confidence_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("final-confidence")
        }
        self.assertIn("flowpilot_final_confidence_gate", final_confidence_commands)
        self.assertIn(
            "run_flowpilot_final_confidence_gate_checks.py",
            " ".join(final_confidence_commands["flowpilot_final_confidence_gate"].command),
        )
        self.assertIn(
            "--repository-confidence-only",
            final_confidence_commands["flowpilot_final_confidence_gate"].command,
        )
        self.assertIn(
            "Per-run terminal-return",
            final_confidence_commands["flowpilot_final_confidence_gate"].description,
        )
        self.assertEqual(
            final_confidence_commands["flowpilot_final_confidence_gate"].evidence_dependency,
            "terminal_consumer",
        )

    def test_complete_workstream_and_resource_checks_participate_in_parent_tiers(self) -> None:
        fast_names = {
            command.name for command in run_test_tier.commands_for_tier("fast")
        }
        all_names = {
            command.name for command in run_test_tier.commands_for_tier("all")
        }
        adversarial_names = {
            command.name
            for command in run_test_tier.commands_for_tier("formal-submit-adversarial")
        }
        release_names = {
            command.name for command in run_test_tier.commands_for_tier("release")
        }

        focused_owners = {
            "flowguard_complete_workstream_orchestration",
            "flowguard_ordinary_resource_discovery",
            "flowguard_skillguard_current_contract",
            "complete_workstream_contract_tests",
        }
        self.assertTrue(focused_owners.issubset(fast_names))
        self.assertTrue(focused_owners.issubset(all_names))
        self.assertIn("complete_workstream_fake_ai_execution_receipts", adversarial_names)
        self.assertIn("acceptance_testmesh_contract_tests", release_names)

    def test_release_and_final_confidence_have_acyclic_single_owner_order(self) -> None:
        release_names = {
            command.name for command in run_test_tier.commands_for_tier("release")
        }
        adversarial_names = {
            command.name
            for command in run_test_tier.commands_for_tier("formal-submit-adversarial")
        }
        final_commands = run_test_tier.commands_for_tier("final-confidence")

        self.assertNotIn("flowpilot_final_confidence_gate", release_names)
        self.assertNotIn("flowpilot_final_confidence_gate", adversarial_names)
        self.assertEqual(
            [command.name for command in final_commands],
            ["flowpilot_final_confidence_gate"],
        )
        self.assertTrue(
            all(command.evidence_dependency == "upstream" for command in run_test_tier.commands_for_tier("release"))
        )
        self.assertEqual(final_commands[0].evidence_dependency, "terminal_consumer")

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

    def test_verify_background_tier_accepts_current_single_command_artifacts(self) -> None:
        command = run_test_tier.TierCommand(
            name="single_current",
            command=(sys.executable, "-c", "pass"),
            description="single current background command",
        )
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-verify-single-") as tmp_name:
            root = Path(tmp_name)
            paths = run_test_tier.artifact_paths(root, command.name)
            for key in ("out", "err", "combined"):
                paths[key].write_text("verified\n", encoding="utf-8")
            paths["exit"].write_text("0\n", encoding="utf-8")
            paths["meta"].write_text(
                json.dumps(
                    {
                        "name": command.name,
                        "command": list(command.command),
                        "status": "passed",
                        "exit_code": 0,
                        "covered_source_fingerprint": "source-current",
                    }
                ),
                encoding="utf-8",
            )

            report = run_test_tier.verify_background_tier(
                "single",
                (command,),
                log_root=root,
                expected_source_fingerprint="source-current",
            )

        self.assertTrue(report["ok"], report)
        self.assertFalse(report["supervisor_present"])
        self.assertEqual(report["verified_count"], 1)

    def test_verify_background_tier_rejects_stale_or_incomplete_supervisor_evidence(self) -> None:
        commands = tuple(
            run_test_tier.TierCommand(
                name=f"child_{index}",
                command=(sys.executable, "-c", "pass"),
                description="current child",
            )
            for index in range(2)
        )
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-verify-supervisor-") as tmp_name:
            root = Path(tmp_name)
            for command in commands:
                paths = run_test_tier.artifact_paths(root, command.name)
                for key in ("out", "err", "combined"):
                    paths[key].write_text("verified\n", encoding="utf-8")
                paths["exit"].write_text("0\n", encoding="utf-8")
                paths["meta"].write_text(
                    json.dumps(
                        {
                            "name": command.name,
                            "command": list(command.command),
                            "status": "passed",
                            "exit_code": 0,
                            "covered_source_fingerprint": "source-old",
                        }
                    ),
                    encoding="utf-8",
                )
            supervisor_paths = run_test_tier.artifact_paths(
                root,
                run_test_tier.background_supervisor_name("multi"),
            )
            for key in ("out", "err", "combined"):
                supervisor_paths[key].write_text("verified\n", encoding="utf-8")
            supervisor_paths["exit"].write_text("0\n", encoding="utf-8")
            supervisor_paths["meta"].write_text(
                json.dumps(
                    {
                        "status": "passed",
                        "command_count": 2,
                        "running": [],
                        "completed": [
                            {"name": command.name, "ok": True} for command in commands
                        ],
                        "covered_source_fingerprint_start": "source-old",
                        "covered_source_fingerprint_end": "source-old",
                        "source_fingerprint_current": True,
                    }
                ),
                encoding="utf-8",
            )
            run_test_tier.artifact_paths(root, commands[1].name)["combined"].unlink()

            report = run_test_tier.verify_background_tier(
                "multi",
                commands,
                log_root=root,
                expected_source_fingerprint="source-current",
            )

        self.assertFalse(report["ok"])
        self.assertIn("supervisor_source_fingerprint_stale", report["failures"])
        self.assertTrue(
            any("covered_source_fingerprint_stale" in failure for failure in report["failures"])
        )
        self.assertTrue(any("missing_artifacts:combined" in failure for failure in report["failures"]))

    def test_fast_tier_excludes_release_coverage_and_full_regression(self) -> None:
        command_names = [command.name for command in run_test_tier.commands_for_tier("fast")]
        text = self.command_text("fast")
        self.assertIn("run_flowpilot_slow_test_contract_checks.py", text)
        self.assertIn("run_flowpilot_model_test_alignment_checks.py", text)
        self.assertIn("run_flowpilot_contract_exhaustion_mesh_checks.py", text)
        self.assertIn("run_flowpilot_cartesian_control_plane_exhaustion_checks.py", text)
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
        self.assertIn("run_flowpilot_current_status_projection_checks.py", text)
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

        names = [command.name for command in run_test_tier.commands_for_tier("fast")]
        self.assertLess(
            names.index("flowguard_current_status_projection"),
            names.index("known_friction_regression_matrix"),
        )

    def test_fast_tier_descriptions_name_multiround_repair_rehearsals(self) -> None:
        descriptions = {
            command.name: command.description
            for command in run_test_tier.commands_for_tier("fast")
        }

        self.assertIn("lifecycle, repair, proof", descriptions["e2e_synthetic_chaos_matrix"])
        self.assertIn("prepared fake AI packages", descriptions["real_router_dry_run_rehearsal_matrix"])
        self.assertIn("PM repair atomicity", descriptions["known_friction_regression_matrix"])
        self.assertNotIn("material", descriptions["real_router_dry_run_rehearsal_tests"].lower())

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
            "synthetic_agent_trace_dirty_terminal_tests",
            "synthetic_agent_trace_bad_repair_envelope_tests",
            "synthetic_agent_trace_stacked_blockers_tests",
            "synthetic_agent_trace_stale_run_state_tests",
            "synthetic_agent_trace_parallel_stop_tests",
            "synthetic_agent_trace_terminal_total_gate_tests",
            "e2e_synthetic_chaos_golden_lifecycle_tests",
            "e2e_synthetic_chaos_worker_repair_tests",
            "e2e_synthetic_chaos_pm_repair_tests",
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
        self.assertIn("router_startup_bootstrap_runtime_release", command_names)
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
        self.assertIn("router_packets_current_node_direct", command_names)
        self.assertIn("router_packets_current_node_dispatch_relay", command_names)
        self.assertIn("router_packets_current_node_dispatch_worker_binding", command_names)
        self.assertIn("router_packets_current_node_dispatch_unready_leaf", command_names)
        self.assertIn("router_packets_result_audit_completion", command_names)
        self.assertIn("router_packets_result_audit_reviewer_map", command_names)
        self.assertIn("router_packets_result_audit_rejection", command_names)
        self.assertIn("router_packets_result_decision_review_card", command_names)
        self.assertIn("router_packets_result_decision_relay", command_names)
        self.assertIn("router_packets_result_decision_pm_repair", command_names)
        self.assertIn("router_packets_grant_result_requires_write", command_names)
        self.assertIn("router_packets_grant_unresolved_node_entry", command_names)
        self.assertIn("router_packets_generic_ack_mail", command_names)
        self.assertIn("router_cards", command_names)
        self.assertIn("router_ack_return", command_names)
        self.assertIn("router_boundaries", command_names)
        self.assertIn("router_route_mutation_draft_policy", command_names)
        self.assertIn("router_route_mutation_draft_activation_reviewed", command_names)
        self.assertIn("router_route_mutation_draft_missing_active_node", command_names)
        self.assertIn("router_route_mutation_model_miss_refs", command_names)
        self.assertIn("router_route_mutation_model_miss_unlocks", command_names)
        self.assertIn("router_route_mutation_model_miss_non_authorizing", command_names)
        self.assertIn("router_route_mutation_model_miss_out_of_scope", command_names)
        self.assertIn("router_route_mutation_model_miss_role_work", command_names)
        self.assertIn("router_route_mutation_model_miss_closed_triage", command_names)
        self.assertIn("router_route_mutation_model_miss_delivery", command_names)
        self.assertIn("router_route_mutation_model_miss_stale_wait", command_names)
        self.assertIn("router_route_mutation_acceptance_revise", command_names)
        self.assertIn("router_route_mutation_acceptance_model_miss", command_names)
        self.assertIn("router_route_mutation_preconditions_final_ledger", command_names)
        self.assertIn("router_route_mutation_preconditions_topology_reset", command_names)
        self.assertIn("router_route_mutation_preconditions_root_gap", command_names)
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
        self.assertIn("router_quality_gates_evidence_package", command_names)
        self.assertIn("router_quality_gates_route_check_reports", command_names)
        self.assertIn("router_quality_gates_route_check_delivery", command_names)
        self.assertIn("router_quality_gates_router_owned_proof", command_names)
        self.assertIn("router_quality_gates_artifact_validation", command_names)
        self.assertIn("router_quality_gates_model_miss_sync", command_names)
        self.assertIn("router_quality_gates_node_acceptance_plan", command_names)
        self.assertIn("router_quality_gates_route_repair_reopens_draft", command_names)
        self.assertIn("router_quality_gates_root_contract", command_names)
        self.assertIn("router_quality_gates_route_draft_product_model", command_names)
        self.assertIn("router_quality_gates_node_contracts", command_names)
        self.assertNotIn("router_material_modeling_intake", command_names)
        self.assertNotIn("router_material_modeling_scan_relay", command_names)
        self.assertNotIn("router_material_modeling_modelability", command_names)
        self.assertNotIn("router_packets_cards_ack", command_names)
        self.assertNotIn("router_startup_runtime", command_names)
        self.assertNotIn("router_startup_bootstrap_review", command_names)
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
                "router_startup_bootstrap_runtime_release",
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
                "router_packets_generic_ack_mail",
                "router_packets_current_node_direct",
                "router_packets_current_node_dispatch_relay",
                "router_packets_current_node_dispatch_worker_binding",
                "router_packets_current_node_dispatch_unready_leaf",
                "router_packets_result_audit_completion",
                "router_packets_result_audit_reviewer_map",
                "router_packets_result_audit_rejection",
                "router_packets_result_decision_review_card",
                "router_packets_result_decision_relay",
                "router_packets_result_decision_pm_repair",
                "router_packets_grant_result_requires_write",
                "router_packets_grant_unresolved_node_entry",
                "router_cards",
                "router_ack_return",
            ],
        )
        command_text = self.command_text("router-packets")
        self.assertIn("tests.test_flowpilot_packet_runtime", command_text)
        self.assertIn("tests.router_runtime.packets", command_text)
        self.assertIn("-k current_node_direct", command_text)
        self.assertIn("-k test_current_node_completion_requires_reviewer_passed_packet_audit", command_text)
        self.assertIn("router_packets_result_audit_completion", [command.name for command in commands])
        self.assertIn("router_packets_result_decision_review_card", [command.name for command in commands])
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
                "router_quality_gates_evidence_package",
                "router_quality_gates_route_check_reports",
                "router_quality_gates_route_check_delivery",
                "router_quality_gates_router_owned_proof",
                "router_quality_gates_artifact_validation",
                "router_quality_gates_model_miss_sync",
                "router_quality_gates_node_acceptance_plan",
                "router_quality_gates_route_repair_reopens_draft",
                "router_quality_gates_root_contract",
                "router_quality_gates_route_draft_product_model",
                "router_quality_gates_node_contracts",
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
        self.assertNotIn("test_material_scan_direct_relay_blocks_body_hash_mismatch", command_text)

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
                    for pattern in patterns:
                        pattern_matches = {
                            test_id
                            for test_id in module_ids
                            if unittest_k_matches(test_id, pattern)
                        }
                        self.assertTrue(
                            pattern_matches,
                            f"{command.name} pattern {pattern!r} matches no tests in {module_name}",
                        )
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
        ):
            missing = ids_for_module(module_name) - covered.get(module_name, set())
            self.assertFalse(missing, f"{module_name} missing from k-shards: {sorted(missing)}")

    def test_router_route_tier_uses_small_stable_child_suites(self) -> None:
        commands = run_test_tier.commands_for_tier("router-route")
        self.assertEqual(
            [command.name for command in commands],
            [
                "router_boundaries",
                "router_route_mutation_draft_policy",
                "router_route_mutation_draft_activation_reviewed",
                "router_route_mutation_draft_missing_active_node",
                "router_route_mutation_model_miss_refs",
                "router_route_mutation_model_miss_unlocks",
                "router_route_mutation_model_miss_non_authorizing",
                "router_route_mutation_model_miss_out_of_scope",
                "router_route_mutation_model_miss_role_work",
                "router_route_mutation_model_miss_closed_triage",
                "router_route_mutation_model_miss_delivery",
                "router_route_mutation_model_miss_stale_wait",
                "router_route_mutation_acceptance_revise",
                "router_route_mutation_acceptance_model_miss",
                "router_route_mutation_preconditions_final_ledger",
                "router_route_mutation_preconditions_topology_reset",
                "router_route_mutation_preconditions_root_gap",
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
        self.assertIn("--background-child-timeout-seconds", args)
        self.assertIn("--covered-source-fingerprint", args)

    def test_unittest_shard_runner_uses_or_semantics_and_rejects_stale_patterns(self) -> None:
        good = subprocess.run(
            [
                sys.executable,
                "scripts/test_tier/unittest_shard.py",
                "-k",
                "test_main_list_tiers_json_uses_public_cli_contract",
                "-k",
                "test_main_release_dry_run_json_marks_release_only_commands",
                "tests.test_flowpilot_test_tiers",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **run_test_tier._hidden_process_kwargs(),
        )
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("Ran 2 tests", good.stderr)

        stale = subprocess.run(
            [
                sys.executable,
                "scripts/test_tier/unittest_shard.py",
                "-k",
                "test_pattern_that_no_longer_exists",
                "tests.test_flowpilot_test_tiers",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **run_test_tier._hidden_process_kwargs(),
        )
        self.assertNotEqual(stale.returncode, 0)
        self.assertIn("stale unittest shard pattern", stale.stderr)

    def test_background_child_timeout_writes_failed_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-timeout-") as tmp_name:
            exit_code = run_test_tier.run_background_child(
                "timeout_fixture",
                (sys.executable, "-c", "import time; time.sleep(5)"),
                log_root=Path(tmp_name),
                timeout_seconds=1,
            )
            paths = run_test_tier.artifact_paths(Path(tmp_name), "timeout_fixture")
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, run_test_tier.BACKGROUND_CHILD_TIMEOUT_EXIT_CODE)
            self.assertEqual(meta["status"], "failed")
            self.assertTrue(meta["timed_out"])
            self.assertTrue(meta["covered_source_fingerprint"])
            self.assertEqual(meta["failure_reason"], "background_child_timeout")
            self.assertTrue(meta["descendant_zero_confirmed"])
            self.assertTrue(meta["cleanup_proof"]["cleanup_confirmed"])
            self.assertEqual(
                paths["exit"].read_text(encoding="utf-8").strip(),
                str(run_test_tier.BACKGROUND_CHILD_TIMEOUT_EXIT_CODE),
            )

    def test_background_child_binds_windows_venv_to_direct_current_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-owner-") as tmp_name:
            exit_code = run_test_tier.run_background_child(
                "direct_current_owner_fixture",
                (
                    sys.executable,
                    "-c",
                    "import json,sys;print(json.dumps({'executable':sys.executable}))",
                ),
                log_root=Path(tmp_name),
                timeout_seconds=5,
            )
            paths = run_test_tier.artifact_paths(
                Path(tmp_name),
                "direct_current_owner_fixture",
            )
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))
            payload = json.loads(paths["out"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 0, meta)
            self.assertEqual(
                os.path.normcase(os.path.abspath(payload["executable"])),
                os.path.normcase(os.path.abspath(sys.executable)),
            )
            plan = meta["process_launch_plan"]
            self.assertEqual(plan["requested_executable"], sys.executable)
            if sys.platform == "win32" and os.path.normcase(
                os.path.abspath(str(getattr(sys, "_base_executable", "") or sys.executable))
            ) != os.path.normcase(os.path.abspath(sys.executable)):
                self.assertEqual(plan["kind"], "windows_venv_direct_base_owner")
                self.assertEqual(
                    os.path.normcase(os.path.abspath(plan["process_owner_executable"])),
                    os.path.normcase(os.path.abspath(sys._base_executable)),
                )
                self.assertEqual(plan["venv_launcher_binding"], sys.executable)
            else:
                self.assertEqual(plan["kind"], "direct_command")

    def test_timeout_terminates_descendant_tree_before_writing_terminal_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-descendants-") as tmp_name:
            exit_code = run_test_tier.run_background_child(
                "descendant_timeout_fixture",
                (
                    sys.executable,
                    "-c",
                    (
                        "import subprocess,sys,time;"
                        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
                        "time.sleep(30)"
                    ),
                ),
                log_root=Path(tmp_name),
                timeout_seconds=1,
            )
            paths = run_test_tier.artifact_paths(
                Path(tmp_name),
                "descendant_timeout_fixture",
            )
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, run_test_tier.BACKGROUND_CHILD_TIMEOUT_EXIT_CODE)
            self.assertTrue(meta["process_identity"]["start_token"])
            self.assertTrue(meta["observed_descendant_identities"])
            self.assertTrue(meta["cleanup_proof"]["cleanup_confirmed"], meta)
            self.assertTrue(meta["cleanup_proof"]["descendant_zero_confirmed"], meta)
            self.assertTrue(meta["descendant_zero_confirmed"], meta)

    def test_descendant_identity_rejects_process_that_predates_exact_owner(self) -> None:
        owner = {"pid": 1100, "start_token": "win-filetime:200"}
        older_process = {"pid": 1101, "start_token": "win-filetime:100"}
        current_child = {"pid": 1102, "start_token": "win-filetime:201"}
        self.assertFalse(
            process_liveness_module.process_identity_started_not_before(
                older_process,
                owner,
            )
        )
        with mock.patch.object(
            process_liveness_module,
            "process_identity_is_live",
            return_value=True,
        ), mock.patch.object(
            process_liveness_module,
            "_descendant_pids",
            return_value=[older_process["pid"], current_child["pid"]],
        ), mock.patch.object(
            process_liveness_module,
            "process_identity",
            side_effect={
                older_process["pid"]: older_process,
                current_child["pid"]: current_child,
            }.get,
        ):
            self.assertEqual(
                process_liveness_module.process_descendant_identities(owner),
                [current_child],
            )
        self.assertTrue(
            process_liveness_module.process_identity_started_not_before(
                current_child,
                owner,
            )
        )

    def test_background_child_allows_exact_descendants_to_exit_within_bounded_settlement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-settlement-") as tmp_name:
            exit_code = run_test_tier.run_background_child(
                "descendant_settlement_fixture",
                (
                    sys.executable,
                    "-c",
                    (
                        "import subprocess,sys,time;"
                        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(8.0)']);"
                        "time.sleep(0.15)"
                    ),
                ),
                log_root=Path(tmp_name),
                timeout_seconds=5,
            )
            paths = run_test_tier.artifact_paths(
                Path(tmp_name),
                "descendant_settlement_fixture",
            )
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 0, meta)
            self.assertTrue(meta["observed_descendant_identities"], meta)
            self.assertEqual(
                meta["cleanup_proof"]["reason"],
                "process_tree_exited_after_bounded_settlement",
            )
            self.assertTrue(meta["descendant_zero_confirmed"], meta)
            self.assertNotIn("cleanup_attempts", meta["cleanup_proof"])

    def test_background_child_rejects_descendant_surviving_bounded_settlement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-orphan-") as tmp_name:
            exit_code = run_test_tier.run_background_child(
                "descendant_orphan_fixture",
                (
                    sys.executable,
                    "-c",
                    (
                        "import subprocess,sys,time;"
                        "subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);"
                        "time.sleep(0.15)"
                    ),
                ),
                log_root=Path(tmp_name),
                timeout_seconds=5,
            )
            paths = run_test_tier.artifact_paths(
                Path(tmp_name),
                "descendant_orphan_fixture",
            )
            meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 1, meta)
            self.assertEqual(meta["status"], "failed")
            self.assertTrue(meta["observed_descendant_identities"], meta)
            self.assertEqual(
                meta["cleanup_proof"]["reason"],
                "orphan_descendants_terminated",
            )
            if sys.platform == "win32":
                self.assertTrue(
                    meta["remaining_identity_details_before_cleanup"],
                    meta,
                )
            self.assertTrue(meta["cleanup_proof"]["cleanup_confirmed"], meta)
            self.assertTrue(meta["descendant_zero_confirmed"], meta)

    def test_background_supervisor_records_launch_failures(self) -> None:
        original_launch = run_test_tier._launch_background
        try:
            with tempfile.TemporaryDirectory(prefix="flowpilot-tier-supervisor-") as tmp_name:
                def fail_launch(  # type: ignore[no-untyped-def]
                    command,
                    *,
                    log_root,
                    timeout_seconds=None,
                    source_fingerprint_value=None,
                ):
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

    def test_background_supervisor_fails_when_covered_source_changes(self) -> None:
        original_fingerprint = run_test_tier.source_fingerprint
        values = iter(("source-at-start", "source-at-end"))
        try:
            run_test_tier.source_fingerprint = lambda: next(values)
            with tempfile.TemporaryDirectory(prefix="flowpilot-tier-source-change-") as tmp_name:
                exit_code = run_test_tier.run_background_supervisor(
                    "collect",
                    [],
                    log_root=Path(tmp_name),
                    max_parallel=1,
                )

                paths = run_test_tier.artifact_paths(
                    Path(tmp_name),
                    run_test_tier.background_supervisor_name("collect"),
                )
                meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

            self.assertEqual(exit_code, 1)
            self.assertFalse(meta["source_fingerprint_current"])
            self.assertEqual(meta["failure_reason"], "covered_source_changed_during_tier")
        finally:
            run_test_tier.source_fingerprint = original_fingerprint

    def test_dedicated_material_modeling_tier_is_not_a_current_public_tier(self) -> None:
        self.assertFalse((ROOT / "tests" / "router_runtime" / "material_modeling.py").exists())
        self.assertFalse((ROOT / "tests" / "test_flowpilot_router_runtime_material_modeling.py").exists())
        self.assertNotIn("router-material-modeling", run_test_tier.tier_names())
        for tier in ("router", "router-terminal", "all", "release"):
            command_names = {
                command.name for command in run_test_tier.commands_for_tier(tier)
            }
            self.assertFalse(
                command_names
                & {
                    "router_material_modeling_intake",
                    "router_material_modeling_scan_relay",
                    "router_material_modeling_modelability",
                }
            )

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
        release_by_name = {command.name: command for command in release_commands}
        release_long = [
            command.name
            for command in release_commands
            if command.long_running and command.background_recommended
        ]
        self.assertIn("public_release_check", release_long)
        self.assertIn("meta_full", release_long)
        self.assertIn("capability_full", release_long)
        self.assertIn("acceptance_testmesh_contract_tests", release_long)
        release_stages = {command.name: command.background_stage for command in release_commands}
        self.assertEqual(release_stages["release_tooling"], 0)
        self.assertEqual(release_stages["meta_full"], 0)
        self.assertEqual(release_stages["capability_full"], 0)
        self.assertNotIn("flowpilot_final_confidence_gate", release_stages)
        self.assertGreater(release_stages["public_release_check"], release_stages["meta_full"])
        for command_name, receipt_name in (
            ("meta_full", "run_meta_checks"),
            ("capability_full", "run_capability_checks"),
        ):
            command = list(release_by_name[command_name].command)
            self.assertIn("scripts/run_flowguard_background.py", command)
            self.assertIn(receipt_name, command)
            self.assertIn("--force", command)
            self.assertNotIn("--verify", command)
            self.assertIn("Sole layered-full", release_by_name[command_name].description)
        verification_contract = (
            ROOT
            / "openspec"
            / "changes"
            / "restore-flowpilot-test-evidence-closure"
            / "verification-contract.yaml"
        ).read_text(encoding="utf-8")
        for receipt_name in ("run_meta_checks", "run_capability_checks"):
            self.assertIn(
                f"--name, {receipt_name}, --verify",
                verification_contract,
            )

    def test_flowguard_background_binds_literal_python_to_current_interpreter(self) -> None:
        command = run_flowguard_background_module._command_from_remainder(
            ("--", "python", "simulations/run_meta_checks.py", "--full", "--force")
        )
        self.assertEqual(command[0], sys.executable)
        self.assertEqual(
            command[1:],
            ("simulations/run_meta_checks.py", "--full", "--force"),
        )

    def test_successor_predecessor_disposition_inventory_is_explicit(self) -> None:
        design = (
            ROOT
            / "openspec"
            / "changes"
            / "restore-flowpilot-test-evidence-closure"
            / "design.md"
        ).read_text(encoding="utf-8")
        disposition_section = design.split(
            "### 13. Predecessor changes have explicit dispositions",
            1,
        )[1].split("## Risks / Trade-offs", 1)[0]
        for predecessor in (
            "harden-flowpilot-control-plane-ledger-hygiene",
            "adopt-runtime-requested-role-bindings",
            "harden-flowpilot-role-continuity-memory",
            "strengthen-flowpilot-reviewer-pm-challenge-chain",
            "reduce-flowpilot-contract-surface",
            "harden-flowpilot-fake-ai-review-window-coverage",
            "harden-review-window-completeness-matrix",
        ):
            with self.subTest(predecessor=predecessor):
                self.assertIn(f"`{predecessor}`", disposition_section)
        self.assertIn(
            "Earlier Cartesian, contract-exhaustion, formal-artifact, and AI-projection coverage changes",
            disposition_section,
        )
        self.assertIn("old coverage report is not successor proof", disposition_section)
        self.assertIn("reject any all-slot or fixed-role restoration interpretation", disposition_section)
        self.assertIn("`independent_challenge` stays forbidden", disposition_section)
        self.assertIn("supersede standalone broad evidence claims", disposition_section)

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

    def test_background_supervisor_serializes_shared_runtime_resources(self) -> None:
        shared = "installed_flowpilot_shadow_runtime"
        running = [
            run_test_tier.TierCommand(
                name="shadow_start",
                command=(sys.executable, "-c", "pass"),
                description="owns the installed shadow runtime",
                background_exclusive_resource=shared,
            )
        ]
        pending = [
            run_test_tier.TierCommand(
                name="shadow_recovery",
                command=(sys.executable, "-c", "pass"),
                description="needs the same installed shadow runtime",
                background_exclusive_resource=shared,
            ),
            run_test_tier.TierCommand(
                name="unrelated_model",
                command=(sys.executable, "-c", "pass"),
                description="does not share the runtime",
            ),
        ]
        self.assertEqual(
            run_test_tier.next_background_launch_index(pending, running),
            1,
        )
        shadow_commands = {
            command.name: command
            for command in run_test_tier.commands_for_tier("all")
            if command.name.startswith("shadow_launcher_")
            and command.name.endswith("_tests")
        }
        expected = {
            "shadow_launcher_shadow_start_tests",
            "shadow_launcher_crash_recovery_tests",
            "shadow_launcher_peer_conflict_tests",
            "shadow_launcher_current_assets_tests",
            "shadow_launcher_malformed_package_tests",
            "shadow_launcher_bounded_soak_tests",
        }
        self.assertLessEqual(expected, set(shadow_commands))
        self.assertEqual(
            {
                shadow_commands[name].background_exclusive_resource
                for name in expected
            },
            {shared},
        )

    def test_tiering_flowguard_model_rejects_known_bad_hazards(self) -> None:
        report = run_tiering_checks.build_report()
        self.assertTrue(report["ok"], report)
        rejected = set(report["scenario_review"]["hazard_scenarios_rejected"])
        self.assertIn("background_progress_only_claimed_pass", rejected)
        self.assertIn("background_running_without_timeout_guard", rejected)
        self.assertIn("background_inner_interpreter_follows_external_upgrade", rejected)
        self.assertIn("background_shared_runtime_resource_race", rejected)
        self.assertIn("background_descendant_settlement_missing", rejected)
        self.assertIn("background_predating_process_misclassified_as_descendant", rejected)
        self.assertIn("background_surviving_descendant_promoted", rejected)
        self.assertIn("json_write_readback_can_hang_control_gate", rejected)
        self.assertIn("root_pytest_scans_backup_tests", rejected)
        self.assertIn("router_slice_import_broken_counted_green", rejected)
        self.assertIn("router_child_tier_duplicates_k_shards", rejected)
        self.assertIn("router_child_tier_stale_k_pattern", rejected)
        self.assertIn("release_public_check_races_model_proofs", rejected)
        self.assertIn("release_embeds_final_confidence_consumer", rejected)
        self.assertIn("testmesh_mta_final_confidence_dependency_cycle", rejected)
        self.assertIn("install_check_races_topology_writers", rejected)
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

