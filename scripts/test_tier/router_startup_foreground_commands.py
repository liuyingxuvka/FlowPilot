"""Router startup and foreground FlowPilot test-tier commands."""

from __future__ import annotations

from .command_builders import _unittest, _unittest_k

ROUTER_STARTUP_COMMANDS = (
    _unittest(
        "router_startup_runtime_contracts",
        "tests.test_flowpilot_router_startup_runtime",
        description="Startup runtime contract and encoding slice.",
    ),
    _unittest(
        "router_bootstrap_cli",
        "tests.router_runtime.bootstrap_cli",
        description="Startup CLI and fresh-run command slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_core",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "run_until",
            "manual_startup",
            "formal_startup",
            "deterministic",
            "startup_daemon",
            "startup_seed",
            "flowguard_snapshot",
            "router_daemon_queues_visible_startup_rows_after_internal_audit",
            "load_controller_core",
            "partial_old_startup_role",
            "old_startup_role",
            "startup_does_not_schedule_background_role_prewarm",
        ),
        description="Startup bootstrap core, daemon, and receipt-owner slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_reconciliation",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_reconciliation",
            "startup_missing_router",
            "startup_obligations",
            "startup_bootloader",
            "startup_async",
        ),
        description="Startup reconciliation, bootloader, and async receipt slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_intake",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_intake",
            "startup_sequence",
            "startup_waits",
            "startup_banner",
            "user_intake_from_startup_ui",
            "new_invocation",
            "unsupported_scheduled_continuation",
        ),
        description="Startup intake, user answer, and banner slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_runtime_release",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_rejects_legacy_reviewer_event_before_pm_work",
            "startup_pre_review",
            "startup_current_path_releases_user_intake_without_startup_role_gate",
            "startup_review_join",
            "startup_old_role_gate_events",
        ),
        description="Startup runtime release, legacy gate rejection, and repair-decision slice.",
    ),
    _unittest_k(
        "router_startup_bootstrap_fact_manual_resume",
        "tests.router_runtime.startup_bootstrap",
        patterns=(
            "startup_fact",
            "reconciled_startup_display",
            "cockpit_startup_answer",
        ),
        description="Startup fact-report, manual-resume, and display rejection slice.",
    ),
    _unittest(
        "router_startup_daemon",
        "tests.router_runtime.startup_daemon",
        description="Persistent startup daemon slice.",
    ),
)

