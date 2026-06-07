"""Controller runtime loop facade for FlowPilot router."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_controller_runtime_apply as runtime_apply
import flowpilot_router_controller_runtime_next as runtime_next
from flowpilot_router_controller_runtime_apply import (
    apply_action,
    apply_controller_action,
    record_controller_action_receipt,
    record_external_event,
    run_until_wait,
)
from flowpilot_router_controller_runtime_next import compute_controller_action, next_action

_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    runtime_next._bind_router(router)
    runtime_apply._bind_router(router)
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
