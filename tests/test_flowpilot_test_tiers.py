from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
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


class FlowPilotTestTierTests(unittest.TestCase):
    def command_text(self, tier: str) -> str:
        plan = run_test_tier.plan_for_tier(
            tier,
            background_dir=ROOT / "tmp" / "test_background",
        )
        return "\n".join(" ".join(command["command"]) for command in plan["commands"])

    def test_collect_tier_scopes_pytest_to_tests_tree(self) -> None:
        commands = run_test_tier.commands_for_tier("collect")
        self.assertEqual(len(commands), 1)
        command = list(commands[0].command)
        self.assertIn("pytest", command)
        self.assertIn("tests", command)
        self.assertIn("--collect-only", command)
        self.assertNotIn("backups", command)
        self.assertNotIn("tmp", command)

    def test_fast_tier_excludes_release_coverage_and_legacy_full(self) -> None:
        text = self.command_text("fast")
        self.assertIn("run_flowpilot_slow_test_contract_checks.py", text)
        self.assertIn("run_flowpilot_model_test_alignment_checks.py", text)
        self.assertIn("tests/test_flowpilot_model_test_alignment.py", text)
        self.assertNotIn("check_public_release.py", text)
        self.assertNotIn("run_flowguard_coverage_sweep.py", text)
        self.assertNotIn("--legacy-full", text)
        self.assertNotIn("--full", text)

    def test_router_parent_composes_child_slice_commands(self) -> None:
        command_names = [command.name for command in run_test_tier.commands_for_tier("router")]
        self.assertIn("router_startup_runtime", command_names)
        self.assertIn("router_foreground_controller", command_names)
        self.assertIn("router_packet_runtime", command_names)
        self.assertIn("router_packets", command_names)
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
        self.assertIn("router_terminal", command_names)
        self.assertIn("router_closure", command_names)
        self.assertIn("router_resume", command_names)
        self.assertIn("router_control_blockers", command_names)
        self.assertIn("router_pm_role_work", command_names)
        self.assertIn("router_quality_gates", command_names)
        self.assertIn("router_material_modeling", command_names)
        self.assertNotIn("router_packets_cards_ack", command_names)
        self.assertNotIn("router_route_mutation", command_names)
        self.assertNotIn("router_route_mutation_core", command_names)
        self.assertNotIn("router_terminal_closure", command_names)
        self.assertNotIn("test_flowpilot_router_runtime.py", self.command_text("router"))

    def test_router_packet_tier_uses_small_stable_child_suites(self) -> None:
        commands = run_test_tier.commands_for_tier("router-packets")
        self.assertEqual(
            [command.name for command in commands],
            [
                "router_packet_runtime",
                "router_packets",
                "router_cards",
                "router_ack_return",
            ],
        )
        command_text = self.command_text("router-packets")
        self.assertIn("tests.test_flowpilot_packet_runtime", command_text)
        self.assertIn("tests.router_runtime.packets", command_text)
        self.assertIn("tests.router_runtime.cards", command_text)
        self.assertIn("tests.router_runtime.ack_return", command_text)

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
        for tier in ("fast", "router", "router-packets", "router-route", "router-terminal"):
            with self.subTest(tier=tier):
                self.assertFalse(
                    [command.name for command in run_test_tier.commands_for_tier(tier) if command.release_only]
                )

    def test_background_artifact_contract_uses_stable_paths(self) -> None:
        paths = run_test_tier.artifact_paths(
            ROOT / "tmp" / "test_background",
            "meta legacy/full",
        )
        self.assertEqual(paths["out"].name, "meta_legacy_full.out.txt")
        self.assertEqual(paths["err"].name, "meta_legacy_full.err.txt")
        self.assertEqual(paths["combined"].name, "meta_legacy_full.combined.txt")
        self.assertEqual(paths["exit"].name, "meta_legacy_full.exit.txt")
        self.assertEqual(paths["meta"].name, "meta_legacy_full.meta.json")

    def test_background_launch_clears_stale_artifacts_before_rerun(self) -> None:
        with tempfile.TemporaryDirectory(prefix="flowpilot-tier-artifacts-") as tmp_name:
            paths = run_test_tier.artifact_paths(Path(tmp_name), "router stale child")
            for path in paths.values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("stale\n", encoding="utf-8")

            run_test_tier.clear_artifacts(paths)

            for path in paths.values():
                self.assertFalse(path.exists(), path)

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

    def test_release_and_legacy_tiers_mark_long_background_recommended_commands(self) -> None:
        release_commands = run_test_tier.commands_for_tier("release")
        release_long = [
            command.name
            for command in release_commands
            if command.long_running and command.background_recommended
        ]
        legacy_long = [
            command.name
            for command in run_test_tier.commands_for_tier("legacy-full")
            if command.long_running and command.background_recommended
        ]
        self.assertIn("public_release_check", release_long)
        self.assertIn("meta_full", release_long)
        self.assertIn("capability_full", release_long)
        self.assertEqual(legacy_long, ["meta_legacy_full", "capability_legacy_full"])
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
