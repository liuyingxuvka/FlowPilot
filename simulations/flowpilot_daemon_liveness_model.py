"""FlowGuard model for FlowPilot daemon heartbeat liveness handoff.

This model covers the small policy boundary where the monitor reads daemon
heartbeat age but must not decide restart by timestamp alone. The monitor may
only report ``ok`` inside the heartbeat grace window or ``check_liveness`` after
the window. The Controller owns the real process/lock/status liveness check and
recovers only when that check proves the daemon is dead.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


HEARTBEAT_CHECK_SECONDS = 5


@dataclass(frozen=True)
class Tick:
    """One monitor/controller daemon liveness step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    lifecycle: str = "active"  # active | terminal
    daemon_process: str = "alive"  # alive | dead
    heartbeat_age_seconds: int = 0
    monitor_status: str = "unread"  # unread | ok | check_liveness | repair_or_restart
    controller_liveness_checked: bool = False
    controller_decision: str = "none"  # none | attach | recover
    second_writer_started: bool = False
    next_action_allowed: bool = False


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


class DaemonLivenessStep:
    """Input x State -> Set(Output x State) for daemon liveness handoff."""

    name = "DaemonLivenessStep"
    input_description = "one daemon heartbeat monitor/controller liveness step"
    output_description = "monitor status, controller liveness check, or recovery transition"
    reads = ("runtime/router_daemon.lock", "runtime/router_daemon_status.json")
    writes = ("foreground monitor status", "controller daemon recovery decision")
    idempotency = "Controller may attach or recover current-run daemon but must not start a second live writer."

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for label, new_state in next_states(state):
            yield FunctionResult(output=Action(label), new_state=new_state, label=label)


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    if state.lifecycle == "terminal":
        return ()

    if state.monitor_status == "unread":
        return (
            (
                "monitor_reports_ok_inside_five_second_window",
                _step(
                    state,
                    daemon_process="alive",
                    heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS,
                    monitor_status="ok",
                    next_action_allowed=True,
                ),
            ),
            (
                "monitor_reports_check_liveness_after_five_second_window",
                _step(
                    state,
                    daemon_process="alive",
                    heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
                    monitor_status="check_liveness",
                ),
            ),
            (
                "monitor_reports_check_liveness_for_dead_daemon_after_window",
                _step(
                    state,
                    daemon_process="dead",
                    heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
                    monitor_status="check_liveness",
                ),
            ),
        )

    if state.monitor_status == "check_liveness" and not state.controller_liveness_checked:
        if state.daemon_process == "alive":
            return (
                (
                    "controller_attaches_after_liveness_check_finds_alive_daemon",
                    _step(
                        state,
                        controller_liveness_checked=True,
                        controller_decision="attach",
                        next_action_allowed=True,
                    ),
                ),
            )
        return (
            (
                "controller_recovers_after_liveness_check_finds_dead_daemon",
                _step(
                    state,
                    daemon_process="alive",
                    controller_liveness_checked=True,
                    controller_decision="recover",
                    next_action_allowed=True,
                ),
            ),
        )

    if state.next_action_allowed:
        return (("terminal_after_safe_liveness_decision", _step(state, lifecycle="terminal")),)

    return ()


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    heartbeat_delayed = state.heartbeat_age_seconds > HEARTBEAT_CHECK_SECONDS

    if heartbeat_delayed and state.monitor_status == "ok":
        failures.append("monitor reported ok after the five-second heartbeat window")
    if heartbeat_delayed and state.monitor_status == "repair_or_restart" and not state.controller_liveness_checked:
        failures.append("monitor decided recovery before Controller liveness check")
    if heartbeat_delayed and state.next_action_allowed and not state.controller_liveness_checked:
        failures.append("Controller continued after delayed heartbeat without liveness check")
    if state.monitor_status == "check_liveness" and state.next_action_allowed and not state.controller_liveness_checked:
        failures.append("check_liveness was treated as final without Controller liveness check")
    if (
        state.controller_liveness_checked
        and state.daemon_process == "dead"
        and state.controller_decision != "recover"
    ):
        failures.append("Controller found dead daemon without recovering current run daemon")
    if state.second_writer_started:
        failures.append("Controller recovery started a second live Router writer")

    return failures


def _invariant(name: str, expected: str) -> Invariant:
    def check(state: State, trace) -> InvariantResult:
        del trace
        failures = invariant_failures(state)
        if expected in failures:
            return InvariantResult.fail(expected)
        return InvariantResult.pass_()

    return Invariant(name=name, description=expected, predicate=check)


INVARIANTS = (
    _invariant("freshness_window_controls_ok_status", "monitor reported ok after the five-second heartbeat window"),
    _invariant("monitor_does_not_decide_recovery", "monitor decided recovery before Controller liveness check"),
    _invariant("controller_checks_delayed_heartbeat", "Controller continued after delayed heartbeat without liveness check"),
    _invariant("check_liveness_is_not_final", "check_liveness was treated as final without Controller liveness check"),
    _invariant("dead_daemon_recovered_after_check", "Controller found dead daemon without recovering current run daemon"),
    _invariant("recovery_preserves_single_writer", "Controller recovery started a second live Router writer"),
)


HAZARD_STATES = {
    "delayed_heartbeat_reported_ok": replace(
        initial_state(),
        heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
        monitor_status="ok",
        next_action_allowed=True,
    ),
    "monitor_decides_restart_from_timestamp": replace(
        initial_state(),
        heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
        monitor_status="repair_or_restart",
        next_action_allowed=True,
    ),
    "controller_skips_liveness_check": replace(
        initial_state(),
        heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
        monitor_status="check_liveness",
        next_action_allowed=True,
    ),
    "dead_daemon_left_dead_after_check": replace(
        initial_state(),
        daemon_process="dead",
        heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
        monitor_status="check_liveness",
        controller_liveness_checked=True,
        controller_decision="attach",
        next_action_allowed=True,
    ),
    "recovery_starts_second_writer": replace(
        initial_state(),
        daemon_process="alive",
        heartbeat_age_seconds=HEARTBEAT_CHECK_SECONDS + 1,
        monitor_status="check_liveness",
        controller_liveness_checked=True,
        controller_decision="recover",
        second_writer_started=True,
        next_action_allowed=True,
    ),
}


def build_workflow() -> Workflow:
    return Workflow((DaemonLivenessStep(),), name="flowpilot_daemon_liveness")


def is_terminal(state: State) -> bool:
    return state.lifecycle == "terminal"


def is_success(state: State) -> bool:
    return state.lifecycle == "terminal"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 4


__all__ = [
    "EXTERNAL_INPUTS",
    "HAZARD_STATES",
    "HEARTBEAT_CHECK_SECONDS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "State",
    "Tick",
    "build_workflow",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
