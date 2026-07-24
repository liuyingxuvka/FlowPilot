"""Focused FlowGuard child model for substantive-role complete workstreams.

The planning-quality parent continues to own project architecture, route
decomposition, acceptance boundaries, integration and closure. This child
owns one narrower question: once a substantive role receives one bounded
assignment, can it understand, plan, assess risk, execute, integrate, verify,
self-repair and report without leaking PM or Controller authority?
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_complete_workstream_orchestration"
MAX_SEQUENCE_LENGTH = 24
RESOURCE_BOUNDEDNESS_CHILD_BINDING = {
    "model_id": "flowpilot_control_plane_resource_boundedness",
    "owned_obligation": "one_obligation_level_workstream_plan_without_command_level_copies",
    "claim_boundary": "workstream orchestration retains completeness and review; the child owns material amplification",
}

SUBSTANTIVE_ROLES = (
    "pm",
    "worker",
    "research_worker",
    "human_like_reviewer",
    "flowguard_operator",
)


@dataclass(frozen=True)
class Tick:
    """One abstract role-work transition."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    role: str = "pm"
    status: str = "new"  # new | running | blocked | complete
    assignment_understood: bool = False
    numbered_plan_written_before_execution: bool = False
    plan_step_count: int = 0
    plan_steps_specific: bool = False
    risk_decision_recorded: bool = False
    role_local_flowguard_used: bool = False
    role_local_flowguard_advisory_only: bool = True
    formal_independent_gate_preserved: bool = True
    execution_completed: bool = False
    bounded_delegation_used: bool = False
    delegated_outputs_integrated: bool = True
    integration_completed: bool = False
    verification_completed: bool = False
    defect_found: bool = False
    in_scope_repair_completed: bool = False
    out_of_scope_issue_escalated: bool = True
    report_submitted: bool = False
    report_contains_plan_rows: bool = False
    report_step_statuses_consistent: bool = False
    report_evidence_matches_artifacts: bool = False
    report_deviations_explicit: bool = False
    report_unresolved_items_explicit: bool = False
    reviewer_audited_plan_against_artifacts: bool = False
    reviewer_score: int = 0
    pm_disposed_sub9_score: bool = False

    # Explicit known-bad controls.
    controller_substantive_plan: bool = False
    worker_changed_product_scope: bool = False
    worker_changed_route_or_acceptance: bool = False
    role_local_flowguard_self_approved: bool = False
    completion_claim_contradicts_plan: bool = False
    stale_evidence_used: bool = False
    vague_plan_accepted: bool = False
    missing_required_step_accepted: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_states() -> tuple[State, ...]:
    return tuple(State(role=role) for role in SUBSTANTIVE_ROLES)


