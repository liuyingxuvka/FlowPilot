"""Route memory, display-plan path, and route item status helpers."""

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

__all__ = (
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
)

_LOCAL_NAMES = set(globals())
