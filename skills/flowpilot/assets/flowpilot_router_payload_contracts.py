"""Internal router owner helpers extracted from flowpilot_router.

The public compatibility names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so legacy private helper lookups remain
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

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
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

def _payload_contract(
    *,
    name: str,
    required_object: str,
    required_fields: list[str],
    optional_fields: list[str] | None = None,
    allowed_values: dict[str, list[Any]] | None = None,
    conditional_required_fields: dict[str, list[str]] | None = None,
    structural_requirements: list[str] | None = None,
    description: str,
    reviewer_check: str | None = None,
) -> dict[str, Any]:
    contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": name,
        "required_object": required_object,
        "required_fields": required_fields,
        "optional_fields": optional_fields or [],
        "conditional_required_fields": conditional_required_fields or {},
        "structural_requirements": structural_requirements or [],
        "allowed_values": allowed_values or {},
        "description": description,
        "controller_may_fill_missing_fields": False,
        "on_missing_or_ambiguous_payload": "ask_user_or_return_to_named_role; do_not_guess",
    }
    if reviewer_check:
        contract["reviewer_check"] = reviewer_check
    return contract

def _startup_answers_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="startup_answers_with_optional_ai_interpretation_receipt",
        required_object="payload.startup_answers",
        required_fields=["background_agents", "scheduled_continuation", "display_surface", "provenance"],
        optional_fields=["payload.startup_answer_interpretation"],
        allowed_values={
            "startup_answers.background_agents": sorted(STARTUP_ANSWER_ENUMS["background_agents"]),
            "startup_answers.scheduled_continuation": sorted(STARTUP_ANSWER_ENUMS["scheduled_continuation"]),
            "startup_answers.display_surface": sorted(STARTUP_ANSWER_ENUMS["display_surface"]),
            "startup_answers.provenance": [
                STARTUP_ANSWER_PROVENANCE,
                STARTUP_ANSWER_INTERPRETATION_PROVENANCE,
            ],
            "startup_answer_interpretation.schema_version": [STARTUP_ANSWER_INTERPRETATION_SCHEMA],
            "startup_answer_interpretation.interpreted_by": ["controller", "bootloader"],
            "startup_answer_interpretation.interpretation_provenance": [STARTUP_ANSWER_INTERPRETATION_PROVENANCE],
            "startup_answer_interpretation.ambiguity_status": ["none"],
            "startup_answer_interpretation.interpreted_answers.background_agents": sorted(
                STARTUP_ANSWER_ENUMS["background_agents"]
            ),
            "startup_answer_interpretation.interpreted_answers.scheduled_continuation": sorted(
                STARTUP_ANSWER_ENUMS["scheduled_continuation"]
            ),
            "startup_answer_interpretation.interpreted_answers.display_surface": sorted(
                STARTUP_ANSWER_ENUMS["display_surface"]
            ),
        },
        conditional_required_fields={
            "when startup_answers.provenance=ai_interpreted_from_explicit_user_reply": [
                "startup_answer_interpretation.schema_version",
                "startup_answer_interpretation.raw_user_reply_text",
                "startup_answer_interpretation.interpreted_by",
                "startup_answer_interpretation.interpretation_provenance",
                "startup_answer_interpretation.ambiguity_status",
                "startup_answer_interpretation.interpreted_answers.background_agents",
                "startup_answer_interpretation.interpreted_answers.scheduled_continuation",
                "startup_answer_interpretation.interpreted_answers.display_surface",
            ],
        },
        description=(
            "Pass canonical enum answers. If the user's reply was natural language, the AI may interpret it into "
            "these fields only with a startup_answer_interpretation receipt that preserves the raw user reply and "
            "states ambiguity_status=none."
        ),
    )

def _terminal_summary_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="terminal_summary_markdown_and_user_display_receipt",
        required_object="payload",
        required_fields=[
            "summary_markdown",
            "displayed_to_user",
            "displayed_summary_sha256",
            "read_scope_used",
        ],
        optional_fields=["source_paths_reviewed"],
        allowed_values={
            "displayed_to_user": [True],
            "read_scope_used": [TERMINAL_SUMMARY_READ_SCOPE],
        },
        structural_requirements=[
            f"summary_markdown must start with this exact attribution line: {TERMINAL_SUMMARY_ATTRIBUTION}",
            "displayed_summary_sha256 must equal sha256(summary_markdown)",
            "source_paths_reviewed, when supplied, may cite only files inside the current run root",
            "Controller must show this same summary text to the user before writing the Controller receipt or applying the direct terminal action",
            "The final user report is output-only and does not create completion authority",
        ],
        description=(
            "Write the final FlowPilot run summary after terminal mode is reached. "
            "This is a terminal-only read exception for all files inside the current run root."
        ),
    )

def _display_surface_receipt_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="display_surface_receipt",
        required_object="payload.display_confirmation",
        required_fields=[
            "display_confirmation.action_type",
            "display_confirmation.display_kind",
            "display_confirmation.display_text_sha256",
            "display_confirmation.provenance",
            "display_confirmation.rendered_to",
        ],
        optional_fields=["payload.display_surface_receipt"],
        allowed_values={
            "display_confirmation.provenance": [DISPLAY_CONFIRMATION_PROVENANCE],
            "display_confirmation.rendered_to": [DISPLAY_CONFIRMATION_TARGET],
            "display_surface_receipt.schema_version": [DISPLAY_SURFACE_RECEIPT_SCHEMA],
            "display_surface_receipt.actual_surface": ["chat_route_sign", "chat_route_sign_fallback", "cockpit"],
            "display_surface_receipt.host_display_surface_verified": [True],
        },
        conditional_required_fields={
            "when payload.display_surface_receipt is supplied": [
                "display_surface_receipt.schema_version",
                "display_surface_receipt.actual_surface",
            ],
            "when display_surface_receipt.actual_surface=cockpit": [
                "display_surface_receipt.host_display_surface_verified",
            ],
        },
        description=(
            "Confirm the router-provided route sign was displayed in the user dialog. If a native Cockpit or "
            "fallback display was attempted, include display_surface_receipt with the actual surface and host result."
        ),
        reviewer_check="Reviewer checks requested cockpit versus actual cockpit/fallback reality when Cockpit was requested.",
    )

def _role_slots_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="role_slots_startup_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "role_agents[].role_key",
            "role_agents[].agent_id",
            "role_agents[].model_policy",
            "role_agents[].reasoning_effort_policy",
            "role_agents[].spawn_result",
            "role_agents[].spawned_for_run_id",
            "role_agents[].spawned_after_startup_answers",
        ],
        optional_fields=["role_agents[].host_spawn_receipt"],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "role_agents[].model_policy": [BACKGROUND_ROLE_MODEL_POLICY],
            "role_agents[].reasoning_effort_policy": [BACKGROUND_ROLE_REASONING_EFFORT_POLICY],
            "role_agents[].spawn_result": [ROLE_AGENT_SPAWN_RESULT],
            "role_agents[].host_spawn_receipt.source_kind": ["host_receipt"],
        },
        conditional_required_fields={
            "when role_agents[].host_spawn_receipt is supplied": [
                "role_agents[].host_spawn_receipt.source_kind",
                "role_agents[].host_spawn_receipt.spawned_for_run_id",
                "role_agents[].host_spawn_receipt.role_key",
                "role_agents[].host_spawn_receipt.agent_id",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate role agent record for each FlowPilot role key.",
            "Each live role agent must be explicitly requested with the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
        ],
        description="Record one fresh live host role agent per FlowPilot role when background agents were allowed, using the strongest available background role intelligence policy.",
        reviewer_check="Reviewer checks live agent spawn freshness unless each slot carries a host receipt.",
    )

def _heartbeat_payload_contract(run_id: str, automation_id_hint: str) -> dict[str, Any]:
    return _payload_contract(
        name="heartbeat_host_automation_receipt",
        required_object="payload",
        required_fields=[
            "route_heartbeat_interval_minutes",
            "host_automation_id",
            "host_automation_verified",
            "host_automation_proof.source_kind",
            "host_automation_proof.run_id",
            "host_automation_proof.host_automation_id",
            "host_automation_proof.route_heartbeat_interval_minutes",
            "host_automation_proof.heartbeat_bound_to_current_run",
        ],
        allowed_values={
            "route_heartbeat_interval_minutes": [1],
            "host_automation_verified": [True],
            "host_automation_proof.source_kind": ["host_receipt"],
            "host_automation_proof.run_id": [run_id],
            "host_automation_proof.route_heartbeat_interval_minutes": [1],
            "host_automation_proof.heartbeat_bound_to_current_run": [True],
        },
        description="Bind the one-minute host heartbeat automation to this exact current run before startup fact review.",
        reviewer_check="Reviewer checks heartbeat host binding when scheduled continuation was requested.",
    )

def _resume_role_rehydration_payload_contract(
    run_state: dict[str, Any],
    contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    del contexts
    return _payload_contract(
        name="resume_role_rehydration_receipt",
        required_object="payload",
        required_fields=[
            "background_agents_capability_status",
            "liveness_probe_batch_id",
            "liveness_probe_mode",
            "all_liveness_probes_started_before_wait",
            "rehydrated_role_agents[].role_key",
            "rehydrated_role_agents[].agent_id",
            "rehydrated_role_agents[].model_policy",
            "rehydrated_role_agents[].reasoning_effort_policy",
            "rehydrated_role_agents[].rehydration_result",
            "rehydrated_role_agents[].rehydrated_for_run_id",
            "rehydrated_role_agents[].rehydrated_after_resume_tick_id",
            "rehydrated_role_agents[].rehydrated_after_resume_state_loaded",
            "rehydrated_role_agents[].core_prompt_path",
            "rehydrated_role_agents[].core_prompt_hash",
            "rehydrated_role_agents[].host_liveness_status",
            "rehydrated_role_agents[].liveness_decision",
            "rehydrated_role_agents[].resume_agent_attempted",
            "rehydrated_role_agents[].bounded_wait_result",
            "rehydrated_role_agents[].bounded_wait_ms",
            "rehydrated_role_agents[].liveness_probe_batch_id",
            "rehydrated_role_agents[].liveness_probe_mode",
            "rehydrated_role_agents[].liveness_probe_started_at",
            "rehydrated_role_agents[].liveness_probe_completed_at",
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active",
        ],
        allowed_values={
            "background_agents_capability_status": ["available"],
            "liveness_probe_mode": [ROLE_AGENT_LIVENESS_PROBE_MODE],
            "all_liveness_probes_started_before_wait": [True],
            "rehydrated_role_agents[].role_key": list(CREW_ROLE_KEYS),
            "rehydrated_role_agents[].model_policy": [BACKGROUND_ROLE_MODEL_POLICY],
            "rehydrated_role_agents[].reasoning_effort_policy": [BACKGROUND_ROLE_REASONING_EFFORT_POLICY],
            "rehydrated_role_agents[].rehydration_result": sorted(RESUME_ROLE_AGENT_RESULTS),
            "rehydrated_role_agents[].rehydrated_for_run_id": [run_state["run_id"]],
            "rehydrated_role_agents[].rehydrated_after_resume_state_loaded": [True],
            "rehydrated_role_agents[].host_liveness_status": sorted(ROLE_AGENT_HOST_LIVENESS_STATUSES),
            "rehydrated_role_agents[].liveness_decision": sorted(ROLE_AGENT_LIVENESS_DECISIONS),
            "rehydrated_role_agents[].resume_agent_attempted": [True],
            "rehydrated_role_agents[].bounded_wait_result": sorted(ROLE_AGENT_BOUNDED_WAIT_RESULTS),
            "rehydrated_role_agents[].liveness_probe_mode": [ROLE_AGENT_LIVENESS_PROBE_MODE],
            "rehydrated_role_agents[].wait_agent_timeout_treated_as_active": [False],
        },
        conditional_required_fields={
            "when role_rehydration_request[].role_memory_status=available": [
                "rehydrated_role_agents[].memory_packet_path",
                "rehydrated_role_agents[].memory_packet_hash",
                "rehydrated_role_agents[].memory_seeded_from_current_run",
            ],
            "when role_rehydration_request[].role_memory_status!=available": [
                "rehydrated_role_agents[].memory_missing_acknowledged",
                "rehydrated_role_agents[].replacement_seeded_from_common_run_context",
            ],
            "when rehydrated_role_agents[].role_key=project_manager": [
                "rehydrated_role_agents[].pm_resume_context_delivered",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate rehydrated role agent record for each FlowPilot role key.",
            "Start all six liveness probes in one concurrent batch before waiting for individual results.",
            "Use one liveness_probe_batch_id for the top-level receipt and every role record.",
            "Each record must match the corresponding role_rehydration_request path/hash fields.",
            "Reuse active current-run role agents after memory/context refresh; spawn only replacement roles whose liveness is missing, cancelled, unknown, completed, or timeout_unknown.",
            "Each restored or replacement live role agent must be bound to the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
            "A wait_agent timeout must be recorded as timeout_unknown and must not justify live_agent_continuity_confirmed.",
            "missing, cancelled, completed, unknown, or timeout_unknown host liveness must spawn a replacement from current-run memory instead of continuing to wait on the old role.",
        ],
        optional_fields=[
            "rehydrated_role_agents[].spawned_after_resume_state_loaded",
        ],
        description="Refresh or replace all six FlowPilot role bindings from current-run memory before PM resume decision, reusing active agents and spawning only failed replacements.",
        reviewer_check="PM and reviewer checks use the written crew_rehydration_report before resume decisions.",
    )

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
            "PM heartbeat/manual-resume recovery decision. This is a role-output body contract, "
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
            "lifecycle_reconciliation.crew_ledger_current",
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
            "lifecycle_reconciliation.crew_ledger_current": [True],
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
            "officer_request_refs",
            "officer_report_refs",
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
                "officer_report_refs[].report_path",
                "officer_report_refs[].report_hash",
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
            "For model-backed repair, officer reports must include old_model_miss_reason, bug_class_definition, same_class_findings, coverage_added, candidate_repairs, minimal_sufficient_repair_recommendation, rejected_larger_repairs, rejected_smaller_repairs, post_repair_model_checks_required, and residual_blindspots.",
            "PM selects the repair path; officer reports provide model evidence and repair recommendations but do not approve route mutation by themselves.",
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

_LOCAL_NAMES = set(globals())
