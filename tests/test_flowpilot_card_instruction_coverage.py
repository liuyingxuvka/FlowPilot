from __future__ import annotations

import json
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
        packet_prompts = model.collect_packet_prompt_facts(ROOT)
        state = model.State()
        steps = 0

        while state.status == "checking":
            transitions = tuple(model.next_safe_states(state, cards, router_facts, packet_prompts))
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

    def test_hazard_packet_prompts_are_rejected(self) -> None:
        for name, packet_prompts in model.hazard_packet_prompts().items():
            with self.subTest(name=name):
                self.assertTrue(model.packet_prompt_failures(packet_prompts))

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

    def test_worker_and_officer_packets_carry_soft_pm_note_guidance(self) -> None:
        guidance_paths = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_material_scan.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_current_node_loop.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_research_package.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_officer_request_report_loop.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_research_report.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/process_flowguard_officer.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md",
            ROOT / "templates/flowpilot/packets/packet_body.template.md",
            ROOT / "templates/flowpilot/packets/result_body.template.md",
        ]
        for path in guidance_paths:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8")
                lowered = text.lower()
                self.assertIn("pm note", lowered)
                self.assertIn("in-scope quality choice", lowered)
                self.assertIn("pm consideration", lowered)
                self.assertIn("decision-support", lowered)

        reviewer_card = (
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/reviewer/worker_result_review.md"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("pm note", reviewer_card)

        contract_text = (
            ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
        ).read_text(encoding="utf-8").lower()
        self.assertNotIn("pm note", contract_text)

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

    def test_pm_suggestion_disposition_guidance_is_unified_but_role_scoped(self) -> None:
        pm_card = (
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md"
        ).read_text(encoding="utf-8").lower()
        for required in (
            "pm_suggestion_ledger.jsonl",
            "flowpilot.pm_suggestion_item.v1",
            "current_gate_blocker",
            "defer_to_named_node",
            "reject_with_reason",
            "waive_with_authority",
            "impact triage",
            "smallest sufficient process/product",
            "flowguard modeling path",
            "no pending dispositions",
        ):
            self.assertIn(required, pm_card)

        suggestion_template = json.loads(
            (
                ROOT / "templates/flowpilot/pm_suggestion_ledger_entry.template.json"
            ).read_text(encoding="utf-8")
        )
        self.assertIn("impact_triage", suggestion_template)
        self.assertIn("impact_level", suggestion_template["impact_triage"])
        self.assertIn("flowguard_considered", suggestion_template["impact_triage"])
        self.assertIn("flowguard_decision", suggestion_template["impact_triage"])

        worker_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_research_report.md",
        ]
        for path in worker_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("pm suggestion items", text)
                self.assertIn("flowpilot.pm_suggestion_item.v1", text)
                self.assertIn("advisory only", text)
                self.assertIn("must not use `current_gate_blocker`", text)

        officer_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/process_flowguard_officer.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md",
        ]
        for path in officer_cards:
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("pm suggestion items", text)
                self.assertIn("formal model-gate", text)
                self.assertIn("current_gate_blocker", text)

        for path in (ROOT / "skills/flowpilot/assets/runtime_kit/cards/reviewer").glob("*.md"):
            with self.subTest(path=path.name):
                text = path.read_text(encoding="utf-8").lower()
                self.assertIn("flowpilot.pm_suggestion_item.v1", text)
                self.assertIn("minimum standard", text)

        packet_template = (
            ROOT / "templates/flowpilot/packets/packet_body.template.md"
        ).read_text(encoding="utf-8").lower()
        result_template = (
            ROOT / "templates/flowpilot/packets/result_body.template.md"
        ).read_text(encoding="utf-8").lower()
        contract_text = (
            ROOT / "skills/flowpilot/assets/runtime_kit/contracts/contract_index.json"
        ).read_text(encoding="utf-8").lower()
        for text in (packet_template, result_template, contract_text):
            self.assertIn("pm suggestion", text)
            self.assertIn("pm_suggestion", text)

    def test_packet_open_success_requires_work_or_existing_exit(self) -> None:
        def normalized(path: Path) -> str:
            return " ".join(path.read_text(encoding="utf-8").lower().split())

        packet_runtime_text = normalized(ROOT / "skills/flowpilot/assets/packet_runtime.py")
        packet_template = normalized(ROOT / "templates/flowpilot/packets/packet_body.template.md")
        pm_card = normalized(ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/project_manager.md")
        pm_startup_intake_card = ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_intake.md"
        pm_verified_open_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_startup_activation.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/phases/pm_review_repair.md",
        ]
        ordinary_role_cards = [
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_a.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_b.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/worker_research_report.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/human_like_reviewer.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/process_flowguard_officer.md",
            ROOT / "skills/flowpilot/assets/runtime_kit/cards/roles/product_flowguard_officer.md",
        ]

        for text in (packet_runtime_text, packet_template, pm_card):
            self.assertIn("successful", text)
            self.assertIn("open-packet", text)
            self.assertIn("do not wait for another relay", text)
            self.assertIn("pm_startup_repair_request", text)
            self.assertIn("pm_startup_protocol_dead_end", text)
            self.assertIn("pm_control_blocker_repair_decision", text)
            self.assertIn("ordinary blocker back to pm", text)

        intake_text = normalized(pm_startup_intake_card)
        self.assertIn("do not run `open-packet`", intake_text)
        self.assertIn("full `user_intake` body remains router-held until pm approves startup activation", intake_text)
        self.assertIn("ordinary blocker back to pm", intake_text)

        for path in pm_verified_open_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("verified open", text)
                self.assertIn("controller relay", text)
                self.assertIn("ordinary blocker back to pm", text)

        for path in ordinary_role_cards:
            with self.subTest(path=path.name):
                text = normalized(path)
                self.assertIn("successful packet-open session is sufficient authority", text)
                self.assertIn("do not wait for another relay", text)
                self.assertIn("formal blocker", text)
                self.assertIn("pm or router can decide", text)


if __name__ == "__main__":
    unittest.main()
