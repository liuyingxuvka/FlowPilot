"""Route node flattening, display filtering, and next-node selection helpers."""

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
)

_LOCAL_NAMES = set(globals())
