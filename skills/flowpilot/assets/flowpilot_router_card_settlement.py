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


def _card_ack_clearance_scope(
    delivery_context: dict[str, Any] | None,
    *,
    card_id: str | None,
    target_role: str,
) -> dict[str, Any]:
    context = delivery_context if isinstance(delivery_context, dict) else {}
    stage = context.get("current_stage") if isinstance(context.get("current_stage"), dict) else {}
    current_node_id = stage.get("current_node_id")
    return {
        "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
        "card_id": card_id,
        "target_role": target_role,
        "current_phase": stage.get("current_phase"),
        "card_phase": stage.get("card_phase"),
        "current_node_id": current_node_id,
        "current_route_id": stage.get("current_route_id"),
        "route_version": stage.get("route_version"),
        "boundary_kind": "node" if current_node_id else "route_or_startup",
        "required_before": [
            "gate_or_node_boundary_transition",
            "formal_work_packet_relay_to_target_role",
        ],
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }


def _delivery_identity(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/")


def _controller_delivery_action_matches_pending_return(action: dict[str, Any], record: dict[str, Any], *, bundle: bool) -> bool:
    action_type = str(action.get("action_type") or "")
    if bundle:
        if action_type != "deliver_system_card_bundle":
            return False
        if record.get("card_bundle_id") and action.get("card_bundle_id") == record.get("card_bundle_id"):
            return True
        if _delivery_identity(record.get("card_bundle_envelope_path")) and (
            _delivery_identity(record.get("card_bundle_envelope_path"))
            == _delivery_identity(action.get("card_bundle_envelope_path"))
        ):
            return True
        record_attempts = {
            str(item)
            for item in (record.get("delivery_attempt_ids") or [])
            if str(item)
        }
        action_attempts = {
            str(item)
            for item in (action.get("delivery_attempt_ids") or [])
            if str(item)
        }
        return bool(record_attempts and action_attempts and record_attempts.intersection(action_attempts))

    if action_type != "deliver_system_card":
        return False
    if record.get("delivery_attempt_id") and action.get("delivery_attempt_id") == record.get("delivery_attempt_id"):
        return True
    if record.get("card_id") and action.get("card_id") == record.get("card_id"):
        if record.get("expected_return_path") and action.get("expected_return_path") == record.get("expected_return_path"):
            return True
        if _delivery_identity(record.get("card_envelope_path")) and (
            _delivery_identity(record.get("card_envelope_path")) == _delivery_identity(action.get("card_envelope_path"))
        ):
            return True
    return False


def _original_card_ack_reminder_policy(
    record: dict[str, Any],
    *,
    bundle: bool = False,
    delivery_fact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    envelope_key = "card_bundle_envelope_path" if bundle else "card_envelope_path"
    receipt_key = "expected_receipt_paths" if bundle else "expected_receipt_path"
    target_allowed = True
    if delivery_fact is not None:
        target_allowed = bool(delivery_fact.get("target_role_ack_reminder_allowed"))
    policy = {
        "missing_ack_recovery": "remind_target_role_to_ack_original_committed_card",
        "reminder_target": "original_committed_card_bundle" if bundle else "original_committed_card",
        "original_envelope_path": record.get(envelope_key),
        "original_expected_return_path": record.get("expected_return_path"),
        "original_expected_receipt_path": record.get(receipt_key),
        "duplicate_system_card_delivery_allowed": False,
        "reissue_allowed_only_if_original_invalid_lost_stale_or_role_replaced": True,
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
        "ack_clearance_scope": record.get("ack_clearance_scope"),
        "controller_delivery_fact": delivery_fact or {},
        "target_role_ack_reminder_allowed": target_allowed,
        "controller_delivery_reissue_required_before_target_ack_reminder": not target_allowed,
    }
    if not target_allowed:
        policy.update(
            {
                "missing_ack_recovery": "confirm_or_reissue_controller_delivery_before_target_ack_reminder",
                "reminder_target": "controller_delivery_task",
                "target_role_ack_reminder_allowed": False,
            }
        )
    return policy


def _pending_action_matches_card_return(pending_action: object, pending_return: dict[str, Any]) -> bool:
    if not isinstance(pending_action, dict):
        return False
    if pending_return.get("return_kind") == "system_card_bundle":
        return (
            pending_action.get("card_bundle_id") == pending_return.get("card_bundle_id")
            or pending_action.get("expected_return_path") == pending_return.get("expected_return_path")
        )
    return (
        pending_action.get("delivery_attempt_id") == pending_return.get("delivery_attempt_id")
        or pending_action.get("expected_return_path") == pending_return.get("expected_return_path")
    )
