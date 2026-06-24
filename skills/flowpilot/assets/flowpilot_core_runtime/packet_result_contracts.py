"""Authoritative FlowPilot packet-result contract rows.

This module is deliberately dependency-light so runtime validators, FlowGuard
models, fake-AI parity checks, and tests can share one current-contract row set
without importing the full runtime.
"""

from __future__ import annotations

from typing import Any, Mapping

try:  # pragma: no cover - direct import fallback for test harnesses.
    from . import packet_stage_evidence_matrix
except ImportError:  # pragma: no cover
    import packet_stage_evidence_matrix  # type: ignore


ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION = "flowpilot.terminal_supplemental_repair_contract.v1"
PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION = "flowpilot.parent_repair_scope_contract.v1"
NODE_PREWORK_FLOWGUARD_SCOPE = "node_prework_flowguard"
PM_FLOWGUARD_ACCEPTANCE_SCOPE = "pm_flowguard_acceptance"

REVIEW_REPORT_REQUIRED_FIELDS = (
    "pm_visible_summary",
    "reviewed_by_role",
    "passed",
    "findings",
    "blockers",
    "pm_suggestion_items",
    "contract_self_check",
)
REVIEW_REPORT_REQUIRED_CHILD_FIELDS = ()
REVIEW_REPORT_EXPLICIT_ARRAY_FIELDS = (
    "pm_visible_summary",
    "findings",
    "blockers",
    "pm_suggestion_items",
)
FLOWGUARD_REPORT_REQUIRED_FIELDS = (
    "pm_visible_summary",
    "reviewed_by_role",
    "passed",
    "modeled_boundary",
    "blockers",
    "pm_suggestion_items",
    "contract_self_check",
)
FLOWGUARD_REPORT_REQUIRED_CHILD_FIELDS = ()
FLOWGUARD_REPORT_EXPLICIT_ARRAY_FIELDS = (
    "pm_visible_summary",
    "blockers",
    "pm_suggestion_items",
)
FLOWGUARD_REPORT_NON_EMPTY_ARRAY_FIELDS = ("pm_visible_summary",)
REVIEW_REPORT_NON_EMPTY_ARRAY_FIELDS = ("pm_visible_summary", "pm_suggestion_items")
TERMINAL_BACKWARD_REPLAY_REQUIRED_FIELDS = (
    "pm_visible_summary",
    "reviewed_by_role",
    "passed",
    "findings",
    "blockers",
    "pm_suggestion_items",
    "final_artifact_refs",
    "acceptance_item_closure",
    "route_segment_replay",
    "waiver_records",
    "final_blockers",
    "contract_self_check",
)
TERMINAL_BACKWARD_REPLAY_REQUIRED_CHILD_FIELDS = ()
TERMINAL_BACKWARD_REPLAY_EXPLICIT_ARRAY_FIELDS = (
    "pm_visible_summary",
    "findings",
    "blockers",
    "pm_suggestion_items",
    "final_artifact_refs",
    "acceptance_item_closure",
    "route_segment_replay",
    "waiver_records",
    "final_blockers",
)
TERMINAL_BACKWARD_REPLAY_NON_EMPTY_ARRAY_FIELDS = (
    "pm_visible_summary",
    "pm_suggestion_items",
    "final_artifact_refs",
    "acceptance_item_closure",
)
PM_DISPOSITION_REQUIRED_FIELDS = (
    "decision",
    "reason",
    "acceptance_item_disposition",
)
PM_DISPOSITION_EXPLICIT_ARRAY_FIELDS = ("acceptance_item_disposition",)
PM_FLOWGUARD_ACCEPTANCE_REQUIRED_FIELDS = (
    "decision",
    "reason",
    "flowguard_absorption",
    "accepted_flowguard_result_id",
)


