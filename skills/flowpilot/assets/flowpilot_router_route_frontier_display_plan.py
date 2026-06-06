"""Display-plan projection and route display sync payload helpers."""

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
    '_display_plan_projection',
    '_waiting_for_pm_display_plan',
    '_current_display_plan',
    '_display_plan_sync_payload',
)

_LOCAL_NAMES = set(globals())
