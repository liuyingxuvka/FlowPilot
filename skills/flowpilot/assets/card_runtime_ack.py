"""Single-card open, ACK, and validation operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from card_runtime_envelopes import (
    _load_envelope,
    _validate_direct_router_ack_token,
    _validate_target_identity,
)
from card_runtime_io import (
    CARD_ACK_ENVELOPE_SCHEMA,
    CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
    CARD_READ_RECEIPT_SCHEMA,
    CardRuntimeError,
    project_relative,
    read_json,
    resolve_project_path,
    sha256_file,
    stable_json_hash,
    utc_now,
    write_json,
    _validate_card_id,
)
from card_runtime_ledgers import (
    _load_card_ledger,
    _load_return_ledger,
    _merge_pending_return_ack,
    _resolved_return_keys,
    _upsert_completed_return_record,
)


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
