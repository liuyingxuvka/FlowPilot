"""FlowGuard model for FlowPilot validation automation and PM risk gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_validation_automation_pm_gates"
MAX_SEQUENCE_LENGTH = 22


@dataclass(frozen=True)
class State:
    status: str = "new"
    ordinary_result_recorded: bool = False
    flowguard_passed: bool = False
    reviewer_passed: bool = False
    system_validation_recorded: bool = False
    system_closure_recorded: bool = False
    system_closure_applied: bool = False
    failed_system_validation_recorded: bool = False
    failed_system_validation_routed_to_pm: bool = False
    low_risk_pm_decision_recorded: bool = False
    low_risk_pm_decision_applied: bool = False
    high_risk_pm_decision_recorded: bool = False
    high_risk_pm_decision_staged: bool = False
    pm_gate_flowguard_passed: bool = False
    pm_gate_reviewer_passed: bool = False
    pm_gate_system_validation_recorded: bool = False
    pm_gate_system_closure_recorded: bool = False
    staged_pm_decision_applied: bool = False
    old_packet_roles_rejected: bool = False
    validator_ai_required_on_ordinary_path: bool = False
    closure_officer_required_on_ordinary_path: bool = False
    old_validator_packet_accepted: bool = False
    old_closure_packet_accepted: bool = False
    system_validation_treated_as_terminal: bool = False
    closure_before_system_validation: bool = False
    system_validation_failure_not_routed_to_pm: bool = False
    system_validation_failure_auto_closed: bool = False
    high_risk_pm_applied_before_gate: bool = False
    pm_waiver_applied_before_gate: bool = False
    pm_mutation_without_flowguard: bool = False
    pm_decision_reviewer_missing: bool = False
    low_risk_repair_forced_through_gate: bool = False


@dataclass(frozen=True)
class Tick:
    """One validation or PM decision-gate transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_ordinary_result",
    "record_flowguard_pass",
    "record_reviewer_pass",
    "record_system_validation",
    "record_system_closure_after_system_validation",
    "advance_after_system_closure",
    "record_failed_system_validation",
    "route_failed_system_validation_to_pm",
    "record_low_risk_pm_decision",
    "apply_low_risk_pm_decision_directly",
    "record_high_risk_pm_decision",
    "stage_high_risk_pm_decision",
    "pass_pm_decision_flowguard_gate",
    "pass_pm_decision_reviewer_gate",
    "record_pm_decision_system_validation",
    "record_pm_decision_system_closure",
    "apply_staged_pm_decision_after_system_closure",
    "reject_old_validator_and_closure_packets",
)


def initial_state() -> State:
    return State()


