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

def _write_pm_resume_decision(project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get("decision_owner") != "project_manager":
        raise RouterError("PM resume decision requires decision_owner=project_manager")
    prior_review = _require_pm_prior_path_context(project_root, run_root, payload, purpose="PM resume decision")
    resume_path = run_root / "continuation" / "resume_reentry.json"
    if not resume_path.exists():
        raise RouterError("PM resume decision requires continuation/resume_reentry.json")
    resume_evidence = read_json(resume_path)
    rehydration_path = run_root / "continuation" / "role_binding_recovery_report.json"
    if not run_state["flags"].get("resume_roles_restored") or not rehydration_path.exists():
        raise RouterError("PM resume decision requires role_binding_recovery_report before PM runway")
    rehydration_report = read_json(rehydration_path)
    if rehydration_report.get("required_role_bindings_ready") is not True:
        raise RouterError("PM resume decision requires runtime-required role bindings ready")
    pm_current_agent_id = _active_agent_id_for_role(run_root, "project_manager")
    if not pm_current_agent_id:
        raise RouterError("PM resume decision requires current project_manager role binding")
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
                "role_binding_ledger": project_relative(project_root, run_root / "role_binding_ledger.json"),
                "role_binding_memory": project_relative(project_root, run_root / "role_binding_memory"),
                "role_binding_recovery_report": project_relative(project_root, rehydration_path),
                "pm_prior_path_context": project_relative(project_root, _pm_prior_path_context_path(run_root)),
                "route_history_index": project_relative(project_root, _route_history_index_path(run_root)),
            },
            "role_binding_recovery_report": {
                "path": project_relative(project_root, rehydration_path),
                "required_role_bindings_ready": bool(rehydration_report.get("required_role_bindings_ready")),
                "current_run_memory_complete": bool(rehydration_report.get("current_run_memory_complete")),
                "pm_memory_rehydrated": bool(rehydration_report.get("pm_memory_rehydrated")),
                "missing_memory_role_keys": rehydration_report.get("missing_memory_role_keys") or [],
            },
            "pm_current_role_binding": {
                "role_key": "project_manager",
                "agent_id": pm_current_agent_id,
                "source": "role_binding_ledger",
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
    if decision == "break_glass":
        decision_path = _resume_decision_path(run_root)
        decision_hash = hashlib.sha256(decision_path.read_bytes()).hexdigest()
        run_state["pm_resume_break_glass"] = {
            "schema_version": "flowpilot.pm_resume_break_glass.v1",
            "status": "control_plane_blocker_requested",
            "source_decision_path": project_relative(project_root, decision_path),
            "source_decision_hash": decision_hash,
            "reason": "pm_resume_break_glass",
            "created_at": utc_now(),
        }
        _bound_router()._write_control_blocker(
            project_root,
            run_root,
            run_state,
            source="pm_resume_break_glass",
            error_message=(
                "PM requested break_glass during resume because current-run evidence shows the "
                "FlowPilot control plane cannot form a legal resume next action."
            ),
            event="pm_resume_recovery_decision_returned",
            action_type="pm_resume_recovery_decision",
            payload={
                "decision_path": project_relative(project_root, decision_path),
                "decision_hash": decision_hash,
            },
        )
    return decision

__all__ = (
    '_write_pm_resume_decision',
)

_LOCAL_NAMES = set(globals())
