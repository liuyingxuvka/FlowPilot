"""FlowGuard model for PM-visible role-authored summary handoff."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_pm_visible_summary"
MAX_SEQUENCE_LENGTH = 8
CONCRETE_REPAIR = "replace stale lifecycle path with current lifecycle path"
GENERIC_REPAIR = "reviewer reported fail"


@dataclass(frozen=True)
class State:
    status: str = "new"
    path: str = ""
    role_result_submitted: bool = False
    summary_present: bool = False
    runner_synthesized_summary: bool = False
    result_contract_blocked: bool = False
    reissue_issued: bool = False
    role_result_accepted: bool = False
    semantic_blocking: bool = False
    required_repair_present: bool = False
    blocker_recorded: bool = False
    pm_packet_issued: bool = False
    pm_summary_context_present: bool = False
    pm_recommended_resolution: str = ""


@dataclass(frozen=True)
class Tick:
    """One role-result to PM-context handoff transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "submit_role_result_without_summary",
    "block_missing_summary_and_reissue_packet",
    "complete_missing_summary_reissue",
    "submit_passing_role_result_with_summary",
    "accept_role_result_summary",
    "issue_pm_packet_with_recent_summary",
    "complete_passing_summary_handoff",
    "submit_blocking_reviewer_result_with_required_repair",
    "record_concrete_required_repair_blocker",
    "issue_pm_repair_packet_with_summary_and_concrete_repair",
    "complete_concrete_repair_handoff",
)


def initial_state() -> State:
    return State()


