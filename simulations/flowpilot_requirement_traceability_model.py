"""FlowGuard model for the FlowPilot requirement traceability upgrade.

Risk purpose header:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  proposed FlowPilot requirement-traceability workflow before production
  template, card, or router edits.
- Guards against concrete bugs: missing stable requirement ids, missing root
  change status, route nodes with no valid requirement coverage, node closure by
  generic/report-only evidence, stale evidence after mutation, external
  OpenSpec-like authority replacing FlowPilot PM authority, light/simple
  FlowPilot profiles, dropped child-skill trace links, final ledger closure with
  unresolved requirements, and trace events that bypass router authority.
- Future agents should update this model whenever FlowPilot changes product
  architecture, root acceptance, route draft, node acceptance, route mutation,
  final ledger, or traceability validation behavior.
- Run with:
  python simulations/run_flowpilot_requirement_traceability_checks.py --json-out simulations/flowpilot_requirement_traceability_results.json
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One abstract traceability-upgrade planning tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    stage: int = 0

    flowpilot_standalone: bool = True
    external_specs_advisory_only: bool = True
    external_spec_import_pm_approved: bool = True
    external_spec_authority_used: bool = False

    full_protocol_required: bool = True
    light_profile_allowed: bool = False
    simple_profile_waiver_allowed: bool = False

    requirement_registry_exists: bool = False
    stable_requirement_ids: bool = False
    product_tasks_trace_ids: bool = False
    product_capabilities_trace_ids: bool = False
    product_acceptance_trace_ids: bool = False

    root_requirements_source_ids: bool = False
    root_requirements_change_status: bool = False
    root_requirements_supersession_policy: bool = False
    root_proof_matrix_trace_ids: bool = False

    route_nodes_cover_requirement_ids: bool = False
    route_nodes_reference_known_requirements: bool = False
    route_nodes_cover_scenarios: bool = False
    route_nodes_source_capabilities: bool = False
    route_nodes_have_rationale: bool = False
    route_nodes_merge_split_review: bool = False

    node_inherits_route_requirements: bool = False
    node_acceptance_experiment_maps_requirements: bool = False
    node_acceptance_maps_standard_scenarios: bool = False
    node_acceptance_direct_evidence_required: bool = False
    child_skill_requirement_trace_kept: bool = False

    mutation_impacted_requirements_listed: bool = False
    mutation_impacted_nodes_listed: bool = False
    mutation_stale_evidence_invalidated: bool = False
    mutation_rerun_models_listed: bool = False
    superseded_requirements_block_old_evidence: bool = False

    final_ledger_requirement_trace_closure: bool = False
    final_ledger_all_effective_requirements_resolved: bool = False
    final_ledger_direct_evidence_required: bool = False
    final_ledger_waiver_authority_checked: bool = False
    final_ledger_stale_status_checked: bool = False

    router_validation_enforces_trace_fields: bool = False
    router_authorized_trace_events: bool = False
    router_rejects_invented_trace_events: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def product_phase_state() -> State:
    return replace(
        State(status="running", stage=1),
        requirement_registry_exists=True,
        stable_requirement_ids=True,
        product_tasks_trace_ids=True,
        product_capabilities_trace_ids=True,
        product_acceptance_trace_ids=True,
    )


def root_phase_state() -> State:
    return replace(
        product_phase_state(),
        stage=2,
        root_requirements_source_ids=True,
        root_requirements_change_status=True,
        root_requirements_supersession_policy=True,
        root_proof_matrix_trace_ids=True,
    )


def route_phase_state() -> State:
    return replace(
        root_phase_state(),
        stage=3,
        route_nodes_cover_requirement_ids=True,
        route_nodes_reference_known_requirements=True,
        route_nodes_cover_scenarios=True,
        route_nodes_source_capabilities=True,
        route_nodes_have_rationale=True,
        route_nodes_merge_split_review=True,
    )


def node_phase_state() -> State:
    return replace(
        route_phase_state(),
        stage=4,
        node_inherits_route_requirements=True,
        node_acceptance_experiment_maps_requirements=True,
        node_acceptance_maps_standard_scenarios=True,
        node_acceptance_direct_evidence_required=True,
        child_skill_requirement_trace_kept=True,
    )


def mutation_phase_state() -> State:
    return replace(
        node_phase_state(),
        stage=5,
        mutation_impacted_requirements_listed=True,
        mutation_impacted_nodes_listed=True,
        mutation_stale_evidence_invalidated=True,
        mutation_rerun_models_listed=True,
        superseded_requirements_block_old_evidence=True,
    )


def final_phase_state() -> State:
    return replace(
        mutation_phase_state(),
        stage=6,
        final_ledger_requirement_trace_closure=True,
        final_ledger_all_effective_requirements_resolved=True,
        final_ledger_direct_evidence_required=True,
        final_ledger_waiver_authority_checked=True,
        final_ledger_stale_status_checked=True,
        router_validation_enforces_trace_fields=True,
        router_authorized_trace_events=True,
        router_rejects_invented_trace_events=True,
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "complete":
        return
    if state.stage == 0:
        yield Transition("add_product_requirement_trace_spine", product_phase_state())
        return
    if state.stage == 1:
        yield Transition("bind_root_contract_to_requirement_deltas", root_phase_state())
        return
    if state.stage == 2:
        yield Transition("bind_route_nodes_to_requirements", route_phase_state())
        return
    if state.stage == 3:
        yield Transition("bind_node_acceptance_to_direct_evidence", node_phase_state())
        return
    if state.stage == 4:
        yield Transition("add_mutation_impact_and_stale_evidence_guards", mutation_phase_state())
        return
    if state.stage == 5:
        yield Transition("add_final_ledger_and_router_trace_closure", final_phase_state())
        return
    if state.stage == 6:
        yield Transition("requirement_traceability_upgrade_completed", replace(state, status="complete"))


class RequirementTraceabilityStep:
    """Model one requirement-traceability upgrade step.

    Input x State -> Set(Output x State)
    reads: current FlowPilot lifecycle phase, requirement provenance, route
    node coverage, node acceptance evidence, mutation impact, final ledger
    closure, and router trace authority
    writes: the next PM-owned traceability guard in the existing FlowPilot
    lifecycle
    idempotency: once a traceability guard is added it remains required by all
    later phases
    """

    name = "RequirementTraceabilityStep"
    input_description = "FlowPilot requirement-traceability upgrade tick"
    output_description = "next traceability guard added to the existing lifecycle"
    reads = (
        "product_trace",
        "root_trace",
        "route_trace",
        "node_trace",
        "mutation_trace",
        "final_trace",
        "router_trace_authority",
    )
    writes = ("traceability_guard", "upgrade_stage", "completion_status")
    idempotency = "monotonic trace guards"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if not state.flowpilot_standalone:
        failures.append("FlowPilot requirement traceability became dependent on an external tool")
    if state.external_spec_authority_used or not (
        state.external_specs_advisory_only and state.external_spec_import_pm_approved
    ):
        failures.append("external OpenSpec-like output became route authority without FlowPilot PM import approval")
    if not state.full_protocol_required or state.light_profile_allowed or state.simple_profile_waiver_allowed:
        failures.append("formal FlowPilot run allowed a light/simple profile instead of the full protocol")

    if state.stage >= 1 and not (
        state.requirement_registry_exists
        and state.stable_requirement_ids
        and state.product_tasks_trace_ids
        and state.product_capabilities_trace_ids
        and state.product_acceptance_trace_ids
    ):
        failures.append("product architecture phase lacked stable requirement trace ids across tasks, capabilities, and acceptance")

    if state.stage >= 2 and not (
        state.root_requirements_source_ids
        and state.root_requirements_change_status
        and state.root_requirements_supersession_policy
        and state.root_proof_matrix_trace_ids
    ):
        failures.append("root contract phase lacked source ids, change status, supersession policy, or proof-matrix trace")

    if state.stage >= 3 and not (
        state.route_nodes_cover_requirement_ids
        and state.route_nodes_reference_known_requirements
        and state.route_nodes_cover_scenarios
        and state.route_nodes_source_capabilities
        and state.route_nodes_have_rationale
        and state.route_nodes_merge_split_review
    ):
        failures.append("route phase lacked valid requirement coverage, scenario/capability links, or node rationale")

    if state.stage >= 4 and not (
        state.node_inherits_route_requirements
        and state.node_acceptance_experiment_maps_requirements
        and state.node_acceptance_maps_standard_scenarios
        and state.node_acceptance_direct_evidence_required
        and state.child_skill_requirement_trace_kept
    ):
        failures.append("node acceptance phase lacked requirement evidence mapping, standard scenarios, direct evidence, or child-skill trace")

    if state.stage >= 5 and not (
        state.mutation_impacted_requirements_listed
        and state.mutation_impacted_nodes_listed
        and state.mutation_stale_evidence_invalidated
        and state.mutation_rerun_models_listed
        and state.superseded_requirements_block_old_evidence
    ):
        failures.append("mutation phase failed to list impacted requirements/nodes, invalidate stale evidence, require reruns, or block old superseded evidence")

    if state.status == "complete" and not (
        state.final_ledger_requirement_trace_closure
        and state.final_ledger_all_effective_requirements_resolved
        and state.final_ledger_direct_evidence_required
        and state.final_ledger_waiver_authority_checked
        and state.final_ledger_stale_status_checked
    ):
        failures.append("final ledger completed without complete requirement closure, direct evidence, waiver authority, and stale-status checks")

    if state.status == "complete" and not (
        state.router_validation_enforces_trace_fields
        and state.router_authorized_trace_events
        and state.router_rejects_invented_trace_events
    ):
        failures.append("traceability completion lacked router validation and router-authorized trace events")

    return failures


def requirement_traceability_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_requirement_traceability_preserves_standalone_full_protocol",
        description=(
            "OpenSpec-style traceability may be added only when FlowPilot stays "
            "standalone, full-protocol-only, PM-owned, evidence-bound, mutation-"
            "aware, and router-authorized."
        ),
        predicate=requirement_traceability_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 7


def build_workflow() -> Workflow:
    return Workflow((RequirementTraceabilityStep(),), name="flowpilot_requirement_traceability")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def hazard_states() -> dict[str, State]:
    return {
        "product_missing_stable_ids": replace(product_phase_state(), stable_requirement_ids=False),
        "product_capability_unmapped": replace(product_phase_state(), product_capabilities_trace_ids=False),
        "root_missing_change_status": replace(root_phase_state(), root_requirements_change_status=False),
        "root_missing_supersession_policy": replace(root_phase_state(), root_requirements_supersession_policy=False),
        "route_node_unknown_requirement": replace(route_phase_state(), route_nodes_reference_known_requirements=False),
        "route_node_without_rationale": replace(route_phase_state(), route_nodes_have_rationale=False),
        "node_plan_missing_direct_evidence": replace(node_phase_state(), node_acceptance_direct_evidence_required=False),
        "node_child_skill_trace_dropped": replace(node_phase_state(), child_skill_requirement_trace_kept=False),
        "mutation_keeps_stale_evidence": replace(mutation_phase_state(), mutation_stale_evidence_invalidated=False),
        "superseded_requirement_closed_by_old_evidence": replace(
            mutation_phase_state(), superseded_requirements_block_old_evidence=False
        ),
        "final_ledger_unresolved_requirement": replace(
            final_phase_state(), status="complete", final_ledger_all_effective_requirements_resolved=False
        ),
        "final_ledger_existence_only": replace(
            final_phase_state(), status="complete", final_ledger_direct_evidence_required=False
        ),
        "external_spec_as_authority": replace(final_phase_state(), status="complete", external_spec_authority_used=True),
        "light_profile_allowed": replace(final_phase_state(), status="complete", light_profile_allowed=True),
        "simple_profile_waiver_allowed": replace(
            final_phase_state(), status="complete", simple_profile_waiver_allowed=True
        ),
        "router_trace_event_not_authorized": replace(
            final_phase_state(), status="complete", router_authorized_trace_events=False
        ),
        "router_trace_validation_missing": replace(
            final_phase_state(), status="complete", router_validation_enforces_trace_fields=False
        ),
    }


def intended_upgrade_catalog() -> dict[str, dict[str, object]]:
    return {
        "requirement_traceability_upgrade": {
            "profile": replace(final_phase_state(), status="complete"),
            "interpretation": "modeled_safe_under_full_protocol_standalone_guards",
            "scope": (
                "stable product requirement ids, root deltas, route/node "
                "coverage, mutation stale-evidence guards, final ledger "
                "closure, and router validation"
            ),
            "runtime_readiness": "model_pass_required_before_template_card_router_edits",
        }
    }
