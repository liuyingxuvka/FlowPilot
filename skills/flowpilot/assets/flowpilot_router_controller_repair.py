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

def _mail_sequence_entry(mail_id: str) -> dict[str, str] | None:
    return next((entry for entry in MAIL_SEQUENCE if entry["mail_id"] == mail_id), None)

def _mail_role_obligation_contract(entry: dict[str, str]) -> dict[str, Any] | None:
    if entry.get("mail_id") != "user_intake":
        return None
    return {
        "schema_version": "flowpilot.mail_role_obligation.v1",
        "mail_id": "user_intake",
        "target_role": "project_manager",
        "mail_is_formal_work_material": True,
        "not_prompt_or_instruction_card": True,
        "first_output_instruction_card_id": "pm.material_scan",
        "first_expected_output_event": "pm_issues_material_and_capability_scan_packets",
        "first_expected_output_summary": (
            "PM opens user_intake, reads the full user request through the runtime, "
            "then produces material/capability scan packet specs for Router."
        ),
        "blocks_independent_pm_dispatch_until_first_output": True,
        "controller_visibility": "metadata_only",
    }

def _mail_delivery_matches(item: object, *, mail_id: str, to_role: str) -> bool:
    return (
        isinstance(item, dict)
        and str(item.get("mail_id") or "") == mail_id
        and str(item.get("to_role") or "") == to_role
    )

def _find_mail_delivery(deliveries: object, *, mail_id: str, to_role: str) -> dict[str, Any] | None:
    if not isinstance(deliveries, list):
        return None
    for item in deliveries:
        if _mail_delivery_matches(item, mail_id=mail_id, to_role=to_role):
            return item
    return None

def _count_unique_mail_deliveries(deliveries: object) -> int:
    if not isinstance(deliveries, list):
        return 0
    keys = {
        (str(item.get("mail_id") or ""), str(item.get("to_role") or ""))
        for item in deliveries
        if isinstance(item, dict) and item.get("mail_id") and item.get("to_role")
    }
    return len(keys)

def _packet_record_for_mail_delivery(ledger: dict[str, Any], *, packet_id: str) -> dict[str, Any] | None:
    packets = ledger.get("packets")
    if not isinstance(packets, list):
        return None
    for item in packets:
        if isinstance(item, dict) and str(item.get("packet_id") or "") == packet_id:
            return item
    return None

