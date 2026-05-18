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

def _resume_role_rehydration_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    mode = answers.get('background_agents')
    contexts = router._resume_role_contexts(project_root, run_root, run_state)
    missing_memory = [item['role_key'] for item in contexts if item['role_memory_status'] != 'available']
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    liveness_probe_batch_id = router._resume_liveness_probe_batch_id(run_state)
    extra: dict[str, Any] = {'background_agents_mode': mode, 'role_keys': list(CREW_ROLE_KEYS), 'resume_tick_id': router._latest_resume_tick_id(run_state), 'awaiting_role_from_packet_ledger': resume_next.get('next_recipient_role'), 'resume_next_recipient_from_packet_ledger': resume_next, 'role_rehydration_request': contexts, 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'applies_to': ['heartbeat_resume_rehydration', 'manual_resume_rehydration', 'missing_role_replacement']}, 'memory_missing_role_keys': missing_memory, 'crew_rehydration_report_path': project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), 'liveness_probe_batch_id': liveness_probe_batch_id, 'liveness_preflight_required': True, 'liveness_preflight_policy': {'roles_to_check': list(CREW_ROLE_KEYS), 'current_waiting_role_source': 'packet_ledger.next_recipient_role', 'resume_agent_check_required': True, 'concurrent_probe_required': True, 'probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': liveness_probe_batch_id, 'start_all_probes_before_waiting': True, 'bounded_wait_allowed': True, 'wait_agent_timeout_result': 'timeout_unknown', 'timeout_unknown_is_active': False, 'missing_cancelled_unknown_requires_replacement': True, 'heartbeat_and_manual_resume_share_path': True}, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    if mode == 'allow':
        extra.update({'requires_payload': 'rehydrated_role_agents', 'payload_contract': _resume_role_rehydration_payload_contract(run_state, contexts), 'requires_host_spawn': False, 'requires_host_role_rehydration': True, 'requires_host_spawn_for_replacements': True, 'spawn_required_only_for_replacements': True, 'reuse_live_agents_when_active': True, 'spawn_policy': 'reuse_confirmed_live_agents_spawn_only_missing_cancelled_completed_unknown_or_timeout', 'pm_memory_rehydration_required': True})
    elif mode == 'single-agent':
        extra.update({'requires_host_spawn': False, 'single_agent_continuity_authorized': True})
    return extra

