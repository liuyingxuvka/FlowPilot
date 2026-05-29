"""Lifecycle request owner public facade for the FlowPilot router.

The behavior is split into terminal fencing, terminal reconciliation, lifecycle
record writing, and exception blocker fallback helpers. Public and private
public names remain available from this module.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_lifecycle_requests_blockers as _owner_child_3
import flowpilot_router_lifecycle_requests_fence as _owner_child_0
import flowpilot_router_lifecycle_requests_reconciliation as _owner_child_1
import flowpilot_router_lifecycle_requests_records as _owner_child_2
from flowpilot_router_lifecycle_requests_blockers import *
from flowpilot_router_lifecycle_requests_fence import *
from flowpilot_router_lifecycle_requests_reconciliation import *
from flowpilot_router_lifecycle_requests_records import *


OWNER_MODULE = "flowpilot_router_lifecycle_requests"
_BOUND_ROUTER: ModuleType | None = None
_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
)


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
    for child_module in _OWNER_CHILD_MODULES:
        child_module._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


def owner_child_module_names() -> tuple[str, ...]:
    return tuple(module.__name__ for module in _OWNER_CHILD_MODULES)


__all__ = (
    "OWNER_MODULE",
    "TERMINAL_CONTROLLER_ACTION_TYPES",
    "_controller_action_is_terminal_cleanup",
    "_supersede_nonterminal_controller_work_for_terminal",
    "_write_terminal_lifecycle_fence",
    "_clear_active_control_blocker_for_terminal_lifecycle",
    "_reconcile_terminal_lifecycle_authorities",
    "_write_run_lifecycle_request",
    "_write_protocol_dead_end_lifecycle",
    "_run_lifecycle_terminal_action",
    "_try_write_control_blocker_for_exception",
    "owner_child_module_names",
)


_LOCAL_NAMES = set(globals())
