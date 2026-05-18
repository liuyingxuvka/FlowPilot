"""Compatibility facade for FlowPilot router control-blocker policy helpers."""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_events_repair_policy_snapshot as _owner_child_0
import flowpilot_router_events_repair_policy_classification as _owner_child_1
import flowpilot_router_events_repair_event_capability as _owner_child_2
from flowpilot_router_events_repair_policy_snapshot import *
from flowpilot_router_events_repair_policy_classification import *
from flowpilot_router_events_repair_event_capability import *

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
        if hasattr(child_module, '_bind_router'):
            child_module._bind_router(router)


def owner_child_module_names() -> tuple[str, ...]:
    return tuple(module.__name__ for module in _OWNER_CHILD_MODULES)

__all__ = (
    '_control_blocker_error_code',
    '_blocker_repair_policy_snapshot_path',
    '_blocker_repair_policy_rows',
    '_write_blocker_repair_policy_snapshot',
    '_control_blocker_policy_row',
    '_control_blocker_attempt_key',
    '_control_blocker_direct_attempts_used',
    '_policy_first_handler_target',
    '_pm_recovery_options_from_policy',
    '_default_pm_recovery_option',
    '_project_relative_if_possible',
    '_payload_source_paths',
    '_control_payload_public_view',
    '_infer_responsible_role',
    '_classify_control_blocker',
    '_should_materialize_control_blocker',
    '_skill_observation_reminder',
    '_validated_external_event_names',
    '_active_node_kind_for_event_capability',
    '_event_capability_issue',
    '_run_state_with_assumed_flag',
    '_validated_event_capability_names',
    '_external_event_validation_issue',
    '_control_blocker_allowed_resolution_events',
    '_control_blocker_policy',
)

_LOCAL_NAMES = set(globals())
