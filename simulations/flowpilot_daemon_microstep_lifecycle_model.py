"""FlowGuard model for FlowPilot daemon lifecycle microsteps.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  fine-grained control-plane order inside each Router daemon tick.
- Guards against the class of bugs where a lifecycle phase looks complete in
  one table or receipt, but the daemon fails to read, reconcile, clear, sync,
  schedule, and write all authoritative tables before returning work.
- Covers the full FlowPilot control lifecycle: startup bootloader rows, normal
  Controller action receipts, role-output waits, external event waits,
  Controller repair receipts, and terminal cleanup.
- Companion check command:
  `python simulations/run_flowpilot_daemon_microstep_lifecycle_checks.py`.

Risk intent brief:
- Protected harm: FlowPilot repeats old work, skips a required cleanup, opens
  the next wait from stale state, or reports terminal status while durable
  control-plane state is still inconsistent.
- Model-critical state: daemon status, bootstrap/run state, Router scheduler
  ledger, Controller action ledger, Controller receipts, role-output/event
  evidence, repair rows, terminal lifecycle records, and writer ownership.
- Adversarial branches: computing next before all required reads, stale startup
  pending_action after a done receipt, stale Router-owned facts after normal
  Controller receipts, role output left only in durable storage, external event
  waits closed by the wrong owner or not closed, repair blockers written before
  reading repair receipts, and terminal status written before runtime cleanup.
- Hard invariants: every daemon tick follows read -> reconcile -> sync
  authority state -> clear pending/wait -> schedule-or-barrier -> write tables
  -> write daemon status; Router writes Router tables, Controller writes only
  receipts/check-offs, and no same action can be reissued after its done
  evidence has been consumed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


STARTUP_RECEIPT_ADVANCES = "startup_receipt_advances"
ROUTE_RECEIPT_ADVANCES = "route_receipt_advances"
ROLE_OUTPUT_ADVANCES = "role_output_advances"
EXTERNAL_EVENT_ADVANCES = "external_event_advances"
REPAIR_RECEIPT_ADVANCES = "repair_receipt_advances"
TERMINAL_CLEANUP_ADVANCES = "terminal_cleanup_advances"

COMPUTE_NEXT_BEFORE_REQUIRED_READS = "compute_next_before_required_reads"
STARTUP_RECEIPT_LEAVES_PENDING = "startup_receipt_leaves_pending"
ROUTE_RECEIPT_LEAVES_ROUTER_FACT_STALE = "route_receipt_leaves_router_fact_stale"
ROLE_OUTPUT_LEFT_DURABLE_ONLY = "role_output_left_durable_only"
EXTERNAL_EVENT_WAIT_NOT_ROUTER_CLOSED = "external_event_wait_not_router_closed"
REPAIR_BLOCKER_BEFORE_RECEIPT_READ = "repair_blocker_before_receipt_read"
TERMINAL_STATUS_BEFORE_CLEANUP = "terminal_status_before_cleanup"
PENDING_CLEARED_BEFORE_AUTHORITY_SYNC = "pending_cleared_before_authority_sync"
CONTROLLER_WRITES_ROUTER_TABLE = "controller_writes_router_table"
DAEMON_STATUS_FROM_STALE_SUMMARY = "daemon_status_from_stale_summary"

VALID_SCENARIOS = (
    STARTUP_RECEIPT_ADVANCES,
    ROUTE_RECEIPT_ADVANCES,
    ROLE_OUTPUT_ADVANCES,
    EXTERNAL_EVENT_ADVANCES,
    REPAIR_RECEIPT_ADVANCES,
    TERMINAL_CLEANUP_ADVANCES,
)

NEGATIVE_SCENARIOS = (
    COMPUTE_NEXT_BEFORE_REQUIRED_READS,
    STARTUP_RECEIPT_LEAVES_PENDING,
    ROUTE_RECEIPT_LEAVES_ROUTER_FACT_STALE,
    ROLE_OUTPUT_LEFT_DURABLE_ONLY,
    EXTERNAL_EVENT_WAIT_NOT_ROUTER_CLOSED,
    REPAIR_BLOCKER_BEFORE_RECEIPT_READ,
    TERMINAL_STATUS_BEFORE_CLEANUP,
    PENDING_CLEARED_BEFORE_AUTHORITY_SYNC,
    CONTROLLER_WRITES_ROUTER_TABLE,
    DAEMON_STATUS_FROM_STALE_SUMMARY,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One daemon microstep lifecycle review tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"
    phase: str = "none"  # startup | route | role_wait | external_event | repair | terminal

    read_daemon_status: bool = False
    read_authority_state: bool = False
    read_router_scheduler: bool = False
    read_controller_ledger: bool = False
    read_receipts: bool = False
    read_events: bool = False
    read_terminal_records: bool = False

    controller_receipt_done: bool = False
    role_output_present: bool = False
    external_event_present: bool = False
    repair_receipt_present: bool = False

    authority_state_synced: bool = False
    router_row_reconciled: bool = False
    controller_row_reconciled: bool = False
    pending_or_wait_cleared: bool = False
    next_scheduled_or_barrier_recorded: bool = False
    write_router_table_done: bool = False
    write_controller_table_done: bool = False
    write_daemon_status_done: bool = False
    terminal_cleanup_done: bool = False

    router_table_writer: str = "router"  # router | controller | none
    controller_table_writer: str = "router"  # router | controller | none
    computed_next_before_required_reads: bool = False
    pending_cleared_before_authority_sync: bool = False
    same_action_reissued_after_done: bool = False
    daemon_status_from_stale_summary: bool = False
    terminal_status_written_before_cleanup: bool = False
    repair_blocker_before_receipt_read: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, phase: str, **changes: object) -> State:
    defaults = {
        "status": "accepted",
        "read_daemon_status": True,
        "read_authority_state": True,
        "read_router_scheduler": True,
        "read_controller_ledger": True,
        "authority_state_synced": True,
        "router_row_reconciled": True,
        "controller_row_reconciled": True,
        "pending_or_wait_cleared": True,
        "next_scheduled_or_barrier_recorded": True,
        "write_router_table_done": True,
        "write_controller_table_done": True,
        "write_daemon_status_done": True,
    }
    defaults.update(changes)
    return replace(State(scenario=scenario, phase=phase), **defaults)


def _rejected(scenario: str, phase: str, **changes: object) -> State:
    return replace(State(scenario=scenario, phase=phase), status="rejected", **changes)


def scenario_state(scenario: str) -> State:
    if scenario == STARTUP_RECEIPT_ADVANCES:
        return _accepted(
            scenario,
            "startup",
            read_receipts=True,
            controller_receipt_done=True,
        )
    if scenario == ROUTE_RECEIPT_ADVANCES:
        return _accepted(
            scenario,
            "route",
            read_receipts=True,
            controller_receipt_done=True,
        )
    if scenario == ROLE_OUTPUT_ADVANCES:
        return _accepted(
            scenario,
            "role_wait",
            read_events=True,
            role_output_present=True,
        )
    if scenario == EXTERNAL_EVENT_ADVANCES:
        return _accepted(
            scenario,
            "external_event",
            read_events=True,
            external_event_present=True,
        )
    if scenario == REPAIR_RECEIPT_ADVANCES:
        return _accepted(
            scenario,
            "repair",
            read_receipts=True,
            repair_receipt_present=True,
        )
    if scenario == TERMINAL_CLEANUP_ADVANCES:
        return _accepted(
            scenario,
            "terminal",
            read_terminal_records=True,
            terminal_cleanup_done=True,
            next_scheduled_or_barrier_recorded=False,
        )

    if scenario == COMPUTE_NEXT_BEFORE_REQUIRED_READS:
        return _rejected(
            scenario,
            "route",
            read_daemon_status=True,
            read_authority_state=False,
            read_router_scheduler=False,
            read_controller_ledger=False,
            computed_next_before_required_reads=True,
            next_scheduled_or_barrier_recorded=True,
            write_daemon_status_done=True,
        )
    if scenario == STARTUP_RECEIPT_LEAVES_PENDING:
        return _rejected(
            scenario,
            "startup",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_receipts=True,
            controller_receipt_done=True,
            authority_state_synced=False,
            router_row_reconciled=False,
            pending_or_wait_cleared=False,
            same_action_reissued_after_done=True,
            write_daemon_status_done=True,
        )
    if scenario == ROUTE_RECEIPT_LEAVES_ROUTER_FACT_STALE:
        return _rejected(
            scenario,
            "route",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_receipts=True,
            controller_receipt_done=True,
            authority_state_synced=False,
            router_row_reconciled=True,
            controller_row_reconciled=True,
            pending_or_wait_cleared=True,
            same_action_reissued_after_done=True,
        )
    if scenario == ROLE_OUTPUT_LEFT_DURABLE_ONLY:
        return _rejected(
            scenario,
            "role_wait",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_events=True,
            role_output_present=True,
            authority_state_synced=False,
            pending_or_wait_cleared=False,
            next_scheduled_or_barrier_recorded=True,
        )
    if scenario == EXTERNAL_EVENT_WAIT_NOT_ROUTER_CLOSED:
        return _rejected(
            scenario,
            "external_event",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_events=True,
            external_event_present=True,
            authority_state_synced=True,
            router_row_reconciled=False,
            pending_or_wait_cleared=False,
            next_scheduled_or_barrier_recorded=True,
        )
    if scenario == REPAIR_BLOCKER_BEFORE_RECEIPT_READ:
        return _rejected(
            scenario,
            "repair",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_receipts=False,
            repair_receipt_present=True,
            repair_blocker_before_receipt_read=True,
            write_daemon_status_done=True,
        )
    if scenario == TERMINAL_STATUS_BEFORE_CLEANUP:
        return _rejected(
            scenario,
            "terminal",
            read_daemon_status=True,
            read_authority_state=True,
            read_terminal_records=True,
            terminal_cleanup_done=False,
            terminal_status_written_before_cleanup=True,
            write_daemon_status_done=True,
        )
    if scenario == PENDING_CLEARED_BEFORE_AUTHORITY_SYNC:
        return _rejected(
            scenario,
            "route",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_receipts=True,
            controller_receipt_done=True,
            authority_state_synced=False,
            pending_or_wait_cleared=True,
            pending_cleared_before_authority_sync=True,
        )
    if scenario == CONTROLLER_WRITES_ROUTER_TABLE:
        return _rejected(
            scenario,
            "route",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=True,
            read_receipts=True,
            controller_receipt_done=True,
            authority_state_synced=True,
            router_row_reconciled=True,
            pending_or_wait_cleared=True,
            router_table_writer="controller",
            write_router_table_done=True,
        )
    if scenario == DAEMON_STATUS_FROM_STALE_SUMMARY:
        return _rejected(
            scenario,
            "role_wait",
            read_daemon_status=True,
            read_authority_state=True,
            read_router_scheduler=True,
            read_controller_ledger=False,
            read_events=True,
            role_output_present=True,
            authority_state_synced=False,
            daemon_status_from_stale_summary=True,
            write_daemon_status_done=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def _required_reads_done(state: State) -> bool:
    base = (
        state.read_daemon_status
        and state.read_authority_state
        and state.read_router_scheduler
        and state.read_controller_ledger
    )
    if state.phase in {"startup", "route", "repair"}:
        return base and state.read_receipts
    if state.phase in {"role_wait", "external_event"}:
        return base and state.read_events
    if state.phase == "terminal":
        return state.read_daemon_status and state.read_authority_state and state.read_terminal_records
    return base


def microstep_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.status == "new":
        return failures
    if (state.next_scheduled_or_barrier_recorded or state.write_daemon_status_done) and not _required_reads_done(state):
        failures.append("daemon computed or reported progress before reading required control tables")
    if state.computed_next_before_required_reads:
        failures.append("daemon computed next action before required reads")
    if state.router_table_writer == "controller":
        failures.append("Controller wrote Router-owned scheduler state")
    if state.pending_cleared_before_authority_sync or (state.pending_or_wait_cleared and not state.authority_state_synced):
        failures.append("daemon cleared pending or wait before syncing authority state")
    if state.controller_receipt_done and not (
        state.authority_state_synced
        and state.router_row_reconciled
        and state.controller_row_reconciled
        and state.pending_or_wait_cleared
    ):
        failures.append("done Controller receipt did not reconcile all authority, Router, Controller, and pending state")
    if state.same_action_reissued_after_done:
        failures.append("daemon reissued an action after done evidence had been read")
    if state.role_output_present and not (state.read_events and state.authority_state_synced and state.pending_or_wait_cleared):
        failures.append("role output stayed in durable storage without authority sync and wait closure")
    if state.external_event_present and not (state.read_events and state.router_row_reconciled and state.pending_or_wait_cleared):
        failures.append("external event did not close the Router-owned wait row")
    if state.repair_blocker_before_receipt_read:
        failures.append("repair blocker was written before the matching repair receipt was read")
    if state.terminal_status_written_before_cleanup or (
        state.phase == "terminal" and state.write_daemon_status_done and not state.terminal_cleanup_done
    ):
        failures.append("terminal daemon status was written before runtime cleanup completed")
    if state.daemon_status_from_stale_summary:
        failures.append("daemon status was written from a stale table summary")
    return failures


def accepts_only_valid_microstep_states(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = microstep_failures(state)
        if failures:
            return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"accepted", "rejected"}:
        return
    if state.scenario == "unset":
        for scenario in SCENARIOS:
            yield Transition(f"select_{scenario}", replace(State(), status="new", scenario=scenario))
        return
    candidate = scenario_state(state.scenario)
    failures = microstep_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected"),
        )


class DaemonMicrostepLifecycleStep:
    """Model one lifecycle microstep sequence.

    Input x State -> Set(Output x State)
    reads: daemon status, authority state, Router scheduler table, Controller
    action table, receipts, events, terminal lifecycle records
    writes: authority state, Router scheduler table, Controller action table,
    wait/pending state, next row, daemon status
    idempotency: receipt/event identities are consumed once before next work is
    calculated
    """

    name = "DaemonMicrostepLifecycleStep"
    input_description = "one daemon microstep lifecycle scenario"
    output_description = "one accepted or rejected microstep contract"
    reads = (
        "daemon_status",
        "bootstrap_or_run_state",
        "router_scheduler_ledger",
        "controller_action_ledger",
        "controller_receipts",
        "role_output_or_event_ledgers",
        "terminal_lifecycle_records",
    )
    writes = (
        "bootstrap_or_run_state",
        "router_scheduler_ledger",
        "controller_action_ledger",
        "pending_or_wait_state",
        "next_controller_row",
        "router_daemon_status",
    )
    idempotency = "stable receipt/event identities prevent repeated actions after evidence is consumed"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def invariant_failures(state: State) -> list[str]:
    if state.status == "accepted":
        return microstep_failures(state)
    return []


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((DaemonMicrostepLifecycleStep(),), name="flowpilot_daemon_microstep_lifecycle")


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="daemon_microstep_lifecycle_contract",
        description="Daemon lifecycle ticks read, reconcile, sync, clear, schedule, and write in order.",
        predicate=accepts_only_valid_microstep_states,
    ),
)


__all__ = [
    "EXTERNAL_INPUTS",
    "INVARIANTS",
    "MAX_SEQUENCE_LENGTH",
    "NEGATIVE_SCENARIOS",
    "SCENARIOS",
    "VALID_SCENARIOS",
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
    "microstep_failures",
    "next_safe_states",
    "scenario_state",
    "terminal_predicate",
]
