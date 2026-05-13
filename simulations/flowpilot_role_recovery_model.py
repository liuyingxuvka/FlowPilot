"""FlowGuard model for unified FlowPilot background-role recovery.

Risk intent brief:
- Recovery is a hard control-plane priority. Any heartbeat/manual resume
  recovery or mid-run role liveness fault must enter the same recovery engine
  before normal route work, waits, gates, packets, or active blockers proceed.
- The engine prefers targeted repair: restore the old role first, then spawn a
  targeted replacement, then reconcile slots, then recycle the full six-role
  crew only when targeted repair cannot succeed.
- Recovered agents are not usable until current-run memory and packet context
  have been injected. PM owns the post-recovery decision.
- Old-generation late output must be quarantined, never accepted as current
  packet or gate progress.

This is an abstract control-plane model. It validates the recovery order and
failure escalation contract before production router/runtime code is changed.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


@dataclass(frozen=True)
class Tick:
    """One Controller/router recovery tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | running | blocked | complete
    trigger_source: str = "none"  # none | heartbeat | manual_resume | mid_run_fault
    recovery_scope: str = "none"  # none | all_six | targeted | full_crew
    target_failed_roles: int = 0

    user_stop_requested: bool = False
    recovery_pending: bool = False
    priority_confirmed: bool = False
    normal_work_suspended: bool = False
    normal_work_attempted_before_recovery: bool = False
    heartbeat_bypassed_unified_recovery: bool = False
    mid_run_fault_treated_as_wait: bool = False

    transaction_opened: bool = False
    state_loaded: bool = False
    scope_confirmed: bool = False

    restore_attempted: bool = False
    restore_result: str = "unknown"  # unknown | success | failed | impossible
    targeted_replace_attempted: bool = False
    targeted_replace_result: str = "unknown"  # unknown | success | failed | capacity_full
    old_close_failed: bool = False
    spawn_capacity_full: bool = False
    slot_reconciliation_attempted: bool = False
    slot_reconciliation_result: str = "unknown"  # unknown | success | failed
    full_recycle_attempted: bool = False
    full_recycle_result: str = "unknown"  # unknown | success | failed

    crew_generation: int = 1
    role_binding_epoch_advanced: bool = False
    crew_ready: bool = False
    memory_context_injected: bool = False
    packet_holder_lost: bool = False
    packet_ownership_reconciled: bool = False
    stale_generation_output_seen: bool = False
    stale_generation_output_quarantined: bool = False
    stale_generation_output_accepted: bool = False

    recovery_report_written: bool = False
    pm_decision_requested: bool = False
    pm_decision_returned: bool = False
    controller_auto_continued_after_recovery: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


class UnifiedRoleRecoveryStep:
    """Model one role-recovery control-plane transition.

    Input x State -> Set(Output x State)
    reads: trigger source, recovery priority, attempt ladder, memory/context
      injection, packet ownership, generation quarantine, and PM readiness
    writes: one durable recovery fact, escalation attempt, report, or terminal
      status
    idempotency: repeated ticks observe existing durable facts and advance at
      most one missing recovery fact; terminal states produce no side effects
    """

    name = "UnifiedRoleRecoveryStep"
    reads = (
        "trigger_source",
        "recovery_pending",
        "recovery_scope",
        "attempt_ladder",
        "memory_context",
        "packet_ownership",
        "generation_epoch",
        "pm_decision",
    )
    writes = (
        "recovery_transaction",
        "recovery_attempt",
        "quarantine_record",
        "recovery_report",
        "terminal_status",
    )
    input_description = "Controller recovery tick"
    output_description = "one abstract FlowPilot role-recovery control action"
    idempotency = "durable recovery facts are recorded once"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(
                output=Action(transition.label),
                new_state=transition.state,
                label=transition.label,
            )


def _start_recovery(trigger_source: str, scope: str, failed_roles: int) -> State:
    return State(
        status="running",
        trigger_source=trigger_source,
        recovery_scope=scope,
        target_failed_roles=failed_roles,
        recovery_pending=True,
        normal_work_suspended=True,
        transaction_opened=True,
        packet_holder_lost=trigger_source == "mid_run_fault",
    )


