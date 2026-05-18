"""Envelope loading and identity validation for FlowPilot card runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from card_runtime_io import (
    CARD_BUNDLE_ENVELOPE_SCHEMA,
    CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
    CARD_ENVELOPE_SCHEMA,
    CardRuntimeError,
    read_json,
    resolve_project_path,
    stable_json_hash,
)


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
