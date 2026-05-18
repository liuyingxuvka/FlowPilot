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

def _reclaim_role_recovery_postcondition_from_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str) -> dict[str, Any]:
    _bind_router(router)
    context = router._role_recovery_ready_context(project_root, run_root, run_state)
    if context is None:
        return {'applied': False, 'reason': 'role_recovery_report_not_ready', 'postcondition': 'role_recovery_roles_restored'}
    report = context['report']
    flags = run_state.setdefault('flags', {})
    flags['role_recovery_state_loaded'] = True
    flags['role_recovery_roles_restored'] = True
    flags['role_recovery_report_written'] = True
    flags['role_recovery_environment_blocked'] = False
    flags['role_recovery_requested'] = False
    flags['resume_reentry_requested'] = True
    flags['resume_state_loaded'] = True
    flags['resume_roles_restored'] = True
    flags['resume_role_agents_rehydrated'] = True
    flags['crew_rehydration_report_written'] = (run_root / 'continuation' / 'crew_rehydration_report.json').exists()
    pm_required = bool(report.get('pm_decision_required_before_normal_work'))
    replay_path = report.get('role_recovery_obligation_replay_path')
    replay: dict[str, Any] = {}
    if isinstance(replay_path, str) and replay_path.strip():
        replay = read_json_if_exists(resolve_project_path(project_root, replay_path))
    if replay.get('schema_version') == ROLE_RECOVERY_OBLIGATION_REPLAY_SCHEMA:
        pm_required = bool(replay.get('pm_escalation_required'))
        flags['role_recovery_obligations_scanned'] = True
        flags['role_recovery_obligation_replay_completed'] = not pm_required
        flags['role_recovery_pm_escalation_required'] = pm_required
        run_state['role_recovery_obligation_replay'] = {'path': replay_path, 'transaction_id': replay.get('transaction_id') or report.get('transaction_id'), 'replacement_count': replay.get('replacement_count'), 'settled_existing_count': replay.get('settled_existing_count'), 'pm_escalation_required': pm_required}
    elif 'mechanical_obligation_replay_completed' in report:
        flags['role_recovery_obligations_scanned'] = True
        flags['role_recovery_obligation_replay_completed'] = bool(report.get('mechanical_obligation_replay_completed'))
        flags['role_recovery_pm_escalation_required'] = pm_required
    if pm_required:
        flags['pm_resume_recovery_decision_returned'] = bool(flags.get('pm_resume_recovery_decision_returned'))
    else:
        flags['pm_resume_recovery_decision_returned'] = True
    append_history(run_state, 'router_reclaimed_role_recovery_report_postcondition', {'source': source, 'transaction_id': report.get('transaction_id'), 'role_recovery_report_path': context['report_relpath'], 'role_recovery_obligation_replay_path': replay_path if isinstance(replay_path, str) else None, 'pm_decision_required_before_normal_work': pm_required})
    return {'applied': True, 'source': source, 'postcondition': 'role_recovery_roles_restored', 'role_recovery_report_path': context['report_relpath'], 'role_recovery_obligation_replay_path': replay_path if isinstance(replay_path, str) else None, 'pm_decision_required_before_normal_work': pm_required}

def _current_crew_generation(router: ModuleType, crew: dict[str, Any]) -> int:
    _bind_router(router)
    raw = crew.get('crew_generation')
    if isinstance(raw, int) and raw > 0:
        return raw
    generations = [int(slot.get('crew_generation')) for slot in (crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []) if isinstance(slot, dict) and isinstance(slot.get('crew_generation'), int)]
    return max(generations) if generations else 1

