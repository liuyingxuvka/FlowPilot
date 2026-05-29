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


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _active_ui_target_id(run_id: str) -> str:
    return f"run:{run_id}"


def _active_ui_task_entry(
    router: ModuleType,
    project_root: Path,
    *,
    run_id: str,
    run_root: str,
    status: str,
    focus_selected: bool,
    stale_residue: bool = False,
    stale_reason: str | None = None,
) -> dict[str, Any]:
    target_id = _active_ui_target_id(run_id)
    entry: dict[str, Any] = {
        "run_id": run_id,
        "flow_block_id": run_id,
        "run_root": run_root,
        "status": status or "running",
        "target_id": target_id,
        "target_scope": "single",
        "operation_target_allowed": not stale_residue,
        "display_plan_path": (
            project_relative(project_root, project_root / run_root / "display_plan.json")
            if run_root
            else None
        ),
        "route_state_snapshot_path": (
            project_relative(project_root, project_root / run_root / "route_state_snapshot.json")
            if run_root
            else None
        ),
        "focus_selected": focus_selected,
        "background_active": (not focus_selected) and (not stale_residue),
        "stale_residue": stale_residue,
        "close_tab_behavior": (
            "return_to_dialog_route_display" if focus_selected else "keep_background_run_available"
        ),
    }
    if stale_reason:
        entry["stale_reason"] = stale_reason
    return entry


def _active_ui_operation_targets(active_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    selectable = [task for task in active_tasks if task.get("operation_target_allowed")]
    focus = next((task for task in selectable if task.get("focus_selected")), None)
    return {
        "target_scope_required": True,
        "current_focus": focus.get("target_id") if isinstance(focus, dict) else None,
        "single_targets": [
            {
                "target_id": task.get("target_id"),
                "run_id": task.get("run_id"),
                "flow_block_id": task.get("flow_block_id"),
                "target_scope": "single",
            }
            for task in selectable
        ],
        "all_active": {
            "target_id": "all_active",
            "target_scope": "all_active",
            "run_ids": [task.get("run_id") for task in selectable],
            "flow_block_ids": [task.get("flow_block_id") for task in selectable],
        },
    }

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
    stale_residue_tasks: list[dict[str, Any]] = []
    seen_run_ids: set[str] = set()
    for item in index.get('runs', []):
        if not isinstance(item, dict):
            continue
        item_run_id = str(item.get('run_id') or '')
        item_run_root = str(item.get('run_root') or '')
        item_status = str(item.get('status') or '')
        if not item_run_id:
            continue
        if item_status in hidden_statuses:
            stale_residue_tasks.append(
                _active_ui_task_entry(
                    router,
                    project_root,
                    run_id=item_run_id,
                    run_root=item_run_root,
                    status=item_status,
                    focus_selected=False,
                    stale_residue=True,
                    stale_reason=f"index_status_{item_status}",
                )
            )
            continue
        seen_run_ids.add(item_run_id)
        focus_selected = item_run_id == current_run_id
        active_tasks.append(
            _active_ui_task_entry(
                router,
                project_root,
                run_id=item_run_id,
                run_root=item_run_root,
                status=item_status or "running",
                focus_selected=focus_selected,
            )
        )
    if current_pointer_matches and effective_status not in hidden_statuses and (run_id not in seen_run_ids):
        active_tasks.append(
            _active_ui_task_entry(
                router,
                project_root,
                run_id=run_id,
                run_root=run_root_rel,
                status=effective_status or "running",
                focus_selected=True,
            )
        )
    active_tasks.sort(key=lambda item: (not bool(item.get('focus_selected')), str(item.get('run_id') or '')))
    background_active_tasks = [item for item in active_tasks if item.get('background_active')]
    block_scoped_agents = run_state.get("active_flow_block_agents")
    if not isinstance(block_scoped_agents, list):
        block_scoped_agents = []
    scope_kind = (
        "block_scoped_agents"
        if block_scoped_agents
        else ("parallel_runs" if len(active_tasks) > 1 else ("single_run" if active_tasks else "no_active_tasks"))
    )
    return {
        "schema_version": "flowpilot.active_ui_task_catalog.v1",
        "authority": "explicit_active_set",
        "source_authority": "index_active_runs_with_current_focus",
        "scope_kind": scope_kind,
        "current_pointer_matches_run": current_pointer_matches,
        "current_pointer_is_ui_focus_only": True,
        "global_main_required": False,
        "operation_target_required": True,
        "active_tasks": active_tasks,
        "background_active_tasks": background_active_tasks,
        "block_scoped_agents": block_scoped_agents,
        "operation_targets": _active_ui_operation_targets(active_tasks),
        "hidden_non_current_running_index_entries": stale_residue_tasks,
        "stale_residue_tasks": stale_residue_tasks,
        "completed_abandoned_stale_history_default_visible": False,
    }


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


__all__ = (
    '_active_ui_task_catalog',
    '_route_node_checklist',
    '_active_route_payload',
    '_current_status_summary_path',
    '_run_elapsed_seconds',
)

_LOCAL_NAMES = set(globals())
