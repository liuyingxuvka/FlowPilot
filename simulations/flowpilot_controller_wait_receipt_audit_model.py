"""FlowGuard model for Controller wait receipt audit.

Risk intent:
- Every Controller wait wakeup checks formal receipt surfaces before quietly
  waiting again.
- `controller_aside` may trigger a formal receipt audit, but never satisfies a
  wait by itself.
- The audit distinguishes ordinary waiting from control-plane stuck states
  without reading sealed bodies or judging work quality.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SCENARIOS = (
    "no_formal_return_waits",
    "formal_return_ready_reenters_ledger",
    "formal_return_seen_wait_not_released_classified_stuck",
    "result_envelope_no_notice_classified_stuck",
    "aside_claim_without_formal_return_keeps_wait",
    "malformed_formal_return_classified_repair",
)

NEGATIVE_SCENARIOS = (
    "aside_releases_wait",
    "audit_reads_sealed_body",
    "audit_approves_quality",
    "formal_return_without_notice_marked_ready",
    "stale_control_plane_silently_waits",
    "malformed_return_marked_ready",
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS
MAX_SEQUENCE_LENGTH = 1
REQUIRED_LABELS = tuple(
    [f"accept_{scenario}" for scenario in VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in NEGATIVE_SCENARIOS]
)


@dataclass(frozen=True)
class Tick:
    """One Controller wait wakeup."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    current_wait_active: bool = True
    aside_claims_done: bool = False
    formal_return_seen: bool = False
    formal_return_malformed: bool = False
    result_envelope_seen: bool = False
    next_action_notice_seen: bool = False
    controller_ledger_ready: bool = False
    audit_reads_sealed_body: bool = False
    audit_judges_work_quality: bool = False
    classification: str = "unset"
    wait_released_by_aside: bool = False
    wait_released_by_formal_surface: bool = False
    user_message_required: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(status="accepted", scenario=scenario), **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(status="rejected", scenario=scenario), **changes)


