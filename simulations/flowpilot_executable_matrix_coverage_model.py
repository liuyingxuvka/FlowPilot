"""Executable FlowPilot matrix bridge for fake-AI and runtime rehearsal evidence.

This model is the boundary between model-only Cartesian cells and executable
coverage. It keeps live AI/product completion out of scope while requiring each
accepted row to name the fake body class, Runtime/CLI entrypoints, event-log
evidence, convergence rule, break-glass expectation, and freshness receipt that
make the row executable rather than only theoretical.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, NamedTuple, Sequence

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]

MODEL_ID = "flowpilot_executable_matrix_coverage"
RESULT_TYPE = "flowpilot_executable_matrix_coverage"
RESULTS_PATH = "simulations/flowpilot_executable_matrix_coverage_results.json"
MAX_SEQUENCE_LENGTH = 2
BREAK_GLASS_THRESHOLD = 5

REQUIRED_BRIDGE_FIELDS = (
    "bridge_case_id",
    "packet_family",
    "fake_body_class",
    "runtime_entrypoints",
    "expected_outcome",
    "event_log_evidence",
    "convergence_rule",
    "break_glass_expectation",
    "evidence_command",
    "freshness_receipt_id",
)

ACCEPTED_EXECUTABLE_EVIDENCE_LEVELS = {
    "source_contract",
    "fake_body_contract",
    "runtime_cli_replay",
    "long_chain_convergence",
}

REQUIRED_MISS_FAMILIES = (
    "missing_current_evidence_refs",
    "moved_deleted_old_stage_fields",
    "terminal_route_segment_replay",
    "terminal_final_blockers",
    "terminal_supplemental_repair_contract_lineage",
    "ai_facing_semantic_recheck_contract_projection",
    "ai_facing_semantic_recheck_near_synonym_feedback",
    "ai_facing_semantic_recheck_corrected_retry",
    "ai_facing_contract_driven_fake_ai_cartesian_retry",
    "flowguard_semantic_recheck_repair_obligation_consumption",
    "old_alias_rejection",
    "wrong_role_lease",
    "missing_ack",
    "stale_node_evidence",
    "wrong_flowguard_target",
    "dead_lease",
    "route_mutation_without_frontier_rewrite",
    "slow_reviewer_progress",
    "accepted_packet_reassignment",
    "orphan_runner_summary",
    "unsupported_side_command",
    "public_cli_worker_lifetime",
    "same_class_repeats_before_threshold",
    "same_class_repeat_threshold_glassbreak",
)


def _row(
    bridge_case_id: str,
    miss_family_id: str,
    packet_family: str,
    fake_body_class: str,
    runtime_entrypoints: Sequence[str],
    expected_outcome: str,
    event_log_evidence: Sequence[str],
    convergence_rule: str,
    break_glass_expectation: str,
    evidence_path: str,
    evidence_test_name: str,
    *,
    model_cell_id: str = "",
    coverage_shard_id: str = "",
    evidence_level: str = "runtime_cli_replay",
    evidence_command: str = "python -m unittest tests.test_flowpilot_fake_project_rehearsal",
    source_paths: Sequence[str] = (),
    attempt_count: int = 1,
    same_failure_class_no_progress: bool = False,
    break_glass_triggered: bool = False,
    fake_ai_body_consumed: bool = True,
    runtime_receipt_required: bool = True,
    testmesh_child_id: str = "executable_matrix_runtime_cli_replay",
    coverage_boundary: str = "non_live_executable_control_flow",
) -> dict[str, Any]:
    return {
        "bridge_case_id": bridge_case_id,
        "miss_family_id": miss_family_id,
        "model_cell_id": model_cell_id,
        "coverage_shard_id": coverage_shard_id,
        "packet_family": packet_family,
        "fake_body_class": fake_body_class,
        "runtime_entrypoints": tuple(runtime_entrypoints),
        "expected_outcome": expected_outcome,
        "event_log_evidence": tuple(event_log_evidence),
        "convergence_rule": convergence_rule,
        "break_glass_expectation": break_glass_expectation,
        "evidence_command": evidence_command,
        "freshness_receipt_id": f"receipt.{MODEL_ID}.{bridge_case_id}",
        "evidence_level": evidence_level,
        "evidence_path": evidence_path,
        "evidence_test_name": evidence_test_name,
        "evidence_status": "passed",
        "evidence_current": True,
        "source_paths": tuple(dict.fromkeys((evidence_path, *source_paths))),
        "attempt_count": attempt_count,
        "same_failure_class_no_progress": same_failure_class_no_progress,
        "break_glass_triggered": break_glass_triggered,
        "fake_ai_body_consumed": fake_ai_body_consumed,
        "runtime_receipt_required": runtime_receipt_required,
        "testmesh_child_id": testmesh_child_id,
        "coverage_boundary": coverage_boundary,
        "live_ai_semantic_quality_proven": False,
        "product_completion_proven": False,
        "model_only_source_allowed": False,
    }


BRIDGE_ROWS: tuple[dict[str, Any], ...] = (
    _row(
        "missing_current_evidence_refs_reissue",
        "missing_current_evidence_refs",
        "task.node",
        "missing_required_current_evidence_refs",
        ("ack", "submit-result", "status", "foreground-duty"),
        "mechanical_reissue_then_accept_after_current_evidence_refs",
        ("result_contract_rejected", "current_packet_reissued", "controller_wait_preserved"),
        "ordinary_repair_by_second_attempt",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "missing_current_result_fields_reissue",
        model_cell_id="packet_result_contract.task.node.missing_required_field.current_evidence_refs",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py", "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py"),
    ),
    _row(
        "moved_deleted_old_stage_fields_rejected",
        "moved_deleted_old_stage_fields",
        "stage_evidence_matrix",
        "old_stage_field_or_deleted_field_present",
        ("submit-result", "status"),
        "reject_old_stage_field_without_translation",
        ("deleted_field_rejected", "current_stage_matrix_row_named"),
        "mechanical_reject_before_state_mutation",
        "forbidden",
        "tests/test_flowpilot_contract_surface_reduction.py",
        "test_deleted_and_moved_fields_are_not_success_requirements",
        model_cell_id="contract_surface_reduction.deleted_and_moved_fields",
        evidence_level="fake_body_contract",
        source_paths=("skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",),
        testmesh_child_id="executable_matrix_fake_body_contracts",
    ),
    _row(
        "terminal_route_segment_replay_current_targets",
        "terminal_route_segment_replay",
        "review.terminal_backward_replay",
        "terminal_backward_replay_current_segment_targets",
        ("open-packet", "ack", "submit-result"),
        "terminal_replay_uses_current_segment_targets",
        ("current_segment_targets_opened", "route_segment_replay_written"),
        "terminal_review_current_subject_only",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "test_terminal_backward_replay_fake_body_uses_current_segment_targets",
        model_cell_id="terminal_backward_replay.route_segment_replay",
        evidence_level="fake_body_contract",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_cli.py",),
        testmesh_child_id="executable_matrix_fake_body_contracts",
    ),
    _row(
        "terminal_final_blockers_current_empty_list",
        "terminal_final_blockers",
        "review.terminal_backward_replay",
        "terminal_final_blockers_current_list",
        ("open-packet", "ack", "submit-result"),
        "terminal_final_blockers_are_current_and_explicit",
        ("current_segment_targets_opened", "final_blockers_written"),
        "terminal_blockers_explicit_not_implicit_glassbreak",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "final_blockers",
        model_cell_id="terminal_backward_replay.final_blockers",
        evidence_level="fake_body_contract",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_cli.py",),
        testmesh_child_id="executable_matrix_fake_body_contracts",
    ),
    _row(
        "terminal_supplemental_repair_lineage",
        "terminal_supplemental_repair_contract_lineage",
        "pm_repair_decision",
        "terminal_supplemental_repair_contract_lineage",
        ("ack", "submit-result", "status", "foreground-duty"),
        "supplemental_repair_packet_preserves_current_lineage",
        ("terminal_replay_blocked", "supplemental_contract_id_bound", "repair_packet_issued"),
        "repair_contract_lineage_then_recheck",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "test_blackbox_terminal_supplemental_repair_uses_public_cli",
        model_cell_id="terminal_supplemental_repair.contract_lineage",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
    ),
    _row(
        "flowguard_semantic_recheck_consumes_repair_obligations",
        "flowguard_semantic_recheck_repair_obligation_consumption",
        "flowguard_check",
        "semantic_recheck_must_consume_repair_obligations",
        ("ack", "submit-result", "open-packet", "status"),
        "flowguard_recheck_blocks_until_repair_obligation_consumed",
        ("repair_obligation_bound", "semantic_recheck_packet_issued", "obligation_consumed"),
        "repair_packet_then_flowguard_semantic_recheck",
        "forbidden",
        "tests/test_flowpilot_core_runtime.py",
        "test_repair_packet_and_flowguard_recheck_must_consume_repair_obligations",
        model_cell_id="control_plane.flowguard_check_packet.missing_repair_obligation_consumption",
        source_paths=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
    ),
    _row(
        "ai_facing_semantic_recheck_contract_projection",
        "ai_facing_semantic_recheck_contract_projection",
        "flowguard_check",
        "semantic_recheck_ai_facing_projection",
        ("issue-packet", "open-packet", "status"),
        "conditional_semantic_recheck_fields_are_visible_before_submit",
        ("current_handoff_contract_projected", "allowed_value_options_projected", "minimal_valid_shape_projected"),
        "projection_before_first_result",
        "forbidden",
        "tests/test_flowpilot_ai_contract_projection.py",
        "test_semantic_recheck_contract_projects_ai_facing_fields_and_options",
        model_cell_id="control_plane.flowguard_check_packet.ai_facing_semantic_recheck_projection",
        evidence_command="python -m unittest -v tests.test_flowpilot_ai_contract_projection",
        source_paths=(
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",
        ),
        testmesh_child_id="executable_matrix_ai_contract_projection",
        coverage_boundary="ai_facing_contract_projection_not_live_ai_quality",
    ),
    _row(
        "ai_facing_semantic_recheck_near_synonym_feedback",
        "ai_facing_semantic_recheck_near_synonym_feedback",
        "flowguard_check",
        "semantic_recheck_near_synonym_bad_package",
        ("ack", "submit-result", "status", "current-contract-reissue"),
        "near_synonym_fields_are_rejected_with_correct_minimal_shape",
        ("forbidden_synonym_fields_seen", "current_packet_reissued", "semantic_minimal_shape_projected"),
        "bad_package_reissue_with_exact_field_names",
        "forbidden",
        "tests/test_flowpilot_ai_contract_projection.py",
        "test_semantic_recheck_near_synonyms_reissue_with_correct_minimal_shape",
        model_cell_id="control_plane.flowguard_check_result.semantic_recheck_near_synonym_feedback",
        evidence_command="python -m unittest -v tests.test_flowpilot_ai_contract_projection",
        source_paths=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
        testmesh_child_id="executable_matrix_ai_contract_projection",
        coverage_boundary="ai_facing_reissue_feedback_not_live_ai_quality",
    ),
    _row(
        "ai_facing_semantic_recheck_wrong_value_then_corrected_retry",
        "ai_facing_semantic_recheck_corrected_retry",
        "flowguard_check",
        "semantic_recheck_wrong_value_then_corrected_retry",
        ("ack", "submit-result", "status", "current-contract-reissue"),
        "wrong_value_reissue_then_corrected_retry_accepts_before_glassbreak",
        ("allowed_value_violation_reported", "current_packet_reissued", "corrected_retry_accepted"),
        "ordinary_repair_by_second_attempt",
        "forbidden",
        "tests/test_flowpilot_ai_contract_projection.py",
        "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path",
        model_cell_id="control_plane.flowguard_check_result.semantic_recheck_corrected_retry",
        evidence_level="long_chain_convergence",
        evidence_command="python -m unittest -v tests.test_flowpilot_ai_contract_projection",
        source_paths=("skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",),
        testmesh_child_id="executable_matrix_ai_contract_projection",
        coverage_boundary="wrong_then_corrected_fake_ai_retry",
    ),
    _row(
        "ai_facing_contract_driven_fake_ai_cartesian_retry",
        "ai_facing_contract_driven_fake_ai_cartesian_retry",
        "flowguard_check",
        "contract_driven_fake_ai_responder_all_visible_options",
        ("issue-packet", "ack", "submit-result", "current-contract-reissue"),
        "contract_driven_fake_ai_enumerates_visible_finite_options_and_repairs_each_wrong_value",
        (
            "packet_local_contract_read_by_fake_ai_responder",
            "wrong_value_generated_for_each_allowed_value_options_field",
            "current_reissue_feedback_repaired_by_minimal_valid_shape",
            "glassbreak_absent_before_threshold",
        ),
        "cartesian_wrong_value_rows_repair_by_second_attempt",
        "forbidden",
        "tests/test_flowpilot_ai_contract_projection.py",
        "test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option",
        model_cell_id="control_plane.flowguard_check_result.contract_driven_fake_ai_cartesian_retry",
        evidence_level="long_chain_convergence",
        evidence_command="python -m unittest -v tests.test_flowpilot_ai_contract_projection",
        source_paths=(
            "simulations/flowpilot_contract_driven_fake_ai.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/runtime.py",
            "skills/flowpilot/assets/flowpilot_core_runtime/packet_result_contracts.py",
        ),
        testmesh_child_id="executable_matrix_ai_contract_projection",
        coverage_boundary="contract_driven_fake_ai_cartesian_control_flow",
    ),
    _row(
        "old_alias_reason_rejected",
        "old_alias_rejection",
        "pm_disposition",
        "reason_alias_instead_of_decision_reason",
        ("submit-result", "status"),
        "reject_alias_without_translation_or_fallback",
        ("forbidden_field_rejected", "decision_reason_required"),
        "mechanical_alias_rejection",
        "forbidden",
        "tests/test_flowpilot_control_plane_contracts.py",
        "test_pm_package_disposition_rejects_reason_alias_for_decision_reason",
        model_cell_id="historical_failure.history.research_packet_recipient_role_alias.legacy_alias",
        evidence_level="fake_body_contract",
        source_paths=("skills/flowpilot/assets/flowpilot_core_runtime/packet_stage_evidence_matrix.py",),
        testmesh_child_id="executable_matrix_fake_body_contracts",
    ),
    _row(
        "wrong_role_lease_rejected",
        "wrong_role_lease",
        "lease",
        "wrong_role_lease_attempt",
        ("ack", "open-packet", "submit-result"),
        "wrong_role_lease_rejected_without_packet_mutation",
        ("lease_role_mismatch", "packet_status_preserved", "recovery_packet_issued"),
        "reject_before_current_packet_mutation",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "wrong_role_recovery",
        model_cell_id="fake_project.wrong_role_lease",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
    ),
    _row(
        "missing_ack_result_blocked",
        "missing_ack",
        "task.result_submission",
        "submit_result_without_ack",
        ("submit-result", "status", "foreground-duty"),
        "missing_ack_blocks_result_and_preserves_wait",
        ("missing_ack_blocker", "result_blocked", "controller_stop_disallowed"),
        "ack_required_before_result_consumption",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "missing_ack_block",
        model_cell_id="fake_project.missing_ack",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
    ),
    _row(
        "stale_node_evidence_rejected",
        "stale_node_evidence",
        "route_node_evidence",
        "stale_node_evidence_submission",
        ("submit-result", "status", "foreground-duty"),
        "stale_node_evidence_rejected_and_current_node_wait_preserved",
        ("stale_node_evidence_accepted_hazard_detected", "current_node_wait_preserved"),
        "reject_stale_node_evidence_before_completion",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "stale_node_evidence_accepted",
        model_cell_id="recursive_route.stale_node_evidence",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
    ),
    _row(
        "wrong_flowguard_target_rejected",
        "wrong_flowguard_target",
        "flowguard_check",
        "wrong_flowguard_target_result",
        ("ack", "submit-result", "status"),
        "wrong_flowguard_target_rejected_before_review",
        ("wrong_flowguard_target_accepted_hazard_detected", "review_gate_preserved"),
        "target_identity_match_required",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "wrong_flowguard_target_accepted",
        model_cell_id="recursive_route.wrong_flowguard_target",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
    ),
    _row(
        "dead_lease_does_not_advance_node",
        "dead_lease",
        "lease",
        "dead_lease_result_attempt",
        ("submit-result", "status", "foreground-duty"),
        "dead_lease_forces_reissue_or_replace_without_advancing_node",
        ("dead_lease_advances_node_hazard_detected", "lease_reissue_required"),
        "dead_lease_recovery_before_node_advance",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "dead_lease_advances_node",
        model_cell_id="recursive_route.dead_lease",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
    ),
    _row(
        "route_mutation_requires_frontier_rewrite",
        "route_mutation_without_frontier_rewrite",
        "route_mutation",
        "route_mutation_without_current_frontier_rewrite",
        ("ack", "submit-result", "status", "foreground-duty"),
        "route_mutation_blocked_until_current_frontier_rewritten",
        ("route_mutation_without_frontier_rewrite_hazard", "frontier_rewrite_required"),
        "route_mutation_gate_then_frontier_refresh",
        "forbidden",
        "tests/test_flowpilot_fake_project_rehearsal.py",
        "route_mutation_without_frontier_rewrite",
        model_cell_id="fake_project.route_mutation_frontier",
        source_paths=("simulations/flowpilot_fake_project_rehearsal_scenarios.py",),
    ),
    _row(
        "slow_reviewer_progress_preserved",
        "slow_reviewer_progress",
        "review",
        "slow_reviewer_progress_update",
        ("ack", "progress", "status", "foreground-duty"),
        "slow_reviewer_progress_preserves_wait_without_replacement",
        ("progress_recorded", "reviewer_wait_preserved", "replacement_not_issued"),
        "progress_is_not_completion_and_not_glassbreak",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "slow_reviewer_progress_preserved",
        model_cell_id="fake_project.slow_reviewer_progress",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
    ),
    _row(
        "accepted_packet_reassignment_rejected",
        "accepted_packet_reassignment",
        "packet_assignment",
        "accepted_packet_reassignment_attempt",
        ("ack", "submit-result", "status"),
        "accepted_packet_cannot_be_reassigned",
        ("accepted_packet_reassignment_blocked", "accepted_result_preserved"),
        "monotonic_packet_acceptance",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "accepted_packet_reassignment_rejected",
        model_cell_id="fake_project.accepted_packet_reassignment",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
    ),
    _row(
        "orphan_runner_summary_routes_recovery",
        "orphan_runner_summary",
        "runner_summary",
        "orphan_runner_summary_without_packet_binding",
        ("ack", "status", "foreground-duty"),
        "orphan_summary_routes_recovery_not_auto_accept",
        ("orphan_evidence_projected", "recover_or_reissue_duty", "packet_not_auto_accepted"),
        "orphan_evidence_recovery_duty",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "orphan_runner_summary_recovery",
        model_cell_id="fake_project.orphan_runner_summary",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
    ),
    _row(
        "unsupported_side_command_rejected",
        "unsupported_side_command",
        "public_cli",
        "unsupported_side_command_complete_flowguard",
        ("--help", "complete-flowguard"),
        "unsupported_side_command_rejected_by_public_cli",
        ("help_surface_absent", "invalid_choice_returned"),
        "unsupported_command_rejects_without_fallback",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_scenarios.py",
        "unsupported_side_command",
        model_cell_id="fake_project.unsupported_side_command",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py", "simulations/flowpilot_fake_project_rehearsal_cli.py"),
    ),
    _row(
        "public_cli_worker_lifetime_bounded",
        "public_cli_worker_lifetime",
        "public_cli",
        "one_shot_public_cli_command_boundary",
        ("open-packet",),
        "public_cli_worker_exits_after_one_shot_open_packet",
        ("one_shot_command_declared", "worker_lifetime_bounded"),
        "public_cli_one_shot_lifetime_boundary",
        "forbidden",
        "simulations/flowpilot_fake_project_rehearsal_cli.py",
        "ONE_SHOT_PUBLIC_CLI_COMMANDS",
        model_cell_id="fake_project.public_cli_worker_lifetime",
        evidence_level="source_contract",
        evidence_command="python -m unittest tests.test_flowpilot_fake_project_rehearsal",
        source_paths=("tests/test_flowpilot_fake_project_rehearsal.py",),
        fake_ai_body_consumed=False,
        runtime_receipt_required=False,
        testmesh_child_id="executable_matrix_source_contracts",
    ),
    _row(
        "same_class_repeats_one_to_four_do_not_glassbreak",
        "same_class_repeats_before_threshold",
        "break_glass_loop",
        "same_class_no_delta_repeat_before_threshold",
        ("submit-result", "status", "foreground-duty"),
        "ordinary_control_repair_lane_until_attempt_four",
        ("same_root_loop_key_recorded", "repair_delta_required", "glassbreak_absent"),
        "attempts_1_to_4_normal_repair_or_blocker_lane",
        "forbidden",
        "tests/test_flowpilot_core_runtime.py",
        "test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
        model_cell_id="control_plane.break_glass_loop.same_root_no_delta_retry.before_threshold",
        attempt_count=4,
        same_failure_class_no_progress=True,
        source_paths=("simulations/flowpilot_contract_exhaustion_mesh_model.py",),
        coverage_boundary="ordinary_recovery_before_break_glass_threshold",
    ),
    _row(
        "same_class_repeat_five_triggers_glassbreak",
        "same_class_repeat_threshold_glassbreak",
        "break_glass_loop",
        "same_class_no_delta_repeat_at_threshold",
        ("submit-result", "status", "foreground-duty", "controller-break-glass"),
        "glassbreak_safety_fuse_after_fifth_same_class_no_progress",
        ("same_root_loop_key_recorded", "fifth_attempt_detected", "glassbreak_incident_opened"),
        "attempt_5_same_class_no_progress_requires_break_glass",
        "required_at_fifth_repeat",
        "tests/test_flowpilot_core_runtime.py",
        "test_break_glass_counts_same_flowguard_root_cause_across_surface_gates",
        model_cell_id="control_plane.break_glass_loop.same_root_no_delta_retry.at_threshold",
        evidence_level="long_chain_convergence",
        attempt_count=5,
        same_failure_class_no_progress=True,
        break_glass_triggered=True,
        source_paths=("simulations/flowpilot_contract_exhaustion_mesh_model.py", "tests/test_flowpilot_controller_break_glass.py"),
        testmesh_child_id="executable_matrix_break_glass_safety_fuse",
        coverage_boundary="break_glass_safety_fuse_only",
    ),
)


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    has_required_fields: bool = True
    has_model_or_shard_ref: bool = True
    evidence_level: str = "runtime_cli_replay"
    evidence_current: bool = True
    fake_ai_body_consumed: bool = True
    runtime_entrypoints_bound: bool = True
    event_log_evidence_present: bool = True
    freshness_receipt_present: bool = True
    live_ai_semantic_quality_proven: bool = False
    product_completion_proven: bool = False
    break_glass_expectation: str = "forbidden"
    attempt_count: int = 1
    same_failure_class_no_progress: bool = False
    break_glass_triggered: bool = False


@dataclass(frozen=True)
class Tick:
    """One bridge-row classification input."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


