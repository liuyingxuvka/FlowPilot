"""Internal router owner helpers extracted from flowpilot_router.

The public router names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so private helper lookups remain
stable while the implementation body lives outside the facade.
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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER
OWNER_MODULE = "flowpilot_router_expected_waits"
def _event_is_router_internal_postcondition(event: str, meta: dict[str, Any] | None = None) -> bool:
    event_meta = meta if isinstance(meta, dict) else EXTERNAL_EVENTS.get(event, {})
    return bool(event_meta.get("router_internal_postcondition"))

def _event_wait_role(event: str, meta: dict[str, str]) -> str:
    del meta
    if event.startswith("pm_"):
        return "project_manager"
    if event.startswith("reviewer_") or event.startswith("current_node_reviewer_"):
        return "human_like_reviewer"
    if event.startswith("flowguard_operator_"):
        return "flowguard_operator"
    if event.startswith("worker_"):
        return "worker"
    if event.startswith("host_"):
        return "host"
    if event.startswith("controller_") or event in {"capability_evidence_synced"}:
        return "controller"
    if event == "research_capability_decision_recorded":
        return "project_manager"
    return "project_manager"
def _active_node_children_status(run_root: Path | None) -> bool | None:
    if run_root is None:
        return None
    try:
        frontier = _active_frontier(run_root)
        return _active_node_has_children(run_root, frontier)
    except (OSError, KeyError, RouterError, json.JSONDecodeError, ValueError, TypeError):
        return None
def _event_applicable_for_active_node(meta: dict[str, Any], active_node_has_children: bool | None) -> bool:
    if active_node_has_children is None:
        return True
    if meta.get("requires_active_node_children") and not active_node_has_children:
        return False
    if meta.get("forbids_active_node_children") and active_node_has_children:
        return False
    return True
def _pending_expected_external_event_groups(
    run_state: dict[str, Any],
    run_root: Path | None = None,
) -> list[list[tuple[str, dict[str, Any]]]]:
    flags = run_state["flags"]
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    ordered_requires: list[str] = []
    active_node_has_children = _active_node_children_status(run_root)
    for event, meta in EXTERNAL_EVENTS.items():
        if _event_is_router_internal_postcondition(event, meta):
            continue
        required_flag = meta.get("requires_flag")
        if not required_flag:
            continue
        if not _event_applicable_for_active_node(meta, active_node_has_children):
            continue
        if required_flag not in grouped:
            grouped[required_flag] = []
            ordered_requires.append(required_flag)
        grouped[required_flag].append((event, meta))

    def group_already_has_terminal_outcome(group: list[tuple[str, dict[str, Any]]]) -> bool:
        recorded_events = [
            event
            for event, meta in group
            if flags.get(meta["flag"]) and _event_is_terminal_gate_outcome(event, meta)
        ]
        if not recorded_events:
            return False
        recorded_blocks = [event for event in recorded_events if event in GATE_OUTCOME_BLOCK_EVENTS]
        if recorded_blocks:
            pass_events = [
                event
                for event, meta in group
                if event in GATE_OUTCOME_PASS_CLEAR_FLAGS and not flags.get(meta["flag"])
            ]
            if pass_events:
                return False
        return True

    pending: list[list[tuple[str, dict[str, Any]]]] = []
    for required_flag in ordered_requires:
        if not flags.get(required_flag):
            continue
        if required_flag == "pm_control_blocker_repair_decision_recorded" and not isinstance(
            run_state.get("active_control_blocker"), dict
        ):
            continue
        group = grouped[required_flag]
        if group_already_has_terminal_outcome(group):
            continue
        pending.append(group)
    return pending
def _pending_role_decision_staleness(run_state: dict[str, Any], pending_action: object) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or not allowed_events:
        return {
            "reason": "await_role_decision_missing_allowed_external_events",
            "action_type": pending_action.get("action_type"),
            "label": pending_action.get("label"),
        }
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    invalid_events: list[dict[str, Any]] = []
    normalized_events: list[str] = []
    for item in allowed_events:
        if not isinstance(item, str):
            invalid_events.append({"issue": "non_string_allowed_external_event", "event": repr(item)})
            continue
        normalized_events.append(item)
        meta = EXTERNAL_EVENTS.get(item)
        if not isinstance(meta, dict):
            invalid_events.append({"issue": "unknown_external_event", "event": item})
            continue
        if _event_is_router_internal_postcondition(item, meta):
            invalid_events.append(
                {
                    "issue": "router_internal_postcondition_not_role_wait",
                    "event": item,
                    "flag": meta.get("flag"),
                    "requires_flag": meta.get("requires_flag"),
                }
            )
            continue
        required_flag = meta.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            invalid_events.append(
                {
                    "issue": "requires_flag_false",
                    "event": item,
                    "requires_flag": required_flag,
                    "current_value": flags.get(required_flag),
                }
            )
    if not invalid_events:
        return None
    return {
        "reason": "await_role_decision_allowed_event_not_currently_receivable",
        "action_type": pending_action.get("action_type"),
        "label": pending_action.get("label"),
        "allowed_external_events": normalized_events,
        "invalid_allowed_external_events": invalid_events,
    }
def _run_state_has_event(run_state: dict[str, Any], event: str) -> bool:
    return any(
        isinstance(item, dict) and item.get("event") == event
        for item in (run_state.get("events") or [])
    )
__all__ = (
    "_event_is_router_internal_postcondition",
    "_event_wait_role",
    "_active_node_children_status",
    "_event_applicable_for_active_node",
    "_pending_expected_external_event_groups",
    "_pending_role_decision_staleness",
    "_run_state_has_event",
)
_LOCAL_NAMES = set(globals())
