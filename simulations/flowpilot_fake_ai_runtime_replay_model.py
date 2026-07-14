"""Fake-AI runtime replay coverage model for FlowPilot.

This model does not replace the concrete runtime tests.  It binds generated
fake-AI contract cells to the runtime reactions those tests must prove:
first-round rejection, actionable reissue, corrected second retry, ordinary
repair before the GlassBreak threshold, and the fifth same-failure fuse.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
import hashlib
from itertools import product
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Mapping, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_PATH) not in sys.path:
    sys.path.insert(0, str(ASSETS_PATH))
if str(ROOT / "simulations") not in sys.path:
    sys.path.insert(0, str(ROOT / "simulations"))

from flowpilot_core_runtime import packet_result_contracts, packet_stage_evidence_matrix  # noqa: E402
from flowpilot_contract_driven_fake_ai import (  # noqa: E402
    ContractDrivenFakeAIResponder,
    MALFORMED_BODY_PROFILE_IDS,
    PROJECTION_GAP_PROFILE_IDS,
    RETRY_PROFILE_IDS,
    REVIEW_WINDOW_FAKE_AI_PROFILE_IDS,
    review_window_behavior_cells,
)
from flowpilot_integration_cartesian_coverage_model import iter_required_cells as integration_cartesian_cells  # noqa: E402


MODEL_ID = "flowpilot_fake_ai_runtime_replay"
RESULT_PATH = "simulations/flowpilot_fake_ai_runtime_replay_summary.json"
REQUIRED_EVIDENCE_OWNER = "fake_ai_runtime_replay_matrix"
MAX_SEQUENCE_LENGTH = 2

PROFILE_EXHAUSTION_SAMPLE_BINDINGS: dict[str, dict[str, object]] = {
    "flowguard.semantic_recheck_required": {
        "blocker_id": "blocker-runtime-replay-sample",
        "coverage_boundary": "subject_bound_semantic",
        "authorized_result_read_ids": ["result-runtime-replay-sample"],
        "repair_obligation_ids": ["repair-obligation-runtime-replay-sample"],
    },
    "flowguard.subject_artifacts_consumed_required": {
        "artifact_ids": ["artifact-runtime-replay-sample"],
    },
}

CONCRETE_RUNTIME_TESTS: dict[str, str] = {
    "malformed_body": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_contract_driven_fake_ai_malformed_body_profiles_reissue_with_strict_json_feedback"
    ),
    "wrong_allowed_value": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_contract_driven_fake_ai_wrong_value_rows_repair_each_finite_option"
    ),
    "corrected_retry": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_semantic_recheck_wrong_value_then_corrected_retry_returns_to_legal_path"
    ),
    "review_window_profile": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_contract_driven_fake_ai_review_window_profiles_are_declared"
    ),
    "review_window_completeness": (
        "tests.test_flowpilot_high_standard_control_flow.FlowPilotHighStandardControlFlowTests."
        "test_runtime_issued_review_packets_have_complete_declared_windows"
    ),
    "legal_current_contract": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_contract_driven_fake_ai_uses_projected_minimal_shape_for_legal_path"
    ),
    "owner_set_feedback": (
        "tests.test_flowpilot_ai_contract_projection.FlowPilotAIContractProjectionTests."
        "test_node_acceptance_projection_owner_set_matrix_rejects_bad_rows_and_accepts_complete_rows"
    ),
    "normal_before_threshold": (
        "tests.test_flowpilot_cartesian_control_plane_exhaustion."
        "FlowPilotCartesianControlPlaneExhaustionTests.test_normal_repair_cells_never_expect_glassbreak"
    ),
    "breakglass_threshold": (
        "tests.test_flowpilot_cartesian_control_plane_exhaustion."
        "FlowPilotCartesianControlPlaneExhaustionTests.test_glassbreak_cells_are_threshold_only_and_name_loop_key"
    ),
    "integration_full_matrix": (
        "tests.test_flowpilot_integration_cartesian_coverage."
        "FlowPilotIntegrationCartesianCoverageTests.test_integration_cartesian_runner_accepts_full_matrix"
    ),
    "integration_hard_failure": (
        "tests.test_flowpilot_integration_cartesian_coverage."
        "FlowPilotIntegrationCartesianCoverageTests.test_hard_composition_failures_are_not_downgraded_to_advisory"
    ),
    "integration_authority_boundary": (
        "tests.test_flowpilot_integration_cartesian_coverage."
        "FlowPilotIntegrationCartesianCoverageTests.test_worker_and_runtime_do_not_gain_semantic_integration_authority"
    ),
    "integration_hazards": (
        "tests.test_flowpilot_integration_cartesian_coverage."
        "FlowPilotIntegrationCartesianCoverageTests.test_flowguard_hazards_cover_underblocking_overblocking_and_model_miss"
    ),
    "parent_entry_return_path": (
        "tests.test_flowpilot_parent_entry_return_path."
        "FlowPilotParentEntryReturnPathTests.test_final_hard_gate_escape_matrix_returns_each_runtime_gate_to_owner"
    ),
    "runtime_submit_result_ingress": (
        "tests.test_flowpilot_lifecycle_guard."
        "FlowPilotLifecycleGuardTests.test_late_result_rejects_noncurrent_packet_statuses_without_mutation"
    ),
    "runtime_duplicate_current_submit": (
        "tests.test_flowpilot_lifecycle_guard."
        "FlowPilotLifecycleGuardTests.test_duplicate_current_same_lease_result_rejects_without_second_result"
    ),
    "runtime_accepted_result_authority": (
        "tests.test_flowpilot_core_runtime."
        "FlowPilotCoreRuntimeTests.test_review_packet_target_result_uses_accepted_result_id_over_result_ids_tail"
    ),
    "reviewer_runtime_mechanical_boundary": (
        "tests.test_flowpilot_reviewer_active_challenge."
        "FlowPilotReviewerActiveChallengeTests.test_runtime_cards_templates_and_contracts_keep_reviewer_challenge_compact"
    ),
    "global_standard_context_prompt": (
        "tests.test_flowpilot_card_instruction_coverage."
        "FlowPilotCardInstructionCoverageTests.test_current_global_standard_references_reach_backstage_roles"
    ),
    "planning_global_standard_model": (
        "tests.test_flowpilot_planning_quality."
        "FlowPilotPlanningQualityTests.test_planning_quality_model_rejects_hazards"
    ),
}

RUNTIME_OWNED_BAD_AI_REPLAY_CELLS: tuple[dict[str, str], ...] = (
    {
        "cell_id": "accepted_packet_resubmit_rejected",
        "family": "submit_result_body_entry",
        "contract_family_id": "runtime.submit_result_ingress",
        "contract_path": "submit-result.packet.accepted_result_id",
        "mutation_kind": "submit_result.accepted_packet_resubmit",
        "expected_runtime_reaction": "hard_reject_before_result_allocation",
        "expected_test_key": "runtime_submit_result_ingress",
    },
    {
        "cell_id": "noncurrent_packet_submit_rejected",
        "family": "submit_result_body_entry",
        "contract_family_id": "runtime.submit_result_ingress",
        "contract_path": "submit-result.packet.status",
        "mutation_kind": "submit_result.noncurrent_packet_submit",
        "expected_runtime_reaction": "hard_reject_before_result_allocation",
        "expected_test_key": "runtime_submit_result_ingress",
    },
    {
        "cell_id": "closed_lease_submit_rejected",
        "family": "submit_result_body_entry",
        "contract_family_id": "runtime.submit_result_ingress",
        "contract_path": "submit-result.lease.status",
        "mutation_kind": "submit_result.closed_lease_submit",
        "expected_runtime_reaction": "hard_reject_before_result_allocation",
        "expected_test_key": "runtime_submit_result_ingress",
    },
    {
        "cell_id": "stale_route_submit_rejected",
        "family": "submit_result_body_entry",
        "contract_family_id": "runtime.submit_result_ingress",
        "contract_path": "submit-result.packet.route_version",
        "mutation_kind": "submit_result.stale_route_submit",
        "expected_runtime_reaction": "hard_reject_before_result_allocation",
        "expected_test_key": "runtime_submit_result_ingress",
    },
    {
        "cell_id": "duplicate_current_lease_submit_rejected",
        "family": "submit_result_body_entry",
        "contract_family_id": "runtime.submit_result_ingress",
        "contract_path": "submit-result.packet.result_ids",
        "mutation_kind": "submit_result.duplicate_current_lease_submit",
        "expected_runtime_reaction": "hard_reject_before_result_allocation",
        "expected_test_key": "runtime_duplicate_current_submit",
    },
    {
        "cell_id": "review_uses_accepted_result_id_not_tail",
        "family": "review_packet",
        "contract_family_id": "runtime.accepted_result_authority",
        "contract_path": "review_packet.target_result_id",
        "mutation_kind": "review_packet.result_ids_tail_after_accepted_result",
        "expected_runtime_reaction": "accepted_result_id_authority_preserved",
        "expected_test_key": "runtime_accepted_result_authority",
    },
    {
        "cell_id": "reviewer_semantic_keyword_gate_rejected_as_runtime_authority",
        "family": "review_result",
        "contract_family_id": "runtime.reviewer_mechanical_boundary",
        "contract_path": "review_result.runtime_mechanical_shape_only",
        "mutation_kind": "reviewer.semantic_keyword_gate_attempt",
        "expected_runtime_reaction": "runtime_mechanical_only_reviewer_boundary",
        "expected_test_key": "reviewer_runtime_mechanical_boundary",
    },
    {
        "cell_id": "reviewer_active_verification_prompt_required",
        "family": "review_packet",
        "contract_family_id": "runtime.reviewer_active_verification_prompt",
        "contract_path": "review_packet.instruction",
        "mutation_kind": "reviewer.prompt_omits_active_verification",
        "expected_runtime_reaction": "reviewer_prompt_requires_active_verification_without_new_fields",
        "expected_test_key": "runtime_accepted_result_authority",
    },
)

GLOBAL_STANDARD_CONTEXT_REPLAY_CELLS: tuple[dict[str, str], ...] = (
    {
        "cell_id": "node_plan_missing_global_standard_references",
        "family": "node_acceptance_plan",
        "contract_family_id": "flowpilot_global_standard_context",
        "contract_path": "node_context_package.relevant_references",
        "mutation_kind": "global_standard_context.node_plan_local_only_references",
        "expected_runtime_reaction": "reviewer_blocks_local_only_global_context",
        "expected_test_key": "planning_global_standard_model",
    },
    {
        "cell_id": "worker_result_ignores_user_pm_standard",
        "family": "worker_result_review",
        "contract_family_id": "flowpilot_global_standard_context",
        "contract_path": "worker_result.acceptance_slice",
        "mutation_kind": "global_standard_context.worker_local_only_completion",
        "expected_runtime_reaction": "reviewer_blocks_worker_result_below_user_pm_standard",
        "expected_test_key": "global_standard_context_prompt",
    },
    {
        "cell_id": "flowguard_models_process_without_user_pm_standard",
        "family": "flowguard_work_order",
        "contract_family_id": "flowpilot_global_standard_context",
        "contract_path": "flowguard_work_order.node_context_package.relevant_references",
        "mutation_kind": "global_standard_context.flowguard_local_only_model",
        "expected_runtime_reaction": "flowguard_models_against_user_pm_standard_or_reports_gap",
        "expected_test_key": "global_standard_context_prompt",
    },
)

CONTROL_PLANE_LEDGER_HYGIENE_OWNER = "control_plane_ledger_hygiene_fake_ai_matrix"
CONTROL_PLANE_LEDGER_HYGIENE_SOURCE = "control_plane_ledger_hygiene_cartesian"
CONTROL_PLANE_LEDGER_HYGIENE_AXES: dict[str, tuple[str, ...]] = {
    "result_status": (
        "accepted",
        "review_blocked",
        "rejected",
        "mechanically_valid",
        "validation_failed",
    ),
    "accepted_pointer": (
        "empty",
        "clean",
        "points_to_review_blocked",
        "points_to_missing",
        "stale",
    ),
    "repair_identity": (
        "all_present",
        "packet_missing",
        "envelope_missing",
        "body_missing",
        "mismatch",
        "gate_derived_missing",
    ),
    "packet_family": (
        "task",
        "pm_repair_decision",
        "flowguard_check",
        "pm_flowguard_acceptance",
        "review",
        "terminal_backward_replay",
    ),
    "blocker": (
        "none",
        "active_current",
        "active_stale",
        "cleared",
        "stopped",
        "awaiting_pm_decision_gate",
    ),
    "break_glass": (
        "none",
        "incident_open",
        "pending_patch",
        "permanent_fix_needed",
        "quarantined",
        "closed",
    ),
    "reviewer_authorization": (
        "none",
        "partial",
        "full",
        "stale_hash",
        "wrong_role",
    ),
    "closure_phase": (
        "node",
        "pm_gate",
        "system_validation",
        "final_replay",
        "final_closure",
        "terminal_return",
    ),
}
CONTROL_PLANE_LEDGER_HYGIENE_EXPECTED_CELL_COUNT = 1
for _axis_values in CONTROL_PLANE_LEDGER_HYGIENE_AXES.values():
    CONTROL_PLANE_LEDGER_HYGIENE_EXPECTED_CELL_COUNT *= len(_axis_values)

TERMINAL_LEDGER_PHASES = {"final_closure", "terminal_return"}
FINAL_REVIEW_PHASES = {"final_replay", "final_closure", "terminal_return"}
REPAIR_CHAIN_PACKET_FAMILIES = {
    "pm_repair_decision",
    "flowguard_check",
    "pm_flowguard_acceptance",
    "review",
    "terminal_backward_replay",
}
DIRTY_ACCEPTED_POINTERS = {"points_to_review_blocked", "points_to_missing", "stale"}
OPEN_BREAK_GLASS_STATES = {"incident_open", "pending_patch", "permanent_fix_needed"}
BLOCKING_BLOCKER_STATES = {"active_current", "active_stale", "awaiting_pm_decision_gate", "stopped"}
REVIEWER_AUTH_FAILURES = {"none", "partial", "stale_hash", "wrong_role"}
CONTROL_PLANE_LEDGER_HYGIENE_REACTIONS = {
    "reject_dirty_accepted_result_pointer",
    "reject_inconsistent_clean_accepted_pointer",
    "reject_repair_identity_discontinuity",
    "block_terminal_break_glass_not_closed",
    "block_terminal_active_or_stopped_blocker",
    "block_final_reviewer_authorization_gap",
    "block_terminal_failed_or_unreviewed_result",
    "require_review_or_validation_before_acceptance",
    "continue_current_runtime_path",
    "allow_terminal_ledger_hygiene",
}


def _control_plane_hygiene_reaction(axis: Mapping[str, str]) -> tuple[str, tuple[str, ...]]:
    result_status = axis["result_status"]
    accepted_pointer = axis["accepted_pointer"]
    repair_identity = axis["repair_identity"]
    packet_family = axis["packet_family"]
    blocker = axis["blocker"]
    break_glass = axis["break_glass"]
    reviewer_authorization = axis["reviewer_authorization"]
    closure_phase = axis["closure_phase"]
    reasons: list[str] = []

    if accepted_pointer in DIRTY_ACCEPTED_POINTERS:
        reasons.append("accepted_result_id_points_to_nonaccepted_or_missing_result")
        return "reject_dirty_accepted_result_pointer", tuple(reasons)
    if accepted_pointer == "clean" and result_status != "accepted":
        reasons.append("clean_accepted_pointer_conflicts_with_result_status")
        return "reject_inconsistent_clean_accepted_pointer", tuple(reasons)
    if repair_identity != "all_present" and packet_family in REPAIR_CHAIN_PACKET_FAMILIES:
        reasons.append("repair_blocker_id_not_consistent_across_packet_envelope_body")
        return "reject_repair_identity_discontinuity", tuple(reasons)
    if closure_phase in TERMINAL_LEDGER_PHASES and break_glass in OPEN_BREAK_GLASS_STATES:
        reasons.append("break_glass_incident_or_patch_has_no_terminal_disposition")
        return "block_terminal_break_glass_not_closed", tuple(reasons)
    if closure_phase in TERMINAL_LEDGER_PHASES and blocker in BLOCKING_BLOCKER_STATES:
        reasons.append("active_or_stopped_blocker_survives_terminal_hygiene")
        return "block_terminal_active_or_stopped_blocker", tuple(reasons)
    if (
        (closure_phase in FINAL_REVIEW_PHASES or packet_family in {"review", "terminal_backward_replay"})
        and reviewer_authorization in REVIEWER_AUTH_FAILURES
    ):
        reasons.append("reviewer_final_or_review_packet_lacks_current_authorized_reads")
        return "block_final_reviewer_authorization_gap", tuple(reasons)
    if closure_phase in TERMINAL_LEDGER_PHASES and result_status in {
        "review_blocked",
        "rejected",
        "validation_failed",
    }:
        reasons.append("terminal_hygiene_found_failed_result_state")
        return "block_terminal_failed_or_unreviewed_result", tuple(reasons)
    if closure_phase in TERMINAL_LEDGER_PHASES and result_status != "accepted":
        reasons.append("terminal_hygiene_found_unaccepted_result_state")
        return "require_review_or_validation_before_acceptance", tuple(reasons)
    if closure_phase in TERMINAL_LEDGER_PHASES:
        reasons.append("all_terminal_ledger_hygiene_conditions_clean")
        return "allow_terminal_ledger_hygiene", tuple(reasons)
    reasons.append("nonterminal_phase_uses_current_runtime_owner_path")
    return "continue_current_runtime_path", tuple(reasons)


def control_plane_ledger_hygiene_cell_id(axis: Mapping[str, str]) -> str:
    return "control_plane_ledger_hygiene:" + "|".join(
        f"{axis_name}={axis[axis_name]}" for axis_name in CONTROL_PLANE_LEDGER_HYGIENE_AXES
    )


def iter_control_plane_ledger_hygiene_cells() -> Iterable[dict[str, Any]]:
    axis_names = tuple(CONTROL_PLANE_LEDGER_HYGIENE_AXES)
    for values in product(*(CONTROL_PLANE_LEDGER_HYGIENE_AXES[name] for name in axis_names)):
        axis = dict(zip(axis_names, values, strict=True))
        reaction, reasons = _control_plane_hygiene_reaction(axis)
        cell_id = control_plane_ledger_hygiene_cell_id(axis)
        yield {
            "cell_id": cell_id,
            "source_cell_id": cell_id,
            "source_matrix": CONTROL_PLANE_LEDGER_HYGIENE_SOURCE,
            "family": "control_plane_ledger_hygiene",
            "contract_family_id": "runtime.control_plane_ledger_hygiene",
            "contract_path": ".".join(f"{name}:{axis[name]}" for name in axis_names),
            "mutation_kind": f"control_plane_ledger_hygiene.{reaction}",
            "branch_kind": reaction,
            "confidence_boundary": "synthetic_non_live_runtime_replay",
            "required_evidence_owner": CONTROL_PLANE_LEDGER_HYGIENE_OWNER,
            "attempt_class": "cartesian_control_plane_ledger_hygiene",
            "expected_runtime_reaction": reaction,
            "expected_test_name": (
                "tests.test_flowpilot_fake_ai_runtime_replay."
                "FlowPilotFakeAIRuntimeReplayTests."
                "test_control_plane_ledger_hygiene_fake_ai_matrix_is_cartesian"
            ),
            "glass_break_allowed": False,
            "normal_path_required": True,
            "live_completion_allowed": False,
            "semantic_runtime_blocker_allowed": False,
            "fallback_allowed": False,
            "runtime_mechanical_only": True,
            "hygiene_reasons": reasons,
            **axis,
        }


@lru_cache(maxsize=1)
def control_plane_ledger_hygiene_cells() -> tuple[dict[str, Any], ...]:
    return tuple(iter_control_plane_ledger_hygiene_cells())


@lru_cache(maxsize=1)
def control_plane_ledger_hygiene_declaration_summary() -> dict[str, Any]:
    """Stream the finite Cartesian universe into a compact structural receipt."""

    digest = hashlib.sha256()
    count = 0
    reactions: Counter[str] = Counter()
    finding_counts: Counter[str] = Counter()
    dirty_pointer_count = 0
    final_authorization_gap_count = 0
    required_fields = (
        "cell_id",
        "source_cell_id",
        "contract_family_id",
        "mutation_kind",
        "expected_runtime_reaction",
        "attempt_class",
        "expected_test_name",
        "required_evidence_owner",
        "confidence_boundary",
    )
    for cell in iter_control_plane_ledger_hygiene_cells():
        count += 1
        cell_id = str(cell.get("cell_id") or "")
        reaction = str(cell.get("expected_runtime_reaction") or "")
        owner = str(cell.get("required_evidence_owner") or "")
        digest.update(cell_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(reaction.encode("utf-8"))
        digest.update(b"\0")
        digest.update(owner.encode("utf-8"))
        digest.update(b"\n")
        reactions[reaction] += 1
        for field in required_fields:
            if not cell.get(field):
                finding_counts[f"missing_required_field:{field}"] += 1
        if owner != CONTROL_PLANE_LEDGER_HYGIENE_OWNER:
            finding_counts["wrong_owner"] += 1
        if reaction not in CONTROL_PLANE_LEDGER_HYGIENE_REACTIONS:
            finding_counts["unknown_reaction"] += 1
        if cell.get("live_completion_allowed") is not False:
            finding_counts["live_completion_overclaim"] += 1
        if cell.get("fallback_allowed") is not False:
            finding_counts["fallback_allowed"] += 1
        if cell.get("glass_break_allowed") is not False:
            finding_counts["glass_break_allowed"] += 1
        if cell.get("normal_path_required") is not True:
            finding_counts["normal_path_not_required"] += 1
        if not cell.get("hygiene_reasons"):
            finding_counts["missing_hygiene_reason"] += 1
        if cell.get("accepted_pointer") in DIRTY_ACCEPTED_POINTERS:
            dirty_pointer_count += 1
            if reaction != "reject_dirty_accepted_result_pointer":
                finding_counts["dirty_pointer_not_rejected"] += 1
        final_authorization_gap = (
            cell.get("closure_phase") in FINAL_REVIEW_PHASES
            and cell.get("reviewer_authorization") in REVIEWER_AUTH_FAILURES
            and cell.get("accepted_pointer") not in DIRTY_ACCEPTED_POINTERS
            and not (
                cell.get("accepted_pointer") == "clean"
                and cell.get("result_status") != "accepted"
            )
            and not (
                cell.get("repair_identity") != "all_present"
                and cell.get("packet_family") in REPAIR_CHAIN_PACKET_FAMILIES
            )
        )
        if final_authorization_gap:
            final_authorization_gap_count += 1
            if reaction == "allow_terminal_ledger_hygiene":
                finding_counts["final_authorization_gap_allowed_terminal"] += 1
    if count != CONTROL_PLANE_LEDGER_HYGIENE_EXPECTED_CELL_COUNT:
        finding_counts["cell_count_mismatch"] += 1
    if not dirty_pointer_count:
        finding_counts["dirty_pointer_branch_missing"] += 1
    if not final_authorization_gap_count:
        finding_counts["final_authorization_gap_branch_missing"] += 1
    return {
        "ok": not finding_counts,
        "owner": CONTROL_PLANE_LEDGER_HYGIENE_OWNER,
        "source": CONTROL_PLANE_LEDGER_HYGIENE_SOURCE,
        "axis_names": list(CONTROL_PLANE_LEDGER_HYGIENE_AXES),
        "axis_sizes": {
            name: len(values) for name, values in CONTROL_PLANE_LEDGER_HYGIENE_AXES.items()
        },
        "expected_cell_count": CONTROL_PLANE_LEDGER_HYGIENE_EXPECTED_CELL_COUNT,
        "declared_cell_count": count,
        "cell_receipt_sha256": digest.hexdigest(),
        "by_reaction": dict(sorted(reactions.items())),
        "dirty_pointer_cell_count": dirty_pointer_count,
        "final_authorization_gap_cell_count": final_authorization_gap_count,
        "finding_counts": dict(sorted(finding_counts.items())),
    }


EXPECTED_REACTION_BY_MUTATION = {
    "empty_required_array": "mechanical_reject_reissue",
    "finite_option_mistake": "mechanical_reject_reissue_with_options",
    "forbidden_alias": "mechanical_reject_reissue_with_exact_field",
    "forbidden_alias_used": "mechanical_reject_reissue_with_exact_field",
    "forbidden_field_present": "mechanical_reject_reissue",
    "hidden_projection_gap": "projection_preflight_failure",
    "missing_active_id_coverage": "mechanical_reject_reissue_with_missing_ids",
    "partial_owner_set_missing_id": "mechanical_reject_reissue_with_missing_ids",
    "extra_owner_id": "mechanical_reject_reissue_with_owner_set",
    "empty_owner_set_extra_id": "mechanical_reject_reissue_with_owner_set",
    "malformed_projection_row": "mechanical_reject_reissue",
    "complete_owner_coverage": "accepted_current_contract",
    "missing_allowed_value_options": "projection_preflight_failure",
    "missing_field_type_requirements": "projection_preflight_failure",
    "missing_required_child_field": "mechanical_reject_reissue",
    "missing_required_field": "mechanical_reject_reissue",
    "wrong_allowed_value": "mechanical_reject_reissue_with_options",
    "wrong_type": "mechanical_reject_reissue",
    "corrected_second_retry": "accepted_after_reissue",
    "partial_repair_then_corrected": "same_family_repair_or_reissue_without_glassbreak_before_threshold",
    "same_payload_retry": "same_family_repair_or_reissue_without_glassbreak_before_threshold",
}

PARENT_ENTRY_GATE_TYPES = (
    "missing_node_acceptance_plan",
    "missing_node_context_package",
    "missing_parent_backward_replay",
    "missing_pm_disposition",
    "active_packet_unresolved",
    "stale_current_evidence",
)
PARENT_ENTRY_SUBJECT_TOPOLOGIES = (
    "ancestor_parent",
    "descendant_child",
    "mutation_created_parent",
)
PARENT_ENTRY_DETECTION_STAGES = (
    "node_entry",
    "parent_backward_replay",
    "pm_disposition",
    "final_preflight",
)


def _contract_family_bucket(contract_id: str) -> str:
    if contract_id.startswith("flowguard."):
        return "flowguard_check_result"
    row = packet_result_contracts.PACKET_RESULT_CONTRACTS_BY_FAMILY.get(contract_id, {})
    packet_kind = str(row.get("packet_kind") or "")
    if packet_kind == "flowguard_check":
        return "flowguard_check_result"
    if packet_kind == "review":
        return "review_result"
    if packet_kind in {"pm_repair_decision", "pm_disposition", "pm_flowguard_acceptance"}:
        return "pm_result"
    return "task_result_body"


def _responder_contracts() -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for row in packet_result_contracts.PACKET_RESULT_CONTRACTS:
        family_id = str(row["family_id"])
        contracts[family_id] = packet_result_contracts.effective_result_contract_for_family(family_id)
    for profile_id in packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS:
        profile = packet_stage_evidence_matrix.result_contract_profile(profile_id)
        family_id = str(profile["family_id"])
        contracts[profile_id] = packet_result_contracts.effective_result_contract_for_family(
            family_id,
            result_contract_profile_ids=(profile_id,),
            result_contract_profile_bindings=PROFILE_EXHAUSTION_SAMPLE_BINDINGS.get(profile_id, {}),
        )
    route_plan_contract = packet_result_contracts.effective_result_contract_for_family("task.planning")
    contracts["task.planning.required_acceptance_item_ids"] = {
        **route_plan_contract,
        "required_acceptance_item_ids": ["acc-runtime-replay-001", "acc-runtime-replay-002"],
    }
    contracts["task.planning.empty_required_acceptance_item_ids"] = {
        **route_plan_contract,
        "required_acceptance_item_ids": [],
    }
    node_context_contract = packet_result_contracts.effective_result_contract_for_family("task.node_acceptance_plan")
    contracts["task.node_acceptance_plan.required_node_acceptance_item_ids"] = {
        **node_context_contract,
        "required_node_acceptance_item_ids": ["acc-runtime-replay-001", "acc-runtime-replay-002"],
    }
    contracts["task.node_acceptance_plan.empty_required_node_acceptance_item_ids"] = {
        **node_context_contract,
        "required_node_acceptance_item_ids": [],
    }
    return contracts


def _expected_reaction(mutation: str, cell: Mapping[str, Any]) -> str:
    if mutation.startswith("malformed_body."):
        return "mechanical_reject_reissue_with_strict_json_feedback"
    if mutation in REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
        retry_class = str(cell.get("retry_count_class") or "")
        if retry_class == "corrected_second_attempt" or mutation == "corrected_second_reviewer_retry":
            return "accepted_after_reissue"
        if retry_class == "same_failure_attempt_5" or mutation == "same_review_failure_attempt_5_break_glass":
            return "breakglass_after_fifth_same_failure"
        if retry_class == "first_failure":
            return "reviewer_blocker_or_reissue_first_failure"
        return "reviewer_blocker_or_reissue_without_glassbreak_before_threshold"
    return EXPECTED_REACTION_BY_MUTATION.get(mutation, "mechanical_reject_reissue")


def _evidence_key_for_reaction(mutation: str, expected_reaction: str) -> str:
    if mutation.startswith("malformed_body."):
        return "malformed_body"
    if expected_reaction == "mechanical_reject_reissue_with_options":
        return "wrong_allowed_value"
    if expected_reaction == "accepted_current_contract":
        return "legal_current_contract"
    if expected_reaction == "mechanical_reject_reissue_with_owner_set":
        return "owner_set_feedback"
    if expected_reaction == "mechanical_reject_reissue_with_missing_ids":
        return "owner_set_feedback"
    if mutation == "malformed_projection_row":
        return "owner_set_feedback"
    if expected_reaction == "accepted_after_reissue":
        return "corrected_retry"
    if expected_reaction == "breakglass_after_fifth_same_failure":
        return "breakglass_threshold"
    if expected_reaction == "reviewer_blocker_or_reissue_first_failure":
        return "review_window_profile"
    if expected_reaction.endswith("without_glassbreak_before_threshold"):
        return "normal_before_threshold"
    if mutation in REVIEW_WINDOW_FAKE_AI_PROFILE_IDS:
        return "review_window_profile"
    return "corrected_retry"


def _attempt_class(expected_reaction: str) -> str:
    if expected_reaction == "accepted_current_contract":
        return "accepted_first_attempt"
    if expected_reaction == "accepted_after_reissue":
        return "corrected_second_attempt"
    if expected_reaction == "breakglass_after_fifth_same_failure":
        return "same_failure_attempt_5"
    if expected_reaction == "reviewer_blocker_or_reissue_first_failure":
        return "first_failure"
    if expected_reaction.endswith("without_glassbreak_before_threshold"):
        return "same_failure_attempts_1_to_4"
    return "first_failure"


def _runtime_replay_cell(
    *,
    source_cell: Mapping[str, Any],
    contract_id: str,
    source: str,
    family: str,
) -> dict[str, Any]:
    mutation = str(source_cell.get("mutation_kind") or "")
    expected_reaction = _expected_reaction(mutation, source_cell)
    evidence_key = _evidence_key_for_reaction(mutation, expected_reaction)
    source_cell_id = str(source_cell.get("cell_id") or f"{contract_id}.{mutation}.{source_cell.get('field_path', '')}")
    return {
        "cell_id": f"runtime_replay.{contract_id}.{source_cell_id}",
        "source_cell_id": source_cell_id,
        "source_matrix": source,
        "family": family,
        "contract_family_id": contract_id,
        "contract_path": str(source_cell.get("contract_path") or source_cell.get("field_path") or "result.body"),
        "mutation_kind": mutation,
        "branch_kind": "runtime_replay",
        "confidence_boundary": "synthetic_non_live_runtime_replay",
        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
        "attempt_class": _attempt_class(expected_reaction),
        "expected_runtime_reaction": expected_reaction,
        "expected_test_name": CONCRETE_RUNTIME_TESTS[evidence_key],
        "glass_break_allowed": expected_reaction == "breakglass_after_fifth_same_failure",
        "normal_path_required": expected_reaction != "breakglass_after_fifth_same_failure",
        "live_completion_allowed": False,
    }


def _integration_expected_reaction(cell: Mapping[str, Any]) -> str:
    outcome = str(cell["expected_outcome"])
    if outcome == "continue_current_flow":
        return "continue_current_flow_without_runtime_blocker"
    if outcome == "pm_suggestion":
        return "pm_integration_suggestion_without_runtime_blocker"
    if outcome == "same_node_repair":
        return "pm_same_node_integration_repair"
    if outcome == "route_mutation":
        return "pm_route_mutation_for_integration"
    if outcome == "model_miss_triage":
        return "pm_model_miss_triage"
    if outcome == "terminal_block":
        return "terminal_composition_block_from_existing_gate"
    return "pm_integration_disposition"


def _integration_evidence_key(cell: Mapping[str, Any]) -> str:
    if str(cell["authority"]) == "runtime_mechanical_rejection" or str(cell["role"]) == "worker":
        return "integration_authority_boundary"
    if str(cell["expected_outcome"]) == "model_miss_triage":
        return "integration_hazards"
    if str(cell["expected_outcome"]) in {"same_node_repair", "route_mutation", "terminal_block"}:
        return "integration_hard_failure"
    return "integration_full_matrix"


def _integration_runtime_replay_cells() -> tuple[dict[str, Any], ...]:
    representatives: dict[tuple[str, str, str, str], Mapping[str, Any]] = {}
    for cell in integration_cartesian_cells():
        key = (
            str(cell["failure_class"]),
            str(cell["severity"]),
            str(cell["authority"]),
            str(cell["expected_outcome"]),
        )
        representatives.setdefault(key, cell)
    return tuple(
        {
            "cell_id": f"runtime_replay.flowpilot_integration_cartesian_coverage.{cell['cell_id']}",
            "source_cell_id": str(cell["cell_id"]),
            "source_matrix": "integration_cartesian_coverage",
            "family": "system_integration_result",
            "contract_family_id": "flowpilot_integration_cartesian_coverage",
            "contract_path": str(cell["coverage_shard_id"]),
            "mutation_kind": str(cell["failure_class"]),
            "branch_kind": "runtime_replay",
            "confidence_boundary": "synthetic_non_live_runtime_replay",
            "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
            "attempt_class": "integration_decision",
            "expected_runtime_reaction": _integration_expected_reaction(cell),
            "expected_test_name": CONCRETE_RUNTIME_TESTS[_integration_evidence_key(cell)],
            "glass_break_allowed": False,
            "normal_path_required": True,
            "live_completion_allowed": False,
            "semantic_runtime_blocker_allowed": False,
            "worker_current_gate_blocker_allowed": False,
        }
        for cell in representatives.values()
    )


def _parent_entry_return_path_replay_cells() -> tuple[dict[str, Any], ...]:
    reactions = {
        "missing_node_acceptance_plan": "return_to_pm_node_acceptance_plan",
        "missing_node_context_package": "return_to_pm_node_acceptance_plan",
        "missing_parent_backward_replay": "return_to_parent_backward_replay",
        "missing_pm_disposition": "return_to_pm_disposition",
        "active_packet_unresolved": "return_to_current_packet_repair",
        "stale_current_evidence": "return_to_pm_node_acceptance_plan",
    }
    rows: list[dict[str, Any]] = []
    for gate_type in PARENT_ENTRY_GATE_TYPES:
        for topology in PARENT_ENTRY_SUBJECT_TOPOLOGIES:
            for stage in PARENT_ENTRY_DETECTION_STAGES:
                cell_id = f"{gate_type}.{topology}.{stage}"
                rows.append(
                    {
                        "cell_id": f"runtime_replay.parent_entry_return_path.{cell_id}",
                        "source_cell_id": cell_id,
                        "source_matrix": "parent_entry_return_path_cartesian",
                        "family": "runtime_hard_gate_return_path",
                        "contract_family_id": "flowpilot_parent_entry_return_path",
                        "contract_path": f"{stage}:{topology}",
                        "mutation_kind": f"hard_gate_escape.{gate_type}",
                        "branch_kind": "runtime_replay",
                        "confidence_boundary": "synthetic_non_live_runtime_replay",
                        "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
                        "attempt_class": "runtime_hard_gate_escape",
                        "expected_runtime_reaction": reactions[gate_type],
                        "expected_test_name": CONCRETE_RUNTIME_TESTS["parent_entry_return_path"],
                        "glass_break_allowed": False,
                        "normal_path_required": True,
                        "live_completion_allowed": False,
                        "final_quality_review_allowed": False,
                        "fallback_allowed": False,
                        "gate_type": gate_type,
                        "subject_topology": topology,
                        "detection_stage": stage,
                    }
                )
    return tuple(rows)


def _runtime_owned_bad_ai_replay_cells() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "cell_id": f"runtime_replay.runtime_owned_bad_ai.{cell['cell_id']}",
            "source_cell_id": cell["cell_id"],
            "source_matrix": "runtime_owned_bad_ai_submit_and_reviewer_boundary",
            "family": cell["family"],
            "contract_family_id": cell["contract_family_id"],
            "contract_path": cell["contract_path"],
            "mutation_kind": cell["mutation_kind"],
            "branch_kind": "runtime_replay",
            "confidence_boundary": "synthetic_non_live_runtime_replay",
            "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
            "attempt_class": "runtime_hard_reject" if cell["family"] == "submit_result_body_entry" else "runtime_boundary",
            "expected_runtime_reaction": cell["expected_runtime_reaction"],
            "expected_test_name": CONCRETE_RUNTIME_TESTS[cell["expected_test_key"]],
            "glass_break_allowed": False,
            "normal_path_required": True,
            "live_completion_allowed": False,
            "semantic_runtime_blocker_allowed": False,
            "fallback_allowed": False,
        }
        for cell in RUNTIME_OWNED_BAD_AI_REPLAY_CELLS
    )


def _global_standard_context_replay_cells() -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "cell_id": f"runtime_replay.global_standard_context.{cell['cell_id']}",
            "source_cell_id": cell["cell_id"],
            "source_matrix": "global_standard_context_fake_ai_matrix",
            "family": cell["family"],
            "contract_family_id": cell["contract_family_id"],
            "contract_path": cell["contract_path"],
            "mutation_kind": cell["mutation_kind"],
            "branch_kind": "runtime_replay",
            "confidence_boundary": "synthetic_non_live_runtime_replay",
            "required_evidence_owner": REQUIRED_EVIDENCE_OWNER,
            "attempt_class": "semantic_review_or_process_block",
            "expected_runtime_reaction": cell["expected_runtime_reaction"],
            "expected_test_name": CONCRETE_RUNTIME_TESTS[cell["expected_test_key"]],
            "glass_break_allowed": False,
            "normal_path_required": True,
            "live_completion_allowed": False,
            "semantic_runtime_blocker_allowed": False,
            "fallback_allowed": False,
            "runtime_mechanical_only": True,
        }
        for cell in GLOBAL_STANDARD_CONTEXT_REPLAY_CELLS
    )


def iter_runtime_replay_cells(
    *,
    include_control_plane_hygiene: bool = True,
) -> Iterable[dict[str, Any]]:
    for contract_id, contract in _responder_contracts().items():
        responder = ContractDrivenFakeAIResponder(contract)
        for cell in responder.coverage_cells():
            yield _runtime_replay_cell(
                source_cell=cell,
                contract_id=contract_id,
                source="contract_driven_fake_ai_responder",
                family=_contract_family_bucket(contract_id),
            )
    for cell in review_window_behavior_cells():
        flow_id = str(cell["review_flow_id"])
        yield _runtime_replay_cell(
            source_cell=cell,
            contract_id=flow_id,
            source="review_window_fake_ai_responder",
            family="review_window_result",
        )
    yield from _integration_runtime_replay_cells()
    yield from _parent_entry_return_path_replay_cells()
    yield from _runtime_owned_bad_ai_replay_cells()
    yield from _global_standard_context_replay_cells()
    if include_control_plane_hygiene:
        yield from control_plane_ledger_hygiene_cells()


def runtime_replay_cells() -> tuple[dict[str, Any], ...]:
    return tuple(iter_runtime_replay_cells())


@lru_cache(maxsize=1)
def runtime_replay_declaration_summary() -> dict[str, Any]:
    """Compact child-model receipt for parents that must not inline all cells."""

    digest = hashlib.sha256()
    count = 0
    reactions: Counter[str] = Counter()
    finding_counts: Counter[str] = Counter()
    for cell in iter_runtime_replay_cells(include_control_plane_hygiene=False):
        count += 1
        cell_id = str(cell.get("cell_id") or "")
        reaction = str(cell.get("expected_runtime_reaction") or "")
        owner = str(cell.get("required_evidence_owner") or "")
        digest.update(cell_id.encode("utf-8"))
        digest.update(b"\0")
        digest.update(reaction.encode("utf-8"))
        digest.update(b"\0")
        digest.update(owner.encode("utf-8"))
        digest.update(b"\n")
        reactions[reaction] += 1
        if not cell_id:
            finding_counts["missing_cell_id"] += 1
        if owner != REQUIRED_EVIDENCE_OWNER:
            finding_counts["wrong_owner"] += 1
        if not reaction:
            finding_counts["missing_reaction"] += 1
    hygiene = control_plane_ledger_hygiene_declaration_summary()
    combined_digest = hashlib.sha256()
    combined_digest.update(digest.hexdigest().encode("ascii"))
    combined_digest.update(b"\0")
    combined_digest.update(str(hygiene["cell_receipt_sha256"]).encode("ascii"))
    total_reactions = Counter(reactions)
    total_reactions.update(hygiene["by_reaction"])
    return {
        "ok": not finding_counts and hygiene["ok"],
        "owner": REQUIRED_EVIDENCE_OWNER,
        "non_hygiene_declared_cell_count": count,
        "non_hygiene_receipt_sha256": digest.hexdigest(),
        "non_hygiene_by_reaction": dict(sorted(reactions.items())),
        "control_plane_ledger_hygiene": hygiene,
        "declared_cell_count": count + int(hygiene["declared_cell_count"]),
        "cell_receipt_sha256": combined_digest.hexdigest(),
        "by_reaction": dict(sorted(total_reactions.items())),
        "finding_counts": dict(sorted(finding_counts.items())),
    }


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    fake_ai_fault_seen: bool = False
    runtime_rejected_or_blocked: bool = False
    feedback_actionable: bool = False
    reissue_or_repair_seen: bool = False
    corrected_second_retry_seen: bool = False
    same_failure_attempts: int = 0
    breakglass_triggered: bool = False
    accepted: bool = False
    synthetic_only: bool = True
    live_completion_claimed: bool = False
    integration_hard_failure_seen: bool = False
    pm_integration_disposition_seen: bool = False
    integration_advisory_only: bool = False
    runtime_semantic_hard_blocker: bool = False
    worker_current_gate_blocker: bool = False
    integration_model_miss_candidate_seen: bool = False
    model_miss_triage_seen: bool = False
    hard_gate_escape_seen: bool = False
    hard_gate_returned_to_owner_gate: bool = False
    hard_gate_breakglass_triggered: bool = False
    hard_gate_sent_to_final_quality_review: bool = False


@dataclass(frozen=True)
class Tick:
    """One fake-AI runtime replay transition."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _valid_first_reissue() -> State:
    return State(
        scenario="valid_first_reissue",
        status="selected",
        fake_ai_fault_seen=True,
        runtime_rejected_or_blocked=True,
        feedback_actionable=True,
        reissue_or_repair_seen=True,
    )


