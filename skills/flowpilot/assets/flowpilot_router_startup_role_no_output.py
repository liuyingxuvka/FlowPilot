"""Startup owner helpers extracted from ``flowpilot_router_startup_flow``.

This module is part of the startup StructureMesh split. It is bound to the
router skeleton before execution so cross-owner transitional lookups stay
explicit while startup behavior is owned by smaller modules.
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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_role_recovery'

def _role_no_output_liveness_result(router: ModuleType, payload: dict[str, Any] | None) -> str:
    _bind_router(router)
    payload = payload or {}
    liveness_probe = payload.get('liveness_probe') if isinstance(payload.get('liveness_probe'), dict) else {}
    for key in ('liveness_probe_result', 'host_liveness_status', 'bounded_wait_result', 'result'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = liveness_probe.get('result')
    return value.strip() if isinstance(value, str) else ''

def _payload_indicates_role_no_output(router: ModuleType, payload: dict[str, Any] | None) -> bool:
    _bind_router(router)
    return router._role_no_output_liveness_result(payload) in WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS

def _role_no_output_target_roles(router: ModuleType, payload: dict[str, Any] | None) -> list[str]:
    _bind_router(router)
    payload = payload or {}
    return router._role_recovery_target_roles(payload.get('target_role_keys') or payload.get('role_key') or payload.get('missing_role_key'))

def _role_no_output_wait_candidate(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, target_role_keys: list[str], payload: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    candidates = router._role_recovery_wait_candidates(project_root, run_root, run_state, set(target_role_keys))
    if not candidates:
        return None
    wanted_action_id = str(payload.get('controller_action_id') or payload.get('current_controller_action_id') or '').strip()
    wanted_row_id = str(payload.get('router_scheduler_row_id') or '').strip()
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    pending_action_id = str(pending.get('controller_action_id') or '').strip()
    pending_row_id = str(pending.get('router_scheduler_row_id') or '').strip()
    for candidate in candidates:
        entry = candidate['entry']
        if wanted_action_id and entry.get('action_id') == wanted_action_id:
            return candidate
        if wanted_row_id and entry.get('router_scheduler_row_id') == wanted_row_id:
            return candidate
    for candidate in candidates:
        entry = candidate['entry']
        if pending_action_id and entry.get('action_id') == pending_action_id:
            return candidate
        if pending_row_id and entry.get('router_scheduler_row_id') == pending_row_id:
            return candidate
    return candidates[0]

def _role_no_output_reissue_attempt(router: ModuleType, candidate: dict[str, Any]) -> int:
    _bind_router(router)
    entry = candidate.get('entry') if isinstance(candidate.get('entry'), dict) else {}
    action = candidate.get('action') if isinstance(candidate.get('action'), dict) else {}
    for source in (action, entry):
        raw = source.get('role_no_output_reissue_attempt') or source.get('no_output_reissue_attempt')
        if isinstance(raw, int):
            return max(0, raw)
        if isinstance(raw, str) and raw.isdigit():
            return max(0, int(raw))
    return 0

def _role_no_output_replacement_action(router: ModuleType, candidate: dict[str, Any], *, attempt: int) -> dict[str, Any]:
    _bind_router(router)
    original = candidate['entry']
    action = dict(candidate['action'])
    original_action_id = str(original.get('action_id') or '')
    original_row_id = str(original.get('router_scheduler_row_id') or '')
    base_label = str(action.get('label') or original.get('label') or 'role_no_output_wait')
    if '_no_output_reissue_' in base_label:
        base_label = base_label.split('_no_output_reissue_', 1)[0]
    target_role = str((candidate.get('matched_roles') or [''])[0])
    for key in ('controller_action_id', 'controller_action_path', 'controller_receipt_path', 'router_scheduler_row_id', 'created_at', 'updated_at', 'last_seen_at'):
        action.pop(key, None)
    action['action_type'] = 'await_role_decision'
    action['label'] = f'{base_label}_no_output_reissue_{attempt:03d}'
    action['idempotency_key'] = f'role-no-output-reissue:{original_action_id or original_row_id}:{attempt}'
    action['replaces'] = original_action_id
    action['replaces_controller_action_id'] = original_action_id
    action['replaces_router_scheduler_row_id'] = original_row_id
    action['replacement_reason'] = 'role_no_output_missing_expected_event'
    action['role_no_output_reissue_attempt'] = attempt
    action['max_role_no_output_reissue_attempts'] = ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS
    action['target_no_output_role'] = target_role
    action['summary'] = f'Role {target_role} was reachable or completed but Router still lacks the expected output. This replaces the prior wait with the same authorized work; the role must submit the original output or blocker through the Router-directed runtime path.'
    action['controller_visibility'] = 'metadata_only_no_output_reissue'
    action['sealed_body_reads_allowed'] = False
    action['chat_history_progress_inference_allowed'] = False
    return action

def _supersede_role_no_output_original_wait(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], replacement_entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_path = candidate['action_path']
    entry = read_json_if_exists(action_path)
    if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        entry = dict(candidate['entry'])
    if str(entry.get('status') or '') in {'done', 'resolved'}:
        return entry
    now = utc_now()
    replacement_action_id = replacement_entry.get('action_id')
    entry['status'] = 'superseded'
    entry['superseded_at'] = now
    entry['superseded_by'] = replacement_action_id
    entry['superseded_by_controller_action_id'] = replacement_action_id
    entry['superseded_by_router_scheduler_row_id'] = replacement_entry.get('router_scheduler_row_id')
    entry['replacement_reason'] = replacement_entry.get('replacement_reason')
    entry['completion_source'] = 'role_no_output_reissue'
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='superseded', reconciliation={'source': 'role_no_output_reissue', 'superseded_by': replacement_action_id, 'replacement_reason': replacement_entry.get('replacement_reason'), 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _record_role_no_output_reissue(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, source_event: str) -> dict[str, Any]:
    _bind_router(router)
    payload = dict(payload or {})
    event = 'controller_reports_role_no_output'
    target_role_keys = router._role_no_output_target_roles(payload)
    _reconcile_durable_wait_evidence(project_root, run_root, run_state)
    _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_no_output_reissue_pre_scan')
    candidate = router._role_no_output_wait_candidate(project_root, run_root, run_state, target_role_keys=target_role_keys, payload=payload)
    if candidate is None:
        run_state['flags']['role_no_output_pm_escalation_required'] = True
        blocker = router._write_control_blocker(project_root, run_root, run_state, source='role_no_output_reissue_no_wait_candidate', error_message='Role no-output report could not find the original Router wait to reissue.', event=event, action_type='role_no_output_reissue', payload={**payload, 'target_role_keys': target_role_keys, 'source_event': source_event})
        return {'ok': False, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': False, 'pm_escalation_required': True, 'control_blocker_id': blocker.get('blocker_id')}
    attempt = router._role_no_output_reissue_attempt(candidate) + 1
    if attempt > ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS:
        run_state['flags']['role_no_output_pm_escalation_required'] = True
        blocker = router._write_control_blocker(project_root, run_root, run_state, source='role_no_output_reissue_budget_exhausted', error_message='Role no-output reissue budget exhausted before the expected Router output arrived.', event=event, action_type='role_no_output_reissue', payload={**payload, 'target_role_keys': target_role_keys, 'source_event': source_event, 'direct_retry_attempts_used': ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS, 'direct_retry_budget': ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS})
        return {'ok': False, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': False, 'pm_escalation_required': True, 'control_blocker_id': blocker.get('blocker_id')}
    replacement_action = router._role_no_output_replacement_action(candidate, attempt=attempt)
    replacement_entry = router._write_controller_action_entry(project_root, run_root, run_state, replacement_action)
    router._supersede_role_no_output_original_wait(project_root, run_root, run_state, candidate, replacement_entry)
    run_state['pending_action'] = dict(replacement_entry['action'])
    run_state['flags']['role_no_output_reissue_recorded'] = True
    run_state['flags']['role_no_output_pm_escalation_required'] = False
    record = {'event': event, 'summary': EXTERNAL_EVENTS[event]['summary'], 'payload': payload, 'source_event': source_event, 'target_role_keys': target_role_keys, 'controller_action_id': candidate['entry'].get('action_id'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'replacement_router_scheduler_row_id': replacement_entry.get('router_scheduler_row_id'), 'role_no_output_reissue_attempt': attempt, 'recorded_at': utc_now()}
    run_state['events'].append(record)
    append_history(run_state, 'router_reissued_role_wait_after_no_output', {'source_event': source_event, 'target_role_keys': target_role_keys, 'controller_action_id': candidate['entry'].get('action_id'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'role_no_output_reissue_attempt': attempt, 'role_recovery_requested': False})
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f'after_external_event:{event}')
    router._sync_derived_run_views(project_root, run_root, run_state, reason=f'after_external_event:{event}')
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': True, 'role_no_output_reissue_attempt': attempt, 'replacement_action': replacement_entry.get('action'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'role_recovery_requested': False, 'pm_escalation_required': False}

def _write_role_recovery_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    records, transaction = router._normalize_role_recovery_agent_records(project_root, run_root, run_state, payload)
    environment_blocked = any((record['recovery_result'] == ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT for record in records))
    runtime_roles_path = run_root / 'role_binding_ledger.json'
    role_binding = read_json_if_exists(runtime_roles_path) or {'schema_version': 'flowpilot.role_binding_ledger.v1', 'run_id': run_state['run_id'], 'role_slots': []}
    current_generation = router._current_role_binding_generation(role_binding)
    full_role_binding = any((record['recovery_result'] == ROLE_BINDING_FULL_SET_RECOVERY_RESULT for record in records))
    next_generation = current_generation + 1 if full_role_binding else current_generation
    slots = role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []
    slots_by_role = {str(slot.get('role_key')): dict(slot) for slot in slots if isinstance(slot, dict) and slot.get('role_key') in RUNTIME_ROLE_KEYS}
    for role in RUNTIME_ROLE_KEYS:
        slots_by_role.setdefault(role, {'role_key': role, 'status': 'unknown', 'agent_id': None})
    if not environment_blocked:
        for record in records:
            role = record['role_key']
            old = slots_by_role.get(role, {})
            old_epoch = old.get('role_binding_epoch')
            epoch = int(old_epoch) if isinstance(old_epoch, int) else 0
            superseded = list(old.get('superseded_agent_ids') or []) if isinstance(old.get('superseded_agent_ids'), list) else []
            old_agent_id = record.get('old_agent_id')
            if isinstance(old_agent_id, str) and old_agent_id and (old_agent_id != record.get('agent_id')) and (old_agent_id not in superseded):
                superseded.append(old_agent_id)
            slots_by_role[role] = {**old, 'role_key': role, 'status': 'live_agent_recovered' if not full_role_binding else 'live_agent_recycled', 'agent_id': record['agent_id'], 'model_policy': record['model_policy'], 'reasoning_effort_policy': record['reasoning_effort_policy'], 'host_liveness_status': record.get('host_liveness_status'), 'liveness_decision': record.get('liveness_decision'), 'host_liveness_verified': bool(record.get('host_liveness_verified')), 'role_binding_generation': next_generation, 'role_binding_epoch': epoch + 1, 'last_role_recovery_transaction_id': transaction['transaction_id'], 'last_role_recovery_result': record['recovery_result'], 'superseded_agent_ids': superseded, 'superseded_agent_output_quarantined': bool(record.get('superseded_agent_output_quarantined')), 'memory_seeded_from_current_run': bool(record.get('memory_seeded_from_current_run')), 'replacement_seeded_from_common_run_context': bool(record.get('replacement_seeded_from_common_run_context')), 'recovered_at': record['recorded_at']}
    all_slots = [slots_by_role[role] for role in RUNTIME_ROLE_KEYS]
    required_bindings_ready = not environment_blocked and all((router._role_slot_has_current_host_liveness(slot) for slot in all_slots))
    report_path = router._role_recovery_report_path(run_root)
    proof_state = {'recovery_requested': True, 'replacement_created': any((record.get('recovery_result') in {ROLE_BINDING_TARGETED_REPLACEMENT_RESULT, ROLE_BINDING_FULL_SET_RECOVERY_RESULT} for record in records)), 'memory_seeded': all((record.get('memory_context_injected') for record in records)) if not environment_blocked else False, 'host_liveness_verified': all((record.get('host_liveness_verified') for record in records)) if not environment_blocked else False}
    report = {'schema_version': ROLE_RECOVERY_REPORT_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction['transaction_id'], 'trigger_source': transaction['trigger_source'], 'recovery_scope': payload.get('recovery_scope') or transaction['recovery_scope'], 'target_role_keys': transaction['target_role_keys'], 'recorded_at': utc_now(), 'priority': 'preempt_normal_work', 'normal_work_suspended_until_report': True, 'required_role_bindings_ready': required_bindings_ready, 'environment_blocked': environment_blocked, 'role_binding_generation_before': current_generation, 'role_binding_generation_after': next_generation, 'role_records': records, 'role_recovery_proof_state': proof_state, 'packet_ownership_reconciled': all((record.get('packet_ownership_reconciled') for record in records)) if not environment_blocked else False, 'memory_context_injected': all((record.get('memory_context_injected') for record in records)) if not environment_blocked else False, 'stale_generation_output_quarantined': all((record.get('superseded_agent_output_quarantined') or record.get('recovery_result') == ROLE_BINDING_RESTORE_RESULT for record in records)) if not environment_blocked else False, 'pm_decision_required_before_normal_work': False, 'mechanical_obligation_replay_before_pm': True, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'source_paths': {'transaction': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), 'state_load': project_relative(project_root, router._role_recovery_state_path(run_root)), 'role_binding_ledger': project_relative(project_root, runtime_roles_path), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}}
    write_json(report_path, report)
    history = role_binding.get('role_recovery_history') if isinstance(role_binding.get('role_recovery_history'), list) else []
    history.append({'transaction_id': transaction['transaction_id'], 'report_path': project_relative(project_root, report_path), 'trigger_source': transaction['trigger_source'], 'target_role_keys': transaction['target_role_keys'], 'recovery_scope': report['recovery_scope'], 'required_role_bindings_ready': required_bindings_ready, 'environment_blocked': environment_blocked, 'recorded_at': report['recorded_at']})
    role_binding.update({'schema_version': 'flowpilot.role_binding_ledger.v1', 'run_id': run_state['run_id'], 'role_binding_generation': next_generation, 'role_slots': all_slots, 'latest_role_recovery_report': project_relative(project_root, report_path), 'role_recovery_history': history, 'updated_at': utc_now()})
    write_json(runtime_roles_path, role_binding)
    ready_records = [record for record in records if record['recovery_result'] != ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT]
    if ready_records:
        _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), ready_records, default_lifecycle_phase='role_liveness_recovery', resume_tick_id=str(transaction['transaction_id']), source_action='recover_role_bindings')
    role_binding_recovery_path = run_root / 'continuation' / 'role_binding_recovery_report.json'
    if not environment_blocked:
        write_json(role_binding_recovery_path, {'schema_version': 'flowpilot.role_binding_recovery_report.v1', 'run_id': run_state['run_id'], 'role_recovery_report_path': project_relative(project_root, report_path), 'resume_tick_id': str(transaction['transaction_id']), 'role_binding_mode': 'current_run_role_recovery', 'recorded_at': report['recorded_at'], 'required_role_bindings_ready': required_bindings_ready, 'current_run_memory_complete': bool(report['memory_context_injected']), 'missing_memory_role_keys': [record['role_key'] for record in records if record.get('role_memory_status') != 'available'], 'pm_memory_rehydrated': any((slot.get('role_key') == 'project_manager' and isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) for slot in all_slots)), 'liveness_preflight': {'checked_at': report['recorded_at'], 'probe_mode': ROLE_BINDING_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': str(transaction['transaction_id']), 'all_liveness_probes_started_before_wait': True, 'roles_checked': list(transaction['target_role_keys']), 'replacement_role_keys': [record['role_key'] for record in records if record['recovery_result'] in {ROLE_BINDING_TARGETED_REPLACEMENT_RESULT, ROLE_BINDING_FULL_SET_RECOVERY_RESULT}], 'wait_agent_timeout_treated_as_active': False, 'host_liveness_verified': bool(proof_state['host_liveness_verified']), 'decision': 'roles_ready_after_role_recovery' if required_bindings_ready else 'role_recovery_incomplete_host_liveness'}, 'role_records': records, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False})
    run_state['flags']['role_recovery_roles_restored'] = not environment_blocked
    run_state['flags']['role_recovery_report_written'] = True
    run_state['flags']['role_recovery_environment_blocked'] = environment_blocked
    if environment_blocked:
        router._write_control_blocker(project_root, run_root, run_state, source='role_recovery_environment_blocked', error_message='Role recovery failed after full role binding recycle; environment or user action is required before route work can continue.', action_type='role_recovery_environment_blocked', payload={'role_recovery_report_path': project_relative(project_root, report_path), 'transaction_id': transaction['transaction_id'], 'target_role_keys': transaction['target_role_keys']})
        return
    run_state['flags']['resume_reentry_requested'] = True
    run_state['flags']['resume_state_loaded'] = True
    run_state['flags']['resume_roles_restored'] = True
    run_state['flags']['resume_role_bindings_rehydrated'] = True
    run_state['flags']['role_binding_recovery_report_written'] = True
    replay = router._plan_role_recovery_obligation_replay(project_root, run_root, run_state, transaction=transaction, records=ready_records, report_path=report_path)
    report['role_recovery_obligation_replay_path'] = run_state['role_recovery_obligation_replay']['path']
    report['pm_decision_required_before_normal_work'] = bool(replay.get('pm_escalation_required'))
    report['mechanical_obligation_replay_completed'] = not bool(replay.get('pm_escalation_required'))
    write_json(report_path, report)
    run_state['flags']['pm_resume_recovery_decision_returned'] = not bool(replay.get('pm_escalation_required'))
    run_state['flags']['role_recovery_requested'] = False

__all__ = (
    '_role_no_output_liveness_result',
    '_payload_indicates_role_no_output',
    '_role_no_output_target_roles',
    '_role_no_output_wait_candidate',
    '_role_no_output_reissue_attempt',
    '_role_no_output_replacement_action',
    '_supersede_role_no_output_original_wait',
    '_record_role_no_output_reissue',
    '_write_role_recovery_report',
)

_LOCAL_NAMES = set(globals())