class CompleteWorkstreamStep:
    """Input x State -> Set(Output x State) for one bounded role assignment.

    Reads the current role, assignment, plan, execution, verification, repair
    and report state. Writes only abstract role-local progress. It never writes
    route, product, acceptance or Controller state.
    """

    name = "CompleteWorkstreamStep"
    reads = (
        "role",
        "assignment_understood",
        "numbered_plan_written_before_execution",
        "risk_decision_recorded",
        "execution_completed",
        "integration_completed",
        "verification_completed",
        "report_submitted",
    )
    writes = (
        "role_local_plan",
        "risk_decision",
        "role_local_execution",
        "role_local_integration",
        "verification_and_repair",
        "role_authored_report",
        "reviewer_plan_audit",
        "pm_sub9_disposition",
    )
    input_description = "one substantive role-work tick"
    output_description = "one monotonic complete-workstream action"
    idempotency = "safe ticks only advance missing role-local evidence"

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
    failures = invariant_failures(state)
    if failures:
        return (
            Transition(
                "workstream_blocks_on_invariant_failure",
                replace(state, status="blocked"),
            ),
        )
    if state.status == "new":
        return (Transition("substantive_role_workstream_started", replace(state, status="running")),)
    if not state.assignment_understood:
        return (Transition("role_understands_bounded_assignment", replace(state, assignment_understood=True)),)
    if not state.numbered_plan_written_before_execution:
        return (
            Transition(
                "role_writes_specific_numbered_plan",
                replace(
                    state,
                    numbered_plan_written_before_execution=True,
                    plan_step_count=4,
                    plan_steps_specific=True,
                ),
            ),
        )
    if not state.risk_decision_recorded:
        return (
            Transition(
                "role_records_risk_and_flowguard_decision",
                replace(
                    state,
                    risk_decision_recorded=True,
                    role_local_flowguard_used=True,
                    role_local_flowguard_advisory_only=True,
                    formal_independent_gate_preserved=True,
                ),
            ),
        )
    if not state.execution_completed:
        return (
            Transition(
                "role_executes_bounded_plan",
                replace(
                    state,
                    execution_completed=True,
                    bounded_delegation_used=state.role in {"pm", "worker", "research_worker"},
                ),
            ),
        )
    if not state.integration_completed:
        return (
            Transition(
                "role_integrates_own_and_delegated_outputs",
                replace(state, integration_completed=True, delegated_outputs_integrated=True),
            ),
        )
    if not state.verification_completed:
        return (
            Transition(
                "role_verifies_and_self_repairs_in_scope",
                replace(
                    state,
                    verification_completed=True,
                    defect_found=True,
                    in_scope_repair_completed=True,
                    out_of_scope_issue_escalated=True,
                ),
            ),
        )
    if not state.report_submitted:
        return (
            Transition(
                "role_submits_plan_completion_report",
                replace(
                    state,
                    report_submitted=True,
                    report_contains_plan_rows=True,
                    report_step_statuses_consistent=True,
                    report_evidence_matches_artifacts=True,
                    report_deviations_explicit=True,
                    report_unresolved_items_explicit=True,
                ),
            ),
        )
    if not state.reviewer_audited_plan_against_artifacts:
        return (
            Transition(
                "reviewer_audits_plan_rows_against_artifacts",
                replace(state, reviewer_audited_plan_against_artifacts=True, reviewer_score=8),
            ),
        )
    if state.reviewer_score < 9 and not state.pm_disposed_sub9_score:
        return (
            Transition(
                "pm_disposes_sub9_reviewer_score",
                replace(state, pm_disposed_sub9_score=True),
            ),
        )
    return (Transition("substantive_role_workstream_complete", replace(state, status="complete")),)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.role not in SUBSTANTIVE_ROLES:
        failures.append("non-substantive Controller entered the substantive workstream lifecycle")
    if state.controller_substantive_plan:
        failures.append("Controller invented a substantive project or role plan")
    if state.worker_changed_product_scope:
        failures.append("Worker changed PM-owned product scope")
    if state.worker_changed_route_or_acceptance:
        failures.append("Worker changed PM-owned route or acceptance boundaries")
    if state.role_local_flowguard_self_approved:
        failures.append("role-local FlowGuard self-approved the role's own work")
    if state.role_local_flowguard_used and not state.role_local_flowguard_advisory_only:
        failures.append("role-local FlowGuard became an approval authority")
    if state.role_local_flowguard_used and not state.formal_independent_gate_preserved:
        failures.append("role-local FlowGuard replaced a required independent gate")
    if state.execution_completed and not state.numbered_plan_written_before_execution:
        failures.append("role executed before writing a numbered plan")
    if state.execution_completed and (state.plan_step_count < 2 or not state.plan_steps_specific):
        failures.append("role executed from a missing or vague plan")
    if state.vague_plan_accepted:
        failures.append("Reviewer accepted a vague plan as complete")
    if state.missing_required_step_accepted:
        failures.append("Reviewer accepted an incomplete required plan step")
    if state.integration_completed and state.bounded_delegation_used and not state.delegated_outputs_integrated:
        failures.append("delegated outputs were not integrated into the role's result")
    if state.report_submitted and not state.integration_completed:
        failures.append("role submitted before integrating its work")
    if state.report_submitted and not state.verification_completed:
        failures.append("role submitted without current verification")
    if state.report_submitted and state.defect_found and not state.in_scope_repair_completed:
        failures.append("role left a known in-scope defect unrepaired")
    if state.report_submitted and not state.out_of_scope_issue_escalated:
        failures.append("role silently ignored an out-of-scope issue")
    if state.report_submitted and not state.report_contains_plan_rows:
        failures.append("substantive report omitted numbered plan completion rows")
    if state.report_submitted and not state.report_step_statuses_consistent:
        failures.append("reported plan statuses contradict execution state")
    if state.report_submitted and not state.report_evidence_matches_artifacts:
        failures.append("reported plan evidence does not match actual artifacts")
    if state.report_submitted and not state.report_deviations_explicit:
        failures.append("substantive report hid plan deviations")
    if state.report_submitted and not state.report_unresolved_items_explicit:
        failures.append("substantive report hid unresolved work")
    if state.completion_claim_contradicts_plan:
        failures.append("completion claim contradicts incomplete plan rows")
    if state.stale_evidence_used:
        failures.append("role or Reviewer used stale evidence for completion")
    if state.reviewer_score and state.reviewer_score < 9 and state.status == "complete" and not state.pm_disposed_sub9_score:
        failures.append("PM silently ignored a Reviewer score below 9")
    if state.status == "complete":
        required = (
            state.assignment_understood,
            state.numbered_plan_written_before_execution,
            state.risk_decision_recorded,
            state.execution_completed,
            state.integration_completed,
            state.verification_completed,
            state.report_submitted,
            state.reviewer_audited_plan_against_artifacts,
        )
        if not all(required):
            failures.append("workstream completed before the full role lifecycle closed")
    return failures


def invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_substantive_role_complete_workstream",
        description=(
            "Every substantive role plans and completes one bounded workstream, "
            "reports plan status and evidence, preserves PM/Controller authority, "
            "and keeps role-local FlowGuard advisory."
        ),
        predicate=invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def build_workflow() -> Workflow:
    return Workflow((CompleteWorkstreamStep(),), name=MODEL_ID)


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def success_state(role: str = "worker") -> State:
    return State(
        role=role,
        status="complete",
        assignment_understood=True,
        numbered_plan_written_before_execution=True,
        plan_step_count=4,
        plan_steps_specific=True,
        risk_decision_recorded=True,
        role_local_flowguard_used=True,
        role_local_flowguard_advisory_only=True,
        formal_independent_gate_preserved=True,
        execution_completed=True,
        bounded_delegation_used=role in {"pm", "worker", "research_worker"},
        delegated_outputs_integrated=True,
        integration_completed=True,
        verification_completed=True,
        defect_found=True,
        in_scope_repair_completed=True,
        out_of_scope_issue_escalated=True,
        report_submitted=True,
        report_contains_plan_rows=True,
        report_step_statuses_consistent=True,
        report_evidence_matches_artifacts=True,
        report_deviations_explicit=True,
        report_unresolved_items_explicit=True,
        reviewer_audited_plan_against_artifacts=True,
        reviewer_score=8,
        pm_disposed_sub9_score=True,
    )


def hazard_states() -> dict[str, State]:
    base = success_state()
    return {
        "missing_plan": replace(base, numbered_plan_written_before_execution=False),
        "vague_plan": replace(base, plan_steps_specific=False, vague_plan_accepted=True),
        "incomplete_required_step": replace(base, missing_required_step_accepted=True),
        "completion_contradiction": replace(base, completion_claim_contradicts_plan=True),
        "evidence_mismatch": replace(base, report_evidence_matches_artifacts=False),
        "stale_evidence": replace(base, stale_evidence_used=True),
        "delegation_not_integrated": replace(base, delegated_outputs_integrated=False),
        "verification_missing": replace(base, verification_completed=False),
        "repair_missing": replace(base, in_scope_repair_completed=False),
        "unresolved_hidden": replace(base, report_unresolved_items_explicit=False),
        "role_local_flowguard_self_approval": replace(base, role_local_flowguard_self_approved=True),
        "formal_gate_replaced": replace(base, formal_independent_gate_preserved=False),
        "worker_product_scope_leak": replace(base, worker_changed_product_scope=True),
        "worker_route_authority_leak": replace(base, worker_changed_route_or_acceptance=True),
        "controller_substantive_plan": replace(
            base,
            role="controller",
            controller_substantive_plan=True,
        ),
        "pm_ignored_sub9": replace(base, pm_disposed_sub9_score=False),
    }
