"""Synthetic-agent coverage matrix for current FlowPilot AI/action branches."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulations"))

from flowpilot_model_test_alignment_diagnostics import (  # noqa: E402
    build_full_model_test_code_diagnostic,
)
from flowpilot_model_test_alignment_family_plans import (  # noqa: E402
    build_alignment_plan_entries,
)


PASS_STATUSES = {"passed"}
BACKGROUND_INCOMPLETE_STATUSES = {"progress_only", "running", "missing", "stale", "failed"}
SYNTHETIC_NON_LIVE_KINDS = {"synthetic_trace", "fixture_trace"}
REPLAY_REQUIRED_RISK_TIERS = {"P0", "P1"}
SYSTEM_TERMINAL_EXPECTATIONS = {"blocked", "continue_allowed", "completion_rejected"}
REQUIRED_ROW_FIELDS = (
    "family",
    "model_id",
    "obligation_id",
    "branch_kind",
    "coverage_kind",
    "evidence_owner",
    "evidence_id",
    "evidence_status",
    "evidence_current",
    "live_completion_allowed",
    "coverage_boundary",
    "risk_tier",
    "synthetic_replay_required",
    "synthetic_replay_status",
    "covered_failure_mode",
    "story_level",
)

ALIGNMENT_ROW_DEFAULTS = {
    "risk_tier": "ordinary",
    "synthetic_replay_required": False,
    "synthetic_replay_status": "not_required",
    "non_replayable_reason": "",
    "covered_failure_mode": "ordinary_model_test_alignment",
    "story_level": "local",
    "recovery_loop": "",
    "story_steps": [],
    "terminal_expectation": "",
}

EXPLICIT_TRACE_ROW_DEFAULTS = {
    "risk_tier": "P2",
    "synthetic_replay_required": False,
    "synthetic_replay_status": "present",
    "non_replayable_reason": "",
    "covered_failure_mode": "baseline_synthetic_trace_contract",
    "story_level": "local",
    "recovery_loop": "",
    "story_steps": [],
    "terminal_expectation": "",
}


SYNTHETIC_TRACE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "family": "packet/card/ack",
        "model_id": "packet_card_ack",
        "obligation_id": "packet.physical_body_boundary",
        "branch_kind": "happy_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.packet.happy.worker_result",
        "test_name": "test_happy_path_worker_trace_reaches_pm_disposition",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
    },
    {
        "family": "packet/card/ack",
        "model_id": "packet_card_ack",
        "obligation_id": "ack.return_wait_preconsumption",
        "branch_kind": "failure_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.packet.failure.ack_only_not_completion",
        "test_name": "test_ack_only_trace_keeps_semantic_work_open",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "ack_return_does_not_complete_semantic_work",
    },
    {
        "family": "packet/card/ack",
        "model_id": "packet_card_ack",
        "obligation_id": "packet.physical_body_boundary",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.packet.negative.sealed_body_identity_hash",
        "test_name": "test_trace_rejects_sealed_body_wrong_identity_and_stale_hash",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "sealed_body_wrong_identity_or_stale_hash_rejected",
    },
    {
        "family": "router loop/daemon",
        "model_id": "router_loop_daemon",
        "obligation_id": "router_loop.packet_result_review_loop",
        "branch_kind": "failure_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.router.failure.raw_result_reviewer_blocked",
        "test_name": "test_raw_worker_result_cannot_skip_pm_disposition_to_reviewer_pass",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "raw_worker_result_cannot_skip_pm_disposition",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "terminal_closure_resume",
        "obligation_id": "terminal.final_ledger_and_backward_replay",
        "branch_kind": "negative_path",
        "coverage_kind": "fixture_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.evidence_boundary.fixture_not_live_completion",
        "test_name": "test_fixture_evidence_is_disclosed_but_not_live_completion_evidence",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "non_live_evidence_disclosure_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "fixture_trace_cannot_support_live_completion_claim",
    },
    {
        "family": "test tiering/slow-test contracts",
        "model_id": "test_tiering_slow_contracts",
        "obligation_id": "test_tiering.background_artifact_contract",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_trace_replay",
        "evidence_id": "synthetic.background.negative.progress_only_not_pass",
        "test_name": "test_background_progress_only_trace_is_not_pass_evidence",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "background_final_artifact_contract",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "background_progress_without_exit_is_not_pass_evidence",
    },
    {
        "family": "control blockers",
        "model_id": "control_blocker_repair",
        "obligation_id": "control_blocker.retry_budget_escalates_to_pm",
        "branch_kind": "failure_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.control_blocker.failure.retry_budget_pm_escalation",
        "test_name": "test_control_blocker_reissue_retry_budget_escalates_to_pm_fake_reviewer_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "same_role_reissue_budget_exhaustion_routes_to_pm",
    },
    {
        "family": "control blockers",
        "model_id": "control_blocker_repair",
        "obligation_id": "control_blocker.pm_repair_decision",
        "branch_kind": "happy_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.control_blocker.happy.pm_repair_target_accepted",
        "test_name": "test_pm_repair_decision_accepts_registered_target_fake_pm_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "pm_repair_accepts_registered_receivable_return_gate",
    },
    {
        "family": "control blockers",
        "model_id": "control_blocker_repair",
        "obligation_id": "control_blocker.pm_repair_decision",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.control_blocker.negative.invalid_pm_repair_target",
        "test_name": "test_pm_repair_decision_rejects_invalid_targets_fake_pm_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "pm_repair_rejects_unregistered_or_not_receivable_targets",
    },
    {
        "family": "control blockers",
        "model_id": "control_blocker_repair",
        "obligation_id": "control_blocker.fatal_protocol_violation",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.control_blocker.negative.fatal_ordinary_waiver_rejected",
        "test_name": "test_fatal_control_blocker_rejects_pm_ordinary_waiver_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "fatal_protocol_blocker_cannot_be_ordinary_waived",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "terminal_closure_resume",
        "obligation_id": "resume.current_run_reentry",
        "branch_kind": "failure_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.resume.failure.active_blocker_or_ambiguous_state",
        "test_name": "test_resume_active_blocker_and_ambiguous_state_preempt_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "resume_preempts_normal_work_for_blocker_or_ambiguity",
    },
    {
        "family": "route mutation",
        "model_id": "route_mutation",
        "obligation_id": "route_mutation.sibling_replacement_stales_old_evidence",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.route_mutation.negative.stale_sibling_proof",
        "test_name": "test_route_mutation_stale_sibling_proof_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "sibling_replacement_requires_affected_siblings_and_stales_old_proof",
    },
    {
        "family": "role/output contracts",
        "model_id": "role_output_contracts",
        "obligation_id": "role_output.registry_authority",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.role_output.negative.pm_disposition_authority",
        "test_name": "test_pm_package_disposition_envelope_authority_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "pm_package_disposition_requires_pm_role_envelope",
    },
    {
        "family": "foreground controller",
        "model_id": "foreground_controller_boundary",
        "obligation_id": "controller_boundary.repair_budget_escalation",
        "branch_kind": "failure_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.controller.failure.boundary_repair_budget_escalation",
        "test_name": "test_controller_boundary_repair_budget_escalates_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "controller_receipts_without_deliverable_escalate_after_retry_budget",
    },
    {
        "family": "material modeling",
        "model_id": "material_modeling",
        "obligation_id": "material_repair.active_generation_overrides_stale_flags",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.material.negative.active_generation_blocks_stale_flags",
        "test_name": "test_material_repair_generation_blocks_stale_flags_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "active_repair_generation_ignores_stale_global_progress_flags",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "terminal_closure_resume",
        "obligation_id": "closure.dirty_ledgers_block_completion",
        "branch_kind": "negative_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "synthetic_agent_exception_trace_replay",
        "evidence_id": "synthetic.terminal.negative.dirty_pm_suggestion_ledger",
        "test_name": "test_dirty_terminal_ledgers_block_completion_fake_package",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "dirty_pm_suggestion_ledger_blocks_final_completion",
    },
    {
        "family": "control blockers",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.valid_envelope_bad_content_rejected",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.valid_envelope_bad_content.pm_repair_self_check",
        "test_name": "test_system_story_valid_repair_envelope_bad_content_is_rejected",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "valid_role_envelope_with_bad_repair_content_is_rejected",
        "story_level": "system",
        "recovery_loop": "pm_repair_content_rejection",
        "story_steps": ["control_blocker", "pm_repair_envelope", "bad_content_rejected"],
        "terminal_expectation": "blocked",
    },
    {
        "family": "control blockers",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.stacked_blockers_preempt_dirty_ledger",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.stacked_blockers.control_preempts_dirty_ledger",
        "test_name": "test_system_story_stacked_blockers_preempt_and_preserve_dirty_ledger",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "active_control_blocker_preempts_and_preserves_dirty_ledger",
        "story_level": "system",
        "recovery_loop": "control_blocker_preemption",
        "story_steps": ["active_control_blocker", "dirty_pm_suggestion_ledger", "handle_control_blocker"],
        "terminal_expectation": "blocked",
    },
    {
        "family": "material modeling",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.failed_pm_repair_loop_escalates",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.pm_repair_loop.followup_blocker",
        "test_name": "test_system_story_failed_pm_repair_loop_registers_followup_blocker",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "pm_repair_attempt_that_still_blocks_registers_followup_blocker",
        "story_level": "system",
        "recovery_loop": "pm_repair_escalation",
        "story_steps": ["pm_repair_decision", "repair_transaction", "recheck_blocked", "followup_blocker"],
        "terminal_expectation": "blocked",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.stale_state_cannot_clear_active_blocker",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.restart.stale_state_preserves_active_blocker",
        "test_name": "test_system_story_stale_run_state_save_cannot_clear_active_blocker",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P0",
        "synthetic_replay_required": True,
        "covered_failure_mode": "stale_state_save_cannot_clear_current_control_blocker",
        "story_level": "system",
        "recovery_loop": "stale_state_quarantine",
        "story_steps": ["stale_state_loaded", "foreground_blocker_written", "stale_save_attempt", "blocker_preserved"],
        "terminal_expectation": "blocked",
    },
    {
        "family": "router loop/daemon",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.parallel_peer_authority_isolated",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.parallel.peer_run_stop_isolated",
        "test_name": "test_system_story_parallel_run_stop_does_not_touch_peer_authority",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "peer_run_daemon_stop_does_not_overwrite_current_run_authority",
        "story_level": "system",
        "recovery_loop": "parallel_run_isolation",
        "story_steps": ["two_active_locks", "stop_one_run", "peer_lock_preserved"],
        "terminal_expectation": "continue_allowed",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "systemic_synthetic_agent_replay",
        "obligation_id": "systemic.terminal_total_gate_rejects_dirty_sources",
        "branch_kind": "system_recovery_path",
        "coverage_kind": "synthetic_trace",
        "evidence_owner": "systemic_synthetic_agent_replay",
        "evidence_id": "systemic.terminal.total_gate_dirty_sources",
        "test_name": "test_system_story_terminal_total_gate_rejects_multiple_dirty_sources",
        "path": "tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "command": "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "control_flow_only",
        "risk_tier": "P1",
        "synthetic_replay_required": True,
        "covered_failure_mode": "terminal_closure_rejects_multiple_dirty_sources",
        "story_level": "system",
        "recovery_loop": "terminal_total_gate",
        "story_steps": ["final_replay_ready", "dirty_pm_suggestion", "dirty_self_interrogation", "dirty_defect", "closure_rejected"],
        "terminal_expectation": "completion_rejected",
    },
    {
        "family": "route mutation",
        "model_id": "route_mutation",
        "obligation_id": "route_mutation.sibling_replacement_stales_old_evidence",
        "branch_kind": "negative_path",
        "coverage_kind": "ordinary_runtime",
        "evidence_owner": "router_runtime_route_mutation",
        "evidence_id": "runtime.route_mutation.negative.old_sibling_proof",
        "test_name": "test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof",
        "path": "tests/router_runtime/route_mutation_sibling_replacement.py",
        "command": "python -m unittest tests.test_flowpilot_router_runtime_route_mutation",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "ordinary_runtime_contract",
        "risk_tier": "ordinary",
        "synthetic_replay_required": False,
        "synthetic_replay_status": "not_required",
        "covered_failure_mode": "ordinary_runtime_explicit_branch_row",
    },
    {
        "family": "terminal/closure/resume",
        "model_id": "terminal_closure_resume",
        "obligation_id": "resume.current_run_reentry",
        "branch_kind": "failure_path",
        "coverage_kind": "ordinary_runtime",
        "evidence_owner": "router_runtime_resume",
        "evidence_id": "runtime.resume.failure.ambiguous_state",
        "test_name": "test_resume_ambiguous_state_blocks_continue_without_recovery_evidence",
        "path": "tests/router_runtime/resume.py",
        "command": "python -m unittest tests.test_flowpilot_router_runtime_resume",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "ordinary_runtime_contract",
        "risk_tier": "ordinary",
        "synthetic_replay_required": False,
        "synthetic_replay_status": "not_required",
        "covered_failure_mode": "ordinary_runtime_explicit_branch_row",
    },
    {
        "family": "role/output contracts",
        "model_id": "role_output_contracts",
        "obligation_id": "role_output.registry_authority",
        "branch_kind": "negative_path",
        "coverage_kind": "ordinary_runtime",
        "evidence_owner": "role_output_runtime",
        "evidence_id": "runtime.role_output.negative.wrong_role",
        "test_name": "test_runtime_rejects_wrong_role_and_role_key_agent_id",
        "path": "tests/test_flowpilot_role_output_runtime.py",
        "command": "python -m unittest tests.test_flowpilot_role_output_runtime",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "ordinary_runtime_contract",
        "risk_tier": "ordinary",
        "synthetic_replay_required": False,
        "synthetic_replay_status": "not_required",
        "covered_failure_mode": "ordinary_runtime_explicit_branch_row",
    },
)


def _coverage_kind_for_evidence(evidence: dict[str, Any], obligation_id: str) -> str:
    text = " ".join(
        str(evidence.get(field, ""))
        for field in ("evidence_id", "test_name", "path", "command")
    )
    if "background" in text or "background" in obligation_id:
        return "background_artifact"
    if "model_test_alignment" in text:
        return "model_alignment_gate"
    return "ordinary_runtime"


def _alignment_required_cells() -> list[dict[str, str]]:
    cells: list[dict[str, str]] = []
    for entry in build_alignment_plan_entries():
        plan = entry["plan"].to_dict()
        obligations = plan["obligations"]
        for obligation in obligations:
            for branch_kind in obligation["required_test_kinds"]:
                cells.append(
                    {
                        "family": str(entry["family"]),
                        "model_id": str(plan["model_id"]),
                        "obligation_id": str(obligation["obligation_id"]),
                        "branch_kind": str(branch_kind),
                    }
                )
    return cells


def _alignment_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in build_alignment_plan_entries():
        plan = entry["plan"].to_dict()
        obligations = {item["obligation_id"]: item for item in plan["obligations"]}
        for evidence in plan["test_evidence"]:
            for obligation_id in evidence["covered_obligations"]:
                obligation = obligations[obligation_id]
                rows.append(
                    {
                        **ALIGNMENT_ROW_DEFAULTS,
                        "family": str(entry["family"]),
                        "model_id": str(plan["model_id"]),
                        "obligation_id": str(obligation_id),
                        "obligation_type": str(obligation["obligation_type"]),
                        "branch_kind": str(evidence["test_kind"]),
                        "coverage_kind": _coverage_kind_for_evidence(evidence, obligation_id),
                        "evidence_owner": str(Path(evidence["path"]).stem),
                        "evidence_id": str(evidence["evidence_id"]),
                        "test_name": str(evidence["test_name"]),
                        "path": str(evidence["path"]),
                        "command": str(evidence["command"]),
                        "evidence_status": str(evidence["result_status"]),
                        "evidence_current": bool(evidence["evidence_current"]),
                        "evidence_role": str(evidence["evidence_role"]),
                        "live_completion_allowed": False,
                        "coverage_boundary": "ordinary_test_evidence",
                        "source": "flowguard_model_test_alignment_plan",
                    }
                )
    return rows


def build_coverage_rows() -> list[dict[str, Any]]:
    rows = _alignment_rows()
    for row in SYNTHETIC_TRACE_ROWS:
        rows.append(
            {
                **EXPLICIT_TRACE_ROW_DEFAULTS,
                **row,
                "evidence_role": "primary",
                "source": "explicit_trace_branch_row",
            }
        )
    return rows


def _cell_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("family", "")),
        str(row.get("model_id", "")),
        str(row.get("obligation_id", "")),
        str(row.get("branch_kind", "")),
    )


def validate_coverage_rows(
    rows: Sequence[dict[str, Any]],
    required_cells: Sequence[dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required_cells = required_cells or []

    passing_cells = {
        _cell_key(row)
        for row in rows
        if row.get("evidence_role", "primary") == "primary"
        and row.get("evidence_status") in PASS_STATUSES
        and row.get("evidence_current") is True
    }
    for cell in required_cells:
        key = _cell_key(cell)
        if key not in passing_cells:
            findings.append(
                {
                    "code": "missing_branch_owner",
                    "message": "required model branch has no current passing primary evidence owner",
                    **cell,
                }
            )

    for row in rows:
        missing_fields = [
            field
            for field in REQUIRED_ROW_FIELDS
            if field not in row or row[field] in ("", None)
        ]
        if missing_fields:
            findings.append(
                {
                    "code": "missing_row_fields",
                    "message": "coverage row is missing required fields",
                    "missing_fields": missing_fields,
                    "evidence_id": str(row.get("evidence_id", "")),
                }
            )
        if row.get("evidence_role", "primary") == "primary" and row.get("evidence_status") not in PASS_STATUSES:
            findings.append(
                {
                    "code": "invalid_primary_evidence_status",
                    "message": "primary coverage evidence is not passed",
                    "evidence_id": str(row.get("evidence_id", "")),
                    "evidence_status": str(row.get("evidence_status", "")),
                }
            )
        if row.get("coverage_kind") == "background_artifact" and row.get("evidence_status") in BACKGROUND_INCOMPLETE_STATUSES:
            findings.append(
                {
                    "code": "progress_only_background_evidence",
                    "message": "background coverage requires final artifact evidence, not progress-only status",
                    "evidence_id": str(row.get("evidence_id", "")),
                    "evidence_status": str(row.get("evidence_status", "")),
                }
            )
        if row.get("coverage_kind") in SYNTHETIC_NON_LIVE_KINDS and row.get("live_completion_allowed") is not False:
            findings.append(
                {
                    "code": "synthetic_overclaims_live_completion",
                    "message": "synthetic or fixture trace row cannot support live completion",
                    "evidence_id": str(row.get("evidence_id", "")),
                }
            )
        boundary = str(row.get("coverage_boundary", "")).lower()
        if (
            row.get("coverage_kind") in SYNTHETIC_NON_LIVE_KINDS
            and "live_completion" in boundary
            and "non_live" not in boundary
        ):
            findings.append(
                {
                    "code": "synthetic_boundary_mentions_live_completion",
                    "message": "synthetic coverage boundary must not be expressed as live completion",
                    "evidence_id": str(row.get("evidence_id", "")),
                }
            )
        if row.get("risk_tier") in REPLAY_REQUIRED_RISK_TIERS and row.get("synthetic_replay_required") is True:
            replay_status = str(row.get("synthetic_replay_status", ""))
            if replay_status == "present":
                if row.get("coverage_kind") not in SYNTHETIC_NON_LIVE_KINDS:
                    findings.append(
                        {
                            "code": "missing_required_synthetic_replay",
                            "message": "P0/P1 replay-required branches need synthetic or fixture trace evidence",
                            "evidence_id": str(row.get("evidence_id", "")),
                            "coverage_kind": str(row.get("coverage_kind", "")),
                        }
                    )
            elif replay_status == "not_replayable":
                if not str(row.get("non_replayable_reason", "")).strip():
                    findings.append(
                        {
                            "code": "missing_non_replayable_reason",
                            "message": "non-replayable P0/P1 branches must explain the replay boundary",
                            "evidence_id": str(row.get("evidence_id", "")),
                        }
                    )
            else:
                findings.append(
                    {
                        "code": "missing_required_synthetic_replay",
                        "message": "P0/P1 replay-required branches need a present or explained replay status",
                        "evidence_id": str(row.get("evidence_id", "")),
                        "synthetic_replay_status": replay_status,
                    }
                )
            if not str(row.get("covered_failure_mode", "")).strip():
                findings.append(
                    {
                        "code": "missing_covered_failure_mode",
                        "message": "P0/P1 replay-required branches must name the covered failure mode",
                        "evidence_id": str(row.get("evidence_id", "")),
                    }
                )
        if row.get("story_level") == "system":
            if not str(row.get("recovery_loop", "")).strip():
                findings.append(
                    {
                        "code": "missing_system_recovery_loop",
                        "message": "system-level replay rows must identify the recovery loop they prove",
                        "evidence_id": str(row.get("evidence_id", "")),
                    }
                )
            story_steps = row.get("story_steps")
            if not isinstance(story_steps, list) or len(story_steps) < 2 or not all(str(step).strip() for step in story_steps):
                findings.append(
                    {
                        "code": "missing_system_story_steps",
                        "message": "system-level replay rows must list at least two story steps",
                        "evidence_id": str(row.get("evidence_id", "")),
                    }
                )
            terminal_expectation = str(row.get("terminal_expectation", ""))
            if terminal_expectation not in SYSTEM_TERMINAL_EXPECTATIONS:
                findings.append(
                    {
                        "code": "missing_system_terminal_expectation",
                        "message": "system-level replay rows must declare the terminal expectation",
                        "evidence_id": str(row.get("evidence_id", "")),
                        "terminal_expectation": terminal_expectation,
                    }
                )
    return findings


def known_bad_cases() -> list[dict[str, Any]]:
    base = {
        "family": "known bad",
        "model_id": "known_bad",
        "obligation_id": "known_bad.obligation",
        "branch_kind": "happy_path",
        "coverage_kind": "ordinary_runtime",
        "evidence_owner": "known_bad",
        "evidence_id": "known_bad.row",
        "evidence_status": "passed",
        "evidence_current": True,
        "live_completion_allowed": False,
        "coverage_boundary": "ordinary_runtime_contract",
        "risk_tier": "ordinary",
        "synthetic_replay_required": False,
        "synthetic_replay_status": "not_required",
        "non_replayable_reason": "",
        "covered_failure_mode": "known_bad_default",
        "story_level": "local",
        "recovery_loop": "",
        "story_steps": [],
        "terminal_expectation": "",
    }
    return [
        {
            "name": "missing_owner",
            "rows": [],
            "required_cells": [
                {
                    "family": "known bad",
                    "model_id": "known_bad",
                    "obligation_id": "known_bad.obligation",
                    "branch_kind": "happy_path",
                }
            ],
            "expected_codes": ["missing_branch_owner"],
        },
        {
            "name": "synthetic_overclaims_live_completion",
            "rows": [
                {
                    **base,
                    "coverage_kind": "synthetic_trace",
                    "live_completion_allowed": True,
                    "coverage_boundary": "control_flow_only",
                }
            ],
            "required_cells": [],
            "expected_codes": ["synthetic_overclaims_live_completion"],
        },
        {
            "name": "progress_only_background",
            "rows": [
                {
                    **base,
                    "coverage_kind": "background_artifact",
                    "evidence_status": "progress_only",
                    "coverage_boundary": "background_final_artifact_contract",
                }
            ],
            "required_cells": [],
            "expected_codes": [
                "invalid_primary_evidence_status",
                "progress_only_background_evidence",
            ],
        },
        {
            "name": "p0_replay_required_ordinary_runtime_only",
            "rows": [
                {
                    **base,
                    "risk_tier": "P0",
                    "synthetic_replay_required": True,
                    "synthetic_replay_status": "present",
                    "coverage_kind": "ordinary_runtime",
                    "covered_failure_mode": "ordinary_runtime_cannot_substitute_for_synthetic_replay",
                }
            ],
            "required_cells": [],
            "expected_codes": ["missing_required_synthetic_replay"],
        },
        {
            "name": "p1_non_replayable_without_reason",
            "rows": [
                {
                    **base,
                    "risk_tier": "P1",
                    "synthetic_replay_required": True,
                    "synthetic_replay_status": "not_replayable",
                    "covered_failure_mode": "requires_explicit_non_replayable_boundary",
                }
            ],
            "required_cells": [],
            "expected_codes": ["missing_non_replayable_reason"],
        },
        {
            "name": "system_replay_missing_recovery_metadata",
            "rows": [
                {
                    **base,
                    "coverage_kind": "synthetic_trace",
                    "risk_tier": "P1",
                    "synthetic_replay_required": True,
                    "synthetic_replay_status": "present",
                    "covered_failure_mode": "system_rows_need_recovery_metadata",
                    "story_level": "system",
                    "recovery_loop": "",
                    "story_steps": ["only_one_step"],
                    "terminal_expectation": "",
                }
            ],
            "required_cells": [],
            "expected_codes": [
                "missing_system_recovery_loop",
                "missing_system_story_steps",
                "missing_system_terminal_expectation",
            ],
        },
    ]


def build_report() -> dict[str, Any]:
    required_cells = _alignment_required_cells()
    rows = build_coverage_rows()
    findings = validate_coverage_rows(rows, required_cells)
    full_diagnostic = build_full_model_test_code_diagnostic()
    for finding in full_diagnostic["actionable_findings"]:
        findings.append(
            {
                "code": "full_diagnostic_actionable_finding",
                "message": finding["message"],
                "source_code": finding["code"],
                "surface_id": finding["surface_id"],
                "path": finding["path"],
                "repair_type": finding["repair_type"],
            }
        )

    rows_by_family: dict[str, int] = defaultdict(int)
    rows_by_coverage_kind: dict[str, int] = defaultdict(int)
    for row in rows:
        rows_by_family[str(row["family"])] += 1
        rows_by_coverage_kind[str(row["coverage_kind"])] += 1

    return {
        "ok": not findings,
        "result_type": "flowpilot_synthetic_agent_coverage_matrix",
        "coverage_boundary": (
            "Matrix rows prove declared control-flow, runtime, model-test, and "
            "background-artifact coverage ownership. Synthetic or fixture rows "
            "do not prove live AI semantic quality or live completion."
        ),
        "required_cell_count": len(required_cells),
        "row_count": len(rows),
        "rows_by_family": dict(sorted(rows_by_family.items())),
        "rows_by_coverage_kind": dict(sorted(rows_by_coverage_kind.items())),
        "synthetic_trace_row_count": sum(
            1 for row in rows if row["coverage_kind"] in SYNTHETIC_NON_LIVE_KINDS
        ),
        "findings": findings,
        "required_cells": required_cells,
        "rows": rows,
        "full_diagnostic": {
            "ok": full_diagnostic["ok"],
            "full_coverage_ok": full_diagnostic["full_coverage_ok"],
            "release_convergence_ok": full_diagnostic["release_convergence_ok"],
            "gap_counts": full_diagnostic["gap_counts"],
            "actionable_summary": full_diagnostic["actionable_summary"],
        },
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