def scenario_state(scenario: str) -> State:
    if scenario == "no_formal_return_waits":
        return _accepted(scenario, classification="no_formal_return_seen")
    if scenario == "formal_return_ready_reenters_ledger":
        return _accepted(
            scenario,
            formal_return_seen=True,
            next_action_notice_seen=True,
            controller_ledger_ready=True,
            classification="formal_return_ready",
            wait_released_by_formal_surface=True,
        )
    if scenario == "formal_return_seen_wait_not_released_classified_stuck":
        return _accepted(
            scenario,
            formal_return_seen=True,
            classification="formal_return_seen_but_wait_not_released",
            user_message_required=True,
        )
    if scenario == "result_envelope_no_notice_classified_stuck":
        return _accepted(
            scenario,
            formal_return_seen=True,
            result_envelope_seen=True,
            classification="result_envelope_seen_but_no_next_notice",
            user_message_required=True,
        )
    if scenario == "aside_claim_without_formal_return_keeps_wait":
        return _accepted(
            scenario,
            aside_claims_done=True,
            classification="aside_claim_without_formal_return",
        )
    if scenario == "malformed_formal_return_classified_repair":
        return _accepted(
            scenario,
            formal_return_seen=True,
            formal_return_malformed=True,
            classification="formal_return_malformed",
            user_message_required=True,
        )
    if scenario == "aside_releases_wait":
        return _rejected(
            scenario,
            aside_claims_done=True,
            classification="formal_return_ready",
            wait_released_by_aside=True,
        )
    if scenario == "audit_reads_sealed_body":
        return _rejected(
            scenario,
            formal_return_seen=True,
            audit_reads_sealed_body=True,
            classification="formal_return_ready",
        )
    if scenario == "audit_approves_quality":
        return _rejected(
            scenario,
            formal_return_seen=True,
            audit_judges_work_quality=True,
            classification="formal_return_ready",
        )
    if scenario == "formal_return_without_notice_marked_ready":
        return _rejected(
            scenario,
            formal_return_seen=True,
            result_envelope_seen=True,
            next_action_notice_seen=False,
            classification="formal_return_ready",
            wait_released_by_formal_surface=True,
        )
    if scenario == "stale_control_plane_silently_waits":
        return _rejected(
            scenario,
            formal_return_seen=True,
            classification="no_formal_return_seen",
        )
    if scenario == "malformed_return_marked_ready":
        return _rejected(
            scenario,
            formal_return_seen=True,
            formal_return_malformed=True,
            classification="formal_return_ready",
            wait_released_by_formal_surface=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


class ControllerWaitReceiptAuditStep:
    """Model one wait-audit decision.

    Input x State -> Set(Output x State)
    reads: current wait metadata, formal receipt ledgers/envelopes/status files
    writes: Controller-visible wait audit classification only
    idempotency: repeated audits classify the same metadata without advancing formal route progress
    """

    name = "ControllerWaitReceiptAuditStep"
    input_description = "one Controller wait wakeup"
    output_description = "accepted or rejected wait-audit transition"
    reads = ("current_wait_metadata", "formal_receipt_surfaces", "controller_aside_metadata")
    writes = ("controller_wait_receipt_audit",)
    idempotency = "audit classifications do not mutate route progress"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        if state.status != "new":
            return
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status != "new":
        return
    for scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{scenario}", scenario_state(scenario))
    for scenario in NEGATIVE_SCENARIOS:
        yield Transition(f"reject_{scenario}", scenario_state(scenario))


def audit_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted" and state.scenario not in VALID_SCENARIOS:
        failures.append("accepted a known-bad wait-audit scenario")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("rejected a valid wait-audit scenario")
    if state.status == "accepted" and state.wait_released_by_aside:
        failures.append("controller_aside released a formal wait")
    if state.status == "accepted" and state.audit_reads_sealed_body:
        failures.append("wait audit read sealed body content")
    if state.status == "accepted" and state.audit_judges_work_quality:
        failures.append("wait audit judged work quality")
    if (
        state.status == "accepted"
        and state.classification == "formal_return_ready"
        and state.result_envelope_seen
        and not state.next_action_notice_seen
    ):
        failures.append("result envelope without next-action notice was marked ready")
    if (
        state.status == "accepted"
        and state.formal_return_seen
        and not state.next_action_notice_seen
        and not state.controller_ledger_ready
        and state.classification == "no_formal_return_seen"
    ):
        failures.append("formal return was hidden as ordinary waiting")
    if (
        state.status == "accepted"
        and state.formal_return_malformed
        and state.classification == "formal_return_ready"
    ):
        failures.append("malformed formal return was marked ready")
    return failures


def invariant_failures(state: State) -> list[str]:
    return audit_failures(state)


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((ControllerWaitReceiptAuditStep(),), name="flowpilot_controller_wait_receipt_audit")


def accepts_only_safe_wait_audits(state: State, trace) -> InvariantResult:
    del trace
    failures = audit_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def _invariant(name: str, description: str) -> Invariant[State]:
    return Invariant(name=name, description=description, predicate=accepts_only_safe_wait_audits)


INVARIANTS = (
    _invariant(
        "controller_wait_audit_does_not_expand_controller_authority",
        "Wait audit must not read sealed bodies, judge work quality, or release waits from asides.",
    ),
    _invariant(
        "controller_wait_audit_exposes_control_plane_stuck_states",
        "Formal returns without release or next-action notice must not be hidden as ordinary waiting.",
    ),
)

EXTERNAL_INPUTS = (Tick(),)


def hazard_states() -> dict[str, State]:
    return {
        scenario: replace(scenario_state(scenario), status="accepted")
        for scenario in NEGATIVE_SCENARIOS
    }


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "REQUIRED_LABELS",
    "SCENARIOS",
    "VALID_SCENARIOS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_safe_states",
    "scenario_state",
    "terminal_predicate",
]
