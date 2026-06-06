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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_controller_repair"

def _close_waiting_controller_actions_for_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {"changed": False, "closed_count": 0, "closed_action_ids": []}
    now = utc_now()
    payload_digest = _external_event_payload_digest(payload)
    closed: list[dict[str, Any]] = []
    for action_path in sorted(action_dir.glob("*.json")):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get("status") != "waiting":
            continue
        action_type = str(entry.get("action_type") or "")
        if action_type != "await_role_decision":
            continue
        allowed_events = _controller_wait_allowed_external_events(entry)
        if event not in allowed_events:
            continue
        action_id = str(entry.get("action_id") or "")
        reconciliation = {
            "source": source,
            "event": event,
            "event_payload_sha256": payload_digest,
            "allowed_external_events": allowed_events,
            "reconciled_at": now,
            "controller_receipt_required": False,
        }
        entry["status"] = "done"
        entry["completed_at"] = now
        entry["completion_source"] = "router_external_event_reconciliation"
        entry["satisfied_by_external_event"] = event
        entry["satisfied_by_event_payload_sha256"] = payload_digest
        entry["router_reconciliation_status"] = "reconciled"
        entry["router_reconciled_at"] = now
        entry["router_reconciliation"] = reconciliation
        entry["controller_receipt_required"] = False
        entry["router_must_not_mark_done_without_controller_receipt"] = False
        write_json(action_path, entry)
        row_id = str(entry.get("router_scheduler_row_id") or "")
        if row_id:
            _update_router_scheduler_row(
                project_root,
                run_root,
                run_state,
                row_id=row_id,
                router_state="reconciled",
                reconciliation=reconciliation,
            )
        closed.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "label": entry.get("label"),
                "router_scheduler_row_id": row_id or None,
            }
        )
    pending = run_state.get("pending_action")
    pending_cleared = False
    if isinstance(pending, dict) and pending.get("action_type") == "await_role_decision":
        pending_allowed = [
            str(item)
            for item in (pending.get("allowed_external_events") or [])
            if isinstance(item, str) and item.strip()
        ]
        if event in pending_allowed:
            run_state["pending_action"] = None
            pending_cleared = True
    if not closed and not pending_cleared:
        return {"changed": False, "closed_count": 0, "closed_action_ids": []}
    ledger = _rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(
        run_state,
        "router_closed_controller_waits_satisfied_by_external_event",
        {
            "event": event,
            "source": source,
            "closed_count": len(closed),
            "closed_action_ids": [item["action_id"] for item in closed if item.get("action_id")],
            "pending_action_cleared": pending_cleared,
            "ledger_counts": ledger.get("counts"),
        },
    )
    return {
        "changed": True,
        "closed_count": len(closed),
        "closed_action_ids": [item["action_id"] for item in closed if item.get("action_id")],
        "pending_action_cleared": pending_cleared,
        "closed_actions": closed,
    }

def _pending_controller_action_id(pending_action: dict[str, Any]) -> str:
    action_id = str(pending_action.get("controller_action_id") or "").strip()
    if action_id:
        return action_id
    return _controller_action_id_for_action(pending_action)

def _pending_action_postcondition(pending_action: dict[str, Any]) -> str:
    postcondition = pending_action.get("postcondition")
    if isinstance(postcondition, str) and postcondition.strip():
        return postcondition.strip()
    contract = pending_action.get("next_step_contract")
    if isinstance(contract, dict):
        postcondition = contract.get("postcondition")
        if isinstance(postcondition, str) and postcondition.strip():
            return postcondition.strip()
    return ""

def _receipt_for_pending_controller_action(run_root: Path, pending_action: dict[str, Any]) -> dict[str, Any]:
    action_id = _pending_controller_action_id(pending_action)
    if not action_id:
        return {}
    receipt = read_json_if_exists(_controller_receipt_path(run_root, action_id))
    if receipt.get("schema_version") != CONTROLLER_RECEIPT_SCHEMA:
        return {}
    if str(receipt.get("action_id") or "") != action_id:
        return {}
    return receipt

def _pending_action_postcondition_satisfied(run_state: dict[str, Any], postcondition: str) -> bool:
    if not postcondition:
        return True
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(flags.get(postcondition))

__all__ = (
    '_close_waiting_controller_actions_for_external_event',
    '_pending_controller_action_id',
    '_pending_action_postcondition',
    '_receipt_for_pending_controller_action',
    '_pending_action_postcondition_satisfied',
)

_LOCAL_NAMES = set(globals())
