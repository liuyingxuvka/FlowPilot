"""Apply/event/foreground folding for FlowPilot controller runtime."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
import flowpilot_router_action_handlers
import flowpilot_router_controller_runtime_next as runtime_next
from flowpilot_router_errors import RouterError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *

_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    runtime_next._bind_router(router)
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


def apply_controller_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("run state is missing")
    _ensure_daemon_runtime_state(project_root, run_root, run_state, lifecycle_status="controller_apply")
    _reconcile_controller_receipts(
        project_root,
        run_root,
        run_state,
        scheduler_fold_owner="foreground_receipt",
    )
    pending = _ensure_pending(run_state, action_type)
    result_extra: dict[str, Any] = {}
    handled_action = flowpilot_router_action_handlers.apply_registered_action(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        pending,
        action_type,
        payload,
    )
    if handled_action is not None:
        if handled_action.early_return is not None:
            return handled_action.early_return
        result_extra.update(handled_action.result_extra)
    else:
        raise RouterError(f"unknown controller action: {action_type}")
    append_history(run_state, str(pending["label"]), {"action_type": action_type})
    _maybe_write_controller_receipt_for_pending(
        project_root,
        run_root,
        run_state,
        pending,
        status="done",
        payload={"applied": action_type},
    )
    next_pending_after_apply = run_state.pop("_pending_action_after_current_apply", None)
    run_state["pending_action"] = next_pending_after_apply if isinstance(next_pending_after_apply, dict) else None
    if action_type == "write_terminal_summary":
        _mark_router_daemon_terminal(project_root, run_root, run_state, reason="terminal_summary_written")
        save_run_state(run_root, run_state)
        result = {"ok": True, "applied": action_type}
        result.update(result_extra)
        return result
    _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_controller_action:{action_type}")
    _sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason=f"after_controller_action:{action_type}",
        update_display=action_type != "sync_display_plan",
    )
    save_run_state(run_root, run_state)
    result = {"ok": True, "applied": action_type}
    result.update(result_extra)
    if action_type == "sync_display_plan":
        result.update(_display_plan_sync_payload(project_root, run_root, run_state))
        if "user_dialog_display_confirmation" in run_state["visible_plan_sync"]:
            result["user_dialog_display_confirmation"] = run_state["visible_plan_sync"]["user_dialog_display_confirmation"]
    return result


def record_external_event(
    project_root: Path,
    event: str,
    payload: dict[str, Any] | None = None,
    *,
    envelope_path: str | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    try:
        return _record_external_event_unchecked(
            project_root,
            event,
            payload,
            envelope_path=envelope_path,
            envelope_hash=envelope_hash,
        )
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.record_external_event",
            error_message=str(exc),
            event=event,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def apply_action(project_root: Path, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == action_type:
        return apply_bootloader_action(project_root, action_type, payload)
    try:
        return apply_controller_action(project_root, action_type, payload)
    except (RouterError, packet_runtime.PacketRuntimeError) as exc:
        existing_blocker = getattr(exc, "control_blocker", None)
        if isinstance(existing_blocker, dict):
            raise
        blocker = _try_write_control_blocker_for_exception(
            project_root,
            source="router.apply_controller_action",
            error_message=str(exc),
            action_type=action_type,
            payload=payload,
        )
        if blocker:
            raise RouterError(str(exc), control_blocker=blocker) from exc
        raise


def run_until_wait(project_root: Path, *, max_steps: int = 50, new_invocation: bool = False) -> dict[str, Any]:
    if max_steps < 1:
        raise RouterError("run-until-wait requires max_steps >= 1")
    applied_actions: list[dict[str, Any]] = []

    def preserve_completed_actions(exc: RouterLedgerWriteInProgress) -> None:
        exc.completed_folded_actions = list(applied_actions)

    start_new = new_invocation
    for _ in range(max_steps):
        try:
            action = runtime_next.next_action(project_root, new_invocation=start_new)
        except RouterLedgerWriteInProgress as exc:
            preserve_completed_actions(exc)
            raise
        start_new = False
        action_type = str(action.get("action_type") or "")
        action_crosses_boundary = (
            action_type not in SAFE_RUN_UNTIL_WAIT_ACTION_TYPES
            or bool(action.get("requires_user"))
            or bool(action.get("requires_payload"))
            or bool(action.get("requires_user_dialog_display_confirmation"))
            or bool(action.get("requires_host_role_binding"))
            or bool(action.get("requires_host_automation"))
            or bool(action.get("card_id"))
        )
        if action_crosses_boundary:
            result = dict(action)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "requires_user_host_or_role_boundary"
            return result
        try:
            applied = apply_action(project_root, action_type, {})
        except RouterLedgerWriteInProgress as exc:
            preserve_completed_actions(exc)
            raise
        applied_actions.append({"action_type": action_type, "result": applied})
        if applied.get("waiting") or applied.get("terminal"):
            result = dict(applied)
            result["folded_command"] = "run-until-wait"
            result["folded_applied_count"] = len(applied_actions)
            result["folded_applied_actions"] = applied_actions
            result["folded_stop_reason"] = "terminal_or_waiting_action_applied"
            return result
    raise RouterError("run-until-wait reached max_steps before a wait boundary")


def record_controller_action_receipt(
    project_root: Path,
    *,
    action_id: str,
    status: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_root = project_root.resolve()
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError("controller receipt requires an active FlowPilot run")
    receipt = _write_controller_receipt(
        project_root,
        run_root,
        run_state,
        action_id=action_id,
        status=status,
        payload=payload,
    )
    _reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    status_payload = _write_router_daemon_status(
        project_root,
        run_root,
        run_state,
        lifecycle_status="controller_receipt_recorded",
        current_action=run_state.get("pending_action") if isinstance(run_state.get("pending_action"), dict) else None,
    )
    save_run_state(run_root, run_state)
    return {
        "ok": True,
        "command": "controller-receipt",
        "receipt": receipt,
        "daemon_status": status_payload,
        "controller_action_ledger": _controller_action_ledger_summary(run_root),
    }


__all__ = (
    "apply_controller_action",
    "record_external_event",
    "apply_action",
    "run_until_wait",
    "record_controller_action_receipt",
)

_LOCAL_NAMES = set(globals())