def _valid_corrected_second() -> State:
    return State(
        scenario="valid_corrected_second",
        status="selected",
        fake_ai_fault_seen=True,
        runtime_rejected_or_blocked=True,
        feedback_actionable=True,
        reissue_or_repair_seen=True,
        corrected_second_retry_seen=True,
        accepted=True,
    )


def _valid_attempts_one_to_four() -> State:
    return State(
        scenario="valid_attempts_one_to_four",
        status="selected",
        fake_ai_fault_seen=True,
        runtime_rejected_or_blocked=True,
        feedback_actionable=True,
        reissue_or_repair_seen=True,
        same_failure_attempts=4,
    )


def _valid_fifth_breakglass() -> State:
    return State(
        scenario="valid_fifth_breakglass",
        status="selected",
        fake_ai_fault_seen=True,
        runtime_rejected_or_blocked=True,
        feedback_actionable=True,
        same_failure_attempts=5,
        breakglass_triggered=True,
    )


def _valid_integration_hard_pm_disposition() -> State:
    return State(
        scenario="valid_integration_hard_pm_disposition",
        status="selected",
        integration_hard_failure_seen=True,
        pm_integration_disposition_seen=True,
    )


def _valid_integration_advisory_pm_support() -> State:
    return State(
        scenario="valid_integration_advisory_pm_support",
        status="selected",
        integration_advisory_only=True,
        pm_integration_disposition_seen=True,
    )


