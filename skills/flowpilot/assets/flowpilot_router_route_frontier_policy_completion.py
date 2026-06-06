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
