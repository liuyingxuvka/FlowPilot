"""FlowGuard model for FlowPilot FlowGuard-first role work orders.

This focused child model checks the new decision-core obligation chain:
PM creates or cites a FlowGuard Work Order, an FlowGuard operator returns a current
FlowGuard Report, PM accepts or dispositions it, Workers return only
packet-scoped FlowGuard obligation coverage, Reviewers check report freshness
and scope before passing gates, and Controller remains status-only.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MAX_SEQUENCE_LENGTH = 12


@dataclass(frozen=True)
class Tick:
    """One FlowGuard work-order transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete

    nontrivial_judgement: bool = True
    flowguard_not_required_reason: bool = False

    pm_work_order_written: bool = False
    pm_decision_made: bool = False
    report_returned: bool = False
    report_scope_matches: bool = False
    report_current: bool = False
    report_skipped_checks_dispositioned: bool = False
    report_progress_only: bool = False
    report_pm_accepted: bool = False

    flowguard_operator_answered_work_order: bool = False
    flowguard_operator_approved_gate: bool = False
    flowguard_operator_mutated_route: bool = False

    worker_obligations_assigned: bool = False
    worker_returned_packet_scoped_coverage: bool = False
    worker_mutated_route: bool = False
    worker_waived_report_gap: bool = False

    reviewer_checked_report: bool = False
    reviewer_passed_gate: bool = False
    reviewer_reran_model_without_pm_route: bool = False

    controller_surfaced_status: bool = False
    controller_interpreted_report: bool = False
    controller_approved_gate: bool = False

    terminal_closure_approved: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class FlowGuardWorkOrderStep:
    """Model one role work-order handoff.

    Input x State -> Set(Output x State)
    reads: PM work-order/report status, role authority flags, reviewer checks,
      controller status flags
    writes: the next monotonic role obligation step
    idempotency: safe ticks only add required evidence or settle terminal state
    """

    name = "FlowGuardWorkOrderStep"
    reads = (
        "pm_work_order_written",
        "report_returned",
        "report_current",
        "report_pm_accepted",
        "worker_returned_packet_scoped_coverage",
        "reviewer_checked_report",
        "controller_surfaced_status",
    )
    writes = (
        "pm_work_order",
        "flowguard_report",
        "pm_acceptance",
        "worker_coverage",
        "reviewer_gate",
        "controller_status",
        "terminal_closure",
    )
    input_description = "one FlowPilot FlowGuard-first decision-core tick"
    output_description = "one abstract role work-order action"
    idempotency = "safe ticks are monotonic and do not transfer PM authority"

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
        return (Transition("flowguard_work_order_run_started", replace(state, status="running")),)
    failures = invariant_failures(state)
    if failures:
        return (Transition("flowguard_work_order_blocked_on_invariant_failure", replace(state, status="blocked")),)
    if state.nontrivial_judgement and not state.pm_work_order_written:
        return (Transition("pm_writes_flowguard_work_order", replace(state, pm_work_order_written=True)),)
    if not state.nontrivial_judgement and not state.flowguard_not_required_reason:
        return (
            Transition(
                "pm_records_flowguard_not_required_reason",
                replace(state, flowguard_not_required_reason=True),
            ),
        )
    if state.pm_work_order_written and not state.report_returned:
        return (
            Transition(
                "flowguard_operator_returns_current_flowguard_report",
                replace(
                    state,
                    flowguard_operator_answered_work_order=True,
                    report_returned=True,
                    report_scope_matches=True,
                    report_current=True,
                    report_skipped_checks_dispositioned=True,
                    report_progress_only=False,
                ),
            ),
        )
    if state.report_returned and not state.report_pm_accepted:
        return (Transition("pm_accepts_flowguard_report", replace(state, report_pm_accepted=True, pm_decision_made=True)),)
    if state.report_pm_accepted and not state.worker_obligations_assigned:
        return (Transition("pm_assigns_packet_scoped_flowguard_obligations", replace(state, worker_obligations_assigned=True)),)
    if state.worker_obligations_assigned and not state.worker_returned_packet_scoped_coverage:
        return (
            Transition(
                "worker_returns_flowguard_obligation_coverage",
                replace(state, worker_returned_packet_scoped_coverage=True),
            ),
        )
    if state.report_pm_accepted and state.worker_returned_packet_scoped_coverage and not state.reviewer_checked_report:
        return (Transition("reviewer_checks_flowguard_report_support", replace(state, reviewer_checked_report=True)),)
    if state.reviewer_checked_report and not state.reviewer_passed_gate:
        return (Transition("reviewer_passes_flowguard_backed_gate", replace(state, reviewer_passed_gate=True)),)
    if state.reviewer_passed_gate and not state.controller_surfaced_status:
        return (Transition("controller_surfaces_flowguard_status_only", replace(state, controller_surfaced_status=True)),)
    if state.controller_surfaced_status and not state.terminal_closure_approved:
        return (Transition("pm_approves_closure_after_report_chain", replace(state, terminal_closure_approved=True)),)
    return (Transition("flowguard_work_order_flow_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.nontrivial_judgement and state.pm_decision_made and not state.pm_work_order_written:
        failures.append("PM made a non-trivial decision without a FlowGuard Work Order")
    if state.nontrivial_judgement and state.pm_decision_made and not state.report_returned:
        failures.append("PM made a non-trivial decision without a FlowGuard Report")
    if state.flowguard_not_required_reason and state.nontrivial_judgement:
        failures.append("PM used flowguard_not_required_reason for non-trivial judgement")
    if state.report_returned and not state.flowguard_operator_answered_work_order:
        failures.append("FlowGuard report was not tied to an FlowGuard operator work-order answer")
    if state.report_pm_accepted and not state.report_scope_matches:
        failures.append("PM accepted a wrongly scoped FlowGuard report")
    if state.report_pm_accepted and not state.report_current:
        failures.append("PM accepted a stale FlowGuard report")
    if state.report_pm_accepted and state.report_progress_only:
        failures.append("PM accepted progress-only FlowGuard evidence")
    if state.report_pm_accepted and not state.report_skipped_checks_dispositioned:
        failures.append("PM accepted skipped FlowGuard checks without disposition")
    if state.flowguard_operator_approved_gate:
        failures.append("FlowGuard operator used FlowGuard report to approve a gate")
    if state.flowguard_operator_mutated_route:
        failures.append("FlowGuard operator used FlowGuard report to mutate the route")
    if state.worker_returned_packet_scoped_coverage and not state.worker_obligations_assigned:
        failures.append("Worker returned FlowGuard coverage without assigned obligations")
    if state.worker_mutated_route:
        failures.append("Worker used FlowGuard obligation coverage to mutate the route")
    if state.worker_waived_report_gap:
        failures.append("Worker waived a FlowGuard report gap")
    if state.reviewer_passed_gate and not state.reviewer_checked_report:
        failures.append("Reviewer passed a FlowGuard-backed gate without checking the report")
    if state.reviewer_passed_gate and not state.report_pm_accepted:
        failures.append("Reviewer passed before PM accepted the FlowGuard report")
    if state.reviewer_passed_gate and (not state.report_current or state.report_progress_only):
        failures.append("Reviewer passed with stale or progress-only FlowGuard evidence")
    if state.reviewer_reran_model_without_pm_route:
        failures.append("Reviewer reran FlowGuard modeling without PM-routed work authority")
    if state.controller_interpreted_report:
        failures.append("Controller interpreted FlowGuard report contents")
    if state.controller_approved_gate:
        failures.append("Controller approved a gate from FlowGuard status")
    if state.terminal_closure_approved and not state.reviewer_passed_gate:
        failures.append("PM closure approved before Reviewer passed the FlowGuard-backed gate")
    if state.status == "complete" and not state.terminal_closure_approved:
        failures.append("FlowGuard work-order flow completed before terminal closure approval")
    return failures


def flowguard_work_order_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_flowguard_work_order_role_chain",
        description=(
            "FlowPilot may use FlowGuard as the decision core only when PM owns "
            "the work order and acceptance, FlowGuard operators produce reports without "
            "gate authority, Reviewers check report support, Workers stay "
            "packet-scoped, and Controller remains status-only."
        ),
        predicate=flowguard_work_order_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((FlowGuardWorkOrderStep(),), name="flowpilot_flowguard_work_order_role_chain")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def target_success_state() -> State:
    return State(
        status="complete",
        pm_work_order_written=True,
        pm_decision_made=True,
        report_returned=True,
        report_scope_matches=True,
        report_current=True,
        report_skipped_checks_dispositioned=True,
        report_pm_accepted=True,
        flowguard_operator_answered_work_order=True,
        worker_obligations_assigned=True,
        worker_returned_packet_scoped_coverage=True,
        reviewer_checked_report=True,
        reviewer_passed_gate=True,
        controller_surfaced_status=True,
        terminal_closure_approved=True,
    )


def hazard_states() -> dict[str, State]:
    base = target_success_state()
    return {
        "missing_work_order": replace(base, pm_work_order_written=False),
        "missing_report": replace(base, report_returned=False),
        "stale_report": replace(base, report_current=False),
        "wrong_scope_report": replace(base, report_scope_matches=False),
        "progress_only_report": replace(base, report_progress_only=True),
        "skipped_checks_not_dispositioned": replace(base, report_skipped_checks_dispositioned=False),
        "unaccepted_report": replace(base, report_pm_accepted=False),
        "flowguard_operator_gate_approval": replace(base, flowguard_operator_approved_gate=True),
        "flowguard_operator_route_mutation": replace(base, flowguard_operator_mutated_route=True),
        "reviewer_bypasses_report_check": replace(base, reviewer_checked_report=False),
        "reviewer_reruns_without_pm_route": replace(base, reviewer_reran_model_without_pm_route=True),
        "worker_route_mutation": replace(base, worker_mutated_route=True),
        "worker_waives_report_gap": replace(base, worker_waived_report_gap=True),
        "controller_interprets_report": replace(base, controller_interpreted_report=True),
        "controller_gate_approval": replace(base, controller_approved_gate=True),
        "closure_before_reviewer_pass": replace(base, reviewer_passed_gate=False),
        "not_required_used_for_nontrivial": replace(base, flowguard_not_required_reason=True),
    }
