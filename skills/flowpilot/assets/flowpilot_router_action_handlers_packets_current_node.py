"""Current-node packet relay action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_basic import _request_ledger_check
from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome

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
    '_apply_enter_next_child_node',
    '_apply_relay_current_node_packet',
    '_apply_relay_current_node_result',
)
