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
OWNER_MODULE = "flowpilot_router_self_interrogation"
def _pm_suggestion_ledger_path(run_root: Path) -> Path:
    return run_root / "pm_suggestion_ledger.jsonl"
def _read_pm_suggestion_ledger(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not path.exists():
        return entries
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RouterError(f"PM suggestion ledger line {line_number} is not valid JSON") from exc
        if not isinstance(entry, dict):
            raise RouterError(f"PM suggestion ledger line {line_number} must be a JSON object")
        entry.setdefault("_line_number", line_number)
        entries.append(entry)
    return entries
def _pm_suggestion_ledger_status(run_root: Path) -> dict[str, Any]:
    ledger_path = _pm_suggestion_ledger_path(run_root)
    entries = _read_pm_suggestion_ledger(ledger_path)
    issues: list[dict[str, str]] = []

    def add_issue(entry: dict[str, Any], message: str) -> None:
        suggestion_id = str(entry.get("suggestion_id") or f"line-{entry.get('_line_number', '?')}")
        issues.append({"suggestion_id": suggestion_id, "message": message})

    for entry in entries:
        if entry.get("schema_version") != PM_SUGGESTION_LEDGER_ENTRY_SCHEMA:
            add_issue(entry, "schema_version must be flowpilot.pm_suggestion_item.v1")
        source_role = str(entry.get("source_role") or "")
        classification = str(entry.get("classification") or "")
        source_output_ref = entry.get("source_output_ref") if isinstance(entry.get("source_output_ref"), dict) else {}
        authority = entry.get("authority_basis") if isinstance(entry.get("authority_basis"), dict) else {}
        disposition = entry.get("pm_disposition") if isinstance(entry.get("pm_disposition"), dict) else {}
        closure = entry.get("closure") if isinstance(entry.get("closure"), dict) else {}
        status = str(disposition.get("status") or "pending")
        closure_status = str(closure.get("status") or "open")

        if source_output_ref.get("sealed_body_content_copied") is True:
            add_issue(entry, "source_output_ref must not copy sealed body content")
        if status not in PM_SUGGESTION_FINAL_DISPOSITIONS:
            add_issue(entry, "pm_disposition.status must be a final PM disposition")
        elif closure_status not in PM_SUGGESTION_CLOSURE_STATUSES_BY_DISPOSITION[status]:
            add_issue(entry, "closure.status must match the PM disposition")
        if status == "defer_to_named_node" and not disposition.get("target_node_or_gate_id"):
            add_issue(entry, "defer_to_named_node requires target_node_or_gate_id")
        if status == "reject_with_reason" and not disposition.get("reason"):
            add_issue(entry, "reject_with_reason requires a PM reason")
        if status == "waive_with_authority" and (
            not disposition.get("reason") or not disposition.get("waiver_authority_role")
        ):
            add_issue(entry, "waive_with_authority requires reason and waiver_authority_role")
        if status == "mutate_route" and (
            not disposition.get("route_version_impact") or not disposition.get("stale_evidence_handling")
        ):
            add_issue(entry, "mutate_route requires route_version_impact and stale_evidence_handling")
        if status == "repair_or_reissue" and (
            not disposition.get("repair_or_reissue_target")
            or disposition.get("same_review_class_recheck_required") is not True
        ):
            add_issue(entry, "repair_or_reissue requires target and same-review-class recheck")
        if classification == "current_gate_blocker":
            if source_role in PM_SUGGESTION_WORKER_ROLES:
                add_issue(entry, "worker-origin suggestions cannot be current_gate_blocker")
            if source_role == "human_like_reviewer" and authority.get("reviewer_minimum_standard_failure") is not True:
                add_issue(entry, "reviewer current_gate_blocker requires reviewer_minimum_standard_failure")
            if source_role in PM_SUGGESTION_OFFICER_ROLES and authority.get("formal_flowguard_model_gate") is not True:
                add_issue(entry, "officer current_gate_blocker requires formal_flowguard_model_gate")
            if closure_status not in {"closed", "stopped_for_user"}:
                add_issue(entry, "current_gate_blocker must be closed or stopped before final closure")
        if closure.get("blocks_current_gate_until_closed") is True and closure_status not in {"closed", "stopped_for_user"}:
            add_issue(entry, "blocking suggestion still blocks the current gate")

    return {
        "path": str(ledger_path),
        "exists": ledger_path.exists(),
        "entry_count": len(entries),
        "issue_count": len(issues),
        "clean": not issues,
        "issues": issues,
    }
__all__ = (
    "_pm_suggestion_ledger_path",
    "_read_pm_suggestion_ledger",
    "_pm_suggestion_ledger_status",
)
_LOCAL_NAMES = set(globals())
