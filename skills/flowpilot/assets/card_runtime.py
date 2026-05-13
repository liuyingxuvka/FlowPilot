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
CARD_BUNDLE_ENVELOPE_SCHEMA = "flowpilot.card_bundle_envelope.v1"
CARD_READ_RECEIPT_SCHEMA = "flowpilot.card_read_receipt.v1"
CARD_ACK_ENVELOPE_SCHEMA = "flowpilot.card_ack_envelope.v1"
CARD_BUNDLE_ACK_ENVELOPE_SCHEMA = "flowpilot.card_bundle_ack_envelope.v1"
CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA = "flowpilot.direct_router_ack_token.v1"
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


def _load_envelope(project_root: Path, envelope_path: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_project_path(project_root, envelope_path)
    envelope = read_json(path)
    if envelope.get("schema_version") != CARD_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card envelope schema mismatch")
    return path, envelope


def _load_bundle_envelope(project_root: Path, envelope_path: str) -> tuple[Path, dict[str, Any]]:
    path = resolve_project_path(project_root, envelope_path)
    envelope = read_json(path)
    if envelope.get("schema_version") != CARD_BUNDLE_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card bundle envelope schema mismatch")
    cards = envelope.get("cards")
    if not isinstance(cards, list) or len(cards) < 2:
        raise CardRuntimeError("card bundle envelope requires at least two cards")
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


def _validate_direct_router_ack_token(
    envelope: dict[str, Any],
    *,
    role: str,
    agent_id: str,
    bundle: bool,
) -> tuple[dict[str, Any], str]:
    token = envelope.get("direct_router_ack_token")
    if not isinstance(token, dict):
        raise CardRuntimeError("card envelope missing direct Router ACK token")
    if token.get("schema_version") != CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA:
        raise CardRuntimeError("direct Router ACK token schema mismatch")
    if token.get("submission_mode") != "direct_to_router":
        raise CardRuntimeError("card ACK token must submit directly to Router")
    if token.get("controller_ack_handoff_allowed") is not False:
        raise CardRuntimeError("card ACK token must forbid Controller ACK handoff")
    expected_kind = "system_card_bundle" if bundle else "system_card"
    if token.get("return_kind") != expected_kind:
        raise CardRuntimeError("card ACK token return kind mismatch")
    checks = {
        "run_id": envelope.get("run_id"),
        "target_role": role,
        "target_agent_id": envelope.get("target_agent_id"),
        "card_return_event": envelope.get("card_return_event"),
        "expected_return_path": envelope.get("expected_return_path"),
    }
    for key, expected in checks.items():
        if expected is not None and token.get(key) != expected:
            raise CardRuntimeError(f"card ACK token {key} mismatch")
    token_agent = token.get("target_agent_id")
    if isinstance(token_agent, str) and token_agent and token_agent != agent_id:
        raise CardRuntimeError("card ACK token target_agent_id mismatch")
    if bundle:
        if token.get("card_bundle_id") != envelope.get("bundle_id"):
            raise CardRuntimeError("card ACK token bundle id mismatch")
        if token.get("card_ids") != envelope.get("card_ids"):
            raise CardRuntimeError("card ACK token bundle card ids mismatch")
        if token.get("expected_receipt_paths") != envelope.get("expected_receipt_paths"):
            raise CardRuntimeError("card ACK token bundle receipt paths mismatch")
    else:
        for key in ("card_id", "delivery_id", "delivery_attempt_id", "expected_receipt_path", "body_hash"):
            expected = envelope.get(key)
            if expected is not None and token.get(key) != expected:
                raise CardRuntimeError(f"card ACK token {key} mismatch")
    token_hash = stable_json_hash(token)
    recorded_hash = envelope.get("direct_router_ack_token_hash")
    if recorded_hash is not None and recorded_hash != token_hash:
        raise CardRuntimeError("direct Router ACK token hash mismatch")
    return token, token_hash


def _validate_ack_direct_router_fields(
    project_root: Path,
    ack_file: Path,
    ack: dict[str, Any],
    *,
    envelope: dict[str, Any] | None,
    bundle: bool,
) -> tuple[dict[str, Any], str]:
    if ack.get("ack_delivery_mode") != "direct_to_router":
        raise CardRuntimeError("card ACK must use direct Router delivery mode")
    if ack.get("submitted_to") != "router":
        raise CardRuntimeError("card ACK must be submitted to Router")
    if ack.get("controller_ack_handoff_used") is not False:
        raise CardRuntimeError("card ACK must not use Controller handoff")
    token = ack.get("direct_router_ack_token")
    if not isinstance(token, dict):
        raise CardRuntimeError("card ACK missing direct Router ACK token")
    if token.get("schema_version") != CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA:
        raise CardRuntimeError("direct Router ACK token schema mismatch")
    token_hash = stable_json_hash(token)
    if ack.get("direct_router_ack_token_hash") != token_hash:
        raise CardRuntimeError("card ACK token hash mismatch")
    if token.get("run_id") != ack.get("run_id"):
        raise CardRuntimeError("card ACK token run mismatch")
    if token.get("target_role") != ack.get("role_key"):
        raise CardRuntimeError("card ACK token role mismatch")
    target_agent = token.get("target_agent_id")
    if isinstance(target_agent, str) and target_agent and target_agent != ack.get("agent_id"):
        raise CardRuntimeError("card ACK token agent mismatch")
    if token.get("card_return_event") != ack.get("card_return_event"):
        raise CardRuntimeError("card ACK token return event mismatch")
    if token.get("expected_return_path") != project_relative(project_root, ack_file):
        raise CardRuntimeError("card ACK token return path mismatch")
    if envelope is not None:
        expected_token, expected_hash = _validate_direct_router_ack_token(
            envelope,
            role=str(ack.get("role_key") or ""),
            agent_id=str(ack.get("agent_id") or ""),
            bundle=bundle,
        )
        if token != expected_token or token_hash != expected_hash:
            raise CardRuntimeError("card ACK token does not match envelope")
    return token, token_hash


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


def open_card_bundle(project_root: Path, *, envelope_path: str, role: str, agent_id: str) -> dict[str, Any]:
    """Open a same-role system-card bundle and write one read receipt per card."""

    project_root = project_root.resolve()
    envelope_file, envelope = _load_bundle_envelope(project_root, envelope_path)
    _validate_target_identity(envelope, role=role, agent_id=agent_id)
    bundle_id = str(envelope.get("bundle_id") or "")
    _validate_card_id(bundle_id)
    opened_at = utc_now()
    opened_cards: list[dict[str, Any]] = []
    ledger_path, ledger = _load_card_ledger(project_root, envelope)
    for card in envelope["cards"]:
        if not isinstance(card, dict):
            raise CardRuntimeError("card bundle member must be an object")
        card_id = str(card.get("card_id") or "")
        _validate_card_id(card_id)
        body_path_raw = card.get("body_path")
        if not isinstance(body_path_raw, str) or not body_path_raw:
            raise CardRuntimeError("card bundle member missing body_path")
        body_path = resolve_project_path(project_root, body_path_raw)
        if not body_path.exists() or not body_path.is_file():
            raise CardRuntimeError(f"card body not found: {body_path_raw}")
        body_hash = sha256_file(body_path)
        if body_hash != card.get("body_hash"):
            raise CardRuntimeError("card bundle member body hash mismatch")
        expected_receipt = card.get("expected_receipt_path")
        if not isinstance(expected_receipt, str) or not expected_receipt:
            raise CardRuntimeError("card bundle member missing expected_receipt_path")
        receipt_path = resolve_project_path(project_root, expected_receipt)
        receipt = {
            "schema_version": CARD_READ_RECEIPT_SCHEMA,
            "run_id": envelope.get("run_id"),
            "resume_tick_id": envelope.get("resume_tick_id"),
            "role_key": role,
            "agent_id": agent_id,
            "card_id": card_id,
            "card_bundle_id": bundle_id,
            "delivery_id": card.get("delivery_id"),
            "delivery_attempt_id": card.get("delivery_attempt_id"),
            "card_envelope_path": project_relative(project_root, envelope_file),
            "card_bundle_envelope_path": project_relative(project_root, envelope_file),
            "card_envelope_hash": stable_json_hash(envelope),
            "card_bundle_envelope_hash": stable_json_hash(envelope),
            "card_body_path": project_relative(project_root, body_path),
            "card_hash": body_hash,
            "manifest_hash": card.get("manifest_hash") or envelope.get("manifest_hash"),
            "opened_at": opened_at,
            "delivered_at": envelope.get("delivered_at"),
            "opened_after_delivery": bool(envelope.get("delivered_at")),
            "body_text_persisted_in_receipt": False,
            "runtime_validates_mechanics_only": True,
            "semantic_understanding_validated": False,
        }
        receipt["receipt_hash"] = stable_json_hash(receipt)
        write_json(receipt_path, receipt)
        ledger.setdefault("read_receipts", []).append(
            {
                "card_id": card_id,
                "card_bundle_id": bundle_id,
                "delivery_id": card.get("delivery_id"),
                "delivery_attempt_id": card.get("delivery_attempt_id"),
                "role_key": role,
                "agent_id": agent_id,
                "receipt_path": project_relative(project_root, receipt_path),
                "receipt_hash": receipt["receipt_hash"],
                "card_hash": body_hash,
                "opened_at": opened_at,
            }
        )
        opened_cards.append(
            {
                "card_id": card_id,
                "body_text": body_path.read_text(encoding="utf-8"),
                "body_text_visibility": "target_role_only",
                "read_receipt_path": project_relative(project_root, receipt_path),
                "read_receipt_hash": receipt["receipt_hash"],
            }
        )
    ledger["updated_at"] = opened_at
    write_json(ledger_path, ledger)
    return {
        "ok": True,
        "bundle_id": bundle_id,
        "role_key": role,
        "agent_id": agent_id,
        "cards": opened_cards,
        "body_text_visibility": "target_role_only",
        "read_receipt_paths": [card["read_receipt_path"] for card in opened_cards],
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
    direct_token, direct_token_hash = _validate_direct_router_ack_token(
        envelope,
        role=role,
        agent_id=agent_id,
        bundle=False,
    )
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
        "ack_delivery_mode": "direct_to_router",
        "submitted_to": "router",
        "controller_ack_handoff_used": False,
        "direct_router_ack_token": direct_token,
        "direct_router_ack_token_hash": direct_token_hash,
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
            "ack_delivery_mode": ack["ack_delivery_mode"],
            "direct_router_ack_token_hash": direct_token_hash,
            "receipt_ref_count": len(receipt_refs),
            "returned_at": returned_at,
        }
    )
    ledger["updated_at"] = returned_at
    write_json(ledger_path, ledger)
    return_path, return_ledger = _load_return_ledger(project_root, envelope)
    completed = return_ledger.setdefault("completed_returns", [])
    ack_rel_path = project_relative(project_root, ack_path)
    _upsert_completed_return_record(
        completed,
        {
            "card_return_event": ack["card_return_event"],
            "status": status,
            "role_key": role,
            "agent_id": agent_id,
            "delivery_id": envelope.get("delivery_id"),
            "delivery_attempt_id": envelope.get("delivery_attempt_id"),
            "ack_path": ack_rel_path,
            "ack_hash": ack["ack_hash"],
            "ack_delivery_mode": ack["ack_delivery_mode"],
            "direct_router_ack_token_hash": direct_token_hash,
            "returned_at": returned_at,
        },
    )
    completed_keys = _resolved_return_keys(completed)
    for pending in return_ledger.setdefault("pending_returns", []):
        if (
            isinstance(pending, dict)
            and pending.get("delivery_attempt_id") == envelope.get("delivery_attempt_id")
            and pending.get("card_return_event") == ack["card_return_event"]
        ):
            _merge_pending_return_ack(
                pending,
                completed_keys=completed_keys,
                next_status="returned",
                ack_path=ack_rel_path,
                ack_hash=ack["ack_hash"],
                returned_at=returned_at,
            )
    return_ledger["updated_at"] = returned_at
    write_json(return_path, return_ledger)
    return {"ok": True, "ack_envelope": ack, "ack_path": ack_rel_path}


