"""Invariants for the FlowPilot persistent Router daemon model."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from flowpilot_persistent_router_daemon_model_state import State


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    ordinary_wait = state.current_wait in {"ack", "report", "controller_receipt"}
    role_wait = state.current_wait in {"ack", "report"}
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
    if state.lifecycle == "active" and state.daemon_mode_enabled and role_wait and not state.wait_target_metadata_present:
        failures.append("daemon-owned role wait lacks Router-authored wait target metadata")
    if state.current_wait in {"ack", "report"} and not (
        state.wait_target_names_role
        and state.wait_target_expected_evidence_visible
        and state.wait_target_reminder_text_present
    ):
        failures.append("wait target metadata does not name role, evidence, and reminder text")
    if state.current_wait == "report" and state.report_reminder_sent and not state.liveness_probe_fresh:
        failures.append("report reminder was sent without a fresh role liveness probe")
    if (state.ack_wait_reminder_sent or state.report_reminder_sent) and not (
        state.wait_target_reminder_controller_action_ready
        and state.wait_target_reminder_receipt_recorded
        and state.wait_target_reminder_updates_wait_metadata
    ):
        failures.append("wait target reminder was not handled as an executable Controller action with receipt metadata")
    if state.stale_liveness_cached_as_truth:
        failures.append("Controller trusted cached role liveness instead of probing during standby")
    if state.current_wait == "ack" and state.ack_wait_age_minutes >= 10 and not state.ack_wait_blocker_recorded and not state.mailbox_evidence_present:
        failures.append("ACK wait reached ten minutes without Router-visible blocker")
    if state.liveness_probe_outcome == "lost" and not state.role_liveness_blocker_recorded:
        failures.append("lost role wait did not route to PM blocker recovery")
    if state.external_event_recorded and state.external_event_matches_wait and state.event_wait_action_open:
        failures.append("recorded external event left matching Controller wait row open")
    if state.external_event_recorded and state.external_event_matches_wait and not state.event_wait_closed_by_router:
        failures.append("recorded external event was not reconciled by Router-owned wait closure")
    if state.next_wait_opened_before_event_wait_closed:
        failures.append("Router opened next wait before closing satisfied external-event wait")
    if state.controller_closed_event_wait:
        failures.append("Controller closed external-event wait instead of Router")
    if state.current_wait == "controller_local" and state.controller_reminded_itself:
        failures.append("Controller sent a reminder to itself instead of self-auditing local action ledger")
    if state.current_wait == "controller_local" and not state.controller_local_self_audit_done:
        failures.append("Controller-local wait did not self-audit action ledger and receipts")
    if state.packet_holder_projection_needed and not (
        state.active_packet_holder
        and state.current_work_owner_kind == "role"
        and state.current_work_owner_key == state.active_packet_holder
        and state.current_work_task_visible
        and state.current_work_source == "packet_ledger"
    ):
        failures.append("packet holder is active but current_work does not name the packet holder")
    if state.passive_reconciliation_wait_open and not (
        state.current_work_owner_kind == "controller"
        and state.current_work_owner_key == "controller"
        and state.current_work_task_visible
        and state.current_work_source == "passive_wait"
    ):
        failures.append("passive reconciliation wait is active but current_work does not name the internal owner")
    if state.router_internal_projection_needed and not (
        state.current_work_owner_kind == "router"
        and state.current_work_owner_key == "router"
        and state.current_work_task_visible
        and state.current_work_source == "router_daemon"
    ):
        failures.append("Router internal work is active but current_work does not name Router")
    if state.current_work_owner_kind == "role" and not state.current_work_owner_key:
        failures.append("role current_work owner lacks owner key")
    if state.daemon_writer_count > 1 or state.daemon_lock_state == "duplicate":
        failures.append("multiple Router daemon writers exist for one run")
    if state.daemon_alive and state.daemon_tick_seconds != 1:
        failures.append("Router daemon tick is not fixed at one second")
    if not state.router_scheduler_ledger_valid_json and not state.runtime_ledger_write_lock_fresh:
        failures.append("Router scheduler ledger is not valid JSON after a durable write")
    if state.runtime_ledger_write_lock_fresh and state.daemon_crashed_after_ledger_decode_error:
        failures.append("fresh runtime ledger write lock was treated as corruption")
    if (
        state.runtime_ledger_write_lock_fresh
        and state.runtime_ledger_write_lock_owner == "dead"
        and state.daemon_deferred_for_runtime_ledger_write
    ):
        failures.append("dead-owner write lock was deferred as live writer settlement")
    if (
        state.runtime_ledger_write_lock_owner == "dead"
        and not state.dead_owner_write_lock_takeover_recorded
    ):
        failures.append("fresh dead-owner write lock was not taken over with diagnostic evidence")
    if state.writer_died_while_holding_runtime_lock and not state.dead_owner_write_lock_takeover_recorded:
        failures.append("writer death while holding runtime lock was not recorded as takeover evidence")
    if (
        state.dead_owner_write_lock_takeover_recorded
        and state.lifecycle == "active"
        and not state.dead_owner_recovery_rejoined_flow
    ):
        failures.append("dead-owner write lock recovery did not rejoin normal daemon replay or terminal flow")
    if not state.controller_action_ledger_valid_json:
        failures.append("Controller action ledger is not valid JSON after a durable write")
    if not state.durable_ledger_writes_atomic:
        failures.append("runtime ledgers are written without atomic replace semantics")
    if not state.router_scheduler_single_writer:
        failures.append("Router scheduler ledger has more than one writer")
    if state.daemon_crashed_after_ledger_decode_error:
        failures.append("Router daemon crashed after reading an invalid scheduler ledger")
    if state.daemon_status_active_after_lock_error:
        failures.append("daemon status reported active after lock error")
    if state.daemon_status_active_without_process:
        failures.append("daemon status reported active without a live process")
    if state.controller_called_router_next_as_metronome:
        failures.append("Controller used diagnostic Router next/run-until-wait as the normal runtime metronome")
    if state.mailbox_consumption_count > 1:
        failures.append("mailbox evidence was consumed more than once")
    if state.controller_action_done and not state.controller_receipt_present:
        failures.append("Controller action was marked done without a Controller receipt")
    if (
        state.startup_controller_receipt_consumed
        and not (
            state.startup_controller_receipt_present
            and state.startup_bootstrap_flag_current
            and not state.startup_bootstrap_pending_action_open
            and state.startup_router_row_reconciled
        )
    ):
        failures.append("Router consumed startup receipt without synchronizing bootstrap flag, pending action, and Router row")
    if (
        state.startup_controller_receipt_consumed
        and not state.startup_next_row_scheduled_after_receipt
        and not state.controller_core_loaded
    ):
        failures.append("Router consumed startup receipt but did not schedule the next startup row")
    if state.startup_controller_receipt_present and state.startup_same_action_reissue_count > 1:
        failures.append("Router reissued the same startup Controller action after a done receipt")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and not state.controller_missing_deliverable_repair_pending
        and not state.controller_missing_deliverable_blocker_recorded
        and state.controller_missing_deliverable_repair_attempts == 0
        and state.controller_missing_deliverable_repair_failed_receipts == 0
    ):
        failures.append("stateful Controller receipt was marked done before Router-visible postcondition evidence existed")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_blocker_recorded
    ):
        failures.append("stateful missing deliverable blocker was recorded while a repair action was still pending")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_failed_receipts > state.controller_missing_deliverable_repair_attempts
    ):
        failures.append("stateful missing deliverable failed receipt count exceeded issued repair attempts")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_pending_attempt != state.controller_missing_deliverable_repair_attempts
    ):
        failures.append("stateful missing deliverable pending repair attempt did not match latest issued attempt")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and (
            state.controller_missing_deliverable_escalated_before_budget
            or (
                state.controller_missing_deliverable_blocker_recorded
                and state.controller_missing_deliverable_repair_failed_receipts < 2
            )
        )
    ):
        failures.append("stateful missing deliverable escalated before Controller repair attempts were exhausted")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_receipt_present
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_failed_receipts >= 2
        and not state.controller_missing_deliverable_repair_pending
        and not state.controller_missing_deliverable_blocker_recorded
    ):
        failures.append("stateful missing deliverable exhausted repair attempts without control blocker")
    if (
        state.controller_action_requires_stateful_postcondition
        and state.controller_action_done
        and not state.controller_stateful_postcondition_evidence_written
    ) or state.router_cleared_stateful_receipt_without_postcondition_evidence:
        failures.append("Router cleared stateful Controller receipt without Router-visible postcondition evidence")
    if state.controller_role_confirmed and not state.controller_boundary_confirmation_written:
        failures.append("Controller role was confirmed without controller boundary confirmation artifact")
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
        if state.terminal_controller_cleanup_best_effort_failed and not state.terminal_fence_written:
            failures.append("terminal cleanup failure blocked immediate daemon fence")
        if not state.terminal_fence_written:
            failures.append("terminal lifecycle missing immediate daemon fence")
        if not state.terminal_projection_refreshed:
            failures.append("terminal lifecycle did not refresh runtime projections")
        if not state.terminal_next_step_cleared:
            failures.append("terminal projection still exposes a nonterminal next step")
        if state.startup_row_scheduled_after_terminal_fence:
            failures.append("terminal lifecycle scheduled startup work")
        if state.heartbeat_binding_scheduled_after_terminal_fence:
            failures.append("terminal lifecycle scheduled heartbeat binding work")
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
    _invariant("router_scheduler_ledger_stays_parseable", "Router scheduler ledger is not valid JSON after a durable write"),
    _invariant("controller_action_ledger_stays_parseable", "Controller action ledger is not valid JSON after a durable write"),
    _invariant("runtime_ledgers_use_atomic_replace", "runtime ledgers are written without atomic replace semantics"),
    _invariant("router_scheduler_ledger_single_writer", "Router scheduler ledger has more than one writer"),
    _invariant("daemon_does_not_crash_on_corrupted_scheduler_ledger", "Router daemon crashed after reading an invalid scheduler ledger"),
    _invariant("dead_owner_write_lock_not_deferred_as_live_writer", "dead-owner write lock was deferred as live writer settlement"),
    _invariant("dead_owner_write_lock_takeover_records_evidence", "fresh dead-owner write lock was not taken over with diagnostic evidence"),
    _invariant("writer_death_records_lock_incident", "writer death while holding runtime lock was not recorded as takeover evidence"),
    _invariant("dead_owner_recovery_rejoins_flow", "dead-owner write lock recovery did not rejoin normal daemon replay or terminal flow"),
    _invariant("daemon_status_matches_error_lock", "daemon status reported active after lock error"),
    _invariant("daemon_status_matches_live_process", "daemon status reported active without a live process"),
    _invariant("daemon_wait_has_wait_target_metadata", "daemon-owned role wait lacks Router-authored wait target metadata"),
    _invariant("wait_target_names_role_evidence_and_reminder", "wait target metadata does not name role, evidence, and reminder text"),
    _invariant("report_reminder_requires_fresh_liveness_probe", "report reminder was sent without a fresh role liveness probe"),
    _invariant(
        "wait_target_reminder_is_executable_controller_work",
        "wait target reminder was not handled as an executable Controller action with receipt metadata",
    ),
    _invariant("controller_does_not_trust_cached_liveness", "Controller trusted cached role liveness instead of probing during standby"),
    _invariant("ack_wait_ten_minutes_routes_blocker", "ACK wait reached ten minutes without Router-visible blocker"),
    _invariant("lost_role_routes_to_pm_blocker", "lost role wait did not route to PM blocker recovery"),
    _invariant("recorded_external_event_closes_matching_wait", "recorded external event left matching Controller wait row open"),
    _invariant("external_event_wait_closure_is_router_owned", "recorded external event was not reconciled by Router-owned wait closure"),
    _invariant("next_wait_after_event_closure", "Router opened next wait before closing satisfied external-event wait"),
    _invariant("controller_does_not_close_external_event_wait", "Controller closed external-event wait instead of Router"),
    _invariant("controller_local_wait_does_not_remind_itself", "Controller sent a reminder to itself instead of self-auditing local action ledger"),
    _invariant("controller_local_wait_self_audits", "Controller-local wait did not self-audit action ledger and receipts"),
    _invariant("current_work_names_packet_holder", "packet holder is active but current_work does not name the packet holder"),
    _invariant("current_work_names_passive_reconciliation_owner", "passive reconciliation wait is active but current_work does not name the internal owner"),
    _invariant("current_work_names_router_internal_owner", "Router internal work is active but current_work does not name Router"),
    _invariant("role_current_work_has_owner_key", "role current_work owner lacks owner key"),
    _invariant("controller_not_runtime_metronome", "Controller used diagnostic Router next/run-until-wait as the normal runtime metronome"),
    _invariant("mailbox_evidence_consumed_once", "mailbox evidence was consumed more than once"),
    _invariant("controller_done_requires_receipt", "Controller action was marked done without a Controller receipt"),
    _invariant(
        "startup_receipt_syncs_bootstrap_and_router_row",
        "Router consumed startup receipt without synchronizing bootstrap flag, pending action, and Router row",
    ),
    _invariant("startup_receipt_schedules_next_row", "Router consumed startup receipt but did not schedule the next startup row"),
    _invariant("startup_done_receipt_not_reissued", "Router reissued the same startup Controller action after a done receipt"),
    _invariant("stateful_controller_receipt_requires_postcondition_evidence", "stateful Controller receipt was marked done before Router-visible postcondition evidence existed"),
    _invariant("stateful_missing_deliverable_repairs_before_blocker", "stateful missing deliverable escalated before Controller repair attempts were exhausted"),
    _invariant("stateful_missing_deliverable_no_blocker_while_repair_pending", "stateful missing deliverable blocker was recorded while a repair action was still pending"),
    _invariant("stateful_missing_deliverable_failure_count_bounded_by_issued_attempts", "stateful missing deliverable failed receipt count exceeded issued repair attempts"),
    _invariant("stateful_missing_deliverable_pending_attempt_matches_latest_issue", "stateful missing deliverable pending repair attempt did not match latest issued attempt"),
    _invariant("stateful_missing_deliverable_blocks_after_budget", "stateful missing deliverable exhausted repair attempts without control blocker"),
    _invariant("router_clears_stateful_receipt_only_after_postcondition_evidence", "Router cleared stateful Controller receipt without Router-visible postcondition evidence"),
    _invariant("controller_role_confirmation_requires_boundary_artifact", "Controller role was confirmed without controller boundary confirmation artifact"),
    _invariant("controller_receipt_updates_router_owned_fact", "Router cleared Controller receipt without updating Router-owned internal action fact"),
    _invariant("same_controller_action_not_reissued_after_receipt", "Router reissued the same Controller action after a done receipt because Router-owned fact stayed stale"),
    _invariant("foreground_controller_handles_pending_controller_action", "Foreground Controller ended while an executable Controller action was pending"),
    _invariant("foreground_controller_stays_attached_when_daemon_has_no_ready_action", "Foreground Controller ended while the Router daemon was live and no Controller action was ready"),
    _invariant("controller_stays_attached_at_ordinary_wait", "Controller stopped at an ordinary daemon-owned wait"),
    _invariant("foreground_controller_standby_keeps_turn_open", "Foreground Controller ended instead of staying in standby for a live daemon-owned role wait"),
    _invariant("foreground_standby_does_not_use_router_metronome", "Foreground standby used diagnostic Router next/run-until-wait instead of daemon status and action ledger"),
    _invariant("foreground_standby_polls_daemon_and_ledger", "Foreground standby did not poll daemon status and Controller action ledger"),
    _invariant("heartbeat_does_not_start_second_daemon", "heartbeat started a second Router daemon while one was live"),
    _invariant("terminal_lifecycle_writes_immediate_fence", "terminal lifecycle missing immediate daemon fence"),
    _invariant("terminal_cleanup_failure_does_not_block_fence", "terminal cleanup failure blocked immediate daemon fence"),
    _invariant("terminal_lifecycle_refreshes_projections", "terminal lifecycle did not refresh runtime projections"),
    _invariant("terminal_projection_clears_nonterminal_next_step", "terminal projection still exposes a nonterminal next step"),
    _invariant("terminal_scheduler_blocks_startup_rows", "terminal lifecycle scheduled startup work"),
    _invariant("terminal_scheduler_blocks_heartbeat_binding", "terminal lifecycle scheduled heartbeat binding work"),
    _invariant("terminal_cleanup_stops_runtime", "terminal lifecycle left daemon, Controller, roles, heartbeat, or route work active"),
)
