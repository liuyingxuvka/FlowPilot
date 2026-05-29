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

OWNER_MODULE = "flowpilot_router_controller_repair"

def _controller_boundary_required_deliverable(project_root: Path, run_root: Path) -> dict[str, Any]:
    contract = CONTROLLER_STATEFUL_VALIDATOR_TABLE["confirm_controller_core_boundary"]
    return {
        "deliverable_id": contract["deliverable_id"],
        "artifact_kind": contract["artifact_kind"],
        "path": project_relative(project_root, _controller_boundary_confirmation_path(run_root)),
        "schema_version": CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA,
        "postcondition": contract["postcondition"],
        "validator": contract["validator"],
        "runtime_channel": contract["runtime_channel"],
        "output_type": contract["output_type"],
        "output_contract_id": contract["output_contract_id"],
        "required_role": "controller",
        "path_key": "confirmation_path",
        "hash_key": "confirmation_hash",
        "controller_may_read_sealed_bodies": False,
        "controller_may_approve_gates": False,
        "controller_may_mutate_route": False,
        "required_before_router_reconciles_done_receipt": True,
    }

def _controller_action_required_deliverables(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
) -> list[dict[str, Any]]:
    del run_state
    raw_required = action.get("required_deliverables")
    if isinstance(raw_required, list) and raw_required:
        return [item for item in raw_required if isinstance(item, dict)]
    raw_missing = action.get("missing_deliverables")
    if isinstance(raw_missing, list) and raw_missing:
        return [item for item in raw_missing if isinstance(item, dict)]
    action_type = str(action.get("action_type") or "")
    if action_type == "confirm_controller_core_boundary":
        return [_controller_boundary_required_deliverable(project_root, run_root)]
    repair_target = str(action.get("repair_target_action_type") or "")
    if action_type == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE and repair_target == "confirm_controller_core_boundary":
        return [_controller_boundary_required_deliverable(project_root, run_root)]
    return []

def _controller_deliverable_contract(deliverables: list[dict[str, Any]]) -> dict[str, Any]:
    if not deliverables:
        return {}
    runtime_contracts = [
        {
            "deliverable_id": str(item.get("deliverable_id") or ""),
            "runtime_channel": str(item.get("runtime_channel") or ""),
            "output_type": str(item.get("output_type") or ""),
            "output_contract_id": str(item.get("output_contract_id") or ""),
            "required_role": str(item.get("required_role") or "controller"),
            "path_key": str(item.get("path_key") or ""),
            "hash_key": str(item.get("hash_key") or ""),
        }
        for item in deliverables
        if isinstance(item, dict) and item.get("runtime_channel")
    ]
    return {
        "schema_version": "flowpilot.controller_deliverable_contract.v1",
        "required_deliverables": deliverables,
        "runtime_contracts": runtime_contracts,
        "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "missing_deliverable_policy": "reclaim_existing_then_controller_repair_then_blocker",
        "router_must_not_synthesize_missing_controller_deliverable_during_receipt_reconciliation": True,
    }

def _missing_deliverables_for_apply_result(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    apply_result: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if isinstance(apply_result, dict):
        raw_missing = apply_result.get("missing_deliverables")
        if isinstance(raw_missing, list) and raw_missing:
            return [item for item in raw_missing if isinstance(item, dict)]
    return _controller_action_required_deliverables(project_root, run_root, run_state, action)

__all__ = (
    '_controller_boundary_required_deliverable',
    '_controller_action_required_deliverables',
    '_controller_deliverable_contract',
    '_missing_deliverables_for_apply_result',
)

_LOCAL_NAMES = set(globals())
