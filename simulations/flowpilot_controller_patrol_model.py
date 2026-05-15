"""FlowGuard model for FlowPilot Controller patrol timer standby.

Risk Purpose Header:
This model uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to
review the Controller foreground keepalive patrol timer. It guards against the
bugs where a quiet Router daemon monitor lets Controller exit the chat, where
starting/restarting the patrol command is treated as completion, or where
`continue_patrol` does not tell Controller to rerun the command and wait for
the next output. Run with:

    python simulations/run_flowpilot_controller_patrol_checks.py --json-out simulations/flowpilot_controller_patrol_results.json

Risk intent brief:
- Prevent foreground Controller from ending while FlowPilot is still active and
  no ordinary Controller row is ready.
- Preserve the existing Router daemon monitor as the source of truth; the
  patrol timer is only a Controller-operated wait wrapper.
- Model-critical state: daemon liveness, existing monitor read, action ledger
  readiness, `continuous_controller_standby` status, patrol command output,
  anti-exit reminder, rerun-and-wait instruction, terminal allowance, and
  forbidden completion evidence.
- Adversarial branches include quiet monitor -> foreground close, command start
  -> completion, continue_patrol without waiting for the next output, patrol
  using a separate monitor, and Controller using router `next` as a metronome.
- Blindspot: this abstract model is not a concrete replay adapter for runtime
  JSON files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One Controller patrol decision step."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    lifecycle: str = "active"  # active | terminal | done
    daemon_live: bool = True
    foreground_required_mode: str = "watch_router_daemon"
    continuous_standby_visible: bool = False
    continuous_standby_status: str = "none"  # none | in_progress | complete
    ordinary_controller_work_ready: bool = False
    controller_action_ledger_processed: bool = False
    existing_monitor_read: bool = False
    separate_monitor_used: bool = False
    patrol_command_named_in_prompt: bool = False
    patrol_command_started: bool = False
    patrol_timer_elapsed: bool = False
    patrol_result: str = "none"  # none | continue_patrol | new_controller_work | terminal_return
    anti_exit_reminder: bool = False
    next_command_named: bool = False
    rerun_instruction: bool = False
    wait_next_output_instruction: bool = False
    command_start_marked_complete: bool = False
    command_restart_marked_complete: bool = False
    next_command_rerun_started: bool = False
    waiting_for_next_output: bool = False
    foreground_closed: bool = False
    controller_stop_allowed: bool = False
    router_next_used_as_metronome: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


class ControllerPatrolStep:
    """Model one Controller patrol timer transition.

    Input x State -> Set(Output x State)
    reads: router_daemon_status, controller_action_ledger,
    controller_receipts, foreground exit policy
    writes: Controller-visible patrol result only
    idempotency: repeated `continue_patrol` outputs restart the same command
    and keep `continuous_controller_standby` in progress.
    """

    name = "ControllerPatrolStep"
    input_description = "one Controller patrol timer or monitor decision"
    output_description = "one Controller-facing patrol instruction"
    reads = (
        "router_daemon_status",
        "controller_action_ledger",
        "controller_receipts",
        "foreground_exit_policy",
    )
    writes = ("controller_patrol_result",)
    idempotency = "continue_patrol reruns the same command and waits for next output"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.lifecycle in {"terminal", "done"}:
        return

    if not state.continuous_standby_visible:
        yield Transition(
            "controller_enters_continuous_standby",
            _step(
                state,
                continuous_standby_visible=True,
                continuous_standby_status="in_progress",
                patrol_command_named_in_prompt=True,
            ),
        )
        yield Transition(
            "controller_action_ready_without_patrol",
            _step(
                state,
                ordinary_controller_work_ready=True,
                foreground_required_mode="process_controller_action",
            ),
        )
        yield Transition(
            "terminal_state_exposed_before_patrol",
            _step(
                state,
                lifecycle="terminal",
                foreground_required_mode="terminal_return",
                controller_stop_allowed=True,
                patrol_result="terminal_return",
            ),
        )
        return

    if (
        state.ordinary_controller_work_ready
        and not state.controller_action_ledger_processed
        and (not state.patrol_command_started or state.patrol_result == "new_controller_work")
    ):
        yield Transition(
            "controller_processes_ready_action_ledger",
            _step(state, controller_action_ledger_processed=True, lifecycle="done"),
        )
        return

    if not state.patrol_command_started:
        yield Transition(
            "controller_runs_named_patrol_timer_command",
            _step(state, patrol_command_started=True),
        )
        return

    if not state.patrol_timer_elapsed:
        yield Transition(
            "patrol_timer_waits_requested_interval",
            _step(state, patrol_timer_elapsed=True),
        )
        yield Transition(
            "new_controller_work_arrives_while_timer_waits",
            _step(
                state,
                patrol_timer_elapsed=True,
                ordinary_controller_work_ready=True,
                foreground_required_mode="process_controller_action",
            ),
        )
        return

    if state.ordinary_controller_work_ready and state.patrol_result == "none":
        yield Transition(
            "patrol_returns_new_controller_work",
            _step(
                state,
                existing_monitor_read=True,
                patrol_result="new_controller_work",
                foreground_required_mode="process_controller_action",
            ),
        )
        return

    if not state.existing_monitor_read:
        yield Transition(
            "patrol_reads_existing_router_monitor",
            _step(state, existing_monitor_read=True),
        )
        return

    if state.patrol_result == "none":
        yield Transition(
            "patrol_returns_continue_with_anti_exit_rerun_and_wait",
            _step(
                state,
                patrol_result="continue_patrol",
                anti_exit_reminder=True,
                next_command_named=True,
                rerun_instruction=True,
                wait_next_output_instruction=True,
            ),
        )
        yield Transition(
            "patrol_returns_terminal_stop_allowed",
            _step(
                state,
                lifecycle="terminal",
                patrol_result="terminal_return",
                foreground_required_mode="terminal_return",
                controller_stop_allowed=True,
            ),
        )
        return

    if state.patrol_result == "continue_patrol" and not state.waiting_for_next_output:
        yield Transition(
            "controller_reruns_patrol_timer_and_waits_for_next_output",
            _step(
                state,
                next_command_rerun_started=True,
                waiting_for_next_output=True,
                lifecycle="done",
            ),
        )


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.separate_monitor_used:
        failures.append("patrol timer used a separate monitor instead of the existing daemon monitor")

    if state.router_next_used_as_metronome:
        failures.append("Controller used router next/apply/run-until-wait as the patrol metronome")

    if (
        state.daemon_live
        and state.foreground_required_mode == "watch_router_daemon"
        and state.lifecycle == "active"
        and state.foreground_closed
    ):
        failures.append("quiet monitor allowed Controller foreground exit")

    if state.command_start_marked_complete or state.command_restart_marked_complete:
        failures.append("patrol command start or restart was treated as standby completion")

    if state.continuous_standby_status == "complete" and not (
        state.patrol_result == "terminal_return" and state.controller_stop_allowed
    ):
        failures.append("continuous standby completed before terminal stop allowance")

    if state.patrol_result == "continue_patrol":
        if not state.anti_exit_reminder:
            failures.append("continue_patrol lacked anti-exit reminder")
        if not state.next_command_named:
            failures.append("continue_patrol did not name the next patrol command")
        if not state.rerun_instruction:
            failures.append("continue_patrol did not instruct Controller to rerun the patrol command")
        if not state.wait_next_output_instruction:
            failures.append("continue_patrol did not instruct Controller to wait for the next output")
        if state.continuous_standby_status != "in_progress":
            failures.append("continue_patrol did not keep continuous standby in progress")

    if state.next_command_rerun_started and not state.waiting_for_next_output:
        failures.append("Controller reran patrol command without waiting for next output")

    if state.patrol_result == "new_controller_work" and not state.ordinary_controller_work_ready:
        failures.append("patrol reported new Controller work when no action was ready")

    if state.patrol_result == "new_controller_work" and state.foreground_required_mode != "process_controller_action":
        failures.append("new Controller work did not switch foreground mode to process_controller_action")

    if state.controller_action_ledger_processed and not state.ordinary_controller_work_ready:
        failures.append("Controller processed action ledger without ready work")

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
    _invariant("patrol_uses_existing_monitor", "patrol timer used a separate monitor instead of the existing daemon monitor"),
    _invariant("patrol_does_not_use_router_next_metronome", "Controller used router next/apply/run-until-wait as the patrol metronome"),
    _invariant("quiet_monitor_cannot_close_foreground", "quiet monitor allowed Controller foreground exit"),
    _invariant("command_start_is_not_completion", "patrol command start or restart was treated as standby completion"),
    _invariant("standby_completion_requires_terminal_allowance", "continuous standby completed before terminal stop allowance"),
    _invariant("continue_patrol_has_anti_exit_reminder", "continue_patrol lacked anti-exit reminder"),
    _invariant("continue_patrol_names_next_command", "continue_patrol did not name the next patrol command"),
    _invariant("continue_patrol_instructs_rerun", "continue_patrol did not instruct Controller to rerun the patrol command"),
    _invariant("continue_patrol_instructs_wait_next_output", "continue_patrol did not instruct Controller to wait for the next output"),
    _invariant("continue_patrol_keeps_standby_in_progress", "continue_patrol did not keep continuous standby in progress"),
    _invariant("rerun_waits_for_next_output", "Controller reran patrol command without waiting for next output"),
    _invariant("new_work_requires_ready_action", "patrol reported new Controller work when no action was ready"),
    _invariant("new_work_switches_foreground_mode", "new Controller work did not switch foreground mode to process_controller_action"),
    _invariant("action_processing_requires_ready_work", "Controller processed action ledger without ready work"),
)


def hazard_states() -> dict[str, State]:
    base = State(
        continuous_standby_visible=True,
        continuous_standby_status="in_progress",
        patrol_command_named_in_prompt=True,
        patrol_command_started=True,
        patrol_timer_elapsed=True,
        existing_monitor_read=True,
    )
    return {
        "quiet_monitor_foreground_exit": replace(base, foreground_closed=True),
        "command_start_marked_complete": replace(base, command_start_marked_complete=True),
        "command_restart_marked_complete": replace(base, command_restart_marked_complete=True),
        "continue_patrol_without_anti_exit": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=False,
            next_command_named=True,
            rerun_instruction=True,
            wait_next_output_instruction=True,
        ),
        "continue_patrol_without_next_command": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=True,
            next_command_named=False,
            rerun_instruction=True,
            wait_next_output_instruction=True,
        ),
        "continue_patrol_without_rerun": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=True,
            next_command_named=True,
            rerun_instruction=False,
            wait_next_output_instruction=True,
        ),
        "continue_patrol_without_wait_next_output": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=True,
            next_command_named=True,
            rerun_instruction=True,
            wait_next_output_instruction=False,
        ),
        "continue_patrol_completes_standby": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=True,
            next_command_named=True,
            rerun_instruction=True,
            wait_next_output_instruction=True,
            continuous_standby_status="complete",
        ),
        "rerun_without_waiting": replace(
            base,
            patrol_result="continue_patrol",
            anti_exit_reminder=True,
            next_command_named=True,
            rerun_instruction=True,
            wait_next_output_instruction=True,
            next_command_rerun_started=True,
            waiting_for_next_output=False,
        ),
        "separate_monitor_used": replace(base, separate_monitor_used=True),
        "router_next_used_as_metronome": replace(base, router_next_used_as_metronome=True),
    }


def build_workflow() -> Workflow:
    return Workflow((ControllerPatrolStep(),), name="flowpilot_controller_patrol")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.lifecycle in {"terminal", "done"}


def is_success(state: State) -> bool:
    return state.lifecycle == "done" or (
        state.lifecycle == "terminal"
        and state.patrol_result == "terminal_return"
        and state.controller_stop_allowed
    )


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 8


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "Action",
    "State",
    "Tick",
    "Transition",
    "build_workflow",
    "hazard_states",
    "initial_state",
    "invariant_failures",
    "is_success",
    "is_terminal",
    "next_states",
]
