"""Controller receipt postcondition effect helpers.

Receives the router facade explicitly so shared state writers and
public entrypoints keep the bound-router contract.
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
import flowpilot_router_action_handlers
import flowpilot_router_controller_scheduler_receipts_bootloader as bootloader_receipts
from flowpilot_control_plane_contracts import ROUTER_OWNED_STATE_REPLAY_ACTION_TYPES
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_controller_scheduler_receipts_packet_folds import (
    CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY,
    _apply_registered_controller_receipt_evidence_fold,
)

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
    for child_module in globals().get('_OWNER_CHILD_MODULES', ()):
        if hasattr(child_module, '_bind_router'):
            child_module._bind_router(router)


def _apply_stateful_receipt_postcondition(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(pending_action.get('action_type') or '')
    startup_bootloader_receipt = router._apply_startup_bootloader_receipt_effects(project_root, run_root, run_state, pending_action, receipt_payload)
    if startup_bootloader_receipt.get('applied') or startup_bootloader_receipt.get('reason') != 'not_bootloader_action':
        return startup_bootloader_receipt
    durable_reclaim = _reclaim_router_owned_postcondition_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload)
    if durable_reclaim.get('applied') or durable_reclaim.get('action_class', {}).get('kind') == 'router_owned_durable_artifact':
        return durable_reclaim
    if action_type == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        repair_target_action_type = str(pending_action.get('repair_target_action_type') or '').strip()
        if repair_target_action_type in CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY:
            original_id = str(pending_action.get('repair_of_controller_action_id') or '').strip()
            original_entry = read_json_if_exists(_controller_action_path(run_root, original_id)) if original_id else {}
            original_action = original_entry.get('action') if isinstance(original_entry.get('action'), dict) else {}
            if not original_action:
                return {'applied': False, 'reason': 'controller_delivery_repair_missing_original_action', 'repair_target_action_type': repair_target_action_type, 'repair_of_controller_action_id': original_id}
            delivery_repair_fold = _apply_registered_controller_receipt_evidence_fold(router, project_root, run_root, run_state, original_action, receipt_payload)
            if delivery_repair_fold.get('applied'):
                delivery_repair_fold = dict(delivery_repair_fold)
                delivery_repair_fold['source'] = 'controller_delivery_repair_fold'
                delivery_repair_fold['repair_action_type'] = action_type
                delivery_repair_fold['repair_target_action_type'] = repair_target_action_type
                delivery_repair_fold['repair_of_controller_action_id'] = original_id
            return delivery_repair_fold
    delivery_evidence_fold = _apply_registered_controller_receipt_evidence_fold(router, project_root, run_root, run_state, pending_action, receipt_payload)
    if delivery_evidence_fold.get('applied') or delivery_evidence_fold.get('reason') != 'not_registered_controller_receipt_evidence_fold':
        return delivery_evidence_fold
    if action_type in ROUTER_OWNED_STATE_REPLAY_ACTION_TYPES:
        outcome = flowpilot_router_action_handlers.apply_registered_action(
            router,
            project_root,
            run_root,
            run_state,
            pending_action,
            action_type,
            receipt_payload,
        )
        if outcome is None:
            return {
                'applied': False,
                'reason': 'router_owned_state_replay_handler_missing',
                'action_type': action_type,
            }
        if outcome.early_return is not None:
            result = dict(outcome.early_return)
            result.setdefault('applied', True)
        else:
            result = {'applied': True, **outcome.result_extra}
        result.setdefault('postcondition', _pending_action_postcondition(pending_action))
        result['source'] = 'router_owned_state_replay_receipt'
        result['action_type'] = action_type
        return result
    if action_type == 'recover_role_bindings':
        if 'recovered_role_bindings' in receipt_payload or 'role_bindings' in receipt_payload:
            router._write_role_recovery_report(project_root, run_root, run_state, receipt_payload)
            return {'applied': True, 'postcondition': 'role_recovery_roles_restored', 'source': 'controller_receipt_role_recovery_report_write'}
        return router._reclaim_role_recovery_postcondition_from_report(project_root, run_root, run_state, source='controller_receipt_role_recovery_report_reclaim')
    if action_type == 'rehydrate_role_bindings':
        has_rehydration_payload = 'rehydrated_role_bindings' in receipt_payload or 'role_bindings' in receipt_payload
        has_report_reference = any(
            isinstance(receipt_payload.get(key), str) and str(receipt_payload.get(key)).strip()
            for key in ('role_binding_recovery_report_path', 'report_path', 'rehydration_report_path')
        )
        if has_report_reference or not has_rehydration_payload:
            reclaim = router._reclaim_resume_rehydration_postcondition_from_report(
                project_root,
                run_root,
                run_state,
                source='controller_receipt_resume_rehydration_report_reclaim',
                payload=receipt_payload,
            )
            if reclaim.get('applied'):
                return reclaim
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
        ledger['updated_at'] = utc_now()
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
            current_last_reminder_at = str(pending.get('last_wait_reminder_at') or '')
            stale_replay = bool(current_last_reminder_at and delivered_at <= current_last_reminder_at)
            if not stale_replay:
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
    return bootloader_receipts._boot_action_meta(router, action_type)

def _matching_bootstrap_pending_action(router: ModuleType, bootstrap_state: dict[str, Any], action: dict[str, Any]) -> bool:
    return bootloader_receipts._matching_bootstrap_pending_action(router, bootstrap_state, action)

def _apply_startup_bootloader_receipt_effects(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any]) -> dict[str, Any]:
    return bootloader_receipts._apply_startup_bootloader_receipt_effects(
        router,
        project_root,
        run_root,
        run_state,
        action,
        receipt_payload,
    )

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

_OWNER_CHILD_MODULES = (bootloader_receipts,)

_LOCAL_NAMES = set(globals())
