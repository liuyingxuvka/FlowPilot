"""Lifecycle request record helpers for FlowPilot router lifecycle requests."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_router_lifecycle_requests_fence as lifecycle_fence
import flowpilot_router_lifecycle_requests_reconciliation as lifecycle_reconciliation


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
    lifecycle_fence._bind_router(router)
    lifecycle_reconciliation._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


def _write_run_lifecycle_request(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
) -> None:
    mode = "cancelled_by_user" if event == "user_requests_run_cancel" else "stopped_by_user"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    cleanup_receipts = payload.get("cleanup_receipts") if isinstance(payload.get("cleanup_receipts"), list) else []
    record = {
        "schema_version": "flowpilot.run_lifecycle.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "requested_by": str(payload.get("requested_by") or "user"),
        "request_event": event,
        "reason": payload.get("reason"),
        "previous_pending_action": previous_pending,
        "active_control_blocker_at_request": active_blocker,
        "cleanup_receipts": cleanup_receipts,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "requested_at": utc_now(),
    }
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    flags = run_state.setdefault("flags", {})
    if mode == "stopped_by_user":
        flags["run_stopped_by_user"] = True
    elif mode == "cancelled_by_user":
        flags["run_cancelled_by_user"] = True
    terminal_fence = lifecycle_fence._write_terminal_lifecycle_fence(project_root, run_root, run_state, mode=mode, event=event)
    reconciliation = lifecycle_reconciliation._reconcile_terminal_lifecycle_authorities(
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
    )
    record["terminal_fence"] = terminal_fence
    record["cleanup_receipts"] = cleanup_receipts + reconciliation["cleanup_receipts"] + [terminal_fence]
    record["reconciliation"] = reconciliation
    write_json(_lifecycle_record_path(run_root), record)
    append_history(run_state, f"run_{mode}", {"event": event, "lifecycle_path": project_relative(project_root, _lifecycle_record_path(run_root))})

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)
    _write_route_state_snapshot(project_root, run_root, run_state, source_event=event)


def _write_protocol_dead_end_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    dead_end_path: Path,
    reason: str | None,
) -> None:
    mode = "protocol_dead_end"
    previous_pending = run_state.get("pending_action")
    active_blocker = run_state.get("active_control_blocker")
    write_json(
        _lifecycle_record_path(run_root),
        {
            "schema_version": "flowpilot.run_lifecycle.v1",
            "run_id": run_state.get("run_id"),
            "status": mode,
            "requested_by": "project_manager",
            "request_event": "protocol_dead_end",
            "reason": reason,
            "protocol_dead_end_path": project_relative(project_root, dead_end_path),
            "previous_pending_action": previous_pending,
            "active_control_blocker_at_request": active_blocker,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "requested_at": utc_now(),
        },
    )
    run_state["status"] = mode
    run_state["phase"] = "terminal"
    run_state["holder"] = "controller"
    run_state["pending_action"] = None
    append_history(
        run_state,
        "run_protocol_dead_end",
        {"protocol_dead_end_path": project_relative(project_root, dead_end_path)},
    )

    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("run_id") == run_state.get("run_id"):
        current["status"] = mode
        current["updated_at"] = utc_now()
        write_json(current_path, current)

    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = mode
            item["updated_at"] = utc_now()
    index["updated_at"] = utc_now()
    if runs:
        index["runs"] = runs
    write_json(index_path, index)


def _run_lifecycle_terminal_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    mode = _terminal_lifecycle_mode(run_state)
    if not mode:
        return None
    if not _terminal_summary_written(project_root, run_state, run_root):
        run_state.setdefault("flags", {})["terminal_summary_card_delivered"] = True
        return _terminal_summary_action(project_root, run_state, run_root, mode=mode)
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(
        action_type="run_lifecycle_terminal",
        actor="controller",
        label=f"controller_observes_{mode}",
        summary="This FlowPilot run is terminal; no further route work is authorized.",
        allowed_reads=[lifecycle_rel, project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        extra={
            "run_lifecycle_status": mode,
            "terminal_for_route": True,
            "controller_may_continue_route_work": False,
            "controller_may_spawn_new_role_work": False,
            "allowed_external_events": ["user_requests_run_stop", "user_requests_run_cancel"],
        },
    )


__all__ = (
    "_write_run_lifecycle_request",
    "_write_protocol_dead_end_lifecycle",
    "_run_lifecycle_terminal_action",
)


_LOCAL_NAMES = set(globals())
