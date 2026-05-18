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
    if boot_action['action_type'] == 'record_startup_answers':
        extra_fields['payload_contract'] = _startup_answers_payload_contract()
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

def _ensure_pending(router: ModuleType, state: dict[str, Any], action_type: str) -> dict[str, Any]:
    _bind_router(router)
    pending = state.get('pending_action')
    if not isinstance(pending, dict):
        raise RouterError("no pending router action; run 'next' before applying an action")
    if pending.get('action_type') != action_type:
        raise RouterError(f"pending action is {pending.get('action_type')!r}, not {action_type!r}")
    return pending

def _set_boot_flag(router: ModuleType, project_root: Path, state: dict[str, Any], flag: str, label: str, details: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    if flag == 'router_loaded':
        state['router_loaded'] = True
        state['status'] = 'running'
    else:
        state['flags'][flag] = True
        state['bootloader_actions'] = int(state.get('bootloader_actions', 0)) + 1
    state['pending_action'] = None
    append_history(state, label, details)
    router.save_bootstrap_state(project_root, state)

def _startup_run_state_if_ready(router: ModuleType, project_root: Path, bootstrap_state: dict[str, Any]) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    _bind_router(router)
    run_root_rel = str(bootstrap_state.get('run_root') or '')
    if not run_root_rel:
        return (None, None)
    run_root = project_root / run_root_rel
    run_state = read_json_if_exists(router.run_state_path(run_root))
    if run_state.get('schema_version') != RUN_STATE_SCHEMA:
        return (None, run_root)
    return (run_state, run_root)

def _sync_startup_bootstrap_flags_to_run_state(router: ModuleType, bootstrap_state: dict[str, Any], run_state: dict[str, Any]) -> None:
    _bind_router(router)
    bootstrap_flags = bootstrap_state.get('flags') if isinstance(bootstrap_state.get('flags'), dict) else {}
    run_flags = run_state.setdefault('flags', {})
    for flag in ('startup_state_written_awaiting_answers', 'dialog_stopped_for_answers', 'startup_answers_recorded', 'banner_emitted', 'roles_started', 'role_core_prompts_injected', 'continuation_binding_recorded'):
        if bootstrap_flags.get(flag):
            run_flags[flag] = True

def _fold_stable_startup_role_flags_from_bootstrap(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    bootstrap_path = run_root / 'bootstrap' / 'startup_state.json'
    if not bootstrap_path.exists():
        return {'changed': False, 'exists': False}
    _raise_if_runtime_write_active(bootstrap_path)
    bootstrap = read_daemon_critical_json_if_exists(bootstrap_path)
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    roles_started = bool(bootstrap_flags.get('roles_started'))
    core_prompts_injected = bool(bootstrap_flags.get('role_core_prompts_injected'))
    if roles_started != core_prompts_injected:
        return {'changed': False, 'exists': True, 'waiting_for_settlement': True, 'roles_started': roles_started, 'role_core_prompts_injected': core_prompts_injected}
    if not roles_started:
        return {'changed': False, 'exists': True}
    flags = run_state.setdefault('flags', {})
    missing = [flag for flag in ('roles_started', 'role_core_prompts_injected') if not flags.get(flag)]
    if not missing:
        return {'changed': False, 'exists': True, 'already_folded': True}
    flags['roles_started'] = True
    flags['role_core_prompts_injected'] = True
    append_history(run_state, 'router_folded_startup_role_flags_from_bootstrap', {'source': 'daemon_settlement_barrier', 'bootstrap_state_path': project_relative(project_root, bootstrap_path), 'folded_flags': ['roles_started', 'role_core_prompts_injected']})
    return {'changed': True, 'exists': True, 'folded_flags': ['roles_started', 'role_core_prompts_injected']}

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

def _finish_bootloader_action(router: ModuleType, project_root: Path, state: dict[str, Any], scheduled_action: dict[str, Any], *, flag: str, label: str, action_type: str, result_extra: dict[str, Any]) -> None:
    _bind_router(router)
    router._set_boot_flag(project_root, state, flag, label, {'action_type': action_type})
    completion = router._complete_startup_daemon_bootloader_row(project_root, state, scheduled_action, applied_action_type=action_type)
    if completion is not None:
        result_extra['startup_daemon_row_completion'] = {'controller_action_id': completion.get('controller_action_id'), 'router_scheduler_row_id': completion.get('router_scheduler_row_id')}
    if router._startup_daemon_controls_bootstrap(state):
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        schedule = router._startup_daemon_schedule_bootloader_action(project_root, run_root, run_state, source='bootloader_apply_catchup')
        if schedule.get('scheduled'):
            next_action = schedule.get('action') if isinstance(schedule.get('action'), dict) else {}
            result_extra['startup_daemon_next_action'] = {'action_type': next_action.get('action_type'), 'controller_action_id': schedule.get('controller_action_id'), 'router_scheduler_row_id': schedule.get('router_scheduler_row_id'), 'existing': bool(schedule.get('existing'))}

def apply_bootloader_action(router: ModuleType, project_root: Path, action_type: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    state = router.load_bootstrap_state(project_root, create_if_missing=False)
    pending = router._ensure_pending(state, action_type)
    payload = payload or {}
    result_extra: dict[str, Any] = {}
    if action_type == 'load_router':
        router._set_boot_flag(project_root, state, 'router_loaded', 'bootloader_router_loaded')
        return {'ok': True, 'applied': action_type}
    action_meta = next((item for item in BOOT_ACTIONS if item['action_type'] == action_type), None)
    if action_meta is None and action_type == 'ask_startup_questions':
        action_meta = {'action_type': 'ask_startup_questions', 'flag': 'startup_questions_asked', 'label': 'legacy_startup_questions_asked_from_router'}
    if action_meta is None:
        raise RouterError(f'unknown bootloader action: {action_type}')
    flag = str(action_meta['flag'])
    if action_type == 'open_startup_intake_ui':
        result_extra.update(router._apply_startup_intake_result_to_bootstrap(project_root, state, payload))
    elif action_type == 'ask_startup_questions':
        state['startup_state'] = 'awaiting_answers_stopped'
        state['flags']['startup_state_written_awaiting_answers'] = True
        state['flags']['dialog_stopped_for_answers'] = True
    elif action_type == 'write_startup_awaiting_answers_state':
        state['startup_state'] = 'awaiting_answers'
    elif action_type == 'stop_for_startup_answers':
        state['startup_state'] = 'awaiting_answers_stopped'
    elif action_type == 'record_startup_answers':
        startup_answers = router._validate_startup_answers(payload)
        state['startup_answers'] = startup_answers
        interpretation = router._validate_startup_answer_interpretation(payload, startup_answers)
        if interpretation:
            state['startup_answer_interpretation'] = interpretation
        else:
            state['startup_answer_interpretation'] = None
        state['startup_state'] = 'answers_complete'
    elif action_type == 'emit_startup_banner':
        banner = router._startup_banner_display()
        confirmation = router._display_confirmation_for_action(payload, pending)
        banner['dialog_display_confirmation'] = confirmation
        state['startup_banner_path'] = banner['display_path']
        state['startup_banner_display'] = banner
        state['startup_banner_dialog_display_confirmation'] = confirmation
        result_extra.update(banner)
    elif action_type == 'create_run_shell':
        run_id = str(payload.get('run_id') or state.get('run_id') or router._create_run_id())
        run_root = project_root / '.flowpilot' / 'runs' / run_id
        run_root.mkdir(parents=True, exist_ok=True)
        state['run_id'] = run_id
        state['run_root'] = project_relative(project_root, run_root)
        write_json(run_root / 'run.json', {'schema_version': 'flowpilot.run.v1', 'run_id': run_id, 'created_at': utc_now(), 'startup_model': 'prompt_isolated_router', 'legacy_backup_required': True})
    elif action_type == 'write_current_pointer':
        if not state.get('run_id') or not state.get('run_root'):
            raise RouterError('cannot write current pointer before run shell exists')
        write_json(project_root / '.flowpilot' / 'current.json', {'schema_version': 'flowpilot.current.v1', 'current_run_id': state['run_id'], 'current_run_root': state['run_root'], 'startup_bootstrap_path': project_relative(project_root, bootstrap_state_path(project_root, state)), 'status': 'running', 'updated_at': utc_now()})
    elif action_type == 'update_run_index':
        if not state.get('run_id') or not state.get('run_root'):
            raise RouterError('cannot update index before run shell exists')
        index_path = project_root / '.flowpilot' / 'index.json'
        index = read_json_if_exists(index_path) or {'schema_version': 'flowpilot.index.v1', 'runs': []}
        runs = index.setdefault('runs', [])
        if not any((isinstance(item, dict) and item.get('run_id') == state['run_id'] for item in runs)):
            runs.append({'run_id': state['run_id'], 'run_root': state['run_root'], 'created_at': utc_now(), 'status': 'running'})
        index['current_run_id'] = state['run_id']
        index['updated_at'] = utc_now()
        write_json(index_path, index)
    elif action_type == 'copy_runtime_kit':
        run_root = project_root / str(state['run_root'])
        _copy_runtime_kit_into_run_root(run_root)
    elif action_type == 'fill_runtime_placeholders':
        run_root = project_root / str(state['run_root'])
        interpretation = state.get('startup_answer_interpretation') if isinstance(state.get('startup_answer_interpretation'), dict) else None
        interpretation_path = run_root / 'startup_answer_interpretation.json'
        if interpretation:
            write_json(interpretation_path, interpretation)
        write_json(run_root / 'startup_answers.json', {'schema_version': 'flowpilot.startup_answers.v1', 'run_id': state['run_id'], 'answers': state.get('startup_answers') or {}, 'startup_answer_interpretation_path': project_relative(project_root, interpretation_path) if interpretation else None, 'recorded_at': utc_now()})
    elif action_type == 'initialize_mailbox':
        run_root = project_root / str(state['run_root'])
        for rel in ('mailbox/system_cards', 'mailbox/inbox', 'mailbox/outbox', 'mailbox/outbox/card_acks', 'runtime_receipts/card_reads', 'runtime_receipts/role_io_protocol', 'packets'):
            (run_root / rel).mkdir(parents=True, exist_ok=True)
        write_json(run_root / 'packet_ledger.json', router._create_empty_packet_ledger(project_root, str(state['run_id']), run_root))
        write_json(run_root / 'prompt_delivery_ledger.json', {'schema_version': 'flowpilot.prompt_delivery_ledger.v1', 'run_id': state['run_id'], 'deliveries': []})
        write_json(_card_ledger_path(run_root), _empty_card_ledger(str(state['run_id'])))
        write_json(_return_event_ledger_path(run_root), _empty_return_event_ledger(str(state['run_id'])))
        write_json(_role_io_protocol_ledger_path(run_root), _empty_role_io_protocol_ledger(str(state['run_id'])))
    elif action_type == 'record_user_request':
        run_root = project_root / str(state['run_root'])
        if router._confirmed_startup_intake(state) is not None and (not payload):
            intake_record = router._materialize_startup_intake_record(project_root, state, run_root)
            user_request = router._user_request_ref_from_startup_intake(project_root, state, intake_record)
            user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'source': 'startup_intake_ui', 'user_request_ref': user_request, 'startup_intake_record': intake_record, 'controller_may_read_body': False, 'body_text_included': False, 'recorded_at': utc_now()}
            state['startup_intake'] = intake_record
            state['startup_intake_record_path'] = intake_record['record_path']
            state['user_request_ref'] = user_request
        else:
            user_request = router._validate_user_request(payload)
            user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'user_request': user_request, 'recorded_at': utc_now()}
        write_json(run_root / 'user_request.json', user_request_record)
        state['user_request'] = user_request
        state['user_request_path'] = project_relative(project_root, run_root / 'user_request.json')
    elif action_type == 'write_user_intake':
        run_root = project_root / str(state['run_root'])
        user_request = state.get('user_request')
        if not isinstance(user_request, dict):
            raise RouterError('cannot write user_intake before record_user_request')
        if user_request.get('schema_version') == USER_REQUEST_REF_SCHEMA:
            body_text = router._build_user_intake_body_from_ref(project_root, user_request, state.get('startup_answers') or {})
            user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=body_text, startup_options=state.get('startup_answers') or {}, source='startup_intake_ui', body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, startup_intake_ref=user_request, router_owned_startup_material=True)
            write_json(run_root / 'mailbox' / 'outbox' / 'user_intake.json', user_intake)
            result_extra['user_intake_source'] = 'startup_intake_ui'
            result_extra['controller_may_read_body'] = False
            result_extra['reviewer_live_review_source'] = 'startup_intake_record'
            router._finish_bootloader_action(project_root, state, pending, flag=flag, label=str(pending['label']), action_type=action_type, result_extra=result_extra)
            result = {'ok': True, 'applied': action_type, 'postcondition': flag}
            result.update(result_extra)
            return result
        user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=json.dumps({'user_request': user_request, 'user_request_path': state.get('user_request_path'), 'startup_answers': state.get('startup_answers') or {}, 'startup_answers_path': project_relative(project_root, run_root / 'startup_answers.json'), 'startup_answer_interpretation_path': project_relative(project_root, run_root / 'startup_answer_interpretation.json') if isinstance(state.get('startup_answer_interpretation'), dict) else None}, indent=2, sort_keys=True), startup_options=state.get('startup_answers') or {}, body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, router_owned_startup_material=True)
        write_json(run_root / 'mailbox' / 'outbox' / 'user_intake.json', user_intake)
    elif action_type == 'start_role_slots':
        run_root = project_root / str(state['run_root'])
        role_slots = router._normalize_role_agent_records(state, payload)
        background_mode = (state.get('startup_answers') or {}).get('background_agents')
        write_json(run_root / 'crew_ledger.json', {'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': state['run_id'], 'background_agents_mode': background_mode, 'role_slots': role_slots, 'created_at': utc_now()})
        crew_memory_root = run_root / 'crew_memory'
        crew_memory_root.mkdir(parents=True, exist_ok=True)
        for role in CREW_ROLE_KEYS:
            write_json(crew_memory_root / f'{role}.json', router._create_empty_role_memory(str(state['run_id']), role))
        _append_role_io_protocol_injections(project_root, run_root, str(state['run_id']), role_slots, default_lifecycle_phase='fresh_spawn', resume_tick_id='manual-resume', source_action='start_role_slots')
        write_json(run_root / 'role_core_prompt_delivery.json', router._role_core_prompt_delivery_payload(project_root, run_root, str(state['run_id']), source_action='start_role_slots'))
        state.setdefault('flags', {})['role_core_prompts_injected'] = True
        append_history(state, 'role_core_prompts_delivered_during_start_role_slots', {'action_type': 'start_role_slots', 'postcondition': 'role_core_prompts_injected', 'delivery_mode': 'same_action_with_role_start'})
        result_extra['coalesced_postconditions'] = ['roles_started', 'role_core_prompts_injected']
        _ensure_startup_run_state(project_root, state)
    elif action_type == 'create_heartbeat_automation':
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        _write_host_heartbeat_binding(project_root, run_root, run_state, payload or {})
        run_state['flags']['continuation_binding_recorded'] = True
        run_state['events'].append({'event': 'host_records_heartbeat_binding', 'summary': EXTERNAL_EVENTS['host_records_heartbeat_binding']['summary'], 'payload': payload or {}, 'recorded_at': utc_now(), 'source_action': action_type, 'startup_phase': 'bootloader'})
        router.save_run_state(run_root, run_state)
    elif action_type == 'inject_role_core_prompts':
        run_root = project_root / str(state['run_root'])
        write_json(run_root / 'role_core_prompt_delivery.json', router._role_core_prompt_delivery_payload(project_root, run_root, str(state['run_id']), source_action='inject_role_core_prompts'))
    elif action_type == 'start_router_daemon':
        if not state.get('run_root'):
            raise RouterError('cannot start Router daemon before run shell exists')
        if not state.get('flags', {}).get('runtime_kit_copied'):
            _copy_runtime_kit_into_run_root(project_root / str(state['run_root']))
            state.setdefault('flags', {})['runtime_kit_copied'] = True
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        result_extra.update(_start_or_attach_formal_router_daemon(project_root, run_root, run_state))
    elif action_type == 'load_controller_core':
        run_state, run_root = _ensure_startup_run_state(project_root, state)
        router._sync_startup_bootstrap_flags_to_run_state(state, run_state)
        if not _formal_router_daemon_ready(project_root, run_root):
            raise RouterError('cannot load Controller core before the formal Router daemon is live and ready')
        run_state['status'] = 'controller_ready'
        run_state['holder'] = 'controller'
        run_state['flags']['controller_core_loaded'] = True
        boundary_reconciliation = router._record_controller_boundary_confirmation_from_core_load(project_root, run_root, run_state, pending, payload or {'controller_action_completed': True, 'controller_boundary_confirmation_source': 'load_controller_core'}, source='load_controller_core_apply')
        result_extra['controller_boundary_confirmation'] = boundary_reconciliation.get('controller_boundary_confirmation')
        result_extra['coalesced_postconditions'] = ['controller_core_loaded', 'controller_role_confirmed']
        router._refresh_route_memory(project_root, run_root, run_state, trigger='load_controller_core')
        write_json(router.run_state_path(run_root), run_state)
    else:
        raise RouterError(f'unimplemented action: {action_type}')
    router._finish_bootloader_action(project_root, state, pending, flag=flag, label=str(pending['label']), action_type=action_type, result_extra=result_extra)
    result = {'ok': True, 'applied': action_type, 'postcondition': flag}
    result.update(result_extra)
    return result

_LOCAL_NAMES = set(globals())
