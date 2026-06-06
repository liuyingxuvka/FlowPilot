"""PM role-work decision and package disposition writer facade."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate as _formal_gate
import flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition as _package_disposition
import flowpilot_router_work_packets_pm_role_writes_decisions_packet_outcomes as _packet_outcomes
import flowpilot_router_work_packets_pm_role_writes_decisions_role_result as _role_result
from flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate import _write_pm_formal_gate_package
from flowpilot_router_work_packets_pm_role_writes_decisions_package_disposition import _write_pm_package_result_disposition
from flowpilot_router_work_packets_pm_role_writes_decisions_role_result import (
    _validate_result_bodies_opened_by_pm,
    _write_pm_role_work_result_decision,
)

_OWNER_CHILD_MODULES = (
    _role_result,
    _formal_gate,
    _packet_outcomes,
    _package_disposition,
)


_BOUND_ROUTER: ModuleType | None = None
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
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_formal_gate_package',
    '_write_pm_package_result_disposition',
)

_LOCAL_NAMES = set(globals())
