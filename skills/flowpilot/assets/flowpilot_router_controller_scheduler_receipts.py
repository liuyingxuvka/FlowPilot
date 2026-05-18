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
    now = utc_now()
    if existing.get('schema_version') == CONTROLLER_ACTION_SCHEMA:
        entry = existing
        entry['seen_count'] = int(entry.get('seen_count') or 0) + 1
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES:
            entry['status'] = entry.get('status') or _controller_action_initial_status(action)
    else:
        created = True
        entry = {'schema_version': CONTROLLER_ACTION_SCHEMA, 'action_id': action_id, 'run_id': run_state.get('run_id'), 'action_type': action.get('action_type'), 'label': action.get('label'), 'summary': action.get('summary'), 'status': _controller_action_initial_status(action), 'created_at': now, 'seen_count': 1, 'source_action_id': action.get('action_id'), 'to_role': action.get('to_role'), 'allowed_reads': action.get('allowed_reads') or [], 'allowed_writes': action.get('allowed_writes') or [], 'allowed_external_events': action.get('allowed_external_events') or [], 'dependencies': [], 'router_scheduler_row_id': action.get('router_scheduler_row_id'), 'scope_kind': action.get('scope_kind'), 'scope_id': action.get('scope_id'), 'controller_visibility': 'router_action_metadata_only', 'sealed_body_reads_allowed': bool(action.get('sealed_body_reads_allowed', False)), 'action_path': project_relative(project_root, action_path), 'expected_receipt_path': receipt_rel, 'controller_receipt_required': controller_receipt_required, 'controller_projection_kind': projection_kind, 'ordinary_controller_work_row': not passive_wait_status, 'router_must_not_mark_done_without_controller_receipt': controller_receipt_required, 'action': action}
    entry['updated_at'] = now
    entry['last_seen_at'] = now
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

def _apply_stateful_receipt_postcondition(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(pending_action.get('action_type') or '')
    startup_bootloader_receipt = router._apply_startup_bootloader_receipt_effects(project_root, run_root, run_state, pending_action, receipt_payload)
    if startup_bootloader_receipt.get('applied') or startup_bootloader_receipt.get('reason') != 'not_bootloader_action':
        return startup_bootloader_receipt
    durable_reclaim = _reclaim_router_owned_postcondition_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload)
    if durable_reclaim.get('applied') or durable_reclaim.get('action_class', {}).get('kind') == 'router_owned_durable_artifact':
        return durable_reclaim
    if action_type == 'load_role_recovery_state':
        router._load_role_recovery_state(project_root, run_root, run_state)
        return {'applied': True, 'postcondition': 'role_recovery_state_loaded'}
    if action_type == 'recover_role_agents':
        if 'recovered_role_agents' in receipt_payload or 'role_agents' in receipt_payload:
            router._write_role_recovery_report(project_root, run_root, run_state, receipt_payload)
            return {'applied': True, 'postcondition': 'role_recovery_roles_restored', 'source': 'controller_receipt_role_recovery_report_write'}
        return router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='controller_receipt_role_recovery_report_reclaim')
    if action_type == 'rehydrate_role_agents':
        router._write_resume_role_rehydration_report(project_root, run_root, run_state, receipt_payload)
        return {'applied': True, 'postcondition': 'resume_roles_restored'}
    if action_type == 'confirm_controller_core_boundary' or (action_type == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and str(pending_action.get('repair_target_action_type') or '') == 'confirm_controller_core_boundary'):
        return _sync_controller_boundary_confirmation_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload, source='controller_receipt_reconciliation')
    if action_type == 'write_display_surface_status':
        confirmation = router._display_confirmation_for_action(receipt_payload, pending_action)
        router._write_display_surface_status(project_root, run_root, run_state, confirmation, receipt_payload)
        router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
        run_state.setdefault('flags', {})['startup_display_status_written'] = True
        return {'applied': True, 'postcondition': 'startup_display_status_written'}
    if action_type == 'deliver_mail':
        return _fold_mail_delivery_postcondition(project_root, run_root, run_state, pending_action, receipt_payload, source='controller_receipt_mail_delivery_fold')
    return {'applied': False, 'reason': 'unsupported_stateful_controller_receipt', 'action_type': action_type}

