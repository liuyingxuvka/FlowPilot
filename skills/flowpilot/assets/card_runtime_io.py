"""Shared I/O, path, and hash helpers for the FlowPilot card runtime."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_CARD_RUNTIME, assert_runtime_gateway_write


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
    assert_runtime_gateway_write(path, GATEWAY_CARD_RUNTIME, operation="card_runtime_write_json")
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
