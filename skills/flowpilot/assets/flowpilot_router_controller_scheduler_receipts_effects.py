"""Controller receipt postcondition effect helpers.

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
    terminal_mode = router._terminal_lifecycle_mode(run_state)
    if terminal_mode:
        append_history(
            run_state,
            'startup_bootloader_receipt_ignored_for_terminal_lifecycle',
            {'action_type': action_type, 'terminal_lifecycle_status': terminal_mode},
        )
        result.update({'source': 'terminal_lifecycle_skipped_startup_receipt', 'terminal_lifecycle_status': terminal_mode})
        return result
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

__all__ = (
    '_apply_stateful_receipt_postcondition',
    '_pending_return_matches_wait_target_reminder',
    '_mark_pending_return_wait_reminded',
    '_apply_wait_target_reminder_receipt',
    '_boot_action_meta',
    '_matching_bootstrap_pending_action',
    '_apply_startup_bootloader_receipt_effects',
    '_apply_done_controller_receipt_effects',
)

_LOCAL_NAMES = set(globals())
