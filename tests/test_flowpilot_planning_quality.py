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
        self.assertTrue(hazards[model.PM_SHALLOW_COMPLETION_TRAPS_MISSING]["detected"])
        self.assertTrue(hazards[model.PRACTICAL_OUTCOME_DESIGN_ONLY_ROUTE]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_LOW_QUALITY_MAPPING]["detected"])
        self.assertTrue(hazards[model.WORK_PACKET_MISSING_LOW_QUALITY_WARNING]["detected"])
        self.assertTrue(hazards[model.WORKER_PACKET_MISSING_IN_SCOPE_REPAIR]["detected"])
        self.assertTrue(hazards[model.WORKER_PACKET_REPAIRS_OUT_OF_SCOPE]["detected"])
        self.assertTrue(hazards[model.EVIDENCE_PACKET_REPAIRS_TARGET_ARTIFACT]["detected"])
        self.assertTrue(hazards[model.FLOWGUARD_OPERATOR_PACKET_REPAIRS_TARGET_ARTIFACT]["detected"])
        self.assertTrue(hazards[model.REVIEWER_PROMPT_GRANTS_DIRECT_REPAIR]["detected"])
        self.assertTrue(hazards[model.GENERIC_TEMPLATE_USES_BLANKET_REPAIR]["detected"])
        self.assertTrue(hazards[model.PM_STRUCTURE_CONVERGENCE_REVIEW_MISSING]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_STRUCTURE_HYGIENE_EXPECTATION]["detected"])
        self.assertTrue(hazards[model.WORK_PACKET_MISSING_STRUCTURE_HYGIENE_DELTA]["detected"])
        self.assertTrue(hazards[model.WORKER_RESULT_LEAVES_UNOWNED_FALLBACK]["detected"])
        self.assertTrue(hazards[model.REPAIR_LEAVES_COMPAT_BRANCH]["detected"])
        self.assertTrue(hazards[model.FINAL_LEDGER_STRUCTURE_DEBT_UNRESOLVED]["detected"])
        self.assertTrue(hazards[model.PM_CLOSURE_LOW_QUALITY_RISK_DISPOSITION_MISSING]["detected"])
        self.assertTrue(hazards[model.PM_CLOSURE_SHALLOW_COMPLETION_TRAPS_UNRESOLVED]["detected"])
        self.assertTrue(hazards[model.PROCESS_SUPPORT_SKILL_IGNORED]["detected"])
        self.assertTrue(hazards[model.ROLE_SKILL_BINDING_MISSING]["detected"])
        self.assertTrue(hazards[model.ROLE_SKILL_USE_SELF_ATTESTED]["detected"])
        self.assertTrue(hazards[model.PM_IMPLEMENTATION_INTENT_MISSING]["detected"])
        self.assertTrue(hazards[model.TARGET_REALIZATION_MODEL_MISSING]["detected"])
        self.assertTrue(hazards[model.TARGET_REALIZATION_MODEL_IGNORES_PM_INTENT]["detected"])
        self.assertTrue(hazards[model.PM_TARGET_REALIZATION_ACCEPTS_DOWNGRADE]["detected"])
        self.assertTrue(hazards[model.REVIEWER_IMPLEMENTATION_INTENT_ALIGNMENT_MISSING]["detected"])
        self.assertTrue(hazards[model.ROUTE_MISSING_REALIZATION_OBLIGATIONS]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_REALIZATION_OBLIGATIONS]["detected"])
        self.assertTrue(hazards[model.WORK_PACKET_MISSING_REALIZATION_OBLIGATIONS]["detected"])
        self.assertTrue(hazards[model.FINAL_LEDGER_REALIZATION_OBLIGATIONS_UNRESOLVED]["detected"])
        self.assertTrue(hazards[model.ACCEPTANCE_ITEM_REGISTRY_MISSING]["detected"])
        self.assertTrue(hazards[model.ACCEPTANCE_ITEM_NO_ROUTE_OWNER]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_ACCEPTANCE_ITEM_PROJECTION]["detected"])
        self.assertTrue(hazards[model.WORK_PACKET_MISSING_ACCEPTANCE_ITEM_MATRIX]["detected"])
        self.assertTrue(hazards[model.FINAL_LEDGER_ACCEPTANCE_ITEM_UNRESOLVED]["detected"])
        self.assertTrue(hazards[model.STARTUP_QUALITY_POSTURE_MISSING]["detected"])
        self.assertTrue(hazards[model.PRODUCT_ARCHITECTURE_IGNORES_STARTUP_QUALITY]["detected"])
        self.assertTrue(hazards[model.ROUTE_QUALITY_POSTURE_DROPPED]["detected"])
        self.assertTrue(hazards[model.PACKET_QUALITY_FLOOR_DROPPED]["detected"])
        self.assertTrue(hazards[model.PRODUCT_ARCHITECTURE_MISSING_SYSTEM_INTEGRATION_INTENT]["detected"])
        self.assertTrue(hazards[model.ROUTE_CONVERGENCE_MISSING_COMPOSITION_REVIEW]["detected"])
        self.assertTrue(hazards[model.NODE_PLAN_MISSING_INTEGRATION_TOUCHPOINT]["detected"])
        self.assertTrue(hazards[model.PM_ABSORBS_LOCAL_RESULT_WITH_BROKEN_INTEGRATION]["detected"])
        self.assertTrue(hazards[model.PARENT_REPLAY_PASSES_SCATTERED_CHILD_OUTPUTS]["detected"])
        self.assertTrue(hazards[model.FINAL_LEDGER_PASSES_NODE_LEVEL_ONLY_COMPOSITION]["detected"])
        self.assertTrue(hazards[model.SCATTERED_OUTPUT_NOT_ROUTED_TO_MODEL_MISS]["detected"])

    def test_runtime_cards_and_templates_expose_planning_quality_contracts(self) -> None:
        startup_intake_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_startup_intake.md"
        ).read_text(encoding="utf-8")
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
        pm_core_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "roles"
            / "project_manager.md"
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
        evidence_quality_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_evidence_quality_package.md"
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
        node_plan_review_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "node_acceptance_plan_review.md"
        ).read_text(encoding="utf-8")
        worker_result_review_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "reviewer"
            / "worker_result_review.md"
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
        startup_decision_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "pm_startup_intake_decision.template.json").read_text(
                encoding="utf-8"
            )
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
        route_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "routes" / "route-001" / "flow.template.json").read_text(
                encoding="utf-8"
            )
        )
        final_ledger_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "final_route_wide_gate_ledger.template.json").read_text(
                encoding="utf-8"
            )
        )
        closure_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "terminal_closure_suite.template.json").read_text(
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
        startup_intake_card_flat = " ".join(startup_intake_card.split())

        self.assertIn("normal high-quality current-run project work", startup_intake_card_flat)
        self.assertIn("short startup request does not lower", startup_intake_card)
        self.assertIn("highest reasonable product target", startup_intake_card)
        self.assertIn("release carries normal high-quality current-run work", startup_decision_template["notes"])
        self.assertNotIn("startup_quality_posture", startup_decision_template)
        self.assertIn("planning_profile", route_card)
        self.assertIn("interactive_software_ui_product", route_card)
        self.assertIn("Structural convergence", pm_core_card)
        self.assertIn("system integration owner", pm_core_card)
        self.assertIn("scattered local-pass/global-incoherent output", pm_core_card)
        self.assertIn("structure_convergence_review", route_card)
        self.assertIn("system_integration_intent", route_card)
        self.assertIn("parent/child and sibling composition", route_card)
        self.assertIn("Old artifacts", route_card)
        self.assertIn("PM user-intent self-check", route_card)
        self.assertIn("product usefulness failures", route_card)
        self.assertIn("PM low-quality-success ownership check", route_card)
        self.assertIn("unjustified route bloat", route_card)
        self.assertIn("PM shallow-completion trap list", route_card)
        self.assertIn("practical next-step evidence", route_card)
        self.assertIn("acceptance_item_registry", route_card)
        self.assertIn("acceptance_item_ids", route_card)
        self.assertIn("deliverable_support", child_selection_card)
        self.assertIn("process_support", child_selection_card)
        self.assertIn("FlowGuard satellite skills", child_selection_card)
        self.assertIn("skill_standard_contracts", child_manifest_card)
        self.assertIn("role_skill_use_bindings", child_manifest_card)
        for category in model.STANDARD_FIELDS:
            self.assertIn(category, child_manifest_card)
        self.assertIn("skill_standard_projection", node_plan_card)
        self.assertIn("active_child_skill_bindings", node_plan_card)
        self.assertIn("role_skill_use_bindings", node_plan_card)
        self.assertIn("Role Skill Use Evidence", node_plan_card)
        self.assertNotIn("work_packet_projection", node_plan_card)
        self.assertIn("acceptance_item_projection", node_plan_card)
        self.assertIn("node-owned acceptance item", node_plan_card)
        self.assertIn("final-user intent and product usefulness self-check", node_plan_card)
        self.assertIn("nonessential improvement", node_plan_card)
        self.assertIn("low-quality-success self-check", node_plan_card)
        self.assertIn("proof of depth", node_plan_card)
        self.assertIn("structure_hygiene_expectation", node_plan_card)
        self.assertIn("integration_touchpoint", node_plan_card)
        self.assertIn("not a runtime-expanded node context field", node_plan_card)
        self.assertIn("Structure Hygiene Delta", packet_template)
        self.assertIn("Structure Hygiene Delta", result_template)
        self.assertIn("Acceptance Item Projection", packet_template)
        self.assertIn("Acceptance Item Result Matrix", result_template)
        self.assertIn("high-quality current-run work within the packet boundary", packet_template)
        self.assertIn("current packet's quality floor", result_template)
        self.assertIn("acceptance_item_projection", node_plan_review_card)
        self.assertIn("structure_hygiene_expectation", node_plan_review_card)
        self.assertIn("integration_touchpoint", node_plan_review_card)
        self.assertIn("unowned fallback", worker_result_review_card)
        self.assertIn("Negative rejection evidence", worker_result_review_card)
        self.assertIn("final-user intent and product usefulness assumptions", product_architecture_card)
        self.assertIn("system_integration_intent", product_architecture_card)
        self.assertIn("startup release as the first high-quality current-run posture source", product_architecture_card)
        self.assertIn("Short or sparse startup wording is not a reason", product_architecture_card)
        self.assertIn("low-quality-success review", product_architecture_card)
        self.assertIn("acceptance_item_registry_seed", product_architecture_card)
        self.assertIn("thin-success shortcuts", product_architecture_card)
        self.assertIn("final-user intent and delivered-product usefulness claims", final_ledger_card)
        self.assertIn("acceptance item closure", final_ledger_card)
        self.assertIn("low-quality-success risks", final_ledger_card)
        self.assertIn("structure debt dispositions", final_ledger_card)
        self.assertIn("whole-output composition closure", final_ledger_card)
        self.assertIn("structure debt dispositions", evidence_quality_card)
        self.assertIn("final_user_outcome_replay", closure_card)
        self.assertIn("hard low-quality-success risks", closure_card)
        self.assertIn("zero unresolved active", closure_card)
        self.assertIn("shallow-completion traps", closure_card)
        self.assertIn("practical next step", closure_card)
        self.assertIn("structural convergence", closure_card)
        self.assertIn("hard block", route_review_card)
        self.assertIn("startup and product high-quality current-run posture", route_card)
        self.assertIn("startup and product high-quality current-run posture", route_review_card)
        self.assertIn("Inherited Skill Standards", packet_template)
        self.assertIn("Active Child Skill Bindings", packet_template)
        self.assertIn("Role Skill Use Bindings", packet_template)
        self.assertIn("Low-Quality Success Guard", packet_template)
        self.assertIn("Skill Standard Result Matrix", result_template)
        self.assertIn("Child Skill Use Evidence", result_template)
        self.assertIn("Role Skill Use Evidence", result_template)
        self.assertIn("Proof of Depth", result_template)

        self.assertIn("low_quality_success_review", product_template)
        self.assertIn("system_integration_intent", product_template)
        self.assertIn("artifact_family_integration_risks", product_template["system_integration_intent"])
        self.assertIn("acceptance_item_registry_seed", product_template["requirement_trace"])
        self.assertIn("proof_of_depth_required", product_template["low_quality_success_review"]["hard_parts"][0])
        self.assertIn(
            "short or sparse startup wording",
            product_template["high_standard_posture"]["minimum_professional_bar"],
        )
        self.assertIn(
            "startup release",
            product_template["highest_achievable_product_target"]["product_vision"],
        )
        self.assertIn("selection_dimensions", pm_selection_template)
        self.assertIn("FlowGuard satellite skills", pm_selection_template["selection_rule"])
        self.assertIn("process_support", pm_selection_template["selection_dimensions"])
        self.assertNotIn("skill_decisions", pm_selection_template)
        skill_decision = pm_selection_template["selected_skills"][0]
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
        self.assertIn("reviewer_or_flowguard_gate_ids", standard)
        self.assertIn("expected_artifact_paths", standard)
        self.assertIn("skill_standard_projection", node_template)
        self.assertIn("node_context_package", node_template)
        self.assertIn("integration_touchpoint", node_template)
        self.assertNotIn("integration_touchpoint", node_template["node_context_package"])
        self.assertIn("acceptance_item_projection", node_template["node_context_package"])
        self.assertEqual(
            set(node_template["node_context_package"]),
            {
                "purpose",
                "acceptance_criteria",
                "relevant_references",
                "known_risks",
                "acceptance_item_projection",
            },
        )
        self.assertIn("acceptance_item_registry", node_template["source_paths"])
        self.assertIn("structure_hygiene_expectation", node_template)
        self.assertIn("active_child_skill_bindings", node_template)
        self.assertIn("role_skill_use_bindings", node_template)
        self.assertFalse(node_template["role_skill_use_bindings"][0]["self_attestation_allowed"])
        self.assertNotIn("work_packet_projection", node_template)
        self.assertIn("local_low_quality_success_risk", node_template["pm_current_node_high_standard_recheck"])
        self.assertIn("no-local-hard-part", node_template["pm_current_node_high_standard_recheck"]["local_low_quality_success_risk"]["task_specific_hard_part"])
        self.assertIn(
            "proof_of_depth_required",
            node_template["pm_current_node_high_standard_recheck"]["local_low_quality_success_risk"],
        )
        self.assertIn("structure_convergence_review", route_template)
        self.assertIn("composition_review", route_template["structure_convergence_review"])
        self.assertFalse(route_template["structure_convergence_review"]["composition_review"]["flat_local_pass_route_rejected"])
        self.assertIn("acceptance_item_traceability_policy", route_template)
        self.assertIn("acceptance_item_ids", route_template["nodes"][0])
        self.assertFalse(route_template["structure_convergence_review"]["old_artifacts_may_close_current_completion"])
        self.assertIn("acceptance_item_closure", final_ledger_template)
        self.assertIn("whole_output_composition_review", final_ledger_template)
        self.assertTrue(final_ledger_template["whole_output_composition_review"]["starts_from_delivered_output"])
        self.assertIn("active_acceptance_item_count", final_ledger_template["counts"])
        self.assertIn("structure_debt_dispositions", final_ledger_template)
        self.assertIn("unresolved_structure_debt_count", final_ledger_template["counts"])
        self.assertIn("structure_debt_triage", closure_template)

        worker_contract = next(
            item
            for item in contracts["contracts"]
            if item["contract_id"] == "flowpilot.output_contract.worker_current_node_result.v1"
        )
        self.assertIn("conditional_required_result_body_sections", worker_contract)
        self.assertIn("Structure Hygiene Delta", worker_contract["required_result_body_sections"])
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