def _crew_ready(state: State, *, full_recycle: bool = False) -> State:
    return replace(
        state,
        crew_ready=True,
        role_binding_epoch_advanced=True,
        crew_generation=state.crew_generation + (1 if full_recycle else 0),
        stale_generation_output_seen=not state.restore_result == "success",
    )


def next_safe_states(state: State) -> Iterable[Transition]:
    if state.status in {"blocked", "complete"}:
        return

    if state.trigger_source == "none":
        yield Transition(
            "heartbeat_entered_unified_recovery",
            _start_recovery("heartbeat", "all_six", 0),
        )
        yield Transition(
            "manual_resume_entered_unified_recovery",
            _start_recovery("manual_resume", "all_six", 0),
        )
        yield Transition(
            "mid_run_liveness_fault_entered_unified_recovery",
            _start_recovery("mid_run_fault", "targeted", 1),
        )
        yield Transition(
            "user_stop_preempts_recovery",
            replace(state, status="blocked", user_stop_requested=True),
        )
        return

    if state.user_stop_requested:
        yield Transition(
            "user_stop_preempts_recovery",
            replace(state, status="blocked", recovery_pending=False),
        )
        return

    if not state.priority_confirmed:
        yield Transition(
            "recovery_preempts_normal_work",
            replace(state, priority_confirmed=True, normal_work_suspended=True),
        )
        return

    if not state.state_loaded:
        yield Transition(
            "current_run_state_loaded",
            replace(state, state_loaded=True),
        )
        return

    if not state.scope_confirmed:
        if state.recovery_scope == "all_six":
            yield Transition(
                "all_six_sweep_selected",
                replace(state, scope_confirmed=True),
            )
        elif state.recovery_scope == "targeted":
            yield Transition(
                "targeted_role_scope_selected",
                replace(state, scope_confirmed=True),
            )
        elif state.recovery_scope == "full_crew":
            yield Transition(
                "full_crew_scope_selected",
                replace(state, scope_confirmed=True),
            )
        return

    if not state.restore_attempted and state.recovery_scope != "full_crew":
        yield Transition(
            "restore_attempted_before_replacement",
            replace(state, restore_attempted=True),
        )
        return

    if state.restore_attempted and state.restore_result == "unknown":
        yield Transition(
            "old_role_restored",
            _crew_ready(replace(state, restore_result="success")),
        )
        yield Transition(
            "old_role_restore_failed",
            replace(state, restore_result="failed"),
        )
        return

    if (
        state.restore_result == "failed"
        and not state.targeted_replace_attempted
        and state.recovery_scope == "targeted"
    ):
        yield Transition(
            "targeted_replacement_spawned",
            _crew_ready(
                replace(
                    state,
                    targeted_replace_attempted=True,
                    targeted_replace_result="success",
                )
            ),
        )
        yield Transition(
            "targeted_replacement_capacity_full",
            replace(
                state,
                targeted_replace_attempted=True,
                targeted_replace_result="capacity_full",
                old_close_failed=True,
                spawn_capacity_full=True,
            ),
        )
        return

    if (
        state.restore_result == "failed"
        and not state.full_recycle_attempted
        and state.recovery_scope == "all_six"
    ):
        yield Transition(
            "full_crew_recycle_attempted",
            replace(
                state,
                recovery_scope="full_crew",
                full_recycle_attempted=True,
            ),
        )
        return

    if (
        state.targeted_replace_result == "capacity_full"
        and not state.slot_reconciliation_attempted
    ):
        yield Transition(
            "slot_reconciliation_attempted_after_capacity_full",
            replace(
                state,
                slot_reconciliation_attempted=True,
                slot_reconciliation_result="failed",
            ),
        )
        return

    if (
        state.slot_reconciliation_result == "failed"
        and not state.full_recycle_attempted
    ):
        yield Transition(
            "full_crew_recycle_attempted",
            replace(
                state,
                recovery_scope="full_crew",
                full_recycle_attempted=True,
            ),
        )
        return

    if state.full_recycle_attempted and state.full_recycle_result == "unknown":
        yield Transition(
            "full_crew_recycle_succeeded",
            _crew_ready(replace(state, full_recycle_result="success"), full_recycle=True),
        )
        yield Transition(
            "full_crew_recycle_failure_blocks_environment",
            replace(
                state,
                status="blocked",
                full_recycle_result="failed",
                recovery_pending=False,
                crew_ready=False,
            ),
        )
        return

    if state.crew_ready and not state.memory_context_injected:
        yield Transition(
            "memory_context_injected",
            replace(state, memory_context_injected=True),
        )
        return

    if (
        state.memory_context_injected
        and state.packet_holder_lost
        and not state.packet_ownership_reconciled
    ):
        yield Transition(
            "packet_ownership_reconciled",
            replace(state, packet_ownership_reconciled=True),
        )
        return

    if (
        state.memory_context_injected
        and state.stale_generation_output_seen
        and not state.stale_generation_output_quarantined
    ):
        yield Transition(
            "stale_generation_output_quarantined",
            replace(state, stale_generation_output_quarantined=True),
        )
        return

    if state.crew_ready and not state.recovery_report_written:
        yield Transition(
            "recovery_report_written",
            replace(state, recovery_report_written=True),
        )
        return

    if state.recovery_report_written and not state.pm_decision_requested:
        yield Transition(
            "pm_decision_requested_after_recovery",
            replace(state, pm_decision_requested=True),
        )
        return

    if state.pm_decision_requested and not state.pm_decision_returned:
        yield Transition(
            "pm_recovery_decision_returned",
            replace(state, pm_decision_returned=True),
        )
        return

    if state.pm_decision_returned:
        yield Transition(
            "recovery_loop_complete",
            replace(state, status="complete", recovery_pending=False),
        )


