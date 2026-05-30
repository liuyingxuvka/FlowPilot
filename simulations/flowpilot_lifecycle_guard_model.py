"""FlowGuard model for the new FlowPilot lifecycle guard."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_new_lifecycle_guard"
MAX_SEQUENCE_LENGTH = 16


@dataclass(frozen=True)
class State:
    status: str = "new"
    current_run_ledger_loaded: bool = False
    packet_ledger_loaded: bool = False
    leases_loaded: bool = False
    nonterminal_next_action_seen: bool = False
    guard_snapshot_written: bool = False
    controller_stop_blocked: bool = False
    manual_resume_requested: bool = False
    resume_rehydrated_from_ledger: bool = False
    wait_for_ack_classified: bool = False
    ack_wait_nonterminal: bool = False
    wait_for_result_classified: bool = False
    result_wait_nonterminal: bool = False
    inactive_lease_recovery_classified: bool = False
    stale_result_quarantined: bool = False
    repeated_action_stuck_classified: bool = False
    final_closure_complete: bool = False
    terminal_stop_allowed: bool = False
    old_monitor_ui_required: bool = False
    old_router_authority_used: bool = False
    sealed_body_leaked_to_guard: bool = False
    chat_history_resume_authority: bool = False
    nonterminal_stop_allowed: bool = False
    ack_only_terminal: bool = False
    inactive_lease_waits_forever: bool = False
    stale_result_accepted: bool = False
    repeated_action_ignored: bool = False


@dataclass(frozen=True)
class Tick:
    """One lifecycle guard transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "load_current_run_ledger",
    "load_packet_lease_state",
    "observe_nonterminal_next_action",
    "write_guard_snapshot",
    "block_controller_stop",
    "request_manual_resume",
    "rehydrate_resume_from_ledger",
    "classify_wait_for_ack",
    "keep_ack_wait_nonterminal",
    "classify_wait_for_result",
    "keep_result_wait_nonterminal",
    "classify_inactive_lease_recovery",
    "quarantine_stale_result",
    "classify_repeated_action_stuck",
    "complete_final_closure",
    "authorize_terminal_stop",
)


def initial_state() -> State:
    return State()


