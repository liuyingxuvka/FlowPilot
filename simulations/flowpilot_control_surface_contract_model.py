"""FlowGuard model for FlowPilot current-run and packet control-surface contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_control_surface_contracts"

SUCCESS = "success"
NEW_CURRENT_SCHEMA_IGNORED = "new_current_schema_ignored"
FALLBACK_SCANS_PROJECT_ROOT = "fallback_scans_project_root"
INVALID_UTF8_CRASHES_AUDIT = "invalid_utf8_crashes_audit"
PM_ONLY_PACKET_CONTRACT = "pm_only_packet_contract"
ACK_TREATED_AS_RESULT = "ack_treated_as_result"
ACCEPTED_RESULT_REASSIGNED = "accepted_result_reassigned"
OLD_GENERATION_RESULT_ACCEPTED = "old_generation_result_accepted"

SCENARIOS = (
    SUCCESS,
    NEW_CURRENT_SCHEMA_IGNORED,
    FALLBACK_SCANS_PROJECT_ROOT,
    INVALID_UTF8_CRASHES_AUDIT,
    PM_ONLY_PACKET_CONTRACT,
    ACK_TREATED_AS_RESULT,
    ACCEPTED_RESULT_REASSIGNED,
    OLD_GENERATION_RESULT_ACCEPTED,
)
RISK_SCENARIOS = set(SCENARIOS) - {SUCCESS}

ROLE_SET = (
    "pm",
    "worker",
    "reviewer",
    "flowguard_operator",
)


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
    new_current_fields_present: bool = True
    legacy_current_fields_present: bool = False
    resolver_accepts_new_fields: bool = True
    resolver_accepts_legacy_fields: bool = True
    resolver_uses_explicit_run_root: bool = True
    resolver_falls_back_to_project_root: bool = False
    resolver_chooses_newest_run: bool = False
    evidence_reader_returns_structured_error: bool = True
    evidence_reader_crashes_on_decode: bool = False
    invalid_utf8_observed: bool = False
    packet_contract_roles: tuple[str, ...] = ROLE_SET
    envelope_has_output_authority: bool = True
    ack_result_accepted_separate: bool = True
    ack_seen: bool = True
    result_seen: bool = True
    accepted_seen: bool = True
    accepted_packet_reassigned: bool = False
    accepted_packet_ack_regressed: bool = False
    current_generation: int = 2
    result_generation: int = 2
    stale_generation_quarantined: bool = True
    classification: str = ""


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _happy_path() -> State:
    return State(status="running", scenario=SUCCESS)


def _selected_state(scenario: str) -> State:
    base = _happy_path()
    if scenario == SUCCESS:
        return base
    if scenario == NEW_CURRENT_SCHEMA_IGNORED:
        return replace(base, scenario=scenario, resolver_accepts_new_fields=False)
    if scenario == FALLBACK_SCANS_PROJECT_ROOT:
        return replace(
            base,
            scenario=scenario,
            resolver_uses_explicit_run_root=False,
            resolver_falls_back_to_project_root=True,
        )
    if scenario == INVALID_UTF8_CRASHES_AUDIT:
        return replace(
            base,
            scenario=scenario,
            invalid_utf8_observed=True,
            evidence_reader_returns_structured_error=False,
            evidence_reader_crashes_on_decode=True,
        )
    if scenario == PM_ONLY_PACKET_CONTRACT:
        return replace(base, scenario=scenario, packet_contract_roles=("pm",))
    if scenario == ACK_TREATED_AS_RESULT:
        return replace(
            base,
            scenario=scenario,
            ack_result_accepted_separate=False,
            ack_seen=True,
            result_seen=False,
            accepted_seen=True,
        )
    if scenario == ACCEPTED_RESULT_REASSIGNED:
        return replace(
            base,
            scenario=scenario,
            accepted_packet_reassigned=True,
            accepted_packet_ack_regressed=True,
        )
    if scenario == OLD_GENERATION_RESULT_ACCEPTED:
        return replace(
            base,
            scenario=scenario,
            result_generation=1,
            stale_generation_quarantined=False,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def control_surface_ready(state: State) -> bool:
    current_pointer_supported = (
        (not state.new_current_fields_present or state.resolver_accepts_new_fields)
        and (not state.legacy_current_fields_present or state.resolver_accepts_legacy_fields)
    )
    all_roles_covered = set(ROLE_SET).issubset(set(state.packet_contract_roles))
    fresh_or_quarantined = (
        state.result_generation >= state.current_generation
        or state.stale_generation_quarantined
    )
    return (
        state.status == "running"
        and current_pointer_supported
        and state.resolver_uses_explicit_run_root
        and not state.resolver_falls_back_to_project_root
        and not state.resolver_chooses_newest_run
        and state.evidence_reader_returns_structured_error
        and not state.evidence_reader_crashes_on_decode
        and all_roles_covered
        and state.envelope_has_output_authority
        and state.ack_result_accepted_separate
        and state.ack_seen
        and state.result_seen
        and state.accepted_seen
        and not state.accepted_packet_reassigned
        and not state.accepted_packet_ack_regressed
        and fresh_or_quarantined
    )


def _block_label(state: State) -> str:
    if state.new_current_fields_present and not state.resolver_accepts_new_fields:
        return "block_new_current_schema_ignored"
    if not state.resolver_uses_explicit_run_root or state.resolver_falls_back_to_project_root:
        return "block_implicit_run_root_fallback"
    if state.resolver_chooses_newest_run:
        return "block_newest_run_fallback"
    if state.invalid_utf8_observed and state.evidence_reader_crashes_on_decode:
        return "block_unreadable_evidence_crash"
    if not state.evidence_reader_returns_structured_error:
        return "block_unstructured_evidence_read_error"
    if not set(ROLE_SET).issubset(set(state.packet_contract_roles)):
        return "block_packet_contract_not_role_symmetric"
    if not state.envelope_has_output_authority:
        return "block_missing_output_authority"
    if not state.ack_result_accepted_separate:
        return "block_ack_result_acceptance_conflated"
    if state.ack_seen and not state.result_seen and state.accepted_seen:
        return "block_ack_treated_as_result"
    if state.accepted_packet_reassigned or state.accepted_packet_ack_regressed:
        return "block_accepted_packet_mutated"
    if state.result_generation < state.current_generation and not state.stale_generation_quarantined:
        return "block_old_generation_result_accepted"
    return "block_control_surface_contract_incomplete"


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", _selected_state(scenario))
        return
    if state.status != "running":
        return
    if control_surface_ready(state):
        yield Transition("accept_control_surface_contract", replace(state, status="complete", classification="accepted"))
        return
    label = _block_label(state)
    yield Transition(label, replace(state, status="blocked", classification=label))


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "blocked"}


def is_success(state: State) -> bool:
    return is_terminal(state)


def hard_check_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "complete" and not control_surface_ready(replace(state, status="running")):
        failures.append("control surface was accepted without the full contract")
    if state.status == "complete" and state.scenario in RISK_SCENARIOS:
        failures.append(f"risk scenario was accepted: {state.scenario}")
    if state.status == "blocked" and state.scenario == SUCCESS:
        failures.append("safe control surface was blocked")
    return failures


def hard_invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = hard_check_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "flowpilot_control_surface_contract_gate",
        "Current-run resolution, evidence reads, packet symmetry, and result authority must all hold.",
        hard_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 3


class FlowPilotControlSurfaceStep:
    name = "FlowPilotControlSurfaceStep"
    reads = (
        "current_json",
        "run_root",
        "evidence_files",
        "packet_envelopes",
        "result_envelopes",
        "source_generation",
    )
    writes = ("control_surface_acceptance_or_block",)
    input_description = "control-surface scenario"
    output_description = "accepted contract or explicit block"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def build_workflow() -> Workflow:
    return Workflow((FlowPilotControlSurfaceStep(),), name=MODEL_ID)


def scenario_matrix() -> dict[str, str]:
    matrix: dict[str, str] = {}
    for scenario in SCENARIOS:
        transitions = list(next_safe_states(_selected_state(scenario)))
        matrix[scenario] = transitions[0].label if len(transitions) == 1 else "missing_transition"
    return matrix


def hazard_states() -> dict[str, State]:
    hazards = {
        f"{scenario}_accepted": replace(_selected_state(scenario), status="complete")
        for scenario in RISK_SCENARIOS
    }
    hazards["success_overblocked"] = replace(_selected_state(SUCCESS), status="blocked")
    return hazards