def submit_card_bundle_ack(
    project_root: Path,
    *,
    envelope_path: str,
    role: str,
    agent_id: str,
    receipt_paths: list[str] | None = None,
    status: str = "acknowledged",
) -> dict[str, Any]:
    """Write one envelope-only ACK for a same-role card bundle."""

    project_root = project_root.resolve()
    envelope_file, envelope = _load_bundle_envelope(project_root, envelope_path)
    _validate_target_identity(envelope, role=role, agent_id=agent_id)
    expected_return = envelope.get("expected_return_path")
    if not isinstance(expected_return, str) or not expected_return:
        raise CardRuntimeError("card bundle envelope missing expected_return_path")
    direct_token, direct_token_hash = _validate_direct_router_ack_token(
        envelope,
        role=role,
        agent_id=agent_id,
        bundle=True,
    )
    if status not in {"acknowledged", "blocked"}:
        raise CardRuntimeError("card bundle ack status must be acknowledged or blocked")
    cards = [card for card in envelope["cards"] if isinstance(card, dict)]
    if receipt_paths is None:
        receipt_paths = [str(card.get("expected_receipt_path") or "") for card in cards]
    if len(receipt_paths) != len(cards):
        raise CardRuntimeError("card bundle ack requires one receipt path per bundled card")
    cards_by_attempt = {
        (str(card.get("card_id") or ""), str(card.get("delivery_attempt_id") or "")): card
        for card in cards
    }
    receipt_refs: list[dict[str, Any]] = []
    seen_attempts: set[tuple[str, str]] = set()
    for raw_path in receipt_paths:
        if not raw_path:
            raise CardRuntimeError("card bundle ack requires receipt paths")
        receipt_path = resolve_project_path(project_root, raw_path)
        receipt = read_json(receipt_path)
        if receipt.get("schema_version") != CARD_READ_RECEIPT_SCHEMA:
            raise CardRuntimeError("card bundle ack referenced non-card read receipt")
        if receipt.get("run_id") != envelope.get("run_id"):
            raise CardRuntimeError("card bundle ack receipt run mismatch")
        if receipt.get("role_key") != role:
            raise CardRuntimeError("card bundle ack receipt role mismatch")
        if receipt.get("agent_id") != agent_id:
            raise CardRuntimeError("card bundle ack receipt agent mismatch")
        key = (str(receipt.get("card_id") or ""), str(receipt.get("delivery_attempt_id") or ""))
        card = cards_by_attempt.get(key)
        if card is None:
            raise CardRuntimeError("card bundle ack receipt does not match a bundled card")
        if key in seen_attempts:
            raise CardRuntimeError("card bundle ack contains duplicate receipt for a bundled card")
        seen_attempts.add(key)
        if receipt.get("card_hash") != card.get("body_hash"):
            raise CardRuntimeError("card bundle ack receipt hash mismatch")
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
    if seen_attempts != set(cards_by_attempt):
        raise CardRuntimeError("card bundle ack missing a bundled card receipt")
    returned_at = utc_now()
    ack = {
        "schema_version": CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
        "run_id": envelope.get("run_id"),
        "resume_tick_id": envelope.get("resume_tick_id"),
        "role_key": role,
        "agent_id": agent_id,
        "card_return_event": envelope.get("card_return_event") or "card_bundle_ack",
        "status": status,
        "card_bundle_id": envelope.get("bundle_id"),
        "card_bundle_envelope_path": project_relative(project_root, envelope_file),
        "card_bundle_envelope_hash": stable_json_hash(envelope),
        "ack_delivery_mode": "direct_to_router",
        "submitted_to": "router",
        "controller_ack_handoff_used": False,
        "direct_router_ack_token": direct_token,
        "direct_router_ack_token_hash": direct_token_hash,
        "acknowledged_bundle": envelope.get("bundle_id"),
        "acknowledged_envelopes": [envelope.get("bundle_id")],
        "member_card_ids": [card.get("card_id") for card in cards],
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
            "card_bundle_id": envelope.get("bundle_id"),
            "member_card_ids": ack["member_card_ids"],
            "ack_path": project_relative(project_root, ack_path),
            "ack_hash": ack["ack_hash"],
            "ack_delivery_mode": ack["ack_delivery_mode"],
            "direct_router_ack_token_hash": direct_token_hash,
            "receipt_ref_count": len(receipt_refs),
            "returned_at": returned_at,
        }
    )
    ledger["updated_at"] = returned_at
    write_json(ledger_path, ledger)
    return_path, return_ledger = _load_return_ledger(project_root, envelope)
    completed = return_ledger.setdefault("completed_returns", [])
    ack_rel_path = project_relative(project_root, ack_path)
    _upsert_completed_return_record(
        completed,
        {
            "return_kind": "system_card_bundle",
            "card_return_event": ack["card_return_event"],
            "status": status,
            "role_key": role,
            "agent_id": agent_id,
            "card_bundle_id": envelope.get("bundle_id"),
            "member_card_ids": ack["member_card_ids"],
            "ack_path": ack_rel_path,
            "ack_hash": ack["ack_hash"],
            "ack_delivery_mode": ack["ack_delivery_mode"],
            "direct_router_ack_token_hash": direct_token_hash,
            "returned_at": returned_at,
        },
    )
    completed_keys = _resolved_return_keys(completed)
    for pending in return_ledger.setdefault("pending_returns", []):
        if (
            isinstance(pending, dict)
            and pending.get("return_kind") == "system_card_bundle"
            and pending.get("card_bundle_id") == envelope.get("bundle_id")
            and pending.get("card_return_event") == ack["card_return_event"]
        ):
            _merge_pending_return_ack(
                pending,
                completed_keys=completed_keys,
                next_status="returned",
                ack_path=ack_rel_path,
                ack_hash=ack["ack_hash"],
                returned_at=returned_at,
            )
    return_ledger["updated_at"] = returned_at
    write_json(return_path, return_ledger)
    return {"ok": True, "ack_envelope": ack, "ack_path": ack_rel_path}


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
    _token, token_hash = _validate_ack_direct_router_fields(
        project_root,
        ack_file,
        ack,
        envelope=envelope,
        bundle=False,
    )
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
        "ack_delivery_mode": ack.get("ack_delivery_mode"),
        "direct_router_ack_token_hash": token_hash,
        "receipt_ref_count": len(validated_refs),
    }


