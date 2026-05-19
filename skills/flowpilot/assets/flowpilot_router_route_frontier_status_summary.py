"""Cohesive child helpers for FlowPilot route-frontier compatibility facades."""

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
    pending_controller_action_ids = controller_ledger.get('pending_action_ids') or []
    waiting_controller_action_ids = controller_ledger.get('waiting_action_ids') or []
    source_action_id = str(pending_action.get('controller_action_id') or '') or None
    if source_action_id is None and pending_action:
        source_action_id = router._controller_action_id_for_action(pending_action)
    pending_action_is_current_executable = bool(pending_action and not _action_is_passive_wait_status(pending_action) and source_action_id in pending_controller_action_ids)
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
    elif pending_action_is_current_executable:
        state_kind = 'controller_action_ready'
    else:
        state_kind = 'running'
    user_required = bool(pending_action_is_current_executable and (pending_action.get('requires_user') or pending_action.get('requires_user_dialog_display_confirmation')))
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
    controller_must_continue_standby = not terminal and (not user_required) and (not daemon_liveness_check_required) and (not controller_action_ready) and (state_kind in {'waiting_for_role', 'running'}) and bool(run_state.get('daemon_mode_enabled'))
    user_status_update_allowed = bool(terminal or user_required or daemon_liveness_check_required)
    no_pending_controller_actions = not bool(pending_controller_action_ids or waiting_controller_action_ids)
    final_answer_allowed = bool(terminal and no_pending_controller_actions and (not controller_must_continue_standby))
    final_answer_blocked_reason = None
    if not final_answer_allowed:
        if not terminal:
            final_answer_blocked_reason = 'nonterminal_controller_must_stay_attached'
        elif not no_pending_controller_actions:
            final_answer_blocked_reason = 'pending_controller_actions_remain'
        else:
            final_answer_blocked_reason = 'continuous_standby_or_duty_still_active'
    foreground_exit_policy = {'foreground_exit_allowed': final_answer_allowed, 'foreground_turn_return_allowed': user_status_update_allowed, 'foreground_turn_return_is_not_controller_stop': True, 'user_status_update_allowed': user_status_update_allowed, 'controller_patrol_required': controller_must_continue_standby, 'controller_stop_allowed': bool(terminal), 'run_complete': bool(terminal), 'nonterminal_controller_must_stay_attached': not bool(terminal), 'foreground_required_mode': foreground_required_mode, 'controller_must_process_pending_action_before_exit': controller_action_ready, 'controller_must_continue_standby': controller_must_continue_standby, 'controller_action_ready_blocks_foreground_exit': True, 'live_daemon_wait_requires_standby': True, 'controller_stop_requires_terminal_run': True, 'user_status_update_is_not_controller_stop': True, 'status_projection_is_not_stop_authority': True, 'normal_progress_source': 'router_daemon_status_and_controller_action_ledger', 'final_answer_preflight': {'final_answer_allowed': final_answer_allowed, 'terminal_state_required': True, 'terminal_state_observed': bool(terminal), 'controller_stop_allowed_required': True, 'controller_stop_allowed': bool(terminal), 'no_pending_controller_actions_required': True, 'no_pending_controller_actions': no_pending_controller_actions, 'continuous_standby_not_in_progress_required': True, 'continuous_standby_status': 'released' if final_answer_allowed else ('in_progress' if controller_must_continue_standby else 'not_active'), 'user_status_update_is_not_stop_permission': True, 'status_projection_is_not_stop_authority': True, 'authority_source': 'router_daemon_status_and_controller_action_ledger', 'blocked_reason': final_answer_blocked_reason}}
    labels = {'terminal': {'en': 'Run is terminal.', 'zh': '这轮任务已经进入终止状态。'}, 'blocked': {'en': 'Run is waiting for a control-plane repair.', 'zh': '当前卡在控制流程修复上。'}, 'waiting_for_role': {'en': f"Waiting for {waiting_for or 'a role'} to return a decision.", 'zh': f"正在等 {waiting_for or '某个角色'} 返回决定。"}, 'controller_action_ready': {'en': 'Controller has the next safe action ready.', 'zh': '控制器已经拿到下一步安全动作。'}, 'running': {'en': 'FlowPilot is running.', 'zh': 'FlowPilot 正在运行。'}}
    current_work_label = node_label or active_node_id or frontier_status or run_status
    project_root = _project_root_from_run_root(run_root)
    current_work = router._derive_current_work(project_root, run_root, run_state, current_wait=daemon_status.get('current_wait') if isinstance(daemon_status.get('current_wait'), dict) else None, current_action=daemon_status.get('current_action') if isinstance(daemon_status.get('current_action'), dict) else None, controller_ledger=controller_ledger)
    next_step_fresh_for_controller_decision = bool(controller_action_ready and pending_action and not _action_is_passive_wait_status(pending_action) and source_action_id in pending_controller_action_ids)
    next_step = {'action_type': pending_action.get('action_type'), 'label': pending_action.get('label'), 'waiting_for': waiting_for, 'current_wait': daemon_status.get('current_wait') if isinstance(daemon_status.get('current_wait'), dict) else {}, 'source_action_id': source_action_id, 'source_status': 'pending' if next_step_fresh_for_controller_decision else ('display_only_or_stale' if pending_action else 'none'), 'fresh_for_controller_decision': next_step_fresh_for_controller_decision, 'display_only': not next_step_fresh_for_controller_decision, 'controller_stop_authority': False, 'stale_projection_cannot_authorize_stop': True}
    projection_authority = {'projection_kind': 'display_only_status_summary', 'display_only': True, 'controller_stop_authority': False, 'controller_progress_authority': False, 'control_authorities': ['runtime/router_daemon_status.json', 'runtime/controller_action_ledger.json'], 'next_step_fresh_for_controller_decision': next_step_fresh_for_controller_decision, 'stale_projection_cannot_authorize_stop': True, 'user_status_update_is_not_controller_stop': True, 'generated_from': ['run_state', 'execution_frontier', 'packet_ledger', 'router_daemon_status', 'controller_action_ledger']}
    return {'schema_version': CURRENT_STATUS_SUMMARY_SCHEMA, 'run_id': run_state.get('run_id'), 'updated_at': utc_now(), 'state_kind': state_kind, 'headline': labels[state_kind], 'current_work': current_work, 'current_work_label': current_work_label, 'progress_summary': router._build_progress_summary(run_root, run_state, route=route, frontier=frontier, active_node_id=active_node_id, state_kind=state_kind), 'projection_authority': projection_authority, 'route': {'route_id': active_route_id or route.get('route_id'), 'route_version': frontier.get('route_version') or route.get('route_version'), 'active_node_id': active_node_id or None, 'active_node_label': node_label, 'completed_node_count': len(frontier.get('completed_nodes') or [])}, 'packet': {'active_packet_id': packet_ledger.get('active_packet_id'), 'status': packet_ledger.get('active_packet_status'), 'holder': packet_ledger.get('active_packet_holder'), 'active_batch': router._current_status_active_batch_summary(run_root)}, 'next_step': next_step, 'blocker': {'active': bool(active_blocker), 'blocker_id': active_blocker.get('blocker_id') if active_blocker else None, 'lane': active_blocker.get('handling_lane') if active_blocker else None}, 'router_daemon': {'status_path': 'runtime/router_daemon_status.json', 'daemon_mode_enabled': bool(run_state.get('daemon_mode_enabled')), 'lifecycle_status': daemon_status.get('lifecycle_status'), 'tick_interval_seconds': daemon_status.get('tick_interval_seconds') or ROUTER_DAEMON_TICK_SECONDS, 'last_tick_at': daemon_status.get('last_tick_at'), 'lock_status': (daemon_status.get('lock') or {}).get('status') if isinstance(daemon_status.get('lock'), dict) else None, 'heartbeat_status': daemon_heartbeat.get('status'), 'heartbeat_age_seconds': daemon_heartbeat.get('age_seconds'), 'heartbeat_check_after_seconds': daemon_heartbeat.get('check_after_seconds') or ROUTER_DAEMON_HEARTBEAT_CHECK_SECONDS, 'controller_liveness_check_required': daemon_liveness_check_required, 'monitor_can_decide_recovery': False, 'router_owns_waiting': True}, 'controller_action_ledger': {'exists': controller_ledger.get('exists', False), 'counts': controller_ledger.get('counts') or _controller_action_counts([]), 'active_work_count': controller_ledger.get('active_work_count', 0), 'history_done_count': controller_ledger.get('history_done_count', 0), 'passive_wait_count': controller_ledger.get('passive_wait_count', 0), 'passive_wait_action_ids': controller_ledger.get('passive_wait_action_ids') or [], 'done_rows_are_audit_history': bool(controller_ledger.get('done_rows_are_audit_history', True)), 'pending_action_ids': pending_controller_action_ids, 'waiting_action_ids': waiting_controller_action_ids}, 'foreground_exit_policy': {**foreground_exit_policy, 'user_required': user_required, 'daemon_status_ok': daemon_status_ok, 'daemon_lock_live': daemon_lock_live, 'daemon_liveness_check_required': daemon_liveness_check_required}, 'ui_contract': {'metadata_only': True, 'sealed_body_fields_excluded': True, 'evidence_table_excluded': True, 'source_fields_excluded': True, 'hash_fields_excluded': True}}


def _write_current_status_summary(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, route_payload: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    write_json(router._current_status_summary_path(run_root), router._build_current_status_summary(run_root, run_state, route_payload=route_payload))


__all__ = (
    '_route_progress_parent_map',
    '_route_progress_completed_ids',
    '_route_progress_path_nodes',
    '_build_progress_summary',
    '_route_node_label',
    '_status_summary_waiting_for',
    '_current_status_active_batch_summary',
    '_build_current_status_summary',
    '_write_current_status_summary',
)

_LOCAL_NAMES = set(globals())