PACKET_RESULT_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "family_id": "task.high_standard_contract",
        "packet_kind": "task",
        "route_scope": "high_standard_contract",
        "owner": "flowpilot_core_runtime",
        "validator": "_high_standard_contract_result_violation",
        "required_fields": ("requirements", "acceptance_item_registry"),
        "required_child_fields": (
            "requirements[].requirement_id",
            "requirements[].classification",
            "requirements[].summary",
            "requirements[].source_user_intent",
            "requirements[].closure_rule",
            "acceptance_item_registry.items[]",
            "acceptance_item_registry.items[].acceptance_item_id",
            "acceptance_item_registry.items[].source_type",
            "acceptance_item_registry.items[].summary",
            "acceptance_item_registry.items[].quality_floor",
            "acceptance_item_registry.items[].future_evidence_rule",
            "acceptance_item_registry.items[].status",
        ),
        "forbidden_fields": (
            "decision",
            "pm_visible_summary",
            "overall_contract",
            "contract_rows",
            "requirements[].evidence_rule",
            "requirements[].closure_blocking",
            "requirements[].report_only_closure_allowed",
            "acceptance_item_registry.items[].owner_node_ids",
            "acceptance_item_registry.items[].review_gate_ids",
            "acceptance_item_registry.items[].final_replay_required",
            "acceptance_item_registry.items[].low_quality_failure_patterns",
            "acceptance_item_registry.items[].required_evidence",
        ),
        "fake_ai_success_fields": ("requirements", "acceptance_item_registry"),
        "unlocks": "high_standard_contract_flowguard_review",
    },
    {
        "family_id": "task.discovery",
        "packet_kind": "task",
        "route_scope": "discovery",
        "owner": "flowpilot_core_runtime",
        "validator": "_discovery_result_violation",
        "required_fields": (
            "decision",
            "material_sources",
            "material_sufficiency",
            "candidate_skill_inventory",
        ),
        "required_child_fields": (),
        "forbidden_fields": ("local_skill_inventory", "candidate_only_skill_policy"),
        "fake_ai_success_fields": (
            "decision",
            "pm_visible_summary",
            "material_sources",
            "material_sufficiency",
            "candidate_skill_inventory",
        ),
        "unlocks": "discovery_record_flowguard_review",
    },
    {
        "family_id": "task.skill_standard",
        "packet_kind": "task",
        "route_scope": "skill_standard",
        "owner": "flowpilot_core_runtime",
        "validator": "_skill_standard_result_violation",
        "required_fields": ("decision", "obligations"),
        "required_child_fields": (
            "obligations[].obligation_id",
            "obligations[].skill",
            "obligations[].classification",
            "obligations[].role_use",
            "obligations[].use_context",
            "obligations[].evidence_rule",
        ),
        "forbidden_fields": (
            "selected_skills",
            "default_required_obligation",
            "obligations[].evidence_required",
            "obligations[].closure_blocking",
        ),
        "fake_ai_success_fields": ("decision", "pm_visible_summary", "obligations"),
        "unlocks": "skill_standard_contract_flowguard_review",
    },
    {
        "family_id": "task.planning",
        "packet_kind": "task",
        "route_scope": "planning",
        "owner": "flowpilot_core_runtime",
        "validator": "_parse_strict_route_plan",
        "required_fields": ("schema_version", "decision", "nodes"),
        "required_child_fields": ("nodes[].node_id", "nodes[].title"),
        "forbidden_fields": ("route_nodes",),
        "fake_ai_success_fields": ("schema_version", "decision", "nodes"),
        "unlocks": "route_materialization_after_review",
    },
    {
        "family_id": "task.node_acceptance_plan",
        "packet_kind": "task",
        "route_scope": "node_acceptance_plan",
        "owner": "flowpilot_core_runtime",
        "validator": "_node_context_package_from_pm_result",
        "required_fields": ("decision",),
        "required_child_fields": (
            "node_context_package when decision=pass",
            "node_context_package.purpose when decision=pass",
            "node_context_package.acceptance_criteria when decision=pass",
            "node_context_package.relevant_references when decision=pass",
            "node_context_package.known_risks when decision=pass",
            "node_context_package.acceptance_item_projection when decision=pass",
            "route_plan when decision=redesign_route",
            "route_plan.schema_version when decision=redesign_route",
            "route_plan.nodes[] when decision=redesign_route",
            "route_plan.nodes[].node_id when decision=redesign_route",
            "route_plan.nodes[].title when decision=redesign_route",
            "route_plan.nodes[].node_kind when decision=redesign_route",
            "route_plan.nodes[].parent_node_id/child_node_ids when decision=redesign_route",
        ),
        "forbidden_fields": (
            "optional_flowguard",
            "needs_flowguard",
            "maybe_flowguard",
            "flowguard_optional",
            "node_context_package.evidence_targets",
            "node_context_package.inspection_targets",
            "node_context_package.flowguard_targets",
            "node_context_package.reviewer_starting_points",
            "node_context_package.high_standard_requirement_ids",
            "node_context_package.low_quality_success_risks",
            "node_context_package.semantic_downgrade_risks",
            "node_context_package.work_packet_projection",
            "node_context_package.final_user_intent_checks",
            "node_context_package.structure_hygiene_expectation",
            "node_context_package.direct_evidence_closure_rules",
            "node_context_package.test_obligation_matrix",
        ),
        "fake_ai_success_fields": (
            "decision",
            "pm_visible_summary",
            "route_node_id",
            "reason",
            "proof_obligations",
            "repair_policy",
            "low_quality_success_risks",
            "node_context_package",
            "route_plan",
        ),
        "unlocks": "staged_node_acceptance_plan_effect",
    },
    {
        "family_id": "task.node",
        "packet_kind": "task",
        "route_scope": "node",
        "owner": "flowpilot_core_runtime",
        "validator": "_strict_packet_outcome_contract_violation",
        "required_fields": ("decision", "pm_visible_summary", "current_evidence_refs"),
        "required_child_fields": (),
        "explicit_array_fields": ("pm_visible_summary", "current_evidence_refs"),
        "non_empty_array_fields": ("pm_visible_summary", "current_evidence_refs"),
        "forbidden_fields": (
            "outcome",
            "status",
            "passed",
            "verdict",
            "result",
            "pass_or_block",
            "validation_status",
            "flowguard_report",
        ),
        "fake_ai_success_fields": ("decision", "pm_visible_summary", "current_evidence_refs"),
        "unlocks": "node_result_flowguard_review",
    },
    {
        "family_id": "review.parent_backward_replay",
        "packet_kind": "review",
        "route_scope": "parent_backward_replay",
        "owner": "flowpilot_core_runtime",
        "validator": "_parent_backward_replay_result_violation",
        "required_fields": (
            "pm_visible_summary",
            "reviewed_by_role",
            "passed",
            "parent_node_id",
            "child_node_ids",
            "child_evidence_refs",
            "findings",
            "blockers",
            "pm_suggestion_items",
            "contract_self_check",
        ),
        "required_child_fields": (),
        "explicit_array_fields": (
            "pm_visible_summary",
            "child_node_ids",
            "child_evidence_refs",
            "findings",
            "blockers",
            "pm_suggestion_items",
        ),
        "non_empty_array_fields": ("pm_visible_summary", "child_node_ids", "child_evidence_refs"),
        "forbidden_fields": (
            "decision",
            "composition_decision",
            "outcome",
            "status",
            "verdict",
            "result",
            "pass_or_block",
            "validation_status",
            "review_id",
            "independent_review_id",
            "parent_backward_replay_review_id",
        ),
        "fake_ai_success_fields": (
            "pm_visible_summary",
            "reviewed_by_role",
            "passed",
            "parent_node_id",
            "child_node_ids",
            "child_evidence_refs",
            "findings",
            "blockers",
            "pm_suggestion_items",
            "contract_self_check",
        ),
        "unlocks": "parent_backward_review_pm_absorption",
    },
    {
        "family_id": "flowguard_check.post_result",
        "packet_kind": "flowguard_check",
        "route_scope": "<subject_route_scope>",
        "owner": "flowpilot_core_runtime",
        "validator": "_current_result_submission_contract_violation",
        "required_fields": FLOWGUARD_REPORT_REQUIRED_FIELDS,
        "required_child_fields": FLOWGUARD_REPORT_REQUIRED_CHILD_FIELDS,
        "explicit_array_fields": FLOWGUARD_REPORT_EXPLICIT_ARRAY_FIELDS,
        "non_empty_array_fields": FLOWGUARD_REPORT_NON_EMPTY_ARRAY_FIELDS,
        "forbidden_fields": (
            "decision",
            "api_fallback_manual_block_eval",
            "fallback_manual_block_eval",
            "commands_run",
            "counterexamples_or_absence",
            "hard_invariants",
            "skipped_checks",
            "model_obligations",
            "ordinary_test_evidence",
            "missing_test_kinds",
            "conformance_boundary",
            "confidence_boundary",
            "residual_blindspots",
            "background_artifact_completion",
            "evidence_consistency",
        ),
        "fake_ai_success_fields": (
            *FLOWGUARD_REPORT_REQUIRED_FIELDS,
            "semantic_recheck",
            "subject_artifacts_consumed",
        ),
        "unlocks": "review_packet_release",
    },
    {
        "family_id": "review.any_current_subject",
        "packet_kind": "review",
        "route_scope": "<subject_route_scope>",
        "owner": "flowpilot_core_runtime",
        "validator": "_current_result_submission_contract_violation",
        "required_fields": REVIEW_REPORT_REQUIRED_FIELDS,
        "required_child_fields": REVIEW_REPORT_REQUIRED_CHILD_FIELDS,
        "explicit_array_fields": REVIEW_REPORT_EXPLICIT_ARRAY_FIELDS,
        "non_empty_array_fields": REVIEW_REPORT_NON_EMPTY_ARRAY_FIELDS,
        "forbidden_fields": (
            "decision",
            "outcome",
            "status",
            "verdict",
            "result",
            "validation_status",
            "direct_evidence_paths_checked",
            "independent_challenge",
            "residual_risks",
        ),
        "fake_ai_success_fields": REVIEW_REPORT_REQUIRED_FIELDS,
        "unlocks": "system_validation",
    },
    {
        "family_id": "review.terminal_backward_replay",
        "packet_kind": "review",
        "route_scope": "terminal_backward_replay",
        "owner": "flowpilot_core_runtime",
        "validator": "_terminal_backward_replay_result_violation",
        "required_fields": TERMINAL_BACKWARD_REPLAY_REQUIRED_FIELDS,
        "required_child_fields": TERMINAL_BACKWARD_REPLAY_REQUIRED_CHILD_FIELDS,
        "explicit_array_fields": TERMINAL_BACKWARD_REPLAY_EXPLICIT_ARRAY_FIELDS,
        "non_empty_array_fields": TERMINAL_BACKWARD_REPLAY_NON_EMPTY_ARRAY_FIELDS,
        "forbidden_fields": (
            "decision",
            "outcome",
            "status",
            "verdict",
            "result",
            "validation_status",
            "segment_reviews",
            "repair_restart_policy",
            "final_artifact_hygiene_review",
            "independent_challenge",
            "recommended_resolution",
        ),
        "fake_ai_success_fields": TERMINAL_BACKWARD_REPLAY_REQUIRED_FIELDS,
        "unlocks": "terminal_backward_replay_closure_confirmation",
    },
    {
        "family_id": "pm_repair_decision.pm_repair_decision",
        "packet_kind": "pm_repair_decision",
        "route_scope": "pm_repair_decision",
        "owner": "flowpilot_core_runtime",
        "validator": "_parse_pm_repair_decision_body",
        "required_fields": ("decision", "reason", "target_blocker_id", "next_action"),
        "required_child_fields": (
            "authority_ref when decision=waive_with_authority",
            "repair_parent_scope_contract when decision=repair_parent_scope",
            "repair_parent_scope_contract.source_parent_node_id when decision=repair_parent_scope",
            "repair_parent_scope_contract.inherit_existing_children when decision=repair_parent_scope",
            "repair_parent_scope_contract.repair_child_specs[] when decision=repair_parent_scope",
            "repair_parent_scope_contract.repair_child_specs[].node_id when decision=repair_parent_scope",
            "repair_parent_scope_contract.repair_child_specs[].purpose when decision=repair_parent_scope",
            "repair_parent_scope_contract.repair_child_specs[].required_evidence when decision=repair_parent_scope",
            "route_plan when decision=redesign_route",
            "route_plan.schema_version when decision=redesign_route",
            "route_plan.nodes[] when decision=redesign_route",
            "route_plan.nodes[].node_id when decision=redesign_route",
            "route_plan.nodes[].title when decision=redesign_route",
            "route_plan.nodes[].node_kind when decision=redesign_route",
            "route_plan.nodes[].parent_node_id/child_node_ids when decision=redesign_route",
            "repair_lineage.original_blocker_id when this is a repeated repair",
            "repair_lineage.prior_repair_packet_id when this is a repeated repair",
            "repair_lineage.prior_repair_result_id when this is a repeated repair",
            "repair_lineage.prior_repair_evidence_refs when this is a repeated repair",
            "repair_lineage.failed_recheck_report_id when this is a repeated repair",
            "repair_lineage.prior_failure_reason when this is a repeated repair",
            "repair_lineage.current_blocking_report_id when this is a repeated repair",
            "repair_lineage.new_repair_delta when this is a repeated repair",
            "repair_lineage.return_gate when this is a repeated repair",
            "supplemental_repair_contract when terminal repair continues",
            "supplemental_repair_contract.schema_version when terminal repair continues",
            "supplemental_repair_contract.contract_id when terminal repair continues",
            "supplemental_repair_contract.round_number when terminal repair continues",
            "supplemental_repair_contract.original_contract_hash when terminal repair continues",
            "supplemental_repair_contract.terminal_blocker_id when terminal repair continues",
            "supplemental_repair_contract.terminal_gap_report_result_id when terminal repair continues",
            "supplemental_repair_contract.repair_items[] when terminal repair continues",
            "supplemental_repair_contract.repair_items[].owner_repair_node_id when terminal repair continues",
            "supplemental_repair_contract.repair_items[].acceptance_item_ids when terminal repair continues",
            "repair_obligation_disposition[] when repair_evidence_obligations exist",
            "repair_obligation_disposition[].obligation_id when repair_evidence_obligations exist",
            "repair_obligation_disposition[].disposition when repair_evidence_obligations exist",
            "repair_obligation_disposition[].return_gate when repair_evidence_obligations exist",
            "repair_obligation_disposition[].evidence_kind when repair_evidence_obligations exist",
        ),
        "forbidden_fields": (
            "authority",
            "summary",
            "repair_decision",
            "pm_repair_decision",
            "supplemental_contract",
            "repair_contract",
            "terminal_repair_contract",
        ),
        "fake_ai_success_fields": (
            "decision",
            "reason",
            "authority_ref",
            "target_blocker_id",
            "next_action",
            "route_plan",
            "repair_lineage",
            "repair_parent_scope_contract",
            "supplemental_repair_contract",
            "repair_obligation_disposition",
        ),
        "unlocks": "current_repair_packet_or_terminal_block",
    },
    {
        "family_id": "pm_disposition.node_pm_disposition",
        "packet_kind": "pm_disposition",
        "route_scope": "node_pm_disposition",
        "owner": "flowpilot_core_runtime",
        "validator": "_decision_from_pm_body",
        "required_fields": PM_DISPOSITION_REQUIRED_FIELDS,
        "required_child_fields": (),
        "explicit_array_fields": PM_DISPOSITION_EXPLICIT_ARRAY_FIELDS,
        "forbidden_fields": (
            "summary",
            "pm_disposition_summary",
            "covered_requirement_ids",
            "accepted_acceptance_item_ids",
            "blocked_acceptance_item_ids",
            "waived_acceptance_item_ids",
            "superseded_acceptance_item_ids",
            "reviewer_absorption",
            "flowguard_absorption",
            "residual_risk_disposition",
            "semantic_downgrade_disposition",
            "validation_evidence_ids",
            "waived_requirement_ids",
        ),
        "fake_ai_success_fields": PM_DISPOSITION_REQUIRED_FIELDS,
        "unlocks": "node_frontier_disposition_or_staged_route_gate",
    },
    {
        "family_id": "pm_flowguard_acceptance.pm_flowguard_acceptance",
        "packet_kind": "pm_flowguard_acceptance",
        "route_scope": PM_FLOWGUARD_ACCEPTANCE_SCOPE,
        "owner": "flowpilot_core_runtime",
        "validator": "_parse_pm_flowguard_acceptance_body",
        "required_fields": PM_FLOWGUARD_ACCEPTANCE_REQUIRED_FIELDS,
        "required_child_fields": (
            "route_plan when decision=redesign_route",
            "route_plan.schema_version when decision=redesign_route",
            "route_plan.nodes[] when decision=redesign_route",
            "route_plan.nodes[].node_id when decision=redesign_route",
            "route_plan.nodes[].title when decision=redesign_route",
            "route_plan.nodes[].node_kind when decision=redesign_route",
            "route_plan.nodes[].parent_node_id/child_node_ids when decision=redesign_route",
        ),
        "forbidden_fields": (
            "optional_flowguard",
            "needs_flowguard",
            "maybe_flowguard",
            "flowguard_optional",
            "summary",
            "pm_absorption",
        ),
        "fake_ai_success_fields": (*PM_FLOWGUARD_ACCEPTANCE_REQUIRED_FIELDS, "route_plan"),
        "unlocks": "reviewer_release_after_pm_flowguard_absorption",
    },
)