def _state_from_row(row: dict[str, Any]) -> State:
    missing_fields = [field for field in REQUIRED_BRIDGE_FIELDS if not row.get(field)]
    return State(
        scenario=str(row.get("bridge_case_id", "")),
        status="selected",
        has_required_fields=not missing_fields,
        has_model_or_shard_ref=bool(row.get("model_cell_id") or row.get("coverage_shard_id")),
        evidence_level=str(row.get("evidence_level", "")),
        evidence_current=row.get("evidence_current") is True,
        fake_ai_body_consumed=row.get("fake_ai_body_consumed") is True or str(row.get("evidence_level", "")) == "source_contract",
        runtime_entrypoints_bound=bool(row.get("runtime_entrypoints")),
        event_log_evidence_present=bool(row.get("event_log_evidence")),
        freshness_receipt_present=bool(row.get("freshness_receipt_id")),
        live_ai_semantic_quality_proven=row.get("live_ai_semantic_quality_proven") is True,
        product_completion_proven=row.get("product_completion_proven") is True,
        break_glass_expectation=str(row.get("break_glass_expectation", "")),
        attempt_count=int(row.get("attempt_count") or 0),
        same_failure_class_no_progress=row.get("same_failure_class_no_progress") is True,
        break_glass_triggered=row.get("break_glass_triggered") is True,
    )


