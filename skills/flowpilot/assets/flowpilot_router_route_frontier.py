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

def _flatten_route_nodes(router: ModuleType, raw_nodes: list[Any], *, parent_node_id: str | None=None, depth: int=1) -> list[dict[str, Any]]:
    _bind_router(router)
    flattened: list[dict[str, Any]] = []
    for raw_node in raw_nodes:
        if not isinstance(raw_node, dict):
            continue
        node = dict(raw_node)
        node_id = _node_identifier(node)
        if not node_id:
            continue
        node.setdefault('node_id', node_id)
        if parent_node_id and (not node.get('parent_node_id')):
            node['parent_node_id'] = parent_node_id
        if not node.get('depth'):
            node['_computed_depth'] = depth
        flattened.append(node)
        flattened.extend(router._flatten_route_nodes(_inline_child_nodes(node), parent_node_id=node_id, depth=depth + 1))
    return flattened

def _route_nodes(router: ModuleType, route: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    return router._flatten_route_nodes(_raw_route_nodes(route))

def _route_node_depth(router: ModuleType, node: dict[str, Any]) -> int:
    _bind_router(router)
    raw_depth = node.get('depth', node.get('_computed_depth', 1))
    try:
        return max(0, int(raw_depth))
    except (TypeError, ValueError):
        return 1

def _route_display_depth(router: ModuleType, route: dict[str, Any]) -> int:
    _bind_router(router)
    display = route.get('display') if isinstance(route.get('display'), dict) else {}
    raw_depth = display.get('display_depth') or route.get('display_depth') or 1
    try:
        return max(1, int(raw_depth))
    except (TypeError, ValueError):
        return 1

def _is_route_root_node(router: ModuleType, node: dict[str, Any]) -> bool:
    _bind_router(router)
    explicit = str(node.get('node_kind') or node.get('kind') or '').strip().lower()
    if explicit == 'root':
        return True
    raw_depth = node['depth'] if 'depth' in node else node.get('route_depth')
    try:
        return int(raw_depth) == 0
    except (TypeError, ValueError):
        return False

def _display_route_nodes(router: ModuleType, route: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    display_depth = router._route_display_depth(route)
    nodes = router._route_nodes(route)
    visible = [node for node in nodes if not router._is_route_root_node(node) and (node.get('user_visible') is True or router._route_node_depth(node) <= display_depth)]
    return visible or [node for node in nodes if not router._is_route_root_node(node)]

def _route_active_path(router: ModuleType, route: dict[str, Any], active_node_id: str | None) -> list[dict[str, str]]:
    _bind_router(router)
    if not active_node_id:
        return []
    nodes = router._route_nodes(route)
    by_id = {_node_identifier(node): node for node in nodes if _node_identifier(node)}
    if str(active_node_id) not in by_id:
        return []
    path: list[dict[str, str]] = []
    seen: set[str] = set()
    cursor: str | None = str(active_node_id)
    while cursor and cursor in by_id and (cursor not in seen):
        seen.add(cursor)
        node = by_id[cursor]
        path.append({'id': cursor, 'label': str(node.get('title') or node.get('label') or cursor), 'node_kind': router._node_kind(node)})
        parent_id = node.get('parent_node_id')
        cursor = str(parent_id) if parent_id else None
    return [item for item in reversed(path) if item.get('node_kind') != 'root']

def _route_hidden_leaf_progress(router: ModuleType, route: dict[str, Any]) -> dict[str, int]:
    _bind_router(router)
    display_depth = router._route_display_depth(route)
    hidden_leaf_nodes = [node for node in router._route_nodes(route) if router._route_node_depth(node) > display_depth and router._node_kind(node) == 'leaf']
    completed = [node for node in hidden_leaf_nodes if str(node.get('status') or '').lower() in {'complete', 'completed', 'done', 'passed'}]
    return {'completed': len(completed), 'total': len(hidden_leaf_nodes)}

def _is_leaf_readiness_passed(router: ModuleType, node: dict[str, Any], plan: dict[str, Any] | None=None) -> bool:
    _bind_router(router)
    candidates = []
    if isinstance(node.get('leaf_readiness_gate'), dict):
        candidates.append(node['leaf_readiness_gate'])
    if plan and isinstance(plan.get('leaf_readiness_gate'), dict):
        candidates.append(plan['leaf_readiness_gate'])
    if not candidates:
        return False
    return any((str(gate.get('status') or '').lower() in {'pass', 'passed', 'approved'} for gate in candidates))

def _node_kind(router: ModuleType, node: dict[str, Any]) -> str:
    _bind_router(router)
    raw_kind = str(node.get('node_kind') or node.get('kind') or '').lower()
    if raw_kind in {'parent', 'module', 'leaf', 'repair'}:
        return raw_kind
    if router._node_child_ids(node):
        return 'parent'
    return 'leaf'

def _route_mutation_superseded_nodes(router: ModuleType, item: dict[str, Any]) -> list[str]:
    _bind_router(router)
    seen: set[str] = set()
    merged: list[str] = []
    for key in ('superseded_nodes', 'affected_sibling_nodes'):
        for node_id in item.get(key) or []:
            node_id_text = str(node_id)
            if node_id_text and node_id_text not in seen:
                seen.add(node_id_text)
                merged.append(node_id_text)
    return merged

def _effective_route_nodes(router: ModuleType, route: dict[str, Any], mutations: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    superseded = {str(node_id) for item in mutations.get('items', []) if isinstance(item, dict) for node_id in router._route_mutation_superseded_nodes(item)}
    effective = []
    for node in router._route_nodes(route):
        node_id = str(node.get('node_id') or node.get('id'))
        if node_id in superseded or node.get('status') in {'superseded', 'stale', 'failed'}:
            continue
        effective.append(node)
    return effective

def _effective_child_ids(router: ModuleType, node: dict[str, Any], nodes_by_id: dict[str, dict[str, Any]]) -> list[str]:
    _bind_router(router)
    return [child_id for child_id in router._node_child_ids(node) if child_id in nodes_by_id]

def _ready_parent_scope_after_child_completion(router: ModuleType, nodes_by_id: dict[str, dict[str, Any]], completed: set[str], current_node_id: str) -> str | None:
    _bind_router(router)
    current = nodes_by_id.get(str(current_node_id))
    cursor = str(current.get('parent_node_id') or '') if current else ''
    seen: set[str] = set()
    while cursor and cursor in nodes_by_id and (cursor not in seen):
        seen.add(cursor)
        node = nodes_by_id[cursor]
        if not router._is_route_root_node(node) and cursor not in completed and (router._node_kind(node) != 'leaf'):
            child_ids = router._effective_child_ids(node, nodes_by_id)
            if child_ids and set(child_ids).issubset(completed):
                return cursor
        parent_id = node.get('parent_node_id')
        cursor = str(parent_id) if parent_id else ''
    return None

def _next_effective_node_id(router: ModuleType, route: dict[str, Any], mutations: dict[str, Any], completed_nodes: list[str], current_node_id: str) -> str | None:
    _bind_router(router)
    effective_nodes = router._effective_route_nodes(route, mutations)
    effective_ids = [str(node.get('node_id') or node.get('id')) for node in effective_nodes]
    if not effective_ids:
        return None
    try:
        start = effective_ids.index(current_node_id) + 1
    except ValueError:
        start = 0
    completed = set(completed_nodes)
    nodes_by_id = {str(node.get('node_id') or node.get('id')): node for node in effective_nodes}
    ready_parent_id = router._ready_parent_scope_after_child_completion(nodes_by_id, completed, current_node_id)
    if ready_parent_id:
        return ready_parent_id
    for node_id in effective_ids[start:] + effective_ids[:start]:
        if node_id not in completed:
            node = nodes_by_id.get(node_id) or {}
            if router._node_kind(node) != 'leaf':
                if router._is_route_root_node(node):
                    continue
                return node_id
            return node_id
    return None

def _route_memory_root(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'route_memory'

def _route_history_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._route_memory_root(run_root) / 'route_history_index.json'

def _pm_prior_path_context_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._route_memory_root(run_root) / 'pm_prior_path_context.json'

def _route_memory_ready(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    return bool(flags.get('route_history_index_refreshed')) and bool(flags.get('pm_prior_path_context_refreshed')) and router._route_history_index_path(run_root).exists() and router._pm_prior_path_context_path(run_root).exists()

def _display_plan_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'display_plan.json'

def _route_state_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'route_state_snapshot.json'

def _route_display_refresh_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'display' / 'route_display_refresh.json'

def _optional_source_path(router: ModuleType, project_root: Path, path: Path) -> str | None:
    _bind_router(router)
    return project_relative(project_root, path) if path.exists() else None

def _plan_item_status(router: ModuleType, raw_status: Any, *, active: bool=False) -> str:
    _bind_router(router)
    status = str(raw_status or '').lower()
    if active:
        return 'in_progress'
    if status in {'complete', 'completed', 'done', 'passed'}:
        return 'completed'
    if status in {'active', 'running', 'current', 'in_progress'}:
        return 'in_progress'
    return 'pending'

def _frontier_completed_node_ids(router: ModuleType, run_root: Path) -> set[str]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    completed = frontier.get('completed_nodes') if isinstance(frontier, dict) else []
    return {str(node_id) for node_id in completed or []}

def _route_item_status(router: ModuleType, run_root: Path, node_id: str, *, active_node_id: str | None, raw_status: Any=None) -> str:
    _bind_router(router)
    if node_id in router._frontier_completed_node_ids(run_root):
        return 'completed'
    if active_node_id and node_id == active_node_id:
        return 'in_progress'
    status = str(raw_status or '').lower()
    if status in {'complete', 'completed', 'done', 'passed'}:
        return 'completed'
    return 'pending'

def _display_plan_projection(router: ModuleType, plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    current_node_id = plan.get('current_node_id')

    def _projected_status(item: dict[str, Any]) -> str:
        item_id = str(item.get('id') or item.get('node_id') or '')
        status = str(item.get('status') or '').lower()
        if status in {'complete', 'completed', 'done', 'passed'}:
            return 'completed'
        if item_id == str(current_node_id or ''):
            return 'in_progress'
        return 'pending'
    return {'title': str(plan.get('title') or 'FlowPilot'), 'items': [{'id': str(item.get('id') or item.get('node_id') or f'item-{index:03d}'), 'label': str(item.get('label') or item.get('title') or item.get('id') or f'Item {index}'), 'status': _projected_status(item)} for index, item in enumerate(plan.get('items') or [], start=1) if isinstance(item, dict)], 'current_node_id': current_node_id, 'current_node': plan.get('current_node') if isinstance(plan.get('current_node'), dict) else None, 'active_path': plan.get('active_path') if isinstance(plan.get('active_path'), list) else [], 'hidden_leaf_progress': plan.get('hidden_leaf_progress') if isinstance(plan.get('hidden_leaf_progress'), dict) else None}

def _waiting_for_pm_display_plan(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': DISPLAY_PLAN_SCHEMA, 'run_id': run_state['run_id'], 'source_role': 'controller', 'scope': 'startup_waiting_for_pm', 'title': 'FlowPilot', 'items': [{'id': 'await_pm_route', 'label': 'Waiting for PM route', 'status': 'in_progress'}], 'current_node_id': None, 'route_authority': 'none_until_pm_display_plan', 'controller_may_invent_route_items': False, 'updated_at': utc_now()}

def _current_display_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del project_root
    path = router._display_plan_path(run_root)
    if path.exists():
        return read_json(path)
    return router._waiting_for_pm_display_plan(run_state)

def _display_plan_sync_payload(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    plan = router._current_display_plan(project_root, run_root, run_state)
    projection = router._display_plan_projection(plan)
    digest = hashlib.sha256(json.dumps(projection, sort_keys=True).encode('utf-8')).hexdigest()
    snapshot_path = router._route_state_snapshot_path(run_root)
    snapshot_digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest() if snapshot_path.exists() else None
    status_summary_path = router._current_status_summary_path(run_root)
    status_summary_digest = hashlib.sha256(status_summary_path.read_bytes()).hexdigest() if status_summary_path.exists() else None
    daemon_status_path = _router_daemon_status_path(run_root)
    daemon_status_digest = hashlib.sha256(daemon_status_path.read_bytes()).hexdigest() if daemon_status_path.exists() else None
    route_sign = router._route_map_route_sign_payload(project_root, write=False, mark_chat_displayed=False)
    route_sign_available = router._route_sign_has_canonical_route(route_sign)
    display_kind = router._display_plan_display_kind(projection)
    dialog_fields = router._display_route_sign_user_dialog_fields(route_sign) if route_sign_available else router._startup_waiting_internal_display_fields() if display_kind == 'startup_waiting_state' else router._display_plan_user_dialog_fields(projection)
    display_degraded_reason = None
    if not route_sign_available:
        display_degraded_reason = 'startup_waiting_for_pm_route' if display_kind == 'startup_waiting_state' else 'canonical_route_source_unavailable'
    route_display_refresh = flowpilot_runtime_closure.route_display_refresh_record(run_id=str(run_state.get('run_id') or ''), display_plan_path=project_relative(project_root, router._display_plan_path(run_root)), route_state_snapshot_path=project_relative(project_root, snapshot_path), route_state_snapshot_hash=snapshot_digest, projection_hash=digest, route_sign_markdown_path=route_sign.get('markdown_preview_path'), route_sign_mermaid_sha256=route_sign.get('mermaid_sha256'), display_kind=display_kind, refreshed_at=utc_now())
    refresh_issues = flowpilot_runtime_closure.validate_route_display_refresh_record(route_display_refresh)
    if refresh_issues:
        raise RouterError(f'route display refresh invariant failed: {refresh_issues}')
    route_display_refresh['path'] = project_relative(project_root, router._route_display_refresh_path(run_root))
    return {'display_plan_path': project_relative(project_root, router._display_plan_path(run_root)), 'display_plan_exists': router._display_plan_path(run_root).exists(), 'route_state_snapshot_path': project_relative(project_root, snapshot_path), 'route_state_snapshot_exists': snapshot_path.exists(), 'route_state_snapshot_hash': snapshot_digest, 'current_status_summary_path': project_relative(project_root, status_summary_path), 'current_status_summary_exists': status_summary_path.exists(), 'current_status_summary_hash': status_summary_digest, 'router_daemon_status_path': project_relative(project_root, daemon_status_path), 'router_daemon_status_exists': daemon_status_path.exists(), 'router_daemon_status_hash': daemon_status_digest, 'user_visible_status_source': {'route_sign_source': 'canonical_route_display', 'status_summary_source': 'current_status_summary', 'daemon_status_source': 'router_daemon_status', 'controller_must_show_status_from_current_status_summary': True, 'controller_must_not_infer_status_from_chat_history': True, 'sealed_body_fields_excluded': True}, 'projection_hash': digest, 'native_plan_projection': projection, 'host_action': 'replace_visible_plan', 'controller_may_invent_route_items': False, 'route_sign_display_required': route_sign_available, 'route_sign_display_degraded_reason': display_degraded_reason, 'route_sign_markdown_path': route_sign.get('markdown_preview_path'), 'route_sign_mermaid_path': route_sign.get('mermaid_path'), 'route_sign_display_packet_path': route_sign.get('display_packet_path'), 'route_sign_mermaid_sha256': route_sign.get('mermaid_sha256'), 'route_sign_source_kind': route_sign.get('route_source_kind'), 'route_sign_node_count': route_sign.get('route_node_count'), 'route_sign_checklist_item_count': route_sign.get('route_checklist_item_count'), 'route_sign_layout': route_sign.get('route_sign_layout'), 'route_sign_source_route_path': route_sign.get('source_route_path'), 'route_sign_source_frontier_path': route_sign.get('source_frontier_path'), 'route_display_refresh_path': route_display_refresh['path'], 'route_display_refresh': route_display_refresh, **dialog_fields}

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

def _event_markers(router: ModuleType, run_state: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    markers: list[dict[str, Any]] = []
    for event in run_state.get('events') or []:
        if not isinstance(event, dict):
            continue
        event_name = str(event.get('event') or '')
        if event_name not in names:
            continue
        markers.append({'event': event_name, 'summary': event.get('summary'), 'recorded_at': event.get('recorded_at')})
    return markers

def _route_node_history(router: ModuleType, project_root: Path, run_root: Path, route_id: str, route: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    nodes: list[dict[str, Any]] = []
    for node in router._route_nodes(route):
        node_id = str(node['node_id'])
        node_root = run_root / 'routes' / route_id / 'nodes' / node_id
        source_paths = {'node_acceptance_plan': router._optional_source_path(project_root, node_root / 'node_acceptance_plan.json'), 'node_acceptance_plan_review': router._optional_source_path(project_root, node_root / 'reviews' / 'node_acceptance_plan_review.json'), 'parent_backward_replay': router._optional_source_path(project_root, node_root / 'parent_backward_replay.json'), 'pm_parent_segment_decision': router._optional_source_path(project_root, node_root / 'pm_parent_segment_decision.json')}
        nodes.append({'node_id': node_id, 'title': node.get('title'), 'status': node.get('status') or 'unknown', 'created_by_mutation': bool(node.get('created_by_mutation')), 'superseded_by': node.get('superseded_by'), 'source_paths': {key: value for key, value in source_paths.items() if value}})
    return nodes

def _refresh_route_memory(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger: str) -> None:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    route_id = str(frontier.get('active_route_id') or '')
    route_version = int(frontier.get('route_version') or 0)
    route_path = run_root / 'routes' / route_id / 'flow.json' if route_id else run_root / 'routes' / 'route-001' / 'flow.json'
    route = read_json_if_exists(route_path)
    mutations_path = run_root / 'routes' / route_id / 'mutations.json' if route_id else run_root / 'routes' / 'route-001' / 'mutations.json'
    mutations = read_json_if_exists(mutations_path)
    stale_ledger_path = run_root / 'evidence' / 'stale_evidence_ledger.json'
    stale_ledger = read_json_if_exists(stale_ledger_path)
    evidence_ledger_path = run_root / 'evidence' / 'evidence_ledger.json'
    evidence_ledger = read_json_if_exists(evidence_ledger_path)
    generated_ledger_path = run_root / 'generated_resource_ledger.json'
    generated_ledger = read_json_if_exists(generated_ledger_path)
    completed_nodes = [str(item) for item in frontier.get('completed_nodes') or []]
    mutation_items = [item for item in mutations.get('items') or [] if isinstance(item, dict)]
    superseded_nodes = sorted({str(node_id) for item in mutation_items for node_id in router._route_mutation_superseded_nodes(item)})
    stale_evidence = sorted({str(item.get('evidence_id')) for item in stale_ledger.get('items') or [] if isinstance(item, dict) and item.get('evidence_id')} | {str(evidence_id) for item in mutation_items for evidence_id in item.get('stale_evidence') or []})
    effective_nodes = [str(node.get('node_id')) for node in router._effective_route_nodes(route, mutations) if node.get('node_id')]
    route_nodes = router._route_node_history(project_root, run_root, route_id or 'route-001', route)
    reviewer_blocks = router._event_markers(run_state, {'current_node_reviewer_blocks_result', 'reviewer_blocks_current_node_dispatch', 'reviewer_blocks_node_acceptance_plan', 'reviewer_reports_material_insufficient', 'reviewer_blocks_material_scan_dispatch'})
    reviewer_passes = router._event_markers(run_state, {'reviewer_reports_material_sufficient', 'reviewer_passes_research_direct_source_check', 'reviewer_passes_node_acceptance_plan', 'current_node_reviewer_passes_result', 'reviewer_passes_parent_backward_replay', 'reviewer_passes_evidence_quality_package', 'reviewer_final_backward_replay_passed'})
    research_or_experiments = []
    for label, path in (('research_package', run_root / 'research' / 'research_package.json'), ('worker_research_report', run_root / 'research' / 'worker_research_report.json'), ('research_reviewer_report', run_root / 'research' / 'research_reviewer_report.json'), ('product_architecture_modelability', run_root / 'flowguard' / 'product_architecture_modelability.json'), ('root_contract_modelability', run_root / 'flowguard' / 'root_contract_modelability.json'), ('child_skill_conformance_model', run_root / 'flowguard' / 'child_skill_conformance_model.json'), ('child_skill_product_fit', run_root / 'flowguard' / 'child_skill_product_fit.json')):
        source_path = router._optional_source_path(project_root, path)
        if source_path:
            research_or_experiments.append({'kind': label, 'source_path': source_path})
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root)), 'execution_frontier': router._optional_source_path(project_root, run_root / 'execution_frontier.json'), 'active_route': router._optional_source_path(project_root, route_path), 'route_mutations': router._optional_source_path(project_root, mutations_path), 'packet_ledger': router._optional_source_path(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': router._optional_source_path(project_root, run_root / 'prompt_delivery_ledger.json'), 'evidence_ledger': router._optional_source_path(project_root, evidence_ledger_path), 'stale_evidence_ledger': router._optional_source_path(project_root, stale_ledger_path), 'generated_resource_ledger': router._optional_source_path(project_root, generated_ledger_path)}
    history_index = {'schema_version': ROUTE_HISTORY_INDEX_SCHEMA, 'run_id': run_state['run_id'], 'generated_by': 'controller', 'controller_decision_authority': False, 'sealed_packet_or_result_bodies_read': False, 'trigger': trigger, 'refreshed_at': utc_now(), 'frontier': {'status': frontier.get('status'), 'active_route_id': frontier.get('active_route_id'), 'active_node_id': frontier.get('active_node_id'), 'route_version': route_version, 'completed_nodes': completed_nodes, 'latest_mutation_path': frontier.get('latest_mutation_path')}, 'route': {'effective_nodes': effective_nodes, 'node_history': route_nodes, 'route_node_count': len(route_nodes)}, 'mutations': {'count': len(mutation_items), 'superseded_nodes': superseded_nodes, 'items': [{'route_version': item.get('route_version'), 'active_node_id': item.get('active_node_id'), 'reason': item.get('reason'), 'superseded_nodes': router._route_mutation_superseded_nodes(item), 'affected_sibling_nodes': item.get('affected_sibling_nodes') or [], 'replay_scope_node_id': item.get('replay_scope_node_id'), 'stale_evidence': item.get('stale_evidence') or [], 'recorded_at': item.get('recorded_at')} for item in mutation_items]}, 'evidence': {'stale_evidence': stale_evidence, 'unresolved_count': int(evidence_ledger.get('unresolved_count', 0) or 0), 'stale_count': int(evidence_ledger.get('stale_count', 0) or 0), 'generated_pending_resource_count': int(generated_ledger.get('pending_resource_count', 0) or 0), 'generated_unresolved_resource_count': int(generated_ledger.get('unresolved_resource_count', 0) or 0)}, 'review_markers': {'blocks': reviewer_blocks, 'passes': reviewer_passes}, 'research_or_experiments': research_or_experiments, 'source_paths': {key: value for key, value in source_paths.items() if value}}
    write_json(router._route_history_index_path(run_root), history_index)
    pm_context = {'schema_version': PM_PRIOR_PATH_CONTEXT_SCHEMA, 'run_id': run_state['run_id'], 'generated_by': 'controller', 'controller_decision_authority': False, 'sealed_packet_or_result_bodies_read': False, 'trigger': trigger, 'refreshed_at': history_index['refreshed_at'], 'route_position': history_index['frontier'], 'completed_nodes_considered': completed_nodes, 'effective_nodes_considered': effective_nodes, 'superseded_nodes_considered': superseded_nodes, 'stale_evidence_considered': stale_evidence, 'review_blocks_considered': reviewer_blocks, 'review_passes_considered': reviewer_passes, 'research_or_experiment_outputs_considered': research_or_experiments, 'future_route_decision_requirements': ['Before route draft, route mutation, repair-node creation, node acceptance planning, resume continuation, final ledger, or closure, PM must read this current context and cite its path.', 'PM must explain how completed, superseded, stale, blocked, and experimental history changes the next route or node decision.', 'Controller-provided history is an index of reviewed files and state only; PM must not treat it as evidence beyond the cited source paths.'], 'source_paths': {**{key: value for key, value in source_paths.items() if value}, 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}}
    write_json(router._pm_prior_path_context_path(run_root), pm_context)
    run_state['flags']['route_history_index_refreshed'] = True
    run_state['flags']['pm_prior_path_context_refreshed'] = True

def _require_pm_prior_path_context(router: ModuleType, project_root: Path, run_root: Path, payload: dict[str, Any], *, purpose: str) -> dict[str, Any]:
    _bind_router(router)
    context_path = router._pm_prior_path_context_path(run_root)
    history_path = router._route_history_index_path(run_root)
    if not context_path.exists() or not history_path.exists():
        raise RouterError(f'{purpose} requires refreshed route memory before PM decision')
    review = payload.get('prior_path_context_review')
    if not isinstance(review, dict):
        raise RouterError(f'{purpose} requires prior_path_context_review')
    if review.get('reviewed') is not True:
        raise RouterError(f'{purpose} requires prior_path_context_review.reviewed=true')
    if review.get('controller_summary_used_as_evidence') is True:
        raise RouterError(f'{purpose} cannot treat Controller route history as acceptance evidence')
    expected_context = project_relative(project_root, context_path)
    expected_history = project_relative(project_root, history_path)
    source_paths = [str(path) for path in review.get('source_paths') or []]
    if expected_context not in source_paths:
        raise RouterError(f'{purpose} must cite current pm_prior_path_context.json')
    if expected_history not in source_paths:
        raise RouterError(f'{purpose} must cite current route_history_index.json')
    missing = [field for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS if field not in review and field not in {'reviewed', 'source_paths'}]
    if missing:
        raise RouterError(f"{purpose} prior_path_context_review missing fields: {', '.join(missing)}")
    return {'reviewed': True, 'source_paths': [expected_context, expected_history], 'completed_nodes_considered': review.get('completed_nodes_considered') or [], 'superseded_nodes_considered': review.get('superseded_nodes_considered') or [], 'stale_evidence_considered': review.get('stale_evidence_considered') or [], 'prior_blocks_or_experiments_considered': review.get('prior_blocks_or_experiments_considered') or [], 'impact_on_decision': review.get('impact_on_decision'), 'controller_summary_used_as_evidence': False}

def _pm_context_action_extra(router: ModuleType, project_root: Path, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if entry.get('to_role') != 'project_manager':
        return {}
    context_path = router._pm_prior_path_context_path(run_root)
    history_path = router._route_history_index_path(run_root)
    extra = {'pm_context_paths': {'pm_prior_path_context': project_relative(project_root, context_path), 'route_history_index': project_relative(project_root, history_path)}, 'pm_prior_path_context_required_for_decision': entry.get('card_id') in PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS, 'controller_history_is_evidence': False}
    return extra

def _card_required_source_paths(router: ModuleType, project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    _bind_router(router)
    source_paths: dict[str, str] = {}
    for label, relative_path in CARD_REQUIRED_SOURCE_PATHS.get(card_id, {}).items():
        path = run_root / relative_path
        if path.exists():
            source_paths[label] = project_relative(project_root, path)
    if card_id in {'process_officer.route_process_check', 'product_officer.route_product_check', 'reviewer.route_challenge'}:
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
    return {'schema_version': LIVE_CARD_CONTEXT_SCHEMA, 'run_id': str(run_state.get('run_id') or run_root.name), 'card_id': card_id, 'to_role': str(entry.get('to_role') or card.get('audience') or ''), 'current_task': {'user_request_path': user_request_path or None, 'startup_intake_record_path': startup_intake_record_path or None, 'user_intake_packet_id': 'user_intake' if (run_root / 'mailbox' / 'outbox' / 'user_intake.json').exists() else None, 'task_authority': 'startup_intake_ui_record_and_user_intake' if startup_intake_record_path else 'router_recorded_user_request_and_user_intake', 'controller_summary_is_task_authority': False, 'reviewer_live_review_source': 'startup_intake_record' if startup_intake_record_path else None}, 'current_stage': {'current_phase': current_phase, 'card_phase': card_phase, 'frontier_status': frontier.get('status'), 'current_node_id': frontier.get('active_node_id'), 'current_route_id': frontier.get('active_route_id'), 'route_version': frontier.get('route_version')}, 'source_paths': source_paths, 'role_prompt_rule': 'Treat this router delivery envelope as the live context for the current run, current task, current card, current phase, and current node/frontier. If required context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.'}

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

def _write_route_draft(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose='route draft')
    contract_path = run_root / 'root_acceptance_contract.json'
    if not contract_path.exists():
        raise RouterError('route draft requires frozen root contract')
    contract = read_json(contract_path)
    if contract.get('status') != 'frozen':
        raise RouterError('route draft requires root contract status=frozen')
    sync_path = run_root / 'capabilities' / 'capability_sync.json'
    child_manifest_path = run_root / 'child_skill_gate_manifest.json'
    if not sync_path.exists():
        raise RouterError('route draft requires capability evidence sync')
    if not child_manifest_path.exists() or read_json(child_manifest_path).get('status') != 'approved':
        raise RouterError('route draft requires approved child-skill gate manifest')
    product_model_path = router._require_product_behavior_model_report(project_root, run_root)
    route_id = str(payload.get('route_id') or 'route-001')
    route_root = run_root / 'routes' / route_id
    draft = payload.get('route') if isinstance(payload.get('route'), dict) else {}
    route_payload = dict(payload)
    original_schema_version = route_payload.get('schema_version')
    if original_schema_version and original_schema_version != 'flowpilot.route_draft.v1':
        route_payload['pm_authored_payload_schema_version'] = original_schema_version
    route_payload['schema_version'] = 'flowpilot.route_draft.v1'
    route_payload['run_id'] = run_state['run_id']
    route_payload['route_id'] = route_id
    route_payload['route_version'] = int(payload.get('route_version') or draft.get('route_version') or 1)
    route_payload['source_root_contract'] = project_relative(project_root, contract_path)
    route_payload['source_product_behavior_model'] = project_relative(project_root, product_model_path)
    route_payload['source_product_behavior_model_hash'] = hashlib.sha256(product_model_path.read_bytes()).hexdigest()
    route_payload['prior_path_context_review'] = prior_review
    root_requirement_ids = router._root_requirement_ids(contract)
    route_payload['requirement_traceability_policy'] = {'schema_version': 'flowpilot.route_requirement_traceability.v1', 'source_root_contract': project_relative(project_root, contract_path), 'source_product_architecture': project_relative(project_root, run_root / 'product_function_architecture.json'), 'full_protocol_required_when_flowpilot_invoked': True, 'light_or_simple_profiles_forbidden': True, 'every_node_requires_requirement_or_risk_rationale': True, 'external_spec_material_advisory_until_pm_imported': True}
    route_payload['nodes'] = router._route_nodes_with_requirement_trace(draft.get('nodes') or payload.get('nodes') or [], root_requirement_ids)
    route_payload['written_by_role'] = 'project_manager'
    route_payload['written_at'] = str(payload.get('written_at') or utc_now())
    route_payload['router_preservation'] = {'schema_version': 'flowpilot.router_artifact_preservation.v1', 'canonical_source': 'pm_role_output_body', 'official_artifact_path': project_relative(project_root, route_root / 'flow.draft.json'), 'role_authored_fields_preserved': True, 'whitelist_rebuild_used': False, 'recorded_at': utc_now()}
    route_payload.update(_role_output_envelope_record(payload))
    write_json(route_root / 'flow.draft.json', route_payload)
    run_state['draft_route_visibility'] = {'route_id': route_id, 'route_version': int(route_payload['route_version']), 'draft_path': project_relative(project_root, route_root / 'flow.draft.json'), 'user_visible': False, 'reason': 'draft_routes_are_internal_until_pm_activates_reviewed_flow_json', 'recorded_at': utc_now()}

def _reset_route_review_after_route_draft_repair(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    for flag in ('process_officer_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'process_officer_route_check_passed', 'process_officer_route_repair_required', 'process_officer_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'product_officer_route_check_card_delivered', 'product_officer_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False

def _reset_route_hard_gate_approvals_for_recheck(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    for flag in ('pm_route_skeleton_card_delivered', 'route_draft_written_by_pm', 'process_officer_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'process_officer_route_check_passed', 'process_officer_route_repair_required', 'process_officer_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'product_officer_route_check_card_delivered', 'product_officer_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False

def _product_behavior_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'product_behavior_model.json'

def _product_behavior_model_compatibility_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'product_architecture_modelability.json'

def _require_product_behavior_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._product_behavior_model_report_path(run_root)
    if not path.exists():
        compatibility_path = router._product_behavior_model_compatibility_report_path(run_root)
        if compatibility_path.exists():
            path = compatibility_path
    if not path.exists():
        raise RouterError('route draft requires Product Officer product behavior model report')
    report = read_json(path)
    if report.get('passed') is not True:
        raise RouterError('route draft requires passed Product Officer product behavior model report')
    return path

def _route_process_check_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'route_process_check.json'

def _process_route_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'process_route_model.json'

def _require_process_route_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._process_route_model_report_path(run_root)
    if not path.exists():
        compatibility_path = router._route_process_check_path(run_root)
        if compatibility_path.exists():
            path = compatibility_path
    if not path.exists():
        raise RouterError('route activation requires process route model report')
    report = read_json(path)
    if report.get('passed') is not True or report.get('process_viability_verdict') != 'pass':
        raise RouterError('route activation requires Process Officer process route model pass')
    return path

def _route_product_check_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'route_product_check.json'

def _require_route_process_pass(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    return router._require_process_route_model_report(project_root, run_root)

def _supersede_active_current_node_packet_for_route_mutation(router: ModuleType, project_root: Path, run_root: Path, *, frontier: dict[str, Any], mutation_record: dict[str, Any]) -> None:
    _bind_router(router)
    ledger_path = run_root / 'packet_ledger.json'
    ledger = read_json_if_exists(ledger_path)
    packets = ledger.get('packets') if isinstance(ledger, dict) else []
    if not isinstance(packets, list):
        return
    active_packet_id = str(ledger.get('active_packet_id') or '').strip()
    active_node_id = str(frontier.get('active_node_id') or '').strip()
    if not active_packet_id and (not active_node_id):
        return
    superseded_at = utc_now()
    disposition = {'schema_version': 'flowpilot.route_mutation_packet_disposition.v1', 'status': 'superseded_by_route_mutation', 'route_id': frontier.get('active_route_id'), 'from_route_version': frontier.get('route_version'), 'candidate_route_version': mutation_record.get('route_version'), 'candidate_node_id': mutation_record.get('active_node_id'), 'topology_strategy': mutation_record.get('topology_strategy'), 'reason': mutation_record.get('reason') or 'route mutation replaces current node obligation', 'recorded_at': superseded_at}
    changed = False
    for record in packets:
        if not isinstance(record, dict):
            continue
        packet_id = str(record.get('packet_id') or '').strip()
        node_id = str(record.get('node_id') or record.get('current_node_id') or '').strip()
        status = str(record.get('active_packet_status') or record.get('status') or '').strip()
        if not router._packet_status_allows_current_work(status):
            continue
        if packet_id != active_packet_id and node_id != active_node_id:
            continue
        record['status'] = 'superseded'
        record['active_packet_status'] = 'superseded'
        record['active_packet_holder'] = 'controller'
        record['router_reconciliation_status'] = 'superseded_by_route_mutation'
        record['route_mutation_disposition'] = disposition
        changed = True
    if not changed:
        return
    ledger['active_packet_status'] = 'superseded'
    ledger['active_packet_holder'] = 'controller'
    ledger['route_mutation_packet_disposition'] = disposition
    ledger['updated_at'] = superseded_at
    write_json(ledger_path, ledger)

def _require_route_product_pass(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._route_product_check_path(run_root)
    if not path.exists():
        raise RouterError('route activation requires route_product_check.json')
    report = read_json(path)
    if report.get('passed') is not True or report.get('route_model_review_verdict') != 'pass':
        raise RouterError('route activation requires passed product-model route review')
    return path

def _current_route_draft_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    route_root = run_root / 'routes'
    candidates = sorted(route_root.glob('*/flow.draft.json')) if route_root.exists() else []
    if not candidates:
        raise RouterError('route check requires a route draft')
    if len(candidates) > 1:
        raise RouterError('route check requires an unambiguous current route draft')
    return candidates[0]

def _latest_event_payload(router: ModuleType, run_state: dict[str, Any], event_name: str) -> dict[str, Any]:
    _bind_router(router)
    for event in reversed(run_state.get('events', [])):
        if isinstance(event, dict) and event.get('event') == event_name:
            payload = event.get('payload')
            return payload if isinstance(payload, dict) else {}
    return {}

def _route_action_policy_registry_path(router: ModuleType, run_root: Path | None=None) -> Path:
    _bind_router(router)
    if run_root is not None:
        candidate = run_root / 'runtime_kit' / 'route_action_policy_registry.json'
        if candidate.exists():
            return candidate
    return runtime_kit_source() / 'route_action_policy_registry.json'

def _load_route_action_policy_registry(router: ModuleType, run_root: Path | None=None) -> dict[str, Any]:
    _bind_router(router)
    return read_json(router._route_action_policy_registry_path(run_root))

def _route_action_policy_rows(router: ModuleType, run_root: Path | None=None) -> list[dict[str, Any]]:
    _bind_router(router)
    registry = router._load_route_action_policy_registry(run_root)
    rows = registry.get('route_actions')
    if not isinstance(rows, list):
        raise RouterError('route action policy registry requires route_actions list')
    return [row for row in rows if isinstance(row, dict)]

def _route_action_policy_issues(router: ModuleType, run_root: Path | None=None) -> list[str]:
    _bind_router(router)
    issues: list[str] = []
    try:
        registry = router._load_route_action_policy_registry(run_root)
    except Exception as exc:
        return [f'route action policy registry cannot be loaded: {exc}']
    if registry.get('schema_version') != ROUTE_ACTION_POLICY_REGISTRY_SCHEMA:
        issues.append('route action policy registry schema_version mismatch')
    if registry.get('authority') != 'router':
        issues.append('route action policy registry authority must be router')
    for field in ROUTE_ACTION_POLICY_REQUIRED_BOOL_FLAGS:
        if registry.get(field) is not True:
            issues.append(f'route action policy registry requires {field}=true')
    raw_rows = registry.get('route_actions')
    if not isinstance(raw_rows, list) or not raw_rows:
        issues.append('route action policy registry requires non-empty route_actions list')
        return issues
    transaction_types = {str(row.get('transaction_type')) for row in _control_transaction_registry_rows(run_root)}
    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            issues.append(f'route_actions[{index}] must be an object')
            continue
        action_id = str(row.get('action_id') or '').strip()
        context = action_id or f'route_actions[{index}]'
        if not action_id:
            issues.append(f'{context}: action_id is required')
        elif action_id in seen:
            issues.append(f'{context}: duplicate action_id')
        seen.add(action_id)
        for field in ('actor_roles', 'router_events', 'requires', 'forbids', 'commit_targets'):
            if not isinstance(row.get(field), list):
                issues.append(f'{context}: {field} must be a list')
        transaction_type = str(row.get('transaction_type') or '').strip()
        if transaction_type not in transaction_types:
            issues.append(f'{context}: transaction_type is not registered: {transaction_type}')
        for event in row.get('router_events', []) if isinstance(row.get('router_events'), list) else []:
            if str(event) not in EXTERNAL_EVENTS:
                issues.append(f'{context}: router_event is not registered: {event}')
        for target in row.get('commit_targets', []) if isinstance(row.get('commit_targets'), list) else []:
            if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                issues.append(f'{context}: unsupported commit_target: {target}')
    return issues

def _validate_route_action_policy_registry(router: ModuleType, run_root: Path | None=None) -> None:
    _bind_router(router)
    issues = router._route_action_policy_issues(run_root)
    if issues:
        raise RouterError('route action policy registry invalid: ' + '; '.join(issues))

def _route_action_policy_by_id(router: ModuleType, run_root: Path | None=None) -> dict[str, dict[str, Any]]:
    _bind_router(router)
    router._validate_route_action_policy_registry(run_root)
    return {str(row['action_id']): row for row in router._route_action_policy_rows(run_root)}

def _active_frontier(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    if not frontier.get('active_route_id') or not frontier.get('active_node_id'):
        raise RouterError('active execution frontier is missing route or node')
    return frontier

def _active_route_path(router: ModuleType, run_root: Path, frontier: dict[str, Any]) -> Path:
    _bind_router(router)
    return run_root / 'routes' / str(frontier['active_route_id']) / 'flow.json'

def _active_route_flow(router: ModuleType, run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    route_path = router._active_route_path(run_root, frontier)
    if not route_path.exists():
        raise RouterError(f'active route flow is missing: {route_path}')
    return read_json(route_path)

def _iter_route_nodes(router: ModuleType, route: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    return router._route_nodes(route)

def _active_node_definition(router: ModuleType, run_root: Path, frontier: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    route = router._active_route_flow(run_root, frontier)
    active_node_id = str(frontier['active_node_id'])
    return router._active_node_definition_from_route(route, active_node_id)

def _active_node_definition_from_route(router: ModuleType, route: dict[str, Any], active_node_id: str) -> dict[str, Any]:
    _bind_router(router)
    for node in router._iter_route_nodes(route):
        if node.get('node_id') == active_node_id or node.get('id') == active_node_id:
            return node
    raise RouterError(f'active route node is missing from route: {active_node_id}')

def _is_route_root_like_node_id(router: ModuleType, node_id: str) -> bool:
    _bind_router(router)
    normalized = str(node_id or '').strip().lower().replace('-', '_')
    return normalized in {'root', 'route_root', 'route'} or normalized.startswith('route_root')

def _route_mutation_review_lane(router: ModuleType, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if flags.get('node_review_blocked'):
        return 'current_node_result_review'
    if flags.get('parent_backward_replay_blocked'):
        return 'parent_backward_replay'
    if flags.get('node_acceptance_plan_review_blocked'):
        return 'node_acceptance_plan_review'
    return 'unknown'

def _validate_route_mutation_phase_boundary(router: ModuleType, run_root: Path, run_state: dict[str, Any], *, route_id: str, current_active_node_id: str) -> None:
    _bind_router(router)
    lane = router._route_mutation_review_lane(run_state)
    if lane != 'node_acceptance_plan_review':
        return
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    completed_nodes = [str(item) for item in frontier.get('completed_nodes') or []]
    if completed_nodes:
        return
    route_path = run_root / 'routes' / route_id / 'flow.json'
    route = read_json_if_exists(route_path)
    active_node = router._active_node_definition_from_route(route, current_active_node_id) if route else {}
    if router._node_kind(active_node) not in {'parent', 'module'} and (not router._is_route_root_like_node_id(current_active_node_id)):
        return
    raise RouterError('planning/root node-entry gaps before executable child work must be resolved by route replanning or ordinary node expansion, not by creating a repair node')

def _node_child_ids(router: ModuleType, node: dict[str, Any]) -> list[str]:
    _bind_router(router)
    child_ids: list[str] = []
    for key in ('child_node_ids', 'children', 'child_nodes'):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            for child in raw_children:
                if isinstance(child, str):
                    child_ids.append(child)
                elif isinstance(child, dict):
                    child_id = child.get('node_id') or child.get('id')
                    if child_id:
                        child_ids.append(str(child_id))
    return child_ids

def _active_node_has_children(router: ModuleType, run_root: Path, frontier: dict[str, Any]) -> bool:
    _bind_router(router)
    return bool(router._node_child_ids(router._active_node_definition(run_root, frontier)))

def _route_node_map(router: ModuleType, route: dict[str, Any]) -> dict[str, dict[str, Any]]:
    _bind_router(router)
    return {str(node.get('node_id') or node.get('id')): node for node in router._iter_route_nodes(route) if node.get('node_id') or node.get('id')}

def _route_descendant_node_ids(router: ModuleType, route: dict[str, Any], node_id: str) -> list[str]:
    _bind_router(router)
    node_by_id = router._route_node_map(route)
    descendants: list[str] = []
    seen: set[str] = set()

    def visit(current_node_id: str) -> None:
        if current_node_id in seen:
            return
        seen.add(current_node_id)
        node = node_by_id.get(current_node_id)
        if not node:
            return
        for child_id in router._node_child_ids(node):
            if child_id not in descendants:
                descendants.append(child_id)
            visit(child_id)
    visit(str(node_id))
    return descendants

def _node_completion_ledger_path_for(router: ModuleType, run_root: Path, route_id: str, node_id: str) -> Path:
    _bind_router(router)
    return run_root / 'routes' / route_id / 'nodes' / node_id / 'node_completion_ledger.json'

def _node_completion_ledger_current(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any], node_id: str) -> dict[str, Any]:
    _bind_router(router)
    route_id = str(frontier.get('active_route_id') or '')
    route_version = int(frontier.get('route_version') or 0)
    ledger_path = router._node_completion_ledger_path_for(run_root, route_id, str(node_id))
    if not ledger_path.exists():
        return {'node_id': str(node_id), 'current': False, 'reason': 'missing_node_completion_ledger', 'ledger_path': project_relative(project_root, ledger_path)}
    ledger = read_json(ledger_path)
    issues: list[str] = []
    if ledger.get('schema_version') != 'flowpilot.node_completion_ledger.v1':
        issues.append('schema_version_mismatch')
    if str(ledger.get('run_id') or '') != str(run_state.get('run_id') or ''):
        issues.append('run_id_mismatch')
    if str(ledger.get('route_id') or '') != route_id:
        issues.append('route_id_mismatch')
    try:
        ledger_route_version = int(ledger.get('route_version') or 0)
    except (TypeError, ValueError):
        ledger_route_version = -1
    if ledger_route_version != route_version:
        issues.append('route_version_mismatch')
    if str(ledger.get('node_id') or '') != str(node_id):
        issues.append('node_id_mismatch')
    if ledger.get('flowpilot_completable_work_closed') is not True:
        issues.append('flowpilot_work_not_closed')
    return {'node_id': str(node_id), 'current': not issues, 'issues': issues, 'ledger_path': project_relative(project_root, ledger_path)}

def _parent_segment_decision_value(router: ModuleType, run_root: Path, frontier: dict[str, Any]) -> str | None:
    _bind_router(router)
    decision_path = _active_node_root(run_root, frontier) / 'pm_parent_segment_decision.json'
    if not decision_path.exists():
        return None
    decision = read_json(decision_path)
    return str(decision.get('decision') or '') or None

def _route_action_for_event(router: ModuleType, event: str) -> str | None:
    _bind_router(router)
    return ROUTE_ACTION_POLICY_EVENT_TO_ACTION.get(str(event))

def _route_action_for_card(router: ModuleType, card_id: str) -> str | None:
    _bind_router(router)
    return ROUTE_ACTION_POLICY_CARD_TO_ACTION.get(str(card_id))

def _legal_next_action_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    policy_by_id = router._route_action_policy_by_id(run_root)
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    active_node_id = str(frontier['active_node_id'])
    active_node = router._active_node_definition_from_route(route, active_node_id)
    child_ids = router._node_child_ids(active_node)
    descendants = router._route_descendant_node_ids(route, active_node_id)
    completed_nodes = {str(item) for item in frontier.get('completed_nodes') or []}
    descendant_ledgers = [router._node_completion_ledger_current(project_root, run_root, run_state, frontier, node_id) for node_id in descendants]
    descendants_in_frontier = all((node_id in completed_nodes for node_id in descendants))
    descendant_ledgers_current = all((bool(item.get('current')) for item in descendant_ledgers))
    child_chain_closed_current = bool(descendants) and descendants_in_frontier and descendant_ledgers_current
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    active_node_kind = router._node_kind(active_node)
    is_parent_scope = active_node_kind in {'parent', 'module'} or bool(child_ids)
    legal_ids: list[str] = []
    reasons: list[str] = []

    def add(action_id: str) -> None:
        if action_id not in policy_by_id:
            reasons.append(f'policy_missing:{action_id}')
            return
        if action_id not in legal_ids:
            legal_ids.append(action_id)
    if is_parent_scope:
        if not child_chain_closed_current:
            reasons.append('child_chain_not_closed_current')
            if child_ids:
                add('enter_next_child')
            add('continue_current_child')
            if flags.get('parent_backward_replay_blocked') or flags.get('node_review_blocked') or flags.get('node_acceptance_plan_review_blocked'):
                add('request_child_repair')
                if flags.get('model_miss_triage_closed'):
                    add('mutate_route')
        elif flags.get('parent_backward_replay_blocked'):
            if flags.get('model_miss_triage_closed'):
                add('mutate_route')
            else:
                add('request_child_repair')
        elif not flags.get('parent_backward_targets_built'):
            add('build_parent_backward_targets')
        elif not flags.get('parent_backward_replay_passed'):
            add('review_parent_backward_replay')
        elif not flags.get('parent_segment_decision_recorded'):
            add('record_parent_segment_decision')
        elif router._parent_segment_decision_value(run_root, frontier) == 'continue' and active_node_id not in completed_nodes:
            add('complete_parent_node')
    elif flags.get('node_review_blocked') or flags.get('node_acceptance_plan_review_blocked'):
        add('request_child_repair')
        if flags.get('model_miss_triage_closed'):
            add('mutate_route')
    elif not flags.get('current_node_result_returned'):
        add('continue_current_child')
    elif not flags.get('current_node_result_relayed_to_pm'):
        add('wait_for_child_result')
    else:
        add('continue_current_child')
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_replay_path = run_root / 'reviews' / 'terminal_backward_replay.json'
    completion_projection_path = _task_completion_projection_path(run_root)
    if flags.get('final_ledger_built_clean') and flags.get('final_backward_replay_passed') and final_ledger_path.exists() and terminal_replay_path.exists() and completion_projection_path.exists():
        projection = read_json_if_exists(completion_projection_path)
        if projection.get('task_status') == 'ready_for_pm_terminal_closure':
            add('terminal_closure')
    parent_actions_illegal = sorted(ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS - set(legal_ids))
    return {'schema_version': 'flowpilot.legal_next_action_context.v1', 'source': 'router', 'route_action_policy_registry': project_relative(project_root, router._route_action_policy_registry_path(run_root)), 'active_route_id': str(frontier['active_route_id']), 'route_version': int(frontier.get('route_version') or 0), 'active_node_id': active_node_id, 'active_node_kind': active_node_kind, 'active_node_has_children': bool(child_ids), 'direct_child_node_ids': child_ids, 'descendant_node_ids': descendants, 'completed_node_ids': sorted(completed_nodes), 'descendant_completion_ledgers': descendant_ledgers, 'child_chain_closed_current': child_chain_closed_current, 'legal_action_ids': legal_ids, 'legal_next_actions': [{'action_id': action_id, 'transaction_type': policy_by_id[action_id].get('transaction_type'), 'commit_targets': policy_by_id[action_id].get('commit_targets') or []} for action_id in legal_ids], 'illegal_parent_closure_action_ids': parent_actions_illegal, 'blocking_reasons': reasons, 'pm_may_choose_only_from_legal_next_actions': True, 'controller_may_advance_or_close_route': False}

def _legal_next_action_ids(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> set[str]:
    _bind_router(router)
    context = router._legal_next_action_context(project_root, run_root, run_state)
    return {str(item) for item in context.get('legal_action_ids', [])}

def _legal_route_action_allowed(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str) -> bool:
    _bind_router(router)
    return str(action_id) in router._legal_next_action_ids(project_root, run_root, run_state)

def _first_incomplete_child_node_id(router: ModuleType, route: dict[str, Any], parent_node: dict[str, Any], completed_nodes: set[str]) -> str | None:
    _bind_router(router)
    node_by_id = router._route_node_map(route)
    for child_id in router._node_child_ids(parent_node):
        child = node_by_id.get(str(child_id))
        if child is None:
            continue
        if str(child_id) not in completed_nodes:
            return str(child_id)
    return None

def _enter_next_child_node(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    router._require_legal_route_action(project_root, run_root, run_state, 'enter_next_child', 'parent/module child entry')
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    parent_node_id = str(frontier['active_node_id'])
    if str(pending_action.get('parent_node_id') or '') != parent_node_id:
        raise RouterError('parent/module child entry parent_node_id no longer matches active frontier')
    parent_node = router._active_node_definition_from_route(route, parent_node_id)
    if router._node_kind(parent_node) not in {'parent', 'module'} and (not router._node_child_ids(parent_node)):
        raise RouterError('parent/module child entry requires active parent or module node')
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    review_path = _active_node_root(run_root, frontier) / 'reviews' / 'node_acceptance_plan_review.json'
    if not plan_path.exists() or not review_path.exists():
        raise RouterError('parent/module child entry requires node acceptance plan and reviewer pass')
    review = read_json(review_path)
    if review.get('passed') is not True:
        raise RouterError('parent/module child entry requires reviewer-passed node acceptance plan')
    completed_nodes = {str(item) for item in frontier.get('completed_nodes') or []}
    next_child_id = router._first_incomplete_child_node_id(route, parent_node, completed_nodes)
    if not next_child_id:
        raise RouterError('parent/module child entry requires an incomplete direct child')
    if str(pending_action.get('next_child_node_id') or '') != next_child_id:
        raise RouterError('parent/module child entry next_child_node_id no longer matches route order')
    next_child = router._active_node_definition_from_route(route, next_child_id)
    _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    frontier.update({'schema_version': 'flowpilot.execution_frontier.v1', 'run_id': run_state['run_id'], 'status': 'current_node_loop', 'active_node_id': next_child_id, 'active_path': router._route_active_path(route, next_child_id), 'active_leaf_node_id': next_child_id if router._node_kind(next_child) in {'leaf', 'repair'} else None, 'parent_entered_from_node_id': parent_node_id, 'updated_at': utc_now(), 'source': 'controller_enters_next_child_node'})
    write_json(run_root / 'execution_frontier.json', frontier)
    router._write_display_plan_from_route(project_root, run_root, run_state, route_id=str(frontier['active_route_id']), route_version=int(frontier.get('route_version') or 0), route_payload=route, active_node_id=next_child_id, source_event='controller_enters_next_child_node')
    return {'parent_node_id': parent_node_id, 'next_child_node_id': next_child_id, 'next_child_node_kind': router._node_kind(next_child), 'controller_may_advance_or_close_route': False}

def _next_parent_child_entry_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if not flags.get('node_acceptance_plan_reviewer_passed'):
        return None
    try:
        legal_context = router._legal_next_action_context(project_root, run_root, run_state)
    except RouterError:
        return None
    if 'enter_next_child' not in {str(item) for item in legal_context.get('legal_action_ids', [])}:
        return None
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    parent_node_id = str(frontier['active_node_id'])
    parent_node = router._active_node_definition_from_route(route, parent_node_id)
    completed_nodes = {str(item) for item in frontier.get('completed_nodes') or []}
    next_child_id = router._first_incomplete_child_node_id(route, parent_node, completed_nodes)
    if not next_child_id:
        return None
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    review_path = _active_node_root(run_root, frontier) / 'reviews' / 'node_acceptance_plan_review.json'
    if not plan_path.exists() or not review_path.exists():
        return None
    return make_action(action_type='enter_next_child_node', actor='controller', label='controller_enters_next_child_node', summary='Router-authorized transition from an accepted parent/module node to its first incomplete direct child without dispatching parent work.', allowed_reads=[project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, router._active_route_path(run_root, frontier)), project_relative(project_root, plan_path), project_relative(project_root, review_path), project_relative(project_root, router._route_action_policy_registry_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, router._route_state_snapshot_path(run_root)), project_relative(project_root, router._current_status_summary_path(run_root))], extra={'postcondition': 'frontier_active_node_entered_child', 'route_action_id': 'enter_next_child', 'parent_node_id': parent_node_id, 'next_child_node_id': next_child_id, 'legal_next_actions': legal_context, 'controller_may_dispatch_parent_work': False, 'controller_may_advance_or_close_route': False})

def _require_legal_route_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str, context: str) -> None:
    _bind_router(router)
    legal_context = router._legal_next_action_context(project_root, run_root, run_state)
    legal_ids = {str(item) for item in legal_context.get('legal_action_ids', [])}
    if str(action_id) in legal_ids:
        return
    reason_items = [str(item) for item in legal_context.get('blocking_reasons', []) if item]
    reasons = ', '.join(reason_items) or 'not in legal_next_actions'
    if str(action_id) == 'mutate_route' and 'child_chain_not_closed_current' in reason_items and ('pm_mutates_route_after_review_block' in str(context)):
        reasons = f'{reasons}; replanning required before route mutation, not repair node'
    raise RouterError(f'{context} requires legal route action {action_id}; current legal actions are {sorted(legal_ids)} ({reasons})')

def _filter_events_by_legal_route_actions(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], events: list[str]) -> list[str]:
    _bind_router(router)
    if not any((router._route_action_for_event(event) for event in events)):
        return events
    legal_ids = router._legal_next_action_ids(project_root, run_root, run_state)
    return [event for event in events if router._route_action_for_event(event) is None or router._route_action_for_event(event) in legal_ids]

def _write_node_completion_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], frontier: dict[str, Any], *, completed_node_id: str, completed_nodes: list[str], next_node_id: str | None, source_event: str='pm_completes_current_node_from_reviewed_result') -> Path:
    _bind_router(router)
    active_node_is_parent = router._active_node_has_children(run_root, frontier)
    packet_envelope: dict[str, Any] = {}
    result_envelope: dict[str, Any] = {}
    packet_envelope_path: Path | None = None
    result_envelope_path: Path | None = None
    if not active_node_is_parent:
        packet_envelope, packet_envelope_path = router._current_node_packet_context(project_root, run_state)
        result_envelope, result_envelope_path = router._current_node_result_context(project_root, run_state)
    audit_path = _active_node_root(run_root, frontier) / 'reviews' / 'current_node_packet_runtime_audit.json'
    ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    source_paths = {'execution_frontier_before_update': project_relative(project_root, run_root / 'execution_frontier.json'), 'node_acceptance_plan': project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier))}
    if packet_envelope_path and result_envelope_path:
        source_paths.update({'current_node_write_grant': project_relative(project_root, _active_node_write_grant_path(run_root, frontier)), 'packet_envelope': project_relative(project_root, packet_envelope_path), 'result_envelope': project_relative(project_root, result_envelope_path), 'current_node_packet_runtime_audit': project_relative(project_root, audit_path)})
    if active_node_is_parent:
        source_paths.update({'parent_backward_replay': project_relative(project_root, _active_node_root(run_root, frontier) / 'parent_backward_replay.json'), 'pm_parent_segment_decision': project_relative(project_root, _active_node_root(run_root, frontier) / 'pm_parent_segment_decision.json')})
    write_json(ledger_path, {'schema_version': 'flowpilot.node_completion_ledger.v1', 'run_id': run_state['run_id'], 'route_id': str(frontier['active_route_id']), 'route_version': int(frontier.get('route_version') or 0), 'node_id': completed_node_id, 'completed_by_role': 'project_manager', 'reviewer_result_passed': True, 'worker_result_packet_id': str(result_envelope.get('packet_id') or ''), 'worker_result_completed_by_role': str(result_envelope.get('completed_by_role') or ''), 'current_node_packet_id': str(packet_envelope.get('packet_id') or ''), 'completion_source_event': source_event, 'parent_backward_replay_completion': active_node_is_parent, 'completed_nodes_after_update': completed_nodes, 'next_node_id': next_node_id, 'flowpilot_completable_work_closed': True, 'human_inspection_notes_belong_in_final_report': True, 'source_paths': source_paths, 'completed_at': utc_now()})
    run_state['flags']['node_completion_ledger_updated'] = True
    return ledger_path

def _mark_current_node_packet_records_completed(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, completed_node_id: str, completion_ledger_path: Path) -> None:
    _bind_router(router)
    try:
        records = router._current_node_packet_records(project_root, run_state)
    except RouterError:
        return
    completed_at = utc_now()
    for record in records:
        packet_id = str(record.get('packet_id') or '').strip()
        if not packet_id:
            continue
        packet_runtime._update_packet_record(project_root, run_root / 'packet_ledger.json', packet_id, {'active_packet_status': 'completed', 'active_packet_holder': 'closed', 'flowpilot_work_completed': True, 'completed_node_id': completed_node_id, 'node_completion_ledger_path': project_relative(project_root, completion_ledger_path), 'completed_by_flow_state': 'pm_completes_current_node_from_reviewed_result', 'completed_at': completed_at, 'holder_history': {'holder': 'closed', 'status': 'completed', 'changed_at': completed_at, 'source': 'node_completion', 'node_id': completed_node_id, 'node_completion_ledger_path': project_relative(project_root, completion_ledger_path)}})

def _mark_frontier_node_completed(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, source_event: str='pm_completes_current_node_from_reviewed_result') -> None:
    _bind_router(router)
    frontier = router._active_frontier(run_root)
    active_node_id = str(payload.get('node_id') or frontier.get('active_node_id') or 'node-001')
    if active_node_id != str(frontier.get('active_node_id')):
        raise RouterError('completed node_id must match active frontier')
    if source_event == 'pm_completes_current_node_from_reviewed_result':
        blockers = _current_node_scope_exit_reconciliation_blockers(project_root, run_root, run_state, frontier)
        if blockers:
            raise RouterError('current-node completion requires local current-scope reconciliation before node exit: ' + '; '.join((str(blocker.get('reason') or blocker.get('kind')) for blocker in blockers)))
    if router._active_node_has_children(run_root, frontier):
        if source_event == 'pm_completes_parent_node_from_backward_replay':
            router._require_legal_route_action(project_root, run_root, run_state, 'complete_parent_node', 'parent node completion commit')
        replay_path = _active_node_root(run_root, frontier) / 'parent_backward_replay.json'
        decision_path = _active_node_root(run_root, frontier) / 'pm_parent_segment_decision.json'
        missing = [project_relative(project_root, path) for path in (replay_path, decision_path) if not path.exists()]
        if missing:
            raise RouterError(f"parent node completion requires backward replay and PM segment decision: {', '.join(missing)}")
        if not run_state['flags'].get('parent_backward_replay_passed'):
            raise RouterError('parent node completion requires reviewer-passed parent backward replay')
        if not run_state['flags'].get('parent_segment_decision_recorded'):
            raise RouterError('parent node completion requires PM parent segment decision')
        decision = read_json(decision_path)
        if decision.get('decision') != 'continue':
            raise RouterError('parent node completion requires PM parent segment decision=continue')
    completed = list(frontier.get('completed_nodes') or [])
    if active_node_id not in completed:
        completed.append(active_node_id)
    route = read_json_if_exists(router._active_route_path(run_root, frontier))
    mutations = read_json_if_exists(run_root / 'routes' / str(frontier['active_route_id']) / 'mutations.json')
    next_node_id = router._next_effective_node_id(route, mutations, completed, active_node_id)
    completion_ledger_path = router._write_node_completion_ledger(project_root, run_root, run_state, frontier, completed_node_id=active_node_id, completed_nodes=completed, next_node_id=next_node_id, source_event=source_event)
    if not router._active_node_has_children(run_root, frontier):
        router._mark_current_node_packet_records_completed(project_root, run_root, run_state, completed_node_id=active_node_id, completion_ledger_path=completion_ledger_path)
    frontier.update({'schema_version': 'flowpilot.execution_frontier.v1', 'run_id': run_state['run_id'], 'status': 'current_node_loop' if next_node_id else 'node_completed_by_pm', 'active_node_id': next_node_id or active_node_id, 'active_path': router._route_active_path(route, next_node_id or active_node_id) if route else frontier.get('active_path', []), 'active_leaf_node_id': next_node_id if next_node_id and route and (router._node_kind(router._active_node_definition_from_route(route, next_node_id)) in {'leaf', 'repair'}) else None, 'completed_nodes': completed, 'latest_node_completion_ledger_path': project_relative(project_root, completion_ledger_path), 'updated_at': utc_now(), 'source': source_event})
    write_json(run_root / 'execution_frontier.json', frontier)
    if next_node_id:
        _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    if route:
        router._write_display_plan_from_route(project_root, run_root, run_state, route_id=str(frontier['active_route_id']), route_version=int(frontier.get('route_version') or 0), route_payload=route, active_node_id=next_node_id, source_event=source_event)


_LOCAL_NAMES = set(globals())
