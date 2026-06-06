"""Internal router owner helpers extracted from flowpilot_router.

The public router names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so private helper lookups remain
stable while the implementation body lives outside the facade.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Iterable

import card_runtime
import flowpilot_runtime_closure
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress
from flowpilot_router_protocol_catalog import *
from flowpilot_router_payload_contracts_startup import _payload_contract

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER
OWNER_MODULE = "flowpilot_router_payload_contracts"
def _pm_resume_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_resume_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_RESUME_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "recovery_evidence",
            "role_freshness_verification",
            "packet_loop_continuation",
            "decision_rationale",
            "controller_reminder.controller_may_create_project_evidence",
            "controller_reminder.controller_may_approve_gates",
            "controller_reminder.controller_may_implement",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_RESUME_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "controller_reminder.controller_only": [True],
            "controller_reminder.controller_may_read_sealed_bodies": [False],
            "controller_reminder.controller_may_infer_from_chat_history": [False],
            "controller_reminder.controller_may_advance_or_close_route": [False],
            "controller_reminder.controller_may_create_project_evidence": [False],
        },
        conditional_required_fields={
            "when continuation/resume_reentry.json records ambiguous_state_blocks_controller_execution=true and decision=continue_current_packet_loop": [
                "explicit_recovery_evidence_recorded=true",
                "recovery_evidence",
            ],
            "when decision=close_after_final_ledger_and_terminal_replay": [
                "final_ledger_built_clean evidence",
                "final_backward_replay_passed evidence",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
        ],
        description=(
            "PM manual-resume recovery decision. This is a role-output body contract, "
            "not Controller-authored project evidence; Controller waits for Router status after the runtime submits it."
        ),
    )
def _pm_parent_segment_decision_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_parent_segment_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_PARENT_SEGMENT_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "repair_node_id",
            "superseded_nodes",
            "stale_evidence_to_mark",
            "decision_rationale",
            "same_parent_replay_rerun_plan",
            "contract_self_check",
        ],
        allowed_values={
            "decision_owner": ["project_manager"],
            "decision": sorted(PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
        },
        conditional_required_fields={
            "when decision!=continue": [
                "decision_rationale",
                "stale_evidence_to_mark or superseded_nodes when affected evidence/nodes exist",
                "same_parent_replay_rerun_plan",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Only decision=continue may close the active parent node; all other decisions require route mutation and same-parent replay rerun.",
        ],
        description=(
            "PM parent-segment decision after reviewer backward replay. This is a role-output body "
            "contract; Controller waits for Router status after the runtime submits it."
        ),
    )
def _pm_terminal_closure_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    pm_context = project_relative(project_root, _pm_prior_path_context_path(run_root))
    route_history = project_relative(project_root, _route_history_index_path(run_root))
    return _payload_contract(
        name="pm_terminal_closure_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_TERMINAL_CLOSURE_DECISION_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "final_report",
            "closure_rationale",
            "lifecycle_reconciliation",
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean",
            "lifecycle_reconciliation.terminal_backward_replay_passed",
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure",
            "lifecycle_reconciliation.execution_frontier_current",
            "lifecycle_reconciliation.role_binding_ledger_current",
            "lifecycle_reconciliation.continuation_binding_current",
            "lifecycle_reconciliation.current_ledgers_clean",
            "lifecycle_reconciliation.pm_suggestion_ledger_clean",
            "lifecycle_reconciliation.self_interrogation_index_clean",
            "contract_self_check",
        ],
        allowed_values={
            "approved_by_role": ["project_manager"],
            "decision": sorted(PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES),
            "prior_path_context_review.reviewed": [True],
            "prior_path_context_review.source_paths": [[pm_context, route_history]],
            "prior_path_context_review.controller_summary_used_as_evidence": [False],
            "lifecycle_reconciliation.final_route_wide_gate_ledger_clean": [True],
            "lifecycle_reconciliation.terminal_backward_replay_passed": [True],
            "lifecycle_reconciliation.task_completion_projection_ready_for_pm_terminal_closure": [True],
            "lifecycle_reconciliation.execution_frontier_current": [True],
            "lifecycle_reconciliation.role_binding_ledger_current": [True],
            "lifecycle_reconciliation.continuation_binding_current": [True],
            "lifecycle_reconciliation.current_ledgers_clean": [True],
            "lifecycle_reconciliation.pm_suggestion_ledger_clean": [True],
            "lifecycle_reconciliation.self_interrogation_index_clean": [True],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Cite exactly the current-run pm_prior_path_context.json and route_history_index.json in prior_path_context_review.source_paths.",
            "Use empty arrays explicitly when no completed, superseded, stale, blocked, or experimental history applies.",
            "Approve closure only after clean final ledger, passed terminal backward replay, current completion projection, clean PM suggestion ledger, clean self-interrogation index, clean lifecycle ledgers, and continuation binding are present.",
        ],
        description=(
            "PM terminal closure approval. This is a role-output body contract; Controller may only "
            "wait for Router status and must not infer closure from chat history."
        ),
    )
def _pm_model_miss_triage_payload_contract(project_root: Path, run_root: Path) -> dict[str, Any]:
    return _payload_contract(
        name="pm_model_miss_triage_decision_role_output",
        required_object="role_output_body",
        required_fields=list(PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS),
        optional_fields=[
            "flowguard_operator_request_refs",
            "flowguard_operator_report_refs",
            "same_class_findings_summary",
            "candidate_repairs_considered",
            "minimal_sufficient_repair_recommendation",
            "rejected_larger_repairs",
            "rejected_smaller_repairs",
            "post_repair_model_checks_required",
            "decision_rationale",
        ],
        allowed_values={
            "decided_by_role": ["project_manager"],
            "decision": sorted(PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES),
            "same_class_findings_reviewed": [True, False],
            "repair_recommendation_reviewed": [True, False],
        },
        conditional_required_fields={
            "when decision=proceed_with_model_backed_repair": [
                "flowguard_capability.can_model_bug_class=true",
                "flowguard_operator_report_refs[].report_path",
                "flowguard_operator_report_refs[].report_hash",
                "same_class_findings_reviewed=true",
                "repair_recommendation_reviewed=true",
                "candidate_repairs_considered",
                "minimal_sufficient_repair_recommendation",
                "post_repair_model_checks_required",
            ],
            "when decision=out_of_scope_not_modelable": [
                "flowguard_capability.can_model_bug_class=false",
                "flowguard_capability.incapability_reason",
                "selected_next_action",
                "why_repair_may_start",
            ],
        },
        structural_requirements=[
            "Submit the body directly to Router with `flowpilot_runtime.py submit-output-to-router`; the role_output_envelope must carry body_ref and runtime_receipt_ref metadata.",
            "Do not start pm.review_repair until this decision either authorizes a model-backed repair or records why FlowGuard cannot model the bug class.",
            "For model-backed repair, FlowGuard operator reports must include old_model_miss_reason, bug_class_definition, same_class_findings, coverage_added, candidate_repairs, minimal_sufficient_repair_recommendation, rejected_larger_repairs, rejected_smaller_repairs, post_repair_model_checks_required, and residual_blindspots.",
            "PM selects the repair path; FlowGuard operator reports provide model evidence and repair recommendations but do not approve route mutation by themselves.",
        ],
        description=(
            "PM model-miss triage decision for reviewer blockers. This closes the obligation to ask why "
            "FlowGuard missed the bug class before normal repair planning can start."
        ),
    )
def _pm_decision_payload_contract_for_card(project_root: Path, run_root: Path, card_id: str) -> dict[str, Any] | None:
    if card_id == "pm.resume_decision":
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if card_id == "pm.model_miss_triage":
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if card_id == "pm.parent_segment_decision":
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if card_id == "pm.closure":
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None
def _role_decision_payload_contract_for_events(
    project_root: Path, run_root: Path, allowed_events: list[str]
) -> dict[str, Any] | None:
    if allowed_events == ["pm_resume_recovery_decision_returned"]:
        return _pm_resume_decision_payload_contract(project_root, run_root)
    if allowed_events == [PM_MODEL_MISS_TRIAGE_DECISION_EVENT]:
        return _pm_model_miss_triage_payload_contract(project_root, run_root)
    if allowed_events == ["pm_records_parent_segment_decision"]:
        return _pm_parent_segment_decision_payload_contract(project_root, run_root)
    if allowed_events == ["pm_approves_terminal_closure"]:
        return _pm_terminal_closure_payload_contract(project_root, run_root)
    return None
__all__ = (
    "_pm_resume_decision_payload_contract",
    "_pm_parent_segment_decision_payload_contract",
    "_pm_terminal_closure_payload_contract",
    "_pm_model_miss_triage_payload_contract",
    "_pm_decision_payload_contract_for_card",
    "_role_decision_payload_contract_for_events",
)
_LOCAL_NAMES = set(globals())
