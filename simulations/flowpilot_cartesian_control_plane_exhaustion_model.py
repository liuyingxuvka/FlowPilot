"""FlowPilot Cartesian control-plane exhaustion model.

This model is the finite-product layer above the packet/result contract
exhaustion mesh. It declares the control-plane boundaries, mutation alphabet,
handoff contexts, and downstream consumers, then proves every product cell is
either applicable with a current-contract repair oracle or skipped with an
explicit reason.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path
import sys
from typing import Any, Iterable, NamedTuple

from flowguard import (
    ContractAxis,
    ContractCoverageShard,
    ContractExhaustionPlan,
    ContractInteractionGroup,
    FunctionResult,
    Invariant,
    InvariantResult,
    Workflow,
)


ROOT = Path(__file__).resolve().parents[1]
SIMULATIONS_PATH = ROOT / "simulations"
if str(SIMULATIONS_PATH) not in sys.path:
    sys.path.insert(0, str(SIMULATIONS_PATH))

try:  # pragma: no cover - package-style import when available
    from . import flowpilot_contract_exhaustion_mesh_model as contract_model
except ImportError:  # pragma: no cover - direct script/test import
    import flowpilot_contract_exhaustion_mesh_model as contract_model


MODEL_ID = "flowpilot_cartesian_control_plane_exhaustion"
MAX_SEQUENCE_LENGTH = 2
GLASSBREAK_THRESHOLD = 5
FLOWGUARD_NATIVE_INTERACTION_GROUP_ID = "control_plane_full_product"
FLOWGUARD_NATIVE_RECEIPT_ID = f"contract_coverage:{MODEL_ID}"

CONTEXTS = (
    "startup_intake",
    "active_packet_dispatch",
    "post_result_review",
    "pm_repair",
    "flowguard_reissue",
    "route_mutation",
    "terminal_closure",
    "synthetic_ai_rehearsal",
    "glassbreak_threshold_probe",
)

NORMAL_CONTEXTS = tuple(context for context in CONTEXTS if context != "glassbreak_threshold_probe")

CONSUMERS = (
    "runtime_router",
    "project_manager",
    "reviewer",
    "flowguard_operator",
    "testmesh_child_suite",
    "modelmesh_closure",
    "glassbreak_controller",
)

EVIDENCE_OWNER_BY_CONSUMER = {
    "runtime_router": "cartesian_runtime_matrix",
    "project_manager": "cartesian_pm_repair_matrix",
    "reviewer": "cartesian_reviewer_matrix",
    "flowguard_operator": "cartesian_flowguard_handoff_matrix",
    "testmesh_child_suite": "cartesian_testmesh_consumption_matrix",
    "modelmesh_closure": "cartesian_modelmesh_closure_matrix",
    "glassbreak_controller": "cartesian_glassbreak_threshold_matrix",
}

REPAIR_COMMAND_BY_REACTION = {
    "mechanical_reject": "flowpilot.runtime.reject_current_material_with_precise_contract_error",
    "repairable_reissue": "flowpilot.pm.reissue_current_packet_with_material_delta",
    "terminal_blocker": "flowpilot.runtime.block_terminal_claim_until_current_evidence_exists",
    "glassbreak_alarm": "flowpilot.runtime.raise_glassbreak_threshold_alarm",
}

MUTATION_GROUPS = {
    "envelope",
    "body",
    "field",
    "path",
    "identity",
    "evidence",
    "formal_artifact",
    "retry",
    "gate",
    "terminal",
    "compatibility",
}

FORMAL_ARTIFACT_MUTATIONS = tuple(
    {"id": mutation, "group": "formal_artifact"}
    for mutation in contract_model.formal_artifact_contracts.FORMAL_ARTIFACT_FAULT_MODES
)

MUTATIONS = (
    {"id": "missing_body", "group": "body"},
    {"id": "empty_body", "group": "body"},
    {"id": "malformed_json", "group": "body"},
    {"id": "body_hash_mismatch", "group": "body"},
    {"id": "missing_required_field", "group": "field"},
    {"id": "missing_required_child_field", "group": "field"},
    {"id": "wrong_type", "group": "field"},
    {"id": "wrong_enum", "group": "field"},
    {"id": "null_value", "group": "field"},
    {"id": "unknown_field", "group": "field"},
    {"id": "forbidden_field_present", "group": "field"},
    {"id": "missing_result_contract_profile", "group": "envelope"},
    {"id": "missing_allowed_value_options", "group": "field"},
    {"id": "missing_field_type_requirements", "group": "field"},
    {"id": "forbidden_alias_used", "group": "compatibility"},
    {"id": "wrong_allowed_value", "group": "field"},
    {"id": "empty_required_manifest", "group": "evidence"},
    {"id": "empty_required_array", "group": "field"},
    {"id": "missing_path", "group": "path"},
    {"id": "wrong_current_path", "group": "path"},
    {"id": "path_outside_root", "group": "path"},
    {"id": "target_not_found", "group": "path"},
    {"id": "wrong_run_id", "group": "identity"},
    {"id": "wrong_node_id", "group": "identity"},
    {"id": "wrong_role_id", "group": "identity"},
    {"id": "wrong_owner", "group": "identity"},
    {"id": "stale_id", "group": "identity"},
    {"id": "foreign_packet", "group": "identity"},
    {"id": "duplicate_packet", "group": "retry"},
    {"id": "same_payload_retry", "group": "retry"},
    {"id": "retry_without_delta", "group": "retry"},
    {"id": "corrected_second_retry", "group": "retry"},
    {"id": "same_blocker_repeat", "group": "retry"},
    {"id": "same_root_no_delta_retry", "group": "retry"},
    {"id": "missing_root_cause_loop_key", "group": "retry"},
    {"id": "missing_repair_guidance", "group": "field"},
    {"id": "missing_current_handoff_manifest", "group": "evidence"},
    {"id": "missing_stage_evidence_matrix", "group": "field"},
    {"id": "stage_evidence_mismatch", "group": "field"},
    {"id": "missing_evidence_manifest", "group": "evidence"},
    {"id": "missing_authorized_read", "group": "evidence"},
    {"id": "missing_related_authorized_body", "group": "evidence"},
    {"id": "packet_body_not_opened", "group": "evidence"},
    {"id": "missing_repair_evidence_obligations", "group": "field"},
    {"id": "missing_repair_obligation_disposition", "group": "field"},
    {"id": "unknown_repair_obligation_id", "group": "field"},
    {"id": "stale_repair_obligation_evidence_ref", "group": "evidence"},
    {"id": "missing_repair_obligation_consumption", "group": "evidence"},
    {"id": "stale_evidence", "group": "evidence"},
    {"id": "progress_only_evidence", "group": "evidence"},
    {"id": "evidence_path_mismatch", "group": "evidence"},
    {"id": "accepted_result_work_order_split", "group": "gate"},
    {"id": "reissue_loses_inherited_policy", "group": "gate"},
    {"id": "reissue_loses_inherited_authorized_reads", "group": "evidence"},
    {"id": "reissue_loses_required_read_manifest", "group": "evidence"},
    {"id": "dirty_terminal", "group": "terminal"},
    {"id": "lock_conflict", "group": "terminal"},
    {"id": "lease_expired", "group": "terminal"},
    {"id": "unsupported_command", "group": "compatibility"},
    {"id": "legacy_alias", "group": "compatibility"},
    {"id": "fallback_prose", "group": "compatibility"},
    {"id": "wrapper_shape", "group": "compatibility"},
    {"id": "missing_runtime_self_check_receipt", "group": "evidence"},
    {"id": "target_requires_dev_repo_simulation", "group": "path"},
    {"id": "synthetic_live_overclaim", "group": "evidence"},
    *FORMAL_ARTIFACT_MUTATIONS,
)

MUTATION_IDS = tuple(str(mutation["id"]) for mutation in MUTATIONS)
MUTATION_BY_ID = {str(mutation["id"]): mutation for mutation in MUTATIONS}

CONTRACT_EXHAUSTION_MUTATION_CANONICALIZATION = {
    "malformed_body.empty_body": "empty_body",
    "malformed_body.markdown_wrapped_json": "malformed_json",
    "malformed_body.prose_plus_json": "malformed_json",
    "malformed_body.top_level_array": "malformed_json",
    "malformed_body.trailing_comma": "malformed_json",
    "malformed_body.unquoted_keys": "malformed_json",
    "partial_repair_then_corrected": "corrected_second_retry",
    "hidden_projection_gap": "missing_required_child_field",
    "finite_option_mistake": "wrong_allowed_value",
    "forbidden_alias": "forbidden_alias_used",
    "missing_active_id_coverage": "missing_required_child_field",
    "missing_live_singleton_required_evidence": "missing_evidence_manifest",
    "missing_review_flow_id": "missing_required_field",
    "orphan_review_flow": "wrong_enum",
    "wrong_subject_family": "stage_evidence_mismatch",
    "wrong_subject_lifecycle_stage": "stage_evidence_mismatch",
    "missing_window_path": "missing_required_field",
    "missing_required_read_manifest": "missing_evidence_manifest",
    "future_stage_demand_allowed": "stage_evidence_mismatch",
    "pm_repair_return_rule_missing": "missing_repair_guidance",
    "envelope_body_window_mismatch": "stage_evidence_mismatch",
    "prose_only_review_scope": "fallback_prose",
    "reviewer_shallow_pass": "missing_evidence_manifest",
    "reviewer_skips_required_read": "packet_body_not_opened",
    "reviewer_future_stage_demand": "stage_evidence_mismatch",
    "reviewer_unauthorized_sealed_body_request": "path_outside_root",
    "reviewer_invents_scope": "wrong_current_path",
    "reviewer_self_repairs_subject": "wrong_owner",
    "reviewer_quality_score_10_exceeds_standard": "corrected_second_retry",
    "reviewer_quality_score_6_soft_pm_optimization": "corrected_second_retry",
    "reviewer_quantitative_gap_blocks": "missing_required_field",
    "reviewer_overblocks_sub9_soft_score": "wrong_owner",
    "reviewer_recheck_consumes_score_context": "corrected_second_retry",
    "pm_bypasses_reviewer_blocker": "accepted_result_work_order_split",
    "corrected_second_reviewer_retry": "corrected_second_retry",
    "same_review_failure_attempts_1_to_4": "same_blocker_repeat",
    "same_review_failure_attempt_5_break_glass": "same_blocker_repeat",
}

BOUNDARIES = (
    {
        "id": "packet_envelope",
        "subject": "current packet envelope",
        "owner": "runtime_router",
        "groups": ("envelope", "identity", "compatibility"),
        "contexts": ("startup_intake", "active_packet_dispatch", "flowguard_reissue"),
        "consumers": ("runtime_router", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "sealed_packet_body",
        "subject": "sealed packet body",
        "owner": "runtime_router",
        "groups": ("body", "field", "evidence", "compatibility"),
        "contexts": ("startup_intake", "active_packet_dispatch", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "packet_body_hash",
        "subject": "packet sealed body hash",
        "owner": "runtime_router",
        "groups": ("body", "identity", "evidence"),
        "contexts": ("startup_intake", "active_packet_dispatch", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "result_envelope",
        "subject": "current result envelope",
        "owner": "runtime_router",
        "groups": ("envelope", "identity", "compatibility"),
        "contexts": ("post_result_review", "terminal_closure", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "reviewer", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "result_body",
        "subject": "current result body",
        "owner": "runtime_router",
        "groups": ("body", "field", "evidence", "formal_artifact", "compatibility"),
        "contexts": ("post_result_review", "terminal_closure", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "reviewer", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "route_run_identity",
        "subject": "current route run id",
        "owner": "runtime_router",
        "groups": ("identity", "path", "compatibility"),
        "contexts": ("startup_intake", "active_packet_dispatch", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "route_node_identity",
        "subject": "current route node id",
        "owner": "runtime_router",
        "groups": ("identity", "path", "compatibility"),
        "contexts": ("active_packet_dispatch", "post_result_review", "pm_repair", "route_mutation"),
        "consumers": ("runtime_router", "project_manager", "reviewer", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "role_identity",
        "subject": "current role identity",
        "owner": "runtime_router",
        "groups": ("identity", "field", "compatibility"),
        "contexts": ("active_packet_dispatch", "post_result_review", "pm_repair", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "project_manager", "reviewer", "testmesh_child_suite"),
    },
    {
        "id": "packet_address",
        "subject": "current packet mailbox address",
        "owner": "runtime_router",
        "groups": ("path", "identity", "field"),
        "contexts": ("active_packet_dispatch", "flowguard_reissue", "pm_repair"),
        "consumers": ("runtime_router", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "target_artifact_path",
        "subject": "current artifact path",
        "owner": "runtime_router",
        "groups": ("path", "evidence", "formal_artifact", "compatibility"),
        "contexts": ("post_result_review", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "reviewer", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "evidence_manifest",
        "subject": "current evidence manifest",
        "owner": "runtime_router",
        "groups": ("evidence", "field", "path", "formal_artifact", "compatibility"),
        "contexts": ("post_result_review", "flowguard_reissue", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "reviewer", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "stage_evidence_matrix",
        "subject": "current packet stage-evidence matrix",
        "owner": "runtime_router",
        "groups": ("field", "evidence", "formal_artifact", "gate"),
        "contexts": ("active_packet_dispatch", "post_result_review", "flowguard_reissue", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "reviewer", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "runtime_self_check_receipt",
        "subject": "installed FlowPilot runtime self-check receipt",
        "owner": "runtime_router",
        "groups": ("field", "path", "evidence", "identity"),
        "contexts": ("startup_intake", "active_packet_dispatch", "terminal_closure"),
        "consumers": ("runtime_router", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "authorized_result_read",
        "subject": "authorized current result read",
        "owner": "runtime_router",
        "groups": ("evidence", "identity", "field"),
        "contexts": ("post_result_review", "pm_repair", "flowguard_reissue", "terminal_closure"),
        "consumers": ("runtime_router", "project_manager", "reviewer", "flowguard_operator", "testmesh_child_suite"),
    },
    {
        "id": "pm_repair_obligation",
        "subject": "PM repair evidence obligation and downstream consumption",
        "owner": "runtime_router",
        "groups": ("field", "evidence", "gate"),
        "contexts": ("pm_repair", "flowguard_reissue", "synthetic_ai_rehearsal"),
        "consumers": ("runtime_router", "project_manager", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "flowguard_report_reference",
        "subject": "current FlowGuard report reference",
        "owner": "flowguard_operator",
        "groups": ("evidence", "path", "identity", "field", "formal_artifact"),
        "contexts": ("flowguard_reissue", "post_result_review", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "reviewer", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "background_proof_artifact",
        "subject": "current background proof artifact",
        "owner": "runtime_router",
        "groups": ("evidence", "path", "terminal"),
        "contexts": ("route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "route_frontier_snapshot",
        "subject": "current route frontier snapshot",
        "owner": "runtime_router",
        "groups": ("identity", "path", "evidence", "field"),
        "contexts": ("route_mutation", "terminal_closure", "pm_repair"),
        "consumers": ("runtime_router", "project_manager", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "pm_repair_guidance",
        "subject": "current PM repair guidance",
        "owner": "project_manager",
        "groups": ("field", "retry", "identity", "compatibility"),
        "contexts": ("pm_repair", "flowguard_reissue", "glassbreak_threshold_probe"),
        "consumers": ("runtime_router", "project_manager", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure", "glassbreak_controller"),
    },
    {
        "id": "active_blocker_record",
        "subject": "current active blocker record",
        "owner": "project_manager",
        "groups": ("retry", "field", "identity", "evidence"),
        "contexts": ("pm_repair", "flowguard_reissue", "terminal_closure", "glassbreak_threshold_probe"),
        "consumers": ("runtime_router", "project_manager", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure", "glassbreak_controller"),
    },
    {
        "id": "reissue_packet_contract",
        "subject": "current reissue packet contract",
        "owner": "runtime_router",
        "groups": ("envelope", "body", "field", "retry", "evidence", "gate", "compatibility"),
        "contexts": ("flowguard_reissue", "pm_repair", "active_packet_dispatch", "glassbreak_threshold_probe"),
        "consumers": ("runtime_router", "project_manager", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure", "glassbreak_controller"),
    },
    {
        "id": "reviewer_gate_manifest",
        "subject": "reviewer gate evidence manifest",
        "owner": "reviewer",
        "groups": ("gate", "evidence", "field", "identity"),
        "contexts": ("post_result_review", "terminal_closure"),
        "consumers": ("runtime_router", "reviewer", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "work_order_binding",
        "subject": "accepted result and work-order binding",
        "owner": "runtime_router",
        "groups": ("gate", "identity", "path", "field"),
        "contexts": ("post_result_review", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "reviewer", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "terminal_ledger_record",
        "subject": "current terminal ledger record",
        "owner": "runtime_router",
        "groups": ("terminal", "evidence", "identity", "field", "path"),
        "contexts": ("terminal_closure",),
        "consumers": ("runtime_router", "project_manager", "reviewer", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "lock_lease_record",
        "subject": "current lock or lease record",
        "owner": "runtime_router",
        "groups": ("terminal", "identity", "field"),
        "contexts": ("startup_intake", "active_packet_dispatch", "route_mutation", "terminal_closure"),
        "consumers": ("runtime_router", "project_manager", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "install_source_binding",
        "subject": "repo-installed source binding",
        "owner": "runtime_router",
        "groups": ("path", "evidence", "identity"),
        "contexts": ("startup_intake", "terminal_closure"),
        "consumers": ("runtime_router", "flowguard_operator", "testmesh_child_suite", "modelmesh_closure"),
    },
    {
        "id": "contract_exhaustion_bridge",
        "subject": "contract-exhaustion required cell bridge",
        "owner": "testmesh_child_suite",
        "groups": tuple(sorted(MUTATION_GROUPS - {"terminal"})),
        "contexts": ("synthetic_ai_rehearsal", "post_result_review", "flowguard_reissue"),
        "consumers": ("testmesh_child_suite", "modelmesh_closure", "flowguard_operator"),
    },
    {
        "id": "historical_failure_bridge",
        "subject": "historical failure family bridge",
        "owner": "flowguard_operator",
        "groups": tuple(sorted(MUTATION_GROUPS - {"envelope"})),
        "contexts": ("synthetic_ai_rehearsal", "pm_repair", "flowguard_reissue", "glassbreak_threshold_probe"),
        "consumers": ("testmesh_child_suite", "modelmesh_closure", "flowguard_operator", "glassbreak_controller"),
    },
)

BOUNDARY_IDS = tuple(str(boundary["id"]) for boundary in BOUNDARIES)

COMPATIBILITY_MUTATIONS = {"unsupported_command", "legacy_alias", "fallback_prose", "wrapper_shape", "forbidden_alias_used"}
RETRY_MUTATIONS = {
    "duplicate_packet",
    "same_payload_retry",
    "retry_without_delta",
    "corrected_second_retry",
    "same_blocker_repeat",
    "same_root_no_delta_retry",
    "missing_root_cause_loop_key",
}
GLASSBREAK_MUTATIONS = {"same_blocker_repeat", "same_root_no_delta_retry", "retry_without_delta"}
TERMINAL_MUTATIONS = {"dirty_terminal", "lock_conflict", "lease_expired", "progress_only_evidence"}


def _sanitize(value: str) -> str:
    return (
        value.replace(" ", "_")
        .replace("/", "_")
        .replace(".", "_")
        .replace("[", "_")
        .replace("]", "")
        .replace("__", "_")
    )


def _contract_combination_order(
    boundary_id: str,
    mutation_id: str,
    context: str,
    consumer: str,
) -> int:
    return (
        (
            (
                BOUNDARY_IDS.index(boundary_id) * len(MUTATION_IDS)
                + MUTATION_IDS.index(mutation_id)
            )
            * len(CONTEXTS)
            + CONTEXTS.index(context)
        )
        * len(CONSUMERS)
        + CONSUMERS.index(consumer)
        + 1
    )


def _contract_combination_case_id(
    boundary_id: str,
    mutation_id: str,
    context: str,
    consumer: str,
) -> str:
    order = _contract_combination_order(boundary_id, mutation_id, context, consumer)
    return f"cartesian:{MODEL_ID}:{FLOWGUARD_NATIVE_INTERACTION_GROUP_ID}:{order}"


def _coverage_shard_id(evidence_owner: str, context: str, reaction: str) -> str:
    return (
        f"flowpilot_shard:{MODEL_ID}:"
        f"{_sanitize(evidence_owner)}:{_sanitize(context)}:{_sanitize(reaction)}"
    )


def _skip_reason(
    boundary: dict[str, Any],
    mutation: dict[str, Any],
    context: str,
    consumer: str,
) -> str:
    group = str(mutation["group"])
    mutation_id = str(mutation["id"])
    boundary_id = str(boundary["id"])
    if group not in set(boundary["groups"]):
        return "boundary_does_not_own_mutation_group"
    if context not in set(boundary["contexts"]):
        return "boundary_not_present_in_context"
    if consumer not in set(boundary["consumers"]):
        return "consumer_not_allowed_for_boundary"
    if consumer == "glassbreak_controller" and context != "glassbreak_threshold_probe":
        return "glassbreak_controller_only_consumes_threshold_probe"
    if context == "glassbreak_threshold_probe" and mutation_id not in GLASSBREAK_MUTATIONS:
        return "threshold_probe_only_accepts_repeated_blocker_mutations"
    if boundary_id not in {"pm_repair_guidance", "active_blocker_record", "reissue_packet_contract", "historical_failure_bridge"} and context == "glassbreak_threshold_probe":
        return "boundary_not_part_of_repeated_blocker_threshold"
    return ""


def expected_reaction(mutation_id: str, context: str, consumer: str) -> str:
    if context == "glassbreak_threshold_probe" and mutation_id in GLASSBREAK_MUTATIONS and consumer == "glassbreak_controller":
        return "glassbreak_alarm"
    if mutation_id in COMPATIBILITY_MUTATIONS:
        return "mechanical_reject"
    if mutation_id in TERMINAL_MUTATIONS:
        return "terminal_blocker"
    if mutation_id in RETRY_MUTATIONS:
        return "repairable_reissue"
    if mutation_id in {"progress_only_evidence", "stale_evidence", "synthetic_live_overclaim"}:
        return "terminal_blocker"
    return "mechanical_reject"


def _repair_fields(mutation_id: str, reaction: str) -> tuple[str, ...]:
    base = (
        "current_subject",
        "mechanical_owner",
        "mutation_kind",
        "boundary_id",
        "downstream_consumer",
        "required_repair_command",
    )
    if reaction == "glassbreak_alarm":
        return (*base, "root_cause_loop_key", "same_blocker_attempt_count")
    if reaction == "mechanical_reject":
        return (*base, "minimum_valid_shape")
    if mutation_id in RETRY_MUTATIONS:
        return (*base, "required_delta")
    if reaction == "terminal_blocker":
        return (*base, "blocking_evidence_path")
    return base


def _cell(
    boundary: dict[str, Any],
    mutation: dict[str, Any],
    context: str,
    consumer: str,
) -> dict[str, Any]:
    mutation_id = str(mutation["id"])
    boundary_id = str(boundary["id"])
    reaction = expected_reaction(mutation_id, context, consumer)
    evidence_owner = EVIDENCE_OWNER_BY_CONSUMER[consumer]
    cell_id = ".".join((_sanitize(boundary_id), _sanitize(mutation_id), context, consumer))
    coverage_shard_id = _coverage_shard_id(evidence_owner, context, reaction)
    return {
        "cell_id": cell_id,
        "boundary_id": boundary_id,
        "boundary_subject": boundary["subject"],
        "mutation_kind": mutation_id,
        "mutation_group": mutation["group"],
        "context": context,
        "consumer": consumer,
        "mechanical_owner": boundary["owner"],
        "current_subject": f"{boundary['subject']} in {context}",
        "expected_reaction": reaction,
        "required_repair_command": REPAIR_COMMAND_BY_REACTION[reaction],
        "required_feedback_fields": _repair_fields(mutation_id, reaction),
        "required_evidence_owner": evidence_owner,
        "contract_combination_case_id": _contract_combination_case_id(
            boundary_id,
            mutation_id,
            context,
            consumer,
        ),
        "coverage_shard_id": coverage_shard_id,
        "coverage_receipt_id": FLOWGUARD_NATIVE_RECEIPT_ID,
        "contract_axis_case_ids": (
            f"boundary:{boundary_id}",
            f"mutation:{mutation_id}",
            f"context:{context}",
            f"consumer:{consumer}",
        ),
        "validation_command": "python -m pytest tests/test_flowpilot_cartesian_control_plane_exhaustion.py -q",
        "glass_break_allowed": reaction == "glassbreak_alarm",
        "normal_repair_context": context in NORMAL_CONTEXTS,
        "requires_next_packet_delta": mutation_id in RETRY_MUTATIONS and reaction != "glassbreak_alarm",
        "unsupported_shape_rejected": mutation_id in COMPATIBILITY_MUTATIONS,
        "repeated_blocker_key_required": reaction == "glassbreak_alarm" or mutation_id in GLASSBREAK_MUTATIONS,
        "same_blocker_attempt_count": GLASSBREAK_THRESHOLD if reaction == "glassbreak_alarm" else 1,
    }


def build_cartesian_matrix() -> dict[str, Any]:
    applicable: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    full_count = 0
    for boundary, mutation, context, consumer in product(BOUNDARIES, MUTATIONS, CONTEXTS, CONSUMERS):
        full_count += 1
        reason = _skip_reason(boundary, mutation, context, consumer)
        if reason:
            skipped.append(
                {
                    "boundary_id": str(boundary["id"]),
                    "mutation_kind": str(mutation["id"]),
                    "context": context,
                    "consumer": consumer,
                    "skip_reason": reason,
                    "contract_combination_case_id": _contract_combination_case_id(
                        str(boundary["id"]),
                        str(mutation["id"]),
                        context,
                        consumer,
                    ),
                }
            )
            continue
        applicable.append(_cell(boundary, mutation, context, consumer))
    return {
        "full_product_count": full_count,
        "applicable_count": len(applicable),
        "skipped_count": len(skipped),
        "applicable_cells": tuple(applicable),
        "skipped_cells": tuple(skipped),
    }


CARTESIAN_MATRIX = build_cartesian_matrix()
REQUIRED_CARTESIAN_CELLS = CARTESIAN_MATRIX["applicable_cells"]
SKIPPED_CARTESIAN_CELLS = CARTESIAN_MATRIX["skipped_cells"]


def build_flowguard_coverage_shards() -> tuple[ContractCoverageShard, ...]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for cell in REQUIRED_CARTESIAN_CELLS:
        grouped.setdefault(str(cell["coverage_shard_id"]), []).append(cell)
    shards: list[ContractCoverageShard] = []
    for shard_id, cells in sorted(grouped.items()):
        first = cells[0]
        shards.append(
            ContractCoverageShard(
                shard_id=shard_id,
                model_id=MODEL_ID,
                interaction_group_id="flowpilot_consumer_context_reaction",
                case_ids=tuple(str(cell["cell_id"]) for cell in cells),
                complete=True,
                total_combinations=len(cells),
                generated_count=len(cells),
                skipped_count=0,
                status="covered",
                metadata={
                    "context": str(first["context"]),
                    "evidence_owner": str(first["required_evidence_owner"]),
                    "expected_reaction": str(first["expected_reaction"]),
                },
            )
        )
    return tuple(shards)


def build_flowguard_contract_exhaustion_plan() -> ContractExhaustionPlan:
    axes = (
        ContractAxis(
            axis_id="boundary",
            model_id=MODEL_ID,
            values=BOUNDARY_IDS,
            description="FlowPilot current control-plane material boundary ids.",
        ),
        ContractAxis(
            axis_id="mutation",
            model_id=MODEL_ID,
            values=MUTATION_IDS,
            description="Declared bad-input and bad-handoff mutation kinds.",
        ),
        ContractAxis(
            axis_id="context",
            model_id=MODEL_ID,
            values=CONTEXTS,
            description="Current FlowPilot handoff or recovery context.",
        ),
        ContractAxis(
            axis_id="consumer",
            model_id=MODEL_ID,
            values=CONSUMERS,
            description="Downstream control-plane consumer.",
        ),
    )
    interaction = ContractInteractionGroup(
        group_id=FLOWGUARD_NATIVE_INTERACTION_GROUP_ID,
        model_id=MODEL_ID,
        axis_ids=("boundary", "mutation", "context", "consumer"),
        required_routes=("model_test_alignment", "test_mesh", "model_mesh"),
        max_combinations=int(CARTESIAN_MATRIX["full_product_count"]),
        oracle_status="block_before_downstream",
        description="Full declared FlowPilot control-plane Cartesian product.",
    )
    return ContractExhaustionPlan(
        plan_id=f"{MODEL_ID}.flowguard_051_native_cartesian",
        model_id=MODEL_ID,
        model_level="leaf",
        axes=axes,
        interaction_groups=(interaction,),
        coverage_shards=build_flowguard_coverage_shards(),
        claim_scope="routine",
        required_route_ids=("model_test_alignment", "test_mesh", "model_mesh"),
        require_model_coverage_receipt=True,
        cartesian_case_limit=int(CARTESIAN_MATRIX["full_product_count"]),
        metadata={
            "applicable_count": len(REQUIRED_CARTESIAN_CELLS),
            "skipped_count": len(SKIPPED_CARTESIAN_CELLS),
            "skip_reason_ids": tuple(
                sorted({str(cell["skip_reason"]) for cell in SKIPPED_CARTESIAN_CELLS})
            ),
        },
    )


def contract_exhaustion_bridge_cells() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for cell in contract_model.REQUIRED_CONTRACT_EXHAUSTION_CELLS:
        mutation = str(cell.get("mutation_kind", ""))
        cartesian_mutation = CONTRACT_EXHAUSTION_MUTATION_CANONICALIZATION.get(mutation, mutation)
        translation_kind = "identity"
        translation_reason = "source mutation is part of the control-plane mutation alphabet"
        if cartesian_mutation != mutation:
            translation_kind = "canonical_current_control_plane"
            translation_reason = "source mutation is a detailed contract-exhaustion subtype of the named control-plane mutation"
        rows.append(
            {
                "bridge_id": f"contract_exhaustion.{cell['cell_id']}",
                "source_model_id": contract_model.MODEL_ID,
                "source_cell_id": str(cell["cell_id"]),
                "source_mutation_kind": mutation,
                "source_mutation_known": mutation in MUTATION_BY_ID
                or mutation in CONTRACT_EXHAUSTION_MUTATION_CANONICALIZATION,
                "source_evidence_owner": str(cell["required_evidence_owner"]),
                "cartesian_boundary_id": "contract_exhaustion_bridge",
                "cartesian_mutation_kind": cartesian_mutation,
                "cartesian_mutation_known": cartesian_mutation in MUTATION_BY_ID,
                "bridge_translation_kind": translation_kind,
                "bridge_translation_reason": translation_reason,
                "cartesian_consumer": "testmesh_child_suite",
                "required_evidence_owner": "cartesian_testmesh_consumption_matrix",
            }
        )
    return tuple(rows)


def historical_failure_bridge_cells() -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for family in contract_model.HISTORICAL_FAILURE_FAMILIES:
        for mutation in family.get("mutation_kinds", ()):
            rows.append(
                {
                    "bridge_id": f"historical_failure.{family['failure_id']}.{mutation}",
                    "source_failure_id": str(family["failure_id"]),
                    "source_class": str(family["source_class"]),
                    "source_mutation_kind": str(mutation),
                    "cartesian_boundary_id": "historical_failure_bridge",
                    "cartesian_mutation_kind": str(mutation),
                    "cartesian_mutation_known": str(mutation) in MUTATION_BY_ID,
                    "glass_break_allowed_in_acceptance": bool(
                        family.get("glass_break_allowed_in_acceptance", False)
                    ),
                    "required_evidence_owner": "cartesian_flowguard_handoff_matrix",
                }
            )
    return tuple(rows)


CONTRACT_EXHAUSTION_BRIDGE_CELLS = contract_exhaustion_bridge_cells()
HISTORICAL_FAILURE_BRIDGE_CELLS = historical_failure_bridge_cells()


@dataclass(frozen=True)
class State:
    scenario: str = "new"
    status: str = "new"
    product_count_recorded: bool = True
    skipped_cell_reason_named: bool = True
    applicable_cell_has_oracle: bool = True
    current_subject_named: bool = True
    owner_named: bool = True
    repair_command_named: bool = True
    evidence_owner_named: bool = True
    testmesh_owner_registered: bool = True
    normal_context_entered_glassbreak: bool = False
    glassbreak_threshold_has_loop_key: bool = True
    glassbreak_threshold_attempt_count: int = GLASSBREAK_THRESHOLD
    unsupported_shape_translated: bool = False
    no_delta_retry_without_feedback: bool = False
    contract_bridge_consumed: bool = True
    historical_bridge_consumed: bool = True


@dataclass(frozen=True)
class Tick:
    """One Cartesian control-plane exhaustion decision."""


@dataclass(frozen=True)
class Action:
    name: str


class Transition(NamedTuple):
    label: str
    state: State


def _valid_full_matrix() -> State:
    return State(scenario="valid_full_matrix", status="selected")


def _valid_threshold_probe() -> State:
    return State(
        scenario="valid_glassbreak_threshold_probe",
        status="selected",
        glassbreak_threshold_has_loop_key=True,
        glassbreak_threshold_attempt_count=GLASSBREAK_THRESHOLD,
    )


SCENARIOS = {
    "valid_full_matrix": _valid_full_matrix(),
    "valid_glassbreak_threshold_probe": _valid_threshold_probe(),
    "silent_skip_filter": replace(
        _valid_full_matrix(),
        scenario="silent_skip_filter",
        skipped_cell_reason_named=False,
    ),
    "missing_oracle": replace(
        _valid_full_matrix(),
        scenario="missing_oracle",
        applicable_cell_has_oracle=False,
    ),
    "missing_precise_feedback": replace(
        _valid_full_matrix(),
        scenario="missing_precise_feedback",
        current_subject_named=False,
        repair_command_named=False,
    ),
    "unregistered_testmesh_owner": replace(
        _valid_full_matrix(),
        scenario="unregistered_testmesh_owner",
        testmesh_owner_registered=False,
    ),
    "normal_repair_enters_glassbreak": replace(
        _valid_full_matrix(),
        scenario="normal_repair_enters_glassbreak",
        normal_context_entered_glassbreak=True,
    ),
    "threshold_probe_missing_loop_key": replace(
        _valid_threshold_probe(),
        scenario="threshold_probe_missing_loop_key",
        glassbreak_threshold_has_loop_key=False,
    ),
    "threshold_probe_under_attempt_count": replace(
        _valid_threshold_probe(),
        scenario="threshold_probe_under_attempt_count",
        glassbreak_threshold_attempt_count=GLASSBREAK_THRESHOLD - 1,
    ),
    "unsupported_shape_translated": replace(
        _valid_full_matrix(),
        scenario="unsupported_shape_translated",
        unsupported_shape_translated=True,
    ),
    "no_delta_retry_without_feedback": replace(
        _valid_full_matrix(),
        scenario="no_delta_retry_without_feedback",
        no_delta_retry_without_feedback=True,
    ),
    "contract_bridge_not_consumed": replace(
        _valid_full_matrix(),
        scenario="contract_bridge_not_consumed",
        contract_bridge_consumed=False,
    ),
    "historical_bridge_not_consumed": replace(
        _valid_full_matrix(),
        scenario="historical_bridge_not_consumed",
        historical_bridge_consumed=False,
    ),
}

VALID_SCENARIOS = {"valid_full_matrix", "valid_glassbreak_threshold_probe"}
NEGATIVE_SCENARIOS = set(SCENARIOS) - VALID_SCENARIOS


def cartesian_failures(state: State) -> list[str]:
    failures: list[str] = []
    if not state.product_count_recorded:
        failures.append("cartesian_product_count_missing")
    if not state.skipped_cell_reason_named:
        failures.append("cartesian_skip_reason_missing")
    if not state.applicable_cell_has_oracle:
        failures.append("cartesian_applicable_cell_missing_oracle")
    if not state.current_subject_named:
        failures.append("cartesian_feedback_missing_current_subject")
    if not state.owner_named:
        failures.append("cartesian_feedback_missing_owner")
    if not state.repair_command_named:
        failures.append("cartesian_feedback_missing_repair_command")
    if not state.evidence_owner_named:
        failures.append("cartesian_cell_missing_evidence_owner")
    if not state.testmesh_owner_registered:
        failures.append("cartesian_testmesh_owner_unregistered")
    if state.normal_context_entered_glassbreak:
        failures.append("cartesian_normal_repair_entered_glassbreak")
    if not state.glassbreak_threshold_has_loop_key:
        failures.append("cartesian_glassbreak_threshold_missing_loop_key")
    if state.glassbreak_threshold_attempt_count < GLASSBREAK_THRESHOLD:
        failures.append("cartesian_glassbreak_threshold_attempt_count_too_low")
    if state.unsupported_shape_translated:
        failures.append("cartesian_unsupported_shape_translated_instead_of_rejected")
    if state.no_delta_retry_without_feedback:
        failures.append("cartesian_no_delta_retry_missing_required_delta_feedback")
    if not state.contract_bridge_consumed:
        failures.append("cartesian_contract_exhaustion_bridge_not_consumed")
    if not state.historical_bridge_consumed:
        failures.append("cartesian_historical_failure_bridge_not_consumed")
    return sorted(set(failures))


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for name, scenario in sorted(SCENARIOS.items()):
            yield Transition(f"select_{name}", scenario)
        return
    if state.status == "selected":
        failures = cartesian_failures(state)
        terminal = "rejected" if failures else "accepted"
        yield Transition(f"{terminal.removesuffix('ed')}_{state.scenario}", replace(state, status=terminal))


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


class CartesianExhaustionStep:
    """Classify one declared control-plane product cell.

    Input x State -> Set(Output x State)
    reads: control-plane material boundary, mutation kind, context, consumer,
    bridge evidence, and TestMesh owner map
    writes: accepted current-contract oracle or blocking diagnostic
    idempotency: pure classification keyed by model id and Cartesian cell id
    """

    name = "CartesianExhaustionStep"
    reads = (
        "control_plane_boundary_inventory",
        "mutation_alphabet",
        "handoff_context",
        "downstream_consumer",
        "contract_exhaustion_bridge",
        "historical_failure_bridge",
    )
    writes = ("cartesian_exhaustion_decision", "cartesian_required_cell_finding")
    input_description = "one declared FlowPilot Cartesian control-plane cell"
    output_description = "safe current-contract repair oracle or hard diagnostic"
    idempotency = "classification is keyed by model id, run id, and Cartesian cell id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        failures = cartesian_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    if state.status == "rejected" and not cartesian_failures(state):
        return InvariantResult.fail("safe Cartesian exhaustion state was rejected")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted Cartesian states cannot contain silent skips, missing oracles, missing feedback, unregistered owners, normal GlassBreak repair, fallback translation, no-delta retries, or unconsumed bridge evidence.",
        accepted_states_are_safe,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CartesianExhaustionStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return failures


def hazard_states() -> dict[str, State]:
    return {name: SCENARIOS[name] for name in sorted(NEGATIVE_SCENARIOS)}


def expected_failures_by_hazard() -> dict[str, list[str]]:
    return {name: cartesian_failures(state) for name, state in hazard_states().items()}