PACKET_RESULT_CONTRACTS_BY_FAMILY = {str(row["family_id"]): row for row in PACKET_RESULT_CONTRACTS}


def packet_result_family_id(envelope: Mapping[str, Any]) -> str:
    packet_kind = str(envelope.get("packet_kind", "task"))
    route_scope = str(envelope.get("route_scope") or "")
    if packet_kind == "task" and route_scope == "parent_backward_replay":
        return "unsupported.task_parent_backward_replay"
    if packet_kind == "task" and route_scope in {
        "high_standard_contract",
        "discovery",
        "skill_standard",
        "planning",
        "node_acceptance_plan",
    }:
        return f"task.{route_scope}"
    if packet_kind == "task":
        return "task.node"
    if packet_kind == "flowguard_check":
        return "flowguard_check.post_result"
    if packet_kind == "review" and route_scope == "parent_backward_replay":
        return "review.parent_backward_replay"
    if packet_kind == "review" and route_scope == "terminal_backward_replay":
        return "review.terminal_backward_replay"
    if packet_kind == "review":
        return "review.any_current_subject"
    if packet_kind == "pm_repair_decision":
        return "pm_repair_decision.pm_repair_decision"
    if packet_kind == "pm_disposition":
        return "pm_disposition.node_pm_disposition"
    if packet_kind == "pm_flowguard_acceptance":
        return "pm_flowguard_acceptance.pm_flowguard_acceptance"
    return f"{packet_kind}.{route_scope or 'unknown'}"


