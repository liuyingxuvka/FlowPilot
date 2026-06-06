"""Public facade for route-artifact helpers.

Implementation lives in focused child modules. Public private-helper exports and
router binding behavior remain stable for current imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_route_artifacts_planning_contract as _flowpilot_router_route_artifacts_planning_contract
from flowpilot_router_route_artifacts_planning_contract import *
import flowpilot_router_route_artifacts_planning_capabilities as _flowpilot_router_route_artifacts_planning_capabilities
from flowpilot_router_route_artifacts_planning_capabilities import *
import flowpilot_router_route_artifacts_planning_resume as _flowpilot_router_route_artifacts_planning_resume
from flowpilot_router_route_artifacts_planning_resume import *

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
    _flowpilot_router_route_artifacts_planning_contract._bind_router(router)
    _flowpilot_router_route_artifacts_planning_capabilities._bind_router(router)
    _flowpilot_router_route_artifacts_planning_resume._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_route_artifacts"

__all__ = (
    '_write_root_acceptance_contract',
    '_freeze_root_acceptance_contract',
    '_write_dependency_policy',
    '_write_capabilities_manifest',
    '_validate_selected_child_skills',
    '_write_child_skill_selection',
    '_write_child_skill_gate_manifest',
    '_write_pm_resume_decision',
)

_LOCAL_NAMES = set(globals())
