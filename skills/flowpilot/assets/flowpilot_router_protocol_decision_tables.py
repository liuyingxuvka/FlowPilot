"""Decision enums, runtime flags, and event identity policies extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *

STARTUP_ANSWER_ENUMS = {
    "background_agents": {"allow", "single-agent"},
    "scheduled_continuation": {"allow", "manual"},
    "display_surface": {"cockpit", "chat"},
}

GATE_DECISION_REQUIRED_FIELDS = (
    "gate_decision_version",
    "gate_id",
    "gate_kind",
    "owner_role",
    "risk_type",
    "gate_strength",
    "decision",
    "blocking",
    "required_evidence",
    "evidence_refs",
    "reason",
    "next_action",
    "contract_self_check",
)

PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS = (
    "reviewed",
    "source_paths",
    "completed_nodes_considered",
    "superseded_nodes_considered",
    "stale_evidence_considered",
    "prior_blocks_or_experiments_considered",
    "impact_on_decision",
    "controller_summary_used_as_evidence",
)

PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS = (
    "controller_only",
    "controller_may_read_sealed_bodies",
    "controller_may_infer_from_chat_history",
    "controller_may_advance_or_close_route",
)

PM_RESUME_DECISION_ALLOWED_VALUES = {
    "continue_current_packet_loop",
    "request_sender_reissue",
    "restore_or_replace_roles_from_memory",
    "create_repair_or_route_mutation_node",
    "stop_for_user_or_environment",
    "close_after_final_ledger_and_terminal_replay",
}

PM_RESUME_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    "explicit_recovery_evidence_recorded",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
    *(f"controller_reminder.{field}" for field in PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS),
)

PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES = {
    "continue",
    "repair_existing_child",
    "add_sibling_child",
    "rebuild_child_subtree",
    "bubble_to_parent",
    "pm_stop",
}

PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS = (
    "decision_owner",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)

PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES = {
    "approve_terminal_closure",
}

PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS = (
    "approved_by_role",
    "decision",
    *(f"prior_path_context_review.{field}" for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS),
)

PM_SUGGESTION_FINAL_DISPOSITIONS = {
    "adopt_now",
    "repair_or_reissue",
    "mutate_route",
    "defer_to_named_node",
    "reject_with_reason",
    "waive_with_authority",
    "stop_for_user",
    "record_for_flowpilot_maintenance",
}

PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION = {
    "adopt_now": {"closed"},
    "repair_or_reissue": {"closed"},
    "mutate_route": {"closed"},
    "defer_to_named_node": {"deferred_to_named_node", "closed"},
    "reject_with_reason": {"closed"},
    "waive_with_authority": {"closed"},
    "stop_for_user": {"stopped_for_user", "closed"},
    "record_for_flowpilot_maintenance": {"closed"},
}

PM_SUGGESTION_WORKER_ROLES = {"worker_a", "worker_b"}

PM_SUGGESTION_OFFICER_ROLES = {"process_flowguard_officer", "product_flowguard_officer"}

SELF_INTERROGATION_SCOPES = {
    "startup",
    "product_architecture",
    "node_entry",
    "repair",
    "completion",
    "role_result",
}

SELF_INTERROGATION_HARD_SEVERITIES = {"hard_blocker", "current_gate_blocker"}

SELF_INTERROGATION_FINAL_DISPOSITIONS = {
    *PM_SUGGESTION_FINAL_DISPOSITIONS,
    "incorporated_into_artifact",
    "entered_pm_suggestion_ledger",
    "no_action_needed",
}

GATE_DECISION_ALLOWED_KINDS = {
    "quality",
    "repair",
    "parent_replay",
    "resource",
    "stage_advance",
    "completion",
    "other",
}

GATE_DECISION_ALLOWED_OWNER_ROLES = {
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
}

GATE_DECISION_ALLOWED_RISKS = {
    "product_state",
    "visual_quality",
    "mixed_product_visual",
    "documentation_only",
    "composition",
    "resource",
    "control_state",
    "none",
}

GATE_DECISION_ALLOWED_STRENGTHS = {
    "hard",
    "soft",
    "advisory",
    "skip_with_reason",
}

GATE_DECISION_ALLOWED_DECISIONS = {
    "pass",
    "block",
    "waive",
    "skip",
    "repair_local",
    "mutate_route",
}

GATE_DECISION_ALLOWED_EVIDENCE_KINDS = {
    "file",
    "command",
    "screenshot",
    "model_result",
    "reviewer_walkthrough",
    "state_ref",
    "none",
}

GATE_DECISION_ALLOWED_NEXT_ACTIONS = {
    "continue",
    "local_repair",
    "route_mutation",
    "collect_evidence",
    "reviewer_recheck",
    "stop",
}

GATE_DECISION_SEMANTIC_OVERREACH_FIELDS = {
    "router_approved_semantic_sufficiency",
    "router_semantic_decision",
    "router_sufficiency_decision",
    "semantic_sufficiency_passed_by_router",
    "controller_approved_gate",
}

CREW_ROLE_KEYS = (
    "project_manager",
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
)

ROLE_CARD_KEYS = ("controller", *CREW_ROLE_KEYS)

RUNTIME_FLAG_DEFAULTS = {
    "resume_state_loaded": False,
    "resume_state_ambiguous": False,
    "resume_roles_restored": False,
    "resume_role_agents_rehydrated": False,
    "crew_rehydration_report_written": False,
    "role_recovery_requested": False,
    "role_recovery_state_loaded": False,
    "role_recovery_roles_restored": False,
    "role_recovery_report_written": False,
    "role_recovery_environment_blocked": False,
    "role_recovery_obligations_scanned": False,
    "role_recovery_obligation_replay_completed": False,
    "role_recovery_pm_escalation_required": False,
    "role_no_output_reissue_recorded": False,
    "role_no_output_pm_escalation_required": False,
    "continuation_binding_recorded": False,
    "controller_boundary_confirmation_written": False,
    "controller_role_confirmed_from_router_core": False,
    "controller_boundary_recovery_requested": False,
    "startup_mechanical_audit_written": False,
    "startup_pending_mail_suspended_after_dead_end": False,
    "startup_display_status_written": False,
    "route_history_index_refreshed": False,
    "pm_prior_path_context_refreshed": False,
    "material_scan_packets_relayed": False,
    "material_scan_results_relayed_to_reviewer": False,
    "material_scan_results_relayed_to_pm": False,
    "material_scan_result_disposition_recorded": False,
    "material_scan_results_absorbed_by_pm": False,
    "research_packet_relayed": False,
    "research_result_relayed_to_reviewer": False,
    "research_result_relayed_to_pm": False,
    "research_result_disposition_recorded": False,
    "research_result_absorbed_for_review_by_pm": False,
    "current_node_packet_relayed": False,
    "current_node_result_relayed_to_reviewer": False,
    "current_node_result_relayed_to_pm": False,
    "current_node_result_disposition_recorded": False,
    "current_node_result_absorbed_by_pm": False,
    "current_node_write_grant_issued": False,
    "node_completion_ledger_updated": False,
    "task_completion_projection_published": False,
    "pm_role_work_request_registered": False,
    "pm_role_work_request_packet_relayed": False,
    "pm_role_work_result_returned": False,
    "pm_role_work_result_relayed_to_pm": False,
    "pm_role_work_result_absorbed": False,
    "model_miss_triage_followup_request_pending": False,
    "model_miss_triage_controlled_stop_recorded": False,
    "terminal_summary_card_delivered": False,
    "terminal_summary_written": False,
    "formal_router_daemon_started": False,
    "router_daemon_start_failed": False,
}

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

__all__ = (
    'STARTUP_ANSWER_ENUMS',
    'GATE_DECISION_REQUIRED_FIELDS',
    'PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS',
    'PM_RESUME_CONTROLLER_REMINDER_REQUIRED_FIELDS',
    'PM_RESUME_DECISION_ALLOWED_VALUES',
    'PM_RESUME_DECISION_REQUIRED_BODY_FIELDS',
    'PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES',
    'PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS',
    'PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES',
    'PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS',
    'PM_SUGGESTION_FINAL_DISPOSITIONS',
    'PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION',
    'PM_SUGGESTION_WORKER_ROLES',
    'PM_SUGGESTION_OFFICER_ROLES',
    'SELF_INTERROGATION_SCOPES',
    'SELF_INTERROGATION_HARD_SEVERITIES',
    'SELF_INTERROGATION_FINAL_DISPOSITIONS',
    'GATE_DECISION_ALLOWED_KINDS',
    'GATE_DECISION_ALLOWED_OWNER_ROLES',
    'GATE_DECISION_ALLOWED_RISKS',
    'GATE_DECISION_ALLOWED_STRENGTHS',
    'GATE_DECISION_ALLOWED_DECISIONS',
    'GATE_DECISION_ALLOWED_EVIDENCE_KINDS',
    'GATE_DECISION_ALLOWED_NEXT_ACTIONS',
    'GATE_DECISION_SEMANTIC_OVERREACH_FIELDS',
    'CREW_ROLE_KEYS',
    'ROLE_CARD_KEYS',
    'RUNTIME_FLAG_DEFAULTS',
    'SAFE_RUN_UNTIL_WAIT_ACTION_TYPES',
    'ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES',
    'ROUTER_INTERNAL_MECHANICAL_MAX_HOPS',
    'ROUTER_READY_PREEMPTION_ACTION_TYPES',
    'CURRENT_NODE_CYCLE_FLAGS',
    'MATERIAL_REPAIR_RECHECK_FLAGS',
    'MODEL_MISS_REVIEW_BLOCK_FLAGS',
    'MODEL_MISS_REVIEW_BLOCK_EVENTS',
    'MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS',
    'MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS',
    'MATERIAL_REPAIR_OUTCOME_EVENTS',
    'CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS',
    'LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS',
    'PARENT_REPAIR_SAFE_EVENTS',
    'PARENT_NODE_EVENT_CAPABILITY_EVENTS',
    'ROUTE_COMPLETION_FLAGS',
    'SCOPED_EVENT_IDENTITY_POLICIES',
)
