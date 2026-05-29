"""Public facade for FlowPilot router repair transaction helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_events_repair_transaction_resolution as _owner_child_0
import flowpilot_router_events_repair_transaction_paths as _owner_child_1
import flowpilot_router_events_repair_transaction_outcomes as _owner_child_2
import flowpilot_router_events_repair_transaction_material as _owner_child_3
import flowpilot_router_events_repair_transaction_finalize as _owner_child_4
from flowpilot_router_events_repair_transaction_resolution import *
from flowpilot_router_events_repair_transaction_paths import *
from flowpilot_router_events_repair_transaction_outcomes import *
from flowpilot_router_events_repair_transaction_material import *
from flowpilot_router_events_repair_transaction_finalize import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
    _owner_child_4,
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
        if hasattr(child_module, '_bind_router'):
            child_module._bind_router(router)


def owner_child_module_names() -> tuple[str, ...]:
    return tuple(module.__name__ for module in _OWNER_CHILD_MODULES)

__all__ = (
    '_control_blocker_allows_resolution_event',
    '_control_resolution_event_name',
    '_resolve_delivered_control_blocker',
    '_repair_transactions_root',
    '_repair_transaction_index_path',
    '_repair_transaction_path',
    '_repair_transaction_id',
    '_control_blocker_repair_origin',
    '_repair_outcome_table',
    '_validate_repair_outcome_table',
    '_repair_outcome_events',
    '_repair_packet_specs_from_decision',
    '_write_repair_transaction_index',
    '_commit_material_scan_repair_generation',
    '_active_repair_transaction_for_event',
    '_repair_transaction_outcome_kind',
    '_clear_successful_repair_lane_state',
    '_finalize_repair_transaction_outcome',
)

_LOCAL_NAMES = set(globals())
