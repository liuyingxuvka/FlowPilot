"""Compatibility facade for route-artifact helpers.

Implementation lives in focused child modules. Public private-helper exports and
router binding behavior remain stable for legacy imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_route_artifacts_nodes_acceptance as _flowpilot_router_route_artifacts_nodes_acceptance
from flowpilot_router_route_artifacts_nodes_acceptance import *
import flowpilot_router_route_artifacts_nodes_parent as _flowpilot_router_route_artifacts_nodes_parent
from flowpilot_router_route_artifacts_nodes_parent import *
import flowpilot_router_route_artifacts_nodes_delegates as _flowpilot_router_route_artifacts_nodes_delegates
from flowpilot_router_route_artifacts_nodes_delegates import *

_BOUND_ROUTER: ModuleType | None = None


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
    _flowpilot_router_route_artifacts_nodes_acceptance._bind_router(router)
    _flowpilot_router_route_artifacts_nodes_parent._bind_router(router)
    _flowpilot_router_route_artifacts_nodes_delegates._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_route_artifacts"

__all__ = (
    '_write_node_acceptance_plan',
    '_write_pm_revised_node_acceptance_plan',
    '_write_parent_backward_targets',
    '_write_parent_backward_replay',
    '_write_parent_segment_decision',
    '_write_pm_research_absorption',
    '_validate_current_node_packet_envelope',
    '_validate_current_node_packet_event',
    '_validate_current_node_result_event',
    '_validate_current_node_reviewer_pass',
    '_route_payload_from_reviewed_draft',
    '_write_route_activation',
    '_write_route_mutation',
)

_LOCAL_NAMES = set(globals())
