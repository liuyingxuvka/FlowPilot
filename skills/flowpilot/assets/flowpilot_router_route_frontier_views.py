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

__all__ = (
    '_flatten_route_nodes',
    '_route_nodes',
    '_route_node_depth',
    '_route_display_depth',
    '_is_route_root_node',
    '_display_route_nodes',
    '_route_active_path',
    '_route_hidden_leaf_progress',
    '_is_leaf_readiness_passed',
    '_node_kind',
    '_route_mutation_superseded_nodes',
    '_effective_route_nodes',
    '_effective_child_ids',
    '_ready_parent_scope_after_child_completion',
    '_next_effective_node_id',
    '_route_memory_root',
    '_route_history_index_path',
    '_pm_prior_path_context_path',
    '_route_memory_ready',
    '_display_plan_path',
    '_route_state_snapshot_path',
    '_route_display_refresh_path',
    '_optional_source_path',
    '_plan_item_status',
    '_frontier_completed_node_ids',
    '_route_item_status',
    '_display_plan_projection',
    '_waiting_for_pm_display_plan',
    '_current_display_plan',
    '_display_plan_sync_payload',
)

_LOCAL_NAMES = set(globals())
