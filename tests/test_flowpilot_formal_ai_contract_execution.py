from __future__ import annotations

import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_ai_response_execution_closure_model as model  # noqa: E402
from scripts.test_tier.background import artifact_paths, classify_background_artifact  # noqa: E402
from scripts.test_tier.definitions import commands_for_tier, formal_tier_contract  # noqa: E402


class FlowPilotFormalAIContractExecutionTests(unittest.TestCase):
    def test_static_universe_exhausts_registered_families_and_declared_faults(self) -> None:
        cells = model.build_static_contract_universe()

        self.assertFalse(model.static_universe_failures(cells))
        self.assertEqual(
            {cell["contract_family"] for cell in cells},
            set(model.packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY),
        )
        by_kind = {
            kind: sum(1 for cell in cells if cell["mutation_kind"] == kind)
            for kind in {str(cell["mutation_kind"]) for cell in cells}
        }
        self.assertEqual(by_kind["valid_minimal_shape"], 15)
        for kind in (
            "missing_required",
            "missing_required_child",
            "wrong_explicit_array_type",
            "empty_non_empty_array",
            "invalid_allowed_value",
            "wrong_field_type",
            "forbidden_field",
            "forbidden_alias",
            "identity_mismatch",
        ):
            self.assertGreater(by_kind[kind], 0, kind)

    def test_source_path_ids_repair_all_22_audited_collisions_and_fail_on_new_collision(self) -> None:
        audit = model.audited_collision_repair_report()

        self.assertTrue(audit["ok"], audit)
        self.assertEqual(audit["audited_collision_pair_count"], 22)
        self.assertEqual(audit["regenerated_case_count"], 44)
        self.assertTrue(audit["pair_ids_distinct"])
        synthetic = [
            {"case_id": "same-id", "source_contract_path": "source/a"},
            {"case_id": "same-id", "source_contract_path": "source/b"},
        ]
        self.assertTrue(model.case_id_collision_failures(synthetic))
        exact_duplicate = [
            {"case_id": "same-id", "source_contract_path": "source/a"},
            {"case_id": "same-id", "source_contract_path": "source/a"},
        ]
        self.assertTrue(model.case_id_collision_failures(exact_duplicate))

    def test_contract_oracle_signature_covers_owner_feedback_transition_and_effects(self) -> None:
        cell = model.build_execution_universe()[0]
        oracle = model.contract_oracle_for_cell(cell)

        self.assertTrue(oracle.owner)
        self.assertTrue(oracle.expected_state_transitions)
        self.assertTrue(oracle.allowed_side_effects)
        self.assertNotEqual(oracle.oracle_signature, replace(oracle, owner="different.owner").oracle_signature)
        self.assertNotEqual(
            oracle.oracle_signature,
            replace(oracle, error_feedback_fields=(*oracle.error_feedback_fields, "extra.feedback")).oracle_signature,
        )
        self.assertNotEqual(
            oracle.oracle_signature,
            replace(oracle, forbidden_side_effects=(*oracle.forbidden_side_effects, "extra.effect")).oracle_signature,
        )

    def test_fast_selector_closes_every_feasible_pair_without_full_product_execution(self) -> None:
        universe = model.build_execution_universe()
        selection = model.select_execution_cases(universe, mode="fast")

        self.assertTrue(selection["selection_complete"], selection["uncovered_tokens"])
        self.assertGreater(selection["pairwise_token_count"], 0)
        self.assertLess(len(selection["selected_case_ids"]), len(universe))
        self.assertTrue(selection["unselected_case_ids"])

    def test_fast_formal_submit_cases_have_real_assertion_receipts(self) -> None:
        report = model.run_execution_closure(mode="fast")

        self.assertTrue(report["ok"], report["failed_receipts"])
        validator = report["real_single_fault_validator"]
        self.assertTrue(validator["ok"], validator["failed_receipts"])
        self.assertEqual(validator["declared_case_count"], len(model.build_static_contract_universe()))
        self.assertEqual(
            validator["declared_case_count"],
            validator["applicable_case_count"] + validator["excluded_case_count"],
        )
        self.assertEqual(validator["selected_case_count"], validator["applicable_case_count"])
        self.assertEqual(validator["executed_case_count"], validator["selected_case_count"])
        self.assertEqual(validator["passed_case_count"], validator["executed_case_count"])
        self.assertEqual(validator["failed_case_count"], 0)
        self.assertEqual(validator["proof_backed_case_count"], validator["passed_case_count"])
        self.assertEqual(validator["source_fingerprint"], report["source_fingerprint"])
        counts = report["execution_universe"]
        self.assertEqual(counts["selected_case_count"], counts["executed_case_count"])
        self.assertEqual(counts["failed_case_count"], 0)
        self.assertGreater(counts["passed_case_count"], 0)
        self.assertGreater(counts["not_run_case_count"], 0)
        for receipt in report["receipts"]:
            if receipt["execution_status"] == "passed":
                self.assertTrue(receipt["assertions"])
                self.assertTrue(all(item["ok"] for item in receipt["assertions"]))
                self.assertEqual(receipt["oracle_signature"], receipt["contract_oracle"]["oracle_signature"])
                self.assertTrue(receipt["observed_transition"])
                self.assertTrue(receipt["observed_next_action"]["action_type"])
                self.assertEqual(
                    receipt["public_pipeline"]["stages_traversed"],
                    list(model.PUBLIC_PIPELINE_STAGES),
                )
                self.assertEqual(
                    receipt["public_pipeline"]["responder_authority"],
                    "submission_checklist.v2",
                )
                self.assertTrue(receipt["proof_backed"])
            elif receipt["execution_status"] == "not_run":
                self.assertEqual(receipt["execution_status"], "not_run")
                self.assertTrue(receipt["not_run_reason"])
            else:
                self.assertEqual(receipt["execution_status"], "excluded")
                self.assertTrue(receipt["structured_exclusion"])
        for receipt in validator["receipts"]:
            if receipt["execution_status"] == "excluded":
                self.assertTrue(receipt["structured_exclusion"])
                continue
            self.assertTrue(receipt["assertions"])
            self.assertTrue(all(item["ok"] for item in receipt["assertions"]), receipt)
            self.assertTrue(receipt["observed_status"])
            self.assertTrue(receipt["repair_action"]["action"])
            self.assertTrue(receipt["observed_transition"])
            self.assertIn("observed_side_effects", receipt)
            self.assertIn("contract_oracle", receipt)
        self.assertTrue(report["timing"]["budget_passed"])
        self.assertLessEqual(report["timing"]["duration_seconds"], model.FAST_BUDGET_SECONDS)
        for row in report["oracle_equivalence"]["receipts"]:
            self.assertTrue(row["oracle_equal"])
            self.assertTrue(row["owner_equal"])
            self.assertTrue(row["feedback_equal"])
            self.assertTrue(row["transition_equal"])
            self.assertTrue(row["side_effect_equal"])
            self.assertFalse(row["counted_as_executed"])
        for representative in report["oracle_equivalence"]["representative_receipts"]:
            self.assertTrue(representative["covered_source_case_ids"])
            self.assertEqual(
                representative["counted_as_executed_case_ids"],
                [representative["representative_case_id"]],
            )

    def test_formal_submit_tiers_feed_the_acyclic_final_confidence_dag(self) -> None:
        all_names = {command.name for command in commands_for_tier("all")}
        adversarial_names = {
            command.name for command in commands_for_tier("formal-submit-adversarial")
        }
        release_names = {command.name for command in commands_for_tier("release")}
        final_names = {command.name for command in commands_for_tier("final-confidence")}

        self.assertIn("formal_ai_submit_fast_runner", all_names)
        self.assertIn("formal_ai_submit_fast_tests", all_names)
        self.assertIn("formal_ai_submit_adversarial_runner", adversarial_names)
        self.assertIn("formal_ai_submit_adversarial_tests", adversarial_names)
        self.assertIn("formal_ai_submit_historical_regressions", adversarial_names)

        # Release and adversarial evidence are independent upstream roots.  The
        # final-confidence tier is a terminal consumer of their compiled
        # TestMesh manifest, so neither upstream tier may recursively embed the
        # other or the final consumer.
        self.assertNotIn("formal_ai_submit_adversarial_runner", release_names)
        self.assertNotIn("formal_ai_submit_adversarial_tests", release_names)
        self.assertNotIn("formal_ai_submit_historical_regressions", release_names)
        self.assertNotIn("formal_ai_submit_adversarial_runner", final_names)
        self.assertNotIn("formal_ai_submit_adversarial_tests", final_names)
        self.assertNotIn("formal_ai_submit_historical_regressions", final_names)
        self.assertEqual(final_names, {"flowpilot_final_confidence_gate"})

    def test_formal_tier_contracts_have_budgets_no_hidden_skip_and_final_artifacts(self) -> None:
        for tier in ("formal-submit-fast", "formal-submit-adversarial"):
            contract = formal_tier_contract(tier)
            commands = commands_for_tier(tier)
            self.assertGreater(contract["budget_seconds"], 0)
            self.assertFalse(contract["hidden_skip_allowed"])
            self.assertEqual(
                set(contract["required_final_artifact_suffixes"]),
                {"out", "err", "combined", "exit", "meta"},
            )
            self.assertEqual(contract["recommended_windows_parallel_workers"], 2)
            self.assertFalse([part for command in commands for part in command.command if part.startswith("--skip")])

    def test_progress_only_and_failed_background_artifacts_cannot_satisfy_formal_tier(self) -> None:
        with tempfile.TemporaryDirectory(prefix="formal-tier-artifacts-") as tmp_name:
            root = Path(tmp_name)
            progress = artifact_paths(root, "progress")
            progress["combined"].write_text("still running\n", encoding="utf-8")
            failed = artifact_paths(root, "failed")
            failed["meta"].write_text('{"status":"failed"}\n', encoding="utf-8")
            failed["exit"].write_text("124\n", encoding="utf-8")

            self.assertEqual(classify_background_artifact(root, "progress")["status"], "progress_only")
            self.assertFalse(classify_background_artifact(root, "progress")["ok"])
            self.assertEqual(classify_background_artifact(root, "failed")["status"], "failed")
            self.assertFalse(classify_background_artifact(root, "failed")["ok"])


if __name__ == "__main__":
    unittest.main()
