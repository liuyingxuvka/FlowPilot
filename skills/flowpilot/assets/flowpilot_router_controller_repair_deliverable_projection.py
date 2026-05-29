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
    _projection_boundary._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_controller_repair"

import flowpilot_router_controller_repair_deliverable_projection_boundary as _projection_boundary
from flowpilot_router_controller_repair_deliverable_projection_boundary import (
    _sync_controller_boundary_confirmation_from_artifact,
    _controller_boundary_flags_synced,
    _router_scheduler_row_for_controller_entry,
    _done_controller_receipt_for_entry,
    _reconcile_controller_boundary_confirmation_projection,
)

def _update_controller_action_entry_fields(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    action_id: str,
    status: str | None = None,
    fields: dict[str, Any] | None = None,
    router_state: str | None = None,
    reconciliation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not action_id:
        return {}
    path = _controller_action_path(run_root, action_id)
    entry = read_json_if_exists(path)
    if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return {}
    if status is not None:
        entry["status"] = status
    if fields:
        entry.update(fields)
    entry["updated_at"] = utc_now()
    write_json(path, entry)
    row_id = str(entry.get("router_scheduler_row_id") or "")
    if row_id and router_state:
        _update_router_scheduler_row(
            project_root,
            run_root,
            run_state,
            row_id=row_id,
            router_state=router_state,
            reconciliation=reconciliation or fields or {},
        )
    _rebuild_controller_action_ledger(project_root, run_root, run_state)
    return entry

def _defer_controller_postcondition_reconciliation_retry(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    entry: dict[str, Any],
    action: dict[str, Any],
    apply_result: dict[str, Any],
) -> dict[str, Any]:
    postcondition = str(
        apply_result.get("postcondition")
        or _pending_action_postcondition(action)
        or ""
    ).strip()
    if not postcondition:
        return {"retry_applicable": False, "reason": "no_postcondition"}

    action_id = str(entry.get("action_id") or action.get("controller_action_id") or "")
    attempts_used = int(entry.get("postcondition_reconciliation_attempts") or 0)
    max_attempts = CONTROLLER_POSTCONDITION_RECONCILIATION_MAX_ATTEMPTS
    if attempts_used >= max_attempts:
        return {
            "retry_applicable": True,
            "retry_pending": False,
            "retry_budget_exhausted": True,
            "direct_retry_attempts_used": attempts_used,
            "direct_retry_budget": max_attempts,
            "postcondition": postcondition,
        }

    next_attempt = attempts_used + 1
    now = utc_now()
    reconciliation = {
        "source": "controller_action_receipt_postcondition_retry_pending",
        "reason": str(apply_result.get("reason") or "postcondition_not_satisfied"),
        "postcondition": postcondition,
        "retry_attempt": next_attempt,
        "max_retry_attempts": max_attempts,
        "next_step": "retry_controller_receipt_reconciliation_before_pm_blocker",
        "apply_result": _json_safe(apply_result),
        "updated_at": now,
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=action_id,
        fields={
            "router_reconciliation_status": "retry_pending",
            "router_reconciliation_retry_pending_at": now,
            "router_reconciliation_retry_reason": reconciliation["reason"],
            "postcondition_reconciliation_attempts": next_attempt,
            "max_postcondition_reconciliation_attempts": max_attempts,
            "postcondition_reconciliation_exhausted": False,
            "router_reconciliation": reconciliation,
        },
        router_state="waiting",
        reconciliation=reconciliation,
    )
    append_history(
        run_state,
        "router_deferred_controller_receipt_postcondition_retry",
        {
            "action_type": action.get("action_type"),
            "controller_action_id": action_id,
            "router_scheduler_row_id": entry.get("router_scheduler_row_id") or action.get("router_scheduler_row_id"),
            "postcondition": postcondition,
            "retry_attempt": next_attempt,
            "max_retry_attempts": max_attempts,
        },
    )
    save_run_state(run_root, run_state)
    return {
        "retry_applicable": True,
        "retry_pending": True,
        "retry_budget_exhausted": False,
        "direct_retry_attempts_used": next_attempt,
        "direct_retry_budget": max_attempts,
        "postcondition": postcondition,
    }

__all__ = (
    '_update_controller_action_entry_fields',
    '_defer_controller_postcondition_reconciliation_retry',
    '_sync_controller_boundary_confirmation_from_artifact',
    '_controller_boundary_flags_synced',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_reconcile_controller_boundary_confirmation_projection',
)

_LOCAL_NAMES = set(globals())
