"""FlowGuard model for stop/cancel, host liveness, and orphan evidence recovery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


MODEL_ID = "flowpilot_stop_host_orphan_recovery"
MAX_SEQUENCE_LENGTH = 16


@dataclass(frozen=True)
class State:
    status: str = "new"
    current_run_loaded: bool = False
    packet_and_lease_loaded: bool = False
    explicit_stop_recorded: bool = False
    explicit_cancel_recorded: bool = False
    terminal_leases_closed: bool = False
    terminal_packets_marked: bool = False
    terminal_preflight_allowed: bool = False
    host_liveness_bridge_written: bool = False
    positive_liveness_preserves_wait: bool = False
    failure_liveness_overrides_progress: bool = False
    no_output_liveness_recovery: bool = False
    orphan_runner_summary_seen: bool = False
    orphan_recovery_duty: bool = False
    orphan_not_auto_accepted: bool = False
    new_work_after_terminal_allowed: bool = False
    terminal_without_ledger_status: bool = False
    stale_progress_overrode_host_failure: bool = False
    completed_without_result_treated_terminal: bool = False
    orphan_evidence_auto_accepted: bool = False
    orphan_evidence_ignored: bool = False


@dataclass(frozen=True)
class Tick:
    """One control-plane recovery transition."""


@dataclass(frozen=True)
class Action:
    label: str


class Transition(NamedTuple):
    label: str
    state: State


REQUIRED_SAFE_LABELS = (
    "load_current_run",
    "load_packet_and_lease",
    "record_explicit_stop_or_cancel",
    "close_terminal_leases",
    "mark_terminal_packets",
    "allow_terminal_preflight",
    "write_host_liveness_bridge",
    "preserve_positive_liveness_wait",
    "override_progress_with_host_failure",
    "route_no_output_to_recovery",
    "detect_orphan_runner_summary",
    "route_orphan_recovery_duty",
    "block_orphan_auto_accept",
)


def initial_state() -> State:
    return State()


class StopHostOrphanStep:
    name = "StopHostOrphanStep"
    reads = (
        "current_run_ledger",
        "lifecycle_state",
        "packet_state",
        "lease_state",
        "host_liveness_report",
        "runner_summary",
    )
    writes = (
        "terminal_lifecycle",
        "lease_closure",
        "packet_terminal_status",
        "lifecycle_guard",
        "foreground_duty",
        "host_liveness_report_ledger",
        "orphan_evidence_ledger",
    )
    input_description = "Input x State: one controller patrol, stop/cancel, or host evidence observation"
    output_description = "Set(Output x State): legal terminal/recovery state or blocked hazard state"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(output=Action(transition.label), new_state=transition.state, label=transition.label)


def next_safe_states(state: State) -> tuple[Transition, ...]:
    if state.status in {"blocked", "complete"}:
        return ()
    failures = invariant_failures(state)
    if failures:
        return (Transition("blocked_on_stop_host_orphan_invariant", replace(state, status="blocked")),)
    if not state.current_run_loaded:
        return (Transition("load_current_run", replace(state, current_run_loaded=True, status="running")),)
    if not state.packet_and_lease_loaded:
        return (Transition("load_packet_and_lease", replace(state, packet_and_lease_loaded=True)),)
    if not (state.explicit_stop_recorded or state.explicit_cancel_recorded):
        return (
            Transition(
                "record_explicit_stop_or_cancel",
                replace(state, explicit_stop_recorded=True, explicit_cancel_recorded=True),
            ),
        )
    if not state.terminal_leases_closed:
        return (Transition("close_terminal_leases", replace(state, terminal_leases_closed=True)),)
    if not state.terminal_packets_marked:
        return (Transition("mark_terminal_packets", replace(state, terminal_packets_marked=True)),)
    if not state.terminal_preflight_allowed:
        return (Transition("allow_terminal_preflight", replace(state, terminal_preflight_allowed=True)),)
    if not state.host_liveness_bridge_written:
        return (Transition("write_host_liveness_bridge", replace(state, host_liveness_bridge_written=True)),)
    if not state.positive_liveness_preserves_wait:
        return (Transition("preserve_positive_liveness_wait", replace(state, positive_liveness_preserves_wait=True)),)
    if not state.failure_liveness_overrides_progress:
        return (Transition("override_progress_with_host_failure", replace(state, failure_liveness_overrides_progress=True)),)
    if not state.no_output_liveness_recovery:
        return (Transition("route_no_output_to_recovery", replace(state, no_output_liveness_recovery=True)),)
    if not state.orphan_runner_summary_seen:
        return (Transition("detect_orphan_runner_summary", replace(state, orphan_runner_summary_seen=True)),)
    if not state.orphan_recovery_duty:
        return (Transition("route_orphan_recovery_duty", replace(state, orphan_recovery_duty=True)),)
    if not state.orphan_not_auto_accepted:
        return (Transition("block_orphan_auto_accept", replace(state, orphan_not_auto_accepted=True, status="complete")),)
    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.packet_and_lease_loaded and not state.current_run_loaded:
        failures.append("packet/lease loaded before current run")
    if (state.explicit_stop_recorded or state.explicit_cancel_recorded) and not state.packet_and_lease_loaded:
        failures.append("terminal lifecycle recorded before packet and lease state")
    if state.terminal_leases_closed and not (state.explicit_stop_recorded or state.explicit_cancel_recorded):
        failures.append("terminal leases closed without explicit stop/cancel")
    if state.terminal_packets_marked and not state.terminal_leases_closed:
        failures.append("terminal packets marked before active leases closed")
    if state.terminal_preflight_allowed and not (state.terminal_packets_marked and state.terminal_leases_closed):
        failures.append("terminal preflight allowed before stop/cancel cleanup")
    if state.host_liveness_bridge_written and not state.packet_and_lease_loaded:
        failures.append("host liveness recorded before packet and lease state")
    if state.failure_liveness_overrides_progress and not state.host_liveness_bridge_written:
        failures.append("host failure override claimed before host bridge")
    if state.no_output_liveness_recovery and not state.host_liveness_bridge_written:
        failures.append("no-output recovery claimed before host bridge")
    if state.orphan_runner_summary_seen and not state.packet_and_lease_loaded:
        failures.append("orphan runner summary checked before packet state")
    if state.orphan_recovery_duty and not state.orphan_runner_summary_seen:
        failures.append("orphan recovery duty emitted before orphan evidence was detected")
    if state.orphan_not_auto_accepted and not state.orphan_recovery_duty:
        failures.append("orphan auto-accept block claimed before recovery duty")
    if state.new_work_after_terminal_allowed:
        failures.append("new work was allowed after explicit terminal lifecycle")
    if state.terminal_without_ledger_status:
        failures.append("terminal return was allowed without terminal lifecycle ledger status")
    if state.stale_progress_overrode_host_failure:
        failures.append("older progress overrode newer host failure")
    if state.completed_without_result_treated_terminal:
        failures.append("completed_without_result was treated as terminal completion")
    if state.orphan_evidence_auto_accepted:
        failures.append("orphan evidence auto-accepted a packet")
    if state.orphan_evidence_ignored:
        failures.append("orphan evidence was ignored instead of routed to recovery")
    return failures


def _invariant(state: State, trace: object) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        "stop_host_orphan_recovery_invariants",
        "Explicit stop/cancel is terminal, host liveness is current authority, orphan evidence routes recovery.",
        _invariant,
    ),
)


def terminal_predicate(_input_obj: Tick, state: State, _trace: object) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete" and not invariant_failures(state)


def target_state() -> State:
    state = initial_state()
    for _ in range(MAX_SEQUENCE_LENGTH):
        transitions = next_safe_states(state)
        if not transitions:
            break
        state = transitions[0].state
    return state


def hazard_states() -> dict[str, State]:
    base = target_state()
    return {
        "new_work_after_terminal_allowed": replace(base, new_work_after_terminal_allowed=True),
        "terminal_without_ledger_status": replace(base, terminal_without_ledger_status=True),
        "stale_progress_overrode_host_failure": replace(base, stale_progress_overrode_host_failure=True),
        "completed_without_result_treated_terminal": replace(base, completed_without_result_treated_terminal=True),
        "orphan_evidence_auto_accepted": replace(base, orphan_evidence_auto_accepted=True),
        "orphan_evidence_ignored": replace(base, orphan_evidence_ignored=True),
    }


def state_summary(state: State) -> dict[str, bool | str]:
    return {
        "status": state.status,
        "terminal_preflight_allowed": state.terminal_preflight_allowed,
        "host_liveness_bridge_written": state.host_liveness_bridge_written,
        "failure_liveness_overrides_progress": state.failure_liveness_overrides_progress,
        "orphan_recovery_duty": state.orphan_recovery_duty,
        "orphan_not_auto_accepted": state.orphan_not_auto_accepted,
    }


def build_workflow() -> Workflow:
    return Workflow(blocks=(StopHostOrphanStep(),), name=MODEL_ID)


EXTERNAL_INPUTS = (Tick(),)