def _mail_delivery_action_envelope_path(
    project_root: Path,
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> Path | None:
    candidates: list[object] = []
    candidates.append(receipt_payload.get("packet_envelope_path"))
    allowed_reads = pending_action.get("allowed_reads")
    if isinstance(allowed_reads, list):
        candidates.extend(allowed_reads)
    for candidate in candidates:
        raw_path = str(candidate or "").strip()
        if not raw_path:
            continue
        path = resolve_project_path(project_root, raw_path)
        if path.exists():
            return path
    return None

def _mail_delivery_packet_released(record: dict[str, Any] | None, *, to_role: str) -> bool:
    if not isinstance(record, dict):
        return False
    relay = record.get("packet_controller_relay")
    if not isinstance(relay, dict):
        relay = record.get("controller_relay")
    return (
        str(record.get("active_packet_holder") or "") == to_role
        and str(record.get("active_packet_status") or "") == "envelope-relayed"
        and isinstance(relay, dict)
        and relay.get("delivered_via_controller") is True
        and str(relay.get("relayed_to_role") or "") == to_role
        and relay.get("body_was_read_by_controller") is False
        and relay.get("body_was_executed_by_controller") is False
    )

def _ensure_mail_delivery_packet_released(
    project_root: Path,
    run_root: Path,
    ledger: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
    *,
    mail_id: str,
    to_role: str,
    source: str,
) -> dict[str, Any]:
    record = _packet_record_for_mail_delivery(ledger, packet_id=mail_id)
    if record is None:
        raise RouterError(f"mail delivery packet record is missing: {mail_id}")
    if _mail_delivery_packet_released(record, to_role=to_role):
        return {
            "packet_released": True,
            "already_released": True,
            "packet_id": mail_id,
            "packet_envelope_path": record.get("packet_envelope_path"),
        }

    raw_packet_path = str(record.get("packet_envelope_path") or "").strip()
    if not raw_packet_path:
        raise RouterError(f"mail delivery packet envelope path is missing: {mail_id}")
    packet_envelope_path = resolve_project_path(project_root, raw_packet_path)
    if not packet_envelope_path.exists():
        raise RouterError(f"mail delivery packet envelope is missing: {raw_packet_path}")

    envelope = packet_runtime.load_envelope(project_root, packet_envelope_path)
    if str(envelope.get("packet_id") or "") != mail_id:
        raise RouterError(
            f"mail delivery packet envelope mismatch: expected {mail_id}, got {envelope.get('packet_id')!r}"
        )
    if str(envelope.get("to_role") or envelope.get("next_holder") or "") != to_role:
        raise RouterError(
            f"mail delivery packet target mismatch: expected {to_role}, got {envelope.get('to_role')!r}"
        )

    relayed = packet_runtime.controller_relay_envelope(
        project_root,
        envelope=envelope,
        envelope_path=packet_envelope_path,
        controller_agent_id=str(receipt_payload.get("controller_agent_id") or pending_action.get("controller_agent_id") or "controller"),
        received_from_role=str(envelope.get("from_role") or record.get("created_by_role") or "unknown"),
        relayed_to_role=to_role,
        body_was_read_by_controller=receipt_payload.get("controller_read_body") is True
        or receipt_payload.get("body_was_read_by_controller") is True,
        body_was_executed_by_controller=receipt_payload.get("controller_executed_body") is True
        or receipt_payload.get("body_was_executed_by_controller") is True,
        private_role_to_role_delivery_detected=receipt_payload.get("private_role_to_role_delivery_detected") is True,
    )
    action_envelope_path = _mail_delivery_action_envelope_path(project_root, pending_action, receipt_payload)
    if action_envelope_path is not None and action_envelope_path.resolve() != packet_envelope_path.resolve():
        write_json(action_envelope_path, relayed)

    updated_ledger_path = run_root / "packet_ledger.json"
    _raise_if_runtime_write_active(updated_ledger_path)
    updated_ledger = read_daemon_critical_json_if_exists(updated_ledger_path)
    updated_record = _packet_record_for_mail_delivery(updated_ledger, packet_id=mail_id)
    if not _mail_delivery_packet_released(updated_record, to_role=to_role):
        raise RouterError(f"mail delivery packet was not released to {to_role}")
    return {
        "packet_released": True,
        "already_released": False,
        "packet_id": mail_id,
        "packet_envelope_path": project_relative(project_root, packet_envelope_path),
        "source": source,
    }

def _fold_mail_delivery_postcondition(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any] | None = None,
    *,
    source: str,
) -> dict[str, Any]:
    receipt_payload = receipt_payload or {}
    mail_id = str(pending_action.get("mail_id") or receipt_payload.get("mail_id") or receipt_payload.get("packet_id") or "")
    if not mail_id:
        raise RouterError("mail delivery requires a mail_id")
    mail_entry = _mail_sequence_entry(mail_id)
    if mail_entry is None:
        raise RouterError(f"unknown mail in pending action: {mail_id}")
    to_role = str(
        pending_action.get("to_role")
        or receipt_payload.get("delivered_to_role")
        or receipt_payload.get("to_role")
        or mail_entry["to_role"]
    )
    if to_role != mail_entry["to_role"]:
        raise RouterError(f"mail delivery target mismatch for {mail_id}: expected {mail_entry['to_role']}, got {to_role}")
    payload_mail_id = str(receipt_payload.get("mail_id") or receipt_payload.get("packet_id") or "")
    if payload_mail_id and payload_mail_id != mail_id:
        raise RouterError(f"mail delivery receipt mail mismatch: expected {mail_id}, got {payload_mail_id}")
    payload_to_role = str(receipt_payload.get("delivered_to_role") or receipt_payload.get("to_role") or "")
    if payload_to_role and payload_to_role != to_role:
        raise RouterError(f"mail delivery receipt target mismatch: expected {to_role}, got {payload_to_role}")
    if receipt_payload.get("delivery_confirmed") is False:
        raise RouterError(f"mail delivery receipt for {mail_id} did not confirm delivery")

    ledger_path = run_root / "packet_ledger.json"
    _raise_if_runtime_write_active(ledger_path)
    ledger = read_daemon_critical_json_if_exists(ledger_path)
    ledger_mail = ledger.setdefault("mail", [])
    if not isinstance(ledger_mail, list):
        raise RouterError("packet ledger mail field must be a list")
    state_mail = run_state.setdefault("delivered_mail", [])
    if not isinstance(state_mail, list):
        raise RouterError("run state delivered_mail field must be a list")

    existing_ledger_delivery = _find_mail_delivery(ledger_mail, mail_id=mail_id, to_role=to_role)
    existing_state_delivery = _find_mail_delivery(state_mail, mail_id=mail_id, to_role=to_role)
    already_recorded = existing_ledger_delivery is not None and existing_state_delivery is not None
    if not run_state.get("ledger_check_requested") and existing_ledger_delivery is None:
        raise RouterError("mail delivery requires a current packet-ledger check")

    packet_release = _ensure_mail_delivery_packet_released(
        project_root,
        run_root,
        ledger,
        pending_action,
        receipt_payload,
        mail_id=mail_id,
        to_role=to_role,
        source=source,
    )
    _raise_if_runtime_write_active(ledger_path)
    ledger = read_daemon_critical_json_if_exists(ledger_path)
    ledger_mail = ledger.setdefault("mail", [])
    if not isinstance(ledger_mail, list):
        raise RouterError("packet ledger mail field must be a list")
    existing_ledger_delivery = _find_mail_delivery(ledger_mail, mail_id=mail_id, to_role=to_role)
    existing_state_delivery = _find_mail_delivery(state_mail, mail_id=mail_id, to_role=to_role)
    already_recorded = existing_ledger_delivery is not None and existing_state_delivery is not None

    delivery = existing_ledger_delivery or existing_state_delivery or {
        "mail_id": mail_id,
        "delivered_by": str(pending_action.get("delivered_by") or "controller"),
        "to_role": to_role,
        "delivered_at": utc_now(),
    }
    delivery.setdefault("packet_id", mail_id)
    if packet_release.get("packet_envelope_path"):
        delivery.setdefault("packet_envelope_path", packet_release.get("packet_envelope_path"))
    if receipt_payload.get("target_agent_id"):
        delivery.setdefault("target_agent_id", receipt_payload.get("target_agent_id"))
    if receipt_payload.get("delivery_channel"):
        delivery.setdefault("delivery_channel", receipt_payload.get("delivery_channel"))

    ledger_changed = False
    state_changed = False
    if existing_ledger_delivery is None:
        ledger_mail.append(delivery)
        ledger_changed = True
    if existing_state_delivery is None:
        state_mail.append(delivery)
        state_changed = True
    if ledger_changed or state_changed:
        run_state["mail_deliveries"] = max(
            int(run_state.get("mail_deliveries", 0)),
            _count_unique_mail_deliveries(state_mail),
            _count_unique_mail_deliveries(ledger_mail),
        )

    run_state.setdefault("flags", {})[mail_entry["flag"]] = True
    run_state["ledger_check_requested"] = False
    ledger["updated_at"] = utc_now()
    write_json(ledger_path, ledger)
    append_history(
        run_state,
        "router_folded_mail_delivery_postcondition",
        {
            "mail_id": mail_id,
            "to_role": to_role,
            "postcondition": mail_entry["flag"],
            "source": source,
            "already_recorded": already_recorded,
            "ledger_changed": ledger_changed,
            "state_changed": state_changed,
            "packet_release": packet_release,
        },
    )
    return {
        "applied": True,
        "source": source,
        "postcondition": mail_entry["flag"],
        "mail_id": mail_id,
        "to_role": to_role,
        "already_recorded": already_recorded,
        "ledger_changed": ledger_changed,
        "state_changed": state_changed,
        "packet_release": packet_release,
    }

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
        allowed_writes=[item for item in dict.fromkeys(deliverable_paths + [project_relative(project_root, run_state_path(run_root))]) if item],
        extra={
            "postcondition": _pending_action_postcondition(original_action),
            "repair_of_controller_action_id": original_id,
            "repair_target_action_type": repair_target_action_type,
            "repair_attempt": next_attempt,
            "max_repair_attempts": CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS,
            "missing_deliverables": missing_deliverables,
            "required_deliverables": missing_deliverables,
            "runtime_output_contracts": _controller_deliverable_contract(missing_deliverables).get("runtime_contracts", []),
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

_LOCAL_NAMES = set(globals())
