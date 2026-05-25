"""Hard-gate red-team coverage matrix for fake AI action packages.

This matrix is intentionally narrower than the broad synthetic-agent matrix.
It tracks the places where a plausible but invalid AI package could otherwise
mutate FlowPilot state or support an overclaimed completion/proof.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
INCOMPLETE_BACKGROUND_STATUSES = {"progress_only", "running", "missing", "stale"}

REQUIRED_ROW_FIELDS = (
    "gate_id",
    "entrypoint",
    "bad_package_class",
    "expected_outcome",
    "protected_state_invariant",
    "recovery_route",
    "evidence_id",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "live_completion_allowed",
)

REQUIRED_GATE_IDS = {
    "hard_gate.router_event.unauthorized_current_wait",
    "hard_gate.role_output.router_supplied_event_mismatch",
    "hard_gate.packet.wrong_active_holder_identity",
    "hard_gate.background.progress_only_not_proof",
    "hard_gate.run_authority.peer_stop_isolated",
    "hard_gate.terminal.dirty_ledger_closure_overclaim",
}


RED_TEAM_ROWS: tuple[dict[str, Any], ...] = (
    {
        "gate_id": "hard_gate.router_event.unauthorized_current_wait",
        "entrypoint": "flowpilot_router.record_external_event",
        "bad_package_class": "event_envelope_not_allowed_by_current_wait",
        "expected_outcome": "RouterError_or_control_blocker_before_gate_flag",
        "protected_state_invariant": "pending_wait_event_flag_remains_false_and_run_not_closed",
        "recovery_route": "control_blocker_or_retry_current_wait",
        "evidence_id": "hard_gate.router_event.unauthorized_current_wait",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_unauthorized_event_envelope_preserves_pending_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "notes": "A valid-looking role output envelope cannot satisfy an event unless the Router is waiting for that event.",
    },
    {
        "gate_id": "hard_gate.role_output.router_supplied_event_mismatch",
        "entrypoint": "role_output_runtime.validate_direct_router_submission_authority",
        "bad_package_class": "router_supplied_event_not_in_current_wait",
        "expected_outcome": "RoleOutputRuntimeError_before_output_write",
        "protected_state_invariant": "no_role_output_body_or_ledger_written",
        "recovery_route": "reject_before_router_submission_then_retry_after_router_wait",
        "evidence_id": "hard_gate.role_output.router_supplied_event_mismatch",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_role_output_authority_mismatch_writes_no_output"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "notes": "Officer/PM outputs using Router-supplied events must be bound to the current pending wait.",
    },
    {
        "gate_id": "hard_gate.packet.wrong_active_holder_identity",
        "entrypoint": "packet_runtime.active_holder_submit_result",
        "bad_package_class": "wrong_active_holder_agent",
        "expected_outcome": "PacketRuntimeError_before_result_envelope",
        "protected_state_invariant": "packet_ledger_keeps_no_result_completion",
        "recovery_route": "same_holder_retry_or_packet_reissue",
        "evidence_id": "hard_gate.packet.wrong_active_holder_identity",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_packet_wrong_holder_identity_preserves_ledger"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "notes": "A different agent id cannot submit work under an active-holder lease.",
    },
    {
        "gate_id": "hard_gate.background.progress_only_not_proof",
        "entrypoint": "scripts.test_tier.background.classify_background_artifact",
        "bad_package_class": "background_progress_without_exit_artifact",
        "expected_outcome": "status_progress_only_and_not_ok",
        "protected_state_invariant": "no_pass_claim_without_exit_code_artifact",
        "recovery_route": "wait_for_final_exit_or_rerun_background_check",
        "evidence_id": "hard_gate.background.progress_only_not_proof",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_background_progress_only_proof_is_not_pass"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "background_final_artifact_required": True,
        "notes": "Progress/liveness logs are not completion evidence.",
    },
    {
        "gate_id": "hard_gate.run_authority.peer_stop_isolated",
        "entrypoint": "flowpilot_router.stop_router_daemon",
        "bad_package_class": "stale_or_peer_run_control_request",
        "expected_outcome": "target_run_only_no_current_focus_mutation",
        "protected_state_invariant": "current_run_focus_and_peer_lock_remain_active",
        "recovery_route": "ignore_peer_mutation_and_keep_current_run_authority",
        "evidence_id": "hard_gate.run_authority.peer_stop_isolated",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_peer_run_stop_preserves_current_run_authority"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "notes": "A stop command for one run must not steal or close the current run authority.",
    },
    {
        "gate_id": "hard_gate.terminal.dirty_ledger_closure_overclaim",
        "entrypoint": "flowpilot_router.record_external_event",
        "bad_package_class": "terminal_closure_with_dirty_pm_ledger",
        "expected_outcome": "RouterError_before_closed_state",
        "protected_state_invariant": "run_status_not_closed_and_terminal_flag_not_approved",
        "recovery_route": "pm_repairs_dirty_ledger_then_terminal_gate_retries",
        "evidence_id": "hard_gate.terminal.dirty_ledger_closure_overclaim",
        "evidence_test": (
            "FlowPilotHardGateRedTeamReplayTests."
            "test_hard_gate_terminal_closure_overclaim_preserves_nonclosed_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "notes": "A final closure package cannot close the run while repair ledgers remain dirty.",
    },
)


def build_red_team_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in RED_TEAM_ROWS]


def validate_red_team_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_gate_ids = {str(row.get("gate_id") or "") for row in rows}
    for gate_id in sorted(REQUIRED_GATE_IDS - present_gate_ids):
        findings.append(
            {
                "code": "missing_required_gate",
                "gate_id": gate_id,
                "message": "required hard-gate red-team row is missing",
            }
        )

    for row in rows:
        gate_id = str(row.get("gate_id") or "")
        missing_fields = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None)
        ]
        if missing_fields:
            findings.append(
                {
                    "code": "missing_required_field",
                    "gate_id": gate_id,
                    "missing_fields": missing_fields,
                    "message": "hard-gate row is missing required field(s)",
                }
            )

        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            if evidence_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_evidence_id",
                        "gate_id": gate_id,
                        "evidence_id": evidence_id,
                        "message": "hard-gate evidence ids must be unique",
                    }
                )
            seen_ids.add(evidence_id)

        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "gate_id": gate_id,
                    "evidence_status": str(row.get("evidence_status") or ""),
                    "message": "hard-gate primary evidence must be current and passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "gate_id": gate_id,
                    "message": "hard-gate evidence must be current",
                }
            )
        if row.get("live_completion_allowed") is not False:
            findings.append(
                {
                    "code": "red_team_overclaims_live_completion",
                    "gate_id": gate_id,
                    "message": "red-team packages cannot prove live AI completion",
                }
            )
        if str(row.get("protected_state_invariant") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_protected_state_invariant",
                    "gate_id": gate_id,
                    "message": "row must name the protected state invariant",
                }
            )
        if str(row.get("recovery_route") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_recovery_route",
                    "gate_id": gate_id,
                    "message": "row must name the recovery route after rejection",
                }
            )
        if str(row.get("evidence_test") or "").strip() == "":
            findings.append(
                {
                    "code": "missing_evidence_test",
                    "gate_id": gate_id,
                    "message": "row must bind to a runnable test",
                }
            )
        if (
            row.get("background_final_artifact_required") is True
            and str(row.get("evidence_status") or "") in INCOMPLETE_BACKGROUND_STATUSES
        ):
            findings.append(
                {
                    "code": "progress_only_proof_claimed_pass",
                    "gate_id": gate_id,
                    "evidence_status": str(row.get("evidence_status") or ""),
                    "message": "background evidence requires a final exit artifact",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "gate_id": "hard_gate.known_bad",
        "entrypoint": "known.entrypoint",
        "bad_package_class": "known_bad",
        "expected_outcome": "rejected",
        "protected_state_invariant": "protected_state_remains_unchanged",
        "recovery_route": "retry_after_repair",
        "evidence_id": "known.bad",
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
    }
    return [
        {
            "name": "missing_evidence_test",
            "rows": [{**base, "evidence_test": ""}],
            "expected_codes": ["missing_required_field", "missing_evidence_test", "missing_required_gate"],
        },
        {
            "name": "missing_protected_state_invariant",
            "rows": [{**base, "protected_state_invariant": ""}],
            "expected_codes": [
                "missing_required_field",
                "missing_protected_state_invariant",
                "missing_required_gate",
            ],
        },
        {
            "name": "missing_recovery_route",
            "rows": [{**base, "recovery_route": ""}],
            "expected_codes": ["missing_required_field", "missing_recovery_route", "missing_required_gate"],
        },
        {
            "name": "progress_only_proof_claimed_pass",
            "rows": [
                {
                    **base,
                    "gate_id": "hard_gate.background.progress_only_not_proof",
                    "background_final_artifact_required": True,
                    "evidence_status": "progress_only",
                }
            ],
            "expected_codes": ["invalid_evidence_status", "progress_only_proof_claimed_pass", "missing_required_gate"],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_red_team_rows()
    findings = validate_red_team_rows(rows)
    rows_by_entrypoint = Counter(str(row["entrypoint"]) for row in rows)
    rows_by_bad_package_class = Counter(str(row["bad_package_class"]) for row in rows)
    return {
        "ok": not findings,
        "result_type": "flowpilot_hard_gate_red_team_matrix",
        "coverage_boundary": (
            "Rows prove rejection and state-preservation behavior for fake AI packages. "
            "They do not prove live AI semantic quality or live project completion."
        ),
        "required_gate_count": len(REQUIRED_GATE_IDS),
        "row_count": len(rows),
        "rows_by_entrypoint": dict(sorted(rows_by_entrypoint.items())),
        "rows_by_bad_package_class": dict(sorted(rows_by_bad_package_class.items())),
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
