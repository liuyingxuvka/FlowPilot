"""Controller boundary projection helpers for deliverable repair."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_protocol_catalog import *
from flowpilot_router_controller_repair_deliverable_contracts import _controller_boundary_required_deliverable

_DEFAULT_SENTINEL = object()
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

OWNER_MODULE = "flowpilot_router_controller_repair"

def _sync_controller_boundary_confirmation_from_artifact(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
    receipt_payload: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        missing = [_controller_boundary_required_deliverable(project_root, run_root)]
        _record_router_ownership_entry(
            project_root,
            run_root,
            run_state,
            action_id=str(pending_action.get("controller_action_id") or ""),
            action_type=str(pending_action.get("action_type") or ""),
            router_state="router_reclaim_pending",
            workflow_owner="router",
            postcondition="controller_role_confirmed",
            source=source,
            receipt_path=str(pending_action.get("controller_receipt_path") or ""),
            details={
                "reason": "controller_boundary_confirmation_missing_or_invalid",
                "missing_deliverables": missing,
                "controller_receipt_payload": receipt_payload,
            },
        )
        return {
            "applied": False,
            "reason": "controller_boundary_confirmation_missing_or_invalid",
            "action_type": pending_action.get("action_type"),
            "repairable": True,
            "missing_deliverables": missing,
        }
    confirmation = run_state.get("controller_boundary_confirmation")
    if not isinstance(confirmation, dict) or not confirmation.get("path"):
        confirmation = {
            "path": project_relative(project_root, context["path"]),
            "sha256": context["sha256"],
            "controller_core_path": context["confirmation"].get("controller_core_path"),
            "controller_core_sha256": context["confirmation"].get("controller_core_sha256"),
            "controller_policy_sha256": context["confirmation"].get("controller_policy_sha256"),
        }
    confirmation.update(
        {
            "runtime_channel": "role_output_runtime",
            "output_type": CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE,
            "output_contract_id": CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID,
            "role_output_envelope": context.get("role_output_envelope"),
            "role_output_runtime_receipt_path": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("path")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
            "role_output_runtime_receipt_hash": (
                context.get("role_output_envelope", {}).get("runtime_receipt_ref", {}).get("hash")
                if isinstance(context.get("role_output_envelope"), dict)
                else None
            ),
        }
    )
    run_state.setdefault("flags", {})["controller_role_confirmed"] = True
    run_state.setdefault("flags", {})["controller_role_confirmed_from_router_core"] = True
    run_state.setdefault("flags", {})["controller_boundary_confirmation_written"] = True
    run_state["controller_boundary_confirmation"] = confirmation
    if not any(
        isinstance(item, dict) and item.get("event") == "controller_role_confirmed_from_router_core"
        for item in run_state.get("events", [])
    ):
        run_state.setdefault("events", []).append(
            {
                "event": "controller_role_confirmed_from_router_core",
                "summary": "Controller confirmed the Router-delivered controller.core boundary.",
                "payload": confirmation,
                "recorded_at": utc_now(),
            }
        )
    entry = _record_router_ownership_entry(
        project_root,
        run_root,
        run_state,
        action_id=str(pending_action.get("controller_action_id") or ""),
        action_type=str(pending_action.get("action_type") or ""),
        router_state="router_reclaimed",
        workflow_owner="router",
        postcondition="controller_role_confirmed",
        source=source,
        receipt_path=str(pending_action.get("controller_receipt_path") or ""),
        artifact_refs={
            "controller_boundary_confirmation_path": project_relative(project_root, context["path"]),
            "controller_boundary_confirmation_hash": context["sha256"],
        },
        details={"controller_receipt_payload": receipt_payload},
    )
    return {
        "applied": True,
        "postcondition": "controller_role_confirmed",
        "source": "router_owned_controller_boundary_confirmation_reclaim",
        "router_ownership_entry_id": entry.get("entry_id"),
    }

def _controller_boundary_flags_synced(run_state: dict[str, Any]) -> bool:
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    return bool(
        flags.get("controller_role_confirmed")
        and flags.get("controller_role_confirmed_from_router_core")
        and flags.get("controller_boundary_confirmation_written")
    )

def _router_scheduler_row_for_controller_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._router_scheduler_row_for_controller_entry(_bound_router(), run_root, entry)

def _done_controller_receipt_for_entry(run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_controller_scheduler._done_controller_receipt_for_entry(_bound_router(), run_root, entry)

def _reconcile_controller_boundary_confirmation_projection(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    context = _controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        return {"changed": False, "reason": "controller_boundary_confirmation_missing_or_invalid"}
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return {"changed": False, "reason": "controller_action_dir_missing"}

    flags_were_synced = _controller_boundary_flags_synced(run_state)
    reconciled_actions: list[str] = []
    pending_cleared = False
    last_projection: dict[str, Any] | None = None

    for action_path in sorted(action_dir.glob("*.json")):
        entry = _read_json_for_runtime_scan(action_path)
        if entry is None:
            continue
        if entry.get("schema_version") != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get("action_type") != "confirm_controller_core_boundary":
            continue
        if entry.get("status") != "done":
            continue
        receipt = _done_controller_receipt_for_entry(run_root, entry)
        if not receipt:
            continue
        action = dict(entry.get("action") if isinstance(entry.get("action"), dict) else {})
        action_id = str(entry.get("action_id") or action.get("controller_action_id") or "").strip()
        if not action_id:
            continue
        action.setdefault("action_type", "confirm_controller_core_boundary")
        action.setdefault("controller_action_id", action_id)
        action.setdefault("postcondition", "controller_role_confirmed")
        if entry.get("router_scheduler_row_id"):
            action.setdefault("router_scheduler_row_id", entry.get("router_scheduler_row_id"))
        action.setdefault(
            "controller_receipt_path",
            project_relative(project_root, _controller_receipt_path(run_root, action_id)),
        )
        row = _router_scheduler_row_for_controller_entry(run_root, entry)
        row_reconciled = bool(row.get("router_state") == "reconciled")
        entry_reconciled = bool(entry.get("router_reconciliation_status") == "reconciled")
        projection_missing = (
            not _controller_boundary_flags_synced(run_state)
            or not isinstance(run_state.get("controller_boundary_confirmation"), dict)
            or not run_state.get("controller_boundary_confirmation", {}).get("path")
        )
        if entry_reconciled and row_reconciled and not projection_missing:
            continue
        applied = _sync_controller_boundary_confirmation_from_artifact(
            project_root,
            run_root,
            run_state,
            action,
            receipt,
            source=source,
        )
        if not applied.get("applied"):
            continue
        reconciliation = dict(applied)
        reconciliation["projection_reconciliation_source"] = source
        now = utc_now()
        entry["status"] = "done"
        entry["router_reconciliation_status"] = "reconciled"
        entry["router_reconciled_at"] = now
        entry["router_reconciliation"] = reconciliation
        entry["updated_at"] = now
        write_json(action_path, entry)
        if entry.get("router_scheduler_row_id"):
            _update_router_scheduler_row(
                project_root,
                run_root,
                run_state,
                row_id=str(entry["router_scheduler_row_id"]),
                router_state="reconciled",
                reconciliation=reconciliation,
            )
        pending = run_state.get("pending_action")
        if isinstance(pending, dict) and (
            pending.get("controller_action_id") == action_id
            or pending.get("action_type") == "confirm_controller_core_boundary"
        ):
            run_state["pending_action"] = None
            pending_cleared = True
        reconciled_actions.append(action_id)
        last_projection = reconciliation

    changed = bool(reconciled_actions) or flags_were_synced != _controller_boundary_flags_synced(run_state)
    if not changed:
        return {"changed": False, "reason": "controller_boundary_projection_already_synced"}
    ledger = _rebuild_controller_action_ledger(project_root, run_root, run_state)
    append_history(
        run_state,
        "router_reconciled_controller_boundary_projection",
        {
            "source": source,
            "reconciled_action_ids": reconciled_actions,
            "pending_action_cleared": pending_cleared,
            "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
            "ledger_counts": ledger.get("counts"),
            "projection": last_projection,
        },
    )
    return {
        "changed": True,
        "reconciled_action_ids": reconciled_actions,
        "pending_action_cleared": pending_cleared,
        "controller_boundary_flags_synced": _controller_boundary_flags_synced(run_state),
        "ledger_counts": ledger.get("counts"),
    }

__all__ = (
    '_sync_controller_boundary_confirmation_from_artifact',
    '_controller_boundary_flags_synced',
    '_router_scheduler_row_for_controller_entry',
    '_done_controller_receipt_for_entry',
    '_reconcile_controller_boundary_confirmation_projection',
)

_LOCAL_NAMES = set(globals())
