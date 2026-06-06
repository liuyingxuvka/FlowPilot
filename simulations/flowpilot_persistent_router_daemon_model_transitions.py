"""Transitions for the FlowPilot persistent Router daemon model."""

from __future__ import annotations

from typing import Iterable

from flowguard import FunctionResult

from flowpilot_persistent_router_daemon_model_state import Action, State, Tick, Transition, _step


class PersistentRouterDaemonStep:
    """Model one persistent Router/Controller tick.

    Input x State -> Set(Output x State)
    reads: daemon lock/status, router state, mailbox evidence, controller
    action ledger, controller receipts, manual resume wake event, role cohort
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
        "patrol_state",
        "role_binding_memory",
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
                manual_resume_binding_active=True,
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
            ),
        )
        return

    if state.stop_requested:
        yield Transition(
            "terminal_stop_reconciles_daemon_controller_roles",
            _step(
                state,
                lifecycle="terminal",
                terminal_fence_written=True,
                terminal_controller_cleanup_best_effort_failed=bool(
                    state.runtime_ledger_write_lock_fresh
                    and state.runtime_ledger_write_lock_owner in {"live", "unknown"}
                ),
                terminal_projection_refreshed=True,
                terminal_next_step_cleared=True,
                daemon_alive=False,
                daemon_lock_state="terminal",
                daemon_writer_count=0,
                controller_core_loaded=False,
                controller_attached=False,
                foreground_standby_active=False,
                foreground_standby_polling_daemon_status=False,
                foreground_standby_polling_action_ledger=False,
                roles_live=False,
                manual_resume_binding_active=False,
                current_wait="terminal",
                event_wait_action_open=False,
                external_event_recorded=False,
                external_event_matches_wait=False,
                event_wait_closed_by_router=False,
                stale_event_wait_row_open=False,
                next_wait_opened_before_event_wait_closed=False,
                controller_closed_event_wait=False,
                wait_target_metadata_present=False,
                controller_action_pending=False,
                controller_action_ready=False,
                startup_bootstrap_pending_action_open=False,
                startup_row_scheduled_after_terminal_fence=False,
                patrol_binding_scheduled_after_terminal_fence=False,
                unsupported_historical_waiting_for_role_null=False,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="none",
                current_work_owner_key="",
                current_work_task_visible=False,
                current_work_source="none",
                route_work_allowed=False,
            ),
        )
        return

    if state.runtime_ledger_write_lock_stale and state.runtime_ledger_write_lock_owner == "self":
        if state.runtime_write_lock_target_valid_json and not state.runtime_write_lock_tmp_file_present:
            yield Transition(
                "daemon_clears_self_owned_stale_write_lock_and_replays",
                _step(
                    state,
                    router_scheduler_ledger_valid_json=True,
                    controller_action_ledger_valid_json=True,
                    runtime_ledger_write_lock_fresh=False,
                    runtime_ledger_write_lock_stale=False,
                    runtime_ledger_write_lock_owner="none",
                    daemon_deferred_for_runtime_ledger_write=False,
                    self_owned_write_lock_takeover_recorded=True,
                    self_owned_write_lock_recovery_rejoined_flow=True,
                    runtime_write_lock_cleanup_failure_recorded=True,
                    runtime_write_lock_mechanical_settlement_recorded=True,
                    startup_bootstrap_pending_action_open=True,
                    startup_bootstrap_flag_current=False,
                    startup_same_action_reissue_count=state.startup_same_action_reissue_count + 1,
                    current_work_owner_kind="controller",
                    current_work_owner_key="controller",
                    current_work_task_visible=True,
                    current_work_source="pending_action",
                ),
            )
        else:
            yield Transition(
                "daemon_blocks_unsafe_self_owned_stale_write_lock_for_repair",
                _step(
                    state,
                    daemon_deferred_for_runtime_ledger_write=False,
                    runtime_write_lock_mechanical_settlement_recorded=True,
                    stop_requested=True,
                ),
            )
        return

    if state.runtime_ledger_write_lock_fresh and state.runtime_ledger_write_lock_owner in {"live", "unknown"}:
        yield Transition(
            "user_requests_terminal_stop_while_cleanup_ledger_locked",
            _step(state, stop_requested=True),
        )
        nested_status_save_risk = (
            not state.controller_core_loaded
            and not state.startup_bootstrap_pending_action_open
            and not state.startup_controller_receipt_present
            and not state.nested_wait_status_write_lock
        )
        if nested_status_save_risk:
            yield Transition(
                "daemon_defers_runtime_ledger_wait_after_nested_state_lock",
                _step(
                    state,
                    router_scheduler_ledger_valid_json=True,
                    runtime_ledger_write_lock_fresh=False,
                    runtime_ledger_write_lock_stale=False,
                    runtime_ledger_write_lock_owner="none",
                    daemon_deferred_for_runtime_ledger_write=True,
                    nested_wait_status_write_lock=True,
                    daemon_deferred_after_nested_write_lock=True,
                    runtime_write_lock_mechanical_settlement_recorded=True,
                ),
            )
        else:
            yield Transition(
                "daemon_defers_runtime_ledger_read_until_next_tick",
                _step(
                    state,
                    router_scheduler_ledger_valid_json=True,
                    runtime_ledger_write_lock_fresh=False,
                    runtime_ledger_write_lock_stale=False,
                    runtime_ledger_write_lock_owner="none",
                    daemon_deferred_for_runtime_ledger_write=True,
                    runtime_write_lock_mechanical_settlement_recorded=True,
                ),
            )
        return

    if state.runtime_ledger_write_lock_fresh and state.runtime_ledger_write_lock_owner == "dead":
        yield Transition(
            "daemon_takes_over_fresh_dead_owner_write_lock_and_replays",
            _step(
                state,
                router_scheduler_ledger_valid_json=True,
                runtime_ledger_write_lock_fresh=False,
                runtime_ledger_write_lock_stale=False,
                runtime_ledger_write_lock_owner="none",
                daemon_deferred_for_runtime_ledger_write=False,
                dead_owner_write_lock_takeover_recorded=True,
                writer_died_while_holding_runtime_lock=True,
                dead_owner_recovery_rejoined_flow=True,
                runtime_write_lock_mechanical_settlement_recorded=True,
            ),
        )
        return

    if (
        state.daemon_alive
        and state.daemon_lock_state == "live"
        and not state.daemon_deferred_for_runtime_ledger_write
        and state.current_wait == "none"
        and not state.controller_action_pending
    ):
        yield Transition(
            "runtime_live_writer_write_lock_appears_during_daemon_read",
            _step(
                state,
                router_scheduler_ledger_valid_json=False,
                runtime_ledger_write_lock_fresh=True,
                runtime_ledger_write_lock_owner="live",
                runtime_write_lock_mechanical_settlement_recorded=False,
            ),
        )
        yield Transition(
            "runtime_dead_owner_write_lock_appears_during_daemon_read",
            _step(
                state,
                router_scheduler_ledger_valid_json=True,
                runtime_ledger_write_lock_fresh=False,
                runtime_ledger_write_lock_stale=False,
                runtime_ledger_write_lock_owner="none",
                daemon_deferred_for_runtime_ledger_write=False,
                dead_owner_write_lock_takeover_recorded=True,
                writer_died_while_holding_runtime_lock=True,
                dead_owner_recovery_rejoined_flow=True,
                runtime_write_lock_mechanical_settlement_recorded=True,
            ),
        )
        if (
            not state.self_owned_write_lock_takeover_recorded
            and not state.controller_core_loaded
            and not state.startup_bootstrap_pending_action_open
            and not state.startup_controller_receipt_present
        ):
            yield Transition(
                "runtime_self_owned_stale_write_lock_left_after_successful_write",
                _step(
                    state,
                    router_scheduler_ledger_valid_json=True,
                    controller_action_ledger_valid_json=True,
                    runtime_ledger_write_lock_fresh=False,
                    runtime_ledger_write_lock_stale=True,
                    runtime_ledger_write_lock_owner="self",
                    runtime_write_lock_target_valid_json=True,
                    runtime_write_lock_tmp_file_present=False,
                    runtime_write_lock_cleanup_failure_recorded=True,
                    runtime_write_lock_mechanical_settlement_recorded=False,
                ),
            )

    if not state.controller_core_loaded and not state.startup_controller_receipt_consumed:
        if not state.startup_bootstrap_pending_action_open and not state.startup_controller_receipt_present:
            yield Transition(
                "daemon_schedules_startup_bootloader_row_before_controller_core",
                _step(
                    state,
                    startup_bootstrap_pending_action_open=True,
                    startup_bootstrap_flag_current=False,
                    startup_same_action_reissue_count=1,
                    current_work_owner_kind="controller",
                    current_work_owner_key="controller",
                    current_work_task_visible=True,
                    current_work_source="pending_action",
                ),
            )
            yield Transition(
                "user_requests_terminal_stop_during_startup_scheduling",
                _step(state, stop_requested=True),
            )
            return
        if state.startup_bootstrap_pending_action_open and not state.startup_controller_receipt_present:
            yield Transition(
                "controller_executes_startup_bootloader_row_writes_receipt",
                _step(
                    state,
                    startup_controller_receipt_present=True,
                ),
            )
            yield Transition(
                "user_requests_terminal_stop_during_startup_scheduling",
                _step(state, stop_requested=True),
            )
            return
        if state.startup_bootstrap_pending_action_open and state.startup_controller_receipt_present:
            yield Transition(
                "daemon_consumes_startup_receipt_clears_pending_and_schedules_next",
                _step(
                    state,
                    startup_controller_receipt_consumed=True,
                    startup_bootstrap_flag_current=True,
                    startup_bootstrap_pending_action_open=False,
                    startup_router_row_reconciled=True,
                    startup_next_row_scheduled_after_receipt=True,
                    current_work_owner_kind="router",
                    current_work_owner_key="router",
                    current_work_task_visible=True,
                    current_work_source="router_daemon",
                ),
            )
            yield Transition(
                "user_requests_terminal_stop_during_startup_scheduling",
                _step(state, stop_requested=True),
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
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
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
                wait_target_metadata_present=True,
                wait_target_expected_evidence_visible=True,
                controller_action_pending=True,
                controller_action_ready=True,
                controller_action_done=False,
                controller_receipt_present=False,
                controller_rescanned_after_receipt=False,
                controller_action_requires_stateful_postcondition=False,
                controller_stateful_postcondition_evidence_written=False,
                controller_boundary_confirmation_written=False,
                controller_role_confirmed=False,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_repair_attempts=0,
                controller_missing_deliverable_repair_failed_receipts=0,
                controller_missing_deliverable_pending_attempt=0,
                controller_missing_deliverable_blocker_recorded=False,
                controller_missing_deliverable_escalated_before_budget=False,
                router_cleared_stateful_receipt_without_postcondition_evidence=False,
                same_controller_action_reissue_count=state.same_controller_action_reissue_count + 1,
                foreground_standby_active=False,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="controller",
                current_work_owner_key="controller",
                current_work_task_visible=True,
                current_work_source="pending_action",
            ),
        )
        yield Transition(
            "router_issues_stateful_controller_boundary_action_to_ledger",
            _step(
                state,
                current_wait="controller_receipt",
                wait_target_metadata_present=True,
                wait_target_expected_evidence_visible=True,
                controller_action_pending=True,
                controller_action_ready=True,
                controller_action_done=False,
                controller_receipt_present=False,
                controller_rescanned_after_receipt=False,
                controller_action_requires_stateful_postcondition=True,
                controller_stateful_postcondition_evidence_written=False,
                controller_boundary_confirmation_written=False,
                controller_role_confirmed=False,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_repair_attempts=0,
                controller_missing_deliverable_repair_failed_receipts=0,
                controller_missing_deliverable_pending_attempt=0,
                controller_missing_deliverable_blocker_recorded=False,
                controller_missing_deliverable_escalated_before_budget=False,
                router_cleared_stateful_receipt_without_postcondition_evidence=False,
                same_controller_action_reissue_count=state.same_controller_action_reissue_count + 1,
                foreground_standby_active=False,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="controller",
                current_work_owner_key="controller",
                current_work_task_visible=True,
                current_work_source="pending_action",
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
        and not state.packet_holder_projection_needed
        and not state.passive_reconciliation_wait_open
        and not state.router_internal_projection_needed
        and state.current_work_source == "router_daemon"
    ):
        yield Transition(
            "daemon_projects_packet_holder_current_work_owner",
            _step(
                state,
                unsupported_historical_waiting_for_role_null=True,
                active_packet_holder="project_manager",
                packet_holder_projection_needed=True,
                current_work_owner_kind="role",
                current_work_owner_key="project_manager",
                current_work_task_visible=True,
                current_work_source="packet_ledger",
            ),
        )
        yield Transition(
            "daemon_projects_passive_reconciliation_current_work_owner",
            _step(
                state,
                unsupported_historical_waiting_for_role_null=True,
                passive_reconciliation_wait_open=True,
                current_work_owner_kind="controller",
                current_work_owner_key="controller",
                current_work_task_visible=True,
                current_work_source="passive_wait",
            ),
        )
        yield Transition(
            "daemon_projects_router_internal_current_work_owner",
            _step(
                state,
                unsupported_historical_waiting_for_role_null=True,
                router_internal_projection_needed=True,
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
            ),
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
                unsupported_historical_waiting_for_role_null=False,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="role",
                current_work_owner_key="target_role",
                current_work_task_visible=True,
                current_work_source="current_wait",
                event_wait_action_open=False,
                external_event_recorded=False,
                external_event_matches_wait=False,
                event_wait_closed_by_router=False,
                stale_event_wait_row_open=False,
                next_wait_opened_before_event_wait_closed=False,
                controller_closed_event_wait=False,
                wait_target_metadata_present=True,
                wait_target_names_role=True,
                wait_target_expected_evidence_visible=True,
                wait_target_reminder_text_present=True,
                foreground_standby_active=True,
                foreground_standby_polling_daemon_status=True,
                foreground_standby_polling_action_ledger=True,
            ),
        )
        yield Transition(
            "router_enters_report_wait_with_liveness_obligation",
            _step(
                state,
                current_wait="report",
                unsupported_historical_waiting_for_role_null=False,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="role",
                current_work_owner_key="target_role",
                current_work_task_visible=True,
                current_work_source="current_wait",
                event_wait_action_open=True,
                external_event_recorded=False,
                external_event_matches_wait=False,
                event_wait_closed_by_router=False,
                stale_event_wait_row_open=False,
                next_wait_opened_before_event_wait_closed=False,
                controller_closed_event_wait=False,
                wait_target_metadata_present=True,
                wait_target_names_role=True,
                wait_target_expected_evidence_visible=True,
                wait_target_reminder_text_present=True,
                liveness_check_required=True,
                foreground_standby_active=True,
                foreground_standby_polling_daemon_status=True,
                foreground_standby_polling_action_ledger=True,
            ),
        )
        yield Transition(
            "router_enters_controller_local_wait_for_self_audit",
            _step(
                state,
                current_wait="controller_local",
                unsupported_historical_waiting_for_role_null=True,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="controller",
                current_work_owner_key="controller",
                current_work_task_visible=True,
                current_work_source="current_wait",
                event_wait_action_open=False,
                wait_target_metadata_present=True,
                wait_target_expected_evidence_visible=True,
                controller_local_self_audit_done=True,
                foreground_standby_active=True,
                foreground_standby_polling_daemon_status=True,
                foreground_standby_polling_action_ledger=True,
            ),
        )
        yield Transition(
            "controller_local_wait_self_audits_ledger",
            _step(
                state,
                current_wait="controller_local",
                unsupported_historical_waiting_for_role_null=True,
                active_packet_holder="",
                packet_holder_projection_needed=False,
                passive_reconciliation_wait_open=False,
                router_internal_projection_needed=False,
                current_work_owner_kind="controller",
                current_work_owner_key="controller",
                current_work_task_visible=True,
                current_work_source="current_wait",
                event_wait_action_open=False,
                wait_target_metadata_present=True,
                wait_target_expected_evidence_visible=True,
                controller_local_self_audit_done=True,
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

    if (
        state.controller_action_pending
        and state.controller_action_ready
        and not state.controller_receipt_present
        and state.controller_action_requires_stateful_postcondition
    ):
        yield Transition(
            "controller_executes_stateful_action_writes_postcondition_evidence_and_receipt",
            _step(
                state,
                controller_receipt_present=True,
                controller_receipt_valid=True,
                controller_stateful_postcondition_evidence_written=True,
                controller_boundary_confirmation_written=True,
                controller_role_confirmed=True,
                controller_missing_deliverable_repair_pending=False,
            ),
        )
        yield Transition(
            "router_marks_stateful_receipt_incomplete_and_enqueues_repair",
            _step(
                state,
                controller_receipt_present=True,
                controller_receipt_valid=True,
                controller_stateful_postcondition_evidence_written=False,
                controller_boundary_confirmation_written=False,
                controller_role_confirmed=False,
                controller_missing_deliverable_repair_pending=True,
                controller_missing_deliverable_repair_attempts=1,
                controller_missing_deliverable_repair_failed_receipts=0,
                controller_missing_deliverable_pending_attempt=1,
                controller_missing_deliverable_blocker_recorded=False,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and state.controller_action_requires_stateful_postcondition
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_repair_attempts == state.controller_missing_deliverable_repair_failed_receipts + 1
        and state.controller_missing_deliverable_pending_attempt < 2
    ):
        yield Transition(
            "controller_completes_stateful_deliverable_repair",
            _step(
                state,
                controller_stateful_postcondition_evidence_written=True,
                controller_boundary_confirmation_written=True,
                controller_role_confirmed=True,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_pending_attempt=0,
            ),
        )
        yield Transition(
            "controller_submits_invalid_stateful_deliverable_repair_receipt",
            _step(
                state,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_repair_failed_receipts=state.controller_missing_deliverable_repair_failed_receipts + 1,
                controller_missing_deliverable_pending_attempt=0,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and state.controller_action_requires_stateful_postcondition
        and not state.controller_stateful_postcondition_evidence_written
        and state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_repair_attempts == state.controller_missing_deliverable_repair_failed_receipts + 1
        and state.controller_missing_deliverable_pending_attempt >= 2
    ):
        yield Transition(
            "controller_completes_stateful_deliverable_repair",
            _step(
                state,
                controller_stateful_postcondition_evidence_written=True,
                controller_boundary_confirmation_written=True,
                controller_role_confirmed=True,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_pending_attempt=0,
            ),
        )
        yield Transition(
            "router_escalates_missing_stateful_deliverable_after_repair_budget",
            _step(
                state,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_repair_failed_receipts=state.controller_missing_deliverable_repair_failed_receipts + 1,
                controller_missing_deliverable_pending_attempt=0,
                controller_missing_deliverable_blocker_recorded=True,
                stop_requested=True,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and state.controller_action_requires_stateful_postcondition
        and not state.controller_stateful_postcondition_evidence_written
        and not state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_repair_failed_receipts >= 1
        and state.controller_missing_deliverable_repair_failed_receipts < 2
    ):
        yield Transition(
            "router_enqueues_second_stateful_deliverable_repair",
            _step(
                state,
                controller_missing_deliverable_repair_pending=True,
                controller_missing_deliverable_repair_attempts=state.controller_missing_deliverable_repair_failed_receipts + 1,
                controller_missing_deliverable_pending_attempt=state.controller_missing_deliverable_repair_failed_receipts + 1,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and state.controller_action_requires_stateful_postcondition
        and not state.controller_stateful_postcondition_evidence_written
        and not state.controller_missing_deliverable_repair_pending
        and state.controller_missing_deliverable_repair_failed_receipts >= 2
    ):
        yield Transition(
            "router_escalates_missing_stateful_deliverable_after_repair_budget",
            _step(
                state,
                controller_missing_deliverable_repair_pending=False,
                controller_missing_deliverable_blocker_recorded=True,
                stop_requested=True,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_action_ready
        and not state.controller_receipt_present
        and not state.controller_action_requires_stateful_postcondition
    ):
        yield Transition(
            "controller_executes_action_and_writes_receipt",
            _step(
                state,
                controller_receipt_present=True,
                controller_receipt_valid=True,
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and not state.controller_action_done
        and state.controller_action_requires_stateful_postcondition
        and state.controller_stateful_postcondition_evidence_written
    ):
        yield Transition(
            "router_reconciles_stateful_receipt_after_postcondition_evidence",
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
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
            ),
        )
        return

    if (
        state.controller_action_pending
        and state.controller_receipt_present
        and not state.controller_action_done
        and not state.controller_action_requires_stateful_postcondition
    ):
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
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
            ),
        )
        return

    if state.current_wait == "ack" and not state.mailbox_evidence_present:
        if state.ack_wait_age_minutes < 3:
            yield Transition(
                "ack_wait_time_advances_before_reminder",
                _step(state, ack_wait_age_minutes=3),
            )
            return
        if state.ack_wait_age_minutes >= 3 and not state.ack_wait_reminder_sent:
            yield Transition(
                "controller_sends_ack_wait_reminder_at_three_minutes",
                _step(
                    state,
                    ack_wait_reminder_sent=True,
                    wait_target_reminder_controller_action_ready=True,
                    wait_target_reminder_receipt_recorded=True,
                    wait_target_reminder_updates_wait_metadata=True,
                ),
            )
            return
        if state.ack_wait_age_minutes < 10:
            yield Transition(
                "controller_records_ack_wait_blocker_at_ten_minutes",
                _step(state, ack_wait_age_minutes=10, ack_wait_blocker_recorded=True),
            )
            return
        if state.ack_wait_age_minutes >= 10 and not state.ack_wait_blocker_recorded:
            yield Transition(
                "controller_records_ack_wait_blocker_at_ten_minutes",
                _step(state, ack_wait_blocker_recorded=True),
            )
            return

    if state.current_wait == "report" and not state.mailbox_evidence_present:
        if state.report_wait_age_minutes < 10:
            yield Transition(
                "report_wait_time_advances_to_reminder",
                _step(state, report_wait_age_minutes=10),
            )
            return
        if state.report_wait_age_minutes >= 10 and not state.report_reminder_sent:
            yield Transition(
                "controller_sends_report_reminder_with_fresh_liveness_probe",
                _step(
                    state,
                    report_reminder_sent=True,
                    wait_target_reminder_controller_action_ready=True,
                    wait_target_reminder_receipt_recorded=True,
                    wait_target_reminder_updates_wait_metadata=True,
                    liveness_check_required=True,
                    liveness_probe_fresh=True,
                    liveness_probe_outcome="working",
                ),
            )
            yield Transition(
                "controller_reports_lost_role_wait_blocker",
                _step(
                    state,
                    report_reminder_sent=True,
                    wait_target_reminder_controller_action_ready=True,
                    wait_target_reminder_receipt_recorded=True,
                    wait_target_reminder_updates_wait_metadata=True,
                    liveness_check_required=True,
                    liveness_probe_fresh=True,
                    liveness_probe_outcome="lost",
                    role_liveness_blocker_recorded=True,
                ),
            )
        if state.report_reminder_sent and state.liveness_probe_outcome == "working":
            yield Transition(
                "healthy_role_continues_report_wait_after_probe",
                _step(
                    state,
                    report_reminder_sent=False,
                    report_wait_age_minutes=0,
                    wait_target_reminder_controller_action_ready=False,
                    wait_target_reminder_receipt_recorded=False,
                    wait_target_reminder_updates_wait_metadata=False,
                ),
            )

    if state.current_wait == "controller_local":
        if not state.controller_local_self_audit_done:
            yield Transition(
                "controller_local_wait_self_audits_ledger",
                _step(state, controller_local_self_audit_done=True),
            )
            yield Transition(
                "controller_local_wait_records_blocker_when_unfinished",
                _step(state, controller_local_self_audit_done=True, controller_local_blocker_recorded=True),
            )
            return
        if state.controller_local_blocker_recorded:
            yield Transition(
                "controller_local_wait_blocker_routes_to_pm",
                _step(
                    state,
                    current_wait="none",
                    stop_requested=True,
                    current_work_owner_kind="controller",
                    current_work_owner_key="controller",
                    current_work_task_visible=True,
                    current_work_source="current_wait",
                ),
            )
            return
        yield Transition(
            "controller_local_self_audit_clears_wait",
            _step(
                state,
                current_wait="none",
                controller_local_self_audit_done=False,
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
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
            "patrol_wakes_and_finds_live_daemon",
            _step(state, manual_resume_woke=True),
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
                external_event_recorded=True,
                external_event_matches_wait=state.current_wait == "report",
                event_wait_closed_by_router=state.current_wait == "report",
                event_wait_action_open=False,
                stale_event_wait_row_open=False,
                router_can_continue_after_evidence=True,
                current_wait="none",
                mailbox_wait_tick_observed=False,
                foreground_standby_active=False,
                current_work_owner_kind="router",
                current_work_owner_key="router",
                current_work_task_visible=True,
                current_work_source="router_daemon",
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
                next_wait_opened_before_event_wait_closed=False,
                stop_requested=True,
            ),
        )
        return

