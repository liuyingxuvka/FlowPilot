"""Evidence readers for Controller packet/result receipt folds."""

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
    del action, spec, failures
    return []

__all__ = (
    "_active_holder_fast_lane_item",
    "_active_holder_lease_evidence",
    "_controller_receipt_fold_records",
    "_packet_ledger_record_for_envelope",
    "_parallel_batch_packet_evidence",
    "_runtime_relay_missing_deliverables",
)

_LOCAL_NAMES = set(globals())