def next_states(state: State) -> Iterable[State]:
    for transition in next_safe_states(state):
        yield transition.state


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []

    if state.recovery_pending and state.normal_work_attempted_before_recovery:
        failures.append("normal work preempted a pending role recovery")
    if (
        state.trigger_source in {"heartbeat", "manual_resume"}
        and state.heartbeat_bypassed_unified_recovery
    ):
        failures.append("heartbeat/manual resume bypassed unified recovery")
    if (
        state.trigger_source == "mid_run_fault"
        and state.mid_run_fault_treated_as_wait
    ):
        failures.append("mid-run role fault was treated as a normal wait")
    if state.targeted_replace_attempted and not state.restore_attempted:
        failures.append("targeted replacement was attempted before restore")
    if (
        state.full_recycle_attempted
        and state.restore_result != "failed"
        and state.recovery_scope != "full_crew"
    ):
        failures.append("full crew recycle happened before targeted recovery failed")
    if (
        state.full_recycle_attempted
        and state.trigger_source == "mid_run_fault"
        and not (
            state.restore_attempted
            and state.targeted_replace_attempted
            and state.slot_reconciliation_attempted
        )
    ):
        failures.append("mid-run full recycle skipped targeted recovery escalation")
    if (
        state.old_close_failed
        and state.spawn_capacity_full
        and not state.full_recycle_attempted
        and (state.recovery_report_written or state.pm_decision_requested)
    ):
        failures.append("capacity/full-slot conflict did not escalate to full recycle")
    if state.full_recycle_result == "failed" and state.crew_ready:
        failures.append("failed full crew recycle was marked crew-ready")
    if state.crew_ready and not state.memory_context_injected and (
        state.recovery_report_written or state.pm_decision_requested
    ):
        failures.append("recovered role was marked ready without memory injection")
    if state.stale_generation_output_accepted:
        failures.append("stale generation output was accepted as current progress")
    if (
        state.pm_decision_requested
        and state.packet_holder_lost
        and not state.packet_ownership_reconciled
    ):
        failures.append("PM continuation requested before packet ownership reconciliation")
    if state.controller_auto_continued_after_recovery:
        failures.append("Controller auto-continued after recovery without PM decision")
    if (
        state.user_stop_requested
        and state.recovery_pending
        and state.status not in {"blocked", "complete"}
    ):
        failures.append("recovery ignored explicit user stop/cancel")
    if state.recovery_report_written and not state.transaction_opened:
        failures.append("recovery report was written without a recovery transaction")
    if state.pm_decision_requested and not state.recovery_report_written:
        failures.append("PM decision was requested before recovery report")
    if state.status == "complete" and not state.pm_decision_returned:
        failures.append("recovery completed without PM recovery decision")

    return failures


