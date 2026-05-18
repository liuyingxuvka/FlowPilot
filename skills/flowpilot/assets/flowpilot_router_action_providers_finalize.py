"""Finalization provider for FlowPilot router actions."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_action_providers_common import ComputeAgain


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
