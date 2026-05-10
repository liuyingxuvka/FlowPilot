"""Open FlowPilot system-card envelopes and return compact ack envelopes.

This runtime is intentionally mechanical. It proves that a target role opened a
specific card body through the runtime and then returned an envelope-only
acknowledgement that references the read receipts. It does not judge whether
the role understood the card.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CARD_ENVELOPE_SCHEMA = "flowpilot.card_envelope.v1"
CARD_READ_RECEIPT_SCHEMA = "flowpilot.card_read_receipt.v1"
CARD_ACK_ENVELOPE_SCHEMA = "flowpilot.card_ack_envelope.v1"
CARD_LEDGER_SCHEMA = "flowpilot.card_ledger.v1"
RETURN_EVENT_LEDGER_SCHEMA = "flowpilot.return_event_ledger.v1"

CARD_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")


class CardRuntimeError(ValueError):
    """Raised when a card envelope operation violates the control plane."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_json_hash(payload: dict[str, Any]) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise CardRuntimeError(f"expected JSON object: {path}")
    return payload


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise CardRuntimeError(f"path is outside project root: {path}") from exc


def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root / path


def _validate_card_id(card_id: str) -> None:
    if not CARD_ID_RE.match(card_id):
        raise CardRuntimeError(f"invalid card_id: {card_id!r}")


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


