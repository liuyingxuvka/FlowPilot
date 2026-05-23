"""Pending Controller receipt reconciliation helpers.

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


def _router_scheduler_row_for_controller_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return {}
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    for row in scheduler.get('rows', []) if isinstance(scheduler.get('rows'), list) else []:
        if isinstance(row, dict) and row.get('row_id') == row_id:
            return row
    return {}

def _done_controller_receipt_for_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_id = str(entry.get('action_id') or '').strip()
    if not action_id:
        return {}
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA:
        return {}
    if receipt.get('status') != 'done':
        return {}
    if str(receipt.get('action_id') or '') != action_id:
        return {}
    return receipt

def _clear_pending_after_reconciled_controller_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, pending_action: dict[str, Any], receipt: dict[str, Any], applied_postcondition: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    if str(pending_action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=pending_action, receipt=receipt, applied_postcondition=applied_postcondition)
    run_state['pending_action'] = None
    blocker_resolution = router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=pending_action, entry={'action_id': receipt.get('action_id'), 'router_scheduler_row_id': pending_action.get('router_scheduler_row_id')}, reconciliation=applied_postcondition)
    append_history(run_state, 'router_reconciled_pending_controller_action_receipt', {'action_type': pending_action.get('action_type'), 'label': pending_action.get('label'), 'controller_action_id': receipt.get('action_id'), 'receipt_status': receipt.get('status'), 'applied_postcondition': applied_postcondition or {}, 'control_blocker_resolution': blocker_resolution})
    router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_receipt_reconciliation')
    router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_receipt_reconciliation', update_display=True)
    router.save_run_state(run_root, run_state)
    return {'changed': True, 'cleared_pending': True, 'receipt_status': receipt.get('status')}

def _apply_controller_repair_work_packet_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, pending_action: dict[str, Any], receipt: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if pending_action.get('controller_may_approve_gate') or pending_action.get('controller_may_mutate_route') or pending_action.get('controller_may_read_sealed_bodies'):
        raise RouterError('controller_repair_work_packet receipt cannot grant gate approval, route mutation, or sealed body access')
    transaction_id = str(pending_action.get('repair_transaction_id') or '')
    if not transaction_id:
        raise RouterError('controller_repair_work_packet receipt requires repair_transaction_id')
    transaction_path = router._repair_transaction_path(run_root, transaction_id)
    transaction = read_json_if_exists(transaction_path)
    if transaction.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
        raise RouterError('controller_repair_work_packet transaction is missing')
    recorded_at = utc_now()
    repair_result = {
        'schema_version': 'flowpilot.controller_repair_work_packet_result.v1',
        'status': str(payload.get('status') or receipt.get('status') or 'done'),
        'evidence': payload.get('evidence'),
        'recorded_at': recorded_at,
        'controller_action_id': receipt.get('action_id') or pending_action.get('controller_action_id'),
        'controller_receipt_path': project_relative(project_root, _controller_receipt_path(run_root, str(receipt.get('action_id') or ''))),
        'controller_receipt_payload_keys': sorted(str(key) for key in payload),
    }
    transaction['controller_repair_work_packet_result'] = repair_result
    transaction['status'] = 'awaiting_recheck'
    transaction['updated_at'] = recorded_at
    write_json(transaction_path, transaction)
    router._write_repair_transaction_index(project_root, run_root, run_state)
    return {
        'applied': True,
        'source': 'router_owned_controller_repair_work_packet_receipt',
        'repair_transaction_id': transaction_id,
        'repair_transaction_path': project_relative(project_root, transaction_path),
        'transaction_status': 'awaiting_recheck',
        'controller_action_id': repair_result['controller_action_id'],
    }

def _reconcile_pending_controller_action_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    pending_action = run_state.get('pending_action')
    if not isinstance(pending_action, dict):
        return {'changed': False}
    receipt = _receipt_for_pending_controller_action(run_root, pending_action)
    if not receipt:
        return {'changed': False}
    status = str(receipt.get('status') or '')
    if status == 'waiting':
        return {'changed': False, 'waiting_receipt': True}
    payload = receipt.get('payload') if isinstance(receipt.get('payload'), dict) else {}
    action_type = str(pending_action.get('action_type') or receipt.get('action_type') or '')
    if status == 'blocked':
        router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_blocked', error_message=f'Controller reported active action {action_type} blocked before Router could continue.', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
        return {'changed': True, 'blocked': True, 'receipt_status': status}
    if status == 'skipped':
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt)
    if status != 'done':
        return {'changed': False, 'unsupported_receipt_status': status}
    action_class = router._controller_action_completion_class(pending_action)
    router._record_router_ownership_entry(project_root, run_root, run_state, action_id=str(receipt.get('action_id') or ''), action_type=action_type, router_state='controller_receipt_done', workflow_owner='router', postcondition=str(action_class.get('postcondition') or _pending_action_postcondition(pending_action) or ''), source='controller_receipt_reconciliation', receipt_path=project_relative(project_root, _controller_receipt_path(run_root, str(receipt.get('action_id') or ''))), details={'action_class': action_class, 'controller_receipt_is_local_evidence_only': True, 'controller_receipt_payload': payload})
    if action_type == 'controller_repair_work_packet':
        try:
            applied = router._apply_controller_repair_work_packet_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, payload=payload)
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_incomplete_for_repair_work_packet', error_message=f'Controller receipt for {action_type} was marked done, but Router could not update repair transaction state: {exc}', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
            return {'changed': True, 'blocked': True, 'receipt_status': status, 'repair_transaction_update_failed': True}
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition=applied)
    if action_class.get('kind') == 'display_status' and action_type == 'sync_display_plan':
        try:
            sync_payload = router._apply_sync_display_plan_state(project_root, run_root, run_state, pending_action, payload)
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_incomplete_for_display_status', error_message=f'Controller receipt for {action_type} was marked done, but Router could not apply the required display/status fact: {exc}', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
            return {'changed': True, 'blocked': True, 'receipt_status': status}
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition={'applied': True, 'source': 'router_owned_display_status_reclaim', 'projection_hash': sync_payload.get('projection_hash'), 'display_plan_path': sync_payload.get('display_plan_path')})
    postcondition = _pending_action_postcondition(pending_action)
    if postcondition and (not _pending_action_postcondition_satisfied(run_state, postcondition) or action_type == 'deliver_mail'):
        try:
            applied = router._apply_stateful_receipt_postcondition(project_root, run_root, run_state, pending_action, payload)
        except RouterLedgerWriteInProgress:
            raise
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            applied = {'applied': False, 'reason': str(exc), 'repairable': bool(_controller_action_required_deliverables(project_root, run_root, run_state, pending_action)), 'missing_deliverables': _controller_action_required_deliverables(project_root, run_root, run_state, pending_action)}
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, apply_result=applied, source='controller_action_receipt_incomplete_for_stateful_action')
            if repair.get('scheduled'):
                router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_deliverable_repair_scheduled')
                router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_deliverable_repair_scheduled', update_display=True)
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_scheduled': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_action_type': CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE}
            if repair.get('blocked'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_budget_exhausted': True}
            if repair.get('pending_repair'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_pending': True, 'receipt_status': status, 'postcondition': postcondition, 'pending_repair_action_id': repair.get('pending_repair_action_id')}
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_incomplete_for_stateful_action', error_message=f'Controller receipt for {action_type} was marked done, but Router could not apply required postcondition {postcondition}: {exc}', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'postcondition': postcondition, 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label')})
            return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition}
        if not applied.get('applied') or not _pending_action_postcondition_satisfied(run_state, postcondition):
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, apply_result=applied, source='controller_action_receipt_missing_stateful_postcondition')
            if repair.get('scheduled'):
                router._refresh_route_memory(project_root, run_root, run_state, trigger='after_controller_deliverable_repair_scheduled')
                router._sync_derived_run_views(project_root, run_root, run_state, reason='after_controller_deliverable_repair_scheduled', update_display=True)
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_scheduled': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_action_type': CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE}
            if repair.get('blocked'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition, 'repair_budget_exhausted': True}
            if repair.get('pending_repair'):
                router.save_run_state(run_root, run_state)
                return {'changed': True, 'repair_pending': True, 'receipt_status': status, 'postcondition': postcondition, 'pending_repair_action_id': repair.get('pending_repair_action_id')}
            router._write_control_blocker(project_root, run_root, run_state, source='controller_action_receipt_missing_stateful_postcondition', error_message=f'Controller receipt for {action_type} was marked done, but Router postcondition {postcondition} is still not satisfied.', action_type=action_type, payload={'controller_action_id': receipt.get('action_id'), 'postcondition': postcondition, 'controller_receipt_payload': payload, 'pending_action_label': pending_action.get('label'), 'apply_result': applied})
            return {'changed': True, 'blocked': True, 'receipt_status': status, 'postcondition': postcondition}
        return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt, applied_postcondition=applied)
    return router._clear_pending_after_reconciled_controller_receipt(project_root, run_root, run_state, pending_action=pending_action, receipt=receipt)

__all__ = (
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_clear_pending_after_reconciled_controller_receipt',
    '_apply_controller_repair_work_packet_receipt',
    '_reconcile_pending_controller_action_receipt',
)

_LOCAL_NAMES = set(globals())
