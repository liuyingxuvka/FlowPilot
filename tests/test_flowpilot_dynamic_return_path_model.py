from __future__ import annotations

import json
import sys
import tempfile
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

    def test_missing_current_run_is_scoped_projection_not_history_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            projection = model.project_live_run_projection(Path(tmp))

        self.assertTrue(projection["ok"], projection)
        self.assertTrue(projection["skipped"])
        self.assertEqual(projection["classification"], "current_run_missing")
        self.assertFalse(projection["current_run_can_continue"])
        self.assertFalse(projection["safe_to_claim_live_run_confidence"])
        self.assertTrue(projection["metadata_only"])

    def test_legacy_current_pointer_aliases_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".flowpilot" / "runs" / "run-legacy").mkdir(parents=True)
            (root / ".flowpilot" / "current.json").write_text(
                json.dumps(
                    {
                        "active_run_id": "run-legacy",
                        "active_run_root": ".flowpilot/runs/run-legacy",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            projection = model.project_live_run_projection(root)

        self.assertFalse(projection["ok"], projection)
        self.assertTrue(projection["skipped"])
        self.assertEqual(projection["classification"], "current_pointer_current_contract_invalid")
        self.assertFalse(projection["current_run_can_continue"])
        self.assertIn("active_run_id", projection["current_findings"][0]["legacy_aliases_rejected"])


if __name__ == "__main__":
    unittest.main()
