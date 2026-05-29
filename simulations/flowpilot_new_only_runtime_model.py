"""FlowGuard model for FlowPilot new-only runtime contraction.

The model checks the contraction boundary for this change: current FlowPilot
inputs may advance the control plane, while retired inputs must be rejected
instead of migrated or canonicalized into current authority-bearing state.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


CURRENT_INPUTS = (
    "start",
    "startup_intake_envelope",
    "router_supplied_event",
    "current_role_output",
    "current_repair_transaction",
    "run_scoped_layout",
)
CURRENT_CONTRACT_TICK = "current_contract_tick"

RETIRED_INPUTS = (
    "next_new_invocation_alias",
    "run_until_wait_new_invocation_alias",
    "retired_chat_startup_payload",
    "retired_startup_answer_record",
    "retired_officer_event_alias",
    "retired_reviewer_event_alias",
    "retired_output_type_alias",
    "event_replay_transaction",
    "retired_reconcile_transaction",
    "retired_material_packet_contract",
    "retired_layout_root",
)

REQUIRED_CURRENT_LABELS = (
    "current_start_accepted",
    "current_startup_intake_recorded",
    "current_router_event_recorded",
    "current_role_output_recorded",
    "current_repair_transaction_recorded",
    "current_runtime_completed",
)

REQUIRED_REJECTION_LABELS = tuple(
    f"unsupported_{retired_input}_rejected" for retired_input in RETIRED_INPUTS
)


@dataclass(frozen=True)
class Tick:
    """One external runtime input presented to FlowPilot."""

    kind: str


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | started | intake | event | role | repair | layout | complete | rejected
    current_start_seen: bool = False
    current_startup_intake_seen: bool = False
    current_event_seen: bool = False
    current_role_output_seen: bool = False
    current_repair_transaction_seen: bool = False
    current_layout_seen: bool = False
    accepted_retired_input: bool = False
    migrated_retired_input: bool = False
    canonicalized_retired_event: bool = False
    retired_prompt_path_offered: bool = False
    prior_authority_quarantined: bool = True


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class NewOnlyRuntimeStep:
    """Model one runtime contract transition.

    Input x State -> Set(Output x State)
    reads: external input kind, current phase, prior-authority quarantine flag
    writes: one current phase advancement or an unsupported retired-input rejection
    idempotency: old inputs never alter current authority-bearing state; current
    inputs advance only along the current FlowPilot contract order.
    """

    name = "NewOnlyRuntimeStep"
    reads = ("input_kind", "runtime_phase", "prior_authority_quarantine")
    writes = ("runtime_phase", "unsupported_rejection")
    input_description = "current or old FlowPilot runtime input"
    output_description = "current transition or unsupported retired-input rejection"
    idempotency = "retired inputs are rejected without migration or canonicalization"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        for transition in next_states(input_obj, state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _reject(input_kind: str, state: State) -> Transition:
    return Transition(
        f"unsupported_{input_kind}_rejected",
        replace(state, status="rejected"),
    )


def next_states(input_obj: Tick, state: State) -> tuple[Transition, ...]:
    if state.status in {"complete", "rejected"}:
        return ()
    if input_obj.kind in RETIRED_INPUTS:
        return (_reject(input_obj.kind, state),)
    if input_obj.kind == CURRENT_CONTRACT_TICK:
        return _next_current_contract_state(state)
    if input_obj.kind == "start" and state.status == "new":
        return (
            Transition(
                "current_start_accepted",
                replace(state, status="started", current_start_seen=True),
            ),
        )
    if input_obj.kind == "startup_intake_envelope" and state.status == "started":
        return (
            Transition(
                "current_startup_intake_recorded",
                replace(state, status="intake", current_startup_intake_seen=True),
            ),
        )
    if input_obj.kind == "router_supplied_event" and state.status == "intake":
        return (
            Transition(
                "current_router_event_recorded",
                replace(state, status="event", current_event_seen=True),
            ),
        )
    if input_obj.kind == "current_role_output" and state.status == "event":
        return (
            Transition(
                "current_role_output_recorded",
                replace(state, status="role", current_role_output_seen=True),
            ),
        )
    if input_obj.kind == "current_repair_transaction" and state.status == "role":
        return (
            Transition(
                "current_repair_transaction_recorded",
                replace(
                    state,
                    status="repair",
                    current_repair_transaction_seen=True,
                ),
            ),
        )
    if input_obj.kind == "run_scoped_layout" and state.status == "repair":
        return (
            Transition(
                "current_runtime_completed",
                replace(state, status="complete", current_layout_seen=True),
            ),
        )
    return ()


def _next_current_contract_state(state: State) -> tuple[Transition, ...]:
    if state.status == "new":
        return (
            Transition(
                "current_start_accepted",
                replace(state, status="started", current_start_seen=True),
            ),
        )
    if state.status == "started":
        return (
            Transition(
                "current_startup_intake_recorded",
                replace(state, status="intake", current_startup_intake_seen=True),
            ),
        )
    if state.status == "intake":
        return (
            Transition(
                "current_router_event_recorded",
                replace(state, status="event", current_event_seen=True),
            ),
        )
    if state.status == "event":
        return (
            Transition(
                "current_role_output_recorded",
                replace(state, status="role", current_role_output_seen=True),
            ),
        )
    if state.status == "role":
        return (
            Transition(
                "current_repair_transaction_recorded",
                replace(
                    state,
                    status="repair",
                    current_repair_transaction_seen=True,
                ),
            ),
        )
    if state.status == "repair":
        return (
            Transition(
                "current_runtime_completed",
                replace(state, status="complete", current_layout_seen=True),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.accepted_retired_input:
        failures.append("retired input was accepted as current runtime input")
    if state.migrated_retired_input:
        failures.append("retired input was migrated into current state")
    if state.canonicalized_retired_event:
        failures.append("retired event alias was canonicalized")
    if state.retired_prompt_path_offered:
        failures.append("active prompt offered a retired path")
    if not state.prior_authority_quarantined:
        failures.append("prior authority quarantine was removed")
    if state.status == "complete":
        if not state.current_start_seen:
            failures.append("completion without current start")
        if not state.current_startup_intake_seen:
            failures.append("completion without current startup intake")
        if not state.current_event_seen:
            failures.append("completion without current router event")
        if not state.current_role_output_seen:
            failures.append("completion without current role output")
        if not state.current_repair_transaction_seen:
            failures.append("completion without current repair transaction")
        if not state.current_layout_seen:
            failures.append("completion without current run-scoped layout")
    return failures


def new_only_runtime_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_new_only_runtime",
        description=(
            "Current FlowPilot inputs may advance, retired inputs must be rejected, "
            "and prior authority quarantine must remain intact."
        ),
        predicate=new_only_runtime_invariant,
    ),
)

EXTERNAL_INPUTS = tuple(Tick(kind) for kind in CURRENT_INPUTS + RETIRED_INPUTS)
MAX_SEQUENCE_LENGTH = len(CURRENT_INPUTS) + 2


def build_workflow() -> Workflow:
    return Workflow((NewOnlyRuntimeStep(),), name="flowpilot_new_only_runtime")


def is_terminal(state: State) -> bool:
    return state.status in {"complete", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def hazard_states() -> dict[str, State]:
    complete = State(
        status="complete",
        current_start_seen=True,
        current_startup_intake_seen=True,
        current_event_seen=True,
        current_role_output_seen=True,
        current_repair_transaction_seen=True,
        current_layout_seen=True,
    )
    return {
        "retired_input_accepted": replace(complete, accepted_retired_input=True),
        "retired_input_migrated": replace(complete, migrated_retired_input=True),
        "retired_event_canonicalized": replace(complete, canonicalized_retired_event=True),
        "retired_prompt_path_offered": replace(complete, retired_prompt_path_offered=True),
        "prior_authority_quarantine_removed": replace(
            complete,
            prior_authority_quarantined=False,
        ),
        "completion_without_current_start": replace(complete, current_start_seen=False),
    }


__all__ = [
    "CURRENT_INPUTS",
    "CURRENT_CONTRACT_TICK",
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "RETIRED_INPUTS",
    "MAX_SEQUENCE_LENGTH",
    "REQUIRED_CURRENT_LABELS",
    "REQUIRED_REJECTION_LABELS",
    "State",
    "Tick",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
