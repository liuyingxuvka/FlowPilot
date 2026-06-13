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

def _write_route_process_pass_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "flowguard_operator":
        raise RouterError("route process check must be reviewed_by_role=flowguard_operator")
    if payload.get("passed") is not True or payload.get("process_viability_verdict") != "pass":
        raise RouterError("route process check requires process_viability_verdict=pass")
    required_true = (
        "product_behavior_model_checked",
        "target_realization_model_checked",
        "route_maps_to_target_realization_model",
        "realization_obligations_projected",
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
        _require_target_realization_model_report(project_root, run_root),
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
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "process_viability_verdict": "pass",
            "product_behavior_model_checked": True,
            "target_realization_model_checked": True,
            "route_maps_to_target_realization_model": True,
            "realization_obligations_projected": True,
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

def _write_route_process_issue_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
    *,
    expected_verdict: str,
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "flowguard_operator":
        raise RouterError("route process issue report must be reviewed_by_role=flowguard_operator")
    if payload.get("passed") is True:
        raise RouterError("route process issue report cannot pass")
    if payload.get("process_viability_verdict") != expected_verdict:
        raise RouterError(f"route process issue report requires process_viability_verdict={expected_verdict}")
    checked_paths = [
        _current_route_draft_path(run_root),
        _require_product_behavior_model_report(project_root, run_root),
        _require_target_realization_model_report(project_root, run_root),
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
            "reviewed_by_role": "flowguard_operator",
            "passed": False,
            "process_viability_verdict": expected_verdict,
            "product_behavior_model_checked": bool(payload.get("product_behavior_model_checked")),
            "target_realization_model_checked": bool(payload.get("target_realization_model_checked")),
            "route_maps_to_target_realization_model": bool(payload.get("route_maps_to_target_realization_model")),
            "realization_obligations_projected": bool(payload.get("realization_obligations_projected")),
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
    for flag in (
        "route_draft_written_by_pm",
        "flowguard_operator_route_check_card_delivered",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "flowguard_operator_route_check_passed",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "flowguard_operator_product_route_check_card_delivered",
        "flowguard_operator_product_route_check_passed",
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

__all__ = (
    '_write_route_process_pass_report',
    '_write_route_process_issue_report',
)

_LOCAL_NAMES = set(globals())
