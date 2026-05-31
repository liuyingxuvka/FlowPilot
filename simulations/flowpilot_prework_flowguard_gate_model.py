"""FlowGuard model for FlowPilot mandatory node pre-work FlowGuard gates.

This focused child model checks the executable node handoff:
PM accepts the node design and context package, runtime issues a FlowGuard pre-work gate,
the FlowGuard operator selects route(s) and records PM-visible artifacts,
worker execution is released only after a current-generation pre-work pass,
and the existing post-result FlowGuard plus independent Reviewer gates remain.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 24


@dataclass(frozen=True)
class Tick:
    """One node-gate transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    repair_generation: int = 0
    prework_pass_generation: int = -1
    context_package_generation: int = -1

    pm_node_design_accepted: bool = False
    pm_context_package_accepted: bool = False
    prework_packet_issued: bool = False
    prework_context_attached: bool = False
    prework_routes_selected: bool = False
    prework_artifacts_pm_visible: bool = False
    prework_passed: bool = False
    prework_blocked: bool = False
    pm_repair_decision_recorded: bool = False

    worker_packet_issued: bool = False
    worker_context_attached: bool = False
    worker_result_submitted: bool = False
    post_result_flowguard_issued: bool = False
    post_result_context_attached: bool = False
    post_result_flowguard_passed: bool = False
    reviewer_packet_issued: bool = False
    reviewer_context_attached: bool = False
    reviewer_independent: bool = False
    reviewer_passed: bool = False
    node_completed: bool = False

    pm_made_prework_optional: bool = False
    flowguard_operator_mutated_route: bool = False
    worker_started_without_prework: bool = False
    worker_started_without_context: bool = False
    reviewer_scoped_by_pm_only: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class NodePreworkFlowGuardStep:
    """Model one node-gate handoff.

    Input x State -> Set(Output x State)
    reads: PM node design, pre-work FlowGuard gate status, repair generation,
      worker packet status, post-result FlowGuard status, Reviewer status
    writes: the next monotonic node-gate transition
    idempotency: safe ticks either add required evidence or stop on blockers
    """

    name = "NodePreworkFlowGuardStep"
    reads = (
        "pm_node_design_accepted",
        "pm_context_package_accepted",
        "prework_packet_issued",
        "prework_pass_generation",
        "worker_packet_issued",
        "post_result_flowguard_passed",
        "reviewer_passed",
    )
    writes = (
        "pm_node_design",
        "pm_node_context_package",
        "prework_flowguard_gate",
        "pm_repair_decision",
        "worker_packet",
        "post_result_flowguard",
        "independent_reviewer",
        "node_completion",
    )
    input_description = "one FlowPilot route-node gate tick"
    output_description = "one abstract runtime/role action"
    idempotency = "safe ticks never release worker execution without current pre-work FlowGuard"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _reset_prework_after_repair(state: State) -> State:
    return replace(
        state,
        repair_generation=state.repair_generation + 1,
        pm_node_design_accepted=True,
        pm_context_package_accepted=False,
        context_package_generation=-1,
        prework_packet_issued=False,
        prework_context_attached=False,
        prework_routes_selected=False,
        prework_artifacts_pm_visible=False,
        prework_passed=False,
        prework_blocked=False,
        pm_repair_decision_recorded=True,
    )


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("node_prework_flow_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.status == "new":
        return (Transition("node_prework_flow_started", replace(state, status="running")),)
    if not state.pm_node_design_accepted:
        return (Transition("pm_accepts_node_design", replace(state, pm_node_design_accepted=True)),)
    if not state.pm_context_package_accepted:
        return (
            Transition(
                "pm_records_node_context_package",
                replace(
                    state,
                    pm_context_package_accepted=True,
                    context_package_generation=state.repair_generation,
                ),
            ),
        )
    if not state.prework_packet_issued:
        return (
            Transition(
                "runtime_issues_prework_flowguard_packet",
                replace(state, prework_packet_issued=True, prework_context_attached=True),
            ),
        )
    if not state.prework_routes_selected:
        return (Transition("flowguard_operator_selects_route_mix", replace(state, prework_routes_selected=True)),)
    if not state.prework_artifacts_pm_visible:
        return (
            Transition(
                "flowguard_operator_records_pm_visible_artifacts",
                replace(state, prework_artifacts_pm_visible=True),
            ),
        )
    if not state.prework_passed and not state.prework_blocked:
        transitions = [
            Transition(
                "flowguard_prework_passes_current_generation",
                replace(
                    state,
                    prework_passed=True,
                    prework_pass_generation=state.repair_generation,
                ),
            )
        ]
        if state.repair_generation == 0:
            transitions.append(
                Transition(
                    "flowguard_prework_blocks_node_design",
                    replace(state, prework_blocked=True),
                )
            )
        return tuple(transitions)
    if state.prework_blocked and state.repair_generation == 0:
        return (Transition("pm_repairs_node_design_after_prework_block", _reset_prework_after_repair(state)),)
    if not state.worker_packet_issued:
        return (
            Transition(
                "runtime_issues_worker_packet_after_prework",
                replace(state, worker_packet_issued=True, worker_context_attached=True),
            ),
        )
    if not state.worker_result_submitted:
        return (Transition("worker_submits_node_result", replace(state, worker_result_submitted=True)),)
    if not state.post_result_flowguard_issued:
        return (
            Transition(
                "runtime_issues_post_result_flowguard",
                replace(state, post_result_flowguard_issued=True, post_result_context_attached=True),
            ),
        )
    if not state.post_result_flowguard_passed:
        return (
            Transition(
                "post_result_flowguard_passes",
                replace(state, post_result_flowguard_passed=True),
            ),
        )
    if not state.reviewer_packet_issued:
        return (
            Transition(
                "runtime_issues_independent_reviewer_packet",
                replace(state, reviewer_packet_issued=True, reviewer_context_attached=True),
            ),
        )
    if not state.reviewer_passed:
        return (
            Transition(
                "reviewer_passes_independently",
                replace(state, reviewer_independent=True, reviewer_passed=True),
            ),
        )
    if not state.node_completed:
        return (Transition("node_completed_after_reviewer", replace(state, node_completed=True)),)
    return (Transition("node_prework_flow_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    current_prework_pass = state.prework_passed and state.prework_pass_generation == state.repair_generation
    current_context = state.pm_context_package_accepted and state.context_package_generation == state.repair_generation
    if state.pm_made_prework_optional:
        failures.append("PM made mandatory pre-work FlowGuard optional")
    if state.pm_context_package_accepted and not state.pm_node_design_accepted:
        failures.append("PM context package recorded before node design")
    if state.pm_context_package_accepted and state.context_package_generation != state.repair_generation:
        failures.append("PM context package is stale for repair generation")
    if state.prework_packet_issued and not current_context:
        failures.append("pre-work FlowGuard issued before current PM node context package")
    if state.prework_packet_issued and not state.prework_context_attached:
        failures.append("pre-work FlowGuard packet missing PM node context package")
    if state.prework_packet_issued and not state.pm_node_design_accepted:
        failures.append("pre-work FlowGuard issued before PM node design")
    if state.prework_routes_selected and not state.prework_packet_issued:
        failures.append("FlowGuard route mix selected before pre-work packet")
    if state.prework_artifacts_pm_visible and not state.prework_routes_selected:
        failures.append("PM-visible artifacts recorded before FlowGuard route selection")
    if state.prework_passed and not state.prework_artifacts_pm_visible:
        failures.append("pre-work FlowGuard passed before PM-visible artifacts")
    if state.prework_blocked and state.worker_packet_issued and not state.pm_repair_decision_recorded:
        failures.append("worker released after pre-work block without PM repair")
    if state.worker_packet_issued and not current_prework_pass:
        failures.append("worker packet issued before current-generation pre-work FlowGuard pass")
    if state.worker_packet_issued and (not current_context or not state.worker_context_attached):
        failures.append("worker packet issued without current PM node context package")
    if state.worker_started_without_prework:
        failures.append("worker started without pre-work FlowGuard")
    if state.worker_started_without_context:
        failures.append("worker started without PM node context package")
    if state.flowguard_operator_mutated_route:
        failures.append("FlowGuard operator mutated route instead of reporting to PM")
    if state.worker_result_submitted and not state.worker_packet_issued:
        failures.append("worker result submitted before worker packet")
    if state.post_result_flowguard_issued and not state.worker_result_submitted:
        failures.append("post-result FlowGuard issued before worker result")
    if state.post_result_flowguard_issued and (not current_context or not state.post_result_context_attached):
        failures.append("post-result FlowGuard packet missing PM node context package")
    if state.post_result_flowguard_passed and not state.post_result_flowguard_issued:
        failures.append("post-result FlowGuard pass without packet")
    if state.reviewer_packet_issued and not state.post_result_flowguard_passed:
        failures.append("Reviewer packet issued before post-result FlowGuard pass")
    if state.reviewer_packet_issued and (not current_context or not state.reviewer_context_attached):
        failures.append("Reviewer packet missing PM node context package")
    if state.reviewer_passed and not state.reviewer_packet_issued:
        failures.append("Reviewer passed before Reviewer packet")
    if state.reviewer_passed and not state.reviewer_independent:
        failures.append("Reviewer pass was not independent")
    if state.reviewer_scoped_by_pm_only:
        failures.append("Reviewer was scoped only by PM rather than independent node contract review")
    if state.node_completed and not state.reviewer_passed:
        failures.append("node completed before independent Reviewer pass")
    if state.status == "complete" and not state.node_completed:
        failures.append("flow completed before node completion")
    return failures


def invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_prework_flowguard_node_gate",
        description=(
            "Worker execution is released only after a current-generation "
            "pre-work FlowGuard pass; post-result FlowGuard and independent "
            "Reviewer gates still follow worker evidence."
        ),
        predicate=invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((NodePreworkFlowGuardStep(),), name="flowpilot_prework_flowguard_node_gate")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def target_success_state() -> State:
    return State(
        status="complete",
        repair_generation=1,
        prework_pass_generation=1,
        context_package_generation=1,
        pm_node_design_accepted=True,
        pm_context_package_accepted=True,
        prework_packet_issued=True,
        prework_context_attached=True,
        prework_routes_selected=True,
        prework_artifacts_pm_visible=True,
        prework_passed=True,
        prework_blocked=False,
        pm_repair_decision_recorded=True,
        worker_packet_issued=True,
        worker_context_attached=True,
        worker_result_submitted=True,
        post_result_flowguard_issued=True,
        post_result_context_attached=True,
        post_result_flowguard_passed=True,
        reviewer_packet_issued=True,
        reviewer_context_attached=True,
        reviewer_independent=True,
        reviewer_passed=True,
        node_completed=True,
    )


def hazard_states() -> dict[str, State]:
    base = target_success_state()
    return {
        "pm_optional_prework": replace(base, pm_made_prework_optional=True),
        "context_before_node_design": replace(base, pm_node_design_accepted=False),
        "stale_context_after_repair": replace(base, context_package_generation=0),
        "prework_context_missing": replace(base, prework_context_attached=False),
        "prework_before_node_design": replace(base, pm_node_design_accepted=False),
        "route_mix_missing": replace(base, prework_routes_selected=False),
        "pm_visible_artifacts_missing": replace(base, prework_artifacts_pm_visible=False),
        "stale_prework_after_repair": replace(base, prework_pass_generation=0),
        "worker_before_prework": replace(base, prework_passed=False),
        "worker_context_missing": replace(base, worker_context_attached=False),
        "prework_block_without_pm_repair": replace(
            base,
            prework_blocked=True,
            pm_repair_decision_recorded=False,
        ),
        "flowguard_operator_route_mutation": replace(base, flowguard_operator_mutated_route=True),
        "post_result_context_missing": replace(base, post_result_context_attached=False),
        "post_result_flowguard_skipped": replace(base, post_result_flowguard_passed=False),
        "reviewer_before_post_result_flowguard": replace(base, post_result_flowguard_passed=False),
        "reviewer_context_missing": replace(base, reviewer_context_attached=False),
        "reviewer_not_independent": replace(base, reviewer_independent=False),
        "reviewer_pm_scoped_only": replace(base, reviewer_scoped_by_pm_only=True),
    }
