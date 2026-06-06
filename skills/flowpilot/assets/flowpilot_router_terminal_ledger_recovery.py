"""Terminal recovery helpers for the FlowPilot router."""

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
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _recover_terminal_status_from_run_authorities(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str | None:
    _bind_router(router)
    recoverable_statuses = {'stopped_by_user', 'cancelled_by_user', 'protocol_dead_end', 'completed', 'closed'}
    run_id = str(run_state.get('run_id') or run_root.name)
    status = str(run_state.get('status') or '')
    if status in recoverable_statuses:
        return status
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}
    if str(current.get('run_id') or '') == run_id:
        current_status = str(current.get('status') or '')
        if current_status in recoverable_statuses:
            return current_status
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    for item in runs:
        if isinstance(item, dict) and str(item.get('run_id') or '') == run_id:
            index_status = str(item.get('status') or '')
            if index_status in recoverable_statuses:
                return index_status
    lifecycle = read_json_if_exists(_lifecycle_record_path(run_root)) or {}
    lifecycle_status = str(lifecycle.get('status') or '')
    if lifecycle_status in recoverable_statuses:
        return lifecycle_status
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    frontier_status = str(frontier.get('status') or '')
    if frontier.get('terminal') is True and frontier_status in recoverable_statuses:
        return frontier_status
    return None

def reconcile_current_run(router: ModuleType, project_root: Path) -> dict[str, Any]:
    _bind_router(router)
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = router.load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError('run state is missing')
    repaired: dict[str, Any] = {'prompt_delivery_contexts': 0, 'role_output_envelope_hashes': 0, 'terminal_lifecycle': False, 'terminal_lifecycle_record_written': False, 'terminal_closure_status_recovered': False, 'terminal_status_recovered_from_authority': False, 'non_current_running_index_entries': 0, 'scheduled_controller_receipts': {'changed': False, 'reconciled': 0, 'blocked': 0}, 'controller_boundary_projection': {'changed': False, 'reason': 'not_run'}}
    status = str(run_state.get('status') or '')
    flags = run_state.setdefault('flags', {})
    recovered_terminal_status = router._recover_terminal_status_from_run_authorities(project_root, run_root, run_state)
    if recovered_terminal_status and status not in RUN_TERMINAL_STATUSES:
        run_state['status'] = recovered_terminal_status
        status = recovered_terminal_status
        repaired['terminal_status_recovered_from_authority'] = True
        if recovered_terminal_status == 'closed':
            flags['terminal_closure_approved'] = True
            repaired['terminal_closure_status_recovered'] = True
    if status == 'stopped_by_user':
        flags['run_stopped_by_user'] = True
    elif status == 'cancelled_by_user':
        flags['run_cancelled_by_user'] = True
    elif status not in RUN_TERMINAL_STATUSES and router._terminal_closure_suite_is_closed(run_root):
        run_state['status'] = 'closed'
        flags['terminal_closure_approved'] = True
        status = 'closed'
        repaired['terminal_closure_status_recovered'] = True
    mode = _terminal_lifecycle_mode(run_state)
    if mode:
        run_state['status'] = mode
        run_state['phase'] = 'terminal'
        run_state['holder'] = 'controller'
        run_state['pending_action'] = None
        reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event='reconcile_current_run')
        lifecycle_path = _lifecycle_record_path(run_root)
        if not lifecycle_path.exists():
            write_json(lifecycle_path, {'schema_version': 'flowpilot.run_lifecycle.v1', 'run_id': run_state.get('run_id'), 'status': mode, 'request_event': 'reconcile_current_run', 'reason': 'terminal_lifecycle_reconciled_from_existing_authorities', 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'reconciliation': reconciliation, 'reconciled_at': utc_now()})
            append_history(run_state, 'run_lifecycle_record_written_by_reconcile', {'lifecycle_path': project_relative(project_root, lifecycle_path), 'status': mode})
            repaired['terminal_lifecycle_record_written'] = True
        _sync_current_and_index_status(project_root, run_state)
        repaired['terminal_lifecycle'] = True
    repaired['prompt_delivery_contexts'] = _repair_prompt_delivery_contexts(project_root, run_root, run_state)
    repaired['role_output_envelope_hashes'] = _repair_role_output_envelope_hashes(project_root, run_root)
    repaired['scheduled_controller_receipts'] = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    repaired['controller_boundary_projection'] = _reconcile_controller_boundary_confirmation_projection(project_root, run_root, run_state, source='reconcile_current_run_projection_repair')
    router._refresh_route_memory(project_root, run_root, run_state, trigger='reconcile_current_run')
    repaired['non_current_running_index_entries'] = router._reconcile_non_current_running_index_entries(project_root, run_state)
    router._sync_derived_run_views(project_root, run_root, run_state, reason='reconcile_current_run')
    append_history(run_state, 'router_reconciled_current_run', repaired)
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'repaired': repaired}

__all__ = (
    '_recover_terminal_status_from_run_authorities',
    'reconcile_current_run',
)

_LOCAL_NAMES = set(globals())