def role_recovery_invariant(state: State, trace) -> InvariantResult:
    del trace
    failures = invariant_failures(state)
    if failures:
        return InvariantResult.fail("; ".join(failures))
    return InvariantResult.pass_()


INVARIANTS = (
    Invariant(
        name="flowpilot_unified_role_recovery",
        description=(
            "Role recovery preempts normal work, uses one unified engine for "
            "heartbeat/manual and mid-run faults, escalates from restore to "
            "targeted replacement to full crew recycle, injects current-run "
            "memory/context before readiness, quarantines old-generation "
            "output, reconciles packet ownership, and waits for PM decision."
        ),
        predicate=role_recovery_invariant,
    ),
)

EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 18


def build_workflow() -> Workflow:
    return Workflow((UnifiedRoleRecoveryStep(),), name="flowpilot_unified_role_recovery")


def is_terminal(state: State) -> bool:
    return state.status in {"blocked", "complete"}


def is_success(state: State) -> bool:
    return state.status == "complete"


def _ready_state(**changes: object) -> State:
    base = State(
        status="running",
        trigger_source="mid_run_fault",
        recovery_scope="targeted",
        target_failed_roles=1,
        recovery_pending=True,
        priority_confirmed=True,
        normal_work_suspended=True,
        transaction_opened=True,
        state_loaded=True,
        scope_confirmed=True,
        restore_attempted=True,
        restore_result="failed",
        targeted_replace_attempted=True,
        targeted_replace_result="success",
        crew_ready=True,
        role_binding_epoch_advanced=True,
        memory_context_injected=True,
        packet_holder_lost=True,
        packet_ownership_reconciled=True,
        stale_generation_output_seen=True,
        stale_generation_output_quarantined=True,
        recovery_report_written=True,
    )
    return replace(base, **changes)


def hazard_states() -> dict[str, State]:
    return {
        "normal_work_preempts_recovery": State(
            status="running",
            trigger_source="mid_run_fault",
            recovery_pending=True,
            normal_work_attempted_before_recovery=True,
        ),
        "heartbeat_bypasses_unified_recovery": State(
            status="running",
            trigger_source="heartbeat",
            heartbeat_bypassed_unified_recovery=True,
        ),
        "mid_run_fault_treated_as_wait": State(
            status="running",
            trigger_source="mid_run_fault",
            mid_run_fault_treated_as_wait=True,
        ),
        "targeted_replace_before_restore": _ready_state(
            restore_attempted=False,
            targeted_replace_attempted=True,
        ),
        "full_recycle_without_targeted_attempt": _ready_state(
            full_recycle_attempted=True,
            targeted_replace_attempted=False,
            slot_reconciliation_attempted=False,
        ),
        "capacity_full_without_full_recycle": _ready_state(
            targeted_replace_result="capacity_full",
            old_close_failed=True,
            spawn_capacity_full=True,
            slot_reconciliation_attempted=True,
            full_recycle_attempted=False,
            recovery_report_written=True,
        ),
        "failed_full_recycle_marked_ready": _ready_state(
            recovery_scope="full_crew",
            full_recycle_attempted=True,
            full_recycle_result="failed",
            crew_ready=True,
        ),
        "ready_without_memory_injection": _ready_state(
            memory_context_injected=False,
            recovery_report_written=True,
        ),
        "stale_generation_output_accepted": _ready_state(
            stale_generation_output_accepted=True,
        ),
        "pm_continue_without_packet_reconciliation": _ready_state(
            packet_holder_lost=True,
            packet_ownership_reconciled=False,
            pm_decision_requested=True,
        ),
        "controller_auto_continues_after_recovery": _ready_state(
            controller_auto_continued_after_recovery=True,
        ),
        "recovery_blocks_user_stop": State(
            status="running",
            trigger_source="mid_run_fault",
            recovery_pending=True,
            user_stop_requested=True,
        ),
    }


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
    "role_recovery_invariant",
]
