"""Runtime system-card delivery sequence for FlowPilot protocol boot cards."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_decision_tables import MODEL_MISS_REVIEW_BLOCK_FLAGS


RUNTIME_SYSTEM_CARD_SEQUENCE: tuple[dict[str, Any], ...] = (
    {
        "flag": "flowguard_operator_route_check_card_delivered",
        "label": "flowguard_operator_route_process_check_card_delivered",
        "card_id": "flowguard_operator.route_process_check",
        "requires_flag": "route_draft_written_by_pm",
        "to_role": "flowguard_operator",
    },
    {
        "flag": "pm_process_route_model_decision_card_delivered",
        "label": "pm_process_route_model_decision_card_delivered",
        "card_id": "pm.process_route_model_decision",
        "requires_flag": "process_route_model_submitted",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_route_check_card_delivered",
        "label": "reviewer_route_challenge_card_delivered",
        "card_id": "reviewer.route_challenge",
        "requires_flag": "pm_process_route_model_accepted",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_current_node_card_delivered",
        "label": "pm_current_node_loop_phase_card_delivered",
        "card_id": "pm.current_node_loop",
        "requires_flag": "route_activated_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_node_started_event_delivered",
        "label": "pm_node_started_event_card_delivered",
        "card_id": "pm.event.node_started",
        "requires_flag": "route_activated_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_node_acceptance_plan_card_delivered",
        "label": "pm_node_acceptance_plan_phase_card_delivered",
        "card_id": "pm.node_acceptance_plan",
        "requires_flag": "pm_node_started_event_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_node_acceptance_plan_card_delivered",
        "label": "reviewer_node_acceptance_plan_review_card_delivered",
        "card_id": "reviewer.node_acceptance_plan_review",
        "requires_flag": "node_acceptance_plan_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_parent_backward_targets_card_delivered",
        "label": "pm_parent_backward_targets_phase_card_delivered",
        "card_id": "pm.parent_backward_targets",
        "requires_flag": "node_acceptance_plan_reviewer_passed",
        "requires_active_node_children": True,
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_parent_backward_replay_card_delivered",
        "label": "reviewer_parent_backward_replay_card_delivered",
        "card_id": "reviewer.parent_backward_replay",
        "requires_flag": "parent_backward_targets_built",
        "requires_active_node_children": True,
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_parent_segment_decision_card_delivered",
        "label": "pm_parent_segment_decision_card_delivered",
        "card_id": "pm.parent_segment_decision",
        "requires_flag": "parent_backward_replay_passed",
        "requires_active_node_children": True,
        "to_role": "project_manager",
    },
    {
        "flag": "pm_model_miss_triage_card_delivered",
        "label": "pm_model_miss_triage_phase_card_delivered",
        "card_id": "pm.model_miss_triage",
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
        "to_role": "project_manager",
    },
    {
        "flag": "pm_review_repair_card_delivered",
        "label": "pm_review_repair_phase_card_delivered",
        "card_id": "pm.review_repair",
        "requires_flag": "model_miss_triage_closed",
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
        "to_role": "project_manager",
    },
    {
        "flag": "pm_reviewer_blocked_event_delivered",
        "label": "pm_reviewer_blocked_event_card_delivered",
        "card_id": "pm.event.reviewer_blocked",
        "requires_any_flag": list(MODEL_MISS_REVIEW_BLOCK_FLAGS),
        "to_role": "project_manager",
    },
    {
        "flag": "pm_evidence_quality_package_card_delivered",
        "label": "pm_evidence_quality_package_card_delivered",
        "card_id": "pm.evidence_quality_package",
        "requires_flag": "node_completed_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_evidence_quality_card_delivered",
        "label": "reviewer_evidence_quality_review_card_delivered",
        "card_id": "reviewer.evidence_quality_review",
        "requires_flag": "evidence_quality_package_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_final_ledger_card_delivered",
        "label": "pm_final_ledger_phase_card_delivered",
        "card_id": "pm.final_ledger",
        "requires_flag": "evidence_quality_reviewer_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_final_backward_replay_card_delivered",
        "label": "reviewer_final_backward_replay_card_delivered",
        "card_id": "reviewer.final_backward_replay",
        "requires_flag": "final_ledger_built_clean",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_closure_card_delivered",
        "label": "pm_closure_phase_card_delivered",
        "card_id": "pm.closure",
        "requires_flag": "final_backward_replay_passed",
        "to_role": "project_manager",
    },
)


def runtime_system_card_catalog() -> dict[str, object]:
    """Return externally visible runtime-card sequence metadata."""

    return {
        "card_count": len(RUNTIME_SYSTEM_CARD_SEQUENCE),
        "card_ids": tuple(card["card_id"] for card in RUNTIME_SYSTEM_CARD_SEQUENCE),
        "flags": tuple(card["flag"] for card in RUNTIME_SYSTEM_CARD_SEQUENCE),
    }


__all__ = (
    "RUNTIME_SYSTEM_CARD_SEQUENCE",
    "runtime_system_card_catalog",
)
