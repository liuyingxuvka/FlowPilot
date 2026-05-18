"""Compatibility facade for model-miss repair and gate-decision helpers.

The behavior lives in focused child modules, while this module preserves the
legacy private import surface used by ``flowpilot_router`` and direct imports.
"""

from __future__ import annotations

from types import ModuleType

import flowpilot_router_events_repair_model_miss as _events_repair_model_miss
import flowpilot_router_events_repair_repair_decisions as _events_repair_repair_decisions
import flowpilot_router_events_repair_gate_decisions as _events_repair_gate_decisions

from flowpilot_router_events_repair_model_miss import (
    _validate_model_miss_officer_report_refs,
    _write_model_miss_triage_decision,
)
from flowpilot_router_events_repair_repair_decisions import (
    _repair_transaction_normalized_plan_kind,
    _event_already_recorded,
    _controller_wait_entries_for_event,
    _existing_event_producer_evidence,
    _list_field,
    _repair_transaction_execution_plan,
    _write_control_blocker_repair_decision,
)
from flowpilot_router_events_repair_gate_decisions import (
    _gate_decision_issue,
    _gate_decision_safe_id,
    _gate_decision_issues,
    _validate_gate_decision,
    _gate_decision_record_path,
    _gate_decision_summary,
    _write_gate_decision,
)

_CHILD_MODULES = (_events_repair_model_miss, _events_repair_repair_decisions, _events_repair_gate_decisions,)

def _bind_router(router: ModuleType) -> None:
    for child_module in _CHILD_MODULES:
        child_module._bind_router(router)

__all__ = (
    '_validate_model_miss_officer_report_refs',
    '_write_model_miss_triage_decision',
    '_repair_transaction_normalized_plan_kind',
    '_event_already_recorded',
    '_controller_wait_entries_for_event',
    '_existing_event_producer_evidence',
    '_list_field',
    '_repair_transaction_execution_plan',
    '_write_control_blocker_repair_decision',
    '_gate_decision_issue',
    '_gate_decision_safe_id',
    '_gate_decision_issues',
    '_validate_gate_decision',
    '_gate_decision_record_path',
    '_gate_decision_summary',
    '_write_gate_decision',
)

_LOCAL_NAMES = set(globals())
