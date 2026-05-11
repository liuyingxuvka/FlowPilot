"""Prompt-isolated FlowPilot router.

This module is the new FlowPilot control entrypoint. It is deliberately small:
it reads the current run state, returns one JSON action envelope, and verifies
that every bootloader/controller action was first authorized by the router.

The router is not a project manager. It does not decide whether evidence is
sufficient, whether a route is good, or whether a worker succeeded. It only
decides which system card or packet-delivery gate is currently allowed.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import flowpilot_user_flow_diagram
import card_runtime
import packet_runtime
import role_output_runtime


SCHEMA_VERSION = "flowpilot.router.v1"
BOOTSTRAP_STATE_SCHEMA = "flowpilot.bootstrap_state.v1"
RUN_STATE_SCHEMA = "flowpilot.run_state.v1"
PROMPT_MANIFEST_SCHEMA = "flowpilot.prompt_manifest.v1"
PACKET_LEDGER_SCHEMA = packet_runtime.PACKET_LEDGER_SCHEMA
CARD_LEDGER_SCHEMA = card_runtime.CARD_LEDGER_SCHEMA
RETURN_EVENT_LEDGER_SCHEMA = card_runtime.RETURN_EVENT_LEDGER_SCHEMA
ROLE_IO_PROTOCOL_SCHEMA = "flowpilot.role_io_protocol.v1"
ROLE_IO_PROTOCOL_LEDGER_SCHEMA = "flowpilot.role_io_protocol_ledger.v1"
ROLE_IO_PROTOCOL_INJECTION_RECEIPT_SCHEMA = "flowpilot.role_io_protocol_injection_receipt.v1"
RESUME_EVIDENCE_SCHEMA = "flowpilot.resume_reentry.v1"
ROUTE_HISTORY_INDEX_SCHEMA = "flowpilot.route_history_index.v1"
PM_PRIOR_PATH_CONTEXT_SCHEMA = "flowpilot.pm_prior_path_context.v1"
DISPLAY_PLAN_SCHEMA = "flowpilot.display_plan.v1"
ROUTE_STATE_SNAPSHOT_SCHEMA = "flowpilot.route_state_snapshot.v1"
CONTROL_BLOCKER_SCHEMA = "flowpilot.control_blocker.v1"
CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA = "flowpilot.control_blocker_repair_packet.v1"
REPAIR_TRANSACTION_SCHEMA = "flowpilot.repair_transaction.v1"
REPAIR_TRANSACTION_INDEX_SCHEMA = "flowpilot.repair_transaction_index.v1"
ROLE_OUTPUT_ENVELOPE_SCHEMA = "flowpilot.role_output_envelope.v1"
EVENT_ENVELOPE_SCHEMA = "flowpilot.event_envelope.v1"
LIVE_CARD_CONTEXT_SCHEMA = "flowpilot.live_card_context.v1"
PAYLOAD_CONTRACT_SCHEMA = "flowpilot.payload_contract.v1"
GATE_DECISION_SCHEMA = "flowpilot.gate_decision.v1"
GATE_DECISION_RECORD_SCHEMA = "flowpilot.gate_decision_record.v1"
GATE_DECISION_LEDGER_SCHEMA = "flowpilot.gate_decision_ledger.v1"
PM_SUGGESTION_LEDGER_ENTRY_SCHEMA = "flowpilot.pm_suggestion_item.v1"
PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT = "pm_records_control_blocker_repair_decision"
PM_MODEL_MISS_TRIAGE_DECISION_EVENT = "pm_records_model_miss_triage_decision"
PM_ROLE_WORK_REQUEST_EVENT = "pm_registers_role_work_request"
ROLE_WORK_RESULT_RETURNED_EVENT = "role_work_result_returned"
PM_ROLE_WORK_RESULT_DECISION_EVENT = "pm_records_role_work_result_decision"
GATE_DECISION_EVENT = "role_records_gate_decision"
EVENT_IDEMPOTENCY_LEDGER_SCHEMA = "flowpilot.external_event_idempotency.v1"
DISPLAY_CONFIRMATION_SCHEMA = "flowpilot.user_dialog_display_confirmation.v1"
DISPLAY_SURFACE_RECEIPT_SCHEMA = "flowpilot.display_surface_receipt.v1"
CURRENT_STATUS_SUMMARY_SCHEMA = "flowpilot.current_status_summary.v1"
STARTUP_MECHANICAL_AUDIT_SCHEMA = "flowpilot.startup_mechanical_audit.v1"
ROUTER_OWNED_CHECK_PROOF_SCHEMA = "flowpilot.router_owned_check_proof.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA = "flowpilot.controller_boundary_confirmation.v1"
STARTUP_ANSWER_PROVENANCE = "explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_PROVENANCE = "ai_interpreted_from_explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_SCHEMA = "flowpilot.startup_answer_interpretation.v1"
USER_REQUEST_PROVENANCE = "explicit_user_request"
DISPLAY_CONFIRMATION_PROVENANCE = "controller_user_dialog_render"
DISPLAY_CONFIRMATION_TARGET = "user_dialog"
ROUTER_TRUSTED_PROOF_SOURCES = {"router_computed", "packet_runtime_hash", "host_receipt"}
ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS = {
    EVENT_ENVELOPE_SCHEMA,
    ROLE_OUTPUT_ENVELOPE_SCHEMA,
}
ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES = {
    "event_envelope_only",
    "role_output_envelope_only",
    "packet_envelope_only",
    "result_envelope_only",
    "packet_and_result_envelopes_only",
    "control_event_envelope_only",
}
FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS = {
    "blockers",
    "checks",
    "commands",
    "decision",
    "decision_body",
    "evidence",
    "findings",
    "passed",
    "recommendations",
    "repair_instructions",
    "report_body",
    "result_body",
}
ROLE_AGENT_SPAWN_RESULT = "spawned_fresh_for_task"
ROLE_AGENT_REHYDRATION_RESULT = "rehydrated_from_current_run_memory"
ROLE_AGENT_CONTINUITY_RESULT = "live_agent_continuity_confirmed"
BACKGROUND_ROLE_MODEL_POLICY = "strongest_available"
BACKGROUND_ROLE_REASONING_EFFORT_POLICY = "highest_available"
BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT = "xhigh"
RESUME_ROLE_AGENT_RESULTS = {ROLE_AGENT_REHYDRATION_RESULT, ROLE_AGENT_CONTINUITY_RESULT}
ROLE_AGENT_HOST_LIVENESS_STATUSES = {"active", "completed", "missing", "cancelled", "timeout_unknown", "unknown"}
ROLE_AGENT_BOUNDED_WAIT_RESULTS = {"not_waited", "completed", "timeout_unknown"}
ROLE_AGENT_LIVENESS_DECISIONS = {"confirmed_existing_agent", "spawned_replacement_from_current_run_memory"}
ROLE_AGENT_LIVENESS_PROBE_MODE = "concurrent_batch"
CONTROL_BLOCKER_LANES = {
    "control_plane_reissue",
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES = {
    "pm_repair_decision_required",
    "fatal_protocol_violation",
}
PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES = {
    "request_officer_model_miss_analysis",
    "proceed_with_model_backed_repair",
    "out_of_scope_not_modelable",
    "needs_evidence_before_modeling",
    "stop_for_user",
}
PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES = {
    "proceed_with_model_backed_repair",
    "out_of_scope_not_modelable",
}
PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS = (
    "decided_by_role",
    "decision",
    "defect_or_blocker_id",
    "reviewer_block_source_path",
    "model_miss_scope",
    "flowguard_capability",
    "same_class_findings_reviewed",
    "repair_recommendation_reviewed",
    "selected_next_action",
    "why_repair_may_start",
    "blockers",
    "contract_self_check",
)
MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS = (
    "old_model_miss_reason",
    "bug_class_definition",
    "same_class_findings",
    "coverage_added",
    "candidate_repairs",
    "minimal_sufficient_repair_recommendation",
    "rejected_larger_repairs",
    "rejected_smaller_repairs",
    "post_repair_model_checks_required",
    "residual_blindspots",
    "contract_self_check",
)
PM_ROLE_WORK_REQUEST_INDEX_SCHEMA = "flowpilot.pm_role_work_request_index.v1"
PM_ROLE_WORK_REQUEST_SCHEMA = "flowpilot.pm_role_work_request.v1"
PM_ROLE_WORK_RESULT_DECISION_SCHEMA = "flowpilot.pm_role_work_result_decision.v1"
PARALLEL_PACKET_BATCH_SCHEMA = "flowpilot.parallel_packet_batch.v1"
PARALLEL_PACKET_BATCH_REF_SCHEMA = "flowpilot.parallel_packet_batch_ref.v1"
PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES = {
    "human_like_reviewer",
    "process_flowguard_officer",
    "product_flowguard_officer",
    "worker_a",
    "worker_b",
}
PM_ROLE_WORK_REQUEST_MODES = {"blocking", "advisory"}
PM_ROLE_WORK_REQUEST_KINDS = {
    "model_miss",
    "evidence",
    "review",
    "implementation",
    "research",
    "model_update",
    "model_check",
    "other",
}
PM_ROLE_WORK_OPEN_STATUSES = {
    "open",
    "packet_created",
    "packet_relayed",
    "result_returned",
    "result_relayed_to_pm",
}
PM_ROLE_WORK_TERMINAL_DECISIONS = {"absorbed", "canceled", "superseded"}
PARALLEL_PACKET_BATCH_OPEN_STATUSES = {
    "registered",
    "packets_relayed",
    "results_joined",
    "results_relayed_to_reviewer",
    "results_relayed_to_pm",
    "reviewed",
}
PROCESS_CONTRACT_BINDINGS: dict[str, dict[str, Any]] = {
    "current_node_work": {
        "task_family": "worker.current_node",
        "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
        "packet_type": "work_packet",
        "required_result_next_recipient": "human_like_reviewer",
        "absorbing_role": "human_like_reviewer",
    },
    "pm_role_work_request": {
        "task_family": "pm.role_work_request",
        "contract_id": "flowpilot.output_contract.pm_role_work_result.v1",
        "packet_type": "pm_role_work_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_report": {
        "task_family": "officer.model_report",
        "contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "officer_model_miss_report": {
        "task_family": "officer.model_miss_report",
        "contract_id": "flowpilot.output_contract.flowguard_model_miss_report.v1",
        "packet_type": "officer_request",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "reviewer_result_review": {
        "task_family": "reviewer.review",
        "contract_id": "flowpilot.output_contract.reviewer_review_report.v1",
        "packet_type": "review_request",
        "required_result_next_recipient": "human_like_reviewer",
        "absorbing_role": "human_like_reviewer",
    },
    "material_scan": {
        "task_family": "worker.material_scan",
        "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
        "packet_type": "material_scan",
        "required_result_next_recipient": "human_like_reviewer",
        "absorbing_role": "human_like_reviewer",
    },
    "research": {
        "task_family": "worker.research",
        "contract_id": "flowpilot.output_contract.worker_research_result.v1",
        "packet_type": "research",
        "required_result_next_recipient": "human_like_reviewer",
        "absorbing_role": "human_like_reviewer",
    },
    "control_blocker_repair": {
        "task_family": "pm.control_blocker_repair_decision",
        "contract_id": "flowpilot.output_contract.pm_control_blocker_repair_decision.v1",
        "packet_type": "role_decision",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "resume_decision": {
        "task_family": "pm.resume_decision",
        "contract_id": "flowpilot.output_contract.pm_resume_decision.v1",
        "packet_type": "role_decision",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
}
PM_ROLE_WORK_CONTRACT_PROCESS_KINDS = {
    "flowpilot.output_contract.pm_role_work_result.v1": "pm_role_work_request",
    "flowpilot.output_contract.officer_model_report.v1": "officer_model_report",
    "flowpilot.output_contract.flowguard_model_miss_report.v1": "officer_model_miss_report",
}
PM_ROLE_WORK_FOREIGN_CONTRACT_IDS = {
    "flowpilot.output_contract.worker_current_node_result.v1",
    "flowpilot.output_contract.worker_material_scan_result.v1",
    "flowpilot.output_contract.worker_research_result.v1",
}
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
    "research_packet_relayed": False,
    "research_result_relayed_to_reviewer": False,
    "current_node_packet_relayed": False,
    "current_node_result_relayed_to_reviewer": False,
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
        "write_user_intake",
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

# Material dispatch blockers are now router/control-blocker repair outcomes, not
# PM model-miss reviewer-block repair inputs.
MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS: tuple[str, ...] = ()

MATERIAL_REPAIR_OUTCOME_EVENTS = {
    "router_direct_material_scan_dispatch_recheck_passed",
    "worker_scan_results_returned",
    "router_direct_material_scan_dispatch_recheck_blocked",
    "router_protocol_blocker_material_scan_dispatch_recheck",
}

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

PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS = {
    "pm.prior_path_context",
    "pm.route_skeleton",
    "pm.crew_rehydration_freshness",
    "pm.resume_decision",
    "pm.current_node_loop",
    "pm.node_acceptance_plan",
    "pm.model_miss_triage",
    "pm.review_repair",
    "pm.parent_segment_decision",
    "pm.evidence_quality_package",
    "pm.final_ledger",
    "pm.closure",
}

STARTUP_QUESTIONS = (
    {
        "id": "background_agents",
        "question": "Allow the standard six live background roles, or use single-agent six-role continuity?",
    },
    {
        "id": "scheduled_continuation",
        "question": "Allow scheduled continuation/heartbeat, or use manual resume only?",
    },
    {
        "id": "display_surface",
        "question": "Open FlowPilot Cockpit when startup state is ready, or use chat route signs?",
    },
)

BOOT_ACTIONS: tuple[dict[str, Any], ...] = (
    {
        "action_type": "ask_startup_questions",
        "flag": "startup_questions_asked",
        "label": "startup_questions_asked_from_router",
        "summary": "Ask the three FlowPilot startup questions, atomically record the waiting/stop boundary, and do not continue work in the same assistant turn.",
        "actor": "bootloader",
        "requires_user": True,
        "terminal_for_turn": True,
        "questions": STARTUP_QUESTIONS,
    },
    {
        "action_type": "write_startup_awaiting_answers_state",
        "flag": "startup_state_written_awaiting_answers",
        "label": "startup_state_written_awaiting_answers",
        "summary": "Record that the startup dialog is waiting for explicit user answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "stop_for_startup_answers",
        "flag": "dialog_stopped_for_answers",
        "label": "dialog_stopped_for_startup_answers",
        "summary": "Stop after asking startup questions; no banner, route, agents, heartbeat, or implementation may start.",
        "actor": "bootloader",
        "terminal_for_turn": True,
    },
    {
        "action_type": "record_startup_answers",
        "flag": "startup_answers_recorded",
        "label": "startup_answers_recorded_by_router",
        "summary": "Record the later user reply that explicitly answered all startup questions.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "startup_answers",
    },
    {
        "action_type": "emit_startup_banner",
        "flag": "banner_emitted",
        "label": "startup_banner_emitted_after_answers",
        "summary": "Display the startup banner in the user dialog after explicit answers, then record the confirmed display.",
        "actor": "bootloader",
        "card_id": "startup_banner",
    },
    {
        "action_type": "create_run_shell",
        "flag": "run_shell_created",
        "label": "run_shell_created",
        "summary": "Create a fresh run root under .flowpilot/runs.",
        "actor": "bootloader",
    },
    {
        "action_type": "write_current_pointer",
        "flag": "current_pointer_written",
        "label": "current_pointer_written",
        "summary": "Write .flowpilot/current.json as the active-run pointer.",
        "actor": "bootloader",
    },
    {
        "action_type": "update_run_index",
        "flag": "run_index_updated",
        "label": "run_index_updated",
        "summary": "Register the active run in .flowpilot/index.json.",
        "actor": "bootloader",
    },
    {
        "action_type": "copy_runtime_kit",
        "flag": "runtime_kit_copied",
        "label": "bootstrap_runtime_kit_copied",
        "summary": "Copy the audited runtime kit into the run root without generating new prompt bodies.",
        "actor": "bootloader",
    },
    {
        "action_type": "fill_runtime_placeholders",
        "flag": "placeholders_filled",
        "label": "bootstrap_placeholders_filled",
        "summary": "Fill run id, timestamps, and startup-answer placeholders only.",
        "actor": "bootloader",
    },
    {
        "action_type": "initialize_mailbox",
        "flag": "mailbox_initialized",
        "label": "mailbox_initialized_from_copied_kit",
        "summary": "Create mailbox, prompt-delivery, and packet-ledger state files.",
        "actor": "bootloader",
    },
    {
        "action_type": "record_user_request",
        "flag": "user_request_recorded",
        "label": "user_request_recorded_from_explicit_user_request",
        "summary": "Record the exact current FlowPilot task text from explicit user input before PM receives user_intake.",
        "actor": "bootloader",
        "requires_user": True,
        "requires_payload": "user_request",
    },
    {
        "action_type": "write_user_intake",
        "flag": "user_intake_ready",
        "label": "user_intake_template_filled_from_raw_user_request",
        "summary": "Write the user-intake packet from the router-recorded raw user request and startup answers.",
        "actor": "bootloader",
    },
    {
        "action_type": "start_role_slots",
        "flag": "roles_started",
        "label": "six_roles_started_from_user_answer",
        "summary": "Start the six current-task roles and record same-action role core prompt delivery according to the user's background-agent answer.",
        "actor": "bootloader",
    },
    {
        "action_type": "inject_role_core_prompts",
        "flag": "role_core_prompts_injected",
        "label": "role_core_prompts_injected_from_copied_kit",
        "summary": "Legacy recovery: deliver each role only its role core card from the copied runtime kit when an older bootstrap state still lacks the delivery receipt.",
        "actor": "bootloader",
    },
    {
        "action_type": "load_controller_core",
        "flag": "controller_core_loaded",
        "label": "controller_core_loaded",
        "summary": "End bootloader startup and enter the Controller-led router loop.",
        "actor": "bootloader",
    },
)

SYSTEM_CARD_SEQUENCE: tuple[dict[str, Any], ...] = (
    {
        "flag": "reviewer_startup_fact_check_card_delivered",
        "label": "reviewer_startup_fact_check_card_delivered",
        "card_id": "reviewer.startup_fact_check",
        "requires_all_flags": ["startup_mechanical_audit_written", "startup_display_status_written"],
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_core_delivered",
        "label": "pm_core_card_delivered",
        "card_id": "pm.core",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_output_contract_catalog_delivered",
        "label": "pm_output_contract_catalog_card_delivered",
        "card_id": "pm.output_contract_catalog",
        "requires_flag": "pm_core_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_role_work_request_card_delivered",
        "label": "pm_role_work_request_card_delivered",
        "card_id": "pm.role_work_request",
        "requires_flag": "pm_output_contract_catalog_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_controller_reset_card_delivered",
        "label": "pm_controller_reset_recovery_card_delivered",
        "card_id": "pm.controller_reset_duty",
        "requires_flag": "controller_boundary_recovery_requested",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_phase_map_delivered",
        "label": "pm_phase_map_card_delivered",
        "card_id": "pm.phase_map",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_startup_intake_card_delivered",
        "label": "pm_startup_intake_phase_card_delivered",
        "card_id": "pm.startup_intake",
        "to_role": "project_manager",
    },
    {
        "flag": "controller_resume_card_delivered",
        "label": "controller_resume_reentry_card_delivered",
        "card_id": "controller.resume_reentry",
        "requires_flag": "resume_state_loaded",
        "to_role": "controller",
    },
    {
        "flag": "pm_crew_rehydration_freshness_card_delivered",
        "label": "pm_crew_rehydration_freshness_card_delivered",
        "card_id": "pm.crew_rehydration_freshness",
        "requires_flag": "resume_roles_restored",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_resume_decision_card_delivered",
        "label": "pm_resume_decision_card_delivered",
        "card_id": "pm.resume_decision",
        "requires_flag": "pm_crew_rehydration_freshness_card_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_startup_activation_card_delivered",
        "label": "pm_startup_activation_card_delivered",
        "card_id": "pm.startup_activation",
        "requires_flag": "startup_fact_reported",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_scan_card_delivered",
        "label": "pm_material_scan_card_delivered",
        "card_id": "pm.material_scan",
        "requires_flag": "startup_activation_approved",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_material_sufficiency_card_delivered",
        "label": "reviewer_material_sufficiency_card_delivered",
        "card_id": "reviewer.material_sufficiency",
        "requires_flag": "material_scan_results_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_reviewer_report_event_delivered",
        "label": "pm_reviewer_report_event_card_delivered",
        "card_id": "pm.event.reviewer_report",
        "requires_any_flag": ["material_review_sufficient", "material_review_insufficient"],
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_absorb_or_research_card_delivered",
        "label": "pm_material_absorb_or_research_card_delivered",
        "card_id": "pm.material_absorb_or_research",
        "requires_flag": "pm_reviewer_report_event_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_research_package_card_delivered",
        "label": "pm_research_package_phase_card_delivered",
        "card_id": "pm.research_package",
        "requires_flag": "pm_research_requested",
        "to_role": "project_manager",
    },
    {
        "flag": "worker_research_report_card_delivered",
        "label": "worker_research_report_duty_card_delivered",
        "card_id": "worker.research_report",
        "requires_flag": "research_capability_decision_recorded",
        "to_role": "worker_a",
    },
    {
        "flag": "reviewer_research_check_card_delivered",
        "label": "reviewer_research_direct_source_check_card_delivered",
        "card_id": "reviewer.research_direct_source_check",
        "requires_flag": "research_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_research_absorb_or_mutate_card_delivered",
        "label": "pm_research_absorb_or_mutate_phase_card_delivered",
        "card_id": "pm.research_absorb_or_mutate",
        "requires_flag": "research_review_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_material_understanding_card_delivered",
        "label": "pm_material_understanding_phase_card_delivered",
        "card_id": "pm.material_understanding",
        "requires_flag": "material_accepted_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_worker_result_card_delivered",
        "label": "reviewer_worker_result_review_card_delivered",
        "card_id": "reviewer.worker_result_review",
        "requires_flag": "current_node_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_product_architecture_card_delivered",
        "label": "pm_product_architecture_phase_card_delivered",
        "card_id": "pm.product_architecture",
        "requires_flag": "material_understanding_written_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "product_officer_product_architecture_card_delivered",
        "label": "product_officer_product_architecture_modelability_card_delivered",
        "card_id": "product_officer.product_architecture_modelability",
        "requires_flag": "product_architecture_written_by_pm",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "reviewer_product_architecture_card_delivered",
        "label": "reviewer_product_architecture_challenge_card_delivered",
        "card_id": "reviewer.product_architecture_challenge",
        "requires_flag": "product_architecture_modelability_passed",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "pm_root_contract_card_delivered",
        "label": "pm_root_contract_phase_card_delivered",
        "card_id": "pm.root_contract",
        "requires_flag": "product_architecture_reviewer_passed",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_root_contract_card_delivered",
        "label": "reviewer_root_contract_challenge_card_delivered",
        "card_id": "reviewer.root_contract_challenge",
        "requires_flag": "root_contract_written_by_pm",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "product_officer_root_contract_card_delivered",
        "label": "product_officer_root_contract_modelability_card_delivered",
        "card_id": "product_officer.root_contract_modelability",
        "requires_flag": "root_contract_reviewer_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "pm_dependency_policy_card_delivered",
        "label": "pm_dependency_policy_phase_card_delivered",
        "card_id": "pm.dependency_policy",
        "requires_flag": "root_contract_frozen_by_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_selection_card_delivered",
        "label": "pm_child_skill_selection_phase_card_delivered",
        "card_id": "pm.child_skill_selection",
        "requires_flag": "capabilities_manifest_written",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_child_skill_gate_manifest_card_delivered",
        "label": "pm_child_skill_gate_manifest_phase_card_delivered",
        "card_id": "pm.child_skill_gate_manifest",
        "requires_flag": "pm_child_skill_selection_written",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "label": "reviewer_child_skill_gate_manifest_review_card_delivered",
        "card_id": "reviewer.child_skill_gate_manifest_review",
        "requires_flag": "child_skill_gate_manifest_written",
        "to_role": "human_like_reviewer",
    },
    {
        "flag": "process_officer_child_skill_card_delivered",
        "label": "process_officer_child_skill_conformance_model_card_delivered",
        "card_id": "process_officer.child_skill_conformance_model",
        "requires_flag": "child_skill_manifest_reviewer_passed",
        "to_role": "process_flowguard_officer",
    },
    {
        "flag": "product_officer_child_skill_card_delivered",
        "label": "product_officer_child_skill_product_fit_card_delivered",
        "card_id": "product_officer.child_skill_product_fit",
        "requires_flag": "child_skill_process_officer_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "pm_prior_path_context_card_delivered",
        "label": "pm_prior_path_context_phase_card_delivered",
        "card_id": "pm.prior_path_context",
        "requires_flag": "capability_evidence_synced",
        "to_role": "project_manager",
    },
    {
        "flag": "pm_route_skeleton_card_delivered",
        "label": "pm_route_skeleton_phase_card_delivered",
        "card_id": "pm.route_skeleton",
        "requires_flag": "pm_prior_path_context_card_delivered",
        "to_role": "project_manager",
    },
    {
        "flag": "process_officer_route_check_card_delivered",
        "label": "process_officer_route_process_check_card_delivered",
        "card_id": "process_officer.route_process_check",
        "requires_flag": "route_draft_written_by_pm",
        "to_role": "process_flowguard_officer",
    },
    {
        "flag": "product_officer_route_check_card_delivered",
        "label": "product_officer_route_product_check_card_delivered",
        "card_id": "product_officer.route_product_check",
        "requires_flag": "process_officer_route_check_passed",
        "to_role": "product_flowguard_officer",
    },
    {
        "flag": "reviewer_route_check_card_delivered",
        "label": "reviewer_route_challenge_card_delivered",
        "card_id": "reviewer.route_challenge",
        "requires_flag": "product_officer_route_check_passed",
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

CARD_PHASE_BY_ID = {
    "pm.product_architecture": "product_architecture",
    "product_officer.product_architecture_modelability": "product_architecture",
    "reviewer.product_architecture_challenge": "product_architecture",
    "pm.root_contract": "root_contract",
    "reviewer.root_contract_challenge": "root_contract",
    "product_officer.root_contract_modelability": "root_contract",
    "pm.dependency_policy": "dependency_policy",
    "pm.child_skill_selection": "child_skill_selection",
    "pm.child_skill_gate_manifest": "child_skill_gate_manifest",
    "reviewer.child_skill_gate_manifest_review": "child_skill_gate_manifest",
    "process_officer.child_skill_conformance_model": "child_skill_gate_manifest",
    "product_officer.child_skill_product_fit": "child_skill_gate_manifest",
    "pm.prior_path_context": "prior_path_context",
    "pm.route_skeleton": "route_skeleton",
    "process_officer.route_process_check": "route_skeleton",
    "product_officer.route_product_check": "route_skeleton",
    "reviewer.route_challenge": "route_skeleton",
}

CARD_REQUIRED_SOURCE_PATHS = {
    "reviewer.startup_fact_check": {
        "startup_answers": "startup_answers.json",
        "startup_mechanical_audit": "startup/startup_mechanical_audit.json",
        "startup_mechanical_audit_proof": "startup/startup_mechanical_audit.json.proof.json",
        "display_surface": "display/display_surface.json",
        "continuation_binding": "continuation/continuation_binding.json",
    },
    "pm.product_architecture": {
        "pm_material_understanding": "pm_material_understanding.json",
        "pm_material_understanding_payload": "material/pm_material_understanding_payload.json",
    },
    "product_officer.product_architecture_modelability": {
        "product_function_architecture": "product_function_architecture.json",
    },
    "reviewer.product_architecture_challenge": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "pm.root_contract": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_challenge": "reviews/product_architecture_challenge.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "reviewer.root_contract_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "standard_scenario_pack": "standard_scenario_pack.json",
    },
    "product_officer.root_contract_modelability": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "standard_scenario_pack": "standard_scenario_pack.json",
    },
    "pm.dependency_policy": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "product_function_architecture": "product_function_architecture.json",
    },
    "pm.child_skill_selection": {
        "dependency_policy": "dependency_policy.json",
        "capabilities": "capabilities.json",
    },
    "pm.child_skill_gate_manifest": {
        "capabilities": "capabilities.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "root_acceptance_contract": "root_acceptance_contract.json",
    },
    "reviewer.child_skill_gate_manifest_review": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "process_officer.child_skill_conformance_model": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_gate_manifest_review": "reviews/child_skill_gate_manifest_review.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
    },
    "product_officer.child_skill_product_fit": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_gate_manifest_review": "reviews/child_skill_gate_manifest_review.json",
        "child_skill_conformance_model": "flowguard/child_skill_conformance_model.json",
        "pm_child_skill_selection": "pm_child_skill_selection.json",
        "capabilities": "capabilities.json",
        "root_acceptance_contract": "root_acceptance_contract.json",
    },
    "pm.prior_path_context": {
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_manifest_pm_approval": "child_skill_manifest_pm_approval.json",
        "capability_sync": "capabilities/capability_sync.json",
    },
    "pm.route_skeleton": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "child_skill_manifest_pm_approval": "child_skill_manifest_pm_approval.json",
        "capability_sync": "capabilities/capability_sync.json",
        "pm_prior_path_context": "route_memory/pm_prior_path_context.json",
    },
    "process_officer.route_process_check": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "capability_sync": "capabilities/capability_sync.json",
    },
    "product_officer.route_product_check": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "route_process_check": "flowguard/route_process_check.json",
    },
    "reviewer.route_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "route_process_check": "flowguard/route_process_check.json",
        "route_product_check": "flowguard/route_product_check.json",
    },
}

RUN_TERMINAL_STATUSES = {"stopped_by_user", "cancelled_by_user", "protocol_dead_end", "completed", "closed", "stopped"}

MAIL_SEQUENCE: tuple[dict[str, str], ...] = (
    {
        "flag": "user_intake_delivered_to_pm",
        "label": "user_intake_delivered_to_pm",
        "mail_id": "user_intake",
        "to_role": "project_manager",
    },
)

EXTERNAL_EVENTS: dict[str, dict[str, str]] = {
    "user_requests_run_stop": {
        "flag": "run_stopped_by_user",
        "summary": "The user explicitly stopped the active FlowPilot run; no further route work is authorized.",
    },
    "user_requests_run_cancel": {
        "flag": "run_cancelled_by_user",
        "summary": "The user explicitly cancelled the active FlowPilot run; no further route work is authorized.",
    },
    "pm_first_decision_resets_controller": {
        "flag": "pm_controller_reset_decision_returned",
        "requires_flag": "pm_controller_reset_card_delivered",
        "summary": "Recovery-only PM reminder that Controller is only a relay and status-flow controller.",
    },
    "controller_role_confirmed_from_pm_reset": {
        "flag": "controller_role_confirmed",
        "requires_flag": "pm_controller_reset_decision_returned",
        "summary": "Controller acknowledged a recovery-only PM reset and remains relay-only.",
    },
    "heartbeat_or_manual_resume_requested": {
        "flag": "resume_reentry_requested",
        "summary": "A heartbeat or manual resume wakeup requested router-guided re-entry.",
    },
    "host_records_heartbeat_binding": {
        "flag": "continuation_binding_recorded",
        "summary": "Host recorded the active run heartbeat/manual-resume binding before startup fact review.",
    },
    "pm_resume_recovery_decision_returned": {
        "flag": "pm_resume_recovery_decision_returned",
        "requires_flag": "pm_resume_decision_card_delivered",
        "summary": "PM returned a resume recovery decision after Controller state re-entry.",
    },
    "reviewer_reports_startup_facts": {
        "flag": "startup_fact_reported",
        "requires_flag": "reviewer_startup_fact_check_card_delivered",
        "summary": "Reviewer reported independent startup facts for PM activation.",
    },
    "pm_approves_startup_activation": {
        "flag": "startup_activation_approved",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM approved opening work beyond startup from the reviewer startup fact report.",
    },
    "pm_requests_startup_repair": {
        "flag": "startup_repair_requested",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM returned a targeted startup repair request instead of opening work beyond startup.",
    },
    "pm_declares_startup_protocol_dead_end": {
        "flag": "startup_protocol_dead_end_declared",
        "requires_flag": "pm_startup_activation_card_delivered",
        "summary": "PM declared that the startup block has no legal repair path in the current protocol and stopped the run.",
    },
    "pm_issues_material_and_capability_scan_packets": {
        "flag": "pm_material_packets_issued",
        "requires_flag": "pm_material_scan_card_delivered",
        "summary": "PM issued bounded material/capability scan packets.",
    },
    "pm_registers_current_node_packet": {
        "flag": "current_node_packet_registered",
        "requires_flag": "node_acceptance_plan_reviewer_passed",
        "forbids_active_node_children": True,
        "summary": "PM registered a current-node packet envelope for router direct dispatch.",
    },
    "router_direct_material_scan_dispatch_recheck_passed": {
        "flag": "material_scan_direct_dispatch_recheck_passed",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck passed for material scan packets.",
    },
    "reviewer_allows_material_scan_dispatch": {
        "flag": "reviewer_dispatch_allowed",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch approval event retained for old run records only.",
    },
    "reviewer_blocks_material_scan_dispatch": {
        "flag": "material_scan_dispatch_blocked",
        "requires_flag": "reviewer_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy reviewer dispatch block event retained for old run records only.",
    },
    "router_direct_material_scan_dispatch_recheck_blocked": {
        "flag": "material_scan_dispatch_recheck_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck blocked material scan packets.",
    },
    "router_protocol_blocker_material_scan_dispatch_recheck": {
        "flag": "material_scan_dispatch_recheck_protocol_blocked",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "Router direct-dispatch repair recheck found a protocol blocker.",
    },
    "reviewer_allows_current_node_dispatch": {
        "flag": "current_node_dispatch_allowed",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch approval event retained for old run records only.",
    },
    "worker_scan_packet_bodies_delivered_after_dispatch": {
        "flag": "worker_packets_delivered",
        "requires_flag": "material_scan_packets_relayed",
        "summary": "Worker packet bodies were delivered after router direct dispatch.",
    },
    "worker_scan_results_returned": {
        "flag": "worker_scan_results_returned",
        "requires_flag": "worker_packets_delivered",
        "summary": "Worker scan results returned to reviewer path.",
    },
    "worker_current_node_result_returned": {
        "flag": "current_node_worker_result_returned",
        "requires_flag": "current_node_packet_relayed",
        "summary": "Worker returned a current-node result envelope.",
    },
    "reviewer_reports_material_sufficient": {
        "flag": "material_review_sufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material sufficient.",
    },
    "reviewer_reports_material_insufficient": {
        "flag": "material_review_insufficient",
        "requires_flag": "reviewer_material_sufficiency_card_delivered",
        "summary": "Reviewer reported material insufficient.",
    },
    "pm_accepts_reviewed_material": {
        "flag": "material_accepted_by_pm",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM accepted reviewer-approved material.",
    },
    "pm_requests_research_after_material_insufficient": {
        "flag": "pm_research_requested",
        "requires_flag": "pm_material_absorb_or_research_card_delivered",
        "summary": "PM requested bounded research instead of accepting insufficient material.",
    },
    "pm_writes_research_package": {
        "flag": "research_package_written_by_pm",
        "requires_flag": "pm_research_package_card_delivered",
        "summary": "PM wrote a bounded research package after insufficient material.",
    },
    "research_capability_decision_recorded": {
        "flag": "research_capability_decision_recorded",
        "requires_flag": "research_package_written_by_pm",
        "summary": "PM recorded research source/tool capability and approval boundaries.",
    },
    "worker_research_report_returned": {
        "flag": "worker_research_report_returned",
        "requires_flag": "worker_research_report_card_delivered",
        "summary": "Worker returned a bounded research report.",
    },
    "reviewer_passes_research_direct_source_check": {
        "flag": "research_review_passed",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer passed direct-source or experiment-output research check.",
    },
    "reviewer_blocks_research_direct_source_check": {
        "flag": "research_review_blocked",
        "requires_flag": "reviewer_research_check_card_delivered",
        "summary": "Reviewer blocked direct-source or experiment-output research check.",
    },
    "pm_absorbs_reviewed_research": {
        "flag": "research_result_absorbed_by_pm",
        "requires_flag": "pm_research_absorb_or_mutate_card_delivered",
        "summary": "PM absorbed reviewer-approved research into material understanding.",
    },
    "pm_writes_material_understanding": {
        "flag": "material_understanding_written_by_pm",
        "requires_flag": "pm_material_understanding_card_delivered",
        "summary": "PM wrote material understanding from reviewed material and approved research if required.",
    },
    "pm_writes_product_function_architecture": {
        "flag": "product_architecture_written_by_pm",
        "requires_flag": "pm_product_architecture_card_delivered",
        "summary": "PM wrote the product-function architecture from reviewed material.",
    },
    "reviewer_passes_product_architecture": {
        "flag": "product_architecture_reviewer_passed",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer passed the PM product-function architecture challenge.",
    },
    "reviewer_blocks_product_architecture": {
        "flag": "product_architecture_reviewer_blocked",
        "requires_flag": "reviewer_product_architecture_card_delivered",
        "summary": "Reviewer blocked the PM product-function architecture challenge.",
    },
    "product_officer_passes_product_architecture_modelability": {
        "flag": "product_architecture_modelability_passed",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "summary": "Product FlowGuard Officer passed product architecture modelability.",
    },
    "product_officer_blocks_product_architecture_modelability": {
        "flag": "product_architecture_modelability_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "summary": "Product FlowGuard Officer blocked product architecture modelability.",
    },
    "pm_writes_root_acceptance_contract": {
        "flag": "root_contract_written_by_pm",
        "requires_flag": "pm_root_contract_card_delivered",
        "summary": "PM wrote the root acceptance contract and standard scenario pack draft.",
    },
    "reviewer_passes_root_acceptance_contract": {
        "flag": "root_contract_reviewer_passed",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer passed the root acceptance contract challenge.",
    },
    "reviewer_blocks_root_acceptance_contract": {
        "flag": "root_contract_reviewer_blocked",
        "requires_flag": "reviewer_root_contract_card_delivered",
        "summary": "Reviewer blocked the root acceptance contract challenge.",
    },
    "product_officer_passes_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_passed",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "summary": "Product FlowGuard Officer passed root contract modelability.",
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_blocked",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "summary": "Product FlowGuard Officer blocked root contract modelability.",
    },
    "pm_freezes_root_acceptance_contract": {
        "flag": "root_contract_frozen_by_pm",
        "requires_flag": "root_contract_modelability_passed",
        "summary": "PM froze the reviewed root acceptance contract as the completion floor.",
    },
    "pm_records_dependency_policy": {
        "flag": "dependency_policy_recorded",
        "requires_flag": "pm_dependency_policy_card_delivered",
        "summary": "PM recorded dependency and installation policy.",
    },
    "pm_writes_capabilities_manifest": {
        "flag": "capabilities_manifest_written",
        "requires_flag": "dependency_policy_recorded",
        "summary": "PM wrote route capabilities manifest from product architecture and root contract.",
    },
    "pm_writes_child_skill_selection": {
        "flag": "pm_child_skill_selection_written",
        "requires_flag": "pm_child_skill_selection_card_delivered",
        "summary": "PM wrote child-skill selection from product needs, not raw availability.",
    },
    "pm_writes_child_skill_gate_manifest": {
        "flag": "child_skill_gate_manifest_written",
        "requires_flag": "pm_child_skill_gate_manifest_card_delivered",
        "summary": "PM wrote the child-skill gate manifest.",
    },
    "reviewer_passes_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_passed",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer passed child-skill gate manifest review.",
    },
    "reviewer_blocks_child_skill_gate_manifest": {
        "flag": "child_skill_manifest_reviewer_blocked",
        "requires_flag": "reviewer_child_skill_gate_manifest_card_delivered",
        "summary": "Reviewer blocked child-skill gate manifest review.",
    },
    "process_officer_passes_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_passed",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "summary": "Process FlowGuard Officer passed child-skill conformance model review.",
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_blocked",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "summary": "Process FlowGuard Officer blocked child-skill conformance model review.",
    },
    "product_officer_passes_child_skill_product_fit": {
        "flag": "child_skill_product_officer_passed",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "summary": "Product FlowGuard Officer passed child-skill product fit review.",
    },
    "product_officer_blocks_child_skill_product_fit": {
        "flag": "child_skill_product_officer_blocked",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "summary": "Product FlowGuard Officer blocked child-skill product fit review.",
    },
    "pm_approves_child_skill_manifest_for_route": {
        "flag": "child_skill_manifest_pm_approved_for_route",
        "requires_flag": "child_skill_product_officer_passed",
        "summary": "PM approved the child-skill manifest for route use.",
    },
    "capability_evidence_synced": {
        "flag": "capability_evidence_synced",
        "requires_flag": "child_skill_manifest_pm_approved_for_route",
        "summary": "Capability evidence was synced after PM child-skill approval.",
    },
    "pm_writes_route_draft": {
        "flag": "route_draft_written_by_pm",
        "requires_flag": "pm_route_skeleton_card_delivered",
        "summary": "PM wrote the route draft from the frozen root contract.",
    },
    "process_officer_passes_route_check": {
        "flag": "process_officer_route_check_passed",
        "requires_flag": "process_officer_route_check_card_delivered",
        "summary": "Process FlowGuard Officer passed the route process check.",
    },
    "process_officer_requires_route_repair": {
        "flag": "process_officer_route_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "summary": "Process FlowGuard Officer reported that the route needs PM repair before activation.",
    },
    "process_officer_blocks_route_check": {
        "flag": "process_officer_route_check_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "summary": "Process FlowGuard Officer blocked the route from activation.",
    },
    "product_officer_passes_route_check": {
        "flag": "product_officer_route_check_passed",
        "requires_flag": "product_officer_route_check_card_delivered",
        "summary": "Product FlowGuard Officer passed the route product check.",
    },
    "product_officer_blocks_route_check": {
        "flag": "product_officer_route_check_blocked",
        "requires_flag": "product_officer_route_check_card_delivered",
        "summary": "Product FlowGuard Officer blocked the route product check.",
    },
    "reviewer_passes_route_check": {
        "flag": "reviewer_route_check_passed",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer passed the route challenge.",
    },
    "reviewer_blocks_route_check": {
        "flag": "reviewer_route_check_blocked",
        "requires_flag": "reviewer_route_check_card_delivered",
        "summary": "Reviewer blocked the route challenge.",
    },
    "pm_activates_reviewed_route": {
        "flag": "route_activated_by_pm",
        "requires_flag": "reviewer_route_check_passed",
        "summary": "PM activated route after required officer and reviewer checks.",
    },
    "pm_writes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_written",
        "requires_flag": "pm_node_acceptance_plan_card_delivered",
        "summary": "PM wrote the active node acceptance plan before packet dispatch.",
    },
    "pm_revises_node_acceptance_plan": {
        "flag": "node_acceptance_plan_revised_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM revised the active node acceptance plan as same-node repair after reviewer block.",
    },
    "reviewer_passes_node_acceptance_plan": {
        "flag": "node_acceptance_plan_reviewer_passed",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer passed the active node acceptance plan.",
    },
    "reviewer_blocks_node_acceptance_plan": {
        "flag": "node_acceptance_plan_review_blocked",
        "requires_flag": "reviewer_node_acceptance_plan_card_delivered",
        "summary": "Reviewer blocked the active node acceptance plan before worker packet registration.",
    },
    "reviewer_blocks_current_node_dispatch": {
        "flag": "current_node_dispatch_blocked",
        "requires_flag": "reviewer_current_node_dispatch_card_delivered",
        "legacy": True,
        "summary": "Legacy current-node reviewer dispatch block event retained for old run records only.",
    },
    "current_node_reviewer_blocks_result": {
        "flag": "node_review_blocked",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer blocked current-node result.",
    },
    "current_node_reviewer_passes_result": {
        "flag": "node_reviewer_passed_result",
        "requires_flag": "reviewer_worker_result_card_delivered",
        "summary": "Reviewer passed current-node result.",
    },
    "pm_builds_parent_backward_targets": {
        "flag": "parent_backward_targets_built",
        "requires_flag": "pm_parent_backward_targets_card_delivered",
        "summary": "PM built local parent backward replay targets for the active node.",
    },
    "reviewer_passes_parent_backward_replay": {
        "flag": "parent_backward_replay_passed",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer passed local parent backward replay.",
    },
    "reviewer_blocks_parent_backward_replay": {
        "flag": "parent_backward_replay_blocked",
        "requires_flag": "reviewer_parent_backward_replay_card_delivered",
        "summary": "Reviewer blocked local parent backward replay.",
    },
    "pm_records_parent_segment_decision": {
        "flag": "parent_segment_decision_recorded",
        "requires_flag": "pm_parent_segment_decision_card_delivered",
        "summary": "PM recorded parent segment decision after local backward replay.",
    },
    "pm_mutates_route_after_review_block": {
        "flag": "route_mutated_by_pm",
        "requires_flag": "model_miss_triage_closed",
        "summary": "PM mutated the route and invalidated affected stale evidence after a reviewer block.",
    },
    "pm_records_model_miss_triage_decision": {
        "flag": "model_miss_triage_closed",
        "requires_flag": "pm_model_miss_triage_card_delivered",
        "summary": "PM recorded the model-miss triage decision that precedes normal repair.",
    },
    "pm_registers_role_work_request": {
        "flag": "pm_role_work_request_registered",
        "summary": "PM registered a bounded role-work request through the generic always-available PM channel.",
    },
    "role_work_result_returned": {
        "flag": "pm_role_work_result_returned",
        "summary": "The requested role returned a result envelope for a PM role-work request.",
    },
    "pm_records_role_work_result_decision": {
        "flag": "pm_role_work_result_absorbed",
        "summary": "PM recorded whether a role-work result was absorbed, canceled, or superseded.",
    },
    "pm_records_control_blocker_repair_decision": {
        "flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a repair decision for a router materialized control blocker.",
    },
    "role_records_gate_decision": {
        "flag": "gate_decision_recorded",
        "summary": "A PM, reviewer, or FlowGuard officer recorded a mechanically valid GateDecision.",
    },
    "pm_completes_current_node_from_reviewed_result": {
        "flag": "node_completed_by_pm",
        "requires_flag": "node_reviewer_passed_result",
        "summary": "PM completed current node from reviewed result.",
    },
    "pm_completes_parent_node_from_backward_replay": {
        "flag": "node_completed_by_pm",
        "requires_flag": "parent_segment_decision_recorded",
        "summary": "PM completed a parent/module node after reviewer-passed backward replay and PM segment decision.",
    },
    "pm_records_evidence_quality_package": {
        "flag": "evidence_quality_package_written",
        "requires_flag": "pm_evidence_quality_package_card_delivered",
        "summary": "PM recorded evidence, generated-resource, UI/visual, and quality package ledgers.",
    },
    "reviewer_passes_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_passed",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer passed the evidence quality package before final ledger work.",
    },
    "reviewer_blocks_evidence_quality_package": {
        "flag": "evidence_quality_reviewer_blocked",
        "requires_flag": "reviewer_evidence_quality_card_delivered",
        "summary": "Reviewer blocked the evidence quality package before final ledger work.",
    },
    "pm_records_final_route_wide_ledger_clean": {
        "flag": "final_ledger_built_clean",
        "requires_flag": "pm_final_ledger_card_delivered",
        "summary": "PM built a current-route final ledger with zero unresolved items.",
    },
    "reviewer_final_backward_replay_passed": {
        "flag": "final_backward_replay_passed",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer passed final backward replay.",
    },
    "reviewer_blocks_final_backward_replay": {
        "flag": "final_backward_replay_blocked",
        "requires_flag": "reviewer_final_backward_replay_card_delivered",
        "summary": "Reviewer blocked final backward replay.",
    },
    "pm_approves_terminal_closure": {
        "flag": "pm_closure_approved",
        "requires_flag": "pm_closure_card_delivered",
        "summary": "PM approved terminal closure after clean final ledger and backward replay.",
    },
}


PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS = (
    "product_architecture_written_by_pm",
    "product_architecture_reviewer_passed",
    "product_architecture_modelability_passed",
    "reviewer_product_architecture_card_delivered",
    "product_officer_product_architecture_card_delivered",
    "root_contract_written_by_pm",
    "root_contract_reviewer_passed",
    "root_contract_modelability_passed",
    "root_contract_frozen_by_pm",
    "pm_child_skill_selection_written",
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "route_draft_written_by_pm",
    "process_officer_route_check_passed",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
ROOT_CONTRACT_REPAIR_RESET_FLAGS = (
    "root_contract_written_by_pm",
    "root_contract_reviewer_passed",
    "root_contract_modelability_passed",
    "root_contract_frozen_by_pm",
    "reviewer_root_contract_card_delivered",
    "product_officer_root_contract_card_delivered",
    "pm_child_skill_selection_written",
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "route_draft_written_by_pm",
    "process_officer_route_check_passed",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
CHILD_SKILL_GATE_REPAIR_RESET_FLAGS = (
    "child_skill_gate_manifest_written",
    "child_skill_manifest_reviewer_passed",
    "child_skill_process_officer_passed",
    "child_skill_product_officer_passed",
    "child_skill_manifest_pm_approved_for_route",
    "capability_evidence_synced",
    "reviewer_child_skill_gate_manifest_card_delivered",
    "process_officer_child_skill_card_delivered",
    "product_officer_child_skill_card_delivered",
    "route_draft_written_by_pm",
    "process_officer_route_check_passed",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
ROUTE_GATE_REPAIR_RESET_FLAGS = (
    "route_draft_written_by_pm",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "process_officer_route_check_card_delivered",
    "product_officer_route_check_card_delivered",
    "reviewer_route_check_card_delivered",
    "route_activated_by_pm",
)
RESEARCH_GATE_REPAIR_RESET_FLAGS = (
    "research_package_written_by_pm",
    "research_capability_decision_recorded",
    "research_packet_relayed",
    "research_result_relayed_to_reviewer",
    "worker_research_report_returned",
    "research_review_passed",
    "reviewer_research_check_card_delivered",
    "pm_research_absorb_or_mutate_card_delivered",
    "research_result_absorbed_by_pm",
)
PARENT_BACKWARD_REPAIR_RESET_FLAGS = (
    "parent_backward_targets_built",
    "parent_backward_replay_passed",
    "reviewer_parent_backward_replay_card_delivered",
    "parent_segment_decision_recorded",
    "pm_parent_segment_decision_card_delivered",
)
EVIDENCE_QUALITY_REPAIR_RESET_FLAGS = (
    "evidence_quality_package_written",
    "evidence_quality_reviewer_passed",
    "reviewer_evidence_quality_card_delivered",
    "final_ledger_built_clean",
    "final_backward_replay_passed",
    "reviewer_final_backward_replay_card_delivered",
    "pm_closure_approved",
    "pm_closure_card_delivered",
)
FINAL_BACKWARD_REPAIR_RESET_FLAGS = (
    "final_ledger_built_clean",
    "final_backward_replay_passed",
    "reviewer_final_backward_replay_card_delivered",
    "pm_closure_approved",
    "pm_closure_card_delivered",
)

GATE_OUTCOME_BLOCK_EVENT_SPECS: dict[str, dict[str, Any]] = {
    "reviewer_blocks_research_direct_source_check": {
        "expected_role": "human_like_reviewer",
        "path": "research/research_reviewer_block.json",
        "schema_version": "flowpilot.research_reviewer_block.v1",
        "checked_paths": ("research/research_package.json", "research/worker_research_report.json"),
        "reset_flags": RESEARCH_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_product_architecture": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/product_architecture_challenge_block.json",
        "schema_version": "flowpilot.product_architecture_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_product_architecture_modelability": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/product_architecture_modelability_block.json",
        "schema_version": "flowpilot.product_architecture_modelability_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_root_acceptance_contract": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/root_contract_challenge_block.json",
        "schema_version": "flowpilot.root_contract_block.v1",
        "checked_paths": ("root_acceptance_contract.json", "standard_scenario_pack.json"),
        "reset_flags": ROOT_CONTRACT_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/root_contract_modelability_block.json",
        "schema_version": "flowpilot.root_contract_modelability_block.v1",
        "checked_paths": (
            "root_acceptance_contract.json",
            "standard_scenario_pack.json",
            "reviews/root_contract_challenge.json",
        ),
        "reset_flags": ROOT_CONTRACT_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_child_skill_gate_manifest": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/child_skill_gate_manifest_block.json",
        "schema_version": "flowpilot.child_skill_gate_manifest_block.v1",
        "checked_paths": ("child_skill_gate_manifest.json", "pm_child_skill_selection.json", "capabilities.json"),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "expected_role": "process_flowguard_officer",
        "path": "flowguard/child_skill_conformance_model_block.json",
        "schema_version": "flowpilot.child_skill_conformance_model_block.v1",
        "checked_paths": ("child_skill_gate_manifest.json", "reviews/child_skill_gate_manifest_review.json"),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_child_skill_product_fit": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/child_skill_product_fit_block.json",
        "schema_version": "flowpilot.child_skill_product_fit_block.v1",
        "checked_paths": (
            "child_skill_gate_manifest.json",
            "flowguard/child_skill_conformance_model.json",
            "product_function_architecture.json",
            "root_acceptance_contract.json",
        ),
        "reset_flags": CHILD_SKILL_GATE_REPAIR_RESET_FLAGS,
    },
    "product_officer_blocks_route_check": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/route_product_check_block.json",
        "schema_version": "flowpilot.route_product_check_block.v1",
        "checked_paths": ("__current_route_draft__", "flowguard/product_architecture_modelability.json", "root_acceptance_contract.json", "flowguard/route_process_check.json"),
        "reset_flags": ROUTE_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_route_check": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/route_challenge_block.json",
        "schema_version": "flowpilot.route_review_block.v1",
        "checked_paths": ("__current_route_draft__", "flowguard/route_process_check.json", "flowguard/route_product_check.json"),
        "reset_flags": ROUTE_GATE_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_parent_backward_replay": {
        "expected_role": "human_like_reviewer",
        "path": "__active_node_root__/reviews/parent_backward_replay_block.json",
        "schema_version": "flowpilot.parent_backward_replay_block.v1",
        "checked_paths": ("__parent_backward_targets__", "__active_node_acceptance_plan__"),
        "reset_flags": PARENT_BACKWARD_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_evidence_quality_package": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/evidence_quality_block.json",
        "schema_version": "flowpilot.evidence_quality_block.v1",
        "checked_paths": ("evidence/evidence_ledger.json", "generated_resource_ledger.json", "quality/quality_package.json"),
        "reset_flags": EVIDENCE_QUALITY_REPAIR_RESET_FLAGS,
    },
    "reviewer_blocks_final_backward_replay": {
        "expected_role": "human_like_reviewer",
        "path": "reviews/final_backward_replay_block.json",
        "schema_version": "flowpilot.final_backward_replay_block.v1",
        "checked_paths": ("final_route_wide_gate_ledger.json", "terminal_human_backward_replay_map.json"),
        "reset_flags": FINAL_BACKWARD_REPAIR_RESET_FLAGS,
    },
}
GATE_OUTCOME_BLOCK_EVENTS = frozenset(GATE_OUTCOME_BLOCK_EVENT_SPECS)
GATE_OUTCOME_PASS_CLEAR_FLAGS: dict[str, tuple[str, ...]] = {
    "reviewer_passes_research_direct_source_check": ("research_review_blocked",),
    "reviewer_passes_product_architecture": ("product_architecture_reviewer_blocked",),
    "product_officer_passes_product_architecture_modelability": ("product_architecture_modelability_blocked",),
    "reviewer_passes_root_acceptance_contract": ("root_contract_reviewer_blocked",),
    "product_officer_passes_root_acceptance_contract_modelability": ("root_contract_modelability_blocked",),
    "reviewer_passes_child_skill_gate_manifest": ("child_skill_manifest_reviewer_blocked",),
    "process_officer_passes_child_skill_conformance_model": ("child_skill_process_officer_blocked",),
    "product_officer_passes_child_skill_product_fit": ("child_skill_product_officer_blocked",),
    "process_officer_passes_route_check": ("process_officer_route_repair_required", "process_officer_route_check_blocked"),
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


class RouterError(ValueError):
    """Raised when a router operation violates the state machine."""

    def __init__(self, message: str, *, control_blocker: dict[str, Any] | None = None):
        super().__init__(message)
        self.control_blocker = control_blocker


def _active_model_miss_review_block_flags(run_state: dict[str, Any]) -> tuple[str, ...]:
    flags = run_state.get("flags", {})
    return tuple(flag for flag in MODEL_MISS_REVIEW_BLOCK_FLAGS if flags.get(flag))


def _require_single_active_model_miss_review_block(run_state: dict[str, Any], purpose: str) -> str:
    active_flags = _active_model_miss_review_block_flags(run_state)
    if not active_flags:
        raise RouterError(
            f"{purpose} requires an active model-miss reviewer block state "
            f"({', '.join(MODEL_MISS_REVIEW_BLOCK_FLAGS)})"
        )
    if len(active_flags) != 1:
        raise RouterError(
            f"{purpose} requires exactly one active model-miss reviewer block state; "
            f"active flags: {', '.join(active_flags)}"
        )
    return active_flags[0]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_kit_source() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit"


def legacy_bootstrap_state_path(project_root: Path) -> Path:
    return project_root / ".flowpilot" / "bootstrap" / "startup_state.json"


def run_bootstrap_state_path(run_root: Path) -> Path:
    return run_root / "bootstrap" / "startup_state.json"


def bootstrap_state_path(project_root: Path, state: dict[str, Any] | None = None) -> Path:
    if state and state.get("run_root"):
        return run_bootstrap_state_path(project_root / str(state["run_root"]))
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    if raw:
        return project_root / str(raw)
    raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_root:
        candidate = run_bootstrap_state_path(project_root / str(raw_root))
        if candidate.exists():
            return candidate
    return legacy_bootstrap_state_path(project_root)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RouterError(f"expected JSON object: {path}")
    return payload


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def _without_role_output_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return body


def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _json_sha256(_without_role_output_envelope(raw))


def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(raw, dict):
        return set()
    body = _without_role_output_envelope(raw)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}


def _role_output_hashes(path: Path) -> tuple[str, str | None]:
    raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return raw_hash, _role_output_semantic_hash(path)


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RouterError(f"path is outside project root: {path}") from exc


def _flowpilot_runtime_entrypoint_ref(project_root: Path) -> str:
    runtime_path = Path(__file__).resolve().with_name("flowpilot_runtime.py")
    try:
        return project_relative(project_root, runtime_path)
    except RouterError:
        return str(runtime_path)


def _card_checkin_instruction(
    project_root: Path,
    *,
    envelope_path: str,
    role: str,
    agent_id: str | None,
    card_return_event: str,
    bundle: bool,
) -> dict[str, Any]:
    command_name = "receive-card-bundle" if bundle else "receive-card"
    entrypoint = _flowpilot_runtime_entrypoint_ref(project_root)
    command = [
        "python",
        entrypoint,
        "--root",
        ".",
        command_name,
        "--envelope-path",
        envelope_path,
        "--role",
        role,
        "--agent-id",
        agent_id or "<agent-id>",
    ]
    return {
        "schema_version": "flowpilot.card_checkin_instruction.v1",
        "required": True,
        "command_name": command_name,
        "runtime_entrypoint": entrypoint,
        "run_from": "project_root",
        "command": command,
        "card_return_event": card_return_event,
        "ack_submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "expected_outcome": "runtime writes the read receipt and direct Router ACK envelope",
        "do_not_handwrite_ack": True,
        "do_not_record_as_external_event": True,
        "plain_instruction": (
            f"Run {command_name} from the project root to open this card through the runtime and submit "
            f"{card_return_event} directly to Router. Do not hand-write the ACK, do not give the ACK to "
            "Controller, and do not record it as a normal external event."
        ),
    }


def _direct_router_ack_token_for_card(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    card_id: str,
    to_role: str,
    target_agent_id: str | None,
    card_return_event: str,
    expected_return_path: str,
    expected_receipt_path: str,
    delivery_id: str | None,
    delivery_attempt_id: str | None,
    body_hash: str | None,
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_id": card_id,
        "card_return_event": card_return_event,
        "target_role": to_role,
        "target_agent_id": target_agent_id,
        "delivery_id": delivery_id,
        "delivery_attempt_id": delivery_attempt_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_path": expected_receipt_path,
        "body_hash": body_hash,
    }


def _direct_router_ack_token_for_bundle(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    bundle_id: str,
    role: str,
    target_agent_id: str | None,
    card_return_event: str,
    card_ids: list[str],
    delivery_attempt_ids: list[str],
    expected_return_path: str,
    expected_receipt_paths: list[str],
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card_bundle",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_bundle_id": bundle_id,
        "card_ids": card_ids,
        "delivery_attempt_ids": delivery_attempt_ids,
        "card_return_event": card_return_event,
        "target_role": role,
        "target_agent_id": target_agent_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_paths": expected_receipt_paths,
    }


def _pm_suggestion_ledger_path(run_root: Path) -> Path:
    return run_root / "pm_suggestion_ledger.jsonl"


def _read_pm_suggestion_ledger(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RouterError(f"PM suggestion ledger line {line_number} is not valid JSON") from exc
        if not isinstance(entry, dict):
            raise RouterError(f"PM suggestion ledger line {line_number} must be a JSON object")
        entry.setdefault("_line_number", line_number)
        entries.append(entry)
    return entries


def _pm_suggestion_ledger_status(run_root: Path) -> dict[str, Any]:
    ledger_path = _pm_suggestion_ledger_path(run_root)
    entries = _read_pm_suggestion_ledger(ledger_path)
    issues: list[dict[str, str]] = []

    def add_issue(entry: dict[str, Any], message: str) -> None:
        suggestion_id = str(entry.get("suggestion_id") or f"line-{entry.get('_line_number', '?')}")
        issues.append({"suggestion_id": suggestion_id, "message": message})

    for entry in entries:
        if entry.get("schema_version") != PM_SUGGESTION_LEDGER_ENTRY_SCHEMA:
            add_issue(entry, "schema_version must be flowpilot.pm_suggestion_item.v1")
        source_role = str(entry.get("source_role") or "")
        classification = str(entry.get("classification") or "")
        source_output_ref = entry.get("source_output_ref") if isinstance(entry.get("source_output_ref"), dict) else {}
        authority = entry.get("authority_basis") if isinstance(entry.get("authority_basis"), dict) else {}
        disposition = entry.get("pm_disposition") if isinstance(entry.get("pm_disposition"), dict) else {}
        closure = entry.get("closure") if isinstance(entry.get("closure"), dict) else {}
        status = str(disposition.get("status") or "pending")
        closure_status = str(closure.get("status") or "open")

        if source_output_ref.get("sealed_body_content_copied") is True:
            add_issue(entry, "source_output_ref must not copy sealed body content")
        if status not in PM_SUGGESTION_FINAL_DISPOSITIONS:
            add_issue(entry, "pm_disposition.status must be a final PM disposition")
        elif closure_status not in PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION[status]:
            add_issue(entry, "closure.status must match the PM disposition")
        if status == "defer_to_named_node" and not disposition.get("target_node_or_gate_id"):
            add_issue(entry, "defer_to_named_node requires target_node_or_gate_id")
        if status == "reject_with_reason" and not disposition.get("reason"):
            add_issue(entry, "reject_with_reason requires a PM reason")
        if status == "waive_with_authority" and (
            not disposition.get("reason") or not disposition.get("waiver_authority_role")
        ):
            add_issue(entry, "waive_with_authority requires reason and waiver_authority_role")
        if status == "mutate_route" and (
            not disposition.get("route_version_impact") or not disposition.get("stale_evidence_handling")
        ):
            add_issue(entry, "mutate_route requires route_version_impact and stale_evidence_handling")
        if status == "repair_or_reissue" and (
            not disposition.get("repair_or_reissue_target")
            or disposition.get("same_review_class_recheck_required") is not True
        ):
            add_issue(entry, "repair_or_reissue requires target and same-review-class recheck")
        if classification == "current_gate_blocker":
            if source_role in PM_SUGGESTION_WORKER_ROLES:
                add_issue(entry, "worker-origin suggestions cannot be current_gate_blocker")
            if source_role == "human_like_reviewer" and authority.get("reviewer_minimum_standard_failure") is not True:
                add_issue(entry, "reviewer current_gate_blocker requires reviewer_minimum_standard_failure")
            if source_role in PM_SUGGESTION_OFFICER_ROLES and authority.get("formal_flowguard_model_gate") is not True:
                add_issue(entry, "officer current_gate_blocker requires formal_flowguard_model_gate")
            if closure_status not in {"closed", "stopped_for_user"}:
                add_issue(entry, "current_gate_blocker must be closed or stopped before final closure")
        if closure.get("blocks_current_gate_until_closed") is True and closure_status not in {"closed", "stopped_for_user"}:
            add_issue(entry, "blocking suggestion still blocks the current gate")

    return {
        "path": str(ledger_path),
        "exists": ledger_path.exists(),
        "entry_count": len(entries),
        "issue_count": len(issues),
        "clean": not issues,
        "issues": issues,
    }


def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def _evidence_path_record(project_root: Path, path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {"path": project_relative(project_root, path), "exists": path.exists()}
    if path.exists() and path.is_file():
        record["sha256"] = packet_runtime.sha256_file(path)
    return record


def _router_owned_check_proof_path(audit_path: Path) -> Path:
    return audit_path.with_name(f"{audit_path.name}.proof.json")


def _write_router_owned_check_proof(
    project_root: Path,
    run_root: Path,
    *,
    check_name: str,
    audit_path: Path,
    source_kind: str,
    evidence_paths: list[Path],
    reviewer_replacement_scope: str = "mechanical_only",
) -> dict[str, Any]:
    if source_kind not in ROUTER_TRUSTED_PROOF_SOURCES:
        raise RouterError(f"unsupported router-owned proof source: {source_kind}")
    if not audit_path.exists():
        raise RouterError(f"router-owned proof requires audit file: {audit_path}")
    proof_path = _router_owned_check_proof_path(audit_path)
    proof = {
        "schema_version": ROUTER_OWNED_CHECK_PROOF_SCHEMA,
        "run_id": run_root.name,
        "check_name": check_name,
        "check_owner": "flowpilot_router",
        "source_kind": source_kind,
        "trust_basis": "non_self_attested_recomputed_or_host_bound",
        "self_attested_ai_claims_accepted_as_proof": False,
        "reviewer_replacement_scope": reviewer_replacement_scope,
        "audit_path": project_relative(project_root, audit_path),
        "audit_sha256": packet_runtime.sha256_file(audit_path),
        "evidence_paths": [_evidence_path_record(project_root, path) for path in evidence_paths],
        "created_at": utc_now(),
    }
    write_json(proof_path, proof)
    return {"proof_path": project_relative(project_root, proof_path), "proof": proof}


def _validate_router_owned_check_proof(
    project_root: Path,
    run_root: Path,
    *,
    check_name: str,
    audit_path: Path,
) -> dict[str, Any]:
    proof_path = _router_owned_check_proof_path(audit_path)
    proof = read_json_if_exists(proof_path)
    if proof.get("schema_version") != ROUTER_OWNED_CHECK_PROOF_SCHEMA:
        raise RouterError(f"router-owned proof is missing or has wrong schema: {proof_path}")
    if proof.get("run_id") != run_root.name:
        raise RouterError("router-owned proof run_id mismatch")
    if proof.get("check_name") != check_name:
        raise RouterError("router-owned proof check_name mismatch")
    if proof.get("check_owner") != "flowpilot_router":
        raise RouterError("router-owned proof must be owned by flowpilot_router")
    if proof.get("source_kind") not in ROUTER_TRUSTED_PROOF_SOURCES:
        raise RouterError("router-owned proof has untrusted source_kind")
    if proof.get("self_attested_ai_claims_accepted_as_proof") is not False:
        raise RouterError("router-owned proof cannot accept self-attested AI claims")
    if proof.get("reviewer_replacement_scope") != "mechanical_only":
        raise RouterError("router-owned proof may replace only mechanical reviewer work")
    if proof.get("audit_path") != project_relative(project_root, audit_path):
        raise RouterError("router-owned proof audit_path mismatch")
    if proof.get("audit_sha256") != packet_runtime.sha256_file(audit_path):
        raise RouterError("router-owned proof audit hash is stale")
    return proof


def _load_file_backed_role_payload(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Load a role report/decision body from an envelope-only event payload."""

    if not isinstance(payload, dict):
        raise RouterError("role event payload must be an object")
    path_keys = (
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "memo_path",
        "architecture_path",
        "contract_path",
        "manifest_path",
        "route_path",
        "draft_path",
        "plan_path",
        "package_path",
        "ledger_path",
    )
    hash_keys = (
        "body_hash",
        "report_hash",
        "decision_hash",
        "result_body_hash",
        "memo_hash",
        "architecture_hash",
        "contract_hash",
        "manifest_hash",
        "route_hash",
        "draft_hash",
        "plan_hash",
        "package_hash",
        "ledger_hash",
    )
    body_path_key = next((key for key in path_keys if payload.get(key)), None)
    body_ref = payload.get("body_ref") if isinstance(payload.get("body_ref"), dict) else None
    if not body_path_key and body_ref and body_ref.get("path"):
        body_path_key = str(body_ref.get("path_key") or "body_ref.path")
    if not body_path_key:
        if "path" in payload or "hash" in payload:
            raise RouterError(
                "role event envelope must use body_ref.path/body_ref.hash or a known "
                "body_path/report_path/decision_path/result_body_path path/hash pair"
            )
        raise RouterError("role event requires a file-backed body path")
    body_hash_key = next((key for key in hash_keys if payload.get(key)), None)
    if not body_hash_key and body_ref and body_ref.get("hash"):
        body_hash_key = str(body_ref.get("hash_key") or "body_ref.hash")
    if not body_hash_key:
        raise RouterError("role event requires a body/report/decision hash")
    body_path = (
        body_ref["path"]
        if body_ref and body_ref.get("path") and not payload.get(body_path_key)
        else payload[body_path_key]
    )
    forbidden_controller_visible_body_keys = {
        "blockers",
        "checks",
        "decision",
        "evidence",
        "findings",
        "passed",
        "recommendations",
        "repair_instructions",
        "commands",
        "report_body",
        "decision_body",
        "result_body",
    }
    leaked_keys = sorted(forbidden_controller_visible_body_keys & set(payload))
    if leaked_keys:
        raise RouterError(f"envelope payload leaked role body fields to Controller: {', '.join(leaked_keys)}")
    try:
        runtime_receipt = role_output_runtime.validate_envelope_runtime_receipt(project_root, payload)
    except role_output_runtime.RoleOutputRuntimeError as exc:
        raise RouterError(str(exc)) from exc
    path = resolve_project_path(project_root, str(body_path))
    if not path.exists():
        raise RouterError(f"role body path is missing: {body_path}")
    expected_hash = str(
        body_ref["hash"]
        if body_ref and body_ref.get("hash") and not payload.get(body_hash_key)
        else payload[body_hash_key]
    )
    raw_hash, semantic_hash = _role_output_hashes(path)
    accepted_hashes = {raw_hash}
    accepted_hashes.update(_role_output_semantic_hashes(path))
    if expected_hash not in accepted_hashes:
        raise RouterError("role body hash mismatch")
    loaded = read_json(path)
    replay_hash = semantic_hash or raw_hash
    loaded["_role_output_envelope"] = {
        "body_path": project_relative(project_root, path),
        "body_hash": replay_hash,
        "body_raw_sha256": raw_hash,
        "body_semantic_sha256": semantic_hash,
        "body_path_key": body_path_key,
        "body_hash_key": body_hash_key,
        "controller_visibility": payload.get("controller_visibility") or "role_output_envelope_only",
        "chat_response_body_allowed": False,
    }
    if isinstance(runtime_receipt, dict):
        receipt_ref = payload.get("runtime_receipt_ref") if isinstance(payload.get("runtime_receipt_ref"), dict) else {}
        loaded["_role_output_envelope"]["role_output_runtime_receipt_path"] = (
            receipt_ref.get("path") or payload.get("role_output_runtime_receipt_path")
        )
        loaded["_role_output_envelope"]["role_output_runtime_receipt_hash"] = (
            receipt_ref.get("hash") or payload.get("role_output_runtime_receipt_hash")
        )
        loaded["_role_output_envelope"]["role_output_runtime_validated"] = True
        loaded["_role_output_envelope"]["output_type"] = runtime_receipt.get("output_type")
        loaded["_role_output_envelope"]["output_contract_id"] = runtime_receipt.get("output_contract_id")
    return loaded


def _load_file_backed_role_payload_if_present(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path_keys = {
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "memo_path",
        "architecture_path",
        "contract_path",
        "manifest_path",
        "route_path",
        "draft_path",
        "plan_path",
        "package_path",
        "ledger_path",
    }
    if isinstance(payload, dict) and (
        any(payload.get(key) for key in path_keys)
        or (isinstance(payload.get("body_ref"), dict) and payload["body_ref"].get("path"))
    ):
        return _load_file_backed_role_payload(project_root, payload)
    return payload


def _record_event_envelope_ref_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    ref = payload.get("event_envelope_ref")
    if ref is None:
        return None
    if not isinstance(ref, dict):
        raise RouterError("event_envelope_ref must be an object with path and hash")
    return ref


def _looks_like_record_event_envelope(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    schema = payload.get("schema_version")
    return (
        isinstance(schema, str)
        and schema in ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS
        and bool(payload.get("event") or payload.get("event_name"))
    )


def _currently_allowed_external_events(run_state: dict[str, Any]) -> list[str]:
    pending_action = run_state.get("pending_action")
    if isinstance(pending_action, dict) and pending_action.get("action_type") == "await_role_decision":
        raw_allowed = pending_action.get("allowed_external_events")
        if isinstance(raw_allowed, list) and all(isinstance(item, str) for item in raw_allowed):
            try:
                allowed = _validated_external_event_names(raw_allowed, context="pending role wait")
            except RouterError:
                if (
                    pending_action.get("label") == "controller_waits_for_control_blocker_resolution"
                    and pending_action.get("handling_lane") in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
                ):
                    allowed = [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
                else:
                    allowed = []
            to_role = str(pending_action.get("to_role") or "")
            if "project_manager" in {part.strip() for part in to_role.split(",")} and PM_ROLE_WORK_REQUEST_EVENT not in allowed:
                allowed.append(PM_ROLE_WORK_REQUEST_EVENT)
            return allowed
    groups = _pending_expected_external_event_groups(run_state)
    if groups:
        allowed = [event for event, _meta in groups[0]]
        if any(_event_wait_role(event, meta) == "project_manager" for event, meta in groups[0]):
            allowed.append(PM_ROLE_WORK_REQUEST_EVENT)
        return allowed
    return []


def _record_event_expected_role(event: str, run_state: dict[str, Any]) -> str:
    if event == ROLE_WORK_RESULT_RETURNED_EVENT:
        summary = run_state.get("pm_role_work_requests") if isinstance(run_state.get("pm_role_work_requests"), dict) else {}
        active_to_role = str(summary.get("active_to_role") or "").strip()
        if active_to_role:
            return active_to_role
        return ",".join(sorted(PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES))
    pending_action = run_state.get("pending_action")
    if isinstance(pending_action, dict) and pending_action.get("action_type") == "await_role_decision":
        raw_allowed = pending_action.get("allowed_external_events")
        if isinstance(raw_allowed, list) and event in raw_allowed:
            if (
                pending_action.get("label") == "controller_waits_for_control_blocker_resolution"
                or pending_action.get("blocker_artifact_path")
            ) and event != PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
                meta = EXTERNAL_EVENTS.get(event) or {}
                return _event_wait_role(event, meta)
            to_role = pending_action.get("to_role")
            if isinstance(to_role, str) and to_role:
                return to_role
    meta = EXTERNAL_EVENTS.get(event) or {}
    return _event_wait_role(event, meta)


def _record_event_from_role_matches(event: str, from_role: str, expected_role: str) -> bool:
    if from_role == expected_role:
        return True
    if event.startswith("worker_") and expected_role == "worker_a" and from_role in {"worker_a", "worker_b"}:
        return True
    if "," in expected_role and from_role in {part.strip() for part in expected_role.split(",") if part.strip()}:
        return True
    return False


def _validate_record_event_envelope(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    schema = envelope.get("schema_version")
    if schema not in ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS:
        allowed = ", ".join(sorted(ALLOWED_RECORD_EVENT_ENVELOPE_SCHEMAS))
        raise RouterError(f"event envelope schema_version must be one of: {allowed}")
    envelope_event = envelope.get("event") or envelope.get("event_name")
    if envelope_event != event:
        raise RouterError(f"event envelope event mismatch: expected {event}, got {envelope_event!r}")
    currently_allowed = _currently_allowed_external_events(run_state)
    meta = EXTERNAL_EVENTS.get(event) or {}
    flag = meta.get("flag")
    event_already_recorded = bool(flag and run_state.get("flags", {}).get(flag))
    if event not in currently_allowed and not event_already_recorded:
        allowed_display = ", ".join(currently_allowed) if currently_allowed else "none"
        raise RouterError(f"event envelope is not currently allowed by router wait state: {event}; allowed: {allowed_display}")
    from_role = envelope.get("from_role")
    if not isinstance(from_role, str) or not from_role:
        raise RouterError("event envelope requires from_role")
    expected_role = _record_event_expected_role(event, run_state)
    if not _record_event_from_role_matches(event, from_role, expected_role):
        raise RouterError(f"event envelope from_role mismatch: expected {expected_role}, got {from_role}")
    visibility = envelope.get("controller_visibility")
    if visibility not in ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES:
        allowed = ", ".join(sorted(ALLOWED_RECORD_EVENT_CONTROLLER_VISIBILITIES))
        raise RouterError(f"event envelope controller_visibility must be one of: {allowed}")
    leaked_keys = sorted(FORBIDDEN_RECORD_EVENT_ENVELOPE_BODY_FIELDS & set(envelope))
    if leaked_keys:
        raise RouterError(f"event envelope leaked role body fields to Controller: {', '.join(leaked_keys)}")
    return envelope


def _load_record_event_envelope_ref(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    path: str,
    expected_hash: str,
) -> dict[str, Any]:
    if not path:
        raise RouterError("record-event --envelope-path or event_envelope_ref.path is required")
    if not expected_hash:
        raise RouterError("record-event --envelope-hash or event_envelope_ref.hash is required")
    resolved = resolve_project_path(project_root, path)
    # project_relative is the containment check for absolute paths.
    project_relative(project_root, resolved)
    if not resolved.exists():
        raise RouterError(f"event envelope file is missing: {path}")
    if not resolved.is_file():
        raise RouterError(f"event envelope path is not a file: {path}")
    actual_hash = packet_runtime.sha256_file(resolved)
    if actual_hash != expected_hash:
        raise RouterError("event envelope hash mismatch")
    envelope = read_json(resolved)
    return _validate_record_event_envelope(project_root, run_state, event=event, envelope=envelope)


def _normalize_record_event_payload(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    if envelope_path or envelope_hash:
        return _load_record_event_envelope_ref(
            project_root,
            run_state,
            event=event,
            path=str(envelope_path or ""),
            expected_hash=str(envelope_hash or ""),
        )
    ref = _record_event_envelope_ref_from_payload(payload)
    if ref is not None:
        return _load_record_event_envelope_ref(
            project_root,
            run_state,
            event=event,
            path=str(ref.get("path") or ""),
            expected_hash=str(ref.get("hash") or ""),
        )
    if _looks_like_record_event_envelope(payload):
        return _validate_record_event_envelope(project_root, run_state, event=event, envelope=payload)
    return payload


def _stable_identity_hash(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _event_identity_ledger(run_state: dict[str, Any]) -> dict[str, Any]:
    ledger = run_state.get("external_event_idempotency")
    if not isinstance(ledger, dict):
        ledger = {}
        run_state["external_event_idempotency"] = ledger
    ledger.setdefault("schema_version", EVENT_IDEMPOTENCY_LEDGER_SCHEMA)
    processed = ledger.get("processed")
    if not isinstance(processed, dict):
        processed = {}
        ledger["processed"] = processed
    attempts = ledger.get("attempts")
    if not isinstance(attempts, list):
        attempts = []
        ledger["attempts"] = attempts
    return ledger


def _payload_view_for_event_identity(project_root: Path, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    if event not in SCOPED_EVENT_IDENTITY_POLICIES:
        return payload
    return _load_file_backed_role_payload_if_present(project_root, payload)


def _payload_body_hash(payload_view: dict[str, Any]) -> str:
    envelope = payload_view.get("_role_output_envelope")
    if isinstance(envelope, dict):
        for key in ("body_hash", "body_raw_sha256", "body_semantic_sha256"):
            value = str(envelope.get(key) or "").strip()
            if value:
                return value
    return _stable_identity_hash(payload_view)


def _frontier_for_event_identity(run_root: Path) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return frontier if isinstance(frontier, dict) else {}


def _active_control_blocker_for_identity(run_state: dict[str, Any]) -> dict[str, Any]:
    active = run_state.get("active_control_blocker")
    return active if isinstance(active, dict) else {}


def _route_mutation_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = _frontier_for_event_identity(run_root)
    active = _active_control_blocker_for_identity(run_state)
    active_block_flags = _active_model_miss_review_block_flags(run_state)
    route_id = str(payload_view.get("route_id") or frontier.get("active_route_id") or "route-001")
    raw_route_version = payload_view.get("route_version")
    route_version = str(raw_route_version).strip() if raw_route_version not in (None, "") else ""
    repair_identity = {
        "active_node_id": payload_view.get("active_node_id") or payload_view.get("repair_node_id") or frontier.get("active_node_id"),
        "reason": payload_view.get("reason"),
        "repair_action": payload_view.get("repair_action") or payload_view.get("selected_next_action"),
        "stale_evidence": payload_view.get("stale_evidence") or [],
        "superseded_nodes": payload_view.get("superseded_nodes") or [],
        "body_hash": _payload_body_hash(payload_view),
    }
    return {
        "event": "pm_mutates_route_after_review_block",
        "control_blocker_id": str(
            payload_view.get("control_blocker_id")
            or payload_view.get("blocker_id")
            or active.get("blocker_id")
            or "no-control-blocker"
        ),
        "repair_transaction_id": str(
            payload_view.get("repair_transaction_id")
            or payload_view.get("transaction_id")
            or active.get("repair_transaction_id")
            or "no-repair-transaction"
        ),
        "route_id": route_id,
        "route_version": route_version or f"payload:{_stable_identity_hash(repair_identity)}",
        "model_miss_block": ",".join(active_block_flags) or "no-model-miss-block",
    }


def _control_blocker_repair_decision_identity_scope(payload_view: dict[str, Any], run_state: dict[str, Any]) -> dict[str, str]:
    active = _active_control_blocker_for_identity(run_state)
    blocker_id = str(payload_view.get("blocker_id") or active.get("blocker_id") or "missing-blocker")
    return {
        "event": PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT,
        "control_blocker_id": blocker_id,
        "repair_transaction_id": str(payload_view.get("repair_transaction_id") or f"repair-tx-{blocker_id}"),
    }


def _gate_decision_identity_scope(run_root: Path, payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = _frontier_for_event_identity(run_root)
    return {
        "event": GATE_DECISION_EVENT,
        "gate_id": str(payload_view.get("gate_id") or "missing-gate-id"),
        "route_version": str(payload_view.get("route_version") or frontier.get("route_version") or "no-route-version"),
        "decided_by_role": str(payload_view.get("owner_role") or payload_view.get("decided_by_role") or "unknown-role"),
    }


def _startup_repair_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    fact_report_path = run_root / "startup" / "startup_fact_report.json"
    fact_hash = packet_runtime.sha256_file(fact_report_path) if fact_report_path.exists() else "missing-startup-fact-report"
    return {
        "event": "pm_requests_startup_repair",
        "startup_review_cycle": str(payload_view.get("startup_review_cycle") or int(run_state.get("startup_repair_cycle") or 0) + 1),
        "startup_fact_report_hash": str(payload_view.get("startup_fact_report_hash") or payload_view.get("blocked_report_hash") or fact_hash),
        "decision_hash": _payload_body_hash(payload_view),
    }


def _route_draft_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    route_payload = payload_view.get("route") if isinstance(payload_view.get("route"), dict) else {}
    route_id = str(payload_view.get("route_id") or route_payload.get("route_id") or "route-001")
    route_hash = str(payload_view.get("route_hash") or payload_view.get("draft_hash") or _payload_body_hash(payload_view))
    return {
        "event": "pm_writes_route_draft",
        "route_id": route_id,
        "draft_version": str(payload_view.get("draft_version") or payload_view.get("route_version") or route_payload.get("route_version") or "1"),
        "route_hash": route_hash,
    }


def _current_node_completion_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    frontier = _frontier_for_event_identity(run_root)
    node_id = str(payload_view.get("node_id") or frontier.get("active_node_id") or "missing-node")
    packet_id = str(payload_view.get("packet_id") or frontier.get("active_packet_id") or run_state.get("current_node_packet_id") or "missing-packet")
    result_hash = str(payload_view.get("result_hash") or payload_view.get("result_body_hash") or payload_view.get("body_hash") or "")
    if not result_hash:
        result_hash = _payload_body_hash(payload_view)
    return {
        "event": "pm_completes_current_node_from_reviewed_result",
        "node_id": node_id,
        "packet_id": packet_id,
        "result_hash": result_hash,
    }


def _pm_role_work_request_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return {
        "event": PM_ROLE_WORK_REQUEST_EVENT,
        "request_id": str(payload_view.get("request_id") or "missing-request-id"),
    }


def _role_work_result_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    result_hash = str(
        payload_view.get("result_hash")
        or payload_view.get("result_body_hash")
        or payload_view.get("body_hash")
        or ""
    )
    if not result_hash:
        result_hash = _payload_body_hash(payload_view)
    return {
        "event": ROLE_WORK_RESULT_RETURNED_EVENT,
        "request_id": str(payload_view.get("request_id") or "missing-request-id"),
        "packet_id": str(payload_view.get("packet_id") or "missing-packet-id"),
        "result_hash": result_hash,
    }


def _current_node_result_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    result_hash = str(
        payload_view.get("result_hash")
        or payload_view.get("result_body_hash")
        or payload_view.get("body_hash")
        or ""
    )
    if not result_hash:
        result_hash = _payload_body_hash(payload_view)
    return {
        "event": "worker_current_node_result_returned",
        "packet_id": str(payload_view.get("packet_id") or "missing-packet-id"),
        "result_hash": result_hash,
    }


def _pm_role_work_result_decision_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return {
        "event": PM_ROLE_WORK_RESULT_DECISION_EVENT,
        "request_id": str(payload_view.get("request_id") or "missing-request-id"),
        "decision": str(payload_view.get("decision") or "missing-decision"),
    }


def _scoped_event_identity(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    policy = SCOPED_EVENT_IDENTITY_POLICIES.get(event)
    if not isinstance(policy, dict):
        return None
    payload_view = _payload_view_for_event_identity(project_root, event, payload)
    if event == "pm_mutates_route_after_review_block":
        scope = _route_mutation_identity_scope(run_root, run_state, payload_view)
    elif event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        scope = _control_blocker_repair_decision_identity_scope(payload_view, run_state)
    elif event == GATE_DECISION_EVENT:
        scope = _gate_decision_identity_scope(run_root, payload_view)
    elif event == "pm_requests_startup_repair":
        scope = _startup_repair_identity_scope(run_root, run_state, payload_view)
    elif event == "pm_writes_route_draft":
        scope = _route_draft_identity_scope(payload_view)
    elif event == "pm_completes_current_node_from_reviewed_result":
        scope = _current_node_completion_identity_scope(run_root, run_state, payload_view)
    elif event == PM_ROLE_WORK_REQUEST_EVENT:
        scope = _pm_role_work_request_identity_scope(payload_view)
    elif event == ROLE_WORK_RESULT_RETURNED_EVENT:
        scope = _role_work_result_identity_scope(payload_view)
    elif event == "worker_current_node_result_returned":
        scope = _current_node_result_identity_scope(payload_view)
    elif event == PM_ROLE_WORK_RESULT_DECISION_EVENT:
        scope = _pm_role_work_result_decision_identity_scope(payload_view)
    else:
        return None
    key_fields = tuple(str(field) for field in policy.get("dedupe_fields", ()))
    key_parts = {field: str(scope.get(field) or "") for field in key_fields}
    dedupe_key = f"{event}:{_stable_identity_hash(key_parts)}"
    retry_group_fields = tuple(str(field) for field in policy.get("retry_group_fields", ()))
    retry_group = f"{event}:{_stable_identity_hash({field: str(scope.get(field) or '') for field in retry_group_fields})}"
    return {
        "schema_version": EVENT_IDEMPOTENCY_LEDGER_SCHEMA,
        "event": event,
        "family": policy.get("family"),
        "dedupe_key": dedupe_key,
        "scope": scope,
        "dedupe_fields": list(key_fields),
        "retry_group": retry_group,
        "max_distinct_keys_per_retry_group": policy.get("max_distinct_keys_per_retry_group"),
    }


def _scoped_event_is_recorded(run_state: dict[str, Any], identity: dict[str, Any] | None) -> bool:
    if not identity:
        return False
    ledger = _event_identity_ledger(run_state)
    processed = ledger.get("processed")
    if not isinstance(processed, dict):
        return False
    event_keys = processed.get(str(identity.get("event")))
    return isinstance(event_keys, dict) and str(identity.get("dedupe_key")) in event_keys


def _check_scoped_event_retry_budget(run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    if not identity:
        return
    raw_budget = identity.get("max_distinct_keys_per_retry_group")
    if raw_budget in (None, ""):
        return
    budget = int(raw_budget)
    ledger = _event_identity_ledger(run_state)
    attempts = ledger.get("attempts") if isinstance(ledger.get("attempts"), list) else []
    group = str(identity.get("retry_group") or "")
    key = str(identity.get("dedupe_key") or "")
    distinct_keys = {
        str(item.get("dedupe_key"))
        for item in attempts
        if isinstance(item, dict)
        and item.get("retry_group") == group
        and item.get("dedupe_key")
    }
    if key not in distinct_keys and len(distinct_keys) >= budget:
        raise RouterError(
            f"event {identity.get('event')} exceeded scoped retry budget for this repair group; "
            "PM must record an escalation or protocol dead-end instead of another silent retry"
        )


def _mark_scoped_event_recorded(run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    if not identity:
        return
    ledger = _event_identity_ledger(run_state)
    processed = ledger["processed"]
    event = str(identity["event"])
    key = str(identity["dedupe_key"])
    event_keys = processed.setdefault(event, {})
    record = {
        "dedupe_key": key,
        "event": event,
        "family": identity.get("family"),
        "scope": identity.get("scope"),
        "retry_group": identity.get("retry_group"),
        "recorded_at": utc_now(),
    }
    event_keys[key] = record
    attempts = ledger.setdefault("attempts", [])
    if isinstance(attempts, list) and not any(
        isinstance(item, dict) and item.get("event") == event and item.get("dedupe_key") == key
        for item in attempts
    ):
        attempts.append(record)


def _already_recorded_external_event_result(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
    scoped_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    finalized = _finalize_repair_transaction_outcome(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
    )
    resolved = _resolve_delivered_control_blocker(
        project_root,
        run_root,
        run_state,
        resolved_by_event=event,
        from_already_recorded_event=True,
    )
    if resolved or finalized:
        run_state["pending_action"] = None
        _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_already_recorded_event:{event}")
        _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_already_recorded_event:{event}")
        save_run_state(run_root, run_state)
        result = {
            "ok": True,
            "event": event,
            "already_recorded": True,
            "control_blocker_resolved": bool(resolved),
            "blocker_id": resolved.get("blocker_id") if resolved else None,
            "repair_transaction_finalized": finalized,
        }
        if scoped_identity:
            result["dedupe_key"] = scoped_identity.get("dedupe_key")
            result["idempotency_scope"] = scoped_identity.get("scope")
        return result
    result = {"ok": True, "event": event, "already_recorded": True}
    if scoped_identity:
        result["dedupe_key"] = scoped_identity.get("dedupe_key")
        result["idempotency_scope"] = scoped_identity.get("scope")
    return result


def _role_output_envelope_record(payload: dict[str, Any]) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if isinstance(envelope, dict):
        return {"_role_output_envelope": envelope}
    return {}


def _role_output_snapshot_name(run_root: Path, output_path: Path) -> str:
    try:
        relative = output_path.resolve().relative_to(run_root.resolve()).as_posix()
    except ValueError:
        relative = output_path.name
    return relative.replace("/", "__").replace("\\", "__")


def _role_output_envelope_record_for_mutable_artifact(
    project_root: Path,
    run_root: Path,
    output_path: Path,
    payload: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if not isinstance(envelope, dict):
        return {}
    body_path = envelope.get("body_path")
    if not isinstance(body_path, str):
        return {"_role_output_envelope": envelope}
    source_path = resolve_project_path(project_root, body_path)
    if source_path.resolve() != output_path.resolve():
        return {"_role_output_envelope": envelope}
    snapshot_path = run_root / "role_output_snapshots" / f"{_role_output_snapshot_name(run_root, output_path)}.json"
    write_json(snapshot_path, _without_role_output_envelope(payload))
    raw_hash, semantic_hash = _role_output_hashes(snapshot_path)
    snapshot_envelope = dict(envelope)
    snapshot_envelope.update(
        {
            "body_path": project_relative(project_root, snapshot_path),
            "body_hash": semantic_hash or raw_hash,
            "body_raw_sha256": raw_hash,
            "body_semantic_sha256": semantic_hash,
            "body_snapshot_for_mutable_artifact": project_relative(project_root, output_path),
            "body_snapshot_reason": reason,
        }
    )
    return {"_role_output_envelope": snapshot_envelope}


def new_bootstrap_state(run_id: str | None = None, run_root_rel: str | None = None) -> dict[str, Any]:
    return {
        "schema_version": BOOTSTRAP_STATE_SCHEMA,
        "status": "new",
        "bootstrap_scope": "run_scoped" if run_id and run_root_rel else "legacy",
        "router_loaded": False,
        "startup_state": "none",
        "bootloader_actions": 0,
        "router_action_requests": 0,
        "pending_action": None,
        "startup_answers": None,
        "user_request": None,
        "run_id": run_id,
        "run_root": run_root_rel,
        "flags": {action["flag"]: False for action in BOOT_ACTIONS},
        "history": [],
    }


def _create_startup_bootstrap_state(project_root: Path) -> dict[str, Any]:
    base_run_id = _create_run_id()
    for suffix in range(100):
        run_id = base_run_id if suffix == 0 else f"{base_run_id}-{suffix:02d}"
        run_root = project_root / ".flowpilot" / "runs" / run_id
        if not run_root.exists():
            break
    else:
        raise RouterError(f"could not allocate unique startup run id from {base_run_id}")
    run_root_rel = project_relative(project_root, run_root)
    state = new_bootstrap_state(run_id=run_id, run_root_rel=run_root_rel)
    write_json(
        project_root / ".flowpilot" / "current.json",
        {
            "schema_version": "flowpilot.current.v1",
            "current_run_id": run_id,
            "current_run_root": run_root_rel,
            "status": "startup_bootstrap",
            "startup_bootstrap_path": project_relative(project_root, run_bootstrap_state_path(run_root)),
            "updated_at": utc_now(),
        },
    )
    return state


def _load_existing_bootstrap_state(project_root: Path) -> dict[str, Any] | None:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    candidate: Path | None = project_root / str(raw) if raw else None
    if candidate is None:
        raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
        if raw_root:
            candidate = run_bootstrap_state_path(project_root / str(raw_root))
    if candidate is None or not candidate.exists():
        return None
    state = read_json(candidate)
    if state.get("schema_version") != BOOTSTRAP_STATE_SCHEMA:
        return None
    return state


def load_bootstrap_state(project_root: Path, *, create_if_missing: bool = False, new_invocation: bool = False) -> dict[str, Any]:
    if new_invocation:
        return _create_startup_bootstrap_state(project_root)
    state = _load_existing_bootstrap_state(project_root)
    if state is None:
        if not create_if_missing:
            return new_bootstrap_state()
        state = _create_startup_bootstrap_state(project_root)
    path = bootstrap_state_path(project_root, state)
    if not path.exists():
        return state
    flags = state.setdefault("flags", {})
    for action in BOOT_ACTIONS:
        flags.setdefault(action["flag"], False)
    state.setdefault("history", [])
    state.setdefault("pending_action", None)
    state.setdefault("router_action_requests", 0)
    state.setdefault("bootloader_actions", 0)
    _normalize_startup_question_stop_boundary(state)
    return state


def save_bootstrap_state(project_root: Path, state: dict[str, Any]) -> None:
    write_json(bootstrap_state_path(project_root, state), state)


def active_run_root(project_root: Path, state: dict[str, Any] | None = None) -> Path | None:
    if state and state.get("run_root"):
        return project_root / str(state["run_root"])
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw:
        return project_root / str(raw)
    run_id = current.get("current_run_id") or current.get("active_run_id") or current.get("run_id")
    if run_id:
        return project_root / ".flowpilot" / "runs" / str(run_id)
    return None


def run_state_path(run_root: Path) -> Path:
    return run_root / "router_state.json"


def new_run_state(run_id: str, run_root_rel: str) -> dict[str, Any]:
    return {
        "schema_version": RUN_STATE_SCHEMA,
        "run_id": run_id,
        "run_root": run_root_rel,
        "status": "controller_ready",
        "phase": "startup_intake",
        "holder": "controller",
        "pending_action": None,
        "manifest_check_requests": 0,
        "manifest_checks": 0,
        "ledger_check_requests": 0,
        "ledger_checks": 0,
        "prompt_deliveries": 0,
        "mail_deliveries": 0,
        "control_blockers": [],
        "resolved_control_blockers": [],
        "protocol_blockers": [],
        "gate_decisions": [],
        "active_control_blocker": None,
        "latest_control_blocker_path": None,
        "delivered_cards": [],
        "delivered_mail": [],
        "events": [],
        "flags": {
            "controller_core_loaded": True,
            **RUNTIME_FLAG_DEFAULTS,
            **{entry["flag"]: False for entry in SYSTEM_CARD_SEQUENCE},
            **{entry["flag"]: False for entry in MAIL_SEQUENCE},
            **{entry["flag"]: False for entry in EXTERNAL_EVENTS.values()},
        },
        "history": [],
    }


def load_run_state(project_root: Path, bootstrap_state: dict[str, Any] | None = None) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    run_root = active_run_root(project_root, bootstrap_state)
    if run_root is None:
        return None, None
    path = run_state_path(run_root)
    if not path.exists():
        return None, run_root
    state = read_json(path)
    state.setdefault("flags", {})
    for flag, default in RUNTIME_FLAG_DEFAULTS.items():
        state["flags"].setdefault(flag, default)
    for entry in SYSTEM_CARD_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for entry in MAIL_SEQUENCE:
        state["flags"].setdefault(entry["flag"], False)
    for event in EXTERNAL_EVENTS.values():
        state["flags"].setdefault(event["flag"], False)
    state.setdefault("history", [])
    state.setdefault("pending_action", None)
    state.setdefault("delivered_cards", [])
    state.setdefault("delivered_mail", [])
    state.setdefault("control_blockers", [])
    state.setdefault("resolved_control_blockers", [])
    state.setdefault("protocol_blockers", [])
    state.setdefault("gate_decisions", [])
    state.setdefault("active_control_blocker", None)
    state.setdefault("latest_control_blocker_path", None)
    state.setdefault("events", [])
    return state, run_root


def save_run_state(run_root: Path, state: dict[str, Any]) -> None:
    write_json(run_state_path(run_root), state)


def load_manifest_from_run(run_root: Path) -> dict[str, Any]:
    manifest_path = run_root / "runtime_kit" / "manifest.json"
    if not manifest_path.exists():
        manifest_path = runtime_kit_source() / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise RouterError("invalid prompt manifest schema")
    return manifest


def manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise RouterError("prompt manifest cards must be a list")
    for card in cards:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    raise RouterError(f"card not found in prompt manifest: {card_id}")


def _safe_delivery_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def _card_ledger_path(run_root: Path) -> Path:
    return run_root / "card_ledger.json"


def _return_event_ledger_path(run_root: Path) -> Path:
    return run_root / "return_event_ledger.json"


def _role_io_protocol_ledger_path(run_root: Path) -> Path:
    return run_root / "role_io_protocol_ledger.json"


def _role_io_protocol_receipt_dir(run_root: Path) -> Path:
    return run_root / "runtime_receipts" / "role_io_protocol"


def _role_io_protocol_payload() -> dict[str, Any]:
    return {
        "schema_version": ROLE_IO_PROTOCOL_SCHEMA,
        "name": "FlowPilot role lifecycle I/O protocol",
        "scope": "role_lifecycle_base_capability",
        "ordinary_system_card": False,
        "rules": [
            "act only on router/controller envelopes",
            "open system cards, mail, packets, and bundles through runtime",
            "when a card envelope includes card_checkin_instruction, run its receive-card or receive-card-bundle command instead of hand-writing ACK files",
            "write read receipts after runtime open",
            "write reports, decisions, and results to run-scoped files",
            "submit ACKs and role-output envelopes directly to Router through runtime commands",
            "do not send card/body/report body text back to chat",
            "stop with a protocol blocker on wrong role, hash mismatch, stale run, missing envelope, or missing result target",
        ],
    }


def _role_io_protocol_hash() -> str:
    return _json_sha256(_role_io_protocol_payload())


def _empty_card_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": CARD_LEDGER_SCHEMA,
        "run_id": run_id,
        "deliveries": [],
        "read_receipts": [],
        "ack_envelopes": [],
        "updated_at": utc_now(),
    }


def _empty_return_event_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": RETURN_EVENT_LEDGER_SCHEMA,
        "run_id": run_id,
        "pending_returns": [],
        "completed_returns": [],
        "updated_at": utc_now(),
    }


def _empty_role_io_protocol_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": ROLE_IO_PROTOCOL_LEDGER_SCHEMA,
        "run_id": run_id,
        "protocol": _role_io_protocol_payload(),
        "protocol_hash": _role_io_protocol_hash(),
        "injection_receipts": [],
        "ack_receipts": [],
        "updated_at": utc_now(),
    }


def _read_card_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(_card_ledger_path(run_root)) or _empty_card_ledger(run_id)
    ledger.setdefault("schema_version", CARD_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("deliveries", [])
    ledger.setdefault("read_receipts", [])
    ledger.setdefault("ack_envelopes", [])
    return ledger


def _read_return_event_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(_return_event_ledger_path(run_root)) or _empty_return_event_ledger(run_id)
    ledger.setdefault("schema_version", RETURN_EVENT_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("pending_returns", [])
    ledger.setdefault("completed_returns", [])
    return ledger


def _read_role_io_protocol_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(_role_io_protocol_ledger_path(run_root)) or _empty_role_io_protocol_ledger(run_id)
    ledger.setdefault("schema_version", ROLE_IO_PROTOCOL_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("protocol", _role_io_protocol_payload())
    ledger.setdefault("protocol_hash", _role_io_protocol_hash())
    ledger.setdefault("injection_receipts", [])
    ledger.setdefault("ack_receipts", [])
    return ledger


def _role_io_receipt_lifecycle_phase(record: dict[str, Any], default_phase: str) -> str:
    if record.get("liveness_decision") == "spawned_replacement_from_current_run_memory":
        return "missing_agent_replacement"
    return default_phase


def _append_role_io_protocol_injections(
    project_root: Path,
    run_root: Path,
    run_id: str,
    role_records: list[dict[str, Any]],
    *,
    default_lifecycle_phase: str,
    resume_tick_id: str,
    source_action: str,
) -> list[dict[str, Any]]:
    ledger = _read_role_io_protocol_ledger(run_root, run_id)
    protocol_hash = str(ledger.get("protocol_hash") or _role_io_protocol_hash())
    existing_keys = {
        (
            item.get("role_key"),
            item.get("agent_id"),
            item.get("resume_tick_id"),
            item.get("protocol_hash"),
            item.get("lifecycle_phase"),
        )
        for item in ledger.get("injection_receipts", [])
        if isinstance(item, dict)
    }
    receipts: list[dict[str, Any]] = []
    for record in role_records:
        role = record.get("role_key")
        agent_id = record.get("agent_id")
        if not isinstance(role, str) or not role:
            continue
        if not isinstance(agent_id, str) or not agent_id.strip():
            continue
        lifecycle_phase = _role_io_receipt_lifecycle_phase(record, default_lifecycle_phase)
        key = (role, agent_id.strip(), resume_tick_id, protocol_hash, lifecycle_phase)
        if key in existing_keys:
            continue
        injected_at = utc_now()
        identity_hash = hashlib.sha256(f"{run_id}:{resume_tick_id}:{role}:{agent_id}:{lifecycle_phase}".encode("utf-8")).hexdigest()[:16]
        receipt_id = _safe_delivery_component(f"{role}-{lifecycle_phase}-{identity_hash}-role-io")
        receipt_path = _role_io_protocol_receipt_dir(run_root) / f"{receipt_id}.json"
        receipt = {
            "schema_version": ROLE_IO_PROTOCOL_INJECTION_RECEIPT_SCHEMA,
            "receipt_id": receipt_id,
            "run_id": run_id,
            "resume_tick_id": resume_tick_id,
            "role_key": role,
            "agent_id": agent_id.strip(),
            "protocol_schema_version": ROLE_IO_PROTOCOL_SCHEMA,
            "protocol_hash": protocol_hash,
            "lifecycle_phase": lifecycle_phase,
            "source_action": source_action,
            "injected_by": "host_router",
            "injection_method": "lifecycle_role_io_protocol",
            "ordinary_system_card_delivery": False,
            "card_body_visible_to_controller": False,
            "requires_card_read_receipt_after_envelope": True,
            "return_to_controller_envelope_only": True,
            "injected_at": injected_at,
        }
        receipt["receipt_hash"] = _json_sha256(receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(receipt_path, receipt)
        summary = {
            "receipt_id": receipt_id,
            "receipt_path": project_relative(project_root, receipt_path),
            "receipt_hash": receipt["receipt_hash"],
            "run_id": run_id,
            "resume_tick_id": resume_tick_id,
            "role_key": role,
            "agent_id": agent_id.strip(),
            "protocol_hash": protocol_hash,
            "lifecycle_phase": lifecycle_phase,
            "source_action": source_action,
            "injected_at": injected_at,
        }
        ledger.setdefault("injection_receipts", []).append(summary)
        receipts.append(summary)
        existing_keys.add(key)
    ledger["updated_at"] = utc_now()
    write_json(_role_io_protocol_ledger_path(run_root), ledger)
    return receipts


def _role_io_protocol_receipt_for_agent(
    run_root: Path,
    run_id: str,
    *,
    role: str,
    agent_id: str | None,
    resume_tick_id: str,
) -> dict[str, Any] | None:
    if not isinstance(agent_id, str) or not agent_id.strip():
        return None
    ledger = _read_role_io_protocol_ledger(run_root, run_id)
    protocol_hash = str(ledger.get("protocol_hash") or _role_io_protocol_hash())
    candidates = list(ledger.get("injection_receipts", [])) + list(ledger.get("ack_receipts", []))
    for item in reversed(candidates):
        if not isinstance(item, dict):
            continue
        if item.get("run_id") != run_id:
            continue
        if item.get("role_key") != role or item.get("agent_id") != agent_id:
            continue
        if item.get("resume_tick_id") != resume_tick_id:
            continue
        if item.get("protocol_hash") != protocol_hash:
            continue
        return item
    return None


def _active_agent_id_for_role(run_root: Path, role: str) -> str | None:
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    for slot in slots:
        if isinstance(slot, dict) and slot.get("role_key") == role:
            agent_id = slot.get("agent_id")
            if isinstance(agent_id, str) and agent_id.strip():
                return agent_id.strip()
    return None


def _next_card_delivery_attempt(run_root: Path, run_id: str, card_id: str) -> tuple[str, str]:
    ledger = _read_card_ledger(run_root, run_id)
    deliveries = [
        item
        for item in ledger.get("deliveries", [])
        if isinstance(item, dict) and item.get("card_id") == card_id
    ]
    attempt = len(deliveries) + 1
    safe_card = _safe_delivery_component(card_id)
    delivery_id = f"{safe_card}-delivery-{attempt:03d}"
    return delivery_id, f"{delivery_id}-attempt-001"


def _card_return_event_for_card(card_id: str) -> str:
    if card_id.startswith("controller."):
        return "controller_card_ack"
    if card_id.startswith("pm."):
        return "pm_card_ack"
    if card_id.startswith("reviewer."):
        return "reviewer_card_ack"
    if card_id.startswith("worker."):
        return "worker_card_ack"
    if card_id.startswith("process_officer."):
        return "process_officer_card_ack"
    if card_id.startswith("product_officer."):
        return "product_officer_card_ack"
    return "card_ack"


def _card_bundle_return_event_for_role(role: str) -> str:
    if role == "controller":
        return "controller_card_bundle_ack"
    if role == "project_manager":
        return "pm_card_bundle_ack"
    if role == "human_like_reviewer":
        return "reviewer_card_bundle_ack"
    if role.startswith("worker"):
        return "worker_card_bundle_ack"
    if role == "process_flowguard_officer":
        return "process_officer_card_bundle_ack"
    if role == "product_flowguard_officer":
        return "product_officer_card_bundle_ack"
    return "card_bundle_ack"


CARD_RETURN_EVENT_NAMES = frozenset(
    {
        "controller_card_ack",
        "pm_card_ack",
        "reviewer_card_ack",
        "worker_card_ack",
        "process_officer_card_ack",
        "product_officer_card_ack",
        "card_ack",
        "controller_card_bundle_ack",
        "pm_card_bundle_ack",
        "reviewer_card_bundle_ack",
        "worker_card_bundle_ack",
        "process_officer_card_bundle_ack",
        "product_officer_card_bundle_ack",
        "card_bundle_ack",
    }
)


def _is_card_return_event_name(event: str) -> bool:
    return event in CARD_RETURN_EVENT_NAMES


def _pending_return_records(run_root: Path, run_id: str) -> list[dict[str, Any]]:
    ledger = _read_return_event_ledger(run_root, run_id)
    pending: list[dict[str, Any]] = []
    for item in ledger.get("pending_returns", []):
        if isinstance(item, dict) and item.get("status") in {None, "pending", "awaiting_return", "reminded", "returned", "bundle_ack_incomplete"}:
            pending.append(item)
    return pending


def _pending_card_return_ack_exists(project_root: Path, pending_action: object) -> bool:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") not in {
        "await_card_return_event",
        "await_card_bundle_return_event",
        "deliver_system_card",
        "deliver_system_card_bundle",
    }:
        return False
    raw_path = pending_action.get("expected_return_path")
    return isinstance(raw_path, str) and raw_path and resolve_project_path(project_root, raw_path).exists()


CARD_RETURN_EVENT_BYPASS_EVENTS = {
    "heartbeat_or_manual_resume_requested",
    "host_records_heartbeat_binding",
    "user_requests_run_stop",
    "user_requests_run_cancel",
}


def _pending_card_return_blocker_for_event(run_root: Path, run_id: str, event: str) -> dict[str, Any] | None:
    if event in CARD_RETURN_EVENT_BYPASS_EVENTS:
        return None
    pending_returns = _pending_return_records(run_root, run_id)
    if not pending_returns:
        return None
    return pending_returns[0]


def _committed_card_artifact_extra(
    project_root: Path,
    record: dict[str, Any],
    *,
    relay_allowed_if_ready: bool,
) -> dict[str, Any]:
    envelope_path = str(record.get("card_envelope_path") or "")
    expected_return_path = str(record.get("expected_return_path") or "")
    expected_receipt_path = str(record.get("expected_receipt_path") or "")
    artifact_exists = False
    artifact_hash_verified = False
    if envelope_path:
        resolved = resolve_project_path(project_root, envelope_path)
        artifact_exists = resolved.exists() and resolved.is_file()
        if artifact_exists:
            try:
                envelope = read_json(resolved)
            except Exception:
                envelope = {}
            recorded_hash = str(record.get("card_envelope_hash") or "")
            artifact_hash_verified = bool(recorded_hash) and envelope.get("envelope_hash") == recorded_hash
    artifact_committed = bool(
        artifact_exists
        and artifact_hash_verified
        and expected_return_path
        and expected_receipt_path
    )
    return {
        "resource_lifecycle": "committed_artifact" if artifact_committed else "missing_committed_artifact",
        "artifact_committed": artifact_committed,
        "artifact_exists": artifact_exists,
        "artifact_hash_verified": artifact_hash_verified,
        "ledger_recorded": True,
        "return_wait_recorded": bool(expected_return_path),
        "relay_allowed": bool(relay_allowed_if_ready and artifact_committed),
        "apply_required": False,
    }


def _next_pending_card_return_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    pending_returns = _pending_return_records(run_root, str(run_state["run_id"]))
    if not pending_returns:
        return None
    record = pending_returns[0]
    if record.get("return_kind") == "system_card_bundle":
        expected_return_path = str(record.get("expected_return_path") or "")
        envelope_path = str(record.get("card_bundle_envelope_path") or "")
        committed_extra = _committed_card_bundle_artifact_extra(
            project_root,
            record,
            relay_allowed_if_ready=False,
        )
        current_ack_hash: str | None = None
        if expected_return_path and resolve_project_path(project_root, expected_return_path).exists():
            try:
                current_ack = read_json(resolve_project_path(project_root, expected_return_path))
                current_ack_hash = str(current_ack.get("ack_hash") or card_runtime.stable_json_hash(current_ack))
            except Exception:
                current_ack_hash = None
        ack_is_unchanged_incomplete = bool(
            record.get("status") == "bundle_ack_incomplete"
            and current_ack_hash
            and current_ack_hash == record.get("incomplete_ack_hash")
        )
        if expected_return_path and resolve_project_path(project_root, expected_return_path).exists() and not ack_is_unchanged_incomplete:
            return make_action(
                action_type="check_card_bundle_return_event",
                actor="controller",
                label=f"controller_checks_card_bundle_return_{_safe_delivery_component(str(record.get('card_bundle_id') or 'pending'))}",
                summary=(
                    f"Validate returned {record.get('card_return_event')} from {record.get('target_role')} "
                    "against all bundled runtime card read receipts before Router may continue."
                ),
                allowed_reads=[
                    expected_return_path,
                    envelope_path,
                    *[str(path) for path in record.get("expected_receipt_paths") or []],
                    project_relative(project_root, _card_ledger_path(run_root)),
                    project_relative(project_root, _return_event_ledger_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, _card_ledger_path(run_root)),
                    project_relative(project_root, _return_event_ledger_path(run_root)),
                    project_relative(project_root, run_state_path(run_root)),
                ],
                card_id=(record.get("card_ids") or [""])[0] if isinstance(record.get("card_ids"), list) else None,
                to_role=str(record.get("target_role") or ""),
                extra={
                    "card_return_event": record.get("card_return_event"),
                    "card_bundle_id": record.get("card_bundle_id"),
                    "card_ids": record.get("card_ids") or [],
                    "delivery_attempt_ids": record.get("delivery_attempt_ids") or [],
                    "expected_return_path": expected_return_path,
                    "card_bundle_envelope_path": envelope_path,
                    "expected_receipt_paths": record.get("expected_receipt_paths") or [],
                    "controller_visibility": "ack_envelope_and_receipts_only",
                    "sealed_body_reads_allowed": False,
                    **committed_extra,
                    "apply_required": True,
                },
            )
        status_hint = " after an incomplete bundle ACK" if ack_is_unchanged_incomplete else ""
        committed_extra = _committed_card_bundle_artifact_extra(
            project_root,
            record,
            relay_allowed_if_ready=True,
        )
        return make_action(
            action_type="await_card_bundle_return_event",
            actor="controller",
            label=f"controller_waits_for_card_bundle_return_{_safe_delivery_component(str(record.get('card_bundle_id') or 'pending'))}",
            summary=(
                f"Relay the committed system-card bundle to {record.get('target_role')} if needed, then wait{status_hint} "
                f"for {record.get('card_return_event')} after the role opens every bundled card through runtime."
            ),
            allowed_reads=[
                envelope_path,
                project_relative(project_root, _return_event_ledger_path(run_root)),
                project_relative(project_root, _card_ledger_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, _return_event_ledger_path(run_root)),
                project_relative(project_root, run_state_path(run_root)),
            ],
            card_id=(record.get("card_ids") or [""])[0] if isinstance(record.get("card_ids"), list) else None,
            to_role=str(record.get("target_role") or ""),
            extra={
                "card_return_event": record.get("card_return_event"),
                "card_bundle_id": record.get("card_bundle_id"),
                "card_ids": record.get("card_ids") or [],
                "delivery_attempt_ids": record.get("delivery_attempt_ids") or [],
                "expected_return_path": expected_return_path,
                "card_bundle_envelope_path": envelope_path,
                "expected_receipt_paths": record.get("expected_receipt_paths") or [],
                "bundle_ack_incomplete": ack_is_unchanged_incomplete,
                "missing_card_ids": record.get("missing_card_ids") or [],
                "incomplete_ack_path": record.get("incomplete_ack_path"),
                "incomplete_ack_hash": record.get("incomplete_ack_hash"),
                "waiting_for_role": record.get("target_role"),
                "waiting_for_agent_id": record.get("target_agent_id"),
                "controller_visibility": "pending_return_metadata_only",
                "sealed_body_reads_allowed": False,
                **committed_extra,
                "next_recovery_actions": [
                    "role_uses_open-card-bundle_then_ack-card-bundle",
                    "controller_reminds_role_if_still_live",
                    "router_reissues_bundle_after_resume_or_replacement",
                    "router_records_protocol_blocker_if_bundle_ack_is_invalid",
                ],
            },
        )
    expected_return_path = str(record.get("expected_return_path") or "")
    envelope_path = str(record.get("card_envelope_path") or "")
    committed_extra = _committed_card_artifact_extra(
        project_root,
        record,
        relay_allowed_if_ready=False,
    )
    if expected_return_path and resolve_project_path(project_root, expected_return_path).exists():
        return make_action(
            action_type="check_card_return_event",
            actor="controller",
            label=f"controller_checks_card_return_{_safe_delivery_component(str(record.get('delivery_attempt_id') or 'pending'))}",
            summary=(
                f"Validate returned {record.get('card_return_event')} from {record.get('target_role')} "
                "against runtime card read receipts before Router may continue."
            ),
            allowed_reads=[
                expected_return_path,
                envelope_path,
                str(record.get("expected_receipt_path") or ""),
                project_relative(project_root, _card_ledger_path(run_root)),
                project_relative(project_root, _return_event_ledger_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, _card_ledger_path(run_root)),
                project_relative(project_root, _return_event_ledger_path(run_root)),
                project_relative(project_root, run_state_path(run_root)),
            ],
            to_role=str(record.get("target_role") or ""),
            extra={
                "card_return_event": record.get("card_return_event"),
                "delivery_id": record.get("delivery_id"),
                "delivery_attempt_id": record.get("delivery_attempt_id"),
                "card_id": record.get("card_id"),
                "expected_return_path": expected_return_path,
                "card_envelope_path": envelope_path,
                "expected_receipt_path": record.get("expected_receipt_path"),
                "controller_visibility": "ack_envelope_and_receipts_only",
                "sealed_body_reads_allowed": False,
                **committed_extra,
                "apply_required": True,
            },
        )
    committed_extra = _committed_card_artifact_extra(
        project_root,
        record,
        relay_allowed_if_ready=True,
    )
    return make_action(
        action_type="await_card_return_event",
        actor="controller",
        label=f"controller_waits_for_card_return_{_safe_delivery_component(str(record.get('delivery_attempt_id') or 'pending'))}",
        summary=(
            f"Relay the committed system-card envelope to {record.get('target_role')} if needed, then wait "
            f"for {record.get('card_return_event')} after the role opens the card through runtime."
        ),
        allowed_reads=[
            envelope_path,
            project_relative(project_root, _return_event_ledger_path(run_root)),
            project_relative(project_root, _card_ledger_path(run_root)),
        ],
        allowed_writes=[
            project_relative(project_root, _return_event_ledger_path(run_root)),
            project_relative(project_root, run_state_path(run_root)),
        ],
        to_role=str(record.get("target_role") or ""),
        extra={
            "card_return_event": record.get("card_return_event"),
            "delivery_id": record.get("delivery_id"),
            "delivery_attempt_id": record.get("delivery_attempt_id"),
            "card_id": record.get("card_id"),
            "expected_return_path": expected_return_path,
            "card_envelope_path": envelope_path,
            "expected_receipt_path": record.get("expected_receipt_path"),
            "waiting_for_role": record.get("target_role"),
            "waiting_for_agent_id": record.get("target_agent_id"),
            "controller_visibility": "pending_return_metadata_only",
            "sealed_body_reads_allowed": False,
            **committed_extra,
            "next_recovery_actions": [
                "role_uses_open-card_then_ack-card",
                "controller_reminds_role_if_still_live",
                "router_reissues_envelope_after_resume_or_replacement",
                "router_records_protocol_blocker_if_ack_is_invalid",
            ],
        },
    )


def append_history(state: dict[str, Any], label: str, details: dict[str, Any] | None = None) -> None:
    history = state.setdefault("history", [])
    history.append({"at": utc_now(), "label": label, "details": details or {}})


def make_action(
    *,
    action_type: str,
    actor: str,
    label: str,
    summary: str,
    source: str = "router",
    allowed_reads: list[str] | None = None,
    allowed_writes: list[str] | None = None,
    card_id: str | None = None,
    mail_id: str | None = None,
    to_role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "action_id": f"{label}:{utc_now()}",
        "action_type": action_type,
        "actor": actor,
        "source": source,
        "issued_by": "router",
        "label": label,
        "summary": summary,
        "allowed_reads": allowed_reads or [],
        "allowed_writes": allowed_writes or [],
        "created_at": utc_now(),
    }
    if card_id:
        action["card_id"] = card_id
        action["from"] = "system"
        action["issued_by"] = "router"
        action["delivered_by"] = "controller"
    if mail_id:
        action["mail_id"] = mail_id
        action["delivered_by"] = "controller"
    if to_role:
        action["to_role"] = to_role
    if extra:
        action.update(extra)
    if action_type == "await_role_decision":
        action["allowed_external_events"] = _validated_external_event_names(
            action.get("allowed_external_events"),
            context=f"await_role_decision action {label}",
        )
    action.setdefault("resource_lifecycle", "pending_action")
    action.setdefault("artifact_committed", False)
    action.setdefault("relay_allowed", False)
    action.setdefault("apply_required", True)
    if action.get("requires_user_dialog_display_confirmation") and "payload_template" not in action:
        display_kind = action.get("display_kind")
        display_text_sha256 = action.get("display_text_sha256")
        if isinstance(display_kind, str) and isinstance(display_text_sha256, str):
            action["payload_template"] = {
                "display_confirmation": {
                    "action_type": action_type,
                    "display_kind": display_kind,
                    "display_text_sha256": display_text_sha256,
                    "provenance": DISPLAY_CONFIRMATION_PROVENANCE,
                    "rendered_to": DISPLAY_CONFIRMATION_TARGET,
                }
            }
            action["payload_template_rule"] = (
                "First paste display_text exactly into the user dialog, then apply "
                "the action with this payload_template. Generated files, host UI "
                "updates, and display paths do not satisfy user-dialog display evidence."
            )
    resolved_recipient = str(action.get("to_role") or actor)
    action.setdefault("why_this_role", summary)
    action["next_step_contract"] = {
        "schema_version": "flowpilot.next_step_contract.v1",
        "controller_has_explicit_next": True,
        "action_type": action_type,
        "recipient_role": resolved_recipient,
        "controller_may_infer_next_from_chat": False,
        "controller_may_contact_unlisted_role": False,
        "controller_may_create_project_evidence": False,
        "sealed_body_reads_allowed": bool(action.get("sealed_body_reads_allowed", False)),
        "resource_lifecycle": action.get("resource_lifecycle"),
        "artifact_committed": bool(action.get("artifact_committed", False)),
        "relay_allowed": bool(action.get("relay_allowed", False)),
        "apply_required": bool(action.get("apply_required", True)),
        "allowed_external_events": action.get("allowed_external_events", []),
        "postcondition": action.get("postcondition"),
    }
    return action


def _payload_contract(
    *,
    name: str,
    required_object: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    allowed_values: dict[str, list[Any]] | None = None,
    conditional_required_fields: dict[str, list[str]] | None = None,
    structural_requirements: list[str] | None = None,
    description: str,
    reviewer_check: str | None = None,
) -> dict[str, Any]:
    contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": name,
        "required_object": required_object,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "conditional_required_fields": conditional_required_fields or {},
        "structural_requirements": structural_requirements or [],
        "allowed_values": allowed_values or {},
        "description": description,
        "controller_may_fill_missing_fields": False,
        "on_missing_or_ambiguous_payload": "ask_user_or_return_to_named_role; do_not_guess",
    }
    if reviewer_check:
        contract["reviewer_check"] = reviewer_check
    return contract


def _startup_answers_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="startup_answers_with_optional_ai_interpretation_receipt",
        required_object="payload.startup_answers",
        required_fields=["background_agents", "scheduled_continuation", "display_surface", "provenance"],
        optional_fields=["payload.startup_answer_interpretation"],
        allowed_values={
            "startup_answers.background_agents": sorted(STARTUP_ANSWER_ENUMS["background_agents"]),
            "startup_answers.scheduled_continuation": sorted(STARTUP_ANSWER_ENUMS["scheduled_continuation"]),
            "startup_answers.display_surface": sorted(STARTUP_ANSWER_ENUMS["display_surface"]),
            "startup_answers.provenance": [
                STARTUP_ANSWER_PROVENANCE,
                STARTUP_ANSWER_INTERPRETATION_PROVENANCE,
            ],
            "startup_answer_interpretation.schema_version": [STARTUP_ANSWER_INTERPRETATION_SCHEMA],
            "startup_answer_interpretation.interpreted_by": ["controller", "bootloader"],
            "startup_answer_interpretation.interpretation_provenance": [STARTUP_ANSWER_INTERPRETATION_PROVENANCE],
            "startup_answer_interpretation.ambiguity_status": ["none"],
            "startup_answer_interpretation.interpreted_answers.background_agents": sorted(
                STARTUP_ANSWER_ENUMS["background_agents"]
            ),
            "startup_answer_interpretation.interpreted_answers.scheduled_continuation": sorted(
                STARTUP_ANSWER_ENUMS["scheduled_continuation"]
            ),
            "startup_answer_interpretation.interpreted_answers.display_surface": sorted(
                STARTUP_ANSWER_ENUMS["display_surface"]
            ),
        },
        conditional_required_fields={
            "when startup_answers.provenance=ai_interpreted_from_explicit_user_reply": [
                "startup_answer_interpretation.schema_version",
                "startup_answer_interpretation.raw_user_reply_text",
                "startup_answer_interpretation.interpreted_by",
                "startup_answer_interpretation.interpretation_provenance",
                "startup_answer_interpretation.ambiguity_status",
                "startup_answer_interpretation.interpreted_answers.background_agents",
                "startup_answer_interpretation.interpreted_answers.scheduled_continuation",
                "startup_answer_interpretation.interpreted_answers.display_surface",
            ],
        },
        description=(
            "Pass canonical enum answers. If the user's reply was natural language, the AI may interpret it into "
            "these fields only with a startup_answer_interpretation receipt that preserves the raw user reply and "
            "states ambiguity_status=none."
        ),
    )


def _display_surface_receipt_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="display_surface_receipt",
        required_object="payload.display_confirmation",
        required_fields=[
            "display_confirmation.action_type",
            "display_confirmation.display_kind",
            "display_confirmation.display_text_sha256",
            "display_confirmation.provenance",
            "display_confirmation.rendered_to",
        ],
        optional_fields=["payload.display_surface_receipt"],
        allowed_values={
            "display_confirmation.provenance": [DISPLAY_CONFIRMATION_PROVENANCE],
            "display_confirmation.rendered_to": [DISPLAY_CONFIRMATION_TARGET],
            "display_surface_receipt.schema_version": [DISPLAY_SURFACE_RECEIPT_SCHEMA],
            "display_surface_receipt.actual_surface": ["chat_route_sign", "chat_route_sign_fallback", "cockpit"],
            "display_surface_receipt.host_display_surface_verified": [True],
        },
        conditional_required_fields={
            "when payload.display_surface_receipt is supplied": [
                "display_surface_receipt.schema_version",
                "display_surface_receipt.actual_surface",
            ],
            "when display_surface_receipt.actual_surface=cockpit": [
                "display_surface_receipt.host_display_surface_verified",
            ],
        },
        description=(
            "Confirm the router-provided route sign was displayed in the user dialog. If a native Cockpit or "
            "fallback display was attempted, include display_surface_receipt with the actual surface and host result."
        ),
        reviewer_check="Reviewer checks requested cockpit versus actual cockpit/fallback reality when Cockpit was requested.",
    )


def _role_slots_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="role_slots_startup_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "role_agents[].role_key",
            "role_agents[].agent_id",
            "role_agents[].model_policy",
            "role_agents[].reasoning_effort_policy",
            "role_agents[].spawn_result",
            "role_agents[].spawned_for_run_id",
            "role_agents[].spawned_after_startup_answers",
        ],
        optional_fields=["role_agents[].host_spawn_receipt"],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "role_agents[].model_policy": [BACKGROUND_ROLE_MODEL_POLICY],
            "role_agents[].reasoning_effort_policy": [BACKGROUND_ROLE_REASONING_EFFORT_POLICY],
            "role_agents[].spawn_result": [ROLE_AGENT_SPAWN_RESULT],
            "role_agents[].host_spawn_receipt.source_kind": ["host_receipt"],
        },
        conditional_required_fields={
            "when role_agents[].host_spawn_receipt is supplied": [
                "role_agents[].host_spawn_receipt.source_kind",
                "role_agents[].host_spawn_receipt.spawned_for_run_id",
                "role_agents[].host_spawn_receipt.role_key",
                "role_agents[].host_spawn_receipt.agent_id",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate role agent record for each FlowPilot role key.",
            "Each live role agent must be explicitly requested with the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
        ],
        description="Record one fresh live host role agent per FlowPilot role when background agents were allowed, using the strongest available background role intelligence policy.",
        reviewer_check="Reviewer checks live agent spawn freshness unless each slot carries a host receipt.",
    )


def _heartbeat_payload_contract(run_id: str, automation_id_hint: str) -> dict[str, Any]:
    return _payload_contract(
        name="heartbeat_host_automation_receipt",
        required_object="payload",
        required_fields=[
            "route_heartbeat_interval_minutes",
            "host_automation_id",
            "host_automation_verified",
            "host_automation_proof.source_kind",
            "host_automation_proof.run_id",
            "host_automation_proof.host_automation_id",
            "host_automation_proof.route_heartbeat_interval_minutes",
            "host_automation_proof.heartbeat_bound_to_current_run",
        ],
        allowed_values={
            "route_heartbeat_interval_minutes": [1],
            "host_automation_verified": [True],
            "host_automation_proof.source_kind": ["host_receipt"],
            "host_automation_proof.run_id": [run_id],
            "host_automation_proof.route_heartbeat_interval_minutes": [1],
            "host_automation_proof.heartbeat_bound_to_current_run": [True],
        },
        description="Bind the one-minute host heartbeat automation to this exact current run before startup fact review.",
        reviewer_check="Reviewer checks heartbeat host binding when scheduled continuation was requested.",
    )


def _resume_role_rehydration_payload_contract(
    run_state: dict[str, Any],
    contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    del contexts
    return _payload_contract(
        name="resume_role_rehydration_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "liveness_probe_batch_id",
            "liveness_probe_mode",
            "all_liveness_probes_started_before_wait",
            "rehydrated_role_agents[].role_key",
            "rehydrated_role_agents[].agent_id",
            "rehydrated_role_agents[].model_policy",
            "rehydrated_role_agents[].reasoning_effort_policy",
            "rehydrated_role_agents[].rehydration_result",
            "rehydrated_role_agents[].rehydrated_for_run_id",
            "rehydrated_role_agents[].rehydrated_after_resume_tick_id",
            "rehydrated_role_agents[].rehydrated_after_resume_state_loaded",
            "rehydrated_role_agents[].core_prompt_path",
            "rehydrated_role_agents[].core_prompt_hash",
            "rehydrated_role_agents[].host_liveness_status",
            "rehydrated_role_agents[].liveness_decision",
            "rehydrated_role_agents[].resume_agent_attempted",
            "rehydrated_role_agents[].bounded_wait_result",
            "rehydrated_role_agents[].bounded_wait_ms",
            "rehydrated_role_agents[].liveness_probe_batch_id",
            "rehydrated_role_agents[].liveness_probe_mode",
            "rehydrated_role_agents[].liveness_probe_started_at",
            "rehydrated_role_agents[].liveness_probe_completed_at",
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active",
        ],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "liveness_probe_mode": [ROLE_AGENT_LIVENESS_PROBE_MODE],
            "all_liveness_probes_started_before_wait": [True],
            "rehydrated_role_agents[].role_key": list(CREW_ROLE_KEYS),
            "rehydrated_role_agents[].model_policy": [BACKGROUND_ROLE_MODEL_POLICY],
            "rehydrated_role_agents[].reasoning_effort_policy": [BACKGROUND_ROLE_REASONING_EFFORT_POLICY],
            "rehydrated_role_agents[].rehydration_result": sorted(RESUME_ROLE_AGENT_RESULTS),
            "rehydrated_role_agents[].rehydrated_for_run_id": [run_state["run_id"]],
            "rehydrated_role_agents[].rehydrated_after_resume_state_loaded": [True],
            "rehydrated_role_agents[].host_liveness_status": sorted(ROLE_AGENT_HOST_LIVENESS_STATUSES),
            "rehydrated_role_agents[].liveness_decision": sorted(ROLE_AGENT_LIVENESS_DECISIONS),
            "rehydrated_role_agents[].resume_agent_attempted": [True],
            "rehydrated_role_agents[].bounded_wait_result": sorted(ROLE_AGENT_BOUNDED_WAIT_RESULTS),
            "rehydrated_role_agents[].liveness_probe_mode": [ROLE_AGENT_LIVENESS_PROBE_MODE],
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active": [False],
        },
        conditional_required_fields={
            "when role_rehydration_request[].role_memory_status=available": [
                "rehydrated_role_agents[].memory_packet_path",
                "rehydrated_role_agents[].memory_packet_hash",
                "rehydrated_role_agents[].memory_seeded_from_current_run",
            ],
            "when role_rehydration_request[].role_memory_status!=available": [
                "rehydrated_role_agents[].memory_missing_acknowledged",
                "rehydrated_role_agents[].replacement_seeded_from_common_run_context",
            ],
            "when rehydrated_role_agents[].role_key=project_manager": [
                "rehydrated_role_agents[].pm_resume_context_delivered",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate rehydrated role agent record for each FlowPilot role key.",
            "Start all six liveness probes in one concurrent batch before waiting for individual results.",
            "Use one liveness_probe_batch_id for the top-level receipt and every role record.",
            "Each record must match the corresponding role_rehydration_request path/hash fields.",
            "Reuse active current-run role agents after memory/context refresh; spawn only replacement roles whose liveness is missing, cancelled, unknown, completed, or timeout_unknown.",
            "Each restored or replacement live role agent must be bound to the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
            "A wait_agent timeout must be recorded as timeout_unknown and must not justify live_agent_continuity_confirmed.",
            "missing, cancelled, completed, unknown, or timeout_unknown host liveness must spawn a replacement from current-run memory instead of continuing to wait on the old role.",
        ],
        optional_fields=[
            "rehydrated_role_agents[].spawned_after_resume_state_loaded",
        ],
        description="Refresh or replace all six FlowPilot role bindings from current-run memory before PM resume decision, reusing active agents and spawning only failed replacements.",
        reviewer_check="PM and reviewer checks use the written crew_rehydration_report before resume decisions.",
    )


def _pm_resume_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_resume_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_RESUME_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "recovery_evidence",
            "role_freshness_verification",
            "packet_loop_continuation",
            "decision_rationale",
            "controller_reminder.controller_may_create_project_evidence",
            "controller_reminder.controller_may_approve_gates",
            "controller_reminder.controller_may_implement",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_RESUME_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "controller_reminder.controller_only": [True],
            "controller_reminder.controller_may_read_sealed_bodies": [False],
            "controller_reminder.controller_may_infer_from_chat_history": [False],
            "controller_reminder.controller_may_advance_or_close_route": [False],
            "controller_reminder.controller_may_create_project_evidence": [False],
        },
        conditional_required_fields={
            "when continuation/resume_reentry.json records ambiguous_state_blocks_controller_execution=true and decision=continue_current_packet_loop": [
                "explicit_recovery_evidence_recorded=true",
                "recovery_evidence",
            ],
            "when decision=close_after_final_ledger_and_terminal_replay": [
                "final_ledger_built_clean evidence",
                "final_backward_replay_passed evidence",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
        ],
        description=(
            "PM heartbeat/manual-resume recovery decision. This is a role-output body contract, "
            "not Controller-authored project evidence; Controller waits for Router status after the runtime submits it."
        ),
    )


def _pm_parent_segment_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_parent_segment_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "repair_node_id",
            "superseded_nodes",
            "stale_evidence_to_mark",
            "decision_rationale",
            "same_parent_replay_rerun_plan",
            "contract_self_check",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
        },
        conditional_required_fields={
            "when decision!=continue": [
                "decision_rationale",
                "stale_evidence_to_mark or superseded_nodes when affected evidence/nodes exist",
                "same_parent_replay_rerun_plan",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Only decision=continue may close the active parent node; all other decisions require route mutation and same-parent replay rerun.",
        ],
        description=(
            "PM parent-segment decision after reviewer backward replay. This is a role-output body "
            "contract; Controller waits for Router status after the runtime submits it."
        ),
    )


def _pm_terminal_closure_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_terminal_closure_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "final_report",
            "closure_rationale",
            "lifecycle_reconciliation",
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean",
            "lifecycle_reconciliation.terminal_backward_replay_passed",
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure",
            "lifecycle_reconciliation.execution_frontier_current",
            "lifecycle_reconciliation.crew_ledger_current",
            "lifecycle_reconciliation.continuation_binding_current",
            "lifecycle_reconciliation.current_ledgers_clean",
            "lifecycle_reconciliation.pm_suggestion_ledger_clean",
            "contract_self_check",
        ],
        allowed_values={
            "approved_by_role": ["project_manager"],
            "decision": sorted(PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean": [True],
            "lifecycle_reconciliation.terminal_backward_replay_passed": [True],
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure": [True],
            "lifecycle_reconciliation.execution_frontier_current": [True],
            "lifecycle_reconciliation.crew_ledger_current": [True],
            "lifecycle_reconciliation.continuation_binding_current": [True],
            "lifecycle_reconciliation.current_ledgers_clean": [True],
            "lifecycle_reconciliation.pm_suggestion_ledger_clean": [True],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Approve closure only after clean final ledger, passed terminal backward replay, current completion projection, clean PM suggestion ledger, clean lifecycle ledgers, and continuation binding are present.",
        ],
        description=(
            "PM terminal closure approval. This is a role-output body contract; Controller may only "
            "wait for Router status and must not infer closure from chat history."
        ),
    )


def _pm_model_miss_triage_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    return _payload_contract(
        name="pm_model_miss_triage_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "officer_request_refs",
            "officer_report_refs",
            "same_class_findings_summary",
            "candidate_repairs_considered",
            "minimal_sufficient_repair_recommendation",
            "rejected_larger_repairs",
            "rejected_smaller_repairs",
            "post_repair_model_checks_required",
            "decision_rationale",
        ],
        allowed_values={
            "decided_by_role": ["project_manager"],
            "decision": sorted(PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES),
            "same_class_findings_reviewed": [True, False],
            "repair_recommendation_reviewed": [True, False],
        },
        conditional_required_fields={
            "when decision=proceed_with_model_backed_repair": [
                "flowguard_capability.can_model_bug_class=true",
                "officer_report_refs[].report_path",
                "officer_report_refs[].report_hash",
                "same_class_findings_reviewed=true",
                "repair_recommendation_reviewed=true",
                "candidate_repairs_considered",
                "minimal_sufficient_repair_recommendation",
                "post_repair_model_checks_required",
            ],
            "when decision=out_of_scope_not_modelable": [
                "flowguard_capability.can_model_bug_class=false",
                "flowguard_capability.incapability_reason",
                "selected_next_action",
                "why_repair_may_start",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Do not start pm.review_repair until this decision either authorizes a model-backed repair or records why FlowGuard cannot model the bug class.",
            "For model-backed repair, officer reports must include old_model_miss_reason, bug_class_definition, same_class_findings, coverage_added, candidate_repairs, minimal_sufficient_repair_recommendation, rejected_larger_repairs, rejected_smaller_repairs, post_repair_model_checks_required, and residual_blindspots.",
            "PM selects the repair path; officer reports provide model evidence and repair recommendations but do not approve route mutation by themselves.",
        ],
        description=(
            "PM model-miss triage decision for reviewer blockers. This closes the obligation to ask why "
            "FlowGuard missed the bug class before normal repair planning can start."
        ),
    )


def _pm_decision_payload_contract_for_card(project_root: Path, run_root: Path, card_id: str) -> dict[str, Any] | None:
    if card_id == "pm.resume_decision":
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if card_id == "pm.model_miss_triage":
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if card_id == "pm.parent_segment_decision":
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if card_id == "pm.closure":
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None


def _role_decision_payload_contract_for_events(
    project_root: Path, run_root: Path, allowed_events: list[str]
) -> dict[str, Any] | None:
    if allowed_events == ["pm_resume_recovery_decision_returned"]:
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if allowed_events == [PM_MODEL_MISS_TRIAGE_DECISION_EVENT]:
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if allowed_events == ["pm_records_parent_segment_decision"]:
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if allowed_events == ["pm_approves_terminal_closure"]:
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _control_blocker_error_code(message: str) -> str:
    cleaned: list[str] = []
    for char in message.lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != "_":
            cleaned.append("_")
    code = "".join(cleaned).strip("_")
    return code[:96] or "router_hard_rejection"


def _project_relative_if_possible(project_root: Path, path: Path) -> str:
    try:
        return project_relative(project_root, path)
    except RouterError:
        return str(path)


def _payload_source_paths(project_root: Path, run_root: Path, payload: dict[str, Any] | None) -> dict[str, str]:
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
    }
    packet_ledger = run_root / "packet_ledger.json"
    if packet_ledger.exists():
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger)
    if not isinstance(payload, dict):
        return source_paths
    for key in (
        "body_path",
        "report_path",
        "decision_path",
        "result_body_path",
        "packet_envelope_path",
        "result_envelope_path",
        "packet_index_path",
        "path",
    ):
        raw = payload.get(key)
        if not raw:
            continue
        candidate = resolve_project_path(project_root, str(raw))
        source_paths[key] = _project_relative_if_possible(project_root, candidate)
    return source_paths


def _control_payload_public_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    forbidden_body_keys = {
        "blockers",
        "checks",
        "commands",
        "decision",
        "decision_body",
        "evidence",
        "findings",
        "passed",
        "direct_material_sources_checked",
        "packet_matches_checked_sources",
        "pm_ready",
        "recommendations",
        "repair_instructions",
        "report_body",
        "result_body",
    }
    public: dict[str, Any] = {}
    for key, value in payload.items():
        if key in forbidden_body_keys:
            public[key] = "[redacted: role body field was controller-visible]"
            continue
        if key.endswith("_path") or key.endswith("_hash") or key in {
            "packet_id",
            "route_id",
            "node_id",
            "role",
            "from_role",
            "to_role",
            "expected_role",
            "completed_by_role",
            "reviewed_by_role",
            "controller_visibility",
            "chat_response_body_allowed",
        }:
            public[key] = _json_safe(value)
    return public


def _infer_responsible_role(event: str | None, payload: dict[str, Any] | None, message: str) -> str:
    if isinstance(payload, dict):
        for key in ("reviewed_by_role", "completed_by_role", "from_role", "to_role", "role", "expected_role"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    if event:
        if event.startswith("reviewer_") or "reviewer" in event:
            return "human_like_reviewer"
        if event.startswith("worker_") or "worker_" in event:
            if "worker_b" in message or "worker-b" in message:
                return "worker_b"
            return "worker_a"
        if event.startswith("product_officer_"):
            return "product_flowguard_officer"
        if event.startswith("process_officer_"):
            return "process_flowguard_officer"
        if event.startswith("pm_"):
            return "project_manager"
    lowered = message.lower()
    if "product_flowguard_officer" in lowered:
        return "product_flowguard_officer"
    if "process_flowguard_officer" in lowered:
        return "process_flowguard_officer"
    if "human_like_reviewer" in lowered or "reviewer" in lowered:
        return "human_like_reviewer"
    if "project_manager" in lowered or message.startswith("PM "):
        return "project_manager"
    return "project_manager"


def _classify_control_blocker(message: str, *, event: str | None = None, action_type: str | None = None) -> str:
    del action_type
    lowered = message.lower()
    fatal_markers = (
        "private role-to-role",
        "controller relay violation",
        "body was read by controller",
        "body was executed by controller",
        "body_was_read_by_controller",
        "body_was_executed_by_controller",
        "controller read",
        "controller executes",
        "contaminated envelope",
        "leaked role body fields to controller",
        "controller relay envelope hash mismatch",
    )
    if any(marker in lowered for marker in fatal_markers):
        return "fatal_protocol_violation"
    if "role output runtime envelope body hash is stale" in lowered:
        return "control_plane_reissue"
    semantic_pm_markers = (
        "controller-origin",
        "controller_origin_artifact",
        "wrong role",
        "wrong-role",
        "result_completed_by_wrong_role",
        "completed_agent_id_not_assigned_to_role",
        "packet body hash mismatch",
        "result body hash mismatch",
        "stale",
        "unresolved",
        "final ledger",
        "route mutation",
        "parent segment",
        "ambiguous",
        "repair decision",
    )
    if any(marker in lowered for marker in semantic_pm_markers):
        return "pm_repair_decision_required"
    mechanical_reissue_markers = (
        "result_body_not_opened",
        "packet_body_not_opened",
        "packet body was not opened by target role after controller relay",
        "body was not opened by target role after controller relay",
        "ledger open receipt is invalid",
        "packet_ledger_missing_packet_body_open_receipt",
        "packet_ledger_missing_result_absorption",
        "packet_ledger_missing_result_body_open_receipt",
        "result body was not opened",
        "completed_agent_id_is_role_key_not_agent_id",
        "role output runtime envelope claims validation but has no receipt",
        "role output runtime receipt requires both path and hash",
        "role output runtime receipt path is missing",
        "role output runtime receipt hash mismatch",
        "role output runtime envelope missing output path/hash pair",
        "role output runtime envelope body hash is stale",
        "missing_quality_pack_check",
        "quality_pack_checks",
    )
    if any(marker in lowered for marker in mechanical_reissue_markers):
        return "control_plane_reissue"
    pm_markers = (
        "reviewer pass rejected by packet audit",
        "current-node result failed pre-relay packet runtime audit",
        "packet group reviewer audit failed",
    )
    if any(marker in lowered for marker in pm_markers):
        return "pm_repair_decision_required"
    if event in {
        "current_node_reviewer_passes_result",
        "reviewer_reports_material_sufficient",
        "reviewer_reports_material_insufficient",
        "reviewer_passes_research_direct_source_check",
        "reviewer_passes_route_check",
        "reviewer_final_backward_replay_passed",
    }:
        return "control_plane_reissue"
    reissue_markers = (
        "requires a file-backed body path",
        "requires a body/report/decision hash",
        "role body path is missing",
        "role body hash mismatch",
        "must be reviewed_by_role",
        "must explicitly pass",
        "gate report must",
        "requires direct_material_sources_checked",
        "requires packet_matches_checked_sources",
        "requires pm_ready",
        "must route to",
        "requires packet_id",
        "requires packet envelope",
        "missing source paths",
    )
    if any(marker in lowered for marker in reissue_markers):
        return "control_plane_reissue"
    return "pm_repair_decision_required"


def _should_materialize_control_blocker(
    message: str,
    *,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> bool:
    lowered = message.lower()
    if lowered.startswith("event ") and " requires " in lowered:
        return False
    if "run 'next' before applying" in lowered or "pending action is" in lowered:
        return False
    if "requires a file-backed body path" in lowered and not payload:
        return False
    material_markers = (
        "requires a file-backed body path",
        "requires a body/report/decision hash",
        "role body path is missing",
        "role body hash mismatch",
        "leaked role body fields to controller",
        "must be reviewed_by_role",
        "must explicitly pass",
        "gate report must",
        "requires direct_material_sources_checked",
        "requires packet_matches_checked_sources",
        "requires pm_ready",
        "packet group reviewer audit failed",
        "reviewer pass rejected by packet audit",
        "current-node result failed pre-relay packet runtime audit",
        "controller-origin",
        "wrong role",
        "wrong-role",
        "result_completed_by_wrong_role",
        "completed_agent_id",
        "packet_ledger_missing_result_absorption",
        "packet_ledger_missing_packet_body_open_receipt",
        "packet_ledger_missing_result_body_open_receipt",
        "ledger open receipt is invalid",
        "packet ledger missing packet body open receipt",
        "packet ledger missing result absorption",
        "packet ledger missing result body open receipt",
        "missing controller relay signature",
        "envelope was not delivered via controller",
        "controller did not sign",
        "private role-to-role",
        "controller relay violation",
        "contaminated envelope",
        "body was not opened",
        "unopened",
        "packet body hash mismatch",
        "result body hash mismatch",
        "controller relay envelope hash mismatch",
        "role output runtime receipt",
        "body_ref",
        "runtime_receipt_ref",
        "quality_pack_checks",
    )
    if any(marker in lowered for marker in material_markers):
        return True
    if action_type in {
        "relay_material_scan_packets",
        "relay_material_scan_results_to_reviewer",
        "relay_research_packet",
        "relay_research_result_to_reviewer",
        "relay_current_node_packet",
        "relay_current_node_result_to_reviewer",
    }:
        return True
    if isinstance(payload, dict) and any(
        payload.get(key)
        for key in (
            "body_path",
            "body_hash",
            "report_path",
            "report_hash",
            "decision_path",
            "decision_hash",
            "result_body_path",
            "result_body_hash",
            "body_ref",
            "runtime_receipt_ref",
        )
    ):
        return event is not None and (
            event.startswith("reviewer_")
            or event.startswith("process_officer_")
            or event.startswith("product_officer_")
            or event
            in {
                "current_node_reviewer_passes_result",
                "pm_resume_recovery_decision_returned",
                PM_MODEL_MISS_TRIAGE_DECISION_EVENT,
                "pm_records_parent_segment_decision",
            }
        )
    return False


def _skill_observation_reminder(
    message: str,
    *,
    event: str | None = None,
    action_type: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    lowered = message.lower()
    suggested_kind = "controller_compensation"
    if "route" in lowered or "frontier" in lowered:
        suggested_kind = "router_state_gap"
    elif "ledger" in lowered:
        suggested_kind = "ledger_gap"
    elif "display_plan" in lowered or "visible plan" in lowered:
        suggested_kind = "display_projection_gap"
    elif "heartbeat" in lowered or "pause" in lowered or "resume" in lowered:
        suggested_kind = "heartbeat_gap"
    elif "schema" in lowered or "field" in lowered or "hash" in lowered or "path" in lowered:
        suggested_kind = "schema_gap"
    return {
        "schema_version": "flowpilot.skill_observation_reminder.v1",
        "should_consider_recording": True,
        "reason": "router_control_plane_exception",
        "originating_event": event,
        "originating_action_type": action_type,
        "handling_lane": category,
        "suggested_kind": suggested_kind,
        "summary": message,
        "write_path": ".flowpilot/runs/<run_id>/flowpilot_skill_improvement_report.json",
        "record_only_if": "This reflects a FlowPilot skill/protocol/router weakness, not ordinary project work.",
        "do_not_include": [
            "sealed packet bodies",
            "sealed result bodies",
            "private role reasoning",
            "secrets",
        ],
    }


def _validated_external_event_names(
    events: Any,
    *,
    context: str,
    allow_pm_repair_event: bool = True,
) -> list[str]:
    if not isinstance(events, list) or not events:
        raise RouterError(f"{context} requires a non-empty allowed_external_events list")
    normalized: list[str] = []
    invalid: list[str] = []
    for item in events:
        name = _control_resolution_event_name(item)
        if not name:
            invalid.append(str(item))
            continue
        if name == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT and not allow_pm_repair_event:
            invalid.append(name)
            continue
        if name not in EXTERNAL_EVENTS:
            invalid.append(name)
            continue
        if name not in normalized:
            normalized.append(name)
    if invalid:
        raise RouterError(f"{context} contains unregistered external event(s): {', '.join(invalid)}")
    return normalized


def _external_event_validation_issue(events: Any) -> dict[str, Any] | None:
    try:
        _validated_external_event_names(events, context="event validation")
    except RouterError as exc:
        return {"reason": "invalid_allowed_external_events", "error": str(exc)}
    return None


def _control_blocker_allowed_resolution_events(category: str, event: str | None) -> list[str]:
    if category == "control_plane_reissue" and event:
        return _validated_external_event_names([event], context="control-plane reissue resolution")
    if category in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
    return sorted(EXTERNAL_EVENTS)


def _control_blocker_policy(category: str, *, responsible_role: str, event: str | None) -> dict[str, Any]:
    if category == "control_plane_reissue":
        target_role = responsible_role
        instruction = (
            f"Deliver the sealed repair packet envelope to `{target_role}` and request a same-role reissue of the "
            "rejected control-plane output. Controller may route the packet path and hash only."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to the responsible role",
            "tell the responsible role to reissue the same control-plane output",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "infer project status from chat history",
            "ask a worker to change project substance",
            "convert the router rejection into PM-owned evidence",
        ]
        pm_required = False
    elif category == "fatal_protocol_violation":
        target_role = "project_manager"
        instruction = (
            "Stop normal route work and deliver this control blocker to `project_manager` for escalation. "
            "Controller may route the sealed repair packet envelope only and must not repair the route from chat."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager",
            "wait for an explicit PM or user recovery decision",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "contact the worker directly",
            "advance, close, or mutate the route",
            "treat controller-visible leaked content as evidence",
        ]
        pm_required = True
    else:
        target_role = "project_manager"
        instruction = (
            "Deliver the sealed repair packet envelope to `project_manager` for a repair decision. Controller must "
            "not decide whether the work is substantively acceptable and must not inspect or restate the repair details."
        )
        allowed = [
            "read this control blocker artifact",
            "deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager",
            "quote blocker_id, error_code, handling_lane, and target_role",
        ]
        forbidden = [
            "open sealed packet/result/report bodies",
            "contact the worker directly about project repair",
            "summarize reviewer or worker body content",
            "advance route state from the rejected event",
        ]
        pm_required = True
    return {
        "target_role": target_role,
        "pm_decision_required": pm_required,
        "controller_instruction": instruction,
        "controller_allowed_actions": allowed,
        "controller_forbidden_actions": forbidden,
        "allowed_resolution_events": _control_blocker_allowed_resolution_events(category, event),
    }


def _write_control_blocker_repair_packet(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    blocker_id: str,
    category: str,
    target_role: str,
    responsible_role: str,
    error_message: str,
    event: str | None,
    action_type: str | None,
    payload: dict[str, Any] | None,
) -> dict[str, str]:
    packet_path = run_root / "control_blocks" / f"{blocker_id}.sealed_repair_packet.json"
    packet = {
        "schema_version": CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA,
        "blocker_id": blocker_id,
        "run_id": run_state.get("run_id"),
        "body_visibility": "sealed_router_repair_details_for_target_role",
        "target_role": target_role,
        "responsible_role_for_reissue": responsible_role if category == "control_plane_reissue" else None,
        "handling_lane": category,
        "originating_event": event,
        "originating_action_type": action_type,
        "error_code": _control_blocker_error_code(error_message),
        "error_message": error_message,
        "source_paths": _payload_source_paths(project_root, run_root, payload),
        "payload_envelope_public_view": _control_payload_public_view(payload),
        "controller_may_read_body": False,
        "controller_may_repair_from_this_packet": False,
        "target_role_repair_instruction": (
            "Inspect this sealed packet, fix the rejected control-plane output, and reissue the router event named "
            "in allowed_resolution_events. Do not ask Controller to infer or patch the body."
        ),
        "allowed_resolution_events": _control_blocker_allowed_resolution_events(category, event),
        "created_at": utc_now(),
    }
    write_json(packet_path, packet)
    return {
        "sealed_repair_packet_path": project_relative(project_root, packet_path),
        "sealed_repair_packet_hash": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
    }


def _supersede_prior_control_blockers(
    run_root: Path,
    *,
    blocker_id: str,
    category: str,
    event: str | None,
    action_type: str | None,
) -> None:
    control_root = run_root / "control_blocks"
    if not control_root.exists():
        return
    superseded_at = utc_now()
    for path in sorted(control_root.glob("*.json")):
        record = read_json_if_exists(path)
        if record.get("schema_version") != CONTROL_BLOCKER_SCHEMA:
            continue
        if record.get("resolution_status") or record.get("blocker_id") == blocker_id:
            continue
        if record.get("handling_lane") != category:
            continue
        if record.get("originating_event") != event or record.get("originating_action_type") != action_type:
            continue
        record["resolution_status"] = "superseded_by_newer_control_blocker"
        record["superseded_by_blocker_id"] = blocker_id
        record["resolved_at"] = superseded_at
        record["resolution_note"] = "A newer router rejection for the same control-plane event replaced this pending repair packet."
        write_json(path, record)


def _write_control_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    category = _classify_control_blocker(error_message, event=event, action_type=action_type)
    if category not in CONTROL_BLOCKER_LANES:
        category = "pm_repair_decision_required"
    responsible_role = _infer_responsible_role(event, payload, error_message)
    policy = _control_blocker_policy(category, responsible_role=responsible_role, event=event)
    index = len(run_state.setdefault("control_blockers", [])) + 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    blocker_id = f"control-blocker-{index:04d}-{stamp}"
    artifact_path = run_root / "control_blocks" / f"{blocker_id}.json"
    artifact_rel = project_relative(project_root, artifact_path)
    repair_packet = _write_control_blocker_repair_packet(
        project_root,
        run_root,
        run_state,
        blocker_id=blocker_id,
        category=category,
        target_role=policy["target_role"],
        responsible_role=responsible_role,
        error_message=error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    )
    record = {
        "schema_version": CONTROL_BLOCKER_SCHEMA,
        "blocker_id": blocker_id,
        "run_id": run_state.get("run_id"),
        "created_at": utc_now(),
        "source": source,
        "originating_event": event,
        "originating_action_type": action_type,
        "handling_lane": category,
        "error_code": _control_blocker_error_code(error_message),
        "controller_visible_summary": "Router rejected a control-plane payload. Deliver the sealed repair packet to the target role.",
        "blocker_artifact_path": artifact_rel,
        "sealed_repair_packet_path": repair_packet["sealed_repair_packet_path"],
        "sealed_repair_packet_hash": repair_packet["sealed_repair_packet_hash"],
        "responsible_role_for_reissue": responsible_role if category == "control_plane_reissue" else None,
        "target_role": policy["target_role"],
        "pm_decision_required": policy["pm_decision_required"],
        "controller_instruction": policy["controller_instruction"],
        "controller_allowed_actions": policy["controller_allowed_actions"],
        "controller_forbidden_actions": policy["controller_forbidden_actions"],
        "allowed_resolution_events": policy["allowed_resolution_events"],
        "sealed_body_read_by_controller_allowed": False,
        "controller_history_is_evidence": False,
        "delivery_status": "pending",
        "skill_observation_reminder": _skill_observation_reminder(
            "Control-plane payload was rejected and a sealed repair packet was issued for the target role.",
            event=event,
            action_type=action_type,
            category=category,
        ),
    }
    write_json(artifact_path, record)
    _supersede_prior_control_blockers(
        run_root,
        blocker_id=blocker_id,
        category=category,
        event=event,
        action_type=action_type,
    )
    active = {
        "blocker_id": blocker_id,
        "handling_lane": category,
        "blocker_artifact_path": artifact_rel,
        "target_role": policy["target_role"],
        "responsible_role_for_reissue": record["responsible_role_for_reissue"],
        "pm_decision_required": policy["pm_decision_required"],
        "delivery_status": "pending",
        "sealed_repair_packet_path": repair_packet["sealed_repair_packet_path"],
        "sealed_repair_packet_hash": repair_packet["sealed_repair_packet_hash"],
        "originating_event": event,
        "originating_action_type": action_type,
        "created_at": record["created_at"],
    }
    run_state["active_control_blocker"] = active
    run_state["latest_control_blocker_path"] = artifact_rel
    run_state["control_blockers"].append(active)
    run_state["pending_action"] = None
    append_history(
        run_state,
        "router_recorded_control_blocker",
        {
            "blocker_id": blocker_id,
            "handling_lane": category,
            "target_role": policy["target_role"],
            "originating_event": event,
            "originating_action_type": action_type,
        },
    )
    _sync_control_plane_indexes(project_root, run_root, run_state)
    save_run_state(run_root, run_state)
    return record


def _control_blocker_record(project_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    raw_path = active.get("blocker_artifact_path")
    if not raw_path:
        return active
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return active
    return read_json(path)


def _control_blocker_summary(record: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "blocker_id",
        "handling_lane",
        "blocker_artifact_path",
        "target_role",
        "responsible_role_for_reissue",
        "pm_decision_required",
        "delivery_status",
        "sealed_repair_packet_path",
        "sealed_repair_packet_hash",
        "originating_event",
        "originating_action_type",
        "created_at",
        "delivered_to_role",
        "delivered_at",
        "resolution_status",
        "resolved_by_event",
        "resolved_at",
        "pm_repair_decision_status",
        "pm_repair_decision_path",
        "pm_repair_decision_hash",
        "pm_repair_rerun_target",
        "repair_transaction_id",
        "repair_transaction_path",
        "repair_outcome_table",
        "allowed_resolution_events",
    )
    return {field: record.get(field) for field in fields if field in record}


def _sync_protocol_blocker_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    blockers: list[dict[str, Any]] = []
    blocker_root = run_root / "blockers"
    if blocker_root.exists():
        for path in sorted(blocker_root.glob("*.json")):
            record = read_json_if_exists(path)
            blockers.append(
                {
                    "path": project_relative(project_root, path),
                    "blocker_id": record.get("blocker_id") or path.stem,
                    "blocker_type": record.get("blocker_type"),
                    "status": record.get("status"),
                    "registered_at": record.get("registered_at") or utc_now(),
                }
            )
    run_state["protocol_blockers"] = blockers


def _sync_control_plane_indexes(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    summaries: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    control_root = run_root / "control_blocks"
    if control_root.exists():
        for path in sorted(control_root.glob("*.json")):
            record = read_json_if_exists(path)
            if record.get("schema_version") != CONTROL_BLOCKER_SCHEMA:
                continue
            summary = _control_blocker_summary(record)
            summaries.append(summary)
            if record.get("resolution_status"):
                resolved.append(summary)
            else:
                active = summary
    run_state["control_blockers"] = summaries
    run_state["resolved_control_blockers"] = resolved
    run_state["active_control_blocker"] = active
    run_state["latest_control_blocker_path"] = active.get("blocker_artifact_path") if active else None
    _sync_protocol_blocker_index(project_root, run_root, run_state)
    _write_repair_transaction_index(project_root, run_root, run_state)


def _control_blocker_wait_events(record: dict[str, Any]) -> tuple[list[str], dict[str, Any] | None]:
    raw_events = record.get("allowed_resolution_events") or sorted(EXTERNAL_EVENTS)
    issue = _external_event_validation_issue(raw_events)
    if issue is None:
        return _validated_external_event_names(raw_events, context="control blocker wait"), None
    lane = str(record.get("handling_lane") or "")
    if lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT], {
            **issue,
            "fallback": "pm_must_resubmit_control_blocker_repair_decision",
            "previous_allowed_resolution_events": raw_events,
        }
    raise RouterError(str(issue.get("error") or "control blocker wait contains invalid allowed external events"))


def _event_producer_roles(allowed_events: list[str]) -> set[str]:
    roles: set[str] = set()
    for event in allowed_events:
        meta = EXTERNAL_EVENTS.get(event) or {}
        roles.add(_event_wait_role(event, meta))
    return roles


def _role_set(to_role: str) -> set[str]:
    return {part.strip() for part in str(to_role or "").split(",") if part.strip()}


def _control_blocker_followup_target_role(allowed_events: list[str], fallback_role: str) -> str:
    roles = _event_producer_roles(allowed_events)
    if not roles:
        return fallback_role
    fallback_roles = _role_set(fallback_role)
    if roles.issubset(fallback_roles):
        return fallback_role
    return ",".join(sorted(roles))


def _validate_wait_event_producer_binding(
    allowed_events: list[str],
    *,
    to_role: str,
    context: str,
) -> None:
    producer_roles = _event_producer_roles(allowed_events)
    target_roles = _role_set(to_role)
    if producer_roles and not producer_roles.issubset(target_roles):
        raise RouterError(
            f"{context} waits for event producer role(s) {sorted(producer_roles)} "
            f"but targets {sorted(target_roles)}"
        )


def _next_control_blocker_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return None
    record = _control_blocker_record(project_root, active)
    artifact_rel = str(record.get("blocker_artifact_path") or active.get("blocker_artifact_path") or "")
    if not artifact_rel:
        return None
    lane = str(record.get("handling_lane") or active.get("handling_lane") or "pm_repair_decision_required")
    target_role = str(record.get("target_role") or active.get("target_role") or "project_manager")
    allowed_resolution_events, event_contract_issue = _control_blocker_wait_events(record)
    target_role = _control_blocker_followup_target_role(allowed_resolution_events, target_role)
    _validate_wait_event_producer_binding(
        allowed_resolution_events,
        to_role=target_role,
        context="control blocker wait",
    )
    if record.get("delivery_status") != "delivered":
        return make_action(
            action_type="handle_control_blocker",
            actor="controller",
            label=f"controller_handles_{lane}_control_blocker",
            summary=f"Deliver router control blocker {record.get('blocker_id')} sealed repair packet envelope to {target_role}.",
            allowed_reads=[artifact_rel, project_relative(project_root, run_state_path(run_root))],
            allowed_writes=[
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, run_root / "control_blocks" / "control_blocker_delivery_ledger.json"),
            ],
            to_role=target_role,
            extra={
                "blocker_id": record.get("blocker_id"),
                "blocker_artifact_path": artifact_rel,
                "sealed_repair_packet_path": record.get("sealed_repair_packet_path"),
                "sealed_repair_packet_hash": record.get("sealed_repair_packet_hash"),
                "handling_lane": lane,
                "pm_decision_required": bool(record.get("pm_decision_required")),
                "responsible_role_for_reissue": record.get("responsible_role_for_reissue"),
                "repair_transaction_id": record.get("repair_transaction_id"),
                "repair_outcome_table": record.get("repair_outcome_table"),
                "controller_instruction": record.get("controller_instruction"),
                "controller_allowed_actions": record.get("controller_allowed_actions") or [],
                "controller_forbidden_actions": record.get("controller_forbidden_actions") or [],
                "sealed_body_reads_allowed": False,
                "controller_history_is_evidence": False,
                "allowed_resolution_events": allowed_resolution_events,
                "event_contract_issue": event_contract_issue,
                "repair_details_visibility": "sealed_to_target_role_not_controller",
                "skill_observation_reminder": record.get("skill_observation_reminder"),
            },
        )
    return make_action(
        action_type="await_role_decision",
        actor="controller",
        label="controller_waits_for_control_blocker_resolution",
        summary="A router control blocker has been delivered. Controller must wait for the target role's corrected event or PM recovery decision.",
        allowed_reads=[artifact_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=target_role,
        extra={
            "allowed_external_events": allowed_resolution_events,
            "blocker_artifact_path": artifact_rel,
            "target_role": target_role,
            "handling_lane": lane,
            "repair_transaction_id": record.get("repair_transaction_id"),
            "repair_outcome_table": record.get("repair_outcome_table"),
            "event_contract_issue": event_contract_issue,
        },
    )


def _mark_control_blocker_delivered(project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> None:
    artifact_rel = str(pending.get("blocker_artifact_path") or "")
    if not artifact_rel:
        raise RouterError("control blocker action is missing blocker_artifact_path")
    artifact_path = resolve_project_path(project_root, artifact_rel)
    record = read_json(artifact_path)
    delivered_at = utc_now()
    target_role = str(pending.get("to_role") or record.get("target_role") or "project_manager")
    record["delivery_status"] = "delivered"
    record["delivered_by"] = "controller"
    record["delivered_to_role"] = target_role
    record["delivered_at"] = delivered_at
    write_json(artifact_path, record)
    active = run_state.get("active_control_blocker")
    if isinstance(active, dict) and active.get("blocker_id") == record.get("blocker_id"):
        active["delivery_status"] = "delivered"
        active["delivered_to_role"] = target_role
        active["delivered_at"] = delivered_at
    ledger_path = run_root / "control_blocks" / "control_blocker_delivery_ledger.json"
    ledger = read_json_if_exists(ledger_path) or {"schema_version": "flowpilot.control_blocker_delivery_ledger.v1", "deliveries": []}
    ledger.setdefault("deliveries", []).append(
        {
            "blocker_id": record.get("blocker_id"),
            "blocker_artifact_path": artifact_rel,
            "handling_lane": record.get("handling_lane"),
            "sealed_repair_packet_path": record.get("sealed_repair_packet_path"),
            "sealed_repair_packet_hash": record.get("sealed_repair_packet_hash"),
            "delivered_by": "controller",
            "delivered_to_role": target_role,
            "delivered_at": delivered_at,
        }
    )
    ledger["updated_at"] = delivered_at
    write_json(ledger_path, ledger)
    _sync_control_plane_indexes(project_root, run_root, run_state)


def _validate_model_miss_officer_report_refs(project_root: Path, decision: dict[str, Any]) -> list[dict[str, Any]]:
    refs = decision.get("officer_report_refs")
    if not isinstance(refs, list) or not refs:
        raise RouterError("model-backed repair requires non-empty officer_report_refs")
    checked: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise RouterError("officer_report_refs entries must be objects")
        report_path = str(ref.get("report_path") or ref.get("path") or "").strip()
        report_hash = str(ref.get("report_hash") or ref.get("hash") or "").strip()
        if not report_path:
            raise RouterError("officer_report_refs[].report_path is required")
        if not report_hash:
            raise RouterError("officer_report_refs[].report_hash is required")
        path = resolve_project_path(project_root, report_path)
        if not path.exists():
            raise RouterError(f"officer model-miss report path does not exist: {report_path}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != report_hash:
            raise RouterError(f"officer model-miss report hash mismatch for {report_path}")
        report = read_json(path)
        missing = [
            field
            for field in MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS
            if field not in report or report.get(field) is None
        ]
        if missing:
            raise RouterError(
                "officer model-miss report is missing required fields: "
                + ", ".join(missing)
            )
        if not isinstance(report.get("same_class_findings"), list):
            raise RouterError("officer model-miss report requires same_class_findings list")
        if not isinstance(report.get("candidate_repairs"), list) or not report.get("candidate_repairs"):
            raise RouterError("officer model-miss report requires non-empty candidate_repairs")
        if not isinstance(report.get("minimal_sufficient_repair_recommendation"), dict):
            raise RouterError("officer model-miss report requires minimal_sufficient_repair_recommendation object")
        contract_self_check = report.get("contract_self_check")
        if not isinstance(contract_self_check, dict):
            raise RouterError("officer model-miss report requires contract_self_check")
        if contract_self_check.get("all_required_fields_present") is not True:
            raise RouterError("officer model-miss report requires contract_self_check.all_required_fields_present=true")
        if contract_self_check.get("exact_field_names_used") is not True:
            raise RouterError("officer model-miss report requires contract_self_check.exact_field_names_used=true")
        checked.append(
            {
                "index": index,
                "officer_role": ref.get("officer_role") or report.get("reported_by_role"),
                "report_path": report_path,
                "report_hash": report_hash,
                "same_class_finding_count": len(report.get("same_class_findings") or []),
                "candidate_repair_count": len(report.get("candidate_repairs") or []),
            }
        )
    return checked


def _write_model_miss_triage_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("model-miss triage decision requires decided_by_role=project_manager")
    _require_single_active_model_miss_review_block(run_state, "model-miss triage decision")
    missing = [
        field
        for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS
        if field not in decision or decision.get(field) is None
    ]
    if missing:
        raise RouterError("model-miss triage decision is missing required fields: " + ", ".join(missing))
    decision_value = str(decision.get("decision") or "").strip()
    if decision_value not in PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES:
        raise RouterError("model-miss triage decision is not an allowed value")
    if not str(decision.get("defect_or_blocker_id") or "").strip():
        raise RouterError("model-miss triage decision requires defect_or_blocker_id")
    block_source = str(decision.get("reviewer_block_source_path") or "").strip()
    if not block_source:
        raise RouterError("model-miss triage decision requires reviewer_block_source_path")
    if not resolve_project_path(project_root, block_source).exists():
        raise RouterError("model-miss triage reviewer_block_source_path must exist")
    scope = decision.get("model_miss_scope")
    if not isinstance(scope, dict) or not str(scope.get("bug_class_definition") or "").strip():
        raise RouterError("model-miss triage decision requires model_miss_scope.bug_class_definition")
    capability = decision.get("flowguard_capability")
    if not isinstance(capability, dict) or not isinstance(capability.get("can_model_bug_class"), bool):
        raise RouterError("model-miss triage decision requires flowguard_capability.can_model_bug_class boolean")
    blockers = decision.get("blockers")
    if not isinstance(blockers, list):
        raise RouterError("model-miss triage decision requires blockers list")
    contract_self_check = decision.get("contract_self_check")
    if not isinstance(contract_self_check, dict):
        raise RouterError("model-miss triage decision requires contract_self_check")
    if contract_self_check.get("all_required_fields_present") is not True:
        raise RouterError("model-miss triage decision requires contract_self_check.all_required_fields_present=true")
    if contract_self_check.get("exact_field_names_used") is not True:
        raise RouterError("model-miss triage decision requires contract_self_check.exact_field_names_used=true")
    checked_reports: list[dict[str, Any]] = []
    if decision_value == "proceed_with_model_backed_repair":
        if capability.get("can_model_bug_class") is not True:
            raise RouterError("model-backed repair requires flowguard_capability.can_model_bug_class=true")
        if decision.get("same_class_findings_reviewed") is not True:
            raise RouterError("model-backed repair requires same_class_findings_reviewed=true")
        if decision.get("repair_recommendation_reviewed") is not True:
            raise RouterError("model-backed repair requires repair_recommendation_reviewed=true")
        if not decision.get("candidate_repairs_considered"):
            raise RouterError("model-backed repair requires candidate_repairs_considered")
        if not isinstance(decision.get("minimal_sufficient_repair_recommendation"), dict):
            raise RouterError("model-backed repair requires minimal_sufficient_repair_recommendation object")
        if not decision.get("post_repair_model_checks_required"):
            raise RouterError("model-backed repair requires post_repair_model_checks_required")
        checked_reports = _validate_model_miss_officer_report_refs(project_root, decision)
    elif decision_value == "out_of_scope_not_modelable":
        if capability.get("can_model_bug_class") is not False:
            raise RouterError("out-of-scope repair requires flowguard_capability.can_model_bug_class=false")
        if not str(capability.get("incapability_reason") or "").strip():
            raise RouterError("out-of-scope repair requires flowguard_capability.incapability_reason")
    elif decision_value in {"request_officer_model_miss_analysis", "needs_evidence_before_modeling", "stop_for_user"}:
        if decision.get("same_class_findings_reviewed") is True or decision.get("repair_recommendation_reviewed") is True:
            raise RouterError("non-authorizing model-miss decision must not claim reviewed repair evidence")
    if decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        if not str(decision.get("selected_next_action") or "").strip():
            raise RouterError("repair-authorizing model-miss decision requires selected_next_action")
        if not str(decision.get("why_repair_may_start") or "").strip():
            raise RouterError("repair-authorizing model-miss decision requires why_repair_may_start")
    output = {
        "schema_version": "flowpilot.pm_model_miss_triage_decision.v1",
        "run_id": run_state["run_id"],
        "recorded_at": utc_now(),
        "decision": decision_value,
        "repair_authorized": decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES,
        "checked_officer_reports": checked_reports,
        **{field: decision.get(field) for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS},
        **_role_output_envelope_record(decision),
    }
    if "officer_report_refs" in decision:
        output["officer_report_refs"] = decision.get("officer_report_refs")
    if "minimal_sufficient_repair_recommendation" in decision:
        output["minimal_sufficient_repair_recommendation"] = decision.get("minimal_sufficient_repair_recommendation")
    if "post_repair_model_checks_required" in decision:
        output["post_repair_model_checks_required"] = decision.get("post_repair_model_checks_required")
    decisions_dir = run_root / "defects" / "model_miss_triage"
    safe_id = "".join(
        char if char.isalnum() or char in {"-", "_"} else "-"
        for char in str(decision.get("defect_or_blocker_id") or "model-miss")
    ).strip("-") or "model-miss"
    decision_path = decisions_dir / f"{safe_id}.pm_model_miss_triage_decision.json"
    write_json(decision_path, output)
    run_state["model_miss_triage"] = {
        "decision": decision_value,
        "repair_authorized": output["repair_authorized"],
        "decision_path": project_relative(project_root, decision_path),
        "decision_hash": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
        "defect_or_blocker_id": decision.get("defect_or_blocker_id"),
        "checked_officer_reports": checked_reports,
    }
    run_state["flags"]["model_miss_triage_followup_request_pending"] = False
    if decision_value == "request_officer_model_miss_analysis":
        run_state["model_miss_triage_followup_request"] = {
            "schema_version": "flowpilot.model_miss_triage_followup_request.v1",
            "status": "awaiting_pm_role_work_request",
            "source_decision_path": project_relative(project_root, decision_path),
            "source_decision_hash": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
            "required_request_kind": "model_miss",
            "required_output_contract_id": "flowpilot.output_contract.flowguard_model_miss_report.v1",
            "suggested_to_roles": ["process_flowguard_officer", "product_flowguard_officer"],
            "required_event": PM_ROLE_WORK_REQUEST_EVENT,
            "reason": "model_miss_triage_followup_request",
            "created_at": utc_now(),
        }
        run_state["flags"]["model_miss_triage_followup_request_pending"] = True
    elif decision_value == "needs_evidence_before_modeling":
        run_state["model_miss_evidence_followup_request"] = {
            "schema_version": "flowpilot.model_miss_evidence_followup_request.v1",
            "status": "awaiting_pm_role_work_request",
            "source_decision_path": project_relative(project_root, decision_path),
            "source_decision_hash": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
            "required_request_kind": "evidence",
            "required_output_contract_id": None,
            "suggested_to_roles": sorted(PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES),
            "required_event": PM_ROLE_WORK_REQUEST_EVENT,
            "reason": "model_miss_evidence_followup_request",
            "created_at": utc_now(),
        }
        run_state["flags"]["model_miss_triage_followup_request_pending"] = True
    elif decision_value == "stop_for_user":
        run_state["model_miss_triage_controlled_stop"] = {
            "schema_version": "flowpilot.model_miss_triage_controlled_stop.v1",
            "status": "waiting_for_user",
            "source_decision_path": project_relative(project_root, decision_path),
            "source_decision_hash": hashlib.sha256(decision_path.read_bytes()).hexdigest(),
            "reason": "model_miss_triage_controlled_stop",
            "created_at": utc_now(),
        }
        run_state["flags"]["model_miss_triage_controlled_stop_recorded"] = True
    elif decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        run_state["model_miss_triage_followup_request"] = None
        run_state["model_miss_evidence_followup_request"] = None
        run_state["model_miss_triage_controlled_stop"] = None
    return decision_value


def _write_control_blocker_repair_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("control blocker repair decision requires decided_by_role=project_manager")
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict) or active.get("delivery_status") != "delivered":
        raise RouterError("control blocker repair decision requires a delivered active control blocker")
    blocker_id = str(decision.get("blocker_id") or "")
    if blocker_id != active.get("blocker_id"):
        raise RouterError("control blocker repair decision must reference the active blocker_id")
    allowed_decisions = {
        "repair_completed",
        "repair_not_required",
        "resolved_by_followup_event",
        "continue_after_pm_review",
    }
    if decision.get("decision") not in allowed_decisions:
        raise RouterError("control blocker repair decision is not an allowed PM repair decision")
    prior_path_context_review = decision.get("prior_path_context_review")
    if not isinstance(prior_path_context_review, dict) or prior_path_context_review.get("reviewed") is not True:
        raise RouterError("control blocker repair decision requires prior_path_context_review.reviewed=true")
    source_paths = prior_path_context_review.get("source_paths")
    if not isinstance(source_paths, list):
        raise RouterError("control blocker repair decision requires prior_path_context_review.source_paths list")
    repair_action = str(decision.get("repair_action") or "").strip()
    if not repair_action:
        raise RouterError("control blocker repair decision requires repair_action")
    raw_rerun_target = decision.get("rerun_target")
    rerun_target = _control_resolution_event_name(raw_rerun_target)
    if not rerun_target:
        raise RouterError("control blocker repair decision rerun_target must name a registered external event")
    if rerun_target == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        raise RouterError("control blocker repair decision rerun_target must name a corrected follow-up event, not the PM decision event")
    rerun_target = _validated_external_event_names(
        [rerun_target],
        context="control blocker repair decision rerun_target",
        allow_pm_repair_event=False,
    )[0]
    repair_transaction_request = decision.get("repair_transaction")
    if not isinstance(repair_transaction_request, dict):
        raise RouterError("control blocker repair decision requires repair_transaction")
    requested_plan_kind = str(repair_transaction_request.get("plan_kind") or "").strip()
    if requested_plan_kind not in {"event_replay", "packet_reissue", "route_mutation"}:
        raise RouterError("repair_transaction.plan_kind must be event_replay, packet_reissue, or route_mutation")
    blockers = decision.get("blockers")
    if not isinstance(blockers, list):
        raise RouterError("control blocker repair decision requires blockers list")
    contract_self_check = decision.get("contract_self_check")
    if not isinstance(contract_self_check, dict):
        raise RouterError("control blocker repair decision requires contract_self_check")
    if contract_self_check.get("all_required_fields_present") is not True:
        raise RouterError("control blocker repair decision requires contract_self_check.all_required_fields_present=true")
    if contract_self_check.get("exact_field_names_used") is not True:
        raise RouterError("control blocker repair decision requires contract_self_check.exact_field_names_used=true")
    outcome_table = _repair_outcome_table(rerun_target)
    allowed_resolution_events = _validated_external_event_names(
        _repair_outcome_events(outcome_table),
        context="control blocker repair outcome table",
        allow_pm_repair_event=False,
    )
    transaction_id = _repair_transaction_id(blocker_id)
    packet_generation_id = f"{transaction_id}-gen-001"
    packet_specs, packet_spec_source = _repair_packet_specs_from_decision(
        project_root,
        run_root,
        decision,
        rerun_target=rerun_target,
    )
    if packet_specs and requested_plan_kind != "packet_reissue":
        raise RouterError("repair transaction with replacement packets requires plan_kind=packet_reissue")
    if requested_plan_kind == "packet_reissue" and not packet_specs:
        raise RouterError("packet_reissue repair transaction requires replacement packets or a packet spec path")
    plan_kind = requested_plan_kind
    if packet_specs and rerun_target not in {
        "router_direct_material_scan_dispatch_recheck_passed",
        "reviewer_allows_material_scan_dispatch",
    }:
        raise RouterError("repair transaction packet reissue is currently supported only for material scan dispatch")
    output = {
        "schema_version": "flowpilot.control_blocker_repair_decision.v1",
        "run_id": run_state["run_id"],
        "blocker_id": blocker_id,
        "decided_by_role": "project_manager",
        "decision": decision["decision"],
        "repair_transaction_id": transaction_id,
        "prior_path_context_review": prior_path_context_review,
        "repair_action": repair_action,
        "rerun_target": rerun_target,
        "outcome_table": outcome_table,
        "blockers": blockers,
        "contract_self_check": contract_self_check,
        "recorded_at": utc_now(),
        **_role_output_envelope_record(decision),
    }
    decision_path = run_root / "control_blocks" / f"{blocker_id}.pm_repair_decision.json"
    write_json(decision_path, output)
    generation_commit: dict[str, Any] | None = None
    if packet_specs:
        generation_commit = _commit_material_scan_repair_generation(
            project_root,
            run_root,
            run_state,
            transaction_id=transaction_id,
            packet_generation_id=packet_generation_id,
            packet_specs=packet_specs,
        )
        _set_pre_route_frontier_phase(run_root, str(run_state["run_id"]), "material_scan")
        run_state["phase"] = "material_scan"
    transaction = {
        "schema_version": REPAIR_TRANSACTION_SCHEMA,
        "transaction_id": transaction_id,
        "run_id": run_state["run_id"],
        "blocker_id": blocker_id,
        "originating_event": active.get("originating_event"),
        "originating_action_type": active.get("originating_action_type"),
        "status": "committed",
        "plan_kind": plan_kind,
        "packet_generation_id": packet_generation_id if generation_commit else None,
        "packet_spec_source": packet_spec_source,
        "generation_commit": generation_commit,
        "pm_repair_decision_path": project_relative(project_root, decision_path),
        "rerun_target": rerun_target,
        "outcome_table": outcome_table,
        "allowed_resolution_events": allowed_resolution_events,
        "opened_at": output["recorded_at"],
        "committed_at": utc_now(),
    }
    write_json(_repair_transaction_path(run_root, transaction_id), transaction)
    active_path = resolve_project_path(project_root, str(active.get("blocker_artifact_path") or ""))
    decision_rel = project_relative(project_root, decision_path)
    decision_hash = hashlib.sha256(decision_path.read_bytes()).hexdigest()
    if active_path.exists():
        record = read_json(active_path)
        record["pm_repair_decision_status"] = "recorded"
        record["pm_repair_decision_path"] = decision_rel
        record["pm_repair_decision_hash"] = decision_hash
        record["pm_repair_rerun_target"] = rerun_target
        record["repair_transaction_id"] = transaction_id
        record["repair_transaction_path"] = project_relative(project_root, _repair_transaction_path(run_root, transaction_id))
        record["repair_outcome_table"] = outcome_table
        record["allowed_resolution_events"] = allowed_resolution_events
        record["resolution_status"] = None
        write_json(active_path, record)
    active["pm_repair_decision_status"] = "recorded"
    active["pm_repair_decision_path"] = decision_rel
    active["pm_repair_decision_hash"] = decision_hash
    active["pm_repair_rerun_target"] = rerun_target
    active["repair_transaction_id"] = transaction_id
    active["repair_transaction_path"] = project_relative(project_root, _repair_transaction_path(run_root, transaction_id))
    active["repair_outcome_table"] = outcome_table
    active["allowed_resolution_events"] = allowed_resolution_events
    _sync_control_plane_indexes(project_root, run_root, run_state)


def _gate_decision_issue(field: str, message: str, owner: str = "gate_owner") -> dict[str, str]:
    return {"field": field, "message": message, "owner": owner}


def _gate_decision_safe_id(raw: str) -> str:
    chars: list[str] = []
    for char in raw.strip().lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != "-":
            chars.append("-")
    safe = "".join(chars).strip("-")
    return safe[:96] or "gate-decision"


def _gate_decision_issues(project_root: Path, decision: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not isinstance(decision, dict):
        return [_gate_decision_issue("gate_decision", "GateDecision must be a JSON object")]
    for field in GATE_DECISION_REQUIRED_FIELDS:
        if field not in decision or decision.get(field) in (None, ""):
            issues.append(_gate_decision_issue(field, "missing required GateDecision field"))
    if decision.get("gate_decision_version") != GATE_DECISION_SCHEMA:
        issues.append(_gate_decision_issue("gate_decision_version", f"must equal {GATE_DECISION_SCHEMA}"))
    enum_specs = (
        ("gate_kind", GATE_DECISION_ALLOWED_KINDS),
        ("owner_role", GATE_DECISION_ALLOWED_OWNER_ROLES),
        ("risk_type", GATE_DECISION_ALLOWED_RISKS),
        ("gate_strength", GATE_DECISION_ALLOWED_STRENGTHS),
        ("decision", GATE_DECISION_ALLOWED_DECISIONS),
        ("next_action", GATE_DECISION_ALLOWED_NEXT_ACTIONS),
    )
    for field, allowed in enum_specs:
        if field in decision and decision.get(field) not in allowed:
            issues.append(_gate_decision_issue(field, f"unsupported value: {decision.get(field)}"))
    leaked_overreach = sorted(GATE_DECISION_SEMANTIC_OVERREACH_FIELDS & set(decision))
    if leaked_overreach:
        issues.append(
            _gate_decision_issue(
                ",".join(leaked_overreach),
                "router may record only mechanical GateDecision conformance, not semantic sufficiency",
                "flowpilot_router",
            )
        )
    if "blocking" in decision and not isinstance(decision.get("blocking"), bool):
        issues.append(_gate_decision_issue("blocking", "must be a boolean"))
    required_evidence = decision.get("required_evidence")
    if not isinstance(required_evidence, list) or any(not isinstance(item, str) for item in required_evidence):
        issues.append(_gate_decision_issue("required_evidence", "must be a list of strings"))
    evidence_refs = decision.get("evidence_refs")
    if not isinstance(evidence_refs, list):
        issues.append(_gate_decision_issue("evidence_refs", "must be a list of evidence reference objects"))
        evidence_refs = []
    reason = str(decision.get("reason") or "").strip()
    if not reason:
        issues.append(_gate_decision_issue("reason", "GateDecision requires a concrete reason"))
    contract_self_check = decision.get("contract_self_check")
    if contract_self_check is not None:
        if not isinstance(contract_self_check, dict):
            issues.append(_gate_decision_issue("contract_self_check", "must be an object when provided"))
        else:
            if contract_self_check.get("all_required_fields_present") is not True:
                issues.append(_gate_decision_issue("contract_self_check.all_required_fields_present", "must be true"))
            if contract_self_check.get("exact_field_names_used") is not True:
                issues.append(_gate_decision_issue("contract_self_check.exact_field_names_used", "must be true"))
    gate_strength = decision.get("gate_strength")
    gate_decision = decision.get("decision")
    blocking = decision.get("blocking")
    next_action = decision.get("next_action")
    if gate_decision == "pass":
        if blocking is not False:
            issues.append(_gate_decision_issue("blocking", "pass decisions must not be blocking"))
        if next_action != "continue":
            issues.append(_gate_decision_issue("next_action", "pass decisions must route to continue"))
        if gate_strength == "hard" and not evidence_refs:
            issues.append(_gate_decision_issue("evidence_refs", "hard pass decisions require evidence references"))
    elif gate_decision == "block":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "block decisions must be blocking"))
    elif gate_decision in {"waive", "skip"}:
        if blocking is not False:
            issues.append(_gate_decision_issue("blocking", "waive and skip decisions must not be blocking"))
        if next_action != "continue":
            issues.append(_gate_decision_issue("next_action", "waive and skip decisions must route to continue"))
    elif gate_decision == "repair_local":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "repair_local decisions must be blocking until repaired"))
        if next_action not in {"local_repair", "reviewer_recheck", "collect_evidence"}:
            issues.append(_gate_decision_issue("next_action", "repair_local requires a local repair, recheck, or evidence collection action"))
    elif gate_decision == "mutate_route":
        if blocking is not True:
            issues.append(_gate_decision_issue("blocking", "mutate_route decisions must be blocking until route mutation"))
        if next_action != "route_mutation":
            issues.append(_gate_decision_issue("next_action", "mutate_route decisions must route to route_mutation"))
    if gate_strength == "advisory" and blocking is True:
        issues.append(_gate_decision_issue("blocking", "advisory gates cannot block"))
    if gate_strength == "skip_with_reason" and gate_decision not in {"skip", "waive"}:
        issues.append(_gate_decision_issue("decision", "skip_with_reason gates require skip or waive decision"))
    for index, evidence in enumerate(evidence_refs):
        prefix = f"evidence_refs[{index}]"
        if not isinstance(evidence, dict):
            issues.append(_gate_decision_issue(prefix, "evidence reference must be an object"))
            continue
        kind = evidence.get("kind")
        if kind not in GATE_DECISION_ALLOWED_EVIDENCE_KINDS:
            issues.append(_gate_decision_issue(f"{prefix}.kind", f"unsupported evidence kind: {kind}"))
            continue
        summary = str(evidence.get("summary") or "").strip()
        if not summary:
            issues.append(_gate_decision_issue(f"{prefix}.summary", "evidence reference requires summary"))
        if kind == "none":
            continue
        raw_path = str(evidence.get("path") or "").strip()
        raw_hash = str(evidence.get("hash") or "").strip()
        if not raw_path:
            issues.append(_gate_decision_issue(f"{prefix}.path", "non-none evidence requires path"))
            continue
        if not raw_hash:
            issues.append(_gate_decision_issue(f"{prefix}.hash", "non-none evidence requires hash"))
            continue
        evidence_path = resolve_project_path(project_root, raw_path)
        try:
            project_relative(project_root, evidence_path)
        except RouterError:
            issues.append(_gate_decision_issue(f"{prefix}.path", "evidence path must stay inside the project root"))
            continue
        if not evidence_path.exists() or not evidence_path.is_file():
            issues.append(_gate_decision_issue(f"{prefix}.path", "evidence path is missing"))
            continue
        actual_hash = packet_runtime.sha256_file(evidence_path)
        if raw_hash != actual_hash:
            issues.append(_gate_decision_issue(f"{prefix}.hash", "evidence hash does not match path content"))
    return issues


def _validate_gate_decision(project_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    issues = _gate_decision_issues(project_root, decision)
    if issues:
        first = issues[0]
        raise RouterError(f"GateDecision mechanical validation failed: {first['field']}: {first['message']}")
    return decision


def _gate_decision_record_path(run_root: Path, gate_id: str) -> Path:
    return run_root / "gate_decisions" / f"{_gate_decision_safe_id(gate_id)}.json"


def _gate_decision_summary(project_root: Path, record_path: Path, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": str(decision["gate_id"]),
        "gate_kind": decision["gate_kind"],
        "owner_role": decision["owner_role"],
        "risk_type": decision["risk_type"],
        "gate_strength": decision["gate_strength"],
        "decision": decision["decision"],
        "blocking": decision["blocking"],
        "next_action": decision["next_action"],
        "decision_path": project_relative(project_root, record_path),
    }


def _write_gate_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    _validate_gate_decision(project_root, decision)
    gate_id = str(decision["gate_id"])
    record_path = _gate_decision_record_path(run_root, gate_id)
    record = {
        "schema_version": GATE_DECISION_RECORD_SCHEMA,
        "run_id": run_state["run_id"],
        "recorded_at": utc_now(),
        "recorded_by_event": GATE_DECISION_EVENT,
        "gate_decision": decision,
        **_role_output_envelope_record(decision),
    }
    write_json(record_path, record)
    summary = _gate_decision_summary(project_root, record_path, decision)
    decisions = run_state.setdefault("gate_decisions", [])
    if not isinstance(decisions, list):
        decisions = []
        run_state["gate_decisions"] = decisions
    decisions[:] = [item for item in decisions if item.get("gate_id") != gate_id]
    decisions.append(summary)
    ledger_path = run_root / "gate_decisions" / "gate_decision_ledger.json"
    write_json(
        ledger_path,
        {
            "schema_version": GATE_DECISION_LEDGER_SCHEMA,
            "run_id": run_state["run_id"],
            "updated_at": utc_now(),
            "gate_decision_count": len(decisions),
            "gate_decisions": decisions,
        },
    )


def _control_blocker_allows_resolution_event(record: dict[str, Any], event: str) -> bool:
    if record.get("handling_lane") in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return False
    raw_events = record.get("allowed_resolution_events")
    if isinstance(raw_events, list) and raw_events:
        allowed_events = {name for item in raw_events if (name := _control_resolution_event_name(item))}
        return event in allowed_events
    if record.get("handling_lane") == "control_plane_reissue":
        return event == record.get("originating_event")
    return event in EXTERNAL_EVENTS


def _control_resolution_event_name(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("event", "corrected_followup_event", "event_name"):
            name = str(value.get(key) or "").strip()
            if name:
                return _control_resolution_event_name(name)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text in EXTERNAL_EVENTS:
        return text
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return None
    return _control_resolution_event_name(parsed)


def _resolve_delivered_control_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    resolved_by_event: str,
    from_already_recorded_event: bool = False,
) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict) or active.get("delivery_status") != "delivered":
        return None
    record = dict(active)
    artifact_rel = str(active.get("blocker_artifact_path") or "")
    artifact_path: Path | None = None
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            record = read_json(artifact_path)
    if from_already_recorded_event:
        lane = record.get("handling_lane")
        pm_repair_recorded = (
            lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
            and record.get("pm_repair_decision_status") == "recorded"
        )
        if lane != "control_plane_reissue" and not pm_repair_recorded:
            return None
    if not _control_blocker_allows_resolution_event(record, resolved_by_event):
        return None
    if artifact_path and artifact_path.exists():
        resolved_at = utc_now()
        record["resolution_status"] = "accepted_followup_event_recorded"
        record["resolved_by_event"] = resolved_by_event
        record["resolved_at"] = resolved_at
        write_json(artifact_path, record)
    resolved = dict(active)
    resolved["resolution_status"] = "accepted_followup_event_recorded"
    resolved["resolved_by_event"] = resolved_by_event
    resolved["resolved_at"] = record.get("resolved_at") or utc_now()
    run_state.setdefault("resolved_control_blockers", []).append(resolved)
    run_state["active_control_blocker"] = None
    run_state["latest_control_blocker_path"] = None
    append_history(
        run_state,
        "router_resolved_control_blocker",
        {"blocker_id": resolved.get("blocker_id"), "resolved_by_event": resolved_by_event},
    )
    _sync_control_plane_indexes(project_root, run_root, run_state)
    return resolved


def _terminal_lifecycle_mode(run_state: dict[str, Any]) -> str | None:
    status = str(run_state.get("status") or "")
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    if status == "cancelled_by_user" or flags.get("run_cancelled_by_user"):
        return "cancelled_by_user"
    if status == "stopped_by_user" or flags.get("run_stopped_by_user"):
        return "stopped_by_user"
    if status == "protocol_dead_end" or flags.get("startup_protocol_dead_end_declared"):
        return "protocol_dead_end"
    if status in {"closed", "completed"} or flags.get("terminal_closure_approved"):
        return "closed"
    return None


def _lifecycle_record_path(run_root: Path) -> Path:
    return run_root / "lifecycle" / "run_lifecycle.json"


def _terminal_closure_suite_is_closed(run_root: Path) -> bool:
    closure = read_json_if_exists(run_root / "closure" / "terminal_closure_suite.json")
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    if not isinstance(closure, dict) or not isinstance(frontier, dict):
        return False
    return closure.get("status") == "closed" and frontier.get("status") == "closed"


def _clear_active_control_blocker_for_terminal_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    cleared_at: str,
) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return None
    blocker_id = str(active.get("blocker_id") or "")
    if not blocker_id:
        run_state["active_control_blocker"] = None
        run_state["latest_control_blocker_path"] = None
        return {"authority": "control_blocker", "status": "cleared_missing_blocker_id"}
    resolved = dict(active)
    resolved["resolution_status"] = "superseded_by_terminal_lifecycle"
    resolved["resolved_by_event"] = event
    resolved["resolved_at"] = cleared_at
    resolved["terminal_lifecycle_status"] = mode
    existing = run_state.get("resolved_control_blockers")
    if not isinstance(existing, list):
        existing = []
        run_state["resolved_control_blockers"] = existing
    if not any(isinstance(item, dict) and item.get("blocker_id") == blocker_id for item in existing):
        existing.append(resolved)
    artifact_path = resolve_project_path(project_root, str(active.get("blocker_artifact_path") or ""))
    if artifact_path.exists():
        record = read_json(artifact_path)
        record["resolution_status"] = "superseded_by_terminal_lifecycle"
        record["resolved_by_event"] = event
        record["resolved_at"] = cleared_at
        record["terminal_lifecycle_status"] = mode
        write_json(artifact_path, record)
    run_state["active_control_blocker"] = None
    run_state["latest_control_blocker_path"] = None
    _sync_control_plane_indexes(project_root, run_root, run_state)
    return {
        "authority": "control_blocker",
        "blocker_id": blocker_id,
        "resolution_status": "superseded_by_terminal_lifecycle",
    }


def _write_run_lifecycle_request(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    mode = "cancelled_by_user" if event == "user_requests_run_cancel" else "stopped_by_user"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    cleanup_receipts = payload.get("cleanup_receipts") if isinstance(payload.get("cleanup_receipts"), list) else []
    record = {
        "schema_version": "flowpilot.run_lifecycle.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "requested_by": str(payload.get("requested_by") or "user"),
        "request_event": event,
        "reason": payload.get("reason"),
        "previous_pending_action": previous_pending,
        "active_control_blocker_at_request": active_blocker,
        "cleanup_receipts": cleanup_receipts,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "requested_at": utc_now(),
    }
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event=event)
    record["cleanup_receipts"] = cleanup_receipts + reconciliation["cleanup_receipts"]
    record["reconciliation"] = reconciliation
    write_json(_lifecycle_record_path(run_root), record)
    append_history(run_state, f"run_{mode}", {"event": event, "lifecycle_path": project_relative(project_root, _lifecycle_record_path(run_root))})

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=event)


def _reconcile_terminal_lifecycle_authorities(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    reconciled_at = utc_now()
    receipts: list[dict[str, Any]] = []
    source_paths: dict[str, str] = {}

    continuation_path = _continuation_binding_path(run_root)
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        source_paths["continuation_binding"] = project_relative(project_root, continuation_path)
        previous_heartbeat_active = bool(continuation.get("heartbeat_active"))
        automation_id = str(continuation.get("host_automation_id") or "")
        automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml" if automation_id else None
        automation_exists = bool(automation_path and automation_path.exists())
        if automation_id and not automation_exists:
            cleanup_status = "missing_verified"
        elif automation_id and previous_heartbeat_active:
            cleanup_status = "external_cleanup_may_be_required"
        else:
            cleanup_status = "inactive_verified"
        continuation["heartbeat_active"] = False
        continuation["lifecycle_status"] = mode
        continuation["terminal_event"] = event
        continuation["terminal_reconciled_at"] = reconciled_at
        continuation["host_automation_cleanup_status"] = cleanup_status
        continuation["host_automation_toml_exists"] = automation_exists if automation_id else None
        continuation["host_automation_checked_path"] = str(automation_path) if automation_path else None
        write_json(continuation_path, continuation)
        receipts.append(
            {
                "authority": "continuation_binding",
                "path": project_relative(project_root, continuation_path),
                "previous_heartbeat_active": previous_heartbeat_active,
                "heartbeat_active": False,
                "host_automation_cleanup_status": continuation["host_automation_cleanup_status"],
                "host_automation_toml_exists": continuation["host_automation_toml_exists"],
            }
        )

    crew_path = run_root / "crew_ledger.json"
    if crew_path.exists():
        crew = read_json(crew_path)
        source_paths["crew_ledger"] = project_relative(project_root, crew_path)
        role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
        live_before = sum(1 for slot in role_slots if isinstance(slot, dict) and str(slot.get("status") or "").startswith("live_"))
        for slot in role_slots:
            if isinstance(slot, dict):
                slot["status"] = "stopped_with_run"
                slot["live_agent_active"] = False
                slot["stopped_at"] = reconciled_at
        crew["lifecycle_status"] = mode
        crew["terminal_reconciled_at"] = reconciled_at
        write_json(crew_path, crew)
        receipts.append(
            {
                "authority": "crew_ledger",
                "path": project_relative(project_root, crew_path),
                "live_role_slots_before": live_before,
                "live_role_slots_after": 0,
            }
        )

    packet_ledger_path = run_root / "packet_ledger.json"
    if packet_ledger_path.exists():
        packet_ledger = read_json(packet_ledger_path)
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger_path)
        previous_status = packet_ledger.get("active_packet_status")
        previous_holder = packet_ledger.get("active_packet_holder")
        packet_ledger["active_packet_status"] = mode
        packet_ledger["active_packet_holder"] = "controller"
        packet_ledger["terminal_lifecycle"] = {
            "status": mode,
            "event": event,
            "previous_active_packet_status": previous_status,
            "previous_active_packet_holder": previous_holder,
            "controller_may_continue_packet_loop": False,
            "reconciled_at": reconciled_at,
        }
        packet_ledger["updated_at"] = reconciled_at
        write_json(packet_ledger_path, packet_ledger)
        receipts.append(
            {
                "authority": "packet_ledger",
                "path": project_relative(project_root, packet_ledger_path),
                "previous_active_packet_status": previous_status,
                "active_packet_status": mode,
            }
        )

    frontier_path = run_root / "execution_frontier.json"
    if frontier_path.exists():
        frontier = read_json(frontier_path)
        source_paths["execution_frontier"] = project_relative(project_root, frontier_path)
        previous_status = frontier.get("status")
        frontier["status"] = mode
        frontier["phase"] = "terminal"
        frontier["terminal"] = True
        frontier["terminal_event"] = event
        frontier["updated_at"] = reconciled_at
        frontier["source"] = event
        write_json(frontier_path, frontier)
        receipts.append(
            {
                "authority": "execution_frontier",
                "path": project_relative(project_root, frontier_path),
                "previous_status": previous_status,
                "status": mode,
            }
        )

    blocker_receipt = _clear_active_control_blocker_for_terminal_lifecycle(
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
        cleared_at=reconciled_at,
    )
    if blocker_receipt:
        receipts.append(blocker_receipt)

    report = {
        "schema_version": "flowpilot.terminal_lifecycle_reconciliation.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "cleanup_receipts": receipts,
        "source_paths": source_paths,
        "reconciled_at": reconciled_at,
    }
    write_json(run_root / "lifecycle" / "terminal_reconciliation.json", report)
    report["reconciliation_path"] = project_relative(project_root, run_root / "lifecycle" / "terminal_reconciliation.json")
    return report


def _write_protocol_dead_end_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    dead_end_path: Path,
    reason: str | None,
) -> None:
    mode = "protocol_dead_end"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    write_json(
        _lifecycle_record_path(run_root),
        {
            "schema_version": "flowpilot.run_lifecycle.v1",
            "run_id": run_state.get("run_id"),
            "status": mode,
            "requested_by": "project_manager",
            "request_event": "pm_declares_startup_protocol_dead_end",
            "reason": reason,
            "protocol_dead_end_path": project_relative(project_root, dead_end_path),
            "previous_pending_action": previous_pending,
            "active_control_blocker_at_request": active_blocker,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "requested_at": utc_now(),
        },
    )
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    append_history(
        run_state,
        "run_protocol_dead_end",
        {"protocol_dead_end_path": project_relative(project_root, dead_end_path)},
    )

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)


def _run_lifecycle_terminal_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    mode = _terminal_lifecycle_mode(run_state)
    if not mode:
        return None
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(
        action_type="run_lifecycle_terminal",
        actor="controller",
        label=f"controller_observes_{mode}",
        summary="This FlowPilot run is terminal; no further route work is authorized.",
        allowed_reads=[lifecycle_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        extra={
            "run_lifecycle_status": mode,
            "terminal_for_route": True,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "allowed_external_events": ["user_requests_run_stop", "user_requests_run_cancel"],
        },
    )


def _try_write_control_blocker_for_exception(
    project_root: Path,
    *,
    source: str,
    error_message: str,
    event: str | None = None,
    action_type: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not _should_materialize_control_blocker(
        error_message,
        event=event,
        action_type=action_type,
        payload=payload,
    ):
        return None
    try:
        bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            return None
        return _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source=source,
            error_message=error_message,
            event=event,
            action_type=action_type,
            payload=payload,
        )
    except Exception:
        try:
            fallback = {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
                "recorded_at": utc_now(),
            }
            flowpilot_root = project_root / ".flowpilot"
            failure_path = flowpilot_root / "control_blocker_materialization_failures.jsonl"
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            with failure_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(fallback, sort_keys=True) + "\n")
            fallback["fallback_diagnostic_path"] = project_relative(project_root, failure_path)
            return fallback
        except Exception:
            return {
                "schema_version": "flowpilot.control_blocker_materialization_failure.v1",
                "materialization_failed": True,
                "source": source,
                "error_message": error_message,
                "event": event,
                "action_type": action_type,
            }


def _next_boot_action(state: dict[str, Any]) -> dict[str, Any] | None:
    if not state.get("router_loaded"):
        return {
            "action_type": "load_router",
            "flag": "router_loaded",
            "label": "bootloader_router_loaded",
            "summary": "Load the FlowPilot router and initialize bootstrap state.",
            "actor": "bootloader",
        }
    for action in BOOT_ACTIONS:
        if not state["flags"].get(action["flag"]):
            return action
    return None


def compute_bootloader_action(project_root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    if state.get("pending_action"):
        return state["pending_action"]
    boot_action = _next_boot_action(state)
    if boot_action is None:
        return None
    bootstrap_rel = project_relative(project_root, bootstrap_state_path(project_root, state))
    extra_fields = {
        "requires_user": bool(boot_action.get("requires_user", False)),
        "terminal_for_turn": bool(boot_action.get("terminal_for_turn", False)),
        "requires_payload": boot_action.get("requires_payload"),
        "questions": boot_action.get("questions", []),
        "postcondition": boot_action["flag"],
    }
    if boot_action["action_type"] == "emit_startup_banner":
        extra_fields.update(_startup_banner_display())
    if boot_action["action_type"] == "record_startup_answers":
        extra_fields["payload_contract"] = _startup_answers_payload_contract()
    if boot_action["action_type"] == "start_role_slots":
        extra_fields.update(_role_spawn_action_extra(state))
    action = make_action(
        action_type=str(boot_action["action_type"]),
        actor=str(boot_action["actor"]),
        label=str(boot_action["label"]),
        summary=str(boot_action["summary"]),
        allowed_reads=[bootstrap_rel],
        allowed_writes=[bootstrap_rel],
        card_id=boot_action.get("card_id"),
        extra=extra_fields,
    )
    state["pending_action"] = action
    if state.get("router_loaded"):
        state["router_action_requests"] = int(state.get("router_action_requests", 0)) + 1
    append_history(state, "router_computed_next_bootloader_action", {"action_type": action["action_type"]})
    save_bootstrap_state(project_root, state)
    return action


def _ensure_pending(state: dict[str, Any], action_type: str) -> dict[str, Any]:
    pending = state.get("pending_action")
    if not isinstance(pending, dict):
        raise RouterError("no pending router action; run 'next' before applying an action")
    if pending.get("action_type") != action_type:
        raise RouterError(f"pending action is {pending.get('action_type')!r}, not {action_type!r}")
    return pending


def _set_boot_flag(project_root: Path, state: dict[str, Any], flag: str, label: str, details: dict[str, Any] | None = None) -> None:
    if flag == "router_loaded":
        state["router_loaded"] = True
        state["status"] = "running"
    else:
        state["flags"][flag] = True
        state["bootloader_actions"] = int(state.get("bootloader_actions", 0)) + 1
    state["pending_action"] = None
    append_history(state, label, details)
    save_bootstrap_state(project_root, state)


def _normalize_startup_question_stop_boundary(state: dict[str, Any]) -> bool:
    flags = state.setdefault("flags", {})
    if not flags.get("startup_questions_asked"):
        return False
    if flags.get("startup_answers_recorded") or state.get("startup_answers"):
        return False
    changed = False
    if not flags.get("startup_state_written_awaiting_answers"):
        flags["startup_state_written_awaiting_answers"] = True
        changed = True
    if not flags.get("dialog_stopped_for_answers"):
        flags["dialog_stopped_for_answers"] = True
        changed = True
    if state.get("startup_state") != "awaiting_answers_stopped":
        state["startup_state"] = "awaiting_answers_stopped"
        changed = True
    pending = state.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") in {
        "write_startup_awaiting_answers_state",
        "stop_for_startup_answers",
    }:
        state["pending_action"] = None
        append_history(
            state,
            "startup_question_stop_boundary_normalized",
            {"cleared_pending_action": pending.get("action_type")},
        )
        changed = True
    return changed


def _validate_startup_answer_interpretation(payload: dict[str, Any], answers: dict[str, str]) -> dict[str, Any] | None:
    provenance = answers.get("provenance")
    if provenance == STARTUP_ANSWER_PROVENANCE:
        if payload.get("startup_answer_interpretation") is not None:
            raise RouterError("startup_answer_interpretation is only allowed with ai_interpreted_from_explicit_user_reply provenance")
        return None
    receipt = payload.get("startup_answer_interpretation")
    if not isinstance(receipt, dict):
        raise RouterError("AI-interpreted startup answers require payload.startup_answer_interpretation receipt")
    if receipt.get("schema_version") != STARTUP_ANSWER_INTERPRETATION_SCHEMA:
        raise RouterError(f"startup_answer_interpretation requires schema_version={STARTUP_ANSWER_INTERPRETATION_SCHEMA}")
    raw_text = receipt.get("raw_user_reply_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RouterError("startup_answer_interpretation.raw_user_reply_text must preserve the user's non-empty reply")
    interpreted_by = receipt.get("interpreted_by")
    if interpreted_by not in {"controller", "bootloader"}:
        raise RouterError("startup_answer_interpretation.interpreted_by must be controller or bootloader")
    if receipt.get("interpretation_provenance") != STARTUP_ANSWER_INTERPRETATION_PROVENANCE:
        raise RouterError("startup_answer_interpretation.interpretation_provenance must match the AI-interpreted startup answer provenance")
    if receipt.get("ambiguity_status") != "none":
        raise RouterError("ambiguous startup answers must be returned to the user instead of applied")
    interpreted_answers = receipt.get("interpreted_answers")
    if not isinstance(interpreted_answers, dict):
        raise RouterError("startup_answer_interpretation.interpreted_answers must be an object")
    expected = {key: answers[key] for key in STARTUP_ANSWER_ENUMS}
    got = {key: interpreted_answers.get(key) for key in STARTUP_ANSWER_ENUMS}
    if got != expected:
        raise RouterError("startup_answer_interpretation.interpreted_answers must match payload.startup_answers")
    allowed_keys = {
        "schema_version",
        "raw_user_reply_text",
        "interpreted_by",
        "interpretation_provenance",
        "ambiguity_status",
        "interpreted_answers",
        "reviewer_must_check_raw_reply_alignment",
        "notes",
    }
    extra = sorted(set(receipt) - allowed_keys)
    if extra:
        raise RouterError(f"startup_answer_interpretation contains unsupported fields: {', '.join(extra)}")
    interpretation = {
        "schema_version": STARTUP_ANSWER_INTERPRETATION_SCHEMA,
        "raw_user_reply_text": raw_text.strip(),
        "interpreted_by": interpreted_by,
        "interpretation_provenance": STARTUP_ANSWER_INTERPRETATION_PROVENANCE,
        "ambiguity_status": "none",
        "interpreted_answers": expected,
        "notes": receipt.get("notes"),
        "recorded_at": utc_now(),
    }
    if "reviewer_must_check_raw_reply_alignment" in receipt:
        interpretation["reviewer_must_check_raw_reply_alignment"] = bool(receipt.get("reviewer_must_check_raw_reply_alignment"))
    return interpretation


def _validate_startup_answers(payload: dict[str, Any]) -> dict[str, str]:
    answers = payload.get("startup_answers")
    if not isinstance(answers, dict):
        raise RouterError("record_startup_answers requires payload.startup_answers object")
    provenance = answers.get("provenance")
    if provenance not in {STARTUP_ANSWER_PROVENANCE, STARTUP_ANSWER_INTERPRETATION_PROVENANCE}:
        raise RouterError("startup answers require provenance=explicit_user_reply or ai_interpreted_from_explicit_user_reply")
    allowed_keys = set(STARTUP_ANSWER_ENUMS) | {"provenance"}
    extra = sorted(set(answers) - allowed_keys)
    if extra:
        raise RouterError(f"startup answers contain unsupported fields: {', '.join(extra)}")
    validated: dict[str, str] = {}
    for answer_id, allowed_values in STARTUP_ANSWER_ENUMS.items():
        value = answers.get(answer_id)
        if not isinstance(value, str) or value not in allowed_values:
            allowed = ", ".join(sorted(allowed_values))
            raise RouterError(f"startup answer {answer_id} must be one of: {allowed}")
        validated[answer_id] = value
    validated["provenance"] = provenance
    _validate_startup_answer_interpretation(payload, validated)
    return validated


def _validate_user_request(payload: dict[str, Any]) -> dict[str, str]:
    request = payload.get("user_request")
    if not isinstance(request, dict):
        raise RouterError("record_user_request requires payload.user_request object")
    provenance = request.get("provenance")
    if provenance != USER_REQUEST_PROVENANCE:
        raise RouterError("user request requires provenance=explicit_user_request")
    text = request.get("text")
    if not isinstance(text, str) or not text.strip():
        raise RouterError("user_request.text must contain the exact non-empty user task")
    allowed_keys = {"text", "provenance", "source"}
    extra = sorted(set(request) - allowed_keys)
    if extra:
        raise RouterError(f"user request contains unsupported fields: {', '.join(extra)}")
    source = request.get("source") or "flowpilot_activation_or_user_reply"
    if not isinstance(source, str) or not source.strip():
        raise RouterError("user_request.source must be a non-empty string when supplied")
    return {
        "text": text.strip(),
        "provenance": USER_REQUEST_PROVENANCE,
        "source": source.strip(),
    }


def _display_text_hash(display_text: str) -> str:
    return hashlib.sha256(display_text.encode("utf-8")).hexdigest()


def _user_dialog_display_gate(
    fields: dict[str, Any],
    *,
    display_kind: str,
    display_text: str,
) -> dict[str, Any]:
    gated = dict(fields)
    gated.update(
        {
            "display_kind": display_kind,
            "display_text_sha256": _display_text_hash(display_text),
            "requires_payload": "display_confirmation",
            "requires_user_dialog_display_confirmation": True,
            "required_render_target": DISPLAY_CONFIRMATION_TARGET,
            "display_confirmation_schema": DISPLAY_CONFIRMATION_SCHEMA,
        }
    )
    return gated


def _validate_display_confirmation(
    payload: dict[str, Any],
    *,
    action_type: str,
    display_kind: str,
    display_text: str,
) -> dict[str, Any]:
    confirmation = payload.get("display_confirmation")
    if not isinstance(confirmation, dict):
        raise RouterError(
            f"{action_type} requires payload.display_confirmation before apply; "
            "render display_text in the user dialog first"
        )
    if confirmation.get("provenance") != DISPLAY_CONFIRMATION_PROVENANCE:
        raise RouterError(
            f"{action_type} display_confirmation requires provenance={DISPLAY_CONFIRMATION_PROVENANCE}"
        )
    if confirmation.get("rendered_to") != DISPLAY_CONFIRMATION_TARGET:
        raise RouterError(
            f"{action_type} display_confirmation requires rendered_to={DISPLAY_CONFIRMATION_TARGET}"
        )
    if confirmation.get("action_type") != action_type:
        raise RouterError(f"{action_type} display_confirmation action_type mismatch")
    if confirmation.get("display_kind") != display_kind:
        raise RouterError(f"{action_type} display_confirmation display_kind mismatch")
    expected_hash = _display_text_hash(display_text)
    if confirmation.get("display_text_sha256") != expected_hash:
        raise RouterError(f"{action_type} display_confirmation display_text_sha256 mismatch")
    return {
        "schema_version": DISPLAY_CONFIRMATION_SCHEMA,
        "action_type": action_type,
        "display_kind": display_kind,
        "rendered_to": DISPLAY_CONFIRMATION_TARGET,
        "display_text_sha256": expected_hash,
        "provenance": DISPLAY_CONFIRMATION_PROVENANCE,
        "confirmed_at": utc_now(),
    }


def _display_confirmation_for_action(payload: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    payload = payload or {}
    display_text = action.get("display_text")
    if not isinstance(display_text, str) or not display_text:
        raise RouterError("display confirmation requested for action without display_text")
    display_kind = action.get("display_kind")
    if not isinstance(display_kind, str) or not display_kind:
        raise RouterError("display confirmation requested for action without display_kind")
    return _validate_display_confirmation(
        payload,
        action_type=str(action.get("action_type") or ""),
        display_kind=display_kind,
        display_text=display_text,
    )


def _append_user_dialog_display_ledger(project_root: Path, run_root: Path, record: dict[str, Any]) -> None:
    del project_root
    ledger_path = run_root / "display" / "user_dialog_display_ledger.json"
    ledger = read_json_if_exists(ledger_path) or {
        "schema_version": "flowpilot.user_dialog_display_ledger.v1",
        "run_id": run_root.name,
        "records": [],
    }
    ledger.setdefault("records", []).append(record)
    ledger["updated_at"] = utc_now()
    write_json(ledger_path, ledger)


def _display_plan_display_kind(plan_projection: dict[str, Any]) -> str:
    items = plan_projection.get("items") if isinstance(plan_projection.get("items"), list) else []
    if (
        len(items) == 1
        and isinstance(items[0], dict)
        and items[0].get("id") == "await_pm_route"
        and plan_projection.get("current_node_id") is None
    ):
        return "startup_waiting_state"
    return "route_map"


def _display_plan_chat_markdown(plan_projection: dict[str, Any], *, display_kind: str) -> str:
    title = "# FlowPilot Startup Status" if display_kind == "startup_waiting_state" else "# FlowPilot Route Map"
    lines = [title, ""]
    for item in plan_projection.get("items") or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or item.get("id") or "Route item")
        status = str(item.get("status") or "pending")
        lines.append(f"- {label} - {status}")
    if len(lines) == 2:
        lines.append("- Waiting for PM route - in_progress")
    active_path = plan_projection.get("active_path") if isinstance(plan_projection.get("active_path"), list) else []
    if active_path:
        path_labels = [
            str(item.get("label") or item.get("id"))
            for item in active_path
            if isinstance(item, dict) and (item.get("label") or item.get("id"))
        ]
        if path_labels:
            lines.extend(["", f"Current path: {' > '.join(path_labels)}"])
    progress = plan_projection.get("hidden_leaf_progress")
    if isinstance(progress, dict) and progress.get("total"):
        lines.append(f"Hidden leaf progress: {progress.get('completed', 0)}/{progress.get('total')} complete")
    return "\n".join(lines).rstrip() + "\n"


def _display_plan_user_dialog_fields(plan_projection: dict[str, Any]) -> dict[str, Any]:
    display_kind = _display_plan_display_kind(plan_projection)
    display_text = _display_plan_chat_markdown(plan_projection, display_kind=display_kind)
    display_label = "startup waiting state" if display_kind == "startup_waiting_state" else "route map"
    return _user_dialog_display_gate(
        {
            "display_text": display_text,
            "display_text_format": "markdown",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": f"Paste this exact {display_label} display_text in the user dialog before applying sync_display_plan; display_plan.json or host-plan replacement alone does not satisfy display.",
        },
        display_kind=display_kind,
        display_text=display_text,
    )


def _display_route_sign_user_dialog_fields(route_sign: dict[str, Any]) -> dict[str, Any]:
    display_text = route_sign.get("markdown")
    if not isinstance(display_text, str) or not display_text.strip():
        raise RouterError("route-sign display requires non-empty markdown")
    return _user_dialog_display_gate(
        {
            "display_text": display_text,
            "display_text_format": "markdown_mermaid",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact FlowPilot Route Sign Mermaid in the user dialog before applying sync_display_plan; display_plan.json or generated files alone do not satisfy display.",
        },
        display_kind="route_map",
        display_text=display_text,
    )


def _startup_banner_display() -> dict[str, Any]:
    banner_path = runtime_kit_source() / "cards" / "system" / "startup_banner.md"
    if not banner_path.exists():
        raise RouterError("startup banner card is missing")
    text = banner_path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if stripped.startswith("<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1"):
        end = stripped.find("-->")
        if end >= 0:
            stripped = stripped[end + 3 :].lstrip()
    display_text = stripped.rstrip() + "\n"
    return _user_dialog_display_gate(
        {
            "display_path": str(banner_path),
            "display_text": display_text,
            "display_text_format": "plain_text",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact startup banner display_text in the user dialog before applying emit_startup_banner; apply requires display_confirmation.rendered_to=user_dialog with matching display_text_sha256.",
        },
        display_kind="startup_banner",
        display_text=display_text,
    )


def _role_spawn_action_extra(state: dict[str, Any]) -> dict[str, Any]:
    answers = state.get("startup_answers") if isinstance(state.get("startup_answers"), dict) else {}
    mode = answers.get("background_agents")
    extra: dict[str, Any] = {
        "background_agents_mode": mode,
        "role_keys": list(CREW_ROLE_KEYS),
        "background_role_agent_model_policy": {
            "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
            "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
            "preferred_reasoning_effort": BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT,
            "inherit_foreground_model_allowed": False,
            "applies_to": [
                "startup_live_role_spawn",
                "heartbeat_resume_rehydration",
                "manual_resume_rehydration",
                "missing_role_replacement",
            ],
        },
    }
    if mode == "allow":
        extra.update(
            {
                "requires_payload": "role_agents",
                "requires_host_spawn": True,
                "spawn_policy": "spawn_all_six_fresh_current_task_agents_before_applying_action",
                "payload_contract": _role_slots_payload_contract(),
                "role_spawn_request": [
                    {
                        "role_key": role,
                        "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
                        "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
                        "preferred_reasoning_effort": BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT,
                        "inherit_foreground_model_allowed": False,
                        "spawn_result": ROLE_AGENT_SPAWN_RESULT,
                        "spawned_for_run_id": state.get("run_id"),
                        "spawned_after_startup_answers": True,
                    }
                    for role in CREW_ROLE_KEYS
                ],
            }
        )
    elif mode == "single-agent":
        extra.update(
            {
                "requires_host_spawn": False,
                "single_agent_continuity_authorized": True,
            }
        )
    return extra


def _normalize_role_agent_records(state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    answers = state.get("startup_answers") if isinstance(state.get("startup_answers"), dict) else {}
    mode = answers.get("background_agents")
    run_id = str(state.get("run_id") or "")
    if mode == "single-agent":
        return [
            {
                "role_key": role,
                "status": "single_agent_continuity_authorized",
                "agent_id": None,
                "spawn_result": "not_requested_single_agent_continuity",
                "fallback_authorized_by_startup_answer": True,
                "recorded_at": utc_now(),
            }
            for role in CREW_ROLE_KEYS
        ]
    if mode != "allow":
        raise RouterError("cannot start roles before background_agents startup answer is recorded")
    raw_records = payload.get("role_agents")
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError("start_role_slots requires payload.role_agents list or object")
    if payload.get("background_agents_capability_status") != "available":
        raise RouterError("live background roles require background_agents_capability_status=available")
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError("each role agent record must be an object")
        role = raw.get("role_key")
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f"role agent record has unsupported role_key: {role!r}")
        if role in records_by_role:
            raise RouterError(f"duplicate role agent record for {role}")
        agent_id = raw.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f"{role} requires a non-empty current agent_id")
        if raw.get("model_policy") != BACKGROUND_ROLE_MODEL_POLICY:
            raise RouterError(f"{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}")
        if raw.get("reasoning_effort_policy") != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
            raise RouterError(f"{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}")
        if raw.get("spawn_result") != ROLE_AGENT_SPAWN_RESULT:
            raise RouterError(f"{role} requires spawn_result=spawned_fresh_for_task")
        if raw.get("spawned_after_startup_answers") is not True:
            raise RouterError(f"{role} must be spawned_after_startup_answers=true")
        if raw.get("spawned_for_run_id") != run_id:
            raise RouterError(f"{role} must be spawned_for_run_id={run_id}")
        host_spawn_receipt = raw.get("host_spawn_receipt")
        if host_spawn_receipt is not None:
            if not isinstance(host_spawn_receipt, dict):
                raise RouterError(f"{role} host_spawn_receipt must be an object")
            if host_spawn_receipt.get("source_kind") != "host_receipt":
                raise RouterError(f"{role} host_spawn_receipt requires source_kind=host_receipt")
            if host_spawn_receipt.get("spawned_for_run_id") != run_id:
                raise RouterError(f"{role} host_spawn_receipt spawned_for_run_id mismatch")
            if host_spawn_receipt.get("role_key") != role:
                raise RouterError(f"{role} host_spawn_receipt role_key mismatch")
            if host_spawn_receipt.get("agent_id") != agent_id:
                raise RouterError(f"{role} host_spawn_receipt agent_id mismatch")
        records_by_role[str(role)] = {
            "role_key": str(role),
            "status": "live_agent_started",
            "agent_id": agent_id.strip(),
            "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
            "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
            "spawn_result": ROLE_AGENT_SPAWN_RESULT,
            "spawned_for_run_id": run_id,
            "spawned_after_startup_answers": True,
            **({"host_spawn_receipt": host_spawn_receipt} if isinstance(host_spawn_receipt, dict) else {}),
            "recorded_at": utc_now(),
        }
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]


def _latest_resume_tick_id(run_state: dict[str, Any]) -> str:
    ticks = run_state.get("heartbeat_ticks") if isinstance(run_state.get("heartbeat_ticks"), list) else []
    for tick in reversed(ticks):
        if isinstance(tick, dict) and tick.get("tick_id"):
            return str(tick["tick_id"])
    return "manual-resume"


def _role_core_prompt_path(run_root: Path, role: str) -> Path:
    return run_root / "runtime_kit" / "cards" / "roles" / f"{role}.md"


def _role_memory_path(run_root: Path, role: str) -> Path:
    return run_root / "crew_memory" / f"{role}.json"


def _path_hash(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return packet_runtime.sha256_file(path)


def _role_core_prompt_delivery_payload(project_root: Path, run_root: Path, run_id: str, *, source_action: str) -> dict[str, Any]:
    role_cards: dict[str, str] = {}
    role_card_hashes: dict[str, str] = {}
    for role in ROLE_CARD_KEYS:
        card_path = _role_core_prompt_path(run_root, role)
        if not card_path.exists():
            raise RouterError(f"role core prompt card is missing for {role}")
        role_cards[role] = card_path.relative_to(run_root).as_posix()
        role_card_hashes[role] = packet_runtime.sha256_file(card_path)
    return {
        "schema_version": "flowpilot.role_core_prompt_delivery.v1",
        "run_id": run_id,
        "source": "copied_runtime_kit",
        "source_action": source_action,
        "delivery_mode": "same_action_with_role_start" if source_action == "start_role_slots" else "legacy_recovery_action",
        "role_cards": role_cards,
        "role_card_hashes": role_card_hashes,
        "delivered_at": utc_now(),
    }


def _resume_role_context(project_root: Path, run_root: Path, run_state: dict[str, Any], role: str) -> dict[str, Any]:
    memory_path = _role_memory_path(run_root, role)
    core_path = _role_core_prompt_path(run_root, role)
    common_context = {
        "resume_reentry": project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
        "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
        "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
        "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
        "role_io_protocol_ledger": project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
        "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
        "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
        "display_plan": project_relative(project_root, _display_plan_path(run_root)),
    }
    context = {
        "role_key": role,
        "required_rehydration_result": "conditional_on_host_liveness",
        "active_liveness_rehydration_result": ROLE_AGENT_CONTINUITY_RESULT,
        "replacement_rehydration_result": ROLE_AGENT_REHYDRATION_RESULT,
        "allowed_rehydration_results": sorted(RESUME_ROLE_AGENT_RESULTS),
        "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
        "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
        "preferred_reasoning_effort": BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT,
        "inherit_foreground_model_allowed": False,
        "rehydrated_for_run_id": run_state["run_id"],
        "rehydrated_after_resume_tick_id": _latest_resume_tick_id(run_state),
        "rehydrated_after_resume_state_loaded": True,
        "spawned_after_resume_state_loaded": False,
        "spawned_after_resume_state_loaded_required_if_replaced": True,
        "core_prompt_path": project_relative(project_root, core_path),
        "core_prompt_hash": _path_hash(core_path),
        "memory_packet_path": project_relative(project_root, memory_path),
        "memory_packet_hash": _path_hash(memory_path),
        "role_memory_status": "available" if memory_path.exists() else "missing",
        "common_context_paths": common_context,
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    if role == "project_manager":
        context["pm_resume_context_required"] = True
        context["pm_resume_context_paths"] = {
            "resume_reentry": common_context["resume_reentry"],
            "execution_frontier": common_context["execution_frontier"],
            "packet_ledger": common_context["packet_ledger"],
            "prompt_delivery_ledger": common_context["prompt_delivery_ledger"],
            "crew_ledger": common_context["crew_ledger"],
            "crew_memory": project_relative(project_root, run_root / "crew_memory"),
            "route_history_index": common_context["route_history_index"],
            "pm_prior_path_context": common_context["pm_prior_path_context"],
            "display_plan": common_context["display_plan"],
        }
    return context


def _resume_role_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [_resume_role_context(project_root, run_root, run_state, role) for role in CREW_ROLE_KEYS]


def _resume_liveness_probe_batch_id(run_state: dict[str, Any]) -> str:
    return f"resume-liveness-{run_state['run_id']}-{_latest_resume_tick_id(run_state)}"


def _resume_role_rehydration_action_extra(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    answers = _startup_answers_from_run(run_root)
    mode = answers.get("background_agents")
    contexts = _resume_role_contexts(project_root, run_root, run_state)
    missing_memory = [item["role_key"] for item in contexts if item["role_memory_status"] != "available"]
    resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
    liveness_probe_batch_id = _resume_liveness_probe_batch_id(run_state)
    extra: dict[str, Any] = {
        "background_agents_mode": mode,
        "role_keys": list(CREW_ROLE_KEYS),
        "resume_tick_id": _latest_resume_tick_id(run_state),
        "awaiting_role_from_packet_ledger": resume_next.get("next_recipient_role"),
        "resume_next_recipient_from_packet_ledger": resume_next,
        "role_rehydration_request": contexts,
        "background_role_agent_model_policy": {
            "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
            "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
            "preferred_reasoning_effort": BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT,
            "inherit_foreground_model_allowed": False,
            "applies_to": [
                "heartbeat_resume_rehydration",
                "manual_resume_rehydration",
                "missing_role_replacement",
            ],
        },
        "memory_missing_role_keys": missing_memory,
        "crew_rehydration_report_path": project_relative(project_root, run_root / "continuation" / "crew_rehydration_report.json"),
        "liveness_probe_batch_id": liveness_probe_batch_id,
        "liveness_preflight_required": True,
        "liveness_preflight_policy": {
            "roles_to_check": list(CREW_ROLE_KEYS),
            "current_waiting_role_source": "packet_ledger.next_recipient_role",
            "resume_agent_check_required": True,
            "concurrent_probe_required": True,
            "probe_mode": ROLE_AGENT_LIVENESS_PROBE_MODE,
            "liveness_probe_batch_id": liveness_probe_batch_id,
            "start_all_probes_before_waiting": True,
            "bounded_wait_allowed": True,
            "wait_agent_timeout_result": "timeout_unknown",
            "timeout_unknown_is_active": False,
            "missing_cancelled_unknown_requires_replacement": True,
            "heartbeat_and_manual_resume_share_path": True,
        },
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    if mode == "allow":
        extra.update(
            {
                "requires_payload": "rehydrated_role_agents",
                "payload_contract": _resume_role_rehydration_payload_contract(run_state, contexts),
                "requires_host_spawn": False,
                "requires_host_role_rehydration": True,
                "requires_host_spawn_for_replacements": True,
                "spawn_required_only_for_replacements": True,
                "reuse_live_agents_when_active": True,
                "spawn_policy": "reuse_confirmed_live_agents_spawn_only_missing_cancelled_completed_unknown_or_timeout",
                "pm_memory_rehydration_required": True,
            }
        )
    elif mode == "single-agent":
        extra.update(
            {
                "requires_host_spawn": False,
                "single_agent_continuity_authorized": True,
            }
        )
    return extra


def _normalize_resume_role_agent_records(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    answers = _startup_answers_from_run(run_root)
    mode = answers.get("background_agents")
    contexts = {item["role_key"]: item for item in _resume_role_contexts(project_root, run_root, run_state)}
    resume_tick_id = _latest_resume_tick_id(run_state)
    if mode == "single-agent":
        return [
            {
                "role_key": role,
                "status": "single_agent_resume_continuity_authorized",
                "agent_id": None,
                "rehydration_result": "not_requested_single_agent_continuity",
                "rehydrated_for_run_id": run_state["run_id"],
                "rehydrated_after_resume_tick_id": resume_tick_id,
                "host_liveness_status": "not_applicable_single_agent",
                "liveness_decision": "single_agent_resume_continuity_authorized",
                "resume_agent_attempted": False,
                "bounded_wait_result": "not_applicable",
                "wait_agent_timeout_treated_as_active": False,
                "fallback_authorized_by_startup_answer": True,
                "recorded_at": utc_now(),
            }
            for role in CREW_ROLE_KEYS
        ]
    if mode != "allow":
        raise RouterError("cannot rehydrate roles before background_agents startup answer is recorded")
    if payload.get("background_agents_capability_status") != "available":
        raise RouterError("resume role rehydration requires background_agents_capability_status=available")
    expected_batch_id = _resume_liveness_probe_batch_id(run_state)
    if payload.get("liveness_probe_batch_id") != expected_batch_id:
        raise RouterError(f"resume role rehydration requires liveness_probe_batch_id={expected_batch_id}")
    if payload.get("liveness_probe_mode") != ROLE_AGENT_LIVENESS_PROBE_MODE:
        raise RouterError(f"resume role rehydration requires liveness_probe_mode={ROLE_AGENT_LIVENESS_PROBE_MODE}")
    if payload.get("all_liveness_probes_started_before_wait") is not True:
        raise RouterError("resume role rehydration requires all_liveness_probes_started_before_wait=true")
    raw_records = payload.get("rehydrated_role_agents") or payload.get("role_agents")
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError("rehydrate_role_agents requires payload.rehydrated_role_agents list or object")
    records_by_role: dict[str, dict[str, Any]] = {}
    probe_started_times: list[datetime] = []
    probe_completed_times: list[datetime] = []

    def parse_probe_time(role_key: str, field: str, value: object) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise RouterError(f"{role_key} requires {field}")
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise RouterError(f"{role_key} requires ISO timestamp {field}") from exc

    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError("each rehydrated role agent record must be an object")
        role = raw.get("role_key")
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f"rehydrated role record has unsupported role_key: {role!r}")
        if role in records_by_role:
            raise RouterError(f"duplicate rehydrated role record for {role}")
        context = contexts[str(role)]
        agent_id = raw.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f"{role} requires a non-empty live resume agent_id")
        if raw.get("model_policy") != BACKGROUND_ROLE_MODEL_POLICY:
            raise RouterError(f"{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}")
        if raw.get("reasoning_effort_policy") != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
            raise RouterError(f"{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}")
        result = raw.get("rehydration_result") or raw.get("spawn_result")
        if result not in RESUME_ROLE_AGENT_RESULTS:
            raise RouterError(f"{role} requires resume rehydration result")
        host_liveness_status = str(raw.get("host_liveness_status") or "")
        if host_liveness_status not in ROLE_AGENT_HOST_LIVENESS_STATUSES:
            raise RouterError(f"{role} requires host_liveness_status")
        liveness_decision = str(raw.get("liveness_decision") or "")
        if liveness_decision not in ROLE_AGENT_LIVENESS_DECISIONS:
            raise RouterError(f"{role} requires liveness_decision")
        if raw.get("resume_agent_attempted") is not True:
            raise RouterError(f"{role} requires resume_agent_attempted=true")
        bounded_wait_result = str(raw.get("bounded_wait_result") or "")
        if bounded_wait_result not in ROLE_AGENT_BOUNDED_WAIT_RESULTS:
            raise RouterError(f"{role} requires bounded_wait_result")
        if raw.get("liveness_probe_batch_id") != expected_batch_id:
            raise RouterError(f"{role} liveness probe batch id mismatch")
        if raw.get("liveness_probe_mode") != ROLE_AGENT_LIVENESS_PROBE_MODE:
            raise RouterError(f"{role} requires concurrent liveness probe mode")
        bounded_wait_ms = raw.get("bounded_wait_ms")
        if isinstance(bounded_wait_ms, bool) or not isinstance(bounded_wait_ms, int) or bounded_wait_ms < 0:
            raise RouterError(f"{role} requires nonnegative bounded_wait_ms")
        started_at = parse_probe_time(str(role), "liveness_probe_started_at", raw.get("liveness_probe_started_at"))
        completed_at = parse_probe_time(str(role), "liveness_probe_completed_at", raw.get("liveness_probe_completed_at"))
        if completed_at < started_at:
            raise RouterError(f"{role} liveness probe completed before it started")
        probe_started_times.append(started_at)
        probe_completed_times.append(completed_at)
        if raw.get("wait_agent_timeout_treated_as_active") is not False:
            raise RouterError(f"{role} must record wait_agent_timeout_treated_as_active=false")
        if bounded_wait_result == "timeout_unknown" and result == ROLE_AGENT_CONTINUITY_RESULT:
            raise RouterError(f"{role} wait_agent timeout_unknown cannot be treated as active continuity")
        if host_liveness_status in {"missing", "cancelled", "unknown", "timeout_unknown"} and liveness_decision == "confirmed_existing_agent":
            raise RouterError(f"{role} missing/cancelled/unknown host liveness cannot confirm existing agent")
        if host_liveness_status == "completed" and liveness_decision == "confirmed_existing_agent":
            raise RouterError(f"{role} completed host liveness cannot confirm existing agent")
        if result == ROLE_AGENT_CONTINUITY_RESULT and not (
            host_liveness_status == "active" and liveness_decision == "confirmed_existing_agent"
        ):
            raise RouterError(f"{role} live continuity requires active host liveness")
        if result == ROLE_AGENT_REHYDRATION_RESULT and liveness_decision != "spawned_replacement_from_current_run_memory":
            raise RouterError(f"{role} replacement rehydration requires spawned_replacement_from_current_run_memory")
        if result == ROLE_AGENT_REHYDRATION_RESULT and host_liveness_status == "active":
            raise RouterError(f"{role} active host liveness must use live_agent_continuity_confirmed, not replacement rehydration")
        if raw.get("rehydrated_for_run_id") != run_state["run_id"]:
            raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
        if raw.get("rehydrated_after_resume_tick_id") != resume_tick_id:
            raise RouterError(f"{role} must be rehydrated_after_resume_tick_id={resume_tick_id}")
        rehydrated_after_state_loaded = raw.get("rehydrated_after_resume_state_loaded")
        legacy_spawned_after_state_loaded = raw.get("spawned_after_resume_state_loaded")
        if rehydrated_after_state_loaded is not True and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f"{role} must be rehydrated_after_resume_state_loaded=true")
        if result == ROLE_AGENT_REHYDRATION_RESULT and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f"{role} replacement rehydration requires spawned_after_resume_state_loaded=true")
        if raw.get("core_prompt_path") != context["core_prompt_path"] or raw.get("core_prompt_hash") != context["core_prompt_hash"]:
            raise RouterError(f"{role} core prompt identity mismatch")
        memory_status = context["role_memory_status"]
        if memory_status == "available":
            if raw.get("memory_packet_path") != context["memory_packet_path"]:
                raise RouterError(f"{role} memory packet path mismatch")
            if raw.get("memory_packet_hash") != context["memory_packet_hash"]:
                raise RouterError(f"{role} memory packet hash mismatch")
            if raw.get("memory_seeded_from_current_run") is not True:
                raise RouterError(f"{role} must be seeded from current-run role memory")
        else:
            if raw.get("memory_missing_acknowledged") is not True:
                raise RouterError(f"{role} missing role memory must be acknowledged")
            if raw.get("replacement_seeded_from_common_run_context") is not True:
                raise RouterError(f"{role} replacement must be seeded from common current-run context")
        if role == "project_manager" and raw.get("pm_resume_context_delivered") is not True:
            raise RouterError("project_manager resume rehydration requires PM context delivery")
        records_by_role[str(role)] = {
            "role_key": str(role),
            "status": "live_agent_rehydrated",
            "agent_id": agent_id.strip(),
            "model_policy": BACKGROUND_ROLE_MODEL_POLICY,
            "reasoning_effort_policy": BACKGROUND_ROLE_REASONING_EFFORT_POLICY,
            "rehydration_result": str(result),
            "host_liveness_status": host_liveness_status,
            "liveness_decision": liveness_decision,
            "resume_agent_attempted": True,
            "bounded_wait_result": bounded_wait_result,
            "bounded_wait_ms": bounded_wait_ms,
            "liveness_probe_batch_id": expected_batch_id,
            "liveness_probe_mode": ROLE_AGENT_LIVENESS_PROBE_MODE,
            "liveness_probe_started_at": raw.get("liveness_probe_started_at"),
            "liveness_probe_completed_at": raw.get("liveness_probe_completed_at"),
            "wait_agent_timeout_treated_as_active": False,
            "rehydrated_for_run_id": run_state["run_id"],
            "rehydrated_after_resume_tick_id": resume_tick_id,
            "rehydrated_after_resume_state_loaded": True,
            "spawned_after_resume_state_loaded": result == ROLE_AGENT_REHYDRATION_RESULT,
            "role_memory_status": memory_status,
            "memory_packet_path": context["memory_packet_path"],
            "memory_packet_hash": context["memory_packet_hash"],
            "core_prompt_path": context["core_prompt_path"],
            "core_prompt_hash": context["core_prompt_hash"],
            "memory_seeded_from_current_run": memory_status == "available",
            "replacement_seeded_from_common_run_context": memory_status != "available",
            "pm_resume_context_delivered": role == "project_manager",
            "recorded_at": utc_now(),
        }
    if probe_started_times and probe_completed_times and max(probe_started_times) > min(probe_completed_times):
        raise RouterError("all liveness probes must start before waiting for individual results")
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing rehydrated live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]


def _write_resume_role_rehydration_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    records = _normalize_resume_role_agent_records(project_root, run_root, run_state, payload)
    memory_complete = all(record.get("role_memory_status") == "available" for record in records)
    resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
    timeout_unknown_roles = [record["role_key"] for record in records if record.get("host_liveness_status") == "timeout_unknown" or record.get("bounded_wait_result") == "timeout_unknown"]
    missing_or_cancelled_roles = [
        record["role_key"]
        for record in records
        if record.get("host_liveness_status") in {"missing", "cancelled", "unknown"}
    ]
    replacement_roles = [
        record["role_key"]
        for record in records
        if record.get("liveness_decision") == "spawned_replacement_from_current_run_memory"
    ]
    report_path = run_root / "continuation" / "crew_rehydration_report.json"
    report = {
        "schema_version": "flowpilot.crew_rehydration_report.v1",
        "run_id": run_state["run_id"],
        "resume_tick_id": _latest_resume_tick_id(run_state),
        "background_agents_mode": _startup_answers_from_run(run_root).get("background_agents"),
        "recorded_at": utc_now(),
        "source_paths": {
            "resume_reentry": project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
            "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
            "crew_memory": project_relative(project_root, run_root / "crew_memory"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
            "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
            "role_io_protocol_ledger": project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "all_six_roles_ready": len(records) == len(CREW_ROLE_KEYS),
        "liveness_preflight": {
            "checked_at": utc_now(),
            "probe_mode": ROLE_AGENT_LIVENESS_PROBE_MODE,
            "liveness_probe_batch_id": _resume_liveness_probe_batch_id(run_state),
            "all_liveness_probes_started_before_wait": True,
            "awaiting_role": resume_next.get("next_recipient_role"),
            "roles_checked": [record["role_key"] for record in records],
            "timeout_unknown_role_keys": timeout_unknown_roles,
            "missing_cancelled_or_unknown_role_keys": missing_or_cancelled_roles,
            "replacement_role_keys": replacement_roles,
            "wait_agent_timeout_treated_as_active": False,
            "decision": "roles_ready_after_replacement" if replacement_roles else "all_roles_active",
        },
        "current_run_memory_complete": memory_complete,
        "missing_memory_role_keys": [record["role_key"] for record in records if record.get("role_memory_status") != "available"],
        "pm_memory_rehydrated": any(
            record["role_key"] == "project_manager"
            and record.get("pm_resume_context_delivered") is True
            and record.get("role_memory_status") == "available"
            for record in records
        ),
        "role_records": records,
        "controller_visibility": "state_and_envelopes_only",
        "sealed_body_reads_allowed": False,
        "chat_history_progress_inference_allowed": False,
    }
    write_json(report_path, report)
    crew_path = run_root / "crew_ledger.json"
    crew = read_json_if_exists(crew_path)
    history = crew.get("resume_rehydration_history") if isinstance(crew.get("resume_rehydration_history"), list) else []
    history.append(
        {
            "report_path": project_relative(project_root, report_path),
            "resume_tick_id": report["resume_tick_id"],
            "recorded_at": report["recorded_at"],
            "all_six_roles_ready": report["all_six_roles_ready"],
            "current_run_memory_complete": memory_complete,
            "liveness_decision": report["liveness_preflight"]["decision"],
            "timeout_unknown_role_keys": timeout_unknown_roles,
            "missing_cancelled_or_unknown_role_keys": missing_or_cancelled_roles,
        }
    )
    crew.update(
        {
            "schema_version": "flowpilot.crew_ledger.v1",
            "run_id": run_state["run_id"],
            "role_slots": records,
            "latest_resume_rehydration_report": project_relative(project_root, report_path),
            "resume_rehydration_history": history,
            "updated_at": utc_now(),
        }
    )
    write_json(crew_path, crew)
    _append_role_io_protocol_injections(
        project_root,
        run_root,
        str(run_state["run_id"]),
        records,
        default_lifecycle_phase="heartbeat_rehydration",
        resume_tick_id=report["resume_tick_id"],
        source_action="rehydrate_role_agents",
    )
    run_state["flags"]["resume_roles_restored"] = True
    run_state["flags"]["resume_role_agents_rehydrated"] = True
    run_state["flags"]["crew_rehydration_report_written"] = True
    if not memory_complete:
        run_state["flags"]["resume_state_ambiguous"] = True


def _create_run_id() -> str:
    return f"run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _create_empty_packet_ledger(project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    return {
        "schema_version": PACKET_LEDGER_SCHEMA,
        "run_id": run_id,
        "run_root": project_relative(project_root, run_root),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "controller_boundary": {
            "controller_only": True,
            "all_role_mail_routes_through_controller": True,
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_create_project_evidence": False,
            "router_direct_dispatch_required_before_worker": True,
            "reviewer_dispatch_required_before_worker": False,
        },
        "mail": [],
        "packets": [],
    }


def _active_packet_ledger_record(packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    active_packet_id = packet_ledger.get("active_packet_id")
    packets = packet_ledger.get("packets") if isinstance(packet_ledger.get("packets"), list) else []
    if active_packet_id:
        for record in reversed(packets):
            if isinstance(record, dict) and record.get("packet_id") == active_packet_id:
                return record
    for record in reversed(packets):
        if isinstance(record, dict):
            return record
    return None


def _derive_resume_next_recipient_from_packet_ledger(run_root: Path) -> dict[str, Any]:
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json") or {}
    record = _active_packet_ledger_record(packet_ledger)
    active_packet_id = packet_ledger.get("active_packet_id")
    status = str(packet_ledger.get("active_packet_status") or "")
    holder = str(packet_ledger.get("active_packet_holder") or "")
    packet_envelope = record.get("packet_envelope") if isinstance(record, dict) and isinstance(record.get("packet_envelope"), dict) else {}
    result_envelope = record.get("result_envelope") if isinstance(record, dict) and isinstance(record.get("result_envelope"), dict) else {}
    assigned_worker = str(record.get("assigned_worker_role") or packet_envelope.get("to_role") or "") if isinstance(record, dict) else ""
    result_recipient = str(result_envelope.get("next_recipient") or "") if result_envelope else ""

    controller_next_action = "resume_without_active_packet_then_request_pm_decision"
    next_recipient = "project_manager"
    reason = "No active packet is recorded, so resume must continue through PM resume decision after role rehydration."
    if active_packet_id:
        if status == "packet-with-controller":
            next_recipient = assigned_worker or "unknown"
            controller_next_action = "relay_packet_envelope_to_recorded_recipient"
            reason = "Packet ledger says the packet is with Controller and records the worker recipient."
        elif status in {"envelope-relayed", "packet-body-opened-by-recipient"}:
            next_recipient = holder or assigned_worker or "unknown"
            controller_next_action = "wait_for_recorded_packet_holder_result"
            reason = "Packet ledger says the packet is already with a role; Controller waits for that role's envelope-only return."
        elif status in {"worker-result-needs-review", "result-envelope-returned"}:
            next_recipient = result_recipient or "human_like_reviewer"
            controller_next_action = "relay_result_envelope_to_recorded_reviewer"
            reason = "Packet ledger says a result envelope is with Controller and records the review recipient."
        elif status in {"result-envelope-relayed", "result-body-opened-by-recipient"}:
            next_recipient = holder or result_recipient or "human_like_reviewer"
            controller_next_action = "wait_for_recorded_result_holder_review"
            reason = "Packet ledger says the result is already with its review holder."
        elif status == "contaminated-returned-to-sender":
            next_recipient = holder or str(record.get("from_role") or "project_manager") if isinstance(record, dict) else "project_manager"
            controller_next_action = "wait_for_sender_reissue_or_pm_repair_decision"
            reason = "Packet ledger says the envelope was returned to sender because the control boundary was violated."
        elif status == "superseded-by-replacement":
            next_recipient = "project_manager"
            controller_next_action = "wait_for_replacement_packet_or_pm_route_repair"
            reason = "Packet ledger says this packet was superseded, so PM owns the replacement or route repair decision."
        else:
            next_recipient = holder or assigned_worker or result_recipient or "project_manager"
            controller_next_action = "wait_for_ledger_recorded_holder_or_pm_resume_decision"
            reason = "Packet ledger has an active packet with a non-standard status; Controller must not infer from chat."

    return {
        "schema_version": "flowpilot.resume_next_recipient.v1",
        "source": "packet_ledger",
        "active_packet_id": active_packet_id,
        "active_packet_status": status or None,
        "active_packet_holder": holder or None,
        "controller_next_action": controller_next_action,
        "next_recipient_role": next_recipient,
        "controller_has_explicit_next_from_ledger": next_recipient != "unknown",
        "controller_may_infer_next_from_chat_history": False,
        "sealed_body_reads_allowed": False,
        "reason": reason,
    }


def _create_empty_execution_frontier(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "flowpilot.execution_frontier.v1",
        "run_id": run_id,
        "status": "startup_intake",
        "active_route_id": None,
        "active_node_id": None,
        "updated_at": utc_now(),
        "source": "router_bootstrap",
    }


def _set_pre_route_frontier_phase(run_root: Path, run_id: str, phase: str) -> None:
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or _create_empty_execution_frontier(run_id)
    if frontier.get("active_route_id") or frontier.get("active_node_id"):
        return
    frontier["status"] = phase
    frontier["phase"] = phase
    frontier["updated_at"] = utc_now()
    frontier["source"] = "flowpilot_router"
    write_json(run_root / "execution_frontier.json", frontier)


def _create_empty_role_memory(run_id: str, role: str) -> dict[str, Any]:
    return {
        "schema_version": "flowpilot.role_memory.v1",
        "run_id": run_id,
        "role_key": role,
        "status": "slot_created_no_work_yet",
        "summary": "",
        "controller_decision_authority": False,
        "updated_at": utc_now(),
    }


def _role_memory_event_role(event: str, payload: dict[str, Any]) -> str | None:
    for key in (
        "completed_by_role",
        "reviewed_by_role",
        "decided_by_role",
        "recorded_by_role",
        "requested_by_role",
        "written_by_role",
        "from_role",
    ):
        value = str(payload.get(key) or "").strip()
        if value in CREW_ROLE_KEYS:
            return value
    if event.startswith("pm_") or event.startswith("project_manager_"):
        return "project_manager"
    if event.startswith("reviewer_") or event.startswith("current_node_reviewer_"):
        return "human_like_reviewer"
    if event.startswith("process_officer_"):
        return "process_flowguard_officer"
    if event.startswith("product_officer_"):
        return "product_flowguard_officer"
    if event.startswith("worker_"):
        return "worker_a"
    return None


def _append_role_memory_delta(run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    role = _role_memory_event_role(event, payload)
    if role not in CREW_ROLE_KEYS:
        return None
    memory_path = _role_memory_path(run_root, role)
    memory = read_json_if_exists(memory_path) or _create_empty_role_memory(str(run_state["run_id"]), role)
    artifact_refs = {
        key: value
        for key, value in payload.items()
        if isinstance(key, str)
        and isinstance(value, str)
        and (
            key.endswith("_path")
            or key.endswith("_hash")
            or key in {"packet_id", "request_id", "defect_or_blocker_id", "decision"}
        )
    }
    delta = {
        "event": event,
        "recorded_at": utc_now(),
        "artifact_refs": artifact_refs,
        "authority": "memory_index_only",
        "controller_decision_authority": False,
        "sealed_body_stored": False,
    }
    deltas = memory.get("recent_deltas") if isinstance(memory.get("recent_deltas"), list) else []
    deltas.append(delta)
    memory["recent_deltas"] = deltas[-16:]
    memory["status"] = "available"
    memory["summary"] = f"Last observed event: {event}"
    memory["updated_at"] = delta["recorded_at"]
    memory["controller_decision_authority"] = False
    memory["role_memory_used_for_completion_authority"] = False
    write_json(memory_path, memory)
    return {"role": role, "event": event, "delta_count": len(memory["recent_deltas"])}


def _startup_answers_from_run(run_root: Path) -> dict[str, Any]:
    payload = read_json_if_exists(run_root / "startup_answers.json")
    answers = payload.get("answers")
    if not isinstance(answers, dict):
        return {}
    return dict(answers)


def _scheduled_continuation_requested(answers: dict[str, Any]) -> bool:
    value = str(answers.get("scheduled_continuation") or "").lower()
    return bool(value) and "manual" not in value and "no" not in value and "disable" not in value


def _continuation_binding_path(run_root: Path) -> Path:
    return run_root / "continuation" / "continuation_binding.json"


def _stable_resume_launcher_contract() -> dict[str, Any]:
    return {
        "event": "heartbeat_or_manual_resume_requested",
        "wake_sources": ["heartbeat", "manual_resume"],
        "resume_action": "load_resume_state",
        "role_liveness_action": "rehydrate_role_agents",
        "router_reentry_required_on_every_wake": True,
        "heartbeat_and_manual_resume_share_path": True,
        "self_keepalive_allowed": False,
        "diagnostic_work_chain_status_only": True,
        "controller_only": True,
        "sealed_body_reads_allowed": False,
    }


def _write_initial_continuation_binding(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    answers = _startup_answers_from_run(run_root)
    scheduled_requested = _scheduled_continuation_requested(answers)
    binding = {
        "schema_version": "flowpilot.continuation_binding.v1",
        "run_id": run_state["run_id"],
        "mode": "scheduled_heartbeat" if scheduled_requested else "manual_resume",
        "scheduled_continuation_requested": scheduled_requested,
        "route_heartbeat_interval_minutes": 1 if scheduled_requested else 0,
        "heartbeat_active": False,
        "host_automation_id": None,
        "host_automation_verified": False,
        "stable_launcher": _stable_resume_launcher_contract(),
        "source_paths": {
            "startup_answers": project_relative(project_root, run_root / "startup_answers.json"),
            "router_state": project_relative(project_root, run_state_path(run_root)),
        },
        "updated_at": utc_now(),
    }
    write_json(_continuation_binding_path(run_root), binding)


def _write_host_heartbeat_binding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    binding_path = _continuation_binding_path(run_root)
    binding = read_json_if_exists(binding_path)
    answers = _startup_answers_from_run(run_root)
    scheduled_requested = _scheduled_continuation_requested(answers)
    interval = int(payload.get("route_heartbeat_interval_minutes") or binding.get("route_heartbeat_interval_minutes") or 0)
    if scheduled_requested and interval != 1:
        raise RouterError("scheduled FlowPilot heartbeat must be one minute")
    if scheduled_requested and not payload.get("host_automation_id"):
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_id")
    if scheduled_requested and payload.get("host_automation_verified") is not True:
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_verified=true")
    host_automation_proof = payload.get("host_automation_proof")
    if scheduled_requested and not isinstance(host_automation_proof, dict):
        raise RouterError("scheduled FlowPilot heartbeat requires host_automation_proof")
    if host_automation_proof is not None:
        if not isinstance(host_automation_proof, dict):
            raise RouterError("host_automation_proof must be an object")
        if host_automation_proof.get("source_kind") != "host_receipt":
            raise RouterError("host_automation_proof requires source_kind=host_receipt")
        if host_automation_proof.get("run_id") != run_state["run_id"]:
            raise RouterError("host_automation_proof run_id must match current run")
        if host_automation_proof.get("host_automation_id") != payload.get("host_automation_id"):
            raise RouterError("host_automation_proof host_automation_id mismatch")
        if int(host_automation_proof.get("route_heartbeat_interval_minutes") or 0) != 1:
            raise RouterError("host_automation_proof requires one-minute heartbeat interval")
        if host_automation_proof.get("heartbeat_bound_to_current_run") is not True:
            raise RouterError("host_automation_proof must bind heartbeat to current run")
    binding.update(
        {
            "schema_version": "flowpilot.continuation_binding.v1",
            "run_id": run_state["run_id"],
            "mode": "scheduled_heartbeat" if scheduled_requested else "manual_resume",
            "scheduled_continuation_requested": scheduled_requested,
            "route_heartbeat_interval_minutes": 1 if scheduled_requested else 0,
            "heartbeat_active": bool(scheduled_requested),
            "host_automation_id": payload.get("host_automation_id") if scheduled_requested else None,
            "host_automation_verified": bool(scheduled_requested),
            "stable_launcher": _stable_resume_launcher_contract(),
            **({"host_automation_proof": host_automation_proof} if scheduled_requested and isinstance(host_automation_proof, dict) else {}),
            "recorded_by": str(payload.get("recorded_by") or "host"),
            "updated_at": utc_now(),
        }
    )
    write_json(binding_path, binding)


def _host_heartbeat_binding_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    binding = read_json_if_exists(_continuation_binding_path(run_root))
    return (
        binding.get("run_id") == run_state.get("run_id")
        and binding.get("mode") == "scheduled_heartbeat"
        and binding.get("scheduled_continuation_requested") is True
        and binding.get("heartbeat_active") is True
        and binding.get("route_heartbeat_interval_minutes") == 1
        and bool(binding.get("host_automation_id"))
        and binding.get("host_automation_verified") is True
        and _continuation_has_host_bound_automation_receipt(binding, str(run_state.get("run_id") or ""))
    )


def _append_heartbeat_tick(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source") or "heartbeat_or_manual_resume")
    tick = {
        "schema_version": "flowpilot.heartbeat_tick.v1",
        "run_id": run_state["run_id"],
        "tick_id": f"heartbeat-{len(run_state.get('heartbeat_ticks', [])) + 1:04d}",
        "work_chain_status": str(payload.get("work_chain_status") or "broken_or_unknown"),
        "work_chain_status_trust": "diagnostic_only",
        "recorded_at": utc_now(),
        "source": source,
        "resume_requested": True,
        "router_reentry_required": True,
        "self_keepalive_allowed": False,
        "heartbeat_automation_status": str(payload.get("heartbeat_automation_status") or "unknown"),
        "heartbeat_automation_status_checked": payload.get("heartbeat_automation_status_checked") is True,
    }
    ticks_path = run_root / "continuation" / "heartbeat_ticks.jsonl"
    ticks_path.parent.mkdir(parents=True, exist_ok=True)
    with ticks_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(tick, sort_keys=True) + "\n")
    run_state.setdefault("heartbeat_ticks", []).append(
        {
            "tick_id": tick["tick_id"],
            "work_chain_status": tick["work_chain_status"],
            "resume_requested": tick["resume_requested"],
            "router_reentry_required": tick["router_reentry_required"],
            "self_keepalive_allowed": tick["self_keepalive_allowed"],
            "heartbeat_automation_status": tick["heartbeat_automation_status"],
            "heartbeat_automation_status_checked": tick["heartbeat_automation_status_checked"],
        }
    )
    return tick


def _reset_resume_cycle_for_wakeup(run_state: dict[str, Any]) -> None:
    for flag in (
        "resume_reentry_requested",
        "resume_state_loaded",
        "resume_state_ambiguous",
        "resume_roles_restored",
        "resume_role_agents_rehydrated",
        "crew_rehydration_report_written",
        "controller_resume_card_delivered",
        "pm_crew_rehydration_freshness_card_delivered",
        "pm_resume_decision_card_delivered",
        "pm_resume_recovery_decision_returned",
    ):
        run_state["flags"][flag] = False


def _current_closure_state_clean(run_root: Path) -> bool:
    evidence = read_json_if_exists(run_root / "evidence" / "evidence_ledger.json")
    generated = read_json_if_exists(run_root / "generated_resource_ledger.json")
    final_ledger = read_json_if_exists(run_root / "final_route_wide_gate_ledger.json")
    terminal = read_json_if_exists(run_root / "reviews" / "terminal_backward_replay.json")
    task_projection = read_json_if_exists(_task_completion_projection_path(run_root))
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    return (
        evidence.get("unresolved_count") == 0
        and evidence.get("stale_count") == 0
        and generated.get("pending_resource_count") == 0
        and generated.get("unresolved_resource_count") == 0
        and final_ledger.get("completion_allowed") is True
        and final_ledger.get("counts", {}).get("unresolved_count") == 0
        and terminal.get("passed") is True
        and task_projection.get("task_status") == "ready_for_pm_terminal_closure"
        and pm_suggestion_status["clean"]
    )


def _invalidate_route_completion_if_dirty_before_closure(run_state: dict[str, Any], run_root: Path) -> None:
    flags = run_state["flags"]
    if not flags.get("final_backward_replay_passed"):
        return
    if flags.get("pm_closure_approved"):
        return
    if _current_closure_state_clean(run_root):
        return
    _reset_flags(run_state, ROUTE_COMPLETION_FLAGS)
    append_history(
        run_state,
        "route_completion_cycle_invalidated_by_dirty_closure_state",
        {
            "reason": "completion ledgers changed after terminal backward replay and before PM closure",
            "restart_from": "pm.evidence_quality_package",
        },
    )


def _startup_fact_checks(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    answers = _startup_answers_from_run(run_root)
    required_answer_ids = {item["id"] for item in STARTUP_QUESTIONS}
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json")
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    role_keys = {slot.get("role_key") for slot in role_slots if isinstance(slot, dict)}
    live_role_slots_current = role_keys == set(CREW_ROLE_KEYS) and all(
        isinstance(slot, dict)
        and slot.get("status") == "live_agent_started"
        and isinstance(slot.get("agent_id"), str)
        and bool(str(slot.get("agent_id")).strip())
        and slot.get("model_policy") == BACKGROUND_ROLE_MODEL_POLICY
        and slot.get("reasoning_effort_policy") == BACKGROUND_ROLE_REASONING_EFFORT_POLICY
        and slot.get("spawn_result") == ROLE_AGENT_SPAWN_RESULT
        and slot.get("spawned_for_run_id") == run_state.get("run_id")
        and slot.get("spawned_after_startup_answers") is True
        for slot in role_slots
    )
    single_agent_slots_current = role_keys == set(CREW_ROLE_KEYS) and all(
        isinstance(slot, dict)
        and slot.get("status") == "single_agent_continuity_authorized"
        and slot.get("agent_id") is None
        and slot.get("fallback_authorized_by_startup_answer") is True
        for slot in role_slots
    )
    indexed_runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    continuation_binding = read_json_if_exists(_continuation_binding_path(run_root))
    scheduled_requested = _scheduled_continuation_requested(answers)
    old_control_paths = [
        project_root / ".flowpilot" / "state.json",
        project_root / ".flowpilot" / "capabilities.json",
        project_root / ".flowpilot" / "execution_frontier.json",
        project_root / ".flowpilot" / "routes",
    ]
    boundary_context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    return {
        "controller_boundary_confirmed": boundary_context is not None or _legacy_pm_reset_boundary_confirmed(run_state),
        "startup_answers_complete": required_answer_ids.issubset({key for key, value in answers.items() if value}),
        "current_pointer_matches_run": current.get("current_run_id") == run_state.get("run_id")
        and current.get("current_run_root") == run_state.get("run_root"),
        "index_points_to_run": index.get("current_run_id") == run_state.get("run_id")
        and any(isinstance(item, dict) and item.get("run_id") == run_state.get("run_id") for item in indexed_runs),
        "crew_slots_current": role_keys == set(CREW_ROLE_KEYS),
        "live_background_agents_current_if_allowed": live_role_slots_current
        if answers.get("background_agents") == "allow"
        else True,
        "single_agent_continuity_current_if_selected": single_agent_slots_current
        if answers.get("background_agents") == "single-agent"
        else True,
        "continuation_mode_recorded": bool(answers.get("scheduled_continuation")),
        "continuation_binding_current": continuation_binding.get("run_id") == run_state.get("run_id")
        and continuation_binding.get("schema_version") == "flowpilot.continuation_binding.v1",
        "scheduled_heartbeat_verified_if_requested": (
            continuation_binding.get("heartbeat_active") is True
            and continuation_binding.get("route_heartbeat_interval_minutes") == 1
            and bool(continuation_binding.get("host_automation_id"))
            and continuation_binding.get("host_automation_verified") is True
        )
        if scheduled_requested
        else continuation_binding.get("mode") == "manual_resume",
        "display_surface_recorded": bool(answers.get("display_surface")),
        "old_state_quarantined": not any(path.exists() for path in old_control_paths),
    }


def _controller_boundary_confirmation_path(run_root: Path) -> Path:
    return run_root / "startup" / "controller_boundary_confirmation.json"


def _run_manifest_path(run_root: Path) -> Path:
    manifest_path = run_root / "runtime_kit" / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    return runtime_kit_source() / "manifest.json"


def _controller_boundary_sources(run_root: Path) -> dict[str, Any]:
    manifest_path = _run_manifest_path(run_root)
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise RouterError("invalid prompt manifest schema")
    controller_core = manifest_card(manifest, "controller.core")
    card_path = manifest_path.parent / str(controller_core["path"])
    if not card_path.exists():
        raise RouterError("controller.core card path is missing")
    policy = manifest.get("controller_policy")
    if not isinstance(policy, dict):
        raise RouterError("prompt manifest controller_policy must be an object")
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_hash": packet_runtime.sha256_file(manifest_path),
        "controller_core_card": controller_core,
        "controller_core_path": card_path,
        "controller_core_hash": packet_runtime.sha256_file(card_path),
        "controller_policy": policy,
        "controller_policy_hash": _json_sha256(policy),
    }


def _controller_boundary_constraints() -> dict[str, Any]:
    return {
        "relay_and_record_only": True,
        "next_step_source": "flowpilot_router.py",
        "controller_may_create_project_evidence": False,
        "controller_may_read_sealed_bodies": False,
        "controller_may_implement": False,
        "controller_may_approve_gate": False,
        "controller_may_mutate_route": False,
        "controller_may_close_node": False,
    }


def _legacy_pm_reset_boundary_confirmed(run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(
        flags.get("controller_role_confirmed")
        and flags.get("pm_controller_reset_card_delivered")
        and flags.get("pm_controller_reset_decision_returned")
    )


def _write_controller_boundary_confirmation(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    if not run_state.get("flags", {}).get("controller_core_loaded"):
        raise RouterError("controller core must be loaded before Controller boundary confirmation")
    sources = _controller_boundary_sources(run_root)
    confirmation_path = _controller_boundary_confirmation_path(run_root)
    confirmation = {
        "schema_version": CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
        "run_id": run_state["run_id"],
        "event": "controller_role_confirmed_from_router_core",
        "confirmed_by_role": "controller",
        "confirmation_source": "router_delivered_controller_core",
        "controller_core_card_id": "controller.core",
        "controller_core_path": project_relative(project_root, sources["controller_core_path"]),
        "controller_core_sha256": sources["controller_core_hash"],
        "manifest_path": project_relative(project_root, sources["manifest_path"]),
        "manifest_sha256": sources["manifest_hash"],
        "controller_policy": sources["controller_policy"],
        "controller_policy_sha256": sources["controller_policy_hash"],
        "boundary_constraints": _controller_boundary_constraints(),
        "sealed_body_reads_allowed": False,
        "router_owned_confirmation": True,
        "confirmed_at": utc_now(),
    }
    write_json(confirmation_path, confirmation)
    confirmation_hash = packet_runtime.sha256_file(confirmation_path)
    return {
        "path": project_relative(project_root, confirmation_path),
        "sha256": confirmation_hash,
        "controller_core_path": confirmation["controller_core_path"],
        "controller_core_sha256": confirmation["controller_core_sha256"],
        "controller_policy_sha256": confirmation["controller_policy_sha256"],
    }


def _controller_boundary_confirmation_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    confirmation_path = _controller_boundary_confirmation_path(run_root)
    if not confirmation_path.exists():
        return None
    confirmation = read_json_if_exists(confirmation_path)
    if confirmation.get("schema_version") != CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA:
        return None
    if confirmation.get("run_id") != run_state.get("run_id"):
        return None
    if confirmation.get("event") != "controller_role_confirmed_from_router_core":
        return None
    if confirmation.get("confirmed_by_role") != "controller":
        return None
    if confirmation.get("router_owned_confirmation") is not True:
        return None
    constraints = confirmation.get("boundary_constraints")
    if constraints != _controller_boundary_constraints():
        return None
    sources = _controller_boundary_sources(run_root)
    if confirmation.get("controller_core_sha256") != sources["controller_core_hash"]:
        return None
    if confirmation.get("manifest_sha256") != sources["manifest_hash"]:
        return None
    if confirmation.get("controller_policy_sha256") != sources["controller_policy_hash"]:
        return None
    if confirmation.get("sealed_body_reads_allowed") is not False:
        return None
    return {
        "path": confirmation_path,
        "sha256": packet_runtime.sha256_file(confirmation_path),
        "confirmation": confirmation,
    }


def _role_slots_have_host_spawn_receipts(role_slots: list[dict[str, Any]], run_id: str) -> bool:
    for slot in role_slots:
        receipt = slot.get("host_spawn_receipt") if isinstance(slot, dict) else None
        if not isinstance(receipt, dict):
            return False
        if receipt.get("source_kind") != "host_receipt":
            return False
        if receipt.get("spawned_for_run_id") != run_id:
            return False
        if receipt.get("role_key") != slot.get("role_key"):
            return False
        if receipt.get("agent_id") != slot.get("agent_id"):
            return False
    return bool(role_slots)


def _continuation_has_host_bound_automation_receipt(continuation_binding: dict[str, Any], run_id: str) -> bool:
    proof = continuation_binding.get("host_automation_proof")
    if not isinstance(proof, dict):
        return False
    return (
        proof.get("source_kind") == "host_receipt"
        and proof.get("run_id") == run_id
        and proof.get("host_automation_id") == continuation_binding.get("host_automation_id")
        and proof.get("route_heartbeat_interval_minutes") == 1
        and proof.get("heartbeat_bound_to_current_run") is True
    )


def _startup_external_fact_requirements(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    answers = _startup_answers_from_run(run_root)
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    continuation_binding = read_json_if_exists(_continuation_binding_path(run_root))
    requirements: list[dict[str, Any]] = []
    if answers.get("background_agents") == "allow" and not _role_slots_have_host_spawn_receipts(role_slots, str(run_state.get("run_id") or "")):
        requirements.append(
            {
                "id": "live_agent_spawn_freshness",
                "reason": "Router validates role-slot shape, run ids, and requested background role intelligence policy, but host spawn freshness and actual model selection need a receipt or reviewer check.",
                "self_attested_payload_fields": [
                    "role_agents[].model_policy",
                    "role_agents[].reasoning_effort_policy",
                    "role_agents[].spawn_result",
                    "role_agents[].spawned_after_startup_answers",
                ],
                "reviewer_direct_check_required": True,
            }
        )
    if _scheduled_continuation_requested(answers) and not _continuation_has_host_bound_automation_receipt(
        continuation_binding,
        str(run_state.get("run_id") or ""),
    ):
        requirements.append(
            {
                "id": "heartbeat_host_automation_current_run_binding",
                "reason": "Router validates the heartbeat binding fields, but host_automation_verified=true alone is an AI/host payload claim unless backed by a host receipt.",
                "self_attested_payload_fields": ["host_automation_verified", "host_automation_id"],
                "reviewer_direct_check_required": True,
            }
        )
    if answers.get("display_surface") == "cockpit":
        requirements.append(
            {
                "id": "cockpit_or_display_fallback_reality",
                "reason": "Router can record selected display mode and chat fallback, but live Cockpit availability or fallback necessity requires direct review when requested.",
                "self_attested_payload_fields": ["display_surface"],
                "reviewer_direct_check_required": True,
            }
        )
    return requirements


def _startup_fact_review_ownership(
    computed_checks: dict[str, bool],
    external_requirements: list[dict[str, Any]],
) -> dict[str, Any]:
    reviewer_ids = {str(item["id"]) for item in external_requirements if item.get("id")}
    router_owned = sorted(computed_checks)
    reviewer_owned = sorted(reviewer_ids)
    pm_decision_owned = ["startup_user_answer_authenticity"]
    covered = set(router_owned) | set(reviewer_owned) | set(pm_decision_owned)
    known = set(computed_checks) | reviewer_ids | set(pm_decision_owned)
    unowned = sorted(known - covered)
    return {
        "router_owned_mechanical_checks": router_owned,
        "reviewer_owned_external_fact_ids": reviewer_owned,
        "pm_decision_owned_unreviewable_fact_ids": pm_decision_owned,
        "unowned_fact_ids": unowned,
        "all_required_facts_have_owner": not unowned,
    }


def _write_startup_mechanical_audit(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    computed_checks: dict[str, bool],
) -> dict[str, Any]:
    audit_path = run_root / "startup" / "startup_mechanical_audit.json"
    proof_path = _router_owned_check_proof_path(audit_path)
    evidence_paths = [
        run_root / "startup_answers.json",
        project_root / ".flowpilot" / "current.json",
        project_root / ".flowpilot" / "index.json",
        run_root / "crew_ledger.json",
        _continuation_binding_path(run_root),
        run_state_path(run_root),
    ]
    boundary_path = _controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        evidence_paths.append(boundary_path)
    external_requirements = _startup_external_fact_requirements(run_root, run_state)
    review_ownership = _startup_fact_review_ownership(computed_checks, external_requirements)
    audit = {
        "schema_version": STARTUP_MECHANICAL_AUDIT_SCHEMA,
        "run_id": run_state["run_id"],
        "check_owner": "flowpilot_router",
        "mechanical_checks": computed_checks,
        "mechanical_checks_passed": all(computed_checks.values()),
        "router_replacement_scope": "mechanical_only",
        "self_attested_ai_claims_accepted_as_proof": False,
        "fact_review_ownership": review_ownership,
        "reviewer_required_external_facts": external_requirements,
        "router_owned_check_proof_path": project_relative(project_root, proof_path),
        "source_paths": [_evidence_path_record(project_root, path) for path in evidence_paths],
        "written_at": utc_now(),
    }
    if not review_ownership["all_required_facts_have_owner"]:
        raise RouterError("startup fact ownership map left unowned requirements")
    write_json(audit_path, audit)
    proof_record = _write_router_owned_check_proof(
        project_root,
        run_root,
        check_name="startup_mechanical_checks",
        audit_path=audit_path,
        source_kind="router_computed",
        evidence_paths=evidence_paths,
    )
    _validate_router_owned_check_proof(
        project_root,
        run_root,
        check_name="startup_mechanical_checks",
        audit_path=audit_path,
    )
    audit["router_owned_check_proof"] = {
        "path": proof_record["proof_path"],
        "schema_version": ROUTER_OWNED_CHECK_PROOF_SCHEMA,
    }
    return audit


def _startup_mechanical_audit_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    audit_path = run_root / "startup" / "startup_mechanical_audit.json"
    if not audit_path.exists():
        return None
    audit = read_json_if_exists(audit_path)
    if audit.get("schema_version") != STARTUP_MECHANICAL_AUDIT_SCHEMA:
        return None
    if audit.get("run_id") != run_state.get("run_id"):
        return None
    try:
        proof = _validate_router_owned_check_proof(
            project_root,
            run_root,
            check_name="startup_mechanical_checks",
            audit_path=audit_path,
        )
    except RouterError:
        return None
    proof_path = _router_owned_check_proof_path(audit_path)
    return {
        "audit": audit,
        "audit_path": audit_path,
        "audit_hash": packet_runtime.sha256_file(audit_path),
        "proof": proof,
        "proof_path": proof_path,
        "proof_hash": packet_runtime.sha256_file(proof_path) if proof_path.exists() else None,
    }


def _startup_mechanical_audit_action_extra(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    context = _startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise RouterError("startup mechanical audit must be written before reviewer startup fact card delivery")
    display_path = run_root / "display" / "display_surface.json"
    if not display_path.exists():
        raise RouterError("startup display-surface status must be written before reviewer startup fact card delivery")
    return {
        "startup_mechanical_audit_path": project_relative(project_root, context["audit_path"]),
        "startup_mechanical_audit_hash": context["audit_hash"],
        "router_owned_check_proof_path": project_relative(project_root, context["proof_path"]),
        "router_owned_check_proof_hash": context["proof_hash"],
        "startup_display_surface_path": project_relative(project_root, display_path),
        "startup_display_surface_hash": packet_runtime.sha256_file(display_path),
        "reviewer_has_direct_display_evidence": True,
        "router_computable_checks_already_enforced": True,
        "reviewer_should_not_reprove_router_computable_checks": True,
        "reviewer_required_external_facts": context["audit"].get("reviewer_required_external_facts") or [],
        "router_replacement_scope": "mechanical_only",
    }


def _validate_startup_external_fact_review(
    payload: dict[str, Any],
    requirements: list[dict[str, Any]],
    *,
    startup_mechanical_audit_hash: str | None = None,
) -> dict[str, Any]:
    if not requirements:
        return {
            "reviewed_by_role": "human_like_reviewer",
            "reviewer_required_external_fact_count": 0,
            "reviewer_checked_requirement_ids": [],
            "self_attested_ai_claims_accepted_as_proof": False,
        }
    review = payload.get("external_fact_review")
    if not isinstance(review, dict):
        raise RouterError("startup fact report requires external_fact_review for non-router-checkable facts")
    if review.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("external_fact_review must be reviewed_by_role=human_like_reviewer")
    if (
        startup_mechanical_audit_hash
        and review.get("router_mechanical_audit_hash") is not None
        and review.get("router_mechanical_audit_hash") != startup_mechanical_audit_hash
    ):
        raise RouterError("external_fact_review must reference the current startup mechanical audit hash")
    if review.get("self_attested_ai_claims_accepted_as_proof") is not False:
        raise RouterError("external_fact_review cannot accept self-attested AI claims as proof")
    checked_ids = review.get("reviewer_checked_requirement_ids")
    if not isinstance(checked_ids, list):
        raise RouterError("external_fact_review requires reviewer_checked_requirement_ids list")
    checked = {str(item) for item in checked_ids}
    required = {str(item["id"]) for item in requirements if item.get("id")}
    missing = sorted(required - checked)
    if missing:
        raise RouterError(f"external_fact_review missing required checks: {', '.join(missing)}")
    direct_paths = review.get("direct_evidence_paths_checked")
    if not isinstance(direct_paths, list) or not direct_paths:
        raise RouterError("external_fact_review requires direct_evidence_paths_checked")
    return {
        "reviewed_by_role": "human_like_reviewer",
        "reviewer_required_external_fact_count": len(requirements),
        "reviewer_checked_requirement_ids": sorted(checked),
        "direct_evidence_paths_checked": direct_paths,
        "self_attested_ai_claims_accepted_as_proof": False,
        "notes": review.get("notes"),
    }


def _write_startup_fact_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    canonical_report_path = run_root / "startup" / "startup_fact_report.json"
    envelope = payload.get("_role_output_envelope")
    if isinstance(envelope, dict) and envelope.get("body_path"):
        source_path = resolve_project_path(project_root, str(envelope["body_path"]))
        if source_path.resolve() == canonical_report_path.resolve():
            raise RouterError("startup fact source report_path must not be the router canonical startup_fact_report.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("startup fact report must be reviewed_by_role=human_like_reviewer")
    computed_checks = _startup_fact_checks(project_root, run_root, run_state)
    claimed_checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    false_claims = [name for name, value in claimed_checks.items() if value is not True]
    passed = payload.get("passed") is True
    if passed and false_claims:
        raise RouterError(f"startup fact report contains failed checks: {', '.join(sorted(false_claims))}")
    blockers = [name for name, ok in computed_checks.items() if not ok]
    if passed and blockers:
        raise RouterError(f"startup facts are not clean: {', '.join(sorted(blockers))}")
    mechanical_context = _startup_mechanical_audit_context(project_root, run_root, run_state)
    if mechanical_context is None:
        raise RouterError("startup mechanical audit must be written before reviewer startup fact report")
    mechanical_audit = mechanical_context["audit"]
    if mechanical_audit.get("mechanical_checks") != computed_checks:
        raise RouterError("startup mechanical audit is stale; rewrite it before reviewer startup fact report")
    external_fact_review = _validate_startup_external_fact_review(
        payload,
        mechanical_audit["reviewer_required_external_facts"],
        startup_mechanical_audit_hash=mechanical_context["audit_hash"],
    )
    write_json(
        canonical_report_path,
        {
            "schema_version": "flowpilot.startup_fact_report.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "passed": passed,
            "status": "pass" if passed else "findings",
            "checks": computed_checks,
            "reviewer_claimed_checks": claimed_checks,
            "reviewer_reported_blockers": payload.get("blockers") if isinstance(payload.get("blockers"), list) else false_claims or blockers,
            "startup_mechanical_audit_path": project_relative(project_root, mechanical_context["audit_path"]),
            "startup_mechanical_audit_hash": mechanical_context["audit_hash"],
            "router_owned_check_proof_path": project_relative(project_root, mechanical_context["proof_path"]),
            "router_owned_check_proof_hash": mechanical_context["proof_hash"],
            "reviewer_required_external_facts": mechanical_audit["reviewer_required_external_facts"],
            "external_fact_review": external_fact_review,
            "requires_pm_startup_decision": not passed,
            "reviewer_directly_blocks_route": False,
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_startup_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("approved_by_role") != "project_manager":
        raise RouterError("PM startup activation requires approved_by_role=project_manager")
    if payload.get("decision") != "approved":
        raise RouterError("PM startup activation requires decision=approved")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    fact_report_path = run_root / "startup" / "startup_fact_report.json"
    if not fact_report_path.exists():
        raise RouterError("PM startup activation requires reviewer startup_fact_report.json")
    clean_report = fact_report.get("passed") is True and fact_report.get("status") == "pass"
    approval_basis = "clean_reviewer_fact_report"
    findings_decision: dict[str, Any] | None = None
    if not clean_report:
        if fact_report.get("status") != "findings" or fact_report.get("requires_pm_startup_decision") is not True:
            raise RouterError("PM startup activation requires a passing reviewer startup fact report or PM findings decision")
        if payload.get("accepts_startup_findings_with_reason") is not True:
            raise RouterError("PM startup activation from reviewer findings requires accepts_startup_findings_with_reason=true")
        reason = str(payload.get("startup_findings_decision_reason") or "").strip()
        if not reason:
            raise RouterError("PM startup activation from reviewer findings requires startup_findings_decision_reason")
        reviewed_report = payload.get("reviewed_report_path") or project_relative(project_root, fact_report_path)
        if resolve_project_path(project_root, str(reviewed_report)).resolve() != fact_report_path.resolve():
            raise RouterError("PM startup activation reviewed_report_path must reference startup_fact_report.json")
        decision_kind = str(payload.get("startup_findings_decision") or "waived_with_reason")
        if decision_kind not in {"waived_with_reason", "unreviewable_requirement_demoted", "accepted_with_documented_risk"}:
            raise RouterError("PM startup activation startup_findings_decision is invalid")
        approval_basis = "pm_file_backed_findings_decision"
        findings_decision = {
            "startup_findings_decision": decision_kind,
            "startup_findings_decision_reason": reason,
            "reviewed_report_path": project_relative(project_root, fact_report_path),
            "reviewed_report_hash": packet_runtime.sha256_file(fact_report_path),
            "reviewer_findings_accepted_by_pm": True,
            "demoted_unreviewable_requirement_ids": payload.get("demoted_unreviewable_requirement_ids")
            if isinstance(payload.get("demoted_unreviewable_requirement_ids"), list)
            else [],
        }
    answers = _startup_answers_from_run(run_root)
    activation = {
        "schema_version": "flowpilot.startup_activation.v1",
        "run_id": run_state["run_id"],
        "approved_by_role": "project_manager",
        "decision": "approved",
        "background_agents": answers.get("background_agents"),
        "scheduled_continuation": answers.get("scheduled_continuation"),
        "display_surface": answers.get("display_surface"),
        "fact_report_path": project_relative(project_root, fact_report_path),
        "approval_basis": approval_basis,
        "approved_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    if findings_decision is not None:
        activation["pm_findings_decision"] = findings_decision
    write_json(run_root / "startup" / "startup_activation.json", activation)


def _write_startup_repair_request(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decided_by_role") != "project_manager":
        raise RouterError("startup repair request requires decided_by_role=project_manager")
    if payload.get("decision") not in {"startup_repair_requested", "repair_requested"}:
        raise RouterError("startup repair request requires decision=startup_repair_requested")
    target = str(payload.get("target_role_or_system") or "").strip()
    allowed_targets = {"flowpilot_router", "human_like_reviewer", "project_manager", "worker_a", "worker_b"}
    if target not in allowed_targets:
        raise RouterError(f"startup repair request target_role_or_system must be one of: {', '.join(sorted(allowed_targets))}")
    repair_action = str(payload.get("repair_action") or "").strip()
    if not repair_action:
        raise RouterError("startup repair request requires repair_action")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    if fact_report.get("passed") is True:
        raise RouterError("startup repair request requires a non-passing reviewer startup fact report")
    current_blocked_report_path = run_root / "startup" / "startup_fact_report.json"
    if not current_blocked_report_path.exists():
        raise RouterError("startup repair request requires the current non-passing startup_fact_report.json")
    requested_blocked_report = payload.get("blocked_report_path") or project_relative(project_root, current_blocked_report_path)
    requested_blocked_report_path = resolve_project_path(project_root, str(requested_blocked_report))
    if requested_blocked_report_path.resolve() != current_blocked_report_path.resolve():
        raise RouterError("startup repair request blocked_report_path must be the current canonical startup_fact_report.json")
    blocked_report_hash = packet_runtime.sha256_file(current_blocked_report_path)
    envelope = payload.get("_role_output_envelope") if isinstance(payload.get("_role_output_envelope"), dict) else {}
    decision_hash = str(envelope.get("body_hash") or "")
    if not decision_hash:
        raise RouterError("startup repair request requires a file-backed PM decision hash")
    previous_request = run_state.get("startup_repair_request") if isinstance(run_state.get("startup_repair_request"), dict) else {}
    last_decision_hash = str(previous_request.get("decision_hash") or "")
    if last_decision_hash and decision_hash == last_decision_hash:
        raise RouterError(
            "startup repair request repeats the previous PM decision; write a fresh PM decision for the current blocking report"
        )
    startup_repair_cycle = int(run_state.get("startup_repair_cycle") or 0) + 1
    record = {
        "schema_version": "flowpilot.startup_repair_request.v1",
        "run_id": run_state["run_id"],
        "startup_repair_cycle": startup_repair_cycle,
        "decided_by_role": "project_manager",
        "decision": "startup_repair_requested",
        "repair_target_kind": payload.get("repair_target_kind") or ("system" if target == "flowpilot_router" else "role"),
        "target_role_or_system": target,
        "repair_action": repair_action,
        "blocked_report_path": project_relative(project_root, current_blocked_report_path),
        "blocked_report_hash": blocked_report_hash,
        "decision_path": envelope.get("body_path"),
        "decision_hash": decision_hash,
        "resume_event": payload.get("resume_event") or "reviewer_reports_startup_facts",
        "resume_condition": payload.get("resume_condition") or "targeted startup repair is complete and reviewer writes a fresh startup fact report",
        "controller_may_invent_repair": False,
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    cycle_path = run_root / "startup" / f"startup_repair_request.cycle-{startup_repair_cycle:03d}.json"
    write_json(cycle_path, record)
    write_json(run_root / "startup" / "startup_repair_request.json", record)
    ledger_path = run_root / "startup" / "startup_repair_requests.json"
    ledger = read_json_if_exists(ledger_path)
    entries = ledger.get("entries") if isinstance(ledger.get("entries"), list) else []
    entries.append(
        {
            "startup_repair_cycle": startup_repair_cycle,
            "path": project_relative(project_root, cycle_path),
            "blocked_report_path": record["blocked_report_path"],
            "blocked_report_hash": blocked_report_hash,
            "decision_path": record["decision_path"],
            "decision_hash": decision_hash,
            "target_role_or_system": target,
            "repair_action": repair_action,
            "recorded_at": record["recorded_at"],
        }
    )
    write_json(
        ledger_path,
        {
            "schema_version": "flowpilot.startup_repair_requests.v1",
            "run_id": run_state["run_id"],
            "entries": entries,
            "latest_cycle": startup_repair_cycle,
            "updated_at": utc_now(),
        },
    )
    for flag in (
        "startup_fact_reported",
        "pm_startup_activation_card_delivered",
        "startup_activation_approved",
        "startup_mechanical_audit_written",
        "reviewer_startup_fact_check_card_delivered",
    ):
        run_state["flags"][flag] = False
    run_state["startup_repair_cycle"] = startup_repair_cycle
    run_state["startup_repair_request"] = {
        "path": project_relative(project_root, run_root / "startup" / "startup_repair_request.json"),
        "cycle_path": project_relative(project_root, cycle_path),
        "ledger_path": project_relative(project_root, ledger_path),
        "startup_repair_cycle": startup_repair_cycle,
        "target_role_or_system": target,
        "repair_action": repair_action,
        "blocked_report_hash": blocked_report_hash,
        "decision_hash": decision_hash,
        "resume_event": record["resume_event"],
    }


def _write_startup_protocol_dead_end(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("declared_by_role") != "project_manager":
        raise RouterError("startup protocol dead-end requires declared_by_role=project_manager")
    if payload.get("decision") != "protocol_dead_end":
        raise RouterError("startup protocol dead-end requires decision=protocol_dead_end")
    if payload.get("no_legal_repair_path") is not True:
        raise RouterError("startup protocol dead-end requires no_legal_repair_path=true")
    reason = str(payload.get("why_no_existing_path_applies") or "").strip()
    if not reason:
        raise RouterError("startup protocol dead-end requires why_no_existing_path_applies")
    attempted_paths = payload.get("attempted_legal_paths")
    if not isinstance(attempted_paths, list) or not attempted_paths:
        raise RouterError("startup protocol dead-end requires attempted_legal_paths")
    resume_conditions = payload.get("resume_conditions")
    if not isinstance(resume_conditions, list) or not resume_conditions:
        raise RouterError("startup protocol dead-end requires resume_conditions")
    fact_report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    if fact_report.get("passed") is True:
        raise RouterError("startup protocol dead-end requires a non-passing reviewer startup fact report")
    dead_end_path = run_root / "lifecycle" / "startup_protocol_dead_end.json"
    record = {
        "schema_version": "flowpilot.startup_protocol_dead_end.v1",
        "run_id": run_state["run_id"],
        "declared_by_role": "project_manager",
        "decision": "protocol_dead_end",
        "dead_end_type": payload.get("dead_end_type") or "startup_block_has_no_protocol_route",
        "no_legal_repair_path": True,
        "why_no_existing_path_applies": reason,
        "attempted_legal_paths": attempted_paths,
        "conceptual_repair_direction": payload.get("conceptual_repair_direction"),
        "unsafe_to_continue_reason": payload.get("unsafe_to_continue_reason") or reason,
        "blocked_report_path": payload.get("blocked_report_path") or project_relative(project_root, run_root / "startup" / "startup_fact_report.json"),
        "effects": {
            "freeze_run": True,
            "cancel_or_suspend_pending_mail": True,
            "prevent_work_beyond_startup": True,
            "heartbeat_should_stop": False,
            "heartbeat_should_remain_for_resume_or_user_decision": True,
            **(payload.get("effects") if isinstance(payload.get("effects"), dict) else {}),
        },
        "resume_conditions": resume_conditions,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "declared_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(dead_end_path, record)
    run_state["flags"]["startup_pending_mail_suspended_after_dead_end"] = True
    _write_protocol_dead_end_lifecycle(
        project_root,
        run_root,
        run_state,
        dead_end_path=dead_end_path,
        reason=reason,
    )


def _route_sign_payload(
    project_root: Path,
    *,
    write: bool,
    trigger: str,
    mark_chat_displayed: bool,
    cockpit_open: bool = False,
    mark_ui_displayed: bool = False,
) -> dict[str, Any]:
    return flowpilot_user_flow_diagram.generate(
        project_root,
        write=write,
        trigger=trigger,
        cockpit_open=cockpit_open,
        display_surface="both" if cockpit_open else "chat",
        mark_chat_displayed=mark_chat_displayed,
        mark_ui_displayed=mark_ui_displayed,
        reviewer_check=False,
    )


def _startup_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return _route_sign_payload(
        project_root,
        write=write,
        trigger="startup",
        mark_chat_displayed=mark_chat_displayed,
    )


def _route_map_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return _route_sign_payload(
        project_root,
        write=write,
        trigger="key_node_change",
        mark_chat_displayed=mark_chat_displayed,
    )


def _route_sign_has_canonical_route(payload: dict[str, Any]) -> bool:
    return (
        payload.get("flowpilot_path_status") == "ok"
        and int(payload.get("route_node_count") or 0) > 0
        and str(payload.get("route_source_kind") or "none") != "none"
    )


def _display_surface_receipt_from_payload(
    payload: dict[str, Any],
    *,
    run_id: str,
    requested: str,
    selected_surface: str,
) -> dict[str, Any]:
    receipt = payload.get("display_surface_receipt") if isinstance(payload, dict) else None
    if receipt is None:
        return {
            "schema_version": DISPLAY_SURFACE_RECEIPT_SCHEMA,
            "run_id": run_id,
            "requested_display_surface": requested,
            "actual_surface": selected_surface,
            "source_kind": "controller_user_dialog_render",
            "host_display_surface_verified": False,
            "fallback_displayed": selected_surface != "cockpit",
            "recorded_at": utc_now(),
        }
    if not isinstance(receipt, dict):
        raise RouterError("display_surface_receipt must be an object when supplied")
    if receipt.get("schema_version") != DISPLAY_SURFACE_RECEIPT_SCHEMA:
        raise RouterError(f"display_surface_receipt requires schema_version={DISPLAY_SURFACE_RECEIPT_SCHEMA}")
    actual = receipt.get("actual_surface")
    if actual not in {"chat_route_sign", "chat_route_sign_fallback", "cockpit"}:
        raise RouterError("display_surface_receipt.actual_surface must be chat_route_sign, chat_route_sign_fallback, or cockpit")
    if receipt.get("run_id") not in {None, run_id}:
        raise RouterError("display_surface_receipt.run_id must match current run_id")
    if actual == "cockpit" and receipt.get("host_display_surface_verified") is not True:
        raise RouterError("display_surface_receipt for cockpit requires host_display_surface_verified=true")
    return {
        "schema_version": DISPLAY_SURFACE_RECEIPT_SCHEMA,
        "run_id": run_id,
        "requested_display_surface": requested,
        "actual_surface": actual,
        "source_kind": str(receipt.get("source_kind") or "host_receipt"),
        "host_display_surface_verified": bool(receipt.get("host_display_surface_verified")),
        "fallback_displayed": bool(receipt.get("fallback_displayed", actual != "cockpit")),
        "host_surface_id": receipt.get("host_surface_id"),
        "notes": receipt.get("notes"),
        "recorded_at": utc_now(),
    }


def _write_display_surface_status(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    display_confirmation: dict[str, Any],
    payload: dict[str, Any] | None = None,
) -> None:
    answers = _startup_answers_from_run(run_root)
    requested = str(answers.get("display_surface") or "chat route signs")
    requested_normalized = requested.lower()
    selected_surface = "chat_route_sign" if "chat" in requested_normalized else "chat_route_sign_fallback"
    display_receipt = _display_surface_receipt_from_payload(
        payload or {},
        run_id=str(run_state["run_id"]),
        requested=requested,
        selected_surface=selected_surface,
    )
    actual_surface = str(display_receipt.get("actual_surface") or selected_surface)
    if actual_surface == "cockpit":
        selected_surface = "cockpit"
    route_sign = _startup_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
    sign_path = run_root / "diagrams" / "current_route_sign.md"
    sign_path.parent.mkdir(parents=True, exist_ok=True)
    sign_path.write_text(route_sign["markdown"], encoding="utf-8")
    write_json(
        run_root / "display" / "display_surface.json",
        {
            "schema_version": "flowpilot.display_surface.v1",
            "run_id": run_state["run_id"],
            "requested_display_surface": requested,
            "selected_surface": selected_surface,
            "actual_display_surface": actual_surface,
            "chat_route_sign_path": project_relative(project_root, sign_path),
            "standard_route_sign_markdown_path": project_relative(project_root, Path(route_sign["markdown_preview_path"])),
            "standard_route_sign_mermaid_path": project_relative(project_root, Path(route_sign["mermaid_path"])),
            "standard_route_sign_display_packet_path": project_relative(project_root, Path(route_sign["display_packet_path"])),
            "route_sign_mermaid_sha256": route_sign["mermaid_sha256"],
            "chat_display_required": route_sign["chat_display_required"],
            "chat_displayed_by_controller": True,
            "user_dialog_display_confirmation": display_confirmation,
            "display_surface_receipt": display_receipt,
            "host_display_surface_verified": bool(display_receipt.get("host_display_surface_verified")),
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Controller must paste the router-provided display_text Mermaid block in chat before applying this action; generated files alone do not satisfy display.",
            "cockpit_status": "host_verified_open" if selected_surface == "cockpit" else "not_started_in_router_runtime",
            "cockpit_probe_required_for_requested_cockpit": "cockpit" in requested_normalized,
            "reviewer_fallback_check_required_for_requested_cockpit": "cockpit" in requested_normalized,
            "fallback_is_display_only_not_product_ui_completion": True,
            "updated_at": utc_now(),
        },
    )


def _material_packet_body_text_from_spec(project_root: Path, spec: dict[str, Any]) -> str:
    body_text = spec.get("body_text")
    if isinstance(body_text, str) and body_text.strip():
        return body_text
    raw_body_path = spec.get("body_path") or spec.get("packet_body_path")
    raw_body_hash = spec.get("body_hash") or spec.get("packet_body_hash")
    if not raw_body_path or not raw_body_hash:
        raise RouterError("material scan packet requires non-empty body_text or file-backed body_path/body_hash")
    body_path = resolve_project_path(project_root, str(raw_body_path))
    if not body_path.exists():
        raise RouterError(f"material scan packet body path is missing: {raw_body_path}")
    actual_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()
    if actual_hash != str(raw_body_hash):
        raise RouterError("material scan packet body hash mismatch")
    loaded_text = body_path.read_text(encoding="utf-8")
    if not loaded_text.strip():
        raise RouterError("material scan packet body file is empty")
    return loaded_text


def _write_material_scan_packets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    packet_specs = payload.get("packets")
    if not isinstance(packet_specs, list) or not packet_specs:
        raise RouterError("material scan requires payload.packets with PM-authored packet bodies")
    records: list[dict[str, Any]] = []
    batch_id = str(payload.get("batch_id") or "material-scan-batch-001")
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError("each material scan packet must be an object")
        packet_id = str(spec.get("packet_id") or f"material-scan-{index:03d}")
        to_role = str(spec.get("to_role") or "worker_a")
        if to_role not in {"worker_a", "worker_b"}:
            raise RouterError("material scan packet must target worker_a or worker_b")
        body_text = _material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(
            project_root,
            run_id=str(run_state["run_id"]),
            packet_id=packet_id,
            from_role="project_manager",
            to_role=to_role,
            node_id=str(spec.get("node_id") or "material-intake"),
            body_text=body_text,
            is_current_node=False,
            packet_type="material_scan",
            metadata={
                "stage": "material_scan",
                "source": "pm_issues_material_and_capability_scan_packets",
                **(spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}),
            },
            output_contract=spec.get("output_contract") if isinstance(spec.get("output_contract"), dict) else None,
        )
        records.append(_packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type="material_scan"))
    _write_parallel_packet_batch(
        project_root,
        run_root,
        run_state,
        batch_id=batch_id,
        batch_kind="material_scan",
        phase="material_scan",
        records=records,
        node_id="material-intake",
        join_policy="all_results_before_review",
        review_policy="batch_material_sufficiency_review_before_pm",
        pm_absorption_required=True,
    )
    write_json(
        _material_scan_index_path(run_root),
        {
            "schema_version": "flowpilot.material_scan_packets.v1",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "batch_id": batch_id,
            "batch_kind": "material_scan",
            "controller_may_read_packet_body": False,
            "router_direct_dispatch_required_before_worker": True,
            "reviewer_dispatch_required_before_worker": False,
            "packets": records,
            "written_at": utc_now(),
        },
    )
    _set_pre_route_frontier_phase(run_root, str(run_state["run_id"]), "material_scan")


def _write_material_dispatch_block_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    checked_by_role = str(payload.get("checked_by_role") or payload.get("reviewed_by_role") or "").strip()
    if checked_by_role not in {"controller", "router", "human_like_reviewer"}:
        raise RouterError("material dispatch block report requires checked_by_role=controller/router or reviewed_by_role=human_like_reviewer")
    if payload.get("dispatch_allowed") is not False:
        raise RouterError("material dispatch block report requires dispatch_allowed=false")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise RouterError("material dispatch block report requires non-empty blockers")
    material_index_path = _material_scan_index_path(run_root)
    if not material_index_path.exists():
        raise RouterError("material dispatch block report requires material scan packet index")
    report_path = run_root / "material" / "material_dispatch_block.json"
    reported_at = utc_now()
    write_json(
        report_path,
        {
            "schema_version": "flowpilot.material_dispatch_block.v1",
            "run_id": run_state["run_id"],
            "checked_by_role": checked_by_role,
            "dispatch_allowed": False,
            "source_paths": [project_relative(project_root, material_index_path)],
            "checks": payload.get("checks") if isinstance(payload.get("checks"), dict) else {},
            "blockers": blockers,
            "residual_risks": payload.get("residual_risks") if isinstance(payload.get("residual_risks"), list) else [],
            "reported_at": reported_at,
            **_role_output_envelope_record(payload),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": project_relative(project_root, report_path),
        "blockers": blockers,
        "reported_at": reported_at,
    }
    run_state["flags"]["reviewer_dispatch_allowed"] = False


def _write_material_dispatch_recheck_protocol_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    event_name: str = "router_protocol_blocker_material_scan_dispatch_recheck",
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    checked_by_role = str(payload.get("checked_by_role") or payload.get("reviewed_by_role") or "").strip()
    if checked_by_role not in {"controller", "router", "human_like_reviewer"}:
        raise RouterError("material dispatch recheck protocol blocker requires checked_by_role=controller/router or reviewed_by_role=human_like_reviewer")
    blockers = payload.get("blockers")
    if not isinstance(blockers, list) or not blockers:
        raise RouterError("material dispatch recheck protocol blocker requires non-empty blockers")
    tx_path, transaction = _active_repair_transaction_for_event(
        run_root,
        event_name,
    )
    if tx_path is None or transaction is None:
        raise RouterError("material dispatch protocol blocker requires an active repair transaction")
    reported_at = utc_now()
    report_path = run_root / "control_blocks" / f"{transaction['transaction_id']}.reviewer_protocol_blocker.json"
    write_json(
        report_path,
        {
            "schema_version": "flowpilot.repair_transaction_protocol_blocker.v1",
            "run_id": run_state["run_id"],
            "repair_transaction_id": transaction["transaction_id"],
            "checked_by_role": checked_by_role,
            "event_name": event_name,
            "blockers": blockers,
            "source_paths": payload.get("source_paths") if isinstance(payload.get("source_paths"), list) else [],
            "residual_risks": payload.get("residual_risks") if isinstance(payload.get("residual_risks"), list) else [],
            "reported_at": reported_at,
            **_role_output_envelope_record(payload),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": project_relative(project_root, report_path),
        "blockers": blockers,
        "reported_at": reported_at,
        "repair_transaction_id": transaction["transaction_id"],
        "protocol_blocker": True,
    }
    run_state["flags"]["reviewer_dispatch_allowed"] = False


def _write_material_sufficiency_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, sufficient: bool) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("material sufficiency report must be reviewed_by_role=human_like_reviewer")
    if not run_state["flags"].get("material_scan_results_relayed_to_reviewer"):
        raise RouterError("material sufficiency report requires material result envelopes made available to reviewer")
    material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
    raw_agent_map = payload.get("agent_role_map")
    _validate_packet_group_for_reviewer(
        project_root,
        run_state,
        material_index["packets"],
        audit_path=run_root / "material" / "material_packet_review_audit.json",
        agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None,
    )
    if payload.get("direct_material_sources_checked") is not True:
        raise RouterError("material sufficiency report requires direct_material_sources_checked=true")
    if payload.get("packet_matches_checked_sources") is not True:
        raise RouterError("material sufficiency report requires packet_matches_checked_sources=true")
    if sufficient and payload.get("pm_ready") is not True:
        raise RouterError("sufficient material report requires pm_ready=true")
    write_json(
        run_root / "material" / "material_sufficiency_report.json",
        {
            "schema_version": "flowpilot.material_sufficiency_report.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "sufficient": sufficient,
            "direct_material_sources_checked": True,
            "packet_matches_checked_sources": True,
            "pm_ready": bool(payload.get("pm_ready")),
            "checked_source_paths": payload.get("checked_source_paths") or [],
            "blockers": payload.get("blockers") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_research_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    decision_question = payload.get("decision_question")
    if not decision_question:
        raise RouterError("research package requires decision_question")
    packet_specs = payload.get("packets")
    if packet_specs is not None and (not isinstance(packet_specs, list) or not packet_specs):
        raise RouterError("research package packets must be a non-empty list when provided")
    package = {
        "schema_version": "flowpilot.research_package.v1",
        "run_id": run_state["run_id"],
        "written_by_role": "project_manager",
        "decision_question": decision_question,
        "allowed_source_types": payload.get("allowed_source_types") or [],
        "host_capability_decision": payload.get("host_capability_decision") or "local_sources_only",
        "worker_owner": payload.get("worker_owner") or "worker_a",
        "batch_id": payload.get("batch_id") or "research-batch-001",
        "packets": packet_specs or [],
        "reviewer_direct_check_required": True,
        "stop_conditions": payload.get("stop_conditions") or [],
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "research" / "research_package.json", package)


def _write_research_capability_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    package_path = run_root / "research" / "research_package.json"
    if not package_path.exists():
        raise RouterError("research capability decision requires research_package.json")
    if payload.get("explicit_user_approval_required") is True and payload.get("explicit_user_approval_recorded") is not True:
        raise RouterError("research capability decision requires recorded user approval for gated sources")
    package = read_json(package_path)
    worker_owner = str(package.get("worker_owner") or "worker_a")
    if worker_owner not in {"worker_a", "worker_b"}:
        raise RouterError("research worker owner must be worker_a or worker_b")
    batch_id = str(payload.get("batch_id") or package.get("batch_id") or "research-batch-001")
    allowed_source_types = list(package.get("allowed_source_types") or [])
    allowed_sources = payload.get("allowed_sources")
    if not isinstance(allowed_sources, list) or not allowed_sources:
        allowed_sources = allowed_source_types
    stop_conditions = list(package.get("stop_conditions") or [])
    research_body_payload = {
        "research_package_path": project_relative(project_root, package_path),
        "decision_question": package.get("decision_question"),
        "allowed_source_types": allowed_source_types,
        "allowed_sources": allowed_sources,
        "host_capability_decision": package.get("host_capability_decision"),
        "worker_owner": worker_owner,
        "reviewer_direct_check_required": bool(package.get("reviewer_direct_check_required")),
        "stop_conditions": stop_conditions,
    }
    raw_packet_specs = payload.get("packets") if isinstance(payload.get("packets"), list) else package.get("packets")
    packet_specs = raw_packet_specs if isinstance(raw_packet_specs, list) and raw_packet_specs else [
        {
            "packet_id": payload.get("packet_id") or "research-packet-001",
            "to_role": worker_owner,
            "body_text": payload.get("worker_packet_body"),
            "output_contract": payload.get("output_contract") if isinstance(payload.get("output_contract"), dict) else None,
        }
    ]
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError("each research packet spec must be an object")
        to_role = str(spec.get("to_role") or spec.get("recipient_role") or worker_owner)
        if to_role not in {"worker_a", "worker_b", "process_flowguard_officer", "product_flowguard_officer"}:
            raise RouterError("research packets may target workers or FlowGuard officers only")
        packet_type = "officer_request" if to_role in {"process_flowguard_officer", "product_flowguard_officer"} else "research"
        packet_id = str(spec.get("packet_id") or f"research-packet-{index:03d}")
        body_text = spec.get("body_text")
        if body_text is None:
            body_text = json.dumps(
                {
                    **research_body_payload,
                    "batch_id": batch_id,
                    "packet_focus": spec.get("packet_focus") or spec.get("request_kind") or "research",
                },
                indent=2,
                sort_keys=True,
            )
        if not isinstance(body_text, str) or not body_text.strip():
            raise RouterError("research packet requires non-empty body_text")
        output_contract = spec.get("output_contract") if isinstance(spec.get("output_contract"), dict) else None
        if output_contract is None and packet_type == "officer_request":
            output_contract = _pm_role_work_output_contract(
                run_root,
                contract_id=str(spec.get("output_contract_id") or "flowpilot.output_contract.officer_model_report.v1"),
                to_role=to_role,
                packet_type=packet_type,
                node_id="research",
            )
        envelope = packet_runtime.create_packet(
            project_root,
            run_id=str(run_state["run_id"]),
            packet_id=packet_id,
            from_role="project_manager",
            to_role=to_role,
            node_id="research",
            body_text=body_text,
            is_current_node=False,
            packet_type=packet_type,
            metadata={
                "stage": "research",
                "source": "research_capability_decision_recorded",
                "batch_id": batch_id,
                "research_package_path": project_relative(project_root, package_path),
                **(spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}),
            },
            output_contract=output_contract,
        )
        records.append(_packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=packet_type))
    _write_parallel_packet_batch(
        project_root,
        run_root,
        run_state,
        batch_id=batch_id,
        batch_kind="research",
        phase="research",
        records=records,
        node_id="research",
        join_policy="all_results_before_review",
        review_policy="batch_research_direct_source_review_before_pm",
        pm_absorption_required=True,
    )
    write_json(
        run_root / "research" / "research_capability_decision.json",
        {
            "schema_version": "flowpilot.research_capability_decision.v1",
            "run_id": run_state["run_id"],
            "recorded_by_role": "project_manager",
            "research_package_path": project_relative(project_root, package_path),
            "decision_question": package.get("decision_question"),
            "allowed_source_types": allowed_source_types,
            "allowed_sources": allowed_sources,
            "host_capability_decision": package.get("host_capability_decision"),
            "worker_owner": worker_owner,
            "batch_id": batch_id,
            "reviewer_direct_check_required": bool(package.get("reviewer_direct_check_required")),
            "stop_conditions": stop_conditions,
            "explicit_user_approval_required": bool(payload.get("explicit_user_approval_required")),
            "explicit_user_approval_recorded": bool(payload.get("explicit_user_approval_recorded")),
            "worker_packet_id": records[0]["packet_id"],
            "packet_ids": [record["packet_id"] for record in records],
            "recorded_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    write_json(
        _research_packet_index_path(run_root),
        {
            "schema_version": "flowpilot.research_packet.v1",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "batch_id": batch_id,
            "packet_id": records[0]["packet_id"],
            "worker_owner": worker_owner,
            "controller_may_read_packet_body": False,
            "packet_envelope_path": records[0]["packet_envelope_path"],
            "packet_body_path": records[0].get("packet_body_path"),
            "packet_body_hash": records[0].get("packet_body_hash"),
            "body_path": records[0].get("packet_body_path"),
            "body_hash": records[0].get("packet_body_hash"),
            "result_envelope_path": records[0]["result_envelope_path"],
            "packets": records,
            "written_at": utc_now(),
        },
    )


def _write_pm_role_work_request(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise RouterError("PM role-work request payload must be an object")
    raw_batch = payload.get("requests") if isinstance(payload.get("requests"), list) else payload.get("packets")
    if isinstance(raw_batch, list):
        if not raw_batch:
            raise RouterError("PM role-work request batch requires at least one request")
        batch_id = str(payload.get("batch_id") or "pm-role-work-batch-001")
        request_ids: list[str] = []
        to_roles: list[str] = []
        for index, spec in enumerate(raw_batch, start=1):
            if not isinstance(spec, dict):
                raise RouterError("PM role-work request batch entries must be objects")
            request_id = str(spec.get("request_id") or f"{batch_id}-request-{index:03d}")
            to_role = str(spec.get("to_role") or spec.get("recipient_role") or "")
            if to_role in to_roles:
                raise RouterError("PM role-work request batch cannot assign two open packets to the same role")
            to_roles.append(to_role)
            request_ids.append(request_id)
            single_payload = {
                **payload,
                **spec,
                "request_id": request_id,
                "batch_id": batch_id,
            }
            single_payload.pop("requests", None)
            single_payload.pop("packets", None)
            _write_pm_role_work_request(project_root, run_root, run_state, single_payload)
        index_doc = _load_pm_role_work_request_index(run_root, run_state)
        records = [
            record
            for request_id in request_ids
            if isinstance((record := _pm_role_work_request_record(index_doc, request_id)), dict)
        ]
        _write_parallel_packet_batch(
            project_root,
            run_root,
            run_state,
            batch_id=batch_id,
            batch_kind="pm_role_work",
            phase="pm_role_work_request",
            records=records,
            node_id=str(payload.get("node_id") or "pm-role-work"),
            join_policy="all_results_before_pm_absorption",
            review_policy="pm_absorbs_batch_without_reviewer_unless_packet_requires_review",
            pm_absorption_required=True,
        )
        index_doc["active_batch_id"] = batch_id
        index_doc["active_request_ids"] = request_ids
        index_doc["active_request_id"] = request_ids[0] if request_ids else None
        _write_pm_role_work_request_index(run_root, index_doc)
        run_state["pm_role_work_requests"] = {
            "index_path": project_relative(project_root, _pm_role_work_request_index_path(run_root)),
            "active_batch_id": batch_id,
            "active_request_ids": request_ids,
            "active_request_mode": payload.get("request_mode") or payload.get("mode") or "blocking",
        }
        return
    if not _pm_role_work_channel_open(run_state):
        raise RouterError("PM role-work request requires an open PM decision context")
    requested_by_role = str(payload.get("requested_by_role") or payload.get("from_role") or "").strip()
    if requested_by_role != "project_manager":
        raise RouterError("PM role-work request requires requested_by_role=project_manager")
    request_id = str(payload.get("request_id") or "").strip()
    if not request_id:
        raise RouterError("PM role-work request requires request_id")
    to_role = str(payload.get("to_role") or payload.get("recipient_role") or "").strip()
    if to_role not in PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES:
        raise RouterError("PM role-work request must target a FlowPilot role other than PM or Controller")
    request_mode = str(payload.get("request_mode") or payload.get("mode") or "").strip()
    if request_mode not in PM_ROLE_WORK_REQUEST_MODES:
        raise RouterError("PM role-work request requires request_mode=blocking or advisory")
    request_kind = str(payload.get("request_kind") or payload.get("kind") or "").strip()
    if request_kind not in PM_ROLE_WORK_REQUEST_KINDS:
        raise RouterError("PM role-work request has unsupported request_kind")
    output_contract = payload.get("output_contract") if isinstance(payload.get("output_contract"), dict) else {}
    output_contract_id = str(
        payload.get("output_contract_id")
        or output_contract.get("contract_id")
        or ""
    ).strip()
    if not output_contract_id:
        raise RouterError("PM role-work request requires output_contract_id")
    index = _load_pm_role_work_request_index(run_root, run_state)
    existing = _pm_role_work_request_record(index, request_id)
    if isinstance(existing, dict) and existing.get("status") in PM_ROLE_WORK_OPEN_STATUSES:
        raise RouterError(f"PM role-work request_id is already open: {request_id}")
    body_text, body_ref = _pm_role_work_request_body_text(project_root, payload)
    _validate_pm_role_work_request_against_followup(
        run_state,
        request_id=request_id,
        to_role=to_role,
        request_kind=request_kind,
        output_contract_id=output_contract_id,
    )
    process_binding = _validate_pm_role_work_process_contract_binding(
        contract_id=output_contract_id,
        to_role=to_role,
        request_kind=request_kind,
    )
    node_id = str(payload.get("node_id") or "pm-role-work").strip() or "pm-role-work"
    packet_id = str(payload.get("packet_id") or f"pm-role-work-{_safe_packet_id_component(request_id)}")
    packet_type = str(process_binding["packet_type"])
    validated_packet_type = _pm_role_work_packet_type_from_contract(
        run_root,
        contract_id=output_contract_id,
        to_role=to_role,
        request_kind=request_kind,
    )
    if validated_packet_type != packet_type:
        raise RouterError("PM role-work packet type does not match process contract binding")
    selected_contract = dict(output_contract) if output_contract else _pm_role_work_output_contract(
        run_root,
        contract_id=output_contract_id,
        to_role=to_role,
        packet_type=packet_type,
        node_id=node_id,
    )
    if output_contract:
        if str(selected_contract.get("contract_id") or output_contract_id) != output_contract_id:
            raise RouterError("PM role-work output_contract.contract_id must match output_contract_id")
        supplied_task_family = str(selected_contract.get("task_family") or process_binding["task_family"])
        if supplied_task_family != process_binding["task_family"]:
            raise RouterError("PM role-work output_contract.task_family must match process contract binding")
        selected_contract["contract_id"] = output_contract_id
        selected_contract.setdefault("selected_by_role", "project_manager")
        selected_contract.setdefault("recipient_role", to_role)
        selected_contract.setdefault("node_id", node_id)
        selected_contract.setdefault("packet_type", packet_type)
    selected_contract["process_kind"] = process_binding["process_kind"]
    selected_contract["task_family"] = process_binding["task_family"]
    selected_contract["required_result_next_recipient"] = process_binding["required_result_next_recipient"]
    selected_contract["absorbing_role"] = process_binding["absorbing_role"]
    envelope = packet_runtime.create_packet(
        project_root,
        run_id=str(run_state["run_id"]),
        packet_id=packet_id,
        from_role="project_manager",
        to_role=to_role,
        node_id=node_id,
        body_text=body_text,
        is_current_node=False,
        packet_type=packet_type,
        metadata={
            "source": PM_ROLE_WORK_REQUEST_EVENT,
            "request_id": request_id,
            "request_kind": request_kind,
            "request_mode": request_mode,
            "pm_role_work_request": True,
            "strict_process_contract_binding": True,
            "process_contract_binding": process_binding,
        },
        output_contract=selected_contract,
    )
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
    record = {
        "schema_version": PM_ROLE_WORK_REQUEST_SCHEMA,
        "request_id": request_id,
        "batch_id": payload.get("batch_id"),
        "requested_by_role": "project_manager",
        "to_role": to_role,
        "request_mode": request_mode,
        "request_kind": request_kind,
        "status": "open",
        "packet_id": packet_id,
        "packet_type": packet_type,
        "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
        "packet_body_path": envelope["body_path"],
        "packet_body_hash": envelope["body_hash"],
        "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
        "result_body_path": project_relative(project_root, paths["result_body"]),
        "output_contract_id": envelope.get("output_contract_id") or output_contract_id,
        "process_kind": process_binding["process_kind"],
        "process_contract_binding": process_binding,
        "strict_process_contract_binding": True,
        "required_result_next_recipient": process_binding["required_result_next_recipient"],
        "controller_may_read_packet_body": False,
        "body_source": body_ref,
        "registered_at": utc_now(),
    }
    if isinstance(existing, dict):
        existing.update(record)
    else:
        index.setdefault("requests", []).append(record)
    index["active_request_id"] = request_id
    if not payload.get("batch_id"):
        batch_id = f"pm-role-work-batch-{_safe_packet_id_component(request_id)}"
        record["batch_id"] = batch_id
        _write_parallel_packet_batch(
            project_root,
            run_root,
            run_state,
            batch_id=batch_id,
            batch_kind="pm_role_work",
            phase="pm_role_work_request",
            records=[record],
            node_id=node_id,
            join_policy="all_results_before_pm_absorption",
            review_policy="pm_absorbs_batch_without_reviewer_unless_packet_requires_review",
            pm_absorption_required=True,
        )
        index["active_batch_id"] = batch_id
        index["active_request_ids"] = [request_id]
    _write_pm_role_work_request_index(run_root, index)
    run_state["pm_role_work_requests"] = {
        "index_path": project_relative(project_root, _pm_role_work_request_index_path(run_root)),
        "active_request_id": request_id,
        "active_packet_id": packet_id,
        "active_to_role": to_role,
        "active_request_mode": request_mode,
    }


def _normalize_pm_role_work_result_recipient(
    project_root: Path,
    result_path: Path,
    result: dict[str, Any],
) -> dict[str, Any]:
    if result.get("next_recipient") == "project_manager":
        return result
    original_recipient = result.get("next_recipient")
    result["next_recipient"] = "project_manager"
    result["next_holder"] = "project_manager"
    result["to_role"] = "project_manager"
    result["recipient_normalization"] = {
        "schema_version": "flowpilot.pm_role_work_result_recipient_normalization.v1",
        "from": original_recipient,
        "to": "project_manager",
        "reason": "pm_role_work_result_returns_to_pm",
        "controller_read_result_body": False,
        "normalized_at": utc_now(),
    }
    write_json(result_path, result)
    paths = packet_runtime.packet_paths_from_result_envelope(project_root, result)
    ledger = read_json(paths["packet_ledger"])
    records = ledger.get("packets") if isinstance(ledger.get("packets"), list) else []
    for item in records:
        if isinstance(item, dict) and item.get("packet_id") == result.get("packet_id"):
            item["result_recipient_normalized_to_pm"] = True
            item["result_recipient_normalized_at"] = result["recipient_normalization"]["normalized_at"]
            nested = item.get("result_envelope")
            if isinstance(nested, dict):
                nested["next_recipient"] = "project_manager"
    ledger["updated_at"] = utc_now()
    write_json(paths["packet_ledger"], ledger)
    return result


def _validate_role_work_result_process_binding(
    project_root: Path,
    result_path: Path,
    *,
    record: dict[str, Any],
    packet_envelope: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    metadata = packet_envelope.get("metadata") if isinstance(packet_envelope.get("metadata"), dict) else {}
    binding = metadata.get("process_contract_binding") if isinstance(metadata.get("process_contract_binding"), dict) else {}
    strict_process_contract_binding = bool(
        metadata.get("strict_process_contract_binding")
        or record.get("strict_process_contract_binding")
    )
    expected_next_recipient = str(
        binding.get("required_result_next_recipient")
        or record.get("required_result_next_recipient")
        or "project_manager"
    )
    if result.get("next_recipient") == expected_next_recipient:
        return result
    if strict_process_contract_binding:
        raise RouterError("role-work result next_recipient must match process binding")
    result["legacy_pm_role_work_result_recipient_normalization"] = True
    return _normalize_pm_role_work_result_recipient(project_root, result_path, result)


def _write_role_work_result_returned(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise RouterError("role-work result payload must be an object")
    request_id = str(payload.get("request_id") or "").strip()
    if not request_id:
        raise RouterError("role-work result requires request_id")
    index = _load_pm_role_work_request_index(run_root, run_state)
    record = _pm_role_work_request_record(index, request_id)
    if not isinstance(record, dict):
        raise RouterError(f"role-work result references unknown request_id: {request_id}")
    if record.get("status") != "packet_relayed":
        raise RouterError("role-work result requires request packet made available to worker")
    packet_id = str(payload.get("packet_id") or record.get("packet_id") or "").strip()
    if packet_id != str(record.get("packet_id") or ""):
        raise RouterError("role-work result packet_id must match request packet")
    result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
    raw_result_path = payload.get("result_envelope_path")
    if raw_result_path:
        supplied = resolve_project_path(project_root, str(raw_result_path))
        if supplied.resolve() != result_path.resolve():
            raise RouterError("role-work result_envelope_path must match request record")
    if not result_path.exists():
        raise RouterError(f"role-work result envelope is missing: {result_path}")
    result_hash = payload.get("result_envelope_hash")
    if result_hash and packet_runtime.sha256_file(result_path) != str(result_hash):
        raise RouterError("role-work result envelope hash mismatch")
    result = packet_runtime.load_envelope(project_root, result_path)
    if result.get("packet_id") != packet_id:
        raise RouterError("role-work result envelope packet_id mismatch")
    if result.get("completed_by_role") != record.get("to_role"):
        raise RouterError("role-work result was completed by the wrong role")
    packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
    packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
    result = _validate_role_work_result_process_binding(
        project_root,
        result_path,
        record=record,
        packet_envelope=packet_envelope,
        result=result,
    )
    audit = packet_runtime.validate_result_ready_for_reviewer_relay(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result,
        agent_role_map=_agent_role_map_from_crew_ledger(run_root),
    )
    if not audit.get("passed"):
        raise RouterError(f"role-work result is not ready for PM relay: {audit.get('blockers')}")
    record["status"] = "result_returned"
    record["result_envelope_path"] = project_relative(project_root, result_path)
    record["result_envelope_hash"] = packet_runtime.sha256_file(result_path)
    record["result_body_path"] = result.get("result_body_path")
    record["result_body_hash"] = result.get("result_body_hash")
    record["result_returned_at"] = utc_now()
    index["active_request_id"] = request_id
    _write_pm_role_work_request_index(run_root, index)
    _mark_parallel_batch_results_joined(project_root, run_root, run_state, "pm_role_work")


def _write_pm_role_work_result_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    decision_payload = _load_file_backed_role_payload_if_present(project_root, payload)
    request_id = str(decision_payload.get("request_id") or "").strip()
    batch_id = str(decision_payload.get("batch_id") or "").strip()
    if not request_id and not batch_id:
        raise RouterError("PM role-work result decision requires request_id or batch_id")
    decided_by_role = str(
        decision_payload.get("decided_by_role")
        or decision_payload.get("recorded_by_role")
        or ""
    ).strip()
    if decided_by_role != "project_manager":
        raise RouterError("PM role-work result decision requires decided_by_role=project_manager")
    decision = str(decision_payload.get("decision") or "").strip()
    if decision not in PM_ROLE_WORK_TERMINAL_DECISIONS:
        raise RouterError("PM role-work result decision must be absorbed, canceled, or superseded")
    index = _load_pm_role_work_request_index(run_root, run_state)
    records: list[dict[str, Any]]
    if batch_id:
        records = [
            record
            for record in index.get("requests", [])
            if isinstance(record, dict) and str(record.get("batch_id") or index.get("active_batch_id") or "") == batch_id
        ]
        if not records:
            active_ids = {str(item) for item in index.get("active_request_ids", []) if item}
            records = [
                record
                for record in index.get("requests", [])
                if isinstance(record, dict) and str(record.get("request_id")) in active_ids
            ]
    else:
        record = _pm_role_work_request_record(index, request_id)
        records = [record] if isinstance(record, dict) else []
    if not records:
        raise RouterError("PM role-work result decision references unknown request_id or batch_id")
    if decision == "absorbed" and any(record.get("status") != "result_relayed_to_pm" for record in records):
        raise RouterError("PM may absorb role-work batch only after Controller relays every result to PM")
    if decision in {"canceled", "superseded"} and any(record.get("status") not in PM_ROLE_WORK_OPEN_STATUSES for record in records):
        raise RouterError("PM role-work result decision can cancel or supersede only unresolved requests")
    decision_record = {
        "schema_version": PM_ROLE_WORK_RESULT_DECISION_SCHEMA,
        "request_id": request_id or records[0].get("request_id"),
        "batch_id": batch_id or records[0].get("batch_id"),
        "request_ids": [record.get("request_id") for record in records],
        "decided_by_role": "project_manager",
        "decision": decision,
        "decision_reason": decision_payload.get("decision_reason") or "",
        "recorded_at": utc_now(),
        **_role_output_envelope_record(decision_payload),
    }
    decisions_dir = run_root / "pm_work_requests" / "decisions"
    decision_key = batch_id or request_id
    decision_path = decisions_dir / f"{_safe_packet_id_component(decision_key)}.{decision}.json"
    write_json(decision_path, decision_record)
    for record in records:
        record["status"] = decision
        record["pm_result_decision"] = {
            "decision": decision,
            "decision_path": project_relative(project_root, decision_path),
            "decision_hash": packet_runtime.sha256_file(decision_path),
            "recorded_at": decision_record["recorded_at"],
        }
    if request_id and index.get("active_request_id") == request_id:
        index["active_request_id"] = None
    if batch_id and index.get("active_batch_id") == batch_id:
        index["active_batch_id"] = None
        index["active_request_ids"] = []
    _write_pm_role_work_request_index(run_root, index)
    if batch_id and decision == "absorbed":
        _mark_parallel_batch_reviewed(
            run_root,
            "pm_role_work",
            passed=True,
            reviewed_packet_ids=[str(record.get("packet_id")) for record in records],
        )
    return decision


def _write_worker_research_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not run_state["flags"].get("research_packet_relayed"):
        raise RouterError("research report requires research packet made available to worker")
    research_index = _load_packet_index(_research_packet_index_path(run_root), label="research")
    _validate_packet_bodies_opened_by_targets(project_root, run_state, research_index["packets"])
    _validate_results_exist_for_packets(project_root, run_state, research_index["packets"], next_recipient="human_like_reviewer")
    completed_roles = sorted({str(record.get("to_role")) for record in research_index["packets"] if isinstance(record, dict)})
    if not payload.get("answers_decision_question", True):
        raise RouterError("research batch report must state whether it answers the PM decision question")
    write_json(
        run_root / "research" / "worker_research_report.json",
        {
            "schema_version": "flowpilot.research_worker_report.v1",
            "run_id": run_state["run_id"],
            "batch_id": research_index.get("batch_id"),
            "packet_count": len(research_index["packets"]),
            "completed_by_roles": completed_roles,
            "completed_by_role": payload.get("completed_by_role") or ",".join(completed_roles),
            "packet_ids": [record.get("packet_id") for record in research_index["packets"] if isinstance(record, dict)],
            "raw_evidence_pointers": payload.get("raw_evidence_pointers") or [],
            "negative_findings": payload.get("negative_findings") or [],
            "contradictions": payload.get("contradictions") or [],
            "confidence_boundary": payload.get("confidence_boundary") or "worker report only; reviewer check required",
            "answers_decision_question": bool(payload.get("answers_decision_question", True)),
            "reported_at": utc_now(),
        },
    )


def _write_material_understanding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("material understanding must be PM-owned")
    if run_state["flags"].get("pm_research_requested") and not run_state["flags"].get("research_result_absorbed_by_pm"):
        raise RouterError("PM material understanding requires reviewed research to be absorbed when research was requested")
    payload_snapshot_path = run_root / "material" / "pm_material_understanding_payload.json"
    write_json(
        payload_snapshot_path,
        {
            "schema_version": "flowpilot.pm_material_understanding_payload.v1",
            "run_id": run_state["run_id"],
            "payload_body": _without_role_output_envelope(payload),
            "source_role_output_envelope": _role_output_envelope_record(payload).get("_role_output_envelope"),
            "written_at": utc_now(),
        },
    )
    write_json(
        run_root / "pm_material_understanding.json",
        {
            "schema_version": "flowpilot.pm_material_understanding.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "source_paths": {
                "payload_snapshot": project_relative(project_root, payload_snapshot_path),
            },
            "source_material_review": run_state.get("material_review"),
            "research_absorbed": bool(run_state["flags"].get("research_result_absorbed_by_pm")),
            "material_summary": payload.get("material_summary") or "",
            "contradictions": payload.get("contradictions") or [],
            "deferred_sources": payload.get("deferred_sources") or [],
            "route_consequences": payload.get("route_consequences") or [],
            "written_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_product_function_architecture(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("product-function architecture must be PM-owned")
    material_understanding_path = run_root / "pm_material_understanding.json"
    if not material_understanding_path.exists():
        raise RouterError("product-function architecture requires pm_material_understanding.json")
    required_lists = ("user_task_map", "product_capability_map", "feature_decisions", "functional_acceptance_matrix")
    missing_lists = [name for name in required_lists if not isinstance(payload.get(name), list) or not payload.get(name)]
    if missing_lists:
        raise RouterError(f"product-function architecture requires non-empty lists: {', '.join(missing_lists)}")
    if not isinstance(payload.get("highest_achievable_product_target"), dict) or not payload.get("highest_achievable_product_target"):
        raise RouterError("product-function architecture requires highest_achievable_product_target")
    semantic_policy = payload.get("semantic_fidelity_policy")
    if not isinstance(semantic_policy, dict) or semantic_policy.get("silent_downgrade_forbidden") is not True:
        raise RouterError("product-function architecture requires semantic_fidelity_policy.silent_downgrade_forbidden=true")
    root_requirements = payload.get("functional_acceptance_matrix")
    if not isinstance(root_requirements, list):
        raise RouterError("functional_acceptance_matrix must be a list when provided")
    architecture = {
        "schema_version": "flowpilot.product_function_architecture.v1",
        "run_id": run_state["run_id"],
        "status": str(payload.get("status") or "draft"),
        "pm_owned": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "startup_answers": project_relative(project_root, run_root / "startup_answers.json"),
            "startup_activation": project_relative(project_root, run_root / "startup" / "startup_activation.json"),
            "display_surface": project_relative(project_root, run_root / "display" / "display_surface.json"),
            "pm_material_understanding": project_relative(project_root, material_understanding_path),
        },
        "source_material_review": run_state.get("material_review"),
        "high_standard_posture": payload.get("high_standard_posture") or {"highest_reasonably_achievable_is_floor": True},
        "unacceptable_result_review": payload.get("unacceptable_result_review") or [],
        "user_task_map": payload.get("user_task_map"),
        "product_capability_map": payload.get("product_capability_map"),
        "feature_decisions": payload.get("feature_decisions"),
        "display_rationale": payload.get("display_rationale") or [],
        "missing_feature_review": payload.get("missing_feature_review") or [],
        "negative_scope": payload.get("negative_scope") or [],
        "semantic_fidelity_policy": semantic_policy,
        "highest_achievable_product_target": payload.get("highest_achievable_product_target"),
        "functional_acceptance_matrix": root_requirements,
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "product_function_architecture.json", architecture)


def _write_role_gate_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"gate report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is not True:
        raise RouterError("gate report must explicitly pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"gate report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_role_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"block report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is True:
        raise RouterError("block report cannot pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"block report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": False,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "repair_recommendation": payload.get("repair_recommendation"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _gate_outcome_path_from_token(run_root: Path, token: str) -> Path:
    if token == "__current_route_draft__":
        return _current_route_draft_path(run_root)
    if token == "__parent_backward_targets__":
        frontier = _active_frontier(run_root)
        return run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if token == "__active_node_acceptance_plan__":
        frontier = _active_frontier(run_root)
        return _active_node_acceptance_plan_path(run_root, frontier)
    if token.startswith("__active_node_root__/"):
        frontier = _active_frontier(run_root)
        return _active_node_root(run_root, frontier) / token.removeprefix("__active_node_root__/")
    return run_root / token


def _write_gate_outcome_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    event: str,
) -> None:
    spec = GATE_OUTCOME_BLOCK_EVENT_SPECS[event]
    checked_paths = [
        _gate_outcome_path_from_token(run_root, str(token))
        for token in spec.get("checked_paths", ())
    ]
    report_path = _gate_outcome_path_from_token(run_root, str(spec["path"]))
    _write_role_block_report(
        project_root,
        run_root,
        run_state,
        payload,
        expected_role=str(spec["expected_role"]),
        path=report_path,
        schema_version=str(spec["schema_version"]),
        checked_paths=checked_paths,
    )
    flags = run_state.setdefault("flags", {})
    for reset_flag in spec.get("reset_flags", ()):
        flags[str(reset_flag)] = False
    gate_blocks = run_state.setdefault("gate_outcome_blocks", [])
    if not isinstance(gate_blocks, list):
        gate_blocks = []
    record = {
        "event": event,
        "report_path": project_relative(project_root, report_path),
        "repair_resets": [str(flag) for flag in spec.get("reset_flags", ())],
        "recorded_at": utc_now(),
    }
    gate_blocks.append(record)
    run_state["gate_outcome_blocks"] = gate_blocks[-20:]
    run_state["active_gate_outcome_block"] = record


def _clear_active_gate_outcome_block_for_pass(run_state: dict[str, Any], *, event: str) -> None:
    cleared_events = set(GATE_OUTCOME_PASS_CLEARS_EVENTS.get(event, ()))
    if not cleared_events:
        return
    active = run_state.get("active_gate_outcome_block")
    if not isinstance(active, dict) or active.get("event") not in cleared_events:
        return
    cleared_at = utc_now()
    active["status"] = "cleared_by_pass"
    active["cleared_by_event"] = event
    active["cleared_at"] = cleared_at
    blocks = run_state.get("gate_outcome_blocks")
    if isinstance(blocks, list):
        for record in reversed(blocks):
            if not isinstance(record, dict):
                continue
            if record.get("event") == active.get("event") and record.get("report_path") == active.get("report_path"):
                record["status"] = "cleared_by_pass"
                record["cleared_by_event"] = event
                record["cleared_at"] = cleared_at
                break
    run_state["active_gate_outcome_block"] = None


def _write_route_process_pass_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "process_flowguard_officer":
        raise RouterError("route process check must be reviewed_by_role=process_flowguard_officer")
    if payload.get("passed") is not True or payload.get("process_viability_verdict") != "pass":
        raise RouterError("route process check requires process_viability_verdict=pass")
    required_true = (
        "product_behavior_model_checked",
        "route_can_reach_product_model",
        "repair_return_policy_checked",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("route process check requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _current_route_draft_path(run_root),
        _product_behavior_model_report_path(run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process check is missing source paths: {', '.join(missing_paths)}")
    write_json(
        _route_process_check_path(run_root),
        {
            "schema_version": "flowpilot.route_process_check.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "process_flowguard_officer",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_can_reach_product_model": True,
            "repair_return_policy_checked": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_route_process_issue_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_verdict: str,
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "process_flowguard_officer":
        raise RouterError("route process issue report must be reviewed_by_role=process_flowguard_officer")
    if payload.get("passed") is True:
        raise RouterError("route process issue report cannot pass")
    if payload.get("process_viability_verdict") != expected_verdict:
        raise RouterError(f"route process issue report requires process_viability_verdict={expected_verdict}")
    checked_paths = [
        _current_route_draft_path(run_root),
        _product_behavior_model_report_path(run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process issue report is missing source paths: {', '.join(missing_paths)}")
    write_json(
        _route_process_check_path(run_root),
        {
            "schema_version": "flowpilot.route_process_check.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "process_flowguard_officer",
            "passed": False,
            "process_viability_verdict": expected_verdict,
            "product_behavior_model_checked": bool(payload.get("product_behavior_model_checked")),
            "route_can_reach_product_model": bool(payload.get("route_can_reach_product_model")),
            "repair_return_policy_checked": bool(payload.get("repair_return_policy_checked")),
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "recommended_resolution": payload.get("recommended_resolution"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    for flag in (
        "route_draft_written_by_pm",
        "process_officer_route_check_card_delivered",
        "process_officer_route_check_passed",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False
    run_state["route_process_viability"] = {
        "verdict": expected_verdict,
        "report_path": project_relative(project_root, _route_process_check_path(run_root)),
        "reported_at": utc_now(),
    }


def _write_route_product_pass_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "product_flowguard_officer":
        raise RouterError("route product check must be reviewed_by_role=product_flowguard_officer")
    if payload.get("passed") is not True or payload.get("route_model_review_verdict") != "pass":
        raise RouterError("route product check requires route_model_review_verdict=pass")
    required_true = (
        "product_behavior_model_checked",
        "route_maps_to_product_behavior_model",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("route product check requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _current_route_draft_path(run_root),
        _product_behavior_model_report_path(run_root),
        run_root / "root_acceptance_contract.json",
        _route_process_check_path(run_root),
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route product check is missing source paths: {', '.join(missing_paths)}")
    write_json(
        _route_product_check_path(run_root),
        {
            "schema_version": "flowpilot.route_product_check.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "product_flowguard_officer",
            "passed": True,
            "route_model_review_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_maps_to_product_behavior_model": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("root acceptance contract must be PM-owned")
    architecture_path = run_root / "product_function_architecture.json"
    if not architecture_path.exists():
        raise RouterError("root contract requires product-function architecture")
    root_requirements = payload.get("root_requirements")
    if not isinstance(root_requirements, list) or not root_requirements:
        raise RouterError("root contract requires a non-empty root_requirements list")
    proof_matrix = payload.get("proof_matrix")
    if not isinstance(proof_matrix, list) or not proof_matrix:
        raise RouterError("root contract requires a non-empty proof_matrix list")
    scenario_ids = payload.get("selected_scenario_ids")
    if not isinstance(scenario_ids, list) or not scenario_ids:
        raise RouterError("root contract requires a non-empty selected_scenario_ids list")
    contract = {
        "schema_version": "flowpilot.root_acceptance_contract.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "product_function_architecture": project_relative(project_root, architecture_path),
        },
        "root_requirements": root_requirements,
        "proof_matrix": proof_matrix,
        "standard_scenario_pack": {
            "required": True,
            "path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "selected_scenario_ids": scenario_ids,
        },
        "completion_policy": {
            "unresolved_residual_risks_allowed": False,
            "risk_triage_required_before_completion": True,
        },
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    scenario_pack = {
        "schema_version": "flowpilot.standard_scenario_pack.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "selected_scenario_ids": scenario_ids,
        "selection_reason": payload.get("scenario_selection_reason") or "Selected from root acceptance contract risk coverage.",
    }
    write_json(run_root / "root_acceptance_contract.json", contract)
    write_json(run_root / "standard_scenario_pack.json", scenario_pack)
    (run_root / "contract.md").write_text(
        "\n".join(
            [
                "# FlowPilot Root Acceptance Contract",
                "",
                f"Run: {run_state['run_id']}",
                "",
                "The PM has frozen the root acceptance contract. See:",
                "",
                "- `root_acceptance_contract.json`",
                "- `standard_scenario_pack.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _freeze_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    required_paths = [
        run_root / "root_acceptance_contract.json",
        run_root / "standard_scenario_pack.json",
        run_root / "contract.md",
        run_root / "reviews" / "root_contract_challenge.json",
        run_root / "flowguard" / "root_contract_modelability.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"cannot freeze root contract; missing paths: {', '.join(missing)}")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("completion_policy", {}).get("unresolved_residual_risks_allowed") is not False:
        raise RouterError("root contract cannot allow unresolved residual risks")
    contract["status"] = "frozen"
    contract["frozen_by_role"] = "project_manager"
    contract["frozen_at"] = utc_now()
    write_json(run_root / "root_acceptance_contract.json", contract)


def _write_dependency_policy(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    contract_path = run_root / "root_acceptance_contract.json"
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("dependency policy requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("dependency policy must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot be authority for dependency policy")
    if payload.get("controller_self_install_allowed") is True:
        raise RouterError("Controller cannot self-approve host-level installs")
    host_install_requested = bool(payload.get("host_level_install_requested"))
    user_approval_recorded = bool(payload.get("explicit_user_approval_recorded"))
    if host_install_requested and not user_approval_recorded:
        raise RouterError("host-level installs require explicit recorded user approval")
    policy = {
        "schema_version": "flowpilot.dependency_policy.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, contract_path),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "host_level_install_requested": host_install_requested,
        "explicit_user_approval_recorded": user_approval_recorded,
        "controller_self_install_allowed": False,
        "allowed_dependency_actions": payload.get("allowed_dependency_actions") or [],
        "blocked_dependency_actions": payload.get("blocked_dependency_actions") or ["host_install_without_user_approval"],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "dependency_policy.json", policy)


def _write_capabilities_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    dependency_path = run_root / "dependency_policy.json"
    architecture_path = run_root / "product_function_architecture.json"
    contract_path = run_root / "root_acceptance_contract.json"
    if not dependency_path.exists():
        raise RouterError("capabilities manifest requires dependency_policy.json")
    if not architecture_path.exists():
        raise RouterError("capabilities manifest requires product_function_architecture.json")
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("capabilities manifest requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("capabilities manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot authorize capabilities")
    architecture = read_json(architecture_path)
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        capabilities = architecture.get("product_capability_map") or []
    if not isinstance(capabilities, list) or not capabilities:
        raise RouterError("capabilities manifest requires a non-empty capabilities list or product_capability_map")
    manifest = {
        "schema_version": "flowpilot.capabilities_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "dependency_policy": project_relative(project_root, dependency_path),
            "product_function_architecture": project_relative(project_root, architecture_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "capabilities": capabilities,
        "capability_to_skill_needs": payload.get("capability_to_skill_needs") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "capabilities.json", manifest)


def _validate_selected_child_skills(selected_skills: Any) -> list[dict[str, Any]]:
    if not isinstance(selected_skills, list):
        raise RouterError("selected child skills must be a list")
    allowed_approvers = {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
    }
    for skill in selected_skills:
        if not isinstance(skill, dict):
            raise RouterError("each selected child skill entry must be an object")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                raise RouterError("each child-skill gate must be an object")
            approver = gate.get("required_approver")
            if approver == "controller" or gate.get("controller_can_approve") is True:
                raise RouterError("Controller cannot approve child-skill gates")
            if approver and approver not in allowed_approvers:
                raise RouterError(f"unsupported child-skill gate approver: {approver}")
    return selected_skills


def _write_child_skill_selection(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    capabilities_path = run_root / "capabilities.json"
    if not capabilities_path.exists():
        raise RouterError("child-skill selection requires capabilities.json")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill selection must be PM-owned")
    if payload.get("raw_inventory_used_as_authority") is True or payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw local skill inventory cannot authorize child-skill selection")
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = payload.get("skill_decisions") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    selection = {
        "schema_version": "flowpilot.pm_child_skill_selection.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "dependency_policy": project_relative(project_root, run_root / "dependency_policy.json"),
        },
        "raw_inventory_used_as_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "selected_from_product_needs": True,
        "selected_skills": selected_skills,
        "deferred_skills": payload.get("deferred_skills") or [],
        "rejected_skills": payload.get("rejected_skills") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "pm_child_skill_selection.json", selection)


def _write_child_skill_gate_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    selection_path = run_root / "pm_child_skill_selection.json"
    capabilities_path = run_root / "capabilities.json"
    contract_path = run_root / "root_acceptance_contract.json"
    for required_path, label in (
        (selection_path, "pm_child_skill_selection.json"),
        (capabilities_path, "capabilities.json"),
        (contract_path, "root_acceptance_contract.json"),
    ):
        if not required_path.exists():
            raise RouterError(f"child-skill gate manifest requires {label}")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill gate manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw inventory cannot be authority for child-skill gate manifest")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill gate manifest cannot allow Controller self-approval")
    selection = read_json(selection_path)
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = selection.get("selected_skills") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    manifest_path = run_root / "child_skill_gate_manifest.json"
    manifest = {
        "schema_version": "flowpilot.child_skill_gate_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "draft"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "pm_child_skill_selection": project_relative(project_root, selection_path),
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "controller_self_approval_allowed": False,
        "selected_skills": selected_skills,
        "approval": {
            "reviewer_passed": False,
            "process_officer_passed": False,
            "product_officer_passed": False,
            "pm_approved_for_route": False,
        },
        **_role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            payload,
            reason="child_skill_gate_manifest_can_be_updated_by_review_gates",
        ),
    }
    write_json(manifest_path, manifest)


def _sync_child_skill_manifest_review_approval(project_root: Path, run_root: Path) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    review_path = run_root / "reviews" / "child_skill_gate_manifest_review.json"
    if not manifest_path.exists() or not review_path.exists():
        return
    review = read_json(review_path)
    if review.get("passed") is not True:
        return
    manifest = read_json(manifest_path)
    manifest.update(
        _role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            manifest,
            reason="child_skill_gate_manifest_review_approval_sync",
        )
    )
    approval = manifest.setdefault("approval", {})
    if approval.get("reviewer_passed") is True:
        return
    approval["reviewer_passed"] = True
    approval["reviewed_at"] = review.get("reported_at") or utc_now()
    manifest["updated_at"] = utc_now()
    write_json(manifest_path, manifest)


def _approve_child_skill_manifest_for_route(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    required_paths = [
        manifest_path,
        run_root / "reviews" / "child_skill_gate_manifest_review.json",
        run_root / "flowguard" / "child_skill_conformance_model.json",
        run_root / "flowguard" / "child_skill_product_fit.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"PM child-skill approval is missing required reports: {', '.join(missing)}")
    if payload.get("approved_by_role", "project_manager") != "project_manager":
        raise RouterError("child-skill manifest route approval must be by project_manager")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill manifest PM approval cannot allow Controller self-approval")
    manifest = read_json(manifest_path)
    manifest["status"] = "approved"
    manifest["updated_at"] = utc_now()
    manifest.setdefault("approval", {})
    manifest["approval"].update(
        {
            "reviewer_passed": True,
            "process_officer_passed": True,
            "product_officer_passed": True,
            "pm_approved_for_route": True,
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
        }
    )
    write_json(manifest_path, manifest)
    write_json(
        run_root / "child_skill_manifest_pm_approval.json",
        {
            "schema_version": "flowpilot.child_skill_manifest_pm_approval.v1",
            "run_id": run_state["run_id"],
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
            "source_paths": [project_relative(project_root, path) for path in required_paths],
        },
    )


def _sync_capability_evidence(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    capabilities_path = run_root / "capabilities.json"
    approval_path = run_root / "child_skill_manifest_pm_approval.json"
    required_paths = [manifest_path, capabilities_path, approval_path]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"capability evidence sync is missing paths: {', '.join(missing)}")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "approved" or manifest.get("approval", {}).get("pm_approved_for_route") is not True:
        raise RouterError("capability evidence sync requires PM-approved child-skill manifest")
    write_json(
        run_root / "capabilities" / "capability_sync.json",
        {
            "schema_version": "flowpilot.capability_evidence_sync.v1",
            "run_id": run_state["run_id"],
            "synced_by": str(payload.get("synced_by") or "controller"),
            "pm_approved_manifest": True,
            "source_paths": [project_relative(project_root, path) for path in required_paths],
            "synced_at": utc_now(),
        },
    )


def _reset_flags(run_state: dict[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        run_state["flags"][name] = False


def _node_identifier(node: dict[str, Any]) -> str:
    return str(node.get("node_id") or node.get("id") or "")


def _raw_route_nodes(route: dict[str, Any]) -> list[Any]:
    nodes = route.get("nodes")
    if isinstance(nodes, dict):
        return list(nodes.values())
    if isinstance(nodes, list):
        return list(nodes)
    return []


def _inline_child_nodes(node: dict[str, Any]) -> list[Any]:
    children: list[Any] = []
    for key in ("children", "child_nodes"):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            children.extend(raw_children)
    return children


def _flatten_route_nodes(raw_nodes: list[Any], *, parent_node_id: str | None = None, depth: int = 1) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node = dict(raw_node)
        node_id = _node_identifier(node)
        if not node_id:
            continue
        node.setdefault("node_id", node_id)
        if parent_node_id and not node.get("parent_node_id"):
            node["parent_node_id"] = parent_node_id
        if not node.get("depth"):
            node["_computed_depth"] = depth
        flattened.append(node)
        flattened.extend(_flatten_route_nodes(_inline_child_nodes(node), parent_node_id=node_id, depth=depth + 1))
    return flattened


def _route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return _flatten_route_nodes(_raw_route_nodes(route))


def _route_node_depth(node: dict[str, Any]) -> int:
    raw_depth = node.get("depth", node.get("_computed_depth", 1))
    try:
        return max(1, int(raw_depth))
    except (TypeError, ValueError):
        return 1


def _route_display_depth(route: dict[str, Any]) -> int:
    display = route.get("display") if isinstance(route.get("display"), dict) else {}
    raw_depth = display.get("display_depth") or route.get("display_depth") or 2
    try:
        return max(1, int(raw_depth))
    except (TypeError, ValueError):
        return 2


def _display_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    display_depth = _route_display_depth(route)
    nodes = _route_nodes(route)
    visible = [
        node
        for node in nodes
        if node.get("user_visible") is True or _route_node_depth(node) <= display_depth
    ]
    return visible or nodes


def _route_active_path(route: dict[str, Any], active_node_id: str | None) -> list[dict[str, str]]:
    if not active_node_id:
        return []
    nodes = _route_nodes(route)
    by_id = {_node_identifier(node): node for node in nodes if _node_identifier(node)}
    if str(active_node_id) not in by_id:
        return []
    path: list[dict[str, str]] = []
    seen: set[str] = set()
    cursor: str | None = str(active_node_id)
    while cursor and cursor in by_id and cursor not in seen:
        seen.add(cursor)
        node = by_id[cursor]
        path.append(
            {
                "id": cursor,
                "label": str(node.get("title") or node.get("label") or cursor),
                "node_kind": _node_kind(node),
            }
        )
        parent_id = node.get("parent_node_id")
        cursor = str(parent_id) if parent_id else None
    return list(reversed(path))


def _route_hidden_leaf_progress(route: dict[str, Any]) -> dict[str, int]:
    display_depth = _route_display_depth(route)
    hidden_leaf_nodes = [
        node
        for node in _route_nodes(route)
        if _route_node_depth(node) > display_depth and _node_kind(node) == "leaf"
    ]
    completed = [
        node
        for node in hidden_leaf_nodes
        if str(node.get("status") or "").lower() in {"complete", "completed", "done", "passed"}
    ]
    return {"completed": len(completed), "total": len(hidden_leaf_nodes)}


def _is_leaf_readiness_passed(node: dict[str, Any], plan: dict[str, Any] | None = None) -> bool:
    candidates = []
    if isinstance(node.get("leaf_readiness_gate"), dict):
        candidates.append(node["leaf_readiness_gate"])
    if plan and isinstance(plan.get("leaf_readiness_gate"), dict):
        candidates.append(plan["leaf_readiness_gate"])
    if not candidates:
        return False
    return any(str(gate.get("status") or "").lower() in {"pass", "passed", "approved"} for gate in candidates)


def _node_kind(node: dict[str, Any]) -> str:
    raw_kind = str(node.get("node_kind") or node.get("kind") or "").lower()
    if raw_kind in {"parent", "module", "leaf", "repair"}:
        return raw_kind
    if _node_child_ids(node):
        return "parent"
    return "leaf"


def _effective_route_nodes(route: dict[str, Any], mutations: dict[str, Any]) -> list[dict[str, Any]]:
    superseded = {
        str(node_id)
        for item in mutations.get("items", [])
        if isinstance(item, dict)
        for node_id in (item.get("superseded_nodes") or [])
    }
    effective = []
    for node in _route_nodes(route):
        node_id = str(node.get("node_id") or node.get("id"))
        if node_id in superseded or node.get("status") in {"superseded", "stale", "failed"}:
            continue
        effective.append(node)
    return effective


def _next_effective_node_id(route: dict[str, Any], mutations: dict[str, Any], completed_nodes: list[str], current_node_id: str) -> str | None:
    effective_nodes = _effective_route_nodes(route, mutations)
    effective_ids = [str(node.get("node_id") or node.get("id")) for node in effective_nodes]
    if not effective_ids:
        return None
    try:
        start = effective_ids.index(current_node_id) + 1
    except ValueError:
        start = 0
    completed = set(completed_nodes)
    nodes_by_id = {str(node.get("node_id") or node.get("id")): node for node in effective_nodes}
    for node_id in effective_ids[start:] + effective_ids[:start]:
        if node_id not in completed:
            node = nodes_by_id.get(node_id) or {}
            if _node_kind(node) != "leaf":
                child_ids = set(_node_child_ids(node))
                if child_ids and child_ids.issubset(completed):
                    return node_id
                continue
            return node_id
    return None


def _route_memory_root(run_root: Path) -> Path:
    return run_root / "route_memory"


def _route_history_index_path(run_root: Path) -> Path:
    return _route_memory_root(run_root) / "route_history_index.json"


def _pm_prior_path_context_path(run_root: Path) -> Path:
    return _route_memory_root(run_root) / "pm_prior_path_context.json"


def _route_memory_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return (
        bool(flags.get("route_history_index_refreshed"))
        and bool(flags.get("pm_prior_path_context_refreshed"))
        and _route_history_index_path(run_root).exists()
        and _pm_prior_path_context_path(run_root).exists()
    )


def _display_plan_path(run_root: Path) -> Path:
    return run_root / "display_plan.json"


def _route_state_snapshot_path(run_root: Path) -> Path:
    return run_root / "route_state_snapshot.json"


def _optional_source_path(project_root: Path, path: Path) -> str | None:
    return project_relative(project_root, path) if path.exists() else None


def _plan_item_status(raw_status: Any, *, active: bool = False) -> str:
    status = str(raw_status or "").lower()
    if active:
        return "in_progress"
    if status in {"complete", "completed", "done", "passed"}:
        return "completed"
    if status in {"active", "running", "current", "in_progress"}:
        return "in_progress"
    return "pending"


def _frontier_completed_node_ids(run_root: Path) -> set[str]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    completed = frontier.get("completed_nodes") if isinstance(frontier, dict) else []
    return {str(node_id) for node_id in completed or []}


def _route_item_status(
    run_root: Path,
    node_id: str,
    *,
    active_node_id: str | None,
    raw_status: Any = None,
) -> str:
    if node_id in _frontier_completed_node_ids(run_root):
        return "completed"
    if active_node_id and node_id == active_node_id:
        return "in_progress"
    status = str(raw_status or "").lower()
    if status in {"complete", "completed", "done", "passed"}:
        return "completed"
    return "pending"


def _display_plan_projection(plan: dict[str, Any]) -> dict[str, Any]:
    current_node_id = plan.get("current_node_id")

    def _projected_status(item: dict[str, Any]) -> str:
        item_id = str(item.get("id") or item.get("node_id") or "")
        status = str(item.get("status") or "").lower()
        if status in {"complete", "completed", "done", "passed"}:
            return "completed"
        if item_id == str(current_node_id or ""):
            return "in_progress"
        return "pending"

    return {
        "title": str(plan.get("title") or "FlowPilot"),
        "items": [
            {
                "id": str(item.get("id") or item.get("node_id") or f"item-{index:03d}"),
                "label": str(item.get("label") or item.get("title") or item.get("id") or f"Item {index}"),
                "status": _projected_status(item),
            }
            for index, item in enumerate(plan.get("items") or [], start=1)
            if isinstance(item, dict)
        ],
        "current_node_id": current_node_id,
        "current_node": plan.get("current_node") if isinstance(plan.get("current_node"), dict) else None,
        "active_path": plan.get("active_path") if isinstance(plan.get("active_path"), list) else [],
        "hidden_leaf_progress": plan.get("hidden_leaf_progress") if isinstance(plan.get("hidden_leaf_progress"), dict) else None,
    }


def _waiting_for_pm_display_plan(run_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "controller",
        "scope": "startup_waiting_for_pm",
        "title": "FlowPilot",
        "items": [
            {
                "id": "await_pm_route",
                "label": "Waiting for PM route",
                "status": "in_progress",
            }
        ],
        "current_node_id": None,
        "route_authority": "none_until_pm_display_plan",
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }


def _current_display_plan(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    del project_root
    path = _display_plan_path(run_root)
    if path.exists():
        return read_json(path)
    return _waiting_for_pm_display_plan(run_state)


def _display_plan_sync_payload(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    plan = _current_display_plan(project_root, run_root, run_state)
    projection = _display_plan_projection(plan)
    digest = hashlib.sha256(json.dumps(projection, sort_keys=True).encode("utf-8")).hexdigest()
    snapshot_path = _route_state_snapshot_path(run_root)
    snapshot_digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest() if snapshot_path.exists() else None
    status_summary_path = _current_status_summary_path(run_root)
    status_summary_digest = hashlib.sha256(status_summary_path.read_bytes()).hexdigest() if status_summary_path.exists() else None
    route_sign = _route_map_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    route_sign_available = _route_sign_has_canonical_route(route_sign)
    dialog_fields = (
        _display_route_sign_user_dialog_fields(route_sign)
        if route_sign_available
        else _display_plan_user_dialog_fields(projection)
    )
    display_degraded_reason = None
    if not route_sign_available:
        display_degraded_reason = (
            "startup_waiting_for_pm_route"
            if _display_plan_display_kind(projection) == "startup_waiting_state"
            else "canonical_route_source_unavailable"
        )
    return {
        "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
        "display_plan_exists": _display_plan_path(run_root).exists(),
        "route_state_snapshot_path": project_relative(project_root, snapshot_path),
        "route_state_snapshot_exists": snapshot_path.exists(),
        "route_state_snapshot_hash": snapshot_digest,
        "current_status_summary_path": project_relative(project_root, status_summary_path),
        "current_status_summary_exists": status_summary_path.exists(),
        "current_status_summary_hash": status_summary_digest,
        "projection_hash": digest,
        "native_plan_projection": projection,
        "host_action": "replace_visible_plan",
        "controller_may_invent_route_items": False,
        "route_sign_display_required": route_sign_available,
        "route_sign_display_degraded_reason": display_degraded_reason,
        "route_sign_markdown_path": route_sign.get("markdown_preview_path"),
        "route_sign_mermaid_path": route_sign.get("mermaid_path"),
        "route_sign_display_packet_path": route_sign.get("display_packet_path"),
        "route_sign_mermaid_sha256": route_sign.get("mermaid_sha256"),
        "route_sign_source_kind": route_sign.get("route_source_kind"),
        "route_sign_node_count": route_sign.get("route_node_count"),
        "route_sign_checklist_item_count": route_sign.get("route_checklist_item_count"),
        "route_sign_layout": route_sign.get("route_sign_layout"),
        "route_sign_source_route_path": route_sign.get("source_route_path"),
        "route_sign_source_frontier_path": route_sign.get("source_frontier_path"),
        **dialog_fields,
    }


def _active_ui_task_catalog(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json") or {}
    run_id = str(run_state.get("run_id") or "")
    run_root_rel = project_relative(project_root, run_root)
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    current_run_root = str(current.get("current_run_root") or current.get("active_run_root") or "")
    run_status = str(run_state.get("status") or "")
    current_status = str(current.get("status") or "")
    hidden_statuses = {
        "completed",
        "closed",
        "stopped",
        "stopped_by_user",
        "cancelled_by_user",
        "protocol_dead_end",
        "abandoned",
        "discarded",
        "stale",
    }
    effective_status = run_status if run_status in hidden_statuses else current_status or run_status
    current_pointer_matches = current_run_id == run_id and current_run_root == run_root_rel
    active_tasks: list[dict[str, Any]] = []
    if current_pointer_matches and effective_status not in hidden_statuses:
        active_tasks.append(
            {
                "run_id": run_id,
                "run_root": run_root_rel,
                "status": effective_status or "running",
                "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
                "route_state_snapshot_path": project_relative(project_root, _route_state_snapshot_path(run_root)),
                "close_tab_behavior": "return_to_dialog_route_display",
            }
        )
    hidden_running = [
        {
            "run_id": str(item.get("run_id") or ""),
            "run_root": str(item.get("run_root") or ""),
            "status": str(item.get("status") or ""),
            "hidden_reason": "not_current_pointer",
        }
        for item in index.get("runs", [])
        if isinstance(item, dict)
        and item.get("status") == "running"
        and str(item.get("run_id") or "") != current_run_id
    ]
    return {
        "schema_version": "flowpilot.active_ui_task_catalog.v1",
        "authority": "current_json_only",
        "current_pointer_matches_run": current_pointer_matches,
        "active_tasks": active_tasks,
        "hidden_non_current_running_index_entries": hidden_running,
        "completed_abandoned_stale_history_default_visible": False,
    }


def _route_node_checklist(node: dict[str, Any], *, node_complete: bool = False) -> list[dict[str, Any]]:
    raw_items = node.get("checklist")
    if not isinstance(raw_items, list):
        raw_items = node.get("required_gates")
    if not isinstance(raw_items, list):
        raw_items = node.get("acceptance_checklist")
    if not isinstance(raw_items, list):
        raw_items = []
    checklist: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items, start=1):
        if isinstance(raw, dict):
            item_id = str(raw.get("id") or raw.get("gate_id") or raw.get("label") or f"check-{index:03d}")
            label = str(raw.get("label") or raw.get("title") or raw.get("gate") or item_id)
            status = "completed" if node_complete else _plan_item_status(raw.get("status"), active=False)
        else:
            item_id = str(raw)
            label = item_id.replace("_", " ")
            status = "completed" if node_complete else "pending"
        checklist.append({"id": item_id, "label": label, "status": status})
    return checklist


def _active_route_payload(run_root: Path, route_id: str | None = None) -> dict[str, Any] | None:
    route_root = run_root / "routes"
    candidates: list[Path] = []
    if route_id:
        candidates.append(route_root / route_id / "flow.json")
    if route_root.exists():
        candidates.extend(sorted(route_root.glob("*/flow.json")))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            return read_json(path)
    return None


def _current_status_summary_path(run_root: Path) -> Path:
    return run_root / "display" / "current_status_summary.json"


def _route_node_label(route: dict[str, Any], node_id: str) -> str:
    for node in _iter_route_nodes(route):
        candidate = str(node.get("node_id") or node.get("id") or "")
        if candidate == node_id:
            return str(node.get("title") or node.get("label") or node_id)
    return node_id


def _status_summary_waiting_for(pending_action: dict[str, Any]) -> str | None:
    for key in ("to_role", "waiting_for_role", "target_role", "actor"):
        value = str(pending_action.get(key) or "").strip()
        if value and value != "controller":
            return value
    allowed = pending_action.get("allowed_external_events")
    if isinstance(allowed, list) and allowed:
        return "external_event"
    return None


def _build_current_status_summary(
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or {}
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json") or {}
    active_route_id = str(frontier.get("active_route_id") or run_state.get("active_route_id") or "")
    route = route_payload or _active_route_payload(run_root, active_route_id) or {}
    active_node_id = str(frontier.get("active_node_id") or route.get("active_node_id") or "")
    node_label = _route_node_label(route, active_node_id) if active_node_id else None
    pending_action = run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else {}
    active_blocker = run_state.get("active_control_blocker") if isinstance(run_state.get("active_control_blocker"), dict) else None
    run_status = str(run_state.get("status") or "running")
    frontier_status = str(frontier.get("status") or "")
    terminal = run_status in RUN_TERMINAL_STATUSES or frontier_status in RUN_TERMINAL_STATUSES or frontier.get("terminal") is True
    waiting_for = _status_summary_waiting_for(pending_action)
    if terminal:
        state_kind = "terminal"
    elif active_blocker:
        state_kind = "blocked"
    elif pending_action.get("action_type") == "await_role_decision":
        state_kind = "waiting_for_role"
    elif pending_action:
        state_kind = "controller_action_ready"
    else:
        state_kind = "running"

    labels = {
        "terminal": {
            "en": "Run is terminal.",
            "zh": "这轮任务已经进入终止状态。",
        },
        "blocked": {
            "en": "Run is waiting for a control-plane repair.",
            "zh": "当前卡在控制流程修复上。",
        },
        "waiting_for_role": {
            "en": f"Waiting for {waiting_for or 'a role'} to return a decision.",
            "zh": f"正在等 {waiting_for or '某个角色'} 返回决定。",
        },
        "controller_action_ready": {
            "en": "Controller has the next safe action ready.",
            "zh": "控制器已经拿到下一步安全动作。",
        },
        "running": {
            "en": "FlowPilot is running.",
            "zh": "FlowPilot 正在运行。",
        },
    }
    current_work = node_label or active_node_id or frontier_status or run_status
    return {
        "schema_version": CURRENT_STATUS_SUMMARY_SCHEMA,
        "run_id": run_state.get("run_id"),
        "updated_at": utc_now(),
        "state_kind": state_kind,
        "headline": labels[state_kind],
        "current_work": current_work,
        "route": {
            "route_id": active_route_id or route.get("route_id"),
            "route_version": frontier.get("route_version") or route.get("route_version"),
            "active_node_id": active_node_id or None,
            "active_node_label": node_label,
            "completed_node_count": len(frontier.get("completed_nodes") or []),
        },
        "packet": {
            "active_packet_id": packet_ledger.get("active_packet_id"),
            "status": packet_ledger.get("active_packet_status"),
            "holder": packet_ledger.get("active_packet_holder"),
        },
        "next_step": {
            "action_type": pending_action.get("action_type"),
            "label": pending_action.get("label"),
            "waiting_for": waiting_for,
        },
        "blocker": {
            "active": bool(active_blocker),
            "blocker_id": active_blocker.get("blocker_id") if active_blocker else None,
            "lane": active_blocker.get("handling_lane") if active_blocker else None,
        },
        "ui_contract": {
            "metadata_only": True,
            "sealed_body_fields_excluded": True,
            "evidence_table_excluded": True,
            "source_fields_excluded": True,
            "hash_fields_excluded": True,
        },
    }


def _write_current_status_summary(
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
) -> None:
    write_json(
        _current_status_summary_path(run_root),
        _build_current_status_summary(run_root, run_state, route_payload=route_payload),
    )


def _build_route_state_snapshot(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
    source_event: str | None = None,
) -> dict[str, Any]:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index = read_json_if_exists(project_root / ".flowpilot" / "index.json") or {}
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or {}
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json") or {}
    active_route_id = str(frontier.get("active_route_id") or run_state.get("active_route_id") or "")
    route = route_payload or _active_route_payload(run_root, active_route_id) or {}
    if not active_route_id:
        active_route_id = str(route.get("route_id") or "")
    active_node_id = str(frontier.get("active_node_id") or route.get("active_node_id") or "")
    completed_nodes = {str(item) for item in (frontier.get("completed_nodes") or [])}
    frontier_status = str(frontier.get("status") or "")
    frontier_terminal = bool(frontier.get("terminal")) or frontier_status in RUN_TERMINAL_STATUSES
    run_id = str(run_state.get("run_id") or "")
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    current_run_root = str(current.get("current_run_root") or current.get("active_run_root") or "")
    run_root_rel = project_relative(project_root, run_root)
    stale_running = [
        {
            "run_id": str(item.get("run_id") or ""),
            "status": str(item.get("status") or ""),
            "run_root": str(item.get("run_root") or ""),
        }
        for item in index.get("runs", [])
        if isinstance(item, dict)
        and item.get("status") == "running"
        and str(item.get("run_id") or "") != current_run_id
    ]
    nodes: list[dict[str, Any]] = []
    for position, node in enumerate(_iter_route_nodes(route), start=1):
        node_id = str(node.get("node_id") or node.get("id") or f"node-{position:03d}")
        is_frontier_current = node_id == active_node_id
        node_complete = node_id in completed_nodes
        status = "completed" if node_complete else _plan_item_status(
            node.get("status"),
            active=is_frontier_current and not frontier_terminal,
        )
        node_complete = status == "completed"
        nodes.append(
            {
                "id": node_id,
                "label": str(node.get("title") or node.get("label") or node_id),
                "status": status,
                "is_active": is_frontier_current and not node_complete and not frontier_terminal,
                "is_frontier_current": is_frontier_current,
                "is_selected": False,
                "is_complete": node_complete,
                "completion_source": "execution_frontier.completed_nodes" if node_id in completed_nodes else "route_status",
                "selection_source": "ui_overlay_only",
                "checklist": _route_node_checklist(node, node_complete=node_complete),
                "children": node.get("children") if isinstance(node.get("children"), list) else [],
            }
        )
    pending_action = run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else {}
    return {
        "schema_version": ROUTE_STATE_SNAPSHOT_SCHEMA,
        "run_id": run_id,
        "run_root": run_root_rel,
        "created_at": utc_now(),
        "source_event": source_event,
        "active_ui_task_catalog": _active_ui_task_catalog(project_root, run_root, run_state),
        "authority": {
            "active_source": "current_json_only",
            "current_pointer_path": ".flowpilot/current.json",
            "current_pointer_matches_run": current_run_id == run_id and current_run_root == run_root_rel,
            "index_running_entries_are_not_active_authority": True,
            "stale_running_index_entries": stale_running,
        },
        "route": {
            "route_id": active_route_id or route.get("route_id"),
            "route_version": route.get("route_version") or frontier.get("route_version"),
            "active_node_id": active_node_id or None,
            "completed_nodes": sorted(completed_nodes),
            "terminal": frontier_terminal,
            "selected_node_id": None,
            "selection_state_is_ui_overlay_only": True,
            "nodes": nodes,
        },
        "frontier": {
            "path": project_relative(project_root, run_root / "execution_frontier.json"),
            "status": frontier.get("status"),
            "active_route_id": frontier.get("active_route_id"),
            "active_node_id": frontier.get("active_node_id"),
            "route_version": frontier.get("route_version"),
        },
        "state": {
            "path": project_relative(project_root, run_state_path(run_root)),
            "status": run_state.get("status"),
            "flags": dict(run_state.get("flags") or {}),
        },
        "packet_ledger": {
            "path": project_relative(project_root, run_root / "packet_ledger.json"),
            "active_packet_id": packet_ledger.get("active_packet_id"),
            "active_packet_status": packet_ledger.get("active_packet_status"),
            "active_packet_holder": packet_ledger.get("active_packet_holder"),
            "latest_packet_chain_audit_passed": packet_ledger.get("latest_packet_chain_audit_passed"),
            "latest_barrier_bundle_audit_passed": packet_ledger.get("latest_barrier_bundle_audit_passed"),
        },
        "next_action": {
            "action_type": pending_action.get("action_type"),
            "to_role": pending_action.get("to_role"),
            "label": pending_action.get("label"),
            "allowed_external_events": pending_action.get("allowed_external_events") or [],
        },
    }


def _write_route_state_snapshot(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_payload: dict[str, Any] | None = None,
    source_event: str | None = None,
) -> None:
    snapshot = _build_route_state_snapshot(
        project_root,
        run_root,
        run_state,
        route_payload=route_payload,
        source_event=source_event,
    )
    write_json(_route_state_snapshot_path(run_root), snapshot)
    _write_current_status_summary(run_root, run_state, route_payload=route_payload)


def _mark_display_plan_dirty(run_state: dict[str, Any]) -> None:
    run_state["visible_plan_sync"] = {}


def _write_display_plan_from_route(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    route_id: str,
    route_version: int,
    route_payload: dict[str, Any],
    active_node_id: str | None,
    source_event: str,
) -> None:
    nodes = _display_route_nodes(route_payload)
    items = []
    for index, node in enumerate(nodes, start=1):
        node_id = str(node.get("node_id") or node.get("id") or f"node-{index:03d}")
        items.append(
            {
                "id": node_id,
                "label": str(node.get("title") or node.get("label") or node_id),
                "status": _route_item_status(
                    run_root,
                    node_id,
                    active_node_id=active_node_id,
                    raw_status=node.get("status"),
                ),
            }
        )
    if not items:
        items.append({"id": "route_pending", "label": "PM route", "status": "pending"})
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "project_manager",
        "source_event": source_event,
        "scope": "route",
        "title": str(route_payload.get("title") or route_payload.get("name") or "FlowPilot route"),
        "route_id": route_id,
        "route_version": route_version,
        "display_depth": _route_display_depth(route_payload),
        "items": items,
        "current_node_id": active_node_id,
        "active_path": _route_active_path(route_payload, active_node_id),
        "hidden_leaf_progress": _route_hidden_leaf_progress(route_payload),
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)
    _mark_display_plan_dirty(run_state)


def _update_display_plan_current_node(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    node_id: str,
    node_title: str,
    checklist: list[dict[str, Any]],
    source_event: str,
) -> None:
    plan = read_json_if_exists(_display_plan_path(run_root))
    if not plan:
        plan = _waiting_for_pm_display_plan(run_state)
    items = plan.setdefault("items", [])
    for item in items:
        if isinstance(item, dict):
            item_id = str(item.get("id") or item.get("node_id") or "")
            item["status"] = _route_item_status(
                run_root,
                item_id,
                active_node_id=node_id,
                raw_status=item.get("status"),
            )
    plan.update(
        {
            "schema_version": DISPLAY_PLAN_SCHEMA,
            "run_id": run_state["run_id"],
            "source_role": "project_manager",
            "source_event": source_event,
            "scope": "node",
            "current_node_id": node_id,
            "current_node": {
                "id": node_id,
                "label": node_title,
                "checklist": checklist,
            },
            "controller_may_invent_route_items": False,
            "updated_at": utc_now(),
        }
    )
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    _mark_display_plan_dirty(run_state)


PRE_ROUTE_PHASE_ITEMS = (
    ("material_understanding", "Material understanding", "pm_material_understanding_card_delivered"),
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


def _latest_pre_route_phase(run_state: dict[str, Any]) -> str | None:
    for delivery in reversed(run_state.get("delivered_cards") or []):
        if not isinstance(delivery, dict):
            continue
        phase = CARD_PHASE_BY_ID.get(str(delivery.get("card_id") or ""))
        if phase:
            return phase
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    for phase, _label, flag in reversed(PRE_ROUTE_PHASE_ITEMS):
        if flags.get(flag):
            return phase
    return None


def _sync_execution_frontier_phase(run_root: Path, run_state: dict[str, Any]) -> None:
    phase = _latest_pre_route_phase(run_state)
    if not phase:
        return
    frontier_path = run_root / "execution_frontier.json"
    frontier = read_json_if_exists(frontier_path)
    if str(frontier.get("status") or run_state.get("status") or "") in RUN_TERMINAL_STATUSES:
        return
    run_state["phase"] = phase
    frontier["phase"] = phase
    if not frontier.get("active_route_id"):
        frontier["status"] = phase
    frontier["updated_at"] = utc_now()
    write_json(frontier_path, frontier)


def _write_pre_route_phase_display_plan_if_needed(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    phase = _latest_pre_route_phase(run_state)
    if phase is None:
        return False
    existing = read_json_if_exists(_display_plan_path(run_root))
    if existing.get("scope") in {"route", "node"} and existing.get("source_role") == "project_manager":
        return False
    phase_order = [item[0] for item in PRE_ROUTE_PHASE_ITEMS]
    active_index = phase_order.index(phase) if phase in phase_order else 0
    items = []
    for index, (item_id, label, _flag) in enumerate(PRE_ROUTE_PHASE_ITEMS):
        if index < active_index:
            status = "completed"
        elif index == active_index:
            status = "in_progress"
        else:
            status = "pending"
        items.append({"id": item_id, "label": label, "status": status})
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "controller",
        "source_event": "derived_pre_route_phase_sync",
        "scope": "pre_route_phase",
        "title": "FlowPilot route preparation",
        "items": items,
        "current_node_id": None,
        "route_authority": "none_until_pm_route_draft",
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    write_json(_display_plan_path(run_root), plan)
    return True


def _reconcile_non_current_running_index_entries(project_root: Path, run_state: dict[str, Any]) -> int:
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json") or {}
    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    current_run_id = str(current.get("current_run_id") or current.get("active_run_id") or "")
    updated = 0
    now = utc_now()
    for item in runs:
        if not isinstance(item, dict):
            continue
        if item.get("run_id") == run_state.get("run_id"):
            item["status"] = run_state.get("status") or item.get("status")
            item["updated_at"] = now
        elif item.get("status") == "running" and str(item.get("run_id") or "") != current_run_id:
            item["status"] = "stale_not_current"
            item["stale_reason"] = "not_current_pointer"
            item["updated_at"] = now
            updated += 1
    if runs:
        index["runs"] = runs
        index["updated_at"] = now
        write_json(index_path, index)
    return updated


def _sync_derived_run_views(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    reason: str,
    update_display: bool = True,
) -> None:
    _sync_control_plane_indexes(project_root, run_root, run_state)
    _sync_child_skill_manifest_review_approval(project_root, run_root)
    _sync_execution_frontier_phase(run_root, run_state)
    _reconcile_non_current_running_index_entries(project_root, run_state)
    display_updated = _write_pre_route_phase_display_plan_if_needed(project_root, run_root, run_state) if update_display else False
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=reason)
    if display_updated:
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        run_state["visible_plan_sync"] = {
            "display_plan_path": sync_payload["display_plan_path"],
            "route_state_snapshot_path": sync_payload["route_state_snapshot_path"],
            "route_state_snapshot_hash": sync_payload["route_state_snapshot_hash"],
            "current_status_summary_path": sync_payload.get("current_status_summary_path"),
            "current_status_summary_hash": sync_payload.get("current_status_summary_hash"),
            "projection_hash": sync_payload["projection_hash"],
            "synced_at": utc_now(),
            "host_action": "derived_pre_route_phase_projection",
        }


def _write_display_plan_from_pm_payload(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str,
) -> None:
    raw_plan = payload.get("display_plan")
    if not isinstance(raw_plan, dict):
        return
    raw_items = raw_plan.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise RouterError(f"{source_event} display_plan requires non-empty items")
    items = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise RouterError(f"{source_event} display_plan items must be objects")
        item_id = item.get("id") or item.get("node_id") or f"item-{index:03d}"
        items.append(
            {
                "id": str(item_id),
                "label": str(item.get("label") or item.get("title") or item_id),
                "status": _route_item_status(
                    run_root,
                    str(item_id),
                    active_node_id=str(raw_plan.get("current_node_id") or ""),
                    raw_status=item.get("status"),
                ),
            }
        )
    plan = {
        "schema_version": DISPLAY_PLAN_SCHEMA,
        "run_id": run_state["run_id"],
        "source_role": "project_manager",
        "source_event": source_event,
        "scope": str(raw_plan.get("scope") or "route"),
        "title": str(raw_plan.get("title") or "FlowPilot route"),
        "items": items,
        "current_node_id": raw_plan.get("current_node_id"),
        "controller_may_invent_route_items": False,
        "updated_at": utc_now(),
    }
    if isinstance(raw_plan.get("current_node"), dict):
        plan["current_node"] = raw_plan["current_node"]
    write_json(_display_plan_path(run_root), plan)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    _mark_display_plan_dirty(run_state)


def _event_markers(run_state: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    for event in run_state.get("events") or []:
        if not isinstance(event, dict):
            continue
        event_name = str(event.get("event") or "")
        if event_name not in names:
            continue
        markers.append(
            {
                "event": event_name,
                "summary": event.get("summary"),
                "recorded_at": event.get("recorded_at"),
            }
        )
    return markers


def _route_node_history(project_root: Path, run_root: Path, route_id: str, route: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for node in _route_nodes(route):
        node_id = str(node["node_id"])
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        source_paths = {
            "node_acceptance_plan": _optional_source_path(project_root, node_root / "node_acceptance_plan.json"),
            "node_acceptance_plan_review": _optional_source_path(project_root, node_root / "reviews" / "node_acceptance_plan_review.json"),
            "parent_backward_replay": _optional_source_path(project_root, node_root / "parent_backward_replay.json"),
            "pm_parent_segment_decision": _optional_source_path(project_root, node_root / "pm_parent_segment_decision.json"),
        }
        nodes.append(
            {
                "node_id": node_id,
                "title": node.get("title"),
                "status": node.get("status") or "unknown",
                "created_by_mutation": bool(node.get("created_by_mutation")),
                "superseded_by": node.get("superseded_by"),
                "source_paths": {key: value for key, value in source_paths.items() if value},
            }
        )
    return nodes


def _refresh_route_memory(project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger: str) -> None:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(frontier.get("active_route_id") or "")
    route_version = int(frontier.get("route_version") or 0)
    route_path = run_root / "routes" / route_id / "flow.json" if route_id else run_root / "routes" / "route-001" / "flow.json"
    route = read_json_if_exists(route_path)
    mutations_path = run_root / "routes" / route_id / "mutations.json" if route_id else run_root / "routes" / "route-001" / "mutations.json"
    mutations = read_json_if_exists(mutations_path)
    stale_ledger_path = run_root / "evidence" / "stale_evidence_ledger.json"
    stale_ledger = read_json_if_exists(stale_ledger_path)
    evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
    evidence_ledger = read_json_if_exists(evidence_ledger_path)
    generated_ledger_path = run_root / "generated_resource_ledger.json"
    generated_ledger = read_json_if_exists(generated_ledger_path)
    completed_nodes = [str(item) for item in (frontier.get("completed_nodes") or [])]
    mutation_items = [item for item in (mutations.get("items") or []) if isinstance(item, dict)]
    superseded_nodes = sorted(
        {
            str(node_id)
            for item in mutation_items
            for node_id in (item.get("superseded_nodes") or [])
        }
    )
    stale_evidence = sorted(
        {
            str(item.get("evidence_id"))
            for item in (stale_ledger.get("items") or [])
            if isinstance(item, dict) and item.get("evidence_id")
        }
        | {
            str(evidence_id)
            for item in mutation_items
            for evidence_id in (item.get("stale_evidence") or [])
        }
    )
    effective_nodes = [str(node.get("node_id")) for node in _effective_route_nodes(route, mutations) if node.get("node_id")]
    route_nodes = _route_node_history(project_root, run_root, route_id or "route-001", route)
    reviewer_blocks = _event_markers(
        run_state,
        {
            "current_node_reviewer_blocks_result",
            "reviewer_blocks_current_node_dispatch",
            "reviewer_blocks_node_acceptance_plan",
            "reviewer_reports_material_insufficient",
            "reviewer_blocks_material_scan_dispatch",
        },
    )
    reviewer_passes = _event_markers(
        run_state,
        {
            "reviewer_reports_material_sufficient",
            "reviewer_passes_research_direct_source_check",
            "reviewer_passes_node_acceptance_plan",
            "current_node_reviewer_passes_result",
            "reviewer_passes_parent_backward_replay",
            "reviewer_passes_evidence_quality_package",
            "reviewer_final_backward_replay_passed",
        },
    )
    research_or_experiments = []
    for label, path in (
        ("research_package", run_root / "research" / "research_package.json"),
        ("worker_research_report", run_root / "research" / "worker_research_report.json"),
        ("research_reviewer_report", run_root / "research" / "research_reviewer_report.json"),
        ("product_architecture_modelability", run_root / "flowguard" / "product_architecture_modelability.json"),
        ("root_contract_modelability", run_root / "flowguard" / "root_contract_modelability.json"),
        ("child_skill_conformance_model", run_root / "flowguard" / "child_skill_conformance_model.json"),
        ("child_skill_product_fit", run_root / "flowguard" / "child_skill_product_fit.json"),
    ):
        source_path = _optional_source_path(project_root, path)
        if source_path:
            research_or_experiments.append({"kind": label, "source_path": source_path})
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
        "execution_frontier": _optional_source_path(project_root, run_root / "execution_frontier.json"),
        "active_route": _optional_source_path(project_root, route_path),
        "route_mutations": _optional_source_path(project_root, mutations_path),
        "packet_ledger": _optional_source_path(project_root, run_root / "packet_ledger.json"),
        "prompt_delivery_ledger": _optional_source_path(project_root, run_root / "prompt_delivery_ledger.json"),
        "evidence_ledger": _optional_source_path(project_root, evidence_ledger_path),
        "stale_evidence_ledger": _optional_source_path(project_root, stale_ledger_path),
        "generated_resource_ledger": _optional_source_path(project_root, generated_ledger_path),
    }
    history_index = {
        "schema_version": ROUTE_HISTORY_INDEX_SCHEMA,
        "run_id": run_state["run_id"],
        "generated_by": "controller",
        "controller_decision_authority": False,
        "sealed_packet_or_result_bodies_read": False,
        "trigger": trigger,
        "refreshed_at": utc_now(),
        "frontier": {
            "status": frontier.get("status"),
            "active_route_id": frontier.get("active_route_id"),
            "active_node_id": frontier.get("active_node_id"),
            "route_version": route_version,
            "completed_nodes": completed_nodes,
            "latest_mutation_path": frontier.get("latest_mutation_path"),
        },
        "route": {
            "effective_nodes": effective_nodes,
            "node_history": route_nodes,
            "route_node_count": len(route_nodes),
        },
        "mutations": {
            "count": len(mutation_items),
            "superseded_nodes": superseded_nodes,
            "items": [
                {
                    "route_version": item.get("route_version"),
                    "active_node_id": item.get("active_node_id"),
                    "reason": item.get("reason"),
                    "superseded_nodes": item.get("superseded_nodes") or [],
                    "stale_evidence": item.get("stale_evidence") or [],
                    "recorded_at": item.get("recorded_at"),
                }
                for item in mutation_items
            ],
        },
        "evidence": {
            "stale_evidence": stale_evidence,
            "unresolved_count": int(evidence_ledger.get("unresolved_count", 0) or 0),
            "stale_count": int(evidence_ledger.get("stale_count", 0) or 0),
            "generated_pending_resource_count": int(generated_ledger.get("pending_resource_count", 0) or 0),
            "generated_unresolved_resource_count": int(generated_ledger.get("unresolved_resource_count", 0) or 0),
        },
        "review_markers": {
            "blocks": reviewer_blocks,
            "passes": reviewer_passes,
        },
        "research_or_experiments": research_or_experiments,
        "source_paths": {key: value for key, value in source_paths.items() if value},
    }
    write_json(_route_history_index_path(run_root), history_index)
    pm_context = {
        "schema_version": PM_PRIOR_PATH_CONTEXT_SCHEMA,
        "run_id": run_state["run_id"],
        "generated_by": "controller",
        "controller_decision_authority": False,
        "sealed_packet_or_result_bodies_read": False,
        "trigger": trigger,
        "refreshed_at": history_index["refreshed_at"],
        "route_position": history_index["frontier"],
        "completed_nodes_considered": completed_nodes,
        "effective_nodes_considered": effective_nodes,
        "superseded_nodes_considered": superseded_nodes,
        "stale_evidence_considered": stale_evidence,
        "review_blocks_considered": reviewer_blocks,
        "review_passes_considered": reviewer_passes,
        "research_or_experiment_outputs_considered": research_or_experiments,
        "future_route_decision_requirements": [
            "Before route draft, route mutation, repair-node creation, node acceptance planning, resume continuation, final ledger, or closure, PM must read this current context and cite its path.",
            "PM must explain how completed, superseded, stale, blocked, and experimental history changes the next route or node decision.",
            "Controller-provided history is an index of reviewed files and state only; PM must not treat it as evidence beyond the cited source paths.",
        ],
        "source_paths": {
            **{key: value for key, value in source_paths.items() if value},
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
    }
    write_json(_pm_prior_path_context_path(run_root), pm_context)
    run_state["flags"]["route_history_index_refreshed"] = True
    run_state["flags"]["pm_prior_path_context_refreshed"] = True


def _require_pm_prior_path_context(project_root: Path, run_root: Path, payload: dict[str, Any], *, purpose: str) -> dict[str, Any]:
    context_path = _pm_prior_path_context_path(run_root)
    history_path = _route_history_index_path(run_root)
    if not context_path.exists() or not history_path.exists():
        raise RouterError(f"{purpose} requires refreshed route memory before PM decision")
    review = payload.get("prior_path_context_review")
    if not isinstance(review, dict):
        raise RouterError(f"{purpose} requires prior_path_context_review")
    if review.get("reviewed") is not True:
        raise RouterError(f"{purpose} requires prior_path_context_review.reviewed=true")
    if review.get("controller_summary_used_as_evidence") is True:
        raise RouterError(f"{purpose} cannot treat Controller route history as acceptance evidence")
    expected_context = project_relative(project_root, context_path)
    expected_history = project_relative(project_root, history_path)
    source_paths = [str(path) for path in (review.get("source_paths") or [])]
    if expected_context not in source_paths:
        raise RouterError(f"{purpose} must cite current pm_prior_path_context.json")
    if expected_history not in source_paths:
        raise RouterError(f"{purpose} must cite current route_history_index.json")
    missing = [
        field
        for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS
        if field not in review and field not in {"reviewed", "source_paths"}
    ]
    if missing:
        raise RouterError(f"{purpose} prior_path_context_review missing fields: {', '.join(missing)}")
    return {
        "reviewed": True,
        "source_paths": [expected_context, expected_history],
        "completed_nodes_considered": review.get("completed_nodes_considered") or [],
        "superseded_nodes_considered": review.get("superseded_nodes_considered") or [],
        "stale_evidence_considered": review.get("stale_evidence_considered") or [],
        "prior_blocks_or_experiments_considered": review.get("prior_blocks_or_experiments_considered") or [],
        "impact_on_decision": review.get("impact_on_decision"),
        "controller_summary_used_as_evidence": False,
    }


def _pm_context_action_extra(project_root: Path, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    if entry.get("to_role") != "project_manager":
        return {}
    context_path = _pm_prior_path_context_path(run_root)
    history_path = _route_history_index_path(run_root)
    extra = {
        "pm_context_paths": {
            "pm_prior_path_context": project_relative(project_root, context_path),
            "route_history_index": project_relative(project_root, history_path),
        },
        "pm_prior_path_context_required_for_decision": entry.get("card_id") in PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS,
        "controller_history_is_evidence": False,
    }
    return extra


def _card_required_source_paths(project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    source_paths: dict[str, str] = {}
    for label, relative_path in CARD_REQUIRED_SOURCE_PATHS.get(card_id, {}).items():
        path = run_root / relative_path
        if path.exists():
            source_paths[label] = project_relative(project_root, path)
    if card_id in {
        "process_officer.route_process_check",
        "product_officer.route_product_check",
        "reviewer.route_challenge",
    }:
        for draft_path in sorted((run_root / "routes").glob("*/flow.draft.json")):
            source_paths[f"route_draft_{draft_path.parent.name}"] = project_relative(project_root, draft_path)
    return source_paths


def _card_delivery_phase(card_id: str, card: dict[str, Any], frontier: dict[str, Any], run_state: dict[str, Any]) -> tuple[str, str | None]:
    card_phase = CARD_PHASE_BY_ID.get(card_id) or card.get("phase")
    current_phase = str(
        card_phase
        or frontier.get("phase")
        or frontier.get("status")
        or run_state.get("phase")
        or "unknown"
    )
    return current_phase, str(card_phase or "") or None


def _live_card_delivery_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    entry: dict[str, Any],
    card: dict[str, Any],
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json") or {}
    card_id = str(entry.get("card_id") or card.get("id") or "")
    current_phase, card_phase = _card_delivery_phase(card_id, card, frontier, run_state)
    user_request_path = str(
        run_state.get("user_request_path")
        or _optional_source_path(project_root, run_root / "user_request.json")
        or ""
    )
    source_paths = {
        "router_state": project_relative(project_root, run_state_path(run_root)),
        "execution_frontier": _optional_source_path(project_root, run_root / "execution_frontier.json"),
        "prompt_delivery_ledger": _optional_source_path(project_root, run_root / "prompt_delivery_ledger.json"),
        "packet_ledger": _optional_source_path(project_root, run_root / "packet_ledger.json"),
        "route_history_index": _optional_source_path(project_root, _route_history_index_path(run_root)),
        "pm_prior_path_context": _optional_source_path(project_root, _pm_prior_path_context_path(run_root)),
        "user_request_path": user_request_path or None,
    }
    source_paths.update(_card_required_source_paths(project_root, run_root, card_id))
    return {
        "schema_version": LIVE_CARD_CONTEXT_SCHEMA,
        "run_id": str(run_state.get("run_id") or run_root.name),
        "card_id": card_id,
        "to_role": str(entry.get("to_role") or card.get("audience") or ""),
        "current_task": {
            "user_request_path": user_request_path or None,
            "user_intake_packet_id": "user_intake" if (run_root / "mailbox" / "outbox" / "user_intake.json").exists() else None,
            "task_authority": "router_recorded_user_request_and_user_intake",
            "controller_summary_is_task_authority": False,
        },
        "current_stage": {
            "current_phase": current_phase,
            "card_phase": card_phase,
            "frontier_status": frontier.get("status"),
            "current_node_id": frontier.get("active_node_id"),
            "current_route_id": frontier.get("active_route_id"),
            "route_version": frontier.get("route_version"),
        },
        "source_paths": source_paths,
        "role_prompt_rule": (
            "Treat this router delivery envelope as the live context for the "
            "current run, current task, current card, current phase, and current "
            "node/frontier. If required context is missing or stale, do not "
            "continue from memory; submit a protocol blocker through the Router-directed runtime path."
        ),
    }


def _write_route_draft(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="route draft")
    contract_path = run_root / "root_acceptance_contract.json"
    if not contract_path.exists():
        raise RouterError("route draft requires frozen root contract")
    contract = read_json(contract_path)
    if contract.get("status") != "frozen":
        raise RouterError("route draft requires root contract status=frozen")
    sync_path = run_root / "capabilities" / "capability_sync.json"
    child_manifest_path = run_root / "child_skill_gate_manifest.json"
    if not sync_path.exists():
        raise RouterError("route draft requires capability evidence sync")
    if not child_manifest_path.exists() or read_json(child_manifest_path).get("status") != "approved":
        raise RouterError("route draft requires approved child-skill gate manifest")
    product_model_path = _require_product_behavior_model_report(project_root, run_root)
    route_id = str(payload.get("route_id") or "route-001")
    route_root = run_root / "routes" / route_id
    draft = payload.get("route") if isinstance(payload.get("route"), dict) else {}
    route_payload = dict(payload)
    original_schema_version = route_payload.get("schema_version")
    if original_schema_version and original_schema_version != "flowpilot.route_draft.v1":
        route_payload["pm_authored_payload_schema_version"] = original_schema_version
    route_payload["schema_version"] = "flowpilot.route_draft.v1"
    route_payload["run_id"] = run_state["run_id"]
    route_payload["route_id"] = route_id
    route_payload["route_version"] = int(payload.get("route_version") or draft.get("route_version") or 1)
    route_payload["source_root_contract"] = project_relative(project_root, contract_path)
    route_payload["source_product_behavior_model"] = project_relative(project_root, product_model_path)
    route_payload["source_product_behavior_model_hash"] = hashlib.sha256(product_model_path.read_bytes()).hexdigest()
    route_payload["prior_path_context_review"] = prior_review
    route_payload["nodes"] = draft.get("nodes") or payload.get("nodes") or []
    route_payload["written_by_role"] = "project_manager"
    route_payload["written_at"] = str(payload.get("written_at") or utc_now())
    route_payload["router_preservation"] = {
        "schema_version": "flowpilot.router_artifact_preservation.v1",
        "canonical_source": "pm_role_output_body",
        "official_artifact_path": project_relative(project_root, route_root / "flow.draft.json"),
        "role_authored_fields_preserved": True,
        "whitelist_rebuild_used": False,
        "recorded_at": utc_now(),
    }
    route_payload.update(_role_output_envelope_record(payload))
    write_json(route_root / "flow.draft.json", route_payload)
    run_state["draft_route_visibility"] = {
        "route_id": route_id,
        "route_version": int(route_payload["route_version"]),
        "draft_path": project_relative(project_root, route_root / "flow.draft.json"),
        "user_visible": False,
        "reason": "draft_routes_are_internal_until_pm_activates_reviewed_flow_json",
        "recorded_at": utc_now(),
    }


def _reset_route_review_after_route_draft_repair(run_state: dict[str, Any]) -> None:
    for flag in (
        "process_officer_route_check_card_delivered",
        "process_officer_route_check_passed",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False


def _reset_route_hard_gate_approvals_for_recheck(run_state: dict[str, Any]) -> None:
    for flag in (
        "pm_route_skeleton_card_delivered",
        "route_draft_written_by_pm",
        "process_officer_route_check_card_delivered",
        "process_officer_route_check_passed",
        "process_officer_route_repair_required",
        "process_officer_route_check_blocked",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False


def _product_behavior_model_report_path(run_root: Path) -> Path:
    return run_root / "flowguard" / "product_architecture_modelability.json"


def _require_product_behavior_model_report(project_root: Path, run_root: Path) -> Path:
    path = _product_behavior_model_report_path(run_root)
    if not path.exists():
        raise RouterError("route draft requires Product Officer product behavior model report")
    report = read_json(path)
    if report.get("passed") is not True:
        raise RouterError("route draft requires passed Product Officer product behavior model report")
    return path


def _route_process_check_path(run_root: Path) -> Path:
    return run_root / "flowguard" / "route_process_check.json"


def _route_product_check_path(run_root: Path) -> Path:
    return run_root / "flowguard" / "route_product_check.json"


def _require_route_process_pass(project_root: Path, run_root: Path) -> Path:
    path = _route_process_check_path(run_root)
    if not path.exists():
        raise RouterError("route activation requires route_process_check.json")
    report = read_json(path)
    if report.get("passed") is not True or report.get("process_viability_verdict") != "pass":
        raise RouterError("route activation requires Process Officer process_viability_verdict=pass")
    return path


def _require_route_product_pass(project_root: Path, run_root: Path) -> Path:
    path = _route_product_check_path(run_root)
    if not path.exists():
        raise RouterError("route activation requires route_product_check.json")
    report = read_json(path)
    if report.get("passed") is not True or report.get("route_model_review_verdict") != "pass":
        raise RouterError("route activation requires passed product-model route review")
    return path


def _current_route_draft_path(run_root: Path) -> Path:
    route_root = run_root / "routes"
    candidates = sorted(route_root.glob("*/flow.draft.json")) if route_root.exists() else []
    if not candidates:
        raise RouterError("route check requires a route draft")
    if len(candidates) > 1:
        raise RouterError("route check requires an unambiguous current route draft")
    return candidates[0]


def _latest_event_payload(run_state: dict[str, Any], event_name: str) -> dict[str, Any]:
    for event in reversed(run_state.get("events", [])):
        if isinstance(event, dict) and event.get("event") == event_name:
            payload = event.get("payload")
            return payload if isinstance(payload, dict) else {}
    return {}


def _packet_paths(project_root: Path, run_state: dict[str, Any], packet_id: str) -> dict[str, Any]:
    return packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))


def _packet_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    raw_path = payload.get("packet_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get("packet_id")
    if not packet_id:
        raise RouterError("current-node packet event requires packet_id or packet_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["packet_envelope"]


def _result_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    raw_path = payload.get("result_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get("packet_id") or _latest_event_payload(run_state, "pm_registers_current_node_packet").get("packet_id")
    if not packet_id:
        raise RouterError("current-node result event requires packet_id or result_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["result_envelope"]


def _current_node_packet_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    payload = _latest_event_payload(run_state, "pm_registers_current_node_packet")
    envelope_path = _packet_envelope_path(project_root, run_state, payload)
    if not envelope_path.exists():
        raise RouterError(f"current-node packet envelope is missing: {envelope_path}")
    envelope = packet_runtime.load_envelope(project_root, envelope_path)
    return envelope, envelope_path


def _current_node_packet_records(project_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    run_root = project_root / str(run_state["run_root"])
    frontier = _active_frontier(run_root)
    index_path = _active_node_packet_index_path(run_root, frontier)
    if index_path.exists():
        return _load_packet_index(index_path, label="current-node batch")["packets"]
    envelope, _envelope_path = _current_node_packet_context(project_root, run_state)
    return [_packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=str(envelope.get("packet_type") or "work_packet"))]


def _current_node_results_complete(project_root: Path, run_state: dict[str, Any]) -> bool:
    for record in _current_node_packet_records(project_root, run_state):
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            return False
    return True


def _current_node_missing_result_roles(project_root: Path, run_state: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for record in _current_node_packet_records(project_root, run_state):
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            missing.append(str(record.get("to_role") or record.get("packet_id") or "unknown"))
    return sorted(set(missing))


def _active_child_skill_bindings_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    raw_bindings = plan.get("active_child_skill_bindings")
    if raw_bindings in (None, []):
        return []
    if not isinstance(raw_bindings, list):
        raise RouterError("node_acceptance_plan.active_child_skill_bindings must be a list")
    bindings: list[dict[str, Any]] = []
    for index, binding in enumerate(raw_bindings, start=1):
        if not isinstance(binding, dict):
            raise RouterError(f"active_child_skill_bindings[{index}] must be an object")
        if binding.get("applies_to_this_node") is False:
            continue
        if not binding.get("binding_id"):
            raise RouterError(f"active_child_skill_bindings[{index}] requires binding_id")
        if not binding.get("source_path"):
            raise RouterError(f"active_child_skill_bindings[{index}] requires source_path")
        bindings.append(binding)
    return bindings


def _active_child_skill_source_paths(bindings: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for binding in bindings:
        source_path = binding.get("source_path")
        if source_path:
            paths.append(str(source_path))
        referenced_paths = binding.get("referenced_paths")
        if isinstance(referenced_paths, list):
            paths.extend(str(item) for item in referenced_paths if item)
    return sorted(set(paths))


def _metadata_string_list(metadata: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw_value = metadata.get(key)
        if isinstance(raw_value, list):
            values.extend(str(item) for item in raw_value if item)
        elif isinstance(raw_value, str) and raw_value:
            values.append(raw_value)
    return sorted(set(values))


def _metadata_binding_ids(metadata: dict[str, Any], *keys: str) -> list[str]:
    ids: list[str] = []
    for key in keys:
        raw_value = metadata.get(key)
        if isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, dict) and item.get("binding_id"):
                    ids.append(str(item["binding_id"]))
                elif isinstance(item, str) and item:
                    ids.append(item)
    return sorted(set(ids))


def _current_node_result_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    payload = _latest_event_payload(run_state, "worker_current_node_result_returned")
    result_path = _result_envelope_path(project_root, run_state, payload)
    if not result_path.exists():
        raise RouterError(f"current-node result envelope is missing: {result_path}")
    result = packet_runtime.load_envelope(project_root, result_path)
    return result, result_path


def _packet_envelope_path_from_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    raw_path = record.get("packet_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get("packet_id")
    if not packet_id:
        raise RouterError("packet record requires packet_id or packet_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["packet_envelope"]


def _result_envelope_path_from_packet_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    raw_path = record.get("result_envelope_path")
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get("packet_id")
    if not packet_id:
        raise RouterError("packet record requires packet_id or result_envelope_path")
    return _packet_paths(project_root, run_state, str(packet_id))["result_envelope"]


def _load_packet_index(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        raise RouterError(f"{label} packet index is missing: {path}")
    index = read_json(path)
    if not isinstance(index.get("packets"), list) or not index["packets"]:
        raise RouterError(f"{label} packet index requires non-empty packets")
    return index


def _ensure_barrier_bundles_ready(project_root: Path, *, node_id: str | None = None) -> None:
    audit = packet_runtime.audit_barrier_bundles(project_root, node_id=node_id or None)
    if not audit.get("passed"):
        raise RouterError(
            "barrier bundle audit failed before packet relay: "
            + json.dumps(audit.get("blockers", []), sort_keys=True)
        )


def _material_scan_index_path(run_root: Path) -> Path:
    return run_root / "material" / "material_scan_packets.json"


def _research_packet_index_path(run_root: Path) -> Path:
    return run_root / "research" / "research_packet.json"


def _parallel_packet_batch_root(run_root: Path) -> Path:
    return run_root / "packet_batches"


def _parallel_packet_batch_path(run_root: Path, batch_id: str) -> Path:
    return _parallel_packet_batch_root(run_root) / f"{_safe_packet_id_component(batch_id)}.json"


def _parallel_packet_batch_ref_path(run_root: Path, batch_kind: str) -> Path:
    return _parallel_packet_batch_root(run_root) / f"active_{_safe_packet_id_component(batch_kind)}.json"


def _packet_record_from_envelope(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    envelope: dict[str, Any],
    packet_type: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    packet_id = str(envelope.get("packet_id") or "").strip()
    if not packet_id:
        raise RouterError("packet envelope requires packet_id")
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
    record = {
        "packet_id": packet_id,
        "to_role": str(envelope.get("to_role") or ""),
        "packet_type": packet_type or str(envelope.get("packet_type") or ""),
        "packet_envelope_path": str(envelope.get("body_path") or "").replace("packet_body.md", "packet_envelope.json"),
        "packet_body_path": envelope.get("body_path"),
        "packet_body_hash": envelope.get("body_hash"),
        "body_path": envelope.get("body_path"),
        "body_hash": envelope.get("body_hash"),
        "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
        "result_body_path": project_relative(project_root, paths["result_body"]),
        "result_write_target": {
            "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
            "result_body_path": project_relative(project_root, paths["result_body"]),
        },
        "output_contract_id": envelope.get("output_contract_id"),
        "status": "registered",
    }
    if request_id:
        record["request_id"] = request_id
    return record


def _write_parallel_packet_batch(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    batch_id: str,
    batch_kind: str,
    phase: str,
    records: list[dict[str, Any]],
    node_id: str | None = None,
    join_policy: str = "all_results_before_review",
    review_policy: str = "batch_review_before_pm",
    pm_absorption_required: bool = True,
    parent_batch_id: str | None = None,
) -> dict[str, Any]:
    if not batch_id:
        raise RouterError("parallel packet batch requires batch_id")
    if not records:
        raise RouterError("parallel packet batch requires at least one packet")
    packet_ids = [str(record.get("packet_id") or "").strip() for record in records]
    if any(not packet_id for packet_id in packet_ids):
        raise RouterError("parallel packet batch packets require packet_id")
    if len(set(packet_ids)) != len(packet_ids):
        raise RouterError("parallel packet batch packet_id values must be unique")
    to_roles = [str(record.get("to_role") or "").strip() for record in records]
    if any(not role for role in to_roles):
        raise RouterError("parallel packet batch packets require to_role")
    if len(set(to_roles)) != len(to_roles):
        raise RouterError("parallel packet batch cannot assign two open packets to the same role")
    batch_path = _parallel_packet_batch_path(run_root, batch_id)
    existing = read_json_if_exists(batch_path)
    if existing and existing.get("status") in PARALLEL_PACKET_BATCH_OPEN_STATUSES:
        raise RouterError(f"parallel packet batch is already open: {batch_id}")
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item["batch_id"] = batch_id
        item["batch_kind"] = batch_kind
        item.setdefault("status", "registered")
        record.update(item)
        normalized_records.append(item)
    batch = {
        "schema_version": PARALLEL_PACKET_BATCH_SCHEMA,
        "run_id": run_state["run_id"],
        "batch_id": batch_id,
        "batch_kind": batch_kind,
        "phase": phase,
        "node_id": node_id,
        "owner_role": "project_manager",
        "join_policy": join_policy,
        "review_policy": review_policy,
        "pm_absorption_required": pm_absorption_required,
        "parent_batch_id": parent_batch_id,
        "status": "registered",
        "controller_visibility": "packet_and_result_envelopes_only",
        "controller_may_read_packet_body": False,
        "controller_may_read_result_body": False,
        "packets": normalized_records,
        "counts": {
            "registered": len(normalized_records),
            "relayed": 0,
            "results_returned": 0,
            "reviewed": 0,
        },
        "written_at": utc_now(),
        "updated_at": utc_now(),
    }
    write_json(batch_path, batch)
    write_json(
        _parallel_packet_batch_ref_path(run_root, batch_kind),
        {
            "schema_version": PARALLEL_PACKET_BATCH_REF_SCHEMA,
            "run_id": run_state["run_id"],
            "batch_kind": batch_kind,
            "active_batch_id": batch_id,
            "batch_path": project_relative(project_root, batch_path),
            "updated_at": utc_now(),
        },
    )
    return batch


def _load_parallel_packet_batch(run_root: Path, batch_id: str) -> dict[str, Any]:
    path = _parallel_packet_batch_path(run_root, batch_id)
    if not path.exists():
        raise RouterError(f"parallel packet batch is missing: {path}")
    batch = read_json(path)
    if batch.get("schema_version") != PARALLEL_PACKET_BATCH_SCHEMA:
        raise RouterError("parallel packet batch has unsupported schema")
    if not isinstance(batch.get("packets"), list) or not batch["packets"]:
        raise RouterError("parallel packet batch requires non-empty packets")
    return batch


def _active_parallel_packet_batch(run_root: Path, batch_kind: str) -> dict[str, Any] | None:
    ref_path = _parallel_packet_batch_ref_path(run_root, batch_kind)
    ref = read_json_if_exists(ref_path)
    if not ref:
        return None
    batch_id = str(ref.get("active_batch_id") or "").strip()
    if not batch_id:
        return None
    return _load_parallel_packet_batch(run_root, batch_id)


def _write_parallel_packet_batch_state(run_root: Path, batch: dict[str, Any]) -> None:
    batch["updated_at"] = utc_now()
    write_json(_parallel_packet_batch_path(run_root, str(batch["batch_id"])), batch)


def _mark_parallel_batch_packets_relayed(run_root: Path, batch_kind: str) -> None:
    batch = _active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return
    for record in batch["packets"]:
        if isinstance(record, dict):
            record["status"] = "packet_relayed"
            record["relayed_at"] = utc_now()
    batch["status"] = "packets_relayed"
    batch["counts"]["relayed"] = len(batch["packets"])
    _write_parallel_packet_batch_state(run_root, batch)


def _mark_parallel_batch_results_joined(project_root: Path, run_root: Path, run_state: dict[str, Any], batch_kind: str) -> None:
    batch = _active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return
    returned = 0
    for record in batch["packets"]:
        if not isinstance(record, dict):
            continue
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if result_path.exists():
            returned += 1
            record["status"] = "result_returned"
            record["result_returned_at"] = utc_now()
    batch["counts"]["results_returned"] = returned
    if returned == len(batch["packets"]):
        batch["status"] = "results_joined"
        batch["joined_at"] = utc_now()
    _write_parallel_packet_batch_state(run_root, batch)


def _mark_parallel_batch_reviewed(run_root: Path, batch_kind: str, *, passed: bool, reviewed_packet_ids: list[str]) -> None:
    batch = _active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return
    batch["status"] = "reviewed" if passed else "review_blocked"
    batch["review"] = {
        "passed": passed,
        "reviewed_packet_ids": reviewed_packet_ids,
        "reviewed_at": utc_now(),
    }
    batch["counts"]["reviewed"] = len(reviewed_packet_ids)
    _write_parallel_packet_batch_state(run_root, batch)


def _pm_role_work_request_index_path(run_root: Path) -> Path:
    return run_root / "pm_work_requests" / "index.json"


def _empty_pm_role_work_request_index(run_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PM_ROLE_WORK_REQUEST_INDEX_SCHEMA,
        "run_id": run_state["run_id"],
        "controller_visibility": "packet_and_result_envelopes_only",
        "controller_may_read_packet_body": False,
        "controller_may_read_result_body": False,
        "active_request_id": None,
        "active_batch_id": None,
        "active_request_ids": [],
        "requests": [],
        "written_at": utc_now(),
        "updated_at": utc_now(),
    }


def _load_pm_role_work_request_index(run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    path = _pm_role_work_request_index_path(run_root)
    if not path.exists():
        return _empty_pm_role_work_request_index(run_state)
    index = read_json(path)
    if index.get("schema_version") != PM_ROLE_WORK_REQUEST_INDEX_SCHEMA:
        raise RouterError("PM role-work request index has unsupported schema")
    if not isinstance(index.get("requests"), list):
        raise RouterError("PM role-work request index requires requests list")
    index.setdefault("active_request_id", None)
    index.setdefault("active_batch_id", None)
    index.setdefault("active_request_ids", [])
    return index


def _write_pm_role_work_request_index(run_root: Path, index: dict[str, Any]) -> None:
    index["updated_at"] = utc_now()
    write_json(_pm_role_work_request_index_path(run_root), index)


def _pm_role_work_request_record(index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    for record in index.get("requests", []):
        if isinstance(record, dict) and record.get("request_id") == request_id:
            return record
    return None


def _active_pm_role_work_request(index: dict[str, Any]) -> dict[str, Any] | None:
    active_id = str(index.get("active_request_id") or "").strip()
    if active_id:
        active = _pm_role_work_request_record(index, active_id)
        if isinstance(active, dict) and active.get("status") in PM_ROLE_WORK_OPEN_STATUSES:
            return active
    for record in reversed(index.get("requests", [])):
        if isinstance(record, dict) and record.get("status") in PM_ROLE_WORK_OPEN_STATUSES:
            return record
    return None


def _active_pm_role_work_batch_records(index: dict[str, Any]) -> list[dict[str, Any]]:
    active_ids = index.get("active_request_ids")
    if not isinstance(active_ids, list) or not active_ids:
        return []
    wanted = {str(item) for item in active_ids}
    records = [
        record
        for record in index.get("requests", [])
        if isinstance(record, dict)
        and str(record.get("request_id")) in wanted
        and record.get("status") in PM_ROLE_WORK_OPEN_STATUSES
    ]
    return records


def _unresolved_pm_role_work_requests(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    index = _load_pm_role_work_request_index(run_root, run_state)
    return [
        record
        for record in index.get("requests", [])
        if isinstance(record, dict) and record.get("status") in PM_ROLE_WORK_OPEN_STATUSES
    ]


def _safe_packet_id_component(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")
    return safe[:80] or "request"


def _pm_role_work_request_body_text(project_root: Path, payload: dict[str, Any]) -> tuple[str, dict[str, str]]:
    path_pairs = (
        ("packet_body_path", "packet_body_hash"),
        ("request_body_path", "request_body_hash"),
        ("body_path", "body_hash"),
    )
    for path_key, hash_key in path_pairs:
        raw_path = payload.get(path_key)
        raw_hash = payload.get(hash_key)
        if not raw_path:
            continue
        if not raw_hash:
            raise RouterError(f"PM role-work request {path_key} requires matching {hash_key}")
        path = resolve_project_path(project_root, str(raw_path))
        if not path.exists():
            raise RouterError(f"PM role-work request body path is missing: {raw_path}")
        actual_hash = packet_runtime.sha256_file(path)
        if actual_hash != str(raw_hash):
            raise RouterError("PM role-work request body hash mismatch")
        body_text = path.read_text(encoding="utf-8")
        if not body_text.strip():
            raise RouterError("PM role-work request body file is empty")
        return body_text, {path_key: project_relative(project_root, path), hash_key: actual_hash}
    if isinstance(payload.get("body_text"), str) and payload["body_text"].strip():
        raise RouterError(
            "PM role-work request body must be file-backed; use packet_body_path/packet_body_hash "
            "so Controller does not receive the role-work body inline"
        )
    raise RouterError("PM role-work request requires file-backed packet_body_path/packet_body_hash")


def _validate_pm_role_work_process_contract_binding(
    *,
    contract_id: str,
    to_role: str,
    request_kind: str,
) -> dict[str, Any]:
    foreign_current_node_contract = "flowpilot.output_contract.worker_current_node_result.v1"
    foreign_current_node_family = "worker.current_node"
    if contract_id in PM_ROLE_WORK_FOREIGN_CONTRACT_IDS or contract_id == foreign_current_node_contract:
        raise RouterError(
            f"output_contract_id {contract_id} does not match PM role-work process; "
            f"{foreign_current_node_family} belongs to current-node execution, not delegated PM side work"
        )
    process_kind = PM_ROLE_WORK_CONTRACT_PROCESS_KINDS.get(contract_id)
    if not process_kind:
        raise RouterError(f"PM role-work request output_contract_id is not allowed for PM role-work process: {contract_id}")
    binding = dict(PROCESS_CONTRACT_BINDINGS[process_kind])
    if process_kind in {"officer_model_report", "officer_model_miss_report"} and to_role not in {
        "process_flowguard_officer",
        "product_flowguard_officer",
    }:
        raise RouterError(f"output_contract_id {contract_id} is an officer process contract and must target an officer role")
    if process_kind == "officer_model_miss_report" and request_kind != "model_miss":
        raise RouterError("officer model-miss contract requires request_kind=model_miss")
    if process_kind == "pm_role_work_request" and to_role not in PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES:
        raise RouterError("PM role-work process target role is not allowed")
    return {
        "process_kind": process_kind,
        "task_family": binding["task_family"],
        "contract_id": binding["contract_id"],
        "packet_type": binding["packet_type"],
        "required_result_next_recipient": binding["required_result_next_recipient"],
        "absorbing_role": binding["absorbing_role"],
    }


def _pm_role_work_packet_type_from_contract(
    run_root: Path,
    *,
    contract_id: str,
    to_role: str,
    request_kind: str,
) -> str:
    del run_root
    binding = _validate_pm_role_work_process_contract_binding(
        contract_id=contract_id,
        to_role=to_role,
        request_kind=request_kind,
    )
    return str(binding["packet_type"])


def _pm_role_work_output_contract(
    run_root: Path,
    *,
    contract_id: str,
    to_role: str,
    packet_type: str,
    node_id: str,
) -> dict[str, Any]:
    registry_path = run_root / "runtime_kit" / "contracts" / "contract_index.json"
    registry = read_json_if_exists(registry_path)
    if not registry:
        registry_path = runtime_kit_source() / "contracts" / "contract_index.json"
        registry = read_json(registry_path)
    for contract in registry.get("contracts", []):
        if not isinstance(contract, dict) or contract.get("contract_id") != contract_id:
            continue
        roles = contract.get("recipient_roles")
        if isinstance(roles, list) and to_role not in roles:
            raise RouterError(f"output contract {contract_id} does not allow recipient role {to_role}")
        selected = dict(contract)
        selected["selected_by_role"] = "project_manager"
        selected["recipient_role"] = to_role
        selected["node_id"] = node_id
        selected["packet_type"] = packet_type
        selected["registry_path"] = "runtime_kit/contracts/contract_index.json"
        return selected
    raise RouterError(f"PM role-work request output_contract_id is not in the registry: {contract_id}")


def _pm_role_work_channel_open(run_state: dict[str, Any]) -> bool:
    if run_state.get("flags", {}).get("model_miss_triage_followup_request_pending"):
        return True
    pending = run_state.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == "await_role_decision":
        to_role = str(pending.get("to_role") or "")
        if "project_manager" in {part.strip() for part in to_role.split(",")}:
            return True
        allowed = pending.get("allowed_external_events")
        if isinstance(allowed, list) and any(str(item).startswith("pm_") for item in allowed):
            return True
    for group in _pending_expected_external_event_groups(run_state):
        roles = {_event_wait_role(event, meta) for event, meta in group}
        if "project_manager" in roles:
            return True
    return False


def _model_miss_followup_expectation(run_state: dict[str, Any]) -> dict[str, Any] | None:
    followup = run_state.get("model_miss_triage_followup_request")
    if isinstance(followup, dict) and followup.get("status") == "awaiting_pm_role_work_request":
        return followup
    followup = run_state.get("model_miss_evidence_followup_request")
    if isinstance(followup, dict) and followup.get("status") == "awaiting_pm_role_work_request":
        return followup
    return None


def _validate_pm_role_work_request_against_followup(
    run_state: dict[str, Any],
    *,
    request_id: str,
    to_role: str,
    request_kind: str,
    output_contract_id: str,
) -> None:
    followup = _model_miss_followup_expectation(run_state)
    if followup is None:
        return
    required_kind = str(followup.get("required_request_kind") or "").strip()
    if required_kind and request_kind != required_kind:
        raise RouterError(f"PM role-work request must use request_kind={required_kind} for the pending model-miss follow-up")
    required_contract = str(followup.get("required_output_contract_id") or "").strip()
    if required_contract and output_contract_id != required_contract:
        raise RouterError(f"PM role-work request must use output_contract_id={required_contract} for the pending model-miss follow-up")
    allowed_roles = followup.get("suggested_to_roles")
    if isinstance(allowed_roles, list) and allowed_roles and to_role not in allowed_roles:
        raise RouterError("PM role-work request targets a role outside the pending model-miss follow-up roles")
    followup["status"] = "request_registered"
    followup["request_id"] = request_id
    followup["registered_at"] = utc_now()
    if run_state.get("model_miss_triage_followup_request") is followup:
        run_state["model_miss_triage_followup_request"] = followup
    if run_state.get("model_miss_evidence_followup_request") is followup:
        run_state["model_miss_evidence_followup_request"] = followup
    run_state["flags"]["model_miss_triage_followup_request_pending"] = False


def _repair_transactions_root(run_root: Path) -> Path:
    return run_root / "control_blocks" / "repair_transactions"


def _repair_transaction_index_path(run_root: Path) -> Path:
    return _repair_transactions_root(run_root) / "repair_transaction_index.json"


def _repair_transaction_path(run_root: Path, transaction_id: str) -> Path:
    return _repair_transactions_root(run_root) / f"{transaction_id}.json"


def _repair_transaction_id(blocker_id: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in blocker_id).strip("-")
    return f"repair-tx-{safe or 'control-blocker'}"


def _repair_outcome_table(rerun_target: str) -> dict[str, dict[str, Any]]:
    if rerun_target in {
        "router_direct_material_scan_dispatch_recheck_passed",
        "reviewer_allows_material_scan_dispatch",
    }:
        return {
            "success": {
                "event": "router_direct_material_scan_dispatch_recheck_passed",
                "terminal": "complete",
            },
            "blocker": {
                "event": "router_direct_material_scan_dispatch_recheck_blocked",
                "terminal": "blocked",
            },
            "protocol_blocker": {
                "event": "router_protocol_blocker_material_scan_dispatch_recheck",
                "terminal": "blocked",
            },
        }
    return {
        "success": {
            "event": rerun_target,
            "terminal": "complete",
        },
        "blocker": {
            "event": rerun_target,
            "terminal": "blocked",
            "shares_success_event": True,
        },
        "protocol_blocker": {
            "event": rerun_target,
            "terminal": "blocked",
            "shares_success_event": True,
        },
    }


def _repair_outcome_events(outcome_table: dict[str, Any]) -> list[str]:
    events: list[str] = []
    for name in ("success", "blocker", "protocol_blocker"):
        outcome = outcome_table.get(name)
        if not isinstance(outcome, dict):
            continue
        event = str(outcome.get("event") or "").strip()
        if event and event not in events:
            events.append(event)
    return events


def _repair_packet_specs_from_decision(
    project_root: Path,
    run_root: Path,
    decision: dict[str, Any],
    *,
    rerun_target: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    transaction = decision.get("repair_transaction") if isinstance(decision.get("repair_transaction"), dict) else {}
    raw_packets = (
        transaction.get("replacement_packets")
        or transaction.get("packets")
        or decision.get("replacement_packets")
        or decision.get("packets")
    )
    if isinstance(raw_packets, list) and raw_packets:
        return raw_packets, {
            "source": "decision_inline",
            "packet_count": len(raw_packets),
        }

    raw_path = (
        transaction.get("replacement_packet_specs_path")
        or transaction.get("packet_reissue_spec_path")
        or decision.get("replacement_packet_specs_path")
        or decision.get("packet_reissue_spec_path")
    )
    if not raw_path and rerun_target in {
        "router_direct_material_scan_dispatch_recheck_passed",
        "reviewer_allows_material_scan_dispatch",
    }:
        default_path = run_root / "material" / "pm_material_scan_packet_specs_reissue.project_manager.json"
        if default_path.exists():
            raw_path = project_relative(project_root, default_path)
    if not raw_path:
        return [], None

    spec_path = resolve_project_path(project_root, str(raw_path))
    if not spec_path.exists():
        raise RouterError(f"repair transaction packet spec path is missing: {raw_path}")
    expected_hash = (
        transaction.get("replacement_packet_specs_hash")
        or transaction.get("packet_reissue_spec_hash")
        or decision.get("replacement_packet_specs_hash")
        or decision.get("packet_reissue_spec_hash")
    )
    if expected_hash and packet_runtime.sha256_file(spec_path) != str(expected_hash):
        raise RouterError("repair transaction packet spec hash mismatch")
    spec = read_json(spec_path)
    packets = spec.get("packets")
    if not isinstance(packets, list) or not packets:
        raise RouterError("repair transaction packet spec requires non-empty packets")
    return packets, {
        "source": "packet_spec_file",
        "path": project_relative(project_root, spec_path),
        "sha256": packet_runtime.sha256_file(spec_path),
        "packet_count": len(packets),
    }


def _write_repair_transaction_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    root = _repair_transactions_root(run_root)
    transactions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    if root.exists():
        for path in sorted(root.glob("repair-tx-*.json")):
            record = read_json_if_exists(path)
            if record.get("schema_version") != REPAIR_TRANSACTION_SCHEMA:
                continue
            summary = {
                "transaction_id": record.get("transaction_id"),
                "blocker_id": record.get("blocker_id"),
                "status": record.get("status"),
                "plan_kind": record.get("plan_kind"),
                "packet_generation_id": record.get("packet_generation_id"),
                "path": project_relative(project_root, path),
                "outcome_table": record.get("outcome_table"),
            }
            transactions.append(summary)
            if record.get("status") in {"opened", "committed", "awaiting_recheck"}:
                active = summary
    index = {
        "schema_version": REPAIR_TRANSACTION_INDEX_SCHEMA,
        "run_id": run_state.get("run_id"),
        "active_transaction": active,
        "transactions": transactions,
        "updated_at": utc_now(),
    }
    write_json(_repair_transaction_index_path(run_root), index)
    run_state["repair_transactions"] = transactions
    run_state["active_repair_transaction"] = active


def _commit_material_scan_repair_generation(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    transaction_id: str,
    packet_generation_id: str,
    packet_specs: list[dict[str, Any]],
) -> dict[str, Any]:
    existing_index = read_json_if_exists(_material_scan_index_path(run_root))
    superseded_packets = []
    for record in existing_index.get("packets", []) if isinstance(existing_index.get("packets"), list) else []:
        if isinstance(record, dict):
            superseded = dict(record)
            superseded["is_current_generation"] = False
            superseded["superseded_by_generation_id"] = packet_generation_id
            superseded_packets.append(superseded)

    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError("each repair transaction packet spec must be an object")
        packet_id = str(spec.get("packet_id") or f"material-scan-repair-{index:03d}")
        to_role = str(spec.get("to_role") or "worker_a")
        if to_role not in {"worker_a", "worker_b"}:
            raise RouterError("material scan repair packet must target worker_a or worker_b")
        body_text = _material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(
            project_root,
            run_id=str(run_state["run_id"]),
            packet_id=packet_id,
            from_role="project_manager",
            to_role=to_role,
            node_id=str(spec.get("node_id") or "material-intake"),
            body_text=body_text,
            is_current_node=False,
            packet_type="material_scan",
            metadata={
                "stage": "material_scan",
                "source": "repair_transaction_commit",
                "repair_transaction_id": transaction_id,
                "packet_generation_id": packet_generation_id,
                "replacement_for": spec.get("replacement_for"),
                **(spec.get("metadata") if isinstance(spec.get("metadata"), dict) else {}),
            },
            output_contract=spec.get("output_contract") if isinstance(spec.get("output_contract"), dict) else None,
        )
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
        records.append(
            {
                "packet_id": packet_id,
                "to_role": to_role,
                "packet_generation_id": packet_generation_id,
                "repair_transaction_id": transaction_id,
                "replacement_for": spec.get("replacement_for"),
                "is_current_generation": True,
                "packet_envelope_path": envelope["body_path"].replace("packet_body.md", "packet_envelope.json"),
                "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                "result_body_path": project_relative(project_root, paths["result_body"]),
                "result_write_target": {
                    "result_envelope_path": project_relative(project_root, paths["result_envelope"]),
                    "result_body_path": project_relative(project_root, paths["result_body"]),
                },
                "output_contract_id": envelope.get("output_contract_id"),
            }
        )

    write_json(
        _material_scan_index_path(run_root),
        {
            "schema_version": "flowpilot.material_scan_packets.v2",
            "run_id": run_state["run_id"],
            "written_by_role": "project_manager",
            "controller_may_read_packet_body": False,
            "router_direct_dispatch_required_before_worker": True,
            "reviewer_dispatch_required_before_worker": False,
            "current_generation_id": packet_generation_id,
            "repair_transaction_id": transaction_id,
            "packets": records,
            "superseded_packets": superseded_packets,
            "written_at": utc_now(),
        },
    )
    run_state["flags"]["material_scan_packets_relayed"] = False
    run_state["flags"]["worker_packets_delivered"] = False
    run_state["flags"]["worker_scan_results_returned"] = False
    run_state["flags"]["material_scan_results_relayed_to_reviewer"] = False
    run_state["flags"]["material_review_sufficient"] = False
    run_state["flags"]["material_review_insufficient"] = False
    run_state["material_review"] = None
    return {
        "packet_generation_id": packet_generation_id,
        "packet_count": len(records),
        "packets": records,
        "superseded_packet_count": len(superseded_packets),
        "dispatch_index_path": project_relative(project_root, _material_scan_index_path(run_root)),
        "packet_ledger_path": project_relative(project_root, run_root / "packet_ledger.json"),
    }


def _active_repair_transaction_for_event(run_root: Path, event: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    root = _repair_transactions_root(run_root)
    if not root.exists():
        return None, None
    for path in sorted(root.glob("repair-tx-*.json"), reverse=True):
        record = read_json_if_exists(path)
        if record.get("schema_version") != REPAIR_TRANSACTION_SCHEMA:
            continue
        if record.get("status") not in {"committed", "awaiting_recheck", "opened"}:
            continue
        if event in _repair_outcome_events(record.get("outcome_table") if isinstance(record.get("outcome_table"), dict) else {}):
            return path, record
    return None, None


def _repair_transaction_outcome_kind(transaction: dict[str, Any], event: str) -> str | None:
    table = transaction.get("outcome_table")
    if not isinstance(table, dict):
        return None
    for kind in ("success", "blocker", "protocol_blocker"):
        outcome = table.get(kind)
        if isinstance(outcome, dict) and outcome.get("event") == event:
            return kind
    return None


def _clear_successful_repair_lane_state(run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    rerun_target = str(transaction.get("rerun_target") or "")
    is_material_repair = event in MATERIAL_REPAIR_OUTCOME_EVENTS or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS
    flags = run_state.get("flags")
    if isinstance(flags, dict) and is_material_repair:
        for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
            flags[flag] = False
        if event in {"router_direct_material_scan_dispatch_recheck_passed", "reviewer_allows_material_scan_dispatch"}:
            flags["material_scan_dispatch_blocked"] = False
    if is_material_repair:
        run_state["material_dispatch_block"] = None
    pending = run_state.get("pending_action")
    if isinstance(pending, dict):
        outcome_events = set(
            _repair_outcome_events(
                transaction.get("outcome_table") if isinstance(transaction.get("outcome_table"), dict) else {}
            )
        )
        pending_events = set(
            str(item)
            for item in pending.get("allowed_external_events", [])
            if isinstance(item, str)
        )
        if pending.get("repair_transaction_id") == transaction.get("transaction_id") or (
            pending_events and pending_events.issubset(outcome_events)
        ):
            run_state["pending_action"] = None


def _finalize_repair_transaction_outcome(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
) -> dict[str, Any] | None:
    tx_path, transaction = _active_repair_transaction_for_event(run_root, event)
    if tx_path is None or transaction is None:
        return None
    outcome_kind = _repair_transaction_outcome_kind(transaction, event)
    if not outcome_kind:
        return None
    now = utc_now()
    transaction["reviewer_recheck"] = {
        "outcome": outcome_kind,
        "event": event,
        "payload_envelope_public_view": _control_payload_public_view(payload),
        "recorded_at": now,
    }
    if outcome_kind == "success":
        transaction["status"] = "complete"
        transaction["completed_at"] = now
        write_json(tx_path, transaction)
        _clear_successful_repair_lane_state(run_state, transaction, event=event)
        _write_repair_transaction_index(project_root, run_root, run_state)
        return {
            "transaction_id": transaction.get("transaction_id"),
            "outcome": outcome_kind,
            "status": "complete",
        }

    transaction["status"] = "blocked"
    transaction["blocked_at"] = now
    transaction["followup_blocker_required"] = True
    write_json(tx_path, transaction)

    blocker_id = str(transaction.get("blocker_id") or "")
    active = run_state.get("active_control_blocker")
    artifact_rel = str(active.get("blocker_artifact_path") or "") if isinstance(active, dict) else ""
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            blocker_record = read_json(artifact_path)
            if blocker_record.get("blocker_id") == blocker_id:
                blocker_record["resolution_status"] = f"repair_transaction_{outcome_kind}"
                blocker_record["resolved_by_event"] = event
                blocker_record["resolved_at"] = now
                blocker_record["repair_transaction_id"] = transaction.get("transaction_id")
                write_json(artifact_path, blocker_record)

    followup = _write_control_blocker(
        project_root,
        run_root,
        run_state,
        source="repair_transaction_recheck",
        error_message=(
            f"repair transaction {transaction.get('transaction_id')} ended with reviewer "
            f"{outcome_kind}; PM repair or routing decision is required before retrying dispatch."
        ),
        event=event,
        payload=payload,
    )
    transaction["followup_blocker_id"] = followup.get("blocker_id")
    transaction["followup_blocker_path"] = followup.get("blocker_artifact_path")
    write_json(tx_path, transaction)
    _write_repair_transaction_index(project_root, run_root, run_state)
    return {
        "transaction_id": transaction.get("transaction_id"),
        "outcome": outcome_kind,
        "status": "blocked",
        "followup_blocker_id": followup.get("blocker_id"),
    }


def _relay_packet_records(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    controller_agent_id: str,
) -> list[str]:
    relayed_ids: list[str] = []
    for record in records:
        envelope_path = _packet_envelope_path_from_record(project_root, run_state, record)
        if not envelope_path.exists():
            raise RouterError(f"packet envelope is missing: {envelope_path}")
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        audit = packet_runtime.validate_packet_ready_for_direct_relay(
            project_root,
            packet_envelope=envelope,
            envelope_path=envelope_path,
        )
        if not audit.get("passed"):
            raise RouterError(f"packet envelope is not ready for direct relay: {audit.get('blockers')}")
        _ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id=controller_agent_id,
            received_from_role=str(envelope.get("from_role") or "project_manager"),
            relayed_to_role=str(envelope.get("to_role")),
        )
        relayed_ids.append(str(envelope["packet_id"]))
    return relayed_ids


def _relay_result_records(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    to_role: str,
    controller_agent_id: str,
) -> list[str]:
    relayed_ids: list[str] = []
    agent_role_map = _agent_role_map_from_crew_ledger(project_root / str(run_state["run_root"]))
    for record in records:
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f"result envelope is missing: {result_path}")
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get("next_recipient") != to_role:
            raise RouterError(f"result envelope must route to {to_role}")
        if result.get("completed_by_role") == "controller":
            raise RouterError("Controller-origin result is invalid")
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result,
            agent_role_map=agent_role_map,
        )
        if not audit.get("passed"):
            raise RouterError(f"result envelope is not ready for reviewer relay: {audit.get('blockers')}")
        _ensure_barrier_bundles_ready(project_root, node_id=str(result.get("node_id") or ""))
        packet_runtime.controller_relay_envelope(
            project_root,
            envelope=result,
            envelope_path=result_path,
            controller_agent_id=controller_agent_id,
            received_from_role=str(result.get("completed_by_role") or "unknown"),
            relayed_to_role=to_role,
        )
        relayed_ids.append(str(result["packet_id"]))
    return relayed_ids


def _agent_role_map_from_crew_ledger(run_root: Path) -> dict[str, str] | None:
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    agent_role_map: dict[str, str] = {}
    for slot in role_slots:
        if not isinstance(slot, dict):
            continue
        role_key = slot.get("role_key")
        agent_id = slot.get("agent_id")
        if isinstance(role_key, str) and isinstance(agent_id, str) and agent_id.strip():
            agent_role_map[agent_id.strip()] = role_key
    return agent_role_map or None


def _merge_agent_role_maps(primary: dict[str, str] | None, fallback: dict[str, str] | None) -> dict[str, str] | None:
    merged: dict[str, str] = {}
    if isinstance(fallback, dict):
        merged.update({str(key): str(value) for key, value in fallback.items()})
    if isinstance(primary, dict):
        merged.update({str(key): str(value) for key, value in primary.items()})
    return merged or None


def _validate_packet_bodies_opened_by_targets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    for record in records:
        envelope_path = _packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        expected_role = envelope.get("to_role")
        if envelope.get("body_opened_by_role", {}).get("role") != expected_role:
            raise RouterError(
                f"packet {envelope.get('packet_id')} for role={expected_role} body was not opened by target role "
                "after Controller relay"
            )
        try:
            packet_runtime.verify_packet_open_receipt(project_root, envelope, role=str(expected_role))
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f"packet {envelope.get('packet_id')} for role={expected_role} ledger open receipt is invalid: {exc}") from exc


def _validate_results_exist_for_packets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, next_recipient: str) -> None:
    run_root = project_root / str(run_state["run_root"])
    agent_role_map = _agent_role_map_from_crew_ledger(run_root)
    for record in records:
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f"result envelope is missing: {result_path}")
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get("next_recipient") != next_recipient:
            raise RouterError(f"result envelope for packet {result.get('packet_id')} must route to {next_recipient}")
        if result.get("completed_by_role") == "controller":
            raise RouterError("Controller-origin result is invalid")
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result,
            agent_role_map=agent_role_map,
        )
        if not audit.get("passed"):
            raise RouterError(
                f"result envelope for packet {result.get('packet_id')} for role={audit.get('expected_role')} "
                f"failed pre-relay audit: {audit.get('blockers')}"
            )


def _validate_packet_group_for_reviewer(
    project_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    audit_path: Path,
    agent_role_map: dict[str, str] | None = None,
) -> None:
    trusted_agent_role_map = _agent_role_map_from_crew_ledger(project_root / str(run_state["run_root"]))
    merged_agent_role_map = _merge_agent_role_maps(trusted_agent_role_map, agent_role_map)
    audits: list[dict[str, Any]] = []
    blockers: list[str] = []
    evidence_paths: list[Path] = []
    for record in records:
        packet_path = _packet_envelope_path_from_record(project_root, run_state, record)
        result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
        evidence_paths.extend([packet_path, result_path])
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        result_envelope = packet_runtime.load_envelope(project_root, result_path)
        audit = packet_runtime.validate_for_reviewer(
            project_root,
            packet_envelope=packet_envelope,
            result_envelope=result_envelope,
            agent_role_map=merged_agent_role_map,
        )
        audits.append(audit)
        blockers.extend(str(blocker) for blocker in audit.get("blockers") or [])
    run_root = project_root / str(run_state["run_root"])
    proof_path = _router_owned_check_proof_path(audit_path)
    batch_ids = sorted({str(record.get("batch_id")) for record in records if isinstance(record, dict) and record.get("batch_id")})
    reviewed_packet_ids = [str(record.get("packet_id")) for record in records if isinstance(record, dict)]
    write_json(
        audit_path,
        {
            "schema_version": "flowpilot.packet_group_reviewer_audit.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "router_replacement_scope": "mechanical_only",
            "self_attested_ai_claims_accepted_as_proof": False,
            "router_owned_check_proof_path": project_relative(project_root, proof_path),
            "batch_id": batch_ids[0] if len(batch_ids) == 1 else None,
            "batch_ids": batch_ids,
            "packet_count": len(records),
            "reviewed_packet_ids": reviewed_packet_ids,
            "overall_passed": not blockers,
            "audits": audits,
            "blockers": blockers,
            "passed": not blockers,
            "reviewed_at": utc_now(),
        },
    )
    _write_router_owned_check_proof(
        project_root,
        run_root,
        check_name="packet_group_reviewer_audit",
        audit_path=audit_path,
        source_kind="packet_runtime_hash",
        evidence_paths=evidence_paths,
    )
    _validate_router_owned_check_proof(
        project_root,
        run_root,
        check_name="packet_group_reviewer_audit",
        audit_path=audit_path,
    )
    if blockers:
        raise RouterError(f"packet group reviewer audit failed: {blockers}")


def _active_frontier(run_root: Path) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    if not frontier.get("active_route_id") or not frontier.get("active_node_id"):
        raise RouterError("active execution frontier is missing route or node")
    return frontier


def _active_route_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return run_root / "routes" / str(frontier["active_route_id"]) / "flow.json"


def _active_route_flow(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    route_path = _active_route_path(run_root, frontier)
    if not route_path.exists():
        raise RouterError(f"active route flow is missing: {route_path}")
    return read_json(route_path)


def _iter_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return _route_nodes(route)


def _active_node_definition(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    route = _active_route_flow(run_root, frontier)
    active_node_id = str(frontier["active_node_id"])
    return _active_node_definition_from_route(route, active_node_id)


def _active_node_definition_from_route(route: dict[str, Any], active_node_id: str) -> dict[str, Any]:
    for node in _iter_route_nodes(route):
        if node.get("node_id") == active_node_id or node.get("id") == active_node_id:
            return node
    return {"node_id": active_node_id}


def _node_child_ids(node: dict[str, Any]) -> list[str]:
    child_ids: list[str] = []
    for key in ("child_node_ids", "children", "child_nodes"):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            for child in raw_children:
                if isinstance(child, str):
                    child_ids.append(child)
                elif isinstance(child, dict):
                    child_id = child.get("node_id") or child.get("id")
                    if child_id:
                        child_ids.append(str(child_id))
    return child_ids


def _active_node_has_children(run_root: Path, frontier: dict[str, Any]) -> bool:
    return bool(_node_child_ids(_active_node_definition(run_root, frontier)))


def _active_node_root(run_root: Path, frontier: dict[str, Any]) -> Path:
    return run_root / "routes" / str(frontier["active_route_id"]) / "nodes" / str(frontier["active_node_id"])


def _active_node_acceptance_plan_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_acceptance_plan.json"


def _active_node_write_grant_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "current_node_write_grant.json"


def _active_node_packet_index_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "current_node_packet_batch.json"


def _active_node_completion_ledger_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_completion_ledger.json"


def _active_node_completion_write_missing(
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any] | None,
) -> bool:
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier.get("active_node_id") or "")
    if not active_node_id:
        return False
    requested_node_id = str((payload or {}).get("node_id") or active_node_id)
    if requested_node_id != active_node_id:
        return False
    completed_nodes = {str(item) for item in (frontier.get("completed_nodes") or [])}
    return (
        active_node_id not in completed_nodes
        or not _active_node_completion_ledger_path(run_root, frontier).exists()
        or not run_state["flags"].get("node_completion_ledger_updated")
    )


def _node_completion_event_advanced_to_next_node(run_root: Path, payload: dict[str, Any]) -> bool:
    del payload
    frontier = _active_frontier(run_root)
    return frontier.get("status") == "current_node_loop"


def _task_completion_projection_path(run_root: Path) -> Path:
    return run_root / "completion" / "task_completion_projection.json"


def _resume_decision_path(run_root: Path) -> Path:
    return run_root / "continuation" / "pm_resume_decision.json"


def _resume_waits_for_pm_decision(run_state: dict[str, Any]) -> bool:
    flags = run_state["flags"]
    return (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and bool(flags.get("crew_rehydration_report_written"))
        and bool(flags.get("pm_resume_decision_card_delivered"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )


def _write_pm_resume_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("PM resume decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="PM resume decision")
    resume_path = run_root / "continuation" / "resume_reentry.json"
    if not resume_path.exists():
        raise RouterError("PM resume decision requires continuation/resume_reentry.json")
    resume_evidence = read_json(resume_path)
    rehydration_path = run_root / "continuation" / "crew_rehydration_report.json"
    if not run_state["flags"].get("resume_roles_restored") or not rehydration_path.exists():
        raise RouterError("PM resume decision requires crew_rehydration_report before PM runway")
    rehydration_report = read_json(rehydration_path)
    if rehydration_report.get("all_six_roles_ready") is not True:
        raise RouterError("PM resume decision requires all six roles ready")
    if rehydration_report.get("pm_memory_rehydrated") is not True and rehydration_report.get("background_agents_mode") != "single-agent":
        raise RouterError("PM resume decision requires project_manager memory rehydration")
    decision = str(payload.get("decision") or "continue_current_packet_loop")
    if decision not in PM_RESUME_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported PM resume decision: {decision}")
    reminder = payload.get("controller_reminder")
    if not isinstance(reminder, dict):
        raise RouterError("PM resume decision requires controller_reminder")
    if reminder.get("controller_only") is not True:
        raise RouterError("PM resume decision must remind Controller it is controller_only")
    if reminder.get("controller_may_read_sealed_bodies") is not False:
        raise RouterError("PM resume decision must forbid sealed body reads")
    if reminder.get("controller_may_infer_from_chat_history") is not False:
        raise RouterError("PM resume decision must forbid chat-history route inference")
    if reminder.get("controller_may_advance_or_close_route") is not False:
        raise RouterError("PM resume decision must forbid Controller route advance or closure")
    ambiguous = bool(resume_evidence.get("ambiguous_state_blocks_controller_execution"))
    recovery_recorded = bool(payload.get("explicit_recovery_evidence_recorded"))
    if ambiguous and decision == "continue_current_packet_loop" and not recovery_recorded:
        raise RouterError("ambiguous resume state cannot continue without explicit recovery evidence")
    if decision == "close_after_final_ledger_and_terminal_replay" and not (
        run_state["flags"].get("final_ledger_built_clean") and run_state["flags"].get("final_backward_replay_passed")
    ):
        raise RouterError("resume closure requires final ledger and terminal replay to have passed")
    write_json(
        _resume_decision_path(run_root),
        {
            "schema_version": "flowpilot.pm_resume_decision.v1",
            "run_id": run_state["run_id"],
            "decision_owner": "project_manager",
            "decision": decision,
            "resume_ambiguous": ambiguous,
            "explicit_recovery_evidence_recorded": recovery_recorded,
            "source_paths": {
                "resume_reentry": project_relative(project_root, resume_path),
                "router_state": project_relative(project_root, run_state_path(run_root)),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
                "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
                "crew_memory": project_relative(project_root, run_root / "crew_memory"),
                "crew_rehydration_report": project_relative(project_root, rehydration_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            },
            "crew_rehydration_report": {
                "path": project_relative(project_root, rehydration_path),
                "all_six_roles_ready": bool(rehydration_report.get("all_six_roles_ready")),
                "current_run_memory_complete": bool(rehydration_report.get("current_run_memory_complete")),
                "pm_memory_rehydrated": bool(rehydration_report.get("pm_memory_rehydrated")),
                "missing_memory_role_keys": rehydration_report.get("missing_memory_role_keys") or [],
            },
            "prior_path_context_review": prior_review,
            "controller_reminder": {
                "controller_only": True,
                "controller_may_read_sealed_bodies": False,
                "controller_may_infer_from_chat_history": False,
                "controller_may_advance_or_close_route": False,
                "controller_may_create_project_evidence": False,
            },
            "recorded_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_display_plan_from_pm_payload(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_resume_recovery_decision_returned",
    )


def _write_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str = "pm_writes_node_acceptance_plan",
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="node acceptance plan")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("node acceptance plan must be PM-owned")
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier["active_node_id"])
    active_route_id = str(frontier["active_route_id"])
    if payload.get("node_id") and str(payload["node_id"]) != active_node_id:
        raise RouterError("node acceptance plan node_id must match active frontier")
    route_version = int(frontier.get("route_version") or 0)
    if payload.get("route_version") is not None and int(payload["route_version"]) != route_version:
        raise RouterError("node acceptance plan route_version must match active frontier")
    node_requirements = payload.get("node_requirements")
    if not isinstance(node_requirements, list) or not node_requirements:
        raise RouterError("node acceptance plan requires a non-empty node_requirements list")
    experiment_plan = payload.get("experiment_plan")
    if not isinstance(experiment_plan, list):
        raise RouterError("node acceptance plan requires experiment_plan list")
    high_standard = payload.get("high_standard_recheck")
    if not isinstance(high_standard, dict):
        raise RouterError("node acceptance plan requires high_standard_recheck")
    required_high_standard_fields = {
        "ideal_outcome",
        "unacceptable_outcomes",
        "higher_standard_opportunities",
        "semantic_downgrade_risks",
        "decision",
        "why_current_plan_meets_highest_reasonable_standard",
    }
    def _blank(value: Any) -> bool:
        return value is None or value == "" or value == []

    missing_high_standard = [
        name
        for name in sorted(required_high_standard_fields)
        if name not in high_standard or _blank(high_standard.get(name))
    ]
    if missing_high_standard:
        raise RouterError(f"node high-standard recheck missing fields: {', '.join(missing_high_standard)}")
    if str(high_standard.get("decision")) != "proceed":
        raise RouterError("node acceptance can proceed only after high_standard_recheck.decision=proceed")
    if high_standard.get("controller_can_downgrade_standard") is True:
        raise RouterError("Controller cannot downgrade node standards")
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    payload_leaf_gate = payload.get("leaf_readiness_gate") if isinstance(payload.get("leaf_readiness_gate"), dict) else None
    if payload_leaf_gate is not None:
        leaf_readiness_gate = dict(payload_leaf_gate)
    elif child_ids:
        leaf_readiness_gate = {
            "status": "not_applicable_parent",
            "reason": "Parent/module nodes are composition boundaries and cannot receive worker packets directly.",
        }
    else:
        leaf_readiness_gate = {
            "status": "pass",
            "legacy_inferred_from_reviewed_node_plan": True,
            "single_outcome": True,
            "worker_executable_without_replanning": True,
            "proof_defined": bool(experiment_plan),
            "dependency_boundary_defined": True,
            "failure_isolation_defined": True,
        }
    plan = {
        "schema_version": "flowpilot.node_acceptance_plan.v1",
        "run_id": run_state["run_id"],
        "route_id": active_route_id,
        "route_version": route_version,
        "node_id": active_node_id,
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "route_flow": project_relative(project_root, _active_route_path(run_root, frontier)),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "prior_path_context_review": prior_review,
        "node_structure": {
            "node_kind": _node_kind(node),
            "has_children": bool(child_ids),
            "child_node_ids": child_ids,
            "parent_backward_replay_required": bool(child_ids),
            "semantic_importance_used_to_trigger_review": False,
        },
        "leaf_readiness_gate": leaf_readiness_gate,
        "node_requirements": node_requirements,
        "experiment_plan": experiment_plan,
        "high_standard_recheck": {
            "ideal_outcome": high_standard.get("ideal_outcome"),
            "unacceptable_outcomes": high_standard.get("unacceptable_outcomes"),
            "higher_standard_opportunities": high_standard.get("higher_standard_opportunities"),
            "semantic_downgrade_risks": high_standard.get("semantic_downgrade_risks"),
            "decision": "proceed",
            "why_current_plan_meets_highest_reasonable_standard": high_standard.get("why_current_plan_meets_highest_reasonable_standard"),
            "controller_can_downgrade_standard": False,
        },
        "advance_gate": {
            "required_before_chunk_execution": True,
            "required_before_node_checkpoint": True,
            "reviewer_or_officer_direct_check_required": True,
        },
        "written_by_role": "project_manager",
        "source_event": source_event,
    }
    for optional_field in [
        "controller_summary_used_as_evidence",
        "identity",
        "node_title",
        "node_objective",
        "product_behavior_model_segment",
        "proof_obligations",
        "recheck_criteria",
        "repair_context",
        "fixtures_and_evidence_paths",
        "forbidden_low_standard_outcomes",
        "minimum_sufficient_complexity_review",
        "inherited_gate_obligations",
        "skill_standard_projection",
        "active_child_skill_bindings",
        "work_packet_projection",
        "result_matrix_requirements",
    ]:
        if optional_field in payload:
            plan[optional_field] = payload.get(optional_field)
    write_json(_active_node_acceptance_plan_path(run_root, frontier), plan)
    _update_display_plan_current_node(
        project_root,
        run_root,
        run_state,
        node_id=str(frontier["active_node_id"]),
        node_title=str(node.get("title") or node.get("label") or frontier["active_node_id"]),
        checklist=[
            {
                "id": str(item.get("requirement_id") or f"requirement-{index:03d}"),
                "label": str(item.get("acceptance_statement") or item.get("label") or item.get("requirement_id") or f"Requirement {index}"),
                "status": "pending",
            }
            for index, item in enumerate(node_requirements, start=1)
            if isinstance(item, dict)
        ],
        source_event=source_event,
    )


def _write_pm_revised_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    if not run_state["flags"].get("node_acceptance_plan_review_blocked"):
        raise RouterError("same-node node acceptance-plan repair requires active node_acceptance_plan_review_blocked flag")
    frontier = _active_frontier(run_root)
    node_root = _active_node_root(run_root, frontier)
    block_path = node_root / "reviews" / "node_acceptance_plan_block.json"
    if not block_path.exists():
        raise RouterError("same-node node acceptance-plan repair requires reviewer block report")
    _write_node_acceptance_plan(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_revises_node_acceptance_plan",
    )
    revised_plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    repair_record_path = node_root / "repairs" / "node_acceptance_plan_revision.json"
    write_json(
        repair_record_path,
        {
            "schema_version": "flowpilot.node_acceptance_plan_revision.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "repair_scope": "same_node_plan_revision",
            "source_block_path": project_relative(project_root, block_path),
            "revised_plan_path": project_relative(project_root, revised_plan_path),
            "stale_blocked_plan_is_context_only": True,
            "reviewer_recheck_required": True,
            "recorded_at": utc_now(),
            "recorded_by": "project_manager",
        },
    )
    run_state["flags"]["node_acceptance_plan_review_blocked"] = False
    run_state["flags"]["node_acceptance_plan_reviewer_passed"] = False
    run_state["flags"]["reviewer_node_acceptance_plan_card_delivered"] = False


def _write_parent_backward_targets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    frontier = _active_frontier(run_root)
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    active_node_id = str(frontier["active_node_id"])
    node_root = _active_node_root(run_root, frontier)
    targets = [
        {
            "parent_node_id": active_node_id,
            "child_node_ids": child_ids,
            "parent_backward_replay_path": project_relative(project_root, node_root / "parent_backward_replay.json"),
            "status": "not_started" if child_ids else "not_required",
            "pm_segment_decision": "not_reviewed" if child_ids else "not_required",
            "latest_repair_requires_rerun": False,
            "latest_replay_route_version": route_version,
        }
    ] if child_ids else []
    record = {
        "schema_version": "flowpilot.parent_backward_targets.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "pm_owned": True,
        "status": "current",
        "built_from_flow_path": project_relative(project_root, _active_route_path(run_root, frontier)),
        "built_at": utc_now(),
        "trigger_rule": {
            "structural_trigger": "any_effective_route_node_with_children",
            "semantic_importance_classification_required": False,
            "leaf_nodes_exempt_from_parent_backward_replay": True,
        },
        "targets": targets,
        "coverage": {
            "parent_targets_total": len(targets),
            "parent_targets_with_replay_passed": 0,
            "parent_targets_with_pm_decision": 0,
            "all_required_parent_replays_passed": not child_ids,
        },
        "written_by_role": "project_manager",
    }
    write_json(run_root / "routes" / route_id / "parent_backward_targets.json", record)


def _write_parent_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    frontier = _active_frontier(run_root)
    if not _active_node_has_children(run_root, frontier):
        raise RouterError("parent backward replay is required only for active nodes with children")
    targets_path = run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if not targets_path.exists():
        raise RouterError("parent backward replay requires parent_backward_targets.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("parent backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("parent backward replay must explicitly pass")
    active_node_id = str(frontier["active_node_id"])
    replay = {
        "schema_version": "flowpilot.parent_backward_replay.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": active_node_id,
        "pm_owned": True,
        "status": "passed",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "parent_backward_targets": project_relative(project_root, targets_path),
            "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
        },
        "reviewer_report": {
            "reviewer_role": "human_like_reviewer",
            "neutral_observation_written": bool(payload.get("neutral_observation_written", True)),
            "independent_probe_done": bool(payload.get("independent_probe_done", True)),
            "child_evidence_replayed": bool(payload.get("child_evidence_replayed", True)),
            "children_compose_into_parent_goal": True,
            "blocking_findings": [],
            "approval_valid": True,
        },
        "closure_gate": {
            "required_before_parent_checkpoint": True,
            "reviewer_passed": True,
            "unresolved_blocking_findings": 0,
            "parent_closure_allowed": False,
        },
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "parent_backward_replay.json", replay)


def _write_parent_segment_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("parent segment decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="parent segment decision")
    frontier = _active_frontier(run_root)
    replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
    if not replay_path.exists():
        raise RouterError("parent segment decision requires parent_backward_replay.json")
    decision = str(payload.get("decision") or "continue")
    if decision not in PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported parent segment decision: {decision}")
    record = {
        "schema_version": "flowpilot.parent_segment_decision.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": str(frontier["active_node_id"]),
        "decision_owner": "project_manager",
        "decision": decision,
        "route_mutation_required": decision != "continue",
        "same_parent_replay_rerun_required": decision != "continue",
        "prior_path_context_review": prior_review,
        "source_paths": {
            "parent_backward_replay": project_relative(project_root, replay_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "pm_parent_segment_decision.json", record)
    if decision != "continue":
        repair_node_id = str(payload.get("repair_node_id") or f"{frontier['active_node_id']}-repair-{int(frontier.get('route_version') or 1) + 1}")
        _write_route_mutation(
            project_root,
            run_root,
            run_state,
            {
                "route_id": frontier["active_route_id"],
                "repair_node_id": repair_node_id,
                "reason": f"parent_segment_decision:{decision}",
                "stale_evidence": [project_relative(project_root, replay_path)],
                "superseded_nodes": payload.get("superseded_nodes") or [],
                "repair_return_to_node_id": payload.get("repair_return_to_node_id") or payload.get("return_to_node_id"),
                "prior_path_context_review": payload.get("prior_path_context_review"),
            },
        )
    return decision


def _write_pm_research_absorption(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    reviewer_report_path = run_root / "research" / "research_reviewer_report.json"
    audit_path = run_root / "research" / "research_packet_review_audit.json"
    if not reviewer_report_path.exists():
        raise RouterError("PM can absorb research only after reviewer research report exists")
    if not audit_path.exists():
        raise RouterError("PM can absorb research only after packet-group reviewer runtime audit exists")
    audit = read_json(audit_path)
    if audit.get("passed") is not True:
        raise RouterError("PM can absorb research only after packet-group reviewer runtime audit passed")
    packet_ledger_path = run_root / "packet_ledger.json"
    if not packet_ledger_path.exists():
        raise RouterError("PM research absorption requires packet_ledger.json")
    absorption_path = run_root / "research" / "pm_research_absorption.json"
    write_json(
        absorption_path,
        {
            "schema_version": "flowpilot.pm_research_absorption.v1",
            "run_id": run_state["run_id"],
            "absorbed_by_role": "project_manager",
            "research_reviewer_report_path": project_relative(project_root, reviewer_report_path),
            "research_reviewer_report_hash": hashlib.sha256(reviewer_report_path.read_bytes()).hexdigest(),
            "packet_group_reviewer_audit_path": project_relative(project_root, audit_path),
            "packet_group_reviewer_audit_hash": hashlib.sha256(audit_path.read_bytes()).hexdigest(),
            "packet_ledger_path": project_relative(project_root, packet_ledger_path),
            "packet_ledger_hash": hashlib.sha256(packet_ledger_path.read_bytes()).hexdigest(),
            "packet_group_audit_passed": True,
            "absorbed_at": utc_now(),
        },
    )


def _validate_current_node_packet_envelope(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    envelope: dict[str, Any],
    envelope_path: Path,
    frontier: dict[str, Any],
    plan: dict[str, Any],
) -> dict[str, Any]:
    active_bindings = _active_child_skill_bindings_from_plan(plan)
    active_binding_source_paths = _active_child_skill_source_paths(active_bindings)
    active_node = frontier.get("active_node_id")
    if active_node and envelope.get("node_id") != active_node:
        raise RouterError(
            f"packet node_id {envelope.get('node_id')!r} does not match frontier active_node_id {active_node!r}"
        )
    route_version = int(frontier.get("route_version") or 0)
    packet_route_version = envelope.get("metadata", {}).get("route_version")
    if packet_route_version is None:
        raise RouterError("current-node packet metadata.route_version is required")
    if int(packet_route_version) != route_version:
        raise RouterError("current-node packet route_version must match active frontier")
    if envelope.get("from_role") != "project_manager":
        raise RouterError("current-node packet must be issued by project_manager")
    if envelope.get("to_role") == "controller":
        raise RouterError("current-node packet cannot assign product work to Controller")
    if active_bindings and envelope.get("to_role") in {"worker_a", "worker_b"}:
        metadata = envelope.get("metadata") if isinstance(envelope.get("metadata"), dict) else {}
        projected_ids = set(
            _metadata_binding_ids(
                metadata,
                "active_child_skill_bindings",
                "child_skill_binding_projection",
            )
        )
        expected_ids = {str(binding["binding_id"]) for binding in active_bindings}
        if not projected_ids:
            raise RouterError("current-node worker packet requires active child skill bindings in metadata")
        missing_ids = sorted(expected_ids - projected_ids)
        if missing_ids:
            raise RouterError(
                "current-node worker packet metadata is missing active child skill bindings: "
                + ", ".join(missing_ids)
            )
        if (
            metadata.get("child_skill_use_instruction_written") is not True
            and metadata.get("active_child_skill_use_instruction_written") is not True
        ):
            raise RouterError("current-node worker packet requires direct child-skill use instruction")
        allowed_paths = set(
            _metadata_string_list(
                metadata,
                "active_child_skill_source_paths_allowed",
                "allowed_child_skill_source_paths",
            )
        )
        missing_paths = sorted(set(active_binding_source_paths) - allowed_paths)
        if missing_paths:
            raise RouterError(
                "current-node worker packet metadata is missing active child skill source paths: "
                + ", ".join(missing_paths)
            )
    if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
        raise RouterError("current-node packet body must be sealed to the target role")
    return {
        "schema_version": "flowpilot.current_node_write_grant.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": route_version,
        "node_id": str(frontier["active_node_id"]),
        "packet_id": str(envelope["packet_id"]),
        "granted_to_role": str(envelope["to_role"]),
        "granted_by_role": "project_manager",
        "grant_scope": "current_node_packet_body_and_result_only",
        "packet_envelope_path": project_relative(project_root, envelope_path),
        "packet_envelope_hash": hashlib.sha256(envelope_path.read_bytes()).hexdigest(),
        "packet_body_path": str(envelope.get("body_path") or ""),
        "packet_body_hash": str(envelope.get("body_hash") or ""),
        "active_child_skill_bindings_declared": bool(active_bindings),
        "active_child_skill_source_paths": active_binding_source_paths,
        "controller_may_read_packet_body": False,
        "controller_may_write_project_artifacts": False,
        "issued_at": utc_now(),
    }


def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    if not run_state["flags"].get("node_acceptance_plan_reviewer_passed"):
        raise RouterError("current-node packet requires reviewer-passed node acceptance plan")
    frontier = _active_frontier(run_root)
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    if not plan_path.exists():
        raise RouterError("current-node packet requires node_acceptance_plan.json")
    plan = read_json(plan_path)
    active_node_definition = _active_node_definition(run_root, frontier)
    if _node_child_ids(active_node_definition):
        raise RouterError("current-node worker packet requires a leaf node; parent/module nodes must enter child subtree or parent backward replay")
    if _node_kind(active_node_definition) not in {"leaf", "repair"}:
        raise RouterError("current-node worker packet requires node_kind=leaf or repair")
    if not _is_leaf_readiness_passed(active_node_definition, plan):
        raise RouterError("current-node worker packet requires leaf_readiness_gate.status=pass")
    raw_packets = payload.get("packets")
    packet_payloads = raw_packets if isinstance(raw_packets, list) and raw_packets else [payload]
    records: list[dict[str, Any]] = []
    grants: list[dict[str, Any]] = []
    batch_id = str(payload.get("batch_id") or f"{frontier['active_node_id']}-batch-001")
    for packet_payload in packet_payloads:
        if not isinstance(packet_payload, dict):
            raise RouterError("current-node batch packet specs must be objects")
        envelope_path = _packet_envelope_path(project_root, run_state, packet_payload)
        if not envelope_path.exists():
            raise RouterError(f"current-node packet envelope is missing: {envelope_path}")
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        grants.append(_validate_current_node_packet_envelope(project_root, run_root, run_state, envelope, envelope_path, frontier, plan))
        records.append(_packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=str(envelope.get("packet_type") or "work_packet")))
    _write_parallel_packet_batch(
        project_root,
        run_root,
        run_state,
        batch_id=batch_id,
        batch_kind="current_node",
        phase="current_node_loop",
        records=records,
        node_id=str(frontier["active_node_id"]),
        join_policy="all_results_before_review",
        review_policy="batch_current_node_result_review_before_pm_completion",
        pm_absorption_required=True,
    )
    write_json(
        _active_node_packet_index_path(run_root, frontier),
        {
            "schema_version": "flowpilot.current_node_packet_batch.v1",
            "run_id": run_state["run_id"],
            "batch_id": batch_id,
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "controller_may_read_packet_body": False,
            "packets": records,
            "written_at": utc_now(),
        },
    )
    grant_path = _active_node_write_grant_path(run_root, frontier)
    write_json(
        grant_path,
        {
            "schema_version": "flowpilot.current_node_write_grants.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "batch_id": batch_id,
            "packet_id": str(grants[0]["packet_id"]),
            "granted_to_role": str(grants[0]["granted_to_role"]),
            "granted_by_role": "project_manager",
            "grant_scope": "current_node_packet_body_and_result_only",
            "packet_envelope_path": str(grants[0]["packet_envelope_path"]),
            "packet_envelope_hash": str(grants[0]["packet_envelope_hash"]),
            "packet_body_path": str(grants[0]["packet_body_path"]),
            "packet_body_hash": str(grants[0]["packet_body_hash"]),
            "active_child_skill_bindings_declared": bool(grants[0]["active_child_skill_bindings_declared"]),
            "active_child_skill_source_paths": grants[0]["active_child_skill_source_paths"],
            "grants": grants,
            "controller_may_read_packet_body": False,
            "controller_may_write_project_artifacts": False,
            "issued_at": utc_now(),
        },
    )
    run_state["flags"]["current_node_write_grant_issued"] = True
    run_state["current_node_packet_id"] = records[0]["packet_id"]
    run_state["current_node_batch_id"] = batch_id


def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    run_root = project_root / str(run_state["run_root"])
    frontier = _active_frontier(run_root)
    grant_path = _active_node_write_grant_path(run_root, frontier)
    if not run_state["flags"].get("current_node_write_grant_issued") or not grant_path.exists():
        raise RouterError("current-node worker result requires a current-node write grant")
    grant = read_json(grant_path)
    result_path = _result_envelope_path(project_root, run_state, payload)
    if not result_path.exists():
        raise RouterError(f"current-node result envelope is missing: {result_path}")
    result = packet_runtime.load_envelope(project_root, result_path)
    grant_records = grant.get("grants") if isinstance(grant.get("grants"), list) else [grant]
    grant_by_packet_id = {str(item.get("packet_id")): item for item in grant_records if isinstance(item, dict)}
    result_packet_id = str(result.get("packet_id") or "")
    expected_grant = grant_by_packet_id.get(result_packet_id)
    if expected_grant is None:
        raise RouterError("current-node result packet_id does not match current-node write grant")
    if str(result.get("completed_by_role") or "") != str(expected_grant.get("granted_to_role") or ""):
        raise RouterError("wrong role: current-node result completed_by_role does not match current-node write grant")
    if result.get("next_recipient") != "human_like_reviewer":
        raise RouterError("current-node worker result must route to human_like_reviewer")
    if result.get("completed_by_role") == "controller":
        raise RouterError("Controller-origin current-node result is invalid")
    packet_path = resolve_project_path(project_root, str(expected_grant.get("packet_envelope_path") or ""))
    packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
    agent_role_map = _agent_role_map_from_crew_ledger(run_root)
    audit = packet_runtime.validate_result_ready_for_reviewer_relay(
        project_root,
        packet_envelope=packet_envelope,
        result_envelope=result,
        agent_role_map=agent_role_map,
    )
    if not audit.get("passed"):
        raise RouterError(f"current-node result failed pre-relay packet runtime audit: {audit.get('blockers')}")
    _mark_parallel_batch_results_joined(project_root, run_root, run_state, "current_node")


def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("current-node reviewer pass must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("current-node reviewer pass must explicitly pass")
    run_root = project_root / str(run_state["run_root"])
    raw_agent_map = payload.get("agent_role_map")
    payload_agent_role_map = raw_agent_map if isinstance(raw_agent_map, dict) else None
    frontier = _active_frontier(run_root)
    audit_path = _active_node_root(run_root, frontier) / "reviews" / "current_node_packet_runtime_audit.json"
    records = _current_node_packet_records(project_root, run_state)
    _validate_packet_group_for_reviewer(
        project_root,
        run_state,
        records,
        audit_path=audit_path,
        agent_role_map=payload_agent_role_map,
    )
    _mark_parallel_batch_reviewed(
        run_root,
        "current_node",
        passed=True,
        reviewed_packet_ids=[str(record.get("packet_id")) for record in records],
    )


def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    draft_path = _current_route_draft_path(run_root)
    draft = read_json(draft_path)
    supplied_route = payload.get("route")
    route_payload = dict(supplied_route) if isinstance(supplied_route, dict) else dict(draft)
    route_payload["schema_version"] = "flowpilot.route.v1"
    route_payload["activated_from_draft_path"] = project_relative(project_root, draft_path)
    route_payload["activated_from_draft_hash"] = hashlib.sha256(draft_path.read_bytes()).hexdigest()
    route_payload["reviewed_route_activation_source"] = "flow.draft.json"
    if not route_payload.get("nodes"):
        raise RouterError("reviewed route activation requires non-empty reviewed route draft nodes")
    return route_payload, draft_path


def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _require_product_behavior_model_report(project_root, run_root)
    _require_route_process_pass(project_root, run_root)
    _require_route_product_pass(project_root, run_root)
    if not run_state["flags"].get("reviewer_route_check_passed"):
        raise RouterError("route activation requires reviewer-passed route challenge")
    route_payload, draft_path = _route_payload_from_reviewed_draft(project_root, run_root, payload)
    route_id = str(payload.get("route_id") or route_payload.get("route_id") or draft_path.parent.name or "route-001")
    route_payload["route_id"] = route_id
    route_version = int(payload.get("route_version") or route_payload.get("route_version") or 1)
    route_payload["route_version"] = route_version
    route_nodes = _iter_route_nodes(route_payload)
    first_node = route_nodes[0] if route_nodes else {}
    active_node_id = str(
        payload.get("active_node_id")
        or payload.get("node_id")
        or route_payload.get("active_node_id")
        or first_node.get("node_id")
        or first_node.get("id")
        or "node-001"
    )
    route_root = run_root / "routes" / route_id
    route_payload["active_node_id"] = active_node_id
    route_payload["source"] = "pm_activates_reviewed_route"
    route_payload["updated_at"] = utc_now()
    write_json(route_root / "flow.json", route_payload)
    frontier = {
        "schema_version": "flowpilot.execution_frontier.v1",
        "run_id": run_state["run_id"],
        "status": "current_node_loop",
        "active_route_id": route_id,
        "active_node_id": active_node_id,
        "active_path": _route_active_path(route_payload, active_node_id),
        "active_leaf_node_id": active_node_id if _node_kind(_active_node_definition_from_route(route_payload, active_node_id)) in {"leaf", "repair"} else None,
        "route_version": route_version,
        "updated_at": utc_now(),
        "source": "pm_activates_reviewed_route",
    }
    write_json(run_root / "execution_frontier.json", frontier)
    _write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=route_id,
        route_version=route_version,
        route_payload=route_payload,
        active_node_id=active_node_id,
        source_event="pm_activates_reviewed_route",
    )


def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="route mutation")
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    route_id = str(payload.get("route_id") or frontier.get("active_route_id") or "route-001")
    current_active_node_id = str(frontier.get("active_node_id") or "node-001")
    active_node_id = str(payload.get("active_node_id") or payload.get("repair_node_id") or current_active_node_id)
    repair_return_to_node_id = str(
        payload.get("repair_return_to_node_id")
        or payload.get("mainline_return_node_id")
        or payload.get("return_to_node_id")
        or ""
    ).strip()
    repair_of_node_id = str(
        payload.get("repair_of_node_id")
        or payload.get("affected_node_id")
        or payload.get("original_node_id")
        or current_active_node_id
    ).strip()
    continue_after_node_id = str(
        payload.get("continue_after_node_id")
        or payload.get("mainline_continue_node_id")
        or payload.get("replacement_continues_to_node_id")
        or ""
    ).strip()
    route_version = int(payload.get("route_version") or int(frontier.get("route_version") or 1) + 1)
    superseded_nodes = [str(item) for item in (payload.get("superseded_nodes") or [])]
    stale_evidence = [str(item) for item in (payload.get("stale_evidence") or [])]
    topology_strategy = str(
        payload.get("topology_strategy")
        or payload.get("mutation_topology")
        or payload.get("mutation_strategy")
        or ""
    ).strip()
    current_node_incapability_reason = str(
        payload.get("why_current_node_cannot_contain_repair")
        or payload.get("current_node_cannot_contain_repair_reason")
        or ""
    ).strip()
    if not topology_strategy:
        if repair_return_to_node_id:
            topology_strategy = "return_to_original"
        elif superseded_nodes:
            topology_strategy = "supersede_original"
        elif continue_after_node_id:
            topology_strategy = "branch_then_continue"
    if topology_strategy not in {"return_to_original", "supersede_original", "branch_then_continue"}:
        raise RouterError("route mutation requires topology_strategy=return_to_original, supersede_original, or branch_then_continue")
    if not repair_of_node_id:
        raise RouterError("route mutation requires repair_of_node_id")
    if topology_strategy == "return_to_original" and not repair_return_to_node_id:
        raise RouterError("return_to_original route mutation requires repair_return_to_node_id")
    if topology_strategy == "supersede_original":
        if not superseded_nodes:
            raise RouterError("supersede_original route mutation requires superseded_nodes")
        if repair_return_to_node_id:
            raise RouterError("supersede_original route mutation must not force repair_return_to_node_id")
    if topology_strategy == "branch_then_continue" and not continue_after_node_id:
        raise RouterError("branch_then_continue route mutation requires continue_after_node_id")
    route_topology = {
        "topology_strategy": topology_strategy,
        "inserted_node_id": active_node_id,
        "repair_of_node_id": repair_of_node_id,
        "repair_return_to_node_id": repair_return_to_node_id or None,
        "superseded_nodes": superseded_nodes,
        "continue_after_node_id": continue_after_node_id or None,
        "process_officer_recheck_required": True,
        "route_activation_recheck_required": True,
        "display_current_route_on_node_entry_only": True,
    }
    mutation_record = {
        "schema_version": "flowpilot.route_mutation.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "active_node_id": active_node_id,
        "reason": payload.get("reason") or "reviewer_block",
        "current_node_cannot_contain_repair_reason": current_node_incapability_reason or None,
        "stale_evidence": stale_evidence,
        "superseded_nodes": superseded_nodes,
        "prior_path_context_review": prior_review,
        "topology_strategy": topology_strategy,
        "route_topology": route_topology,
        "repair_return_policy": {
            "repair_node_id": active_node_id,
            "repair_of_node_id": repair_of_node_id,
            "repair_return_to_node_id": repair_return_to_node_id or None,
            "superseded_nodes": superseded_nodes,
            "continue_after_node_id": continue_after_node_id or None,
            "topology_strategy": topology_strategy,
            "process_officer_recheck_required": True,
            "route_activation_recheck_required": True,
        },
        "repair_restart_policy": {
            "same_scope_replay_rerun_required": True,
            "final_ledger_rebuild_required": True,
            "terminal_replay_restart_default": "restart_from_delivered_product",
        },
        "recorded_at": utc_now(),
        "recorded_by": "project_manager",
    }
    mutation_path = run_root / "routes" / route_id / "mutations.json"
    mutations = read_json_if_exists(mutation_path) or {"schema_version": "flowpilot.route_mutations.v1", "items": []}
    mutations.setdefault("items", []).append(mutation_record)
    mutations["updated_at"] = utc_now()
    write_json(mutation_path, mutations)
    route_path = run_root / "routes" / route_id / "flow.json"
    route = read_json_if_exists(route_path)
    route.setdefault("schema_version", "flowpilot.route.v1")
    route.setdefault("route_id", route_id)
    draft_route = dict(route)
    draft_route["schema_version"] = "flowpilot.route_draft.v1"
    draft_route["route_id"] = route_id
    draft_route["route_version"] = route_version
    draft_route["source"] = "pm_mutates_route_after_review_block"
    draft_route["candidate_activation_required"] = True
    draft_route["candidate_activation_status"] = "pending_route_recheck"
    draft_route["active_node_id"] = active_node_id
    draft_route["route_topology"] = route_topology
    draft_route["route_mutation_source_path"] = project_relative(project_root, mutation_path)
    draft_route["updated_at"] = utc_now()
    nodes = [
        dict(node)
        for node in draft_route.get("nodes", [])
        if isinstance(node, dict)
    ]
    for node in nodes:
        if isinstance(node, dict) and str(node.get("node_id") or node.get("id")) in superseded_nodes:
            node["status"] = "superseded"
            node["superseded_by"] = active_node_id
            node["superseded_at"] = utc_now()
    if not any(isinstance(node, dict) and str(node.get("node_id") or node.get("id")) == active_node_id for node in nodes):
        nodes.append(
            {
                "node_id": active_node_id,
                "status": "pending_activation",
                "title": str(payload.get("repair_node_title") or "Repair node"),
                "created_by_mutation": True,
                "mutation_reason": mutation_record["reason"],
                "topology_strategy": topology_strategy,
                "repair_of_node_id": repair_of_node_id,
                "repair_return_to_node_id": repair_return_to_node_id or None,
                "supersedes_node_ids": superseded_nodes,
                "continue_after_node_id": continue_after_node_id or None,
                "route_topology": route_topology,
            }
        )
    draft_route["nodes"] = nodes
    write_json(run_root / "routes" / route_id / "flow.draft.json", draft_route)
    stale_ledger_path = run_root / "evidence" / "stale_evidence_ledger.json"
    stale_ledger = read_json_if_exists(stale_ledger_path) or {"schema_version": "flowpilot.stale_evidence_ledger.v1", "items": []}
    for evidence_id in stale_evidence:
        stale_ledger.setdefault("items", []).append(
            {
                "evidence_id": evidence_id,
                "status": "stale",
                "reason": mutation_record["reason"],
                "route_version": route_version,
                "recorded_at": utc_now(),
            }
        )
    stale_ledger["updated_at"] = utc_now()
    write_json(stale_ledger_path, stale_ledger)
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "route_mutation_pending_recheck",
            "active_route_id": route_id,
            "active_node_id": current_active_node_id,
            "latest_mutation_path": project_relative(project_root, mutation_path),
            "pending_route_mutation": {
                "candidate_node_id": active_node_id,
                "candidate_route_version": route_version,
                "candidate_route_draft_path": project_relative(project_root, run_root / "routes" / route_id / "flow.draft.json"),
                "topology_strategy": topology_strategy,
                "display_current_route_on_node_entry_only": True,
            },
            "updated_at": utc_now(),
            "source": "pm_mutates_route_after_review_block",
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    _reset_route_hard_gate_approvals_for_recheck(run_state)
    run_state.setdefault("flags", {})["pm_route_skeleton_card_delivered"] = True
    run_state.setdefault("flags", {})["route_draft_written_by_pm"] = True
    _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS + ROUTE_COMPLETION_FLAGS)


def _write_material_dispatch_repair(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("material dispatch repair requires decided_by_role=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, decision, purpose="material dispatch repair")
    repair_action = str(decision.get("repair_action") or decision.get("selected_next_action") or "").strip()
    if not repair_action:
        raise RouterError("material dispatch repair requires repair_action or selected_next_action")
    block = run_state.get("material_dispatch_block")
    block_path = block.get("path") if isinstance(block, dict) else None
    repair_path = run_root / "material" / "material_dispatch_repair.json"
    write_json(
        repair_path,
        {
            "schema_version": "flowpilot.material_dispatch_repair.v1",
            "run_id": run_state["run_id"],
            "decided_by_role": "project_manager",
            "repair_action": repair_action,
            "source_block_path": block_path,
            "prior_path_context_review": prior_review,
            "recorded_at": utc_now(),
            **_role_output_envelope_record(decision),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": block_path,
        "repair_path": project_relative(project_root, repair_path),
        "repair_recorded_at": utc_now(),
        "status": "repair_ready_for_reviewer_recheck",
    }
    run_state["flags"]["material_scan_dispatch_blocked"] = False
    run_state["flags"]["reviewer_dispatch_allowed"] = False
    run_state["flags"]["reviewer_dispatch_card_delivered"] = False
    for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
        run_state["flags"][flag] = False


def _write_pm_review_block_repair(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    active_block_flag = _require_single_active_model_miss_review_block(run_state, "review-block repair")
    if active_block_flag in MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS:
        _write_material_dispatch_repair(project_root, run_root, run_state, payload)
        return
    if active_block_flag in MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS:
        _write_route_mutation(project_root, run_root, run_state, payload)
        return
    raise RouterError(f"review-block repair has no writer for active block flag {active_block_flag}")


def _write_evidence_quality_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="evidence quality package")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("evidence quality package must be PM-owned")
    if not run_state["flags"].get("node_completed_by_pm"):
        raise RouterError("evidence quality package requires PM-completed current node")
    frontier = _active_frontier(run_root)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("evidence quality package requires node completion ledger")
    evidence_items = payload.get("evidence_items")
    if evidence_items is None:
        evidence_items = []
    if not isinstance(evidence_items, list):
        raise RouterError("evidence_items must be a list")
    generated_resources = payload.get("generated_resources")
    if generated_resources is None:
        generated_resources = []
    if not isinstance(generated_resources, list):
        raise RouterError("generated_resources must be a list")
    ui_visual_required = bool(payload.get("ui_visual_evidence_required"))
    ui_visual_evidence = payload.get("ui_visual_evidence") if isinstance(payload.get("ui_visual_evidence"), dict) else {}
    if ui_visual_required:
        screenshot_paths = ui_visual_evidence.get("screenshot_paths")
        if not isinstance(screenshot_paths, list) or not screenshot_paths:
            raise RouterError("required UI/visual evidence needs screenshot_paths")
        if ui_visual_evidence.get("old_assets_reused") is True:
            raise RouterError("UI/visual evidence cannot reuse old assets as current evidence")
    unresolved_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") in {"unresolved", "blocked"}]
    stale_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") == "stale"]
    pending_resources = [
        item
        for item in generated_resources
        if isinstance(item, dict) and item.get("disposition") in {None, "", "pending", "unresolved"}
    ]
    if unresolved_evidence or stale_evidence:
        raise RouterError("evidence quality package cannot contain unresolved or stale current evidence")
    if pending_resources:
        raise RouterError("generated resources must have terminal dispositions")
    evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
    generated_resource_ledger_path = run_root / "generated_resource_ledger.json"
    quality_package_path = run_root / "quality" / "quality_package.json"
    write_json(
        evidence_ledger_path,
        {
            "schema_version": "flowpilot.evidence_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "items": evidence_items,
            "current_evidence_count": len(evidence_items),
            "stale_count": 0,
            "unresolved_count": 0,
            "controller_origin_evidence_allowed": False,
            "completion_report_only_allowed": False,
            "updated_at": utc_now(),
        },
    )
    write_json(
        generated_resource_ledger_path,
        {
            "schema_version": "flowpilot.generated_resource_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "resources": generated_resources,
            "resource_count": len(generated_resources),
            "pending_resource_count": 0,
            "unresolved_resource_count": 0,
            "old_visual_assets_may_close_current_gate": False,
            "all_resources_have_terminal_disposition": True,
            "updated_at": utc_now(),
        },
    )
    write_json(
        quality_package_path,
        {
            "schema_version": "flowpilot.quality_package.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "source_paths": {
                "evidence_ledger": project_relative(project_root, evidence_ledger_path),
                "generated_resource_ledger": project_relative(project_root, generated_resource_ledger_path),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "node_completion_ledger": project_relative(project_root, node_completion_ledger_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
                "packet_chain_audit": project_relative(project_root, run_root / "packet_chain_audit.json")
                if (run_root / "packet_chain_audit.json").exists()
                else None,
            },
            "prior_path_context_review": prior_review,
            "quality_checks": {
                "human_like_review_required": True,
                "completion_report_only_allowed": False,
                "rough_or_placeholder_completion_forbidden": True,
                "unresolved_evidence_count_zero": True,
                "unresolved_resource_count_zero": True,
            },
            "ui_visual_evidence": {
                "required": ui_visual_required,
                "status": "provided" if ui_visual_required else "not_applicable",
                "old_assets_reused": bool(ui_visual_evidence.get("old_assets_reused")),
                "screenshot_paths": ui_visual_evidence.get("screenshot_paths") or [],
                "visual_review_notes_path": ui_visual_evidence.get("visual_review_notes_path"),
            },
            "written_at": utc_now(),
        },
    )


def _root_requirement_ids(contract: dict[str, Any]) -> list[str]:
    ids = []
    for item in contract.get("root_requirements") or []:
        if isinstance(item, dict) and item.get("requirement_id"):
            ids.append(str(item["requirement_id"]))
    return ids


def _validated_root_replay(payload: dict[str, Any], required_ids: list[str]) -> list[dict[str, Any]]:
    replay = payload.get("root_contract_replay")
    if not isinstance(replay, list) or not replay:
        raise RouterError("final ledger requires root_contract_replay for every frozen root requirement")
    by_id = {str(item.get("requirement_id")): item for item in replay if isinstance(item, dict)}
    missing = [req_id for req_id in required_ids if req_id not in by_id]
    if missing:
        raise RouterError(f"final ledger missing root contract replay for: {', '.join(missing)}")
    failed = [
        req_id
        for req_id in required_ids
        if by_id[req_id].get("status") != "approved" or not by_id[req_id].get("evidence_paths")
    ]
    if failed:
        raise RouterError(f"final ledger root contract replay not approved with evidence for: {', '.join(failed)}")
    return [by_id[req_id] for req_id in required_ids]


def _build_source_of_truth_final_entries(
    project_root: Path,
    run_root: Path,
    frontier: dict[str, Any],
    route: dict[str, Any],
    mutations: dict[str, Any],
    contract: dict[str, Any],
    root_replay: list[dict[str, Any]],
    child_manifest: dict[str, Any],
    evidence_ledger: dict[str, Any],
    generated_ledger: dict[str, Any],
) -> list[dict[str, Any]]:
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    entries: list[dict[str, Any]] = []
    for replay in root_replay:
        entries.append(
            {
                "entry_id": f"root_contract:{replay['requirement_id']}",
                "route_version": route_version,
                "gate_family": "root_acceptance",
                "required_approver": "human_like_reviewer",
                "status": "approved",
                "source_of_truth_paths": replay.get("evidence_paths") or [],
                "evidence_paths": replay.get("evidence_paths") or [],
            }
        )
    for node in _effective_route_nodes(route, mutations):
        node_id = str(node["node_id"])
        node_root = run_root / "routes" / route_id / "nodes" / node_id
        entries.append(
            {
                "entry_id": f"{route_id}:{node_id}",
                "route_version": route_version,
                "node_id": node_id,
                "gate_family": "route_node",
                "required_approver": "project_manager",
                "status": "approved" if node_id in (frontier.get("completed_nodes") or []) or node_id == frontier.get("active_node_id") else "pending_review",
                "source_of_truth_paths": [
                    project_relative(project_root, path)
                    for path in (
                        node_root / "node_acceptance_plan.json",
                        node_root / "reviews" / "node_acceptance_plan_review.json",
                        node_root / "node_completion_ledger.json",
                        node_root / "parent_backward_replay.json",
                        node_root / "pm_parent_segment_decision.json",
                    )
                    if path.exists()
                ],
            }
        )
        entries[-1]["evidence_paths"] = list(entries[-1]["source_of_truth_paths"])
    for item in mutations.get("items") or []:
        if not isinstance(item, dict):
            continue
        for node_id in item.get("superseded_nodes") or []:
            entries.append(
                {
                    "entry_id": f"superseded:{node_id}",
                    "route_version": item.get("route_version", route_version),
                    "node_id": str(node_id),
                    "gate_family": "superseded_node",
                    "required_approver": "project_manager",
                    "status": "superseded_explained",
                    "source_of_truth_paths": [project_relative(project_root, run_root / "routes" / route_id / "mutations.json")],
                    "evidence_paths": [project_relative(project_root, run_root / "routes" / route_id / "mutations.json")],
                }
            )
    for skill in child_manifest.get("selected_skills") or []:
        if not isinstance(skill, dict):
            continue
        skill_name = str(skill.get("skill_name") or skill.get("name") or "child_skill")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                continue
            entries.append(
                {
                    "entry_id": f"child_skill:{skill_name}:{gate.get('gate_id') or len(entries)}",
                    "route_version": route_version,
                    "gate_family": "child_skill_gate",
                    "required_approver": gate.get("required_approver") or "project_manager",
                    "status": "approved",
                    "source_of_truth_paths": [project_relative(project_root, run_root / "child_skill_gate_manifest.json")],
                    "evidence_paths": [project_relative(project_root, run_root / "child_skill_gate_manifest.json")],
                }
            )
    for item in evidence_ledger.get("items") or []:
        if isinstance(item, dict) and item.get("evidence_id"):
            entries.append(
                {
                    "entry_id": f"evidence:{item['evidence_id']}",
                    "route_version": route_version,
                    "gate_family": "evidence_integrity",
                    "required_approver": "human_like_reviewer",
                    "status": item.get("status") or "current",
                    "source_of_truth_paths": [item.get("path")] if item.get("path") else [],
                    "evidence_paths": [item.get("path")] if item.get("path") else [],
                }
            )
    for resource in generated_ledger.get("resources") or []:
        if isinstance(resource, dict) and (resource.get("resource_id") or resource.get("path")):
            entries.append(
                {
                    "entry_id": f"generated_resource:{resource.get('resource_id') or resource.get('path')}",
                    "route_version": route_version,
                    "gate_family": "generated_resource_lineage",
                    "required_approver": "project_manager",
                    "status": resource.get("disposition") or "resolved",
                    "source_of_truth_paths": [resource.get("path")] if resource.get("path") else [],
                    "evidence_paths": [resource.get("path")] if resource.get("path") else [],
                }
            )
    if not entries:
        raise RouterError("final ledger source-of-truth scan produced no entries")
    return entries


def _write_final_route_wide_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="final route-wide ledger")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("final route-wide ledger must be PM-owned")
    required_paths = [
        run_root / "evidence" / "evidence_ledger.json",
        run_root / "generated_resource_ledger.json",
        run_root / "quality" / "quality_package.json",
        run_root / "reviews" / "evidence_quality_review.json",
        run_root / "execution_frontier.json",
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"final ledger requires evidence quality package and review: {', '.join(missing)}")
    if not run_state["flags"].get("evidence_quality_reviewer_passed"):
        raise RouterError("final ledger requires reviewer-passed evidence quality package")
    evidence_ledger = read_json(run_root / "evidence" / "evidence_ledger.json")
    generated_ledger = read_json(run_root / "generated_resource_ledger.json")
    quality_package = read_json(run_root / "quality" / "quality_package.json")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("status") != "frozen":
        raise RouterError("final ledger requires frozen root acceptance contract")
    child_manifest = read_json(run_root / "child_skill_gate_manifest.json")
    frontier = _active_frontier(run_root)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("final ledger requires node completion ledger")
    evidence_unresolved_count = int(evidence_ledger.get("unresolved_count", 0) or 0)
    payload_unresolved_count = int(payload.get("unresolved_count", 0) or 0)
    unresolved_count = max(evidence_unresolved_count, payload_unresolved_count)
    unresolved_resource_count = int(payload.get("unresolved_resource_count", generated_ledger.get("unresolved_resource_count", 0) or 0))
    pending_resource_count = int(generated_ledger.get("pending_resource_count", 0) or 0)
    unresolved_residual_risk_count = int(payload.get("unresolved_residual_risk_count", 0))
    stale_count = int(payload.get("stale_count", evidence_ledger.get("stale_count", 0) or 0))
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status["clean"]:
        first_issue = pm_suggestion_status["issues"][0]["message"] if pm_suggestion_status["issues"] else "unknown issue"
        raise RouterError(f"final ledger requires clean PM suggestion ledger: {first_issue}")
    if unresolved_count != 0:
        raise RouterError("final ledger requires unresolved_count=0")
    if unresolved_resource_count != 0:
        raise RouterError("final ledger requires unresolved_resource_count=0")
    if pending_resource_count != 0:
        raise RouterError("final ledger requires generated resources to have terminal dispositions")
    if unresolved_residual_risk_count != 0:
        raise RouterError("final ledger requires unresolved_residual_risk_count=0")
    if stale_count != 0:
        raise RouterError("final ledger cannot include stale current evidence")
    if quality_package.get("quality_checks", {}).get("completion_report_only_allowed") is not False:
        raise RouterError("final ledger forbids completion report-only closure")
    route_path = _active_route_path(run_root, frontier)
    route = read_json(route_path)
    mutations = read_json_if_exists(run_root / "routes" / route_id / "mutations.json")
    root_replay = _validated_root_replay(payload, _root_requirement_ids(contract))
    entries = _build_source_of_truth_final_entries(
        project_root,
        run_root,
        frontier,
        route,
        mutations,
        contract,
        root_replay,
        child_manifest,
        evidence_ledger,
        generated_ledger,
    )
    bad_entry_statuses = [
        str(entry.get("entry_id"))
        for entry in entries
        if entry.get("status") in {"pending", "pending_review", "blocked", "unresolved", "stale"}
    ]
    if bad_entry_statuses:
        raise RouterError(f"final ledger has unresolved source-of-truth entries: {', '.join(bad_entry_statuses)}")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
    terminal_segments = [
        {
            "segment_id": str(entry["entry_id"]),
            "source_entry_id": str(entry["entry_id"]),
            "gate_family": entry.get("gate_family"),
            "status": "not_reviewed",
            "requires_pm_segment_decision": True,
        }
        for entry in entries
    ]
    gate_decision_ledger_path = run_root / "gate_decisions" / "gate_decision_ledger.json"
    gate_decisions = list(run_state.get("gate_decisions") or [])
    ledger = {
        "schema_version": "flowpilot.final_route_wide_gate_ledger.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "clean",
        "built_from_route": route_id,
        "built_from_route_version": route_version,
        "built_at": utc_now(),
        "source_paths": {
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "active_flow": project_relative(project_root, route_path),
            "node_completion_ledger": project_relative(project_root, node_completion_ledger_path),
            "evidence_ledger": project_relative(project_root, run_root / "evidence" / "evidence_ledger.json"),
            "generated_resource_ledger": project_relative(project_root, run_root / "generated_resource_ledger.json"),
            "quality_package": project_relative(project_root, run_root / "quality" / "quality_package.json"),
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "child_skill_gate_manifest": project_relative(project_root, run_root / "child_skill_gate_manifest.json"),
            "route_mutations": project_relative(project_root, run_root / "routes" / route_id / "mutations.json")
            if (run_root / "routes" / route_id / "mutations.json").exists()
            else None,
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            "gate_decision_ledger": project_relative(project_root, gate_decision_ledger_path)
            if gate_decision_ledger_path.exists()
            else None,
            "pm_suggestion_ledger": project_relative(project_root, _pm_suggestion_ledger_path(run_root))
            if pm_suggestion_status["exists"]
            else None,
        },
        "prior_path_context_review": prior_review,
        "current_route_scanned": True,
        "effective_nodes_resolved": True,
        "gate_families": {
            "child_skill_gates_collected": True,
            "human_review_gates_collected": True,
            "parent_backward_replays_collected": True,
            "product_process_gates_collected": True,
            "generated_resource_lineage_collected": True,
            "final_completion_gates_collected": True,
            "gate_decisions_collected": True,
            "pm_suggestions_disposed": True,
        },
        "evidence_integrity": {
            "generated_resource_lineage_resolved": True,
            "stale_evidence_checked": True,
            "superseded_nodes_explained": True,
            "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True)),
            "residual_risk_triage_done": True,
            "unresolved_residual_risk_count_zero": True,
            "blocked_items_have_pm_repair_or_stop_decision": True,
        },
        "counts": {
            "effective_node_count": len(_effective_route_nodes(route, mutations)),
            "gate_count": len(entries),
            "stale_count": stale_count,
            "generated_resource_count": int(generated_ledger.get("resource_count", 0) or 0),
            "pending_resource_count": pending_resource_count,
            "unresolved_resource_count": unresolved_resource_count,
            "unresolved_residual_risk_count": unresolved_residual_risk_count,
            "unresolved_count": unresolved_count,
            "gate_decision_count": len(gate_decisions),
            "pm_suggestion_count": pm_suggestion_status["entry_count"],
            "pm_suggestion_issue_count": pm_suggestion_status["issue_count"],
        },
        "entries": entries,
        "gate_decisions": gate_decisions,
        "root_contract_replay": root_replay,
        "frozen_contract_replay": {
            "status": "replayed",
            "root_acceptance_contract_path": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "standard_scenario_pack_path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "requirement_count": len(root_replay),
            "standard_scenarios_replayed": bool(payload.get("standard_scenarios_replayed", True)),
        },
        "terminal_human_backward_replay": {
            "required": True,
            "status": "ready_for_reviewer",
            "review_map_path": project_relative(project_root, terminal_map_path),
            "report_only_allowed": False,
        },
        "completion_allowed": False,
    }
    write_json(final_ledger_path, ledger)
    write_json(
        terminal_map_path,
        {
            "schema_version": "flowpilot.terminal_human_backward_replay_map.v1",
            "run_id": run_state["run_id"],
            "route_id": route_id,
            "route_version": route_version,
            "pm_owned": True,
            "status": "ready_for_reviewer",
            "built_from_ledger_path": project_relative(project_root, final_ledger_path),
            "built_at": utc_now(),
            "replay_order": ["delivered_product", "root_acceptance", "parent_or_module_nodes", "leaf_nodes", "pm_segment_decisions", "repair_restart_policy"],
            "segments": terminal_segments,
            "coverage": {
                "effective_nodes_total": len(_effective_route_nodes(route, mutations)),
                "segments_total": len(terminal_segments),
                "segments_reviewed": 0,
                "effective_nodes_reviewed_by_human": 0,
                "root_acceptance_reviewed": False,
                "parent_nodes_reviewed": False,
                "leaf_nodes_reviewed": False,
                "every_effective_node_has_pm_segment_decision": False,
            },
            "repair_restart_policy": {
                "default_restart": "restart_from_delivered_product",
                "latest_repair_invalidates_affected_segments": True,
                "latest_repair_requires_ledger_rebuild": True,
                "latest_repair_requires_replay_rerun": True,
                "latest_repair_requires_pm_reapproval": True,
            },
            "completion_gate": {
                "reviewer_passed": False,
                "pm_segment_decisions_recorded": False,
                "repair_restart_policy_recorded": True,
                "unresolved_repair_findings": 0,
                "completion_allowed": False,
            },
        },
    )


def _write_terminal_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("terminal backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("terminal backward replay must explicitly pass")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_map_path = run_root / "terminal_human_backward_replay_map.json"
    if not final_ledger_path.exists() or not terminal_map_path.exists():
        raise RouterError("terminal backward replay requires final ledger and PM replay map")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get("pm_owned") is not True or final_ledger.get("status") != "clean":
        raise RouterError("terminal replay requires a PM-owned clean final ledger")
    if final_ledger.get("counts", {}).get("unresolved_count") != 0:
        raise RouterError("terminal replay cannot pass unless final ledger unresolved_count is zero")
    terminal_map = read_json(terminal_map_path)
    if terminal_map.get("status") != "ready_for_reviewer":
        raise RouterError("terminal replay map must be ready_for_reviewer")
    segments = terminal_map.get("segments") if isinstance(terminal_map.get("segments"), list) else []
    required_segment_ids = [
        str(segment.get("segment_id"))
        for segment in segments
        if isinstance(segment, dict) and segment.get("segment_id")
    ]
    segment_reviews = payload.get("segment_reviews")
    if not isinstance(segment_reviews, list) or not segment_reviews:
        raise RouterError("terminal backward replay requires segment_reviews for every replay-map segment")
    reviews_by_id = {
        str(item.get("segment_id")): item
        for item in segment_reviews
        if isinstance(item, dict) and item.get("segment_id")
    }
    missing_segments = [segment_id for segment_id in required_segment_ids if segment_id not in reviews_by_id]
    if missing_segments:
        raise RouterError(f"terminal backward replay missing segment reviews: {', '.join(missing_segments)}")
    failed_segments = [
        segment_id
        for segment_id in required_segment_ids
        if reviews_by_id[segment_id].get("reviewed_by_role") != "human_like_reviewer"
        or reviews_by_id[segment_id].get("passed") is not True
        or reviews_by_id[segment_id].get("pm_segment_decision") != "continue"
    ]
    if failed_segments:
        raise RouterError(f"terminal replay segments require reviewer pass and PM continue: {', '.join(failed_segments)}")
    for segment in segments:
        if isinstance(segment, dict) and segment.get("segment_id"):
            review = reviews_by_id.get(str(segment["segment_id"]))
            if review:
                segment["status"] = "passed"
                segment["review"] = review
    terminal_map["status"] = "passed"
    terminal_map.setdefault("coverage", {})
    terminal_map["coverage"].update(
        {
            "effective_nodes_reviewed_by_human": int(terminal_map["coverage"].get("effective_nodes_total", 1) or 1),
            "segments_reviewed": len(required_segment_ids),
            "root_acceptance_reviewed": True,
            "parent_nodes_reviewed": True,
            "leaf_nodes_reviewed": True,
            "every_effective_node_has_pm_segment_decision": True,
        }
    )
    terminal_map.setdefault("completion_gate", {})
    terminal_map["completion_gate"].update(
        {
            "reviewer_passed": True,
            "pm_segment_decisions_recorded": True,
            "repair_restart_policy_recorded": True,
            "unresolved_repair_findings": 0,
            "completion_allowed": True,
        }
    )
    terminal_map["reviewed_by_role"] = "human_like_reviewer"
    terminal_map["reviewed_at"] = utc_now()
    write_json(terminal_map_path, terminal_map)
    final_ledger.setdefault("terminal_human_backward_replay", {})
    final_ledger["terminal_human_backward_replay"].update(
        {
            "status": "passed",
            "review_map_path": project_relative(project_root, terminal_map_path),
            "report_only_allowed": False,
            "segments_reviewed": len(required_segment_ids),
        }
    )
    final_ledger["completion_allowed"] = True
    final_ledger["terminal_replay_review_path"] = project_relative(project_root, run_root / "reviews" / "terminal_backward_replay.json")
    final_ledger["terminal_replay_reviewed_at"] = utc_now()
    write_json(final_ledger_path, final_ledger)
    write_json(
        run_root / "reviews" / "terminal_backward_replay.json",
        {
            "schema_version": "flowpilot.terminal_backward_replay_review.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "human_like_reviewer",
            "passed": True,
            "source_paths": {
                "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
                "terminal_human_backward_replay_map": project_relative(project_root, terminal_map_path),
            },
            "segment_reviews": segment_reviews,
            "report_only_allowed": False,
            "reviewed_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_task_completion_projection(
        project_root,
        run_root,
        run_state,
        source_event="reviewer_final_backward_replay_passed",
    )


def _write_task_completion_projection(project_root: Path, run_root: Path, run_state: dict[str, Any], *, source_event: str) -> Path:
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_replay_path = run_root / "reviews" / "terminal_backward_replay.json"
    frontier_path = run_root / "execution_frontier.json"
    final_ledger = read_json(final_ledger_path)
    terminal_replay = read_json(terminal_replay_path)
    frontier = read_json(frontier_path)
    if final_ledger.get("completion_allowed") is not True:
        raise RouterError("task completion projection requires completion_allowed final ledger")
    if terminal_replay.get("passed") is not True:
        raise RouterError("task completion projection requires passed terminal backward replay")
    projection_path = _task_completion_projection_path(run_root)
    write_json(
        projection_path,
        {
            "schema_version": "flowpilot.task_completion_projection.v1",
            "run_id": run_state["run_id"],
            "task_status": "ready_for_pm_terminal_closure",
            "projection_owner": "controller",
            "completion_fact_owner": "project_manager",
            "source_event": source_event,
            "derived_from": "active_route_state_frontier_and_ledger",
            "controller_may_declare_completion": False,
            "ui_or_chat_is_display_only": True,
            "source_paths": {
                "execution_frontier": project_relative(project_root, frontier_path),
                "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
                "terminal_backward_replay": project_relative(project_root, terminal_replay_path),
                "latest_node_completion_ledger": str(frontier.get("latest_node_completion_ledger_path") or ""),
            },
            "published_at": utc_now(),
        },
    )
    run_state["flags"]["task_completion_projection_published"] = True
    return projection_path


def _write_terminal_closure_suite(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("approved_by_role", "project_manager") != "project_manager":
        raise RouterError("terminal closure must be approved_by_role=project_manager")
    decision = str(payload.get("decision") or "")
    if decision not in PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES:
        raise RouterError("terminal closure requires decision=approve_terminal_closure")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="terminal closure")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_replay_path = run_root / "reviews" / "terminal_backward_replay.json"
    task_projection_path = _task_completion_projection_path(run_root)
    continuation_path = _continuation_binding_path(run_root)
    required_paths = [
        final_ledger_path,
        terminal_replay_path,
        task_projection_path,
        run_root / "execution_frontier.json",
        run_root / "crew_ledger.json",
        continuation_path,
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"terminal closure missing lifecycle paths: {', '.join(missing)}")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get("completion_allowed") is not True:
        raise RouterError("terminal closure requires completion_allowed final ledger")
    replay = read_json(terminal_replay_path)
    if replay.get("passed") is not True:
        raise RouterError("terminal closure requires passed terminal backward replay")
    task_projection = read_json(task_projection_path)
    if task_projection.get("task_status") != "ready_for_pm_terminal_closure":
        raise RouterError("terminal closure requires task completion projection")
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status["clean"]:
        first_issue = pm_suggestion_status["issues"][0]["message"] if pm_suggestion_status["issues"] else "unknown issue"
        raise RouterError(f"terminal closure requires clean PM suggestion ledger: {first_issue}")
    unresolved_role_work = _unresolved_pm_role_work_requests(run_root, run_state)
    if unresolved_role_work:
        request_ids = ", ".join(str(item.get("request_id")) for item in unresolved_role_work[:5])
        raise RouterError(f"terminal closure requires all PM role-work requests resolved first: {request_ids}")
    if not _current_closure_state_clean(run_root):
        raise RouterError("terminal closure requires current clean evidence/resource/final ledgers")
    continuation = read_json(continuation_path)
    continuation["heartbeat_active"] = False
    continuation["closed_at"] = utc_now()
    continuation["closure_reason"] = "terminal_completion"
    write_json(continuation_path, continuation)
    closure = {
        "schema_version": "flowpilot.terminal_closure_suite.v1",
        "run_id": run_state["run_id"],
        "approved_by_role": "project_manager",
        "status": "closed",
        "closed_at": utc_now(),
        "source_paths": {
            "final_route_wide_gate_ledger": project_relative(project_root, final_ledger_path),
            "terminal_backward_replay": project_relative(project_root, terminal_replay_path),
            "task_completion_projection": project_relative(project_root, task_projection_path),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
            "continuation_binding": project_relative(project_root, continuation_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            "pm_suggestion_ledger": project_relative(project_root, _pm_suggestion_ledger_path(run_root))
            if pm_suggestion_status["exists"]
            else None,
        },
        "decision": decision,
        "prior_path_context_review": prior_review,
        "pm_suggestion_ledger_review": {
            "entry_count": pm_suggestion_status["entry_count"],
            "issue_count": pm_suggestion_status["issue_count"],
            "clean": pm_suggestion_status["clean"],
        },
        "lifecycle": {
            "heartbeat_active": False,
            "manual_resume_notice_required": False,
            "terminal_completion_notice_recorded": True,
            "crew_memory_archived": True,
        },
        "final_report": payload.get("final_report") or {},
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "closure" / "terminal_closure_suite.json", closure)
    run_state["status"] = "closed"
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    run_state.setdefault("flags", {})["terminal_closure_approved"] = True
    frontier = _active_frontier(run_root)
    frontier["status"] = "closed"
    frontier["phase"] = "terminal"
    frontier["terminal"] = True
    frontier["terminal_event"] = "pm_approves_terminal_closure"
    frontier["closed_at"] = utc_now()
    frontier["source"] = "pm_approves_terminal_closure"
    write_json(run_root / "execution_frontier.json", frontier)
    reconciliation = _reconcile_terminal_lifecycle_authorities(
        project_root,
        run_root,
        run_state,
        mode="closed",
        event="pm_approves_terminal_closure",
    )
    write_json(
        _lifecycle_record_path(run_root),
        {
            "schema_version": "flowpilot.run_lifecycle.v1",
            "run_id": run_state.get("run_id"),
            "status": "closed",
            "request_event": "pm_approves_terminal_closure",
            "reason": "terminal_completion",
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "reconciliation": reconciliation,
            "closed_at": closure["closed_at"],
        },
    )
    append_history(
        run_state,
        "run_closed",
        {"event": "pm_approves_terminal_closure", "lifecycle_path": project_relative(project_root, _lifecycle_record_path(run_root))},
    )
    _sync_current_and_index_status(project_root, run_state)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event="pm_approves_terminal_closure")


def _write_node_completion_ledger(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    frontier: dict[str, Any],
    *,
    completed_node_id: str,
    completed_nodes: list[str],
    next_node_id: str | None,
    source_event: str = "pm_completes_current_node_from_reviewed_result",
) -> Path:
    active_node_is_parent = _active_node_has_children(run_root, frontier)
    packet_envelope: dict[str, Any] = {}
    result_envelope: dict[str, Any] = {}
    packet_envelope_path: Path | None = None
    result_envelope_path: Path | None = None
    if not active_node_is_parent:
        packet_envelope, packet_envelope_path = _current_node_packet_context(project_root, run_state)
        result_envelope, result_envelope_path = _current_node_result_context(project_root, run_state)
    audit_path = _active_node_root(run_root, frontier) / "reviews" / "current_node_packet_runtime_audit.json"
    ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    source_paths = {
        "execution_frontier_before_update": project_relative(project_root, run_root / "execution_frontier.json"),
        "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
    }
    if packet_envelope_path and result_envelope_path:
        source_paths.update(
            {
                "current_node_write_grant": project_relative(project_root, _active_node_write_grant_path(run_root, frontier)),
                "packet_envelope": project_relative(project_root, packet_envelope_path),
                "result_envelope": project_relative(project_root, result_envelope_path),
                "current_node_packet_runtime_audit": project_relative(project_root, audit_path),
            }
        )
    if active_node_is_parent:
        source_paths.update(
            {
                "parent_backward_replay": project_relative(
                    project_root,
                    _active_node_root(run_root, frontier) / "parent_backward_replay.json",
                ),
                "pm_parent_segment_decision": project_relative(
                    project_root,
                    _active_node_root(run_root, frontier) / "pm_parent_segment_decision.json",
                ),
            }
        )
    write_json(
        ledger_path,
        {
            "schema_version": "flowpilot.node_completion_ledger.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": completed_node_id,
            "completed_by_role": "project_manager",
            "reviewer_result_passed": True,
            "worker_result_packet_id": str(result_envelope.get("packet_id") or ""),
            "worker_result_completed_by_role": str(result_envelope.get("completed_by_role") or ""),
            "current_node_packet_id": str(packet_envelope.get("packet_id") or ""),
            "completion_source_event": source_event,
            "parent_backward_replay_completion": active_node_is_parent,
            "completed_nodes_after_update": completed_nodes,
            "next_node_id": next_node_id,
            "flowpilot_completable_work_closed": True,
            "human_inspection_notes_belong_in_final_report": True,
            "source_paths": source_paths,
            "completed_at": utc_now(),
        },
    )
    run_state["flags"]["node_completion_ledger_updated"] = True
    return ledger_path


def _mark_frontier_node_completed(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str = "pm_completes_current_node_from_reviewed_result",
) -> None:
    frontier = _active_frontier(run_root)
    active_node_id = str(payload.get("node_id") or frontier.get("active_node_id") or "node-001")
    if active_node_id != str(frontier.get("active_node_id")):
        raise RouterError("completed node_id must match active frontier")
    if _active_node_has_children(run_root, frontier):
        replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
        decision_path = _active_node_root(run_root, frontier) / "pm_parent_segment_decision.json"
        missing = [project_relative(project_root, path) for path in (replay_path, decision_path) if not path.exists()]
        if missing:
            raise RouterError(f"parent node completion requires backward replay and PM segment decision: {', '.join(missing)}")
        if not run_state["flags"].get("parent_backward_replay_passed"):
            raise RouterError("parent node completion requires reviewer-passed parent backward replay")
        if not run_state["flags"].get("parent_segment_decision_recorded"):
            raise RouterError("parent node completion requires PM parent segment decision")
        decision = read_json(decision_path)
        if decision.get("decision") != "continue":
            raise RouterError("parent node completion requires PM parent segment decision=continue")
    completed = list(frontier.get("completed_nodes") or [])
    if active_node_id not in completed:
        completed.append(active_node_id)
    route = read_json_if_exists(_active_route_path(run_root, frontier))
    mutations = read_json_if_exists(run_root / "routes" / str(frontier["active_route_id"]) / "mutations.json")
    next_node_id = _next_effective_node_id(route, mutations, completed, active_node_id)
    completion_ledger_path = _write_node_completion_ledger(
        project_root,
        run_root,
        run_state,
        frontier,
        completed_node_id=active_node_id,
        completed_nodes=completed,
        next_node_id=next_node_id,
        source_event=source_event,
    )
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "current_node_loop" if next_node_id else "node_completed_by_pm",
            "active_node_id": next_node_id or active_node_id,
            "active_path": _route_active_path(route, next_node_id or active_node_id) if route else frontier.get("active_path", []),
            "active_leaf_node_id": (
                next_node_id
                if next_node_id and route and _node_kind(_active_node_definition_from_route(route, next_node_id)) in {"leaf", "repair"}
                else None
            ),
            "completed_nodes": completed,
            "latest_node_completion_ledger_path": project_relative(project_root, completion_ledger_path),
            "updated_at": utc_now(),
            "source": source_event,
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    if next_node_id:
        _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    if route:
        _write_display_plan_from_route(
            project_root,
            run_root,
            run_state,
            route_id=str(frontier["active_route_id"]),
            route_version=int(frontier.get("route_version") or 0),
            route_payload=route,
            active_node_id=next_node_id,
            source_event=source_event,
        )


def apply_bootloader_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_bootstrap_state(project_root, create_if_missing=False)
    pending = _ensure_pending(state, action_type)
    payload = payload or {}
    result_extra: dict[str, Any] = {}

    if action_type == "load_router":
        _set_boot_flag(project_root, state, "router_loaded", "bootloader_router_loaded")
        return {"ok": True, "applied": action_type}

    action_meta = next((item for item in BOOT_ACTIONS if item["action_type"] == action_type), None)
    if action_meta is None:
        raise RouterError(f"unknown bootloader action: {action_type}")
    flag = str(action_meta["flag"])

    if action_type == "ask_startup_questions":
        state["startup_state"] = "awaiting_answers_stopped"
        state["flags"]["startup_state_written_awaiting_answers"] = True
        state["flags"]["dialog_stopped_for_answers"] = True
    elif action_type == "write_startup_awaiting_answers_state":
        state["startup_state"] = "awaiting_answers"
    elif action_type == "stop_for_startup_answers":
        state["startup_state"] = "awaiting_answers_stopped"
    elif action_type == "record_startup_answers":
        startup_answers = _validate_startup_answers(payload)
        state["startup_answers"] = startup_answers
        interpretation = _validate_startup_answer_interpretation(payload, startup_answers)
        if interpretation:
            state["startup_answer_interpretation"] = interpretation
        else:
            state["startup_answer_interpretation"] = None
        state["startup_state"] = "answers_complete"
    elif action_type == "emit_startup_banner":
        banner = _startup_banner_display()
        confirmation = _display_confirmation_for_action(payload, pending)
        banner["dialog_display_confirmation"] = confirmation
        state["startup_banner_path"] = banner["display_path"]
        state["startup_banner_display"] = banner
        state["startup_banner_dialog_display_confirmation"] = confirmation
        result_extra.update(banner)
    elif action_type == "create_run_shell":
        run_id = str(payload.get("run_id") or state.get("run_id") or _create_run_id())
        run_root = project_root / ".flowpilot" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        state["run_id"] = run_id
        state["run_root"] = project_relative(project_root, run_root)
        write_json(
            run_root / "run.json",
            {
                "schema_version": "flowpilot.run.v1",
                "run_id": run_id,
                "created_at": utc_now(),
                "startup_model": "prompt_isolated_router",
                "legacy_backup_required": True,
            },
        )
    elif action_type == "write_current_pointer":
        if not state.get("run_id") or not state.get("run_root"):
            raise RouterError("cannot write current pointer before run shell exists")
        write_json(
            project_root / ".flowpilot" / "current.json",
            {
                "schema_version": "flowpilot.current.v1",
                "current_run_id": state["run_id"],
                "current_run_root": state["run_root"],
                "startup_bootstrap_path": project_relative(project_root, bootstrap_state_path(project_root, state)),
                "status": "running",
                "updated_at": utc_now(),
            },
        )
    elif action_type == "update_run_index":
        if not state.get("run_id") or not state.get("run_root"):
            raise RouterError("cannot update index before run shell exists")
        index_path = project_root / ".flowpilot" / "index.json"
        index = read_json_if_exists(index_path) or {"schema_version": "flowpilot.index.v1", "runs": []}
        runs = index.setdefault("runs", [])
        if not any(isinstance(item, dict) and item.get("run_id") == state["run_id"] for item in runs):
            runs.append({"run_id": state["run_id"], "run_root": state["run_root"], "created_at": utc_now(), "status": "running"})
        index["current_run_id"] = state["run_id"]
        index["updated_at"] = utc_now()
        write_json(index_path, index)
    elif action_type == "copy_runtime_kit":
        run_root = project_root / str(state["run_root"])
        source = runtime_kit_source()
        target = run_root / "runtime_kit"
        try:
            target.resolve().relative_to(run_root.resolve())
        except ValueError as exc:
            raise RouterError(f"runtime kit target outside run root: {target}") from exc
        if target.name != "runtime_kit":
            raise RouterError(f"refusing to replace unexpected runtime kit target: {target}")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    elif action_type == "fill_runtime_placeholders":
        run_root = project_root / str(state["run_root"])
        interpretation = state.get("startup_answer_interpretation") if isinstance(state.get("startup_answer_interpretation"), dict) else None
        interpretation_path = run_root / "startup_answer_interpretation.json"
        if interpretation:
            write_json(interpretation_path, interpretation)
        write_json(
            run_root / "startup_answers.json",
            {
                "schema_version": "flowpilot.startup_answers.v1",
                "run_id": state["run_id"],
                "answers": state.get("startup_answers") or {},
                "startup_answer_interpretation_path": project_relative(project_root, interpretation_path) if interpretation else None,
                "recorded_at": utc_now(),
            },
        )
    elif action_type == "initialize_mailbox":
        run_root = project_root / str(state["run_root"])
        for rel in (
            "mailbox/system_cards",
            "mailbox/inbox",
            "mailbox/outbox",
            "mailbox/outbox/card_acks",
            "runtime_receipts/card_reads",
            "runtime_receipts/role_io_protocol",
            "packets",
        ):
            (run_root / rel).mkdir(parents=True, exist_ok=True)
        write_json(run_root / "packet_ledger.json", _create_empty_packet_ledger(project_root, str(state["run_id"]), run_root))
        write_json(run_root / "prompt_delivery_ledger.json", {"schema_version": "flowpilot.prompt_delivery_ledger.v1", "run_id": state["run_id"], "deliveries": []})
        write_json(_card_ledger_path(run_root), _empty_card_ledger(str(state["run_id"])))
        write_json(_return_event_ledger_path(run_root), _empty_return_event_ledger(str(state["run_id"])))
        write_json(_role_io_protocol_ledger_path(run_root), _empty_role_io_protocol_ledger(str(state["run_id"])))
    elif action_type == "record_user_request":
        run_root = project_root / str(state["run_root"])
        user_request = _validate_user_request(payload)
        user_request_record = {
            "schema_version": "flowpilot.user_request.v1",
            "run_id": state["run_id"],
            "user_request": user_request,
            "recorded_at": utc_now(),
        }
        write_json(run_root / "user_request.json", user_request_record)
        state["user_request"] = user_request
        state["user_request_path"] = project_relative(project_root, run_root / "user_request.json")
    elif action_type == "write_user_intake":
        run_root = project_root / str(state["run_root"])
        user_request = state.get("user_request")
        if not isinstance(user_request, dict):
            raise RouterError("cannot write user_intake before record_user_request")
        user_intake = packet_runtime.create_user_intake_packet(
            project_root,
            run_id=str(state["run_id"]),
            packet_id="user_intake",
            node_id="startup",
            body_text=json.dumps(
                {
                    "user_request": user_request,
                    "user_request_path": state.get("user_request_path"),
                    "startup_answers": state.get("startup_answers") or {},
                    "startup_answers_path": project_relative(project_root, run_root / "startup_answers.json"),
                    "startup_answer_interpretation_path": project_relative(project_root, run_root / "startup_answer_interpretation.json")
                    if isinstance(state.get("startup_answer_interpretation"), dict)
                    else None,
                },
                indent=2,
                sort_keys=True,
            ),
            startup_options=state.get("startup_answers") or {},
        )
        write_json(run_root / "mailbox" / "outbox" / "user_intake.json", user_intake)
    elif action_type == "start_role_slots":
        run_root = project_root / str(state["run_root"])
        role_slots = _normalize_role_agent_records(state, payload)
        background_mode = (state.get("startup_answers") or {}).get("background_agents")
        write_json(
            run_root / "crew_ledger.json",
            {
                "schema_version": "flowpilot.crew_ledger.v1",
                "run_id": state["run_id"],
                "background_agents_mode": background_mode,
                "role_slots": role_slots,
                "created_at": utc_now(),
            },
        )
        crew_memory_root = run_root / "crew_memory"
        crew_memory_root.mkdir(parents=True, exist_ok=True)
        for role in CREW_ROLE_KEYS:
            write_json(crew_memory_root / f"{role}.json", _create_empty_role_memory(str(state["run_id"]), role))
        _append_role_io_protocol_injections(
            project_root,
            run_root,
            str(state["run_id"]),
            role_slots,
            default_lifecycle_phase="fresh_spawn",
            resume_tick_id="manual-resume",
            source_action="start_role_slots",
        )
        write_json(
            run_root / "role_core_prompt_delivery.json",
            _role_core_prompt_delivery_payload(
                project_root,
                run_root,
                str(state["run_id"]),
                source_action="start_role_slots",
            ),
        )
        state.setdefault("flags", {})["role_core_prompts_injected"] = True
        append_history(
            state,
            "role_core_prompts_delivered_during_start_role_slots",
            {
                "action_type": "start_role_slots",
                "postcondition": "role_core_prompts_injected",
                "delivery_mode": "same_action_with_role_start",
            },
        )
        result_extra["coalesced_postconditions"] = ["roles_started", "role_core_prompts_injected"]
    elif action_type == "inject_role_core_prompts":
        run_root = project_root / str(state["run_root"])
        write_json(
            run_root / "role_core_prompt_delivery.json",
            _role_core_prompt_delivery_payload(
                project_root,
                run_root,
                str(state["run_id"]),
                source_action="inject_role_core_prompts",
            ),
        )
    elif action_type == "load_controller_core":
        run_root = project_root / str(state["run_root"])
        run_state = new_run_state(str(state["run_id"]), str(state["run_root"]))
        write_json(run_root / "execution_frontier.json", _create_empty_execution_frontier(str(state["run_id"])))
        _write_initial_continuation_binding(project_root, run_root, run_state)
        _refresh_route_memory(project_root, run_root, run_state, trigger="load_controller_core")
        write_json(run_state_path(run_root), run_state)
    else:
        raise RouterError(f"unimplemented action: {action_type}")

    _set_boot_flag(project_root, state, flag, str(pending["label"]), {"action_type": action_type})
    result = {"ok": True, "applied": action_type, "postcondition": flag}
    result.update(result_extra)
    return result


def _next_resume_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("resume_reentry_requested"):
        return None
    if not flags.get("resume_state_loaded"):
        resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
        return make_action(
            action_type="load_resume_state",
            actor="controller",
            label="controller_loads_resume_state_before_role_rehydration",
            summary="Controller loads current-run state, ledgers, frontier, visible plan, and crew memory before live role rehydration.",
            allowed_reads=[
                ".flowpilot/current.json",
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, run_root / "execution_frontier.json"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_root / "crew_memory"),
                project_relative(project_root, _continuation_binding_path(run_root)),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
                project_relative(project_root, _display_plan_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
                project_relative(project_root, run_state_path(run_root)),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
            ],
            extra={
                "postcondition": "resume_state_loaded",
                "controller_visibility": "state_and_envelopes_only",
                "sealed_body_reads_allowed": False,
                "chat_history_progress_inference_allowed": False,
                "wake_recorded_to_router_required": True,
                "visible_plan_restore_required": True,
                "role_rehydration_required_before_pm_resume_decision": True,
                "resume_next_recipient_from_packet_ledger": resume_next,
            },
        )
    if not flags.get("resume_roles_restored"):
        return make_action(
            action_type="rehydrate_role_agents",
            actor="controller",
            label="host_rehydrates_resume_roles_before_pm_decision",
            summary="Host restores or replaces all six live FlowPilot roles from current-run memory before PM resume decision.",
            allowed_reads=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
                project_relative(project_root, run_root / "runtime_kit" / "cards" / "roles"),
                project_relative(project_root, run_root / "crew_memory"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_root / "execution_frontier.json"),
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, _route_history_index_path(run_root)),
                project_relative(project_root, _pm_prior_path_context_path(run_root)),
                project_relative(project_root, _display_plan_path(run_root)),
            ],
            allowed_writes=[
                project_relative(project_root, run_root / "continuation" / "crew_rehydration_report.json"),
                project_relative(project_root, run_root / "crew_ledger.json"),
                project_relative(project_root, run_state_path(run_root)),
            ],
            extra={
                "postcondition": "resume_roles_restored",
                **_resume_role_rehydration_action_extra(project_root, run_root, run_state),
            },
        )
    return None


def _next_startup_heartbeat_binding_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    answers = _startup_answers_from_run(run_root)
    if not _scheduled_continuation_requested(answers):
        return None
    if run_state["flags"].get("continuation_binding_recorded") and _host_heartbeat_binding_ready(run_root, run_state):
        return None
    automation_id_hint = f"flowpilot-{run_state['run_id']}-heartbeat"
    automation_name = f"FlowPilot {run_state['run_id']} heartbeat"
    prompt = (
        f"Wake the active FlowPilot run {run_state['run_id']} in {project_root} by returning to the "
        "FlowPilot router loop. Every heartbeat wake must record heartbeat_or_manual_resume_requested "
        "before any wait or resume claim. Do not self-classify the work chain as alive from old "
        "crew or route state, and do not use wait_agent timeout as proof of liveness. The router must "
        "load the current resume state, restore the visible plan, and request six-role liveness "
        "rehydration before any PM resume decision. Any restored or replacement background role "
        "agent must be explicitly requested with the strongest available host model and highest "
        "available reasoning effort; do not rely on foreground model inheritance. Do not read "
        "sealed packet/result/report bodies."
    )
    return make_action(
        action_type="create_heartbeat_automation",
        actor="controller",
        label="host_creates_startup_heartbeat_automation",
        summary="Create the one-minute Codex heartbeat for the current run, then record its host receipt before startup fact review.",
        allowed_reads=[
            ".flowpilot/current.json",
            project_relative(project_root, run_state_path(run_root)),
            project_relative(project_root, run_root / "startup_answers.json"),
            project_relative(project_root, _continuation_binding_path(run_root)),
        ],
        allowed_writes=[
            project_relative(project_root, _continuation_binding_path(run_root)),
            project_relative(project_root, run_state_path(run_root)),
        ],
        extra={
            "postcondition": "continuation_binding_recorded",
            "requires_host_automation": True,
            "host_tool": "codex_app.automation_update",
            "automation_update_request": {
                "mode": "create",
                "kind": "heartbeat",
                "destination": "thread",
                "name": automation_name,
                "prompt": prompt,
                "rrule": "FREQ=MINUTELY;INTERVAL=1",
                "status": "ACTIVE",
            },
            "expected_payload": {
                "route_heartbeat_interval_minutes": 1,
                "host_automation_id": automation_id_hint,
                "host_automation_verified": True,
                "host_automation_proof": {
                    "source_kind": "host_receipt",
                    "run_id": run_state["run_id"],
                    "host_automation_id": automation_id_hint,
                    "route_heartbeat_interval_minutes": 1,
                    "heartbeat_bound_to_current_run": True,
                },
            },
            "payload_contract": _heartbeat_payload_contract(run_state["run_id"], automation_id_hint),
            "proof_required_before_apply": True,
        },
    )


def _next_controller_boundary_confirmation_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("controller_core_loaded"):
        return None
    if flags.get("controller_role_confirmed") and _controller_boundary_confirmation_context(project_root, run_root, run_state) is not None:
        return None
    if _legacy_pm_reset_boundary_confirmed(run_state):
        return None
    sources = _controller_boundary_sources(run_root)
    return make_action(
        action_type="confirm_controller_core_boundary",
        actor="controller",
        label="controller_role_confirmed_from_router_core",
        summary="Controller records a router-owned confirmation that controller.core is the active boundary authority.",
        allowed_reads=[
            project_relative(project_root, sources["manifest_path"]),
            project_relative(project_root, sources["controller_core_path"]),
        ],
        allowed_writes=[
            project_relative(project_root, _controller_boundary_confirmation_path(run_root)),
            project_relative(project_root, run_state_path(run_root)),
        ],
        extra={
            "postcondition": "controller_role_confirmed",
            "controller_boundary_confirmation_schema": CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
            "controller_core_card_id": "controller.core",
            "sealed_body_reads_allowed": False,
            "controller_may_create_project_evidence": False,
        },
    )


def _next_startup_mechanical_audit_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("controller_role_confirmed"):
        return None
    if flags.get("startup_mechanical_audit_written") and _startup_mechanical_audit_context(project_root, run_root, run_state):
        return None
    allowed_reads = [
        project_relative(project_root, run_root / "startup_answers.json"),
        project_relative(project_root, project_root / ".flowpilot" / "current.json"),
        project_relative(project_root, project_root / ".flowpilot" / "index.json"),
        project_relative(project_root, run_root / "crew_ledger.json"),
        project_relative(project_root, _continuation_binding_path(run_root)),
        project_relative(project_root, run_state_path(run_root)),
    ]
    boundary_path = _controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        allowed_reads.append(project_relative(project_root, boundary_path))
    return make_action(
        action_type="write_startup_mechanical_audit",
        actor="controller",
        label="controller_writes_startup_mechanical_audit",
        summary="Write the router-owned startup mechanical audit and proof before delivering the reviewer startup fact-check card.",
        allowed_reads=allowed_reads,
        allowed_writes=[
            project_relative(project_root, run_root / "startup" / "startup_mechanical_audit.json"),
            project_relative(project_root, run_root / "startup" / "startup_mechanical_audit.json.proof.json"),
            project_relative(project_root, run_state_path(run_root)),
        ],
        to_role="human_like_reviewer",
        extra={
            "postcondition": "startup_mechanical_audit_written",
            "reviewer_card_waiting_for_audit": "reviewer.startup_fact_check",
            "router_replacement_scope": "mechanical_only",
        },
    )


def _next_display_plan_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
    last_sync = run_state.get("visible_plan_sync") if isinstance(run_state.get("visible_plan_sync"), dict) else {}
    route_sign_fresh = (
        not sync_payload.get("route_sign_display_required")
        or last_sync.get("route_sign_mermaid_sha256") == sync_payload.get("route_sign_mermaid_sha256")
    )
    if last_sync.get("projection_hash") == sync_payload["projection_hash"] and route_sign_fresh:
        return None
    allowed_writes = [
        project_relative(project_root, run_state_path(run_root)),
        project_relative(project_root, _route_state_snapshot_path(run_root)),
        project_relative(project_root, run_root / "display" / "user_dialog_display_ledger.json"),
    ]
    if not sync_payload["display_plan_exists"]:
        allowed_writes.append(project_relative(project_root, _display_plan_path(run_root)))
    if sync_payload.get("route_sign_display_required"):
        allowed_writes.extend(
            [
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.mmd"),
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.md"),
                project_relative(project_root, run_root / "diagrams" / "user-flow-diagram-display.json"),
            ]
        )
    allowed_reads = [
        project_relative(project_root, project_root / ".flowpilot" / "current.json"),
        project_relative(project_root, _display_plan_path(run_root)),
        project_relative(project_root, _route_state_snapshot_path(run_root)),
        project_relative(project_root, run_state_path(run_root)),
    ]
    for raw_path in (
        sync_payload.get("route_sign_source_frontier_path"),
        sync_payload.get("route_sign_source_route_path"),
    ):
        if isinstance(raw_path, str) and raw_path:
            path = Path(raw_path)
            read_path = path if path.is_absolute() else project_root / path
            try:
                rel_path = project_relative(project_root, read_path)
            except RouterError:
                continue
            if rel_path not in allowed_reads:
                allowed_reads.append(rel_path)
    return make_action(
        action_type="sync_display_plan",
        actor="controller",
        label="controller_syncs_display_plan",
        summary="Display the route map in the user dialog, then replace the host visible plan from the run display_plan.json or clear it to a waiting-for-PM placeholder.",
        allowed_reads=allowed_reads,
        allowed_writes=allowed_writes,
        extra={
            "postcondition": "visible_plan_synced",
            **sync_payload,
        },
    )


def _next_startup_display_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("controller_role_confirmed"):
        return None
    if flags.get("startup_display_status_written"):
        return None
    route_sign = _startup_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    answers = _startup_answers_from_run(run_root)
    requested_display_surface = str(answers.get("display_surface") or "chat")
    cockpit_requested = requested_display_surface == "cockpit"
    display_gate = _user_dialog_display_gate(
        {
            "display_text": route_sign["markdown"],
            "display_text_format": "markdown_mermaid",
            "display_required": True,
            "controller_must_display_text_before_apply": True,
            "generated_files_alone_satisfy_chat_display": False,
            "controller_display_rule": "Paste this exact startup route-sign display_text in the user dialog before applying write_display_surface_status; generated files alone do not satisfy display.",
        },
        display_kind="startup_route_sign",
        display_text=route_sign["markdown"],
    )
    return make_action(
        action_type="write_display_surface_status",
        actor="controller",
        label="controller_writes_startup_display_surface_status",
        summary="Display the startup FlowPilot Route Sign Mermaid in chat, then write startup display-surface status before reviewer startup fact review.",
        allowed_reads=[
            project_relative(project_root, run_root / "startup_answers.json"),
            project_relative(project_root, run_root / "execution_frontier.json"),
        ],
        allowed_writes=[
            project_relative(project_root, run_root / "display" / "display_surface.json"),
            project_relative(project_root, run_root / "diagrams" / "current_route_sign.md"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.mmd"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram.md"),
            project_relative(project_root, run_root / "diagrams" / "user-flow-diagram-display.json"),
            project_relative(project_root, run_root / "display" / "user_dialog_display_ledger.json"),
            project_relative(project_root, run_state_path(run_root)),
        ],
        extra={
            "postcondition": "startup_display_status_written",
            **display_gate,
            "chat_display_required": route_sign["chat_display_required"],
            "route_sign_mermaid_sha256": route_sign["mermaid_sha256"],
            "requested_display_surface": requested_display_surface,
            "resolved_display_surface": "chat-fallback" if cockpit_requested else "chat-requested",
            "cockpit_probe_required_for_requested_cockpit": cockpit_requested,
            "reviewer_fallback_check_required_for_requested_cockpit": cockpit_requested,
            "fallback_is_display_only_not_product_ui_completion": True,
            "payload_contract": _display_surface_receipt_payload_contract(),
        },
    )


def _next_system_card_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    manifest = load_manifest_from_run(run_root)
    resume_waiting_for_pm = (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )
    resume_card_ids = {"controller.resume_reentry", "pm.crew_rehydration_freshness", "pm.resume_decision"}
    for entry in SYSTEM_CARD_SEQUENCE:
        if resume_waiting_for_pm and entry["card_id"] not in resume_card_ids:
            continue
        if flags.get(entry["flag"]):
            continue
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        required_all = entry.get("requires_all_flags")
        if required_all and not all(flags.get(flag) for flag in required_all):
            continue
        required_any = entry.get("requires_any_flag")
        if required_any and not any(flags.get(flag) for flag in required_any):
            continue
        if entry.get("requires_active_node_children") and not _active_node_has_children(run_root, _active_frontier(run_root)):
            continue
        to_role = _system_card_to_role(run_root, entry)
        if not run_state.get("manifest_check_requested"):
            return make_action(
                action_type="check_prompt_manifest",
                actor="controller",
                label="controller_instructed_to_check_prompt_manifest",
                summary="Controller must check prompt manifest before delivering the next system card.",
                allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_card_id": entry["card_id"], "to_role": to_role},
            )
        card = manifest_card(manifest, entry["card_id"])
        delivery_extra = {"postcondition": entry["flag"]}
        delivery_extra.update(_pm_context_action_extra(project_root, run_root, entry))
        pm_decision_contract = _pm_decision_payload_contract_for_card(project_root, run_root, entry["card_id"])
        if pm_decision_contract is not None:
            delivery_extra["payload_contract"] = pm_decision_contract
        if entry["card_id"] == "reviewer.startup_fact_check":
            delivery_extra.update(_startup_mechanical_audit_action_extra(project_root, run_root, run_state))
        resolved_entry = {**entry, "to_role": to_role}
        delivery_context = _live_card_delivery_context(project_root, run_root, run_state, resolved_entry, card)
        delivery_extra["delivery_context"] = delivery_context
        run_id = str(run_state["run_id"])
        delivery_id, delivery_attempt_id = _next_card_delivery_attempt(run_root, run_id, entry["card_id"])
        safe_delivery_id = _safe_delivery_component(delivery_attempt_id)
        card_body_path = run_root / "runtime_kit" / str(card["path"])
        manifest_path = run_root / "runtime_kit" / "manifest.json"
        if not manifest_path.exists():
            manifest_path = runtime_kit_source() / "manifest.json"
        card_hash = hashlib.sha256(card_body_path.read_bytes()).hexdigest()
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        envelope_path = run_root / "mailbox" / "system_cards" / f"{safe_delivery_id}.json"
        expected_receipt_path = run_root / "runtime_receipts" / "card_reads" / f"{safe_delivery_id}.receipt.json"
        expected_return_path = run_root / "mailbox" / "outbox" / "card_acks" / f"{safe_delivery_id}.ack.json"
        card_return_event = _card_return_event_for_card(entry["card_id"])
        target_agent_id = _active_agent_id_for_role(run_root, to_role)
        card_checkin_instruction = _card_checkin_instruction(
            project_root,
            envelope_path=project_relative(project_root, envelope_path),
            role=to_role,
            agent_id=target_agent_id,
            card_return_event=card_return_event,
            bundle=False,
        )
        expected_return_rel = project_relative(project_root, expected_return_path)
        expected_receipt_rel = project_relative(project_root, expected_receipt_path)
        direct_ack_token = _direct_router_ack_token_for_card(
            run_state,
            run_root,
            card_id=entry["card_id"],
            to_role=to_role,
            target_agent_id=target_agent_id,
            card_return_event=card_return_event,
            expected_return_path=expected_return_rel,
            expected_receipt_path=expected_receipt_rel,
            delivery_id=delivery_id,
            delivery_attempt_id=delivery_attempt_id,
            body_hash=card_hash,
        )
        direct_ack_token_hash = card_runtime.stable_json_hash(direct_ack_token)
        resume_tick_id = _latest_resume_tick_id(run_state)
        role_io_receipt = _role_io_protocol_receipt_for_agent(
            run_root,
            run_id,
            role=to_role,
            agent_id=target_agent_id,
            resume_tick_id=resume_tick_id,
        )
        if target_agent_id and role_io_receipt is None:
            return make_action(
                action_type="inject_role_io_protocol",
                actor="host",
                label=f"host_injects_role_io_protocol_for_{_safe_delivery_component(to_role)}",
                summary=(
                    f"Inject FlowPilot role I/O protocol to {to_role} before delivering "
                    f"system card {entry['card_id']}."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "crew_ledger.json"),
                    project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
                    project_relative(project_root, _role_io_protocol_receipt_dir(run_root)),
                    project_relative(project_root, run_state_path(run_root)),
                ],
                to_role=to_role,
                extra={
                    "target_agent_id": target_agent_id,
                    "resume_tick_id": resume_tick_id,
                    "protocol_schema_version": ROLE_IO_PROTOCOL_SCHEMA,
                    "protocol_hash": _role_io_protocol_hash(),
                    "required_before_card_id": entry["card_id"],
                    "controller_visibility": "role_io_protocol_envelope_only",
                    "ordinary_system_card_delivery": False,
                },
            )
        delivery_extra.update(
            {
                "delivery_mode": "envelope_only_v2",
                "resource_lifecycle": "planned_internal_action",
                "artifact_committed": False,
                "relay_allowed": False,
                "apply_required": True,
                "controller_visibility": "system_card_envelope_only",
                "sealed_body_reads_allowed": False,
                "requires_read_receipt": True,
                "open_method": "open-card",
                "card_return_event": card_return_event,
                "card_checkin_instruction": card_checkin_instruction,
                "direct_router_ack_token": direct_ack_token,
                "direct_router_ack_token_hash": direct_ack_token_hash,
                "expected_return_path": expected_return_rel,
                "expected_receipt_path": expected_receipt_rel,
                "card_envelope_path": project_relative(project_root, envelope_path),
                "delivery_id": delivery_id,
                "delivery_attempt_id": delivery_attempt_id,
                "body_path": project_relative(project_root, card_body_path),
                "body_hash": card_hash,
                "manifest_path": project_relative(project_root, manifest_path),
                "manifest_hash": manifest_hash,
                "target_agent_id": target_agent_id,
                "resume_tick_id": resume_tick_id,
                "role_io_protocol_hash": _role_io_protocol_hash(),
                "role_io_protocol_receipt_path": role_io_receipt.get("receipt_path") if isinstance(role_io_receipt, dict) else None,
                "role_io_protocol_receipt_hash": role_io_receipt.get("receipt_hash") if isinstance(role_io_receipt, dict) else None,
                "ack_report_required": True,
                "ack_submission_mode": "direct_to_router",
                "controller_ack_handoff_allowed": False,
                "read_receipt_is_mechanical_only": True,
                "planned_artifacts": {
                    "card_envelope_path": project_relative(project_root, envelope_path),
                    "expected_receipt_path": expected_receipt_rel,
                    "expected_return_path": expected_return_rel,
                },
            }
        )
        allowed_reads = [
            project_relative(project_root, run_root / "runtime_kit" / "manifest.json"),
        ]
        allowed_reads.extend(
            str(path)
            for path in delivery_context.get("source_paths", {}).values()
            if isinstance(path, str) and path
        )
        if entry["card_id"] == "reviewer.startup_fact_check":
            allowed_reads.extend(
                [
                    delivery_extra["startup_mechanical_audit_path"],
                    delivery_extra["router_owned_check_proof_path"],
                ]
            )
        return make_action(
            action_type="deliver_system_card",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver system card envelope {entry['card_id']} to {to_role}; role must open through runtime and submit {card_return_event} directly to Router.",
            allowed_reads=allowed_reads,
            allowed_writes=[
                project_relative(project_root, envelope_path),
                project_relative(project_root, expected_return_path),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, _card_ledger_path(run_root)),
                project_relative(project_root, _return_event_ledger_path(run_root)),
            ],
            card_id=entry["card_id"],
            to_role=to_role,
            extra=delivery_extra,
        )
    return None


def _system_card_bundle_candidate_actions(project_root: Path, run_state: dict[str, Any], run_root: Path) -> list[dict[str, Any]]:
    probe_state = dict(run_state)
    probe_state["flags"] = dict(run_state.get("flags") or {})
    probe_state["manifest_check_requested"] = True
    actions: list[dict[str, Any]] = []
    target_role: str | None = None
    target_agent_id: str | None = None
    resume_tick_id: str | None = None
    for _entry in SYSTEM_CARD_SEQUENCE:
        action = _next_system_card_action(project_root, probe_state, run_root)
        if not isinstance(action, dict) or action.get("action_type") != "deliver_system_card":
            break
        if action.get("payload_contract"):
            break
        role = str(action.get("to_role") or "")
        agent_id = str(action.get("target_agent_id") or "")
        tick_id = str(action.get("resume_tick_id") or "")
        if target_role is None:
            target_role = role
            target_agent_id = agent_id
            resume_tick_id = tick_id
        elif role != target_role or agent_id != target_agent_id or tick_id != resume_tick_id:
            break
        actions.append(action)
        postcondition = action.get("postcondition")
        if not isinstance(postcondition, str) or not postcondition:
            break
        probe_state["flags"][postcondition] = True
        probe_state["manifest_check_requested"] = True
    return actions if len(actions) >= 2 else []


def _next_system_card_bundle_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    actions = _system_card_bundle_candidate_actions(project_root, run_state, run_root)
    if len(actions) < 2:
        return None
    first = actions[0]
    role = str(first.get("to_role") or "")
    card_ids = [str(action.get("card_id") or "") for action in actions]
    if not run_state.get("manifest_check_requested"):
        return make_action(
            action_type="check_prompt_manifest",
            actor="controller",
            label="controller_instructed_to_check_prompt_manifest",
            summary="Controller must check prompt manifest before delivering the next same-role system-card bundle.",
            allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
            allowed_writes=[project_relative(project_root, run_state_path(run_root))],
            extra={
                "next_card_id": card_ids[0],
                "bundle_candidate": True,
                "bundle_card_ids": card_ids,
                "to_role": role,
            },
        )
    first_attempt = str(first.get("delivery_attempt_id") or card_ids[0])
    last_attempt = str(actions[-1].get("delivery_attempt_id") or card_ids[-1])
    bundle_id = f"{_safe_delivery_component(first_attempt)}--to--{_safe_delivery_component(last_attempt)}"
    bundle_envelope_path = run_root / "mailbox" / "system_card_bundles" / f"{bundle_id}.json"
    expected_return_path = run_root / "mailbox" / "outbox" / "card_bundle_acks" / f"{bundle_id}.ack.json"
    expected_receipt_paths = [str(action.get("expected_receipt_path") or "") for action in actions]
    allowed_reads: list[str] = []
    for action in actions:
        for raw_path in action.get("allowed_reads") or []:
            if isinstance(raw_path, str) and raw_path and raw_path not in allowed_reads:
                allowed_reads.append(raw_path)
    cards: list[dict[str, Any]] = []
    for action in actions:
        member = {
            "card_id": action.get("card_id"),
            "label": action.get("label"),
            "postcondition": action.get("postcondition"),
            "delivery_id": action.get("delivery_id"),
            "delivery_attempt_id": action.get("delivery_attempt_id"),
            "body_path": action.get("body_path"),
            "body_hash": action.get("body_hash"),
            "manifest_path": action.get("manifest_path"),
            "manifest_hash": action.get("manifest_hash"),
            "expected_receipt_path": action.get("expected_receipt_path"),
            "card_return_event": action.get("card_return_event"),
            "delivery_context": action.get("delivery_context"),
        }
        for key in (
            "pm_context_paths",
            "pm_prior_path_context_required_for_decision",
            "controller_history_is_evidence",
        ):
            if key in action:
                member[key] = action[key]
        cards.append(member)
    card_return_event = _card_bundle_return_event_for_role(role)
    direct_ack_token = _direct_router_ack_token_for_bundle(
        run_state,
        run_root,
        bundle_id=bundle_id,
        role=role,
        target_agent_id=str(first.get("target_agent_id") or "") or None,
        card_return_event=card_return_event,
        card_ids=card_ids,
        delivery_attempt_ids=[str(action.get("delivery_attempt_id") or "") for action in actions],
        expected_return_path=project_relative(project_root, expected_return_path),
        expected_receipt_paths=expected_receipt_paths,
    )
    direct_ack_token_hash = card_runtime.stable_json_hash(direct_ack_token)
    card_checkin_instruction = _card_checkin_instruction(
        project_root,
        envelope_path=project_relative(project_root, bundle_envelope_path),
        role=role,
        agent_id=str(first.get("target_agent_id") or "") or None,
        card_return_event=card_return_event,
        bundle=True,
    )
    return make_action(
        action_type="deliver_system_card_bundle",
        actor="controller",
        label=f"same_role_system_card_bundle_delivered_{_safe_delivery_component(card_ids[0])}_to_{_safe_delivery_component(card_ids[-1])}",
        summary=(
            f"Deliver one committed system-card bundle with {len(card_ids)} cards to {role}; "
            f"the role must open it through runtime and submit {card_return_event} directly to Router."
        ),
        allowed_reads=allowed_reads,
        allowed_writes=[
            project_relative(project_root, bundle_envelope_path),
            project_relative(project_root, expected_return_path),
            project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
            project_relative(project_root, _card_ledger_path(run_root)),
            project_relative(project_root, _return_event_ledger_path(run_root)),
        ],
        card_id=card_ids[0],
        to_role=role,
        extra={
            "card_ids": card_ids,
            "postconditions": [str(action.get("postcondition") or "") for action in actions],
            "delivery_mode": "same_role_system_card_bundle_v1",
            "resource_lifecycle": "planned_internal_action",
            "artifact_committed": False,
            "relay_allowed": False,
            "apply_required": True,
            "controller_visibility": "system_card_bundle_envelope_only",
            "sealed_body_reads_allowed": False,
            "requires_read_receipt": True,
            "open_method": "open-card-bundle",
            "card_return_event": card_return_event,
            "card_checkin_instruction": card_checkin_instruction,
            "direct_router_ack_token": direct_ack_token,
            "direct_router_ack_token_hash": direct_ack_token_hash,
            "expected_return_path": project_relative(project_root, expected_return_path),
            "expected_receipt_paths": expected_receipt_paths,
            "card_bundle_id": bundle_id,
            "card_bundle_envelope_path": project_relative(project_root, bundle_envelope_path),
            "target_agent_id": first.get("target_agent_id"),
            "resume_tick_id": first.get("resume_tick_id"),
            "role_io_protocol_hash": first.get("role_io_protocol_hash"),
            "role_io_protocol_receipt_path": first.get("role_io_protocol_receipt_path"),
            "role_io_protocol_receipt_hash": first.get("role_io_protocol_receipt_hash"),
            "ack_report_required": True,
            "ack_submission_mode": "direct_to_router",
            "controller_ack_handoff_allowed": False,
            "read_receipt_is_mechanical_only": True,
            "same_role_bundle": True,
            "manifest_batch_checked": True,
            "bundle_does_not_cross_role_or_agent": True,
            "bundle_stops_before_role_output": True,
            "cards": cards,
            "planned_artifacts": {
                "card_bundle_envelope_path": project_relative(project_root, bundle_envelope_path),
                "expected_receipt_paths": expected_receipt_paths,
                "expected_return_path": project_relative(project_root, expected_return_path),
            },
        },
    )


def _system_card_to_role(run_root: Path, entry: dict[str, Any]) -> str:
    default_role = str(entry.get("to_role") or "")
    if entry.get("card_id") == "worker.research_report":
        index_path = _research_packet_index_path(run_root)
        if index_path.exists():
            try:
                index = _load_packet_index(index_path, label="research")
            except RouterError:
                return default_role
            packets = index.get("packets")
            if isinstance(packets, list) and packets:
                to_role = str(packets[0].get("to_role") or "").strip()
                if to_role:
                    return to_role
    return default_role


def _next_mail_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    for entry in MAIL_SEQUENCE:
        if flags.get(entry["flag"]):
            continue
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="check_packet_ledger",
                actor="controller",
                label="controller_instructed_to_check_packet_ledger",
                summary="Controller must check packet ledger before delivering the next mail body.",
                allowed_reads=[project_relative(project_root, run_root / "packet_ledger.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_mail_id": entry["mail_id"], "to_role": entry["to_role"]},
            )
        return make_action(
            action_type="deliver_mail",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver mail {entry['mail_id']} to {entry['to_role']} through Controller.",
            allowed_reads=[project_relative(project_root, run_root / "mailbox" / "outbox" / f"{entry['mail_id']}.json")],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            mail_id=entry["mail_id"],
            to_role=entry["to_role"],
            extra={"postcondition": entry["flag"]},
        )
    return None


def _next_material_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if (
        flags.get("pm_material_packets_issued")
        and not flags.get("material_scan_packets_relayed")
    ):
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_material_scan_packets",
                actor="controller",
                label="material_scan_packets_relayed_after_router_direct_preflight_with_ledger_check",
                summary="Check the packet ledger and directly relay material scan packet envelopes to workers without opening bodies.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _material_scan_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="worker_a,worker_b",
                extra={
                    "postcondition": "material_scan_packets_relayed",
                    "controller_visibility": "packet_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_material_scan_packets",
            actor="controller",
            label="material_scan_packets_relayed_after_router_direct_preflight",
            summary="Directly relay material scan packet envelopes to workers without opening bodies.",
            allowed_reads=[project_relative(project_root, _material_scan_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="worker_a,worker_b",
            extra={
                "postcondition": "material_scan_packets_relayed",
                "controller_visibility": "packet_envelopes_only",
                "sealed_body_reads_allowed": False,
            },
        )
    if flags.get("worker_scan_results_returned") and not flags.get("material_scan_results_relayed_to_reviewer"):
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_material_scan_results_to_reviewer",
                actor="controller",
                label="material_scan_results_relayed_to_reviewer_with_ledger_check",
                summary="Check the packet ledger and relay material scan result envelopes to reviewer without opening result bodies.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _material_scan_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "postcondition": "material_scan_results_relayed_to_reviewer",
                    "controller_visibility": "result_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_material_scan_results_to_reviewer",
            actor="controller",
            label="material_scan_results_relayed_to_reviewer",
            summary="Relay material scan result envelopes to reviewer without opening result bodies.",
            allowed_reads=[project_relative(project_root, _material_scan_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "postcondition": "material_scan_results_relayed_to_reviewer",
                "controller_visibility": "result_envelopes_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _next_research_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if flags.get("research_capability_decision_recorded") and not flags.get("research_packet_relayed"):
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_research_packet",
                actor="controller",
                label="research_packet_relayed_to_worker_with_ledger_check",
                summary="Check the packet ledger and relay research packet envelope to worker without opening the body.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _research_packet_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role=",".join(sorted({str(record.get("to_role") or "worker_a") for record in index["packets"]})),
                extra={
                    "postcondition": "research_packet_relayed",
                    "controller_visibility": "packet_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_research_packet",
            actor="controller",
            label="research_packet_relayed_to_worker",
            summary="Relay research batch packet envelopes without opening their bodies.",
            allowed_reads=[project_relative(project_root, _research_packet_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role=",".join(sorted({str(record.get("to_role") or "worker_a") for record in index["packets"]})),
            extra={
                "postcondition": "research_packet_relayed",
                "controller_visibility": "packet_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    if flags.get("worker_research_report_returned") and not flags.get("research_result_relayed_to_reviewer"):
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_research_result_to_reviewer",
                actor="controller",
                label="research_result_relayed_to_reviewer_with_ledger_check",
                summary="Check the packet ledger and relay research result envelope to reviewer without opening the result body.",
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, _research_packet_index_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "postcondition": "research_result_relayed_to_reviewer",
                    "controller_visibility": "result_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": [record.get("packet_id") for record in index["packets"]],
                },
            )
        return make_action(
            action_type="relay_research_result_to_reviewer",
            actor="controller",
            label="research_result_relayed_to_reviewer",
            summary="Relay research result envelope to reviewer without opening the result body.",
            allowed_reads=[project_relative(project_root, _research_packet_index_path(run_root))],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "postcondition": "research_result_relayed_to_reviewer",
                "controller_visibility": "result_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _next_current_node_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    if not flags.get("current_node_packet_registered"):
        return None
    if not flags.get("current_node_packet_relayed"):
        records = _current_node_packet_records(project_root, run_state)
        frontier = _active_frontier(run_root)
        grant_path = _active_node_write_grant_path(run_root, frontier)
        grant_extra: dict[str, Any] = {}
        relay_allowed_reads = [
            project_relative(project_root, _packet_envelope_path_from_record(project_root, run_state, record))
            for record in records
        ]
        if grant_path.exists():
            relay_allowed_reads.append(project_relative(project_root, grant_path))
            grant_extra = {
                "current_node_write_grant_path": project_relative(project_root, grant_path),
                "current_node_write_grant_hash": hashlib.sha256(grant_path.read_bytes()).hexdigest(),
            }
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_current_node_packet",
                actor="controller",
                label="current_node_packet_relayed_after_router_direct_preflight_with_ledger_check",
                summary=(
                    "Check the packet ledger and relay every current-node batch packet "
                    "without opening packet bodies."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    *relay_allowed_reads,
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role=",".join(sorted({str(record.get("to_role")) for record in records})),
                extra={
                    "packet_ids": [record.get("packet_id") for record in records],
                    "postcondition": "current_node_packet_relayed",
                    "controller_visibility": "packet_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    **grant_extra,
                },
            )
        return make_action(
            action_type="relay_current_node_packet",
            actor="controller",
            label="current_node_packet_relayed_after_router_direct_preflight",
            summary="Directly relay current-node batch packet envelopes without opening their bodies.",
            allowed_reads=relay_allowed_reads,
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role=",".join(sorted({str(record.get("to_role")) for record in records})),
            extra={
                "packet_ids": [record.get("packet_id") for record in records],
                "postcondition": "current_node_packet_relayed",
                "controller_visibility": "packet_envelope_only",
                "sealed_body_reads_allowed": False,
                **grant_extra,
            },
        )
    if flags.get("current_node_worker_result_returned") and not flags.get("current_node_result_relayed_to_reviewer"):
        if not _current_node_results_complete(project_root, run_state):
            missing_roles = _current_node_missing_result_roles(project_root, run_state)
            return _expected_role_decision_wait_action(
                project_root,
                run_state,
                run_root,
                label="controller_waits_for_remaining_current_node_batch_results",
                summary="Controller must wait for every current-node batch result before relaying the batch to reviewer.",
                allowed_external_events=["worker_current_node_result_returned"],
                to_role=",".join(missing_roles) if missing_roles else "worker_a,worker_b",
                payload_contract={
                    "schema_version": PAYLOAD_CONTRACT_SCHEMA,
                    "name": "current_node_batch_result_envelope",
                    "required_fields": ["packet_id", "result_envelope_path"],
                    "batch_join_policy": "all_results_before_review",
                },
                producer_roles_override=missing_roles,
            )
        records = _current_node_packet_records(project_root, run_state)
        result_paths = [
            _result_envelope_path_from_packet_record(project_root, run_state, record)
            for record in records
        ]
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_current_node_result_to_reviewer",
                actor="controller",
                label="current_node_result_relayed_to_reviewer_with_ledger_check",
                summary=(
                    "Check the packet ledger and relay the current-node worker "
                    "batch result envelopes to reviewer without opening result bodies."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    *[project_relative(project_root, path) for path in result_paths],
                ],
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                ],
                to_role="human_like_reviewer",
                extra={
                    "packet_ids": [record.get("packet_id") for record in records],
                    "postcondition": "current_node_result_relayed_to_reviewer",
                    "controller_visibility": "result_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                },
            )
        return make_action(
            action_type="relay_current_node_result_to_reviewer",
            actor="controller",
            label="current_node_result_relayed_to_reviewer",
            summary="Relay current-node batch result envelopes to reviewer without opening result bodies.",
            allowed_reads=[project_relative(project_root, path) for path in result_paths],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            to_role="human_like_reviewer",
            extra={
                "packet_ids": [record.get("packet_id") for record in records],
                "postcondition": "current_node_result_relayed_to_reviewer",
                "controller_visibility": "result_envelope_only",
                "sealed_body_reads_allowed": False,
            },
        )
    return None


def _controller_status_packet_path_from_packet_envelope(packet_envelope_path: object) -> str | None:
    raw = str(packet_envelope_path or "").replace("\\", "/")
    suffix = "/packet_envelope.json"
    if not raw.endswith(suffix):
        return None
    return raw[: -len("packet_envelope.json")] + "controller_status_packet.json"


def _role_output_status_packet_path_for_wait(
    project_root: Path,
    run_root: Path,
    *,
    to_role: str,
    allowed_events: list[str],
    payload_contract: dict[str, Any] | None,
) -> str | None:
    if not isinstance(payload_contract, dict):
        return None
    if payload_contract.get("required_object") != "role_output_body":
        return None
    if not to_role or "," in to_role or to_role == "host":
        return None
    event_name = "_or_".join(allowed_events) if allowed_events else str(payload_contract.get("name") or "")
    path = role_output_runtime.default_role_output_status_packet_path(
        run_root,
        role=to_role,
        output_type=str(payload_contract.get("name") or "role_output"),
        event_name=event_name,
    )
    return project_relative(project_root, path)


def _next_pm_role_work_request_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    index = _load_pm_role_work_request_index(run_root, run_state)
    batch_records = _active_pm_role_work_batch_records(index)
    if batch_records:
        index_path = _pm_role_work_request_index_path(run_root)
        packet_ids = [record.get("packet_id") for record in batch_records]
        to_roles = ",".join(sorted({str(record.get("to_role") or "") for record in batch_records if record.get("to_role")}))
        if any(record.get("status") == "open" for record in batch_records):
            allowed_reads = [
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, index_path),
                *[str(record.get("packet_envelope_path")) for record in batch_records],
            ]
            if not run_state.get("ledger_check_requested"):
                return make_action(
                    action_type="relay_pm_role_work_request_packet",
                    actor="controller",
                    label="pm_role_work_request_batch_relayed_with_ledger_check",
                    summary="Check the packet ledger and relay every PM role-work request packet in the active batch without opening sealed bodies.",
                    allowed_reads=allowed_reads,
                    allowed_writes=[
                        project_relative(project_root, run_state_path(run_root)),
                        project_relative(project_root, run_root / "packet_ledger.json"),
                        project_relative(project_root, index_path),
                    ],
                    to_role=to_roles,
                    extra={
                        "batch_id": index.get("active_batch_id"),
                        "request_id": batch_records[0].get("request_id") if len(batch_records) == 1 else None,
                        "packet_id": batch_records[0].get("packet_id") if len(batch_records) == 1 else None,
                        "packet_ids": packet_ids,
                        "postcondition": "pm_role_work_request_packet_relayed",
                        "controller_visibility": "packet_envelopes_only",
                        "sealed_body_reads_allowed": False,
                        "combined_ledger_check_and_relay": True,
                        "ledger_check_receipt_required": True,
                        "pm_work_requests": project_relative(project_root, index_path),
                    },
                )
            return make_action(
                action_type="relay_pm_role_work_request_packet",
                actor="controller",
                label="pm_role_work_request_batch_relayed",
                summary="Relay every PM role-work request packet in the active batch without opening sealed bodies.",
                allowed_reads=[project_relative(project_root, index_path), *[str(record.get("packet_envelope_path")) for record in batch_records]],
                allowed_writes=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, index_path),
                ],
                to_role=to_roles,
                extra={
                    "batch_id": index.get("active_batch_id"),
                    "request_id": batch_records[0].get("request_id") if len(batch_records) == 1 else None,
                    "packet_id": batch_records[0].get("packet_id") if len(batch_records) == 1 else None,
                    "packet_ids": packet_ids,
                    "postcondition": "pm_role_work_request_packet_relayed",
                    "controller_visibility": "packet_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "pm_work_requests": project_relative(project_root, index_path),
                },
            )
        if (
            any(record.get("status") in {"packet_relayed", "result_returned"} for record in batch_records)
            and not all(record.get("status") == "result_returned" for record in batch_records)
        ):
            missing_roles = [
                str(record.get("to_role") or record.get("request_id") or "unknown")
                for record in batch_records
                if not resolve_project_path(project_root, str(record.get("result_envelope_path") or "")).exists()
            ]
            return _expected_role_decision_wait_action(
                project_root,
                run_state,
                run_root,
                label="controller_waits_for_pm_role_work_batch_results",
                summary="Controller has relayed the PM role-work batch and must wait for every target role to return a result envelope.",
                allowed_external_events=[ROLE_WORK_RESULT_RETURNED_EVENT],
                to_role=",".join(sorted(set(missing_roles))) if missing_roles else to_roles,
                payload_contract={
                    "schema_version": PAYLOAD_CONTRACT_SCHEMA,
                    "name": "role_work_result_returned_envelope",
                    "required_fields": ["request_id", "packet_id", "result_envelope_path"],
                    "batch_id": index.get("active_batch_id"),
                    "batch_join_policy": "all_results_before_pm_absorption",
                    "expected_next_recipient": "project_manager",
                },
                producer_roles_override=missing_roles,
            )
        if all(record.get("status") == "result_returned" for record in batch_records):
            allowed_reads = [
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, index_path),
                *[str(record.get("result_envelope_path")) for record in batch_records],
            ]
            if not run_state.get("ledger_check_requested"):
                return make_action(
                    action_type="relay_pm_role_work_result_to_pm",
                    actor="controller",
                    label="pm_role_work_result_batch_relayed_to_pm_with_ledger_check",
                    summary="Check the packet ledger and relay every role-work result envelope in the batch back to PM without opening sealed result bodies.",
                    allowed_reads=allowed_reads,
                    allowed_writes=[
                        project_relative(project_root, run_state_path(run_root)),
                        project_relative(project_root, run_root / "packet_ledger.json"),
                        project_relative(project_root, index_path),
                    ],
                    to_role="project_manager",
                    extra={
                        "batch_id": index.get("active_batch_id"),
                        "request_id": batch_records[0].get("request_id") if len(batch_records) == 1 else None,
                        "packet_id": batch_records[0].get("packet_id") if len(batch_records) == 1 else None,
                        "packet_ids": packet_ids,
                        "postcondition": "pm_role_work_result_relayed_to_pm",
                        "controller_visibility": "result_envelopes_only",
                        "sealed_body_reads_allowed": False,
                        "combined_ledger_check_and_relay": True,
                        "ledger_check_receipt_required": True,
                        "pm_work_requests": project_relative(project_root, index_path),
                    },
                )
            return make_action(
                action_type="relay_pm_role_work_result_to_pm",
                actor="controller",
                label="pm_role_work_result_batch_relayed_to_pm",
                summary="Relay every role-work result envelope in the batch back to PM without opening sealed result bodies.",
                allowed_reads=[project_relative(project_root, index_path), *[str(record.get("result_envelope_path")) for record in batch_records]],
                allowed_writes=[
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, index_path),
                ],
                to_role="project_manager",
                extra={
                    "batch_id": index.get("active_batch_id"),
                    "request_id": batch_records[0].get("request_id") if len(batch_records) == 1 else None,
                    "packet_id": batch_records[0].get("packet_id") if len(batch_records) == 1 else None,
                    "packet_ids": packet_ids,
                    "postcondition": "pm_role_work_result_relayed_to_pm",
                    "controller_visibility": "result_envelopes_only",
                    "sealed_body_reads_allowed": False,
                    "pm_work_requests": project_relative(project_root, index_path),
                },
            )
        if all(record.get("status") == "result_relayed_to_pm" for record in batch_records):
            return _expected_role_decision_wait_action(
                project_root,
                run_state,
                run_root,
                label="controller_waits_for_pm_role_work_batch_result_decision",
                summary="Controller relayed the full role-work result batch to PM and must wait for one PM batch disposition.",
                allowed_external_events=[PM_ROLE_WORK_RESULT_DECISION_EVENT],
                to_role="project_manager",
                payload_contract={
                    "schema_version": PAYLOAD_CONTRACT_SCHEMA,
                    "name": "pm_role_work_batch_result_decision",
                    "required_fields": ["decided_by_role", "batch_id", "decision"],
                    "allowed_values": {
                        "decided_by_role": ["project_manager"],
                        "decision": sorted(PM_ROLE_WORK_TERMINAL_DECISIONS),
                    },
                    "expected_batch_id": index.get("active_batch_id"),
                },
            )
    active = _active_pm_role_work_request(index)
    if not isinstance(active, dict):
        return None
    index_path = _pm_role_work_request_index_path(run_root)
    packet_ids = [active.get("packet_id")]
    if active.get("status") == "open":
        allowed_reads = [
            project_relative(project_root, run_root / "packet_ledger.json"),
            project_relative(project_root, index_path),
            str(active.get("packet_envelope_path")),
        ]
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_pm_role_work_request_packet",
                actor="controller",
                label="pm_role_work_request_packet_relayed_with_ledger_check",
                summary="Check the packet ledger and relay the PM role-work request packet without opening the sealed body.",
                allowed_reads=allowed_reads,
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, index_path),
                ],
                to_role=str(active.get("to_role") or ""),
                extra={
                    "request_id": active.get("request_id"),
                    "packet_id": active.get("packet_id"),
                    "postcondition": "pm_role_work_request_packet_relayed",
                    "controller_visibility": "packet_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": packet_ids,
                    "pm_work_requests": project_relative(project_root, index_path),
                },
            )
        return make_action(
            action_type="relay_pm_role_work_request_packet",
            actor="controller",
            label="pm_role_work_request_packet_relayed",
            summary="Relay the PM role-work request packet without opening the sealed body.",
            allowed_reads=[project_relative(project_root, index_path), str(active.get("packet_envelope_path"))],
            allowed_writes=[
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, index_path),
            ],
            to_role=str(active.get("to_role") or ""),
            extra={
                "request_id": active.get("request_id"),
                "packet_id": active.get("packet_id"),
                "postcondition": "pm_role_work_request_packet_relayed",
                "controller_visibility": "packet_envelope_only",
                "sealed_body_reads_allowed": False,
                "pm_work_requests": project_relative(project_root, index_path),
            },
        )
    if active.get("status") == "result_returned":
        allowed_reads = [
            project_relative(project_root, run_root / "packet_ledger.json"),
            project_relative(project_root, index_path),
            str(active.get("result_envelope_path")),
        ]
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="relay_pm_role_work_result_to_pm",
                actor="controller",
                label="pm_role_work_result_relayed_to_pm_with_ledger_check",
                summary="Check the packet ledger and relay the role-work result envelope back to PM without opening the sealed result body.",
                allowed_reads=allowed_reads,
                allowed_writes=[
                    project_relative(project_root, run_state_path(run_root)),
                    project_relative(project_root, run_root / "packet_ledger.json"),
                    project_relative(project_root, index_path),
                ],
                to_role="project_manager",
                extra={
                    "request_id": active.get("request_id"),
                    "packet_id": active.get("packet_id"),
                    "postcondition": "pm_role_work_result_relayed_to_pm",
                    "controller_visibility": "result_envelope_only",
                    "sealed_body_reads_allowed": False,
                    "combined_ledger_check_and_relay": True,
                    "ledger_check_receipt_required": True,
                    "packet_ids": packet_ids,
                    "pm_work_requests": project_relative(project_root, index_path),
                },
            )
        return make_action(
            action_type="relay_pm_role_work_result_to_pm",
            actor="controller",
            label="pm_role_work_result_relayed_to_pm",
            summary="Relay the role-work result envelope back to PM without opening the sealed result body.",
            allowed_reads=[project_relative(project_root, index_path), str(active.get("result_envelope_path"))],
            allowed_writes=[
                project_relative(project_root, run_root / "packet_ledger.json"),
                project_relative(project_root, index_path),
            ],
            to_role="project_manager",
            extra={
                "request_id": active.get("request_id"),
                "packet_id": active.get("packet_id"),
                "postcondition": "pm_role_work_result_relayed_to_pm",
                "controller_visibility": "result_envelope_only",
                "sealed_body_reads_allowed": False,
                "pm_work_requests": project_relative(project_root, index_path),
            },
        )
    if active.get("status") == "packet_relayed":
        status_packet_path = _controller_status_packet_path_from_packet_envelope(active.get("packet_envelope_path"))
        allowed_reads = [project_relative(project_root, run_state_path(run_root))]
        if status_packet_path:
            allowed_reads.append(status_packet_path)
        return _expected_role_decision_wait_action(
            project_root,
            run_state,
            run_root,
            label="controller_waits_for_role_work_result_returned",
            summary="Controller has relayed the PM role-work packet and must wait for the target role to return its result envelope.",
            allowed_external_events=[ROLE_WORK_RESULT_RETURNED_EVENT],
            to_role=str(active.get("to_role") or ""),
            allowed_reads_extra=allowed_reads,
            payload_contract={
                "schema_version": PAYLOAD_CONTRACT_SCHEMA,
                "name": "role_work_result_returned_envelope",
                "required_fields": ["request_id", "packet_id", "result_envelope_path"],
                "expected_request_id": active.get("request_id"),
                "expected_packet_id": active.get("packet_id"),
                "expected_next_recipient": "project_manager",
            },
        )
    if active.get("status") == "result_relayed_to_pm":
        return _expected_role_decision_wait_action(
            project_root,
            run_state,
            run_root,
            label="controller_waits_for_pm_role_work_result_decision",
            summary="Controller relayed the role-work result to PM and must wait for PM to absorb, cancel, or supersede it.",
            allowed_external_events=[PM_ROLE_WORK_RESULT_DECISION_EVENT],
            to_role="project_manager",
            payload_contract={
                "schema_version": PAYLOAD_CONTRACT_SCHEMA,
                "name": "pm_role_work_result_decision",
                "required_fields": ["decided_by_role", "request_id", "decision"],
                "allowed_values": {
                    "decided_by_role": ["project_manager"],
                    "decision": sorted(PM_ROLE_WORK_TERMINAL_DECISIONS),
                },
                "expected_request_id": active.get("request_id"),
            },
        )
    return None


def _next_model_miss_followup_request_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    followup = _model_miss_followup_expectation(run_state)
    if followup is None:
        return None
    index = _load_pm_role_work_request_index(run_root, run_state)
    if _active_pm_role_work_request(index) is not None:
        return None
    kind = str(followup.get("required_request_kind") or "model_miss")
    return _expected_role_decision_wait_action(
        project_root,
        run_state,
        run_root,
        label=f"pm_{kind}_triage_waits_for_generic_role_work_request",
        summary=(
            "PM chose to gather more information before repair. Controller must wait for PM to register "
            "a generic role-work request; Controller may not reopen the same model-miss decision loop."
        ),
        allowed_external_events=[PM_ROLE_WORK_REQUEST_EVENT],
        to_role="project_manager",
        payload_contract={
            "schema_version": PAYLOAD_CONTRACT_SCHEMA,
            "name": "pm_role_work_request",
            "required_fields": [
                "requested_by_role",
                "request_id",
                "to_role",
                "request_mode",
                "request_kind",
                "output_contract_id",
                "packet_body_path",
                "packet_body_hash",
            ],
            "allowed_values": {
                "requested_by_role": ["project_manager"],
                "to_role": sorted(PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES),
                "request_mode": sorted(PM_ROLE_WORK_REQUEST_MODES),
                "request_kind": sorted(PM_ROLE_WORK_REQUEST_KINDS),
            },
            "pending_followup": followup,
        },
    )


def _next_model_miss_controlled_stop_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    stop = run_state.get("model_miss_triage_controlled_stop")
    if not isinstance(stop, dict) or stop.get("status") != "waiting_for_user":
        return None
    return make_action(
        action_type="await_user_after_model_miss_stop",
        actor="controller",
        label="model_miss_triage_controlled_stop",
        summary="PM stopped the model-miss triage path for user input; Controller must wait and must not loop the same PM event.",
        allowed_reads=[project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[],
        to_role="user",
        extra={
            "requires_user": True,
            "apply_required": False,
            "model_miss_triage_controlled_stop": stop,
        },
    )


def _expected_role_decision_wait_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    label: str,
    summary: str,
    allowed_external_events: list[str],
    to_role: str,
    payload_contract: dict[str, Any] | None = None,
    allowed_reads_extra: list[str] | None = None,
    pm_work_request_channel: bool = True,
    producer_roles_override: list[str] | None = None,
) -> dict[str, Any]:
    role_output_events = list(allowed_external_events)
    role_output_status_packet_path = _role_output_status_packet_path_for_wait(
        project_root,
        run_root,
        to_role=to_role,
        allowed_events=role_output_events,
        payload_contract=payload_contract,
    )
    if role_output_status_packet_path and payload_contract is not None:
        payload_contract = dict(payload_contract)
        structural = list(payload_contract.get("structural_requirements") or [])
        structural.append(
            "Maintain role-output progress through flowpilot_runtime.py progress-output; progress is metadata-only and is not pass/fail evidence."
        )
        payload_contract["structural_requirements"] = structural
        payload_contract["progress_status"] = {
            "default_progress_required": True,
            "controller_status_packet_path": role_output_status_packet_path,
            "runtime_command": "flowpilot_runtime.py progress-output",
            "controller_visibility": "metadata_only",
            "progress_is_decision_evidence": False,
        }
    allowed_events = list(allowed_external_events)
    if pm_work_request_channel and to_role == "project_manager" and PM_ROLE_WORK_REQUEST_EVENT not in allowed_events:
        allowed_events.append(PM_ROLE_WORK_REQUEST_EVENT)
    allowed_events = _validated_external_event_names(
        allowed_events,
        context=f"await_role_decision action {label}",
    )
    if producer_roles_override is None:
        _validate_wait_event_producer_binding(
            allowed_events,
            to_role=to_role,
            context=f"await_role_decision action {label}",
        )
    else:
        producer_roles = {str(role) for role in producer_roles_override if str(role)}
        target_roles = _role_set(to_role)
        if producer_roles and not producer_roles.issubset(target_roles):
            raise RouterError(
                f"await_role_decision action {label} waits for event producer role(s) {sorted(producer_roles)} "
                f"but targets {sorted(target_roles)}"
            )
    extra: dict[str, Any] = {
        "allowed_external_events": allowed_events,
        "controller_only_mode_active": True,
        "controller_may_create_project_evidence": False,
        "expected_wait_is_not_control_blocker": True,
    }
    if producer_roles_override is not None:
        extra["expected_event_producer_roles"] = sorted({str(role) for role in producer_roles_override if str(role)})
    if pm_work_request_channel and to_role == "project_manager":
        extra["pm_work_request_channel_available"] = True
        extra["pm_role_work_request_event"] = PM_ROLE_WORK_REQUEST_EVENT
    if payload_contract is not None:
        extra["payload_contract"] = payload_contract
    if role_output_status_packet_path:
        extra["role_output_progress_status"] = {
            "controller_status_packet_path": role_output_status_packet_path,
            "default_progress_required": True,
            "runtime_command": "flowpilot_runtime.py progress-output",
            "controller_visibility": "metadata_only",
            "progress_is_decision_evidence": False,
        }
    allowed_reads = [project_relative(project_root, run_state_path(run_root))]
    if role_output_status_packet_path and role_output_status_packet_path not in allowed_reads:
        allowed_reads.append(role_output_status_packet_path)
    for item in allowed_reads_extra or []:
        if item and item not in allowed_reads:
            allowed_reads.append(item)
    return make_action(
        action_type="await_role_decision",
        actor="controller",
        label=label,
        summary=summary,
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=to_role,
        extra=extra,
    )


def _event_wait_role(event: str, meta: dict[str, str]) -> str:
    del meta
    if event.startswith("pm_"):
        return "project_manager"
    if event.startswith("reviewer_") or event.startswith("current_node_reviewer_"):
        return "human_like_reviewer"
    if event.startswith("product_officer_"):
        return "product_flowguard_officer"
    if event.startswith("process_officer_"):
        return "process_flowguard_officer"
    if event.startswith("worker_"):
        return "worker_a"
    if event.startswith("host_"):
        return "host"
    if event.startswith("controller_") or event in {"capability_evidence_synced"}:
        return "controller"
    if event == "research_capability_decision_recorded":
        return "project_manager"
    return "project_manager"


def _active_node_children_status(run_root: Path | None) -> bool | None:
    if run_root is None:
        return None
    try:
        frontier = _active_frontier(run_root)
        return _active_node_has_children(run_root, frontier)
    except (OSError, KeyError, RouterError, json.JSONDecodeError, ValueError, TypeError):
        return None


def _event_applicable_for_active_node(meta: dict[str, Any], active_node_has_children: bool | None) -> bool:
    if active_node_has_children is None:
        return True
    if meta.get("requires_active_node_children") and not active_node_has_children:
        return False
    if meta.get("forbids_active_node_children") and active_node_has_children:
        return False
    return True


def _pending_expected_external_event_groups(
    run_state: dict[str, Any],
    run_root: Path | None = None,
) -> list[list[tuple[str, dict[str, Any]]]]:
    flags = run_state["flags"]
    grouped: dict[str, list[tuple[str, dict[str, str]]]] = {}
    ordered_requires: list[str] = []
    active_node_has_children = _active_node_children_status(run_root)
    for event, meta in EXTERNAL_EVENTS.items():
        required_flag = meta.get("requires_flag")
        if not required_flag:
            continue
        if not _event_applicable_for_active_node(meta, active_node_has_children):
            continue
        if required_flag not in grouped:
            grouped[required_flag] = []
            ordered_requires.append(required_flag)
        grouped[required_flag].append((event, meta))

    def group_already_has_terminal_outcome(group: list[tuple[str, dict[str, str]]]) -> bool:
        recorded_events = [event for event, meta in group if flags.get(meta["flag"])]
        if not recorded_events:
            return False
        recorded_blocks = [event for event in recorded_events if event in GATE_OUTCOME_BLOCK_EVENTS]
        if recorded_blocks:
            pass_events = [
                event
                for event, meta in group
                if event in GATE_OUTCOME_PASS_CLEAR_FLAGS and not flags.get(meta["flag"])
            ]
            if pass_events:
                return False
        return True

    pending: list[list[tuple[str, dict[str, str]]]] = []
    for required_flag in ordered_requires:
        if not flags.get(required_flag):
            continue
        if required_flag == "pm_control_blocker_repair_decision_recorded" and not isinstance(
            run_state.get("active_control_blocker"), dict
        ):
            continue
        group = grouped[required_flag]
        if group_already_has_terminal_outcome(group):
            continue
        pending.append(group)
    return pending


def _next_expected_role_decision_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    pending_groups = _pending_expected_external_event_groups(run_state, run_root)
    if not pending_groups:
        return None
    group = pending_groups[0]
    allowed_events = [event for event, _meta in group]
    roles = sorted({_event_wait_role(event, meta) for event, meta in group})
    required_flag = str(group[0][1].get("requires_flag") or "")
    role_label = roles[0] if len(roles) == 1 else ",".join(roles)
    safe_event_label = "_or_".join(allowed_events).replace("-", "_")
    return _expected_role_decision_wait_action(
        project_root,
        run_state,
        run_root,
        label=f"controller_waits_for_expected_event_{safe_event_label}",
        summary=(
            f"Prerequisite {required_flag} is satisfied and no controller action is due. "
            f"Controller must wait for expected external event(s): {', '.join(allowed_events)}."
        ),
        allowed_external_events=allowed_events,
        to_role=role_label,
        payload_contract=_role_decision_payload_contract_for_events(project_root, run_root, allowed_events),
    )


def _pending_role_decision_staleness(run_state: dict[str, Any], pending_action: object) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or not allowed_events:
        return {
            "reason": "await_role_decision_missing_allowed_external_events",
            "action_type": pending_action.get("action_type"),
            "label": pending_action.get("label"),
        }
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    invalid_events: list[dict[str, Any]] = []
    normalized_events: list[str] = []
    for item in allowed_events:
        if not isinstance(item, str):
            invalid_events.append({"issue": "non_string_allowed_external_event", "event": repr(item)})
            continue
        normalized_events.append(item)
        meta = EXTERNAL_EVENTS.get(item)
        if not isinstance(meta, dict):
            invalid_events.append({"issue": "unknown_external_event", "event": item})
            continue
        required_flag = meta.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            invalid_events.append(
                {
                    "issue": "requires_flag_false",
                    "event": item,
                    "requires_flag": required_flag,
                    "current_value": flags.get(required_flag),
                }
            )
    if not invalid_events:
        return None
    return {
        "reason": "await_role_decision_allowed_event_not_currently_receivable",
        "action_type": pending_action.get("action_type"),
        "label": pending_action.get("label"),
        "allowed_external_events": normalized_events,
        "invalid_allowed_external_events": invalid_events,
    }


def _reconcile_pending_role_wait_from_packet_status(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: object,
) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or "worker_current_node_result_returned" not in allowed_events:
        return None
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    meta = EXTERNAL_EVENTS["worker_current_node_result_returned"]
    required_flag = str(meta.get("requires_flag") or "")
    if required_flag and not flags.get(required_flag):
        return None
    if flags.get(meta["flag"]):
        return None
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json")
    status = str(packet_ledger.get("active_packet_status") or "")
    if status not in {"worker-result-needs-review", "result-envelope-returned"}:
        return None
    record = _active_packet_ledger_record(packet_ledger)
    if not isinstance(record, dict):
        return None
    packet_id = str(record.get("packet_id") or packet_ledger.get("active_packet_id") or "")
    if not packet_id:
        return None
    result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
    if not result_path.exists():
        return None
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
    status_packet = read_json_if_exists(paths["controller_status_packet"])
    if status_packet.get("schema_version") != "flowpilot.controller_status_packet.v1":
        return None
    if status_packet.get("status") != "result-envelope-returned":
        return None
    result = packet_runtime.load_envelope(project_root, result_path)
    if result.get("next_recipient") != "human_like_reviewer":
        return None
    result_hash = packet_runtime.sha256_file(result_path)
    payload = {
        "packet_id": packet_id,
        "result_envelope_path": project_relative(project_root, result_path),
        "result_envelope_hash": result_hash,
        "reconciled_from_packet_ledger": True,
        "reconciled_from_controller_status_packet": True,
    }
    _validate_current_node_result_event(project_root, run_state, payload)
    event = "worker_current_node_result_returned"
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        return None
    run_state["flags"][meta["flag"]] = True
    run_state["events"].append(
        {
            "event": event,
            "summary": meta["summary"],
            "payload": payload,
            "recorded_at": utc_now(),
            "reconciled_by_router": True,
        }
    )
    _mark_scoped_event_recorded(run_state, scoped_identity)
    append_history(
        run_state,
        "router_reconciled_pending_role_wait_from_packet_status",
        {
            "event": event,
            "packet_id": packet_id,
            "packet_status": status,
            "result_envelope_path": payload["result_envelope_path"],
            "status_packet_checked": True,
        },
    )
    return {
        "event": event,
        "packet_id": packet_id,
        "result_envelope_path": payload["result_envelope_path"],
        "packet_status": status,
    }


def _commit_system_card_delivery_artifact(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending: dict[str, Any],
) -> dict[str, Any]:
    card_id = str(pending["card_id"])
    card_entry = next((entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
    if card_entry is None:
        raise RouterError(f"unknown system card in pending action: {card_id}")
    if not run_state.get("manifest_check_requested"):
        raise RouterError("system card delivery requires a current manifest check")
    manifest = load_manifest_from_run(run_root)
    card = manifest_card(manifest, card_id)
    delivery_context = pending.get("delivery_context")
    if not isinstance(delivery_context, dict):
        delivery_context = _live_card_delivery_context(project_root, run_root, run_state, card_entry, card)
    delivery = {
        "card_id": card_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "to_role": pending["to_role"],
        "path": card["path"],
        "delivery_mode": pending.get("delivery_mode") or "envelope_only_v2",
        "controller_visibility": "system_card_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": pending.get("open_method") or "open-card",
        "card_return_event": pending.get("card_return_event") or _card_return_event_for_card(card_id),
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "direct_router_ack_token": pending.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
        "expected_return_path": pending.get("expected_return_path"),
        "expected_receipt_path": pending.get("expected_receipt_path"),
        "card_envelope_path": pending.get("card_envelope_path"),
        "delivery_id": pending.get("delivery_id"),
        "delivery_attempt_id": pending.get("delivery_attempt_id"),
        "body_path": pending.get("body_path"),
        "body_hash": pending.get("body_hash"),
        "manifest_path": pending.get("manifest_path"),
        "manifest_hash": pending.get("manifest_hash"),
        "target_agent_id": pending.get("target_agent_id"),
        "resume_tick_id": pending.get("resume_tick_id"),
        "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
        "delivery_context": delivery_context,
        "delivered_at": utc_now(),
    }
    if card_id == "reviewer.startup_fact_check":
        delivery.update(
            {
                "startup_mechanical_audit_path": pending.get("startup_mechanical_audit_path"),
                "startup_mechanical_audit_hash": pending.get("startup_mechanical_audit_hash"),
                "router_owned_check_proof_path": pending.get("router_owned_check_proof_path"),
                "router_owned_check_proof_hash": pending.get("router_owned_check_proof_hash"),
                "router_computable_checks_already_enforced": True,
                "reviewer_should_not_reprove_router_computable_checks": True,
                "reviewer_required_external_facts": pending.get("reviewer_required_external_facts") or [],
            }
        )
    envelope_path_raw = delivery.get("card_envelope_path")
    expected_return_path_raw = delivery.get("expected_return_path")
    expected_receipt_path_raw = delivery.get("expected_receipt_path")
    if not all(isinstance(item, str) and item for item in (envelope_path_raw, expected_return_path_raw, expected_receipt_path_raw)):
        raise RouterError("system card envelope delivery requires envelope, receipt, and return paths")
    envelope_path = resolve_project_path(project_root, str(envelope_path_raw))
    expected_return_path = resolve_project_path(project_root, str(expected_return_path_raw))
    expected_receipt_path = resolve_project_path(project_root, str(expected_receipt_path_raw))
    envelope = {
        "schema_version": card_runtime.CARD_ENVELOPE_SCHEMA,
        "run_id": run_state["run_id"],
        "run_root": project_relative(project_root, run_root),
        "resume_tick_id": delivery.get("resume_tick_id"),
        "envelope_id": delivery.get("delivery_attempt_id"),
        "delivery_id": delivery.get("delivery_id"),
        "delivery_attempt_id": delivery.get("delivery_attempt_id"),
        "card_id": card_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "target_role": pending["to_role"],
        "target_agent_id": delivery.get("target_agent_id"),
        "body_path": delivery.get("body_path"),
        "body_hash": delivery.get("body_hash"),
        "manifest_path": delivery.get("manifest_path"),
        "manifest_hash": delivery.get("manifest_hash"),
        "body_visibility": "target_role_runtime_only",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "controller_visibility": "system_card_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": delivery.get("open_method") or "open-card",
        "card_return_event": delivery.get("card_return_event"),
        "card_checkin_instruction": delivery.get("card_checkin_instruction"),
        "direct_router_ack_token": delivery.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
        "expected_receipt_path": project_relative(project_root, expected_receipt_path),
        "expected_return_path": project_relative(project_root, expected_return_path),
        "delivery_context": delivery_context,
        "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
        "delivered_at": delivery["delivered_at"],
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated_by_receipt": False,
    }
    envelope["envelope_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(envelope_path, envelope)
    delivery["card_envelope_hash"] = envelope["envelope_hash"]
    delivery["resource_lifecycle"] = "committed_artifact"
    delivery["artifact_committed"] = True
    delivery["relay_allowed"] = True
    delivery["apply_required"] = False
    run_state["delivered_cards"].append(delivery)
    run_state["flags"][card_entry["flag"]] = True
    run_state["manifest_check_requested"] = False
    run_state["prompt_deliveries"] = int(run_state.get("prompt_deliveries", 0)) + 1
    ledger = read_json_if_exists(run_root / "prompt_delivery_ledger.json") or {"schema_version": "flowpilot.prompt_delivery_ledger.v1", "deliveries": []}
    ledger.setdefault("deliveries", []).append(delivery)
    ledger["updated_at"] = utc_now()
    write_json(run_root / "prompt_delivery_ledger.json", ledger)
    card_ledger = _read_card_ledger(run_root, str(run_state["run_id"]))
    card_ledger.setdefault("deliveries", []).append(
        {
            "card_id": card_id,
            "delivery_id": delivery.get("delivery_id"),
            "delivery_attempt_id": delivery.get("delivery_attempt_id"),
            "to_role": pending["to_role"],
            "target_agent_id": delivery.get("target_agent_id"),
            "card_envelope_path": project_relative(project_root, envelope_path),
            "card_envelope_hash": envelope["envelope_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "body_hash": delivery.get("body_hash"),
            "manifest_hash": delivery.get("manifest_hash"),
            "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
            "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
            "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
            "requires_read_receipt": True,
            "card_return_event": delivery.get("card_return_event"),
            "card_checkin_instruction": delivery.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "expected_return_path": project_relative(project_root, expected_return_path),
            "delivered_at": delivery["delivered_at"],
        }
    )
    card_ledger["updated_at"] = utc_now()
    write_json(_card_ledger_path(run_root), card_ledger)
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    return_ledger.setdefault("pending_returns", []).append(
        {
            "card_return_event": delivery.get("card_return_event"),
            "status": "pending",
            "card_id": card_id,
            "delivery_id": delivery.get("delivery_id"),
            "delivery_attempt_id": delivery.get("delivery_attempt_id"),
            "target_role": pending["to_role"],
            "target_agent_id": delivery.get("target_agent_id"),
            "card_envelope_path": project_relative(project_root, envelope_path),
            "card_envelope_hash": envelope["envelope_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "expected_return_path": project_relative(project_root, expected_return_path),
            "card_checkin_instruction": delivery.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
            "sent_at": delivery["delivered_at"],
        }
    )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    return {
        "ok": True,
        "applied": "commit_system_card_delivery_artifact",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "artifact_exists": True,
        "artifact_hash_verified": True,
        "ledger_recorded": True,
        "return_wait_recorded": True,
        "relay_allowed": True,
        "apply_required": False,
        "card_envelope_path": project_relative(project_root, envelope_path),
        "card_checkin_instruction": delivery.get("card_checkin_instruction"),
        "expected_return_path": project_relative(project_root, expected_return_path),
        "expected_receipt_path": project_relative(project_root, expected_receipt_path),
    }


def _commit_system_card_bundle_delivery_artifact(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending: dict[str, Any],
) -> dict[str, Any]:
    if not run_state.get("manifest_check_requested"):
        raise RouterError("system card bundle delivery requires a current manifest check")
    cards = pending.get("cards")
    if not isinstance(cards, list) or len(cards) < 2:
        raise RouterError("system card bundle delivery requires at least two member cards")
    role = str(pending.get("to_role") or "")
    bundle_id = str(pending.get("card_bundle_id") or "")
    bundle_path_raw = str(pending.get("card_bundle_envelope_path") or "")
    expected_return_path_raw = str(pending.get("expected_return_path") or "")
    expected_receipt_paths = pending.get("expected_receipt_paths")
    if not bundle_id or not bundle_path_raw or not expected_return_path_raw:
        raise RouterError("system card bundle delivery requires bundle id, envelope path, and return path")
    if not isinstance(expected_receipt_paths, list) or len(expected_receipt_paths) != len(cards):
        raise RouterError("system card bundle delivery requires one expected receipt path per member")
    bundle_path = resolve_project_path(project_root, bundle_path_raw)
    expected_return_path = resolve_project_path(project_root, expected_return_path_raw)
    manifest = load_manifest_from_run(run_root)
    delivered_at = utc_now()
    envelope_cards: list[dict[str, Any]] = []
    deliveries: list[dict[str, Any]] = []
    for index, member in enumerate(cards):
        if not isinstance(member, dict):
            raise RouterError("system card bundle member must be an object")
        card_id = str(member.get("card_id") or "")
        card_entry = next((entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
        if card_entry is None:
            raise RouterError(f"unknown system card in bundle: {card_id}")
        card = manifest_card(manifest, card_id)
        delivery_context = member.get("delivery_context")
        if not isinstance(delivery_context, dict):
            delivery_context = _live_card_delivery_context(project_root, run_root, run_state, card_entry, card)
        expected_receipt_path = resolve_project_path(project_root, str(expected_receipt_paths[index]))
        body_path_raw = str(member.get("body_path") or "")
        body_hash = str(member.get("body_hash") or "")
        if not body_path_raw or not body_hash:
            raise RouterError(f"system card bundle member {card_id} missing body path or hash")
        envelope_card = {
            "card_id": card_id,
            "path": card["path"],
            "delivery_id": member.get("delivery_id"),
            "delivery_attempt_id": member.get("delivery_attempt_id"),
            "body_path": body_path_raw,
            "body_hash": body_hash,
            "manifest_path": member.get("manifest_path"),
            "manifest_hash": member.get("manifest_hash"),
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "card_return_event": member.get("card_return_event") or _card_return_event_for_card(card_id),
            "delivery_context": delivery_context,
        }
        envelope_cards.append(envelope_card)
        deliveries.append(
            {
                "card_id": card_id,
                "from": "system",
                "issued_by": "router",
                "delivered_by": "controller",
                "to_role": role,
                "path": card["path"],
                "delivery_mode": "same_role_system_card_bundle_v1",
                "controller_visibility": "system_card_bundle_envelope_only",
                "sealed_body_reads_allowed": False,
                "requires_read_receipt": True,
                "open_method": "open-card-bundle",
                "card_return_event": envelope_card["card_return_event"],
                "bundle_return_event": pending.get("card_return_event"),
                "card_checkin_instruction": pending.get("card_checkin_instruction"),
                "direct_router_ack_token": pending.get("direct_router_ack_token"),
                "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
                "expected_return_path": expected_return_path_raw,
                "expected_receipt_path": project_relative(project_root, expected_receipt_path),
                "card_bundle_id": bundle_id,
                "card_bundle_envelope_path": bundle_path_raw,
                "card_envelope_path": bundle_path_raw,
                "delivery_id": member.get("delivery_id"),
                "delivery_attempt_id": member.get("delivery_attempt_id"),
                "body_path": body_path_raw,
                "body_hash": body_hash,
                "manifest_path": member.get("manifest_path"),
                "manifest_hash": member.get("manifest_hash"),
                "target_agent_id": pending.get("target_agent_id"),
                "resume_tick_id": pending.get("resume_tick_id"),
                "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
                "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
                "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
                "delivery_context": delivery_context,
                "delivered_at": delivered_at,
            }
        )
        for key in (
            "pm_context_paths",
            "pm_prior_path_context_required_for_decision",
            "controller_history_is_evidence",
        ):
            if key in member:
                deliveries[-1][key] = member[key]
    envelope = {
        "schema_version": card_runtime.CARD_BUNDLE_ENVELOPE_SCHEMA,
        "run_id": run_state["run_id"],
        "run_root": project_relative(project_root, run_root),
        "resume_tick_id": pending.get("resume_tick_id"),
        "bundle_id": bundle_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "target_role": role,
        "target_agent_id": pending.get("target_agent_id"),
        "cards": envelope_cards,
        "card_ids": [card["card_id"] for card in envelope_cards],
        "body_visibility": "target_role_runtime_only",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "controller_visibility": "system_card_bundle_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": "open-card-bundle",
        "card_return_event": pending.get("card_return_event"),
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "direct_router_ack_token": pending.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
        "expected_receipt_paths": [card["expected_receipt_path"] for card in envelope_cards],
        "expected_return_path": project_relative(project_root, expected_return_path),
        "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
        "delivered_at": delivered_at,
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated_by_receipt": False,
        "same_role_bundle": True,
        "manifest_batch_checked": True,
    }
    envelope["bundle_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(bundle_path, envelope)
    run_state.setdefault("delivered_cards", [])
    ledger = read_json_if_exists(run_root / "prompt_delivery_ledger.json") or {
        "schema_version": "flowpilot.prompt_delivery_ledger.v1",
        "run_id": run_state["run_id"],
        "deliveries": [],
    }
    card_ledger = _read_card_ledger(run_root, str(run_state["run_id"]))
    for delivery in deliveries:
        delivery["card_bundle_envelope_hash"] = envelope["bundle_hash"]
        delivery["card_envelope_hash"] = envelope["bundle_hash"]
        delivery["resource_lifecycle"] = "committed_artifact"
        delivery["artifact_committed"] = True
        delivery["relay_allowed"] = True
        delivery["apply_required"] = False
        run_state["delivered_cards"].append(delivery)
        card_entry = next(entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == delivery["card_id"])
        run_state["flags"][card_entry["flag"]] = True
        ledger.setdefault("deliveries", []).append(delivery)
        card_ledger.setdefault("deliveries", []).append(
            {
                "card_id": delivery.get("card_id"),
                "card_bundle_id": bundle_id,
                "delivery_id": delivery.get("delivery_id"),
                "delivery_attempt_id": delivery.get("delivery_attempt_id"),
                "to_role": role,
                "target_agent_id": delivery.get("target_agent_id"),
                "card_bundle_envelope_path": bundle_path_raw,
                "card_envelope_path": bundle_path_raw,
                "card_bundle_envelope_hash": envelope["bundle_hash"],
                "card_envelope_hash": envelope["bundle_hash"],
                "resource_lifecycle": "committed_artifact",
                "artifact_committed": True,
                "relay_allowed": True,
                "apply_required": False,
                "body_hash": delivery.get("body_hash"),
                "manifest_hash": delivery.get("manifest_hash"),
                "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
                "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
                "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
                "requires_read_receipt": True,
                "card_return_event": delivery.get("card_return_event"),
                "bundle_return_event": pending.get("card_return_event"),
                "card_checkin_instruction": delivery.get("card_checkin_instruction"),
                "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
                "expected_receipt_path": delivery.get("expected_receipt_path"),
                "expected_return_path": expected_return_path_raw,
                "delivered_at": delivered_at,
            }
        )
    run_state["manifest_check_requested"] = False
    run_state["prompt_deliveries"] = int(run_state.get("prompt_deliveries", 0)) + len(deliveries)
    ledger["updated_at"] = utc_now()
    write_json(run_root / "prompt_delivery_ledger.json", ledger)
    card_ledger["updated_at"] = utc_now()
    write_json(_card_ledger_path(run_root), card_ledger)
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    return_ledger.setdefault("pending_returns", []).append(
        {
            "return_kind": "system_card_bundle",
            "card_return_event": pending.get("card_return_event"),
            "status": "pending",
            "card_bundle_id": bundle_id,
            "card_ids": [delivery.get("card_id") for delivery in deliveries],
            "delivery_attempt_ids": [delivery.get("delivery_attempt_id") for delivery in deliveries],
            "target_role": role,
            "target_agent_id": pending.get("target_agent_id"),
            "card_bundle_envelope_path": bundle_path_raw,
            "card_bundle_envelope_hash": envelope["bundle_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "expected_receipt_paths": [delivery.get("expected_receipt_path") for delivery in deliveries],
            "expected_return_path": expected_return_path_raw,
            "card_checkin_instruction": pending.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
            "sent_at": delivered_at,
        }
    )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    return {
        "ok": True,
        "applied": "commit_system_card_bundle_delivery_artifact",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "artifact_exists": True,
        "artifact_hash_verified": True,
        "ledger_recorded": True,
        "return_wait_recorded": True,
        "relay_allowed": True,
        "apply_required": False,
        "card_bundle_id": bundle_id,
        "card_bundle_envelope_path": bundle_path_raw,
        "card_bundle_envelope_hash": envelope["bundle_hash"],
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "expected_return_path": expected_return_path_raw,
        "expected_receipt_paths": [delivery.get("expected_receipt_path") for delivery in deliveries],
    }


def _pending_return_record_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    delivery_attempt_id = action.get("delivery_attempt_id")
    for record in _pending_return_records(run_root, run_id):
        if (
            isinstance(record, dict)
            and record.get("delivery_attempt_id") == delivery_attempt_id
            and record.get("card_id") == action.get("card_id")
        ):
            return record
    return None


def _pending_bundle_return_record_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    bundle_id = action.get("card_bundle_id")
    for record in _pending_return_records(run_root, run_id):
        if (
            isinstance(record, dict)
            and record.get("return_kind") == "system_card_bundle"
            and record.get("card_bundle_id") == bundle_id
        ):
            return record
    return None


def _apply_card_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    ack_path = str(pending.get("expected_return_path") or "")
    envelope_path = str(pending.get("card_envelope_path") or "")
    if not ack_path or not envelope_path:
        raise RouterError("card return check requires expected_return_path and card_envelope_path")
    validation = card_runtime.validate_card_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    for item in return_ledger.setdefault("pending_returns", []):
        if (
            isinstance(item, dict)
            and item.get("delivery_attempt_id") == pending.get("delivery_attempt_id")
            and item.get("card_return_event") == pending.get("card_return_event")
        ):
            item["status"] = "resolved"
            item["resolved_at"] = utc_now()
            item["ack_path"] = validation["ack_path"]
            item["ack_hash"] = validation["ack_hash"]
            item["receipt_ref_count"] = validation["receipt_ref_count"]
    completed = return_ledger.setdefault("completed_returns", [])
    if not any(
        isinstance(item, dict)
        and item.get("delivery_attempt_id") == pending.get("delivery_attempt_id")
        and item.get("card_return_event") == pending.get("card_return_event")
        for item in completed
    ):
        completed.append(
            {
                "card_return_event": pending.get("card_return_event"),
                "delivery_id": pending.get("delivery_id"),
                "delivery_attempt_id": pending.get("delivery_attempt_id"),
                "card_id": pending.get("card_id"),
                "target_role": pending.get("to_role"),
                "ack_path": validation["ack_path"],
                "ack_hash": validation["ack_hash"],
                "receipt_ref_count": validation["receipt_ref_count"],
                "checked_at": utc_now(),
                "status": "resolved",
            }
        )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    run_state["card_return_checks"] = int(run_state.get("card_return_checks", 0)) + 1
    run_state.setdefault("card_return_events", []).append(validation)
    return {"ok": True, "status": "resolved", "validation": validation}


def _apply_card_bundle_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    ack_path = str(pending.get("expected_return_path") or "")
    envelope_path = str(pending.get("card_bundle_envelope_path") or "")
    if not ack_path or not envelope_path:
        raise RouterError("card bundle return check requires expected_return_path and card_bundle_envelope_path")
    try:
        validation = card_runtime.validate_card_bundle_ack(project_root, ack_path=ack_path, envelope_path=envelope_path)
    except card_runtime.CardRuntimeError:
        inspection = card_runtime.inspect_card_bundle_ack_incomplete(project_root, ack_path=ack_path, envelope_path=envelope_path)
        if not inspection.get("incomplete"):
            raise
        return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
        incomplete_record = {
            "return_kind": "system_card_bundle",
            "card_return_event": pending.get("card_return_event"),
            "card_bundle_id": pending.get("card_bundle_id"),
            "card_ids": pending.get("card_ids") or [],
            "target_role": pending.get("to_role"),
            "ack_path": inspection["ack_path"],
            "ack_hash": inspection["ack_hash"],
            "missing_card_ids": inspection["missing_card_ids"],
            "checked_at": utc_now(),
            "status": "bundle_ack_incomplete",
            "recovery": "same_role_must_resubmit_bundle_ack_with_all_member_receipts",
        }
        for item in return_ledger.setdefault("pending_returns", []):
            if (
                isinstance(item, dict)
                and item.get("return_kind") == "system_card_bundle"
                and item.get("card_bundle_id") == pending.get("card_bundle_id")
                and item.get("card_return_event") == pending.get("card_return_event")
            ):
                item["status"] = "bundle_ack_incomplete"
                item["missing_card_ids"] = list(inspection["missing_card_ids"])
                item["incomplete_ack_path"] = inspection["ack_path"]
                item["incomplete_ack_hash"] = inspection["ack_hash"]
                item["incomplete_checked_at"] = incomplete_record["checked_at"]
                item["recovery"] = incomplete_record["recovery"]
        return_ledger.setdefault("incomplete_returns", []).append(incomplete_record)
        return_ledger["updated_at"] = utc_now()
        write_json(_return_event_ledger_path(run_root), return_ledger)
        run_state["card_return_checks"] = int(run_state.get("card_return_checks", 0)) + 1
        run_state.setdefault("card_return_events", []).append(incomplete_record)
        return {
            "ok": False,
            "waiting": True,
            "status": "bundle_ack_incomplete",
            "record": incomplete_record,
            "missing_card_ids": inspection["missing_card_ids"],
            "expected_return_path": ack_path,
            "waiting_for_role": pending.get("to_role"),
        }
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    for item in return_ledger.setdefault("pending_returns", []):
        if (
            isinstance(item, dict)
            and item.get("return_kind") == "system_card_bundle"
            and item.get("card_bundle_id") == pending.get("card_bundle_id")
            and item.get("card_return_event") == pending.get("card_return_event")
        ):
            item["status"] = "resolved"
            item["resolved_at"] = utc_now()
            item["ack_path"] = validation["ack_path"]
            item["ack_hash"] = validation["ack_hash"]
            item["receipt_ref_count"] = validation["receipt_ref_count"]
    completed = return_ledger.setdefault("completed_returns", [])
    if not any(
        isinstance(item, dict)
        and item.get("return_kind") == "system_card_bundle"
        and item.get("card_bundle_id") == pending.get("card_bundle_id")
        and item.get("card_return_event") == pending.get("card_return_event")
        for item in completed
    ):
        completed.append(
            {
                "return_kind": "system_card_bundle",
                "card_return_event": pending.get("card_return_event"),
                "card_bundle_id": pending.get("card_bundle_id"),
                "card_ids": validation["member_card_ids"],
                "target_role": pending.get("to_role"),
                "ack_path": validation["ack_path"],
                "ack_hash": validation["ack_hash"],
                "receipt_ref_count": validation["receipt_ref_count"],
                "checked_at": utc_now(),
                "status": "resolved",
            }
        )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    run_state["card_return_checks"] = int(run_state.get("card_return_checks", 0)) + 1
    run_state.setdefault("card_return_events", []).append(validation)
    return {"ok": True, "status": "resolved", "validation": validation}


def _try_auto_consume_pending_card_return_ack(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    if pending.get("artifact_committed") is False:
        return {"consumed": False, "preserve_pending": True, "reason": "artifact_not_committed"}
    try:
        if pending.get("action_type") in {"await_card_bundle_return_event", "check_card_bundle_return_event", "deliver_system_card_bundle"}:
            result = _apply_card_bundle_return_event_check(project_root, run_root, run_state, pending)
        else:
            result = _apply_card_return_event_check(project_root, run_root, run_state, pending)
    except (RouterError, card_runtime.CardRuntimeError) as exc:
        return {"consumed": False, "preserve_pending": False, "reason": "ack_requires_explicit_check", "error": str(exc)}
    return {"consumed": True, "result": result}


def _pending_action_matches_card_return(pending_action: object, pending_return: dict[str, Any]) -> bool:
    if not isinstance(pending_action, dict):
        return False
    if pending_return.get("return_kind") == "system_card_bundle":
        return (
            pending_action.get("card_bundle_id") == pending_return.get("card_bundle_id")
            or pending_action.get("expected_return_path") == pending_return.get("expected_return_path")
        )
    return (
        pending_action.get("delivery_attempt_id") == pending_return.get("delivery_attempt_id")
        or pending_action.get("expected_return_path") == pending_return.get("expected_return_path")
    )


def _record_card_return_event_from_external_entrypoint(project_root: Path, event: str) -> dict[str, Any]:
    del project_root
    raise RouterError(
        f"{event} is a system-card ACK return event, and the legacy record-event ACK path is disabled. "
        "The addressed role must run the card check-in command from the envelope so the ACK is submitted "
        "directly to Router with its direct Router ACK token."
    )


def _committed_card_bundle_artifact_extra(
    project_root: Path,
    record: dict[str, Any],
    *,
    relay_allowed_if_ready: bool,
) -> dict[str, Any]:
    envelope_path = str(record.get("card_bundle_envelope_path") or "")
    expected_return_path = str(record.get("expected_return_path") or "")
    expected_receipt_paths = record.get("expected_receipt_paths")
    artifact_exists = False
    artifact_hash_verified = False
    if envelope_path:
        resolved = resolve_project_path(project_root, envelope_path)
        artifact_exists = resolved.exists() and resolved.is_file()
        if artifact_exists:
            try:
                envelope = read_json(resolved)
            except Exception:
                envelope = {}
            recorded_hash = str(record.get("card_bundle_envelope_hash") or "")
            artifact_hash_verified = bool(recorded_hash) and envelope.get("bundle_hash") == recorded_hash
    artifact_committed = bool(
        artifact_exists
        and artifact_hash_verified
        and expected_return_path
        and isinstance(expected_receipt_paths, list)
        and expected_receipt_paths
    )
    return {
        "resource_lifecycle": "committed_artifact" if artifact_committed else "missing_committed_artifact",
        "artifact_committed": artifact_committed,
        "artifact_exists": artifact_exists,
        "artifact_hash_verified": artifact_hash_verified,
        "ledger_recorded": True,
        "return_wait_recorded": bool(expected_return_path),
        "relay_allowed": bool(relay_allowed_if_ready and artifact_committed),
        "apply_required": False,
    }


def _auto_commit_system_card_delivery_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    planned = dict(action)
    planned["resource_lifecycle"] = "planned_internal_action"
    planned["artifact_committed"] = False
    planned["relay_allowed"] = False
    planned["apply_required"] = True
    planned.setdefault(
        "planned_artifacts",
        {
            "card_envelope_path": planned.get("card_envelope_path"),
            "expected_receipt_path": planned.get("expected_receipt_path"),
            "expected_return_path": planned.get("expected_return_path"),
        },
    )
    run_state["pending_action"] = planned
    append_history(
        run_state,
        "router_auto_commits_internal_system_card_delivery",
        {
            "action_type": planned.get("action_type"),
            "card_id": planned.get("card_id"),
            "planned_artifacts_exposed_to_controller": False,
        },
    )
    commit_result = _commit_system_card_delivery_artifact(project_root, run_state, run_root, planned)
    append_history(
        run_state,
        "router_committed_system_card_delivery_artifact",
        {
            "card_id": planned.get("card_id"),
            "card_envelope_path": commit_result.get("card_envelope_path"),
            "relay_allowed": commit_result.get("relay_allowed"),
        },
    )
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger="after_router_internal_commit:deliver_system_card")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_internal_commit:deliver_system_card",
        update_display=True,
    )
    save_run_state(run_root, run_state)
    record = _pending_return_record_for_action(run_root, str(run_state["run_id"]), planned)
    if record is None:
        raise RouterError("system card auto-commit did not establish a pending return record")
    committed_extra = _committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    if not committed_extra["relay_allowed"]:
        raise RouterError("system card auto-commit did not produce a relay-ready committed artifact")
    committed = {
        **planned,
        **committed_extra,
        "summary": (
            f"Relay committed system card envelope {planned.get('card_id')} to {planned.get('to_role')}; "
            f"the role must open it through runtime and return {planned.get('card_return_event')}."
        ),
        "allowed_writes": [],
        "auto_committed_by_router": True,
        "auto_commit_result": commit_result,
        "next_after_relay": "await_card_return_event",
    }
    committed["next_step_contract"] = {
        **committed.get("next_step_contract", {}),
        "resource_lifecycle": committed["resource_lifecycle"],
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
    }
    run_state["pending_action"] = committed
    append_history(
        run_state,
        "router_returned_committed_system_card_relay_action",
        {
            "card_id": committed.get("card_id"),
            "card_envelope_path": committed.get("card_envelope_path"),
            "relay_allowed": committed.get("relay_allowed"),
        },
    )
    save_run_state(run_root, run_state)
    return committed


def _auto_commit_system_card_bundle_delivery_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    planned = dict(action)
    planned["resource_lifecycle"] = "planned_internal_action"
    planned["artifact_committed"] = False
    planned["relay_allowed"] = False
    planned["apply_required"] = True
    planned.setdefault(
        "planned_artifacts",
        {
            "card_bundle_envelope_path": planned.get("card_bundle_envelope_path"),
            "expected_receipt_paths": planned.get("expected_receipt_paths"),
            "expected_return_path": planned.get("expected_return_path"),
        },
    )
    run_state["pending_action"] = planned
    append_history(
        run_state,
        "router_auto_commits_internal_system_card_bundle_delivery",
        {
            "action_type": planned.get("action_type"),
            "card_ids": planned.get("card_ids"),
            "planned_artifacts_exposed_to_controller": False,
        },
    )
    commit_result = _commit_system_card_bundle_delivery_artifact(project_root, run_state, run_root, planned)
    append_history(
        run_state,
        "router_committed_system_card_bundle_delivery_artifact",
        {
            "card_bundle_id": planned.get("card_bundle_id"),
            "card_bundle_envelope_path": commit_result.get("card_bundle_envelope_path"),
            "relay_allowed": commit_result.get("relay_allowed"),
        },
    )
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger="after_router_internal_commit:deliver_system_card_bundle")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_internal_commit:deliver_system_card_bundle",
        update_display=True,
    )
    save_run_state(run_root, run_state)
    record = _pending_bundle_return_record_for_action(run_root, str(run_state["run_id"]), planned)
    if record is None:
        raise RouterError("system card bundle auto-commit did not establish a pending return record")
    committed_extra = _committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    if not committed_extra["relay_allowed"]:
        raise RouterError("system card bundle auto-commit did not produce a relay-ready committed artifact")
    committed = {
        **planned,
        **committed_extra,
        "card_bundle_envelope_hash": record.get("card_bundle_envelope_hash"),
        "summary": (
            f"Relay committed system-card bundle {planned.get('card_bundle_id')} to {planned.get('to_role')}; "
            f"the role must open it through runtime and return {planned.get('card_return_event')}."
        ),
        "allowed_writes": [],
        "auto_committed_by_router": True,
        "auto_commit_result": commit_result,
        "next_after_relay": "await_card_bundle_return_event",
    }
    committed["next_step_contract"] = {
        **committed.get("next_step_contract", {}),
        "resource_lifecycle": committed["resource_lifecycle"],
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
    }
    run_state["pending_action"] = committed
    append_history(
        run_state,
        "router_returned_committed_system_card_bundle_relay_action",
        {
            "card_bundle_id": committed.get("card_bundle_id"),
            "card_ids": committed.get("card_ids"),
            "card_bundle_envelope_path": committed.get("card_bundle_envelope_path"),
            "relay_allowed": committed.get("relay_allowed"),
        },
    )
    save_run_state(run_root, run_state)
    return committed


def compute_controller_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any]:
    terminal_action = _run_lifecycle_terminal_action(project_root, run_state, run_root)
    if terminal_action is not None:
        run_state["pending_action"] = terminal_action
        append_history(run_state, "router_computed_terminal_lifecycle_action", {"action_type": terminal_action["action_type"]})
        save_run_state(run_root, run_state)
        return terminal_action
    pending_action = run_state.get("pending_action")
    stale_pending = _pending_role_decision_staleness(run_state, pending_action)
    reconciled_pending = None
    if stale_pending:
        run_state["pending_action"] = None
        append_history(run_state, "router_cleared_stale_pending_action", stale_pending)
        save_run_state(run_root, run_state)
    else:
        reconciled_pending = _reconcile_pending_role_wait_from_packet_status(
            project_root,
            run_root,
            run_state,
            pending_action,
        )
        if reconciled_pending is not None:
            run_state["pending_action"] = None
            _refresh_route_memory(project_root, run_root, run_state, trigger="after_router_reconciled_pending_role_wait")
            _sync_derived_run_views(
                project_root,
                run_root,
                run_state,
                reason="after_router_reconciled_pending_role_wait",
                update_display=True,
            )
            save_run_state(run_root, run_state)
    pending_action = run_state.get("pending_action")
    if (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "deliver_system_card"
        and pending_action.get("artifact_committed") is not True
    ):
        return _auto_commit_system_card_delivery_action(project_root, run_state, run_root, pending_action)
    elif (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "deliver_system_card_bundle"
        and pending_action.get("artifact_committed") is not True
    ):
        return _auto_commit_system_card_bundle_delivery_action(project_root, run_state, run_root, pending_action)
    elif _pending_card_return_ack_exists(project_root, pending_action):
        auto_ack = _try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, pending_action)
        if auto_ack.get("consumed"):
            run_state["pending_action"] = None
            append_history(
                run_state,
                "router_auto_consumed_card_return_ack",
                {
                    "action_type": pending_action.get("action_type") if isinstance(pending_action, dict) else None,
                    "expected_return_path": pending_action.get("expected_return_path") if isinstance(pending_action, dict) else None,
                    "status": (auto_ack.get("result") or {}).get("status"),
                },
            )
            _refresh_route_memory(project_root, run_root, run_state, trigger="after_router_auto_consumed_card_return_ack")
            _sync_derived_run_views(
                project_root,
                run_root,
                run_state,
                reason="after_router_auto_consumed_card_return_ack",
                update_display=True,
            )
            save_run_state(run_root, run_state)
        elif auto_ack.get("preserve_pending"):
            append_history(run_state, "router_preserved_card_wait_before_artifact_commit", auto_ack)
            save_run_state(run_root, run_state)
            return pending_action
        else:
            run_state["pending_action"] = None
            append_history(
                run_state,
                "router_deferred_invalid_card_ack_to_explicit_check",
                {
                    "action_type": pending_action.get("action_type") if isinstance(pending_action, dict) else None,
                    "expected_return_path": pending_action.get("expected_return_path") if isinstance(pending_action, dict) else None,
                    "reason": auto_ack.get("reason"),
                    "error": auto_ack.get("error"),
                },
            )
            save_run_state(run_root, run_state)
    elif pending_action:
        return pending_action
    if not _route_memory_ready(run_root, run_state):
        _refresh_route_memory(project_root, run_root, run_state, trigger="router_next_action")
    action = _next_control_blocker_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_heartbeat_binding_action(project_root, run_state, run_root)
    if action is None:
        action = _next_display_plan_action(project_root, run_state, run_root)
    if action is None:
        action = _next_resume_action(project_root, run_state, run_root)
    if action is None:
        action = _next_controller_boundary_confirmation_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_mechanical_audit_action(project_root, run_state, run_root)
    if action is None:
        action = _next_startup_display_action(project_root, run_state, run_root)
    if action is None:
        _invalidate_route_completion_if_dirty_before_closure(run_state, run_root)
        action = _next_pending_card_return_action(project_root, run_state, run_root)
    if action is None:
        action = _next_system_card_bundle_action(project_root, run_state, run_root)
    if action is None:
        action = _next_system_card_action(project_root, run_state, run_root)
    if isinstance(action, dict) and action.get("action_type") == "deliver_system_card":
        return _auto_commit_system_card_delivery_action(project_root, run_state, run_root, action)
    if isinstance(action, dict) and action.get("action_type") == "deliver_system_card_bundle":
        return _auto_commit_system_card_bundle_delivery_action(project_root, run_state, run_root, action)
    if action is None and _resume_waits_for_pm_decision(run_state):
        action = _expected_role_decision_wait_action(
            project_root,
            run_state,
            run_root,
            label="controller_waits_for_pm_resume_decision",
            summary="Resume state has been loaded and resume cards delivered. Controller must wait for PM resume decision before continuing any route, mail, or packet work.",
            allowed_external_events=["pm_resume_recovery_decision_returned"],
            to_role="project_manager",
            allowed_reads_extra=[
                project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
            ],
            payload_contract=_pm_resume_decision_payload_contract(project_root, run_root),
            pm_work_request_channel=False,
        )
    if action is None:
        action = _next_mail_action(project_root, run_state, run_root)
    if action is None:
        action = _next_material_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_research_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_current_node_packet_action(project_root, run_state, run_root)
    if action is None:
        action = _next_pm_role_work_request_action(project_root, run_state, run_root)
    if action is None:
        action = _next_model_miss_followup_request_wait_action(project_root, run_state, run_root)
    if action is None:
        action = _next_model_miss_controlled_stop_action(project_root, run_state, run_root)
    if action is None:
        action = _next_expected_role_decision_wait_action(project_root, run_state, run_root)
    if action is None:
        _write_control_blocker(
            project_root,
            run_root,
            run_state,
            source="router_no_legal_next_action",
            error_message=(
                "Controller has no legal next action; PM repair or routing decision is required before any "
                "further route, mail, packet, or project work."
            ),
            action_type="controller_no_legal_next_action",
            payload={
                "path": project_relative(project_root, run_state_path(run_root)),
                "role": "controller",
            },
        )
        action = _next_control_blocker_action(project_root, run_state, run_root)
        if action is None:
            raise RouterError("no legal next action control blocker was not materialized")
    run_state["pending_action"] = action
    append_history(run_state, "router_computed_next_controller_action", {"action_type": action["action_type"]})
    save_run_state(run_root, run_state)
    return action


def next_action(project_root: Path, *, new_invocation: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=True, new_invocation=new_invocation)
    boot_action = compute_bootloader_action(project_root, bootstrap)
    if boot_action is not None:
        return boot_action
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("bootloader complete but run router state is missing")
    return compute_controller_action(project_root, run_state, run_root)


def apply_controller_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    pending = _ensure_pending(run_state, action_type)
    result_extra: dict[str, Any] = {}
    if action_type == "check_prompt_manifest":
        run_state["manifest_check_requested"] = True
        run_state["manifest_check_requests"] = int(run_state.get("manifest_check_requests", 0)) + 1
        run_state["manifest_checks"] = int(run_state.get("manifest_checks", 0)) + 1
    elif action_type == "confirm_controller_core_boundary":
        confirmation = _write_controller_boundary_confirmation(project_root, run_root, run_state)
        if _controller_boundary_confirmation_context(project_root, run_root, run_state) is None:
            raise RouterError("controller boundary confirmation was not written with current controller.core evidence")
        run_state["flags"]["controller_role_confirmed"] = True
        run_state["flags"]["controller_role_confirmed_from_router_core"] = True
        run_state["flags"]["controller_boundary_confirmation_written"] = True
        run_state["controller_boundary_confirmation"] = confirmation
        run_state["events"].append(
            {
                "event": "controller_role_confirmed_from_router_core",
                "summary": "Controller confirmed the Router-delivered controller.core boundary.",
                "payload": confirmation,
                "recorded_at": utc_now(),
            }
        )
    elif action_type == "write_startup_mechanical_audit":
        computed_checks = _startup_fact_checks(project_root, run_root, run_state)
        _write_startup_mechanical_audit(project_root, run_root, run_state, computed_checks)
        context = _startup_mechanical_audit_context(project_root, run_root, run_state)
        if context is None:
            raise RouterError("startup mechanical audit was not written with a valid proof")
        run_state["flags"]["startup_mechanical_audit_written"] = True
        run_state["startup_mechanical_audit"] = {
            "path": project_relative(project_root, context["audit_path"]),
            "sha256": context["audit_hash"],
            "proof_path": project_relative(project_root, context["proof_path"]),
            "proof_sha256": context["proof_hash"],
            "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
        }
    elif action_type == "inject_role_io_protocol":
        role = str(pending.get("to_role") or "")
        agent_id = str(pending.get("target_agent_id") or "")
        if role not in CREW_ROLE_KEYS or not agent_id:
            raise RouterError("role I/O protocol injection requires a live target role and agent")
        resume_tick_id = str(pending.get("resume_tick_id") or _latest_resume_tick_id(run_state))
        receipts = _append_role_io_protocol_injections(
            project_root,
            run_root,
            str(run_state["run_id"]),
            [{"role_key": role, "agent_id": agent_id}],
            default_lifecycle_phase="router_repair_injection",
            resume_tick_id=resume_tick_id,
            source_action="inject_role_io_protocol",
        )
        if not receipts:
            receipt = _role_io_protocol_receipt_for_agent(
                run_root,
                str(run_state["run_id"]),
                role=role,
                agent_id=agent_id,
                resume_tick_id=resume_tick_id,
            )
            if receipt is None:
                raise RouterError("role I/O protocol injection did not produce a usable receipt")
            receipts = [receipt]
        run_state["role_io_protocol_injections"] = int(run_state.get("role_io_protocol_injections", 0)) + len(receipts)
        result_extra.update({
            "role_io_protocol_receipts": receipts,
            "protocol_hash": _role_io_protocol_hash(),
        })
    elif action_type == "deliver_system_card":
        raise RouterError("deliver_system_card is relay-only; Router commits the card envelope internally and Controller must only relay it")
    elif action_type == "deliver_system_card_bundle":
        raise RouterError("deliver_system_card_bundle is relay-only; Router commits the card bundle envelope internally and Controller must only relay it")
    elif action_type == "check_packet_ledger":
        run_state["ledger_check_requested"] = True
        run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
        run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
    elif action_type == "deliver_mail":
        mail_id = str(pending["mail_id"])
        mail_entry = next((entry for entry in MAIL_SEQUENCE if entry["mail_id"] == mail_id), None)
        if mail_entry is None:
            raise RouterError(f"unknown mail in pending action: {mail_id}")
        if not run_state.get("ledger_check_requested"):
            raise RouterError("mail delivery requires a current packet-ledger check")
        delivery = {
            "mail_id": mail_id,
            "delivered_by": "controller",
            "to_role": pending["to_role"],
            "delivered_at": utc_now(),
        }
        run_state["delivered_mail"].append(delivery)
        run_state["flags"][mail_entry["flag"]] = True
        run_state["ledger_check_requested"] = False
        run_state["mail_deliveries"] = int(run_state.get("mail_deliveries", 0)) + 1
        ledger = read_json(run_root / "packet_ledger.json")
        ledger.setdefault("mail", []).append(delivery)
        ledger["updated_at"] = utc_now()
        write_json(run_root / "packet_ledger.json", ledger)
    elif action_type == "check_card_return_event":
        _apply_card_return_event_check(project_root, run_root, run_state, pending)
    elif action_type == "check_card_bundle_return_event":
        bundle_result = _apply_card_bundle_return_event_check(project_root, run_root, run_state, pending)
        if bundle_result.get("status") == "bundle_ack_incomplete":
            append_history(run_state, "bundle_ack_incomplete", bundle_result["record"])
            run_state["pending_action"] = None
            _refresh_route_memory(project_root, run_root, run_state, trigger="after_controller_action:bundle_ack_incomplete")
            _sync_derived_run_views(
                project_root,
                run_root,
                run_state,
                reason="after_controller_action:bundle_ack_incomplete",
                update_display=True,
            )
            save_run_state(run_root, run_state)
            return {
                "ok": False,
                "applied": action_type,
                "waiting": True,
                "status": "bundle_ack_incomplete",
                "missing_card_ids": bundle_result["missing_card_ids"],
                "expected_return_path": bundle_result["expected_return_path"],
                "waiting_for_role": bundle_result["waiting_for_role"],
            }
    elif action_type == "await_card_return_event":
        return {"ok": True, "applied": action_type, "waiting": True, "expected_return_path": pending.get("expected_return_path")}
    elif action_type == "await_card_bundle_return_event":
        return {"ok": True, "applied": action_type, "waiting": True, "expected_return_path": pending.get("expected_return_path")}
    elif action_type == "await_user_after_model_miss_stop":
        return {"ok": True, "applied": action_type, "waiting": True, "waiting_for": "user"}
    elif action_type == "relay_material_scan_packets":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("material scan packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("material scan packet relay requires a current packet-ledger check")
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
        _mark_parallel_batch_packets_relayed(run_root, "material_scan")
        run_state["flags"]["material_scan_packets_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_material_scan_results_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("material scan result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("material scan result relay requires a current packet-ledger check")
        index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _relay_result_records(project_root, run_state, index["packets"], to_role="human_like_reviewer", controller_agent_id="controller")
        run_state["flags"]["material_scan_results_relayed_to_reviewer"] = True
        batch = _active_parallel_packet_batch(run_root, "material_scan")
        if batch:
            batch["status"] = "results_relayed_to_reviewer"
            _write_parallel_packet_batch_state(run_root, batch)
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_research_packet":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("research packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("research packet relay requires a current packet-ledger check")
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        _relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
        _mark_parallel_batch_packets_relayed(run_root, "research")
        run_state["flags"]["research_packet_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_research_result_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("research result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("research result relay requires a current packet-ledger check")
        index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        _relay_result_records(project_root, run_state, index["packets"], to_role="human_like_reviewer", controller_agent_id="controller")
        batch = _active_parallel_packet_batch(run_root, "research")
        if batch:
            batch["status"] = "results_relayed_to_reviewer"
            _write_parallel_packet_batch_state(run_root, batch)
        run_state["flags"]["research_result_relayed_to_reviewer"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_pm_role_work_request_packet":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("PM role-work request relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        index = _load_pm_role_work_request_index(run_root, run_state)
        batch_records = _active_pm_role_work_batch_records(index)
        records = [record for record in batch_records if record.get("status") == "open"] if batch_records else []
        if not records:
            active = _active_pm_role_work_request(index)
            records = [active] if isinstance(active, dict) and active.get("status") == "open" else []
        if not records:
            raise RouterError("PM role-work request relay requires an open active request")
        _relay_packet_records(project_root, run_state, records, controller_agent_id="controller")
        for record in records:
            record["status"] = "packet_relayed"
            record["packet_relayed_at"] = utc_now()
        _mark_parallel_batch_packets_relayed(run_root, "pm_role_work")
        index["active_request_id"] = records[0].get("request_id")
        _write_pm_role_work_request_index(run_root, index)
        run_state["flags"]["pm_role_work_request_packet_relayed"] = True
        run_state["ledger_check_requested"] = False
        run_state["pm_role_work_requests"] = {
            "index_path": project_relative(project_root, _pm_role_work_request_index_path(run_root)),
            "active_batch_id": index.get("active_batch_id"),
            "active_request_ids": [record.get("request_id") for record in records],
            "active_packet_ids": [record.get("packet_id") for record in records],
            "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
            "active_request_mode": records[0].get("request_mode"),
        }
    elif action_type == "relay_pm_role_work_result_to_pm":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("PM role-work result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        index = _load_pm_role_work_request_index(run_root, run_state)
        batch_records = _active_pm_role_work_batch_records(index)
        records = [record for record in batch_records if record.get("status") == "result_returned"] if batch_records else []
        if not records:
            active = _active_pm_role_work_request(index)
            records = [active] if isinstance(active, dict) and active.get("status") == "result_returned" else []
        if not records:
            raise RouterError("PM role-work result relay requires an active returned result")
        _relay_result_records(project_root, run_state, records, to_role="project_manager", controller_agent_id="controller")
        for record in records:
            record["status"] = "result_relayed_to_pm"
            record["result_relayed_to_pm_at"] = utc_now()
        batch = _active_parallel_packet_batch(run_root, "pm_role_work")
        if batch:
            batch["status"] = "results_relayed_to_pm"
            _write_parallel_packet_batch_state(run_root, batch)
        index["active_request_id"] = records[0].get("request_id")
        _write_pm_role_work_request_index(run_root, index)
        run_state["flags"]["pm_role_work_result_relayed_to_pm"] = True
        run_state["ledger_check_requested"] = False
        run_state["pm_role_work_requests"] = {
            "index_path": project_relative(project_root, _pm_role_work_request_index_path(run_root)),
            "active_batch_id": index.get("active_batch_id"),
            "active_request_ids": [record.get("request_id") for record in records],
            "active_packet_ids": [record.get("packet_id") for record in records],
            "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
            "active_request_mode": records[0].get("request_mode"),
        }
    elif action_type == "relay_current_node_packet":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("current-node packet relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state.get("ledger_check_requested"):
            raise RouterError("current-node packet relay requires a current packet-ledger check")
        records = _current_node_packet_records(project_root, run_state)
        for record in records:
            envelope_path = _packet_envelope_path_from_record(project_root, run_state, record)
            envelope = packet_runtime.load_envelope(project_root, envelope_path)
            audit = packet_runtime.validate_packet_ready_for_direct_relay(
                project_root,
                packet_envelope=envelope,
                envelope_path=envelope_path,
            )
            if not audit.get("passed"):
                raise RouterError(f"current-node packet envelope is not ready for direct relay: {audit.get('blockers')}")
            _ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
            packet_runtime.controller_relay_envelope(
                project_root,
                envelope=envelope,
                envelope_path=envelope_path,
                controller_agent_id="controller",
                received_from_role=str(envelope.get("from_role") or "project_manager"),
                relayed_to_role=str(envelope.get("to_role")),
            )
        _mark_parallel_batch_packets_relayed(run_root, "current_node")
        run_state["flags"]["current_node_packet_relayed"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "relay_current_node_result_to_reviewer":
        combined_ledger_check = pending.get("combined_ledger_check_and_relay") is True
        if not run_state.get("ledger_check_requested"):
            if not combined_ledger_check:
                raise RouterError("current-node result relay requires a current packet-ledger check")
            run_state["ledger_check_requested"] = True
            run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
            run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
        if not run_state["flags"].get("current_node_worker_result_returned"):
            raise RouterError("current-node result relay requires worker result event")
        records = _current_node_packet_records(project_root, run_state)
        _validate_results_exist_for_packets(project_root, run_state, records, next_recipient="human_like_reviewer")
        _relay_result_records(project_root, run_state, records, to_role="human_like_reviewer", controller_agent_id="controller")
        batch = _active_parallel_packet_batch(run_root, "current_node")
        if batch:
            batch["status"] = "results_relayed_to_reviewer"
            _write_parallel_packet_batch_state(run_root, batch)
        run_state["flags"]["current_node_result_relayed_to_reviewer"] = True
        run_state["ledger_check_requested"] = False
    elif action_type == "load_resume_state":
        resume_next = _derive_resume_next_recipient_from_packet_ledger(run_root)
        required_paths = {
            "current_pointer": project_root / ".flowpilot" / "current.json",
            "router_state": run_state_path(run_root),
            "prompt_delivery_ledger": run_root / "prompt_delivery_ledger.json",
            "packet_ledger": run_root / "packet_ledger.json",
            "execution_frontier": run_root / "execution_frontier.json",
            "crew_ledger": run_root / "crew_ledger.json",
            "crew_memory": run_root / "crew_memory",
            "continuation_binding": _continuation_binding_path(run_root),
            "route_history_index": _route_history_index_path(run_root),
            "pm_prior_path_context": _pm_prior_path_context_path(run_root),
        }
        missing = [
            name
            for name, path in required_paths.items()
            if not path.exists()
        ]
        crew_memory_files = sorted((run_root / "crew_memory").glob("*.json")) if (run_root / "crew_memory").exists() else []
        display_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        resume_record = {
            "schema_version": RESUME_EVIDENCE_SCHEMA,
            "run_id": run_state["run_id"],
            "resume_tick_id": _latest_resume_tick_id(run_state),
            "recorded_at": utc_now(),
            "recorded_by": "controller",
            "stable_launcher": True,
            "wake_recorded_to_router": True,
            "controller_only": True,
            "loaded_paths": {
                name: project_relative(project_root, path)
                for name, path in required_paths.items()
                if path.exists()
            },
            "missing_paths": missing,
            "crew_memory_count": len(crew_memory_files),
            "crew_memory_ready_for_rehydration": len(crew_memory_files) == len(CREW_ROLE_KEYS),
            "roles_restored_or_replaced": False,
            "role_rehydration_required": True,
            "controller_visibility": "state_and_envelopes_only",
            "controller_may_read_packet_body": False,
            "controller_may_read_result_body": False,
            "controller_may_infer_route_progress_from_chat_history": False,
            "display_plan_path": project_relative(project_root, _display_plan_path(run_root)),
            "visible_plan_restore_required": True,
            "visible_plan_restored_from_run": True,
            "display_plan_exists": display_payload["display_plan_exists"],
            "display_plan_projection_hash": display_payload["projection_hash"],
            "display_plan_projection": display_payload["native_plan_projection"],
            "resume_next_recipient_from_packet_ledger": resume_next,
            "pm_resume_decision_required": True,
            "ambiguous_state_blocks_controller_execution": bool(missing) or len(crew_memory_files) != len(CREW_ROLE_KEYS),
        }
        write_json(run_root / "continuation" / "resume_reentry.json", resume_record)
        run_state["flags"]["resume_state_loaded"] = True
        run_state["flags"]["resume_state_ambiguous"] = bool(resume_record["ambiguous_state_blocks_controller_execution"])
        run_state["flags"]["resume_roles_restored"] = False
    elif action_type == "rehydrate_role_agents":
        if not run_state["flags"].get("resume_state_loaded"):
            raise RouterError("resume role rehydration requires load_resume_state first")
        _write_resume_role_rehydration_report(project_root, run_root, run_state, payload or {})
    elif action_type == "create_heartbeat_automation":
        _write_host_heartbeat_binding(project_root, run_root, run_state, payload or {})
        run_state["flags"]["continuation_binding_recorded"] = True
        run_state["events"].append(
            {
                "event": "host_records_heartbeat_binding",
                "summary": EXTERNAL_EVENTS["host_records_heartbeat_binding"]["summary"],
                "payload": payload or {},
                "recorded_at": utc_now(),
                "source_action": action_type,
            }
        )
    elif action_type == "sync_display_plan":
        confirmation = _display_confirmation_for_action(payload, pending)
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        if not sync_payload["display_plan_exists"]:
            write_json(_display_plan_path(run_root), _waiting_for_pm_display_plan(run_state))
            sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        _write_route_state_snapshot(project_root, run_root, run_state, source_event="sync_display_plan")
        sync_payload = _display_plan_sync_payload(project_root, run_root, run_state)
        if sync_payload.get("route_sign_display_required"):
            route_sign = _route_map_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
            sync_payload = {
                **sync_payload,
                "route_sign_markdown_path": route_sign.get("markdown_preview_path"),
                "route_sign_mermaid_path": route_sign.get("mermaid_path"),
                "route_sign_display_packet_path": route_sign.get("display_packet_path"),
                "route_sign_mermaid_sha256": route_sign.get("mermaid_sha256"),
                "route_sign_source_kind": route_sign.get("route_source_kind"),
                "route_sign_node_count": route_sign.get("route_node_count"),
                "route_sign_checklist_item_count": route_sign.get("route_checklist_item_count"),
                "route_sign_layout": route_sign.get("route_sign_layout"),
                "route_sign_source_route_path": route_sign.get("source_route_path"),
                "route_sign_source_frontier_path": route_sign.get("source_frontier_path"),
            }
        _append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state["visible_plan_sync"] = {
            "display_plan_path": sync_payload["display_plan_path"],
            "route_state_snapshot_path": sync_payload["route_state_snapshot_path"],
            "route_state_snapshot_hash": sync_payload["route_state_snapshot_hash"],
            "current_status_summary_path": sync_payload.get("current_status_summary_path"),
            "current_status_summary_hash": sync_payload.get("current_status_summary_hash"),
            "projection_hash": sync_payload["projection_hash"],
            "display_text_format": sync_payload.get("display_text_format"),
            "route_sign_display_required": sync_payload.get("route_sign_display_required"),
            "route_sign_display_degraded_reason": sync_payload.get("route_sign_display_degraded_reason"),
            "route_sign_markdown_path": sync_payload.get("route_sign_markdown_path"),
            "route_sign_mermaid_path": sync_payload.get("route_sign_mermaid_path"),
            "route_sign_display_packet_path": sync_payload.get("route_sign_display_packet_path"),
            "route_sign_mermaid_sha256": sync_payload.get("route_sign_mermaid_sha256"),
            "route_sign_source_kind": sync_payload.get("route_sign_source_kind"),
            "route_sign_node_count": sync_payload.get("route_sign_node_count"),
            "route_sign_checklist_item_count": sync_payload.get("route_sign_checklist_item_count"),
            "route_sign_layout": sync_payload.get("route_sign_layout"),
            "route_sign_source_route_path": sync_payload.get("route_sign_source_route_path"),
            "route_sign_source_frontier_path": sync_payload.get("route_sign_source_frontier_path"),
            "synced_at": utc_now(),
            "host_action": sync_payload["host_action"],
            "user_dialog_display_confirmation": confirmation,
        }
    elif action_type == "write_display_surface_status":
        confirmation = _display_confirmation_for_action(payload, pending)
        _write_display_surface_status(project_root, run_root, run_state, confirmation, payload or {})
        _append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state["flags"]["startup_display_status_written"] = True
    elif action_type == "handle_control_blocker":
        _mark_control_blocker_delivered(project_root, run_root, run_state, pending)
    elif action_type == "run_lifecycle_terminal":
        return {"ok": True, "applied": action_type, "terminal": True, "run_lifecycle_status": _terminal_lifecycle_mode(run_state)}
    elif action_type == "await_role_decision":
        return {"ok": True, "applied": action_type, "waiting": True}
    else:
        raise RouterError(f"unknown controller action: {action_type}")
    append_history(run_state, str(pending["label"]), {"action_type": action_type})
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_controller_action:{action_type}")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason=f"after_controller_action:{action_type}",
        update_display=action_type != "sync_display_plan",
    )
    save_run_state(run_root, run_state)
    result = {"ok": True, "applied": action_type}
    result.update(result_extra)
    if action_type == "sync_display_plan":
        result.update(_display_plan_sync_payload(project_root, run_root, run_state))
        result["user_dialog_display_confirmation"] = run_state["visible_plan_sync"]["user_dialog_display_confirmation"]
    return result


def _record_external_event_unchecked(
    project_root: Path,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    if event not in EXTERNAL_EVENTS:
        if _is_card_return_event_name(event):
            return _record_card_return_event_from_external_entrypoint(project_root, event)
        raise RouterError(f"unknown external event: {event}")
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    meta = EXTERNAL_EVENTS[event]
    flag = meta["flag"]
    required_flag = meta.get("requires_flag")
    parent_segment_decision: str | None = None
    model_miss_triage_decision: str | None = None
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"before_external_event:{event}")
    if event == "heartbeat_or_manual_resume_requested":
        tick = _append_heartbeat_tick(project_root, run_root, run_state, payload or {})
        _reset_resume_cycle_for_wakeup(run_state)
        run_state["flags"]["resume_reentry_requested"] = True
        run_state["pending_action"] = None
        record = {
            "event": event,
            "summary": meta["summary"],
            "payload": payload or {},
            "recorded_at": utc_now(),
        }
        run_state["events"].append(record)
        append_history(run_state, event, {"heartbeat_tick": tick})
        _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
        _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
        save_run_state(run_root, run_state)
        return {"ok": True, "event": event, "heartbeat_tick": tick, "resume_requested": True}
    pending_card_return = _pending_card_return_blocker_for_event(run_root, str(run_state["run_id"]), event)
    if pending_card_return is not None:
        raise RouterError(
            "event blocked by unresolved card return: "
            f"waiting for {pending_card_return.get('card_return_event')} "
            f"from {pending_card_return.get('target_role')} "
            f"for card {pending_card_return.get('card_id')}; "
            "validate the expected return envelope before recording another role event"
        )
    payload = _normalize_record_event_payload(
        project_root,
        run_state,
        event=event,
        payload=payload,
        envelope_path=envelope_path,
        envelope_hash=envelope_hash,
    )
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        return _already_recorded_external_event_result(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
            scoped_identity=scoped_identity,
        )
    if required_flag and not run_state["flags"].get(required_flag):
        raise RouterError(f"event {event} requires {required_flag}")
    _check_scoped_event_retry_budget(run_state, scoped_identity)
    active_blocker = run_state.get("active_control_blocker")
    repeatable_pm_repair_decision = (
        event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT
        and isinstance(active_blocker, dict)
        and active_blocker.get("delivery_status") == "delivered"
        and active_blocker.get("handling_lane") in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES
    )
    repeatable_gate_decision = event == GATE_DECISION_EVENT
    repeatable_gate_outcome_block = event in GATE_OUTCOME_BLOCK_EVENTS
    repeatable_startup_repair_request = (
        event == "pm_requests_startup_repair"
        and run_state["flags"].get(flag)
        and run_state["flags"].get("startup_fact_reported")
        and run_state["flags"].get("pm_startup_activation_card_delivered")
    )
    repeatable_route_draft_repair = (
        event == "pm_writes_route_draft"
        and run_state["flags"].get(flag)
        and not run_state["flags"].get("route_activated_by_pm")
    )
    repeatable_current_node_completion = (
        event in {
            "pm_completes_current_node_from_reviewed_result",
            "pm_completes_parent_node_from_backward_replay",
        }
        and run_state["flags"].get(flag)
        and _active_node_completion_write_missing(run_root, run_state, payload)
    )
    repeatable_pm_role_work_request = event == PM_ROLE_WORK_REQUEST_EVENT
    repeatable_role_work_result = event == ROLE_WORK_RESULT_RETURNED_EVENT
    repeatable_pm_role_work_result_decision = event == PM_ROLE_WORK_RESULT_DECISION_EVENT
    repeatable_current_node_result = event == "worker_current_node_result_returned"
    scoped_event_has_active_repair_context = bool(
        scoped_identity
        and event == "pm_mutates_route_after_review_block"
        and _active_model_miss_review_block_flags(run_state)
    )
    if run_state["flags"].get(flag) and not scoped_event_has_active_repair_context and not (
        repeatable_pm_repair_decision
        or repeatable_gate_decision
        or repeatable_gate_outcome_block
        or repeatable_startup_repair_request
        or repeatable_route_draft_repair
        or repeatable_current_node_completion
        or repeatable_pm_role_work_request
        or repeatable_role_work_result
        or repeatable_pm_role_work_result_decision
        or repeatable_current_node_result
    ):
        return _already_recorded_external_event_result(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
            scoped_identity=scoped_identity,
        )
    payload = payload or {}
    if event in {"user_requests_run_stop", "user_requests_run_cancel"}:
        _write_run_lifecycle_request(project_root, run_root, run_state, event=event, payload=payload)
    elif event == "pm_activates_reviewed_route":
        _write_route_activation(project_root, run_root, run_state, payload)
    elif event == "pm_resume_recovery_decision_returned":
        _write_pm_resume_decision(project_root, run_root, run_state, payload)
    elif event == "host_records_heartbeat_binding":
        _write_host_heartbeat_binding(project_root, run_root, run_state, payload)
    elif event == "pm_writes_node_acceptance_plan":
        _write_node_acceptance_plan(project_root, run_root, run_state, payload)
    elif event == "pm_revises_node_acceptance_plan":
        _write_pm_revised_node_acceptance_plan(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_node_acceptance_plan":
        frontier = _active_frontier(run_root)
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=_active_node_root(run_root, frontier) / "reviews" / "node_acceptance_plan_review.json",
            schema_version="flowpilot.node_acceptance_plan_review.v1",
            checked_paths=[
                _active_node_acceptance_plan_path(run_root, frontier),
                run_root / "execution_frontier.json",
            ],
        )
    elif event == "reviewer_blocks_node_acceptance_plan":
        frontier = _active_frontier(run_root)
        _write_role_block_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=_active_node_root(run_root, frontier) / "reviews" / "node_acceptance_plan_block.json",
            schema_version="flowpilot.node_acceptance_plan_block.v1",
            checked_paths=[
                _active_node_acceptance_plan_path(run_root, frontier),
                run_root / "execution_frontier.json",
            ],
        )
        run_state["flags"]["node_acceptance_plan_reviewer_passed"] = False
        run_state["flags"]["node_acceptance_plan_revised_by_pm"] = False
    elif event == "reviewer_blocks_current_node_dispatch":
        frontier = _active_frontier(run_root)
        packet_id = str(frontier.get("active_packet_id") or run_state.get("current_node_packet_id") or "")
        checked_paths = [
            _active_node_acceptance_plan_path(run_root, frontier),
            run_root / "execution_frontier.json",
        ]
        if packet_id:
            checked_paths.append(run_root / "packets" / packet_id / "packet_envelope.json")
        _write_role_block_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=_active_node_root(run_root, frontier) / "reviews" / "current_node_dispatch_block.json",
            schema_version="flowpilot.current_node_dispatch_block.v1",
            checked_paths=checked_paths,
        )
        run_state["flags"]["current_node_dispatch_allowed"] = False
    elif event == "reviewer_reports_startup_facts":
        _write_startup_fact_report(project_root, run_root, run_state, payload)
    elif event == "pm_approves_startup_activation":
        _write_startup_activation(project_root, run_root, run_state, payload)
    elif event == "pm_requests_startup_repair":
        _write_startup_repair_request(project_root, run_root, run_state, payload)
    elif event == "pm_declares_startup_protocol_dead_end":
        _write_startup_protocol_dead_end(project_root, run_root, run_state, payload)
    elif event == "pm_issues_material_and_capability_scan_packets":
        _write_material_scan_packets(project_root, run_root, run_state, payload)
    elif event == "reviewer_blocks_material_scan_dispatch":
        _write_material_dispatch_block_report(project_root, run_root, run_state, payload)
    elif event in {"reviewer_blocks_material_scan_dispatch_recheck", "router_direct_material_scan_dispatch_recheck_blocked"}:
        _write_material_dispatch_block_report(project_root, run_root, run_state, payload)
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event in {"reviewer_protocol_blocker_material_scan_dispatch_recheck", "router_protocol_blocker_material_scan_dispatch_recheck"}:
        _write_material_dispatch_recheck_protocol_blocker(project_root, run_root, run_state, payload, event_name=event)
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event == "worker_scan_packet_bodies_delivered_after_dispatch":
        material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _validate_packet_bodies_opened_by_targets(project_root, run_state, material_index["packets"])
    elif event == "worker_scan_results_returned":
        material_index = _load_packet_index(_material_scan_index_path(run_root), label="material scan")
        _validate_results_exist_for_packets(project_root, run_state, material_index["packets"], next_recipient="human_like_reviewer")
        _mark_parallel_batch_results_joined(project_root, run_root, run_state, "material_scan")
    elif event == "reviewer_reports_material_sufficient":
        _write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=True)
        material_batch = _active_parallel_packet_batch(run_root, "material_scan")
        if material_batch:
            _mark_parallel_batch_reviewed(
                run_root,
                "material_scan",
                passed=True,
                reviewed_packet_ids=[str(record.get("packet_id")) for record in material_batch["packets"] if isinstance(record, dict)],
            )
    elif event == "reviewer_reports_material_insufficient":
        _write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=False)
        material_batch = _active_parallel_packet_batch(run_root, "material_scan")
        if material_batch:
            _mark_parallel_batch_reviewed(
                run_root,
                "material_scan",
                passed=False,
                reviewed_packet_ids=[str(record.get("packet_id")) for record in material_batch["packets"] if isinstance(record, dict)],
            )
    elif event == "pm_writes_research_package":
        _write_research_package(project_root, run_root, run_state, payload)
    elif event == "research_capability_decision_recorded":
        _write_research_capability_decision(project_root, run_root, run_state, payload)
    elif event == PM_ROLE_WORK_REQUEST_EVENT:
        _write_pm_role_work_request(project_root, run_root, run_state, payload)
    elif event == ROLE_WORK_RESULT_RETURNED_EVENT:
        _write_role_work_result_returned(project_root, run_root, run_state, payload)
    elif event == PM_ROLE_WORK_RESULT_DECISION_EVENT:
        _write_pm_role_work_result_decision(project_root, run_root, run_state, payload)
    elif event == "worker_research_report_returned":
        _write_worker_research_report(project_root, run_root, run_state, payload)
        _mark_parallel_batch_results_joined(project_root, run_root, run_state, "research")
    elif event == "reviewer_passes_research_direct_source_check":
        research_index = _load_packet_index(_research_packet_index_path(run_root), label="research")
        raw_agent_map = payload.get("agent_role_map")
        _validate_packet_group_for_reviewer(
            project_root,
            run_state,
            research_index["packets"],
            audit_path=run_root / "research" / "research_packet_review_audit.json",
            agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None,
        )
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "research" / "research_reviewer_report.json",
            schema_version="flowpilot.research_reviewer_report.v1",
            checked_paths=[run_root / "research" / "research_package.json", run_root / "research" / "worker_research_report.json"],
        )
        research_batch = _active_parallel_packet_batch(run_root, "research")
        if research_batch:
            _mark_parallel_batch_reviewed(
                run_root,
                "research",
                passed=True,
                reviewed_packet_ids=[str(record.get("packet_id")) for record in research_batch["packets"] if isinstance(record, dict)],
            )
    elif event == "pm_absorbs_reviewed_research":
        _write_pm_research_absorption(project_root, run_root, run_state)
    elif event == "pm_writes_material_understanding":
        _write_material_understanding(project_root, run_root, run_state, payload)
    elif event == "pm_writes_product_function_architecture":
        _write_product_function_architecture(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_product_architecture":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "product_architecture_challenge.json",
            schema_version="flowpilot.product_architecture_review.v1",
            checked_paths=[run_root / "product_function_architecture.json"],
        )
    elif event == "product_officer_passes_product_architecture_modelability":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "product_architecture_modelability.json",
            schema_version="flowpilot.product_architecture_modelability.v1",
            checked_paths=[run_root / "product_function_architecture.json"],
        )
    elif event == "pm_writes_root_acceptance_contract":
        _write_root_acceptance_contract(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_root_acceptance_contract":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "root_contract_challenge.json",
            schema_version="flowpilot.root_contract_review.v1",
            checked_paths=[run_root / "root_acceptance_contract.json", run_root / "standard_scenario_pack.json"],
        )
    elif event == "product_officer_passes_root_acceptance_contract_modelability":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "root_contract_modelability.json",
            schema_version="flowpilot.root_contract_modelability.v1",
            checked_paths=[
                run_root / "root_acceptance_contract.json",
                run_root / "standard_scenario_pack.json",
                run_root / "reviews" / "root_contract_challenge.json",
            ],
        )
    elif event == "pm_freezes_root_acceptance_contract":
        _freeze_root_acceptance_contract(project_root, run_root, run_state)
    elif event == "pm_records_dependency_policy":
        _write_dependency_policy(project_root, run_root, run_state, payload)
    elif event == "pm_writes_capabilities_manifest":
        _write_capabilities_manifest(project_root, run_root, run_state, payload)
    elif event == "pm_writes_child_skill_selection":
        _write_child_skill_selection(project_root, run_root, run_state, payload)
    elif event == "pm_writes_child_skill_gate_manifest":
        _write_child_skill_gate_manifest(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_child_skill_gate_manifest":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "child_skill_gate_manifest_review.json",
            schema_version="flowpilot.child_skill_gate_manifest_review.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "pm_child_skill_selection.json",
                run_root / "capabilities.json",
            ],
        )
        _sync_child_skill_manifest_review_approval(project_root, run_root)
    elif event == "process_officer_passes_child_skill_conformance_model":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="process_flowguard_officer",
            path=run_root / "flowguard" / "child_skill_conformance_model.json",
            schema_version="flowpilot.child_skill_conformance_model.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "reviews" / "child_skill_gate_manifest_review.json",
            ],
        )
    elif event == "product_officer_passes_child_skill_product_fit":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="product_flowguard_officer",
            path=run_root / "flowguard" / "child_skill_product_fit.json",
            schema_version="flowpilot.child_skill_product_fit.v1",
            checked_paths=[
                run_root / "child_skill_gate_manifest.json",
                run_root / "flowguard" / "child_skill_conformance_model.json",
                run_root / "product_function_architecture.json",
                run_root / "root_acceptance_contract.json",
            ],
        )
    elif event == "pm_approves_child_skill_manifest_for_route":
        _approve_child_skill_manifest_for_route(project_root, run_root, run_state, payload)
    elif event == "capability_evidence_synced":
        _sync_capability_evidence(project_root, run_root, run_state, payload)
    elif event == "pm_writes_route_draft":
        if repeatable_route_draft_repair:
            _reset_route_review_after_route_draft_repair(run_state)
        _write_route_draft(project_root, run_root, run_state, payload)
    elif event == "process_officer_passes_route_check":
        _write_route_process_pass_report(project_root, run_root, run_state, payload)
    elif event == "process_officer_requires_route_repair":
        _write_route_process_issue_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_verdict="repair_required",
        )
    elif event == "process_officer_blocks_route_check":
        _write_route_process_issue_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_verdict="blocked",
        )
    elif event == "product_officer_passes_route_check":
        _write_route_product_pass_report(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_route_check":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "route_challenge.json",
            schema_version="flowpilot.route_review.v1",
            checked_paths=[
                _current_route_draft_path(run_root),
                run_root / "flowguard" / "route_process_check.json",
                run_root / "flowguard" / "route_product_check.json",
            ],
        )
    elif event == "pm_registers_current_node_packet":
        _validate_current_node_packet_event(project_root, run_root, run_state, payload)
    elif event == "worker_current_node_result_returned":
        _validate_current_node_result_event(project_root, run_state, payload)
    elif event == "current_node_reviewer_passes_result":
        _validate_current_node_reviewer_pass(project_root, run_state, payload)
    elif event == "pm_builds_parent_backward_targets":
        _write_parent_backward_targets(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_parent_backward_replay":
        _write_parent_backward_replay(project_root, run_root, run_state, payload)
    elif event == "pm_records_parent_segment_decision":
        parent_segment_decision = _write_parent_segment_decision(project_root, run_root, run_state, payload)
    elif event == "pm_completes_current_node_from_reviewed_result":
        _mark_frontier_node_completed(project_root, run_root, run_state, payload)
    elif event == "pm_completes_parent_node_from_backward_replay":
        _mark_frontier_node_completed(
            project_root,
            run_root,
            run_state,
            payload,
            source_event="pm_completes_parent_node_from_backward_replay",
        )
    elif event == "pm_records_evidence_quality_package":
        _write_evidence_quality_package(project_root, run_root, run_state, payload)
    elif event == "reviewer_passes_evidence_quality_package":
        _write_role_gate_report(
            project_root,
            run_root,
            run_state,
            payload,
            expected_role="human_like_reviewer",
            path=run_root / "reviews" / "evidence_quality_review.json",
            schema_version="flowpilot.evidence_quality_review.v1",
            checked_paths=[
                run_root / "evidence" / "evidence_ledger.json",
                run_root / "generated_resource_ledger.json",
                run_root / "quality" / "quality_package.json",
            ],
        )
    elif event == "pm_records_final_route_wide_ledger_clean":
        _write_final_route_wide_ledger(project_root, run_root, run_state, payload)
    elif event == "reviewer_final_backward_replay_passed":
        _write_terminal_backward_replay(project_root, run_root, run_state, payload)
    elif event in GATE_OUTCOME_BLOCK_EVENTS:
        _write_gate_outcome_block_report(project_root, run_root, run_state, payload, event=event)
    elif event == "pm_mutates_route_after_review_block":
        if not run_state["flags"].get("model_miss_triage_closed"):
            raise RouterError("review-block repair or route mutation requires closed model-miss triage first")
        _write_pm_review_block_repair(project_root, run_root, run_state, payload)
    elif event == PM_MODEL_MISS_TRIAGE_DECISION_EVENT:
        model_miss_triage_decision = _write_model_miss_triage_decision(project_root, run_root, run_state, payload)
    elif event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        _write_control_blocker_repair_decision(project_root, run_root, run_state, payload)
    elif event == GATE_DECISION_EVENT:
        _write_gate_decision(project_root, run_root, run_state, payload)
    elif event == "pm_approves_terminal_closure":
        _write_terminal_closure_suite(project_root, run_root, run_state, payload)
    elif event == "pm_accepts_reviewed_material":
        if run_state.get("material_review") != "sufficient":
            raise RouterError("PM can accept material only after a sufficient reviewer material report")
    elif event == "pm_requests_research_after_material_insufficient":
        if run_state.get("material_review") != "insufficient":
            raise RouterError("PM can request research on this path only after an insufficient reviewer material report")
    for clear_flag in GATE_OUTCOME_PASS_CLEAR_FLAGS.get(event, ()):
        run_state.setdefault("flags", {})[clear_flag] = False
    _clear_active_gate_outcome_block_for_pass(run_state, event=event)
    record = {
        "event": event,
        "summary": meta["summary"],
        "payload": payload,
        "recorded_at": utc_now(),
    }
    run_state["flags"][flag] = True
    if event in {
        "pm_completes_current_node_from_reviewed_result",
        "pm_completes_parent_node_from_backward_replay",
    } and _node_completion_event_advanced_to_next_node(
        run_root,
        payload,
    ):
        run_state["flags"][flag] = False
    if event in MODEL_MISS_REVIEW_BLOCK_EVENTS:
        run_state["flags"]["pm_model_miss_triage_card_delivered"] = False
        run_state["flags"]["model_miss_triage_closed"] = False
        run_state["flags"]["pm_review_repair_card_delivered"] = False
        run_state["model_miss_triage"] = None
        run_state["model_miss_triage_followup_request"] = None
        run_state["model_miss_evidence_followup_request"] = None
        run_state["model_miss_triage_controlled_stop"] = None
        run_state["flags"]["model_miss_triage_followup_request_pending"] = False
        run_state["flags"]["model_miss_triage_controlled_stop_recorded"] = False
    if (
        event == PM_MODEL_MISS_TRIAGE_DECISION_EVENT
        and model_miss_triage_decision not in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES
    ):
        run_state["flags"][flag] = False
    if event == "pm_records_parent_segment_decision" and (parent_segment_decision or "continue") != "continue":
        run_state["flags"][flag] = False
    if event == "pm_absorbs_reviewed_research":
        run_state["flags"]["material_accepted_by_pm"] = True
    run_state["events"].append(record)
    _mark_scoped_event_recorded(run_state, scoped_identity)
    if event in {"router_direct_material_scan_dispatch_recheck_passed", "reviewer_allows_material_scan_dispatch"}:
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
        run_state["flags"]["material_scan_dispatch_blocked"] = False
        run_state["material_dispatch_block"] = None
    else:
        _finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    if event == "reviewer_reports_material_sufficient":
        run_state["material_review"] = "sufficient"
    elif event == "reviewer_reports_material_insufficient":
        run_state["material_review"] = "insufficient"
    append_history(run_state, event, payload)
    role_memory_delta = _append_role_memory_delta(run_root, run_state, event=event, payload=payload)
    if role_memory_delta is not None:
        deltas = run_state.setdefault("role_memory_deltas", [])
        deltas.append(role_memory_delta)
        run_state["role_memory_deltas"] = deltas[-32:]
    _resolve_delivered_control_blocker(project_root, run_root, run_state, resolved_by_event=event)
    run_state["pending_action"] = None
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_external_event:{event}")
    _sync_derived_run_views(project_root, run_root, run_state, reason=f"after_external_event:{event}")
    save_run_state(run_root, run_state)
    return {"ok": True, "event": event}


def record_external_event(
    project_root: Path,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    try:
        return _record_external_event_unchecked(
            project_root,
            event,
            payload,
            envelope_path=envelope_path,
            envelope_hash=envelope_hash,
        )
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.record_external_event",
            error_message=str(exc),
            event=event,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def apply_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == action_type:
        return apply_bootloader_action(project_root, action_type, payload)
    try:
        return apply_controller_action(project_root, action_type, payload)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.apply_controller_action",
            error_message=str(exc),
            action_type=action_type,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def run_until_wait(project_root: Path, *, max_steps: int = 50, new_invocation: bool = False) -> dict[str, Any]:
    if max_steps < 1:
        raise RouterError("run-until-wait requires max_steps >= 1")
    applied_actions: list[dict[str, Any]] = []
    start_new = new_invocation
    for _ in range(max_steps):
        action = next_action(project_root, new_invocation=start_new)
        start_new = False
        action_type = str(action.get("action_type") or "")
        action_crosses_boundary = (
            action_type not in SAFE_RUN_UNTIL_WAIT_ACTION_TYPES
            or bool(action.get("requires_user"))
            or bool(action.get("requires_payload"))
            or bool(action.get("requires_user_dialog_display_confirmation"))
            or bool(action.get("requires_host_spawn"))
            or bool(action.get("requires_host_automation"))
            or bool(action.get("card_id"))
        )
        if action_crosses_boundary:
            result = dict(action)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "requires_user_host_or_role_boundary"
            return result
        applied = apply_action(project_root, action_type, {})
        applied_actions.append({"action_type": action_type, "result": applied})
        if applied.get("waiting") or applied.get("terminal"):
            result = dict(applied)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "terminal_or_waiting_action_applied"
            return result
    raise RouterError("run-until-wait reached max_steps before a wait boundary")


def _repair_role_output_envelope_hashes(project_root: Path, run_root: Path) -> int:
    repaired = 0
    for path in sorted(run_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        envelope = payload.get("_role_output_envelope")
        if not isinstance(envelope, dict):
            continue
        body_path = envelope.get("body_path")
        if not isinstance(body_path, str):
            continue
        resolved = resolve_project_path(project_root, body_path)
        if not resolved.exists():
            continue
        raw_hash, semantic_hash = _role_output_hashes(resolved)
        replay_hash = semantic_hash or raw_hash
        accepted_hashes = {raw_hash}
        accepted_hashes.update(_role_output_semantic_hashes(resolved))
        if envelope.get("body_hash") not in accepted_hashes and resolved.resolve() == path.resolve():
            payload.update(
                _role_output_envelope_record_for_mutable_artifact(
                    project_root,
                    run_root,
                    path,
                    payload,
                    reason="reconcile_mutable_artifact_role_output_hash",
                )
            )
            write_json(path, payload)
            repaired += 1
            continue
        if (
            envelope.get("body_hash") == replay_hash
            and envelope.get("body_raw_sha256") == raw_hash
            and envelope.get("body_semantic_sha256") == semantic_hash
        ):
            continue
        envelope["body_hash"] = replay_hash
        envelope["body_raw_sha256"] = raw_hash
        envelope["body_semantic_sha256"] = semantic_hash
        payload["_role_output_envelope"] = envelope
        write_json(path, payload)
        repaired += 1
    return repaired


def _reconciled_card_delivery_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    delivery: dict[str, Any],
    manifest: dict[str, Any],
    entries: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    card_id = str(delivery.get("card_id") or "")
    if card_id not in CARD_PHASE_BY_ID and card_id not in CARD_REQUIRED_SOURCE_PATHS:
        return None
    entry = entries.get(card_id)
    if entry is None:
        return None
    card = manifest_card(manifest, card_id)
    previous = delivery.get("delivery_context") if isinstance(delivery.get("delivery_context"), dict) else {}
    context = _live_card_delivery_context(project_root, run_root, run_state, entry, card)
    context["context_reconciled_at"] = utc_now()
    context["context_reconciled_reason"] = "current_run_state_reconciliation"
    if isinstance(previous, dict):
        context["original_current_stage"] = previous.get("current_stage")
    return context


def _repair_prompt_delivery_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> int:
    manifest = load_manifest_from_run(run_root)
    entries = {entry["card_id"]: entry for entry in SYSTEM_CARD_SEQUENCE}
    repaired = 0

    def repair_list(deliveries: list[Any]) -> int:
        count = 0
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                continue
            context = _reconciled_card_delivery_context(project_root, run_root, run_state, delivery, manifest, entries)
            if context is None:
                continue
            if delivery.get("delivery_context") != context:
                delivery["delivery_context"] = context
                count += 1
        return count

    repaired += repair_list(run_state.setdefault("delivered_cards", []))
    ledger_path = run_root / "prompt_delivery_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    deliveries = ledger.get("deliveries") if isinstance(ledger.get("deliveries"), list) else []
    ledger_repairs = repair_list(deliveries)
    if ledger_repairs:
        ledger["deliveries"] = deliveries
        ledger["updated_at"] = utc_now()
        write_json(ledger_path, ledger)
    return repaired + ledger_repairs


def _sync_current_and_index_status(project_root: Path, run_state: dict[str, Any]) -> None:
    now = utc_now()
    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("current_run_id") == run_state.get("run_id"):
        current["status"] = run_state.get("status") or current.get("status")
        current["updated_at"] = now
        write_json(current_path, current)
    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = run_state.get("status") or item.get("status")
            item["updated_at"] = now
    if runs:
        index["runs"] = runs
        index["updated_at"] = now
        write_json(index_path, index)


def _repair_legacy_material_packet_contracts(project_root: Path, run_root: Path) -> int:
    index_path = _material_scan_index_path(run_root)
    index = read_json_if_exists(index_path)
    ledger_path = run_root / "packet_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    if not isinstance(index, dict) and not isinstance(ledger, dict):
        return 0

    run_id = str(
        (index.get("run_id") if isinstance(index, dict) else None)
        or (ledger.get("run_id") if isinstance(ledger, dict) else None)
        or run_root.name
    )
    ledger_packets = ledger.get("packets") if isinstance(ledger, dict) and isinstance(ledger.get("packets"), list) else []
    ledger_by_id = {
        str(packet.get("packet_id")): packet
        for packet in ledger_packets
        if isinstance(packet, dict) and packet.get("packet_id")
    }

    records_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(index, dict):
        for list_name in ("packets", "superseded_packets"):
            for record in index.get(list_name, []) if isinstance(index.get(list_name), list) else []:
                if isinstance(record, dict) and record.get("packet_id"):
                    records_by_id[str(record["packet_id"])] = record
    for packet in ledger_packets:
        if not isinstance(packet, dict):
            continue
        packet_id = str(packet.get("packet_id") or "")
        packet_type = str(packet.get("packet_type") or packet.get("packet_envelope", {}).get("packet_type") or "")
        if packet_id and (packet_type == "material_scan" or packet_id.startswith("material-scan")):
            records_by_id.setdefault(packet_id, {})

    changed_index = False
    changed_ledger = False
    repaired: list[dict[str, Any]] = []
    repaired_at = utc_now()

    for packet_id, record in sorted(records_by_id.items()):
        paths = packet_runtime.packet_paths(project_root, packet_id, run_id)
        ledger_record = ledger_by_id.get(packet_id, {})
        result_body_rel = str(
            record.get("result_body_path")
            or ledger_record.get("result_body_path")
            or project_relative(project_root, paths["result_body"])
        )
        result_envelope_rel = str(
            record.get("result_envelope_path")
            or ledger_record.get("result_envelope_path")
            or project_relative(project_root, paths["result_envelope"])
        )
        envelope_rel = str(
            record.get("packet_envelope_path")
            or ledger_record.get("packet_envelope_path")
            or project_relative(project_root, paths["packet_envelope"])
        )
        envelope_path = resolve_project_path(project_root, envelope_rel)
        envelope = read_json_if_exists(envelope_path)
        if not isinstance(envelope, dict):
            continue

        envelope_changed = False
        for key, value in (
            ("result_body_path", result_body_rel),
            ("expected_result_body_path", result_body_rel),
            ("write_target_path", result_body_rel),
            ("result_envelope_path", result_envelope_rel),
            ("expected_result_envelope_path", result_envelope_rel),
        ):
            if envelope.get(key) != value:
                envelope[key] = value
                envelope_changed = True
        target = {"result_envelope_path": result_envelope_rel, "result_body_path": result_body_rel}
        if envelope.get("result_write_target") != target:
            envelope["result_write_target"] = target
            envelope_changed = True

        metadata = envelope.get("metadata") if isinstance(envelope.get("metadata"), dict) else {}
        metadata_updates = {
            "expected_result_body_path": result_body_rel,
            "expected_result_envelope_path": result_envelope_rel,
            "write_target_path": result_body_rel,
        }
        for key, value in metadata_updates.items():
            if metadata.get(key) != value:
                metadata[key] = value
                envelope_changed = True
        if metadata:
            envelope["metadata"] = metadata

        output_contract = envelope.get("output_contract") if isinstance(envelope.get("output_contract"), dict) else None
        if isinstance(output_contract, dict):
            contract = dict(output_contract)
            for key, value in metadata_updates.items():
                if contract.get(key) != value:
                    contract[key] = value
                    envelope_changed = True
            if contract != output_contract:
                envelope["output_contract"] = contract

        replacement_for = record.get("replacement_for") or metadata.get("replacement_for") or ledger_record.get("replacement_for")
        if replacement_for and not envelope.get("replacement_for"):
            envelope["replacement_for"] = replacement_for
            envelope_changed = True
        if replacement_for and not envelope.get("supersedes"):
            envelope["supersedes"] = [replacement_for]
            envelope_changed = True

        if envelope_changed:
            envelope["legacy_material_packet_contract_migration"] = {
                "schema_version": "flowpilot.legacy_material_packet_contract_migration.v1",
                "sealed_packet_body_not_read": True,
                "sealed_packet_body_not_rewritten": True,
                "envelope_result_write_target_backfilled": True,
                "body_hash_preserved": True,
                "migrated_at": repaired_at,
            }
            write_json(envelope_path, envelope)
            repaired.append(
                {
                    "packet_id": packet_id,
                    "packet_envelope_path": project_relative(project_root, envelope_path),
                    "result_body_path": result_body_rel,
                    "result_envelope_path": result_envelope_rel,
                    "sealed_packet_body_not_read": True,
                    "sealed_packet_body_not_rewritten": True,
                }
            )

        if record:
            for key, value in (
                ("packet_envelope_path", project_relative(project_root, envelope_path)),
                ("result_body_path", result_body_rel),
                ("result_envelope_path", result_envelope_rel),
                ("expected_result_body_path", result_body_rel),
                ("write_target_path", result_body_rel),
            ):
                if record.get(key) != value:
                    record[key] = value
                    changed_index = True
            target = {"result_envelope_path": result_envelope_rel, "result_body_path": result_body_rel}
            if record.get("result_write_target") != target:
                record["result_write_target"] = target
                changed_index = True

        if ledger_record:
            for key, value in (
                ("result_body_path", result_body_rel),
                ("result_envelope_path", result_envelope_rel),
                ("expected_result_body_path", result_body_rel),
                ("write_target_path", result_body_rel),
            ):
                if ledger_record.get(key) != value:
                    ledger_record[key] = value
                    changed_ledger = True
            if ledger_record.get("result_write_target") != target:
                ledger_record["result_write_target"] = target
                changed_ledger = True
            packet_envelope = ledger_record.get("packet_envelope") if isinstance(ledger_record.get("packet_envelope"), dict) else {}
            for key, value in (
                ("result_body_path", result_body_rel),
                ("result_envelope_path", result_envelope_rel),
                ("expected_result_body_path", result_body_rel),
                ("write_target_path", result_body_rel),
            ):
                if packet_envelope.get(key) != value:
                    packet_envelope[key] = value
                    changed_ledger = True
            if packet_envelope:
                ledger_record["packet_envelope"] = packet_envelope

    if changed_index and isinstance(index, dict):
        index["updated_at"] = repaired_at
        write_json(index_path, index)
    if changed_ledger and isinstance(ledger, dict):
        ledger["updated_at"] = repaired_at
        write_json(ledger_path, ledger)
    if repaired:
        write_json(
            run_root / "material" / "legacy_material_packet_migration.json",
            {
                "schema_version": "flowpilot.legacy_material_packet_contract_migration.v1",
                "run_id": run_id,
                "packet_count": len(repaired),
                "packets": repaired,
                "sealed_packet_bodies_read": False,
                "sealed_packet_bodies_rewritten": False,
                "migrated_at": repaired_at,
            },
        )
    return len(repaired)


def reconcile_current_run(project_root: Path) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    repaired: dict[str, Any] = {
        "prompt_delivery_contexts": 0,
        "role_output_envelope_hashes": 0,
        "terminal_lifecycle": False,
        "terminal_lifecycle_record_written": False,
        "terminal_closure_status_recovered": False,
        "legacy_material_packet_contracts": 0,
        "non_current_running_index_entries": 0,
    }
    status = str(run_state.get("status") or "")
    flags = run_state.setdefault("flags", {})
    if status == "stopped_by_user":
        flags["run_stopped_by_user"] = True
    elif status == "cancelled_by_user":
        flags["run_cancelled_by_user"] = True
    elif status not in RUN_TERMINAL_STATUSES and _terminal_closure_suite_is_closed(run_root):
        run_state["status"] = "closed"
        flags["terminal_closure_approved"] = True
        status = "closed"
        repaired["terminal_closure_status_recovered"] = True
    mode = _terminal_lifecycle_mode(run_state)
    if mode:
        run_state["status"] = mode
        run_state["phase"] = "terminal"
        run_state["holder"] = "controller"
        run_state["pending_action"] = None
        reconciliation = _reconcile_terminal_lifecycle_authorities(
            project_root,
            run_root,
            run_state,
            mode=mode,
            event="reconcile_current_run",
        )
        lifecycle_path = _lifecycle_record_path(run_root)
        if not lifecycle_path.exists():
            write_json(
                lifecycle_path,
                {
                    "schema_version": "flowpilot.run_lifecycle.v1",
                    "run_id": run_state.get("run_id"),
                    "status": mode,
                    "request_event": "reconcile_current_run",
                    "reason": "terminal_lifecycle_reconciled_from_existing_authorities",
                    "controller_may_continue_route_work": False,
                    "controller_may_spawn_new_role_work": False,
                    "reconciliation": reconciliation,
                    "reconciled_at": utc_now(),
                },
            )
            append_history(
                run_state,
                "run_lifecycle_record_written_by_reconcile",
                {"lifecycle_path": project_relative(project_root, lifecycle_path), "status": mode},
            )
            repaired["terminal_lifecycle_record_written"] = True
        _sync_current_and_index_status(project_root, run_state)
        repaired["terminal_lifecycle"] = True
    repaired["prompt_delivery_contexts"] = _repair_prompt_delivery_contexts(project_root, run_root, run_state)
    repaired["role_output_envelope_hashes"] = _repair_role_output_envelope_hashes(project_root, run_root)
    repaired["legacy_material_packet_contracts"] = _repair_legacy_material_packet_contracts(project_root, run_root)
    _refresh_route_memory(project_root, run_root, run_state, trigger="reconcile_current_run")
    repaired["non_current_running_index_entries"] = _reconcile_non_current_running_index_entries(project_root, run_state)
    _sync_derived_run_views(project_root, run_root, run_state, reason="reconcile_current_run")
    append_history(run_state, "router_reconciled_current_run", repaired)
    save_run_state(run_root, run_state)
    return {
        "ok": True,
        "run_id": run_state.get("run_id"),
        "run_root": project_relative(project_root, run_root),
        "repaired": repaired,
    }


def write_role_output_envelope(
    project_root: Path,
    *,
    output_path: str,
    body: dict[str, Any] | None = None,
    body_file: str | None = None,
    path_key: str = "report_path",
    hash_key: str = "report_hash",
    event_name: str | None = None,
    from_role: str | None = None,
    to_role: str = "controller",
) -> dict[str, Any]:
    if path_key not in {"body_path", "report_path", "decision_path", "result_body_path"}:
        raise RouterError(f"unsupported role envelope path key: {path_key}")
    if hash_key not in {"body_hash", "report_hash", "decision_hash", "result_body_hash"}:
        raise RouterError(f"unsupported role envelope hash key: {hash_key}")
    path = resolve_project_path(project_root, output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if body_file:
        source_path = resolve_project_path(project_root, body_file)
        if not source_path.exists():
            raise RouterError(f"role output body file is missing: {body_file}")
        path.write_bytes(source_path.read_bytes())
    elif body is not None:
        write_json(path, body)
    elif not path.exists():
        raise RouterError("role output envelope requires body-json, body-file, or an existing output path")
    raw_hash, semantic_hash = _role_output_hashes(path)
    body_hash = semantic_hash or raw_hash
    envelope = {
        "schema_version": ROLE_OUTPUT_ENVELOPE_SCHEMA,
        path_key: project_relative(project_root, path),
        hash_key: body_hash,
        "controller_visibility": "role_output_envelope_only",
        "chat_response_body_allowed": False,
        "from_role": from_role,
        "to_role": to_role,
    }
    if event_name:
        envelope["event_name"] = event_name
    return envelope


def _artifact_issue(field: str, message: str, repair_owner: str = "project_manager") -> dict[str, str]:
    return {"field": field, "message": message, "repair_owner": repair_owner}


def _validate_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != str(raw_hash):
        issues.append(_artifact_issue(hash_key, "hash does not match file content", "artifact_author"))
    return issues


def _validate_role_output_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual, semantic = _role_output_hashes(path)
    accepted = {actual}
    accepted.update(_role_output_semantic_hashes(path))
    if str(raw_hash) not in accepted:
        issues.append(_artifact_issue(hash_key, "hash does not match role output content", "artifact_author"))
    return issues


def validate_artifact(project_root: Path, artifact_type: str, artifact_path: str) -> dict[str, Any]:
    path = resolve_project_path(project_root, artifact_path)
    payload = read_json(path)
    issues: list[dict[str, str]] = []
    if artifact_type == "node_acceptance_plan":
        required_top = ("schema_version", "run_id", "route_id", "route_version", "node_id", "node_requirements", "experiment_plan", "high_standard_recheck", "prior_path_context_review")
        for field in required_top:
            if field not in payload or payload.get(field) in (None, "", []):
                issues.append(_artifact_issue(field, "missing required field", "project_manager"))
        high_standard = payload.get("high_standard_recheck") if isinstance(payload.get("high_standard_recheck"), dict) else {}
        for field in (
            "ideal_outcome",
            "unacceptable_outcomes",
            "higher_standard_opportunities",
            "semantic_downgrade_risks",
            "decision",
            "why_current_plan_meets_highest_reasonable_standard",
        ):
            if field not in high_standard or high_standard.get(field) in (None, "", []):
                issues.append(_artifact_issue(f"high_standard_recheck.{field}", "missing required field", "project_manager"))
        prior = payload.get("prior_path_context_review") if isinstance(payload.get("prior_path_context_review"), dict) else {}
        for field in (
            "reviewed",
            "source_paths",
            "completed_nodes_considered",
            "superseded_nodes_considered",
            "stale_evidence_considered",
            "prior_blocks_or_experiments_considered",
            "impact_on_decision",
        ):
            if field not in prior:
                issues.append(_artifact_issue(f"prior_path_context_review.{field}", "missing required field", "project_manager"))
    elif artifact_type == "packet_envelope":
        envelope = packet_runtime.normalize_envelope_aliases(payload)
        for field in ("schema_version", "packet_id", "from_role", "to_role", "node_id", "body_path", "body_hash", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required packet envelope field", str(envelope.get("from_role") or "project_manager")))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "packet body must stay sealed to target role", str(envelope.get("from_role") or "project_manager")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "body_path", "body_hash"))
        if envelope.get("packet_type") != "user_intake":
            audit = packet_runtime.validate_packet_ready_for_direct_relay(
                project_root,
                packet_envelope=envelope,
                envelope_path=path,
            )
            for blocker in audit.get("blockers") or []:
                issues.append(_artifact_issue("direct_dispatch_preflight", str(blocker), str(envelope.get("from_role") or "project_manager")))
    elif artifact_type == "result_envelope":
        envelope = packet_runtime.normalize_envelope_aliases(payload)
        for field in ("schema_version", "packet_id", "completed_by_role", "result_body_path", "result_body_hash", "next_recipient", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required result envelope field", str(envelope.get("completed_by_role") or "worker")))
        if envelope.get("completed_by_role") == "controller":
            issues.append(_artifact_issue("completed_by_role", "Controller cannot author current-node results", "worker"))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "result body must stay sealed to reviewer/PM recipient", str(envelope.get("completed_by_role") or "worker")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "result_body_path", "result_body_hash"))
    elif artifact_type == "role_output_envelope":
        path_keys = ("body_path", "report_path", "decision_path", "result_body_path", "memo_path", "architecture_path", "contract_path", "manifest_path", "route_path", "draft_path", "plan_path", "package_path", "ledger_path")
        found = False
        body_ref = payload.get("body_ref") if isinstance(payload.get("body_ref"), dict) else None
        if body_ref and body_ref.get("path"):
            found = True
            if body_ref.get("hash"):
                ref_payload = {"body_path": body_ref.get("path"), "body_hash": body_ref.get("hash")}
                issues.extend(_validate_role_output_hash_if_present(project_root, ref_payload, "body_path", "body_hash"))
            else:
                issues.append(_artifact_issue("body_ref.hash", "role output envelope body_ref requires hash", str(payload.get("from_role") or "role")))
        for path_key in path_keys:
            if payload.get(path_key):
                hash_key = path_key[:-5] + "_hash" if path_key.endswith("_path") else f"{path_key}_hash"
                found = True
                if payload.get(hash_key):
                    issues.extend(_validate_role_output_hash_if_present(project_root, payload, path_key, hash_key))
        if not found:
            issues.append(_artifact_issue("path", "role output envelope must include a known artifact path field", str(payload.get("from_role") or "role")))
        if not payload.get("from_role"):
            issues.append(_artifact_issue("from_role", "missing producing role", "role"))
        if not payload.get("to_role"):
            issues.append(_artifact_issue("to_role", "missing recipient role", "role"))
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, payload)
        except role_output_runtime.RoleOutputRuntimeError as exc:
            issues.append(_artifact_issue("role_output_runtime_receipt", str(exc), str(payload.get("from_role") or "role")))
    elif artifact_type == "gate_decision":
        decision = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else payload
        issues.extend(_gate_decision_issues(project_root, decision))
    else:
        raise RouterError(f"unsupported artifact validation type: {artifact_type}")
    return {
        "ok": not issues,
        "artifact_type": artifact_type,
        "artifact_path": project_relative(project_root, path),
        "issue_count": len(issues),
        "errors": issues,
        "next_action": None if not issues else f"repair_{artifact_type}",
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FlowPilot prompt-isolated router.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    sub = parser.add_subparsers(dest="command", required=True)
    next_parser = sub.add_parser("next", help="Return the next router-authorized action")
    next_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    next_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    run_wait_parser = sub.add_parser("run-until-wait", help="Apply safe internal router actions and return the next wait-boundary action")
    run_wait_parser.add_argument("--max-steps", type=int, default=50)
    run_wait_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    run_wait_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    apply_parser = sub.add_parser("apply", help="Apply a pending router action")
    apply_parser.add_argument("--action-type", required=True)
    apply_parser.add_argument("--payload-json", default="")
    apply_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    event_parser = sub.add_parser("record-event", help="Record a PM/reviewer/worker external event")
    event_parser.add_argument("--event", required=True)
    event_parser.add_argument("--payload-json", default="")
    event_parser.add_argument("--envelope-path", default="", help="Project-local controller-visible event envelope path")
    event_parser.add_argument("--envelope-hash", default="", help="Expected sha256 for --envelope-path")
    event_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    envelope_parser = sub.add_parser("role-output-envelope", help="Write a role output body and return a controller-visible envelope")
    envelope_parser.add_argument("--output-path", required=True)
    envelope_parser.add_argument("--body-json", default="")
    envelope_parser.add_argument("--body-file", default="")
    envelope_parser.add_argument("--path-key", default="report_path")
    envelope_parser.add_argument("--hash-key", default="report_hash")
    envelope_parser.add_argument("--event-name", default="")
    envelope_parser.add_argument("--from-role", default="")
    envelope_parser.add_argument("--to-role", default="controller")
    envelope_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    validate_parser = sub.add_parser("validate-artifact", help="Validate a FlowPilot artifact before or during record-event")
    validate_parser.add_argument("--type", required=True, choices=["node_acceptance_plan", "packet_envelope", "result_envelope", "role_output_envelope", "gate_decision"])
    validate_parser.add_argument("--path", required=True)
    validate_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    reconcile_parser = sub.add_parser("reconcile-run", help="Rebuild derived indexes and live-run views for the current run")
    reconcile_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    state_parser = sub.add_parser("state", help="Print bootstrap and current run router state")
    state_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    try:
        if args.command == "next":
            result = next_action(root, new_invocation=bool(getattr(args, "new_invocation", False)))
        elif args.command == "run-until-wait":
            result = run_until_wait(
                root,
                max_steps=int(args.max_steps),
                new_invocation=bool(getattr(args, "new_invocation", False)),
            )
        elif args.command == "apply":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = apply_action(root, args.action_type, payload)
        elif args.command == "record-event":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = record_external_event(
                root,
                args.event,
                payload,
                envelope_path=args.envelope_path or None,
                envelope_hash=args.envelope_hash or None,
            )
        elif args.command == "role-output-envelope":
            body = json.loads(args.body_json) if args.body_json else None
            result = write_role_output_envelope(
                root,
                output_path=args.output_path,
                body=body,
                body_file=args.body_file or None,
                path_key=args.path_key,
                hash_key=args.hash_key,
                event_name=args.event_name or None,
                from_role=args.from_role or None,
                to_role=args.to_role,
            )
        elif args.command == "validate-artifact":
            result = validate_artifact(root, args.type, args.path)
        elif args.command == "reconcile-run":
            result = reconcile_current_run(root)
        elif args.command == "state":
            bootstrap = load_bootstrap_state(root, create_if_missing=False)
            run_state, run_root = load_run_state(root, bootstrap)
            active_ui_task_catalog = (
                _active_ui_task_catalog(root, run_root, run_state)
                if run_state is not None and run_root is not None
                else {"schema_version": "flowpilot.active_ui_task_catalog.v1", "active_tasks": []}
            )
            result = {
                "bootstrap": bootstrap,
                "run_root": str(run_root) if run_root else None,
                "run_state": run_state,
                "active_ui_task_catalog": active_ui_task_catalog,
            }
        else:
            raise RouterError(f"unknown command: {args.command}")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error = {"ok": False, "error": str(exc)}
        control_blocker = getattr(exc, "control_blocker", None)
        if isinstance(control_blocker, dict):
            error["control_blocker"] = control_blocker
            error["blocker_artifact_path"] = control_blocker.get("blocker_artifact_path")
            error["handling_lane"] = control_blocker.get("handling_lane")
            error["controller_instruction"] = control_blocker.get("controller_instruction")
            if isinstance(control_blocker.get("skill_observation_reminder"), dict):
                error["skill_observation_reminder"] = control_blocker["skill_observation_reminder"]
        if "skill_observation_reminder" not in error and args.command in {"apply", "record-event"}:
            error["skill_observation_reminder"] = _skill_observation_reminder(
                str(exc),
                event=getattr(args, "event", None),
                action_type=getattr(args, "action_type", None),
            )
        print(json.dumps(error, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