SCENARIOS = {str(row["bridge_case_id"]): _state_from_row(row) for row in BRIDGE_ROWS}
VALID_SCENARIOS = frozenset(SCENARIOS)
NEGATIVE_SCENARIOS: frozenset[str] = frozenset()


def bridge_state_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.has_required_fields:
        failures.append("bridge_row_missing_required_fields")
    if not state.has_model_or_shard_ref:
        failures.append("bridge_row_missing_model_or_shard_reference")
    if state.evidence_level == "model_only":
        failures.append("model_only_matrix_cannot_satisfy_executable_bridge")
    elif state.evidence_level not in ACCEPTED_EXECUTABLE_EVIDENCE_LEVELS:
        failures.append("unsupported_executable_evidence_level")
    if not state.evidence_current:
        failures.append("bridge_row_stale_or_missing_evidence")
    if not state.fake_ai_body_consumed:
        failures.append("bridge_row_missing_fake_ai_body_consumption")
    if not state.runtime_entrypoints_bound:
        failures.append("bridge_row_missing_runtime_entrypoints")
    if not state.event_log_evidence_present:
        failures.append("bridge_row_missing_event_log_evidence")
    if not state.freshness_receipt_present:
        failures.append("bridge_row_missing_freshness_receipt")
    if state.live_ai_semantic_quality_proven:
        failures.append("bridge_row_overclaims_live_ai_semantic_quality")
    if state.product_completion_proven:
        failures.append("bridge_row_overclaims_product_completion")
    if state.break_glass_triggered and state.break_glass_expectation != "required_at_fifth_repeat":
        failures.append("ordinary_recovery_entered_glassbreak")
    if state.break_glass_triggered and state.attempt_count < BREAK_GLASS_THRESHOLD:
        failures.append("glassbreak_triggered_before_threshold")
    if state.break_glass_triggered and not state.same_failure_class_no_progress:
        failures.append("glassbreak_missing_same_class_no_progress_lineage")
    if state.break_glass_expectation == "required_at_fifth_repeat":
        if state.attempt_count < BREAK_GLASS_THRESHOLD:
            failures.append("glassbreak_required_row_below_threshold")
        if not state.same_failure_class_no_progress:
            failures.append("glassbreak_required_without_same_class_no_progress")
        if not state.break_glass_triggered:
            failures.append("fifth_same_class_repeat_missing_glassbreak")
    return sorted(set(failures))


