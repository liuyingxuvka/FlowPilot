"""FlowGuard model for FlowPilot persistent Router daemon control.

Risk intent brief:
- Prevent FlowPilot from stalling when a role writes the expected ACK/report
  file after Controller has stopped at an ordinary wait boundary.
- Preserve the existing authority split: Router decides route state,
  Controller executes host actions from a durable checklist, and roles only
  write mailbox evidence.
- Model-critical durable state: daemon lock/status, one-second daemon tick,
  mailbox evidence, ACK consumption, Controller action ledger entries,
  Controller receipts, heartbeat/manual resume recovery, role cohort liveness,
  and terminal cleanup.
- Adversarial branches include formal startup skipping or failing daemon
  launch before Controller core load, no daemon at a wait, duplicate Router
  writers, duplicate ACK observation, Router marking Controller work done
  without a receipt, Controller acting as the normal Router metronome,
  Controller stopping at ordinary waits, foreground Controller ending while a
  live daemon-owned role wait is active, foreground Controller ending while
  the daemon is live but no Controller action is ready, heartbeat starting a
  second live daemon, and terminal stop leaving daemon/Controller/roles active.
- Hard invariants: formal startup must start a live one-second Router daemon
  before Controller core loads; active ordinary waits have a live daemon; one
  daemon writer owns a run; mailbox evidence is consumed at most once;
  Controller-required work is done only with a Controller receipt; receipt
  reconciliation must also advance the matching Router-owned internal fact so
  the same Controller action is not reissued forever; Controller follows the
  daemon-owned ledger instead of manually ticking the Router during normal
  runtime; Controller stays attached to the ledger during all nonterminal
  daemon-live runtime, processes pending executable Controller actions, and
  keeps a foreground standby loop active during ordinary daemon-owned role
  waits;
  heartbeat restarts only dead/stale daemon state; and terminal stop disables
  daemon, Controller, heartbeat, roles, and route work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One one-second daemon/controller/recovery tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    lifecycle: str = "new"  # new | active | terminal
    formal_startup_started: bool = False
    startup_daemon_step_completed: bool = False
    startup_daemon_failed: bool = False
    daemon_mode_enabled: bool = False
    daemon_alive: bool = False
    daemon_lock_state: str = "none"  # none | live | stale | duplicate
    daemon_writer_count: int = 0
    daemon_tick_seconds: int = 0
    controller_core_loaded: bool = False
    controller_attached: bool = False
    controller_called_router_next_as_metronome: bool = False
    controller_finaled_at_wait: bool = False
    foreground_standby_active: bool = False
    foreground_standby_polling_daemon_status: bool = False
    foreground_standby_polling_action_ledger: bool = False
    foreground_standby_timeout_count: int = 0
    foreground_controller_ended_turn_while_daemon_waiting: bool = False
    foreground_controller_ended_while_controller_action_pending: bool = False
    foreground_controller_ended_while_daemon_active_no_action: bool = False
    roles_live: bool = False
    heartbeat_active: bool = False
    current_wait: str = "none"  # none | ack | report | controller_receipt | user | terminal
    mailbox_wait_tick_observed: bool = False
    mailbox_evidence_present: bool = False
    mailbox_evidence_valid: bool = True
    mailbox_evidence_consumed: bool = False
    mailbox_consumption_count: int = 0
    router_can_continue_after_evidence: bool = False
    controller_action_pending: bool = False
    controller_action_ready: bool = False
    controller_action_done: bool = False
    controller_receipt_present: bool = False
    controller_receipt_valid: bool = True
    controller_marked_done_without_receipt: bool = False
    controller_rescanned_after_receipt: bool = False
    router_internal_action_fact_current: bool = False
    router_internal_fact_updated_from_receipt: bool = False
    router_cleared_pending_without_internal_fact: bool = False
    same_controller_action_reissue_count: int = 0
    heartbeat_woke: bool = False
    heartbeat_started_second_daemon: bool = False
    heartbeat_restarted_dead_daemon: bool = False
    heartbeat_restored_controller: bool = False
    heartbeat_restored_roles: bool = False
    stop_requested: bool = False
    route_work_allowed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


class PersistentRouterDaemonStep:
    """Model one persistent Router/Controller tick.

    Input x State -> Set(Output x State)
    reads: daemon lock/status, router state, mailbox evidence, controller
    action ledger, controller receipts, heartbeat wake event, role cohort
    writes: daemon status, consumed mailbox evidence, controller actions,
    controller receipts, recovery records, terminal lifecycle
    idempotency: repeated ticks over the same durable evidence do not duplicate
    consumption or action completion
    """

    name = "PersistentRouterDaemonStep"
    input_description = "one-second persistent Router daemon tick"
    output_description = "one daemon, controller, or lifecycle transition"
    reads = (
        "router_state",
        "daemon_lock",
        "mailbox",
        "controller_action_ledger",
        "controller_receipts",
        "heartbeat_state",
        "crew_memory",
    )
    writes = (
        "daemon_status",
        "controller_action_ledger",
        "controller_receipts",
        "return_event_ledger",
        "lifecycle_state",
        "recovery_records",
    )
    idempotency = "mailbox evidence and controller receipts are keyed and consumed once"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.lifecycle == "terminal":
        return

    if state.lifecycle == "new":
        yield Transition(
            "formal_startup_starts_builtin_router_daemon",
            _step(
                state,
                lifecycle="active",
                formal_startup_started=True,
                startup_daemon_step_completed=True,
                daemon_mode_enabled=True,
                daemon_alive=True,
                daemon_lock_state="live",
                daemon_writer_count=1,
                daemon_tick_seconds=1,
                roles_live=True,
                heartbeat_active=True,
            ),
        )
        return

    if state.stop_requested:
        yield Transition(
            "terminal_stop_reconciles_daemon_controller_roles",
            _step(
                state,
                lifecycle="terminal",
                daemon_alive=False,
                daemon_lock_state="none",
                daemon_writer_count=0,
                controller_core_loaded=False,
                controller_attached=False,
                foreground_standby_active=False,
                foreground_standby_polling_daemon_status=False,
                foreground_standby_polling_action_ledger=False,
                roles_live=False,
                heartbeat_active=False,
                current_wait="terminal",
                controller_action_pending=False,
                controller_action_ready=False,
                route_work_allowed=False,
            ),
        )
        return

    if not state.controller_core_loaded:
        yield Transition(
            "controller_core_loaded_after_builtin_daemon_start",
            _step(
                state,
                controller_core_loaded=True,
                controller_attached=True,
                route_work_allowed=True,
            ),
        )
        return

    if (
        state.current_wait == "none"
        and not state.controller_action_pending
        and not state.router_internal_action_fact_current
    ):
        yield Transition(
            "router_issues_controller_action_to_ledger",
            _step(
                state,
                current_wait="controller_receipt",
                controller_action_pending=True,
                controller_action_ready=True,
                controller_action_done=False,
                controller_receipt_present=False,
                controller_rescanned_after_receipt=False,
                same_controller_action_reissue_count=state.same_controller_action_reissue_count + 1,
                foreground_standby_active=False,
            ),
        )
        yield Transition(
            "user_requests_terminal_stop",
            _step(state, stop_requested=True),
        )
        return

    if (
        state.current_wait == "none"
        and not state.controller_action_pending
        and state.router_internal_action_fact_current
    ):
        yield Transition(
            "router_enters_ack_wait_owned_by_daemon",
            _step(
                state,
                current_wait="ack",
                foreground_standby_active=True,
                foreground_standby_polling_daemon_status=True,
                foreground_standby_polling_action_ledger=True,
            ),
        )
        yield Transition(
            "user_requests_terminal_stop",
            _step(state, stop_requested=True),
        )
        return

    if state.controller_action_pending and state.controller_action_ready and not state.controller_receipt_present:
        yield Transition(
            "controller_executes_action_and_writes_receipt",
            _step(
                state,
                controller_receipt_present=True,
                controller_receipt_valid=True,
            ),
        )
        return

    if state.controller_action_pending and state.controller_receipt_present and not state.controller_action_done:
        yield Transition(
            "router_reconciles_controller_receipt_updates_router_fact_and_requires_rescan",
            _step(
                state,
                controller_action_done=True,
                controller_action_pending=False,
                controller_action_ready=False,
                current_wait="none",
                controller_rescanned_after_receipt=True,
                router_internal_action_fact_current=True,
                router_internal_fact_updated_from_receipt=True,
                foreground_standby_active=False,
            ),
        )
        return

    if state.current_wait in {"ack", "report"} and not state.mailbox_evidence_present:
        if not state.mailbox_wait_tick_observed:
            yield Transition(
                "daemon_wait_tick_keeps_checking_mailbox",
                _step(state, mailbox_wait_tick_observed=True),
            )
        if state.foreground_standby_active and not state.mailbox_wait_tick_observed:
            yield Transition(
                "foreground_controller_standby_poll_tick_keeps_turn_open",
                _step(
                    state,
                    mailbox_wait_tick_observed=True,
                    foreground_standby_timeout_count=state.foreground_standby_timeout_count + 1,
                ),
            )
        if state.foreground_standby_active and state.foreground_standby_timeout_count == 0:
            yield Transition(
                "foreground_controller_bounded_timeout_reenters_standby",
                _step(state, foreground_standby_timeout_count=state.foreground_standby_timeout_count + 1),
            )
        yield Transition(
            "role_writes_expected_mailbox_evidence",
            _step(state, mailbox_evidence_present=True, mailbox_evidence_valid=True),
        )
        yield Transition(
            "heartbeat_wakes_and_finds_live_daemon",
            _step(state, heartbeat_woke=True),
        )
        yield Transition(
            "user_requests_terminal_stop",
            _step(state, stop_requested=True),
        )
        return

    if (
        state.current_wait in {"ack", "report"}
        and state.mailbox_evidence_present
        and state.mailbox_evidence_valid
        and not state.mailbox_evidence_consumed
    ):
        yield Transition(
            "daemon_consumes_mailbox_evidence_once",
            _step(
                state,
                mailbox_evidence_consumed=True,
                mailbox_consumption_count=state.mailbox_consumption_count + 1,
                router_can_continue_after_evidence=True,
                current_wait="none",
                mailbox_wait_tick_observed=False,
                foreground_standby_active=False,
            ),
        )
        return

    if state.mailbox_evidence_consumed and state.router_can_continue_after_evidence:
        yield Transition(
            "daemon_continues_after_consumed_evidence",
            _step(
                state,
                router_can_continue_after_evidence=False,
                mailbox_evidence_present=False,
                mailbox_evidence_consumed=False,
                stop_requested=True,
            ),
        )
        return


def hazard_states() -> dict[str, State]:
    safe_active = State(
        lifecycle="active",
        formal_startup_started=True,
        startup_daemon_step_completed=True,
        daemon_mode_enabled=True,
        daemon_alive=True,
        daemon_lock_state="live",
        daemon_writer_count=1,
        daemon_tick_seconds=1,
        controller_core_loaded=True,
        controller_attached=True,
        roles_live=True,
        heartbeat_active=True,
        route_work_allowed=True,
    )
    return {
        "ack_wait_without_daemon": replace(
            safe_active,
            daemon_alive=False,
            daemon_lock_state="none",
            daemon_writer_count=0,
            current_wait="ack",
            mailbox_evidence_present=True,
        ),
        "duplicate_router_writers": replace(
            safe_active,
            daemon_writer_count=2,
            daemon_lock_state="duplicate",
        ),
        "duplicate_ack_consumption": replace(
            safe_active,
            current_wait="none",
            mailbox_evidence_consumed=True,
            mailbox_consumption_count=2,
        ),
        "controller_done_without_receipt": replace(
            safe_active,
            controller_action_pending=True,
            controller_action_done=True,
            controller_receipt_present=False,
            controller_marked_done_without_receipt=True,
        ),
        "controller_stopped_at_ordinary_wait": replace(
            safe_active,
            current_wait="ack",
            controller_attached=False,
            controller_finaled_at_wait=True,
        ),
        "foreground_controller_ended_during_live_daemon_wait": replace(
            safe_active,
            current_wait="report",
            foreground_standby_active=False,
            foreground_controller_ended_turn_while_daemon_waiting=True,
        ),
        "foreground_controller_ended_with_pending_controller_action": replace(
            safe_active,
            current_wait="controller_receipt",
            controller_action_pending=True,
            controller_action_ready=True,
            controller_receipt_present=False,
            foreground_controller_ended_while_controller_action_pending=True,
        ),
        "foreground_controller_ended_while_daemon_active_no_action": replace(
            safe_active,
            current_wait="none",
            controller_action_pending=False,
            controller_action_ready=False,
            controller_attached=False,
            foreground_controller_ended_while_daemon_active_no_action=True,
        ),
        "router_cleared_controller_receipt_without_internal_fact": replace(
            safe_active,
            current_wait="none",
            controller_action_done=True,
            controller_receipt_present=True,
            controller_rescanned_after_receipt=True,
            router_internal_action_fact_current=False,
            router_internal_fact_updated_from_receipt=False,
            router_cleared_pending_without_internal_fact=True,
        ),
        "same_controller_action_reissued_after_done_receipt": replace(
            safe_active,
            current_wait="controller_receipt",
            controller_action_pending=True,
            controller_action_ready=True,
            controller_action_done=False,
            controller_receipt_present=True,
            router_internal_action_fact_current=False,
            same_controller_action_reissue_count=2,
        ),
        "controller_core_loaded_after_skipped_daemon_start": replace(
            safe_active,
            startup_daemon_step_completed=False,
            daemon_mode_enabled=False,
            daemon_alive=False,
            daemon_lock_state="none",
            daemon_writer_count=0,
        ),
        "formal_startup_continued_after_daemon_failure": replace(
            safe_active,
            startup_daemon_failed=True,
            startup_daemon_step_completed=False,
            daemon_mode_enabled=False,
            daemon_alive=False,
            daemon_lock_state="none",
            daemon_writer_count=0,
        ),
        "controller_used_router_next_as_metronome": replace(
            safe_active,
            controller_called_router_next_as_metronome=True,
        ),
        "heartbeat_started_second_live_daemon": replace(
            safe_active,
            heartbeat_woke=True,
            heartbeat_started_second_daemon=True,
            daemon_writer_count=2,
        ),
        "terminal_left_runtime_active": State(
            lifecycle="terminal",
            formal_startup_started=True,
            startup_daemon_step_completed=True,
            daemon_mode_enabled=True,
            daemon_alive=True,
            daemon_lock_state="live",
            daemon_writer_count=1,
            controller_core_loaded=True,
            controller_attached=True,
            roles_live=True,
            heartbeat_active=True,
            route_work_allowed=True,
            current_wait="ack",
        ),
    }


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    ordinary_wait = state.current_wait in {"ack", "report", "controller_receipt"}
    daemon_ready_for_controller = (
        state.startup_daemon_step_completed
        and state.daemon_mode_enabled
        and state.daemon_alive
        and state.daemon_lock_state == "live"
        and state.daemon_writer_count == 1
        and state.daemon_tick_seconds == 1
    )
    if state.lifecycle == "active" and state.controller_core_loaded and not daemon_ready_for_controller:
        failures.append("Controller core loaded before formal startup daemon was live")
    if state.startup_daemon_failed and (state.controller_core_loaded or state.route_work_allowed):
        failures.append("formal startup continued after Router daemon startup failure")
    if state.lifecycle == "active" and state.daemon_mode_enabled and ordinary_wait and not state.daemon_alive:
        failures.append("ordinary wait exists without a live Router daemon")
    if state.daemon_writer_count > 1 or state.daemon_lock_state == "duplicate":
        failures.append("multiple Router daemon writers exist for one run")
    if state.daemon_alive and state.daemon_tick_seconds != 1:
        failures.append("Router daemon tick is not fixed at one second")
    if state.controller_called_router_next_as_metronome:
        failures.append("Controller used diagnostic Router next/run-until-wait as the normal runtime metronome")
    if state.mailbox_consumption_count > 1:
        failures.append("mailbox evidence was consumed more than once")
    if state.controller_action_done and not state.controller_receipt_present:
        failures.append("Controller action was marked done without a Controller receipt")
    if (
        state.controller_action_done
        and state.controller_receipt_present
        and not state.router_internal_action_fact_current
    ) or state.router_cleared_pending_without_internal_fact:
        failures.append("Router cleared Controller receipt without updating Router-owned internal action fact")
    if state.same_controller_action_reissue_count > 1 and state.controller_receipt_present:
        failures.append("Router reissued the same Controller action after a done receipt because Router-owned fact stayed stale")
    if state.lifecycle == "active" and state.daemon_mode_enabled and state.controller_action_pending and state.controller_action_ready:
        if not state.controller_attached or state.foreground_controller_ended_while_controller_action_pending:
            failures.append("Foreground Controller ended while an executable Controller action was pending")
    if (
        state.lifecycle == "active"
        and state.daemon_mode_enabled
        and state.daemon_alive
        and state.controller_core_loaded
        and state.current_wait == "none"
        and not state.controller_action_pending
        and not state.stop_requested
    ):
        if not state.controller_attached or state.foreground_controller_ended_while_daemon_active_no_action:
            failures.append("Foreground Controller ended while the Router daemon was live and no Controller action was ready")
    if state.lifecycle == "active" and state.daemon_mode_enabled and state.current_wait in {"ack", "report"}:
        if not state.controller_attached or state.controller_finaled_at_wait:
            failures.append("Controller stopped at an ordinary daemon-owned wait")
        if not state.foreground_standby_active or state.foreground_controller_ended_turn_while_daemon_waiting:
            failures.append("Foreground Controller ended instead of staying in standby for a live daemon-owned role wait")
        if state.controller_called_router_next_as_metronome:
            failures.append("Foreground standby used diagnostic Router next/run-until-wait instead of daemon status and action ledger")
        if not state.foreground_standby_polling_daemon_status or not state.foreground_standby_polling_action_ledger:
            failures.append("Foreground standby did not poll daemon status and Controller action ledger")
    if state.heartbeat_started_second_daemon:
        failures.append("heartbeat started a second Router daemon while one was live")
    if state.lifecycle == "terminal":
        if (
            state.daemon_alive
            or state.controller_attached
            or state.roles_live
            or state.heartbeat_active
            or state.route_work_allowed
        ):
            failures.append("terminal lifecycle left daemon, Controller, roles, heartbeat, or route work active")
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
    _invariant("controller_core_requires_formal_daemon", "Controller core loaded before formal startup daemon was live"),
    _invariant("daemon_failure_blocks_formal_startup", "formal startup continued after Router daemon startup failure"),
    _invariant("ordinary_wait_has_live_daemon", "ordinary wait exists without a live Router daemon"),
    _invariant("single_router_writer", "multiple Router daemon writers exist for one run"),
    _invariant("fixed_one_second_tick", "Router daemon tick is not fixed at one second"),
    _invariant("controller_not_runtime_metronome", "Controller used diagnostic Router next/run-until-wait as the normal runtime metronome"),
    _invariant("mailbox_evidence_consumed_once", "mailbox evidence was consumed more than once"),
    _invariant("controller_done_requires_receipt", "Controller action was marked done without a Controller receipt"),
    _invariant("controller_receipt_updates_router_owned_fact", "Router cleared Controller receipt without updating Router-owned internal action fact"),
    _invariant("same_controller_action_not_reissued_after_receipt", "Router reissued the same Controller action after a done receipt because Router-owned fact stayed stale"),
    _invariant("foreground_controller_handles_pending_controller_action", "Foreground Controller ended while an executable Controller action was pending"),
    _invariant("foreground_controller_stays_attached_when_daemon_has_no_ready_action", "Foreground Controller ended while the Router daemon was live and no Controller action was ready"),
    _invariant("controller_stays_attached_at_ordinary_wait", "Controller stopped at an ordinary daemon-owned wait"),
    _invariant("foreground_controller_standby_keeps_turn_open", "Foreground Controller ended instead of staying in standby for a live daemon-owned role wait"),
    _invariant("foreground_standby_does_not_use_router_metronome", "Foreground standby used diagnostic Router next/run-until-wait instead of daemon status and action ledger"),
    _invariant("foreground_standby_polls_daemon_and_ledger", "Foreground standby did not poll daemon status and Controller action ledger"),
    _invariant("heartbeat_does_not_start_second_daemon", "heartbeat started a second Router daemon while one was live"),
    _invariant("terminal_cleanup_stops_runtime", "terminal lifecycle left daemon, Controller, roles, heartbeat, or route work active"),
)


def build_workflow() -> Workflow:
    return Workflow((PersistentRouterDaemonStep(),), name="flowpilot_persistent_router_daemon")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.lifecycle == "terminal"


def is_success(state: State) -> bool:
    return state.lifecycle == "terminal"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 12


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
    "next_safe_states",
    "next_states",
]
