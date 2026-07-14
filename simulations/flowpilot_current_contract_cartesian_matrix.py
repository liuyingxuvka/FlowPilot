"""Current-contract FlowPilot full Cartesian scenario matrix.

This model sits above the lower-level control-plane Cartesian matrix.  The
lower layer proves boundary x mutation x context x consumer.  This layer proves
the currently narrowed FlowPilot process axes: stage, action, package/material
family, object state, AI return profile, timing, blocker/repair state, route
shape, execution source, and final-claim pressure.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
import sys
from typing import Any, Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ROOT = Path(__file__).resolve().parents[1]
ASSETS_PATH = ROOT / "skills" / "flowpilot" / "assets"
if str(ASSETS_PATH) not in sys.path:
    sys.path.insert(0, str(ASSETS_PATH))

from flowpilot_core_runtime import packet_stage_evidence_matrix as stage_matrix  # noqa: E402


MODEL_ID = "flowpilot_current_contract_cartesian_matrix"
MAX_SEQUENCE_LENGTH = 2

FLOW_STAGE_ROWS = tuple(
    {
        "family_id": family_id,
        "lifecycle_stage": str(stage_matrix.stage_evidence_row_for_family(family_id)["lifecycle_stage"]),
        "evidence_owner": str(stage_matrix.stage_evidence_row_for_family(family_id)["required_evidence_owner"]),
    }
    for family_id in stage_matrix.PACKET_FAMILY_IDS
)
STAGE_ROW_BY_FAMILY = {
    family_id: stage_matrix.stage_evidence_row_for_family(family_id)
    for family_id in stage_matrix.PACKET_FAMILY_IDS
}

FLOW_STAGE_IDS = tuple(row["family_id"] for row in FLOW_STAGE_ROWS)
PACKAGE_MATERIAL_KINDS = FLOW_STAGE_IDS

ACTION_IDS = (
    "define_contract",
    "project_future_evidence",
    "issue_packet",
    "dispatch_current_role",
    "ack_packet",
    "open_packet",
    "submit_result",
    "review_current_subject",
    "flowguard_check",
    "pm_dispose_result",
    "block_current_subject",
    "reissue_current_packet",
    "repair_current_scope",
    "repair_parent_scope",
    "redesign_route",
    "commit_route_mutation",
    "terminal_backward_replay",
    "close_route",
    "resume_current_run",
    "replay_late_result",
)

OBJECT_STATES = (
    "missing_not_due",
    "missing_due",
    "current_valid",
    "current_unopened",
    "current_progress_only",
    "stale_run",
    "stale_route",
    "stale_packet",
    "wrong_owner",
    "duplicate_conflict",
    "unreadable_path",
    "current_pointer_corrupt_unambiguous",
    "current_pointer_corrupt_ambiguous",
    "index_pointer_corrupt",
    "pointer_write_in_progress",
    "future_claim_without_evidence",
    "unsupported_legacy_shape",
)

AI_RETURN_PROFILES = (
    "runtime_no_ai",
    "well_formed_pass",
    "well_formed_block",
    "malformed_json_unquoted_keys",
    "malformed_json_markdown_wrapped",
    "malformed_json_prose_plus_json",
    "malformed_json_top_level_array",
    "malformed_json_empty_body",
    "malformed_json_trailing_comma",
    "malformed_json_stringified_object",
    "ack_only",
    "summary_only",
    "old_protocol",
    "wrong_role",
    "retired_role_alias",
    "hallucinated_artifact",
    "overclaims_completion",
    "rejects_valid_task",
    "repeated_bad_fix",
    "contradictory_result",
)

TIMING_STATES = (
    "on_time",
    "one_step_early",
    "one_step_late",
    "old_result_after_reissue",
    "new_result_before_old",
    "resume_after_wait",
    "route_mutation_after_packet",
    "background_progress_late",
)

BLOCKER_STATES = (
    "no_blocker",
    "new_current_blocker",
    "route_decomposition",
    "stale_blocker",
    "wrong_owner_blocker",
    "solved_still_blocks",
    "unsolved_skipped",
    "same_blocker_before_threshold",
    "same_blocker_at_threshold",
    "repair_after_failed_recheck",
)

ROUTE_SHAPES = (
    "single_node",
    "multi_node",
    "parent_child",
    "route_mutation_replacement",
    "sibling_branch_replacement",
    "superseded_node",
    "parallel_background",
    "terminal_replay",
    "manual_resume",
)

CURRENT_EXECUTION_SOURCES = (
    "foreground_runtime",
    "background_role",
    "manual_resume",
    "installed_skill_self_check",
)

HISTORICAL_NEGATIVE_EXECUTION_SOURCES = (
    "daemon_replay",
    "stale_workspace",
    "old_router",
    "body_only_contract",
    "private_helper_source",
)

EXECUTION_SOURCES = CURRENT_EXECUTION_SOURCES + HISTORICAL_NEGATIVE_EXECUTION_SOURCES

ROLE_SOURCE_NEGATIVE_AI_PROFILES = (
    "wrong_role",
    "retired_role_alias",
)

SOURCE_PURITY_ENTRYPOINTS = (
    {
        "entrypoint_id": "route_planning",
        "family_id": "task.planning",
        "action": "redesign_route",
        "route_shape": "multi_node",
        "default_ai_profile": "runtime_no_ai",
    },
    {
        "entrypoint_id": "dispatch",
        "family_id": "task.node",
        "action": "dispatch_current_role",
        "route_shape": "single_node",
        "default_ai_profile": "runtime_no_ai",
    },
    {
        "entrypoint_id": "open",
        "family_id": "task.node",
        "action": "open_packet",
        "route_shape": "single_node",
        "default_ai_profile": "runtime_no_ai",
    },
    {
        "entrypoint_id": "submit",
        "family_id": "task.node",
        "action": "submit_result",
        "route_shape": "single_node",
        "default_ai_profile": "well_formed_pass",
    },
    {
        "entrypoint_id": "replay",
        "family_id": "review.terminal_backward_replay",
        "action": "terminal_backward_replay",
        "route_shape": "terminal_replay",
        "default_ai_profile": "well_formed_pass",
    },
)

SOURCE_PURITY_FAILURE_PROFILES = (
    {
        "failure_class": "wrong_role",
        "ai_profile": "wrong_role",
        "source": "foreground_runtime",
        "historical_negative": False,
    },
    {
        "failure_class": "retired_role_alias",
        "ai_profile": "retired_role_alias",
        "source": "foreground_runtime",
        "historical_negative": True,
    },
    *(
        {
            "failure_class": source,
            "ai_profile": "",
            "source": source,
            "historical_negative": True,
        }
        for source in HISTORICAL_NEGATIVE_EXECUTION_SOURCES
    ),
)

SOURCE_PURITY_REQUIRED_CELL_COUNT = len(SOURCE_PURITY_ENTRYPOINTS) * len(SOURCE_PURITY_FAILURE_PROFILES)

FINAL_CLAIM_TYPES = (
    "no_claim",
    "node_complete",
    "route_complete",
    "task_complete",
    "routine_evidence_claim",
    "release_evidence_claim",
    "future_evidence_claim",
    "live_ai_quality_claim",
)

AXIS_VALUES = {
    "flow_stage": FLOW_STAGE_IDS,
    "action": ACTION_IDS,
    "package_material_kind": PACKAGE_MATERIAL_KINDS,
    "object_state": OBJECT_STATES,
    "ai_return_profile": AI_RETURN_PROFILES,
    "timing": TIMING_STATES,
    "blocker_state": BLOCKER_STATES,
    "route_shape": ROUTE_SHAPES,
    "execution_source": EXECUTION_SOURCES,
    "final_claim_type": FINAL_CLAIM_TYPES,
}


STAGE_GROUP_BY_FAMILY = {
    "task.high_standard_contract": "preplanning",
    "task.discovery": "preplanning",
    "task.skill_standard": "preplanning",
    "task.planning": "planning",
    "task.node_acceptance_plan": "planning",
    "task.node": "result",
    "review.parent_backward_replay": "review",
    "flowguard_check.post_result": "flowguard",
    "review.any_current_subject": "review",
    "review.terminal_backward_replay": "terminal",
    "pm_repair_decision.pm_repair_decision": "repair",
    "pm_disposition.node_pm_disposition": "disposition",
    "pm_flowguard_acceptance.pm_flowguard_acceptance": "route_mutation",
}

PROFILE_BY_STAGE_GROUP: dict[str, dict[str, tuple[str, ...]]] = {
    "preplanning": {
        "actions": ("define_contract", "project_future_evidence", "flowguard_check"),
        "object_states": (
            "missing_not_due",
            "missing_due",
            "current_valid",
            "future_claim_without_evidence",
            "unsupported_legacy_shape",
            "wrong_owner",
        ),
        "ai_profiles": (
            "runtime_no_ai",
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "summary_only",
            "old_protocol",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "background_progress_late"),
        "blockers": ("no_blocker", "new_current_blocker", "wrong_owner_blocker", "solved_still_blocks"),
        "routes": ("single_node", "multi_node", "manual_resume"),
        "sources": ("foreground_runtime", "background_role", "manual_resume", "installed_skill_self_check"),
        "claims": ("no_claim", "future_evidence_claim", "task_complete"),
    },
    "planning": {
        "actions": ("issue_packet", "project_future_evidence", "redesign_route", "flowguard_check"),
        "object_states": (
            "missing_not_due",
            "missing_due",
            "current_valid",
            "current_unopened",
            "future_claim_without_evidence",
            "stale_route",
            "unsupported_legacy_shape",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_prose_plus_json",
            "summary_only",
            "old_protocol",
            "hallucinated_artifact",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "route_mutation_after_packet"),
        "blockers": ("no_blocker", "new_current_blocker", "route_decomposition", "wrong_owner_blocker"),
        "routes": ("single_node", "multi_node", "parent_child", "route_mutation_replacement"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "node_complete", "future_evidence_claim"),
    },
    "result": {
        "actions": ("ack_packet", "submit_result", "reissue_current_packet", "replay_late_result"),
        "object_states": (
            "missing_due",
            "current_valid",
            "current_unopened",
            "current_progress_only",
            "stale_run",
            "stale_route",
            "stale_packet",
            "wrong_owner",
            "duplicate_conflict",
            "unreadable_path",
            "current_pointer_corrupt_unambiguous",
            "current_pointer_corrupt_ambiguous",
            "index_pointer_corrupt",
            "pointer_write_in_progress",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "well_formed_block",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "malformed_json_prose_plus_json",
            "malformed_json_top_level_array",
            "malformed_json_empty_body",
            "malformed_json_trailing_comma",
            "malformed_json_stringified_object",
            "ack_only",
            "summary_only",
            "old_protocol",
            "hallucinated_artifact",
            "overclaims_completion",
            "repeated_bad_fix",
            "contradictory_result",
            "rejects_valid_task",
        ),
        "timing": (
            "on_time",
            "old_result_after_reissue",
            "new_result_before_old",
            "resume_after_wait",
            "route_mutation_after_packet",
            "background_progress_late",
        ),
        "blockers": (
            "no_blocker",
            "new_current_blocker",
            "stale_blocker",
            "same_blocker_before_threshold",
            "same_blocker_at_threshold",
            "repair_after_failed_recheck",
        ),
        "routes": (
            "single_node",
            "multi_node",
            "parent_child",
            "route_mutation_replacement",
            "sibling_branch_replacement",
            "superseded_node",
            "parallel_background",
        ),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "node_complete", "future_evidence_claim", "live_ai_quality_claim"),
    },
    "review": {
        "actions": ("review_current_subject", "block_current_subject", "reissue_current_packet"),
        "object_states": (
            "missing_not_due",
            "missing_due",
            "current_valid",
            "current_progress_only",
            "stale_packet",
            "wrong_owner",
            "future_claim_without_evidence",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "well_formed_block",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "malformed_json_prose_plus_json",
            "malformed_json_top_level_array",
            "malformed_json_empty_body",
            "malformed_json_trailing_comma",
            "summary_only",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "background_progress_late"),
        "blockers": ("no_blocker", "new_current_blocker", "wrong_owner_blocker", "solved_still_blocks", "unsolved_skipped"),
        "routes": ("single_node", "parent_child", "terminal_replay"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "node_complete", "route_complete", "future_evidence_claim"),
    },
    "flowguard": {
        "actions": ("flowguard_check", "reissue_current_packet", "block_current_subject"),
        "object_states": (
            "missing_not_due",
            "missing_due",
            "current_valid",
            "stale_run",
            "stale_route",
            "current_progress_only",
            "future_claim_without_evidence",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "malformed_json_prose_plus_json",
            "malformed_json_top_level_array",
            "malformed_json_empty_body",
            "malformed_json_trailing_comma",
            "summary_only",
            "old_protocol",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "background_progress_late"),
        "blockers": ("no_blocker", "new_current_blocker", "same_blocker_before_threshold", "same_blocker_at_threshold"),
        "routes": ("single_node", "parent_child", "route_mutation_replacement", "terminal_replay"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "node_complete", "future_evidence_claim", "live_ai_quality_claim"),
    },
    "repair": {
        "actions": ("repair_current_scope", "repair_parent_scope", "redesign_route", "reissue_current_packet"),
        "object_states": (
            "missing_due",
            "current_valid",
            "stale_packet",
            "wrong_owner",
            "duplicate_conflict",
            "future_claim_without_evidence",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "summary_only",
            "overclaims_completion",
            "repeated_bad_fix",
            "contradictory_result",
        ),
        "timing": ("on_time", "one_step_late", "old_result_after_reissue", "resume_after_wait"),
        "blockers": (
            "new_current_blocker",
            "stale_blocker",
            "wrong_owner_blocker",
            "same_blocker_before_threshold",
            "same_blocker_at_threshold",
            "repair_after_failed_recheck",
        ),
        "routes": ("single_node", "parent_child", "route_mutation_replacement", "sibling_branch_replacement"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "node_complete", "route_complete"),
    },
    "route_mutation": {
        "actions": ("flowguard_check", "redesign_route", "commit_route_mutation", "review_current_subject"),
        "object_states": (
            "missing_due",
            "current_valid",
            "stale_route",
            "stale_packet",
            "wrong_owner",
            "future_claim_without_evidence",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_prose_plus_json",
            "summary_only",
            "hallucinated_artifact",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_early", "route_mutation_after_packet", "old_result_after_reissue"),
        "blockers": ("no_blocker", "new_current_blocker", "stale_blocker", "unsolved_skipped"),
        "routes": ("route_mutation_replacement", "sibling_branch_replacement", "superseded_node", "parent_child"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "route_complete", "future_evidence_claim"),
    },
    "disposition": {
        "actions": ("pm_dispose_result", "block_current_subject", "repair_current_scope", "redesign_route"),
        "object_states": (
            "missing_due",
            "current_valid",
            "current_progress_only",
            "stale_packet",
            "wrong_owner",
            "duplicate_conflict",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "summary_only",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_late", "old_result_after_reissue", "background_progress_late"),
        "blockers": ("no_blocker", "new_current_blocker", "stale_blocker", "solved_still_blocks", "unsolved_skipped"),
        "routes": ("single_node", "parent_child", "route_mutation_replacement"),
        "sources": ("foreground_runtime", "background_role"),
        "claims": ("no_claim", "node_complete", "future_evidence_claim"),
    },
    "replay": {
        "actions": ("review_current_subject", "block_current_subject", "repair_parent_scope"),
        "object_states": ("missing_due", "current_valid", "stale_route", "wrong_owner", "future_claim_without_evidence"),
        "ai_profiles": (
            "well_formed_pass",
            "well_formed_block",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "summary_only",
            "overclaims_completion",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "route_mutation_after_packet"),
        "blockers": ("no_blocker", "new_current_blocker", "stale_blocker", "unsolved_skipped"),
        "routes": ("parent_child", "sibling_branch_replacement", "terminal_replay"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("no_claim", "route_complete", "future_evidence_claim"),
    },
    "terminal": {
        "actions": ("terminal_backward_replay", "close_route", "block_current_subject", "resume_current_run"),
        "object_states": (
            "missing_due",
            "current_valid",
            "current_progress_only",
            "stale_run",
            "stale_route",
            "wrong_owner",
            "future_claim_without_evidence",
        ),
        "ai_profiles": (
            "well_formed_pass",
            "malformed_json_unquoted_keys",
            "malformed_json_markdown_wrapped",
            "malformed_json_empty_body",
            "summary_only",
            "overclaims_completion",
            "contradictory_result",
        ),
        "timing": ("on_time", "one_step_early", "one_step_late", "background_progress_late"),
        "blockers": ("no_blocker", "new_current_blocker", "stale_blocker", "solved_still_blocks", "unsolved_skipped"),
        "routes": ("multi_node", "parent_child", "terminal_replay", "manual_resume"),
        "sources": ("foreground_runtime", "background_role", "manual_resume"),
        "claims": ("node_complete", "route_complete", "task_complete", "routine_evidence_claim", "release_evidence_claim", "future_evidence_claim", "live_ai_quality_claim"),
    },
}


NOT_APPLICABLE_CLASSES = (
    {
        "class_id": "global_cross_stage_product_not_materialized",
        "reason": "The full unrestricted cross of every axis would combine stages with actions and materials that no current runtime owner can produce.",
    },
    {
        "class_id": "legacy_protocol_positive_path_forbidden",
        "reason": "Legacy aliases, heartbeat recovery, old role recovery, fallback prose, and old-router surfaces are negative or historical-only cells.",
    },
    {
        "class_id": "noncurrent_execution_source_positive_path_forbidden",
        "reason": "Daemon replay, stale workspace, old router, body-only contract, and private-helper sources are historical negative inputs only; every current entrypoint must reject them mechanically.",
    },
    {
        "class_id": "terminal_claim_not_applicable_before_terminal_or_result_stage",
        "reason": "Preplanning and plan packets may project future evidence but cannot claim terminal proof as present.",
    },
    {
        "class_id": "glassbreak_not_current_contract_success_path",
        "reason": "GlassBreak is an emergency stop or historical negative signal, not a passing current-contract path. Repeated blockers must be absorbed by structured repair, reissue, PM disposition, or route redesign.",
    },
)


EXISTING_TEST_LINKS = (
    {
        "link_id": "contract_surface_reduction_current_matrix",
        "path": "tests/test_flowpilot_contract_surface_reduction.py",
        "test_name": "test_every_packet_result_family_has_current_matrix_row",
        "covers": ("stage_matrix_rows", "deleted_fields_negative_only"),
        "required_markers": ("stage_evidence_row_for_family", "legacy.unknown_family", "assertRaises"),
    },
    {
        "link_id": "cartesian_control_plane_existing_matrix",
        "path": "tests/test_flowpilot_cartesian_control_plane_exhaustion.py",
        "test_name": "test_compatibility_and_fallback_surfaces_are_rejected",
        "covers": ("unsupported_legacy_shape", "fallback_prose", "legacy_alias"),
        "required_markers": ("mechanical_reject", "unsupported_shape_rejected", "legacy_alias"),
    },
    {
        "link_id": "synthetic_non_live_boundary",
        "path": "tests/test_flowpilot_synthetic_agent_coverage_matrix.py",
        "test_name": "test_synthetic_rows_are_non_live_and_backed_by_trace_tests",
        "covers": ("synthetic_ai_profiles", "live_ai_quality_claim_rejected"),
        "required_markers": ("live_completion_allowed", "False", "SYNTHETIC_NON_LIVE_KINDS"),
    },
    {
        "link_id": "fake_project_current_contract_bodies",
        "path": "tests/test_flowpilot_fake_project_rehearsal.py",
        "test_name": "test_fake_project_success_bodies_use_declared_contract_fields",
        "covers": ("fake_ai_current_contract_shapes", "existing_test_duplicate_cells"),
        "required_markers": ("undeclared_success_fields_for_family", "forbidden_success_fields_for_family"),
    },
    {
        "link_id": "fake_ai_malformed_body_profiles",
        "path": "tests/test_flowpilot_ai_contract_projection.py",
        "test_name": "test_contract_driven_fake_ai_malformed_body_profiles_reissue_with_strict_json_feedback",
        "covers": ("malformed_json_profiles", "strict_json_object_reissue"),
        "required_markers": ("MALFORMED_BODY_PROFILE_IDS", "strict JSON object"),
    },
    {
        "link_id": "route_mutation_stale_old_evidence",
        "path": "tests/test_flowpilot_complete_system_runtime.py",
        "test_name": "test_complete_packet_flow_rejects_cockpit_direct_state_write_and_old_authority",
        "covers": ("stale_route", "stale_packet", "old_evidence_quarantine"),
        "required_markers": ("quarantined_after_route_mutation", "old_ui_evidence_unresolved"),
    },
    {
        "link_id": "current_run_no_project_root_fallback",
        "path": "tests/test_flowpilot_cartesian_control_plane_exhaustion.py",
        "test_name": "test_high_risk_cells_have_current_runtime_canaries",
        "covers": ("stale_workspace", "no_newest_run_fallback"),
        "required_markers": ("test_current_run_resolver_accepts_new_schema_and_rejects_project_root_fallback",),
    },
    {
        "link_id": "pointer_persistence_canaries",
        "path": "tests/test_flowpilot_core_runtime.py",
        "test_name": "test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
        "covers": ("pointer_recovery",),
        "required_markers": (
            "test_corrupt_current_pointer_recovers_from_single_current_run_evidence",
            "test_corrupt_index_pointer_rebuilds_without_new_pointer_fields",
            "test_pointer_recovery_respects_active_runtime_json_write_lock",
        ),
    },
    {
        "link_id": "submit_result_body_entry_canaries",
        "path": "tests/test_flowpilot_new_entrypoint.py",
        "test_name": "test_submit_result_rejects_pseudo_json_before_loading_current_run",
        "covers": ("submit_result_body_entry",),
        "required_markers": (
            "test_submit_result_body_file_accepts_top_level_json_object",
            "test_submit_result_rejects_pseudo_json_before_loading_current_run",
            "test_submit_result_rejects_invalid_body_sources_without_normalizing",
            "test_cli_submit_result_reports_body_type_as_json_error",
        ),
    },
    {
        "link_id": "current_contract_source_purity_negatives",
        "path": "tests/test_flowpilot_current_contract_cartesian_matrix.py",
        "test_name": "test_source_purity_cartesian_rejects_every_failure_at_every_entrypoint",
        "covers": (
            "wrong_role",
            "retired_role_alias",
            "daemon_replay",
            "stale_workspace",
            "old_router",
            "body_only_contract",
            "private_helper_source",
        ),
        "required_markers": (
            "SOURCE_PURITY_FAILURE_PROFILES",
            "SOURCE_PURITY_ENTRYPOINTS",
            "mechanical_reject",
            "historical_negative",
        ),
    },
)


def _sanitize(value: str) -> str:
    return (
        value.replace(" ", "_")
        .replace("/", "_")
        .replace(".", "_")
        .replace("[", "_")
        .replace("]", "")
        .replace("__", "_")
    )


def _profile_for_family(family_id: str) -> dict[str, tuple[str, ...]]:
    group = STAGE_GROUP_BY_FAMILY[family_id]
    return PROFILE_BY_STAGE_GROUP[group]


def expected_reaction(
    *,
    family_id: str,
    action: str,
    object_state: str,
    ai_profile: str,
    timing: str,
    blocker_state: str,
    route_shape: str,
    source: str,
    claim_type: str,
) -> str:
    group = STAGE_GROUP_BY_FAMILY[family_id]
    if ai_profile.startswith("malformed_json_"):
        return "mechanical_reject"
    if (
        object_state == "unsupported_legacy_shape"
        or ai_profile == "old_protocol"
        or ai_profile in ROLE_SOURCE_NEGATIVE_AI_PROFILES
        or source in HISTORICAL_NEGATIVE_EXECUTION_SOURCES
    ):
        return "mechanical_reject"
    if object_state in {"current_pointer_corrupt_unambiguous", "index_pointer_corrupt"}:
        return "recover_pointer"
    if object_state in {"current_pointer_corrupt_ambiguous", "pointer_write_in_progress"}:
        return "structured_blocker"
    if object_state in {"stale_run", "stale_route", "stale_packet"} or timing == "old_result_after_reissue":
        return "ignore_stale_late_material"
    if ai_profile == "rejects_valid_task":
        return "reissue_current_packet"
    if ai_profile in {"ack_only", "summary_only"} and group in {"result", "review", "flowguard"}:
        return "reissue_current_packet"
    if object_state == "missing_not_due" or timing == "one_step_early":
        return "not_due_structured_wait"
    if object_state in {"missing_due", "unreadable_path", "wrong_owner", "duplicate_conflict"}:
        return "structured_blocker"
    if object_state == "current_progress_only" or timing == "background_progress_late":
        return "progress_only_not_evidence"
    if (
        object_state == "future_claim_without_evidence"
        or claim_type in {"future_evidence_claim", "live_ai_quality_claim"}
        or ai_profile == "overclaims_completion"
    ):
        return "reject_overclaim"
    if blocker_state in {
        "solved_still_blocks",
        "unsolved_skipped",
        "wrong_owner_blocker",
        "stale_blocker",
        "same_blocker_before_threshold",
        "repair_after_failed_recheck",
    }:
        return "structured_blocker"
    if blocker_state == "same_blocker_at_threshold":
        return "require_repair_delta"
    if blocker_state == "route_decomposition":
        return "route_mutation_gate"
    if action in {"redesign_route", "commit_route_mutation"} or route_shape in {"route_mutation_replacement", "sibling_branch_replacement"}:
        return "route_mutation_gate"
    if group == "terminal" and claim_type in {"task_complete", "release_evidence_claim", "routine_evidence_claim"}:
        return "terminal_evidence_gate"
    return "continue_current_stage"


REACTION_OWNER = {
    "continue_current_stage": "current_contract_runtime_matrix",
    "mechanical_reject": "current_contract_runtime_matrix",
    "ignore_stale_late_material": "current_contract_runtime_matrix",
    "not_due_structured_wait": "current_contract_stage_timing_matrix",
    "structured_blocker": "current_contract_blocker_repair_matrix",
    "recover_pointer": "current_contract_runtime_matrix",
    "progress_only_not_evidence": "current_contract_evidence_freshness_matrix",
    "reject_overclaim": "current_contract_overclaim_matrix",
    "reissue_current_packet": "current_contract_reissue_matrix",
    "route_mutation_gate": "current_contract_route_mutation_matrix",
    "terminal_evidence_gate": "current_contract_terminal_matrix",
    "require_repair_delta": "current_contract_no_delta_repair_matrix",
}

ABSORBING_NEXT_ACTION_BY_REACTION = {
    "continue_current_stage": "advance_current_stage_with_current_artifact",
    "mechanical_reject": "reject_current_submission_with_contract_feedback_and_reissue",
    "ignore_stale_late_material": "ignore_late_or_stale_material_and_wait_for_current_packet",
    "not_due_structured_wait": "record_not_due_wait_with_current_stage_pointer",
    "structured_blocker": "issue_owner_named_repair_or_reissue_packet",
    "recover_pointer": "backup_corrupt_pointer_and_restore_only_unambiguous_current_run",
    "progress_only_not_evidence": "keep_packet_open_and_require_real_result_artifact",
    "reject_overclaim": "reject_overclaim_and_reissue_current_packet_with_evidence_boundary",
    "reissue_current_packet": "reissue_same_current_packet_with_missing_delta_feedback",
    "route_mutation_gate": "stage_route_mutation_for_pm_flowguard_acceptance",
    "terminal_evidence_gate": "run_terminal_backward_replay_or_block_missing_terminal_evidence",
    "require_repair_delta": "absorb_no_delta_repeat_with_pm_repair_delta_requirement",
}


def _existing_test_link_for_cell(
    *,
    object_state: str,
    ai_profile: str,
    timing: str,
    source: str,
    reaction: str,
) -> str:
    if ai_profile in ROLE_SOURCE_NEGATIVE_AI_PROFILES or source in HISTORICAL_NEGATIVE_EXECUTION_SOURCES:
        return "current_contract_source_purity_negatives"
    if object_state == "unsupported_legacy_shape" or ai_profile == "old_protocol":
        return "cartesian_control_plane_existing_matrix"
    if (
        object_state
        in {
            "current_pointer_corrupt_unambiguous",
            "current_pointer_corrupt_ambiguous",
            "index_pointer_corrupt",
            "pointer_write_in_progress",
        }
    ):
        return "pointer_persistence_canaries"
    if ai_profile == "malformed_json_stringified_object":
        return "submit_result_body_entry_canaries"
    if ai_profile.startswith("malformed_json_"):
        return "fake_ai_malformed_body_profiles"
    if ai_profile in {"ack_only", "summary_only", "overclaims_completion"} or reaction == "reject_overclaim":
        return "synthetic_non_live_boundary"
    if object_state in {"stale_run", "stale_route", "stale_packet"} or timing == "old_result_after_reissue":
        return "route_mutation_stale_old_evidence"
    return ""


def _cell(
    *,
    family_id: str,
    action: str,
    object_state: str,
    ai_profile: str,
    timing: str,
    blocker_state: str,
    route_shape: str,
    source: str,
    claim_type: str,
) -> dict[str, Any]:
    reaction = expected_reaction(
        family_id=family_id,
        action=action,
        object_state=object_state,
        ai_profile=ai_profile,
        timing=timing,
        blocker_state=blocker_state,
        route_shape=route_shape,
        source=source,
        claim_type=claim_type,
    )
    stage_row = STAGE_ROW_BY_FAMILY[family_id]
    cell_id = ".".join(
        _sanitize(value)
        for value in (
            family_id,
            action,
            object_state,
            ai_profile,
            timing,
            blocker_state,
            route_shape,
            source,
            claim_type,
        )
    )
    existing_link = _existing_test_link_for_cell(
        object_state=object_state,
        ai_profile=ai_profile,
        timing=timing,
        source=source,
        reaction=reaction,
    )
    return {
        "cell_id": cell_id,
        "model_id": MODEL_ID,
        "family_id": family_id,
        "lifecycle_stage": stage_row["lifecycle_stage"],
        "stage_group": STAGE_GROUP_BY_FAMILY[family_id],
        "action": action,
        "package_material_kind": family_id,
        "object_state": object_state,
        "ai_return_profile": ai_profile,
        "timing": timing,
        "blocker_state": blocker_state,
        "route_shape": route_shape,
        "execution_source": source,
        "final_claim_type": claim_type,
        "expected_reaction": reaction,
        "required_evidence_owner": REACTION_OWNER[reaction],
        "absorbing_next_action": ABSORBING_NEXT_ACTION_BY_REACTION[reaction],
        "existing_test_link_id": existing_link,
        "reused_existing_test": bool(existing_link),
        "glassbreak_allowed": False,
        "current_contract_glassbreak_forbidden": True,
        "normal_repair_context": True,
        "coverage_shard_id": f"current_contract_cartesian:{REACTION_OWNER[reaction]}:{STAGE_GROUP_BY_FAMILY[family_id]}:{reaction}",
    }


def iter_source_purity_negative_cells() -> Iterable[dict[str, Any]]:
    for entrypoint, failure in product(SOURCE_PURITY_ENTRYPOINTS, SOURCE_PURITY_FAILURE_PROFILES):
        ai_profile = str(failure["ai_profile"] or entrypoint["default_ai_profile"])
        source = str(failure["source"])
        cell = _cell(
            family_id=str(entrypoint["family_id"]),
            action=str(entrypoint["action"]),
            object_state="current_valid",
            ai_profile=ai_profile,
            timing="on_time",
            blocker_state="no_blocker",
            route_shape=str(entrypoint["route_shape"]),
            source=source,
            claim_type="no_claim",
        )
        yield {
            **cell,
            "source_purity_entrypoint": str(entrypoint["entrypoint_id"]),
            "source_purity_failure_class": str(failure["failure_class"]),
            "source_purity_negative_only": True,
            "historical_negative": bool(failure["historical_negative"]),
            "current_stage_profile": False,
        }


def iter_required_cells() -> Iterable[dict[str, Any]]:
    for row in FLOW_STAGE_ROWS:
        family_id = row["family_id"]
        profile = _profile_for_family(family_id)
        for action, object_state, ai_profile, timing, blocker, route, source, claim in product(
            profile["actions"],
            profile["object_states"],
            profile["ai_profiles"],
            profile["timing"],
            profile["blockers"],
            profile["routes"],
            profile["sources"],
            profile["claims"],
        ):
            yield _cell(
                family_id=family_id,
                action=action,
                object_state=object_state,
                ai_profile=ai_profile,
                timing=timing,
                blocker_state=blocker,
                route_shape=route,
                source=source,
                claim_type=claim,
            )
    yield from iter_source_purity_negative_cells()


def positive_stage_profile_cell_count() -> int:
    declared_full_count = 0
    for row in FLOW_STAGE_ROWS:
        profile = _profile_for_family(row["family_id"])
        count = 1
        for key in ("actions", "object_states", "ai_profiles", "timing", "blockers", "routes", "sources", "claims"):
            count *= len(profile[key])
        declared_full_count += count
    return declared_full_count


def required_cell_count() -> int:
    return positive_stage_profile_cell_count() + SOURCE_PURITY_REQUIRED_CELL_COUNT


def build_required_cells(limit: int | None = None) -> tuple[dict[str, Any], ...]:
    cells: list[dict[str, Any]] = []
    for index, cell in enumerate(iter_required_cells()):
        if limit is not None and index >= limit:
            break
        cells.append(cell)
    return tuple(cells)


class RequiredFullCartesianCells:
    def __iter__(self) -> Iterable[dict[str, Any]]:
        return iter_required_cells()

    def __len__(self) -> int:
        return required_cell_count()


REQUIRED_FULL_CARTESIAN_CELLS = RequiredFullCartesianCells()


def axis_value_coverage() -> dict[str, dict[str, list[str]]]:
    axes = {axis: set(values) for axis, values in AXIS_VALUES.items()}
    present = {
        "flow_stage": set(FLOW_STAGE_IDS),
        "action": set(),
        "package_material_kind": set(PACKAGE_MATERIAL_KINDS),
        "object_state": set(),
        "ai_return_profile": set(),
        "timing": set(),
        "blocker_state": set(),
        "route_shape": set(),
        "execution_source": set(),
        "final_claim_type": set(),
    }
    for row in FLOW_STAGE_ROWS:
        profile = _profile_for_family(row["family_id"])
        present["action"].update(profile["actions"])
        present["object_state"].update(profile["object_states"])
        present["ai_return_profile"].update(profile["ai_profiles"])
        present["timing"].update(profile["timing"])
        present["blocker_state"].update(profile["blockers"])
        present["route_shape"].update(profile["routes"])
        present["execution_source"].update(profile["sources"])
        present["final_claim_type"].update(profile["claims"])
    for cell in iter_source_purity_negative_cells():
        present["action"].add(str(cell["action"]))
        present["object_state"].add(str(cell["object_state"]))
        present["ai_return_profile"].add(str(cell["ai_return_profile"]))
        present["timing"].add(str(cell["timing"]))
        present["blocker_state"].add(str(cell["blocker_state"]))
        present["route_shape"].add(str(cell["route_shape"]))
        present["execution_source"].add(str(cell["execution_source"]))
        present["final_claim_type"].add(str(cell["final_claim_type"]))
    return {
        axis: {
            "present": sorted(present[axis]),
            "missing": sorted(values - present[axis]),
        }
        for axis, values in axes.items()
    }


def matrix_counts() -> dict[str, int]:
    declared_profile_full_count = positive_stage_profile_cell_count()
    required_count = declared_profile_full_count + SOURCE_PURITY_REQUIRED_CELL_COUNT
    unrestricted_symbolic_count = (
        len(FLOW_STAGE_IDS)
        * len(ACTION_IDS)
        * len(PACKAGE_MATERIAL_KINDS)
        * len(OBJECT_STATES)
        * len(AI_RETURN_PROFILES)
        * len(TIMING_STATES)
        * len(BLOCKER_STATES)
        * len(ROUTE_SHAPES)
        * len(EXECUTION_SOURCES)
        * len(FINAL_CLAIM_TYPES)
    )
    return {
        "declared_profile_full_count": declared_profile_full_count,
        "source_purity_required_cell_count": SOURCE_PURITY_REQUIRED_CELL_COUNT,
        "required_cell_count": required_count,
        "unrestricted_symbolic_product_count": unrestricted_symbolic_count,
        "not_applicable_class_count": len(NOT_APPLICABLE_CLASSES),
    }


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    every_axis_value_covered: bool = True
    every_cell_has_oracle: bool = True
    every_reused_test_audited: bool = True
    existing_test_legacy_positive: bool = False
    current_contract_marker_missing: bool = False
    glassbreak_entered: bool = False
    old_evidence_accepted_as_current: bool = False
    future_evidence_claim_accepted: bool = False


@dataclass(frozen=True)
class Tick:
    """One full-current-contract matrix decision."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