class LifecycleGuardStep:
    name = "LifecycleGuardStep"
    reads = (
        "current_run_ledger",
        "packet_ledger",
        "lease_state",
        "router_next_action",
        "lifecycle_guard_history",
        "closure_state",
    )
    writes = (
        "lifecycle_guard_snapshot",
        "resume_rehydration_record",
        "wait_patrol_decision",
        "stale_result_quarantine",
        "terminal_stop_authority",
    )
    input_description = "Input x State: one lifecycle guard patrol or resume transition"
    output_description = "Set(Output x State): legal guard state or blocked hazard state"
    idempotency = "guard snapshots are metadata-only and cannot approve product work"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_lifecycle_guard_invariant", replace(state, status="blocked")),)
    if not state.current_run_ledger_loaded:
        return (Transition("load_current_run_ledger", replace(state, status="running", current_run_ledger_loaded=True)),)
    if not state.packet_ledger_loaded or not state.leases_loaded:
        return (Transition("load_packet_lease_state", replace(state, packet_ledger_loaded=True, leases_loaded=True)),)
    if not state.nonterminal_next_action_seen:
        return (Transition("observe_nonterminal_next_action", replace(state, nonterminal_next_action_seen=True)),)
    if not state.guard_snapshot_written:
        return (Transition("write_guard_snapshot", replace(state, guard_snapshot_written=True)),)
    if not state.controller_stop_blocked:
        return (Transition("block_controller_stop", replace(state, controller_stop_blocked=True)),)
    if not state.manual_resume_requested:
        return (Transition("request_manual_resume", replace(state, manual_resume_requested=True)),)
    if not state.resume_rehydrated_from_ledger:
        return (Transition("rehydrate_resume_from_ledger", replace(state, resume_rehydrated_from_ledger=True)),)
    if not state.wait_for_ack_classified:
        return (Transition("classify_wait_for_ack", replace(state, wait_for_ack_classified=True)),)
    if not state.ack_wait_nonterminal:
        return (Transition("keep_ack_wait_nonterminal", replace(state, ack_wait_nonterminal=True)),)
    if not state.wait_for_result_classified:
        return (Transition("classify_wait_for_result", replace(state, wait_for_result_classified=True)),)
    if not state.result_wait_nonterminal:
        return (Transition("keep_result_wait_nonterminal", replace(state, result_wait_nonterminal=True)),)
    if not state.inactive_lease_recovery_classified:
        return (Transition("classify_inactive_lease_recovery", replace(state, inactive_lease_recovery_classified=True)),)
    if not state.stale_result_quarantined:
        return (Transition("quarantine_stale_result", replace(state, stale_result_quarantined=True)),)
    if not state.repeated_action_stuck_classified:
        return (Transition("classify_repeated_action_stuck", replace(state, repeated_action_stuck_classified=True)),)
    if not state.final_closure_complete:
        return (Transition("complete_final_closure", replace(state, final_closure_complete=True)),)
    if not state.terminal_stop_allowed:
        return (Transition("authorize_terminal_stop", replace(state, terminal_stop_allowed=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.packet_ledger_loaded and not state.current_run_ledger_loaded:
        failures.append("packet ledger loaded before current-run ledger")
    if state.leases_loaded and not state.packet_ledger_loaded:
        failures.append("leases loaded before packet ledger")
    if state.nonterminal_next_action_seen and not state.leases_loaded:
        failures.append("next action observed before current packet/lease state")
    if state.guard_snapshot_written and not state.nonterminal_next_action_seen:
        failures.append("guard snapshot written before next action")
    if state.controller_stop_blocked and not state.guard_snapshot_written:
        failures.append("Controller stop blocked before guard snapshot")
    if state.resume_rehydrated_from_ledger and not (
        state.manual_resume_requested and state.current_run_ledger_loaded and state.packet_ledger_loaded and state.leases_loaded
    ):
        failures.append("resume did not rehydrate from current-run ledger, packet ledger, and leases")
    if state.ack_wait_nonterminal and not state.wait_for_ack_classified:
        failures.append("ACK wait marked nonterminal before classification")
    if state.result_wait_nonterminal and not state.wait_for_result_classified:
        failures.append("result wait marked nonterminal before classification")
    if state.terminal_stop_allowed and not state.final_closure_complete:
        failures.append("terminal stop allowed before final closure")
    if state.terminal_stop_allowed and not state.controller_stop_blocked:
        failures.append("terminal stop authority skipped prior nonterminal stop guard")
    if state.old_monitor_ui_required:
        failures.append("old monitor UI was required by the new guard")
    if state.old_router_authority_used:
        failures.append("old Router authority was used by the new guard")
    if state.sealed_body_leaked_to_guard:
        failures.append("guard leaked sealed body content")
    if state.chat_history_resume_authority:
        failures.append("resume used chat history as authority")
    if state.nonterminal_stop_allowed:
        failures.append("nonterminal next action allowed Controller stop")
    if state.ack_only_terminal:
        failures.append("ACK-only wait reached terminal completion")
    if state.inactive_lease_waits_forever:
        failures.append("inactive lease was treated as healthy indefinite wait")
    if state.stale_result_accepted:
        failures.append("stale or late result was accepted")
    if state.repeated_action_ignored:
        failures.append("repeated unchanged next action was not classified as stuck")
    return failures


def target_state() -> State:
    state = initial_state()
    for label in REQUIRED_SAFE_LABELS:
        transitions = {transition.label: transition for transition in next_safe_states(state)}
        state = transitions[label].state
    return state


def hazard_states() -> dict[str, State]:
    target = target_state()
    return {
        "old_monitor_ui_required": replace(target, old_monitor_ui_required=True),
        "old_router_authority_used": replace(target, old_router_authority_used=True),
        "sealed_body_leak": replace(target, sealed_body_leaked_to_guard=True),
        "chat_history_resume": replace(target, chat_history_resume_authority=True),
        "nonterminal_stop_allowed": replace(target, final_closure_complete=False, nonterminal_stop_allowed=True),
        "terminal_without_closure": replace(target, final_closure_complete=False, terminal_stop_allowed=True),
        "ack_only_terminal": replace(target, ack_only_terminal=True),
        "inactive_lease_waits_forever": replace(target, inactive_lease_recovery_classified=False, inactive_lease_waits_forever=True),
        "stale_result_accepted": replace(target, stale_result_quarantined=False, stale_result_accepted=True),
        "repeated_action_ignored": replace(target, repeated_action_stuck_classified=False, repeated_action_ignored=True),
    }


def is_success(state: State) -> bool:
    return state.status == "complete" and state.terminal_stop_allowed and not invariant_failures(state)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"complete", "blocked"}


def state_summary(state: State) -> dict[str, bool | str]:
    return dict(state.__dict__)


def build_workflow() -> Workflow:
    return Workflow(blocks=(LifecycleGuardStep(),), name=MODEL_ID)


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "new_flowpilot_lifecycle_guard_order_and_authority",
        "The new runtime guard must block nonterminal exit, rehydrate resume from current-run files, classify wait/recovery branches, and allow terminal return only after final closure.",
        _invariant,
    ),
)
EXTERNAL_INPUTS = (Tick(),)
