"""Gate pass-to-block clear mappings for FlowPilot router protocol."""

from __future__ import annotations

from flowpilot_router_protocol_external_events import EXTERNAL_EVENTS
from flowpilot_router_protocol_gate_block_specs import GATE_OUTCOME_BLOCK_EVENTS

GATE_OUTCOME_PASS_CLEAR_FLAGS: dict[str, tuple[str, ...]] = {
    "reviewer_passes_research_direct_source_check": ("research_review_blocked",),
    "reviewer_passes_product_architecture": ("product_architecture_reviewer_blocked",),
    "product_officer_passes_product_architecture_modelability": (
        "product_behavior_model_blocked",
        "product_architecture_modelability_blocked",
    ),
    "product_officer_submits_product_behavior_model": (
        "product_behavior_model_blocked",
        "product_architecture_modelability_blocked",
    ),
    "reviewer_passes_root_acceptance_contract": ("root_contract_reviewer_blocked",),
    "product_officer_passes_root_acceptance_contract_modelability": ("root_contract_modelability_blocked",),
    "reviewer_passes_child_skill_gate_manifest": ("child_skill_manifest_reviewer_blocked",),
    "process_officer_passes_child_skill_conformance_model": ("child_skill_process_officer_blocked",),
    "product_officer_passes_child_skill_product_fit": ("child_skill_product_officer_blocked",),
    "process_officer_passes_route_check": (
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
    ),
    "process_officer_submits_process_route_model": (
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
    ),
    "product_officer_passes_route_check": ("product_officer_route_check_blocked",),
    "reviewer_passes_route_check": ("reviewer_route_check_blocked",),
    "reviewer_passes_parent_backward_replay": ("parent_backward_replay_blocked",),
    "reviewer_passes_evidence_quality_package": ("evidence_quality_reviewer_blocked",),
    "reviewer_final_backward_replay_passed": ("final_backward_replay_blocked",),
}

GATE_OUTCOME_PASS_CLEARS_EVENTS: dict[str, tuple[str, ...]] = {
    pass_event: tuple(
        block_event
        for block_event in GATE_OUTCOME_BLOCK_EVENTS
        if EXTERNAL_EVENTS[block_event]["flag"] in clear_flags
    )
    for pass_event, clear_flags in GATE_OUTCOME_PASS_CLEAR_FLAGS.items()
}

__all__ = (
    'GATE_OUTCOME_PASS_CLEAR_FLAGS',
    'GATE_OUTCOME_PASS_CLEARS_EVENTS',
)
