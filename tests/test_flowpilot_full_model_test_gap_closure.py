from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

import run_flowpilot_full_model_coverage_inventory as inventory  # noqa: E402
from scripts import run_flowguard_coverage_sweep as sweep  # noqa: E402


BASELINE_UNPARSED_RUNNERS: set[str] = set()

BASELINE_NOT_OK_RUNNERS: set[str] = set()

BASELINE_LIVE_RUNTIME_OR_STATE_FINDING_RUNNERS: set[str] = set()

BASELINE_SOURCE_OR_CODE_FINDING_RUNNERS = {
    "flowpilot_model_test_alignment",
}

BASELINE_MISSING_OR_SCOPED_REPLAY_ADAPTER_RUNNERS = {
    "flowpilot_controller_patrol",
    "flowpilot_decision_liveness",
    "flowpilot_persistent_router_daemon",
    "flowpilot_resume",
    "flowpilot_role_recovery",
    "flowpilot_route_mutation_activation",
    "flowpilot_router_loop",
    "flowpilot_startup_control",
    "flowpilot_terminal_state_monotonicity",
    "output_contract",
    "protocol_contract_conformance",
    "router_action_contract",
}

BASELINE_SKIPPED_OR_SCOPED_EVIDENCE_RUNNERS = {
    "flowpilot_control_plane_friction",
    "flowpilot_controller_patrol",
    "flowpilot_cross_plane_friction",
    "flowpilot_decision_liveness",
    "flowpilot_deterministic_startup_bootstrap",
    "flowpilot_gate_policy_audit",
    "flowpilot_persistent_router_daemon",
    "flowpilot_repair_transaction",
    "flowpilot_resume",
    "flowpilot_role_output_runtime",
    "flowpilot_role_recovery",
    "flowpilot_route_display",
    "flowpilot_route_mutation_activation",
    "flowpilot_router_internal_mechanics",
    "flowpilot_router_loop",
    "flowpilot_startup_control",
    "flowpilot_terminal_state_monotonicity",
    "output_contract",
    "protocol_contract_conformance",
    "router_action_contract",
}

BASELINE_ABSTRACT_WITHOUT_DETECTED_ORDINARY_TEST_REFERENCE_RUNNERS = {
    "command_refinement",
    "flowpilot_control_plane_ledger_consolidation",
    "flowpilot_control_plane_state_consistency",
    "flowpilot_daemon_microstep_lifecycle",
    "flowpilot_decision_liveness",
    "flowpilot_derived_view_prompt_boundary",
    "flowpilot_dynamic_return_path",
    "flowpilot_event_capability_registry",
    "flowpilot_event_envelope_transfer",
    "flowpilot_gate_decision_contract",
    "flowpilot_handoff_artifact_protocol",
    "flowpilot_model_driven_recursive_route",
    "flowpilot_model_hierarchy",
    "flowpilot_optimization_proposal",
    "flowpilot_packet_open_authority",
    "flowpilot_parallel_run_isolation",
    "flowpilot_parent_child_lifecycle",
    "flowpilot_pm_package_absorption",
    "flowpilot_prompt_boundary",
    "flowpilot_requirement_traceability",
    "flowpilot_reviewer_only_gate",
    "flowpilot_route_replanning_policy",
    "flowpilot_router_error_recovery",
    "flowpilot_router_facade_split",
    "flowpilot_router_internal_mechanics",
    "flowpilot_shared_maintenance_log",
    "flowpilot_startup_optimization",
    "flowpilot_structural_refactor",
    "flowpilot_structure_maintenance",
    "flowpilot_two_table_async_scheduler",
    "long_check_observability",
    "prompt_isolation",
    "proof_carrying",
    "router_action_contract",
    "router_next_recipient",
    "startup_pm_review",
}

GAP_CLASS_STRATEGY = {
    "runner_unparsed_or_unavailable": "failure-sentinel",
    "runner_not_ok": "failure-sentinel",
    "live_runtime_or_state_findings": "failure-sentinel",
    "source_or_code_findings": "result-contract",
    "missing_or_scoped_replay_adapter": "scoped-boundary",
    "skipped_or_scoped_evidence": "scoped-boundary",
    "abstract_without_detected_ordinary_test_reference": "runner-exec",
    "unclassified_model_tier": "result-contract",
}