def _pending_return_matches_wait_target_reminder(router: ModuleType, record: dict[str, Any], action: dict[str, Any]) -> bool:
    _bind_router(router)
    expected_return_path = str(action.get('expected_return_path') or '')
    target_role = str(action.get('target_role') or action.get('waiting_for_role') or '')
    if expected_return_path and str(record.get('expected_return_path') or '') == expected_return_path:
        return True
    if target_role and str(record.get('target_role') or '') != target_role:
        return False
    for key in ('card_bundle_id', 'delivery_attempt_id', 'card_id', 'card_return_event'):
        action_value = str(action.get(key) or '')
        if action_value and str(record.get(key) or '') == action_value:
            return True
    source_identity = action.get('source_wait_identity') if isinstance(action.get('source_wait_identity'), dict) else {}
    identity_expected_path = str(source_identity.get('expected_return_path') or '')
    return bool(identity_expected_path and str(record.get('expected_return_path') or '') == identity_expected_path)

def _mark_pending_return_wait_reminded(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any], *, delivered_at: str, reminder_hash: str, receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    ledger = _read_return_event_ledger(run_root, run_id)
    changed = False
    reminded_ids: list[str] = []
    for record in ledger.setdefault('pending_returns', []):
        if not isinstance(record, dict):
            continue
        if not router._pending_return_matches_wait_target_reminder(record, action):
            continue
        if record.get('status') in {None, 'pending', 'awaiting_return', 'returned'}:
            record['status'] = 'reminded'
        record['last_wait_reminder_at'] = delivered_at
        record['last_wait_reminder_sha256'] = reminder_hash
        history = record.setdefault('wait_reminder_history', [])
        if isinstance(history, list):
            history.append({'at': delivered_at, 'reminder_text_sha256': reminder_hash, 'controller_action_id': action.get('controller_action_id'), 'delivered_to_role': receipt_payload.get('delivered_to_role')})
        reminded_ids.append(str(record.get('return_id') or record.get('card_bundle_id') or record.get('delivery_attempt_id') or ''))
        changed = True
    if changed:
        write_json(_return_event_ledger_path(run_root), ledger)
    return {'changed': changed, 'reminded_return_ids': [item for item in reminded_ids if item]}

