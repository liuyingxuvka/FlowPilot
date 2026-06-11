"""Authoritative FlowPilot packet-result contract rows.

This module is deliberately dependency-light so runtime validators, FlowGuard
models, fake-AI parity checks, and tests can share one current-contract row set
without importing the full runtime.
"""

from __future__ import annotations

from typing import Any, Mapping


ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
NODE_PREWORK_FLOWGUARD_SCOPE = "node_prework_flowguard"
PM_FLOWGUARD_ACCEPTANCE_SCOPE = "pm_flowguard_acceptance"

REVIEW_REPORT_REQUIRED_FIELDS = (
    "pm_visible_summary",
    "reviewed_by_role",
    "passed",
    "direct_evidence_paths_checked",
    "independent_challenge",
    "findings",
    "blockers",
    "residual_risks",
    "pm_suggestion_items",
    "contract_self_check",
)
REVIEW_REPORT_REQUIRED_CHILD_FIELDS = (
    "independent_challenge.scope_restatement",
    "independent_challenge.explicit_and_implicit_commitments",
    "independent_challenge.failure_hypotheses",
    "independent_challenge.challenge_actions",
    "independent_challenge.blocking_findings",
    "independent_challenge.non_blocking_findings",
    "independent_challenge.pass_or_block",
    "independent_challenge.reroute_request",
    "independent_challenge.challenge_waivers",
)
REVIEW_REPORT_EXPLICIT_ARRAY_FIELDS = (
    "pm_visible_summary",
    "direct_evidence_paths_checked",
    "findings",
    "blockers",
    "residual_risks",
    "pm_suggestion_items",
    "independent_challenge.explicit_and_implicit_commitments",
    "independent_challenge.failure_hypotheses",
    "independent_challenge.challenge_actions",
    "independent_challenge.blocking_findings",
    "independent_challenge.non_blocking_findings",
    "independent_challenge.reroute_request",
    "independent_challenge.challenge_waivers",
)
FLOWGUARD_REPORT_REQUIRED_FIELDS = (
    "pm_visible_summary",
    "reviewed_by_role",
    "passed",
    "modeled_boundary",
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
    "pm_suggestion_items",
    "evidence_consistency",
    "contract_self_check",
)
FLOWGUARD_REPORT_REQUIRED_CHILD_FIELDS = (
    "evidence_consistency.self_check_passed",
    "evidence_consistency.child_reports_all_passed",
    "evidence_consistency.blocking_child_reports",
    "evidence_consistency.hard_evidence_decision",
)
FLOWGUARD_REPORT_EXPLICIT_ARRAY_FIELDS = (
    "pm_visible_summary",
    "commands_run",
    "counterexamples_or_absence",
    "hard_invariants",
    "skipped_checks",
    "model_obligations",
    "ordinary_test_evidence",
    "missing_test_kinds",
    "residual_blindspots",
    "background_artifact_completion",
    "pm_suggestion_items",
    "evidence_consistency.blocking_child_reports",
)
FLOWGUARD_REPORT_NON_EMPTY_ARRAY_FIELDS = (
    "pm_visible_summary",
    "commands_run",
    "hard_invariants",
    "model_obligations",
    "ordinary_test_evidence",
)
REVIEW_REPORT_NON_EMPTY_ARRAY_FIELDS = (
    "pm_visible_summary",
    "direct_evidence_paths_checked",
    "independent_challenge.explicit_and_implicit_commitments",
    "independent_challenge.failure_hypotheses",
    "independent_challenge.challenge_actions",
)
TERMINAL_BACKWARD_REPLAY_REQUIRED_FIELDS = (
    *REVIEW_REPORT_REQUIRED_FIELDS,
    "segment_reviews",
    "repair_restart_policy",
)
TERMINAL_BACKWARD_REPLAY_REQUIRED_CHILD_FIELDS = (
    *REVIEW_REPORT_REQUIRED_CHILD_FIELDS,
    "segment_reviews[].segment_id",
    "segment_reviews[].segment_kind",
    "segment_reviews[].reviewed_by_role",
    "segment_reviews[].passed",
    "segment_reviews[].pm_segment_decision",
    "segment_reviews[].direct_evidence_paths_checked",
)
TERMINAL_BACKWARD_REPLAY_EXPLICIT_ARRAY_FIELDS = (
    *REVIEW_REPORT_EXPLICIT_ARRAY_FIELDS,
    "segment_reviews",
    "segment_reviews[].direct_evidence_paths_checked",
)
TERMINAL_BACKWARD_REPLAY_NON_EMPTY_ARRAY_FIELDS = (
    *REVIEW_REPORT_NON_EMPTY_ARRAY_FIELDS,
    "segment_reviews",
)
PM_DISPOSITION_REQUIRED_FIELDS = (
    "decision",
    "reason",
    "covered_requirement_ids",
    "reviewer_absorption",
    "flowguard_absorption",
    "residual_risk_disposition",
    "semantic_downgrade_disposition",
    "validation_evidence_ids",
    "waived_requirement_ids",
)
PM_DISPOSITION_EXPLICIT_ARRAY_FIELDS = (
    "covered_requirement_ids",
    "validation_evidence_ids",
    "waived_requirement_ids",
)
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
        "required_fields": ("requirements",),
        "required_child_fields": (
            "requirements[].requirement_id",
            "requirements[].classification",
            "requirements[].summary",
            "requirements[].source_user_intent",
            "requirements[].evidence_rule",
            "requirements[].closure_blocking",
            "requirements[].report_only_closure_allowed",
        ),
        "forbidden_fields": ("decision", "pm_visible_summary", "overall_contract", "contract_rows"),
        "fake_ai_success_fields": ("requirements",),
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
            "local_skill_inventory",
            "candidate_only_skill_policy",
        ),
        "required_child_fields": (),
        "forbidden_fields": (),
        "fake_ai_success_fields": (
            "decision",
            "pm_visible_summary",
            "material_sources",
            "material_sufficiency",
            "local_skill_inventory",
            "candidate_only_skill_policy",
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
            "obligations[].evidence_required",
            "obligations[].closure_blocking",
        ),
        "forbidden_fields": ("selected_skills", "default_required_obligation"),
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
            "node_context_package.evidence_targets when decision=pass",
            "node_context_package.inspection_targets when decision=pass",
            "node_context_package.known_risks when decision=pass",
            "node_context_package.flowguard_targets when decision=pass",
            "node_context_package.reviewer_starting_points when decision=pass",
            "node_context_package.high_standard_requirement_ids when decision=pass",
            "node_context_package.low_quality_success_risks when decision=pass",
            "node_context_package.semantic_downgrade_risks when decision=pass",
            "node_context_package.work_packet_projection when decision=pass",
            "node_context_package.final_user_intent_checks when decision=pass",
            "node_context_package.structure_hygiene_expectation when decision=pass",
            "node_context_package.direct_evidence_closure_rules when decision=pass",
            "node_context_package.test_obligation_matrix.pre_worker[] when decision=pass",
            "route_plan when decision=redesign_route",
            "route_plan.schema_version when decision=redesign_route",
            "route_plan.nodes[] when decision=redesign_route",
            "route_plan.nodes[].node_id when decision=redesign_route",
            "route_plan.nodes[].title when decision=redesign_route",
        ),
        "forbidden_fields": ("optional_flowguard", "needs_flowguard", "maybe_flowguard", "flowguard_optional"),
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
        "required_fields": ("decision", "pm_visible_summary"),
        "required_child_fields": (),
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
        "fake_ai_success_fields": ("decision", "pm_visible_summary"),
        "unlocks": "node_result_flowguard_review",
    },
    {
        "family_id": "task.parent_backward_replay",
        "packet_kind": "task",
        "route_scope": "parent_backward_replay",
        "owner": "flowpilot_core_runtime",
        "validator": "_strict_packet_outcome_contract_violation",
        "required_fields": ("decision", "pm_visible_summary"),
        "required_child_fields": (),
        "forbidden_fields": ("outcome", "status", "passed", "verdict", "result", "pass_or_block", "validation_status"),
        "fake_ai_success_fields": ("route_node_id", "decision", "pm_visible_summary", "composition_checked"),
        "unlocks": "parent_backward_replay_flowguard_review",
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
        "forbidden_fields": ("decision", "api_fallback_manual_block_eval", "fallback_manual_block_eval"),
        "fake_ai_success_fields": FLOWGUARD_REPORT_REQUIRED_FIELDS,
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
        "forbidden_fields": ("decision", "outcome", "status", "verdict", "result", "validation_status"),
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
        "forbidden_fields": ("decision", "outcome", "status", "verdict", "result", "validation_status"),
        "fake_ai_success_fields": TERMINAL_BACKWARD_REPLAY_REQUIRED_FIELDS,
        "unlocks": "terminal_backward_replay_closure_confirmation",
    },
    {
        "family_id": "pm_repair_decision.pm_repair_decision",
        "packet_kind": "pm_repair_decision",
        "route_scope": "pm_repair_decision",
        "owner": "flowpilot_core_runtime",
        "validator": "_parse_pm_repair_decision_body",
        "required_fields": ("decision", "reason"),
        "required_child_fields": (
            "authority_ref when decision=waive_with_authority",
            "route_plan when decision=redesign_route",
            "route_plan.schema_version when decision=redesign_route",
            "route_plan.nodes[] when decision=redesign_route",
            "route_plan.nodes[].node_id when decision=redesign_route",
            "route_plan.nodes[].title when decision=redesign_route",
        ),
        "forbidden_fields": ("authority", "summary", "repair_decision", "pm_repair_decision"),
        "fake_ai_success_fields": ("decision", "reason", "authority_ref", "route_plan"),
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
        "forbidden_fields": ("summary", "pm_disposition_summary"),
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
    if packet_kind == "task" and route_scope in {
        "high_standard_contract",
        "discovery",
        "skill_standard",
        "planning",
        "node_acceptance_plan",
        "parent_backward_replay",
    }:
        return f"task.{route_scope}"
    if packet_kind == "task":
        return "task.node"
    if packet_kind == "flowguard_check":
        return "flowguard_check.post_result"
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
                "responsibility": "worker",
                "acceptance_criteria": ["Current repair acceptance criterion."],
            }
        ],
    }