def _records_by_runner() -> dict[str, dict[str, object]]:
    report = inventory.build_inventory()
    return {str(record["runner"]): record for record in report["records"]}


def _replay_manifest() -> dict[str, object]:
    return json.loads((ROOT / "simulations" / "flowpilot_full_model_replay_evidence.json").read_text(encoding="utf-8"))


def _baseline_strategies_for_runner(runner: str) -> set[str]:
    strategies: set[str] = set()
    if runner in BASELINE_UNPARSED_RUNNERS:
        strategies.add("failure-sentinel")
    if runner in BASELINE_NOT_OK_RUNNERS:
        strategies.add("failure-sentinel")
    if runner in BASELINE_LIVE_RUNTIME_OR_STATE_FINDING_RUNNERS:
        strategies.add("failure-sentinel")
    if runner in BASELINE_SOURCE_OR_CODE_FINDING_RUNNERS:
        strategies.add("result-contract")
    if runner in BASELINE_MISSING_OR_SCOPED_REPLAY_ADAPTER_RUNNERS:
        strategies.add("scoped-boundary")
    if runner in BASELINE_SKIPPED_OR_SCOPED_EVIDENCE_RUNNERS:
        strategies.add("scoped-boundary")
    if runner in BASELINE_ABSTRACT_WITHOUT_DETECTED_ORDINARY_TEST_REFERENCE_RUNNERS:
        strategies.add("runner-exec")
    return strategies


