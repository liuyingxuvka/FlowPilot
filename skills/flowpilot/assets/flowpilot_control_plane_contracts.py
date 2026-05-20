"""Shared FlowPilot control-plane contract helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


CONTROL_BLOCKER_DELIVERY_POSTCONDITION_PREFIX = "control_blocker_delivered"
CONTROL_BLOCKER_IDENTITY_FIELDS = (
    "blocker_id",
    "blocker_artifact_path",
    "policy_row_id",
    "handling_lane",
    "repair_transaction_id",
    "sealed_repair_packet_hash",
)
BASE_ACTION_IDENTITY_FIELDS = (
    "action_type",
    "scope_kind",
    "scope_id",
    "label",
    "card_id",
    "card_bundle_id",
    "delivery_attempt_id",
    "mail_id",
    "expected_return_path",
    "postcondition",
    "projection_hash",
    "next_card_id",
)
PENDING_WAIT_IDENTITY_FIELDS = (
    "action_type",
    "label",
    "to_role",
    "waiting_for_role",
    "expected_return_path",
    "controller_action_id",
)


def _nonempty(value: Any) -> bool:
    return value not in (None, "", [])


def control_blocker_delivery_postcondition(blocker_id: Any) -> str:
    blocker = str(blocker_id or "").strip()
    if not blocker:
        return CONTROL_BLOCKER_DELIVERY_POSTCONDITION_PREFIX
    return f"{CONTROL_BLOCKER_DELIVERY_POSTCONDITION_PREFIX}:{blocker}"


def control_plane_action_identity_extra_fields(action: dict[str, Any]) -> tuple[str, ...]:
    action_type = str(action.get("action_type") or "")
    if action_type == "handle_control_blocker":
        return CONTROL_BLOCKER_IDENTITY_FIELDS
    return ()


def control_plane_scheduler_identity_extras(action: dict[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    for field in control_plane_action_identity_extra_fields(action):
        value = action.get(field)
        if _nonempty(value):
            extras[field] = value
    return extras


def control_plane_action_identity_parts(action: dict[str, Any]) -> dict[str, Any]:
    parts: dict[str, Any] = {}
    for field in BASE_ACTION_IDENTITY_FIELDS + control_plane_action_identity_extra_fields(action):
        value = action.get(field)
        if _nonempty(value):
            parts[field] = value
    idempotency_key = action.get("idempotency_key")
    if _nonempty(idempotency_key):
        parts["idempotency_key"] = idempotency_key
    if str(action.get("action_type") or "") == "sync_display_plan":
        parts["projection_hash"] = action.get("projection_hash")
    return parts


def control_plane_action_identity_fingerprint(action: dict[str, Any] | None) -> str:
    if not isinstance(action, dict):
        return ""
    payload = control_plane_action_identity_parts(action)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def control_plane_pending_wait_identity_parts(wait: dict[str, Any]) -> dict[str, Any]:
    parts: dict[str, Any] = {}
    for field in PENDING_WAIT_IDENTITY_FIELDS:
        value = wait.get(field)
        if _nonempty(value):
            parts[field] = value
    return parts


def control_plane_pending_wait_same_identity(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return control_plane_pending_wait_identity_parts(first) == control_plane_pending_wait_identity_parts(second)


def control_plane_completion_class_override(
    action: dict[str, Any],
    *,
    postcondition: str = "",
) -> dict[str, str] | None:
    if str(action.get("action_type") or "") != "handle_control_blocker":
        return None
    resolved_postcondition = postcondition or control_blocker_delivery_postcondition(action.get("blocker_id"))
    return {
        "kind": "stateful_host_postcondition",
        "artifact_kind": "control_blocker_delivery",
        "postcondition": resolved_postcondition,
    }


def control_plane_envelope_is_hash_bound(envelope: dict[str, Any]) -> bool:
    relay = envelope.get("controller_relay")
    if isinstance(relay, dict) and relay.get("envelope_hash"):
        return True
    startup_release = envelope.get("router_startup_release")
    return isinstance(startup_release, dict) and bool(startup_release.get("envelope_hash"))


__all__ = (
    "CONTROL_BLOCKER_DELIVERY_POSTCONDITION_PREFIX",
    "CONTROL_BLOCKER_IDENTITY_FIELDS",
    "PENDING_WAIT_IDENTITY_FIELDS",
    "control_blocker_delivery_postcondition",
    "control_plane_action_identity_extra_fields",
    "control_plane_scheduler_identity_extras",
    "control_plane_action_identity_parts",
    "control_plane_action_identity_fingerprint",
    "control_plane_pending_wait_identity_parts",
    "control_plane_pending_wait_same_identity",
    "control_plane_completion_class_override",
    "control_plane_envelope_is_hash_bound",
)