def validate_card_bundle_ack(project_root: Path, *, ack_path: str, envelope_path: str) -> dict[str, Any]:
    """Validate a bundle ACK and every per-card read receipt it references."""

    project_root = project_root.resolve()
    ack_file = resolve_project_path(project_root, ack_path)
    ack = read_json(ack_file)
    if ack.get("schema_version") != CARD_BUNDLE_ACK_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card bundle ack schema mismatch")
    if ack.get("contains_card_body") is not False:
        raise CardRuntimeError("card bundle ack must not contain card body")
    envelope_file, envelope = _load_bundle_envelope(project_root, envelope_path)
    expected_envelope_path = project_relative(project_root, envelope_file)
    if ack.get("card_bundle_envelope_path") != expected_envelope_path:
        raise CardRuntimeError("card bundle ack envelope path mismatch")
    if ack.get("card_bundle_envelope_hash") != stable_json_hash(envelope):
        raise CardRuntimeError("card bundle ack envelope hash mismatch")
    _token, token_hash = _validate_ack_direct_router_fields(
        project_root,
        ack_file,
        ack,
        envelope=envelope,
        bundle=True,
    )
    refs = ack.get("receipt_refs")
    if not isinstance(refs, list) or not refs:
        raise CardRuntimeError("card bundle ack requires receipt_refs")
    cards = [card for card in envelope["cards"] if isinstance(card, dict)]
    cards_by_attempt = {
        (str(card.get("card_id") or ""), str(card.get("delivery_attempt_id") or "")): card
        for card in cards
    }
    validated_refs: list[dict[str, Any]] = []
    seen_attempts: set[tuple[str, str]] = set()
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("receipt_path"), str):
            raise CardRuntimeError("card bundle ack has invalid receipt ref")
        receipt_path = resolve_project_path(project_root, ref["receipt_path"])
        receipt = read_json(receipt_path)
        if receipt.get("schema_version") != CARD_READ_RECEIPT_SCHEMA:
            raise CardRuntimeError("card bundle ack referenced invalid read receipt")
        if receipt.get("run_id") != ack.get("run_id"):
            raise CardRuntimeError("card bundle ack receipt run mismatch")
        if receipt.get("role_key") != ack.get("role_key"):
            raise CardRuntimeError("card bundle ack receipt role mismatch")
        if receipt.get("agent_id") != ack.get("agent_id"):
            raise CardRuntimeError("card bundle ack receipt agent mismatch")
        key = (str(receipt.get("card_id") or ""), str(receipt.get("delivery_attempt_id") or ""))
        card = cards_by_attempt.get(key)
        if card is None:
            raise CardRuntimeError("card bundle ack receipt does not match a bundled card")
        if key in seen_attempts:
            raise CardRuntimeError("card bundle ack contains duplicate receipt for a bundled card")
        seen_attempts.add(key)
        if receipt.get("card_hash") != card.get("body_hash"):
            raise CardRuntimeError("card bundle ack receipt body hash mismatch")
        validated_refs.append(ref)
    if seen_attempts != set(cards_by_attempt):
        raise CardRuntimeError("card bundle ack missing a bundled card receipt")
    return {
        "ok": True,
        "ack_path": project_relative(project_root, ack_file),
        "ack_hash": ack.get("ack_hash") or stable_json_hash(ack),
        "card_return_event": ack.get("card_return_event"),
        "role_key": ack.get("role_key"),
        "agent_id": ack.get("agent_id"),
        "ack_delivery_mode": ack.get("ack_delivery_mode"),
        "direct_router_ack_token_hash": token_hash,
        "card_bundle_id": ack.get("card_bundle_id"),
        "member_card_ids": [card.get("card_id") for card in cards],
        "receipt_ref_count": len(validated_refs),
    }