def contract_for_family(family_id: str) -> Mapping[str, Any] | None:
    return PACKET_RESULT_CONTRACTS_BY_FAMILY.get(family_id)


def stage_evidence_row_for_family(family_id: str) -> Mapping[str, Any]:
    return packet_stage_evidence_matrix.stage_evidence_row_for_family(family_id)


def stage_evidence_row_json_for_family(family_id: str) -> dict[str, Any]:
    return packet_stage_evidence_matrix.stage_evidence_row_json(family_id)


def role_visible_stage_evidence_row_json_for_family(family_id: str) -> dict[str, Any]:
    return packet_stage_evidence_matrix.role_visible_stage_evidence_row_json(family_id)


def allowed_value_options_for_family(family_id: str) -> Mapping[str, tuple[Any, ...]]:
    return packet_stage_evidence_matrix.allowed_value_options_for_family(family_id)


def allowed_value_options_json_for_family(family_id: str) -> dict[str, Any]:
    return {
        str(field): list(options)
        for field, options in allowed_value_options_for_family(family_id).items()
    }


def _copy_jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _copy_jsonable(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_copy_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_copy_jsonable(item) for item in value]
    return value


def _dedupe_strings(*groups: Any) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for group in groups:
        if not group:
            continue
        for item in group:
            text = str(item)
            if text:
                seen[text] = None
    return tuple(seen)


