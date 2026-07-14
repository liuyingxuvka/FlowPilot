"""Fresh-action provider for FlowPilot router actions."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_providers_common import ProviderOutcome


def fresh_action_provider(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> ProviderOutcome | None:
    if not router._route_memory_ready(run_root, run_state):
        router._refresh_route_memory(project_root, run_root, run_state, trigger="router_next_action")

    action = router._next_role_recovery_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_resume_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_control_blocker_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_display_plan_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_controller_boundary_confirmation_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_startup_mechanical_audit_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_startup_display_action(project_root, run_state, run_root)
    startup_deferred_returns: list[dict[str, Any]] = []
    if action is None:
        router._invalidate_route_completion_if_dirty_before_closure(project_root, run_state, run_root)
        pending_returns = router._pending_return_records(run_root, str(run_state["run_id"]))
        startup_deferred_returns, blocking_returns = router._startup_async_pending_returns(run_root, pending_returns)
        if blocking_returns:
            action = router._next_pending_card_return_action(project_root, run_state, run_root, blocking_returns)
    if action is None:
        candidate = router._next_system_card_bundle_action(project_root, run_state, run_root)
        if candidate is not None and (not startup_deferred_returns or router._action_is_startup_async_delivery(candidate)):
            action = candidate
    if action is None:
        candidate = router._next_system_card_action(project_root, run_state, run_root)
        if candidate is not None and (not startup_deferred_returns or router._action_is_startup_async_delivery(candidate)):
            action = candidate
    if action is None and startup_deferred_returns:
        clearance_reason = (
            "current_scope_pre_review_reconciliation"
            if any(router._pending_return_is_pre_review_startup_scope(record) for record in startup_deferred_returns)
            and not router._startup_pre_review_ack_join_clean(run_root, run_state)
            else "router_progress"
        )
        action = router._next_pending_card_return_action(
            project_root,
            run_state,
            run_root,
            startup_deferred_returns,
            clearance_reason=clearance_reason,
        )
    if isinstance(action, dict) and action.get("action_type") == "deliver_system_card":
        gated_action = router._apply_dispatch_recipient_gate(project_root, run_state, run_root, action)
        if gated_action.get("action_type") != "deliver_system_card":
            run_state["pending_action"] = gated_action
            router.save_run_state(run_root, run_state)
            return ProviderOutcome(gated_action, finalized=True)
        return ProviderOutcome(
            router._auto_commit_system_card_delivery_action(project_root, run_state, run_root, action),
            finalized=True,
        )
    if isinstance(action, dict) and action.get("action_type") == "deliver_system_card_bundle":
        gated_action = router._apply_dispatch_recipient_gate(project_root, run_state, run_root, action)
        if gated_action.get("action_type") != "deliver_system_card_bundle":
            run_state["pending_action"] = gated_action
            router.save_run_state(run_root, run_state)
            return ProviderOutcome(gated_action, finalized=True)
        return ProviderOutcome(
            router._auto_commit_system_card_bundle_delivery_action(project_root, run_state, run_root, action),
            finalized=True,
        )
    if action is None and router._resume_waits_for_pm_decision(run_state):
        action = router._expected_role_decision_wait_action(
            project_root,
            run_state,
            run_root,
            label="controller_waits_for_pm_resume_decision",
            summary="Resume state has been loaded and resume cards delivered. Controller must wait for PM resume decision before continuing any route, mail, or packet work.",
            allowed_external_events=["pm_resume_recovery_decision_returned"],
            to_role="project_manager",
            allowed_reads_extra=[
                router.project_relative(project_root, run_root / "continuation" / "resume_reentry.json"),
            ],
            payload_contract=router._pm_resume_decision_payload_contract(project_root, run_root),
            pm_work_request_channel=False,
        )
    if action is None:
        action = router._next_mail_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_research_packet_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_parent_child_entry_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_current_node_packet_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_pm_role_work_request_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_model_miss_followup_request_wait_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_model_miss_controlled_stop_action(project_root, run_state, run_root)
    if action is None:
        action = router._next_expected_role_decision_wait_action(project_root, run_state, run_root)
    if action is None:
        router._write_control_blocker(
            project_root,
            run_root,
            run_state,
            source="router_no_legal_next_action",
            error_message=(
                "Controller has no legal next action; PM repair or routing decision is required before any "
                "further route, mail, packet, or project work."
            ),
            action_type="controller_no_legal_next_action",
            payload={
                "path": router.project_relative(project_root, router.run_state_path(run_root)),
                "role": "controller",
            },
        )
        action = router._next_control_blocker_action(project_root, run_state, run_root)
        if action is None:
            raise router.RouterError("no legal next action control blocker was not materialized")
    return ProviderOutcome(action, finalized=False)