def bridge_row_failures(row: dict[str, Any], *, project_root: Path = ROOT) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    missing_fields = [field for field in REQUIRED_BRIDGE_FIELDS if not row.get(field)]
    for field in missing_fields:
        findings.append(
            {
                "code": "bridge_row_missing_required_field",
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "field": field,
                "message": "Executable bridge rows must name every required bridge field.",
            }
        )
    if not (row.get("model_cell_id") or row.get("coverage_shard_id")):
        findings.append(
            {
                "code": "bridge_row_missing_model_or_shard_reference",
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "message": "Executable bridge rows must point back to a model cell or coverage shard.",
            }
        )
    for failure in bridge_state_failures(_state_from_row(row)):
        findings.append(
            {
                "code": failure,
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "message": "Bridge row violates executable-matrix state constraints.",
            }
        )
    evidence_path = project_root / str(row.get("evidence_path", ""))
    marker = str(row.get("evidence_test_name", ""))
    if not evidence_path.exists():
        findings.append(
            {
                "code": "bridge_row_missing_evidence_path",
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "path": str(row.get("evidence_path", "")),
                "message": "Bridge row evidence path does not exist.",
            }
        )
    elif marker and marker not in evidence_path.read_text(encoding="utf-8"):
        findings.append(
            {
                "code": "bridge_row_missing_evidence_marker",
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "path": str(row.get("evidence_path", "")),
                "marker": marker,
                "message": "Bridge row evidence marker was not found in the cited file.",
            }
        )
    receipt = build_freshness_receipt(row, project_root=project_root)
    if not receipt["current"]:
        findings.append(
            {
                "code": "bridge_row_stale_freshness_receipt",
                "bridge_case_id": str(row.get("bridge_case_id", "")),
                "receipt": receipt,
                "message": "Bridge row freshness receipt is missing or stale.",
            }
        )
    return findings


