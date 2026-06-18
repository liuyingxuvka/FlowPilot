"""Runtime-checkable review-window completeness contracts.

This module is intentionally data-oriented. Runtime, tests, and FlowGuard
coverage models all consume the same rows so Reviewer window scope does not
drift into prose-only prompts or hand-written fixtures.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


REVIEW_WINDOW_SCHEMA_VERSION = "black_box_flowpilot.review_window.v1"

BASE_REQUIRED_WINDOW_PATHS = (
    "schema_version",
    "review_flow_id",
    "review_window_coverage_status",
    "review_result_family_id",
    "subject_packet_id",
    "target_result_id",
    "subject_result_family_id",
    "subject_lifecycle_stage",
    "required_window_paths",
    "required_material_classes",
    "required_authorized_read_purposes_before_submit",
    "authorized_result_read_purposes",
    "forbidden_future_stage_classes",
    "required_current_fields",
    "allowed_blocker_classes",
    "blocker_next_actions",
    "authorized_result_read_ids",
    "required_authorized_result_read_ids_before_submit",
    "sealed_body_access",
    "review_depth_rule",
    "forbidden_future_stage_demands",
    "pm_repair_return_rule",
)

REVIEW_WINDOW_MUTATION_KINDS = (
    "missing_review_flow_id",
    "orphan_review_flow",
    "wrong_subject_family",
    "wrong_subject_lifecycle_stage",
    "missing_window_path",
    "missing_authorized_read",
    "missing_required_read_manifest",
    "future_stage_demand_allowed",
    "pm_repair_return_rule_missing",
    "envelope_body_window_mismatch",
    "prose_only_review_scope",
)

REVIEW_WINDOW_FAKE_AI_PROFILE_IDS = (
    "reviewer_shallow_pass",
    "reviewer_skips_required_read",
    "reviewer_future_stage_demand",
    "reviewer_unauthorized_sealed_body_request",
    "reviewer_invents_scope",
    "reviewer_self_repairs_subject",
    "reviewer_quality_score_10_exceeds_standard",
    "reviewer_quality_score_6_soft_pm_optimization",
    "reviewer_quantitative_gap_blocks",
    "reviewer_overblocks_sub9_soft_score",
    "reviewer_recheck_consumes_score_context",
    "pm_bypasses_reviewer_blocker",
    "corrected_second_reviewer_retry",
    "same_review_failure_attempts_1_to_4",
    "same_review_failure_attempt_5_break_glass",
)

REVIEW_WINDOW_MATERIAL_STATE_CLASSES = (
    "all_required_material_available",
    "missing_required_material",
    "required_read_not_consumed",
    "unauthorized_body_requested",
    "future_stage_material_requested",
)

RETRY_COUNT_CLASSES = (
    "first_failure",
    "corrected_second_attempt",
    "same_failure_attempts_1_to_4",
    "same_failure_attempt_5",
)

REVIEW_WINDOW_COMPLETENESS_ROWS = (
    {
        "review_flow_id": "preplanning_high_standard_contract_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.high_standard_contract",
        "subject_lifecycle_stage": "preplanning_contract_definition",
        "review_kind": "current_subject_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("subject_result_body", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("worker_result_artifacts", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "preplanning_discovery_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.discovery",
        "subject_lifecycle_stage": "preplanning_material_discovery",
        "review_kind": "current_subject_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("subject_result_body", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("worker_result_artifacts", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "preplanning_skill_standard_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.skill_standard",
        "subject_lifecycle_stage": "preplanning_skill_standard_contract",
        "review_kind": "current_subject_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("subject_result_body", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("worker_result_artifacts", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "route_planning_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.planning",
        "subject_lifecycle_stage": "route_planning",
        "review_kind": "route_plan_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("subject_result_body", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("worker_result_artifacts", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "node_acceptance_plan_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.node_acceptance_plan",
        "subject_lifecycle_stage": "node_plan_definition",
        "review_kind": "node_plan_quality_review",
        "required_read_purposes": ("subject_result_for_review",),
        "required_material_classes": ("node_acceptance_plan_result", "node_context_package"),
        "forbidden_future_stage_classes": ("worker_result_artifacts", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "worker_node_result_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.node",
        "subject_lifecycle_stage": "node_result_execution",
        "review_kind": "worker_result_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("worker_result_body", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("terminal_replay_evidence",),
    },
    {
        "review_flow_id": "parent_backward_replay_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "task.parent_backward_replay",
        "subject_lifecycle_stage": "parent_composition_replay",
        "review_kind": "parent_composition_quality_review",
        "required_read_purposes": ("subject_result_for_review", "matching_flowguard_result_for_review"),
        "required_material_classes": ("parent_replay_result_body", "child_evidence_refs", "matching_flowguard_report"),
        "forbidden_future_stage_classes": ("terminal_replay_evidence",),
    },
    {
        "review_flow_id": "pm_flowguard_acceptance_review",
        "review_result_family_id": "review.any_current_subject",
        "subject_family_id": "pm_flowguard_acceptance.pm_flowguard_acceptance",
        "subject_lifecycle_stage": "pm_flowguard_absorption",
        "review_kind": "pm_absorbed_flowguard_quality_review",
        "required_read_purposes": (
            "subject_result_for_review",
            "structural_pm_decision_under_review",
            "flowguard_report_absorbed_by_pm",
        ),
        "required_material_classes": (
            "pm_flowguard_acceptance_result",
            "structural_pm_decision_result",
            "absorbed_flowguard_report",
        ),
        "forbidden_future_stage_classes": ("worker_result_artifacts_after_redesign", "terminal_replay_evidence"),
    },
    {
        "review_flow_id": "terminal_backward_replay_review",
        "review_result_family_id": "review.terminal_backward_replay",
        "subject_family_id": "review.terminal_backward_replay",
        "subject_lifecycle_stage": "terminal_final_backward_replay",
        "review_kind": "terminal_backward_replay",
        "required_read_purposes": (),
        "required_material_classes": (
            "final_route_wide_gate_ledger_status",
            "final_requirement_evidence_matrix_status",
            "segment_targets",
        ),
        "forbidden_future_stage_classes": (),
    },
)


def review_window_rows() -> tuple[dict[str, Any], ...]:
    return tuple(deepcopy(dict(row)) for row in REVIEW_WINDOW_COMPLETENESS_ROWS)


def review_flow_ids() -> tuple[str, ...]:
    return tuple(str(row["review_flow_id"]) for row in REVIEW_WINDOW_COMPLETENESS_ROWS)


def review_flow_row(review_flow_id: str) -> dict[str, Any]:
    for row in REVIEW_WINDOW_COMPLETENESS_ROWS:
        if row["review_flow_id"] == review_flow_id:
            return deepcopy(dict(row))
    raise KeyError(f"unknown review_flow_id: {review_flow_id}")


def find_review_flow_row(
    *,
    review_result_family_id: str,
    subject_family_id: str,
    subject_lifecycle_stage: str,
) -> dict[str, Any] | None:
    for row in REVIEW_WINDOW_COMPLETENESS_ROWS:
        if (
            row["review_result_family_id"] == review_result_family_id
            and row["subject_family_id"] == subject_family_id
            and row["subject_lifecycle_stage"] == subject_lifecycle_stage
        ):
            return deepcopy(dict(row))
    return None


def required_window_paths_for_row(row: Mapping[str, Any]) -> tuple[str, ...]:
    extra = tuple(str(path) for path in row.get("required_window_paths") or ())
    return tuple(dict.fromkeys((*BASE_REQUIRED_WINDOW_PATHS, *extra)))


def review_window_contract_for_context(
    *,
    review_result_family_id: str,
    subject_family_id: str,
    subject_lifecycle_stage: str,
) -> dict[str, Any]:
    row = find_review_flow_row(
        review_result_family_id=review_result_family_id,
        subject_family_id=subject_family_id,
        subject_lifecycle_stage=subject_lifecycle_stage,
    )
    if row is None:
        review_flow_id = (
            "orphan:"
            f"{review_result_family_id or 'unknown_review'}:"
            f"{subject_family_id or 'unknown_subject'}:"
            f"{subject_lifecycle_stage or 'unknown_stage'}"
        )
        return {
            "review_flow_id": review_flow_id,
            "coverage_status": "orphan_review_flow",
            "review_result_family_id": review_result_family_id,
            "subject_family_id": subject_family_id,
            "subject_lifecycle_stage": subject_lifecycle_stage,
            "required_window_paths": BASE_REQUIRED_WINDOW_PATHS,
            "required_read_purposes": (),
            "required_material_classes": (),
            "forbidden_future_stage_classes": (),
        }
    return {
        **row,
        "coverage_status": "declared",
        "required_window_paths": required_window_paths_for_row(row),
    }


def review_window_completeness_failures(review_window: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not isinstance(review_window, Mapping):
        return ("review_window_not_structured",)
    failures: list[str] = []
    if review_window.get("schema_version") != REVIEW_WINDOW_SCHEMA_VERSION:
        failures.append("review_window_schema_version_mismatch")
    flow_id = str(review_window.get("review_flow_id") or "")
    coverage_status = str(review_window.get("review_window_coverage_status") or "")
    if coverage_status != "declared":
        failures.append(str(coverage_status or "review_window_coverage_status_missing"))
    if not flow_id:
        failures.append("review_flow_id_missing")
    else:
        try:
            row = review_flow_row(flow_id)
        except KeyError:
            failures.append("orphan_review_flow")
        else:
            expected_pairs = (
                ("review_result_family_id", "review_result_family_id"),
                ("subject_result_family_id", "subject_family_id"),
                ("subject_lifecycle_stage", "subject_lifecycle_stage"),
            )
            for window_key, row_key in expected_pairs:
                if str(review_window.get(window_key) or "") != str(row.get(row_key) or ""):
                    failures.append(f"review_window_{window_key}_mismatch")
            required_paths = set(required_window_paths_for_row(row))
            declared_paths = {
                str(path)
                for path in review_window.get("required_window_paths", [])
                if str(path)
            }
            missing_declared_paths = sorted(required_paths - declared_paths)
            failures.extend(f"required_window_path_not_declared:{path}" for path in missing_declared_paths)
            missing_structured_paths = sorted(
                path for path in required_paths if path not in review_window
            )
            failures.extend(f"required_window_path_missing:{path}" for path in missing_structured_paths)
            expected_required_reads = {
                str(purpose)
                for purpose in row.get("required_read_purposes") or ()
                if str(purpose)
            }
            projected_required_reads = {
                str(purpose)
                for purpose in review_window.get("required_authorized_read_purposes_before_submit", [])
                if str(purpose)
            }
            authorized_read_purposes = {
                str(purpose)
                for purpose in review_window.get("authorized_result_read_purposes", [])
                if str(purpose)
            }
            failures.extend(
                f"required_authorized_read_purpose_not_projected:{purpose}"
                for purpose in sorted(expected_required_reads - projected_required_reads)
            )
            failures.extend(
                f"required_authorized_read_purpose_not_authorized:{purpose}"
                for purpose in sorted(expected_required_reads - authorized_read_purposes)
            )
    return tuple(dict.fromkeys(failures))


def review_window_pair_failures(
    envelope_review_window: Mapping[str, Any] | None,
    body_review_window: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    failures = list(review_window_completeness_failures(envelope_review_window))
    if not isinstance(body_review_window, Mapping):
        failures.append("body_review_window_not_structured")
    elif dict(envelope_review_window or {}) != dict(body_review_window):
        failures.append("envelope_body_window_mismatch")
    return tuple(dict.fromkeys(failures))


def review_window_completeness_cells() -> tuple[dict[str, str], ...]:
    cells: list[dict[str, str]] = []
    for row in REVIEW_WINDOW_COMPLETENESS_ROWS:
        flow_id = str(row["review_flow_id"])
        for path in required_window_paths_for_row(row):
            cells.append(
                {
                    "cell_id": f"review_window.{flow_id}.path.{_sanitize_cell_part(path)}",
                    "review_flow_id": flow_id,
                    "family": "review_packet",
                    "contract_family_id": flow_id,
                    "contract_path": f"review_window.{path}",
                    "mutation_kind": "missing_window_path",
                    "branch_kind": "ordinary_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "review_window_completeness_matrix",
                }
            )
        for purpose in row.get("required_read_purposes") or ():
            cells.append(
                {
                    "cell_id": f"review_window.{flow_id}.read.{_sanitize_cell_part(str(purpose))}",
                    "review_flow_id": flow_id,
                    "family": "review_packet",
                    "contract_family_id": flow_id,
                    "contract_path": f"authorized_result_reads[{purpose}]",
                    "mutation_kind": "missing_authorized_read",
                    "branch_kind": "ordinary_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "review_window_completeness_matrix",
                }
            )
        for mutation in REVIEW_WINDOW_MUTATION_KINDS:
            cells.append(
                {
                    "cell_id": f"review_window.{flow_id}.mutation.{mutation}",
                    "review_flow_id": flow_id,
                    "family": "review_packet",
                    "contract_family_id": flow_id,
                    "contract_path": "envelope.review_window",
                    "mutation_kind": mutation,
                    "branch_kind": "ordinary_runtime",
                    "confidence_boundary": "current_runtime_contract",
                    "required_evidence_owner": "review_window_completeness_matrix",
                }
            )
        for material_state in REVIEW_WINDOW_MATERIAL_STATE_CLASSES:
            for profile in REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
                for retry_class in RETRY_COUNT_CLASSES:
                    if retry_class == "same_failure_attempt_5":
                        expected = "break_glass_threshold"
                    elif retry_class == "corrected_second_attempt":
                        expected = "accepted_after_reviewer_recheck"
                    else:
                        expected = "normal_repair_or_reissue"
                    cells.append(
                        {
                            "cell_id": (
                                f"review_window.{flow_id}.fake_ai."
                                f"{material_state}.{profile}.{retry_class}"
                            ),
                            "review_flow_id": flow_id,
                            "family": "review_packet",
                            "contract_family_id": flow_id,
                            "contract_path": "review_window.fake_ai_behavior",
                            "mutation_kind": profile,
                            "material_state_class": material_state,
                            "retry_count_class": retry_class,
                            "branch_kind": "synthetic_replay",
                            "confidence_boundary": "synthetic_non_live_control_flow",
                            "required_evidence_owner": "review_window_fake_ai_matrix",
                            "expected_reaction": expected,
                        }
                    )
    return tuple(cells)


def _sanitize_cell_part(value: str) -> str:
    return (
        value.replace("[]", "_items")
        .replace("[", "_")
        .replace("]", "")
        .replace(".", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .replace("=", "_")
        .replace(":", "_")
    )
