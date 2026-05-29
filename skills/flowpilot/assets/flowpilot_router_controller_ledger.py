"""Controller ledger path and scheduler projection helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from flowpilot_router_controller_reconciliation import (
    _router_scheduler_idempotency_key,
    _router_scheduler_row_id_for_action,
)
from flowpilot_router_startup_daemon import ROUTER_DAEMON_TICK_SECONDS


CONTROLLER_ACTION_LEDGER_SCHEMA = "flowpilot.controller_action_ledger.v1"
CONTROLLER_ACTION_SCHEMA = "flowpilot.controller_action.v1"
CONTROLLER_RECEIPT_SCHEMA = "flowpilot.controller_receipt.v1"
ROUTER_OWNERSHIP_LEDGER_SCHEMA = "flowpilot.router_ownership_ledger.v1"
ROUTER_SCHEDULER_LEDGER_SCHEMA = "flowpilot.router_scheduler_ledger.v1"
ROUTER_SCHEDULER_ROW_SCHEMA = "flowpilot.router_scheduler_row.v1"


def runtime_dir(run_root: Path) -> Path:
    return run_root / "runtime"


def router_daemon_lock_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "router_daemon.lock"


def router_daemon_status_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "router_daemon_status.json"


def router_daemon_event_log_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "router_daemon_events.jsonl"


def controller_action_ledger_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "controller_action_ledger.json"


def router_scheduler_ledger_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "router_scheduler_ledger.json"


def router_ownership_ledger_path(run_root: Path) -> Path:
    return runtime_dir(run_root) / "router_ownership_ledger.json"


def controller_actions_dir(run_root: Path) -> Path:
    return runtime_dir(run_root) / "controller_actions"


def controller_receipts_dir(run_root: Path) -> Path:
    return runtime_dir(run_root) / "controller_receipts"


def controller_action_path(run_root: Path, action_id: str) -> Path:
    return controller_actions_dir(run_root) / f"{action_id}.json"


def controller_receipt_path(run_root: Path, action_id: str) -> Path:
    return controller_receipts_dir(run_root) / f"{action_id}.json"


def router_scheduler_progress_class(
    action: dict[str, Any],
    *,
    startup_scoped: Callable[[dict[str, Any] | None], bool] | None = None,
) -> str:
    action_type = str(action.get("action_type") or "")
    explicit = str(action.get("scheduler_progress_class") or action.get("router_scheduler_progress_class") or "").strip()
    if explicit:
        return explicit
    if action_type in {"emit_startup_banner", "create_heartbeat_automation", "write_display_surface_status"}:
        return "parallel_obligation"
    if action_type == "sync_display_plan" and startup_scoped is not None and startup_scoped(action):
        return "parallel_obligation"
    if action_type == "start_role_slots":
        return "local_dependency"
    if action_type == "load_controller_core":
        return "phase_handoff"
    if action_type in {
        "open_startup_intake_ui",
        "record_user_request",
        "await_current_scope_reconciliation",
        "await_role_decision",
        "await_card_return_event",
        "await_card_bundle_return_event",
        "handle_control_blocker",
        "run_lifecycle_terminal",
        "write_terminal_summary",
        "controller_no_legal_next_action",
    }:
        return "true_barrier"
    if str(action.get("actor") or "") == "host":
        return "true_barrier"
    if bool(action.get("requires_user")):
        return "true_barrier"
    if bool(action.get("requires_payload")) or bool(action.get("requires_host_spawn")) or bool(action.get("requires_host_automation")):
        return "true_barrier"
    if bool(action.get("requires_user_dialog_display_confirmation")):
        return "true_barrier"
    return "ordinary"


def router_scheduler_barrier_kind(
    action: dict[str, Any],
    *,
    progress_class: str | None = None,
) -> str:
    action_type = str(action.get("action_type") or "")
    progress = progress_class or router_scheduler_progress_class(action)
    if progress in {"parallel_obligation", "local_dependency"}:
        return "none"
    if progress == "phase_handoff":
        return action_type or "phase_handoff"
    if progress == "true_barrier" and str(action.get("actor") or "") == "host":
        return "host_action_barrier"
    if progress == "true_barrier" and (
        bool(action.get("requires_user")) or bool(action.get("requires_payload")) or bool(action.get("requires_host_spawn"))
    ):
        return "external_barrier"
    if progress == "true_barrier" and bool(action.get("requires_host_automation")):
        return "host_automation_barrier"
    if progress == "true_barrier" and bool(action.get("requires_user_dialog_display_confirmation")):
        return "user_display_barrier"
    if action_type in {
        "await_current_scope_reconciliation",
        "await_role_decision",
        "await_card_return_event",
        "await_card_bundle_return_event",
        "handle_control_blocker",
        "run_lifecycle_terminal",
        "write_terminal_summary",
        "controller_no_legal_next_action",
    }:
        return action_type
    if action_type == "check_prompt_manifest":
        return "local_manifest_check"
    if action_type == "load_controller_core":
        return "controller_core_handoff"
    return "none"


def prepare_router_scheduled_action(
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    *,
    scope_for_action: Callable[[dict[str, Any], Path], tuple[str, str]],
    progress_class_for_action: Callable[[dict[str, Any]], str],
    barrier_kind_for_action: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    scope_kind, scope_id = scope_for_action(action, run_root)
    action.setdefault("scope_kind", scope_kind)
    action.setdefault("scope_id", scope_id)
    action.setdefault("idempotency_key", _router_scheduler_idempotency_key(action, scope_kind, scope_id))
    action.setdefault("router_scheduler_row_id", _router_scheduler_row_id_for_action(action))
    action.setdefault("router_scheduler_table", "runtime/router_scheduler_ledger.json")
    action.setdefault("controller_table", "runtime/controller_action_ledger.json")
    action.setdefault("controller_table_contract", "simple_work_board")
    action.setdefault("router_scheduler_progress_class", progress_class_for_action(action))
    action.setdefault("router_scheduler_barrier_kind", barrier_kind_for_action(action))
    action.setdefault("router_daemon_tick_seconds", ROUTER_DAEMON_TICK_SECONDS)
    action.setdefault("run_id", run_state.get("run_id"))
    return action
