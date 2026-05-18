"""Ledger helpers for FlowPilot card read and return records."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from card_runtime_io import (
    CARD_LEDGER_SCHEMA,
    RETURN_EVENT_LEDGER_SCHEMA,
    CardRuntimeError,
    read_json_if_exists,
    resolve_project_path,
)


def _ledger_paths(project_root: Path, envelope: dict[str, Any]) -> tuple[Path, Path]:
    run_root_raw = envelope.get("run_root")
    if not isinstance(run_root_raw, str) or not run_root_raw:
        raise CardRuntimeError("card envelope missing run_root")
    run_root = resolve_project_path(project_root, run_root_raw)
    return run_root / "card_ledger.json", run_root / "return_event_ledger.json"


def _load_card_ledger(project_root: Path, envelope: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path, _return_path = _ledger_paths(project_root, envelope)
    ledger = read_json_if_exists(path) or {
        "schema_version": CARD_LEDGER_SCHEMA,
        "run_id": envelope.get("run_id"),
        "deliveries": [],
        "read_receipts": [],
        "ack_envelopes": [],
    }
    ledger.setdefault("schema_version", CARD_LEDGER_SCHEMA)
    ledger.setdefault("run_id", envelope.get("run_id"))
    ledger.setdefault("deliveries", [])
    ledger.setdefault("read_receipts", [])
    ledger.setdefault("ack_envelopes", [])
    return path, ledger


def _load_return_ledger(project_root: Path, envelope: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    _card_path, path = _ledger_paths(project_root, envelope)
    ledger = read_json_if_exists(path) or {
        "schema_version": RETURN_EVENT_LEDGER_SCHEMA,
        "run_id": envelope.get("run_id"),
        "pending_returns": [],
        "completed_returns": [],
    }
    ledger.setdefault("schema_version", RETURN_EVENT_LEDGER_SCHEMA)
    ledger.setdefault("run_id", envelope.get("run_id"))
    ledger.setdefault("pending_returns", [])
    ledger.setdefault("completed_returns", [])
    return path, ledger


def _return_record_identity(record: dict[str, Any]) -> tuple[str, str, str]:
    return_kind = str(record.get("return_kind") or "system_card")
    identity = str(record.get("card_bundle_id") or record.get("delivery_attempt_id") or "")
    event_name = str(record.get("card_return_event") or "")
    return return_kind, identity, event_name


def _resolved_return_keys(completed_returns: list[Any]) -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for item in completed_returns:
        if not isinstance(item, dict) or item.get("status") != "resolved":
            continue
        identity = _return_record_identity(item)
        if identity[1] and identity[2]:
            keys.add(identity)
    return keys


def _return_has_terminal_proof(record: dict[str, Any], completed_keys: set[tuple[str, str, str]]) -> bool:
    identity = _return_record_identity(record)
    return bool(record.get("resolved_at")) or record.get("status") == "resolved" or identity in completed_keys


def _record_terminal_replay_audit(record: dict[str, Any], *, ack_path: str, ack_hash: str, returned_at: str, status: str) -> None:
    audit = record.setdefault("terminal_replay_ack", {})
    if not isinstance(audit, dict):
        audit = {}
        record["terminal_replay_ack"] = audit
    audit["count"] = int(audit.get("count") or 0) + 1
    audit["last_ack_path"] = ack_path
    audit["last_ack_hash"] = ack_hash
    audit["last_status"] = status
    audit["last_returned_at"] = returned_at


def _upsert_completed_return_record(completed_returns: list[Any], record: dict[str, Any]) -> None:
    identity = _return_record_identity(record)
    for item in completed_returns:
        if not isinstance(item, dict) or _return_record_identity(item) != identity:
            continue
        if item.get("status") == "resolved":
            _record_terminal_replay_audit(
                item,
                ack_path=str(record.get("ack_path") or ""),
                ack_hash=str(record.get("ack_hash") or ""),
                returned_at=str(record.get("returned_at") or ""),
                status=str(record.get("status") or ""),
            )
            return
        item.update(record)
        item["return_replay_count"] = int(item.get("return_replay_count") or 0) + 1
        return
    completed_returns.append(record)


def _merge_pending_return_ack(
    pending: dict[str, Any],
    *,
    completed_keys: set[tuple[str, str, str]],
    next_status: str,
    ack_path: str,
    ack_hash: str,
    returned_at: str,
) -> None:
    if _return_has_terminal_proof(pending, completed_keys):
        _record_terminal_replay_audit(
            pending,
            ack_path=ack_path,
            ack_hash=ack_hash,
            returned_at=returned_at,
            status=next_status,
        )
        return
    pending["status"] = next_status
    pending["ack_path"] = ack_path
    pending["ack_hash"] = ack_hash
    pending["returned_at"] = returned_at
