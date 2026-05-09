from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_reviewer_active_challenge_model as model  # noqa: E402
import run_flowpilot_reviewer_active_challenge_checks as runner  # noqa: E402


class FlowPilotReviewerActiveChallengeTests(unittest.TestCase):
    def test_reviewer_active_challenge_model_rejects_hazards(self) -> None:
        result = runner.run_checks()
        self.assertTrue(result["ok"], json.dumps(result, indent=2, sort_keys=True))

        hazards = result["hazard_checks"]["hazards"]
        self.assertTrue(hazards[model.CHECKLIST_ONLY_PASS]["detected"])
        self.assertTrue(hazards[model.NO_FAILURE_HYPOTHESES]["detected"])
        self.assertTrue(hazards[model.HARD_ISSUE_DOWNGRADED_TO_RESIDUAL]["detected"])
        self.assertTrue(hazards[model.SIMPLE_REVIEW_OVERBURDENED]["detected"])

    def test_runtime_cards_templates_and_contracts_expose_independent_challenge(self) -> None:
        reviewer_core = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "roles"
            / "human_like_reviewer.md"
        ).read_text(encoding="utf-8")
        worker_review_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "worker_result_review.md"
        ).read_text(encoding="utf-8")
        packet_template = (ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md").read_text(
            encoding="utf-8"
        )
        human_review_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "human_review.template.json").read_text(encoding="utf-8")
        )
        contracts = json.loads(
            (
                ROOT
                / "skills"
                / "flowpilot"
                / "assets"
                / "runtime_kit"
                / "contracts"
                / "contract_index.json"
            ).read_text(encoding="utf-8")
        )

        for text in (
            "Reviewer Independent Challenge Gate",
            "scope_restatement",
            "explicit_and_implicit_commitments",
            "failure_hypotheses",
            "challenge_actions",
            "reroute_request",
        ):
            self.assertIn(text, reviewer_core)

        self.assertIn("independent_challenge", worker_review_card)
        self.assertIn("Reviewer Independent Challenge Context", packet_template)
        self.assertIn("independent_challenge", human_review_template)
        self.assertIn("challenge_actions", human_review_template["independent_challenge"])

        reviewer_contracts = [
            item
            for item in contracts["contracts"]
            if "human_like_reviewer" in item.get("recipient_roles", [])
            and item.get("task_family", "").startswith("reviewer.")
        ]
        self.assertTrue(reviewer_contracts)
        for contract in reviewer_contracts:
            fields = contract.get("required_body_fields", [])
            self.assertIn("independent_challenge", fields, contract["contract_id"])
            self.assertIn("independent_challenge.failure_hypotheses", fields, contract["contract_id"])
            self.assertIn("independent_challenge.challenge_actions", fields, contract["contract_id"])


if __name__ == "__main__":
    unittest.main()
