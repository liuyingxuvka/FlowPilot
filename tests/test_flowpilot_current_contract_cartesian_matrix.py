from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
    "run_flowpilot_current_contract_cartesian_matrix_checks",
    ROOT / "simulations" / "run_flowpilot_current_contract_cartesian_matrix_checks.py",
)
model = runner.model


class FlowPilotCurrentContractCartesianMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = runner.run_checks()

    def test_current_contract_cartesian_runner_accepts_full_matrix(self) -> None:
        report = self.report

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["model_id"], model.MODEL_ID)
        self.assertGreater(report["matrix"]["declared_counts"]["required_cell_count"], 3_000_000)
        self.assertEqual(
            report["matrix"]["observed_cell_count"],
            report["matrix"]["declared_counts"]["required_cell_count"],
        )
        self.assertGreater(
            report["matrix"]["declared_counts"]["unrestricted_symbolic_product_count"],
            report["matrix"]["declared_counts"]["required_cell_count"],
        )

    def test_every_declared_axis_value_is_materialized(self) -> None:
        coverage = self.report["axis_coverage"]

        self.assertTrue(coverage["ok"], coverage)
        self.assertEqual(coverage["missing_axis_values"], {})
        for axis, values in model.AXIS_VALUES.items():
            with self.subTest(axis=axis):
                self.assertEqual(set(coverage["coverage"][axis]["present"]), set(values))

    def test_no_glassbreak_is_a_passing_current_contract_reaction(self) -> None:
        matrix = self.report["matrix"]

        self.assertNotIn("glassbreak_alarm", matrix["by_reaction"])
        self.assertEqual(matrix["glassbreak_reactions"], [])
        self.assertGreater(matrix["by_reaction"]["require_repair_delta"], 0)
        self.assertIn(
            "glassbreak_entered_current_contract_path",
            self.report["hazards"]["hazards"]["glassbreak_entered"],
        )
        threshold_cells = [
            cell
            for cell in model.REQUIRED_FULL_CARTESIAN_CELLS
            if cell["blocker_state"] == "same_blocker_at_threshold"
        ]
        self.assertTrue(threshold_cells)
        self.assertFalse([
            cell["cell_id"]
            for cell in threshold_cells
            if cell["expected_reaction"] == "glassbreak_alarm" or cell["glassbreak_allowed"]
        ])
        self.assertTrue([
            cell
            for cell in threshold_cells
            if cell["expected_reaction"] == "require_repair_delta"
        ])
        for cell in threshold_cells[:50]:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertTrue(cell["current_contract_glassbreak_forbidden"])

    def test_reject_block_and_reissue_paths_have_absorbing_next_actions(self) -> None:
        matrix = self.report["matrix"]

        self.assertEqual(matrix["missing_absorbing_next_action"], [])
        self.assertLessEqual(
            set(matrix["by_reaction"]),
            set(model.ABSORBING_NEXT_ACTION_BY_REACTION),
        )
        for reaction in matrix["by_reaction"]:
            with self.subTest(reaction=reaction):
                self.assertTrue(model.ABSORBING_NEXT_ACTION_BY_REACTION[reaction])

    def test_old_future_progress_and_legacy_paths_are_not_accepted(self) -> None:
        matrix = self.report["matrix"]

        self.assertEqual(matrix["stale_or_old_evidence_accepted"], [])
        self.assertEqual(matrix["future_claim_accepted"], [])
        self.assertEqual(matrix["progress_accepted_as_evidence"], [])
        self.assertEqual(matrix["legacy_positive_acceptance"], [])
        self.assertGreater(matrix["by_reaction"]["mechanical_reject"], 0)
        self.assertGreater(matrix["by_reaction"]["reject_overclaim"], 0)
        self.assertGreater(matrix["by_reaction"]["progress_only_not_evidence"], 0)

    def test_malformed_json_ai_profiles_are_mechanical_reject_cells(self) -> None:
        malformed_profiles = {
            value
            for value in model.AI_RETURN_PROFILES
            if str(value).startswith("malformed_json_")
        }
        self.assertEqual(
            malformed_profiles,
            {
                "malformed_json_unquoted_keys",
                "malformed_json_markdown_wrapped",
                "malformed_json_prose_plus_json",
                "malformed_json_top_level_array",
                "malformed_json_empty_body",
                "malformed_json_trailing_comma",
            },
        )
        cells = [
            cell
            for cell in model.REQUIRED_FULL_CARTESIAN_CELLS
            if cell["ai_return_profile"] in malformed_profiles
        ]
        self.assertTrue(cells)
        self.assertFalse([
            cell["cell_id"]
            for cell in cells[:500]
            if cell["expected_reaction"] != "mechanical_reject"
            or cell["existing_test_link_id"] != "fake_ai_malformed_body_profiles"
        ])

    def test_reused_existing_tests_are_current_contract_audited(self) -> None:
        audit = self.report["existing_test_reuse_audit"]

        self.assertTrue(audit["ok"], audit)
        self.assertEqual(audit["failed_used_links"], [])
        self.assertEqual(audit["missing_registered_links"], [])
        for link_id, link_audit in audit["audits"].items():
            with self.subTest(link_id=link_id):
                if link_audit["used_by_matrix"]:
                    self.assertTrue(link_audit["ok"], link_audit)
                    self.assertGreater(link_audit["covered_cell_count"], 0)
                    self.assertEqual(link_audit["missing_markers"], [])
                    self.assertEqual(link_audit["forbidden_legacy_positive_markers"], [])

    def test_non_materialized_product_classes_are_explicit(self) -> None:
        class_ids = {entry["class_id"] for entry in self.report["not_applicable_classes"]}

        self.assertIn("global_cross_stage_product_not_materialized", class_ids)
        self.assertIn("legacy_protocol_positive_path_forbidden", class_ids)
        self.assertIn("glassbreak_not_current_contract_success_path", class_ids)


if __name__ == "__main__":
    unittest.main()