def inspect_card_bundle_ack_incomplete(project_root: Path, *, ack_path: str, envelope_path: str) -> dict[str, Any]:
    """Return missing bundle member receipts without treating that as success."""

    project_root = project_root.resolve()
    ack_file = resolve_project_path(project_root, ack_path)
    ack = read_json(ack_file)
    if ack.get("schema_version") != CARD_BUNDLE_ACK_ENVELOPE_SCHEMA:
        raise CardRuntimeError("card bundle ack schema mismatch")
    envelope_file, envelope = _load_bundle_envelope(project_root, envelope_path)
    expected_envelope_path = project_relative(project_root, envelope_file)
    if ack.get("card_bundle_envelope_path") != expected_envelope_path:
        raise CardRuntimeError("card bundle ack envelope path mismatch")
    if ack.get("card_bundle_envelope_hash") != stable_json_hash(envelope):
        raise CardRuntimeError("card bundle ack envelope hash mismatch")
    _validate_ack_direct_router_fields(
        project_root,
        ack_file,
        ack,
        envelope=envelope,
        bundle=True,
    )
    cards = [card for card in envelope["cards"] if isinstance(card, dict)]
    cards_by_attempt = {
        (str(card.get("card_id") or ""), str(card.get("delivery_attempt_id") or "")): card
        for card in cards
    }
    refs = ack.get("receipt_refs")
    if not isinstance(refs, list):
        refs = []
    seen_attempts: set[tuple[str, str]] = set()
    invalid_refs: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("receipt_path"), str):
            invalid_refs.append({"issue": "invalid_ref_shape", "ref": repr(ref)})
            continue
        try:
            receipt_path = resolve_project_path(project_root, ref["receipt_path"])
            receipt = read_json(receipt_path)
        except Exception as exc:
            invalid_refs.append({"issue": "receipt_unreadable", "receipt_path": ref.get("receipt_path"), "error": str(exc)})
            continue
        key = (str(receipt.get("card_id") or ""), str(receipt.get("delivery_attempt_id") or ""))
        card = cards_by_attempt.get(key)
        if card is None:
            invalid_refs.append({"issue": "receipt_not_in_bundle", "receipt_path": ref.get("receipt_path"), "card_id": receipt.get("card_id")})
            continue
        if receipt.get("schema_version") != CARD_READ_RECEIPT_SCHEMA:
            invalid_refs.append({"issue": "invalid_receipt_schema", "receipt_path": ref.get("receipt_path")})
            continue
        if receipt.get("run_id") != ack.get("run_id"):
            invalid_refs.append({"issue": "receipt_run_mismatch", "receipt_path": ref.get("receipt_path")})
            continue
        if receipt.get("role_key") != ack.get("role_key"):
            invalid_refs.append({"issue": "receipt_role_mismatch", "receipt_path": ref.get("receipt_path")})
            continue
        if receipt.get("agent_id") != ack.get("agent_id"):
            invalid_refs.append({"issue": "receipt_agent_mismatch", "receipt_path": ref.get("receipt_path")})
            continue
        if receipt.get("card_hash") != card.get("body_hash"):
            invalid_refs.append({"issue": "receipt_hash_mismatch", "receipt_path": ref.get("receipt_path"), "card_id": receipt.get("card_id")})
            continue
        seen_attempts.add(key)
    missing_keys = set(cards_by_attempt) - seen_attempts
    missing_card_ids = [key[0] for key in sorted(missing_keys)]
    ack_hash = ack.get("ack_hash") or stable_json_hash(ack)
    return {
        "ok": not missing_card_ids and not invalid_refs,
        "incomplete": bool(missing_card_ids) and not invalid_refs,
        "missing_card_ids": missing_card_ids,
        "invalid_receipt_refs": invalid_refs,
        "ack_path": project_relative(project_root, ack_file),
        "ack_hash": ack_hash,
        "card_bundle_id": envelope.get("bundle_id"),
        "card_return_event": ack.get("card_return_event"),
        "role_key": ack.get("role_key"),
        "agent_id": ack.get("agent_id"),
    }
