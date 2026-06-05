"""FlowGuard model for reattaching PM-stopped blockers to required recheck."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_stopped_blocker_recheck"
MAX_SEQUENCE_LENGTH = 12
RECHECK_ROLES = ("flowguard_operator", "reviewer")


@dataclass(frozen=True)
class State:
    status: str = "new"
    recheck_role: str = ""
    pm_stop_recorded: bool = False
    wait_observed: bool = False
    user_requested_recovery: bool = False
    target_previous_status_recorded: bool = False
    target_packet_status: str = ""
    target_restored: bool = False
    blocker_status: str = "active"
    fresh_flowguard_packet_issued: bool = False
    flowguard_passed: bool = False
    fresh_reviewer_packet_issued: bool = False
    reviewer_passed: bool = False
    direct_clear_attempted: bool = False
    reused_old_recheck_packet: bool = False
    pm_reissue_loop_attempted: bool = False
    reattached_without_user_request: bool = False


@dataclass(frozen=True)
class Tick:
    """One stopped-blocker recovery transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "select_flowguard_operator_stopped_blocker",
    "select_reviewer_stopped_blocker",
    "keep_stopped_until_user_request",
    "record_user_requested_recovery",
    "restore_pm_stopped_target_status",
    "reattach_blocker_to_awaiting_recheck",
    "issue_fresh_flowguard_recheck_packet",
    "record_fresh_flowguard_pass",
    "issue_fresh_reviewer_after_flowguard",
    "issue_fresh_reviewer_recheck_packet",
    "record_fresh_reviewer_pass",
    "clear_blocker_via_existing_owner_pass",
)


def initial_state() -> State:
    return State()


def _stopped_state(recheck_role: str) -> State:
    return State(
        status="stopped",
        recheck_role=recheck_role,
        pm_stop_recorded=True,
        target_previous_status_recorded=True,
        target_packet_status="pm_stopped",
        blocker_status="stopped",
    )


class StoppedBlockerRecheckStep:
    """Model stopped semantic blocker recovery.

    Input x State -> Set(Output x State)
    reads: stopped blocker metadata, target packet status, user recovery request,
    existing FlowGuard/Reviewer packet state.
    writes: blocker recovery markers, target packet status, fresh recheck packet,
    and eventual blocker clearance through owner-pass semantics.
    """

    name = "StoppedBlockerRecheckStep"
    reads = (
        "active_blockers",
        "packets",
        "results",
        "pm_repair_decisions",
        "user_recovery_request",
    )
    writes = (
        "active_blockers",
        "packets",
        "events",
    )
    input_description = "Input x State: one stopped-blocker recovery action"
    output_description = "Set(Output x State): wait, reattach, fresh owner recheck, or owner-pass clearance"
    idempotency = "reattachment is per stopped blocker and does not clear without fresh owner pass"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_stopped_blocker_recheck_invariant", replace(state, status="blocked")),)
    if state.status == "new":
        return tuple(
            Transition(f"select_{role}_stopped_blocker", _stopped_state(role)) for role in RECHECK_ROLES
        )
    if state.status == "stopped" and not state.wait_observed:
        return (Transition("keep_stopped_until_user_request", replace(state, wait_observed=True)),)
    if state.status == "stopped" and not state.user_requested_recovery:
        return (Transition("record_user_requested_recovery", replace(state, user_requested_recovery=True)),)
    if state.status == "stopped" and not state.target_restored:
        return (
            Transition(
                "restore_pm_stopped_target_status",
                replace(state, target_restored=True, target_packet_status="result_submitted"),
            ),
        )
    if state.status == "stopped" and state.blocker_status == "stopped":
        return (
            Transition(
                "reattach_blocker_to_awaiting_recheck",
                replace(state, status="awaiting_recheck", blocker_status="awaiting_recheck"),
            ),
        )
    if state.status == "awaiting_recheck" and state.recheck_role == "flowguard_operator":
        if not state.fresh_flowguard_packet_issued:
            return (
                Transition(
                    "issue_fresh_flowguard_recheck_packet",
                    replace(state, fresh_flowguard_packet_issued=True),
                ),
            )
        if not state.flowguard_passed:
            return (Transition("record_fresh_flowguard_pass", replace(state, flowguard_passed=True)),)
        if not state.fresh_reviewer_packet_issued:
            return (
                Transition(
                    "issue_fresh_reviewer_after_flowguard",
                    replace(state, fresh_reviewer_packet_issued=True),
                ),
            )
    if state.status == "awaiting_recheck" and state.recheck_role == "reviewer":
        if not state.fresh_reviewer_packet_issued:
            return (
                Transition(
                    "issue_fresh_reviewer_recheck_packet",
                    replace(state, fresh_reviewer_packet_issued=True),
                ),
            )
    if state.status == "awaiting_recheck" and state.fresh_reviewer_packet_issued and not state.reviewer_passed:
        return (Transition("record_fresh_reviewer_pass", replace(state, reviewer_passed=True)),)
    if state.status == "awaiting_recheck" and state.reviewer_passed and state.blocker_status != "cleared":
        return (
            Transition(
                "clear_blocker_via_existing_owner_pass",
                replace(state, status="complete", blocker_status="cleared"),
            ),
        )
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.pm_reissue_loop_attempted:
        failures.append("stopped blocker recovery looped through PM instead of required recheck")
    if state.direct_clear_attempted:
        failures.append("stopped blocker recovery attempted direct blocker clearance")
    if state.reused_old_recheck_packet:
        failures.append("stopped blocker recovery reused old recheck packet")
    if state.reattached_without_user_request:
        failures.append("stopped blocker reattached without explicit user request")
    if state.pm_stop_recorded and state.blocker_status == "stopped" and state.status != "stopped":
        failures.append("stopped blocker status diverged from stopped runtime state")
    if state.user_requested_recovery and not state.pm_stop_recorded:
        failures.append("user recovery recorded before PM stop")
    if state.target_restored and not state.target_previous_status_recorded:
        failures.append("PM-stopped target restored without recorded previous status")
    if state.blocker_status == "awaiting_recheck" and not state.user_requested_recovery:
        failures.append("blocker entered awaiting_recheck without explicit user request")
    if state.blocker_status == "awaiting_recheck" and not state.target_restored:
        failures.append("blocker reattached before PM-stopped target was restored")
    if state.blocker_status == "awaiting_recheck" and state.target_packet_status == "pm_stopped":
        failures.append("recheck issued while target packet remained pm_stopped")
    if state.fresh_flowguard_packet_issued and state.recheck_role != "flowguard_operator":
        failures.append("FlowGuard recheck packet issued for non-FlowGuard blocker")
    if state.flowguard_passed and not state.fresh_flowguard_packet_issued:
        failures.append("FlowGuard pass recorded before fresh FlowGuard recheck packet")
    if state.recheck_role == "flowguard_operator" and state.fresh_reviewer_packet_issued and not state.flowguard_passed:
        failures.append("Reviewer packet issued before fresh FlowGuard pass")
    if state.reviewer_passed and not state.fresh_reviewer_packet_issued:
        failures.append("Reviewer pass recorded before fresh Reviewer recheck packet")
    if state.blocker_status == "cleared" and not state.reviewer_passed:
        failures.append("blocker cleared before fresh Reviewer pass")
    if state.status == "complete" and state.blocker_status != "cleared":
        failures.append("recovery completed before blocker cleared")
    return failures


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "stopped_blocker_recheck_invariants",
        "Stopped blockers wait for user recovery, reattach to fresh owner recheck, and clear only on owner pass.",
        _invariant,
    ),
)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete" and state.blocker_status == "cleared" and not invariant_failures(state)


