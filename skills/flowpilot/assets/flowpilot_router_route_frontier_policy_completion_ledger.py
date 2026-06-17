"""Node-completion ledger and frontier commit helpers for route-frontier policy."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_errors import RouterError

_BOUND_ROUTER: ModuleType | None = None


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


def _write_node_completion_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    frontier: dict[str, Any],
    *,
    completed_node_id: str,
    completed_nodes: list[str],
    next_node_id: str | None,
    source_event: str = "pm_completes_current_node_from_reviewed_result",
) -> Path:
    _bind_router(router)
    active_node_is_parent = router._active_node_has_children(run_root, frontier)
    packet_envelope: dict[str, Any] = {}
    result_envelope: dict[str, Any] = {}
    packet_envelope_path: Path | None = None
    result_envelope_path: Path | None = None
    if not active_node_is_parent:
        packet_envelope, packet_envelope_path = router._current_node_packet_context(project_root, run_state)
        result_envelope, result_envelope_path = router._current_node_result_context(project_root, run_state)
    audit_path = _active_node_root(run_root, frontier) / "reviews" / "current_node_packet_runtime_audit.json"
    ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    source_paths = {
        "execution_frontier_before_update": project_relative(project_root, run_root / "execution_frontier.json"),
        "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
    }
    if packet_envelope_path and result_envelope_path:
        source_paths.update(
            {
                "current_node_write_grant": project_relative(project_root, _active_node_write_grant_path(run_root, frontier)),
                "packet_envelope": project_relative(project_root, packet_envelope_path),
                "result_envelope": project_relative(project_root, result_envelope_path),
                "current_node_packet_runtime_audit": project_relative(project_root, audit_path),
            }
        )
    if active_node_is_parent:
        source_paths.update(
            {
                "parent_backward_replay": project_relative(project_root, _active_node_root(run_root, frontier) / "parent_backward_replay.json"),
                "pm_parent_segment_decision": project_relative(project_root, _active_node_root(run_root, frontier) / "pm_parent_segment_decision.json"),
            }
        )
    write_json(
        ledger_path,
        {
            "schema_version": "flowpilot.node_completion_ledger.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": completed_node_id,
            "completed_by_role": "project_manager",
            "reviewer_result_passed": True,
            "worker_result_packet_id": str(result_envelope.get("packet_id") or ""),
            "worker_result_completed_by_role": str(result_envelope.get("completed_by_role") or ""),
            "current_node_packet_id": str(packet_envelope.get("packet_id") or ""),
            "completion_source_event": source_event,
            "parent_backward_replay_completion": active_node_is_parent,
            "completed_nodes_after_update": completed_nodes,
            "next_node_id": next_node_id,
            "flowpilot_completable_work_closed": True,
            "human_inspection_notes_belong_in_final_report": True,
            "source_paths": source_paths,
            "completed_at": utc_now(),
        },
    )
    run_state["flags"]["node_completion_ledger_updated"] = True
    return ledger_path


def _mark_current_node_packet_records_completed(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    completed_node_id: str,
    completion_ledger_path: Path,
) -> None:
    _bind_router(router)
    try:
        records = router._current_node_packet_records(project_root, run_state)
    except RouterError:
        return
    completed_at = utc_now()
    for record in records:
        packet_id = str(record.get("packet_id") or "").strip()
        if not packet_id:
            continue
        packet_runtime._update_packet_record(
            project_root,
            run_root / "packet_ledger.json",
            packet_id,
            {
                "active_packet_status": "completed",
                "active_packet_holder": "closed",
                "flowpilot_work_completed": True,
                "completed_node_id": completed_node_id,
                "node_completion_ledger_path": project_relative(project_root, completion_ledger_path),
                "completed_by_flow_state": "pm_completes_current_node_from_reviewed_result",
                "completed_at": completed_at,
                "holder_history": {
                    "holder": "closed",
                    "status": "completed",
                    "changed_at": completed_at,
                    "source": "node_completion",
                    "node_id": completed_node_id,
                    "node_completion_ledger_path": project_relative(project_root, completion_ledger_path),
                },
            },
        )


def _mark_frontier_node_completed(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str = "pm_completes_current_node_from_reviewed_result",
) -> None:
    _bind_router(router)
    frontier = router._active_frontier(run_root)
    active_node_id = str(payload.get("node_id") or frontier.get("active_node_id") or "node-001")
    if active_node_id != str(frontier.get("active_node_id")):
        raise RouterError("completed node_id must match active frontier")
    if source_event == "pm_completes_current_node_from_reviewed_result":
        blockers = _current_node_scope_exit_reconciliation_blockers(project_root, run_root, run_state, frontier)
        if blockers:
            raise RouterError(
                "current-node completion requires local current-scope reconciliation before node exit: "
                + "; ".join((str(blocker.get("reason") or blocker.get("kind")) for blocker in blockers))
            )
    if router._active_node_has_children(run_root, frontier):
        if source_event == "pm_completes_parent_node_from_backward_replay":
            router._require_legal_route_action(project_root, run_root, run_state, "complete_parent_node", "parent node completion commit")
        replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
        decision_path = _active_node_root(run_root, frontier) / "pm_parent_segment_decision.json"
        missing = [project_relative(project_root, path) for path in (replay_path, decision_path) if not path.exists()]
        if missing:
            raise RouterError(f"parent node completion requires backward replay and PM segment decision: {', '.join(missing)}")
        if not run_state["flags"].get("parent_backward_replay_passed"):
            raise RouterError("parent node completion requires reviewer-passed parent backward replay")
        if not run_state["flags"].get("parent_segment_decision_recorded"):
            raise RouterError("parent node completion requires PM parent segment decision")
        decision = read_json(decision_path)
        if decision.get("decision") != "continue":
            raise RouterError("parent node completion requires PM parent segment decision=continue")
    completed = list(frontier.get("completed_nodes") or [])
    if active_node_id not in completed:
        completed.append(active_node_id)
    route = read_json_if_exists(router._active_route_path(run_root, frontier))
    mutations = read_json_if_exists(run_root / "routes" / str(frontier["active_route_id"]) / "mutations.json")
    next_node_id = router._next_effective_node_id(route, mutations, completed, active_node_id)
    completion_ledger_path = router._write_node_completion_ledger(
        project_root,
        run_root,
        run_state,
        frontier,
        completed_node_id=active_node_id,
        completed_nodes=completed,
        next_node_id=next_node_id,
        source_event=source_event,
    )
    if not router._active_node_has_children(run_root, frontier):
        router._mark_current_node_packet_records_completed(project_root, run_root, run_state, completed_node_id=active_node_id, completion_ledger_path=completion_ledger_path)
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "current_node_loop" if next_node_id else "node_completed_by_pm",
            "active_node_id": next_node_id or active_node_id,
            "active_path": router._route_active_path(route, next_node_id or active_node_id) if route else frontier.get("active_path", []),
            "active_leaf_node_id": next_node_id if next_node_id and route and (router._node_kind(router._active_node_definition_from_route(route, next_node_id)) in {"leaf", "repair"}) else None,
            "completed_nodes": completed,
            "latest_node_completion_ledger_path": project_relative(project_root, completion_ledger_path),
            "updated_at": utc_now(),
            "source": source_event,
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    if next_node_id:
        _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    if route:
        router._write_display_plan_from_route(
            project_root,
            run_root,
            run_state,
            route_id=str(frontier["active_route_id"]),
            route_version=int(frontier.get("route_version") or 0),
            route_payload=route,
            active_node_id=next_node_id,
            source_event=source_event,
        )


__all__ = (
    "_write_node_completion_ledger",
    "_mark_current_node_packet_records_completed",
    "_mark_frontier_node_completed",
)


_LOCAL_NAMES = set(globals())
