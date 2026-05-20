"""Dispatch-recipient gate policy constants for FlowPilot router."""

from __future__ import annotations

from flowpilot_router_protocol_work_contracts import ROLE_WORK_RESULT_RETURNED_EVENT


FORMAL_WORK_PACKET_RELAY_ACTION_TYPES = {
    "relay_material_scan_packets",
    "relay_research_packet",
    "relay_current_node_packet",
    "relay_pm_role_work_request_packet",
}

DISPATCH_RECIPIENT_GATE_ACTION_TYPES = {
    "deliver_mail",
    "deliver_system_card",
    "deliver_system_card_bundle",
    *FORMAL_WORK_PACKET_RELAY_ACTION_TYPES,
}

DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS = {
    "relay_material_scan_packets": (
        "worker_scan_packet_bodies_delivered_after_dispatch",
        "worker_scan_results_returned",
    ),
    "relay_research_packet": ("worker_research_report_returned",),
    "relay_current_node_packet": ("worker_current_node_result_returned",),
    "relay_pm_role_work_request_packet": (ROLE_WORK_RESULT_RETURNED_EVENT,),
}

DISPATCH_RECIPIENT_GATE_CONTEXT_CARD_OUTPUT_EVENTS = {
    "pm.event.reviewer_report": (
        "pm_accepts_reviewed_material",
        "pm_requests_research_after_material_insufficient",
    ),
    "pm.event.reviewer_blocked": (
        "pm_records_model_miss_triage_decision",
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
    "pm.review_repair": (
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
}


__all__ = (
    "FORMAL_WORK_PACKET_RELAY_ACTION_TYPES",
    "DISPATCH_RECIPIENT_GATE_ACTION_TYPES",
    "DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS",
    "DISPATCH_RECIPIENT_GATE_CONTEXT_CARD_OUTPUT_EVENTS",
)
