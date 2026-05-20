"""startup bootloader bootstrap/run-state synchronization helpers for ``flowpilot_router_startup_bootloader``.

This child module is imported by the compatibility facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_bootloader'

def _ensure_pending(router: ModuleType, state: dict[str, Any], action_type: str) -> dict[str, Any]:
    _bind_router(router)
    pending = state.get('pending_action')
    if not isinstance(pending, dict):
        raise RouterError("no pending router action; run 'next' before applying an action")
    if pending.get('action_type') != action_type:
        raise RouterError(f"pending action is {pending.get('action_type')!r}, not {action_type!r}")
    return pending

def _set_boot_flag(router: ModuleType, project_root: Path, state: dict[str, Any], flag: str, label: str, details: dict[str, Any] | None=None) -> None:
    _bind_router(router)
    if flag == 'router_loaded':
        state['router_loaded'] = True
        state['status'] = 'running'
    else:
        state['flags'][flag] = True
        state['bootloader_actions'] = int(state.get('bootloader_actions', 0)) + 1
    state['pending_action'] = None
    append_history(state, label, details)
    router.save_bootstrap_state(project_root, state)

def _startup_run_state_if_ready(router: ModuleType, project_root: Path, bootstrap_state: dict[str, Any]) -> tuple[dict[str, Any], Path] | tuple[None, None]:
    _bind_router(router)
    run_root_rel = str(bootstrap_state.get('run_root') or '')
    if not run_root_rel:
        return (None, None)
    run_root = project_root / run_root_rel
    run_state = read_json_if_exists(router.run_state_path(run_root))
    if run_state.get('schema_version') != RUN_STATE_SCHEMA:
        return (None, run_root)
    return (run_state, run_root)

def _sync_startup_bootstrap_flags_to_run_state(router: ModuleType, bootstrap_state: dict[str, Any], run_state: dict[str, Any]) -> None:
    _bind_router(router)
    bootstrap_flags = bootstrap_state.get('flags') if isinstance(bootstrap_state.get('flags'), dict) else {}
    run_flags = run_state.setdefault('flags', {})
    for flag in ('startup_state_written_awaiting_answers', 'dialog_stopped_for_answers', 'startup_answers_recorded', 'banner_emitted', 'flowguard_capability_snapshot_written', 'roles_started', 'role_core_prompts_injected', 'continuation_binding_recorded'):
        if bootstrap_flags.get(flag):
            run_flags[flag] = True

def _fold_stable_startup_role_flags_from_bootstrap(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    bootstrap_path = run_root / 'bootstrap' / 'startup_state.json'
    if not bootstrap_path.exists():
        return {'changed': False, 'exists': False}
    _raise_if_runtime_write_active(bootstrap_path)
    bootstrap = read_daemon_critical_json_if_exists(bootstrap_path)
    bootstrap_flags = bootstrap.get('flags') if isinstance(bootstrap.get('flags'), dict) else {}
    roles_started = bool(bootstrap_flags.get('roles_started'))
    core_prompts_injected = bool(bootstrap_flags.get('role_core_prompts_injected'))
    if roles_started != core_prompts_injected:
        return {'changed': False, 'exists': True, 'waiting_for_settlement': True, 'roles_started': roles_started, 'role_core_prompts_injected': core_prompts_injected}
    if not roles_started:
        return {'changed': False, 'exists': True}
    flags = run_state.setdefault('flags', {})
    missing = [flag for flag in ('roles_started', 'role_core_prompts_injected') if not flags.get(flag)]
    if not missing:
        return {'changed': False, 'exists': True, 'already_folded': True}
    flags['roles_started'] = True
    flags['role_core_prompts_injected'] = True
    append_history(run_state, 'router_folded_startup_role_flags_from_bootstrap', {'source': 'daemon_settlement_barrier', 'bootstrap_state_path': project_relative(project_root, bootstrap_path), 'folded_flags': ['roles_started', 'role_core_prompts_injected']})
    return {'changed': True, 'exists': True, 'folded_flags': ['roles_started', 'role_core_prompts_injected']}

__all__ = (
    '_ensure_pending',
    '_set_boot_flag',
    '_startup_run_state_if_ready',
    '_sync_startup_bootstrap_flags_to_run_state',
    '_fold_stable_startup_role_flags_from_bootstrap',
)

_LOCAL_NAMES = set(globals())