def branch_valid_shapes_for_family(family_id: str) -> dict[str, Any]:
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
            },
            "decision=repair_parent_scope": {
                "decision": "repair_parent_scope",
                "reason": "Concrete PM parent-scope repair reason.",
            },
            "decision=redesign_route": {
                "decision": "redesign_route",
                "reason": "Concrete PM redesign reason.",
                "route_plan": strict_route_plan_minimal_shape(),
            },
            "decision=waive_with_authority": {
                "decision": "waive_with_authority",
                "reason": "Concrete PM waiver reason.",
                "authority_ref": "current authority reference",
            },
            "decision=stop_for_user": {
                "decision": "stop_for_user",
                "reason": "Concrete stop reason for user.",
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
                    "evidence_rule": "Direct current evidence or explicit waiver required.",
                    "closure_blocking": True,
                    "report_only_closure_allowed": False,
                }
            ]
        }
    if family_id == "task.discovery":
        return {
            "decision": "pass",
            "material_sources": ["current source id"],
            "material_sufficiency": "sufficient_for_route_planning",
            "local_skill_inventory": [],
            "candidate_only_skill_policy": True,
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
                    "evidence_required": "current evidence",
                    "closure_blocking": True,
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
                "evidence_targets": ["evidence"],
                "inspection_targets": ["inspection"],
                "known_risks": ["risk"],
                "flowguard_targets": ["development_process"],
                "reviewer_starting_points": ["result"],
                "high_standard_requirement_ids": ["hsr-001"],
                "low_quality_success_risks": ["thin-success risk"],
                "semantic_downgrade_risks": ["semantic downgrade risk"],
                "work_packet_projection": ["copy hsr-001 into Worker, FlowGuard, Reviewer, and PM disposition packets"],
                "final_user_intent_checks": ["current node advances the user's real outcome"],
                "structure_hygiene_expectation": ["no fallback or compatibility branch may be added"],
                "direct_evidence_closure_rules": ["report-only closure is not sufficient"],
                "test_obligation_matrix": {
                    "pre_worker": [
                        {
                            "obligation_id": "test-obligation-001",
                            "source": "node_acceptance_plan",
                            "required_test_kind": "targeted_current_validation",
                            "owner_role": "worker",
                            "expected_evidence": "current validation evidence",
                            "freshness_rule": "after current node work",
                            "pm_disposition": "pending",
                        }
                    ]
                },
            },
        }
    if family_id == "pm_repair_decision.pm_repair_decision":
        return {"decision": "repair_current_scope", "reason": "Concrete PM repair reason."}
    if family_id == "pm_disposition.node_pm_disposition":
        return {
            "decision": "accept",
            "reason": "Concrete PM disposition reason.",
            "covered_requirement_ids": ["hsr-001"],
            "reviewer_absorption": "Reviewer findings absorbed into PM node disposition.",
            "flowguard_absorption": "FlowGuard boundary and missing-test report absorbed into PM node disposition.",
            "residual_risk_disposition": "No unresolved residual risk remains for this node.",
            "semantic_downgrade_disposition": "No semantic downgrade remains for this node.",
            "validation_evidence_ids": ["validation-current-node"],
            "waived_requirement_ids": [],
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
            "commands_run": ["python simulations/run_flowpilot_model_test_alignment_checks.py"],
            "counterexamples_or_absence": ["No counterexample in the current modeled boundary."],
            "hard_invariants": ["No stale evidence, fallback, or old packet shape accepted."],
            "skipped_checks": [],
            "model_obligations": ["Current packet-result contract fields match current role report contract."],
            "ordinary_test_evidence": ["Targeted runtime and fake-AI regression evidence."],
            "missing_test_kinds": [],
            "conformance_boundary": "Runtime validates mechanics; semantic adequacy remains FlowGuard-owned.",
            "confidence_boundary": "Scoped to the current packet-result family.",
            "residual_blindspots": [],
            "background_artifact_completion": [],
            "pm_suggestion_items": [],
            "evidence_consistency": {
                "self_check_passed": True,
                "child_reports_all_passed": True,
                "blocking_child_reports": [],
                "hard_evidence_decision": "pass",
            },
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
            "direct_evidence_paths_checked": ["current result body"],
            "independent_challenge": {
                "scope_restatement": "Review the current packet result against current acceptance criteria.",
                "explicit_and_implicit_commitments": ["current contract fields", "quality sufficient for next gate"],
                "failure_hypotheses": ["The result may satisfy fields without satisfying the task."],
                "challenge_actions": ["Checked current evidence and challenged the strongest likely failure."],
                "blocking_findings": [],
                "non_blocking_findings": [],
                "pass_or_block": "pass",
                "reroute_request": [],
                "challenge_waivers": [],
            },
            "findings": [],
            "blockers": [],
            "residual_risks": [],
            "pm_suggestion_items": [],
            "contract_self_check": {
                "all_required_fields_present": True,
                "exact_field_names_used": True,
                "empty_required_arrays_explicit": True,
                "runtime_mechanical_validation_passed": True,
                "semantic_sufficiency_reviewed_by_runtime": False,
            },
        }
    if family_id == "review.terminal_backward_replay":
        payload = minimal_valid_shape_for_family("review.any_current_subject")
        payload["pm_visible_summary"] = ["Terminal backward replay report is mechanically complete."]
        payload["segment_reviews"] = [
            {
                "segment_id": "delivered-product",
                "segment_kind": "delivered_product",
                "reviewed_by_role": "human_like_reviewer",
                "passed": True,
                "pm_segment_decision": "continue",
                "direct_evidence_paths_checked": ["final deliverable"],
            }
        ]
        payload["repair_restart_policy"] = "Any terminal replay repair invalidates terminal closure and requires replay restart from the delivered product unless PM records a narrower impacted-ancestor reason."
        return payload
    return {"decision": "pass", "pm_visible_summary": ["Role-authored summary for PM."]}
