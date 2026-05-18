"""Bundle open, ACK, and validation operations for system cards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from card_runtime_ack import _validate_ack_direct_router_fields
from card_runtime_envelopes import (
    _load_bundle_envelope,
    _validate_direct_router_ack_token,
    _validate_target_identity,
)
from card_runtime_io import (
    CARD_BUNDLE_ACK_ENVELOPE_SCHEMA,
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
