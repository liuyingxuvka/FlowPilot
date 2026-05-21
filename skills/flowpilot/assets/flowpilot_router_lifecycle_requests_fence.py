"""Terminal lifecycle fence helpers for FlowPilot router lifecycle requests."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


TERMINAL_CONTROLLER_ACTION_TYPES = {"write_terminal_summary", "run_lifecycle_terminal"}


def _controller_action_is_terminal_cleanup(entry: dict[str, Any]) -> bool:
    action_type = str(entry.get("action_type") or "")
    action = entry.get("action") if isinstance(entry.get("action"), dict) else {}
    return (
        action_type in TERMINAL_CONTROLLER_ACTION_TYPES
        or str(action.get("action_type") or "") in TERMINAL_CONTROLLER_ACTION_TYPES
        or bool(entry.get("terminal_for_route"))
        or bool(action.get("terminal_for_route"))
    )


def _supersede_nonterminal_controller_work_for_terminal(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    fenced_at: str,
) -> dict[str, Any]:
    action_dir = _controller_actions_dir(run_root)
    action_receipts: list[dict[str, Any]] = []
    if action_dir.exists():
        for action_path in sorted(action_dir.glob("*.json")):
            entry = read_json_if_exists(action_path)
            if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
                continue
            previous_status = str(entry.get("status") or "pending")
            if previous_status in CONTROLLER_ACTION_CLOSED_STATUSES:
                continue
            if _controller_action_is_terminal_cleanup(entry):
                continue
            entry["status"] = "superseded"
            entry["superseded_by"] = event
            entry["terminal_lifecycle_status"] = mode
            entry["controller_may_execute"] = False
            entry["updated_at"] = fenced_at
            write_json(action_path, entry)
            action_receipts.append(
                {
                    "authority": "controller_action",
                    "path": project_relative(project_root, action_path),
                    "action_id": entry.get("action_id"),
                    "action_type": entry.get("action_type"),
                    "previous_status": previous_status,
                    "status": "superseded",
                }
            )

    scheduler_receipts: list[dict[str, Any]] = []
    scheduler_path = _router_scheduler_ledger_path(run_root)
    if scheduler_path.exists():
        ledger = _read_router_scheduler_ledger(project_root, run_root, run_state)
        changed = False
        rows: list[dict[str, Any]] = []
        for row in ledger.get("rows", []):
            if not isinstance(row, dict):
                continue
            action_type = str(row.get("action_type") or "")
            router_state = str(row.get("router_state") or "")
            controller_status = str(row.get("controller_status") or "")
            if (
                action_type not in TERMINAL_CONTROLLER_ACTION_TYPES
                and (
                    router_state in {"queued", "waiting", "receipt_done"}
                    or controller_status in {"pending", "waiting", "in_progress", "blocked", "incomplete", "repair_pending"}
                )
            ):
                row["router_state"] = "superseded"
                row["controller_status"] = "superseded"
                row["superseded_by"] = event
                row["terminal_lifecycle_status"] = mode
                row["updated_at"] = fenced_at
                changed = True
                scheduler_receipts.append(
                    {
                        "authority": "router_scheduler_row",
                        "row_id": row.get("row_id"),
                        "controller_action_id": row.get("controller_action_id"),
                        "action_type": action_type,
                        "status": "superseded",
                    }
                )
            rows.append(row)
        if changed:
            ledger["rows"] = rows
            _write_router_scheduler_ledger(project_root, run_root, run_state, ledger)

    bootstrap_receipt: dict[str, Any] | None = None
    bootstrap = load_bootstrap_state(project_root, create_if_missing=False)
    pending = bootstrap.get("pending_action") if isinstance(bootstrap.get("pending_action"), dict) else None
    if pending and str(pending.get("action_type") or "") not in TERMINAL_CONTROLLER_ACTION_TYPES:
        bootstrap_receipt = {
            "authority": "startup_bootstrap",
            "previous_action_type": pending.get("action_type"),
            "previous_label": pending.get("label"),
            "status": "superseded",
        }
        bootstrap["pending_action"] = None
        append_history(
            bootstrap,
            "startup_bootstrap_pending_action_superseded_by_terminal_lifecycle",
            {
                "event": event,
                "terminal_lifecycle_status": mode,
                "previous_action_type": pending.get("action_type"),
            },
        )
        save_bootstrap_state(project_root, bootstrap)

    _rebuild_controller_action_ledger(project_root, run_root, run_state)
    receipts: list[dict[str, Any]] = [*action_receipts, *scheduler_receipts]
    if bootstrap_receipt:
        receipts.append(bootstrap_receipt)
    return {
        "authority": "terminal_controller_work_fence",
        "path": project_relative(project_root, _controller_action_ledger_path(run_root)),
        "superseded_count": len(receipts),
        "receipts": receipts,
    }


def _write_terminal_lifecycle_fence(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    fenced_at = utc_now()
    run_state["daemon_mode_enabled"] = False
    flags = run_state.setdefault("flags", {})
    flags["terminal_daemon_fence_written"] = True
    flags["terminal_projection_refreshed"] = True
    flags["terminal_next_step_cleared"] = True
    daemon_status = _mark_router_daemon_terminal(
        project_root,
        run_root,
        run_state,
        reason=f"{event}_terminal_fence",
    )
    controller_fence = {
        "authority": "terminal_controller_work_fence",
        "status": "pending",
        "superseded_count": 0,
        "receipts": [],
    }
    fence = {
        "schema_version": "flowpilot.terminal_lifecycle_fence.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "fenced_at": fenced_at,
        "daemon_mode_enabled": False,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "terminal_cleanup_actions_allowed": sorted(TERMINAL_CONTROLLER_ACTION_TYPES),
        "controller_work_fence": controller_fence,
        "router_daemon_status": daemon_status,
    }
    fence_path = run_root / "lifecycle" / "terminal_fence.json"
    write_json(fence_path, fence)
    try:
        controller_fence = _supersede_nonterminal_controller_work_for_terminal(
            project_root,
            run_root,
            run_state,
            mode=mode,
            event=event,
            fenced_at=fenced_at,
        )
    except Exception as exc:
        controller_fence = {
            "authority": "terminal_controller_work_fence",
            "status": "best_effort_failed",
            "superseded_count": 0,
            "receipts": [],
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        append_history(
            run_state,
            "terminal_controller_work_fence_best_effort_failed",
            {
                "event": event,
                "terminal_lifecycle_status": mode,
                "error_type": type(exc).__name__,
            },
        )
    fence["controller_work_fence"] = controller_fence
    write_json(fence_path, fence)
    append_history(
        run_state,
        "terminal_lifecycle_fence_written",
        {
            "event": event,
            "terminal_lifecycle_status": mode,
            "terminal_fence_path": project_relative(project_root, fence_path),
            "superseded_count": controller_fence["superseded_count"],
        },
    )
    return {**fence, "terminal_fence_path": project_relative(project_root, fence_path)}


__all__ = (
    "TERMINAL_CONTROLLER_ACTION_TYPES",
    "_controller_action_is_terminal_cleanup",
    "_supersede_nonterminal_controller_work_for_terminal",
    "_write_terminal_lifecycle_fence",
)


_LOCAL_NAMES = set(globals())
