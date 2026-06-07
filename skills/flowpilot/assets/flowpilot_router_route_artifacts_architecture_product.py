"""Internal router owner helpers extracted from flowpilot_router."""

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
            "inferred_from_functional_acceptance_matrix": True,
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
        expected_role="flowguard_operator",
        path=canonical_path,
        schema_version="flowpilot.product_behavior_model.v1",
        checked_paths=[run_root / "product_function_architecture.json"],
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

__all__ = (
    '_write_product_function_architecture',
    '_write_role_gate_report',
    '_write_product_behavior_model_report',
    '_write_pm_model_decision',
    '_write_pm_product_behavior_model_decision',
    '_write_pm_process_route_model_decision',
)

_LOCAL_NAMES = set(globals())