def _valid_integration_model_miss_triage() -> State:
    return State(
        scenario="valid_integration_model_miss_triage",
        status="selected",
        integration_model_miss_candidate_seen=True,
        model_miss_triage_seen=True,
    )


def _valid_hard_gate_escape_owner_return() -> State:
    return State(
        scenario="valid_hard_gate_escape_owner_return",
        status="selected",
        hard_gate_escape_seen=True,
        hard_gate_returned_to_owner_gate=True,
    )


SCENARIOS: dict[str, State] = {
    "valid_first_reissue": _valid_first_reissue(),
    "valid_corrected_second": _valid_corrected_second(),
    "valid_attempts_one_to_four": _valid_attempts_one_to_four(),
    "valid_fifth_breakglass": _valid_fifth_breakglass(),
    "valid_integration_hard_pm_disposition": _valid_integration_hard_pm_disposition(),
    "valid_integration_advisory_pm_support": _valid_integration_advisory_pm_support(),
    "valid_integration_model_miss_triage": _valid_integration_model_miss_triage(),
    "valid_hard_gate_escape_owner_return": _valid_hard_gate_escape_owner_return(),
}

VALID_SCENARIOS = tuple(SCENARIOS)
NEGATIVE_SCENARIOS = (
    "missing_actionable_feedback",
    "corrected_second_still_blocked",
    "attempts_one_to_four_glassbreak",
    "fifth_attempt_no_glassbreak",
    "synthetic_claims_live_completion",
    "integration_hard_underblocked",
    "integration_advisory_runtime_overblock",
    "integration_worker_current_gate_blocker",
    "integration_model_miss_without_triage",
    "hard_gate_escape_not_returned_to_owner",
    "hard_gate_escape_entered_breakglass",
    "hard_gate_escape_entered_final_quality_review",
)


