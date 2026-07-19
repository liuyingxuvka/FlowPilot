"""Invariant helpers for ``flowpilot_daemon_reconciliation_model``."""

from __future__ import annotations

from flowguard import Invariant, InvariantResult

from flowpilot_daemon_reconciliation_model_state import State


def invariant_failures(state: State) -> list[str]:
    failures: list[str] = []
    durable_receipt_exists = state.controller_receipt_status in {"done", "blocked"}
    durable_role_output_exists = state.role_output_ledger_submitted or state.canonical_artifact_exists
    durable_card_bundle_ack_exists = state.startup_card_bundle_ack_resolved
    durable_controller_boundary_exists = (
        state.controller_boundary_artifact_exists
        or state.controller_boundary_action_reconciled
        or state.controller_boundary_scheduler_reconciled
    )
    durable_evidence_exists = (
        durable_receipt_exists
        or durable_role_output_exists
        or durable_card_bundle_ack_exists
        or durable_controller_boundary_exists
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

    if state.foreground_start_fatal_from_active_writer:
        failures.append("foreground start command failed on active runtime writer instead of waiting and retrying")

    if (
        state.foreground_start_command_active
        and state.foreground_start_returns_live_daemon_status
        and state.runtime_writer_active
    ):
        failures.append("foreground start reported live daemon status before runtime writer settled")

    if (
        state.foreground_start_retries_after_writer_finishes
        and not state.foreground_start_waits_for_runtime_writer
    ):
        failures.append("foreground start retried runtime read without first waiting on the active writer")

    if state.foreground_start_run_allocation_count > 1:
        failures.append("one foreground start command allocated more than one current run")

    if (
        state.foreground_start_returns_live_daemon_status
        and state.foreground_start_completed_actions_before_writer
        and not state.foreground_start_completed_actions_preserved
    ):
        failures.append("foreground start retry lost completed folded-action evidence")

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

    if state.startup_card_bundle_ack_resolved:
        if state.user_intake_packet_with_controller:
            failures.append("startup user_intake was Controller-held instead of Router-owned startup material")
        if state.next_action_computed and not (
            state.startup_card_bundle_wait_action_reconciled
            and state.startup_card_bundle_wait_scheduler_reconciled
        ):
            failures.append("system-card bundle ACK resolved but its wait row stayed open")
        if (
            state.startup_card_bundle_wait_action_reconciled
            != state.startup_card_bundle_wait_scheduler_reconciled
        ):
            failures.append("system-card bundle ACK wait action and scheduler reconciliation disagreed")
        if state.next_action_computed and not state.startup_card_bundle_ack_completion_normalized:
            failures.append("system-card bundle ACK completion was not normalized to resolved")
        if state.next_action_computed and state.user_intake_delivery_action_queued:
            failures.append("PM system-card ACK queued user_intake deliver_mail before startup activation")
        if state.user_intake_released_to_pm or state.user_intake_release_count > 0:
            failures.append("PM system-card ACK released startup user_intake before startup activation")
        if (
            state.unrelated_controller_action_repeated_after_ack
            and state.user_intake_router_owned
            and state.user_intake_packet_to_pm
            and not state.user_intake_released_to_pm
        ):
            failures.append("Router repeated unrelated Controller work after PM ACK before startup fact review")

    if state.controller_receipt_action_class == "startup_bootloader":
        startup_fold_complete = (
            state.controller_receipt_reconciled
            and state.pending_cleared_after_receipt
            and state.stateful_postconditions_applied
            and state.startup_row_reconciled
            and state.startup_postcondition_satisfied
            and state.startup_reconciliation_owner == "startup_bootloader_controller_receipt"
        )
        if state.startup_receipt_apply_split and state.startup_receipt_requires_apply_to_advance:
            failures.append("startup Controller receipt required a separate apply path to advance")
        if state.startup_receipt_apply_split and state.next_action_computed:
            failures.append("startup Controller receipt reached next action through split receipt/apply ownership")
        if state.startup_receipt_single_owner_folded and not startup_fold_complete:
            failures.append("startup bootloader receipt single-owner fold did not update every durable projection")
        if state.startup_row_reconciled and not state.startup_postcondition_satisfied:
            failures.append("startup bootloader row was reconciled without its postcondition")
        if (
            state.controller_receipt_status == "done"
            and state.startup_row_reconciled
            and state.startup_reconciliation_owner != "startup_bootloader_controller_receipt"
        ):
            failures.append("startup bootloader row was reconciled by the wrong owner")
        elif state.startup_row_reconciled and state.startup_reconciliation_owner not in {
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
        if (
            state.startup_bootloader_receipt_kind == "native_startup_intake"
            and state.controller_receipt_status == "done"
            and state.controller_receipt_payload_quality == "complete"
            and state.unsupported_startup_receipt_action
        ):
            failures.append("native startup intake Controller receipt was unsupported despite a complete native UI payload")
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
    _invariant("foreground_start_waits_on_active_runtime_writer", "foreground start command failed on active runtime writer instead of waiting and retrying"),
    _invariant("foreground_start_reports_after_runtime_writer_settlement", "foreground start reported live daemon status before runtime writer settled"),
    _invariant("foreground_start_retry_requires_writer_wait", "foreground start retried runtime read without first waiting on the active writer"),
    _invariant("foreground_start_retry_keeps_one_run_allocation", "one foreground start command allocated more than one current run"),
    _invariant("foreground_start_retry_preserves_completed_action_evidence", "foreground start retry lost completed folded-action evidence"),
    _invariant("mail_delivery_receipt_folds_or_blocks", "mail delivery receipt reached next action without packet ledger fold or control blocker"),
    _invariant("mail_delivery_postcondition_folds_packet_ledger", "mail delivery postcondition was applied without moving the packet ledger and Router flag together"),
    _invariant("mail_delivery_flag_requires_packet_release", "mail delivery Router flag was set while the packet still belonged to Controller"),
    _invariant("pm_mail_delivery_decision_consumed", "PM mail delivery repair decision stayed only in durable storage"),
    _invariant("mail_delivery_reissue_has_repair_transaction", "mail delivery reissue was queued without a repair transaction"),
    _invariant("mail_delivery_repair_transaction_queues_reissue", "mail delivery repair transaction did not queue the reissue"),
    _invariant("card_bundle_ack_resolves_wait_row", "system-card bundle ACK resolved but its wait row stayed open"),
    _invariant("card_bundle_ack_action_scheduler_agree", "system-card bundle ACK wait action and scheduler reconciliation disagreed"),
    _invariant("card_bundle_ack_completion_normalized", "system-card bundle ACK completion was not normalized to resolved"),
    _invariant("startup_user_intake_router_owned", "startup user_intake was Controller-held instead of Router-owned startup material"),
    _invariant("pm_ack_does_not_queue_controller_user_intake_delivery", "PM system-card ACK queued user_intake deliver_mail before startup activation"),
    _invariant("pm_ack_does_not_release_user_intake_before_activation", "PM system-card ACK released startup user_intake before startup activation"),
    _invariant("pm_ack_preempts_unrelated_controller_loop", "Router repeated unrelated Controller work after PM ACK before startup fact review"),
    _invariant("startup_receipt_does_not_depend_on_later_apply_path", "startup Controller receipt required a separate apply path to advance"),
    _invariant("startup_receipt_single_owner_before_next_action", "startup Controller receipt reached next action through split receipt/apply ownership"),
    _invariant("startup_receipt_single_owner_fold_updates_all_projections", "startup bootloader receipt single-owner fold did not update every durable projection"),
    _invariant("startup_bootloader_reconciles_with_postcondition", "startup bootloader row was reconciled without its postcondition"),
    _invariant("startup_bootloader_reconciliation_owner", "startup bootloader row was reconciled by the wrong owner"),
    _invariant("startup_bootloader_no_false_pm_blocker_after_reconciled", "startup bootloader row produced a control blocker after it was already reconciled"),
    _invariant("startup_missing_postcondition_uses_mechanical_reissue_budget", "startup bootloader missing postcondition was sent to PM before mechanical reissue budget was exhausted"),
    _invariant("startup_success_resolves_same_action_blocker", "startup bootloader blocker stayed active after its postcondition was reconciled"),
    _invariant("startup_success_prevents_pm_repair_action_queue", "PM repair action was queued after startup bootloader postcondition reconciliation"),
    _invariant("unsupported_startup_receipt_not_pm_repair_after_success", "unsupported startup bootloader receipt was escalated to PM repair after the startup postcondition was satisfied"),
    _invariant("native_startup_intake_receipt_supported", "native startup intake Controller receipt was unsupported despite a complete native UI payload"),
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
