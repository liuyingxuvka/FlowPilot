"""Shared lifecycle-closure classification for FlowPilot runtime records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


CLOSURE_OPEN = "open"
CLOSURE_CLOSED_SUCCESS = "closed_success"
CLOSURE_CLOSED_TERMINAL = "closed_terminal"
CLOSURE_REPAIR_REQUIRED = "repair_required"
CLOSURE_INVALID_OR_INCOMPLETE = "invalid_or_incomplete"
CLOSURE_UNKNOWN_NEEDS_RECHECK = "unknown_needs_recheck"

NONBLOCKING_CLASSIFICATIONS = frozenset(
    {CLOSURE_CLOSED_SUCCESS, CLOSURE_CLOSED_TERMINAL}
)

CONTROLLER_SUCCESS_STATUSES = frozenset({"done", "resolved"})
CONTROLLER_TERMINAL_STATUSES = frozenset(
    {"blocked", "skipped", "superseded", "closed", "cancelled", "canceled"}
)
CONTROLLER_OPEN_STATUSES = frozenset(
    {"pending", "in_progress", "waiting", "queued", "receipt_done"}
)

PM_ROLE_TARGET_BUSY_STATUSES = frozenset({"open", "packet_created", "packet_relayed"})
PM_ROLE_PM_BUSY_STATUSES = frozenset({"result_returned", "result_relayed_to_pm"})
PM_ROLE_CLOSED_STATUSES = frozenset(
    {
        "absorbed",
        "pm_absorbed",
        "reviewed",
        "review_blocked",
        "canceled",
        "cancelled",
        "superseded",
        "closed",
    }
)

PACKET_HOLDER_CLOSED_STATUSES = frozenset(
    {
        "done",
        "complete",
        "completed",
        "cancelled",
        "canceled",
        "closed",
        "stopped_by_user",
        "result-returned",
        "result_returned",
        "result-relayed-to-pm",
        "result_relayed_to_pm",
        "result-absorbed",
        "result_absorbed",
        "absorbed",
        "pm_absorbed",
        "reviewed",
        "superseded",
    }
)

ACK_OPEN_STATUSES = frozenset(
    {
        "",
        "pending",
        "awaiting_return",
        "reminded",
        "returned",
        "acknowledged",
    }
)
ACK_INCOMPLETE_STATUSES = frozenset(
    {"bundle_ack_incomplete", "invalid_ack_pending_explicit_check"}
)

CONTROL_BLOCKER_CLOSED_STATUSES = frozenset({"resolved", "superseded", "closed"})


@dataclass(frozen=True, slots=True)
class ClosureDecision:
    classification: str
    blocks_progress: bool
    reason: str


def _text(value: Any) -> str:
    return str(value or "").strip()


def _normalized(value: Any) -> str:
    return _text(value).lower()


def _action(record: dict[str, Any]) -> dict[str, Any]:
    action = record.get("action")
    return action if isinstance(action, dict) else {}


def _has_router_reconciliation(record: dict[str, Any]) -> bool:
    status = _normalized(record.get("router_reconciliation_status"))
    if status == "reconciled" or status.startswith("superseded"):
        return True
    if _text(record.get("router_reconciled_at")):
        return True
    reconciliation = record.get("router_reconciliation")
    return isinstance(reconciliation, dict) and bool(reconciliation)


def _decision(classification: str, reason: str) -> ClosureDecision:
    return ClosureDecision(
        classification=classification,
        blocks_progress=classification not in NONBLOCKING_CLASSIFICATIONS,
        reason=reason,
    )


def classify_controller_action(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    if not status:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "controller_action_status_missing")
    reconciled = _has_router_reconciliation(record)
    if status in CONTROLLER_SUCCESS_STATUSES:
        if reconciled:
            return _decision(CLOSURE_CLOSED_SUCCESS, "controller_action_closed_and_reconciled")
        return _decision(CLOSURE_REPAIR_REQUIRED, "controller_action_closed_without_router_reconciliation")
    if status in CONTROLLER_TERMINAL_STATUSES:
        if reconciled or status in {"superseded", "closed", "cancelled", "canceled"}:
            return _decision(CLOSURE_CLOSED_TERMINAL, "controller_action_terminal")
        return _decision(CLOSURE_REPAIR_REQUIRED, "controller_action_terminal_without_router_reconciliation")
    if status in CONTROLLER_OPEN_STATUSES:
        return _decision(CLOSURE_OPEN, "controller_action_open")
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "controller_action_status_unknown")


def classify_controller_passive_wait(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    if _has_router_reconciliation(record):
        return _decision(CLOSURE_CLOSED_SUCCESS, "passive_wait_reconciled")
    if status in CONTROLLER_SUCCESS_STATUSES:
        return _decision(CLOSURE_CLOSED_SUCCESS, "passive_wait_closed")
    if status in CONTROLLER_TERMINAL_STATUSES:
        return _decision(CLOSURE_CLOSED_TERMINAL, "passive_wait_terminal")
    if status in {"", *CONTROLLER_OPEN_STATUSES}:
        return _decision(CLOSURE_OPEN, "passive_wait_open")
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "passive_wait_status_unknown")


def classify_pm_role_work_target(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    if status in PM_ROLE_TARGET_BUSY_STATUSES:
        return _decision(CLOSURE_OPEN, "pm_role_target_work_open")
    if status in PM_ROLE_PM_BUSY_STATUSES or status in PM_ROLE_CLOSED_STATUSES:
        return _decision(CLOSURE_CLOSED_SUCCESS, "pm_role_target_no_longer_busy")
    if not status:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "pm_role_work_status_missing")
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "pm_role_target_status_unknown")


def classify_pm_role_work_pm(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    if status in PM_ROLE_PM_BUSY_STATUSES:
        return _decision(CLOSURE_OPEN, "pm_role_work_waiting_for_pm_disposition")
    if status in PM_ROLE_TARGET_BUSY_STATUSES or status in PM_ROLE_CLOSED_STATUSES:
        return _decision(CLOSURE_CLOSED_SUCCESS, "pm_role_work_not_waiting_for_pm")
    if not status:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "pm_role_work_status_missing")
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "pm_role_pm_status_unknown")


def classify_packet_holder(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("active_packet_status") or record.get("status"))
    if not status:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "packet_status_missing")
    if status in PACKET_HOLDER_CLOSED_STATUSES:
        return _decision(CLOSURE_CLOSED_SUCCESS, "packet_holder_obligation_closed")
    return _decision(CLOSURE_OPEN, "packet_holder_obligation_open")


def classify_ack_return(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    has_resolution_evidence = bool(
        _text(record.get("resolved_at"))
        or _text(record.get("ack_path"))
        or _text(record.get("ack_hash"))
    )
    if status == "resolved":
        if has_resolution_evidence:
            return _decision(CLOSURE_CLOSED_SUCCESS, "ack_return_resolved")
        return _decision(CLOSURE_REPAIR_REQUIRED, "ack_return_resolved_without_evidence")
    if status in ACK_INCOMPLETE_STATUSES:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "ack_return_incomplete")
    if status in ACK_OPEN_STATUSES:
        return _decision(CLOSURE_OPEN, "ack_return_open")
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "ack_return_status_unknown")


def classify_control_blocker(record: dict[str, Any]) -> ClosureDecision:
    status = _normalized(record.get("status"))
    if status in CONTROL_BLOCKER_CLOSED_STATUSES:
        return _decision(CLOSURE_CLOSED_TERMINAL, "control_blocker_closed")
    if not status:
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "control_blocker_status_missing")
    return _decision(CLOSURE_OPEN, "control_blocker_open")


def classify_closure(record_kind: str, record: dict[str, Any] | None) -> ClosureDecision:
    if not isinstance(record, dict):
        return _decision(CLOSURE_INVALID_OR_INCOMPLETE, "record_missing")
    kind = _normalized(record_kind)
    if kind == "controller_action":
        return classify_controller_action(record)
    if kind == "controller_passive_wait":
        return classify_controller_passive_wait(record)
    if kind == "pm_role_work_target":
        return classify_pm_role_work_target(record)
    if kind == "pm_role_work_pm":
        return classify_pm_role_work_pm(record)
    if kind == "packet_holder":
        return classify_packet_holder(record)
    if kind == "ack_return":
        return classify_ack_return(record)
    if kind == "control_blocker":
        return classify_control_blocker(record)
    return _decision(CLOSURE_UNKNOWN_NEEDS_RECHECK, "record_kind_unknown")


def closure_blocks_progress(record_kind: str, record: dict[str, Any] | None) -> bool:
    return classify_closure(record_kind, record).blocks_progress


__all__ = (
    "CLOSURE_OPEN",
    "CLOSURE_CLOSED_SUCCESS",
    "CLOSURE_CLOSED_TERMINAL",
    "CLOSURE_REPAIR_REQUIRED",
    "CLOSURE_INVALID_OR_INCOMPLETE",
    "CLOSURE_UNKNOWN_NEEDS_RECHECK",
    "ClosureDecision",
    "classify_closure",
    "closure_blocks_progress",
    "classify_ack_return",
    "classify_controller_action",
    "classify_controller_passive_wait",
    "classify_control_blocker",
    "classify_packet_holder",
    "classify_pm_role_work_pm",
    "classify_pm_role_work_target",
)
