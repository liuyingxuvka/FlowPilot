"""Pending-action provider for FlowPilot router actions."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_providers_common import ComputeAgain


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
