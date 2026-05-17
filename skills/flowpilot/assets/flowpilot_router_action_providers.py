"""Controller-action provider orchestration for FlowPilot router.

The provider layer keeps `compute_controller_action` as an orchestration
surface while preserving the existing action priority order and state writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


ComputeAgain = Callable[[Path, dict[str, Any], Path, int], dict[str, Any]]


@dataclass(frozen=True)
class ProviderOutcome:
    action: dict[str, Any]
    finalized: bool = False


PROVIDER_ORDER = (
    "lifecycle",
    "pending_action",
    "role_recovery",
    "resume",
    "control_blocker",
    "startup_heartbeat",
    "display_plan",
    "controller_boundary",
    "startup_mechanical_audit",
    "startup_display",
    "pending_card_return",
    "system_card_bundle",
    "system_card",
    "resume_wait",
    "mail",
    "material_packet",
    "research_packet",
    "parent_child_entry",
    "current_node_packet",
    "pm_role_work_request",
    "model_miss_followup",
    "model_miss_controlled_stop",
    "expected_role_decision_wait",
    "no_legal_next_action_blocker",
)


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


def pending_action_provider(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    router_internal_depth: int,
    compute_again: ComputeAgain,
) -> dict[str, Any] | None:
    pending_action = run_state.get("pending_action")
    stale_pending = router._pending_role_decision_staleness(run_state, pending_action)
    reconciled_pending = None
    if stale_pending:
        run_state["pending_action"] = None
        router.append_history(run_state, "router_cleared_stale_pending_action", stale_pending)
        router.save_run_state(run_root, run_state)
    else:
        reconciled_pending = router._reconcile_pending_role_wait_from_packet_status(
            project_root,
            run_root,
            run_state,
            pending_action,
        )
        if reconciled_pending is not None:
            run_state["pending_action"] = None
            router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_reconciled_pending_role_wait")
            router._sync_derived_run_views(
                project_root,
                run_root,
                run_state,
                reason="after_router_reconciled_pending_role_wait",
                update_display=True,
            )
            router.save_run_state(run_root, run_state)

    pending_action = run_state.get("pending_action")
    if (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "deliver_system_card"
        and pending_action.get("artifact_committed") is not True
    ):
        gated_action = router._apply_dispatch_recipient_gate(project_root, run_state, run_root, pending_action)
        if gated_action.get("action_type") != "deliver_system_card":
            run_state["pending_action"] = gated_action
            router.save_run_state(run_root, run_state)
            return gated_action
        return router._auto_commit_system_card_delivery_action(project_root, run_state, run_root, pending_action)
    if (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "deliver_system_card_bundle"
        and pending_action.get("artifact_committed") is not True
    ):
        gated_action = router._apply_dispatch_recipient_gate(project_root, run_state, run_root, pending_action)
        if gated_action.get("action_type") != "deliver_system_card_bundle":
            run_state["pending_action"] = gated_action
            router.save_run_state(run_root, run_state)
            return gated_action
        return router._auto_commit_system_card_bundle_delivery_action(project_root, run_state, run_root, pending_action)
    if router._pending_card_return_ack_exists(project_root, pending_action):
        auto_ack = router._try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, pending_action)
        if auto_ack.get("consumed"):
            run_state["pending_action"] = None
            settlement_after_auto_ack = router._run_router_return_settlement_finalizers(
                project_root,
                run_root,
                run_state,
                source="after_router_auto_consumed_card_return_ack",
            )
            router.append_history(
                run_state,
                "router_auto_consumed_card_return_ack",
                {
                    "action_type": pending_action.get("action_type") if isinstance(pending_action, dict) else None,
                    "expected_return_path": pending_action.get("expected_return_path") if isinstance(pending_action, dict) else None,
                    "status": (auto_ack.get("result") or {}).get("status"),
                    "return_settlement": settlement_after_auto_ack,
                },
            )
            router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_auto_consumed_card_return_ack")
            router._sync_derived_run_views(
                project_root,
                run_root,
                run_state,
                reason="after_router_auto_consumed_card_return_ack",
                update_display=True,
            )
            router.save_run_state(run_root, run_state)
        elif auto_ack.get("preserve_pending"):
            router.append_history(run_state, "router_preserved_card_wait_before_artifact_commit", auto_ack)
            router.save_run_state(run_root, run_state)
            return pending_action
        else:
            run_state["pending_action"] = None
            router._mark_card_return_pending_explicit_check(
                run_root,
                str(run_state["run_id"]),
                pending_action,
                reason=str(auto_ack.get("reason") or "ack_requires_explicit_check"),
                error=auto_ack.get("error"),
            )
            router.append_history(
                run_state,
                "router_deferred_invalid_card_ack_to_explicit_check",
                {
                    "action_type": pending_action.get("action_type") if isinstance(pending_action, dict) else None,
                    "expected_return_path": pending_action.get("expected_return_path") if isinstance(pending_action, dict) else None,
                    "reason": auto_ack.get("reason"),
                    "error": auto_ack.get("error"),
                },
            )
            router.save_run_state(run_root, run_state)
        return None
    if not pending_action:
        return None

    if router._action_is_router_internal_mechanical(pending_action if isinstance(pending_action, dict) else None):
        if router_internal_depth >= router.ROUTER_INTERNAL_MECHANICAL_MAX_HOPS:
            raise router.RouterError("Router-internal mechanical action chain exceeded max hops")
        router._consume_router_internal_mechanical_action(project_root, run_root, run_state, pending_action)
        return compute_again(project_root, run_state, run_root, router_internal_depth + 1)
    if isinstance(pending_action, dict):
        reminder_action = router._next_wait_target_reminder_action(project_root, run_root, run_state, pending_action)
        if reminder_action is not None:
            router.append_history(
                run_state,
                "router_exposed_wait_target_reminder_before_passive_wait",
                {
                    "target_role": reminder_action.get("target_role"),
                    "wait_class": reminder_action.get("wait_class"),
                    "source_wait_action_type": pending_action.get("action_type"),
                },
            )
            router.save_run_state(run_root, run_state)
            return reminder_action
    if (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "await_role_decision"
        and pending_action.get("nonblocking_wait") is True
    ):
        run_state["pending_action"] = None
        router.append_history(
            run_state,
            "router_rechecks_before_nonblocking_role_wait",
            {
                "label": pending_action.get("label"),
                "dependency_class": pending_action.get("dependency_class"),
                "allowed_external_events": pending_action.get("allowed_external_events"),
            },
        )
        router.save_run_state(run_root, run_state)
        return None
    if router._action_is_startup_async_card_wait(pending_action if isinstance(pending_action, dict) else None):
        run_state["pending_action"] = None
        router.append_history(
            run_state,
            "router_rechecks_before_deferred_startup_card_ack_wait",
            {
                "label": pending_action.get("label") if isinstance(pending_action, dict) else None,
                "card_id": pending_action.get("card_id") if isinstance(pending_action, dict) else None,
                "card_ids": pending_action.get("card_ids") if isinstance(pending_action, dict) else None,
                "card_return_event": pending_action.get("card_return_event") if isinstance(pending_action, dict) else None,
                "startup_ack_wait_deferred_to_join": True,
                "common_progress_source": "runtime/controller_action_ledger.json_and_card_pending_return_ledger",
            },
        )
        router.save_run_state(run_root, run_state)
        return None
    if (
        isinstance(pending_action, dict)
        and pending_action.get("action_type") == "await_current_scope_reconciliation"
    ):
        if router._current_scope_reconciliation_wait_still_blocked(project_root, run_root, run_state, pending_action):
            local_obligation = router._next_local_obligation_before_passive_wait(project_root, run_root, run_state, pending_action)
            if local_obligation is not None:
                run_state["pending_action"] = None
                router.append_history(
                    run_state,
                    "router_local_obligation_preempted_passive_reconciliation_wait",
                    {
                        "wait_action_type": pending_action.get("action_type"),
                        "wait_label": pending_action.get("label"),
                        "scope_kind": pending_action.get("scope_kind"),
                        "scope_id": pending_action.get("scope_id"),
                        "local_obligation_action_type": local_obligation.get("action_type"),
                        "local_obligation_label": local_obligation.get("label"),
                    },
                )
                router.save_run_state(run_root, run_state)
                if router._action_is_router_internal_mechanical(local_obligation):
                    if router_internal_depth >= router.ROUTER_INTERNAL_MECHANICAL_MAX_HOPS:
                        raise router.RouterError("Router-internal mechanical action chain exceeded max hops")
                    router._consume_router_internal_mechanical_action(project_root, run_root, run_state, local_obligation)
                    return compute_again(project_root, run_state, run_root, router_internal_depth + 1)
                run_state["pending_action"] = local_obligation
                router._sync_derived_run_views(
                    project_root,
                    run_root,
                    run_state,
                    reason="after_router_local_obligation_preempted_passive_wait",
                    update_display=True,
                )
                router.save_run_state(run_root, run_state)
                return local_obligation
            return pending_action
        run_state["pending_action"] = None
        router.append_history(
            run_state,
            "router_rechecks_after_current_scope_reconciliation_cleared",
            {
                "scope_kind": pending_action.get("scope_kind"),
                "scope_id": pending_action.get("scope_id"),
                "review_trigger": pending_action.get("review_trigger"),
            },
        )
        router.save_run_state(run_root, run_state)
        return None
    return pending_action


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
        action = router._next_startup_heartbeat_binding_action(project_root, run_state, run_root)
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
        action = router._next_material_packet_action(project_root, run_state, run_root)
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


def finalize_controller_action(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
    *,
    router_internal_depth: int,
    compute_again: ComputeAgain,
) -> dict[str, Any]:
    action = router._apply_formal_work_packet_ack_preflight(project_root, run_state, run_root, action)
    action = router._apply_dispatch_recipient_gate(project_root, run_state, run_root, action)
    if router._action_is_router_internal_mechanical(action):
        if router_internal_depth >= router.ROUTER_INTERNAL_MECHANICAL_MAX_HOPS:
            raise router.RouterError("Router-internal mechanical action chain exceeded max hops")
        router._consume_router_internal_mechanical_action(project_root, run_root, run_state, action)
        return compute_again(project_root, run_state, run_root, router_internal_depth + 1)
    run_state["pending_action"] = action
    router.append_history(run_state, "router_computed_next_controller_action", {"action_type": action["action_type"]})
    router._sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_computed_pending_controller_action",
        update_display=True,
    )
    router.save_run_state(run_root, run_state)
    return action
