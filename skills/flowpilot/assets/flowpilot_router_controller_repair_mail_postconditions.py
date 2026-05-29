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

from flowpilot_router_controller_repair_mail_delivery import _count_unique_mail_deliveries, _ensure_mail_delivery_packet_released, _find_mail_delivery, _mail_sequence_entry

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
    '_fold_mail_delivery_postcondition',
)

_LOCAL_NAMES = set(globals())
