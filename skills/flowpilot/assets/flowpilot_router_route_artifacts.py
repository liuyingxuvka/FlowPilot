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

def _write_product_function_architecture(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("pm_owned", True) is not True:
        raise RouterError("product-function architecture must be PM-owned")
    material_understanding_path = run_root / "pm_material_understanding.json"
    if not material_understanding_path.exists():
        raise RouterError("product-function architecture requires pm_material_understanding.json")
    required_lists = ("user_task_map", "product_capability_map", "feature_decisions", "functional_acceptance_matrix")
    missing_lists = [name for name in required_lists if not isinstance(payload.get(name), list) or not payload.get(name)]
    if missing_lists:
        raise RouterError(f"product-function architecture requires non-empty lists: {', '.join(missing_lists)}")
    if not isinstance(payload.get("highest_achievable_product_target"), dict) or not payload.get("highest_achievable_product_target"):
        raise RouterError("product-function architecture requires highest_achievable_product_target")
    semantic_policy = payload.get("semantic_fidelity_policy")
    if not isinstance(semantic_policy, dict) or semantic_policy.get("silent_downgrade_forbidden") is not True:
        raise RouterError("product-function architecture requires semantic_fidelity_policy.silent_downgrade_forbidden=true")
    root_requirements = payload.get("functional_acceptance_matrix")
    if not isinstance(root_requirements, list):
        raise RouterError("functional_acceptance_matrix must be a list when provided")
    requirement_trace = payload.get("requirement_trace") if isinstance(payload.get("requirement_trace"), dict) else {}
    if not requirement_trace:
        source_registry = [
            {
                "source_requirement_id": str(item.get("source_requirement_id") or item.get("requirement_id") or item.get("acceptance_id") or f"req-{index:03d}"),
                "source_type": str(item.get("source") or "product_function_architecture"),
                "source_path": project_relative(project_root, material_understanding_path),
                "statement": str(item.get("goal") or item.get("behavior") or item.get("acceptance_statement") or item.get("acceptance_id") or f"Requirement {index}"),
                "status": "active",
                "superseded_by": [],
            }
            for index, item in enumerate(root_requirements, start=1)
            if isinstance(item, dict)
        ]
        requirement_trace = {
            "schema_version": "flowpilot.requirement_trace.v1",
            "pm_owned": True,
            "flowpilot_standalone": True,
            "external_tools_required": False,
            "full_protocol_required_when_flowpilot_invoked": True,
            "source_registry": source_registry,
            "legacy_inferred_from_functional_acceptance_matrix": True,
        }
    architecture = {
        "schema_version": "flowpilot.product_function_architecture.v1",
        "run_id": run_state["run_id"],
        "status": str(payload.get("status") or "draft"),
        "pm_owned": True,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "startup_answers": project_relative(project_root, run_root / "startup_answers.json"),
            "startup_activation": project_relative(project_root, run_root / "startup" / "startup_activation.json"),
            "display_surface": project_relative(project_root, run_root / "display" / "display_surface.json"),
            "pm_material_understanding": project_relative(project_root, material_understanding_path),
        },
        "source_material_review": run_state.get("material_review"),
        "requirement_trace": requirement_trace,
        "high_standard_posture": payload.get("high_standard_posture") or {"highest_reasonably_achievable_is_floor": True},
        "unacceptable_result_review": payload.get("unacceptable_result_review") or [],
        "user_task_map": payload.get("user_task_map"),
        "product_capability_map": payload.get("product_capability_map"),
        "feature_decisions": payload.get("feature_decisions"),
        "display_rationale": payload.get("display_rationale") or [],
        "missing_feature_review": payload.get("missing_feature_review") or [],
        "negative_scope": payload.get("negative_scope") or [],
        "semantic_fidelity_policy": semantic_policy,
        "highest_achievable_product_target": payload.get("highest_achievable_product_target"),
        "functional_acceptance_matrix": root_requirements,
        "written_by_role": "project_manager",
        **_role_output_envelope_record(payload),
    }
    write_json(run_root / "product_function_architecture.json", architecture)

def _write_role_gate_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"gate report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is not True:
        raise RouterError("gate report must explicitly pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"gate report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

def _write_compatibility_alias_artifact(
    project_root: Path,
    source_path: Path,
    alias_path: Path,
    *,
    schema_version: str,
    alias_kind: str,
) -> None:
    artifact = read_json(source_path)
    artifact["schema_version"] = schema_version
    artifact["compatibility_alias_kind"] = alias_kind
    artifact["compatibility_alias_for"] = project_relative(project_root, source_path)
    artifact["compatibility_alias_recorded_at"] = utc_now()
    write_json(alias_path, artifact)

def _write_product_behavior_model_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    canonical_path = _product_behavior_model_report_path(run_root)
    _write_role_gate_report(
        project_root,
        run_root,
        run_state,
        payload,
        expected_role="product_flowguard_officer",
        path=canonical_path,
        schema_version="flowpilot.product_behavior_model.v1",
        checked_paths=[run_root / "product_function_architecture.json"],
    )
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _product_behavior_model_compatibility_report_path(run_root),
        schema_version="flowpilot.product_architecture_modelability.v1",
        alias_kind="product_architecture_modelability",
    )

