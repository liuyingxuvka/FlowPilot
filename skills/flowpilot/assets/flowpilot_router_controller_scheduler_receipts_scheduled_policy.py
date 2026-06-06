"""Finite policy helpers for scheduled Controller receipt reconciliation."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


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


def _scheduler_row_reconciliation_for_entry(
    router: ModuleType,
    run_root: Path,
    entry: dict[str, Any],
) -> dict[str, Any] | None:
    _bind_router(router)
    row_id = str(entry.get("router_scheduler_row_id") or "").strip()
    if not row_id:
        return None
    scheduler = read_json_if_exists(_router_scheduler_ledger_path(run_root))
    for row in scheduler.get("rows", []) if isinstance(scheduler.get("rows"), list) else []:
        if not isinstance(row, dict) or row.get("row_id") != row_id:
            continue
        reconciliation = row.get("reconciliation") if isinstance(row.get("reconciliation"), dict) else {}
        if row.get("router_state") == "reconciled" and reconciliation.get("applied"):
            return dict(reconciliation)
    return None


def _backfill_scheduler_row_from_reconciled_controller_action(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    entry: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    _bind_router(router)
    row_id = str(entry.get("router_scheduler_row_id") or "").strip()
    if not row_id:
        return {"changed": False, "reason": "controller_action_has_no_router_scheduler_row"}
    if not (entry.get("router_reconciliation_status") == "reconciled" or entry.get("router_reconciled_at")):
        return {"changed": False, "reason": "controller_action_not_reconciled"}
    row = router._router_scheduler_row_for_controller_entry(run_root, entry)
    if not row:
        return {"changed": False, "reason": "router_scheduler_row_missing", "row_id": row_id}
    if row.get("router_state") == "reconciled":
        return {"changed": False, "reason": "router_scheduler_row_already_reconciled", "row_id": row_id}
    reconciliation = dict(entry.get("router_reconciliation")) if isinstance(entry.get("router_reconciliation"), dict) else {}
    reconciliation.setdefault("applied", True)
    reconciliation.setdefault("source", source)
    reconciliation["scheduler_backfill_source"] = source
    reconciliation["controller_action_id"] = str(entry.get("action_id") or "")
    reconciliation["controller_action_reconciliation_status"] = entry.get("router_reconciliation_status")
    if entry.get("router_reconciled_at"):
        reconciliation["controller_action_reconciled_at"] = entry.get("router_reconciled_at")
    router._update_router_scheduler_row(
        project_root,
        run_root,
        run_state,
        row_id=row_id,
        router_state="reconciled",
        reconciliation=reconciliation,
    )
    return {"changed": True, "row_id": row_id, "reconciliation": reconciliation}


def _clear_pending_controller_action_if_matches(
    router: ModuleType,
    run_state: dict[str, Any],
    entry: dict[str, Any],
    action: dict[str, Any],
    *,
    action_id: str,
    source: str,
) -> bool:
    _bind_router(router)
    pending = run_state.get("pending_action")
    if not isinstance(pending, dict):
        return False
    row_id = str(entry.get("router_scheduler_row_id") or action.get("router_scheduler_row_id") or "").strip()
    pending_row_id = str(pending.get("router_scheduler_row_id") or "").strip()
    action_type = str(entry.get("action_type") or action.get("action_type") or "").strip()
    pending_action_type = str(pending.get("action_type") or "").strip()
    label = str(entry.get("label") or action.get("label") or "").strip()
    pending_label = str(pending.get("label") or "").strip()
    idempotency_key = str(action.get("idempotency_key") or "").strip()
    pending_idempotency_key = str(pending.get("idempotency_key") or "").strip()
    postcondition = str(_pending_action_postcondition(action) or "").strip()
    pending_postcondition = str(_pending_action_postcondition(pending) or "").strip()
    matches = bool(
        (action_id and str(pending.get("controller_action_id") or "").strip() == action_id)
        or (row_id and pending_row_id == row_id)
        or (idempotency_key and pending_idempotency_key == idempotency_key)
        or (action_type and pending_action_type == action_type and postcondition and pending_postcondition == postcondition)
        or (action_type and pending_action_type == action_type and label and pending_label == label)
    )
    if not matches:
        return False
    run_state["pending_action"] = None
    append_history(
        run_state,
        "router_cleared_resolved_controller_pending_projection",
        {
            "action_type": action_type,
            "controller_action_id": action_id,
            "router_scheduler_row_id": row_id,
            "postcondition": postcondition,
            "source": source,
        },
    )
    return True


def _commit_controller_action_reconciliation(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action_path: Path,
    entry: dict[str, Any],
    *,
    action: dict[str, Any],
    reconciliation: dict[str, Any],
    status: str = "done",
    reconciliation_status: str = "reconciled",
    scheduler_state: str | None = None,
    resolve_blockers: bool = False,
    clear_pending_apply_required: bool = True,
    preserve_reconciled_at: bool = False,
    set_status: bool = True,
    set_completed_at: bool = True,
    now: str | None = None,
) -> str:
    _bind_router(router)
    applied_at = now or utc_now()
    if set_status:
        entry["status"] = status
    if set_completed_at:
        entry["completed_at"] = entry.get("completed_at") or applied_at
    entry["router_reconciliation_status"] = reconciliation_status
    entry["router_reconciled_at"] = (
        entry.get("router_reconciled_at") or applied_at
        if preserve_reconciled_at
        else applied_at
    )
    entry["router_reconciliation"] = reconciliation
    if clear_pending_apply_required:
        entry["router_pending_apply_required"] = False
        if isinstance(entry.get("action"), dict):
            entry["action"]["router_pending_apply_required"] = False
    write_json(action_path, entry)
    row_id = str(entry.get("router_scheduler_row_id") or "")
    if row_id and scheduler_state:
        router._update_router_scheduler_row(
            project_root,
            run_root,
            run_state,
            row_id=row_id,
            router_state=scheduler_state,
            reconciliation=reconciliation,
        )
    if resolve_blockers:
        router._resolve_control_blockers_for_reconciled_controller_action(
            project_root,
            run_root,
            run_state,
            action=action or {"action_type": entry.get("action_type")},
            entry=entry,
            reconciliation=reconciliation,
        )
    return row_id


def _scheduled_controller_receipt_apply_result_case(
    applied: dict[str, Any],
    retry: dict[str, Any] | None = None,
) -> str:
    if applied.get("applied"):
        return "reconciled"
    if applied.get("repair_scheduled") or applied.get("repair_pending"):
        return "repair_pending"
    if applied.get("blocked"):
        return "blocked"
    if retry is None or retry.get("retry_pending"):
        return "retry_pending"
    return "blocked"


def _clear_matching_controller_pending_and_save(
    router: ModuleType,
    run_root: Path,
    run_state: dict[str, Any],
    entry: dict[str, Any],
    action: dict[str, Any],
    *,
    action_id: str,
    source: str,
) -> bool:
    if not router._clear_pending_controller_action_if_matches(
        run_state,
        entry,
        action,
        action_id=action_id,
        source=source,
    ):
        return False
    router.save_run_state(run_root, run_state)
    return True


__all__ = (
    "_scheduler_row_reconciliation_for_entry",
    "_backfill_scheduler_row_from_reconciled_controller_action",
    "_clear_pending_controller_action_if_matches",
    "_commit_controller_action_reconciliation",
    "_scheduled_controller_receipt_apply_result_case",
    "_clear_matching_controller_pending_and_save",
)

_LOCAL_NAMES = set(globals())