def hazard_states() -> dict[str, State]:
    return {
        "missing_actionable_feedback": replace(_valid_first_reissue(), feedback_actionable=False),
        "corrected_second_still_blocked": replace(_valid_corrected_second(), accepted=False),
        "attempts_one_to_four_glassbreak": replace(
            _valid_attempts_one_to_four(),
            breakglass_triggered=True,
        ),
        "fifth_attempt_no_glassbreak": replace(_valid_fifth_breakglass(), breakglass_triggered=False),
        "synthetic_claims_live_completion": replace(_valid_corrected_second(), live_completion_claimed=True),
        "integration_hard_underblocked": replace(
            _valid_integration_hard_pm_disposition(),
            pm_integration_disposition_seen=False,
        ),
        "integration_advisory_runtime_overblock": replace(
            _valid_integration_advisory_pm_support(),
            runtime_semantic_hard_blocker=True,
        ),
        "integration_worker_current_gate_blocker": replace(
            _valid_integration_advisory_pm_support(),
            worker_current_gate_blocker=True,
        ),
        "integration_model_miss_without_triage": replace(
            _valid_integration_model_miss_triage(),
            model_miss_triage_seen=False,
        ),
        "hard_gate_escape_not_returned_to_owner": replace(
            _valid_hard_gate_escape_owner_return(),
            hard_gate_returned_to_owner_gate=False,
        ),
        "hard_gate_escape_entered_breakglass": replace(
            _valid_hard_gate_escape_owner_return(),
            hard_gate_breakglass_triggered=True,
        ),
        "hard_gate_escape_entered_final_quality_review": replace(
            _valid_hard_gate_escape_owner_return(),
            hard_gate_sent_to_final_quality_review=True,
        ),
    }


