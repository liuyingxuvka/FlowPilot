"""FlowGuard model for FlowPilot daemon durable reconciliation.

Risk intent brief:
- Review the second-layer Router/daemon failure class where durable evidence
  exists on disk but the daemon keeps returning stale work.
- Model-critical durable state: Controller action receipts, stateful
  Controller-action postconditions, role-output ledgers, canonical report
  artifacts, Router event flags, stale in-memory daemon snapshots, and the
  one-tick reconciliation barrier before next-action computation.
- Adversarial branches include a completed Controller action repeated forever,
  a done receipt that updates only the action ledger but not Router state,
  an incomplete stateful receipt treated as success, a submitted role output
  left only in the role-output ledger, a canonical report file not synced back
  into Router flags, a daemon save that overwrites newer role-output evidence,
  and next-action computation that reads old pending_action before durable
  reconciliation.
- Hard invariants: every active daemon tick must reconcile durable receipts and
  role outputs before returning work; completed or blocked Controller actions
  must be cleared, applied, or surfaced as a blocker; expected valid role
  outputs must become Router events exactly once; canonical artifacts and flags
  must not diverge; startup-daemon bootloader rows must have one
  reconciliation owner and must not be converted into PM repair blockers after
  their postcondition is already satisfied; and stale daemon snapshots must
  never erase newer durable evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One active Router daemon tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    lifecycle: str = "active"  # active | terminal
    daemon_alive: bool = True
    reconciliation_barrier_started: bool = False

    pending_action_kind: str = "await_role_decision"  # none | await_role_decision | rehydrate_role_agents
    pending_action_status: str = "waiting"  # none | pending | waiting | done | blocked
    pending_action_returned_again: bool = False
    next_action_computed: bool = False
    computed_before_reconciliation: bool = False

    controller_receipt_status: str = "none"  # none | done | blocked
    controller_receipt_payload_quality: str = "none"  # none | complete | incomplete
    controller_receipt_action_class: str = "stateful"  # stateful | startup_bootloader
    controller_receipt_reconciled: bool = False
    pending_cleared_after_receipt: bool = False
    stateful_postconditions_applied: bool = False
    control_blocker_written: bool = False
    startup_row_reconciled: bool = False
    startup_postcondition_satisfied: bool = False
    startup_reconciliation_owner: str = "none"  # none | startup_daemon | generic_receipt
    generic_receipt_reconciler_touched_startup_row: bool = False
    unsupported_startup_receipt_action: bool = False

    role_output_ledger_submitted: bool = False
    role_output_envelope_valid: bool = True
    role_output_event_expected: bool = True
    canonical_artifact_exists: bool = False
    role_output_reconciled: bool = False
    router_event_recorded: bool = False
    router_event_flag_synced: bool = False
    scoped_event_recorded: bool = False
    role_output_consumption_count: int = 0
    role_wait_cleared_after_event: bool = False
    invalid_role_output_accepted: bool = False

    stale_daemon_snapshot_loaded: bool = False
    stale_snapshot_saved_after_external_event: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)


class DaemonReconciliationStep:
    """Model one daemon reconciliation and next-action step.

    Input x State -> Set(Output x State)
    reads: router_state.pending_action, controller_receipts,
    controller_action_ledger, role_output_ledger, canonical report artifacts,
    scoped event identities, daemon in-memory snapshot
    writes: canonical router_state flags/events, cleared pending_action,
    stateful action postconditions, control blockers, daemon status
    idempotency: repeated ticks over the same durable evidence do not repeat
    Controller actions or duplicate Router events.
    """

    name = "DaemonReconciliationStep"
    input_description = "one active persistent Router daemon tick"
    output_description = "one durable reconciliation or next-action transition"
    reads = (
        "router_state.pending_action",
        "controller_receipts",
        "controller_action_ledger",
        "role_output_ledger",
        "canonical_role_output_artifacts",
        "scoped_event_registry",
        "daemon_snapshot",
    )
    writes = (
        "router_state.pending_action",
        "router_state.flags",
        "router_state.events",
        "controller_action_ledger",
        "control_blockers",
        "router_daemon_status",
    )
    idempotency = "receipt action_id and scoped role-output identity are consumed at most once"

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

    if not state.reconciliation_barrier_started:
        yield Transition(
            "daemon_tick_starts_durable_reconciliation_barrier",
            _step(state, reconciliation_barrier_started=True),
        )
        return

    if not state.role_output_ledger_submitted and state.pending_action_kind == "await_role_decision":
        yield Transition(
            "role_output_submitted_while_router_waits",
            _step(
                state,
                role_output_ledger_submitted=True,
                canonical_artifact_exists=True,
                stale_daemon_snapshot_loaded=True,
            ),
        )
        yield Transition(
            "daemon_reconciles_startup_bootloader_receipt_once",
            _step(
                state,
                pending_action_kind="none",
                pending_action_status="none",
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
                controller_receipt_action_class="startup_bootloader",
                controller_receipt_reconciled=True,
                pending_cleared_after_receipt=True,
                stateful_postconditions_applied=True,
                startup_row_reconciled=True,
                startup_postcondition_satisfied=True,
                startup_reconciliation_owner="startup_daemon",
            ),
        )
        yield Transition(
            "heartbeat_opens_rehydrate_pending_action",
            _step(
                state,
                pending_action_kind="rehydrate_role_agents",
                pending_action_status="pending",
                role_wait_cleared_after_event=False,
                stale_daemon_snapshot_loaded=True,
            ),
        )
        return

    if state.role_output_ledger_submitted and state.pending_action_kind == "await_role_decision":
        yield Transition(
            "heartbeat_opens_rehydrate_pending_action_after_role_output",
            _step(
                state,
                pending_action_kind="rehydrate_role_agents",
                pending_action_status="pending",
                stale_daemon_snapshot_loaded=True,
            ),
        )
        yield Transition(
            "daemon_reconciles_role_output_to_router_event",
            _step(
                state,
                role_output_reconciled=True,
                router_event_recorded=True,
                router_event_flag_synced=True,
                scoped_event_recorded=True,
                role_output_consumption_count=state.role_output_consumption_count + 1,
                pending_action_kind="none",
                pending_action_status="none",
                role_wait_cleared_after_event=True,
            ),
        )
        return

    if (
        state.pending_action_kind == "rehydrate_role_agents"
        and not state.role_output_ledger_submitted
        and state.controller_receipt_status == "none"
    ):
        yield Transition(
            "role_output_submitted_while_rehydrate_pending",
            _step(
                state,
                role_output_ledger_submitted=True,
                canonical_artifact_exists=True,
                stale_daemon_snapshot_loaded=True,
            ),
        )
        yield Transition(
            "controller_writes_complete_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
            ),
        )
        yield Transition(
            "controller_writes_incomplete_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="done",
                controller_receipt_payload_quality="incomplete",
            ),
        )
        yield Transition(
            "controller_writes_blocked_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="blocked",
                controller_receipt_payload_quality="incomplete",
            ),
        )
        return

    if state.pending_action_kind == "rehydrate_role_agents" and state.controller_receipt_status == "none":
        yield Transition(
            "controller_writes_complete_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
            ),
        )
        yield Transition(
            "controller_writes_incomplete_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="done",
                controller_receipt_payload_quality="incomplete",
            ),
        )
        yield Transition(
            "controller_writes_blocked_rehydrate_receipt",
            _step(
                state,
                controller_receipt_status="blocked",
                controller_receipt_payload_quality="incomplete",
            ),
        )
        return

    if (
        state.pending_action_kind == "rehydrate_role_agents"
        and state.controller_receipt_status == "done"
        and not state.controller_receipt_reconciled
    ):
        if state.controller_receipt_payload_quality == "complete":
            yield Transition(
                "daemon_applies_complete_receipt_and_clears_pending",
                _step(
                    state,
                    controller_receipt_reconciled=True,
                    pending_cleared_after_receipt=True,
                    stateful_postconditions_applied=True,
                    pending_action_kind="none",
                    pending_action_status="none",
                ),
            )
        else:
            yield Transition(
                "daemon_converts_incomplete_receipt_to_control_blocker",
                _step(
                    state,
                    controller_receipt_reconciled=True,
                    pending_cleared_after_receipt=True,
                    control_blocker_written=True,
                    pending_action_kind="none",
                    pending_action_status="none",
                ),
            )
        return

    if (
        state.pending_action_kind == "rehydrate_role_agents"
        and state.controller_receipt_status == "blocked"
        and not state.controller_receipt_reconciled
    ):
        yield Transition(
            "daemon_surfaces_blocked_receipt_as_control_blocker",
            _step(
                state,
                controller_receipt_reconciled=True,
                pending_cleared_after_receipt=True,
                control_blocker_written=True,
                pending_action_kind="none",
                pending_action_status="none",
            ),
        )
        return

    if (
        state.role_output_ledger_submitted
        and not state.role_output_reconciled
        and state.role_output_envelope_valid
        and state.role_output_event_expected
    ):
        yield Transition(
            "daemon_reconciles_role_output_to_router_event",
            _step(
                state,
                role_output_reconciled=True,
                router_event_recorded=True,
                router_event_flag_synced=True,
                scoped_event_recorded=True,
                role_output_consumption_count=state.role_output_consumption_count + 1,
                role_wait_cleared_after_event=True,
            ),
        )
        return

    if (
        state.role_output_ledger_submitted
        and not state.role_output_reconciled
        and (not state.role_output_envelope_valid or not state.role_output_event_expected)
    ):
        yield Transition(
            "daemon_rejects_invalid_role_output_with_control_blocker",
            _step(state, role_output_reconciled=True, control_blocker_written=True),
        )
        return

    if state.router_event_recorded and state.role_output_consumption_count == 1 and not state.next_action_computed:
        yield Transition(
            "daemon_idempotently_ignores_already_recorded_role_output",
            _step(state, role_output_reconciled=True),
        )
        yield Transition(
            "daemon_computes_next_action_after_reconciliation",
            _step(state, next_action_computed=True),
        )
        return

    if state.control_blocker_written and not state.next_action_computed:
        yield Transition(
            "daemon_returns_control_blocker_after_reconciliation",
            _step(state, next_action_computed=True),
        )
        return

    if (
        state.controller_receipt_reconciled
        and state.stateful_postconditions_applied
        and not state.role_output_ledger_submitted
        and not state.next_action_computed
    ):
        yield Transition(
            "daemon_computes_next_action_after_reconciliation",
            _step(state, next_action_computed=True),
        )
        return

    if state.next_action_computed:
        yield Transition(
            "terminal_stop_after_reconciliation_contract_checked",
            _step(state, lifecycle="terminal"),
        )
        return


def hazard_states() -> dict[str, State]:
    safe = State(reconciliation_barrier_started=True)
    return {
        "completed_controller_action_repeated": replace(
            safe,
            pending_action_kind="rehydrate_role_agents",
            pending_action_status="done",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_reconciled=True,
            pending_action_returned_again=True,
            next_action_computed=True,
        ),
        "done_receipt_without_stateful_postconditions": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=False,
            next_action_computed=True,
        ),
        "incomplete_stateful_receipt_silently_done": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="incomplete",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            control_blocker_written=False,
            next_action_computed=True,
        ),
        "submitted_role_output_left_in_ledger": replace(
            safe,
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            role_output_reconciled=False,
            router_event_recorded=False,
            next_action_computed=True,
        ),
        "canonical_artifact_flag_not_synced": replace(
            safe,
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            role_output_reconciled=True,
            router_event_recorded=True,
            router_event_flag_synced=False,
            next_action_computed=True,
        ),
        "stale_snapshot_overwrites_role_output_event": replace(
            safe,
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            router_event_recorded=False,
            stale_daemon_snapshot_loaded=True,
            stale_snapshot_saved_after_external_event=True,
            next_action_computed=True,
        ),
        "computed_from_pending_before_reconciliation": replace(
            safe,
            pending_action_kind="rehydrate_role_agents",
            pending_action_status="pending",
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            computed_before_reconciliation=True,
            next_action_computed=True,
        ),
        "startup_reconciled_action_false_pm_blocker": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="startup_bootloader",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            startup_row_reconciled=True,
            startup_postcondition_satisfied=True,
            startup_reconciliation_owner="startup_daemon",
            control_blocker_written=True,
            next_action_computed=True,
        ),
        "startup_unsupported_receipt_escalated_to_pm": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="startup_bootloader",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            startup_row_reconciled=True,
            startup_postcondition_satisfied=True,
            startup_reconciliation_owner="startup_daemon",
            generic_receipt_reconciler_touched_startup_row=True,
            unsupported_startup_receipt_action=True,
            control_blocker_written=True,
            next_action_computed=True,
        ),
        "startup_row_reconciled_without_postcondition": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="startup_bootloader",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            startup_row_reconciled=True,
            startup_postcondition_satisfied=False,
            startup_reconciliation_owner="startup_daemon",
            next_action_computed=True,
        ),
        "startup_row_reconciled_by_wrong_owner": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="startup_bootloader",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            startup_row_reconciled=True,
            startup_postcondition_satisfied=True,
            startup_reconciliation_owner="generic_receipt",
            next_action_computed=True,
        ),
        "role_wait_not_cleared_after_event": replace(
            safe,
            pending_action_kind="await_role_decision",
            pending_action_status="waiting",
            role_output_ledger_submitted=True,
            role_output_reconciled=True,
            router_event_recorded=True,
            router_event_flag_synced=True,
            role_wait_cleared_after_event=False,
            next_action_computed=True,
        ),
        "duplicate_role_output_consumption": replace(
            safe,
            role_output_ledger_submitted=True,
            role_output_reconciled=True,
            router_event_recorded=True,
            router_event_flag_synced=True,
            scoped_event_recorded=True,
            role_output_consumption_count=2,
            next_action_computed=True,
        ),
        "blocked_receipt_repeated_instead_of_blocker": replace(
            safe,
            pending_action_kind="rehydrate_role_agents",
            pending_action_status="blocked",
            controller_receipt_status="blocked",
            controller_receipt_reconciled=True,
            pending_action_returned_again=True,
            control_blocker_written=False,
            next_action_computed=True,
        ),
        "invalid_role_output_silently_accepted": replace(
            safe,
            role_output_ledger_submitted=True,
            role_output_envelope_valid=False,
            role_output_event_expected=True,
            role_output_reconciled=True,
            router_event_recorded=True,
            invalid_role_output_accepted=True,
            next_action_computed=True,
        ),
        "receipt_and_role_output_interleaving_starves_role_output": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            role_output_reconciled=False,
            router_event_recorded=False,
            next_action_computed=True,
        ),
    }


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    durable_receipt_exists = state.controller_receipt_status in {"done", "blocked"}
    durable_role_output_exists = state.role_output_ledger_submitted or state.canonical_artifact_exists
    durable_evidence_exists = durable_receipt_exists or durable_role_output_exists

    if state.lifecycle == "active" and state.daemon_alive and durable_evidence_exists:
        if not state.reconciliation_barrier_started:
            failures.append("daemon tick handled durable evidence without starting reconciliation barrier")
        if state.computed_before_reconciliation:
            failures.append("daemon computed next action from stale pending_action before durable reconciliation")

    if state.pending_action_returned_again and state.controller_receipt_status in {"done", "blocked"}:
        failures.append("daemon repeated a completed or blocked Controller action instead of clearing or blocking")

    if state.controller_receipt_status in {"done", "blocked"} and state.next_action_computed:
        if not state.controller_receipt_reconciled:
            failures.append("Controller receipt existed but was not reconciled before next action")
        if not state.pending_cleared_after_receipt:
            failures.append("Controller receipt was reconciled but pending_action was not cleared")

    if (
        state.controller_receipt_status == "done"
        and state.controller_receipt_payload_quality == "complete"
        and state.controller_receipt_action_class != "startup_bootloader"
        and state.next_action_computed
        and not state.stateful_postconditions_applied
    ):
        failures.append("stateful Controller receipt was marked done without applying Router postconditions")

    if state.controller_receipt_action_class == "startup_bootloader":
        if state.startup_row_reconciled and not state.startup_postcondition_satisfied:
            failures.append("startup bootloader row was reconciled without its postcondition")
        if state.startup_row_reconciled and state.startup_reconciliation_owner != "startup_daemon":
            failures.append("startup bootloader row was reconciled by the wrong owner")
        if state.startup_row_reconciled and state.control_blocker_written:
            failures.append("startup bootloader row produced a control blocker after it was already reconciled")
        if (
            state.generic_receipt_reconciler_touched_startup_row
            and state.unsupported_startup_receipt_action
            and state.startup_postcondition_satisfied
            and state.control_blocker_written
        ):
            failures.append("unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied")
        if state.next_action_computed and state.controller_receipt_status == "done" and not (
            state.startup_row_reconciled or state.control_blocker_written
        ):
            failures.append("startup bootloader receipt reached next action without startup reconciliation or a real blocker")

    if (
        state.controller_receipt_status == "done"
        and state.controller_receipt_payload_quality == "incomplete"
        and state.next_action_computed
        and not state.control_blocker_written
    ):
        failures.append("incomplete stateful Controller receipt was accepted without a control blocker")

    if (
        state.controller_receipt_status == "blocked"
        and state.next_action_computed
        and not state.control_blocker_written
    ):
        failures.append("blocked Controller receipt was not surfaced as a control blocker")

    if (
        durable_role_output_exists
        and state.role_output_envelope_valid
        and state.role_output_event_expected
        and state.next_action_computed
    ):
        if not state.role_output_reconciled or not state.router_event_recorded:
            failures.append("submitted expected role output was left only in durable storage")
        if state.canonical_artifact_exists and not state.router_event_flag_synced:
            failures.append("canonical role-output artifact existed without synced Router event flag")
        if not state.role_wait_cleared_after_event:
            failures.append("expected role wait remained current after Router recorded the role output")

    if state.role_output_consumption_count > 1:
        failures.append("role output durable evidence was consumed more than once")

    if state.stale_snapshot_saved_after_external_event:
        failures.append("daemon saved a stale router_state snapshot over newer durable role output")

    if state.invalid_role_output_accepted or (
        durable_role_output_exists
        and (not state.role_output_envelope_valid or not state.role_output_event_expected)
        and state.router_event_recorded
    ):
        failures.append("invalid or unauthorized role output was accepted as a Router event")

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
    _invariant("durable_evidence_requires_reconciliation_barrier", "daemon tick handled durable evidence without starting reconciliation barrier"),
    _invariant("next_action_after_reconciliation_only", "daemon computed next action from stale pending_action before durable reconciliation"),
    _invariant("completed_controller_action_not_repeated", "daemon repeated a completed or blocked Controller action instead of clearing or blocking"),
    _invariant("controller_receipt_reconciled_before_next", "Controller receipt existed but was not reconciled before next action"),
    _invariant("receipt_reconciliation_clears_pending_action", "Controller receipt was reconciled but pending_action was not cleared"),
    _invariant("stateful_receipt_applies_postconditions", "stateful Controller receipt was marked done without applying Router postconditions"),
    _invariant("startup_bootloader_reconciles_with_postcondition", "startup bootloader row was reconciled without its postcondition"),
    _invariant("startup_bootloader_reconciliation_owner", "startup bootloader row was reconciled by the wrong owner"),
    _invariant("startup_bootloader_no_false_pm_blocker_after_reconciled", "startup bootloader row produced a control blocker after it was already reconciled"),
    _invariant("unsupported_startup_receipt_not_pm_repair_after_success", "unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied"),
    _invariant("startup_bootloader_receipt_must_be_reconciled", "startup bootloader receipt reached next action without startup reconciliation or a real blocker"),
    _invariant("incomplete_stateful_receipt_blocks", "incomplete stateful Controller receipt was accepted without a control blocker"),
    _invariant("blocked_receipt_surfaces_blocker", "blocked Controller receipt was not surfaced as a control blocker"),
    _invariant("role_output_storage_becomes_router_event", "submitted expected role output was left only in durable storage"),
    _invariant("canonical_artifact_flag_sync", "canonical role-output artifact existed without synced Router event flag"),
    _invariant("role_wait_cleared_after_event", "expected role wait remained current after Router recorded the role output"),
    _invariant("role_output_consumed_once", "role output durable evidence was consumed more than once"),
    _invariant("stale_daemon_snapshot_cannot_overwrite_evidence", "daemon saved a stale router_state snapshot over newer durable role output"),
    _invariant("invalid_role_output_not_accepted", "invalid or unauthorized role output was accepted as a Router event"),
)


def build_workflow() -> Workflow:
    return Workflow((DaemonReconciliationStep(),), name="flowpilot_daemon_reconciliation")


def next_states(state: State) -> tuple[tuple[str, State], ...]:
    return tuple((transition.label, transition.state) for transition in next_safe_states(state))


def is_terminal(state: State) -> bool:
    return state.lifecycle == "terminal"


def is_success(state: State) -> bool:
    return state.lifecycle == "terminal"


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 10


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
