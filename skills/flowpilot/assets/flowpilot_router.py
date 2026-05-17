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
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import flowpilot_user_flow_diagram
import card_runtime
import packet_runtime
import role_output_runtime
import flowpilot_runtime_closure
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_identity
import flowpilot_router_event_intake
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_route
import flowpilot_router_runtime_state
import flowpilot_router_startup_flow
import flowpilot_router_controller_scheduler
import flowpilot_router_work_packets
import flowpilot_router_events_repair
import flowpilot_router_event_dispatcher
import flowpilot_router_route_frontier
import flowpilot_router_terminal_ledger
from flowpilot_prompt_store import (
    PromptStoreError,
    card_manifest_entry,
    load_card_manifest_from_run,
)
from flowpilot_router_card_delivery import (
    CARD_LEDGER_SCHEMA,
    CARD_RETURN_EVENT_NAMES,
    RETURN_EVENT_LEDGER_SCHEMA,
    card_bundle_return_event_for_role as _card_bundle_return_event_for_role,
    card_ledger_path as _card_ledger_path,
    card_return_event_for_card as _card_return_event_for_card,
    empty_card_ledger as _empty_card_ledger,
    empty_return_event_ledger as _empty_return_event_ledger,
    is_card_return_event_name as _is_card_return_event_name,
    next_card_delivery_attempt as _next_card_delivery_attempt,
    read_card_ledger as _read_card_ledger,
    read_return_event_ledger as _read_return_event_ledger,
    return_event_ledger_path as _return_event_ledger_path,
    safe_delivery_component as _safe_delivery_component,
)
from flowpilot_router_card_settlement import (
    CARD_ACK_COMPLETE_STATUSES,
    CARD_BUNDLE_ACK_COMPLETE_STATUSES,
    _card_ack_clearance_scope,
    _controller_delivery_action_matches_pending_return,
    _delivery_identity,
    _original_card_ack_reminder_policy,
    _pending_action_matches_card_return,
    _record_matches_card_bundle_identity,
    _record_matches_card_identity,
    _record_value_for_bundle,
    _record_value_for_card,
    is_startup_pm_card_bundle_ack_record,
)
from flowpilot_router_controller_boundary import (
    CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE,
    CONTROLLER_ACTION_CLOSED_STATUSES,
    CONTROLLER_ACTION_RECEIPT_PRESERVED_STATUSES,
    CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE,
    CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
    CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS,
    CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE,
    CONTROLLER_POSTCONDITION_RECONCILIATION_MAX_ATTEMPTS,
    CONTROLLER_RECEIPT_STATUSES,
    CONTROLLER_RUNTIME_HELPER_AGENT_ID,
    FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS,
    FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS,
    PASSIVE_WAIT_STATUS_ACTION_TYPES,
    ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS,
    WAIT_TARGET_ACK_BLOCKER_SECONDS,
    WAIT_TARGET_ACK_REMINDER_SECONDS,
    WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS,
    WAIT_TARGET_REMINDER_ACTION_TYPE,
    WAIT_TARGET_REPORT_REMINDER_SECONDS,
    WAIT_TARGET_UNHEALTHY_LIVENESS_RESULTS,
    _controller_patrol_timer_command,
    _format_seconds_for_command,
)
from flowpilot_router_controller_ledger import (
    CONTROLLER_ACTION_LEDGER_SCHEMA,
    CONTROLLER_ACTION_SCHEMA,
    CONTROLLER_RECEIPT_SCHEMA,
    ROUTER_OWNERSHIP_LEDGER_SCHEMA,
    ROUTER_SCHEDULER_LEDGER_SCHEMA,
    ROUTER_SCHEDULER_ROW_SCHEMA,
    controller_action_ledger_path as _controller_action_ledger_path,
    controller_action_path as _controller_action_path,
    controller_actions_dir as _controller_actions_dir,
    controller_receipt_path as _controller_receipt_path,
    controller_receipts_dir as _controller_receipts_dir,
    prepare_router_scheduled_action as _prepare_router_scheduled_action_base,
    router_daemon_event_log_path as _router_daemon_event_log_path,
    router_daemon_lock_path as _router_daemon_lock_path,
    router_daemon_status_path as _router_daemon_status_path,
    router_ownership_ledger_path as _router_ownership_ledger_path,
    router_scheduler_barrier_kind as _router_scheduler_barrier_kind_base,
    router_scheduler_ledger_path as _router_scheduler_ledger_path,
    router_scheduler_progress_class as _router_scheduler_progress_class_base,
    runtime_dir as _runtime_dir,
)
from flowpilot_router_controller_reconciliation import (
    _action_is_passive_wait_status,
    _controller_action_active_work_count,
    _controller_action_counts,
    _controller_action_id_for_action,
    _controller_action_initial_status,
    _controller_action_is_ordinary_work_row,
    _controller_action_projection_kind,
    _controller_action_summary,
    _controller_receipt_display_rule,
    _controller_receipt_rule_for_display_action,
    _controller_ledger_action_view,
    _router_scheduler_idempotency_key,
    _router_scheduler_row_counts,
    _router_scheduler_row_id_for_action,
)
from flowpilot_router_dispatch_gate import (
    DISPATCH_RECIPIENT_GATE_PACKET_COMPLETION_FLAGS,
    DISPATCH_RECIPIENT_GATE_SAME_OBLIGATION_CARDS_BY_PACKET,
    PM_ROLE_WORK_PM_BUSY_STATUSES,
    PM_ROLE_WORK_TARGET_BUSY_STATUSES,
    _dispatch_gate_candidate_packet_ids,
    _dispatch_gate_candidate_request_ids,
    _dispatch_gate_packet_completed_by_flow_state,
    _dispatch_gate_same_obligation_instruction,
    _dispatch_gate_system_card_ids,
    _dispatch_gate_target_roles,
    _dispatch_gate_wait_events_for_packet_record,
)
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_io import (
    RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS,
    RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS,
    RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS,
    _copy_runtime_kit_into_run_root,
    _flowpilot_runtime_entrypoint_ref,
    _json_sha256,
    _json_write_lock_liveness,
    _json_write_lock_path,
    _parse_utc_timestamp,
    _project_root_from_run_root,
    _raise_if_runtime_write_active,
    _read_json_for_runtime_scan,
    _role_output_hashes,
    _role_output_semantic_hashes,
    _role_output_semantic_hash,
    _run_foreground_with_runtime_writer_settlement,
    _without_role_output_envelope,
    bootstrap_state_path,
    legacy_bootstrap_state_path,
    project_relative,
    read_daemon_critical_json_if_exists,
    read_json,
    read_json_if_exists,
    read_json_if_valid,
    run_bootstrap_state_path,
    runtime_kit_source,
    skill_root,
    utc_now,
    write_json,
    write_json_atomic,
)
from flowpilot_router_protocol_tables import MAIL_SEQUENCE, RUN_TERMINAL_STATUSES
from flowpilot_router_prompt_delivery import (
    card_checkin_instruction as _card_checkin_instruction,
    controller_break_glass_reminder as _controller_break_glass_reminder,
    controller_table_prompt as _controller_table_prompt,
    startup_heartbeat_prompt as _startup_heartbeat_prompt,
)
from flowpilot_router_role_io_protocol import (
    ROLE_IO_PROTOCOL_INJECTION_RECEIPT_SCHEMA,
    ROLE_IO_PROTOCOL_LEDGER_SCHEMA,
    ROLE_IO_PROTOCOL_SCHEMA,
    append_role_io_protocol_injections as _append_role_io_protocol_injections,
    empty_role_io_protocol_ledger as _empty_role_io_protocol_ledger,
    read_role_io_protocol_ledger as _read_role_io_protocol_ledger,
    role_io_protocol_hash as _role_io_protocol_hash,
    role_io_protocol_ledger_path as _role_io_protocol_ledger_path,
    role_io_protocol_payload as _role_io_protocol_payload,
    role_io_protocol_receipt_dir as _role_io_protocol_receipt_dir,
    role_io_protocol_receipt_for_agent as _role_io_protocol_receipt_for_agent,
    role_io_receipt_lifecycle_phase as _role_io_receipt_lifecycle_phase,
)
from flowpilot_router_startup_daemon import (
    ROUTER_DAEMON_EVENT_LOG_SCHEMA,
    ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS,
    ROUTER_DAEMON_LOCK_SCHEMA,
    ROUTER_DAEMON_LOCK_STALE_SECONDS,
    ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK,
    ROUTER_DAEMON_STARTUP_POLL_SECONDS,
    ROUTER_DAEMON_STARTUP_TIMEOUT_SECONDS,
    ROUTER_DAEMON_STATUS_SCHEMA,
    ROUTER_DAEMON_TICK_SECONDS,
    _lock_age_seconds,
    _process_is_live,
    _router_daemon_heartbeat_monitor,
    _router_daemon_lock_has_live_owner,
    _router_daemon_lock_is_live,
    _router_daemon_lock_liveness,
    _router_daemon_owner,
)
from flowpilot_router_terminal import (
    FLOWPILOT_PROJECT_URL,
    TERMINAL_SUMMARY_ATTRIBUTION,
    TERMINAL_SUMMARY_READ_SCOPE,
    TERMINAL_SUMMARY_SCHEMA,
    _path_is_inside,
    _terminal_lifecycle_mode,
    _terminal_summary_hash,
    _terminal_summary_json_path,
    _terminal_summary_markdown_path,
)


SCHEMA_VERSION = "flowpilot.router.v1"
BOOTSTRAP_STATE_SCHEMA = "flowpilot.bootstrap_state.v1"
RUN_STATE_SCHEMA = "flowpilot.run_state.v1"
PROMPT_MANIFEST_SCHEMA = "flowpilot.prompt_manifest.v1"
PACKET_LEDGER_SCHEMA = packet_runtime.PACKET_LEDGER_SCHEMA
RESUME_EVIDENCE_SCHEMA = "flowpilot.resume_reentry.v1"
ROUTE_HISTORY_INDEX_SCHEMA = "flowpilot.route_history_index.v1"
PM_PRIOR_PATH_CONTEXT_SCHEMA = "flowpilot.pm_prior_path_context.v1"
DISPLAY_PLAN_SCHEMA = "flowpilot.display_plan.v1"
ROUTE_STATE_SNAPSHOT_SCHEMA = "flowpilot.route_state_snapshot.v1"
CONTROL_BLOCKER_SCHEMA = "flowpilot.control_blocker.v1"
CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA = "flowpilot.control_blocker_repair_packet.v1"
BLOCKER_REPAIR_POLICY_SCHEMA = "flowpilot.blocker_repair_policy.v1"
REPAIR_TRANSACTION_SCHEMA = "flowpilot.repair_transaction.v1"
REPAIR_TRANSACTION_INDEX_SCHEMA = "flowpilot.repair_transaction_index.v1"
ROLE_RECOVERY_TRANSACTION_SCHEMA = "flowpilot.role_recovery_transaction.v1"
ROLE_RECOVERY_REPORT_SCHEMA = "flowpilot.role_recovery_report.v1"
ROLE_RECOVERY_OBLIGATION_REPLAY_SCHEMA = "flowpilot.role_recovery_obligation_replay.v1"
CONTROL_TRANSACTION_REGISTRY_SCHEMA = "flowpilot.control_transaction_registry.v1"
ROUTE_ACTION_POLICY_REGISTRY_SCHEMA = "flowpilot.route_action_policy_registry.v1"
ROLE_OUTPUT_ENVELOPE_SCHEMA = "flowpilot.role_output_envelope.v1"
EVENT_ENVELOPE_SCHEMA = "flowpilot.event_envelope.v1"
LIVE_CARD_CONTEXT_SCHEMA = "flowpilot.live_card_context.v1"
PAYLOAD_CONTRACT_SCHEMA = "flowpilot.payload_contract.v1"
GATE_DECISION_SCHEMA = "flowpilot.gate_decision.v1"
GATE_DECISION_RECORD_SCHEMA = "flowpilot.gate_decision_record.v1"
GATE_DECISION_LEDGER_SCHEMA = "flowpilot.gate_decision_ledger.v1"
PM_SUGGESTION_LEDGER_ENTRY_SCHEMA = "flowpilot.pm_suggestion_item.v1"
SELF_INTERROGATION_INDEX_SCHEMA = "flowpilot.self_interrogation_index.v1"
SELF_INTERROGATION_RECORD_SCHEMA = "flowpilot.self_interrogation_record.v1"
PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT = "pm_records_control_blocker_repair_decision"
PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT = "pm_records_control_blocker_followup_blocker"
PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT = "pm_records_control_blocker_protocol_blocker"
PM_PARENT_PROTOCOL_BLOCKER_EVENT = "pm_records_parent_protocol_blocker"
PM_MODEL_MISS_TRIAGE_DECISION_EVENT = "pm_records_model_miss_triage_decision"
PM_ROLE_WORK_REQUEST_EVENT = "pm_registers_role_work_request"
ROLE_WORK_RESULT_RETURNED_EVENT = "role_work_result_returned"
PM_ROLE_WORK_RESULT_DECISION_EVENT = "pm_records_role_work_result_decision"
GATE_DECISION_EVENT = "role_records_gate_decision"
EVENT_IDEMPOTENCY_LEDGER_SCHEMA = "flowpilot.external_event_idempotency.v1"
DISPLAY_CONFIRMATION_SCHEMA = "flowpilot.user_dialog_display_confirmation.v1"
DISPLAY_SURFACE_RECEIPT_SCHEMA = "flowpilot.display_surface_receipt.v1"
CURRENT_STATUS_SUMMARY_SCHEMA = "flowpilot.current_status_summary.v1"
OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA = flowpilot_runtime_closure.OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA
CONTINUATION_QUARANTINE_SCHEMA = flowpilot_runtime_closure.CONTINUATION_QUARANTINE_SCHEMA
FINAL_USER_REPORT_SCHEMA = flowpilot_runtime_closure.FINAL_USER_REPORT_SCHEMA
ROUTE_DISPLAY_REFRESH_SCHEMA = flowpilot_runtime_closure.ROUTE_DISPLAY_REFRESH_SCHEMA
CONTROLLER_USER_REPORTING_POLICY_SCHEMA = "flowpilot.controller_user_reporting_policy.v1"
DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA = "flowpilot.deterministic_bootstrap_seed_evidence.v1"
FOREGROUND_CONTROLLER_STANDBY_SCHEMA = "flowpilot.foreground_controller_standby.v1"
CONTROLLER_PATROL_TIMER_SCHEMA = "flowpilot.controller_patrol_timer.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE
CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID
CONTROLLER_STATEFUL_VALIDATOR_TABLE = {
    "confirm_controller_core_boundary": {
        "validator": "controller_boundary_confirmation_context",
        "postcondition": "controller_role_confirmed",
        "deliverable_id": "controller_boundary_confirmation",
        "artifact_kind": "controller_boundary_confirmation",
        "runtime_channel": "role_output_runtime",
        "output_type": CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
        "output_contract_id": CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
    },
}
STARTUP_MECHANICAL_AUDIT_SCHEMA = "flowpilot.startup_mechanical_audit.v1"
ROUTER_OWNED_CHECK_PROOF_SCHEMA = "flowpilot.router_owned_check_proof.v1"
CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA = role_output_runtime.CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA
STARTUP_ANSWER_PROVENANCE = "explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_PROVENANCE = "ai_interpreted_from_explicit_user_reply"
STARTUP_ANSWER_INTERPRETATION_SCHEMA = "flowpilot.startup_answer_interpretation.v1"
STARTUP_INTAKE_RESULT_SCHEMA = "flowpilot.startup_intake_result.v1"
STARTUP_INTAKE_RECEIPT_SCHEMA = "flowpilot.startup_intake_receipt.v1"
STARTUP_INTAKE_ENVELOPE_SCHEMA = "flowpilot.startup_intake_envelope.v1"
STARTUP_INTAKE_RECORD_SCHEMA = "flowpilot.startup_intake_record.v1"
STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE = "interactive_native"
USER_REQUEST_REF_SCHEMA = "flowpilot.user_request_ref.v1"
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
ROLE_AGENT_OLD_RESTORE_RESULT = "old_agent_restored"
ROLE_AGENT_TARGETED_REPLACEMENT_RESULT = "targeted_replacement_spawned"
ROLE_AGENT_FULL_CREW_RECYCLE_RESULT = "full_crew_recycle_spawned"
ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT = "environment_blocked"
BACKGROUND_ROLE_MODEL_POLICY = "strongest_available"
BACKGROUND_ROLE_REASONING_EFFORT_POLICY = "highest_available"
BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT = "xhigh"
RESUME_ROLE_AGENT_RESULTS = {ROLE_AGENT_REHYDRATION_RESULT, ROLE_AGENT_CONTINUITY_RESULT}
ROLE_RECOVERY_RESULTS = {
    ROLE_AGENT_OLD_RESTORE_RESULT,
    ROLE_AGENT_TARGETED_REPLACEMENT_RESULT,
    ROLE_AGENT_FULL_CREW_RECYCLE_RESULT,
    ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT,
}
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
PM_BLOCKER_RECOVERY_OPTIONS = (
    "same_gate_repair",
    "rollback_to_prior_gate",
    "supplemental_node",
    "repair_node",
    "route_mutation",
    "evidence_quarantine",
    "allowed_waiver",
    "user_stop",
    "protocol_dead_end",
)
REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS = {
    "operation_replay",
    "controller_repair_work_packet",
    "packet_reissue",
    "role_reissue",
    "router_internal_reconcile",
    "await_existing_event",
    "route_mutation",
    "terminal_stop",
}
REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES = {
    "event_replay": "await_existing_event",
}
REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES = {
    "deliver_mail",
    "deliver_system_card",
    "deliver_system_card_bundle",
    "relay_material_scan_packets",
    "relay_research_packets",
    "relay_current_node_packet",
    "relay_material_scan_results_to_pm",
    "relay_current_node_result_to_pm",
    "relay_research_results_to_pm",
}
BLOCKER_REPAIR_POLICY_ROWS: dict[str, dict[str, Any]] = {
    "mechanical_control_plane_reissue": {
        "policy_row_id": "mechanical_control_plane_reissue",
        "blocker_family": "mechanical_control_plane",
        "first_handler": "responsible_role",
        "direct_retry_budget": 2,
        "escalate_to": "project_manager",
        "pm_recovery_options": PM_BLOCKER_RECOVERY_OPTIONS,
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "originating_event",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [],
        "controller_boundary": "deliver policy row and sealed repair packet only; do not open sealed bodies or decide project substance",
    },
    "pm_semantic_repair": {
        "policy_row_id": "pm_semantic_repair",
        "blocker_family": "semantic_or_route_repair",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": PM_BLOCKER_RECOVERY_OPTIONS,
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "pm_selected_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [],
        "controller_boundary": "deliver blocker metadata only and wait for PM recovery decision",
    },
    "fatal_protocol_violation": {
        "policy_row_id": "fatal_protocol_violation",
        "blocker_family": "fatal_protocol_violation",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": (
            "same_gate_repair",
            "rollback_to_prior_gate",
            "route_mutation",
            "evidence_quarantine",
            "user_stop",
            "protocol_dead_end",
        ),
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "pm_selected_safe_recovery_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [
            "controller_body_access",
            "private_role_to_role_relay",
            "contaminated_evidence",
        ],
        "controller_boundary": "stop normal route work and deliver sealed repair packet envelope to PM",
    },
    "self_interrogation_repair": {
        "policy_row_id": "self_interrogation_repair",
        "blocker_family": "self_interrogation_disposition",
        "first_handler": "project_manager",
        "direct_retry_budget": 0,
        "escalate_to": "project_manager",
        "pm_recovery_options": (
            "rerun_self_interrogation",
            "record_disposition",
            "convert_findings_to_repair",
            "same_gate_repair",
            "rollback_to_prior_gate",
            "supplemental_node",
            "route_mutation",
            "evidence_quarantine",
            "allowed_waiver",
            "user_stop",
        ),
        "return_policy": {
            "requires_named_return_gate": True,
            "default_return_gate": "blocked_self_interrogation_gate",
            "blocked_gate_may_not_be_marked_passed_directly": True,
        },
        "hard_stop_conditions": [
            "unresolved_hard_current_findings_require_repair_or_authorized_waiver",
        ],
        "controller_boundary": "deliver blocker metadata to PM; do not rerun grill-me or decide finding disposition",
    },
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
PM_ROLE_WORK_REQUEST_MODES = {"blocking", "advisory", "prep-only"}
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
PM_PACKAGE_RESULT_DECISIONS = {
    "absorbed",
    "rework_requested",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}
