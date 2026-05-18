"""Terminal closure and replay helpers for the FlowPilot router.

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


def _terminal_closure_suite_is_closed(router: ModuleType, run_root: Path) -> bool:
    _bind_router(router)
    closure = read_json_if_exists(run_root / 'closure' / 'terminal_closure_suite.json')
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    if not isinstance(closure, dict) or not isinstance(frontier, dict):
        return False
    return closure.get('status') == 'closed' and frontier.get('status') == 'closed'

def _write_terminal_backward_replay(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('terminal backward replay must be reviewed_by_role=human_like_reviewer')
    if payload.get('passed') is not True:
        raise RouterError('terminal backward replay must explicitly pass')
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_map_path = run_root / 'terminal_human_backward_replay_map.json'
    if not final_ledger_path.exists() or not terminal_map_path.exists():
        raise RouterError('terminal backward replay requires final ledger and PM replay map')
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get('pm_owned') is not True or final_ledger.get('status') != 'clean':
        raise RouterError('terminal replay requires a PM-owned clean final ledger')
    if final_ledger.get('counts', {}).get('unresolved_count') != 0:
        raise RouterError('terminal replay cannot pass unless final ledger unresolved_count is zero')
    terminal_map = read_json(terminal_map_path)
    if terminal_map.get('status') != 'ready_for_reviewer':
        raise RouterError('terminal replay map must be ready_for_reviewer')
    segments = terminal_map.get('segments') if isinstance(terminal_map.get('segments'), list) else []
    required_segment_ids = [str(segment.get('segment_id')) for segment in segments if isinstance(segment, dict) and segment.get('segment_id')]
    segment_reviews = payload.get('segment_reviews')
    if not isinstance(segment_reviews, list) or not segment_reviews:
        raise RouterError('terminal backward replay requires segment_reviews for every replay-map segment')
    reviews_by_id = {str(item.get('segment_id')): item for item in segment_reviews if isinstance(item, dict) and item.get('segment_id')}
    missing_segments = [segment_id for segment_id in required_segment_ids if segment_id not in reviews_by_id]
    if missing_segments:
        raise RouterError(f"terminal backward replay missing segment reviews: {', '.join(missing_segments)}")
    failed_segments = [segment_id for segment_id in required_segment_ids if reviews_by_id[segment_id].get('reviewed_by_role') != 'human_like_reviewer' or reviews_by_id[segment_id].get('passed') is not True or reviews_by_id[segment_id].get('pm_segment_decision') != 'continue']
    if failed_segments:
        raise RouterError(f"terminal replay segments require reviewer pass and PM continue: {', '.join(failed_segments)}")
    for segment in segments:
        if isinstance(segment, dict) and segment.get('segment_id'):
            review = reviews_by_id.get(str(segment['segment_id']))
            if review:
                segment['status'] = 'passed'
                segment['review'] = review
    terminal_map['status'] = 'passed'
    terminal_map.setdefault('coverage', {})
    terminal_map['coverage'].update({'effective_nodes_reviewed_by_human': int(terminal_map['coverage'].get('effective_nodes_total', 1) or 1), 'segments_reviewed': len(required_segment_ids), 'root_acceptance_reviewed': True, 'parent_nodes_reviewed': True, 'leaf_nodes_reviewed': True, 'every_effective_node_has_pm_segment_decision': True})
    terminal_map.setdefault('completion_gate', {})
    terminal_map['completion_gate'].update({'reviewer_passed': True, 'pm_segment_decisions_recorded': True, 'repair_restart_policy_recorded': True, 'unresolved_repair_findings': 0, 'completion_allowed': True})
    terminal_map['reviewed_by_role'] = 'human_like_reviewer'
    terminal_map['reviewed_at'] = utc_now()
    write_json(terminal_map_path, terminal_map)
    final_ledger.setdefault('terminal_human_backward_replay', {})
    final_ledger['terminal_human_backward_replay'].update({'status': 'passed', 'review_map_path': project_relative(project_root, terminal_map_path), 'report_only_allowed': False, 'segments_reviewed': len(required_segment_ids)})
    final_ledger['completion_allowed'] = True
    final_ledger['terminal_replay_review_path'] = project_relative(project_root, run_root / 'reviews' / 'terminal_backward_replay.json')
    final_ledger['terminal_replay_reviewed_at'] = utc_now()
    write_json(final_ledger_path, final_ledger)
    write_json(run_root / 'reviews' / 'terminal_backward_replay.json', {'schema_version': 'flowpilot.terminal_backward_replay_review.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'passed': True, 'source_paths': {'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_human_backward_replay_map': project_relative(project_root, terminal_map_path)}, 'segment_reviews': segment_reviews, 'report_only_allowed': False, 'reviewed_at': utc_now(), **_role_output_envelope_record(payload)})
    router._write_task_completion_projection(project_root, run_root, run_state, source_event='reviewer_final_backward_replay_passed')

def _write_task_completion_projection(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source_event: str) -> Path:
    _bind_router(router)
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_replay_path = run_root / 'reviews' / 'terminal_backward_replay.json'
    frontier_path = run_root / 'execution_frontier.json'
    final_ledger = read_json(final_ledger_path)
    terminal_replay = read_json(terminal_replay_path)
    frontier = read_json(frontier_path)
    if final_ledger.get('completion_allowed') is not True:
        raise RouterError('task completion projection requires completion_allowed final ledger')
    if terminal_replay.get('passed') is not True:
        raise RouterError('task completion projection requires passed terminal backward replay')
    projection_path = _task_completion_projection_path(run_root)
    write_json(projection_path, {'schema_version': 'flowpilot.task_completion_projection.v1', 'run_id': run_state['run_id'], 'task_status': 'ready_for_pm_terminal_closure', 'projection_owner': 'controller', 'completion_fact_owner': 'project_manager', 'source_event': source_event, 'derived_from': 'active_route_state_frontier_and_ledger', 'controller_may_declare_completion': False, 'ui_or_chat_is_display_only': True, 'source_paths': {'execution_frontier': project_relative(project_root, frontier_path), 'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_backward_replay': project_relative(project_root, terminal_replay_path), 'latest_node_completion_ledger': str(frontier.get('latest_node_completion_ledger_path') or '')}, 'published_at': utc_now()})
    run_state['flags']['task_completion_projection_published'] = True
    return projection_path

def _write_terminal_closure_suite(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('approved_by_role', 'project_manager') != 'project_manager':
        raise RouterError('terminal closure must be approved_by_role=project_manager')
    decision = str(payload.get('decision') or '')
    if decision not in PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES:
        raise RouterError('terminal closure requires decision=approve_terminal_closure')
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose='terminal closure')
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_replay_path = run_root / 'reviews' / 'terminal_backward_replay.json'
    task_projection_path = _task_completion_projection_path(run_root)
    continuation_path = router._continuation_binding_path(run_root)
    required_paths = [final_ledger_path, terminal_replay_path, task_projection_path, run_root / 'execution_frontier.json', run_root / 'crew_ledger.json', continuation_path]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"terminal closure missing lifecycle paths: {', '.join(missing)}")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get('completion_allowed') is not True:
        raise RouterError('terminal closure requires completion_allowed final ledger')
    replay = read_json(terminal_replay_path)
    if replay.get('passed') is not True:
        raise RouterError('terminal closure requires passed terminal backward replay')
    task_projection = read_json(task_projection_path)
    if task_projection.get('task_status') != 'ready_for_pm_terminal_closure':
        raise RouterError('terminal closure requires task completion projection')
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status['clean']:
        first_issue = pm_suggestion_status['issues'][0]['message'] if pm_suggestion_status['issues'] else 'unknown issue'
        raise RouterError(f'terminal closure requires clean PM suggestion ledger: {first_issue}')
    self_interrogation_status = _require_clean_self_interrogation(project_root, run_root, gate_name='terminal closure')
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, run_state)
    if not closure_reconciliation['clean']:
        raise RouterError('terminal closure requires clean reconciliation ledgers: ' + router._closure_reconciliation_blocker_message(closure_reconciliation))
    unresolved_role_work = router._unresolved_pm_role_work_requests(run_root, run_state)
    if unresolved_role_work:
        request_ids = ', '.join((str(item.get('request_id')) for item in unresolved_role_work[:5]))
        raise RouterError(f'terminal closure requires all PM role-work requests resolved first: {request_ids}')
    if not router._current_closure_state_clean(project_root, run_root):
        raise RouterError('terminal closure requires current clean evidence/resource/final ledgers')
    continuation = read_json(continuation_path)
    continuation['heartbeat_active'] = False
    continuation['closed_at'] = utc_now()
    continuation['closure_reason'] = 'terminal_completion'
    write_json(continuation_path, continuation)
    closure = {'schema_version': 'flowpilot.terminal_closure_suite.v1', 'run_id': run_state['run_id'], 'approved_by_role': 'project_manager', 'status': 'closed', 'closed_at': utc_now(), 'source_paths': {'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_backward_replay': project_relative(project_root, terminal_replay_path), 'task_completion_projection': project_relative(project_root, task_projection_path), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'continuation_binding': project_relative(project_root, continuation_path), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root)), 'pm_suggestion_ledger': project_relative(project_root, _pm_suggestion_ledger_path(run_root)) if pm_suggestion_status['exists'] else None, 'self_interrogation_index': project_relative(project_root, _self_interrogation_index_path(run_root)) if self_interrogation_status['exists'] else None, 'defect_ledger': closure_reconciliation['defect_ledger']['path'], 'crew_memory': closure_reconciliation['role_memory']['path'], 'continuation_quarantine': closure_reconciliation['continuation_quarantine']['path']}, 'decision': decision, 'prior_path_context_review': prior_review, 'pm_suggestion_ledger_review': {'entry_count': pm_suggestion_status['entry_count'], 'issue_count': pm_suggestion_status['issue_count'], 'clean': pm_suggestion_status['clean']}, 'self_interrogation_review': {'record_count': self_interrogation_status['record_count'], 'issue_count': self_interrogation_status['issue_count'], 'unresolved_hard_finding_count': self_interrogation_status['unresolved_hard_finding_count'], 'clean': self_interrogation_status['clean']}, 'terminal_closure_reconciliation': closure_reconciliation, 'lifecycle': {'heartbeat_active': False, 'manual_resume_notice_required': False, 'terminal_completion_notice_recorded': True, 'crew_memory_archived': True}, 'final_report': payload.get('final_report') or {}, **_role_output_envelope_record(payload)}
    write_json(run_root / 'closure' / 'terminal_closure_suite.json', closure)
    run_state['status'] = 'closed'
    run_state['phase'] = 'terminal'
    run_state['holder'] = 'controller'
    run_state['pending_action'] = None
    run_state.setdefault('flags', {})['terminal_closure_approved'] = True
    frontier = router._active_frontier(run_root)
    frontier['status'] = 'closed'
    frontier['phase'] = 'terminal'
    frontier['terminal'] = True
    frontier['terminal_event'] = 'pm_approves_terminal_closure'
    frontier['closed_at'] = utc_now()
    frontier['source'] = 'pm_approves_terminal_closure'
    write_json(run_root / 'execution_frontier.json', frontier)
    reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode='closed', event='pm_approves_terminal_closure')
    write_json(_lifecycle_record_path(run_root), {'schema_version': 'flowpilot.run_lifecycle.v1', 'run_id': run_state.get('run_id'), 'status': 'closed', 'request_event': 'pm_approves_terminal_closure', 'reason': 'terminal_completion', 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'reconciliation': reconciliation, 'closed_at': closure['closed_at']})
    append_history(run_state, 'run_closed', {'event': 'pm_approves_terminal_closure', 'lifecycle_path': project_relative(project_root, _lifecycle_record_path(run_root))})
    _sync_current_and_index_status(project_root, run_state)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event='pm_approves_terminal_closure')

__all__ = (
    '_terminal_closure_suite_is_closed',
    '_write_terminal_backward_replay',
    '_write_task_completion_projection',
    '_write_terminal_closure_suite',
)

_LOCAL_NAMES = set(globals())