def normalize_result_contract_profile_ids(raw_ids: Any) -> tuple[str, ...]:
    if not isinstance(raw_ids, (list, tuple)):
        return ()
    allowed = set(packet_stage_evidence_matrix.RESULT_CONTRACT_PROFILE_IDS)
    normalized: list[str] = []
    for raw_id in raw_ids:
        profile_id = str(raw_id)
        if not profile_id:
            continue
        if profile_id not in allowed:
            raise KeyError(f"unsupported result contract profile: {profile_id}")
        normalized.append(profile_id)
    return _dedupe_strings(normalized)


def result_contract_profile_ids_from_envelope(envelope: Mapping[str, Any]) -> tuple[str, ...]:
    return normalize_result_contract_profile_ids(envelope.get("result_contract_profile_ids"))


def result_contract_profile_bindings_from_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    raw_bindings = envelope.get("result_contract_profile_bindings")
    if not isinstance(raw_bindings, Mapping):
        return {}
    return _copy_jsonable(raw_bindings)


def _profile_binding(profile_bindings: Mapping[str, Any] | None, profile_id: str) -> Mapping[str, Any]:
    if not isinstance(profile_bindings, Mapping):
        return {}
    binding = profile_bindings.get(profile_id)
    return binding if isinstance(binding, Mapping) else {}


def _profile_minimal_shape(profile_id: str, binding: Mapping[str, Any]) -> dict[str, Any]:
    if profile_id == "flowguard.semantic_recheck_required":
        coverage_boundary = str(binding.get("coverage_boundary") or "subject_bound_semantic")
        authorized_read_ids = [
            str(item)
            for item in binding.get("authorized_result_read_ids", [])
            if str(item)
        ] if isinstance(binding.get("authorized_result_read_ids"), list) else []
        repair_obligation_ids = [
            str(item)
            for item in binding.get("repair_obligation_ids", [])
            if str(item)
        ] if isinstance(binding.get("repair_obligation_ids"), list) else []
        return {
            "semantic_recheck": {
                "blocker_id": str(binding.get("blocker_id") or ""),
                "subject_result_consumed": True,
                "subject_bound_semantic_coverage": True,
                "coverage_boundary": coverage_boundary,
                "consumed_authorized_result_read_ids": authorized_read_ids,
                "consumed_repair_obligation_ids": repair_obligation_ids,
            }
        }
    if profile_id == "flowguard.subject_artifacts_consumed_required":
        artifact_ids = [
            str(item)
            for item in binding.get("artifact_ids", [])
            if str(item)
        ] if isinstance(binding.get("artifact_ids"), list) else []
        return {
            "subject_artifacts_consumed": [
                {"artifact_id": artifact_id}
                for artifact_id in artifact_ids
            ]
        }
    return {}


def _profile_allowed_value_options(
    profile_id: str,
    profile: Mapping[str, Any],
    binding: Mapping[str, Any],
) -> dict[str, tuple[Any, ...]]:
    options = {
        str(field): tuple(values)
        for field, values in (profile.get("allowed_value_options") or {}).items()
        if isinstance(values, (list, tuple))
    }
    if profile_id == "flowguard.semantic_recheck_required":
        blocker_id = str(binding.get("blocker_id") or "")
        if blocker_id:
            options["semantic_recheck.blocker_id"] = (blocker_id,)
        authorized_read_ids = tuple(
            str(item)
            for item in binding.get("authorized_result_read_ids", [])
            if str(item)
        ) if isinstance(binding.get("authorized_result_read_ids"), list) else ()
        if authorized_read_ids:
            options["semantic_recheck.consumed_authorized_result_read_ids[]"] = authorized_read_ids
        repair_obligation_ids = tuple(
            str(item)
            for item in binding.get("repair_obligation_ids", [])
            if str(item)
        ) if isinstance(binding.get("repair_obligation_ids"), list) else ()
        if repair_obligation_ids:
            options["semantic_recheck.consumed_repair_obligation_ids[]"] = repair_obligation_ids
    if profile_id == "flowguard.subject_artifacts_consumed_required":
        artifact_ids = tuple(
            str(item)
            for item in binding.get("artifact_ids", [])
            if str(item)
        ) if isinstance(binding.get("artifact_ids"), list) else ()
        if artifact_ids:
            options["subject_artifacts_consumed[].artifact_id"] = artifact_ids
    return options


def _profile_forbidden_fields(profile: Mapping[str, Any]) -> tuple[str, ...]:
    aliases = profile.get("forbidden_aliases")
    if not isinstance(aliases, Mapping):
        return ()
    return tuple(str(field) for field in aliases if str(field))