def _open_role_recovery_transaction(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger_source: str, recovery_scope: str, target_role_keys: list[str], fault_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    recovery_dir = router._role_recovery_dir(run_root)
    recovery_dir.mkdir(parents=True, exist_ok=True)
    index_path = recovery_dir / 'index.json'
    index = read_json_if_exists(index_path) or {'schema_version': 'flowpilot.role_recovery_index.v1', 'run_id': run_state['run_id'], 'transactions': []}
    sequence = len(index.get('transactions') if isinstance(index.get('transactions'), list) else []) + 1
    transaction_id = f"role-recovery-{run_state['run_id']}-{sequence:03d}"
    active_packet = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    transaction = {'schema_version': ROLE_RECOVERY_TRANSACTION_SCHEMA, 'transaction_id': transaction_id, 'run_id': run_state['run_id'], 'trigger_source': trigger_source, 'recovery_scope': recovery_scope, 'target_role_keys': list(target_role_keys), 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'started_at': utc_now(), 'fault_payload': fault_payload, 'active_packet_context': active_packet, 'recovery_ladder': ['restore_old_agent', 'targeted_replacement', 'slot_reconciliation', 'full_crew_recycle', 'environment_blocked'], 'controller_may_wait_for_normal_work_before_recovery': False, 'controller_may_infer_completion_from_old_agent': False}
    tx_path = recovery_dir / f'{transaction_id}.json'
    write_json(tx_path, transaction)
    write_json(router._role_recovery_latest_transaction_path(run_root), transaction)
    index.setdefault('transactions', []).append({'transaction_id': transaction_id, 'path': project_relative(project_root, tx_path), 'trigger_source': trigger_source, 'recovery_scope': recovery_scope, 'target_role_keys': list(target_role_keys), 'started_at': transaction['started_at'], 'status': 'open'})
    index['latest_transaction_id'] = transaction_id
    index['latest_transaction_path'] = project_relative(project_root, tx_path)
    index['updated_at'] = utc_now()
    write_json(index_path, index)
    run_state['role_recovery'] = {'transaction_id': transaction_id, 'trigger_source': trigger_source, 'recovery_scope': recovery_scope, 'target_role_keys': list(target_role_keys), 'transaction_path': project_relative(project_root, tx_path), 'latest_transaction_path': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root))}
    return transaction

