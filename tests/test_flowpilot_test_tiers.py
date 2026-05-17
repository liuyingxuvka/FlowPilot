from __future__ import annotations

import importlib.util
import sys
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
        self.assertNotIn("check_public_release.py", text)
        self.assertNotIn("run_flowguard_coverage_sweep.py", text)
        self.assertNotIn("--legacy-full", text)
        self.assertNotIn("--full", text)

    def test_router_parent_composes_child_slice_commands(self) -> None:
        command_names = [command.name for command in run_test_tier.commands_for_tier("router")]
        self.assertIn("router_startup_runtime", command_names)
        self.assertIn("router_foreground_controller", command_names)
        self.assertIn("router_packets_cards_ack", command_names)
        self.assertIn("router_route_mutation", command_names)
        self.assertIn("router_terminal_closure", command_names)
        self.assertNotIn("test_flowpilot_router_runtime.py", self.command_text("router"))

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

    def test_release_and_legacy_tiers_mark_long_background_recommended_commands(self) -> None:
        release_long = [
            command.name
            for command in run_test_tier.commands_for_tier("release")
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

    def test_tiering_flowguard_model_rejects_known_bad_hazards(self) -> None:
        report = run_tiering_checks.build_report()
        self.assertTrue(report["ok"], report)
        rejected = set(report["scenario_review"]["hazard_scenarios_rejected"])
        self.assertIn("background_progress_only_claimed_pass", rejected)
        self.assertIn("root_pytest_scans_backup_tests", rejected)
        self.assertIn("router_slice_import_broken_counted_green", rejected)
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
