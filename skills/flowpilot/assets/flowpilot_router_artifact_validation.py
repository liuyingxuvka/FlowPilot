"""Router skeleton owner helpers for flowpilot_router_artifact_validation.

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


OWNER_MODULE = 'flowpilot_router_artifact_validation'

def _artifact_issue(field: str, message: str, repair_owner: str = "project_manager") -> dict[str, str]:
    return {"field": field, "message": message, "repair_owner": repair_owner}

def _validate_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != str(raw_hash):
        issues.append(_artifact_issue(hash_key, "hash does not match file content", "artifact_author"))
    return issues

def _validate_role_output_hash_if_present(project_root: Path, payload: dict[str, Any], path_key: str, hash_key: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    raw_path = payload.get(path_key)
    raw_hash = payload.get(hash_key)
    if not raw_path:
        issues.append(_artifact_issue(path_key, "missing required path field", "artifact_author"))
        return issues
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        issues.append(_artifact_issue(path_key, f"path does not exist: {raw_path}", "artifact_author"))
        return issues
    if not raw_hash:
        issues.append(_artifact_issue(hash_key, "missing required sha256 hash field", "artifact_author"))
        return issues
    actual, semantic = _role_output_hashes(path)
    accepted = {actual}
    accepted.update(_role_output_semantic_hashes(path))
    if str(raw_hash) not in accepted:
        issues.append(_artifact_issue(hash_key, "hash does not match role output content", "artifact_author"))
    return issues

def validate_artifact(project_root: Path, artifact_type: str, artifact_path: str) -> dict[str, Any]:
    path = resolve_project_path(project_root, artifact_path)
    payload = read_json(path)
    issues: list[dict[str, str]] = []
    if artifact_type == "node_acceptance_plan":
        required_top = ("schema_version", "run_id", "route_id", "route_version", "node_id", "node_requirements", "experiment_plan", "high_standard_recheck", "prior_path_context_review")
        for field in required_top:
            if field not in payload or payload.get(field) in (None, "", []):
                issues.append(_artifact_issue(field, "missing required field", "project_manager"))
        high_standard = payload.get("high_standard_recheck") if isinstance(payload.get("high_standard_recheck"), dict) else {}
        for field in (
            "ideal_outcome",
            "unacceptable_outcomes",
            "higher_standard_opportunities",
            "semantic_downgrade_risks",
            "decision",
            "why_current_plan_meets_highest_reasonable_standard",
        ):
            if field not in high_standard or high_standard.get(field) in (None, "", []):
                issues.append(_artifact_issue(f"high_standard_recheck.{field}", "missing required field", "project_manager"))
        prior = payload.get("prior_path_context_review") if isinstance(payload.get("prior_path_context_review"), dict) else {}
        for field in (
            "reviewed",
            "source_paths",
            "completed_nodes_considered",
            "superseded_nodes_considered",
            "stale_evidence_considered",
            "prior_blocks_or_experiments_considered",
            "impact_on_decision",
        ):
            if field not in prior:
                issues.append(_artifact_issue(f"prior_path_context_review.{field}", "missing required field", "project_manager"))
        issues.extend(_node_acceptance_traceability_issues(payload))
    elif artifact_type == "final_route_wide_gate_ledger":
        required_top = (
            "schema_version",
            "run_id",
            "pm_owned",
            "status",
            "source_paths",
            "evidence_integrity",
            "counts",
            "entries",
            "root_contract_replay",
            "requirement_trace_closure",
        )
        for field in required_top:
            if field not in payload or payload.get(field) in (None, "", []):
                issues.append(_artifact_issue(field, "missing required field", "project_manager"))
        if payload.get("pm_owned") is not True:
            issues.append(_artifact_issue("pm_owned", "final ledger must be PM-owned", "project_manager"))
        if payload.get("status") != "clean":
            issues.append(_artifact_issue("status", "final ledger must be clean", "project_manager"))
        counts = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
        if int(counts.get("unresolved_count", 0) or 0) != 0:
            issues.append(_artifact_issue("counts.unresolved_count", "final ledger requires unresolved_count=0", "project_manager"))
        issues.extend(_final_ledger_traceability_issues(payload))
    elif artifact_type == "self_interrogation_record":
        record_issues, unresolved_hard_count = _self_interrogation_record_issues(
            project_root,
            project_root / ".flowpilot" / "runs" / str(payload.get("run_id") or ""),
            path,
            payload,
        )
        for issue in record_issues:
            issues.append(_artifact_issue(str(issue.get("scope") or issue.get("record_id") or "self_interrogation_record"), str(issue.get("message") or "invalid self-interrogation record"), str(payload.get("owner_role") or "project_manager")))
        if unresolved_hard_count != 0:
            issues.append(_artifact_issue("unresolved_hard_finding_count", "self-interrogation record has unresolved hard/current findings", str(payload.get("owner_role") or "project_manager")))
    elif artifact_type == "packet_envelope":
        envelope = dict(payload)
        for field in ("schema_version", "packet_id", "from_role", "to_role", "node_id", "body_path", "body_hash", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required packet envelope field", str(envelope.get("from_role") or "project_manager")))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "packet body must stay sealed to target role", str(envelope.get("from_role") or "project_manager")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "body_path", "body_hash"))
        if envelope.get("packet_type") != "user_intake":
            audit = packet_runtime.validate_packet_ready_for_direct_relay(
                project_root,
                packet_envelope=envelope,
                envelope_path=path,
            )
            for blocker in audit.get("blockers") or []:
                issues.append(_artifact_issue("direct_dispatch_preflight", str(blocker), str(envelope.get("from_role") or "project_manager")))
    elif artifact_type == "result_envelope":
        envelope = dict(payload)
        for field in ("schema_version", "packet_id", "completed_by_role", "result_body_path", "result_body_hash", "next_recipient", "body_visibility"):
            if field not in envelope or envelope.get(field) in (None, ""):
                issues.append(_artifact_issue(field, "missing required result envelope field", str(envelope.get("completed_by_role") or "worker")))
        if envelope.get("completed_by_role") == "controller":
            issues.append(_artifact_issue("completed_by_role", "Controller cannot author current-node results", "worker"))
        if envelope.get("body_visibility") != packet_runtime.SEALED_BODY_VISIBILITY:
            issues.append(_artifact_issue("body_visibility", "result body must stay sealed to reviewer/PM recipient", str(envelope.get("completed_by_role") or "worker")))
        issues.extend(_validate_hash_if_present(project_root, envelope, "result_body_path", "result_body_hash"))
    elif artifact_type == "role_output_envelope":
        path_keys = ("body_path", "report_path", "decision_path", "result_body_path", "memo_path", "architecture_path", "contract_path", "manifest_path", "route_path", "draft_path", "plan_path", "package_path", "ledger_path")
        found = False
        body_ref = payload.get("body_ref") if isinstance(payload.get("body_ref"), dict) else None
        if body_ref and body_ref.get("path"):
            found = True
            if body_ref.get("hash"):
                ref_payload = {"body_path": body_ref.get("path"), "body_hash": body_ref.get("hash")}
                issues.extend(_validate_role_output_hash_if_present(project_root, ref_payload, "body_path", "body_hash"))
            else:
                issues.append(_artifact_issue("body_ref.hash", "role output envelope body_ref requires hash", str(payload.get("from_role") or "role")))
        for path_key in path_keys:
            if payload.get(path_key):
                hash_key = path_key[:-5] + "_hash" if path_key.endswith("_path") else f"{path_key}_hash"
                found = True
                if payload.get(hash_key):
                    issues.extend(_validate_role_output_hash_if_present(project_root, payload, path_key, hash_key))
        if not found:
            issues.append(_artifact_issue("path", "role output envelope must include a known artifact path field", str(payload.get("from_role") or "role")))
        if not payload.get("from_role"):
            issues.append(_artifact_issue("from_role", "missing producing role", "role"))
        if not payload.get("to_role"):
            issues.append(_artifact_issue("to_role", "missing recipient role", "role"))
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, payload)
        except role_output_runtime.RoleOutputRuntimeError as exc:
            issues.append(_artifact_issue("role_output_runtime_receipt", str(exc), str(payload.get("from_role") or "role")))
    elif artifact_type == "gate_decision":
        decision = payload.get("gate_decision") if isinstance(payload.get("gate_decision"), dict) else payload
        issues.extend(_gate_decision_issues(project_root, decision))
    else:
        raise RouterError(f"unsupported artifact validation type: {artifact_type}")
    return {
        "ok": not issues,
        "artifact_type": artifact_type,
        "artifact_path": project_relative(project_root, path),
        "issue_count": len(issues),
        "errors": issues,
        "next_action": None if not issues else f"repair_{artifact_type}",
    }

_LOCAL_NAMES = set(globals())
