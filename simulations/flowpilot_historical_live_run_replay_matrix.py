"""Historical live-run replay package matrix for FlowPilot.

This matrix turns user-observed live-run failure shapes into bounded fake-AI
package rows. Each row names the real FlowPilot surfaces that must be exercised
before the row can support a confidence claim.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}
PRIMARY_ROLES = {"primary_historical_replay"}
SUPPORTING_ROLES = {"supporting_matrix", "supporting_runtime"}
REQUIRED_SURFACES = {
    "historical_snapshot",
    "host_role_lifecycle",
    "production_replay_adapter",
    "relay_receipt_mechanics",
    "parallel_stress",
    "background_proof_edges",
    "install_split_brain",
    "route_mutation_stale_evidence",
    "semantic_contract",
    "ui_display_projection",
    "windows_filesystem",
}
REQUIRED_REPLAY_IDS = {
    "historical.snapshot.stale_pending_terminal_display",
    "host.lifecycle.partial_rehydrate_thread_limit",
    "production.replay.adapter_gap_disclosed",
    "relay.receipt.done_without_runtime_mutation",
    "parallel.stress.high_parallel_peer_proof_isolation",
    "background.proof.edge_artifact_mismatch",
    "install.split_brain.stale_installed_and_loaded_prompt",
    "route.mutation.old_frontier_and_sibling_evidence",
    "semantic.contract.missing_standard_matrix_or_waiver",
    "ui.display.stale_projection_not_authority",
    "windows.fs.path_lock_and_partial_json",
}

REQUIRED_ROW_FIELDS = (
    "replay_id",
    "priority",
    "surface",
    "source_records",
    "phase_sequence",
    "entrypoints",
    "fake_ai_artifacts",
    "failure_package",
    "expected_standard_state",
    "protected_state_invariant",
    "required_evidence",
    "forbidden_shortcuts",
    "finite_package_classes",
    "evidence_test",
    "evidence_status",
    "evidence_current",
    "evidence_role",
    "live_ai_semantic_quality_proven",
    "historical_snapshot_required",
    "production_replay_adapter_required",
    "production_replay_adapter_present",
    "destructive_live_state_mutation",
    "confidence_boundary",
)

HISTORICAL_PACKAGE_CLASSES = (
    "stale_historical_snapshot",
    "partial_host_role_rehydration",
    "production_adapter_gap",
    "relay_done_without_runtime_mutation",
    "parallel_peer_proof_reuse",
    "background_exit_meta_mismatch",
    "install_source_split_brain",
    "route_mutation_stale_evidence",
    "missing_skill_standard_result_matrix",
    "stale_ui_projection",
    "windows_lock_partial_json",
)


HISTORICAL_LIVE_RUN_REPLAY_ROWS: tuple[dict[str, Any], ...] = (
    {
        "replay_id": "historical.snapshot.stale_pending_terminal_display",
        "priority": "P0",
        "surface": "historical_snapshot",
        "source_records": ["prior_live_run_control_plane_blockers", "router_state_snapshot_fixture"],
        "phase_sequence": ["snapshot_load", "current_pointer_check", "terminal_display_check", "standard_state_gate"],
        "entrypoints": ["run_snapshot_loader", "real_router_runtime", "current.json", "terminal_ledger"],
        "fake_ai_artifacts": ["stale_pending_action", "terminal_display_projection"],
        "failure_package": "historical snapshot shows terminal-looking display while Router still owns a pending action",
        "expected_standard_state": "display is treated as projection only and Router state remains authoritative",
        "protected_state_invariant": "historical snapshot replay cannot mark completion unless current run state and terminal ledger agree",
        "required_evidence": [
            "snapshot_run_id_loaded",
            "current_pointer_matches_snapshot_or_rejected",
            "pending_action_not_counted_as_terminal",
            "terminal_ledger_authority_checked",
        ],
        "forbidden_shortcuts": ["trust_chat_display_as_router_state", "skip_current_pointer_check"],
        "finite_package_classes": ["stale_historical_snapshot"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": True,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves stale snapshot authority handling, not every archived schema variant",
    },
    {
        "replay_id": "host.lifecycle.partial_rehydrate_thread_limit",
        "priority": "P0",
        "surface": "host_role_lifecycle",
        "source_records": ["resume_reentry", "role_binding_recovery_report", "role_io_protocol_ledger"],
        "phase_sequence": ["resume_wake", "load_resume_state", "rehydrate_role_bindings", "normal_work_gate"],
        "entrypoints": ["real_router_runtime", "load_resume_state", "rehydrate_role_bindings", "role_io_protocol"],
        "fake_ai_artifacts": ["partial_rehydration_receipt", "stale_memory_packet", "timeout_unknown_liveness"],
        "failure_package": "resume continues after only some roles report liveness or after unknown liveness is treated as active",
        "expected_standard_state": "normal work stays blocked until all runtime role records and resume memory evidence pass",
        "protected_state_invariant": "resume cannot resume work from partial host-role lifecycle evidence",
        "required_evidence": [
            "load_resume_state_evidence_written",
            "all_runtime_roles_checked",
            "missing_role_rejected",
            "timeout_unknown_not_active",
        ],
        "forbidden_shortcuts": ["continue_with_partial_runtime_roles", "treat_timeout_unknown_as_active"],
        "finite_package_classes": ["partial_host_role_rehydration"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_host_role_lifecycle_resume_requires_full_rehydrate_evidence"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves mechanical host-role rehydration gates, not host scheduler delivery guarantees",
    },
    {
        "replay_id": "production.replay.adapter_gap_disclosed",
        "priority": "P0",
        "surface": "production_replay_adapter",
        "source_records": ["adapter_contract", "fixture_snapshot_manifest"],
        "phase_sequence": ["fixture_snapshot", "adapter_boundary_check", "claim_boundary"],
        "entrypoints": ["production_replay_adapter_manifest", "real_router_runtime", "package_confidence_gate"],
        "fake_ai_artifacts": ["fixture_without_live_adapter"],
        "failure_package": "fixture replay is incorrectly claimed to prove production replay coverage",
        "expected_standard_state": "row passes only when adapter absence is disclosed and no production-live overclaim is made",
        "protected_state_invariant": "fixture-only replay cannot be counted as production adapter conformance",
        "required_evidence": [
            "adapter_presence_field_recorded",
            "adapter_gap_disclosed",
            "fixture_scope_disclosed",
            "production_live_claim_absent",
        ],
        "forbidden_shortcuts": ["claim_fixture_is_production_replay", "omit_adapter_presence"],
        "finite_package_classes": ["production_adapter_gap"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_relay_lifecycle_and_semantic_contract_packages_block_overclaims"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": True,
        "production_replay_adapter_required": True,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "explicitly records adapter gap; does not prove production replay adapter parity",
    },
    {
        "replay_id": "relay.receipt.done_without_runtime_mutation",
        "priority": "P0",
        "surface": "relay_receipt_mechanics",
        "source_records": ["packet_ledger", "controller_action_ledger", "runtime_receipt"],
        "phase_sequence": ["issue_packet", "controller_relay", "done_receipt", "runtime_state_audit"],
        "entrypoints": ["packet_runtime", "deliver_envelope_metadata", "controller_receipt", "packet_ledger"],
        "fake_ai_artifacts": ["done_receipt_without_relay_mutation", "packet_envelope_only"],
        "failure_package": "Controller marks relay done while packet ledger or runtime envelope was not mutated",
        "expected_standard_state": "completion remains blocked until runtime relay evidence and Router ledger agree",
        "protected_state_invariant": "done receipt cannot replace packet/runtime state mutation evidence",
        "required_evidence": [
            "controller_relay_signature_recorded",
            "packet_ledger_status_mutated",
            "receipt_hash_current",
            "done_without_mutation_rejected",
        ],
        "forbidden_shortcuts": ["trust_done_receipt_without_ledger", "controller_reads_body_to_infer_success"],
        "finite_package_classes": ["relay_done_without_runtime_mutation"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_relay_lifecycle_and_semantic_contract_packages_block_overclaims"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves mechanical relay evidence agreement for selected packet paths",
    },
    {
        "replay_id": "parallel.stress.high_parallel_peer_proof_isolation",
        "priority": "P1",
        "surface": "parallel_stress",
        "source_records": ["peer_background_artifacts", "current_run_pointer"],
        "phase_sequence": ["parallel_runs", "peer_proof_write", "current_run_check", "proof_scope_check"],
        "entrypoints": ["current.json", "background_artifact_classifier", "router_daemon.lock"],
        "fake_ai_artifacts": ["peer_run_proof", "current_run_replay_package"],
        "failure_package": "peer run proof is reused as current run evidence during parallel package execution",
        "expected_standard_state": "peer proof remains scoped to peer run and current run authority is unchanged",
        "protected_state_invariant": "parallel peer evidence cannot overwrite current-run authority",
        "required_evidence": [
            "peer_run_id_in_proof",
            "current_run_id_compared",
            "peer_proof_not_current",
            "current_pointer_unchanged",
        ],
        "forbidden_shortcuts": ["reuse_peer_proof_for_current_run", "rewrite_current_pointer_to_peer"],
        "finite_package_classes": ["parallel_peer_proof_reuse"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "bounded peer proof isolation, not an unbounded load test",
    },
    {
        "replay_id": "background.proof.edge_artifact_mismatch",
        "priority": "P1",
        "surface": "background_proof_edges",
        "source_records": ["background_out", "background_err", "background_exit", "background_meta"],
        "phase_sequence": ["background_run", "progress_log", "exit_meta_race", "proof_gate"],
        "entrypoints": ["background_artifact_classifier", "tmp/flowguard_background"],
        "fake_ai_artifacts": ["progress_only_log", "exit_meta_mismatch"],
        "failure_package": "background progress or mismatched exit/meta artifact is counted as final proof",
        "expected_standard_state": "progress-only and stale meta evidence is rejected before pass claims",
        "protected_state_invariant": "only final current artifacts count as completion evidence",
        "required_evidence": [
            "progress_only_status_rejected",
            "missing_exit_detected",
            "exit_meta_mismatch_classified",
            "current_run_binding_checked",
        ],
        "forbidden_shortcuts": ["count_progress_line_as_pass", "ignore_exit_meta_mismatch"],
        "finite_package_classes": ["background_exit_meta_mismatch"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves artifact classification, not remote runner durability",
    },
    {
        "replay_id": "install.split_brain.stale_installed_and_loaded_prompt",
        "priority": "P1",
        "surface": "install_split_brain",
        "source_records": ["repo_skill_digest", "installed_skill_digest", "loaded_prompt_manifest"],
        "phase_sequence": ["repo_change", "installed_skill_check", "prompt_manifest_check", "install_sync_gate"],
        "entrypoints": ["install_flowpilot.py", "audit_local_install_sync.py", "installed_flowpilot_skill"],
        "fake_ai_artifacts": ["stale_installed_skill", "loaded_old_prompt_manifest"],
        "failure_package": "installed skill or loaded prompt differs from repository source after tests pass",
        "expected_standard_state": "install split-brain is detected before local sync claim",
        "protected_state_invariant": "repository tests cannot imply installed skill freshness",
        "required_evidence": [
            "repo_digest_recorded",
            "installed_digest_recorded",
            "digest_mismatch_detected",
            "install_sync_required",
        ],
        "forbidden_shortcuts": ["skip_install_audit_after_source_change", "assume_repo_test_means_installed_fresh"],
        "finite_package_classes": ["install_source_split_brain"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_install_split_brain_and_ui_projection_packages_do_not_count_as_authority"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves local digest mismatch detection, not full external install deployment",
    },
    {
        "replay_id": "route.mutation.old_frontier_and_sibling_evidence",
        "priority": "P1",
        "surface": "route_mutation_stale_evidence",
        "source_records": ["execution_frontier", "route_version", "node_completion_ledger"],
        "phase_sequence": ["route_mutation", "old_frontier_replay", "sibling_evidence_check", "same_scope_gate"],
        "entrypoints": ["execution_frontier.json", "route_artifacts", "node_completion_ledger"],
        "fake_ai_artifacts": ["old_frontier_current_node_packet", "stale_sibling_completion_proof"],
        "failure_package": "old route frontier or sibling proof is reused after route mutation",
        "expected_standard_state": "old evidence is stale unless replay scope and same-scope ledger are current",
        "protected_state_invariant": "route mutation stales old current-node and sibling evidence",
        "required_evidence": [
            "route_version_compared",
            "frontier_version_compared",
            "sibling_evidence_scope_checked",
            "stale_evidence_blocked",
        ],
        "forbidden_shortcuts": ["reuse_old_frontier_packet", "skip_same_scope_replay"],
        "finite_package_classes": ["route_mutation_stale_evidence"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_install_split_brain_and_ui_projection_packages_do_not_count_as_authority"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "package-level route evidence scope check; full route mutation tests remain separate",
    },
    {
        "replay_id": "semantic.contract.missing_standard_matrix_or_waiver",
        "priority": "P2",
        "surface": "semantic_contract",
        "source_records": ["skill_standard_contract", "worker_result", "reviewer_gate"],
        "phase_sequence": ["work_packet", "fake_worker_result", "skill_standard_matrix_check", "review_gate"],
        "entrypoints": ["packet_runtime", "role_output_runtime", "skill_standard_result_matrix"],
        "fake_ai_artifacts": ["result_without_skill_standard_matrix", "unapproved_waiver"],
        "failure_package": "AI result claims completion without inherited standard rows or approved waiver",
        "expected_standard_state": "semantic completion remains blocked and package is routed to repair/review",
        "protected_state_invariant": "mechanical result success cannot replace Skill Standard Result Matrix evidence",
        "required_evidence": [
            "inherited_standard_ids_declared",
            "result_matrix_present_or_waiver_approved",
            "missing_matrix_rejected",
        ],
        "forbidden_shortcuts": ["treat_contract_self_check_as_standard_matrix", "accept_unapproved_waiver"],
        "finite_package_classes": ["missing_skill_standard_result_matrix"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_relay_lifecycle_and_semantic_contract_packages_block_overclaims"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves standard-result-matrix gating for named packages, not answer truth",
    },
    {
        "replay_id": "ui.display.stale_projection_not_authority",
        "priority": "P2",
        "surface": "ui_display_projection",
        "source_records": ["display_plan_projection", "router_state", "controller_status"],
        "phase_sequence": ["display_projection_load", "router_state_check", "authority_gate"],
        "entrypoints": ["display_plan_projection", "state", "controller_status"],
        "fake_ai_artifacts": ["stale_visible_plan", "chat_status_claim"],
        "failure_package": "display projection says complete while Router state still waits for evidence",
        "expected_standard_state": "display is non-authoritative and Router state remains the source of truth",
        "protected_state_invariant": "visible projection cannot close Router-controlled waits",
        "required_evidence": [
            "display_projection_version_compared",
            "router_state_authority_checked",
            "stale_projection_rejected",
        ],
        "forbidden_shortcuts": ["trust_visible_projection_as_completion", "skip_router_state_authority"],
        "finite_package_classes": ["stale_ui_projection"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_install_split_brain_and_ui_projection_packages_do_not_count_as_authority"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves projection authority boundary for package rows, not all UI rendering states",
    },
    {
        "replay_id": "windows.fs.path_lock_and_partial_json",
        "priority": "P2",
        "surface": "windows_filesystem",
        "source_records": ["runtime_write_lock", "partial_json_candidate", "path_normalization_case"],
        "phase_sequence": ["write_lock_probe", "partial_json_probe", "path_case_probe", "recovery_gate"],
        "entrypoints": ["router_json_write_lock", "read_json", "project_relative"],
        "fake_ai_artifacts": ["held_windows_lock", "partial_json_write", "mixed_separator_path"],
        "failure_package": "Windows path lock or partial JSON residue is treated as valid runtime state",
        "expected_standard_state": "runtime classifies residue as recoverable mechanical state and does not advance",
        "protected_state_invariant": "partial or locked filesystem writes cannot become authoritative Router state",
        "required_evidence": [
            "write_lock_path_detected",
            "partial_json_rejected",
            "path_scope_preserved",
            "recovery_state_recorded",
        ],
        "forbidden_shortcuts": ["ignore_write_lock", "parse_partial_json_as_state", "accept_out_of_root_path"],
        "finite_package_classes": ["windows_lock_partial_json"],
        "evidence_test": (
            "FlowPilotHistoricalLiveRunReplayTests."
            "test_windows_filesystem_package_uses_lock_and_partial_json_as_recoverable_mechanical_state"
        ),
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": False,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "proves bounded filesystem residue classification, not every OS-level file race",
    },
)


def build_rows() -> list[dict[str, Any]]:
    return [dict(row) for row in HISTORICAL_LIVE_RUN_REPLAY_ROWS]


def validate_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    present_ids = {str(row.get("replay_id") or "") for row in rows}
    for replay_id in sorted(REQUIRED_REPLAY_IDS - present_ids):
        findings.append(
            {
                "code": "missing_required_replay",
                "replay_id": replay_id,
                "message": "required historical live-run replay row is missing",
            }
        )

    present_surfaces = {str(row.get("surface") or "") for row in rows}
    for surface in sorted(REQUIRED_SURFACES - present_surfaces):
        findings.append(
            {
                "code": "missing_required_surface",
                "surface": surface,
                "message": "required historical replay surface is missing",
            }
        )

    for row in rows:
        replay_id = str(row.get("replay_id") or "")
        for field in REQUIRED_ROW_FIELDS:
            if field not in row:
                findings.append(
                    {
                        "code": "missing_required_field",
                        "replay_id": replay_id,
                        "field": field,
                        "message": "historical replay rows must carry the full evidence contract",
                    }
                )
                continue
            value = row[field]
            if isinstance(value, (str, list, tuple, dict, set)) and not value:
                findings.append(
                    {
                        "code": "empty_required_field",
                        "replay_id": replay_id,
                        "field": field,
                        "message": "historical replay row field cannot be empty",
                    }
                )

        if replay_id:
            if replay_id in seen_ids:
                findings.append(
                    {
                        "code": "duplicate_replay_id",
                        "replay_id": replay_id,
                        "message": "historical replay ids must be unique",
                    }
                )
            seen_ids.add(replay_id)

        if str(row.get("surface") or "") not in REQUIRED_SURFACES:
            findings.append(
                {
                    "code": "unknown_surface",
                    "replay_id": replay_id,
                    "surface": str(row.get("surface") or ""),
                    "message": "row surface must be one of the required historical replay surfaces",
                }
            )
        if str(row.get("priority") or "") not in {"P0", "P1", "P2"}:
            findings.append(
                {
                    "code": "invalid_priority",
                    "replay_id": replay_id,
                    "message": "priority must be P0, P1, or P2",
                }
            )
        if str(row.get("evidence_status") or "") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_evidence_status",
                    "replay_id": replay_id,
                    "message": "primary historical replay evidence must be passed",
                }
            )
        if row.get("evidence_current") is not True:
            findings.append(
                {
                    "code": "stale_evidence",
                    "replay_id": replay_id,
                    "message": "historical replay evidence must be current",
                }
            )
        if str(row.get("evidence_role") or "") not in PRIMARY_ROLES | SUPPORTING_ROLES:
            findings.append(
                {
                    "code": "invalid_evidence_role",
                    "replay_id": replay_id,
                    "message": "evidence role must classify primary or supporting historical replay coverage",
                }
            )
        if row.get("destructive_live_state_mutation") is not False:
            findings.append(
                {
                    "code": "live_state_mutation_overclaim",
                    "replay_id": replay_id,
                    "message": "historical replay packages must stay in isolated fixtures and cannot mutate live user state",
                }
            )
        if row.get("live_ai_semantic_quality_proven") is not False:
            findings.append(
                {
                    "code": "live_ai_semantic_overclaim",
                    "replay_id": replay_id,
                    "message": "fake AI packages prove protocol flow, not live model answer quality",
                }
            )

        package_classes = set(row.get("finite_package_classes") or [])
        if not package_classes <= set(HISTORICAL_PACKAGE_CLASSES):
            findings.append(
                {
                    "code": "unknown_package_class",
                    "replay_id": replay_id,
                    "message": "finite package classes must be drawn from the historical package class list",
                }
            )
        if not package_classes:
            findings.append(
                {
                    "code": "missing_package_class",
                    "replay_id": replay_id,
                    "message": "row must declare at least one finite package class",
                }
            )

        if row.get("surface") == "historical_snapshot" and row.get("historical_snapshot_required") is not True:
            findings.append(
                {
                    "code": "missing_historical_snapshot_requirement",
                    "replay_id": replay_id,
                    "message": "historical snapshot rows must require an explicit historical snapshot",
                }
            )
        if row.get("priority") == "P0" and row.get("surface") in {
            "historical_snapshot",
            "production_replay_adapter",
        }:
            if row.get("historical_snapshot_required") is not True:
                findings.append(
                    {
                        "code": "p0_missing_historical_snapshot",
                        "replay_id": replay_id,
                        "message": "P0 snapshot/adapter rows must require a historical snapshot source",
                    }
                )

        if row.get("production_replay_adapter_required") is True:
            if not row.get("confidence_boundary"):
                findings.append(
                    {
                        "code": "production_adapter_boundary_missing",
                        "replay_id": replay_id,
                        "message": "production adapter rows must disclose adapter coverage boundary",
                    }
                )
            if row.get("production_replay_adapter_present") is not True:
                boundary = str(row.get("confidence_boundary") or "").lower()
                if "adapter gap" not in boundary and "does not prove production replay adapter" not in boundary:
                    findings.append(
                        {
                            "code": "production_adapter_overclaim",
                            "replay_id": replay_id,
                            "message": "missing production replay adapter must be explicitly disclosed",
                        }
                    )

        entrypoints = {str(item) for item in row.get("entrypoints", [])}
        if row.get("surface") in {"relay_receipt_mechanics", "semantic_contract"}:
            if not ({"packet_runtime", "role_output_runtime"} & entrypoints):
                findings.append(
                    {
                        "code": "missing_runtime_entrypoint",
                        "replay_id": replay_id,
                        "message": "relay and semantic rows must bind to packet or role-output runtime entrypoints",
                    }
                )
        if row.get("surface") == "host_role_lifecycle" and "rehydrate_role_bindings" not in entrypoints:
            findings.append(
                {
                    "code": "missing_rehydrate_entrypoint",
                    "replay_id": replay_id,
                    "message": "host lifecycle rows must bind to the rehydrate_role_bindings action",
                }
            )
        if row.get("surface") == "background_proof_edges" and "background_artifact_classifier" not in entrypoints:
            findings.append(
                {
                    "code": "missing_background_classifier_entrypoint",
                    "replay_id": replay_id,
                    "message": "background proof rows must use the background artifact classifier",
                }
            )

        forbidden = {str(item) for item in row.get("forbidden_shortcuts", [])}
        if row.get("surface") == "relay_receipt_mechanics" and "trust_done_receipt_without_ledger" not in forbidden:
            findings.append(
                {
                    "code": "relay_done_shortcut_not_forbidden",
                    "replay_id": replay_id,
                    "message": "relay rows must forbid trusting done receipts without runtime ledger evidence",
                }
            )
        if row.get("surface") == "semantic_contract" and "treat_contract_self_check_as_standard_matrix" not in forbidden:
            findings.append(
                {
                    "code": "semantic_shortcut_not_forbidden",
                    "replay_id": replay_id,
                    "message": "semantic rows must forbid treating contract self-check as skill standard evidence",
                }
            )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "replay_id": "known.bad",
        "priority": "P0",
        "surface": "historical_snapshot",
        "source_records": ["known_bad_source"],
        "phase_sequence": ["load"],
        "entrypoints": ["run_snapshot_loader", "real_router_runtime"],
        "fake_ai_artifacts": ["known_bad_package"],
        "failure_package": "known bad fixture",
        "expected_standard_state": "blocked_until_repair",
        "protected_state_invariant": "bad input cannot mutate protected state",
        "required_evidence": ["test_evidence"],
        "forbidden_shortcuts": ["trust_chat_display_as_router_state"],
        "finite_package_classes": ["stale_historical_snapshot"],
        "evidence_test": "KnownBad.test_case",
        "evidence_status": "passed",
        "evidence_current": True,
        "evidence_role": "primary_historical_replay",
        "live_ai_semantic_quality_proven": False,
        "historical_snapshot_required": True,
        "production_replay_adapter_required": False,
        "production_replay_adapter_present": False,
        "destructive_live_state_mutation": False,
        "confidence_boundary": "known bad fixture only",
    }
    return [
        {
            "name": "missing_required_surface",
            "rows": [{**base, "replay_id": "historical.snapshot.stale_pending_terminal_display"}],
            "expected_codes": ["missing_required_replay", "missing_required_surface"],
        },
        {
            "name": "stale_evidence",
            "rows": [{**base, "evidence_current": False}],
            "expected_codes": ["stale_evidence", "missing_required_replay"],
        },
        {
            "name": "missing_historical_snapshot_for_p0",
            "rows": [{**base, "historical_snapshot_required": False}],
            "expected_codes": [
                "missing_historical_snapshot_requirement",
                "p0_missing_historical_snapshot",
                "missing_required_replay",
            ],
        },
        {
            "name": "production_adapter_overclaim_without_adapter",
            "rows": [
                {
                    **base,
                    "surface": "production_replay_adapter",
                    "production_replay_adapter_required": True,
                    "production_replay_adapter_present": False,
                    "confidence_boundary": "claims full production replay parity",
                }
            ],
            "expected_codes": ["production_adapter_overclaim", "missing_required_replay"],
        },
        {
            "name": "relay_done_without_runtime_mutation",
            "rows": [
                {
                    **base,
                    "surface": "relay_receipt_mechanics",
                    "entrypoints": ["controller_receipt"],
                    "forbidden_shortcuts": ["controller_reads_body_to_infer_success"],
                    "finite_package_classes": ["relay_done_without_runtime_mutation"],
                }
            ],
            "expected_codes": [
                "missing_runtime_entrypoint",
                "relay_done_shortcut_not_forbidden",
                "missing_required_replay",
            ],
        },
        {
            "name": "live_ai_semantic_overclaim",
            "rows": [{**base, "live_ai_semantic_quality_proven": True}],
            "expected_codes": ["live_ai_semantic_overclaim", "missing_required_replay"],
        },
        {
            "name": "destructive_live_state_mutation",
            "rows": [{**base, "destructive_live_state_mutation": True}],
            "expected_codes": ["live_state_mutation_overclaim", "missing_required_replay"],
        },
        {
            "name": "progress_only_background_evidence",
            "rows": [
                {
                    **base,
                    "surface": "background_proof_edges",
                    "entrypoints": ["tmp/flowguard_background"],
                    "evidence_status": "progress_only",
                    "finite_package_classes": ["background_exit_meta_mismatch"],
                }
            ],
            "expected_codes": [
                "invalid_evidence_status",
                "missing_background_classifier_entrypoint",
                "missing_required_replay",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    rows = build_rows()
    findings = validate_rows(rows)
    rows_by_surface = Counter(str(row["surface"]) for row in rows)
    rows_by_priority = Counter(str(row["priority"]) for row in rows)
    return {
        "ok": not findings,
        "result_type": "flowpilot_historical_live_run_replay_matrix",
        "coverage_boundary": (
            "Rows prove bounded historical live-run replay package behavior through fake AI artifacts "
            "and real FlowPilot control surfaces: Router state, packet and role-output runtime, resume, "
            "background proof classification, install freshness, route evidence scope, display projection "
            "authority, and filesystem residue handling. They do not prove arbitrary live AI semantic "
            "quality, every possible production adapter trace, or unbounded parallel stress."
        ),
        "required_surface_count": len(REQUIRED_SURFACES),
        "required_replay_count": len(REQUIRED_REPLAY_IDS),
        "row_count": len(rows),
        "rows_by_surface": dict(sorted(rows_by_surface.items())),
        "rows_by_priority": dict(sorted(rows_by_priority.items())),
        "historical_package_classes": list(HISTORICAL_PACKAGE_CLASSES),
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
