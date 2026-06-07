"""Router skeleton owner facade for controller runtime loop exports."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_controller_runtime_loop as runtime_loop
from flowpilot_router_controller_runtime_loop import (
    apply_action,
    apply_controller_action,
    compute_controller_action,
    next_action,
    record_controller_action_receipt,
    record_external_event,
    run_until_wait,
)

_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    runtime_loop._bind_router(router)
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
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = "flowpilot_router_controller_runtime"

__all__ = (
    "compute_controller_action",
    "next_action",
    "apply_controller_action",
    "record_external_event",
    "apply_action",
    "run_until_wait",
    "record_controller_action_receipt",
)

_LOCAL_NAMES = set(globals())
