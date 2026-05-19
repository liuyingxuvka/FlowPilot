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


CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY: dict[str, dict[str, str]] = {
    "relay_material_scan_packets": {
        "kind": "packet_dispatch",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_packets_relayed",
    },
    "relay_research_packet": {
        "kind": "packet_dispatch",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_packet_relayed",
    },
    "relay_current_node_packet": {
        "kind": "packet_dispatch",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_packet_relayed",
    },
    "relay_pm_role_work_request_packet": {
        "kind": "packet_dispatch",
        "family": "pm_role_work",
        "record_source": "pm_role_work_request_index",
        "postcondition": "pm_role_work_request_packet_relayed",
    },
    "relay_material_scan_results_to_pm": {
        "kind": "result_relay",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_results_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_material_scan_results_to_reviewer": {
        "kind": "result_relay",
        "family": "material_scan",
        "record_source": "material_scan_index",
        "postcondition": "material_scan_results_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_research_result_to_pm": {
        "kind": "result_relay",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_result_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_research_result_to_reviewer": {
        "kind": "result_relay",
        "family": "research",
        "record_source": "research_packet_index",
        "postcondition": "research_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_current_node_result_to_pm": {
        "kind": "result_relay",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_result_relayed_to_pm",
        "to_role": "project_manager",
    },
    "relay_current_node_result_to_reviewer": {
        "kind": "result_relay",
        "family": "current_node",
        "record_source": "current_node_records",
        "postcondition": "current_node_result_relayed_to_reviewer",
        "to_role": "human_like_reviewer",
    },
    "relay_pm_role_work_result_to_pm": {
        "kind": "result_relay",
        "family": "pm_role_work",
        "record_source": "pm_role_work_request_index",
        "postcondition": "pm_role_work_result_relayed_to_pm",
        "to_role": "project_manager",
    },
}


def _registered_controller_receipt_evidence_fold_actions() -> tuple[str, ...]:
    return tuple(sorted(CONTROLLER_RECEIPT_EVIDENCE_FOLD_REGISTRY))


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


def _result_relay_record_status(spec: dict[str, str]) -> str:
    to_role = str(spec.get("to_role") or "").strip()
    if to_role == "human_like_reviewer":
        return "result_relayed_to_reviewer"
    return "result_relayed_to_pm"


def _result_relay_batch_status(spec: dict[str, str]) -> str:
    to_role = str(spec.get("to_role") or "").strip()
    if to_role == "human_like_reviewer":
        return "results_relayed_to_reviewer"
    return "results_relayed_to_pm"


def _apply_parallel_batch_receipt_lifecycle(
    router: ModuleType,
    run_root: Path,
    spec: dict[str, str],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    _bind_router(router)
    family = spec["family"]
    batch = router._active_parallel_packet_batch(run_root, family)
    if not isinstance(batch, dict):
        return {"changed": False, "reason": "no_active_parallel_batch"}
    packet_ids = {str(record.get("packet_id") or "").strip() for record in records if record.get("packet_id")}
    if not packet_ids:
        return {"changed": False, "reason": "no_packet_ids"}
    changed = False
    now = utc_now()
    if spec["kind"] == "packet_dispatch":
        for record in batch.get("packets") or []:
            if isinstance(record, dict) and str(record.get("packet_id") or "") in packet_ids:
                if record.get("status") != "packet_relayed":
                    record["status"] = "packet_relayed"
                    changed = True
                record.setdefault("relayed_at", now)
        if batch.get("status") != "packets_relayed":
            batch["status"] = "packets_relayed"
            changed = True
        counts = batch.setdefault("counts", {})
        relayed = len([item for item in batch.get("packets") or [] if isinstance(item, dict) and item.get("status") == "packet_relayed"])
        if counts.get("relayed") != relayed:
            counts["relayed"] = relayed
            changed = True
    elif spec["kind"] == "result_relay":
        record_status = _result_relay_record_status(spec)
        timestamp_field = f"{record_status}_at"
        for record in batch.get("packets") or []:
            if isinstance(record, dict) and str(record.get("packet_id") or "") in packet_ids:
                if record.get("status") != record_status:
                    record["status"] = record_status
                    changed = True
                record.setdefault(timestamp_field, now)
        batch_status = _result_relay_batch_status(spec)
        if batch.get("status") != batch_status:
            batch["status"] = batch_status
            changed = True
    if changed:
        router._write_parallel_packet_batch_state(run_root, batch)
    return {"changed": changed, "batch_id": batch.get("batch_id"), "batch_status": batch.get("status")}


def _apply_pm_role_work_receipt_lifecycle(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    spec: dict[str, str],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    _bind_router(router)
    if spec["family"] != "pm_role_work":
        return {"changed": False, "reason": "not_pm_role_work"}
    index = router._load_pm_role_work_request_index(run_root, run_state)
    changed = False
    now = utc_now()
    touched_request_ids: list[str] = []
    for source in records:
        request_id = str(source.get("request_id") or "").strip()
        if not request_id:
            continue
        record = router._pm_role_work_request_record(index, request_id)
        if not isinstance(record, dict):
            continue
        if spec["kind"] == "packet_dispatch":
            target_status = "packet_relayed"
            timestamp_field = "packet_relayed_at"
            lifecycle_status = "packet_relayed"
        elif spec["kind"] == "result_relay":
            target_status = _result_relay_record_status(spec)
            timestamp_field = f"{target_status}_at"
            lifecycle_status = target_status
        else:
            continue
        if record.get("status") != target_status:
            record["status"] = target_status
            changed = True
        record.setdefault(timestamp_field, now)
        router._record_officer_lifecycle_status(
            project_root,
            run_root,
            run_state,
            record,
            lifecycle_status=lifecycle_status,
        )
        touched_request_ids.append(request_id)
    if touched_request_ids:
        index["active_request_id"] = touched_request_ids[0]
    if changed:
        router._write_pm_role_work_request_index(run_root, index)
    return {"changed": changed, "request_ids": touched_request_ids}


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
