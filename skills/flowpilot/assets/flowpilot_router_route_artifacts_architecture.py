"""Facade for route-artifact helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_route_artifacts_architecture_product as _flowpilot_router_route_artifacts_architecture_product
from flowpilot_router_route_artifacts_architecture_product import *
import flowpilot_router_route_artifacts_architecture_gate_blocks as _flowpilot_router_route_artifacts_architecture_gate_blocks
from flowpilot_router_route_artifacts_architecture_gate_blocks import *
import flowpilot_router_route_artifacts_architecture_route_checks as _flowpilot_router_route_artifacts_architecture_route_checks
from flowpilot_router_route_artifacts_architecture_route_checks import *

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
    _flowpilot_router_route_artifacts_architecture_product._bind_router(router)
    _flowpilot_router_route_artifacts_architecture_gate_blocks._bind_router(router)
    _flowpilot_router_route_artifacts_architecture_route_checks._bind_router(router)


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
    '_write_role_block_report',
    '_gate_outcome_path_from_token',
    '_write_gate_outcome_block_report',
    '_clear_active_gate_outcome_block_for_pass',
    '_write_route_process_pass_report',
    '_write_route_process_issue_report',
)

_LOCAL_NAMES = set(globals())
