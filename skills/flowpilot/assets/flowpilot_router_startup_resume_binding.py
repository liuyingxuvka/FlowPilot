"""Startup resume binding compatibility facade."""

from __future__ import annotations

from flowpilot_router_startup_resume_binding_records import (
    _normalize_resume_role_agent_records,
    _resume_role_rehydration_action_extra,
)
from flowpilot_router_startup_resume_binding_reports import (
    _reclaim_resume_rehydration_postcondition_from_report,
    _resume_rehydration_report_candidates,
    _stable_resume_launcher_contract,
    _write_initial_continuation_binding,
    _write_resume_role_rehydration_report,
)
from flowpilot_router_startup_resume_binding_actions import (
    _next_resume_action,
    _next_role_recovery_action,
    _next_startup_heartbeat_binding_action,
)

__all__ = (
    '_resume_role_rehydration_action_extra',
    '_normalize_resume_role_agent_records',
    '_write_resume_role_rehydration_report',
    '_resume_rehydration_report_candidates',
    '_reclaim_resume_rehydration_postcondition_from_report',
    '_stable_resume_launcher_contract',
    '_write_initial_continuation_binding',
    '_next_resume_action',
    '_next_role_recovery_action',
    '_next_startup_heartbeat_binding_action',
)

_LOCAL_NAMES = set(globals())
