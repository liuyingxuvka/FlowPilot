"""FlowGuard model for FlowPilot role-recovery binding evidence gates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_role_recovery_binding_evidence_proofs"

VALID_CURRENT_REPORT = "valid_current_report"
STALE_REPORT_RECLAIM = "stale_report_reclaim"
UNKNOWN_BINDING_EVIDENCE = "unknown_binding_evidence"
REPLACEMENT_INTENT_ONLY = "replacement_intent_only"
DAEMON_ERROR_WITH_DIAGNOSTICS = "daemon_error_with_diagnostics"
DAEMON_ERROR_WITHOUT_DIAGNOSTICS = "daemon_error_without_diagnostics"

SCENARIOS = (
    VALID_CURRENT_REPORT,
    STALE_REPORT_RECLAIM,
    UNKNOWN_BINDING_EVIDENCE,
    REPLACEMENT_INTENT_ONLY,
    DAEMON_ERROR_WITH_DIAGNOSTICS,
    DAEMON_ERROR_WITHOUT_DIAGNOSTICS,
)

SAFE_SCENARIOS = {VALID_CURRENT_REPORT, DAEMON_ERROR_WITH_DIAGNOSTICS}
RISK_SCENARIOS = {
    STALE_REPORT_RECLAIM,
    UNKNOWN_BINDING_EVIDENCE,
    REPLACEMENT_INTENT_ONLY,
    DAEMON_ERROR_WITHOUT_DIAGNOSTICS,
}


@dataclass(frozen=True)
class Tick:
    pass


@dataclass(frozen=True)
class Action:
    label: str


@dataclass(frozen=True)
class State:
    status: str = "new"
    scenario: str = ""
    latest_transaction_id: str = ""
    report_transaction_id: str = ""
    runtime_roles_slot_transaction_id: str = ""
    target_role_in_report: bool = False
    agent_id_present: bool = False
    role_surface_addressable: bool = False
    current_run_binding_decision: str = ""
    replacement_intent_recorded: bool = False
    daemon_error_type: str = ""
    daemon_traceback_or_reason_present: bool = False
    daemon_action_context_present: bool = False
    daemon_artifact_sizes_present: bool = False
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _selected_state(scenario: str) -> State:
    if scenario == VALID_CURRENT_REPORT:
        return State(
            status="running",
            scenario=scenario,
            latest_transaction_id="T2",
            report_transaction_id="T2",
            runtime_roles_slot_transaction_id="T2",
            target_role_in_report=True,
            agent_id_present=True,
            role_surface_addressable=True,
            current_run_binding_decision="current_run_replacement_opened",
        )
    if scenario == STALE_REPORT_RECLAIM:
        return State(
            status="running",
            scenario=scenario,
            latest_transaction_id="T2",
            report_transaction_id="T1",
            runtime_roles_slot_transaction_id="T1",
            target_role_in_report=True,
            agent_id_present=True,
            role_surface_addressable=True,
            current_run_binding_decision="current_run_replacement_opened",
        )
    if scenario == UNKNOWN_BINDING_EVIDENCE:
        return State(
            status="running",
            scenario=scenario,
            latest_transaction_id="T2",
            report_transaction_id="T2",
            runtime_roles_slot_transaction_id="T2",
            target_role_in_report=True,
            agent_id_present=True,
            role_surface_addressable=False,
            current_run_binding_decision="current_run_replacement_opened",
        )
    if scenario == REPLACEMENT_INTENT_ONLY:
        return State(
            status="running",
            scenario=scenario,
            latest_transaction_id="T2",
            report_transaction_id="T2",
            runtime_roles_slot_transaction_id="T2",
            target_role_in_report=True,
            agent_id_present=True,
            role_surface_addressable=False,
            current_run_binding_decision="current_run_replacement_opened",
            replacement_intent_recorded=True,
        )
    if scenario == DAEMON_ERROR_WITH_DIAGNOSTICS:
        return State(
            status="running",
            scenario=scenario,
            daemon_error_type="MemoryError",
            daemon_traceback_or_reason_present=True,
            daemon_action_context_present=True,
            daemon_artifact_sizes_present=True,
        )
    if scenario == DAEMON_ERROR_WITHOUT_DIAGNOSTICS:
        return State(
            status="running",
            scenario=scenario,
            daemon_error_type="MemoryError",
        )
    raise ValueError(f"unknown scenario: {scenario}")


def _role_recovery_proof_is_current(state: State) -> bool:
    return (
        bool(state.latest_transaction_id)
        and state.report_transaction_id == state.latest_transaction_id
        and state.runtime_roles_slot_transaction_id == state.latest_transaction_id
        and state.target_role_in_report
        and state.agent_id_present
        and state.role_surface_addressable is True
        and state.current_run_binding_decision in {
            "existing_current_agent_reused",
            "current_run_replacement_opened",
        }
    )


def _daemon_error_diagnostics_complete(state: State) -> bool:
    return (
        bool(state.daemon_error_type)
        and state.daemon_traceback_or_reason_present
        and state.daemon_action_context_present
        and state.daemon_artifact_sizes_present
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if state.daemon_error_type:
        if _daemon_error_diagnostics_complete(state):
            yield Transition("classify_daemon_error_diagnostics_complete", replace(state, status="safe", classification="safe"))
        else:
            yield Transition("classify_daemon_error_diagnostics_missing", replace(state, status="risk", classification="risk"))
        return
    if _role_recovery_proof_is_current(state):
        yield Transition("classify_current_recovery_binding_proven", replace(state, status="safe", classification="safe"))
        return
    if state.report_transaction_id != state.latest_transaction_id:
        yield Transition("classify_stale_recovery_report_risk", replace(state, status="risk", classification="risk"))
        return
    if state.runtime_roles_slot_transaction_id != state.latest_transaction_id:
        yield Transition("classify_runtime_roles_slot_transaction_mismatch_risk", replace(state, status="risk", classification="risk"))
        return
    if not state.role_surface_addressable:
        yield Transition("classify_missing_current_binding_risk", replace(state, status="risk", classification="risk"))
        return
    yield Transition("classify_role_recovery_evidence_insufficient", replace(state, status="risk", classification="risk"))


def is_terminal(state: State) -> bool:
    return state.status in {"safe", "risk"}


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def is_success(state: State) -> bool:
    return is_terminal(state)


def _hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "safe" and not state.daemon_error_type and not _role_recovery_proof_is_current(state):
        failures.append("role recovery was marked safe without current transaction and current binding evidence")
    if state.status == "safe" and state.daemon_error_type and not _daemon_error_diagnostics_complete(state):
        failures.append("daemon fatal error was marked safe without actionable diagnostics")
    if state.status == "risk" and state.scenario in SAFE_SCENARIOS:
        failures.append("safe role recovery or daemon diagnostic scenario was overblocked")
    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = _hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_role_recovery_binding_evidence_contract",
        "Current role recovery readiness requires current transaction and current binding evidence.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


class RoleRecoveryBindingStep:
    """Input x State -> Set(Output x State) for role recovery binding evidence."""

    name = "RoleRecoveryBindingStep"
    reads = ("transaction_id", "role_slot", "current_binding_evidence", "daemon_error")
    writes = ("recovery_readiness_classification",)
    input_description = "role recovery proof or daemon fatal-error observation"
    output_description = "safe/risk classification for continuing normal work"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def build_workflow() -> Workflow:
    return Workflow((RoleRecoveryBindingStep(),), name=MODEL_ID)


def hazard_states() -> dict[str, State]:
    return {
        "stale_report_marked_safe": replace(_selected_state(STALE_REPORT_RECLAIM), status="safe"),
        "unknown_binding_evidence_marked_safe": replace(_selected_state(UNKNOWN_BINDING_EVIDENCE), status="safe"),
        "replacement_intent_only_marked_safe": replace(_selected_state(REPLACEMENT_INTENT_ONLY), status="safe"),
        "daemon_error_without_diagnostics_marked_safe": replace(_selected_state(DAEMON_ERROR_WITHOUT_DIAGNOSTICS), status="safe"),
        "current_report_overblocked": replace(_selected_state(VALID_CURRENT_REPORT), status="risk"),
    }
