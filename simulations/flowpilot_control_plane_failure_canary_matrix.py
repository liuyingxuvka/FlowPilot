"""FlowPilot control-plane failure canary coverage matrix.

This matrix tracks bounded fake-control failures that are easy to miss when
only the ordinary fake-AI package path is replayed: locks, half-written
runtime files, daemon liveness, duplicate resume wakes, peer-run authority,
terminal fences, and background proof artifacts.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLES = {"primary_canary"}
SUPPORTING_ROLES = {"supporting_runtime", "supporting_matrix"}

REQUIRED_ROW_FIELDS = (
    "canary_id",
    "surface",
    "failure_injection",
    "expected_outcome",
    "protected_state_invariant",
    "recovery_route",
    "standard_final_state",
    "evidence_id",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "destructive_live_state_mutation",
    "unmodeled_failure_boundary",
)

REQUIRED_CANARY_IDS = {
    "control.lock.fresh_write_waits_then_recovers",
    "control.persistence.corrupt_scheduler_blocks_daemon",
    "control.daemon.dead_owner_resume_restart",
    "control.heartbeat.duplicate_resume_idempotent",
    "control.peer.peer_stop_isolated",
    "control.background.progress_only_not_proof",
    "control.terminal.stop_fence_survives_scheduler_lock",
}


CANARY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "canary_id": "control.lock.fresh_write_waits_then_recovers",
        "surface": "runtime_json_lock",
        "failure_injection": "fresh_controller_or_scheduler_write_lock_then_writer_finishes",
        "expected_outcome": "router_waits_on_fresh_lock_then_continues_after_valid_json_is_restored",
        "protected_state_invariant": "fresh_runtime_lock_is_not_stolen_and_settlement_is_recorded",
        "recovery_route": "runtime_write_settlement_wait_then_retry",
        "standard_final_state": "valid_runtime_ledger_and_no_stray_write_lock",
        "evidence_id": "control.lock.fresh_write_waits_then_recovers",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_fresh_scheduler_write_lock_waits_then_recovers"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_model_kernel_level_file_handle_loss_after_successful_json_replace",
    },
    {
        "canary_id": "control.persistence.corrupt_scheduler_blocks_daemon",
        "surface": "runtime_persistence",
        "failure_injection": "scheduler_ledger_contains_valid_prefix_plus_trailing_broken_bytes",
        "expected_outcome": "daemon_records_error_status_and_stops_claiming_live_progress",
        "protected_state_invariant": "corrupt_runtime_ledger_never_counts_as_daemon_progress",
        "recovery_route": "daemon_error_status_then_manual_or_replay_repair",
        "standard_final_state": "daemon_error_status_with_daemon_live_false",
        "evidence_id": "control.persistence.corrupt_scheduler_blocks_daemon",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_corrupt_scheduler_ledger_marks_daemon_error_not_live"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_repair_arbitrary_user_edited_json_without_a_recovery_event",
    },
    {
        "canary_id": "control.daemon.dead_owner_resume_restart",
        "surface": "daemon_liveness",
        "failure_injection": "router_daemon_lock_points_to_missing_pid_and_stale_last_tick",
        "expected_outcome": "resume_checks_liveness_and_restarts_daemon_before_normal_work",
        "protected_state_invariant": "dead_daemon_lock_cannot_be_treated_as_current_execution_authority",
        "recovery_route": "heartbeat_resume_liveness_check_restart_router_daemon",
        "standard_final_state": "resume_reentry_written_with_router_daemon_restarted_if_dead",
        "evidence_id": "control.daemon.dead_owner_resume_restart",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_dead_daemon_resume_restart_path_before_normal_work"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_prove_recovery_from_os_process_table_corruption",
    },
    {
        "canary_id": "control.heartbeat.duplicate_resume_idempotent",
        "surface": "heartbeat_resume",
        "failure_injection": "same_resume_wake_is_recorded_twice_before_resume_state_loads",
        "expected_outcome": "router_keeps_one_resume_boundary_and_replays_current_state_once",
        "protected_state_invariant": "duplicate_wake_does_not_skip_resume_liveness_or_spawn_parallel_resume_work",
        "recovery_route": "idempotent_resume_reentry_with_current_run_authority_check",
        "standard_final_state": "resume_state_loaded_with_single_reentry_evidence_and_role_rehydration_next",
        "evidence_id": "control.heartbeat.duplicate_resume_idempotent",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_duplicate_heartbeat_resume_is_idempotent"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_verify_external_scheduler_exactly_once_delivery",
    },
    {
        "canary_id": "control.peer.peer_stop_isolated",
        "surface": "run_authority",
        "failure_injection": "stop_request_targets_peer_run_while_current_run_has_active_daemon_lock",
        "expected_outcome": "peer_lock_released_without_mutating_current_focus_or_current_daemon",
        "protected_state_invariant": "current_run_pointer_and_current_daemon_lock_remain_authoritative",
        "recovery_route": "scoped_peer_run_stop_only",
        "standard_final_state": "peer_released_current_run_still_active",
        "evidence_id": "control.peer.peer_stop_isolated",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_peer_run_stop_does_not_mutate_current_run"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_model_two_real_human_operators_editing_current_pointer_concurrently",
    },
    {
        "canary_id": "control.background.progress_only_not_proof",
        "surface": "background_evidence",
        "failure_injection": "combined_log_contains_progress_but_exit_and_meta_artifacts_are_missing",
        "expected_outcome": "progress_only_artifact_is_rejected_until_final_exit_and_meta_exist",
        "protected_state_invariant": "background_progress_lines_do_not_satisfy_completion_or_release_proof",
        "recovery_route": "wait_for_final_artifacts_or_rerun_background_check",
        "standard_final_state": "passed_background_artifact_requires_exit_zero_and_passed_meta",
        "evidence_id": "control.background.progress_only_not_proof",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_progress_only_background_artifact_is_not_standard_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_prove_the_semantic_quality_of_the_background_command_itself",
    },
    {
        "canary_id": "control.terminal.stop_fence_survives_scheduler_lock",
        "surface": "terminal_fence",
        "failure_injection": "user_stop_arrives_while_scheduler_ledger_has_fresh_write_lock",
        "expected_outcome": "terminal_fence_and_daemon_stop_are_written_before_best_effort_scheduler_cleanup",
        "protected_state_invariant": "terminal_stop_blocks_normal_controller_work_even_if_scheduler_cleanup_waits",
        "recovery_route": "terminal_fence_first_then_best_effort_cleanup_diagnostic",
        "standard_final_state": "stopped_by_user_with_terminal_stopped_daemon_and_best_effort_failure_recorded",
        "evidence_id": "control.terminal.stop_fence_survives_scheduler_lock",
        "evidence_test": (
            "FlowPilotControlPlaneFailureCanaryReplayTests."
            "test_canary_stop_fence_survives_scheduler_lock"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "does_not_model_power_loss_between_terminal_fence_write_and_filesystem_flush",
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in CANARY_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_ids = {str(row.get("canary_id") or "") for row in rows}
    for canary_id in sorted(REQUIRED_CANARY_IDS - present_ids):
        findings.append(
            {
                "code": "missing_required_canary",
                "canary_id": canary_id,
                "message": "required control-plane canary row is missing",
            }
        )

    for row in rows:
        canary_id = str(row.get("canary_id") or "")
        missing_fields = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None, [])
        ]
        if missing_fields:
            findings.append(
                {
                    "code": "missing_required_field",
                    "canary_id": canary_id,
                    "missing_fields": missing_fields,
                    "message": "control-plane canary row is missing required field(s)",
                }
            )

        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            if evidence_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_evidence_id",
                        "canary_id": canary_id,
                        "evidence_id": evidence_id,
                        "message": "control-plane canary evidence ids must be unique",
                    }
                )
            seen_ids.add(evidence_id)

        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "canary_id": canary_id,
                    "evidence_status": str(row.get("evidence_status") or ""),
                    "message": "primary control-plane canary evidence must be passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "canary_id": canary_id,
                    "message": "control-plane canary evidence must be current",
                }
            )
        if str(row.get("evidence_role") or "") not in PRIMARY_ROLES | SUPPORTING_ROLES:
            findings.append(
                {
                    "code": "invalid_evidence_role",
                    "canary_id": canary_id,
                    "evidence_role": str(row.get("evidence_role") or ""),
                    "message": "evidence role must classify primary or supporting canary coverage",
                }
            )
        if str(row.get("protected_state_invariant") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_protected_state_invariant",
                    "canary_id": canary_id,
                    "message": "row must name the protected state invariant",
                }
            )
        if str(row.get("recovery_route") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_recovery_route",
                    "canary_id": canary_id,
                    "message": "row must name the recovery route",
                }
            )
        if str(row.get("standard_final_state") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_standard_final_state",
                    "canary_id": canary_id,
                    "message": "row must name the standard final state",
                }
            )
        if str(row.get("evidence_test") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_evidence_test",
                    "canary_id": canary_id,
                    "message": "row must bind to a runnable test",
                }
            )
        if row.get("destructive_live_state_mutation") is not False:
            findings.append(
                {
                    "code": "live_state_mutation_overclaim",
                    "canary_id": canary_id,
                    "message": "canary rows must stay in isolated temp runs and cannot mutate live user state",
                }
            )
        if (
            "progress_only" in str(row.get("failure_injection") or "")
            and "passed_background_artifact" not in str(row.get("standard_final_state") or "")
        ):
            findings.append(
                {
                    "code": "progress_only_final_proof_overclaim",
                    "canary_id": canary_id,
                    "message": "progress-only evidence cannot be reported as the final background proof",
                }
            )
        if str(row.get("unmodeled_failure_boundary") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_unmodeled_failure_boundary",
                    "canary_id": canary_id,
                    "message": "row must state what the canary does not prove",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "canary_id": "known.bad",
        "surface": "runtime_json_lock",
        "failure_injection": "known_bad",
        "expected_outcome": "rejected",
        "protected_state_invariant": "state_is_not_mutated_by_bad_control_input",
        "recovery_route": "retry_after_repair",
        "standard_final_state": "blocked_until_repair",
        "evidence_id": "known.bad",
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_canary",
        "destructive_live_state_mutation": False,
        "unmodeled_failure_boundary": "known_bad_fixture_only",
    }
    return [
        {
            "name": "missing_protected_state_invariant",
            "rows": [{**base, "protected_state_invariant": ""}],
            "expected_codes": [
                "missing_required_field",
                "missing_protected_state_invariant",
                "missing_required_canary",
            ],
        },
        {
            "name": "missing_recovery_route",
            "rows": [{**base, "recovery_route": ""}],
            "expected_codes": ["missing_required_field", "missing_recovery_route", "missing_required_canary"],
        },
        {
            "name": "missing_standard_final_state",
            "rows": [{**base, "standard_final_state": ""}],
            "expected_codes": ["missing_required_field", "missing_standard_final_state", "missing_required_canary"],
        },
        {
            "name": "missing_evidence_test",
            "rows": [{**base, "evidence_test": ""}],
            "expected_codes": ["missing_required_field", "missing_evidence_test", "missing_required_canary"],
        },
        {
            "name": "progress_only_final_proof_overclaim",
            "rows": [
                {
                    **base,
                    "canary_id": "control.background.progress_only_not_proof",
                    "failure_injection": "progress_only_background_artifact",
                    "standard_final_state": "closed",
                }
            ],
            "expected_codes": ["progress_only_final_proof_overclaim", "missing_required_canary"],
        },
        {
            "name": "live_state_mutation_overclaim",
            "rows": [{**base, "destructive_live_state_mutation": True}],
            "expected_codes": ["live_state_mutation_overclaim", "missing_required_canary"],
        },
        {
            "name": "missing_unmodeled_failure_boundary",
            "rows": [{**base, "unmodeled_failure_boundary": ""}],
            "expected_codes": [
                "missing_required_field",
                "missing_unmodeled_failure_boundary",
                "missing_required_canary",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    findings = validate_rows(rows)
    rows_by_surface = Counter(str(row["surface"]) for row in rows)
    return {
        "ok": not findings,
        "result_type": "flowpilot_control_plane_failure_canary_matrix",
        "coverage_boundary": (
            "Rows prove bounded control-plane recovery through isolated fake-control failures: locks, "
            "runtime persistence, daemon liveness, duplicate resume, peer-run authority, terminal fences, "
            "and background artifacts. They do not prove every OS, hardware, antivirus, or live AI failure."
        ),
        "required_canary_count": len(REQUIRED_CANARY_IDS),
        "row_count": len(rows),
        "rows_by_surface": dict(sorted(rows_by_surface.items())),
        "findings": findings,
        "rows": rows,
        "known_bad_cases": known_bad_cases(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    report = build_report()
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
