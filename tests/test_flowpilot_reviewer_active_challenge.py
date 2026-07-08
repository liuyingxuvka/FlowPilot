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
        self.assertTrue(hazards[model.SOURCE_INTENT_DILUTION_ACCEPTED]["detected"])
        self.assertTrue(hazards[model.REVIEWER_MADE_PM_ROUTE_DECISION]["detected"])
        self.assertTrue(hazards[model.LOW_QUALITY_SUCCESS_CHALLENGE_MISSING]["detected"])
        self.assertTrue(hazards[model.EXISTENCE_ONLY_HARD_PART_EVIDENCE_ACCEPTED]["detected"])
        self.assertTrue(hazards[model.SHALLOW_COMPLETION_TRAPS_NOT_CHALLENGED]["detected"])
        self.assertTrue(hazards[model.SHALLOW_COMPLETION_TRAP_DOWNGRADED]["detected"])
        self.assertTrue(hazards[model.STRUCTURAL_ROUTE_QUALITY_FLOOR_LOSS_ACCEPTED]["detected"])

    def test_runtime_cards_templates_and_contracts_keep_reviewer_challenge_compact(self) -> None:
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
        worker_review_card_flat = " ".join(worker_review_card.split())
        packet_template_flat = " ".join(packet_template.split())

        self.assertIn("independent challenge internally", reviewer_core)
        self.assertIn("formal review result body stays on the current small contract", reviewer_core_flat)
        for text in ("pm_visible_summary", "reviewed_by_role", "findings", "blockers", "pm_suggestion_items"):
            self.assertIn(text, reviewer_core)
        for text in (
            "known starting evidence, not a review boundary",
            "router delivery `source_paths`",
            "Treat self-attested AI claims as claims",
            "higher-standard recommendation",
            "final-user intent",
            "source-intent comparison",
            "semantic dilution",
            "product usefulness",
            "Existence evidence is not enough",
            "low-quality success",
            "thin-success hypothesis",
            "proof of depth",
            "Existence-only evidence",
            "Active verification is part of your review duty",
            "Run targeted tests",
            "review-scope tests or fixtures",
        ):
            self.assertIn(text, reviewer_core_flat)

        self.assertNotIn("independent_challenge", worker_review_card)
        self.assertIn("final-user usefulness", worker_review_card_flat)
        self.assertIn("file existence", worker_review_card_flat)
        self.assertIn("source-intent", worker_review_card_flat)
        self.assertIn("current artifact", worker_review_card_flat)
        self.assertIn("Low-Quality Success Guard", worker_review_card_flat)
        self.assertIn("Proof of Depth", worker_review_card_flat)
        self.assertIn("shallow-completion traps", worker_review_card_flat)
        self.assertIn("practical next step", worker_review_card_flat)
        self.assertIn("run targeted tests", worker_review_card_flat)
        self.assertIn("review-scope tests or fixtures", worker_review_card_flat)
        self.assertIn("Reviewer Independent Challenge Context", packet_template)
        self.assertIn("starting points, not the outer boundary", packet_template_flat)
        self.assertIn("PM decision-support recommendations", packet_template_flat)
        self.assertNotIn("independent_challenge", packet_template)
        self.assertNotIn("independent_challenge", human_review_template)
        self.assertNotIn("final_artifact_hygiene_review", human_review_template)
        for field in (
            "pm_visible_summary",
            "reviewed_by_role",
            "passed",
            "findings",
            "blockers",
            "pm_suggestion_items",
            "contract_self_check",
        ):
            self.assertIn(field, human_review_template)

        reviewer_contracts = [
            item
            for item in contracts["contracts"]
            if "human_like_reviewer" in item.get("recipient_roles", [])
            and item.get("task_family", "").startswith("reviewer.")
        ]
        self.assertTrue(reviewer_contracts)
        for contract in reviewer_contracts:
            fields = contract.get("required_body_fields", [])
            if contract["contract_id"] == "flowpilot.output_contract.terminal_backward_replay_report.v1":
                self.assertEqual(
                    fields,
                    [
                        "final_artifact_refs",
                        "acceptance_item_closure",
                        "route_segment_replay",
                        "waiver_records",
                        "final_blockers",
                    ],
                )
                continue
            self.assertIn("pm_visible_summary", fields, contract["contract_id"])
            self.assertIn("reviewed_by_role", fields, contract["contract_id"])
            self.assertIn("passed", fields, contract["contract_id"])
            self.assertIn("findings", fields, contract["contract_id"])
            self.assertIn("blockers", fields, contract["contract_id"])
            self.assertIn("pm_suggestion_items", fields, contract["contract_id"])
            self.assertIn("contract_self_check", fields, contract["contract_id"])
            self.assertNotIn("independent_challenge", fields, contract["contract_id"])
            self.assertNotIn("direct_evidence_paths_checked", fields, contract["contract_id"])

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
        self.assertIn("startup and product high-quality current-run posture", route_review)
        self.assertIn("merely passable plan", route_review)


if __name__ == "__main__":
    unittest.main()
