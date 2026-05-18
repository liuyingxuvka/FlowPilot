"""Coarse events repair owner helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
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

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress

_DEFAULT_SENTINEL = object()


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _write_control_blocker_repair_packet(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, category: str, target_role: str, responsible_role: str, error_message: str, event: str | None, action_type: str | None, payload: dict[str, Any] | None, policy_row: dict[str, Any], policy_snapshot_path: str, direct_retry_attempts_used: int, direct_retry_budget_exhausted: bool) -> dict[str, str]:
    _bind_router(router)
    packet_path = run_root / 'control_blocks' / f'{blocker_id}.sealed_repair_packet.json'
    packet = {'schema_version': CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA, 'blocker_id': blocker_id, 'run_id': run_state.get('run_id'), 'body_visibility': 'sealed_router_repair_details_for_target_role', 'target_role': target_role, 'responsible_role_for_reissue': responsible_role if category == 'control_plane_reissue' else None, 'handling_lane': category, 'policy_row_id': policy_row.get('policy_row_id'), 'blocker_family': policy_row.get('blocker_family'), 'first_handler': policy_row.get('first_handler'), 'direct_retry_budget': policy_row.get('direct_retry_budget'), 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'originating_event': event, 'originating_action_type': action_type, 'error_code': router._control_blocker_error_code(error_message), 'error_message': error_message, 'source_paths': router._payload_source_paths(project_root, run_root, payload), 'payload_envelope_public_view': router._control_payload_public_view(payload), 'controller_may_read_body': False, 'controller_may_repair_from_this_packet': False, 'target_role_repair_instruction': 'Inspect this sealed packet, fix the rejected control-plane output, and reissue the router event named in allowed_resolution_events. Do not ask Controller to infer or patch the body.', 'allowed_resolution_events': router._control_blocker_allowed_resolution_events(category, event), 'created_at': utc_now()}
    write_json(packet_path, packet)
    return {'sealed_repair_packet_path': project_relative(project_root, packet_path), 'sealed_repair_packet_hash': hashlib.sha256(packet_path.read_bytes()).hexdigest()}

def _supersede_prior_control_blockers(router: ModuleType, run_root: Path, *, blocker_id: str, category: str, event: str | None, action_type: str | None, attempt_key: str | None=None) -> None:
    _bind_router(router)
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return
    superseded_at = utc_now()
    for path in sorted(control_root.glob('*.json')):
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        if record.get('resolution_status') or record.get('blocker_id') == blocker_id:
            continue
        if attempt_key:
            if record.get('attempt_key') != attempt_key:
                continue
        else:
            if record.get('handling_lane') != category:
                continue
            if record.get('originating_event') != event or record.get('originating_action_type') != action_type:
                continue
        record['resolution_status'] = 'superseded_by_newer_control_blocker'
        record['superseded_by_blocker_id'] = blocker_id
        record['resolved_at'] = superseded_at
        record['resolution_note'] = 'A newer router rejection for the same control-plane event replaced this pending repair packet.'
        write_json(path, record)

def _nonnegative_int_or_none(router: ModuleType, value: Any) -> int | None:
    _bind_router(router)
    if value is None or value == '':
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None

def _write_control_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str, error_message: str, event: str | None=None, action_type: str | None=None, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    base_category = router._classify_control_blocker(error_message, event=event, action_type=action_type, source=source)
    if base_category not in CONTROL_BLOCKER_LANES:
        base_category = 'pm_repair_decision_required'
    payload_view = payload if isinstance(payload, dict) else {}
    apply_result = payload_view.get('apply_result') if isinstance(payload_view.get('apply_result'), dict) else {}
    origin_controller_action_id = str(payload_view.get('controller_action_id') or payload_view.get('current_controller_action_id') or apply_result.get('controller_action_id') or '').strip() or None
    origin_router_scheduler_row_id = str(payload_view.get('router_scheduler_row_id') or apply_result.get('router_scheduler_row_id') or '').strip() or None
    origin_postcondition = str(payload_view.get('postcondition') or apply_result.get('postcondition') or '').strip() or None
    responsible_role = router._infer_responsible_role(event, payload, error_message)
    if source == CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE and base_category == 'control_plane_reissue' and (responsible_role == 'project_manager'):
        responsible_role = 'controller'
    policy_row = router._control_blocker_policy_row(error_message, base_category)
    policy_row_id = str(policy_row.get('policy_row_id') or 'pm_semantic_repair')
    attempt_key = router._control_blocker_attempt_key(policy_row_id=policy_row_id, event=event, action_type=action_type, responsible_role=responsible_role)
    retry_attempt_override = router._nonnegative_int_or_none(payload_view.get('direct_retry_attempts_used'))
    if retry_attempt_override is None:
        retry_attempt_override = router._nonnegative_int_or_none(apply_result.get('direct_retry_attempts_used'))
    if retry_attempt_override is None:
        direct_retry_attempts_used = router._control_blocker_direct_attempts_used(run_state, attempt_key)
    else:
        direct_retry_attempts_used = retry_attempt_override
    retry_budget_override = router._nonnegative_int_or_none(payload_view.get('direct_retry_budget'))
    if retry_budget_override is None:
        retry_budget_override = router._nonnegative_int_or_none(apply_result.get('direct_retry_budget'))
    direct_retry_budget = retry_budget_override if retry_budget_override is not None else int(policy_row.get('direct_retry_budget') or 0)
    first_handler = str(policy_row.get('first_handler') or 'project_manager')
    direct_retry_budget_exhausted = direct_retry_attempts_used >= direct_retry_budget
    if base_category == 'fatal_protocol_violation':
        category = base_category
        target_role = 'project_manager'
    elif first_handler == 'responsible_role' and direct_retry_budget_exhausted:
        category = 'pm_repair_decision_required'
        target_role = str(policy_row.get('escalate_to') or 'project_manager')
    else:
        category = base_category
        target_role = router._policy_first_handler_target(policy_row, responsible_role)
    if target_role == 'project_manager' and category == 'control_plane_reissue':
        category = 'pm_repair_decision_required'
    policy = router._control_blocker_policy(category, responsible_role=responsible_role, event=event, policy_row=policy_row, target_role=target_role)
    policy_snapshot_path = router._write_blocker_repair_policy_snapshot(project_root, run_root, run_state)
    index = len(run_state.setdefault('control_blockers', [])) + 1
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    blocker_id = f'control-blocker-{index:04d}-{stamp}'
    artifact_path = run_root / 'control_blocks' / f'{blocker_id}.json'
    artifact_rel = project_relative(project_root, artifact_path)
    repair_packet = router._write_control_blocker_repair_packet(project_root, run_root, run_state, blocker_id=blocker_id, category=category, target_role=policy['target_role'], responsible_role=responsible_role, error_message=error_message, event=event, action_type=action_type, payload=payload, policy_row=policy_row, policy_snapshot_path=policy_snapshot_path, direct_retry_attempts_used=direct_retry_attempts_used, direct_retry_budget_exhausted=direct_retry_budget_exhausted)
    record = {'schema_version': CONTROL_BLOCKER_SCHEMA, 'blocker_id': blocker_id, 'run_id': run_state.get('run_id'), 'created_at': utc_now(), 'source': source, 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'originating_handling_lane': base_category, 'handling_lane': category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'controller_boundary': policy_row.get('controller_boundary'), 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'error_code': router._control_blocker_error_code(error_message), 'controller_visible_summary': 'Router rejected a control-plane payload. Deliver the sealed repair packet to the target role.', 'blocker_artifact_path': artifact_rel, 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'responsible_role_for_reissue': responsible_role if base_category == 'control_plane_reissue' else None, 'target_role': policy['target_role'], 'pm_decision_required': policy['pm_decision_required'], 'controller_instruction': policy['controller_instruction'], 'controller_allowed_actions': policy['controller_allowed_actions'], 'controller_forbidden_actions': policy['controller_forbidden_actions'], 'allowed_resolution_events': policy['allowed_resolution_events'], 'sealed_body_read_by_controller_allowed': False, 'controller_history_is_evidence': False, 'delivery_status': 'pending', 'skill_observation_reminder': router._skill_observation_reminder('Control-plane payload was rejected and a sealed repair packet was issued for the target role.', event=event, action_type=action_type, category=category)}
    write_json(artifact_path, record)
    router._supersede_prior_control_blockers(run_root, blocker_id=blocker_id, category=category, event=event, action_type=action_type, attempt_key=attempt_key)
    active = {'blocker_id': blocker_id, 'handling_lane': category, 'originating_handling_lane': base_category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'blocker_artifact_path': artifact_rel, 'target_role': policy['target_role'], 'responsible_role_for_reissue': record['responsible_role_for_reissue'], 'pm_decision_required': policy['pm_decision_required'], 'delivery_status': 'pending', 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'created_at': record['created_at']}
    run_state['active_control_blocker'] = active
    run_state.setdefault('blocker_repair_attempts', {})[attempt_key] = {'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'originating_event': event, 'originating_action_type': action_type, 'responsible_role': responsible_role, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'latest_blocker_id': blocker_id, 'latest_target_role': policy['target_role'], 'updated_at': record['created_at']}
    run_state['latest_control_blocker_path'] = artifact_rel
    run_state['control_blockers'].append(active)
    run_state['pending_action'] = None
    append_history(run_state, 'router_recorded_control_blocker', {'blocker_id': blocker_id, 'handling_lane': category, 'policy_row_id': policy_row_id, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'target_role': policy['target_role'], 'originating_event': event, 'originating_action_type': action_type})
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    router.save_run_state(run_root, run_state)
    return record

def _control_blocker_record(router: ModuleType, project_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    raw_path = active.get('blocker_artifact_path')
    if not raw_path:
        return active
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return active
    return read_json(path)

def _control_blocker_matches_reconciled_action(router: ModuleType, record: dict[str, Any], *, action_type: str, controller_action_id: str, router_scheduler_row_id: str, postcondition: str, postcondition_satisfied: bool) -> str | None:
    _bind_router(router)
    if record.get('resolution_status'):
        return None
    originating_action_type = str(record.get('originating_action_type') or '')
    if originating_action_type and originating_action_type != action_type:
        return None
    blocker_action_id = str(record.get('originating_controller_action_id') or '')
    if blocker_action_id and controller_action_id and (blocker_action_id == controller_action_id):
        return 'matching_controller_action_id'
    blocker_row_id = str(record.get('originating_router_scheduler_row_id') or '')
    if blocker_row_id and router_scheduler_row_id and (blocker_row_id == router_scheduler_row_id):
        return 'matching_router_scheduler_row_id'
    blocker_postcondition = str(record.get('originating_postcondition') or '')
    if originating_action_type == action_type and blocker_postcondition and postcondition and (blocker_postcondition == postcondition) and postcondition_satisfied:
        return 'matching_postcondition'
    if record.get('source') == 'controller_action_receipt_missing_router_postcondition' and router._boot_action_meta(action_type) is not None and postcondition and postcondition_satisfied:
        return 'startup_bootloader_postcondition_fallback'
    return None

def _supersede_queued_control_blocker_actions(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, resolved_at: str, resolution_status: str) -> int:
    _bind_router(router)
    if not blocker_id:
        return 0
    superseded = 0
    action_dir = _controller_actions_dir(run_root)
    if action_dir.exists():
        for path in sorted(action_dir.glob('*.json')):
            entry = read_json_if_exists(path)
            if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
                continue
            if entry.get('action_type') != 'handle_control_blocker':
                continue
            if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES:
                continue
            action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
            if blocker_id not in {str(entry.get('blocker_id') or ''), str(action.get('blocker_id') or '')}:
                continue
            reconciliation = {'resolution_status': 'superseded_by_resolved_control_blocker', 'source_blocker_resolution_status': resolution_status, 'blocker_id': blocker_id, 'resolved_at': resolved_at}
            _update_controller_action_entry_fields(project_root, run_root, run_state, action_id=str(entry.get('action_id') or ''), status='superseded', fields={'router_reconciliation_status': 'superseded_by_resolved_control_blocker', 'router_reconciled_at': resolved_at, 'router_reconciliation': reconciliation, 'superseded_by_control_blocker_resolution': blocker_id}, router_state='superseded', reconciliation=reconciliation)
            superseded += 1
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') == 'handle_control_blocker':
        if blocker_id == str(pending.get('blocker_id') or ''):
            run_state['pending_action'] = None
            append_history(run_state, 'router_cleared_pending_control_blocker_action_after_resolution', {'blocker_id': blocker_id, 'resolution_status': resolution_status})
    return superseded

def _resolve_control_blockers_for_reconciled_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action: dict[str, Any], entry: dict[str, Any] | None=None, reconciliation: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get('action_type') or (entry or {}).get('action_type') or '')
    if not action_type:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    controller_action_id = str((entry or {}).get('action_id') or action.get('controller_action_id') or '')
    router_scheduler_row_id = str((entry or {}).get('router_scheduler_row_id') or action.get('router_scheduler_row_id') or '')
    postcondition = str(_pending_action_postcondition(action) or (reconciliation or {}).get('bootstrap_postcondition') or (reconciliation or {}).get('postcondition') or '')
    postcondition_satisfied = bool(postcondition and _pending_action_postcondition_satisfied(run_state, postcondition))
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    resolved_ids: list[str] = []
    superseded_actions = 0
    resolved_at = utc_now()
    resolution_status = 'resolved_by_startup_reconciliation' if router._boot_action_meta(action_type) is not None else 'resolved_by_controller_action_reconciliation'
    for path in sorted(control_root.glob('*.json')):
        if path.name.endswith('.sealed_repair_packet.json') or path.name == 'blocker_repair_policy_snapshot.json':
            continue
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        match_reason = router._control_blocker_matches_reconciled_action(record, action_type=action_type, controller_action_id=controller_action_id, router_scheduler_row_id=router_scheduler_row_id, postcondition=postcondition, postcondition_satisfied=postcondition_satisfied)
        if not match_reason:
            continue
        blocker_id = str(record.get('blocker_id') or '')
        record['resolution_status'] = resolution_status
        record['resolution_reason'] = match_reason
        record['resolved_by_controller_action_id'] = controller_action_id or None
        record['resolved_by_router_scheduler_row_id'] = router_scheduler_row_id or None
        record['resolved_postcondition'] = postcondition or None
        record['resolved_at'] = resolved_at
        record['resolution_note'] = 'The originating Controller action/postcondition reconciled before this blocker needed role repair.'
        if reconciliation is not None:
            record['resolved_by_reconciliation'] = _json_safe(reconciliation)
        write_json(path, record)
        resolved_ids.append(blocker_id)
        superseded_actions += router._supersede_queued_control_blocker_actions(project_root, run_root, run_state, blocker_id=blocker_id, resolved_at=resolved_at, resolution_status=resolution_status)
    if not resolved_ids:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    append_history(run_state, 'router_resolved_control_blockers_by_controller_action_reconciliation', {'action_type': action_type, 'controller_action_id': controller_action_id, 'router_scheduler_row_id': router_scheduler_row_id, 'postcondition': postcondition, 'resolved_blocker_ids': resolved_ids, 'superseded_control_blocker_actions': superseded_actions})
    return {'changed': True, 'resolved': len(resolved_ids), 'resolved_blocker_ids': resolved_ids, 'superseded_actions': superseded_actions}

def _control_blocker_summary(router: ModuleType, record: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    fields = ('blocker_id', 'handling_lane', 'originating_handling_lane', 'policy_row_id', 'blocker_family', 'first_handler', 'attempt_key', 'direct_retry_budget', 'direct_retry_attempts_used', 'direct_retry_budget_exhausted', 'escalate_to', 'pm_recovery_options', 'return_policy', 'hard_stop_conditions', 'blocker_repair_policy_snapshot_path', 'blocker_artifact_path', 'target_role', 'responsible_role_for_reissue', 'pm_decision_required', 'delivery_status', 'sealed_repair_packet_path', 'sealed_repair_packet_hash', 'originating_event', 'originating_action_type', 'originating_controller_action_id', 'originating_router_scheduler_row_id', 'originating_postcondition', 'created_at', 'delivered_to_role', 'delivered_at', 'resolution_status', 'resolved_by_event', 'resolved_at', 'pm_repair_decision_status', 'pm_repair_decision_path', 'pm_repair_decision_hash', 'pm_repair_rerun_target', 'pm_recovery_option', 'pm_repair_return_gate', 'repair_origin', 'repair_transaction_id', 'repair_transaction_path', 'repair_outcome_table', 'allowed_resolution_events')
    return {field: record.get(field) for field in fields if field in record}

def _resume_reentry_gate_pending(router: ModuleType, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags', {})
    return bool(flags.get('resume_reentry_requested')) and (not bool(flags.get('pm_resume_recovery_decision_returned')))

def _sync_protocol_blocker_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    blockers: list[dict[str, Any]] = []
    blocker_root = run_root / 'blockers'
    if blocker_root.exists():
        for path in sorted(blocker_root.glob('*.json')):
            record = read_json_if_exists(path)
            blockers.append({'path': project_relative(project_root, path), 'blocker_id': record.get('blocker_id') or path.stem, 'blocker_type': record.get('blocker_type'), 'status': record.get('status'), 'registered_at': record.get('registered_at') or utc_now()})
    run_state['protocol_blockers'] = blockers

def _sync_control_plane_indexes(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    summaries: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    control_root = run_root / 'control_blocks'
    if control_root.exists():
        for path in sorted(control_root.glob('*.json')):
            record = read_json_if_exists(path)
            if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
                continue
            summary = router._control_blocker_summary(record)
            summaries.append(summary)
            if record.get('resolution_status'):
                resolved.append(summary)
            else:
                active = summary
    run_state['control_blockers'] = summaries
    run_state['resolved_control_blockers'] = resolved
    run_state['active_control_blocker'] = active
    run_state['latest_control_blocker_path'] = active.get('blocker_artifact_path') if active else None
    router._sync_protocol_blocker_index(project_root, run_root, run_state)
    router._write_repair_transaction_index(project_root, run_root, run_state)

def _control_blocker_wait_events(router: ModuleType, record: dict[str, Any], *, run_root: Path | None=None, run_state: dict[str, Any] | None=None) -> tuple[list[str], dict[str, Any] | None]:
    _bind_router(router)
    raw_events = record.get('allowed_resolution_events') or sorted(EXTERNAL_EVENTS)
    lane = str(record.get('handling_lane') or '')
    if lane == 'control_plane_reissue':
        _validate_control_transaction_requirements(run_root, transaction_type='control_plane_reissue', producer_role='router', required_event_usages=('wait',), required_commit_targets=('blocker_index', 'run_state', 'status_summary'), require_repair_transaction=False, outcome_policy='single_event')
    issue = router._external_event_validation_issue(raw_events)
    if issue is None:
        repair_origin = str(record.get('repair_origin') or ('control_plane_reissue' if lane == 'control_plane_reissue' else 'none'))
        return (router._validated_event_capability_names(raw_events, context='control blocker wait', run_root=run_root, run_state=run_state, usage='wait', repair_origin=repair_origin), None)
    if lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return ([PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT], {**issue, 'fallback': 'pm_must_resubmit_control_blocker_repair_decision', 'previous_allowed_resolution_events': raw_events})
    raise RouterError(str(issue.get('error') or 'control blocker wait contains invalid allowed external events'))

def _event_producer_roles(router: ModuleType, allowed_events: list[str]) -> set[str]:
    _bind_router(router)
    roles: set[str] = set()
    for event in allowed_events:
        meta = EXTERNAL_EVENTS.get(event) or {}
        roles.add(_event_wait_role(event, meta))
    return roles

def _role_set(router: ModuleType, to_role: str) -> set[str]:
    _bind_router(router)
    return {part.strip() for part in str(to_role or '').split(',') if part.strip()}

def _control_blocker_followup_target_role(router: ModuleType, allowed_events: list[str], fallback_role: str) -> str:
    _bind_router(router)
    roles = router._event_producer_roles(allowed_events)
    if not roles:
        return fallback_role
    fallback_roles = router._role_set(fallback_role)
    if roles.issubset(fallback_roles):
        return fallback_role
    return ','.join(sorted(roles))

def _validate_wait_event_producer_binding(router: ModuleType, allowed_events: list[str], *, to_role: str, context: str) -> None:
    _bind_router(router)
    producer_roles = router._event_producer_roles(allowed_events)
    target_roles = router._role_set(to_role)
    if producer_roles and (not producer_roles.issubset(target_roles)):
        raise RouterError(f'{context} waits for event producer role(s) {sorted(producer_roles)} but targets {sorted(target_roles)}')

def _repair_transaction_for_control_blocker(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    raw_path = record.get('repair_transaction_path')
    if not raw_path:
        return None
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return None
    transaction = read_json_if_exists(path)
    if transaction.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
        return None
    return transaction

def _make_operation_replay_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    replay_source = execution_plan.get('replay_source') if isinstance(execution_plan.get('replay_source'), dict) else {}
    source_action = replay_source.get('source_action') if isinstance(replay_source.get('source_action'), dict) else {}
    action_type = str(execution_plan.get('queued_action_type') or replay_source.get('action_type') or record.get('originating_action_type') or '')
    if action_type not in REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES:
        raise RouterError(f"operation_replay repair transaction cannot queue action_type={action_type or 'missing'}")
    extra = {key: value for key, value in source_action.items() if key not in {'schema_version', 'action_id', 'action_type', 'actor', 'source', 'issued_by', 'label', 'summary', 'allowed_reads', 'allowed_writes', 'created_at'}}
    extra.update({'repair_transaction_id': transaction.get('transaction_id'), 'control_blocker_id': record.get('blocker_id'), 'replay_of_controller_action_id': replay_source.get('controller_action_id'), 'idempotency_key': f"repair-transaction:{transaction.get('transaction_id')}:operation-replay", 'repair_execution_plan': execution_plan})
    action = make_action(action_type=action_type, actor=str(source_action.get('actor') or 'controller'), label=f"controller_replays_{action_type}_for_{record.get('blocker_id')}", summary=f"Replay recorded operation {action_type} for repair transaction {transaction.get('transaction_id')}.", allowed_reads=list(source_action.get('allowed_reads') or [project_relative(project_root, router.run_state_path(run_root))]), allowed_writes=list(source_action.get('allowed_writes') or [project_relative(project_root, router.run_state_path(run_root))]), card_id=source_action.get('card_id'), mail_id=source_action.get('mail_id'), to_role=source_action.get('to_role'), extra=extra)
    return action

def _make_controller_repair_work_packet_action(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return make_action(action_type='controller_repair_work_packet', actor='controller', label=f"controller_executes_repair_work_packet_for_{record.get('blocker_id')}", summary=f"Execute bounded Controller repair work packet for repair transaction {transaction.get('transaction_id')} and report success evidence or a follow-up blocker.", allowed_reads=list(execution_plan.get('allowed_reads') or []), allowed_writes=list(execution_plan.get('allowed_writes') or [project_relative(project_root, router.run_state_path(run_root))]), to_role='controller', extra={'repair_transaction_id': transaction.get('transaction_id'), 'control_blocker_id': record.get('blocker_id'), 'repair_execution_plan': execution_plan, 'forbidden_actions': execution_plan.get('forbidden_actions') or [], 'success_evidence': execution_plan.get('success_evidence') or [], 'sealed_body_reads_allowed': False, 'controller_may_approve_gate': False, 'controller_may_mutate_route': False, 'controller_may_read_sealed_bodies': False, 'idempotency_key': f"repair-transaction:{transaction.get('transaction_id')}:controller-repair-work-packet"})

def _next_repair_transaction_executable_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    transaction = router._repair_transaction_for_control_blocker(project_root, run_root, record)
    if not isinstance(transaction, dict) or transaction.get('status') != 'committed':
        return None
    execution_plan = transaction.get('execution_plan')
    if not isinstance(execution_plan, dict):
        return None
    mode = str(execution_plan.get('mode') or transaction.get('plan_kind') or '')
    if mode == 'operation_replay':
        return router._make_operation_replay_action(project_root, run_root, run_state, record, transaction, execution_plan)
    if mode == 'controller_repair_work_packet':
        return router._make_controller_repair_work_packet_action(project_root, run_root, record, transaction, execution_plan)
    return None

def _next_control_blocker_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict):
        return None
    if router._resume_reentry_gate_pending(run_state) and active.get('originating_action_type') not in {'load_resume_state', 'rehydrate_role_agents'}:
        return None
    record = router._control_blocker_record(project_root, active)
    artifact_rel = str(record.get('blocker_artifact_path') or active.get('blocker_artifact_path') or '')
    if not artifact_rel:
        return None
    lane = str(record.get('handling_lane') or active.get('handling_lane') or 'pm_repair_decision_required')
    target_role = str(record.get('target_role') or active.get('target_role') or 'project_manager')
    allowed_resolution_events, event_contract_issue = router._control_blocker_wait_events(record, run_root=run_root, run_state=run_state)
    target_role = router._control_blocker_followup_target_role(allowed_resolution_events, target_role)
    router._validate_wait_event_producer_binding(allowed_resolution_events, to_role=target_role, context='control blocker wait')
    if record.get('delivery_status') != 'delivered':
        return make_action(action_type='handle_control_blocker', actor='controller', label=f'controller_handles_{lane}_control_blocker', summary=f"Deliver router control blocker {record.get('blocker_id')} sealed repair packet envelope to {target_role}.", allowed_reads=[artifact_rel, project_relative(project_root, router.run_state_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'control_blocks' / 'control_blocker_delivery_ledger.json')], to_role=target_role, extra={'blocker_id': record.get('blocker_id'), 'blocker_artifact_path': artifact_rel, 'policy_row_id': record.get('policy_row_id'), 'blocker_family': record.get('blocker_family'), 'first_handler': record.get('first_handler'), 'direct_retry_budget': record.get('direct_retry_budget'), 'direct_retry_attempts_used': record.get('direct_retry_attempts_used'), 'direct_retry_budget_exhausted': record.get('direct_retry_budget_exhausted'), 'pm_recovery_options': record.get('pm_recovery_options') or [], 'return_policy': record.get('return_policy') or {}, 'hard_stop_conditions': record.get('hard_stop_conditions') or [], 'blocker_repair_policy_snapshot_path': record.get('blocker_repair_policy_snapshot_path'), 'sealed_repair_packet_path': record.get('sealed_repair_packet_path'), 'sealed_repair_packet_hash': record.get('sealed_repair_packet_hash'), 'handling_lane': lane, 'pm_decision_required': bool(record.get('pm_decision_required')), 'responsible_role_for_reissue': record.get('responsible_role_for_reissue'), 'repair_transaction_id': record.get('repair_transaction_id'), 'repair_outcome_table': record.get('repair_outcome_table'), 'controller_instruction': record.get('controller_instruction'), 'controller_allowed_actions': record.get('controller_allowed_actions') or [], 'controller_forbidden_actions': record.get('controller_forbidden_actions') or [], 'sealed_body_reads_allowed': False, 'controller_history_is_evidence': False, 'allowed_resolution_events': allowed_resolution_events, 'event_contract_issue': event_contract_issue, 'repair_details_visibility': 'sealed_to_target_role_not_controller', 'skill_observation_reminder': record.get('skill_observation_reminder')})
    executable_action = router._next_repair_transaction_executable_action(project_root, run_root, run_state, record)
    if executable_action is not None:
        return executable_action
    return make_action(action_type='await_role_decision', actor='controller', label='controller_waits_for_control_blocker_resolution', summary="A router control blocker has been delivered. Controller must wait for the target role's corrected event or PM recovery decision.", allowed_reads=[artifact_rel, project_relative(project_root, router.run_state_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root))], to_role=target_role, extra={'allowed_external_events': allowed_resolution_events, 'blocker_artifact_path': artifact_rel, 'policy_row_id': record.get('policy_row_id'), 'blocker_family': record.get('blocker_family'), 'first_handler': record.get('first_handler'), 'direct_retry_budget': record.get('direct_retry_budget'), 'direct_retry_attempts_used': record.get('direct_retry_attempts_used'), 'direct_retry_budget_exhausted': record.get('direct_retry_budget_exhausted'), 'pm_recovery_options': record.get('pm_recovery_options') or [], 'return_policy': record.get('return_policy') or {}, 'hard_stop_conditions': record.get('hard_stop_conditions') or [], 'target_role': target_role, 'handling_lane': lane, 'repair_transaction_id': record.get('repair_transaction_id'), 'repair_outcome_table': record.get('repair_outcome_table'), 'event_contract_issue': event_contract_issue})

def _mark_control_blocker_delivered(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> None:
    _bind_router(router)
    artifact_rel = str(pending.get('blocker_artifact_path') or '')
    if not artifact_rel:
        raise RouterError('control blocker action is missing blocker_artifact_path')
    artifact_path = resolve_project_path(project_root, artifact_rel)
    record = read_json(artifact_path)
    delivered_at = utc_now()
    target_role = str(pending.get('to_role') or record.get('target_role') or 'project_manager')
    record['delivery_status'] = 'delivered'
    record['delivered_by'] = 'controller'
    record['delivered_to_role'] = target_role
    record['delivered_at'] = delivered_at
    write_json(artifact_path, record)
    active = run_state.get('active_control_blocker')
    if isinstance(active, dict) and active.get('blocker_id') == record.get('blocker_id'):
        active['delivery_status'] = 'delivered'
        active['delivered_to_role'] = target_role
        active['delivered_at'] = delivered_at
    ledger_path = run_root / 'control_blocks' / 'control_blocker_delivery_ledger.json'
    ledger = read_json_if_exists(ledger_path) or {'schema_version': 'flowpilot.control_blocker_delivery_ledger.v1', 'deliveries': []}
    ledger.setdefault('deliveries', []).append({'blocker_id': record.get('blocker_id'), 'blocker_artifact_path': artifact_rel, 'handling_lane': record.get('handling_lane'), 'sealed_repair_packet_path': record.get('sealed_repair_packet_path'), 'sealed_repair_packet_hash': record.get('sealed_repair_packet_hash'), 'delivered_by': 'controller', 'delivered_to_role': target_role, 'delivered_at': delivered_at})
    ledger['updated_at'] = delivered_at
    write_json(ledger_path, ledger)
    router._sync_control_plane_indexes(project_root, run_root, run_state)

__all__ = (
    '_write_control_blocker_repair_packet',
    '_supersede_prior_control_blockers',
    '_nonnegative_int_or_none',
    '_write_control_blocker',
    '_control_blocker_record',
    '_control_blocker_matches_reconciled_action',
    '_supersede_queued_control_blocker_actions',
    '_resolve_control_blockers_for_reconciled_controller_action',
    '_control_blocker_summary',
    '_resume_reentry_gate_pending',
    '_sync_protocol_blocker_index',
    '_sync_control_plane_indexes',
    '_control_blocker_wait_events',
    '_event_producer_roles',
    '_role_set',
    '_control_blocker_followup_target_role',
    '_validate_wait_event_producer_binding',
    '_repair_transaction_for_control_blocker',
    '_make_operation_replay_action',
    '_make_controller_repair_work_packet_action',
    '_next_repair_transaction_executable_action',
    '_next_control_blocker_action',
    '_mark_control_blocker_delivered',
)

_LOCAL_NAMES = set(globals())
