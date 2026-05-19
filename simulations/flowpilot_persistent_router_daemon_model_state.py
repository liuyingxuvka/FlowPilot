"""State objects for the FlowPilot persistent Router daemon model.

FlowGuard model for FlowPilot persistent Router daemon control.

Risk intent brief:
- Prevent FlowPilot from stalling when a role writes the expected ACK/report
  file after Controller has stopped at an ordinary wait boundary.
- Preserve the existing authority split: Router decides route state,
  Controller executes host actions from a durable checklist, and roles only
  write mailbox evidence.
- Model-critical durable state: daemon lock/status, one-second daemon tick,
  mailbox evidence, ACK consumption, Controller action ledger entries,
  external-event wait row closure, Controller receipts, stateful Controller
  postcondition evidence, Router scheduler ledger parseability, atomic durable
  ledger writes, daemon status/lock/process consistency, heartbeat/manual
  resume recovery, role cohort liveness, missing-deliverable repair
  issue/failure counts, and terminal cleanup.
- Adversarial branches include formal startup skipping or failing daemon
  launch before Controller core load, no daemon at a wait, duplicate Router
  writers, duplicate ACK observation, Router marking Controller work done
  without a receipt, Controller acting as the normal Router metronome,
  daemon-scheduled startup rows whose done receipts do not update bootstrap
  flags, clear bootstrap pending_action, reconcile the Router row, and schedule
  the next startup row,
  Controller stopping at ordinary waits, foreground Controller ending while a
  live daemon-owned role wait is active, foreground Controller ending while
  the daemon is live but no Controller action is ready, heartbeat starting a
  second live daemon, Router scheduler ledger corruption from partial writes,
  monitor current-work projection dropping active packet holders or internal
  reconciliation owners after `pending_action` is cleared,
  treating a fresh runtime write lock as corruption instead of a one-tick
  defer, treating the daemon's own stale write-lock sentinel as another live
  writer forever, swallowing lock cleanup failures without diagnostic evidence,
  daemon status claiming active after an error lock or missing process, and
  terminal stop leaving daemon/Controller/roles active.
- Hard invariants: formal startup must start a live one-second Router daemon
  before Controller core loads; active ordinary waits have a live daemon; one
  daemon writer owns a run; mailbox evidence is consumed at most once;
  recorded external events close every matching durable wait row before Router
  opens the next wait;
  Controller-required work is done only with a Controller receipt; stateful
  Controller receipts such as startup boundary confirmation must either have
  Router-visible postcondition evidence before Router marks the action done, or
  remain incomplete with a bounded Controller deliverable repair row;
  Router may count a repair attempt as failed only after the matching
  Controller repair receipt is received and invalid, and must not write a
  budget-exhausted blocker while a repair action is still pending;
  receipt reconciliation must also advance the matching Router-owned internal
  fact, and daemon-scheduled startup receipts must advance the bootstrap flag,
  clear bootstrap pending_action, and reconcile the Router scheduler row, so the
  same Controller action is not reissued forever; Controller
  follows the daemon-owned ledger instead of manually ticking the Router during
  normal runtime; Controller stays attached to the ledger during all
  nonterminal daemon-live runtime, processes pending executable Controller
  actions, and keeps a foreground standby loop active during ordinary
  daemon-owned role waits; monitor current-work projection names active packet
  holders, passive reconciliation owners, and internal Router/Controller work
  even when the legacy wait target is null; Router/Controller durable ledgers stay valid JSON
  after every write, fresh in-progress write locks defer daemon progress
  instead of surfacing as corruption, self-owned stale write locks are cleared
  only after safe artifact checks and diagnostic evidence, durable ledgers are
  written atomically, and daemon active status never contradicts an error lock
  or missing process;
  heartbeat restarts only dead/stale daemon state; and terminal stop disables
  daemon, Controller, heartbeat, roles, and route work.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import NamedTuple

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
    daemon_lock_state: str = "none"  # none | live | stale | duplicate | error
    daemon_writer_count: int = 0
    daemon_tick_seconds: int = 0
    router_scheduler_ledger_valid_json: bool = True
    controller_action_ledger_valid_json: bool = True
    runtime_ledger_write_lock_fresh: bool = False
    runtime_ledger_write_lock_stale: bool = False
    runtime_ledger_write_lock_owner: str = "none"  # none | self | live | dead | unknown
    runtime_write_lock_target_valid_json: bool = field(default=True, compare=False)
    runtime_write_lock_tmp_file_present: bool = field(default=False, compare=False)
    daemon_deferred_for_runtime_ledger_write: bool = False
    nested_wait_status_write_lock: bool = field(default=False, compare=False)
    daemon_deferred_after_nested_write_lock: bool = field(default=False, compare=False)
    self_owned_write_lock_takeover_recorded: bool = field(default=False, compare=False)
    self_owned_write_lock_recovery_rejoined_flow: bool = field(default=False, compare=False)
    dead_owner_write_lock_takeover_recorded: bool = False
    writer_died_while_holding_runtime_lock: bool = False
    dead_owner_recovery_rejoined_flow: bool = False
    runtime_write_lock_mechanical_settlement_recorded: bool = field(default=False, compare=False)
    runtime_write_lock_promoted_to_pm_semantic_blocker: bool = field(default=False, compare=False)
    runtime_write_lock_cleanup_failure_recorded: bool = field(default=False, compare=False)
    runtime_write_lock_cleanup_error_swallowed: bool = field(default=False, compare=False)
    durable_ledger_writes_atomic: bool = True
    router_scheduler_single_writer: bool = True
    daemon_status_active_after_lock_error: bool = False
    daemon_status_active_without_process: bool = False
    daemon_crashed_after_ledger_decode_error: bool = False
    controller_core_loaded: bool = False
    startup_bootstrap_pending_action_open: bool = False
    startup_controller_receipt_present: bool = False
    startup_controller_receipt_consumed: bool = False
    startup_bootstrap_flag_current: bool = False
    startup_router_row_reconciled: bool = False
    startup_next_row_scheduled_after_receipt: bool = False
    startup_row_scheduled_after_terminal_fence: bool = False
    startup_same_action_reissue_count: int = 0
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
    current_wait: str = "none"  # none | ack | report | controller_receipt | controller_local | user | terminal
    event_wait_action_open: bool = False
    external_event_recorded: bool = False
    external_event_matches_wait: bool = False
    event_wait_closed_by_router: bool = False
    stale_event_wait_row_open: bool = False
    next_wait_opened_before_event_wait_closed: bool = False
    controller_closed_event_wait: bool = False
    wait_target_metadata_present: bool = False
    wait_target_names_role: bool = False
    wait_target_expected_evidence_visible: bool = False
    wait_target_reminder_text_present: bool = False
    wait_target_reminder_controller_action_ready: bool = False
    wait_target_reminder_receipt_recorded: bool = False
    wait_target_reminder_updates_wait_metadata: bool = False
    ack_wait_age_minutes: int = 0
    ack_wait_reminder_sent: bool = False
    ack_wait_blocker_recorded: bool = False
    report_wait_age_minutes: int = 0
    report_reminder_sent: bool = False
    liveness_check_required: bool = False
    liveness_probe_fresh: bool = False
    liveness_probe_outcome: str = "none"  # none | working | lost
    stale_liveness_cached_as_truth: bool = False
    role_liveness_blocker_recorded: bool = False
    controller_local_self_audit_done: bool = False
    controller_local_blocker_recorded: bool = False
    controller_reminded_itself: bool = False
    legacy_waiting_for_role_null: bool = False
    active_packet_holder: str = ""
    packet_holder_projection_needed: bool = False
    passive_reconciliation_wait_open: bool = False
    router_internal_projection_needed: bool = False
    current_work_owner_kind: str = "none"  # none | role | controller | router | user
    current_work_owner_key: str = ""
    current_work_task_visible: bool = False
    current_work_source: str = "none"
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
    controller_action_requires_stateful_postcondition: bool = False
    controller_stateful_postcondition_evidence_written: bool = False
    controller_boundary_confirmation_written: bool = False
    controller_role_confirmed: bool = False
    controller_missing_deliverable_repair_pending: bool = False
    controller_missing_deliverable_repair_attempts: int = 0
    controller_missing_deliverable_repair_failed_receipts: int = 0
    controller_missing_deliverable_pending_attempt: int = 0
    controller_missing_deliverable_blocker_recorded: bool = False
    controller_missing_deliverable_escalated_before_budget: bool = False
    router_cleared_stateful_receipt_without_postcondition_evidence: bool = False
    router_internal_action_fact_current: bool = False
    router_internal_fact_updated_from_receipt: bool = False
    router_cleared_pending_without_internal_fact: bool = False
    same_controller_action_reissue_count: int = 0
    heartbeat_woke: bool = False
    heartbeat_started_second_daemon: bool = False
    heartbeat_restarted_dead_daemon: bool = False
    heartbeat_restored_controller: bool = False
    heartbeat_restored_roles: bool = False
    heartbeat_binding_scheduled_after_terminal_fence: bool = False
    stop_requested: bool = False
    terminal_fence_written: bool = False
    terminal_controller_cleanup_best_effort_failed: bool = False
    terminal_projection_refreshed: bool = False
    terminal_next_step_cleared: bool = False
    route_work_allowed: bool = False


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _step(state: State, **changes: object) -> State:
    return replace(state, **changes)
