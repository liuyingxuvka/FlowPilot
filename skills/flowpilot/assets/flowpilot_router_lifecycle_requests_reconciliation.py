"""Terminal lifecycle reconciliation helpers for FlowPilot router lifecycle requests."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_lifecycle_requests_terminal_quarantine import (
    clear_active_repair_transaction_for_terminal_lifecycle,
    quarantine_duplicate_role_events_for_terminal_lifecycle,
    quarantine_material_progress_for_terminal_lifecycle,
    quarantine_packet_result_authority_for_terminal_lifecycle,
)


_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


def _clear_active_control_blocker_for_terminal_lifecycle(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
    cleared_at: str,
) -> dict[str, Any] | None:
    active = run_state.get("active_control_blocker")
    if not isinstance(active, dict):
        return None
    blocker_id = str(active.get("blocker_id") or "")
    if not blocker_id:
        run_state["active_control_blocker"] = None
        run_state["latest_control_blocker_path"] = None
        return {"authority": "control_blocker", "status": "cleared_missing_blocker_id"}
    resolved = dict(active)
    resolved["resolution_status"] = "superseded_by_terminal_lifecycle"
    resolved["resolved_by_event"] = event
    resolved["resolved_at"] = cleared_at
    resolved["terminal_lifecycle_status"] = mode
    existing = run_state.get("resolved_control_blockers")
    if not isinstance(existing, list):
        existing = []
        run_state["resolved_control_blockers"] = existing
    if not any(isinstance(item, dict) and item.get("blocker_id") == blocker_id for item in existing):
        existing.append(resolved)
    artifact_path = resolve_project_path(project_root, str(active.get("blocker_artifact_path") or ""))
    if artifact_path.exists():
        record = read_json(artifact_path)
        record["resolution_status"] = "superseded_by_terminal_lifecycle"
        record["resolved_by_event"] = event
        record["resolved_at"] = cleared_at
        record["terminal_lifecycle_status"] = mode
        write_json(artifact_path, record)
    run_state["active_control_blocker"] = None
    run_state["latest_control_blocker_path"] = None
    _sync_control_plane_indexes(project_root, run_root, run_state)
    return {
        "authority": "control_blocker",
        "blocker_id": blocker_id,
        "resolution_status": "superseded_by_terminal_lifecycle",
    }


def _reconcile_terminal_lifecycle_authorities(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    mode: str,
    event: str,
) -> dict[str, Any]:
    reconciled_at = utc_now()
    receipts: list[dict[str, Any]] = []
    source_paths: dict[str, str] = {}

    continuation_path = _continuation_binding_path(run_root)
    if continuation_path.exists():
        continuation = read_json(continuation_path)
        source_paths["continuation_binding"] = project_relative(project_root, continuation_path)
        previous_heartbeat_active = bool(continuation.get("heartbeat_active"))
        automation_id = str(continuation.get("host_automation_id") or "")
        automation_path = Path.home() / ".codex" / "automations" / automation_id / "automation.toml" if automation_id else None
        automation_exists = bool(automation_path and automation_path.exists())
        if automation_id and not automation_exists:
            cleanup_status = "missing_verified"
        elif automation_id and previous_heartbeat_active:
            cleanup_status = "external_cleanup_may_be_required"
        else:
            cleanup_status = "inactive_verified"
        continuation["heartbeat_active"] = False
        continuation["lifecycle_status"] = mode
        continuation["terminal_event"] = event
        continuation["terminal_reconciled_at"] = reconciled_at
        continuation["host_automation_cleanup_status"] = cleanup_status
        continuation["host_automation_toml_exists"] = automation_exists if automation_id else None
        continuation["host_automation_checked_path"] = str(automation_path) if automation_path else None
        write_json(continuation_path, continuation)
        receipts.append(
            {
                "authority": "continuation_binding",
                "path": project_relative(project_root, continuation_path),
                "previous_heartbeat_active": previous_heartbeat_active,
                "heartbeat_active": False,
                "host_automation_cleanup_status": continuation["host_automation_cleanup_status"],
                "host_automation_toml_exists": continuation["host_automation_toml_exists"],
            }
        )

    crew_path = run_root / "crew_ledger.json"
    if crew_path.exists():
        crew = read_json(crew_path)
        source_paths["crew_ledger"] = project_relative(project_root, crew_path)
        role_slots = crew.get("role_slots") if isinstance(crew.get("role_slots"), list) else []
        live_before = sum(1 for slot in role_slots if isinstance(slot, dict) and str(slot.get("status") or "").startswith("live_"))
        for slot in role_slots:
            if isinstance(slot, dict):
                slot["status"] = "stopped_with_run"
                slot["live_agent_active"] = False
                slot["stopped_at"] = reconciled_at
        crew["lifecycle_status"] = mode
        crew["terminal_reconciled_at"] = reconciled_at
        write_json(crew_path, crew)
        receipts.append(
            {
                "authority": "crew_ledger",
                "path": project_relative(project_root, crew_path),
                "live_role_slots_before": live_before,
                "live_role_slots_after": 0,
            }
        )

    packet_ledger_path = run_root / "packet_ledger.json"
    if packet_ledger_path.exists():
        packet_ledger = read_json(packet_ledger_path)
        source_paths["packet_ledger"] = project_relative(project_root, packet_ledger_path)
        previous_status = packet_ledger.get("active_packet_status")
        previous_holder = packet_ledger.get("active_packet_holder")
        packet_ledger["active_packet_status"] = mode
        packet_ledger["active_packet_holder"] = "controller"
        packet_ledger["terminal_lifecycle"] = {
            "status": mode,
            "event": event,
            "previous_active_packet_status": previous_status,
            "previous_active_packet_holder": previous_holder,
            "controller_may_continue_packet_loop": False,
            "reconciled_at": reconciled_at,
        }
        packet_ledger["updated_at"] = reconciled_at
        write_json(packet_ledger_path, packet_ledger)
        receipts.append(
            {
                "authority": "packet_ledger",
                "path": project_relative(project_root, packet_ledger_path),
                "previous_active_packet_status": previous_status,
                "active_packet_status": mode,
            }
        )

    frontier_path = run_root / "execution_frontier.json"
    if frontier_path.exists():
        frontier = read_json(frontier_path)
        source_paths["execution_frontier"] = project_relative(project_root, frontier_path)
        previous_status = frontier.get("status")
        frontier["status"] = mode
        frontier["phase"] = "terminal"
        frontier["terminal"] = True
        frontier["terminal_event"] = event
        frontier["updated_at"] = reconciled_at
        frontier["source"] = event
        write_json(frontier_path, frontier)
        receipts.append(
            {
                "authority": "execution_frontier",
                "path": project_relative(project_root, frontier_path),
                "previous_status": previous_status,
                "status": mode,
            }
        )

    blocker_receipt = _clear_active_control_blocker_for_terminal_lifecycle(
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
        cleared_at=reconciled_at,
    )
    if blocker_receipt:
        receipts.append(blocker_receipt)
    router = _bound_router()
    repair_receipt = clear_active_repair_transaction_for_terminal_lifecycle(
        router,
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
        cleared_at=reconciled_at,
    )
    if repair_receipt:
        receipts.append(repair_receipt)
    material_receipt = quarantine_material_progress_for_terminal_lifecycle(
        router,
        project_root,
        run_root,
        run_state,
        mode=mode,
        event=event,
        reconciled_at=reconciled_at,
    )
    if material_receipt:
        receipts.append(material_receipt)
    role_event_receipt = quarantine_duplicate_role_events_for_terminal_lifecycle(
        run_state,
        mode=mode,
        event=event,
        reconciled_at=reconciled_at,
    )
    if role_event_receipt:
        receipts.append(role_event_receipt)
    packet_authority_receipt = quarantine_packet_result_authority_for_terminal_lifecycle(
        router,
        project_root,
        run_root,
        mode=mode,
        event=event,
        reconciled_at=reconciled_at,
    )
    if packet_authority_receipt:
        receipts.append(packet_authority_receipt)

    report = {
        "schema_version": "flowpilot.terminal_lifecycle_reconciliation.v1",
        "run_id": run_state.get("run_id"),
        "status": mode,
        "event": event,
        "controller_may_continue_route_work": False,
        "controller_may_spawn_new_role_work": False,
        "cleanup_receipts": receipts,
        "source_paths": source_paths,
        "reconciled_at": reconciled_at,
    }
    write_json(run_root / "lifecycle" / "terminal_reconciliation.json", report)
    report["reconciliation_path"] = project_relative(project_root, run_root / "lifecycle" / "terminal_reconciliation.json")
    return report


__all__ = (
    "_clear_active_control_blocker_for_terminal_lifecycle",
    "_reconcile_terminal_lifecycle_authorities",
)


_LOCAL_NAMES = set(globals())
