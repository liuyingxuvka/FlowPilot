"""Coarse startup flow owner helpers for the FlowPilot router.

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

def _normalize_startup_question_stop_boundary(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    if state.get('status') == 'startup_cancelled' or state.get('startup_state') == 'startup_cancelled':
        return False
    flags = state.setdefault('flags', {})
    if not flags.get('startup_questions_asked'):
        return False
    if flags.get('startup_answers_recorded') or state.get('startup_answers'):
        return False
    changed = False
    if not flags.get('startup_state_written_awaiting_answers'):
        flags['startup_state_written_awaiting_answers'] = True
        changed = True
    if not flags.get('dialog_stopped_for_answers'):
        flags['dialog_stopped_for_answers'] = True
        changed = True
    if state.get('startup_state') != 'awaiting_answers_stopped':
        state['startup_state'] = 'awaiting_answers_stopped'
        changed = True
    pending = state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') in {'write_startup_awaiting_answers_state', 'stop_for_startup_answers'}:
        state['pending_action'] = None
        append_history(state, 'startup_question_stop_boundary_normalized', {'cleared_pending_action': pending.get('action_type')})
        changed = True
    return changed

def _startup_intake_ui_launcher_ref(router: ModuleType, project_root: Path) -> str:
    _bind_router(router)
    launcher = Path(__file__).resolve().parent / 'ui' / 'startup_intake' / 'flowpilot_startup_intake.ps1'
    try:
        return project_relative(project_root, launcher)
    except RouterError:
        return str(launcher)

def _startup_intake_output_dir_ref(router: ModuleType, project_root: Path, state: dict[str, Any]) -> str:
    _bind_router(router)
    run_id = str(state.get('run_id') or router._create_run_id())
    output_dir = project_root / '.flowpilot' / 'bootstrap' / 'startup_intake' / run_id
    return project_relative(project_root, output_dir)

def _startup_intake_result_payload_contract(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'payload_key': 'startup_intake_result', 'required': True, 'expected_shape': {'startup_intake_result': {'result_path': '<path returned by the native startup intake UI>'}}, 'result_schema_version': STARTUP_INTAKE_RESULT_SCHEMA, 'receipt_schema_version': STARTUP_INTAKE_RECEIPT_SCHEMA, 'envelope_schema_version': STARTUP_INTAKE_ENVELOPE_SCHEMA, 'formal_launch_provenance': {'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True}, 'output_dir': router._startup_intake_output_dir_ref(project_root, state), 'controller_body_boundary': {'controller_may_read_body': False, 'body_text_must_not_be_in_payload': True, 'allowed_controller_view': 'result/envelope paths, body hash, startup answers, and status only'}}

def _startup_intake_ui_action_extra(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    launcher = router._startup_intake_ui_launcher_ref(project_root)
    output_dir = router._startup_intake_output_dir_ref(project_root, state)
    command = ['powershell', '-STA', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', launcher, '-OutputDir', output_dir]
    return {'startup_intake_ui': {'schema_version': 'flowpilot.startup_intake_ui_launcher.v1', 'launcher_path': launcher, 'output_dir': output_dir, 'command': command, 'result_path_expected': f'{output_dir}/startup_intake_result.json', 'body_text_is_never_router_payload': True, 'cancel_result_is_terminal': True, 'headless_result_is_not_formal_startup': True}, 'payload_contract': router._startup_intake_result_payload_contract(project_root, state), 'plain_instruction': "Open the native FlowPilot startup intake UI with the provided command. Formal startup must use the interactive native UI result; do not use headless auto-confirmation, scripted result synthesis, chat substitution, or direct JSON creation. After the UI closes, return to Router daemon status and the Controller action ledger before continuing. Do not paste the user's work request into chat and do not include it in the Router payload."}

def _confirmed_startup_intake(router: ModuleType, state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    intake = state.get('startup_intake')
    if isinstance(intake, dict) and intake.get('status') == 'confirmed':
        return intake
    return None

def _forbidden_startup_intake_body_fields(router: ModuleType, payload: Any, prefix: str='') -> list[str]:
    _bind_router(router)
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_path = f'{prefix}.{key}' if prefix else str(key)
            if key in _FORBIDDEN_STARTUP_INTAKE_BODY_KEYS:
                found.append(key_path)
            found.extend(router._forbidden_startup_intake_body_fields(value, key_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(router._forbidden_startup_intake_body_fields(value, f'{prefix}[{index}]'))
    return found

def _resolve_existing_project_file(router: ModuleType, project_root: Path, raw_path: Any, label: str) -> Path:
    _bind_router(router)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise RouterError(f'startup intake {label} path is required')
    path = resolve_project_path(project_root, raw_path.strip()).resolve()
    project_relative(project_root, path)
    if not path.exists() or not path.is_file():
        raise RouterError(f'startup intake {label} file not found: {raw_path}')
    return path

def _same_project_file(router: ModuleType, project_root: Path, left: Any, right: Path) -> bool:
    _bind_router(router)
    if not isinstance(left, str) or not left.strip():
        return False
    return resolve_project_path(project_root, left).resolve() == right.resolve()

def _startup_intake_result_path_from_payload(router: ModuleType, payload: dict[str, Any]) -> str:
    _bind_router(router)
    result_ref = payload.get('startup_intake_result')
    if isinstance(result_ref, str):
        return result_ref
    if isinstance(result_ref, dict):
        result_path = result_ref.get('result_path') or result_ref.get('path')
        if isinstance(result_path, str) and result_path.strip():
            return result_path
    result_path = payload.get('result_path')
    if isinstance(result_path, str) and result_path.strip():
        return result_path
    raise RouterError('open_startup_intake_ui requires payload.startup_intake_result.result_path')

def _require_interactive_startup_intake_artifact(router: ModuleType, artifact: dict[str, Any], label: str) -> None:
    _bind_router(router)
    launch_mode = artifact.get('launch_mode')
    headless = artifact.get('headless')
    formal_allowed = artifact.get('formal_startup_allowed')
    if launch_mode != STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE or headless is not False or formal_allowed is not True:
        raise RouterError(f'formal FlowPilot startup requires the native interactive startup intake UI; {label} must declare launch_mode={STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE}, headless=false, and formal_startup_allowed=true')

def _validate_startup_intake_result_payload(router: ModuleType, project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    result_path = router._resolve_existing_project_file(project_root, router._startup_intake_result_path_from_payload(payload), 'result')
    result = read_json(result_path)
    if result.get('schema_version') != STARTUP_INTAKE_RESULT_SCHEMA:
        raise RouterError(f'startup intake result requires schema_version={STARTUP_INTAKE_RESULT_SCHEMA}')
    leaked = router._forbidden_startup_intake_body_fields(result)
    if leaked:
        raise RouterError(f"startup intake result contains forbidden body text fields: {', '.join(leaked)}")
    status = result.get('status')
    if status not in {'confirmed', 'cancelled'}:
        raise RouterError('startup intake result status must be confirmed or cancelled')
    router._require_interactive_startup_intake_artifact(result, 'startup intake result')
    result_rel = project_relative(project_root, result_path)
    receipt_path: Path | None = None
    receipt: dict[str, Any] | None = None
    if result.get('receipt_path'):
        receipt_path = router._resolve_existing_project_file(project_root, result.get('receipt_path'), 'receipt')
        receipt = read_json(receipt_path)
        if receipt.get('schema_version') != STARTUP_INTAKE_RECEIPT_SCHEMA:
            raise RouterError(f'startup intake receipt requires schema_version={STARTUP_INTAKE_RECEIPT_SCHEMA}')
        leaked_receipt = router._forbidden_startup_intake_body_fields(receipt)
        if leaked_receipt:
            raise RouterError(f"startup intake receipt contains forbidden body text fields: {', '.join(leaked_receipt)}")
        router._require_interactive_startup_intake_artifact(receipt, 'startup intake receipt')
    if receipt_path is None or receipt is None:
        raise RouterError('startup intake result requires receipt_path from the native interactive startup intake UI')
    if status == 'cancelled':
        return {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'status': 'cancelled', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'result_path': result_rel, 'receipt_path': project_relative(project_root, receipt_path), 'controller_visibility': result.get('controller_visibility') or 'cancel_status_only', 'body_text_included': False, 'recorded_at': result.get('recorded_at') or utc_now()}
    if result.get('body_text_included') is not False or result.get('controller_may_read_body') is not False:
        raise RouterError('startup intake confirmed result must be envelope-only for Controller')
    envelope_path = router._resolve_existing_project_file(project_root, result.get('envelope_path'), 'envelope')
    body_path = router._resolve_existing_project_file(project_root, result.get('body_path'), 'body')
    envelope = read_json(envelope_path)
    if envelope.get('schema_version') != STARTUP_INTAKE_ENVELOPE_SCHEMA:
        raise RouterError(f'startup intake envelope requires schema_version={STARTUP_INTAKE_ENVELOPE_SCHEMA}')
    router._require_interactive_startup_intake_artifact(envelope, 'startup intake envelope')
    leaked_envelope = router._forbidden_startup_intake_body_fields(envelope)
    if leaked_envelope:
        raise RouterError(f"startup intake envelope contains forbidden body text fields: {', '.join(leaked_envelope)}")
    if envelope.get('body_text_included') is not False or envelope.get('controller_may_read_body') is not False:
        raise RouterError('startup intake envelope must not expose body text to Controller')
    body_hash = result.get('body_hash')
    if not isinstance(body_hash, str) or not body_hash.strip():
        raise RouterError('startup intake confirmed result requires body_hash')
    actual_hash = packet_runtime.sha256_file(body_path)
    if actual_hash != body_hash.lower():
        raise RouterError('startup intake body hash mismatch')
    if not router._same_project_file(project_root, envelope.get('body_path'), body_path):
        raise RouterError('startup intake envelope body_path does not match result')
    if envelope.get('body_hash') != actual_hash:
        raise RouterError('startup intake envelope body_hash does not match body')
    if not router._same_project_file(project_root, envelope.get('receipt_path'), receipt_path):
        raise RouterError('startup intake envelope receipt_path does not match result')
    if receipt.get('body_hash') != actual_hash:
        raise RouterError('startup intake receipt body_hash does not match body')
    if not router._same_project_file(project_root, receipt.get('body_path'), body_path):
        raise RouterError('startup intake receipt body_path does not match result')
    startup_answers = router._validate_startup_answers({'startup_answers': result.get('startup_answers')})
    if envelope.get('startup_answers') != startup_answers or receipt.get('startup_answers') != startup_answers:
        raise RouterError('startup intake startup_answers mismatch across result, receipt, and envelope')
    return {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'status': 'confirmed', 'source': envelope.get('source') or 'native_wpf_startup_intake', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'language': result.get('language') or envelope.get('language') or receipt.get('language'), 'result_path': result_rel, 'receipt_path': project_relative(project_root, receipt_path), 'envelope_path': project_relative(project_root, envelope_path), 'body_path': project_relative(project_root, body_path), 'body_hash': actual_hash, 'startup_answers': startup_answers, 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'recorded_at': result.get('recorded_at') or utc_now()}

def _apply_startup_intake_result_to_bootstrap(router: ModuleType, project_root: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    startup_intake = router._validate_startup_intake_result_payload(project_root, payload)
    state.setdefault('flags', {})
    state['startup_intake'] = startup_intake
    result_extra: dict[str, Any] = {'startup_intake': startup_intake}
    if startup_intake['status'] == 'cancelled':
        state['status'] = 'startup_cancelled'
        state['startup_state'] = 'startup_cancelled'
        state['pending_action'] = None
        return result_extra
    state['startup_answers'] = startup_intake['startup_answers']
    state['startup_answer_interpretation'] = None
    state['startup_state'] = 'answers_complete'
    state['flags']['startup_state_written_awaiting_answers'] = True
    state['flags']['dialog_stopped_for_answers'] = True
    state['flags']['startup_answers_recorded'] = True
    seed_proof = router._run_deterministic_startup_bootstrap_seed(project_root, state)
    result_extra['deterministic_bootstrap_seed'] = {'evidence_path': state.get('deterministic_bootstrap_seed_evidence_path'), 'artifact_keys': sorted((seed_proof.get('artifacts') or {}).keys())}
    return result_extra

def _validate_startup_answer_interpretation(router: ModuleType, payload: dict[str, Any], answers: dict[str, str]) -> dict[str, Any] | None:
    _bind_router(router)
    provenance = answers.get('provenance')
    if provenance == STARTUP_ANSWER_PROVENANCE:
        if payload.get('startup_answer_interpretation') is not None:
            raise RouterError('startup_answer_interpretation is only allowed with ai_interpreted_from_explicit_user_reply provenance')
        return None
    receipt = payload.get('startup_answer_interpretation')
    if not isinstance(receipt, dict):
        raise RouterError('AI-interpreted startup answers require payload.startup_answer_interpretation receipt')
    if receipt.get('schema_version') != STARTUP_ANSWER_INTERPRETATION_SCHEMA:
        raise RouterError(f'startup_answer_interpretation requires schema_version={STARTUP_ANSWER_INTERPRETATION_SCHEMA}')
    raw_text = receipt.get('raw_user_reply_text')
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RouterError("startup_answer_interpretation.raw_user_reply_text must preserve the user's non-empty reply")
    interpreted_by = receipt.get('interpreted_by')
    if interpreted_by not in {'controller', 'bootloader'}:
        raise RouterError('startup_answer_interpretation.interpreted_by must be controller or bootloader')
    if receipt.get('interpretation_provenance') != STARTUP_ANSWER_INTERPRETATION_PROVENANCE:
        raise RouterError('startup_answer_interpretation.interpretation_provenance must match the AI-interpreted startup answer provenance')
    if receipt.get('ambiguity_status') != 'none':
        raise RouterError('ambiguous startup answers must be returned to the user instead of applied')
    interpreted_answers = receipt.get('interpreted_answers')
    if not isinstance(interpreted_answers, dict):
        raise RouterError('startup_answer_interpretation.interpreted_answers must be an object')
    expected = {key: answers[key] for key in STARTUP_ANSWER_ENUMS}
    got = {key: interpreted_answers.get(key) for key in STARTUP_ANSWER_ENUMS}
    if got != expected:
        raise RouterError('startup_answer_interpretation.interpreted_answers must match payload.startup_answers')
    allowed_keys = {'schema_version', 'raw_user_reply_text', 'interpreted_by', 'interpretation_provenance', 'ambiguity_status', 'interpreted_answers', 'reviewer_must_check_raw_reply_alignment', 'notes'}
    extra = sorted(set(receipt) - allowed_keys)
    if extra:
        raise RouterError(f"startup_answer_interpretation contains unsupported fields: {', '.join(extra)}")
    interpretation = {'schema_version': STARTUP_ANSWER_INTERPRETATION_SCHEMA, 'raw_user_reply_text': raw_text.strip(), 'interpreted_by': interpreted_by, 'interpretation_provenance': STARTUP_ANSWER_INTERPRETATION_PROVENANCE, 'ambiguity_status': 'none', 'interpreted_answers': expected, 'notes': receipt.get('notes'), 'recorded_at': utc_now()}
    if 'reviewer_must_check_raw_reply_alignment' in receipt:
        interpretation['reviewer_must_check_raw_reply_alignment'] = bool(receipt.get('reviewer_must_check_raw_reply_alignment'))
    return interpretation

def _validate_startup_answers(router: ModuleType, payload: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    answers = payload.get('startup_answers')
    if not isinstance(answers, dict):
        raise RouterError('record_startup_answers requires payload.startup_answers object')
    provenance = answers.get('provenance')
    if provenance not in {STARTUP_ANSWER_PROVENANCE, STARTUP_ANSWER_INTERPRETATION_PROVENANCE}:
        raise RouterError('startup answers require provenance=explicit_user_reply or ai_interpreted_from_explicit_user_reply')
    allowed_keys = set(STARTUP_ANSWER_ENUMS) | {'provenance'}
    extra = sorted(set(answers) - allowed_keys)
    if extra:
        raise RouterError(f"startup answers contain unsupported fields: {', '.join(extra)}")
    validated: dict[str, str] = {}
    for answer_id, allowed_values in STARTUP_ANSWER_ENUMS.items():
        value = answers.get(answer_id)
        if not isinstance(value, str) or value not in allowed_values:
            allowed = ', '.join(sorted(allowed_values))
            raise RouterError(f'startup answer {answer_id} must be one of: {allowed}')
        validated[answer_id] = value
    validated['provenance'] = provenance
    router._validate_startup_answer_interpretation(payload, validated)
    return validated

def _validate_user_request(router: ModuleType, payload: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    request = payload.get('user_request')
    if not isinstance(request, dict):
        raise RouterError('record_user_request requires payload.user_request object')
    provenance = request.get('provenance')
    if provenance != USER_REQUEST_PROVENANCE:
        raise RouterError('user request requires provenance=explicit_user_request')
    text = request.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RouterError('user_request.text must contain the exact non-empty user task')
    allowed_keys = {'text', 'provenance', 'source'}
    extra = sorted(set(request) - allowed_keys)
    if extra:
        raise RouterError(f"user request contains unsupported fields: {', '.join(extra)}")
    source = request.get('source') or 'flowpilot_activation_or_user_reply'
    if not isinstance(source, str) or not source.strip():
        raise RouterError('user_request.source must be a non-empty string when supplied')
    return {'text': text.strip(), 'provenance': USER_REQUEST_PROVENANCE, 'source': source.strip()}

def _copy_startup_intake_file(router: ModuleType, project_root: Path, run_root: Path, raw_path: str, target_name: str) -> Path:
    _bind_router(router)
    source = router._resolve_existing_project_file(project_root, raw_path, target_name)
    target_dir = run_root / 'startup_intake'
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / target_name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target

def _materialize_startup_intake_record(router: ModuleType, project_root: Path, state: dict[str, Any], run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    intake = router._confirmed_startup_intake(state)
    if intake is None:
        raise RouterError('cannot materialize startup intake record before confirmed UI intake')
    result_path = router._copy_startup_intake_file(project_root, run_root, str(intake['result_path']), 'startup_intake_result.json')
    receipt_path = router._copy_startup_intake_file(project_root, run_root, str(intake['receipt_path']), 'startup_intake_receipt.json')
    envelope_path = router._copy_startup_intake_file(project_root, run_root, str(intake['envelope_path']), 'startup_intake_envelope.json')
    body_path = router._copy_startup_intake_file(project_root, run_root, str(intake['body_path']), 'startup_intake_body.md')
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != intake.get('body_hash'):
        raise RouterError('startup intake copied body hash mismatch')
    record = {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'run_id': state.get('run_id'), 'status': 'confirmed', 'source': intake.get('source') or 'native_wpf_startup_intake', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'language': intake.get('language'), 'result_path': project_relative(project_root, result_path), 'receipt_path': project_relative(project_root, receipt_path), 'envelope_path': project_relative(project_root, envelope_path), 'body_path': project_relative(project_root, body_path), 'body_hash': body_hash, 'startup_answers': intake.get('startup_answers') or {}, 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'materialized_at': utc_now()}
    record_path = run_root / 'startup_intake' / 'startup_intake_record.json'
    write_json(record_path, record)
    record['record_path'] = project_relative(project_root, record_path)
    return record

def _user_request_ref_from_startup_intake(router: ModuleType, project_root: Path, state: dict[str, Any], intake_record: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': USER_REQUEST_REF_SCHEMA, 'run_id': state.get('run_id'), 'provenance': 'startup_intake_ui', 'source': intake_record.get('source') or 'native_wpf_startup_intake', 'startup_intake_record_path': intake_record['record_path'], 'startup_intake_result_path': intake_record['result_path'], 'startup_intake_receipt_path': intake_record['receipt_path'], 'startup_intake_envelope_path': intake_record['envelope_path'], 'body_path': intake_record['body_path'], 'body_hash': intake_record['body_hash'], 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'pm_may_open_body_via_packet_runtime': True, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'recorded_at': utc_now()}

def _build_user_intake_body_from_ref(router: ModuleType, project_root: Path, user_request_ref: dict[str, Any], startup_answers: dict[str, Any]) -> str:
    _bind_router(router)
    body_path = router._resolve_existing_project_file(project_root, user_request_ref.get('body_path'), 'startup intake body')
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != user_request_ref.get('body_hash'):
        raise RouterError('startup intake body hash mismatch before user_intake packet')
    metadata = {'schema_version': 'flowpilot.pm_startup_intake_context.v1', 'source': 'native_startup_intake_ui', 'startup_intake_record_path': user_request_ref.get('startup_intake_record_path'), 'startup_intake_receipt_path': user_request_ref.get('startup_intake_receipt_path'), 'startup_intake_envelope_path': user_request_ref.get('startup_intake_envelope_path'), 'body_path': user_request_ref.get('body_path'), 'body_hash': user_request_ref.get('body_hash'), 'startup_answers': startup_answers, 'controller_may_read_body': False, 'reviewer_live_review_source': 'startup_intake_record'}
    return f"# FlowPilot Startup Intake\n\nThe user's work request came from the native startup intake UI. Router holds this sealed startup packet and releases it to Project Manager after PM system-card ACK. Controller must not read this packet body.\n\n```json\n{json.dumps(metadata, indent=2, sort_keys=True)}\n```\n\n## User Work Request\n\n{body_path.read_text(encoding='utf-8-sig').strip()}\n"

def _deterministic_bootstrap_seed_evidence_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'bootstrap' / 'deterministic_bootstrap_seed_evidence.json'

def _write_startup_answers_record(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    interpretation = state.get('startup_answer_interpretation') if isinstance(state.get('startup_answer_interpretation'), dict) else None
    interpretation_path = run_root / 'startup_answer_interpretation.json'
    if interpretation:
        write_json(interpretation_path, interpretation)
    record = {'schema_version': 'flowpilot.startup_answers.v1', 'run_id': state['run_id'], 'answers': state.get('startup_answers') or {}, 'startup_answer_interpretation_path': project_relative(project_root, interpretation_path) if interpretation else None, 'recorded_at': utc_now()}
    write_json(run_root / 'startup_answers.json', record)
    return record

def _initialize_mailbox_foundation(router: ModuleType, project_root: Path, run_root: Path, run_id: str) -> dict[str, Any]:
    _bind_router(router)
    dirs = ('mailbox/system_cards', 'mailbox/inbox', 'mailbox/outbox', 'mailbox/outbox/card_acks', 'runtime_receipts/card_reads', 'runtime_receipts/role_io_protocol', 'packets')
    for rel in dirs:
        (run_root / rel).mkdir(parents=True, exist_ok=True)
    packet_ledger_path = run_root / 'packet_ledger.json'
    prompt_delivery_ledger_path = run_root / 'prompt_delivery_ledger.json'
    card_ledger_path = _card_ledger_path(run_root)
    return_event_ledger_path = _return_event_ledger_path(run_root)
    role_io_protocol_ledger_path = _role_io_protocol_ledger_path(run_root)
    write_json(packet_ledger_path, router._create_empty_packet_ledger(project_root, run_id, run_root))
    write_json(prompt_delivery_ledger_path, {'schema_version': 'flowpilot.prompt_delivery_ledger.v1', 'run_id': run_id, 'deliveries': []})
    write_json(card_ledger_path, _empty_card_ledger(run_id))
    write_json(return_event_ledger_path, _empty_return_event_ledger(run_id))
    write_json(role_io_protocol_ledger_path, _empty_role_io_protocol_ledger(run_id))
    return {'directories': [project_relative(project_root, run_root / rel) for rel in dirs], 'ledgers': [project_relative(project_root, packet_ledger_path), project_relative(project_root, prompt_delivery_ledger_path), project_relative(project_root, card_ledger_path), project_relative(project_root, return_event_ledger_path), project_relative(project_root, role_io_protocol_ledger_path)]}

def _record_startup_user_request_ref(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if router._confirmed_startup_intake(state) is not None:
        intake_record = router._materialize_startup_intake_record(project_root, state, run_root)
        user_request = router._user_request_ref_from_startup_intake(project_root, state, intake_record)
        user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'source': 'startup_intake_ui', 'user_request_ref': user_request, 'startup_intake_record': intake_record, 'controller_may_read_body': False, 'body_text_included': False, 'recorded_at': utc_now()}
        state['startup_intake'] = intake_record
        state['startup_intake_record_path'] = intake_record['record_path']
        state['user_request_ref'] = user_request
    else:
        user_request = state.get('user_request')
        if not isinstance(user_request, dict):
            raise RouterError('deterministic startup seed requires confirmed startup intake or user_request')
        user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'user_request': user_request, 'recorded_at': utc_now()}
    user_request_path = run_root / 'user_request.json'
    write_json(user_request_path, user_request_record)
    state['user_request'] = user_request
    state['user_request_path'] = project_relative(project_root, user_request_path)
    return user_request_record

def _write_startup_user_intake_scaffold(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    user_request = state.get('user_request')
    if not isinstance(user_request, dict):
        raise RouterError('cannot write deterministic user_intake scaffold before user request reference')
    if user_request.get('schema_version') == USER_REQUEST_REF_SCHEMA:
        body_text = router._build_user_intake_body_from_ref(project_root, user_request, state.get('startup_answers') or {})
        user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=body_text, startup_options=state.get('startup_answers') or {}, source='startup_intake_ui', body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, startup_intake_ref=user_request, router_owned_startup_material=True)
    else:
        user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=json.dumps({'user_request': user_request, 'user_request_path': state.get('user_request_path'), 'startup_answers': state.get('startup_answers') or {}, 'startup_answers_path': project_relative(project_root, run_root / 'startup_answers.json'), 'startup_answer_interpretation_path': project_relative(project_root, run_root / 'startup_answer_interpretation.json') if isinstance(state.get('startup_answer_interpretation'), dict) else None}, indent=2, sort_keys=True), startup_options=state.get('startup_answers') or {}, body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, router_owned_startup_material=True)
    user_intake_path = run_root / 'mailbox' / 'outbox' / 'user_intake.json'
    write_json(user_intake_path, user_intake)
    return {'path': project_relative(project_root, user_intake_path), 'body_visibility': user_intake.get('body_visibility'), 'startup_owner': 'router', 'release_condition': 'pm_system_card_bundle_ack_resolved', 'controller_may_read_body': False}

def _run_deterministic_startup_bootstrap_seed(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if not state.get('run_id') or not state.get('run_root'):
        raise RouterError('deterministic startup seed requires run shell')
    if not state.get('startup_answers'):
        raise RouterError('deterministic startup seed requires startup answers')
    run_root = project_root / str(state['run_root'])
    flags = state.setdefault('flags', {})
    evidence_path = router._deterministic_bootstrap_seed_evidence_path(run_root)
    if flags.get('deterministic_bootstrap_seed_completed') and evidence_path.exists():
        existing_proof = read_json(evidence_path)
        if existing_proof.get('schema_version') == DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA and existing_proof.get('completed') is True:
            state['deterministic_bootstrap_seed_evidence_path'] = project_relative(project_root, evidence_path)
            return existing_proof
        raise RouterError('completed deterministic startup seed has invalid evidence')
    artifacts: dict[str, Any] = {}
    if not flags.get('runtime_kit_copied'):
        _copy_runtime_kit_into_run_root(run_root)
        flags['runtime_kit_copied'] = True
    artifacts['runtime_kit'] = project_relative(project_root, run_root / 'runtime_kit')
    artifacts['startup_answers'] = project_relative(project_root, run_root / 'startup_answers.json')
    router._write_startup_answers_record(project_root, run_root, state)
    flags['placeholders_filled'] = True
    mailbox = router._initialize_mailbox_foundation(project_root, run_root, str(state['run_id']))
    artifacts['mailbox'] = mailbox
    flags['mailbox_initialized'] = True
    user_request_record = router._record_startup_user_request_ref(project_root, run_root, state)
    artifacts['user_request'] = project_relative(project_root, run_root / 'user_request.json')
    flags['user_request_recorded'] = True
    user_intake = router._write_startup_user_intake_scaffold(project_root, run_root, state)
    artifacts['user_intake'] = user_intake
    flags['user_intake_ready'] = True
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    required_flags = ('runtime_kit_copied', 'placeholders_filled', 'mailbox_initialized', 'user_request_recorded', 'user_intake_ready')
    proof = {'schema_version': DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA, 'run_id': state['run_id'], 'source': 'deterministic_bootstrap_seed', 'controller_action_row_created': False, 'pm_blocker_allowed': False, 'required_flags': {flag: bool(flags.get(flag)) for flag in required_flags}, 'artifacts': artifacts, 'user_request_record_controller_may_read_body': bool(user_request_record.get('controller_may_read_body', True)), 'completed': all((bool(flags.get(flag)) for flag in required_flags)), 'completed_at': utc_now()}
    if not proof['completed']:
        missing = [flag for flag, value in proof['required_flags'].items() if not value]
        raise RouterError(f"deterministic startup seed missing required flags: {', '.join(missing)}")
    write_json(evidence_path, proof)
    state['deterministic_bootstrap_seed_evidence_path'] = project_relative(project_root, evidence_path)
    flags['deterministic_bootstrap_seed_completed'] = True
    append_history(state, 'deterministic_startup_bootstrap_seed_completed', {'evidence_path': state['deterministic_bootstrap_seed_evidence_path'], 'artifacts': sorted(artifacts)})
    return proof

def _display_text_hash(router: ModuleType, display_text: str) -> str:
    _bind_router(router)
    return hashlib.sha256(display_text.encode('utf-8')).hexdigest()

def _user_dialog_display_gate(router: ModuleType, fields: dict[str, Any], *, display_kind: str, display_text: str) -> dict[str, Any]:
    _bind_router(router)
    gated = dict(fields)
    gated.update({'display_kind': display_kind, 'display_text_sha256': router._display_text_hash(display_text), 'requires_payload': 'display_confirmation', 'requires_user_dialog_display_confirmation': True, 'required_render_target': DISPLAY_CONFIRMATION_TARGET, 'display_confirmation_schema': DISPLAY_CONFIRMATION_SCHEMA})
    return gated

def _validate_display_confirmation(router: ModuleType, payload: dict[str, Any], *, action_type: str, display_kind: str, display_text: str) -> dict[str, Any]:
    _bind_router(router)
    confirmation = payload.get('display_confirmation')
    if not isinstance(confirmation, dict):
        raise RouterError(f'{action_type} requires payload.display_confirmation before apply; render display_text in the user dialog first')
    if confirmation.get('provenance') != DISPLAY_CONFIRMATION_PROVENANCE:
        raise RouterError(f'{action_type} display_confirmation requires provenance={DISPLAY_CONFIRMATION_PROVENANCE}')
    if confirmation.get('rendered_to') != DISPLAY_CONFIRMATION_TARGET:
        raise RouterError(f'{action_type} display_confirmation requires rendered_to={DISPLAY_CONFIRMATION_TARGET}')
    if confirmation.get('action_type') != action_type:
        raise RouterError(f'{action_type} display_confirmation action_type mismatch')
    if confirmation.get('display_kind') != display_kind:
        raise RouterError(f'{action_type} display_confirmation display_kind mismatch')
    expected_hash = router._display_text_hash(display_text)
    if confirmation.get('display_text_sha256') != expected_hash:
        raise RouterError(f'{action_type} display_confirmation display_text_sha256 mismatch')
    return {'schema_version': DISPLAY_CONFIRMATION_SCHEMA, 'action_type': action_type, 'display_kind': display_kind, 'rendered_to': DISPLAY_CONFIRMATION_TARGET, 'display_text_sha256': expected_hash, 'provenance': DISPLAY_CONFIRMATION_PROVENANCE, 'confirmed_at': utc_now()}

def _display_confirmation_for_action(router: ModuleType, payload: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    payload = payload or {}
    display_text = action.get('display_text')
    if not isinstance(display_text, str) or not display_text:
        raise RouterError('display confirmation requested for action without display_text')
    display_kind = action.get('display_kind')
    if not isinstance(display_kind, str) or not display_kind:
        raise RouterError('display confirmation requested for action without display_kind')
    return router._validate_display_confirmation(payload, action_type=str(action.get('action_type') or ''), display_kind=display_kind, display_text=display_text)

def _append_user_dialog_display_ledger(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any]) -> None:
    _bind_router(router)
    del project_root
    ledger_path = run_root / 'display' / 'user_dialog_display_ledger.json'
    ledger = read_json_if_exists(ledger_path) or {'schema_version': 'flowpilot.user_dialog_display_ledger.v1', 'run_id': run_root.name, 'records': []}
    ledger.setdefault('records', []).append(record)
    ledger['updated_at'] = utc_now()
    write_json(ledger_path, ledger)

def _display_plan_display_kind(router: ModuleType, plan_projection: dict[str, Any]) -> str:
    _bind_router(router)
    items = plan_projection.get('items') if isinstance(plan_projection.get('items'), list) else []
    if len(items) == 1 and isinstance(items[0], dict) and (items[0].get('id') == 'await_pm_route') and (plan_projection.get('current_node_id') is None):
        return 'startup_waiting_state'
    return 'route_map'

def _display_plan_chat_markdown(router: ModuleType, plan_projection: dict[str, Any], *, display_kind: str) -> str:
    _bind_router(router)
    title = '# FlowPilot Startup Status' if display_kind == 'startup_waiting_state' else '# FlowPilot Route Map'
    lines = [title, '']
    for item in plan_projection.get('items') or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get('label') or item.get('id') or 'Route item')
        status = str(item.get('status') or 'pending')
        lines.append(f'- {label} - {status}')
    if len(lines) == 2:
        lines.append('- Waiting for PM route - in_progress')
    active_path = plan_projection.get('active_path') if isinstance(plan_projection.get('active_path'), list) else []
    if active_path:
        path_labels = [str(item.get('label') or item.get('id')) for item in active_path if isinstance(item, dict) and (item.get('label') or item.get('id'))]
        if path_labels:
            lines.extend(['', f"Current path: {' > '.join(path_labels)}"])
    progress = plan_projection.get('hidden_leaf_progress')
    if isinstance(progress, dict) and progress.get('total'):
        lines.append(f"Hidden leaf progress: {progress.get('completed', 0)}/{progress.get('total')} complete")
    return '\n'.join(lines).rstrip() + '\n'

def _display_plan_user_dialog_fields(router: ModuleType, plan_projection: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    display_kind = router._display_plan_display_kind(plan_projection)
    display_text = router._display_plan_chat_markdown(plan_projection, display_kind=display_kind)
    display_label = 'startup waiting state' if display_kind == 'startup_waiting_state' else 'route map'
    return router._user_dialog_display_gate({'display_text': display_text, 'display_text_format': 'markdown', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': f'Paste this exact {display_label} display_text in the user dialog before writing the Controller receipt for sync_display_plan; display_plan.json or host-plan replacement alone does not satisfy display.'}, display_kind=display_kind, display_text=display_text)

def _startup_waiting_internal_display_fields(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return {'display_kind': 'startup_waiting_state', 'display_required': False, 'display_text_format': 'internal_state', 'controller_must_display_text_before_apply': False, 'requires_user_dialog_display_confirmation': False, 'generated_files_alone_satisfy_chat_display': False, 'user_visible_display_suppressed': True, 'internal_display_reason': 'waiting_for_pm_route_before_canonical_route', 'controller_display_rule': 'Do not paste a FlowPilot Startup Status waiting card into the user dialog. This sync is internal host-plan state only; startup user visibility is handled by the startup FlowPilot Route Sign display.'}

def _display_route_sign_user_dialog_fields(router: ModuleType, route_sign: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    display_text = route_sign.get('markdown')
    if not isinstance(display_text, str) or not display_text.strip():
        raise RouterError('route-sign display requires non-empty markdown')
    return router._user_dialog_display_gate({'display_text': display_text, 'display_text_format': 'markdown_mermaid', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact FlowPilot Route Sign Mermaid in the user dialog before writing the Controller receipt for sync_display_plan; display_plan.json or generated files alone do not satisfy display.'}, display_kind='route_map', display_text=display_text)

def _startup_banner_display(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    banner_path = runtime_kit_source() / 'cards' / 'system' / 'startup_banner.md'
    if not banner_path.exists():
        raise RouterError('startup banner card is missing')
    text = banner_path.read_text(encoding='utf-8')
    stripped = text.lstrip()
    if stripped.startswith('<!-- FLOWPILOT_IDENTITY_BOUNDARY_V1'):
        end = stripped.find('-->')
        if end >= 0:
            stripped = stripped[end + 3:].lstrip()
    display_text = stripped.rstrip() + '\n'
    return router._user_dialog_display_gate({'display_path': str(banner_path), 'display_text': display_text, 'display_text_format': 'plain_text', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact startup banner display_text in the user dialog before writing the Controller receipt for emit_startup_banner; the Controller receipt requires display_confirmation.rendered_to=user_dialog with matching display_text_sha256.'}, display_kind='startup_banner', display_text=display_text)

def _role_spawn_action_extra(router: ModuleType, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    answers = state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {}
    mode = answers.get('background_agents')
    extra: dict[str, Any] = {'background_agents_mode': mode, 'role_keys': list(CREW_ROLE_KEYS), 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'applies_to': ['startup_live_role_spawn', 'heartbeat_resume_rehydration', 'manual_resume_rehydration', 'missing_role_replacement']}}
    if mode == 'allow':
        extra.update({'requires_payload': 'role_agents', 'requires_host_spawn': True, 'spawn_policy': 'spawn_all_six_fresh_current_task_agents_before_controller_receipt', 'payload_contract': _role_slots_payload_contract(), 'role_spawn_request': [{'role_key': role, 'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'spawn_result': ROLE_AGENT_SPAWN_RESULT, 'spawned_for_run_id': state.get('run_id'), 'spawned_after_startup_answers': True} for role in CREW_ROLE_KEYS]})
    elif mode == 'single-agent':
        extra.update({'requires_host_spawn': False, 'single_agent_continuity_authorized': True})
    return extra

def _normalize_role_agent_records(router: ModuleType, state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {}
    mode = answers.get('background_agents')
    run_id = str(state.get('run_id') or '')
    if mode == 'single-agent':
        return [{'role_key': role, 'status': 'single_agent_continuity_authorized', 'agent_id': None, 'spawn_result': 'not_requested_single_agent_continuity', 'fallback_authorized_by_startup_answer': True, 'recorded_at': utc_now()} for role in CREW_ROLE_KEYS]
    if mode != 'allow':
        raise RouterError('cannot start roles before background_agents startup answer is recorded')
    raw_records = payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('start_role_slots requires payload.role_agents list or object')
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('live background roles require background_agents_capability_status=available')
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each role agent record must be an object')
        role = raw.get('role_key')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'role agent record has unsupported role_key: {role!r}')
        if role in records_by_role:
            raise RouterError(f'duplicate role agent record for {role}')
        agent_id = raw.get('agent_id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f'{role} requires a non-empty current agent_id')
        if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
            raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
        if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
            raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
        if raw.get('spawn_result') != ROLE_AGENT_SPAWN_RESULT:
            raise RouterError(f'{role} requires spawn_result=spawned_fresh_for_task')
        if raw.get('spawned_after_startup_answers') is not True:
            raise RouterError(f'{role} must be spawned_after_startup_answers=true')
        if raw.get('spawned_for_run_id') != run_id:
            raise RouterError(f'{role} must be spawned_for_run_id={run_id}')
        host_spawn_receipt = raw.get('host_spawn_receipt')
        if host_spawn_receipt is not None:
            if not isinstance(host_spawn_receipt, dict):
                raise RouterError(f'{role} host_spawn_receipt must be an object')
            if host_spawn_receipt.get('source_kind') != 'host_receipt':
                raise RouterError(f'{role} host_spawn_receipt requires source_kind=host_receipt')
            if host_spawn_receipt.get('spawned_for_run_id') != run_id:
                raise RouterError(f'{role} host_spawn_receipt spawned_for_run_id mismatch')
            if host_spawn_receipt.get('role_key') != role:
                raise RouterError(f'{role} host_spawn_receipt role_key mismatch')
            if host_spawn_receipt.get('agent_id') != agent_id:
                raise RouterError(f'{role} host_spawn_receipt agent_id mismatch')
        records_by_role[str(role)] = {'role_key': str(role), 'status': 'live_agent_started', 'agent_id': agent_id.strip(), 'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'spawn_result': ROLE_AGENT_SPAWN_RESULT, 'spawned_for_run_id': run_id, 'spawned_after_startup_answers': True, 'crew_generation': 1, 'role_binding_epoch': 1, **({'host_spawn_receipt': host_spawn_receipt} if isinstance(host_spawn_receipt, dict) else {}), 'recorded_at': utc_now()}
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]

def _latest_resume_tick_id(router: ModuleType, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    ticks = run_state.get('heartbeat_ticks') if isinstance(run_state.get('heartbeat_ticks'), list) else []
    for tick in reversed(ticks):
        if isinstance(tick, dict) and tick.get('tick_id'):
            return str(tick['tick_id'])
    return 'manual-resume'

def _role_core_prompt_path(router: ModuleType, run_root: Path, role: str) -> Path:
    _bind_router(router)
    return run_root / 'runtime_kit' / 'cards' / 'roles' / f'{role}.md'

def _role_memory_path(router: ModuleType, run_root: Path, role: str) -> Path:
    _bind_router(router)
    return run_root / 'crew_memory' / f'{role}.json'

def _path_hash(router: ModuleType, path: Path) -> str | None:
    _bind_router(router)
    if not path.exists() or not path.is_file():
        return None
    return packet_runtime.sha256_file(path)

def _role_core_prompt_delivery_payload(router: ModuleType, project_root: Path, run_root: Path, run_id: str, *, source_action: str) -> dict[str, Any]:
    _bind_router(router)
    role_cards: dict[str, str] = {}
    role_card_hashes: dict[str, str] = {}
    for role in ROLE_CARD_KEYS:
        card_path = router._role_core_prompt_path(run_root, role)
        if not card_path.exists():
            raise RouterError(f'role core prompt card is missing for {role}')
        role_cards[role] = card_path.relative_to(run_root).as_posix()
        role_card_hashes[role] = packet_runtime.sha256_file(card_path)
    return {'schema_version': 'flowpilot.role_core_prompt_delivery.v1', 'run_id': run_id, 'source': 'copied_runtime_kit', 'source_action': source_action, 'delivery_mode': 'same_action_with_role_start' if source_action == 'start_role_slots' else 'legacy_recovery_action', 'role_cards': role_cards, 'role_card_hashes': role_card_hashes, 'delivered_at': utc_now()}

def _resume_role_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], role: str) -> dict[str, Any]:
    _bind_router(router)
    memory_path = router._role_memory_path(run_root, role)
    core_path = router._role_core_prompt_path(run_root, role)
    common_context = {'resume_reentry': project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'role_io_protocol_ledger': project_relative(project_root, _role_io_protocol_ledger_path(run_root)), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root)), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'display_plan': project_relative(project_root, router._display_plan_path(run_root))}
    context = {'role_key': role, 'required_rehydration_result': 'conditional_on_host_liveness', 'active_liveness_rehydration_result': ROLE_AGENT_CONTINUITY_RESULT, 'replacement_rehydration_result': ROLE_AGENT_REHYDRATION_RESULT, 'allowed_rehydration_results': sorted(RESUME_ROLE_AGENT_RESULTS), 'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': router._latest_resume_tick_id(run_state), 'rehydrated_after_resume_state_loaded': True, 'spawned_after_resume_state_loaded': False, 'spawned_after_resume_state_loaded_required_if_replaced': True, 'core_prompt_path': project_relative(project_root, core_path), 'core_prompt_hash': router._path_hash(core_path), 'memory_packet_path': project_relative(project_root, memory_path), 'memory_packet_hash': router._path_hash(memory_path), 'role_memory_status': 'available' if memory_path.exists() else 'missing', 'common_context_paths': common_context, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    if role == 'project_manager':
        context['pm_resume_context_required'] = True
        context['pm_resume_context_paths'] = {'resume_reentry': common_context['resume_reentry'], 'execution_frontier': common_context['execution_frontier'], 'packet_ledger': common_context['packet_ledger'], 'prompt_delivery_ledger': common_context['prompt_delivery_ledger'], 'crew_ledger': common_context['crew_ledger'], 'crew_memory': project_relative(project_root, run_root / 'crew_memory'), 'route_history_index': common_context['route_history_index'], 'pm_prior_path_context': common_context['pm_prior_path_context'], 'display_plan': common_context['display_plan']}
    return context

def _resume_role_contexts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    return [router._resume_role_context(project_root, run_root, run_state, role) for role in CREW_ROLE_KEYS]

def _resume_liveness_probe_batch_id(router: ModuleType, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    return f"resume-liveness-{run_state['run_id']}-{router._latest_resume_tick_id(run_state)}"

def _role_recovery_dir(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'role_recovery'

def _role_recovery_latest_transaction_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._role_recovery_dir(run_root) / 'latest_transaction.json'

def _role_recovery_state_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._role_recovery_dir(run_root) / 'state_load.json'

def _role_recovery_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'role_recovery_report.json'

def _role_recovery_target_roles(router: ModuleType, raw_roles: object, *, default_all: bool=False) -> list[str]:
    _bind_router(router)
    if default_all:
        return list(CREW_ROLE_KEYS)
    if isinstance(raw_roles, str):
        roles = [raw_roles]
    elif isinstance(raw_roles, list):
        roles = [str(role) for role in raw_roles]
    else:
        roles = []
    normalized: list[str] = []
    for role in roles:
        role_key = str(role).strip()
        if role_key not in CREW_ROLE_KEYS:
            raise RouterError(f'role recovery target has unsupported role_key: {role_key!r}')
        if role_key not in normalized:
            normalized.append(role_key)
    if not normalized:
        raise RouterError('role recovery requires at least one target_role_key')
    return normalized

def _latest_role_recovery_transaction(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    return read_json_if_exists(router._role_recovery_latest_transaction_path(run_root))

def _role_recovery_ready_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    report_path = router._role_recovery_report_path(run_root)
    report = read_json_if_exists(report_path)
    if report.get('schema_version') != ROLE_RECOVERY_REPORT_SCHEMA:
        return None
    if str(report.get('run_id') or '') != str(run_state.get('run_id') or ''):
        return None
    if report.get('all_six_roles_ready') is not True or report.get('environment_blocked') is True:
        return None
    crew_path = run_root / 'crew_ledger.json'
    crew = read_json_if_exists(crew_path)
    slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    ready_agents: dict[str, str] = {}
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        role = str(slot.get('role_key') or '')
        agent_id = slot.get('agent_id')
        if role in CREW_ROLE_KEYS and isinstance(agent_id, str) and agent_id.strip():
            ready_agents[role] = agent_id.strip()
    missing_roles = [role for role in CREW_ROLE_KEYS if role not in ready_agents]
    if missing_roles:
        return None
    return {'report': report, 'report_path': report_path, 'report_relpath': project_relative(project_root, report_path), 'crew_path': crew_path, 'crew_relpath': project_relative(project_root, crew_path), 'ready_role_keys': list(CREW_ROLE_KEYS), 'ready_agents': ready_agents}

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
    flags['resume_role_agents_rehydrated'] = True
    flags['crew_rehydration_report_written'] = (run_root / 'continuation' / 'crew_rehydration_report.json').exists()
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

def _current_crew_generation(router: ModuleType, crew: dict[str, Any]) -> int:
    _bind_router(router)
    raw = crew.get('crew_generation')
    if isinstance(raw, int) and raw > 0:
        return raw
    generations = [int(slot.get('crew_generation')) for slot in (crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []) if isinstance(slot, dict) and isinstance(slot.get('crew_generation'), int)]
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
    transaction = {'schema_version': ROLE_RECOVERY_TRANSACTION_SCHEMA, 'transaction_id': transaction_id, 'run_id': run_state['run_id'], 'trigger_source': trigger_source, 'recovery_scope': recovery_scope, 'target_role_keys': list(target_role_keys), 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'started_at': utc_now(), 'fault_payload': fault_payload, 'active_packet_context': active_packet, 'recovery_ladder': ['restore_old_agent', 'targeted_replacement', 'slot_reconciliation', 'full_crew_recycle', 'environment_blocked'], 'controller_may_wait_for_normal_work_before_recovery': False, 'controller_may_infer_completion_from_old_agent': False}
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
    required_fields = ['background_agents_capability_status', 'recovery_transaction_id', 'trigger_source', 'recovery_scope', 'target_role_keys', 'recovered_role_agents[].role_key', 'recovered_role_agents[].agent_id', 'recovered_role_agents[].model_policy', 'recovered_role_agents[].reasoning_effort_policy', 'recovered_role_agents[].recovery_result', 'recovered_role_agents[].restore_attempted', 'recovered_role_agents[].restore_result', 'recovered_role_agents[].rehydrated_for_run_id', 'recovered_role_agents[].memory_context_injected', 'recovered_role_agents[].packet_ownership_reconciled']
    if scope == 'targeted':
        required_fields.extend(['recovered_role_agents[].old_agent_id', 'recovered_role_agents[].role_binding_epoch_advanced', 'recovered_role_agents[].superseded_agent_output_quarantined'])
    return _payload_contract(name='role_liveness_recovery_receipt', required_object='payload', required_fields=required_fields, allowed_values={'background_agents_capability_status': ['available'], 'recovery_transaction_id': [str(transaction.get('transaction_id') or '')], 'trigger_source': [str(transaction.get('trigger_source') or '')], 'recovery_scope': [scope, 'full_crew'], 'target_role_keys': [target_roles], 'recovered_role_agents[].role_key': list(CREW_ROLE_KEYS), 'recovered_role_agents[].model_policy': [BACKGROUND_ROLE_MODEL_POLICY], 'recovered_role_agents[].reasoning_effort_policy': [BACKGROUND_ROLE_REASONING_EFFORT_POLICY], 'recovered_role_agents[].recovery_result': sorted(ROLE_RECOVERY_RESULTS), 'recovered_role_agents[].rehydrated_for_run_id': [run_state['run_id']], 'recovered_role_agents[].memory_context_injected': [True], 'recovered_role_agents[].packet_ownership_reconciled': [True]}, structural_requirements=['Recovery must be recorded before any normal route, packet, gate, or control-blocker work resumes.', 'For targeted recovery, attempt old-agent restore before replacement.', 'If old close fails and targeted spawn reports capacity_full, slot reconciliation and full crew recycle must be attempted before any success report.', 'A failed full crew recycle must return recovery_result=environment_blocked and must not mark the crew ready.', 'Recovered or replacement roles must receive current-run memory/context before being marked usable.', 'Late output from superseded agent ids must be quarantined and cannot count as packet or gate progress.', 'Packet ownership must be reconciled before PM is asked to continue.'], description='Record the host recovery attempt ladder for a missing or unhealthy FlowPilot role.', reviewer_check='PM checks this role recovery report before deciding whether to resume, re-dispatch, or escalate.')

def _load_role_recovery_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery state load requires an open role recovery transaction')
    loaded_paths = {'role_recovery_transaction': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), 'router_state': project_relative(project_root, router.run_state_path(run_root)), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'crew_memory': project_relative(project_root, run_root / 'crew_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}
    missing_paths = [rel for rel in loaded_paths.values() if not resolve_project_path(project_root, rel).exists()]
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    record = {'schema_version': 'flowpilot.role_recovery_state_load.v1', 'run_id': run_state['run_id'], 'transaction_id': transaction['transaction_id'], 'trigger_source': transaction['trigger_source'], 'recovery_scope': transaction['recovery_scope'], 'target_role_keys': transaction['target_role_keys'], 'loaded_at': utc_now(), 'loaded_paths': loaded_paths, 'missing_paths': missing_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'priority': 'preempt_normal_work', 'normal_work_suspended': True, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False}
    write_json(router._role_recovery_state_path(run_root), record)
    resume_reentry_path = run_root / 'continuation' / 'resume_reentry.json'
    if not resume_reentry_path.exists():
        write_json(resume_reentry_path, {'schema_version': 'flowpilot.resume_reentry.v1', 'run_id': run_state['run_id'], 'stable_launcher': True, 'controller_only': True, 'wake_recorded_to_router': True, 'role_recovery_triggered': True, 'role_recovery_transaction_id': transaction['transaction_id'], 'visible_plan_restore_required': True, 'visible_plan_restored_from_run': True, 'role_rehydration_required': True, 'roles_restored_or_replaced': False, 'ambiguous_state_blocks_controller_execution': bool(missing_paths), 'missing_paths': missing_paths, 'loaded_paths': loaded_paths, 'resume_next_recipient_from_packet_ledger': resume_next, 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'controller_may_infer_route_progress_from_chat_history': False, 'recorded_at': record['loaded_at']})
    run_state['flags']['role_recovery_state_loaded'] = True
    return record

def _normalize_role_recovery_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _bind_router(router)
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('role recovery requires background_agents_capability_status=available')
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery requires an open role recovery transaction')
    if payload.get('recovery_transaction_id') != transaction.get('transaction_id'):
        raise RouterError('role recovery transaction id mismatch')
    trigger_source = str(transaction.get('trigger_source') or '')
    if payload.get('trigger_source') != trigger_source:
        raise RouterError('role recovery trigger_source mismatch')
    requested_scope = str(transaction.get('recovery_scope') or 'targeted')
    payload_scope = str(payload.get('recovery_scope') or requested_scope)
    if payload_scope not in {requested_scope, 'full_crew'}:
        raise RouterError('role recovery scope mismatch')
    target_roles = [str(role) for role in transaction.get('target_role_keys') or []]
    payload_targets = payload.get('target_role_keys')
    if payload_targets != target_roles:
        raise RouterError('role recovery target_role_keys mismatch')
    raw_records = payload.get('recovered_role_agents') or payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('role recovery requires payload.recovered_role_agents list or object')
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    existing_by_role = {str(slot.get('role_key')): slot for slot in slots if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    full_crew = payload_scope == 'full_crew' or any((isinstance(raw, dict) and raw.get('recovery_result') == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT for raw in iterable))
    expected_roles = list(CREW_ROLE_KEYS) if full_crew else target_roles
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    records_by_role: dict[str, dict[str, Any]] = {}
    environment_blocked = False
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each recovered role agent record must be an object')
        role = str(raw.get('role_key') or '')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'role recovery record has unsupported role_key: {role!r}')
        if role not in expected_roles:
            raise RouterError(f'role recovery record {role} is outside the expected recovery scope')
        if role in records_by_role:
            raise RouterError(f'duplicate role recovery record for {role}')
        result = str(raw.get('recovery_result') or '')
        if result not in ROLE_RECOVERY_RESULTS:
            raise RouterError(f'{role} requires supported recovery_result')
        restore_attempted = raw.get('restore_attempted') is True
        restore_result = str(raw.get('restore_result') or 'unknown')
        targeted_attempted = raw.get('targeted_replacement_attempted') is True
        targeted_result = str(raw.get('targeted_replacement_result') or 'not_attempted')
        old_close_failed = raw.get('old_close_failed') is True
        spawn_capacity_full = raw.get('spawn_capacity_full') is True or targeted_result == 'capacity_full'
        slot_reconciliation_attempted = raw.get('slot_reconciliation_attempted') is True
        full_recycle_attempted = raw.get('full_crew_recycle_attempted') is True
        full_recycle_result = str(raw.get('full_crew_recycle_result') or 'not_attempted')
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            agent_id = raw.get('agent_id')
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RouterError(f'{role} requires a recovered live agent_id')
            if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
                raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
            if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
                raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
            if raw.get('rehydrated_for_run_id') != run_state['run_id']:
                raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
            if raw.get('memory_context_injected') is not True:
                raise RouterError(f'{role} recovery requires memory_context_injected=true')
            if raw.get('packet_ownership_reconciled') is not True:
                raise RouterError(f'{role} recovery requires packet_ownership_reconciled=true')
            if raw.get('role_binding_epoch_advanced') is not True:
                raise RouterError(f'{role} recovery requires role_binding_epoch_advanced=true')
        else:
            environment_blocked = True
            agent_id = None
        if result == ROLE_AGENT_OLD_RESTORE_RESULT:
            if not restore_attempted or restore_result != 'success':
                raise RouterError(f'{role} old-agent restore result requires restore_attempted=true and restore_result=success')
        elif result == ROLE_AGENT_TARGETED_REPLACEMENT_RESULT:
            if not restore_attempted or restore_result != 'failed':
                raise RouterError(f'{role} targeted replacement requires failed restore first')
            if not targeted_attempted or targeted_result != 'success':
                raise RouterError(f'{role} targeted replacement requires targeted_replacement_attempted=true and targeted_replacement_result=success')
        elif result == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT:
            if requested_scope == 'targeted' and (not (restore_attempted and restore_result == 'failed' and targeted_attempted and (targeted_result in {'failed', 'capacity_full'}) and slot_reconciliation_attempted)):
                raise RouterError(f'{role} full crew recycle requires targeted restore/replacement/slot reconciliation escalation')
            if not full_recycle_attempted or full_recycle_result != 'success':
                raise RouterError(f'{role} full crew recycle requires full_crew_recycle_attempted=true and full_crew_recycle_result=success')
        elif result == ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if not full_recycle_attempted or full_recycle_result != 'failed':
                raise RouterError(f'{role} environment_blocked requires failed full crew recycle')
        if old_close_failed and spawn_capacity_full and (not full_recycle_attempted):
            raise RouterError(f'{role} capacity/full-slot conflict requires full crew recycle escalation')
        if result in {ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, ROLE_AGENT_FULL_CREW_RECYCLE_RESULT}:
            if raw.get('superseded_agent_output_quarantined') is not True:
                raise RouterError(f'{role} replacement/recycle requires superseded_agent_output_quarantined=true')
        context = contexts[role]
        memory_status = context['role_memory_status']
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run memory')
        elif result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        old_slot = existing_by_role.get(role) or {}
        old_agent_id = raw.get('old_agent_id') or old_slot.get('agent_id')
        records_by_role[role] = {'role_key': role, 'old_agent_id': old_agent_id, 'agent_id': agent_id, 'model_policy': BACKGROUND_ROLE_MODEL_POLICY if agent_id else None, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY if agent_id else None, 'recovery_result': result, 'restore_attempted': restore_attempted, 'restore_result': restore_result, 'targeted_replacement_attempted': targeted_attempted, 'targeted_replacement_result': targeted_result, 'old_close_failed': old_close_failed, 'spawn_capacity_full': spawn_capacity_full, 'slot_reconciliation_attempted': slot_reconciliation_attempted, 'full_crew_recycle_attempted': full_recycle_attempted, 'full_crew_recycle_result': full_recycle_result, 'rehydrated_for_run_id': run_state['run_id'], 'memory_context_injected': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'packet_ownership_reconciled': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'role_binding_epoch_advanced': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'superseded_agent_output_quarantined': bool(raw.get('superseded_agent_output_quarantined')), 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available', 'replacement_seeded_from_common_run_context': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status != 'available', 'recorded_at': utc_now()}
    missing = [role for role in expected_roles if role not in records_by_role]
    if missing:
        raise RouterError(f"missing role recovery records: {', '.join(missing)}")
    if environment_blocked and any((record['recovery_result'] != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT for record in records_by_role.values())):
        raise RouterError('environment-blocked role recovery report cannot mix ready and blocked role records')
    return ([records_by_role[role] for role in expected_roles], transaction)

def _role_recovery_obligation_replay_path(router: ModuleType, run_root: Path, transaction_id: str) -> Path:
    _bind_router(router)
    safe_transaction = _safe_delivery_component(transaction_id or 'role-recovery')
    return router._role_recovery_dir(run_root) / f'{safe_transaction}_obligation_replay.json'

def _controller_action_entry_view(router: ModuleType, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
    if action:
        return dict(action)
    return {key: entry.get(key) for key in ('action_type', 'label', 'summary', 'to_role', 'allowed_reads', 'allowed_writes', 'allowed_external_events', 'expected_return_path', 'card_envelope_path', 'card_bundle_envelope_path', 'card_return_event', 'card_id', 'card_bundle_id') if entry.get(key) not in (None, '', [])}

def _controller_action_wait_roles(router: ModuleType, entry: dict[str, Any]) -> set[str]:
    _bind_router(router)
    action = router._controller_action_entry_view(entry)
    roles = {str(value).strip() for value in (entry.get('to_role'), entry.get('target_role'), entry.get('waiting_for_role'), action.get('to_role'), action.get('target_role'), action.get('waiting_for_role')) if isinstance(value, str) and value.strip()}
    if str(entry.get('action_type') or action.get('action_type') or '') == 'await_role_decision':
        for event in _controller_wait_allowed_external_events(entry):
            meta = EXTERNAL_EVENTS.get(event)
            if isinstance(meta, dict):
                role = _event_wait_role(event, meta)
                if role:
                    roles.add(role)
    return roles

def _role_recovery_action_sort_key(router: ModuleType, entry: dict[str, Any]) -> tuple[str, str, str]:
    _bind_router(router)
    return (str(entry.get('created_at') or ''), str(entry.get('router_scheduler_row_id') or ''), str(entry.get('action_id') or ''))

def _role_recovery_pending_return_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    for record in _pending_return_records(run_root, run_id):
        if _pending_action_matches_card_return(action, record):
            return record
    return None

def _role_recovery_wait_candidates(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], target_roles: set[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    del project_root
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return []
    candidates: list[dict[str, Any]] = []
    run_id = str(run_state['run_id'])
    for action_path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(action_path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if str(entry.get('status') or '') in CONTROLLER_ACTION_CLOSED_STATUSES:
            continue
        action = router._controller_action_entry_view(entry)
        action_type = str(entry.get('action_type') or action.get('action_type') or '')
        if action_type not in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event', 'await_role_decision'}:
            continue
        wait_roles = router._controller_action_wait_roles(entry)
        matched_roles = sorted(wait_roles.intersection(target_roles))
        if not matched_roles:
            continue
        pending_return = None
        replay_kind = 'role_output'
        if action_type in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event'}:
            replay_kind = 'card_ack'
            pending_return = router._role_recovery_pending_return_for_action(run_root, run_id, action)
        candidates.append({'entry': entry, 'action': action, 'action_path': action_path, 'kind': replay_kind, 'matched_roles': matched_roles, 'pending_return': pending_return, 'sort_key': router._role_recovery_action_sort_key(entry)})
    candidates.sort(key=lambda item: item['sort_key'])
    return candidates

def _mark_controller_action_done_by_role_recovery(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], *, evidence: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_path = candidate['action_path']
    entry = read_json_if_exists(action_path)
    if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        entry = dict(candidate['entry'])
    now = utc_now()
    entry['status'] = 'done'
    entry['completed_at'] = now
    entry['completion_source'] = 'role_recovery_obligation_replay'
    entry['router_reconciliation_status'] = 'reconciled'
    entry['router_reconciled_at'] = now
    entry['satisfied_by_existing_recovery_evidence'] = evidence
    entry['controller_receipt_required'] = False
    entry['router_must_not_mark_done_without_controller_receipt'] = False
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation={'source': 'role_recovery_obligation_replay', 'evidence': evidence, 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _role_recovery_existing_event_for_wait(router: ModuleType, run_state: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    allowed_events = set(_controller_wait_allowed_external_events(entry))
    if not allowed_events:
        return None
    for record in run_state.get('events') or []:
        if isinstance(record, dict) and record.get('event') in allowed_events:
            return record
    return None

def _settle_role_recovery_candidate_if_evidence_exists(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    action = dict(candidate['action'])
    if candidate['kind'] == 'card_ack':
        pending_return = candidate.get('pending_return')
        if isinstance(pending_return, dict):
            pending = dict(pending_return)
            pending.update({key: value for key, value in action.items() if value not in (None, '', [])})
        else:
            pending = action
        expected_return_path = str(pending.get('expected_return_path') or '')
        if not expected_return_path or not resolve_project_path(project_root, expected_return_path).exists():
            return None
        result = _try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, pending)
        if not result.get('consumed'):
            return None
        _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_recovery_obligation_replay')
        evidence = {'kind': 'existing_card_ack', 'expected_return_path': expected_return_path, 'validation': result.get('result')}
        router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
        return {'outcome': 'settled_existing_ack', 'evidence': evidence}
    event_record = router._role_recovery_existing_event_for_wait(run_state, candidate['entry'])
    if event_record is None:
        return None
    closure = _close_waiting_controller_actions_for_external_event(project_root, run_root, run_state, event=str(event_record.get('event') or ''), payload=event_record.get('payload') if isinstance(event_record.get('payload'), dict) else {}, source='role_recovery_obligation_replay')
    evidence = {'kind': 'existing_role_output_event', 'event': event_record.get('event'), 'recorded_at': event_record.get('recorded_at'), 'wait_closure': closure}
    router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
    return {'outcome': 'settled_existing_output', 'evidence': evidence}

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
    target_roles = {str(record.get('role_key') or '') for record in records if record.get('recovery_result') != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT}
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

def _role_no_output_liveness_result(router: ModuleType, payload: dict[str, Any] | None) -> str:
    _bind_router(router)
    payload = payload or {}
    liveness_probe = payload.get('liveness_probe') if isinstance(payload.get('liveness_probe'), dict) else {}
    for key in ('liveness_probe_result', 'host_liveness_status', 'bounded_wait_result', 'result'):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = liveness_probe.get('result')
    return value.strip() if isinstance(value, str) else ''

def _payload_indicates_role_no_output(router: ModuleType, payload: dict[str, Any] | None) -> bool:
    _bind_router(router)
    return router._role_no_output_liveness_result(payload) in WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS

def _role_no_output_target_roles(router: ModuleType, payload: dict[str, Any] | None) -> list[str]:
    _bind_router(router)
    payload = payload or {}
    return router._role_recovery_target_roles(payload.get('target_role_keys') or payload.get('role_key') or payload.get('missing_role_key'))

def _role_no_output_wait_candidate(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, target_role_keys: list[str], payload: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    candidates = router._role_recovery_wait_candidates(project_root, run_root, run_state, set(target_role_keys))
    if not candidates:
        return None
    wanted_action_id = str(payload.get('controller_action_id') or payload.get('current_controller_action_id') or '').strip()
    wanted_row_id = str(payload.get('router_scheduler_row_id') or '').strip()
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    pending_action_id = str(pending.get('controller_action_id') or '').strip()
    pending_row_id = str(pending.get('router_scheduler_row_id') or '').strip()
    for candidate in candidates:
        entry = candidate['entry']
        if wanted_action_id and entry.get('action_id') == wanted_action_id:
            return candidate
        if wanted_row_id and entry.get('router_scheduler_row_id') == wanted_row_id:
            return candidate
    for candidate in candidates:
        entry = candidate['entry']
        if pending_action_id and entry.get('action_id') == pending_action_id:
            return candidate
        if pending_row_id and entry.get('router_scheduler_row_id') == pending_row_id:
            return candidate
    return candidates[0]

def _role_no_output_reissue_attempt(router: ModuleType, candidate: dict[str, Any]) -> int:
    _bind_router(router)
    entry = candidate.get('entry') if isinstance(candidate.get('entry'), dict) else {}
    action = candidate.get('action') if isinstance(candidate.get('action'), dict) else {}
    for source in (action, entry):
        raw = source.get('role_no_output_reissue_attempt') or source.get('no_output_reissue_attempt')
        if isinstance(raw, int):
            return max(0, raw)
        if isinstance(raw, str) and raw.isdigit():
            return max(0, int(raw))
    return 0

def _role_no_output_replacement_action(router: ModuleType, candidate: dict[str, Any], *, attempt: int) -> dict[str, Any]:
    _bind_router(router)
    original = candidate['entry']
    action = dict(candidate['action'])
    original_action_id = str(original.get('action_id') or '')
    original_row_id = str(original.get('router_scheduler_row_id') or '')
    base_label = str(action.get('label') or original.get('label') or 'role_no_output_wait')
    if '_no_output_reissue_' in base_label:
        base_label = base_label.split('_no_output_reissue_', 1)[0]
    target_role = str((candidate.get('matched_roles') or [''])[0])
    for key in ('controller_action_id', 'controller_action_path', 'controller_receipt_path', 'router_scheduler_row_id', 'created_at', 'updated_at', 'last_seen_at'):
        action.pop(key, None)
    action['action_type'] = 'await_role_decision'
    action['label'] = f'{base_label}_no_output_reissue_{attempt:03d}'
    action['idempotency_key'] = f'role-no-output-reissue:{original_action_id or original_row_id}:{attempt}'
    action['replaces'] = original_action_id
    action['replaces_controller_action_id'] = original_action_id
    action['replaces_router_scheduler_row_id'] = original_row_id
    action['replacement_reason'] = 'role_no_output_missing_expected_event'
    action['role_no_output_reissue_attempt'] = attempt
    action['max_role_no_output_reissue_attempts'] = ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS
    action['target_no_output_role'] = target_role
    action['summary'] = f'Role {target_role} was reachable or completed but Router still lacks the expected output. This replaces the prior wait with the same authorized work; the role must submit the original output or blocker through the Router-directed runtime path.'
    action['controller_visibility'] = 'metadata_only_no_output_reissue'
    action['sealed_body_reads_allowed'] = False
    action['chat_history_progress_inference_allowed'] = False
    return action

def _supersede_role_no_output_original_wait(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], replacement_entry: dict[str, Any]) -> dict[str, Any]:
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
    entry['completion_source'] = 'role_no_output_reissue'
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='superseded', reconciliation={'source': 'role_no_output_reissue', 'superseded_by': replacement_action_id, 'replacement_reason': replacement_entry.get('replacement_reason'), 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _record_role_no_output_reissue(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, source_event: str) -> dict[str, Any]:
    _bind_router(router)
    payload = dict(payload or {})
    event = 'controller_reports_role_no_output'
    target_role_keys = router._role_no_output_target_roles(payload)
    _reconcile_durable_wait_evidence(project_root, run_root, run_state)
    _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_no_output_reissue_pre_scan')
    candidate = router._role_no_output_wait_candidate(project_root, run_root, run_state, target_role_keys=target_role_keys, payload=payload)
    if candidate is None:
        run_state['flags']['role_no_output_pm_escalation_required'] = True
        blocker = router._write_control_blocker(project_root, run_root, run_state, source='role_no_output_reissue_no_wait_candidate', error_message='Role no-output report could not find the original Router wait to reissue.', event=event, action_type='role_no_output_reissue', payload={**payload, 'target_role_keys': target_role_keys, 'source_event': source_event})
        return {'ok': False, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': False, 'pm_escalation_required': True, 'control_blocker_id': blocker.get('blocker_id')}
    attempt = router._role_no_output_reissue_attempt(candidate) + 1
    if attempt > ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS:
        run_state['flags']['role_no_output_pm_escalation_required'] = True
        blocker = router._write_control_blocker(project_root, run_root, run_state, source='role_no_output_reissue_budget_exhausted', error_message='Role no-output reissue budget exhausted before the expected Router output arrived.', event=event, action_type='role_no_output_reissue', payload={**payload, 'target_role_keys': target_role_keys, 'source_event': source_event, 'direct_retry_attempts_used': ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS, 'direct_retry_budget': ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS})
        return {'ok': False, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': False, 'pm_escalation_required': True, 'control_blocker_id': blocker.get('blocker_id')}
    replacement_action = router._role_no_output_replacement_action(candidate, attempt=attempt)
    replacement_entry = router._write_controller_action_entry(project_root, run_root, run_state, replacement_action)
    router._supersede_role_no_output_original_wait(project_root, run_root, run_state, candidate, replacement_entry)
    run_state['pending_action'] = dict(replacement_entry['action'])
    run_state['flags']['role_no_output_reissue_recorded'] = True
    run_state['flags']['role_no_output_pm_escalation_required'] = False
    record = {'event': event, 'summary': EXTERNAL_EVENTS[event]['summary'], 'payload': payload, 'source_event': source_event, 'target_role_keys': target_role_keys, 'controller_action_id': candidate['entry'].get('action_id'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'replacement_router_scheduler_row_id': replacement_entry.get('router_scheduler_row_id'), 'role_no_output_reissue_attempt': attempt, 'recorded_at': utc_now()}
    run_state['events'].append(record)
    append_history(run_state, 'router_reissued_role_wait_after_no_output', {'source_event': source_event, 'target_role_keys': target_role_keys, 'controller_action_id': candidate['entry'].get('action_id'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'role_no_output_reissue_attempt': attempt, 'role_recovery_requested': False})
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f'after_external_event:{event}')
    router._sync_derived_run_views(project_root, run_root, run_state, reason=f'after_external_event:{event}')
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'event': event, 'source_event': source_event, 'role_no_output_reissue_created': True, 'role_no_output_reissue_attempt': attempt, 'replacement_action': replacement_entry.get('action'), 'replacement_controller_action_id': replacement_entry.get('action_id'), 'role_recovery_requested': False, 'pm_escalation_required': False}

def _write_role_recovery_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    records, transaction = router._normalize_role_recovery_agent_records(project_root, run_root, run_state, payload)
    environment_blocked = any((record['recovery_result'] == ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT for record in records))
    crew_path = run_root / 'crew_ledger.json'
    crew = read_json_if_exists(crew_path) or {'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'role_slots': []}
    current_generation = router._current_crew_generation(crew)
    full_crew = any((record['recovery_result'] == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT for record in records))
    next_generation = current_generation + 1 if full_crew else current_generation
    slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    slots_by_role = {str(slot.get('role_key')): dict(slot) for slot in slots if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    for role in CREW_ROLE_KEYS:
        slots_by_role.setdefault(role, {'role_key': role, 'status': 'unknown', 'agent_id': None})
    if not environment_blocked:
        for record in records:
            role = record['role_key']
            old = slots_by_role.get(role, {})
            old_epoch = old.get('role_binding_epoch')
            epoch = int(old_epoch) if isinstance(old_epoch, int) else 0
            superseded = list(old.get('superseded_agent_ids') or []) if isinstance(old.get('superseded_agent_ids'), list) else []
            old_agent_id = record.get('old_agent_id')
            if isinstance(old_agent_id, str) and old_agent_id and (old_agent_id != record.get('agent_id')) and (old_agent_id not in superseded):
                superseded.append(old_agent_id)
            slots_by_role[role] = {**old, 'role_key': role, 'status': 'live_agent_recovered' if not full_crew else 'live_agent_recycled', 'agent_id': record['agent_id'], 'model_policy': record['model_policy'], 'reasoning_effort_policy': record['reasoning_effort_policy'], 'crew_generation': next_generation, 'role_binding_epoch': epoch + 1, 'last_role_recovery_transaction_id': transaction['transaction_id'], 'last_role_recovery_result': record['recovery_result'], 'superseded_agent_ids': superseded, 'superseded_agent_output_quarantined': bool(record.get('superseded_agent_output_quarantined')), 'memory_seeded_from_current_run': bool(record.get('memory_seeded_from_current_run')), 'replacement_seeded_from_common_run_context': bool(record.get('replacement_seeded_from_common_run_context')), 'recovered_at': record['recorded_at']}
    all_slots = [slots_by_role[role] for role in CREW_ROLE_KEYS]
    all_six_ready = not environment_blocked and all((isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) for slot in all_slots))
    report_path = router._role_recovery_report_path(run_root)
    report = {'schema_version': ROLE_RECOVERY_REPORT_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction['transaction_id'], 'trigger_source': transaction['trigger_source'], 'recovery_scope': payload.get('recovery_scope') or transaction['recovery_scope'], 'target_role_keys': transaction['target_role_keys'], 'recorded_at': utc_now(), 'priority': 'preempt_normal_work', 'normal_work_suspended_until_report': True, 'all_six_roles_ready': all_six_ready, 'environment_blocked': environment_blocked, 'crew_generation_before': current_generation, 'crew_generation_after': next_generation, 'role_records': records, 'packet_ownership_reconciled': all((record.get('packet_ownership_reconciled') for record in records)) if not environment_blocked else False, 'memory_context_injected': all((record.get('memory_context_injected') for record in records)) if not environment_blocked else False, 'stale_generation_output_quarantined': all((record.get('superseded_agent_output_quarantined') or record.get('recovery_result') == ROLE_AGENT_OLD_RESTORE_RESULT for record in records)) if not environment_blocked else False, 'pm_decision_required_before_normal_work': False, 'mechanical_obligation_replay_before_pm': True, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'source_paths': {'transaction': project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), 'state_load': project_relative(project_root, router._role_recovery_state_path(run_root)), 'crew_ledger': project_relative(project_root, crew_path), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}}
    write_json(report_path, report)
    history = crew.get('role_recovery_history') if isinstance(crew.get('role_recovery_history'), list) else []
    history.append({'transaction_id': transaction['transaction_id'], 'report_path': project_relative(project_root, report_path), 'trigger_source': transaction['trigger_source'], 'target_role_keys': transaction['target_role_keys'], 'recovery_scope': report['recovery_scope'], 'all_six_roles_ready': all_six_ready, 'environment_blocked': environment_blocked, 'recorded_at': report['recorded_at']})
    crew.update({'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'crew_generation': next_generation, 'role_slots': all_slots, 'latest_role_recovery_report': project_relative(project_root, report_path), 'role_recovery_history': history, 'updated_at': utc_now()})
    write_json(crew_path, crew)
    ready_records = [record for record in records if record['recovery_result'] != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT]
    if ready_records:
        _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), ready_records, default_lifecycle_phase='role_liveness_recovery', resume_tick_id=str(transaction['transaction_id']), source_action='recover_role_agents')
    crew_rehydration_path = run_root / 'continuation' / 'crew_rehydration_report.json'
    if not environment_blocked:
        write_json(crew_rehydration_path, {'schema_version': 'flowpilot.crew_rehydration_report.v1', 'run_id': run_state['run_id'], 'role_recovery_report_path': project_relative(project_root, report_path), 'resume_tick_id': str(transaction['transaction_id']), 'background_agents_mode': router._startup_answers_from_run(run_root).get('background_agents'), 'recorded_at': report['recorded_at'], 'all_six_roles_ready': all_six_ready, 'current_run_memory_complete': bool(report['memory_context_injected']), 'missing_memory_role_keys': [record['role_key'] for record in records if record.get('role_memory_status') != 'available'], 'pm_memory_rehydrated': any((slot.get('role_key') == 'project_manager' and isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) for slot in all_slots)), 'liveness_preflight': {'checked_at': report['recorded_at'], 'probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': str(transaction['transaction_id']), 'all_liveness_probes_started_before_wait': True, 'roles_checked': list(transaction['target_role_keys']), 'replacement_role_keys': [record['role_key'] for record in records if record['recovery_result'] in {ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, ROLE_AGENT_FULL_CREW_RECYCLE_RESULT}], 'wait_agent_timeout_treated_as_active': False, 'decision': 'roles_ready_after_role_recovery'}, 'role_records': records, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False})
    run_state['flags']['role_recovery_roles_restored'] = not environment_blocked
    run_state['flags']['role_recovery_report_written'] = True
    run_state['flags']['role_recovery_environment_blocked'] = environment_blocked
    if environment_blocked:
        router._write_control_blocker(project_root, run_root, run_state, source='role_recovery_environment_blocked', error_message='Role recovery failed after full crew recycle; environment or user action is required before route work can continue.', action_type='role_recovery_environment_blocked', payload={'role_recovery_report_path': project_relative(project_root, report_path), 'transaction_id': transaction['transaction_id'], 'target_role_keys': transaction['target_role_keys']})
        return
    run_state['flags']['resume_reentry_requested'] = True
    run_state['flags']['resume_state_loaded'] = True
    run_state['flags']['resume_roles_restored'] = True
    run_state['flags']['resume_role_agents_rehydrated'] = True
    run_state['flags']['crew_rehydration_report_written'] = True
    replay = router._plan_role_recovery_obligation_replay(project_root, run_root, run_state, transaction=transaction, records=ready_records, report_path=report_path)
    report['role_recovery_obligation_replay_path'] = run_state['role_recovery_obligation_replay']['path']
    report['pm_decision_required_before_normal_work'] = bool(replay.get('pm_escalation_required'))
    report['mechanical_obligation_replay_completed'] = not bool(replay.get('pm_escalation_required'))
    write_json(report_path, report)
    run_state['flags']['pm_resume_recovery_decision_returned'] = not bool(replay.get('pm_escalation_required'))
    run_state['flags']['role_recovery_requested'] = False

def _resume_role_rehydration_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    mode = answers.get('background_agents')
    contexts = router._resume_role_contexts(project_root, run_root, run_state)
    missing_memory = [item['role_key'] for item in contexts if item['role_memory_status'] != 'available']
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    liveness_probe_batch_id = router._resume_liveness_probe_batch_id(run_state)
    extra: dict[str, Any] = {'background_agents_mode': mode, 'role_keys': list(CREW_ROLE_KEYS), 'resume_tick_id': router._latest_resume_tick_id(run_state), 'awaiting_role_from_packet_ledger': resume_next.get('next_recipient_role'), 'resume_next_recipient_from_packet_ledger': resume_next, 'role_rehydration_request': contexts, 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'applies_to': ['heartbeat_resume_rehydration', 'manual_resume_rehydration', 'missing_role_replacement']}, 'memory_missing_role_keys': missing_memory, 'crew_rehydration_report_path': project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), 'liveness_probe_batch_id': liveness_probe_batch_id, 'liveness_preflight_required': True, 'liveness_preflight_policy': {'roles_to_check': list(CREW_ROLE_KEYS), 'current_waiting_role_source': 'packet_ledger.next_recipient_role', 'resume_agent_check_required': True, 'concurrent_probe_required': True, 'probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': liveness_probe_batch_id, 'start_all_probes_before_waiting': True, 'bounded_wait_allowed': True, 'wait_agent_timeout_result': 'timeout_unknown', 'timeout_unknown_is_active': False, 'missing_cancelled_unknown_requires_replacement': True, 'heartbeat_and_manual_resume_share_path': True}, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    if mode == 'allow':
        extra.update({'requires_payload': 'rehydrated_role_agents', 'payload_contract': _resume_role_rehydration_payload_contract(run_state, contexts), 'requires_host_spawn': False, 'requires_host_role_rehydration': True, 'requires_host_spawn_for_replacements': True, 'spawn_required_only_for_replacements': True, 'reuse_live_agents_when_active': True, 'spawn_policy': 'reuse_confirmed_live_agents_spawn_only_missing_cancelled_completed_unknown_or_timeout', 'pm_memory_rehydration_required': True})
    elif mode == 'single-agent':
        extra.update({'requires_host_spawn': False, 'single_agent_continuity_authorized': True})
    return extra

def _normalize_resume_role_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    mode = answers.get('background_agents')
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    current_generation = router._current_crew_generation(crew)
    existing_slots = {str(slot.get('role_key')): slot for slot in (crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []) if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    resume_tick_id = router._latest_resume_tick_id(run_state)
    if mode == 'single-agent':
        return [{'role_key': role, 'status': 'single_agent_resume_continuity_authorized', 'agent_id': None, 'rehydration_result': 'not_requested_single_agent_continuity', 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': resume_tick_id, 'host_liveness_status': 'not_applicable_single_agent', 'liveness_decision': 'single_agent_resume_continuity_authorized', 'resume_agent_attempted': False, 'bounded_wait_result': 'not_applicable', 'wait_agent_timeout_treated_as_active': False, 'fallback_authorized_by_startup_answer': True, 'recorded_at': utc_now()} for role in CREW_ROLE_KEYS]
    if mode != 'allow':
        raise RouterError('cannot rehydrate roles before background_agents startup answer is recorded')
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('resume role rehydration requires background_agents_capability_status=available')
    expected_batch_id = router._resume_liveness_probe_batch_id(run_state)
    if payload.get('liveness_probe_batch_id') != expected_batch_id:
        raise RouterError(f'resume role rehydration requires liveness_probe_batch_id={expected_batch_id}')
    if payload.get('liveness_probe_mode') != ROLE_AGENT_LIVENESS_PROBE_MODE:
        raise RouterError(f'resume role rehydration requires liveness_probe_mode={ROLE_AGENT_LIVENESS_PROBE_MODE}')
    if payload.get('all_liveness_probes_started_before_wait') is not True:
        raise RouterError('resume role rehydration requires all_liveness_probes_started_before_wait=true')
    raw_records = payload.get('rehydrated_role_agents') or payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('rehydrate_role_agents requires payload.rehydrated_role_agents list or object')
    records_by_role: dict[str, dict[str, Any]] = {}
    probe_started_times: list[datetime] = []
    probe_completed_times: list[datetime] = []

    def parse_probe_time(role_key: str, field: str, value: object) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise RouterError(f'{role_key} requires {field}')
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise RouterError(f'{role_key} requires ISO timestamp {field}') from exc
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each rehydrated role agent record must be an object')
        role = raw.get('role_key')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'rehydrated role record has unsupported role_key: {role!r}')
        if role in records_by_role:
            raise RouterError(f'duplicate rehydrated role record for {role}')
        context = contexts[str(role)]
        old_slot = existing_slots.get(str(role)) or {}
        old_epoch = old_slot.get('role_binding_epoch')
        role_epoch = int(old_epoch) if isinstance(old_epoch, int) else 0
        agent_id = raw.get('agent_id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f'{role} requires a non-empty live resume agent_id')
        if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
            raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
        if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
            raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
        result = raw.get('rehydration_result') or raw.get('spawn_result')
        if result not in RESUME_ROLE_AGENT_RESULTS:
            raise RouterError(f'{role} requires resume rehydration result')
        host_liveness_status = str(raw.get('host_liveness_status') or '')
        if host_liveness_status not in ROLE_AGENT_HOST_LIVENESS_STATUSES:
            raise RouterError(f'{role} requires host_liveness_status')
        liveness_decision = str(raw.get('liveness_decision') or '')
        if liveness_decision not in ROLE_AGENT_LIVENESS_DECISIONS:
            raise RouterError(f'{role} requires liveness_decision')
        if raw.get('resume_agent_attempted') is not True:
            raise RouterError(f'{role} requires resume_agent_attempted=true')
        bounded_wait_result = str(raw.get('bounded_wait_result') or '')
        if bounded_wait_result not in ROLE_AGENT_BOUNDED_WAIT_RESULTS:
            raise RouterError(f'{role} requires bounded_wait_result')
        if raw.get('liveness_probe_batch_id') != expected_batch_id:
            raise RouterError(f'{role} liveness probe batch id mismatch')
        if raw.get('liveness_probe_mode') != ROLE_AGENT_LIVENESS_PROBE_MODE:
            raise RouterError(f'{role} requires concurrent liveness probe mode')
        bounded_wait_ms = raw.get('bounded_wait_ms')
        if isinstance(bounded_wait_ms, bool) or not isinstance(bounded_wait_ms, int) or bounded_wait_ms < 0:
            raise RouterError(f'{role} requires nonnegative bounded_wait_ms')
        started_at = parse_probe_time(str(role), 'liveness_probe_started_at', raw.get('liveness_probe_started_at'))
        completed_at = parse_probe_time(str(role), 'liveness_probe_completed_at', raw.get('liveness_probe_completed_at'))
        if completed_at < started_at:
            raise RouterError(f'{role} liveness probe completed before it started')
        probe_started_times.append(started_at)
        probe_completed_times.append(completed_at)
        if raw.get('wait_agent_timeout_treated_as_active') is not False:
            raise RouterError(f'{role} must record wait_agent_timeout_treated_as_active=false')
        if bounded_wait_result == 'timeout_unknown' and result == ROLE_AGENT_CONTINUITY_RESULT:
            raise RouterError(f'{role} wait_agent timeout_unknown cannot be treated as active continuity')
        if host_liveness_status in {'missing', 'cancelled', 'unknown', 'timeout_unknown'} and liveness_decision == 'confirmed_existing_agent':
            raise RouterError(f'{role} missing/cancelled/unknown host liveness cannot confirm existing agent')
        if host_liveness_status == 'completed' and liveness_decision == 'confirmed_existing_agent':
            raise RouterError(f'{role} completed host liveness cannot confirm existing agent')
        if result == ROLE_AGENT_CONTINUITY_RESULT and (not (host_liveness_status == 'active' and liveness_decision == 'confirmed_existing_agent')):
            raise RouterError(f'{role} live continuity requires active host liveness')
        if result == ROLE_AGENT_REHYDRATION_RESULT and liveness_decision != 'spawned_replacement_from_current_run_memory':
            raise RouterError(f'{role} replacement rehydration requires spawned_replacement_from_current_run_memory')
        if result == ROLE_AGENT_REHYDRATION_RESULT and host_liveness_status == 'active':
            raise RouterError(f'{role} active host liveness must use live_agent_continuity_confirmed, not replacement rehydration')
        if raw.get('rehydrated_for_run_id') != run_state['run_id']:
            raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
        if raw.get('rehydrated_after_resume_tick_id') != resume_tick_id:
            raise RouterError(f'{role} must be rehydrated_after_resume_tick_id={resume_tick_id}')
        rehydrated_after_state_loaded = raw.get('rehydrated_after_resume_state_loaded')
        legacy_spawned_after_state_loaded = raw.get('spawned_after_resume_state_loaded')
        if rehydrated_after_state_loaded is not True and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f'{role} must be rehydrated_after_resume_state_loaded=true')
        if result == ROLE_AGENT_REHYDRATION_RESULT and legacy_spawned_after_state_loaded is not True:
            raise RouterError(f'{role} replacement rehydration requires spawned_after_resume_state_loaded=true')
        if raw.get('core_prompt_path') != context['core_prompt_path'] or raw.get('core_prompt_hash') != context['core_prompt_hash']:
            raise RouterError(f'{role} core prompt identity mismatch')
        memory_status = context['role_memory_status']
        if memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run role memory')
        else:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing role memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        if role == 'project_manager' and raw.get('pm_resume_context_delivered') is not True:
            raise RouterError('project_manager resume rehydration requires PM context delivery')
        records_by_role[str(role)] = {'role_key': str(role), 'status': 'live_agent_rehydrated', 'agent_id': agent_id.strip(), 'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'rehydration_result': str(result), 'host_liveness_status': host_liveness_status, 'liveness_decision': liveness_decision, 'resume_agent_attempted': True, 'bounded_wait_result': bounded_wait_result, 'bounded_wait_ms': bounded_wait_ms, 'liveness_probe_batch_id': expected_batch_id, 'liveness_probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_started_at': raw.get('liveness_probe_started_at'), 'liveness_probe_completed_at': raw.get('liveness_probe_completed_at'), 'wait_agent_timeout_treated_as_active': False, 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': resume_tick_id, 'rehydrated_after_resume_state_loaded': True, 'spawned_after_resume_state_loaded': result == ROLE_AGENT_REHYDRATION_RESULT, 'crew_generation': current_generation, 'role_binding_epoch': role_epoch + (1 if result == ROLE_AGENT_REHYDRATION_RESULT or agent_id.strip() != str(old_slot.get('agent_id') or '') else 0), 'superseded_agent_ids': [str(old_slot.get('agent_id'))] if result == ROLE_AGENT_REHYDRATION_RESULT and isinstance(old_slot.get('agent_id'), str) and (old_slot.get('agent_id') != agent_id.strip()) else [], 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': memory_status == 'available', 'replacement_seeded_from_common_run_context': memory_status != 'available', 'pm_resume_context_delivered': role == 'project_manager', 'recorded_at': utc_now()}
    if probe_started_times and probe_completed_times and (max(probe_started_times) > min(probe_completed_times)):
        raise RouterError('all liveness probes must start before waiting for individual results')
    missing = [role for role in CREW_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing rehydrated live role agent records: {', '.join(missing)}")
    return [records_by_role[role] for role in CREW_ROLE_KEYS]

def _write_resume_role_rehydration_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    records = router._normalize_resume_role_agent_records(project_root, run_root, run_state, payload)
    memory_complete = all((record.get('role_memory_status') == 'available' for record in records))
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    timeout_unknown_roles = [record['role_key'] for record in records if record.get('host_liveness_status') == 'timeout_unknown' or record.get('bounded_wait_result') == 'timeout_unknown']
    missing_or_cancelled_roles = [record['role_key'] for record in records if record.get('host_liveness_status') in {'missing', 'cancelled', 'unknown'}]
    replacement_roles = [record['role_key'] for record in records if record.get('liveness_decision') == 'spawned_replacement_from_current_run_memory']
    report_path = run_root / 'continuation' / 'crew_rehydration_report.json'
    report = {'schema_version': 'flowpilot.crew_rehydration_report.v1', 'run_id': run_state['run_id'], 'resume_tick_id': router._latest_resume_tick_id(run_state), 'background_agents_mode': router._startup_answers_from_run(run_root).get('background_agents'), 'recorded_at': utc_now(), 'source_paths': {'resume_reentry': project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'crew_memory': project_relative(project_root, run_root / 'crew_memory'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'role_io_protocol_ledger': project_relative(project_root, _role_io_protocol_ledger_path(run_root)), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}, 'all_six_roles_ready': len(records) == len(CREW_ROLE_KEYS), 'liveness_preflight': {'checked_at': utc_now(), 'probe_mode': ROLE_AGENT_LIVENESS_PROBE_MODE, 'liveness_probe_batch_id': router._resume_liveness_probe_batch_id(run_state), 'all_liveness_probes_started_before_wait': True, 'awaiting_role': resume_next.get('next_recipient_role'), 'roles_checked': [record['role_key'] for record in records], 'timeout_unknown_role_keys': timeout_unknown_roles, 'missing_cancelled_or_unknown_role_keys': missing_or_cancelled_roles, 'replacement_role_keys': replacement_roles, 'wait_agent_timeout_treated_as_active': False, 'decision': 'roles_ready_after_replacement' if replacement_roles else 'all_roles_active'}, 'current_run_memory_complete': memory_complete, 'missing_memory_role_keys': [record['role_key'] for record in records if record.get('role_memory_status') != 'available'], 'pm_memory_rehydrated': any((record['role_key'] == 'project_manager' and record.get('pm_resume_context_delivered') is True and (record.get('role_memory_status') == 'available') for record in records)), 'role_records': records, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    write_json(report_path, report)
    crew_path = run_root / 'crew_ledger.json'
    crew = read_json_if_exists(crew_path)
    history = crew.get('resume_rehydration_history') if isinstance(crew.get('resume_rehydration_history'), list) else []
    history.append({'report_path': project_relative(project_root, report_path), 'resume_tick_id': report['resume_tick_id'], 'recorded_at': report['recorded_at'], 'all_six_roles_ready': report['all_six_roles_ready'], 'current_run_memory_complete': memory_complete, 'liveness_decision': report['liveness_preflight']['decision'], 'timeout_unknown_role_keys': timeout_unknown_roles, 'missing_cancelled_or_unknown_role_keys': missing_or_cancelled_roles})
    crew.update({'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'role_slots': records, 'crew_generation': router._current_crew_generation(crew), 'latest_resume_rehydration_report': project_relative(project_root, report_path), 'resume_rehydration_history': history, 'updated_at': utc_now()})
    write_json(crew_path, crew)
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') == ROLE_RECOVERY_TRANSACTION_SCHEMA:
        role_recovery_report_path = router._role_recovery_report_path(run_root)
        replay_ready = memory_complete and bool(report['all_six_roles_ready'])
        role_recovery_report = {'schema_version': ROLE_RECOVERY_REPORT_SCHEMA, 'run_id': run_state['run_id'], 'transaction_id': transaction.get('transaction_id'), 'trigger_source': transaction.get('trigger_source'), 'recovery_scope': transaction.get('recovery_scope'), 'target_role_keys': transaction.get('target_role_keys') or list(CREW_ROLE_KEYS), 'recorded_at': report['recorded_at'], 'priority': 'preempt_normal_work', 'normal_work_suspended_until_report': True, 'all_six_roles_ready': report['all_six_roles_ready'], 'environment_blocked': False, 'crew_generation_after': crew.get('crew_generation'), 'role_records': [{'role_key': record['role_key'], 'old_agent_id': None, 'agent_id': record.get('agent_id'), 'recovery_result': ROLE_AGENT_OLD_RESTORE_RESULT if record.get('rehydration_result') == ROLE_AGENT_CONTINUITY_RESULT else ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, 'memory_context_injected': record.get('role_memory_status') == 'available', 'packet_ownership_reconciled': True, 'role_binding_epoch': record.get('role_binding_epoch'), 'crew_generation': record.get('crew_generation'), 'superseded_agent_output_quarantined': bool(record.get('superseded_agent_ids'))} for record in records], 'packet_ownership_reconciled': True, 'memory_context_injected': memory_complete, 'stale_generation_output_quarantined': True, 'pm_decision_required_before_normal_work': not replay_ready, 'mechanical_obligation_replay_before_pm': replay_ready, 'mechanical_obligation_replay_completed': False, 'compatibility_crew_rehydration_report': project_relative(project_root, report_path), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
        write_json(role_recovery_report_path, role_recovery_report)
        run_state['flags']['role_recovery_state_loaded'] = True
        run_state['flags']['role_recovery_roles_restored'] = True
        run_state['flags']['role_recovery_report_written'] = True
        run_state['flags']['role_recovery_environment_blocked'] = False
        run_state['flags']['role_recovery_requested'] = False
        if replay_ready:
            replay = router._plan_role_recovery_obligation_replay(project_root, run_root, run_state, transaction=transaction, records=role_recovery_report['role_records'], report_path=role_recovery_report_path)
            role_recovery_report['role_recovery_obligation_replay_path'] = run_state['role_recovery_obligation_replay']['path']
            role_recovery_report['pm_decision_required_before_normal_work'] = bool(replay.get('pm_escalation_required'))
            role_recovery_report['mechanical_obligation_replay_completed'] = not bool(replay.get('pm_escalation_required'))
            write_json(role_recovery_report_path, role_recovery_report)
            run_state['flags']['pm_resume_recovery_decision_returned'] = not bool(replay.get('pm_escalation_required'))
        else:
            skipped_reason = 'missing_current_run_memory' if not memory_complete else 'roles_not_ready'
            role_recovery_report['resume_rehydration_replay_skipped_reason'] = skipped_reason
            write_json(role_recovery_report_path, role_recovery_report)
            run_state['flags']['role_recovery_obligations_scanned'] = False
            run_state['flags']['role_recovery_obligation_replay_completed'] = False
            run_state['flags']['role_recovery_pm_escalation_required'] = True
            run_state['flags']['pm_resume_recovery_decision_returned'] = False
            append_history(run_state, 'router_skipped_resume_obligation_replay', {'transaction_id': transaction.get('transaction_id'), 'reason': skipped_reason, 'memory_complete': memory_complete, 'all_six_roles_ready': report['all_six_roles_ready']})
    _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), records, default_lifecycle_phase='heartbeat_rehydration', resume_tick_id=report['resume_tick_id'], source_action='rehydrate_role_agents')
    run_state['flags']['resume_roles_restored'] = True
    run_state['flags']['resume_role_agents_rehydrated'] = True
    run_state['flags']['crew_rehydration_report_written'] = True
    if not memory_complete:
        run_state['flags']['resume_state_ambiguous'] = True

def _stable_resume_launcher_contract(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return {'event': 'heartbeat_or_manual_resume_requested', 'wake_sources': ['heartbeat', 'manual_resume'], 'resume_action': 'load_resume_state', 'role_liveness_action': 'rehydrate_role_agents', 'router_reentry_required_on_every_wake': True, 'heartbeat_and_manual_resume_share_path': True, 'self_keepalive_allowed': False, 'diagnostic_work_chain_status_only': True, 'controller_only': True, 'sealed_body_reads_allowed': False}

def _write_initial_continuation_binding(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    scheduled_requested = router._scheduled_continuation_requested(answers)
    binding = {'schema_version': 'flowpilot.continuation_binding.v1', 'run_id': run_state['run_id'], 'mode': 'scheduled_heartbeat' if scheduled_requested else 'manual_resume', 'scheduled_continuation_requested': scheduled_requested, 'route_heartbeat_interval_minutes': 1 if scheduled_requested else 0, 'heartbeat_active': False, 'host_automation_id': None, 'host_automation_verified': False, 'stable_launcher': router._stable_resume_launcher_contract(), 'source_paths': {'startup_answers': project_relative(project_root, run_root / 'startup_answers.json'), 'router_state': project_relative(project_root, router.run_state_path(run_root))}, 'updated_at': utc_now()}
    write_json(router._continuation_binding_path(run_root), binding)
    router._write_continuation_quarantine(project_root, run_root, run_state)

def _host_heartbeat_binding_ready(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    binding = read_json_if_exists(router._continuation_binding_path(run_root))
    return binding.get('run_id') == run_state.get('run_id') and binding.get('mode') == 'scheduled_heartbeat' and (binding.get('scheduled_continuation_requested') is True) and (binding.get('heartbeat_active') is True) and (binding.get('route_heartbeat_interval_minutes') == 1) and bool(binding.get('host_automation_id')) and (binding.get('host_automation_verified') is True) and router._continuation_has_host_bound_automation_receipt(binding, str(run_state.get('run_id') or ''))

def _defect_ledger_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = run_root / 'defects' / 'defect_ledger.json'
    status: dict[str, Any] = {'present': path.exists(), 'path': project_relative(project_root, path) if path.exists() else None, 'required_for_current_run': False, 'absence_is_pass_claim': False, 'blocker_open_count': 0, 'fixed_pending_recheck_count': 0, 'closed_defect_missing_recheck_count': 0, 'issue_count': 0, 'issues': [], 'clean': True}
    if not path.exists():
        return status
    ledger = read_json(path)
    issues: list[str] = []
    if ledger.get('schema_version') != 'flowpilot.defect_ledger.v1':
        issues.append('schema_version mismatch')
    counts = ledger.get('counts') if isinstance(ledger.get('counts'), dict) else {}
    defects = ledger.get('defects') if isinstance(ledger.get('defects'), list) else []
    count_blocker_open = int(counts.get('blocker_open', 0) or 0)
    count_fixed_pending = int(counts.get('fixed_pending_recheck', 0) or 0)
    scan_blocker_open = 0
    scan_fixed_pending = 0
    closed_missing_recheck = 0
    for defect in defects:
        if not isinstance(defect, dict):
            continue
        defect_status = str(defect.get('status') or '').lower()
        severity = str(defect.get('severity') or '').lower()
        if severity == 'blocker' and defect_status in {'open', 'accepted', 'fixing'}:
            scan_blocker_open += 1
        if defect_status == 'fixed_pending_recheck':
            scan_fixed_pending += 1
        pm_triage = defect.get('pm_triage') if isinstance(defect.get('pm_triage'), dict) else {}
        recheck_role = str(pm_triage.get('recheck_role_class') or '').lower()
        if defect_status == 'closed' and recheck_role not in {'', 'none'} and (not defect.get('recheck_paths')):
            closed_missing_recheck += 1
    blocker_open = max(count_blocker_open, scan_blocker_open, 0)
    fixed_pending = max(count_fixed_pending, scan_fixed_pending, 0)
    if blocker_open:
        issues.append('blocker defects remain open')
    if fixed_pending:
        issues.append('defects are fixed but pending recheck')
    if closed_missing_recheck:
        issues.append('closed defects are missing required recheck evidence')
    status.update({'required_for_current_run': True, 'blocker_open_count': blocker_open, 'fixed_pending_recheck_count': fixed_pending, 'closed_defect_missing_recheck_count': closed_missing_recheck, 'issue_count': len(issues), 'issues': issues, 'clean': not issues})
    return status

def _role_memory_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    memory_root = run_root / 'crew_memory'
    files = sorted(memory_root.glob('*.json')) if memory_root.exists() else []
    expected_run_id = str(run_state.get('run_id') or run_root.name)
    issues: list[str] = []
    stale_paths: list[str] = []
    role_keys_seen: set[str] = set()
    historical_authority_count = 0
    for path in files:
        memory = read_json(path)
        rel_path = project_relative(project_root, path)
        if memory.get('schema_version') != 'flowpilot.role_memory.v1':
            issues.append(f'{rel_path}: schema_version mismatch')
        role_key = str(memory.get('role_key') or path.stem)
        if role_key not in CREW_ROLE_KEYS:
            issues.append(f'{rel_path}: unknown role_key')
        else:
            role_keys_seen.add(role_key)
        if str(memory.get('run_id') or '') != expected_run_id:
            stale_paths.append(rel_path)
            issues.append(f'{rel_path}: run_id does not match current run')
        identity_policy = memory.get('identity_policy') if isinstance(memory.get('identity_policy'), dict) else {}
        if identity_policy and identity_policy.get('agent_id_is_diagnostic_only') is False:
            historical_authority_count += 1
            issues.append(f'{rel_path}: agent_id is not diagnostic-only')
        last_rehydration = memory.get('last_rehydration') if isinstance(memory.get('last_rehydration'), dict) else {}
        if last_rehydration.get('historical_agent_id_reused') is True:
            historical_authority_count += 1
            issues.append(f'{rel_path}: historical agent id reused')
        if memory.get('controller_decision_authority') is True or memory.get('role_memory_used_for_completion_authority') is True:
            historical_authority_count += 1
            issues.append(f'{rel_path}: role memory claims completion authority')
    missing_roles = [role for role in CREW_ROLE_KEYS if files and role not in role_keys_seen]
    return {'present': bool(files), 'path': project_relative(project_root, memory_root) if memory_root.exists() else None, 'required_for_current_run': bool(files), 'absence_is_pass_claim': False, 'file_count': len(files), 'role_count': len(role_keys_seen), 'missing_role_keys': missing_roles, 'stale_role_memory_paths': stale_paths, 'historical_agent_authority_count': historical_authority_count, 'issue_count': len(issues), 'issues': issues, 'clean': not issues}

def _continuation_quarantine_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = router._continuation_quarantine_path(run_root)
    status: dict[str, Any] = {'present': path.exists(), 'path': project_relative(project_root, path) if path.exists() else None, 'required_for_current_run': path.exists(), 'absence_is_pass_claim': False, 'current_pointer_matches_run': None, 'prior_run_files_are_evidence_by_default': None, 'old_agent_ids_are_current_authority': None, 'old_assets_are_current_evidence_by_default': None, 'old_agent_id_count': 0, 'old_asset_count': 0, 'issue_count': 0, 'issues': [], 'clean': True}
    if not path.exists():
        return status
    record = read_json(path)
    issues = list(flowpilot_runtime_closure.validate_continuation_quarantine_record(record))
    old_agent_ids = record.get('old_agent_ids') if isinstance(record.get('old_agent_ids'), list) else []
    old_assets = record.get('old_assets') if isinstance(record.get('old_assets'), list) else []
    imported_authority_count = 0
    for item in old_agent_ids:
        if isinstance(item, dict) and item.get('current_authority') is True:
            imported_authority_count += 1
    for item in old_assets:
        if isinstance(item, dict) and (item.get('current_evidence') is True or item.get('current_authority') is True):
            imported_authority_count += 1
    if imported_authority_count:
        issues.append('imported old artifacts still claim current authority')
    if record.get('current_pointer_matches_run') is False:
        issues.append('current pointer does not match run')
    status.update({'current_pointer_matches_run': record.get('current_pointer_matches_run'), 'prior_run_files_are_evidence_by_default': record.get('prior_run_files_are_evidence_by_default'), 'old_agent_ids_are_current_authority': record.get('old_agent_ids_are_current_authority'), 'old_assets_are_current_evidence_by_default': record.get('old_assets_are_current_evidence_by_default'), 'old_agent_id_count': len(old_agent_ids), 'old_asset_count': len(old_assets), 'imported_artifact_authority_count': imported_authority_count, 'issue_count': len(issues), 'issues': issues, 'clean': not issues})
    return status

def _terminal_closure_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    defect_status = router._defect_ledger_reconciliation_status(project_root, run_root)
    role_memory_status = router._role_memory_reconciliation_status(project_root, run_root, run_state)
    quarantine_status = router._continuation_quarantine_reconciliation_status(project_root, run_root)
    families = {'defect_ledger': defect_status, 'role_memory': role_memory_status, 'continuation_quarantine': quarantine_status}
    dirty = [name for name, family_status in families.items() if not bool(family_status.get('clean'))]
    return {'schema_version': 'flowpilot.terminal_closure_reconciliation.v1', 'clean': not dirty, 'dirty_families': dirty, 'defect_ledger': defect_status, 'role_memory': role_memory_status, 'continuation_quarantine': quarantine_status}

def _closure_reconciliation_blocker_message(router: ModuleType, status: dict[str, Any]) -> str:
    _bind_router(router)
    dirty = status.get('dirty_families') if isinstance(status.get('dirty_families'), list) else []
    if not dirty:
        return 'terminal closure reconciliation is dirty'
    details = []
    for family in dirty:
        family_status = status.get(str(family)) if isinstance(status.get(str(family)), dict) else {}
        issues = family_status.get('issues') if isinstance(family_status.get('issues'), list) else []
        first_issue = str(issues[0]) if issues else 'dirty'
        details.append(f'{family}: {first_issue}')
    return '; '.join(details)

def _closure_reconciliation_entries(router: ModuleType, project_root: Path, status: dict[str, Any], *, route_version: int) -> list[dict[str, Any]]:
    _bind_router(router)
    entries: list[dict[str, Any]] = []
    for family in ('defect_ledger', 'role_memory', 'continuation_quarantine'):
        family_status = status.get(family) if isinstance(status.get(family), dict) else {}
        path = family_status.get('path')
        entries.append({'entry_id': f'closure_reconciliation:{family}', 'route_version': route_version, 'gate_family': 'terminal_closure_reconciliation', 'required_approver': 'project_manager', 'status': 'approved' if family_status.get('clean') and family_status.get('present') else 'not_present' if family_status.get('clean') else 'blocked', 'source_of_truth_paths': [path] if isinstance(path, str) and path else [], 'evidence_paths': [path] if isinstance(path, str) and path else [], 'reconciliation': family_status})
    return entries

def _current_closure_state_clean(router: ModuleType, project_root: Path, run_root: Path) -> bool:
    _bind_router(router)
    evidence = read_json_if_exists(run_root / 'evidence' / 'evidence_ledger.json')
    generated = read_json_if_exists(run_root / 'generated_resource_ledger.json')
    final_ledger = read_json_if_exists(run_root / 'final_route_wide_gate_ledger.json')
    terminal = read_json_if_exists(run_root / 'reviews' / 'terminal_backward_replay.json')
    task_projection = read_json_if_exists(_task_completion_projection_path(run_root))
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    route_id = str(frontier.get('active_route_id') or 'route-001')
    mutations = read_json_if_exists(run_root / 'routes' / route_id / 'mutations.json')
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    self_interrogation_status = _self_interrogation_status(project_root, run_root)
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, {})
    return evidence.get('unresolved_count') == 0 and evidence.get('stale_count') == 0 and (generated.get('pending_resource_count') == 0) and (generated.get('unresolved_resource_count') == 0) and (final_ledger.get('completion_allowed') is True) and (final_ledger.get('counts', {}).get('unresolved_count') == 0) and (terminal.get('passed') is True) and (task_projection.get('task_status') == 'ready_for_pm_terminal_closure') and pm_suggestion_status['clean'] and self_interrogation_status['clean'] and closure_reconciliation['clean'] and (not router._route_mutation_completion_issues(frontier, mutations))

def _invalidate_route_completion_if_dirty_before_closure(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('final_backward_replay_passed'):
        return
    if flags.get('pm_closure_approved'):
        return
    if router._current_closure_state_clean(project_root, run_root):
        return
    _reset_flags(run_state, ROUTE_COMPLETION_FLAGS)
    append_history(run_state, 'route_completion_cycle_invalidated_by_dirty_closure_state', {'reason': 'completion ledgers changed after terminal backward replay and before PM closure', 'restart_from': 'pm.evidence_quality_package'})

def _startup_fact_checks(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    required_answer_ids = {item['id'] for item in STARTUP_QUESTIONS}
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json')
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json')
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    role_slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    role_keys = {slot.get('role_key') for slot in role_slots if isinstance(slot, dict)}
    live_role_slots_current = role_keys == set(CREW_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'live_agent_started' and isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) and (slot.get('model_policy') == BACKGROUND_ROLE_MODEL_POLICY) and (slot.get('reasoning_effort_policy') == BACKGROUND_ROLE_REASONING_EFFORT_POLICY) and (slot.get('spawn_result') == ROLE_AGENT_SPAWN_RESULT) and (slot.get('spawned_for_run_id') == run_state.get('run_id')) and (slot.get('spawned_after_startup_answers') is True) for slot in role_slots))
    single_agent_slots_current = role_keys == set(CREW_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'single_agent_continuity_authorized' and (slot.get('agent_id') is None) and (slot.get('fallback_authorized_by_startup_answer') is True) for slot in role_slots))
    indexed_runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    scheduled_requested = router._scheduled_continuation_requested(answers)
    old_control_paths = [project_root / '.flowpilot' / 'state.json', project_root / '.flowpilot' / 'capabilities.json', project_root / '.flowpilot' / 'execution_frontier.json', project_root / '.flowpilot' / 'routes']
    boundary_context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    return {'controller_boundary_confirmed': boundary_context is not None or router._legacy_pm_reset_boundary_confirmed(run_state), 'startup_intake_record_current': startup_intake_context is not None, 'startup_intake_receipt_envelope_hash_current': bool(startup_intake_context and startup_intake_context.get('receipt_envelope_body_hash_current')), 'reviewer_live_review_uses_startup_intake_record': bool(startup_intake_context and startup_intake_context.get('reviewer_must_not_use_chat_history')), 'startup_answers_complete': required_answer_ids.issubset({key for key, value in answers.items() if value}), 'current_pointer_matches_run': current.get('current_run_id') == run_state.get('run_id') and current.get('current_run_root') == run_state.get('run_root'), 'index_points_to_run': index.get('current_run_id') == run_state.get('run_id') and any((isinstance(item, dict) and item.get('run_id') == run_state.get('run_id') for item in indexed_runs)), 'crew_slots_current': role_keys == set(CREW_ROLE_KEYS), 'live_background_agents_current_if_allowed': live_role_slots_current if answers.get('background_agents') == 'allow' else True, 'single_agent_continuity_current_if_selected': single_agent_slots_current if answers.get('background_agents') == 'single-agent' else True, 'continuation_mode_recorded': bool(answers.get('scheduled_continuation')), 'continuation_binding_current': continuation_binding.get('run_id') == run_state.get('run_id') and continuation_binding.get('schema_version') == 'flowpilot.continuation_binding.v1', 'scheduled_heartbeat_verified_if_requested': continuation_binding.get('heartbeat_active') is True and continuation_binding.get('route_heartbeat_interval_minutes') == 1 and bool(continuation_binding.get('host_automation_id')) and (continuation_binding.get('host_automation_verified') is True) if scheduled_requested else continuation_binding.get('mode') == 'manual_resume', 'display_surface_recorded': bool(answers.get('display_surface')), 'old_state_quarantined': not any((path.exists() for path in old_control_paths))}

def _startup_intake_record_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    record_path = run_root / 'startup_intake' / 'startup_intake_record.json'
    if not record_path.exists():
        return None
    record = read_json_if_exists(record_path)
    if record.get('schema_version') != STARTUP_INTAKE_RECORD_SCHEMA:
        return None
    if record.get('run_id') != run_state.get('run_id'):
        return None
    if record.get('status') != 'confirmed':
        return None
    if record.get('controller_may_read_body') is not False or record.get('body_text_included') is not False:
        return None
    try:
        body_path = router._resolve_existing_project_file(project_root, record.get('body_path'), 'startup intake record body')
        receipt_path = router._resolve_existing_project_file(project_root, record.get('receipt_path'), 'startup intake record receipt')
        envelope_path = router._resolve_existing_project_file(project_root, record.get('envelope_path'), 'startup intake record envelope')
        result_path = router._resolve_existing_project_file(project_root, record.get('result_path'), 'startup intake record result')
    except RouterError:
        return None
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != record.get('body_hash'):
        return None
    receipt = read_json_if_exists(receipt_path)
    envelope = read_json_if_exists(envelope_path)
    result = read_json_if_exists(result_path)
    receipt_envelope_body_hash_current = receipt.get('schema_version') == STARTUP_INTAKE_RECEIPT_SCHEMA and envelope.get('schema_version') == STARTUP_INTAKE_ENVELOPE_SCHEMA and (result.get('schema_version') == STARTUP_INTAKE_RESULT_SCHEMA) and (receipt.get('body_hash') == body_hash) and (envelope.get('body_hash') == body_hash) and (result.get('body_hash') == body_hash) and (receipt.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (envelope.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (result.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (receipt.get('headless') is False) and (envelope.get('headless') is False) and (result.get('headless') is False) and (receipt.get('formal_startup_allowed') is True) and (envelope.get('formal_startup_allowed') is True) and (result.get('formal_startup_allowed') is True) and (envelope.get('controller_may_read_body') is False) and (result.get('controller_may_read_body') is False) and (envelope.get('body_text_included') is False) and (result.get('body_text_included') is False)
    return {'record_path': record_path, 'record': record, 'result_path': result_path, 'receipt_path': receipt_path, 'envelope_path': envelope_path, 'body_path': body_path, 'body_hash': body_hash, 'receipt_envelope_body_hash_current': receipt_envelope_body_hash_current, 'reviewer_must_not_use_chat_history': record.get('reviewer_must_not_use_chat_history') is True}

def _controller_boundary_confirmation_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'startup' / 'controller_boundary_confirmation.json'

def _run_manifest_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    manifest_path = run_root / 'runtime_kit' / 'manifest.json'
    if manifest_path.exists():
        return manifest_path
    return runtime_kit_source() / 'manifest.json'

def _controller_boundary_sources(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    manifest_path = router._run_manifest_path(run_root)
    manifest = read_json(manifest_path)
    if manifest.get('schema_version') != PROMPT_MANIFEST_SCHEMA:
        raise RouterError('invalid prompt manifest schema')
    controller_core = manifest_card(manifest, 'controller.core')
    card_path = manifest_path.parent / str(controller_core['path'])
    if not card_path.exists():
        raise RouterError('controller.core card path is missing')
    policy = manifest.get('controller_policy')
    if not isinstance(policy, dict):
        raise RouterError('prompt manifest controller_policy must be an object')
    return {'manifest': manifest, 'manifest_path': manifest_path, 'manifest_hash': packet_runtime.sha256_file(manifest_path), 'controller_core_card': controller_core, 'controller_core_path': card_path, 'controller_core_hash': packet_runtime.sha256_file(card_path), 'controller_policy': policy, 'controller_policy_hash': _json_sha256(policy)}

def _controller_boundary_constraints(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return role_output_runtime.controller_boundary_constraints()

def _legacy_pm_reset_boundary_confirmed(router: ModuleType, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    return bool(flags.get('controller_role_confirmed') and flags.get('pm_controller_reset_card_delivered') and flags.get('pm_controller_reset_decision_returned'))

def _controller_boundary_confirmation_body(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del run_root
    try:
        return role_output_runtime.build_controller_boundary_confirmation_body(project_root, run_id=str(run_state['run_id']))
    except role_output_runtime.RoleOutputRuntimeError as exc:
        raise RouterError(str(exc)) from exc

def _controller_boundary_runtime_evidence_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, confirmation_path: Path, confirmation_hash: str) -> dict[str, Any] | None:
    _bind_router(router)
    del run_root
    try:
        envelope = role_output_runtime.runtime_envelope_for_body(project_root, output_type=CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, body_path=confirmation_path, body_hash=confirmation_hash, run_id=str(run_state.get('run_id') or '') or None)
        if not isinstance(envelope, dict):
            return None
        if envelope.get('output_contract_id') != CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID:
            return None
        if envelope.get('from_role') != 'controller':
            return None
        receipt = role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
    except role_output_runtime.RoleOutputRuntimeError:
        return None
    if receipt.get('role') != 'controller':
        return None
    if receipt.get('output_type') != CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE:
        return None
    return {'envelope': envelope, 'receipt': receipt}

def _write_controller_boundary_confirmation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, controller_agent_id: str | None=None, action_id: str | None=None, source_action_id: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if not run_state.get('flags', {}).get('controller_core_loaded'):
        raise RouterError('controller core must be loaded before Controller boundary confirmation')
    confirmation_path = router._controller_boundary_confirmation_path(run_root)
    try:
        envelope = role_output_runtime.submit_controller_boundary_confirmation(project_root, agent_id=controller_agent_id or CONTROLLER_RUNTIME_HELPER_AGENT_ID, run_id=str(run_state['run_id']), action_id=action_id, source_action_id=source_action_id, output_path=confirmation_path)
    except role_output_runtime.RoleOutputRuntimeError as exc:
        raise RouterError(str(exc)) from exc
    runtime_receipt = role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
    confirmation = read_json(confirmation_path)
    confirmation_hash = packet_runtime.sha256_file(confirmation_path)
    return {'path': project_relative(project_root, confirmation_path), 'sha256': confirmation_hash, 'controller_core_path': confirmation['controller_core_path'], 'controller_core_sha256': confirmation['controller_core_sha256'], 'controller_policy_sha256': confirmation['controller_policy_sha256'], 'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'role_output_envelope': envelope, 'role_output_runtime_receipt_path': runtime_receipt.get('body_path') and (envelope.get('runtime_receipt_ref') or {}).get('path'), 'role_output_runtime_receipt_hash': runtime_receipt.get('body_hash') and (envelope.get('runtime_receipt_ref') or {}).get('hash')}

def _record_controller_boundary_confirmation_from_core_load(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any] | None, *, source: str) -> dict[str, Any]:
    _bind_router(router)
    if not run_state.get('flags', {}).get('controller_core_loaded'):
        raise RouterError('Controller boundary confirmation requires loaded controller.core')
    action_id = str(action.get('controller_action_id') or action.get('action_id') or '').strip()
    source_action_id = str(action.get('action_id') or action_id or 'load_controller_core')
    context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        confirmation = router._write_controller_boundary_confirmation(project_root, run_root, run_state, controller_agent_id=CONTROLLER_RUNTIME_HELPER_AGENT_ID, action_id=action_id or None, source_action_id=source_action_id)
    else:
        confirmation = {'path': project_relative(project_root, context['path']), 'sha256': context['sha256'], 'controller_core_path': context['confirmation'].get('controller_core_path'), 'controller_core_sha256': context['confirmation'].get('controller_core_sha256'), 'controller_policy_sha256': context['confirmation'].get('controller_policy_sha256'), 'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'role_output_envelope': context.get('role_output_envelope'), 'role_output_runtime_receipt_path': context.get('role_output_envelope', {}).get('runtime_receipt_ref', {}).get('path') if isinstance(context.get('role_output_envelope'), dict) else None, 'role_output_runtime_receipt_hash': context.get('role_output_envelope', {}).get('runtime_receipt_ref', {}).get('hash') if isinstance(context.get('role_output_envelope'), dict) else None}
    pending_action = dict(action)
    pending_action.setdefault('action_type', 'load_controller_core')
    pending_action.setdefault('postcondition', 'controller_role_confirmed')
    if action_id:
        pending_action.setdefault('controller_action_id', action_id)
        pending_action.setdefault('controller_receipt_path', project_relative(project_root, _controller_receipt_path(run_root, action_id)))
    applied = _sync_controller_boundary_confirmation_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload or {'controller_action_completed': True, 'controller_boundary_confirmation_source': 'load_controller_core'}, source=source)
    if not applied.get('applied'):
        raise RouterError(f"Controller boundary confirmation was not reconciled during core load: {applied.get('reason')}")
    applied['controller_boundary_confirmation'] = confirmation
    applied['controller_boundary_confirmation_owned_by'] = 'load_controller_core'
    return applied

def _controller_boundary_confirmation_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    confirmation_path = router._controller_boundary_confirmation_path(run_root)
    if not confirmation_path.exists():
        return None
    confirmation = read_json_if_exists(confirmation_path)
    if confirmation.get('schema_version') != CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA:
        return None
    if confirmation.get('run_id') != run_state.get('run_id'):
        return None
    if confirmation.get('event') != 'controller_role_confirmed_from_router_core':
        return None
    if confirmation.get('confirmed_by_role') != 'controller':
        return None
    if confirmation.get('router_owned_confirmation') is not True:
        return None
    constraints = confirmation.get('boundary_constraints')
    if constraints != router._controller_boundary_constraints():
        return None
    sources = router._controller_boundary_sources(run_root)
    if confirmation.get('controller_core_sha256') != sources['controller_core_hash']:
        return None
    if confirmation.get('manifest_sha256') != sources['manifest_hash']:
        return None
    if confirmation.get('controller_policy_sha256') != sources['controller_policy_hash']:
        return None
    if confirmation.get('sealed_body_reads_allowed') is not False:
        return None
    confirmation_hash = packet_runtime.sha256_file(confirmation_path)
    runtime_context = router._controller_boundary_runtime_evidence_context(project_root, run_root, run_state, confirmation_path=confirmation_path, confirmation_hash=confirmation_hash)
    if runtime_context is None:
        return None
    return {'path': confirmation_path, 'sha256': confirmation_hash, 'confirmation': confirmation, 'role_output_envelope': runtime_context['envelope'], 'role_output_runtime_receipt': runtime_context['receipt']}

def _role_slots_have_host_spawn_receipts(router: ModuleType, role_slots: list[dict[str, Any]], run_id: str) -> bool:
    _bind_router(router)
    for slot in role_slots:
        receipt = slot.get('host_spawn_receipt') if isinstance(slot, dict) else None
        if not isinstance(receipt, dict):
            return False
        if receipt.get('source_kind') != 'host_receipt':
            return False
        if receipt.get('spawned_for_run_id') != run_id:
            return False
        if receipt.get('role_key') != slot.get('role_key'):
            return False
        if receipt.get('agent_id') != slot.get('agent_id'):
            return False
    return bool(role_slots)

def _continuation_has_host_bound_automation_receipt(router: ModuleType, continuation_binding: dict[str, Any], run_id: str) -> bool:
    _bind_router(router)
    proof = continuation_binding.get('host_automation_proof')
    if not isinstance(proof, dict):
        return False
    return proof.get('source_kind') == 'host_receipt' and proof.get('run_id') == run_id and (proof.get('host_automation_id') == continuation_binding.get('host_automation_id')) and (proof.get('route_heartbeat_interval_minutes') == 1) and (proof.get('heartbeat_bound_to_current_run') is True)

def _startup_external_fact_requirements(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    role_slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    requirements: list[dict[str, Any]] = []
    if answers.get('background_agents') == 'allow' and (not router._role_slots_have_host_spawn_receipts(role_slots, str(run_state.get('run_id') or ''))):
        requirements.append({'id': 'live_agent_spawn_freshness', 'reason': 'Router validates role-slot shape, run ids, and requested background role intelligence policy, but host spawn freshness and actual model selection need a receipt or reviewer check.', 'self_attested_payload_fields': ['role_agents[].model_policy', 'role_agents[].reasoning_effort_policy', 'role_agents[].spawn_result', 'role_agents[].spawned_after_startup_answers'], 'reviewer_direct_check_required': True})
    if router._scheduled_continuation_requested(answers) and (not router._continuation_has_host_bound_automation_receipt(continuation_binding, str(run_state.get('run_id') or ''))):
        requirements.append({'id': 'heartbeat_host_automation_current_run_binding', 'reason': 'Router validates the heartbeat binding fields, but host_automation_verified=true alone is an AI/host payload claim unless backed by a host receipt.', 'self_attested_payload_fields': ['host_automation_verified', 'host_automation_id'], 'reviewer_direct_check_required': True})
    if answers.get('display_surface') == 'cockpit':
        requirements.append({'id': 'cockpit_or_display_fallback_reality', 'reason': 'Router can record selected display mode and chat fallback, but live Cockpit availability or fallback necessity requires direct review when requested.', 'self_attested_payload_fields': ['display_surface'], 'reviewer_direct_check_required': True})
    return requirements

def _startup_fact_review_ownership(router: ModuleType, computed_checks: dict[str, bool], external_requirements: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    reviewer_ids = {str(item['id']) for item in external_requirements if item.get('id')}
    router_owned = sorted(computed_checks)
    reviewer_owned = sorted(reviewer_ids)
    pm_decision_owned = ['startup_user_answer_authenticity']
    covered = set(router_owned) | set(reviewer_owned) | set(pm_decision_owned)
    known = set(computed_checks) | reviewer_ids | set(pm_decision_owned)
    unowned = sorted(known - covered)
    return {'router_owned_mechanical_checks': router_owned, 'reviewer_owned_external_fact_ids': reviewer_owned, 'pm_decision_owned_unreviewable_fact_ids': pm_decision_owned, 'unowned_fact_ids': unowned, 'all_required_facts_have_owner': not unowned}

def _write_startup_mechanical_audit(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], computed_checks: dict[str, bool]) -> dict[str, Any]:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    proof_path = _router_owned_check_proof_path(audit_path)
    evidence_paths = [run_root / 'startup_answers.json', project_root / '.flowpilot' / 'current.json', project_root / '.flowpilot' / 'index.json', run_root / 'crew_ledger.json', router._continuation_binding_path(run_root), router.run_state_path(run_root)]
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        evidence_paths.extend([startup_intake_context['record_path'], startup_intake_context['result_path'], startup_intake_context['receipt_path'], startup_intake_context['envelope_path'], startup_intake_context['body_path']])
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        evidence_paths.append(boundary_path)
    external_requirements = router._startup_external_fact_requirements(run_root, run_state)
    review_ownership = router._startup_fact_review_ownership(computed_checks, external_requirements)
    audit = {'schema_version': STARTUP_MECHANICAL_AUDIT_SCHEMA, 'run_id': run_state['run_id'], 'check_owner': 'flowpilot_router', 'mechanical_checks': computed_checks, 'mechanical_checks_passed': all(computed_checks.values()), 'router_replacement_scope': 'mechanical_only', 'self_attested_ai_claims_accepted_as_proof': False, 'fact_review_ownership': review_ownership, 'reviewer_required_external_facts': external_requirements, 'router_owned_check_proof_path': project_relative(project_root, proof_path), 'source_paths': [_evidence_path_record(project_root, path) for path in evidence_paths], 'written_at': utc_now()}
    if not review_ownership['all_required_facts_have_owner']:
        raise RouterError('startup fact ownership map left unowned requirements')
    write_json(audit_path, audit)
    proof_record = _write_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path, source_kind='router_computed', evidence_paths=evidence_paths)
    _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    audit['router_owned_check_proof'] = {'path': proof_record['proof_path'], 'schema_version': ROUTER_OWNED_CHECK_PROOF_SCHEMA}
    return audit

def _startup_mechanical_audit_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    if not audit_path.exists():
        return None
    audit = read_json_if_exists(audit_path)
    if audit.get('schema_version') != STARTUP_MECHANICAL_AUDIT_SCHEMA:
        return None
    if audit.get('run_id') != run_state.get('run_id'):
        return None
    try:
        proof = _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    except RouterError:
        return None
    proof_path = _router_owned_check_proof_path(audit_path)
    return {'audit': audit, 'audit_path': audit_path, 'audit_hash': packet_runtime.sha256_file(audit_path), 'proof': proof, 'proof_path': proof_path, 'proof_hash': packet_runtime.sha256_file(proof_path) if proof_path.exists() else None}

def _startup_mechanical_audit_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise RouterError('startup mechanical audit must be written before reviewer startup fact card delivery')
    display_path = run_root / 'display' / 'display_surface.json'
    if not display_path.exists():
        raise RouterError('startup display-surface status must be written before reviewer startup fact card delivery')
    return {'startup_mechanical_audit_path': project_relative(project_root, context['audit_path']), 'startup_mechanical_audit_hash': context['audit_hash'], 'router_owned_check_proof_path': project_relative(project_root, context['proof_path']), 'router_owned_check_proof_hash': context['proof_hash'], 'startup_intake_record_path': router._optional_source_path(project_root, run_root / 'startup_intake' / 'startup_intake_record.json'), 'startup_display_surface_path': project_relative(project_root, display_path), 'startup_display_surface_hash': packet_runtime.sha256_file(display_path), 'reviewer_has_direct_display_evidence': True, 'router_computable_checks_already_enforced': True, 'reviewer_should_not_reprove_router_computable_checks': True, 'reviewer_required_external_facts': context['audit'].get('reviewer_required_external_facts') or [], 'router_replacement_scope': 'mechanical_only'}

def _validate_startup_external_fact_review(router: ModuleType, payload: dict[str, Any], requirements: list[dict[str, Any]], *, startup_mechanical_audit_hash: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if not requirements:
        return {'reviewed_by_role': 'human_like_reviewer', 'reviewer_required_external_fact_count': 0, 'reviewer_checked_requirement_ids': [], 'self_attested_ai_claims_accepted_as_proof': False}
    review = payload.get('external_fact_review')
    if not isinstance(review, dict):
        raise RouterError('startup fact report requires external_fact_review for non-router-checkable facts')
    if review.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('external_fact_review must be reviewed_by_role=human_like_reviewer')
    if startup_mechanical_audit_hash and review.get('router_mechanical_audit_hash') is not None and (review.get('router_mechanical_audit_hash') != startup_mechanical_audit_hash):
        raise RouterError('external_fact_review must reference the current startup mechanical audit hash')
    if review.get('self_attested_ai_claims_accepted_as_proof') is not False:
        raise RouterError('external_fact_review cannot accept self-attested AI claims as proof')
    checked_ids = review.get('reviewer_checked_requirement_ids')
    if not isinstance(checked_ids, list):
        raise RouterError('external_fact_review requires reviewer_checked_requirement_ids list')
    checked = {str(item) for item in checked_ids}
    required = {str(item['id']) for item in requirements if item.get('id')}
    missing = sorted(required - checked)
    if missing:
        raise RouterError(f"external_fact_review missing required checks: {', '.join(missing)}")
    direct_paths = review.get('direct_evidence_paths_checked')
    if not isinstance(direct_paths, list) or not direct_paths:
        raise RouterError('external_fact_review requires direct_evidence_paths_checked')
    return {'reviewed_by_role': 'human_like_reviewer', 'reviewer_required_external_fact_count': len(requirements), 'reviewer_checked_requirement_ids': sorted(checked), 'direct_evidence_paths_checked': direct_paths, 'self_attested_ai_claims_accepted_as_proof': False, 'notes': review.get('notes')}

def _write_startup_fact_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    canonical_report_path = run_root / 'startup' / 'startup_fact_report.json'
    envelope = payload.get('_role_output_envelope')
    if isinstance(envelope, dict) and envelope.get('body_path'):
        source_path = resolve_project_path(project_root, str(envelope['body_path']))
        if source_path.resolve() == canonical_report_path.resolve():
            raise RouterError('startup fact source report_path must not be the router canonical startup_fact_report.json')
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('startup fact report must be reviewed_by_role=human_like_reviewer')
    computed_checks = router._startup_fact_checks(project_root, run_root, run_state)
    claimed_checks = payload.get('checks') if isinstance(payload.get('checks'), dict) else {}
    false_claims = [name for name, value in claimed_checks.items() if value is not True]
    passed = payload.get('passed') is True
    if passed and false_claims:
        raise RouterError(f"startup fact report contains failed checks: {', '.join(sorted(false_claims))}")
    blockers = [name for name, ok in computed_checks.items() if not ok]
    if passed and blockers:
        raise RouterError(f"startup facts are not clean: {', '.join(sorted(blockers))}")
    mechanical_context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if mechanical_context is None:
        raise RouterError('startup mechanical audit must be written before reviewer startup fact report')
    mechanical_audit = mechanical_context['audit']
    if mechanical_audit.get('mechanical_checks') != computed_checks:
        raise RouterError('startup mechanical audit is stale; rewrite it before reviewer startup fact report')
    external_fact_review = router._validate_startup_external_fact_review(payload, mechanical_audit['reviewer_required_external_facts'], startup_mechanical_audit_hash=mechanical_context['audit_hash'])
    write_json(canonical_report_path, {'schema_version': 'flowpilot.startup_fact_report.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'passed': passed, 'status': 'pass' if passed else 'findings', 'checks': computed_checks, 'reviewer_claimed_checks': claimed_checks, 'reviewer_reported_blockers': payload.get('blockers') if isinstance(payload.get('blockers'), list) else false_claims or blockers, 'startup_mechanical_audit_path': project_relative(project_root, mechanical_context['audit_path']), 'startup_mechanical_audit_hash': mechanical_context['audit_hash'], 'router_owned_check_proof_path': project_relative(project_root, mechanical_context['proof_path']), 'router_owned_check_proof_hash': mechanical_context['proof_hash'], 'reviewer_required_external_facts': mechanical_audit['reviewer_required_external_facts'], 'external_fact_review': external_fact_review, 'requires_pm_startup_decision': not passed, 'reviewer_directly_blocks_route': False, 'reported_at': utc_now(), **_role_output_envelope_record(payload)})

def _write_startup_activation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('approved_by_role') != 'project_manager':
        raise RouterError('PM startup activation requires approved_by_role=project_manager')
    if payload.get('decision') != 'approved':
        raise RouterError('PM startup activation requires decision=approved')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    fact_report_path = run_root / 'startup' / 'startup_fact_report.json'
    if not fact_report_path.exists():
        raise RouterError('PM startup activation requires reviewer startup_fact_report.json')
    clean_report = fact_report.get('passed') is True and fact_report.get('status') == 'pass'
    approval_basis = 'clean_reviewer_fact_report'
    findings_decision: dict[str, Any] | None = None
    if not clean_report:
        if fact_report.get('status') != 'findings' or fact_report.get('requires_pm_startup_decision') is not True:
            raise RouterError('PM startup activation requires a passing reviewer startup fact report or PM findings decision')
        if payload.get('accepts_startup_findings_with_reason') is not True:
            raise RouterError('PM startup activation from reviewer findings requires accepts_startup_findings_with_reason=true')
        reason = str(payload.get('startup_findings_decision_reason') or '').strip()
        if not reason:
            raise RouterError('PM startup activation from reviewer findings requires startup_findings_decision_reason')
        reviewed_report = payload.get('reviewed_report_path') or project_relative(project_root, fact_report_path)
        if resolve_project_path(project_root, str(reviewed_report)).resolve() != fact_report_path.resolve():
            raise RouterError('PM startup activation reviewed_report_path must reference startup_fact_report.json')
        decision_kind = str(payload.get('startup_findings_decision') or 'waived_with_reason')
        if decision_kind not in {'waived_with_reason', 'unreviewable_requirement_demoted', 'accepted_with_documented_risk'}:
            raise RouterError('PM startup activation startup_findings_decision is invalid')
        approval_basis = 'pm_file_backed_findings_decision'
        findings_decision = {'startup_findings_decision': decision_kind, 'startup_findings_decision_reason': reason, 'reviewed_report_path': project_relative(project_root, fact_report_path), 'reviewed_report_hash': packet_runtime.sha256_file(fact_report_path), 'reviewer_findings_accepted_by_pm': True, 'demoted_unreviewable_requirement_ids': payload.get('demoted_unreviewable_requirement_ids') if isinstance(payload.get('demoted_unreviewable_requirement_ids'), list) else []}
    answers = router._startup_answers_from_run(run_root)
    activation = {'schema_version': 'flowpilot.startup_activation.v1', 'run_id': run_state['run_id'], 'approved_by_role': 'project_manager', 'decision': 'approved', 'background_agents': answers.get('background_agents'), 'scheduled_continuation': answers.get('scheduled_continuation'), 'display_surface': answers.get('display_surface'), 'fact_report_path': project_relative(project_root, fact_report_path), 'approval_basis': approval_basis, 'approved_at': utc_now(), **_role_output_envelope_record(payload)}
    if findings_decision is not None:
        activation['pm_findings_decision'] = findings_decision
    write_json(run_root / 'startup' / 'startup_activation.json', activation)

def _write_startup_repair_request(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('decided_by_role') != 'project_manager':
        raise RouterError('startup repair request requires decided_by_role=project_manager')
    if payload.get('decision') not in {'startup_repair_requested', 'repair_requested'}:
        raise RouterError('startup repair request requires decision=startup_repair_requested')
    target = str(payload.get('target_role_or_system') or '').strip()
    allowed_targets = {'flowpilot_router', 'human_like_reviewer', 'project_manager', 'worker_a', 'worker_b'}
    if target not in allowed_targets:
        raise RouterError(f"startup repair request target_role_or_system must be one of: {', '.join(sorted(allowed_targets))}")
    repair_action = str(payload.get('repair_action') or '').strip()
    if not repair_action:
        raise RouterError('startup repair request requires repair_action')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    if fact_report.get('passed') is True:
        raise RouterError('startup repair request requires a non-passing reviewer startup fact report')
    current_blocked_report_path = run_root / 'startup' / 'startup_fact_report.json'
    if not current_blocked_report_path.exists():
        raise RouterError('startup repair request requires the current non-passing startup_fact_report.json')
    requested_blocked_report = payload.get('blocked_report_path') or project_relative(project_root, current_blocked_report_path)
    requested_blocked_report_path = resolve_project_path(project_root, str(requested_blocked_report))
    if requested_blocked_report_path.resolve() != current_blocked_report_path.resolve():
        raise RouterError('startup repair request blocked_report_path must be the current canonical startup_fact_report.json')
    blocked_report_hash = packet_runtime.sha256_file(current_blocked_report_path)
    envelope = payload.get('_role_output_envelope') if isinstance(payload.get('_role_output_envelope'), dict) else {}
    decision_hash = str(envelope.get('body_hash') or '')
    if not decision_hash:
        raise RouterError('startup repair request requires a file-backed PM decision hash')
    previous_request = run_state.get('startup_repair_request') if isinstance(run_state.get('startup_repair_request'), dict) else {}
    last_decision_hash = str(previous_request.get('decision_hash') or '')
    if last_decision_hash and decision_hash == last_decision_hash:
        raise RouterError('startup repair request repeats the previous PM decision; write a fresh PM decision for the current blocking report')
    startup_repair_cycle = int(run_state.get('startup_repair_cycle') or 0) + 1
    record = {'schema_version': 'flowpilot.startup_repair_request.v1', 'run_id': run_state['run_id'], 'startup_repair_cycle': startup_repair_cycle, 'decided_by_role': 'project_manager', 'decision': 'startup_repair_requested', 'repair_target_kind': payload.get('repair_target_kind') or ('system' if target == 'flowpilot_router' else 'role'), 'target_role_or_system': target, 'repair_action': repair_action, 'blocked_report_path': project_relative(project_root, current_blocked_report_path), 'blocked_report_hash': blocked_report_hash, 'decision_path': envelope.get('body_path'), 'decision_hash': decision_hash, 'resume_event': payload.get('resume_event') or 'reviewer_reports_startup_facts', 'resume_condition': payload.get('resume_condition') or 'targeted startup repair is complete and reviewer writes a fresh startup fact report', 'controller_may_invent_repair': False, 'recorded_at': utc_now(), **_role_output_envelope_record(payload)}
    cycle_path = run_root / 'startup' / f'startup_repair_request.cycle-{startup_repair_cycle:03d}.json'
    write_json(cycle_path, record)
    write_json(run_root / 'startup' / 'startup_repair_request.json', record)
    ledger_path = run_root / 'startup' / 'startup_repair_requests.json'
    ledger = read_json_if_exists(ledger_path)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    entries.append({'startup_repair_cycle': startup_repair_cycle, 'path': project_relative(project_root, cycle_path), 'blocked_report_path': record['blocked_report_path'], 'blocked_report_hash': blocked_report_hash, 'decision_path': record['decision_path'], 'decision_hash': decision_hash, 'target_role_or_system': target, 'repair_action': repair_action, 'recorded_at': record['recorded_at']})
    write_json(ledger_path, {'schema_version': 'flowpilot.startup_repair_requests.v1', 'run_id': run_state['run_id'], 'entries': entries, 'latest_cycle': startup_repair_cycle, 'updated_at': utc_now()})
    for flag in ('startup_fact_reported', 'pm_startup_activation_card_delivered', 'startup_activation_approved', 'startup_mechanical_audit_written', 'reviewer_startup_fact_check_card_delivered'):
        run_state['flags'][flag] = False
    run_state['startup_repair_cycle'] = startup_repair_cycle
    run_state['startup_repair_request'] = {'path': project_relative(project_root, run_root / 'startup' / 'startup_repair_request.json'), 'cycle_path': project_relative(project_root, cycle_path), 'ledger_path': project_relative(project_root, ledger_path), 'startup_repair_cycle': startup_repair_cycle, 'target_role_or_system': target, 'repair_action': repair_action, 'blocked_report_hash': blocked_report_hash, 'decision_hash': decision_hash, 'resume_event': record['resume_event']}

def _write_startup_protocol_dead_end(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('declared_by_role') != 'project_manager':
        raise RouterError('startup protocol dead-end requires declared_by_role=project_manager')
    if payload.get('decision') != 'protocol_dead_end':
        raise RouterError('startup protocol dead-end requires decision=protocol_dead_end')
    if payload.get('no_legal_repair_path') is not True:
        raise RouterError('startup protocol dead-end requires no_legal_repair_path=true')
    reason = str(payload.get('why_no_existing_path_applies') or '').strip()
    if not reason:
        raise RouterError('startup protocol dead-end requires why_no_existing_path_applies')
    attempted_paths = payload.get('attempted_legal_paths')
    if not isinstance(attempted_paths, list) or not attempted_paths:
        raise RouterError('startup protocol dead-end requires attempted_legal_paths')
    resume_conditions = payload.get('resume_conditions')
    if not isinstance(resume_conditions, list) or not resume_conditions:
        raise RouterError('startup protocol dead-end requires resume_conditions')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    if fact_report.get('passed') is True:
        raise RouterError('startup protocol dead-end requires a non-passing reviewer startup fact report')
    dead_end_path = run_root / 'lifecycle' / 'startup_protocol_dead_end.json'
    record = {'schema_version': 'flowpilot.startup_protocol_dead_end.v1', 'run_id': run_state['run_id'], 'declared_by_role': 'project_manager', 'decision': 'protocol_dead_end', 'dead_end_type': payload.get('dead_end_type') or 'startup_block_has_no_protocol_route', 'no_legal_repair_path': True, 'why_no_existing_path_applies': reason, 'attempted_legal_paths': attempted_paths, 'conceptual_repair_direction': payload.get('conceptual_repair_direction'), 'unsafe_to_continue_reason': payload.get('unsafe_to_continue_reason') or reason, 'blocked_report_path': payload.get('blocked_report_path') or project_relative(project_root, run_root / 'startup' / 'startup_fact_report.json'), 'effects': {'freeze_run': True, 'cancel_or_suspend_pending_mail': True, 'prevent_work_beyond_startup': True, 'heartbeat_should_stop': False, 'heartbeat_should_remain_for_resume_or_user_decision': True, **(payload.get('effects') if isinstance(payload.get('effects'), dict) else {})}, 'resume_conditions': resume_conditions, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'declared_at': utc_now(), **_role_output_envelope_record(payload)}
    write_json(dead_end_path, record)
    run_state['flags']['startup_pending_mail_suspended_after_dead_end'] = True
    _write_protocol_dead_end_lifecycle(project_root, run_root, run_state, dead_end_path=dead_end_path, reason=reason)

def _route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, trigger: str, mark_chat_displayed: bool, cockpit_open: bool=False, mark_ui_displayed: bool=False) -> dict[str, Any]:
    _bind_router(router)
    return flowpilot_user_flow_diagram.generate(project_root, write=write, trigger=trigger, cockpit_open=cockpit_open, display_surface='both' if cockpit_open else 'chat', mark_chat_displayed=mark_chat_displayed, mark_ui_displayed=mark_ui_displayed, reviewer_check=False)

def _startup_route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    _bind_router(router)
    return router._route_sign_payload(project_root, write=write, trigger='startup', mark_chat_displayed=mark_chat_displayed)

def _route_map_route_sign_payload(router: ModuleType, project_root: Path, *, write: bool, mark_chat_displayed: bool) -> dict[str, Any]:
    _bind_router(router)
    return router._route_sign_payload(project_root, write=write, trigger='key_node_change', mark_chat_displayed=mark_chat_displayed)

def _route_sign_has_canonical_route(router: ModuleType, payload: dict[str, Any]) -> bool:
    _bind_router(router)
    return payload.get('flowpilot_path_status') == 'ok' and int(payload.get('route_node_count') or 0) > 0 and (str(payload.get('route_source_kind') or 'none') != 'none')

def _display_surface_receipt_from_payload(router: ModuleType, payload: dict[str, Any], *, run_id: str, requested: str, selected_surface: str) -> dict[str, Any]:
    _bind_router(router)
    receipt = payload.get('display_surface_receipt') if isinstance(payload, dict) else None
    if receipt is None:
        return {'schema_version': DISPLAY_SURFACE_RECEIPT_SCHEMA, 'run_id': run_id, 'requested_display_surface': requested, 'actual_surface': selected_surface, 'source_kind': 'controller_user_dialog_render', 'host_display_surface_verified': False, 'fallback_displayed': selected_surface != 'cockpit', 'recorded_at': utc_now()}
    if not isinstance(receipt, dict):
        raise RouterError('display_surface_receipt must be an object when supplied')
    if receipt.get('schema_version') != DISPLAY_SURFACE_RECEIPT_SCHEMA:
        raise RouterError(f'display_surface_receipt requires schema_version={DISPLAY_SURFACE_RECEIPT_SCHEMA}')
    actual = receipt.get('actual_surface')
    if actual not in {'chat_route_sign', 'chat_route_sign_fallback', 'cockpit'}:
        raise RouterError('display_surface_receipt.actual_surface must be chat_route_sign, chat_route_sign_fallback, or cockpit')
    if receipt.get('run_id') not in {None, run_id}:
        raise RouterError('display_surface_receipt.run_id must match current run_id')
    if actual == 'cockpit' and receipt.get('host_display_surface_verified') is not True:
        raise RouterError('display_surface_receipt for cockpit requires host_display_surface_verified=true')
    return {'schema_version': DISPLAY_SURFACE_RECEIPT_SCHEMA, 'run_id': run_id, 'requested_display_surface': requested, 'actual_surface': actual, 'source_kind': str(receipt.get('source_kind') or 'host_receipt'), 'host_display_surface_verified': bool(receipt.get('host_display_surface_verified')), 'fallback_displayed': bool(receipt.get('fallback_displayed', actual != 'cockpit')), 'host_surface_id': receipt.get('host_surface_id'), 'notes': receipt.get('notes'), 'recorded_at': utc_now()}

def _write_display_surface_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], display_confirmation: dict[str, Any], payload: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    requested = str(answers.get('display_surface') or 'chat route signs')
    requested_normalized = requested.lower()
    selected_surface = 'chat_route_sign' if 'chat' in requested_normalized else 'chat_route_sign_fallback'
    display_receipt = router._display_surface_receipt_from_payload(payload or {}, run_id=str(run_state['run_id']), requested=requested, selected_surface=selected_surface)
    actual_surface = str(display_receipt.get('actual_surface') or selected_surface)
    if actual_surface == 'cockpit':
        selected_surface = 'cockpit'
    route_sign = router._startup_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
    sign_path = run_root / 'diagrams' / 'current_route_sign.md'
    sign_path.parent.mkdir(parents=True, exist_ok=True)
    sign_path.write_text(route_sign['markdown'], encoding='utf-8')
    write_json(run_root / 'display' / 'display_surface.json', {'schema_version': 'flowpilot.display_surface.v1', 'run_id': run_state['run_id'], 'requested_display_surface': requested, 'selected_surface': selected_surface, 'actual_display_surface': actual_surface, 'chat_route_sign_path': project_relative(project_root, sign_path), 'standard_route_sign_markdown_path': project_relative(project_root, Path(route_sign['markdown_preview_path'])), 'standard_route_sign_mermaid_path': project_relative(project_root, Path(route_sign['mermaid_path'])), 'standard_route_sign_display_packet_path': project_relative(project_root, Path(route_sign['display_packet_path'])), 'route_sign_mermaid_sha256': route_sign['mermaid_sha256'], 'chat_display_required': route_sign['chat_display_required'], 'chat_displayed_by_controller': True, 'user_dialog_display_confirmation': display_confirmation, 'display_surface_receipt': display_receipt, 'host_display_surface_verified': bool(display_receipt.get('host_display_surface_verified')), 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Controller must paste the router-provided display_text Mermaid block in chat before writing the Controller receipt for this action; generated files alone do not satisfy display.', 'cockpit_status': 'host_verified_open' if selected_surface == 'cockpit' else 'not_started_in_router_runtime', 'cockpit_probe_required_for_requested_cockpit': 'cockpit' in requested_normalized, 'reviewer_fallback_check_required_for_requested_cockpit': 'cockpit' in requested_normalized, 'fallback_is_display_only_not_product_ui_completion': True, 'updated_at': utc_now()})

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

def _next_resume_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('resume_reentry_requested'):
        return None
    if not flags.get('resume_state_loaded'):
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
        return make_action(action_type='load_resume_state', actor='controller', label='controller_loads_resume_state_before_role_rehydration', summary='Controller loads current-run state, ledgers, frontier, visible plan, and crew memory before live role rehydration.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _router_daemon_lock_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], extra={'postcondition': 'resume_state_loaded', 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'wake_recorded_to_router_required': True, 'visible_plan_restore_required': True, 'role_rehydration_required_before_pm_resume_decision': True, 'continuation_quarantine_required': True, 'resume_next_recipient_from_packet_ledger': resume_next, 'router_daemon_resume_recovery': _router_daemon_resume_recovery_summary(project_root, run_root)})
    if not flags.get('resume_roles_restored'):
        active_blocker = run_state.get('active_control_blocker')
        if isinstance(active_blocker, dict) and active_blocker.get('originating_action_type') == 'rehydrate_role_agents':
            return None
        return make_action(action_type='rehydrate_role_agents', actor='controller', label='host_rehydrates_resume_roles_before_pm_decision', summary='Host restores or replaces all six live FlowPilot roles from current-run memory before PM resume decision.', allowed_reads=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'resume_roles_restored', **router._resume_role_rehydration_action_extra(project_root, run_root, run_state)})
    return None

def _next_role_recovery_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('role_recovery_requested'):
        return None
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        return None
    trigger_source = str(transaction.get('trigger_source') or '')
    if trigger_source in {'heartbeat_resume', 'manual_resume'}:
        return None
    if not flags.get('role_recovery_state_loaded'):
        return make_action(action_type='load_role_recovery_state', actor='controller', label='controller_loads_role_recovery_state_before_normal_work', summary='Controller loads current-run role recovery state before any normal route, packet, gate, wait, or control-blocker work continues.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_state_loaded', 'role_recovery_transaction': transaction, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'recovery_priority': 'preempt_normal_work', 'normal_waits_allowed_before_recovery': False})
    if not flags.get('role_recovery_roles_restored') and (not flags.get('role_recovery_environment_blocked')):
        return make_action(action_type='recover_role_agents', actor='controller', label='host_recovers_role_agents_before_normal_work', summary='Host restores or replaces the unhealthy background role, escalating to full crew recycle when targeted recovery cannot succeed.', allowed_reads=[project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_roles_restored', 'role_recovery_transaction': transaction, 'target_role_keys': list(transaction.get('target_role_keys') or []), 'recovery_ladder': transaction.get('recovery_ladder') or [], 'payload_contract': router._role_recovery_payload_contract(run_root, run_state, transaction), 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False}, 'role_recovery_request': [{**router._resume_role_context(project_root, run_root, run_state, role), 'recovery_transaction_id': transaction.get('transaction_id'), 'recovery_scope': transaction.get('recovery_scope'), 'old_agent_id': _active_agent_id_for_role(run_root, role), 'restore_first_required': True, 'packet_ownership_reconciliation_required': True, 'superseded_agent_output_quarantine_required': True} for role in transaction.get('target_role_keys') or [] if role in CREW_ROLE_KEYS], 'full_crew_recycle_scope_if_escalated': list(CREW_ROLE_KEYS), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'normal_waits_allowed_before_recovery': False, 'mechanical_obligation_replay_after_recovery': True, 'pm_decision_required_after_recovery': False, 'pm_escalation_only_for_semantic_ambiguity': True})
    return None

def _next_startup_heartbeat_binding_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    if not router._scheduled_continuation_requested(answers):
        return None
    if run_state['flags'].get('continuation_binding_recorded') and router._host_heartbeat_binding_ready(run_root, run_state):
        return None
    if not run_state['flags'].get('controller_core_loaded'):
        return None
    automation_id_hint = f"flowpilot-{run_state['run_id']}-heartbeat"
    automation_name = f"FlowPilot {run_state['run_id']} heartbeat"
    prompt = _startup_heartbeat_prompt(project_root, str(run_state['run_id']))
    return make_action(action_type='create_heartbeat_automation', actor='bootloader', label='host_bootstraps_startup_heartbeat_automation', summary='Create the one-minute Codex heartbeat for the current run after Controller core handoff and before startup review.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, router._continuation_binding_path(run_root))], allowed_writes=[project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'continuation_binding_recorded', 'requires_host_automation': True, 'host_tool': 'codex_app.automation_update', 'automation_update_request': {'mode': 'create', 'kind': 'heartbeat', 'destination': 'thread', 'name': automation_name, 'prompt': prompt, 'rrule': 'FREQ=MINUTELY;INTERVAL=1', 'status': 'ACTIVE'}, 'expected_payload': {'route_heartbeat_interval_minutes': 1, 'host_automation_id': automation_id_hint, 'host_automation_verified': True, 'host_automation_proof': {'source_kind': 'host_receipt', 'run_id': run_state['run_id'], 'host_automation_id': automation_id_hint, 'route_heartbeat_interval_minutes': 1, 'heartbeat_bound_to_current_run': True}}, 'payload_contract': _heartbeat_payload_contract(run_state['run_id'], automation_id_hint), 'proof_required_before_controller_receipt': True})

def _next_controller_boundary_confirmation_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_core_loaded'):
        return None
    if flags.get('controller_role_confirmed') and router._controller_boundary_confirmation_context(project_root, run_root, run_state) is not None:
        return None
    if router._controller_action_open_for(run_root, action_type='confirm_controller_core_boundary', postcondition='controller_role_confirmed'):
        return None
    if router._legacy_pm_reset_boundary_confirmed(run_state):
        return None
    if not flags.get('controller_boundary_recovery_requested'):
        return None
    sources = router._controller_boundary_sources(run_root)
    return make_action(action_type='confirm_controller_core_boundary', actor='controller', label='controller_role_confirmed_from_router_core', summary='Controller records a router-owned confirmation that controller.core is the active boundary authority.', allowed_reads=[project_relative(project_root, sources['manifest_path']), project_relative(project_root, sources['controller_core_path'])], allowed_writes=[project_relative(project_root, router._controller_boundary_confirmation_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'controller_role_confirmed', 'controller_boundary_confirmation_schema': CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA, 'controller_core_card_id': 'controller.core', 'runtime_output_contract': {'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'required_role': 'controller', 'controller_visibility': 'role_output_envelope_only', 'runtime_command': 'flowpilot_runtime.py submit-controller-boundary-confirmation', 'requires_runtime_receipt': True, 'controller_must_not_handwrite_deliverable': True, 'controller_may_read_sealed_bodies': False, 'controller_may_approve_gates': False, 'controller_may_mutate_route': False}, 'sealed_body_reads_allowed': False, 'controller_may_create_project_evidence': False})

def _next_startup_mechanical_audit_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_role_confirmed'):
        return None
    if flags.get('startup_mechanical_audit_written') and router._startup_mechanical_audit_context(project_root, run_root, run_state):
        return None
    if router._controller_action_open_for(run_root, action_type='write_startup_mechanical_audit', postcondition='startup_mechanical_audit_written'):
        return None
    allowed_reads = [project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, project_root / '.flowpilot' / 'current.json'), project_relative(project_root, project_root / '.flowpilot' / 'index.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))]
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        allowed_reads.append(project_relative(project_root, boundary_path))
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        allowed_reads.extend([project_relative(project_root, startup_intake_context['record_path']), project_relative(project_root, startup_intake_context['result_path']), project_relative(project_root, startup_intake_context['receipt_path']), project_relative(project_root, startup_intake_context['envelope_path'])])
    return make_action(action_type='write_startup_mechanical_audit', actor='router', label='router_writes_startup_mechanical_audit', summary='Router writes the startup mechanical audit and proof before exposing the reviewer startup fact-check card.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json'), project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json.proof.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'startup_mechanical_audit_written', 'reviewer_card_waiting_for_audit': 'reviewer.startup_fact_check', 'router_replacement_scope': 'mechanical_only'})

def _next_display_plan_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    last_sync = run_state.get('visible_plan_sync') if isinstance(run_state.get('visible_plan_sync'), dict) else {}
    route_sign_fresh = not sync_payload.get('route_sign_display_required') or last_sync.get('route_sign_mermaid_sha256') == sync_payload.get('route_sign_mermaid_sha256')
    if last_sync.get('projection_hash') == sync_payload['projection_hash'] and route_sign_fresh:
        return None
    idempotency_key = _router_scheduler_idempotency_key({'action_type': 'sync_display_plan', 'label': 'controller_syncs_display_plan', 'projection_hash': sync_payload['projection_hash']}, 'startup', 'startup')
    if router._controller_action_open_for(run_root, action_type='sync_display_plan', idempotency_key=idempotency_key):
        return None
    allowed_writes = [project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._route_state_snapshot_path(run_root)), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router._route_display_refresh_path(run_root)), project_relative(project_root, run_root / 'display' / 'user_dialog_display_ledger.json')]
    if not sync_payload['display_plan_exists']:
        allowed_writes.append(project_relative(project_root, router._display_plan_path(run_root)))
    if sync_payload.get('route_sign_display_required'):
        allowed_writes.extend([project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.mmd'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram-display.json')])
    allowed_reads = [project_relative(project_root, project_root / '.flowpilot' / 'current.json'), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, router._route_state_snapshot_path(run_root)), project_relative(project_root, router._current_status_summary_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, router.run_state_path(run_root))]
    for raw_path in (sync_payload.get('route_sign_source_frontier_path'), sync_payload.get('route_sign_source_route_path')):
        if isinstance(raw_path, str) and raw_path:
            path = Path(raw_path)
            read_path = path if path.is_absolute() else project_root / path
            try:
                rel_path = project_relative(project_root, read_path)
            except RouterError:
                continue
            if rel_path not in allowed_reads:
                allowed_reads.append(rel_path)
    return make_action(action_type='sync_display_plan', actor='controller', label='controller_syncs_display_plan', summary=router._display_plan_sync_action_summary(sync_payload), allowed_reads=allowed_reads, allowed_writes=allowed_writes, extra={**sync_payload})

def _display_plan_sync_action_summary(router: ModuleType, sync_payload: dict[str, Any]) -> str:
    _bind_router(router)
    if sync_payload.get('route_sign_display_required'):
        return 'Display the canonical FlowPilot Route Sign in the user dialog, then sync the host visible plan from committed route state.'
    if sync_payload.get('display_kind') == 'startup_waiting_state' and sync_payload.get('user_visible_display_suppressed'):
        return 'Sync the host visible plan to the internal waiting-for-PM-route placeholder; no user-dialog route map is required until a canonical PM route exists.'
    return 'Display the current route map projection in the user dialog, then sync the host visible plan from display_plan.json.'

def _apply_sync_display_plan_state(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    payload = payload or {}
    confirmation = None
    if action.get('requires_user_dialog_display_confirmation'):
        confirmation = router._display_confirmation_for_action(payload, action)
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    if not sync_payload['display_plan_exists']:
        write_json(router._display_plan_path(run_root), router._waiting_for_pm_display_plan(run_state))
        sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event='sync_display_plan')
    sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
    if sync_payload.get('route_sign_display_required'):
        route_sign = router._route_map_route_sign_payload(project_root, write=True, mark_chat_displayed=True)
        sync_payload = {**sync_payload, 'route_sign_markdown_path': route_sign.get('markdown_preview_path'), 'route_sign_mermaid_path': route_sign.get('mermaid_path'), 'route_sign_display_packet_path': route_sign.get('display_packet_path'), 'route_sign_mermaid_sha256': route_sign.get('mermaid_sha256'), 'route_sign_source_kind': route_sign.get('route_source_kind'), 'route_sign_node_count': route_sign.get('route_node_count'), 'route_sign_checklist_item_count': route_sign.get('route_checklist_item_count'), 'route_sign_layout': route_sign.get('route_sign_layout'), 'route_sign_source_route_path': route_sign.get('source_route_path'), 'route_sign_source_frontier_path': route_sign.get('source_frontier_path')}
        if isinstance(sync_payload.get('route_display_refresh'), dict):
            sync_payload['route_display_refresh']['route_sign_markdown_path'] = route_sign.get('markdown_preview_path')
            sync_payload['route_display_refresh']['route_sign_mermaid_sha256'] = route_sign.get('mermaid_sha256')
    if confirmation is not None:
        router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
    if isinstance(sync_payload.get('route_display_refresh'), dict):
        write_json(router._route_display_refresh_path(run_root), sync_payload['route_display_refresh'])
    run_state['visible_plan_sync'] = {'display_plan_path': sync_payload['display_plan_path'], 'route_state_snapshot_path': sync_payload['route_state_snapshot_path'], 'route_state_snapshot_hash': sync_payload['route_state_snapshot_hash'], 'current_status_summary_path': sync_payload.get('current_status_summary_path'), 'current_status_summary_hash': sync_payload.get('current_status_summary_hash'), 'projection_hash': sync_payload['projection_hash'], 'display_text_format': sync_payload.get('display_text_format'), 'route_sign_display_required': sync_payload.get('route_sign_display_required'), 'route_sign_display_degraded_reason': sync_payload.get('route_sign_display_degraded_reason'), 'route_sign_markdown_path': sync_payload.get('route_sign_markdown_path'), 'route_sign_mermaid_path': sync_payload.get('route_sign_mermaid_path'), 'route_sign_display_packet_path': sync_payload.get('route_sign_display_packet_path'), 'route_sign_mermaid_sha256': sync_payload.get('route_sign_mermaid_sha256'), 'route_sign_source_kind': sync_payload.get('route_sign_source_kind'), 'route_sign_node_count': sync_payload.get('route_sign_node_count'), 'route_sign_checklist_item_count': sync_payload.get('route_sign_checklist_item_count'), 'route_sign_layout': sync_payload.get('route_sign_layout'), 'route_sign_source_route_path': sync_payload.get('route_sign_source_route_path'), 'route_sign_source_frontier_path': sync_payload.get('route_sign_source_frontier_path'), 'route_display_refresh_path': sync_payload.get('route_display_refresh_path'), 'route_display_refresh_sha256': packet_runtime.sha256_file(router._route_display_refresh_path(run_root)) if router._route_display_refresh_path(run_root).exists() else None, 'display_is_route_authority': False, 'display_required': sync_payload.get('display_required'), 'user_visible_display_suppressed': sync_payload.get('user_visible_display_suppressed', False), 'internal_display_reason': sync_payload.get('internal_display_reason'), 'synced_at': utc_now(), 'host_action': sync_payload['host_action']}
    if confirmation is not None:
        run_state['visible_plan_sync']['user_dialog_display_confirmation'] = confirmation
    run_state.setdefault('flags', {})['visible_plan_synced'] = True
    return sync_payload

def _next_startup_display_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_role_confirmed'):
        return None
    if flags.get('startup_display_status_written'):
        return None
    if router._controller_action_open_for(run_root, action_type='write_display_surface_status', postcondition='startup_display_status_written'):
        return None
    route_sign = router._startup_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    answers = router._startup_answers_from_run(run_root)
    requested_display_surface = str(answers.get('display_surface') or 'chat')
    cockpit_requested = requested_display_surface == 'cockpit'
    display_gate = router._user_dialog_display_gate({'display_text': route_sign['markdown'], 'display_text_format': 'markdown_mermaid', 'display_required': True, 'controller_must_display_text_before_apply': True, 'generated_files_alone_satisfy_chat_display': False, 'controller_display_rule': 'Paste this exact startup route-sign display_text in the user dialog before writing the Controller receipt for write_display_surface_status; generated files alone do not satisfy display.'}, display_kind='startup_route_sign', display_text=route_sign['markdown'])
    return make_action(action_type='write_display_surface_status', actor='controller', label='controller_writes_startup_display_surface_status', summary='Display the startup FlowPilot Route Sign Mermaid in chat, then write startup display-surface status before reviewer startup fact review.', allowed_reads=[project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, run_root / 'execution_frontier.json')], allowed_writes=[project_relative(project_root, run_root / 'display' / 'display_surface.json'), project_relative(project_root, run_root / 'diagrams' / 'current_route_sign.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.mmd'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram.md'), project_relative(project_root, run_root / 'diagrams' / 'user-flow-diagram-display.json'), project_relative(project_root, run_root / 'display' / 'user_dialog_display_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'startup_display_status_written', **display_gate, 'chat_display_required': route_sign['chat_display_required'], 'route_sign_mermaid_sha256': route_sign['mermaid_sha256'], 'requested_display_surface': requested_display_surface, 'resolved_display_surface': 'chat-fallback' if cockpit_requested else 'chat-requested', 'cockpit_probe_required_for_requested_cockpit': cockpit_requested, 'reviewer_fallback_check_required_for_requested_cockpit': cockpit_requested, 'fallback_is_display_only_not_product_ui_completion': True, 'payload_contract': _display_surface_receipt_payload_contract()})


_LOCAL_NAMES = set(globals())
