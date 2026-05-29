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
OWNER_MODULE = "flowpilot_router_expected_waits"
def _reconcile_pending_role_wait_from_packet_status(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending_action: object,
) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or "worker_current_node_result_returned" not in allowed_events:
        return None
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    meta = EXTERNAL_EVENTS["worker_current_node_result_returned"]
    required_flag = str(meta.get("requires_flag") or "")
    if required_flag and not flags.get(required_flag):
        return None
    if flags.get(meta["flag"]):
        return None
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json")
    status = str(packet_ledger.get("active_packet_status") or "")
    if status not in {"worker-result-needs-review", "result-envelope-returned", "router-next-action-ready-for-controller"}:
        return None
    record = _active_packet_ledger_record(packet_ledger)
    if not isinstance(record, dict):
        return None
    packet_id = str(record.get("packet_id") or packet_ledger.get("active_packet_id") or "")
    if not packet_id:
        return None
    result_path = _result_envelope_path_from_packet_record(project_root, run_state, record)
    if not result_path.exists():
        return None
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state["run_id"]))
    status_packet = read_json_if_exists(paths["controller_status_packet"])
    if status_packet.get("schema_version") != "flowpilot.controller_status_packet.v1":
        return None
    if status_packet.get("status") not in {"result-envelope-returned", "router-next-action-ready-for-controller"}:
        return None
    result = packet_runtime.load_envelope(project_root, result_path)
    if result.get("next_recipient") != "project_manager":
        return None
    result_hash = packet_runtime.sha256_file(result_path)
    payload = {
        "packet_id": packet_id,
        "result_envelope_path": project_relative(project_root, result_path),
        "result_envelope_hash": result_hash,
        "reconciled_from_packet_ledger": True,
        "reconciled_from_controller_status_packet": True,
    }
    _validate_current_node_result_event(project_root, run_state, payload)
    event = "worker_current_node_result_returned"
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        wait_closure = _close_waiting_controller_actions_for_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
            payload=payload,
            source="already_reconciled_packet_status_event",
        )
        if not wait_closure.get("changed"):
            return None
        return {
            "event": event,
            "packet_id": packet_id,
            "result_envelope_path": payload["result_envelope_path"],
            "packet_status": status,
            "already_recorded": True,
            "wait_closure": wait_closure,
        }
    run_state["flags"][meta["flag"]] = True
    run_state["events"].append(
        {
            "event": event,
            "summary": meta["summary"],
            "payload": payload,
            "recorded_at": utc_now(),
            "reconciled_by_router": True,
        }
    )
    _mark_scoped_event_recorded(run_state, scoped_identity)
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="router_reconciled_pending_role_wait_from_packet_status",
    )
    append_history(
        run_state,
        "router_reconciled_pending_role_wait_from_packet_status",
        {
            "event": event,
            "packet_id": packet_id,
            "packet_status": status,
            "result_envelope_path": payload["result_envelope_path"],
            "status_packet_checked": True,
            "wait_closure": wait_closure,
        },
    )
    return {
        "event": event,
        "packet_id": packet_id,
        "result_envelope_path": payload["result_envelope_path"],
        "packet_status": status,
    }

def _record_router_reconciled_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    from flowpilot_router_expected_waits_reconciliation_pm_package import (
        _record_router_reconciled_external_event as _record_pm_package_event,
    )

    return _record_pm_package_event(_bound_router(), project_root, run_root, run_state, event, payload)
def _try_reconcile_material_scan_body_delivery(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_body_delivery(_bound_router(), project_root, run_root, run_state)
def _try_reconcile_material_scan_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_results(_bound_router(), project_root, run_root, run_state)
def _try_reconcile_research_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_research_results(_bound_router(), project_root, run_root, run_state)
def _try_reconcile_current_node_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_current_node_results(_bound_router(), project_root, run_root, run_state)
def _try_reconcile_pm_role_work_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_pm_role_work_results(_bound_router(), project_root, run_root, run_state)
__all__ = (
    "_reconcile_pending_role_wait_from_packet_status",
    "_record_router_reconciled_external_event",
    "_try_reconcile_material_scan_body_delivery",
    "_try_reconcile_material_scan_results",
    "_try_reconcile_research_results",
    "_try_reconcile_current_node_results",
    "_try_reconcile_pm_role_work_results",
)
_LOCAL_NAMES = set(globals())