class FlowPilotFullModelTestGapClosureTests(unittest.TestCase):
    def test_all_inventory_gap_classes_have_closure_strategy(self) -> None:
        report = inventory.build_inventory()

        missing = set(report["gap_class_counts"]) - set(GAP_CLASS_STRATEGY)
        self.assertEqual(missing, set())

    def test_baseline_gap_runners_all_have_scripts_and_test_strategy(self) -> None:
        records = _records_by_runner()
        planned = (
            BASELINE_UNPARSED_RUNNERS
            | BASELINE_NOT_OK_RUNNERS
            | BASELINE_LIVE_RUNTIME_OR_STATE_FINDING_RUNNERS
            | BASELINE_SOURCE_OR_CODE_FINDING_RUNNERS
            | BASELINE_MISSING_OR_SCOPED_REPLAY_ADAPTER_RUNNERS
            | BASELINE_SKIPPED_OR_SCOPED_EVIDENCE_RUNNERS
            | BASELINE_ABSTRACT_WITHOUT_DETECTED_ORDINARY_TEST_REFERENCE_RUNNERS
        )

        for runner in sorted(planned):
            with self.subTest(runner=runner):
                record = records[runner]
                self.assertTrue(record["script"], runner)
                self.assertTrue((ROOT / str(record["script"])).exists(), runner)
                strategies = _baseline_strategies_for_runner(runner)
                self.assertTrue(strategies, runner)

    def test_abstract_gap_queue_now_has_ordinary_test_ownership(self) -> None:
        records = _records_by_runner()

        for runner in sorted(BASELINE_ABSTRACT_WITHOUT_DETECTED_ORDINARY_TEST_REFERENCE_RUNNERS):
            with self.subTest(runner=runner):
                self.assertIn(runner, records)
                self.assertNotEqual(
                    records[runner]["ordinary_test_reference_strength"],
                    "none_detected",
                )

    def test_no_model_runner_is_left_without_detected_test_reference(self) -> None:
        records = _records_by_runner()

        missing = sorted(
            runner
            for runner, record in records.items()
            if record["ordinary_test_reference_strength"] == "none_detected"
        )

        self.assertEqual(missing, [])

    def test_green_abstract_runners_have_executed_sweep_evidence(self) -> None:
        records = _records_by_runner()
        expected_non_green = BASELINE_NOT_OK_RUNNERS | BASELINE_UNPARSED_RUNNERS

        for runner in sorted(BASELINE_ABSTRACT_WITHOUT_DETECTED_ORDINARY_TEST_REFERENCE_RUNNERS):
            with self.subTest(runner=runner):
                record = records[runner]
                if runner in expected_non_green:
                    self.assertTrue(
                        (record["ok"] is False) or (not record["parsed"]),
                        runner,
                    )
                else:
                    self.assertTrue(record["parsed"], runner)
                    self.assertTrue(record["ok"], runner)

    def test_replay_and_skipped_gaps_have_exact_evidence_manifest(self) -> None:
        records = _records_by_runner()
        scoped_runners = (
            BASELINE_MISSING_OR_SCOPED_REPLAY_ADAPTER_RUNNERS
            | BASELINE_SKIPPED_OR_SCOPED_EVIDENCE_RUNNERS
        )

        for runner in sorted(scoped_runners):
            with self.subTest(runner=runner):
                record = records[runner]
                skipped = {
                    key: value
                    for key, value in dict(record["skipped_checks"]).items()
                    if key != "default_results_file"
                }
                self.assertTrue(skipped, runner)
                self.assertEqual(set(record["covered_skipped_checks"]), set(skipped))
                self.assertNotIn("missing_or_scoped_replay_adapter", record["gap_classes"])
                self.assertNotIn("skipped_or_scoped_evidence", record["gap_classes"])
                replay_evidence = dict(record["replay_evidence"])
                self.assertTrue(replay_evidence.get("evidence"), runner)

    def test_replay_manifest_matches_current_skipped_runner_keys(self) -> None:
        records = _records_by_runner()
        manifest_entries = {
            str(entry["runner"]): entry
            for entry in _replay_manifest()["entries"]
            if isinstance(entry, dict)
        }

        skipped_runners = {
            runner
            for runner, record in records.items()
            if any(key != "default_results_file" for key in dict(record["skipped_checks"]))
        }
        self.assertEqual(skipped_runners, BASELINE_SKIPPED_OR_SCOPED_EVIDENCE_RUNNERS)

        for runner in sorted(skipped_runners):
            with self.subTest(runner=runner):
                record = records[runner]
                entry = manifest_entries[runner]
                skipped = {
                    key
                    for key in dict(record["skipped_checks"])
                    if key != "default_results_file"
                }
                covered = set(entry["covered_skipped_checks"])
                self.assertEqual(covered, skipped)
                evidence_ids = {evidence["evidence_id"] for evidence in entry["evidence"]}
                for covered_row in entry["covered_skipped_checks"].values():
                    self.assertEqual(covered_row["status"], "covered_elsewhere")
                    self.assertLessEqual(set(covered_row["evidence_ids"]), evidence_ids)
                for evidence in entry["evidence"]:
                    self.assertTrue((ROOT / evidence["path"]).exists(), evidence["path"])

    def test_not_ok_and_unparsed_runners_remain_failure_sentinels(self) -> None:
        records = _records_by_runner()

        for runner in sorted(BASELINE_NOT_OK_RUNNERS):
            with self.subTest(runner=runner):
                self.assertFalse(records[runner]["ok"], runner)
                self.assertTrue(records[runner]["parsed"], runner)

        for runner in sorted(BASELINE_UNPARSED_RUNNERS):
            with self.subTest(runner=runner):
                self.assertFalse(records[runner]["parsed"], runner)

    def test_process_liveness_runner_is_parseable_after_facade_arg_discovery(self) -> None:
        records = _records_by_runner()
        record = records["flowpilot_process_liveness"]

        self.assertTrue(record["parsed"])
        self.assertTrue(record["ok"])
        self.assertNotIn("runner_unparsed_or_unavailable", record["gap_classes"])
        self.assertIn("--json", record["metadata"]["command"])
        self.assertIn("--no-write-results", record["metadata"]["command"])

    def test_process_liveness_facade_advertises_impl_json_arguments(self) -> None:
        path = ROOT / "simulations" / "run_flowpilot_process_liveness_checks.py"
        text = path.read_text(encoding="utf-8")

        self.assertTrue(sweep._supports_argument(path, text, "--json"))
        self.assertTrue(sweep._supports_argument(path, text, "--no-write-results"))


if __name__ == "__main__":
    unittest.main()
