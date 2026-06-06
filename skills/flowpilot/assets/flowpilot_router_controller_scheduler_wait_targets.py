"""Wait-target summaries, due-state, reminders, and reminder actions."""

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

def _elapsed_seconds_since(router: ModuleType, raw_timestamp: object, *, now: datetime | None=None) -> int | None:
    _bind_router(router)
    parsed = _parse_utc_timestamp(raw_timestamp)
    if parsed is None:
        return None
    current = now or datetime.now(timezone.utc)
    return max(0, int((current - parsed).total_seconds()))

def _wait_target_path_exists(router: ModuleType, project_root: Path | None, raw_path: object) -> bool:
    _bind_router(router)
    if project_root is None or not isinstance(raw_path, str) or (not raw_path.strip()):
        return False
    return resolve_project_path(project_root, raw_path).exists()

def _pending_wait_class(router: ModuleType, pending: dict[str, Any]) -> str:
    _bind_router(router)
    explicit = str(pending.get('wait_class') or pending.get('wait_target_class') or '').strip()
    if explicit in {'ack', 'report_result', 'controller_local_action', 'router_reconciliation', 'none'}:
        return explicit
    action_type = str(pending.get('action_type') or '')
    if action_type in {'await_card_return_event', 'await_card_bundle_return_event', 'check_card_return_event', 'check_card_bundle_return_event', 'deliver_system_card', 'deliver_system_card_bundle'}:
        return 'ack'
    if action_type == 'await_role_decision':
        return 'report_result'
    if action_type == 'await_current_scope_reconciliation':
        return 'router_reconciliation'
    if action_type:
        return 'controller_local_action'
    return 'none'

def _wait_target_reminder_text(router: ModuleType, wait_class: str, target_role: str, wait_reason: str) -> str | None:
    _bind_router(router)
    if wait_class == 'ack':
        return f"Router is still waiting for {target_role or 'the target role'} to acknowledge {wait_reason or 'the assigned card'}. If you received it, submit the ACK through the original runtime path. If you are blocked, submit a blocker."
    if wait_class == 'report_result':
        return f"Router is still waiting for {target_role or 'the target role'} to finish {wait_reason or 'the assigned work'}. If you are still working, continue. If finished, submit through the original runtime path. If blocked, submit a blocker. Do not paste sealed report or result bodies into chat."
    return None

