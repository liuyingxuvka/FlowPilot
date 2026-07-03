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


runner = load_module(
    "run_flowpilot_integration_cartesian_coverage_checks",
    ROOT / "simulations" / "run_flowpilot_integration_cartesian_coverage_checks.py",
)
model = runner.model


class FlowPilotIntegrationCartesianCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = runner.run_checks()

    def test_integration_cartesian_runner_accepts_full_matrix(self) -> None:
        report = self.report

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["model_id"], model.MODEL_ID)
        self.assertEqual(report["matrix"]["declared_counts"]["required_cell_count"], 132_000)
        self.assertEqual(
            report["matrix"]["observed_cell_count"],
            report["matrix"]["declared_counts"]["required_cell_count"],
        )
        self.assertEqual(report["matrix"]["runtime_hard_blocker_cells"], [])
        self.assertEqual(report["matrix"]["worker_current_gate_blocker_cells"], [])

    def test_every_declared_axis_value_is_materialized(self) -> None:
        coverage = self.report["matrix"]["axis_coverage"]

        self.assertEqual(self.report["matrix"]["missing_axis_values"], {})
        for axis, values in model.AXIS_VALUES.items():
            with self.subTest(axis=axis):
                self.assertEqual(set(coverage[axis]["present"]), set(values))

    def test_hard_composition_failures_are_not_downgraded_to_advisory(self) -> None:
        hard_cases = [
            cell
            for cell in model.iter_required_cells()
            if cell["severity"] == "hard_failure"
            and cell["failure_class"]
            in {
                "missing_integration_intent",
                "flat_checklist_route",
                "producer_after_consumer",
                "orphan_output",
                "consumer_missing",
                "child_outputs_do_not_compose",
                "final_output_scattered",
                "integration_issue_downgraded_to_nonblocking",
                "model_miss_not_triggered",
            }
        ]
        self.assertTrue(hard_cases)
        self.assertFalse(
            [
                cell["cell_id"]
                for cell in hard_cases
                if cell["expected_outcome"] in {"continue_current_flow", "pm_suggestion"}
            ]
        )

    def test_advisory_and_overblocking_cases_remain_pm_decision_support(self) -> None:
        advisory_cases = [
            cell
            for cell in model.iter_required_cells()
            if cell["severity"] in {"pm_decision_support", "nonblocking_note"}
            or cell["failure_class"] in {"duplicate_sibling_work", "optimization_incorrectly_hard_blocked"}
        ]
        self.assertTrue(advisory_cases)
        self.assertFalse(
            [
                cell["cell_id"]
                for cell in advisory_cases
                if cell["expected_outcome"] in {"same_node_repair", "route_mutation", "terminal_block"}
            ]
        )

    def test_worker_and_runtime_do_not_gain_semantic_integration_authority(self) -> None:
        worker_cells = [cell for cell in model.iter_required_cells() if cell["role"] == "worker"]
        runtime_cells = [cell for cell in model.iter_required_cells() if cell["authority"] == "runtime_mechanical_rejection"]

        self.assertTrue(worker_cells)
        self.assertTrue(runtime_cells)
        self.assertFalse([cell["cell_id"] for cell in worker_cells if cell["worker_current_gate_blocker_allowed"]])
        self.assertFalse([cell["cell_id"] for cell in runtime_cells if cell["runtime_hard_blocker_allowed"]])
        self.assertIn("prompt_or_pm_decision_not_runtime_mechanical_rejection", self.report["matrix"]["by_required_authority"])
        self.assertIn("worker_reports_blocked_needs_pm_or_pm_suggestion", self.report["matrix"]["by_required_authority"])

    def test_flowguard_hazards_cover_underblocking_overblocking_and_model_miss(self) -> None:
        hazards = self.report["hazard_checks"]["hazards"]

        self.assertIn("hard_integration_failure_underblocked_as_advisory", hazards["hard_failure_underblocked"]["failures"])
        self.assertIn("advisory_integration_finding_overblocked", hazards["advisory_overblocked"]["failures"])
        self.assertIn("semantic_integration_added_runtime_hard_blocker", hazards["runtime_semantic_hard_blocker"]["failures"])
        self.assertIn("worker_claimed_current_gate_blocker_for_integration", hazards["worker_current_gate_blocker"]["failures"])
        self.assertIn("scattered_integration_model_miss_not_routed", hazards["model_miss_not_routed"]["failures"])


if __name__ == "__main__":
    unittest.main()
