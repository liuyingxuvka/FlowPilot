"""Continuous standby task payload helpers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_controller_wait_audit import controller_wait_receipt_audit
from flowpilot_router_controller_scheduler_standby_policy import *


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _continuous_standby_watch_label(router: ModuleType, current_wait: dict[str, Any]) -> str:
    _bind_router(router)
    target = str(current_wait.get("waiting_for_role") or current_wait.get("target_role") or "").strip()
    wait_class = str(current_wait.get("wait_class") or "none")
    if target and wait_class in {"ack", "report_result"}:
        return f"{target} {wait_class} wait"
    label = str(current_wait.get("label") or "").strip()
    if label:
        return label
    return "Router daemon"


def _continuous_standby_release_conditions(router: ModuleType) -> list[str]:
    _bind_router(router)
    return [
        "controller_action_ready",
        "formal_return_ready",
        "wait_receipt_audit_control_plane_stuck",
        "wait_target_check_due",
        "wait_target_blocker_required",
        "terminal",
        "user_input_required",
        "daemon_liveness_check_required",
        "daemon_stale_or_missing",
        "explicit_host_stop",
    ]


def _continuous_standby_task_payload(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    current_wait: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    wait_class = str(current_wait.get("wait_class") or "none")
    patrol_command = _controller_patrol_timer_command()
    break_glass = _controller_break_glass_reminder()
    wait_receipt_audit = controller_wait_receipt_audit(project_root, run_root, current_wait)
    wait_policy: dict[str, Any] = {
        "wait_class": wait_class,
        "next_due": current_wait.get("next_due") or {},
        "strict_wait_until_router_release_condition": True,
        "ack_reminder_seconds": WAIT_TARGET_ACK_REMINDER_SECONDS,
        "ack_blocker_seconds": WAIT_TARGET_ACK_BLOCKER_SECONDS,
        "report_reminder_and_liveness_seconds": WAIT_TARGET_REPORT_REMINDER_SECONDS,
        "receipt_audit_before_each_wait_wakeup": True,
    }
    return {
        "task_kind": "continuous_controller_standby",
        "task_type": "foreground_keepalive_waiting_patrol",
        "status": "in_progress",
        "purpose": "Prevent Controller from accidentally exiting the foreground chat while FlowPilot is still running.",
        "required_command": patrol_command,
        "patrol_timer_seconds": CONTROLLER_PATROL_TIMER_DEFAULT_SECONDS,
        "loop_rule": "Run required_command and wait for its output. If it returns continue_patrol, immediately run required_command again and wait for the next output. Starting or restarting the command is not completion.",
        "monitor_source": "existing_router_daemon_monitor",
        "additional_monitor_sources": ["wait_receipt_audit"],
        "watching": router._continuous_standby_watch_label(current_wait),
        "monitor_sources": {
            "router_daemon_status_path": project_relative(project_root, _router_daemon_status_path(run_root)),
            "controller_action_ledger_path": project_relative(project_root, _controller_action_ledger_path(run_root)),
            "controller_receipts_dir": project_relative(project_root, _controller_receipts_dir(run_root)),
            "wait_receipt_audit": "controller-visible formal return metadata only",
        },
        "current_wait": {
            "action_type": current_wait.get("action_type"),
            "label": current_wait.get("label"),
            "waiting_for_role": current_wait.get("waiting_for_role"),
            "wait_class": wait_class,
            "target_role": current_wait.get("target_role"),
            "elapsed_seconds": current_wait.get("elapsed_seconds"),
            "expected_return_path": current_wait.get("expected_return_path"),
            "next_due": current_wait.get("next_due"),
            "wait_receipt_audit": wait_receipt_audit,
        },
        "codex_plan_sync": {
            "required": True,
            "plan_item": f"FlowPilot continuous standby: this is the final standby row when all ordinary Controller rows are complete but FlowPilot is still running. Keep this row in progress as a continuous monitoring duty and foreground anti-exit patrol duty. Run the patrol timer command, wait for its output, and before each continued wait check Controller-visible formal return metadata. Do not read sealed bodies, judge work quality, or treat controller_aside notes as completion proof. If formal return metadata exists but Router has not released the wait or exposed a next step, report the control-plane stuck status. If the command returns continue_patrol, rerun the same command and wait for the next output. Keep quiet patrol internal by default; only update the user when a real user action, blocker, recovery, terminal result, required display, control-plane stuck status, or user-relevant waiting target change occurs. Keep the foreground Controller attached, sync the visible Codex plan from the Controller action ledger and receipts, and when Router exposes new Controller work, update the table and return to top-to-bottom row processing. {break_glass['text']}",
            "plan_status": "in_progress",
            "sync_after_each_controller_row": True,
            "check_for_missed_rows_and_receipts_before_sleep": True,
            "check_formal_return_metadata_before_sleep": True,
            "new_controller_work_returns_to_top_down_processing": True,
        },
        "break_glass_reminder": break_glass,
        "wait_policy": wait_policy,
        "wait_receipt_audit": wait_receipt_audit,
        "quiet_user_reporting_policy": {
            "continue_patrol_user_visible_message_required": False,
            "silent_by_default_for": ["quiet_patrol_continue", "no_new_controller_work", "routine_process_asides", "receipt_or_ledger_housekeeping"],
            "report_when": ["user_action_required", "blocker_or_recovery", "control_plane_stuck_from_wait_receipt_audit", "terminal_stop_or_completion", "user_relevant_wait_target_changed", "required_display_text", "explicit_user_status_request"],
        },
        "do_not_mark_complete_on": ["command_started", "command_restarted", "timer_finished", "monitor_checked_once", "one_monitor_poll", "timeout_still_waiting", "target_role_alive", "target_role_still_working", "controller_aside_claim", "no_new_controller_action_yet", "no_new_controller_work", "continue_patrol"],
        "completion_allowed_only_when": "terminal_return_and_controller_stop_allowed_true",
        "release_conditions": router._continuous_standby_release_conditions(),
        "release_condition_meaning": "switch duty, report stuck control-plane metadata, or process new work; not foreground closure while FlowPilot is running",
        "controller_must_not_exit_foreground": True,
        "foreground_close_allowed_while_flowpilot_running": False,
        "new_controller_work_requires_ledger_update_and_top_down_reentry": True,
        "controller_must_not_use_router_next_as_metronome": True,
        "metadata_only": True,
        "sealed_body_reads_allowed": False,
    }


_LOCAL_NAMES = set(globals())
