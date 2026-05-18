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

def _current_work_owner_kind(router: ModuleType, owner_key: str) -> str:
    _bind_router(router)
    key = owner_key.strip()
    if key in {'router', 'controller', 'user'}:
        return key
    if key:
        return 'role'
    return 'none'

def _current_work_owner_label(router: ModuleType, owner_key: str) -> str:
    _bind_router(router)
    labels = {'router': 'Router', 'controller': 'Controller', 'user': 'User', 'project_manager': 'Project Manager', 'human_like_reviewer': 'Human-like Reviewer', 'process_flowguard_officer': 'Process FlowGuard Officer', 'product_flowguard_officer': 'Product FlowGuard Officer', 'worker_a': 'Worker A', 'worker_b': 'Worker B'}
    key = owner_key.strip()
    if key in labels:
        return labels[key]
    return key.replace('_', ' ').strip().title() if key else 'None'

def _current_work_payload(router: ModuleType, *, owner_key: str, task_label: str, source: str, source_path: str | None=None, action_type: str | None=None, action_id: str | None=None, packet_id: str | None=None, wait_class: str | None=None, waiting_for_role: str | None=None, diagnostics: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    owner_key = owner_key.strip()
    owner_kind = router._current_work_owner_kind(owner_key)
    owner_label = router._current_work_owner_label(owner_key)
    task = task_label.strip() or 'Monitor current FlowPilot progress'
    return {'owner_kind': owner_kind, 'owner_key': owner_key or None, 'owner_label': owner_label, 'task_label': task, 'source': source, 'source_path': source_path, 'action_type': action_type, 'action_id': action_id, 'packet_id': packet_id, 'wait_class': wait_class, 'legacy_waiting_for_role': waiting_for_role, 'display': {'en': f'Current owner: {owner_label}. Current task: {task}.', 'zh': f'当前处理方：{owner_label}。当前任务：{task}。'}, 'controller_use': {'primary_monitor_field': True, 'ownership_projection_only': True, 'does_not_satisfy_wait_or_approval': True, 'role_liveness_checks_apply': owner_kind == 'role', 'internal_owner': owner_kind in {'router', 'controller'}}, 'diagnostics': diagnostics or {}}

def _current_work_from_action(router: ModuleType, action: dict[str, Any], *, source: str, source_path: str | None=None, fallback_owner: str='controller') -> dict[str, Any] | None:
    _bind_router(router)
    if not isinstance(action, dict) or not action:
        return None
    action_type = str(action.get('action_type') or '')
    label = str(action.get('summary') or action.get('label') or action_type or 'Process FlowPilot action')
    target = str(action.get('waiting_for_role') or action.get('to_role') or action.get('target_role') or action.get('actor') or '').strip()
    if action.get('requires_user') or action.get('requires_user_dialog_display_confirmation'):
        owner_key = 'user'
    elif _action_is_passive_wait_status(action):
        owner_key = target
        if not owner_key and action_type == 'await_current_scope_reconciliation':
            owner_key = 'controller'
        if not owner_key:
            owner_key = 'router'
    elif target in {'router', 'controller'}:
        owner_key = target
    else:
        owner_key = fallback_owner
    wait_class = router._pending_wait_class(action)
    return router._current_work_payload(owner_key=owner_key, task_label=label, source=source, source_path=source_path, action_type=action_type or None, action_id=str(action.get('action_id') or action.get('controller_action_id') or '') or None, wait_class=wait_class, waiting_for_role=target or None, diagnostics={'passive_wait_status': _action_is_passive_wait_status(action), 'ordinary_controller_work_row': not _action_is_passive_wait_status(action)})

def _packet_status_allows_current_work(router: ModuleType, status: str) -> bool:
    _bind_router(router)
    normalized = status.strip().lower()
    if not normalized:
        return False
    return normalized not in {'done', 'complete', 'completed', 'cancelled', 'canceled', 'closed', 'stopped_by_user', 'result-returned', 'result_returned', 'result-absorbed', 'result_absorbed', 'absorbed', 'superseded'}

def _current_work_from_packet_ledger(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    path = run_root / 'packet_ledger.json'
    packet_ledger = read_json_if_exists(path)
    if not isinstance(packet_ledger, dict) or not packet_ledger:
        return None
    holder = str(packet_ledger.get('active_packet_holder') or '').strip()
    status = str(packet_ledger.get('active_packet_status') or '').strip()
    packet_id = str(packet_ledger.get('active_packet_id') or '').strip()
    if not holder or not router._packet_status_allows_current_work(status):
        return None
    task = f"Advance active packet {packet_id or 'work'} ({status})"
    return router._current_work_payload(owner_key=holder, task_label=task, source='packet_ledger', source_path=project_relative(project_root, path), packet_id=packet_id or None, diagnostics={'active_packet_status': status, 'active_packet_holder': holder, 'packet_ledger_schema': packet_ledger.get('schema_version')})

def _current_work_from_passive_waits(router: ModuleType, project_root: Path, run_root: Path, *, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    if controller_ledger is None:
        controller_ledger = router._controller_action_ledger_summary(run_root)
    passive_waits = controller_ledger.get('passive_waits') if isinstance(controller_ledger, dict) else []
    if isinstance(passive_waits, list):
        for item in passive_waits:
            if not isinstance(item, dict):
                continue
            status = str(item.get('status') or '').strip()
            reconciled = str(item.get('router_reconciliation_status') or '').strip()
            if status in {'done', 'resolved', 'skipped', 'superseded'} or reconciled == 'reconciled':
                continue
            payload = router._current_work_from_action(item, source='controller_action_ledger.passive_waits', source_path=controller_ledger.get('path') if isinstance(controller_ledger.get('path'), str) else None, fallback_owner='controller')
            if payload:
                return payload
    scheduler_path = _router_scheduler_ledger_path(run_root)
    scheduler = read_json_if_exists(scheduler_path)
    rows = scheduler.get('rows') if isinstance(scheduler, dict) and isinstance(scheduler.get('rows'), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        router_state = str(row.get('router_state') or '').strip()
        controller_status = str(row.get('controller_status') or '').strip()
        if router_state not in {'queued', 'waiting', 'receipt_done'} and controller_status not in {'pending', 'waiting', 'in_progress'}:
            continue
        action_type = str(row.get('action_type') or '')
        target = str(row.get('to_role') or row.get('waiting_for_role') or '').strip()
        if action_type == 'await_current_scope_reconciliation' and (not target):
            target = 'controller'
        payload = router._current_work_payload(owner_key=target or 'router', task_label=str(row.get('label') or action_type or 'Reconcile scheduler wait'), source='router_scheduler_ledger', source_path=project_relative(project_root, scheduler_path), action_type=action_type or None, action_id=str(row.get('row_id') or '') or None, waiting_for_role=target or None, diagnostics={'router_state': router_state, 'controller_status': controller_status, 'barrier_kind': row.get('barrier_kind')})
        return payload
    return None

def _derive_current_work(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, current_wait: dict[str, Any] | None=None, current_action: dict[str, Any] | None=None, controller_ledger: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    pending = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    if pending:
        payload = router._current_work_from_action(pending, source='pending_action', source_path=project_relative(project_root, router.run_state_path(run_root)))
        if payload:
            return payload
    if isinstance(current_action, dict) and current_action:
        payload = router._current_work_from_action(current_action, source='current_action', source_path=project_relative(project_root, _router_daemon_status_path(run_root)))
        if payload:
            return payload
    packet_payload = router._current_work_from_packet_ledger(project_root, run_root)
    if packet_payload:
        return packet_payload
    passive_payload = router._current_work_from_passive_waits(project_root, run_root, controller_ledger=controller_ledger)
    if passive_payload:
        return passive_payload
    if isinstance(current_wait, dict) and current_wait:
        payload = router._current_work_from_action(current_wait, source='current_wait', source_path=project_relative(project_root, _router_daemon_status_path(run_root)), fallback_owner='router')
        if payload and payload.get('owner_kind') != 'none':
            return payload
    if run_state.get('daemon_mode_enabled'):
        return router._current_work_payload(owner_key='router', task_label='Compute or observe the next safe FlowPilot step', source='router_daemon', source_path=project_relative(project_root, _router_daemon_status_path(run_root)), diagnostics={'daemon_mode_enabled': True, 'run_status': run_state.get('status')})
    return router._current_work_payload(owner_key='controller', task_label='Inspect FlowPilot state', source='controller', source_path=project_relative(project_root, router.run_state_path(run_root)), diagnostics={'run_status': run_state.get('status')})

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
    '_current_work_owner_kind',
    '_current_work_owner_label',
    '_current_work_payload',
    '_current_work_from_action',
    '_packet_status_allows_current_work',
    '_current_work_from_packet_ledger',
    '_current_work_from_passive_waits',
    '_derive_current_work',
    '_wait_target_reminder_text_sha256',
    '_wait_target_identity',
    '_wait_target_reminder_payload_contract',
    '_next_wait_target_reminder_action',
    '_ensure_wait_target_reminder_controller_action',
)

_LOCAL_NAMES = set(globals())