def effective_result_contract_for_family(
    family_id: str,
    *,
    result_contract_profile_ids: tuple[str, ...] | list[str] | None = None,
    result_contract_profile_bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    profile_ids = normalize_result_contract_profile_ids(result_contract_profile_ids or ())
    base_row = contract_for_family(family_id) or {}
    required_fields = list(required_fields_for_family(family_id))
    required_child_fields = list(required_child_fields_for_family(family_id))
    explicit_array_fields = list(explicit_array_fields_for_family(family_id))
    non_empty_array_fields = list(non_empty_array_fields_for_family(family_id))
    forbidden_fields = list(forbidden_fields_for_family(family_id))
    allowed_options: dict[str, tuple[Any, ...]] = dict(allowed_value_options_for_family(family_id))
    field_type_requirements: dict[str, str] = {}
    forbidden_aliases: dict[str, str] = {}
    minimal_valid_shape = minimal_valid_shape_for_family(family_id)

    for profile_id in profile_ids:
        profile = packet_stage_evidence_matrix.result_contract_profile(profile_id)
        if str(profile.get("family_id") or "") != family_id:
            raise KeyError(f"result contract profile {profile_id} does not apply to {family_id}")
        binding = _profile_binding(result_contract_profile_bindings, profile_id)
        required_fields.extend(str(field) for field in profile.get("required_fields", ()) if str(field))
        required_child_fields.extend(str(field) for field in profile.get("required_child_fields", ()) if str(field))
        explicit_array_fields.extend(str(field) for field in profile.get("explicit_array_fields", ()) if str(field))
        non_empty_array_fields.extend(str(field) for field in profile.get("non_empty_array_fields", ()) if str(field))
        forbidden_fields.extend(_profile_forbidden_fields(profile))
        allowed_options.update(_profile_allowed_value_options(profile_id, profile, binding))
        raw_types = profile.get("field_type_requirements")
        if isinstance(raw_types, Mapping):
            field_type_requirements.update({str(field): str(kind) for field, kind in raw_types.items()})
        raw_aliases = profile.get("forbidden_aliases")
        if isinstance(raw_aliases, Mapping):
            forbidden_aliases.update({str(alias): str(target) for alias, target in raw_aliases.items()})
        minimal_valid_shape.update(_profile_minimal_shape(profile_id, binding))

    return {
        "family_id": family_id,
        "result_contract_profile_ids": list(profile_ids),
        "result_contract_profile_bindings": _copy_jsonable(result_contract_profile_bindings or {}),
        "required_fields": list(_dedupe_strings(required_fields)),
        "required_child_fields": list(_dedupe_strings(required_child_fields)),
        "explicit_array_fields": list(_dedupe_strings(explicit_array_fields)),
        "non_empty_array_fields": list(_dedupe_strings(non_empty_array_fields)),
        "forbidden_fields": list(_dedupe_strings(forbidden_fields)),
        "allowed_value_options": {
            str(field): list(values)
            for field, values in allowed_options.items()
        },
        "field_type_requirements": field_type_requirements,
        "forbidden_aliases": forbidden_aliases,
        "minimal_valid_shape": minimal_valid_shape,
        "branch_valid_shapes": branch_valid_shapes_for_family(family_id),
        "validator": str(base_row.get("validator") or ""),
    }


def effective_result_contract_from_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    family_id = packet_result_family_id(envelope)
    return effective_result_contract_for_family(
        family_id,
        result_contract_profile_ids=result_contract_profile_ids_from_envelope(envelope),
        result_contract_profile_bindings=result_contract_profile_bindings_from_envelope(envelope),
    )


def required_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return ("decision",)
    return tuple(str(field) for field in row["required_fields"])


def forbidden_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return ()
    return tuple(str(field) for field in row["forbidden_fields"])


def required_child_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return ()
    return tuple(
        str(field)
        for field in row.get("required_child_fields", ())
        if " when " not in str(field)
    )


def explicit_array_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return ()
    return tuple(str(field) for field in row.get("explicit_array_fields", ()))


def non_empty_array_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return ()
    return tuple(str(field) for field in row.get("non_empty_array_fields", ()))


def fake_ai_success_fields_for_family(family_id: str) -> tuple[str, ...]:
    row = contract_for_family(family_id)
    if not row:
        return required_fields_for_family(family_id)
    return tuple(str(field) for field in row["fake_ai_success_fields"])


def undeclared_success_fields_for_family(family_id: str, payload: Mapping[str, Any]) -> tuple[str, ...]:
    declared = set(fake_ai_success_fields_for_family(family_id))
    return tuple(sorted(str(field) for field in payload if str(field) not in declared))


def forbidden_success_fields_for_family(family_id: str, payload: Mapping[str, Any]) -> tuple[str, ...]:
    forbidden = set(forbidden_fields_for_family(family_id))
    return tuple(sorted(str(field) for field in payload if str(field) in forbidden))


def strict_route_plan_minimal_shape() -> dict[str, Any]:
    return {
        "schema_version": ROUTE_PLAN_SCHEMA_VERSION,
        "nodes": [
            {
                "node_id": "repair-current-scope",
                "title": "Repair current scope",
                "node_kind": "module",
                "parent_node_id": "",
                "child_node_ids": ["repair-current-scope-leaf"],
                "responsibility": "pm",
                "acceptance_criteria": ["Current repair scope is decomposed into executable child work."],
                "acceptance_item_ids": [],
                "supplemental_repair_contract_ids": [],
                "supplemental_repair_item_ids": [],
            },
            {
                "node_id": "repair-current-scope-leaf",
                "title": "Execute repaired current scope",
                "node_kind": "leaf",
                "parent_node_id": "repair-current-scope",
                "child_node_ids": [],
                "responsibility": "worker",
                "acceptance_criteria": ["Current repair acceptance criterion."],
                "acceptance_item_ids": ["acc-001", "acc-002"],
                "supplemental_repair_contract_ids": [],
                "supplemental_repair_item_ids": [],
            }
        ],
    }


def terminal_supplemental_repair_contract_minimal_shape(round_number: int = 1) -> dict[str, Any]:
    return {
        "schema_version": SUPPLEMENTAL_REPAIR_CONTRACT_SCHEMA_VERSION,
        "contract_id": f"terminal-supplemental-repair-r{round_number}",
        "round_number": round_number,
        "original_contract_hash": "<current ledger contract_hash>",
        "terminal_blocker_id": "<terminal blocker id>",
        "terminal_gap_report_result_id": "<terminal reviewer result id>",
        "pm_reason": "Why this repair is required for the original user goal.",
        "repair_items": [
            {
                "repair_item_id": f"terminal-gap-r{round_number}-item-1",
                "gap_kind": "final_artifact_hygiene_gap",
                "hygiene_category": "artifact_lineage",
                "original_goal_link": "Which original user-goal obligation this item closes.",
                "reviewer_gap": "Concrete terminal Reviewer gap.",
                "required_repair": "Concrete repair work PM is adding.",
                "owner_repair_node_id": "repair-current-scope-leaf",
                "acceptance_item_ids": ["acc-001"],
                "required_evidence": ["fresh implementation evidence", "fresh validation evidence"],
                "status": "open",
            }
        ],
    }


def parent_repair_scope_contract_minimal_shape(source_parent_node_id: str = "parent-node-id") -> dict[str, Any]:
    return {
        "schema_version": PARENT_REPAIR_SCOPE_CONTRACT_SCHEMA_VERSION,
        "source_parent_node_id": source_parent_node_id,
        "inherit_existing_children": True,
        "repair_child_specs": [
            {
                "node_id": f"{source_parent_node_id}-repair-child-001",
                "title": "Repair parent scope blocker",
                "purpose": "Repair the blocked parent-scope obligation with current evidence.",
                "required_evidence": ["current repair child result", "parent replay authorization proof"],
                "acceptance_criteria": ["Current repair child evidence closes the parent-scope blocker."],
            }
        ],
    }


def repair_obligation_disposition_minimal_shape(
    disposition: str = "fresh_repair_packet_required",
    return_gate: str = "current_scope_repair_packet",
) -> list[dict[str, str]]:
    return [
        {
            "obligation_id": "repair-obligation-current-blocker-evidence",
            "disposition": disposition,
            "return_gate": return_gate,
            "evidence_kind": "current_blocker_evidence",
        }
    ]


def branch_valid_shapes_for_family(family_id: str) -> dict[str, Any]:
    if family_id == "review.terminal_backward_replay":
        pass_shape = minimal_valid_shape_for_family("review.terminal_backward_replay")
        block_shape = minimal_valid_shape_for_family("review.terminal_backward_replay")
        block_shape["final_blockers"] = [
            {
                "blocker_id": "terminal-blocker-001",
                "blocker_class": "terminal_closure",
                "summary": "Current delivered product does not satisfy the terminal replay target.",
                "required_repair": "Repair the delivered product or replay target before terminal closure.",
            }
        ]
        return {
            "passed=true": pass_shape,
            "passed=false": block_shape,
        }
    if family_id == "task.node_acceptance_plan":
        pass_shape = minimal_valid_shape_for_family("task.node_acceptance_plan")
        return {
            "decision=pass": pass_shape,
            "decision=redesign_route": {
                "decision": "redesign_route",
                "reason": "PM found the current node or route structure too coarse, too fine, or wrong.",
                "route_plan": strict_route_plan_minimal_shape(),
            },
            "decision=block": {
                "decision": "block",
                "pm_visible_summary": ["PM cannot write a safe node plan from current inputs."],
                "blocker_class": "missing_required_information",
                "recommended_resolution": "Provide the missing route or node context.",
            },
        }
    if family_id == "pm_repair_decision.pm_repair_decision":
        return {
            "decision=repair_current_scope": {
                "decision": "repair_current_scope",
                "reason": "Concrete PM repair reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "repair_current_scope",
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "fresh_repair_packet_required",
                    "current_scope_repair_packet",
                ),
            },
            "decision=repair_parent_scope": {
                "decision": "repair_parent_scope",
                "reason": "Concrete PM parent-scope repair reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "repair_parent_scope",
                "repair_parent_scope_contract": parent_repair_scope_contract_minimal_shape(),
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "parent_scope_repair_required",
                    "parent_scope_repair_packet",
                ),
            },
            "decision=redesign_route": {
                "decision": "redesign_route",
                "reason": "Concrete PM redesign reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "redesign_route",
                "route_plan": strict_route_plan_minimal_shape(),
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "route_redesign_required",
                    "route_redesign_gate",
                ),
            },
            "decision=redesign_route_terminal_supplemental": {
                "decision": "redesign_route",
                "reason": "Concrete PM terminal supplemental repair reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "redesign_route",
                "supplemental_repair_contract": terminal_supplemental_repair_contract_minimal_shape(),
                "route_plan": {
                    **strict_route_plan_minimal_shape(),
                    "nodes": [
                        {
                            **strict_route_plan_minimal_shape()["nodes"][0],
                            "supplemental_repair_contract_ids": ["terminal-supplemental-repair-r1"],
                        },
                        {
                            **strict_route_plan_minimal_shape()["nodes"][1],
                            "supplemental_repair_contract_ids": ["terminal-supplemental-repair-r1"],
                            "supplemental_repair_item_ids": ["terminal-gap-r1-item-1"],
                        },
                    ],
                },
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "route_redesign_required",
                    "route_redesign_gate",
                ),
            },
            "decision=waive_with_authority": {
                "decision": "waive_with_authority",
                "reason": "Concrete PM waiver reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "waive_with_authority",
                "authority_ref": "current authority reference",
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "waived_with_authority",
                    "authority_record",
                ),
            },
            "decision=stop_for_user": {
                "decision": "stop_for_user",
                "reason": "Concrete stop reason for user.",
                "target_blocker_id": "blocker-current",
                "next_action": "stop_for_user",
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "stop_for_user",
                    "user_input",
                ),
            },
            "decision=break_glass": {
                "decision": "break_glass",
                "reason": "Concrete FlowPilot control-plane break-glass reason.",
                "target_blocker_id": "blocker-current",
                "next_action": "break_glass",
                "repair_obligation_disposition": repair_obligation_disposition_minimal_shape(
                    "break_glass",
                    "controller_break_glass",
                ),
            },
        }
    if family_id == "pm_flowguard_acceptance.pm_flowguard_acceptance":
        return {
            "decision=accept": {
                "decision": "accept",
                "reason": "PM absorbed the FlowGuard report and keeps the staged structural decision.",
                "flowguard_absorption": "Concrete PM absorption of current FlowGuard findings.",
                "accepted_flowguard_result_id": "result-flowguard-current",
            },
            "decision=redesign_route": {
                "decision": "redesign_route",
                "reason": "PM absorbed FlowGuard findings and rewrote the route plan.",
                "flowguard_absorption": "Concrete PM absorption of current FlowGuard findings.",
                "accepted_flowguard_result_id": "result-flowguard-current",
                "route_plan": strict_route_plan_minimal_shape(),
            },
            "decision=block": {
                "decision": "block",
                "reason": "PM cannot proceed with the structural decision after absorbing FlowGuard.",
                "flowguard_absorption": "Concrete PM absorption of current FlowGuard findings.",
                "accepted_flowguard_result_id": "result-flowguard-current",
            },
            "decision=stop_for_user": {
                "decision": "stop_for_user",
                "reason": "PM requires user input after absorbing FlowGuard.",
                "flowguard_absorption": "Concrete PM absorption of current FlowGuard findings.",
                "accepted_flowguard_result_id": "result-flowguard-current",
            },
            "decision=break_glass": {
                "decision": "break_glass",
                "reason": "PM found a FlowPilot control-plane defect while absorbing FlowGuard.",
                "flowguard_absorption": "Concrete PM absorption of current FlowGuard findings.",
                "accepted_flowguard_result_id": "result-flowguard-current",
            },
        }
    return {}


