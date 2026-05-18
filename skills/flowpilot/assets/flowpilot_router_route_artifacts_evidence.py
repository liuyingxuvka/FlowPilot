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

__all__ = (
    '_write_material_dispatch_repair',
    '_write_pm_review_block_repair',
    '_write_evidence_quality_package',
)

_LOCAL_NAMES = set(globals())
