"""Cohesive child helpers for FlowPilot route-frontier public facades."""

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

def _card_required_source_paths(router: ModuleType, project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    _bind_router(router)
    source_paths: dict[str, str] = {}
    for label, relative_path in CARD_REQUIRED_SOURCE_PATHS.get(card_id, {}).items():
        path = run_root / relative_path
        if path.exists():
            source_paths[label] = project_relative(project_root, path)
    if card_id in {'flowguard_operator.route_process_check', 'reviewer.route_challenge'}:
        for draft_path in sorted((run_root / 'routes').glob('*/flow.draft.json')):
            source_paths[f'route_draft_{draft_path.parent.name}'] = project_relative(project_root, draft_path)
    return source_paths


def _card_delivery_phase(router: ModuleType, card_id: str, card: dict[str, Any], frontier: dict[str, Any], run_state: dict[str, Any]) -> tuple[str, str | None]:
    _bind_router(router)
    card_phase = CARD_PHASE_BY_ID.get(card_id) or card.get('phase')
    current_phase = str(card_phase or frontier.get('phase') or frontier.get('status') or run_state.get('phase') or 'unknown')
    return (current_phase, str(card_phase or '') or None)


def _live_card_delivery_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    card_id = str(entry.get('card_id') or card.get('id') or '')
    current_phase, card_phase = router._card_delivery_phase(card_id, card, frontier, run_state)
    user_request_path = str(run_state.get('user_request_path') or router._optional_source_path(project_root, run_root / 'user_request.json') or '')
    startup_intake_record_path = str(run_state.get('startup_intake_record_path') or router._optional_source_path(project_root, run_root / 'startup_intake' / 'startup_intake_record.json') or '')
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root)), 'execution_frontier': router._optional_source_path(project_root, run_root / 'execution_frontier.json'), 'prompt_delivery_ledger': router._optional_source_path(project_root, run_root / 'prompt_delivery_ledger.json'), 'packet_ledger': router._optional_source_path(project_root, run_root / 'packet_ledger.json'), 'route_history_index': router._optional_source_path(project_root, router._route_history_index_path(run_root)), 'pm_prior_path_context': router._optional_source_path(project_root, router._pm_prior_path_context_path(run_root)), 'user_request_path': user_request_path or None, 'startup_intake_record_path': startup_intake_record_path or None}
    source_paths.update(router._card_required_source_paths(project_root, run_root, card_id))
    return {'schema_version': LIVE_CARD_CONTEXT_SCHEMA, 'run_id': str(run_state.get('run_id') or run_root.name), 'card_id': card_id, 'to_role': str(entry.get('to_role') or card.get('audience') or ''), 'current_task': {'user_request_path': user_request_path or None, 'startup_intake_record_path': startup_intake_record_path or None, 'user_intake_packet_id': 'user_intake' if (run_root / 'mailbox' / 'outbox' / 'user_intake.json').exists() else None, 'task_authority': 'startup_intake_ui_record_and_user_intake' if startup_intake_record_path else 'router_recorded_user_request_and_user_intake', 'controller_summary_is_task_authority': False, 'startup_intake_authority_source': 'startup_intake_record' if startup_intake_record_path else None}, 'current_stage': {'current_phase': current_phase, 'card_phase': card_phase, 'frontier_status': frontier.get('status'), 'current_node_id': frontier.get('active_node_id'), 'current_route_id': frontier.get('active_route_id'), 'route_version': frontier.get('route_version')}, 'source_paths': source_paths, 'role_prompt_rule': 'Treat this router delivery envelope as the live context for the current run, current task, current card, current phase, and current node/frontier. If required context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.'}


def _matching_controller_delivery_actions(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool) -> list[dict[str, Any]]:
    _bind_router(router)
    matches: list[dict[str, Any]] = []
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return matches
    for path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        if not _controller_delivery_action_matches_pending_return(action, record, bundle=bundle):
            continue
        receipt_path = str(entry.get('receipt_path') or entry.get('expected_receipt_path') or '')
        matches.append({'action_id': entry.get('action_id'), 'action_type': entry.get('action_type'), 'status': entry.get('status') or 'pending', 'action_path': project_relative(project_root, path), 'receipt_path': receipt_path, 'updated_at': entry.get('updated_at'), 'completed_at': entry.get('completed_at')})
    return matches


def _controller_delivery_fact_for_pending_return(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool, committed_extra: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    extra = committed_extra
    if extra is None:
        extra = _committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=True) if bundle else _committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    matches = router._matching_controller_delivery_actions(project_root, run_root, record, bundle=bundle)
    statuses = {str(item.get('status') or 'pending') for item in matches}
    artifact_committed = bool(extra.get('artifact_committed'))
    if not artifact_committed:
        status = 'committed_artifact_missing_or_invalid'
        target_allowed = False
        reissue_reason = 'original_committed_artifact_missing_or_invalid'
    elif 'done' in statuses:
        status = 'controller_delivery_done'
        target_allowed = True
        reissue_reason = ''
    elif 'blocked' in statuses:
        status = 'controller_delivery_blocked'
        target_allowed = False
        reissue_reason = 'controller_delivery_blocked'
    elif 'skipped' in statuses and (not statuses - {'skipped'}):
        status = 'controller_delivery_skipped'
        target_allowed = False
        reissue_reason = 'controller_delivery_skipped'
    elif matches:
        status = 'controller_delivery_unconfirmed'
        target_allowed = False
        reissue_reason = 'controller_delivery_not_marked_done'
    else:
        status = 'controller_delivery_fact_unrecorded'
        target_allowed = True
        reissue_reason = ''
    controller_read_paths: list[str] = []
    for item in matches:
        for key in ('action_path', 'receipt_path'):
            value = str(item.get(key) or '')
            if value and value not in controller_read_paths:
                controller_read_paths.append(value)
    return {'schema_version': 'flowpilot.controller_delivery_fact.v1', 'return_kind': 'system_card_bundle' if bundle else 'system_card', 'card_id': None if bundle else record.get('card_id'), 'card_bundle_id': record.get('card_bundle_id') if bundle else None, 'delivery_attempt_id': None if bundle else record.get('delivery_attempt_id'), 'delivery_attempt_ids': record.get('delivery_attempt_ids') if bundle else None, 'card_envelope_path': record.get('card_bundle_envelope_path') if bundle else record.get('card_envelope_path'), 'expected_return_path': record.get('expected_return_path'), 'artifact_committed': artifact_committed, 'artifact_exists': bool(extra.get('artifact_exists')), 'artifact_hash_verified': bool(extra.get('artifact_hash_verified')), 'matching_controller_actions': matches, 'controller_read_paths': controller_read_paths, 'controller_delivery_fact_status': status, 'controller_delivery_done': status == 'controller_delivery_done', 'controller_delivery_fact_unrecorded': status == 'controller_delivery_fact_unrecorded', 'target_role_ack_reminder_allowed': target_allowed, 'target_role_ack_reminder_blocked_until_controller_delivery_done': not target_allowed, 'controller_delivery_reissue_required': not target_allowed, 'controller_delivery_reissue_reason': reissue_reason, 'controller_must_not_remind_target_before_delivery_done': True}


__all__ = (
    '_card_required_source_paths',
    '_card_delivery_phase',
    '_live_card_delivery_context',
    '_matching_controller_delivery_actions',
    '_controller_delivery_fact_for_pending_return',
)

_LOCAL_NAMES = set(globals())
