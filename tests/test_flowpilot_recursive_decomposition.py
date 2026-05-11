from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_recursive_decomposition_model as model  # noqa: E402
import run_flowpilot_recursive_decomposition_checks as runner  # noqa: E402


class FlowPilotRecursiveDecompositionTests(unittest.TestCase):
    def test_recursive_decomposition_model_rejects_all_declared_hazards(self) -> None:
        result = runner.run_checks()
        self.assertTrue(result["ok"], json.dumps(result, indent=2, sort_keys=True))

        hazards = result["hazard_checks"]["hazards"]
        for scenario in model.NEGATIVE_SCENARIOS:
            self.assertTrue(hazards[scenario]["detected"], scenario)
        self.assertTrue(result["intended_plan"]["ok"])
        self.assertEqual(result["safe_graph"]["accepted_scenarios"], [model.INTENDED_RECURSIVE_ROUTE])

    def test_runtime_prompts_and_templates_expose_recursive_decomposition_contracts(self) -> None:
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
        current_node_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "phases"
            / "pm_current_node_loop.md"
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
        process_card = (
            ROOT
            / "skills"
            / "flowpilot"
            / "assets"
            / "runtime_kit"
            / "cards"
            / "officers"
            / "route_process_check.md"
        ).read_text(encoding="utf-8")
        route_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "routes" / "route-001" / "flow.template.json").read_text(
                encoding="utf-8"
            )
        )
        node_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "node_acceptance_plan.template.json").read_text(encoding="utf-8")
        )
        frontier_template = json.loads(
            (ROOT / "templates" / "flowpilot" / "execution_frontier.template.json").read_text(encoding="utf-8")
        )

        self.assertIn("full_route_tree", route_card)
        self.assertIn("display_depth", route_card)
        self.assertIn("leaf_readiness_gate", route_card)
        self.assertIn("over-decomposition", route_review_card)
        self.assertIn("under-decomposition", route_review_card)
        self.assertIn("parent/module node", current_node_card)
        self.assertIn("leaf_readiness_gate", node_plan_card)
        self.assertIn("parent backward review", process_card)

        self.assertTrue(route_template["decomposition_policy"]["recursive_decomposition_allowed"])
        self.assertTrue(route_template["decomposition_policy"]["fixed_two_layer_cap_forbidden"])
        self.assertEqual(route_template["display_plan"]["display_depth"], 2)
        self.assertIn("leaf_readiness_gate", route_template["nodes"][0])
        self.assertIn("leaf_readiness_gate", node_template)
        self.assertIn("active_path", frontier_template)
        self.assertIn("hidden_leaf_progress", frontier_template["user_flow_diagram"])


if __name__ == "__main__":
    unittest.main()
