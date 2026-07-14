"""Current FlowPilot control-plane friction FlowGuard model.

The positive route uses ordinary research, PM role-work, and current-node
packets.  Retired material-specific protocols appear only as known-bad inputs
that the ordinary dispatch contract rejects.
"""

from __future__ import annotations

from flowguard import Workflow

from flowpilot_control_plane_friction_model_audit import (
    audit_live_run,
    audit_retired_material_surfaces,
)
from flowpilot_control_plane_friction_model_hazards import hazard_states
from flowpilot_control_plane_friction_model_invariants import INVARIANTS, invariant_failures
from flowpilot_control_plane_friction_model_state import (
    PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES,
    Action,
    State,
    Tick,
    Transition,
    initial_state,
)
from flowpilot_control_plane_friction_model_transitions import (
    ControlPlaneStep,
    next_safe_states,
)


def build_workflow() -> Workflow:
    return Workflow((ControlPlaneStep(),), name="flowpilot_control_plane_friction")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 54


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES",
    "Action",
    "State",
    "Tick",
    "Transition",
    "audit_live_run",
    "audit_retired_material_surfaces",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "next_states",
]
