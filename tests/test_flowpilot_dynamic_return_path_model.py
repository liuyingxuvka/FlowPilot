from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_dynamic_return_path_model as model  # noqa: E402
import run_flowpilot_dynamic_return_path_checks as runner  # noqa: E402


class FlowPilotDynamicReturnPathModelTests(unittest.TestCase):
    def test_flowpilot_dynamic_return_path_model_accepts_and_rejects_declared_cases(self) -> None:
        graph = runner._build_graph()
        safe_graph = runner._safe_graph_report(graph)

        self.assertTrue(safe_graph["ok"], safe_graph)
        self.assertEqual(set(safe_graph["accepted_scenarios"]), set(model.VALID_SCENARIOS))
        self.assertEqual(set(safe_graph["rejected_scenarios"]), set(model.NEGATIVE_SCENARIOS))
        self.assertEqual(safe_graph["missing_labels"], [])

    def test_flowpilot_dynamic_return_path_model_has_progress_and_hazard_evidence(self) -> None:
        graph = runner._build_graph()
        progress = runner._progress_report(graph)
        hazards = runner._hazard_report()
        explorer = runner._flowguard_report()

        self.assertTrue(progress["ok"], progress)
        self.assertTrue(hazards["ok"], hazards)
        self.assertTrue(explorer["ok"], explorer)
        self.assertGreaterEqual(len(hazards["hazards"]), len(model.NEGATIVE_SCENARIOS))


if __name__ == "__main__":
    unittest.main()
