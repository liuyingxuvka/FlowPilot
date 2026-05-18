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

def _sync_controller_boundary_confirmation_from_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        missing = [_controller_boundary_required_deliverable(project_root, run_root)]
        _record_router_ownership_entry(
            project_root,
            run_root,
            run_state,
            action_id=str(pending_action.get("controller_action_id") or ""),
            action_type=str(pending_action.get("action_type") or ""),
            router_state="router_reclaim_pending",
            workflow_owner="router",
            postcondition="controller_role_confirmed",
            source=source,
            receipt_path=str(pending_action.get("controller_receipt_path") or ""),
            details={
                "reason": "controller_boundary_confirmation_missing_or_invalid",
                "missing_deliverables": missing,
                "controller_receipt_payload": receipt_payload,
            },
        )
        return {
            "applied": False,
            "reason": "controller_boundary_confirmation_missing_or_invalid",
            "action_type": pending_action.get("action_type"),
            "repairable": True,
            "missing_deliverables": missing,
        }
    confirmation = run_state.get("controller_boundary_confirmation")
    if not isinstance(confirmation, dict) or not confirmation.get("path"):
        confirmation = {
            "path": project_relative(project_root, context["path"]),
            "sha256": context["sha256"],
            "controller_core_path": context["confirmation"].get("controller_core_path"),
            "controller_core_sha256": context["confirmation"].get("controller_core_sha256"),
            "controller_policy_sha256": context["confirmation"].get("controller_policy_sha256"),
        }
    confirmation.update(
        {
            "runtime_channel": "role_output_runtime",
            "output_type": CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
            "output_contract_id": CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
            "role_output_envelope": context.get("role_output_envelope"),
            "role_output_runtime_receipt_path": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("path")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
            "role_output_runtime_receipt_hash": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("hash")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
        }
    )
    run_state.setdefault("flags", {})["controller_role_confirmed"] = True
    run_state.setdefault("flags", {})["controller_role_confirmed_from_router_core"] = True
    run_state.setdefault("flags", {})["controller_boundary_confirmation_written"] = True
    run_state["controller_boundary_confirmation"] = confirmation
    if not any(
        isinstance(item, dict) and item.get("event") == "controller_role_confirmed_from_router_core"
        for item in run_state.get("events", [])
    ):
        run_state.setdefault("events", []).append(
            {
                "event": "controller_role_confirmed_from_router_core",
                "summary": "Controller confirmed the Router-delivered controller.core boundary.",
                "payload": confirmation,
                "recorded_at": utc_now(),
            }
        )
    entry = _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=str(pending_action.get("controller_action_id") or ""),
        action_type=str(pending_action.get("action_type") or ""),
        router_state="router_reclaimed",
        workflow_owner="router",
        postcondition="controller_role_confirmed",
        source=source,
        receipt_path=str(pending_action.get("controller_receipt_path") or ""),
        artifact_refs={
            "controller_boundary_confirmation_path": project_relative(project_root, context["path"]),
            "controller_boundary_confirmation_hash": context["sha256"],
        },
        details={"controller_receipt_payload": receipt_payload},
    )
    return {
        "applied": True,
        "postcondition": "controller_role_confirmed",
        "source": "router_owned_controller_boundary_confirmation_reclaim",
        "router_ownership_entry_id": entry.get("entry_id"),
    }

