"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints stay aligned.
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

def _supersede_queued_control_blocker_actions(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, resolved_at: str, resolution_status: str) -> int:
    _bind_router(router)
    if not blocker_id:
        return 0
    superseded = 0
    action_dir = _controller_actions_dir(run_root)
    if action_dir.exists():
        for path in sorted(action_dir.glob('*.json')):
            entry = read_json_if_exists(path)
            if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
                continue
            if entry.get('action_type') != 'handle_control_blocker':
                continue
            if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES:
                continue
            action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
            if blocker_id not in {str(entry.get('blocker_id') or ''), str(action.get('blocker_id') or '')}:
                continue
            reconciliation = {'resolution_status': 'superseded_by_resolved_control_blocker', 'source_blocker_resolution_status': resolution_status, 'blocker_id': blocker_id, 'resolved_at': resolved_at}
            _update_controller_action_entry_fields(project_root, run_root, run_state, action_id=str(entry.get('action_id') or ''), status='superseded', fields={'router_reconciliation_status': 'superseded_by_resolved_control_blocker', 'router_reconciled_at': resolved_at, 'router_reconciliation': reconciliation, 'superseded_by_control_blocker_resolution': blocker_id}, router_state='superseded', reconciliation=reconciliation)
            superseded += 1
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') == 'handle_control_blocker':
        if blocker_id == str(pending.get('blocker_id') or ''):
            run_state['pending_action'] = None
            append_history(run_state, 'router_cleared_pending_control_blocker_action_after_resolution', {'blocker_id': blocker_id, 'resolution_status': resolution_status})
    return superseded

def _resolve_control_blockers_for_reconciled_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action: dict[str, Any], entry: dict[str, Any] | None=None, reconciliation: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get('action_type') or (entry or {}).get('action_type') or '')
    if not action_type:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    controller_action_id = str((entry or {}).get('action_id') or action.get('controller_action_id') or '')
    router_scheduler_row_id = str((entry or {}).get('router_scheduler_row_id') or action.get('router_scheduler_row_id') or '')
    postcondition = str(_pending_action_postcondition(action) or (reconciliation or {}).get('bootstrap_postcondition') or (reconciliation or {}).get('postcondition') or '')
    postcondition_satisfied = bool(postcondition and _pending_action_postcondition_satisfied(run_state, postcondition))
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    resolved_ids: list[str] = []
    superseded_actions = 0
    resolved_at = utc_now()
    resolution_status = 'resolved_by_startup_reconciliation' if router._boot_action_meta(action_type) is not None else 'resolved_by_controller_action_reconciliation'
    for path in sorted(control_root.glob('*.json')):
        if path.name.endswith('.sealed_repair_packet.json') or path.name == 'blocker_repair_policy_snapshot.json':
            continue
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        match_reason = router._control_blocker_matches_reconciled_action(record, action_type=action_type, controller_action_id=controller_action_id, router_scheduler_row_id=router_scheduler_row_id, postcondition=postcondition, postcondition_satisfied=postcondition_satisfied)
        if not match_reason:
            continue
        blocker_id = str(record.get('blocker_id') or '')
        record['resolution_status'] = resolution_status
        record['resolution_reason'] = match_reason
        record['resolved_by_controller_action_id'] = controller_action_id or None
        record['resolved_by_router_scheduler_row_id'] = router_scheduler_row_id or None
        record['resolved_postcondition'] = postcondition or None
        record['resolved_at'] = resolved_at
        record['resolution_note'] = 'The originating Controller action/postcondition reconciled before this blocker needed role repair.'
        if reconciliation is not None:
            record['resolved_by_reconciliation'] = _json_safe(reconciliation)
        write_json(path, record)
        resolved_ids.append(blocker_id)
        superseded_actions += router._supersede_queued_control_blocker_actions(project_root, run_root, run_state, blocker_id=blocker_id, resolved_at=resolved_at, resolution_status=resolution_status)
    if not resolved_ids:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    append_history(run_state, 'router_resolved_control_blockers_by_controller_action_reconciliation', {'action_type': action_type, 'controller_action_id': controller_action_id, 'router_scheduler_row_id': router_scheduler_row_id, 'postcondition': postcondition, 'resolved_blocker_ids': resolved_ids, 'superseded_control_blocker_actions': superseded_actions})
    return {'changed': True, 'resolved': len(resolved_ids), 'resolved_blocker_ids': resolved_ids, 'superseded_actions': superseded_actions}

def _control_blocker_summary(router: ModuleType, record: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    fields = ('blocker_id', 'handling_lane', 'originating_handling_lane', 'policy_row_id', 'blocker_family', 'first_handler', 'attempt_key', 'family_key', 'direct_retry_budget', 'direct_retry_attempts_used', 'direct_retry_budget_exhausted', 'escalate_to', 'pm_recovery_options', 'return_policy', 'hard_stop_conditions', 'blocker_repair_policy_snapshot_path', 'blocker_artifact_path', 'target_role', 'responsible_role_for_reissue', 'pm_decision_required', 'delivery_status', 'sealed_repair_packet_path', 'sealed_repair_packet_hash', 'originating_event', 'originating_action_type', 'originating_controller_action_id', 'originating_router_scheduler_row_id', 'originating_postcondition', 'created_at', 'delivered_to_role', 'delivered_at', 'resolution_status', 'resolved_by_event', 'resolved_at', 'pm_repair_decision_status', 'pm_repair_decision_path', 'pm_repair_decision_hash', 'pm_repair_rerun_target', 'pm_recovery_option', 'pm_repair_return_gate', 'repair_origin', 'repair_transaction_id', 'repair_transaction_path', 'repair_outcome_table', 'allowed_resolution_events')
    return {field: record.get(field) for field in fields if field in record}

def _resume_reentry_gate_pending(router: ModuleType, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags', {})
    return bool(flags.get('resume_reentry_requested')) and (
        not bool(flags.get('resume_state_loaded')) or not bool(flags.get('resume_roles_restored'))
    )

def _sync_protocol_blocker_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    blockers: list[dict[str, Any]] = []
    blocker_root = run_root / 'blockers'
    if blocker_root.exists():
        for path in sorted(blocker_root.glob('*.json')):
            record = read_json_if_exists(path)
            blockers.append({'path': project_relative(project_root, path), 'blocker_id': record.get('blocker_id') or path.stem, 'blocker_type': record.get('blocker_type'), 'status': record.get('status'), 'registered_at': record.get('registered_at') or utc_now()})
    run_state['protocol_blockers'] = blockers

def _sync_control_plane_indexes(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    summaries: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    control_root = run_root / 'control_blocks'
    if control_root.exists():
        for path in sorted(control_root.glob('*.json')):
            record = read_json_if_exists(path)
            if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
                continue
            summary = router._control_blocker_summary(record)
            summaries.append(summary)
            if record.get('resolution_status'):
                resolved.append(summary)
            else:
                active = summary
    run_state['control_blockers'] = summaries
    run_state['resolved_control_blockers'] = resolved
    run_state['active_control_blocker'] = active
    run_state['latest_control_blocker_path'] = active.get('blocker_artifact_path') if active else None
    router._sync_protocol_blocker_index(project_root, run_root, run_state)
    router._write_repair_transaction_index(project_root, run_root, run_state)

__all__ = (
    '_supersede_queued_control_blocker_actions',
    '_resolve_control_blockers_for_reconciled_controller_action',
    '_control_blocker_summary',
    '_resume_reentry_gate_pending',
    '_sync_protocol_blocker_index',
    '_sync_control_plane_indexes',
)

_LOCAL_NAMES = set(globals())
