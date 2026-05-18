"""Decision-table child declarations for FlowPilot router protocol."""

from __future__ import annotations

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *

SAFE_RUN_UNTIL_WAIT_ACTION_TYPES = frozenset(
    {
        "load_router",
        "create_run_shell",
        "write_current_pointer",
        "update_run_index",
        "copy_runtime_kit",
        "fill_runtime_placeholders",
        "initialize_mailbox",
        "record_user_request",
        "write_user_intake",
        "start_router_daemon",
        "check_prompt_manifest",
        "sync_display_plan",
    }
)

ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES = frozenset(
    {
        "check_prompt_manifest",
        "check_packet_ledger",
        "write_startup_mechanical_audit",
    }
)

ROUTER_INTERNAL_MECHANICAL_MAX_HOPS = 8

ROUTER_READY_PREEMPTION_ACTION_TYPES = frozenset(
    {
        "await_card_return_event",
        "await_card_bundle_return_event",
        "check_card_return_event",
        "check_card_bundle_return_event",
        "deliver_system_card",
        "deliver_system_card_bundle",
    }
)

CURRENT_NODE_CYCLE_FLAGS = (
    "pm_current_node_card_delivered",
    "pm_node_started_event_delivered",
    "pm_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_written",
    "node_acceptance_plan_revised_by_pm",
    "reviewer_node_acceptance_plan_card_delivered",
    "node_acceptance_plan_reviewer_passed",
    "node_acceptance_plan_review_blocked",
    "current_node_packet_registered",
    "current_node_write_grant_issued",
    "current_node_packet_relayed",
    "current_node_worker_result_returned",
    "current_node_result_relayed_to_pm",
    "current_node_result_disposition_recorded",
    "current_node_result_absorbed_by_pm",
    "reviewer_worker_result_card_delivered",
    "current_node_result_relayed_to_reviewer",
    "node_reviewer_passed_result",
    "node_review_blocked",
    "pm_model_miss_triage_card_delivered",
    "model_miss_triage_closed",
    "pm_review_repair_card_delivered",
    "pm_reviewer_blocked_event_delivered",
    "pm_parent_backward_targets_card_delivered",
    "parent_backward_targets_built",
    "reviewer_parent_backward_replay_card_delivered",
    "parent_backward_replay_passed",
    "pm_parent_segment_decision_card_delivered",
    "parent_segment_decision_recorded",
    "node_completed_by_pm",
    "node_completion_ledger_updated",
)

MATERIAL_REPAIR_RECHECK_FLAGS = (
    "material_scan_dispatch_recheck_blocked",
    "material_scan_dispatch_recheck_protocol_blocked",
)

MODEL_MISS_REVIEW_BLOCK_FLAGS = (
    "node_acceptance_plan_review_blocked",
    "node_review_blocked",
)

MODEL_MISS_REVIEW_BLOCK_EVENTS = (
    "reviewer_blocks_node_acceptance_plan",
    "current_node_reviewer_blocks_result",
)

MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS = (
    "node_acceptance_plan_review_blocked",
    "node_review_blocked",
)

MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS: tuple[str, ...] = ()

MATERIAL_REPAIR_OUTCOME_EVENTS = {
    "router_direct_material_scan_dispatch_recheck_passed",
    "worker_scan_results_returned",
    "router_direct_material_scan_dispatch_recheck_blocked",
    "router_protocol_blocker_material_scan_dispatch_recheck",
}

CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS = {
    PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT,
    PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT,
}

LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS = {
    "pm_registers_current_node_packet",
    "worker_current_node_result_returned",
    "current_node_reviewer_passes_result",
    "current_node_reviewer_blocks_result",
    "pm_completes_current_node_from_reviewed_result",
}

PARENT_REPAIR_SAFE_EVENTS = {
    "pm_builds_parent_backward_targets",
    "reviewer_passes_parent_backward_replay",
    "reviewer_blocks_parent_backward_replay",
    "pm_records_parent_segment_decision",
    "pm_completes_parent_node_from_backward_replay",
    PM_PARENT_PROTOCOL_BLOCKER_EVENT,
}

PARENT_NODE_EVENT_CAPABILITY_EVENTS = PARENT_REPAIR_SAFE_EVENTS

ROUTE_COMPLETION_FLAGS = (
    "pm_evidence_quality_package_card_delivered",
    "evidence_quality_package_written",
    "reviewer_evidence_quality_card_delivered",
    "evidence_quality_reviewer_passed",
    "pm_final_ledger_card_delivered",
    "final_ledger_built_clean",
    "reviewer_final_backward_replay_card_delivered",
    "final_backward_replay_passed",
    "task_completion_projection_published",
    "pm_closure_card_delivered",
    "pm_closure_approved",
)
