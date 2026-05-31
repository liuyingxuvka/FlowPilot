"""Shadow launcher chaos coverage matrix for FlowPilot.

This matrix closes the gap between prepared fake-AI work packages and the
real installed launcher/Router control plane. It tracks bounded scenarios that
must pass before claiming the system can recover to a standard state when the
AI follows FlowPilot's protocol but the control plane hits common failure
modes.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLES = {"primary_shadow_rehearsal"}
SUPPORTING_ROLES = {"supporting_matrix", "supporting_runtime"}
REQUIRED_SURFACES = {
    "installed_launcher",
    "crash_recovery",
    "peer_conflict",
    "current_pointer",
    "malformed_packages",
    "bounded_soak",
}
REQUIRED_REHEARSAL_IDS = {
    "shadow.launcher.installed_skill_cli_startup",
    "shadow.crash_recovery.stale_lock_duplicate_resume_progress_proof",
    "shadow.peer_conflict.current_run_isolation",
    "shadow.current_pointer.install_freshness",
    "shadow.malformed_packages.finite_bad_package_classes",
    "shadow.soak.bounded_startup_recovery_cleanup",
}

REQUIRED_ROW_FIELDS = (
    "rehearsal_id",
    "surface",
    "phase_sequence",
    "entrypoints",
    "fake_ai_artifacts",
    "failure_injection",
    "expected_standard_state",
    "protected_state_invariant",
    "required_evidence",
    "forbidden_shortcuts",
    "finite_package_classes",
    "soak_cycle_bound",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "live_ai_semantic_quality_proven",
    "destructive_live_state_mutation",
    "confidence_boundary",
)


MALFORMED_PACKAGE_CLASSES = (
    "missing_runtime_envelope",
    "wrong_event_schema",
    "controller_visible_body_leak",
    "wrong_author_role",
    "stale_hash_or_path",
)


SHADOW_LAUNCHER_CHAOS_ROWS: tuple[dict[str, Any], ...] = (
    {
        "rehearsal_id": "shadow.launcher.installed_skill_cli_startup",
        "surface": "installed_launcher",
        "phase_sequence": ["installed_skill_entrypoint", "start", "state", "daemon_stop"],
        "entrypoints": ["installed_flowpilot_skill", "flowpilot_router.py", "state", "daemon-stop"],
        "fake_ai_artifacts": ["startup_intake_receipt", "router_action_ledger"],
        "failure_injection": "installed_launcher_shadow_run_without_repo_cli_shortcut",
        "expected_standard_state": "current_run_created_with_router_state_and_releasable_daemon_lock",
        "protected_state_invariant": "installed launcher must create run-scoped .flowpilot state through the public Router CLI",
        "required_evidence": [
            "installed_skill_path_exists",
            "subprocess_cli_exit_zero",
            "current_json_written",
            "state_command_returns_run_root",
            "daemon_stop_exit_zero_or_no_live_daemon",
        ],
        "forbidden_shortcuts": ["direct_router_state_mutation", "repo_only_router_main_call"],
        "finite_package_classes": ["startup_shadow_package"],
        "soak_cycle_bound": 1,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_installed_launcher_shadow_start_reaches_releasable_standard_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves installed launcher control flow, not live model reasoning quality",
    },
    {
        "rehearsal_id": "shadow.crash_recovery.stale_lock_duplicate_resume_progress_proof",
        "surface": "crash_recovery",
        "phase_sequence": ["startup", "activation", "stale_daemon_lock", "duplicate_resume", "proof_gate"],
        "entrypoints": ["record-event", "next", "load_resume_state", "background_artifact_classifier"],
        "fake_ai_artifacts": ["heartbeat_resume_event", "resume_reentry", "background_artifacts"],
        "failure_injection": "dead_daemon_lock_duplicate_resume_and_progress_only_background_log",
        "expected_standard_state": "resume_state_loaded_after_liveness_check_and_progress_only_proof_rejected",
        "protected_state_invariant": "resume cannot continue normal work until daemon liveness and final proof artifacts are checked",
        "required_evidence": [
            "dead_daemon_decision_restart",
            "duplicate_resume_idempotent",
            "resume_reentry_written",
            "progress_only_background_status_rejected",
        ],
        "forbidden_shortcuts": ["count_progress_line_as_pass", "skip_resume_liveness_check"],
        "finite_package_classes": ["resume_shadow_package", "background_progress_only_artifact"],
        "soak_cycle_bound": 1,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_crash_recovery_bundle_handles_dead_daemon_duplicate_resume_and_progress_only_proof"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "does not prove external scheduler exactly-once delivery",
    },
    {
        "rehearsal_id": "shadow.peer_conflict.current_run_isolation",
        "surface": "peer_conflict",
        "phase_sequence": ["parallel_runs", "two_daemon_locks", "peer_stop", "current_state_assert"],
        "entrypoints": ["stop_router_daemon", "current.json", "router_daemon.lock"],
        "fake_ai_artifacts": ["peer_run_a_state", "current_run_b_state", "peer_background_proof"],
        "failure_injection": "peer_run_stop_and_stale_peer_proof_attempt_while_current_run_is_active",
        "expected_standard_state": "peer_run_released_current_run_still_active_and_peer_proof_not_current",
        "protected_state_invariant": "current run focus and current daemon lock remain authoritative under peer cleanup",
        "required_evidence": [
            "peer_lock_released",
            "current_pointer_unchanged",
            "current_lock_still_active",
            "stale_peer_proof_marked_not_current",
        ],
        "forbidden_shortcuts": ["rewrite_current_pointer_to_peer", "reuse_peer_proof_as_current_run_proof"],
        "finite_package_classes": ["peer_stop_shadow_package", "peer_proof_shadow_package"],
        "soak_cycle_bound": 1,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_peer_conflict_keeps_current_run_authority_and_rejects_stale_peer_proof"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "does not prove simultaneous human edits to current.json",
    },
    {
        "rehearsal_id": "shadow.current_pointer.install_freshness",
        "surface": "current_pointer",
        "phase_sequence": ["current_pointer", "state_load", "installed_source_presence"],
        "entrypoints": ["state", "load_bootstrap_state", "load_run_state", "installed_skill_files"],
        "fake_ai_artifacts": ["current_pointer", "minimal_running_run"],
        "failure_injection": "current_pointer_fields_and_existing_installed_skill",
        "expected_standard_state": "current_pointer_resolves_to_current_run_state_without_unscoped_state",
        "protected_state_invariant": "current pointer must identify the run root authority without unscoped state fallback",
        "required_evidence": [
            "current_run_root_loaded",
            "run_state_matches_current_pointer_run",
            "installed_skill_assets_present",
        ],
        "forbidden_shortcuts": ["fallback_to_unscoped_dot_flowpilot_root", "assume_install_fresh_without_file_evidence"],
        "finite_package_classes": ["current_pointer_shadow_package"],
        "soak_cycle_bound": 1,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_current_pointer_and_installed_assets_resolve_to_current_standard_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "does not prove arbitrary external state recovery",
    },
    {
        "rehearsal_id": "shadow.malformed_packages.finite_bad_package_classes",
        "surface": "malformed_packages",
        "phase_sequence": ["startup_wait", "bad_package_generator", "record_event_rejection", "state_unchanged"],
        "entrypoints": ["role-output-envelope", "record-event", "RouterError"],
        "fake_ai_artifacts": list(MALFORMED_PACKAGE_CLASSES),
        "failure_injection": "finite_generated_bad_fake_ai_packages",
        "expected_standard_state": "bad_packages_blocked_or_quarantined_without_startup_activation",
        "protected_state_invariant": "bad role output cannot advance the Router wait or leak body content to Controller",
        "required_evidence": [
            "finite_bad_package_class_list",
            "each_bad_package_rejected",
            "startup_activation_flag_still_false",
        ],
        "forbidden_shortcuts": ["unbounded_random_fuzz_claim", "accept_controller_visible_body_fields"],
        "finite_package_classes": list(MALFORMED_PACKAGE_CLASSES),
        "soak_cycle_bound": 1,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_malformed_fake_ai_package_generator_rejects_finite_bad_classes"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "finite generator proves named protocol classes, not arbitrary natural-language bad answers",
    },
    {
        "rehearsal_id": "shadow.soak.bounded_startup_recovery_cleanup",
        "surface": "bounded_soak",
        "phase_sequence": ["cycle_startup", "cycle_recovery_probe", "cycle_stop_cleanup", "residue_check"],
        "entrypoints": ["next", "record-event", "daemon-stop", "router_daemon.lock"],
        "fake_ai_artifacts": ["startup_shadow_package", "resume_shadow_package"],
        "failure_injection": "two_cycle_startup_resume_stop_repetition",
        "expected_standard_state": "each_cycle_finishes_with_released_or_terminal_daemon_lock_and_no_cross_cycle_current_leak",
        "protected_state_invariant": "repeated bounded control-plane cycles do not reuse stale run authority across temp projects",
        "required_evidence": [
            "cycle_count_bounded",
            "each_cycle_has_current_run",
            "each_cycle_stop_releases_daemon_authority",
        ],
        "forbidden_shortcuts": ["claim_unbounded_soak", "share_temp_project_between_cycles"],
        "finite_package_classes": ["startup_shadow_package", "resume_shadow_package"],
        "soak_cycle_bound": 2,
        "evidence_test": (
            "FlowPilotShadowLauncherChaosReplayTests."
            "test_bounded_soak_repeats_startup_recovery_and_cleanup_without_residue"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "bounded soak catches residue regressions but is not a long-duration stress test",
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in SHADOW_LAUNCHER_CHAOS_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_ids = {str(row.get("rehearsal_id") or "") for row in rows}
    for rehearsal_id in sorted(REQUIRED_REHEARSAL_IDS - present_ids):
        findings.append(
            {
                "code": "missing_required_rehearsal",
                "rehearsal_id": rehearsal_id,
                "message": "required shadow launcher chaos rehearsal row is missing",
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
                    "message": "shadow launcher chaos row is missing required field(s)",
                }
            )

        if rehearsal_id:
            if rehearsal_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_rehearsal_id",
                        "rehearsal_id": rehearsal_id,
                        "message": "shadow launcher chaos rehearsal ids must be unique",
                    }
                )
            seen_ids.add(rehearsal_id)

        if str(row.get("surface") or "") not in REQUIRED_SURFACES:
            findings.append(
                {
                    "code": "unknown_surface",
                    "rehearsal_id": rehearsal_id,
                    "surface": str(row.get("surface") or ""),
                    "message": "row surface must be one of the required shadow chaos surfaces",
                }
            )
        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "rehearsal_id": rehearsal_id,
                    "message": "primary shadow rehearsal evidence must be passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "rehearsal_id": rehearsal_id,
                    "message": "shadow rehearsal evidence must be current",
                }
            )
        if str(row.get("evidence_role") or "") not in PRIMARY_ROLES | SUPPORTING_ROLES:
            findings.append(
                {
                    "code": "invalid_evidence_role",
                    "rehearsal_id": rehearsal_id,
                    "message": "evidence role must classify primary or supporting shadow coverage",
                }
            )
        if row.get("destructive_live_state_mutation") is not False:
            findings.append(
                {
                    "code": "live_state_mutation_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "shadow rehearsals must stay in isolated temp runs and cannot mutate live user state",
                }
            )
        if row.get("live_ai_semantic_quality_proven") is not False:
            findings.append(
                {
                    "code": "live_ai_semantic_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "fake AI packages prove protocol flow, not live model answer quality",
                }
            )
        if (
            row.get("surface") == "installed_launcher"
            and "installed_flowpilot_skill" not in {str(item) for item in row.get("entrypoints", [])}
        ):
            findings.append(
                {
                    "code": "missing_installed_launcher_entrypoint",
                    "rehearsal_id": rehearsal_id,
                    "message": "installed launcher row must bind to the installed FlowPilot skill",
                }
            )
        if (
            row.get("surface") == "malformed_packages"
            and set(row.get("finite_package_classes") or []) != set(MALFORMED_PACKAGE_CLASSES)
        ):
            findings.append(
                {
                    "code": "bad_package_classes_not_finite_or_complete",
                    "rehearsal_id": rehearsal_id,
                    "message": "malformed package row must enumerate the finite required bad package classes",
                }
            )
        cycle_bound = row.get("soak_cycle_bound")
        if not isinstance(cycle_bound, int) or cycle_bound < 1:
            findings.append(
                {
                    "code": "invalid_soak_cycle_bound",
                    "rehearsal_id": rehearsal_id,
                    "message": "row must declare a positive bounded soak cycle count",
                }
            )
        elif row.get("surface") == "bounded_soak" and cycle_bound > 3:
            findings.append(
                {
                    "code": "unbounded_soak_overclaim",
                    "rehearsal_id": rehearsal_id,
                    "message": "fast-tier shadow soak rows must stay bounded and must not claim unlimited stress coverage",
                }
            )
        if "direct_router_state_mutation" in {str(item) for item in row.get("forbidden_shortcuts", [])}:
            if row.get("surface") != "installed_launcher":
                findings.append(
                    {
                        "code": "shortcut_scope_mismatch",
                        "rehearsal_id": rehearsal_id,
                        "message": "direct state mutation shortcut is only the installed launcher row's explicit forbidden shortcut",
                    }
                )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "rehearsal_id": "known.bad",
        "surface": "installed_launcher",
        "phase_sequence": ["start"],
        "entrypoints": ["installed_flowpilot_skill"],
        "fake_ai_artifacts": ["known_bad_package"],
        "failure_injection": "known_bad",
        "expected_standard_state": "blocked_until_repair",
        "protected_state_invariant": "bad input cannot mutate protected state",
        "required_evidence": ["test_evidence"],
        "forbidden_shortcuts": ["repo_only_router_main_call"],
        "finite_package_classes": ["known_bad_package"],
        "soak_cycle_bound": 1,
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_shadow_rehearsal",
        "live_ai_semantic_quality_proven": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "known bad fixture only",
    }
    return [
        {
            "name": "progress_only_background_evidence",
            "rows": [{**base, "evidence_status": "progress_only"}],
            "expected_codes": ["invalid_evidence_status", "missing_required_rehearsal"],
        },
        {
            "name": "stale_peer_proof",
            "rows": [{**base, "surface": "peer_conflict", "evidence_current": False}],
            "expected_codes": ["stale_evidence", "missing_required_rehearsal"],
        },
        {
            "name": "missing_installed_launcher_evidence",
            "rows": [{**base, "entrypoints": ["repo_only_router_main_call"]}],
            "expected_codes": ["missing_installed_launcher_entrypoint", "missing_required_rehearsal"],
        },
        {
            "name": "direct_state_mutation",
            "rows": [{**base, "destructive_live_state_mutation": True}],
            "expected_codes": ["live_state_mutation_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "unbounded_soak_claim",
            "rows": [{**base, "surface": "bounded_soak", "soak_cycle_bound": 100}],
            "expected_codes": ["unbounded_soak_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "live_ai_semantic_overclaim",
            "rows": [{**base, "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["live_ai_semantic_overclaim", "missing_required_rehearsal"],
        },
        {
            "name": "malformed_package_class_missing",
            "rows": [
                {
                    **base,
                    "surface": "malformed_packages",
                    "finite_package_classes": ["missing_runtime_envelope"],
                }
            ],
            "expected_codes": ["bad_package_classes_not_finite_or_complete", "missing_required_rehearsal"],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    findings = validate_rows(rows)
    rows_by_surface = Counter(str(row["surface"]) for row in rows)
    return {
        "ok": not findings,
        "result_type": "flowpilot_shadow_launcher_chaos_matrix",
        "coverage_boundary": (
            "Rows prove bounded end-to-end control-plane behavior through fake AI packages, the installed "
            "launcher, real Router state, daemon recovery, peer isolation, malformed package rejection, "
            "and short cleanup repetition. They do not prove arbitrary live AI semantic quality, every "
            "historical migration, or indefinite stress behavior."
        ),
        "required_surface_count": len(REQUIRED_SURFACES),
        "required_rehearsal_count": len(REQUIRED_REHEARSAL_IDS),
        "row_count": len(rows),
        "rows_by_surface": dict(sorted(rows_by_surface.items())),
        "malformed_package_classes": list(MALFORMED_PACKAGE_CLASSES),
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
