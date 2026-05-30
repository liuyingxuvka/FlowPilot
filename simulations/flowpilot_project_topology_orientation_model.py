"""FlowGuard model for FlowGuard project topology orientation.

This focused model checks that a mature FlowGuard project treats the generated
project topology as background architecture before non-trivial work, keeps the
topology current, and never uses topology as validation evidence or role
authority.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 10


@dataclass(frozen=True)
class Tick:
    """One topology-orientation transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    mature_flowguard_project: bool = True
    nontrivial_work: bool = True
    topology_artifacts_present: bool = False
    topology_current: bool = False
    topology_read_before_work: bool = False
    model_layer_present: bool = False
    test_layer_present: bool = False
    code_layer_present: bool = False
    evidence_layer_present: bool = False
    known_bad_layer_present: bool = False
    topology_used_as_validation_evidence: bool = False
    owning_validation_evidence_present: bool = False
    downstream_route_selected_after_orientation: bool = False
    pm_considered_topology: bool = False
    officer_treated_topology_as_background: bool = False
    reviewer_treated_topology_as_background: bool = False
    controller_interpreted_topology_as_report: bool = False
    reviewer_approved_gate_from_topology: bool = False
    pm_mutated_route_from_topology_alone: bool = False
    topology_refreshed_after_source_change: bool = True


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class ProjectTopologyOrientationStep:
    """Model one project-topology intake step.

    Input x State -> Set(Output x State)
    reads: topology presence/freshness/layers, role authority, validation split
    writes: topology intake, downstream route selection, terminal status
    idempotency: safe ticks only add orientation or separate validation evidence
    """

    name = "ProjectTopologyOrientationStep"
    reads = (
        "mature_flowguard_project",
        "topology_artifacts_present",
        "topology_current",
        "topology_read_before_work",
        "owning_validation_evidence_present",
    )
    writes = (
        "topology_generation",
        "topology_intake",
        "role_orientation",
        "downstream_route_selection",
        "validation_evidence_boundary",
    )
    input_description = "one mature FlowGuard project orientation tick"
    output_description = "one topology orientation action"
    idempotency = "safe ticks do not turn topology into validation evidence"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    if state.status == "new":
        return (Transition("topology_orientation_started", replace(state, status="running")),)
    failures = invariant_failures(state)
    if failures:
        return (Transition("topology_orientation_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.mature_flowguard_project and not state.topology_artifacts_present:
        return (
            Transition(
                "generate_flowguard_project_topology",
                replace(
                    state,
                    topology_artifacts_present=True,
                    topology_current=True,
                    model_layer_present=True,
                    test_layer_present=True,
                    code_layer_present=True,
                    evidence_layer_present=True,
                    known_bad_layer_present=True,
                ),
            ),
        )
    if state.topology_artifacts_present and not state.topology_current:
        return (Transition("refresh_stale_project_topology", replace(state, topology_current=True)),)
    if state.topology_current and not state.topology_read_before_work:
        return (Transition("agent_reads_topology_before_nontrivial_work", replace(state, topology_read_before_work=True)),)
    if state.topology_read_before_work and not state.pm_considered_topology:
        return (Transition("pm_considers_topology_as_background", replace(state, pm_considered_topology=True)),)
    if state.pm_considered_topology and not state.officer_treated_topology_as_background:
        return (
            Transition(
                "officer_keeps_topology_as_background",
                replace(state, officer_treated_topology_as_background=True),
            ),
        )
    if state.officer_treated_topology_as_background and not state.reviewer_treated_topology_as_background:
        return (
            Transition(
                "reviewer_keeps_topology_as_background",
                replace(state, reviewer_treated_topology_as_background=True),
            ),
        )
    if state.reviewer_treated_topology_as_background and not state.downstream_route_selected_after_orientation:
        return (
            Transition(
                "select_downstream_flowguard_route_after_orientation",
                replace(state, downstream_route_selected_after_orientation=True),
            ),
        )
    if state.downstream_route_selected_after_orientation and not state.owning_validation_evidence_present:
        return (
            Transition(
                "attach_owning_validation_evidence_separate_from_topology",
                replace(state, owning_validation_evidence_present=True),
            ),
        )
    return (Transition("topology_orientation_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.mature_flowguard_project and state.nontrivial_work and state.status == "complete" and not state.topology_read_before_work:
        failures.append("Mature FlowGuard project completed non-trivial work without topology intake")
    if state.mature_flowguard_project and state.topology_artifacts_present and not state.topology_current:
        failures.append("Stale topology was accepted for mature FlowGuard work")
    if state.topology_artifacts_present and not state.model_layer_present:
        failures.append("Topology missing model layer")
    if state.topology_artifacts_present and not state.test_layer_present:
        failures.append("Topology missing test layer")
    if state.topology_artifacts_present and not state.code_layer_present:
        failures.append("Topology missing code layer")
    if state.topology_artifacts_present and not state.evidence_layer_present:
        failures.append("Topology missing evidence layer")
    if state.topology_artifacts_present and not state.known_bad_layer_present:
        failures.append("Topology missing known-bad/risk layer")
    if state.topology_used_as_validation_evidence:
        failures.append("Topology was used as validation evidence")
    if state.status == "complete" and state.nontrivial_work and not state.owning_validation_evidence_present:
        failures.append("Topology orientation completed without separate owning validation evidence")
    if state.controller_interpreted_topology_as_report:
        failures.append("Controller interpreted topology as a FlowGuard report")
    if state.reviewer_approved_gate_from_topology:
        failures.append("Reviewer approved a gate from topology")
    if state.pm_mutated_route_from_topology_alone:
        failures.append("PM mutated route from topology alone")
    if state.nontrivial_work and state.topology_read_before_work and not state.downstream_route_selected_after_orientation:
        if state.status == "complete":
            failures.append("Topology was read but no downstream FlowGuard route was selected")
    if not state.topology_refreshed_after_source_change:
        failures.append("Topology source changed without rebuild/check")
    return failures


def topology_orientation_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_project_topology_orientation_boundaries",
        description=(
            "Project topology is read before mature FlowGuard work, remains current "
            "and complete, and never replaces owning validation or role authority."
        ),
        predicate=topology_orientation_invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((ProjectTopologyOrientationStep(),), name="flowpilot_project_topology_orientation")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def target_success_state() -> State:
    return State(
        status="complete",
        mature_flowguard_project=True,
        nontrivial_work=True,
        topology_artifacts_present=True,
        topology_current=True,
        topology_read_before_work=True,
        model_layer_present=True,
        test_layer_present=True,
        code_layer_present=True,
        evidence_layer_present=True,
        known_bad_layer_present=True,
        owning_validation_evidence_present=True,
        downstream_route_selected_after_orientation=True,
        pm_considered_topology=True,
        officer_treated_topology_as_background=True,
        reviewer_treated_topology_as_background=True,
        topology_refreshed_after_source_change=True,
    )


def hazard_states() -> dict[str, State]:
    base = target_success_state()
    return {
        "skipped_topology_intake": replace(base, topology_read_before_work=False),
        "stale_topology": replace(base, topology_current=False),
        "missing_model_layer": replace(base, model_layer_present=False),
        "missing_test_layer": replace(base, test_layer_present=False),
        "missing_code_layer": replace(base, code_layer_present=False),
        "missing_evidence_layer": replace(base, evidence_layer_present=False),
        "missing_known_bad_layer": replace(base, known_bad_layer_present=False),
        "topology_as_validation": replace(base, topology_used_as_validation_evidence=True),
        "missing_owning_validation": replace(base, owning_validation_evidence_present=False),
        "controller_interprets_topology": replace(base, controller_interpreted_topology_as_report=True),
        "reviewer_gate_from_topology": replace(base, reviewer_approved_gate_from_topology=True),
        "pm_route_mutation_from_topology": replace(base, pm_mutated_route_from_topology_alone=True),
        "source_change_without_refresh": replace(base, topology_refreshed_after_source_change=False),
    }