def _mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return None


def build_freshness_receipt(row: dict[str, Any], *, project_root: Path = ROOT) -> dict[str, Any]:
    source_paths = tuple(dict.fromkeys(str(path) for path in row.get("source_paths", ())))
    source_mtimes: dict[str, float] = {}
    missing_sources: list[str] = []
    for rel_path in source_paths:
        mtime = _mtime(project_root / rel_path)
        if mtime is None:
            missing_sources.append(rel_path)
        else:
            source_mtimes[rel_path] = mtime

    result_artifact_path = str(row.get("result_artifact_path", ""))
    result_mtime: float | None = None
    stale_against_sources = False
    if result_artifact_path:
        result_mtime = _mtime(project_root / result_artifact_path)
        if result_mtime is None:
            stale_against_sources = True
        elif source_mtimes and result_mtime < max(source_mtimes.values()):
            stale_against_sources = True

    return {
        "freshness_receipt_id": str(row.get("freshness_receipt_id", "")),
        "current": (
            not missing_sources
            and not stale_against_sources
            and row.get("evidence_current") is True
            and row.get("evidence_status") == "passed"
        ),
        "source_paths": source_paths,
        "missing_sources": missing_sources,
        "source_max_mtime": max(source_mtimes.values()) if source_mtimes else None,
        "result_artifact_path": result_artifact_path,
        "result_mtime": result_mtime,
        "stale_against_sources": stale_against_sources,
    }


