"""Known-friction parent gate for recurring FlowPilot failure classes.

The child replay suites prove bounded slices. This parent matrix prevents those
slice-level passes from being reported as full confidence until each historical
friction class has current model, replay, runtime, install, and evidence
boundaries.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from flowguard import (
    DEFECT_CASE_ROLE_HISTORICAL_HOLDOUT,
    DEFECT_CASE_ROLE_OBSERVED_FAILURE,
    DEFECT_CASE_ROLE_SAME_CLASS_GENERALIZED,
    DEFECT_FAMILY_DECISION_FULL,
    DEFECT_FAMILY_DECISION_SCOPED,
    RISK_CONFIDENCE_BLOCKED,
    RISK_CONFIDENCE_FULL,
    RISK_CONFIDENCE_SCOPED,
    DefectFamilyCase,
    DefectFamilyEvidence,
    DefectFamilyGate,
    DefectFamilyGatePlan,
    ProofArtifactRef,
    RiskEvidenceLedgerPlan,
    RiskEvidenceProof,
    RiskEvidenceRow,
    review_defect_family_gates,
    review_risk_evidence_ledger,
)
from flowpilot_packet_result_family_parity_model import build_report as build_packet_result_family_parity_report


PASS_STATUSES = {"passed"}
PRIMARY_ROLE = "primary_known_friction_gate"
ROOT = Path(__file__).resolve().parents[1]
SIM_ROOT = Path(__file__).resolve().parent

SCRIPT_RESULT_PATHS = {
    "run_flowpilot_control_plane_friction_checks.py": "simulations/flowpilot_control_plane_friction_results.json",
    "run_flowpilot_repair_transaction_checks.py": "simulations/flowpilot_repair_transaction_results.json",
    "run_flowpilot_event_idempotency_checks.py": "simulations/flowpilot_event_idempotency_results.json",
    "run_flowpilot_model_test_alignment_checks.py": "simulations/flowpilot_model_test_alignment_results.json",
    "run_flowpilot_card_envelope_checks.py": "simulations/flowpilot_card_envelope_results.json",
    "run_flowpilot_runtime_closure_checks.py": "simulations/flowpilot_runtime_closure_results.json",
    "run_flowpilot_role_output_runtime_checks.py": "simulations/flowpilot_role_output_runtime_results.json",
    "run_flowpilot_resume_checks.py": "simulations/flowpilot_resume_results.json",
    "run_flowpilot_terminal_state_monotonicity_checks.py": "simulations/flowpilot_terminal_state_monotonicity_results.json",
    "run_flowpilot_controller_break_glass_checks.py": "simulations/flowpilot_controller_break_glass_results.json",
    "run_flowpilot_daemon_liveness_checks.py": "simulations/flowpilot_daemon_liveness_results.json",
    "run_flowpilot_daemon_terminal_projection_checks.py": "simulations/flowpilot_daemon_terminal_projection_results.json",
}

REQUIRED_FRICTION_IDS = {
    "known_friction.worker_self_check_failure",
    "known_friction.pm_repair_atomicity",
    "known_friction.package_disposition_conflict_replay",
    "known_friction.packet_reissue_continuation",
    "known_friction.status_projection_stale",
    "known_friction.ack_false_blocker",
    "known_friction.controlled_stop_reconciliation",
    "known_friction.local_fixed_router_event_receipt_only",
    "known_friction.resume_rehydration_postcondition_replay_miss",
    "known_friction.control_blocker_same_family_storm",
    "known_friction.protocol_dead_end_reopened_by_resume",
    "known_friction.break_glass_patch_limbo",
    "known_friction.heartbeat_diagnostic_only_resume",
}

REQUIRED_SOURCE_CLASSES = {
    "worker_output_contract_failure",
    "pm_repair_transaction_interleaving",
    "pm_package_disposition_replay_conflict",
    "material_packet_generation_reissue",
    "user_visible_status_projection",
    "ack_completion_conflation",
    "daemon_lifecycle_stop_boundary",
    "local_role_output_receipt_without_router_event",
    "resume_rehydration_postcondition_replay",
    "same_family_control_blocker_repetition",
    "protocol_dead_end_resume_reactivation",
    "break_glass_unvalidated_patch_closure",
    "heartbeat_resume_diagnostic_only_loop",
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
    "defect_family_id",
    "defect_family_recurrence_count",
    "defect_family_high_risk",
    "defect_family_authority_boundary",
    "defect_family_gate_required",
    "defect_family_promoted",
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
        "friction_id": "known_friction.package_disposition_conflict_replay",
        "priority": "P0",
        "source_class": "pm_package_disposition_replay_conflict",
        "historical_bad_case": "A daemon role-output ledger replay sees the same PM package disposition identity with a different body_hash after either a blocker/PM repair owns the conflict or a newer foreground PM body is already canonical.",
        "trigger_state": "A PM package disposition for the same batch/generation is already recorded, a stale conflicting role-output envelope remains replayable, and authority already points at either a blocker/repair owner or the current canonical package artifact.",
        "expected_safe_behavior": "Router classifies the stale conflict, preserves the legal wait or canonical package body, writes audit evidence, never accepts the stale body as success, and keeps the daemon live.",
        "model_obligation": "event_idempotency.package_conflict_repair_owned_replay + event_idempotency.package_conflict_stale_unowned_replay + control_plane_friction.pm_package_repair_owned_conflict_replay + control_plane_friction.pm_package_stale_unowned_conflict_replay",
        "model_check": "python simulations/run_flowpilot_event_idempotency_checks.py && python simulations/run_flowpilot_control_plane_friction_checks.py",
        "runtime_surface": "scoped event identity replay + role-output ledger reconciliation + daemon durable-wait reconciliation",
        "runtime_test": "tests.test_flowpilot_control_plane_contracts.FlowPilotControlPlaneContractTests.test_pm_package_disposition_conflict_classifier_marks_repair_owned_replay; tests.test_flowpilot_role_output_reconciliation.RoleOutputReconciliationTests.test_repair_owned_package_disposition_conflict_replay_is_quarantined_without_daemon_error; tests.test_flowpilot_role_output_reconciliation.RoleOutputReconciliationTests.test_stale_unowned_package_disposition_replay_preserves_canonical_body; tests.test_flowpilot_role_output_reconciliation.RoleOutputReconciliationTests.test_daemon_tick_quarantines_stale_unowned_package_replay_without_reverting_body",
        "replay_fixture": "current_transcript.package_disposition_same_identity_different_body_hash_daemon_replay",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "pm_package_disposition_semantics",
            "daemon_replay_restart_matrix",
        ],
        "global_gates": [
            "repo_source_to_installed_skill_sync",
            "copied_runtime_kit_freshness",
            "historical_live_run_replay",
            "background_final_artifact_contract",
            "current_transcript_regression",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "treat_conflicting_body_hash_as_idempotent_replay",
            "clear_pm_or_control_blocker_wait_from_stale_conflict",
            "let_stale_role_output_replay_overwrite_canonical_package_body",
            "create_duplicate_blocker_for_repair_owned_replay",
            "count_scoped_model_pass_as_live_daemon_evidence",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers known repair-owned and stale-unowned package-disposition body_hash replay branches, including the foreground/daemon interleaving that previously recurred; does not prove unbounded daemon soak or live AI semantic quality without fresh historical replay and daemon artifacts.",
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
    {
        "friction_id": "known_friction.local_fixed_router_event_receipt_only",
        "priority": "P0",
        "source_class": "local_role_output_receipt_without_router_event",
        "historical_bad_case": "run-20260527-212331 recorded repeated PM control-blocker repair receipts through the local submit-output entrypoint, but the fixed Router event was not recorded as the authoritative state transition.",
        "trigger_state": "A formal role-output contract has a fixed Router event and the role tries to close the obligation through a local receipt path.",
        "expected_safe_behavior": "Local-only submission is rejected for fixed-event outputs; the role must use the Router-directed runtime path that records both receipt and Router event evidence before any blocker can close.",
        "model_obligation": "role_output_runtime.accepted_outputs_submit_directly_to_router",
        "model_check": "python simulations/run_flowpilot_role_output_runtime_checks.py",
        "runtime_surface": "role_output_runtime submit-output / submit-output-to-router boundary + Router event recorder",
        "runtime_test": "tests.test_flowpilot_role_output_runtime.FlowPilotRoleOutputRuntimeTests.test_fixed_router_event_output_requires_router_directed_submission",
        "replay_fixture": "run-20260527-212331.pm_control_blocker_repair_receipt_without_router_event",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "role_output_runtime_matrix",
        ],
        "global_gates": [
            "repo_source_to_installed_skill_sync",
            "copied_runtime_kit_freshness",
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "treat_local_receipt_as_router_event",
            "close_control_blocker_before_fixed_router_event_records",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers fixed Router-event output transaction boundaries and local-only rejection; does not prove semantic correctness of the PM decision body.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.resume_rehydration_postcondition_replay_miss",
        "priority": "P0",
        "source_class": "resume_rehydration_postcondition_replay",
        "historical_bad_case": "run-20260527-212331 had a valid six-role rehydration report, but a later receipt replay did not restore resume_roles_restored and reopened a mechanical control blocker.",
        "trigger_state": "Heartbeat/manual resume sees a done rehydrate_role_agents receipt or report while run-state flags are stale or incomplete.",
        "expected_safe_behavior": "Router validates the current-run crew rehydration report, reclaims the resume postcondition idempotently, and only opens a blocker when current-run evidence is absent or invalid.",
        "model_obligation": "resume.resume_rehydration_obligations_replayed_mechanically",
        "model_check": "python simulations/run_flowpilot_resume_checks.py",
        "runtime_surface": "startup resume binding reports + Controller scheduler receipt reconciliation",
        "runtime_test": "tests.router_runtime.resume.ResumeRuntimeTests.test_done_rehydrate_receipt_reclaims_existing_current_run_report_before_blocker",
        "replay_fixture": "run-20260527-212331.crew_rehydration_report_ready_but_resume_flags_false",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "resume_rehydration_replay",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "ignore_current_run_crew_rehydration_report",
            "open_rehydrate_blocker_before_replay_scan",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers current-run six-role report replay and invalid-report blocking; does not prove host agents stay alive forever after rehydration.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.control_blocker_same_family_storm",
        "priority": "P0",
        "source_class": "same_family_control_blocker_repetition",
        "historical_bad_case": "run-20260527-212331 accumulated hundreds of blockers with the same mechanical_control_plane_reissue family key instead of preserving one active PM/control repair state.",
        "trigger_state": "The same responsible role, action type, stage, postcondition, and error class fails repeatedly during heartbeat/manual resume.",
        "expected_safe_behavior": "Router computes a same-family key before writing, reuses active or PM-pending family records, and still materializes distinct blockers for distinct causes.",
        "model_obligation": "control_plane_friction.control_blocker_action_identity_bound_to_artifact + control_blocker.family_key_coalescing",
        "model_check": "python simulations/run_flowpilot_control_plane_friction_checks.py",
        "runtime_surface": "control blocker write path, active index summaries, PM repair decision terminal disposition",
        "runtime_test": "tests.router_runtime.control_blockers.ControlBlockersRuntimeTests.test_same_family_pending_pm_control_blocker_reuses_existing_artifact",
        "replay_fixture": "run-20260527-212331.repeated_mechanical_control_plane_reissue_family",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "control_blocker_family_runtime",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "write_new_blocker_for_same_family_pending_pm",
            "swallow_distinct_blocker_with_old_family_record",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers same-family blocker coalescing and distinct-cause materialization for the audited control paths; does not prove every future blocker schema has a perfect family key.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.protocol_dead_end_reopened_by_resume",
        "priority": "P0",
        "source_class": "protocol_dead_end_resume_reactivation",
        "historical_bad_case": "run-20260527-212331 recorded PM protocol-dead-end / terminal-stop decisions, but heartbeat/manual resume could still reopen the same blocker family instead of surfacing the terminal protocol boundary.",
        "trigger_state": "A same-family control blocker already has a terminal protocol-dead-end disposition and a resume tick replays the old failure.",
        "expected_safe_behavior": "Router writes durable protocol-dead-end lifecycle evidence, marks the run state terminal/protocol-dead-end, and suppresses same-family reopen during resume.",
        "model_obligation": "control_plane_friction.control_blocker_done_receipt_applies_delivery_postcondition + control_blocker.protocol_dead_end_terminal_disposition",
        "model_check": "python simulations/run_flowpilot_control_plane_friction_checks.py && python simulations/run_flowpilot_daemon_terminal_projection_checks.py",
        "runtime_surface": "PM repair decision handler + control blocker family lookup + daemon terminal projection",
        "runtime_test": "tests.router_runtime.control_blockers.ControlBlockersRuntimeTests.test_protocol_dead_end_terminal_family_suppresses_reopened_blocker",
        "replay_fixture": "run-20260527-212331.protocol_dead_end_decision_reopened_by_heartbeat",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "terminal_state_monotonicity",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "reopen_protocol_dead_end_family_on_resume",
            "report_terminal_protocol_state_as_live_work",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers same-family protocol-dead-end suppression and terminal status projection; does not prove the PM chose the right protocol-dead-end disposition semantically.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.break_glass_patch_limbo",
        "priority": "P0",
        "source_class": "break_glass_unvalidated_patch_closure",
        "historical_bad_case": "run-20260527-212331 left a break-glass incident open with a patch listed as validation not_run and no durable recovery transaction or blocked/quarantined closure path.",
        "trigger_state": "Controller uses the break-glass lane for a FlowPilot control-plane defect and records a patch or recovery transaction.",
        "expected_safe_behavior": "Break-glass closure requires normal-lane exclusion, incident/recovery linkage, validation evidence for permanent fixes, or an explicit blocked/quarantined disposition that keeps permanent_fix_needed visible.",
        "model_obligation": "flowpilot_controller_break_glass.patch_validation_before_return_to_normal",
        "model_check": "python simulations/run_flowpilot_controller_break_glass_checks.py",
        "runtime_surface": "controller_break_glass incident index + recovery transaction + patch validation/finalization",
        "runtime_test": "tests.test_flowpilot_controller_break_glass.FlowPilotControllerBreakGlassTests.test_break_glass_close_rejects_unvalidated_permanent_patch",
        "replay_fixture": "run-20260527-212331.break_glass_open_patch_validation_not_run",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "controller_break_glass_model",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "close_permanent_fix_with_not_run_validation",
            "hide_open_break_glass_incident_as_normal_standby",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers break-glass patch validation, quarantine, blocked, and recovery-link closure paths; does not authorize Controller to perform target-project work.",
        "live_ai_semantic_quality_proven": False,
    },
    {
        "friction_id": "known_friction.heartbeat_diagnostic_only_resume",
        "priority": "P0",
        "source_class": "heartbeat_resume_diagnostic_only_loop",
        "historical_bad_case": "run-20260527-212331 heartbeat wakes recorded diagnostic or launcher work but did not stay attached to current daemon/action-ledger evidence long enough to expose real Controller work or a terminal boundary.",
        "trigger_state": "Heartbeat/manual resume fires after daemon heartbeat is stale, old chat state still looks active, or wait-agent timeout is tempting to treat as liveness.",
        "expected_safe_behavior": "Heartbeat records the wake, then Controller checks current daemon process/lock/status and action ledger, attaches or restores only after that check, and never claims work-chain liveness from old route state or wait-agent timeout.",
        "model_obligation": "daemon_liveness.controller_checks_delayed_heartbeat + resume.resume_wake_recorded_to_router",
        "model_check": "python simulations/run_flowpilot_daemon_liveness_checks.py && python simulations/run_flowpilot_daemon_terminal_projection_checks.py",
        "runtime_surface": "router daemon status control_projection + heartbeat/manual resume attach/recover path",
        "runtime_test": "tests.router_runtime.resume.ResumeRuntimeTests.test_resume_reentry_attaches_to_live_router_daemon_and_ledger",
        "replay_fixture": "run-20260527-212331.heartbeat_wake_without_current_daemon_authority",
        "child_evidence_ids": [
            "historical_live_run_replay_matrix",
            "current_transcript_regression",
            "daemon_liveness_model",
        ],
        "global_gates": [
            "historical_live_run_replay",
            "current_transcript_regression",
            "background_final_artifact_contract",
            "scoped_confidence_disclosure",
        ],
        "forbidden_shortcuts": [
            "treat_wait_agent_timeout_as_live_agent",
            "start_second_router_writer_while_live_lock_exists",
        ],
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": PRIMARY_ROLE,
        "full_confidence_boundary": "Covers stale-heartbeat attach/recover authority and status projection boundaries; does not prove host scheduler delivery under all Codex desktop failures.",
        "live_ai_semantic_quality_proven": False,
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [_row_with_defect_family(row) for row in KNOWN_FRICTION_ROWS]


def _defect_family_id(friction_id: str) -> str:
    return "defect_family:" + friction_id.replace("known_friction.", "")


def _proof_evidence_id(defect_family_id: str) -> str:
    return "proof:" + defect_family_id


def _artifact_id(defect_family_id: str) -> str:
    return "artifact:" + defect_family_id


def _proof_artifact_result_paths(command: str) -> tuple[str, ...]:
    paths = [
        result_path
        for script_name, result_path in SCRIPT_RESULT_PATHS.items()
        if script_name in command
    ]
    return tuple(dict.fromkeys(paths))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _artifact_status_for_path(path: Path) -> tuple[str, tuple[str, ...]]:
    if not path.exists():
        return "not_run", ("missing_result_artifact",)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "error", ("unreadable_result_artifact",)
    if payload.get("ok") is not True:
        return "failed", ("result_artifact_not_ok",)
    return "passed", ()


def _proof_artifact_from_row(row: dict[str, Any], proof_id: str) -> ProofArtifactRef:
    command = f"{row.get('model_check')}; {row.get('runtime_test')}"
    result_paths = _proof_artifact_result_paths(str(row.get("model_check") or ""))
    fingerprints: dict[str, str] = {}
    gap_codes: list[str] = []
    status = "passed"
    for result_path in result_paths:
        absolute_path = ROOT / result_path
        path_status, path_gaps = _artifact_status_for_path(absolute_path)
        if path_status != "passed" and status == "passed":
            status = path_status
        gap_codes.extend(path_gaps)
        if absolute_path.exists():
            fingerprints[result_path] = _sha256(absolute_path)
    if not result_paths:
        status = "not_run"
        gap_codes.append("missing_result_artifact_mapping")
    if row.get("evidence_status") != "passed" and status == "passed":
        status = str(row.get("evidence_status") or "not_run")
    current = row.get("evidence_current") is True and not gap_codes
    return ProofArtifactRef(
        _artifact_id(str(row.get("defect_family_id") or "")),
        producer_route="known_friction_regression_matrix",
        command=command,
        result_path=";".join(result_paths),
        result_status=status,
        exit_code=0 if status == "passed" else 1,
        artifact_fingerprints=fingerprints,
        covered_obligation_ids=(
            str(row.get("model_obligation") or ""),
            proof_id,
            str(row.get("friction_id") or ""),
        ),
        assertion_scope="external_contract",
        current=current,
        route_evidence_current=current,
        route_gap_codes=tuple(gap_codes),
        metadata={
            "friction_id": str(row.get("friction_id") or ""),
            "result_paths": list(result_paths),
        },
    )


def _row_with_defect_family(row: dict[str, Any]) -> dict[str, Any]:
    friction_id = str(row["friction_id"])
    priority = str(row["priority"])
    defect_family_id = _defect_family_id(friction_id)
    enriched = dict(row)
    enriched.update(
        {
            "defect_family_id": defect_family_id,
            "defect_family_recurrence_count": 2,
            "defect_family_high_risk": priority == "P0",
            "defect_family_authority_boundary": str(row["runtime_surface"]),
            "defect_family_gate_required": True,
            "defect_family_promoted": True,
        }
    )
    return enriched


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
        if row.get("defect_family_gate_required") is not True:
            findings.append(
                {
                    "code": "missing_defect_family_gate_requirement",
                    "friction_id": friction_id,
                    "message": "recurring known-friction rows must require a defect-family gate",
                }
            )
        if row.get("defect_family_promoted") is not True:
            findings.append(
                {
                    "code": "defect_family_not_promoted",
                    "friction_id": friction_id,
                    "message": "recurring known-friction rows must be explicitly promoted to a defect-family gate",
                }
            )
        if int(row.get("defect_family_recurrence_count") or 0) < 2 and row.get("defect_family_high_risk") is not True:
            findings.append(
                {
                    "code": "defect_family_not_promoted_from_recurring_or_high_risk",
                    "friction_id": friction_id,
                    "message": "known-friction rows must be promoted as recurring or high-risk families",
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


def build_defect_family_gate_plan(
    rows: Sequence[dict[str, Any]] | None = None,
    *,
    require_proof_artifacts: bool = True,
    include_proof_artifacts: bool = True,
) -> DefectFamilyGatePlan:
    """Build the upgraded FlowGuard recurring defect-family gate plan."""

    rows = list(rows) if rows is not None else build_rows()
    gates: list[DefectFamilyGate] = []
    proof_evidence: list[DefectFamilyEvidence] = []
    for row in rows:
        defect_family_id = str(row.get("defect_family_id") or _defect_family_id(str(row.get("friction_id") or "")))
        observed_id = f"{defect_family_id}:observed"
        same_class_id = f"{defect_family_id}:same_class"
        holdout_id = f"{defect_family_id}:holdout"
        proof_id = _proof_evidence_id(defect_family_id)
        artifact = _proof_artifact_from_row(row, proof_id) if include_proof_artifacts else None
        proof_evidence.append(
            DefectFamilyEvidence(
                proof_id,
                result_status=str(row.get("evidence_status") or "not_run"),
                current=row.get("evidence_current") is True,
                assertion_scope="external_contract",
                producer_route="known_friction_regression_matrix",
                command=f"{row.get('model_check')}; {row.get('runtime_test')}",
                summary=str(row.get("full_confidence_boundary") or ""),
                proof_artifact=artifact,
                metadata={
                    "friction_id": str(row.get("friction_id") or ""),
                    "child_evidence_ids": list(row.get("child_evidence_ids") or ()),
                    "global_gates": list(row.get("global_gates") or ()),
                },
            )
        )
        gates.append(
            DefectFamilyGate(
                gate_id=defect_family_id,
                family_name=str(row.get("source_class") or ""),
                description=str(row.get("expected_safe_behavior") or ""),
                recurrence_count=int(row.get("defect_family_recurrence_count") or 1),
                high_risk=row.get("defect_family_high_risk") is True,
                required=row.get("defect_family_gate_required") is True,
                promoted=row.get("defect_family_promoted") is True,
                model_obligation_id=str(row.get("model_obligation") or ""),
                authority_boundary=str(row.get("defect_family_authority_boundary") or row.get("runtime_surface") or ""),
                cases=(
                    DefectFamilyCase(
                        observed_id,
                        DEFECT_CASE_ROLE_OBSERVED_FAILURE,
                        description=str(row.get("historical_bad_case") or ""),
                        source=str(row.get("replay_fixture") or ""),
                    ),
                    DefectFamilyCase(
                        same_class_id,
                        DEFECT_CASE_ROLE_SAME_CLASS_GENERALIZED,
                        description=str(row.get("expected_safe_behavior") or ""),
                        source=str(row.get("source_class") or ""),
                    ),
                    DefectFamilyCase(
                        holdout_id,
                        DEFECT_CASE_ROLE_HISTORICAL_HOLDOUT,
                        description=str(row.get("trigger_state") or ""),
                        source=str(row.get("runtime_test") or ""),
                    ),
                ),
                observed_failure_case_id=observed_id,
                same_class_generalized_case_id=same_class_id,
                historical_holdout_case_id=holdout_id,
                proof_evidence_ids=(proof_id,),
                metadata={"friction_id": str(row.get("friction_id") or "")},
            )
        )
    return DefectFamilyGatePlan(
        "flowpilot_known_friction_defect_families",
        gates=tuple(gates),
        proof_evidence=tuple(proof_evidence),
        allow_scoped_confidence=True,
        require_proof_artifacts=require_proof_artifacts,
    )


def build_defect_family_risk_ledger_plan(
    rows: Sequence[dict[str, Any]] | None = None,
    *,
    require_proof_artifacts: bool = True,
    include_proof_artifacts: bool = True,
) -> RiskEvidenceLedgerPlan:
    """Build the final confidence ledger rows that consume defect-family gates."""

    rows = list(rows) if rows is not None else build_rows()
    gate_report = review_defect_family_gates(
        build_defect_family_gate_plan(
            rows,
            require_proof_artifacts=require_proof_artifacts,
            include_proof_artifacts=include_proof_artifacts,
        )
    )
    full_ids = set(gate_report.passed_gate_ids)
    scoped_ids = set(gate_report.scoped_gate_ids)
    proof_evidence: list[RiskEvidenceProof] = []
    ledger_rows: list[RiskEvidenceRow] = []
    for row in rows:
        defect_family_id = str(row.get("defect_family_id") or _defect_family_id(str(row.get("friction_id") or "")))
        proof_id = _proof_evidence_id(defect_family_id)
        artifact = _proof_artifact_from_row(row, proof_id) if include_proof_artifacts else None
        gate_current = defect_family_id in full_ids or defect_family_id in scoped_ids
        if defect_family_id in full_ids:
            gate_confidence = RISK_CONFIDENCE_FULL
            scoped_reasons: tuple[str, ...] = ()
        elif defect_family_id in scoped_ids:
            gate_confidence = RISK_CONFIDENCE_SCOPED
            scoped_reasons = ("defect-family gate is scoped; do not claim unbounded live AI semantic quality",)
        else:
            gate_confidence = RISK_CONFIDENCE_BLOCKED
            scoped_reasons = ()
        proof_evidence.append(
            RiskEvidenceProof(
                proof_id,
                proof_kind="known_friction_regression",
                result_status=str(row.get("evidence_status") or "not_run"),
                current=row.get("evidence_current") is True,
                assertion_scope="external_contract",
                producer_route="known_friction_regression_matrix",
                command=f"{row.get('model_check')}; {row.get('runtime_test')}",
                summary=str(row.get("full_confidence_boundary") or ""),
                proof_artifact=artifact,
            )
        )
        ledger_rows.append(
            RiskEvidenceRow(
                risk_id=str(row.get("friction_id") or ""),
                description=str(row.get("historical_bad_case") or ""),
                model_obligation_id=str(row.get("model_obligation") or ""),
                proof_evidence_ids=(proof_id,),
                require_external_proof=True,
                defect_family_id=defect_family_id,
                defect_family_gate_required=True,
                defect_family_gate_current=gate_current,
                defect_family_gate_confidence=gate_confidence,
                defect_family_scoped_reasons=scoped_reasons,
                next_actions=tuple(str(item) for item in row.get("forbidden_shortcuts") or ()),
            )
        )
    return RiskEvidenceLedgerPlan(
        "flowpilot_known_friction_risk_ledger",
        rows=tuple(ledger_rows),
        proof_evidence=tuple(proof_evidence),
        require_code_contracts=False,
        allow_scoped_confidence=True,
        require_proof_artifacts=require_proof_artifacts,
    )


def build_defect_family_report(
    rows: Sequence[dict[str, Any]] | None = None,
    *,
    require_proof_artifacts: bool = True,
    include_proof_artifacts: bool = True,
) -> dict[str, Any]:
    rows = list(rows) if rows is not None else build_rows()
    gate_plan = build_defect_family_gate_plan(
        rows,
        require_proof_artifacts=require_proof_artifacts,
        include_proof_artifacts=include_proof_artifacts,
    )
    gate_report = review_defect_family_gates(gate_plan)
    ledger_plan = build_defect_family_risk_ledger_plan(
        rows,
        require_proof_artifacts=require_proof_artifacts,
        include_proof_artifacts=include_proof_artifacts,
    )
    ledger_report = review_risk_evidence_ledger(ledger_plan)
    return {
        "ok": gate_report.ok and ledger_report.ok,
        "gate_report": gate_report.to_dict(),
        "risk_ledger_report": ledger_report.to_dict(),
        "gate_plan": {
            "plan_id": gate_plan.plan_id,
            "gate_count": len(gate_plan.gates),
            "proof_evidence_count": len(gate_plan.proof_evidence),
        },
        "risk_ledger_plan": {
            "ledger_id": ledger_plan.ledger_id,
            "row_count": len(ledger_plan.rows),
            "proof_evidence_count": len(ledger_plan.proof_evidence),
        },
        "defect_family_ids": [gate.gate_id for gate in gate_plan.gates],
    }


def defect_family_known_bad_cases() -> list[dict[str, Any]]:
    row = build_rows()[0]
    missing_promotion = dict(row)
    missing_promotion["defect_family_promoted"] = False

    progress_only = dict(row)
    progress_only["evidence_status"] = "progress_only"

    stale = dict(row)
    stale["evidence_current"] = False

    internal_only_rows = [dict(row)]
    internal_gate_plan = build_defect_family_gate_plan(internal_only_rows)
    internal_evidence = tuple(
        DefectFamilyEvidence(
            evidence.evidence_id,
            result_status=evidence.result_status,
            current=evidence.current,
            assertion_scope="internal_path",
            producer_route=evidence.producer_route,
            command=evidence.command,
            summary=evidence.summary,
        )
        for evidence in internal_gate_plan.proof_evidence
    )
    internal_gate_report = review_defect_family_gates(
        DefectFamilyGatePlan(
            internal_gate_plan.plan_id,
            gates=internal_gate_plan.gates,
            proof_evidence=internal_evidence,
            allow_scoped_confidence=True,
        )
    )

    return [
        {
            "name": "missing_family_promotion",
            "report": build_defect_family_report((missing_promotion,)),
            "row_findings": validate_rows((missing_promotion,)),
            "expected_codes": [
                "defect_family_not_promoted",
                "recurring_miss_not_promoted",
            ],
        },
        {
            "name": "progress_only_defect_family_proof",
            "report": build_defect_family_report((progress_only,)),
            "row_findings": validate_rows((progress_only,)),
            "expected_codes": ["invalid_evidence_status"],
        },
        {
            "name": "stale_defect_family_proof",
            "report": build_defect_family_report((stale,)),
            "row_findings": validate_rows((stale,)),
            "expected_codes": ["stale_evidence"],
        },
        {
            "name": "internal_only_defect_family_proof",
            "report": internal_gate_report.to_dict(),
            "row_findings": [],
            "expected_codes": ["defect_family_proof_internal_path_only"],
        },
    ]


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "friction_id": "known.bad",
        "defect_family_id": "defect_family:known.bad",
        "defect_family_recurrence_count": 2,
        "defect_family_high_risk": True,
        "defect_family_authority_boundary": "role_output_runtime",
        "defect_family_gate_required": True,
        "defect_family_promoted": True,
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
    defect_family_report = build_defect_family_report(rows)
    packet_result_family_parity = build_packet_result_family_parity_report()
    if not defect_family_report["ok"]:
        findings.append(
            {
                "code": "defect_family_gate_failed",
                "message": "one or more known-friction defect-family gates failed",
                "gate_report": defect_family_report["gate_report"],
                "risk_ledger_report": defect_family_report["risk_ledger_report"],
            }
        )
    if not packet_result_family_parity["ok"]:
        findings.append(
            {
                "code": "packet_result_family_parity_failed",
                "message": "packet-result obligation-family parity is required before durable-result reconciliation can support known-friction confidence",
                "packet_result_family_parity": packet_result_family_parity,
            }
        )
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
            "Each row is also promoted to a FlowGuard defect-family gate consumed "
            "by the final risk ledger. They do not prove arbitrary live AI semantic "
            "quality or unbounded production stress."
        ),
        "required_friction_count": len(REQUIRED_FRICTION_IDS),
        "row_count": len(rows),
        "defect_family_gate_ok": defect_family_report["ok"],
        "defect_family_gate_report": defect_family_report,
        "packet_result_family_parity_ok": packet_result_family_parity["ok"],
        "packet_result_family_parity": packet_result_family_parity,
        "rows_by_priority": dict(sorted(rows_by_priority.items())),
        "required_global_gates": sorted(REQUIRED_GLOBAL_GATES),
        "observed_global_gates": observed_global_gates,
        "missing_global_gates": missing_global_gates,
        "findings": findings,
        "rows": rows,
        "known_bad_cases": known_bad_cases(),
        "defect_family_known_bad_cases": defect_family_known_bad_cases(),
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
