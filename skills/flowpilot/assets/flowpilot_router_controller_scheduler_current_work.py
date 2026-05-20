"""Current-work ownership projection helpers for scheduler status."""

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
import flowpilot_closure_kernel
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
    return flowpilot_closure_kernel.closure_blocks_progress('packet_holder', {'status': status})

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

def _current_work_from_active_batch_summary(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    try:
        active_batch = router._current_status_active_batch_summary(run_root)
    except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(active_batch, dict):
        return None
    candidates: list[dict[str, Any]] = []
    for key in ('active_partial_batches', 'batches'):
        items = active_batch.get(key)
        if isinstance(items, list):
            candidates.extend([item for item in items if isinstance(item, dict)])
    for batch in candidates:
        missing_roles = [str(role).strip() for role in batch.get('missing_roles') or [] if str(role).strip()]
        if not missing_roles or batch.get('all_results_returned'):
            continue
        returned_roles = [str(role).strip() for role in batch.get('returned_roles') or [] if str(role).strip()]
        batch_kind = str(batch.get('batch_kind') or 'packet_batch')
        batch_id = str(batch.get('batch_id') or '').strip()
        source_path = None
        if batch_id:
            try:
                source_path = project_relative(project_root, router._parallel_packet_batch_path(run_root, batch_id))
            except (RouterError, OSError, ValueError, TypeError):
                source_path = None
        owner_key = ','.join(missing_roles)
        task = f"Wait for {', '.join(missing_roles)} to return {batch_kind.replace('_', ' ')} result"
        if len(missing_roles) > 1:
            task += "s"
        return router._current_work_payload(
            owner_key=owner_key,
            task_label=task,
            source='packet_batch_member_status',
            source_path=source_path,
            wait_class='role_decision',
            diagnostics={
                'batch_kind': batch_kind,
                'batch_id': batch_id or None,
                'missing_roles': missing_roles,
                'returned_roles': returned_roles,
                'packet_count': batch.get('packet_count'),
                'results_returned': batch.get('results_returned'),
                'partial_results_returned': bool(batch.get('partial_results_returned')),
                'all_results_returned': bool(batch.get('all_results_returned')),
            },
        )
    return None

def _pending_action_has_controller_authority(router: ModuleType, pending: dict[str, Any], controller_ledger: dict[str, Any]) -> bool:
    _bind_router(router)
    if not isinstance(pending, dict) or not pending:
        return False
    action_id = str(pending.get('controller_action_id') or '').strip()
    if not action_id:
        try:
            action_id = router._controller_action_id_for_action(pending)
        except (RouterError, ValueError, TypeError):
            action_id = ''
    if not action_id:
        return True
    active_ids: set[str] = set()
    for key in ('pending_action_ids', 'waiting_action_ids', 'passive_wait_action_ids'):
        values = controller_ledger.get(key) if isinstance(controller_ledger, dict) else []
        if isinstance(values, list):
            active_ids.update(str(value) for value in values if value)
    return action_id in active_ids

def _pending_role_wait_should_use_batch_projection(router: ModuleType, pending: dict[str, Any]) -> bool:
    _bind_router(router)
    if not isinstance(pending, dict) or pending.get('action_type') != 'await_role_decision':
        return False
    target = str(pending.get('to_role') or pending.get('waiting_for_role') or pending.get('target_role') or '').strip()
    if target.startswith('worker_') or ',' in target:
        return True
    allowed = pending.get('allowed_external_events')
    return bool(isinstance(allowed, list) and any(str(event).startswith('worker_') for event in allowed))

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
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    if terminal_mode:
        return router._current_work_payload(
            owner_key='controller',
            task_label='Run is terminal; only terminal cleanup or summary is allowed',
            source='terminal_lifecycle',
            source_path=project_relative(project_root, router.run_state_path(run_root)),
            diagnostics={
                'run_status': run_state.get('status'),
                'terminal_lifecycle_status': terminal_mode,
                'nonterminal_work_allowed': False,
            },
        )
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    if controller_ledger is None:
        controller_ledger = router._controller_action_ledger_summary(run_root)
    if pending and _pending_role_wait_should_use_batch_projection(router, pending):
        batch_payload = _current_work_from_active_batch_summary(router, project_root, run_root)
        if batch_payload:
            return batch_payload
    if pending and _pending_action_has_controller_authority(router, pending, controller_ledger):
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

__all__ = (
    '_current_work_owner_kind',
    '_current_work_owner_label',
    '_current_work_payload',
    '_current_work_from_action',
    '_packet_status_allows_current_work',
    '_current_work_from_packet_ledger',
    '_current_work_from_active_batch_summary',
    '_pending_action_has_controller_authority',
    '_pending_role_wait_should_use_batch_projection',
    '_current_work_from_passive_waits',
    '_derive_current_work',
)

_LOCAL_NAMES = set(globals())
