"""Scheduled Controller receipt reconciliation and backfill helpers.

Receives the router facade explicitly so shared state writers and
public entrypoints keep the bound-router compatibility contract.
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

__all__ = (
    '_scheduler_row_reconciliation_for_entry',
    '_backfill_scheduler_row_from_reconciled_controller_action',
    '_canonicalize_legacy_startup_daemon_reconciliation',
    '_reconcile_scheduled_controller_action_receipts',
)

_LOCAL_NAMES = set(globals())
