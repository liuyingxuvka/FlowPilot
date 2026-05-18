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


__all__ = (
    '_active_frontier',
    '_active_route_path',
    '_active_route_flow',
    '_iter_route_nodes',
    '_active_node_definition',
    '_active_node_definition_from_route',
    '_is_route_root_like_node_id',
    '_route_mutation_review_lane',
    '_validate_route_mutation_phase_boundary',
    '_node_child_ids',
    '_active_node_has_children',
    '_route_node_map',
    '_route_descendant_node_ids',
    '_node_completion_ledger_path_for',
    '_node_completion_ledger_current',
    '_parent_segment_decision_value',
)

_LOCAL_NAMES = set(globals())
