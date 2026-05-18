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

OWNER_MODULE = "flowpilot_router_route_artifacts"

def _write_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("root acceptance contract must be PM-owned")
    architecture_path = run_root / "product_function_architecture.json"
    if not architecture_path.exists():
        raise RouterError("root contract requires product-function architecture")
    root_requirements = payload.get("root_requirements")
    if not isinstance(root_requirements, list) or not root_requirements:
        raise RouterError("root contract requires a non-empty root_requirements list")
    proof_matrix = payload.get("proof_matrix")
    if not isinstance(proof_matrix, list) or not proof_matrix:
        raise RouterError("root contract requires a non-empty proof_matrix list")
    scenario_ids = payload.get("selected_scenario_ids")
    if not isinstance(scenario_ids, list) or not scenario_ids:
        raise RouterError("root contract requires a non-empty selected_scenario_ids list")
    traced_requirements: list[dict[str, Any]] = []
    source_ids_by_requirement: dict[str, list[str]] = {}
    for item in root_requirements:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        requirement_id = str(traced.get("requirement_id") or f"root-{len(traced_requirements) + 1:03d}")
        traced["requirement_id"] = requirement_id
        source_ids = _string_list(traced.get("source_requirement_ids")) or [requirement_id]
        traced["source_requirement_ids"] = source_ids
        traced.setdefault("change_status", "ADDED")
        traced.setdefault("supersedes_requirement_ids", [])
        traced.setdefault("changed_reason", "Initial PM root-contract import from product-function architecture.")
        traced.setdefault("approval_owner_role", "project_manager")
        source_ids_by_requirement[requirement_id] = source_ids
        traced_requirements.append(traced)
    traced_proof_matrix: list[dict[str, Any]] = []
    for item in proof_matrix:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        requirement_id = str(traced.get("requirement_id") or "")
        traced.setdefault("source_requirement_ids", source_ids_by_requirement.get(requirement_id, [requirement_id] if requirement_id else []))
        traced_proof_matrix.append(traced)
    root_requirements = traced_requirements
    proof_matrix = traced_proof_matrix
    contract = {
        "schema_version": "flowpilot.root_acceptance_contract.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "product_function_architecture": project_relative(project_root, architecture_path),
        },
        "requirement_traceability_policy": {
            "schema_version": "flowpilot.root_requirement_traceability.v1",
            "source": "product_function_architecture.requirement_trace",
            "stable_source_requirement_ids_required": True,
            "change_status_required": True,
            "external_spec_material_advisory_until_pm_imported": True,
            "completion_requires_final_trace_closure": True,
        },
        "root_requirements": root_requirements,
        "proof_matrix": proof_matrix,
        "standard_scenario_pack": {
            "required": True,
            "path": project_relative(project_root, run_root / "standard_scenario_pack.json"),
            "selected_scenario_ids": scenario_ids,
            "covers_requirement_ids": _root_requirement_ids({"root_requirements": root_requirements}),
        },
        "completion_policy": {
            "unresolved_residual_risks_allowed": False,
            "risk_triage_required_before_completion": True,
        },
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    scenario_pack = {
        "schema_version": "flowpilot.standard_scenario_pack.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": "approved",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "selected_scenario_ids": scenario_ids,
        "covers_requirement_ids": _root_requirement_ids({"root_requirements": root_requirements}),
        "selection_reason": payload.get("scenario_selection_reason") or "Selected from root acceptance contract risk coverage.",
    }
    write_json(run_root / "root_acceptance_contract.json", contract)
    write_json(run_root / "standard_scenario_pack.json", scenario_pack)
    (run_root / "contract.md").write_text(
        "\n".join(
            [
                "# FlowPilot Root Acceptance Contract",
                "",
                f"Run: {run_state['run_id']}",
                "",
                "The PM has frozen the root acceptance contract. See:",
                "",
                "- `root_acceptance_contract.json`",
                "- `standard_scenario_pack.json`",
                "",
            ]
        ),
        encoding="utf-8",
    )