def _wait_target_due_state(router: ModuleType, *, wait_class: str, elapsed_seconds: int | None, last_reminder_elapsed_seconds: int | None, evidence_exists: bool, liveness_probe_result: str) -> dict[str, Any]:
    _bind_router(router)
    reminder_due = False
    blocker_required = False
    blocker_reason = None
    reissue_required = False
    reissue_reason = None
    liveness_check_due = False
    reminder_interval_seconds = None
    blocker_after_seconds = None
    next_due_seconds = None
    next_due_reason = None
    if wait_class == 'ack':
        reminder_interval_seconds = WAIT_TARGET_ACK_REMINDER_SECONDS
        blocker_after_seconds = WAIT_TARGET_ACK_BLOCKER_SECONDS
        if not evidence_exists and elapsed_seconds is not None:
            reminder_due = elapsed_seconds >= WAIT_TARGET_ACK_REMINDER_SECONDS and (last_reminder_elapsed_seconds is None or last_reminder_elapsed_seconds >= WAIT_TARGET_ACK_REMINDER_SECONDS)
            blocker_required = elapsed_seconds >= WAIT_TARGET_ACK_BLOCKER_SECONDS
            if blocker_required:
                blocker_reason = 'ack_missing_after_ten_minutes'
            if blocker_required:
                next_due_seconds = 0
                next_due_reason = 'ack_blocker'
            elif reminder_due:
                next_due_seconds = 0
                next_due_reason = 'ack_reminder'
            else:
                candidates: list[tuple[int, str]] = []
                if last_reminder_elapsed_seconds is None:
                    candidates.append((WAIT_TARGET_ACK_REMINDER_SECONDS - elapsed_seconds, 'ack_reminder'))
                else:
                    candidates.append((WAIT_TARGET_ACK_REMINDER_SECONDS - last_reminder_elapsed_seconds, 'ack_reminder'))
                candidates.append((WAIT_TARGET_ACK_BLOCKER_SECONDS - elapsed_seconds, 'ack_blocker'))
                next_due_seconds, next_due_reason = min(((max(0, seconds), reason) for seconds, reason in candidates), key=lambda item: item[0])
    elif wait_class == 'report_result':
        reminder_interval_seconds = WAIT_TARGET_REPORT_REMINDER_SECONDS
        if not evidence_exists and elapsed_seconds is not None:
            reminder_due = elapsed_seconds >= WAIT_TARGET_REPORT_REMINDER_SECONDS and (last_reminder_elapsed_seconds is None or last_reminder_elapsed_seconds >= WAIT_TARGET_REPORT_REMINDER_SECONDS)
            liveness_check_due = reminder_due
        if liveness_probe_result in WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS:
            reissue_required = True
            reissue_reason = f'role_no_output_{liveness_probe_result}'
        elif liveness_probe_result in WAIT_TARGET_UNHEALTHY_LIVENESS_RESULTS:
            blocker_required = True
            blocker_reason = f'role_liveness_{liveness_probe_result}'
        if blocker_required:
            next_due_seconds = 0
            next_due_reason = 'role_liveness_blocker'
        elif reissue_required:
            next_due_seconds = 0
            next_due_reason = 'role_no_output_reissue'
        elif reminder_due or liveness_check_due:
            next_due_seconds = 0
            next_due_reason = 'report_reminder_liveness_check'
        elif not evidence_exists and elapsed_seconds is not None:
            if last_reminder_elapsed_seconds is None:
                next_due_seconds = max(0, WAIT_TARGET_REPORT_REMINDER_SECONDS - elapsed_seconds)
            else:
                next_due_seconds = max(0, WAIT_TARGET_REPORT_REMINDER_SECONDS - last_reminder_elapsed_seconds)
            next_due_reason = 'report_reminder_liveness_check'
    elif wait_class == 'controller_local_action':
        reminder_due = False
        liveness_check_due = False
        next_due_seconds = 0
        next_due_reason = 'controller_local_self_audit'
    return {'reminder_interval_seconds': reminder_interval_seconds, 'blocker_after_seconds': blocker_after_seconds, 'reminder_due': reminder_due, 'liveness_check_due': liveness_check_due, 'blocker_required': blocker_required, 'blocker_reason': blocker_reason, 'reissue_required': reissue_required, 'reissue_reason': reissue_reason, 'next_due_seconds': next_due_seconds, 'next_due_reason': next_due_reason}

def _pending_wait_summary(router: ModuleType, run_state: dict[str, Any], *, project_root: Path | None=None) -> dict[str, Any]:
    _bind_router(router)
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    wait_class = router._pending_wait_class(pending)
    target_role = str(pending.get('waiting_for_role') or pending.get('to_role') or '').strip()
    wait_reason = str(pending.get('wait_reason') or pending.get('summary') or pending.get('label') or '').strip()
    expected_return_path = pending.get('expected_return_path')
    started_at = pending.get('wait_started_at') or pending.get('created_at') or pending.get('updated_at')
    last_reminder_at = pending.get('last_wait_reminder_at')
    last_liveness_probe = pending.get('last_liveness_probe')
    if not isinstance(last_liveness_probe, dict):
        last_liveness_probe = {}
    liveness_probe_result = str(pending.get('liveness_probe_result') or last_liveness_probe.get('result') or 'none')
    elapsed_seconds = router._elapsed_seconds_since(started_at)
    last_reminder_elapsed_seconds = router._elapsed_seconds_since(last_reminder_at)
    evidence_exists = router._wait_target_path_exists(project_root, expected_return_path)
    due_state = router._wait_target_due_state(wait_class=wait_class, elapsed_seconds=elapsed_seconds, last_reminder_elapsed_seconds=last_reminder_elapsed_seconds, evidence_exists=evidence_exists, liveness_probe_result=liveness_probe_result)
    return {'action_type': pending.get('action_type'), 'label': pending.get('label'), 'to_role': pending.get('to_role'), 'waiting_for_role': pending.get('waiting_for_role') or pending.get('to_role'), 'allowed_external_events': pending.get('allowed_external_events') or [], 'expected_return_path': expected_return_path, 'controller_action_id': pending.get('controller_action_id'), 'resource_lifecycle': pending.get('resource_lifecycle'), 'artifact_committed': pending.get('artifact_committed'), 'relay_allowed': pending.get('relay_allowed'), 'wait_class': wait_class, 'target_role': target_role or None, 'wait_reason': wait_reason or None, 'started_at': started_at, 'elapsed_seconds': elapsed_seconds, 'expected_evidence': {'path': expected_return_path, 'exists': evidence_exists, 'controller_visible_only': True}, 'reminder': {'text': pending.get('wait_reminder_text') or router._wait_target_reminder_text(wait_class, target_role, wait_reason), 'last_sent_at': last_reminder_at, 'due': due_state['reminder_due'], 'interval_seconds': due_state['reminder_interval_seconds'], 'controller_must_use_router_authored_text': True}, 'liveness_probe': {'required': wait_class == 'report_result' and bool(target_role), 'due': due_state['liveness_check_due'], 'target_role': target_role or None, 'last_checked_at': last_liveness_probe.get('checked_at'), 'last_result': liveness_probe_result, 'last_evidence_path': last_liveness_probe.get('evidence_path'), 'current_liveness_is_not_cached_authority': True}, 'controller_local_self_audit': {'required': wait_class == 'controller_local_action', 'reminder_allowed': False, 'check_action_ledger': True, 'check_receipts': True}, 'next_due': {'seconds': due_state['next_due_seconds'], 'reason': due_state['next_due_reason'], 'strict_wait_until_due': wait_class in {'ack', 'report_result', 'controller_local_action'}}, 'reissue': {'required': due_state['reissue_required'], 'reason': due_state['reissue_reason'], 'event': 'controller_reports_role_no_output' if due_state['reissue_required'] else None, 'record_event_payload': {'role_key': target_role, 'target_role_keys': [target_role] if target_role else [], 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'expected_return_path': expected_return_path, 'liveness_probe_result': liveness_probe_result, 'elapsed_seconds': elapsed_seconds, 'current_controller_action_id': pending.get('controller_action_id'), 'router_scheduler_row_id': pending.get('router_scheduler_row_id')} if due_state['reissue_required'] else None, 'same_work_reissue_before_role_recovery': bool(due_state['reissue_required']), 'pm_recovery_required': False}, 'blocker': {'required': due_state['blocker_required'], 'reason': due_state['blocker_reason'], 'event': 'controller_reports_role_liveness_fault' if due_state['blocker_required'] else None, 'record_event_payload': {'role_key': target_role, 'target_role_keys': [target_role] if target_role else [], 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'expected_return_path': expected_return_path, 'liveness_probe_result': liveness_probe_result, 'elapsed_seconds': elapsed_seconds} if due_state['blocker_required'] else None, 'pm_recovery_required': bool(due_state['blocker_required'])}}

