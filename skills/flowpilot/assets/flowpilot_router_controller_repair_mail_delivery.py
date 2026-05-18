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

__all__ = (
    '_mail_sequence_entry',
    '_mail_role_obligation_contract',
    '_mail_delivery_matches',
    '_find_mail_delivery',
    '_count_unique_mail_deliveries',
    '_packet_record_for_mail_delivery',
    '_mail_delivery_action_envelope_path',
    '_mail_delivery_packet_released',
    '_ensure_mail_delivery_packet_released',
)

_LOCAL_NAMES = set(globals())
