"""startup daemon bootloader scheduling and reconciliation helpers for ``flowpilot_router_startup_bootloader``.

This child module is imported by the compatibility facade and keeps
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


OWNER_MODULE = 'flowpilot_router_startup_bootloader'

def _complete_startup_daemon_bootloader_row(router: ModuleType, project_root: Path, bootstrap_state: dict[str, Any], scheduled_action: dict[str, Any], *, applied_action_type: str) -> dict[str, Any] | None:
    _bind_router(router)
    if not router._daemon_scheduled_bootloader_action(scheduled_action):
        return None
    action_id = str(scheduled_action.get('controller_action_id') or '').strip()
    row_id = str(scheduled_action.get('router_scheduler_row_id') or '').strip()
    if not action_id:
        return None
    run_state, run_root = router._startup_run_state_if_ready(project_root, bootstrap_state)
    if run_state is None or run_root is None:
        return None
    action_path = _controller_action_path(run_root, action_id)
    entry = read_json_if_exists(action_path)
    if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        return None
    existing_reconciliation = entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else {}
    if entry.get('router_reconciliation_status') == 'reconciled' and existing_reconciliation.get('source') == 'startup_bootloader_controller_receipt':
        scheduler_backfill = router._backfill_scheduler_row_from_reconciled_controller_action(project_root, run_root, run_state, entry, source='startup_bootloader_already_reconciled_scheduler_backfill')
        return {'controller_action_id': action_id, 'router_scheduler_row_id': row_id, 'already_reconciled': True, 'router_reconciliation': existing_reconciliation, 'scheduler_backfill': scheduler_backfill}
    receipt = router._write_controller_receipt(project_root, run_root, run_state, action_id=action_id, status='done', payload={'source': 'startup_daemon_bootloader_apply', 'applied_action_type': applied_action_type, 'bootstrap_postcondition': scheduled_action.get('postcondition'), 'bootstrap_flag_satisfied': bool((bootstrap_state.get('flags') if isinstance(bootstrap_state.get('flags'), dict) else {}).get(str(scheduled_action.get('postcondition') or '')))})
    scheduled_reconciliation = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    entry = read_json_if_exists(action_path)
    reconciliation = entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else {}
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(run_state, 'router_folded_startup_daemon_bootloader_row_through_receipt', {'action_type': scheduled_action.get('action_type'), 'controller_action_id': action_id, 'router_scheduler_row_id': row_id, 'receipt_status': receipt.get('status'), 'scheduled_reconciliation': scheduled_reconciliation, 'router_reconciliation': reconciliation})
    router.save_run_state(run_root, run_state)
    return {'controller_action_id': action_id, 'router_scheduler_row_id': row_id, 'receipt': receipt, 'scheduled_reconciliation': scheduled_reconciliation, 'router_reconciliation': reconciliation}

def _startup_daemon_schedule_bootloader_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, lock: dict[str, Any] | None=None, source: str='router_daemon_tick') -> dict[str, Any]:
    _bind_router(router)
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    if not router._startup_daemon_controls_bootstrap(bootstrap):
        status = _write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_startup_driver_idle', current_action=None, lock=lock)
        router.save_run_state(run_root, run_state)
        return {'scheduled': False, 'reason': 'startup_not_daemon_controlled', 'tick_at': status['last_tick_at'], 'terminal': bool(status.get('run_lifecycle_status'))}
    queued_actions: list[dict[str, Any]] = []
    current_action: dict[str, Any] | None = None
    current_entry: dict[str, Any] | None = None
    existing = False
    stop_reason = 'no_bootloader_action'
    for _index in range(ROUTER_DAEMON_MAX_QUEUE_ACTIONS_PER_TICK):
        pending = bootstrap.get('pending_action')
        if isinstance(pending, dict):
            if not router._daemon_scheduled_bootloader_action(pending):
                return {'scheduled': False, 'reason': 'non_daemon_bootloader_pending', 'action': pending}
            action = router._prepare_router_scheduled_action(project_root, run_root, run_state, pending)
            existing = True
        else:
            action = router.compute_bootloader_action(project_root, bootstrap, daemon_tick=True)
            if not isinstance(action, dict):
                stop_reason = 'no_bootloader_action'
                break
            action['startup_daemon_scheduled'] = True
            action['scheduled_by_router_daemon'] = True
            action['startup_daemon_scheduler_source'] = source
            action['scope_kind'] = 'startup'
            action['scope_id'] = 'startup'
            action['controller_table_contract'] = 'simple_work_board'
            action['normal_progress_source'] = 'runtime/router_daemon_status.json_and_controller_action_ledger'
            action = router._prepare_router_scheduled_action(project_root, run_root, run_state, action)
            existing = False
        entry = router._write_controller_action_entry(project_root, run_root, run_state, action)
        current_action = action
        current_entry = entry
        bootstrap['pending_action'] = action
        queued_actions.append({'action_type': action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'progress_class': action.get('router_scheduler_progress_class'), 'barrier_kind': action.get('router_scheduler_barrier_kind'), 'existing': existing})
        append_history(run_state, 'router_daemon_scheduled_startup_bootloader_action', {'action_type': action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'source': source, 'existing': existing})
        if not _router_daemon_can_continue_after_enqueued_action(action):
            stop_reason = 'barrier'
            router.save_bootstrap_state(project_root, bootstrap)
            break
        bootstrap['pending_action'] = None
        append_history(bootstrap, 'startup_daemon_deferred_nonblocking_bootloader_row', {'action_type': action.get('action_type'), 'controller_action_id': entry.get('action_id'), 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'progress_class': action.get('router_scheduler_progress_class')})
        router.save_bootstrap_state(project_root, bootstrap)
        stop_reason = 'continued_after_nonblocking_startup_row'
    else:
        stop_reason = 'max_actions_per_tick'
    if current_action is None:
        status = _write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_startup_driver_idle', current_action=None, lock=lock)
        router.save_run_state(run_root, run_state)
        return {'scheduled': False, 'reason': 'no_bootloader_action', 'tick_at': status['last_tick_at'], 'terminal': bool(status.get('run_lifecycle_status'))}
    router.save_bootstrap_state(project_root, bootstrap)
    status = _write_router_daemon_status(project_root, run_root, run_state, lifecycle_status='daemon_startup_driver_active', current_action=current_action, lock=lock)
    router.save_run_state(run_root, run_state)
    return {'scheduled': True, 'existing': bool(current_action and queued_actions[-1].get('existing')) if queued_actions else False, 'action': current_action, 'controller_action_id': current_entry.get('action_id') if isinstance(current_entry, dict) else None, 'router_scheduler_row_id': current_action.get('router_scheduler_row_id') if isinstance(current_action, dict) else None, 'queued_count': len(queued_actions), 'queued_actions': queued_actions, 'queue_stop_reason': stop_reason, 'tick_at': status['last_tick_at'], 'terminal': bool(status.get('run_lifecycle_status'))}

__all__ = (
    '_complete_startup_daemon_bootloader_row',
    '_startup_daemon_schedule_bootloader_action',
)

_LOCAL_NAMES = set(globals())