def _write_pm_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    path: Path,
    schema_version: str,
    expected_decision: str,
    source_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("decided_by_role") != "project_manager":
        raise RouterError("PM model decision must include decided_by_role=project_manager")
    if payload.get("decision") != expected_decision:
        raise RouterError(f"PM model decision requires decision={expected_decision}")
    missing = [project_relative(project_root, item) for item in source_paths if not item.exists()]
    if missing:
        raise RouterError(f"PM model decision is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "decided_by_role": "project_manager",
            "decision": expected_decision,
            "source_paths": [project_relative(project_root, item) for item in source_paths],
            "pm_model_fit_review": payload.get("pm_model_fit_review"),
            "product_goal_coverage": payload.get("product_goal_coverage"),
            "unmodeled_or_ambiguous_behavior": payload.get("unmodeled_or_ambiguous_behavior") or [],
            "serial_execution_line_review": payload.get("serial_execution_line_review"),
            "recursive_node_entry_review": payload.get("recursive_node_entry_review"),
            "leaf_worker_readiness_review": payload.get("leaf_worker_readiness_review"),
            "parent_and_final_backward_review_policy": payload.get("parent_and_final_backward_review_policy"),
            "model_miss_repair_policy": payload.get("model_miss_repair_policy"),
            "next_action": payload.get("next_action"),
            "decided_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

def _write_pm_product_behavior_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    accepted: bool,
) -> None:
    _write_pm_model_decision(
        project_root,
        run_root,
        run_state,
        payload,
        path=run_root / "flowguard" / "product_behavior_model_pm_decision.json",
        schema_version="flowpilot.product_behavior_model_pm_decision.v1",
        expected_decision="accept_product_behavior_model"
        if accepted
        else "request_product_behavior_model_rebuild",
        source_paths=[
            run_root / "product_function_architecture.json",
            _require_product_behavior_model_report(project_root, run_root),
        ],
    )
    if not accepted:
        for flag in PRODUCT_ARCHITECTURE_REPAIR_RESET_FLAGS:
            run_state.setdefault("flags", {})[flag] = False

def _write_pm_process_route_model_decision(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    accepted: bool,
) -> None:
    _write_pm_model_decision(
        project_root,
        run_root,
        run_state,
        payload,
        path=run_root / "flowguard" / "process_route_model_pm_decision.json",
        schema_version="flowpilot.process_route_model_pm_decision.v1",
        expected_decision="accept_process_route_model" if accepted else "request_process_route_model_rebuild",
        source_paths=[
            _current_route_draft_path(run_root),
            _require_process_route_model_report(project_root, run_root),
        ],
    )
    if not accepted:
        _reset_route_review_after_route_draft_repair(run_state)

