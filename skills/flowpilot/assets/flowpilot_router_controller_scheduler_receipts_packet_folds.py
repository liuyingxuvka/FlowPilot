"""Evidence folds for packet/result Controller receipts.

These helpers reconcile Controller ``done`` receipts for packet relay actions
from Router-visible evidence only. They do not invoke relay handlers and do
not read sealed packet or result bodies.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_control_plane_contracts import control_blocker_delivery_postcondition
from flowpilot_router_errors import RouterError
import flowpilot_router_controller_scheduler_receipts_packet_fold_lifecycle as _packet_fold_lifecycle
import flowpilot_router_controller_scheduler_receipts_packet_fold_evidence as _packet_fold_evidence
import flowpilot_router_controller_scheduler_receipts_packet_fold_record_evidence as _packet_fold_record_evidence
from flowpilot_router_controller_scheduler_receipts_packet_fold_lifecycle import *
from flowpilot_router_controller_scheduler_receipts_packet_fold_evidence import *
from flowpilot_router_controller_scheduler_receipts_packet_fold_record_evidence import *
from flowpilot_router_controller_scheduler_receipts_packet_fold_registry import *


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
    _packet_fold_lifecycle._bind_router(router)
    _packet_fold_evidence._bind_router(router)
    _packet_fold_record_evidence._bind_router(router)


def _sync_pm_role_work_request_summary(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    _bind_router(router)
    if not records:
        return
    index = router._load_pm_role_work_request_index(run_root, run_state)
    run_state["pm_role_work_requests"] = {
        "index_path": project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
        "active_batch_id": index.get("active_batch_id"),
        "active_request_ids": [record.get("request_id") for record in records],
        "active_packet_ids": [record.get("packet_id") for record in records],
        "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records if record.get("to_role")})),
        "active_request_mode": records[0].get("request_mode"),
    }


def _apply_control_blocker_delivery_receipt_fold(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    blocker_id = action.get("blocker_id")
    postcondition = str(
        router._pending_action_postcondition(action)
        or control_blocker_delivery_postcondition(blocker_id)
    ).strip()
    try:
        router._mark_control_blocker_delivered(project_root, run_root, run_state, action)
    except (RouterError, OSError, ValueError) as exc:
        return {
            "applied": False,
            "reason": "control_blocker_delivery_fold_failed",
            "action_type": "handle_control_blocker",
            "postcondition": postcondition,
            "error": str(exc),
        }
    if postcondition:
        run_state.setdefault("flags", {})[postcondition] = True
    return {
        "applied": True,
        "source": "controller_receipt_control_blocker_delivery_fold",
        "action_type": "handle_control_blocker",
        "postcondition": postcondition,
        "blocker_id": blocker_id,
        "blocker_artifact_path": action.get("blocker_artifact_path"),
        "sealed_body_reads": False,
    }


def _apply_registered_controller_receipt_evidence_fold(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    receipt_payload: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    del receipt_payload
    action_type = str(action.get("action_type") or "").strip()
    spec = CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY.get(action_type)
    if not spec:
        return {"applied": False, "reason": "not_registered_controller_receipt_evidence_fold", "action_type": action_type}
    if spec["kind"] == "control_blocker_delivery":
        return _apply_control_blocker_delivery_receipt_fold(router, project_root, run_root, run_state, action)
    try:
        records, record_context = _controller_receipt_fold_records(router, project_root, run_root, run_state, spec)
    except (RouterError, OSError, ValueError) as exc:
        return {
            "applied": False,
            "reason": "controller_receipt_evidence_records_unavailable",
            "action_type": action_type,
            "postcondition": spec["postcondition"],
            "error": str(exc),
        }
    if not records:
        return {
            "applied": False,
            "reason": "controller_receipt_evidence_records_missing",
            "action_type": action_type,
            "postcondition": spec["postcondition"],
            "record_source": spec["record_source"],
        }
    if spec["kind"] == "packet_dispatch":
        record_results = [
            _packet_dispatch_record_evidence(router, project_root, run_root, run_state, spec, action, record)
            for record in records
        ]
    else:
        record_results = [
            _result_relay_record_evidence(router, project_root, run_state, spec, record, action)
            for record in records
        ]
    failures = [item for item in record_results if not item.get("ok")]
    if failures:
        missing_deliverables = _runtime_relay_missing_deliverables(action, spec, failures)
        return {
            "applied": False,
            "reason": "controller_receipt_evidence_fold_not_satisfied",
            "action_type": action_type,
            "postcondition": spec["postcondition"],
            "fold_kind": spec["kind"],
            "record_context": record_context,
            "failures": failures,
            "repairable": bool(missing_deliverables),
            "relay_repair_required": bool(missing_deliverables),
            "missing_deliverables": missing_deliverables,
        }
    flag = spec["postcondition"]
    run_state.setdefault("flags", {})[flag] = True
    batch_lifecycle = _apply_parallel_batch_receipt_lifecycle(router, run_root, spec, records)
    pm_role_work_lifecycle = _apply_pm_role_work_receipt_lifecycle(
        router,
        project_root,
        run_root,
        run_state,
        spec,
        records,
    )
    if spec["family"] == "pm_role_work":
        _sync_pm_role_work_request_summary(router, project_root, run_root, run_state, records)
    if action.get("ledger_check_receipt_required") or action.get("combined_ledger_check_and_relay"):
        run_state["ledger_check_requested"] = False
    append_history(
        run_state,
        "router_folded_controller_delivery_receipt_evidence",
        {
            "action_type": action_type,
            "postcondition": flag,
            "fold_kind": spec["kind"],
            "packet_ids": [item.get("packet_id") for item in record_results],
            "record_source": spec["record_source"],
            "batch_lifecycle": batch_lifecycle,
            "pm_role_work_lifecycle": pm_role_work_lifecycle,
        },
    )
    return {
        "applied": True,
        "source": "controller_receipt_evidence_fold",
        "action_type": action_type,
        "postcondition": flag,
        "fold_kind": spec["kind"],
        "record_context": record_context,
        "record_count": len(record_results),
        "evidence": record_results,
        "batch_lifecycle": batch_lifecycle,
        "pm_role_work_lifecycle": pm_role_work_lifecycle,
        "sealed_body_reads": False,
    }


__all__ = (
    "CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY",
    "_registered_controller_receipt_evidence_fold_actions",
    "_apply_registered_controller_receipt_evidence_fold",
)

_LOCAL_NAMES = set(globals())
