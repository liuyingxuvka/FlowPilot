"""FlowGuard model for FlowPilot daemon durable reconciliation.

Risk intent brief:
- Review the second-layer Router/daemon failure class where durable evidence
  exists on disk but the daemon keeps returning stale work.
- Model-critical durable state: Controller action receipts, stateful
  Controller-action postconditions, Controller-boundary confirmation artifacts,
  Controller action rows, Router scheduler rows, packet ledgers, mail delivery
  flags, startup secondary-state role flags, role-output ledgers, canonical
  report artifacts, Router event flags, transient Controller action temp files,
  stale in-memory daemon snapshots, and the one-tick reconciliation barrier
  before next-action computation.
- Adversarial branches include a completed Controller action repeated forever,
  a done receipt that updates only the action ledger but not Router state,
  an incomplete stateful receipt treated as success, a submitted role output
  left only in the role-output ledger, a canonical report file not synced back
  into Router flags, a daemon save that overwrites newer role-output evidence,
  and next-action computation that reads old pending_action before durable
  reconciliation.
- Hard invariants: every active daemon tick must reconcile durable receipts and
  role outputs before returning work; completed or blocked Controller actions
  must be cleared, applied, or surfaced as a blocker; a completed mail-delivery
  receipt must either fold the packet ledger and Router flag together or remain
  an explicit control blocker; a submitted PM repair decision for that blocker
  must be consumed into a repair transaction or reissue before the daemon keeps
  waiting on the same role; expected valid role outputs must become Router
  events exactly once; canonical artifacts and flags must not diverge; a valid
  Controller-boundary artifact plus reconciled receipt/action/scheduler rows
  must rebuild Router flags before any next action is exposed; startup-daemon
  bootloader rows must have one reconciliation owner, startup postcondition
  misses must stay on the mechanical reissue lane until that budget is
  exhausted, and any blocker for the same startup row must be resolved before
  PM repair work can be queued once the postcondition is satisfied; daemon
  startup role flags written into the secondary startup record must be folded
  into Router state atomically before next-action computation; Controller
  action directory scans must skip transient `.tmp-*.json` files and transient
  file disappearance must never stop the daemon; daemon
  queue budget exhaustion must immediately start the next tick instead of
  sleeping; real waits must not busy-loop; and stale daemon snapshots must
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
    controller_receipt_action_class: str = "stateful"  # stateful | startup_bootloader | mail_delivery
    controller_receipt_reconciled: bool = False
    pending_cleared_after_receipt: bool = False
    stateful_postconditions_applied: bool = False
    control_blocker_written: bool = False
    control_blocker_lane: str = "none"  # none | control_plane_reissue | pm_repair_decision_required
    control_blocker_direct_retry_budget: int = 0
    control_blocker_resolved_by_reconciliation: bool = False
    pm_repair_action_queued: bool = False
    pm_repair_action_superseded: bool = False
    startup_reissue_budget_exhausted: bool = False
    startup_row_reconciled: bool = False
    startup_postcondition_satisfied: bool = False
    startup_reconciliation_owner: str = "none"  # none | startup_daemon | startup_bootloader_controller_receipt | generic_receipt
    generic_receipt_reconciler_touched_startup_row: bool = False
    unsupported_startup_receipt_action: bool = False
    startup_secondary_record_roles_started: bool = False
    startup_secondary_record_core_prompts_injected: bool = False
    startup_router_state_roles_started: bool = False
    startup_router_state_core_prompts_injected: bool = False
    startup_dual_ledger_folded: bool = False

    mail_delivery_receipt_claimed: bool = False
    mail_delivery_postcondition_required: bool = False
    mail_delivery_postcondition_applied: bool = False
    mail_delivery_packet_ledger_folded: bool = False
    mail_delivery_packet_released_to_role: bool = False
    mail_delivery_router_flag_synced: bool = False
    mail_delivery_unsupported_receipt: bool = False
    pm_mail_repair_decision_submitted: bool = False
    pm_mail_repair_decision_consumed: bool = False
    mail_delivery_repair_transaction_started: bool = False
    mail_delivery_reissue_queued: bool = False

    controller_boundary_artifact_exists: bool = False
    controller_boundary_artifact_valid: bool = False
    controller_boundary_action_reconciled: bool = False
    controller_boundary_scheduler_reconciled: bool = False
    controller_boundary_flags_synced: bool = False
    controller_boundary_reissued_after_reconcile: bool = False
    controller_boundary_action_returned_without_pending: bool = False
    controller_action_directory_scan_includes_temp_json: bool = False
    temp_controller_action_file_seen: bool = False
    temp_controller_action_file_renamed_before_read: bool = False
    temp_controller_action_file_read_attempted: bool = False
    temp_file_race_deferred_or_skipped: bool = False
    daemon_error_from_temp_action_file: bool = False
    runtime_writer_active: bool = False
    runtime_writer_stalled: bool = False
    runtime_settlement_waiting: bool = False
    runtime_settlement_progress_observed: bool = False
    queue_stop_reason: str = "none"  # none | barrier | no_action | pending_action_changed | max_actions_per_tick
    sleep_taken: bool = False
    immediate_tick_requested: bool = False

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
    controller_action_ledger, router_scheduler_ledger,
    controller_boundary_confirmation, role_output_ledger, canonical report
    artifacts, scoped event identities, daemon in-memory snapshot
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
        "router_scheduler_ledger",
        "startup/controller_boundary_confirmation.json",
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

    if (
        state.control_blocker_written
        and state.mail_delivery_unsupported_receipt
        and not state.pm_mail_repair_decision_submitted
        and not state.next_action_computed
    ):
        yield Transition(
            "pm_mail_delivery_repair_decision_submitted",
            _step(
                state,
                pm_mail_repair_decision_submitted=True,
                role_output_ledger_submitted=True,
                canonical_artifact_exists=True,
            ),
        )
        yield Transition(
            "daemon_returns_control_blocker_after_reconciliation",
            _step(state, next_action_computed=True),
        )
        return

    if (
        state.control_blocker_written
        and state.mail_delivery_unsupported_receipt
        and state.pm_mail_repair_decision_submitted
        and not state.pm_mail_repair_decision_consumed
    ):
        yield Transition(
            "daemon_consumes_pm_mail_delivery_decision_as_reissue",
            _step(
                state,
                role_output_reconciled=True,
                router_event_recorded=True,
                router_event_flag_synced=True,
                scoped_event_recorded=True,
                role_output_consumption_count=state.role_output_consumption_count + 1,
                role_wait_cleared_after_event=True,
                pm_mail_repair_decision_consumed=True,
                mail_delivery_repair_transaction_started=True,
                mail_delivery_reissue_queued=True,
                control_blocker_resolved_by_reconciliation=True,
                next_action_computed=True,
            ),
        )
        return

    if (
        state.startup_secondary_record_roles_started
        and state.startup_secondary_record_core_prompts_injected
        and not state.startup_dual_ledger_folded
        and not state.next_action_computed
    ):
        yield Transition(
            "daemon_folds_startup_role_flags_from_secondary_record",
            _step(
                state,
                startup_router_state_roles_started=True,
                startup_router_state_core_prompts_injected=True,
                startup_dual_ledger_folded=True,
            ),
        )
        return

    if (
        state.runtime_writer_active
        and not state.runtime_writer_stalled
        and not state.runtime_settlement_waiting
        and not state.next_action_computed
    ):
        yield Transition(
            "daemon_defers_reconciliation_for_active_runtime_writer",
            _step(state, runtime_settlement_waiting=True),
        )
        return

    if (
        state.runtime_writer_active
        and state.runtime_settlement_waiting
        and not state.runtime_settlement_progress_observed
        and not state.next_action_computed
    ):
        yield Transition(
            "daemon_observes_writer_progress_and_keeps_waiting",
            _step(state, runtime_settlement_progress_observed=True),
        )
        return

    if (
        state.runtime_writer_active
        and state.runtime_settlement_progress_observed
        and not state.next_action_computed
    ):
        yield Transition(
            "runtime_writer_finishes_before_next_action",
            _step(
                state,
                runtime_writer_active=False,
                runtime_settlement_waiting=False,
                runtime_settlement_progress_observed=False,
            ),
        )
        return

    if (
        state.controller_action_directory_scan_includes_temp_json
        and state.temp_controller_action_file_seen
        and state.temp_controller_action_file_renamed_before_read
        and not state.temp_file_race_deferred_or_skipped
        and not state.next_action_computed
    ):
        yield Transition(
            "daemon_skips_transient_controller_action_temp_file",
            _step(state, temp_file_race_deferred_or_skipped=True),
        )
        return

    if not state.role_output_ledger_submitted and state.pending_action_kind == "await_role_decision":
        if not state.startup_secondary_record_roles_started:
            yield Transition(
                "startup_role_flags_written_to_secondary_record_only",
                _step(
                    state,
                    startup_secondary_record_roles_started=True,
                    startup_secondary_record_core_prompts_injected=True,
                ),
            )
        if not state.temp_controller_action_file_seen:
            yield Transition(
                "daemon_sees_transient_controller_action_temp_file",
                _step(
                    state,
                    controller_action_directory_scan_includes_temp_json=True,
                    temp_controller_action_file_seen=True,
                    temp_controller_action_file_renamed_before_read=True,
                ),
            )
        if not state.runtime_writer_active:
            yield Transition(
                "daemon_observes_active_runtime_writer",
                _step(state, runtime_writer_active=True),
            )
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
                startup_reconciliation_owner="startup_bootloader_controller_receipt",
            ),
        )
        yield Transition(
            "daemon_reconciles_mail_delivery_receipt_to_packet_ledger",
            _step(
                state,
                pending_action_kind="none",
                pending_action_status="none",
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
                controller_receipt_action_class="mail_delivery",
                controller_receipt_reconciled=True,
                pending_cleared_after_receipt=True,
                stateful_postconditions_applied=True,
                mail_delivery_receipt_claimed=True,
                mail_delivery_postcondition_required=True,
                mail_delivery_postcondition_applied=True,
                mail_delivery_packet_ledger_folded=True,
                mail_delivery_packet_released_to_role=True,
                mail_delivery_router_flag_synced=True,
            ),
        )
        yield Transition(
            "daemon_blocks_unsupported_mail_delivery_receipt_before_next_action",
            _step(
                state,
                pending_action_kind="none",
                pending_action_status="none",
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
                controller_receipt_action_class="mail_delivery",
                controller_receipt_reconciled=True,
                pending_cleared_after_receipt=True,
                control_blocker_written=True,
                control_blocker_lane="pm_repair_decision_required",
                control_blocker_direct_retry_budget=2,
                mail_delivery_receipt_claimed=True,
                mail_delivery_postcondition_required=True,
                mail_delivery_unsupported_receipt=True,
            ),
        )
        yield Transition(
            "daemon_resolves_prior_startup_blocker_and_supersedes_pm_row",
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
                startup_reconciliation_owner="startup_bootloader_controller_receipt",
                control_blocker_written=True,
                control_blocker_lane="control_plane_reissue",
                control_blocker_direct_retry_budget=2,
                control_blocker_resolved_by_reconciliation=True,
                pm_repair_action_queued=True,
                pm_repair_action_superseded=True,
            ),
        )
        yield Transition(
            "controller_boundary_receipt_artifact_seen_with_stale_flags",
            _step(
                state,
                pending_action_kind="none",
                pending_action_status="none",
                controller_receipt_status="done",
                controller_receipt_payload_quality="complete",
                controller_receipt_action_class="controller_boundary",
                controller_receipt_reconciled=True,
                pending_cleared_after_receipt=True,
                stateful_postconditions_applied=True,
                controller_boundary_artifact_exists=True,
                controller_boundary_artifact_valid=True,
                controller_boundary_action_reconciled=True,
                controller_boundary_scheduler_reconciled=True,
                controller_boundary_flags_synced=False,
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

    if (
        state.controller_boundary_artifact_exists
        and state.controller_boundary_artifact_valid
        and state.controller_boundary_action_reconciled
        and state.controller_boundary_scheduler_reconciled
        and not state.controller_boundary_flags_synced
    ):
        yield Transition(
            "daemon_reclaims_controller_boundary_projection_from_artifact",
            _step(state, controller_boundary_flags_synced=True),
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

    if state.next_action_computed and state.queue_stop_reason == "none":
        yield Transition(
            "daemon_queue_stops_at_barrier_and_sleeps",
            _step(state, queue_stop_reason="barrier", sleep_taken=True),
        )
        yield Transition(
            "daemon_queue_budget_exhausted_requests_immediate_tick",
            _step(state, queue_stop_reason="max_actions_per_tick", immediate_tick_requested=True),
        )
        yield Transition(
            "daemon_queue_finds_no_action_and_sleeps",
            _step(state, queue_stop_reason="no_action", sleep_taken=True),
        )
        return

    if state.next_action_computed and state.queue_stop_reason != "none":
        yield Transition(
            "terminal_stop_after_reconciliation_and_sleep_policy_checked",
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
        "mail_delivery_receipt_without_packet_ledger_fold": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="mail_delivery",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            mail_delivery_receipt_claimed=True,
            mail_delivery_postcondition_required=True,
            mail_delivery_postcondition_applied=True,
            mail_delivery_packet_ledger_folded=False,
            mail_delivery_packet_released_to_role=False,
            mail_delivery_router_flag_synced=True,
            next_action_computed=True,
        ),
        "mail_delivery_flag_without_packet_release": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="mail_delivery",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            mail_delivery_receipt_claimed=True,
            mail_delivery_postcondition_required=True,
            mail_delivery_postcondition_applied=True,
            mail_delivery_packet_ledger_folded=True,
            mail_delivery_packet_released_to_role=False,
            mail_delivery_router_flag_synced=True,
            next_action_computed=True,
        ),
        "mail_delivery_pm_decision_left_unconsumed": replace(
            safe,
            pending_action_kind="await_role_decision",
            pending_action_status="waiting",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="mail_delivery",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            control_blocker_written=True,
            control_blocker_lane="pm_repair_decision_required",
            mail_delivery_receipt_claimed=True,
            mail_delivery_postcondition_required=True,
            mail_delivery_unsupported_receipt=True,
            pm_mail_repair_decision_submitted=True,
            pm_mail_repair_decision_consumed=False,
            role_output_ledger_submitted=True,
            canonical_artifact_exists=True,
            next_action_computed=True,
        ),
        "mail_delivery_reissue_without_repair_transaction": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="mail_delivery",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            control_blocker_written=True,
            control_blocker_lane="pm_repair_decision_required",
            mail_delivery_receipt_claimed=True,
            mail_delivery_postcondition_required=True,
            mail_delivery_unsupported_receipt=True,
            pm_mail_repair_decision_submitted=True,
            pm_mail_repair_decision_consumed=True,
            mail_delivery_reissue_queued=True,
            mail_delivery_repair_transaction_started=False,
            control_blocker_resolved_by_reconciliation=True,
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
        "startup_role_flags_left_in_secondary_record": replace(
            safe,
            startup_secondary_record_roles_started=True,
            startup_secondary_record_core_prompts_injected=True,
            startup_router_state_roles_started=False,
            startup_router_state_core_prompts_injected=False,
            startup_dual_ledger_folded=False,
            next_action_computed=True,
        ),
        "startup_roles_started_without_core_prompt_router_flag": replace(
            safe,
            startup_secondary_record_roles_started=True,
            startup_secondary_record_core_prompts_injected=True,
            startup_router_state_roles_started=True,
            startup_router_state_core_prompts_injected=False,
            startup_dual_ledger_folded=False,
            next_action_computed=True,
        ),
        "temp_controller_action_file_read_as_real_action": replace(
            safe,
            controller_action_directory_scan_includes_temp_json=True,
            temp_controller_action_file_seen=True,
            temp_controller_action_file_renamed_before_read=True,
            temp_controller_action_file_read_attempted=True,
            temp_file_race_deferred_or_skipped=False,
            daemon_error_from_temp_action_file=True,
        ),
        "temp_controller_action_file_error_kills_daemon": replace(
            safe,
            daemon_alive=False,
            controller_action_directory_scan_includes_temp_json=True,
            temp_controller_action_file_seen=True,
            temp_controller_action_file_renamed_before_read=True,
            temp_controller_action_file_read_attempted=True,
            temp_file_race_deferred_or_skipped=False,
            daemon_error_from_temp_action_file=True,
        ),
        "active_runtime_writer_false_control_blocker": replace(
            safe,
            runtime_writer_active=True,
            runtime_writer_stalled=False,
            runtime_settlement_waiting=False,
            control_blocker_written=True,
            next_action_computed=True,
        ),
        "active_runtime_writer_stops_daemon": replace(
            safe,
            daemon_alive=False,
            runtime_writer_active=True,
            runtime_writer_stalled=False,
            runtime_settlement_waiting=False,
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
            control_blocker_lane="pm_repair_decision_required",
            next_action_computed=True,
        ),
        "startup_missing_postcondition_pm_lane_before_reissue": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="startup_bootloader",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            startup_row_reconciled=False,
            startup_postcondition_satisfied=False,
            generic_receipt_reconciler_touched_startup_row=True,
            unsupported_startup_receipt_action=True,
            control_blocker_written=True,
            control_blocker_lane="pm_repair_decision_required",
            control_blocker_direct_retry_budget=0,
            startup_reissue_budget_exhausted=False,
            next_action_computed=True,
        ),
        "startup_blocker_not_resolved_after_success": replace(
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
            control_blocker_written=True,
            control_blocker_lane="control_plane_reissue",
            control_blocker_direct_retry_budget=2,
            control_blocker_resolved_by_reconciliation=False,
            next_action_computed=True,
        ),
        "startup_reconciled_action_queued_pm_repair": replace(
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
            control_blocker_written=True,
            control_blocker_lane="control_plane_reissue",
            control_blocker_direct_retry_budget=2,
            control_blocker_resolved_by_reconciliation=True,
            pm_repair_action_queued=True,
            pm_repair_action_superseded=False,
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
            control_blocker_lane="pm_repair_decision_required",
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
        "controller_boundary_reconciled_artifact_left_flags_false": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="controller_boundary",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            controller_boundary_artifact_exists=True,
            controller_boundary_artifact_valid=True,
            controller_boundary_action_reconciled=True,
            controller_boundary_scheduler_reconciled=True,
            controller_boundary_flags_synced=False,
            next_action_computed=True,
        ),
        "controller_boundary_reissued_after_reconciled_artifact": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="controller_boundary",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            controller_boundary_artifact_exists=True,
            controller_boundary_artifact_valid=True,
            controller_boundary_action_reconciled=True,
            controller_boundary_scheduler_reconciled=True,
            controller_boundary_flags_synced=False,
            controller_boundary_reissued_after_reconcile=True,
            next_action_computed=True,
        ),
        "controller_boundary_returned_without_pending_action": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="controller_boundary",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            controller_boundary_artifact_exists=True,
            controller_boundary_artifact_valid=True,
            controller_boundary_action_reconciled=True,
            controller_boundary_scheduler_reconciled=True,
            controller_boundary_flags_synced=False,
            controller_boundary_action_returned_without_pending=True,
            next_action_computed=True,
        ),
        "controller_boundary_action_scheduler_disagree": replace(
            safe,
            pending_action_kind="none",
            pending_action_status="none",
            controller_receipt_status="done",
            controller_receipt_payload_quality="complete",
            controller_receipt_action_class="controller_boundary",
            controller_receipt_reconciled=True,
            pending_cleared_after_receipt=True,
            stateful_postconditions_applied=True,
            controller_boundary_artifact_exists=True,
            controller_boundary_artifact_valid=True,
            controller_boundary_action_reconciled=True,
            controller_boundary_scheduler_reconciled=False,
            controller_boundary_flags_synced=False,
            next_action_computed=True,
        ),
        "daemon_sleeps_after_queue_budget_exhausted": replace(
            safe,
            next_action_computed=True,
            queue_stop_reason="max_actions_per_tick",
            sleep_taken=True,
            immediate_tick_requested=False,
        ),
        "daemon_fast_loops_after_barrier": replace(
            safe,
            next_action_computed=True,
            queue_stop_reason="barrier",
            sleep_taken=False,
            immediate_tick_requested=True,
        ),
        "daemon_fast_loops_after_no_action": replace(
            safe,
            next_action_computed=True,
            queue_stop_reason="no_action",
            sleep_taken=False,
            immediate_tick_requested=True,
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
    durable_controller_boundary_exists = (
        state.controller_boundary_artifact_exists
        or state.controller_boundary_action_reconciled
        or state.controller_boundary_scheduler_reconciled
    )
    durable_evidence_exists = (
        durable_receipt_exists or durable_role_output_exists or durable_controller_boundary_exists
    )

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
        and not state.control_blocker_written
    ):
        failures.append("stateful Controller receipt was marked done without applying Router postconditions")

    if (
        state.startup_secondary_record_roles_started
        and state.startup_secondary_record_core_prompts_injected
        and state.next_action_computed
        and not (
            state.startup_router_state_roles_started
            and state.startup_router_state_core_prompts_injected
            and state.startup_dual_ledger_folded
        )
    ):
        failures.append("startup role flags stayed in secondary startup record without Router-state fold")

    if state.startup_router_state_roles_started and not state.startup_router_state_core_prompts_injected:
        failures.append("startup roles_started Router flag was synced without role_core_prompts_injected")

    if (
        state.startup_dual_ledger_folded
        and not (
            state.startup_router_state_roles_started
            and state.startup_router_state_core_prompts_injected
        )
    ):
        failures.append("startup role flag fold was marked complete while Router flags were still incomplete")

    if (
        state.controller_action_directory_scan_includes_temp_json
        and state.temp_controller_action_file_seen
        and state.temp_controller_action_file_renamed_before_read
        and state.temp_controller_action_file_read_attempted
        and not state.temp_file_race_deferred_or_skipped
    ):
        failures.append("daemon tried to read a transient Controller action temp file")

    if state.daemon_error_from_temp_action_file or (
        not state.daemon_alive
        and state.temp_controller_action_file_seen
        and state.temp_controller_action_file_renamed_before_read
        and not state.temp_file_race_deferred_or_skipped
    ):
        failures.append("transient Controller action temp file race stopped the daemon")

    if state.runtime_writer_active and not state.runtime_writer_stalled and state.control_blocker_written:
        failures.append("active runtime writer was converted into a control blocker before settlement")

    if state.runtime_writer_active and not state.runtime_writer_stalled and not state.daemon_alive:
        failures.append("active runtime writer stopped the daemon before settlement")

    if state.controller_receipt_action_class == "mail_delivery":
        mail_fold_complete = (
            state.mail_delivery_postcondition_applied
            and state.mail_delivery_packet_ledger_folded
            and state.mail_delivery_packet_released_to_role
            and state.mail_delivery_router_flag_synced
        )
        if (
            state.mail_delivery_receipt_claimed
            and state.mail_delivery_postcondition_required
            and state.next_action_computed
            and not mail_fold_complete
            and not state.control_blocker_written
        ):
            failures.append("mail delivery receipt reached next action without packet ledger fold or control blocker")
        if (
            state.mail_delivery_postcondition_applied
            and not mail_fold_complete
        ):
            failures.append("mail delivery postcondition was applied without moving the packet ledger and Router flag together")
        if (
            state.mail_delivery_router_flag_synced
            and not state.mail_delivery_packet_released_to_role
        ):
            failures.append("mail delivery Router flag was set while the packet still belonged to Controller")
        if (
            state.control_blocker_written
            and state.mail_delivery_unsupported_receipt
            and state.pm_mail_repair_decision_submitted
            and state.next_action_computed
            and not state.pm_mail_repair_decision_consumed
        ):
            failures.append("PM mail delivery repair decision stayed only in durable storage")
        if (
            state.pm_mail_repair_decision_consumed
            and state.mail_delivery_reissue_queued
            and not state.mail_delivery_repair_transaction_started
        ):
            failures.append("mail delivery reissue was queued without a repair transaction")
        if (
            state.pm_mail_repair_decision_consumed
            and state.mail_delivery_repair_transaction_started
            and not state.mail_delivery_reissue_queued
        ):
            failures.append("mail delivery repair transaction did not queue the reissue")

    if state.controller_receipt_action_class == "startup_bootloader":
        if state.startup_row_reconciled and not state.startup_postcondition_satisfied:
            failures.append("startup bootloader row was reconciled without its postcondition")
        if state.startup_row_reconciled and state.startup_reconciliation_owner not in {
            "startup_daemon",
            "startup_bootloader_controller_receipt",
        }:
            failures.append("startup bootloader row was reconciled by the wrong owner")
        if (
            state.startup_row_reconciled
            and state.control_blocker_written
            and not state.control_blocker_resolved_by_reconciliation
        ):
            failures.append("startup bootloader row produced a control blocker after it was already reconciled")
        if (
            state.control_blocker_written
            and not state.startup_postcondition_satisfied
            and not state.startup_reissue_budget_exhausted
            and (
                state.control_blocker_lane != "control_plane_reissue"
                or state.control_blocker_direct_retry_budget < 1
            )
        ):
            failures.append(
                "startup bootloader missing postcondition was sent to PM before mechanical reissue budget was exhausted"
            )
        if (
            state.startup_postcondition_satisfied
            and state.control_blocker_written
            and not state.control_blocker_resolved_by_reconciliation
        ):
            failures.append("startup bootloader blocker stayed active after its postcondition was reconciled")
        if state.startup_postcondition_satisfied and state.pm_repair_action_queued:
            if not state.pm_repair_action_superseded:
                failures.append("PM repair action was queued after startup bootloader postcondition reconciliation")
        if state.pm_repair_action_superseded and not state.control_blocker_resolved_by_reconciliation:
            failures.append("PM repair action was superseded before the source blocker was resolved")
        if (
            state.generic_receipt_reconciler_touched_startup_row
            and state.unsupported_startup_receipt_action
            and state.startup_postcondition_satisfied
            and state.control_blocker_written
            and not state.control_blocker_resolved_by_reconciliation
        ):
            failures.append("unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied")
        if state.next_action_computed and state.controller_receipt_status == "done" and not (
            state.startup_row_reconciled or state.control_blocker_written
        ):
            failures.append("startup bootloader receipt reached next action without startup reconciliation or a real blocker")

    if state.controller_receipt_action_class == "controller_boundary":
        boundary_projection_complete = (
            state.controller_boundary_artifact_exists
            and state.controller_boundary_artifact_valid
            and state.controller_receipt_status == "done"
            and state.controller_receipt_reconciled
        )
        if boundary_projection_complete and (
            state.controller_boundary_action_reconciled
            != state.controller_boundary_scheduler_reconciled
        ):
            failures.append("Controller boundary action and scheduler reconciliation disagreed")
        if (
            boundary_projection_complete
            and state.controller_boundary_action_reconciled
            and state.controller_boundary_scheduler_reconciled
            and state.next_action_computed
            and not state.controller_boundary_flags_synced
        ):
            failures.append("Controller boundary confirmation was reconciled but Router flags stayed false")
        if (
            boundary_projection_complete
            and state.controller_boundary_reissued_after_reconcile
        ):
            failures.append("Controller boundary confirmation was reissued after valid reconciled evidence")
        if (
            boundary_projection_complete
            and state.controller_boundary_action_returned_without_pending
        ):
            failures.append("Controller boundary action was exposed while pending_action was empty")

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

    if state.queue_stop_reason == "max_actions_per_tick" and state.sleep_taken:
        failures.append("daemon slept after queue budget exhaustion instead of starting the next tick immediately")

    if state.queue_stop_reason in {"barrier", "no_action", "pending_action_changed"} and state.immediate_tick_requested:
        failures.append("daemon fast-looped after a real wait instead of sleeping")

    if (
        state.next_action_computed
        and state.queue_stop_reason == "max_actions_per_tick"
        and not state.immediate_tick_requested
    ):
        failures.append("daemon queue budget exhaustion did not request an immediate next tick")

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
    _invariant("startup_role_flags_fold_from_secondary_record", "startup role flags stayed in secondary startup record without Router-state fold"),
    _invariant("startup_role_flags_fold_atomically", "startup roles_started Router flag was synced without role_core_prompts_injected"),
    _invariant("startup_role_flag_fold_completion_requires_router_flags", "startup role flag fold was marked complete while Router flags were still incomplete"),
    _invariant("controller_action_scan_skips_temp_json", "daemon tried to read a transient Controller action temp file"),
    _invariant("temp_controller_action_race_cannot_stop_daemon", "transient Controller action temp file race stopped the daemon"),
    _invariant("active_runtime_writer_defers_blocker", "active runtime writer was converted into a control blocker before settlement"),
    _invariant("active_runtime_writer_cannot_stop_daemon", "active runtime writer stopped the daemon before settlement"),
    _invariant("mail_delivery_receipt_folds_or_blocks", "mail delivery receipt reached next action without packet ledger fold or control blocker"),
    _invariant("mail_delivery_postcondition_folds_packet_ledger", "mail delivery postcondition was applied without moving the packet ledger and Router flag together"),
    _invariant("mail_delivery_flag_requires_packet_release", "mail delivery Router flag was set while the packet still belonged to Controller"),
    _invariant("pm_mail_delivery_decision_consumed", "PM mail delivery repair decision stayed only in durable storage"),
    _invariant("mail_delivery_reissue_has_repair_transaction", "mail delivery reissue was queued without a repair transaction"),
    _invariant("mail_delivery_repair_transaction_queues_reissue", "mail delivery repair transaction did not queue the reissue"),
    _invariant("startup_bootloader_reconciles_with_postcondition", "startup bootloader row was reconciled without its postcondition"),
    _invariant("startup_bootloader_reconciliation_owner", "startup bootloader row was reconciled by the wrong owner"),
    _invariant("startup_bootloader_no_false_pm_blocker_after_reconciled", "startup bootloader row produced a control blocker after it was already reconciled"),
    _invariant("startup_missing_postcondition_uses_mechanical_reissue_budget", "startup bootloader missing postcondition was sent to PM before mechanical reissue budget was exhausted"),
    _invariant("startup_success_resolves_same_action_blocker", "startup bootloader blocker stayed active after its postcondition was reconciled"),
    _invariant("startup_success_prevents_pm_repair_action_queue", "PM repair action was queued after startup bootloader postcondition reconciliation"),
    _invariant("unsupported_startup_receipt_not_pm_repair_after_success", "unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied"),
    _invariant("startup_bootloader_receipt_must_be_reconciled", "startup bootloader receipt reached next action without startup reconciliation or a real blocker"),
    _invariant("controller_boundary_action_scheduler_agree", "Controller boundary action and scheduler reconciliation disagreed"),
    _invariant("controller_boundary_reconciled_projection_updates_flags", "Controller boundary confirmation was reconciled but Router flags stayed false"),
    _invariant("controller_boundary_not_reissued_after_reconciled_evidence", "Controller boundary confirmation was reissued after valid reconciled evidence"),
    _invariant("controller_boundary_action_requires_pending_action", "Controller boundary action was exposed while pending_action was empty"),
    _invariant("incomplete_stateful_receipt_blocks", "incomplete stateful Controller receipt was accepted without a control blocker"),
    _invariant("blocked_receipt_surfaces_blocker", "blocked Controller receipt was not surfaced as a control blocker"),
    _invariant("role_output_storage_becomes_router_event", "submitted expected role output was left only in durable storage"),
    _invariant("canonical_artifact_flag_sync", "canonical role-output artifact existed without synced Router event flag"),
    _invariant("role_wait_cleared_after_event", "expected role wait remained current after Router recorded the role output"),
    _invariant("role_output_consumed_once", "role output durable evidence was consumed more than once"),
    _invariant("stale_daemon_snapshot_cannot_overwrite_evidence", "daemon saved a stale router_state snapshot over newer durable role output"),
    _invariant("invalid_role_output_not_accepted", "invalid or unauthorized role output was accepted as a Router event"),
    _invariant("queue_budget_exhaustion_skips_sleep", "daemon slept after queue budget exhaustion instead of starting the next tick immediately"),
    _invariant("real_waits_do_not_fast_loop", "daemon fast-looped after a real wait instead of sleeping"),
    _invariant("queue_budget_exhaustion_requests_next_tick", "daemon queue budget exhaustion did not request an immediate next tick"),
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
    "next_states",
]
