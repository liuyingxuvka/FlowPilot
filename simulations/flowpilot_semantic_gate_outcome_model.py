"""FlowGuard model for fresh FlowPilot semantic gate outcomes."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_semantic_gate_outcomes"
MAX_SEQUENCE_LENGTH = 20


@dataclass(frozen=True)
class State:
    status: str = "new"
    mechanical_result_recorded: bool = False
    semantic_outcome_parsed: bool = False
    pass_outcome_advances: bool = False
    nonpass_outcome_recorded: bool = False
    active_blocker_recorded: bool = False
    pm_repair_packet_issued: bool = False
    pm_repair_decision_recorded: bool = False
    repair_transaction_opened: bool = False
    stale_failed_evidence_preserved: bool = False
    same_class_recheck_required: bool = False
    same_class_pass_recorded: bool = False
    blocker_cleared_by_same_class_pass: bool = False
    downstream_released_after_clear: bool = False
    semantic_block_treated_as_pass: bool = False
    validation_fail_issued_closure: bool = False
    pm_impersonated_reviewer_pass: bool = False
    stale_failed_evidence_used_as_pass: bool = False
    blocker_without_pm_repair: bool = False
    wrong_role_recheck_cleared_blocker: bool = False


@dataclass(frozen=True)
class Tick:
    """One semantic outcome lifecycle transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "record_mechanically_valid_result",
    "parse_semantic_outcome",
    "advance_on_pass_outcome",
    "record_nonpass_outcome",
    "record_active_blocker",
    "issue_pm_repair_decision_packet",
    "record_pm_repair_decision",
    "open_repair_transaction",
    "preserve_stale_failed_evidence",
    "require_same_class_recheck",
    "record_same_class_pass",
    "clear_blocker_by_same_class_pass",
    "release_downstream_after_clear",
)


def initial_state() -> State:
    return State()