def _freeze_root_acceptance_contract(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    required_paths = [
        run_root / "root_acceptance_contract.json",
        run_root / "standard_scenario_pack.json",
        run_root / "contract.md",
        run_root / "reviews" / "root_contract_challenge.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"cannot freeze root contract; missing paths: {', '.join(missing)}")
    contract = read_json(run_root / "root_acceptance_contract.json")
    if contract.get("completion_policy", {}).get("unresolved_residual_risks_allowed") is not False:
        raise RouterError("root contract cannot allow unresolved residual risks")
    _require_clean_self_interrogation(
        project_root,
        run_root,
        gate_name="root contract freeze",
        scopes=("startup", "product_architecture"),
    )
    contract["status"] = "frozen"
    contract["frozen_by_role"] = "project_manager"
    contract["frozen_at"] = utc_now()
    write_json(run_root / "root_acceptance_contract.json", contract)

def _write_dependency_policy(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    contract_path = run_root / "root_acceptance_contract.json"
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("dependency policy requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("dependency policy must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot be authority for dependency policy")
    if payload.get("controller_self_install_allowed") is True:
        raise RouterError("Controller cannot self-approve host-level installs")
    host_install_requested = bool(payload.get("host_level_install_requested"))
    user_approval_recorded = bool(payload.get("explicit_user_approval_recorded"))
    if host_install_requested and not user_approval_recorded:
        raise RouterError("host-level installs require explicit recorded user approval")
    policy = {
        "schema_version": "flowpilot.dependency_policy.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, contract_path),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "host_level_install_requested": host_install_requested,
        "explicit_user_approval_recorded": user_approval_recorded,
        "controller_self_install_allowed": False,
        "allowed_dependency_actions": payload.get("allowed_dependency_actions") or [],
        "blocked_dependency_actions": payload.get("blocked_dependency_actions") or ["host_install_without_user_approval"],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "dependency_policy.json", policy)

def _write_capabilities_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    dependency_path = run_root / "dependency_policy.json"
    architecture_path = run_root / "product_function_architecture.json"
    contract_path = run_root / "root_acceptance_contract.json"
    if not dependency_path.exists():
        raise RouterError("capabilities manifest requires dependency_policy.json")
    if not architecture_path.exists():
        raise RouterError("capabilities manifest requires product_function_architecture.json")
    if not contract_path.exists() or read_json(contract_path).get("status") != "frozen":
        raise RouterError("capabilities manifest requires frozen root contract")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("capabilities manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw skill or host inventory cannot authorize capabilities")
    architecture = read_json(architecture_path)
    capabilities = payload.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        capabilities = architecture.get("product_capability_map") or []
    if not isinstance(capabilities, list) or not capabilities:
        raise RouterError("capabilities manifest requires a non-empty capabilities list or product_capability_map")
    manifest = {
        "schema_version": "flowpilot.capabilities_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "dependency_policy": project_relative(project_root, dependency_path),
            "product_function_architecture": project_relative(project_root, architecture_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "capabilities": capabilities,
        "capability_to_skill_needs": payload.get("capability_to_skill_needs") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "capabilities.json", manifest)

def _validate_selected_child_skills(selected_skills: Any) -> list[dict[str, Any]]:
    if not isinstance(selected_skills, list):
        raise RouterError("selected child skills must be a list")
    allowed_approvers = {
        "project_manager",
        "human_like_reviewer",
        "process_flowguard_officer",
        "product_flowguard_officer",
    }
    for skill in selected_skills:
        if not isinstance(skill, dict):
            raise RouterError("each selected child skill entry must be an object")
        for gate in skill.get("gates") or []:
            if not isinstance(gate, dict):
                raise RouterError("each child-skill gate must be an object")
            approver = gate.get("required_approver")
            if approver == "controller" or gate.get("controller_can_approve") is True:
                raise RouterError("Controller cannot approve child-skill gates")
            if approver and approver not in allowed_approvers:
                raise RouterError(f"unsupported child-skill gate approver: {approver}")
    return selected_skills

def _write_child_skill_selection(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    capabilities_path = run_root / "capabilities.json"
    if not capabilities_path.exists():
        raise RouterError("child-skill selection requires capabilities.json")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill selection must be PM-owned")
    if payload.get("raw_inventory_used_as_authority") is True or payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw local skill inventory cannot authorize child-skill selection")
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = payload.get("skill_decisions") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    selection = {
        "schema_version": "flowpilot.pm_child_skill_selection.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "source_paths": {
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "dependency_policy": project_relative(project_root, run_root / "dependency_policy.json"),
        },
        "raw_inventory_used_as_authority": False,
        "raw_inventory_can_seed_candidates_only": True,
        "selected_from_product_needs": True,
        "selected_skills": selected_skills,
        "deferred_skills": payload.get("deferred_skills") or [],
        "rejected_skills": payload.get("rejected_skills") or [],
        "written_by_role": "project_manager",
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "pm_child_skill_selection.json", selection)

def _write_child_skill_gate_manifest(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    selection_path = run_root / "pm_child_skill_selection.json"
    capabilities_path = run_root / "capabilities.json"
    contract_path = run_root / "root_acceptance_contract.json"
    for required_path, label in (
        (selection_path, "pm_child_skill_selection.json"),
        (capabilities_path, "capabilities.json"),
        (contract_path, "root_acceptance_contract.json"),
    ):
        if not required_path.exists():
            raise RouterError(f"child-skill gate manifest requires {label}")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("child-skill gate manifest must be PM-owned")
    if payload.get("raw_inventory_is_authority") is True:
        raise RouterError("raw inventory cannot be authority for child-skill gate manifest")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill gate manifest cannot allow Controller self-approval")
    selection = read_json(selection_path)
    selected_skills = payload.get("selected_skills")
    if selected_skills is None:
        selected_skills = selection.get("selected_skills") or []
    selected_skills = _validate_selected_child_skills(selected_skills)
    manifest_path = run_root / "child_skill_gate_manifest.json"
    manifest = {
        "schema_version": "flowpilot.child_skill_gate_manifest.v1",
        "run_id": run_state["run_id"],
        "pm_owned": True,
        "status": str(payload.get("status") or "draft"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "pm_child_skill_selection": project_relative(project_root, selection_path),
            "capabilities_manifest": project_relative(project_root, capabilities_path),
            "root_acceptance_contract": project_relative(project_root, contract_path),
        },
        "raw_inventory_is_authority": False,
        "controller_self_approval_allowed": False,
        "selected_skills": selected_skills,
        "approval": {
            "reviewer_passed": False,
            "process_officer_passed": False,
            "product_officer_passed": False,
            "pm_approved_for_route": False,
        },
        **_role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            payload,
            reason="child_skill_gate_manifest_can_be_updated_by_review_gates",
        ),
    }
    write_json(manifest_path, manifest)

def _write_pm_resume_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("PM resume decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="PM resume decision")
    resume_path = run_root / "continuation" / "resume_reentry.json"
    if not resume_path.exists():
        raise RouterError("PM resume decision requires continuation/resume_reentry.json")
    resume_evidence = read_json(resume_path)
    rehydration_path = run_root / "continuation" / "crew_rehydration_report.json"
    if not run_state["flags"].get("resume_roles_restored") or not rehydration_path.exists():
        raise RouterError("PM resume decision requires crew_rehydration_report before PM runway")
    rehydration_report = read_json(rehydration_path)
    if rehydration_report.get("all_six_roles_ready") is not True:
        raise RouterError("PM resume decision requires all six roles ready")
    if rehydration_report.get("pm_memory_rehydrated") is not True and rehydration_report.get("background_agents_mode") != "single-agent":
        raise RouterError("PM resume decision requires project_manager memory rehydration")
    decision = str(payload.get("decision") or "continue_current_packet_loop")
    if decision not in PM_RESUME_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported PM resume decision: {decision}")
    reminder = payload.get("controller_reminder")
    if not isinstance(reminder, dict):
        raise RouterError("PM resume decision requires controller_reminder")
    if reminder.get("controller_only") is not True:
        raise RouterError("PM resume decision must remind Controller it is controller_only")
    if reminder.get("controller_may_read_sealed_bodies") is not False:
        raise RouterError("PM resume decision must forbid sealed body reads")
    if reminder.get("controller_may_infer_from_chat_history") is not False:
        raise RouterError("PM resume decision must forbid chat-history route inference")
    if reminder.get("controller_may_advance_or_close_route") is not False:
        raise RouterError("PM resume decision must forbid Controller route advance or closure")
    ambiguous = bool(resume_evidence.get("ambiguous_state_blocks_controller_execution"))
    recovery_recorded = bool(payload.get("explicit_recovery_evidence_recorded"))
    if ambiguous and decision == "continue_current_packet_loop" and not recovery_recorded:
        raise RouterError("ambiguous resume state cannot continue without explicit recovery evidence")
    if decision == "close_after_final_ledger_and_terminal_replay" and not (
        run_state["flags"].get("final_ledger_built_clean") and run_state["flags"].get("final_backward_replay_passed")
    ):
        raise RouterError("resume closure requires final ledger and terminal replay to have passed")
    write_json(
        _resume_decision_path(run_root),
        {
            "schema_version": "flowpilot.pm_resume_decision.v1",
            "run_id": run_state["run_id"],
            "decision_owner": "project_manager",
            "decision": decision,
            "resume_ambiguous": ambiguous,
            "explicit_recovery_evidence_recorded": recovery_recorded,
            "source_paths": {
                "resume_reentry": project_relative(project_root, resume_path),
                "router_state": project_relative(project_root, run_state_path(run_root)),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "packet_ledger": project_relative(project_root, run_root / "packet_ledger.json"),
                "prompt_delivery_ledger": project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                "crew_ledger": project_relative(project_root, run_root / "crew_ledger.json"),
                "crew_memory": project_relative(project_root, run_root / "crew_memory"),
                "crew_rehydration_report": project_relative(project_root, rehydration_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            },
            "crew_rehydration_report": {
                "path": project_relative(project_root, rehydration_path),
                "all_six_roles_ready": bool(rehydration_report.get("all_six_roles_ready")),
                "current_run_memory_complete": bool(rehydration_report.get("current_run_memory_complete")),
                "pm_memory_rehydrated": bool(rehydration_report.get("pm_memory_rehydrated")),
                "missing_memory_role_keys": rehydration_report.get("missing_memory_role_keys") or [],
            },
            "prior_path_context_review": prior_review,
            "controller_reminder": {
                "controller_only": True,
                "controller_may_read_sealed_bodies": False,
                "controller_may_infer_from_chat_history": False,
                "controller_may_advance_or_close_route": False,
                "controller_may_create_project_evidence": False,
            },
            "recorded_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_display_plan_from_pm_payload(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_resume_recovery_decision_returned",
    )

__all__ = (
    '_write_root_acceptance_contract',
    '_freeze_root_acceptance_contract',
    '_write_dependency_policy',
    '_write_capabilities_manifest',
    '_validate_selected_child_skills',
    '_write_child_skill_selection',
    '_write_child_skill_gate_manifest',
    '_write_pm_resume_decision',
)

_LOCAL_NAMES = set(globals())
