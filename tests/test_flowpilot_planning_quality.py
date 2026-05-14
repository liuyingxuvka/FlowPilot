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
        self.assertTrue(hazards[model.PM_USER_INTENT_SELF_CHECK_MISSING]["detected"])
        self.assertTrue(hazards[model.PM_HIGHER_STANDARD_SELF_CHECK_MISSING]["detected"])
        self.assertTrue(hazards[model.PM_IMPROVEMENT_SCOPE_CREEP]["detected"])
        self.assertTrue(hazards[model.PM_CLOSURE_USER_OUTCOME_REPLAY_MISSING]["detected"])
        self.assertTrue(hazards[model.PM_LOW_QUALITY_REVIEW_MISSING]["detected"])
        self.assertTrue(hazards[model.PM_LOW_QUALITY_REVIEW_GENERIC]["detected"])
        self.assertTrue(hazards[model.HARD_LOW_QUALITY_RISK_NO_ROUTE_OWNER]["detected"])
        self.assertTrue(hazards[model.LOW_QUALITY_RISK_CAUSES_ROUTE_BLOAT]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_LOW_QUALITY_MAPPING]["detected"])
        self.assertTrue(hazards[model.WORK_PACKET_MISSING_LOW_QUALITY_WARNING]["detected"])
        self.assertTrue(hazards[model.PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING]["detected"])
        self.assertTrue(hazards[model.PROCESS_SUPPORT_SKILL_IGNORED]["detected"])
        self.assertTrue(hazards[model.ROLE_SKILL_BINDING_MISSING]["detected"])
        self.assertTrue(hazards[model.ROLE_SKILL_USE_SELF_ATTESTED]["detected"])

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
        child_selection_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_child_skill_selection.md"
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
        product_architecture_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_product_architecture.md"
        ).read_text(encoding="utf-8")
        final_ledger_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_final_ledger.md"
        ).read_text(encoding="utf-8")
        closure_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_closure.md"
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
        product_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "product_function_architecture.template.json").read_text(
                encoding="utf-8"
            )
        )
        pm_selection_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "pm_child_skill_selection.template.json").read_text(
                encoding="utf-8"
            )
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
        self.assertIn("PM user-intent self-check", route_card)
        self.assertIn("product usefulness failures", route_card)
        self.assertIn("PM low-quality-success ownership check", route_card)
        self.assertIn("unjustified route bloat", route_card)
        self.assertIn("deliverable_support", child_selection_card)
        self.assertIn("process_support", child_selection_card)
        self.assertIn("skill_standard_contracts", child_manifest_card)
        self.assertIn("role_skill_use_bindings", child_manifest_card)
        for category in model.STANDARD_FIELDS:
            self.assertIn(category, child_manifest_card)
        self.assertIn("skill_standard_projection", node_plan_card)
        self.assertIn("active_child_skill_bindings", node_plan_card)
        self.assertIn("role_skill_use_bindings", node_plan_card)
        self.assertIn("Role Skill Use Evidence", node_plan_card)
        self.assertIn("work_packet_projection", node_plan_card)
        self.assertIn("final-user intent and product usefulness self-check", node_plan_card)
        self.assertIn("nonessential improvement", node_plan_card)
        self.assertIn("low-quality-success self-check", node_plan_card)
        self.assertIn("proof of depth", node_plan_card)
        self.assertIn("final-user intent and product usefulness assumptions", product_architecture_card)
        self.assertIn("low-quality-success review", product_architecture_card)
        self.assertIn("thin-success shortcuts", product_architecture_card)
        self.assertIn("final-user intent and delivered-product usefulness claims", final_ledger_card)
        self.assertIn("low-quality-success risks", final_ledger_card)
        self.assertIn("final_user_outcome_replay", closure_card)
        self.assertIn("hard low-quality-success risks", closure_card)
        self.assertIn("hard block", route_review_card)
        self.assertIn("Inherited Skill Standards", packet_template)
        self.assertIn("Active Child Skill Bindings", packet_template)
        self.assertIn("Role Skill Use Bindings", packet_template)
        self.assertIn("Low-Quality Success Guard", packet_template)
        self.assertIn("Skill Standard Result Matrix", result_template)
        self.assertIn("Child Skill Use Evidence", result_template)
        self.assertIn("Role Skill Use Evidence", result_template)
        self.assertIn("Proof of Depth", result_template)

        self.assertIn("low_quality_success_review", product_template)
        self.assertIn("proof_of_depth_required", product_template["low_quality_success_review"]["hard_parts"][0])
        self.assertIn("selection_dimensions", pm_selection_template)
        self.assertIn("process_support", pm_selection_template["selection_dimensions"])
        skill_decision = pm_selection_template["skill_decisions"][0]
        self.assertIn("support_dimensions", skill_decision)
        self.assertIn("role_skill_use_candidates", skill_decision)
        selected_skill = manifest_template["selected_skills"][0]
        self.assertIn("support_dimensions", selected_skill)
        self.assertIn("role_skill_use_bindings", selected_skill)
        self.assertFalse(selected_skill["role_skill_use_bindings"][0]["self_attestation_allowed"])
        self.assertIn("skill_standard_contract", selected_skill)
        standard = selected_skill["skill_standard_contract"]["standards"][0]
        self.assertIn("category", standard)
        self.assertIn("route_node_ids", standard)
        self.assertIn("work_packet_slices", standard)
        self.assertIn("reviewer_or_officer_gate_ids", standard)
        self.assertIn("expected_artifact_paths", standard)
        self.assertIn("skill_standard_projection", node_template)
        self.assertIn("active_child_skill_bindings", node_template)
        self.assertIn("role_skill_use_bindings", node_template)
        self.assertFalse(node_template["role_skill_use_bindings"][0]["self_attestation_allowed"])
        self.assertIn("work_packet_projection", node_template)
        self.assertIn("role_skill_use_binding_ids", node_template["work_packet_projection"][0])
        self.assertIn("role_skill_use_evidence_required", node_template["work_packet_projection"][0])
        self.assertIn("local_low_quality_success_risk", node_template["pm_current_node_high_standard_recheck"])
        self.assertIn(
            "proof_of_depth_required",
            node_template["pm_current_node_high_standard_recheck"]["local_low_quality_success_risk"],
        )

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
        self.assertIn(
            "Role Skill Use Evidence",
            worker_contract["conditional_required_result_body_sections"][
                "source_packet_declares_role_skill_use_bindings"
            ],
        )
        role_work_contract = next(
            item
            for item in contracts["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.pm_role_work_result.v1"
        )
        self.assertIn(
            "Role Skill Use Evidence",
            role_work_contract["conditional_required_result_body_sections"][
                "source_request_declares_role_skill_use_bindings"
            ],
        )


if __name__ == "__main__":
    unittest.main()