class SemanticGateOutcomeStep:
    name = "SemanticGateOutcomeStep"
    reads = (
        "packet_result",
        "packet_body",
        "packet_kind",
        "active_blockers",
        "pm_repair_decisions",
        "repair_transactions",
    )
    writes = (
        "packet_outcomes",
        "active_blockers",
        "pm_repair_decision_packet",
        "repair_transactions",
        "packet_status",
    )
    input_description = "Input x State: one packet result or repair transition"
    output_description = "Set(Output x State): pass progression, blocker repair, or rejected hazard"
    idempotency = "PM repair decisions do not clear reviewer/validator/FlowGuard blockers without same-class recheck"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_semantic_gate_outcome_invariant", replace(state, status="blocked")),)
    if not state.mechanical_result_recorded:
        return (Transition("record_mechanically_valid_result", replace(state, status="running", mechanical_result_recorded=True)),)
    if not state.semantic_outcome_parsed:
        return (Transition("parse_semantic_outcome", replace(state, semantic_outcome_parsed=True)),)
    if not state.pass_outcome_advances:
        return (Transition("advance_on_pass_outcome", replace(state, pass_outcome_advances=True)),)
    if not state.nonpass_outcome_recorded:
        return (Transition("record_nonpass_outcome", replace(state, nonpass_outcome_recorded=True)),)
    if not state.active_blocker_recorded:
        return (Transition("record_active_blocker", replace(state, active_blocker_recorded=True)),)
    if not state.pm_repair_packet_issued:
        return (Transition("issue_pm_repair_decision_packet", replace(state, pm_repair_packet_issued=True)),)
    if not state.pm_repair_decision_recorded:
        return (Transition("record_pm_repair_decision", replace(state, pm_repair_decision_recorded=True)),)
    if not state.repair_transaction_opened:
        return (Transition("open_repair_transaction", replace(state, repair_transaction_opened=True)),)
    if not state.stale_failed_evidence_preserved:
        return (Transition("preserve_stale_failed_evidence", replace(state, stale_failed_evidence_preserved=True)),)
    if not state.same_class_recheck_required:
        return (Transition("require_same_class_recheck", replace(state, same_class_recheck_required=True)),)
    if not state.same_class_pass_recorded:
        return (Transition("record_same_class_pass", replace(state, same_class_pass_recorded=True)),)
    if not state.blocker_cleared_by_same_class_pass:
        return (
            Transition(
                "clear_blocker_by_same_class_pass",
                replace(state, blocker_cleared_by_same_class_pass=True),
            ),
        )
    if not state.downstream_released_after_clear:
        return (
            Transition(
                "release_downstream_after_clear",
                replace(state, downstream_released_after_clear=True, status="complete"),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.semantic_outcome_parsed and not state.mechanical_result_recorded:
        failures.append("semantic outcome parsed before mechanical result")
    if state.nonpass_outcome_recorded and not state.semantic_outcome_parsed:
        failures.append("non-pass outcome recorded before semantic parse")
    if state.active_blocker_recorded and not state.nonpass_outcome_recorded:
        failures.append("active blocker recorded without non-pass outcome")
    if state.pm_repair_packet_issued and not state.active_blocker_recorded:
        failures.append("PM repair packet issued without active blocker")
    if state.pm_repair_decision_recorded and not state.pm_repair_packet_issued:
        failures.append("PM repair decision recorded without PM repair packet")
    if state.repair_transaction_opened and not state.pm_repair_decision_recorded:
        failures.append("repair transaction opened without PM decision")
    if state.stale_failed_evidence_preserved and not state.repair_transaction_opened:
        failures.append("stale evidence preservation claimed before repair transaction")
    if state.same_class_recheck_required and not state.stale_failed_evidence_preserved:
        failures.append("same-class recheck required before stale evidence was preserved")
    if state.same_class_pass_recorded and not state.same_class_recheck_required:
        failures.append("same-class pass recorded before recheck requirement")
    if state.blocker_cleared_by_same_class_pass and not state.same_class_pass_recorded:
        failures.append("blocker cleared before same-class pass")
    if state.downstream_released_after_clear and not state.blocker_cleared_by_same_class_pass:
        failures.append("downstream released before blocker clear")
    if state.semantic_block_treated_as_pass:
        failures.append("semantic block treated as pass")
    if state.validation_fail_issued_closure:
        failures.append("validation fail issued closure")
    if state.pm_impersonated_reviewer_pass:
        failures.append("PM repair decision impersonated reviewer pass")
    if state.stale_failed_evidence_used_as_pass:
        failures.append("stale failed evidence used as pass")
    if state.blocker_without_pm_repair:
        failures.append("blocker lacked PM repair decision packet")
    if state.wrong_role_recheck_cleared_blocker:
        failures.append("wrong role recheck cleared blocker")
    return failures


def semantic_gate_outcome_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def is_success(state: State) -> bool:
    return (
        state.status == "complete"
        and state.pass_outcome_advances
        and state.active_blocker_recorded
        and state.pm_repair_decision_recorded
        and state.stale_failed_evidence_preserved
        and state.blocker_cleared_by_same_class_pass
        and state.downstream_released_after_clear
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
        "semantic_block_treated_as_pass": replace(base, semantic_block_treated_as_pass=True),
        "validation_fail_issued_closure": replace(base, validation_fail_issued_closure=True),
        "pm_impersonated_reviewer_pass": replace(base, pm_impersonated_reviewer_pass=True),
        "stale_failed_evidence_used_as_pass": replace(base, stale_failed_evidence_used_as_pass=True),
        "blocker_without_pm_repair": replace(base, blocker_without_pm_repair=True),
        "wrong_role_recheck_cleared_blocker": replace(base, wrong_role_recheck_cleared_blocker=True),
    }


def state_summary(state: State) -> dict[str, object]:
    return {
        "status": state.status,
        "semantic_outcome_parsed": state.semantic_outcome_parsed,
        "active_blocker_recorded": state.active_blocker_recorded,
        "pm_repair_decision_recorded": state.pm_repair_decision_recorded,
        "same_class_recheck_required": state.same_class_recheck_required,
        "blocker_cleared_by_same_class_pass": state.blocker_cleared_by_same_class_pass,
        "downstream_released_after_clear": state.downstream_released_after_clear,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(SemanticGateOutcomeStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)
INVARIANTS = (
    Invariant(
        "semantic_gate_outcome_order_and_authority",
        "Semantic block/fail outcomes must create PM-routed blockers and clear only after same-class recheck.",
        semantic_gate_outcome_invariant,
    ),
)
