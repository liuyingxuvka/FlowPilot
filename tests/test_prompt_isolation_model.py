from __future__ import annotations

import json
import sys
import unittest
from dataclasses import fields
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import prompt_isolation_model as model  # noqa: E402
import run_prompt_isolation_checks as runner  # noqa: E402


class PromptIsolationModelTests(unittest.TestCase):
    def test_flowguard_step_keeps_input_state_output_contract(self) -> None:
        results = list(model.PromptIsolationStep().apply(model.Tick(), model.initial_state()))

        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0].output, model.Action)
        self.assertIsInstance(results[0].new_state, model.State)
        self.assertEqual(results[0].label, "bootloader_router_loaded")

    def test_material_specific_state_family_is_retired(self) -> None:
        state_fields = {field.name for field in fields(model.State)}
        retired = sorted(
            name for name in state_fields if "material" in name or "research" in name
        )

        self.assertEqual(retired, [])

    def test_user_intake_progresses_directly_to_product_architecture(self) -> None:
        safe = runner.explore_safe_graph()
        scenarios = runner.check_scenarios(safe)
        progress = runner.check_progress(safe)

        self.assertTrue(safe["ok"])
        self.assertTrue(scenarios["ok"])
        self.assertTrue(progress["ok"])
        self.assertEqual(safe["retired_special_resource_labels"], [])
        self.assertEqual(progress["nonterminal_without_completion_path"], [])

    def test_hazards_cover_direct_architecture_gate_without_old_material_family(self) -> None:
        hazards = model.hazard_states()

        self.assertIn("product_architecture_before_full_user_intake", hazards)
        self.assertFalse(
            [name for name in hazards if "material" in name or "research" in name]
        )
        for name, state in hazards.items():
            with self.subTest(name=name):
                self.assertTrue(model.invariant_failures(state))

    def test_canonical_result_records_scenario_progress_and_hazard_checks(self) -> None:
        result = json.loads(
            (ROOT / "simulations" / "prompt_isolation_results.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(result["ok"])
        self.assertTrue(result["scenario_checks"]["ok"])
        self.assertTrue(result["progress_checks"]["ok"])
        self.assertTrue(result["hazard_checks"]["ok"])


if __name__ == "__main__":
    unittest.main()