def target_state_for_role(recheck_role: str) -> State:
    state = _stopped_state(recheck_role)
    for _ in range(MAX_SEQUENCE_LENGTH):
        transitions = next_safe_states(state)
        if not transitions:
            break
        state = transitions[0].state
    return state


def hazard_states() -> dict[str, State]:
    reviewer_stopped = _stopped_state("reviewer")
    flowguard_stopped = _stopped_state("flowguard_operator")
    return {
        "reattached_without_user_request": replace(
            reviewer_stopped,
            target_restored=True,
            target_packet_status="result_submitted",
            blocker_status="awaiting_recheck",
            reattached_without_user_request=True,
        ),
        "pm_reissue_loop_after_stop": replace(flowguard_stopped, pm_reissue_loop_attempted=True),
        "direct_clear_after_break_glass": replace(
            reviewer_stopped,
            user_requested_recovery=True,
            target_restored=True,
            target_packet_status="result_submitted",
            blocker_status="cleared",
            status="complete",
            direct_clear_attempted=True,
        ),
        "stale_recheck_packet_reused": replace(
            target_state_for_role("flowguard_operator"),
            reused_old_recheck_packet=True,
        ),
        "target_unrestored_at_recheck": replace(
            reviewer_stopped,
            user_requested_recovery=True,
            blocker_status="awaiting_recheck",
            target_packet_status="pm_stopped",
        ),
        "cleared_before_reviewer_pass": replace(
            reviewer_stopped,
            user_requested_recovery=True,
            target_restored=True,
            target_packet_status="result_submitted",
            blocker_status="cleared",
            status="complete",
        ),
    }


def state_summary(state: State) -> dict[str, bool | str]:
    return {
        "status": state.status,
        "recheck_role": state.recheck_role,
        "blocker_status": state.blocker_status,
        "user_requested_recovery": state.user_requested_recovery,
        "target_packet_status": state.target_packet_status,
        "fresh_flowguard_packet_issued": state.fresh_flowguard_packet_issued,
        "flowguard_passed": state.flowguard_passed,
        "fresh_reviewer_packet_issued": state.fresh_reviewer_packet_issued,
        "reviewer_passed": state.reviewer_passed,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(StoppedBlockerRecheckStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "MODEL_ID",
    "REQUIRED_SAFE_LABELS",
    "RECHECK_ROLES",
    "State",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "state_summary",
    "target_state_for_role",
    "terminal_predicate",
]
