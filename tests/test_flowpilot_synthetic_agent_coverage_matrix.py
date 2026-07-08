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


coverage_matrix = load_module(
    "flowpilot_synthetic_agent_coverage_matrix",
    ROOT / "simulations" / "flowpilot_synthetic_agent_coverage_matrix.py",
)


class FlowPilotSyntheticAgentCoverageMatrixTests(unittest.TestCase):
    def test_coverage_matrix_has_current_required_branch_owners(self) -> None:
        report = coverage_matrix.build_report()

        self.assertTrue(report["ok"], report["findings"])
        self.assertGreater(report["required_cell_count"], 20)
        self.assertGreater(report["row_count"], report["required_cell_count"])
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["full_diagnostic"]["release_convergence_ok"], report["full_diagnostic"])
        self.assertEqual(report["full_diagnostic"]["blocking_actionable_findings"], [])
        for finding in report["full_diagnostic"]["deferred_structure_split_findings"]:
            with self.subTest(surface_id=finding["surface_id"]):
                self.assertEqual(finding["source_code"], "needs_structure_split")
                self.assertEqual(finding["repair_type"], "defer_structure_split")
        for family in (
            "startup",
            "packet/card/ack",
            "route mutation",
            "route authority singularity",
            "current-node trunk invariant",
            "terminal/closure/resume",
            "role/output contracts",
            "router loop/daemon",
            "test tiering/slow-test contracts",
            "meta/capability parents",
        ):
            with self.subTest(family=family):
                self.assertGreater(report["rows_by_family"].get(family, 0), 0)

    def test_synthetic_rows_are_non_live_and_backed_by_trace_tests(self) -> None:
        report = coverage_matrix.build_report()
        synthetic_rows = [
            row
            for row in report["rows"]
            if row["coverage_kind"] in coverage_matrix.SYNTHETIC_NON_LIVE_KINDS
        ]

        self.assertGreaterEqual(len(synthetic_rows), 22)
        test_text_cache: dict[Path, str] = {}
        for row in synthetic_rows:
            with self.subTest(evidence_id=row["evidence_id"]):
                self.assertFalse(row["live_completion_allowed"])
                self.assertIn(row["coverage_boundary"], {
                    "control_flow_only",
                    "non_live_evidence_disclosure_only",
                    "background_final_artifact_contract",
                    "historical_same_class_non_live_control_flow",
                    "glassbreak_threshold_only",
                    "model_only_current_contract_cartesian_summary",
                })
                evidence_test_path = ROOT / row["path"]
                self.assertTrue(evidence_test_path.exists())
                test_text = test_text_cache.setdefault(
                    evidence_test_path,
                    evidence_test_path.read_text(encoding="utf-8"),
                )
                self.assertIn(row["test_name"], test_text)
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertIn(row["story_level"], {"local", "system"})

    def test_liveness_evidence_cartesian_summary_is_wired_to_synthetic_matrix(self) -> None:
        report = coverage_matrix.build_report()
        summary = report["liveness_evidence_cartesian"]
        rows = [
            row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.LIVENESS_EVIDENCE_CARTESIAN_MODEL_ID
        ]

        self.assertTrue(summary["ok"], summary)
        self.assertEqual(summary["row_count"], 35_280)
        self.assertEqual(len(rows), summary["row_count"])
        self.assertGreater(summary["runtime_executable_count"], 0)
        self.assertGreater(summary["legacy_pollution_case_count"], 0)
        self.assertLessEqual(
            {
                "wait_missing_ack",
                "remind_missing_ack",
                "replace_missing_ack",
                "wait_fresh_evidence",
                "remind_stale_progress",
                "replace_stale_progress",
                "final_result_wins",
                "mechanical_result_block",
                "invalid_setup",
            },
            set(summary["by_reaction"]),
        )
        for row in rows[:100]:
            with self.subTest(evidence_id=row["evidence_id"]):
                self.assertEqual(row["coverage_kind"], "synthetic_trace")
                self.assertFalse(row["live_completion_allowed"])
                self.assertEqual(row["coverage_boundary"], "control_flow_only")
                self.assertIn("liveness_evidence.", row["obligation_id"])

    def test_rejection_liveness_required_cells_have_owners(self) -> None:
        report = coverage_matrix.build_report()
        matrix_cell_ids = {
            matrix_cell["cell_id"]
            for matrix_cell in coverage_matrix.REQUIRED_REJECTION_LIVENESS_CELLS
        }
        required_cells = [
            cell
            for cell in report["required_cells"]
            if cell["model_id"] == coverage_matrix.REJECTION_LIVENESS_MODEL_ID
            and str(cell["obligation_id"]).startswith("rejection_liveness.")
            and str(cell["obligation_id"]).removeprefix("rejection_liveness.") in matrix_cell_ids
        ]
        rows = [
            row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.REJECTION_LIVENESS_MODEL_ID
            and str(row["obligation_id"]).startswith("rejection_liveness.")
            and str(row["obligation_id"]).removeprefix("rejection_liveness.") in matrix_cell_ids
        ]

        self.assertEqual(len(required_cells), len(coverage_matrix.REQUIRED_REJECTION_LIVENESS_CELLS))
        self.assertEqual(len(rows), len(required_cells))
        self.assertEqual({cell["family"] for cell in required_cells}, {
            cell["family"] for cell in coverage_matrix.REQUIRED_REJECTION_LIVENESS_CELLS
        })
        self.assertEqual({cell["branch_kind"] for cell in required_cells}, {
            cell["branch_kind"] for cell in coverage_matrix.REQUIRED_REJECTION_LIVENESS_CELLS
        })

        rows_by_obligation = {row["obligation_id"]: row for row in rows}
        for cell in coverage_matrix.REQUIRED_REJECTION_LIVENESS_CELLS:
            obligation_id = f"rejection_liveness.{cell['cell_id']}"
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertIn(obligation_id, rows_by_obligation)
                row = rows_by_obligation[obligation_id]
                self.assertFalse(row["live_completion_allowed"])
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_status"], "passed")
                if cell["defect_class"] in coverage_matrix.RETRY_DEFECT_CLASSES:
                    self.assertEqual(row["coverage_kind"], "synthetic_trace")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "control_flow_only")
                else:
                    self.assertEqual(row["coverage_kind"], "ordinary_runtime")
                    self.assertFalse(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "ordinary_runtime_contract")

    def test_contract_exhaustion_required_cells_have_owners(self) -> None:
        report = coverage_matrix.build_report()
        matrix_cell_ids = {
            matrix_cell["cell_id"]
            for matrix_cell in coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS
        }
        required_cells = [
            cell
            for cell in report["required_cells"]
            if cell["model_id"] == coverage_matrix.CONTRACT_EXHAUSTION_MODEL_ID
            and str(cell["obligation_id"]).startswith("contract_exhaustion.")
            and str(cell["obligation_id"]).removeprefix("contract_exhaustion.") in matrix_cell_ids
        ]
        rows = [
            row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.CONTRACT_EXHAUSTION_MODEL_ID
            and str(row["obligation_id"]).startswith("contract_exhaustion.")
            and str(row["obligation_id"]).removeprefix("contract_exhaustion.") in matrix_cell_ids
        ]

        self.assertEqual(len(required_cells), len(coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS))
        self.assertEqual(len(rows), len(required_cells))
        self.assertEqual({cell["family"] for cell in required_cells}, {
            cell["family"] for cell in coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS
        })
        self.assertEqual({cell["branch_kind"] for cell in required_cells}, {
            cell["branch_kind"] for cell in coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS
        })

        rows_by_obligation = {row["obligation_id"]: row for row in rows}
        for cell in coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS:
            obligation_id = f"contract_exhaustion.{cell['cell_id']}"
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertIn(obligation_id, rows_by_obligation)
                row = rows_by_obligation[obligation_id]
                self.assertFalse(row["live_completion_allowed"])
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_status"], "passed")
                owner = cell.get("required_evidence_owner")
                if owner == "contract_exhaustion_historical_failure_matrix":
                    self.assertEqual(row["coverage_kind"], "historical_failure_replay")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "historical_same_class_non_live_control_flow")
                    self.assertTrue(row["normal_repair_route"])
                    self.assertFalse(row["glass_break_allowed_in_acceptance"])
                    self.assertIn(str(cell["source_class"]), row["covered_failure_mode"])
                elif owner == "fake_ai_runtime_replay_matrix":
                    self.assertEqual(row["evidence_owner"], "fake_ai_runtime_replay_matrix")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertIn(row["coverage_kind"], {"synthetic_trace", "threshold_probe"})
                    self.assertIn(row["coverage_boundary"], {"control_flow_only", "glassbreak_threshold_only"})
                    self.assertEqual(row["test_name"], "test_runtime_replay_cells_bind_fake_ai_errors_to_runtime_reactions")
                elif owner == "real_issue_backfeed_matrix":
                    self.assertEqual(row["coverage_kind"], "historical_failure_replay")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "historical_same_class_non_live_control_flow")
                    self.assertEqual(row["test_name"], "test_real_issue_backfeed_registry_bridges_every_issue_to_runtime_replay")
                elif cell["mutation_kind"] in coverage_matrix.CONTRACT_EXHAUSTION_SYNTHETIC_MUTATIONS:
                    self.assertEqual(row["coverage_kind"], "synthetic_trace")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "control_flow_only")
                else:
                    self.assertEqual(row["coverage_kind"], "ordinary_runtime")
                    self.assertFalse(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "ordinary_runtime_contract")

    def test_review_window_completeness_and_fake_ai_cells_are_cartesian_rows(self) -> None:
        report = coverage_matrix.build_report()
        review_cells = [
            cell
            for cell in coverage_matrix.REQUIRED_CONTRACT_EXHAUSTION_CELLS
            if cell.get("required_evidence_owner") in {
                "review_window_completeness_matrix",
                "review_window_fake_ai_matrix",
            }
        ]
        rows_by_obligation = {
            row["obligation_id"]: row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.CONTRACT_EXHAUSTION_MODEL_ID
        }

        self.assertTrue(review_cells)
        self.assertEqual(
            {cell["required_evidence_owner"] for cell in review_cells},
            {"review_window_completeness_matrix", "review_window_fake_ai_matrix"},
        )
        flow_ids = {str(cell["review_flow_id"]) for cell in review_cells}
        fake_profile_ids = set(coverage_matrix.CONTRACT_EXHAUSTION_SYNTHETIC_MUTATIONS).intersection(
            {str(cell["mutation_kind"]) for cell in review_cells}
        )

        for cell in review_cells:
            obligation_id = f"contract_exhaustion.{cell['cell_id']}"
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertIn(obligation_id, rows_by_obligation)
                row = rows_by_obligation[obligation_id]
                self.assertFalse(row["live_completion_allowed"])
                self.assertTrue(row["evidence_current"])
                self.assertEqual(row["evidence_status"], "passed")
                if cell["required_evidence_owner"] == "review_window_completeness_matrix":
                    self.assertEqual(row["coverage_kind"], "ordinary_runtime")
                    self.assertFalse(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "ordinary_runtime_contract")
                    self.assertEqual(row["evidence_owner"], "review_window_completeness_matrix")
                    self.assertEqual(row["test_name"], "test_review_window_completeness_cells_have_runtime_owners")
                else:
                    self.assertEqual(row["coverage_kind"], "synthetic_trace")
                    self.assertTrue(row["synthetic_replay_required"])
                    self.assertEqual(row["coverage_boundary"], "control_flow_only")
                    self.assertEqual(row["evidence_owner"], "review_window_fake_ai_matrix")
                    self.assertEqual(row["test_name"], "test_review_window_fake_ai_profiles_are_cartesian_covered")

        completeness_flow_ids = {
            str(cell["review_flow_id"])
            for cell in review_cells
            if cell["required_evidence_owner"] == "review_window_completeness_matrix"
            and cell["mutation_kind"] == "missing_window_path"
        }
        fake_pairs = {
            (
                str(cell["review_flow_id"]),
                str(cell["mutation_kind"]),
                str(cell.get("material_state_class") or ""),
                str(cell.get("retry_count_class") or ""),
            )
            for cell in review_cells
            if cell["required_evidence_owner"] == "review_window_fake_ai_matrix"
        }
        material_state_classes = {
            str(cell.get("material_state_class") or "")
            for cell in review_cells
            if cell["required_evidence_owner"] == "review_window_fake_ai_matrix"
        }
        retry_count_classes = {
            str(cell.get("retry_count_class") or "")
            for cell in review_cells
            if cell["required_evidence_owner"] == "review_window_fake_ai_matrix"
        }

        self.assertLessEqual(flow_ids, completeness_flow_ids)
        self.assertGreaterEqual(len(material_state_classes), 5)
        self.assertGreaterEqual(len(retry_count_classes), 4)
        for flow_id in flow_ids:
            for profile_id in fake_profile_ids:
                for material_state in material_state_classes:
                    for retry_class in retry_count_classes:
                        self.assertIn((flow_id, profile_id, material_state, retry_class), fake_pairs)

    def test_review_window_completeness_cells_have_runtime_owners(self) -> None:
        self.test_review_window_completeness_and_fake_ai_cells_are_cartesian_rows()

    def test_review_window_fake_ai_profiles_are_cartesian_covered(self) -> None:
        self.test_review_window_completeness_and_fake_ai_cells_are_cartesian_rows()

    def test_cartesian_exhaustion_required_cells_have_owners(self) -> None:
        report = coverage_matrix.build_report()
        matrix_cell_ids = {
            matrix_cell["cell_id"]
            for matrix_cell in coverage_matrix.REQUIRED_CARTESIAN_CELLS
        }
        required_cells = [
            cell
            for cell in report["required_cells"]
            if cell["model_id"] == coverage_matrix.CARTESIAN_EXHAUSTION_MODEL_ID
            and str(cell["obligation_id"]).startswith("cartesian_exhaustion.")
            and str(cell["obligation_id"]).removeprefix("cartesian_exhaustion.") in matrix_cell_ids
        ]
        rows = [
            row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.CARTESIAN_EXHAUSTION_MODEL_ID
            and str(row["obligation_id"]).startswith("cartesian_exhaustion.")
            and str(row["obligation_id"]).removeprefix("cartesian_exhaustion.") in matrix_cell_ids
        ]

        self.assertEqual(len(required_cells), len(coverage_matrix.REQUIRED_CARTESIAN_CELLS))
        self.assertEqual(len(rows), len(required_cells))
        rows_by_obligation = {row["obligation_id"]: row for row in rows}
        self.assertGreater(len(rows_by_obligation), 7000)
        for cell in coverage_matrix.REQUIRED_CARTESIAN_CELLS:
            obligation_id = f"cartesian_exhaustion.{cell['cell_id']}"
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertIn(obligation_id, rows_by_obligation)
                row = rows_by_obligation[obligation_id]
                self.assertEqual(row["evidence_owner"], cell["required_evidence_owner"])
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertFalse(row["live_completion_allowed"])
                self.assertEqual(row["glass_break_allowed"], cell["glass_break_allowed"])
                self.assertEqual(
                    row["contract_combination_case_id"],
                    cell["contract_combination_case_id"],
                )
                self.assertEqual(row["coverage_shard_id"], cell["coverage_shard_id"])
                self.assertEqual(row["coverage_receipt_id"], cell["coverage_receipt_id"])
                if cell["expected_reaction"] == "glassbreak_alarm":
                    self.assertEqual(row["coverage_kind"], "threshold_probe")
                    self.assertEqual(row["coverage_boundary"], "glassbreak_threshold_only")
                    self.assertTrue(row["synthetic_replay_required"])
                elif cell["context"] == "synthetic_ai_rehearsal":
                    self.assertEqual(row["coverage_kind"], "synthetic_trace")
                    self.assertEqual(row["coverage_boundary"], "control_flow_only")
                    self.assertTrue(row["synthetic_replay_required"])
                else:
                    self.assertEqual(row["coverage_kind"], "ordinary_runtime")
                    self.assertEqual(row["coverage_boundary"], "ordinary_runtime_contract")
                    self.assertFalse(row["synthetic_replay_required"])

    def test_current_contract_cartesian_summary_is_wired_without_live_ai_claim(self) -> None:
        report = coverage_matrix.build_report()
        rows = [
            row
            for row in report["rows"]
            if row["model_id"] == coverage_matrix.CURRENT_CONTRACT_CARTESIAN_MODEL_ID
        ]

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["branch_kind"], "full_matrix_runner")
        self.assertEqual(row["coverage_kind"], "model_matrix")
        self.assertFalse(row["live_completion_allowed"])
        self.assertEqual(row["coverage_boundary"], "model_only_current_contract_cartesian_summary")
        self.assertIn(
            str(coverage_matrix.CURRENT_CONTRACT_CARTESIAN_COUNTS["required_cell_count"]),
            row["covered_failure_mode"],
        )
        self.assertIn("model_only_not_runtime_replay", row["covered_failure_mode"])

    def test_executable_bridge_summary_is_wired_without_live_ai_claim(self) -> None:
        report = coverage_matrix.build_report()
        bridge = report["executable_bridge"]

        self.assertTrue(bridge["ok"], bridge)
        self.assertEqual(bridge["model_id"], coverage_matrix.EXECUTABLE_MATRIX_COVERAGE_MODEL_ID)
        self.assertGreaterEqual(bridge["row_count"], bridge["required_miss_family_count"])
        self.assertGreater(bridge["ordinary_recovery_row_count"], 0)
        self.assertGreater(bridge["break_glass_safety_fuse_row_count"], 0)
        self.assertFalse(bridge["live_ai_semantic_quality_proven"])
        self.assertFalse(bridge["product_completion_proven"])
        self.assertEqual(bridge["missing_miss_families"], [])

    def test_p0_p1_required_branches_have_synthetic_replay_or_reason(self) -> None:
        report = coverage_matrix.build_report()
        high_risk_rows = [
            row
            for row in report["rows"]
            if row["risk_tier"] in coverage_matrix.REPLAY_REQUIRED_RISK_TIERS
            and row["synthetic_replay_required"] is True
        ]
        evidence_ids = {row["evidence_id"] for row in high_risk_rows}

        self.assertGreaterEqual(len(high_risk_rows), 21)
        self.assertLessEqual(
            {
                "synthetic.control_blocker.failure.retry_budget_pm_escalation",
                "synthetic.control_blocker.happy.pm_repair_target_accepted",
                "synthetic.control_blocker.negative.invalid_pm_repair_target",
                "synthetic.control_blocker.negative.fatal_ordinary_waiver_rejected",
                "synthetic.resume.failure.active_blocker_or_ambiguous_state",
                "synthetic.route_mutation.negative.stale_sibling_proof",
                "synthetic.role_output.negative.pm_disposition_authority",
                "synthetic.controller.failure.boundary_repair_budget_escalation",
                "synthetic.material.negative.active_generation_blocks_stale_flags",
                "synthetic.terminal.negative.dirty_pm_suggestion_ledger",
                "systemic.valid_envelope_bad_content.pm_repair_self_check",
                "systemic.stacked_blockers.control_preempts_dirty_ledger",
                "systemic.pm_repair_loop.followup_blocker",
                "systemic.restart.stale_state_preserves_active_blocker",
                "systemic.parallel.peer_run_stop_isolated",
                "systemic.terminal.total_gate_dirty_sources",
            },
            evidence_ids,
        )
        for row in high_risk_rows:
            with self.subTest(evidence_id=row["evidence_id"]):
                self.assertIn(row["synthetic_replay_status"], {"present", "not_replayable"})
                if row["synthetic_replay_status"] == "present":
                    self.assertIn(row["coverage_kind"], coverage_matrix.SYNTHETIC_NON_LIVE_KINDS)
                else:
                    self.assertTrue(row.get("non_replayable_reason"))
                self.assertTrue(row["covered_failure_mode"])

    def test_system_level_rows_name_recovery_loop_and_terminal_expectation(self) -> None:
        report = coverage_matrix.build_report()
        system_rows = [
            row
            for row in report["rows"]
            if row["story_level"] == "system"
        ]
        evidence_ids = {row["evidence_id"] for row in system_rows}

        self.assertEqual(len(system_rows), 7)
        self.assertLessEqual(
            {
                "synthetic.core_deliverable.negative.downgrade_chain",
                "systemic.valid_envelope_bad_content.pm_repair_self_check",
                "systemic.stacked_blockers.control_preempts_dirty_ledger",
                "systemic.pm_repair_loop.followup_blocker",
                "systemic.restart.stale_state_preserves_active_blocker",
                "systemic.parallel.peer_run_stop_isolated",
                "systemic.terminal.total_gate_dirty_sources",
            },
            evidence_ids,
        )
        for row in system_rows:
            with self.subTest(evidence_id=row["evidence_id"]):
                self.assertEqual(row["coverage_kind"], "synthetic_trace")
                self.assertTrue(row["recovery_loop"])
                self.assertGreaterEqual(len(row["story_steps"]), 2)
                self.assertIn(row["terminal_expectation"], coverage_matrix.SYSTEM_TERMINAL_EXPECTATIONS)
                self.assertFalse(row["live_completion_allowed"])

    def test_route_resume_and_role_authority_branches_are_explicit_rows(self) -> None:
        rows = {
            (
                row["model_id"],
                row["obligation_id"],
                row["branch_kind"],
                row["evidence_id"],
            )
            for row in coverage_matrix.build_report()["rows"]
        }

        for expected in (
            (
                "route_mutation",
                "route_mutation.sibling_replacement_stales_old_evidence",
                "negative_path",
                "runtime.route_mutation.negative.old_sibling_proof",
            ),
            (
                "flowpilot_route_authority_singularity",
                "route_authority.corrected_retry_changes_packet_shape",
                "replay_path",
                "synthetic.route_authority.replay.wrong_path_corrected_retry",
            ),
            (
                "terminal_closure_resume",
                "resume.current_run_reentry",
                "failure_path",
                "runtime.resume.failure.ambiguous_state",
            ),
            (
                "role_output_contracts",
                "role_output.registry_authority",
                "negative_path",
                "runtime.role_output.negative.wrong_role",
            ),
            (
                "packet_result_family",
                "packet_result_family.clean_e2e_authorized_material_openings",
                "replay_path",
                "runtime.clean_e2e.replay.required_authorized_materials_opened",
            ),
            (
                "packet_result_family",
                "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                "edge_path",
                "runtime.flowguard_reissue.edge.inherited_authorized_reads",
            ),
            (
                "packet_result_family",
                "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                "edge_path",
                "runtime.flowguard_reissue.edge.semantic_recheck_missing_inherits_authorized_reads",
            ),
            (
                "packet_result_family",
                "packet_result_family.flowguard_reissue_preserves_required_authorized_result_reads",
                "negative_path",
                "runtime.flowguard_reissue.negative.inherited_body_not_opened",
            ),
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, rows)

    def test_known_bad_matrix_cases_reject_false_confidence_hazards(self) -> None:
        for case in coverage_matrix.known_bad_cases():
            with self.subTest(case=case["name"]):
                findings = coverage_matrix.validate_coverage_rows(
                    case["rows"],
                    case["required_cells"],
                )
                finding_codes = {finding["code"] for finding in findings}
                self.assertLessEqual(set(case["expected_codes"]), finding_codes)


if __name__ == "__main__":
    unittest.main()
