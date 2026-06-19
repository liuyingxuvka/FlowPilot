"""Foreground Controller standby state policy helpers."""

from __future__ import annotations

from typing import Any

_STANDBY_CONTINUE_STATES = frozenset({"waiting_for_role", "daemon_alive_no_controller_action"})
_STANDBY_WAIT_TARGET_READY_STATES = frozenset(
    {
        "wait_target_check_due",
        "wait_target_blocker_required",
        "wait_target_reissue_required",
    }
)
_STANDBY_FOREGROUND_RETURN_STATES = (
    frozenset({"terminal", "user_input_required", "daemon_liveness_check_required"})
    | _STANDBY_WAIT_TARGET_READY_STATES
)
_STANDBY_FOREGROUND_MODE_BY_STATE = {
    "controller_action_ready": "process_controller_action",
    "wait_target_check_due": "process_wait_target_check",
    "wait_target_blocker_required": "record_wait_target_blocker",
    "wait_target_reissue_required": "record_wait_target_no_output_reissue",
    "waiting_for_role": "watch_router_daemon",
    "daemon_alive_no_controller_action": "watch_router_daemon",
    "user_input_required": "return_for_user_input",
    "daemon_liveness_check_required": "check_liveness",
    "terminal": "terminal_return",
}


def _foreground_standby_state(
    *,
    terminal: bool,
    user_required: bool,
    daemon_liveness_check_required: bool,
    pending_action_ids: list[str],
    current_wait: dict[str, Any],
) -> str:
    if terminal:
        return "terminal"
    if user_required:
        return "user_input_required"
    if daemon_liveness_check_required:
        return "daemon_liveness_check_required"
    if pending_action_ids:
        return "controller_action_ready"
    if (current_wait.get("blocker") or {}).get("required"):
        return "wait_target_blocker_required"
    if (current_wait.get("reissue") or {}).get("required"):
        return "wait_target_reissue_required"
    if (
        (current_wait.get("reminder") or {}).get("due")
        or (current_wait.get("controller_local_self_audit") or {}).get("required")
    ):
        return "wait_target_check_due"
    if current_wait.get("waiting_for_role") or current_wait.get("action_type") == "await_role_decision":
        return "waiting_for_role"
    return "daemon_alive_no_controller_action"


def _foreground_standby_policy(standby_state: str) -> dict[str, Any]:
    controller_must_continue_standby = standby_state in _STANDBY_CONTINUE_STATES
    return {
        "controller_must_continue_standby": controller_must_continue_standby,
        "controller_must_process_pending_action": standby_state == "controller_action_ready",
        "controller_stop_allowed": standby_state == "terminal",
        "wait_target_action_ready": standby_state in _STANDBY_WAIT_TARGET_READY_STATES,
        "foreground_turn_return_allowed": standby_state in _STANDBY_FOREGROUND_RETURN_STATES,
        "controller_patrol_required": controller_must_continue_standby,
        "foreground_required_mode": _STANDBY_FOREGROUND_MODE_BY_STATE.get(standby_state, "terminal_return"),
    }


__all__ = (
    "_foreground_standby_state",
    "_foreground_standby_policy",
)
