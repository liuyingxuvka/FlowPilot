"""Router skeleton owner helpers for flowpilot_router_model_gate_state.

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
    if _BOUND_ROUTER is router:
        return
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


OWNER_MODULE = 'flowpilot_router_model_gate_state'

def _sync_model_gate_flags(run_state: dict[str, Any], event: str) -> None:
    flags = run_state.setdefault("flags", {})
    if event in PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS:
        flags["product_behavior_model_submitted"] = True
        flags["product_behavior_model_blocked"] = False
    elif event in PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS:
        flags["product_behavior_model_submitted"] = False
        flags["product_behavior_model_blocked"] = True
    elif event in PROCESS_ROUTE_MODEL_PASS_EVENTS:
        flags["process_route_model_submitted"] = True
        flags["process_route_model_repair_required"] = False
        flags["process_route_model_blocked"] = False
    elif event in PROCESS_ROUTE_MODEL_REPAIR_EVENTS:
        flags["process_route_model_submitted"] = False
        flags["process_route_model_repair_required"] = True
        flags["process_route_model_blocked"] = False
    elif event in PROCESS_ROUTE_MODEL_BLOCK_EVENTS:
        flags["process_route_model_submitted"] = False
        flags["process_route_model_repair_required"] = False
        flags["process_route_model_blocked"] = True

def _active_model_miss_review_block_flags(run_state: dict[str, Any]) -> tuple[str, ...]:
    flags = run_state.get("flags", {})
    return tuple(flag for flag in MODEL_MISS_REVIEW_BLOCK_FLAGS if flags.get(flag))

def _require_single_active_model_miss_review_block(run_state: dict[str, Any], purpose: str) -> str:
    active_flags = _active_model_miss_review_block_flags(run_state)
    if not active_flags:
        raise RouterError(
            f"{purpose} requires an active model-miss reviewer block state "
            f"({', '.join(MODEL_MISS_REVIEW_BLOCK_FLAGS)})"
        )
    if len(active_flags) != 1:
        raise RouterError(
            f"{purpose} requires exactly one active model-miss reviewer block state; "
            f"active flags: {', '.join(active_flags)}"
        )
    return active_flags[0]

_LOCAL_NAMES = set(globals())
