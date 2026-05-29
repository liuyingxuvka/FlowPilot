"""role recovery wait candidate settlement helpers for ``flowpilot_router_startup_role_transactions``.

This child module is imported by the public facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_role_recovery'

def _controller_action_entry_view(router: ModuleType, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
    if action:
        return dict(action)
    return {key: entry.get(key) for key in ('action_type', 'label', 'summary', 'to_role', 'allowed_reads', 'allowed_writes', 'allowed_external_events', 'expected_return_path', 'card_envelope_path', 'card_bundle_envelope_path', 'card_return_event', 'card_id', 'card_bundle_id') if entry.get(key) not in (None, '', [])}

def _controller_action_wait_roles(router: ModuleType, entry: dict[str, Any]) -> set[str]:
    _bind_router(router)
    action = router._controller_action_entry_view(entry)
    roles = {str(value).strip() for value in (entry.get('to_role'), entry.get('target_role'), entry.get('waiting_for_role'), action.get('to_role'), action.get('target_role'), action.get('waiting_for_role')) if isinstance(value, str) and value.strip()}
    if str(entry.get('action_type') or action.get('action_type') or '') == 'await_role_decision':
        for event in _controller_wait_allowed_external_events(entry):
            meta = EXTERNAL_EVENTS.get(event)
            if isinstance(meta, dict):
                role = _event_wait_role(event, meta)
                if role:
                    roles.add(role)
    return roles

def _role_recovery_action_sort_key(router: ModuleType, entry: dict[str, Any]) -> tuple[str, str, str, str]:
    _bind_router(router)
    try:
        created_sequence = f"{int(entry.get('created_sequence') or 0):020d}"
    except (TypeError, ValueError):
        created_sequence = "00000000000000000000"
    return (str(entry.get('created_at') or ''), created_sequence, str(entry.get('router_scheduler_row_id') or ''), str(entry.get('action_id') or ''))

def _role_recovery_pending_return_for_action(router: ModuleType, run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    for record in _pending_return_records(run_root, run_id):
        if _pending_action_matches_card_return(action, record):
            return record
    return None

def _role_recovery_wait_candidates(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], target_roles: set[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    del project_root
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return []
    candidates: list[dict[str, Any]] = []
    run_id = str(run_state['run_id'])
    for action_path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(action_path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if str(entry.get('status') or '') in CONTROLLER_ACTION_CLOSED_STATUSES:
            continue
        action = router._controller_action_entry_view(entry)
        action_type = str(entry.get('action_type') or action.get('action_type') or '')
        if action_type not in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event', 'await_role_decision'}:
            continue
        wait_roles = router._controller_action_wait_roles(entry)
        matched_roles = sorted(wait_roles.intersection(target_roles))
        if not matched_roles:
            continue
        pending_return = None
        replay_kind = 'role_output'
        if action_type in {'await_card_return_event', 'check_card_return_event', 'await_card_bundle_return_event', 'check_card_bundle_return_event'}:
            replay_kind = 'card_ack'
            pending_return = router._role_recovery_pending_return_for_action(run_root, run_id, action)
        candidates.append({'entry': entry, 'action': action, 'action_path': action_path, 'kind': replay_kind, 'matched_roles': matched_roles, 'pending_return': pending_return, 'sort_key': router._role_recovery_action_sort_key(entry)})
    candidates.sort(key=lambda item: item['sort_key'])
    return candidates

def _mark_controller_action_done_by_role_recovery(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any], *, evidence: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    action_path = candidate['action_path']
    entry = read_json_if_exists(action_path)
    if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
        entry = dict(candidate['entry'])
    now = utc_now()
    entry['status'] = 'done'
    entry['completed_at'] = now
    entry['completion_source'] = 'role_recovery_obligation_replay'
    entry['router_reconciliation_status'] = 'reconciled'
    entry['router_reconciled_at'] = now
    entry['satisfied_by_existing_recovery_evidence'] = evidence
    entry['controller_receipt_required'] = False
    entry['router_must_not_mark_done_without_controller_receipt'] = False
    write_json(action_path, entry)
    row_id = str(entry.get('router_scheduler_row_id') or '')
    if row_id:
        router._update_router_scheduler_row(project_root, run_root, run_state, row_id=row_id, router_state='reconciled', reconciliation={'source': 'role_recovery_obligation_replay', 'evidence': evidence, 'reconciled_at': now})
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and (pending.get('controller_action_id') == entry.get('action_id') or pending.get('router_scheduler_row_id') == entry.get('router_scheduler_row_id') or pending.get('label') == entry.get('label')):
        run_state['pending_action'] = None
    return entry

def _role_recovery_existing_event_for_wait(router: ModuleType, run_state: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    allowed_events = set(_controller_wait_allowed_external_events(entry))
    if not allowed_events:
        return None
    for record in run_state.get('events') or []:
        if isinstance(record, dict) and record.get('event') in allowed_events:
            return record
    return None

def _settle_role_recovery_candidate_if_evidence_exists(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    action = dict(candidate['action'])
    if candidate['kind'] == 'card_ack':
        pending_return = candidate.get('pending_return')
        if isinstance(pending_return, dict):
            pending = dict(pending_return)
            pending.update({key: value for key, value in action.items() if value not in (None, '', [])})
        else:
            pending = action
        expected_return_path = str(pending.get('expected_return_path') or '')
        if not expected_return_path or not resolve_project_path(project_root, expected_return_path).exists():
            return None
        result = _try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, pending)
        if not result.get('consumed'):
            return None
        _run_router_return_settlement_finalizers(project_root, run_root, run_state, source='role_recovery_obligation_replay')
        evidence = {'kind': 'existing_card_ack', 'expected_return_path': expected_return_path, 'validation': result.get('result')}
        router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
        return {'outcome': 'settled_existing_ack', 'evidence': evidence}
    event_record = router._role_recovery_existing_event_for_wait(run_state, candidate['entry'])
    if event_record is None:
        return None
    closure = _close_waiting_controller_actions_for_external_event(project_root, run_root, run_state, event=str(event_record.get('event') or ''), payload=event_record.get('payload') if isinstance(event_record.get('payload'), dict) else {}, source='role_recovery_obligation_replay')
    evidence = {'kind': 'existing_role_output_event', 'event': event_record.get('event'), 'recorded_at': event_record.get('recorded_at'), 'wait_closure': closure}
    router._mark_controller_action_done_by_role_recovery(project_root, run_root, run_state, candidate, evidence=evidence)
    return {'outcome': 'settled_existing_output', 'evidence': evidence}

__all__ = (
    '_controller_action_entry_view',
    '_controller_action_wait_roles',
    '_role_recovery_action_sort_key',
    '_role_recovery_pending_return_for_action',
    '_role_recovery_wait_candidates',
    '_mark_controller_action_done_by_role_recovery',
    '_role_recovery_existing_event_for_wait',
    '_settle_role_recovery_candidate_if_evidence_exists',
)

_LOCAL_NAMES = set(globals())
