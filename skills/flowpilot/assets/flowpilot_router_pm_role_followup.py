"""Router skeleton owner helpers for flowpilot_router_pm_role_followup.

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


OWNER_MODULE = 'flowpilot_router_pm_role_followup'

def _pm_role_work_channel_open(run_state: dict[str, Any]) -> bool:
    if run_state.get("flags", {}).get("model_miss_triage_followup_request_pending"):
        return True
    pending = run_state.get("pending_action")
    if isinstance(pending, dict) and pending.get("action_type") == "await_role_decision":
        to_role = str(pending.get("to_role") or "")
        if "project_manager" in {part.strip() for part in to_role.split(",")}:
            return True
        allowed = pending.get("allowed_external_events")
        if isinstance(allowed, list) and any(str(item).startswith("pm_") for item in allowed):
            return True
    for group in _pending_expected_external_event_groups(run_state):
        roles = {_event_wait_role(event, meta) for event, meta in group}
        if "project_manager" in roles:
            return True
    return False

def _model_miss_followup_expectation(run_state: dict[str, Any]) -> dict[str, Any] | None:
    followup = run_state.get("model_miss_triage_followup_request")
    if isinstance(followup, dict) and followup.get("status") == "awaiting_pm_role_work_request":
        return followup
    followup = run_state.get("model_miss_evidence_followup_request")
    if isinstance(followup, dict) and followup.get("status") == "awaiting_pm_role_work_request":
        return followup
    return None

def _validate_pm_role_work_request_against_followup(
    run_state: dict[str, Any],
    *,
    request_id: str,
    to_role: str,
    request_kind: str,
    output_contract_id: str,
) -> None:
    followup = _model_miss_followup_expectation(run_state)
    if followup is None:
        return
    required_kind = str(followup.get("required_request_kind") or "").strip()
    if required_kind and request_kind != required_kind:
        raise RouterError(f"PM role-work request must use request_kind={required_kind} for the pending model-miss follow-up")
    required_contract = str(followup.get("required_output_contract_id") or "").strip()
    if required_contract and output_contract_id != required_contract:
        raise RouterError(f"PM role-work request must use output_contract_id={required_contract} for the pending model-miss follow-up")
    allowed_roles = followup.get("suggested_to_roles")
    if isinstance(allowed_roles, list) and allowed_roles and to_role not in allowed_roles:
        raise RouterError("PM role-work request targets a role outside the pending model-miss follow-up roles")
    followup["status"] = "request_registered"
    followup["request_id"] = request_id
    followup["registered_at"] = utc_now()
    if run_state.get("model_miss_triage_followup_request") is followup:
        run_state["model_miss_triage_followup_request"] = followup
    if run_state.get("model_miss_evidence_followup_request") is followup:
        run_state["model_miss_evidence_followup_request"] = followup
    run_state["flags"]["model_miss_triage_followup_request_pending"] = False

_LOCAL_NAMES = set(globals())