def _apply_wait_target_reminder_receipt(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del project_root
    target_role = str(action.get('target_role') or action.get('waiting_for_role') or '').strip()
    delivered_to = str(receipt_payload.get('delivered_to_role') or receipt_payload.get('target_role') or '').strip()
    if target_role and delivered_to != target_role:
        return {'applied': False, 'reason': 'wait_target_reminder_wrong_role', 'target_role': target_role, 'delivered_to_role': delivered_to or None}
    expected_hash = str(action.get('reminder_text_sha256') or '')
    actual_hash = str(receipt_payload.get('reminder_text_sha256') or '')
    if not expected_hash or actual_hash != expected_hash:
        return {'applied': False, 'reason': 'wait_target_reminder_text_hash_mismatch', 'expected_reminder_text_sha256': expected_hash or None, 'actual_reminder_text_sha256': actual_hash or None}
    if receipt_payload.get('sealed_body_reads') is not False:
        return {'applied': False, 'reason': 'wait_target_reminder_sealed_body_boundary_not_confirmed'}
    delivered_at = str(receipt_payload.get('delivered_at') or utc_now())
    liveness_payload = receipt_payload.get('liveness_probe') if isinstance(receipt_payload.get('liveness_probe'), dict) else {}
    liveness_result = str(receipt_payload.get('liveness_probe_result') or liveness_payload.get('result') or '').strip()
    liveness_checked_at = str(receipt_payload.get('liveness_probe_checked_at') or liveness_payload.get('checked_at') or delivered_at)
    if action.get('fresh_liveness_probe_required') and (not liveness_result):
        return {'applied': False, 'reason': 'wait_target_reminder_missing_fresh_liveness_probe'}
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    pending_updated = False
    if pending and _action_is_passive_wait_status(pending):
        current_identity = router._wait_target_identity(pending, router._pending_wait_summary(run_state, project_root=None))
        if current_identity == action.get('source_wait_identity'):
            pending['last_wait_reminder_at'] = delivered_at
            pending['wait_reminder_text'] = action.get('reminder_text')
            pending['wait_reminder_text_sha256'] = expected_hash
            reminder_history = pending.setdefault('wait_reminder_history', [])
            if isinstance(reminder_history, list):
                reminder_history.append({'at': delivered_at, 'target_role': target_role, 'reminder_text_sha256': expected_hash, 'controller_action_id': action.get('controller_action_id')})
            if liveness_result:
                pending['last_liveness_probe'] = {'checked_at': liveness_checked_at, 'result': liveness_result, 'evidence_path': liveness_payload.get('evidence_path') or receipt_payload.get('liveness_probe_evidence_path')}
                pending['liveness_probe_result'] = liveness_result
            run_state['pending_action'] = pending
            pending_updated = True
    return_update = {'changed': False, 'reminded_return_ids': []}
    if str(action.get('wait_class') or '') == 'ack':
        return_update = router._mark_pending_return_wait_reminded(run_root, str(run_state['run_id']), action, delivered_at=delivered_at, reminder_hash=expected_hash, receipt_payload=receipt_payload)
    append_history(run_state, 'router_recorded_wait_target_reminder_receipt', {'target_role': target_role, 'wait_class': action.get('wait_class'), 'source_wait_action_type': action.get('source_wait_action_type'), 'pending_wait_updated': pending_updated, 'return_event_ledger_updated': return_update.get('changed')})
    return {'applied': True, 'source': 'wait_target_reminder_receipt', 'target_role': target_role, 'wait_class': action.get('wait_class'), 'delivered_at': delivered_at, 'pending_wait_updated': pending_updated, 'return_event_ledger_update': return_update}

def _boot_action_meta(router: ModuleType, action_type: str) -> dict[str, Any] | None:
    _bind_router(router)
    if action_type == 'load_router':
        return {'action_type': 'load_router', 'flag': 'router_loaded', 'label': 'bootloader_router_loaded', 'actor': 'bootloader'}
    for item in BOOT_ACTIONS:
        if item.get('action_type') == action_type:
            return item
    return None

def _matching_bootstrap_pending_action(router: ModuleType, bootstrap_state: dict[str, Any], action: dict[str, Any]) -> bool:
    _bind_router(router)
    pending = bootstrap_state.get('pending_action')
    if not isinstance(pending, dict):
        return False
    for key in ('controller_action_id', 'router_scheduler_row_id', 'action_id'):
        if pending.get(key) and pending.get(key) == action.get(key):
            return True
    return bool(pending.get('action_type') and pending.get('action_type') == action.get('action_type'))

def _apply_startup_bootloader_receipt_effects(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get('action_type') or '')
    action_meta = router._boot_action_meta(action_type)
    if action_meta is None:
        return {'applied': False, 'reason': 'not_bootloader_action'}
    if str(action.get('scope_kind') or '') != 'startup' and (not router._daemon_scheduled_bootloader_action(action)):
        return {'applied': False, 'reason': 'not_startup_bootloader_scheduler_row'}
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    flag = str(action_meta.get('flag') or _pending_action_postcondition(action) or '')
    result: dict[str, Any] = {'applied': True, 'source': 'startup_bootloader_controller_receipt', 'postcondition': flag, 'action_type': action_type}
    if action_type == 'open_startup_intake_ui' and str(receipt_payload.get('source') or '') != 'startup_daemon_bootloader_apply':
        result.update(router._apply_startup_intake_result_to_bootstrap(project_root, bootstrap, receipt_payload))
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
    elif action_type == 'emit_startup_banner':
        banner = router._startup_banner_display()
        confirmation = router._display_confirmation_for_action(receipt_payload, action)
        banner['dialog_display_confirmation'] = confirmation
        bootstrap['startup_banner_path'] = banner['display_path']
        bootstrap['startup_banner_display'] = banner
        bootstrap['startup_banner_dialog_display_confirmation'] = confirmation
        run_state.setdefault('flags', {})['banner_emitted'] = True
        result['display_text_sha256'] = confirmation.get('display_text_sha256')
    elif action_type == 'start_role_slots':
        role_slots = router._normalize_role_agent_records(bootstrap, receipt_payload)
        write_json(run_root / 'crew_ledger.json', {'schema_version': 'flowpilot.crew_ledger.v1', 'run_id': run_state['run_id'], 'background_agents_mode': (bootstrap.get('startup_answers') or {}).get('background_agents'), 'role_slots': role_slots, 'created_at': utc_now()})
        crew_memory_root = run_root / 'crew_memory'
        crew_memory_root.mkdir(parents=True, exist_ok=True)
        for role in CREW_ROLE_KEYS:
            write_json(crew_memory_root / f'{role}.json', router._create_empty_role_memory(str(run_state['run_id']), role))
        _append_role_io_protocol_injections(project_root, run_root, str(run_state['run_id']), role_slots, default_lifecycle_phase='fresh_spawn', resume_tick_id='manual-resume', source_action='start_role_slots')
        write_json(run_root / 'role_core_prompt_delivery.json', router._role_core_prompt_delivery_payload(project_root, run_root, str(run_state['run_id']), source_action='start_role_slots'))
        bootstrap.setdefault('flags', {})['role_core_prompts_injected'] = True
        run_state.setdefault('flags', {})['roles_started'] = True
        run_state.setdefault('flags', {})['role_core_prompts_injected'] = True
        result['coalesced_postconditions'] = ['roles_started', 'role_core_prompts_injected']
    elif action_type == 'create_heartbeat_automation':
        _write_host_heartbeat_binding(project_root, run_root, run_state, receipt_payload)
        run_state.setdefault('flags', {})['continuation_binding_recorded'] = True
        run_state.setdefault('events', []).append({'event': 'host_records_heartbeat_binding', 'summary': EXTERNAL_EVENTS['host_records_heartbeat_binding']['summary'], 'payload': receipt_payload, 'recorded_at': utc_now(), 'source_action': action_type, 'startup_phase': 'bootloader_controller_receipt'})
    elif action_type == 'load_controller_core':
        if not _formal_router_daemon_ready(project_root, run_root):
            return {'applied': False, 'reason': 'startup_router_daemon_not_ready_for_controller_core', 'action_type': action_type, 'postcondition': flag}
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        run_state['status'] = 'controller_ready'
        run_state['holder'] = 'controller'
        run_state.setdefault('flags', {})['controller_core_loaded'] = True
        boundary_reconciliation = router._record_controller_boundary_confirmation_from_core_load(project_root, run_root, run_state, action, receipt_payload, source='load_controller_core_receipt_reconciliation')
        result['controller_boundary_confirmation'] = boundary_reconciliation.get('controller_boundary_confirmation')
        result['coalesced_postconditions'] = sorted(set(result.get('coalesced_postconditions') or []) | {'controller_role_confirmed'})
        result['source'] = 'startup_bootloader_controller_receipt'
    elif str(receipt_payload.get('source') or '') == 'startup_daemon_bootloader_apply':
        bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
        if flag and (not (receipt_payload.get('bootstrap_flag_satisfied') or bootstrap_flags.get(flag))):
            return {'applied': False, 'reason': 'startup_bootloader_receipt_postcondition_missing', 'action_type': action_type, 'postcondition': flag}
        router._sync_startup_bootstrap_flags_to_run_state(bootstrap, run_state)
        result['bootstrap_flag_satisfied'] = bool(flag and bootstrap_flags.get(flag))
        result['source'] = 'startup_bootloader_controller_receipt'
    else:
        return {'applied': False, 'reason': 'unsupported_startup_bootloader_receipt_action', 'action_type': action_type}
    if flag:
        bootstrap.setdefault('flags', {})[flag] = True
        run_state.setdefault('flags', {})[flag] = True
    if router._matching_bootstrap_pending_action(bootstrap, action):
        bootstrap['pending_action'] = None
        result['cleared_bootstrap_pending_action'] = True
    append_history(bootstrap, 'router_reconciled_startup_bootloader_receipt', {'action_type': action_type, 'postcondition': flag, 'controller_action_id': action.get('controller_action_id'), 'router_scheduler_row_id': action.get('router_scheduler_row_id')})
    router.save_bootstrap_state(project_root, bootstrap)
    router.save_run_state(run_root, run_state)
    return result

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

def _apply_done_controller_receipt_effects(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    payload = receipt.get('payload') if isinstance(receipt.get('payload'), dict) else {}
    action_type = str(action.get('action_type') or receipt.get('action_type') or '')
    startup_bootloader_receipt = router._apply_startup_bootloader_receipt_effects(project_root, run_root, run_state, action, payload)
    if startup_bootloader_receipt.get('applied') or startup_bootloader_receipt.get('reason') != 'not_bootloader_action':
        return startup_bootloader_receipt
    if action_type == WAIT_TARGET_REMINDER_ACTION_TYPE:
        return router._apply_wait_target_reminder_receipt(project_root, run_root, run_state, action, payload)
    action_class = router._controller_action_completion_class(action)
    if action_class.get('kind') == 'display_status' and action_type == 'sync_display_plan':
        sync_payload = router._apply_sync_display_plan_state(project_root, run_root, run_state, action, payload)
        return {'applied': True, 'source': 'router_owned_display_status_reclaim', 'projection_hash': sync_payload.get('projection_hash'), 'display_plan_path': sync_payload.get('display_plan_path')}
    postcondition = _pending_action_postcondition(action)
    if postcondition and (not _pending_action_postcondition_satisfied(run_state, postcondition) or action_type == 'deliver_mail'):
        applied = router._apply_stateful_receipt_postcondition(project_root, run_root, run_state, action, payload)
        if not applied.get('applied') or not _pending_action_postcondition_satisfied(run_state, postcondition):
            repair = _schedule_controller_deliverable_repair(project_root, run_root, run_state, pending_action=action, receipt=receipt, apply_result=applied, source='scheduled_controller_action_receipt_missing_stateful_postcondition')
            if repair.get('scheduled') or repair.get('blocked'):
                result = {'applied': False, 'reason': 'deliverable_repair_scheduled' if repair.get('scheduled') else 'deliverable_repair_budget_exhausted', 'postcondition': postcondition, 'apply_result': applied, 'repair': repair}
                result['repair_scheduled'] = bool(repair.get('scheduled'))
                result['blocked'] = bool(repair.get('blocked'))
                return result
            if repair.get('pending_repair'):
                return {'applied': False, 'reason': 'deliverable_repair_pending', 'postcondition': postcondition, 'apply_result': applied, 'repair': repair, 'repair_pending': True}
            return {'applied': False, 'reason': 'postcondition_not_satisfied', 'postcondition': postcondition, 'apply_result': applied}
        if str(action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
            _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=action, receipt=receipt, applied_postcondition=applied)
        return applied
    if str(action.get('action_type') or '') == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and postcondition and _pending_action_postcondition_satisfied(run_state, postcondition):
        applied = {'applied': True, 'source': 'repair_postcondition_already_satisfied', 'postcondition': postcondition}
        _mark_controller_deliverable_repair_resolved(project_root, run_root, run_state, repair_action=action, receipt=receipt, applied_postcondition=applied)
        return applied
    return {'applied': True, 'source': 'controller_local_receipt'}

def _scheduler_row_reconciliation_for_entry(router: ModuleType, run_root: Path, entry: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return None
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    for row in scheduler.get('rows', []) if isinstance(scheduler.get('rows'), list) else []:
        if not isinstance(row, dict) or row.get('row_id') != row_id:
            continue
        reconciliation = row.get('reconciliation') if isinstance(row.get('reconciliation'), dict) else {}
        if row.get('router_state') == 'reconciled' and reconciliation.get('applied'):
            return dict(reconciliation)
    return None

def _backfill_scheduler_row_from_reconciled_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], *, source: str) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(entry.get('router_scheduler_row_id') or '').strip()
    if not row_id:
        return {'changed': False, 'reason': 'controller_action_has_no_router_scheduler_row'}
    if not (entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at')):
        return {'changed': False, 'reason': 'controller_action_not_reconciled'}
    row = router._router_scheduler_row_for_controller_entry(run_root, entry)
    if not row:
        return {'changed': False, 'reason': 'router_scheduler_row_missing', 'row_id': row_id}
    if row.get('router_state') == 'reconciled':
        return {'changed': False, 'reason': 'router_scheduler_row_already_reconciled', 'row_id': row_id}
    reconciliation = dict(entry.get('router_reconciliation')) if isinstance(entry.get('router_reconciliation'), dict) else {}
    reconciliation.setdefault('applied', True)
    reconciliation.setdefault('source', source)
    reconciliation['scheduler_backfill_source'] = source
    reconciliation['controller_action_id'] = str(entry.get('action_id') or '')
    reconciliation['controller_action_reconciliation_status'] = entry.get('router_reconciliation_status')
    if entry.get('router_reconciled_at'):
        reconciliation['controller_action_reconciled_at'] = entry.get('router_reconciled_at')
    router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=reconciliation)
    return {'changed': True, 'row_id': row_id, 'reconciliation': reconciliation}

def _canonicalize_legacy_startup_daemon_reconciliation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], action: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    current = entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else {}
    source = current.get('source')
    if source == 'startup_bootloader_controller_receipt' and current.get('postcondition'):
        return {'applied': False, 'reason': 'startup_receipt_owner_already_complete'}
    if source not in {'startup_daemon_bootloader_postcondition', 'startup_bootloader_controller_receipt'}:
        return {'applied': False, 'reason': 'not_legacy_startup_daemon_owner'}
    if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA or receipt.get('status') != 'done':
        return {'applied': False, 'reason': 'startup_receipt_missing_or_not_done'}
    if not router._daemon_scheduled_bootloader_action(action):
        return {'applied': False, 'reason': 'not_daemon_scheduled_bootloader_action'}
    action_type = str(action.get('action_type') or entry.get('action_type') or '')
    action_meta = router._boot_action_meta(action_type)
    if action_meta is None:
        return {'applied': False, 'reason': 'not_bootloader_action'}
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    flag = str(action_meta.get('flag') or _pending_action_postcondition(action) or '')
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    run_flags = run_state.setdefault('flags', {})
    if flag and (not (bootstrap_flags.get(flag) or run_flags.get(flag))):
        return {'applied': False, 'reason': 'legacy_startup_postcondition_not_satisfied', 'postcondition': flag, 'action_type': action_type}
    if flag:
        run_flags[flag] = True
    canonical = dict(current)
    canonical.update({'applied': True, 'source': 'startup_bootloader_controller_receipt', 'canonicalized_from': source, 'controller_receipt_path': project_relative(project_root, _controller_receipt_path(run_root, str(receipt.get('action_id') or entry.get('action_id') or ''))), 'postcondition': flag, 'bootstrap_postcondition': current.get('bootstrap_postcondition') or flag, 'bootstrap_flag_satisfied': True})
    return canonical