def _role_recovery_payload_contract(router: ModuleType, run_root: Path, run_state: dict[str, Any], transaction: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    target_roles = [str(role) for role in transaction.get('target_role_keys') or []]
    scope = str(transaction.get('recovery_scope') or 'targeted')
    required_fields = ['background_agents_capability_status', 'recovery_transaction_id', 'trigger_source', 'recovery_scope', 'target_role_keys', 'recovered_role_agents[].role_key', 'recovered_role_agents[].agent_id', 'recovered_role_agents[].model_policy', 'recovered_role_agents[].reasoning_effort_policy', 'recovered_role_agents[].recovery_result', 'recovered_role_agents[].restore_attempted', 'recovered_role_agents[].restore_result', 'recovered_role_agents[].rehydrated_for_run_id', 'recovered_role_agents[].memory_context_injected', 'recovered_role_agents[].packet_ownership_reconciled']
    if scope == 'targeted':
        required_fields.extend(['recovered_role_agents[].old_agent_id', 'recovered_role_agents[].role_binding_epoch_advanced', 'recovered_role_agents[].superseded_agent_output_quarantined'])
    return _payload_contract(name='role_liveness_recovery_receipt', required_object='payload', required_fields=required_fields, allowed_values={'background_agents_capability_status': ['available'], 'recovery_transaction_id': [str(transaction.get('transaction_id') or '')], 'trigger_source': [str(transaction.get('trigger_source') or '')], 'recovery_scope': [scope, 'full_crew'], 'target_role_keys': [target_roles], 'recovered_role_agents[].role_key': list(CREW_ROLE_KEYS), 'recovered_role_agents[].model_policy': [BACKGROUND_ROLE_MODEL_POLICY], 'recovered_role_agents[].reasoning_effort_policy': [BACKGROUND_ROLE_REASONING_EFFORT_POLICY], 'recovered_role_agents[].recovery_result': sorted(ROLE_RECOVERY_RESULTS), 'recovered_role_agents[].rehydrated_for_run_id': [run_state['run_id']], 'recovered_role_agents[].memory_context_injected': [True], 'recovered_role_agents[].packet_ownership_reconciled': [True]}, structural_requirements=['Recovery must be recorded before any normal route, packet, gate, or control-blocker work resumes.', 'For targeted recovery, attempt old-agent restore before replacement.', 'If old close fails and targeted spawn reports capacity_full, slot reconciliation and full crew recycle must be attempted before any success report.', 'A failed full crew recycle must return recovery_result=environment_blocked and must not mark the crew ready.', 'Recovered or replacement roles must receive current-run memory/context before being marked usable.', 'Late output from superseded agent ids must be quarantined and cannot count as packet or gate progress.', 'Packet ownership must be reconciled before PM is asked to continue.'], description='Record the host recovery attempt ladder for a missing or unhealthy FlowPilot role.', reviewer_check='PM checks this role recovery report before deciding whether to resume, re-dispatch, or escalate.')

def _load_role_recovery_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery state load requires an open role recovery transaction')
    loaded_paths = {'role_recovery_transaction': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), 'router_state': project_relative(project_root, router.run_state_path(run_root)), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'crew_memory': project_relative(project_root, run_root / 'crew_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}
    missing_paths = [rel for rel in loaded_paths.values() if not resolve_project_path(project_root, rel).exists()]
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    record = {'schema_version': 'flowpilot.role_recovery_state_load.v1', 'run_id': run_state['run_id'], 'transaction_id': transaction['transaction_id'], 'trigger_source': transaction['trigger_source'], 'recovery_scope': transaction['recovery_scope'], 'target_role_keys': transaction['target_role_keys'], 'loaded_at': utc_now(), 'loaded_paths': loaded_paths, 'missing_paths': missing_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False}
    write_json(router._role_recovery_state_path(run_root), record)
    resume_reentry_path = run_root / 'continuation' / 'resume_reentry.json'
    if not resume_reentry_path.exists():
        write_json(resume_reentry_path, {'schema_version': 'flowpilot.resume_reentry.v1', 'run_id': run_state['run_id'], 'stable_launcher': True, 'controller_only': True, 'wake_recorded_to_router': True, 'role_recovery_triggered': True, 'role_recovery_transaction_id': transaction['transaction_id'], 'visible_plan_restore_required': True, 'visible_plan_restored_from_run': True, 'role_rehydration_required': True, 'roles_restored_or_replaced': False, 'ambiguous_state_blocks_controller_execution': bool(missing_paths), 'missing_paths': missing_paths, 'loaded_paths': loaded_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False, 'recorded_at': record['loaded_at']})
    run_state['flags']['role_recovery_state_loaded'] = True
    return record

def _normalize_role_recovery_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _bind_router(router)
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('role recovery requires background_agents_capability_status=available')
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery requires an open role recovery transaction')
    if payload.get('recovery_transaction_id') != transaction.get('transaction_id'):
        raise RouterError('role recovery transaction id mismatch')
    trigger_source = str(transaction.get('trigger_source') or '')
    if payload.get('trigger_source') != trigger_source:
        raise RouterError('role recovery trigger_source mismatch')
    requested_scope = str(transaction.get('recovery_scope') or 'targeted')
    payload_scope = str(payload.get('recovery_scope') or requested_scope)
    if payload_scope not in {requested_scope, 'full_crew'}:
        raise RouterError('role recovery scope mismatch')
    target_roles = [str(role) for role in transaction.get('target_role_keys') or []]
    payload_targets = payload.get('target_role_keys')
    if payload_targets != target_roles:
        raise RouterError('role recovery target_role_keys mismatch')
    raw_records = payload.get('recovered_role_agents') or payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('role recovery requires payload.recovered_role_agents list or object')
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    existing_by_role = {str(slot.get('role_key')): slot for slot in slots if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    full_crew = payload_scope == 'full_crew' or any((isinstance(raw, dict) and raw.get('recovery_result') == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT for raw in iterable))
    expected_roles = list(CREW_ROLE_KEYS) if full_crew else target_roles
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    records_by_role: dict[str, dict[str, Any]] = {}
    environment_blocked = False
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each recovered role agent record must be an object')
        role = str(raw.get('role_key') or '')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'role recovery record has unsupported role_key: {role!r}')
        if role not in expected_roles:
            raise RouterError(f'role recovery record {role} is outside the expected recovery scope')
        if role in records_by_role:
            raise RouterError(f'duplicate role recovery record for {role}')
        result = str(raw.get('recovery_result') or '')
        if result not in ROLE_RECOVERY_RESULTS:
            raise RouterError(f'{role} requires supported recovery_result')
        restore_attempted = raw.get('restore_attempted') is True
        restore_result = str(raw.get('restore_result') or 'unknown')
        targeted_attempted = raw.get('targeted_replacement_attempted') is True
        targeted_result = str(raw.get('targeted_replacement_result') or 'not_attempted')
        old_close_failed = raw.get('old_close_failed') is True
        spawn_capacity_full = raw.get('spawn_capacity_full') is True or targeted_result == 'capacity_full'
        slot_reconciliation_attempted = raw.get('slot_reconciliation_attempted') is True
        full_recycle_attempted = raw.get('full_crew_recycle_attempted') is True
        full_recycle_result = str(raw.get('full_crew_recycle_result') or 'not_attempted')
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            agent_id = raw.get('agent_id')
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RouterError(f'{role} requires a recovered live agent_id')
            if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
                raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
            if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
                raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
            if raw.get('rehydrated_for_run_id') != run_state['run_id']:
                raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
            if raw.get('memory_context_injected') is not True:
                raise RouterError(f'{role} recovery requires memory_context_injected=true')
            if raw.get('packet_ownership_reconciled') is not True:
                raise RouterError(f'{role} recovery requires packet_ownership_reconciled=true')
            if raw.get('role_binding_epoch_advanced') is not True:
                raise RouterError(f'{role} recovery requires role_binding_epoch_advanced=true')
        else:
            environment_blocked = True
            agent_id = None
        if result == ROLE_AGENT_OLD_RESTORE_RESULT:
            if not restore_attempted or restore_result != 'success':
                raise RouterError(f'{role} old-agent restore result requires restore_attempted=true and restore_result=success')
        elif result == ROLE_AGENT_TARGETED_REPLACEMENT_RESULT:
            if not restore_attempted or restore_result != 'failed':
                raise RouterError(f'{role} targeted replacement requires failed restore first')
            if not targeted_attempted or targeted_result != 'success':
                raise RouterError(f'{role} targeted replacement requires targeted_replacement_attempted=true and targeted_replacement_result=success')
        elif result == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT:
            if requested_scope == 'targeted' and (not (restore_attempted and restore_result == 'failed' and targeted_attempted and (targeted_result in {'failed', 'capacity_full'}) and slot_reconciliation_attempted)):
                raise RouterError(f'{role} full crew recycle requires targeted restore/replacement/slot reconciliation escalation')
            if not full_recycle_attempted or full_recycle_result != 'success':
                raise RouterError(f'{role} full crew recycle requires full_crew_recycle_attempted=true and full_crew_recycle_result=success')
        elif result == ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if not full_recycle_attempted or full_recycle_result != 'failed':
                raise RouterError(f'{role} environment_blocked requires failed full crew recycle')
        if old_close_failed and spawn_capacity_full and (not full_recycle_attempted):
            raise RouterError(f'{role} capacity/full-slot conflict requires full crew recycle escalation')
        if result in {ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, ROLE_AGENT_FULL_CREW_RECYCLE_RESULT}:
            if raw.get('superseded_agent_output_quarantined') is not True:
                raise RouterError(f'{role} replacement/recycle requires superseded_agent_output_quarantined=true')
        context = contexts[role]
        memory_status = context['role_memory_status']
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run memory')
        elif result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        old_slot = existing_by_role.get(role) or {}
        old_agent_id = raw.get('old_agent_id') or old_slot.get('agent_id')
        records_by_role[role] = {'role_key': role, 'old_agent_id': old_agent_id, 'agent_id': agent_id, 'model_policy': BACKGROUND_ROLE_MODEL_POLICY if agent_id else None, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY if agent_id else None, 'recovery_result': result, 'restore_attempted': restore_attempted, 'restore_result': restore_result, 'targeted_replacement_attempted': targeted_attempted, 'targeted_replacement_result': targeted_result, 'old_close_failed': old_close_failed, 'spawn_capacity_full': spawn_capacity_full, 'slot_reconciliation_attempted': slot_reconciliation_attempted, 'full_crew_recycle_attempted': full_recycle_attempted, 'full_crew_recycle_result': full_recycle_result, 'rehydrated_for_run_id': run_state['run_id'], 'memory_context_injected': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'packet_ownership_reconciled': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'role_binding_epoch_advanced': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'superseded_agent_output_quarantined': bool(raw.get('superseded_agent_output_quarantined')), 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available', 'replacement_seeded_from_common_run_context': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status != 'available', 'recorded_at': utc_now()}
    missing = [role for role in expected_roles if role not in records_by_role]
    if missing:
        raise RouterError(f"missing role recovery records: {', '.join(missing)}")
    if environment_blocked and any((record['recovery_result'] != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT for record in records_by_role.values())):
        raise RouterError('environment-blocked role recovery report cannot mix ready and blocked role records')
    return ([records_by_role[role] for role in expected_roles], transaction)

def _role_recovery_obligation_replay_path(router: ModuleType, run_root: Path, transaction_id: str) -> Path:
    _bind_router(router)
    safe_transaction = _safe_delivery_component(transaction_id or 'role-recovery')
    return router._role_recovery_dir(run_root) / f'{safe_transaction}_obligation_replay.json'

def _controller_action_entry_view(router: ModuleType, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
    if action:
        return dict(action)
    return {key: entry.get(key) for key in ('action_type', 'label', 'summary', 'to_role', 'allowed_reads', 'allowed_writes', 'allowed_external_events', 'expected_return_path', 'card_envelope_path', 'card_bundle_envelope_path', 'card_return_event', 'card_id', 'card_bundle_id') if entry.get(key) not in (None, '', [])}

def _controller_action_wait_roles(router: ModuleType, entry: dict[str, Any]) -> set[str]:
    _bind_router(router)
    action = router._controller_action_entry_view(entry)
    roles = {str(value).strip() for value in (entry.get('to_role'), entry.get('target_role'), entry.get('waiting_for_role'), action.get('to_role'), action.get('target_role'), action.get('waiting_for_role')) if isinstance(value, str) and value.strip()}
    if str(entry.get('action_type') or action.get('action_type') or '') == 'await_role_decision':
        for event in _controller_wait_allowed_external_events(entry):
            meta = EXTERNAL_EVENTS.get(event)
            if isinstance(meta, dict):
                role = _event_wait_role(event, meta)
                if role:
                    roles.add(role)
    return roles

def _role_recovery_action_sort_key(router: ModuleType, entry: dict[str, Any]) -> tuple[str, str, str]:
    _bind_router(router)
    return (str(entry.get('created_at') or ''), str(entry.get('router_scheduler_row_id') or ''), str(entry.get('action_id') or ''))

def _role_recovery_pending_return_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    for record in _pending_return_records(run_root, run_id):
        if _pending_action_matches_card_return(action, record):
            return record
    return None

def _role_recovery_wait_candidates(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], target_roles: set[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    del project_root
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return []
    candidates: list[dict[str, Any]] = []
    run_id = str(run_state['run_id'])
    for action_path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(action_path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if str(entry.get('status') or '') in CONTROLLER_ACTION_CLOSED_STATUSES:
            continue
        action = router._controller_action_entry_view(entry)
        action_type = str(entry.get('action_type') or action.get('action_type') or '')
        if action_type not in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event', 'await_role_decision'}:
            continue
        wait_roles = router._controller_action_wait_roles(entry)
        matched_roles = sorted(wait_roles.intersection(target_roles))
        if not matched_roles:
            continue
        pending_return = None
        replay_kind = 'role_output'
        if action_type in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event'}:
            replay_kind = 'card_ack'
            pending_return = router._role_recovery_pending_return_for_action(run_root, run_id, action)
        candidates.append({'entry': entry, 'action': action, 'action_path': action_path, 'kind': replay_kind, 'matched_roles': matched_roles, 'pending_return': pending_return, 'sort_key': router._role_recovery_action_sort_key(entry)})
    candidates.sort(key=lambda item: item['sort_key'])
    return candidates

def _mark_controller_action_done_by_role_recovery(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], *, evidence: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_path = candidate['action_path']
    entry = read_json_if_exists(action_path)
    if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        entry = dict(candidate['entry'])
    now = utc_now()
    entry['status'] = 'done'
    entry['completed_at'] = now
    entry['completion_source'] = 'role_recovery_obligation_replay'
    entry['router_reconciliation_status'] = 'reconciled'
    entry['router_reconciled_at'] = now
    entry['satisfied_by_existing_recovery_evidence'] = evidence
    entry['controller_receipt_required'] = False
    entry['router_must_not_mark_done_without_controller_receipt'] = False
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation={'source': 'role_recovery_obligation_replay', 'evidence': evidence, 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _role_recovery_existing_event_for_wait(router: ModuleType, run_state: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    allowed_events = set(_controller_wait_allowed_external_events(entry))
    if not allowed_events:
        return None
    for record in run_state.get('events') or []:
        if isinstance(record, dict) and record.get('event') in allowed_events:
            return record
    return None

def _settle_role_recovery_candidate_if_evidence_exists(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    action = dict(candidate['action'])
    if candidate['kind'] == 'card_ack':
        pending_return = candidate.get('pending_return')
        if isinstance(pending_return, dict):
            pending = dict(pending_return)
            pending.update({key: value for key, value in action.items() if value not in (None, '', [])})
        else:
            pending = action
        expected_return_path = str(pending.get('expected_return_path') or '')
        if not expected_return_path or not resolve_project_path(project_root, expected_return_path).exists():
            return None
        result = _try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, pending)
        if not result.get('consumed'):
            return None
        _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_recovery_obligation_replay')
        evidence = {'kind': 'existing_card_ack', 'expected_return_path': expected_return_path, 'validation': result.get('result')}
        router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
        return {'outcome': 'settled_existing_ack', 'evidence': evidence}
    event_record = router._role_recovery_existing_event_for_wait(run_state, candidate['entry'])
    if event_record is None:
        return None
    closure = _close_waiting_controller_actions_for_external_event(project_root, run_root, run_state, event=str(event_record.get('event') or ''), payload=event_record.get('payload') if isinstance(event_record.get('payload'), dict) else {}, source='role_recovery_obligation_replay')
    evidence = {'kind': 'existing_role_output_event', 'event': event_record.get('event'), 'recorded_at': event_record.get('recorded_at'), 'wait_closure': closure}
    router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
    return {'outcome': 'settled_existing_output', 'evidence': evidence}

def _role_recovery_replacement_action(router: ModuleType, transaction: dict[str, Any], candidate: dict[str, Any], *, original_order: int) -> dict[str, Any]:
    _bind_router(router)
    original = candidate['entry']
    action = dict(candidate['action'])
    original_action_id = str(original.get('action_id') or '')
    original_row_id = str(original.get('router_scheduler_row_id') or '')
    base_label = str(action.get('label') or original.get('label') or 'role_recovery_wait')
    transaction_id = str(transaction.get('transaction_id') or '')
    replay_kind = str(candidate['kind'])
    target_role = str((candidate.get('matched_roles') or [''])[0])
    if replay_kind == 'card_ack':
        if str(action.get('action_type') or original.get('action_type') or '') in {'await_card_bundle_return_event', 'check_card_bundle_return_event'}:
            action['action_type'] = 'await_card_bundle_return_event'
        else:
            action['action_type'] = 'await_card_return_event'
        replacement_reason = 'role_recovered_missing_or_invalid_ack'
        action['summary'] = f'Role {target_role} was mechanically recovered. This replaces the original ACK wait; the role must ACK the original committed card or bundle from current-run memory.'
    else:
        action['action_type'] = 'await_role_decision'
        replacement_reason = 'role_recovered_missing_or_invalid_output'
        action['summary'] = f'Role {target_role} was mechanically recovered. This replaces the original role-output wait; the role must return the original authorized output contract from current-run memory.'
    for key in ('controller_action_id', 'controller_action_path', 'controller_receipt_path', 'router_scheduler_row_id', 'created_at', 'updated_at', 'last_seen_at'):
        action.pop(key, None)
    action['label'] = f'{base_label}_role_recovery_replay_{original_order:03d}'
    action['idempotency_key'] = f'role-recovery-replay:{transaction_id}:{original_action_id or original_row_id}:{original_order}'
    action['replaces'] = original_action_id
    action['replaces_controller_action_id'] = original_action_id
    action['replaces_router_scheduler_row_id'] = original_row_id
    action['replacement_reason'] = replacement_reason
    action['original_order'] = original_order
    action['role_recovery_transaction_id'] = transaction_id
    action['role_recovery_replay_kind'] = replay_kind
    action['target_recovered_role'] = target_role
    action['controller_visibility'] = 'metadata_only_recovery_replay'
    action['sealed_body_reads_allowed'] = False
    action['chat_history_progress_inference_allowed'] = False
    return action

def _supersede_role_recovery_original_wait(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], replacement_entry: dict[str, Any], *, original_order: int) -> dict[str, Any]:
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
    entry['role_recovery_transaction_id'] = replacement_entry.get('role_recovery_transaction_id')
    entry['original_order'] = original_order
    entry['completion_source'] = 'role_recovery_obligation_replay'
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='superseded', reconciliation={'source': 'role_recovery_obligation_replay', 'superseded_by': replacement_action_id, 'replacement_reason': replacement_entry.get('replacement_reason'), 'original_order': original_order, 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _plan_role_recovery_obligation_replay(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction: dict[str, Any], records: list[dict[str, Any]], report_path: Path) -> dict[str, Any]:
    _bind_router(router)
    target_roles = {str(record.get('role_key') or '') for record in records if record.get('recovery_result') != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT}
    target_roles.discard('')
    _reconcile_durable_wait_evidence(project_root, run_root, run_state)
    _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_recovery_obligation_replay_pre_scan')
    candidates = router._role_recovery_wait_candidates(project_root, run_root, run_state, target_roles)
    outcomes: list[dict[str, Any]] = []
    replacement_entries: list[dict[str, Any]] = []
    first_replacement_action: dict[str, Any] | None = None
    for original_order, candidate in enumerate(candidates, start=1):
        settled = router._settle_role_recovery_candidate_if_evidence_exists(project_root, run_root, run_state, candidate)
        if settled is not None:
            outcomes.append({'original_order': original_order, 'controller_action_id': candidate['entry'].get('action_id'), 'kind': candidate['kind'], **settled})
            continue
        replacement_action = router._role_recovery_replacement_action(transaction, candidate, original_order=original_order)
        replacement_entry = router._write_controller_action_entry(project_root, run_root, run_state, replacement_action)
        for field in ('replaces', 'replaces_controller_action_id', 'replaces_router_scheduler_row_id', 'replacement_reason', 'original_order', 'role_recovery_transaction_id', 'role_recovery_replay_kind', 'target_recovered_role'):
            if replacement_action.get(field) not in (None, '', []):
                replacement_entry[field] = replacement_action.get(field)
        write_json(_controller_action_path(run_root, str(replacement_entry['action_id'])), replacement_entry)
        router._supersede_role_recovery_original_wait(project_root, run_root, run_state, candidate, replacement_entry, original_order=original_order)
        if first_replacement_action is None and isinstance(replacement_entry.get('action'), dict):
            first_replacement_action = dict(replacement_entry['action'])
        replacement_entries.append(replacement_entry)
        outcomes.append({'original_order': original_order, 'controller_action_id': candidate['entry'].get('action_id'), 'kind': candidate['kind'], 'outcome': 'replacement_obligation_created', 'replacement_controller_action_id': replacement_entry.get('action_id'), 'replacement_router_scheduler_row_id': replacement_entry.get('router_scheduler_row_id'), 'replacement_reason': replacement_entry.get('replacement_reason')})
    if first_replacement_action is not None:
        run_state['_pending_action_after_current_apply'] = first_replacement_action
    replay = {'schema_version': ROLE_RECOVERY_OBLIGATION_REPLAY_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction.get('transaction_id'), 'role_recovery_report_path': project_relative(project_root, report_path), 'target_role_keys': sorted(target_roles), 'scanned_at': utc_now(), 'candidate_count': len(candidates), 'outcomes': outcomes, 'replacement_count': len(replacement_entries), 'settled_existing_count': len([item for item in outcomes if str(item.get('outcome') or '').startswith('settled_existing')]), 'pm_escalation_required': False, 'pm_escalation_reasons': [], 'controller_visibility': 'metadata_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'replacement_order': [{'original_order': entry.get('original_order'), 'replacement_controller_action_id': entry.get('action_id'), 'replaces_controller_action_id': entry.get('replaces_controller_action_id')} for entry in replacement_entries]}
    replay_path = router._role_recovery_obligation_replay_path(run_root, str(transaction.get('transaction_id') or ''))
    write_json(replay_path, replay)
    run_state['role_recovery_obligation_replay'] = {'path': project_relative(project_root, replay_path), 'transaction_id': transaction.get('transaction_id'), 'replacement_count': replay['replacement_count'], 'settled_existing_count': replay['settled_existing_count'], 'pm_escalation_required': False}
    run_state['flags']['role_recovery_obligations_scanned'] = True
    run_state['flags']['role_recovery_obligation_replay_completed'] = True
    run_state['flags']['role_recovery_pm_escalation_required'] = False
    append_history(run_state, 'router_planned_role_recovery_obligation_replay', {'transaction_id': transaction.get('transaction_id'), 'target_role_keys': sorted(target_roles), 'candidate_count': len(candidates), 'replacement_count': replay['replacement_count'], 'settled_existing_count': replay['settled_existing_count'], 'replay_path': project_relative(project_root, replay_path)})
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    return replay

__all__ = (
    '_reclaim_role_recovery_postcondition_from_report',
    '_current_crew_generation',
    '_open_role_recovery_transaction',
    '_role_recovery_payload_contract',
    '_load_role_recovery_state',
    '_normalize_role_recovery_agent_records',
    '_role_recovery_obligation_replay_path',
    '_controller_action_entry_view',
    '_controller_action_wait_roles',
    '_role_recovery_action_sort_key',
    '_role_recovery_pending_return_for_action',
    '_role_recovery_wait_candidates',
    '_mark_controller_action_done_by_role_recovery',
    '_role_recovery_existing_event_for_wait',
    '_settle_role_recovery_candidate_if_evidence_exists',
    '_role_recovery_replacement_action',
    '_supersede_role_recovery_original_wait',
    '_plan_role_recovery_obligation_replay',
)

_LOCAL_NAMES = set(globals())