def _load_envelope(project_root: Path, envelope_path: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_project_path(project_root, envelope_path)
    envelope = read_json(path)
    if envelope.get("schema_version") != CARD_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card envelope schema mismatch")
    return path, envelope


def _validate_target_identity(envelope: dict[str, Any], *, role: str, agent_id: str) -> None:
    target_role = envelope.get("target_role")
    if target_role != role:
        raise CardRuntimeError(f"card envelope target role mismatch: expected {target_role!r}, got {role!r}")
    if not isinstance(agent_id, str) or not agent_id.strip():
        raise CardRuntimeError("agent_id is required for card runtime")
    target_agent = envelope.get("target_agent_id")
    if isinstance(target_agent, str) and target_agent and target_agent != agent_id:
        raise CardRuntimeError("card envelope target agent mismatch")


def open_card(project_root: Path, *, envelope_path: str, role: str, agent_id: str) -> dict[str, Any]:
    """Open a system-card body through the runtime and write a read receipt."""

    project_root = project_root.resolve()
    envelope_file, envelope = _load_envelope(project_root, envelope_path)
    _validate_target_identity(envelope, role=role, agent_id=agent_id)
    card_id = str(envelope.get("card_id") or "")
    _validate_card_id(card_id)
    body_path_raw = envelope.get("body_path")
    if not isinstance(body_path_raw, str) or not body_path_raw:
        raise CardRuntimeError("card envelope missing body_path")
    body_path = resolve_project_path(project_root, body_path_raw)
    if not body_path.exists() or not body_path.is_file():
        raise CardRuntimeError(f"card body not found: {body_path_raw}")
    body_hash = sha256_file(body_path)
    if body_hash != envelope.get("body_hash"):
        raise CardRuntimeError("card body hash mismatch")
    expected_receipt = envelope.get("expected_receipt_path")
    if not isinstance(expected_receipt, str) or not expected_receipt:
        raise CardRuntimeError("card envelope missing expected_receipt_path")
    receipt_path = resolve_project_path(project_root, expected_receipt)
    opened_at = utc_now()
    receipt = {
        "schema_version": CARD_READ_RECEIPT_SCHEMA,
        "run_id": envelope.get("run_id"),
        "resume_tick_id": envelope.get("resume_tick_id"),
        "role_key": role,
        "agent_id": agent_id,
        "card_id": card_id,
        "delivery_id": envelope.get("delivery_id"),
        "delivery_attempt_id": envelope.get("delivery_attempt_id"),
        "card_envelope_path": project_relative(project_root, envelope_file),
        "card_envelope_hash": stable_json_hash(envelope),
        "card_body_path": project_relative(project_root, body_path),
        "card_hash": body_hash,
        "manifest_hash": envelope.get("manifest_hash"),
        "opened_at": opened_at,
        "delivered_at": envelope.get("delivered_at"),
        "opened_after_delivery": bool(envelope.get("delivered_at")),
        "body_text_persisted_in_receipt": False,
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated": False,
    }
    receipt["receipt_hash"] = stable_json_hash(receipt)
    write_json(receipt_path, receipt)
    ledger_path, ledger = _load_card_ledger(project_root, envelope)
    ledger.setdefault("read_receipts", []).append(
        {
            "card_id": card_id,
            "delivery_id": envelope.get("delivery_id"),
            "delivery_attempt_id": envelope.get("delivery_attempt_id"),
            "role_key": role,
            "agent_id": agent_id,
            "receipt_path": project_relative(project_root, receipt_path),
            "receipt_hash": receipt["receipt_hash"],
            "card_hash": body_hash,
            "opened_at": opened_at,
        }
    )
    ledger["updated_at"] = opened_at
    write_json(ledger_path, ledger)
    return {
        "ok": True,
        "card_id": card_id,
        "role_key": role,
        "agent_id": agent_id,
        "body_text": body_path.read_text(encoding="utf-8"),
        "body_text_visibility": "target_role_only",
        "read_receipt_path": project_relative(project_root, receipt_path),
        "read_receipt_hash": receipt["receipt_hash"],
        "next_required_card_return_event": envelope.get("card_return_event"),
        "expected_return_path": envelope.get("expected_return_path"),
    }


def submit_card_ack(
    project_root: Path,
    *,
    envelope_path: str,
    role: str,
    agent_id: str,
    receipt_paths: list[str] | None = None,
    status: str = "acknowledged",
) -> dict[str, Any]:
    """Write an envelope-only ack/report for a card or card bundle."""

    project_root = project_root.resolve()
    envelope_file, envelope = _load_envelope(project_root, envelope_path)
    _validate_target_identity(envelope, role=role, agent_id=agent_id)
    expected_return = envelope.get("expected_return_path")
    if not isinstance(expected_return, str) or not expected_return:
        raise CardRuntimeError("card envelope missing expected_return_path")
    if status not in {"acknowledged", "blocked"}:
        raise CardRuntimeError("card ack status must be acknowledged or blocked")
    if receipt_paths is None:
        receipt_paths = [str(envelope.get("expected_receipt_path") or "")]
    if not receipt_paths:
        raise CardRuntimeError("card ack requires receipt paths")
    receipt_refs: list[dict[str, Any]] = []
    for raw_path in receipt_paths:
        if not raw_path:
            raise CardRuntimeError("card ack requires receipt paths")
        receipt_path = resolve_project_path(project_root, raw_path)
        receipt = read_json(receipt_path)
        if receipt.get("schema_version") != CARD_READ_RECEIPT_SCHEMA:
            raise CardRuntimeError("card ack referenced non-card read receipt")
        if receipt.get("run_id") != envelope.get("run_id"):
            raise CardRuntimeError("card ack receipt run mismatch")
        if receipt.get("role_key") != role:
            raise CardRuntimeError("card ack receipt role mismatch")
        if receipt.get("agent_id") != agent_id:
            raise CardRuntimeError("card ack receipt agent mismatch")
        if receipt.get("card_hash") != envelope.get("body_hash"):
            raise CardRuntimeError("card ack receipt hash mismatch")
        receipt_refs.append(
            {
                "receipt_path": project_relative(project_root, receipt_path),
                "receipt_hash": receipt.get("receipt_hash") or stable_json_hash(receipt),
                "card_id": receipt.get("card_id"),
                "delivery_id": receipt.get("delivery_id"),
                "delivery_attempt_id": receipt.get("delivery_attempt_id"),
                "card_hash": receipt.get("card_hash"),
                "opened_at": receipt.get("opened_at"),
            }
        )
    returned_at = utc_now()
    ack = {
        "schema_version": CARD_ACK_ENVELOPE_SCHEMA,
        "run_id": envelope.get("run_id"),
        "resume_tick_id": envelope.get("resume_tick_id"),
        "role_key": role,
        "agent_id": agent_id,
        "card_return_event": envelope.get("card_return_event") or "card_ack",
        "status": status,
        "card_envelope_path": project_relative(project_root, envelope_file),
        "card_envelope_hash": stable_json_hash(envelope),
        "delivery_id": envelope.get("delivery_id"),
        "delivery_attempt_id": envelope.get("delivery_attempt_id"),
        "acknowledged_envelopes": [envelope.get("envelope_id")],
        "receipt_refs": receipt_refs,
        "body_visibility": "ack_envelope_only",
        "contains_card_body": False,
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated": False,
        "returned_at": returned_at,
    }
    ack["ack_hash"] = stable_json_hash(ack)
    ack_path = resolve_project_path(project_root, expected_return)
    write_json(ack_path, ack)
    ledger_path, ledger = _load_card_ledger(project_root, envelope)
    ledger.setdefault("ack_envelopes", []).append(
        {
            "card_return_event": ack["card_return_event"],
            "status": status,
            "role_key": role,
            "agent_id": agent_id,
            "delivery_id": envelope.get("delivery_id"),
            "delivery_attempt_id": envelope.get("delivery_attempt_id"),
            "ack_path": project_relative(project_root, ack_path),
            "ack_hash": ack["ack_hash"],
            "receipt_ref_count": len(receipt_refs),
            "returned_at": returned_at,
        }
    )
    ledger["updated_at"] = returned_at
    write_json(ledger_path, ledger)
    return_path, return_ledger = _load_return_ledger(project_root, envelope)
    completed = return_ledger.setdefault("completed_returns", [])
    completed.append(
        {
            "card_return_event": ack["card_return_event"],
            "status": status,
            "role_key": role,
            "agent_id": agent_id,
            "delivery_id": envelope.get("delivery_id"),
            "delivery_attempt_id": envelope.get("delivery_attempt_id"),
            "ack_path": project_relative(project_root, ack_path),
            "ack_hash": ack["ack_hash"],
            "returned_at": returned_at,
        }
    )
    for pending in return_ledger.setdefault("pending_returns", []):
        if (
            isinstance(pending, dict)
            and pending.get("delivery_attempt_id") == envelope.get("delivery_attempt_id")
            and pending.get("card_return_event") == ack["card_return_event"]
        ):
            pending["status"] = "returned"
            pending["ack_path"] = project_relative(project_root, ack_path)
            pending["ack_hash"] = ack["ack_hash"]
            pending["returned_at"] = returned_at
    return_ledger["updated_at"] = returned_at
    write_json(return_path, return_ledger)
    return {"ok": True, "ack_envelope": ack, "ack_path": project_relative(project_root, ack_path)}


def validate_card_ack(project_root: Path, *, ack_path: str, envelope_path: str | None = None) -> dict[str, Any]:
    """Validate an ack envelope and the read receipts it references."""

    project_root = project_root.resolve()
    ack_file = resolve_project_path(project_root, ack_path)
    ack = read_json(ack_file)
    if ack.get("schema_version") != CARD_ACK_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card ack schema mismatch")
    if ack.get("contains_card_body") is not False:
        raise CardRuntimeError("card ack must not contain card body")
    refs = ack.get("receipt_refs")
    if not isinstance(refs, list) or not refs:
        raise CardRuntimeError("card ack requires receipt_refs")
    if envelope_path is not None:
        envelope_file, envelope = _load_envelope(project_root, envelope_path)
        expected_envelope_path = project_relative(project_root, envelope_file)
        if ack.get("card_envelope_path") != expected_envelope_path:
            raise CardRuntimeError("card ack envelope path mismatch")
        if ack.get("card_envelope_hash") != stable_json_hash(envelope):
            raise CardRuntimeError("card ack envelope hash mismatch")
    else:
        envelope = None
    validated_refs: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("receipt_path"), str):
            raise CardRuntimeError("card ack has invalid receipt ref")
        receipt_path = resolve_project_path(project_root, ref["receipt_path"])
        receipt = read_json(receipt_path)
        if receipt.get("schema_version") != CARD_READ_RECEIPT_SCHEMA:
            raise CardRuntimeError("card ack referenced invalid read receipt")
        if receipt.get("run_id") != ack.get("run_id"):
            raise CardRuntimeError("card ack receipt run mismatch")
        if receipt.get("role_key") != ack.get("role_key"):
            raise CardRuntimeError("card ack receipt role mismatch")
        if receipt.get("agent_id") != ack.get("agent_id"):
            raise CardRuntimeError("card ack receipt agent mismatch")
        if envelope is not None and receipt.get("card_hash") != envelope.get("body_hash"):
            raise CardRuntimeError("card ack receipt body hash mismatch")
        validated_refs.append(ref)
    return {
        "ok": True,
        "ack_path": project_relative(project_root, ack_file),
        "ack_hash": ack.get("ack_hash") or stable_json_hash(ack),
        "card_return_event": ack.get("card_return_event"),
        "role_key": ack.get("role_key"),
        "agent_id": ack.get("agent_id"),
        "receipt_ref_count": len(validated_refs),
    }
