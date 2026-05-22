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
from flowpilot_router_controller_scheduler_receipts_packet_fold_lifecycle import *
from flowpilot_router_controller_scheduler_receipts_packet_fold_registry import *


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value
    _packet_fold_lifecycle._bind_router(router)


def _controller_receipt_fold_records(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _bind_router(router)
    source = spec["record_source"]
    if source == "material_scan_index":
        index = router._load_packet_index(router._material_scan_index_path(run_root), label="material scan")
        return list(index["packets"]), {"index_path": project_relative(project_root, router._material_scan_index_path(run_root))}
    if source == "research_packet_index":
        index = router._load_packet_index(router._research_packet_index_path(run_root), label="research")
        return list(index["packets"]), {"index_path": project_relative(project_root, router._research_packet_index_path(run_root))}
    if source == "current_node_records":
        return router._current_node_packet_records(project_root, run_state), {"record_source": "current_node_records"}
    if source == "pm_role_work_request_index":
        index = router._load_pm_role_work_request_index(run_root, run_state)
        records = router._active_pm_role_work_batch_records(index)
        if not records:
            active = router._active_pm_role_work_request(index)
            records = [active] if isinstance(active, dict) else []
        return list(records), {
            "index_path": project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
            "active_batch_id": index.get("active_batch_id"),
        }
    raise RouterError(f"unsupported receipt evidence fold record source: {source}")


def _parallel_batch_packet_evidence(
    router: ModuleType,
    run_root: Path,
    spec: dict[str, str],
    packet_id: str,
) -> dict[str, Any] | None:
    _bind_router(router)
    family = spec["family"]
    batch = router._active_parallel_packet_batch(run_root, family)
    if not isinstance(batch, dict):
        return None
    if str(batch.get("status") or "") not in {
        "packets_relayed",
        "partial_results_returned",
        "results_joined",
        "results_relayed_to_pm",
        "results_relayed_to_reviewer",
        "reviewed",
    }:
        return None
    batch_records = [item for item in batch.get("packets") or [] if isinstance(item, dict)]
    match = next((item for item in batch_records if str(item.get("packet_id") or "") == packet_id), None)
    if not match:
        return None
    if str(match.get("status") or "") not in {
        "packet_relayed",
        "result_returned",
        "result_relayed_to_pm",
        "result_relayed_to_reviewer",
        "reviewed",
        "absorbed",
    }:
        return None
    counts = batch.get("counts") if isinstance(batch.get("counts"), dict) else {}
    return {
        "source": "parallel_packet_batch",
        "batch_id": batch.get("batch_id"),
        "batch_status": batch.get("status"),
        "packet_status": match.get("status"),
        "counts": counts,
    }


def _packet_dispatch_record_evidence(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    record: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    packet_id = str(record.get("packet_id") or "").strip()
    if not packet_id:
        return {"ok": False, "reason": "packet_record_missing_packet_id"}
    try:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
    except (RouterError, OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {"ok": False, "packet_id": packet_id, "reason": "packet_envelope_unreadable", "error": str(exc)}
    expected_role = str(envelope.get("to_role") or record.get("to_role") or "").strip()
    if not expected_role:
        return {"ok": False, "packet_id": packet_id, "reason": "packet_record_missing_target_role"}
    evidence: list[dict[str, Any]] = []
    try:
        relay = packet_runtime.verify_controller_relay(envelope, recipient_role=expected_role)
        evidence.append({"source": "packet_controller_relay", "relayed_at": relay.get("relayed_at")})
    except packet_runtime.PacketRuntimeError as exc:
        relay_error = str(exc)
    else:
        relay_error = ""
    try:
        open_record = packet_runtime.verify_packet_open_receipt(project_root, envelope, role=expected_role)
        evidence.append({"source": "packet_open_receipt", "opened_by_role": open_record.get("packet_body_opened_by_role")})
    except packet_runtime.PacketRuntimeError:
        pass
    try:
        lease_path = packet_runtime.packet_paths_from_envelope(project_root, envelope)["packet_dir"] / "active_holder_lease.json"
        if lease_path.exists():
            lease = packet_runtime._load_active_holder_lease(project_root, lease_path)  # type: ignore[attr-defined]
            if (
                lease.get("status") == "active"
                and lease.get("packet_id") == packet_id
                and lease.get("holder_role") == expected_role
                and lease.get("packet_body_hash") == envelope.get("body_hash")
            ):
                evidence.append(
                    {
                        "source": "active_holder_lease",
                        "lease_id": lease.get("lease_id"),
                        "holder_role": lease.get("holder_role"),
                    }
                )
    except (OSError, ValueError, packet_runtime.PacketRuntimeError):
        pass
    batch_evidence = _parallel_batch_packet_evidence(router, run_root, spec, packet_id)
    if batch_evidence:
        evidence.append(batch_evidence)
    if not evidence:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_dispatch_evidence_missing",
            "controller_relay_error": relay_error,
        }
    return {
        "ok": True,
        "packet_id": packet_id,
        "target_role": expected_role,
        "packet_envelope_path": project_relative(project_root, envelope_path),
        "evidence": evidence,
    }


def _result_relay_record_evidence(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    record: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    packet_id = str(record.get("packet_id") or "").strip()
    if not packet_id:
        return {"ok": False, "reason": "packet_record_missing_packet_id"}
    expected_role = str(action.get("to_role") or spec.get("to_role") or "").strip()
    if not expected_role:
        return {"ok": False, "packet_id": packet_id, "reason": "result_relay_missing_expected_recipient"}
    try:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        result = packet_runtime.load_envelope(project_root, result_path)
    except (RouterError, OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {"ok": False, "packet_id": packet_id, "reason": "result_envelope_unreadable", "error": str(exc)}
    if str(result.get("next_recipient") or "") != expected_role:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_relay_wrong_next_recipient",
            "expected_recipient": expected_role,
            "actual_recipient": result.get("next_recipient"),
        }
    try:
        relay = packet_runtime.verify_controller_relay(result, recipient_role=expected_role)
    except packet_runtime.PacketRuntimeError as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_relay_evidence_missing",
            "controller_relay_error": str(exc),
        }
    return {
        "ok": True,
        "packet_id": packet_id,
        "target_role": expected_role,
        "result_envelope_path": project_relative(project_root, result_path),
        "evidence": [{"source": "result_controller_relay", "relayed_at": relay.get("relayed_at")}],
    }


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
            _packet_dispatch_record_evidence(router, project_root, run_root, run_state, spec, record)
            for record in records
        ]
    else:
        record_results = [
            _result_relay_record_evidence(router, project_root, run_state, spec, record, action)
            for record in records
        ]
    failures = [item for item in record_results if not item.get("ok")]
    if failures:
        return {
            "applied": False,
            "reason": "controller_receipt_evidence_fold_not_satisfied",
            "action_type": action_type,
            "postcondition": spec["postcondition"],
            "fold_kind": spec["kind"],
            "record_context": record_context,
            "failures": failures,
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
        "router_folded_controller_relay_receipt_evidence",
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