def minimal_valid_shape_for_family(family_id: str) -> dict[str, Any]:
    if family_id == "task.high_standard_contract":
        return {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Concrete requirement summary.",
                    "source_user_intent": "Current sealed startup request.",
                    "closure_rule": "Future closure requires current evidence or explicit waiver at the owning gate.",
                }
            ],
            "acceptance_item_registry": {
                "schema_version": "flowpilot.acceptance_item_registry.v1",
                "items": [
                    {
                        "acceptance_item_id": "acc-001",
                        "source_type": "user_explicit",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Complete the requested outcome.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Future owner nodes and terminal replay must close this item.",
                        "status": "active",
                    },
                    {
                        "acceptance_item_id": "acc-002",
                        "source_type": "pm_high_standard",
                        "source_requirement_ids": ["hsr-001"],
                        "summary": "Hold the result to the highest reasonable current-run quality bar.",
                        "quality_floor": "high_quality_required",
                        "future_evidence_rule": "Future owner nodes and terminal replay must close this item.",
                        "status": "active",
                    }
                ],
            },
        }
    if family_id == "task.discovery":
        return {
            "decision": "pass",
            "material_sources": ["current source id"],
            "material_sufficiency": "sufficient_for_route_planning",
            "candidate_skill_inventory": [],
        }
    if family_id == "task.skill_standard":
        return {
            "decision": "pass",
            "obligations": [
                {
                    "obligation_id": "skill-std-001",
                    "skill": "skill id",
                    "classification": "required",
                    "role_use": "flowguard_operator",
                    "use_context": "node_validation",
                    "evidence_rule": "FlowGuard operator produces current model/report evidence in its own packet.",
                }
            ],
        }
    if family_id == "task.planning":
        return {"schema_version": ROUTE_PLAN_SCHEMA_VERSION, "decision": "pass", "nodes": []}
    if family_id == "task.node_acceptance_plan":
        return {
            "decision": "pass",
            "node_context_package": {
                "purpose": "Current node purpose.",
                "acceptance_criteria": ["criterion"],
                "relevant_references": ["reference"],
                "known_risks": ["risk"],
                "acceptance_item_projection": [],
            },
        }
    if family_id == "pm_repair_decision.pm_repair_decision":
        return {
            "decision": "repair_current_scope",
            "reason": "Concrete PM repair reason.",
            "target_blocker_id": "blocker-current",
            "next_action": "repair_current_scope",
        }
    if family_id == "pm_disposition.node_pm_disposition":
        return {
            "decision": "accept",
            "reason": "Concrete PM disposition reason.",
            "acceptance_item_disposition": [
                {
                    "acceptance_item_id": "acc-001",
                    "disposition": "accepted",
                    "basis": "Current node evidence and required reviews support this item.",
                }
            ],
        }
    if family_id == "pm_flowguard_acceptance.pm_flowguard_acceptance":
        return {
            "decision": "accept",
            "reason": "PM absorbed the current FlowGuard report and keeps the staged structural plan.",
            "flowguard_absorption": "PM accepted FlowGuard's current modeled boundary, residual risks, and missing-test disposition.",
            "accepted_flowguard_result_id": "result-flowguard-current",
        }
    if family_id.startswith("flowguard_check."):
        return {
            "pm_visible_summary": ["FlowGuard operator report is mechanically complete."],
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "modeled_boundary": "Current packet, current node, and current evidence only.",
            "blockers": [],
            "pm_suggestion_items": [
                "FlowPilot installed runtime self-check receipt was considered for this run; do not substitute a development-repository simulation script."
            ],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        }
    if family_id == "review.any_current_subject":
        return {
            "pm_visible_summary": ["Reviewer report is mechanically complete."],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "findings": [],
            "blockers": [],
            "pm_suggestion_items": [
                "PM decision-support: current minimum gate passes; consider whether a 9/10 quality optimization pass is useful before closure."
            ],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        }
    if family_id == "review.terminal_backward_replay":
        return {
            "pm_visible_summary": ["Terminal backward replay report is mechanically complete."],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "findings": [],
            "blockers": [],
            "pm_suggestion_items": [
                "PM decision-support: terminal replay passes; consider whether any segment deserves an optional quality improvement before final close."
            ],
            "final_artifact_refs": [
                {"id": "delivered-product", "status": "closed", "basis": "Final artifact was inspected directly."}
            ],
            "acceptance_item_closure": [
                {"id": "acc-001", "status": "closed", "basis": "Accepted item is closed by current evidence."}
            ],
            "route_segment_replay": [
                {
                    "segment_id": "delivered-product",
                    "segment_kind": "delivered_product",
                    "status": "closed",
                    "basis": "Segment is closed by current evidence.",
                }
            ],
            "waiver_records": [],
            "final_blockers": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        }
    if family_id == "task.node":
        return {
            "decision": "pass",
            "pm_visible_summary": ["Role-authored summary for PM."],
            "current_evidence_refs": ["current-output"],
        }
    if family_id == "review.parent_backward_replay":
        return {
            "pm_visible_summary": ["Parent backward review composes current child results."],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "parent_node_id": "parent-node",
            "child_node_ids": ["child-node"],
            "child_evidence_refs": ["child-result"],
            "findings": [],
            "blockers": [],
            "pm_suggestion_items": [
                "PM decision-support: parent backward review passes; continue only after current route memory is checked."
            ],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        }
    return {"decision": "pass", "pm_visible_summary": ["Role-authored summary for PM."]}
