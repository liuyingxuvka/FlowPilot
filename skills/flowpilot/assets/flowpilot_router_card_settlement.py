"""Pure card-return settlement predicates for the FlowPilot router."""

from __future__ import annotations

from typing import Any


CARD_ACK_COMPLETE_STATUSES = {"acknowledged", "returned", "resolved"}
CARD_BUNDLE_ACK_COMPLETE_STATUSES = CARD_ACK_COMPLETE_STATUSES


def _record_value_for_card(record: dict[str, Any], key: str) -> str:
    nested = record.get("action") if isinstance(record.get("action"), dict) else {}
    return str(record.get(key) or nested.get(key) or "")


def _record_value_for_bundle(record: dict[str, Any], key: str) -> str:
    nested = record.get("action") if isinstance(record.get("action"), dict) else {}
    return str(record.get(key) or nested.get(key) or "")


def _record_matches_card_identity(
    record: dict[str, Any],
    *,
    delivery_attempt_id: str,
    expected_return_path: str,
    card_return_event: str,
    card_id: str,
) -> bool:
    record_attempt = _record_value_for_card(record, "delivery_attempt_id")
    record_return = _record_value_for_card(record, "expected_return_path")
    record_event = _record_value_for_card(record, "card_return_event")
    record_card = _record_value_for_card(record, "card_id")
    return bool(
        (delivery_attempt_id and record_attempt == delivery_attempt_id)
        or (expected_return_path and record_return == expected_return_path)
        or (card_id and record_card == card_id and card_return_event and record_event == card_return_event)
    )


def _record_matches_card_bundle_identity(
    record: dict[str, Any],
    *,
    bundle_id: str,
    expected_return_path: str,
    card_return_event: str,
) -> bool:
    record_bundle = _record_value_for_bundle(record, "card_bundle_id")
    record_return = _record_value_for_bundle(record, "expected_return_path")
    record_event = _record_value_for_bundle(record, "card_return_event")
    return bool(
        (bundle_id and record_bundle == bundle_id)
        or (expected_return_path and record_return == expected_return_path)
        or (card_return_event and record_event == card_return_event and (record_bundle or record_return))
    )


def is_startup_pm_card_bundle_ack_record(
    record: dict[str, Any],
    *,
    pre_review_startup_card_ids: set[str],
) -> bool:
    target_role = str(record.get("target_role") or record.get("to_role") or record.get("role_key") or "")
    if target_role not in {"project_manager", "pm"}:
        return False
    raw_card_ids = record.get("card_ids") or record.get("member_card_ids") or []
    card_ids = {str(card_id) for card_id in raw_card_ids if str(card_id or "").strip()} if isinstance(raw_card_ids, list) else set()
    return bool(card_ids & pre_review_startup_card_ids) or str(record.get("card_return_event") or "") == "pm_card_bundle_ack"
