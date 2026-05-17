"""Coarse controller scheduler owner helpers for the FlowPilot router.

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

def _empty_router_scheduler_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': ROUTER_SCHEDULER_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'rows': [], 'counts': _router_scheduler_row_counts([]), 'router_is_only_scheduler_writer': True, 'controller_table_is_simple_work_board': True, 'controller_may_write_only_receipts': True}

def _read_router_scheduler_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = _router_scheduler_ledger_path(run_root)
    ledger = read_daemon_critical_json_if_exists(path)
    if ledger.get('schema_version') != ROUTER_SCHEDULER_LEDGER_SCHEMA:
        return router._empty_router_scheduler_ledger(project_root, run_root, run_state)
    rows = ledger.get('rows') if isinstance(ledger.get('rows'), list) else []
    ledger['rows'] = [row for row in rows if isinstance(row, dict)]
    ledger['counts'] = _router_scheduler_row_counts(ledger['rows'])
    return ledger

def _write_router_scheduler_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    rows = ledger.get('rows') if isinstance(ledger.get('rows'), list) else []
    ledger.update({'schema_version': ROUTER_SCHEDULER_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'rows': [row for row in rows if isinstance(row, dict)], 'router_is_only_scheduler_writer': True, 'controller_table_is_simple_work_board': True, 'controller_may_write_only_receipts': True})
    ledger['counts'] = _router_scheduler_row_counts(ledger['rows'])
    write_json(_router_scheduler_ledger_path(run_root), ledger)
    run_state['router_scheduler_ledger_path'] = project_relative(project_root, _router_scheduler_ledger_path(run_root))
    return ledger

def _ensure_router_scheduler_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    ledger = router._read_router_scheduler_ledger(project_root, run_root, run_state)
    return router._write_router_scheduler_ledger(project_root, run_root, run_state, ledger)

def _router_scheduler_ledger_summary(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = _router_scheduler_ledger_path(run_root)
    try:
        ledger = read_json_if_exists(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = _json_write_lock_liveness(path)
        return {'exists': path.exists(), 'valid_json': False, 'write_in_progress': write_lock.get('active', write_lock.get('fresh', False)), 'write_lock': write_lock, 'error': str(exc), 'path': str(path), 'counts': _router_scheduler_row_counts([]), 'rows': []}
    if ledger.get('schema_version') != ROUTER_SCHEDULER_LEDGER_SCHEMA:
        return {'exists': False, 'valid_json': True, 'counts': _router_scheduler_row_counts([]), 'rows': []}
    rows = [row for row in ledger.get('rows') or [] if isinstance(row, dict)]
    return {'exists': True, 'valid_json': True, 'path': str(_router_scheduler_ledger_path(run_root)), 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') or _router_scheduler_row_counts(rows), 'open_row_ids': [row.get('row_id') for row in rows if row.get('router_state') in {'queued', 'waiting', 'receipt_done'}], 'barrier_row_ids': [row.get('row_id') for row in rows if row.get('barrier_kind') not in {None, '', 'none'} and row.get('router_state') not in {'reconciled', 'blocked', 'skipped', 'superseded'}]}

def _router_scheduler_scope_for_action(router: ModuleType, action: dict[str, Any], run_root: Path) -> tuple[str, str]:
    _bind_router(router)
    explicit_kind = str(action.get('scope_kind') or '').strip()
    explicit_id = str(action.get('scope_id') or '').strip()
    if explicit_kind:
        return (explicit_kind, explicit_id or explicit_kind)
    if router._action_is_startup_scoped(action):
        return ('startup', 'startup')
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    if str(frontier.get('status') or '') == 'current_node_loop' and frontier.get('active_node_id'):
        return ('current_node', str(frontier.get('active_node_id')))
    return ('run', 'run')

def _action_is_startup_scoped(router: ModuleType, action: dict[str, Any] | None) -> bool:
    _bind_router(router)
    if not isinstance(action, dict):
        return False
    action_type = str(action.get('action_type') or '')
    if action_type in {'emit_startup_banner', 'start_role_slots', 'create_heartbeat_automation', 'confirm_controller_core_boundary', CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE, 'write_startup_mechanical_audit', 'write_display_surface_status'}:
        return True
    if action_type == 'sync_display_plan' and (not str(action.get('scope_kind') or '')):
        return True
    if action_type in {'check_card_return_event', 'check_card_bundle_return_event'}:
        if _pending_return_is_startup_async_scope(action):
            return True
    if _action_is_startup_async_delivery(action) or _action_is_startup_async_card_wait(action):
        return True
    card_id = str(action.get('card_id') or action.get('next_card_id') or '')
    if card_id in STARTUP_ASYNC_CARD_IDS:
        return True
    raw_card_ids = action.get('card_ids')
    if isinstance(raw_card_ids, list) and raw_card_ids:
        return {str(card_id) for card_id in raw_card_ids}.issubset(STARTUP_ASYNC_CARD_IDS)
    return False

def _router_scheduler_progress_class(router: ModuleType, action: dict[str, Any]) -> str:
    _bind_router(router)
    return _router_scheduler_progress_class_base(action, startup_scoped=router._action_is_startup_scoped)

def _router_scheduler_barrier_kind(router: ModuleType, action: dict[str, Any]) -> str:
    _bind_router(router)
    return _router_scheduler_barrier_kind_base(action, progress_class=router._router_scheduler_progress_class(action))

def _prepare_router_scheduled_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del project_root
    return _prepare_router_scheduled_action_base(run_root, run_state, action, scope_for_action=router._router_scheduler_scope_for_action, progress_class_for_action=router._router_scheduler_progress_class, barrier_kind_for_action=router._router_scheduler_barrier_kind)

def _record_router_scheduler_row(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], controller_entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(action.get('router_scheduler_row_id') or _router_scheduler_row_id_for_action(action))
    status = str(controller_entry.get('status') or _controller_action_initial_status(action))
    if status == 'done':
        router_state = 'receipt_done'
    elif status == 'blocked':
        router_state = 'blocked'
    elif status == 'skipped':
        router_state = 'skipped'
    elif status == 'waiting':
        router_state = 'waiting'
    else:
        router_state = 'queued'
    scope_kind, scope_id = router._router_scheduler_scope_for_action(action, run_root)
    row = {'schema_version': ROUTER_SCHEDULER_ROW_SCHEMA, 'row_id': row_id, 'run_id': run_state.get('run_id'), 'controller_action_id': controller_entry.get('action_id'), 'action_type': action.get('action_type'), 'label': action.get('label'), 'scope_kind': scope_kind, 'scope_id': scope_id, 'idempotency_key': action.get('idempotency_key'), 'router_state': router_state, 'controller_status': status, 'progress_class': action.get('router_scheduler_progress_class') or router._router_scheduler_progress_class(action), 'barrier_kind': action.get('router_scheduler_barrier_kind') or router._router_scheduler_barrier_kind(action), 'dependencies': action.get('dependencies') or action.get('depends_on') or [], 'postcondition': _pending_action_postcondition(action), 'completion_class': router._controller_action_completion_class(action), 'required_deliverables': action.get('required_deliverables') or controller_entry.get('required_deliverables') or [], 'deliverable_status': controller_entry.get('deliverable_status'), 'deliverable_repair_attempts': controller_entry.get('deliverable_repair_attempts'), 'max_deliverable_repair_attempts': controller_entry.get('max_deliverable_repair_attempts'), 'replaces': action.get('replaces') or controller_entry.get('replaces'), 'replaces_controller_action_id': action.get('replaces_controller_action_id') or controller_entry.get('replaces_controller_action_id'), 'replaces_router_scheduler_row_id': action.get('replaces_router_scheduler_row_id') or controller_entry.get('replaces_router_scheduler_row_id'), 'replacement_reason': action.get('replacement_reason') or controller_entry.get('replacement_reason'), 'original_order': action.get('original_order') or controller_entry.get('original_order'), 'role_recovery_transaction_id': action.get('role_recovery_transaction_id') or controller_entry.get('role_recovery_transaction_id'), 'role_no_output_reissue_attempt': action.get('role_no_output_reissue_attempt') or controller_entry.get('role_no_output_reissue_attempt'), 'max_role_no_output_reissue_attempts': action.get('max_role_no_output_reissue_attempts') or controller_entry.get('max_role_no_output_reissue_attempts'), 'target_no_output_role': action.get('target_no_output_role') or controller_entry.get('target_no_output_role'), 'controller_action_path': controller_entry.get('action_path'), 'controller_receipt_path': controller_entry.get('expected_receipt_path'), 'router_only_dependency_metadata': True, 'controller_table_contract': 'simple_work_board', 'created_at': controller_entry.get('created_at') or utc_now(), 'updated_at': utc_now()}
    existing_ledger = router._read_router_scheduler_ledger(project_root, run_root, run_state)
    existing_by_id = {str(item.get('row_id')): item for item in existing_ledger.get('rows', []) if isinstance(item, dict) and item.get('row_id')}
    existing = existing_by_id.get(row_id)
    if isinstance(existing, dict):
        row['created_at'] = existing.get('created_at') or row['created_at']
        if existing.get('router_state') == 'reconciled' and router_state in {'queued', 'waiting', 'receipt_done'}:
            row['router_state'] = 'reconciled'
            row['reconciled_at'] = existing.get('reconciled_at')
            row['reconciliation'] = existing.get('reconciliation')
    rows = [item for item in existing_ledger.get('rows', []) if isinstance(item, dict) and item.get('row_id') != row_id]
    rows.append(row)
    existing_ledger['rows'] = rows
    router._write_router_scheduler_ledger(project_root, run_root, run_state, existing_ledger)
    return row

def _update_router_scheduler_row(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, row_id: str, router_state: str, reconciliation: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    ledger = router._read_router_scheduler_ledger(project_root, run_root, run_state)
    rows: list[dict[str, Any]] = []
    for row in ledger.get('rows', []):
        if not isinstance(row, dict):
            continue
        if row.get('row_id') == row_id:
            existing_state = str(row.get('router_state') or '')
            if existing_state == 'reconciled' and router_state in {'queued', 'waiting', 'receipt_done'}:
                if reconciliation is not None:
                    existing_reconciliation = row.get('reconciliation')
                    if isinstance(existing_reconciliation, dict):
                        existing_reconciliation.update({'latest_receipt_sync': reconciliation})
                        row['reconciliation'] = existing_reconciliation
                    else:
                        row['reconciliation'] = {'latest_receipt_sync': reconciliation}
                row['updated_at'] = utc_now()
                rows.append(row)
                continue
            row['router_state'] = router_state
            row['updated_at'] = utc_now()
            if router_state == 'reconciled':
                row['reconciled_at'] = utc_now()
            if reconciliation is not None:
                row['reconciliation'] = reconciliation
        rows.append(row)
    ledger['rows'] = rows
    router._write_router_scheduler_ledger(project_root, run_root, run_state, ledger)

def _controller_action_open_for(router: ModuleType, run_root: Path, *, action_type: str | None=None, postcondition: str | None=None, idempotency_key: str | None=None, label: str | None=None) -> bool:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return False
    for path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        if action_type and entry.get('action_type') != action_type:
            continue
        if postcondition and _pending_action_postcondition(action) != postcondition:
            continue
        if idempotency_key and action.get('idempotency_key') != idempotency_key:
            continue
        if label and entry.get('label') != label:
            continue
        return True
    return False

def _router_ownership_counts(router: ModuleType, entries: list[dict[str, Any]]) -> dict[str, int]:
    _bind_router(router)
    counts: dict[str, int] = {'controller_receipt_done': 0, 'router_reclaim_pending': 0, 'router_reclaimed': 0, 'waiting_for_role': 0, 'blocked': 0}
    for item in entries:
        state = str(item.get('router_state') or 'unknown')
        counts[state] = counts.get(state, 0) + 1
    counts['total'] = len(entries)
    return counts

def _empty_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': ROUTER_OWNERSHIP_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'entries': [], 'counts': router._router_ownership_counts([]), 'controller_may_record_only_local_receipts': True, 'router_only_fields': ['router_state', 'workflow_owner', 'postcondition', 'artifact_refs', 'blocker_source']}

def _read_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = _router_ownership_ledger_path(run_root)
    ledger = read_json_if_exists(path)
    if ledger.get('schema_version') != ROUTER_OWNERSHIP_LEDGER_SCHEMA:
        return router._empty_router_ownership_ledger(project_root, run_root, run_state)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    ledger['entries'] = [item for item in entries if isinstance(item, dict)]
    ledger['counts'] = router._router_ownership_counts(ledger['entries'])
    return ledger

def _write_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    ledger.update({'schema_version': ROUTER_OWNERSHIP_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'entries': [item for item in entries if isinstance(item, dict)]})
    ledger['counts'] = router._router_ownership_counts(ledger['entries'])
    write_json(_router_ownership_ledger_path(run_root), ledger)
    run_state['router_ownership_ledger_path'] = project_relative(project_root, _router_ownership_ledger_path(run_root))
    return ledger

def _ensure_router_ownership_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    ledger = router._read_router_ownership_ledger(project_root, run_root, run_state)
    return router._write_router_ownership_ledger(project_root, run_root, run_state, ledger)

def _router_ownership_ledger_summary(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    ledger = read_json_if_exists(_router_ownership_ledger_path(run_root))
    if ledger.get('schema_version') != ROUTER_OWNERSHIP_LEDGER_SCHEMA:
        return {'exists': False, 'counts': router._router_ownership_counts([]), 'entries': []}
    entries = [item for item in ledger.get('entries') or [] if isinstance(item, dict)]
    return {'exists': True, 'path': str(_router_ownership_ledger_path(run_root)), 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') or router._router_ownership_counts(entries), 'entries': [{'entry_id': item.get('entry_id'), 'action_id': item.get('action_id'), 'action_type': item.get('action_type'), 'router_state': item.get('router_state'), 'workflow_owner': item.get('workflow_owner'), 'postcondition': item.get('postcondition'), 'updated_at': item.get('updated_at')} for item in entries]}

def _record_router_ownership_entry(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, action_type: str, router_state: str, workflow_owner: str, postcondition: str='', source: str, receipt_path: str | None=None, artifact_refs: dict[str, Any] | None=None, details: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    ledger = router._read_router_ownership_ledger(project_root, run_root, run_state)
    entry_id = action_id or f'{action_type}:{postcondition or router_state}'
    entry = {'entry_id': entry_id, 'schema_version': 'flowpilot.router_ownership_entry.v1', 'run_id': run_state.get('run_id'), 'action_id': action_id, 'action_type': action_type, 'router_state': router_state, 'workflow_owner': workflow_owner, 'postcondition': postcondition, 'source': source, 'receipt_path': receipt_path, 'artifact_refs': artifact_refs or {}, 'details': details or {}, 'updated_at': utc_now(), 'controller_may_write_this_entry': False}
    entries = [item for item in ledger.get('entries', []) if isinstance(item, dict) and item.get('entry_id') != entry_id]
    entries.append(entry)
    ledger['entries'] = entries
    router._write_router_ownership_ledger(project_root, run_root, run_state, ledger)
    return entry

def _controller_action_completion_class(router: ModuleType, action: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    action_type = str(action.get('action_type') or '')
    postcondition = _pending_action_postcondition(action)
    if _action_is_passive_wait_status(action):
        return {'kind': 'passive_wait_status', 'artifact_kind': '', 'postcondition': postcondition}
    if action_type == CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE:
        return {'kind': 'continuous_standby_monitor', 'artifact_kind': '', 'postcondition': ''}
    if action_type == WAIT_TARGET_REMINDER_ACTION_TYPE:
        return {'kind': 'wait_target_reminder', 'artifact_kind': '', 'postcondition': ''}
    if action_type == 'write_startup_mechanical_audit':
        return {'kind': 'router_owned_durable_artifact', 'artifact_kind': 'startup_mechanical_audit', 'postcondition': postcondition or 'startup_mechanical_audit_written'}
    if action_type in {'write_display_surface_status', 'sync_display_plan'}:
        return {'kind': 'display_status', 'artifact_kind': '', 'postcondition': postcondition}
    if action_type in {'deliver_system_card', 'deliver_system_card_bundle'} or action.get('to_role'):
        return {'kind': 'role_delivery_wait', 'artifact_kind': '', 'postcondition': postcondition}
    if postcondition:
        return {'kind': 'stateful_host_postcondition', 'artifact_kind': '', 'postcondition': postcondition}
    return {'kind': 'controller_local_receipt', 'artifact_kind': '', 'postcondition': ''}

def _controller_action_ledger_has_prompt_header(router: ModuleType, ledger: dict[str, Any]) -> bool:
    _bind_router(router)
    if ledger.get('schema_version') != CONTROLLER_ACTION_LEDGER_SCHEMA:
        return False
    if not isinstance(ledger.get('controller_table_prompt'), dict):
        return False
    keys = list(ledger)
    return 'controller_table_prompt' in keys and 'actions' in keys and (keys.index('controller_table_prompt') < keys.index('actions'))

def _write_controller_action_ledger(router: ModuleType, path: Path, ledger: dict[str, Any]) -> None:
    _bind_router(router)
    write_json_atomic(path, ledger, sort_keys=False, verify=True)

def _rebuild_controller_action_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    entries: list[dict[str, Any]] = []
    passive_waits: list[dict[str, Any]] = []
    if action_dir.exists():
        for path in sorted(action_dir.glob('*.json')):
            entry = _read_json_for_runtime_scan(path)
            if entry is None:
                continue
            if entry.get('schema_version') == CONTROLLER_ACTION_SCHEMA:
                summary = _controller_action_summary(entry)
                if _controller_action_is_ordinary_work_row(entry):
                    entries.append(summary)
                else:
                    passive_waits.append(summary)
    ledger = {'schema_version': CONTROLLER_ACTION_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'controller_table_prompt': _controller_table_prompt(), 'actions': entries, 'passive_waits': passive_waits, 'counts': _controller_action_counts(entries), 'passive_wait_count': len(passive_waits), 'controller_must_clear_pending_actions': True, 'controller_actions_are_executable_only': True, 'passive_waits_projected_via_status_not_work_board': True, 'router_must_not_mark_done_without_controller_receipt': True}
    router._write_controller_action_ledger(_controller_action_ledger_path(run_root), ledger)
    run_state['controller_action_ledger_path'] = project_relative(project_root, _controller_action_ledger_path(run_root))
    return ledger

def _ensure_controller_action_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = _controller_action_ledger_path(run_root)
    if path.exists():
        try:
            ledger = read_json(path)
            if router._controller_action_ledger_has_prompt_header(ledger):
                run_state['controller_action_ledger_path'] = project_relative(project_root, path)
                return ledger
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
            write_lock = _json_write_lock_liveness(path)
            if write_lock.get('active', write_lock.get('fresh', False)):
                raise RouterLedgerWriteInProgress(path, write_lock, str(exc)) from exc
            pass
    return router._rebuild_controller_action_ledger(project_root, run_root, run_state)

def _controller_action_ledger_summary(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = _controller_action_ledger_path(run_root)
    try:
        ledger = read_json_if_exists(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = _json_write_lock_liveness(path)
        return {'exists': path.exists(), 'valid_json': False, 'write_in_progress': write_lock.get('active', write_lock.get('fresh', False)), 'write_lock': write_lock, 'error': str(exc), 'path': str(path), 'counts': _controller_action_counts([]), 'active_work_count': 0, 'history_done_count': 0, 'actions': [], 'passive_waits': [], 'pending_action_ids': [], 'waiting_action_ids': [], 'passive_wait_action_ids': []}
    if ledger.get('schema_version') != CONTROLLER_ACTION_LEDGER_SCHEMA:
        return {'exists': False, 'valid_json': True, 'counts': _controller_action_counts([]), 'active_work_count': 0, 'history_done_count': 0, 'actions': [], 'passive_waits': [], 'passive_wait_action_ids': []}
    actions = ledger.get('actions') if isinstance(ledger.get('actions'), list) else []
    passive_waits = ledger.get('passive_waits') if isinstance(ledger.get('passive_waits'), list) else []
    valid_actions = [item for item in actions if isinstance(item, dict)]
    valid_passive_waits = [item for item in passive_waits if isinstance(item, dict)]
    counts = ledger.get('counts') or _controller_action_counts(valid_actions)
    return {'exists': True, 'valid_json': True, 'path': str(_controller_action_ledger_path(run_root)), 'updated_at': ledger.get('updated_at'), 'counts': counts, 'active_work_count': _controller_action_active_work_count(counts), 'history_done_count': int(counts.get('done', 0) or 0), 'done_rows_are_audit_history': True, 'passive_wait_count': int(ledger.get('passive_wait_count') or len(valid_passive_waits)), 'passive_waits': valid_passive_waits, 'passive_wait_action_ids': [item.get('action_id') for item in valid_passive_waits if item.get('action_id')], 'pending_action_ids': [item.get('action_id') for item in valid_actions if item.get('status') in {'pending', 'in_progress'}], 'waiting_action_ids': [item.get('action_id') for item in valid_actions if item.get('status') == 'waiting']}

def _write_controller_action_entry(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action = router._prepare_router_scheduled_action(project_root, run_root, run_state, action)
    passive_wait_status = _action_is_passive_wait_status(action)
    projection_kind = _controller_action_projection_kind(action)
    action_id = str(action.get('controller_action_id') or _controller_action_id_for_action(action))
    action_path = _controller_action_path(run_root, action_id)
    receipt_path = _controller_receipt_path(run_root, action_id)
    receipt_rel = project_relative(project_root, receipt_path)
    controller_receipt_required = not passive_wait_status and action.get('action_type') not in {'await_card_return_event', 'await_card_bundle_return_event', 'await_role_decision'}
    created = False
    existing = read_json_if_exists(action_path)
    now = utc_now()
    if existing.get('schema_version') == CONTROLLER_ACTION_SCHEMA:
        entry = existing
        entry['seen_count'] = int(entry.get('seen_count') or 0) + 1
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES:
            entry['status'] = entry.get('status') or _controller_action_initial_status(action)
    else:
        created = True
        entry = {'schema_version': CONTROLLER_ACTION_SCHEMA, 'action_id': action_id, 'run_id': run_state.get('run_id'), 'action_type': action.get('action_type'), 'label': action.get('label'), 'summary': action.get('summary'), 'status': _controller_action_initial_status(action), 'created_at': now, 'seen_count': 1, 'source_action_id': action.get('action_id'), 'to_role': action.get('to_role'), 'allowed_reads': action.get('allowed_reads') or [], 'allowed_writes': action.get('allowed_writes') or [], 'allowed_external_events': action.get('allowed_external_events') or [], 'dependencies': [], 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'scope_kind': action.get('scope_kind'), 'scope_id': action.get('scope_id'), 'controller_visibility': 'router_action_metadata_only', 'sealed_body_reads_allowed': bool(action.get('sealed_body_reads_allowed', False)), 'action_path': project_relative(project_root, action_path), 'expected_receipt_path': receipt_rel, 'controller_receipt_required': controller_receipt_required, 'controller_projection_kind': projection_kind, 'ordinary_controller_work_row': not passive_wait_status, 'router_must_not_mark_done_without_controller_receipt': controller_receipt_required, 'action': action}
    entry['updated_at'] = now
    entry['last_seen_at'] = now
    required_deliverables = _controller_action_required_deliverables(project_root, run_root, run_state, action)
    deliverable_contract = _controller_deliverable_contract(required_deliverables)
    if required_deliverables:
        action['required_deliverables'] = required_deliverables
    entry['completion_class'] = router._controller_action_completion_class(action)
    entry['required_deliverables'] = required_deliverables
    entry['deliverable_contract'] = deliverable_contract
    if required_deliverables and (not entry.get('deliverable_status')):
        entry['deliverable_status'] = 'required'
        entry['deliverable_repair_attempts'] = int(entry.get('deliverable_repair_attempts') or 0)
        entry['max_deliverable_repair_attempts'] = CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS
    if action.get('repair_of_controller_action_id'):
        entry['repair_of_controller_action_id'] = action.get('repair_of_controller_action_id')
        entry['repair_target_action_type'] = action.get('repair_target_action_type')
        entry['repair_attempt'] = action.get('repair_attempt')
    for replacement_field in ('replaces', 'replaces_controller_action_id', 'replaces_router_scheduler_row_id', 'replacement_reason', 'original_order', 'role_recovery_transaction_id', 'role_recovery_replay_kind', 'target_recovered_role', 'role_no_output_reissue_attempt', 'max_role_no_output_reissue_attempts', 'target_no_output_role'):
        if action.get(replacement_field) not in (None, '', []):
            entry[replacement_field] = action.get(replacement_field)
    controller_action_view = _controller_ledger_action_view(action, action_id=action_id, receipt_path=receipt_rel, controller_receipt_required=controller_receipt_required)
    entry['router_scheduler_row_id'] = action.get('router_scheduler_row_id')
    entry['scope_kind'] = action.get('scope_kind')
    entry['scope_id'] = action.get('scope_id')
    entry['controller_receipt_required'] = controller_receipt_required
    entry['controller_projection_kind'] = projection_kind
    entry['ordinary_controller_work_row'] = not passive_wait_status
    entry['router_must_not_mark_done_without_controller_receipt'] = controller_receipt_required
    entry['controller_completion_command'] = controller_action_view.get('controller_completion_command')
    entry['controller_completion_mode'] = controller_action_view.get('controller_completion_mode')
    entry['router_pending_apply_required'] = controller_action_view.get('router_pending_apply_required')
    entry['action'] = controller_action_view
    entry['expected_receipt_path'] = receipt_rel
    write_json(action_path, entry)
    router._record_router_scheduler_row(project_root, run_root, run_state, action, entry)
    action['controller_action_id'] = action_id
    action['controller_action_path'] = project_relative(project_root, action_path)
    action['controller_receipt_path'] = project_relative(project_root, receipt_path)
    if isinstance(run_state.get('pending_action'), dict):
        pending = run_state['pending_action']
        if pending.get('action_id') == action.get('action_id') or pending.get('label') == action.get('label'):
            pending.update({'controller_action_id': action_id, 'controller_action_path': project_relative(project_root, action_path), 'controller_receipt_path': project_relative(project_root, receipt_path)})
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    if created:
        append_history(run_state, 'router_recorded_controller_action_entry', {'controller_action_id': action_id, 'action_type': action.get('action_type'), 'status': entry.get('status')})
    return entry

def _write_controller_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    if status not in CONTROLLER_RECEIPT_STATUSES:
        raise RouterError(f'unsupported controller receipt status: {status}')
    action_path = _controller_action_path(run_root, action_id)
    action = read_json_if_exists(action_path)
    if action.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        raise RouterError(f'controller action is missing: {action_id}')
    receipt = {'schema_version': CONTROLLER_RECEIPT_SCHEMA, 'run_id': run_state.get('run_id'), 'action_id': action_id, 'action_type': action.get('action_type'), 'status': status, 'recorded_by': 'controller', 'recorded_at': utc_now(), 'controller_visibility': 'receipt_metadata_only', 'payload': payload or {}}
    write_json(_controller_receipt_path(run_root, action_id), receipt)
    _append_router_daemon_event(run_root, 'controller_receipt_recorded', {'action_id': action_id, 'status': status, 'receipt_path': project_relative(project_root, _controller_receipt_path(run_root, action_id))})
    router._reconcile_controller_receipts(project_root, run_root, run_state)
    return receipt

def _maybe_write_controller_receipt_for_pending(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any], *, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    action_id = str(pending.get('controller_action_id') or '')
    if not action_id:
        return None
    return router._write_controller_receipt(project_root, run_root, run_state, action_id=action_id, status=status, payload=payload)

def _reconcile_controller_receipts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    receipt_dir = _controller_receipts_dir(run_root)
    reconciled = 0
    blocked = 0
    if receipt_dir.exists():
        for receipt_path in sorted(receipt_dir.glob('*.json')):
            receipt = read_json_if_exists(receipt_path)
            if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA:
                continue
            action_id = str(receipt.get('action_id') or '')
            status = str(receipt.get('status') or '')
            if not action_id or status not in CONTROLLER_RECEIPT_STATUSES:
                continue
            action_path = _controller_action_path(run_root, action_id)
            action = read_json_if_exists(action_path)
            if action.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
                continue
            previous_status = str(action.get('status') or '')
            preserve_router_status = status == 'done' and previous_status in CONTROLLER_ACTION_RECEIPT_PRESERVED_STATUSES
            if preserve_router_status:
                action['receipt_status'] = status
            else:
                action['status'] = status
            action['receipt_path'] = project_relative(project_root, receipt_path)
            action['receipt_recorded_at'] = receipt.get('recorded_at')
            action['updated_at'] = utc_now()
            if status == 'done' and (not preserve_router_status):
                action['completed_at'] = receipt.get('recorded_at')
            if status == 'blocked':
                blocked += 1
                action['blocked_at'] = receipt.get('recorded_at')
                action['blocked_payload'] = receipt.get('payload') or {}
            write_json(action_path, action)
            row_id = str(action.get('router_scheduler_row_id') or '')
            if row_id:
                router_state = 'waiting' if preserve_router_status and previous_status == 'repair_pending' else 'superseded' if preserve_router_status and previous_status == 'superseded' else 'reconciled' if preserve_router_status and previous_status == 'resolved' else 'receipt_done' if status == 'done' else 'blocked' if status == 'blocked' else 'skipped' if status == 'skipped' else 'waiting'
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state=router_state, reconciliation={'receipt_status': status, 'receipt_path': project_relative(project_root, receipt_path), 'receipt_recorded_at': receipt.get('recorded_at')})
            reconciled += 1
    ledger = router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    return {'reconciled_receipts': reconciled, 'blocked_receipts': blocked, 'ledger_counts': ledger.get('counts')}

def _router_scheduler_row_for_controller_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return {}
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    for row in scheduler.get('rows', []) if isinstance(scheduler.get('rows'), list) else []:
        if isinstance(row, dict) and row.get('row_id') == row_id:
            return row
    return {}

def _done_controller_receipt_for_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_id = str(entry.get('action_id') or '').strip()
    if not action_id:
        return {}
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA:
        return {}
    if receipt.get('status') != 'done':
        return {}
    if str(receipt.get('action_id') or '') != action_id:
        return {}
    return receipt

def _apply_stateful_receipt_postcondition(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(pending_action.get('action_type') or '')
    startup_bootloader_receipt = router._apply_startup_bootloader_receipt_effects(project_root, run_root, run_state, pending_action, receipt_payload)
    if startup_bootloader_receipt.get('applied') or startup_bootloader_receipt.get('reason') != 'not_bootloader_action':
        return startup_bootloader_receipt
    durable_reclaim = _reclaim_router_owned_postcondition_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload)
    if durable_reclaim.get('applied') or durable_reclaim.get('action_class', {}).get('kind') == 'router_owned_durable_artifact':
        return durable_reclaim
    if action_type == 'load_role_recovery_state':
        router._load_role_recovery_state(project_root, run_root, run_state)
        return {'applied': True, 'postcondition': 'role_recovery_state_loaded'}
    if action_type == 'recover_role_agents':
        if 'recovered_role_agents' in receipt_payload or 'role_agents' in receipt_payload:
            router._write_role_recovery_report(project_root, run_root, run_state, receipt_payload)
            return {'applied': True, 'postcondition': 'role_recovery_roles_restored', 'source': 'controller_receipt_role_recovery_report_write'}
        return router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='controller_receipt_role_recovery_report_reclaim')
    if action_type == 'rehydrate_role_agents':
        router._write_resume_role_rehydration_report(project_root, run_root, run_state, receipt_payload)
        return {'applied': True, 'postcondition': 'resume_roles_restored'}
    if action_type == 'confirm_controller_core_boundary' or (action_type == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and str(pending_action.get('repair_target_action_type') or '') == 'confirm_controller_core_boundary'):
        return _sync_controller_boundary_confirmation_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload, source='controller_receipt_reconciliation')
    if action_type == 'write_display_surface_status':
        confirmation = router._display_confirmation_for_action(receipt_payload, pending_action)
        router._write_display_surface_status(project_root, run_root, run_state, confirmation, receipt_payload)
        router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state.setdefault('flags', {})['startup_display_status_written'] = True
        return {'applied': True, 'postcondition': 'startup_display_status_written'}
    if action_type == 'deliver_mail':
        return _fold_mail_delivery_postcondition(project_root, run_root, run_state, pending_action, receipt_payload, source='controller_receipt_mail_delivery_fold')
    return {'applied': False, 'reason': 'unsupported_stateful_controller_receipt', 'action_type': action_type}

def _pending_return_matches_wait_target_reminder(router: ModuleType, record: dict[str, Any], action: dict[str, Any]) -> bool:
    _bind_router(router)
    expected_return_path = str(action.get('expected_return_path') or '')
    target_role = str(action.get('target_role') or action.get('waiting_for_role') or '')
    if expected_return_path and str(record.get('expected_return_path') or '') == expected_return_path:
        return True
    if target_role and str(record.get('target_role') or '') != target_role:
        return False
    for key in ('card_bundle_id', 'delivery_attempt_id', 'card_id', 'card_return_event'):
        action_value = str(action.get(key) or '')
        if action_value and str(record.get(key) or '') == action_value:
            return True
    source_identity = action.get('source_wait_identity') if isinstance(action.get('source_wait_identity'), dict) else {}
    identity_expected_path = str(source_identity.get('expected_return_path') or '')
    return bool(identity_expected_path and str(record.get('expected_return_path') or '') == identity_expected_path)

def _mark_pending_return_wait_reminded(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any], *, delivered_at: str, reminder_hash: str, receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    ledger = _read_return_event_ledger(run_root, run_id)
    changed = False
    reminded_ids: list[str] = []
    for record in ledger.setdefault('pending_returns', []):
        if not isinstance(record, dict):
            continue
        if not router._pending_return_matches_wait_target_reminder(record, action):
            continue
        if record.get('status') in {None, 'pending', 'awaiting_return', 'returned'}:
            record['status'] = 'reminded'
        record['last_wait_reminder_at'] = delivered_at
        record['last_wait_reminder_sha256'] = reminder_hash
        history = record.setdefault('wait_reminder_history', [])
        if isinstance(history, list):
            history.append({'at': delivered_at, 'reminder_text_sha256': reminder_hash, 'controller_action_id': action.get('controller_action_id'), 'delivered_to_role': receipt_payload.get('delivered_to_role')})
        reminded_ids.append(str(record.get('return_id') or record.get('card_bundle_id') or record.get('delivery_attempt_id') or ''))
        changed = True
    if changed:
        write_json(_return_event_ledger_path(run_root), ledger)
    return {'changed': changed, 'reminded_return_ids': [item for item in reminded_ids if item]}

def _apply_wait_target_reminder_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del project_root
    target_role = str(action.get('target_role') or action.get('waiting_for_role') or '').strip()
    delivered_to = str(receipt_payload.get('delivered_to_role') or receipt_payload.get('target_role') or '').strip()
    if target_role and delivered_to != target_role:
        return {'applied': False, 'reason': 'wait_target_reminder_wrong_role', 'target_role': target_role, 'delivered_to_role': delivered_to or None}
    expected_hash = str(action.get('reminder_text_sha256') or '')
    actual_hash = str(receipt_payload.get('reminder_text_sha256') or '')
    if not expected_hash or actual_hash != expected_hash:
        return {'applied': False, 'reason': 'wait_target_reminder_text_hash_mismatch', 'expected_reminder_text_sha256': expected_hash or None, 'actual_reminder_text_sha256': actual_hash or None}
    if receipt_payload.get('sealed_body_reads') is not False:
        return {'applied': False, 'reason': 'wait_target_reminder_sealed_body_boundary_not_confirmed'}
    delivered_at = str(receipt_payload.get('delivered_at') or utc_now())
    liveness_payload = receipt_payload.get('liveness_probe') if isinstance(receipt_payload.get('liveness_probe'), dict) else {}
    liveness_result = str(receipt_payload.get('liveness_probe_result') or liveness_payload.get('result') or '').strip()
    liveness_checked_at = str(receipt_payload.get('liveness_probe_checked_at') or liveness_payload.get('checked_at') or delivered_at)
    if action.get('fresh_liveness_probe_required') and (not liveness_result):
        return {'applied': False, 'reason': 'wait_target_reminder_missing_fresh_liveness_probe'}
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    pending_updated = False
    if pending and _action_is_passive_wait_status(pending):
        current_identity = router._wait_target_identity(pending, router._pending_wait_summary(run_state, project_root=None))
        if current_identity == action.get('source_wait_identity'):
            pending['last_wait_reminder_at'] = delivered_at
            pending['wait_reminder_text'] = action.get('reminder_text')
            pending['wait_reminder_text_sha256'] = expected_hash
            reminder_history = pending.setdefault('wait_reminder_history', [])
            if isinstance(reminder_history, list):
                reminder_history.append({'at': delivered_at, 'target_role': target_role, 'reminder_text_sha256': expected_hash, 'controller_action_id': action.get('controller_action_id')})
            if liveness_result:
                pending['last_liveness_probe'] = {'checked_at': liveness_checked_at, 'result': liveness_result, 'evidence_path': liveness_payload.get('evidence_path') or receipt_payload.get('liveness_probe_evidence_path')}
                pending['liveness_probe_result'] = liveness_result
            run_state['pending_action'] = pending
            pending_updated = True
    return_update = {'changed': False, 'reminded_return_ids': []}
    if str(action.get('wait_class') or '') == 'ack':
        return_update = router._mark_pending_return_wait_reminded(run_root, str(run_state['run_id']), action, delivered_at=delivered_at, reminder_hash=expected_hash, receipt_payload=receipt_payload)
    append_history(run_state, 'router_recorded_wait_target_reminder_receipt', {'target_role': target_role, 'wait_class': action.get('wait_class'), 'source_wait_action_type': action.get('source_wait_action_type'), 'pending_wait_updated': pending_updated, 'return_event_ledger_updated': return_update.get('changed')})
    return {'applied': True, 'source': 'wait_target_reminder_receipt', 'target_role': target_role, 'wait_class': action.get('wait_class'), 'delivered_at': delivered_at, 'pending_wait_updated': pending_updated, 'return_event_ledger_update': return_update}

def _boot_action_meta(router: ModuleType, action_type: str) -> dict[str, Any] | None:
    _bind_router(router)
    if action_type == 'load_router':
        return {'action_type': 'load_router', 'flag': 'router_loaded', 'label': 'bootloader_router_loaded', 'actor': 'bootloader'}
    for item in BOOT_ACTIONS:
        if item.get('action_type') == action_type:
            return item
    return None

def _matching_bootstrap_pending_action(router: ModuleType, bootstrap_state: dict[str, Any], action: dict[str, Any]) -> bool:
    _bind_router(router)
    pending = bootstrap_state.get('pending_action')
    if not isinstance(pending, dict):
        return False
    for key in ('controller_action_id', 'router_scheduler_row_id', 'action_id'):
        if pending.get(key) and pending.get(key) == action.get(key):
            return True
    return bool(pending.get('action_type') and pending.get('action_type') == action.get('action_type'))

def _apply_startup_bootloader_receipt_effects(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get('action_type') or '')
    action_meta = router._boot_action_meta(action_type)
    if action_meta is None:
        return {'applied': False, 'reason': 'not_bootloader_action'}
    if str(action.get('scope_kind') or '') != 'startup' and (not router._daemon_scheduled_bootloader_action(action)):
        return {'applied': False, 'reason': 'not_startup_bootloader_scheduler_row'}
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    flag = str(action_meta.get('flag') or _pending_action_postcondition(action) or '')
    result: dict[str, Any] = {'applied': True, 'source': 'startup_bootloader_controller_receipt', 'postcondition': flag, 'action_type': action_type}
    if action_type == 'open_startup_intake_ui' and str(receipt_payload.get('source') or '') != 'startup_daemon_bootloader_apply':
        result.update(router._apply_startup_intake_result_to_bootstrap(project_root, bootstrap, receipt_payload))
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
    elif action_type == 'emit_startup_banner':
        banner = router._startup_banner_display()
        confirmation = router._display_confirmation_for_action(receipt_payload, action)
        banner['dialog_display_confirmation'] = confirmation
        bootstrap['startup_banner_path'] = banner['display_path']
        bootstrap['startup_banner_display'] = banner
        bootstrap['startup_banner_dialog_display_confirmation'] = confirmation
        run_state.setdefault('flags', {})['banner_emitted'] = True
        result['display_text_sha256'] = confirmation.get('display_text_sha256')
    elif action_type == 'start_role_slots':
        role_slots = router._normalize_role_agent_records(bootstrap, receipt_payload)
        write_json(run_root / 'crew_ledger.json', {'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'background_agents_mode': (bootstrap.get('startup_answers') or {}).get('background_agents'), 'role_slots': role_slots, 'created_at': utc_now()})
        crew_memory_root = run_root / 'crew_memory'
        crew_memory_root.mkdir(parents=True, exist_ok=True)
        for role in CREW_ROLE_KEYS:
            write_json(crew_memory_root / f'{role}.json', router._create_empty_role_memory(str(run_state['run_id']), role))
        _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), role_slots, default_lifecycle_phase='fresh_spawn', resume_tick_id='manual-resume', source_action='start_role_slots')
        write_json(run_root / 'role_core_prompt_delivery.json', router._role_core_prompt_delivery_payload(project_root, run_root, str(run_state['run_id']), source_action='start_role_slots'))
        bootstrap.setdefault('flags', {})['role_core_prompts_injected'] = True
        run_state.setdefault('flags', {})['roles_started'] = True
        run_state.setdefault('flags', {})['role_core_prompts_injected'] = True
        result['coalesced_postconditions'] = ['roles_started', 'role_core_prompts_injected']
    elif action_type == 'create_heartbeat_automation':
        _write_host_heartbeat_binding(project_root, run_root, run_state, receipt_payload)
        run_state.setdefault('flags', {})['continuation_binding_recorded'] = True
        run_state.setdefault('events', []).append({'event': 'host_records_heartbeat_binding', 'summary': EXTERNAL_EVENTS['host_records_heartbeat_binding']['summary'], 'payload': receipt_payload, 'recorded_at': utc_now(), 'source_action': action_type, 'startup_phase': 'bootloader_controller_receipt'})
    elif action_type == 'load_controller_core':
        if not _formal_router_daemon_ready(project_root, run_root):
            return {'applied': False, 'reason': 'startup_router_daemon_not_ready_for_controller_core', 'action_type': action_type, 'postcondition': flag}
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        run_state['status'] = 'controller_ready'
        run_state['holder'] = 'controller'
        run_state.setdefault('flags', {})['controller_core_loaded'] = True
        boundary_reconciliation = router._record_controller_boundary_confirmation_from_core_load(project_root, run_root, run_state, action, receipt_payload, source='load_controller_core_receipt_reconciliation')
        result['controller_boundary_confirmation'] = boundary_reconciliation.get('controller_boundary_confirmation')
        result['coalesced_postconditions'] = sorted(set(result.get('coalesced_postconditions') or []) | {'controller_role_confirmed'})
        result['source'] = 'startup_bootloader_controller_receipt'
    elif str(receipt_payload.get('source') or '') == 'startup_daemon_bootloader_apply':
        bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
        if flag and (not (receipt_payload.get('bootstrap_flag_satisfied') or bootstrap_flags.get(flag))):
            return {'applied': False, 'reason': 'startup_bootloader_receipt_postcondition_missing', 'action_type': action_type, 'postcondition': flag}
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        result['bootstrap_flag_satisfied'] = bool(flag and bootstrap_flags.get(flag))
        result['source'] = 'startup_bootloader_controller_receipt'
    else:
        return {'applied': False, 'reason': 'unsupported_startup_bootloader_receipt_action', 'action_type': action_type}
    if flag:
        bootstrap.setdefault('flags', {})[flag] = True
        run_state.setdefault('flags', {})[flag] = True
    if router._matching_bootstrap_pending_action(bootstrap, action):
        bootstrap['pending_action'] = None
        result['cleared_bootstrap_pending_action'] = True
    append_history(bootstrap, 'router_reconciled_startup_bootloader_receipt', {'action_type': action_type, 'postcondition': flag, 'controller_action_id': action.get('controller_action_id'), 'router_scheduler_row_id': action.get('router_scheduler_row_id')})
    router.save_bootstrap_state(project_root, bootstrap)
    router.save_run_state(run_root, run_state)
    return result

def _clear_pending_after_reconciled_controller_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, pending_action: dict[str, Any], receipt: dict[str, Any], applied_postcondition: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    if str(pending_action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=pending_action, receipt=receipt, applied_postcondition=applied_postcondition)
    run_state['pending_action'] = None
    blocker_resolution = router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=pending_action, entry={'action_id': receipt.get('action_id'), 'router_scheduler_row_id': pending_action.get('router_scheduler_row_id')}, reconciliation=applied_postcondition)
    append_history(run_state, 'router_reconciled_pending_controller_action_receipt', {'action_type': pending_action.get('action_type'), 'label': pending_action.get('label'), 'controller_action_id': receipt.get('action_id'), 'receipt_status': receipt.get('status'), 'applied_postcondition': applied_postcondition or {}, 'control_blocker_resolution': blocker_resolution})
    router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_receipt_reconciliation')
    router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_receipt_reconciliation', update_display=True)
    router.save_run_state(run_root, run_state)
    return {'changed': True, 'cleared_pending': True, 'receipt_status': receipt.get('status')}

def _reconcile_pending_controller_action_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    pending_action = run_state.get('pending_action')
    if not isinstance(pending_action, dict):
        return {'changed': False}
    receipt = _receipt_for_pending_controller_action(run_root, pending_action)
    if not receipt:
        return {'changed': False}
    status = str(receipt.get('status') or '')
    if status == 'waiting':
        return {'changed': False, 'waiting_receipt': True}
    payload = receipt.get('payload') if isinstance(receipt.get('payload'), dict) else {}
    action_type = str(pending_action.get('action_type') or receipt.get('action_type') or '')
    if status == 'blocked':
        router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_blocked', error_message=f'Controller reported active action {action_type} blocked before Router could continue.', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
        return {'changed': True, 'blocked': True, 'receipt_status': status}
    if status == 'skipped':
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt)
    if status != 'done':
        return {'changed': False, 'unsupported_receipt_status': status}
    action_class = router._controller_action_completion_class(pending_action)
    router._record_router_ownership_entry(project_root, run_root, run_state, action_id=str(receipt.get('action_id') or ''), action_type=action_type, router_state='controller_receipt_done', workflow_owner='router', postcondition=str(action_class.get('postcondition') or _pending_action_postcondition(pending_action) or ''), source='controller_receipt_reconciliation', receipt_path=project_relative(project_root, _controller_receipt_path(run_root, str(receipt.get('action_id') or ''))), details={'action_class': action_class, 'controller_receipt_is_local_evidence_only': True, 'controller_receipt_payload': payload})
    if action_class.get('kind') == 'display_status' and action_type == 'sync_display_plan':
        try:
            sync_payload = router._apply_sync_display_plan_state(project_root, run_root, run_state, pending_action, payload)
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_incomplete_for_display_status', error_message=f'Controller receipt for {action_type} was marked done, but Router could not apply the required display/status fact: {exc}', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
            return {'changed': True, 'blocked': True, 'receipt_status': status}
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition={'applied': True, 'source': 'router_owned_display_status_reclaim', 'projection_hash': sync_payload.get('projection_hash'), 'display_plan_path': sync_payload.get('display_plan_path')})
    postcondition = _pending_action_postcondition(pending_action)
    if postcondition and (not _pending_action_postcondition_satisfied(run_state, postcondition) or action_type == 'deliver_mail'):
        try:
            applied = router._apply_stateful_receipt_postcondition(project_root, run_root, run_state, pending_action, payload)
        except RouterLedgerWriteInProgress:
            raise
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            applied = {'applied': False, 'reason': str(exc), 'repairable': bool(_controller_action_required_deliverables(project_root, run_root, run_state, pending_action)), 'missing_deliverables': _controller_action_required_deliverables(project_root, run_root, run_state, pending_action)}
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, apply_result=applied, source='controller_action_receipt_incomplete_for_stateful_action')
            if repair.get('scheduled'):
                router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_deliverable_repair_scheduled')
                router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_deliverable_repair_scheduled', update_display=True)
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_scheduled': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_action_type': CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE}
            if repair.get('blocked'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_budget_exhausted': True}
            if repair.get('pending_repair'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_pending': True, 'receipt_status': status, 'postcondition': postcondition, 'pending_repair_action_id': repair.get('pending_repair_action_id')}
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_incomplete_for_stateful_action', error_message=f'Controller receipt for {action_type} was marked done, but Router could not apply required postcondition {postcondition}: {exc}', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'postcondition': postcondition, 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
            return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition}
        if not applied.get('applied') or not _pending_action_postcondition_satisfied(run_state, postcondition):
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, apply_result=applied, source='controller_action_receipt_missing_stateful_postcondition')
            if repair.get('scheduled'):
                router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_deliverable_repair_scheduled')
                router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_deliverable_repair_scheduled', update_display=True)
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_scheduled': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_action_type': CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE}
            if repair.get('blocked'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_budget_exhausted': True}
            if repair.get('pending_repair'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_pending': True, 'receipt_status': status, 'postcondition': postcondition, 'pending_repair_action_id': repair.get('pending_repair_action_id')}
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_missing_stateful_postcondition', error_message=f'Controller receipt for {action_type} was marked done, but Router postcondition {postcondition} is still not satisfied.', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'postcondition': postcondition, 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label'), 'apply_result': applied})
            return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition}
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition=applied)
    return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt)

def _apply_done_controller_receipt_effects(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    payload = receipt.get('payload') if isinstance(receipt.get('payload'), dict) else {}
    action_type = str(action.get('action_type') or receipt.get('action_type') or '')
    startup_bootloader_receipt = router._apply_startup_bootloader_receipt_effects(project_root, run_root, run_state, action, payload)
    if startup_bootloader_receipt.get('applied') or startup_bootloader_receipt.get('reason') != 'not_bootloader_action':
        return startup_bootloader_receipt
    if action_type == WAIT_TARGET_REMINDER_ACTION_TYPE:
        return router._apply_wait_target_reminder_receipt(project_root, run_root, run_state, action, payload)
    action_class = router._controller_action_completion_class(action)
    if action_class.get('kind') == 'display_status' and action_type == 'sync_display_plan':
        sync_payload = router._apply_sync_display_plan_state(project_root, run_root, run_state, action, payload)
        return {'applied': True, 'source': 'router_owned_display_status_reclaim', 'projection_hash': sync_payload.get('projection_hash'), 'display_plan_path': sync_payload.get('display_plan_path')}
    postcondition = _pending_action_postcondition(action)
    if postcondition and (not _pending_action_postcondition_satisfied(run_state, postcondition) or action_type == 'deliver_mail'):
        applied = router._apply_stateful_receipt_postcondition(project_root, run_root, run_state, action, payload)
        if not applied.get('applied') or not _pending_action_postcondition_satisfied(run_state, postcondition):
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=action, receipt=receipt, apply_result=applied, source='scheduled_controller_action_receipt_missing_stateful_postcondition')
            if repair.get('scheduled') or repair.get('blocked'):
                result = {'applied': False, 'reason': 'deliverable_repair_scheduled' if repair.get('scheduled') else 'deliverable_repair_budget_exhausted', 'postcondition': postcondition, 'apply_result': applied, 'repair': repair}
                result['repair_scheduled'] = bool(repair.get('scheduled'))
                result['blocked'] = bool(repair.get('blocked'))
                return result
            if repair.get('pending_repair'):
                return {'applied': False, 'reason': 'deliverable_repair_pending', 'postcondition': postcondition, 'apply_result': applied, 'repair': repair, 'repair_pending': True}
            return {'applied': False, 'reason': 'postcondition_not_satisfied', 'postcondition': postcondition, 'apply_result': applied}
        if str(action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
            _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=action, receipt=receipt, applied_postcondition=applied)
        return applied
    if str(action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and postcondition and _pending_action_postcondition_satisfied(run_state, postcondition):
        applied = {'applied': True, 'source': 'repair_postcondition_already_satisfied', 'postcondition': postcondition}
        _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=action, receipt=receipt, applied_postcondition=applied)
        return applied
    return {'applied': True, 'source': 'controller_local_receipt'}

def _scheduler_row_reconciliation_for_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return None
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    for row in scheduler.get('rows', []) if isinstance(scheduler.get('rows'), list) else []:
        if not isinstance(row, dict) or row.get('row_id') != row_id:
            continue
        reconciliation = row.get('reconciliation') if isinstance(row.get('reconciliation'), dict) else {}
        if row.get('router_state') == 'reconciled' and reconciliation.get('applied'):
            return dict(reconciliation)
    return None

def _backfill_scheduler_row_from_reconciled_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], *, source: str) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return {'changed': False, 'reason': 'controller_action_has_no_router_scheduler_row'}
    if not (entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at')):
        return {'changed': False, 'reason': 'controller_action_not_reconciled'}
    row = router._router_scheduler_row_for_controller_entry(run_root, entry)
    if not row:
        return {'changed': False, 'reason': 'router_scheduler_row_missing', 'row_id': row_id}
    if row.get('router_state') == 'reconciled':
        return {'changed': False, 'reason': 'router_scheduler_row_already_reconciled', 'row_id': row_id}
    reconciliation = dict(entry.get('router_reconciliation')) if isinstance(entry.get('router_reconciliation'), dict) else {}
    reconciliation.setdefault('applied', True)
    reconciliation.setdefault('source', source)
    reconciliation['scheduler_backfill_source'] = source
    reconciliation['controller_action_id'] = str(entry.get('action_id') or '')
    reconciliation['controller_action_reconciliation_status'] = entry.get('router_reconciliation_status')
    if entry.get('router_reconciled_at'):
        reconciliation['controller_action_reconciled_at'] = entry.get('router_reconciled_at')
    router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=reconciliation)
    return {'changed': True, 'row_id': row_id, 'reconciliation': reconciliation}

def _canonicalize_legacy_startup_daemon_reconciliation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    current = entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else {}
    source = current.get('source')
    if source == 'startup_bootloader_controller_receipt' and current.get('postcondition'):
        return {'applied': False, 'reason': 'startup_receipt_owner_already_complete'}
    if source not in {'startup_daemon_bootloader_postcondition', 'startup_bootloader_controller_receipt'}:
        return {'applied': False, 'reason': 'not_legacy_startup_daemon_owner'}
    if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA or receipt.get('status') != 'done':
        return {'applied': False, 'reason': 'startup_receipt_missing_or_not_done'}
    if not router._daemon_scheduled_bootloader_action(action):
        return {'applied': False, 'reason': 'not_daemon_scheduled_bootloader_action'}
    action_type = str(action.get('action_type') or entry.get('action_type') or '')
    action_meta = router._boot_action_meta(action_type)
    if action_meta is None:
        return {'applied': False, 'reason': 'not_bootloader_action'}
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    flag = str(action_meta.get('flag') or _pending_action_postcondition(action) or '')
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    run_flags = run_state.setdefault('flags', {})
    if flag and (not (bootstrap_flags.get(flag) or run_flags.get(flag))):
        return {'applied': False, 'reason': 'legacy_startup_postcondition_not_satisfied', 'postcondition': flag, 'action_type': action_type}
    if flag:
        run_flags[flag] = True
    canonical = dict(current)
    canonical.update({'applied': True, 'source': 'startup_bootloader_controller_receipt', 'canonicalized_from': source, 'controller_receipt_path': project_relative(project_root, _controller_receipt_path(run_root, str(receipt.get('action_id') or entry.get('action_id') or ''))), 'postcondition': flag, 'bootstrap_postcondition': current.get('bootstrap_postcondition') or flag, 'bootstrap_flag_satisfied': True})
    return canonical

def _reconcile_scheduled_controller_action_receipts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {'changed': False, 'reconciled': 0, 'blocked': 0}
    changed = False
    reconciled = 0
    blocked = 0
    for action_path in sorted(action_dir.glob('*.json')):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        row_reconciliation = router._scheduler_row_reconciliation_for_entry(run_root, entry)
        action_id = str(entry.get('action_id') or action.get('controller_action_id') or '')
        receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id)) if action_id else {}
        legacy_startup_canonical = router._canonicalize_legacy_startup_daemon_reconciliation(project_root, run_root, run_state, entry, action, receipt)
        if legacy_startup_canonical.get('applied'):
            now = utc_now()
            entry['status'] = 'done'
            entry['completed_at'] = entry.get('completed_at') or now
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = now
            entry['router_reconciliation'] = legacy_startup_canonical
            entry['router_pending_apply_required'] = False
            if isinstance(entry.get('action'), dict):
                entry['action']['router_pending_apply_required'] = False
            write_json(action_path, entry)
            row_id = str(entry.get('router_scheduler_row_id') or '')
            if row_id:
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=legacy_startup_canonical)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=legacy_startup_canonical)
            changed = True
            reconciled += 1
            continue
        if row_reconciliation is not None and (not (entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'))):
            entry['status'] = 'done'
            entry['completed_at'] = entry.get('completed_at') or utc_now()
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = row_reconciliation
            write_json(action_path, entry)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action or {'action_type': entry.get('action_type')}, entry=entry, reconciliation=row_reconciliation)
            changed = True
            reconciled += 1
            continue
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES and _card_return_resolved_for_action(run_root, str(run_state['run_id']), action):
            applied = {'applied': True, 'source': 'role_card_return_resolved_delivery_relay', 'card_id': action.get('card_id'), 'card_bundle_id': action.get('card_bundle_id'), 'delivery_attempt_id': action.get('delivery_attempt_id')}
            entry['status'] = 'done'
            entry['completed_at'] = utc_now()
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = applied
            write_json(action_path, entry)
            row_id = str(entry.get('router_scheduler_row_id') or '')
            if row_id:
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
            changed = True
            reconciled += 1
            continue
        if entry.get('status') != 'done':
            continue
        if entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'):
            scheduler_backfill = router._backfill_scheduler_row_from_reconciled_controller_action(project_root, run_root, run_state, entry, source='reconciled_controller_action_scheduler_backfill')
            blocker_resolution = router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action or {'action_type': entry.get('action_type')}, entry=entry, reconciliation=entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else None)
            if scheduler_backfill.get('changed') or blocker_resolution.get('changed'):
                changed = True
                if scheduler_backfill.get('changed'):
                    reconciled += 1
            continue
        if entry.get('router_reconciliation_status') == 'blocked':
            postcondition = _pending_action_postcondition(action)
            action_type = str(action.get('action_type') or entry.get('action_type') or '')
            if action_type == 'recover_role_agents' or postcondition == 'role_recovery_roles_restored':
                applied = router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='blocked_controller_action_role_recovery_report_reclaim')
                if applied.get('applied') and (not postcondition or _pending_action_postcondition_satisfied(run_state, postcondition)):
                    now = utc_now()
                    entry['status'] = 'done'
                    entry['completed_at'] = entry.get('completed_at') or now
                    entry['router_reconciliation_status'] = 'reconciled'
                    entry['router_reconciled_at'] = now
                    entry['router_reconciliation'] = applied
                    entry['router_reconciliation_recovered_from_blocked_state'] = True
                    write_json(action_path, entry)
                    row_id = str(entry.get('router_scheduler_row_id') or '')
                    if row_id:
                        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
                    router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=applied)
                    changed = True
                    reconciled += 1
                    continue
            continue
        if not action:
            continue
        if row_reconciliation is not None:
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = row_reconciliation
            write_json(action_path, entry)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=row_reconciliation)
            changed = True
            reconciled += 1
            continue
        if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA or receipt.get('status') != 'done':
            continue
        try:
            applied = router._apply_done_controller_receipt_effects(project_root, run_root, run_state, action, receipt)
        except RouterLedgerWriteInProgress:
            raise
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            applied = {'applied': False, 'reason': str(exc)}
        if not applied.get('applied'):
            if applied.get('repair_scheduled'):
                changed = True
                continue
            if applied.get('blocked'):
                blocked += 1
                changed = True
                continue
            if applied.get('repair_pending'):
                changed = True
                continue
            retry = _defer_controller_postcondition_reconciliation_retry(project_root, run_root, run_state, entry=entry, action=action, apply_result=applied)
            if retry.get('retry_pending'):
                changed = True
                continue
            blocked += 1
            retry_exhausted = bool(retry.get('retry_budget_exhausted'))
            if retry_exhausted:
                entry['postcondition_reconciliation_exhausted'] = True
                entry['max_postcondition_reconciliation_attempts'] = retry.get('direct_retry_budget')
            entry['router_reconciliation_status'] = 'blocked'
            entry['router_reconciliation_blocked_at'] = utc_now()
            entry['router_reconciliation_blocker'] = applied
            write_json(action_path, entry)
            router._write_control_blocker(project_root, run_root, run_state, source=CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE, error_message=f"Controller action {entry.get('action_type')} was marked done, but Router could not apply its required postcondition before reconciliation.", action_type=str(entry.get('action_type') or ''), payload={'controller_action_id': action_id, 'router_scheduler_row_id': entry.get('router_scheduler_row_id'), 'postcondition': retry.get('postcondition') or applied.get('postcondition'), 'direct_retry_attempts_used': retry.get('direct_retry_attempts_used'), 'direct_retry_budget': retry.get('direct_retry_budget'), 'direct_retry_budget_exhausted': retry_exhausted, 'apply_result': applied})
            changed = True
            continue
        entry['router_reconciliation_status'] = 'reconciled'
        entry['router_reconciled_at'] = utc_now()
        entry['router_reconciliation'] = applied
        write_json(action_path, entry)
        row_id = str(entry.get('router_scheduler_row_id') or '')
        if row_id:
            router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
        router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=applied)
        changed = True
        reconciled += 1
    if changed:
        router._rebuild_controller_action_ledger(project_root, run_root, run_state)
        router._refresh_route_memory(project_root, run_root, run_state, trigger='after_scheduled_controller_receipt_reconciliation')
        router._sync_derived_run_views(project_root, run_root, run_state, reason='after_scheduled_controller_receipt_reconciliation', update_display=True)
        router.save_run_state(run_root, run_state)
    return {'changed': changed, 'reconciled': reconciled, 'blocked': blocked}

def _elapsed_seconds_since(router: ModuleType, raw_timestamp: object, *, now: datetime | None=None) -> int | None:
    _bind_router(router)
    parsed = _parse_utc_timestamp(raw_timestamp)
    if parsed is None:
        return None
    current = now or datetime.now(timezone.utc)
    return max(0, int((current - parsed).total_seconds()))

def _wait_target_path_exists(router: ModuleType, project_root: Path | None, raw_path: object) -> bool:
    _bind_router(router)
    if project_root is None or not isinstance(raw_path, str) or (not raw_path.strip()):
        return False
    return resolve_project_path(project_root, raw_path).exists()

def _pending_wait_class(router: ModuleType, pending: dict[str, Any]) -> str:
    _bind_router(router)
    explicit = str(pending.get('wait_class') or pending.get('wait_target_class') or '').strip()
    if explicit in {'ack', 'report_result', 'controller_local_action', 'router_reconciliation', 'none'}:
        return explicit
    action_type = str(pending.get('action_type') or '')
    if action_type in {'await_card_return_event', 'await_card_bundle_return_event', 'check_card_return_event', 'check_card_bundle_return_event', 'deliver_system_card', 'deliver_system_card_bundle'}:
        return 'ack'
    if action_type == 'await_role_decision':
        return 'report_result'
    if action_type == 'await_current_scope_reconciliation':
        return 'router_reconciliation'
    if action_type:
        return 'controller_local_action'
    return 'none'

def _wait_target_reminder_text(router: ModuleType, wait_class: str, target_role: str, wait_reason: str) -> str | None:
    _bind_router(router)
    if wait_class == 'ack':
        return f"Router is still waiting for {target_role or 'the target role'} to acknowledge {wait_reason or 'the assigned card'}. If you received it, submit the ACK through the original runtime path. If you are blocked, submit a blocker."
    if wait_class == 'report_result':
        return f"Router is still waiting for {target_role or 'the target role'} to finish {wait_reason or 'the assigned work'}. If you are still working, continue. If finished, submit through the original runtime path. If blocked, submit a blocker. Do not paste sealed report or result bodies into chat."
    return None

def _wait_target_due_state(router: ModuleType, *, wait_class: str, elapsed_seconds: int | None, last_reminder_elapsed_seconds: int | None, evidence_exists: bool, liveness_probe_result: str) -> dict[str, Any]:
    _bind_router(router)
    reminder_due = False
    blocker_required = False
    blocker_reason = None
    reissue_required = False
    reissue_reason = None
    liveness_check_due = False
    reminder_interval_seconds = None
    blocker_after_seconds = None
    next_due_seconds = None
    next_due_reason = None
    if wait_class == 'ack':
        reminder_interval_seconds = WAIT_TARGET_ACK_REMINDER_SECONDS
        blocker_after_seconds = WAIT_TARGET_ACK_BLOCKER_SECONDS
        if not evidence_exists and elapsed_seconds is not None:
            reminder_due = elapsed_seconds >= WAIT_TARGET_ACK_REMINDER_SECONDS and (last_reminder_elapsed_seconds is None or last_reminder_elapsed_seconds >= WAIT_TARGET_ACK_REMINDER_SECONDS)
            blocker_required = elapsed_seconds >= WAIT_TARGET_ACK_BLOCKER_SECONDS
            if blocker_required:
                blocker_reason = 'ack_missing_after_ten_minutes'
            if blocker_required:
                next_due_seconds = 0
                next_due_reason = 'ack_blocker'
            elif reminder_due:
                next_due_seconds = 0
                next_due_reason = 'ack_reminder'
            else:
                candidates: list[tuple[int, str]] = []
                if last_reminder_elapsed_seconds is None:
                    candidates.append((WAIT_TARGET_ACK_REMINDER_SECONDS - elapsed_seconds, 'ack_reminder'))
                else:
                    candidates.append((WAIT_TARGET_ACK_REMINDER_SECONDS - last_reminder_elapsed_seconds, 'ack_reminder'))
                candidates.append((WAIT_TARGET_ACK_BLOCKER_SECONDS - elapsed_seconds, 'ack_blocker'))
                next_due_seconds, next_due_reason = min(((max(0, seconds), reason) for seconds, reason in candidates), key=lambda item: item[0])
    elif wait_class == 'report_result':
        reminder_interval_seconds = WAIT_TARGET_REPORT_REMINDER_SECONDS
        if not evidence_exists and elapsed_seconds is not None:
            reminder_due = elapsed_seconds >= WAIT_TARGET_REPORT_REMINDER_SECONDS and (last_reminder_elapsed_seconds is None or last_reminder_elapsed_seconds >= WAIT_TARGET_REPORT_REMINDER_SECONDS)
            liveness_check_due = reminder_due
        if liveness_probe_result in WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS:
            reissue_required = True
            reissue_reason = f'role_no_output_{liveness_probe_result}'
        elif liveness_probe_result in WAIT_TARGET_UNHEALTHY_LIVENESS_RESULTS:
            blocker_required = True
            blocker_reason = f'role_liveness_{liveness_probe_result}'
        if blocker_required:
            next_due_seconds = 0
            next_due_reason = 'role_liveness_blocker'
        elif reissue_required:
            next_due_seconds = 0
            next_due_reason = 'role_no_output_reissue'
        elif reminder_due or liveness_check_due:
            next_due_seconds = 0
            next_due_reason = 'report_reminder_liveness_check'
        elif not evidence_exists and elapsed_seconds is not None:
            if last_reminder_elapsed_seconds is None:
                next_due_seconds = max(0, WAIT_TARGET_REPORT_REMINDER_SECONDS - elapsed_seconds)
            else:
                next_due_seconds = max(0, WAIT_TARGET_REPORT_REMINDER_SECONDS - last_reminder_elapsed_seconds)
            next_due_reason = 'report_reminder_liveness_check'
    elif wait_class == 'controller_local_action':
        reminder_due = False
        liveness_check_due = False
        next_due_seconds = 0
        next_due_reason = 'controller_local_self_audit'
    return {'reminder_interval_seconds': reminder_interval_seconds, 'blocker_after_seconds': blocker_after_seconds, 'reminder_due': reminder_due, 'liveness_check_due': liveness_check_due, 'blocker_required': blocker_required, 'blocker_reason': blocker_reason, 'reissue_required': reissue_required, 'reissue_reason': reissue_reason, 'next_due_seconds': next_due_seconds, 'next_due_reason': next_due_reason}

def _pending_wait_summary(router: ModuleType, run_state: dict[str, Any], *, project_root: Path | None=None) -> dict[str, Any]:
    _bind_router(router)
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    wait_class = router._pending_wait_class(pending)
    target_role = str(pending.get('waiting_for_role') or pending.get('to_role') or '').strip()
    wait_reason = str(pending.get('wait_reason') or pending.get('summary') or pending.get('label') or '').strip()
    expected_return_path = pending.get('expected_return_path')
    started_at = pending.get('wait_started_at') or pending.get('created_at') or pending.get('updated_at')
    last_reminder_at = pending.get('last_wait_reminder_at')
    last_liveness_probe = pending.get('last_liveness_probe')
    if not isinstance(last_liveness_probe, dict):
        last_liveness_probe = {}
    liveness_probe_result = str(pending.get('liveness_probe_result') or last_liveness_probe.get('result') or 'none')
    elapsed_seconds = router._elapsed_seconds_since(started_at)
    last_reminder_elapsed_seconds = router._elapsed_seconds_since(last_reminder_at)
    evidence_exists = router._wait_target_path_exists(project_root, expected_return_path)
    due_state = router._wait_target_due_state(wait_class=wait_class, elapsed_seconds=elapsed_seconds, last_reminder_elapsed_seconds=last_reminder_elapsed_seconds, evidence_exists=evidence_exists, liveness_probe_result=liveness_probe_result)
    return {'action_type': pending.get('action_type'), 'label': pending.get('label'), 'to_role': pending.get('to_role'), 'waiting_for_role': pending.get('waiting_for_role') or pending.get('to_role'), 'allowed_external_events': pending.get('allowed_external_events') or [], 'expected_return_path': expected_return_path, 'controller_action_id': pending.get('controller_action_id'), 'resource_lifecycle': pending.get('resource_lifecycle'), 'artifact_committed': pending.get('artifact_committed'), 'relay_allowed': pending.get('relay_allowed'), 'wait_class': wait_class, 'target_role': target_role or None, 'wait_reason': wait_reason or None, 'started_at': started_at, 'elapsed_seconds': elapsed_seconds, 'expected_evidence': {'path': expected_return_path, 'exists': evidence_exists, 'controller_visible_only': True}, 'reminder': {'text': pending.get('wait_reminder_text') or router._wait_target_reminder_text(wait_class, target_role, wait_reason), 'last_sent_at': last_reminder_at, 'due': due_state['reminder_due'], 'interval_seconds': due_state['reminder_interval_seconds'], 'controller_must_use_router_authored_text': True}, 'liveness_probe': {'required': wait_class == 'report_result' and bool(target_role), 'due': due_state['liveness_check_due'], 'target_role': target_role or None, 'last_checked_at': last_liveness_probe.get('checked_at'), 'last_result': liveness_probe_result, 'last_evidence_path': last_liveness_probe.get('evidence_path'), 'current_liveness_is_not_cached_authority': True}, 'controller_local_self_audit': {'required': wait_class == 'controller_local_action', 'reminder_allowed': False, 'check_action_ledger': True, 'check_receipts': True}, 'next_due': {'seconds': due_state['next_due_seconds'], 'reason': due_state['next_due_reason'], 'strict_wait_until_due': wait_class in {'ack', 'report_result', 'controller_local_action'}}, 'reissue': {'required': due_state['reissue_required'], 'reason': due_state['reissue_reason'], 'event': 'controller_reports_role_no_output' if due_state['reissue_required'] else None, 'record_event_payload': {'role_key': target_role, 'target_role_keys': [target_role] if target_role else [], 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'expected_return_path': expected_return_path, 'liveness_probe_result': liveness_probe_result, 'elapsed_seconds': elapsed_seconds, 'current_controller_action_id': pending.get('controller_action_id'), 'router_scheduler_row_id': pending.get('router_scheduler_row_id')} if due_state['reissue_required'] else None, 'same_work_reissue_before_role_recovery': bool(due_state['reissue_required']), 'pm_recovery_required': False}, 'blocker': {'required': due_state['blocker_required'], 'reason': due_state['blocker_reason'], 'event': 'controller_reports_role_liveness_fault' if due_state['blocker_required'] else None, 'record_event_payload': {'role_key': target_role, 'target_role_keys': [target_role] if target_role else [], 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'expected_return_path': expected_return_path, 'liveness_probe_result': liveness_probe_result, 'elapsed_seconds': elapsed_seconds} if due_state['blocker_required'] else None, 'pm_recovery_required': bool(due_state['blocker_required'])}}

def _current_work_owner_kind(router: ModuleType, owner_key: str) -> str:
    _bind_router(router)
    key = owner_key.strip()
    if key in {'router', 'controller', 'user'}:
        return key
    if key:
        return 'role'
    return 'none'

def _current_work_owner_label(router: ModuleType, owner_key: str) -> str:
    _bind_router(router)
    labels = {'router': 'Router', 'controller': 'Controller', 'user': 'User', 'project_manager': 'Project Manager', 'human_like_reviewer': 'Human-like Reviewer', 'process_flowguard_officer': 'Process FlowGuard Officer', 'product_flowguard_officer': 'Product FlowGuard Officer', 'worker_a': 'Worker A', 'worker_b': 'Worker B'}
    key = owner_key.strip()
    if key in labels:
        return labels[key]
    return key.replace('_', ' ').strip().title() if key else 'None'

def _current_work_payload(router: ModuleType, *, owner_key: str, task_label: str, source: str, source_path: str | None=None, action_type: str | None=None, action_id: str | None=None, packet_id: str | None=None, wait_class: str | None=None, waiting_for_role: str | None=None, diagnostics: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    owner_key = owner_key.strip()
    owner_kind = router._current_work_owner_kind(owner_key)
    owner_label = router._current_work_owner_label(owner_key)
    task = task_label.strip() or 'Monitor current FlowPilot progress'
    return {'owner_kind': owner_kind, 'owner_key': owner_key or None, 'owner_label': owner_label, 'task_label': task, 'source': source, 'source_path': source_path, 'action_type': action_type, 'action_id': action_id, 'packet_id': packet_id, 'wait_class': wait_class, 'legacy_waiting_for_role': waiting_for_role, 'display': {'en': f'Current owner: {owner_label}. Current task: {task}.', 'zh': f'当前处理方：{owner_label}。当前任务：{task}。'}, 'controller_use': {'primary_monitor_field': True, 'ownership_projection_only': True, 'does_not_satisfy_wait_or_approval': True, 'role_liveness_checks_apply': owner_kind == 'role', 'internal_owner': owner_kind in {'router', 'controller'}}, 'diagnostics': diagnostics or {}}

def _current_work_from_action(router: ModuleType, action: dict[str, Any], *, source: str, source_path: str | None=None, fallback_owner: str='controller') -> dict[str, Any] | None:
    _bind_router(router)
    if not isinstance(action, dict) or not action:
        return None
    action_type = str(action.get('action_type') or '')
    label = str(action.get('summary') or action.get('label') or action_type or 'Process FlowPilot action')
    target = str(action.get('waiting_for_role') or action.get('to_role') or action.get('target_role') or action.get('actor') or '').strip()
    if action.get('requires_user') or action.get('requires_user_dialog_display_confirmation'):
        owner_key = 'user'
    elif _action_is_passive_wait_status(action):
        owner_key = target
        if not owner_key and action_type == 'await_current_scope_reconciliation':
            owner_key = 'controller'
        if not owner_key:
            owner_key = 'router'
    elif target in {'router', 'controller'}:
        owner_key = target
    else:
        owner_key = fallback_owner
    wait_class = router._pending_wait_class(action)
    return router._current_work_payload(owner_key=owner_key, task_label=label, source=source, source_path=source_path, action_type=action_type or None, action_id=str(action.get('action_id') or action.get('controller_action_id') or '') or None, wait_class=wait_class, waiting_for_role=target or None, diagnostics={'passive_wait_status': _action_is_passive_wait_status(action), 'ordinary_controller_work_row': not _action_is_passive_wait_status(action)})

def _packet_status_allows_current_work(router: ModuleType, status: str) -> bool:
    _bind_router(router)
    normalized = status.strip().lower()
    if not normalized:
        return False
    return normalized not in {'done', 'complete', 'completed', 'cancelled', 'canceled', 'closed', 'stopped_by_user', 'result-returned', 'result_returned', 'result-absorbed', 'result_absorbed', 'absorbed', 'superseded'}

def _current_work_from_packet_ledger(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    path = run_root / 'packet_ledger.json'
    packet_ledger = read_json_if_exists(path)
    if not isinstance(packet_ledger, dict) or not packet_ledger:
        return None
    holder = str(packet_ledger.get('active_packet_holder') or '').strip()
    status = str(packet_ledger.get('active_packet_status') or '').strip()
    packet_id = str(packet_ledger.get('active_packet_id') or '').strip()
    if not holder or not router._packet_status_allows_current_work(status):
        return None
    task = f"Advance active packet {packet_id or 'work'} ({status})"
    return router._current_work_payload(owner_key=holder, task_label=task, source='packet_ledger', source_path=project_relative(project_root, path), packet_id=packet_id or None, diagnostics={'active_packet_status': status, 'active_packet_holder': holder, 'packet_ledger_schema': packet_ledger.get('schema_version')})

def _current_work_from_passive_waits(router: ModuleType, project_root: Path, run_root: Path, *, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    if controller_ledger is None:
        controller_ledger = router._controller_action_ledger_summary(run_root)
    passive_waits = controller_ledger.get('passive_waits') if isinstance(controller_ledger, dict) else []
    if isinstance(passive_waits, list):
        for item in passive_waits:
            if not isinstance(item, dict):
                continue
            status = str(item.get('status') or '').strip()
            reconciled = str(item.get('router_reconciliation_status') or '').strip()
            if status in {'done', 'resolved', 'skipped', 'superseded'} or reconciled == 'reconciled':
                continue
            payload = router._current_work_from_action(item, source='controller_action_ledger.passive_waits', source_path=controller_ledger.get('path') if isinstance(controller_ledger.get('path'), str) else None, fallback_owner='controller')
            if payload:
                return payload
    scheduler_path = _router_scheduler_ledger_path(run_root)
    scheduler = read_json_if_exists(scheduler_path)
    rows = scheduler.get('rows') if isinstance(scheduler, dict) and isinstance(scheduler.get('rows'), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        router_state = str(row.get('router_state') or '').strip()
        controller_status = str(row.get('controller_status') or '').strip()
        if router_state not in {'queued', 'waiting', 'receipt_done'} and controller_status not in {'pending', 'waiting', 'in_progress'}:
            continue
        action_type = str(row.get('action_type') or '')
        target = str(row.get('to_role') or row.get('waiting_for_role') or '').strip()
        if action_type == 'await_current_scope_reconciliation' and (not target):
            target = 'controller'
        payload = router._current_work_payload(owner_key=target or 'router', task_label=str(row.get('label') or action_type or 'Reconcile scheduler wait'), source='router_scheduler_ledger', source_path=project_relative(project_root, scheduler_path), action_type=action_type or None, action_id=str(row.get('row_id') or '') or None, waiting_for_role=target or None, diagnostics={'router_state': router_state, 'controller_status': controller_status, 'barrier_kind': row.get('barrier_kind')})
        return payload
    return None

def _derive_current_work(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, current_wait: dict[str, Any] | None=None, current_action: dict[str, Any] | None=None, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    if pending:
        payload = router._current_work_from_action(pending, source='pending_action', source_path=project_relative(project_root, router.run_state_path(run_root)))
        if payload:
            return payload
    if isinstance(current_action, dict) and current_action:
        payload = router._current_work_from_action(current_action, source='current_action', source_path=project_relative(project_root, _router_daemon_status_path(run_root)))
        if payload:
            return payload
    packet_payload = router._current_work_from_packet_ledger(project_root, run_root)
    if packet_payload:
        return packet_payload
    passive_payload = router._current_work_from_passive_waits(project_root, run_root, controller_ledger=controller_ledger)
    if passive_payload:
        return passive_payload
    if isinstance(current_wait, dict) and current_wait:
        payload = router._current_work_from_action(current_wait, source='current_wait', source_path=project_relative(project_root, _router_daemon_status_path(run_root)), fallback_owner='router')
        if payload and payload.get('owner_kind') != 'none':
            return payload
    if run_state.get('daemon_mode_enabled'):
        return router._current_work_payload(owner_key='router', task_label='Compute or observe the next safe FlowPilot step', source='router_daemon', source_path=project_relative(project_root, _router_daemon_status_path(run_root)), diagnostics={'daemon_mode_enabled': True, 'run_status': run_state.get('status')})
    return router._current_work_payload(owner_key='controller', task_label='Inspect FlowPilot state', source='controller', source_path=project_relative(project_root, router.run_state_path(run_root)), diagnostics={'run_status': run_state.get('status')})

def _wait_target_reminder_text_sha256(router: ModuleType, reminder_text: str) -> str:
    _bind_router(router)
    return hashlib.sha256(reminder_text.encode('utf-8')).hexdigest()

def _wait_target_identity(router: ModuleType, pending: dict[str, Any], current_wait: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'action_type': pending.get('action_type') or current_wait.get('action_type'), 'label': pending.get('label') or current_wait.get('label'), 'wait_class': current_wait.get('wait_class'), 'target_role': current_wait.get('target_role') or current_wait.get('waiting_for_role'), 'expected_return_path': current_wait.get('expected_return_path'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'source_wait_action_id': pending.get('action_id'), 'source_wait_controller_action_id': pending.get('controller_action_id'), 'wait_started_at': current_wait.get('started_at') or pending.get('created_at')}

def _wait_target_reminder_payload_contract(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return _payload_contract(name='wait_target_reminder_receipt', required_object='payload', required_fields=['target_role', 'delivered_to_role', 'reminder_text_sha256', 'sealed_body_reads'], optional_fields=['delivered_at', 'delivery_channel', 'liveness_probe', 'liveness_probe_result', 'liveness_probe_checked_at'], allowed_values={'sealed_body_reads': [False]}, conditional_required_fields={'when fresh_liveness_probe_required=true': ['liveness_probe.result', 'liveness_probe.checked_at']}, structural_requirements=['reminder_text_sha256 must match the Router-authored reminder_text on the action row', 'Controller must send the reminder_text exactly as supplied and must not paste sealed result bodies', 'target_role and delivered_to_role must name the wait target role'], description="Receipt proving Controller sent the Router-authored wait reminder to the current waiting role. This records reminder delivery only; it does not satisfy the role's original ACK or result-return obligation.")

def _next_wait_target_reminder_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    if not _action_is_passive_wait_status(pending_action):
        return None
    current_wait = current_wait or router._pending_wait_summary(run_state, project_root=project_root)
    wait_class = str(current_wait.get('wait_class') or '')
    if wait_class not in {'ack', 'report_result'}:
        return None
    if (current_wait.get('blocker') or {}).get('required'):
        return None
    reminder = current_wait.get('reminder') if isinstance(current_wait.get('reminder'), dict) else {}
    liveness_probe = current_wait.get('liveness_probe') if isinstance(current_wait.get('liveness_probe'), dict) else {}
    reminder_due = bool(reminder.get('due'))
    liveness_due = bool(liveness_probe.get('due'))
    if not (reminder_due or liveness_due):
        return None
    target_role = str(current_wait.get('target_role') or current_wait.get('waiting_for_role') or '').strip()
    if not target_role:
        return None
    wait_reason = str(current_wait.get('wait_reason') or pending_action.get('summary') or pending_action.get('label') or '').strip()
    reminder_text = str(reminder.get('text') or router._wait_target_reminder_text(wait_class, target_role, wait_reason) or '').strip()
    if not reminder_text:
        return None
    reminder_hash = router._wait_target_reminder_text_sha256(reminder_text)
    identity = router._wait_target_identity(pending_action, current_wait)
    last_sent = str(reminder.get('last_sent_at') or pending_action.get('last_wait_reminder_at') or 'initial')
    safe_target = _safe_delivery_component(target_role)
    safe_wait_class = _safe_delivery_component(wait_class)
    label = f'controller_sends_wait_target_reminder_{safe_target}_{safe_wait_class}'
    return make_action(action_type=WAIT_TARGET_REMINDER_ACTION_TYPE, actor='controller', label=label, summary=f'Send the Router-authored {wait_class} wait reminder to {target_role}. This is a generic wait-target reminder action, not completion of the original wait.', allowed_reads=[project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], allowed_writes=[], extra={'controller_side_effect_required': True, 'target_role': target_role, 'waiting_for_role': target_role, 'waiting_for_agent_id': pending_action.get('waiting_for_agent_id'), 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'source_wait_identity': identity, 'source_wait_action_type': pending_action.get('action_type'), 'source_wait_label': pending_action.get('label'), 'source_wait_action_id': pending_action.get('action_id'), 'source_wait_controller_action_id': pending_action.get('controller_action_id'), 'expected_return_path': current_wait.get('expected_return_path'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'reminder_text': reminder_text, 'reminder_text_sha256': reminder_hash, 'controller_must_use_router_authored_text': True, 'controller_may_edit_reminder_text': False, 'fresh_liveness_probe_required': bool(liveness_due), 'liveness_probe_target_role': liveness_probe.get('target_role') or target_role, 'liveness_probe_current_liveness_is_not_cached_authority': bool(liveness_probe.get('current_liveness_is_not_cached_authority')), 'payload_contract': router._wait_target_reminder_payload_contract(), 'controller_receipt_rule': 'Send reminder_text exactly to target_role, do not read or paste sealed bodies, then write a Controller receipt whose payload includes target_role, delivered_to_role, reminder_text_sha256, sealed_body_reads=false, and a fresh liveness_probe when fresh_liveness_probe_required is true.', 'idempotency_key': f"wait-target-reminder:{run_state.get('run_id')}:{hashlib.sha256(json.dumps(identity, sort_keys=True).encode('utf-8')).hexdigest()[:20]}:{last_sent}", 'scope_kind': pending_action.get('scope_kind') or 'wait_target', 'scope_id': pending_action.get('scope_id') or identity.get('expected_return_path') or identity.get('label') or target_role, 'apply_required': True, 'relay_allowed': False, 'sealed_body_reads_allowed': False})

def _ensure_wait_target_reminder_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    action = router._next_wait_target_reminder_action(project_root, run_root, run_state, pending_action, current_wait)
    if action is None:
        return None
    entry = router._write_controller_action_entry(project_root, run_root, run_state, action)
    append_history(run_state, 'router_materialized_wait_target_reminder_action', {'controller_action_id': entry.get('action_id'), 'target_role': action.get('target_role'), 'wait_class': action.get('wait_class'), 'source_wait_action_type': action.get('source_wait_action_type')})
    return entry

def _continuous_standby_watch_label(router: ModuleType, current_wait: dict[str, Any]) -> str:
    _bind_router(router)
    target = str(current_wait.get('waiting_for_role') or current_wait.get('target_role') or '').strip()
    wait_class = str(current_wait.get('wait_class') or 'none')
    if target and wait_class in {'ack', 'report_result'}:
        return f'{target} {wait_class} wait'
    label = str(current_wait.get('label') or '').strip()
    if label:
        return label
    return 'Router daemon'

def _continuous_standby_release_conditions(router: ModuleType) -> list[str]:
    _bind_router(router)
    return ['controller_action_ready', 'wait_target_check_due', 'wait_target_blocker_required', 'terminal', 'user_input_required', 'daemon_liveness_check_required', 'daemon_stale_or_missing', 'explicit_host_stop']

def _continuous_standby_task_payload(router: ModuleType, project_root: Path, run_root: Path, current_wait: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    wait_class = str(current_wait.get('wait_class') or 'none')
    patrol_command = _controller_patrol_timer_command()
    break_glass = _controller_break_glass_reminder()
    wait_policy: dict[str, Any] = {'wait_class': wait_class, 'next_due': current_wait.get('next_due') or {}, 'strict_wait_until_router_release_condition': True, 'ack_reminder_seconds': WAIT_TARGET_ACK_REMINDER_SECONDS, 'ack_blocker_seconds': WAIT_TARGET_ACK_BLOCKER_SECONDS, 'report_reminder_and_liveness_seconds': WAIT_TARGET_REPORT_REMINDER_SECONDS}
    return {'task_kind': 'continuous_controller_standby', 'task_type': 'foreground_keepalive_waiting_patrol', 'status': 'in_progress', 'purpose': 'Prevent Controller from accidentally exiting the foreground chat while FlowPilot is still running.', 'required_command': patrol_command, 'patrol_timer_seconds': CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS, 'loop_rule': 'Run required_command and wait for its output. If it returns continue_patrol, immediately run required_command again and wait for the next output. Starting or restarting the command is not completion.', 'monitor_source': 'existing_router_daemon_monitor', 'watching': router._continuous_standby_watch_label(current_wait), 'monitor_sources': {'router_daemon_status_path': project_relative(project_root, _router_daemon_status_path(run_root)), 'controller_action_ledger_path': project_relative(project_root, _controller_action_ledger_path(run_root)), 'controller_receipts_dir': project_relative(project_root, _controller_receipts_dir(run_root))}, 'current_wait': {'action_type': current_wait.get('action_type'), 'label': current_wait.get('label'), 'waiting_for_role': current_wait.get('waiting_for_role'), 'wait_class': wait_class, 'target_role': current_wait.get('target_role'), 'elapsed_seconds': current_wait.get('elapsed_seconds'), 'expected_return_path': current_wait.get('expected_return_path'), 'next_due': current_wait.get('next_due')}, 'codex_plan_sync': {'required': True, 'plan_item': f"FlowPilot continuous standby: this is the final fallback row when all ordinary Controller rows are complete but FlowPilot is still running. Keep this row in progress as a continuous monitoring duty and foreground anti-exit patrol duty. Run the patrol timer command, wait for its output, and if it returns continue_patrol, rerun the same command and wait for the next output. Keep the foreground Controller attached, sync the visible Codex plan from the Controller action ledger and receipts, and when Router exposes new Controller work, update the table and return to top-to-bottom row processing. {break_glass['text']}", 'plan_status': 'in_progress', 'sync_after_each_controller_row': True, 'check_for_missed_rows_and_receipts_before_sleep': True, 'new_controller_work_returns_to_top_down_processing': True}, 'break_glass_reminder': break_glass, 'wait_policy': wait_policy, 'do_not_mark_complete_on': ['command_started', 'command_restarted', 'timer_finished', 'monitor_checked_once', 'one_monitor_poll', 'timeout_still_waiting', 'target_role_alive', 'target_role_still_working', 'no_new_controller_action_yet', 'no_new_controller_work', 'continue_patrol'], 'completion_allowed_only_when': 'terminal_return_and_controller_stop_allowed_true', 'release_conditions': router._continuous_standby_release_conditions(), 'release_condition_meaning': 'switch duty or process new work, not foreground closure while FlowPilot is running', 'controller_must_not_exit_foreground': True, 'foreground_close_allowed_while_flowpilot_running': False, 'new_controller_work_requires_ledger_update_and_top_down_reentry': True, 'controller_must_not_use_router_next_as_metronome': True, 'metadata_only': True, 'sealed_body_reads_allowed': False}

def _current_action_is_ordinary_controller_work(router: ModuleType, current_action: dict[str, Any] | None) -> bool:
    _bind_router(router)
    if not isinstance(current_action, dict):
        return False
    if str(current_action.get('action_type') or '') == CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE:
        return False
    return _controller_action_initial_status(current_action) != 'waiting'

def _should_refresh_continuous_standby_row(router: ModuleType, run_state: dict[str, Any], *, lifecycle_status: str, current_action: dict[str, Any] | None) -> bool:
    _bind_router(router)
    if _terminal_lifecycle_mode(run_state):
        return False
    if lifecycle_status not in {'daemon_active', 'daemon_observing', 'manual_router_loop'}:
        return False
    if not bool(run_state.get('daemon_mode_enabled')):
        return False
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if not flags.get('controller_core_loaded'):
        return False
    pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    if pending_action.get('requires_user') or pending_action.get('requires_user_dialog_display_confirmation'):
        return False
    return not router._current_action_is_ordinary_controller_work(current_action)

def _ensure_continuous_standby_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], current_wait: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    standby_task = router._continuous_standby_task_payload(project_root, run_root, current_wait)
    action = make_action(action_type=CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE, actor='controller', label='controller_continuous_flowpilot_standby', summary='Continuous standby duty: keep the foreground Controller attached while FlowPilot is running, sync the visible Codex plan from FlowPilot ledgers, watch Router daemon status, and return to top-to-bottom Controller action ledger row processing when Router exposes new Controller work.', allowed_reads=[project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _controller_receipts_dir(run_root))], allowed_writes=[], extra={'resource_lifecycle': 'continuous_standby', 'artifact_committed': True, 'apply_required': False, 'relay_allowed': False, 'continuous_standby_task': standby_task, 'codex_plan_sync': standby_task['codex_plan_sync'], 'idempotency_key': f"controller-continuous-standby:{run_state.get('run_id')}", 'scope_kind': 'run', 'scope_id': str(run_state.get('run_id') or 'run'), 'router_scheduler_barrier_kind': 'continuous_standby', 'controller_should_keep_status_waiting': True})
    return router._write_controller_action_entry(project_root, run_root, run_state, action)

def _foreground_standby_pending_action_ids(router: ModuleType, ledger: dict[str, Any]) -> list[str]:
    _bind_router(router)
    actions = ledger.get('actions') if isinstance(ledger.get('actions'), list) else []
    return [str(item.get('action_id')) for item in actions if isinstance(item, dict) and item.get('action_id') and _controller_action_is_ordinary_work_row(item) and (item.get('status') in {'pending', 'in_progress'})]

def _foreground_standby_waiting_action_ids(router: ModuleType, ledger: dict[str, Any]) -> list[str]:
    _bind_router(router)
    actions = ledger.get('actions') if isinstance(ledger.get('actions'), list) else []
    return [str(item.get('action_id')) for item in actions if isinstance(item, dict) and item.get('action_id') and _controller_action_is_ordinary_work_row(item) and (item.get('status') == 'waiting')]

def _build_foreground_controller_standby_snapshot(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, started_at: str, start_monotonic: float, poll_count: int, max_seconds: float, poll_seconds: float) -> dict[str, Any]:
    _bind_router(router)
    lock_path = _router_daemon_lock_path(run_root)
    status_path = _router_daemon_status_path(run_root)
    ledger_path = _controller_action_ledger_path(run_root)
    lock = read_json_if_exists(lock_path)
    daemon_status = read_json_if_exists(status_path)
    ledger = read_json_if_exists(ledger_path)
    lock_liveness = _router_daemon_lock_liveness(lock)
    lock_live = bool(lock_liveness.get('live'))
    status_ok = daemon_status.get('schema_version') == ROUTER_DAEMON_STATUS_SCHEMA
    heartbeat_monitor = _router_daemon_heartbeat_monitor(lock, lock_liveness, status_exists=status_path.exists(), status_ok=status_ok)
    daemon_liveness_check_required = heartbeat_monitor.get('status') == 'check_liveness'
    daemon_live = lock_live and status_ok and bool(daemon_status.get('daemon_mode_enabled')) and (daemon_status.get('run_root') == project_relative(project_root, run_root))
    ledger_ok = ledger.get('schema_version') == CONTROLLER_ACTION_LEDGER_SCHEMA
    pending_action_ids = router._foreground_standby_pending_action_ids(ledger) if ledger_ok else []
    waiting_action_ids = router._foreground_standby_waiting_action_ids(ledger) if ledger_ok else []
    daemon_wait = daemon_status.get('current_wait') if isinstance(daemon_status.get('current_wait'), dict) else {}
    current_wait = router._pending_wait_summary(run_state, project_root=project_root)
    if daemon_wait:
        for key in ('action_type', 'label', 'to_role', 'waiting_for_role', 'allowed_external_events', 'expected_return_path', 'next_due'):
            if current_wait.get(key) in (None, '', []) and daemon_wait.get(key) not in (None, '', []):
                current_wait[key] = daemon_wait.get(key)
    current_work = router._derive_current_work(project_root, run_root, run_state, current_wait=current_wait, current_action=daemon_status.get('current_action') if isinstance(daemon_status.get('current_action'), dict) else None, controller_ledger=router._controller_action_ledger_summary(run_root))
    current_action = daemon_status.get('current_action') if isinstance(daemon_status.get('current_action'), dict) else {}
    continuous_standby_task = daemon_status.get('continuous_standby_task') if isinstance(daemon_status.get('continuous_standby_task'), dict) else router._continuous_standby_task_payload(project_root, run_root, current_wait)
    pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    run_lifecycle = str(run_state.get('status') or '')
    terminal = daemon_status.get('lifecycle_status') == 'terminal_stopped' or bool(daemon_status.get('run_lifecycle_status')) or run_lifecycle in RUN_TERMINAL_STATUSES
    user_required = bool(pending_action.get('requires_user') or pending_action.get('requires_user_dialog_display_confirmation'))
    if terminal:
        standby_state = 'terminal'
    elif user_required:
        standby_state = 'user_input_required'
    elif daemon_liveness_check_required:
        standby_state = 'daemon_liveness_check_required'
    elif pending_action_ids:
        standby_state = 'controller_action_ready'
    elif (current_wait.get('blocker') or {}).get('required'):
        standby_state = 'wait_target_blocker_required'
    elif (current_wait.get('reissue') or {}).get('required'):
        standby_state = 'wait_target_reissue_required'
    elif (current_wait.get('reminder') or {}).get('due') or (current_wait.get('liveness_probe') or {}).get('due') or (current_wait.get('controller_local_self_audit') or {}).get('required'):
        standby_state = 'wait_target_check_due'
    elif current_wait.get('waiting_for_role') or current_wait.get('action_type') == 'await_role_decision':
        standby_state = 'waiting_for_role'
    else:
        standby_state = 'daemon_alive_no_controller_action'
    controller_must_continue_standby = standby_state in {'waiting_for_role', 'daemon_alive_no_controller_action'}
    controller_must_process_pending_action = standby_state == 'controller_action_ready'
    controller_stop_allowed = standby_state == 'terminal'
    wait_target_action_ready = standby_state in {'wait_target_check_due', 'wait_target_blocker_required', 'wait_target_reissue_required'}
    foreground_turn_return_allowed = standby_state in {'terminal', 'user_input_required', 'daemon_liveness_check_required', 'wait_target_check_due', 'wait_target_blocker_required', 'wait_target_reissue_required'}
    if controller_must_process_pending_action:
        foreground_required_mode = 'process_controller_action'
    elif standby_state == 'wait_target_check_due':
        foreground_required_mode = 'process_wait_target_check'
    elif standby_state == 'wait_target_blocker_required':
        foreground_required_mode = 'record_wait_target_blocker'
    elif standby_state == 'wait_target_reissue_required':
        foreground_required_mode = 'record_wait_target_no_output_reissue'
    elif controller_must_continue_standby:
        foreground_required_mode = 'watch_router_daemon'
    elif standby_state == 'user_input_required':
        foreground_required_mode = 'return_for_user_input'
    elif standby_state == 'daemon_liveness_check_required':
        foreground_required_mode = 'check_liveness'
    else:
        foreground_required_mode = 'terminal_return'
    elapsed = max(0.0, time.monotonic() - start_monotonic)
    return {'schema_version': FOREGROUND_CONTROLLER_STANDBY_SCHEMA, 'ok': True, 'command': 'controller-standby', 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'started_at': started_at, 'observed_at': utc_now(), 'elapsed_seconds': round(elapsed, 3), 'max_seconds': max_seconds, 'poll_seconds': poll_seconds, 'poll_count': poll_count, 'standby_state': standby_state, 'controller_must_continue_standby': controller_must_continue_standby, 'controller_must_process_pending_action_before_exit': controller_must_process_pending_action, 'controller_must_process_wait_target_before_exit': wait_target_action_ready, 'foreground_exit_allowed': controller_stop_allowed, 'foreground_turn_return_allowed': foreground_turn_return_allowed, 'foreground_required_mode': foreground_required_mode, 'controller_stop_allowed': controller_stop_allowed, 'nonterminal_controller_must_stay_attached': not controller_stop_allowed, 'normal_router_progress_source': 'router_daemon_status_and_controller_action_ledger', 'diagnostic_router_reentry_commands': ['next', 'run-until-wait'], 'diagnostic_router_reentry_policy': 'diagnostic/test/explicit-repair only; not normal progress while daemon status and the Controller action ledger own the active run', 'break_glass_reminder': _controller_break_glass_reminder(), 'standby_does_not_drive_router_progress': True, 'metadata_only': True, 'sealed_body_reads_allowed': False, 'router_daemon': {'lock_path': project_relative(project_root, lock_path), 'status_path': project_relative(project_root, status_path), 'lock_exists': lock_path.exists(), 'lock_live': lock_live, 'lock_status': lock.get('status'), 'lock_last_tick_at': lock.get('last_tick_at'), 'status_exists': status_path.exists(), 'status_ok': status_ok, 'daemon_live': daemon_live, 'active_owner_live': _router_daemon_lock_has_live_owner(lock_liveness), 'heartbeat_status': heartbeat_monitor['status'], 'heartbeat_age_seconds': heartbeat_monitor['age_seconds'], 'heartbeat_check_after_seconds': heartbeat_monitor['check_after_seconds'], 'heartbeat_reasons': heartbeat_monitor['reasons'], 'controller_liveness_check_required': heartbeat_monitor['controller_liveness_check_required'], 'monitor_can_decide_recovery': heartbeat_monitor['monitor_can_decide_recovery'], 'controller_instruction': heartbeat_monitor['controller_instruction'], 'lifecycle_status': daemon_status.get('lifecycle_status'), 'last_tick_at': daemon_status.get('last_tick_at'), 'tick_interval_seconds': daemon_status.get('tick_interval_seconds')}, 'controller_action_ledger': {'path': project_relative(project_root, ledger_path), 'exists': ledger_path.exists(), 'schema_ok': ledger_ok, 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') if ledger_ok else _controller_action_counts([]), 'passive_wait_count': int(ledger.get('passive_wait_count') or 0) if ledger_ok else 0, 'passive_waits_projected_via_status_not_work_board': bool(ledger.get('passive_waits_projected_via_status_not_work_board')) if ledger_ok else False, 'pending_action_ids': pending_action_ids, 'waiting_action_ids': waiting_action_ids}, 'current_work': current_work, 'current_wait': {'action_type': current_wait.get('action_type'), 'label': current_wait.get('label'), 'waiting_for_role': current_wait.get('waiting_for_role'), 'wait_class': current_wait.get('wait_class'), 'target_role': current_wait.get('target_role'), 'wait_reason': current_wait.get('wait_reason'), 'started_at': current_wait.get('started_at'), 'elapsed_seconds': current_wait.get('elapsed_seconds'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'expected_return_path': current_wait.get('expected_return_path'), 'expected_evidence': current_wait.get('expected_evidence'), 'reminder': current_wait.get('reminder'), 'liveness_probe': current_wait.get('liveness_probe'), 'controller_local_self_audit': current_wait.get('controller_local_self_audit'), 'next_due': current_wait.get('next_due'), 'reissue': current_wait.get('reissue'), 'blocker': current_wait.get('blocker')}, 'continuous_standby_task': continuous_standby_task, 'current_action': {'action_type': current_action.get('action_type'), 'label': current_action.get('label'), 'controller_action_id': current_action.get('controller_action_id'), 'controller_projection_kind': current_action.get('controller_projection_kind') or _controller_action_projection_kind(current_action), 'ordinary_controller_work_row': not _action_is_passive_wait_status(current_action), 'apply_required': current_action.get('apply_required')} if current_action else None, 'exit_policy': {'returns_on_controller_action': True, 'returns_on_terminal': True, 'returns_on_user_required': True, 'returns_on_daemon_liveness_check_required': True, 'returns_on_bounded_timeout': True, 'bounded_timeout_is_diagnostic_only': True, 'returns_on_wait_target_check_due': True, 'returns_on_wait_target_blocker_required': True, 'returns_on_wait_target_reissue_required': True, 'controller_action_ready_blocks_foreground_exit': True, 'live_daemon_wait_requires_standby': True, 'controller_stop_requires_terminal_run': True, 'nonterminal_modes': ['process_controller_action', 'watch_router_daemon', 'check_liveness']}}

def foreground_controller_standby(router: ModuleType, project_root: Path, *, max_seconds: float=_DEFAULT_SENTINEL, poll_seconds: float=_DEFAULT_SENTINEL, bounded_diagnostic: bool=False) -> dict[str, Any]:
    _bind_router(router)
    if max_seconds is _DEFAULT_SENTINEL:
        max_seconds = FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS
    if poll_seconds is _DEFAULT_SENTINEL:
        poll_seconds = FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS
    if max_seconds < 0:
        raise RouterError('controller standby requires max_seconds >= 0')
    if poll_seconds <= 0:
        raise RouterError('controller standby requires poll_seconds > 0')
    project_root = project_root.resolve()
    started_at = utc_now()
    start_monotonic = time.monotonic()
    poll_count = 0
    while True:
        bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
        run_state, run_root = router.load_run_state(project_root, bootstrap)
        if run_state is None or run_root is None:
            raise RouterError('controller standby requires an active FlowPilot run')
        snapshot = router._build_foreground_controller_standby_snapshot(project_root, run_root, run_state, started_at=started_at, start_monotonic=start_monotonic, poll_count=poll_count, max_seconds=max_seconds, poll_seconds=poll_seconds)
        snapshot['bounded_diagnostic'] = bounded_diagnostic
        if snapshot['standby_state'] == 'wait_target_check_due':
            pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
            current_wait = snapshot.get('current_wait') if isinstance(snapshot.get('current_wait'), dict) else {}
            reminder_entry = router._ensure_wait_target_reminder_controller_action(project_root, run_root, run_state, pending_action, current_wait)
            if reminder_entry is not None:
                router.save_run_state(run_root, run_state)
                snapshot = router._build_foreground_controller_standby_snapshot(project_root, run_root, run_state, started_at=started_at, start_monotonic=start_monotonic, poll_count=poll_count, max_seconds=max_seconds, poll_seconds=poll_seconds)
                snapshot['bounded_diagnostic'] = bounded_diagnostic
                snapshot['materialized_wait_target_controller_action'] = {'controller_action_id': reminder_entry.get('action_id'), 'action_type': reminder_entry.get('action_type'), 'target_role': (reminder_entry.get('action') or {}).get('target_role') if isinstance(reminder_entry.get('action'), dict) else None, 'wait_class': (reminder_entry.get('action') or {}).get('wait_class') if isinstance(reminder_entry.get('action'), dict) else None}
                return snapshot
        if snapshot['standby_state'] in {'controller_action_ready', 'wait_target_check_due', 'wait_target_blocker_required', 'wait_target_reissue_required', 'terminal', 'user_input_required', 'daemon_liveness_check_required'}:
            return snapshot
        elapsed = time.monotonic() - start_monotonic
        if elapsed >= max_seconds:
            if not bounded_diagnostic and snapshot['controller_must_continue_standby']:
                poll_count += 1
                time.sleep(poll_seconds)
                continue
            snapshot['standby_state'] = 'timeout_still_waiting'
            snapshot['controller_must_continue_standby'] = bool(snapshot['router_daemon']['daemon_live'] and (not snapshot['controller_action_ledger']['pending_action_ids']))
            snapshot['controller_must_process_pending_action_before_exit'] = False
            snapshot['foreground_required_mode'] = 'watch_router_daemon' if snapshot['controller_must_continue_standby'] else snapshot['foreground_required_mode']
            snapshot['foreground_exit_allowed'] = False
            snapshot['foreground_turn_return_allowed'] = not bool(snapshot['controller_must_continue_standby'])
            snapshot['controller_stop_allowed'] = False
            snapshot['nonterminal_controller_must_stay_attached'] = True
            snapshot['bounded_timeout_is_diagnostic_only'] = True
            return snapshot
        poll_count += 1
        remaining = max_seconds - elapsed
        time.sleep(min(poll_seconds, max(0.0, remaining)))

def controller_patrol_timer(router: ModuleType, project_root: Path, *, seconds: float=_DEFAULT_SENTINEL) -> dict[str, Any]:
    _bind_router(router)
    if seconds is _DEFAULT_SENTINEL:
        seconds = CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS
    if seconds < 0:
        raise RouterError('controller patrol timer requires seconds >= 0')
    poll_seconds = max(0.01, float(seconds))
    snapshot = router.foreground_controller_standby(project_root, max_seconds=float(seconds), poll_seconds=poll_seconds, bounded_diagnostic=True)
    next_command = _controller_patrol_timer_command(seconds)
    standby_state = str(snapshot.get('standby_state') or '')
    foreground_mode = str(snapshot.get('foreground_required_mode') or '')
    controller_stop_allowed = bool(snapshot.get('controller_stop_allowed'))
    must_continue = bool(snapshot.get('controller_must_continue_standby'))
    pending_ids = (snapshot.get('controller_action_ledger') or {}).get('pending_action_ids') if isinstance(snapshot.get('controller_action_ledger'), dict) else []
    if standby_state == 'controller_action_ready' or pending_ids:
        patrol_result = 'new_controller_work'
        controller_instruction = 'New Controller work exists. Read controller_action_ledger.json and process ready Controller rows from top to bottom before returning to patrol.'
        anti_exit_reminder = ''
    elif standby_state == 'terminal' and controller_stop_allowed:
        patrol_result = 'terminal_return'
        controller_instruction = 'The monitored run is terminal and controller_stop_allowed is true. Controller may end the foreground turn after terminal cleanup.'
        anti_exit_reminder = ''
    elif standby_state == 'daemon_liveness_check_required' or foreground_mode == 'check_liveness':
        patrol_result = 'check_liveness'
        anti_exit_reminder = 'This patrol exists to prevent Controller from accidentally exiting the foreground chat while FlowPilot is still running.'
        router_daemon = snapshot.get('router_daemon') if isinstance(snapshot.get('router_daemon'), dict) else {}
        controller_instruction = str(router_daemon.get('controller_instruction') or 'Daemon heartbeat needs a Controller liveness check. If the daemon is alive, stay attached and continue. If it is dead, recover the current-run Router daemon without starting a second live writer.')
    elif must_continue or foreground_mode == 'watch_router_daemon':
        patrol_result = 'continue_patrol'
        anti_exit_reminder = 'This patrol exists to prevent Controller from accidentally exiting the foreground chat while FlowPilot is still running.'
        controller_instruction = "No new Controller work exists. Do not final-answer. Do not close the foreground chat. Immediately rerun next_command and wait for that command's next output. Starting or restarting the command is not completion."
    else:
        patrol_result = foreground_mode or standby_state or 'non_standby_duty'
        anti_exit_reminder = 'This patrol exists to prevent Controller from accidentally exiting the foreground chat while FlowPilot is still running.'
        controller_instruction = 'A non-standby duty is due. Follow foreground_required_mode before any foreground exit decision.'
    return {'schema_version': CONTROLLER_PATROL_TIMER_SCHEMA, 'ok': True, 'command': 'controller-patrol-timer', 'seconds': float(seconds), 'patrol_result': patrol_result, 'foreground_required_mode': foreground_mode, 'controller_stop_allowed': controller_stop_allowed, 'anti_exit_reminder': anti_exit_reminder, 'break_glass_reminder': _controller_break_glass_reminder(), 'controller_instruction': controller_instruction, 'next_command': next_command if patrol_result == 'continue_patrol' else None, 'standby_status_after_rerun': 'continuous_controller_standby remains in_progress until the next command output' if patrol_result == 'continue_patrol' else None, 'completion_allowed_only_when': 'terminal_return_and_controller_stop_allowed_true', 'command_start_is_completion': False, 'command_restart_is_completion': False, 'monitor_source': 'existing_router_daemon_monitor', 'normal_progress_source': 'router_daemon_status_and_controller_action_ledger', 'standby_snapshot': snapshot}


_LOCAL_NAMES = set(globals())
