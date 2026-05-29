"""Public facade for router action construction helpers.

The behavior lives in focused child modules, but this owner facade keeps the
router import surface stable for ``flowpilot_router`` and direct imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_action_factory_dispatch as _dispatch
import flowpilot_router_action_factory_envelope as _envelope
import flowpilot_router_action_factory_reconciliation as _reconciliation
from flowpilot_router_action_factory_dispatch import (
    _apply_dispatch_recipient_gate,
    _dispatch_gate_action_is_ack_only_prompt,
    _dispatch_gate_action_work_class,
    _dispatch_gate_card_entry,
    _dispatch_gate_output_events_for_action,
    _dispatch_gate_output_events_for_card_id,
    _dispatch_gate_packet_blocker,
    _dispatch_gate_passive_wait_blocker,
    _dispatch_gate_pending_ack_wait,
    _dispatch_gate_pending_expected_output_blocker,
    _dispatch_gate_pm_role_work_blocker,
    _dispatch_gate_same_obligation_instruction_context,
    _dispatch_gate_wait_action,
)
from flowpilot_router_action_factory_envelope import (
    _controller_user_reporting_policy,
    append_history,
    make_action,
)
from flowpilot_router_action_factory_reconciliation import (
    _action_is_startup_async_card_wait,
    _action_is_startup_async_delivery,
    _apply_formal_work_packet_ack_preflight,
    _committed_card_artifact_extra,
    _current_node_scope_exit_reconciliation_blockers,
    _current_scope_pre_review_reconciliation_action,
    _current_scope_reconciliation_wait_still_blocked,
    _next_local_obligation_before_passive_wait,
    _next_pending_card_return_action,
    _pending_card_return_blocker_for_event,
    _roles_from_action_to_role,
    _startup_async_pending_returns,
)

_BOUND_ROUTER: ModuleType | None = None
_CHILD_MODULES = (_reconciliation, _dispatch, _envelope)

OWNER_MODULE = "flowpilot_router_action_factory"


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    for child_module in _CHILD_MODULES:
        child_module._bind_router(router)
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


__all__ = (
    "OWNER_MODULE",
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
    "_dispatch_gate_card_entry",
    "_dispatch_gate_output_events_for_card_id",
    "_dispatch_gate_output_events_for_action",
    "_dispatch_gate_action_is_ack_only_prompt",
    "_dispatch_gate_action_work_class",
    "_dispatch_gate_same_obligation_instruction_context",
    "_dispatch_gate_wait_action",
    "_dispatch_gate_pending_ack_wait",
    "_dispatch_gate_packet_blocker",
    "_dispatch_gate_pending_expected_output_blocker",
    "_dispatch_gate_pm_role_work_blocker",
    "_dispatch_gate_passive_wait_blocker",
    "_apply_dispatch_recipient_gate",
    "append_history",
    "_controller_user_reporting_policy",
    "make_action",
)

_LOCAL_NAMES = set(globals())
