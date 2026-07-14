"""Thin current-contract entrypoint for the FlowPilot cross-plane friction model."""

from __future__ import annotations

from typing import Iterable

from flowguard import FunctionResult, Workflow

from flowpilot_cross_plane_friction_model_audit import (
    CURRENT_ROLE_CARD_PATHS,
    ROLE_GATE_EVENT_PREFIXES,
    ROLE_GATE_NON_PASS_MARKERS,
    ROLE_GATE_PASS_MARKERS,
    RETIRED_MATERIAL_CARD_IDS,
    RETIRED_MATERIAL_EVENTS,
    RETIRED_MATERIAL_FIELDS,
    RETIRED_MATERIAL_PACKET_FAMILIES,
    STRUCTURED_REPORT_GATES,
    audit_current_prework_sources,
    audit_live_run,
    state_from_findings,
)
from flowpilot_cross_plane_friction_model_hazards import hazard_states, repair_solution_state
from flowpilot_cross_plane_friction_model_invariants import INVARIANTS, invariant_failures
from flowpilot_cross_plane_friction_model_state import (
    ACTIVE_STATUSES,
    BODY_PATH_NAMES,
    DONE_ITEM_STATUSES,
    CURRENT_ROLE_ARCHETYPES,
    TERMINAL_STATUSES,
    Action,
    State,
    Tick,
    Transition,
    initial_state,
)
from flowpilot_cross_plane_friction_model_strategy import REPAIR_ACTIONS, minimal_repair_strategy
from flowpilot_cross_plane_friction_model_transitions import (
    CrossPlaneReconciliationStep,
    next_safe_states,
)


def build_workflow() -> Workflow:
    return Workflow([CrossPlaneReconciliationStep()])


def next_states(state: State) -> Iterable[tuple[str, State]]:
    return next_safe_states(state)


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 20


__all__ = [
    "ACTIVE_STATUSES",
    "BODY_PATH_NAMES",
    "CURRENT_ROLE_CARD_PATHS",
    "DONE_ITEM_STATUSES",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "REPAIR_ACTIONS",
    "ROLE_GATE_EVENT_PREFIXES",
    "ROLE_GATE_NON_PASS_MARKERS",
    "ROLE_GATE_PASS_MARKERS",
    "RETIRED_MATERIAL_CARD_IDS",
    "RETIRED_MATERIAL_EVENTS",
    "RETIRED_MATERIAL_FIELDS",
    "RETIRED_MATERIAL_PACKET_FAMILIES",
    "CURRENT_ROLE_ARCHETYPES",
    "STRUCTURED_REPORT_GATES",
    "TERMINAL_STATUSES",
    "Action",
    "CrossPlaneReconciliationStep",
    "State",
    "Tick",
    "Transition",
    "audit_current_prework_sources",
    "audit_live_run",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "minimal_repair_strategy",
    "next_safe_states",
    "next_states",
    "repair_solution_state",
    "state_from_findings",
]

