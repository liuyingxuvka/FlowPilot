"""Reconciliation and ACK-preflight helpers for router action construction.

This child module is bound to the router facade before execution so moved
helpers can keep using router-owned state readers and current public exports.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_router_card_returns
from flowpilot_router_protocol_dispatch_policy import FORMAL_WORK_PACKET_RELAY_ACTION_TYPES
from flowpilot_router_protocol_catalog import *

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


OWNER_MODULE = "flowpilot_router_action_factory_reconciliation"


def _current_scope_pre_review_reconciliation_action(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    blockers: list[dict[str, Any]],
    review_trigger: str,
) -> dict[str, Any]:
    scope_kind = "startup" if any(blocker.get("scope_kind") == "startup" for blocker in blockers) else "current_node"
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    if scope_kind == "current_node":
        frontier = _active_frontier(run_root)
    active_node_id = str(frontier.get("active_node_id") or "")
    scope_id = "startup" if scope_kind == "startup" else active_node_id
    label = (
        "controller_waits_for_startup_scope_pre_review_reconciliation"
        if scope_kind == "startup"
        else "controller_waits_for_current_scope_pre_review_reconciliation"
    )
    summary = (
        "Startup reviewer work is blocked until startup-local obligations are reconciled."
        if scope_kind == "startup"
        else "Current-node reviewer work is blocked until local node obligations are reconciled."
    )
    allowed_reads = [
        project_relative(project_root, run_state_path(run_root)),
        project_relative(project_root, run_root / "execution_frontier.json"),
        project_relative(project_root, run_root / "return_event_ledger.json"),
        project_relative(project_root, _controller_action_ledger_path(run_root)),
        project_relative(project_root, _router_scheduler_ledger_path(run_root)),
    ]
    if scope_kind == "current_node":
        allowed_reads.append(project_relative(project_root, _parallel_packet_batch_ref_path(run_root, "current_node")))
    return _bound_router().make_action(
        action_type="await_current_scope_reconciliation",
        actor="controller",
        label=label,
        summary=summary,
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role="controller",
        extra={
            "apply_required": False,
            "scope_kind": scope_kind,
            "scope_id": scope_id,
            "route_id": frontier.get("active_route_id"),
            "route_version": frontier.get("route_version"),
            "review_trigger": review_trigger,
            "blockers": blockers,
            "local_scope_only": True,
            "future_or_sibling_scopes_touched": False,
            "reconciliation_rule": "resolve_or_explicitly_classify_current_scope_obligations_before_reviewer_work",
        },
    )


def _current_scope_reconciliation_wait_still_blocked(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
) -> bool:
    return flowpilot_router_card_returns._current_scope_reconciliation_wait_still_blocked(_bound_router(), project_root, run_root, run_state, pending_action)


def _next_local_obligation_before_passive_wait(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._next_local_obligation_before_passive_wait(_bound_router(), project_root, run_root, run_state, pending_action)


def _current_node_scope_exit_reconciliation_blockers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    frontier: dict[str, Any],
) -> list[dict[str, Any]]:
    return flowpilot_router_card_returns._current_node_scope_exit_reconciliation_blockers(_bound_router(), project_root, run_root, run_state, frontier)


def _action_is_startup_async_delivery(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_card_returns._action_is_startup_async_delivery(_bound_router(), action)


def _action_is_startup_async_card_wait(action: dict[str, Any] | None) -> bool:
    return flowpilot_router_card_returns._action_is_startup_async_card_wait(_bound_router(), action)


def _startup_async_pending_returns(
    run_root: Path,
    pending_returns: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return flowpilot_router_card_returns._startup_async_pending_returns(_bound_router(), run_root, pending_returns)


def _pending_card_return_blocker_for_event(
    run_root: Path,
    run_id: str,
    event: str,
    run_state: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._pending_card_return_blocker_for_event(_bound_router(), run_root, run_id, event, run_state)


def _committed_card_artifact_extra(
    project_root: Path,
    record: dict[str, Any],
    *,
    relay_allowed_if_ready: bool,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._committed_card_artifact_extra(_bound_router(), project_root, record, relay_allowed_if_ready=relay_allowed_if_ready)


def _next_pending_card_return_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending_records: list[dict[str, Any]] | None = None,
    *,
    clearance_reason: str = "router_progress",
) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._next_pending_card_return_action(_bound_router(), project_root, run_state, run_root, pending_records, clearance_reason=clearance_reason)


def _roles_from_action_to_role(action: dict[str, Any]) -> set[str]:
    raw = str(action.get("to_role") or "")
    roles = {role.strip() for role in raw.split(",") if role.strip()}
    return roles


def _apply_formal_work_packet_ack_preflight(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    if action.get("action_type") not in FORMAL_WORK_PACKET_RELAY_ACTION_TYPES:
        return action
    target_roles = _roles_from_action_to_role(action)
    if not target_roles:
        return action
    pending = [
        record
        for record in _pending_return_records(run_root, str(run_state["run_id"]))
        if str(record.get("target_role") or "") in target_roles
    ]
    preflight = {
        "schema_version": "flowpilot.formal_work_packet_ack_preflight.v1",
        "target_roles": sorted(target_roles),
        "source_ledger_path": project_relative(project_root, _return_event_ledger_path(run_root)),
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
    if pending:
        wait_action = _next_pending_card_return_action(
            project_root,
            run_state,
            run_root,
            pending,
            clearance_reason="formal_work_packet_preflight",
        )
        if wait_action is None:
            return action
        blocked_packet = {
            "action_type": action.get("action_type"),
            "label": action.get("label"),
            "to_role": action.get("to_role"),
            "target_roles": sorted(target_roles),
        }
        wait_action["blocked_formal_work_packet"] = blocked_packet
        wait_action["formal_work_packet_ack_preflight"] = {
            **preflight,
            "passed": False,
            "pending_return_count": len(pending),
            "blocked_packet": blocked_packet,
        }
        wait_action["next_step_contract"]["formal_work_packet_ack_preflight"] = wait_action[
            "formal_work_packet_ack_preflight"
        ]
        return wait_action
    action["formal_work_packet_ack_preflight"] = {
        **preflight,
        "passed": True,
        "pending_return_count": 0,
    }
    action["ack_is_read_receipt_only"] = True
    action["target_work_completion_evidence_required_separately"] = True
    action["next_step_contract"]["formal_work_packet_ack_preflight"] = action["formal_work_packet_ack_preflight"]
    action["next_step_contract"]["ack_is_read_receipt_only"] = True
    action["next_step_contract"]["target_work_completion_evidence_required_separately"] = True
    return action


__all__ = (
    "_current_scope_pre_review_reconciliation_action",
    "_current_scope_reconciliation_wait_still_blocked",
    "_next_local_obligation_before_passive_wait",
    "_current_node_scope_exit_reconciliation_blockers",
    "_action_is_startup_async_delivery",
    "_action_is_startup_async_card_wait",
    "_startup_async_pending_returns",
    "_pending_card_return_blocker_for_event",
    "_committed_card_artifact_extra",
    "_next_pending_card_return_action",
    "_roles_from_action_to_role",
    "_apply_formal_work_packet_ack_preflight",
)

_LOCAL_NAMES = set(globals())
