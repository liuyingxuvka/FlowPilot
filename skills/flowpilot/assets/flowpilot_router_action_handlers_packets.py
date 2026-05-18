"""Controller-action application handlers for FlowPilot router.

This module is a thin extraction layer. It keeps state persistence and
post-apply finalization in `flowpilot_router.apply_controller_action` while
moving low-risk action bodies behind an action-type registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

from flowpilot_router_controller_boundary import CONTROLLER_DELIVERABLE_REPAIR_ACTION_TYPE
from flowpilot_router_action_handlers_basic import _request_ledger_check


@dataclass(frozen=True)
class ActionHandlerOutcome:
    result_extra: dict[str, Any] = field(default_factory=dict)
    early_return: dict[str, Any] | None = None


ActionHandler = Callable[
    [ModuleType, Path, Path, dict[str, Any], dict[str, Any], dict[str, Any] | None],
    ActionHandlerOutcome,
]

def _apply_relay_material_scan_packets(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="material scan packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._material_scan_index_path(run_root), label="material scan")
    router._relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
    router._mark_parallel_batch_packets_relayed(run_root, "material_scan")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        index["packets"],
        packet_family="material_scan",
        mode="lease_on_material_scan_relay",
    )
    run_state["flags"]["material_scan_packets_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})

def _apply_relay_material_scan_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="material scan result relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._material_scan_index_path(run_root), label="material scan")
    router._relay_result_records(project_root, run_state, index["packets"], to_role="project_manager", controller_agent_id="controller")
    run_state["flags"]["material_scan_results_relayed_to_pm"] = True
    batch = router._active_parallel_packet_batch(run_root, "material_scan")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()

def _apply_relay_research_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="research packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._research_packet_index_path(run_root), label="research")
    router._relay_packet_records(project_root, run_state, index["packets"], controller_agent_id="controller")
    router._mark_parallel_batch_packets_relayed(run_root, "research")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        index["packets"],
        packet_family="research",
        mode="lease_on_research_packet_relay",
    )
    run_state["flags"]["research_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})

def _apply_relay_research_result(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="research result relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    index = router._load_packet_index(router._research_packet_index_path(run_root), label="research")
    router._relay_result_records(project_root, run_state, index["packets"], to_role="project_manager", controller_agent_id="controller")
    batch = router._active_parallel_packet_batch(run_root, "research")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["flags"]["research_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()

def _apply_relay_pm_role_work_request_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="PM role-work request relay requires a current packet-ledger check",
    )
    index = router._load_pm_role_work_request_index(run_root, run_state)
    batch_records = router._active_pm_role_work_batch_records(index)
    records = [record for record in batch_records if record.get("status") == "open"] if batch_records else []
    if not records:
        active = router._active_pm_role_work_request(index)
        records = [active] if isinstance(active, dict) and active.get("status") == "open" else []
    if not records:
        raise router.RouterError("PM role-work request relay requires an open active request")
    router._relay_packet_records(project_root, run_state, records, controller_agent_id="controller")
    for record in records:
        record["status"] = "packet_relayed"
        record["packet_relayed_at"] = router.utc_now()
        router._record_officer_lifecycle_status(
            project_root,
            run_root,
            run_state,
            record,
            lifecycle_status="packet_relayed",
        )
    router._mark_parallel_batch_packets_relayed(run_root, "pm_role_work")
    lease_summary = router._issue_packet_active_holder_leases(
        project_root,
        run_root,
        run_state,
        records,
        packet_family="pm_role_work",
        mode="lease_on_pm_role_work_request_relay",
    )
    index["active_request_id"] = records[0].get("request_id")
    router._write_pm_role_work_request_index(run_root, index)
    run_state["flags"]["pm_role_work_request_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    run_state["pm_role_work_requests"] = {
        "index_path": router.project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
        "active_batch_id": index.get("active_batch_id"),
        "active_request_ids": [record.get("request_id") for record in records],
        "active_packet_ids": [record.get("packet_id") for record in records],
        "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
        "active_request_mode": records[0].get("request_mode"),
    }
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})

def _apply_relay_pm_role_work_result_to_pm(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="PM role-work result relay requires a current packet-ledger check",
    )
    index = router._load_pm_role_work_request_index(run_root, run_state)
    batch_records = router._active_pm_role_work_batch_records(index)
    records = [record for record in batch_records if record.get("status") == "result_returned"] if batch_records else []
    if not records:
        active = router._active_pm_role_work_request(index)
        records = [active] if isinstance(active, dict) and active.get("status") == "result_returned" else []
    if not records:
        raise router.RouterError("PM role-work result relay requires an active returned result")
    router._relay_result_records(project_root, run_state, records, to_role="project_manager", controller_agent_id="controller")
    for record in records:
        record["status"] = "result_relayed_to_pm"
        record["result_relayed_to_pm_at"] = router.utc_now()
        router._record_officer_lifecycle_status(
            project_root,
            run_root,
            run_state,
            record,
            lifecycle_status="result_relayed_to_pm",
        )
    batch = router._active_parallel_packet_batch(run_root, "pm_role_work")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    index["active_request_id"] = records[0].get("request_id")
    router._write_pm_role_work_request_index(run_root, index)
    run_state["flags"]["pm_role_work_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    run_state["pm_role_work_requests"] = {
        "index_path": router.project_relative(project_root, router._pm_role_work_request_index_path(run_root)),
        "active_batch_id": index.get("active_batch_id"),
        "active_request_ids": [record.get("request_id") for record in records],
        "active_packet_ids": [record.get("packet_id") for record in records],
        "active_to_role": ",".join(sorted({str(record.get("to_role")) for record in records})),
        "active_request_mode": records[0].get("request_mode"),
    }
    return ActionHandlerOutcome()

def _apply_enter_next_child_node(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    return ActionHandlerOutcome(result_extra=router._enter_next_child_node(project_root, run_root, run_state, pending))

def _apply_relay_current_node_packet(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="current-node packet relay requires a current packet-ledger check",
        verify_after_request=True,
    )
    frontier = router._active_frontier(run_root)
    router._require_clean_self_interrogation(
        project_root,
        run_root,
        gate_name="current-node packet relay",
        scopes=("node_entry",),
        node_id=str(frontier["active_node_id"]),
        route_version=int(frontier.get("route_version") or 0),
    )
    records = router._current_node_packet_records(project_root, run_state)
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = router.packet_runtime.load_envelope(project_root, envelope_path)
        audit = router.packet_runtime.validate_packet_ready_for_direct_relay(
            project_root,
            packet_envelope=envelope,
            envelope_path=envelope_path,
        )
        if not audit.get("passed"):
            raise router.RouterError(f"current-node packet envelope is not ready for direct relay: {audit.get('blockers')}")
        router._ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get("node_id") or ""))
        router.packet_runtime.controller_relay_envelope(
            project_root,
            envelope=envelope,
            envelope_path=envelope_path,
            controller_agent_id="controller",
            received_from_role=str(envelope.get("from_role") or "project_manager"),
            relayed_to_role=str(envelope.get("to_role")),
        )
    lease_summary = router._issue_current_node_active_holder_leases(project_root, run_root, run_state, records)
    router._mark_parallel_batch_packets_relayed(run_root, "current_node")
    run_state["flags"]["current_node_packet_relayed"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome(result_extra={"active_holder_fast_lane": lease_summary})

def _apply_relay_current_node_result(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
    payload: dict[str, Any] | None,
) -> ActionHandlerOutcome:
    del payload
    _request_ledger_check(
        router,
        run_state,
        pending,
        error_message="current-node result relay requires a current packet-ledger check",
    )
    if not run_state["flags"].get("current_node_worker_result_returned"):
        raise router.RouterError("current-node result relay requires worker result event")
    records = router._current_node_packet_records(project_root, run_state)
    router._validate_results_exist_for_packets(project_root, run_state, records, next_recipient="project_manager")
    router._relay_result_records(project_root, run_state, records, to_role="project_manager", controller_agent_id="controller")
    batch = router._active_parallel_packet_batch(run_root, "current_node")
    if batch:
        batch["status"] = "results_relayed_to_pm"
        router._write_parallel_packet_batch_state(run_root, batch)
    run_state["flags"]["current_node_result_relayed_to_pm"] = True
    run_state["ledger_check_requested"] = False
    return ActionHandlerOutcome()

__all__ = (
    '_apply_relay_material_scan_packets',
    '_apply_relay_material_scan_results',
    '_apply_relay_research_packet',
    '_apply_relay_research_result',
    '_apply_relay_pm_role_work_request_packet',
    '_apply_relay_pm_role_work_result_to_pm',
    '_apply_enter_next_child_node',
    '_apply_relay_current_node_packet',
    '_apply_relay_current_node_result',
)
