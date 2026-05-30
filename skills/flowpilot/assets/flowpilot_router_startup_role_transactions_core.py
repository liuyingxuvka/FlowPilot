"""role recovery transaction state helpers for ``flowpilot_router_startup_role_transactions``.

This child module is imported by the public facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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
    flags['resume_role_bindings_rehydrated'] = True
    flags['role_binding_recovery_report_written'] = (run_root / 'continuation' / 'role_binding_recovery_report.json').exists()
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

def _current_role_binding_generation(router: ModuleType, role_binding: dict[str, Any]) -> int:
    _bind_router(router)
    raw = role_binding.get('role_binding_generation')
    if isinstance(raw, int) and raw > 0:
        return raw
    generations = [int(slot.get('role_binding_generation')) for slot in (role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []) if isinstance(slot, dict) and isinstance(slot.get('role_binding_generation'), int)]
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
    transaction = {'schema_version': ROLE_RECOVERY_TRANSACTION_SCHEMA, 'transaction_id': transaction_id, 'run_id': run_state['run_id'], 'trigger_source': trigger_source, 'recovery_scope': recovery_scope, 'target_role_keys': list(target_role_keys), 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'started_at': utc_now(), 'fault_payload': fault_payload, 'active_packet_context': active_packet, 'recovery_ladder': ['restore_old_agent', 'targeted_replacement', 'slot_reconciliation', 'full_role_binding_recovery', 'environment_blocked'], 'controller_may_wait_for_normal_work_before_recovery': False, 'controller_may_infer_completion_from_old_agent': False}
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
    required_fields = ['runtime_role_assistance_capability_status', 'recovery_transaction_id', 'trigger_source', 'recovery_scope', 'target_role_keys', 'recovered_role_bindings[].role_key', 'recovered_role_bindings[].agent_id', 'recovered_role_bindings[].model_policy', 'recovered_role_bindings[].reasoning_effort_policy', 'recovered_role_bindings[].recovery_result', 'recovered_role_bindings[].restore_attempted', 'recovered_role_bindings[].restore_result', 'recovered_role_bindings[].host_liveness_status', 'recovered_role_bindings[].liveness_decision', 'recovered_role_bindings[].rehydrated_for_run_id', 'recovered_role_bindings[].memory_context_injected', 'recovered_role_bindings[].packet_ownership_reconciled']
    if scope == 'targeted':
        required_fields.extend(['recovered_role_bindings[].old_agent_id', 'recovered_role_bindings[].role_binding_epoch_advanced', 'recovered_role_bindings[].superseded_agent_output_quarantined'])
    return _payload_contract(name='role_liveness_recovery_receipt', required_object='payload', required_fields=required_fields, allowed_values={'runtime_role_assistance_capability_status': ['available'], 'recovery_transaction_id': [str(transaction.get('transaction_id') or '')], 'trigger_source': [str(transaction.get('trigger_source') or '')], 'recovery_scope': [scope, 'full_crew'], 'target_role_keys': [target_roles], 'recovered_role_bindings[].role_key': list(RUNTIME_ROLE_KEYS), 'recovered_role_bindings[].model_policy': [ROLE_BINDING_MODEL_POLICY], 'recovered_role_bindings[].reasoning_effort_policy': [ROLE_BINDING_REASONING_EFFORT_POLICY], 'recovered_role_bindings[].recovery_result': sorted(ROLE_RECOVERY_RESULTS), 'recovered_role_bindings[].host_liveness_status': ['active'], 'recovered_role_bindings[].liveness_decision': sorted(ROLE_BINDING_LIVENESS_DECISIONS), 'recovered_role_bindings[].rehydrated_for_run_id': [run_state['run_id']], 'recovered_role_bindings[].memory_context_injected': [True], 'recovered_role_bindings[].packet_ownership_reconciled': [True]}, structural_requirements=['Recovery must be recorded before any normal route, packet, gate, or control-blocker work resumes.', 'For targeted recovery, attempt old-agent restore before replacement.', 'If old close fails and targeted open reports capacity_full, slot reconciliation and full role binding recycle must be attempted before any success report.', 'A failed full role binding recycle must return recovery_result=environment_blocked and must not mark the role binding ready.', 'Recovered or replacement roles must receive current-run memory/context before being marked usable.', 'Recovered or replacement roles must have active host addressability proof before being marked usable.', 'Late output from superseded agent ids must be quarantined and cannot count as packet or gate progress.', 'Packet ownership must be reconciled before PM is asked to continue.'], description='Record the host recovery attempt ladder for a missing or unhealthy FlowPilot role.', reviewer_check='PM checks this role recovery report before deciding whether to resume, re-dispatch, or escalate.')

def _load_role_recovery_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery state load requires an open role recovery transaction')
    loaded_paths = {'role_recovery_transaction': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), 'router_state': project_relative(project_root, router.run_state_path(run_root)), 'role_binding_ledger': project_relative(project_root, run_root / 'role_binding_ledger.json'), 'role_binding_memory': project_relative(project_root, run_root / 'role_binding_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}
    missing_paths = [rel for rel in loaded_paths.values() if not resolve_project_path(project_root, rel).exists()]
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    record = {'schema_version': 'flowpilot.role_recovery_state_load.v1', 'run_id': run_state['run_id'], 'transaction_id': transaction['transaction_id'], 'trigger_source': transaction['trigger_source'], 'recovery_scope': transaction['recovery_scope'], 'target_role_keys': transaction['target_role_keys'], 'loaded_at': utc_now(), 'loaded_paths': loaded_paths, 'missing_paths': missing_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False}
    write_json(router._role_recovery_state_path(run_root), record)
    resume_reentry_path = run_root / 'continuation' / 'resume_reentry.json'
    if not resume_reentry_path.exists():
        write_json(resume_reentry_path, {'schema_version': 'flowpilot.resume_reentry.v1', 'run_id': run_state['run_id'], 'stable_launcher': True, 'controller_only': True, 'wake_recorded_to_router': True, 'role_recovery_triggered': True, 'role_recovery_transaction_id': transaction['transaction_id'], 'visible_plan_restore_required': True, 'visible_plan_restored_from_run': True, 'role_rehydration_required': True, 'roles_restored_or_replaced': False, 'ambiguous_state_blocks_controller_execution': bool(missing_paths), 'missing_paths': missing_paths, 'loaded_paths': loaded_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False, 'recorded_at': record['loaded_at']})
    run_state['flags']['role_recovery_state_loaded'] = True
    return record

__all__ = (
    '_reclaim_role_recovery_postcondition_from_report',
    '_current_role_binding_generation',
    '_open_role_recovery_transaction',
    '_role_recovery_payload_contract',
    '_load_role_recovery_state',
)

_LOCAL_NAMES = set(globals())
