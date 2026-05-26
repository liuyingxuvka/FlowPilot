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
        trace_test_text = (ROOT / "tests" / "test_flowpilot_synthetic_agent_trace_replay.py").read_text(
            encoding="utf-8"
        )
        synthetic_rows = [
            row
            for row in report["rows"]
            if row["coverage_kind"] in coverage_matrix.SYNTHETIC_NON_LIVE_KINDS
        ]

        self.assertGreaterEqual(len(synthetic_rows), 22)
        for row in synthetic_rows:
            with self.subTest(evidence_id=row["evidence_id"]):
                self.assertFalse(row["live_completion_allowed"])
                self.assertIn(row["coverage_boundary"], {
                    "control_flow_only",
                    "non_live_evidence_disclosure_only",
                    "background_final_artifact_contract",
                })
                self.assertIn(row["test_name"], trace_test_text)
                self.assertEqual(row["evidence_status"], "passed")
                self.assertTrue(row["evidence_current"])
                self.assertIn(row["story_level"], {"local", "system"})

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

        self.assertEqual(len(system_rows), 6)
        self.assertLessEqual(
            {
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
