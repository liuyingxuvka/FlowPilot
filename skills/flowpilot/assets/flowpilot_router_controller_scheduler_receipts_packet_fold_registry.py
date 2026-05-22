"""Registered Controller receipt evidence-fold action metadata."""

from __future__ import annotations


CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY: dict[str, dict[str, str]] = {
    "relay_material_scan_packets": {
        "kind": "packet_dispatch",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_packets_relayed",
    },
    "relay_research_packet": {
        "kind": "packet_dispatch",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_packet_relayed",
    },
    "relay_current_node_packet": {
        "kind": "packet_dispatch",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_packet_relayed",
    },
    "relay_pm_role_work_request_packet": {
        "kind": "packet_dispatch",
        "family": "pm_role_work",
        "record_source": "pm_role_work_request_index",
        "postcondition": "pm_role_work_request_packet_relayed",
    },
    "relay_material_scan_results_to_pm": {
        "kind": "result_relay",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_results_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_material_scan_results_to_reviewer": {
        "kind": "result_relay",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_results_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_research_result_to_pm": {
        "kind": "result_relay",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_result_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_research_result_to_reviewer": {
        "kind": "result_relay",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_current_node_result_to_pm": {
        "kind": "result_relay",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_result_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_current_node_result_to_reviewer": {
        "kind": "result_relay",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_pm_role_work_result_to_pm": {
        "kind": "result_relay",
        "family": "pm_role_work",
        "record_source": "pm_role_work_request_index",
        "postcondition": "pm_role_work_result_relayed_to_pm",
        "to_role": "project_manager",
    },
    "handle_control_blocker": {
        "kind": "control_blocker_delivery",
        "family": "control_blocker",
        "record_source": "control_blocker_artifact",
        "postcondition": "control_blocker_delivered",
    },
}


def _registered_controller_receipt_evidence_fold_actions() -> tuple[str, ...]:
    return tuple(sorted(CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY))


__all__ = (
    "CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY",
    "_registered_controller_receipt_evidence_fold_actions",
)
