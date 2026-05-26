"""Known-friction parent gate for recurring FlowPilot failure classes.

The child replay suites prove bounded slices. This parent matrix prevents those
slice-level passes from being reported as full confidence until each historical
friction class has current model, replay, runtime, install, and evidence
boundaries.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLE = "primary_known_friction_gate"

REQUIRED_FRICTION_IDS = {
    "known_friction.worker_self_check_failure",
    "known_friction.pm_repair_atomicity",
    "known_friction.packet_reissue_continuation",
    "known_friction.status_projection_stale",
    "known_friction.ack_false_blocker",
    "known_friction.controlled_stop_reconciliation",
}

REQUIRED_SOURCE_CLASSES = {
    "worker_output_contract_failure",
    "pm_repair_transaction_interleaving",
    "material_packet_generation_reissue",
    "user_visible_status_projection",
    "ack_completion_conflation",
    "daemon_lifecycle_stop_boundary",
}

REQUIRED_GLOBAL_GATES = {
    "repo_source_to_installed_skill_sync",
    "copied_runtime_kit_freshness",
    "historical_live_run_replay",
    "background_final_artifact_contract",
    "current_transcript_regression",
    "scoped_confidence_disclosure",
}

REQUIRED_ROW_FIELDS = (
    "friction_id",
    "priority",
    "source_class",
    "historical_bad_case",
    "trigger_state",
    "expected_safe_behavior",
    "model_obligation",
    "model_check",
    "runtime_surface",
    "runtime_test",
    "replay_fixture",
    "child_evidence_ids",
    "global_gates",
    "forbidden_shortcuts",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "full_confidence_boundary",
    "live_ai_semantic_quality_proven",
)


KNOWN_FRICTION_ROWS: tuple[dict[str, Any], ...] = (
    {
        "friction_id": "known_friction.worker_self_check_failure",
        "priority": "P0",
        "source_class": "worker_output_contract_failure",
        "historical_bad_case": "Worker material-scan result body has a Contract Self-Check heading but misses required machine fields.",
        "trigger_state": "material_scan batch is results_relayed_to_pm and PM must decide whether every worker result satisfies the source output contract.",
        "expected_safe_behavior": "PM disposition records rework without reviewer release, status names the failed self-check, and repair continues through fresh packet generation.",
        "model_obligation": "control_plane_friction.pm_package_disposition_packet_outcomes_missing",
        "model_check": "python simulations/run_flowpilot_control_plane_friction_checks.py",
        "runtime_surface": "role_output_runtime + packet_runtime + material_scan PM disposition writer",
        "runtime_test": "tests.test_flowpilot_output_contracts.FlowPilotOutputContractTests.test_contract_self_check_metadata_reports_live_worker_missing_fields",
        "replay_fixture": "historical_live_run.semantic.contract.missing_standard_matrix_or_waiver",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "hard_gate_red_team_matrix",
            "pm_package_disposition_semantics",
        ],
        "global_gates": [
            "repo_source_to_installed_skill_sync",
            "copied_runtime_kit_freshness",
            "historical_live_run_replay",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "treat_contract_self_check_heading_as_pass",
            "release_reviewer_gate_without_formal_pm_package",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers missing mechanical self-check fields and PM package disposition behavior; does not judge live AI semantic quality.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.pm_repair_atomicity",
        "priority": "P0",
        "source_class": "pm_repair_transaction_interleaving",
        "historical_bad_case": "PM repair decision writes allowed follow-up events before daemon-visible state can see the PM repair decision flag.",
        "trigger_state": "control blocker requires PM repair and Router commits a follow-up wait or recheck event.",
        "expected_safe_behavior": "Repair transaction, blocker index, decision flag, and daemon-visible next action are committed as one post-decision boundary.",
        "model_obligation": "repair_transactions.pm_decision_flag_atomicity",
        "model_check": "python simulations/run_flowpilot_repair_transaction_checks.py",
        "runtime_surface": "control_blocker PM repair decision handler + persistent router daemon status projection",
        "runtime_test": "tests.router_runtime.material_modeling.MaterialModelingRuntimeTests.test_pm_repair_decision_side_effect_exposes_flag_before_wait_events",
        "replay_fixture": "known_friction.pm_repair_decision_enables_material_recheck",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "control_plane_failure_canary_matrix",
            "e2e_synthetic_chaos_matrix",
            "real_router_dry_run_rehearsal_matrix",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "background_final_artifact_contract",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "relax_required_pm_repair_flag",
            "count_model_only_daemon_projection_as_live_evidence",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers executable repair waits and daemon-visible state for selected interleavings; does not prove an unbounded daemon soak.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.packet_reissue_continuation",
        "priority": "P0",
        "source_class": "material_packet_generation_reissue",
        "historical_bad_case": "A packet_reissue repair leaves stale PM decision wording or waits for an event without a fresh packet producer.",
        "trigger_state": "material repair requires reissuing worker packets after a rejected or rework-requested result.",
        "expected_safe_behavior": "Router exposes fresh producer evidence and only relays or waits on current-generation material work.",
        "model_obligation": "repair_transactions.material_rework_requires_fresh_producer",
        "model_check": "python simulations/run_flowpilot_repair_transaction_checks.py",
        "runtime_surface": "material packet generation registry + Router next-action projection",
        "runtime_test": "tests.router_runtime.material_modeling.MaterialModelingRuntimeTests.test_pm_material_repair_rejects_role_reissue_without_fresh_packet_producer",
        "replay_fixture": "e2e_synthetic_chaos.stale_worker_result_flags_then_packet_reissue",
        "child_evidence_ids": [
            "e2e_synthetic_chaos_matrix",
            "real_router_dry_run_rehearsal_matrix",
            "historical_live_run_replay_matrix",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "reuse_old_worker_result_flags",
            "wait_for_role_event_without_current_producer",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers current-generation producer proof and stale-result rejection for bounded repair paths; does not prove every packet family.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.status_projection_stale",
        "priority": "P1",
        "source_class": "user_visible_status_projection",
        "historical_bad_case": "Current status or display projection says a stale blocker, old ACK wait, or terminal-looking state while Router facts disagree.",
        "trigger_state": "Router has resolved ACK or PM repair facts but status summary is regenerated from old projection state.",
        "expected_safe_behavior": "User-visible status derives from current Router facts and explicitly treats display as projection, not authority.",
        "model_obligation": "router_loop.historical_live_run_replay_package_suite",
        "model_check": "python simulations/run_flowpilot_model_test_alignment_checks.py",
        "runtime_surface": "current status summary + route frontier display projection",
        "runtime_test": "tests.test_flowpilot_historical_live_run_replay.FlowPilotHistoricalLiveRunReplayTests.test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence",
        "replay_fixture": "historical.snapshot.stale_pending_terminal_display",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "control_plane_failure_canary_matrix",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "trust_chat_display_as_router_state",
            "skip_current_pointer_check",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers stale projection and current-pointer authority; does not prove every UI rendering path.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.ack_false_blocker",
        "priority": "P0",
        "source_class": "ack_completion_conflation",
        "historical_bad_case": "ACK-only receipt clearance reappears as a missing ACK blocker or is mistaken for semantic role output completion.",
        "trigger_state": "Controller/Router return ledger has a valid ACK while the semantic role-output obligation remains pending.",
        "expected_safe_behavior": "ACK wait settlement and output-work completion remain separate obligations with separate status text and replay evidence.",
        "model_obligation": "ack.return_wait_preconsumption",
        "model_check": "python simulations/run_flowpilot_card_envelope_checks.py",
        "runtime_surface": "card ACK return ledger + Router ACK/return preconsumption",
        "runtime_test": "tests.router_runtime.ack_return.AckReturnRuntimeTests.test_record_external_event_preconsumes_valid_card_ack_before_blocking",
        "replay_fixture": "known_friction.ack_only_card_resolved_role_output_pending",
        "child_evidence_ids": [
            "packet/card/ack",
            "historical_live_run_replay_matrix",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "treat_ack_as_role_output_completion",
            "reopen_ack_blocker_after_valid_receipt",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers ACK/return separation for known receipt paths; does not complete semantic role work.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.controlled_stop_reconciliation",
        "priority": "P1",
        "source_class": "daemon_lifecycle_stop_boundary",
        "historical_bad_case": "A controlled stop releases daemon state but current pointer, pending Controller action, heartbeat, or role continuation still looks active.",
        "trigger_state": "User stop/cancel or daemon release races current-run lifecycle projection and resume logic.",
        "expected_safe_behavior": "Stop reconciles current pointer, run lifecycle, daemon status, heartbeat/manual-resume, pending Controller actions, and role continuation authority together.",
        "model_obligation": "terminal.final_ledger_and_backward_replay",
        "model_check": "python simulations/run_flowpilot_runtime_closure_checks.py",
        "runtime_surface": "lifecycle stop request + daemon status + current pointer reconciliation",
        "runtime_test": "tests.router_runtime.terminal.TerminalRuntimeTests.test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work",
        "replay_fixture": "historical_live_run.daemon_lifecycle.user_stop_boundary",
        "child_evidence_ids": [
            "control_plane_failure_canary_matrix",
            "shadow_launcher_chaos_matrix",
            "historical_live_run_replay_matrix",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "resume_stopped_run_without_recovery_decision",
            "treat_released_daemon_lock_as_active",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers controlled stop reconciliation for current pointer, daemon, and pending work authority; does not prove external scheduler delivery.",
        "live_ai_semantic_quality_proven": False,
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in KNOWN_FRICTION_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    present_ids = {str(row.get("friction_id") or "") for row in rows}
    for friction_id in sorted(REQUIRED_FRICTION_IDS - present_ids):
        findings.append(
            {
                "code": "missing_required_friction",
                "friction_id": friction_id,
                "message": "required known-friction row is missing",
            }
        )

    source_classes = {str(row.get("source_class") or "") for row in rows}
    for source_class in sorted(REQUIRED_SOURCE_CLASSES - source_classes):
        findings.append(
            {
                "code": "missing_source_class",
                "source_class": source_class,
                "message": "required historical source class is not represented",
            }
        )

    for row in rows:
        friction_id = str(row.get("friction_id") or "")
        missing = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None, [])
        ]
        if missing:
            findings.append(
                {
                    "code": "missing_required_field",
                    "friction_id": friction_id,
                    "missing_fields": missing,
                    "message": "known-friction row is missing required field(s)",
                }
            )

        if row.get("evidence_status") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "friction_id": friction_id,
                    "message": "known-friction evidence must be passed before parent confidence can pass",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "friction_id": friction_id,
                    "message": "known-friction evidence must be current",
                }
            )
        if row.get("evidence_role") != PRIMARY_ROLE:
            findings.append(
                {
                    "code": "wrong_evidence_role",
                    "friction_id": friction_id,
                    "message": "known-friction rows must use primary parent-gate evidence role",
                }
            )
        if row.get("live_ai_semantic_quality_proven") is not False:
            findings.append(
                {
                    "code": "live_ai_semantic_overclaim",
                    "friction_id": friction_id,
                    "message": "known-friction fake/replay gates cannot prove arbitrary live AI semantic quality",
                }
            )

        child_ids = {str(item) for item in row.get("child_evidence_ids", [])}
        if not child_ids:
            findings.append(
                {
                    "code": "missing_child_evidence",
                    "friction_id": friction_id,
                    "message": "parent row must consume child evidence ids",
                }
            )
        if "historical_live_run_replay_matrix" not in child_ids:
            findings.append(
                {
                    "code": "missing_historical_replay_child",
                    "friction_id": friction_id,
                    "message": "known-friction parent rows must consume historical live-run replay evidence",
                }
            )

        gates = {str(item) for item in row.get("global_gates", [])}
        if "scoped_confidence_disclosure" not in gates:
            findings.append(
                {
                    "code": "missing_confidence_boundary_gate",
                    "friction_id": friction_id,
                    "message": "known-friction rows must preserve scoped/full confidence disclosure",
                }
            )
        if str(row.get("priority") or "") == "P0" and "current_transcript_regression" not in gates:
            findings.append(
                {
                    "code": "p0_missing_current_transcript_gate",
                    "friction_id": friction_id,
                    "message": "P0 known-friction rows must require current transcript regression evidence",
                }
            )

        runtime_surface = str(row.get("runtime_surface") or "")
        runtime_test = str(row.get("runtime_test") or "")
        if "model" in runtime_surface.lower() and "runtime" not in runtime_surface.lower():
            findings.append(
                {
                    "code": "model_only_surface",
                    "friction_id": friction_id,
                    "message": "runtime surface cannot be model-only for known live misses",
                }
            )
        if not runtime_test.startswith(("tests.", "tests/")):
            findings.append(
                {
                    "code": "missing_runtime_test",
                    "friction_id": friction_id,
                    "message": "runtime test must point to a real tests surface",
                }
            )

        forbidden = {str(item) for item in row.get("forbidden_shortcuts", [])}
        if len(forbidden) < 2:
            findings.append(
                {
                    "code": "missing_forbidden_shortcuts",
                    "friction_id": friction_id,
                    "message": "row must forbid at least two shortcuts that caused false confidence",
                }
            )
        boundary = str(row.get("full_confidence_boundary") or "").lower()
        if not boundary or "does not" not in boundary:
            findings.append(
                {
                    "code": "missing_scoped_boundary",
                    "friction_id": friction_id,
                    "message": "row must state what the evidence does not prove",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "friction_id": "known.bad",
        "priority": "P0",
        "source_class": "worker_output_contract_failure",
        "historical_bad_case": "known bad fixture",
        "trigger_state": "known bad state",
        "expected_safe_behavior": "blocked_until_repair",
        "model_obligation": "known_bad.model_obligation",
        "model_check": "python simulations/run_flowpilot_control_plane_friction_checks.py",
        "runtime_surface": "role_output_runtime",
        "runtime_test": "tests.known_bad.KnownBad.test_case",
        "replay_fixture": "known_bad.fixture",
        "child_evidence_ids": ["historical_live_run_replay_matrix"],
        "global_gates": ["current_transcript_regression", "scoped_confidence_disclosure"],
        "forbidden_shortcuts": ["shortcut_one", "shortcut_two"],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "known bad evidence; does not prove live AI semantic quality",
        "live_ai_semantic_quality_proven": False,
    }
    return [
        {
            "name": "missing_required_friction",
            "rows": [{**base, "friction_id": "known_friction.worker_self_check_failure"}],
            "expected_codes": ["missing_required_friction", "missing_source_class"],
        },
        {
            "name": "progress_only_evidence",
            "rows": [{**base, "evidence_status": "progress_only"}],
            "expected_codes": ["invalid_evidence_status", "missing_required_friction"],
        },
        {
            "name": "stale_evidence",
            "rows": [{**base, "evidence_current": False}],
            "expected_codes": ["stale_evidence", "missing_required_friction"],
        },
        {
            "name": "model_only_surface",
            "rows": [{**base, "runtime_surface": "model_check_only"}],
            "expected_codes": ["model_only_surface", "missing_required_friction"],
        },
        {
            "name": "missing_historical_child",
            "rows": [{**base, "child_evidence_ids": ["hard_gate_red_team_matrix"]}],
            "expected_codes": ["missing_historical_replay_child", "missing_required_friction"],
        },
        {
            "name": "live_ai_semantic_overclaim",
            "rows": [{**base, "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["live_ai_semantic_overclaim", "missing_required_friction"],
        },
        {
            "name": "p0_missing_current_transcript",
            "rows": [{**base, "global_gates": ["historical_live_run_replay", "scoped_confidence_disclosure"]}],
            "expected_codes": ["p0_missing_current_transcript_gate", "missing_required_friction"],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    findings = validate_rows(rows)
    rows_by_priority = Counter(str(row["priority"]) for row in rows)
    observed_global_gates = sorted(
        {str(gate) for row in rows for gate in row.get("global_gates", [])}
    )
    missing_global_gates = sorted(REQUIRED_GLOBAL_GATES - set(observed_global_gates))
    for gate in missing_global_gates:
        findings.append(
            {
                "code": "missing_global_gate",
                "gate": gate,
                "message": "required known-friction global gate is not represented",
            }
        )
    return {
        "ok": not findings,
        "result_type": "flowpilot_known_friction_regression_matrix",
        "coverage_boundary": (
            "Rows prove that historically recurring FlowPilot control-plane failures "
            "are represented as parent gates over child fake-AI, historical replay, "
            "runtime, install-sync, current-transcript, and background-evidence checks. "
            "They do not prove arbitrary live AI semantic quality or unbounded production stress."
        ),
        "required_friction_count": len(REQUIRED_FRICTION_IDS),
        "row_count": len(rows),
        "rows_by_priority": dict(sorted(rows_by_priority.items())),
        "required_global_gates": sorted(REQUIRED_GLOBAL_GATES),
        "observed_global_gates": observed_global_gates,
        "missing_global_gates": missing_global_gates,
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
