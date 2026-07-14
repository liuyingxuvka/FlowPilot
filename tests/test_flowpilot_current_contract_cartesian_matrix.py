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
        cls.report = runner.run_checks(declaration_only=True)

    def test_current_contract_cartesian_runner_accepts_full_matrix(self) -> None:
        report = self.report

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["claim_scope"], "declaration_only")
        self.assertEqual(report["evidence_status"], "not_run")
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
        self.assertEqual(matrix["source_purity_positive_acceptance"], [])
        self.assertEqual(matrix["source_purity_shape_failures"], [])
        self.assertEqual(matrix["noncurrent_sources_in_positive_profiles"], {})
        self.assertGreater(matrix["by_reaction"]["mechanical_reject"], 0)
        self.assertGreater(matrix["by_reaction"]["reject_overclaim"], 0)
        self.assertGreater(matrix["by_reaction"]["progress_only_not_evidence"], 0)

    def test_source_purity_cartesian_rejects_every_failure_at_every_entrypoint(self) -> None:
        cells = list(model.iter_source_purity_negative_cells())
        expected_pairs = {
            (str(entrypoint["entrypoint_id"]), str(failure["failure_class"]))
            for entrypoint in model.SOURCE_PURITY_ENTRYPOINTS
            for failure in model.SOURCE_PURITY_FAILURE_PROFILES
        }

        self.assertEqual(len(cells), model.SOURCE_PURITY_REQUIRED_CELL_COUNT)
        self.assertEqual(len(cells), 35)
        self.assertEqual(
            {
                (str(cell["source_purity_entrypoint"]), str(cell["source_purity_failure_class"]))
                for cell in cells
            },
            expected_pairs,
        )
        self.assertEqual(len({str(cell["cell_id"]) for cell in cells}), len(cells))
        self.assertFalse([
            cell["cell_id"]
            for cell in cells
            if cell["expected_reaction"] != "mechanical_reject"
            or cell["required_evidence_owner"] != "current_contract_runtime_matrix"
            or cell["existing_test_link_id"] != "current_contract_source_purity_negatives"
            or cell["source_purity_negative_only"] is not True
            or cell["current_stage_profile"] is not False
        ])
        historical_negative = [cell for cell in cells if cell["historical_negative"]]
        self.assertEqual(len(historical_negative), 30)
        self.assertEqual(
            {str(cell["source_purity_failure_class"]) for cell in cells if not cell["historical_negative"]},
            {"wrong_role"},
        )

    def test_daemon_replay_is_historical_negative_only(self) -> None:
        self.assertIn("daemon_replay", model.HISTORICAL_NEGATIVE_EXECUTION_SOURCES)
        self.assertNotIn("daemon_replay", model.CURRENT_EXECUTION_SOURCES)
        for group, profile in model.PROFILE_BY_STAGE_GROUP.items():
            with self.subTest(group=group):
                self.assertNotIn("daemon_replay", profile["sources"])
                self.assertTrue(
                    set(profile["sources"]).isdisjoint(model.HISTORICAL_NEGATIVE_EXECUTION_SOURCES)
                )
        daemon_cells = [
            cell
            for cell in model.iter_source_purity_negative_cells()
            if cell["source_purity_failure_class"] == "daemon_replay"
        ]
        self.assertEqual(len(daemon_cells), len(model.SOURCE_PURITY_ENTRYPOINTS))
        self.assertFalse([
            cell["cell_id"]
            for cell in daemon_cells
            if cell["expected_reaction"] != "mechanical_reject"
            or cell["historical_negative"] is not True
        ])

    def test_source_purity_runner_reports_exact_counts(self) -> None:
        matrix = self.report["matrix"]

        self.assertEqual(matrix["declared_counts"]["source_purity_required_cell_count"], 35)
        self.assertEqual(matrix["source_purity_observed_cell_count"], 35)
        self.assertEqual(matrix["source_purity_historical_negative_count"], 30)
        self.assertEqual(
            matrix["source_purity_by_entrypoint"],
            {str(entrypoint["entrypoint_id"]): 7 for entrypoint in model.SOURCE_PURITY_ENTRYPOINTS},
        )
        self.assertEqual(
            matrix["source_purity_by_failure_class"],
            {str(failure["failure_class"]): 5 for failure in model.SOURCE_PURITY_FAILURE_PROFILES},
        )

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
                "malformed_json_stringified_object",
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
        ])
        ordinary_malformed = [cell for cell in cells if cell["ai_return_profile"] != "malformed_json_stringified_object"]
        self.assertFalse([
            cell["cell_id"]
            for cell in ordinary_malformed[:500]
            if cell["existing_test_link_id"] != "fake_ai_malformed_body_profiles"
        ])
        stringified_cells = [cell for cell in cells if cell["ai_return_profile"] == "malformed_json_stringified_object"]
        self.assertTrue(stringified_cells)
        self.assertFalse([
            cell["cell_id"]
            for cell in stringified_cells[:500]
            if cell["existing_test_link_id"] != "submit_result_body_entry_canaries"
        ])

    def test_pointer_corruption_cells_recover_or_block_without_guessing(self) -> None:
        pointer_states = {
            "current_pointer_corrupt_unambiguous",
            "current_pointer_corrupt_ambiguous",
            "index_pointer_corrupt",
            "pointer_write_in_progress",
        }
        pointer_cells = [
            cell
            for cell in model.REQUIRED_FULL_CARTESIAN_CELLS
            if cell["object_state"] in pointer_states
        ]

        self.assertTrue(pointer_cells)
        reactions_by_state = {}
        for cell in pointer_cells:
            reactions_by_state.setdefault(cell["object_state"], cell["expected_reaction"])
        self.assertEqual(reactions_by_state["current_pointer_corrupt_unambiguous"], "recover_pointer")
        self.assertEqual(reactions_by_state["index_pointer_corrupt"], "recover_pointer")
        self.assertEqual(reactions_by_state["current_pointer_corrupt_ambiguous"], "structured_blocker")
        self.assertEqual(reactions_by_state["pointer_write_in_progress"], "structured_blocker")
        self.assertFalse([
            cell["cell_id"]
            for cell in pointer_cells[:500]
            if cell["existing_test_link_id"] != "pointer_persistence_canaries"
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

    def test_strict_testmesh_consumes_current_proof_counts_not_model_cells(self) -> None:
        proof = {
            "artifact_id": "proof.current-cartesian-tests",
            "producer_route": "flowguard-test-mesh",
            "command": "python scripts/run_test_tier.py --tier all --background",
            "result_path": "tmp/test_background/current-all",
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {"all.meta.json": "a" * 64, "all.exit.txt": "b" * 64},
            "covered_obligation_ids": ["all-current-tests"],
            "assertion_scope": "external_contract",
            "current": True,
            "route_evidence_current": True,
            "progress_only": False,
            "metadata": {"selected_child_command_count": 17, "executed_child_command_count": 17},
        }
        manifest = {
            "source_fingerprint": runner.source_fingerprint(),
            "routine": {
                "all": {
                    "result_status": "passed",
                    "selected_count": 17,
                    "test_count": 17,
                    "proof_artifact": proof,
                }
            },
        }
        strict = runner._test_mesh_report(
            self.report["matrix"],
            evidence_manifest=manifest,
            declaration_only=False,
            evidence_scope="routine",
        )

        self.assertTrue(strict["ok"], strict)
        for suite in strict["child_suites"].values():
            self.assertEqual(suite["test_count"], 17)
            self.assertNotEqual(suite["test_count"], suite["owned_cell_count"])
            self.assertTrue(suite["proof_artifact"])
            self.assertTrue(suite["reuse_ticket"])
            self.assertTrue(suite["owned_shard_ids"])

    def test_strict_testmesh_rejects_reused_proof_without_ticket(self) -> None:
        proof = {
            "artifact_id": "proof.reused-without-ticket",
            "producer_route": "flowguard-test-mesh",
            "command": "python scripts/run_test_tier.py --tier all --background",
            "result_path": "tmp/test_background/current-all",
            "result_status": "passed",
            "exit_code": 0,
            "artifact_fingerprints": {"all.meta.json": "a" * 64},
            "covered_obligation_ids": ["all-current-tests"],
            "assertion_scope": "external_contract",
            "current": True,
            "metadata": {"selected_child_command_count": 1, "executed_child_command_count": 1},
        }
        manifest = {
            "source_fingerprint": runner.source_fingerprint(),
            "routine": {
                "all": {
                    "result_status": "passed",
                    "selected_count": 1,
                    "test_count": 1,
                    "result_reused": True,
                    "proof_artifact": proof,
                }
            },
        }
        strict = runner._test_mesh_report(
            self.report["matrix"],
            evidence_manifest=manifest,
            declaration_only=False,
            evidence_scope="routine",
        )

        self.assertFalse(strict["ok"])
        self.assertIn("all:missing_test_reuse_ticket", strict["execution_evidence"]["failures"])

    def test_non_materialized_product_classes_are_explicit(self) -> None:
        class_ids = {entry["class_id"] for entry in self.report["not_applicable_classes"]}

        self.assertIn("global_cross_stage_product_not_materialized", class_ids)
        self.assertIn("legacy_protocol_positive_path_forbidden", class_ids)
        self.assertIn("noncurrent_execution_source_positive_path_forbidden", class_ids)
        self.assertIn("glassbreak_not_current_contract_success_path", class_ids)


if __name__ == "__main__":
    unittest.main()