VALID_SCENARIOS = {
    "valid_full_matrix",
    "valid_existing_test_reuse_audit",
}

SCENARIOS = {
    "valid_full_matrix": State(scenario="valid_full_matrix", status="selected"),
    "valid_existing_test_reuse_audit": State(scenario="valid_existing_test_reuse_audit", status="selected"),
    "missing_axis_value": replace(State(scenario="valid_full_matrix", status="selected"), scenario="missing_axis_value", every_axis_value_covered=False),
    "missing_oracle": replace(State(scenario="valid_full_matrix", status="selected"), scenario="missing_oracle", every_cell_has_oracle=False),
    "reused_test_not_audited": replace(State(scenario="valid_existing_test_reuse_audit", status="selected"), scenario="reused_test_not_audited", every_reused_test_audited=False),
    "legacy_positive_existing_test": replace(State(scenario="valid_existing_test_reuse_audit", status="selected"), scenario="legacy_positive_existing_test", existing_test_legacy_positive=True),
    "current_contract_marker_missing": replace(State(scenario="valid_existing_test_reuse_audit", status="selected"), scenario="current_contract_marker_missing", current_contract_marker_missing=True),
    "glassbreak_entered": replace(State(scenario="valid_full_matrix", status="selected"), scenario="glassbreak_entered", glassbreak_entered=True),
    "old_evidence_accepted": replace(State(scenario="valid_full_matrix", status="selected"), scenario="old_evidence_accepted", old_evidence_accepted_as_current=True),
    "future_evidence_claim_accepted": replace(State(scenario="valid_full_matrix", status="selected"), scenario="future_evidence_claim_accepted", future_evidence_claim_accepted=True),
}

NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def matrix_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.every_axis_value_covered:
        failures.append("full_cartesian_axis_value_missing")
    if not state.every_cell_has_oracle:
        failures.append("full_cartesian_cell_missing_oracle")
    if not state.every_reused_test_audited:
        failures.append("reused_existing_test_missing_currentness_audit")
    if state.existing_test_legacy_positive:
        failures.append("existing_test_still_accepts_legacy_positive_path")
    if state.current_contract_marker_missing:
        failures.append("existing_test_missing_current_contract_marker")
    if state.glassbreak_entered:
        failures.append("glassbreak_entered_current_contract_path")
    if state.old_evidence_accepted_as_current:
        failures.append("old_or_stale_evidence_accepted_as_current")
    if state.future_evidence_claim_accepted:
        failures.append("future_evidence_claim_accepted_as_current")
    return failures


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = matrix_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def initial_state() -> State:
    return State()


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


class CurrentContractCartesianStep:
    """Classify one current-contract scenario matrix cell.

    Input x State -> Set(Output x State)
    reads: stage/evidence row, package family, object state, AI-return profile,
    timing, blocker lifecycle, route shape, execution source, final claim, and
    existing-test reuse audit
    writes: accepted current-contract oracle or blocking diagnostic
    idempotency: pure classification keyed by model id and matrix cell id
    """

    name = "CurrentContractCartesianStep"
    reads = (
        "packet_stage_evidence_matrix",
        "current_contract_scenario_axis",
        "existing_test_reuse_audit",
    )
    writes = ("current_contract_cartesian_decision", "existing_test_currentness_finding")
    input_description = "one bounded FlowPilot current-contract Cartesian scenario cell"
    output_description = "safe current-contract oracle or blocking diagnostic"
    idempotency = "classification is keyed by model id and cell id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        failures = matrix_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not matrix_failures(state):
        return InvariantResult.fail("safe full Cartesian matrix state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted full-current-contract matrix states cannot miss axis values, miss oracles, reuse unaudited tests, accept legacy positives, enter GlassBreak, or accept old/future evidence as current.",
        accepted_states_are_safe,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CurrentContractCartesianStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    return [
        str(result.message)
        for invariant in INVARIANTS
        for result in (invariant.predicate(state, ()),)
        if not result.ok
    ]


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: matrix_failures(state) for name, state in hazard_states().items()}
