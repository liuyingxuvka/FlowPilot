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

__all__ = (
    '_close_waiting_controller_actions_for_external_event',
    '_pending_controller_action_id',
    '_pending_action_postcondition',
    '_receipt_for_pending_controller_action',
    '_pending_action_postcondition_satisfied',
    '_mail_sequence_entry',
    '_mail_role_obligation_contract',
    '_mail_delivery_matches',
    '_find_mail_delivery',
    '_count_unique_mail_deliveries',
    '_packet_record_for_mail_delivery',
    '_mail_delivery_action_envelope_path',
    '_mail_delivery_packet_released',
    '_ensure_mail_delivery_packet_released',
    '_fold_mail_delivery_postcondition',
)

_LOCAL_NAMES = set(globals())
