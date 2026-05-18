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
