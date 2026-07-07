"""FlowGuard model for FlowPilot current status projection convergence.

This model owns the finite product behind the public status bug class:
current authority can be complete while projection surfaces still expose stale,
null, awaiting, or historical rows as current. The model deliberately stays
FlowPilot-generic; target-project examples are symptom samples only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from itertools import product
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_current_status_projection"
MAX_SEQUENCE_LENGTH = 2

AUTHORITY_STATES = (
    "running",
    "blocked_current_work",
    "terminal_complete",
)

BLOCKER_LIFECYCLES = (
    "none",
    "current_active",
    "awaiting_pm_decision_gate",
    "cleared_history",
    "superseded_history",
)

NODE_CLOSURE_LIFECYCLES = (
    "none",
    "awaiting_without_pm_disposition",
    "accepted_after_pm_disposition",
    "repair_after_pm_disposition",
    "stale_awaiting_after_pm_disposition",
)

REPAIR_DOSSIER_LIFECYCLES = (
    "none",
    "current_active_pointer",
    "history_only_noncurrent_pointer",
    "stale_noncurrent_pointer_as_active",
)

PROJECTION_SURFACE_BEHAVIORS = (
    "current_pointer_ok",
    "console_ok",
    "console_missing_top_level",
    "status_projection_ok",
    "status_projection_null",
    "role_memory_ok",
    "role_memory_stale_blocker_current",
    "node_closure_projection_ok",
    "node_closure_stale_awaiting",
    "repair_dossier_projection_ok",
    "repair_dossier_stale_active",
    "historical_run_fallback_used",
)

CURRENT_BLOCKERS = {"current_active", "awaiting_pm_decision_gate"}
HISTORY_BLOCKERS = {"cleared_history", "superseded_history"}
PM_RESOLVED_NODE_CLOSURES = {
    "accepted_after_pm_disposition",
    "repair_after_pm_disposition",
    "stale_awaiting_after_pm_disposition",
}
NONCURRENT_DOSSIERS = {"history_only_noncurrent_pointer", "stale_noncurrent_pointer_as_active"}


@dataclass(frozen=True)
class ProjectionCell:
    authority_state: str
    blocker_lifecycle: str
    node_closure_lifecycle: str
    repair_dossier_lifecycle: str
    projection_surface_behavior: str

    @property
    def cell_id(self) -> str:
        return ".".join(
            (
                self.authority_state,
                self.blocker_lifecycle,
                self.node_closure_lifecycle,
                self.repair_dossier_lifecycle,
                self.projection_surface_behavior,
            )
        )


def _all_cells() -> tuple[ProjectionCell, ...]:
    return tuple(
        ProjectionCell(*values)
        for values in product(
            AUTHORITY_STATES,
            BLOCKER_LIFECYCLES,
            NODE_CLOSURE_LIFECYCLES,
            REPAIR_DOSSIER_LIFECYCLES,
            PROJECTION_SURFACE_BEHAVIORS,
        )
    )


CELLS = _all_cells()
CELL_BY_ID = {cell.cell_id: cell for cell in CELLS}


def projection_failures(cell: ProjectionCell) -> tuple[str, ...]:
    failures: list[str] = []
    surface = cell.projection_surface_behavior

    if surface == "historical_run_fallback_used":
        failures.append("projection_used_historical_or_fallback_authority")

    if cell.authority_state == "terminal_complete":
        if surface == "console_missing_top_level":
            failures.append("terminal_console_missing_current_top_level_fields")
        if surface == "status_projection_null":
            failures.append("terminal_status_projection_left_null")

    if surface == "role_memory_stale_blocker_current" and cell.blocker_lifecycle in HISTORY_BLOCKERS:
        failures.append("historical_blocker_projected_as_current_role_memory")

    if surface == "role_memory_ok" and cell.blocker_lifecycle in HISTORY_BLOCKERS:
        return tuple(failures)

    if (
        surface == "node_closure_stale_awaiting"
        and cell.node_closure_lifecycle in PM_RESOLVED_NODE_CLOSURES
    ):
        failures.append("pm_resolved_node_closure_left_awaiting")

    if (
        surface == "repair_dossier_stale_active"
        and cell.repair_dossier_lifecycle in NONCURRENT_DOSSIERS
    ):
        failures.append("noncurrent_repair_dossier_projected_active")

    if (
        cell.blocker_lifecycle in HISTORY_BLOCKERS
        and surface in {"console_ok", "status_projection_ok", "current_pointer_ok"}
    ):
        return tuple(failures)

    return tuple(failures)


def projection_classification(cell: ProjectionCell) -> str:
    failures = projection_failures(cell)
    if failures:
        return "reject"
    if (
        cell.blocker_lifecycle in HISTORY_BLOCKERS
        or cell.repair_dossier_lifecycle == "history_only_noncurrent_pointer"
    ):
        return "history_only"
    return "current"


VALID_CELL_IDS = tuple(cell.cell_id for cell in CELLS if projection_classification(cell) != "reject")
NEGATIVE_CELL_IDS = tuple(cell.cell_id for cell in CELLS if projection_classification(cell) == "reject")
REQUIRED_LABELS = tuple(
    [f"select_{cell.cell_id}" for cell in CELLS]
    + [f"accept_{cell_id}" for cell_id in VALID_CELL_IDS]
    + [f"reject_{cell_id}" for cell_id in NEGATIVE_CELL_IDS]
)


@dataclass(frozen=True)
class Tick:
    """One current-status projection cell."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    cell_id: str = ""
    terminal_reason: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.status == "new":
        for cell in CELLS:
            yield Transition(f"select_{cell.cell_id}", replace(state, status="selected", cell_id=cell.cell_id))
        return
    cell = CELL_BY_ID[state.cell_id]
    failures = projection_failures(cell)
    if failures:
        yield Transition(
            f"reject_{cell.cell_id}",
            replace(state, status="rejected", terminal_reason=";".join(failures)),
        )
    else:
        yield Transition(
            f"accept_{cell.cell_id}",
            replace(state, status="accepted", terminal_reason=projection_classification(cell)),
        )


