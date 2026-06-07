"""Miscellaneous role-facing controller-action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome


def _apply_deliver_mail(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    return ActionHandlerOutcome(
        result_extra={
            "mail_delivery": router._fold_mail_delivery_postcondition(
                project_root,
                run_root,
                run_state,
                pending,
                payload,
                source="direct_controller_action_mail_delivery_fold",
            )
        }
    )


def _apply_controller_repair_work_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del project_root, run_state
    if pending.get("controller_may_approve_gate") or pending.get("controller_may_mutate_route") or pending.get("controller_may_read_sealed_bodies"):
        raise router.RouterError("controller_repair_work_packet cannot grant gate approval, route mutation, or sealed body access")
    transaction_id = str(pending.get("repair_transaction_id") or "")
    if not transaction_id:
        raise router.RouterError("controller_repair_work_packet requires repair_transaction_id")
    transaction_path = router._repair_transaction_path(run_root, transaction_id)
    transaction = router.read_json_if_exists(transaction_path)
    if transaction.get("schema_version") != router.REPAIR_TRANSACTION_SCHEMA:
        raise router.RouterError("controller_repair_work_packet transaction is missing")
    repair_result = {
        "schema_version": "flowpilot.controller_repair_work_packet_result.v1",
        "status": str((payload or {}).get("status") or "done"),
        "evidence": (payload or {}).get("evidence") if isinstance(payload, dict) else None,
        "recorded_at": router.utc_now(),
        "controller_action_id": pending.get("controller_action_id"),
    }
    transaction["controller_repair_work_packet_result"] = repair_result
    transaction["status"] = "awaiting_recheck"
    transaction["updated_at"] = repair_result["recorded_at"]
    router.write_json(transaction_path, transaction)
    return ActionHandlerOutcome(
        result_extra={
            "repair_transaction_id": transaction_id,
            "controller_repair_work_packet_result": repair_result,
        }
    )


def _apply_write_display_surface_status(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    confirmation = router._display_confirmation_for_action(payload, pending)
    router._write_display_surface_status(project_root, run_root, run_state, confirmation, payload or {})
    router._append_user_dialog_display_ledger(project_root, run_root, confirmation)
    run_state["flags"]["startup_display_status_written"] = True
    return ActionHandlerOutcome()


def _apply_handle_control_blocker(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    router._mark_control_blocker_delivered(project_root, run_root, run_state, pending)
    return ActionHandlerOutcome()


__all__ = (
    "_apply_deliver_mail",
    "_apply_controller_repair_work_packet",
    "_apply_write_display_surface_status",
    "_apply_handle_control_blocker",
)