def _write_role_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_role: str,
    path: Path,
    schema_version: str,
    checked_paths: list[Path],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != expected_role:
        raise RouterError(f"block report must be reviewed_by_role={expected_role}")
    if payload.get("passed") is True:
        raise RouterError("block report cannot pass")
    missing = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing:
        raise RouterError(f"block report is missing source paths: {', '.join(missing)}")
    write_json(
        path,
        {
            "schema_version": schema_version,
            "run_id": run_state["run_id"],
            "reviewed_by_role": expected_role,
            "passed": False,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "repair_recommendation": payload.get("repair_recommendation"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

def _gate_outcome_path_from_token(run_root: Path, token: str) -> Path:
    if token == "__current_route_draft__":
        return _current_route_draft_path(run_root)
    if token == "__parent_backward_targets__":
        frontier = _active_frontier(run_root)
        return run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if token == "__active_node_acceptance_plan__":
        frontier = _active_frontier(run_root)
        return _active_node_acceptance_plan_path(run_root, frontier)
    if token.startswith("__active_node_root__/"):
        frontier = _active_frontier(run_root)
        return _active_node_root(run_root, frontier) / token.removeprefix("__active_node_root__/")
    return run_root / token

def _write_gate_outcome_block_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    event: str,
) -> None:
    spec = GATE_OUTCOME_BLOCK_EVENT_SPECS[event]
    checked_paths = [
        _gate_outcome_path_from_token(run_root, str(token))
        for token in spec.get("checked_paths", ())
    ]
    report_path = _gate_outcome_path_from_token(run_root, str(spec["path"]))
    _write_role_block_report(
        project_root,
        run_root,
        run_state,
        payload,
        expected_role=str(spec["expected_role"]),
        path=report_path,
        schema_version=str(spec["schema_version"]),
        checked_paths=checked_paths,
    )
    flags = run_state.setdefault("flags", {})
    for reset_flag in spec.get("reset_flags", ()):
        flags[str(reset_flag)] = False
    gate_blocks = run_state.setdefault("gate_outcome_blocks", [])
    if not isinstance(gate_blocks, list):
        gate_blocks = []
    record = {
        "event": event,
        "report_path": project_relative(project_root, report_path),
        "repair_resets": [str(flag) for flag in spec.get("reset_flags", ())],
        "recorded_at": utc_now(),
    }
    gate_blocks.append(record)
    run_state["gate_outcome_blocks"] = gate_blocks[-20:]
    run_state["active_gate_outcome_block"] = record

def _clear_active_gate_outcome_block_for_pass(run_state: dict[str, Any], *, event: str) -> None:
    cleared_events = set(GATE_OUTCOME_PASS_CLEARS_EVENTS.get(event, ()))
    if not cleared_events:
        return
    active = run_state.get("active_gate_outcome_block")
    if not isinstance(active, dict) or active.get("event") not in cleared_events:
        return
    cleared_at = utc_now()
    active["status"] = "cleared_by_pass"
    active["cleared_by_event"] = event
    active["cleared_at"] = cleared_at
    blocks = run_state.get("gate_outcome_blocks")
    if isinstance(blocks, list):
        for record in reversed(blocks):
            if not isinstance(record, dict):
                continue
            if record.get("event") == active.get("event") and record.get("report_path") == active.get("report_path"):
                record["status"] = "cleared_by_pass"
                record["cleared_by_event"] = event
                record["cleared_at"] = cleared_at
                break
    run_state["active_gate_outcome_block"] = None

def _write_route_process_pass_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "process_flowguard_officer":
        raise RouterError("route process check must be reviewed_by_role=process_flowguard_officer")
    if payload.get("passed") is not True or payload.get("process_viability_verdict") != "pass":
        raise RouterError("route process check requires process_viability_verdict=pass")
    required_true = (
        "product_behavior_model_checked",
        "route_can_reach_product_model",
        "repair_return_policy_checked",
        "serial_execution_model_checked",
        "all_effective_nodes_reachable_in_order",
        "recursive_child_routes_serialized",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("route process check requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _current_route_draft_path(run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process check is missing source paths: {', '.join(missing_paths)}")
    canonical_path = _process_route_model_report_path(run_root)
    write_json(
        canonical_path,
        {
            "schema_version": "flowpilot.process_route_model.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "process_flowguard_officer",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_can_reach_product_model": True,
            "repair_return_policy_checked": True,
            "serial_execution_model_checked": True,
            "all_effective_nodes_reachable_in_order": True,
            "recursive_child_routes_serialized": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _route_process_check_path(run_root),
        schema_version="flowpilot.route_process_check.v1",
        alias_kind="route_process_check",
    )

def _write_route_process_issue_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_verdict: str,
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "process_flowguard_officer":
        raise RouterError("route process issue report must be reviewed_by_role=process_flowguard_officer")
    if payload.get("passed") is True:
        raise RouterError("route process issue report cannot pass")
    if payload.get("process_viability_verdict") != expected_verdict:
        raise RouterError(f"route process issue report requires process_viability_verdict={expected_verdict}")
    checked_paths = [
        _current_route_draft_path(run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route process issue report is missing source paths: {', '.join(missing_paths)}")
    canonical_path = _process_route_model_report_path(run_root)
    write_json(
        canonical_path,
        {
            "schema_version": "flowpilot.process_route_model.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "process_flowguard_officer",
            "passed": False,
            "process_viability_verdict": expected_verdict,
            "product_behavior_model_checked": bool(payload.get("product_behavior_model_checked")),
            "route_can_reach_product_model": bool(payload.get("route_can_reach_product_model")),
            "repair_return_policy_checked": bool(payload.get("repair_return_policy_checked")),
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "recommended_resolution": payload.get("recommended_resolution"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
    _write_compatibility_alias_artifact(
        project_root,
        canonical_path,
        _route_process_check_path(run_root),
        schema_version="flowpilot.route_process_check.v1",
        alias_kind="route_process_check",
    )
    for flag in (
        "route_draft_written_by_pm",
        "process_officer_route_check_card_delivered",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "process_officer_route_check_passed",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "product_officer_route_check_card_delivered",
        "product_officer_route_check_passed",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False
    run_state["route_process_viability"] = {
        "verdict": expected_verdict,
        "report_path": project_relative(project_root, canonical_path),
        "reported_at": utc_now(),
    }

def _write_route_product_pass_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "product_flowguard_officer":
        raise RouterError("route product check must be reviewed_by_role=product_flowguard_officer")
    if payload.get("passed") is not True or payload.get("route_model_review_verdict") != "pass":
        raise RouterError("route product check requires route_model_review_verdict=pass")
    required_true = (
        "product_behavior_model_checked",
        "route_maps_to_product_behavior_model",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("route product check requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _current_route_draft_path(run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "root_acceptance_contract.json",
        _require_process_route_model_report(project_root, run_root),
        run_root / "flowguard" / "process_route_model_pm_decision.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"route product check is missing source paths: {', '.join(missing_paths)}")
    write_json(
        _route_product_check_path(run_root),
        {
            "schema_version": "flowpilot.route_product_check.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "product_flowguard_officer",
            "passed": True,
            "route_model_review_verdict": "pass",
            "product_behavior_model_checked": True,
            "route_maps_to_product_behavior_model": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

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

def _write_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    source_event: str = "pm_writes_node_acceptance_plan",
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="node acceptance plan")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("node acceptance plan must be PM-owned")
    frontier = _active_frontier(run_root)
    active_node_id = str(frontier["active_node_id"])
    active_route_id = str(frontier["active_route_id"])
    if payload.get("node_id") and str(payload["node_id"]) != active_node_id:
        raise RouterError("node acceptance plan node_id must match active frontier")
    route_version = int(frontier.get("route_version") or 0)
    if payload.get("route_version") is not None and int(payload["route_version"]) != route_version:
        raise RouterError("node acceptance plan route_version must match active frontier")
    node_requirements = payload.get("node_requirements")
    if not isinstance(node_requirements, list) or not node_requirements:
        raise RouterError("node acceptance plan requires a non-empty node_requirements list")
    experiment_plan = payload.get("experiment_plan")
    if not isinstance(experiment_plan, list):
        raise RouterError("node acceptance plan requires experiment_plan list")
    high_standard = payload.get("high_standard_recheck")
    if not isinstance(high_standard, dict):
        raise RouterError("node acceptance plan requires high_standard_recheck")
    required_high_standard_fields = {
        "ideal_outcome",
        "unacceptable_outcomes",
        "higher_standard_opportunities",
        "semantic_downgrade_risks",
        "decision",
        "why_current_plan_meets_highest_reasonable_standard",
    }
    def _blank(value: Any) -> bool:
        return value is None or value == "" or value == []

    missing_high_standard = [
        name
        for name in sorted(required_high_standard_fields)
        if name not in high_standard or _blank(high_standard.get(name))
    ]
    if missing_high_standard:
        raise RouterError(f"node high-standard recheck missing fields: {', '.join(missing_high_standard)}")
    if str(high_standard.get("decision")) != "proceed":
        raise RouterError("node acceptance can proceed only after high_standard_recheck.decision=proceed")
    if high_standard.get("controller_can_downgrade_standard") is True:
        raise RouterError("Controller cannot downgrade node standards")
    node = _active_node_definition(run_root, frontier)
    contract = read_json_if_exists(run_root / "root_acceptance_contract.json")
    root_requirement_ids = _root_requirement_ids(contract) if isinstance(contract, dict) else []
    route_node_requirement_ids = _string_list(node.get("covers_requirement_ids")) or root_requirement_ids
    route_node_scenario_ids = _string_list(node.get("covers_scenario_ids"))
    route_node_capability_ids = _string_list(node.get("source_product_capability_ids"))
    node_requirement_ids = [
        str(item.get("requirement_id"))
        for item in node_requirements
        if isinstance(item, dict) and item.get("requirement_id")
    ]
    traced_node_requirements: list[dict[str, Any]] = []
    for item in node_requirements:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("source_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_scenario_ids", route_node_scenario_ids)
        traced.setdefault("source_product_capability_ids", route_node_capability_ids)
        traced.setdefault("change_status", "UNCHANGED")
        traced.setdefault("supersedes_requirement_ids", [])
        traced_node_requirements.append(traced)
    traced_experiment_plan: list[dict[str, Any]] = []
    for item in experiment_plan:
        if not isinstance(item, dict):
            continue
        traced = dict(item)
        traced.setdefault("covers_requirements", node_requirement_ids or route_node_requirement_ids)
        traced.setdefault("covers_root_requirement_ids", route_node_requirement_ids)
        traced.setdefault("covers_product_requirement_ids", _string_list(traced.get("covers_product_requirement_ids")))
        traced_experiment_plan.append(traced)
    node_requirements = traced_node_requirements
    experiment_plan = traced_experiment_plan
    child_ids = _node_child_ids(node)
    payload_leaf_gate = payload.get("leaf_readiness_gate") if isinstance(payload.get("leaf_readiness_gate"), dict) else None
    if payload_leaf_gate is not None:
        leaf_readiness_gate = dict(payload_leaf_gate)
    elif child_ids:
        leaf_readiness_gate = {
            "status": "not_applicable_parent",
            "reason": "Parent/module nodes are composition boundaries and cannot receive worker packets directly.",
        }
    else:
        leaf_readiness_gate = {
            "status": "pass",
            "legacy_inferred_from_reviewed_node_plan": True,
            "single_outcome": True,
            "worker_executable_without_replanning": True,
            "proof_defined": bool(experiment_plan),
            "dependency_boundary_defined": True,
            "failure_isolation_defined": True,
        }
    plan = {
        "schema_version": "flowpilot.node_acceptance_plan.v1",
        "run_id": run_state["run_id"],
        "route_id": active_route_id,
        "route_version": route_version,
        "node_id": active_node_id,
        "pm_owned": True,
        "status": str(payload.get("status") or "approved"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "root_acceptance_contract": project_relative(project_root, run_root / "root_acceptance_contract.json"),
            "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
            "route_flow": project_relative(project_root, _active_route_path(run_root, frontier)),
            "product_function_architecture": project_relative(project_root, run_root / "product_function_architecture.json"),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "requirement_traceability": {
            "schema_version": "flowpilot.node_requirement_traceability.v1",
            "source_route_node_id": active_node_id,
            "source_route_node_covers_requirement_ids": route_node_requirement_ids,
            "source_route_node_covers_scenario_ids": route_node_scenario_ids,
            "source_product_capability_ids": route_node_capability_ids,
            "full_protocol_required_when_flowpilot_invoked": True,
            "all_covered_requirements_must_close_or_be_triaged": True,
            "closure_by_report_only_forbidden": True,
            "external_spec_material_advisory_until_pm_imported": True,
            "legacy_trace_defaults_inferred_by_router": "requirement_traceability" not in payload,
        },
        "prior_path_context_review": prior_review,
        "node_structure": {
            "node_kind": _node_kind(node),
            "has_children": bool(child_ids),
            "child_node_ids": child_ids,
            "parent_backward_replay_required": bool(child_ids),
            "semantic_importance_used_to_trigger_review": False,
        },
        "leaf_readiness_gate": leaf_readiness_gate,
        "node_requirements": node_requirements,
        "experiment_plan": experiment_plan,
        "high_standard_recheck": {
            "ideal_outcome": high_standard.get("ideal_outcome"),
            "unacceptable_outcomes": high_standard.get("unacceptable_outcomes"),
            "higher_standard_opportunities": high_standard.get("higher_standard_opportunities"),
            "semantic_downgrade_risks": high_standard.get("semantic_downgrade_risks"),
            "decision": "proceed",
            "why_current_plan_meets_highest_reasonable_standard": high_standard.get("why_current_plan_meets_highest_reasonable_standard"),
            "controller_can_downgrade_standard": False,
        },
        "advance_gate": {
            "required_before_chunk_execution": True,
            "required_before_node_checkpoint": True,
            "reviewer_or_officer_direct_check_required": True,
            "all_covered_requirements_closed_or_triaged": False,
            "unresolved_requirement_ids": route_node_requirement_ids,
        },
        "written_by_role": "project_manager",
        "source_event": source_event,
    }
    for optional_field in [
        "controller_summary_used_as_evidence",
        "identity",
        "node_title",
        "node_objective",
        "product_behavior_model_segment",
        "proof_obligations",
        "recheck_criteria",
        "repair_context",
        "fixtures_and_evidence_paths",
        "forbidden_low_standard_outcomes",
        "minimum_sufficient_complexity_review",
        "inherited_gate_obligations",
        "skill_standard_projection",
        "active_child_skill_bindings",
        "work_packet_projection",
        "result_matrix_requirements",
        "inherited_root_requirements",
    ]:
        if optional_field in payload:
            plan[optional_field] = payload.get(optional_field)
    issues = _node_acceptance_traceability_issues(plan)
    if issues:
        raise RouterError("node acceptance plan traceability invalid: " + "; ".join(str(issue["message"]) for issue in issues[:5]))
    write_json(_active_node_acceptance_plan_path(run_root, frontier), plan)
    _update_display_plan_current_node(
        project_root,
        run_root,
        run_state,
        node_id=str(frontier["active_node_id"]),
        node_title=str(node.get("title") or node.get("label") or frontier["active_node_id"]),
        checklist=[
            {
                "id": str(item.get("requirement_id") or f"requirement-{index:03d}"),
                "label": str(item.get("acceptance_statement") or item.get("label") or item.get("requirement_id") or f"Requirement {index}"),
                "status": "pending",
            }
            for index, item in enumerate(node_requirements, start=1)
            if isinstance(item, dict)
        ],
        source_event=source_event,
    )

def _write_pm_revised_node_acceptance_plan(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    if not run_state["flags"].get("node_acceptance_plan_review_blocked"):
        raise RouterError("same-node node acceptance-plan repair requires active node_acceptance_plan_review_blocked flag")
    frontier = _active_frontier(run_root)
    node_root = _active_node_root(run_root, frontier)
    block_path = node_root / "reviews" / "node_acceptance_plan_block.json"
    if not block_path.exists():
        raise RouterError("same-node node acceptance-plan repair requires reviewer block report")
    _write_node_acceptance_plan(
        project_root,
        run_root,
        run_state,
        payload,
        source_event="pm_revises_node_acceptance_plan",
    )
    revised_plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    repair_record_path = node_root / "repairs" / "node_acceptance_plan_revision.json"
    write_json(
        repair_record_path,
        {
            "schema_version": "flowpilot.node_acceptance_plan_revision.v1",
            "run_id": run_state["run_id"],
            "route_id": str(frontier["active_route_id"]),
            "route_version": int(frontier.get("route_version") or 0),
            "node_id": str(frontier["active_node_id"]),
            "repair_scope": "same_node_plan_revision",
            "source_block_path": project_relative(project_root, block_path),
            "revised_plan_path": project_relative(project_root, revised_plan_path),
            "stale_blocked_plan_is_context_only": True,
            "reviewer_recheck_required": True,
            "recorded_at": utc_now(),
            "recorded_by": "project_manager",
        },
    )
    run_state["flags"]["node_acceptance_plan_review_blocked"] = False
    run_state["flags"]["node_acceptance_plan_reviewer_passed"] = False
    run_state["flags"]["reviewer_node_acceptance_plan_card_delivered"] = False

def _write_parent_backward_targets(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    frontier = _active_frontier(run_root)
    node = _active_node_definition(run_root, frontier)
    child_ids = _node_child_ids(node)
    route_id = str(frontier["active_route_id"])
    route_version = int(frontier.get("route_version") or 0)
    active_node_id = str(frontier["active_node_id"])
    node_root = _active_node_root(run_root, frontier)
    targets = [
        {
            "parent_node_id": active_node_id,
            "child_node_ids": child_ids,
            "parent_backward_replay_path": project_relative(project_root, node_root / "parent_backward_replay.json"),
            "status": "not_started" if child_ids else "not_required",
            "pm_segment_decision": "not_reviewed" if child_ids else "not_required",
            "latest_repair_requires_rerun": False,
            "latest_replay_route_version": route_version,
        }
    ] if child_ids else []
    record = {
        "schema_version": "flowpilot.parent_backward_targets.v1",
        "run_id": run_state["run_id"],
        "route_id": route_id,
        "route_version": route_version,
        "pm_owned": True,
        "status": "current",
        "built_from_flow_path": project_relative(project_root, _active_route_path(run_root, frontier)),
        "built_at": utc_now(),
        "trigger_rule": {
            "structural_trigger": "any_effective_route_node_with_children",
            "semantic_importance_classification_required": False,
            "leaf_nodes_exempt_from_parent_backward_replay": True,
        },
        "targets": targets,
        "coverage": {
            "parent_targets_total": len(targets),
            "parent_targets_with_replay_passed": 0,
            "parent_targets_with_pm_decision": 0,
            "all_required_parent_replays_passed": not child_ids,
        },
        "written_by_role": "project_manager",
    }
    write_json(run_root / "routes" / route_id / "parent_backward_targets.json", record)

def _write_parent_backward_replay(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    frontier = _active_frontier(run_root)
    if not _active_node_has_children(run_root, frontier):
        raise RouterError("parent backward replay is required only for active nodes with children")
    targets_path = run_root / "routes" / str(frontier["active_route_id"]) / "parent_backward_targets.json"
    if not targets_path.exists():
        raise RouterError("parent backward replay requires parent_backward_targets.json")
    if payload.get("reviewed_by_role") != "human_like_reviewer":
        raise RouterError("parent backward replay must be reviewed_by_role=human_like_reviewer")
    if payload.get("passed") is not True:
        raise RouterError("parent backward replay must explicitly pass")
    active_node_id = str(frontier["active_node_id"])
    replay = {
        "schema_version": "flowpilot.parent_backward_replay.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": active_node_id,
        "pm_owned": True,
        "status": "passed",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "source_paths": {
            "parent_backward_targets": project_relative(project_root, targets_path),
            "node_acceptance_plan": project_relative(project_root, _active_node_acceptance_plan_path(run_root, frontier)),
        },
        "reviewer_report": {
            "reviewer_role": "human_like_reviewer",
            "neutral_observation_written": bool(payload.get("neutral_observation_written", True)),
            "independent_probe_done": bool(payload.get("independent_probe_done", True)),
            "child_evidence_replayed": bool(payload.get("child_evidence_replayed", True)),
            "children_compose_into_parent_goal": True,
            "blocking_findings": [],
            "approval_valid": True,
        },
        "closure_gate": {
            "required_before_parent_checkpoint": True,
            "reviewer_passed": True,
            "unresolved_blocking_findings": 0,
            "parent_closure_allowed": False,
        },
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "parent_backward_replay.json", replay)

def _write_parent_segment_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("parent segment decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="parent segment decision")
    frontier = _active_frontier(run_root)
    replay_path = _active_node_root(run_root, frontier) / "parent_backward_replay.json"
    if not replay_path.exists():
        raise RouterError("parent segment decision requires parent_backward_replay.json")
    decision = str(payload.get("decision") or "continue")
    if decision not in PM_PARENT_SEGMENT_DECISION_ALLOWED_VALUES:
        raise RouterError(f"unsupported parent segment decision: {decision}")
    record = {
        "schema_version": "flowpilot.parent_segment_decision.v1",
        "run_id": run_state["run_id"],
        "route_id": str(frontier["active_route_id"]),
        "route_version": int(frontier.get("route_version") or 0),
        "parent_node_id": str(frontier["active_node_id"]),
        "decision_owner": "project_manager",
        "decision": decision,
        "route_mutation_required": decision != "continue",
        "same_parent_replay_rerun_required": decision != "continue",
        "prior_path_context_review": prior_review,
        "source_paths": {
            "parent_backward_replay": project_relative(project_root, replay_path),
            "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
            "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
        },
        "recorded_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(_active_node_root(run_root, frontier) / "pm_parent_segment_decision.json", record)
    if decision != "continue":
        repair_node_id = str(payload.get("repair_node_id") or f"{frontier['active_node_id']}-repair-{int(frontier.get('route_version') or 1) + 1}")
        _write_route_mutation(
            project_root,
            run_root,
            run_state,
            {
                "route_id": frontier["active_route_id"],
                "repair_node_id": repair_node_id,
                "reason": f"parent_segment_decision:{decision}",
                "stale_evidence": [project_relative(project_root, replay_path)],
                "superseded_nodes": payload.get("superseded_nodes") or [],
                "repair_return_to_node_id": payload.get("repair_return_to_node_id") or payload.get("return_to_node_id"),
                "prior_path_context_review": payload.get("prior_path_context_review"),
            },
        )
    return decision

def _write_pm_research_absorption(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._write_pm_research_absorption(_bound_router(), project_root, run_root, run_state)

def _validate_current_node_packet_envelope(project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    return flowpilot_router_work_packets._validate_current_node_packet_envelope(_bound_router(), project_root, run_root, run_state, envelope, envelope_path, frontier, plan)

def _validate_current_node_packet_event(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_packet_event(_bound_router(), project_root, run_root, run_state, payload)

def _validate_current_node_result_event(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_result_event(_bound_router(), project_root, run_state, payload)

def _validate_current_node_reviewer_pass(project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    return flowpilot_router_work_packets._validate_current_node_reviewer_pass(_bound_router(), project_root, run_state, payload)

def _route_payload_from_reviewed_draft(project_root: Path, run_root: Path, payload: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    return flowpilot_router_route.route_payload_from_reviewed_draft(
        _bound_router(),
        project_root,
        run_root,
        payload,
    )

def _write_route_activation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_activation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

def _write_route_mutation(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    flowpilot_router_route.write_route_mutation(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        payload,
    )

def _write_material_dispatch_repair(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get("decided_by_role") != "project_manager":
        raise RouterError("material dispatch repair requires decided_by_role=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, decision, purpose="material dispatch repair")
    repair_action = str(decision.get("repair_action") or decision.get("selected_next_action") or "").strip()
    if not repair_action:
        raise RouterError("material dispatch repair requires repair_action or selected_next_action")
    block = run_state.get("material_dispatch_block")
    block_path = block.get("path") if isinstance(block, dict) else None
    repair_path = run_root / "material" / "material_dispatch_repair.json"
    write_json(
        repair_path,
        {
            "schema_version": "flowpilot.material_dispatch_repair.v1",
            "run_id": run_state["run_id"],
            "decided_by_role": "project_manager",
            "repair_action": repair_action,
            "source_block_path": block_path,
            "prior_path_context_review": prior_review,
            "recorded_at": utc_now(),
            **_role_output_envelope_record(decision),
        },
    )
    run_state["material_dispatch_block"] = {
        "path": block_path,
        "repair_path": project_relative(project_root, repair_path),
        "repair_recorded_at": utc_now(),
        "status": "repair_ready_for_reviewer_recheck",
    }
    run_state["flags"]["material_scan_dispatch_blocked"] = False
    run_state["flags"]["reviewer_dispatch_allowed"] = False
    run_state["flags"]["reviewer_dispatch_card_delivered"] = False
    for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
        run_state["flags"][flag] = False

def _write_pm_review_block_repair(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    active_block_flag = _require_single_active_model_miss_review_block(run_state, "review-block repair")
    if active_block_flag in MODEL_MISS_MATERIAL_DISPATCH_REPAIR_FLAGS:
        _write_material_dispatch_repair(project_root, run_root, run_state, payload)
        return
    if active_block_flag in MODEL_MISS_ROUTE_MUTATION_BLOCK_FLAGS:
        _write_route_mutation(project_root, run_root, run_state, payload)
        return
    raise RouterError(f"review-block repair has no writer for active block flag {active_block_flag}")

def _write_evidence_quality_package(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="evidence quality package")
    if payload.get("pm_owned", True) is not True:
        raise RouterError("evidence quality package must be PM-owned")
    if not run_state["flags"].get("node_completed_by_pm"):
        raise RouterError("evidence quality package requires PM-completed current node")
    frontier = _active_frontier(run_root)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state["flags"].get("node_completion_ledger_updated") or not node_completion_ledger_path.exists():
        raise RouterError("evidence quality package requires node completion ledger")
    evidence_items = payload.get("evidence_items")
    if evidence_items is None:
        evidence_items = []
    if not isinstance(evidence_items, list):
        raise RouterError("evidence_items must be a list")
    generated_resources = payload.get("generated_resources")
    if generated_resources is None:
        generated_resources = []
    if not isinstance(generated_resources, list):
        raise RouterError("generated_resources must be a list")
    ui_visual_required = bool(payload.get("ui_visual_evidence_required"))
    ui_visual_evidence = payload.get("ui_visual_evidence") if isinstance(payload.get("ui_visual_evidence"), dict) else {}
    if ui_visual_required:
        screenshot_paths = ui_visual_evidence.get("screenshot_paths")
        if not isinstance(screenshot_paths, list) or not screenshot_paths:
            raise RouterError("required UI/visual evidence needs screenshot_paths")
        if ui_visual_evidence.get("old_assets_reused") is True:
            raise RouterError("UI/visual evidence cannot reuse old assets as current evidence")
    unresolved_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") in {"unresolved", "blocked"}]
    stale_evidence = [item for item in evidence_items if isinstance(item, dict) and item.get("status") == "stale"]
    pending_resources = [
        item
        for item in generated_resources
        if isinstance(item, dict) and item.get("disposition") in {None, "", "pending", "unresolved"}
    ]
    if unresolved_evidence or stale_evidence:
        raise RouterError("evidence quality package cannot contain unresolved or stale current evidence")
    if pending_resources:
        raise RouterError("generated resources must have terminal dispositions")
    evidence_ledger_path = run_root / "evidence" / "evidence_ledger.json"
    generated_resource_ledger_path = run_root / "generated_resource_ledger.json"
    quality_package_path = run_root / "quality" / "quality_package.json"
    write_json(
        evidence_ledger_path,
        {
            "schema_version": "flowpilot.evidence_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "items": evidence_items,
            "current_evidence_count": len(evidence_items),
            "stale_count": 0,
            "unresolved_count": 0,
            "controller_origin_evidence_allowed": False,
            "completion_report_only_allowed": False,
            "updated_at": utc_now(),
        },
    )
    write_json(
        generated_resource_ledger_path,
        {
            "schema_version": "flowpilot.generated_resource_ledger.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "resources": generated_resources,
            "resource_count": len(generated_resources),
            "pending_resource_count": 0,
            "unresolved_resource_count": 0,
            "old_visual_assets_may_close_current_gate": False,
            "all_resources_have_terminal_disposition": True,
            "updated_at": utc_now(),
        },
    )
    write_json(
        quality_package_path,
        {
            "schema_version": "flowpilot.quality_package.v1",
            "run_id": run_state["run_id"],
            "pm_owned": True,
            "source_paths": {
                "evidence_ledger": project_relative(project_root, evidence_ledger_path),
                "generated_resource_ledger": project_relative(project_root, generated_resource_ledger_path),
                "execution_frontier": project_relative(project_root, run_root / "execution_frontier.json"),
                "node_completion_ledger": project_relative(project_root, node_completion_ledger_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
                "packet_chain_audit": project_relative(project_root, run_root / "packet_chain_audit.json")
                if (run_root / "packet_chain_audit.json").exists()
                else None,
            },
            "prior_path_context_review": prior_review,
            "quality_checks": {
                "human_like_review_required": True,
                "completion_report_only_allowed": False,
                "rough_or_placeholder_completion_forbidden": True,
                "unresolved_evidence_count_zero": True,
                "unresolved_resource_count_zero": True,
            },
            "ui_visual_evidence": {
                "required": ui_visual_required,
                "status": "provided" if ui_visual_required else "not_applicable",
                "old_assets_reused": bool(ui_visual_evidence.get("old_assets_reused")),
                "screenshot_paths": ui_visual_evidence.get("screenshot_paths") or [],
                "visual_review_notes_path": ui_visual_evidence.get("visual_review_notes_path"),
            },
            "written_at": utc_now(),
        },
    )

_LOCAL_NAMES = set(globals())
