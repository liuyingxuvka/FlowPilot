"""Router skeleton owner helpers for flowpilot_router_route_completion_support.

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


OWNER_MODULE = 'flowpilot_router_route_completion_support'

def _reset_flags(run_state: dict[str, Any], names: tuple[str, ...]) -> None:
    for name in names:
        run_state["flags"][name] = False

def _node_identifier(node: dict[str, Any]) -> str:
    return str(node.get("node_id") or node.get("id") or "")

def _raw_route_nodes(route: dict[str, Any]) -> list[Any]:
    nodes = route.get("nodes")
    if isinstance(nodes, dict):
        return list(nodes.values())
    if isinstance(nodes, list):
        return list(nodes)
    return []

def _inline_child_nodes(node: dict[str, Any]) -> list[Any]:
    children: list[Any] = []
    for key in ("children", "child_nodes"):
        raw_children = node.get(key)
        if isinstance(raw_children, list):
            children.extend(raw_children)
    return children

def _active_node_root(run_root: Path, frontier: dict[str, Any]) -> Path:
    return run_root / "routes" / str(frontier["active_route_id"]) / "nodes" / str(frontier["active_node_id"])

def _active_node_acceptance_plan_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_acceptance_plan.json"

def _active_node_write_grant_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "current_node_write_grant.json"

def _active_node_packet_index_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "current_node_packet_batch.json"

def _active_node_completion_ledger_path(run_root: Path, frontier: dict[str, Any]) -> Path:
    return _active_node_root(run_root, frontier) / "node_completion_ledger.json"

def _active_node_completion_write_missing(
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any] | None,
) -> bool:
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier.get("active_node_id") or "")
    if not active_node_id:
        return False
    requested_node_id = str((payload or {}).get("node_id") or active_node_id)
    if requested_node_id != active_node_id:
        return False
    completed_nodes = {str(item) for item in (frontier.get("completed_nodes") or [])}
    return (
        active_node_id not in completed_nodes
        or not _active_node_completion_ledger_path(run_root, frontier).exists()
        or not run_state["flags"].get("node_completion_ledger_updated")
    )

def _node_completion_event_advanced_to_next_node(run_root: Path, payload: dict[str, Any]) -> bool:
    del payload
    frontier = _active_frontier(run_root)
    return frontier.get("status") == "current_node_loop"

def _task_completion_projection_path(run_root: Path) -> Path:
    return run_root / "completion" / "task_completion_projection.json"

def _resume_decision_path(run_root: Path) -> Path:
    return run_root / "continuation" / "pm_resume_decision.json"

def _resume_waits_for_pm_decision(run_state: dict[str, Any]) -> bool:
    flags = run_state["flags"]
    return (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and bool(flags.get("role_binding_recovery_report_written"))
        and bool(flags.get("pm_resume_decision_card_delivered"))
        and not bool(flags.get("role_recovery_obligation_replay_completed"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )

def _resume_mechanical_replay_completed_without_pm(run_state: dict[str, Any]) -> bool:
    flags = run_state["flags"]
    return (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and bool(flags.get("role_recovery_obligations_scanned"))
        and bool(flags.get("role_recovery_obligation_replay_completed"))
        and not bool(flags.get("role_recovery_pm_escalation_required"))
        and bool(flags.get("pm_resume_recovery_decision_returned"))
    )

_LOCAL_NAMES = set(globals())
