"""FlowGuard model for FlowPilot two-table async Router scheduling.

Risk purpose:
- Uses FlowGuard (https://github.com/liuyingxuvka/FlowGuard) to review the
  FlowPilot rule that Router owns scheduling in a Router-only table while
  Controller receives simple executable rows in the Controller action table.
- Guards against startup remaining a one-row-at-a-time special case, Controller
  inheriting Router dependency complexity, duplicate queued side effects after
  daemon retries, Reviewer startup fact review starting before startup-scope
  reconciliation, foreground Controller waits becoming an empty/complete plan,
  Controller forgetting top-to-bottom row order during long ledgers, startup
  host/UI/role/heartbeat work happening before the daemon becomes the driver,
  a daemon that starts but only waits for Controller core instead of driving
  startup, Controller receipts that leave bootstrap `pending_action` stale and
  reissue the same startup row forever, treating a fresh runtime write lock as
  ledger corruption instead of waiting for the next tick, PM startup activation
  gaining a redundant global ACK gate, and cross-ledger drift where a durable
  single-card ACK resolution leaves the matching Controller passive wait or
  Router scheduler row stuck as waiting.
- Update and run this model whenever Router daemon queue filling, Controller
  action ledger schema, startup pre-review gating, or card ACK reconciliation
  behavior changes.
- Companion check command:
  `python simulations/run_flowpilot_two_table_async_scheduler_checks.py`.

Risk intent brief:
- Protected harm: the Router appears async but still waits on Controller rows
  that do not block the next work, or it advances gates without reconciling the
  current scope.
- Model-critical state: Router scheduler rows, Controller rows, daemon tick,
  barriers, receipts, postconditions, startup prep cards/ACKs, Reviewer fact
  review, PM activation ACK semantics, and durable ledger file integrity.
- Adversarial branches: hidden dependency metadata in Controller rows, retry
  duplicate side effects, Reviewer review before startup cleanup, route work
  before PM activation, daemon enqueue past a real barrier, missing table-local
  Controller prompt, startup UI/roles/heartbeat before daemon ownership,
  pre-Controller-core daemon idling, daemon-scheduled startup rows whose done
  receipts do not update bootstrap flags or clear bootstrap pending_action,
  startup banner/display/heartbeat/role-slot obligations that still behave as
  global queue barriers, role-dependent startup work queued before role slots
  are ready, true barriers accidentally demoted to nonblocking obligations,
  startup obligations reconciled without Router-visible proof, reconciled
  scheduler rows downgraded by later receipt sync,
  single-card ACK returns resolved in the return ledger while the matching
  Controller wait or Router scheduler row remains unreconciled,
  scheduler ledger partial writes that leave invalid JSON without a fresh write
  lock, fresh write-lock reads reported as corruption instead of deferred,
  standby completion after one monitor check, foreground closure while
  FlowPilot is still running, standby ignoring new Controller work, and
  redundant PM activation global join.
- Hard invariants: Router and Controller tables stay separate; daemon enqueues
  independent rows until barrier; broad mechanics are not barriers unless the
  action is a true dependency wall; barriers stop enqueueing; startup banner,
  heartbeat, and display/status are parallel obligations; startup role-slot
  spawn is only a local dependency; done receipts need
  required Router-visible postconditions before reconciliation; startup review
  uses current-scope reconciliation; startup external actions are daemon-owned
  after the minimal run shell exists; the Controller action ledger carries a
  compact top-to-bottom table prompt; ledger writes are atomic and leave both
  table files parseable after every daemon/controller write; Router scheduler
  ledger remains Router-single-writer; daemon-scheduled startup receipts must
  update the matching bootstrap flag, clear bootstrap pending_action, reconcile
  the Router row, and compute the next startup row unless a real barrier is
  reached;
  single-card ACK settlement must update the return ledger, Controller
  passive-wait row, and Router scheduler row together;
  live waits keep a continuous Controller
  standby row and Codex-plan sync duty; running FlowPilot keeps foreground
  Controller attached; PM activation uses same-role ACK only.
- Blindspot: this is a focused control-plane model. Runtime tests must still
  exercise concrete Router actions, ledgers, receipts, and install sync.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, NamedTuple

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


ASYNC_STARTUP_ROWS_UNTIL_BARRIER = "async_startup_rows_until_barrier"
STARTUP_DAEMON_FIRST_DRIVER = "startup_daemon_first_driver"
CONTROLLER_TABLE_SIMPLE_ROUTER_TABLE_COMPLEX = "controller_table_simple_router_table_complex"
STATEFUL_RECEIPT_RECONCILED_WITH_POSTCONDITION = "stateful_receipt_reconciled_with_postcondition"
STARTUP_REVIEW_WAITS_FOR_CURRENT_SCOPE_RECONCILIATION = "startup_review_waits_for_current_scope_reconciliation"
PM_ACTIVATION_SAME_ROLE_ACK_ONLY = "pm_activation_same_role_ack_only"
CONTINUOUS_STANDBY_ROW_DURING_LIVE_WAIT = "continuous_standby_row_during_live_wait"
PASSIVE_WAIT_STATUS_NOT_CONTROLLER_WORK = "passive_wait_status_not_controller_work"
STANDBY_REENTERS_TOP_DOWN_ON_NEW_WORK = "standby_reenters_top_down_on_new_work"
NO_OUTPUT_WAIT_REISSUES_BEFORE_RECOVERY = "no_output_wait_reissues_before_recovery"
UNAVAILABLE_WAIT_USES_ROLE_RECOVERY = "unavailable_wait_uses_role_recovery"
TRANSIENT_SCHEDULER_WRITE_LOCK_WAITS = "transient_scheduler_write_lock_waits"
STARTUP_BOOTLOADER_RECEIPT_CONSUMES_PENDING_AND_ADVANCES = (
    "startup_bootloader_receipt_consumes_pending_and_advances"
)
PARALLEL_STARTUP_OBLIGATIONS_QUEUE_UNRELATED_WORK = "parallel_startup_obligations_queue_unrelated_work"
STARTUP_ROLE_SLOTS_LOCAL_DEPENDENCY = "startup_role_slots_local_dependency"
TRUE_BARRIERS_STOP_QUEUEING = "true_barriers_stop_queueing"
STARTUP_PARALLEL_OBLIGATION_REVIEW_JOIN = "startup_parallel_obligation_review_join"
RECONCILED_SCHEDULER_ROW_STATUS_MONOTONIC = "reconciled_scheduler_row_status_monotonic"
SINGLE_CARD_ACK_RETURN_RECONCILES_WAIT_ROWS = "single_card_ack_return_reconciles_wait_rows"

CONTROLLER_OWNS_ROUTER_DEPENDENCIES = "controller_owns_router_dependencies"
DAEMON_DUPLICATES_CONTROLLER_ROW_ON_RETRY = "daemon_duplicates_controller_row_on_retry"
REVIEWER_STARTS_BEFORE_STARTUP_SCOPE_CLEAN = "reviewer_starts_before_startup_scope_clean"
DAEMON_ENQUEUES_PAST_BARRIER = "daemon_enqueues_past_barrier"
PM_ACTIVATION_REQUIRES_SECOND_GLOBAL_JOIN = "pm_activation_requires_second_global_join"
STATEFUL_RECEIPT_CLEARED_WITHOUT_POSTCONDITION = "stateful_receipt_cleared_without_postcondition"
LIVE_WAIT_WITH_EMPTY_CONTROLLER_PLAN = "live_wait_with_empty_controller_plan"
PASSIVE_WAIT_WRITTEN_AS_CONTROLLER_WORK = "passive_wait_written_as_controller_work"
PASSIVE_WAIT_HIDES_ROUTER_LOCAL_OBLIGATION = "passive_wait_hides_router_local_obligation"
STANDBY_WITHOUT_WAIT_TARGET_STATUS = "standby_without_wait_target_status"
CONTROLLER_LEDGER_PROMPT_MISSING_TOP_DOWN = "controller_ledger_prompt_missing_top_down"
FLOWPILOT_RUNNING_FOREGROUND_CLOSURE_ALLOWED = "flowpilot_running_foreground_closure_allowed"
STANDBY_COMPLETES_AFTER_ONE_CHECK = "standby_completes_after_one_check"
STANDBY_TIMEOUT_TREATED_AS_COMPLETION = "standby_timeout_treated_as_completion"
STANDBY_NEW_WORK_IGNORED = "standby_new_work_ignored"
NO_OUTPUT_WAIT_TRIGGERS_ROLE_RECOVERY = "no_output_wait_triggers_role_recovery"
NO_OUTPUT_REISSUE_WITHOUT_SUPERSEDE = "no_output_reissue_without_supersede"
UNAVAILABLE_WAIT_REISSUED_INSTEAD_OF_RECOVERY = "unavailable_wait_reissued_instead_of_recovery"
STARTUP_UI_BEFORE_DAEMON = "startup_ui_before_daemon"
STARTUP_ROLES_OR_HEARTBEAT_BEFORE_DAEMON = "startup_roles_or_heartbeat_before_daemon"
DAEMON_WAITS_FOR_CONTROLLER_CORE_DURING_STARTUP = "daemon_waits_for_controller_core_during_startup"
ROUTER_SCHEDULER_LEDGER_PARTIAL_WRITE = "router_scheduler_ledger_partial_write"
CONTROLLER_ACTION_LEDGER_PARTIAL_WRITE = "controller_action_ledger_partial_write"
ROUTER_SCHEDULER_LEDGER_MULTI_WRITER = "router_scheduler_ledger_multi_writer"
FRESH_SCHEDULER_WRITE_LOCK_REPORTED_CORRUPT = "fresh_scheduler_write_lock_reported_corrupt"
STARTUP_BOOTLOADER_RECEIPT_LEAVES_STALE_PENDING_ACTION = (
    "startup_bootloader_receipt_leaves_stale_pending_action"
)
STARTUP_BANNER_DISPLAY_GLOBAL_BARRIER = "startup_banner_display_global_barrier"
STARTUP_HEARTBEAT_GLOBAL_BARRIER = "startup_heartbeat_global_barrier"
STARTUP_ROLE_SPAWN_GLOBAL_BARRIER = "startup_role_spawn_global_barrier"
STARTUP_OBLIGATION_BEFORE_CONTROLLER_CORE = "startup_obligation_before_controller_core"
ROLE_DEPENDENT_WORK_BEFORE_ROLE_SLOTS_READY = "role_dependent_work_before_role_slots_ready"
REVIEWER_STARTS_BEFORE_PARALLEL_STARTUP_OBLIGATIONS_CLEAN = (
    "reviewer_starts_before_parallel_startup_obligations_clean"
)
TRUE_BARRIER_DEMOTED_TO_PARALLEL = "true_barrier_demoted_to_parallel"
DUPLICATE_STARTUP_PARALLEL_OBLIGATION_ROW = "duplicate_startup_parallel_obligation_row"
STARTUP_OBLIGATION_RECONCILED_WITHOUT_ROUTER_PROOF = (
    "startup_obligation_reconciled_without_router_proof"
)
SCHEDULER_RECONCILED_ROW_DOWNGRADED = "scheduler_reconciled_row_downgraded"
SINGLE_CARD_ACK_WAIT_STALE_AFTER_RETURN_RESOLUTION = "single_card_ack_wait_stale_after_return_resolution"
SINGLE_CARD_ACK_SCHEDULER_STALE_AFTER_RETURN_RESOLUTION = (
    "single_card_ack_scheduler_stale_after_return_resolution"
)

VALID_SCENARIOS = (
    ASYNC_STARTUP_ROWS_UNTIL_BARRIER,
    STARTUP_DAEMON_FIRST_DRIVER,
    CONTROLLER_TABLE_SIMPLE_ROUTER_TABLE_COMPLEX,
    STATEFUL_RECEIPT_RECONCILED_WITH_POSTCONDITION,
    STARTUP_REVIEW_WAITS_FOR_CURRENT_SCOPE_RECONCILIATION,
    PM_ACTIVATION_SAME_ROLE_ACK_ONLY,
    CONTINUOUS_STANDBY_ROW_DURING_LIVE_WAIT,
    PASSIVE_WAIT_STATUS_NOT_CONTROLLER_WORK,
    STANDBY_REENTERS_TOP_DOWN_ON_NEW_WORK,
    NO_OUTPUT_WAIT_REISSUES_BEFORE_RECOVERY,
    UNAVAILABLE_WAIT_USES_ROLE_RECOVERY,
    TRANSIENT_SCHEDULER_WRITE_LOCK_WAITS,
    STARTUP_BOOTLOADER_RECEIPT_CONSUMES_PENDING_AND_ADVANCES,
    PARALLEL_STARTUP_OBLIGATIONS_QUEUE_UNRELATED_WORK,
    STARTUP_ROLE_SLOTS_LOCAL_DEPENDENCY,
    TRUE_BARRIERS_STOP_QUEUEING,
    STARTUP_PARALLEL_OBLIGATION_REVIEW_JOIN,
    RECONCILED_SCHEDULER_ROW_STATUS_MONOTONIC,
    SINGLE_CARD_ACK_RETURN_RECONCILES_WAIT_ROWS,
)

NEGATIVE_SCENARIOS = (
    CONTROLLER_OWNS_ROUTER_DEPENDENCIES,
    DAEMON_DUPLICATES_CONTROLLER_ROW_ON_RETRY,
    REVIEWER_STARTS_BEFORE_STARTUP_SCOPE_CLEAN,
    DAEMON_ENQUEUES_PAST_BARRIER,
    PM_ACTIVATION_REQUIRES_SECOND_GLOBAL_JOIN,
    STATEFUL_RECEIPT_CLEARED_WITHOUT_POSTCONDITION,
    LIVE_WAIT_WITH_EMPTY_CONTROLLER_PLAN,
    PASSIVE_WAIT_WRITTEN_AS_CONTROLLER_WORK,
    PASSIVE_WAIT_HIDES_ROUTER_LOCAL_OBLIGATION,
    STANDBY_WITHOUT_WAIT_TARGET_STATUS,
    CONTROLLER_LEDGER_PROMPT_MISSING_TOP_DOWN,
    FLOWPILOT_RUNNING_FOREGROUND_CLOSURE_ALLOWED,
    STANDBY_COMPLETES_AFTER_ONE_CHECK,
    STANDBY_TIMEOUT_TREATED_AS_COMPLETION,
    STANDBY_NEW_WORK_IGNORED,
    NO_OUTPUT_WAIT_TRIGGERS_ROLE_RECOVERY,
    NO_OUTPUT_REISSUE_WITHOUT_SUPERSEDE,
    UNAVAILABLE_WAIT_REISSUED_INSTEAD_OF_RECOVERY,
    STARTUP_UI_BEFORE_DAEMON,
    STARTUP_ROLES_OR_HEARTBEAT_BEFORE_DAEMON,
    DAEMON_WAITS_FOR_CONTROLLER_CORE_DURING_STARTUP,
    ROUTER_SCHEDULER_LEDGER_PARTIAL_WRITE,
    CONTROLLER_ACTION_LEDGER_PARTIAL_WRITE,
    ROUTER_SCHEDULER_LEDGER_MULTI_WRITER,
    FRESH_SCHEDULER_WRITE_LOCK_REPORTED_CORRUPT,
    STARTUP_BOOTLOADER_RECEIPT_LEAVES_STALE_PENDING_ACTION,
    STARTUP_BANNER_DISPLAY_GLOBAL_BARRIER,
    STARTUP_HEARTBEAT_GLOBAL_BARRIER,
    STARTUP_ROLE_SPAWN_GLOBAL_BARRIER,
    STARTUP_OBLIGATION_BEFORE_CONTROLLER_CORE,
    ROLE_DEPENDENT_WORK_BEFORE_ROLE_SLOTS_READY,
    REVIEWER_STARTS_BEFORE_PARALLEL_STARTUP_OBLIGATIONS_CLEAN,
    TRUE_BARRIER_DEMOTED_TO_PARALLEL,
    DUPLICATE_STARTUP_PARALLEL_OBLIGATION_ROW,
    STARTUP_OBLIGATION_RECONCILED_WITHOUT_ROUTER_PROOF,
    SCHEDULER_RECONCILED_ROW_DOWNGRADED,
    SINGLE_CARD_ACK_WAIT_STALE_AFTER_RETURN_RESOLUTION,
    SINGLE_CARD_ACK_SCHEDULER_STALE_AFTER_RETURN_RESOLUTION,
)

SCENARIOS = VALID_SCENARIOS + NEGATIVE_SCENARIOS


@dataclass(frozen=True)
class Tick:
    """One abstract daemon scheduling tick."""


@dataclass(frozen=True)
class Action:
    name: str


@dataclass(frozen=True)
class State:
    status: str = "new"  # new | accepted | rejected
    scenario: str = "unset"

    daemon_started: bool = False
    daemon_tick_seconds: int = 0
    router_scheduler_table_exists: bool = False
    controller_action_table_exists: bool = False
    router_scheduler_ledger_valid_json: bool = True
    controller_action_ledger_valid_json: bool = True
    router_scheduler_write_lock_fresh: bool = False
    daemon_deferred_for_fresh_write_lock: bool = False
    ledger_writes_atomic: bool = True
    router_scheduler_single_writer: bool = True
    router_table_has_dependency_metadata: bool = False
    controller_table_has_router_dependency_graph: bool = False
    controller_table_prompt_present: bool = False
    controller_table_prompt_before_actions: bool = False
    controller_table_prompt_top_down_order: bool = False
    controller_table_prompt_receipt_duty: bool = False
    controller_table_prompt_foreground_while_running: bool = False
    controller_table_prompt_authority_limits: bool = False

    minimal_run_shell_created: bool = False
    daemon_first_driver_before_external_startup_actions: bool = False
    startup_ui_opened_before_daemon: bool = False
    startup_roles_started_before_daemon: bool = False
    startup_heartbeat_bound_before_daemon: bool = False
    daemon_drives_startup_before_controller_core: bool = False
    daemon_waits_for_controller_core_without_startup_drive: bool = False
    controller_core_loaded: bool = False
    startup_bootstrap_pending_action_open: bool = False
    startup_bootstrap_flag_current: bool = False
    startup_controller_receipt_done: bool = False
    startup_daemon_processed_done_receipt: bool = False
    startup_router_row_reconciled: bool = False
    startup_next_row_scheduled_after_receipt: bool = False
    startup_real_barrier_reached_after_receipt: bool = False
    startup_same_action_reissued_after_done_receipt: bool = False

    startup_scope_active: bool = False
    independent_controller_row_pending: bool = False
    independent_row_enqueued: bool = False
    next_independent_row_enqueued: bool = False
    barrier_active: bool = False
    enqueued_after_barrier: bool = False

    idempotency_key_used: bool = False
    duplicate_controller_row_created: bool = False
    receipt_done: bool = False
    stateful_postcondition_required: bool = False
    router_visible_postcondition_written: bool = False
    router_marked_row_reconciled: bool = False

    startup_local_rows_clean: bool = False
    startup_prep_cards_sent: bool = False
    startup_prep_acks_clean: bool = False
    startup_parallel_obligation_open: bool = False
    startup_parallel_obligation_proof_written: bool = False
    startup_parallel_obligation_reconciled: bool = False
    startup_parallel_obligations_clean: bool = False
    startup_parallel_obligation_blocked_unrelated_queue: bool = False
    startup_heartbeat_obligation_open: bool = False
    startup_role_slots_open: bool = False
    startup_role_slots_ready: bool = False
    startup_role_slots_blocked_unrelated_queue: bool = False
    unrelated_startup_work_available: bool = False
    unrelated_startup_work_enqueued: bool = False
    role_independent_work_enqueued: bool = False
    role_dependent_work_enqueued: bool = False
    current_action_true_barrier: bool = False
    queue_continued_after_true_barrier: bool = False
    duplicate_startup_parallel_obligation_rows: bool = False
    scheduler_row_status_reconciled: bool = False
    scheduler_row_status_downgraded_to_receipt_done: bool = False
    startup_scope_reconciliation_checked: bool = False
    startup_scope_reconciliation_clean: bool = False
    reviewer_startup_fact_review_started: bool = False

    reviewer_fact_report_recorded: bool = False
    pm_startup_activation_card_sent: bool = False
    pm_startup_activation_ack_clean: bool = False
    single_card_ack_return_resolved: bool = False
    single_card_controller_wait_row_reconciled: bool = False
    single_card_scheduler_row_reconciled: bool = False
    single_card_wait_still_waiting_after_return_resolution: bool = False
    single_card_scheduler_still_waiting_after_return_resolution: bool = False
    pm_activation_decision_accepted: bool = False
    pm_activation_second_global_join_required: bool = False
    route_work_started: bool = False
    flowpilot_still_running: bool = False
    running_wait_state_kind: str = "none"
    passive_wait_status_present: bool = False
    passive_wait_written_as_ordinary_controller_row: bool = False
    passive_wait_metadata_in_monitor: bool = False
    router_local_obligation_available: bool = False
    router_local_obligation_hidden_by_passive_wait: bool = False
    live_wait_without_ordinary_controller_row: bool = False
    continuous_standby_row_present: bool = False
    standby_row_stable_idempotency: bool = False
    standby_row_names_wait_target: bool = False
    standby_codex_plan_sync_required: bool = False
    standby_codex_plan_item_in_progress: bool = False
    standby_strict_monitor_wait_policy: bool = False
    standby_completed_after_one_check: bool = False
    standby_timeout_still_waiting_treated_as_completion: bool = False
    foreground_closure_allowed_while_running: bool = False
    foreground_controller_stopped_during_standby: bool = False
    new_controller_work_exposed_during_standby: bool = False
    standby_updates_ledger_on_new_work: bool = False
    standby_returns_to_top_down_row_processing: bool = False
    wait_target_status: str = "none"  # none | still_working | no_output | unavailable | ambiguous
    no_output_reissue_created: bool = False
    no_output_retry_budget_exhausted: bool = False
    no_output_pm_escalation_recorded: bool = False
    no_output_original_wait_superseded: bool = False
    no_output_replacement_wait_durable: bool = False
    role_recovery_requested: bool = False
    terminal_reason: str = "none"


class Transition(NamedTuple):
    label: str
    state: State


def initial_state() -> State:
    return State()


def _accepted(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="accepted", terminal_reason="valid", **changes)


def _rejected(scenario: str, **changes: object) -> State:
    return replace(State(scenario=scenario), status="rejected", terminal_reason="invalid", **changes)


def scenario_state(scenario: str) -> State:
    base = {
        "daemon_started": True,
        "daemon_tick_seconds": 1,
        "router_scheduler_table_exists": True,
        "controller_action_table_exists": True,
        "router_scheduler_ledger_valid_json": True,
        "controller_action_ledger_valid_json": True,
        "ledger_writes_atomic": True,
        "router_scheduler_single_writer": True,
        "router_table_has_dependency_metadata": True,
        "controller_table_prompt_present": True,
        "controller_table_prompt_before_actions": True,
        "controller_table_prompt_top_down_order": True,
        "controller_table_prompt_receipt_duty": True,
        "controller_table_prompt_foreground_while_running": True,
        "controller_table_prompt_authority_limits": True,
        "minimal_run_shell_created": True,
        "daemon_first_driver_before_external_startup_actions": True,
        "daemon_drives_startup_before_controller_core": True,
        "controller_core_loaded": False,
        "startup_scope_active": True,
        "flowpilot_still_running": True,
    }
    if scenario == ASYNC_STARTUP_ROWS_UNTIL_BARRIER:
        return _accepted(
            scenario,
            **base,
            independent_controller_row_pending=True,
            independent_row_enqueued=True,
            next_independent_row_enqueued=True,
            barrier_active=True,
            enqueued_after_barrier=False,
            idempotency_key_used=True,
        )
    if scenario == STARTUP_DAEMON_FIRST_DRIVER:
        return _accepted(
            scenario,
            **base,
            startup_ui_opened_before_daemon=False,
            startup_roles_started_before_daemon=False,
            startup_heartbeat_bound_before_daemon=False,
            daemon_waits_for_controller_core_without_startup_drive=False,
            independent_row_enqueued=True,
            next_independent_row_enqueued=True,
            idempotency_key_used=True,
        )
    if scenario == CONTROLLER_TABLE_SIMPLE_ROUTER_TABLE_COMPLEX:
        return _accepted(
            scenario,
            **base,
            independent_row_enqueued=True,
            idempotency_key_used=True,
        )
    if scenario == STATEFUL_RECEIPT_RECONCILED_WITH_POSTCONDITION:
        return _accepted(
            scenario,
            **base,
            receipt_done=True,
            stateful_postcondition_required=True,
            router_visible_postcondition_written=True,
            router_marked_row_reconciled=True,
        )
    if scenario == STARTUP_REVIEW_WAITS_FOR_CURRENT_SCOPE_RECONCILIATION:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            startup_local_rows_clean=True,
            startup_prep_cards_sent=True,
            startup_prep_acks_clean=True,
            startup_parallel_obligations_clean=True,
            startup_scope_reconciliation_checked=True,
            startup_scope_reconciliation_clean=True,
            reviewer_startup_fact_review_started=True,
        )
    if scenario == PM_ACTIVATION_SAME_ROLE_ACK_ONLY:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            startup_local_rows_clean=True,
            startup_prep_cards_sent=True,
            startup_prep_acks_clean=True,
            startup_parallel_obligations_clean=True,
            startup_scope_reconciliation_checked=True,
            startup_scope_reconciliation_clean=True,
            reviewer_startup_fact_review_started=True,
            reviewer_fact_report_recorded=True,
            pm_startup_activation_card_sent=True,
            pm_startup_activation_ack_clean=True,
            pm_activation_decision_accepted=True,
            pm_activation_second_global_join_required=False,
            route_work_started=True,
        )
    if scenario == CONTINUOUS_STANDBY_ROW_DURING_LIVE_WAIT:
        return _accepted(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
        )
    if scenario == PASSIVE_WAIT_STATUS_NOT_CONTROLLER_WORK:
        return _accepted(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            passive_wait_written_as_ordinary_controller_row=False,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
        )
    if scenario == STANDBY_REENTERS_TOP_DOWN_ON_NEW_WORK:
        return _accepted(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            new_controller_work_exposed_during_standby=True,
            standby_updates_ledger_on_new_work=True,
            standby_returns_to_top_down_row_processing=True,
        )
    if scenario == NO_OUTPUT_WAIT_REISSUES_BEFORE_RECOVERY:
        return _accepted(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            wait_target_status="no_output",
            no_output_reissue_created=True,
            no_output_replacement_wait_durable=True,
            no_output_original_wait_superseded=True,
            role_recovery_requested=False,
        )
    if scenario == UNAVAILABLE_WAIT_USES_ROLE_RECOVERY:
        return _accepted(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            wait_target_status="unavailable",
            no_output_reissue_created=False,
            role_recovery_requested=True,
        )
    if scenario == TRANSIENT_SCHEDULER_WRITE_LOCK_WAITS:
        return _accepted(
            scenario,
            **base,
            independent_row_enqueued=True,
            router_scheduler_write_lock_fresh=True,
            daemon_deferred_for_fresh_write_lock=True,
        )
    if scenario == STARTUP_BOOTLOADER_RECEIPT_CONSUMES_PENDING_AND_ADVANCES:
        return _accepted(
            scenario,
            **base,
            independent_row_enqueued=True,
            receipt_done=True,
            idempotency_key_used=True,
            startup_bootstrap_pending_action_open=False,
            startup_bootstrap_flag_current=True,
            startup_controller_receipt_done=True,
            startup_daemon_processed_done_receipt=True,
            startup_router_row_reconciled=True,
            startup_next_row_scheduled_after_receipt=True,
            startup_same_action_reissued_after_done_receipt=False,
        )
    if scenario == PARALLEL_STARTUP_OBLIGATIONS_QUEUE_UNRELATED_WORK:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            startup_parallel_obligation_open=True,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=False,
            startup_parallel_obligations_clean=False,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=True,
            independent_row_enqueued=True,
            next_independent_row_enqueued=True,
            idempotency_key_used=True,
        )
    if scenario == STARTUP_ROLE_SLOTS_LOCAL_DEPENDENCY:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            startup_role_slots_open=True,
            startup_role_slots_ready=False,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=True,
            role_independent_work_enqueued=True,
            role_dependent_work_enqueued=False,
            idempotency_key_used=True,
        )
    if scenario == TRUE_BARRIERS_STOP_QUEUEING:
        return _accepted(
            scenario,
            **base,
            current_action_true_barrier=True,
            barrier_active=True,
            queue_continued_after_true_barrier=False,
            enqueued_after_barrier=False,
        )
    if scenario == STARTUP_PARALLEL_OBLIGATION_REVIEW_JOIN:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            startup_parallel_obligation_open=False,
            startup_parallel_obligation_proof_written=True,
            startup_parallel_obligation_reconciled=True,
            startup_parallel_obligations_clean=True,
            startup_local_rows_clean=True,
            startup_prep_cards_sent=True,
            startup_prep_acks_clean=True,
            startup_scope_reconciliation_checked=True,
            startup_scope_reconciliation_clean=True,
            reviewer_startup_fact_review_started=True,
        )
    if scenario == RECONCILED_SCHEDULER_ROW_STATUS_MONOTONIC:
        return _accepted(
            scenario,
            **base,
            receipt_done=True,
            router_marked_row_reconciled=True,
            scheduler_row_status_reconciled=True,
            scheduler_row_status_downgraded_to_receipt_done=False,
        )
    if scenario == SINGLE_CARD_ACK_RETURN_RECONCILES_WAIT_ROWS:
        return _accepted(
            scenario,
            **{**base, "controller_core_loaded": True},
            reviewer_fact_report_recorded=True,
            pm_startup_activation_card_sent=True,
            pm_startup_activation_ack_clean=True,
            single_card_ack_return_resolved=True,
            single_card_controller_wait_row_reconciled=True,
            single_card_scheduler_row_reconciled=True,
            single_card_wait_still_waiting_after_return_resolution=False,
            single_card_scheduler_still_waiting_after_return_resolution=False,
        )
    if scenario == CONTROLLER_OWNS_ROUTER_DEPENDENCIES:
        return _rejected(
            scenario,
            **base,
            controller_table_has_router_dependency_graph=True,
        )
    if scenario == DAEMON_DUPLICATES_CONTROLLER_ROW_ON_RETRY:
        return _rejected(
            scenario,
            **base,
            independent_row_enqueued=True,
            idempotency_key_used=False,
            duplicate_controller_row_created=True,
        )
    if scenario == REVIEWER_STARTS_BEFORE_STARTUP_SCOPE_CLEAN:
        return _rejected(
            scenario,
            **base,
            startup_local_rows_clean=False,
            startup_prep_cards_sent=True,
            startup_prep_acks_clean=False,
            startup_scope_reconciliation_checked=False,
            startup_scope_reconciliation_clean=False,
            reviewer_startup_fact_review_started=True,
        )
    if scenario == DAEMON_ENQUEUES_PAST_BARRIER:
        return _rejected(
            scenario,
            **base,
            independent_row_enqueued=True,
            barrier_active=True,
            enqueued_after_barrier=True,
        )
    if scenario == PM_ACTIVATION_REQUIRES_SECOND_GLOBAL_JOIN:
        return _rejected(
            scenario,
            **base,
            reviewer_fact_report_recorded=True,
            pm_startup_activation_card_sent=True,
            pm_startup_activation_ack_clean=True,
            pm_activation_decision_accepted=False,
            pm_activation_second_global_join_required=True,
        )
    if scenario == STATEFUL_RECEIPT_CLEARED_WITHOUT_POSTCONDITION:
        return _rejected(
            scenario,
            **base,
            receipt_done=True,
            stateful_postcondition_required=True,
            router_visible_postcondition_written=False,
            router_marked_row_reconciled=True,
        )
    if scenario == LIVE_WAIT_WITH_EMPTY_CONTROLLER_PLAN:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=False,
            standby_codex_plan_item_in_progress=False,
        )
    if scenario == PASSIVE_WAIT_WRITTEN_AS_CONTROLLER_WORK:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            passive_wait_written_as_ordinary_controller_row=True,
            live_wait_without_ordinary_controller_row=False,
            continuous_standby_row_present=False,
        )
    if scenario == PASSIVE_WAIT_HIDES_ROUTER_LOCAL_OBLIGATION:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            passive_wait_written_as_ordinary_controller_row=False,
            router_local_obligation_available=True,
            router_local_obligation_hidden_by_passive_wait=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
        )
    if scenario == STANDBY_WITHOUT_WAIT_TARGET_STATUS:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=False,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=False,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
        )
    if scenario == CONTROLLER_LEDGER_PROMPT_MISSING_TOP_DOWN:
        prompt_missing_base = {
            **base,
            "controller_table_prompt_present": True,
            "controller_table_prompt_before_actions": True,
            "controller_table_prompt_top_down_order": False,
            "controller_table_prompt_receipt_duty": False,
        }
        return _rejected(
            scenario,
            **prompt_missing_base,
        )
    if scenario == FLOWPILOT_RUNNING_FOREGROUND_CLOSURE_ALLOWED:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            running_wait_state_kind="blocker_or_user_or_repair_wait",
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            foreground_closure_allowed_while_running=True,
        )
    if scenario == STANDBY_COMPLETES_AFTER_ONE_CHECK:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_completed_after_one_check=True,
            foreground_controller_stopped_during_standby=True,
        )
    if scenario == STANDBY_NEW_WORK_IGNORED:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            new_controller_work_exposed_during_standby=True,
            standby_updates_ledger_on_new_work=False,
            standby_returns_to_top_down_row_processing=False,
        )
    if scenario == STANDBY_TIMEOUT_TREATED_AS_COMPLETION:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_timeout_still_waiting_treated_as_completion=True,
            foreground_controller_stopped_during_standby=True,
        )
    if scenario == NO_OUTPUT_WAIT_TRIGGERS_ROLE_RECOVERY:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            wait_target_status="no_output",
            no_output_reissue_created=False,
            role_recovery_requested=True,
        )
    if scenario == NO_OUTPUT_REISSUE_WITHOUT_SUPERSEDE:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            wait_target_status="no_output",
            no_output_reissue_created=True,
            no_output_replacement_wait_durable=False,
            no_output_original_wait_superseded=False,
            role_recovery_requested=False,
        )
    if scenario == UNAVAILABLE_WAIT_REISSUED_INSTEAD_OF_RECOVERY:
        return _rejected(
            scenario,
            **base,
            barrier_active=True,
            passive_wait_status_present=True,
            passive_wait_metadata_in_monitor=True,
            live_wait_without_ordinary_controller_row=True,
            continuous_standby_row_present=True,
            standby_row_stable_idempotency=True,
            standby_row_names_wait_target=True,
            standby_codex_plan_sync_required=True,
            standby_codex_plan_item_in_progress=True,
            standby_strict_monitor_wait_policy=True,
            wait_target_status="unavailable",
            no_output_reissue_created=True,
            no_output_replacement_wait_durable=True,
            no_output_original_wait_superseded=True,
            role_recovery_requested=False,
        )
    if scenario == STARTUP_UI_BEFORE_DAEMON:
        return _rejected(
            scenario,
            **{
                **base,
                "daemon_first_driver_before_external_startup_actions": False,
                "startup_ui_opened_before_daemon": True,
            },
        )
    if scenario == STARTUP_ROLES_OR_HEARTBEAT_BEFORE_DAEMON:
        return _rejected(
            scenario,
            **{
                **base,
                "daemon_first_driver_before_external_startup_actions": False,
                "startup_roles_started_before_daemon": True,
                "startup_heartbeat_bound_before_daemon": True,
            },
        )
    if scenario == DAEMON_WAITS_FOR_CONTROLLER_CORE_DURING_STARTUP:
        return _rejected(
            scenario,
            **{
                **base,
                "daemon_drives_startup_before_controller_core": False,
                "daemon_waits_for_controller_core_without_startup_drive": True,
            },
        )
    if scenario == ROUTER_SCHEDULER_LEDGER_PARTIAL_WRITE:
        return _rejected(
            scenario,
            **{
                **base,
                "independent_row_enqueued": True,
                "next_independent_row_enqueued": True,
                "receipt_done": True,
                "router_scheduler_ledger_valid_json": False,
                "ledger_writes_atomic": False,
            },
        )
    if scenario == CONTROLLER_ACTION_LEDGER_PARTIAL_WRITE:
        return _rejected(
            scenario,
            **{
                **base,
                "independent_row_enqueued": True,
                "controller_action_ledger_valid_json": False,
                "ledger_writes_atomic": False,
            },
        )
    if scenario == ROUTER_SCHEDULER_LEDGER_MULTI_WRITER:
        return _rejected(
            scenario,
            **{
                **base,
                "independent_row_enqueued": True,
                "router_scheduler_single_writer": False,
            },
        )
    if scenario == FRESH_SCHEDULER_WRITE_LOCK_REPORTED_CORRUPT:
        return _rejected(
            scenario,
            **{
                **base,
                "independent_row_enqueued": True,
                "router_scheduler_ledger_valid_json": False,
                "router_scheduler_write_lock_fresh": True,
                "daemon_deferred_for_fresh_write_lock": False,
            },
        )
    if scenario == STARTUP_BOOTLOADER_RECEIPT_LEAVES_STALE_PENDING_ACTION:
        return _rejected(
            scenario,
            **{
                **base,
                "independent_row_enqueued": True,
                "receipt_done": True,
                "idempotency_key_used": True,
                "startup_bootstrap_pending_action_open": True,
                "startup_bootstrap_flag_current": False,
                "startup_controller_receipt_done": True,
                "startup_daemon_processed_done_receipt": True,
                "startup_router_row_reconciled": False,
                "startup_next_row_scheduled_after_receipt": False,
                "startup_same_action_reissued_after_done_receipt": True,
            },
        )
    if scenario == STARTUP_BANNER_DISPLAY_GLOBAL_BARRIER:
        return _rejected(
            scenario,
            **base,
            startup_parallel_obligation_open=True,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=False,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=False,
            startup_parallel_obligation_blocked_unrelated_queue=True,
        )
    if scenario == STARTUP_HEARTBEAT_GLOBAL_BARRIER:
        return _rejected(
            scenario,
            **base,
            startup_parallel_obligation_open=True,
            startup_heartbeat_obligation_open=True,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=False,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=False,
            startup_parallel_obligation_blocked_unrelated_queue=True,
        )
    if scenario == STARTUP_ROLE_SPAWN_GLOBAL_BARRIER:
        return _rejected(
            scenario,
            **base,
            startup_role_slots_open=True,
            startup_role_slots_ready=False,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=False,
            role_independent_work_enqueued=False,
            startup_role_slots_blocked_unrelated_queue=True,
        )
    if scenario == STARTUP_OBLIGATION_BEFORE_CONTROLLER_CORE:
        return _rejected(
            scenario,
            **{**base, "controller_core_loaded": False},
            startup_parallel_obligation_open=True,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=False,
        )
    if scenario == ROLE_DEPENDENT_WORK_BEFORE_ROLE_SLOTS_READY:
        return _rejected(
            scenario,
            **base,
            startup_role_slots_open=True,
            startup_role_slots_ready=False,
            role_dependent_work_enqueued=True,
        )
    if scenario == REVIEWER_STARTS_BEFORE_PARALLEL_STARTUP_OBLIGATIONS_CLEAN:
        return _rejected(
            scenario,
            **base,
            startup_parallel_obligation_open=True,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=False,
            startup_parallel_obligations_clean=False,
            startup_local_rows_clean=True,
            startup_prep_cards_sent=True,
            startup_prep_acks_clean=True,
            startup_scope_reconciliation_checked=True,
            startup_scope_reconciliation_clean=True,
            reviewer_startup_fact_review_started=True,
        )
    if scenario == TRUE_BARRIER_DEMOTED_TO_PARALLEL:
        return _rejected(
            scenario,
            **base,
            current_action_true_barrier=True,
            queue_continued_after_true_barrier=True,
            independent_row_enqueued=True,
            next_independent_row_enqueued=True,
        )
    if scenario == DUPLICATE_STARTUP_PARALLEL_OBLIGATION_ROW:
        return _rejected(
            scenario,
            **base,
            startup_parallel_obligation_open=True,
            unrelated_startup_work_available=True,
            unrelated_startup_work_enqueued=True,
            idempotency_key_used=True,
            duplicate_startup_parallel_obligation_rows=True,
        )
    if scenario == STARTUP_OBLIGATION_RECONCILED_WITHOUT_ROUTER_PROOF:
        return _rejected(
            scenario,
            **base,
            startup_parallel_obligation_open=False,
            startup_parallel_obligation_proof_written=False,
            startup_parallel_obligation_reconciled=True,
            startup_parallel_obligations_clean=True,
        )
    if scenario == SCHEDULER_RECONCILED_ROW_DOWNGRADED:
        return _rejected(
            scenario,
            **base,
            receipt_done=True,
            router_marked_row_reconciled=True,
            scheduler_row_status_reconciled=True,
            scheduler_row_status_downgraded_to_receipt_done=True,
        )
    if scenario == SINGLE_CARD_ACK_WAIT_STALE_AFTER_RETURN_RESOLUTION:
        return _rejected(
            scenario,
            **{**base, "controller_core_loaded": True},
            reviewer_fact_report_recorded=True,
            pm_startup_activation_card_sent=True,
            pm_startup_activation_ack_clean=True,
            single_card_ack_return_resolved=True,
            single_card_controller_wait_row_reconciled=False,
            single_card_scheduler_row_reconciled=True,
            single_card_wait_still_waiting_after_return_resolution=True,
            single_card_scheduler_still_waiting_after_return_resolution=False,
        )
    if scenario == SINGLE_CARD_ACK_SCHEDULER_STALE_AFTER_RETURN_RESOLUTION:
        return _rejected(
            scenario,
            **{**base, "controller_core_loaded": True},
            reviewer_fact_report_recorded=True,
            pm_startup_activation_card_sent=True,
            pm_startup_activation_ack_clean=True,
            single_card_ack_return_resolved=True,
            single_card_controller_wait_row_reconciled=True,
            single_card_scheduler_row_reconciled=False,
            single_card_wait_still_waiting_after_return_resolution=False,
            single_card_scheduler_still_waiting_after_return_resolution=True,
        )
    raise ValueError(f"unknown scenario: {scenario}")


def scheduler_failures(state: State) -> list[str]:
    failures: list[str] = []
    if state.daemon_started and state.daemon_tick_seconds != 1:
        failures.append("Router daemon is not a one-second scheduling driver")
    if (
        state.router_scheduler_table_exists
        and state.router_scheduler_write_lock_fresh
        and not state.daemon_deferred_for_fresh_write_lock
    ):
        failures.append("fresh Router scheduler ledger write lock was not deferred to the next tick")
    if (
        state.router_scheduler_table_exists
        and not state.router_scheduler_ledger_valid_json
        and not state.router_scheduler_write_lock_fresh
    ):
        failures.append("Router scheduler ledger was not valid JSON after daemon table write")
    if state.controller_action_table_exists and not state.controller_action_ledger_valid_json:
        failures.append("Controller action ledger was not valid JSON after Controller table write")
    if (state.router_scheduler_table_exists or state.controller_action_table_exists) and not state.ledger_writes_atomic:
        failures.append("runtime ledgers were written without atomic replace semantics")
    if state.router_scheduler_table_exists and not state.router_scheduler_single_writer:
        failures.append("Router scheduler ledger had more than one writer")
    if (
        state.minimal_run_shell_created
        and not state.daemon_first_driver_before_external_startup_actions
        and (
            state.startup_ui_opened_before_daemon
            or state.startup_roles_started_before_daemon
            or state.startup_heartbeat_bound_before_daemon
        )
    ):
        failures.append("startup external actions ran before Router daemon became the startup driver")
    if (
        state.daemon_started
        and state.startup_scope_active
        and not state.controller_core_loaded
        and not state.daemon_drives_startup_before_controller_core
    ):
        failures.append("Router daemon waited for Controller core instead of driving startup work")
    if state.daemon_waits_for_controller_core_without_startup_drive:
        failures.append("pre-Controller-core daemon tick idled instead of scheduling startup work")
    if (
        not state.controller_core_loaded
        and (
            state.startup_parallel_obligation_open
            or state.startup_heartbeat_obligation_open
            or state.startup_role_slots_open
        )
    ):
        failures.append("Controller-ledger startup obligation was exposed before Controller core loaded")
    if (
        state.startup_controller_receipt_done
        and state.startup_daemon_processed_done_receipt
        and not (
            state.startup_bootstrap_flag_current
            and not state.startup_bootstrap_pending_action_open
            and state.startup_router_row_reconciled
        )
    ):
        failures.append("daemon consumed startup Controller receipt without syncing bootstrap flag, pending action, and Router row")
    if (
        state.startup_controller_receipt_done
        and state.startup_daemon_processed_done_receipt
        and not state.startup_real_barrier_reached_after_receipt
        and not state.startup_next_row_scheduled_after_receipt
    ):
        failures.append("daemon consumed startup Controller receipt but did not schedule the next startup row")
    if state.startup_same_action_reissued_after_done_receipt:
        failures.append("daemon reissued a completed startup Controller action because bootstrap pending_action stayed stale")
    if (
        state.startup_parallel_obligation_open
        and state.unrelated_startup_work_available
        and not state.unrelated_startup_work_enqueued
        and state.startup_parallel_obligation_blocked_unrelated_queue
    ):
        failures.append("startup parallel obligation blocked unrelated startup queueing")
    if (
        state.startup_role_slots_open
        and state.unrelated_startup_work_available
        and not state.role_independent_work_enqueued
        and state.startup_role_slots_blocked_unrelated_queue
    ):
        failures.append("startup role-slot dependency blocked unrelated startup queueing")
    if state.role_dependent_work_enqueued and not state.startup_role_slots_ready:
        failures.append("role-dependent startup work was queued before role slots were ready")
    if state.current_action_true_barrier and state.queue_continued_after_true_barrier:
        failures.append("Router daemon continued queueing after a true barrier")
    if state.duplicate_startup_parallel_obligation_rows:
        failures.append("daemon retry duplicated a startup parallel obligation row without open-row skip")
    if state.startup_parallel_obligation_reconciled and not state.startup_parallel_obligation_proof_written:
        failures.append("startup obligation was reconciled without Router-visible proof")
    if state.scheduler_row_status_reconciled and state.scheduler_row_status_downgraded_to_receipt_done:
        failures.append("Router scheduler row reconciliation status was downgraded after receipt sync")
    if state.single_card_ack_return_resolved and not (
        state.single_card_controller_wait_row_reconciled and state.single_card_scheduler_row_reconciled
    ):
        failures.append("single-card ACK return resolved without reconciling Controller wait row and Router scheduler row")
    if state.single_card_wait_still_waiting_after_return_resolution:
        failures.append("Controller passive wait stayed waiting after single-card ACK return resolved")
    if state.single_card_scheduler_still_waiting_after_return_resolution:
        failures.append("Router scheduler row stayed waiting after single-card ACK return resolved")
    if state.controller_action_table_exists and state.controller_table_has_router_dependency_graph:
        failures.append("Controller table owns Router dependency metadata")
    if state.router_scheduler_table_exists and not state.router_table_has_dependency_metadata:
        failures.append("Router scheduler table lacks dependency or barrier metadata")
    if state.controller_action_table_exists and not (
        state.controller_table_prompt_present
        and state.controller_table_prompt_before_actions
        and state.controller_table_prompt_top_down_order
        and state.controller_table_prompt_receipt_duty
        and state.controller_table_prompt_foreground_while_running
        and state.controller_table_prompt_authority_limits
    ):
        failures.append("Controller action ledger lacks table-local top-to-bottom prompt coverage")
    if state.next_independent_row_enqueued and not state.independent_row_enqueued:
        failures.append("Router enqueued a later row without recording the first row")
    if state.duplicate_controller_row_created and not state.idempotency_key_used:
        failures.append("daemon retry duplicated Controller row without deterministic idempotency")
    if state.barrier_active and state.enqueued_after_barrier:
        failures.append("Router daemon enqueued work after a barrier")
    if state.router_marked_row_reconciled and state.stateful_postcondition_required and not state.router_visible_postcondition_written:
        failures.append("Router reconciled stateful receipt without Router-visible postcondition evidence")
    if state.reviewer_startup_fact_review_started and not (
        state.startup_scope_reconciliation_checked
        and state.startup_scope_reconciliation_clean
        and state.startup_local_rows_clean
        and state.startup_prep_cards_sent
        and state.startup_prep_acks_clean
        and state.startup_parallel_obligations_clean
    ):
        failures.append("Reviewer startup fact review started before startup current-scope reconciliation was clean")
    if state.reviewer_startup_fact_review_started and not state.startup_parallel_obligations_clean:
        failures.append("Reviewer startup fact review started before startup parallel obligations were reconciled")
    if (
        not state.controller_core_loaded
        and (
            state.reviewer_startup_fact_review_started
            or state.pm_activation_decision_accepted
            or state.route_work_started
        )
    ):
        failures.append("startup review, PM activation, or route work started before Controller core loaded")
    if state.pm_activation_second_global_join_required:
        failures.append("PM startup activation required redundant all-startup ACK join")
    if state.route_work_started and not state.pm_activation_decision_accepted:
        failures.append("route work started before PM startup activation decision was accepted")
    if state.live_wait_without_ordinary_controller_row and not state.continuous_standby_row_present:
        failures.append("live daemon wait exposed an empty Controller plan instead of a continuous standby row")
    if state.passive_wait_status_present and state.passive_wait_written_as_ordinary_controller_row:
        failures.append("passive wait status was written as ordinary Controller work")
    if state.passive_wait_status_present and not state.passive_wait_metadata_in_monitor:
        failures.append("passive wait status was not projected into Router monitor status")
    if state.passive_wait_status_present and state.router_local_obligation_hidden_by_passive_wait:
        failures.append("passive wait hid a Router-local obligation that should have preempted waiting")
    if state.continuous_standby_row_present and not state.standby_row_stable_idempotency:
        failures.append("continuous standby row lacks stable idempotency")
    if state.continuous_standby_row_present and not state.standby_row_names_wait_target:
        failures.append("continuous standby row does not name the watched wait target")
    if state.continuous_standby_row_present and not (
        state.standby_codex_plan_sync_required and state.standby_codex_plan_item_in_progress
    ):
        failures.append("continuous standby row does not keep Codex plan sync in progress")
    if state.continuous_standby_row_present and not state.standby_strict_monitor_wait_policy:
        failures.append("continuous standby row does not require strict monitor wait timing")
    if state.standby_completed_after_one_check:
        failures.append("continuous standby row was completed after one monitor check")
    if state.standby_timeout_still_waiting_treated_as_completion:
        failures.append("timeout_still_waiting was treated as standby completion")
    if state.flowpilot_still_running and state.foreground_closure_allowed_while_running:
        failures.append("foreground Controller closure was allowed while FlowPilot was still running")
    if state.foreground_controller_stopped_during_standby:
        failures.append("foreground Controller stopped during a live continuous standby duty")
    if state.new_controller_work_exposed_during_standby and not (
        state.standby_updates_ledger_on_new_work and state.standby_returns_to_top_down_row_processing
    ):
        failures.append("continuous standby ignored new Controller work instead of returning to top-to-bottom row processing")
    if state.wait_target_status == "no_output" and state.role_recovery_requested:
        failures.append("no-output wait requested role recovery before bounded same-work reissue")
    if state.wait_target_status == "no_output" and not state.no_output_retry_budget_exhausted:
        if not state.no_output_reissue_created:
            failures.append("no-output wait did not create a replacement work attempt")
        if state.no_output_reissue_created and not state.no_output_replacement_wait_durable:
            failures.append("no-output replacement was not durable before continuation")
        if state.no_output_reissue_created and not state.no_output_original_wait_superseded:
            failures.append("no-output original wait was not superseded after replacement")
    if state.no_output_retry_budget_exhausted and not state.no_output_pm_escalation_recorded:
        failures.append("no-output retry budget exhausted without PM/control-blocker escalation")
    if state.wait_target_status == "unavailable" and not state.role_recovery_requested:
        failures.append("unavailable role did not enter role recovery")
    if state.wait_target_status == "unavailable" and state.no_output_reissue_created:
        failures.append("unavailable role was reissued same-work instead of recovered")
    return failures


def accepts_only_valid_scheduler_states(state: State, trace) -> InvariantResult:
    del trace
    if state.status == "accepted":
        failures = scheduler_failures(state)
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
    failures = scheduler_failures(candidate)
    if not failures and state.scenario in VALID_SCENARIOS:
        yield Transition(f"accept_{state.scenario}", candidate)
    else:
        yield Transition(
            f"reject_{state.scenario}",
            replace(candidate, status="rejected", terminal_reason=failures[0] if failures else "negative scenario rejected"),
        )


class TwoTableAsyncSchedulerStep:
    """Model one Router scheduler transition.

    Input x State -> Set(Output x State)
    reads: Router scheduler table, Controller action table, Controller
    receipts, startup ACK ledger, current-scope reconciliation state
    writes: Router scheduler rows, Controller action rows, reconciliation
    states, barrier waits, startup review permission, PM activation decision
    idempotency: daemon-enqueued rows are keyed by Router row id and stable
    action id so retries do not duplicate side effects
    """

    name = "TwoTableAsyncSchedulerStep"
    input_description = "one Router daemon scheduler tick"
    output_description = "one scheduling, reconciliation, or gate transition"
    reads = (
        "router_scheduler_ledger",
        "controller_action_ledger",
        "controller_receipts",
        "card_pending_return_ledger",
        "current_scope_reconciliation",
        "router_daemon_status",
    )
    writes = (
        "router_scheduler_ledger",
        "controller_action_ledger",
        "router_reconciliation_state",
        "barrier_wait",
        "startup_review_permission",
        "foreground_standby_plan_projection",
    )
    idempotency = "router_row_id and controller idempotency key dedupe daemon retries"

    def apply(self, input_obj: Tick, state: State) -> Iterable[FunctionResult]:
        del input_obj
        for transition in next_safe_states(state):
            yield FunctionResult(Action(transition.label), transition.state, transition.label)


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    for invariant in INVARIANTS:
        result = invariant.predicate(state, ())
        if not result.ok:
            failures.append(result.message)
    return failures


def is_terminal(state: State) -> bool:
    return state.status in {"accepted", "rejected"}


def is_success(state: State) -> bool:
    return state.status == "accepted" and state.scenario in VALID_SCENARIOS


def terminal_predicate(_input_obj: Tick, state: State, _trace) -> bool:
    return is_terminal(state)


def build_workflow() -> Workflow:
    return Workflow((TwoTableAsyncSchedulerStep(),), name="flowpilot_two_table_async_scheduler")


EXTERNAL_INPUTS = (Tick(),)
MAX_SEQUENCE_LENGTH = 2
INVARIANTS = (
    Invariant(
        name="two_table_async_scheduler",
        description="Router queues independent rows until barriers and reconciles current scope before review.",
        predicate=accepts_only_valid_scheduler_states,
    ),
)


def hazard_states() -> dict[str, State]:
    return {scenario: scenario_state(scenario) for scenario in NEGATIVE_SCENARIOS}
