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

def _schedule_controller_deliverable_repair(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    pending_action: dict[str, Any],
    receipt: dict[str, Any],
    apply_result: dict[str, Any] | None = None,
    source: str,
) -> dict[str, Any]:
    missing_deliverables = _missing_deliverables_for_apply_result(
        project_root,
        run_root,
        run_state,
        pending_action,
        apply_result,
    )
    if not missing_deliverables:
        return {"scheduled": False, "repairable": False, "reason": "no_declared_missing_deliverables"}
    pending_action_id = str(receipt.get("action_id") or pending_action.get("controller_action_id") or "")
    if str(pending_action.get("action_type") or "") == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE:
        original_id = str(pending_action.get("repair_of_controller_action_id") or "")
        repair_target_action_type = str(pending_action.get("repair_target_action_type") or "")
    else:
        original_id = pending_action_id
        repair_target_action_type = str(pending_action.get("action_type") or receipt.get("action_type") or "")
    if not original_id:
        return {"scheduled": False, "repairable": False, "reason": "missing_original_controller_action_id"}
    original_entry = read_json_if_exists(_controller_action_path(run_root, original_id))
    if original_entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
        return {"scheduled": False, "repairable": False, "reason": "missing_original_controller_action_entry"}
    issued_attempts = int(original_entry.get("deliverable_repair_attempts") or 0)
    failed_ids = _controller_deliverable_failed_repair_ids(original_entry)
    failed_receipts = int(original_entry.get("deliverable_repair_failed_receipts") or len(failed_ids) or 0)
    is_repair_receipt = str(pending_action.get("action_type") or "") == CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE
    pending_repair_action_id = str(original_entry.get("pending_deliverable_repair_action_id") or "")
    pending_repair_attempt = int(original_entry.get("pending_deliverable_repair_attempt") or 0)
    if is_repair_receipt and pending_action_id:
        if pending_action_id not in failed_ids:
            failed_ids.append(pending_action_id)
            failed_receipts += 1
        if pending_repair_action_id == pending_action_id:
            pending_repair_action_id = ""
            pending_repair_attempt = 0
    if failed_receipts >= CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS:
        original_entry = {
            **original_entry,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": None,
            "pending_deliverable_repair_attempt": 0,
        }
        blocker = _write_controller_deliverable_budget_blocker(
            project_root,
            run_root,
            run_state,
            original_entry=original_entry,
            current_action=pending_action,
            receipt=receipt,
            missing_deliverables=missing_deliverables,
            apply_result=apply_result,
        )
        return {
            "scheduled": False,
            "blocked": True,
            "budget_exhausted": True,
            "blocker": blocker,
            "missing_deliverables": missing_deliverables,
        }
    if pending_repair_action_id and _controller_repair_action_is_pending(run_root, pending_repair_action_id):
        pending_fields = {
            "deliverable_status": "repair_pending",
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": pending_repair_action_id,
            "pending_deliverable_repair_attempt": pending_repair_attempt,
            "missing_deliverables": missing_deliverables,
            "last_incomplete_receipt_action_id": pending_action_id,
            "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "last_apply_result": apply_result or {},
            "router_reconciliation_status": "repair_pending",
            "router_reconciliation_updated_at": utc_now(),
        }
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=original_id,
            status="repair_pending",
            fields=pending_fields,
            router_state="waiting",
            reconciliation=pending_fields,
        )
        return {
            "scheduled": False,
            "pending_repair": True,
            "repairable": True,
            "missing_deliverables": missing_deliverables,
            "pending_repair_action_id": pending_repair_action_id,
            "pending_repair_attempt": pending_repair_attempt,
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
        }
    if issued_attempts >= CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS:
        pending_fields = {
            "deliverable_status": "repair_pending",
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
            "deliverable_repair_failed_action_ids": failed_ids,
            "pending_deliverable_repair_action_id": pending_repair_action_id or None,
            "pending_deliverable_repair_attempt": pending_repair_attempt,
            "missing_deliverables": missing_deliverables,
            "last_incomplete_receipt_action_id": pending_action_id,
            "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "last_apply_result": apply_result or {},
            "router_reconciliation_status": "repair_pending",
            "router_reconciliation_updated_at": utc_now(),
        }
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=original_id,
            status="repair_pending",
            fields=pending_fields,
            router_state="waiting",
            reconciliation=pending_fields,
        )
        return {
            "scheduled": False,
            "pending_repair": True,
            "repairable": True,
            "reason": "repair_attempt_issued_waiting_for_returned_evidence",
            "missing_deliverables": missing_deliverables,
            "deliverable_repair_attempts": issued_attempts,
            "deliverable_repair_failed_receipts": failed_receipts,
        }
    next_attempt = issued_attempts + 1
    deliverable_paths = [
        str(item.get("path") or "")
        for item in missing_deliverables
        if isinstance(item, dict) and str(item.get("path") or "").strip()
    ]
    runtime_relay_operations = [
        item.get("runtime_relay_operation")
        for item in missing_deliverables
        if isinstance(item, dict) and isinstance(item.get("runtime_relay_operation"), dict)
    ]
    runtime_expected_writes = [
        str(path)
        for operation in runtime_relay_operations
        for path in (operation.get("expected_writes") or [])
        if isinstance(path, str) and path.strip()
    ]
    original_action = original_entry.get("action") if isinstance(original_entry.get("action"), dict) else pending_action
    allowed_reads = [
        str(original_entry.get("action_path") or ""),
        project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
    ]
    allowed_reads.extend(str(path) for path in (original_action.get("allowed_reads") or []) if isinstance(path, str))
    repair_action = make_action(
        action_type=CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE,
        actor="controller",
        label=f"controller_completes_missing_deliverable_attempt_{next_attempt}_{original_id}",
        summary=(
            f"Complete missing Controller deliverable(s) for {repair_target_action_type}; "
            "Router will reconcile the original action only after the declared artifact validates."
        ),
        allowed_reads=[item for item in dict.fromkeys(allowed_reads) if item],
        allowed_writes=[item for item in dict.fromkeys(deliverable_paths + runtime_expected_writes + [project_relative(project_root, run_state_path(run_root))]) if item],
        extra={
            "postcondition": _pending_action_postcondition(original_action),
            "repair_of_controller_action_id": original_id,
            "repair_target_action_type": repair_target_action_type,
            "repair_attempt": next_attempt,
            "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
            "missing_deliverables": missing_deliverables,
            "required_deliverables": missing_deliverables,
            "runtime_output_contracts": _controller_deliverable_contract(missing_deliverables).get("runtime_contracts", []),
            "runtime_relay_operations": runtime_relay_operations,
            "runtime_relay_operation_count": len(runtime_relay_operations),
            "source_receipt_action_id": pending_action_id,
            "source_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
            "idempotency_key": f"controller-deliverable-repair:{original_id}:{next_attempt}",
            "scope_kind": str(original_entry.get("scope_kind") or pending_action.get("scope_kind") or "startup"),
            "scope_id": str(original_entry.get("scope_id") or pending_action.get("scope_id") or "startup"),
            "sealed_body_reads_allowed": False,
            "controller_may_create_project_evidence": False,
            "deliverable_repair_is_router_scheduled": True,
        },
    )
    repair_entry = _write_controller_action_entry(project_root, run_root, run_state, repair_action)
    repair_ids = [item for item in (original_entry.get("repair_action_ids") or []) if isinstance(item, str)]
    repair_ids.append(str(repair_entry.get("action_id") or ""))
    now = utc_now()
    original_fields = {
        "deliverable_status": "repair_pending",
        "deliverable_repair_attempts": next_attempt,
        "deliverable_repair_failed_receipts": failed_receipts,
        "deliverable_repair_failed_action_ids": failed_ids,
        "max_deliverable_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
        "missing_deliverables": missing_deliverables,
        "repair_action_ids": repair_ids,
        "pending_deliverable_repair_action_id": repair_entry.get("action_id"),
        "pending_deliverable_repair_attempt": next_attempt,
        "last_incomplete_receipt_action_id": pending_action_id,
        "last_incomplete_receipt_path": project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
        "last_apply_result": apply_result or {},
        "router_reconciliation_status": "repair_pending",
        "router_reconciliation_updated_at": now,
    }
    _update_controller_action_entry_fields(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        status="repair_pending",
        fields=original_fields,
        router_state="waiting",
        reconciliation=original_fields,
    )
    if pending_action_id and pending_action_id != original_id:
        _update_controller_action_entry_fields(
            project_root,
            run_root,
            run_state,
            action_id=pending_action_id,
            status="superseded",
            fields={
                "deliverable_status": "superseded_by_next_repair",
                "superseded_by_controller_action_id": repair_entry.get("action_id"),
                "router_reconciliation_status": "superseded_by_next_repair",
                "router_reconciliation_updated_at": now,
            },
            router_state="superseded",
            reconciliation={"superseded_by_controller_action_id": repair_entry.get("action_id")},
        )
    run_state["pending_action"] = repair_action
    _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=original_id,
        action_type=repair_target_action_type,
        router_state="router_reclaim_pending",
        workflow_owner="router",
        postcondition=str(original_fields.get("postcondition") or _pending_action_postcondition(original_action)),
        source=source,
        receipt_path=project_relative(project_root, _controller_receipt_path(run_root, pending_action_id)) if pending_action_id else "",
        details={
            "missing_deliverables": missing_deliverables,
            "repair_controller_action_id": repair_entry.get("action_id"),
            "repair_attempt": next_attempt,
            "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
            "apply_result": apply_result or {},
        },
    )
    append_history(
        run_state,
        "router_scheduled_controller_deliverable_repair",
        {
            "original_controller_action_id": original_id,
            "repair_controller_action_id": repair_entry.get("action_id"),
            "repair_attempt": next_attempt,
            "missing_deliverables": missing_deliverables,
        },
    )
    return {
        "scheduled": True,
        "changed": True,
        "repair_action": repair_action,
        "repair_entry": repair_entry,
        "original_controller_action_id": original_id,
        "repair_attempt": next_attempt,
        "missing_deliverables": missing_deliverables,
    }

