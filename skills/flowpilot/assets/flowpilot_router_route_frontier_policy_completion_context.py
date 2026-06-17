"""Legal next-action and parent child-entry helpers for route-frontier policy."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

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


def _legal_next_action_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    policy_by_id = router._route_action_policy_by_id(run_root)
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    active_node_id = str(frontier["active_node_id"])
    active_node = router._active_node_definition_from_route(route, active_node_id)
    child_ids = router._node_child_ids(active_node)
    descendants = router._route_descendant_node_ids(route, active_node_id)
    completed_nodes = {str(item) for item in frontier.get("completed_nodes") or []}
    descendant_ledgers = [router._node_completion_ledger_current(project_root, run_root, run_state, frontier, node_id) for node_id in descendants]
    descendants_in_frontier = all((node_id in completed_nodes for node_id in descendants))
    descendant_ledgers_current = all((bool(item.get("current")) for item in descendant_ledgers))
    child_chain_closed_current = bool(descendants) and descendants_in_frontier and descendant_ledgers_current
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    active_node_kind = router._node_kind(active_node)
    is_parent_scope = active_node_kind in {"parent", "module"} or bool(child_ids)
    legal_ids: list[str] = []
    reasons: list[str] = []

    def add(action_id: str) -> None:
        if action_id not in policy_by_id:
            reasons.append(f"policy_missing:{action_id}")
            return
        if action_id not in legal_ids:
            legal_ids.append(action_id)

    if is_parent_scope:
        if not child_chain_closed_current:
            reasons.append("child_chain_not_closed_current")
            if child_ids:
                add("enter_next_child")
            add("continue_current_child")
            if flags.get("parent_backward_replay_blocked") or flags.get("node_review_blocked") or flags.get("node_acceptance_plan_review_blocked"):
                add("request_child_repair")
                if flags.get("model_miss_triage_closed"):
                    add("mutate_route")
        elif flags.get("parent_backward_replay_blocked"):
            if flags.get("model_miss_triage_closed"):
                add("mutate_route")
            else:
                add("request_child_repair")
        elif not flags.get("parent_backward_targets_built"):
            add("build_parent_backward_targets")
        elif not flags.get("parent_backward_replay_passed"):
            add("review_parent_backward_replay")
        elif not flags.get("parent_segment_decision_recorded"):
            add("record_parent_segment_decision")
        elif router._parent_segment_decision_value(run_root, frontier) == "continue" and active_node_id not in completed_nodes:
            add("complete_parent_node")
    elif flags.get("node_review_blocked") or flags.get("node_acceptance_plan_review_blocked"):
        add("request_child_repair")
        if flags.get("model_miss_triage_closed"):
            add("mutate_route")
    elif not flags.get("current_node_result_returned"):
        add("continue_current_child")
    elif not flags.get("current_node_result_relayed_to_pm"):
        add("wait_for_child_result")
    else:
        add("continue_current_child")
    final_ledger_path = run_root / "final_route_wide_gate_ledger.json"
    terminal_replay_path = run_root / "reviews" / "terminal_backward_replay.json"
    completion_projection_path = _task_completion_projection_path(run_root)
    if flags.get("final_ledger_built_clean") and flags.get("final_backward_replay_passed") and final_ledger_path.exists() and terminal_replay_path.exists() and completion_projection_path.exists():
        projection = read_json_if_exists(completion_projection_path)
        if projection.get("task_status") == "ready_for_pm_terminal_closure":
            add("terminal_closure")
    parent_actions_illegal = sorted(ROUTE_ACTION_POLICY_PARENT_CLOSURE_ACTIONS - set(legal_ids))
    route_authority_snapshot = router._route_authority_snapshot(
        project_root,
        run_root,
        policy_by_id=policy_by_id,
        frontier=frontier,
        active_node_kind=active_node_kind,
        legal_ids=legal_ids,
        blocking_reasons=reasons,
    )
    return {
        "schema_version": "flowpilot.legal_next_action_context.v1",
        "source": "router",
        "route_action_policy_registry": project_relative(project_root, router._route_action_policy_registry_path(run_root)),
        "active_route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "active_node_id": active_node_id,
        "active_node_kind": active_node_kind,
        "active_node_has_children": bool(child_ids),
        "direct_child_node_ids": child_ids,
        "descendant_node_ids": descendants,
        "completed_node_ids": sorted(completed_nodes),
        "descendant_completion_ledgers": descendant_ledgers,
        "child_chain_closed_current": child_chain_closed_current,
        "legal_action_ids": legal_ids,
        "legal_next_actions": route_authority_snapshot["legal_next_actions"],
        "illegal_parent_closure_action_ids": parent_actions_illegal,
        "blocking_reasons": reasons,
        "pm_may_choose_only_from_legal_next_actions": True,
        "controller_may_advance_or_close_route": False,
        "route_authority_snapshot": route_authority_snapshot,
        "current_owner": route_authority_snapshot["current_owner"],
        "current_owner_roles": route_authority_snapshot["current_owner_roles"],
        "current_state_family": route_authority_snapshot["current_state_family"],
        "forbidden_action_ids": route_authority_snapshot["forbidden_action_ids"],
        "required_repair_command": route_authority_snapshot["required_repair_command"],
        "single_authority": route_authority_snapshot["single_authority"],
        "fallback_or_alias_translation_allowed": False,
    }


def _legal_next_action_ids(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> set[str]:
    _bind_router(router)
    context = router._legal_next_action_context(project_root, run_root, run_state)
    return {str(item) for item in context.get("legal_action_ids", [])}


def _legal_route_action_allowed(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str) -> bool:
    _bind_router(router)
    return str(action_id) in router._legal_next_action_ids(project_root, run_root, run_state)


def _first_incomplete_child_node_id(router: ModuleType, route: dict[str, Any], parent_node: dict[str, Any], completed_nodes: set[str]) -> str | None:
    _bind_router(router)
    node_by_id = router._route_node_map(route)
    for child_id in router._node_child_ids(parent_node):
        child = node_by_id.get(str(child_id))
        if child is None:
            continue
        if str(child_id) not in completed_nodes:
            return str(child_id)
    return None


def _enter_next_child_node(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending_action: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    router._require_legal_route_action(project_root, run_root, run_state, "enter_next_child", "parent/module child entry")
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    parent_node_id = str(frontier["active_node_id"])
    if str(pending_action.get("parent_node_id") or "") != parent_node_id:
        raise RouterError("parent/module child entry parent_node_id no longer matches active frontier")
    parent_node = router._active_node_definition_from_route(route, parent_node_id)
    if router._node_kind(parent_node) not in {"parent", "module"} and (not router._node_child_ids(parent_node)):
        raise RouterError("parent/module child entry requires active parent or module node")
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    review_path = _active_node_root(run_root, frontier) / "reviews" / "node_acceptance_plan_review.json"
    if not plan_path.exists() or not review_path.exists():
        raise RouterError("parent/module child entry requires node acceptance plan and reviewer pass")
    review = read_json(review_path)
    if review.get("passed") is not True:
        raise RouterError("parent/module child entry requires reviewer-passed node acceptance plan")
    completed_nodes = {str(item) for item in frontier.get("completed_nodes") or []}
    next_child_id = router._first_incomplete_child_node_id(route, parent_node, completed_nodes)
    if not next_child_id:
        raise RouterError("parent/module child entry requires an incomplete direct child")
    if str(pending_action.get("next_child_node_id") or "") != next_child_id:
        raise RouterError("parent/module child entry next_child_node_id no longer matches route order")
    next_child = router._active_node_definition_from_route(route, next_child_id)
    _reset_flags(run_state, CURRENT_NODE_CYCLE_FLAGS)
    frontier.update(
        {
            "schema_version": "flowpilot.execution_frontier.v1",
            "run_id": run_state["run_id"],
            "status": "current_node_loop",
            "active_node_id": next_child_id,
            "active_path": router._route_active_path(route, next_child_id),
            "active_leaf_node_id": next_child_id if router._node_kind(next_child) in {"leaf", "repair"} else None,
            "parent_entered_from_node_id": parent_node_id,
            "updated_at": utc_now(),
            "source": "controller_enters_next_child_node",
        }
    )
    write_json(run_root / "execution_frontier.json", frontier)
    router._write_display_plan_from_route(
        project_root,
        run_root,
        run_state,
        route_id=str(frontier["active_route_id"]),
        route_version=int(frontier.get("route_version") or 0),
        route_payload=route,
        active_node_id=next_child_id,
        source_event="controller_enters_next_child_node",
    )
    return {
        "parent_node_id": parent_node_id,
        "next_child_node_id": next_child_id,
        "next_child_node_kind": router._node_kind(next_child),
        "controller_may_advance_or_close_route": False,
    }


def _next_parent_child_entry_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    if not flags.get("node_acceptance_plan_reviewer_passed"):
        return None
    try:
        legal_context = router._legal_next_action_context(project_root, run_root, run_state)
    except RouterError:
        return None
    if "enter_next_child" not in {str(item) for item in legal_context.get("legal_action_ids", [])}:
        return None
    frontier = router._active_frontier(run_root)
    route = router._active_route_flow(run_root, frontier)
    parent_node_id = str(frontier["active_node_id"])
    parent_node = router._active_node_definition_from_route(route, parent_node_id)
    completed_nodes = {str(item) for item in frontier.get("completed_nodes") or []}
    next_child_id = router._first_incomplete_child_node_id(route, parent_node, completed_nodes)
    if not next_child_id:
        return None
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    review_path = _active_node_root(run_root, frontier) / "reviews" / "node_acceptance_plan_review.json"
    if not plan_path.exists() or not review_path.exists():
        return None
    return make_action(
        action_type="enter_next_child_node",
        actor="controller",
        label="controller_enters_next_child_node",
        summary="Router-authorized transition from an accepted parent/module node to its first incomplete direct child without dispatching parent work.",
        allowed_reads=[
            project_relative(project_root, run_root / "execution_frontier.json"),
            project_relative(project_root, router._active_route_path(run_root, frontier)),
            project_relative(project_root, plan_path),
            project_relative(project_root, review_path),
            project_relative(project_root, router._route_action_policy_registry_path(run_root)),
        ],
        allowed_writes=[
            project_relative(project_root, run_root / "execution_frontier.json"),
            project_relative(project_root, router.run_state_path(run_root)),
            project_relative(project_root, router._display_plan_path(run_root)),
            project_relative(project_root, router._route_state_snapshot_path(run_root)),
            project_relative(project_root, router._current_status_summary_path(run_root)),
        ],
        extra={
            "postcondition": "frontier_active_node_entered_child",
            "route_action_id": "enter_next_child",
            "parent_node_id": parent_node_id,
            "next_child_node_id": next_child_id,
            "legal_next_actions": legal_context,
            "controller_may_dispatch_parent_work": False,
            "controller_may_advance_or_close_route": False,
        },
    )


def _require_legal_route_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action_id: str, context: str) -> None:
    _bind_router(router)
    legal_context = router._legal_next_action_context(project_root, run_root, run_state)
    legal_ids = {str(item) for item in legal_context.get("legal_action_ids", [])}
    if str(action_id) in legal_ids:
        return
    reason_items = [str(item) for item in legal_context.get("blocking_reasons", []) if item]
    reasons = ", ".join(reason_items) or "not in legal_next_actions"
    if str(action_id) == "mutate_route" and "child_chain_not_closed_current" in reason_items and ("pm_mutates_route_after_review_block" in str(context)):
        reasons = f"{reasons}; replanning required before route mutation, not repair node"
    router._reject_route_authority_submission(
        project_root,
        run_root,
        run_state,
        rejected_action_id=str(action_id),
        context=context,
        rejected_event=str(context).replace("external event ", "") if str(context).startswith("external event ") else None,
        rejection_kind="wrong_path",
    )


def _filter_events_by_legal_route_actions(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], events: list[str]) -> list[str]:
    _bind_router(router)
    if not any((router._route_action_for_event(event) for event in events)):
        return events
    legal_ids = router._legal_next_action_ids(project_root, run_root, run_state)
    return [event for event in events if router._route_action_for_event(event) is None or router._route_action_for_event(event) in legal_ids]


__all__ = (
    "_legal_next_action_context",
    "_legal_next_action_ids",
    "_legal_route_action_allowed",
    "_first_incomplete_child_node_id",
    "_enter_next_child_node",
    "_next_parent_child_entry_action",
    "_require_legal_route_action",
    "_filter_events_by_legal_route_actions",
)


_LOCAL_NAMES = set(globals())
