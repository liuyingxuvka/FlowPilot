"""Decision-table child declarations for FlowPilot router protocol."""

from __future__ import annotations

from typing import Any

from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_event_capabilities import *

SCOPED_EVENT_IDENTITY_POLICIES: dict[str, dict[str, Any]] = {
    "pm_mutates_route_after_review_block": {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id", "route_version"),
        "retry_group_fields": ("event", "control_blocker_id", "model_miss_block"),
        "max_distinct_keys_per_retry_group": 3,
    },
    PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT: {
        "family": "transaction",
        "dedupe_fields": ("control_blocker_id", "repair_transaction_id"),
        "retry_group_fields": ("event", "control_blocker_id"),
    },
    **{
        event: {
            "family": "control_blocker_repair_outcome",
            "dedupe_fields": ("control_blocker_id", "repair_transaction_id", "outcome"),
            "retry_group_fields": ("event", "control_blocker_id", "repair_transaction_id"),
        }
        for event in (*sorted(CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS), PM_PARENT_PROTOCOL_BLOCKER_EVENT)
    },
    PM_ROLE_WORK_REQUEST_EVENT: {
        "family": "pm_role_work_request",
        "dedupe_fields": ("request_id",),
        "retry_group_fields": ("event", "request_id"),
    },
    ROLE_WORK_RESULT_RETURNED_EVENT: {
        "family": "pm_role_work_result",
        "dedupe_fields": ("request_id", "packet_id", "result_hash"),
        "retry_group_fields": ("event", "request_id"),
    },
    PM_ROLE_WORK_RESULT_DECISION_EVENT: {
        "family": "pm_role_work_result_decision",
        "dedupe_fields": ("request_id", "decision"),
        "retry_group_fields": ("event", "request_id"),
    },
    "pm_records_material_scan_result_disposition": {
        "family": "pm_package_disposition",
        "dedupe_fields": ("batch_id", "packet_ids", "packet_generation_id"),
        "retry_group_fields": ("event", "batch_id", "packet_generation_id"),
        "conflict_fields": ("body_hash",),
    },
    "pm_records_research_result_disposition": {
        "family": "pm_package_disposition",
        "dedupe_fields": ("batch_id", "packet_ids", "packet_generation_id"),
        "retry_group_fields": ("event", "batch_id", "packet_generation_id"),
        "conflict_fields": ("body_hash",),
    },
    "pm_records_current_node_result_disposition": {
        "family": "pm_package_disposition",
        "dedupe_fields": ("batch_id", "packet_ids", "packet_generation_id"),
        "retry_group_fields": ("event", "batch_id", "packet_generation_id"),
        "conflict_fields": ("body_hash",),
    },
    "worker_current_node_result_returned": {
        "family": "current_node_result",
        "dedupe_fields": ("packet_id", "result_hash"),
        "retry_group_fields": ("event", "packet_id"),
    },
    GATE_DECISION_EVENT: {
        "family": "gate",
        "dedupe_fields": ("gate_id", "route_version", "decided_by_role"),
        "retry_group_fields": ("event", "gate_id", "route_version"),
    },
    "pm_requests_startup_repair": {
        "family": "startup_cycle",
        "dedupe_fields": ("startup_review_cycle", "startup_fact_report_hash"),
        "retry_group_fields": ("event", "startup_fact_report_hash"),
    },
    "pm_writes_route_draft": {
        "family": "route_draft",
        "dedupe_fields": ("draft_version", "route_hash"),
        "retry_group_fields": ("event", "route_id"),
    },
    "pm_completes_current_node_from_reviewed_result": {
        "family": "node_completion",
        "dedupe_fields": ("node_id", "packet_id", "result_hash"),
        "retry_group_fields": ("event", "node_id"),
    },
    "pm_completes_parent_node_from_backward_replay": {
        "family": "node_completion",
        "dedupe_fields": ("node_id", "parent_backward_replay_hash", "parent_segment_decision_hash"),
        "retry_group_fields": ("event", "node_id"),
    },
}
