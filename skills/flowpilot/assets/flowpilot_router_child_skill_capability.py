"""Router skeleton owner helpers for flowpilot_router_child_skill_capability.

These helpers were moved out of ``flowpilot_router.py`` during the final
StructureMesh skeleton cleanup. The module is bound to the router skeleton
before execution so cross-owner transitional lookups stay explicit.
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
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_dispatcher
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_startup_flow
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
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_child_skill_capability'

def _sync_child_skill_manifest_review_approval(project_root: Path, run_root: Path) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    review_path = run_root / "reviews" / "child_skill_gate_manifest_review.json"
    if not manifest_path.exists() or not review_path.exists():
        return
    review = read_json(review_path)
    if review.get("passed") is not True:
        return
    manifest = read_json(manifest_path)
    manifest.update(
        _role_output_envelope_record_for_mutable_artifact(
            project_root,
            run_root,
            manifest_path,
            manifest,
            reason="child_skill_gate_manifest_review_approval_sync",
        )
    )
    approval = manifest.setdefault("approval", {})
    if approval.get("reviewer_passed") is True:
        return
    approval["reviewer_passed"] = True
    approval["reviewed_at"] = review.get("reported_at") or utc_now()
    manifest["updated_at"] = utc_now()
    write_json(manifest_path, manifest)

def _approve_child_skill_manifest_for_route(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    required_paths = [
        manifest_path,
        run_root / "reviews" / "child_skill_gate_manifest_review.json",
    ]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"PM child-skill approval is missing required reports: {', '.join(missing)}")
    if payload.get("approved_by_role", "project_manager") != "project_manager":
        raise RouterError("child-skill manifest route approval must be by project_manager")
    if payload.get("controller_self_approval_allowed") is True:
        raise RouterError("child-skill manifest PM approval cannot allow Controller self-approval")
    manifest = read_json(manifest_path)
    manifest["status"] = "approved"
    manifest["updated_at"] = utc_now()
    manifest.setdefault("approval", {})
    manifest["approval"].update(
        {
            "reviewer_passed": True,
            "flowguard_operator_process_passed": False,
            "flowguard_operator_process_default_gate_removed": True,
            "flowguard_operator_product_passed": False,
            "flowguard_operator_product_default_gate_removed": True,
            "pm_approved_for_route": True,
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
        }
    )
    write_json(manifest_path, manifest)
    write_json(
        run_root / "child_skill_manifest_pm_approval.json",
        {
            "schema_version": "flowpilot.child_skill_manifest_pm_approval.v1",
            "run_id": run_state["run_id"],
            "approved_by_role": "project_manager",
            "approved_at": utc_now(),
            "source_paths": [project_relative(project_root, path) for path in required_paths],
        },
    )

def _sync_capability_evidence(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    manifest_path = run_root / "child_skill_gate_manifest.json"
    capabilities_path = run_root / "capabilities.json"
    approval_path = run_root / "child_skill_manifest_pm_approval.json"
    required_paths = [manifest_path, capabilities_path, approval_path]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"capability evidence sync is missing paths: {', '.join(missing)}")
    manifest = read_json(manifest_path)
    if manifest.get("status") != "approved" or manifest.get("approval", {}).get("pm_approved_for_route") is not True:
        raise RouterError("capability evidence sync requires PM-approved child-skill manifest")
    write_json(
        run_root / "capabilities" / "capability_sync.json",
        {
            "schema_version": "flowpilot.capability_evidence_sync.v1",
            "run_id": run_state["run_id"],
            "synced_by": str(payload.get("synced_by") or "controller"),
            "pm_approved_manifest": True,
            "source_paths": [project_relative(project_root, path) for path in required_paths],
            "synced_at": utc_now(),
        },
    )

_LOCAL_NAMES = set(globals())