def _controller_boundary_flags_synced(run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(
        flags.get("controller_role_confirmed")
        and flags.get("controller_role_confirmed_from_router_core")
        and flags.get("controller_boundary_confirmation_written")
    )

def _router_scheduler_row_for_controller_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._router_scheduler_row_for_controller_entry(_bound_router(), run_root, entry)

def _done_controller_receipt_for_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._done_controller_receipt_for_entry(_bound_router(), run_root, entry)

def _reconcile_controller_boundary_confirmation_projection(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        return {"changed": False, "reason": "controller_boundary_confirmation_missing_or_invalid"}
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {"changed": False, "reason": "controller_action_dir_missing"}

    flags_were_synced = _controller_boundary_flags_synced(run_state)
    reconciled_actions: list[str] = []
    pending_cleared = False
    last_projection: dict[str, Any] | None = None

    for action_path in sorted(action_dir.glob("*.json")):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get("action_type") != "confirm_controller_core_boundary":
            continue
        if entry.get("status") != "done":
            continue
        receipt = _done_controller_receipt_for_entry(run_root, entry)
        if not receipt:
            continue
        action = dict(entry.get("action") if isinstance(entry.get("action"), dict) else {})
        action_id = str(entry.get("action_id") or action.get("controller_action_id") or "").strip()
        if not action_id:
            continue
        action.setdefault("action_type", "confirm_controller_core_boundary")
        action.setdefault("controller_action_id", action_id)
        action.setdefault("postcondition", "controller_role_confirmed")
        if entry.get("router_scheduler_row_id"):
            action.setdefault("router_scheduler_row_id", entry.get("router_scheduler_row_id"))
        action.setdefault(
            "controller_receipt_path",
            project_relative(project_root, _controller_receipt_path(run_root, action_id)),
        )
        row = _router_scheduler_row_for_controller_entry(run_root, entry)
        row_reconciled = bool(row.get("router_state") == "reconciled")
        entry_reconciled = bool(entry.get("router_reconciliation_status") == "reconciled")
        projection_missing = (
            not _controller_boundary_flags_synced(run_state)
            or not isinstance(run_state.get("controller_boundary_confirmation"), dict)
            or not run_state.get("controller_boundary_confirmation", {}).get("path")
        )
        if entry_reconciled and row_reconciled and not projection_missing:
            continue
        applied = _sync_controller_boundary_confirmation_from_artifact(
            project_root,
            run_root,
            run_state,
            action,
            receipt,
            source=source,
        )
        if not applied.get("applied"):
            continue
        reconciliation = dict(applied)
        reconciliation["projection_reconciliation_source"] = source
        now = utc_now()
        entry["status"] = "done"
        entry["router_reconciliation_status"] = "reconciled"
        entry["router_reconciled_at"] = now
        entry["router_reconciliation"] = reconciliation
        entry["updated_at"] = now
        write_json(action_path, entry)
        if entry.get("router_scheduler_row_id"):
            _update_router_scheduler_row(
                project_root,
                run_root,
                run_state,
                row_id=str(entry["router_scheduler_row_id"]),
                router_state="reconciled",
                reconciliation=reconciliation,
            )
        pending = run_state.get("pending_action")
        if isinstance(pending, dict) and (
            pending.get("controller_action_id") == action_id
            or pending.get("action_type") == "confirm_controller_core_boundary"
        ):
            run_state["pending_action"] = None
            pending_cleared = True
        reconciled_actions.append(action_id)
        last_projection = reconciliation

    changed = bool(reconciled_actions) or flags_were_synced != _controller_boundary_flags_synced(run_state)
    if not changed:
        return {"changed": False, "reason": "controller_boundary_projection_already_synced"}
    ledger = _rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(
        run_state,
        "router_reconciled_controller_boundary_projection",
        {
            "source": source,
            "reconciled_action_ids": reconciled_actions,
            "pending_action_cleared": pending_cleared,
            "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
            "ledger_counts": ledger.get("counts"),
            "projection": last_projection,
        },
    )
    return {
        "changed": True,
        "reconciled_action_ids": reconciled_actions,
        "pending_action_cleared": pending_cleared,
        "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
        "ledger_counts": ledger.get("counts"),
    }

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
    '_controller_boundary_required_deliverable',
    '_controller_action_required_deliverables',
    '_controller_deliverable_contract',
    '_missing_deliverables_for_apply_result',
    '_update_controller_action_entry_fields',
    '_defer_controller_postcondition_reconciliation_retry',
    '_sync_controller_boundary_confirmation_from_artifact',
    '_controller_boundary_flags_synced',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_reconcile_controller_boundary_confirmation_projection',
    '_mark_controller_deliverable_repair_resolved',
    '_controller_deliverable_failed_repair_ids',
    '_controller_repair_action_is_pending',
    '_write_controller_deliverable_budget_blocker',
)

_LOCAL_NAMES = set(globals())
