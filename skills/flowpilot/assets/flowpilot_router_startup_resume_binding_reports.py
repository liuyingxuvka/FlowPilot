"""Resume role-binding report and continuation binding writes."""

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

def _write_resume_role_rehydration_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    records = router._normalize_resume_role_agent_records(project_root, run_root, run_state, payload)
    target_role_keys = router._current_resume_role_keys(project_root, run_root, run_state)
    memory_complete = all((record.get('role_memory_status') == 'available' for record in records))
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    replacement_roles = [record['role_key'] for record in records if record.get('current_run_binding_decision') == 'current_run_replacement_opened']
    report_path = run_root / 'continuation' / 'role_binding_recovery_report.json'
    report = {'schema_version': 'flowpilot.role_binding_recovery_report.v1', 'run_id': run_state['run_id'], 'resume_tick_id': router._latest_resume_tick_id(run_state), 'role_binding_mode': 'current_run_manual_resume_rehydration', 'target_role_keys': target_role_keys, 'recorded_at': utc_now(), 'source_paths': {'resume_reentry': project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), 'role_binding_ledger': project_relative(project_root, run_root / 'role_binding_ledger.json'), 'role_binding_memory': project_relative(project_root, run_root / 'role_binding_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'role_io_protocol_ledger': project_relative(project_root, _role_io_protocol_ledger_path(run_root)), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}, 'required_role_bindings_ready': [record['role_key'] for record in records] == target_role_keys, 'role_binding_evidence_policy': {'checked_at': utc_now(), 'current_wait_authority': 'ack_progress_evidence_only', 'awaiting_role': resume_next.get('next_recipient_role'), 'roles_checked': [record['role_key'] for record in records], 'replacement_role_keys': replacement_roles, 'decision': 'roles_ready_after_replacement' if replacement_roles else 'current_resume_roles_addressable'}, 'liveness_preflight': {'roles_checked': target_role_keys, 'current_wait_authority': 'ack_progress_evidence_only', 'wait_agent_timeout_treated_as_active': any((record.get('wait_agent_timeout_treated_as_active') is True for record in records)), 'bounded_wait_result_values': [str(record.get('bounded_wait_result') or '') for record in records if record.get('bounded_wait_result')]}, 'current_run_memory_complete': memory_complete, 'missing_memory_role_keys': [record['role_key'] for record in records if record.get('role_memory_status') != 'available'], 'pm_memory_rehydrated': any((record['role_key'] == 'project_manager' and record.get('pm_resume_context_delivered') is True and (record.get('role_memory_status') == 'available') for record in records)), 'role_records': records, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    runtime_roles_path = run_root / 'role_binding_ledger.json'
    role_binding = read_json_if_exists(runtime_roles_path)
    if role_binding.get('schema_version') != 'flowpilot.role_binding_ledger.v1':
        raise RouterError('resume role rehydration requires current role_binding_ledger schema')
    if str(role_binding.get('run_id') or '') != str(run_state['run_id']):
        raise RouterError('resume role rehydration requires current role_binding_ledger run_id')
    existing_slots = role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []
    slots_by_role: dict[str, dict[str, Any]] = {}
    for slot in existing_slots:
        if not isinstance(slot, dict):
            raise RouterError('resume role rehydration found non-object role slot')
        role = str(slot.get('role_key') or '')
        if role not in RUNTIME_ROLE_KEYS or role in slots_by_role:
            raise RouterError('resume role rehydration found unsupported or duplicate role slot')
        slots_by_role[role] = dict(slot)
    for record in records:
        slots_by_role[str(record['role_key'])] = dict(record)
    role_order = {role: index for index, role in enumerate(RUNTIME_ROLE_KEYS)}
    merged_slots = sorted(
        slots_by_role.values(),
        key=lambda slot: role_order.get(str(slot.get('role_key') or ''), 999),
    )
    binding_generation = max(
        [
            router._current_role_binding_generation(role_binding),
            *[
                int(record['role_binding_generation'])
                for record in records
                if isinstance(record.get('role_binding_generation'), int)
            ],
        ]
    )
    memory_updates: list[tuple[Path, dict[str, Any]]] = []
    for record in records:
        role = str(record['role_key'])
        memory_path = router._role_memory_path(run_root, role)
        memory = read_json_if_exists(memory_path)
        if memory and (
            memory.get('schema_version') != 'flowpilot.role_memory.v1'
            or str(memory.get('run_id') or '') != str(run_state['run_id'])
            or str(memory.get('role_key') or '') != role
        ):
            raise RouterError(f'resume role rehydration rejects stale role memory for {role}')
        recent_deltas = list(memory.get('recent_deltas') or []) if isinstance(memory.get('recent_deltas'), list) else []
        memory.update({
            'schema_version': 'flowpilot.role_memory.v1',
            'run_id': run_state['run_id'],
            'role_key': role,
            'agent_id': record.get('agent_id'),
            'role_binding_generation': record.get('role_binding_generation'),
            'status': 'available',
            'summary': memory.get('summary') or '',
            'recent_deltas': recent_deltas,
            'identity_policy': {'agent_id_is_diagnostic_only': True, 'current_authority_source': 'role_binding_ledger'},
            'controller_decision_authority': False,
            'role_memory_used_for_completion_authority': False,
            'last_rehydration': {
                'historical_agent_id_reused': False,
                'current_role_agent_binding': True,
                'resume_tick_id': report['resume_tick_id'],
            },
            'updated_at': report['recorded_at'],
        })
        memory_updates.append((memory_path, memory))
    history = role_binding.get('resume_rehydration_history') if isinstance(role_binding.get('resume_rehydration_history'), list) else []
    history.append({'report_path': project_relative(project_root, report_path), 'resume_tick_id': report['resume_tick_id'], 'recorded_at': report['recorded_at'], 'required_role_bindings_ready': report['required_role_bindings_ready'], 'current_run_memory_complete': memory_complete, 'binding_decision': report['role_binding_evidence_policy']['decision'], 'replacement_role_keys': replacement_roles})
    target_roles = {str(record['role_key']) for record in records}
    role_binding.update({'schema_version': 'flowpilot.role_binding_ledger.v1', 'run_id': run_state['run_id'], 'role_slots': merged_slots, 'role_binding_generation': binding_generation, 'latest_resume_rehydration_report': project_relative(project_root, report_path), 'resume_rehydration_history': history, 'role_binding_memory_paths': [project_relative(project_root, router._role_memory_path(run_root, str(slot['role_key']))) for slot in merged_slots if str(slot['role_key']) in target_roles or router._role_memory_path(run_root, str(slot['role_key'])).exists()], 'updated_at': utc_now()})
    write_json(runtime_roles_path, role_binding)
    for memory_path, memory in memory_updates:
        write_json(memory_path, memory)
    write_json(report_path, report)
    for record in records:
        role = str(record['role_key'])
        memory_path = router._role_memory_path(run_root, role)
        current_bindings = run_state.setdefault('current_role_agent_bindings', {})
        if isinstance(current_bindings, dict):
            current_bindings[role] = {
                'role_binding_ledger_path': project_relative(project_root, runtime_roles_path),
                'role_binding_memory_path': project_relative(project_root, memory_path),
                'agent_id': record.get('agent_id'),
                'role_binding_generation': record.get('role_binding_generation'),
                'opened_at': report['recorded_at'],
            }
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') == ROLE_RECOVERY_TRANSACTION_SCHEMA:
        role_recovery_report_path = router._role_recovery_report_path(run_root)
        replay_ready = memory_complete and bool(report['required_role_bindings_ready'])
        role_recovery_report = {'schema_version': ROLE_RECOVERY_REPORT_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction.get('transaction_id'), 'trigger_source': transaction.get('trigger_source'), 'recovery_scope': transaction.get('recovery_scope'), 'target_role_keys': transaction.get('target_role_keys') or target_role_keys, 'recorded_at': report['recorded_at'], 'priority': 'preempt_normal_work', 'normal_work_suspended_until_report': True, 'required_role_bindings_ready': report['required_role_bindings_ready'], 'environment_blocked': False, 'role_binding_generation_after': role_binding.get('role_binding_generation'), 'role_records': [{'role_key': record['role_key'], 'old_agent_id': None, 'agent_id': record.get('agent_id'), 'recovery_result': ROLE_BINDING_RESTORE_RESULT if record.get('rehydration_result') == ROLE_BINDING_CONTINUITY_RESULT else ROLE_BINDING_TARGETED_REPLACEMENT_RESULT, 'memory_context_injected': record.get('role_memory_status') == 'available', 'packet_ownership_reconciled': True, 'role_binding_epoch': record.get('role_binding_epoch'), 'role_binding_generation': record.get('role_binding_generation'), 'superseded_agent_output_quarantined': bool(record.get('superseded_agent_ids'))} for record in records], 'packet_ownership_reconciled': True, 'memory_context_injected': memory_complete, 'stale_generation_output_quarantined': True, 'pm_decision_required_before_normal_work': not replay_ready, 'mechanical_obligation_replay_before_pm': replay_ready, 'mechanical_obligation_replay_completed': False, 'role_binding_recovery_report_path': project_relative(project_root, report_path), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
        write_json(role_recovery_report_path, role_recovery_report)
        run_state['flags']['role_recovery_state_loaded'] = True
        run_state['flags']['role_recovery_roles_restored'] = True
        run_state['flags']['role_recovery_report_written'] = True
        run_state['flags']['role_recovery_environment_blocked'] = False
        run_state['flags']['role_recovery_requested'] = False
        if replay_ready:
            replay = router._plan_role_recovery_obligation_replay(project_root, run_root, run_state, transaction=transaction, records=role_recovery_report['role_records'], report_path=role_recovery_report_path)
            role_recovery_report['role_recovery_obligation_replay_path'] = run_state['role_recovery_obligation_replay']['path']
            role_recovery_report['pm_decision_required_before_normal_work'] = bool(replay.get('pm_escalation_required'))
            role_recovery_report['mechanical_obligation_replay_completed'] = not bool(replay.get('pm_escalation_required'))
            write_json(role_recovery_report_path, role_recovery_report)
            run_state['flags']['pm_resume_recovery_decision_returned'] = not bool(replay.get('pm_escalation_required'))
        else:
            skipped_reason = 'missing_current_run_memory' if not memory_complete else 'roles_not_ready'
            role_recovery_report['resume_rehydration_replay_skipped_reason'] = skipped_reason
            write_json(role_recovery_report_path, role_recovery_report)
            run_state['flags']['role_recovery_obligations_scanned'] = False
            run_state['flags']['role_recovery_obligation_replay_completed'] = False
            run_state['flags']['role_recovery_pm_escalation_required'] = True
            run_state['flags']['pm_resume_recovery_decision_returned'] = False
            append_history(run_state, 'router_skipped_resume_obligation_replay', {'transaction_id': transaction.get('transaction_id'), 'reason': skipped_reason, 'memory_complete': memory_complete, 'required_role_bindings_ready': report['required_role_bindings_ready']})
    _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), records, default_lifecycle_phase='manual_resume_rehydration', resume_tick_id=report['resume_tick_id'], source_action='rehydrate_role_bindings')
    run_state['flags']['resume_roles_restored'] = True
    run_state['flags']['resume_role_bindings_rehydrated'] = True
    run_state['flags']['role_binding_recovery_report_written'] = True
    if not memory_complete:
        run_state['flags']['resume_state_ambiguous'] = True

def _resume_rehydration_report_candidates(router: ModuleType, project_root: Path, run_root: Path, payload: dict[str, Any] | None = None) -> list[Path]:
    _bind_router(router)
    candidates: list[Path] = []
    payload = payload if isinstance(payload, dict) else {}
    for key in ('role_binding_recovery_report_path', 'report_path', 'rehydration_report_path'):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            candidates.append(resolve_project_path(project_root, raw))
    candidates.append(run_root / 'continuation' / 'role_binding_recovery_report.json')
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        marker = str(path.resolve()) if path.exists() else str(path)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(path)
    return unique

def _reclaim_resume_rehydration_postcondition_from_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    _bind_router(router)
    expected_roles = set(router._current_resume_role_keys(project_root, run_root, run_state))
    last_reason = 'role_binding_recovery_report_missing'
    for report_path in router._resume_rehydration_report_candidates(project_root, run_root, payload):
        report = read_json_if_exists(report_path)
        if not report:
            last_reason = 'role_binding_recovery_report_missing'
            continue
        if report.get('schema_version') != 'flowpilot.role_binding_recovery_report.v1':
            last_reason = 'role_binding_recovery_report_schema_mismatch'
            continue
        if str(report.get('run_id') or '') != str(run_state.get('run_id') or ''):
            last_reason = 'role_binding_recovery_report_wrong_run'
            continue
        records = report.get('role_records') if isinstance(report.get('role_records'), list) else []
        role_keys = {str(record.get('role_key') or '') for record in records if isinstance(record, dict)}
        if role_keys != expected_roles:
            last_reason = 'role_binding_recovery_report_role_set_incomplete'
            continue
        if report.get('required_role_bindings_ready') is not True:
            last_reason = 'role_binding_recovery_report_roles_not_ready'
            continue
        if report.get('current_run_memory_complete') is not True:
            last_reason = 'role_binding_recovery_report_memory_incomplete'
            continue
        evidence_policy = report.get('role_binding_evidence_policy') if isinstance(report.get('role_binding_evidence_policy'), dict) else {}
        if evidence_policy.get('current_wait_authority') != 'ack_progress_evidence_only':
            last_reason = 'role_binding_recovery_report_missing_ack_progress_policy'
            continue
        if report.get('sealed_body_reads_allowed') is not False:
            last_reason = 'role_binding_recovery_report_boundary_not_confirmed'
            continue
        flags = run_state.setdefault('flags', {})
        flags['resume_roles_restored'] = True
        flags['resume_role_bindings_rehydrated'] = True
        flags['role_binding_recovery_report_written'] = True
        flags['resume_state_loaded'] = True
        flags['resume_reentry_requested'] = True
        relpath = project_relative(project_root, report_path)
        append_history(
            run_state,
            'router_reclaimed_resume_rehydration_report_postcondition',
            {
                'source': source,
                'role_binding_recovery_report_path': relpath,
                'role_keys': sorted(role_keys),
                'current_run_memory_complete': True,
            },
        )
        return {
            'applied': True,
            'source': source,
            'postcondition': 'resume_roles_restored',
            'role_binding_recovery_report_path': relpath,
            'role_keys': sorted(role_keys),
        }
    return {'applied': False, 'reason': last_reason, 'postcondition': 'resume_roles_restored'}

def _stable_resume_launcher_contract(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return {'event': 'manual_resume_requested', 'wake_sources': ['manual_resume'], 'resume_action': 'load_resume_state', 'role_liveness_action': 'rehydrate_role_bindings', 'router_reentry_required_on_every_wake': True, 'host_automation_supported': False, 'self_keepalive_allowed': False, 'diagnostic_work_chain_status_only': True, 'controller_only': True, 'sealed_body_reads_allowed': False}

def _write_initial_continuation_binding(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    binding = {'schema_version': 'flowpilot.continuation_binding.v1', 'run_id': run_state['run_id'], 'mode': 'manual_resume', 'manual_resume_required': True, 'manual_resume_binding_active': True, 'host_automation_supported': False, 'stable_launcher': router._stable_resume_launcher_contract(), 'source_paths': {'startup_answers': project_relative(project_root, run_root / 'startup_answers.json'), 'router_state': project_relative(project_root, router.run_state_path(run_root))}, 'updated_at': utc_now()}
    write_json(router._continuation_binding_path(run_root), binding)
    router._write_continuation_quarantine(project_root, run_root, run_state)

__all__ = (
    '_write_resume_role_rehydration_report',
    '_resume_rehydration_report_candidates',
    '_reclaim_resume_rehydration_postcondition_from_report',
    '_stable_resume_launcher_contract',
    '_write_initial_continuation_binding',
)
