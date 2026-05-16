"""Controller-facing constants and pure command helpers for FlowPilot router."""

from __future__ import annotations


FOREGROUND_CONTROLLER_STANDBY_DEFAULT_MAX_SECONDS = 300.0
FOREGROUND_CONTROLLER_STANDBY_POLL_SECONDS = 1.0
CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS = 10.0
CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE = "continuous_controller_standby"
WAIT_TARGET_REMINDER_ACTION_TYPE = "send_wait_target_reminder"
PASSIVE_WAIT_STATUS_ACTION_TYPES = frozenset(
    {
        "await_role_decision",
        "await_card_return_event",
        "await_card_bundle_return_event",
        "await_current_scope_reconciliation",
    }
)
WAIT_TARGET_ACK_REMINDER_SECONDS = 180
WAIT_TARGET_ACK_BLOCKER_SECONDS = 600
WAIT_TARGET_REPORT_REMINDER_SECONDS = 600
WAIT_TARGET_UNHEALTHY_LIVENESS_RESULTS = {"missing", "cancelled", "unknown", "unresponsive", "blocked", "lost"}
WAIT_TARGET_NO_OUTPUT_LIVENESS_RESULTS = {
    "no_output",
    "alive_no_output",
    "not_working_no_output",
    "completed",
    "completed_without_expected_event",
}
ROLE_NO_OUTPUT_REISSUE_MAX_ATTEMPTS = 2
CONTROLLER_RECEIPT_STATUSES = {"done", "blocked", "waiting", "skipped"}
CONTROLLER_ACTION_CLOSED_STATUSES = {"done", "blocked", "skipped", "resolved", "superseded"}
CONTROLLER_ACTION_RECEIPT_PRESERVED_STATUSES = {"incomplete", "repair_pending", "resolved", "superseded"}
CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE = "complete_missing_controller_deliverable"
CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS = 2
CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE = "controller_action_receipt_missing_router_postcondition"
CONTROLLER_POSTCONDITION_RECONCILIATION_MAX_ATTEMPTS = CONTROLLER_DELIVERABLE_REPAIR_MAX_ATTEMPTS
CONTROLLER_RUNTIME_HELPER_AGENT_ID = "controller-runtime-helper"


def _format_seconds_for_command(seconds: float) -> str:
    seconds_float = float(seconds)
    if seconds_float.is_integer():
        return str(int(seconds_float))
    return f"{seconds_float:g}"


def _controller_patrol_timer_command(seconds: float = CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS) -> str:
    return (
        "python skills\\flowpilot\\assets\\flowpilot_router.py --root . --json "
        f"controller-patrol-timer --seconds {_format_seconds_for_command(seconds)}"
    )
