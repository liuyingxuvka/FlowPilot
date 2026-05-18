"""Lifecycle and reconciliation providers for FlowPilot router actions."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


def lifecycle_provider(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> dict[str, Any] | None:
    terminal_action = router._run_lifecycle_terminal_action(project_root, run_state, run_root)
    if terminal_action is None:
        return None
    run_state["pending_action"] = terminal_action
    router.append_history(
        run_state,
        "router_computed_terminal_lifecycle_action",
        {"action_type": terminal_action["action_type"]},
    )
    router.save_run_state(run_root, run_state)
    return terminal_action


def run_reconciliation_barrier(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> None:
    router._reconcile_controller_receipts(project_root, run_root, run_state)
    scheduled_reconciliation = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    receipt_reconciliation = router._reconcile_pending_controller_action_receipt(project_root, run_root, run_state)
    boundary_projection = router._reconcile_controller_boundary_confirmation_projection(
        project_root,
        run_root,
        run_state,
        source="next_action_reconciliation_barrier",
    )
    durable_reconciliation = router._reconcile_durable_wait_evidence(project_root, run_root, run_state)
    return_settlement = router._run_router_return_settlement_finalizers(
        project_root,
        run_root,
        run_state,
        source="compute_controller_action_return_settlement",
    )
    pending_action = run_state.get("pending_action")
    if (
        durable_reconciliation.get("changed")
        and isinstance(pending_action, dict)
        and pending_action.get("action_type") == "await_role_decision"
    ):
        run_state["pending_action"] = None
        router.append_history(
            run_state,
            "router_cleared_pending_role_wait_after_durable_reconciliation",
            {
                "label": pending_action.get("label"),
                "allowed_external_events": pending_action.get("allowed_external_events"),
            },
        )
        router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_durable_wait_reconciliation")
        router._sync_derived_run_views(
            project_root,
            run_root,
            run_state,
            reason="after_router_durable_wait_reconciliation",
            update_display=True,
        )
        router.save_run_state(run_root, run_state)
    elif (
        durable_reconciliation.get("changed")
        or receipt_reconciliation.get("changed")
        or scheduled_reconciliation.get("changed")
        or boundary_projection.get("changed")
        or return_settlement.get("changed")
    ):
        router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_durable_reconciliation_barrier")
        router._sync_derived_run_views(
            project_root,
            run_root,
            run_state,
            reason="after_router_durable_reconciliation_barrier",
            update_display=True,
        )
        router.save_run_state(run_root, run_state)
