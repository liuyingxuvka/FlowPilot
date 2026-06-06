"""Dispatch-recipient gate helpers for router action construction.

This public facade keeps the router module import path stable while
card classification, blocker detection, wait-action construction, and gate
orchestration live in focused child modules.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_action_factory_dispatch_apply as _apply
import flowpilot_router_action_factory_dispatch_blockers as _blockers
import flowpilot_router_action_factory_dispatch_cards as _cards
import flowpilot_router_action_factory_dispatch_waits as _waits
from flowpilot_router_action_factory_dispatch_apply import *
from flowpilot_router_action_factory_dispatch_blockers import *
from flowpilot_router_action_factory_dispatch_cards import *
from flowpilot_router_action_factory_dispatch_waits import *

_BOUND_ROUTER: ModuleType | None = None
_CHILD_MODULES = (_cards, _waits, _blockers, _apply)
OWNER_MODULE = "flowpilot_router_action_factory_dispatch"


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
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
    *_cards.__all__,
    *_waits.__all__,
    *_blockers.__all__,
    *_apply.__all__,
)

_LOCAL_NAMES = set(globals())
