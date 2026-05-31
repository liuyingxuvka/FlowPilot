"""PM role-work packet relay action handlers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_handlers_basic import _request_ledger_check
from flowpilot_router_action_handlers_packets_types import ActionHandlerOutcome

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
        router._record_flowguard_operator_lifecycle_status(
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
        router._record_flowguard_operator_lifecycle_status(
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

__all__ = (
    '_apply_relay_pm_role_work_request_packet',
    '_apply_relay_pm_role_work_result_to_pm',
)
