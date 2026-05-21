"""FlowGuard model for FlowPilot Controller process asides.

Risk intent:
- Add a short Controller-facing process aside channel without creating a second
  report body, evidence source, approval path, or Worker-to-Worker chat lane.
- Keep Router's role simple: preserve and expose aside metadata, but never
  semantically inspect aside text or use it to satisfy waits.
- Keep missing asides optional so formal packet/result/role-output paths still
  decide progress.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


VALID_SCENARIOS = (
    "aside_with_valid_formal_output",
    "aside_omitted_formal_output_ok",
    "controller_uses_aside_for_operational_status",
)

NEGATIVE_SCENARIOS = (
    "aside_satisfies_formal_wait",
    "aside_replaces_formal_body",
    "aside_becomes_evidence",
    "aside_drives_router_event",
    "worker_to_worker_aside",
    "missing_aside_blocks_flow",
    "controller_reports_formal_content_from_aside",
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS
MAX_SEQUENCE_LENGTH = 1
REQUIRED_LABELS = tuple(
    [f"accept_{scenario}" for scenario in VALID_SCENARIOS]
    + [f"reject_{scenario}" for scenario in NEGATIVE_SCENARIOS]
)


@dataclass(frozen=True)
class Tick:
    """One Controller process-aside boundary decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    aside_present: bool = False
    aside_labeled_process_only: bool = False
    aside_marked_not_formal_evidence: bool = False
    aside_marked_no_progress_authority: bool = False
    formal_output_present: bool = False
    formal_output_validated: bool = False
    formal_wait_satisfied_by_formal_output: bool = False
    formal_wait_satisfied_by_aside: bool = False
    router_preserved_aside: bool = False
    router_semantically_inspected_aside: bool = False
    router_event_derived_from_aside: bool = False
    controller_reads_aside: bool = False
    controller_uses_aside_for_operational_status: bool = False
    controller_uses_aside_for_formal_content: bool = False
    worker_aside_controller_only: bool = True
    worker_aside_visible_to_sibling_worker: bool = False
    missing_aside_blocks_flow: bool = False


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
    if scenario == "aside_with_valid_formal_output":
        return _accepted(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            aside_marked_not_formal_evidence=True,
            aside_marked_no_progress_authority=True,
            formal_output_present=True,
            formal_output_validated=True,
            formal_wait_satisfied_by_formal_output=True,
            router_preserved_aside=True,
            controller_reads_aside=True,
            controller_uses_aside_for_operational_status=True,
        )
    if scenario == "aside_omitted_formal_output_ok":
        return _accepted(
            scenario,
            formal_output_present=True,
            formal_output_validated=True,
            formal_wait_satisfied_by_formal_output=True,
        )
    if scenario == "controller_uses_aside_for_operational_status":
        return _accepted(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            aside_marked_not_formal_evidence=True,
            aside_marked_no_progress_authority=True,
            formal_output_present=True,
            formal_output_validated=True,
            formal_wait_satisfied_by_formal_output=True,
            router_preserved_aside=True,
            controller_reads_aside=True,
            controller_uses_aside_for_operational_status=True,
        )
    if scenario == "aside_satisfies_formal_wait":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            aside_marked_not_formal_evidence=True,
            aside_marked_no_progress_authority=True,
            formal_output_present=False,
            formal_wait_satisfied_by_aside=True,
            router_preserved_aside=True,
        )
    if scenario == "aside_replaces_formal_body":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            formal_output_present=False,
            formal_output_validated=True,
        )
    if scenario == "aside_becomes_evidence":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            formal_output_present=True,
            formal_wait_satisfied_by_formal_output=True,
            aside_marked_not_formal_evidence=False,
            controller_uses_aside_for_formal_content=True,
        )
    if scenario == "aside_drives_router_event":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            router_preserved_aside=True,
            router_semantically_inspected_aside=True,
            router_event_derived_from_aside=True,
        )
    if scenario == "worker_to_worker_aside":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            worker_aside_controller_only=False,
            worker_aside_visible_to_sibling_worker=True,
        )
    if scenario == "missing_aside_blocks_flow":
        return _rejected(
            scenario,
            aside_present=False,
            formal_output_present=True,
            formal_output_validated=True,
            missing_aside_blocks_flow=True,
        )
    if scenario == "controller_reports_formal_content_from_aside":
        return _rejected(
            scenario,
            aside_present=True,
            aside_labeled_process_only=True,
            aside_marked_not_formal_evidence=True,
            formal_output_present=True,
            formal_wait_satisfied_by_formal_output=True,
            controller_reads_aside=True,
            controller_uses_aside_for_formal_content=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


class ControllerProcessAsideStep:
    """Model the aside handoff boundary.

    Input x State -> Set(Output x State)
    reads: role work metadata, optional controller_aside, formal output state
    writes: Controller-visible process context only
    idempotency: repeated aside reads do not create formal events or approvals
    """

    name = "ControllerProcessAsideStep"
    input_description = "one optional Controller process-aside boundary"
    output_description = "accepted or rejected process-aside transition"
    reads = ("role_metadata", "controller_aside", "formal_output_state")
    writes = ("controller_visible_process_context",)
    idempotency = "process aside visibility never advances formal state"

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


def process_aside_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "accepted" and state.scenario not in VALID_SCENARIOS:
        failures.append("accepted a known-bad process-aside scenario")
    if state.status == "rejected" and state.scenario in VALID_SCENARIOS:
        failures.append("rejected a valid process-aside scenario")
    if state.status == "accepted" and state.aside_present:
        if not state.aside_labeled_process_only:
            failures.append("process aside lacked process-only label")
        if not state.aside_marked_not_formal_evidence:
            failures.append("process aside was not marked non-evidence")
        if not state.aside_marked_no_progress_authority:
            failures.append("process aside was not marked non-authority")
    if state.status == "accepted" and state.formal_wait_satisfied_by_aside:
        failures.append("process aside satisfied a formal wait")
    if state.status == "accepted" and state.formal_output_validated and not state.formal_output_present:
        failures.append("process aside replaced the formal output body")
    if state.status == "accepted" and state.router_semantically_inspected_aside:
        failures.append("Router semantically inspected process aside text")
    if state.status == "accepted" and state.router_event_derived_from_aside:
        failures.append("Router derived a formal event from process aside text")
    if state.status == "accepted" and state.controller_uses_aside_for_formal_content:
        failures.append("Controller used process aside as formal content")
    if state.status == "accepted" and state.worker_aside_visible_to_sibling_worker:
        failures.append("worker process aside became Worker-to-Worker communication")
    if state.status == "accepted" and state.missing_aside_blocks_flow:
        failures.append("missing optional process aside blocked formal flow")
    return failures


def invariant_failures(state: State) -> list[str]:
    return process_aside_failures(state)


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((ControllerProcessAsideStep(),), name="flowpilot_controller_process_aside")


def accepts_only_safe_process_asides(state: State, trace) -> InvariantResult:
    del trace
    failures = process_aside_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def _invariant(name: str, description: str) -> Invariant[State]:
    return Invariant(
        name=name,
        description=description,
        predicate=accepts_only_safe_process_asides,
    )


INVARIANTS = (
    _invariant(
        "controller_process_aside_has_no_formal_authority",
        "Process asides must not satisfy waits, replace bodies, create events, or become evidence.",
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
    "process_aside_failures",
    "scenario_state",
    "terminal_predicate",
]