def _reclaim_router_owned_postcondition_from_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> dict[str, Any]:
    action_class = _controller_action_completion_class(pending_action)
    if action_class.get("kind") != "router_owned_durable_artifact":
        return {
            "applied": False,
            "reason": "not_router_owned_durable_artifact",
            "action_class": action_class,
        }

    action_type = str(pending_action.get("action_type") or "")
    action_id = str(pending_action.get("controller_action_id") or "")
    postcondition = str(action_class.get("postcondition") or _pending_action_postcondition(pending_action) or "")
    receipt_path = str(pending_action.get("controller_receipt_path") or "")

    if action_class.get("artifact_kind") == "startup_mechanical_audit":
        context = _startup_mechanical_audit_context(project_root, run_root, run_state)
        if context is None:
            _record_router_ownership_entry(
                project_root,
                run_root,
                run_state,
                action_id=action_id,
                action_type=action_type,
                router_state="router_reclaim_pending",
                workflow_owner="router",
                postcondition=postcondition,
                source="controller_receipt_reconciliation",
                receipt_path=receipt_path,
                details={
                    "reason": "startup_mechanical_audit_missing_or_invalid",
                    "controller_receipt_payload": receipt_payload,
                },
            )
            return {
                "applied": False,
                "reason": "startup_mechanical_audit_missing_or_invalid",
                "action_class": action_class,
            }

        run_state.setdefault("flags", {})[postcondition] = True
        run_state["startup_mechanical_audit"] = {
            "path": project_relative(project_root, context["audit_path"]),
            "sha256": context["audit_hash"],
            "proof_path": project_relative(project_root, context["proof_path"]),
            "proof_sha256": context["proof_hash"],
            "written_before_reviewer_card": not run_state["flags"].get("reviewer_startup_fact_check_card_delivered"),
            "reclaimed_from_durable_artifact": True,
        }
        entry = _record_router_ownership_entry(
            project_root,
            run_root,
            run_state,
            action_id=action_id,
            action_type=action_type,
            router_state="router_reclaimed",
            workflow_owner="router",
            postcondition=postcondition,
            source="controller_receipt_reconciliation",
            receipt_path=receipt_path,
            artifact_refs={
                "artifact_kind": action_class.get("artifact_kind"),
                "startup_mechanical_audit_path": project_relative(project_root, context["audit_path"]),
                "startup_mechanical_audit_hash": context["audit_hash"],
                "router_owned_check_proof_path": project_relative(project_root, context["proof_path"]),
                "router_owned_check_proof_hash": context["proof_hash"],
            },
            details={
                "controller_receipt_payload": receipt_payload,
                "controller_receipt_did_not_mark_workflow_complete": True,
            },
        )
        append_history(
            run_state,
            "router_reclaimed_controller_receipt_artifact_postcondition",
            {
                "action_type": action_type,
                "controller_action_id": action_id,
                "postcondition": postcondition,
                "router_ownership_entry_id": entry.get("entry_id"),
            },
        )
        return {
            "applied": True,
            "postcondition": postcondition,
            "source": "router_owned_artifact_reclaim",
            "action_class": action_class,
            "router_ownership_entry_id": entry.get("entry_id"),
        }

    return {
        "applied": False,
        "reason": "unsupported_router_owned_artifact",
        "action_class": action_class,
    }

__all__ = (
    '_schedule_controller_deliverable_repair',
    '_reclaim_router_owned_postcondition_from_artifact',
)

_LOCAL_NAMES = set(globals())
