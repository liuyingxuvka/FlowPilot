"""Authoritative FlowPilot packet-result contract rows.

This module is deliberately dependency-light so runtime validators, FlowGuard
models, fake-AI parity checks, and tests can share one current-contract row set
without importing the full runtime.
"""

from __future__ import annotations

from typing import Any, Mapping


ROUTE_PLAN_SCHEMA_VERSION = "flowpilot.route_plan.v1"
NODE_PREWORK_FLOWGUARD_SCOPE = "node_prework_flowguard"


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
            "requirements[].closure_blocking",
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
        "required_fields": ("decision", "node_context_package"),
        "required_child_fields": (
            "node_context_package.purpose",
            "node_context_package.acceptance_criteria",
            "node_context_package.relevant_references",
            "node_context_package.evidence_targets",
            "node_context_package.inspection_targets",
            "node_context_package.known_risks",
            "node_context_package.flowguard_targets",
            "node_context_package.reviewer_starting_points",
        ),
        "forbidden_fields": (),
        "fake_ai_success_fields": (
            "decision",
            "pm_visible_summary",
            "route_node_id",
            "proof_obligations",
            "repair_policy",
            "low_quality_success_risks",
            "node_context_package",
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
        "forbidden_fields": ("outcome", "status", "passed", "verdict", "result", "pass_or_block", "validation_status"),
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
        "family_id": "flowguard_check.node_prework_flowguard",
        "packet_kind": "flowguard_check",
        "route_scope": NODE_PREWORK_FLOWGUARD_SCOPE,
        "owner": "flowpilot_core_runtime",
        "validator": "_current_result_submission_contract_violation",
        "required_fields": ("decision", "pm_visible_summary"),
        "required_child_fields": (),
        "forbidden_fields": ("api_fallback_manual_block_eval", "fallback_manual_block_eval"),
        "fake_ai_success_fields": ("decision", "pm_visible_summary"),
        "unlocks": "worker_packet_release",
    },
    {
        "family_id": "flowguard_check.post_result",
        "packet_kind": "flowguard_check",
        "route_scope": "<subject_route_scope>",
        "owner": "flowpilot_core_runtime",
        "validator": "_current_result_submission_contract_violation",
        "required_fields": ("decision", "pm_visible_summary"),
        "required_child_fields": (),
        "forbidden_fields": ("api_fallback_manual_block_eval", "fallback_manual_block_eval"),
        "fake_ai_success_fields": ("decision", "pm_visible_summary"),
        "unlocks": "review_packet_release",
    },
    {
        "family_id": "review.any_current_subject",
        "packet_kind": "review",
        "route_scope": "<subject_route_scope>",
        "owner": "flowpilot_core_runtime",
        "validator": "_current_result_submission_contract_violation",
        "required_fields": ("decision", "pm_visible_summary"),
        "required_child_fields": (),
        "forbidden_fields": ("outcome", "status", "passed", "verdict", "result", "pass_or_block", "validation_status"),
        "fake_ai_success_fields": ("decision", "pm_visible_summary"),
        "unlocks": "system_validation",
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
        "required_fields": ("decision", "reason"),
        "required_child_fields": (),
        "forbidden_fields": ("summary", "pm_disposition_summary"),
        "fake_ai_success_fields": ("decision", "reason", "pm_visible_summary"),
        "unlocks": "node_frontier_disposition_or_staged_route_gate",
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
    if packet_kind == "flowguard_check" and route_scope == NODE_PREWORK_FLOWGUARD_SCOPE:
        return "flowguard_check.node_prework_flowguard"
    if packet_kind == "flowguard_check":
        return "flowguard_check.post_result"
    if packet_kind == "review":
        return "review.any_current_subject"
    if packet_kind == "pm_repair_decision":
        return "pm_repair_decision.pm_repair_decision"
    if packet_kind == "pm_disposition":
        return "pm_disposition.node_pm_disposition"
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


def minimal_valid_shape_for_family(family_id: str) -> dict[str, Any]:
    if family_id == "task.high_standard_contract":
        return {
            "requirements": [
                {
                    "requirement_id": "hsr-001",
                    "classification": "hard_current",
                    "summary": "Concrete requirement summary.",
                    "closure_blocking": True,
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
            },
        }
    if family_id == "pm_repair_decision.pm_repair_decision":
        return {"decision": "repair_current_scope", "reason": "Concrete PM repair reason."}
    if family_id == "pm_disposition.node_pm_disposition":
        return {"decision": "accept", "reason": "Concrete PM disposition reason."}
    return {"decision": "pass", "pm_visible_summary": ["Role-authored summary for PM."]}