def runtime_replay_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.fake_ai_fault_seen and state.runtime_rejected_or_blocked and not state.feedback_actionable:
        failures.append("runtime_replay_rejection_lacked_actionable_feedback")
    if state.corrected_second_retry_seen and not state.accepted:
        failures.append("corrected_second_retry_did_not_return_to_accepted_path")
    if 1 <= state.same_failure_attempts <= 4 and state.breakglass_triggered:
        failures.append("attempts_one_to_four_entered_glassbreak")
    if state.same_failure_attempts >= 5 and not state.breakglass_triggered:
        failures.append("fifth_same_failure_did_not_trigger_glassbreak")
    if state.synthetic_only and state.live_completion_claimed:
        failures.append("synthetic_replay_claimed_live_completion")
    if state.integration_hard_failure_seen and not state.pm_integration_disposition_seen:
        failures.append("hard_integration_failure_lacked_pm_disposition")
    if state.integration_advisory_only and state.runtime_semantic_hard_blocker:
        failures.append("advisory_integration_finding_became_runtime_hard_blocker")
    if state.worker_current_gate_blocker:
        failures.append("worker_claimed_current_gate_blocker_for_integration")
    if state.integration_model_miss_candidate_seen and not state.model_miss_triage_seen:
        failures.append("integration_model_miss_candidate_lacked_triage")
    if state.hard_gate_escape_seen and not state.hard_gate_returned_to_owner_gate:
        failures.append("hard_gate_escape_did_not_return_to_owner_gate")
    if state.hard_gate_escape_seen and state.hard_gate_breakglass_triggered:
        failures.append("hard_gate_escape_entered_breakglass")
    if state.hard_gate_escape_seen and state.hard_gate_sent_to_final_quality_review:
        failures.append("hard_gate_escape_entered_final_quality_review")
    return failures


