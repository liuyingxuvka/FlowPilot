"""End-to-end synthetic AI chaos replay coverage matrix.

This matrix sits above the single-boundary hard-gate matrix. It tracks full
fake-AI stories that cross Router/daemon, packet, PM repair, background proof,
parallel-run isolation, and terminal closure phases.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLES = {"primary_full_flow"}
SUPPORTING_ROLES = {"leaf_support", "parent_support"}

REQUIRED_ROW_FIELDS = (
    "flow_id",
    "phase_sequence",
    "injected_error_sequence",
    "expected_outcome",
    "protected_state_invariant",
    "recovery_route",
    "final_state",
    "evidence_id",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "live_ai_semantic_quality_proven",
)

REQUIRED_FLOW_IDS = {
    "e2e.happy.startup_to_terminal",
    "e2e.worker.bad_then_repaired_package",
    "e2e.pm_repair.bad_then_corrected",
    "e2e.background.progress_only_then_final_proof",
    "e2e.parallel.peer_run_isolation",
    "e2e.terminal.overclaim_then_clean_closure",
}


CHAOS_ROWS: tuple[dict[str, Any], ...] = (
    {
        "flow_id": "e2e.happy.startup_to_terminal",
        "phase_sequence": [
            "startup",
            "daemon_takeover",
            "pm_dispatch",
            "worker_result",
            "pm_review",
            "terminal_ledger",
            "terminal_closure",
            "daemon_terminal_lifecycle",
        ],
        "injected_error_sequence": ["none"],
        "expected_outcome": "clean_terminal_closure",
        "protected_state_invariant": "daemon_lock_and_run_lifecycle_end_terminal_without_dirty_ledgers",
        "recovery_route": "not_required",
        "final_state": "closed_with_terminal_lifecycle_record",
        "evidence_id": "e2e.happy.startup_to_terminal",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_golden_fake_ai_run_reaches_clean_terminal_lifecycle"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "router-startup child tier",
            "router-terminal child tier",
        ],
        "live_ai_semantic_quality_proven": False,
    },
    {
        "flow_id": "e2e.worker.bad_then_repaired_package",
        "phase_sequence": [
            "startup",
            "daemon_takeover",
            "pm_dispatch",
            "worker_bad_package",
            "worker_repair",
            "pm_review",
            "terminal_closure",
        ],
        "injected_error_sequence": ["wrong_active_holder_agent", "correct_active_holder_repair"],
        "expected_outcome": "first_result_rejected_then_repaired_result_accepted",
        "protected_state_invariant": "packet_ledger_has_no_completion_before_repaired_result",
        "recovery_route": "same_holder_retry_then_pm_disposition",
        "final_state": "node_completed_and_run_closed",
        "evidence_id": "e2e.worker.bad_then_repaired_package",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_worker_bad_package_then_repair_continues_to_terminal"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "hard_gate.packet.wrong_active_holder_identity",
            "router-packets child tier",
        ],
        "live_ai_semantic_quality_proven": False,
    },
    {
        "flow_id": "e2e.pm_repair.bad_then_corrected",
        "phase_sequence": [
            "startup",
            "control_blocker",
            "pm_bad_repair",
            "pm_corrected_repair",
            "legal_wait_restored",
        ],
        "injected_error_sequence": ["invalid_pm_repair_target", "registered_pm_repair_target"],
        "expected_outcome": "bad_repair_rejected_then_corrected_repair_opens_legal_wait",
        "protected_state_invariant": "active_blocker_remains_until_correct_pm_repair_decision",
        "recovery_route": "pm_records_control_blocker_repair_decision",
        "final_state": "awaiting_registered_return_gate_with_blocker_record",
        "evidence_id": "e2e.pm_repair.bad_then_corrected",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_pm_repair_bad_package_then_corrected_repair_restores_legal_wait"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "synthetic PM control-blocker repair tests",
        ],
        "live_ai_semantic_quality_proven": False,
    },
    {
        "flow_id": "e2e.background.progress_only_then_final_proof",
        "phase_sequence": ["background_regression", "proof_gate", "final_proof"],
        "injected_error_sequence": ["progress_only_background_artifact", "final_exit_zero_artifact"],
        "expected_outcome": "progress_only_rejected_then_final_artifact_passed",
        "protected_state_invariant": "no_completion_claim_without_exit_meta_and_combined_artifacts",
        "recovery_route": "wait_for_final_exit_or_rerun_background_check",
        "final_state": "background_proof_passed",
        "evidence_id": "e2e.background.progress_only_then_final_proof",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_background_progress_only_then_final_artifacts_controls_proof_gate"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "hard_gate.background.progress_only_not_proof",
            "test tier background artifact contract",
        ],
        "live_ai_semantic_quality_proven": False,
    },
    {
        "flow_id": "e2e.parallel.peer_run_isolation",
        "phase_sequence": ["parallel_run_setup", "peer_stop", "current_run_continues"],
        "injected_error_sequence": ["peer_run_stop_request", "current_run_authority_check"],
        "expected_outcome": "peer_stop_releases_only_target_run",
        "protected_state_invariant": "current_run_focus_and_daemon_lock_remain_active",
        "recovery_route": "ignore_peer_mutation_and_continue_current_run",
        "final_state": "current_run_still_active_peer_released",
        "evidence_id": "e2e.parallel.peer_run_isolation",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_parallel_run_peer_stop_does_not_mutate_current_run"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "hard_gate.run_authority.peer_stop_isolated",
            "router-startup daemon stop tests",
        ],
        "live_ai_semantic_quality_proven": False,
    },
    {
        "flow_id": "e2e.terminal.overclaim_then_clean_closure",
        "phase_sequence": [
            "startup",
            "worker_result",
            "terminal_ledger",
            "dirty_terminal_overclaim",
            "clean_terminal_retry",
            "daemon_terminal_lifecycle",
        ],
        "injected_error_sequence": ["dirty_pm_suggestion_ledger", "clean_pm_suggestion_ledger"],
        "expected_outcome": "dirty_closure_rejected_then_clean_closure_accepted",
        "protected_state_invariant": "run_status_not_closed_until_all_terminal_ledgers_clean",
        "recovery_route": "pm_cleans_dirty_ledger_then_retries_terminal_closure",
        "final_state": "closed_with_terminal_lifecycle_record",
        "evidence_id": "e2e.terminal.overclaim_then_clean_closure",
        "evidence_test": (
            "FlowPilotEndToEndSyntheticChaosReplayTests."
            "test_e2e_terminal_overclaim_then_clean_retry_closes_run"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "supporting_evidence": [
            "hard_gate.terminal.dirty_ledger_closure_overclaim",
            "router-terminal child tier",
        ],
        "live_ai_semantic_quality_proven": False,
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in CHAOS_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_flow_ids = {str(row.get("flow_id") or "") for row in rows}
    for flow_id in sorted(REQUIRED_FLOW_IDS - present_flow_ids):
        findings.append(
            {
                "code": "missing_required_flow",
                "flow_id": flow_id,
                "message": "required end-to-end chaos flow row is missing",
            }
        )

    for row in rows:
        flow_id = str(row.get("flow_id") or "")
        missing_fields = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None, [])
        ]
        if missing_fields:
            findings.append(
                {
                    "code": "missing_required_field",
                    "flow_id": flow_id,
                    "missing_fields": missing_fields,
                    "message": "end-to-end chaos row is missing required field(s)",
                }
            )

        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            if evidence_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_evidence_id",
                        "flow_id": flow_id,
                        "evidence_id": evidence_id,
                        "message": "end-to-end chaos evidence ids must be unique",
                    }
                )
            seen_ids.add(evidence_id)

        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "flow_id": flow_id,
                    "evidence_status": str(row.get("evidence_status") or ""),
                    "message": "primary full-flow evidence must be current and passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "flow_id": flow_id,
                    "message": "full-flow evidence must be current",
                }
            )
        if str(row.get("evidence_role") or "") not in PRIMARY_ROLES | SUPPORTING_ROLES:
            findings.append(
                {
                    "code": "invalid_evidence_role",
                    "flow_id": flow_id,
                    "evidence_role": str(row.get("evidence_role") or ""),
                    "message": "evidence role must classify primary or supporting coverage",
                }
            )
        if str(row.get("protected_state_invariant") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_protected_state_invariant",
                    "flow_id": flow_id,
                    "message": "row must name the protected state invariant",
                }
            )
        if str(row.get("recovery_route") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_recovery_route",
                    "flow_id": flow_id,
                    "message": "row must name the recovery route",
                }
            )
        if str(row.get("final_state") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_final_state",
                    "flow_id": flow_id,
                    "message": "row must name the final state",
                }
            )
        if str(row.get("evidence_test") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_evidence_test",
                    "flow_id": flow_id,
                    "message": "row must bind to a runnable test",
                }
            )
        if (
            "progress_only" in [str(item) for item in row.get("injected_error_sequence", [])]
            and str(row.get("final_state") or "") == "closed"
        ):
            findings.append(
                {
                    "code": "progress_only_final_proof_overclaim",
                    "flow_id": flow_id,
                    "message": "progress-only evidence cannot be the final proof for closure",
                }
            )
        injected_errors = [str(item) for item in row.get("injected_error_sequence", [])]
        if (
            "no_producer_pm_role_reissue" in injected_errors
            and "corrected_registered_producer" not in injected_errors
            and "corrected_safe_operation_replay" not in injected_errors
        ):
            findings.append(
                {
                    "code": "no_producer_repair_without_corrected_recovery",
                    "flow_id": flow_id,
                    "message": "no-producer PM repair rehearsal rows must include a corrected registered producer or safe operation replay",
                }
            )
        if (
            "stale_worker_result_flags" in injected_errors
            and "current_producer_evidence" not in str(row.get("final_state") or "")
            and "current_operation_replay" not in str(row.get("final_state") or "")
        ):
            findings.append(
                {
                    "code": "stale_evidence_used_as_repair_proof",
                    "flow_id": flow_id,
                    "message": "stale worker result flags cannot count as fresh repair producer evidence",
                }
            )
        if row.get("live_ai_semantic_quality_proven") is not False:
            findings.append(
                {
                    "code": "semantic_quality_overclaim",
                    "flow_id": flow_id,
                    "message": "fake package replay cannot prove live AI semantic quality",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "flow_id": "known.bad",
        "phase_sequence": ["startup"],
        "injected_error_sequence": ["known_bad"],
        "expected_outcome": "rejected",
        "protected_state_invariant": "protected_state_remains_unchanged",
        "recovery_route": "retry_after_repair",
        "final_state": "blocked_until_repair",
        "evidence_id": "known.bad",
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_full_flow",
        "live_ai_semantic_quality_proven": False,
    }
    return [
        {
            "name": "missing_phase_sequence",
            "rows": [{**base, "phase_sequence": []}],
            "expected_codes": ["missing_required_field", "missing_required_flow"],
        },
        {
            "name": "missing_evidence_test",
            "rows": [{**base, "evidence_test": ""}],
            "expected_codes": ["missing_required_field", "missing_evidence_test", "missing_required_flow"],
        },
        {
            "name": "missing_protected_state_invariant",
            "rows": [{**base, "protected_state_invariant": ""}],
            "expected_codes": [
                "missing_required_field",
                "missing_protected_state_invariant",
                "missing_required_flow",
            ],
        },
        {
            "name": "missing_recovery_route",
            "rows": [{**base, "recovery_route": ""}],
            "expected_codes": ["missing_required_field", "missing_recovery_route", "missing_required_flow"],
        },
        {
            "name": "missing_final_state",
            "rows": [{**base, "final_state": ""}],
            "expected_codes": ["missing_required_field", "missing_final_state", "missing_required_flow"],
        },
        {
            "name": "progress_only_final_proof_overclaim",
            "rows": [
                {
                    **base,
                    "flow_id": "e2e.background.progress_only_then_final_proof",
                    "injected_error_sequence": ["progress_only"],
                    "final_state": "closed",
                }
            ],
            "expected_codes": ["progress_only_final_proof_overclaim", "missing_required_flow"],
        },
        {
            "name": "semantic_quality_overclaim",
            "rows": [{**base, "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["semantic_quality_overclaim", "missing_required_flow"],
        },
        {
            "name": "no_producer_repair_without_corrected_recovery",
            "rows": [
                {
                    **base,
                    "injected_error_sequence": ["no_producer_pm_role_reissue"],
                    "final_state": "awaiting_worker_result_without_new_packet",
                }
            ],
            "expected_codes": ["no_producer_repair_without_corrected_recovery", "missing_required_flow"],
        },
        {
            "name": "stale_worker_flags_used_as_repair_proof",
            "rows": [
                {
                    **base,
                    "injected_error_sequence": ["stale_worker_result_flags", "no_producer_pm_role_reissue"],
                    "final_state": "awaiting_worker_result_without_new_packet",
                }
            ],
            "expected_codes": [
                "no_producer_repair_without_corrected_recovery",
                "stale_evidence_used_as_repair_proof",
                "missing_required_flow",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    findings = validate_rows(rows)
    rows_by_phase = Counter(
        phase
        for row in rows
        for phase in row.get("phase_sequence", [])
    )
    rows_by_final_state = Counter(str(row["final_state"]) for row in rows)
    return {
        "ok": not findings,
        "result_type": "flowpilot_e2e_synthetic_chaos_matrix",
        "coverage_boundary": (
            "Rows prove fake-package protocol, state, recovery, isolation, proof, and terminal gates across "
            "bounded full-flow replays. They do not prove live AI semantic quality or all possible project work."
        ),
        "required_flow_count": len(REQUIRED_FLOW_IDS),
        "row_count": len(rows),
        "rows_by_phase": dict(sorted(rows_by_phase.items())),
        "rows_by_final_state": dict(sorted(rows_by_final_state.items())),
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
