"""Transition helpers for ``flowpilot_daemon_reconciliation_model``."""

from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from flowguard import FunctionResult

from flowpilot_daemon_reconciliation_model_state import Action, State, Tick, Transition


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
        "return_event_ledger",
        "packet_ledger",
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
        "packet_ledger",
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
        and state.foreground_start_command_active
        and state.foreground_start_reads_runtime_during_writer
        and not state.foreground_start_waits_for_runtime_writer
        and not state.next_action_computed
    ):
        yield Transition(
            "foreground_start_waits_for_active_runtime_writer",
            _step(state, foreground_start_waits_for_runtime_writer=True),
        )
        return

    if (
        state.runtime_writer_active
        and state.foreground_start_command_active
        and state.foreground_start_waits_for_runtime_writer
        and not state.foreground_start_retries_after_writer_finishes
        and not state.next_action_computed
    ):
        yield Transition(
            "foreground_start_retries_after_runtime_writer_finishes",
            _step(
                state,
                runtime_writer_active=False,
                runtime_settlement_waiting=False,
                runtime_settlement_progress_observed=False,
                foreground_start_retries_after_writer_finishes=True,
                foreground_start_completed_actions_preserved=True,
            ),
        )
        return

    if (
        state.foreground_start_command_active
        and state.foreground_start_retries_after_writer_finishes
        and not state.foreground_start_returns_live_daemon_status
        and not state.next_action_computed
    ):
        yield Transition(
            "foreground_start_returns_live_daemon_status_after_settlement",
            _step(
                state,
                foreground_start_command_active=False,
                foreground_start_returns_live_daemon_status=True,
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

    if (
        state.startup_card_bundle_ack_resolved
        and not state.startup_card_bundle_wait_action_reconciled
        and not state.next_action_computed
    ):
        if state.user_intake_router_owned and state.user_intake_packet_to_pm:
            yield Transition(
                "daemon_reconciles_card_bundle_ack_wait_without_user_intake_release",
                _step(
                    state,
                    startup_card_bundle_wait_action_reconciled=True,
                    startup_card_bundle_wait_scheduler_reconciled=True,
                    startup_card_bundle_ack_completion_normalized=True,
                    user_intake_released_to_pm=False,
                    user_intake_release_count=0,
                    user_intake_delivery_action_queued=False,
                    pending_action_kind="none",
                    pending_action_status="none",
                    next_action_computed=True,
                ),
            )
        else:
            yield Transition(
                "daemon_reconciles_card_bundle_ack_wait_without_user_intake",
                _step(
                    state,
                    startup_card_bundle_wait_action_reconciled=True,
                    startup_card_bundle_wait_scheduler_reconciled=True,
                    startup_card_bundle_ack_completion_normalized=True,
                    pending_action_kind="none",
                    pending_action_status="none",
                    next_action_computed=True,
                ),
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
            if not state.foreground_start_returns_live_daemon_status:
                yield Transition(
                    "foreground_start_observes_active_runtime_writer",
                    _step(
                        state,
                        runtime_writer_active=True,
                        foreground_start_command_active=True,
                        foreground_start_reads_runtime_during_writer=True,
                        foreground_start_run_allocation_count=1,
                        foreground_start_completed_actions_before_writer=True,
                    ),
                )
        if not state.startup_card_bundle_ack_resolved:
            yield Transition(
                "card_bundle_ack_arrives_while_user_intake_waits",
                _step(
                    state,
                    startup_card_bundle_ack_resolved=True,
                    user_intake_router_owned=True,
                    user_intake_packet_to_pm=True,
                    stale_daemon_snapshot_loaded=True,
                ),
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
                startup_receipt_single_owner_folded=True,
            ),
        )
        yield Transition(
            "daemon_folds_startup_receipt_with_single_owner",
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
                startup_receipt_single_owner_folded=True,
            ),
        )
        yield Transition(
            "daemon_folds_native_startup_intake_receipt_with_single_owner",
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
                startup_bootloader_receipt_kind="native_startup_intake",
                startup_receipt_single_owner_folded=True,
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
                startup_receipt_single_owner_folded=True,
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
            "manual_resume_opens_rehydrate_pending_action",
            _step(
                state,
                pending_action_kind="rehydrate_role_bindings",
                pending_action_status="pending",
                role_wait_cleared_after_event=False,
                stale_daemon_snapshot_loaded=True,
            ),
        )
        return

    if (
        state.controller_receipt_action_class == "startup_bootloader"
        and state.controller_receipt_status == "done"
        and state.startup_receipt_single_owner_folded
        and not state.startup_receipt_replay_is_noop
        and not state.next_action_computed
    ):
        yield Transition(
            "startup_receipt_replay_is_noop",
            _step(state, startup_receipt_replay_is_noop=True),
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
            "manual_resume_opens_rehydrate_pending_action_after_role_output",
            _step(
                state,
                pending_action_kind="rehydrate_role_bindings",
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
        state.pending_action_kind == "rehydrate_role_bindings"
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

    if state.pending_action_kind == "rehydrate_role_bindings" and state.controller_receipt_status == "none":
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
        state.pending_action_kind == "rehydrate_role_bindings"
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
        state.pending_action_kind == "rehydrate_role_bindings"
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
