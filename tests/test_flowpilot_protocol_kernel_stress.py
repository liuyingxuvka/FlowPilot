from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "flowpilot_protocol_kernel"


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


runner = load_module(
    "flowpilot_protocol_kernel_stress_runner",
    ROOT / "simulations" / "run_flowpilot_protocol_kernel_stress_checks.py",
)
model = load_module(
    "flowpilot_protocol_kernel_stress_model_for_tests",
    ROOT / "simulations" / "flowpilot_protocol_kernel_stress_model.py",
)


class FlowPilotProtocolStressTests(unittest.TestCase):
    def test_stress_asset_documents_multiround_and_testmesh_boundaries(self) -> None:
        doc = (ASSET_ROOT / "stress_testing.md").read_text(encoding="utf-8")
        for phrase in (
            "Fake AI actors are deterministic protocol actors",
            "replacement worker succeeds after a dead worker",
            "A green model for the wrong target is a blocked path",
            "Missing, stale, skipped, failed, progress-only, or not-run evidence",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, doc)

    def test_scripted_scenarios_accept_only_safe_paths(self) -> None:
        report = model.run_scripted_scenarios()
        self.assertTrue(report["ok"], report)
        self.assertEqual(
            {"happy_path_replacement_worker", "mixed_correct_and_stale_results"},
            set(report["accepted_cases"]),
        )

        for case in report["cases"]:
            with self.subTest(case=case["name"]):
                if case["name"] in report["accepted_cases"]:
                    self.assertEqual(case["actual_classification"], model.ACCEPTED)
                else:
                    self.assertTrue(
                        case["actual_classification"].startswith("block_"),
                        case["actual_classification"],
                    )

    def test_replacement_success_keeps_old_stale_result_out_of_authority(self) -> None:
        result = model.run_scripted_scenario(model.SCENARIO_BY_NAME["mixed_correct_and_stale_results"])
        self.assertTrue(result.ok, result.to_json())
        self.assertTrue(result.accepted)
        self.assertEqual(result.final_state.old_route_disposition, "closed")
        self.assertTrue(result.final_state.stale_result_rejected)
        self.assertEqual(result.final_state.active_route_version, result.final_state.result_route_version)

    def test_historical_replay_blocks_known_bad_families(self) -> None:
        replay = model.run_historical_replay()
        self.assertTrue(replay["ok"], replay)
        self.assertGreaterEqual(replay["case_count"], 9)
        for case in replay["cases"]:
            with self.subTest(case=case["name"]):
                self.assertFalse(case["accepted"])
                self.assertTrue(case["actual_classification"].startswith("block_"))

    def test_seeded_random_long_run_is_reproducible_and_clean(self) -> None:
        first = model.run_seeded_random_long_runs(seeds=(101, 202), steps_per_seed=40)
        second = model.run_seeded_random_long_runs(seeds=(101, 202), steps_per_seed=40)
        self.assertTrue(first["ok"], first)
        self.assertEqual(first["runs"], second["runs"])
        self.assertEqual([], first["violations"])

    def test_runner_builds_routine_testmesh_without_release_overclaim(self) -> None:
        report = runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertEqual(report["mode"], "routine")
        self.assertTrue(report["test_mesh"]["parent_gates"]["routine_stress_gate"]["ok"])
        self.assertFalse(report["test_mesh"]["parent_gates"]["release_stress_gate"]["ok"])

        rows = {row["id"]: row for row in report["test_mesh"]["rows"]}
        self.assertEqual(rows["background_project_regressions"]["status"], "not_run")
        self.assertEqual(rows["install_surface_parity"]["status"], "not_run")
        for row_id in (
            "focused_kernel_unsupported_historical",
            "deterministic_multiround_scenarios",
            "seeded_random_long_run",
            "historical_bad_case_replay",
            "flowguard_stress_explorer",
        ):
            with self.subTest(row_id=row_id):
                self.assertEqual(rows[row_id]["status"], "passed")
                self.assertEqual(rows[row_id]["freshness"], "current")

    def test_hazard_states_reject_false_stress_completion(self) -> None:
        hazards = model.hazard_states()
        self.assertIn("happy_path_forced_blocked", hazards)
        self.assertGreaterEqual(len(hazards), 12)
        for name, state in hazards.items():
            with self.subTest(name=name):
                self.assertTrue(model.hard_check_failures(state))


if __name__ == "__main__":
    unittest.main()
