"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints stay aligned.
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
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
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

def _control_blocker_family_key(router: ModuleType, *, attempt_key: str, error_code: str, postcondition: str | None) -> str:
    _bind_router(router)
    return "||".join([attempt_key, error_code, postcondition or ""])

def _existing_control_blocker_family_record(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    family_key: str,
    attempt_key: str,
    allow_active_reuse: bool=True,
) -> dict[str, Any] | None:
    _bind_router(router)
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return None
    terminal_statuses = {'repair_transaction_terminal_stop', 'superseded_by_terminal_lifecycle'}
    matching: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(control_root.glob('*.json')):
        if path.name.endswith('.sealed_repair_packet.json') or path.name == 'blocker_repair_policy_snapshot.json':
            continue
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        record_had_family_identity = bool(record.get('family_key') or record.get('error_code') or record.get('originating_postcondition'))
        record_family_key = str(record.get('family_key') or '')
        if not record_family_key:
            record_family_key = router._control_blocker_family_key(
                attempt_key=str(record.get('attempt_key') or ''),
                error_code=str(record.get('error_code') or ''),
                postcondition=str(record.get('originating_postcondition') or '') or None,
            )
        if record_family_key != family_key and (record_had_family_identity or str(record.get('attempt_key') or '') != attempt_key):
            continue
        matching.append((path, record))
    for path, record in reversed(matching):
        status = str(record.get('resolution_status') or '')
        if status in terminal_statuses:
            record['family_key'] = record.get('family_key') or family_key
            record['same_family_terminal_reused_at'] = utc_now()
            record['same_family_reuse_count'] = int(record.get('same_family_reuse_count') or 0) + 1
            write_json(path, record)
            return {'reuse_kind': 'terminal_same_family', 'path': path, 'record': record}
    if allow_active_reuse:
        for path, record in reversed(matching):
            if record.get('resolution_status'):
                continue
            pm_lane = record.get('handling_lane') == 'pm_repair_decision_required' or record.get('target_role') == 'project_manager' or record.get('pm_decision_required') is True
            still_pending_delivery = record.get('delivery_status') == 'pending'
            pm_repair_recorded = record.get('pm_repair_decision_status') == 'recorded'
            if not (pm_lane or still_pending_delivery or pm_repair_recorded):
                continue
            record['family_key'] = record.get('family_key') or family_key
            record['same_family_reused_at'] = utc_now()
            record['same_family_reuse_count'] = int(record.get('same_family_reuse_count') or 0) + 1
            write_json(path, record)
            return {'reuse_kind': 'active_same_family', 'path': path, 'record': record}
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
    error_code = router._control_blocker_error_code(error_message)
    family_key = router._control_blocker_family_key(attempt_key=attempt_key, error_code=error_code, postcondition=origin_postcondition)
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
    reusable = router._existing_control_blocker_family_record(
        project_root,
        run_root,
        run_state,
        family_key=family_key,
        attempt_key=attempt_key,
        allow_active_reuse=base_category != 'control_plane_reissue',
    )
    if reusable is not None:
        record = dict(reusable['record'])
        reuse_kind = str(reusable.get('reuse_kind') or '')
        if reuse_kind == 'terminal_same_family':
            run_state.setdefault('control_blocker_family_terminal_dispositions', {})[family_key] = {
                'blocker_id': record.get('blocker_id'),
                'resolution_status': record.get('resolution_status'),
                'attempt_key': attempt_key,
                'family_key': family_key,
                'preserved_at': utc_now(),
            }
            if record.get('pm_recovery_option') == 'protocol_dead_end':
                run_state['status'] = 'protocol_dead_end'
                flags = run_state.setdefault('flags', {})
                flags['control_blocker_protocol_dead_end_declared'] = True
                flags['control_blocker_terminal_stop_declared'] = True
        else:
            run_state['active_control_blocker'] = router._control_blocker_summary(record)
            run_state['latest_control_blocker_path'] = record.get('blocker_artifact_path')
        append_history(run_state, 'router_reused_control_blocker_family', {'reuse_kind': reuse_kind, 'blocker_id': record.get('blocker_id'), 'attempt_key': attempt_key, 'family_key': family_key, 'source': source, 'originating_event': event, 'originating_action_type': action_type})
        router._sync_control_plane_indexes(project_root, run_root, run_state)
        router.save_run_state(run_root, run_state)
        return record
    policy_snapshot_path = router._write_blocker_repair_policy_snapshot(project_root, run_root, run_state)
    index = len(run_state.setdefault('control_blockers', [])) + 1
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    blocker_id = f'control-blocker-{index:04d}-{stamp}'
    artifact_path = run_root / 'control_blocks' / f'{blocker_id}.json'
    artifact_rel = project_relative(project_root, artifact_path)
    repair_packet = router._write_control_blocker_repair_packet(project_root, run_root, run_state, blocker_id=blocker_id, category=category, target_role=policy['target_role'], responsible_role=responsible_role, error_message=error_message, event=event, action_type=action_type, payload=payload, policy_row=policy_row, policy_snapshot_path=policy_snapshot_path, direct_retry_attempts_used=direct_retry_attempts_used, direct_retry_budget_exhausted=direct_retry_budget_exhausted)
    record = {'schema_version': CONTROL_BLOCKER_SCHEMA, 'blocker_id': blocker_id, 'run_id': run_state.get('run_id'), 'created_at': utc_now(), 'source': source, 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'originating_handling_lane': base_category, 'handling_lane': category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'family_key': family_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'controller_boundary': policy_row.get('controller_boundary'), 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'error_code': error_code, 'controller_visible_summary': 'Router rejected a control-plane payload. Deliver the sealed repair packet to the target role.', 'blocker_artifact_path': artifact_rel, 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'responsible_role_for_reissue': responsible_role if base_category == 'control_plane_reissue' else None, 'target_role': policy['target_role'], 'pm_decision_required': policy['pm_decision_required'], 'controller_instruction': policy['controller_instruction'], 'controller_allowed_actions': policy['controller_allowed_actions'], 'controller_forbidden_actions': policy['controller_forbidden_actions'], 'allowed_resolution_events': policy['allowed_resolution_events'], 'sealed_body_read_by_controller_allowed': False, 'controller_history_is_evidence': False, 'delivery_status': 'pending', 'skill_observation_reminder': router._skill_observation_reminder('Control-plane payload was rejected and a sealed repair packet was issued for the target role.', event=event, action_type=action_type, category=category)}
    write_json(artifact_path, record)
    router._supersede_prior_control_blockers(run_root, blocker_id=blocker_id, category=category, event=event, action_type=action_type, attempt_key=attempt_key)
    active = {'blocker_id': blocker_id, 'handling_lane': category, 'originating_handling_lane': base_category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'family_key': family_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'blocker_artifact_path': artifact_rel, 'target_role': policy['target_role'], 'responsible_role_for_reissue': record['responsible_role_for_reissue'], 'pm_decision_required': policy['pm_decision_required'], 'delivery_status': 'pending', 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'created_at': record['created_at']}
    run_state['active_control_blocker'] = active
    run_state.setdefault('blocker_repair_attempts', {})[attempt_key] = {'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'originating_event': event, 'originating_action_type': action_type, 'responsible_role': responsible_role, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'latest_blocker_id': blocker_id, 'latest_target_role': policy['target_role'], 'updated_at': record['created_at']}
    run_state['latest_control_blocker_path'] = artifact_rel
    run_state['control_blockers'].append(active)
    run_state['pending_action'] = None
    append_history(run_state, 'router_recorded_control_blocker', {'blocker_id': blocker_id, 'handling_lane': category, 'policy_row_id': policy_row_id, 'attempt_key': attempt_key, 'family_key': family_key, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'target_role': policy['target_role'], 'originating_event': event, 'originating_action_type': action_type})
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
        return 'startup_bootloader_postcondition_repair'
    return None

__all__ = (
    '_write_control_blocker_repair_packet',
    '_supersede_prior_control_blockers',
    '_nonnegative_int_or_none',
    '_control_blocker_family_key',
    '_existing_control_blocker_family_record',
    '_write_control_blocker',
    '_control_blocker_record',
    '_control_blocker_matches_reconciled_action',
)

_LOCAL_NAMES = set(globals())
