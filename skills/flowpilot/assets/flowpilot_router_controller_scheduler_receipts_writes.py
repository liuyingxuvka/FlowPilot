"""Controller scheduler action and receipt write helpers.

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
from flowpilot_control_plane_contracts import control_plane_action_identity_fingerprint
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


def _write_controller_action_entry(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action = router._prepare_router_scheduled_action(project_root, run_root, run_state, action)
    passive_wait_status = _action_is_passive_wait_status(action)
    projection_kind = _controller_action_projection_kind(action)
    action_id = str(action.get('controller_action_id') or _controller_action_id_for_action(action))
    action_path = _controller_action_path(run_root, action_id)
    receipt_path = _controller_receipt_path(run_root, action_id)
    receipt_rel = project_relative(project_root, receipt_path)
    controller_receipt_required = not passive_wait_status and action.get('action_type') not in {'await_card_return_event', 'await_card_bundle_return_event', 'await_role_decision'}
    created = False
    existing = read_json_if_exists(action_path)
    action_identity = control_plane_action_identity_fingerprint(action)
    now = utc_now()
    if existing.get('schema_version') == CONTROLLER_ACTION_SCHEMA:
        existing_action = existing.get('action') if isinstance(existing.get('action'), dict) else existing
        existing_identity = str(existing.get('action_identity') or control_plane_action_identity_fingerprint(existing_action))
        if existing.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES and existing_identity and existing_identity != action_identity:
            raise RouterError(
                f"controller action identity collision for {action_id}: "
                f"existing={existing_identity} new={action_identity}"
            )
        entry = existing
        entry['seen_count'] = int(entry.get('seen_count') or 0) + 1
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES:
            entry['status'] = entry.get('status') or _controller_action_initial_status(action)
    else:
        created = True
        entry = {'schema_version': CONTROLLER_ACTION_SCHEMA, 'action_id': action_id, 'run_id': run_state.get('run_id'), 'action_type': action.get('action_type'), 'label': action.get('label'), 'summary': action.get('summary'), 'status': _controller_action_initial_status(action), 'created_at': now, 'seen_count': 1, 'source_action_id': action.get('action_id'), 'to_role': action.get('to_role'), 'allowed_reads': action.get('allowed_reads') or [], 'allowed_writes': action.get('allowed_writes') or [], 'allowed_external_events': action.get('allowed_external_events') or [], 'dependencies': [], 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'scope_kind': action.get('scope_kind'), 'scope_id': action.get('scope_id'), 'controller_visibility': 'router_action_metadata_only', 'sealed_body_reads_allowed': bool(action.get('sealed_body_reads_allowed', False)), 'action_path': project_relative(project_root, action_path), 'expected_receipt_path': receipt_rel, 'controller_receipt_required': controller_receipt_required, 'controller_projection_kind': projection_kind, 'ordinary_controller_work_row': not passive_wait_status, 'router_must_not_mark_done_without_controller_receipt': controller_receipt_required, 'action': action}
    entry['updated_at'] = now
    entry['last_seen_at'] = now
    entry['action_identity'] = action_identity
    required_deliverables = _controller_action_required_deliverables(project_root, run_root, run_state, action)
    deliverable_contract = _controller_deliverable_contract(required_deliverables)
    if required_deliverables:
        action['required_deliverables'] = required_deliverables
    entry['completion_class'] = router._controller_action_completion_class(action)
    entry['required_deliverables'] = required_deliverables
    entry['deliverable_contract'] = deliverable_contract
    if required_deliverables and (not entry.get('deliverable_status')):
        entry['deliverable_status'] = 'required'
        entry['deliverable_repair_attempts'] = int(entry.get('deliverable_repair_attempts') or 0)
        entry['max_deliverable_repair_attempts'] = CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS
    if action.get('repair_of_controller_action_id'):
        entry['repair_of_controller_action_id'] = action.get('repair_of_controller_action_id')
        entry['repair_target_action_type'] = action.get('repair_target_action_type')
        entry['repair_attempt'] = action.get('repair_attempt')
    for replacement_field in ('replaces', 'replaces_controller_action_id', 'replaces_router_scheduler_row_id', 'replacement_reason', 'original_order', 'role_recovery_transaction_id', 'role_recovery_replay_kind', 'target_recovered_role', 'role_no_output_reissue_attempt', 'max_role_no_output_reissue_attempts', 'target_no_output_role'):
        if action.get(replacement_field) not in (None, '', []):
            entry[replacement_field] = action.get(replacement_field)
    controller_action_view = _controller_ledger_action_view(action, action_id=action_id, receipt_path=receipt_rel, controller_receipt_required=controller_receipt_required)
    entry['router_scheduler_row_id'] = action.get('router_scheduler_row_id')
    entry['scope_kind'] = action.get('scope_kind')
    entry['scope_id'] = action.get('scope_id')
    entry['controller_receipt_required'] = controller_receipt_required
    entry['controller_projection_kind'] = projection_kind
    entry['ordinary_controller_work_row'] = not passive_wait_status
    entry['router_must_not_mark_done_without_controller_receipt'] = controller_receipt_required
    entry['controller_completion_command'] = controller_action_view.get('controller_completion_command')
    entry['controller_completion_mode'] = controller_action_view.get('controller_completion_mode')
    entry['router_pending_apply_required'] = controller_action_view.get('router_pending_apply_required')
    entry['action'] = controller_action_view
    entry['expected_receipt_path'] = receipt_rel
    write_json(action_path, entry)
    router._record_router_scheduler_row(project_root, run_root, run_state, action, entry)
    action['controller_action_id'] = action_id
    action['controller_action_path'] = project_relative(project_root, action_path)
    action['controller_receipt_path'] = project_relative(project_root, receipt_path)
    if isinstance(run_state.get('pending_action'), dict):
        pending = run_state['pending_action']
        if pending.get('action_id') == action.get('action_id') or pending.get('label') == action.get('label'):
            pending.update({'controller_action_id': action_id, 'controller_action_path': project_relative(project_root, action_path), 'controller_receipt_path': project_relative(project_root, receipt_path)})
    router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    if created:
        append_history(run_state, 'router_recorded_controller_action_entry', {'controller_action_id': action_id, 'action_type': action.get('action_type'), 'status': entry.get('status')})
    return entry

def _write_controller_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action_id: str, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    if status not in CONTROLLER_RECEIPT_STATUSES:
        raise RouterError(f'unsupported controller receipt status: {status}')
    action_path = _controller_action_path(run_root, action_id)
    action = read_json_if_exists(action_path)
    if action.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        raise RouterError(f'controller action is missing: {action_id}')
    receipt = {'schema_version': CONTROLLER_RECEIPT_SCHEMA, 'run_id': run_state.get('run_id'), 'action_id': action_id, 'action_type': action.get('action_type'), 'status': status, 'recorded_by': 'controller', 'recorded_at': utc_now(), 'controller_visibility': 'receipt_metadata_only', 'payload': payload or {}}
    write_json(_controller_receipt_path(run_root, action_id), receipt)
    _append_router_daemon_event(run_root, 'controller_receipt_recorded', {'action_id': action_id, 'status': status, 'receipt_path': project_relative(project_root, _controller_receipt_path(run_root, action_id))})
    router._reconcile_controller_receipts(project_root, run_root, run_state)
    return receipt

def _maybe_write_controller_receipt_for_pending(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any], *, status: str, payload: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    action_id = str(pending.get('controller_action_id') or '')
    if not action_id:
        return None
    return router._write_controller_receipt(project_root, run_root, run_state, action_id=action_id, status=status, payload=payload)

def _reconcile_controller_receipts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    receipt_dir = _controller_receipts_dir(run_root)
    reconciled = 0
    blocked = 0
    if receipt_dir.exists():
        for receipt_path in sorted(receipt_dir.glob('*.json')):
            receipt = read_json_if_exists(receipt_path)
            if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA:
                continue
            action_id = str(receipt.get('action_id') or '')
            status = str(receipt.get('status') or '')
            if not action_id or status not in CONTROLLER_RECEIPT_STATUSES:
                continue
            action_path = _controller_action_path(run_root, action_id)
            action = read_json_if_exists(action_path)
            if action.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
                continue
            previous_status = str(action.get('status') or '')
            preserve_router_status = status == 'done' and previous_status in CONTROLLER_ACTION_RECEIPT_PRESERVED_STATUSES
            if preserve_router_status:
                action['receipt_status'] = status
            else:
                action['status'] = status
            action['receipt_path'] = project_relative(project_root, receipt_path)
            action['receipt_recorded_at'] = receipt.get('recorded_at')
            action['updated_at'] = utc_now()
            if status == 'done' and (not preserve_router_status):
                action['completed_at'] = receipt.get('recorded_at')
            if status == 'blocked':
                blocked += 1
                action['blocked_at'] = receipt.get('recorded_at')
                action['blocked_payload'] = receipt.get('payload') or {}
            write_json(action_path, action)
            row_id = str(action.get('router_scheduler_row_id') or '')
            if row_id:
                router_state = 'waiting' if preserve_router_status and previous_status == 'repair_pending' else 'superseded' if preserve_router_status and previous_status == 'superseded' else 'reconciled' if preserve_router_status and previous_status == 'resolved' else 'receipt_done' if status == 'done' else 'blocked' if status == 'blocked' else 'skipped' if status == 'skipped' else 'waiting'
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state=router_state, reconciliation={'receipt_status': status, 'receipt_path': project_relative(project_root, receipt_path), 'receipt_recorded_at': receipt.get('recorded_at')})
            reconciled += 1
    ledger = router._rebuild_controller_action_ledger(project_root, run_root, run_state)
    return {'reconciled_receipts': reconciled, 'blocked_receipts': blocked, 'ledger_counts': ledger.get('counts')}

__all__ = (
    '_write_controller_action_entry',
    '_write_controller_receipt',
    '_maybe_write_controller_receipt_for_pending',
    '_reconcile_controller_receipts',
)

_LOCAL_NAMES = set(globals())
