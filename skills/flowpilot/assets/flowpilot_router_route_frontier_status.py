"""Coarse route frontier owner helpers for the FlowPilot router.

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

def _active_ui_task_catalog(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}
    run_id = str(run_state.get('run_id') or '')
    run_root_rel = project_relative(project_root, run_root)
    current_run_id = str(current.get('current_run_id') or current.get('active_run_id') or '')
    current_run_root = str(current.get('current_run_root') or current.get('active_run_root') or '')
    run_status = str(run_state.get('status') or '')
    current_status = str(current.get('status') or '')
    hidden_statuses = {'completed', 'closed', 'stopped', 'stopped_by_user', 'cancelled_by_user', 'protocol_dead_end', 'abandoned', 'discarded', 'stale'}
    effective_status = run_status if run_status in hidden_statuses else current_status or run_status
    current_pointer_matches = current_run_id == run_id and current_run_root == run_root_rel
    active_tasks: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    for item in index.get('runs', []):
        if not isinstance(item, dict):
            continue
        item_run_id = str(item.get('run_id') or '')
        item_run_root = str(item.get('run_root') or '')
        item_status = str(item.get('status') or '')
        if not item_run_id or item_status in hidden_statuses:
            continue
        seen_run_ids.add(item_run_id)
        focus_selected = item_run_id == current_run_id
        active_tasks.append({'run_id': item_run_id, 'run_root': item_run_root, 'status': item_status or 'running', 'display_plan_path': project_relative(project_root, project_root / item_run_root / 'display_plan.json') if item_run_root else None, 'route_state_snapshot_path': project_relative(project_root, project_root / item_run_root / 'route_state_snapshot.json') if item_run_root else None, 'focus_selected': focus_selected, 'background_active': not focus_selected, 'close_tab_behavior': 'return_to_dialog_route_display' if focus_selected else 'keep_background_run_available'})
    if current_pointer_matches and effective_status not in hidden_statuses and (run_id not in seen_run_ids):
        active_tasks.append({'run_id': run_id, 'run_root': run_root_rel, 'status': effective_status or 'running', 'display_plan_path': project_relative(project_root, router._display_plan_path(run_root)), 'route_state_snapshot_path': project_relative(project_root, router._route_state_snapshot_path(run_root)), 'focus_selected': True, 'background_active': False, 'close_tab_behavior': 'return_to_dialog_route_display'})
    active_tasks.sort(key=lambda item: (not bool(item.get('focus_selected')), str(item.get('run_id') or '')))
    background_active_tasks = [item for item in active_tasks if item.get('background_active')]
    return {'schema_version': 'flowpilot.active_ui_task_catalog.v1', 'authority': 'index_active_runs_with_current_focus', 'current_pointer_matches_run': current_pointer_matches, 'current_pointer_is_ui_focus_only': True, 'active_tasks': active_tasks, 'background_active_tasks': background_active_tasks, 'hidden_non_current_running_index_entries': [], 'completed_abandoned_stale_history_default_visible': False}

def _route_node_checklist(router: ModuleType, node: dict[str, Any], *, node_complete: bool=False) -> list[dict[str, Any]]:
    _bind_router(router)
    raw_items = node.get('checklist')
    if not isinstance(raw_items, list):
        raw_items = node.get('required_gates')
    if not isinstance(raw_items, list):
        raw_items = node.get('acceptance_checklist')
    if not isinstance(raw_items, list):
        raw_items = []
    checklist: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_items, start=1):
        if isinstance(raw, dict):
            item_id = str(raw.get('id') or raw.get('gate_id') or raw.get('label') or f'check-{index:03d}')
            label = str(raw.get('label') or raw.get('title') or raw.get('gate') or item_id)
            status = 'completed' if node_complete else router._plan_item_status(raw.get('status'), active=False)
        else:
            item_id = str(raw)
            label = item_id.replace('_', ' ')
            status = 'completed' if node_complete else 'pending'
        checklist.append({'id': item_id, 'label': label, 'status': status})
    return checklist

def _active_route_payload(router: ModuleType, run_root: Path, route_id: str | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    route_root = run_root / 'routes'
    candidates: list[Path] = []
    if route_id:
        candidates.append(route_root / route_id / 'flow.json')
    if route_root.exists():
        candidates.extend(sorted(route_root.glob('*/flow.json')))
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            return read_json(path)
    return None

def _current_status_summary_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'display' / 'current_status_summary.json'

def _run_elapsed_seconds(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> int | None:
    _bind_router(router)
    timestamps: list[datetime] = []

    def add_timestamp(raw: object) -> None:
        parsed = _parse_utc_timestamp(raw)
        if parsed is not None:
            timestamps.append(parsed)
    for key in ('created_at', 'started_at'):
        add_timestamp(run_state.get(key))
    history = run_state.get('history')
    if isinstance(history, list):
        for item in history:
            if isinstance(item, dict):
                add_timestamp(item.get('at'))
    bootstrap = read_json_if_exists(run_root / 'bootstrap' / 'startup_state.json')
    for key in ('created_at', 'started_at'):
        add_timestamp(bootstrap.get(key))
    bootstrap_history = bootstrap.get('history')
    if isinstance(bootstrap_history, list):
        for item in bootstrap_history:
            if isinstance(item, dict):
                add_timestamp(item.get('at'))
    if not timestamps:
        return None
    started_at = min(timestamps)
    return max(0, int((datetime.now(timezone.utc) - started_at).total_seconds()))

def _route_progress_parent_map(router: ModuleType, nodes: list[dict[str, Any]]) -> dict[str, str]:
    _bind_router(router)
    parent_by_id: dict[str, str] = {}
    for node in nodes:
        node_id = _node_identifier(node)
        raw_parent = node.get('parent_node_id') or node.get('parent_id')
        if node_id and raw_parent:
            parent_by_id[node_id] = str(raw_parent)
    for node in nodes:
        node_id = _node_identifier(node)
        if not node_id:
            continue
        for child_id in router._node_child_ids(node):
            parent_by_id.setdefault(str(child_id), node_id)
    return parent_by_id

def _route_progress_completed_ids(router: ModuleType, nodes: list[dict[str, Any]], frontier: dict[str, Any]) -> set[str]:
    _bind_router(router)
    completed = {str(item) for item in frontier.get('completed_nodes') or []}
    for node in nodes:
        node_id = _node_identifier(node)
        if not node_id:
            continue
        if router._plan_item_status(node.get('status'), active=False) == 'completed':
            completed.add(node_id)
    return completed

def _route_progress_path_nodes(router: ModuleType, nodes_by_id: dict[str, dict[str, Any]], parent_by_id: dict[str, str], active_node_id: str) -> list[dict[str, Any]]:
    _bind_router(router)
    if not active_node_id or active_node_id not in nodes_by_id:
        return []
    path_ids: list[str] = []
    seen: set[str] = set()
    cursor: str | None = active_node_id
    while cursor and cursor in nodes_by_id and (cursor not in seen):
        seen.add(cursor)
        path_ids.append(cursor)
        cursor = parent_by_id.get(cursor)
    return [nodes_by_id[node_id] for node_id in reversed(path_ids) if not router._is_route_root_node(nodes_by_id[node_id])]

def _build_progress_summary(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, route: dict[str, Any], frontier: dict[str, Any], active_node_id: str, state_kind: str) -> dict[str, Any]:
    _bind_router(router)
    nodes = [node for node in router._route_nodes(route) if not router._is_route_root_node(node)]
    nodes_by_id = {_node_identifier(node): node for node in nodes if _node_identifier(node)}
    completed_ids = router._route_progress_completed_ids(nodes, frontier)
    parent_by_id = router._route_progress_parent_map(router._route_nodes(route))
    active_path = router._route_progress_path_nodes(nodes_by_id, parent_by_id, active_node_id)
    route_order = {_node_identifier(node): index for index, node in enumerate(nodes)}
    levels: list[dict[str, Any]] = []
    for level_index, node in enumerate(active_path, start=1):
        node_id = _node_identifier(node)
        parent_id = parent_by_id.get(node_id)
        siblings = [candidate for candidate in nodes if parent_by_id.get(_node_identifier(candidate)) == parent_id]
        siblings.sort(key=lambda item: route_order.get(_node_identifier(item), 0))
        sibling_ids = [_node_identifier(item) for item in siblings]
        current_index = sibling_ids.index(node_id) + 1 if node_id in sibling_ids else None
        levels.append({'level': level_index, 'total_nodes': len(siblings), 'completed_nodes': sum((1 for item_id in sibling_ids if item_id in completed_ids)), 'current_index': current_index, 'current_node_id': node_id, 'current_label': str(node.get('title') or node.get('label') or node_id)})
    route_node_ids = set(nodes_by_id)
    return {'schema_version': 'flowpilot.progress_summary.v1', 'state': state_kind, 'level_count': len(levels), 'levels': levels, 'overall_completed_nodes': len(completed_ids & route_node_ids), 'overall_total_nodes': len(route_node_ids), 'elapsed_seconds': router._run_elapsed_seconds(run_root, run_state), 'metadata_only': True, 'sealed_body_fields_excluded': True, 'evidence_table_excluded': True, 'source_fields_excluded': True, 'diagnostic_paths_excluded': True, 'hash_fields_excluded': True}

def _route_node_label(router: ModuleType, route: dict[str, Any], node_id: str) -> str:
    _bind_router(router)
    for node in router._iter_route_nodes(route):
        candidate = str(node.get('node_id') or node.get('id') or '')
        if candidate == node_id:
            return str(node.get('title') or node.get('label') or node_id)
    return node_id

def _status_summary_waiting_for(router: ModuleType, pending_action: dict[str, Any]) -> str | None:
    _bind_router(router)
    for key in ('to_role', 'waiting_for_role', 'target_role', 'actor'):
        value = str(pending_action.get(key) or '').strip()
        if value and value != 'controller':
            return value
    allowed = pending_action.get('allowed_external_events')
    if isinstance(allowed, list) and allowed:
        return 'external_event'
    return None

def _current_status_active_batch_summary(router: ModuleType, run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    summaries: list[dict[str, Any]] = []
    for batch_kind in ('material_scan', 'research', 'current_node', 'pm_role_work'):
        try:
            batch = router._active_parallel_packet_batch(run_root, batch_kind)
        except (RouterError, OSError, json.JSONDecodeError):
            continue
        if not batch:
            continue
        member_status = batch.get('member_status') if isinstance(batch.get('member_status'), dict) else {}
        if not member_status:
            member_status = {'packet_count': len(batch.get('packets') or []), 'results_returned': (batch.get('counts') or {}).get('results_returned', 0), 'missing_roles': [], 'returned_roles': [], 'partial_results_returned': False, 'all_results_returned': False}
        summaries.append({'batch_kind': batch_kind, 'batch_id': batch.get('batch_id'), 'status': batch.get('status'), 'packet_count': member_status.get('packet_count'), 'results_returned': member_status.get('results_returned'), 'missing_roles': member_status.get('missing_roles') or [], 'returned_roles': member_status.get('returned_roles') or [], 'partial_results_returned': bool(member_status.get('partial_results_returned')), 'all_results_returned': bool(member_status.get('all_results_returned')), 'controller_visibility': 'metadata_only'})
    if not summaries:
        return None
    active_partial = [item for item in summaries if item.get('partial_results_returned')]
    return {'controller_visibility': 'metadata_only', 'active_partial_batches': active_partial, 'batches': summaries}

def _build_current_status_summary(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    packet_ledger = read_json_if_exists(run_root / 'packet_ledger.json') or {}
    active_route_id = str(frontier.get('active_route_id') or run_state.get('active_route_id') or '')
    route = route_payload or router._active_route_payload(run_root, active_route_id) or {}
    active_node_id = str(frontier.get('active_node_id') or route.get('active_node_id') or '')
    node_label = router._route_node_label(route, active_node_id) if active_node_id else None
    pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    active_blocker = run_state.get('active_control_blocker') if isinstance(run_state.get('active_control_blocker'), dict) else None
    daemon_status = read_json_if_exists(_router_daemon_status_path(run_root))
    controller_ledger = router._controller_action_ledger_summary(run_root)
    run_status = str(run_state.get('status') or 'running')
    frontier_status = str(frontier.get('status') or '')
    terminal = run_status in RUN_TERMINAL_STATUSES or frontier_status in RUN_TERMINAL_STATUSES or frontier.get('terminal') is True
    waiting_for = router._status_summary_waiting_for(pending_action)
    if terminal:
        state_kind = 'terminal'
    elif active_blocker:
        state_kind = 'blocked'
    elif _action_is_passive_wait_status(pending_action):
        state_kind = 'waiting_for_role'
    elif pending_action:
        state_kind = 'controller_action_ready'
    else:
        state_kind = 'running'
    pending_controller_action_ids = controller_ledger.get('pending_action_ids') or []
    waiting_controller_action_ids = controller_ledger.get('waiting_action_ids') or []
    user_required = bool(pending_action.get('requires_user') or pending_action.get('requires_user_dialog_display_confirmation'))
    daemon_status_ok = daemon_status.get('schema_version') == ROUTER_DAEMON_STATUS_SCHEMA
    daemon_lifecycle = str(daemon_status.get('lifecycle_status') or '')
    daemon_lock_live = bool((daemon_status.get('lock') or {}).get('live')) if daemon_status_ok else False
    daemon_heartbeat = daemon_status.get('heartbeat') if isinstance(daemon_status.get('heartbeat'), dict) else {}
    daemon_liveness_check_required = not daemon_status_ok or not daemon_lock_live or daemon_heartbeat.get('status') == 'check_liveness' or (daemon_lifecycle in {'daemon_error', 'daemon_stale_or_missing'})
    controller_action_ready = state_kind == 'controller_action_ready' or bool(pending_controller_action_ids)
    if terminal:
        foreground_required_mode = 'terminal_return'
    elif user_required:
        foreground_required_mode = 'return_for_user_input'
    elif daemon_liveness_check_required:
        foreground_required_mode = 'check_liveness'
    elif controller_action_ready:
        foreground_required_mode = 'process_controller_action'
    else:
        foreground_required_mode = 'watch_router_daemon' if run_state.get('daemon_mode_enabled') else 'router_action_diagnostic'
    foreground_exit_policy = {'foreground_exit_allowed': bool(terminal), 'foreground_turn_return_allowed': bool(terminal or user_required or daemon_liveness_check_required), 'controller_stop_allowed': bool(terminal), 'run_complete': bool(terminal), 'nonterminal_controller_must_stay_attached': not bool(terminal), 'foreground_required_mode': foreground_required_mode, 'controller_must_process_pending_action_before_exit': controller_action_ready, 'controller_must_continue_standby': not terminal and (not user_required) and (not daemon_liveness_check_required) and (not controller_action_ready) and (state_kind in {'waiting_for_role', 'running'}) and bool(run_state.get('daemon_mode_enabled')), 'controller_action_ready_blocks_foreground_exit': True, 'live_daemon_wait_requires_standby': True, 'controller_stop_requires_terminal_run': True, 'normal_progress_source': 'router_daemon_status_and_controller_action_ledger'}
    labels = {'terminal': {'en': 'Run is terminal.', 'zh': '这轮任务已经进入终止状态。'}, 'blocked': {'en': 'Run is waiting for a control-plane repair.', 'zh': '当前卡在控制流程修复上。'}, 'waiting_for_role': {'en': f"Waiting for {waiting_for or 'a role'} to return a decision.", 'zh': f"正在等 {waiting_for or '某个角色'} 返回决定。"}, 'controller_action_ready': {'en': 'Controller has the next safe action ready.', 'zh': '控制器已经拿到下一步安全动作。'}, 'running': {'en': 'FlowPilot is running.', 'zh': 'FlowPilot 正在运行。'}}
    current_work_label = node_label or active_node_id or frontier_status or run_status
    project_root = _project_root_from_run_root(run_root)
    current_work = router._derive_current_work(project_root, run_root, run_state, current_wait=daemon_status.get('current_wait') if isinstance(daemon_status.get('current_wait'), dict) else None, current_action=daemon_status.get('current_action') if isinstance(daemon_status.get('current_action'), dict) else None, controller_ledger=controller_ledger)
    return {'schema_version': CURRENT_STATUS_SUMMARY_SCHEMA, 'run_id': run_state.get('run_id'), 'updated_at': utc_now(), 'state_kind': state_kind, 'headline': labels[state_kind], 'current_work': current_work, 'current_work_label': current_work_label, 'progress_summary': router._build_progress_summary(run_root, run_state, route=route, frontier=frontier, active_node_id=active_node_id, state_kind=state_kind), 'route': {'route_id': active_route_id or route.get('route_id'), 'route_version': frontier.get('route_version') or route.get('route_version'), 'active_node_id': active_node_id or None, 'active_node_label': node_label, 'completed_node_count': len(frontier.get('completed_nodes') or [])}, 'packet': {'active_packet_id': packet_ledger.get('active_packet_id'), 'status': packet_ledger.get('active_packet_status'), 'holder': packet_ledger.get('active_packet_holder'), 'active_batch': router._current_status_active_batch_summary(run_root)}, 'next_step': {'action_type': pending_action.get('action_type'), 'label': pending_action.get('label'), 'waiting_for': waiting_for, 'current_wait': daemon_status.get('current_wait') if isinstance(daemon_status.get('current_wait'), dict) else {}}, 'blocker': {'active': bool(active_blocker), 'blocker_id': active_blocker.get('blocker_id') if active_blocker else None, 'lane': active_blocker.get('handling_lane') if active_blocker else None}, 'router_daemon': {'status_path': 'runtime/router_daemon_status.json', 'daemon_mode_enabled': bool(run_state.get('daemon_mode_enabled')), 'lifecycle_status': daemon_status.get('lifecycle_status'), 'tick_interval_seconds': daemon_status.get('tick_interval_seconds') or ROUTER_DAEMON_TICK_SECONDS, 'last_tick_at': daemon_status.get('last_tick_at'), 'lock_status': (daemon_status.get('lock') or {}).get('status') if isinstance(daemon_status.get('lock'), dict) else None, 'heartbeat_status': daemon_heartbeat.get('status'), 'heartbeat_age_seconds': daemon_heartbeat.get('age_seconds'), 'heartbeat_check_after_seconds': daemon_heartbeat.get('check_after_seconds') or ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS, 'controller_liveness_check_required': daemon_liveness_check_required, 'monitor_can_decide_recovery': False, 'router_owns_waiting': True}, 'controller_action_ledger': {'exists': controller_ledger.get('exists', False), 'counts': controller_ledger.get('counts') or _controller_action_counts([]), 'active_work_count': controller_ledger.get('active_work_count', 0), 'history_done_count': controller_ledger.get('history_done_count', 0), 'passive_wait_count': controller_ledger.get('passive_wait_count', 0), 'passive_wait_action_ids': controller_ledger.get('passive_wait_action_ids') or [], 'done_rows_are_audit_history': bool(controller_ledger.get('done_rows_are_audit_history', True)), 'pending_action_ids': pending_controller_action_ids, 'waiting_action_ids': waiting_controller_action_ids}, 'foreground_exit_policy': {**foreground_exit_policy, 'user_required': user_required, 'daemon_status_ok': daemon_status_ok, 'daemon_lock_live': daemon_lock_live, 'daemon_liveness_check_required': daemon_liveness_check_required}, 'ui_contract': {'metadata_only': True, 'sealed_body_fields_excluded': True, 'evidence_table_excluded': True, 'source_fields_excluded': True, 'hash_fields_excluded': True}}

def _write_current_status_summary(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    write_json(router._current_status_summary_path(run_root), router._build_current_status_summary(run_root, run_state, route_payload=route_payload))

def _build_route_state_snapshot(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None, source_event: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    packet_ledger = read_json_if_exists(run_root / 'packet_ledger.json') or {}
    active_route_id = str(frontier.get('active_route_id') or run_state.get('active_route_id') or '')
    route = route_payload or router._active_route_payload(run_root, active_route_id) or {}
    if not active_route_id:
        active_route_id = str(route.get('route_id') or '')
    active_node_id = str(frontier.get('active_node_id') or route.get('active_node_id') or '')
    completed_nodes = {str(item) for item in frontier.get('completed_nodes') or []}
    frontier_status = str(frontier.get('status') or '')
    frontier_terminal = bool(frontier.get('terminal')) or frontier_status in RUN_TERMINAL_STATUSES
    run_id = str(run_state.get('run_id') or '')
    current_run_id = str(current.get('current_run_id') or current.get('active_run_id') or '')
    current_run_root = str(current.get('current_run_root') or current.get('active_run_root') or '')
    run_root_rel = project_relative(project_root, run_root)
    background_running = [{'run_id': str(item.get('run_id') or ''), 'status': str(item.get('status') or ''), 'run_root': str(item.get('run_root') or ''), 'focus_selected': False} for item in index.get('runs', []) if isinstance(item, dict) and item.get('status') == 'running' and (str(item.get('run_id') or '') != current_run_id)]
    nodes: list[dict[str, Any]] = []
    for position, node in enumerate(router._iter_route_nodes(route), start=1):
        node_id = str(node.get('node_id') or node.get('id') or f'node-{position:03d}')
        is_frontier_current = node_id == active_node_id
        node_complete = node_id in completed_nodes
        status = 'completed' if node_complete else router._plan_item_status(node.get('status'), active=is_frontier_current and (not frontier_terminal))
        node_complete = status == 'completed'
        nodes.append({'id': node_id, 'label': str(node.get('title') or node.get('label') or node_id), 'status': status, 'is_active': is_frontier_current and (not node_complete) and (not frontier_terminal), 'is_frontier_current': is_frontier_current, 'is_selected': False, 'is_complete': node_complete, 'completion_source': 'execution_frontier.completed_nodes' if node_id in completed_nodes else 'route_status', 'selection_source': 'ui_overlay_only', 'checklist': router._route_node_checklist(node, node_complete=node_complete), 'children': node.get('children') if isinstance(node.get('children'), list) else []})
    pending_action = run_state.get('pending_action') if isinstance(run_state.get('pending_action'), dict) else {}
    created_at = utc_now()
    continuation_quarantine = router._build_continuation_quarantine_record(project_root, run_root, run_state, created_at=created_at)
    return {'schema_version': ROUTE_STATE_SNAPSHOT_SCHEMA, 'run_id': run_id, 'run_root': run_root_rel, 'created_at': created_at, 'source_event': source_event, 'active_ui_task_catalog': router._active_ui_task_catalog(project_root, run_root, run_state), 'continuation_quarantine': continuation_quarantine, 'authority': {'active_source': 'index_active_runs_with_current_focus', 'current_pointer_path': '.flowpilot/current.json', 'current_pointer_is_ui_focus_only': True, 'current_pointer_matches_run': current_run_id == run_id and current_run_root == run_root_rel, 'index_running_entries_are_parallel_run_authority': True, 'background_running_index_entries': background_running, 'stale_running_index_entries': []}, 'route': {'route_id': active_route_id or route.get('route_id'), 'route_version': route.get('route_version') or frontier.get('route_version'), 'active_node_id': active_node_id or None, 'completed_nodes': sorted(completed_nodes), 'terminal': frontier_terminal, 'selected_node_id': None, 'selection_state_is_ui_overlay_only': True, 'nodes': nodes}, 'frontier': {'path': project_relative(project_root, run_root / 'execution_frontier.json'), 'status': frontier.get('status'), 'active_route_id': frontier.get('active_route_id'), 'active_node_id': frontier.get('active_node_id'), 'route_version': frontier.get('route_version')}, 'state': {'path': project_relative(project_root, router.run_state_path(run_root)), 'status': run_state.get('status'), 'flags': dict(run_state.get('flags') or {})}, 'packet_ledger': {'path': project_relative(project_root, run_root / 'packet_ledger.json'), 'active_packet_id': packet_ledger.get('active_packet_id'), 'active_packet_status': packet_ledger.get('active_packet_status'), 'active_packet_holder': packet_ledger.get('active_packet_holder'), 'latest_packet_chain_audit_passed': packet_ledger.get('latest_packet_chain_audit_passed'), 'latest_barrier_bundle_audit_passed': packet_ledger.get('latest_barrier_bundle_audit_passed')}, 'next_action': {'action_type': pending_action.get('action_type'), 'to_role': pending_action.get('to_role'), 'label': pending_action.get('label'), 'allowed_external_events': pending_action.get('allowed_external_events') or []}}

def _write_route_state_snapshot(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None, source_event: str | None=None) -> None:
    _bind_router(router)
    snapshot = router._build_route_state_snapshot(project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)
    if isinstance(snapshot.get('continuation_quarantine'), dict):
        router._write_continuation_quarantine(project_root, run_root, run_state, snapshot['continuation_quarantine'])
    write_json(router._route_state_snapshot_path(run_root), snapshot)
    router._write_current_status_summary(run_root, run_state, route_payload=route_payload)

def _mark_display_plan_dirty(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    run_state['visible_plan_sync'] = {}
    run_state.setdefault('flags', {})['visible_plan_synced'] = False

def _write_display_plan_from_route(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, route_id: str, route_version: int, route_payload: dict[str, Any], active_node_id: str | None, source_event: str) -> None:
    _bind_router(router)
    nodes = router._display_route_nodes(route_payload)
    items = []
    for index, node in enumerate(nodes, start=1):
        node_id = str(node.get('node_id') or node.get('id') or f'node-{index:03d}')
        items.append({'id': node_id, 'label': str(node.get('title') or node.get('label') or node_id), 'status': router._route_item_status(run_root, node_id, active_node_id=active_node_id, raw_status=node.get('status'))})
    if not items:
        items.append({'id': 'route_pending', 'label': 'PM route', 'status': 'pending'})
    plan = {'schema_version': DISPLAY_PLAN_SCHEMA, 'run_id': run_state['run_id'], 'source_role': 'project_manager', 'source_event': source_event, 'scope': 'route', 'title': str(route_payload.get('title') or route_payload.get('name') or 'FlowPilot route'), 'route_id': route_id, 'route_version': route_version, 'display_depth': router._route_display_depth(route_payload), 'items': items, 'current_node_id': active_node_id, 'active_path': router._route_active_path(route_payload, active_node_id), 'hidden_leaf_progress': router._route_hidden_leaf_progress(route_payload), 'controller_may_invent_route_items': False, 'updated_at': utc_now()}
    write_json(router._display_plan_path(run_root), plan)
    router._write_route_state_snapshot(project_root, run_root, run_state, route_payload=route_payload, source_event=source_event)
    router._mark_display_plan_dirty(run_state)

def _update_display_plan_current_node(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, node_id: str, node_title: str, checklist: list[dict[str, Any]], source_event: str) -> None:
    _bind_router(router)
    plan = read_json_if_exists(router._display_plan_path(run_root))
    if not plan:
        plan = router._waiting_for_pm_display_plan(run_state)
    items = plan.setdefault('items', [])
    for item in items:
        if isinstance(item, dict):
            item_id = str(item.get('id') or item.get('node_id') or '')
            item['status'] = router._route_item_status(run_root, item_id, active_node_id=node_id, raw_status=item.get('status'))
    plan.update({'schema_version': DISPLAY_PLAN_SCHEMA, 'run_id': run_state['run_id'], 'source_role': 'project_manager', 'source_event': source_event, 'scope': 'node', 'current_node_id': node_id, 'current_node': {'id': node_id, 'label': node_title, 'checklist': checklist}, 'controller_may_invent_route_items': False, 'updated_at': utc_now()})
    write_json(router._display_plan_path(run_root), plan)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    router._mark_display_plan_dirty(run_state)

def _latest_pre_route_phase(router: ModuleType, run_state: dict[str, Any]) -> str | None:
    _bind_router(router)
    for delivery in reversed(run_state.get('delivered_cards') or []):
        if not isinstance(delivery, dict):
            continue
        phase = CARD_PHASE_BY_ID.get(str(delivery.get('card_id') or ''))
        if phase:
            return phase
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    for phase, _label, flag in reversed(PRE_ROUTE_PHASE_ITEMS):
        if flags.get(flag):
            return phase
    return None

def _sync_execution_frontier_phase(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    phase = router._latest_pre_route_phase(run_state)
    if not phase:
        return
    frontier_path = run_root / 'execution_frontier.json'
    frontier = read_json_if_exists(frontier_path)
    if str(frontier.get('status') or run_state.get('status') or '') in RUN_TERMINAL_STATUSES:
        return
    run_state['phase'] = phase
    frontier['phase'] = phase
    if not frontier.get('active_route_id'):
        frontier['status'] = phase
    frontier['updated_at'] = utc_now()
    write_json(frontier_path, frontier)

def _write_pre_route_phase_display_plan_if_needed(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    phase = router._latest_pre_route_phase(run_state)
    if phase is None:
        return False
    existing = read_json_if_exists(router._display_plan_path(run_root))
    if existing.get('scope') in {'route', 'node'} and existing.get('source_role') == 'project_manager':
        return False
    phase_order = [item[0] for item in PRE_ROUTE_PHASE_ITEMS]
    active_index = phase_order.index(phase) if phase in phase_order else 0
    items = []
    for index, (item_id, label, _flag) in enumerate(PRE_ROUTE_PHASE_ITEMS):
        if index < active_index:
            status = 'completed'
        elif index == active_index:
            status = 'in_progress'
        else:
            status = 'pending'
        items.append({'id': item_id, 'label': label, 'status': status})
    plan = {'schema_version': DISPLAY_PLAN_SCHEMA, 'run_id': run_state['run_id'], 'source_role': 'controller', 'source_event': 'derived_pre_route_phase_sync', 'scope': 'pre_route_phase', 'title': 'FlowPilot route preparation', 'items': items, 'current_node_id': None, 'route_authority': 'none_until_pm_route_draft', 'controller_may_invent_route_items': False, 'updated_at': utc_now()}
    write_json(router._display_plan_path(run_root), plan)
    return True

def _reconcile_non_current_running_index_entries(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> int:
    _bind_router(router)
    index_path = project_root / '.flowpilot' / 'index.json'
    index = read_json_if_exists(index_path) or {}
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    updated = 0
    now = utc_now()
    for item in runs:
        if not isinstance(item, dict):
            continue
        if item.get('run_id') == run_state.get('run_id'):
            item['status'] = run_state.get('status') or item.get('status')
            item['updated_at'] = now
    if runs:
        index['runs'] = runs
        index['updated_at'] = now
        write_json(index_path, index)
    return updated

def _sync_derived_run_views(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, reason: str, update_display: bool=True) -> None:
    _bind_router(router)
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    _sync_child_skill_manifest_review_approval(project_root, run_root)
    router._sync_execution_frontier_phase(run_root, run_state)
    router._reconcile_non_current_running_index_entries(project_root, run_state)
    display_updated = router._write_pre_route_phase_display_plan_if_needed(project_root, run_root, run_state) if update_display else False
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event=reason)
    if display_updated:
        sync_payload = router._display_plan_sync_payload(project_root, run_root, run_state)
        run_state['visible_plan_sync'] = {'display_plan_path': sync_payload['display_plan_path'], 'route_state_snapshot_path': sync_payload['route_state_snapshot_path'], 'route_state_snapshot_hash': sync_payload['route_state_snapshot_hash'], 'current_status_summary_path': sync_payload.get('current_status_summary_path'), 'current_status_summary_hash': sync_payload.get('current_status_summary_hash'), 'projection_hash': sync_payload['projection_hash'], 'synced_at': utc_now(), 'host_action': 'derived_pre_route_phase_projection'}
        run_state.setdefault('flags', {})['visible_plan_synced'] = True

def _write_display_plan_from_pm_payload(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, source_event: str) -> None:
    _bind_router(router)
    raw_plan = payload.get('display_plan')
    if not isinstance(raw_plan, dict):
        return
    raw_items = raw_plan.get('items')
    if not isinstance(raw_items, list) or not raw_items:
        raise RouterError(f'{source_event} display_plan requires non-empty items')
    items = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise RouterError(f'{source_event} display_plan items must be objects')
        item_id = item.get('id') or item.get('node_id') or f'item-{index:03d}'
        items.append({'id': str(item_id), 'label': str(item.get('label') or item.get('title') or item_id), 'status': router._route_item_status(run_root, str(item_id), active_node_id=str(raw_plan.get('current_node_id') or ''), raw_status=item.get('status'))})
    plan = {'schema_version': DISPLAY_PLAN_SCHEMA, 'run_id': run_state['run_id'], 'source_role': 'project_manager', 'source_event': source_event, 'scope': str(raw_plan.get('scope') or 'route'), 'title': str(raw_plan.get('title') or 'FlowPilot route'), 'items': items, 'current_node_id': raw_plan.get('current_node_id'), 'controller_may_invent_route_items': False, 'updated_at': utc_now()}
    if isinstance(raw_plan.get('current_node'), dict):
        plan['current_node'] = raw_plan['current_node']
    write_json(router._display_plan_path(run_root), plan)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event=source_event)
    router._mark_display_plan_dirty(run_state)

__all__ = (
    '_active_ui_task_catalog',
    '_route_node_checklist',
    '_active_route_payload',
    '_current_status_summary_path',
    '_run_elapsed_seconds',
    '_route_progress_parent_map',
    '_route_progress_completed_ids',
    '_route_progress_path_nodes',
    '_build_progress_summary',
    '_route_node_label',
    '_status_summary_waiting_for',
    '_current_status_active_batch_summary',
    '_build_current_status_summary',
    '_write_current_status_summary',
    '_build_route_state_snapshot',
    '_write_route_state_snapshot',
    '_mark_display_plan_dirty',
    '_write_display_plan_from_route',
    '_update_display_plan_current_node',
    '_latest_pre_route_phase',
    '_sync_execution_frontier_phase',
    '_write_pre_route_phase_display_plan_if_needed',
    '_reconcile_non_current_running_index_entries',
    '_sync_derived_run_views',
    '_write_display_plan_from_pm_payload',
)

_LOCAL_NAMES = set(globals())
