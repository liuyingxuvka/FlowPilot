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


def _packet_ledger_record_for_envelope(
    project_root: Path,
    envelope: dict[str, Any],
) -> tuple[dict[str, Any] | None, Path]:
    paths = packet_runtime.packet_paths_from_any_envelope(project_root, envelope)
    return packet_runtime.packet_ledger_record_for_envelope(project_root, envelope), paths["packet_ledger"]


def _active_holder_fast_lane_item(action: dict[str, Any], packet_id: str) -> dict[str, Any] | None:
    plan = action.get("active_holder_fast_lane")
    if not isinstance(plan, dict):
        return None
    for item in plan.get("packets") or []:
        if isinstance(item, dict) and str(item.get("packet_id") or "") == packet_id:
            return item
    return None


def _active_holder_lease_evidence(
    project_root: Path,
    packet_id: str,
    expected_role: str,
    action: dict[str, Any],
) -> dict[str, Any]:
    item = _active_holder_fast_lane_item(action, packet_id)
    if not isinstance(item, dict) or not str(item.get("target_agent_id") or "").strip():
        return {"required": False}
    lease_path = str(item.get("active_holder_lease_path") or "").strip()
    if not lease_path:
        return {"required": True, "ok": False, "reason": "active_holder_lease_path_missing"}
    try:
        lease = packet_runtime._load_active_holder_lease(project_root, lease_path)  # type: ignore[attr-defined]
    except (OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {
            "required": True,
            "ok": False,
            "reason": "active_holder_lease_missing_or_unreadable",
            "active_holder_lease_path": lease_path,
            "error": str(exc),
        }
    if str(lease.get("packet_id") or "") != packet_id:
        return {"required": True, "ok": False, "reason": "active_holder_lease_packet_mismatch", "active_holder_lease_path": lease_path}
    if str(lease.get("holder_role") or "") != expected_role:
        return {
            "required": True,
            "ok": False,
            "reason": "active_holder_lease_role_mismatch",
            "active_holder_lease_path": lease_path,
            "expected_role": expected_role,
            "actual_role": lease.get("holder_role"),
        }
    if str(lease.get("holder_agent_id") or "") != str(item.get("target_agent_id") or ""):
        return {
            "required": True,
            "ok": False,
            "reason": "active_holder_lease_agent_mismatch",
            "active_holder_lease_path": lease_path,
            "expected_agent_id": item.get("target_agent_id"),
            "actual_agent_id": lease.get("holder_agent_id"),
        }
    if str(lease.get("status") or "") not in {"active", "closed"}:
        return {
            "required": True,
            "ok": False,
            "reason": "active_holder_lease_not_active",
            "active_holder_lease_path": lease_path,
            "status": lease.get("status"),
        }
    liveness = lease.get("holder_liveness") if isinstance(lease.get("holder_liveness"), dict) else {}
    if liveness.get("host_liveness_proven") is not True:
        return {
            "required": True,
            "ok": False,
            "reason": "active_holder_lease_liveness_missing",
            "active_holder_lease_path": lease_path,
        }
    return {
        "required": True,
        "ok": True,
        "source": "active_holder_lease",
        "active_holder_lease_path": lease_path,
        "lease_id": lease.get("lease_id"),
        "holder_role": lease.get("holder_role"),
        "holder_agent_id": lease.get("holder_agent_id"),
        "holder_liveness": liveness,
    }


def _runtime_relay_missing_deliverables(
    action: dict[str, Any],
    spec: dict[str, str],
    failures: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    repairable_reasons = {
        "packet_runtime_relay_evidence_missing",
        "packet_ledger_controller_relay_missing",
        "packet_ledger_record_missing",
        "packet_ledger_relay_holder_mismatch",
        "packet_ledger_relay_status_mismatch",
        "active_holder_lease_path_missing",
        "active_holder_lease_missing_or_unreadable",
        "active_holder_lease_packet_mismatch",
        "active_holder_lease_role_mismatch",
        "active_holder_lease_agent_mismatch",
        "active_holder_lease_not_active",
        "active_holder_lease_liveness_missing",
        "result_relay_evidence_missing",
        "result_ledger_controller_relay_missing",
        "result_ledger_record_missing",
        "result_ledger_relay_holder_mismatch",
    }
    failed_packet_ids = {
        str(item.get("packet_id") or "")
        for item in failures
        if isinstance(item, dict) and str(item.get("reason") or "") in repairable_reasons
    }
    if not failed_packet_ids:
        return []
    operations = [
        item
        for item in action.get("runtime_relay_operations") or []
        if isinstance(item, dict) and str(item.get("packet_id") or "") in failed_packet_ids
    ]
    deliverables: list[dict[str, Any]] = []
    for operation in operations:
        packet_id = str(operation.get("packet_id") or "")
        envelope_kind = str(operation.get("envelope_kind") or "")
        path = str(operation.get("envelope_path") or "").strip()
        if not packet_id or not path:
            continue
        deliverables.append(
            {
                "deliverable_id": f"runtime_relay:{spec['postcondition']}:{packet_id}:{envelope_kind}",
                "artifact_kind": str(operation.get("expected_relay_kind") or "controller_relay"),
                "path": path,
                "postcondition": spec["postcondition"],
                "runtime_channel": "flowpilot_runtime.py relay-envelope",
                "output_type": "runtime_relay_evidence",
                "output_contract_id": "flowpilot.runtime_relay_operation.v1",
                "path_key": "envelope_path",
                "hash_key": "controller_relay_envelope_hash",
                "required_role": "controller",
                "controller_may_read_sealed_bodies": False,
                "required_before_router_reconciles_done_receipt": True,
                "runtime_relay_operation": operation,
                "expected_writes": operation.get("expected_writes") or [],
                "path_only_handoff_is_not_completion": True,
            }
        )
    return deliverables


def _packet_dispatch_record_evidence(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    action: dict[str, Any],
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
    try:
        relay = packet_runtime.verify_controller_relay(envelope, recipient_role=expected_role)
    except packet_runtime.PacketRuntimeError as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_runtime_relay_evidence_missing",
            "controller_relay_error": str(exc),
            "packet_envelope_path": project_relative(project_root, envelope_path),
        }
    try:
        ledger_record, ledger_path = _packet_ledger_record_for_envelope(project_root, envelope)
    except (OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_record_missing",
            "error": str(exc),
            "packet_envelope_path": project_relative(project_root, envelope_path),
        }
    if not isinstance(ledger_record, dict):
        return {"ok": False, "packet_id": packet_id, "reason": "packet_ledger_record_missing"}
    if not isinstance(ledger_record.get("packet_controller_relay"), dict):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_controller_relay_missing",
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    holder_matches = str(ledger_record.get("active_packet_holder") or "") == expected_role
    opened_by_expected = str(ledger_record.get("packet_body_opened_by_role") or "") == expected_role
    result_recorded = bool(ledger_record.get("result_envelope_path") or ledger_record.get("result_body_path"))
    if not (holder_matches or opened_by_expected or result_recorded):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "packet_ledger_relay_holder_mismatch",
            "expected_holder": expected_role,
            "actual_holder": ledger_record.get("active_packet_holder"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    lease_evidence = _active_holder_lease_evidence(project_root, packet_id, expected_role, action)
    if lease_evidence.get("required") and not lease_evidence.get("ok"):
        return {"ok": False, "packet_id": packet_id, **lease_evidence}
    evidence: list[dict[str, Any]] = [
        {"source": "packet_controller_relay", "relayed_at": relay.get("relayed_at")},
        {
            "source": "packet_ledger_controller_relay",
            "active_packet_holder": ledger_record.get("active_packet_holder"),
            "active_packet_status": ledger_record.get("active_packet_status"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        },
    ]
    if lease_evidence.get("ok"):
        evidence.append({key: value for key, value in lease_evidence.items() if key not in {"required", "ok"}})
    try:
        open_record = packet_runtime.verify_packet_open_receipt(project_root, envelope, role=expected_role)
        evidence.append({"source": "packet_open_receipt", "opened_by_role": open_record.get("packet_body_opened_by_role")})
    except packet_runtime.PacketRuntimeError:
        pass
    batch_evidence = _parallel_batch_packet_evidence(router, run_root, spec, packet_id)
    if batch_evidence:
        evidence.append(batch_evidence)
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
    try:
        ledger_record, ledger_path = _packet_ledger_record_for_envelope(project_root, result)
    except (OSError, ValueError, packet_runtime.PacketRuntimeError) as exc:
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_record_missing",
            "error": str(exc),
            "result_envelope_path": project_relative(project_root, result_path),
        }
    if not isinstance(ledger_record, dict):
        return {"ok": False, "packet_id": packet_id, "reason": "result_ledger_record_missing"}
    if not isinstance(ledger_record.get("result_controller_relay"), dict):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_controller_relay_missing",
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    holder_matches = str(ledger_record.get("active_packet_holder") or "") == expected_role
    opened_by_expected = str(ledger_record.get("result_body_opened_by_role") or "") == expected_role
    if not (holder_matches or opened_by_expected):
        return {
            "ok": False,
            "packet_id": packet_id,
            "reason": "result_ledger_relay_holder_mismatch",
            "expected_holder": expected_role,
            "actual_holder": ledger_record.get("active_packet_holder"),
            "packet_ledger_path": project_relative(project_root, ledger_path),
        }
    return {
        "ok": True,
        "packet_id": packet_id,
        "target_role": expected_role,
        "result_envelope_path": project_relative(project_root, result_path),
        "evidence": [
            {"source": "result_controller_relay", "relayed_at": relay.get("relayed_at")},
            {
                "source": "packet_ledger_result_controller_relay",
                "active_packet_holder": ledger_record.get("active_packet_holder"),
                "active_packet_status": ledger_record.get("active_packet_status"),
                "packet_ledger_path": project_relative(project_root, ledger_path),
            },
        ],
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
