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

from flowpilot_router_controller_repair_deliverable_projection import _update_controller_action_entry_fields

def _mark_controller_deliverable_repair_resolved(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    repair_action: dict[str, Any],
    receipt: dict[str, Any] | None = None,
    applied_postcondition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if str(repair_action.get("action_type") or "") != CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        return {}
    original_id = str(repair_action.get("repair_of_controller_action_id") or "")
    repair_id = str(
        (receipt or {}).get("action_id")
        or repair_action.get("controller_action_id")
        or ""
    )
    if not original_id:
        return {}
    now = utc_now()
    resolution = {
        "deliverable_status": "resolved",
        "resolution_status": "resolved_by_controller_repair",
        "resolved_at": now,
        "resolved_by_controller_action_id": repair_id,
        "pending_deliverable_repair_action_id": None,
        "pending_deliverable_repair_attempt": 0,
        "last_repair_result": applied_postcondition or {},
        "router_reconciliation_status": "reconciled",
        "router_reconciled_at": now,
        "router_reconciliation": applied_postcondition or {
            "applied": True,
            "source": "controller_deliverable_repair_resolved",
        },
    }
    original = _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="resolved",
        fields=resolution,
        router_state="reconciled",
        reconciliation=resolution,
    )
    if repair_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=repair_id,
            fields={
                "router_reconciliation_status": "reconciled",
                "router_reconciled_at": now,
                "router_reconciliation": applied_postcondition or {},
            },
            router_state="reconciled",
            reconciliation=applied_postcondition or resolution,
        )
    append_history(
        run_state,
        "router_resolved_controller_action_by_deliverable_repair",
        {
            "original_controller_action_id": original_id,
            "repair_controller_action_id": repair_id,
            "original_action_type": original.get("action_type"),
        },
    )
    return original

def _controller_deliverable_failed_repair_ids(original_entry: dict[str, Any]) -> list[str]:
    raw = original_entry.get("deliverable_repair_failed_action_ids")
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, str) and item]

def _controller_repair_action_is_pending(run_root: Path, action_id: str) -> bool:
    if not action_id:
        return False
    action = read_json_if_exists(_controller_action_path(run_root, action_id))
    if action.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return False
    if action.get("status") in CONTROLLER_ACTION_CLOSED_STATUSES:
        return False
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get("schema_version") == CONTROLLER_RECEIPT_SCHEMA and receipt.get("status") in {"done", "blocked", "skipped"}:
        return False
    return True

def _write_controller_deliverable_budget_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    original_entry: dict[str, Any],
    current_action: dict[str, Any],
    receipt: dict[str, Any],
    missing_deliverables: list[dict[str, Any]],
    apply_result: dict[str, Any] | None,
) -> dict[str, Any]:
    original_id = str(original_entry.get("action_id") or "")
    current_id = str(receipt.get("action_id") or current_action.get("controller_action_id") or "")
    payload = {
        "controller_action_id": original_id,
        "current_controller_action_id": current_id,
        "action_type": original_entry.get("action_type"),
        "postcondition": _pending_action_postcondition(
            original_entry.get("action") if isinstance(original_entry.get("action"), dict) else current_action
        ),
        "missing_deliverables": missing_deliverables,
        "deliverable_repair_attempts": int(original_entry.get("deliverable_repair_attempts") or 0),
        "deliverable_repair_failed_receipts": int(original_entry.get("deliverable_repair_failed_receipts") or 0),
        "deliverable_repair_failed_action_ids": _controller_deliverable_failed_repair_ids(original_entry),
        "max_deliverable_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "controller_receipt_payload": receipt.get("payload") if isinstance(receipt.get("payload"), dict) else {},
        "apply_result": apply_result or {},
    }
    now = utc_now()
    blocker = _write_control_blocker(
        project_root,
        run_root,
        run_state,
        source="controller_deliverable_repair_budget_exhausted",
        error_message=(
            f"Controller action {original_entry.get('action_type')} still lacks required deliverables "
            f"after {CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS} repair attempts."
        ),
        action_type=str(original_entry.get("action_type") or ""),
        payload=payload,
    )
    fields = {
        "deliverable_status": "blocked",
        "deliverable_repair_failed_receipts": int(original_entry.get("deliverable_repair_failed_receipts") or 0),
        "deliverable_repair_failed_action_ids": _controller_deliverable_failed_repair_ids(original_entry),
        "pending_deliverable_repair_action_id": None,
        "pending_deliverable_repair_attempt": 0,
        "router_reconciliation_status": "blocked",
        "router_reconciliation_blocked_at": now,
        "router_reconciliation_blocker": payload,
        "control_blocker_id": blocker.get("blocker_id"),
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="blocked",
        fields=fields,
        router_state="blocked",
        reconciliation=fields,
    )
    if current_id and current_id != original_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=current_id,
            status="blocked",
            fields=fields,
            router_state="blocked",
            reconciliation=fields,
        )
    _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        action_type=str(original_entry.get("action_type") or ""),
        router_state="blocked",
        workflow_owner="router",
        postcondition=str(payload.get("postcondition") or ""),
        source="controller_deliverable_repair_budget_exhausted",
        receipt_path=project_relative(project_root, _controller_receipt_path(run_root, current_id)) if current_id else "",
        details=payload,
    )
    return blocker

__all__ = (
    '_mark_controller_deliverable_repair_resolved',
    '_controller_deliverable_failed_repair_ids',
    '_controller_repair_action_is_pending',
    '_write_controller_deliverable_budget_blocker',
)

_LOCAL_NAMES = set(globals())