PARALLEL_PACKET_BATCH_OPEN_STATUSES = {
    "registered",
    "packets_relayed",
    "partial_results_returned",
    "results_joined",
    "results_relayed_to_reviewer",
    "results_relayed_to_pm",
    "reviewed",
}
PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES = {
    "result_returned",
    "result_relayed_to_pm",
    "result_relayed_to_reviewer",
    "reviewed",
    "absorbed",
}
PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES = {
    "results_relayed_to_pm",
    "results_relayed_to_reviewer",
    "reviewed",
    "review_blocked",
    "pm_absorbed",
    "absorbed",
    "canceled",
    "blocked",
    "route_or_node_mutation_required",
}
PROCESS_CONTRACT_BINDINGS: dict[str, dict[str, Any]] = {
    "current_node_work": {
        "task_family": "worker.current_node",
        "contract_id": "flowpilot.output_contract.worker_current_node_result.v1",
        "packet_type": "work_packet",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
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
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "material_scan": {
        "task_family": "worker.material_scan",
        "contract_id": "flowpilot.output_contract.worker_material_scan_result.v1",
        "packet_type": "material_scan",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
    },
    "research": {
        "task_family": "worker.research",
        "contract_id": "flowpilot.output_contract.worker_research_result.v1",
        "packet_type": "research",
        "required_result_next_recipient": "project_manager",
        "absorbing_role": "project_manager",
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

# Material dispatch blockers are now router/control-blocker repair outcomes, not
# PM model-miss reviewer-block repair inputs.
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

PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS = {
    "pm.prior_path_context",
    "pm.route_skeleton",
    "pm.product_behavior_model_decision",
    "pm.process_route_model_decision",
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
        "action_type": "start_router_daemon",
        "flag": "router_daemon_started",
        "label": "formal_router_daemon_started_as_startup_driver",
        "summary": "Start or attach the built-in one-second Router daemon, then let it schedule startup rows before any external startup work.",
        "actor": "bootloader",
    },
    {
        "action_type": "open_startup_intake_ui",
        "flag": "startup_questions_asked",
        "label": "startup_intake_ui_opened_from_router",
        "summary": "Open the native FlowPilot startup intake UI, then return to Router daemon status and the Controller action ledger without reading the body text in Controller context.",
        "actor": "bootloader",
        "requires_host_automation": True,
        "requires_payload": "startup_intake_result",
        "terminal_for_turn": True,
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
        "summary": "Record the exact current FlowPilot task text from explicit user input while the full user_intake remains sealed until startup activation.",
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
        "action_type": "load_controller_core",
        "flag": "controller_core_loaded",
        "label": "controller_core_loaded",
        "summary": "End bootloader startup, attach Controller to the Router daemon action ledger, and record Controller boundary confirmation evidence before Controller-ledger startup obligations.",
        "actor": "bootloader",
    },
    {
        "action_type": "emit_startup_banner",
        "flag": "banner_emitted",
        "label": "startup_banner_emitted_after_controller_core",
        "summary": "Display the startup banner in the user dialog after Controller core is loaded, then record the confirmed display.",
        "actor": "bootloader",
        "card_id": "startup_banner",
    },
    {
        "action_type": "create_heartbeat_automation",
        "flag": "continuation_binding_recorded",
        "label": "host_bootstraps_startup_heartbeat_automation",
        "summary": "Create the one-minute Codex heartbeat after Controller core handoff and before startup review or route work.",
        "actor": "bootloader",
        "requires_host_automation": True,
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
        "requires_flag": "user_intake_delivered_to_pm",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_material_sufficiency_card_delivered",
        "label": "reviewer_material_sufficiency_card_delivered",
        "card_id": "reviewer.material_sufficiency",
        "requires_flag": "material_scan_results_absorbed_by_pm",
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
        "requires_flag": "research_result_absorbed_for_review_by_pm",
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
        "requires_flag": "current_node_result_absorbed_by_pm",
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
        "flag": "pm_product_behavior_model_decision_card_delivered",
        "label": "pm_product_behavior_model_decision_card_delivered",
        "card_id": "pm.product_behavior_model_decision",
        "requires_flag": "product_behavior_model_submitted",
        "to_role": "project_manager",
    },
    {
        "flag": "reviewer_product_architecture_card_delivered",
        "label": "reviewer_product_architecture_challenge_card_delivered",
        "card_id": "reviewer.product_architecture_challenge",
        "requires_flag": "pm_product_behavior_model_accepted",
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

CARD_PHASE_BY_ID = {
    "pm.product_architecture": "product_architecture",
    "product_officer.product_architecture_modelability": "product_architecture",
    "pm.product_behavior_model_decision": "product_architecture",
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
    "pm.process_route_model_decision": "route_skeleton",
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
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
    },
    "pm.product_behavior_model_decision": {
        "product_function_architecture": "product_function_architecture.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
    },
    "pm.root_contract": {
        "product_function_architecture": "product_function_architecture.json",
        "product_architecture_challenge": "reviews/product_architecture_challenge.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
        "product_architecture_modelability": "flowguard/product_architecture_modelability.json",
        "pm_product_behavior_model_decision": "flowguard/product_behavior_model_pm_decision.json",
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
        "pm_process_route_model_decision": "flowguard/process_route_model_pm_decision.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
    },
    "reviewer.route_challenge": {
        "root_acceptance_contract": "root_acceptance_contract.json",
        "child_skill_gate_manifest": "child_skill_gate_manifest.json",
        "pm_process_route_model_decision": "flowguard/process_route_model_pm_decision.json",
        "process_route_model": "flowguard/process_route_model.json",
        "route_process_check": "flowguard/route_process_check.json",
        "product_behavior_model": "flowguard/product_behavior_model.json",
    },
}

EXTERNAL_EVENTS: dict[str, dict[str, Any]] = {
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
    "controller_reports_role_liveness_fault": {
        "flag": "role_recovery_requested",
        "summary": "Controller reported that a background role is missing, cancelled, unknown, timed out, or no longer addressable; unified role recovery must preempt normal work.",
    },
    "controller_reports_role_no_output": {
        "flag": "role_no_output_reissue_recorded",
        "summary": "Controller reported that the waited role is reachable or completed but Router still lacks the expected output; Router may reissue the same work before role recovery.",
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
        "summary": "Worker scan results returned to the PM-first result path.",
    },
    "pm_records_material_scan_result_disposition": {
        "flag": "material_scan_result_disposition_recorded",
        "requires_flag": "material_scan_results_relayed_to_pm",
        "summary": "PM recorded material scan result disposition and released a formal material sufficiency package when absorbed.",
    },
    "worker_current_node_result_returned": {
        "flag": "current_node_worker_result_returned",
        "requires_flag": "current_node_packet_relayed",
        "summary": "Worker returned a current-node result envelope.",
    },
    "pm_records_current_node_result_disposition": {
        "flag": "current_node_result_disposition_recorded",
        "requires_flag": "current_node_result_relayed_to_pm",
        "summary": "PM recorded current-node worker result disposition and released the formal node-completion review package when absorbed.",
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
    "pm_records_research_result_disposition": {
        "flag": "research_result_disposition_recorded",
        "requires_flag": "research_result_relayed_to_pm",
        "summary": "PM recorded research result disposition and released a formal research source-check package when absorbed.",
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
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer submitted the product behavior model.",
    },
    "product_officer_submits_product_behavior_model": {
        "flag": "product_behavior_model_submitted",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer submitted the canonical product behavior model.",
    },
    "product_officer_model_report": {
        "flag": "legacy_product_officer_model_report_received",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "legacy": True,
        "terminal_gate_outcome": False,
        "summary": "Legacy Product FlowGuard model-report status event retained only so old run artifacts remain registered in the event taxonomy.",
    },
    "pm_accepts_product_behavior_model": {
        "flag": "pm_product_behavior_model_accepted",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM accepted the Product FlowGuard product behavior model as the product basis for review and route planning.",
    },
    "pm_requests_product_behavior_model_rebuild": {
        "flag": "pm_product_behavior_model_rebuild_requested",
        "requires_flag": "pm_product_behavior_model_decision_card_delivered",
        "summary": "PM rejected the current product behavior model and requested product architecture/model rebuild before reviewer challenge.",
    },
    "product_officer_blocks_product_architecture_modelability": {
        "flag": "product_architecture_modelability_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Product FlowGuard Officer blocked the product behavior model.",
    },
    "product_officer_blocks_product_behavior_model": {
        "flag": "product_behavior_model_blocked",
        "requires_flag": "product_officer_product_architecture_card_delivered",
        "gate_id": "product_behavior_model",
        "terminal_gate_outcome": True,
        "summary": "Product FlowGuard Officer blocked the canonical product behavior model.",
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
        "legacy": True,
        "summary": "Product FlowGuard Officer passed root contract modelability.",
    },
    "product_officer_blocks_root_acceptance_contract_modelability": {
        "flag": "root_contract_modelability_blocked",
        "requires_flag": "product_officer_root_contract_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked root contract modelability.",
    },
    "pm_freezes_root_acceptance_contract": {
        "flag": "root_contract_frozen_by_pm",
        "requires_flag": "root_contract_reviewer_passed",
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
        "legacy": True,
        "summary": "Process FlowGuard Officer passed child-skill conformance model review.",
    },
    "process_officer_blocks_child_skill_conformance_model": {
        "flag": "child_skill_process_officer_blocked",
        "requires_flag": "process_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Process FlowGuard Officer blocked child-skill conformance model review.",
    },
    "product_officer_passes_child_skill_product_fit": {
        "flag": "child_skill_product_officer_passed",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer passed child-skill product fit review.",
    },
    "product_officer_blocks_child_skill_product_fit": {
        "flag": "child_skill_product_officer_blocked",
        "requires_flag": "product_officer_child_skill_card_delivered",
        "legacy": True,
        "summary": "Product FlowGuard Officer blocked child-skill product fit review.",
    },
    "pm_approves_child_skill_manifest_for_route": {
        "flag": "child_skill_manifest_pm_approved_for_route",
        "requires_flag": "child_skill_manifest_reviewer_passed",
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
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer submitted the process route model.",
    },
    "process_officer_submits_process_route_model": {
        "flag": "process_route_model_submitted",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer submitted the canonical process route model.",
    },
    "pm_accepts_process_route_model": {
        "flag": "pm_process_route_model_accepted",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM accepted the Process FlowGuard serial route execution model before Reviewer route challenge.",
    },
    "pm_requests_process_route_model_rebuild": {
        "flag": "pm_process_route_model_rebuild_requested",
        "requires_flag": "pm_process_route_model_decision_card_delivered",
        "summary": "PM rejected the current process route model and requested route/model rebuild before route challenge.",
    },
    "process_officer_requires_route_repair": {
        "flag": "process_officer_route_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer requested process route model repair.",
    },
    "process_officer_requests_process_route_model_repair": {
        "flag": "process_route_model_repair_required",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer requested repair of the canonical process route model.",
    },
    "process_officer_blocks_route_check": {
        "flag": "process_officer_route_check_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Compatibility alias: Process FlowGuard Officer blocked the process route model.",
    },
    "process_officer_blocks_process_route_model": {
        "flag": "process_route_model_blocked",
        "requires_flag": "process_officer_route_check_card_delivered",
        "gate_id": "process_route_model",
        "terminal_gate_outcome": True,
        "summary": "Process FlowGuard Officer blocked the canonical process route model.",
    },
    "product_officer_passes_route_check": {
        "flag": "product_officer_route_check_passed",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer passed the legacy route product check.",
    },
    "product_officer_blocks_route_check": {
        "flag": "product_officer_route_check_blocked",
        "requires_flag": "product_officer_route_check_card_delivered",
        "legacy": True,
        "summary": "Compatibility event: Product FlowGuard Officer blocked the legacy route product check.",
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
        "summary": "PM activated route after Product Officer product model, Process Officer route model, and Reviewer route challenge.",
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
    "pm_records_control_blocker_followup_blocker": {
        "flag": "pm_control_blocker_followup_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up ended in a blocker that needs a new PM decision.",
    },
    "pm_records_control_blocker_protocol_blocker": {
        "flag": "pm_control_blocker_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded that a control-blocker repair follow-up exposed a protocol blocker.",
    },
    "pm_records_parent_protocol_blocker": {
        "flag": "parent_protocol_blocker_recorded",
        "requires_flag": "pm_control_blocker_repair_decision_recorded",
        "summary": "PM recorded a parent/module repair protocol blocker after parent backward replay repair.",
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
    "pm_product_architecture_card_delivered",
    "product_architecture_written_by_pm",
    "pm_product_behavior_model_decision_card_delivered",
    "pm_product_behavior_model_accepted",
    "pm_product_behavior_model_rebuild_requested",
    "product_architecture_reviewer_passed",
    "product_behavior_model_submitted",
    "product_behavior_model_blocked",
    "product_architecture_modelability_passed",
    "product_architecture_modelability_blocked",
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
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
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
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
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
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "route_activated_by_pm",
)
ROUTE_GATE_REPAIR_RESET_FLAGS = (
    "route_draft_written_by_pm",
    "process_route_model_submitted",
    "process_route_model_repair_required",
    "process_route_model_blocked",
    "process_officer_route_check_passed",
    "process_officer_route_repair_required",
    "process_officer_route_check_blocked",
    "pm_process_route_model_decision_card_delivered",
    "pm_process_route_model_accepted",
    "pm_process_route_model_rebuild_requested",
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
    "research_result_relayed_to_pm",
    "research_result_disposition_recorded",
    "research_result_absorbed_for_review_by_pm",
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
        "reset_flags": tuple(
            flag
            for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS
            if flag != "product_architecture_modelability_blocked"
        ),
    },
    "product_officer_blocks_product_behavior_model": {
        "expected_role": "product_flowguard_officer",
        "path": "flowguard/product_behavior_model_block.json",
        "schema_version": "flowpilot.product_behavior_model_block.v1",
        "checked_paths": ("product_function_architecture.json",),
        "reset_flags": tuple(
            flag
            for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS
            if flag != "product_behavior_model_blocked"
        ),
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
        "checked_paths": (
            "__current_route_draft__",
            "flowguard/route_process_check.json",
            "flowguard/process_route_model_pm_decision.json",
            "flowguard/product_behavior_model.json",
        ),
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

GATE_CONTRACT_SCHEMA = "flowpilot.gate_contract.v1"
GATE_CONTRACTS: dict[str, dict[str, Any]] = {
    "product_behavior_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "product_behavior_model",
        "card_id": "product_officer.product_architecture_modelability",
        "required_flag": "product_behavior_model_submitted",
        "wait_requires_flag": "product_officer_product_architecture_card_delivered",
        "target_role": "product_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "product_officer_submits_product_behavior_model",
            "product_officer_passes_product_architecture_modelability",
        ),
        "block_events": (
            "product_officer_blocks_product_behavior_model",
            "product_officer_blocks_product_architecture_modelability",
        ),
        "legacy_non_completion_events": ("product_officer_model_report",),
        "completion_rule": "pass_or_block_event_required",
        "legacy_event_policy": "registered_metadata_only_not_gate_completion",
        "canonical_artifact": "flowguard/product_behavior_model.json",
        "compatibility_artifact": "flowguard/product_architecture_modelability.json",
    },
    "process_route_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "process_route_model",
        "card_id": "process_officer.route_process_check",
        "required_flag": "process_route_model_submitted",
        "wait_requires_flag": "process_officer_route_check_card_delivered",
        "target_role": "process_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "process_officer_submits_process_route_model",
            "process_officer_passes_route_check",
        ),
        "block_events": (
            "process_officer_requests_process_route_model_repair",
            "process_officer_blocks_process_route_model",
            "process_officer_requires_route_repair",
            "process_officer_blocks_route_check",
        ),
        "legacy_non_completion_events": (),
        "completion_rule": "pass_repair_or_block_event_required",
        "legacy_event_policy": "compatibility_aliases_satisfy_canonical_flags",
        "canonical_artifact": "flowguard/process_route_model.json",
        "compatibility_artifact": "flowguard/route_process_check.json",
    },
}
GATE_CONTRACT_ALIASES = {
    "product_architecture_modelability": "product_behavior_model",
    "route_process_check": "process_route_model",
}
GATE_CONTRACTS_BY_CARD = {
    str(contract["card_id"]): gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
}
GATE_CONTRACTS_BY_EVENT = {
    event: gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
    for event in (
        *contract.get("pass_events", ()),
        *contract.get("block_events", ()),
        *contract.get("legacy_non_completion_events", ()),
    )
}


def _public_gate_contract(contract: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(contract, dict):
        return None
    public = dict(contract)
    for key in ("pass_events", "block_events", "legacy_non_completion_events"):
        public[key] = list(public.get(key) or [])
    return public


def _gate_contract_for_id(gate_id: str | None) -> dict[str, Any] | None:
    if not gate_id:
        return None
    key = str(gate_id)
    return GATE_CONTRACTS.get(key) or GATE_CONTRACTS.get(GATE_CONTRACT_ALIASES.get(key, ""))


def _gate_contract_for_card(card_id: str | None) -> dict[str, Any] | None:
    if not card_id:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_CARD.get(str(card_id)))


def _gate_contract_for_event(event: str | None) -> dict[str, Any] | None:
    if not event:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_EVENT.get(str(event)))


def _gate_contract_for_events(events: Iterable[str]) -> dict[str, Any] | None:
    gate_ids = {
        GATE_CONTRACTS_BY_EVENT[str(event)]
        for event in events
        if str(event) in GATE_CONTRACTS_BY_EVENT
    }
    if len(gate_ids) == 1:
        return _gate_contract_for_id(next(iter(gate_ids)))
    return None


def _event_is_terminal_gate_outcome(event: str, meta: dict[str, Any]) -> bool:
    if meta.get("legacy") or meta.get("terminal_gate_outcome") is False:
        return False
    contract = _gate_contract_for_event(event)
    if contract is None:
        return True
    return event in set(contract.get("pass_events") or ()) | set(contract.get("block_events") or ())


def _gate_completion_wait_group(group: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    if not _gate_contract_for_events(event for event, _meta in group):
        return group
    terminal_group = [
        (event, meta)
        for event, meta in group
        if _event_is_terminal_gate_outcome(event, meta)
    ]
    return terminal_group or group


PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS = frozenset(
    {
        "product_officer_submits_product_behavior_model",
        "product_officer_passes_product_architecture_modelability",
    }
)
PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS = frozenset(
    {
        "product_officer_blocks_product_behavior_model",
        "product_officer_blocks_product_architecture_modelability",
    }
)
PROCESS_ROUTE_MODEL_PASS_EVENTS = frozenset(
    {
        "process_officer_submits_process_route_model",
        "process_officer_passes_route_check",
    }
)
PROCESS_ROUTE_MODEL_REPAIR_EVENTS = frozenset(
    {
        "process_officer_requests_process_route_model_repair",
        "process_officer_requires_route_repair",
    }
)
PROCESS_ROUTE_MODEL_BLOCK_EVENTS = frozenset(
    {
        "process_officer_blocks_process_route_model",
        "process_officer_blocks_route_check",
    }
)


def _sync_model_gate_alias_flags(run_state: dict[str, Any], event: str) -> None:
    flags = run_state.setdefault("flags", {})
    if event in PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS:
        flags["product_behavior_model_submitted"] = True
        flags["product_architecture_modelability_passed"] = True
        flags["product_behavior_model_blocked"] = False
        flags["product_architecture_modelability_blocked"] = False
    elif event in PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS:
        flags["product_behavior_model_submitted"] = False
        flags["product_architecture_modelability_passed"] = False
        flags["product_behavior_model_blocked"] = True
        flags["product_architecture_modelability_blocked"] = True
    elif event in PROCESS_ROUTE_MODEL_PASS_EVENTS:
        flags["process_route_model_submitted"] = True
        flags["process_officer_route_check_passed"] = True
        flags["process_route_model_repair_required"] = False
        flags["process_officer_route_repair_required"] = False
        flags["process_route_model_blocked"] = False
        flags["process_officer_route_check_blocked"] = False
    elif event in PROCESS_ROUTE_MODEL_REPAIR_EVENTS:
        flags["process_route_model_submitted"] = False
        flags["process_officer_route_check_passed"] = False
        flags["process_route_model_repair_required"] = True
        flags["process_officer_route_repair_required"] = True
        flags["process_route_model_blocked"] = False
        flags["process_officer_route_check_blocked"] = False
    elif event in PROCESS_ROUTE_MODEL_BLOCK_EVENTS:
        flags["process_route_model_submitted"] = False
        flags["process_officer_route_check_passed"] = False
        flags["process_route_model_repair_required"] = False
        flags["process_officer_route_repair_required"] = False
        flags["process_route_model_blocked"] = True
        flags["process_officer_route_check_blocked"] = True


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


def _self_interrogation_index_path(run_root: Path) -> Path:
    return run_root / "self_interrogation_index.json"


def _self_interrogation_issue(
    message: str,
    *,
    record_id: str = "",
    record_path: str = "",
    scope: str = "",
) -> dict[str, str]:
    issue = {"message": message}
    if record_id:
        issue["record_id"] = record_id
    if record_path:
        issue["record_path"] = record_path
    if scope:
        issue["scope"] = scope
    return issue


def _self_interrogation_entry_path(entry: dict[str, Any]) -> str:
    return str(entry.get("record_path") or entry.get("path") or "")


def _self_interrogation_final_status(status: str) -> bool:
    return status in SELF_INTERROGATION_FINAL_DISPOSITIONS


def _self_interrogation_record_issues(
    project_root: Path,
    run_root: Path,
    record_path: Path,
    record: dict[str, Any],
    *,
    expected_scope: str | None = None,
    expected_node_id: str | None = None,
    expected_route_version: int | None = None,
) -> tuple[list[dict[str, str]], int]:
    record_rel = project_relative(project_root, record_path)
    record_id = str(record.get("record_id") or record_path.stem)
    scope = str(record.get("scope") or "")
    issues: list[dict[str, str]] = []
    unresolved_hard_count = 0

    def add(message: str) -> None:
        issues.append(_self_interrogation_issue(message, record_id=record_id, record_path=record_rel, scope=scope))

    if record.get("schema_version") != SELF_INTERROGATION_RECORD_SCHEMA:
        add(f"schema_version must be {SELF_INTERROGATION_RECORD_SCHEMA}")
    if not record.get("record_id"):
        add("record_id is required")
    if scope not in SELF_INTERROGATION_SCOPES:
        add("scope must be a supported self-interrogation scope")
    if expected_scope and scope != expected_scope:
        add(f"scope must be {expected_scope}")
    if not record.get("owner_role"):
        add("owner_role is required")
    if not record.get("source_event"):
        add("source_event is required")
    raw_source_path = str(record.get("source_artifact_path") or "")
    if not raw_source_path:
        add("source_artifact_path is required")
    else:
        source_path = resolve_project_path(project_root, raw_source_path)
        if not source_path.exists():
            add(f"source_artifact_path does not exist: {raw_source_path}")
    if expected_node_id and scope in {"node_entry", "repair", "role_result"}:
        if str(record.get("node_id") or "") != expected_node_id:
            add(f"node_id must match active node {expected_node_id}")
    if expected_route_version is not None and record.get("route_version") is not None:
        try:
            record_route_version = int(record.get("route_version"))
        except (TypeError, ValueError):
            add("route_version must be an integer when present")
        else:
            if record_route_version != expected_route_version:
                add(f"route_version must match active route version {expected_route_version}")

    findings = record.get("findings")
    if not isinstance(findings, list):
        add("findings must be a list")
        findings = []
    for index, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            add(f"findings[{index}] must be an object")
            continue
        finding_id = str(finding.get("finding_id") or f"finding-{index}")
        severity = str(finding.get("severity") or "")
        disposition = finding.get("disposition") if isinstance(finding.get("disposition"), dict) else {}
        disposition_status = str(disposition.get("status") or "")
        for field in ("finding_id", "severity", "category", "summary"):
            if not finding.get(field):
                add(f"finding {finding_id} missing {field}")
        if not disposition_status:
            add(f"finding {finding_id} missing disposition.status")
        hard_or_current = severity in SELF_INTERROGATION_HARD_SEVERITIES or finding.get("blocks_current_gate_until_disposition") is True
        if hard_or_current and not _self_interrogation_final_status(disposition_status):
            unresolved_hard_count += 1
            add(f"finding {finding_id} is unresolved for a hard/current self-interrogation finding")
        if disposition_status == "reject_with_reason" and not disposition.get("reason"):
            add(f"finding {finding_id} reject_with_reason requires reason")
        if disposition_status == "waive_with_authority" and (
            not disposition.get("reason") or not disposition.get("waiver_authority_role")
        ):
            add(f"finding {finding_id} waive_with_authority requires reason and waiver_authority_role")
        if disposition_status == "defer_to_named_node" and not disposition.get("target_node_or_gate_id"):
            add(f"finding {finding_id} defer_to_named_node requires target_node_or_gate_id")
        if disposition_status == "entered_pm_suggestion_ledger" and not (
            disposition.get("suggestion_id") or record.get("pm_suggestion_ledger_ids")
        ):
            add(f"finding {finding_id} entered_pm_suggestion_ledger requires a suggestion id")
        if disposition_status == "incorporated_into_artifact" and not (
            disposition.get("artifact_path") or record.get("downstream_artifact_paths")
        ):
            add(f"finding {finding_id} incorporated_into_artifact requires downstream artifact evidence")

    try:
        declared_unresolved = int(record.get("unresolved_hard_finding_count", 0) or 0)
    except (TypeError, ValueError):
        declared_unresolved = -1
        add("unresolved_hard_finding_count must be an integer")
    if declared_unresolved > 0:
        unresolved_hard_count = max(unresolved_hard_count, declared_unresolved)
        add("record declares unresolved hard/current self-interrogation findings")
    disposition_summary = record.get("pm_disposition_summary")
    if not isinstance(disposition_summary, dict):
        add("pm_disposition_summary must be an object")
    for field in ("downstream_artifact_paths", "pm_suggestion_ledger_ids"):
        if not isinstance(record.get(field), list):
            add(f"{field} must be a list")
    if run_root.name and record.get("run_id") and str(record.get("run_id")) != run_root.name:
        add("run_id must match current run")

    return issues, unresolved_hard_count


def _self_interrogation_status(
    project_root: Path,
    run_root: Path,
    *,
    scopes: Iterable[str] | None = None,
    node_id: str | None = None,
    route_version: int | None = None,
    require_index: bool = True,
    require_records: bool = True,
) -> dict[str, Any]:
    index_path = _self_interrogation_index_path(run_root)
    index_rel = project_relative(project_root, index_path)
    issues: list[dict[str, str]] = []
    scope_filter = {str(scope) for scope in scopes} if scopes is not None else None
    records: list[dict[str, Any]] = []
    matched_scopes: set[str] = set()
    unresolved_hard_count = 0

    if not index_path.exists():
        if require_index:
            issues.append(_self_interrogation_issue("self-interrogation index is missing", record_path=index_rel))
        return {
            "path": str(index_path),
            "exists": False,
            "record_count": 0,
            "unresolved_hard_finding_count": unresolved_hard_count,
            "issue_count": len(issues),
            "clean": not issues,
            "issues": issues,
        }

    index = read_json(index_path)
    if index.get("schema_version") != SELF_INTERROGATION_INDEX_SCHEMA:
        issues.append(_self_interrogation_issue(f"index schema_version must be {SELF_INTERROGATION_INDEX_SCHEMA}", record_path=index_rel))
    raw_entries = index.get("records")
    if raw_entries is None:
        raw_entries = index.get("entries")
    if not isinstance(raw_entries, list):
        issues.append(_self_interrogation_issue("self-interrogation index records must be a list", record_path=index_rel))
        raw_entries = []

    for entry in raw_entries:
        if not isinstance(entry, dict):
            issues.append(_self_interrogation_issue("self-interrogation index entry must be an object", record_path=index_rel))
            continue
        entry_scope = str(entry.get("scope") or "")
        if scope_filter is not None and entry_scope and entry_scope not in scope_filter:
            continue
        raw_record_path = _self_interrogation_entry_path(entry)
        if not raw_record_path:
            issues.append(_self_interrogation_issue("self-interrogation index entry requires record_path", record_path=index_rel, scope=entry_scope))
            continue
        record_path = resolve_project_path(project_root, raw_record_path)
        record_rel = project_relative(project_root, record_path)
        if not record_path.exists():
            issues.append(_self_interrogation_issue("self-interrogation record path is missing", record_path=record_rel, scope=entry_scope))
            continue
        record = read_json(record_path)
        record_scope = str(record.get("scope") or entry_scope)
        if scope_filter is not None and record_scope not in scope_filter:
            continue
        if node_id and record_scope in {"node_entry", "repair", "role_result"}:
            entry_node_id = str(entry.get("node_id") or "")
            record_node_id = str(record.get("node_id") or entry_node_id)
            if record_node_id != node_id:
                continue
        if route_version is not None:
            raw_route_version = record.get("route_version", entry.get("route_version"))
            if raw_route_version is not None:
                try:
                    if int(raw_route_version) != route_version:
                        continue
                except (TypeError, ValueError):
                    issues.append(_self_interrogation_issue("route_version must be an integer", record_path=record_rel, scope=record_scope))
                    continue
        matched_scopes.add(record_scope)
        record_issues, record_unresolved = _self_interrogation_record_issues(
            project_root,
            run_root,
            record_path,
            record,
            expected_scope=record_scope,
            expected_node_id=node_id,
            expected_route_version=route_version,
        )
        issues.extend(record_issues)
        unresolved_hard_count += record_unresolved
        records.append(
            {
                "record_id": str(record.get("record_id") or record_path.stem),
                "scope": record_scope,
                "path": record_rel,
                "unresolved_hard_finding_count": record_unresolved,
            }
        )

    if require_records and not records:
        if scope_filter:
            issues.append(
                _self_interrogation_issue(
                    "missing required self-interrogation record scope(s): " + ", ".join(sorted(scope_filter)),
                    record_path=index_rel,
                )
            )
        else:
            issues.append(_self_interrogation_issue("self-interrogation index has no records", record_path=index_rel))
    if scope_filter:
        missing_scopes = sorted(scope_filter - matched_scopes)
        if missing_scopes:
            issues.append(
                _self_interrogation_issue(
                    "missing required self-interrogation record scope(s): " + ", ".join(missing_scopes),
                    record_path=index_rel,
                )
            )

    return {
        "path": str(index_path),
        "exists": True,
        "record_count": len(records),
        "unresolved_hard_finding_count": unresolved_hard_count,
        "issue_count": len(issues),
        "clean": not issues and unresolved_hard_count == 0,
        "issues": issues,
        "records": records,
    }


def _format_self_interrogation_status_issue(status: dict[str, Any]) -> str:
    issues = status.get("issues") if isinstance(status.get("issues"), list) else []
    if not issues:
        return "unknown issue"
    first = issues[0] if isinstance(issues[0], dict) else {"message": str(issues[0])}
    location = first.get("record_path") or status.get("path") or ""
    return f"{first.get('message', 'unknown issue')} ({location})" if location else str(first.get("message") or "unknown issue")


def _require_clean_self_interrogation(
    project_root: Path,
    run_root: Path,
    *,
    gate_name: str,
    scopes: Iterable[str] | None = None,
    node_id: str | None = None,
    route_version: int | None = None,
) -> dict[str, Any]:
    status = _self_interrogation_status(
        project_root,
        run_root,
        scopes=scopes,
        node_id=node_id,
        route_version=route_version,
    )
    if not status["clean"]:
        raise RouterError(f"{gate_name} requires clean self-interrogation records: {_format_self_interrogation_status_issue(status)}")
    return status


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
    return flowpilot_router_event_identity._load_file_backed_role_payload(sys.modules[__name__], project_root, payload)


def _load_file_backed_role_payload_if_present(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_event_identity._load_file_backed_role_payload_if_present(sys.modules[__name__], project_root, payload)


def _record_event_envelope_ref_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    return flowpilot_router_event_identity._record_event_envelope_ref_from_payload(sys.modules[__name__], payload)


def _looks_like_record_event_envelope(payload: dict[str, Any] | None) -> bool:
    return flowpilot_router_event_identity._looks_like_record_event_envelope(sys.modules[__name__], payload)


def _payload_requires_record_event_envelope_validation(
    payload: dict[str, Any] | None,
    *,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> bool:
    return flowpilot_router_event_identity._payload_requires_record_event_envelope_validation(sys.modules[__name__], payload, envelope_path=envelope_path, envelope_hash=envelope_hash)


def _currently_allowed_external_events(run_state: dict[str, Any]) -> list[str]:
    return flowpilot_router_event_identity._currently_allowed_external_events(sys.modules[__name__], run_state)


def _record_event_expected_role(event: str, run_state: dict[str, Any]) -> str:
    return flowpilot_router_event_identity._record_event_expected_role(sys.modules[__name__], event, run_state)


def _record_event_from_role_matches(event: str, from_role: str, expected_role: str) -> bool:
    return flowpilot_router_event_identity._record_event_from_role_matches(sys.modules[__name__], event, from_role, expected_role)


def _validate_record_event_envelope(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    envelope: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_event_identity._validate_record_event_envelope(sys.modules[__name__], project_root, run_state, event=event, envelope=envelope)


def _load_record_event_envelope_ref(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    path: str,
    expected_hash: str,
) -> dict[str, Any]:
    return flowpilot_router_event_identity._load_record_event_envelope_ref(sys.modules[__name__], project_root, run_state, event=event, path=path, expected_hash=expected_hash)


def _normalize_record_event_payload(
    project_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    return flowpilot_router_event_identity._normalize_record_event_payload(sys.modules[__name__], project_root, run_state, event=event, payload=payload, envelope_path=envelope_path, envelope_hash=envelope_hash)


def _stable_identity_hash(value: Any) -> str:
    return flowpilot_router_event_identity._stable_identity_hash(sys.modules[__name__], value)


def _event_identity_ledger(run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_event_identity._event_identity_ledger(sys.modules[__name__], run_state)


def _payload_view_for_event_identity(project_root: Path, event: str, payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_event_identity._payload_view_for_event_identity(sys.modules[__name__], project_root, event, payload)


def _payload_body_hash(payload_view: dict[str, Any]) -> str:
    return flowpilot_router_event_identity._payload_body_hash(sys.modules[__name__], payload_view)


def _frontier_for_event_identity(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_event_identity._frontier_for_event_identity(sys.modules[__name__], run_root)


def _active_control_blocker_for_identity(run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_event_identity._active_control_blocker_for_identity(sys.modules[__name__], run_state)


def _route_mutation_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._route_mutation_identity_scope(sys.modules[__name__], run_root, run_state, payload_view)


def _control_blocker_repair_decision_identity_scope(payload_view: dict[str, Any], run_state: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._control_blocker_repair_decision_identity_scope(sys.modules[__name__], payload_view, run_state)


def _control_blocker_repair_outcome_identity_scope(
    payload_view: dict[str, Any],
    run_state: dict[str, Any],
    event: str,
) -> dict[str, str]:
    return flowpilot_router_event_identity._control_blocker_repair_outcome_identity_scope(sys.modules[__name__], payload_view, run_state, event)


def _gate_decision_identity_scope(run_root: Path, payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._gate_decision_identity_scope(sys.modules[__name__], run_root, payload_view)


def _startup_repair_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._startup_repair_identity_scope(sys.modules[__name__], run_root, run_state, payload_view)


def _route_draft_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._route_draft_identity_scope(sys.modules[__name__], payload_view)


def _current_node_completion_identity_scope(run_root: Path, run_state: dict[str, Any], payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._current_node_completion_identity_scope(sys.modules[__name__], run_root, run_state, payload_view)


def _pm_role_work_request_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._pm_role_work_request_identity_scope(sys.modules[__name__], payload_view)


def _role_work_result_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._role_work_result_identity_scope(sys.modules[__name__], payload_view)


def _current_node_result_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._current_node_result_identity_scope(sys.modules[__name__], payload_view)


def _pm_role_work_result_decision_identity_scope(payload_view: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_event_identity._pm_role_work_result_decision_identity_scope(sys.modules[__name__], payload_view)


def _scoped_event_identity(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_event_identity._scoped_event_identity(sys.modules[__name__], project_root, run_root, run_state, event, payload)


def _scoped_event_is_recorded(run_state: dict[str, Any], identity: dict[str, Any] | None) -> bool:
    return flowpilot_router_event_identity._scoped_event_is_recorded(sys.modules[__name__], run_state, identity)


def _check_scoped_event_retry_budget(run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    return flowpilot_router_event_identity._check_scoped_event_retry_budget(sys.modules[__name__], run_state, identity)


def _mark_scoped_event_recorded(run_state: dict[str, Any], identity: dict[str, Any] | None) -> None:
    return flowpilot_router_event_identity._mark_scoped_event_recorded(sys.modules[__name__], run_state, identity)


def _already_recorded_external_event_result(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
    scoped_identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return flowpilot_router_event_identity._already_recorded_external_event_result(sys.modules[__name__], project_root, run_root, run_state, event=event, payload=payload, scoped_identity=scoped_identity)


def _external_event_flag_replay_requires_new_processing(
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    flag: str,
    payload: dict[str, Any],
    scoped_identity: dict[str, Any] | None,
) -> bool:
    return flowpilot_router_event_identity._external_event_flag_replay_requires_new_processing(sys.modules[__name__], run_root, run_state, event=event, flag=flag, payload=payload, scoped_identity=scoped_identity)


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


def new_bootstrap_state(run_id: str | None=None, run_root_rel: str | None=None) -> dict[str, Any]:
    return flowpilot_router_runtime_state.new_bootstrap_state(sys.modules[__name__], run_id, run_root_rel)



def _create_startup_bootstrap_state(project_root: Path) -> dict[str, Any]:
    return flowpilot_router_runtime_state._create_startup_bootstrap_state(sys.modules[__name__], project_root)



def _load_existing_bootstrap_state(project_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_runtime_state._load_existing_bootstrap_state(sys.modules[__name__], project_root)



def load_bootstrap_state(project_root: Path, *, create_if_missing: bool=False, new_invocation: bool=False) -> dict[str, Any]:
    return flowpilot_router_runtime_state.load_bootstrap_state(sys.modules[__name__], project_root, create_if_missing=create_if_missing, new_invocation=new_invocation)



def save_bootstrap_state(project_root: Path, state: dict[str, Any]) -> None:
    return flowpilot_router_runtime_state.save_bootstrap_state(sys.modules[__name__], project_root, state)



def active_run_root(project_root: Path, state: dict[str, Any] | None=None) -> Path | None:
    return flowpilot_router_runtime_state.active_run_root(sys.modules[__name__], project_root, state)



def _resolve_run_root_target(
    project_root: Path,
    *,
    run_id: str | None = None,
    run_root: str | Path | None = None,
    bootstrap_state: dict[str, Any] | None = None,
) -> Path | None:
    return flowpilot_router_daemon_runtime._resolve_run_root_target(sys.modules[__name__], project_root, run_id=run_id, run_root=run_root, bootstrap_state=bootstrap_state)


def run_state_path(run_root: Path) -> Path:
    return flowpilot_router_runtime_state.run_state_path(sys.modules[__name__], run_root)



def new_run_state(run_id: str, run_root_rel: str, *, controller_core_loaded: bool=False) -> dict[str, Any]:
    return flowpilot_router_runtime_state.new_run_state(sys.modules[__name__], run_id, run_root_rel, controller_core_loaded=controller_core_loaded)



def load_run_state(project_root: Path, bootstrap_state: dict[str, Any] | None=None) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    return flowpilot_router_runtime_state.load_run_state(sys.modules[__name__], project_root, bootstrap_state)



def load_run_state_from_run_root(project_root: Path, run_root: Path) -> tuple[dict[str, Any], Path] | tuple[None, Path]:
    return flowpilot_router_runtime_state.load_run_state_from_run_root(sys.modules[__name__], project_root, run_root)



def save_run_state(run_root: Path, state: dict[str, Any]) -> None:
    return flowpilot_router_runtime_state.save_run_state(sys.modules[__name__], run_root, state)



def _append_router_daemon_event(run_root: Path, event: str, details: dict[str, Any] | None = None) -> None:
    return flowpilot_router_daemon_runtime._append_router_daemon_event(sys.modules[__name__], run_root, event, details)


def _acquire_router_daemon_lock(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    replace_stale: bool = False,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._acquire_router_daemon_lock(sys.modules[__name__], project_root, run_root, run_state, replace_stale=replace_stale)


def _refresh_router_daemon_lock(project_root: Path, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._refresh_router_daemon_lock(sys.modules[__name__], project_root, run_root)


def _release_router_daemon_lock(
    project_root: Path,
    run_root: Path,
    *,
    reason: str,
    status: str = "released",
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._release_router_daemon_lock(sys.modules[__name__], project_root, run_root, reason=reason, status=status)


def _empty_router_scheduler_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._empty_router_scheduler_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _read_router_scheduler_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._read_router_scheduler_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _write_router_scheduler_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._write_router_scheduler_ledger(sys.modules[__name__], project_root, run_root, run_state, ledger)



def _ensure_router_scheduler_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._ensure_router_scheduler_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _router_scheduler_ledger_summary(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._router_scheduler_ledger_summary(sys.modules[__name__], run_root)



def _router_scheduler_scope_for_action(action: dict[str, Any], run_root: Path) -> tuple[str, str]:
    return flowpilot_router_controller_scheduler._router_scheduler_scope_for_action(sys.modules[__name__], action, run_root)



def _action_is_startup_scoped(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_controller_scheduler._action_is_startup_scoped(sys.modules[__name__], action)



def _router_scheduler_progress_class(action: dict[str, Any]) -> str:
    return flowpilot_router_controller_scheduler._router_scheduler_progress_class(sys.modules[__name__], action)



def _router_scheduler_barrier_kind(action: dict[str, Any]) -> str:
    return flowpilot_router_controller_scheduler._router_scheduler_barrier_kind(sys.modules[__name__], action)



def _prepare_router_scheduled_action(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._prepare_router_scheduled_action(sys.modules[__name__], project_root, run_root, run_state, action)



def _record_router_scheduler_row(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], controller_entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._record_router_scheduler_row(sys.modules[__name__], project_root, run_root, run_state, action, controller_entry)



def _update_router_scheduler_row(project_root: Path, run_root: Path, run_state: dict[str, Any], *, row_id: str, router_state: str, reconciliation: dict[str, Any] | None=None) -> None:
    return flowpilot_router_controller_scheduler._update_router_scheduler_row(sys.modules[__name__], project_root, run_root, run_state, row_id=row_id, router_state=router_state, reconciliation=reconciliation)



def _controller_action_open_for(run_root: Path, *, action_type: str | None=None, postcondition: str | None=None, idempotency_key: str | None=None, label: str | None=None) -> bool:
    return flowpilot_router_controller_scheduler._controller_action_open_for(sys.modules[__name__], run_root, action_type=action_type, postcondition=postcondition, idempotency_key=idempotency_key, label=label)



def _router_ownership_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    return flowpilot_router_controller_scheduler._router_ownership_counts(sys.modules[__name__], entries)



def _empty_router_ownership_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._empty_router_ownership_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _read_router_ownership_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._read_router_ownership_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _write_router_ownership_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._write_router_ownership_ledger(sys.modules[__name__], project_root, run_root, run_state, ledger)



def _ensure_router_ownership_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._ensure_router_ownership_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _router_ownership_ledger_summary(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._router_ownership_ledger_summary(sys.modules[__name__], run_root)



def _record_router_ownership_entry(project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, action_type: str, router_state: str, workflow_owner: str, postcondition: str='', source: str, receipt_path: str | None=None, artifact_refs: dict[str, Any] | None=None, details: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._record_router_ownership_entry(sys.modules[__name__], project_root, run_root, run_state, action_id=action_id, action_type=action_type, router_state=router_state, workflow_owner=workflow_owner, postcondition=postcondition, source=source, receipt_path=receipt_path, artifact_refs=artifact_refs, details=details)



def _controller_action_completion_class(action: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_controller_scheduler._controller_action_completion_class(sys.modules[__name__], action)



def _controller_action_ledger_has_prompt_header(ledger: dict[str, Any]) -> bool:
    return flowpilot_router_controller_scheduler._controller_action_ledger_has_prompt_header(sys.modules[__name__], ledger)



def _write_controller_action_ledger(path: Path, ledger: dict[str, Any]) -> None:
    return flowpilot_router_controller_scheduler._write_controller_action_ledger(sys.modules[__name__], path, ledger)



def _rebuild_controller_action_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._rebuild_controller_action_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _ensure_controller_action_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._ensure_controller_action_ledger(sys.modules[__name__], project_root, run_root, run_state)



def _controller_action_ledger_summary(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._controller_action_ledger_summary(sys.modules[__name__], run_root)



def _write_controller_action_entry(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._write_controller_action_entry(sys.modules[__name__], project_root, run_root, run_state, action)



def _write_controller_receipt(project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._write_controller_receipt(sys.modules[__name__], project_root, run_root, run_state, action_id=action_id, status=status, payload=payload)



def _maybe_write_controller_receipt_for_pending(project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any], *, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._maybe_write_controller_receipt_for_pending(sys.modules[__name__], project_root, run_root, run_state, pending, status=status, payload=payload)



def _reconcile_controller_receipts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._reconcile_controller_receipts(sys.modules[__name__], project_root, run_root, run_state)



def _controller_wait_allowed_external_events(entry: dict[str, Any]) -> list[str]:
    raw_allowed = entry.get("allowed_external_events")
    if not isinstance(raw_allowed, list):
        action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
        raw_allowed = action.get("allowed_external_events")
    if not isinstance(raw_allowed, list):
        return []
    return [str(item) for item in raw_allowed if isinstance(item, str) and item.strip()]


def _external_event_payload_digest(payload: dict[str, Any] | None) -> str:
    try:
        encoded = json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")
    except TypeError:
        encoded = repr(payload or {}).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _close_waiting_controller_actions_for_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {"changed": False, "closed_count": 0, "closed_action_ids": []}
    now = utc_now()
    payload_digest = _external_event_payload_digest(payload)
    closed: list[dict[str, Any]] = []
    for action_path in sorted(action_dir.glob("*.json")):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get("status") != "waiting":
            continue
        action_type = str(entry.get("action_type") or "")
        if action_type != "await_role_decision":
            continue
        allowed_events = _controller_wait_allowed_external_events(entry)
        if event not in allowed_events:
            continue
        action_id = str(entry.get("action_id") or "")
        reconciliation = {
            "source": source,
            "event": event,
            "event_payload_sha256": payload_digest,
            "allowed_external_events": allowed_events,
            "reconciled_at": now,
            "controller_receipt_required": False,
        }
        entry["status"] = "done"
        entry["completed_at"] = now
        entry["completion_source"] = "router_external_event_reconciliation"
        entry["satisfied_by_external_event"] = event
        entry["satisfied_by_event_payload_sha256"] = payload_digest
        entry["router_reconciliation_status"] = "reconciled"
        entry["router_reconciled_at"] = now
        entry["router_reconciliation"] = reconciliation
        entry["controller_receipt_required"] = False
        entry["router_must_not_mark_done_without_controller_receipt"] = False
        write_json(action_path, entry)
        row_id = str(entry.get("router_scheduler_row_id") or "")
        if row_id:
            _update_router_scheduler_row(
                project_root,
                run_root,
                run_state,
                row_id=row_id,
                router_state="reconciled",
                reconciliation=reconciliation,
            )
        closed.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "label": entry.get("label"),
                "router_scheduler_row_id": row_id or None,
            }
        )
    pending = run_state.get("pending_action")
    pending_cleared = False
    if isinstance(pending, dict) and pending.get("action_type") == "await_role_decision":
        pending_allowed = [
            str(item)
            for item in (pending.get("allowed_external_events") or [])
            if isinstance(item, str) and item.strip()
        ]
        if event in pending_allowed:
            run_state["pending_action"] = None
            pending_cleared = True
    if not closed and not pending_cleared:
        return {"changed": False, "closed_count": 0, "closed_action_ids": []}
    ledger = _rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(
        run_state,
        "router_closed_controller_waits_satisfied_by_external_event",
        {
            "event": event,
            "source": source,
            "closed_count": len(closed),
            "closed_action_ids": [item["action_id"] for item in closed if item.get("action_id")],
            "pending_action_cleared": pending_cleared,
            "ledger_counts": ledger.get("counts"),
        },
    )
    return {
        "changed": True,
        "closed_count": len(closed),
        "closed_action_ids": [item["action_id"] for item in closed if item.get("action_id")],
        "pending_action_cleared": pending_cleared,
        "closed_actions": closed,
    }


def _pending_controller_action_id(pending_action: dict[str, Any]) -> str:
    action_id = str(pending_action.get("controller_action_id") or "").strip()
    if action_id:
        return action_id
    return _controller_action_id_for_action(pending_action)


def _pending_action_postcondition(pending_action: dict[str, Any]) -> str:
    postcondition = pending_action.get("postcondition")
    if isinstance(postcondition, str) and postcondition.strip():
        return postcondition.strip()
    contract = pending_action.get("next_step_contract")
    if isinstance(contract, dict):
        postcondition = contract.get("postcondition")
        if isinstance(postcondition, str) and postcondition.strip():
            return postcondition.strip()
    return ""


def _receipt_for_pending_controller_action(run_root: Path, pending_action: dict[str, Any]) -> dict[str, Any]:
    action_id = _pending_controller_action_id(pending_action)
    if not action_id:
        return {}
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get("schema_version") != CONTROLLER_RECEIPT_SCHEMA:
        return {}
    if str(receipt.get("action_id") or "") != action_id:
        return {}
    return receipt


def _pending_action_postcondition_satisfied(run_state: dict[str, Any], postcondition: str) -> bool:
    if not postcondition:
        return True
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(flags.get(postcondition))


def _mail_sequence_entry(mail_id: str) -> dict[str, str] | None:
    return next((entry for entry in MAIL_SEQUENCE if entry["mail_id"] == mail_id), None)


def _mail_role_obligation_contract(entry: dict[str, str]) -> dict[str, Any] | None:
    if entry.get("mail_id") != "user_intake":
        return None
    return {
        "schema_version": "flowpilot.mail_role_obligation.v1",
        "mail_id": "user_intake",
        "target_role": "project_manager",
        "mail_is_formal_work_material": True,
        "not_prompt_or_instruction_card": True,
        "first_output_instruction_card_id": "pm.material_scan",
        "first_expected_output_event": "pm_issues_material_and_capability_scan_packets",
        "first_expected_output_summary": (
            "PM opens user_intake, reads the full user request through the runtime, "
            "then produces material/capability scan packet specs for Router."
        ),
        "blocks_independent_pm_dispatch_until_first_output": True,
        "controller_visibility": "metadata_only",
    }


def _mail_delivery_matches(item: object, *, mail_id: str, to_role: str) -> bool:
    return (
        isinstance(item, dict)
        and str(item.get("mail_id") or "") == mail_id
        and str(item.get("to_role") or "") == to_role
    )


def _find_mail_delivery(deliveries: object, *, mail_id: str, to_role: str) -> dict[str, Any] | None:
    if not isinstance(deliveries, list):
        return None
    for item in deliveries:
        if _mail_delivery_matches(item, mail_id=mail_id, to_role=to_role):
            return item
    return None


def _count_unique_mail_deliveries(deliveries: object) -> int:
    if not isinstance(deliveries, list):
        return 0
    keys = {
        (str(item.get("mail_id") or ""), str(item.get("to_role") or ""))
        for item in deliveries
        if isinstance(item, dict) and item.get("mail_id") and item.get("to_role")
    }
    return len(keys)


def _packet_record_for_mail_delivery(ledger: dict[str, Any], *, packet_id: str) -> dict[str, Any] | None:
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return None
    for item in packets:
        if isinstance(item, dict) and str(item.get("packet_id") or "") == packet_id:
            return item
    return None


def _mail_delivery_action_envelope_path(
    project_root: Path,
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> Path | None:
    candidates: list[object] = []
    candidates.append(receipt_payload.get("packet_envelope_path"))
    allowed_reads = pending_action.get("allowed_reads")
    if isinstance(allowed_reads, list):
        candidates.extend(allowed_reads)
    for candidate in candidates:
        raw_path = str(candidate or "").strip()
        if not raw_path:
            continue
        path = resolve_project_path(project_root, raw_path)
        if path.exists():
            return path
    return None


def _mail_delivery_packet_released(record: dict[str, Any] | None, *, to_role: str) -> bool:
    if not isinstance(record, dict):
        return False
    relay = record.get("packet_controller_relay")
    if not isinstance(relay, dict):
        relay = record.get("controller_relay")
    return (
        str(record.get("active_packet_holder") or "") == to_role
        and str(record.get("active_packet_status") or "") == "envelope-relayed"
        and isinstance(relay, dict)
        and relay.get("delivered_via_controller") is True
        and str(relay.get("relayed_to_role") or "") == to_role
        and relay.get("body_was_read_by_controller") is False
        and relay.get("body_was_executed_by_controller") is False
    )


def _ensure_mail_delivery_packet_released(
    project_root: Path,
    run_root: Path,
    ledger: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
    *,
    mail_id: str,
    to_role: str,
    source: str,
) -> dict[str, Any]:
    record = _packet_record_for_mail_delivery(ledger, packet_id=mail_id)
    if record is None:
        raise RouterError(f"mail delivery packet record is missing: {mail_id}")
    if _mail_delivery_packet_released(record, to_role=to_role):
        return {
            "packet_released": True,
            "already_released": True,
            "packet_id": mail_id,
            "packet_envelope_path": record.get("packet_envelope_path"),
        }

    raw_packet_path = str(record.get("packet_envelope_path") or "").strip()
    if not raw_packet_path:
        raise RouterError(f"mail delivery packet envelope path is missing: {mail_id}")
    packet_envelope_path = resolve_project_path(project_root, raw_packet_path)
    if not packet_envelope_path.exists():
        raise RouterError(f"mail delivery packet envelope is missing: {raw_packet_path}")

    envelope = packet_runtime.load_envelope(project_root, packet_envelope_path)
    if str(envelope.get("packet_id") or "") != mail_id:
        raise RouterError(
            f"mail delivery packet envelope mismatch: expected {mail_id}, got {envelope.get('packet_id')!r}"
        )
    if str(envelope.get("to_role") or envelope.get("next_holder") or "") != to_role:
        raise RouterError(
            f"mail delivery packet target mismatch: expected {to_role}, got {envelope.get('to_role')!r}"
        )

    relayed = packet_runtime.controller_relay_envelope(
        project_root,
        envelope=envelope,
        envelope_path=packet_envelope_path,
        controller_agent_id=str(receipt_payload.get("controller_agent_id") or pending_action.get("controller_agent_id") or "controller"),
        received_from_role=str(envelope.get("from_role") or record.get("created_by_role") or "unknown"),
        relayed_to_role=to_role,
        body_was_read_by_controller=receipt_payload.get("controller_read_body") is True
        or receipt_payload.get("body_was_read_by_controller") is True,
        body_was_executed_by_controller=receipt_payload.get("controller_executed_body") is True
        or receipt_payload.get("body_was_executed_by_controller") is True,
        private_role_to_role_delivery_detected=receipt_payload.get("private_role_to_role_delivery_detected") is True,
    )
    action_envelope_path = _mail_delivery_action_envelope_path(project_root, pending_action, receipt_payload)
    if action_envelope_path is not None and action_envelope_path.resolve() != packet_envelope_path.resolve():
        write_json(action_envelope_path, relayed)

    updated_ledger_path = run_root / "packet_ledger.json"
    _raise_if_runtime_write_active(updated_ledger_path)
    updated_ledger = read_daemon_critical_json_if_exists(updated_ledger_path)
    updated_record = _packet_record_for_mail_delivery(updated_ledger, packet_id=mail_id)
    if not _mail_delivery_packet_released(updated_record, to_role=to_role):
        raise RouterError(f"mail delivery packet was not released to {to_role}")
    return {
        "packet_released": True,
        "already_released": False,
        "packet_id": mail_id,
        "packet_envelope_path": project_relative(project_root, packet_envelope_path),
        "source": source,
    }


def _fold_mail_delivery_postcondition(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any] | None = None,
    *,
    source: str,
) -> dict[str, Any]:
    receipt_payload = receipt_payload or {}
    mail_id = str(pending_action.get("mail_id") or receipt_payload.get("mail_id") or receipt_payload.get("packet_id") or "")
    if not mail_id:
        raise RouterError("mail delivery requires a mail_id")
    mail_entry = _mail_sequence_entry(mail_id)
    if mail_entry is None:
        raise RouterError(f"unknown mail in pending action: {mail_id}")
    to_role = str(
        pending_action.get("to_role")
        or receipt_payload.get("delivered_to_role")
        or receipt_payload.get("to_role")
        or mail_entry["to_role"]
    )
    if to_role != mail_entry["to_role"]:
        raise RouterError(f"mail delivery target mismatch for {mail_id}: expected {mail_entry['to_role']}, got {to_role}")
    payload_mail_id = str(receipt_payload.get("mail_id") or receipt_payload.get("packet_id") or "")
    if payload_mail_id and payload_mail_id != mail_id:
        raise RouterError(f"mail delivery receipt mail mismatch: expected {mail_id}, got {payload_mail_id}")
    payload_to_role = str(receipt_payload.get("delivered_to_role") or receipt_payload.get("to_role") or "")
    if payload_to_role and payload_to_role != to_role:
        raise RouterError(f"mail delivery receipt target mismatch: expected {to_role}, got {payload_to_role}")
    if receipt_payload.get("delivery_confirmed") is False:
        raise RouterError(f"mail delivery receipt for {mail_id} did not confirm delivery")

    ledger_path = run_root / "packet_ledger.json"
    _raise_if_runtime_write_active(ledger_path)
    ledger = read_daemon_critical_json_if_exists(ledger_path)
    ledger_mail = ledger.setdefault("mail", [])
    if not isinstance(ledger_mail, list):
        raise RouterError("packet ledger mail field must be a list")
    state_mail = run_state.setdefault("delivered_mail", [])
    if not isinstance(state_mail, list):
        raise RouterError("run state delivered_mail field must be a list")

    existing_ledger_delivery = _find_mail_delivery(ledger_mail, mail_id=mail_id, to_role=to_role)
    existing_state_delivery = _find_mail_delivery(state_mail, mail_id=mail_id, to_role=to_role)
    already_recorded = existing_ledger_delivery is not None and existing_state_delivery is not None
    if not run_state.get("ledger_check_requested") and existing_ledger_delivery is None:
        raise RouterError("mail delivery requires a current packet-ledger check")

    packet_release = _ensure_mail_delivery_packet_released(
        project_root,
        run_root,
        ledger,
        pending_action,
        receipt_payload,
        mail_id=mail_id,
        to_role=to_role,
        source=source,
    )
    _raise_if_runtime_write_active(ledger_path)
    ledger = read_daemon_critical_json_if_exists(ledger_path)
    ledger_mail = ledger.setdefault("mail", [])
    if not isinstance(ledger_mail, list):
        raise RouterError("packet ledger mail field must be a list")
    existing_ledger_delivery = _find_mail_delivery(ledger_mail, mail_id=mail_id, to_role=to_role)
    existing_state_delivery = _find_mail_delivery(state_mail, mail_id=mail_id, to_role=to_role)
    already_recorded = existing_ledger_delivery is not None and existing_state_delivery is not None

    delivery = existing_ledger_delivery or existing_state_delivery or {
        "mail_id": mail_id,
        "delivered_by": str(pending_action.get("delivered_by") or "controller"),
        "to_role": to_role,
        "delivered_at": utc_now(),
    }
    delivery.setdefault("packet_id", mail_id)
    if packet_release.get("packet_envelope_path"):
        delivery.setdefault("packet_envelope_path", packet_release.get("packet_envelope_path"))
    if receipt_payload.get("target_agent_id"):
        delivery.setdefault("target_agent_id", receipt_payload.get("target_agent_id"))
    if receipt_payload.get("delivery_channel"):
        delivery.setdefault("delivery_channel", receipt_payload.get("delivery_channel"))

    ledger_changed = False
    state_changed = False
    if existing_ledger_delivery is None:
        ledger_mail.append(delivery)
        ledger_changed = True
    if existing_state_delivery is None:
        state_mail.append(delivery)
        state_changed = True
    if ledger_changed or state_changed:
        run_state["mail_deliveries"] = max(
            int(run_state.get("mail_deliveries", 0)),
            _count_unique_mail_deliveries(state_mail),
            _count_unique_mail_deliveries(ledger_mail),
        )

    run_state.setdefault("flags", {})[mail_entry["flag"]] = True
    run_state["ledger_check_requested"] = False
    ledger["updated_at"] = utc_now()
    write_json(ledger_path, ledger)
    append_history(
        run_state,
        "router_folded_mail_delivery_postcondition",
        {
            "mail_id": mail_id,
            "to_role": to_role,
            "postcondition": mail_entry["flag"],
            "source": source,
            "already_recorded": already_recorded,
            "ledger_changed": ledger_changed,
            "state_changed": state_changed,
            "packet_release": packet_release,
        },
    )
    return {
        "applied": True,
        "source": source,
        "postcondition": mail_entry["flag"],
        "mail_id": mail_id,
        "to_role": to_role,
        "already_recorded": already_recorded,
        "ledger_changed": ledger_changed,
        "state_changed": state_changed,
        "packet_release": packet_release,
    }


def _controller_boundary_required_deliverable(project_root: Path, run_root: Path) -> dict[str, Any]:
    contract = CONTROLLER_STATEFUL_VALIDATOR_TABLE["confirm_controller_core_boundary"]
    return {
        "deliverable_id": contract["deliverable_id"],
        "artifact_kind": contract["artifact_kind"],
        "path": project_relative(project_root, _controller_boundary_confirmation_path(run_root)),
        "schema_version": CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
        "postcondition": contract["postcondition"],
        "validator": contract["validator"],
        "runtime_channel": contract["runtime_channel"],
        "output_type": contract["output_type"],
        "output_contract_id": contract["output_contract_id"],
        "required_role": "controller",
        "path_key": "confirmation_path",
        "hash_key": "confirmation_hash",
        "controller_may_read_sealed_bodies": False,
        "controller_may_approve_gates": False,
        "controller_may_mutate_route": False,
        "required_before_router_reconciles_done_receipt": True,
    }


def _controller_action_required_deliverables(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
) -> list[dict[str, Any]]:
    del run_state
    raw_required = action.get("required_deliverables")
    if isinstance(raw_required, list) and raw_required:
        return [item for item in raw_required if isinstance(item, dict)]
    raw_missing = action.get("missing_deliverables")
    if isinstance(raw_missing, list) and raw_missing:
        return [item for item in raw_missing if isinstance(item, dict)]
    action_type = str(action.get("action_type") or "")
    if action_type == "confirm_controller_core_boundary":
        return [_controller_boundary_required_deliverable(project_root, run_root)]
    repair_target = str(action.get("repair_target_action_type") or "")
    if action_type == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and repair_target == "confirm_controller_core_boundary":
        return [_controller_boundary_required_deliverable(project_root, run_root)]
    return []


def _controller_deliverable_contract(deliverables: list[dict[str, Any]]) -> dict[str, Any]:
    if not deliverables:
        return {}
    runtime_contracts = [
        {
            "deliverable_id": str(item.get("deliverable_id") or ""),
            "runtime_channel": str(item.get("runtime_channel") or ""),
            "output_type": str(item.get("output_type") or ""),
            "output_contract_id": str(item.get("output_contract_id") or ""),
            "required_role": str(item.get("required_role") or "controller"),
            "path_key": str(item.get("path_key") or ""),
            "hash_key": str(item.get("hash_key") or ""),
        }
        for item in deliverables
        if isinstance(item, dict) and item.get("runtime_channel")
    ]
    return {
        "schema_version": "flowpilot.controller_deliverable_contract.v1",
        "required_deliverables": deliverables,
        "runtime_contracts": runtime_contracts,
        "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "missing_deliverable_policy": "reclaim_existing_then_controller_repair_then_blocker",
        "router_must_not_synthesize_missing_controller_deliverable_during_receipt_reconciliation": True,
    }


def _missing_deliverables_for_apply_result(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    apply_result: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if isinstance(apply_result, dict):
        raw_missing = apply_result.get("missing_deliverables")
        if isinstance(raw_missing, list) and raw_missing:
            return [item for item in raw_missing if isinstance(item, dict)]
    return _controller_action_required_deliverables(project_root, run_root, run_state, action)


def _update_controller_action_entry_fields(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    action_id: str,
    status: str | None = None,
    fields: dict[str, Any] | None = None,
    router_state: str | None = None,
    reconciliation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not action_id:
        return {}
    path = _controller_action_path(run_root, action_id)
    entry = read_json_if_exists(path)
    if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return {}
    if status is not None:
        entry["status"] = status
    if fields:
        entry.update(fields)
    entry["updated_at"] = utc_now()
    write_json(path, entry)
    row_id = str(entry.get("router_scheduler_row_id") or "")
    if row_id and router_state:
        _update_router_scheduler_row(
            project_root,
            run_root,
            run_state,
            row_id=row_id,
            router_state=router_state,
            reconciliation=reconciliation or fields or {},
        )
    _rebuild_controller_action_ledger(project_root, run_root, run_state)
    return entry


def _defer_controller_postcondition_reconciliation_retry(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    entry: dict[str, Any],
    action: dict[str, Any],
    apply_result: dict[str, Any],
) -> dict[str, Any]:
    postcondition = str(
        apply_result.get("postcondition")
        or _pending_action_postcondition(action)
        or ""
    ).strip()
    if not postcondition:
        return {"retry_applicable": False, "reason": "no_postcondition"}

    action_id = str(entry.get("action_id") or action.get("controller_action_id") or "")
    attempts_used = int(entry.get("postcondition_reconciliation_attempts") or 0)
    max_attempts = CONTROLLER_POSTCONDITION_RECONCILIATION_MAX_ATTEMPTS
    if attempts_used >= max_attempts:
        return {
            "retry_applicable": True,
            "retry_pending": False,
            "retry_budget_exhausted": True,
            "direct_retry_attempts_used": attempts_used,
            "direct_retry_budget": max_attempts,
            "postcondition": postcondition,
        }

    next_attempt = attempts_used + 1
    now = utc_now()
    reconciliation = {
        "source": "controller_action_receipt_postcondition_retry_pending",
        "reason": str(apply_result.get("reason") or "postcondition_not_satisfied"),
        "postcondition": postcondition,
        "retry_attempt": next_attempt,
        "max_retry_attempts": max_attempts,
        "next_step": "retry_controller_receipt_reconciliation_before_pm_blocker",
        "apply_result": _json_safe(apply_result),
        "updated_at": now,
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=action_id,
        fields={
            "router_reconciliation_status": "retry_pending",
            "router_reconciliation_retry_pending_at": now,
            "router_reconciliation_retry_reason": reconciliation["reason"],
            "postcondition_reconciliation_attempts": next_attempt,
            "max_postcondition_reconciliation_attempts": max_attempts,
            "postcondition_reconciliation_exhausted": False,
            "router_reconciliation": reconciliation,
        },
        router_state="waiting",
        reconciliation=reconciliation,
    )
    append_history(
        run_state,
        "router_deferred_controller_receipt_postcondition_retry",
        {
            "action_type": action.get("action_type"),
            "controller_action_id": action_id,
            "router_scheduler_row_id": entry.get("router_scheduler_row_id") or action.get("router_scheduler_row_id"),
            "postcondition": postcondition,
            "retry_attempt": next_attempt,
            "max_retry_attempts": max_attempts,
        },
    )
    save_run_state(run_root, run_state)
    return {
        "retry_applicable": True,
        "retry_pending": True,
        "retry_budget_exhausted": False,
        "direct_retry_attempts_used": next_attempt,
        "direct_retry_budget": max_attempts,
        "postcondition": postcondition,
    }


def _sync_controller_boundary_confirmation_from_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        missing = [_controller_boundary_required_deliverable(project_root, run_root)]
        _record_router_ownership_entry(
            project_root,
            run_root,
            run_state,
            action_id=str(pending_action.get("controller_action_id") or ""),
            action_type=str(pending_action.get("action_type") or ""),
            router_state="router_reclaim_pending",
            workflow_owner="router",
            postcondition="controller_role_confirmed",
            source=source,
            receipt_path=str(pending_action.get("controller_receipt_path") or ""),
            details={
                "reason": "controller_boundary_confirmation_missing_or_invalid",
                "missing_deliverables": missing,
                "controller_receipt_payload": receipt_payload,
            },
        )
        return {
            "applied": False,
            "reason": "controller_boundary_confirmation_missing_or_invalid",
            "action_type": pending_action.get("action_type"),
            "repairable": True,
            "missing_deliverables": missing,
        }
    confirmation = run_state.get("controller_boundary_confirmation")
    if not isinstance(confirmation, dict) or not confirmation.get("path"):
        confirmation = {
            "path": project_relative(project_root, context["path"]),
            "sha256": context["sha256"],
            "controller_core_path": context["confirmation"].get("controller_core_path"),
            "controller_core_sha256": context["confirmation"].get("controller_core_sha256"),
            "controller_policy_sha256": context["confirmation"].get("controller_policy_sha256"),
        }
    confirmation.update(
        {
            "runtime_channel": "role_output_runtime",
            "output_type": CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
            "output_contract_id": CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
            "role_output_envelope": context.get("role_output_envelope"),
            "role_output_runtime_receipt_path": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("path")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
            "role_output_runtime_receipt_hash": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("hash")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
        }
    )
    run_state.setdefault("flags", {})["controller_role_confirmed"] = True
    run_state.setdefault("flags", {})["controller_role_confirmed_from_router_core"] = True
    run_state.setdefault("flags", {})["controller_boundary_confirmation_written"] = True
    run_state["controller_boundary_confirmation"] = confirmation
    if not any(
        isinstance(item, dict) and item.get("event") == "controller_role_confirmed_from_router_core"
        for item in run_state.get("events", [])
    ):
        run_state.setdefault("events", []).append(
            {
                "event": "controller_role_confirmed_from_router_core",
                "summary": "Controller confirmed the Router-delivered controller.core boundary.",
                "payload": confirmation,
                "recorded_at": utc_now(),
            }
        )
    entry = _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=str(pending_action.get("controller_action_id") or ""),
        action_type=str(pending_action.get("action_type") or ""),
        router_state="router_reclaimed",
        workflow_owner="router",
        postcondition="controller_role_confirmed",
        source=source,
        receipt_path=str(pending_action.get("controller_receipt_path") or ""),
        artifact_refs={
            "controller_boundary_confirmation_path": project_relative(project_root, context["path"]),
            "controller_boundary_confirmation_hash": context["sha256"],
        },
        details={"controller_receipt_payload": receipt_payload},
    )
    return {
        "applied": True,
        "postcondition": "controller_role_confirmed",
        "source": "router_owned_controller_boundary_confirmation_reclaim",
        "router_ownership_entry_id": entry.get("entry_id"),
    }


def _controller_boundary_flags_synced(run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(
        flags.get("controller_role_confirmed")
        and flags.get("controller_role_confirmed_from_router_core")
        and flags.get("controller_boundary_confirmation_written")
    )


def _router_scheduler_row_for_controller_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._router_scheduler_row_for_controller_entry(sys.modules[__name__], run_root, entry)



def _done_controller_receipt_for_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._done_controller_receipt_for_entry(sys.modules[__name__], run_root, entry)



def _reconcile_controller_boundary_confirmation_projection(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        return {"changed": False, "reason": "controller_boundary_confirmation_missing_or_invalid"}
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {"changed": False, "reason": "controller_action_dir_missing"}

    flags_were_synced = _controller_boundary_flags_synced(run_state)
    reconciled_actions: list[str] = []
    pending_cleared = False
    last_projection: dict[str, Any] | None = None

    for action_path in sorted(action_dir.glob("*.json")):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get("action_type") != "confirm_controller_core_boundary":
            continue
        if entry.get("status") != "done":
            continue
        receipt = _done_controller_receipt_for_entry(run_root, entry)
        if not receipt:
            continue
        action = dict(entry.get("action") if isinstance(entry.get("action"), dict) else {})
        action_id = str(entry.get("action_id") or action.get("controller_action_id") or "").strip()
        if not action_id:
            continue
        action.setdefault("action_type", "confirm_controller_core_boundary")
        action.setdefault("controller_action_id", action_id)
        action.setdefault("postcondition", "controller_role_confirmed")
        if entry.get("router_scheduler_row_id"):
            action.setdefault("router_scheduler_row_id", entry.get("router_scheduler_row_id"))
        action.setdefault(
            "controller_receipt_path",
            project_relative(project_root, _controller_receipt_path(run_root, action_id)),
        )
        row = _router_scheduler_row_for_controller_entry(run_root, entry)
        row_reconciled = bool(row.get("router_state") == "reconciled")
        entry_reconciled = bool(entry.get("router_reconciliation_status") == "reconciled")
        projection_missing = (
            not _controller_boundary_flags_synced(run_state)
            or not isinstance(run_state.get("controller_boundary_confirmation"), dict)
            or not run_state.get("controller_boundary_confirmation", {}).get("path")
        )
        if entry_reconciled and row_reconciled and not projection_missing:
            continue
        applied = _sync_controller_boundary_confirmation_from_artifact(
            project_root,
            run_root,
            run_state,
            action,
            receipt,
            source=source,
        )
        if not applied.get("applied"):
            continue
        reconciliation = dict(applied)
        reconciliation["projection_reconciliation_source"] = source
        now = utc_now()
        entry["status"] = "done"
        entry["router_reconciliation_status"] = "reconciled"
        entry["router_reconciled_at"] = now
        entry["router_reconciliation"] = reconciliation
        entry["updated_at"] = now
        write_json(action_path, entry)
        if entry.get("router_scheduler_row_id"):
            _update_router_scheduler_row(
                project_root,
                run_root,
                run_state,
                row_id=str(entry["router_scheduler_row_id"]),
                router_state="reconciled",
                reconciliation=reconciliation,
            )
        pending = run_state.get("pending_action")
        if isinstance(pending, dict) and (
            pending.get("controller_action_id") == action_id
            or pending.get("action_type") == "confirm_controller_core_boundary"
        ):
            run_state["pending_action"] = None
            pending_cleared = True
        reconciled_actions.append(action_id)
        last_projection = reconciliation

    changed = bool(reconciled_actions) or flags_were_synced != _controller_boundary_flags_synced(run_state)
    if not changed:
        return {"changed": False, "reason": "controller_boundary_projection_already_synced"}
    ledger = _rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(
        run_state,
        "router_reconciled_controller_boundary_projection",
        {
            "source": source,
            "reconciled_action_ids": reconciled_actions,
            "pending_action_cleared": pending_cleared,
            "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
            "ledger_counts": ledger.get("counts"),
            "projection": last_projection,
        },
    )
    return {
        "changed": True,
        "reconciled_action_ids": reconciled_actions,
        "pending_action_cleared": pending_cleared,
        "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
        "ledger_counts": ledger.get("counts"),
    }


def _mark_controller_deliverable_repair_resolved(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    repair_action: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    applied_postcondition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if str(repair_action.get("action_type") or "") != CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        return {}
    original_id = str(repair_action.get("repair_of_controller_action_id") or "")
    repair_id = str(
        (receipt or {}).get("action_id")
        or repair_action.get("controller_action_id")
        or ""
    )
    if not original_id:
        return {}
    now = utc_now()
    resolution = {
        "deliverable_status": "resolved",
        "resolution_status": "resolved_by_controller_repair",
        "resolved_at": now,
        "resolved_by_controller_action_id": repair_id,
        "pending_deliverable_repair_action_id": None,
        "pending_deliverable_repair_attempt": 0,
        "last_repair_result": applied_postcondition or {},
    }
    original = _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="resolved",
        fields=resolution,
        router_state="reconciled",
        reconciliation=resolution,
    )
    if repair_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=repair_id,
            fields={
                "router_reconciliation_status": "reconciled",
                "router_reconciled_at": now,
                "router_reconciliation": applied_postcondition or {},
            },
            router_state="reconciled",
            reconciliation=applied_postcondition or resolution,
        )
    append_history(
        run_state,
        "router_resolved_controller_action_by_deliverable_repair",
        {
            "original_controller_action_id": original_id,
            "repair_controller_action_id": repair_id,
            "original_action_type": original.get("action_type"),
        },
    )
    return original


def _controller_deliverable_failed_repair_ids(original_entry: dict[str, Any]) -> list[str]:
    raw = original_entry.get("deliverable_repair_failed_action_ids")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str) and item]


def _controller_repair_action_is_pending(run_root: Path, action_id: str) -> bool:
    if not action_id:
        return False
    action = read_json_if_exists(_controller_action_path(run_root, action_id))
    if action.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return False
    if action.get("status") in CONTROLLER_ACTION_CLOSED_STATUSES:
        return False
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get("schema_version") == CONTROLLER_RECEIPT_SCHEMA and receipt.get("status") in {"done", "blocked", "skipped"}:
        return False
    return True


def _write_controller_deliverable_budget_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    original_entry: dict[str, Any],
    current_action: dict[str, Any],
    receipt: dict[str, Any],
    missing_deliverables: list[dict[str, Any]],
    apply_result: dict[str, Any] | None,
) -> dict[str, Any]:
    original_id = str(original_entry.get("action_id") or "")
    current_id = str(receipt.get("action_id") or current_action.get("controller_action_id") or "")
    payload = {
        "controller_action_id": original_id,
        "current_controller_action_id": current_id,
        "action_type": original_entry.get("action_type"),
        "postcondition": _pending_action_postcondition(
            original_entry.get("action") if isinstance(original_entry.get("action"), dict) else current_action
        ),
        "missing_deliverables": missing_deliverables,
        "deliverable_repair_attempts": int(original_entry.get("deliverable_repair_attempts") or 0),
        "deliverable_repair_failed_receipts": int(original_entry.get("deliverable_repair_failed_receipts") or 0),
        "deliverable_repair_failed_action_ids": _controller_deliverable_failed_repair_ids(original_entry),
        "max_deliverable_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "controller_receipt_payload": receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {},
        "apply_result": apply_result or {},
    }
    now = utc_now()
    blocker = _write_control_blocker(
        project_root,
        run_root,
        run_state,
        source="controller_deliverable_repair_budget_exhausted",
        error_message=(
            f"Controller action {original_entry.get('action_type')} still lacks required deliverables "
            f"after {CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS} repair attempts."
        ),
        action_type=str(original_entry.get("action_type") or ""),
        payload=payload,
    )
    fields = {
        "deliverable_status": "blocked",
        "deliverable_repair_failed_receipts": int(original_entry.get("deliverable_repair_failed_receipts") or 0),
        "deliverable_repair_failed_action_ids": _controller_deliverable_failed_repair_ids(original_entry),
        "pending_deliverable_repair_action_id": None,
        "pending_deliverable_repair_attempt": 0,
        "router_reconciliation_status": "blocked",
        "router_reconciliation_blocked_at": now,
        "router_reconciliation_blocker": payload,
        "control_blocker_id": blocker.get("blocker_id"),
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="blocked",
        fields=fields,
        router_state="blocked",
        reconciliation=fields,
    )
    if current_id and current_id != original_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=current_id,
            status="blocked",
            fields=fields,
            router_state="blocked",
            reconciliation=fields,
        )
    _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        action_type=str(original_entry.get("action_type") or ""),
        router_state="blocked",
        workflow_owner="router",
        postcondition=str(payload.get("postcondition") or ""),
        source="controller_deliverable_repair_budget_exhausted",
        receipt_path=project_relative(project_root, _controller_receipt_path(run_root, current_id)) if current_id else "",
        details=payload,
    )
    return blocker


def _schedule_controller_deliverable_repair(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    pending_action: dict[str, Any],
    receipt: dict[str, Any],
    apply_result: dict[str, Any] | None = None,
    source: str,
) -> dict[str, Any]:
    missing_deliverables = _missing_deliverables_for_apply_result(
        project_root,
        run_root,
        run_state,
        pending_action,
        apply_result,
    )
    if not missing_deliverables:
        return {"scheduled": False, "repairable": False, "reason": "no_declared_missing_deliverables"}
    pending_action_id = str(receipt.get("action_id") or pending_action.get("controller_action_id") or "")
    if str(pending_action.get("action_type") or "") == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        original_id = str(pending_action.get("repair_of_controller_action_id") or "")
        repair_target_action_type = str(pending_action.get("repair_target_action_type") or "")
    else:
        original_id = pending_action_id
        repair_target_action_type = str(pending_action.get("action_type") or receipt.get("action_type") or "")
    if not original_id:
        return {"scheduled": False, "repairable": False, "reason": "missing_original_controller_action_id"}
    original_entry = read_json_if_exists(_controller_action_path(run_root, original_id))
    if original_entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return {"scheduled": False, "repairable": False, "reason": "missing_original_controller_action_entry"}
    issued_attempts = int(original_entry.get("deliverable_repair_attempts") or 0)
    failed_ids = _controller_deliverable_failed_repair_ids(original_entry)
    failed_receipts = int(original_entry.get("deliverable_repair_failed_receipts") or len(failed_ids) or 0)
    is_repair_receipt = str(pending_action.get("action_type") or "") == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE
    pending_repair_action_id = str(original_entry.get("pending_deliverable_repair_action_id") or "")
    pending_repair_attempt = int(original_entry.get("pending_deliverable_repair_attempt") or 0)
    if is_repair_receipt and pending_action_id:
        if pending_action_id not in failed_ids:
            failed_ids.append(pending_action_id)
            failed_receipts += 1
        if pending_repair_action_id == pending_action_id:
            pending_repair_action_id = ""
            pending_repair_attempt = 0
    if failed_receipts >= CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS:
        original_entry = {
            **original_entry,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": None,
            "pending_deliverable_repair_attempt": 0,
        }
        blocker = _write_controller_deliverable_budget_blocker(
            project_root,
            run_root,
            run_state,
            original_entry=original_entry,
            current_action=pending_action,
            receipt=receipt,
            missing_deliverables=missing_deliverables,
            apply_result=apply_result,
        )
        return {
            "scheduled": False,
            "blocked": True,
            "budget_exhausted": True,
            "blocker": blocker,
            "missing_deliverables": missing_deliverables,
        }
    if pending_repair_action_id and _controller_repair_action_is_pending(run_root, pending_repair_action_id):
        pending_fields = {
            "deliverable_status": "repair_pending",
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": pending_repair_action_id,
            "pending_deliverable_repair_attempt": pending_repair_attempt,
            "missing_deliverables": missing_deliverables,
            "last_incomplete_receipt_action_id": pending_action_id,
            "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "last_apply_result": apply_result or {},
            "router_reconciliation_status": "repair_pending",
            "router_reconciliation_updated_at": utc_now(),
        }
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=original_id,
            status="repair_pending",
            fields=pending_fields,
            router_state="waiting",
            reconciliation=pending_fields,
        )
        return {
            "scheduled": False,
            "pending_repair": True,
            "repairable": True,
            "missing_deliverables": missing_deliverables,
            "pending_repair_action_id": pending_repair_action_id,
            "pending_repair_attempt": pending_repair_attempt,
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
        }
    if issued_attempts >= CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS:
        pending_fields = {
            "deliverable_status": "repair_pending",
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": pending_repair_action_id or None,
            "pending_deliverable_repair_attempt": pending_repair_attempt,
            "missing_deliverables": missing_deliverables,
            "last_incomplete_receipt_action_id": pending_action_id,
            "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "last_apply_result": apply_result or {},
            "router_reconciliation_status": "repair_pending",
            "router_reconciliation_updated_at": utc_now(),
        }
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=original_id,
            status="repair_pending",
            fields=pending_fields,
            router_state="waiting",
            reconciliation=pending_fields,
        )
        return {
            "scheduled": False,
            "pending_repair": True,
            "repairable": True,
            "reason": "repair_attempt_issued_waiting_for_returned_evidence",
            "missing_deliverables": missing_deliverables,
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
        }
    next_attempt = issued_attempts + 1
    deliverable_paths = [
        str(item.get("path") or "")
        for item in missing_deliverables
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    original_action = original_entry.get("action") if isinstance(original_entry.get("action"), dict) else pending_action
    allowed_reads = [
        str(original_entry.get("action_path") or ""),
        project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
    ]
    allowed_reads.extend(str(path) for path in (original_action.get("allowed_reads") or []) if isinstance(path, str))
    repair_action = make_action(
        action_type=CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE,
        actor="controller",
        label=f"controller_completes_missing_deliverable_attempt_{next_attempt}_{original_id}",
        summary=(
            f"Complete missing Controller deliverable(s) for {repair_target_action_type}; "
            "Router will reconcile the original action only after the declared artifact validates."
        ),
        allowed_reads=[item for item in dict.fromkeys(allowed_reads) if item],
        allowed_writes=[item for item in dict.fromkeys(deliverable_paths + [project_relative(project_root, run_state_path(run_root))]) if item],
        extra={
            "postcondition": _pending_action_postcondition(original_action),
            "repair_of_controller_action_id": original_id,
            "repair_target_action_type": repair_target_action_type,
            "repair_attempt": next_attempt,
            "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
            "missing_deliverables": missing_deliverables,
            "required_deliverables": missing_deliverables,
            "runtime_output_contracts": _controller_deliverable_contract(missing_deliverables).get("runtime_contracts", []),
            "source_receipt_action_id": pending_action_id,
            "source_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "idempotency_key": f"controller-deliverable-repair:{original_id}:{next_attempt}",
            "scope_kind": str(original_entry.get("scope_kind") or pending_action.get("scope_kind") or "startup"),
            "scope_id": str(original_entry.get("scope_id") or pending_action.get("scope_id") or "startup"),
            "sealed_body_reads_allowed": False,
            "controller_may_create_project_evidence": False,
            "deliverable_repair_is_router_scheduled": True,
        },
    )
    repair_entry = _write_controller_action_entry(project_root, run_root, run_state, repair_action)
    repair_ids = [item for item in (original_entry.get("repair_action_ids") or []) if isinstance(item, str)]
    repair_ids.append(str(repair_entry.get("action_id") or ""))
    now = utc_now()
    original_fields = {
        "deliverable_status": "repair_pending",
        "deliverable_repair_attempts": next_attempt,
        "deliverable_repair_failed_receipts": failed_receipts,
        "deliverable_repair_failed_action_ids": failed_ids,
        "max_deliverable_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "missing_deliverables": missing_deliverables,
        "repair_action_ids": repair_ids,
        "pending_deliverable_repair_action_id": repair_entry.get("action_id"),
        "pending_deliverable_repair_attempt": next_attempt,
        "last_incomplete_receipt_action_id": pending_action_id,
        "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
        "last_apply_result": apply_result or {},
        "router_reconciliation_status": "repair_pending",
        "router_reconciliation_updated_at": now,
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="repair_pending",
        fields=original_fields,
        router_state="waiting",
        reconciliation=original_fields,
    )
    if pending_action_id and pending_action_id != original_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=pending_action_id,
            status="superseded",
            fields={
                "deliverable_status": "superseded_by_next_repair",
                "superseded_by_controller_action_id": repair_entry.get("action_id"),
                "router_reconciliation_status": "superseded_by_next_repair",
                "router_reconciliation_updated_at": now,
            },
            router_state="superseded",
            reconciliation={"superseded_by_controller_action_id": repair_entry.get("action_id")},
        )
    run_state["pending_action"] = repair_action
    _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        action_type=repair_target_action_type,
        router_state="router_reclaim_pending",
        workflow_owner="router",
        postcondition=str(original_fields.get("postcondition") or _pending_action_postcondition(original_action)),
        source=source,
        receipt_path=project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
        details={
            "missing_deliverables": missing_deliverables,
            "repair_controller_action_id": repair_entry.get("action_id"),
            "repair_attempt": next_attempt,
            "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
            "apply_result": apply_result or {},
        },
    )
    append_history(
        run_state,
        "router_scheduled_controller_deliverable_repair",
        {
            "original_controller_action_id": original_id,
            "repair_controller_action_id": repair_entry.get("action_id"),
            "repair_attempt": next_attempt,
            "missing_deliverables": missing_deliverables,
        },
    )
    return {
        "scheduled": True,
        "changed": True,
        "repair_action": repair_action,
        "repair_entry": repair_entry,
        "original_controller_action_id": original_id,
        "repair_attempt": next_attempt,
        "missing_deliverables": missing_deliverables,
    }


def _reclaim_router_owned_postcondition_from_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> dict[str, Any]:
    action_class = _controller_action_completion_class(pending_action)
    if action_class.get("kind") != "router_owned_durable_artifact":
        return {
            "applied": False,
            "reason": "not_router_owned_durable_artifact",
            "action_class": action_class,
        }

    action_type = str(pending_action.get("action_type") or "")
    action_id = str(pending_action.get("controller_action_id") or "")
    postcondition = str(action_class.get("postcondition") or _pending_action_postcondition(pending_action) or "")
    receipt_path = str(pending_action.get("controller_receipt_path") or "")

    if action_class.get("artifact_kind") == "startup_mechanical_audit":
        context = _startup_mechanical_audit_context(project_root, run_root, run_state)
        if context is None:
            _record_router_ownership_entry(
                project_root,
                run_root,
                run_state,
                action_id=action_id,
                action_type=action_type,
                router_state="router_reclaim_pending",
                workflow_owner="router",
                postcondition=postcondition,
                source="controller_receipt_reconciliation",
                receipt_path=receipt_path,
                details={
                    "reason": "startup_mechanical_audit_missing_or_invalid",
                    "controller_receipt_payload": receipt_payload,
                },
            )
            return {
                "applied": False,
                "reason": "startup_mechanical_audit_missing_or_invalid",
                "action_class": action_class,
            }

        run_state.setdefault("flags", {})[postcondition] = True
        run_state["startup_mechanical_audit"] = {
            "path": project_relative(project_root, context["audit_path"]),
            "sha256": context["audit_hash"],
            "proof_path": project_relative(project_root, context["proof_path"]),
            "proof_sha256": context["proof_hash"],
            "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
            "reclaimed_from_durable_artifact": True,
        }
        entry = _record_router_ownership_entry(
            project_root,
            run_root,
            run_state,
            action_id=action_id,
            action_type=action_type,
            router_state="router_reclaimed",
            workflow_owner="router",
            postcondition=postcondition,
            source="controller_receipt_reconciliation",
            receipt_path=receipt_path,
            artifact_refs={
                "artifact_kind": action_class.get("artifact_kind"),
                "startup_mechanical_audit_path": project_relative(project_root, context["audit_path"]),
                "startup_mechanical_audit_hash": context["audit_hash"],
                "router_owned_check_proof_path": project_relative(project_root, context["proof_path"]),
                "router_owned_check_proof_hash": context["proof_hash"],
            },
            details={
                "controller_receipt_payload": receipt_payload,
                "controller_receipt_did_not_mark_workflow_complete": True,
            },
        )
        append_history(
            run_state,
            "router_reclaimed_controller_receipt_artifact_postcondition",
            {
                "action_type": action_type,
                "controller_action_id": action_id,
                "postcondition": postcondition,
                "router_ownership_entry_id": entry.get("entry_id"),
            },
        )
        return {
            "applied": True,
            "postcondition": postcondition,
            "source": "router_owned_artifact_reclaim",
            "action_class": action_class,
            "router_ownership_entry_id": entry.get("entry_id"),
        }

    return {
        "applied": False,
        "reason": "unsupported_router_owned_artifact",
        "action_class": action_class,
    }


def _apply_stateful_receipt_postcondition(project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._apply_stateful_receipt_postcondition(sys.modules[__name__], project_root, run_root, run_state, pending_action, receipt_payload)



def _pending_return_matches_wait_target_reminder(record: dict[str, Any], action: dict[str, Any]) -> bool:
    return flowpilot_router_controller_scheduler._pending_return_matches_wait_target_reminder(sys.modules[__name__], record, action)



def _mark_pending_return_wait_reminded(run_root: Path, run_id: str, action: dict[str, Any], *, delivered_at: str, reminder_hash: str, receipt_payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._mark_pending_return_wait_reminded(sys.modules[__name__], run_root, run_id, action, delivered_at=delivered_at, reminder_hash=reminder_hash, receipt_payload=receipt_payload)



def _apply_wait_target_reminder_receipt(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._apply_wait_target_reminder_receipt(sys.modules[__name__], project_root, run_root, run_state, action, receipt_payload)



def _boot_action_meta(action_type: str) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._boot_action_meta(sys.modules[__name__], action_type)



def _matching_bootstrap_pending_action(bootstrap_state: dict[str, Any], action: dict[str, Any]) -> bool:
    return flowpilot_router_controller_scheduler._matching_bootstrap_pending_action(sys.modules[__name__], bootstrap_state, action)



def _apply_startup_bootloader_receipt_effects(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._apply_startup_bootloader_receipt_effects(sys.modules[__name__], project_root, run_root, run_state, action, receipt_payload)



def _clear_pending_after_reconciled_controller_receipt(project_root: Path, run_root: Path, run_state: dict[str, Any], *, pending_action: dict[str, Any], receipt: dict[str, Any], applied_postcondition: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._clear_pending_after_reconciled_controller_receipt(sys.modules[__name__], project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition=applied_postcondition)



def _reconcile_pending_controller_action_receipt(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._reconcile_pending_controller_action_receipt(sys.modules[__name__], project_root, run_root, run_state)



def _apply_done_controller_receipt_effects(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._apply_done_controller_receipt_effects(sys.modules[__name__], project_root, run_root, run_state, action, receipt)



def _scheduler_row_reconciliation_for_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._scheduler_row_reconciliation_for_entry(sys.modules[__name__], run_root, entry)



def _backfill_scheduler_row_from_reconciled_controller_action(project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], *, source: str) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._backfill_scheduler_row_from_reconciled_controller_action(sys.modules[__name__], project_root, run_root, run_state, entry, source=source)



def _canonicalize_legacy_startup_daemon_reconciliation(project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._canonicalize_legacy_startup_daemon_reconciliation(sys.modules[__name__], project_root, run_root, run_state, entry, action, receipt)



def _reconcile_scheduled_controller_action_receipts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._reconcile_scheduled_controller_action_receipts(sys.modules[__name__], project_root, run_root, run_state)



def _elapsed_seconds_since(raw_timestamp: object, *, now: datetime | None=None) -> int | None:
    return flowpilot_router_controller_scheduler._elapsed_seconds_since(sys.modules[__name__], raw_timestamp, now=now)



def _wait_target_path_exists(project_root: Path | None, raw_path: object) -> bool:
    return flowpilot_router_controller_scheduler._wait_target_path_exists(sys.modules[__name__], project_root, raw_path)



def _pending_wait_class(pending: dict[str, Any]) -> str:
    return flowpilot_router_controller_scheduler._pending_wait_class(sys.modules[__name__], pending)



def _wait_target_reminder_text(wait_class: str, target_role: str, wait_reason: str) -> str | None:
    return flowpilot_router_controller_scheduler._wait_target_reminder_text(sys.modules[__name__], wait_class, target_role, wait_reason)



def _wait_target_due_state(*, wait_class: str, elapsed_seconds: int | None, last_reminder_elapsed_seconds: int | None, evidence_exists: bool, liveness_probe_result: str) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._wait_target_due_state(sys.modules[__name__], wait_class=wait_class, elapsed_seconds=elapsed_seconds, last_reminder_elapsed_seconds=last_reminder_elapsed_seconds, evidence_exists=evidence_exists, liveness_probe_result=liveness_probe_result)



def _pending_wait_summary(run_state: dict[str, Any], *, project_root: Path | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._pending_wait_summary(sys.modules[__name__], run_state, project_root=project_root)



def _current_work_owner_kind(owner_key: str) -> str:
    return flowpilot_router_controller_scheduler._current_work_owner_kind(sys.modules[__name__], owner_key)



def _current_work_owner_label(owner_key: str) -> str:
    return flowpilot_router_controller_scheduler._current_work_owner_label(sys.modules[__name__], owner_key)



def _current_work_payload(*, owner_key: str, task_label: str, source: str, source_path: str | None=None, action_type: str | None=None, action_id: str | None=None, packet_id: str | None=None, wait_class: str | None=None, waiting_for_role: str | None=None, diagnostics: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._current_work_payload(sys.modules[__name__], owner_key=owner_key, task_label=task_label, source=source, source_path=source_path, action_type=action_type, action_id=action_id, packet_id=packet_id, wait_class=wait_class, waiting_for_role=waiting_for_role, diagnostics=diagnostics)



def _current_work_from_action(action: dict[str, Any], *, source: str, source_path: str | None=None, fallback_owner: str='controller') -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._current_work_from_action(sys.modules[__name__], action, source=source, source_path=source_path, fallback_owner=fallback_owner)



def _packet_status_allows_current_work(status: str) -> bool:
    return flowpilot_router_controller_scheduler._packet_status_allows_current_work(sys.modules[__name__], status)



def _current_work_from_packet_ledger(project_root: Path, run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._current_work_from_packet_ledger(sys.modules[__name__], project_root, run_root)



def _current_work_from_passive_waits(project_root: Path, run_root: Path, *, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._current_work_from_passive_waits(sys.modules[__name__], project_root, run_root, controller_ledger=controller_ledger)



def _derive_current_work(project_root: Path, run_root: Path, run_state: dict[str, Any], *, current_wait: dict[str, Any] | None=None, current_action: dict[str, Any] | None=None, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._derive_current_work(sys.modules[__name__], project_root, run_root, run_state, current_wait=current_wait, current_action=current_action, controller_ledger=controller_ledger)



def _wait_target_reminder_text_sha256(reminder_text: str) -> str:
    return flowpilot_router_controller_scheduler._wait_target_reminder_text_sha256(sys.modules[__name__], reminder_text)



def _wait_target_identity(pending: dict[str, Any], current_wait: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._wait_target_identity(sys.modules[__name__], pending, current_wait)



def _wait_target_reminder_payload_contract() -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._wait_target_reminder_payload_contract(sys.modules[__name__])



def _next_wait_target_reminder_action(project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._next_wait_target_reminder_action(sys.modules[__name__], project_root, run_root, run_state, pending_action, current_wait)



def _ensure_wait_target_reminder_controller_action(project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    return flowpilot_router_controller_scheduler._ensure_wait_target_reminder_controller_action(sys.modules[__name__], project_root, run_root, run_state, pending_action, current_wait)



def _continuous_standby_watch_label(current_wait: dict[str, Any]) -> str:
    return flowpilot_router_controller_scheduler._continuous_standby_watch_label(sys.modules[__name__], current_wait)



def _continuous_standby_release_conditions() -> list[str]:
    return flowpilot_router_controller_scheduler._continuous_standby_release_conditions(sys.modules[__name__])



def _continuous_standby_task_payload(project_root: Path, run_root: Path, current_wait: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._continuous_standby_task_payload(sys.modules[__name__], project_root, run_root, current_wait)



def _current_action_is_ordinary_controller_work(current_action: dict[str, Any] | None) -> bool:
    return flowpilot_router_controller_scheduler._current_action_is_ordinary_controller_work(sys.modules[__name__], current_action)



def _should_refresh_continuous_standby_row(run_state: dict[str, Any], *, lifecycle_status: str, current_action: dict[str, Any] | None) -> bool:
    return flowpilot_router_controller_scheduler._should_refresh_continuous_standby_row(sys.modules[__name__], run_state, lifecycle_status=lifecycle_status, current_action=current_action)



def _ensure_continuous_standby_controller_action(project_root: Path, run_root: Path, run_state: dict[str, Any], current_wait: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._ensure_continuous_standby_controller_action(sys.modules[__name__], project_root, run_root, run_state, current_wait)



def _write_router_daemon_status(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    lifecycle_status: str,
    current_action: dict[str, Any] | None = None,
    recovery_hints: list[str] | None = None,
    lock: dict[str, Any] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._write_router_daemon_status(sys.modules[__name__], project_root, run_root, run_state, lifecycle_status=lifecycle_status, current_action=current_action, recovery_hints=recovery_hints, lock=lock, error=error)


def _router_daemon_resume_recovery_summary(project_root: Path, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._router_daemon_resume_recovery_summary(sys.modules[__name__], project_root, run_root)


def _ensure_daemon_runtime_state(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    lifecycle_status: str = "manual_router_loop",
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._ensure_daemon_runtime_state(sys.modules[__name__], project_root, run_root, run_state, lifecycle_status=lifecycle_status)


def _formal_router_daemon_ready(project_root: Path, run_root: Path) -> bool:
    return flowpilot_router_daemon_runtime._formal_router_daemon_ready(sys.modules[__name__], project_root, run_root)


def _foreground_standby_pending_action_ids(ledger: dict[str, Any]) -> list[str]:
    return flowpilot_router_controller_scheduler._foreground_standby_pending_action_ids(sys.modules[__name__], ledger)



def _foreground_standby_waiting_action_ids(ledger: dict[str, Any]) -> list[str]:
    return flowpilot_router_controller_scheduler._foreground_standby_waiting_action_ids(sys.modules[__name__], ledger)



def _build_foreground_controller_standby_snapshot(project_root: Path, run_root: Path, run_state: dict[str, Any], *, started_at: str, start_monotonic: float, poll_count: int, max_seconds: float, poll_seconds: float) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._build_foreground_controller_standby_snapshot(sys.modules[__name__], project_root, run_root, run_state, started_at=started_at, start_monotonic=start_monotonic, poll_count=poll_count, max_seconds=max_seconds, poll_seconds=poll_seconds)



def foreground_controller_standby(project_root: Path, *, max_seconds: float=FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS, poll_seconds: float=FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS, bounded_diagnostic: bool=False) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler.foreground_controller_standby(sys.modules[__name__], project_root, max_seconds=max_seconds, poll_seconds=poll_seconds, bounded_diagnostic=bounded_diagnostic)



def controller_patrol_timer(project_root: Path, *, seconds: float=CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler.controller_patrol_timer(sys.modules[__name__], project_root, seconds=seconds)



def _tail_text(path: Path, *, max_chars: int = 2000) -> str:
    return flowpilot_router_daemon_runtime._tail_text(sys.modules[__name__], path, max_chars=max_chars)


def _spawn_startup_router_daemon_process(project_root: Path, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._spawn_startup_router_daemon_process(sys.modules[__name__], project_root, run_root)


def _start_or_attach_formal_router_daemon(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._start_or_attach_formal_router_daemon(sys.modules[__name__], project_root, run_root, run_state)


def _mark_router_daemon_terminal(project_root: Path, run_root: Path, run_state: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._mark_router_daemon_terminal(sys.modules[__name__], project_root, run_root, run_state, reason=reason)


def _ensure_startup_run_state(project_root: Path, bootstrap_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    run_id = str(bootstrap_state.get("run_id") or "")
    run_root_rel = str(bootstrap_state.get("run_root") or "")
    if not run_id or not run_root_rel:
        raise RouterError("startup run state requires run shell first")
    run_root = project_root / run_root_rel
    path = run_state_path(run_root)
    if path.exists():
        run_state = read_json(path)
        run_state.setdefault("flags", {})
        for flag, default in RUNTIME_FLAG_DEFAULTS.items():
            run_state["flags"].setdefault(flag, default)
        for entry in SYSTEM_CARD_SEQUENCE:
            run_state["flags"].setdefault(entry["flag"], False)
        for entry in MAIL_SEQUENCE:
            run_state["flags"].setdefault(entry["flag"], False)
        for event in EXTERNAL_EVENTS.values():
            run_state["flags"].setdefault(event["flag"], False)
        run_state.setdefault("history", [])
        run_state.setdefault("events", [])
        run_state.setdefault("pending_action", None)
        run_state.setdefault("daemon_mode_enabled", False)
        run_state.setdefault("router_daemon_status_path", None)
        run_state.setdefault("controller_action_ledger_path", None)
    else:
        run_state = new_run_state(run_id, run_root_rel, controller_core_loaded=False)
    if not (run_root / "execution_frontier.json").exists():
        write_json(run_root / "execution_frontier.json", _create_empty_execution_frontier(run_id))
    if not _continuation_binding_path(run_root).exists():
        _write_initial_continuation_binding(project_root, run_root, run_state)
    startup_lifecycle = "daemon_active" if run_state.get("daemon_mode_enabled") else "manual_router_loop"
    _ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status=startup_lifecycle)
    save_run_state(run_root, run_state)
    return run_state, run_root


def load_manifest_from_run(run_root: Path) -> dict[str, Any]:
    try:
        return load_card_manifest_from_run(run_root, runtime_kit_source())
    except PromptStoreError as exc:
        raise RouterError(str(exc)) from exc


def manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    try:
        return card_manifest_entry(manifest, card_id)
    except PromptStoreError as exc:
        raise RouterError(str(exc)) from exc


def _active_agent_id_for_role(run_root: Path, role: str) -> str | None:
    crew = read_json_if_exists(run_root / "crew_ledger.json")
    slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
    for slot in slots:
        if isinstance(slot, dict) and slot.get("role_key") == role:
            agent_id = slot.get("agent_id")
            if isinstance(agent_id, str) and agent_id.strip():
                return agent_id.strip()
    return None


def _pending_return_records(run_root: Path, run_id: str) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._pending_return_records(sys.modules[__name__], run_root, run_id)


def _card_return_resolved_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._card_return_resolved_for_action(sys.modules[__name__], run_root, run_id, action)


def _pending_card_return_ack_exists(project_root: Path, pending_action: object) -> bool:
    return flowpilot_router_card_returns._pending_card_return_ack_exists(sys.modules[__name__], project_root, pending_action)


CARD_RETURN_EVENT_BYPASS_EVENTS = {
    "heartbeat_or_manual_resume_requested",
    "controller_reports_role_liveness_fault",
    "controller_reports_role_no_output",
    "host_records_heartbeat_binding",
    "user_requests_run_stop",
    "user_requests_run_cancel",
}

STARTUP_REVIEW_BEGIN_JOIN_EVENTS = {
    "reviewer_reports_startup_facts",
}

PRE_REVIEW_STARTUP_CARD_IDS = {
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
}

STARTUP_ASYNC_CARD_IDS = {
    "reviewer.startup_fact_check",
    "pm.core",
    "pm.output_contract_catalog",
    "pm.role_work_request",
    "pm.phase_map",
    "pm.startup_intake",
    "pm.startup_activation",
}

REVIEWER_STARTUP_FACT_CARD_ID = "reviewer.startup_fact_check"


def _pending_return_card_ids(pending_return: dict[str, Any]) -> set[str]:
    return flowpilot_router_card_returns._pending_return_card_ids(sys.modules[__name__], pending_return)


def _pending_return_is_startup_async_scope(pending_return: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._pending_return_is_startup_async_scope(sys.modules[__name__], pending_return)


def _pending_return_is_pre_review_startup_scope(pending_return: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._pending_return_is_pre_review_startup_scope(sys.modules[__name__], pending_return)


def _startup_pre_review_card_flags() -> set[str]:
    return flowpilot_router_card_returns._startup_pre_review_card_flags(sys.modules[__name__])


def _startup_pre_review_cards_delivered(run_state: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._startup_pre_review_cards_delivered(sys.modules[__name__], run_state)


def _startup_pre_review_pending_returns(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._startup_pre_review_pending_returns(sys.modules[__name__], run_root, run_state)


def _startup_pre_review_ack_join_clean(run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._startup_pre_review_ack_join_clean(sys.modules[__name__], run_root, run_state)


CURRENT_SCOPE_REVIEWER_CARD_IDS = {
    "reviewer.worker_result_review",
}

CURRENT_SCOPE_REVIEW_EVENTS = {
    "current_node_reviewer_passes_result",
    "current_node_reviewer_blocks_result",
}


def _pending_return_matches_active_node_scope(pending_return: dict[str, Any], frontier: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._pending_return_matches_active_node_scope(sys.modules[__name__], pending_return, frontier)


def _pending_return_is_outside_active_node_scope(run_root: Path, pending_return: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._pending_return_is_outside_active_node_scope(sys.modules[__name__], run_root, pending_return)


def _current_node_pre_review_reconciliation_blockers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._current_node_pre_review_reconciliation_blockers(sys.modules[__name__], project_root, run_root, run_state)


def _startup_pre_review_reconciliation_blockers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._startup_pre_review_reconciliation_blockers(sys.modules[__name__], project_root, run_root, run_state)


def _pre_review_reconciliation_blockers_for_trigger(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    review_trigger: str,
) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._pre_review_reconciliation_blockers_for_trigger(sys.modules[__name__], project_root, run_root, run_state, review_trigger)


def _current_scope_pre_review_reconciliation_action(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    blockers: list[dict[str, Any]],
    review_trigger: str,
) -> dict[str, Any]:
    scope_kind = "startup" if any(blocker.get("scope_kind") == "startup" for blocker in blockers) else "current_node"
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    if scope_kind == "current_node":
        frontier = _active_frontier(run_root)
    active_node_id = str(frontier.get("active_node_id") or "")
    scope_id = "startup" if scope_kind == "startup" else active_node_id
    label = (
        "controller_waits_for_startup_scope_pre_review_reconciliation"
        if scope_kind == "startup"
        else "controller_waits_for_current_scope_pre_review_reconciliation"
    )
    summary = (
        "Startup reviewer work is blocked until startup-local obligations are reconciled."
        if scope_kind == "startup"
        else "Current-node reviewer work is blocked until local node obligations are reconciled."
    )
    allowed_reads = [
        project_relative(project_root, run_state_path(run_root)),
        project_relative(project_root, run_root / "execution_frontier.json"),
        project_relative(project_root, run_root / "return_event_ledger.json"),
        project_relative(project_root, _controller_action_ledger_path(run_root)),
        project_relative(project_root, _router_scheduler_ledger_path(run_root)),
    ]
    if scope_kind == "current_node":
        allowed_reads.append(project_relative(project_root, _parallel_packet_batch_ref_path(run_root, "current_node")))
    return make_action(
        action_type="await_current_scope_reconciliation",
        actor="controller",
        label=label,
        summary=summary,
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role="controller",
        extra={
            "apply_required": False,
            "scope_kind": scope_kind,
            "scope_id": scope_id,
            "route_id": frontier.get("active_route_id"),
            "route_version": frontier.get("route_version"),
            "review_trigger": review_trigger,
            "blockers": blockers,
            "local_scope_only": True,
            "future_or_sibling_scopes_touched": False,
            "reconciliation_rule": "resolve_or_explicitly_classify_current_scope_obligations_before_reviewer_work",
        },
    )


def _current_scope_reconciliation_wait_still_blocked(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
) -> bool:
    return flowpilot_router_card_returns._current_scope_reconciliation_wait_still_blocked(sys.modules[__name__], project_root, run_root, run_state, pending_action)


def _next_local_obligation_before_passive_wait(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._next_local_obligation_before_passive_wait(sys.modules[__name__], project_root, run_root, run_state, pending_action)


def _current_node_scope_exit_reconciliation_blockers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    frontier: dict[str, Any],
) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._current_node_scope_exit_reconciliation_blockers(sys.modules[__name__], project_root, run_root, run_state, frontier)


def _action_is_startup_async_delivery(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_card_returns._action_is_startup_async_delivery(sys.modules[__name__], action)


def _action_is_startup_async_card_wait(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_card_returns._action_is_startup_async_card_wait(sys.modules[__name__], action)


def _startup_async_pending_returns(
    run_root: Path,
    pending_returns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return flowpilot_router_card_returns._startup_async_pending_returns(sys.modules[__name__], run_root, pending_returns)


def _pending_card_return_blocker_for_event(
    run_root: Path,
    run_id: str,
    event: str,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._pending_card_return_blocker_for_event(sys.modules[__name__], run_root, run_id, event, run_state)


def _committed_card_artifact_extra(
    project_root: Path,
    record: dict[str, Any],
    *,
    relay_allowed_if_ready: bool,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._committed_card_artifact_extra(sys.modules[__name__], project_root, record, relay_allowed_if_ready=relay_allowed_if_ready)


def _next_pending_card_return_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending_records: list[dict[str, Any]] | None = None,
    *,
    clearance_reason: str = "router_progress",
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._next_pending_card_return_action(sys.modules[__name__], project_root, run_state, run_root, pending_records, clearance_reason=clearance_reason)


FORMAL_WORK_PACKET_RELAY_ACTION_TYPES = {
    "relay_material_scan_packets",
    "relay_research_packet",
    "relay_current_node_packet",
    "relay_pm_role_work_request_packet",
}


def _roles_from_action_to_role(action: dict[str, Any]) -> set[str]:
    raw = str(action.get("to_role") or "")
    roles = {role.strip() for role in raw.split(",") if role.strip()}
    return roles


def _apply_formal_work_packet_ack_preflight(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    if action.get("action_type") not in FORMAL_WORK_PACKET_RELAY_ACTION_TYPES:
        return action
    target_roles = _roles_from_action_to_role(action)
    if not target_roles:
        return action
    pending = [
        record
        for record in _pending_return_records(run_root, str(run_state["run_id"]))
        if str(record.get("target_role") or "") in target_roles
    ]
    preflight = {
        "schema_version": "flowpilot.formal_work_packet_ack_preflight.v1",
        "target_roles": sorted(target_roles),
        "source_ledger_path": project_relative(project_root, _return_event_ledger_path(run_root)),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
    if pending:
        wait_action = _next_pending_card_return_action(
            project_root,
            run_state,
            run_root,
            pending,
            clearance_reason="formal_work_packet_preflight",
        )
        if wait_action is None:
            return action
        blocked_packet = {
            "action_type": action.get("action_type"),
            "label": action.get("label"),
            "to_role": action.get("to_role"),
            "target_roles": sorted(target_roles),
        }
        wait_action["blocked_formal_work_packet"] = blocked_packet
        wait_action["formal_work_packet_ack_preflight"] = {
            **preflight,
            "passed": False,
            "pending_return_count": len(pending),
            "blocked_packet": blocked_packet,
        }
        wait_action["next_step_contract"]["formal_work_packet_ack_preflight"] = wait_action[
            "formal_work_packet_ack_preflight"
        ]
        return wait_action
    action["formal_work_packet_ack_preflight"] = {
        **preflight,
        "passed": True,
        "pending_return_count": 0,
    }
    action["ack_is_read_receipt_only"] = True
    action["target_work_completion_evidence_required_separately"] = True
    action["next_step_contract"]["formal_work_packet_ack_preflight"] = action["formal_work_packet_ack_preflight"]
    action["next_step_contract"]["ack_is_read_receipt_only"] = True
    action["next_step_contract"]["target_work_completion_evidence_required_separately"] = True
    return action


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
        PM_MODEL_MISS_TRIAGE_DECISION_EVENT,
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
    "pm.review_repair": (
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
}


def _dispatch_gate_card_entry(card_id: str) -> dict[str, Any] | None:
    return next((entry for entry in SYSTEM_CARD_SEQUENCE if entry.get("card_id") == card_id), None)


def _dispatch_gate_output_events_for_card_id(card_id: str) -> list[str]:
    entry = _dispatch_gate_card_entry(card_id)
    if not isinstance(entry, dict):
        return []
    card_flag = str(entry.get("flag") or "")
    output_events: list[str] = []
    for event, meta in EXTERNAL_EVENTS.items():
        if meta.get("requires_flag") == card_flag:
            output_events.append(event)
    output_events.extend(DISPATCH_RECIPIENT_GATE_CONTEXT_CARD_OUTPUT_EVENTS.get(card_id, ()))
    return list(dict.fromkeys(output_events))


def _dispatch_gate_output_events_for_action(action: dict[str, Any]) -> list[str]:
    output_events: list[str] = []
    for card_id in _dispatch_gate_system_card_ids(action):
        output_events.extend(_dispatch_gate_output_events_for_card_id(card_id))
    output_events.extend(DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS.get(str(action.get("action_type") or ""), ()))
    return list(dict.fromkeys(output_events))


def _dispatch_gate_action_is_ack_only_prompt(action: dict[str, Any]) -> bool:
    if action.get("action_type") not in {"deliver_system_card", "deliver_system_card_bundle"}:
        return False
    card_ids = _dispatch_gate_system_card_ids(action)
    return bool(card_ids) and not _dispatch_gate_output_events_for_action(action)


def _dispatch_gate_action_work_class(action: dict[str, Any]) -> str:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return "ack_only_prompt"
    if action.get("action_type") in {"deliver_system_card", "deliver_system_card_bundle"}:
        return "output_bearing_work_package"
    return "work_dispatch"


def _dispatch_gate_same_obligation_instruction_context(
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json")
    packets = packet_ledger.get("packets") if isinstance(packet_ledger, dict) else []
    if not isinstance(packets, list):
        return None
    for record in packets:
        if not isinstance(record, dict):
            continue
        holder = str(record.get("active_packet_holder") or "").strip()
        status = str(record.get("active_packet_status") or record.get("status") or "").strip()
        if holder not in target_roles or not _packet_status_allows_current_work(status):
            continue
        if _dispatch_gate_same_obligation_instruction(action, record, run_state):
            return {
                "packet_id": record.get("packet_id"),
                "active_packet_holder": holder,
                "instruction_card_id": action.get("card_id"),
                "expected_first_output_event": "pm_issues_material_and_capability_scan_packets",
            }
    return None


def _dispatch_gate_wait_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    blocked_action: dict[str, Any],
    blocker: dict[str, Any],
) -> dict[str, Any]:
    target_role = str(blocker.get("target_role") or "").strip()
    if not target_role:
        target_role = ",".join(sorted(_dispatch_gate_target_roles(blocked_action))) or "project_manager"
    allowed_events = [str(item) for item in blocker.get("allowed_external_events") or [] if str(item)]
    if not allowed_events:
        if target_role == "project_manager":
            allowed_events = [PM_ROLE_WORK_RESULT_DECISION_EVENT]
        else:
            allowed_events = [ROLE_WORK_RESULT_RETURNED_EVENT]
    source_path = str(blocker.get("source_path") or "").strip()
    allowed_reads = [project_relative(project_root, run_state_path(run_root))]
    if source_path and source_path not in allowed_reads:
        allowed_reads.append(source_path)
    payload_contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": "dispatch_recipient_gate_wait",
        "required_fields": [],
        "blocked_action_type": blocked_action.get("action_type"),
        "blocked_label": blocked_action.get("label"),
        "target_role": target_role,
        "busy_source": blocker.get("source"),
        "busy_reason": blocker.get("reason"),
        "packet_id": blocker.get("packet_id"),
        "request_id": blocker.get("request_id"),
        "blocked_work_package_class": blocker.get("blocked_work_package_class"),
        "blocked_output_events": blocker.get("blocked_output_events") or [],
        "controller_visibility": "metadata_only",
        "sealed_body_reads_allowed": False,
    }
    wait_action = make_action(
        action_type="await_role_decision",
        actor="controller",
        label=f"controller_waits_for_dispatch_recipient_idle_{_safe_delivery_component(target_role)}",
        summary=(
            "Controller must wait because Router blocked a new dispatch until "
            f"{target_role} finishes the prior unfinished obligation."
        ),
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=target_role,
        extra={
            "allowed_external_events": allowed_events,
            "controller_only_mode_active": True,
            "controller_may_create_project_evidence": False,
            "expected_wait_is_not_control_blocker": True,
            "payload_contract": payload_contract,
            "dispatch_recipient_gate": {
                "schema_version": "flowpilot.dispatch_recipient_gate.v1",
                "passed": False,
                "blocked_action_type": blocked_action.get("action_type"),
                "blocked_label": blocked_action.get("label"),
                "target_role": target_role,
                "busy_source": blocker.get("source"),
                "busy_reason": blocker.get("reason"),
                "packet_id": blocker.get("packet_id"),
                "request_id": blocker.get("request_id"),
                "blocked_work_package_class": blocker.get("blocked_work_package_class"),
                "blocked_output_events": blocker.get("blocked_output_events") or [],
                "source_path": source_path or None,
                "sealed_body_reads_allowed": False,
            },
        },
    )
    wait_action["nonblocking_wait"] = False
    return wait_action


def _dispatch_gate_pending_ack_wait(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    pending = [
        record
        for record in _pending_return_records(run_root, str(run_state["run_id"]))
        if str(record.get("target_role") or "") in target_roles
    ]
    if not pending:
        return None
    wait_action = _next_pending_card_return_action(
        project_root,
        run_state,
        run_root,
        pending,
        clearance_reason="dispatch_recipient_gate",
    )
    if wait_action is None:
        return None
    wait_action["dispatch_recipient_gate"] = {
        "schema_version": "flowpilot.dispatch_recipient_gate.v1",
        "passed": False,
        "blocked_action_type": action.get("action_type"),
        "blocked_label": action.get("label"),
        "target_roles": sorted(target_roles),
        "busy_source": "pending_return_ledger",
        "busy_reason": "target_role_ack_or_bundle_return_unresolved",
        "pending_return_count": len(pending),
        "blocked_work_package_class": _dispatch_gate_action_work_class(action),
        "blocked_output_events": _dispatch_gate_output_events_for_action(action),
        "source_path": project_relative(project_root, _return_event_ledger_path(run_root)),
        "sealed_body_reads_allowed": False,
    }
    wait_action.setdefault("next_step_contract", {})["dispatch_recipient_gate"] = wait_action["dispatch_recipient_gate"]
    return wait_action


def _dispatch_gate_packet_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
    candidate_packet_ids: set[str],
) -> dict[str, Any] | None:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return None
    packet_ledger_path = run_root / "packet_ledger.json"
    packet_ledger = read_json_if_exists(packet_ledger_path)
    packets = packet_ledger.get("packets") if isinstance(packet_ledger, dict) else []
    if not isinstance(packets, list):
        return None
    for record in packets:
        if not isinstance(record, dict):
            continue
        packet_id = str(record.get("packet_id") or "").strip()
        if packet_id and packet_id in candidate_packet_ids:
            continue
        if _dispatch_gate_packet_completed_by_flow_state(record, run_state):
            continue
        holder = str(record.get("active_packet_holder") or "").strip()
        status = str(record.get("active_packet_status") or record.get("status") or "").strip()
        if holder not in target_roles or not _packet_status_allows_current_work(status):
            continue
        if _dispatch_gate_same_obligation_instruction(action, record, run_state):
            continue
        return {
            "source": "packet_ledger",
            "source_path": project_relative(project_root, packet_ledger_path),
            "reason": "target_role_holds_unfinished_packet",
            "target_role": holder,
            "packet_id": packet_id or None,
            "active_packet_status": status,
            "blocked_work_package_class": _dispatch_gate_action_work_class(action),
            "blocked_output_events": _dispatch_gate_output_events_for_action(action),
            "allowed_external_events": _dispatch_gate_wait_events_for_packet_record(record),
        }
    return None


def _dispatch_gate_pending_expected_output_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return None
    candidate_output_events = set(_dispatch_gate_output_events_for_action(action))
    for group in _pending_expected_external_event_groups(run_state, run_root):
        wait_group = _gate_completion_wait_group(group)
        group_events = [event for event, _meta in wait_group]
        allowed_events = _filter_events_by_legal_route_actions(project_root, run_root, run_state, group_events)
        if not allowed_events:
            continue
        allowed_event_set = set(allowed_events)
        filtered_group = [(event, meta) for event, meta in wait_group if event in allowed_event_set]
        roles = {_event_wait_role(event, meta) for event, meta in filtered_group}
        overlapping_roles = roles.intersection(target_roles)
        if not overlapping_roles:
            continue
        if candidate_output_events and candidate_output_events.intersection(allowed_event_set):
            continue
        target_role = sorted(overlapping_roles)[0]
        return {
            "source": "pending_expected_output",
            "source_path": project_relative(project_root, run_state_path(run_root)),
            "reason": "target_role_output_obligation_already_pending",
            "target_role": target_role,
            "blocked_work_package_class": _dispatch_gate_action_work_class(action),
            "blocked_output_events": sorted(candidate_output_events),
            "allowed_external_events": allowed_events,
        }
    return None


def _dispatch_gate_pm_role_work_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
    candidate_packet_ids: set[str],
    candidate_request_ids: set[str],
) -> dict[str, Any] | None:
    index_path = _pm_role_work_request_index_path(run_root)
    index = _load_pm_role_work_request_index(run_root, run_state)
    for record in index.get("requests", []):
        if not isinstance(record, dict):
            continue
        request_id = str(record.get("request_id") or "").strip()
        packet_id = str(record.get("packet_id") or "").strip()
        if (request_id and request_id in candidate_request_ids) or (packet_id and packet_id in candidate_packet_ids):
            continue
        status = str(record.get("status") or "").strip()
        to_role = str(record.get("to_role") or "").strip()
        if to_role in target_roles and status in PM_ROLE_WORK_TARGET_BUSY_STATUSES:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "target_role_pm_role_work_unfinished",
                "target_role": to_role,
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
                "blocked_work_package_class": _dispatch_gate_action_work_class(action),
                "blocked_output_events": _dispatch_gate_output_events_for_action(action),
                "allowed_external_events": [ROLE_WORK_RESULT_RETURNED_EVENT],
            }
        if "project_manager" in target_roles and status in PM_ROLE_WORK_PM_BUSY_STATUSES:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "pm_role_work_result_disposition_pending",
                "target_role": "project_manager",
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
                "blocked_work_package_class": _dispatch_gate_action_work_class(action),
                "blocked_output_events": _dispatch_gate_output_events_for_action(action),
                "allowed_external_events": [PM_ROLE_WORK_RESULT_DECISION_EVENT],
            }
    return None


def _dispatch_gate_passive_wait_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    _run_router_return_settlement_finalizers(
        project_root,
        run_root,
        run_state,
        source="dispatch_recipient_gate_passive_wait_recheck",
    )
    controller_ledger = _controller_action_ledger_summary(run_root)
    passive_waits = controller_ledger.get("passive_waits") if isinstance(controller_ledger, dict) else []
    if not isinstance(passive_waits, list):
        return None
    for item in passive_waits:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").strip()
        reconciled = str(item.get("router_reconciliation_status") or "").strip()
        if status in {"done", "resolved", "skipped", "superseded"} or reconciled == "reconciled":
            continue
        target = str(item.get("waiting_for_role") or item.get("to_role") or item.get("target_role") or "").strip()
        if target not in target_roles:
            continue
        return {
            "source": "controller_action_ledger.passive_waits",
            "source_path": controller_ledger.get("path"),
            "reason": "target_role_wait_already_active",
            "target_role": target,
            "action_id": item.get("action_id"),
            "allowed_external_events": item.get("allowed_external_events") if isinstance(item.get("allowed_external_events"), list) else [],
        }
    return None


def _apply_dispatch_recipient_gate(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    if action.get("action_type") not in DISPATCH_RECIPIENT_GATE_ACTION_TYPES:
        return action
    target_roles = _dispatch_gate_target_roles(action)
    if not target_roles:
        return action
    _run_router_return_settlement_finalizers(
        project_root,
        run_root,
        run_state,
        source="dispatch_recipient_gate_return_settlement",
    )
    candidate_packet_ids = _dispatch_gate_candidate_packet_ids(action)
    candidate_request_ids = _dispatch_gate_candidate_request_ids(action)
    wait_action = _dispatch_gate_pending_ack_wait(project_root, run_state, run_root, action, target_roles)
    if wait_action is not None:
        return wait_action
    blocker = _dispatch_gate_passive_wait_blocker(project_root, run_root, run_state, target_roles)
    same_obligation_instruction = _dispatch_gate_same_obligation_instruction_context(
        run_root,
        run_state,
        action,
        target_roles,
    )
    if blocker is None:
        blocker = _dispatch_gate_pending_expected_output_blocker(project_root, run_root, run_state, action, target_roles)
    if blocker is None:
        blocker = _dispatch_gate_packet_blocker(project_root, run_root, run_state, action, target_roles, candidate_packet_ids)
    if blocker is None and not _dispatch_gate_action_is_ack_only_prompt(action):
        blocker = _dispatch_gate_pm_role_work_blocker(
            project_root,
            run_root,
            run_state,
            action,
            target_roles,
            candidate_packet_ids,
            candidate_request_ids,
        )
    if blocker is None:
        action["dispatch_recipient_gate"] = {
            "schema_version": "flowpilot.dispatch_recipient_gate.v1",
            "passed": True,
            "target_roles": sorted(target_roles),
            "candidate_packet_ids": sorted(candidate_packet_ids),
            "candidate_request_ids": sorted(candidate_request_ids),
            "grouped_delivery": action.get("action_type") == "deliver_system_card_bundle",
            "same_obligation_instruction": same_obligation_instruction,
            "work_package_class": _dispatch_gate_action_work_class(action),
            "output_events": _dispatch_gate_output_events_for_action(action),
            "sealed_body_reads_allowed": False,
        }
        action.setdefault("next_step_contract", {})["dispatch_recipient_gate"] = action["dispatch_recipient_gate"]
        return action
    return _dispatch_gate_wait_action(
        project_root,
        run_state,
        run_root,
        blocked_action=action,
        blocker=blocker,
    )


def append_history(state: dict[str, Any], label: str, details: dict[str, Any] | None = None) -> None:
    history = state.setdefault("history", [])
    history.append({"at": utc_now(), "label": label, "details": details or {}})


def _controller_user_reporting_policy() -> dict[str, Any]:
    return {
        "schema_version": CONTROLLER_USER_REPORTING_POLICY_SCHEMA,
        "plain_language_required": True,
        "reminder": (
            "If this action is mentioned to the user, explain it in plain "
            "language instead of copying internal action names or metadata."
        ),
        "allowed_user_report_points": [
            "what_is_happening_now",
            "what_flowpilot_is_waiting_for",
            "whether_user_needs_to_act",
        ],
        "hide_internal_metadata_by_default": [
            "event_names",
            "packet_ids",
            "ledger_names",
            "hashes",
            "action_ids",
            "contract_names",
            "diagnostic_file_paths",
        ],
        "technical_details_allowed_when_user_asks": True,
        "sealed_body_boundary_unchanged": True,
    }


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
    user_reporting_policy = _controller_user_reporting_policy()
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
    action["controller_user_reporting_policy"] = user_reporting_policy
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
        "controller_user_reporting_policy": user_reporting_policy,
    }
    if action.get("gate_contract") is not None:
        action["next_step_contract"]["gate_contract"] = action["gate_contract"]
    if action.get("ack_clearance_scope") is not None:
        action["next_step_contract"]["ack_clearance_scope"] = action["ack_clearance_scope"]
    if "ack_is_read_receipt_only" in action:
        action["next_step_contract"]["ack_is_read_receipt_only"] = bool(action.get("ack_is_read_receipt_only"))
    if "target_work_completion_evidence_required_separately" in action:
        action["next_step_contract"]["target_work_completion_evidence_required_separately"] = bool(
            action.get("target_work_completion_evidence_required_separately")
        )
    relay_or_wait_boundary = (
        action_type in ROUTER_READY_PREEMPTION_ACTION_TYPES
        or action_type.startswith("relay_")
        or action_type == "await_role_decision"
        or bool(action.get("relay_allowed"))
    )
    if actor == "controller" and relay_or_wait_boundary:
        policy = {
            "schema_version": "flowpilot.router_ready_preemption.v1",
            "router_ready_preempts_foreground_wait": True,
            "controller_must_scan_daemon_before_foreground_role_wait": True,
            "normal_router_progress_source": "router_daemon_status_and_controller_action_ledger",
            "allowed_router_reentry_commands": [],
            "diagnostic_router_reentry_commands": ["next", "run-until-wait"],
            "diagnostic_router_reentry_policy": (
                "diagnostic/test/explicit-repair only; not normal progress while daemon status "
                "and the Controller action ledger own the active run"
            ),
            "foreground_wait_agent_allowed": False,
            "foreground_role_chat_wait_allowed": False,
            "controlled_wait_records_allowed": [
                "await_card_return_event",
                "await_card_bundle_return_event",
                "await_role_decision",
            ],
            "liveness_wait_allowed_only_when_router_requests_recovery": True,
            "timeout_unknown_is_not_active": True,
            "sealed_body_reads_allowed": bool(action.get("sealed_body_reads_allowed", False)),
        }
        action["controller_after_relay_policy"] = policy
        action["next_step_contract"]["router_ready_preempts_foreground_wait"] = True
        action["next_step_contract"]["controller_must_scan_daemon_before_foreground_role_wait"] = True
        action["next_step_contract"]["normal_router_progress_source"] = "router_daemon_status_and_controller_action_ledger"
        action["next_step_contract"]["foreground_wait_agent_allowed"] = False
        action["next_step_contract"]["foreground_role_chat_wait_allowed"] = False
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


def _terminal_summary_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="terminal_summary_markdown_and_user_display_receipt",
        required_object="payload",
        required_fields=[
            "summary_markdown",
            "displayed_to_user",
            "displayed_summary_sha256",
            "read_scope_used",
        ],
        optional_fields=["source_paths_reviewed"],
        allowed_values={
            "displayed_to_user": [True],
            "read_scope_used": [TERMINAL_SUMMARY_READ_SCOPE],
        },
        structural_requirements=[
            f"summary_markdown must start with this exact attribution line: {TERMINAL_SUMMARY_ATTRIBUTION}",
            "displayed_summary_sha256 must equal sha256(summary_markdown)",
            "source_paths_reviewed, when supplied, may cite only files inside the current run root",
            "Controller must show this same summary text to the user before writing the Controller receipt or applying the direct terminal action",
            "The final user report is output-only and does not create completion authority",
        ],
        description=(
            "Write the final FlowPilot run summary after terminal mode is reached. "
            "This is a terminal-only read exception for all files inside the current run root."
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
            "lifecycle_reconciliation.self_interrogation_index_clean",
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
            "lifecycle_reconciliation.self_interrogation_index_clean": [True],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Approve closure only after clean final ledger, passed terminal backward replay, current completion projection, clean PM suggestion ledger, clean self-interrogation index, clean lifecycle ledgers, and continuation binding are present.",
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
    return flowpilot_router_events_repair._control_blocker_error_code(sys.modules[__name__], message)



def _blocker_repair_policy_snapshot_path(run_root: Path) -> Path:
    return flowpilot_router_events_repair._blocker_repair_policy_snapshot_path(sys.modules[__name__], run_root)



def _blocker_repair_policy_rows() -> list[dict[str, Any]]:
    return flowpilot_router_events_repair._blocker_repair_policy_rows(sys.modules[__name__])



def _write_blocker_repair_policy_snapshot(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str:
    return flowpilot_router_events_repair._write_blocker_repair_policy_snapshot(sys.modules[__name__], project_root, run_root, run_state)



def _control_blocker_policy_row(error_message: str, category: str) -> dict[str, Any]:
    return flowpilot_router_events_repair._control_blocker_policy_row(sys.modules[__name__], error_message, category)



def _control_blocker_attempt_key(*, policy_row_id: str, event: str | None, action_type: str | None, responsible_role: str) -> str:
    return flowpilot_router_events_repair._control_blocker_attempt_key(sys.modules[__name__], policy_row_id=policy_row_id, event=event, action_type=action_type, responsible_role=responsible_role)



def _control_blocker_direct_attempts_used(run_state: dict[str, Any], attempt_key: str) -> int:
    return flowpilot_router_events_repair._control_blocker_direct_attempts_used(sys.modules[__name__], run_state, attempt_key)



def _policy_first_handler_target(policy_row: dict[str, Any], responsible_role: str) -> str:
    return flowpilot_router_events_repair._policy_first_handler_target(sys.modules[__name__], policy_row, responsible_role)



def _pm_recovery_options_from_policy(policy_row: dict[str, Any]) -> list[str]:
    return flowpilot_router_events_repair._pm_recovery_options_from_policy(sys.modules[__name__], policy_row)



def _default_pm_recovery_option(active: dict[str, Any], requested_plan_kind: str) -> str:
    return flowpilot_router_events_repair._default_pm_recovery_option(sys.modules[__name__], active, requested_plan_kind)



def _project_relative_if_possible(project_root: Path, path: Path) -> str:
    return flowpilot_router_events_repair._project_relative_if_possible(sys.modules[__name__], project_root, path)



def _payload_source_paths(project_root: Path, run_root: Path, payload: dict[str, Any] | None) -> dict[str, str]:
    return flowpilot_router_events_repair._payload_source_paths(sys.modules[__name__], project_root, run_root, payload)



def _control_payload_public_view(payload: dict[str, Any] | None) -> dict[str, Any]:
    return flowpilot_router_events_repair._control_payload_public_view(sys.modules[__name__], payload)



def _infer_responsible_role(event: str | None, payload: dict[str, Any] | None, message: str) -> str:
    return flowpilot_router_events_repair._infer_responsible_role(sys.modules[__name__], event, payload, message)



def _classify_control_blocker(message: str, *, event: str | None=None, action_type: str | None=None, source: str | None=None) -> str:
    return flowpilot_router_events_repair._classify_control_blocker(sys.modules[__name__], message, event=event, action_type=action_type, source=source)



def _should_materialize_control_blocker(message: str, *, event: str | None=None, action_type: str | None=None, payload: dict[str, Any] | None=None) -> bool:
    return flowpilot_router_events_repair._should_materialize_control_blocker(sys.modules[__name__], message, event=event, action_type=action_type, payload=payload)



def _skill_observation_reminder(message: str, *, event: str | None=None, action_type: str | None=None, category: str | None=None) -> dict[str, Any]:
    return flowpilot_router_events_repair._skill_observation_reminder(sys.modules[__name__], message, event=event, action_type=action_type, category=category)



def _validated_external_event_names(events: Any, *, context: str, allow_pm_repair_event: bool=True) -> list[str]:
    return flowpilot_router_events_repair._validated_external_event_names(sys.modules[__name__], events, context=context, allow_pm_repair_event=allow_pm_repair_event)



def _active_node_kind_for_event_capability(run_root: Path | None) -> str | None:
    return flowpilot_router_events_repair._active_node_kind_for_event_capability(sys.modules[__name__], run_root)



def _event_capability_issue(event: str, *, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, currently_receivable: bool=True) -> str | None:
    return flowpilot_router_events_repair._event_capability_issue(sys.modules[__name__], event, run_root=run_root, run_state=run_state, usage=usage, repair_origin=repair_origin, outcome_kind=outcome_kind, currently_receivable=currently_receivable)



def _run_state_with_assumed_flag(run_state: dict[str, Any], flag: str) -> dict[str, Any]:
    return flowpilot_router_events_repair._run_state_with_assumed_flag(sys.modules[__name__], run_state, flag)



def _validated_event_capability_names(events: Any, *, context: str, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, allow_pm_repair_event: bool=True, currently_receivable: bool=True) -> list[str]:
    return flowpilot_router_events_repair._validated_event_capability_names(sys.modules[__name__], events, context=context, run_root=run_root, run_state=run_state, usage=usage, repair_origin=repair_origin, outcome_kind=outcome_kind, allow_pm_repair_event=allow_pm_repair_event, currently_receivable=currently_receivable)



def _external_event_validation_issue(events: Any) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._external_event_validation_issue(sys.modules[__name__], events)



def _control_blocker_allowed_resolution_events(category: str, event: str | None) -> list[str]:
    return flowpilot_router_events_repair._control_blocker_allowed_resolution_events(sys.modules[__name__], category, event)



def _control_blocker_policy(category: str, *, responsible_role: str, event: str | None, policy_row: dict[str, Any], target_role: str) -> dict[str, Any]:
    return flowpilot_router_events_repair._control_blocker_policy(sys.modules[__name__], category, responsible_role=responsible_role, event=event, policy_row=policy_row, target_role=target_role)



def _write_control_blocker_repair_packet(project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, category: str, target_role: str, responsible_role: str, error_message: str, event: str | None, action_type: str | None, payload: dict[str, Any] | None, policy_row: dict[str, Any], policy_snapshot_path: str, direct_retry_attempts_used: int, direct_retry_budget_exhausted: bool) -> dict[str, str]:
    return flowpilot_router_events_repair._write_control_blocker_repair_packet(sys.modules[__name__], project_root, run_root, run_state, blocker_id=blocker_id, category=category, target_role=target_role, responsible_role=responsible_role, error_message=error_message, event=event, action_type=action_type, payload=payload, policy_row=policy_row, policy_snapshot_path=policy_snapshot_path, direct_retry_attempts_used=direct_retry_attempts_used, direct_retry_budget_exhausted=direct_retry_budget_exhausted)



def _supersede_prior_control_blockers(run_root: Path, *, blocker_id: str, category: str, event: str | None, action_type: str | None, attempt_key: str | None=None) -> None:
    return flowpilot_router_events_repair._supersede_prior_control_blockers(sys.modules[__name__], run_root, blocker_id=blocker_id, category=category, event=event, action_type=action_type, attempt_key=attempt_key)



def _nonnegative_int_or_none(value: Any) -> int | None:
    return flowpilot_router_events_repair._nonnegative_int_or_none(sys.modules[__name__], value)



def _write_control_blocker(project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str, error_message: str, event: str | None=None, action_type: str | None=None, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_events_repair._write_control_blocker(sys.modules[__name__], project_root, run_root, run_state, source=source, error_message=error_message, event=event, action_type=action_type, payload=payload)



def _control_blocker_record(project_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._control_blocker_record(sys.modules[__name__], project_root, active)



def _control_blocker_matches_reconciled_action(record: dict[str, Any], *, action_type: str, controller_action_id: str, router_scheduler_row_id: str, postcondition: str, postcondition_satisfied: bool) -> str | None:
    return flowpilot_router_events_repair._control_blocker_matches_reconciled_action(sys.modules[__name__], record, action_type=action_type, controller_action_id=controller_action_id, router_scheduler_row_id=router_scheduler_row_id, postcondition=postcondition, postcondition_satisfied=postcondition_satisfied)



def _supersede_queued_control_blocker_actions(project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, resolved_at: str, resolution_status: str) -> int:
    return flowpilot_router_events_repair._supersede_queued_control_blocker_actions(sys.modules[__name__], project_root, run_root, run_state, blocker_id=blocker_id, resolved_at=resolved_at, resolution_status=resolution_status)



def _resolve_control_blockers_for_reconciled_controller_action(project_root: Path, run_root: Path, run_state: dict[str, Any], *, action: dict[str, Any], entry: dict[str, Any] | None=None, reconciliation: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_events_repair._resolve_control_blockers_for_reconciled_controller_action(sys.modules[__name__], project_root, run_root, run_state, action=action, entry=entry, reconciliation=reconciliation)



def _control_blocker_summary(record: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._control_blocker_summary(sys.modules[__name__], record)



def _resume_reentry_gate_pending(run_state: dict[str, Any]) -> bool:
    return flowpilot_router_events_repair._resume_reentry_gate_pending(sys.modules[__name__], run_state)



def _sync_protocol_blocker_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._sync_protocol_blocker_index(sys.modules[__name__], project_root, run_root, run_state)



def _sync_control_plane_indexes(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._sync_control_plane_indexes(sys.modules[__name__], project_root, run_root, run_state)



def _control_blocker_wait_events(record: dict[str, Any], *, run_root: Path | None=None, run_state: dict[str, Any] | None=None) -> tuple[list[str], dict[str, Any] | None]:
    return flowpilot_router_events_repair._control_blocker_wait_events(sys.modules[__name__], record, run_root=run_root, run_state=run_state)



def _event_producer_roles(allowed_events: list[str]) -> set[str]:
    return flowpilot_router_events_repair._event_producer_roles(sys.modules[__name__], allowed_events)



def _role_set(to_role: str) -> set[str]:
    return flowpilot_router_events_repair._role_set(sys.modules[__name__], to_role)



def _control_blocker_followup_target_role(allowed_events: list[str], fallback_role: str) -> str:
    return flowpilot_router_events_repair._control_blocker_followup_target_role(sys.modules[__name__], allowed_events, fallback_role)



def _validate_wait_event_producer_binding(allowed_events: list[str], *, to_role: str, context: str) -> None:
    return flowpilot_router_events_repair._validate_wait_event_producer_binding(sys.modules[__name__], allowed_events, to_role=to_role, context=context)



def _repair_transaction_for_control_blocker(project_root: Path, run_root: Path, record: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._repair_transaction_for_control_blocker(sys.modules[__name__], project_root, run_root, record)



def _make_operation_replay_action(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._make_operation_replay_action(sys.modules[__name__], project_root, run_root, run_state, record, transaction, execution_plan)



def _make_controller_repair_work_packet_action(project_root: Path, run_root: Path, record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._make_controller_repair_work_packet_action(sys.modules[__name__], project_root, run_root, record, transaction, execution_plan)



def _next_repair_transaction_executable_action(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._next_repair_transaction_executable_action(sys.modules[__name__], project_root, run_root, run_state, record)



def _next_control_blocker_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._next_control_blocker_action(sys.modules[__name__], project_root, run_state, run_root)



def _mark_control_blocker_delivered(project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._mark_control_blocker_delivered(sys.modules[__name__], project_root, run_root, run_state, pending)



def _validate_model_miss_officer_report_refs(project_root: Path, decision: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_events_repair._validate_model_miss_officer_report_refs(sys.modules[__name__], project_root, decision)



def _write_model_miss_triage_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    return flowpilot_router_events_repair._write_model_miss_triage_decision(sys.modules[__name__], project_root, run_root, run_state, payload)



def _repair_transaction_normalized_plan_kind(raw_plan_kind: str) -> tuple[str, str | None]:
    return flowpilot_router_events_repair._repair_transaction_normalized_plan_kind(sys.modules[__name__], raw_plan_kind)



def _event_already_recorded(run_state: dict[str, Any], event: str) -> bool:
    return flowpilot_router_events_repair._event_already_recorded(sys.modules[__name__], run_state, event)



def _controller_wait_entries_for_event(run_root: Path, event: str) -> list[dict[str, Any]]:
    return flowpilot_router_events_repair._controller_wait_entries_for_event(sys.modules[__name__], run_root, event)



def _existing_event_producer_evidence(run_root: Path, run_state: dict[str, Any], event: str) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._existing_event_producer_evidence(sys.modules[__name__], run_root, run_state, event)



def _list_field(value: Any, *, field: str, required: bool=True) -> list[str]:
    return flowpilot_router_events_repair._list_field(sys.modules[__name__], value, field=field, required=required)



def _repair_transaction_execution_plan(project_root: Path, run_root: Path, run_state: dict[str, Any], active: dict[str, Any], request: dict[str, Any], *, requested_plan_kind: str, legacy_plan_kind: str | None, rerun_target: str, repair_origin: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    return flowpilot_router_events_repair._repair_transaction_execution_plan(sys.modules[__name__], project_root, run_root, run_state, active, request, requested_plan_kind=requested_plan_kind, legacy_plan_kind=legacy_plan_kind, rerun_target=rerun_target, repair_origin=repair_origin, packet_specs=packet_specs)



def _write_control_blocker_repair_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._write_control_blocker_repair_decision(sys.modules[__name__], project_root, run_root, run_state, payload)



def _gate_decision_issue(field: str, message: str, owner: str='gate_owner') -> dict[str, str]:
    return flowpilot_router_events_repair._gate_decision_issue(sys.modules[__name__], field, message, owner)



def _gate_decision_safe_id(raw: str) -> str:
    return flowpilot_router_events_repair._gate_decision_safe_id(sys.modules[__name__], raw)



def _gate_decision_issues(project_root: Path, decision: dict[str, Any]) -> list[dict[str, str]]:
    return flowpilot_router_events_repair._gate_decision_issues(sys.modules[__name__], project_root, decision)



def _validate_gate_decision(project_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._validate_gate_decision(sys.modules[__name__], project_root, decision)



def _gate_decision_record_path(run_root: Path, gate_id: str) -> Path:
    return flowpilot_router_events_repair._gate_decision_record_path(sys.modules[__name__], run_root, gate_id)



def _gate_decision_summary(project_root: Path, record_path: Path, decision: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_events_repair._gate_decision_summary(sys.modules[__name__], project_root, record_path, decision)



def _write_gate_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._write_gate_decision(sys.modules[__name__], project_root, run_root, run_state, payload)



def _control_blocker_allows_resolution_event(record: dict[str, Any], event: str) -> bool:
    return flowpilot_router_events_repair._control_blocker_allows_resolution_event(sys.modules[__name__], record, event)



def _control_resolution_event_name(value: Any) -> str | None:
    return flowpilot_router_events_repair._control_resolution_event_name(sys.modules[__name__], value)



def _resolve_delivered_control_blocker(project_root: Path, run_root: Path, run_state: dict[str, Any], *, resolved_by_event: str, from_already_recorded_event: bool=False) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._resolve_delivered_control_blocker(sys.modules[__name__], project_root, run_root, run_state, resolved_by_event=resolved_by_event, from_already_recorded_event=from_already_recorded_event)



def _lifecycle_record_path(run_root: Path) -> Path:
    return run_root / "lifecycle" / "run_lifecycle.json"


def _terminal_summary_index_entry(project_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_terminal_ledger._terminal_summary_index_entry(sys.modules[__name__], project_root, run_state)



def _terminal_summary_written(project_root: Path, run_state: dict[str, Any], run_root: Path) -> bool:
    return flowpilot_router_terminal_ledger._terminal_summary_written(sys.modules[__name__], project_root, run_state, run_root)



def _terminal_summary_action(project_root: Path, run_state: dict[str, Any], run_root: Path, *, mode: str) -> dict[str, Any]:
    return flowpilot_router_terminal_ledger._terminal_summary_action(sys.modules[__name__], project_root, run_state, run_root, mode=mode)



def _validate_terminal_summary_payload(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> tuple[str, dict[str, Any]]:
    return flowpilot_router_terminal_ledger._validate_terminal_summary_payload(sys.modules[__name__], project_root, run_root, run_state, payload, mode=mode)



def _write_terminal_summary(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> dict[str, Any]:
    return flowpilot_router_terminal_ledger._write_terminal_summary(sys.modules[__name__], project_root, run_root, run_state, payload, mode=mode)



def _terminal_closure_suite_is_closed(run_root: Path) -> bool:
    return flowpilot_router_terminal_ledger._terminal_closure_suite_is_closed(sys.modules[__name__], run_root)



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
    flags = run_state.setdefault("flags", {})
    if mode == "stopped_by_user":
        flags["run_stopped_by_user"] = True
    elif mode == "cancelled_by_user":
        flags["run_cancelled_by_user"] = True
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
    if not _terminal_summary_written(project_root, run_state, run_root):
        run_state.setdefault("flags", {})["terminal_summary_card_delivered"] = True
        return _terminal_summary_action(project_root, run_state, run_root, mode=mode)
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


def _startup_bootloader_open_entries_by_action_type(project_root: Path, state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return flowpilot_router_startup_flow._startup_bootloader_open_entries_by_action_type(sys.modules[__name__], project_root, state)



def _startup_open_entry_progress_class(entry: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._startup_open_entry_progress_class(sys.modules[__name__], entry)



def _startup_bootloader_entry_is_nonblocking(entry: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._startup_bootloader_entry_is_nonblocking(sys.modules[__name__], entry)



def _startup_bootloader_action_depends_on_role_slots(action_type: str) -> bool:
    return flowpilot_router_startup_flow._startup_bootloader_action_depends_on_role_slots(sys.modules[__name__], action_type)



def _next_boot_action(project_root: Path | None, state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_boot_action(sys.modules[__name__], project_root, state)



def _bootstrap_startup_cancelled(state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._bootstrap_startup_cancelled(sys.modules[__name__], state)



def _startup_bootloader_has_remaining_work(state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._startup_bootloader_has_remaining_work(sys.modules[__name__], state)



def _startup_daemon_controls_bootstrap(state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._startup_daemon_controls_bootstrap(sys.modules[__name__], state)



def _daemon_scheduled_bootloader_action(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_startup_flow._daemon_scheduled_bootloader_action(sys.modules[__name__], action)



def compute_bootloader_action(project_root: Path, state: dict[str, Any], *, daemon_tick: bool=False) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow.compute_bootloader_action(sys.modules[__name__], project_root, state, daemon_tick=daemon_tick)



def _ensure_pending(state: dict[str, Any], action_type: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._ensure_pending(sys.modules[__name__], state, action_type)



def _set_boot_flag(project_root: Path, state: dict[str, Any], flag: str, label: str, details: dict[str, Any] | None=None) -> None:
    return flowpilot_router_startup_flow._set_boot_flag(sys.modules[__name__], project_root, state, flag, label, details)



def _startup_run_state_if_ready(project_root: Path, bootstrap_state: dict[str, Any]) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    return flowpilot_router_startup_flow._startup_run_state_if_ready(sys.modules[__name__], project_root, bootstrap_state)



def _sync_startup_bootstrap_flags_to_run_state(bootstrap_state: dict[str, Any], run_state: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._sync_startup_bootstrap_flags_to_run_state(sys.modules[__name__], bootstrap_state, run_state)



def _fold_stable_startup_role_flags_from_bootstrap(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._fold_stable_startup_role_flags_from_bootstrap(sys.modules[__name__], project_root, run_root, run_state)



def _complete_startup_daemon_bootloader_row(project_root: Path, bootstrap_state: dict[str, Any], scheduled_action: dict[str, Any], *, applied_action_type: str) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._complete_startup_daemon_bootloader_row(sys.modules[__name__], project_root, bootstrap_state, scheduled_action, applied_action_type=applied_action_type)



def _startup_daemon_schedule_bootloader_action(project_root: Path, run_root: Path, run_state: dict[str, Any], *, lock: dict[str, Any] | None=None, source: str='router_daemon_tick') -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_daemon_schedule_bootloader_action(sys.modules[__name__], project_root, run_root, run_state, lock=lock, source=source)



def _finish_bootloader_action(project_root: Path, state: dict[str, Any], scheduled_action: dict[str, Any], *, flag: str, label: str, action_type: str, result_extra: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._finish_bootloader_action(sys.modules[__name__], project_root, state, scheduled_action, flag=flag, label=label, action_type=action_type, result_extra=result_extra)



def _normalize_startup_question_stop_boundary(state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._normalize_startup_question_stop_boundary(sys.modules[__name__], state)



def _startup_intake_ui_launcher_ref(project_root: Path) -> str:
    return flowpilot_router_startup_flow._startup_intake_ui_launcher_ref(sys.modules[__name__], project_root)



def _startup_intake_output_dir_ref(project_root: Path, state: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._startup_intake_output_dir_ref(sys.modules[__name__], project_root, state)



def _startup_intake_result_payload_contract(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_intake_result_payload_contract(sys.modules[__name__], project_root, state)



def _startup_intake_ui_action_extra(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_intake_ui_action_extra(sys.modules[__name__], project_root, state)



def _confirmed_startup_intake(state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._confirmed_startup_intake(sys.modules[__name__], state)



_FORBIDDEN_STARTUP_INTAKE_BODY_KEYS = {
    "body_text",
    "content",
    "prompt_text",
    "raw_body",
    "raw_text",
    "request_text",
    "text",
    "user_prompt",
    "user_request_text",
}


def _forbidden_startup_intake_body_fields(payload: Any, prefix: str='') -> list[str]:
    return flowpilot_router_startup_flow._forbidden_startup_intake_body_fields(sys.modules[__name__], payload, prefix)



def _resolve_existing_project_file(project_root: Path, raw_path: Any, label: str) -> Path:
    return flowpilot_router_startup_flow._resolve_existing_project_file(sys.modules[__name__], project_root, raw_path, label)



def _same_project_file(project_root: Path, left: Any, right: Path) -> bool:
    return flowpilot_router_startup_flow._same_project_file(sys.modules[__name__], project_root, left, right)



def _startup_intake_result_path_from_payload(payload: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._startup_intake_result_path_from_payload(sys.modules[__name__], payload)



def _require_interactive_startup_intake_artifact(artifact: dict[str, Any], label: str) -> None:
    return flowpilot_router_startup_flow._require_interactive_startup_intake_artifact(sys.modules[__name__], artifact, label)



def _validate_startup_intake_result_payload(project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._validate_startup_intake_result_payload(sys.modules[__name__], project_root, payload)



def _apply_startup_intake_result_to_bootstrap(project_root: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._apply_startup_intake_result_to_bootstrap(sys.modules[__name__], project_root, state, payload)



def _validate_startup_answer_interpretation(payload: dict[str, Any], answers: dict[str, str]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._validate_startup_answer_interpretation(sys.modules[__name__], payload, answers)



def _validate_startup_answers(payload: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_startup_flow._validate_startup_answers(sys.modules[__name__], payload)



def _validate_user_request(payload: dict[str, Any]) -> dict[str, str]:
    return flowpilot_router_startup_flow._validate_user_request(sys.modules[__name__], payload)



def _copy_startup_intake_file(project_root: Path, run_root: Path, raw_path: str, target_name: str) -> Path:
    return flowpilot_router_startup_flow._copy_startup_intake_file(sys.modules[__name__], project_root, run_root, raw_path, target_name)



def _materialize_startup_intake_record(project_root: Path, state: dict[str, Any], run_root: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._materialize_startup_intake_record(sys.modules[__name__], project_root, state, run_root)



def _user_request_ref_from_startup_intake(project_root: Path, state: dict[str, Any], intake_record: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._user_request_ref_from_startup_intake(sys.modules[__name__], project_root, state, intake_record)



def _build_user_intake_body_from_ref(project_root: Path, user_request_ref: dict[str, Any], startup_answers: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._build_user_intake_body_from_ref(sys.modules[__name__], project_root, user_request_ref, startup_answers)



def _deterministic_bootstrap_seed_evidence_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._deterministic_bootstrap_seed_evidence_path(sys.modules[__name__], run_root)



def _write_startup_answers_record(project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._write_startup_answers_record(sys.modules[__name__], project_root, run_root, state)



def _initialize_mailbox_foundation(project_root: Path, run_root: Path, run_id: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._initialize_mailbox_foundation(sys.modules[__name__], project_root, run_root, run_id)



def _record_startup_user_request_ref(project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._record_startup_user_request_ref(sys.modules[__name__], project_root, run_root, state)



def _write_startup_user_intake_scaffold(project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._write_startup_user_intake_scaffold(sys.modules[__name__], project_root, run_root, state)



def _run_deterministic_startup_bootstrap_seed(project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._run_deterministic_startup_bootstrap_seed(sys.modules[__name__], project_root, state)



def _display_text_hash(display_text: str) -> str:
    return flowpilot_router_startup_flow._display_text_hash(sys.modules[__name__], display_text)



def _user_dialog_display_gate(fields: dict[str, Any], *, display_kind: str, display_text: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._user_dialog_display_gate(sys.modules[__name__], fields, display_kind=display_kind, display_text=display_text)



def _validate_display_confirmation(payload: dict[str, Any], *, action_type: str, display_kind: str, display_text: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._validate_display_confirmation(sys.modules[__name__], payload, action_type=action_type, display_kind=display_kind, display_text=display_text)



def _display_confirmation_for_action(payload: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._display_confirmation_for_action(sys.modules[__name__], payload, action)



def _append_user_dialog_display_ledger(project_root: Path, run_root: Path, record: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._append_user_dialog_display_ledger(sys.modules[__name__], project_root, run_root, record)



def _display_plan_display_kind(plan_projection: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._display_plan_display_kind(sys.modules[__name__], plan_projection)



def _display_plan_chat_markdown(plan_projection: dict[str, Any], *, display_kind: str) -> str:
    return flowpilot_router_startup_flow._display_plan_chat_markdown(sys.modules[__name__], plan_projection, display_kind=display_kind)



def _display_plan_user_dialog_fields(plan_projection: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._display_plan_user_dialog_fields(sys.modules[__name__], plan_projection)



def _startup_waiting_internal_display_fields() -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_waiting_internal_display_fields(sys.modules[__name__])



def _display_route_sign_user_dialog_fields(route_sign: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._display_route_sign_user_dialog_fields(sys.modules[__name__], route_sign)



def _startup_banner_display() -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_banner_display(sys.modules[__name__])



def _role_spawn_action_extra(state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_spawn_action_extra(sys.modules[__name__], state)



def _normalize_role_agent_records(state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._normalize_role_agent_records(sys.modules[__name__], state, payload)



def _latest_resume_tick_id(run_state: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._latest_resume_tick_id(sys.modules[__name__], run_state)



def _role_core_prompt_path(run_root: Path, role: str) -> Path:
    return flowpilot_router_startup_flow._role_core_prompt_path(sys.modules[__name__], run_root, role)



def _role_memory_path(run_root: Path, role: str) -> Path:
    return flowpilot_router_startup_flow._role_memory_path(sys.modules[__name__], run_root, role)



def _path_hash(path: Path) -> str | None:
    return flowpilot_router_startup_flow._path_hash(sys.modules[__name__], path)



def _role_core_prompt_delivery_payload(project_root: Path, run_root: Path, run_id: str, *, source_action: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_core_prompt_delivery_payload(sys.modules[__name__], project_root, run_root, run_id, source_action=source_action)



def _resume_role_context(project_root: Path, run_root: Path, run_state: dict[str, Any], role: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._resume_role_context(sys.modules[__name__], project_root, run_root, run_state, role)



def _resume_role_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._resume_role_contexts(sys.modules[__name__], project_root, run_root, run_state)



def _resume_liveness_probe_batch_id(run_state: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._resume_liveness_probe_batch_id(sys.modules[__name__], run_state)



def _role_recovery_dir(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._role_recovery_dir(sys.modules[__name__], run_root)



def _role_recovery_latest_transaction_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._role_recovery_latest_transaction_path(sys.modules[__name__], run_root)



def _role_recovery_state_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._role_recovery_state_path(sys.modules[__name__], run_root)



def _role_recovery_report_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._role_recovery_report_path(sys.modules[__name__], run_root)



def _role_recovery_target_roles(raw_roles: object, *, default_all: bool=False) -> list[str]:
    return flowpilot_router_startup_flow._role_recovery_target_roles(sys.modules[__name__], raw_roles, default_all=default_all)



def _latest_role_recovery_transaction(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._latest_role_recovery_transaction(sys.modules[__name__], run_root)



def _role_recovery_ready_context(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._role_recovery_ready_context(sys.modules[__name__], project_root, run_root, run_state)



def _reclaim_role_recovery_postcondition_from_report(project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._reclaim_role_recovery_postcondition_from_report(sys.modules[__name__], project_root, run_root, run_state, source=source)



def _current_crew_generation(crew: dict[str, Any]) -> int:
    return flowpilot_router_startup_flow._current_crew_generation(sys.modules[__name__], crew)



def _open_role_recovery_transaction(project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger_source: str, recovery_scope: str, target_role_keys: list[str], fault_payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._open_role_recovery_transaction(sys.modules[__name__], project_root, run_root, run_state, trigger_source=trigger_source, recovery_scope=recovery_scope, target_role_keys=target_role_keys, fault_payload=fault_payload)



def _role_recovery_payload_contract(run_root: Path, run_state: dict[str, Any], transaction: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_recovery_payload_contract(sys.modules[__name__], run_root, run_state, transaction)



def _load_role_recovery_state(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._load_role_recovery_state(sys.modules[__name__], project_root, run_root, run_state)



def _normalize_role_recovery_agent_records(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return flowpilot_router_startup_flow._normalize_role_recovery_agent_records(sys.modules[__name__], project_root, run_root, run_state, payload)



def _role_recovery_obligation_replay_path(run_root: Path, transaction_id: str) -> Path:
    return flowpilot_router_startup_flow._role_recovery_obligation_replay_path(sys.modules[__name__], run_root, transaction_id)



def _controller_action_entry_view(entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._controller_action_entry_view(sys.modules[__name__], entry)



def _controller_action_wait_roles(entry: dict[str, Any]) -> set[str]:
    return flowpilot_router_startup_flow._controller_action_wait_roles(sys.modules[__name__], entry)



def _role_recovery_action_sort_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return flowpilot_router_startup_flow._role_recovery_action_sort_key(sys.modules[__name__], entry)



def _role_recovery_pending_return_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._role_recovery_pending_return_for_action(sys.modules[__name__], run_root, run_id, action)



def _role_recovery_wait_candidates(project_root: Path, run_root: Path, run_state: dict[str, Any], target_roles: set[str]) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._role_recovery_wait_candidates(sys.modules[__name__], project_root, run_root, run_state, target_roles)



def _mark_controller_action_done_by_role_recovery(project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], *, evidence: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._mark_controller_action_done_by_role_recovery(sys.modules[__name__], project_root, run_root, run_state, candidate, evidence=evidence)



def _role_recovery_existing_event_for_wait(run_state: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._role_recovery_existing_event_for_wait(sys.modules[__name__], run_state, entry)



def _settle_role_recovery_candidate_if_evidence_exists(project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._settle_role_recovery_candidate_if_evidence_exists(sys.modules[__name__], project_root, run_root, run_state, candidate)



def _role_recovery_replacement_action(transaction: dict[str, Any], candidate: dict[str, Any], *, original_order: int) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_recovery_replacement_action(sys.modules[__name__], transaction, candidate, original_order=original_order)



def _supersede_role_recovery_original_wait(project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], replacement_entry: dict[str, Any], *, original_order: int) -> dict[str, Any]:
    return flowpilot_router_startup_flow._supersede_role_recovery_original_wait(sys.modules[__name__], project_root, run_root, run_state, candidate, replacement_entry, original_order=original_order)



def _plan_role_recovery_obligation_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction: dict[str, Any], records: list[dict[str, Any]], report_path: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._plan_role_recovery_obligation_replay(sys.modules[__name__], project_root, run_root, run_state, transaction=transaction, records=records, report_path=report_path)



def _role_no_output_liveness_result(payload: dict[str, Any] | None) -> str:
    return flowpilot_router_startup_flow._role_no_output_liveness_result(sys.modules[__name__], payload)



def _payload_indicates_role_no_output(payload: dict[str, Any] | None) -> bool:
    return flowpilot_router_startup_flow._payload_indicates_role_no_output(sys.modules[__name__], payload)



def _role_no_output_target_roles(payload: dict[str, Any] | None) -> list[str]:
    return flowpilot_router_startup_flow._role_no_output_target_roles(sys.modules[__name__], payload)



def _role_no_output_wait_candidate(project_root: Path, run_root: Path, run_state: dict[str, Any], *, target_role_keys: list[str], payload: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._role_no_output_wait_candidate(sys.modules[__name__], project_root, run_root, run_state, target_role_keys=target_role_keys, payload=payload)



def _role_no_output_reissue_attempt(candidate: dict[str, Any]) -> int:
    return flowpilot_router_startup_flow._role_no_output_reissue_attempt(sys.modules[__name__], candidate)



def _role_no_output_replacement_action(candidate: dict[str, Any], *, attempt: int) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_no_output_replacement_action(sys.modules[__name__], candidate, attempt=attempt)



def _supersede_role_no_output_original_wait(project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], replacement_entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._supersede_role_no_output_original_wait(sys.modules[__name__], project_root, run_root, run_state, candidate, replacement_entry)



def _record_role_no_output_reissue(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, source_event: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._record_role_no_output_reissue(sys.modules[__name__], project_root, run_root, run_state, payload, source_event=source_event)



def _write_role_recovery_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_role_recovery_report(sys.modules[__name__], project_root, run_root, run_state, payload)



def _resume_role_rehydration_action_extra(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._resume_role_rehydration_action_extra(sys.modules[__name__], project_root, run_root, run_state)



def _normalize_resume_role_agent_records(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._normalize_resume_role_agent_records(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_resume_role_rehydration_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_resume_role_rehydration_report(sys.modules[__name__], project_root, run_root, run_state, payload)



def _create_run_id() -> str:
    return flowpilot_router_runtime_state._create_run_id(sys.modules[__name__])



def _create_empty_packet_ledger(project_root: Path, run_id: str, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_runtime_state._create_empty_packet_ledger(sys.modules[__name__], project_root, run_id, run_root)



def _active_packet_ledger_record(packet_ledger: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_runtime_state._active_packet_ledger_record(sys.modules[__name__], packet_ledger)



def _packet_ledger_record_by_id(run_root: Path, packet_id: str) -> dict[str, Any] | None:
    return flowpilot_router_runtime_state._packet_ledger_record_by_id(sys.modules[__name__], run_root, packet_id)



def _derive_resume_next_recipient_from_packet_ledger(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_runtime_state._derive_resume_next_recipient_from_packet_ledger(sys.modules[__name__], run_root)



def _create_empty_execution_frontier(run_id: str) -> dict[str, Any]:
    return flowpilot_router_runtime_state._create_empty_execution_frontier(sys.modules[__name__], run_id)



def _set_pre_route_frontier_phase(run_root: Path, run_id: str, phase: str) -> None:
    return flowpilot_router_runtime_state._set_pre_route_frontier_phase(sys.modules[__name__], run_root, run_id, phase)



def _create_empty_role_memory(run_id: str, role: str) -> dict[str, Any]:
    return flowpilot_router_runtime_state._create_empty_role_memory(sys.modules[__name__], run_id, role)



def _role_memory_event_role(event: str, payload: dict[str, Any]) -> str | None:
    return flowpilot_router_runtime_state._role_memory_event_role(sys.modules[__name__], event, payload)



def _append_role_memory_delta(run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_runtime_state._append_role_memory_delta(sys.modules[__name__], run_root, run_state, event=event, payload=payload)



def _startup_answers_from_run(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_runtime_state._startup_answers_from_run(sys.modules[__name__], run_root)



def _scheduled_continuation_requested(answers: dict[str, Any]) -> bool:
    return flowpilot_router_runtime_state._scheduled_continuation_requested(sys.modules[__name__], answers)



def _continuation_binding_path(run_root: Path) -> Path:
    return flowpilot_router_runtime_state._continuation_binding_path(sys.modules[__name__], run_root)



def _continuation_quarantine_path(run_root: Path) -> Path:
    return flowpilot_router_runtime_state._continuation_quarantine_path(sys.modules[__name__], run_root)



def _build_continuation_quarantine_record(project_root: Path, run_root: Path, run_state: dict[str, Any], *, created_at: str) -> dict[str, Any]:
    return flowpilot_router_runtime_state._build_continuation_quarantine_record(sys.modules[__name__], project_root, run_root, run_state, created_at=created_at)



def _write_continuation_quarantine(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_runtime_state._write_continuation_quarantine(sys.modules[__name__], project_root, run_root, run_state, record)



def _stable_resume_launcher_contract() -> dict[str, Any]:
    return flowpilot_router_startup_flow._stable_resume_launcher_contract(sys.modules[__name__])



def _write_initial_continuation_binding(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_initial_continuation_binding(sys.modules[__name__], project_root, run_root, run_state)



def _write_host_heartbeat_binding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_resume.write_host_heartbeat_binding(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        payload,
    )

def _host_heartbeat_binding_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._host_heartbeat_binding_ready(sys.modules[__name__], run_root, run_state)



def _append_heartbeat_tick(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_resume.append_heartbeat_tick(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        payload,
    )

def _reset_resume_cycle_for_wakeup(run_state: dict[str, Any]) -> None:
    flowpilot_router_resume.reset_resume_cycle_for_wakeup(sys.modules[__name__], run_state)

def _defect_ledger_reconciliation_status(project_root: Path, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._defect_ledger_reconciliation_status(sys.modules[__name__], project_root, run_root)



def _role_memory_reconciliation_status(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._role_memory_reconciliation_status(sys.modules[__name__], project_root, run_root, run_state)



def _continuation_quarantine_reconciliation_status(project_root: Path, run_root: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._continuation_quarantine_reconciliation_status(sys.modules[__name__], project_root, run_root)



def _terminal_closure_reconciliation_status(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._terminal_closure_reconciliation_status(sys.modules[__name__], project_root, run_root, run_state)



def _closure_reconciliation_blocker_message(status: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._closure_reconciliation_blocker_message(sys.modules[__name__], status)



def _closure_reconciliation_entries(project_root: Path, status: dict[str, Any], *, route_version: int) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._closure_reconciliation_entries(sys.modules[__name__], project_root, status, route_version=route_version)



def _current_closure_state_clean(project_root: Path, run_root: Path) -> bool:
    return flowpilot_router_startup_flow._current_closure_state_clean(sys.modules[__name__], project_root, run_root)



def _invalidate_route_completion_if_dirty_before_closure(project_root: Path, run_state: dict[str, Any], run_root: Path) -> None:
    return flowpilot_router_startup_flow._invalidate_route_completion_if_dirty_before_closure(sys.modules[__name__], project_root, run_state, run_root)



def _startup_fact_checks(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    return flowpilot_router_startup_flow._startup_fact_checks(sys.modules[__name__], project_root, run_root, run_state)



def _startup_intake_record_context(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._startup_intake_record_context(sys.modules[__name__], project_root, run_root, run_state)



def _controller_boundary_confirmation_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._controller_boundary_confirmation_path(sys.modules[__name__], run_root)



def _run_manifest_path(run_root: Path) -> Path:
    return flowpilot_router_startup_flow._run_manifest_path(sys.modules[__name__], run_root)



def _controller_boundary_sources(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_startup_flow._controller_boundary_sources(sys.modules[__name__], run_root)



def _controller_boundary_constraints() -> dict[str, Any]:
    return flowpilot_router_startup_flow._controller_boundary_constraints(sys.modules[__name__])



def _legacy_pm_reset_boundary_confirmed(run_state: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._legacy_pm_reset_boundary_confirmed(sys.modules[__name__], run_state)



def _controller_boundary_confirmation_body(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._controller_boundary_confirmation_body(sys.modules[__name__], project_root, run_root, run_state)



def _controller_boundary_runtime_evidence_context(project_root: Path, run_root: Path, run_state: dict[str, Any], *, confirmation_path: Path, confirmation_hash: str) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._controller_boundary_runtime_evidence_context(sys.modules[__name__], project_root, run_root, run_state, confirmation_path=confirmation_path, confirmation_hash=confirmation_hash)



def _write_controller_boundary_confirmation(project_root: Path, run_root: Path, run_state: dict[str, Any], *, controller_agent_id: str | None=None, action_id: str | None=None, source_action_id: str | None=None) -> dict[str, Any]:
    return flowpilot_router_startup_flow._write_controller_boundary_confirmation(sys.modules[__name__], project_root, run_root, run_state, controller_agent_id=controller_agent_id, action_id=action_id, source_action_id=source_action_id)



def _record_controller_boundary_confirmation_from_core_load(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any] | None, *, source: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._record_controller_boundary_confirmation_from_core_load(sys.modules[__name__], project_root, run_root, run_state, action, receipt_payload, source=source)



def _controller_boundary_confirmation_context(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._controller_boundary_confirmation_context(sys.modules[__name__], project_root, run_root, run_state)



def _role_slots_have_host_spawn_receipts(role_slots: list[dict[str, Any]], run_id: str) -> bool:
    return flowpilot_router_startup_flow._role_slots_have_host_spawn_receipts(sys.modules[__name__], role_slots, run_id)



def _continuation_has_host_bound_automation_receipt(continuation_binding: dict[str, Any], run_id: str) -> bool:
    return flowpilot_router_startup_flow._continuation_has_host_bound_automation_receipt(sys.modules[__name__], continuation_binding, run_id)



def _startup_external_fact_requirements(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_startup_flow._startup_external_fact_requirements(sys.modules[__name__], run_root, run_state)



def _startup_fact_review_ownership(computed_checks: dict[str, bool], external_requirements: list[dict[str, Any]]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_fact_review_ownership(sys.modules[__name__], computed_checks, external_requirements)



def _write_startup_mechanical_audit(project_root: Path, run_root: Path, run_state: dict[str, Any], computed_checks: dict[str, bool]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._write_startup_mechanical_audit(sys.modules[__name__], project_root, run_root, run_state, computed_checks)



def _startup_mechanical_audit_context(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._startup_mechanical_audit_context(sys.modules[__name__], project_root, run_root, run_state)



def _startup_mechanical_audit_action_extra(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_mechanical_audit_action_extra(sys.modules[__name__], project_root, run_root, run_state)



def _validate_startup_external_fact_review(payload: dict[str, Any], requirements: list[dict[str, Any]], *, startup_mechanical_audit_hash: str | None=None) -> dict[str, Any]:
    return flowpilot_router_startup_flow._validate_startup_external_fact_review(sys.modules[__name__], payload, requirements, startup_mechanical_audit_hash=startup_mechanical_audit_hash)



def _write_startup_fact_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_startup_fact_report(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_startup_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_startup_activation(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_startup_repair_request(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_startup_repair_request(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_startup_protocol_dead_end(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_startup_flow._write_startup_protocol_dead_end(sys.modules[__name__], project_root, run_root, run_state, payload)



def _route_sign_payload(project_root: Path, *, write: bool, trigger: str, mark_chat_displayed: bool, cockpit_open: bool=False, mark_ui_displayed: bool=False) -> dict[str, Any]:
    return flowpilot_router_startup_flow._route_sign_payload(sys.modules[__name__], project_root, write=write, trigger=trigger, mark_chat_displayed=mark_chat_displayed, cockpit_open=cockpit_open, mark_ui_displayed=mark_ui_displayed)



def _startup_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return flowpilot_router_startup_flow._startup_route_sign_payload(sys.modules[__name__], project_root, write=write, mark_chat_displayed=mark_chat_displayed)



def _route_map_route_sign_payload(project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    return flowpilot_router_startup_flow._route_map_route_sign_payload(sys.modules[__name__], project_root, write=write, mark_chat_displayed=mark_chat_displayed)



def _route_sign_has_canonical_route(payload: dict[str, Any]) -> bool:
    return flowpilot_router_startup_flow._route_sign_has_canonical_route(sys.modules[__name__], payload)



def _display_surface_receipt_from_payload(payload: dict[str, Any], *, run_id: str, requested: str, selected_surface: str) -> dict[str, Any]:
    return flowpilot_router_startup_flow._display_surface_receipt_from_payload(sys.modules[__name__], payload, run_id=run_id, requested=requested, selected_surface=selected_surface)



def _write_display_surface_status(project_root: Path, run_root: Path, run_state: dict[str, Any], display_confirmation: dict[str, Any], payload: dict[str, Any] | None=None) -> None:
    return flowpilot_router_startup_flow._write_display_surface_status(sys.modules[__name__], project_root, run_root, run_state, display_confirmation, payload)



def _material_packet_body_text_from_spec(project_root: Path, spec: dict[str, Any]) -> str:
    return flowpilot_router_work_packets._material_packet_body_text_from_spec(sys.modules[__name__], project_root, spec)



def _write_material_scan_packets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_material_scan_packets(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_material_dispatch_block_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_material_dispatch_block_report(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_material_dispatch_recheck_protocol_blocker(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, event_name: str='router_protocol_blocker_material_scan_dispatch_recheck') -> None:
    return flowpilot_router_work_packets._write_material_dispatch_recheck_protocol_blocker(sys.modules[__name__], project_root, run_root, run_state, payload, event_name=event_name)



def _write_material_sufficiency_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, sufficient: bool) -> None:
    return flowpilot_router_work_packets._write_material_sufficiency_report(sys.modules[__name__], project_root, run_root, run_state, payload, sufficient=sufficient)



def _write_research_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_research_package(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_research_capability_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_research_capability_decision(sys.modules[__name__], project_root, run_root, run_state, payload)



def _pm_role_work_target_gate_contract(payload: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._pm_role_work_target_gate_contract(sys.modules[__name__], payload)



def _pm_role_work_gate_mapping_candidates(decision_payload: dict[str, Any], record: dict[str, Any]) -> str:
    return flowpilot_router_work_packets._pm_role_work_gate_mapping_candidates(sys.modules[__name__], decision_payload, record)



def _pm_role_work_gate_mapping_artifact_path(run_root: Path, gate_contract: dict[str, Any], mapped_event: str) -> Path:
    return flowpilot_router_work_packets._pm_role_work_gate_mapping_artifact_path(sys.modules[__name__], run_root, gate_contract, mapped_event)



def _pm_role_work_gate_mapping_alias_specs(run_root: Path, gate_contract: dict[str, Any], mapped_event: str) -> list[tuple[Path, str, str]]:
    return flowpilot_router_work_packets._pm_role_work_gate_mapping_alias_specs(sys.modules[__name__], run_root, gate_contract, mapped_event)



def _pm_role_work_gate_mappings_for_decision(decision_payload: dict[str, Any], records: list[dict[str, Any]], *, decision: str) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._pm_role_work_gate_mappings_for_decision(sys.modules[__name__], decision_payload, records, decision=decision)



def _apply_pm_role_work_gate_mappings(project_root: Path, run_root: Path, run_state: dict[str, Any], *, decision_path: Path, decision_record: dict[str, Any], mappings: list[dict[str, Any]]) -> None:
    return flowpilot_router_work_packets._apply_pm_role_work_gate_mappings(sys.modules[__name__], project_root, run_root, run_state, decision_path=decision_path, decision_record=decision_record, mappings=mappings)



def _pm_role_work_result_decision_payload_contract(*, name: str, required_fields: list[str], allowed_values: dict[str, list[Any]], records: list[dict[str, Any]], expected_request_id: str | None=None, expected_batch_id: str | None=None) -> dict[str, Any]:
    return flowpilot_router_work_packets._pm_role_work_result_decision_payload_contract(sys.modules[__name__], name=name, required_fields=required_fields, allowed_values=allowed_values, records=records, expected_request_id=expected_request_id, expected_batch_id=expected_batch_id)



def _write_pm_role_work_request(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_pm_role_work_request(sys.modules[__name__], project_root, run_root, run_state, payload)



def _normalize_pm_role_work_result_recipient(project_root: Path, result_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._normalize_pm_role_work_result_recipient(sys.modules[__name__], project_root, result_path, result)



def _validate_role_work_result_process_binding(project_root: Path, result_path: Path, *, record: dict[str, Any], packet_envelope: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_role_work_result_process_binding(sys.modules[__name__], project_root, result_path, record=record, packet_envelope=packet_envelope, result=result)



def _write_role_work_result_returned(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_role_work_result_returned(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_pm_role_work_result_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    return flowpilot_router_work_packets._write_pm_role_work_result_decision(sys.modules[__name__], project_root, run_root, run_state, payload)



def _validate_result_bodies_opened_by_pm(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    return flowpilot_router_work_packets._validate_result_bodies_opened_by_pm(sys.modules[__name__], project_root, run_state, records)



def _write_pm_package_result_disposition(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, batch_kind: str, package_label: str, gate_kind: str, output_path: Path) -> None:
    return flowpilot_router_work_packets._write_pm_package_result_disposition(sys.modules[__name__], project_root, run_root, run_state, payload, batch_kind=batch_kind, package_label=package_label, gate_kind=gate_kind, output_path=output_path)



def _write_worker_research_report(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_worker_research_report(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_material_understanding(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_material_understanding(sys.modules[__name__], project_root, run_root, run_state, payload)



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
    requirement_trace = payload.get("requirement_trace") if isinstance(payload.get("requirement_trace"), dict) else {}
    if not requirement_trace:
        source_registry = [
            {
                "source_requirement_id": str(item.get("source_requirement_id") or item.get("requirement_id") or item.get("acceptance_id") or f"req-{index:03d}"),
                "source_type": str(item.get("source") or "product_function_architecture"),
                "source_path": project_relative(project_root, material_understanding_path),
                "statement": str(item.get("goal") or item.get("behavior") or item.get("acceptance_statement") or item.get("acceptance_id") or f"Requirement {index}"),
                "status": "active",
                "superseded_by": [],
            }
            for index, item in enumerate(root_requirements, start=1)
            if isinstance(item, dict)
        ]
        requirement_trace = {
            "schema_version": "flowpilot.requirement_trace.v1",
            "pm_owned": True,
            "flowpilot_standalone": True,
            "external_tools_required": False,
            "full_protocol_required_when_flowpilot_invoked": True,
            "source_registry": source_registry,
            "legacy_inferred_from_functional_acceptance_matrix": True,
        }
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
        "requirement_trace": requirement_trace,
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


def _write_compatibility_alias_artifact(
    project_root: Path,
    source_path: Path,
    alias_path: Path,
    *,
    schema_version: str,
    alias_kind: str,
) -> None:
    artifact = read_json(source_path)
    artifact["schema_version"] = schema_version
    artifact["compatibility_alias_kind"] = alias_kind
    artifact["compatibility_alias_for"] = project_relative(project_root, source_path)
    artifact["compatibility_alias_recorded_at"] = utc_now()
    write_json(alias_path, artifact)


def _write_product_behavior_model_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    canonical_path = _product_behavior_model_report_path(run_root)
    _write_role_gate_report(
        project_root,
        run_root,
        run_state,
        payload,
        expected_role="product_flowguard_officer",
        path=canonical_path,
        schema_version="flowpilot.product_behavior_model.v1",
        checked_paths=[run_root / "product_function_architecture.json"],
    )
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _product_behavior_model_compatibility_report_path(run_root),
        schema_version="flowpilot.product_architecture_modelability.v1",
        alias_kind="product_architecture_modelability",
    )


def _write_pm_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    path: Path,
    schema_version: str,
    expected_decision: str,
    source_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("decided_by_role") != "project_manager":
        raise RouterError("PM model decision must include decided_by_role=project_manager")
    if payload.get("decision") != expected_decision:
        raise RouterError(f"PM model decision requires decision={expected_decision}")
    missing = [project_relative(project_root, item) for item in source_paths if not item.exists()]
    if missing:
        raise RouterError(f"PM model decision is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "decided_by_role": "project_manager",
            "decision": expected_decision,
            "source_paths": [project_relative(project_root, item) for item in source_paths],
            "pm_model_fit_review": payload.get("pm_model_fit_review"),
            "product_goal_coverage": payload.get("product_goal_coverage"),
            "unmodeled_or_ambiguous_behavior": payload.get("unmodeled_or_ambiguous_behavior") or [],
            "serial_execution_line_review": payload.get("serial_execution_line_review"),
            "recursive_node_entry_review": payload.get("recursive_node_entry_review"),
            "leaf_worker_readiness_review": payload.get("leaf_worker_readiness_review"),
            "parent_and_final_backward_review_policy": payload.get("parent_and_final_backward_review_policy"),
            "model_miss_repair_policy": payload.get("model_miss_repair_policy"),
            "next_action": payload.get("next_action"),
            "decided_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )


def _write_pm_product_behavior_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    accepted: bool,
) -> None:
    _write_pm_model_decision(
        project_root,
        run_root,
        run_state,
        payload,
        path=run_root / "flowguard" / "product_behavior_model_pm_decision.json",
        schema_version="flowpilot.product_behavior_model_pm_decision.v1",
        expected_decision="accept_product_behavior_model"
        if accepted
        else "request_product_behavior_model_rebuild",
        source_paths=[
            run_root / "product_function_architecture.json",
            _require_product_behavior_model_report(project_root, run_root),
        ],
    )
    if not accepted:
        for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS:
            run_state.setdefault("flags", {})[flag] = False


def _write_pm_process_route_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    accepted: bool,
) -> None:
    _write_pm_model_decision(
        project_root,
        run_root,
        run_state,
        payload,
        path=run_root / "flowguard" / "process_route_model_pm_decision.json",
        schema_version="flowpilot.process_route_model_pm_decision.v1",
        expected_decision="accept_process_route_model" if accepted else "request_process_route_model_rebuild",
        source_paths=[
            _current_route_draft_path(run_root),
            _require_process_route_model_report(project_root, run_root),
        ],
    )
    if not accepted:
        _reset_route_review_after_route_draft_repair(run_state)


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
        "serial_execution_model_checked",
        "all_effective_nodes_reachable_in_order",
        "recursive_child_routes_serialized",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("route process check requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _current_route_draft_path(run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process check is missing source paths: {', '.join(missing_paths)}")
    canonical_path = _process_route_model_report_path(run_root)
    write_json(
        canonical_path,
        {
            "schema_version": "flowpilot.process_route_model.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "process_flowguard_officer",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_can_reach_product_model": True,
            "repair_return_policy_checked": True,
            "serial_execution_model_checked": True,
            "all_effective_nodes_reachable_in_order": True,
            "recursive_child_routes_serialized": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _route_process_check_path(run_root),
        schema_version="flowpilot.route_process_check.v1",
        alias_kind="route_process_check",
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
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process issue report is missing source paths: {', '.join(missing_paths)}")
    canonical_path = _process_route_model_report_path(run_root)
    write_json(
        canonical_path,
        {
            "schema_version": "flowpilot.process_route_model.v1",
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
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _route_process_check_path(run_root),
        schema_version="flowpilot.route_process_check.v1",
        alias_kind="route_process_check",
    )
    for flag in (
        "route_draft_written_by_pm",
        "process_officer_route_check_card_delivered",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_check_passed",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False
    run_state["route_process_viability"] = {
        "verdict": expected_verdict,
        "report_path": project_relative(project_root, canonical_path),
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
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        _require_process_route_model_report(project_root, run_root),
        run_root / "flowguard" / "process_route_model_pm_decision.json",
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
    traced_requirements: list[dict[str, Any]] = []
    source_ids_by_requirement: dict[str, list[str]] = {}
    for item in root_requirements:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        requirement_id = str(traced.get("requirement_id") or f"root-{len(traced_requirements) + 1:03d}")
        traced["requirement_id"] = requirement_id
        source_ids = _string_list(traced.get("source_requirement_ids")) or [requirement_id]
        traced["source_requirement_ids"] = source_ids
        traced.setdefault("change_status", "ADDED")
        traced.setdefault("supersedes_requirement_ids", [])
        traced.setdefault("changed_reason", "Initial PM root-contract import from product-function architecture.")
        traced.setdefault("approval_owner_role", "project_manager")
        source_ids_by_requirement[requirement_id] = source_ids
        traced_requirements.append(traced)
    traced_proof_matrix: list[dict[str, Any]] = []
    for item in proof_matrix:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        requirement_id = str(traced.get("requirement_id") or "")
        traced.setdefault("source_requirement_ids", source_ids_by_requirement.get(requirement_id, [requirement_id] if requirement_id else []))
        traced_proof_matrix.append(traced)
    root_requirements = traced_requirements
    proof_matrix = traced_proof_matrix
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
        "requirement_traceability_policy": {
            "schema_version": "flowpilot.root_requirement_traceability.v1",
            "source": "product_function_architecture.requirement_trace",
            "stable_source_requirement_ids_required": True,
            "change_status_required": True,
            "external_spec_material_advisory_until_pm_imported": True,
            "completion_requires_final_trace_closure": True,
        },
        "root_requirements": root_requirements,
        "proof_matrix": proof_matrix,
        "standard_scenario_pack": {
            "required": True,
            "path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "selected_scenario_ids": scenario_ids,
            "covers_requirement_ids": _root_requirement_ids({"root_requirements": root_requirements}),
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
        "covers_requirement_ids": _root_requirement_ids({"root_requirements": root_requirements}),
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
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"cannot freeze root contract; missing paths: {', '.join(missing)}")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("completion_policy", {}).get("unresolved_residual_risks_allowed") is not False:
        raise RouterError("root contract cannot allow unresolved residual risks")
    _require_clean_self_interrogation(
        project_root,
        run_root,
        gate_name="root contract freeze",
        scopes=("startup", "product_architecture"),
    )
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
            "process_officer_passed": False,
            "process_officer_default_gate_removed": True,
            "product_officer_passed": False,
            "product_officer_default_gate_removed": True,
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


def _flatten_route_nodes(raw_nodes: list[Any], *, parent_node_id: str | None=None, depth: int=1) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._flatten_route_nodes(sys.modules[__name__], raw_nodes, parent_node_id=parent_node_id, depth=depth)



def _route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._route_nodes(sys.modules[__name__], route)



def _route_node_depth(node: dict[str, Any]) -> int:
    return flowpilot_router_route_frontier._route_node_depth(sys.modules[__name__], node)



def _route_display_depth(route: dict[str, Any]) -> int:
    return flowpilot_router_route_frontier._route_display_depth(sys.modules[__name__], route)



def _is_route_root_node(node: dict[str, Any]) -> bool:
    return flowpilot_router_route_frontier._is_route_root_node(sys.modules[__name__], node)



def _display_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._display_route_nodes(sys.modules[__name__], route)



def _route_active_path(route: dict[str, Any], active_node_id: str | None) -> list[dict[str, str]]:
    return flowpilot_router_route_frontier._route_active_path(sys.modules[__name__], route, active_node_id)



def _route_hidden_leaf_progress(route: dict[str, Any]) -> dict[str, int]:
    return flowpilot_router_route_frontier._route_hidden_leaf_progress(sys.modules[__name__], route)



def _is_leaf_readiness_passed(node: dict[str, Any], plan: dict[str, Any] | None=None) -> bool:
    return flowpilot_router_route_frontier._is_leaf_readiness_passed(sys.modules[__name__], node, plan)



def _node_kind(node: dict[str, Any]) -> str:
    return flowpilot_router_route_frontier._node_kind(sys.modules[__name__], node)



def _route_mutation_superseded_nodes(item: dict[str, Any]) -> list[str]:
    return flowpilot_router_route_frontier._route_mutation_superseded_nodes(sys.modules[__name__], item)



def _effective_route_nodes(route: dict[str, Any], mutations: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._effective_route_nodes(sys.modules[__name__], route, mutations)



def _effective_child_ids(node: dict[str, Any], nodes_by_id: dict[str, dict[str, Any]]) -> list[str]:
    return flowpilot_router_route_frontier._effective_child_ids(sys.modules[__name__], node, nodes_by_id)



def _ready_parent_scope_after_child_completion(nodes_by_id: dict[str, dict[str, Any]], completed: set[str], current_node_id: str) -> str | None:
    return flowpilot_router_route_frontier._ready_parent_scope_after_child_completion(sys.modules[__name__], nodes_by_id, completed, current_node_id)



def _next_effective_node_id(route: dict[str, Any], mutations: dict[str, Any], completed_nodes: list[str], current_node_id: str) -> str | None:
    return flowpilot_router_route_frontier._next_effective_node_id(sys.modules[__name__], route, mutations, completed_nodes, current_node_id)



def _route_memory_root(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_memory_root(sys.modules[__name__], run_root)



def _route_history_index_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_history_index_path(sys.modules[__name__], run_root)



def _pm_prior_path_context_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._pm_prior_path_context_path(sys.modules[__name__], run_root)



def _route_memory_ready(run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_route_frontier._route_memory_ready(sys.modules[__name__], run_root, run_state)



def _display_plan_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._display_plan_path(sys.modules[__name__], run_root)



def _route_state_snapshot_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_state_snapshot_path(sys.modules[__name__], run_root)



def _route_display_refresh_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_display_refresh_path(sys.modules[__name__], run_root)



def _optional_source_path(project_root: Path, path: Path) -> str | None:
    return flowpilot_router_route_frontier._optional_source_path(sys.modules[__name__], project_root, path)



def _plan_item_status(raw_status: Any, *, active: bool=False) -> str:
    return flowpilot_router_route_frontier._plan_item_status(sys.modules[__name__], raw_status, active=active)



def _frontier_completed_node_ids(run_root: Path) -> set[str]:
    return flowpilot_router_route_frontier._frontier_completed_node_ids(sys.modules[__name__], run_root)



def _route_item_status(run_root: Path, node_id: str, *, active_node_id: str | None, raw_status: Any=None) -> str:
    return flowpilot_router_route_frontier._route_item_status(sys.modules[__name__], run_root, node_id, active_node_id=active_node_id, raw_status=raw_status)



def _display_plan_projection(plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._display_plan_projection(sys.modules[__name__], plan)



def _waiting_for_pm_display_plan(run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._waiting_for_pm_display_plan(sys.modules[__name__], run_state)



def _current_display_plan(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._current_display_plan(sys.modules[__name__], project_root, run_root, run_state)



def _display_plan_sync_payload(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._display_plan_sync_payload(sys.modules[__name__], project_root, run_root, run_state)



def _active_ui_task_catalog(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._active_ui_task_catalog(sys.modules[__name__], project_root, run_root, run_state)



def _route_node_checklist(node: dict[str, Any], *, node_complete: bool=False) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._route_node_checklist(sys.modules[__name__], node, node_complete=node_complete)



def _active_route_payload(run_root: Path, route_id: str | None=None) -> dict[str, Any] | None:
    return flowpilot_router_route_frontier._active_route_payload(sys.modules[__name__], run_root, route_id)



def _current_status_summary_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._current_status_summary_path(sys.modules[__name__], run_root)



def _run_elapsed_seconds(run_root: Path, run_state: dict[str, Any]) -> int | None:
    return flowpilot_router_route_frontier._run_elapsed_seconds(sys.modules[__name__], run_root, run_state)



def _route_progress_parent_map(nodes: list[dict[str, Any]]) -> dict[str, str]:
    return flowpilot_router_route_frontier._route_progress_parent_map(sys.modules[__name__], nodes)



def _route_progress_completed_ids(nodes: list[dict[str, Any]], frontier: dict[str, Any]) -> set[str]:
    return flowpilot_router_route_frontier._route_progress_completed_ids(sys.modules[__name__], nodes, frontier)



def _route_progress_path_nodes(nodes_by_id: dict[str, dict[str, Any]], parent_by_id: dict[str, str], active_node_id: str) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._route_progress_path_nodes(sys.modules[__name__], nodes_by_id, parent_by_id, active_node_id)



def _build_progress_summary(run_root: Path, run_state: dict[str, Any], *, route: dict[str, Any], frontier: dict[str, Any], active_node_id: str, state_kind: str) -> dict[str, Any]:
    return flowpilot_router_route_frontier._build_progress_summary(sys.modules[__name__], run_root, run_state, route=route, frontier=frontier, active_node_id=active_node_id, state_kind=state_kind)



def _route_node_label(route: dict[str, Any], node_id: str) -> str:
    return flowpilot_router_route_frontier._route_node_label(sys.modules[__name__], route, node_id)



def _status_summary_waiting_for(pending_action: dict[str, Any]) -> str | None:
    return flowpilot_router_route_frontier._status_summary_waiting_for(sys.modules[__name__], pending_action)



def _current_status_active_batch_summary(run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_route_frontier._current_status_active_batch_summary(sys.modules[__name__], run_root)



def _build_current_status_summary(run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_route_frontier._build_current_status_summary(sys.modules[__name__], run_root, run_state, route_payload=route_payload)



def _write_current_status_summary(run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None) -> None:
    return flowpilot_router_route_frontier._write_current_status_summary(sys.modules[__name__], run_root, run_state, route_payload=route_payload)



def _build_route_state_snapshot(project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None, source_event: str | None=None) -> dict[str, Any]:
    return flowpilot_router_route_frontier._build_route_state_snapshot(sys.modules[__name__], project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)



def _write_route_state_snapshot(project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None, source_event: str | None=None) -> None:
    return flowpilot_router_route_frontier._write_route_state_snapshot(sys.modules[__name__], project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)



def _mark_display_plan_dirty(run_state: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._mark_display_plan_dirty(sys.modules[__name__], run_state)



def _write_display_plan_from_route(project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_id: str, route_version: int, route_payload: dict[str, Any], active_node_id: str | None, source_event: str) -> None:
    return flowpilot_router_route_frontier._write_display_plan_from_route(sys.modules[__name__], project_root, run_root, run_state, route_id=route_id, route_version=route_version, route_payload=route_payload, active_node_id=active_node_id, source_event=source_event)



def _update_display_plan_current_node(project_root: Path, run_root: Path, run_state: dict[str, Any], *, node_id: str, node_title: str, checklist: list[dict[str, Any]], source_event: str) -> None:
    return flowpilot_router_route_frontier._update_display_plan_current_node(sys.modules[__name__], project_root, run_root, run_state, node_id=node_id, node_title=node_title, checklist=checklist, source_event=source_event)



PRE_ROUTE_PHASE_ITEMS = (
    ("material_understanding", "Material understanding", "pm_material_understanding_card_delivered"),
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


def _latest_pre_route_phase(run_state: dict[str, Any]) -> str | None:
    return flowpilot_router_route_frontier._latest_pre_route_phase(sys.modules[__name__], run_state)



def _sync_execution_frontier_phase(run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._sync_execution_frontier_phase(sys.modules[__name__], run_root, run_state)



def _write_pre_route_phase_display_plan_if_needed(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_route_frontier._write_pre_route_phase_display_plan_if_needed(sys.modules[__name__], project_root, run_root, run_state)



def _reconcile_non_current_running_index_entries(project_root: Path, run_state: dict[str, Any]) -> int:
    return flowpilot_router_route_frontier._reconcile_non_current_running_index_entries(sys.modules[__name__], project_root, run_state)



def _sync_derived_run_views(project_root: Path, run_root: Path, run_state: dict[str, Any], *, reason: str, update_display: bool=True) -> None:
    return flowpilot_router_route_frontier._sync_derived_run_views(sys.modules[__name__], project_root, run_root, run_state, reason=reason, update_display=update_display)



def _write_display_plan_from_pm_payload(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, source_event: str) -> None:
    return flowpilot_router_route_frontier._write_display_plan_from_pm_payload(sys.modules[__name__], project_root, run_root, run_state, payload, source_event=source_event)



def _event_markers(run_state: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._event_markers(sys.modules[__name__], run_state, names)



def _route_node_history(project_root: Path, run_root: Path, route_id: str, route: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._route_node_history(sys.modules[__name__], project_root, run_root, route_id, route)



def _refresh_route_memory(project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger: str) -> None:
    return flowpilot_router_route_frontier._refresh_route_memory(sys.modules[__name__], project_root, run_root, run_state, trigger=trigger)



def _require_pm_prior_path_context(project_root: Path, run_root: Path, payload: dict[str, Any], *, purpose: str) -> dict[str, Any]:
    return flowpilot_router_route_frontier._require_pm_prior_path_context(sys.modules[__name__], project_root, run_root, payload, purpose=purpose)



def _pm_context_action_extra(project_root: Path, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._pm_context_action_extra(sys.modules[__name__], project_root, run_root, entry)



def _card_required_source_paths(project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    return flowpilot_router_route_frontier._card_required_source_paths(sys.modules[__name__], project_root, run_root, card_id)



def _card_delivery_phase(card_id: str, card: dict[str, Any], frontier: dict[str, Any], run_state: dict[str, Any]) -> tuple[str, str | None]:
    return flowpilot_router_route_frontier._card_delivery_phase(sys.modules[__name__], card_id, card, frontier, run_state)



def _live_card_delivery_context(project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._live_card_delivery_context(sys.modules[__name__], project_root, run_root, run_state, entry, card)



def _matching_controller_delivery_actions(project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._matching_controller_delivery_actions(sys.modules[__name__], project_root, run_root, record, bundle=bundle)



def _controller_delivery_fact_for_pending_return(project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool, committed_extra: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_route_frontier._controller_delivery_fact_for_pending_return(sys.modules[__name__], project_root, run_root, record, bundle=bundle, committed_extra=committed_extra)



def _write_route_draft(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._write_route_draft(sys.modules[__name__], project_root, run_root, run_state, payload)



def _reset_route_review_after_route_draft_repair(run_state: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._reset_route_review_after_route_draft_repair(sys.modules[__name__], run_state)



def _reset_route_hard_gate_approvals_for_recheck(run_state: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._reset_route_hard_gate_approvals_for_recheck(sys.modules[__name__], run_state)



def _product_behavior_model_report_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._product_behavior_model_report_path(sys.modules[__name__], run_root)



def _product_behavior_model_compatibility_report_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._product_behavior_model_compatibility_report_path(sys.modules[__name__], run_root)



def _require_product_behavior_model_report(project_root: Path, run_root: Path) -> Path:
    return flowpilot_router_route_frontier._require_product_behavior_model_report(sys.modules[__name__], project_root, run_root)



def _route_process_check_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_process_check_path(sys.modules[__name__], run_root)



def _process_route_model_report_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._process_route_model_report_path(sys.modules[__name__], run_root)



def _require_process_route_model_report(project_root: Path, run_root: Path) -> Path:
    return flowpilot_router_route_frontier._require_process_route_model_report(sys.modules[__name__], project_root, run_root)



def _route_product_check_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._route_product_check_path(sys.modules[__name__], run_root)



def _require_route_process_pass(project_root: Path, run_root: Path) -> Path:
    return flowpilot_router_route_frontier._require_route_process_pass(sys.modules[__name__], project_root, run_root)



def _supersede_active_current_node_packet_for_route_mutation(project_root: Path, run_root: Path, *, frontier: dict[str, Any], mutation_record: dict[str, Any]) -> None:
    return flowpilot_router_route_frontier._supersede_active_current_node_packet_for_route_mutation(sys.modules[__name__], project_root, run_root, frontier=frontier, mutation_record=mutation_record)



def _require_route_product_pass(project_root: Path, run_root: Path) -> Path:
    return flowpilot_router_route_frontier._require_route_product_pass(sys.modules[__name__], project_root, run_root)



def _current_route_draft_path(run_root: Path) -> Path:
    return flowpilot_router_route_frontier._current_route_draft_path(sys.modules[__name__], run_root)



def _latest_event_payload(run_state: dict[str, Any], event_name: str) -> dict[str, Any]:
    return flowpilot_router_route_frontier._latest_event_payload(sys.modules[__name__], run_state, event_name)



def _packet_paths(project_root: Path, run_state: dict[str, Any], packet_id: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._packet_paths(sys.modules[__name__], project_root, run_state, packet_id)



def _active_current_node_packet_records(project_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._active_current_node_packet_records(sys.modules[__name__], project_root, run_state)



def _current_node_batch_packet_record(project_root: Path, run_state: dict[str, Any], *, preferred_packet_id: str | None=None) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._current_node_batch_packet_record(sys.modules[__name__], project_root, run_state, preferred_packet_id=preferred_packet_id)



def _packet_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    return flowpilot_router_work_packets._packet_envelope_path(sys.modules[__name__], project_root, run_state, payload)



def _result_envelope_path(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    return flowpilot_router_work_packets._result_envelope_path(sys.modules[__name__], project_root, run_state, payload)



def _current_node_packet_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_work_packets._current_node_packet_context(sys.modules[__name__], project_root, run_state)



def _current_node_packet_records(project_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._current_node_packet_records(sys.modules[__name__], project_root, run_state)



def _current_node_results_complete(project_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._current_node_results_complete(sys.modules[__name__], project_root, run_state)



def _current_node_missing_result_roles(project_root: Path, run_state: dict[str, Any]) -> list[str]:
    return flowpilot_router_work_packets._current_node_missing_result_roles(sys.modules[__name__], project_root, run_state)



def _active_child_skill_bindings_from_plan(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._active_child_skill_bindings_from_plan(sys.modules[__name__], plan)



def _active_child_skill_source_paths(bindings: list[dict[str, Any]]) -> list[str]:
    return flowpilot_router_work_packets._active_child_skill_source_paths(sys.modules[__name__], bindings)



def _metadata_string_list(metadata: dict[str, Any], *keys: str) -> list[str]:
    return flowpilot_router_work_packets._metadata_string_list(sys.modules[__name__], metadata, *keys)



def _metadata_binding_ids(metadata: dict[str, Any], *keys: str) -> list[str]:
    return flowpilot_router_work_packets._metadata_binding_ids(sys.modules[__name__], metadata, *keys)



def _current_node_result_context(project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_work_packets._current_node_result_context(sys.modules[__name__], project_root, run_state)



def _packet_envelope_path_from_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    return flowpilot_router_work_packets._packet_envelope_path_from_record(sys.modules[__name__], project_root, run_state, record)



def _result_envelope_path_from_packet_record(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    return flowpilot_router_work_packets._result_envelope_path_from_packet_record(sys.modules[__name__], project_root, run_state, record)



def _load_packet_index(path: Path, *, label: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._load_packet_index(sys.modules[__name__], path, label=label)



def _ensure_barrier_bundles_ready(project_root: Path, *, node_id: str | None=None) -> None:
    return flowpilot_router_work_packets._ensure_barrier_bundles_ready(sys.modules[__name__], project_root, node_id=node_id)



def _material_scan_index_path(run_root: Path) -> Path:
    return flowpilot_router_work_packets._material_scan_index_path(sys.modules[__name__], run_root)



def _research_packet_index_path(run_root: Path) -> Path:
    return flowpilot_router_work_packets._research_packet_index_path(sys.modules[__name__], run_root)



def _parallel_packet_batch_root(run_root: Path) -> Path:
    return flowpilot_router_work_packets._parallel_packet_batch_root(sys.modules[__name__], run_root)



def _parallel_packet_batch_path(run_root: Path, batch_id: str) -> Path:
    return flowpilot_router_work_packets._parallel_packet_batch_path(sys.modules[__name__], run_root, batch_id)



def _parallel_packet_batch_ref_path(run_root: Path, batch_kind: str) -> Path:
    return flowpilot_router_work_packets._parallel_packet_batch_ref_path(sys.modules[__name__], run_root, batch_kind)



def _packet_record_from_envelope(project_root: Path, run_state: dict[str, Any], *, envelope: dict[str, Any], packet_type: str | None=None, request_id: str | None=None) -> dict[str, Any]:
    return flowpilot_router_work_packets._packet_record_from_envelope(sys.modules[__name__], project_root, run_state, envelope=envelope, packet_type=packet_type, request_id=request_id)



def _write_parallel_packet_batch(project_root: Path, run_root: Path, run_state: dict[str, Any], *, batch_id: str, batch_kind: str, phase: str, records: list[dict[str, Any]], node_id: str | None=None, join_policy: str='all_results_before_review', review_policy: str='batch_review_before_pm', pm_absorption_required: bool=True, parent_batch_id: str | None=None) -> dict[str, Any]:
    return flowpilot_router_work_packets._write_parallel_packet_batch(sys.modules[__name__], project_root, run_root, run_state, batch_id=batch_id, batch_kind=batch_kind, phase=phase, records=records, node_id=node_id, join_policy=join_policy, review_policy=review_policy, pm_absorption_required=pm_absorption_required, parent_batch_id=parent_batch_id)



def _load_parallel_packet_batch(run_root: Path, batch_id: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._load_parallel_packet_batch(sys.modules[__name__], run_root, batch_id)



def _active_parallel_packet_batch(run_root: Path, batch_kind: str) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._active_parallel_packet_batch(sys.modules[__name__], run_root, batch_kind)



def _write_parallel_packet_batch_state(run_root: Path, batch: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_parallel_packet_batch_state(sys.modules[__name__], run_root, batch)



def _parallel_batch_record_result_exists(project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> tuple[bool, Path]:
    return flowpilot_router_work_packets._parallel_batch_record_result_exists(sys.modules[__name__], project_root, run_state, record)



def _parallel_packet_batch_member_summary(project_root: Path, run_state: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._parallel_packet_batch_member_summary(sys.modules[__name__], project_root, run_state, batch)



def _refresh_parallel_packet_batch_from_durable_results(project_root: Path, run_root: Path, run_state: dict[str, Any], batch_kind: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._refresh_parallel_packet_batch_from_durable_results(sys.modules[__name__], project_root, run_root, run_state, batch_kind)



def _refresh_all_parallel_packet_batches_from_durable_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._refresh_all_parallel_packet_batches_from_durable_results(sys.modules[__name__], project_root, run_root, run_state)



def _mark_parallel_batch_packets_relayed(run_root: Path, batch_kind: str) -> None:
    return flowpilot_router_work_packets._mark_parallel_batch_packets_relayed(sys.modules[__name__], run_root, batch_kind)



def _mark_parallel_batch_results_joined(project_root: Path, run_root: Path, run_state: dict[str, Any], batch_kind: str) -> None:
    return flowpilot_router_work_packets._mark_parallel_batch_results_joined(sys.modules[__name__], project_root, run_root, run_state, batch_kind)



def _mark_parallel_batch_reviewed(run_root: Path, batch_kind: str, *, passed: bool, reviewed_packet_ids: list[str]) -> None:
    return flowpilot_router_work_packets._mark_parallel_batch_reviewed(sys.modules[__name__], run_root, batch_kind, passed=passed, reviewed_packet_ids=reviewed_packet_ids)



def _pm_role_work_request_index_path(run_root: Path) -> Path:
    return flowpilot_router_work_packets._pm_role_work_request_index_path(sys.modules[__name__], run_root)



def _empty_pm_role_work_request_index(run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._empty_pm_role_work_request_index(sys.modules[__name__], run_state)



def _load_pm_role_work_request_index(run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._load_pm_role_work_request_index(sys.modules[__name__], run_root, run_state)



def _write_pm_role_work_request_index(run_root: Path, index: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_pm_role_work_request_index(sys.modules[__name__], run_root, index)



def _officer_request_lifecycle_index_path(run_root: Path) -> Path:
    return flowpilot_router_work_packets._officer_request_lifecycle_index_path(sys.modules[__name__], run_root)



def _empty_officer_request_lifecycle_index(run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._empty_officer_request_lifecycle_index(sys.modules[__name__], run_state)



def _load_officer_request_lifecycle_index(run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._load_officer_request_lifecycle_index(sys.modules[__name__], run_root, run_state)



def _officer_lifecycle_entry(index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._officer_lifecycle_entry(sys.modules[__name__], index, request_id)



def _upsert_officer_lifecycle_entry(index: dict[str, Any], entry: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._upsert_officer_lifecycle_entry(sys.modules[__name__], index, entry)



def _write_officer_request_lifecycle_index(project_root: Path, run_root: Path, run_state: dict[str, Any], index: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_officer_request_lifecycle_index(sys.modules[__name__], project_root, run_root, run_state, index)



def _record_officer_lifecycle_request(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._record_officer_lifecycle_request(sys.modules[__name__], project_root, run_root, run_state, record)



def _record_officer_lifecycle_status(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], *, lifecycle_status: str) -> None:
    return flowpilot_router_work_packets._record_officer_lifecycle_status(sys.modules[__name__], project_root, run_root, run_state, record, lifecycle_status=lifecycle_status)



def _record_officer_lifecycle_result_returned(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], result: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._record_officer_lifecycle_result_returned(sys.modules[__name__], project_root, run_root, run_state, record, result)



def _record_officer_lifecycle_pm_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], decision_record: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._record_officer_lifecycle_pm_decision(sys.modules[__name__], project_root, run_root, run_state, record, decision_record)



def _pm_role_work_request_record(index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._pm_role_work_request_record(sys.modules[__name__], index, request_id)



def _active_pm_role_work_request(index: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._active_pm_role_work_request(sys.modules[__name__], index)



def _active_pm_role_work_batch_records(index: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._active_pm_role_work_batch_records(sys.modules[__name__], index)



def _unresolved_pm_role_work_requests(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._unresolved_pm_role_work_requests(sys.modules[__name__], run_root, run_state)



def _safe_packet_id_component(value: str) -> str:
    return flowpilot_router_work_packets._safe_packet_id_component(sys.modules[__name__], value)



def _pm_role_work_request_body_text(project_root: Path, payload: dict[str, Any]) -> tuple[str, dict[str, str]]:
    return flowpilot_router_work_packets._pm_role_work_request_body_text(sys.modules[__name__], project_root, payload)



def _validate_pm_role_work_process_contract_binding(*, contract_id: str, to_role: str, request_kind: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_pm_role_work_process_contract_binding(sys.modules[__name__], contract_id=contract_id, to_role=to_role, request_kind=request_kind)



def _pm_role_work_packet_type_from_contract(run_root: Path, *, contract_id: str, to_role: str, request_kind: str) -> str:
    return flowpilot_router_work_packets._pm_role_work_packet_type_from_contract(sys.modules[__name__], run_root, contract_id=contract_id, to_role=to_role, request_kind=request_kind)



def _pm_role_work_output_contract(run_root: Path, *, contract_id: str, to_role: str, packet_type: str, node_id: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._pm_role_work_output_contract(sys.modules[__name__], run_root, contract_id=contract_id, to_role=to_role, packet_type=packet_type, node_id=node_id)



CONTROL_TRANSACTION_EVENT_USAGES = {
    "recorded_event",
    "wait",
    "rerun_target",
    "repair_outcome",
    "reconcile",
}
CONTROL_TRANSACTION_COMMIT_TARGETS = {
    "frontier",
    "run_state",
    "status_summary",
    "packet_ledger",
    "blocker_index",
    "repair_transaction",
    "repair_transaction_index",
    "route",
    "stale_evidence",
    "dispatch_index",
}
CONTROL_TRANSACTION_OUTCOME_POLICIES = {
    "single_event",
    "three_distinct_outcomes",
    "quarantine_invalid",
}
CONTROL_TRANSACTION_LEGACY_POLICIES = {
    "block_if_invalid",
    "quarantine_invalid",
}
CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES = {
    True,
    False,
    "when_reviewing_packet_result",
    "when_repair_rechecks_packet_result",
    "audit_existing_only",
}
CONTROL_TRANSACTION_REPAIR_POLICIES = {
    True,
    False,
    "when_mutation_resolves_control_blocker",
    "audit_existing_only",
}


def _control_transaction_registry_path(run_root: Path | None = None) -> Path:
    if run_root is not None:
        candidate = run_root / "runtime_kit" / "control_transaction_registry.json"
        if candidate.exists():
            return candidate
    return runtime_kit_source() / "control_transaction_registry.json"


def _control_transaction_contract_registry_path(run_root: Path | None = None) -> Path:
    if run_root is not None:
        candidate = run_root / "runtime_kit" / "contracts" / "contract_index.json"
        if candidate.exists():
            return candidate
    return runtime_kit_source() / "contracts" / "contract_index.json"


def _load_control_transaction_registry(run_root: Path | None = None) -> dict[str, Any]:
    return read_json(_control_transaction_registry_path(run_root))


def _registered_output_contract_ids(run_root: Path | None = None) -> set[str]:
    registry = read_json(_control_transaction_contract_registry_path(run_root))
    return {
        str(item.get("contract_id"))
        for item in registry.get("contracts", [])
        if isinstance(item, dict) and item.get("contract_id")
    }


def _control_transaction_registry_rows(run_root: Path | None = None) -> list[dict[str, Any]]:
    registry = _load_control_transaction_registry(run_root)
    rows = registry.get("transaction_types")
    if not isinstance(rows, list):
        raise RouterError("control transaction registry requires transaction_types list")
    return [row for row in rows if isinstance(row, dict)]


def _control_transaction_registry_issues(run_root: Path | None = None) -> list[str]:
    issues: list[str] = []
    try:
        registry = _load_control_transaction_registry(run_root)
    except Exception as exc:
        return [f"control transaction registry cannot be loaded: {exc}"]

    if registry.get("schema_version") != CONTROL_TRANSACTION_REGISTRY_SCHEMA:
        issues.append("control transaction registry schema_version mismatch")
    if registry.get("authority") != "router":
        issues.append("control transaction registry authority must be router")
    if registry.get("controller_may_invent_transactions") is not False:
        issues.append("control transaction registry must forbid controller-invented transactions")

    raw_rows = registry.get("transaction_types")
    if not isinstance(raw_rows, list) or not raw_rows:
        issues.append("control transaction registry requires non-empty transaction_types list")
        return issues

    try:
        contract_ids = _registered_output_contract_ids(run_root)
    except Exception as exc:
        contract_ids = set()
        issues.append(f"control transaction registry cannot load contract index: {exc}")

    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            issues.append(f"transaction_types[{index}] must be an object")
            continue
        transaction_type = str(row.get("transaction_type") or "").strip()
        context = transaction_type or f"transaction_types[{index}]"
        if not transaction_type:
            issues.append(f"{context}: transaction_type is required")
        elif transaction_type in seen:
            issues.append(f"{context}: duplicate transaction_type")
        seen.add(transaction_type)

        for field in ("producer_roles", "output_contract_ids", "router_events", "event_usages", "commit_targets"):
            if not isinstance(row.get(field), list):
                issues.append(f"{context}: {field} must be a list")

        producer_roles = row.get("producer_roles") if isinstance(row.get("producer_roles"), list) else []
        if transaction_type != "legacy_reconcile" and not [role for role in producer_roles if str(role).strip()]:
            issues.append(f"{context}: producer_roles must be non-empty")

        output_contract_ids = row.get("output_contract_ids") if isinstance(row.get("output_contract_ids"), list) else []
        for contract_id in output_contract_ids:
            if str(contract_id) not in contract_ids:
                issues.append(f"{context}: output_contract_id is not registered: {contract_id}")

        router_events = row.get("router_events") if isinstance(row.get("router_events"), list) else []
        for event in router_events:
            if str(event) not in EXTERNAL_EVENTS:
                issues.append(f"{context}: router_event is not registered: {event}")

        event_usages = row.get("event_usages") if isinstance(row.get("event_usages"), list) else []
        for usage in event_usages:
            if str(usage) not in CONTROL_TRANSACTION_EVENT_USAGES:
                issues.append(f"{context}: unsupported event_usage: {usage}")

        commit_targets = row.get("commit_targets") if isinstance(row.get("commit_targets"), list) else []
        if not commit_targets:
            issues.append(f"{context}: commit_targets must be non-empty")
        for target in commit_targets:
            if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                issues.append(f"{context}: unsupported commit_target: {target}")
        optional_targets = row.get("optional_commit_targets", [])
        if optional_targets is None:
            optional_targets = []
        if not isinstance(optional_targets, list):
            issues.append(f"{context}: optional_commit_targets must be a list when present")
        else:
            for target in optional_targets:
                if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                    issues.append(f"{context}: unsupported optional_commit_target: {target}")

        if row.get("packet_authority_required") not in CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES:
            issues.append(f"{context}: unsupported packet_authority_required policy")
        if row.get("repair_transaction_required") not in CONTROL_TRANSACTION_REPAIR_POLICIES:
            issues.append(f"{context}: unsupported repair_transaction_required policy")
        if row.get("outcome_policy") not in CONTROL_TRANSACTION_OUTCOME_POLICIES:
            issues.append(f"{context}: unsupported outcome_policy")
        if row.get("legacy_policy") not in CONTROL_TRANSACTION_LEGACY_POLICIES:
            issues.append(f"{context}: unsupported legacy_policy")

    return issues


def _validate_control_transaction_registry(run_root: Path | None = None) -> None:
    issues = _control_transaction_registry_issues(run_root)
    if issues:
        raise RouterError("control transaction registry invalid: " + "; ".join(issues))


def _control_transaction_row(run_root: Path | None, transaction_type: str) -> dict[str, Any]:
    _validate_control_transaction_registry(run_root)
    for row in _control_transaction_registry_rows(run_root):
        if row.get("transaction_type") == transaction_type:
            return row
    raise RouterError(f"control transaction type is not registered: {transaction_type}")


def _validate_control_transaction_requirements(
    run_root: Path | None,
    *,
    transaction_type: str,
    producer_role: str,
    output_contract_id: str | None = None,
    router_events: tuple[str, ...] = (),
    required_event_usages: tuple[str, ...] = (),
    required_commit_targets: tuple[str, ...] = (),
    require_packet_authority: bool | None = None,
    require_repair_transaction: bool | None = None,
    outcome_policy: str | None = None,
) -> dict[str, Any]:
    row = _control_transaction_row(run_root, transaction_type)
    issues: list[str] = []
    producer_roles = {str(role) for role in row.get("producer_roles", [])}
    if producer_role not in producer_roles:
        issues.append(f"producer role {producer_role} is not allowed")
    if output_contract_id:
        contract_ids = {str(contract_id) for contract_id in row.get("output_contract_ids", [])}
        if output_contract_id not in contract_ids:
            issues.append(f"output contract {output_contract_id} is not allowed")
    declared_events = {str(event) for event in row.get("router_events", [])}
    for event in router_events:
        if event not in declared_events:
            issues.append(f"router event {event} is not declared")
    declared_usages = {str(usage) for usage in row.get("event_usages", [])}
    for usage in required_event_usages:
        if usage not in declared_usages:
            issues.append(f"event usage {usage} is not declared")
    declared_targets = {str(target) for target in row.get("commit_targets", [])}
    for target in required_commit_targets:
        if target not in declared_targets:
            issues.append(f"commit target {target} is not declared")
    if require_packet_authority is True and row.get("packet_authority_required") is not True:
        issues.append("packet authority is required but not declared as unconditional")
    if require_packet_authority is False and row.get("packet_authority_required") not in {False}:
        issues.append("packet authority is declared but this transaction expected none")
    if require_repair_transaction is True and row.get("repair_transaction_required") is not True:
        issues.append("repair transaction is required but not declared as unconditional")
    if require_repair_transaction is False and row.get("repair_transaction_required") not in {False}:
        issues.append("repair transaction is declared but this transaction expected none")
    if outcome_policy and row.get("outcome_policy") != outcome_policy:
        issues.append(f"outcome policy must be {outcome_policy}")
    if issues:
        raise RouterError(
            f"control transaction registry does not authorize {transaction_type}: "
            + "; ".join(issues)
        )
    return {
        "schema_version": CONTROL_TRANSACTION_REGISTRY_SCHEMA,
        "transaction_type": transaction_type,
        "producer_role": producer_role,
        "output_contract_id": output_contract_id,
        "router_events": list(router_events),
        "event_usages": list(required_event_usages),
        "commit_targets": list(required_commit_targets),
        "packet_authority_required": row.get("packet_authority_required"),
        "repair_transaction_required": row.get("repair_transaction_required"),
        "outcome_policy": row.get("outcome_policy"),
        "legacy_policy": row.get("legacy_policy"),
        "registry_path": "runtime_kit/control_transaction_registry.json",
    }


ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS = (
    "router_must_compute_before_pm_decision",
    "router_must_validate_before_event_acceptance",
    "router_must_validate_before_commit",
    "pm_may_choose_only_from_legal_next_actions",
)


ROUTE_ACTION_POLICY_EVENT_TO_ACTION = {
    "pm_builds_parent_backward_targets": "build_parent_backward_targets",
    "reviewer_passes_parent_backward_replay": "review_parent_backward_replay",
    "reviewer_blocks_parent_backward_replay": "review_parent_backward_replay",
    "pm_records_parent_segment_decision": "record_parent_segment_decision",
    "pm_completes_parent_node_from_backward_replay": "complete_parent_node",
    "pm_mutates_route_after_review_block": "mutate_route",
    "pm_approves_terminal_closure": "terminal_closure",
}


ROUTE_ACTION_POLICY_CARD_TO_ACTION = {
    "pm.parent_backward_targets": "build_parent_backward_targets",
    "reviewer.parent_backward_replay": "review_parent_backward_replay",
    "pm.parent_segment_decision": "record_parent_segment_decision",
    "pm.closure": "terminal_closure",
}


ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS = {
    "build_parent_backward_targets",
    "review_parent_backward_replay",
    "record_parent_segment_decision",
    "complete_parent_node",
}


ROUTE_ACTION_POLICY_ROUTE_MOVEMENT_ACTIONS = set(ROUTE_ACTION_POLICY_EVENT_TO_ACTION.values())


def _route_action_policy_registry_path(run_root: Path | None=None) -> Path:
    return flowpilot_router_route_frontier._route_action_policy_registry_path(sys.modules[__name__], run_root)



def _load_route_action_policy_registry(run_root: Path | None=None) -> dict[str, Any]:
    return flowpilot_router_route_frontier._load_route_action_policy_registry(sys.modules[__name__], run_root)



def _route_action_policy_rows(run_root: Path | None=None) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._route_action_policy_rows(sys.modules[__name__], run_root)



def _route_action_policy_issues(run_root: Path | None=None) -> list[str]:
    return flowpilot_router_route_frontier._route_action_policy_issues(sys.modules[__name__], run_root)



def _validate_route_action_policy_registry(run_root: Path | None=None) -> None:
    return flowpilot_router_route_frontier._validate_route_action_policy_registry(sys.modules[__name__], run_root)



def _route_action_policy_by_id(run_root: Path | None=None) -> dict[str, dict[str, Any]]:
    return flowpilot_router_route_frontier._route_action_policy_by_id(sys.modules[__name__], run_root)



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
    return flowpilot_router_events_repair._repair_transactions_root(sys.modules[__name__], run_root)



def _repair_transaction_index_path(run_root: Path) -> Path:
    return flowpilot_router_events_repair._repair_transaction_index_path(sys.modules[__name__], run_root)



def _repair_transaction_path(run_root: Path, transaction_id: str) -> Path:
    return flowpilot_router_events_repair._repair_transaction_path(sys.modules[__name__], run_root, transaction_id)



def _repair_transaction_id(blocker_id: str) -> str:
    return flowpilot_router_events_repair._repair_transaction_id(sys.modules[__name__], blocker_id)



def _control_blocker_repair_origin(active: dict[str, Any], *, rerun_target: str, requested_plan_kind: str, run_root: Path, run_state: dict[str, Any]) -> str:
    return flowpilot_router_events_repair._control_blocker_repair_origin(sys.modules[__name__], active, rerun_target=rerun_target, requested_plan_kind=requested_plan_kind, run_root=run_root, run_state=run_state)



def _repair_outcome_table(rerun_target: str, *, repair_origin: str='none') -> dict[str, dict[str, Any]]:
    return flowpilot_router_events_repair._repair_outcome_table(sys.modules[__name__], rerun_target, repair_origin=repair_origin)



def _validate_repair_outcome_table(outcome_table: dict[str, Any], *, context: str, run_root: Path, run_state: dict[str, Any], repair_origin: str) -> None:
    return flowpilot_router_events_repair._validate_repair_outcome_table(sys.modules[__name__], outcome_table, context=context, run_root=run_root, run_state=run_state, repair_origin=repair_origin)



def _repair_outcome_events(outcome_table: dict[str, Any]) -> list[str]:
    return flowpilot_router_events_repair._repair_outcome_events(sys.modules[__name__], outcome_table)



def _repair_packet_specs_from_decision(project_root: Path, run_root: Path, decision: dict[str, Any], *, rerun_target: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    return flowpilot_router_events_repair._repair_packet_specs_from_decision(sys.modules[__name__], project_root, run_root, decision, rerun_target=rerun_target)



def _write_repair_transaction_index(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_events_repair._write_repair_transaction_index(sys.modules[__name__], project_root, run_root, run_state)



def _commit_material_scan_repair_generation(project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction_id: str, packet_generation_id: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    return flowpilot_router_events_repair._commit_material_scan_repair_generation(sys.modules[__name__], project_root, run_root, run_state, transaction_id=transaction_id, packet_generation_id=packet_generation_id, packet_specs=packet_specs)



def _active_repair_transaction_for_event(run_root: Path, event: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    return flowpilot_router_events_repair._active_repair_transaction_for_event(sys.modules[__name__], run_root, event)



def _repair_transaction_outcome_kind(transaction: dict[str, Any], event: str) -> str | None:
    return flowpilot_router_events_repair._repair_transaction_outcome_kind(sys.modules[__name__], transaction, event)



def _clear_successful_repair_lane_state(run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    return flowpilot_router_events_repair._clear_successful_repair_lane_state(sys.modules[__name__], run_state, transaction, event=event)



def _finalize_repair_transaction_outcome(project_root: Path, run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    return flowpilot_router_events_repair._finalize_repair_transaction_outcome(sys.modules[__name__], project_root, run_root, run_state, event=event, payload=payload)



def _relay_packet_records(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, controller_agent_id: str) -> list[str]:
    return flowpilot_router_work_packets._relay_packet_records(sys.modules[__name__], project_root, run_state, records, controller_agent_id=controller_agent_id)



def _active_holder_frontier_version(frontier: dict[str, Any]) -> int:
    return flowpilot_router_work_packets._active_holder_frontier_version(sys.modules[__name__], frontier)



def _current_node_active_holder_lease_plan(project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], frontier: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    return flowpilot_router_work_packets._current_node_active_holder_lease_plan(sys.modules[__name__], project_root, run_root, run_state, records, frontier)



def _issue_current_node_active_holder_leases(project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return flowpilot_router_work_packets._issue_current_node_active_holder_leases(sys.modules[__name__], project_root, run_root, run_state, records)



def _packet_active_holder_lease_plan(project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> tuple[dict[str, Any], list[str]]:
    return flowpilot_router_work_packets._packet_active_holder_lease_plan(sys.modules[__name__], project_root, run_root, run_state, records, packet_family=packet_family, mode=mode)



def _issue_packet_active_holder_leases(project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> dict[str, Any]:
    return flowpilot_router_work_packets._issue_packet_active_holder_leases(sys.modules[__name__], project_root, run_root, run_state, records, packet_family=packet_family, mode=mode)



def _relay_result_records(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, to_role: str, controller_agent_id: str) -> list[str]:
    return flowpilot_router_work_packets._relay_result_records(sys.modules[__name__], project_root, run_state, records, to_role=to_role, controller_agent_id=controller_agent_id)



def _agent_role_map_from_crew_ledger(run_root: Path) -> dict[str, str] | None:
    return flowpilot_router_work_packets._agent_role_map_from_crew_ledger(sys.modules[__name__], run_root)



def _merge_agent_role_maps(primary: dict[str, str] | None, fallback: dict[str, str] | None) -> dict[str, str] | None:
    return flowpilot_router_work_packets._merge_agent_role_maps(sys.modules[__name__], primary, fallback)



def _validate_packet_bodies_opened_by_targets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    return flowpilot_router_work_packets._validate_packet_bodies_opened_by_targets(sys.modules[__name__], project_root, run_state, records)



def _validate_results_exist_for_packets(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, next_recipient: str) -> None:
    return flowpilot_router_work_packets._validate_results_exist_for_packets(sys.modules[__name__], project_root, run_state, records, next_recipient=next_recipient)



def _validate_packet_group_for_reviewer(project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, audit_path: Path, agent_role_map: dict[str, str] | None=None) -> None:
    return flowpilot_router_work_packets._validate_packet_group_for_reviewer(sys.modules[__name__], project_root, run_state, records, audit_path=audit_path, agent_role_map=agent_role_map)



def _active_frontier(run_root: Path) -> dict[str, Any]:
    return flowpilot_router_route_frontier._active_frontier(sys.modules[__name__], run_root)



def _active_route_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return flowpilot_router_route_frontier._active_route_path(sys.modules[__name__], run_root, frontier)



def _active_route_flow(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._active_route_flow(sys.modules[__name__], run_root, frontier)



def _iter_route_nodes(route: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_route_frontier._iter_route_nodes(sys.modules[__name__], route)



def _active_node_definition(run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._active_node_definition(sys.modules[__name__], run_root, frontier)



def _active_node_definition_from_route(route: dict[str, Any], active_node_id: str) -> dict[str, Any]:
    return flowpilot_router_route_frontier._active_node_definition_from_route(sys.modules[__name__], route, active_node_id)



def _is_route_root_like_node_id(node_id: str) -> bool:
    return flowpilot_router_route_frontier._is_route_root_like_node_id(sys.modules[__name__], node_id)



def _route_mutation_review_lane(run_state: dict[str, Any]) -> str:
    return flowpilot_router_route_frontier._route_mutation_review_lane(sys.modules[__name__], run_state)



def _validate_route_mutation_phase_boundary(run_root: Path, run_state: dict[str, Any], *, route_id: str, current_active_node_id: str) -> None:
    return flowpilot_router_route_frontier._validate_route_mutation_phase_boundary(sys.modules[__name__], run_root, run_state, route_id=route_id, current_active_node_id=current_active_node_id)



def _node_child_ids(node: dict[str, Any]) -> list[str]:
    return flowpilot_router_route_frontier._node_child_ids(sys.modules[__name__], node)



def _active_node_has_children(run_root: Path, frontier: dict[str, Any]) -> bool:
    return flowpilot_router_route_frontier._active_node_has_children(sys.modules[__name__], run_root, frontier)



def _route_node_map(route: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return flowpilot_router_route_frontier._route_node_map(sys.modules[__name__], route)



def _route_descendant_node_ids(route: dict[str, Any], node_id: str) -> list[str]:
    return flowpilot_router_route_frontier._route_descendant_node_ids(sys.modules[__name__], route, node_id)



def _node_completion_ledger_path_for(run_root: Path, route_id: str, node_id: str) -> Path:
    return flowpilot_router_route_frontier._node_completion_ledger_path_for(sys.modules[__name__], run_root, route_id, node_id)



def _node_completion_ledger_current(project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any], node_id: str) -> dict[str, Any]:
    return flowpilot_router_route_frontier._node_completion_ledger_current(sys.modules[__name__], project_root, run_root, run_state, frontier, node_id)



def _parent_segment_decision_value(run_root: Path, frontier: dict[str, Any]) -> str | None:
    return flowpilot_router_route_frontier._parent_segment_decision_value(sys.modules[__name__], run_root, frontier)



def _route_action_for_event(event: str) -> str | None:
    return flowpilot_router_route_frontier._route_action_for_event(sys.modules[__name__], event)



def _route_action_for_card(card_id: str) -> str | None:
    return flowpilot_router_route_frontier._route_action_for_card(sys.modules[__name__], card_id)



def _legal_next_action_context(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._legal_next_action_context(sys.modules[__name__], project_root, run_root, run_state)



def _legal_next_action_ids(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> set[str]:
    return flowpilot_router_route_frontier._legal_next_action_ids(sys.modules[__name__], project_root, run_root, run_state)



def _legal_route_action_allowed(project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str) -> bool:
    return flowpilot_router_route_frontier._legal_route_action_allowed(sys.modules[__name__], project_root, run_root, run_state, action_id)



def _first_incomplete_child_node_id(route: dict[str, Any], parent_node: dict[str, Any], completed_nodes: set[str]) -> str | None:
    return flowpilot_router_route_frontier._first_incomplete_child_node_id(sys.modules[__name__], route, parent_node, completed_nodes)



def _enter_next_child_node(project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_route_frontier._enter_next_child_node(sys.modules[__name__], project_root, run_root, run_state, pending_action)



def _next_parent_child_entry_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_route_frontier._next_parent_child_entry_action(sys.modules[__name__], project_root, run_state, run_root)



def _require_legal_route_action(project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str, context: str) -> None:
    return flowpilot_router_route_frontier._require_legal_route_action(sys.modules[__name__], project_root, run_root, run_state, action_id, context)



def _filter_events_by_legal_route_actions(project_root: Path, run_root: Path, run_state: dict[str, Any], events: list[str]) -> list[str]:
    return flowpilot_router_route_frontier._filter_events_by_legal_route_actions(sys.modules[__name__], project_root, run_root, run_state, events)



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
        and not bool(flags.get("role_recovery_obligation_replay_completed"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )


def _resume_mechanical_replay_completed_without_pm(run_state: dict[str, Any]) -> bool:
    flags = run_state["flags"]
    return (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and bool(flags.get("role_recovery_obligations_scanned"))
        and bool(flags.get("role_recovery_obligation_replay_completed"))
        and not bool(flags.get("role_recovery_pm_escalation_required"))
        and bool(flags.get("pm_resume_recovery_decision_returned"))
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
    contract = read_json_if_exists(run_root / "root_acceptance_contract.json")
    root_requirement_ids = _root_requirement_ids(contract) if isinstance(contract, dict) else []
    route_node_requirement_ids = _string_list(node.get("covers_requirement_ids")) or root_requirement_ids
    route_node_scenario_ids = _string_list(node.get("covers_scenario_ids"))
    route_node_capability_ids = _string_list(node.get("source_product_capability_ids"))
    node_requirement_ids = [
        str(item.get("requirement_id"))
        for item in node_requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]
    traced_node_requirements: list[dict[str, Any]] = []
    for item in node_requirements:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("source_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_scenario_ids", route_node_scenario_ids)
        traced.setdefault("source_product_capability_ids", route_node_capability_ids)
        traced.setdefault("change_status", "UNCHANGED")
        traced.setdefault("supersedes_requirement_ids", [])
        traced_node_requirements.append(traced)
    traced_experiment_plan: list[dict[str, Any]] = []
    for item in experiment_plan:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("covers_requirements", node_requirement_ids or route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_product_requirement_ids", _string_list(traced.get("covers_product_requirement_ids")))
        traced_experiment_plan.append(traced)
    node_requirements = traced_node_requirements
    experiment_plan = traced_experiment_plan
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
        "requirement_traceability": {
            "schema_version": "flowpilot.node_requirement_traceability.v1",
            "source_route_node_id": active_node_id,
            "source_route_node_covers_requirement_ids": route_node_requirement_ids,
            "source_route_node_covers_scenario_ids": route_node_scenario_ids,
            "source_product_capability_ids": route_node_capability_ids,
            "full_protocol_required_when_flowpilot_invoked": True,
            "all_covered_requirements_must_close_or_be_triaged": True,
            "closure_by_report_only_forbidden": True,
            "external_spec_material_advisory_until_pm_imported": True,
            "legacy_trace_defaults_inferred_by_router": "requirement_traceability" not in payload,
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
            "all_covered_requirements_closed_or_triaged": False,
            "unresolved_requirement_ids": route_node_requirement_ids,
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
        "inherited_root_requirements",
    ]:
        if optional_field in payload:
            plan[optional_field] = payload.get(optional_field)
    issues = _node_acceptance_traceability_issues(plan)
    if issues:
        raise RouterError("node acceptance plan traceability invalid: " + "; ".join(str(issue["message"]) for issue in issues[:5]))
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
    return flowpilot_router_work_packets._write_pm_research_absorption(sys.modules[__name__], project_root, run_root, run_state)



def _validate_current_node_packet_envelope(project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_current_node_packet_envelope(sys.modules[__name__], project_root, run_root, run_state, envelope, envelope_path, frontier, plan)



def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_packet_event(sys.modules[__name__], project_root, run_root, run_state, payload)



def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_result_event(sys.modules[__name__], project_root, run_state, payload)



def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_reviewer_pass(sys.modules[__name__], project_root, run_state, payload)



def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_route.route_payload_from_reviewed_draft(
        sys.modules[__name__],
        project_root,
        run_root,
        payload,
    )


def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_activation(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        payload,
    )


def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_mutation(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        payload,
    )

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
    return flowpilot_router_terminal_ledger._root_requirement_ids(sys.modules[__name__], contract)



def _string_list(value: Any) -> list[str]:
    return flowpilot_router_terminal_ledger._string_list(sys.modules[__name__], value)



def _route_nodes_with_requirement_trace(nodes: Any, root_requirement_ids: list[str]) -> list[dict[str, Any]]:
    return flowpilot_router_terminal_ledger._route_nodes_with_requirement_trace(sys.modules[__name__], nodes, root_requirement_ids)



def _node_acceptance_traceability_issues(payload: dict[str, Any]) -> list[dict[str, str]]:
    return flowpilot_router_terminal_ledger._node_acceptance_traceability_issues(sys.modules[__name__], payload)



def _requirement_trace_closure_from_root_replay(contract: dict[str, Any], root_replay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return flowpilot_router_terminal_ledger._requirement_trace_closure_from_root_replay(sys.modules[__name__], contract, root_replay)



def _final_ledger_traceability_issues(payload: dict[str, Any]) -> list[dict[str, str]]:
    return flowpilot_router_terminal_ledger._final_ledger_traceability_issues(sys.modules[__name__], payload)



def _validated_root_replay(payload: dict[str, Any], required_ids: list[str]) -> list[dict[str, Any]]:
    return flowpilot_router_terminal_ledger._validated_root_replay(sys.modules[__name__], payload, required_ids)



def _build_source_of_truth_final_entries(project_root: Path, run_root: Path, frontier: dict[str, Any], route: dict[str, Any], mutations: dict[str, Any], contract: dict[str, Any], root_replay: list[dict[str, Any]], child_manifest: dict[str, Any], evidence_ledger: dict[str, Any], generated_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_terminal_ledger._build_source_of_truth_final_entries(sys.modules[__name__], project_root, run_root, frontier, route, mutations, contract, root_replay, child_manifest, evidence_ledger, generated_ledger)



def _route_mutation_completion_issues(frontier: dict[str, Any], mutations: dict[str, Any]) -> list[str]:
    return flowpilot_router_terminal_ledger._route_mutation_completion_issues(sys.modules[__name__], frontier, mutations)



def _write_final_route_wide_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_terminal_ledger._write_final_route_wide_ledger(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_terminal_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_terminal_ledger._write_terminal_backward_replay(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_task_completion_projection(project_root: Path, run_root: Path, run_state: dict[str, Any], *, source_event: str) -> Path:
    return flowpilot_router_terminal_ledger._write_task_completion_projection(sys.modules[__name__], project_root, run_root, run_state, source_event=source_event)



def _write_terminal_closure_suite(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_terminal_ledger._write_terminal_closure_suite(sys.modules[__name__], project_root, run_root, run_state, payload)



def _write_node_completion_ledger(project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any], *, completed_node_id: str, completed_nodes: list[str], next_node_id: str | None, source_event: str='pm_completes_current_node_from_reviewed_result') -> Path:
    return flowpilot_router_route_frontier._write_node_completion_ledger(sys.modules[__name__], project_root, run_root, run_state, frontier, completed_node_id=completed_node_id, completed_nodes=completed_nodes, next_node_id=next_node_id, source_event=source_event)



def _mark_current_node_packet_records_completed(project_root: Path, run_root: Path, run_state: dict[str, Any], *, completed_node_id: str, completion_ledger_path: Path) -> None:
    return flowpilot_router_route_frontier._mark_current_node_packet_records_completed(sys.modules[__name__], project_root, run_root, run_state, completed_node_id=completed_node_id, completion_ledger_path=completion_ledger_path)



def _mark_frontier_node_completed(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, source_event: str='pm_completes_current_node_from_reviewed_result') -> None:
    return flowpilot_router_route_frontier._mark_frontier_node_completed(sys.modules[__name__], project_root, run_root, run_state, payload, source_event=source_event)



def apply_bootloader_action(project_root: Path, action_type: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_startup_flow.apply_bootloader_action(sys.modules[__name__], project_root, action_type, payload)



def _next_resume_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_resume_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_role_recovery_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_role_recovery_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_startup_heartbeat_binding_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_startup_heartbeat_binding_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_controller_boundary_confirmation_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_controller_boundary_confirmation_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_startup_mechanical_audit_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_startup_mechanical_audit_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_display_plan_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_display_plan_action(sys.modules[__name__], project_root, run_state, run_root)



def _display_plan_sync_action_summary(sync_payload: dict[str, Any]) -> str:
    return flowpilot_router_startup_flow._display_plan_sync_action_summary(sys.modules[__name__], sync_payload)



def _apply_sync_display_plan_state(project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], payload: dict[str, Any] | None=None) -> dict[str, Any]:
    return flowpilot_router_startup_flow._apply_sync_display_plan_state(sys.modules[__name__], project_root, run_root, run_state, action, payload)



def _next_startup_display_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_startup_flow._next_startup_display_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_system_card_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    manifest = load_manifest_from_run(run_root)
    resume_waiting_for_pm = (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )
    resume_replayed_without_pm = _resume_mechanical_replay_completed_without_pm(run_state)
    resume_card_ids = {"controller.resume_reentry", "pm.crew_rehydration_freshness", "pm.resume_decision"}
    for entry in SYSTEM_CARD_SEQUENCE:
        if entry["card_id"] == REVIEWER_STARTUP_FACT_CARD_ID:
            blockers = _startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
            if blockers:
                if any(blocker.get("kind") == "startup_prep_cards_not_all_sent" for blocker in blockers):
                    continue
                return _current_scope_pre_review_reconciliation_action(
                    project_root,
                    run_root,
                    run_state,
                    blockers=blockers,
                    review_trigger=entry["card_id"],
                )
        if resume_replayed_without_pm and entry["card_id"] in {"pm.crew_rehydration_freshness", "pm.resume_decision"}:
            continue
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
        if entry["card_id"] in CURRENT_SCOPE_REVIEWER_CARD_IDS:
            blockers = _pre_review_reconciliation_blockers_for_trigger(project_root, run_root, run_state, entry["card_id"])
            if blockers:
                return _current_scope_pre_review_reconciliation_action(
                    project_root,
                    run_root,
                    run_state,
                    blockers=blockers,
                    review_trigger=entry["card_id"],
                )
        policy_action = _route_action_for_card(entry["card_id"])
        legal_context: dict[str, Any] | None = None
        if policy_action:
            legal_context = _legal_next_action_context(project_root, run_root, run_state)
            if policy_action not in {str(item) for item in legal_context.get("legal_action_ids", [])}:
                continue
        to_role = _system_card_to_role(run_root, entry)
        if entry["card_id"] in STARTUP_ASYNC_CARD_IDS and to_role in CREW_ROLE_KEYS and not _active_agent_id_for_role(run_root, to_role):
            return _current_scope_pre_review_reconciliation_action(
                project_root,
                run_root,
                run_state,
                blockers=[
                    {
                        "kind": "startup_role_slots_not_ready",
                        "target_role": to_role,
                        "card_id": entry["card_id"],
                        "reason": "startup role slots must be reconciled before role-dependent startup work",
                        "scope_kind": "startup",
                        "scope_id": "startup",
                    }
                ],
                review_trigger=entry["card_id"],
            )
        if not run_state.get("manifest_check_requested"):
            manifest_extra = {"next_card_id": entry["card_id"], "next_recipient_role": to_role}
            if legal_context is not None:
                manifest_extra["legal_next_actions"] = legal_context
            return make_action(
                action_type="check_prompt_manifest",
                actor="router",
                label="router_checks_prompt_manifest",
                summary="Router checks the prompt manifest internally before exposing the next system-card relay.",
                allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra=manifest_extra,
            )
        card = manifest_card(manifest, entry["card_id"])
        delivery_extra = {"postcondition": entry["flag"]}
        gate_contract = _public_gate_contract(_gate_contract_for_card(entry["card_id"]))
        if gate_contract is not None:
            delivery_extra["gate_contract"] = gate_contract
        if legal_context is not None:
            delivery_extra["legal_next_actions"] = legal_context
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
            actor="router",
            label="router_checks_prompt_manifest",
            summary="Router checks the prompt manifest internally before exposing the next same-role system-card bundle relay.",
            allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
            allowed_writes=[project_relative(project_root, run_state_path(run_root))],
            extra={
                "next_card_id": card_ids[0],
                "bundle_candidate": True,
                "bundle_card_ids": card_ids,
                "next_recipient_role": role,
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
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        if not run_state.get("ledger_check_requested"):
            return make_action(
                action_type="check_packet_ledger",
                actor="router",
                label="router_checks_packet_ledger",
                summary="Router checks the packet ledger internally before exposing the next mail relay.",
                allowed_reads=[project_relative(project_root, run_root / "packet_ledger.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra={"next_mail_id": entry["mail_id"], "next_mail_to_role": entry["to_role"]},
            )
        extra = {"postcondition": entry["flag"]}
        role_obligation = _mail_role_obligation_contract(entry)
        if role_obligation is not None:
            extra["mail_role_obligation"] = role_obligation
        action = make_action(
            action_type="deliver_mail",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver mail {entry['mail_id']} to {entry['to_role']} through Controller.",
            allowed_reads=[project_relative(project_root, run_root / "mailbox" / "outbox" / f"{entry['mail_id']}.json")],
            allowed_writes=[project_relative(project_root, run_root / "packet_ledger.json")],
            mail_id=entry["mail_id"],
            to_role=entry["to_role"],
            extra=extra,
        )
        if role_obligation is not None:
            action["next_step_contract"]["mail_role_obligation"] = role_obligation
        return action
    return None


def _next_material_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._next_material_packet_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_research_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._next_research_packet_action(sys.modules[__name__], project_root, run_state, run_root)



def _next_current_node_packet_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._next_current_node_packet_action(sys.modules[__name__], project_root, run_state, run_root)



def _controller_status_packet_path_from_packet_envelope(packet_envelope_path: object) -> str | None:
    return flowpilot_router_work_packets._controller_status_packet_path_from_packet_envelope(sys.modules[__name__], packet_envelope_path)



def _role_output_status_packet_path_for_wait(project_root: Path, run_root: Path, *, to_role: str, allowed_events: list[str], payload_contract: dict[str, Any] | None) -> str | None:
    return flowpilot_router_work_packets._role_output_status_packet_path_for_wait(sys.modules[__name__], project_root, run_root, to_role=to_role, allowed_events=allowed_events, payload_contract=payload_contract)



def _pm_role_work_record_is_nonblocking(record: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._pm_role_work_record_is_nonblocking(sys.modules[__name__], record)



def _pm_role_work_records_are_nonblocking(records: list[dict[str, Any]]) -> bool:
    return flowpilot_router_work_packets._pm_role_work_records_are_nonblocking(sys.modules[__name__], records)



def _pm_role_work_records_dependency_class(records: list[dict[str, Any]]) -> str:
    return flowpilot_router_work_packets._pm_role_work_records_dependency_class(sys.modules[__name__], records)



def _unresolved_advisory_pm_role_work_records(run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    return flowpilot_router_work_packets._unresolved_advisory_pm_role_work_records(sys.modules[__name__], run_root, run_state)



def _next_pm_role_work_request_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    return flowpilot_router_work_packets._next_pm_role_work_request_action(sys.modules[__name__], project_root, run_state, run_root)



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
    gate_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_output_events = list(allowed_external_events)
    route_action_event_present = any(_route_action_for_event(event) for event in role_output_events)
    if route_action_event_present:
        pm_work_request_channel = False
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
    allowed_events = _validated_event_capability_names(
        allowed_events,
        context=f"await_role_decision action {label}",
        run_root=run_root,
        run_state=run_state,
        usage="wait",
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
    if route_action_event_present:
        extra["legal_next_actions"] = _legal_next_action_context(project_root, run_root, run_state)
        extra["pm_may_choose_only_from_legal_next_actions"] = True
        extra["pm_role_work_request_channel_available"] = False
    if producer_roles_override is not None:
        extra["expected_event_producer_roles"] = sorted({str(role) for role in producer_roles_override if str(role)})
    if pm_work_request_channel and to_role == "project_manager":
        extra["pm_work_request_channel_available"] = True
        extra["pm_role_work_request_event"] = PM_ROLE_WORK_REQUEST_EVENT
    if payload_contract is not None:
        extra["payload_contract"] = payload_contract
    public_gate_contract = _public_gate_contract(gate_contract)
    if public_gate_contract is not None:
        extra["gate_contract"] = public_gate_contract
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
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
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

    def group_already_has_terminal_outcome(group: list[tuple[str, dict[str, Any]]]) -> bool:
        recorded_events = [
            event
            for event, meta in group
            if flags.get(meta["flag"]) and _event_is_terminal_gate_outcome(event, meta)
        ]
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

    pending: list[list[tuple[str, dict[str, Any]]]] = []
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
    for group in pending_groups:
        group = _gate_completion_wait_group(group)
        group_events = [event for event, _meta in group]
        allowed_events = _filter_events_by_legal_route_actions(project_root, run_root, run_state, group_events)
        if not allowed_events:
            continue
        allowed_event_set = set(allowed_events)
        filtered_group = [(event, meta) for event, meta in group if event in allowed_event_set]
        roles = sorted({_event_wait_role(event, meta) for event, meta in filtered_group})
        required_flag = str(filtered_group[0][1].get("requires_flag") or "")
        role_label = roles[0] if len(roles) == 1 else ",".join(roles)
        safe_event_label = "_or_".join(allowed_events).replace("-", "_")
        route_action_wait = any(_route_action_for_event(event) for event in allowed_events)
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
            pm_work_request_channel=not route_action_wait,
            gate_contract=_gate_contract_for_events(allowed_events),
        )
    return None


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
    if status not in {"worker-result-needs-review", "result-envelope-returned", "router-next-action-ready-for-controller"}:
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
    if status_packet.get("status") not in {"result-envelope-returned", "router-next-action-ready-for-controller"}:
        return None
    result = packet_runtime.load_envelope(project_root, result_path)
    if result.get("next_recipient") != "project_manager":
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
        wait_closure = _close_waiting_controller_actions_for_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
            source="already_reconciled_packet_status_event",
        )
        if not wait_closure.get("changed"):
            return None
        return {
            "event": event,
            "packet_id": packet_id,
            "result_envelope_path": payload["result_envelope_path"],
            "packet_status": status,
            "already_recorded": True,
            "wait_closure": wait_closure,
        }
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
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="router_reconciled_pending_role_wait_from_packet_status",
    )
    append_history(
        run_state,
        "router_reconciled_pending_role_wait_from_packet_status",
        {
            "event": event,
            "packet_id": packet_id,
            "packet_status": status,
            "result_envelope_path": payload["result_envelope_path"],
            "status_packet_checked": True,
            "wait_closure": wait_closure,
        },
    )
    return {
        "event": event,
        "packet_id": packet_id,
        "result_envelope_path": payload["result_envelope_path"],
        "packet_status": status,
    }


def _record_router_reconciled_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    repeatable = event in {ROLE_WORK_RESULT_RETURNED_EVENT, "worker_current_node_result_returned"}
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        return False
    if run_state.setdefault("flags", {}).get(flag) and not repeatable:
        return False
    run_state["flags"][flag] = True
    run_state.setdefault("events", []).append(
        {
            "event": event,
            "summary": meta["summary"],
            "payload": payload,
            "recorded_at": utc_now(),
            "reconciled_by_router": True,
        }
    )
    _mark_scoped_event_recorded(run_state, scoped_identity)
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="router_reconciled_external_event",
    )
    append_history(
        run_state,
        f"router_reconciled_{event}",
        {
            "event": event,
            "payload": payload,
            "controller_visibility": "metadata_only",
            "wait_closure": wait_closure,
        },
    )
    return True


def _try_reconcile_material_scan_body_delivery(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_body_delivery(sys.modules[__name__], project_root, run_root, run_state)



def _try_reconcile_material_scan_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_results(sys.modules[__name__], project_root, run_root, run_state)



def _try_reconcile_current_node_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_current_node_results(sys.modules[__name__], project_root, run_root, run_state)



def _try_reconcile_pm_role_work_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_pm_role_work_results(sys.modules[__name__], project_root, run_root, run_state)



def _run_state_has_event(run_state: dict[str, Any], event: str) -> bool:
    return any(
        isinstance(item, dict) and item.get("event") == event
        for item in (run_state.get("events") or [])
    )


def _startup_fact_canonical_report_is_valid(run_root: Path, run_state: dict[str, Any]) -> bool:
    report = read_json_if_exists(run_root / "startup" / "startup_fact_report.json")
    return (
        report.get("schema_version") == "flowpilot.startup_fact_report.v1"
        and report.get("run_id") == run_state.get("run_id")
        and report.get("reviewed_by_role") == "human_like_reviewer"
        and report.get("status") in {"pass", "findings"}
    )


def _role_output_ledger_outputs(run_root: Path) -> list[dict[str, Any]]:
    ledger = read_json_if_exists(run_root / "role_output_ledger.json")
    outputs = ledger.get("outputs") if isinstance(ledger.get("outputs"), list) else []
    return [item for item in outputs if isinstance(item, dict)]


def _try_reconcile_startup_fact_role_output_ledger(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    event = "reviewer_reports_startup_facts"
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    flags = run_state.setdefault("flags", {})
    required_flag = str(meta.get("requires_flag") or "")
    changed = False
    reconciled = 0
    skipped_invalid = 0
    if flags.get(flag) and _run_state_has_event(run_state, event):
        return {"changed": False, "reconciled": 0, "skipped_invalid": 0}
    for record in _role_output_ledger_outputs(run_root):
        envelope = record.get("envelope")
        if not isinstance(envelope, dict):
            continue
        if str(envelope.get("event_name") or "") != event:
            continue
        if required_flag and not flags.get(required_flag):
            continue
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
        except role_output_runtime.RoleOutputRuntimeError:
            skipped_invalid += 1
            continue
        _preconsume_pending_card_return_ack_before_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
        )
        if _pending_card_return_blocker_for_event(run_root, str(run_state["run_id"]), event, run_state) is not None:
            continue
        if not _startup_fact_canonical_report_is_valid(run_root, run_state):
            try:
                _write_startup_fact_report(project_root, run_root, run_state, envelope)
            except (RouterError, role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError):
                skipped_invalid += 1
                continue
        if _run_state_has_event(run_state, event):
            if not flags.get(flag):
                flags[flag] = True
                append_history(
                    run_state,
                    "router_synced_startup_fact_flag_from_role_output_ledger",
                    {
                        "event": event,
                        "output_id": record.get("output_id"),
                        "canonical_report_path": project_relative(project_root, run_root / "startup" / "startup_fact_report.json"),
                    },
                )
                changed = True
                reconciled += 1
            break
        if _record_router_reconciled_external_event(project_root, run_root, run_state, event, envelope):
            changed = True
            reconciled += 1
            break
    return {
        "changed": changed,
        "reconciled": reconciled,
        "skipped_invalid": skipped_invalid,
    }


def _reconcile_durable_wait_evidence(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    batch_reconciliation = _refresh_all_parallel_packet_batches_from_durable_results(project_root, run_root, run_state)
    changed = bool(batch_reconciliation.get("changed"))
    role_output_reconciliation = _try_reconcile_startup_fact_role_output_ledger(project_root, run_root, run_state)
    changed = bool(role_output_reconciliation.get("changed")) or changed
    changed = _try_reconcile_material_scan_body_delivery(project_root, run_root, run_state) or changed
    changed = _try_reconcile_material_scan_results(project_root, run_root, run_state) or changed
    changed = _try_reconcile_current_node_results(project_root, run_root, run_state) or changed
    changed = _try_reconcile_pm_role_work_results(project_root, run_root, run_state) or changed
    if changed:
        run_state["parallel_batch_reconciliation"] = batch_reconciliation
        append_history(
            run_state,
            "router_reconciled_durable_wait_evidence",
            {
                "changed": changed,
                "controller_visibility": "metadata_only",
                "batches": batch_reconciliation.get("batches"),
                "role_output_reconciliation": role_output_reconciliation,
            },
        )
    return {**batch_reconciliation, "changed": changed, "role_output_reconciliation": role_output_reconciliation}


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
        "gate_contract": pending.get("gate_contract"),
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
        "gate_contract": delivery.get("gate_contract"),
        "delivered_at": delivery["delivered_at"],
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated_by_receipt": False,
    }
    envelope["envelope_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(envelope_path, envelope)
    ack_clearance_scope = _card_ack_clearance_scope(
        delivery_context,
        card_id=card_id,
        target_role=str(pending["to_role"]),
    )
    delivery["card_envelope_hash"] = envelope["envelope_hash"]
    delivery["resource_lifecycle"] = "committed_artifact"
    delivery["artifact_committed"] = True
    delivery["relay_allowed"] = True
    delivery["apply_required"] = False
    delivery["ack_clearance_scope"] = ack_clearance_scope
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
            "gate_contract": delivery.get("gate_contract"),
            "ack_clearance_scope": ack_clearance_scope,
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
            "ack_clearance_scope": ack_clearance_scope,
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
    ack_clearance_scopes: list[dict[str, Any]] = []
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
        ack_clearance_scope = _card_ack_clearance_scope(
            delivery_context,
            card_id=card_id,
            target_role=role,
        )
        ack_clearance_scopes.append(ack_clearance_scope)
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
            "ack_clearance_scope": ack_clearance_scope,
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
                "ack_clearance_scope": ack_clearance_scope,
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
                "ack_clearance_scope": delivery.get("ack_clearance_scope"),
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
    bundle_ack_clearance_scope = {
        "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
        "return_kind": "system_card_bundle",
        "card_bundle_id": bundle_id,
        "card_ids": [delivery.get("card_id") for delivery in deliveries],
        "target_role": role,
        "member_scopes": ack_clearance_scopes,
        "required_before": [
            "gate_or_node_boundary_transition",
            "formal_work_packet_relay_to_target_role",
        ],
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
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
            "ack_clearance_scope": bundle_ack_clearance_scope,
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
    return flowpilot_router_card_returns._pending_return_record_for_action(sys.modules[__name__], run_root, run_id, action)


def _pending_bundle_return_record_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._pending_bundle_return_record_for_action(sys.modules[__name__], run_root, run_id, action)


def _apply_card_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._apply_card_return_event_check(sys.modules[__name__], project_root, run_root, run_state, pending)


def _apply_card_bundle_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._apply_card_bundle_return_event_check(sys.modules[__name__], project_root, run_root, run_state, pending)


def _try_auto_consume_pending_card_return_ack(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._try_auto_consume_pending_card_return_ack(sys.modules[__name__], project_root, run_root, run_state, pending)


def _startup_pm_card_bundle_ack_record(record: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._startup_pm_card_bundle_ack_record(sys.modules[__name__], record)


def _reconcile_card_wait_rows(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    delivery_attempt_id: str,
    expected_return_path: str,
    card_return_event: str,
    card_id: str,
    source: str,
    ack_path: str | None,
) -> int:
    return flowpilot_router_card_returns._reconcile_card_wait_rows(sys.modules[__name__], project_root, run_root, run_state, delivery_attempt_id=delivery_attempt_id, expected_return_path=expected_return_path, card_return_event=card_return_event, card_id=card_id, source=source, ack_path=ack_path)


def _reconcile_card_bundle_wait_rows(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    bundle_id: str,
    expected_return_path: str,
    card_return_event: str,
    source: str,
    ack_path: str | None,
) -> int:
    return flowpilot_router_card_returns._reconcile_card_bundle_wait_rows(sys.modules[__name__], project_root, run_root, run_state, bundle_id=bundle_id, expected_return_path=expected_return_path, card_return_event=card_return_event, source=source, ack_path=ack_path)


def _router_release_startup_user_intake_to_pm(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._router_release_startup_user_intake_to_pm(sys.modules[__name__], project_root, run_root, run_state, source=source)


def _run_router_return_settlement_finalizers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._run_router_return_settlement_finalizers(sys.modules[__name__], project_root, run_root, run_state, source=source)


def _mark_card_return_pending_explicit_check(
    run_root: Path,
    run_id: str,
    action: dict[str, Any],
    *,
    reason: str,
    error: object = None,
) -> None:
    return flowpilot_router_card_returns._mark_card_return_pending_explicit_check(sys.modules[__name__], run_root, run_id, action, reason=reason, error=error)


def _preconsume_pending_card_return_ack_before_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
) -> dict[str, Any]:
    return flowpilot_router_event_intake.preconsume_pending_card_return_ack_before_external_event(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        event=event,
    )


def _system_card_delivery_flag(card_id: object) -> str:
    return flowpilot_router_event_intake.system_card_delivery_flag(sys.modules[__name__], card_id)


def _pending_return_card_delivery_flags(pending_return: dict[str, Any]) -> set[str]:
    return flowpilot_router_event_intake.pending_return_card_delivery_flags(sys.modules[__name__], pending_return)


def _role_list(value: object) -> set[str]:
    return flowpilot_router_event_intake.role_list(value)


def _pending_card_return_matches_event_dependency(
    pending_return: dict[str, Any],
    event: str,
    run_state: dict[str, Any],
) -> bool:
    return flowpilot_router_event_intake.pending_card_return_matches_event_dependency(
        sys.modules[__name__],
        pending_return,
        event,
        run_state,
    )


def _next_quarantined_role_report_path(run_root: Path, event: str) -> Path:
    return flowpilot_router_event_intake.next_quarantined_role_report_path(sys.modules[__name__], run_root, event)


def _clear_stale_role_wait_for_quarantined_report(
    run_state: dict[str, Any],
    pending_return: dict[str, Any],
    event: str,
) -> str:
    return flowpilot_router_event_intake.clear_stale_role_wait_for_quarantined_report(
        sys.modules[__name__],
        run_state,
        pending_return,
        event,
    )


def _quarantine_missing_ack_report_before_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None,
    envelope_hash: str | None,
    pending_return: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_event_intake.quarantine_missing_ack_report_before_external_event(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        envelope_path=envelope_path,
        envelope_hash=envelope_hash,
        pending_return=pending_return,
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
    return flowpilot_router_card_returns._committed_card_bundle_artifact_extra(sys.modules[__name__], project_root, record, relay_allowed_if_ready=relay_allowed_if_ready)


def _auto_commit_system_card_delivery_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_action_handlers.auto_commit_system_card_delivery_action(
        sys.modules[__name__],
        project_root,
        run_state,
        run_root,
        action,
    )


def _auto_commit_system_card_bundle_delivery_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_action_handlers.auto_commit_system_card_bundle_delivery_action(
        sys.modules[__name__],
        project_root,
        run_state,
        run_root,
        action,
    )


def _action_is_router_internal_mechanical(action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    action_type = str(action.get("action_type") or "")
    if action_type not in ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES:
        return False
    if bool(action.get("requires_user")) or bool(action.get("requires_payload")):
        return False
    if bool(action.get("requires_host_spawn")) or bool(action.get("requires_host_automation")):
        return False
    if bool(action.get("requires_user_dialog_display_confirmation")):
        return False
    if action.get("card_id") or action.get("mail_id"):
        return False
    if bool(action.get("sealed_body_reads_allowed", False)):
        return False
    return True


def _router_internal_mechanical_identity(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("action_type") or "")
    identity = {
        "action_type": action_type,
        "label": action.get("label"),
        "next_card_id": action.get("next_card_id"),
        "next_recipient_role": action.get("next_recipient_role"),
        "bundle_card_ids": action.get("bundle_card_ids") or [],
        "next_mail_id": action.get("next_mail_id"),
        "next_mail_to_role": action.get("next_mail_to_role"),
        "postcondition": action.get("postcondition"),
        "scope_kind": action.get("scope_kind"),
        "scope_id": action.get("scope_id"),
    }
    return {key: value for key, value in identity.items() if value not in (None, "", [])}


def _append_router_internal_mechanical_record(
    run_state: dict[str, Any],
    action: dict[str, Any],
    *,
    status: str,
    side_effect_applied: bool,
    error: str | None = None,
) -> dict[str, Any]:
    identity = _router_internal_mechanical_identity(action)
    event_id = "router-internal-" + hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    record = {
        "event_id": event_id,
        "action_type": action.get("action_type"),
        "label": action.get("label"),
        "identity": identity,
        "status": status,
        "side_effect_applied": side_effect_applied,
        "controller_row_written": False,
        "sealed_body_reads_allowed": False,
        "recorded_at": utc_now(),
    }
    if error:
        record["error"] = error
    run_state.setdefault("router_internal_mechanical_events", []).append(record)
    append_history(
        run_state,
        "router_consumed_internal_mechanical_action",
        {
            "action_type": action.get("action_type"),
            "event_id": event_id,
            "status": status,
            "side_effect_applied": side_effect_applied,
            "controller_row_written": False,
        },
    )
    return record


def _consume_router_internal_mechanical_action(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    if not _action_is_router_internal_mechanical(action):
        raise RouterError(f"action is not Router-internal mechanical work: {action.get('action_type')}")
    action_type = str(action.get("action_type") or "")
    try:
        side_effect_applied = False
        result_extra: dict[str, Any] = {}
        if action_type == "check_prompt_manifest":
            manifest = load_manifest_from_run(run_root)
            next_card_id = str(action.get("next_card_id") or "")
            if next_card_id:
                manifest_card(manifest, next_card_id)
            for card_id in action.get("bundle_card_ids") or []:
                if isinstance(card_id, str) and card_id:
                    manifest_card(manifest, card_id)
            if not run_state.get("manifest_check_requested"):
                run_state["manifest_check_requested"] = True
                run_state["manifest_check_requests"] = int(run_state.get("manifest_check_requests", 0)) + 1
                run_state["manifest_checks"] = int(run_state.get("manifest_checks", 0)) + 1
                side_effect_applied = True
            result_extra["next_card_id"] = next_card_id or None
        elif action_type == "check_packet_ledger":
            ledger = read_json(run_root / "packet_ledger.json")
            if ledger.get("schema_version") != PACKET_LEDGER_SCHEMA:
                raise RouterError("invalid packet ledger schema")
            if not run_state.get("ledger_check_requested"):
                run_state["ledger_check_requested"] = True
                run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
                run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
                side_effect_applied = True
            result_extra["next_mail_id"] = action.get("next_mail_id")
        elif action_type == "write_startup_mechanical_audit":
            context = _startup_mechanical_audit_context(project_root, run_root, run_state)
            if not run_state.get("flags", {}).get("startup_mechanical_audit_written") or context is None:
                computed_checks = _startup_fact_checks(project_root, run_root, run_state)
                _write_startup_mechanical_audit(project_root, run_root, run_state, computed_checks)
                context = _startup_mechanical_audit_context(project_root, run_root, run_state)
                if context is None:
                    raise RouterError("startup mechanical audit was not written with a valid proof")
                run_state.setdefault("flags", {})["startup_mechanical_audit_written"] = True
                run_state["startup_mechanical_audit"] = {
                    "path": project_relative(project_root, context["audit_path"]),
                    "sha256": context["audit_hash"],
                    "proof_path": project_relative(project_root, context["proof_path"]),
                    "proof_sha256": context["proof_hash"],
                    "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
                }
                side_effect_applied = True
            result_extra["postcondition"] = "startup_mechanical_audit_written"
        else:
            raise RouterError(f"unsupported Router-internal mechanical action: {action_type}")
        run_state["pending_action"] = None
        record = _append_router_internal_mechanical_record(
            run_state,
            action,
            status="done",
            side_effect_applied=side_effect_applied,
        )
        _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_router_internal_mechanical:{action_type}")
        _sync_derived_run_views(
            project_root,
            run_root,
            run_state,
            reason=f"after_router_internal_mechanical:{action_type}",
            update_display=True,
        )
        save_run_state(run_root, run_state)
        return {
            "ok": True,
            "consumed": True,
            "action_type": action_type,
            "event": record,
            "side_effect_applied": side_effect_applied,
            **result_extra,
        }
    except Exception as exc:
        _append_router_internal_mechanical_record(
            run_state,
            action,
            status="failed",
            side_effect_applied=False,
            error=str(exc),
        )
        save_run_state(run_root, run_state)
        raise


def compute_controller_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    _router_internal_depth: int = 0,
) -> dict[str, Any]:
    router_module = sys.modules[__name__]

    def compute_again(
        next_project_root: Path,
        next_run_state: dict[str, Any],
        next_run_root: Path,
        next_depth: int,
    ) -> dict[str, Any]:
        return compute_controller_action(
            next_project_root,
            next_run_state,
            next_run_root,
            _router_internal_depth=next_depth,
        )

    lifecycle_action = flowpilot_router_action_providers.lifecycle_provider(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    if lifecycle_action is not None:
        return lifecycle_action

    flowpilot_router_action_providers.run_reconciliation_barrier(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    pending_action = flowpilot_router_action_providers.pending_action_provider(
        router_module,
        project_root,
        run_state,
        run_root,
        router_internal_depth=_router_internal_depth,
        compute_again=compute_again,
    )
    if pending_action is not None:
        return pending_action

    action_outcome = flowpilot_router_action_providers.fresh_action_provider(
        router_module,
        project_root,
        run_state,
        run_root,
    )
    if action_outcome is None:
        raise RouterError("no legal next action provider returned an action")
    if action_outcome.finalized:
        return action_outcome.action

    return flowpilot_router_action_providers.finalize_controller_action(
        router_module,
        project_root,
        run_state,
        run_root,
        action_outcome.action,
        router_internal_depth=_router_internal_depth,
        compute_again=compute_again,
    )

def next_action(project_root: Path, *, new_invocation: bool = False) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=True, new_invocation=new_invocation)
    if _startup_daemon_controls_bootstrap(bootstrap):
        pending = bootstrap.get("pending_action")
        if (
            isinstance(pending, dict)
            and _daemon_scheduled_bootloader_action(pending)
            and _router_daemon_can_continue_after_enqueued_action(pending)
        ):
            run_state, run_root = load_run_state(project_root, bootstrap)
            if run_state is None or run_root is None:
                raise RouterError("startup daemon controls bootloader but run router state is missing")
            schedule = _startup_daemon_schedule_bootloader_action(
                project_root,
                run_root,
                run_state,
                source="foreground_next_daemon_catchup",
            )
            action = schedule.get("action") if isinstance(schedule.get("action"), dict) else None
            if isinstance(action, dict):
                return action
        boot_action = compute_bootloader_action(project_root, bootstrap)
        if boot_action is not None:
            return boot_action
        run_state, run_root = load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            raise RouterError("startup daemon controls bootloader but run router state is missing")
        schedule = _startup_daemon_schedule_bootloader_action(
            project_root,
            run_root,
            run_state,
            source="foreground_next_daemon_catchup",
        )
        action = schedule.get("action") if isinstance(schedule.get("action"), dict) else None
        if isinstance(action, dict):
            return action
        raise RouterError(
            "Router daemon controls startup but has not scheduled the next startup row; "
            f"reason={schedule.get('reason')}"
        )
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
    _ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status="controller_apply")
    _reconcile_controller_receipts(project_root, run_root, run_state)
    pending = _ensure_pending(run_state, action_type)
    result_extra: dict[str, Any] = {}
    handled_action = flowpilot_router_action_handlers.apply_registered_action(
        sys.modules[__name__],
        project_root,
        run_root,
        run_state,
        pending,
        action_type,
        payload,
    )
    if handled_action is not None:
        if handled_action.early_return is not None:
            return handled_action.early_return
        result_extra.update(handled_action.result_extra)
    else:
        raise RouterError(f"unknown controller action: {action_type}")
    append_history(run_state, str(pending["label"]), {"action_type": action_type})
    _maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="done",
        payload={"applied": action_type},
    )
    next_pending_after_apply = run_state.pop("_pending_action_after_current_apply", None)
    run_state["pending_action"] = next_pending_after_apply if isinstance(next_pending_after_apply, dict) else None
    if action_type == "write_terminal_summary":
        _mark_router_daemon_terminal(project_root, run_root, run_state, reason="terminal_summary_written")
        save_run_state(run_root, run_state)
        result = {"ok": True, "applied": action_type}
        result.update(result_extra)
        return result
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
        if "user_dialog_display_confirmation" in run_state["visible_plan_sync"]:
            result["user_dialog_display_confirmation"] = run_state["visible_plan_sync"]["user_dialog_display_confirmation"]
    return result


def _record_external_event_unchecked(project_root: Path, event: str, payload: dict[str, Any] | None=None, *, envelope_path: str | None=None, envelope_hash: str | None=None) -> dict[str, Any]:
    return flowpilot_router_event_dispatcher._record_external_event_unchecked(sys.modules[__name__], project_root, event, payload, envelope_path=envelope_path, envelope_hash=envelope_hash)



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


def _router_daemon_can_continue_after_enqueued_action(action: dict[str, Any]) -> bool:
    return flowpilot_router_daemon_runtime._router_daemon_can_continue_after_enqueued_action(sys.modules[__name__], action)


def _router_daemon_fill_action_queue(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    max_actions: int = ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._router_daemon_fill_action_queue(sys.modules[__name__], project_root, run_root, run_state, max_actions=max_actions)


def _router_daemon_tick_requests_immediate_next_tick(tick: dict[str, Any]) -> bool:
    return flowpilot_router_daemon_runtime._router_daemon_tick_requests_immediate_next_tick(sys.modules[__name__], tick)


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


def _router_daemon_tick(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    observe_only: bool,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime._router_daemon_tick(sys.modules[__name__], project_root, run_root, run_state, observe_only=observe_only)


def run_router_daemon(
    project_root: Path,
    *,
    max_ticks: int | None = None,
    observe_only: bool = False,
    replace_stale_lock: bool = False,
    release_lock_on_exit: bool = False,
    run_id: str | None = None,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime.run_router_daemon(sys.modules[__name__], project_root, max_ticks=max_ticks, observe_only=observe_only, replace_stale_lock=replace_stale_lock, release_lock_on_exit=release_lock_on_exit, run_id=run_id, run_root=run_root)


def stop_router_daemon(
    project_root: Path,
    *,
    reason: str = "manual_stop",
    run_id: str | None = None,
    run_root: str | Path | None = None,
) -> dict[str, Any]:
    return flowpilot_router_daemon_runtime.stop_router_daemon(sys.modules[__name__], project_root, reason=reason, run_id=run_id, run_root=run_root)


def record_controller_action_receipt(
    project_root: Path,
    *,
    action_id: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("controller receipt requires an active FlowPilot run")
    receipt = _write_controller_receipt(
        project_root,
        run_root,
        run_state,
        action_id=action_id,
        status=status,
        payload=payload,
    )
    _reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    status_payload = _write_router_daemon_status(
        project_root,
        run_root,
        run_state,
        lifecycle_status="controller_receipt_recorded",
        current_action=run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else None,
    )
    save_run_state(run_root, run_state)
    return {
        "ok": True,
        "command": "controller-receipt",
        "receipt": receipt,
        "daemon_status": status_payload,
        "controller_action_ledger": _controller_action_ledger_summary(run_root),
    }


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


def _recover_terminal_status_from_run_authorities(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str | None:
    return flowpilot_router_terminal_ledger._recover_terminal_status_from_run_authorities(sys.modules[__name__], project_root, run_root, run_state)



def _repair_legacy_material_packet_contracts(project_root: Path, run_root: Path) -> int:
    return flowpilot_router_terminal_ledger._repair_legacy_material_packet_contracts(sys.modules[__name__], project_root, run_root)



def reconcile_current_run(project_root: Path) -> dict[str, Any]:
    return flowpilot_router_terminal_ledger.reconcile_current_run(sys.modules[__name__], project_root)



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
        issues.extend(_node_acceptance_traceability_issues(payload))
    elif artifact_type == "final_route_wide_gate_ledger":
        required_top = (
            "schema_version",
            "run_id",
            "pm_owned",
            "status",
            "source_paths",
            "evidence_integrity",
            "counts",
            "entries",
            "root_contract_replay",
            "requirement_trace_closure",
        )
        for field in required_top:
            if field not in payload or payload.get(field) in (None, "", []):
                issues.append(_artifact_issue(field, "missing required field", "project_manager"))
        if payload.get("pm_owned") is not True:
            issues.append(_artifact_issue("pm_owned", "final ledger must be PM-owned", "project_manager"))
        if payload.get("status") != "clean":
            issues.append(_artifact_issue("status", "final ledger must be clean", "project_manager"))
        counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
        if int(counts.get("unresolved_count", 0) or 0) != 0:
            issues.append(_artifact_issue("counts.unresolved_count", "final ledger requires unresolved_count=0", "project_manager"))
        issues.extend(_final_ledger_traceability_issues(payload))
    elif artifact_type == "self_interrogation_record":
        record_issues, unresolved_hard_count = _self_interrogation_record_issues(
            project_root,
            project_root / ".flowpilot" / "runs" / str(payload.get("run_id") or ""),
            path,
            payload,
        )
        for issue in record_issues:
            issues.append(_artifact_issue(str(issue.get("scope") or issue.get("record_id") or "self_interrogation_record"), str(issue.get("message") or "invalid self-interrogation record"), str(payload.get("owner_role") or "project_manager")))
        if unresolved_hard_count != 0:
            issues.append(_artifact_issue("unresolved_hard_finding_count", "self-interrogation record has unresolved hard/current findings", str(payload.get("owner_role") or "project_manager")))
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
    start_parser = sub.add_parser("start", help="Start a fresh formal FlowPilot invocation")
    start_parser.add_argument("--max-steps", type=int, default=50)
    start_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    next_parser = sub.add_parser("next", help="Return the next router-authorized action for an existing run")
    next_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    next_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    run_wait_parser = sub.add_parser("run-until-wait", help="Apply safe internal router actions and return the next wait-boundary action")
    run_wait_parser.add_argument("--max-steps", type=int, default=50)
    run_wait_parser.add_argument("--new-invocation", action="store_true", help="Start a fresh formal FlowPilot invocation")
    run_wait_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    daemon_parser = sub.add_parser("daemon", help="Run the persistent Router daemon loop for the current run")
    daemon_parser.add_argument("--max-ticks", type=int, default=None, help="Stop after this many one-second daemon ticks")
    daemon_parser.add_argument("--observe-only", action="store_true", help="Write daemon status without advancing router state")
    daemon_parser.add_argument("--replace-stale-lock", action="store_true", help="Replace a stale daemon lock explicitly")
    daemon_parser.add_argument("--release-lock-on-exit", action="store_true", help="Release the daemon lock when a bounded daemon run exits")
    daemon_parser.add_argument("--run-id", default="", help="Bind daemon to this run id instead of the current focus run")
    daemon_parser.add_argument("--run-root", default="", help="Bind daemon to this run root instead of the current focus run")
    daemon_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    daemon_stop_parser = sub.add_parser("daemon-stop", help="Stop or release the current run's Router daemon lock")
    daemon_stop_parser.add_argument("--reason", default="manual_stop")
    daemon_stop_parser.add_argument("--run-id", default="", help="Stop this run id instead of the current focus run")
    daemon_stop_parser.add_argument("--run-root", default="", help="Stop this run root instead of the current focus run")
    daemon_stop_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    standby_parser = sub.add_parser("controller-standby", help="Keep foreground Controller waiting on Router daemon status and action ledger")
    standby_parser.add_argument("--max-seconds", type=float, default=FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS)
    standby_parser.add_argument("--poll-seconds", type=float, default=FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS)
    standby_parser.add_argument("--bounded-diagnostic", action="store_true", help="Return timeout_still_waiting at max-seconds for diagnostics/tests instead of continuing standby")
    standby_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    patrol_parser = sub.add_parser("controller-patrol-timer", help="Wait, read the existing Router daemon monitor, and return the next Controller patrol instruction")
    patrol_parser.add_argument("--seconds", type=float, default=CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS)
    patrol_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    receipt_parser = sub.add_parser("controller-receipt", help="Record a Controller action ledger receipt")
    receipt_parser.add_argument("--action-id", required=True)
    receipt_parser.add_argument("--status", required=True, choices=sorted(CONTROLLER_RECEIPT_STATUSES))
    receipt_parser.add_argument("--payload-json", default="")
    receipt_parser.add_argument("--json", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
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
    validate_parser.add_argument("--type", required=True, choices=["node_acceptance_plan", "final_route_wide_gate_ledger", "self_interrogation_record", "packet_envelope", "result_envelope", "role_output_envelope", "gate_decision"])
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
        if args.command == "start":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: run_until_wait(root, max_steps=int(args.max_steps), new_invocation=True),
                command_name=args.command,
            )
        elif args.command == "next":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: next_action(root, new_invocation=bool(getattr(args, "new_invocation", False))),
                command_name=args.command,
            )
        elif args.command == "run-until-wait":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: run_until_wait(
                    root,
                    max_steps=int(args.max_steps),
                    new_invocation=bool(getattr(args, "new_invocation", False)),
                ),
                command_name=args.command,
            )
        elif args.command == "daemon":
            result = run_router_daemon(
                root,
                max_ticks=getattr(args, "max_ticks", None),
                observe_only=bool(getattr(args, "observe_only", False)),
                replace_stale_lock=bool(getattr(args, "replace_stale_lock", False)),
                release_lock_on_exit=bool(getattr(args, "release_lock_on_exit", False)),
                run_id=getattr(args, "run_id", "") or None,
                run_root=getattr(args, "run_root", "") or None,
            )
        elif args.command == "daemon-stop":
            result = stop_router_daemon(
                root,
                reason=str(getattr(args, "reason", "manual_stop") or "manual_stop"),
                run_id=getattr(args, "run_id", "") or None,
                run_root=getattr(args, "run_root", "") or None,
            )
        elif args.command == "controller-standby":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: foreground_controller_standby(
                    root,
                    max_seconds=float(getattr(args, "max_seconds", FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS)),
                    poll_seconds=float(getattr(args, "poll_seconds", FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS)),
                    bounded_diagnostic=bool(getattr(args, "bounded_diagnostic", False)),
                ),
                command_name=args.command,
            )
        elif args.command == "controller-patrol-timer":
            result = _run_foreground_with_runtime_writer_settlement(
                lambda: controller_patrol_timer(
                    root,
                    seconds=float(getattr(args, "seconds", CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS)),
                ),
                command_name=args.command,
            )
        elif args.command == "controller-receipt":
            payload = json.loads(args.payload_json) if args.payload_json else {}
            result = record_controller_action_receipt(root, action_id=args.action_id, status=args.status, payload=payload)
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
            def _state_command() -> dict[str, Any]:
                bootstrap = load_bootstrap_state(root, create_if_missing=False)
                run_state, run_root = load_run_state(root, bootstrap)
                active_ui_task_catalog = (
                    _active_ui_task_catalog(root, run_root, run_state)
                    if run_state is not None and run_root is not None
                    else {"schema_version": "flowpilot.active_ui_task_catalog.v1", "active_tasks": []}
                )
                return {
                    "bootstrap": bootstrap,
                    "run_root": str(run_root) if run_root else None,
                    "run_state": run_state,
                    "active_ui_task_catalog": active_ui_task_catalog,
                    "router_daemon_status": read_json_if_exists(_router_daemon_status_path(run_root)) if run_root else {},
                    "controller_action_ledger": read_json_if_exists(_controller_action_ledger_path(run_root)) if run_root else {},
                }

            result = _run_foreground_with_runtime_writer_settlement(_state_command, command_name=args.command)
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
