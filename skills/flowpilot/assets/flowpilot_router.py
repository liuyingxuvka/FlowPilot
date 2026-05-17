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


def _direct_router_ack_token_for_card(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._direct_router_ack_token_for_card(*args, **kwargs)


def _direct_router_ack_token_for_bundle(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._direct_router_ack_token_for_bundle(*args, **kwargs)


def _pm_suggestion_ledger_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._pm_suggestion_ledger_path(*args, **kwargs)


def _read_pm_suggestion_ledger(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._read_pm_suggestion_ledger(*args, **kwargs)


def _pm_suggestion_ledger_status(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._pm_suggestion_ledger_status(*args, **kwargs)


def _self_interrogation_index_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_index_path(*args, **kwargs)


def _self_interrogation_issue(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_issue(*args, **kwargs)


def _self_interrogation_entry_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_entry_path(*args, **kwargs)


def _self_interrogation_final_status(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_final_status(*args, **kwargs)


def _self_interrogation_record_issues(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_record_issues(*args, **kwargs)


def _self_interrogation_status(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._self_interrogation_status(*args, **kwargs)


def _format_self_interrogation_status_issue(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._format_self_interrogation_status_issue(*args, **kwargs)


def _require_clean_self_interrogation(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._require_clean_self_interrogation(*args, **kwargs)


def resolve_project_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation.resolve_project_path(*args, **kwargs)


def _evidence_path_record(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._evidence_path_record(*args, **kwargs)


def _router_owned_check_proof_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._router_owned_check_proof_path(*args, **kwargs)


def _write_router_owned_check_proof(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_self_interrogation._bind_router(sys.modules[__name__])
    return flowpilot_router_self_interrogation._write_router_owned_check_proof(*args, **kwargs)


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


def _close_waiting_controller_actions_for_external_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._close_waiting_controller_actions_for_external_event(*args, **kwargs)


def _pending_controller_action_id(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._pending_controller_action_id(*args, **kwargs)


def _pending_action_postcondition(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._pending_action_postcondition(*args, **kwargs)


def _receipt_for_pending_controller_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._receipt_for_pending_controller_action(*args, **kwargs)


def _pending_action_postcondition_satisfied(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._pending_action_postcondition_satisfied(*args, **kwargs)


def _mail_sequence_entry(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mail_sequence_entry(*args, **kwargs)


def _mail_role_obligation_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mail_role_obligation_contract(*args, **kwargs)


def _mail_delivery_matches(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mail_delivery_matches(*args, **kwargs)


def _find_mail_delivery(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._find_mail_delivery(*args, **kwargs)


def _count_unique_mail_deliveries(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._count_unique_mail_deliveries(*args, **kwargs)


def _packet_record_for_mail_delivery(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._packet_record_for_mail_delivery(*args, **kwargs)


def _mail_delivery_action_envelope_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mail_delivery_action_envelope_path(*args, **kwargs)


def _mail_delivery_packet_released(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mail_delivery_packet_released(*args, **kwargs)


def _ensure_mail_delivery_packet_released(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._ensure_mail_delivery_packet_released(*args, **kwargs)


def _fold_mail_delivery_postcondition(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._fold_mail_delivery_postcondition(*args, **kwargs)


def _controller_boundary_required_deliverable(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_boundary_required_deliverable(*args, **kwargs)


def _controller_action_required_deliverables(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_action_required_deliverables(*args, **kwargs)


def _controller_deliverable_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_deliverable_contract(*args, **kwargs)


def _missing_deliverables_for_apply_result(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._missing_deliverables_for_apply_result(*args, **kwargs)


def _update_controller_action_entry_fields(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._update_controller_action_entry_fields(*args, **kwargs)


def _defer_controller_postcondition_reconciliation_retry(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._defer_controller_postcondition_reconciliation_retry(*args, **kwargs)


def _sync_controller_boundary_confirmation_from_artifact(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._sync_controller_boundary_confirmation_from_artifact(*args, **kwargs)


def _controller_boundary_flags_synced(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_boundary_flags_synced(*args, **kwargs)


def _router_scheduler_row_for_controller_entry(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._router_scheduler_row_for_controller_entry(*args, **kwargs)



def _done_controller_receipt_for_entry(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._done_controller_receipt_for_entry(*args, **kwargs)



def _reconcile_controller_boundary_confirmation_projection(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._reconcile_controller_boundary_confirmation_projection(*args, **kwargs)


def _mark_controller_deliverable_repair_resolved(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._mark_controller_deliverable_repair_resolved(*args, **kwargs)


def _controller_deliverable_failed_repair_ids(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_deliverable_failed_repair_ids(*args, **kwargs)


def _controller_repair_action_is_pending(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._controller_repair_action_is_pending(*args, **kwargs)


def _write_controller_deliverable_budget_blocker(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._write_controller_deliverable_budget_blocker(*args, **kwargs)


def _schedule_controller_deliverable_repair(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._schedule_controller_deliverable_repair(*args, **kwargs)


def _reclaim_router_owned_postcondition_from_artifact(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_controller_repair._bind_router(sys.modules[__name__])
    return flowpilot_router_controller_repair._reclaim_router_owned_postcondition_from_artifact(*args, **kwargs)


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


def _current_scope_pre_review_reconciliation_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._current_scope_pre_review_reconciliation_action(*args, **kwargs)


def _current_scope_reconciliation_wait_still_blocked(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._current_scope_reconciliation_wait_still_blocked(*args, **kwargs)


def _next_local_obligation_before_passive_wait(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._next_local_obligation_before_passive_wait(*args, **kwargs)


def _current_node_scope_exit_reconciliation_blockers(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._current_node_scope_exit_reconciliation_blockers(*args, **kwargs)


def _action_is_startup_async_delivery(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._action_is_startup_async_delivery(*args, **kwargs)


def _action_is_startup_async_card_wait(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._action_is_startup_async_card_wait(*args, **kwargs)


def _startup_async_pending_returns(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._startup_async_pending_returns(*args, **kwargs)


def _pending_card_return_blocker_for_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._pending_card_return_blocker_for_event(*args, **kwargs)


def _committed_card_artifact_extra(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._committed_card_artifact_extra(*args, **kwargs)


def _next_pending_card_return_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._next_pending_card_return_action(*args, **kwargs)


FORMAL_WORK_PACKET_RELAY_ACTION_TYPES = {
    "relay_material_scan_packets",
    "relay_research_packet",
    "relay_current_node_packet",
    "relay_pm_role_work_request_packet",
}


def _roles_from_action_to_role(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._roles_from_action_to_role(*args, **kwargs)


def _apply_formal_work_packet_ack_preflight(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._apply_formal_work_packet_ack_preflight(*args, **kwargs)


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


def _dispatch_gate_card_entry(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_card_entry(*args, **kwargs)


def _dispatch_gate_output_events_for_card_id(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_output_events_for_card_id(*args, **kwargs)


def _dispatch_gate_output_events_for_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_output_events_for_action(*args, **kwargs)


def _dispatch_gate_action_is_ack_only_prompt(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_action_is_ack_only_prompt(*args, **kwargs)


def _dispatch_gate_action_work_class(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_action_work_class(*args, **kwargs)


def _dispatch_gate_same_obligation_instruction_context(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_same_obligation_instruction_context(*args, **kwargs)


def _dispatch_gate_wait_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_wait_action(*args, **kwargs)


def _dispatch_gate_pending_ack_wait(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_pending_ack_wait(*args, **kwargs)


def _dispatch_gate_packet_blocker(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_packet_blocker(*args, **kwargs)


def _dispatch_gate_pending_expected_output_blocker(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_pending_expected_output_blocker(*args, **kwargs)


def _dispatch_gate_pm_role_work_blocker(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_pm_role_work_blocker(*args, **kwargs)


def _dispatch_gate_passive_wait_blocker(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._dispatch_gate_passive_wait_blocker(*args, **kwargs)


def _apply_dispatch_recipient_gate(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._apply_dispatch_recipient_gate(*args, **kwargs)


def append_history(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory.append_history(*args, **kwargs)


def _controller_user_reporting_policy(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory._controller_user_reporting_policy(*args, **kwargs)


def make_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_action_factory._bind_router(sys.modules[__name__])
    return flowpilot_router_action_factory.make_action(*args, **kwargs)


def _payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._payload_contract(*args, **kwargs)


def _startup_answers_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._startup_answers_payload_contract(*args, **kwargs)


def _terminal_summary_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._terminal_summary_payload_contract(*args, **kwargs)


def _display_surface_receipt_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._display_surface_receipt_payload_contract(*args, **kwargs)


def _role_slots_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._role_slots_payload_contract(*args, **kwargs)


def _heartbeat_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._heartbeat_payload_contract(*args, **kwargs)


def _resume_role_rehydration_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._resume_role_rehydration_payload_contract(*args, **kwargs)


def _pm_resume_decision_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._pm_resume_decision_payload_contract(*args, **kwargs)


def _pm_parent_segment_decision_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._pm_parent_segment_decision_payload_contract(*args, **kwargs)


def _pm_terminal_closure_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._pm_terminal_closure_payload_contract(*args, **kwargs)


def _pm_model_miss_triage_payload_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._pm_model_miss_triage_payload_contract(*args, **kwargs)


def _pm_decision_payload_contract_for_card(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._pm_decision_payload_contract_for_card(*args, **kwargs)


def _role_decision_payload_contract_for_events(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_payload_contracts._bind_router(sys.modules[__name__])
    return flowpilot_router_payload_contracts._role_decision_payload_contract_for_events(*args, **kwargs)


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



def _clear_active_control_blocker_for_terminal_lifecycle(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._clear_active_control_blocker_for_terminal_lifecycle(*args, **kwargs)


def _write_run_lifecycle_request(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._write_run_lifecycle_request(*args, **kwargs)


def _reconcile_terminal_lifecycle_authorities(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._reconcile_terminal_lifecycle_authorities(*args, **kwargs)


def _write_protocol_dead_end_lifecycle(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._write_protocol_dead_end_lifecycle(*args, **kwargs)


def _run_lifecycle_terminal_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._run_lifecycle_terminal_action(*args, **kwargs)


def _try_write_control_blocker_for_exception(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_lifecycle_requests._bind_router(sys.modules[__name__])
    return flowpilot_router_lifecycle_requests._try_write_control_blocker_for_exception(*args, **kwargs)


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



def _write_product_function_architecture(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_product_function_architecture(*args, **kwargs)


def _write_role_gate_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_role_gate_report(*args, **kwargs)


def _write_compatibility_alias_artifact(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_compatibility_alias_artifact(*args, **kwargs)


def _write_product_behavior_model_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_product_behavior_model_report(*args, **kwargs)


def _write_pm_model_decision(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_model_decision(*args, **kwargs)


def _write_pm_product_behavior_model_decision(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_product_behavior_model_decision(*args, **kwargs)


def _write_pm_process_route_model_decision(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_process_route_model_decision(*args, **kwargs)


def _write_role_block_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_role_block_report(*args, **kwargs)


def _gate_outcome_path_from_token(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._gate_outcome_path_from_token(*args, **kwargs)


def _write_gate_outcome_block_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_gate_outcome_block_report(*args, **kwargs)


def _clear_active_gate_outcome_block_for_pass(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._clear_active_gate_outcome_block_for_pass(*args, **kwargs)


def _write_route_process_pass_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_route_process_pass_report(*args, **kwargs)


def _write_route_process_issue_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_route_process_issue_report(*args, **kwargs)


def _write_route_product_pass_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_route_product_pass_report(*args, **kwargs)


def _write_root_acceptance_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_root_acceptance_contract(*args, **kwargs)


def _freeze_root_acceptance_contract(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._freeze_root_acceptance_contract(*args, **kwargs)


def _write_dependency_policy(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_dependency_policy(*args, **kwargs)


def _write_capabilities_manifest(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_capabilities_manifest(*args, **kwargs)


def _validate_selected_child_skills(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._validate_selected_child_skills(*args, **kwargs)


def _write_child_skill_selection(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_child_skill_selection(*args, **kwargs)


def _write_child_skill_gate_manifest(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_child_skill_gate_manifest(*args, **kwargs)


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


def _write_pm_resume_decision(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_resume_decision(*args, **kwargs)


def _write_node_acceptance_plan(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_node_acceptance_plan(*args, **kwargs)


def _write_pm_revised_node_acceptance_plan(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_revised_node_acceptance_plan(*args, **kwargs)


def _write_parent_backward_targets(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_parent_backward_targets(*args, **kwargs)


def _write_parent_backward_replay(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_parent_backward_replay(*args, **kwargs)


def _write_parent_segment_decision(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_parent_segment_decision(*args, **kwargs)


def _write_pm_research_absorption(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_research_absorption(*args, **kwargs)



def _validate_current_node_packet_envelope(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._validate_current_node_packet_envelope(*args, **kwargs)



def _validate_current_node_packet_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._validate_current_node_packet_event(*args, **kwargs)



def _validate_current_node_result_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._validate_current_node_result_event(*args, **kwargs)



def _validate_current_node_reviewer_pass(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._validate_current_node_reviewer_pass(*args, **kwargs)



def _route_payload_from_reviewed_draft(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._route_payload_from_reviewed_draft(*args, **kwargs)


def _write_route_activation(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_route_activation(*args, **kwargs)


def _write_route_mutation(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_route_mutation(*args, **kwargs)

def _write_material_dispatch_repair(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_material_dispatch_repair(*args, **kwargs)


def _write_pm_review_block_repair(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_pm_review_block_repair(*args, **kwargs)


def _write_evidence_quality_package(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_route_artifacts._bind_router(sys.modules[__name__])
    return flowpilot_router_route_artifacts._write_evidence_quality_package(*args, **kwargs)


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



def _next_system_card_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._next_system_card_action(*args, **kwargs)


def _system_card_bundle_candidate_actions(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._system_card_bundle_candidate_actions(*args, **kwargs)


def _next_system_card_bundle_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._next_system_card_bundle_action(*args, **kwargs)


def _system_card_to_role(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._system_card_to_role(*args, **kwargs)


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



def _next_model_miss_followup_request_wait_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._next_model_miss_followup_request_wait_action(*args, **kwargs)


def _next_model_miss_controlled_stop_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._next_model_miss_controlled_stop_action(*args, **kwargs)


def _expected_role_decision_wait_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._expected_role_decision_wait_action(*args, **kwargs)


def _event_wait_role(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._event_wait_role(*args, **kwargs)


def _active_node_children_status(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._active_node_children_status(*args, **kwargs)


def _event_applicable_for_active_node(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._event_applicable_for_active_node(*args, **kwargs)


def _pending_expected_external_event_groups(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._pending_expected_external_event_groups(*args, **kwargs)


def _next_expected_role_decision_wait_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._next_expected_role_decision_wait_action(*args, **kwargs)


def _pending_role_decision_staleness(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._pending_role_decision_staleness(*args, **kwargs)


def _reconcile_pending_role_wait_from_packet_status(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._reconcile_pending_role_wait_from_packet_status(*args, **kwargs)


def _record_router_reconciled_external_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._record_router_reconciled_external_event(*args, **kwargs)


def _try_reconcile_material_scan_body_delivery(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._try_reconcile_material_scan_body_delivery(*args, **kwargs)



def _try_reconcile_material_scan_results(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._try_reconcile_material_scan_results(*args, **kwargs)



def _try_reconcile_current_node_results(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._try_reconcile_current_node_results(*args, **kwargs)



def _try_reconcile_pm_role_work_results(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._try_reconcile_pm_role_work_results(*args, **kwargs)



def _run_state_has_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_expected_waits._bind_router(sys.modules[__name__])
    return flowpilot_router_expected_waits._run_state_has_event(*args, **kwargs)


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


def _reconcile_durable_wait_evidence(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._reconcile_durable_wait_evidence(*args, **kwargs)


def _commit_system_card_delivery_artifact(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._commit_system_card_delivery_artifact(*args, **kwargs)


def _commit_system_card_bundle_delivery_artifact(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._commit_system_card_bundle_delivery_artifact(*args, **kwargs)


def _pending_return_record_for_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._pending_return_record_for_action(*args, **kwargs)


def _pending_bundle_return_record_for_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._pending_bundle_return_record_for_action(*args, **kwargs)


def _apply_card_return_event_check(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._apply_card_return_event_check(*args, **kwargs)


def _apply_card_bundle_return_event_check(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._apply_card_bundle_return_event_check(*args, **kwargs)


def _try_auto_consume_pending_card_return_ack(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._try_auto_consume_pending_card_return_ack(*args, **kwargs)


def _startup_pm_card_bundle_ack_record(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._startup_pm_card_bundle_ack_record(*args, **kwargs)


def _reconcile_card_wait_rows(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._reconcile_card_wait_rows(*args, **kwargs)


def _reconcile_card_bundle_wait_rows(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._reconcile_card_bundle_wait_rows(*args, **kwargs)


def _router_release_startup_user_intake_to_pm(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._router_release_startup_user_intake_to_pm(*args, **kwargs)


def _run_router_return_settlement_finalizers(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._run_router_return_settlement_finalizers(*args, **kwargs)


def _mark_card_return_pending_explicit_check(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._mark_card_return_pending_explicit_check(*args, **kwargs)


def _preconsume_pending_card_return_ack_before_external_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._preconsume_pending_card_return_ack_before_external_event(*args, **kwargs)


def _system_card_delivery_flag(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._system_card_delivery_flag(*args, **kwargs)


def _pending_return_card_delivery_flags(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._pending_return_card_delivery_flags(*args, **kwargs)


def _role_list(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._role_list(*args, **kwargs)


def _pending_card_return_matches_event_dependency(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._pending_card_return_matches_event_dependency(*args, **kwargs)


def _next_quarantined_role_report_path(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._next_quarantined_role_report_path(*args, **kwargs)


def _clear_stale_role_wait_for_quarantined_report(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._clear_stale_role_wait_for_quarantined_report(*args, **kwargs)


def _quarantine_missing_ack_report_before_external_event(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._quarantine_missing_ack_report_before_external_event(*args, **kwargs)


def _record_card_return_event_from_external_entrypoint(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._record_card_return_event_from_external_entrypoint(*args, **kwargs)


def _committed_card_bundle_artifact_extra(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._committed_card_bundle_artifact_extra(*args, **kwargs)


def _auto_commit_system_card_delivery_action(*args: Any, **kwargs: Any) -> Any:
    flowpilot_router_system_cards._bind_router(sys.modules[__name__])
    return flowpilot_router_system_cards._auto_commit_system_card_delivery_action(*args, **kwargs)


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
