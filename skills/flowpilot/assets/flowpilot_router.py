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
from types import ModuleType
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
import flowpilot_router_self_interrogation
import flowpilot_router_controller_repair
import flowpilot_router_action_factory
import flowpilot_router_payload_contracts
import flowpilot_router_lifecycle_requests
import flowpilot_router_route_artifacts
import flowpilot_router_system_cards
import flowpilot_router_expected_waits
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


from flowpilot_router_protocol_catalog import *
from flowpilot_router_facade_exports import install_facade_exports


_ROUTER_MODULE = sys.modules.get(__name__)
if _ROUTER_MODULE is None:
    _ROUTER_MODULE = ModuleType(__name__)
    sys.modules[__name__] = _ROUTER_MODULE
_ROUTER_MODULE.__dict__.update(globals())
install_facade_exports(_ROUTER_MODULE, globals())
_ROUTER_MODULE.__dict__.update(globals())


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


CURRENT_SCOPE_REVIEWER_CARD_IDS = {
    "reviewer.worker_result_review",
}

CURRENT_SCOPE_REVIEW_EVENTS = {
    "current_node_reviewer_passes_result",
    "current_node_reviewer_blocks_result",
}


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
        PM_MODEL_MISS_TRIAGE_DECISION_EVENT,
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
    "pm.review_repair": (
        "pm_revises_node_acceptance_plan",
        "pm_mutates_route_after_review_block",
    ),
}


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


PRE_ROUTE_PHASE_ITEMS = (
    ("material_understanding", "Material understanding", "pm_material_understanding_card_delivered"),
    ("product_architecture", "Product architecture", "pm_product_architecture_card_delivered"),
    ("root_contract", "Root contract", "pm_root_contract_card_delivered"),
    ("dependency_policy", "Dependency policy", "pm_dependency_policy_card_delivered"),
    ("child_skill_gate_manifest", "Child-skill gates", "pm_child_skill_gate_manifest_card_delivered"),
)


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


_ROUTER_MODULE.__dict__.update(globals())


if __name__ == "__main__":
    raise SystemExit(main())
