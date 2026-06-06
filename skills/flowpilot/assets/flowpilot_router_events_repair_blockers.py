"""Public facade for control blocker repair helpers.

The behavior lives in focused child modules, while this module preserves the
router binding surface used by ``flowpilot_router`` and direct imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_events_repair_blocker_records as _events_repair_blocker_records
import flowpilot_router_events_repair_blocker_indexes as _events_repair_blocker_indexes
import flowpilot_router_events_repair_blocker_actions as _events_repair_blocker_actions

from flowpilot_router_events_repair_blocker_records import (
    _write_control_blocker_repair_packet,
    _supersede_prior_control_blockers,
    _nonnegative_int_or_none,
    _control_blocker_family_key,
    _existing_control_blocker_family_record,
    _write_control_blocker,
    _control_blocker_record,
    _control_blocker_matches_reconciled_action,
)
from flowpilot_router_events_repair_blocker_indexes import (
    _supersede_queued_control_blocker_actions,
    _resolve_control_blockers_for_reconciled_controller_action,
    _control_blocker_summary,
    _resume_reentry_gate_pending,
    _sync_protocol_blocker_index,
    _sync_control_plane_indexes,
)
from flowpilot_router_events_repair_blocker_actions import (
    _control_blocker_wait_events,
    _event_producer_roles,
    _role_set,
    _control_blocker_followup_target_role,
    _validate_wait_event_producer_binding,
    _repair_transaction_for_control_blocker,
    _make_operation_replay_action,
    _make_controller_repair_work_packet_action,
    _next_repair_transaction_executable_action,
    _next_control_blocker_action,
    _mark_control_blocker_delivered,
)

_CHILD_MODULES = (_events_repair_blocker_records, _events_repair_blocker_indexes, _events_repair_blocker_actions,)

_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    for child_module in _CHILD_MODULES:
        child_module._bind_router(router)

__all__ = (
    '_write_control_blocker_repair_packet',
    '_supersede_prior_control_blockers',
    '_nonnegative_int_or_none',
    '_control_blocker_family_key',
    '_existing_control_blocker_family_record',
    '_write_control_blocker',
    '_control_blocker_record',
    '_control_blocker_matches_reconciled_action',
    '_supersede_queued_control_blocker_actions',
    '_resolve_control_blockers_for_reconciled_controller_action',
    '_control_blocker_summary',
    '_resume_reentry_gate_pending',
    '_sync_protocol_blocker_index',
    '_sync_control_plane_indexes',
    '_control_blocker_wait_events',
    '_event_producer_roles',
    '_role_set',
    '_control_blocker_followup_target_role',
    '_validate_wait_event_producer_binding',
    '_repair_transaction_for_control_blocker',
    '_make_operation_replay_action',
    '_make_controller_repair_work_packet_action',
    '_next_repair_transaction_executable_action',
    '_next_control_blocker_action',
    '_mark_control_blocker_delivered',
)

_LOCAL_NAMES = set(globals())
