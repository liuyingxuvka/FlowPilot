"""FlowGuard model for current-node route-change gates.

The historical filename is retained for the existing maintenance runner, but
the current contract no longer has a mandatory per-node pre-worker FlowGuard
gate. This focused child model now checks the current executable-node trunk:

* ordinary node entry: PM self-check -> Reviewer -> Worker -> post-result
  FlowGuard -> independent Reviewer;
* structural route change: PM route redesign -> FlowGuard simulation of the
  current route/work/validation/failure lines -> PM absorption -> Reviewer ->
  route mutation commit.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 28


@dataclass(frozen=True)
class Tick:
    """One node-entry or route-redesign transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    route_plan_generation: int = 0
    flowguard_generation: int = -1
    pm_absorption_generation: int = -1

    pm_self_checked_node: bool = False
    node_plan_decision: str = ""  # pass | redesign_route

    node_context_package_accepted: bool = False
    node_plan_reviewer_packet_issued: bool = False
    node_plan_reviewer_used_plan_stage_standard: bool = False
    node_plan_reviewer_required_worker_artifacts: bool = False
    node_plan_reviewer_treated_plan_as_result_proof: bool = False
    node_plan_reviewer_passed: bool = False
    worker_packet_issued: bool = False
    worker_context_attached: bool = False
    worker_result_submitted: bool = False
    post_result_flowguard_issued: bool = False
    post_result_flowguard_passed: bool = False
    final_reviewer_packet_issued: bool = False
    final_reviewer_independent: bool = False
    final_reviewer_used_result_stage_standard: bool = False
    final_reviewer_inspected_worker_artifacts: bool = False
    final_reviewer_passed: bool = False
    node_completed: bool = False

    route_plan_staged: bool = False
    route_redesign_flowguard_packet_issued: bool = False
    flowguard_current_subject_bound: bool = False
    flowguard_simulated_work_validation_failure_paths: bool = False
    flowguard_passed: bool = False
    flowguard_blocked: bool = False
    pm_route_repair_recorded: bool = False
    pm_flowguard_acceptance_packet_issued: bool = False
    pm_absorbed_flowguard: bool = False
    route_reviewer_packet_issued: bool = False
    route_reviewer_passed: bool = False
    route_mutation_committed: bool = False

    pm_made_flowguard_optional: bool = False
    flowguard_operator_mutated_route: bool = False
    flowguard_scope_missing: bool = False
    flowguard_validation_path_missing: bool = False
    pm_accepts_blocked_flowguard: bool = False
    route_mutation_without_pm_absorption: bool = False
    reviewer_before_pm_absorption: bool = False
    worker_started_before_node_plan_review: bool = False
    worker_replanned_broad_leaf: bool = False
    final_reviewer_accepted_without_worker_artifacts: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class CurrentNodeRouteGateStep:
    """Model one current node-entry or structural route-change tick.

    Input x State -> Set(Output x State)
    reads: PM node self-check, node plan decision, route redesign gate,
      FlowGuard report state, PM absorption, Reviewer state, worker state
    writes: the next monotonic gate transition
    idempotency: safe ticks either add the next required evidence or block
    """

    name = "CurrentNodeRouteGateStep"
    reads = (
        "pm_self_checked_node",
        "node_plan_decision",
        "route_plan_staged",
        "flowguard_passed",
        "pm_absorbed_flowguard",
        "node_plan_reviewer_passed",
        "worker_result_submitted",
        "post_result_flowguard_passed",
        "final_reviewer_passed",
    )
    writes = (
        "node_entry_self_check",
        "ordinary_node_reviewer",
        "worker_packet",
        "post_result_flowguard",
        "independent_reviewer",
        "route_redesign_flowguard",
        "pm_flowguard_acceptance",
        "route_reviewer",
        "route_mutation_commit",
    )
    input_description = "one FlowPilot current-node route gate tick"
    output_description = "one abstract runtime/role action"
    idempotency = "safe ticks never commit route effects without FlowGuard, PM absorption, and Reviewer"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _reset_redesign_after_pm_route_repair(state: State) -> State:
    return replace(
        state,
        route_plan_generation=state.route_plan_generation + 1,
        route_plan_staged=False,
        route_redesign_flowguard_packet_issued=False,
        flowguard_current_subject_bound=False,
        flowguard_simulated_work_validation_failure_paths=False,
        flowguard_passed=False,
        flowguard_blocked=False,
        pm_route_repair_recorded=True,
        pm_flowguard_acceptance_packet_issued=False,
        pm_absorbed_flowguard=False,
        route_reviewer_packet_issued=False,
        route_reviewer_passed=False,
        route_mutation_committed=False,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("current_node_route_gate_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("current_node_flow_started", replace(state, status="running")),)
    if not state.pm_self_checked_node:
        return (Transition("pm_self_checks_node_entry", replace(state, pm_self_checked_node=True)),)

    if not state.node_plan_decision:
        return (
            Transition("pm_passes_ordinary_node_plan", replace(state, node_plan_decision="pass")),
            Transition("pm_stages_route_redesign_plan", replace(state, node_plan_decision="redesign_route", route_plan_staged=True)),
        )

    if state.node_plan_decision == "pass":
        if not state.node_context_package_accepted:
            return (Transition("pm_records_node_context_package", replace(state, node_context_package_accepted=True)),)
        if not state.node_plan_reviewer_packet_issued:
            return (Transition("runtime_issues_node_plan_reviewer", replace(state, node_plan_reviewer_packet_issued=True)),)
        if not state.node_plan_reviewer_passed:
            return (
                Transition(
                    "reviewer_passes_node_plan",
                    replace(
                        state,
                        node_plan_reviewer_used_plan_stage_standard=True,
                        node_plan_reviewer_passed=True,
                    ),
                ),
            )
        if not state.worker_packet_issued:
            return (
                Transition(
                    "runtime_issues_worker_packet_after_reviewer",
                    replace(state, worker_packet_issued=True, worker_context_attached=True),
                ),
            )
        if not state.worker_result_submitted:
            return (Transition("worker_submits_node_result", replace(state, worker_result_submitted=True)),)
        if not state.post_result_flowguard_issued:
            return (Transition("runtime_issues_post_result_flowguard", replace(state, post_result_flowguard_issued=True)),)
        if not state.post_result_flowguard_passed:
            return (Transition("post_result_flowguard_passes", replace(state, post_result_flowguard_passed=True)),)
        if not state.final_reviewer_packet_issued:
            return (Transition("runtime_issues_independent_reviewer_packet", replace(state, final_reviewer_packet_issued=True)),)
        if not state.final_reviewer_passed:
            return (
                Transition(
                    "reviewer_passes_independently",
                    replace(
                        state,
                        final_reviewer_independent=True,
                        final_reviewer_used_result_stage_standard=True,
                        final_reviewer_inspected_worker_artifacts=True,
                        final_reviewer_passed=True,
                    ),
                ),
            )
        if not state.node_completed:
            return (Transition("node_completed_after_reviewer", replace(state, node_completed=True)),)
        return (Transition("current_node_flow_complete", replace(state, status="complete")),)

    if state.node_plan_decision == "redesign_route":
        if not state.route_plan_staged:
            return (Transition("pm_stages_route_redesign_plan", replace(state, route_plan_staged=True)),)
        if not state.route_redesign_flowguard_packet_issued:
            return (Transition("runtime_issues_route_redesign_flowguard", replace(state, route_redesign_flowguard_packet_issued=True)),)
        if not state.flowguard_current_subject_bound or not state.flowguard_simulated_work_validation_failure_paths:
            return (
                Transition(
                    "flowguard_simulates_current_route_plan",
                    replace(
                        state,
                        flowguard_current_subject_bound=True,
                        flowguard_simulated_work_validation_failure_paths=True,
                    ),
                ),
            )
        if not state.flowguard_passed and not state.flowguard_blocked:
            transitions = [
                Transition(
                    "flowguard_route_redesign_passes",
                    replace(state, flowguard_passed=True, flowguard_generation=state.route_plan_generation),
                )
            ]
            if state.route_plan_generation == 0:
                transitions.append(
                    Transition("flowguard_route_redesign_blocks", replace(state, flowguard_blocked=True))
                )
            return tuple(transitions)
        if state.flowguard_blocked and state.route_plan_generation == 0:
            return (
                Transition("pm_repairs_route_plan_after_flowguard_block", _reset_redesign_after_pm_route_repair(state)),
            )
        if not state.pm_flowguard_acceptance_packet_issued:
            return (
                Transition(
                    "runtime_issues_pm_flowguard_acceptance_packet",
                    replace(state, pm_flowguard_acceptance_packet_issued=True),
                ),
            )
        if not state.pm_absorbed_flowguard:
            if state.route_plan_generation == 0:
                return (
                    Transition("pm_absorbs_flowguard_report", replace(state, pm_absorbed_flowguard=True, pm_absorption_generation=state.route_plan_generation)),
                    Transition("pm_rewrites_route_from_flowguard_advice", _reset_redesign_after_pm_route_repair(state)),
                )
            return (
                Transition(
                    "pm_absorbs_flowguard_report",
                    replace(state, pm_absorbed_flowguard=True, pm_absorption_generation=state.route_plan_generation),
                ),
            )
        if not state.route_reviewer_packet_issued:
            return (Transition("runtime_issues_route_redesign_reviewer_packet", replace(state, route_reviewer_packet_issued=True)),)
        if not state.route_reviewer_passed:
            return (Transition("reviewer_passes_pm_absorption_package", replace(state, route_reviewer_passed=True)),)
        if not state.route_mutation_committed:
            return (Transition("route_redesign_committed_after_review", replace(state, route_mutation_committed=True)),)
        return (Transition("route_redesign_flow_complete", replace(state, status="complete")),)

    return (Transition("current_node_route_gate_blocked_on_unknown_decision", replace(state, status="blocked")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    current_flowguard = state.flowguard_passed and state.flowguard_generation == state.route_plan_generation
    current_pm_absorption = (
        state.pm_absorbed_flowguard and state.pm_absorption_generation == state.route_plan_generation
    )

    if state.pm_made_flowguard_optional:
        failures.append("PM made structural route FlowGuard optional")
    if state.flowguard_operator_mutated_route:
        failures.append("FlowGuard operator mutated route instead of reporting to PM")
    if state.flowguard_scope_missing:
        failures.append("FlowGuard did not bind the current route plan as simulation subject")
    if state.flowguard_validation_path_missing:
        failures.append("FlowGuard did not simulate work, validation, failure, and repair paths")
    if state.pm_accepts_blocked_flowguard:
        failures.append("PM accepted a blocked FlowGuard route result")
    if state.route_mutation_without_pm_absorption:
        failures.append("route mutation committed without PM FlowGuard absorption")
    if state.reviewer_before_pm_absorption:
        failures.append("Reviewer inspected route effect before PM absorbed FlowGuard result")
    if state.worker_started_before_node_plan_review:
        failures.append("worker packet issued before ordinary node plan Reviewer pass")
    if state.worker_replanned_broad_leaf:
        failures.append("Worker replanned a broad leaf instead of PM route deepening")
    if state.node_plan_reviewer_required_worker_artifacts:
        failures.append("Node plan Reviewer required Worker artifacts before Worker dispatch")
    if state.node_plan_reviewer_treated_plan_as_result_proof:
        failures.append("Node plan Reviewer treated PM plan as Worker-result proof")
    if state.final_reviewer_accepted_without_worker_artifacts:
        failures.append("Worker result Reviewer accepted without current Worker artifacts")

    if state.node_plan_decision == "pass":
        if state.worker_packet_issued and not state.node_plan_reviewer_passed:
            failures.append("worker packet issued before ordinary node plan Reviewer pass")
        if state.worker_packet_issued and not state.node_context_package_accepted:
            failures.append("worker packet issued without PM node context package")
        if state.worker_packet_issued and not state.worker_context_attached:
            failures.append("worker packet missing PM node context package")
        if state.node_plan_reviewer_passed and not state.node_plan_reviewer_used_plan_stage_standard:
            failures.append("node plan Reviewer passed without plan-stage review standard")
        if state.worker_result_submitted and not state.worker_packet_issued:
            failures.append("worker result submitted before worker packet")
        if state.post_result_flowguard_issued and not state.worker_result_submitted:
            failures.append("post-result FlowGuard issued before worker result")
        if state.post_result_flowguard_passed and not state.post_result_flowguard_issued:
            failures.append("post-result FlowGuard pass without packet")
        if state.final_reviewer_packet_issued and not state.post_result_flowguard_passed:
            failures.append("Reviewer packet issued before post-result FlowGuard pass")
        if state.final_reviewer_passed and not state.final_reviewer_packet_issued:
            failures.append("Reviewer passed before Reviewer packet")
        if state.final_reviewer_passed and not state.final_reviewer_independent:
            failures.append("Reviewer pass was not independent")
        if state.final_reviewer_passed and not state.final_reviewer_used_result_stage_standard:
            failures.append("Worker result Reviewer passed without result-stage review standard")
        if state.final_reviewer_passed and not state.final_reviewer_inspected_worker_artifacts:
            failures.append("Worker result Reviewer passed without current Worker artifacts")
        if state.node_completed and not state.final_reviewer_passed:
            failures.append("node completed before independent Reviewer pass")

    if state.node_plan_decision == "redesign_route":
        if state.route_redesign_flowguard_packet_issued and not state.route_plan_staged:
            failures.append("route FlowGuard issued before PM staged route plan")
        if state.flowguard_passed and not state.route_redesign_flowguard_packet_issued:
            failures.append("FlowGuard route pass without packet")
        if state.flowguard_passed and not state.flowguard_current_subject_bound:
            failures.append("FlowGuard passed without binding current route plan")
        if state.flowguard_passed and not state.flowguard_simulated_work_validation_failure_paths:
            failures.append("FlowGuard passed without simulating work, validation, failure, and repair paths")
        if state.pm_flowguard_acceptance_packet_issued and not current_flowguard:
            failures.append("PM FlowGuard acceptance packet issued before current FlowGuard pass")
        if state.pm_absorbed_flowguard and not state.pm_flowguard_acceptance_packet_issued:
            failures.append("PM absorbed FlowGuard without pm_flowguard_acceptance packet")
        if state.pm_absorbed_flowguard and not current_flowguard:
            failures.append("PM absorbed stale or missing FlowGuard result")
        if state.route_reviewer_packet_issued and not current_pm_absorption:
            failures.append("Reviewer packet issued before current PM FlowGuard absorption")
        if state.route_reviewer_passed and not state.route_reviewer_packet_issued:
            failures.append("Reviewer passed route effect before packet")
        if state.route_mutation_committed and not state.route_reviewer_passed:
            failures.append("route mutation committed before Reviewer pass")
        if state.route_mutation_committed and not current_pm_absorption:
            failures.append("route mutation committed without current PM FlowGuard absorption")

    if state.status == "complete":
        ordinary_complete = state.node_plan_decision == "pass" and state.node_completed
        redesign_complete = state.node_plan_decision == "redesign_route" and state.route_mutation_committed
        if not ordinary_complete and not redesign_complete:
            failures.append("flow completed before ordinary node or route redesign completion")
    return failures


def invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_current_node_route_change_gate",
        description=(
            "Ordinary node entry reaches Worker through Reviewer without "
            "pre-worker FlowGuard; structural route changes require current "
            "FlowGuard simulation, PM absorption, and Reviewer before commit."
        ),
        predicate=invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CurrentNodeRouteGateStep(),), name="flowpilot_current_node_route_change_gate")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def target_success_state() -> State:
    return State(
        status="complete",
        route_plan_generation=1,
        flowguard_generation=1,
        pm_absorption_generation=1,
        pm_self_checked_node=True,
        node_plan_decision="redesign_route",
        route_plan_staged=True,
        route_redesign_flowguard_packet_issued=True,
        flowguard_current_subject_bound=True,
        flowguard_simulated_work_validation_failure_paths=True,
        flowguard_passed=True,
        flowguard_blocked=False,
        pm_route_repair_recorded=True,
        pm_flowguard_acceptance_packet_issued=True,
        pm_absorbed_flowguard=True,
        route_reviewer_packet_issued=True,
        route_reviewer_passed=True,
        route_mutation_committed=True,
    )


def ordinary_node_success_state() -> State:
    return State(
        status="complete",
        pm_self_checked_node=True,
        node_plan_decision="pass",
        node_context_package_accepted=True,
        node_plan_reviewer_packet_issued=True,
        node_plan_reviewer_used_plan_stage_standard=True,
        node_plan_reviewer_passed=True,
        worker_packet_issued=True,
        worker_context_attached=True,
        worker_result_submitted=True,
        post_result_flowguard_issued=True,
        post_result_flowguard_passed=True,
        final_reviewer_packet_issued=True,
        final_reviewer_independent=True,
        final_reviewer_used_result_stage_standard=True,
        final_reviewer_inspected_worker_artifacts=True,
        final_reviewer_passed=True,
        node_completed=True,
    )


def hazard_states() -> dict[str, State]:
    route_base = target_success_state()
    ordinary_base = ordinary_node_success_state()
    return {
        "pm_optional_flowguard": replace(route_base, pm_made_flowguard_optional=True),
        "flowguard_scope_missing": replace(route_base, flowguard_scope_missing=True),
        "flowguard_validation_path_missing": replace(route_base, flowguard_validation_path_missing=True),
        "flowguard_operator_route_mutation": replace(route_base, flowguard_operator_mutated_route=True),
        "pm_accepts_blocked_flowguard": replace(route_base, pm_accepts_blocked_flowguard=True),
        "stale_flowguard_after_route_rewrite": replace(route_base, flowguard_generation=0),
        "reviewer_before_pm_absorption": replace(route_base, reviewer_before_pm_absorption=True),
        "route_mutation_without_pm_absorption": replace(route_base, route_mutation_without_pm_absorption=True),
        "route_reviewer_before_pm_absorption": replace(route_base, pm_absorbed_flowguard=False, route_reviewer_packet_issued=True),
        "route_commit_before_reviewer": replace(route_base, route_reviewer_passed=False),
        "worker_before_node_plan_reviewer": replace(ordinary_base, worker_started_before_node_plan_review=True),
        "worker_context_missing": replace(ordinary_base, worker_context_attached=False),
        "worker_replans_broad_leaf": replace(ordinary_base, worker_replanned_broad_leaf=True),
        "node_plan_reviewer_demands_worker_artifacts": replace(
            ordinary_base,
            node_plan_reviewer_required_worker_artifacts=True,
        ),
        "node_plan_reviewer_treats_plan_as_result_proof": replace(
            ordinary_base,
            node_plan_reviewer_treated_plan_as_result_proof=True,
        ),
        "post_result_flowguard_skipped": replace(ordinary_base, post_result_flowguard_passed=False),
        "reviewer_not_independent": replace(ordinary_base, final_reviewer_independent=False),
        "final_reviewer_without_artifacts": replace(
            ordinary_base,
            final_reviewer_inspected_worker_artifacts=False,
        ),
        "final_reviewer_accepts_without_worker_artifacts": replace(
            ordinary_base,
            final_reviewer_accepted_without_worker_artifacts=True,
        ),
    }
