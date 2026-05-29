"""Pending-action resolution helpers for scheduler current-work projection.

Receives the router facade explicitly so controller-ledger and scheduler-row
authority stay under the existing router-owned boundary.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_closure_kernel
from flowpilot_router_errors import RouterError


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _pending_action_has_controller_authority(
    router: ModuleType,
    pending: dict[str, Any],
    controller_ledger: dict[str, Any],
) -> bool:
    _bind_router(router)
    if not isinstance(pending, dict) or not pending:
        return False
    if not isinstance(controller_ledger, dict) or controller_ledger.get("valid_json") is False:
        return True
    action_id = str(pending.get("controller_action_id") or "").strip()
    if not action_id:
        try:
            action_id = router._controller_action_id_for_action(pending)
        except (RouterError, ValueError, TypeError):
            action_id = ""
    if not action_id:
        return True
    actions = controller_ledger.get("actions") if isinstance(controller_ledger.get("actions"), list) else []
    passive_waits = (
        controller_ledger.get("passive_waits")
        if isinstance(controller_ledger.get("passive_waits"), list)
        else []
    )
    for item in actions:
        if not isinstance(item, dict) or str(item.get("action_id") or "") != action_id:
            continue
        return flowpilot_closure_kernel.closure_blocks_progress("controller_action", item)
    for item in passive_waits:
        if not isinstance(item, dict) or str(item.get("action_id") or "") != action_id:
            continue
        return flowpilot_closure_kernel.closure_blocks_progress("controller_passive_wait", item)
    return False


def _scheduler_row_for_pending_action(
    router: ModuleType,
    run_root: Path,
    pending: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(pending.get("router_scheduler_row_id") or "").strip()
    action_id = str(pending.get("controller_action_id") or "").strip()
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    rows = scheduler.get("rows") if isinstance(scheduler.get("rows"), list) else []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row_id and str(row.get("row_id") or "") == row_id:
            return row
        if action_id and str(row.get("controller_action_id") or "") == action_id:
            return row
    return {}


def _pending_action_durable_resolution(
    router: ModuleType,
    run_root: Path,
    pending: dict[str, Any],
    *,
    controller_ledger: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    _bind_router(router)
    if not isinstance(pending, dict) or not pending:
        return None
    if controller_ledger is None:
        controller_ledger = router._controller_action_ledger_summary(run_root)
    action_id = str(pending.get("controller_action_id") or "").strip()
    if not action_id:
        try:
            action_id = router._controller_action_id_for_action(pending)
        except (RouterError, ValueError, TypeError):
            action_id = ""
    if isinstance(controller_ledger, dict) and controller_ledger.get("valid_json") is not False and action_id:
        for key, kind in (("actions", "controller_action"), ("passive_waits", "controller_passive_wait")):
            records = controller_ledger.get(key) if isinstance(controller_ledger.get(key), list) else []
            for record in records:
                if not isinstance(record, dict) or str(record.get("action_id") or "") != action_id:
                    continue
                closure = flowpilot_closure_kernel.classify_closure(kind, record)
                if not closure.blocks_progress:
                    return {
                        "source": f"{key}.{kind}",
                        "controller_action_id": action_id,
                        "status": record.get("status"),
                        "closure_classification": closure.classification,
                        "closure_reason": closure.reason,
                    }
    row = router._scheduler_row_for_pending_action(run_root, pending)
    if row:
        closure = flowpilot_closure_kernel.classify_closure("router_scheduler_row", row)
        if not closure.blocks_progress:
            return {
                "source": "router_scheduler_ledger",
                "router_scheduler_row_id": row.get("row_id"),
                "controller_action_id": row.get("controller_action_id") or action_id or None,
                "router_state": row.get("router_state"),
                "controller_status": row.get("controller_status"),
                "closure_classification": closure.classification,
                "closure_reason": closure.reason,
            }
    return None


def _clear_pending_action_if_durable_wait_resolved(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    _bind_router(router)
    del project_root
    pending = run_state.get("pending_action")
    if not isinstance(pending, dict):
        return {"changed": False}
    resolution = router._pending_action_durable_resolution(run_root, pending)
    if resolution is None:
        return {"changed": False}
    run_state["pending_action"] = None
    append_history(
        run_state,
        "router_cleared_pending_action_after_durable_wait_resolution",
        {
            "source": source,
            "action_type": pending.get("action_type"),
            "label": pending.get("label"),
            "controller_action_id": pending.get("controller_action_id"),
            "router_scheduler_row_id": pending.get("router_scheduler_row_id"),
            "resolution": resolution,
        },
    )
    return {"changed": True, "cleared_pending": True, "resolution": resolution}


def _pending_role_wait_should_use_batch_projection(router: ModuleType, pending: dict[str, Any]) -> bool:
    _bind_router(router)
    if not isinstance(pending, dict) or pending.get("action_type") != "await_role_decision":
        return False
    target = str(pending.get("to_role") or pending.get("waiting_for_role") or pending.get("target_role") or "").strip()
    if target.startswith("worker_") or "," in target:
        return True
    allowed = pending.get("allowed_external_events")
    return bool(isinstance(allowed, list) and any(str(event).startswith("worker_") for event in allowed))


__all__ = (
    "_pending_action_has_controller_authority",
    "_scheduler_row_for_pending_action",
    "_pending_action_durable_resolution",
    "_clear_pending_action_if_durable_wait_resolved",
    "_pending_role_wait_should_use_batch_projection",
)

_LOCAL_NAMES = set(globals())