ROUTER_FOREGROUND_COMMANDS = (
    _unittest(
        "router_foreground",
        "tests.router_runtime.foreground",
        description="Foreground progress and display-sync slice.",
    ),
    _unittest(
        "router_controller",
        "tests.router_runtime.controller",
        description="Controller status and passive wait slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_current_node_review",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "current_node_completion_waits_for_review_created_local_obligations",
            "current_node_parallel_batch_waits_for_all_results_before_review",
            "current_node_pre_review_reconciliation_blocks_reviewer_card",
            "current_node_reviewer_pass_event_waits_for_local_reconciliation",
            "future_node_pending_return_does_not_block_current_node_review",
        ),
        description="Dispatch-gate current-node review slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_recipient_policy",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "dispatch_recipient_gate_allows_pm_after_user_intake_first_output",
            "dispatch_recipient_gate_allows_same_role_system_card_bundle",
            "dispatch_recipient_gate_allows_system_card_for_active_holder",
            "dispatch_recipient_gate_blocks_busy_packet_holder",
            "dispatch_recipient_gate_blocks_followup_when_role_wait_is_active",
            "dispatch_recipient_gate_blocks_independent_pm_dispatch_while_user_intake_output_pending",
            "dispatch_recipient_gate_blocks_new_output_card_when_pm_output_pending",
            "dispatch_recipient_gate_frees_worker_after_result_but_blocks_pm_disposition",
            "dispatch_recipient_gate_allows_role_work_replacement_for_unrelayed_old_request",
            "dispatch_recipient_gate_still_blocks_relayed_role_work_target",
        ),
        description="Dispatch-gate recipient policy slice.",
    ),
    _unittest_k(
        "router_dispatch_gate_user_pm_control",
        "tests.router_runtime.dispatch_gate",
        patterns=(
            "no_legal_next_action_materializes_pm_decision_control_blocker",
            "router_hard_rejection_returns_control_plane_reissue_action",
            "user_intake_mail_declares_first_pm_output_obligation",
        ),
        description="Dispatch-gate PM/user-control slice.",
    ),
    _unittest_k(
        "router_foreground_controller_core",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "controller_action_summary",
            "controller_next_action",
            "controller_route_memory",
            "passive_wait_projection",
            "router_daemon_tick",
            "foreground_next_waits_on_fresh_controller_action_write_lock",
            "foreground_next_waits_on_stale_lock",
        ),
        description="Foreground controller core scheduling and lock slice.",
    ),
    _unittest_k(
        "router_foreground_controller_standby",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "foreground_controller_standby_default_waits_past_timeout_until_action",
            "foreground_controller_standby_does_not_compute_router_next",
            "foreground_controller_standby_keeps_alive_when_daemon_has_no_ready_action",
            "foreground_controller_standby_materializes_report_progress_reminder",
            "foreground_controller_standby_requests_liveness_check_on_stale_or_missing_daemon",
            "foreground_controller_standby_returns_ack_reminder_and_blocker_due",
            "foreground_controller_standby_returns_no_output_reissue_required",
            "foreground_controller_standby_self_audits_controller_local_wait",
            "controller_patrol_timer_allows_terminal_return_only_when_stopped",
            "controller_patrol_timer_continues_for_daemon_patrol_inside_five_minute_window",
            "controller_patrol_timer_continue_patrol_restarts_and_waits",
            "controller_patrol_timer_requests_liveness_check_after_delayed_daemon_patrol",
            "nonterminal_user_status_return_is_not_controller_stop",
            "wait_reminder_receipt_rejects_legacy_liveness_probe_payload",
        ),
        description="Foreground standby and patrol timer slice.",
    ),
    _unittest_k(
        "router_foreground_controller_receipts",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "completed_pending_controller_action_receipt",
            "controller_action_ledger_handles_multiple_receipts",
            "controller_boundary_done_receipt_reclaims_router_postcondition",
            "controller_boundary_duplicate_old_receipt_does_not_block_while_second_repair_pending",
            "controller_patrol_timer_wakes_on_controller_action_ledger",
            "foreground_controller_standby_wakes_on_controller_action_ledger",
            "reconcile_replays_reconciled_wait_reminder_receipt_after_state_drift",
            "reconciled_controller_action_backfills_receipt_done_scheduler_row",
        ),
        description="Foreground Controller receipt and scheduler reconciliation slice.",
    ),
    _unittest_k(
        "router_foreground_controller_boundary",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "child_skill_gates_block_raw_inventory_and_controller_approval",
            "controller_action_reconciliation_ignores_transient_temp_files",
            "controller_boundary_confirmation_records_envelope_only_event",
            "controller_boundary_done_receipt_missing_deliverable_schedules_repair",
            "controller_boundary_handwritten_artifact_without_runtime_evidence_schedules_repair",
            "controller_boundary_projection_reclaims_stale_flags_without_pending_action",
            "controller_boundary_valid_artifact_reclaims_before_repair",
            "role_output",
            "display_plan",
        ),
        description="Foreground Controller boundary, display, and card-delivery slice.",
    ),
    _unittest_k(
        "router_foreground_controller_repair",
        "tests.router_runtime.foreground_controller",
        patterns=(
            "controller_boundary_repair_action_resolves_original",
            "controller_boundary_repair_budget_escalates_after_two_failures",
            "controller_repair_work_packet_queues_bounded_controller_action",
        ),
        description="Foreground Controller repair and confirmation slice.",
    ),
)

