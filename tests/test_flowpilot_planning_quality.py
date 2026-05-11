from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_planning_quality_model as model  # noqa: E402
import run_flowpilot_planning_quality_checks as runner  # noqa: E402


class FlowPilotPlanningQualityTests(unittest.TestCase):
    def test_planning_quality_model_rejects_hazards(self) -> None:
        result = runner.run_checks()
        self.assertTrue(result["ok"], json.dumps(result, indent=2, sort_keys=True))

        hazards = result["hazard_checks"]["hazards"]
        self.assertTrue(hazards[model.UI_WITHOUT_PROFILE]["detected"])
        self.assertTrue(hazards[model.SKILL_SELECTED_NO_CONTRACT]["detected"])
        self.assertTrue(hazards[model.REVIEWER_PASSES_HARD_BLINDSPOT]["detected"])
        self.assertTrue(hazards[model.SIMPLE_TASK_OVERTEMPLATED]["detected"])

    def test_runtime_cards_and_templates_expose_planning_quality_contracts(self) -> None:
        route_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_route_skeleton.md"
        ).read_text(encoding="utf-8")
        child_manifest_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_child_skill_gate_manifest.md"
        ).read_text(encoding="utf-8")
        node_plan_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_node_acceptance_plan.md"
        ).read_text(encoding="utf-8")
        route_review_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "route_challenge.md"
        ).read_text(encoding="utf-8")
        packet_template = (ROOT / "templates" / "flowpilot" / "packets" / "packet_body.template.md").read_text(
            encoding="utf-8"
        )
        result_template = (ROOT / "templates" / "flowpilot" / "packets" / "result_body.template.md").read_text(
            encoding="utf-8"
        )
        manifest_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "child_skill_gate_manifest.template.json").read_text(
                encoding="utf-8"
            )
        )
        node_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "node_acceptance_plan.template.json").read_text(
                encoding="utf-8"
            )
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

        self.assertIn("planning_profile", route_card)
        self.assertIn("interactive_software_ui_product", route_card)
        self.assertIn("skill_standard_contracts", child_manifest_card)
        for category in model.STANDARD_FIELDS:
            self.assertIn(category, child_manifest_card)
        self.assertIn("skill_standard_projection", node_plan_card)
        self.assertIn("active_child_skill_bindings", node_plan_card)
        self.assertIn("work_packet_projection", node_plan_card)
        self.assertIn("hard block", route_review_card)
        self.assertIn("Inherited Skill Standards", packet_template)
        self.assertIn("Active Child Skill Bindings", packet_template)
        self.assertIn("Skill Standard Result Matrix", result_template)
        self.assertIn("Child Skill Use Evidence", result_template)

        selected_skill = manifest_template["selected_skills"][0]
        self.assertIn("skill_standard_contract", selected_skill)
        standard = selected_skill["skill_standard_contract"]["standards"][0]
        self.assertIn("category", standard)
        self.assertIn("route_node_ids", standard)
        self.assertIn("work_packet_slices", standard)
        self.assertIn("reviewer_or_officer_gate_ids", standard)
        self.assertIn("expected_artifact_paths", standard)
        self.assertIn("skill_standard_projection", node_template)
        self.assertIn("active_child_skill_bindings", node_template)
        self.assertIn("work_packet_projection", node_template)

        worker_contract = next(
            item
            for item in contracts["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.worker_current_node_result.v1"
        )
        self.assertIn("conditional_required_result_body_sections", worker_contract)
        self.assertIn(
            "Skill Standard Result Matrix",
            worker_contract["conditional_required_result_body_sections"][
                "source_packet_declares_inherited_skill_standard_ids"
            ],
        )
        self.assertIn(
            "Child Skill Use Evidence",
            worker_contract["conditional_required_result_body_sections"][
                "source_packet_declares_active_child_skill_bindings"
            ],
        )


if __name__ == "__main__":
    unittest.main()