def _normalize_resume_role_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    mode = answers.get('background_agents')
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    current_generation = router._current_crew_generation(crew)
    existing_slots = {str(slot.get('role_key')): slot for slot in (crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []) if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    resume_tick_id = router._latest_resume_tick_id(run_state)
    if mode == 'single-agent':
        return [{'role_key': role, 'status': 'single_agent_resume_continuity_authorized', 'agent_id': None, 'rehydration_result': 'not_requested_single_agent_continuity', 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': resume_tick_id, 'host_liveness_status': 'not_applicable_single_agent', 'liveness_decision': 'single_agent_resume_continuity_authorized', 'resume_agent_attempted': False, 'bounded_wait_result': 'not_applicable', 'wait_agent_timeout_treated_as_active': False, 'fallback_authorized_by_startup_answer': True, 'recorded_at': utc_now()} for role in CREW_ROLE_KEYS]
    if mode != 'allow':
        raise RouterError('cannot rehydrate roles before background_agents startup answer is recorded')
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('resume role rehydration requires background_agents_capability_status=available')
    expected_batch_id = router._resume_liveness_probe_batch_id(run_state)
    if payload.get('liveness_probe_batch_id') != expected_batch_id:
        raise RouterError(f'resume role rehydration requires liveness_probe_batch_id={expected_batch_id}')
    if payload.get('liveness_probe_mode') != ROLE_AGENT_LIVENESS_PROBE_MODE:
        raise RouterError(f'resume role rehydration requires liveness_probe_mode={ROLE_AGENT_LIVENESS_PROBE_MODE}')
    if payload.get('all_liveness_probes_started_before_wait') is not True:
        raise RouterError('resume role rehydration requires all_liveness_probes_started_before_wait=true')
    raw_records = payload.get('rehydrated_role_agents') or payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('rehydrate_role_agents requires payload.rehydrated_role_agents list or object')
    records_by_role: dict[str, dict[str, Any]] = {}
    probe_started_times: list[datetime] = []
    probe_completed_times: list[datetime] = []

    def parse_probe_time(role_key: str, field: str, value: object) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise RouterError(f'{role_key} requires {field}')
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise RouterError(f'{role_key} requires ISO timestamp {field}') from exc
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each rehydrated role agent record must be an object')
        role = raw.get('role_key')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'rehydrated role record has unsupported role_key: {role!r}')
        if role in records_by_role:
            raise RouterError(f'duplicate rehydrated role record for {role}')
        context = contexts[str(role)]
        old_slot = existing_slots.get(str(role)) or {}
        old_epoch = old_slot.get('role_binding_epoch')
        role_epoch = int(old_epoch) if isinstance(old_epoch, int) else 0
        agent_id = raw.get('agent_id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f'{role} requires a non-empty live resume agent_id')
        if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
            raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
        if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
            raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
        result = raw.get('rehydration_result') or raw.get('spawn_result')
        if result not in RESUME_ROLE_AGENT_RESULTS:
            raise RouterError(f'{role} requires resume rehydration result')
        host_liveness_status = str(raw.get('host_liveness_status') or '')
        if host_liveness_status not in ROLE_AGENT_HOST_LIVENESS_STATUSES:
            raise RouterError(f'{role} requires host_liveness_status')
        liveness_decision = str(raw.get('liveness_decision') or '')
        if liveness_decision not in ROLE_AGENT_LIVENESS_DECISIONS:
            raise RouterError(f'{role} requires liveness_decision')
        if raw.get('resume_agent_attempted') is not True:
            raise RouterError(f'{role} requires resume_agent_attempted=true')
        bounded_wait_result = str(raw.get('bounded_wait_result') or '')
        if bounded_wait_result not in ROLE_AGENT_BOUNDED_WAIT_RESULTS:
            raise RouterError(f'{role} requires bounded_wait_result')
        if raw.get('liveness_probe_batch_id') != expected_batch_id:
            raise RouterError(f'{role} liveness probe batch id mismatch')
        if raw.get('liveness_probe_mode') != ROLE_AGENT_LIVENESS_PROBE_MODE:
            raise RouterError(f'{role} requires concurrent liveness probe mode')
        bounded_wait_ms = raw.get('bounded_wait_ms')
        if isinstance(bounded_wait_ms, bool) or not isinstance(bounded_wait_ms, int) or bounded_wait_ms < 0:
            raise RouterError(f'{role} requires nonnegative bounded_wait_ms')
        started_at = parse_probe_time(str(role), 'liveness_probe_started_at', raw.get('liveness_probe_started_at'))
        completed_at = parse_probe_time(str(role), 'liveness_probe_completed_at', raw.get('liveness_probe_completed_at'))
        if completed_at < started_at:
            raise RouterError(f'{role} liveness probe completed before it started')
        probe_started_times.append(started_at)
        probe_completed_times.append(completed_at)
        if raw.get('wait_agent_timeout_treated_as_active') is not False:
            raise RouterError(f'{role} must record wait_agent_timeout_treated_as_active=false')
        if bounded_wait_result == 'timeout_unknown' and result == ROLE_AGENT_CONTINUITY_RESULT:
            raise RouterError(f'{role} wait_agent timeout_unknown cannot be treated as active continuity')
        if host_liveness_status in {'missing', 'cancelled', 'unknown', 'timeout_unknown'} and liveness_decision == 'confirmed_existing_agent':
            raise RouterError(f'{role} missing/cancelled/unknown host liveness cannot confirm existing agent')
        if host_liveness_status == 'completed' and liveness_decision == 'confirmed_existing_agent':
            raise RouterError(f'{role} completed host liveness cannot confirm existing agent')
        if result == ROLE_AGENT_CONTINUITY_RESULT and (not (host_liveness_status == 'active' and liveness_decision == 'confirmed_existing_agent')):
            raise RouterError(f'{role} live continuity requires active host liveness')
        if result == ROLE_AGENT_REHYDRATION_RESULT and liveness_decision != 'spawned_replacement_from_current_run_memory':
            raise RouterError(f'{role} replacement rehydration requires spawned_replacement_from_current_run_memory')
        if result == ROLE_AGENT_REHYDRATION_RESULT and host_liveness_status == 'active':
            raise RouterError(f'{role} active host liveness must use live_agent_continuity_confirmed, not replacement rehydration')
        if raw.get('rehydrated_for_run_id') != run_state['run_id']:
            raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
        if raw.get('rehydrated_after_resume_tick_id') != resume_tick_id:
            raise RouterError(f'{role} must be rehydrated_after_resume_tick_id={resume_tick_id}')
        rehydrated_after_state_loaded = raw.get('rehydrated_after_resume_state_loaded')
        legacy_spawned_after_state_loaded = raw.get('spawned_after_resume_state_loaded')
        if rehydrated_after_state_loaded is not True and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f'{role} must be rehydrated_after_resume_state_loaded=true')
        if result == ROLE_AGENT_REHYDRATION_RESULT and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f'{role} replacement rehydration requires spawned_after_resume_state_loaded=true')
        if raw.get('core_prompt_path') != context['core_prompt_path'] or raw.get('core_prompt_hash') != context['core_prompt_hash']:
            raise RouterError(f'{role} core prompt identity mismatch')
        memory_status = context['role_memory_status']
        if memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run role memory')
        else:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing role memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        if role == 'project_manager' and raw.get('pm_resume_context_delivered') is not True:
            raise RouterError('project_manager resume rehydration requires PM context delivery')
        records_by_role[str(role)] = {'role_key': str(role), 'status': 'live_agent_rehydrated', 'agent_id': agent_id.strip(), 'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'rehydration_result': str(result), 'host_liveness_status': host_liveness_status, 'liveness_decision': liveness_decision, 'resume_agent_attempted': True, 'bounded_wait_result': bounded_wait_result, 'bounded_wait_ms': bounded_wait_ms, 'liveness_probe_batch_id': expected_batch_id, 'liveness_probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_started_at': raw.get('liveness_probe_started_at'), 'liveness_probe_completed_at': raw.get('liveness_probe_completed_at'), 'wait_agent_timeout_treated_as_active': False, 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': resume_tick_id, 'rehydrated_after_resume_state_loaded': True, 'spawned_after_resume_state_loaded': result == ROLE_AGENT_REHYDRATION_RESULT, 'crew_generation': current_generation, 'role_binding_epoch': role_epoch + (1 if result == ROLE_AGENT_REHYDRATION_RESULT or agent_id.strip() != str(old_slot.get('agent_id') or '') else 0), 'superseded_agent_ids': [str(old_slot.get('agent_id'))] if result == ROLE_AGENT_REHYDRATION_RESULT and isinstance(old_slot.get('agent_id'), str) and (old_slot.get('agent_id') != agent_id.strip()) else [], 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': memory_status == 'available', 'replacement_seeded_from_common_run_context': memory_status != 'available', 'pm_resume_context_delivered': role == 'project_manager', 'recorded_at': utc_now()}
    if probe_started_times and probe_completed_times and (max(probe_started_times) > min(probe_completed_times)):
        raise RouterError('all liveness probes must start before waiting for individual results')
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing rehydrated live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]

def _write_resume_role_rehydration_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    records = router._normalize_resume_role_agent_records(project_root, run_root, run_state, payload)
    memory_complete = all((record.get('role_memory_status') == 'available' for record in records))
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    timeout_unknown_roles = [record['role_key'] for record in records if record.get('host_liveness_status') == 'timeout_unknown' or record.get('bounded_wait_result') == 'timeout_unknown']
    missing_or_cancelled_roles = [record['role_key'] for record in records if record.get('host_liveness_status') in {'missing', 'cancelled', 'unknown'}]
    replacement_roles = [record['role_key'] for record in records if record.get('liveness_decision') == 'spawned_replacement_from_current_run_memory']
    report_path = run_root / 'continuation' / 'crew_rehydration_report.json'
    report = {'schema_version': 'flowpilot.crew_rehydration_report.v1', 'run_id': run_state['run_id'], 'resume_tick_id': router._latest_resume_tick_id(run_state), 'background_agents_mode': router._startup_answers_from_run(run_root).get('background_agents'), 'recorded_at': utc_now(), 'source_paths': {'resume_reentry': project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'crew_memory': project_relative(project_root, run_root / 'crew_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'role_io_protocol_ledger': project_relative(project_root, _role_io_protocol_ledger_path(run_root)), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}, 'all_six_roles_ready': len(records) == len(CREW_ROLE_KEYS), 'liveness_preflight': {'checked_at': utc_now(), 'probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': router._resume_liveness_probe_batch_id(run_state), 'all_liveness_probes_started_before_wait': True, 'awaiting_role': resume_next.get('next_recipient_role'), 'roles_checked': [record['role_key'] for record in records], 'timeout_unknown_role_keys': timeout_unknown_roles, 'missing_cancelled_or_unknown_role_keys': missing_or_cancelled_roles, 'replacement_role_keys': replacement_roles, 'wait_agent_timeout_treated_as_active': False, 'decision': 'roles_ready_after_replacement' if replacement_roles else 'all_roles_active'}, 'current_run_memory_complete': memory_complete, 'missing_memory_role_keys': [record['role_key'] for record in records if record.get('role_memory_status') != 'available'], 'pm_memory_rehydrated': any((record['role_key'] == 'project_manager' and record.get('pm_resume_context_delivered') is True and (record.get('role_memory_status') == 'available') for record in records)), 'role_records': records, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    write_json(report_path, report)
    crew_path = run_root / 'crew_ledger.json'
    crew = read_json_if_exists(crew_path)
    history = crew.get('resume_rehydration_history') if isinstance(crew.get('resume_rehydration_history'), list) else []
    history.append({'report_path': project_relative(project_root, report_path), 'resume_tick_id': report['resume_tick_id'], 'recorded_at': report['recorded_at'], 'all_six_roles_ready': report['all_six_roles_ready'], 'current_run_memory_complete': memory_complete, 'liveness_decision': report['liveness_preflight']['decision'], 'timeout_unknown_role_keys': timeout_unknown_roles, 'missing_cancelled_or_unknown_role_keys': missing_or_cancelled_roles})
    crew.update({'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'role_slots': records, 'crew_generation': router._current_crew_generation(crew), 'latest_resume_rehydration_report': project_relative(project_root, report_path), 'resume_rehydration_history': history, 'updated_at': utc_now()})
    write_json(crew_path, crew)
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') == ROLE_RECOVERY_TRANSACTION_SCHEMA:
        role_recovery_report_path = router._role_recovery_report_path(run_root)
        replay_ready = memory_complete and bool(report['all_six_roles_ready'])
        role_recovery_report = {'schema_version': ROLE_RECOVERY_REPORT_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction.get('transaction_id'), 'trigger_source': transaction.get('trigger_source'), 'recovery_scope': transaction.get('recovery_scope'), 'target_role_keys': transaction.get('target_role_keys') or list(CREW_ROLE_KEYS), 'recorded_at': report['recorded_at'], 'priority': 'preempt_normal_work', 'normal_work_suspended_until_report': True, 'all_six_roles_ready': report['all_six_roles_ready'], 'environment_blocked': False, 'crew_generation_after': crew.get('crew_generation'), 'role_records': [{'role_key': record['role_key'], 'old_agent_id': None, 'agent_id': record.get('agent_id'), 'recovery_result': ROLE_AGENT_OLD_RESTORE_RESULT if record.get('rehydration_result') == ROLE_AGENT_CONTINUITY_RESULT else ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, 'memory_context_injected': record.get('role_memory_status') == 'available', 'packet_ownership_reconciled': True, 'role_binding_epoch': record.get('role_binding_epoch'), 'crew_generation': record.get('crew_generation'), 'superseded_agent_output_quarantined': bool(record.get('superseded_agent_ids'))} for record in records], 'packet_ownership_reconciled': True, 'memory_context_injected': memory_complete, 'stale_generation_output_quarantined': True, 'pm_decision_required_before_normal_work': not replay_ready, 'mechanical_obligation_replay_before_pm': replay_ready, 'mechanical_obligation_replay_completed': False, 'compatibility_crew_rehydration_report': project_relative(project_root, report_path), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
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
            append_history(run_state, 'router_skipped_resume_obligation_replay', {'transaction_id': transaction.get('transaction_id'), 'reason': skipped_reason, 'memory_complete': memory_complete, 'all_six_roles_ready': report['all_six_roles_ready']})
    _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), records, default_lifecycle_phase='heartbeat_rehydration', resume_tick_id=report['resume_tick_id'], source_action='rehydrate_role_agents')
    run_state['flags']['resume_roles_restored'] = True
    run_state['flags']['resume_role_agents_rehydrated'] = True
    run_state['flags']['crew_rehydration_report_written'] = True
    if not memory_complete:
        run_state['flags']['resume_state_ambiguous'] = True

def _stable_resume_launcher_contract(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return {'event': 'heartbeat_or_manual_resume_requested', 'wake_sources': ['heartbeat', 'manual_resume'], 'resume_action': 'load_resume_state', 'role_liveness_action': 'rehydrate_role_agents', 'router_reentry_required_on_every_wake': True, 'heartbeat_and_manual_resume_share_path': True, 'self_keepalive_allowed': False, 'diagnostic_work_chain_status_only': True, 'controller_only': True, 'sealed_body_reads_allowed': False}

def _write_initial_continuation_binding(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    scheduled_requested = router._scheduled_continuation_requested(answers)
    binding = {'schema_version': 'flowpilot.continuation_binding.v1', 'run_id': run_state['run_id'], 'mode': 'scheduled_heartbeat' if scheduled_requested else 'manual_resume', 'scheduled_continuation_requested': scheduled_requested, 'route_heartbeat_interval_minutes': 1 if scheduled_requested else 0, 'heartbeat_active': False, 'host_automation_id': None, 'host_automation_verified': False, 'stable_launcher': router._stable_resume_launcher_contract(), 'source_paths': {'startup_answers': project_relative(project_root, run_root / 'startup_answers.json'), 'router_state': project_relative(project_root, router.run_state_path(run_root))}, 'updated_at': utc_now()}
    write_json(router._continuation_binding_path(run_root), binding)
    router._write_continuation_quarantine(project_root, run_root, run_state)

def _next_resume_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('resume_reentry_requested'):
        return None
    if not flags.get('resume_state_loaded'):
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
        return make_action(action_type='load_resume_state', actor='controller', label='controller_loads_resume_state_before_role_rehydration', summary='Controller loads current-run state, ledgers, frontier, visible plan, and crew memory before live role rehydration.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _router_daemon_lock_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], extra={'postcondition': 'resume_state_loaded', 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'wake_recorded_to_router_required': True, 'visible_plan_restore_required': True, 'role_rehydration_required_before_pm_resume_decision': True, 'continuation_quarantine_required': True, 'resume_next_recipient_from_packet_ledger': resume_next, 'router_daemon_resume_recovery': _router_daemon_resume_recovery_summary(project_root, run_root)})
    if not flags.get('resume_roles_restored'):
        active_blocker = run_state.get('active_control_blocker')
        if isinstance(active_blocker, dict) and active_blocker.get('originating_action_type') == 'rehydrate_role_agents':
            return None
        return make_action(action_type='rehydrate_role_agents', actor='controller', label='host_rehydrates_resume_roles_before_pm_decision', summary='Host restores or replaces all six live FlowPilot roles from current-run memory before PM resume decision.', allowed_reads=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'resume_roles_restored', **router._resume_role_rehydration_action_extra(project_root, run_root, run_state)})
    return None

def _next_role_recovery_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('role_recovery_requested'):
        return None
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        return None
    trigger_source = str(transaction.get('trigger_source') or '')
    if trigger_source in {'heartbeat_resume', 'manual_resume'}:
        return None
    if not flags.get('role_recovery_state_loaded'):
        return make_action(action_type='load_role_recovery_state', actor='controller', label='controller_loads_role_recovery_state_before_normal_work', summary='Controller loads current-run role recovery state before any normal route, packet, gate, wait, or control-blocker work continues.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_state_loaded', 'role_recovery_transaction': transaction, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'recovery_priority': 'preempt_normal_work', 'normal_waits_allowed_before_recovery': False})
    if not flags.get('role_recovery_roles_restored') and (not flags.get('role_recovery_environment_blocked')):
        return make_action(action_type='recover_role_agents', actor='controller', label='host_recovers_role_agents_before_normal_work', summary='Host restores or replaces the unhealthy background role, escalating to full crew recycle when targeted recovery cannot succeed.', allowed_reads=[project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_roles_restored', 'role_recovery_transaction': transaction, 'target_role_keys': list(transaction.get('target_role_keys') or []), 'recovery_ladder': transaction.get('recovery_ladder') or [], 'payload_contract': router._role_recovery_payload_contract(run_root, run_state, transaction), 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False}, 'role_recovery_request': [{**router._resume_role_context(project_root, run_root, run_state, role), 'recovery_transaction_id': transaction.get('transaction_id'), 'recovery_scope': transaction.get('recovery_scope'), 'old_agent_id': _active_agent_id_for_role(run_root, role), 'restore_first_required': True, 'packet_ownership_reconciliation_required': True, 'superseded_agent_output_quarantine_required': True} for role in transaction.get('target_role_keys') or [] if role in CREW_ROLE_KEYS], 'full_crew_recycle_scope_if_escalated': list(CREW_ROLE_KEYS), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'normal_waits_allowed_before_recovery': False, 'mechanical_obligation_replay_after_recovery': True, 'pm_decision_required_after_recovery': False, 'pm_escalation_only_for_semantic_ambiguity': True})
    return None

def _next_startup_heartbeat_binding_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    if not router._scheduled_continuation_requested(answers):
        return None
    if run_state['flags'].get('continuation_binding_recorded') and router._host_heartbeat_binding_ready(run_root, run_state):
        return None
    if not run_state['flags'].get('controller_core_loaded'):
        return None
    automation_id_hint = f"flowpilot-{run_state['run_id']}-heartbeat"
    automation_name = f"FlowPilot {run_state['run_id']} heartbeat"
    prompt = _startup_heartbeat_prompt(project_root, str(run_state['run_id']))
    return make_action(action_type='create_heartbeat_automation', actor='bootloader', label='host_bootstraps_startup_heartbeat_automation', summary='Create the one-minute Codex heartbeat for the current run after Controller core handoff and before startup review.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, router._continuation_binding_path(run_root))], allowed_writes=[project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'continuation_binding_recorded', 'requires_host_automation': True, 'host_tool': 'codex_app.automation_update', 'automation_update_request': {'mode': 'create', 'kind': 'heartbeat', 'destination': 'thread', 'name': automation_name, 'prompt': prompt, 'rrule': 'FREQ=MINUTELY;INTERVAL=1', 'status': 'ACTIVE'}, 'expected_payload': {'route_heartbeat_interval_minutes': 1, 'host_automation_id': automation_id_hint, 'host_automation_verified': True, 'host_automation_proof': {'source_kind': 'host_receipt', 'run_id': run_state['run_id'], 'host_automation_id': automation_id_hint, 'route_heartbeat_interval_minutes': 1, 'heartbeat_bound_to_current_run': True}}, 'payload_contract': _heartbeat_payload_contract(run_state['run_id'], automation_id_hint), 'proof_required_before_controller_receipt': True})

__all__ = (
    '_resume_role_rehydration_action_extra',
    '_normalize_resume_role_agent_records',
    '_write_resume_role_rehydration_report',
    '_stable_resume_launcher_contract',
    '_write_initial_continuation_binding',
    '_next_resume_action',
    '_next_role_recovery_action',
    '_next_startup_heartbeat_binding_action',
)

_LOCAL_NAMES = set(globals())
