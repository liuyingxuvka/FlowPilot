"""startup bootloader progress selection helpers for ``flowpilot_router_startup_bootloader``.

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


OWNER_MODULE = 'flowpilot_router_startup_bootloader'

def _startup_bootloader_open_entries_by_action_type(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    _bind_router(router)
    run_state, run_root = router._startup_run_state_if_ready(project_root, state)
    if run_state is None or run_root is None:
        return {}
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {}
    open_entries: dict[str, list[dict[str, Any]]] = {}
    for action_path in sorted(action_dir.glob('*.json')):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES and entry.get('router_reconciliation_status') == 'reconciled':
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        scope_kind = str(entry.get('scope_kind') or action.get('scope_kind') or '')
        if scope_kind != 'startup' and (not router._action_is_startup_scoped(action)):
            continue
        action_type = str(entry.get('action_type') or action.get('action_type') or '')
        if not action_type:
            continue
        open_entries.setdefault(action_type, []).append(entry)
    return open_entries

def _startup_open_entry_progress_class(router: ModuleType, entry: dict[str, Any]) -> str:
    _bind_router(router)
    action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
    explicit = str(action.get('router_scheduler_progress_class') or action.get('scheduler_progress_class') or '').strip()
    if explicit:
        return explicit
    return router._router_scheduler_progress_class(action or {'action_type': entry.get('action_type'), 'scope_kind': 'startup'})

def _startup_bootloader_entry_is_nonblocking(router: ModuleType, entry: dict[str, Any]) -> bool:
    _bind_router(router)
    return router._startup_open_entry_progress_class(entry) in {'parallel_obligation', 'local_dependency'}

def _startup_bootloader_action_depends_on_role_slots(router: ModuleType, action_type: str) -> bool:
    _bind_router(router)
    return action_type == 'inject_role_core_prompts'

def _next_boot_action(router: ModuleType, project_root: Path | None, state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    if not state.get('router_loaded'):
        return {'action_type': 'load_router', 'flag': 'router_loaded', 'label': 'bootloader_router_loaded', 'summary': 'Load the FlowPilot router and initialize bootstrap state.', 'actor': 'bootloader'}
    open_entries = router._startup_bootloader_open_entries_by_action_type(project_root, state) if project_root is not None else {}
    flags = state.setdefault('flags', {})
    role_slots_open = bool(open_entries.get('start_role_slots')) and (not bool(flags.get('roles_started')))
    for action in BOOT_ACTIONS:
        action_type = str(action['action_type'])
        if action_type == 'create_heartbeat_automation' and (not router._scheduled_continuation_requested(state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {})):
            continue
        if flags.get(action['flag']):
            continue
        if role_slots_open and router._startup_bootloader_action_depends_on_role_slots(action_type):
            continue
        entries = open_entries.get(action_type) or []
        if any((router._startup_bootloader_entry_is_nonblocking(entry) for entry in entries)):
            continue
        if not flags.get(action['flag']):
            return action
    return None

def _bootstrap_startup_cancelled(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    return state.get('status') == 'startup_cancelled' or state.get('startup_state') == 'startup_cancelled'

def _startup_bootloader_has_remaining_work(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = state.get('flags') if isinstance(state.get('flags'), dict) else {}
    startup_answers = state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {}
    for action in BOOT_ACTIONS:
        action_type = str(action.get('action_type') or '')
        if action_type == 'create_heartbeat_automation' and (not router._scheduled_continuation_requested(startup_answers)):
            continue
        if not bool(flags.get(str(action.get('flag') or ''))):
            return True
    return False

def _startup_daemon_controls_bootstrap(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    if router._bootstrap_startup_cancelled(state):
        return False
    flags = state.get('flags') if isinstance(state.get('flags'), dict) else {}
    return bool(state.get('router_loaded')) and bool(flags.get('run_shell_created')) and bool(flags.get('current_pointer_written')) and bool(flags.get('run_index_updated')) and bool(flags.get('router_daemon_started')) and router._startup_bootloader_has_remaining_work(state)

def _daemon_scheduled_bootloader_action(router: ModuleType, action: dict[str, Any] | None) -> bool:
    _bind_router(router)
    return isinstance(action, dict) and (bool(action.get('startup_daemon_scheduled')) or bool(action.get('scheduled_by_router_daemon')))

def compute_bootloader_action(router: ModuleType, project_root: Path, state: dict[str, Any], *, daemon_tick: bool=False) -> dict[str, Any] | None:
    _bind_router(router)
    if state.get('status') == 'startup_cancelled' or state.get('startup_state') == 'startup_cancelled':
        bootstrap_rel = project_relative(project_root, bootstrap_state_path(project_root, state))
        return make_action(action_type='startup_cancelled', actor='bootloader', label='startup_cancelled_by_ui', summary='FlowPilot startup was cancelled from the native startup intake UI; no run, roles, heartbeat, Cockpit, or Controller may start.', allowed_reads=[bootstrap_rel], allowed_writes=[], extra={'apply_required': False, 'terminal': True, 'requires_user': False, 'requires_payload': None, 'startup_cancelled': True})
    if state.get('pending_action'):
        return state['pending_action']
    if router._startup_daemon_controls_bootstrap(state) and (not daemon_tick):
        return None
    boot_action = router._next_boot_action(project_root, state)
    if boot_action is None:
        return None
    bootstrap_rel = project_relative(project_root, bootstrap_state_path(project_root, state))
    extra_fields = {'requires_user': bool(boot_action.get('requires_user', False)), 'requires_host_automation': bool(boot_action.get('requires_host_automation', False)), 'terminal_for_turn': bool(boot_action.get('terminal_for_turn', False)), 'requires_payload': boot_action.get('requires_payload'), 'questions': boot_action.get('questions', []), 'postcondition': boot_action['flag']}
    if daemon_tick:
        extra_fields.update({'startup_daemon_scheduled': True, 'scheduled_by_router_daemon': True, 'scope_kind': 'startup', 'scope_id': 'startup', 'controller_table': 'runtime/controller_action_ledger.json', 'router_scheduler_table': 'runtime/router_scheduler_ledger.json', 'controller_table_contract': 'simple_work_board', 'normal_progress_source': 'runtime/router_daemon_status.json_and_controller_action_ledger', 'controller_checks_off_row_when_done': True, 'router_retains_ordering_and_barrier_metadata': True})
    additional_allowed_reads: list[str] = []
    additional_allowed_writes: list[str] = []
    if boot_action['action_type'] == 'open_startup_intake_ui':
        extra_fields.update(router._startup_intake_ui_action_extra(project_root, state))
    if boot_action['action_type'] == 'emit_startup_banner':
        extra_fields.update(router._startup_banner_display())
    if boot_action['action_type'] == 'record_user_request' and router._confirmed_startup_intake(state) is not None:
        extra_fields['requires_user'] = False
        extra_fields['requires_payload'] = None
        extra_fields['summary'] = 'Record a sealed user request reference from the native startup intake UI artifacts.'
    if boot_action['action_type'] == 'start_role_slots':
        extra_fields.update(router._role_spawn_action_extra(state))
    if boot_action['action_type'] == 'start_router_daemon':
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        extra_fields.update({'formal_startup_daemon_required': True, 'daemon_off_option_allowed': False, 'tick_interval_seconds': ROUTER_DAEMON_TICK_SECONDS, 'lock_path': project_relative(project_root, _router_daemon_lock_path(run_root)), 'status_path': project_relative(project_root, _router_daemon_status_path(run_root)), 'controller_action_ledger_path': project_relative(project_root, _controller_action_ledger_path(run_root)), 'startup_readiness_contract': {'requires_live_lock': True, 'requires_status_file': True, 'requires_controller_action_ledger': True, 'failure_blocks_controller_core': True}})
        additional_allowed_reads.extend([project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, _router_daemon_lock_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))])
        additional_allowed_writes.extend([project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, _router_daemon_lock_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_daemon_event_log_path(run_root)), project_relative(project_root, _runtime_dir(run_root) / 'router_daemon.startup.out.txt'), project_relative(project_root, _runtime_dir(run_root) / 'router_daemon.startup.err.txt')])
    heartbeat_action: dict[str, Any] | None = None
    if boot_action['action_type'] == 'create_heartbeat_automation':
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        heartbeat_action = router._next_startup_heartbeat_binding_action(project_root, run_state, run_root)
        if heartbeat_action is None:
            raise RouterError('startup heartbeat action requested but no heartbeat binding action is available')
        for key, value in heartbeat_action.items():
            if key not in {'action_id', 'action_type', 'actor', 'allowed_reads', 'allowed_writes', 'created_at', 'label', 'schema_version', 'source', 'summary'}:
                extra_fields[key] = value
    action = make_action(action_type=str(boot_action['action_type']), actor=str((heartbeat_action or boot_action)['actor']), label=str((heartbeat_action or boot_action)['label']), summary=str((heartbeat_action or boot_action)['summary']), allowed_reads=[bootstrap_rel] + list((heartbeat_action or {}).get('allowed_reads') or []) + additional_allowed_reads, allowed_writes=[bootstrap_rel] + list((heartbeat_action or {}).get('allowed_writes') or []) + additional_allowed_writes, card_id=boot_action.get('card_id'), extra=extra_fields)
    state['pending_action'] = action
    if state.get('router_loaded'):
        state['router_action_requests'] = int(state.get('router_action_requests', 0)) + 1
    append_history(state, 'router_computed_next_bootloader_action', {'action_type': action['action_type']})
    router.save_bootstrap_state(project_root, state)
    return action

__all__ = (
    '_startup_bootloader_open_entries_by_action_type',
    '_startup_open_entry_progress_class',
    '_startup_bootloader_entry_is_nonblocking',
    '_startup_bootloader_action_depends_on_role_slots',
    '_next_boot_action',
    '_bootstrap_startup_cancelled',
    '_startup_bootloader_has_remaining_work',
    '_startup_daemon_controls_bootstrap',
    '_daemon_scheduled_bootloader_action',
    'compute_bootloader_action',
)

_LOCAL_NAMES = set(globals())