def expected_failures_by_hazard() -> dict[str, tuple[str, ...]]:
    return {name: tuple(runtime_replay_failures(state)) for name, state in hazard_states().items()}


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in SCENARIOS.items():
            yield Transition(f"select_{name}", scenario)
    elif state.status == "selected":
        if runtime_replay_failures(state):
            yield Transition(f"reject_{state.scenario}", replace(state, status="rejected"))
        else:
            yield Transition(f"accept_{state.scenario}", replace(state, status="accepted"))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def invariant_failures(state: State) -> list[str]:
    return runtime_replay_failures(state)


class RuntimeReplayStep:
    name = "runtime_replay_step"
    reads = ("fake_ai_result", "runtime_feedback", "retry_lineage")
    writes = ("replay_disposition",)
    input_description = "one fake-AI runtime replay matrix step"
    state_description = "current replay state"
    output_description = "accepted/rejected replay disposition"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def runtime_replay_states_are_safe(state: State, _trace: object = ()) -> InvariantResult:
    if state.status == "accepted":
        failures = runtime_replay_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not runtime_replay_failures(state):
        return InvariantResult.fail("safe fake-AI runtime replay state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "fake_ai_runtime_replay_safety",
        "Accepted fake-AI replay states cannot miss feedback, overuse GlassBreak, skip the fifth-attempt fuse, claim live completion, or lose the PM-owned system-integration boundary.",
        runtime_replay_states_are_safe,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((RuntimeReplayStep(),), name=MODEL_ID)


def cell_findings(
    cells: Iterable[Mapping[str, Any]] | None = None,
    *,
    hygiene_summary: Mapping[str, Any] | None = None,
) -> list[dict[str, str]]:
    rows = list(
        cells
        if cells is not None
        else iter_runtime_replay_cells(include_control_plane_hygiene=False)
    )
    hygiene = dict(hygiene_summary or control_plane_ledger_hygiene_declaration_summary())
    findings: list[dict[str, str]] = []
    required_mutations = {
        *(f"malformed_body.{profile}" for profile in MALFORMED_BODY_PROFILE_IDS),
        *PROJECTION_GAP_PROFILE_IDS,
        *RETRY_PROFILE_IDS,
        *REVIEW_WINDOW_FAKE_AI_PROFILE_IDS,
        "empty_required_array",
        "forbidden_alias_used",
        "missing_required_child_field",
        "missing_required_field",
        "wrong_allowed_value",
        "wrong_type",
        *(f"hard_gate_escape.{gate_type}" for gate_type in PARENT_ENTRY_GATE_TYPES),
        *(cell["mutation_kind"] for cell in RUNTIME_OWNED_BAD_AI_REPLAY_CELLS),
        *(cell["mutation_kind"] for cell in GLOBAL_STANDARD_CONTEXT_REPLAY_CELLS),
    }
    mutations = {str(row.get("mutation_kind") or "") for row in rows}
    for mutation in sorted(required_mutations - mutations):
        findings.append({"code": "missing_runtime_replay_mutation", "mutation_kind": mutation})
    for code, failure_count in sorted(dict(hygiene.get("finding_counts") or {}).items()):
        findings.append(
            {
                "code": f"control_plane_ledger_hygiene:{code}",
                "failure_count": str(failure_count),
            }
        )
    for row in rows:
        for field in (
            "cell_id",
            "source_cell_id",
            "contract_family_id",
            "mutation_kind",
            "expected_runtime_reaction",
            "attempt_class",
            "expected_test_name",
            "required_evidence_owner",
            "confidence_boundary",
        ):
            if not row.get(field):
                findings.append(
                    {
                        "code": "missing_runtime_replay_cell_field",
                        "cell_id": str(row.get("cell_id") or ""),
                        "field": field,
                    }
                )
        expected_owner = (
            CONTROL_PLANE_LEDGER_HYGIENE_OWNER
            if row.get("source_matrix") == CONTROL_PLANE_LEDGER_HYGIENE_SOURCE
            else REQUIRED_EVIDENCE_OWNER
        )
        if row.get("required_evidence_owner") != expected_owner:
            findings.append(
                {
                    "code": "wrong_runtime_replay_owner",
                    "cell_id": str(row.get("cell_id") or ""),
                }
            )
        if row.get("expected_runtime_reaction") == "breakglass_after_fifth_same_failure":
            if row.get("attempt_class") != "same_failure_attempt_5" or row.get("glass_break_allowed") is not True:
                findings.append(
                    {
                        "code": "breakglass_threshold_cell_not_fifth_attempt",
                        "cell_id": str(row.get("cell_id") or ""),
                    }
                )
        elif row.get("glass_break_allowed") is True:
            findings.append(
                {
                    "code": "normal_repair_cell_allows_glassbreak",
                    "cell_id": str(row.get("cell_id") or ""),
                }
            )
        if row.get("source_matrix") == CONTROL_PLANE_LEDGER_HYGIENE_SOURCE:
            if row.get("required_evidence_owner") != CONTROL_PLANE_LEDGER_HYGIENE_OWNER:
                findings.append(
                    {
                        "code": "control_plane_ledger_hygiene_wrong_owner",
                        "cell_id": str(row.get("cell_id") or ""),
                    }
                )
            if row.get("expected_runtime_reaction") not in CONTROL_PLANE_LEDGER_HYGIENE_REACTIONS:
                findings.append(
                    {
                        "code": "control_plane_ledger_hygiene_unknown_reaction",
                        "cell_id": str(row.get("cell_id") or ""),
                        "expected_runtime_reaction": str(row.get("expected_runtime_reaction") or ""),
                    }
                )
    return findings


def build_report(*, include_cells: bool = True) -> dict[str, Any]:
    cells = list(iter_runtime_replay_cells(include_control_plane_hygiene=False))
    hygiene = control_plane_ledger_hygiene_declaration_summary()
    findings = cell_findings(cells, hygiene_summary=hygiene)
    by_mutation = Counter(str(cell["mutation_kind"]) for cell in cells)
    by_reaction = Counter(str(cell["expected_runtime_reaction"]) for cell in cells)
    by_attempt = Counter(str(cell["attempt_class"]) for cell in cells)
    by_source = Counter(str(cell["source_matrix"]) for cell in cells)
    for reaction, reaction_count in dict(hygiene["by_reaction"]).items():
        by_mutation[f"control_plane_ledger_hygiene.{reaction}"] += int(reaction_count)
        by_reaction[str(reaction)] += int(reaction_count)
    hygiene_count = int(hygiene["declared_cell_count"])
    by_attempt["cartesian_control_plane_ledger_hygiene"] += hygiene_count
    by_source[CONTROL_PLANE_LEDGER_HYGIENE_SOURCE] += hygiene_count
    expected_test_names = {str(cell["expected_test_name"]) for cell in cells}
    expected_test_names.add(
        "tests.test_flowpilot_fake_ai_runtime_replay."
        "FlowPilotFakeAIRuntimeReplayTests."
        "test_control_plane_ledger_hygiene_fake_ai_matrix_is_cartesian"
    )
    report = {
        "ok": not findings,
        "model_id": MODEL_ID,
        "result_path": RESULT_PATH,
        "coverage_boundary": "synthetic_non_live_runtime_replay",
        "live_ai_semantic_quality_proven": False,
        "product_completion_proven": False,
        "cell_count": len(cells) + hygiene_count,
        "by_mutation_kind": dict(sorted(by_mutation.items())),
        "by_expected_runtime_reaction": dict(sorted(by_reaction.items())),
        "by_attempt_class": dict(sorted(by_attempt.items())),
        "by_source_matrix": dict(sorted(by_source.items())),
        "control_plane_ledger_hygiene": {
            "owner": CONTROL_PLANE_LEDGER_HYGIENE_OWNER,
            "axis_names": list(CONTROL_PLANE_LEDGER_HYGIENE_AXES),
            "axis_sizes": {name: len(values) for name, values in CONTROL_PLANE_LEDGER_HYGIENE_AXES.items()},
            "expected_cell_count": CONTROL_PLANE_LEDGER_HYGIENE_EXPECTED_CELL_COUNT,
            "actual_cell_count": hygiene_count,
            "cell_receipt_sha256": hygiene["cell_receipt_sha256"],
            "by_reaction": dict(hygiene["by_reaction"]),
            "finding_counts": dict(hygiene["finding_counts"]),
        },
        "expected_test_names": sorted(expected_test_names),
        "findings": findings,
        "cell_sample": cells[:25],
    }
    if include_cells:
        report["cells"] = [*cells, *iter_control_plane_ledger_hygiene_cells()]
    return report


def write_report(path: Path | str = RESULT_PATH, *, include_cells: bool = False) -> dict[str, Any]:
    report = build_report(include_cells=include_cells)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