class PMVisibleSummaryStep:
    """Model role-authored summary handoff.

    Input x State -> Set(Output x State)
    reads: current packet kind, role result body, semantic blocker payload,
    previous accepted/blocking role results.
    writes: result contract status, reissue packet, semantic blocker,
    PM packet body summary context, and PM-facing repair guidance.
    """

    name = "PMVisibleSummaryStep"
    reads = ("packet", "result_body", "active_blockers", "recent_results")
    writes = ("result_status", "packet_status", "pm_packet_body", "active_blockers")
    input_description = "Input x State: one current role result or PM packet issue"
    output_description = "Set(Output x State): block/reissue or PM-visible role summary handoff"
    idempotency = "summary context is source result scoped and runner never synthesizes text"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_pm_visible_summary_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return (
            Transition(
                "submit_role_result_without_summary",
                replace(state, status="missing_summary", path="missing_summary", role_result_submitted=True),
            ),
            Transition(
                "submit_passing_role_result_with_summary",
                replace(
                    state,
                    status="passing_summary",
                    path="passing_summary",
                    role_result_submitted=True,
                    summary_present=True,
                ),
            ),
            Transition(
                "submit_blocking_reviewer_result_with_required_repair",
                replace(
                    state,
                    status="blocking_summary",
                    path="blocking_summary",
                    role_result_submitted=True,
                    summary_present=True,
                    semantic_blocking=True,
                    required_repair_present=True,
                ),
            ),
        )
    if state.status == "missing_summary" and not state.result_contract_blocked:
        return (
            Transition(
                "block_missing_summary_and_reissue_packet",
                replace(state, result_contract_blocked=True, reissue_issued=True),
            ),
        )
    if state.status == "missing_summary" and state.result_contract_blocked and state.reissue_issued:
        return (Transition("complete_missing_summary_reissue", replace(state, status="complete")),)
    if state.status == "passing_summary" and not state.role_result_accepted:
        return (Transition("accept_role_result_summary", replace(state, role_result_accepted=True)),)
    if state.status == "passing_summary" and not state.pm_packet_issued:
        return (
            Transition(
                "issue_pm_packet_with_recent_summary",
                replace(state, pm_packet_issued=True, pm_summary_context_present=True),
            ),
        )
    if state.status == "passing_summary" and state.pm_packet_issued:
        return (Transition("complete_passing_summary_handoff", replace(state, status="complete")),)
    if state.status == "blocking_summary" and not state.blocker_recorded:
        return (
            Transition(
                "record_concrete_required_repair_blocker",
                replace(state, blocker_recorded=True, pm_recommended_resolution=CONCRETE_REPAIR),
            ),
        )
    if state.status == "blocking_summary" and state.blocker_recorded and not state.pm_packet_issued:
        return (
            Transition(
                "issue_pm_repair_packet_with_summary_and_concrete_repair",
                replace(state, pm_packet_issued=True, pm_summary_context_present=True),
            ),
        )
    if state.status == "blocking_summary" and state.pm_packet_issued:
        return (Transition("complete_concrete_repair_handoff", replace(state, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.runner_synthesized_summary:
        failures.append("runner synthesized PM-visible summary instead of relaying role-authored text")
    if state.role_result_submitted and not state.summary_present:
        if state.role_result_accepted:
            failures.append("role result accepted without required PM-visible summary")
        if state.pm_packet_issued or state.pm_summary_context_present:
            failures.append("PM packet received summary context from a result that had no role-authored summary")
        if state.status == "complete" and not (state.result_contract_blocked and state.reissue_issued):
            failures.append("missing summary path completed without contract block and reissue")
    if state.result_contract_blocked and not state.reissue_issued:
        failures.append("missing summary contract block did not reissue current packet family")
    if state.summary_present and state.role_result_accepted and state.pm_packet_issued and not state.pm_summary_context_present:
        failures.append("PM packet missed recent role-authored report summary")
    if state.semantic_blocking and state.required_repair_present:
        if state.blocker_recorded and state.pm_recommended_resolution != CONCRETE_REPAIR:
            failures.append("semantic blocker did not preserve concrete required repair")
        if state.pm_packet_issued and state.pm_recommended_resolution == GENERIC_REPAIR:
            failures.append("PM repair packet fell back to generic reviewer failure despite concrete repair")
    if state.pm_summary_context_present and not state.summary_present:
        failures.append("PM summary context exists without role-authored summary")
    return failures


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "pm_visible_role_summary_invariants",
        "Role summaries are required, role-authored, and relayed into PM packets with concrete repair guidance.",
        _invariant,
    ),
)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    if invariant_failures(state) or state.status != "complete":
        return False
    if state.path == "missing_summary":
        return state.result_contract_blocked and state.reissue_issued
    if state.path == "passing_summary":
        return state.role_result_accepted and state.pm_packet_issued and state.pm_summary_context_present
    if state.path == "blocking_summary":
        return (
            state.blocker_recorded
            and state.pm_packet_issued
            and state.pm_summary_context_present
            and state.pm_recommended_resolution == CONCRETE_REPAIR
        )
    return False


def target_state_for_path(path: str) -> State:
    state = initial_state()
    for _ in range(MAX_SEQUENCE_LENGTH):
        transitions = next_safe_states(state)
        if not state.path:
            transitions = tuple(transition for transition in transitions if transition.state.path == path)
        if not transitions:
            break
        state = transitions[0].state
    return state


def hazard_states() -> dict[str, State]:
    return {
        "accepted_without_summary": State(
            status="complete",
            path="missing_summary",
            role_result_submitted=True,
            role_result_accepted=True,
        ),
        "runner_synthesized_summary": State(
            status="complete",
            path="missing_summary",
            role_result_submitted=True,
            runner_synthesized_summary=True,
            pm_packet_issued=True,
            pm_summary_context_present=True,
        ),
        "blocked_without_reissue": State(
            status="complete",
            path="missing_summary",
            role_result_submitted=True,
            result_contract_blocked=True,
        ),
        "pm_packet_missing_summary_context": State(
            status="complete",
            path="passing_summary",
            role_result_submitted=True,
            summary_present=True,
            role_result_accepted=True,
            pm_packet_issued=True,
        ),
        "generic_repair_overrode_concrete_repair": State(
            status="complete",
            path="blocking_summary",
            role_result_submitted=True,
            summary_present=True,
            semantic_blocking=True,
            required_repair_present=True,
            blocker_recorded=True,
            pm_packet_issued=True,
            pm_summary_context_present=True,
            pm_recommended_resolution=GENERIC_REPAIR,
        ),
    }


def state_summary(state: State) -> dict[str, bool | str]:
    return {
        "status": state.status,
        "path": state.path,
        "summary_present": state.summary_present,
        "result_contract_blocked": state.result_contract_blocked,
        "reissue_issued": state.reissue_issued,
        "role_result_accepted": state.role_result_accepted,
        "semantic_blocking": state.semantic_blocking,
        "required_repair_present": state.required_repair_present,
        "pm_packet_issued": state.pm_packet_issued,
        "pm_summary_context_present": state.pm_summary_context_present,
        "pm_recommended_resolution": state.pm_recommended_resolution,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(PMVisibleSummaryStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)


__all__ = [
    "CONCRETE_REPAIR",
    "EXTERNAL_INPUTS",
    "GENERIC_REPAIR",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "REQUIRED_SAFE_LABELS",
    "State",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "state_summary",
    "target_state_for_path",
    "terminal_predicate",
]
