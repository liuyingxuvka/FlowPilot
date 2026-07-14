"""Parallel packet batch result reconciliation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_errors import RouterError

_BOUND_ROUTER: ModuleType | None = None

_PARALLEL_PACKET_BATCH_EXPECTED_RESULT_RECIPIENTS = {
    "research": "project_manager",
    "current_node": "project_manager",
    "pm_role_work": "project_manager",
}


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


def _parallel_batch_record_result_exists(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    record: dict[str, Any],
) -> tuple[bool, Path]:
    _bind_router(router)
    result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
    return (result_path.exists(), result_path)


def _parallel_batch_record_result_is_valid(
    router: ModuleType,
    project_root: Path,
    result_path: Path,
    *,
    expected_next_recipient: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    _bind_router(router)
    try:
        result = packet_runtime.load_envelope(project_root, result_path)
    except (OSError, json.JSONDecodeError, packet_runtime.PacketRuntimeError):
        return False, {"reason": "invalid_result_envelope"}
    if expected_next_recipient and result.get("next_recipient") != expected_next_recipient:
        return False, {
            "reason": "wrong_next_recipient",
            "expected_next_recipient": expected_next_recipient,
            "actual_next_recipient": result.get("next_recipient"),
        }
    return True, result


def _parallel_packet_batch_member_summary(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    batch: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    expected_next_recipient = _PARALLEL_PACKET_BATCH_EXPECTED_RESULT_RECIPIENTS.get(str(batch.get("batch_kind") or ""))
    returned_roles: list[str] = []
    missing_roles: list[str] = []
    returned_packet_ids: list[str] = []
    missing_packet_ids: list[str] = []
    invalid_result_roles: list[str] = []
    invalid_result_packet_ids: list[str] = []
    packet_count = 0
    for record in batch.get("packets") or []:
        if not isinstance(record, dict):
            continue
        packet_count += 1
        packet_id = str(record.get("packet_id") or "")
        role = str(record.get("to_role") or packet_id or "unknown")
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        valid_result_exists = False
        if result_exists:
            valid_result_exists, _result = router._parallel_batch_record_result_is_valid(
                project_root,
                result_path,
                expected_next_recipient=expected_next_recipient,
            )
            if not valid_result_exists:
                invalid_result_roles.append(role)
                if packet_id:
                    invalid_result_packet_ids.append(packet_id)
        status = str(record.get("status") or "")
        if valid_result_exists or (not result_exists and status in PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES):
            returned_roles.append(role)
            if packet_id:
                returned_packet_ids.append(packet_id)
        else:
            missing_roles.append(role)
            if packet_id:
                missing_packet_ids.append(packet_id)
    returned_roles = sorted(set(returned_roles))
    missing_roles = sorted(set(missing_roles))
    returned_packet_ids = sorted(set(returned_packet_ids))
    missing_packet_ids = sorted(set(missing_packet_ids))
    invalid_result_roles = sorted(set(invalid_result_roles))
    invalid_result_packet_ids = sorted(set(invalid_result_packet_ids))
    return {
        "batch_id": batch.get("batch_id"),
        "batch_kind": batch.get("batch_kind"),
        "packet_count": packet_count,
        "results_returned": len(returned_packet_ids),
        "missing_count": len(missing_packet_ids),
        "returned_roles": returned_roles,
        "missing_roles": missing_roles,
        "returned_packet_ids": returned_packet_ids,
        "missing_packet_ids": missing_packet_ids,
        "invalid_result_roles": invalid_result_roles,
        "invalid_result_packet_ids": invalid_result_packet_ids,
        "all_results_returned": packet_count > 0 and len(returned_packet_ids) == packet_count,
        "partial_results_returned": 0 < len(returned_packet_ids) < packet_count,
        "controller_visibility": "metadata_only",
    }


def _refresh_parallel_packet_batch_from_durable_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    batch_kind: str,
) -> dict[str, Any]:
    _bind_router(router)
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return {"batch_kind": batch_kind, "active": False, "changed": False}
    expected_next_recipient = _PARALLEL_PACKET_BATCH_EXPECTED_RESULT_RECIPIENTS.get(batch_kind)
    before = json.dumps(batch, sort_keys=True)
    returned = 0
    relayed = 0
    for record in batch.get("packets") or []:
        if not isinstance(record, dict):
            continue
        if str(record.get("status") or "") in {"packet_relayed", *PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES}:
            relayed += 1
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if not result_exists:
            continue
        valid_result, result = router._parallel_batch_record_result_is_valid(
            project_root,
            result_path,
            expected_next_recipient=expected_next_recipient,
        )
        record["result_envelope_path"] = project_relative(project_root, result_path)
        record["result_envelope_hash"] = packet_runtime.sha256_file(result_path)
        if not valid_result:
            record["result_invalid_reason"] = result.get("reason")
            record["result_invalid_details"] = result
            if str(record.get("status") or "") in PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES:
                record["status"] = "packet_relayed"
            continue
        returned += 1
        record.pop("result_invalid_reason", None)
        record.pop("result_invalid_details", None)
        if str(record.get("status") or "") not in PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES:
            record["status"] = "result_returned"
        record.setdefault("result_returned_at", utc_now())
        if isinstance(result, dict):
            if result.get("result_body_path"):
                record["result_body_path"] = result.get("result_body_path")
            if result.get("result_body_hash"):
                record["result_body_hash"] = result.get("result_body_hash")
    summary = router._parallel_packet_batch_member_summary(project_root, run_state, batch)
    counts = batch.setdefault("counts", {})
    counts["registered"] = summary["packet_count"]
    counts["relayed"] = max(int(counts.get("relayed") or 0), relayed)
    counts["results_returned"] = summary["results_returned"]
    previous_member_status = batch.get("member_status") if isinstance(batch.get("member_status"), dict) else {}
    member_status = {
        "schema_version": "flowpilot.parallel_packet_batch_member_status.v1",
        "controller_visibility": "metadata_only",
        "returned_roles": summary["returned_roles"],
        "missing_roles": summary["missing_roles"],
        "returned_packet_ids": summary["returned_packet_ids"],
        "missing_packet_ids": summary["missing_packet_ids"],
        "invalid_result_roles": summary["invalid_result_roles"],
        "invalid_result_packet_ids": summary["invalid_result_packet_ids"],
        "results_returned": summary["results_returned"],
        "packet_count": summary["packet_count"],
        "partial_results_returned": summary["partial_results_returned"],
        "all_results_returned": summary["all_results_returned"],
    }
    comparable_previous = {key: value for key, value in previous_member_status.items() if key != "updated_at"}
    member_status["updated_at"] = (
        previous_member_status.get("updated_at")
        if comparable_previous == member_status and previous_member_status.get("updated_at")
        else utc_now()
    )
    batch["member_status"] = member_status
    if summary["all_results_returned"] and str(batch.get("status") or "") not in PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES:
        batch["status"] = "results_joined"
        batch.setdefault("joined_at", utc_now())
    elif summary["partial_results_returned"] and str(batch.get("status") or "") not in PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES:
        batch["status"] = "partial_results_returned"
    changed = before != json.dumps(batch, sort_keys=True)
    if changed:
        router._write_parallel_packet_batch_state(run_root, batch)
    return {**summary, "active": True, "changed": changed, "batch_status": batch.get("status")}


def _refresh_all_parallel_packet_batches_from_durable_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    summaries = {
        batch_kind: router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind)
        for batch_kind in ("research", "current_node", "pm_role_work")
    }
    return {
        "schema_version": "flowpilot.parallel_packet_batch_reconciliation.v1",
        "changed": any(bool(summary.get("changed")) for summary in summaries.values()),
        "batches": summaries,
        "reconciled_at": utc_now(),
    }


def _mark_parallel_batch_results_joined(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    batch_kind: str,
) -> None:
    _bind_router(router)
    router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind)


__all__ = (
    "_parallel_batch_record_result_exists",
    "_parallel_batch_record_result_is_valid",
    "_parallel_packet_batch_member_summary",
    "_refresh_parallel_packet_batch_from_durable_results",
    "_refresh_all_parallel_packet_batches_from_durable_results",
    "_mark_parallel_batch_results_joined",
)

_LOCAL_NAMES = set(globals())
