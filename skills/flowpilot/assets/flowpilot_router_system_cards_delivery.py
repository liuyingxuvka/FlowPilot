"""Compatibility facade for FlowPilot router system-card delivery helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_system_cards_delivery_bundle as _bundle
import flowpilot_router_system_cards_delivery_single as _single
from flowpilot_router_system_cards_delivery_bundle import *
from flowpilot_router_system_cards_delivery_single import *

_OWNER_CHILD_MODULES = (_single, _bundle)


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


__all__ = (*_single.__all__, *_bundle.__all__)

_LOCAL_NAMES = set(globals())
