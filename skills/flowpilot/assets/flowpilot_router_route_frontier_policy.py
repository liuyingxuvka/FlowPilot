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

__all__ = (
    '_latest_event_payload',
    '_route_action_policy_registry_path',
    '_load_route_action_policy_registry',
    '_route_action_policy_rows',
    '_route_action_policy_issues',
    '_validate_route_action_policy_registry',
    '_route_action_policy_by_id',
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
    '_route_action_for_event',
    '_route_action_for_card',
    '_legal_next_action_context',
    '_legal_next_action_ids',
    '_legal_route_action_allowed',
    '_first_incomplete_child_node_id',
    '_enter_next_child_node',
    '_next_parent_child_entry_action',
    '_require_legal_route_action',
    '_filter_events_by_legal_route_actions',
    '_write_node_completion_ledger',
    '_mark_current_node_packet_records_completed',
    '_mark_frontier_node_completed',
)

_LOCAL_NAMES = set(globals())
