from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import flowpilot_modeling_coverage_model as model  # noqa: E402
import run_flowpilot_modeling_coverage_checks as runner  # noqa: E402


class FlowPilotModelingCoverageTests(unittest.TestCase):
    def test_flowguard_model_rejects_modeling_coverage_hazards(self) -> None:
        result = runner.run_checks()
        self.assertTrue(result["ok"], json.dumps(result, indent=2, sort_keys=True))

        hazards = result["hazard_checks"]["hazards"]
        for name in model.NEGATIVE_SCENARIOS:
            with self.subTest(name=name):
                self.assertTrue(hazards[name]["detected"], hazards[name])

        self.assertEqual(
            result["safe_graph"]["accepted_scenarios"],
            [model.INTENDED_MODEL_COVERAGE],
        )
        self.assertIn(
            model.FLOWGUARD_OPTIONAL_CHILD_SKILL,
            result["safe_graph"]["rejected_scenarios"],
        )
        self.assertIn(
            "startup FlowGuard capability snapshot",
            result["model_plan"]["core_order"],
        )

    def test_runtime_cards_expose_pm_owned_modeling_plan_sequence(self) -> None:
        cards_root = ROOT / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards"
        product_architecture = (cards_root / "phases" / "pm_product_architecture.md").read_text(
            encoding="utf-8"
        )
        product_officer = (cards_root / "officers" / "product_architecture_modelability.md").read_text(
            encoding="utf-8"
        )
        product_decision = (cards_root / "phases" / "pm_product_behavior_model_decision.md").read_text(
            encoding="utf-8"
        )
        child_manifest = (cards_root / "phases" / "pm_child_skill_gate_manifest.md").read_text(
            encoding="utf-8"
        )
        route_skeleton = (cards_root / "phases" / "pm_route_skeleton.md").read_text(
            encoding="utf-8"
        )
        process_officer = (cards_root / "officers" / "route_process_check.md").read_text(
            encoding="utf-8"
        )
        final_ledger = (cards_root / "phases" / "pm_final_ledger.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("flowguard/capability_snapshot.json", product_architecture)
        self.assertIn("FlowGuard is a required foundation", product_architecture)
        self.assertIn("flowguard/product_modeling_plan.json", product_architecture)
        self.assertIn("product model family", product_architecture)
        self.assertIn("product_model_family_coverage", product_officer)
        self.assertIn("single", product_officer)
        self.assertIn("over-collapsed model", product_officer)
        self.assertIn("product_model_family_coverage_review", product_decision)
        self.assertIn("ordinary child skills only", child_manifest)
        self.assertIn("after PM has accepted", child_manifest)
        self.assertIn("manifest as a substitute", child_manifest)
        self.assertIn("flowguard/process_modeling_plan.json", route_skeleton)
        self.assertIn("child-skill conformance", route_skeleton)
        self.assertIn("process_model_family_coverage", process_officer)
        self.assertIn("Manifest-only coverage is not enough", process_officer)
        self.assertIn("FlowGuard modeling coverage closure", final_ledger)
        self.assertIn("unresolved model-family count", final_ledger)

    def test_templates_capture_snapshot_plans_and_manifest_boundary(self) -> None:
        templates = ROOT / "templates" / "flowpilot"
        snapshot = json.loads(
            (templates / "flowguard_capability_snapshot.template.json").read_text(
                encoding="utf-8"
            )
        )
        product_plan = json.loads(
            (templates / "product_modeling_plan.template.json").read_text(
                encoding="utf-8"
            )
        )
        process_plan = json.loads(
            (templates / "process_modeling_plan.template.json").read_text(
                encoding="utf-8"
            )
        )
        manifest = json.loads(
            (templates / "child_skill_gate_manifest.template.json").read_text(
                encoding="utf-8"
            )
        )
        modeling_request = json.loads(
            (templates / "flowguard_modeling_request.template.json").read_text(
                encoding="utf-8"
            )
        )
        modeling_report = json.loads(
            (templates / "flowguard_modeling_report.template.json").read_text(
                encoding="utf-8"
            )
        )
        final_ledger = json.loads(
            (templates / "final_route_wide_gate_ledger.template.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertTrue(snapshot["policy"]["flowguard_is_required_foundation"])
        self.assertFalse(snapshot["policy"]["ordinary_child_skill"])
        self.assertEqual(snapshot["generated_by_role_key"], "router")
        self.assertFalse(snapshot["portable_resolution"]["hardcoded_user_path_required"])
        self.assertEqual(snapshot["portable_resolution"]["generator"], "flowpilot_router_startup_seed")
        self.assertIn("skill_routes", snapshot)
        self.assertTrue(product_plan["flowguard_foundation_confirmed"] is False)
        self.assertIn("product_model_families", product_plan)
        self.assertIn("merged_families", product_plan)
        self.assertIn("process_model_families", process_plan)
        self.assertIn("accepted_product_model_decision", process_plan["source_paths"])
        self.assertFalse(manifest["manifest_can_close_model_family_coverage"])
        self.assertIn("model_family_projection", manifest)
        self.assertTrue(
            modeling_request["model_family_scope"][
                "single_model_allowed_only_with_pm_merge_reason"
            ]
        )
        self.assertIn("model_family_coverage", modeling_report)
        self.assertIn("flowguard_modeling_coverage_closure", final_ledger)
        self.assertTrue(
            final_ledger["flowguard_modeling_coverage_closure"][
                "completion_blocked_when_unresolved"
            ]
        )


if __name__ == "__main__":
    unittest.main()
