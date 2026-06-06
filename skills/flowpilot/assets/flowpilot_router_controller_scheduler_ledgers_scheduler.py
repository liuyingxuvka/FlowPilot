"""Router scheduler ledger helpers for the FlowPilot router."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_closure_kernel
from flowpilot_router_errors import RouterError


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
    return {'exists': True, 'valid_json': True, 'path': str(_router_scheduler_ledger_path(run_root)), 'updated_at': ledger.get('updated_at'), 'counts': ledger.get('counts') or _router_scheduler_row_counts(rows), 'open_row_ids': [row.get('row_id') for row in rows if flowpilot_closure_kernel.closure_blocks_progress('router_scheduler_row', row)], 'barrier_row_ids': [row.get('row_id') for row in rows if row.get('barrier_kind') not in {None, '', 'none'} and flowpilot_closure_kernel.closure_blocks_progress('router_scheduler_row', row)]}


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
    if action_type in {'emit_startup_banner', 'confirm_controller_core_boundary', CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE, 'write_startup_mechanical_audit', 'write_display_surface_status'}:
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
        if not flowpilot_closure_kernel.closure_blocks_progress('controller_action', entry):
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


def _controller_action_reconciled_for(router: ModuleType, run_root: Path, *, action_type: str | None=None, postcondition: str | None=None, idempotency_key: str | None=None, label: str | None=None) -> bool:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return False
    for path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        closure_record = dict(entry)
        reconciliation_status = str(entry.get('router_reconciliation_status') or '')
        if reconciliation_status in {'retry_pending', 'blocked'} and not closure_record.get('router_reconciliation'):
            closure_record['router_reconciliation'] = {'status': reconciliation_status}
        if flowpilot_closure_kernel.closure_blocks_progress('controller_action', closure_record):
            continue
        if not (reconciliation_status in {'reconciled', 'retry_pending', 'blocked'} or entry.get('router_reconciled_at')):
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
    '_controller_action_reconciled_for',
)

_LOCAL_NAMES = set(globals())