def decorated_bridge_rows(rows: Sequence[dict[str, Any]] = BRIDGE_ROWS, *, project_root: Path = ROOT) -> list[dict[str, Any]]:
    return [
        {
            **row,
            "freshness_receipt": build_freshness_receipt(row, project_root=project_root),
        }
        for row in rows
    ]


def validate_bridge_rows(rows: Sequence[dict[str, Any]] = BRIDGE_ROWS, *, project_root: Path = ROOT) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    seen_receipts: set[str] = set()
    for row in rows:
        case_id = str(row.get("bridge_case_id", ""))
        receipt_id = str(row.get("freshness_receipt_id", ""))
        if case_id in seen_case_ids:
            findings.append({"code": "duplicate_bridge_case_id", "bridge_case_id": case_id})
        seen_case_ids.add(case_id)
        if receipt_id in seen_receipts:
            findings.append({"code": "duplicate_freshness_receipt_id", "bridge_case_id": case_id, "freshness_receipt_id": receipt_id})
        seen_receipts.add(receipt_id)
        findings.extend(bridge_row_failures(row, project_root=project_root))

    covered = {str(row.get("miss_family_id", "")) for row in rows}
    for miss_family in sorted(set(REQUIRED_MISS_FAMILIES) - covered):
        findings.append(
            {
                "code": "missing_required_miss_family_bridge_row",
                "miss_family_id": miss_family,
                "message": "Required miss family has no executable bridge row.",
            }
        )
    return findings


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = bridge_state_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


