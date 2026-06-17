"""Public facade for route-frontier policy completion helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_route_frontier_policy_completion_authority as _owner_child_0
import flowpilot_router_route_frontier_policy_completion_context as _owner_child_1
import flowpilot_router_route_frontier_policy_completion_ledger as _owner_child_2
from flowpilot_router_route_frontier_policy_completion_authority import *
from flowpilot_router_route_frontier_policy_completion_context import *
from flowpilot_router_route_frontier_policy_completion_ledger import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
)


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
    for child_module in _OWNER_CHILD_MODULES:
        child_module._bind_router(router)


__all__ = (
    "ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS",
    "_route_authority_owner_for_action",
    "_route_authority_required_repair_command",
    "_route_authority_snapshot",
    "_route_authority_rejection_payload",
    "_write_route_authority_rejection_blocker",
    "_reject_route_authority_submission",
    "_unsupported_route_authority_payload_fields",
    "_reject_unsupported_route_authority_payload",
    "_legal_next_action_context",
    "_legal_next_action_ids",
    "_legal_route_action_allowed",
    "_first_incomplete_child_node_id",
    "_enter_next_child_node",
    "_next_parent_child_entry_action",
    "_require_legal_route_action",
    "_filter_events_by_legal_route_actions",
    "_write_node_completion_ledger",
    "_mark_current_node_packet_records_completed",
    "_mark_frontier_node_completed",
)


_LOCAL_NAMES = set(globals())
