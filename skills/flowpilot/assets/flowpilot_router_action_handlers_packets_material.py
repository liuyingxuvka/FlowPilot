"""Material and research packet relay action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_basic import _request_ledger_check
from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome

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

__all__ = (
    '_apply_relay_material_scan_packets',
    '_apply_relay_material_scan_results',
    '_apply_relay_research_packet',
    '_apply_relay_research_result',
)