class CurrentStatusProjectionStep:
    """Classify one current-status projection combination.

    Input x State -> Set(Output x State)
    reads: current run authority, blocker lifecycle, node-closure lifecycle,
    repair-dossier lifecycle, and projection surface behavior
    writes: current/history-only/reject projection classification
    """

    name = "CurrentStatusProjectionStep"
    reads = (
        "current_run_ledger",
        "lifecycle_guard",
        "foreground_duty",
        "final_return_preflight",
        "blocker_lifecycle",
        "node_closure_lifecycle",
        "repair_dossier_lifecycle",
    )
    writes = ("current_status_projection_classification",)
    input_description = "one finite current-status projection combination"
    output_description = "current, history-only, or rejected projection cell"
    idempotency = "same current run authority and projection rows produce the same classification"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def accepted_states_are_safe(state: State, _trace: object) -> InvariantResult:
    if state.status == "accepted":
        cell = CELL_BY_ID[state.cell_id]
        failures = projection_failures(cell)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    if state.status != "accepted":
        return False
    return projection_classification(CELL_BY_ID[state.cell_id]) != "reject"


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((CurrentStatusProjectionStep(),), name=MODEL_ID)


def invariant_failures(state: State) -> tuple[str, ...]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(str(result.message))
    return tuple(failures)


def matrix_report() -> dict[str, object]:
    classified = {"current": 0, "history_only": 0, "reject": 0}
    by_surface: dict[str, int] = {}
    by_failure: dict[str, int] = {}
    missing_classification: list[str] = []
    for cell in CELLS:
        classification = projection_classification(cell)
        if classification not in classified:
            missing_classification.append(cell.cell_id)
            continue
        classified[classification] += 1
        by_surface[cell.projection_surface_behavior] = by_surface.get(cell.projection_surface_behavior, 0) + 1
        for failure in projection_failures(cell):
            by_failure[failure] = by_failure.get(failure, 0) + 1
    return {
        "ok": not missing_classification and sum(classified.values()) == len(CELLS),
        "full_product_count": len(CELLS),
        "axis_counts": {
            "authority_states": len(AUTHORITY_STATES),
            "blocker_lifecycles": len(BLOCKER_LIFECYCLES),
            "node_closure_lifecycles": len(NODE_CLOSURE_LIFECYCLES),
            "repair_dossier_lifecycles": len(REPAIR_DOSSIER_LIFECYCLES),
            "projection_surface_behaviors": len(PROJECTION_SURFACE_BEHAVIORS),
        },
        "classified_counts": classified,
        "negative_cell_count": len(NEGATIVE_CELL_IDS),
        "valid_cell_count": len(VALID_CELL_IDS),
        "by_surface": dict(sorted(by_surface.items())),
        "by_failure": dict(sorted(by_failure.items())),
        "missing_classification": missing_classification,
        "sample_negative_cells": list(NEGATIVE_CELL_IDS[:20]),
    }


def hazard_states() -> dict[str, State]:
    return {
        cell_id: State(status="selected", cell_id=cell_id)
        for cell_id in NEGATIVE_CELL_IDS
    }


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    Invariant(
        "accepted_states_are_safe",
        "Accepted current-status projection cells cannot rely on fallback authority, null terminal projection, stale current blockers, stale node closures, or stale repair-dossier active pointers.",
        accepted_states_are_safe,
    ),
)