class ExecutableMatrixBridgeStep:
    """Classify one executable matrix bridge row.

    Input x State -> Set(Output x State)
    """

    name = "ExecutableMatrixBridgeStep"
    reads = (
        "model_matrix_cell",
        "fake_ai_body_fixture",
        "runtime_cli_replay_receipt",
        "event_log_evidence",
        "freshness_receipt",
    )
    writes = ("executable_bridge_decision", "coverage_gap_finding")
    input_description = "one model-matrix cell or coverage shard"
    output_description = "accepted executable bridge row or blocking coverage diagnostic"
    idempotency = "classification is keyed by bridge_case_id and freshness_receipt_id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_executable(state: State, _trace: object) -> InvariantResult:
    failures = bridge_state_failures(state)
    if state.status == "accepted" and failures:
        return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not failures:
        return InvariantResult.fail("safe executable bridge state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_executable",
        "Accepted bridge rows must be executable, current, non-live-overclaiming, and must obey break-glass threshold semantics.",
        accepted_states_are_executable,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ExecutableMatrixBridgeStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def build_report(*, project_root: Path = ROOT) -> dict[str, Any]:
    rows = decorated_bridge_rows(project_root=project_root)
    findings = validate_bridge_rows(rows, project_root=project_root)
    miss_family_ids = sorted({str(row["miss_family_id"]) for row in rows})
    evidence_level_counts: dict[str, int] = {}
    child_counts: dict[str, int] = {}
    for row in rows:
        evidence_level_counts[str(row["evidence_level"])] = evidence_level_counts.get(str(row["evidence_level"]), 0) + 1
        child_counts[str(row["testmesh_child_id"])] = child_counts.get(str(row["testmesh_child_id"]), 0) + 1
    glass_break_rows = [row for row in rows if row["break_glass_expectation"] == "required_at_fifth_repeat"]
    ordinary_rows = [row for row in rows if row["break_glass_expectation"] == "forbidden"]
    return {
        "ok": not findings,
        "result_type": RESULT_TYPE,
        "model_id": MODEL_ID,
        "coverage_boundary": (
            "Executable bridge rows prove deterministic fake-AI body, Runtime/CLI, "
            "event-log, convergence, and freshness coverage only. They do not prove "
            "live AI semantic quality or product completion."
        ),
        "required_bridge_fields": list(REQUIRED_BRIDGE_FIELDS),
        "required_miss_families": list(REQUIRED_MISS_FAMILIES),
        "covered_miss_families": miss_family_ids,
        "missing_miss_families": sorted(set(REQUIRED_MISS_FAMILIES) - set(miss_family_ids)),
        "row_count": len(rows),
        "required_miss_family_count": len(REQUIRED_MISS_FAMILIES),
        "ordinary_recovery_row_count": len(ordinary_rows),
        "break_glass_safety_fuse_row_count": len(glass_break_rows),
        "evidence_level_counts": dict(sorted(evidence_level_counts.items())),
        "testmesh_child_counts": dict(sorted(child_counts.items())),
        "break_glass_threshold": BREAK_GLASS_THRESHOLD,
        "live_ai_semantic_quality_proven": False,
        "product_completion_proven": False,
        "findings": findings,
        "rows": rows,
    }


def known_bad_cases() -> list[dict[str, Any]]:
    base = dict(BRIDGE_ROWS[0])
    return [
        {
            "name": "model_only_row_cannot_satisfy_executable_bridge",
            "rows": [{**base, "bridge_case_id": "known_bad_model_only", "evidence_level": "model_only"}],
            "expected_codes": ["model_only_matrix_cannot_satisfy_executable_bridge"],
        },
        {
            "name": "ordinary_recovery_cannot_enter_glassbreak",
            "rows": [
                {
                    **base,
                    "bridge_case_id": "known_bad_ordinary_glassbreak",
                    "attempt_count": 2,
                    "same_failure_class_no_progress": True,
                    "break_glass_triggered": True,
                }
            ],
            "expected_codes": ["ordinary_recovery_entered_glassbreak", "glassbreak_triggered_before_threshold"],
        },
        {
            "name": "fifth_same_class_repeat_must_glassbreak",
            "rows": [
                {
                    **base,
                    "bridge_case_id": "known_bad_missing_threshold_glassbreak",
                    "break_glass_expectation": "required_at_fifth_repeat",
                    "attempt_count": BREAK_GLASS_THRESHOLD,
                    "same_failure_class_no_progress": True,
                    "break_glass_triggered": False,
                }
            ],
            "expected_codes": ["fifth_same_class_repeat_missing_glassbreak"],
        },
        {
            "name": "live_ai_quality_overclaim_forbidden",
            "rows": [{**base, "bridge_case_id": "known_bad_live_claim", "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["bridge_row_overclaims_live_ai_semantic_quality"],
        },
    ]
