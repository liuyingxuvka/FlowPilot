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

    def test_pm_worker_packet_cards_carry_lightweight_dispatch_guidance(self) -> None:
        worker_packet_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md",
        ]
        for path in worker_packet_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Before assigning a worker packet, consider worker balance and packet shape.", text)
                self.assertIn("worker opportunities roughly balanced across the current run", text)
                self.assertIn("bounded separate packets for", text)
                self.assertIn("without overlapping files", text)
                self.assertIn("evidence duties, or review ownership", text)
                lowered = text.lower()
                self.assertNotIn("default `worker_a`", lowered)
                self.assertNotIn("default worker_a", lowered)
                self.assertNotIn("do not default", lowered)

        repair_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/events/pm_reviewer_blocked.md",
        ]
        for path in repair_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("same worker who produced the blocked result", text)
                self.assertIn("repair keeps local context", text)
                self.assertIn("fundamental", text)
                self.assertIn("separable new work", text)


if __name__ == "__main__":
    unittest.main()
