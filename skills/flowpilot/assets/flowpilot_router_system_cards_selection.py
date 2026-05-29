"""Public facade for FlowPilot router system-card selection helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_system_cards_selection_bundle as _bundle
import flowpilot_router_system_cards_selection_next as _next
import flowpilot_router_system_cards_selection_reconcile as _reconcile
import flowpilot_router_system_cards_selection_tokens as _tokens
from flowpilot_router_system_cards_selection_bundle import *
from flowpilot_router_system_cards_selection_next import *
from flowpilot_router_system_cards_selection_reconcile import *
from flowpilot_router_system_cards_selection_tokens import *

_OWNER_CHILD_MODULES = (_tokens, _next, _bundle, _reconcile)


def _bind_router(router: ModuleType) -> None:
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


__all__ = (*_tokens.__all__, *_next.__all__, *_bundle.__all__, *_reconcile.__all__)

_LOCAL_NAMES = set(globals())
