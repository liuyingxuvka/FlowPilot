"""Real Router dry-run rehearsal coverage matrix.

This matrix is stricter than the synthetic chaos matrix. It tracks prepared
fake AI work packages only when they pass through the real FlowPilot Router,
card, packet, role-output, proof, and lifecycle boundaries used by a live run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLES = {"primary_real_router_rehearsal"}
SUPPORTING_ROLES = {"supporting_control_plane", "supporting_e2e_chaos"}

REQUIRED_ROW_FIELDS = (
    "rehearsal_id",
    "phase_sequence",
    "fake_ai_artifacts",
    "router_entrypoints",
    "required_ack_or_receipt_gates",
    "allowed_event_boundary",
    "forbidden_shortcuts",
    "expected_standard_state",
    "evidence_id",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "confidence_boundary",
    "live_ai_semantic_quality_proven",
)

REQUIRED_REHEARSAL_IDS = {
    "real_router.full.startup_to_terminal_fake_ai_packages",
    "real_router.cli.public_boundary_smoke",
    "real_router.recovery.resume_and_background_proof_gate",
    "real_router.repair.producer_proof_recovery",
    "real_router.authority.rejects_shortcut_overclaims",
}

REQUIRED_ENTRYPOINTS = {
    "router_cli.start",
    "router_cli.next",
    "router_cli.apply",
    "router_cli.record_event",
    "router_cli.run_until_wait",
    "card_runtime.open_card",
    "card_runtime.submit_card_ack",
    "packet_runtime.create_packet",
    "packet_runtime.active_holder_ack",
    "packet_runtime.active_holder_submit_result",
    "role_output_runtime.envelope",
    "background_artifact_classifier",
    "router_lifecycle_terminal",
}


REHEARSAL_ROWS: tuple[dict[str, Any], ...] = (
    {
        "rehearsal_id": "real_router.full.startup_to_terminal_fake_ai_packages",
        "phase_sequence": [
            "startup",
            "material_scan",
            "product_architecture",
            "route_activation",
            "current_node_packet_dispatch",
            "active_holder_result",
            "pm_absorb_and_reviewer_review",
            "evidence_quality",
            "final_ledger",
            "terminal_replay",
            "pm_closure",
            "lifecycle_terminal",
        ],
        "fake_ai_artifacts": [
            "startup_fact_report",
            "pm_startup_activation_decision",
            "material_scan_packets",
            "product_behavior_model",
            "current_node_packet_body",
            "worker_result_envelope",
            "pm_package_result_disposition",
            "reviewer_result_report",
            "evidence_quality_review",
            "terminal_backward_replay_report",
            "pm_terminal_closure_decision",
        ],
        "router_entrypoints": [
            "router_runtime.next_action",
            "router_runtime.apply_action",
            "router_runtime.record_external_event",
            "card_runtime.open_card",
            "card_runtime.submit_card_ack",
            "packet_runtime.create_packet",
            "packet_runtime.active_holder_ack",
            "packet_runtime.active_holder_submit_result",
            "role_output_runtime.envelope",
            "router_lifecycle_terminal",
        ],
        "required_ack_or_receipt_gates": [
            "system_card_read_receipts",
            "system_card_ack_return_events",
            "packet_active_holder_ack",
            "packet_body_read_receipt",
            "reviewer_runtime_result_body_hash_match",
            "role_output_envelope_hashes",
        ],
        "allowed_event_boundary": "only Router-declared external events for the current wait may advance flags",
        "forbidden_shortcuts": [
            "direct_state_mutation",
            "direct_run_state_mutation",
            "unsupported_historical_record_event_card_ack",
            "invented_external_event",
            "controller_reads_packet_body",
            "terminal_closure_without_lifecycle_record",
        ],
        "expected_standard_state": "closed_run_with_terminal_lifecycle_record_and_no_active_control_blocker",
        "evidence_id": "real_router.full.startup_to_terminal_fake_ai_packages",
        "evidence_test": (
            "FlowPilotRealRouterDryRunRehearsalTests."
            "test_real_router_full_fake_ai_package_rehearsal_reaches_terminal_standard_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "supporting_evidence": [
            "e2e.happy.startup_to_terminal",
            "router-packets child tier",
            "router-terminal child tier",
        ],
        "confidence_boundary": (
            "proves prepared fake AI packages can exercise the real control plane to terminal state"
        ),
        "live_ai_semantic_quality_proven": False,
    },
    {
        "rehearsal_id": "real_router.cli.public_boundary_smoke",
        "phase_sequence": [
            "cli_start",
            "cli_state",
            "cli_next",
            "cli_apply",
            "cli_role_event",
            "cli_run_until_wait",
        ],
        "fake_ai_artifacts": [
            "reviewer_startup_fact_report_envelope",
            "pm_startup_activation_decision_envelope",
        ],
        "router_entrypoints": [
            "router_cli.start",
            "router_cli.state",
            "router_cli.next",
            "router_cli.apply",
            "router_cli.record_event",
            "router_cli.run_until_wait",
            "card_runtime.open_card",
            "card_runtime.submit_card_ack",
        ],
        "required_ack_or_receipt_gates": [
            "startup_fact_card_ack",
            "role_output_envelope_hashes",
            "router_cli_json_results",
        ],
        "allowed_event_boundary": "CLI record-event must submit Router-recognized events with controller-visible envelopes",
        "forbidden_shortcuts": [
            "direct_state_mutation",
            "manual_pending_action_clear",
            "manual_flag_set",
            "non_json_cli_result",
            "invented_external_event",
        ],
        "expected_standard_state": "legal_wait_after_cli_recorded_startup_activation_event",
        "evidence_id": "real_router.cli.public_boundary_smoke",
        "evidence_test": (
            "FlowPilotRealRouterDryRunRehearsalTests."
            "test_router_cli_boundary_runs_fake_role_output_through_public_commands"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "supporting_evidence": ["router bootstrap CLI tests"],
        "confidence_boundary": "proves public Router command path can participate in prepared fake output rehearsal",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "rehearsal_id": "real_router.recovery.resume_and_background_proof_gate",
        "phase_sequence": [
            "startup_complete",
            "stale_daemon_owner",
            "manual_resume",
            "duplicate_resume",
            "resume_state_load",
            "progress_only_background_artifact",
            "final_background_artifacts",
        ],
        "fake_ai_artifacts": [
            "heartbeat_or_manual_resume_event",
            "background_progress_log",
            "background_exit_artifact",
            "background_meta_artifact",
        ],
        "router_entrypoints": [
            "router_runtime.record_external_event",
            "router_runtime.next_action",
            "router_runtime.apply_action",
            "background_artifact_classifier",
        ],
        "required_ack_or_receipt_gates": [
            "resume_reentry_evidence",
            "controller_action_ledger_loaded",
            "background_exit_artifact",
            "background_meta_artifact",
        ],
        "allowed_event_boundary": "resume events may trigger load_resume_state but progress-only proof cannot close work",
        "forbidden_shortcuts": [
            "direct_state_mutation",
            "daemon_status_live_without_owner_check",
            "duplicate_resume_double_advance",
            "progress_only_background_completion",
        ],
        "expected_standard_state": "resume_state_loaded_and_background_proof_classifies_passed_only_after_final_artifacts",
        "evidence_id": "real_router.recovery.resume_and_background_proof_gate",
        "evidence_test": (
            "FlowPilotRealRouterDryRunRehearsalTests."
            "test_recovery_rehearsal_resume_idempotency_and_background_proof_gate"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "supporting_evidence": [
            "control_plane_canary.dead_daemon_resume",
            "control_plane_canary.progress_only_background_artifact",
        ],
        "confidence_boundary": "proves selected compounded recovery/proof gates return to legal control-plane state",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "rehearsal_id": "real_router.repair.producer_proof_recovery",
        "phase_sequence": [
            "startup_complete",
            "material_scan_dispatch",
            "stale_worker_result_flags",
            "control_blocker",
            "pm_no_producer_repair_rejected",
            "pm_packet_reissue_repair",
            "producer_backed_wait_exposed",
        ],
        "fake_ai_artifacts": [
            "material_scan_packets",
            "stale_worker_result_flags",
            "pm_no_producer_repair_decision",
            "pm_packet_reissue_repair_decision",
            "repair_packet_generation",
        ],
        "router_entrypoints": [
            "router_runtime.record_external_event",
            "router_runtime.next_action",
            "packet_runtime.create_packet",
        ],
        "required_ack_or_receipt_gates": [
            "pm_repair_decision_envelope",
            "repair_packet_generation_receipt",
            "producer_evidence_on_followup_wait",
        ],
        "allowed_event_boundary": (
            "post-repair waits count only when the repair transaction exposes current producer evidence"
        ),
        "forbidden_shortcuts": [
            "direct_state_mutation",
            "stale_worker_result_flag_as_fresh_producer",
            "role_reissue_without_packet_generation",
            "await_role_event_without_producer_evidence",
        ],
        "expected_standard_state": "legal_wait_with_repair_packet_generation_producer_evidence",
        "evidence_id": "real_router.repair.producer_proof_recovery",
        "evidence_test": (
            "FlowPilotRealRouterDryRunRehearsalTests."
            "test_real_router_repair_rehearsal_rejects_no_producer_then_accepts_packet_reissue"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "supporting_evidence": [
            "e2e.pm_repair.no_producer_then_packet_reissue",
            "repair_transactions.negative.material_role_reissue_no_producer",
        ],
        "confidence_boundary": (
            "proves a prepared fake PM repair cannot advance until a current repair producer exists"
        ),
        "live_ai_semantic_quality_proven": False,
    },
    {
        "rehearsal_id": "real_router.authority.rejects_shortcut_overclaims",
        "phase_sequence": [
            "matrix_validation",
            "known_bad_rows",
            "authority_rejection",
        ],
        "fake_ai_artifacts": [
            "missing_ack_row",
            "invented_event_row",
            "direct_state_mutation_row",
            "progress_only_proof_row",
            "semantic_overclaim_row",
        ],
        "router_entrypoints": [
            "matrix_validator",
            "router_event_catalog",
            "background_artifact_classifier",
        ],
        "required_ack_or_receipt_gates": [
            "matrix_required_ack_or_receipt_gates",
            "matrix_allowed_event_boundary",
            "matrix_forbidden_shortcuts",
        ],
        "allowed_event_boundary": "known-bad rows are rejected before they can be counted as rehearsal proof",
        "forbidden_shortcuts": [
            "missing_ack_or_receipt_gate",
            "invented_external_event",
            "direct_state_mutation",
            "progress_only_background_completion",
            "semantic_quality_overclaim",
        ],
        "expected_standard_state": "known_bad_rejected_without_pass_evidence",
        "evidence_id": "real_router.authority.rejects_shortcut_overclaims",
        "evidence_test": (
            "FlowPilotRealRouterDryRunRehearsalMatrixTests.test_known_bad_rows_are_rejected"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "supporting_evidence": ["hard_gate_red_team_matrix"],
        "confidence_boundary": "prevents rehearsal coverage from counting shortcut or overclaimed rows",
        "live_ai_semantic_quality_proven": False,
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in REHEARSAL_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_ids = {str(row.get("rehearsal_id") or "") for row in rows}
    for rehearsal_id in sorted(REQUIRED_REHEARSAL_IDS - present_ids):
        findings.append(
            {
                "code": "missing_required_rehearsal",
                "rehearsal_id": rehearsal_id,
                "message": "required real-Router rehearsal row is missing",
            }
        )

    for row in rows:
        rehearsal_id = str(row.get("rehearsal_id") or "")
        missing_fields = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None, [])
        ]
        if missing_fields:
            findings.append(
                {
                    "code": "missing_required_field",
                    "rehearsal_id": rehearsal_id,
                    "missing_fields": missing_fields,
                    "message": "real-Router rehearsal row is missing required field(s)",
                }
            )

        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            if evidence_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_evidence_id",
                        "rehearsal_id": rehearsal_id,
                        "evidence_id": evidence_id,
                        "message": "rehearsal evidence ids must be unique",
                    }
                )
            seen_ids.add(evidence_id)

        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "rehearsal_id": rehearsal_id,
                    "message": "primary real-Router rehearsal evidence must be passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "rehearsal_id": rehearsal_id,
                    "message": "real-Router rehearsal evidence must be current",
                }
            )
        if str(row.get("evidence_role") or "") not in PRIMARY_ROLES | SUPPORTING_ROLES:
            findings.append(
                {
                    "code": "invalid_evidence_role",
                    "rehearsal_id": rehearsal_id,
                    "message": "evidence role must classify primary or supporting rehearsal coverage",
                }
            )
        if not set(row.get("router_entrypoints", [])) & REQUIRED_ENTRYPOINTS:
            findings.append(
                {
                    "code": "missing_real_router_entrypoint",
                    "rehearsal_id": rehearsal_id,
                    "message": "row must name at least one real Router/runtime entrypoint",
                }
            )
        if "direct_state_mutation" not in [str(item) for item in row.get("forbidden_shortcuts", [])]:
            findings.append(
                {
                    "code": "missing_direct_state_mutation_ban",
                    "rehearsal_id": rehearsal_id,
                    "message": "row must explicitly forbid direct state mutation as coverage evidence",
                }
            )
        if not any("ack" in str(item).lower() or "receipt" in str(item).lower() for item in row.get("required_ack_or_receipt_gates", [])):
            findings.append(
                {
                    "code": "missing_ack_or_receipt_gate",
                    "rehearsal_id": rehearsal_id,
                    "message": "row must name a required ACK or receipt gate",
                }
            )
        if "invented_external_event" in [str(item) for item in row.get("fake_ai_artifacts", [])]:
            findings.append(
                {
                    "code": "invented_external_event_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "invented external events cannot be counted as fake AI artifacts",
                }
            )
        if (
            "progress_only_background_artifact" in [str(item) for item in row.get("fake_ai_artifacts", [])]
            and "final_background_artifacts" not in [str(phase) for phase in row.get("phase_sequence", [])]
        ):
            findings.append(
                {
                    "code": "progress_only_final_proof_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "progress-only background output cannot be final proof",
                }
            )
        fake_artifacts = [str(item) for item in row.get("fake_ai_artifacts", [])]
        forbidden = [str(item) for item in row.get("forbidden_shortcuts", [])]
        expected_state = str(row.get("expected_standard_state") or "")
        if "pm_no_producer_repair_decision" in fake_artifacts and "repair_packet_generation" not in fake_artifacts:
            findings.append(
                {
                    "code": "no_producer_repair_without_generation",
                    "rehearsal_id": rehearsal_id,
                    "message": "no-producer PM repair rows must include corrected repair packet generation",
                }
            )
        if (
            "stale_worker_result_flags" in fake_artifacts
            and "stale_worker_result_flag_as_fresh_producer" not in forbidden
            and "repair_packet_generation" not in expected_state
        ):
            findings.append(
                {
                    "code": "stale_evidence_used_as_repair_proof",
                    "rehearsal_id": rehearsal_id,
                    "message": "stale worker flags must be forbidden or superseded by current repair generation evidence",
                }
            )
        if "terminal" in rehearsal_id and "closed" not in str(row.get("expected_standard_state") or ""):
            findings.append(
                {
                    "code": "missing_terminal_standard_state",
                    "rehearsal_id": rehearsal_id,
                    "message": "terminal rehearsal rows must name a closed standard state",
                }
            )
        if row.get("live_ai_semantic_quality_proven") is not False:
            findings.append(
                {
                    "code": "semantic_quality_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "fake package rehearsal cannot prove live AI semantic quality",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "rehearsal_id": "known.bad",
        "phase_sequence": ["startup"],
        "fake_ai_artifacts": ["fake_report"],
        "router_entrypoints": ["router_cli.next"],
        "required_ack_or_receipt_gates": ["card_ack"],
        "allowed_event_boundary": "known Router event only",
        "forbidden_shortcuts": ["direct_state_mutation"],
        "expected_standard_state": "blocked_until_repair",
        "evidence_id": "known.bad",
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_real_router_rehearsal",
        "confidence_boundary": "known bad fixture",
        "live_ai_semantic_quality_proven": False,
    }
    return [
        {
            "name": "missing_ack_or_receipt",
            "rows": [{**base, "required_ack_or_receipt_gates": []}],
            "expected_codes": ["missing_required_field", "missing_ack_or_receipt_gate", "missing_required_rehearsal"],
        },
        {
            "name": "invented_external_event_artifact",
            "rows": [{**base, "fake_ai_artifacts": ["invented_external_event"]}],
            "expected_codes": ["invented_external_event_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "direct_state_mutation_not_forbidden",
            "rows": [{**base, "forbidden_shortcuts": ["manual_flag_set"]}],
            "expected_codes": ["missing_direct_state_mutation_ban", "missing_required_rehearsal"],
        },
        {
            "name": "progress_only_without_final_artifacts",
            "rows": [{**base, "fake_ai_artifacts": ["progress_only_background_artifact"]}],
            "expected_codes": ["progress_only_final_proof_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "non_terminal_final_state",
            "rows": [
                {
                    **base,
                    "rehearsal_id": "real_router.full.startup_to_terminal_fake_ai_packages",
                    "expected_standard_state": "ready_for_pm_review",
                }
            ],
            "expected_codes": ["missing_terminal_standard_state", "missing_required_rehearsal"],
        },
        {
            "name": "semantic_quality_overclaim",
            "rows": [{**base, "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["semantic_quality_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "no_producer_repair_without_generation",
            "rows": [
                {
                    **base,
                    "fake_ai_artifacts": ["pm_no_producer_repair_decision"],
                    "expected_standard_state": "awaiting_worker_result_without_new_packet",
                }
            ],
            "expected_codes": ["no_producer_repair_without_generation", "missing_required_rehearsal"],
        },
        {
            "name": "stale_worker_flags_used_as_repair_proof",
            "rows": [
                {
                    **base,
                    "fake_ai_artifacts": ["stale_worker_result_flags"],
                    "forbidden_shortcuts": ["direct_state_mutation"],
                    "expected_standard_state": "awaiting_worker_result_without_new_packet",
                }
            ],
            "expected_codes": ["stale_evidence_used_as_repair_proof", "missing_required_rehearsal"],
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
    rows_by_entrypoint = Counter(
        entrypoint
        for row in rows
        for entrypoint in row.get("router_entrypoints", [])
    )
    return {
        "ok": not findings,
        "result_type": "flowpilot_real_router_dry_run_rehearsal_matrix",
        "coverage_boundary": (
            "Rows prove prepared fake AI packages can exercise selected real Router/runtime control-plane "
            "paths, including ACK/receipt, recovery, proof, and terminal gates. They do not prove live AI "
            "semantic quality or every possible project-specific failure."
        ),
        "required_rehearsal_count": len(REQUIRED_REHEARSAL_IDS),
        "row_count": len(rows),
        "rows_by_phase": dict(sorted(rows_by_phase.items())),
        "rows_by_entrypoint": dict(sorted(rows_by_entrypoint.items())),
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
