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


runtime_replay = load_module(
    "flowpilot_fake_ai_runtime_replay_model",
    ROOT / "simulations" / "flowpilot_fake_ai_runtime_replay_model.py",
)
runner = load_module(
    "run_flowpilot_fake_ai_runtime_replay_checks",
    ROOT / "simulations" / "run_flowpilot_fake_ai_runtime_replay_checks.py",
)

ASSETS_PATH = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_PATH) not in sys.path:
    sys.path.insert(0, str(ASSETS_PATH))
from flowpilot_core_runtime import review_window_contracts  # noqa: E402


class FlowPilotFakeAIRuntimeReplayTests(unittest.TestCase):
    def test_fake_ai_runtime_replay_runner_accepts_valid_and_rejects_hazards(self) -> None:
        report = runner.run_checks()

        self.assertTrue(report["ok"], report)
        self.assertEqual(report["model_id"], runtime_replay.MODEL_ID)
        self.assertTrue(report["flowguard"]["ok"], report["flowguard"])
        self.assertTrue(report["walk"]["ok"], report["walk"])
        self.assertTrue(report["hazards"]["ok"], report["hazards"])
        self.assertEqual(report["matrix"]["findings"], [])

    def test_runtime_replay_cells_bind_fake_ai_errors_to_runtime_reactions(self) -> None:
        cells = list(runtime_replay.runtime_replay_cells())
        mutations = {str(cell["mutation_kind"]) for cell in cells}
        reactions = {str(cell["expected_runtime_reaction"]) for cell in cells}
        attempt_classes = {str(cell["attempt_class"]) for cell in cells}

        self.assertGreater(len(cells), 400)
        for profile_id in runtime_replay.MALFORMED_BODY_PROFILE_IDS:
            self.assertIn(f"malformed_body.{profile_id}", mutations)
        for mutation in (
            "missing_required_field",
            "missing_required_child_field",
            "wrong_type",
            "wrong_allowed_value",
            "forbidden_alias_used",
            "hidden_projection_gap",
            "finite_option_mistake",
            "missing_active_id_coverage",
            "corrected_second_retry",
            "same_payload_retry",
            "submit_result.accepted_packet_resubmit",
            "submit_result.noncurrent_packet_submit",
            "submit_result.closed_lease_submit",
            "submit_result.stale_route_submit",
            "submit_result.duplicate_current_lease_submit",
            "review_packet.result_ids_tail_after_accepted_result",
            "reviewer.semantic_keyword_gate_attempt",
            "reviewer.prompt_omits_active_verification",
        ):
            with self.subTest(mutation=mutation):
                self.assertIn(mutation, mutations)
        for profile_id in (
            "reviewer_quality_score_10_exceeds_standard",
            "reviewer_quality_score_6_soft_pm_optimization",
            "reviewer_quantitative_gap_blocks",
            "reviewer_overblocks_sub9_soft_score",
            "reviewer_recheck_consumes_score_context",
        ):
            with self.subTest(profile_id=profile_id):
                self.assertIn(profile_id, mutations)
        for mutation in (
            "flat_checklist_route",
            "child_outputs_do_not_compose",
            "final_output_scattered",
            "optimization_incorrectly_hard_blocked",
            "model_miss_not_triggered",
            "hard_gate_escape.missing_node_acceptance_plan",
            "hard_gate_escape.missing_node_context_package",
            "hard_gate_escape.missing_parent_backward_replay",
            "hard_gate_escape.missing_pm_disposition",
            "hard_gate_escape.active_packet_unresolved",
            "hard_gate_escape.stale_current_evidence",
        ):
            with self.subTest(integration_mutation=mutation):
                self.assertIn(mutation, mutations)
        for reaction in (
            "mechanical_reject_reissue_with_strict_json_feedback",
            "mechanical_reject_reissue_with_options",
            "mechanical_reject_reissue_with_exact_field",
            "accepted_after_reissue",
            "same_family_repair_or_reissue_without_glassbreak_before_threshold",
            "breakglass_after_fifth_same_failure",
            "pm_route_mutation_for_integration",
            "pm_integration_suggestion_without_runtime_blocker",
            "terminal_composition_block_from_existing_gate",
            "pm_model_miss_triage",
            "return_to_pm_node_acceptance_plan",
            "return_to_parent_backward_replay",
            "return_to_pm_disposition",
            "return_to_current_packet_repair",
            "hard_reject_before_result_allocation",
            "accepted_result_id_authority_preserved",
            "runtime_mechanical_only_reviewer_boundary",
            "reviewer_prompt_requires_active_verification_without_new_fields",
        ):
            with self.subTest(reaction=reaction):
                self.assertIn(reaction, reactions)
        self.assertLessEqual(
            {"first_failure", "corrected_second_attempt", "same_failure_attempts_1_to_4", "same_failure_attempt_5"},
            attempt_classes,
        )
        for cell in cells:
            with self.subTest(cell_id=cell["cell_id"]):
                self.assertEqual(cell["required_evidence_owner"], runtime_replay.REQUIRED_EVIDENCE_OWNER)
                self.assertFalse(cell["live_completion_allowed"])
                if cell["expected_runtime_reaction"] == "breakglass_after_fifth_same_failure":
                    self.assertEqual(cell["attempt_class"], "same_failure_attempt_5")
                    self.assertTrue(cell["glass_break_allowed"])
                else:
                    self.assertFalse(cell["glass_break_allowed"])

    def test_fake_ai_runtime_replay_includes_system_integration_cases(self) -> None:
        integration_cells = [
            cell
            for cell in runtime_replay.runtime_replay_cells()
            if cell["source_matrix"] == "integration_cartesian_coverage"
        ]
        reactions = {cell["expected_runtime_reaction"] for cell in integration_cells}
        mutation_kinds = {cell["mutation_kind"] for cell in integration_cells}

        self.assertGreaterEqual(len(integration_cells), 100)
        self.assertLessEqual(
            {
                "missing_integration_intent",
                "flat_checklist_route",
                "child_outputs_do_not_compose",
                "final_output_scattered",
                "optimization_incorrectly_hard_blocked",
                "model_miss_not_triggered",
            },
            mutation_kinds,
        )
        self.assertLessEqual(
            {
                "continue_current_flow_without_runtime_blocker",
                "pm_integration_suggestion_without_runtime_blocker",
                "pm_same_node_integration_repair",
                "pm_route_mutation_for_integration",
                "terminal_composition_block_from_existing_gate",
                "pm_model_miss_triage",
            },
            reactions,
        )
        self.assertFalse([cell["cell_id"] for cell in integration_cells if cell["semantic_runtime_blocker_allowed"]])
        self.assertFalse([cell["cell_id"] for cell in integration_cells if cell["worker_current_gate_blocker_allowed"]])

    def test_system_integration_replay_hazards_are_explicit(self) -> None:
        expected = runtime_replay.expected_failures_by_hazard()

        self.assertEqual(
            expected["integration_hard_underblocked"],
            ("hard_integration_failure_lacked_pm_disposition",),
        )
        self.assertEqual(
            expected["integration_advisory_runtime_overblock"],
            ("advisory_integration_finding_became_runtime_hard_blocker",),
        )
        self.assertEqual(
            expected["integration_worker_current_gate_blocker"],
            ("worker_claimed_current_gate_blocker_for_integration",),
        )
        self.assertEqual(
            expected["integration_model_miss_without_triage"],
            ("integration_model_miss_candidate_lacked_triage",),
        )
        self.assertEqual(
            expected["hard_gate_escape_not_returned_to_owner"],
            ("hard_gate_escape_did_not_return_to_owner_gate",),
        )
        self.assertEqual(
            expected["hard_gate_escape_entered_breakglass"],
            ("hard_gate_escape_entered_breakglass",),
        )
        self.assertEqual(
            expected["hard_gate_escape_entered_final_quality_review"],
            ("hard_gate_escape_entered_final_quality_review",),
        )

    def test_parent_entry_return_path_replay_is_cartesian(self) -> None:
        cells = [
            cell
            for cell in runtime_replay.runtime_replay_cells()
            if cell["source_matrix"] == "parent_entry_return_path_cartesian"
        ]
        keys = {
            (
                cell["gate_type"],
                cell["subject_topology"],
                cell["detection_stage"],
            )
            for cell in cells
        }
        expected_count = (
            len(runtime_replay.PARENT_ENTRY_GATE_TYPES)
            * len(runtime_replay.PARENT_ENTRY_SUBJECT_TOPOLOGIES)
            * len(runtime_replay.PARENT_ENTRY_DETECTION_STAGES)
        )

        self.assertEqual(len(cells), expected_count)
        self.assertEqual(len(keys), expected_count)
        self.assertFalse([cell["cell_id"] for cell in cells if cell["glass_break_allowed"]])
        self.assertFalse([cell["cell_id"] for cell in cells if cell["fallback_allowed"]])
        self.assertFalse([cell["cell_id"] for cell in cells if cell["final_quality_review_allowed"]])
        reactions = {cell["expected_runtime_reaction"] for cell in cells}
        self.assertLessEqual(
            {
                "return_to_pm_node_acceptance_plan",
                "return_to_parent_backward_replay",
                "return_to_pm_disposition",
                "return_to_current_packet_repair",
            },
            reactions,
        )

    def test_pm_break_glass_branches_are_in_fake_ai_runtime_replay_matrix(self) -> None:
        cells = list(runtime_replay.runtime_replay_cells())
        branch_cells = [
            cell
            for cell in cells
            if cell["contract_family_id"]
            in {
                "pm_repair_decision.pm_repair_decision",
                "pm_flowguard_acceptance.pm_flowguard_acceptance",
            }
            and "break_glass" in str(cell).lower()
        ]

        self.assertGreater(len(branch_cells), 0)
        families = {cell["contract_family_id"] for cell in branch_cells}
        self.assertEqual(
            families,
            {
                "pm_repair_decision.pm_repair_decision",
                "pm_flowguard_acceptance.pm_flowguard_acceptance",
            },
        )
        reactions = {cell["expected_runtime_reaction"] for cell in branch_cells}
        self.assertIn("mechanical_reject_reissue", reactions)
        self.assertIn("accepted_after_reissue", reactions)
        self.assertTrue(
            any(
                "repair_obligation_disposition" in str(cell.get("contract_path", ""))
                for cell in branch_cells
            )
        )

    def test_review_window_fake_ai_runtime_replay_is_cartesian(self) -> None:
        cells = [
            cell
            for cell in runtime_replay.runtime_replay_cells()
            if cell["source_matrix"] == "review_window_fake_ai_responder"
        ]
        keys = {
            (
                cell["contract_family_id"],
                cell["mutation_kind"],
                cell["attempt_class"],
            )
            for cell in cells
        }
        expected_count = (
            len(review_window_contracts.review_flow_ids())
            * len(review_window_contracts.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS)
            * len(review_window_contracts.REVIEW_WINDOW_MATERIAL_STATE_CLASSES)
            * len(review_window_contracts.RETRY_COUNT_CLASSES)
        )

        self.assertEqual(len(cells), expected_count)
        for flow_id in review_window_contracts.review_flow_ids():
            for profile_id in review_window_contracts.REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
                for retry_class in review_window_contracts.RETRY_COUNT_CLASSES:
                    with self.subTest(flow_id=flow_id, profile_id=profile_id, retry_class=retry_class):
                        if profile_id == "corrected_second_reviewer_retry" or retry_class == "corrected_second_attempt":
                            attempt_class = "corrected_second_attempt"
                        elif profile_id == "same_review_failure_attempt_5_break_glass" or retry_class == "same_failure_attempt_5":
                            attempt_class = "same_failure_attempt_5"
                        elif retry_class == "same_failure_attempts_1_to_4":
                            attempt_class = "same_failure_attempts_1_to_4"
                        else:
                            attempt_class = "first_failure"
                        self.assertIn((flow_id, profile_id, attempt_class), keys)


if __name__ == "__main__":
    unittest.main()