def _reconcile_scheduled_controller_action_receipts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {'changed': False, 'reconciled': 0, 'blocked': 0}
    changed = False
    reconciled = 0
    blocked = 0
    for action_path in sorted(action_dir.glob('*.json')):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        row_reconciliation = router._scheduler_row_reconciliation_for_entry(run_root, entry)
        action_id = str(entry.get('action_id') or action.get('controller_action_id') or '')
        receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id)) if action_id else {}
        legacy_startup_canonical = router._canonicalize_legacy_startup_daemon_reconciliation(project_root, run_root, run_state, entry, action, receipt)
        if legacy_startup_canonical.get('applied'):
            now = utc_now()
            entry['status'] = 'done'
            entry['completed_at'] = entry.get('completed_at') or now
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = now
            entry['router_reconciliation'] = legacy_startup_canonical
            entry['router_pending_apply_required'] = False
            if isinstance(entry.get('action'), dict):
                entry['action']['router_pending_apply_required'] = False
            write_json(action_path, entry)
            row_id = str(entry.get('router_scheduler_row_id') or '')
            if row_id:
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=legacy_startup_canonical)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=legacy_startup_canonical)
            changed = True
            reconciled += 1
            continue
        if row_reconciliation is not None and (not (entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'))):
            entry['status'] = 'done'
            entry['completed_at'] = entry.get('completed_at') or utc_now()
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = row_reconciliation
            write_json(action_path, entry)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action or {'action_type': entry.get('action_type')}, entry=entry, reconciliation=row_reconciliation)
            changed = True
            reconciled += 1
            continue
        if entry.get('status') not in CONTROLLER_ACTION_CLOSED_STATUSES and _card_return_resolved_for_action(run_root, str(run_state['run_id']), action):
            applied = {'applied': True, 'source': 'role_card_return_resolved_delivery_relay', 'card_id': action.get('card_id'), 'card_bundle_id': action.get('card_bundle_id'), 'delivery_attempt_id': action.get('delivery_attempt_id')}
            entry['status'] = 'done'
            entry['completed_at'] = utc_now()
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = applied
            write_json(action_path, entry)
            row_id = str(entry.get('router_scheduler_row_id') or '')
            if row_id:
                router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
            changed = True
            reconciled += 1
            continue
        if entry.get('status') != 'done':
            continue
        if entry.get('router_reconciliation_status') == 'reconciled' or entry.get('router_reconciled_at'):
            scheduler_backfill = router._backfill_scheduler_row_from_reconciled_controller_action(project_root, run_root, run_state, entry, source='reconciled_controller_action_scheduler_backfill')
            blocker_resolution = router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action or {'action_type': entry.get('action_type')}, entry=entry, reconciliation=entry.get('router_reconciliation') if isinstance(entry.get('router_reconciliation'), dict) else None)
            if scheduler_backfill.get('changed') or blocker_resolution.get('changed'):
                changed = True
                if scheduler_backfill.get('changed'):
                    reconciled += 1
            continue
        if entry.get('router_reconciliation_status') == 'blocked':
            postcondition = _pending_action_postcondition(action)
            action_type = str(action.get('action_type') or entry.get('action_type') or '')
            if action_type == 'recover_role_agents' or postcondition == 'role_recovery_roles_restored':
                applied = router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='blocked_controller_action_role_recovery_report_reclaim')
                if applied.get('applied') and (not postcondition or _pending_action_postcondition_satisfied(run_state, postcondition)):
                    now = utc_now()
                    entry['status'] = 'done'
                    entry['completed_at'] = entry.get('completed_at') or now
                    entry['router_reconciliation_status'] = 'reconciled'
                    entry['router_reconciled_at'] = now
                    entry['router_reconciliation'] = applied
                    entry['router_reconciliation_recovered_from_blocked_state'] = True
                    write_json(action_path, entry)
                    row_id = str(entry.get('router_scheduler_row_id') or '')
                    if row_id:
                        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
                    router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=applied)
                    changed = True
                    reconciled += 1
                    continue
            continue
        if not action:
            continue
        if row_reconciliation is not None:
            entry['router_reconciliation_status'] = 'reconciled'
            entry['router_reconciled_at'] = utc_now()
            entry['router_reconciliation'] = row_reconciliation
            write_json(action_path, entry)
            router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=row_reconciliation)
            changed = True
            reconciled += 1
            continue
        if receipt.get('schema_version') != CONTROLLER_RECEIPT_SCHEMA or receipt.get('status') != 'done':
            continue
        try:
            applied = router._apply_done_controller_receipt_effects(project_root, run_root, run_state, action, receipt)
        except RouterLedgerWriteInProgress:
            raise
        except (RouterError, ValueError, OSError, json.JSONDecodeError) as exc:
            applied = {'applied': False, 'reason': str(exc)}
        if not applied.get('applied'):
            if applied.get('repair_scheduled'):
                changed = True
                continue
            if applied.get('blocked'):
                blocked += 1
                changed = True
                continue
            if applied.get('repair_pending'):
                changed = True
                continue
            retry = _defer_controller_postcondition_reconciliation_retry(project_root, run_root, run_state, entry=entry, action=action, apply_result=applied)
            if retry.get('retry_pending'):
                changed = True
                continue
            blocked += 1
            retry_exhausted = bool(retry.get('retry_budget_exhausted'))
            if retry_exhausted:
                entry['postcondition_reconciliation_exhausted'] = True
                entry['max_postcondition_reconciliation_attempts'] = retry.get('direct_retry_budget')
            entry['router_reconciliation_status'] = 'blocked'
            entry['router_reconciliation_blocked_at'] = utc_now()
            entry['router_reconciliation_blocker'] = applied
            write_json(action_path, entry)
            router._write_control_blocker(project_root, run_root, run_state, source=CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE, error_message=f"Controller action {entry.get('action_type')} was marked done, but Router could not apply its required postcondition before reconciliation.", action_type=str(entry.get('action_type') or ''), payload={'controller_action_id': action_id, 'router_scheduler_row_id': entry.get('router_scheduler_row_id'), 'postcondition': retry.get('postcondition') or applied.get('postcondition'), 'direct_retry_attempts_used': retry.get('direct_retry_attempts_used'), 'direct_retry_budget': retry.get('direct_retry_budget'), 'direct_retry_budget_exhausted': retry_exhausted, 'apply_result': applied})
            changed = True
            continue
        entry['router_reconciliation_status'] = 'reconciled'
        entry['router_reconciled_at'] = utc_now()
        entry['router_reconciliation'] = applied
        write_json(action_path, entry)
        row_id = str(entry.get('router_scheduler_row_id') or '')
        if row_id:
            router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation=applied)
        router._resolve_control_blockers_for_reconciled_controller_action(project_root, run_root, run_state, action=action, entry=entry, reconciliation=applied)
        changed = True
        reconciled += 1
    if changed:
        router._rebuild_controller_action_ledger(project_root, run_root, run_state)
        router._refresh_route_memory(project_root, run_root, run_state, trigger='after_scheduled_controller_receipt_reconciliation')
        router._sync_derived_run_views(project_root, run_root, run_state, reason='after_scheduled_controller_receipt_reconciliation', update_display=True)
        router.save_run_state(run_root, run_state)
    return {'changed': changed, 'reconciled': reconciled, 'blocked': blocked}

__all__ = (
    '_write_controller_action_entry',
    '_write_controller_receipt',
    '_maybe_write_controller_receipt_for_pending',
    '_reconcile_controller_receipts',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_apply_stateful_receipt_postcondition',
    '_pending_return_matches_wait_target_reminder',
    '_mark_pending_return_wait_reminded',
    '_apply_wait_target_reminder_receipt',
    '_boot_action_meta',
    '_matching_bootstrap_pending_action',
    '_apply_startup_bootloader_receipt_effects',
    '_clear_pending_after_reconciled_controller_receipt',
    '_reconcile_pending_controller_action_receipt',
    '_apply_done_controller_receipt_effects',
    '_scheduler_row_reconciliation_for_entry',
    '_backfill_scheduler_row_from_reconciled_controller_action',
    '_canonicalize_legacy_startup_daemon_reconciliation',
    '_reconcile_scheduled_controller_action_receipts',
)

_LOCAL_NAMES = set(globals())
