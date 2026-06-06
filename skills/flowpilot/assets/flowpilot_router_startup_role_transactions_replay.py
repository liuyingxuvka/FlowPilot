"""role recovery replacement and replay planning helpers for ``flowpilot_router_startup_role_transactions``.

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
    target_roles = {str(record.get('role_key') or '') for record in records if record.get('recovery_result') != ROLE_BINDING_ENVIRONMENT_BLOCKED_RESULT}
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
    '_role_recovery_replacement_action',
    '_supersede_role_recovery_original_wait',
    '_plan_role_recovery_obligation_replay',
)

_LOCAL_NAMES = set(globals())
