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

__all__ = (
    '_empty_router_scheduler_ledger',
    '_read_router_scheduler_ledger',
    '_write_router_scheduler_ledger',
    '_ensure_router_scheduler_ledger',
    '_router_scheduler_ledger_summary',
    '_router_scheduler_scope_for_action',
    '_action_is_startup_scoped',
    '_router_scheduler_progress_class',
    '_router_scheduler_barrier_kind',
    '_prepare_router_scheduled_action',
    '_record_router_scheduler_row',
    '_update_router_scheduler_row',
    '_controller_action_open_for',
    '_router_ownership_counts',
    '_empty_router_ownership_ledger',
    '_read_router_ownership_ledger',
    '_write_router_ownership_ledger',
    '_ensure_router_ownership_ledger',
    '_router_ownership_ledger_summary',
    '_record_router_ownership_entry',
    '_controller_action_completion_class',
    '_controller_action_ledger_has_prompt_header',
    '_write_controller_action_ledger',
    '_rebuild_controller_action_ledger',
    '_ensure_controller_action_ledger',
    '_controller_action_ledger_summary',
)

_LOCAL_NAMES = set(globals())
