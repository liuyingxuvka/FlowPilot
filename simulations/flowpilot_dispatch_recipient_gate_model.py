"""FlowGuard model for FlowPilot's Router pre-dispatch recipient gate.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  Router workflow that decides whether a role-facing dispatch may be exposed
  as Controller work.
- Guards against a busy target role receiving a second independent packet,
  mail, or PM role-work request before its prior obligation has closed.
- Treats user_intake as PM's first formal work material: the only PM system
  card allowed while PM holds user_intake is the pm.material_scan
  same-obligation instruction card, and independent PM dispatch waits until PM
  returns material/capability scan packet specs.
- Classifies role-facing system cards by obligation: only ACK-only cards are
  prompt/material delivery; any card or bundle that asks for a decision,
  report, packet, result, or blocker is an output-bearing work package.
- Also preserves existing dispatch constraints: same-role card bundles are one
  grouped delivery, different idle roles can work in parallel, illegal packets
  stay rejected, and PM remains busy while returned role-work results await PM
  disposition.
- Future agents should update this model when adding new role-facing dispatch
  action types, new unfinished-work ledgers, or new terminal status names.
- Companion command: python simulations/run_flowpilot_dispatch_recipient_gate_checks.py
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One abstract Router dispatch-gate tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | complete
    candidate_kind: str = "none"
    target_role: str = ""
    target_identity_valid: bool = True
    packet_legal: bool = True
    active_holder_legal: bool = True

    same_role_grouped_delivery: bool = False
    parallel_roles_unique: bool = True
    different_idle_roles_parallel: bool = False
    candidate_output_bearing: bool = True

    unresolved_ack_for_target: bool = False
    passive_wait_for_target: bool = False
    pending_expected_output_for_target: bool = False
    same_output_context_card: bool = False
    active_packet_held_by_target: bool = False
    same_obligation_instruction: bool = False
    prior_packet_completed_by_flow_state: bool = False
    pm_role_work_status_for_target: str = "none"  # none | open | packet_relayed | result_returned | result_relayed_to_pm | absorbed
    pm_disposition_pending: bool = False

    gate_ran: bool = False
    dispatch_exposed: bool = False
    wait_exposed: bool = False
    block_exposed: bool = False
    wait_target_role: str = ""
    wait_source_named: bool = True
    sealed_body_exposed_in_wait: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _base_candidate(kind: str, target_role: str) -> State:
    return State(status="running", candidate_kind=kind, target_role=target_role)


def _target_role_busy(state: State) -> bool:
    if state.unresolved_ack_for_target:
        return True
    if state.passive_wait_for_target:
        return True
    if not state.candidate_output_bearing:
        return False
    if state.pending_expected_output_for_target and not state.same_output_context_card:
        return True
    if (
        state.active_packet_held_by_target
        and not state.same_obligation_instruction
        and not state.prior_packet_completed_by_flow_state
    ):
        return True
    return state.pm_role_work_status_for_target in {"open", "packet_relayed"}


def _candidate_legal(state: State) -> bool:
    return state.target_identity_valid and state.packet_legal and state.active_holder_legal


def _gate_pass(state: State) -> State:
    return replace(state, status="complete", gate_ran=True, dispatch_exposed=True)


def _gate_wait(state: State, *, wait_target_role: str | None = None) -> State:
    return replace(
        state,
        status="complete",
        gate_ran=True,
        wait_exposed=True,
        wait_target_role=wait_target_role or state.target_role,
        wait_source_named=True,
    )


def _gate_block(state: State) -> State:
    return replace(state, status="complete", gate_ran=True, block_exposed=True)


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status != "new":
        return

    yield Transition(
        "dispatch_idle_work_packet",
        _gate_pass(_base_candidate("work_packet", "worker_a")),
    )

    yield Transition(
        "wait_for_busy_active_packet_before_dispatch",
        _gate_wait(replace(_base_candidate("work_packet", "worker_a"), active_packet_held_by_target=True)),
    )

    yield Transition(
        "wait_for_missing_ack_before_formal_packet",
        _gate_wait(replace(_base_candidate("work_packet", "human_like_reviewer"), unresolved_ack_for_target=True)),
    )

    yield Transition(
        "wait_for_passive_role_result_before_dispatch",
        _gate_wait(replace(_base_candidate("system_card", "process_flowguard_officer"), passive_wait_for_target=True)),
    )

    yield Transition(
        "allow_ack_only_prompt_while_packet_active",
        _gate_pass(
            replace(
                _base_candidate("system_card", "project_manager"),
                active_packet_held_by_target=True,
                candidate_output_bearing=False,
            )
        ),
    )

    yield Transition(
        "wait_for_pending_pm_output_before_independent_output_card",
        _gate_wait(
            replace(
                _base_candidate("system_card", "project_manager"),
                pending_expected_output_for_target=True,
                candidate_output_bearing=True,
            )
        ),
    )

    yield Transition(
        "allow_event_card_for_same_pending_pm_output",
        _gate_pass(
            replace(
                _base_candidate("system_card", "project_manager"),
                pending_expected_output_for_target=True,
                same_output_context_card=True,
                candidate_output_bearing=True,
            )
        ),
    )

    yield Transition(
        "allow_system_card_for_active_obligation",
        _gate_pass(
            replace(
                _base_candidate("system_card", "project_manager"),
                active_packet_held_by_target=True,
                same_obligation_instruction=True,
            )
        ),
    )

    yield Transition(
        "wait_for_user_intake_first_output_before_independent_pm_card",
        _gate_wait(replace(_base_candidate("system_card", "project_manager"), active_packet_held_by_target=True)),
    )

    yield Transition(
        "allow_pm_dispatch_after_user_intake_first_output",
        _gate_pass(
            replace(
                _base_candidate("mail", "project_manager"),
                active_packet_held_by_target=True,
                prior_packet_completed_by_flow_state=True,
            )
        ),
    )

    yield Transition(
        "allow_same_role_system_card_bundle",
        _gate_pass(replace(_base_candidate("system_card_bundle", "project_manager"), same_role_grouped_delivery=True)),
    )

    yield Transition(
        "allow_different_idle_roles_parallel",
        _gate_pass(
            replace(
                _base_candidate("parallel_work_packet_batch", "worker_a,worker_b"),
                different_idle_roles_parallel=True,
                parallel_roles_unique=True,
            )
        ),
    )

    yield Transition(
        "block_duplicate_same_role_batch",
        _gate_block(
            replace(
                _base_candidate("parallel_work_packet_batch", "worker_a"),
                parallel_roles_unique=False,
            )
        ),
    )

    yield Transition(
        "block_illegal_packet_even_when_idle",
        _gate_block(replace(_base_candidate("work_packet", "worker_b"), packet_legal=False)),
    )

    yield Transition(
        "allow_worker_after_role_work_result_returned",
        _gate_pass(
            replace(
                _base_candidate("work_packet", "worker_b"),
                pm_role_work_status_for_target="result_returned",
                pm_disposition_pending=True,
            )
        ),
    )

    yield Transition(
        "wait_for_pm_disposition_before_new_pm_dispatch",
        _gate_wait(
            replace(_base_candidate("mail", "project_manager"), pm_disposition_pending=True),
            wait_target_role="project_manager",
        ),
    )


class DispatchRecipientGateStep:
    """Model one Router pre-dispatch gate transition.

    Input x State -> Set(Output x State)
    reads: candidate dispatch metadata, target role, ACK returns, passive waits,
    packet ledger, PM role-work index, packet legality, grouping metadata
    writes: either a dispatch exposure, wait exposure, or block exposure
    idempotency: repeated gate checks for the same candidate must not create a
    second dispatch while the same busy source remains unfinished.
    """

    name = "DispatchRecipientGateStep"
    input_description = "FlowPilot dispatch candidate"
    output_description = "dispatch pass, wait, or block"
    reads = (
        "candidate_action",
        "pending_return_ledger",
        "controller_action_ledger",
        "packet_ledger",
        "pm_role_work_index",
        "packet_validation",
        "grouping_metadata",
    )
    writes = ("controller_action_exposure", "wait_exposure", "blocker_exposure")
    idempotency = "candidate action id plus busy source id"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures

    if not state.gate_ran:
        failures.append("dispatch candidate reached terminal state without running recipient gate")

    exposed_outputs = sum(bool(item) for item in (state.dispatch_exposed, state.wait_exposed, state.block_exposed))
    if exposed_outputs != 1:
        failures.append("recipient gate must expose exactly one of dispatch, wait, or block")

    if state.dispatch_exposed and not _candidate_legal(state):
        failures.append("illegal packet or target dispatch was exposed")

    if state.dispatch_exposed and not state.parallel_roles_unique:
        failures.append("same batch assigned two independent open packets to one role")

    if (
        state.dispatch_exposed
        and _target_role_busy(state)
        and not state.same_role_grouped_delivery
    ):
        failures.append("busy target role received a second independent dispatch")

    if (
        state.candidate_kind == "system_card"
        and not state.candidate_output_bearing
        and state.active_packet_held_by_target
        and not state.dispatch_exposed
    ):
        failures.append("ACK-only prompt card was treated as independent work")

    if (
        state.candidate_kind == "system_card"
        and state.pending_expected_output_for_target
        and state.same_output_context_card
        and not state.dispatch_exposed
    ):
        failures.append("same-output event/context card was blocked")

    if state.wait_exposed and not state.wait_source_named:
        failures.append("busy-recipient wait did not name the blocking source")

    if state.wait_exposed and state.sealed_body_exposed_in_wait:
        failures.append("busy-recipient wait exposed sealed body content")

    if (
        state.same_role_grouped_delivery
        and state.candidate_kind == "system_card_bundle"
        and not state.dispatch_exposed
    ):
        failures.append("same-role system-card bundle was rejected instead of treated as one grouped delivery")

    if (
        state.candidate_kind == "system_card"
        and state.active_packet_held_by_target
        and state.same_obligation_instruction
        and not state.dispatch_exposed
    ):
        failures.append("same-obligation instruction card was blocked")

    if (
        state.active_packet_held_by_target
        and state.prior_packet_completed_by_flow_state
        and not state.dispatch_exposed
    ):
        failures.append("prior packet completion did not free the target role")

    if state.different_idle_roles_parallel and state.parallel_roles_unique and not state.dispatch_exposed:
        failures.append("different idle roles were blocked from parallel dispatch")

    if (
        state.pm_role_work_status_for_target in {"result_returned", "result_relayed_to_pm"}
        and state.target_role != "project_manager"
        and state.dispatch_exposed is False
    ):
        failures.append("returned role-work result did not free the original target role")

    if (
        state.pm_disposition_pending
        and state.target_role == "project_manager"
        and not state.same_obligation_instruction
        and state.dispatch_exposed
    ):
        failures.append("PM received a new dispatch while prior result disposition was pending")

    return failures


def dispatch_gate_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_dispatch_recipient_gate_blocks_busy_recipients",
        description=(
            "Router may expose role-facing dispatch only after checking target "
            "identity, packet legality, grouping rules, and recipient idle state."
        ),
        predicate=dispatch_gate_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2


def build_workflow() -> Workflow:
    return Workflow((DispatchRecipientGateStep(),), name="flowpilot_dispatch_recipient_gate")


def is_terminal(state: State) -> bool:
    return state.status == "complete"


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def implementation_plan_state() -> State:
    return _gate_wait(replace(_base_candidate("work_packet", "worker_a"), active_packet_held_by_target=True))


def hazard_states() -> dict[str, State]:
    safe = _gate_pass(_base_candidate("work_packet", "worker_a"))
    return {
        "busy_active_packet_dispatch_exposed": replace(safe, active_packet_held_by_target=True),
        "missing_ack_dispatch_exposed": replace(
            safe,
            target_role="human_like_reviewer",
            unresolved_ack_for_target=True,
        ),
        "passive_wait_dispatch_exposed": replace(
            safe,
            target_role="process_flowguard_officer",
            passive_wait_for_target=True,
        ),
        "ack_only_prompt_blocked_as_work": _gate_wait(
            replace(
                _base_candidate("system_card", "project_manager"),
                active_packet_held_by_target=True,
                candidate_output_bearing=False,
            )
        ),
        "independent_output_card_exposed_while_pm_output_pending": _gate_pass(
            replace(
                _base_candidate("system_card", "project_manager"),
                pending_expected_output_for_target=True,
                candidate_output_bearing=True,
            )
        ),
        "same_output_context_card_blocked": _gate_wait(
            replace(
                _base_candidate("system_card", "project_manager"),
                pending_expected_output_for_target=True,
                same_output_context_card=True,
                candidate_output_bearing=True,
            )
        ),
        "duplicate_same_role_batch_exposed": replace(
            safe,
            candidate_kind="parallel_work_packet_batch",
            parallel_roles_unique=False,
        ),
        "illegal_packet_exposed": replace(safe, packet_legal=False),
        "same_role_bundle_rejected": _gate_block(
            replace(_base_candidate("system_card_bundle", "project_manager"), same_role_grouped_delivery=True)
        ),
        "system_card_for_active_holder_blocked": _gate_wait(
            replace(
                _base_candidate("system_card", "project_manager"),
                active_packet_held_by_target=True,
                same_obligation_instruction=True,
            )
        ),
        "independent_pm_card_exposed_while_user_intake_active": _gate_pass(
            replace(_base_candidate("system_card", "project_manager"), active_packet_held_by_target=True)
        ),
        "user_intake_first_output_still_blocks_pm": _gate_wait(
            replace(
                _base_candidate("mail", "project_manager"),
                active_packet_held_by_target=True,
                prior_packet_completed_by_flow_state=True,
            )
        ),
        "different_idle_parallel_blocked": _gate_block(
            replace(
                _base_candidate("parallel_work_packet_batch", "worker_a,worker_b"),
                different_idle_roles_parallel=True,
                parallel_roles_unique=True,
            )
        ),
        "returned_worker_result_still_blocks_worker": _gate_wait(
            replace(
                _base_candidate("work_packet", "worker_b"),
                pm_role_work_status_for_target="result_returned",
                pm_disposition_pending=True,
            )
        ),
        "pm_dispatch_exposed_before_disposition": replace(
            safe,
            candidate_kind="mail",
            target_role="project_manager",
            pm_disposition_pending=True,
        ),
        "wait_leaks_sealed_body": replace(
            _gate_wait(replace(_base_candidate("work_packet", "worker_a"), active_packet_held_by_target=True)),
            sealed_body_exposed_in_wait=True,
        ),
    }
