"""Lifecycle writeback helpers for Controller receipt evidence folds."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


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


def _receipt_lifecycle_policy(spec: dict[str, str]) -> dict[str, str] | None:
    kind = spec["kind"]
    if kind == "packet_dispatch":
        return {
            "record_status": "packet_relayed",
            "batch_timestamp_field": "relayed_at",
            "pm_timestamp_field": "packet_relayed_at",
            "batch_status": "packets_relayed",
            "count_key": "relayed",
            "count_status": "packet_relayed",
            "flowguard_operator_lifecycle_status": "packet_relayed",
        }
    if kind == "result_relay":
        record_status = _result_relay_record_status(spec)
        return {
            "record_status": record_status,
            "batch_timestamp_field": f"{record_status}_at",
            "pm_timestamp_field": f"{record_status}_at",
            "batch_status": _result_relay_batch_status(spec),
            "count_key": "",
            "count_status": "",
            "flowguard_operator_lifecycle_status": record_status,
        }
    return None


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
    policy = _receipt_lifecycle_policy(spec)
    if not policy:
        return {"changed": False, "reason": "unsupported_receipt_lifecycle_kind"}
    changed = False
    now = utc_now()
    record_status = policy["record_status"]
    timestamp_field = policy["batch_timestamp_field"]
    for record in batch.get("packets") or []:
        if isinstance(record, dict) and str(record.get("packet_id") or "") in packet_ids:
            if record.get("status") != record_status:
                record["status"] = record_status
                changed = True
            record.setdefault(timestamp_field, now)
    batch_status = policy["batch_status"]
    if batch.get("status") != batch_status:
        batch["status"] = batch_status
        changed = True
    count_key = policy.get("count_key")
    count_status = policy.get("count_status")
    if count_key and count_status:
        counts = batch.setdefault("counts", {})
        count = len(
            [
                item
                for item in batch.get("packets") or []
                if isinstance(item, dict) and item.get("status") == count_status
            ]
        )
        if counts.get(count_key) != count:
            counts[count_key] = count
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
    policy = _receipt_lifecycle_policy(spec)
    if not policy:
        return {"changed": False, "reason": "unsupported_receipt_lifecycle_kind"}
    index = router._load_pm_role_work_request_index(run_root, run_state)
    changed = False
    now = utc_now()
    touched_request_ids: list[str] = []
    target_status = policy["record_status"]
    timestamp_field = policy["pm_timestamp_field"]
    lifecycle_status = policy["flowguard_operator_lifecycle_status"]
    for source in records:
        request_id = str(source.get("request_id") or "").strip()
        if not request_id:
            continue
        record = router._pm_role_work_request_record(index, request_id)
        if not isinstance(record, dict):
            continue
        if record.get("status") != target_status:
            record["status"] = target_status
            changed = True
        record.setdefault(timestamp_field, now)
        router._record_flowguard_operator_lifecycle_status(
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


__all__ = (
    "_receipt_lifecycle_policy",
    "_apply_parallel_batch_receipt_lifecycle",
    "_apply_pm_role_work_receipt_lifecycle",
)

_LOCAL_NAMES = set(globals())
