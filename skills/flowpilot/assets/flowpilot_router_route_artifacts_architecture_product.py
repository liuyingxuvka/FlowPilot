"""Facade for product architecture route-artifact helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_route_artifacts_architecture_product_core as _product_core
from flowpilot_router_route_artifacts_architecture_product_core import *
import flowpilot_router_route_artifacts_architecture_product_intent as _product_intent
from flowpilot_router_route_artifacts_architecture_product_intent import *
import flowpilot_router_route_artifacts_architecture_product_decisions as _product_decisions
from flowpilot_router_route_artifacts_architecture_product_decisions import *

_BOUND_ROUTER: ModuleType | None = None
_OWNER_CHILD_MODULES = (
    _product_core,
    _product_intent,
    _product_decisions,
)


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


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_route_artifacts"

__all__ = (
    '_write_product_function_architecture',
    '_write_role_gate_report',
    '_write_product_behavior_model_report',
    '_write_pm_implementation_intent',
    '_write_target_realization_model_report',
    '_write_target_realization_model_issue_report',
    '_write_pm_model_decision',
    '_write_pm_product_behavior_model_decision',
    '_write_pm_target_realization_model_decision',
    '_write_pm_process_route_model_decision',
)

_LOCAL_NAMES = set(globals())
