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

__all__ = (
    '_write_product_function_architecture',
    '_write_role_gate_report',
    '_write_compatibility_alias_artifact',
    '_write_product_behavior_model_report',
    '_write_pm_model_decision',
    '_write_pm_product_behavior_model_decision',
    '_write_pm_process_route_model_decision',
    '_write_role_block_report',
    '_gate_outcome_path_from_token',
    '_write_gate_outcome_block_report',
    '_clear_active_gate_outcome_block_for_pass',
    '_write_route_process_pass_report',
    '_write_route_process_issue_report',
    '_write_route_product_pass_report',
)

_LOCAL_NAMES = set(globals())
