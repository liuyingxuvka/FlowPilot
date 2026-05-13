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
        self.assertTrue(hazards[model.REVIEW_PACKAGE_TREATED_AS_BOUNDARY]["detected"])
        self.assertTrue(hazards[model.NO_EVIDENCE_DISCOVERY_OR_WAIVER]["detected"])
        self.assertTrue(hazards[model.NO_FAILURE_HYPOTHESES]["detected"])
        self.assertTrue(hazards[model.HARD_ISSUE_DOWNGRADED_TO_RESIDUAL]["detected"])
        self.assertTrue(hazards[model.PM_IMPROVEMENT_SIGNAL_DROPPED]["detected"])
        self.assertTrue(hazards[model.SIMPLE_REVIEW_OVERBURDENED]["detected"])
        self.assertTrue(hazards[model.FINAL_USER_INTENT_OMITTED]["detected"])
        self.assertTrue(hazards[model.HARD_USER_INTENT_FAILURE_DOWNGRADED]["detected"])
        self.assertTrue(hazards[model.FINAL_REPLAY_LEDGER_ONLY]["detected"])
        self.assertTrue(hazards[model.USER_FACING_EVIDENCE_EXISTS_ONLY]["detected"])
        self.assertTrue(hazards[model.REVIEWER_MADE_PM_ROUTE_DECISION]["detected"])
        self.assertTrue(hazards[model.LOW_QUALITY_SUCCESS_CHALLENGE_MISSING]["detected"])
        self.assertTrue(hazards[model.EXISTENCE_ONLY_HARD_PART_EVIDENCE_ACCEPTED]["detected"])

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
        reviewer_core_flat = " ".join(reviewer_core.split())
        packet_template_flat = " ".join(packet_template.split())

        for text in (
            "Reviewer Independent Challenge Gate",
            "scope_restatement",
            "explicit_and_implicit_commitments",
            "failure_hypotheses",
            "challenge_actions",
            "reroute_request",
        ):
            self.assertIn(text, reviewer_core)
        for text in (
            "known starting evidence, not a review boundary",
            "router delivery `source_paths`",
            "Treat self-attested AI claims as claims",
            "higher-standard recommendation",
            "final-user intent",
            "product usefulness",
            "Existence evidence is not enough",
            "low-quality success",
            "thin-success hypothesis",
            "proof of depth",
            "Existence-only evidence",
        ):
            self.assertIn(text, reviewer_core_flat)

        self.assertIn("independent_challenge", worker_review_card)
        self.assertIn("final-user usefulness", worker_review_card)
        self.assertIn("file existence", worker_review_card)
        self.assertIn("Low-Quality Success Guard", worker_review_card)
        self.assertIn("Proof of Depth", worker_review_card)
        self.assertIn("Reviewer Independent Challenge Context", packet_template)
        self.assertIn("starting points, not the outer boundary", packet_template_flat)
        self.assertIn("PM decision-support recommendations", packet_template_flat)
        self.assertIn("independent_challenge", human_review_template)
        self.assertIn("challenge_actions", human_review_template["independent_challenge"])
        self.assertIn("low_quality_success_challenge", human_review_template)
        self.assertIn("proof_of_depth_actions", human_review_template["low_quality_success_challenge"])

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

    def test_reviewer_standard_challenge_stays_pm_decision_support(self) -> None:
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
        pm_core = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "roles"
            / "project_manager.md"
        ).read_text(encoding="utf-8")
        node_review = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "node_acceptance_plan_review.md"
        ).read_text(encoding="utf-8")
        route_review = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "route_challenge.md"
        ).read_text(encoding="utf-8")

        self.assertIn("You are not a second Project Manager", reviewer_core)
        self.assertIn("PM owns final route choice", reviewer_core)
        self.assertIn("decision-support", reviewer_core)
        self.assertIn("product usefulness", reviewer_core)
        self.assertIn("PM decision-support", pm_core)
        self.assertIn("final-user intent and product usefulness self-check", pm_core)
        self.assertIn("minimum sufficient path", pm_core)
        self.assertIn("high_standard_recheck", node_review)
        self.assertIn("PM-decision recommendations", node_review)
        self.assertIn("second route owner", route_review)


if __name__ == "__main__":
    unittest.main()
