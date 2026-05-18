"""PM role-work request/result writer compatibility facade."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_work_packets_pm_role_writes_request as _owner_child_0
import flowpilot_router_work_packets_pm_role_writes_results as _owner_child_1
import flowpilot_router_work_packets_pm_role_writes_decisions as _owner_child_2
from flowpilot_router_work_packets_pm_role_writes_request import *
from flowpilot_router_work_packets_pm_role_writes_results import *
from flowpilot_router_work_packets_pm_role_writes_decisions import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
)


def _bind_router(router: ModuleType) -> None:
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
    '_write_pm_role_work_request',
    '_normalize_pm_role_work_result_recipient',
    '_validate_role_work_result_process_binding',
    '_write_role_work_result_returned',
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_package_result_disposition',
)

_LOCAL_NAMES = set(globals())
