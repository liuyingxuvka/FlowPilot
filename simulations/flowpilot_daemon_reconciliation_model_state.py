"""FlowGuard model for FlowPilot daemon durable reconciliation.

Risk intent brief:
- Review the second-layer Router/daemon failure class where durable evidence
  exists on disk but the daemon keeps returning stale work.
- Model-critical durable state: Controller action receipts, stateful
  Controller-action postconditions, Controller-boundary confirmation artifacts,
  Controller action rows, Router scheduler rows, packet ledgers, mail delivery
  flags, startup system-card bundle ACK returns, startup secondary-state role
  flags, role-output ledgers, canonical report artifacts, Router event flags,
  transient Controller action temp files, stale in-memory daemon snapshots, and
  the one-tick reconciliation barrier before next-action computation.
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
  waiting on the same role; a resolved PM system-card bundle ACK must close the
  matching wait row and immediately expose the real user-intake packet dispatch
  if that packet is still held by Controller; expected valid role outputs must
  become Router events exactly once; canonical artifacts and flags must not
  diverge; a valid Controller-boundary artifact plus reconciled
  receipt/action/scheduler rows must rebuild Router flags before any next
  action is exposed; startup-daemon bootloader rows must have one
  reconciliation owner, startup postcondition misses must stay on the
  mechanical reissue lane until that budget is exhausted, and any blocker for
  the same startup row must be resolved before PM repair work can be queued
  once the postcondition is satisfied; daemon startup role flags written into
  the secondary startup record must be folded into Router state atomically
  before next-action computation; Controller action directory scans must skip
  transient `.tmp-*.json` files and transient file disappearance must never
  stop the daemon; daemon
  queue budget exhaustion must immediately start the next tick instead of
  sleeping; foreground start commands that collide with a fresh runtime-state
  writer must wait for settlement and return live daemon status instead of
  failing; startup Controller receipts must fold action, scheduler, pending,
  bootstrap, and run-state projections under one owner instead of depending on
  a later apply path; real waits must not busy-loop; and stale daemon snapshots
  must never erase newer durable evidence.
"""

from __future__ import annotations


from dataclasses import dataclass
from typing import NamedTuple






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

    pending_action_kind: str = "await_role_decision"  # none | await_role_decision | rehydrate_role_bindings
    pending_action_status: str = "waiting"  # none | pending | waiting | done | blocked
    pending_action_returned_again: bool = False
    next_action_computed: bool = False
    computed_before_reconciliation: bool = False

    controller_receipt_status: str = "none"  # none | done | blocked
    controller_receipt_payload_quality: str = "none"  # none | complete | incomplete
    controller_receipt_action_class: str = "stateful"  # stateful | startup_bootloader | mail_delivery | controller_boundary
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
    startup_bootloader_receipt_kind: str = "generic"  # generic | native_startup_intake
    unsupported_startup_receipt_action: bool = False
    startup_receipt_apply_split: bool = False
    startup_receipt_requires_apply_to_advance: bool = False
    startup_receipt_single_owner_folded: bool = False
    startup_receipt_replay_is_noop: bool = False
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

    startup_card_bundle_ack_resolved: bool = False
    startup_card_bundle_wait_action_reconciled: bool = False
    startup_card_bundle_wait_scheduler_reconciled: bool = False
    startup_card_bundle_ack_completion_normalized: bool = False
    user_intake_router_owned: bool = False
    user_intake_packet_with_controller: bool = False
    user_intake_packet_to_pm: bool = False
    user_intake_released_to_pm: bool = False
    user_intake_release_count: int = 0
    user_intake_delivery_action_queued: bool = False
    unrelated_controller_action_repeated_after_ack: bool = False

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
    foreground_start_command_active: bool = False
    foreground_start_reads_runtime_during_writer: bool = False
    foreground_start_waits_for_runtime_writer: bool = False
    foreground_start_retries_after_writer_finishes: bool = False
    foreground_start_run_allocation_count: int = 0
    foreground_start_completed_actions_before_writer: bool = False
    foreground_start_completed_actions_preserved: bool = False
    foreground_start_returns_live_daemon_status: bool = False
    foreground_start_fatal_from_active_writer: bool = False
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
