from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import card_instruction_coverage_model as model  # noqa: E402


class FlowPilotCardInstructionCoverageTests(unittest.TestCase):
    def test_actual_runtime_cards_have_router_return_instruction_coverage(self) -> None:
        cards = model.collect_card_facts(ROOT)
        router_facts = model.collect_router_facts(ROOT)
        state = model.State()
        steps = 0

        while state.status == "checking":
            transitions = tuple(model.next_safe_states(state, cards, router_facts))
            self.assertEqual(len(transitions), 1)
            state = transitions[0].state
            steps += 1
            self.assertLessEqual(steps, len(cards) + 2)

        self.assertEqual(state.status, "complete", state.failures)
        self.assertEqual(len(state.checked), len(cards))
        self.assertFalse(model.invariant_failures(state))

    def test_hazard_cards_are_rejected(self) -> None:
        for name, card in model.hazard_cards().items():
            with self.subTest(name=name):
                self.assertTrue(model.card_failures(card))


if __name__ == "__main__":
    unittest.main()
