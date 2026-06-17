"""Facade for work-packet next-action helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_role_agents as _role_agents
from flowpilot_router_work_packets_role_agents import *
import flowpilot_router_work_packets_material_next as _material_next
from flowpilot_router_work_packets_material_next import *
import flowpilot_router_work_packets_research_next as _research_next
from flowpilot_router_work_packets_research_next import *
import flowpilot_router_work_packets_result_reconciliation as _result_reconciliation
from flowpilot_router_work_packets_result_reconciliation import *

_BOUND_ROUTER: ModuleType | None = None
_OWNER_CHILD_MODULES = (
    _role_agents,
    _material_next,
    _research_next,
    _result_reconciliation,
)


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    for child_module in _OWNER_CHILD_MODULES:
        child_module._bind_router(router)

__all__ = (
    '_current_role_agent_payload_contract_for_packet',
    '_missing_active_holder_roles',
    '_open_current_role_agent_for_packet_plan',
    '_active_material_generation_progress',
    '_next_material_packet_action',
    '_next_research_packet_action',
    '_try_reconcile_material_scan_body_delivery',
    '_try_reconcile_material_scan_results',
    '_try_reconcile_research_results',
)

_LOCAL_NAMES = set(globals())
