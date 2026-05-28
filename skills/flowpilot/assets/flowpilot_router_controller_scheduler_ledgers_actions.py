"""Controller action ledger helpers for the FlowPilot router."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_control_plane_contracts import control_plane_completion_class_override
from flowpilot_router_errors import RouterError, RouterLedgerWriteInProgress


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


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
    override = control_plane_completion_class_override(action, postcondition=postcondition)
    if override is not None:
        return override
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
    ledger = {'schema_version': CONTROLLER_ACTION_LEDGER_SCHEMA, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'updated_at': utc_now(), 'controller_table_prompt': _controller_table_prompt(run_root / 'runtime_kit'), 'actions': entries, 'passive_waits': passive_waits, 'counts': _controller_action_counts(entries), 'passive_wait_count': len(passive_waits), 'controller_must_clear_pending_actions': True, 'controller_actions_are_executable_only': True, 'passive_waits_projected_via_status_not_work_board': True, 'router_must_not_mark_done_without_controller_receipt': True}
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
    '_controller_action_completion_class',
    '_controller_action_ledger_has_prompt_header',
    '_write_controller_action_ledger',
    '_rebuild_controller_action_ledger',
    '_ensure_controller_action_ledger',
    '_controller_action_ledger_summary',
)

_LOCAL_NAMES = set(globals())
