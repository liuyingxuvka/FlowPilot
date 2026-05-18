"""Internal router owner helpers extracted from flowpilot_router.

The public compatibility names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so legacy private helper lookups remain
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

OWNER_MODULE = "flowpilot_router_route_artifacts"

def _write_pm_research_absorption(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_pm_research_absorption(_bound_router(), project_root, run_root, run_state)

def _validate_current_node_packet_envelope(project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_current_node_packet_envelope(_bound_router(), project_root, run_root, run_state, envelope, envelope_path, frontier, plan)

def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_packet_event(_bound_router(), project_root, run_root, run_state, payload)

def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_result_event(_bound_router(), project_root, run_state, payload)

def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_reviewer_pass(_bound_router(), project_root, run_state, payload)

def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_route.route_payload_from_reviewed_draft(
        _bound_router(),
        project_root,
        run_root,
        payload,
    )

def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_activation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_mutation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

__all__ = (
    '_write_pm_research_absorption',
    '_validate_current_node_packet_envelope',
    '_validate_current_node_packet_event',
    '_validate_current_node_result_event',
    '_validate_current_node_reviewer_pass',
    '_route_payload_from_reviewed_draft',
    '_write_route_activation',
    '_write_route_mutation',
)

_LOCAL_NAMES = set(globals())
