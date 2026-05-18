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

def _write_role_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"block report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is True:
        raise RouterError("block report cannot pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"block report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": False,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "repair_recommendation": payload.get("repair_recommendation"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

def _gate_outcome_path_from_token(run_root: Path, token: str) -> Path:
    if token == "__current_route_draft__":
        return _current_route_draft_path(run_root)
    if token == "__parent_backward_targets__":
        frontier = _active_frontier(run_root)
        return run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if token == "__active_node_acceptance_plan__":
        frontier = _active_frontier(run_root)
        return _active_node_acceptance_plan_path(run_root, frontier)
    if token.startswith("__active_node_root__/"):
        frontier = _active_frontier(run_root)
        return _active_node_root(run_root, frontier) / token.removeprefix("__active_node_root__/")
    return run_root / token

def _write_gate_outcome_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    event: str,
) -> None:
    spec = GATE_OUTCOME_BLOCK_EVENT_SPECS[event]
    checked_paths = [
        _gate_outcome_path_from_token(run_root, str(token))
        for token in spec.get("checked_paths", ())
    ]
    report_path = _gate_outcome_path_from_token(run_root, str(spec["path"]))
    _write_role_block_report(
        project_root,
        run_root,
        run_state,
        payload,
        expected_role=str(spec["expected_role"]),
        path=report_path,
        schema_version=str(spec["schema_version"]),
        checked_paths=checked_paths,
    )
    flags = run_state.setdefault("flags", {})
    for reset_flag in spec.get("reset_flags", ()):
        flags[str(reset_flag)] = False
    gate_blocks = run_state.setdefault("gate_outcome_blocks", [])
    if not isinstance(gate_blocks, list):
        gate_blocks = []
    record = {
        "event": event,
        "report_path": project_relative(project_root, report_path),
        "repair_resets": [str(flag) for flag in spec.get("reset_flags", ())],
        "recorded_at": utc_now(),
    }
    gate_blocks.append(record)
    run_state["gate_outcome_blocks"] = gate_blocks[-20:]
    run_state["active_gate_outcome_block"] = record

def _clear_active_gate_outcome_block_for_pass(run_state: dict[str, Any], *, event: str) -> None:
    cleared_events = set(GATE_OUTCOME_PASS_CLEARS_EVENTS.get(event, ()))
    if not cleared_events:
        return
    active = run_state.get("active_gate_outcome_block")
    if not isinstance(active, dict) or active.get("event") not in cleared_events:
        return
    cleared_at = utc_now()
    active["status"] = "cleared_by_pass"
    active["cleared_by_event"] = event
    active["cleared_at"] = cleared_at
    blocks = run_state.get("gate_outcome_blocks")
    if isinstance(blocks, list):
        for record in reversed(blocks):
            if not isinstance(record, dict):
                continue
            if record.get("event") == active.get("event") and record.get("report_path") == active.get("report_path"):
                record["status"] = "cleared_by_pass"
                record["cleared_by_event"] = event
                record["cleared_at"] = cleared_at
                break
    run_state["active_gate_outcome_block"] = None

__all__ = (
    '_write_role_block_report',
    '_gate_outcome_path_from_token',
    '_write_gate_outcome_block_report',
    '_clear_active_gate_outcome_block_for_pass',
)

_LOCAL_NAMES = set(globals())
