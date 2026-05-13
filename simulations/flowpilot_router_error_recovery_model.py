"""FlowGuard model for FlowPilot RouterError recovery.

Risk purpose:
This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review
the `submit-output-to-router` runtime path when Router rejects a role output
after writing a control blocker. It guards against Controller chain breaks,
missing Router next-action handoff, swallowed non-control errors, hard-coded PM
routing, original-event acceptance after rejection, and sealed-body leakage.

Run with:
    python simulations/run_flowpilot_router_error_recovery_checks.py

Update this model whenever direct Router submission, control blocker handling,
or Controller recovery handoff changes.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One runtime submission/recovery decision."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | submitting | rejected | runtime_returned | waiting_for_role | plain_error_failed
    scenario: str = "unset"  # unset | control_blocker | plain_error
    router_error_kind: str = "none"  # none | control_blocker | plain

    role_output_submitted: bool = False
    router_rejected_event: bool = False
    control_blocker_written: bool = False
    control_blocker_count: int = 0
    original_event_accepted: bool = False
    original_event_retried_by_controller: bool = False

    runtime_exit_code: str = "unset"  # unset | success | failure
    runtime_returned_blocked_result: bool = False
    runtime_returned_control_blocker: bool = False
    runtime_requested_router_next_action: bool = False
    runtime_hardcoded_pm_target: bool = False
    next_action_source: str = "none"  # none | router | hardcoded
    next_action_type: str = "none"  # none | handle_control_blocker | await_role_decision | unsafe_continue
    next_action_target_role: str = "none"

    controller_applied_next_action: bool = False
    controller_self_repaired: bool = False
    controller_read_sealed_body: bool = False
    pm_or_target_role_wait_exposed: bool = False
    chain_broken: bool = False
    heartbeat_required_for_recovery: bool = False
    non_control_error_swallowed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


class RouterErrorRecoveryStep:
    """Model direct Router submission recovery.

    Input x State -> Set(Output x State)
    reads: Router submission result, RouterError control_blocker payload, and
    Router-computed next_action.
    writes: runtime JSON result or failure exit, controller-visible blocker
    metadata, and the next legal Router action.
    idempotency: converting one Router-written blocker into a blocked runtime
    result must not create a second blocker or accept the rejected event.
    """

    name = "RouterErrorRecoveryStep"
    reads = ("router_error", "control_blocker", "router_next_action")
    writes = ("runtime_result", "controller_next_action")
    input_description = "one direct role-output submission to Router"
    output_description = "accepted event, ordinary failure, or blocked result with Router next_action"
    idempotency = "control blocker is written once by Router; runtime only converts it into a handoff result"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def initial_state() -> State:
    return State()


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 4


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status == "new":
        yield Transition(
            "role_output_reaches_router_control_blocker_case",
            replace(state, status="submitting", scenario="control_blocker", role_output_submitted=True),
        )
        yield Transition(
            "role_output_reaches_router_plain_error_case",
            replace(state, status="submitting", scenario="plain_error", role_output_submitted=True),
        )
        return

    if state.status == "submitting" and state.scenario == "control_blocker":
        yield Transition(
            "router_rejects_event_and_writes_control_blocker",
            replace(
                state,
                status="rejected",
                router_error_kind="control_blocker",
                router_rejected_event=True,
                control_blocker_written=True,
                control_blocker_count=1,
            ),
        )
        return

    if state.status == "submitting" and state.scenario == "plain_error":
        yield Transition(
            "router_rejects_event_without_control_blocker",
            replace(
                state,
                status="plain_error_failed",
                router_error_kind="plain",
                router_rejected_event=True,
                runtime_exit_code="failure",
            ),
        )
        return

    if state.status == "rejected" and state.router_error_kind == "control_blocker":
        yield Transition(
            "runtime_returns_blocked_result_with_router_next_action",
            replace(
                state,
                status="runtime_returned",
                runtime_exit_code="success",
                runtime_returned_blocked_result=True,
                runtime_returned_control_blocker=True,
                runtime_requested_router_next_action=True,
                next_action_source="router",
                next_action_type="handle_control_blocker",
                next_action_target_role="project_manager",
            ),
        )
        return

    if state.status == "runtime_returned" and state.next_action_type == "handle_control_blocker":
        yield Transition(
            "controller_applies_router_next_action_and_waits_for_target_role",
            replace(
                state,
                status="waiting_for_role",
                controller_applied_next_action=True,
                pm_or_target_role_wait_exposed=True,
            ),
        )


def hazard_states() -> dict[str, State]:
    safe_rejected = State(
        status="rejected",
        scenario="control_blocker",
        router_error_kind="control_blocker",
        role_output_submitted=True,
        router_rejected_event=True,
        control_blocker_written=True,
        control_blocker_count=1,
    )
    safe_blocked = replace(
        safe_rejected,
        status="runtime_returned",
        runtime_exit_code="success",
        runtime_returned_blocked_result=True,
        runtime_returned_control_blocker=True,
        runtime_requested_router_next_action=True,
        next_action_source="router",
        next_action_type="handle_control_blocker",
        next_action_target_role="project_manager",
    )
    return {
        "control_blocker_error_broke_controller_chain": replace(
            safe_rejected,
            status="plain_error_failed",
            runtime_exit_code="failure",
            chain_broken=True,
            heartbeat_required_for_recovery=True,
        ),
        "blocked_result_missing_control_blocker": replace(
            safe_blocked,
            runtime_returned_control_blocker=False,
        ),
        "blocked_result_missing_next_action": replace(
            safe_blocked,
            runtime_requested_router_next_action=False,
            next_action_source="none",
            next_action_type="none",
        ),
        "runtime_hardcoded_pm_instead_of_router_next_action": replace(
            safe_blocked,
            runtime_requested_router_next_action=False,
            runtime_hardcoded_pm_target=True,
            next_action_source="hardcoded",
        ),
        "plain_router_error_swallowed": State(
            status="runtime_returned",
            scenario="plain_error",
            router_error_kind="plain",
            role_output_submitted=True,
            router_rejected_event=True,
            runtime_exit_code="success",
            non_control_error_swallowed=True,
        ),
        "rejected_event_marked_accepted": replace(
            safe_blocked,
            original_event_accepted=True,
        ),
        "controller_self_repairs_control_blocker": replace(
            safe_blocked,
            controller_self_repaired=True,
        ),
        "controller_reads_sealed_blocker_body": replace(
            safe_blocked,
            controller_read_sealed_body=True,
        ),
        "duplicate_blocker_written_during_recovery": replace(
            safe_blocked,
            control_blocker_count=2,
        ),
    }


def control_blocker_error_does_not_break_controller_chain(state: State, trace) -> InvariantResult:
    del trace
    if state.control_blocker_written and (state.chain_broken or state.heartbeat_required_for_recovery):
        return InvariantResult.fail("control blocker RouterError broke controller chain instead of returning Router next_action")
    if state.control_blocker_written and state.runtime_exit_code == "failure":
        return InvariantResult.fail("control blocker RouterError exited as failure")
    return InvariantResult.pass_()


def blocked_result_includes_control_blocker_and_next_action(state: State, trace) -> InvariantResult:
    del trace
    if not state.runtime_returned_blocked_result:
        return InvariantResult.pass_()
    if not state.runtime_returned_control_blocker:
        return InvariantResult.fail("blocked runtime result omitted control_blocker metadata")
    if not state.runtime_requested_router_next_action or state.next_action_source != "router":
        return InvariantResult.fail("blocked runtime result omitted Router-supplied next_action")
    if state.next_action_type in {"none", "unsafe_continue"}:
        return InvariantResult.fail("blocked runtime result exposed no legal recovery action")
    return InvariantResult.pass_()


def plain_router_errors_remain_failures(state: State, trace) -> InvariantResult:
    del trace
    if state.router_error_kind == "plain" and state.non_control_error_swallowed:
        return InvariantResult.fail("plain RouterError was swallowed as a successful blocked result")
    if state.router_error_kind == "plain" and state.runtime_exit_code == "success":
        return InvariantResult.fail("plain RouterError returned success")
    return InvariantResult.pass_()


def rejected_event_is_not_accepted_or_retried_by_controller(state: State, trace) -> InvariantResult:
    del trace
    if state.router_rejected_event and state.original_event_accepted:
        return InvariantResult.fail("rejected role event was marked accepted")
    if state.router_rejected_event and state.original_event_retried_by_controller:
        return InvariantResult.fail("Controller retried rejected event instead of following Router next_action")
    return InvariantResult.pass_()


def controller_does_not_self_repair_or_read_sealed_body(state: State, trace) -> InvariantResult:
    del trace
    if state.controller_self_repaired:
        return InvariantResult.fail("Controller attempted to self-repair a control blocker")
    if state.controller_read_sealed_body:
        return InvariantResult.fail("Controller read sealed control blocker body")
    return InvariantResult.pass_()


def recovery_does_not_create_duplicate_blockers(state: State, trace) -> InvariantResult:
    del trace
    if state.control_blocker_count > 1:
        return InvariantResult.fail("runtime recovery created duplicate control blockers")
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="control_blocker_error_does_not_break_controller_chain",
        description="A RouterError with control_blocker becomes a blocked runtime result, not a chain-breaking failure.",
        predicate=control_blocker_error_does_not_break_controller_chain,
    ),
    Invariant(
        name="blocked_result_includes_control_blocker_and_next_action",
        description="Blocked runtime results include control_blocker metadata and Router-supplied next_action.",
        predicate=blocked_result_includes_control_blocker_and_next_action,
    ),
    Invariant(
        name="plain_router_errors_remain_failures",
        description="Router errors without control_blocker still fail loudly.",
        predicate=plain_router_errors_remain_failures,
    ),
    Invariant(
        name="rejected_event_is_not_accepted_or_retried_by_controller",
        description="The rejected role event is not accepted or retried by Controller.",
        predicate=rejected_event_is_not_accepted_or_retried_by_controller,
    ),
    Invariant(
        name="controller_does_not_self_repair_or_read_sealed_body",
        description="Controller only relays Router next_action metadata and does not self-repair or read sealed bodies.",
        predicate=controller_does_not_self_repair_or_read_sealed_body,
    ),
    Invariant(
        name="recovery_does_not_create_duplicate_blockers",
        description="Runtime recovery conversion does not create duplicate control blockers.",
        predicate=recovery_does_not_create_duplicate_blockers,
    ),
)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.passed:
            failures.append(str(result.message or invariant.name))
    return failures


def next_states(state: State) -> Iterable[tuple[str, State]]:
    for transition in next_safe_states(state):
        yield transition.label, transition.state


def workflow() -> Workflow:
    return Workflow((RouterErrorRecoveryStep(),), name="flowpilot_router_error_recovery")


def build_workflow() -> Workflow:
    return workflow()


def is_terminal(state: State) -> bool:
    return state.status in {"waiting_for_role", "plain_error_failed"}


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return is_terminal(state)


def is_success(state: State) -> bool:
    return (
        state.status == "waiting_for_role"
        and state.runtime_returned_blocked_result
        and state.runtime_returned_control_blocker
        and state.runtime_requested_router_next_action
        and state.next_action_source == "router"
        and state.controller_applied_next_action
        and state.pm_or_target_role_wait_exposed
    ) or (
        state.status == "plain_error_failed"
        and state.router_error_kind == "plain"
        and state.runtime_exit_code == "failure"
    )
