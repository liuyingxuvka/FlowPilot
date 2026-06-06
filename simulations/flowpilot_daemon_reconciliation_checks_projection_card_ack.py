"""Card-ack handoff live-projection findings for daemon reconciliation checks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_daemon_reconciliation_checks_projection_common import (
    ACK_COMPLETE_STATUSES,
    PROJECT_ROOT,
    TERMINAL_ACTION_STATES,
    TERMINAL_ROUTER_ROW_STATES,
    _bundle_identity,
    _computed_actions_after,
    _mail_ledger_has_user_intake,
    _read_json,
    _record_matches_bundle,
    _user_intake_delivery_action_exists,
    _user_intake_packet_summary,
    _user_intake_router_released,
)

def _card_ack_handoff_projection_findings(
    run_root: Path,
    row_by_id: dict[str, dict[str, Any]],
    actions: list[dict[str, Any]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    return_ledger_path = run_root / "return_event_ledger.json"
    packet_ledger_path = run_root / "packet_ledger.json"
    router_state_path = run_root / "router_state.json"
    return_ledger = _read_json(return_ledger_path) if return_ledger_path.exists() else {}
    packet_ledger = _read_json(packet_ledger_path) if packet_ledger_path.exists() else {}
    router_state = _read_json(router_state_path) if router_state_path.exists() else {}

    completed_returns = [
        item for item in return_ledger.get("completed_returns", [])
        if isinstance(item, dict)
        and item.get("return_kind") == "system_card_bundle"
        and str(item.get("status") or "") in ACK_COMPLETE_STATUSES
    ]
    pending_resolved = [
        item for item in return_ledger.get("pending_returns", [])
        if isinstance(item, dict)
        and item.get("return_kind") == "system_card_bundle"
        and (item.get("status") == "resolved" or bool(item.get("resolved_at")))
    ]

    resolved_by_bundle: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in pending_resolved + completed_returns:
        key = _bundle_identity(item)
        if key[0] or key[1]:
            resolved_by_bundle[key] = item

    if not resolved_by_bundle:
        return findings

    user_intake_packet = _user_intake_packet_summary(packet_ledger)
    user_intake_released = _user_intake_router_released(user_intake_packet, packet_ledger)
    user_intake_delivery_exists = _user_intake_delivery_action_exists(actions)
    user_intake_mail_folded = _mail_ledger_has_user_intake(packet_ledger)
    flags = router_state.get("flags") if isinstance(router_state.get("flags"), dict) else {}
    startup_runtime_ready_for_pm_intake = (
        flags.get("startup_mechanical_audit_written") is True
        and flags.get("startup_display_status_written") is True
    )

    for key, resolved in sorted(resolved_by_bundle.items()):
        bundle_id, expected_return_path, event = key
        completed_for_key = [
            item for item in completed_returns
            if _record_matches_bundle(item, bundle_id, expected_return_path, event)
        ]
        pending_for_key = [
            item for item in pending_resolved
            if _record_matches_bundle(item, bundle_id, expected_return_path, event)
        ]
        if completed_for_key and any(item.get("status") != "resolved" for item in completed_for_key):
            findings.append(
                {
                    "id": "card_bundle_ack_completion_status_not_normalized",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "completed_statuses": sorted({str(item.get("status") or "") for item in completed_for_key}),
                    "pending_statuses": sorted({str(item.get("status") or "") for item in pending_for_key}),
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                }
            )

        matching_wait_actions = [
            action for action in actions
            if action.get("action_type") in {"await_card_bundle_return_event", "check_card_bundle_return_event"}
            and _record_matches_bundle(action, bundle_id, expected_return_path, event)
        ]
        for action in matching_wait_actions:
            row = row_by_id.get(str(action.get("router_scheduler_row_id") or ""))
            row_state = str(row.get("router_state") or "") if row else ""
            action_done = str(action.get("status") or "") in TERMINAL_ACTION_STATES
            action_reconciled = str(action.get("router_reconciliation_status") or "") in TERMINAL_ACTION_STATES
            row_reconciled = row_state in TERMINAL_ROUTER_ROW_STATES
            if not (action_done and action_reconciled and row_reconciled):
                findings.append(
                    {
                        "id": "card_bundle_ack_resolved_wait_row_still_open",
                        "action_type": action.get("action_type"),
                        "action_id": action.get("action_id"),
                        "action_status": action.get("status"),
                        "router_reconciliation_status": action.get("router_reconciliation_status"),
                        "router_scheduler_row_id": action.get("router_scheduler_row_id"),
                        "row_state": row_state or None,
                        "card_bundle_id": bundle_id,
                        "card_return_event": event,
                        "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    }
                )

        if (
            user_intake_packet
            and user_intake_packet.get("packet_holder") == "controller"
            and user_intake_packet.get("packet_status") == "packet-with-controller"
        ):
            findings.append(
                {
                    "id": "startup_user_intake_owned_by_controller",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_packet": user_intake_packet,
                }
            )
        if user_intake_delivery_exists and not startup_runtime_ready_for_pm_intake:
            findings.append(
                {
                    "id": "pm_ack_resolved_queued_controller_user_intake_delivery_before_startup_runtime_ready",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_delivery_action_exists": user_intake_delivery_exists,
                }
            )
        if (
            user_intake_packet
            and str(user_intake_packet.get("to_role") or user_intake_packet.get("next_holder") or "") == "project_manager"
            and not user_intake_released
            and startup_runtime_ready_for_pm_intake
        ):
            findings.append(
                {
                    "id": "startup_runtime_ready_user_intake_not_controller_relayed",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_packet": user_intake_packet,
                    "user_intake_mail_folded": user_intake_mail_folded,
                    "user_intake_controller_relayed": user_intake_released,
                }
            )
        if (
            user_intake_packet
            and user_intake_packet.get("router_release_recorded") is True
            and not startup_runtime_ready_for_pm_intake
        ):
            findings.append(
                {
                    "id": "pm_ack_resolved_user_intake_router_released_before_startup_runtime_ready",
                    "card_bundle_id": bundle_id,
                    "card_return_event": event,
                    "ack_path": resolved.get("ack_path") or resolved.get("expected_return_path"),
                    "user_intake_packet": user_intake_packet,
                }
            )

    return findings
