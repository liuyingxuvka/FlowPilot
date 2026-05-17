"""Role lifecycle I/O protocol helpers for FlowPilot router."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from flowpilot_router_card_delivery import safe_delivery_component
from flowpilot_router_io import _json_sha256, project_relative, read_json_if_exists, utc_now, write_json


ROLE_IO_PROTOCOL_SCHEMA = "flowpilot.role_io_protocol.v1"
ROLE_IO_PROTOCOL_LEDGER_SCHEMA = "flowpilot.role_io_protocol_ledger.v1"
ROLE_IO_PROTOCOL_INJECTION_RECEIPT_SCHEMA = "flowpilot.role_io_protocol_injection_receipt.v1"


def role_io_protocol_ledger_path(run_root: Path) -> Path:
    return run_root / "role_io_protocol_ledger.json"


def role_io_protocol_receipt_dir(run_root: Path) -> Path:
    return run_root / "runtime_receipts" / "role_io_protocol"


def role_io_protocol_payload() -> dict[str, Any]:
    return {
        "schema_version": ROLE_IO_PROTOCOL_SCHEMA,
        "name": "FlowPilot role lifecycle I/O protocol",
        "scope": "role_lifecycle_base_capability",
        "ordinary_system_card": False,
        "rules": [
            "act only on router/controller envelopes",
            "open system cards, mail, packets, and bundles through runtime",
            "when a card envelope includes card_checkin_instruction, run its receive-card or receive-card-bundle command instead of hand-writing ACK files",
            "write read receipts after runtime open",
            "write reports, decisions, and results to run-scoped files",
            "submit ACKs and role-output envelopes directly to Router through runtime commands",
            "do not send card/body/report body text back to chat",
            "stop with a protocol blocker on wrong role, hash mismatch, stale run, missing envelope, or missing result target",
        ],
    }


def role_io_protocol_hash() -> str:
    return _json_sha256(role_io_protocol_payload())


def empty_role_io_protocol_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": ROLE_IO_PROTOCOL_LEDGER_SCHEMA,
        "run_id": run_id,
        "protocol": role_io_protocol_payload(),
        "protocol_hash": role_io_protocol_hash(),
        "injection_receipts": [],
        "ack_receipts": [],
        "updated_at": utc_now(),
    }


def read_role_io_protocol_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(role_io_protocol_ledger_path(run_root)) or empty_role_io_protocol_ledger(run_id)
    ledger.setdefault("schema_version", ROLE_IO_PROTOCOL_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("protocol", role_io_protocol_payload())
    ledger.setdefault("protocol_hash", role_io_protocol_hash())
    ledger.setdefault("injection_receipts", [])
    ledger.setdefault("ack_receipts", [])
    return ledger


def role_io_receipt_lifecycle_phase(record: dict[str, Any], default_phase: str) -> str:
    if record.get("liveness_decision") == "spawned_replacement_from_current_run_memory":
        return "missing_agent_replacement"
    return default_phase


def append_role_io_protocol_injections(
    project_root: Path,
    run_root: Path,
    run_id: str,
    role_records: list[dict[str, Any]],
    *,
    default_lifecycle_phase: str,
    resume_tick_id: str,
    source_action: str,
) -> list[dict[str, Any]]:
    ledger = read_role_io_protocol_ledger(run_root, run_id)
    protocol_hash = str(ledger.get("protocol_hash") or role_io_protocol_hash())
    existing_keys = {
        (
            item.get("role_key"),
            item.get("agent_id"),
            item.get("resume_tick_id"),
            item.get("protocol_hash"),
            item.get("lifecycle_phase"),
        )
        for item in ledger.get("injection_receipts", [])
        if isinstance(item, dict)
    }
    receipts: list[dict[str, Any]] = []
    for record in role_records:
        role = record.get("role_key")
        agent_id = record.get("agent_id")
        if not isinstance(role, str) or not role:
            continue
        if not isinstance(agent_id, str) or not agent_id.strip():
            continue
        lifecycle_phase = role_io_receipt_lifecycle_phase(record, default_lifecycle_phase)
        key = (role, agent_id.strip(), resume_tick_id, protocol_hash, lifecycle_phase)
        if key in existing_keys:
            continue
        injected_at = utc_now()
        identity_hash = hashlib.sha256(f"{run_id}:{resume_tick_id}:{role}:{agent_id}:{lifecycle_phase}".encode("utf-8")).hexdigest()[:16]
        receipt_id = safe_delivery_component(f"{role}-{lifecycle_phase}-{identity_hash}-role-io")
        receipt_path = role_io_protocol_receipt_dir(run_root) / f"{receipt_id}.json"
        receipt = {
            "schema_version": ROLE_IO_PROTOCOL_INJECTION_RECEIPT_SCHEMA,
            "receipt_id": receipt_id,
            "run_id": run_id,
            "resume_tick_id": resume_tick_id,
            "role_key": role,
            "agent_id": agent_id.strip(),
            "protocol_schema_version": ROLE_IO_PROTOCOL_SCHEMA,
            "protocol_hash": protocol_hash,
            "lifecycle_phase": lifecycle_phase,
            "source_action": source_action,
            "injected_by": "host_router",
            "injection_method": "lifecycle_role_io_protocol",
            "ordinary_system_card_delivery": False,
            "card_body_visible_to_controller": False,
            "requires_card_read_receipt_after_envelope": True,
            "return_to_controller_envelope_only": True,
            "injected_at": injected_at,
        }
        receipt["receipt_hash"] = _json_sha256(receipt)
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(receipt_path, receipt)
        summary = {
            "receipt_id": receipt_id,
            "receipt_path": project_relative(project_root, receipt_path),
            "receipt_hash": receipt["receipt_hash"],
            "run_id": run_id,
            "resume_tick_id": resume_tick_id,
            "role_key": role,
            "agent_id": agent_id.strip(),
            "protocol_hash": protocol_hash,
            "lifecycle_phase": lifecycle_phase,
            "source_action": source_action,
            "injected_at": injected_at,
        }
        ledger.setdefault("injection_receipts", []).append(summary)
        receipts.append(summary)
        existing_keys.add(key)
    ledger["updated_at"] = utc_now()
    write_json(role_io_protocol_ledger_path(run_root), ledger)
    return receipts


def role_io_protocol_receipt_for_agent(
    run_root: Path,
    run_id: str,
    *,
    role: str,
    agent_id: str | None,
    resume_tick_id: str,
) -> dict[str, Any] | None:
    if not isinstance(agent_id, str) or not agent_id.strip():
        return None
    ledger = read_role_io_protocol_ledger(run_root, run_id)
    protocol_hash = str(ledger.get("protocol_hash") or role_io_protocol_hash())
    candidates = list(ledger.get("injection_receipts", [])) + list(ledger.get("ack_receipts", []))
    for item in reversed(candidates):
        if not isinstance(item, dict):
            continue
        if item.get("run_id") != run_id:
            continue
        if item.get("role_key") != role or item.get("agent_id") != agent_id:
            continue
        if item.get("resume_tick_id") != resume_tick_id:
            continue
        if item.get("protocol_hash") != protocol_hash:
            continue
        return item
    return None
