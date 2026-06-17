"""Focused child helpers for FlowPilot router structure ownership."""

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


def _write_pm_implementation_intent(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get("written_by_role") != "project_manager":
        raise RouterError("implementation intent must include written_by_role=project_manager")
    source_paths = [
        run_root / "product_function_architecture.json",
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "flowguard" / "product_behavior_model_pm_decision.json",
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
        run_root / "child_skill_manifest_pm_approval.json",
        run_root / "capabilities" / "capability_sync.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in source_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"implementation intent is missing source paths: {', '.join(missing_paths)}")
    required_lists = (
        "implementation_pathways",
        "realization_obligations",
        "thin_success_traps",
        "non_downgrade_rules",
        "evidence_gates",
    )
    missing_lists = [
        field
        for field in required_lists
        if not isinstance(payload.get(field), list) or not payload.get(field)
    ]
    if missing_lists:
        raise RouterError("implementation intent requires non-empty lists: " + ", ".join(missing_lists))
    intent_path = _pm_implementation_intent_path(run_root)
    intent = {
        "schema_version": "flowpilot.pm_implementation_intent.v1",
        "run_id": run_state["run_id"],
        "status": str(payload.get("status") or "written"),
        "written_by_role": "project_manager",
        "source_paths": [project_relative(project_root, item) for item in source_paths],
        "implementation_intent_summary": payload.get("implementation_intent_summary"),
        "implementation_pathways": payload.get("implementation_pathways"),
        "target_realization_model_request": payload.get("target_realization_model_request") or {},
        "realization_obligations": payload.get("realization_obligations"),
        "thin_success_traps": payload.get("thin_success_traps"),
        "non_downgrade_rules": payload.get("non_downgrade_rules"),
        "evidence_gates": payload.get("evidence_gates"),
        "residual_blindspots": payload.get("residual_blindspots") or [],
        "next_action": payload.get("next_action"),
        "written_at": utc_now(),
        **_role_output_envelope_record(payload),
    }
    write_json(intent_path, intent)
    for flag in (
        "flowguard_operator_target_realization_model_card_delivered",
        "target_realization_model_submitted",
        "target_realization_model_blocked",
        "pm_target_realization_model_decision_card_delivered",
        "pm_target_realization_model_accepted",
        "pm_target_realization_model_rebuild_requested",
        "reviewer_implementation_intent_card_delivered",
        "implementation_intent_reviewer_passed",
        "implementation_intent_reviewer_blocked",
        "pm_prior_path_context_card_delivered",
        "route_draft_written_by_pm",
        "process_route_model_submitted",
        "process_route_model_repair_required",
        "process_route_model_blocked",
        "pm_process_route_model_decision_card_delivered",
        "pm_process_route_model_accepted",
        "pm_process_route_model_rebuild_requested",
        "reviewer_route_check_card_delivered",
        "reviewer_route_check_passed",
        "route_activated_by_pm",
    ):
        run_state.setdefault("flags", {})[flag] = False
def _write_target_realization_model_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "flowguard_operator":
        raise RouterError("target realization model must be reviewed_by_role=flowguard_operator")
    if payload.get("passed") is not True or payload.get("target_realization_verdict") != "pass":
        raise RouterError("target realization model requires target_realization_verdict=pass")
    required_true = (
        "pm_implementation_intent_checked",
        "product_behavior_model_checked",
        "pm_intent_preserved",
        "realization_obligations_modeled",
        "thin_success_traps_modeled",
        "evidence_gates_modeled",
    )
    missing = [field for field in required_true if payload.get(field) is not True]
    if missing:
        raise RouterError("target realization model requires " + ", ".join(f"{field}=true" for field in missing))
    checked_paths = [
        _require_pm_implementation_intent(project_root, run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "product_function_architecture.json",
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
        run_root / "capabilities" / "capability_sync.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"target realization model is missing source paths: {', '.join(missing_paths)}")
    canonical_path = _target_realization_model_report_path(run_root)
    write_json(
        canonical_path,
        {
            "schema_version": "flowpilot.target_realization_model.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "flowguard_operator",
            "passed": True,
            "target_realization_verdict": "pass",
            "pm_implementation_intent_checked": True,
            "product_behavior_model_checked": True,
            "pm_intent_preserved": True,
            "realization_obligations_modeled": True,
            "thin_success_traps_modeled": True,
            "evidence_gates_modeled": True,
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "realization_obligation_ids": payload.get("realization_obligation_ids") or [],
            "model_obligations": payload.get("model_obligations") or payload.get("realization_obligations") or [],
            "thin_success_traps": payload.get("thin_success_traps") or [],
            "non_downgrade_rules": payload.get("non_downgrade_rules") or [],
            "evidence_gates": payload.get("evidence_gates") or [],
            "target_state_model": payload.get("target_state_model") or {},
            "transition_model": payload.get("transition_model") or {},
            "conformance_boundary": payload.get("conformance_boundary") or {},
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )
def _write_target_realization_model_issue_report(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    payload: dict[str, Any],
) -> None:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("reviewed_by_role") != "flowguard_operator":
        raise RouterError("target realization model issue report must be reviewed_by_role=flowguard_operator")
    if payload.get("passed") is True:
        raise RouterError("target realization model issue report cannot pass")
    if payload.get("target_realization_verdict") != "blocked":
        raise RouterError("target realization model issue report requires target_realization_verdict=blocked")
    checked_paths = [
        _require_pm_implementation_intent(project_root, run_root),
        _require_product_behavior_model_report(project_root, run_root),
        run_root / "product_function_architecture.json",
        run_root / "root_acceptance_contract.json",
        run_root / "child_skill_gate_manifest.json",
    ]
    missing_paths = [project_relative(project_root, item) for item in checked_paths if not item.exists()]
    if missing_paths:
        raise RouterError(f"target realization model issue report is missing source paths: {', '.join(missing_paths)}")
    write_json(
        _target_realization_model_report_path(run_root),
        {
            "schema_version": "flowpilot.target_realization_model.v1",
            "run_id": run_state["run_id"],
            "reviewed_by_role": "flowguard_operator",
            "passed": False,
            "target_realization_verdict": "blocked",
            "source_paths": [project_relative(project_root, item) for item in checked_paths],
            "blocking_findings": payload.get("blocking_findings") or payload.get("findings") or [],
            "recommended_resolution": payload.get("recommended_resolution"),
            "residual_blindspots": payload.get("residual_blindspots") or [],
            "reported_at": utc_now(),
            **_role_output_envelope_record(payload),
        },
    )

__all__ = (
    '_write_pm_implementation_intent',
    '_write_target_realization_model_report',
    '_write_target_realization_model_issue_report',
)

_LOCAL_NAMES = set(globals())
