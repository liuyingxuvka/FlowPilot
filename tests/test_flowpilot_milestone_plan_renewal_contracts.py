from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills" / "flowpilot" / "assets"
CORE_RUNTIME = ASSETS / "flowpilot_core_runtime"
if str(ASSETS) not in sys.path:
    sys.path.insert(0, str(ASSETS))
if str(CORE_RUNTIME) not in sys.path:
    sys.path.insert(0, str(CORE_RUNTIME))

packet_result_contracts = importlib.import_module("packet_result_contracts")
packet_stage_evidence_matrix = importlib.import_module("packet_stage_evidence_matrix")
review_window_contracts = importlib.import_module("review_window_contracts")


class FlowPilotMilestonePlanRenewalContractTests(unittest.TestCase):
    def test_nested_pm_disposition_keeps_the_base_lightweight_contract(self) -> None:
        family_id = "pm_disposition.node_pm_disposition"

        self.assertEqual(
            packet_result_contracts.required_fields_for_family(family_id),
            ("decision", "reason", "acceptance_item_disposition"),
        )
        base = packet_result_contracts.effective_result_contract_for_family(family_id)
        self.assertNotIn("milestone_audit", base["required_fields"])
        self.assertNotIn("remaining_route_plan", base["required_fields"])
        self.assertNotIn("milestone_audit", base["minimal_valid_shape"])
        self.assertNotIn("remaining_route_plan", base["minimal_valid_shape"])

    def test_milestone_profile_projects_complete_dynamic_contract_and_shape(self) -> None:
        family_id = "pm_disposition.node_pm_disposition"
        profile_id = (
            packet_stage_evidence_matrix.MILESTONE_PLAN_RENEWAL_RESULT_CONTRACT_PROFILE_ID
        )
        contract = packet_result_contracts.effective_result_contract_for_family(
            family_id,
            result_contract_profile_ids=(profile_id,),
            result_contract_profile_bindings={
                profile_id: {
                    "current_milestone_evidence_refs": ["result-current-accepted-node"],
                    "remaining_acceptance_item_ids": ["acc-next"],
                }
            },
        )

        self.assertIn("milestone_audit", contract["required_fields"])
        self.assertIn("remaining_route_plan", contract["required_fields"])
        for field_path in (
            "milestone_audit.completed[]",
            "milestone_audit.completed[].outcome",
            "milestone_audit.completed[].evidence_refs[]",
            "milestone_audit.deviations",
            "milestone_audit.remaining",
            "milestone_audit.prior_plan_assessment",
            "milestone_audit.replan_rationale",
            "remaining_route_plan.schema_version",
            "remaining_route_plan.nodes",
        ):
            self.assertIn(field_path, contract["required_child_fields"])
        for field_path in (
            "milestone_audit.completed",
            "milestone_audit.completed[].evidence_refs",
            "milestone_audit.deviations",
            "milestone_audit.remaining",
            "remaining_route_plan.nodes",
        ):
            self.assertIn(field_path, contract["explicit_array_fields"])

        shape = contract["minimal_valid_shape"]
        self.assertEqual(
            shape["milestone_audit"]["completed"][0]["evidence_refs"],
            ["result-current-accepted-node"],
        )
        self.assertEqual(
            shape["remaining_route_plan"]["schema_version"],
            packet_result_contracts.ROUTE_PLAN_SCHEMA_VERSION,
        )
        self.assertEqual(
            shape["remaining_route_plan"]["nodes"][0]["acceptance_item_ids"],
            ["acc-next"],
        )
        self.assertTrue(
            shape["remaining_route_plan"]["nodes"][0]["acceptance_criteria"]
        )
        self.assertTrue(
            shape["remaining_route_plan"]["nodes"][0]["validation_checks"]
        )
        self.assertEqual(
            shape["remaining_route_plan"]["nodes"][0]["required_outputs"],
            [],
        )
        self.assertEqual(
            shape["remaining_route_plan"]["nodes"][0]["deliverable_checks"],
            [],
        )

    def test_terminal_profile_shape_keeps_explicit_empty_remaining_surfaces(self) -> None:
        profile_id = (
            packet_stage_evidence_matrix.MILESTONE_PLAN_RENEWAL_RESULT_CONTRACT_PROFILE_ID
        )
        contract = packet_result_contracts.effective_result_contract_for_family(
            "pm_disposition.node_pm_disposition",
            result_contract_profile_ids=(profile_id,),
            result_contract_profile_bindings={
                profile_id: {
                    "current_milestone_evidence_refs": ["result-current-final-node"],
                    "remaining_acceptance_item_ids": [],
                    "terminal_remaining_plan": True,
                }
            },
        )

        shape = contract["minimal_valid_shape"]
        self.assertEqual(shape["milestone_audit"]["remaining"], [])
        self.assertEqual(shape["remaining_route_plan"]["nodes"], [])
        self.assertEqual(shape["milestone_audit"]["deviations"], [])

    def test_static_success_surface_allows_milestone_branch_fields(self) -> None:
        family_id = "pm_disposition.node_pm_disposition"
        allowed = packet_result_contracts.fake_ai_success_fields_for_family(family_id)
        self.assertIn("milestone_audit", allowed)
        self.assertIn("remaining_route_plan", allowed)

        payload = {
            **packet_result_contracts.minimal_valid_shape_for_family(family_id),
            **packet_result_contracts.milestone_plan_renewal_minimal_shape(),
        }
        self.assertEqual(
            packet_result_contracts.undeclared_success_fields_for_family(
                family_id,
                payload,
            ),
            (),
        )

    def test_branch_shapes_distinguish_nested_and_top_level_acceptance(self) -> None:
        branches = packet_result_contracts.branch_valid_shapes_for_family(
            "pm_disposition.node_pm_disposition"
        )
        nested = branches["decision=accept,nested_child"]
        milestone = branches["decision=accept,top_level_milestone"]

        self.assertNotIn("milestone_audit", nested)
        self.assertNotIn("remaining_route_plan", nested)
        self.assertIn("milestone_audit", milestone)
        self.assertIn("remaining_route_plan", milestone)

    def test_pm_flowguard_reviewer_challenges_the_whole_renewal_claim(self) -> None:
        rule = review_window_contracts.review_flow_stage_challenge_rule(
            "pm_flowguard_acceptance_review"
        ).lower()

        for phrase in (
            "completed outcomes",
            "current evidence",
            "deviations",
            "remaining goal gaps",
            "prior remaining plan",
            "replan rationale",
            "accepted final user goal",
            "unchanged route is allowed",
            "never demand artificial plan churn",
            "first remaining node",
            "execution-ready",
            "nested child disposition",
        ):
            self.assertIn(phrase, rule)

        row = review_window_contracts.review_flow_row(
            "pm_flowguard_acceptance_review"
        )
        self.assertIn(
            "structural_pm_decision_under_review",
            row["required_read_purposes"],
        )
        self.assertIn(
            "structural_pm_decision_result",
            row["required_material_classes"],
        )


if __name__ == "__main__":
    unittest.main()