def _wait_target_reminder_text_sha256(router: ModuleType, reminder_text: str) -> str:
    _bind_router(router)
    return hashlib.sha256(reminder_text.encode('utf-8')).hexdigest()

def _wait_target_identity(router: ModuleType, pending: dict[str, Any], current_wait: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'action_type': pending.get('action_type') or current_wait.get('action_type'), 'label': pending.get('label') or current_wait.get('label'), 'wait_class': current_wait.get('wait_class'), 'target_role': current_wait.get('target_role') or current_wait.get('waiting_for_role'), 'expected_return_path': current_wait.get('expected_return_path'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'source_wait_action_id': pending.get('action_id'), 'source_wait_controller_action_id': pending.get('controller_action_id'), 'wait_started_at': current_wait.get('started_at') or pending.get('created_at')}

def _wait_target_reminder_payload_contract(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return _payload_contract(name='wait_target_reminder_receipt', required_object='payload', required_fields=['target_role', 'delivered_to_role', 'reminder_text_sha256', 'sealed_body_reads'], optional_fields=['delivered_at', 'delivery_channel', 'liveness_probe', 'liveness_probe_result', 'liveness_probe_checked_at'], allowed_values={'sealed_body_reads': [False]}, conditional_required_fields={'when fresh_liveness_probe_required=true': ['liveness_probe.result', 'liveness_probe.checked_at']}, structural_requirements=['reminder_text_sha256 must match the Router-authored reminder_text on the action row', 'Controller must send the reminder_text exactly as supplied and must not paste sealed result bodies', 'target_role and delivered_to_role must name the wait target role'], description="Receipt proving Controller sent the Router-authored wait reminder to the current waiting role. This records reminder delivery only; it does not satisfy the role's original ACK or result-return obligation.")

def _next_wait_target_reminder_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    if not _action_is_passive_wait_status(pending_action):
        return None
    current_wait = current_wait or router._pending_wait_summary(run_state, project_root=project_root)
    wait_class = str(current_wait.get('wait_class') or '')
    if wait_class not in {'ack', 'report_result'}:
        return None
    if (current_wait.get('blocker') or {}).get('required'):
        return None
    reminder = current_wait.get('reminder') if isinstance(current_wait.get('reminder'), dict) else {}
    liveness_probe = current_wait.get('liveness_probe') if isinstance(current_wait.get('liveness_probe'), dict) else {}
    reminder_due = bool(reminder.get('due'))
    liveness_due = bool(liveness_probe.get('due'))
    if not (reminder_due or liveness_due):
        return None
    target_role = str(current_wait.get('target_role') or current_wait.get('waiting_for_role') or '').strip()
    if not target_role:
        return None
    wait_reason = str(current_wait.get('wait_reason') or pending_action.get('summary') or pending_action.get('label') or '').strip()
    reminder_text = str(reminder.get('text') or router._wait_target_reminder_text(wait_class, target_role, wait_reason) or '').strip()
    if not reminder_text:
        return None
    reminder_hash = router._wait_target_reminder_text_sha256(reminder_text)
    identity = router._wait_target_identity(pending_action, current_wait)
    last_sent = str(reminder.get('last_sent_at') or pending_action.get('last_wait_reminder_at') or 'initial')
    safe_target = _safe_delivery_component(target_role)
    safe_wait_class = _safe_delivery_component(wait_class)
    label = f'controller_sends_wait_target_reminder_{safe_target}_{safe_wait_class}'
    return make_action(action_type=WAIT_TARGET_REMINDER_ACTION_TYPE, actor='controller', label=label, summary=f'Send the Router-authored {wait_class} wait reminder to {target_role}. This is a generic wait-target reminder action, not completion of the original wait.', allowed_reads=[project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], allowed_writes=[], extra={'controller_side_effect_required': True, 'target_role': target_role, 'waiting_for_role': target_role, 'waiting_for_agent_id': pending_action.get('waiting_for_agent_id'), 'wait_class': wait_class, 'wait_reason': wait_reason or None, 'source_wait_identity': identity, 'source_wait_action_type': pending_action.get('action_type'), 'source_wait_label': pending_action.get('label'), 'source_wait_action_id': pending_action.get('action_id'), 'source_wait_controller_action_id': pending_action.get('controller_action_id'), 'expected_return_path': current_wait.get('expected_return_path'), 'allowed_external_events': current_wait.get('allowed_external_events') or [], 'reminder_text': reminder_text, 'reminder_text_sha256': reminder_hash, 'controller_must_use_router_authored_text': True, 'controller_may_edit_reminder_text': False, 'fresh_liveness_probe_required': bool(liveness_due), 'liveness_probe_target_role': liveness_probe.get('target_role') or target_role, 'liveness_probe_current_liveness_is_not_cached_authority': bool(liveness_probe.get('current_liveness_is_not_cached_authority')), 'payload_contract': router._wait_target_reminder_payload_contract(), 'controller_receipt_rule': 'Send reminder_text exactly to target_role, do not read or paste sealed bodies, then write a Controller receipt whose payload includes target_role, delivered_to_role, reminder_text_sha256, sealed_body_reads=false, and a fresh liveness_probe when fresh_liveness_probe_required is true.', 'idempotency_key': f"wait-target-reminder:{run_state.get('run_id')}:{hashlib.sha256(json.dumps(identity, sort_keys=True).encode('utf-8')).hexdigest()[:20]}:{last_sent}", 'scope_kind': pending_action.get('scope_kind') or 'wait_target', 'scope_id': pending_action.get('scope_id') or identity.get('expected_return_path') or identity.get('label') or target_role, 'apply_required': True, 'relay_allowed': False, 'sealed_body_reads_allowed': False})

def _ensure_wait_target_reminder_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any], current_wait: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    action = router._next_wait_target_reminder_action(project_root, run_root, run_state, pending_action, current_wait)
    if action is None:
        return None
    entry = router._write_controller_action_entry(project_root, run_root, run_state, action)
    append_history(run_state, 'router_materialized_wait_target_reminder_action', {'controller_action_id': entry.get('action_id'), 'target_role': action.get('target_role'), 'wait_class': action.get('wait_class'), 'source_wait_action_type': action.get('source_wait_action_type')})
    return entry

__all__ = (
    '_elapsed_seconds_since',
    '_wait_target_path_exists',
    '_pending_wait_class',
    '_wait_target_reminder_text',
    '_wait_target_due_state',
    '_pending_wait_summary',
    '_wait_target_reminder_text_sha256',
    '_wait_target_identity',
    '_wait_target_reminder_payload_contract',
    '_next_wait_target_reminder_action',
    '_ensure_wait_target_reminder_controller_action',
)

_LOCAL_NAMES = set(globals())
