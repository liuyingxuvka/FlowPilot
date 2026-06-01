"""Router skeleton owner helpers for flowpilot_router_startup_support.

These helpers were moved out of ``flowpilot_router.py`` during the final
StructureMesh skeleton cleanup. The module is bound to the router skeleton
before execution so cross-owner transitional lookups stay explicit.
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
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_dispatcher
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_startup_flow
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


OWNER_MODULE = 'flowpilot_router_startup_support'

_STALE_OR_UNKNOWN_HOST_LIVENESS = {"missing", "cancelled", "unknown", "timeout_unknown", "completed"}


def _role_slot_has_current_host_liveness(slot: dict[str, Any]) -> bool:
    agent_id = slot.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id.strip():
        return False
    status = str(slot.get("status") or "")
    host_liveness = str(slot.get("host_liveness_status") or "")
    liveness_decision = str(slot.get("liveness_decision") or "")
    if host_liveness in _STALE_OR_UNKNOWN_HOST_LIVENESS:
        return False
    if status == "live_agent_started":
        return host_liveness in {"", "active"}
    if status == "live_agent_rehydrated":
        return host_liveness == "active" and liveness_decision == "confirmed_existing_agent"
    if status in {"live_agent_recovered", "live_agent_recycled"}:
        return host_liveness == "active" and liveness_decision in ROLE_BINDING_LIVENESS_DECISIONS
    return False


def _ensure_startup_run_state(project_root: Path, bootstrap_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    run_id = str(bootstrap_state.get("run_id") or "")
    run_root_rel = str(bootstrap_state.get("run_root") or "")
    if not run_id or not run_root_rel:
        raise RouterError("startup run state requires run shell first")
    run_root = project_root / run_root_rel
    path = run_state_path(run_root)
    if path.exists():
        run_state = read_json(path)
        run_state.setdefault("flags", {})
        for flag, default in RUNTIME_FLAG_DEFAULTS.items():
            run_state["flags"].setdefault(flag, default)
        for entry in SYSTEM_CARD_SEQUENCE:
            run_state["flags"].setdefault(entry["flag"], False)
        for entry in MAIL_SEQUENCE:
            run_state["flags"].setdefault(entry["flag"], False)
        for event in EXTERNAL_EVENTS.values():
            run_state["flags"].setdefault(event["flag"], False)
        run_state.setdefault("history", [])
        run_state.setdefault("events", [])
        run_state.setdefault("pending_action", None)
        run_state.setdefault("daemon_mode_enabled", False)
        run_state.setdefault("router_daemon_status_path", None)
        run_state.setdefault("controller_action_ledger_path", None)
    else:
        run_state = new_run_state(run_id, run_root_rel, controller_core_loaded=False)
    if not (run_root / "execution_frontier.json").exists():
        write_json(run_root / "execution_frontier.json", _create_empty_execution_frontier(run_id))
    if not _continuation_binding_path(run_root).exists():
        _write_initial_continuation_binding(project_root, run_root, run_state)
    startup_lifecycle = "daemon_active" if run_state.get("daemon_mode_enabled") else "manual_router_loop"
    _ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status=startup_lifecycle)
    save_run_state(run_root, run_state)
    return run_state, run_root

def _active_agent_id_for_role(run_root: Path, role: str) -> str | None:
    role_binding = read_json_if_exists(run_root / "role_binding_ledger.json")
    slots = role_binding.get("role_slots") if isinstance(role_binding.get("role_slots"), list) else []
    for slot in slots:
        if isinstance(slot, dict) and slot.get("role_key") == role:
            agent_id = slot.get("agent_id")
            if isinstance(agent_id, str) and agent_id.strip() and _role_slot_has_current_host_liveness(slot):
                return agent_id.strip()
    return None

def load_manifest_from_run(run_root: Path) -> dict[str, Any]:
    try:
        return load_card_manifest_from_run(run_root)
    except PromptStoreError as exc:
        raise RouterError(str(exc)) from exc

def manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    try:
        return card_manifest_entry(manifest, card_id)
    except PromptStoreError as exc:
        raise RouterError(str(exc)) from exc

def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

def _controller_wait_allowed_external_events(entry: dict[str, Any]) -> list[str]:
    raw_allowed = entry.get("allowed_external_events")
    if not isinstance(raw_allowed, list):
        action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
        raw_allowed = action.get("allowed_external_events")
    if not isinstance(raw_allowed, list):
        return []
    return [str(item) for item in raw_allowed if isinstance(item, str) and item.strip()]

def _external_event_payload_digest(payload: dict[str, Any] | None) -> str:
    try:
        encoded = json.dumps(payload or {}, sort_keys=True, default=str).encode("utf-8")
    except TypeError:
        encoded = repr(payload or {}).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

_LOCAL_NAMES = set(globals())
