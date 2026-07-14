from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS = ROOT / "simulations"
if str(SIMULATIONS) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS))

import flowpilot_ai_response_execution_closure_model as model  # noqa: E402
import run_flowpilot_ai_response_execution_closure_checks as runner  # noqa: E402


class FlowPilotAIResponseExecutionClosureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = model.run_execution_closure(mode="adversarial")

    def test_adversarial_selector_closes_pairwise_and_critical_three_way_tokens(self) -> None:
        universe = model.build_execution_universe()
        selection = model.select_execution_cases(universe, mode="adversarial")

        self.assertTrue(selection["selection_complete"], selection["uncovered_tokens"])
        self.assertGreater(selection["pairwise_token_count"], 0)
        self.assertGreater(selection["critical_triple_token_count"], 0)
        self.assertEqual(set(selection["business_triple_groups"]), set(model.BUSINESS_TRIPLE_AXES))
        for group in selection["business_triple_groups"].values():
            self.assertEqual(group["covered_token_count"], group["required_token_count"])
        self.assertLessEqual(len(selection["selected_case_ids"]), len(universe))

    def test_adversarial_execution_keeps_not_run_failed_and_passed_separate(self) -> None:
        report = self.report

        self.assertTrue(report["ok"], report["failed_receipts"])
        counts = report["execution_universe"]
        self.assertEqual(counts["failed_case_count"], 0)
        self.assertEqual(counts["selected_case_count"], counts["executed_case_count"])
        self.assertEqual(
            counts["declared_case_count"],
            counts["passed_case_count"]
            + counts["failed_case_count"]
            + counts["not_run_case_count"]
            + counts["excluded_case_count"],
        )
        self.assertEqual(counts["proof_backed_case_count"], counts["passed_case_count"])
        expected_count_fields = {
            "declared",
            "applicable",
            "excluded",
            "generated",
            "selected",
            "executed",
            "passed",
            "failed",
            "stale",
            "proof_backed",
        }
        self.assertEqual(set(report["coverage_summary"]["count_fields"]), expected_count_fields)
        self.assertTrue(report["coverage_summary"]["counts_are_independent"])
        self.assertEqual(set(report["coverage_summary"]["aggregate"]), expected_count_fields)
        self.assertEqual(report["test_mesh"]["status"], "passed")
        self.assertEqual(
            report["test_mesh"]["required_child_case_ids"],
            report["test_mesh"]["executed_child_case_ids"],
        )

    def test_adversarial_lane_executes_every_pinned_fuzz_and_registers_every_historical_miss(self) -> None:
        fuzz = self.report["deterministic_fuzz"]
        historical = self.report["historical_misses"]

        self.assertTrue(fuzz["ok"], fuzz["failed_receipts"])
        self.assertEqual(fuzz["declared_profile_count"], len(model.FUZZ_PROFILE_IDS))
        self.assertEqual(fuzz["executed_profile_count"], len(model.FUZZ_PROFILE_IDS))
        self.assertEqual(fuzz["failed_profile_count"], 0)
        self.assertEqual(
            {receipt["profile_id"] for receipt in fuzz["receipts"]},
            set(model.FUZZ_PROFILE_IDS),
        )
        self.assertTrue(historical["ok"], historical)
        self.assertEqual(set(historical["mandatory_case_ids"]), set(model.HISTORICAL_MISS_IDS))
        self.assertEqual(historical["registered_case_count"], len(model.HISTORICAL_MISS_IDS))
        self.assertGreater(historical["locally_executed_case_count"], 0)
        self.assertGreater(historical["delegated_child_case_count"], 0)

    def test_hostile_syntax_oracles_record_creation_reissue_and_state_mutation(self) -> None:
        receipts = {
            receipt["profile_id"]: receipt for receipt in self.report["deterministic_fuzz"]["receipts"]
        }
        for profile_id in (
            "invalid_numeric_nan",
            "invalid_numeric_infinity",
            "utf8_bom",
            "top_level_non_object",
            "prose_wrapper",
            "markdown_wrapper",
        ):
            receipt = receipts[profile_id]
            self.assertEqual(receipt["observed_status"], "mechanical_contract_blocked")
            self.assertTrue(receipt["result_created"])
            self.assertTrue(receipt["reissue_packet_id"])
            self.assertEqual(receipt["state_transition"], "superseded_after_repair")
            self.assertTrue(all(assertion["ok"] for assertion in receipt["assertions"]))
        self.assertEqual(
            receipts["invalid_unicode_scalar"]["observed_status"],
            "rejected_without_result_allocation",
        )
        for profile_id in ("sequential_replay", "concurrent_double_submit"):
            self.assertEqual(receipts[profile_id]["observed_status"], "one_result_plus_one_rejection")
        duplicate = receipts["duplicate_json_keys"]
        self.assertTrue(duplicate["duplicate_key_preflight"]["object_pairs_hook_used"])
        self.assertEqual(duplicate["duplicate_key_preflight"]["duplicate_keys"], ["decision"])
        self.assertTrue(duplicate["duplicate_key_preflight"]["plain_json_loads_is_not_duplicate_evidence"])

    def test_cross_run_direct_surface_limitation_is_visible_problem_backfeed(self) -> None:
        cross_run = next(
            row
            for row in self.report["deterministic_fuzz"]["receipts"]
            if row["profile_id"] == "cross_run_identity_collision"
        )
        backfeed = self.report["observed_problem_backfeed"]

        self.assertEqual(cross_run["observed_status"], "accepted_by_run_local_direct_surface")
        self.assertIn("no run-id parameter", cross_run["claim_boundary"])
        self.assertTrue(backfeed["all_historical_misses_backfed"])
        self.assertIn(
            "observed-problem:fuzz:cross_run_identity_collision",
            {row["problem_id"] for row in backfeed["rows"]},
        )

    def test_public_path_benchmark_measures_40_cases_in_four_shards_with_two_workers(self) -> None:
        benchmark = self.report["public_path_benchmark"]

        self.assertTrue(benchmark["ok"], benchmark)
        self.assertEqual(benchmark["case_count"], 40)
        self.assertEqual(benchmark["worker_count"], 2)
        self.assertTrue(benchmark["windows_recommended_parallelism_confirmed"])
        self.assertEqual(len(benchmark["case_timings"]), 40)
        self.assertEqual(len(benchmark["shards"]), 4)
        self.assertEqual(sum(shard["case_count"] for shard in benchmark["shards"]), 40)
        self.assertTrue(all(row["duration_ms"] >= 0 for row in benchmark["case_timings"]))
        self.assertTrue(all(row["proof_backed"] for row in benchmark["case_timings"]))
        self.assertTrue(
            all(row["public_pipeline_stages"] == list(model.PUBLIC_PIPELINE_STAGES) for row in benchmark["case_timings"])
        )
        self.assertTrue(all(row["responder_authority"] == "submission_checklist.v2" for row in benchmark["case_timings"]))
        self.assertTrue(all(shard["public_pipeline_complete"] for shard in benchmark["shards"]))
        self.assertTrue(all(shard["proof_backed_case_count"] == shard["case_count"] for shard in benchmark["shards"]))
        self.assertEqual(benchmark["source_fingerprint"], self.report["source_fingerprint"])
        self.assertTrue(self.report["timing"]["budget_passed"])

    def test_every_selected_runtime_receipt_is_bound_to_an_executable_contract_oracle(self) -> None:
        selected = [row for row in self.report["receipts"] if row["execution_status"] == "passed"]

        self.assertTrue(selected)
        for receipt in selected:
            oracle = receipt["contract_oracle"]
            self.assertEqual(receipt["case_id"], oracle["case_id"])
            self.assertEqual(receipt["oracle_signature"], oracle["oracle_signature"])
            self.assertTrue(oracle["owner"])
            self.assertTrue(oracle["expected_state_transitions"])
            self.assertTrue(oracle["allowed_side_effects"])
            self.assertTrue(all(assertion["ok"] for assertion in receipt["assertions"]))
            self.assertEqual(receipt["public_pipeline"]["stages_traversed"], list(model.PUBLIC_PIPELINE_STAGES))
            self.assertEqual(receipt["public_pipeline"]["submission_checklist_schema"], "black_box_flowpilot.submission_checklist.v2")
            self.assertEqual(receipt["public_pipeline"]["responder_authority"], "submission_checklist.v2")
            self.assertFalse(receipt["public_pipeline"]["packet_body_used_as_responder_authority"])

    def test_flowguard_runner_rejects_false_green_hazards_and_consumes_real_receipts(self) -> None:
        report = runner.run_checks(mode="fast")

        self.assertTrue(report["ok"], report)
        self.assertTrue(report["flowguard_explorer"]["ok"])
        self.assertTrue(report["known_bad_hazards"]["ok"])
        self.assertTrue(report["execution_closure"]["ok"])
        for case in report["known_bad_hazards"]["cases"].values():
            self.assertTrue(case["detected"])


if __name__ == "__main__":
    unittest.main()
