"""FlowGuard model for FlowPilot validation automation and PM risk gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_validation_automation_pm_gates"
MAX_SEQUENCE_LENGTH = 18


@dataclass(frozen=True)
class State:
    status: str = "new"
    ordinary_result_recorded: bool = False
    flowguard_passed: bool = False
    reviewer_passed: bool = False
    system_validation_recorded: bool = False
    closure_packet_issued: bool = False
    closure_result_accepted: bool = False
    low_risk_pm_decision_recorded: bool = False
    low_risk_pm_decision_applied: bool = False
    high_risk_pm_decision_recorded: bool = False
    high_risk_pm_decision_staged: bool = False
    pm_gate_flowguard_passed: bool = False
    pm_gate_reviewer_passed: bool = False
    pm_gate_system_validation_recorded: bool = False
    pm_gate_closure_accepted: bool = False
    staged_pm_decision_applied: bool = False
    legacy_validation_fail_blocked: bool = False
    validator_ai_required_on_ordinary_path: bool = False
    system_validation_treated_as_terminal: bool = False
    closure_before_system_validation: bool = False
    high_risk_pm_applied_before_gate: bool = False
    pm_waiver_applied_before_gate: bool = False
    pm_mutation_without_flowguard: bool = False
    pm_decision_reviewer_missing: bool = False
    low_risk_repair_forced_through_gate: bool = False
    legacy_validation_fail_issued_closure: bool = False


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
    "issue_closure_packet_after_system_validation",
    "accept_closure_after_system_validation",
    "record_low_risk_pm_decision",
    "apply_low_risk_pm_decision_directly",
    "record_high_risk_pm_decision",
    "stage_high_risk_pm_decision",
    "pass_pm_decision_flowguard_gate",
    "pass_pm_decision_reviewer_gate",
    "record_pm_decision_system_validation",
    "accept_pm_decision_gate_closure",
    "apply_staged_pm_decision_after_gate",
    "block_legacy_validation_failure",
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
        "pm_repair_decisions",
        "pm_dispositions",
        "pm_decision_gates",
    )
    writes = (
        "validation_evidence",
        "closure_packets",
        "pm_decision_gates",
        "route_state",
        "active_blockers",
    )
    input_description = "Input x State: one packet result, system validation action, or PM decision gate action"
    output_description = "Set(Output x State): ordinary release, low-risk PM repair, high-risk PM gated application"
    idempotency = "System validation is evidence only; high-risk PM decisions apply only after gate closure"

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
    if not state.closure_packet_issued:
        return (
            Transition(
                "issue_closure_packet_after_system_validation",
                replace(state, closure_packet_issued=True),
            ),
        )
    if not state.closure_result_accepted:
        return (
            Transition(
                "accept_closure_after_system_validation",
                replace(state, closure_result_accepted=True),
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
    if not state.pm_gate_closure_accepted:
        return (
            Transition(
                "accept_pm_decision_gate_closure",
                replace(state, pm_gate_closure_accepted=True),
            ),
        )
    if not state.staged_pm_decision_applied:
        return (
            Transition(
                "apply_staged_pm_decision_after_gate",
                replace(state, staged_pm_decision_applied=True),
            ),
        )
    if not state.legacy_validation_fail_blocked:
        return (
            Transition(
                "block_legacy_validation_failure",
                replace(state, legacy_validation_fail_blocked=True, status="complete"),
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
    if state.closure_packet_issued and not state.system_validation_recorded:
        failures.append("closure issued before system validation")
    if state.closure_result_accepted and not state.closure_packet_issued:
        failures.append("closure accepted before closure packet")
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
    if state.pm_gate_closure_accepted and not state.pm_gate_system_validation_recorded:
        failures.append("PM gate closure before system validation")
    if state.staged_pm_decision_applied and not state.pm_gate_closure_accepted:
        failures.append("staged PM decision applied before gate closure")
    if state.validator_ai_required_on_ordinary_path:
        failures.append("ordinary path still required validator AI")
    if state.system_validation_treated_as_terminal:
        failures.append("system validation treated as terminal completion")
    if state.closure_before_system_validation:
        failures.append("closure before system validation")
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
    if state.legacy_validation_fail_issued_closure:
        failures.append("legacy validation fail issued closure")
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
        and state.closure_result_accepted
        and state.low_risk_pm_decision_applied
        and state.high_risk_pm_decision_staged
        and state.pm_gate_closure_accepted
        and state.staged_pm_decision_applied
        and state.legacy_validation_fail_blocked
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
        "system_validation_treated_as_terminal": replace(base, system_validation_treated_as_terminal=True),
        "closure_before_system_validation": replace(base, closure_before_system_validation=True),
        "high_risk_pm_applied_before_gate": replace(base, high_risk_pm_applied_before_gate=True),
        "pm_waiver_applied_before_gate": replace(base, pm_waiver_applied_before_gate=True),
        "pm_mutation_without_flowguard": replace(base, pm_mutation_without_flowguard=True),
        "pm_decision_reviewer_missing": replace(base, pm_decision_reviewer_missing=True),
        "low_risk_repair_forced_through_gate": replace(base, low_risk_repair_forced_through_gate=True),
        "legacy_validation_fail_issued_closure": replace(base, legacy_validation_fail_issued_closure=True),
    }


def state_summary(state: State) -> dict[str, object]:
    return {
        "status": state.status,
        "system_validation_recorded": state.system_validation_recorded,
        "closure_result_accepted": state.closure_result_accepted,
        "low_risk_pm_decision_applied": state.low_risk_pm_decision_applied,
        "high_risk_pm_decision_staged": state.high_risk_pm_decision_staged,
        "pm_gate_flowguard_passed": state.pm_gate_flowguard_passed,
        "pm_gate_reviewer_passed": state.pm_gate_reviewer_passed,
        "pm_gate_closure_accepted": state.pm_gate_closure_accepted,
        "staged_pm_decision_applied": state.staged_pm_decision_applied,
        "legacy_validation_fail_blocked": state.legacy_validation_fail_blocked,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(ValidationAutomationPmGateStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    Invariant(
        "validation_automation_and_pm_decision_gate_order",
        "System validation replaces ordinary validator AI, and high-risk PM decisions apply only after gated closure.",
        validation_pm_gate_invariant,
    ),
)
