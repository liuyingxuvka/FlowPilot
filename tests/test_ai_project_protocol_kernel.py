from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "skills" / "flowpilot" / "assets" / "ai_project_protocol"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(name)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old_module
    return module


runner = load_module(
    "ai_project_protocol_runner",
    ROOT / "simulations" / "run_ai_project_protocol_checks.py",
)
model = load_module(
    "ai_project_protocol_model_for_tests",
    ROOT / "simulations" / "ai_project_protocol_model.py",
)


class AIProjectProtocolKernelTests(unittest.TestCase):
    def test_protocol_assets_define_required_boundaries(self) -> None:
        required_files = {
            "README.md",
            "protocol_contract.md",
            "schema_examples.json",
            "flowguard_route_scheduler.json",
            "stress_testing.md",
        }
        self.assertEqual(required_files, {path.name for path in ASSET_ROOT.iterdir() if path.is_file()})

        contract = (ASSET_ROOT / "protocol_contract.md").read_text(encoding="utf-8")
        for phrase in (
            "ACK does not mean the work is done",
            "Output from a closed, expired, or superseded lease is not authoritative",
            "The project can close only after a backward chain exists",
            "A model of the target product cannot be used as proof that the development process is safe",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, contract)

    def test_schema_examples_cover_ledger_packets_review_flowguard_and_closure(self) -> None:
        schema = json.loads((ASSET_ROOT / "schema_examples.json").read_text(encoding="utf-8"))
        for key in (
            "black_box_ledger_entry",
            "agent_lease",
            "task_packet_envelope",
            "result_packet_envelope",
            "review_report",
            "flowguard_work_order",
            "final_backward_closure",
        ):
            with self.subTest(key=key):
                self.assertIn(key, schema)

        self.assertEqual(schema["agent_lease"]["status"], "active")
        self.assertEqual(schema["task_packet_envelope"]["required_reviewer"], "independent")
        self.assertTrue(schema["review_report"]["independent_from_producer"])
        self.assertEqual(
            schema["flowguard_work_order"]["selected_skill"],
            "flowguard-development-process-flow",
        )
        self.assertEqual(schema["final_backward_closure"]["decision"], "complete")

    def test_flowguard_scheduler_maps_each_risk_to_a_specific_skill(self) -> None:
        scheduler = json.loads(
            (ASSET_ROOT / "flowguard_route_scheduler.json").read_text(encoding="utf-8")
        )
        routes = {route["modeled_target"]: route for route in scheduler["routes"]}
        expected = {
            "target_product_behavior": "model-first-function-flow",
            "development_process": "flowguard-development-process-flow",
            "ui_interaction_flow": "flowguard-ui-flow-structure",
            "code_structure_plan": "flowguard-code-structure-recommendation",
            "large_structure_split": "flowguard-structure-mesh",
            "test_and_evidence_hierarchy": "flowguard-test-mesh",
            "model_test_alignment": "flowguard-model-test-alignment",
            "model_hierarchy": "flowguard-model-mesh",
            "model_miss": "flowguard-model-miss-review",
            "architecture_reduction": "flowguard-architecture-reduction",
        }

        self.assertEqual(set(expected), set(routes))
        for modeled_target, selected_skill in expected.items():
            with self.subTest(modeled_target=modeled_target):
                self.assertEqual(routes[modeled_target]["selected_skill"], selected_skill)

    def test_flowguard_model_accepts_happy_path_and_blocks_fake_agent_failures(self) -> None:
        report = runner.run_checks()
        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard"]["ok"], report["flowguard"])
        self.assertTrue(report["hazard_detection"]["ok"], report["hazard_detection"])
        self.assertTrue(report["scenario_matrix"]["ok"], report["scenario_matrix"])

        matrix = report["scenario_matrix"]["matrix"]
        self.assertEqual(matrix["success"], "accept_verified_result")
        for scenario in report["risk_scenarios"]:
            with self.subTest(scenario=scenario):
                self.assertTrue(matrix[scenario].startswith("block_"), matrix[scenario])

    def test_model_hazard_states_reject_false_completion_and_overblocking(self) -> None:
        hazards = model.hazard_states()
        self.assertIn("success_overblocked", hazards)
        self.assertGreaterEqual(len(hazards), 11)

        for name, state in hazards.items():
            with self.subTest(name=name):
                self.assertTrue(model.hard_check_failures(state))


if __name__ == "__main__":
    unittest.main()