class ValidationAutomationPmGateStep:
    name = "ValidationAutomationPmGateStep"
    reads = (
        "packets",
        "packet_outcomes",
        "flowguard_work_orders",
        "reviews",
        "validation_evidence",
        "system_closures",
        "pm_repair_decisions",
        "pm_dispositions",
        "pm_decision_gates",
    )
    writes = (
        "validation_evidence",
        "system_closures",
        "pm_decision_gates",
        "route_state",
        "active_blockers",
    )
    input_description = "Input x State: one packet result, system validation action, or PM decision gate action"
    output_description = "Set(Output x State): ordinary system closure, failed-validation PM repair, low-risk PM repair, high-risk PM gated application"
    idempotency = "System closure is recorded once per passed validation; high-risk PM decisions apply only after system closure"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_validation_pm_gate_invariant", replace(state, status="blocked")),)
    if not state.ordinary_result_recorded:
        return (Transition("record_ordinary_result", replace(state, status="running", ordinary_result_recorded=True)),)
    if not state.flowguard_passed:
        return (Transition("record_flowguard_pass", replace(state, flowguard_passed=True)),)
    if not state.reviewer_passed:
        return (Transition("record_reviewer_pass", replace(state, reviewer_passed=True)),)
    if not state.system_validation_recorded:
        return (Transition("record_system_validation", replace(state, system_validation_recorded=True)),)
    if not state.system_closure_recorded:
        return (
            Transition(
                "record_system_closure_after_system_validation",
                replace(state, system_closure_recorded=True),
            ),
        )
    if not state.system_closure_applied:
        return (
            Transition(
                "advance_after_system_closure",
                replace(state, system_closure_applied=True),
            ),
        )
    if not state.failed_system_validation_recorded:
        return (
            Transition(
                "record_failed_system_validation",
                replace(state, failed_system_validation_recorded=True),
            ),
        )
    if not state.failed_system_validation_routed_to_pm:
        return (
            Transition(
                "route_failed_system_validation_to_pm",
                replace(state, failed_system_validation_routed_to_pm=True),
            ),
        )
    if not state.low_risk_pm_decision_recorded:
        return (Transition("record_low_risk_pm_decision", replace(state, low_risk_pm_decision_recorded=True)),)
    if not state.low_risk_pm_decision_applied:
        return (
            Transition(
                "apply_low_risk_pm_decision_directly",
                replace(state, low_risk_pm_decision_applied=True),
            ),
        )
    if not state.high_risk_pm_decision_recorded:
        return (Transition("record_high_risk_pm_decision", replace(state, high_risk_pm_decision_recorded=True)),)
    if not state.high_risk_pm_decision_staged:
        return (Transition("stage_high_risk_pm_decision", replace(state, high_risk_pm_decision_staged=True)),)
    if not state.pm_gate_flowguard_passed:
        return (Transition("pass_pm_decision_flowguard_gate", replace(state, pm_gate_flowguard_passed=True)),)
    if not state.pm_gate_reviewer_passed:
        return (Transition("pass_pm_decision_reviewer_gate", replace(state, pm_gate_reviewer_passed=True)),)
    if not state.pm_gate_system_validation_recorded:
        return (
            Transition(
                "record_pm_decision_system_validation",
                replace(state, pm_gate_system_validation_recorded=True),
            ),
        )
    if not state.pm_gate_system_closure_recorded:
        return (
            Transition(
                "record_pm_decision_system_closure",
                replace(state, pm_gate_system_closure_recorded=True),
            ),
        )
    if not state.staged_pm_decision_applied:
        return (
            Transition(
                "apply_staged_pm_decision_after_system_closure",
                replace(state, staged_pm_decision_applied=True),
            ),
        )
    if not state.old_packet_roles_rejected:
        return (
            Transition(
                "reject_old_validator_and_closure_packets",
                replace(state, old_packet_roles_rejected=True, status="complete"),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.flowguard_passed and not state.ordinary_result_recorded:
        failures.append("FlowGuard passed before ordinary result")
    if state.reviewer_passed and not state.flowguard_passed:
        failures.append("reviewer passed before FlowGuard")
    if state.system_validation_recorded and not state.reviewer_passed:
        failures.append("system validation recorded before reviewer pass")
    if state.system_closure_recorded and not state.system_validation_recorded:
        failures.append("system closure recorded before system validation")
    if state.system_closure_applied and not state.system_closure_recorded:
        failures.append("system closure applied before system closure record")
    if state.failed_system_validation_routed_to_pm and not state.failed_system_validation_recorded:
        failures.append("failed system validation routed before failed evidence")
    if state.low_risk_pm_decision_applied and not state.low_risk_pm_decision_recorded:
        failures.append("low-risk PM decision applied before record")
    if state.high_risk_pm_decision_staged and not state.high_risk_pm_decision_recorded:
        failures.append("high-risk PM decision staged before record")
    if state.pm_gate_flowguard_passed and not state.high_risk_pm_decision_staged:
        failures.append("PM gate FlowGuard passed before high-risk decision staging")
    if state.pm_gate_reviewer_passed and not state.pm_gate_flowguard_passed:
        failures.append("PM gate reviewer passed before FlowGuard")
    if state.pm_gate_system_validation_recorded and not state.pm_gate_reviewer_passed:
        failures.append("PM gate system validation before reviewer")
    if state.pm_gate_system_closure_recorded and not state.pm_gate_system_validation_recorded:
        failures.append("PM gate system closure before system validation")
    if state.staged_pm_decision_applied and not state.pm_gate_system_closure_recorded:
        failures.append("staged PM decision applied before system closure")
    if state.validator_ai_required_on_ordinary_path:
        failures.append("ordinary path still required validator AI")
    if state.closure_officer_required_on_ordinary_path:
        failures.append("ordinary path still required Closure Officer AI")
    if state.old_validator_packet_accepted:
        failures.append("old validator packet was accepted")
    if state.old_closure_packet_accepted:
        failures.append("old closure packet was accepted")
    if state.system_validation_treated_as_terminal:
        failures.append("system validation treated as terminal completion")
    if state.closure_before_system_validation:
        failures.append("closure before system validation")
    if state.system_validation_failure_not_routed_to_pm:
        failures.append("system validation failure was not routed to PM repair")
    if state.system_validation_failure_auto_closed:
        failures.append("failed system validation auto-closed the subject")
    if state.high_risk_pm_applied_before_gate:
        failures.append("high-risk PM decision applied before gate")
    if state.pm_waiver_applied_before_gate:
        failures.append("PM waiver applied before gate")
    if state.pm_mutation_without_flowguard:
        failures.append("PM route mutation applied without FlowGuard")
    if state.pm_decision_reviewer_missing:
        failures.append("PM decision gate lacked reviewer pass")
    if state.low_risk_repair_forced_through_gate:
        failures.append("low-risk PM repair was forced through high-risk gate")
    return failures


def validation_pm_gate_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def is_success(state: State) -> bool:
    return (
        state.status == "complete"
        and state.system_validation_recorded
        and state.system_closure_applied
        and state.failed_system_validation_routed_to_pm
        and state.low_risk_pm_decision_applied
        and state.high_risk_pm_decision_staged
        and state.pm_gate_system_closure_recorded
        and state.staged_pm_decision_applied
        and state.old_packet_roles_rejected
    )


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return state.status in {"blocked", "complete"}


def target_state() -> State:
    state = initial_state()
    for _ in range(len(REQUIRED_SAFE_LABELS) + 2):
        transitions = next_safe_states(state)
        if not transitions:
            break
        state = transitions[0].state
    return state


def hazard_states() -> dict[str, State]:
    base = target_state()
    return {
        "validator_ai_required_on_ordinary_path": replace(base, validator_ai_required_on_ordinary_path=True),
        "closure_officer_required_on_ordinary_path": replace(base, closure_officer_required_on_ordinary_path=True),
        "old_validator_packet_accepted": replace(base, old_validator_packet_accepted=True),
        "old_closure_packet_accepted": replace(base, old_closure_packet_accepted=True),
        "system_validation_treated_as_terminal": replace(base, system_validation_treated_as_terminal=True),
        "closure_before_system_validation": replace(base, closure_before_system_validation=True),
        "system_validation_failure_not_routed_to_pm": replace(base, system_validation_failure_not_routed_to_pm=True),
        "system_validation_failure_auto_closed": replace(base, system_validation_failure_auto_closed=True),
        "high_risk_pm_applied_before_gate": replace(base, high_risk_pm_applied_before_gate=True),
        "pm_waiver_applied_before_gate": replace(base, pm_waiver_applied_before_gate=True),
        "pm_mutation_without_flowguard": replace(base, pm_mutation_without_flowguard=True),
        "pm_decision_reviewer_missing": replace(base, pm_decision_reviewer_missing=True),
        "low_risk_repair_forced_through_gate": replace(base, low_risk_repair_forced_through_gate=True),
    }


def state_summary(state: State) -> dict[str, object]:
    return {
        "status": state.status,
        "system_validation_recorded": state.system_validation_recorded,
        "system_closure_recorded": state.system_closure_recorded,
        "system_closure_applied": state.system_closure_applied,
        "failed_system_validation_routed_to_pm": state.failed_system_validation_routed_to_pm,
        "low_risk_pm_decision_applied": state.low_risk_pm_decision_applied,
        "high_risk_pm_decision_staged": state.high_risk_pm_decision_staged,
        "pm_gate_flowguard_passed": state.pm_gate_flowguard_passed,
        "pm_gate_reviewer_passed": state.pm_gate_reviewer_passed,
        "pm_gate_system_closure_recorded": state.pm_gate_system_closure_recorded,
        "staged_pm_decision_applied": state.staged_pm_decision_applied,
        "old_packet_roles_rejected": state.old_packet_roles_rejected,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(ValidationAutomationPmGateStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    Invariant(
        "validation_automation_and_pm_decision_gate_order",
        "System validation replaces ordinary validator AI, system closure replaces ordinary Closure Officer AI, and high-risk PM decisions apply only after gated system closure.",
        validation_pm_gate_invariant,
    ),
)
