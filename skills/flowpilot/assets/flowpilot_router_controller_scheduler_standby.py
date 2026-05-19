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
    user_status_update_allowed = foreground_turn_return_allowed
    controller_patrol_required = controller_must_continue_standby
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
    no_pending_controller_actions = not (pending_action_ids or waiting_action_ids)
    final_answer_allowed = bool(controller_stop_allowed and no_pending_controller_actions and (not controller_must_continue_standby) and (not controller_must_process_pending_action) and (not wait_target_action_ready))
    continuous_standby_status = 'released' if final_answer_allowed else ('in_progress' if controller_patrol_required or controller_must_continue_standby else 'not_active')
    final_answer_preflight = {
        'final_answer_allowed': final_answer_allowed,
        'controller_stop_allowed': controller_stop_allowed,
        'terminal_state_required': True,
        'terminal_state_observed': controller_stop_allowed,
        'controller_stop_allowed_required': True,
        'no_pending_controller_actions_required': True,
        'no_pending_controller_actions': no_pending_controller_actions,
        'continuous_standby_not_in_progress_required': True,
        'continuous_standby_status': continuous_standby_status,
        'user_status_update_is_not_stop_permission': True,
        'status_projection_is_not_stop_authority': True,
        'authority_source': 'router_daemon_status_and_controller_action_ledger',
    }
    if not final_answer_allowed:
        if not controller_stop_allowed:
            final_answer_preflight['blocked_reason'] = 'nonterminal_controller_must_stay_attached'
        elif not no_pending_controller_actions:
            final_answer_preflight['blocked_reason'] = 'pending_controller_actions_remain'
        else:
            final_answer_preflight['blocked_reason'] = 'continuous_standby_or_duty_still_active'
    return {'schema_version': FOREGROUND_CONTROLLER_STANDBY_SCHEMA, 'ok': True, 'command': 'controller-standby', 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'started_at': started_at, 'observed_at': utc_now(), 'elapsed_seconds': round(elapsed, 3), 'max_seconds': max_seconds, 'poll_seconds': poll_seconds, 'poll_count': poll_count, 'standby_state': standby_state, 'controller_must_continue_standby': controller_must_continue_standby, 'controller_must_process_pending_action_before_exit': controller_must_process_pending_action, 'controller_must_process_wait_target_before_exit': wait_target_action_ready, 'foreground_exit_allowed': controller_stop_allowed, 'foreground_turn_return_allowed': foreground_turn_return_allowed, 'foreground_turn_return_is_not_controller_stop': True, 'user_status_update_allowed': user_status_update_allowed, 'controller_patrol_required': controller_patrol_required, 'foreground_required_mode': foreground_required_mode, 'controller_stop_allowed': controller_stop_allowed, 'nonterminal_controller_must_stay_attached': not controller_stop_allowed, 'final_answer_preflight': final_answer_preflight, 'normal_router_progress_source': 'router_daemon_status_and_controller_action_ledger', 'diagnostic_router_reentry_commands': ['next', 'run-until-wait'], 'diagnostic_router_reentry_policy': 'diagnostic/test/explicit-repair only; not normal progress while daemon status and the Controller action ledger own the active run', 'break_glass_reminder': _controller_break_glass_reminder(), 'standby_does_not_drive_router_progress': True, 'metadata_only': True, 'sealed_body_reads_allowed': False, 'router_daemon': {'lock_path': project_relative(project_root, lock_path), 'status_path': project_relative(project_root, status_path), 'lock_exists': lock_path.exists(), 'lock_live': lock_live, 'lock_status': lock.get('status'), 'lock_last_tick_at': lock.get('last_tick_at'), 'status_exists': status_path.exists(), 'status_ok': status_ok, 'daemon_live': daemon_live, 'active_owner_live': _router_daemon_lock_has_live_owner(lock_liveness), 'heartbeat_status': heartbeat_monitor['status'], 'heartbeat_age_seconds': heartbeat_monitor['age_seconds'], 'heartbeat_check_after_seconds': heartbeat_monitor['check_after_seconds'], 'heartbeat_reasons': heartbeat_monitor['reasons'], 'controller_liveness_check_required': heartbeat_monitor['controller_liveness_check_required'], 'monitor_can_decide_recovery': heartbeat_monitor['monitor_can_decide_recovery'], 'controller_instruction': heartbeat_monitor['controller_instruction'], 'lifecycle_status': daemon_status.get('lifecycle_status'), 'last_tick_at': daemon_status.get('last_tick_at'), 'tick_interval_seconds': daemon_status.get('tick_interval_seconds')}, 'controller_action_ledger': {'path': project_relative(project_root, ledger_path), 'exists': ledger_path.exists(), 'schema_ok': ledger_ok, 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') if ledger_ok else _controller_action_counts([]), 'passive_wait_count': int(ledger.get('passive_wait_count') or 0) if ledger_ok else 0, 'passive_waits_projected_via_status_not_work_board': bool(ledger.get('passive_waits_projected_via_status_not_work_board')) if ledger_ok else False, 'pending_action_ids': pending_action_ids, 'waiting_action_ids': waiting_action_ids}, 'current_work': current_work, 'current_wait': {'action_type': current_wait.get('action_type'), 'label': current_wait.get('label'), 'waiting_for_role': current_wait.get('waiting_for_role'), 'wait_class': current_wait.get('wait_class'), 'target_role': current_wait.get('target_role'), 'wait_reason': current_wait.get('wait_reason'), 'started_at': current_wait.get('started_at'), 'elapsed_seconds': current_wait.get('elapsed_seconds'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'expected_return_path': current_wait.get('expected_return_path'), 'expected_evidence': current_wait.get('expected_evidence'), 'reminder': current_wait.get('reminder'), 'liveness_probe': current_wait.get('liveness_probe'), 'controller_local_self_audit': current_wait.get('controller_local_self_audit'), 'next_due': current_wait.get('next_due'), 'reissue': current_wait.get('reissue'), 'blocker': current_wait.get('blocker')}, 'continuous_standby_task': continuous_standby_task, 'current_action': {'action_type': current_action.get('action_type'), 'label': current_action.get('label'), 'controller_action_id': current_action.get('controller_action_id'), 'controller_projection_kind': current_action.get('controller_projection_kind') or _controller_action_projection_kind(current_action), 'ordinary_controller_work_row': not _action_is_passive_wait_status(current_action), 'apply_required': current_action.get('apply_required')} if current_action else None, 'exit_policy': {'returns_on_controller_action': True, 'returns_on_terminal': True, 'returns_on_user_required': True, 'returns_on_daemon_liveness_check_required': True, 'returns_on_bounded_timeout': True, 'bounded_timeout_is_diagnostic_only': True, 'returns_on_wait_target_check_due': True, 'returns_on_wait_target_blocker_required': True, 'returns_on_wait_target_reissue_required': True, 'controller_action_ready_blocks_foreground_exit': True, 'live_daemon_wait_requires_standby': True, 'controller_stop_requires_terminal_run': True, 'user_status_update_is_not_controller_stop': True, 'status_projection_is_not_stop_authority': True, 'nonterminal_modes': ['process_controller_action', 'watch_router_daemon', 'check_liveness', 'return_for_user_input', 'process_wait_target_check', 'record_wait_target_blocker', 'record_wait_target_no_output_reissue']}}

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
            snapshot['foreground_turn_return_is_not_controller_stop'] = True
            snapshot['user_status_update_allowed'] = bool(snapshot['foreground_turn_return_allowed'])
            snapshot['controller_patrol_required'] = bool(snapshot['controller_must_continue_standby'])
            snapshot['controller_stop_allowed'] = False
            snapshot['nonterminal_controller_must_stay_attached'] = True
            snapshot['final_answer_preflight'] = {
                'final_answer_allowed': False,
                'controller_stop_allowed': False,
                'terminal_state_required': True,
                'terminal_state_observed': False,
                'controller_stop_allowed_required': True,
                'no_pending_controller_actions_required': True,
                'no_pending_controller_actions': not bool(snapshot['controller_action_ledger']['pending_action_ids'] or snapshot['controller_action_ledger']['waiting_action_ids']),
                'continuous_standby_not_in_progress_required': True,
                'continuous_standby_status': 'in_progress' if snapshot['controller_must_continue_standby'] else 'not_active',
                'user_status_update_is_not_stop_permission': True,
                'status_projection_is_not_stop_authority': True,
                'authority_source': 'router_daemon_status_and_controller_action_ledger',
                'blocked_reason': 'timeout_still_waiting_nonterminal',
            }
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
    snapshot_preflight = snapshot.get('final_answer_preflight') if isinstance(snapshot.get('final_answer_preflight'), dict) else {}
    final_answer_allowed = bool(patrol_result == 'terminal_return' and controller_stop_allowed and snapshot_preflight.get('final_answer_allowed', controller_stop_allowed))
    final_answer_preflight = {
        'final_answer_allowed': final_answer_allowed,
        'controller_stop_allowed': controller_stop_allowed,
        'terminal_return_required': True,
        'controller_stop_allowed_required': True,
        'no_pending_controller_actions_required': True,
        'no_pending_controller_actions': bool(snapshot_preflight.get('no_pending_controller_actions', False)),
        'continuous_controller_standby_status': str(snapshot_preflight.get('continuous_standby_status') or ('released' if final_answer_allowed else 'in_progress')),
        'user_status_update_is_not_stop_permission': True,
        'status_projection_is_not_stop_authority': True,
        'authority_source': 'router_daemon_status_and_controller_action_ledger',
    }
    if not final_answer_allowed:
        final_answer_preflight['blocked_reason'] = 'patrol_result_is_nonterminal'
    return {'schema_version': CONTROLLER_PATROL_TIMER_SCHEMA, 'ok': True, 'command': 'controller-patrol-timer', 'seconds': float(seconds), 'patrol_result': patrol_result, 'foreground_required_mode': foreground_mode, 'controller_stop_allowed': controller_stop_allowed, 'final_answer_preflight': final_answer_preflight, 'anti_exit_reminder': anti_exit_reminder, 'break_glass_reminder': _controller_break_glass_reminder(), 'controller_instruction': controller_instruction, 'next_command': next_command if patrol_result == 'continue_patrol' else None, 'standby_status_after_rerun': 'continuous_controller_standby remains in_progress until the next command output' if patrol_result == 'continue_patrol' else None, 'completion_allowed_only_when': 'terminal_return_and_controller_stop_allowed_true', 'command_start_is_completion': False, 'command_restart_is_completion': False, 'monitor_source': 'existing_router_daemon_monitor', 'normal_progress_source': 'router_daemon_status_and_controller_action_ledger', 'display_projection_is_stop_authority': False, 'standby_snapshot': snapshot}

__all__ = (
    '_continuous_standby_watch_label',
    '_continuous_standby_release_conditions',
    '_continuous_standby_task_payload',
    '_current_action_is_ordinary_controller_work',
    '_should_refresh_continuous_standby_row',
    '_ensure_continuous_standby_controller_action',
    '_foreground_standby_pending_action_ids',
    '_foreground_standby_waiting_action_ids',
    '_build_foreground_controller_standby_snapshot',
    'foreground_controller_standby',
    'controller_patrol_timer',
)

_LOCAL_NAMES = set(globals())
