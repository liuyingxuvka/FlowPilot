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
from flowpilot_router_expected_waits_events import (
    _event_is_router_internal_postcondition,
    _event_wait_role,
    _pending_expected_external_event_groups,
    _run_state_has_event,
)

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
OWNER_MODULE = "flowpilot_router_expected_waits"
def _next_model_miss_followup_request_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    followup = _model_miss_followup_expectation(run_state)
    if followup is None:
        return None
    index = _load_pm_role_work_request_index(run_root, run_state)
    if _active_pm_role_work_request(index) is not None:
        return None
    kind = str(followup.get("required_request_kind") or "model_miss")
    return _expected_role_decision_wait_action(
        project_root,
        run_state,
        run_root,
        label=f"pm_{kind}_triage_waits_for_generic_role_work_request",
        summary=(
            "PM chose to gather more information before repair. Controller must wait for PM to register "
            "a generic role-work request; Controller may not reopen the same model-miss decision loop."
        ),
        allowed_external_events=[PM_ROLE_WORK_REQUEST_EVENT],
        to_role="project_manager",
        payload_contract={
            "schema_version": PAYLOAD_CONTRACT_SCHEMA,
            "name": "pm_role_work_request",
            "required_fields": [
                "requested_by_role",
                "request_id",
                "to_role",
                "request_mode",
                "request_kind",
                "output_contract_id",
                "packet_body_path",
                "packet_body_hash",
            ],
            "allowed_values": {
                "requested_by_role": ["project_manager"],
                "to_role": sorted(PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES),
                "request_mode": sorted(PM_ROLE_WORK_REQUEST_MODES),
                "request_kind": sorted(PM_ROLE_WORK_REQUEST_KINDS),
            },
            "pending_followup": followup,
        },
    )
def _next_model_miss_controlled_stop_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    stop = run_state.get("model_miss_triage_controlled_stop")
    if not isinstance(stop, dict) or stop.get("status") != "waiting_for_user":
        return None
    return make_action(
        action_type="await_user_after_model_miss_stop",
        actor="controller",
        label="model_miss_triage_controlled_stop",
        summary="PM stopped the model-miss triage path for user input; Controller must wait and must not loop the same PM event.",
        allowed_reads=[project_relative(project_root, run_state_path(run_root))],
        allowed_writes=[],
        to_role="user",
        extra={
            "requires_user": True,
            "apply_required": False,
            "model_miss_triage_controlled_stop": stop,
        },
    )
def _expected_role_decision_wait_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    label: str,
    summary: str,
    allowed_external_events: list[str],
    to_role: str,
    payload_contract: dict[str, Any] | None = None,
    allowed_reads_extra: list[str] | None = None,
    pm_work_request_channel: bool = True,
    producer_roles_override: list[str] | None = None,
    gate_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role_output_events = list(allowed_external_events)
    route_action_event_present = any(_route_action_for_event(event) for event in role_output_events)
    if route_action_event_present:
        pm_work_request_channel = False
    role_output_status_packet_path = _role_output_status_packet_path_for_wait(
        project_root,
        run_root,
        to_role=to_role,
        allowed_events=role_output_events,
        payload_contract=payload_contract,
    )
    if role_output_status_packet_path and payload_contract is not None:
        payload_contract = dict(payload_contract)
        structural = list(payload_contract.get("structural_requirements") or [])
        structural.append(
            "Maintain role-output progress through flowpilot_runtime.py progress-output; progress is metadata-only and is not pass/fail evidence."
        )
        payload_contract["structural_requirements"] = structural
        payload_contract["progress_status"] = {
            "default_progress_required": True,
            "controller_status_packet_path": role_output_status_packet_path,
            "runtime_command": "flowpilot_runtime.py progress-output",
            "controller_visibility": "metadata_only",
            "progress_is_decision_evidence": False,
        }
    allowed_events = list(allowed_external_events)
    if pm_work_request_channel and to_role == "project_manager" and PM_ROLE_WORK_REQUEST_EVENT not in allowed_events:
        allowed_events.append(PM_ROLE_WORK_REQUEST_EVENT)
    allowed_events = _validated_event_capability_names(
        allowed_events,
        context=f"await_role_decision action {label}",
        run_root=run_root,
        run_state=run_state,
        usage="wait",
    )
    if producer_roles_override is None:
        _validate_wait_event_producer_binding(
            allowed_events,
            to_role=to_role,
            context=f"await_role_decision action {label}",
        )
    else:
        producer_roles = {str(role) for role in producer_roles_override if str(role)}
        target_roles = _role_set(to_role)
        if producer_roles and not producer_roles.issubset(target_roles):
            raise RouterError(
                f"await_role_decision action {label} waits for event producer role(s) {sorted(producer_roles)} "
                f"but targets {sorted(target_roles)}"
            )
    extra: dict[str, Any] = {
        "allowed_external_events": allowed_events,
        "controller_only_mode_active": True,
        "controller_may_create_project_evidence": False,
        "expected_wait_is_not_control_blocker": True,
    }
    if route_action_event_present:
        extra["legal_next_actions"] = _legal_next_action_context(project_root, run_root, run_state)
        extra["pm_may_choose_only_from_legal_next_actions"] = True
        extra["pm_role_work_request_channel_available"] = False
    if producer_roles_override is not None:
        extra["expected_event_producer_roles"] = sorted({str(role) for role in producer_roles_override if str(role)})
    if pm_work_request_channel and to_role == "project_manager":
        extra["pm_work_request_channel_available"] = True
        extra["pm_role_work_request_event"] = PM_ROLE_WORK_REQUEST_EVENT
    if payload_contract is not None:
        extra["payload_contract"] = payload_contract
    public_gate_contract = _public_gate_contract(gate_contract)
    if public_gate_contract is not None:
        extra["gate_contract"] = public_gate_contract
    if role_output_status_packet_path:
        extra["role_output_progress_status"] = {
            "controller_status_packet_path": role_output_status_packet_path,
            "default_progress_required": True,
            "runtime_command": "flowpilot_runtime.py progress-output",
            "controller_visibility": "metadata_only",
            "progress_is_decision_evidence": False,
        }
    allowed_reads = [project_relative(project_root, run_state_path(run_root))]
    if role_output_status_packet_path and role_output_status_packet_path not in allowed_reads:
        allowed_reads.append(role_output_status_packet_path)
    for item in allowed_reads_extra or []:
        if item and item not in allowed_reads:
            allowed_reads.append(item)
    return make_action(
        action_type="await_role_decision",
        actor="controller",
        label=label,
        summary=summary,
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=to_role,
        extra=extra,
    )

def _capability_sync_artifact_path(run_root: Path) -> Path:
    return run_root / "capabilities" / "capability_sync.json"

def _capability_sync_artifact_valid(run_root: Path, run_state: dict[str, Any]) -> bool:
    artifact = read_json_if_exists(_capability_sync_artifact_path(run_root))
    if artifact.get("schema_version") != "flowpilot.capability_evidence_sync.v1":
        return False
    if str(artifact.get("run_id") or "") != str(run_state.get("run_id") or ""):
        return False
    return artifact.get("pm_approved_manifest") is True

def _capability_sync_event_payload(project_root: Path, run_root: Path) -> dict[str, Any]:
    artifact_path = _capability_sync_artifact_path(run_root)
    artifact = read_json_if_exists(artifact_path)
    return {
        "synced_by": "router",
        "router_internal_postcondition": True,
        "capability_sync_path": project_relative(project_root, artifact_path),
        "capability_sync_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest() if artifact_path.exists() else "",
        "source_paths": artifact.get("source_paths") if isinstance(artifact.get("source_paths"), list) else [],
    }

def _record_router_internal_postcondition_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    changed = False
    if not run_state.setdefault("flags", {}).get(flag):
        run_state["flags"][flag] = True
        changed = True
    if not _run_state_has_event(run_state, event):
        run_state.setdefault("events", []).append(
            {
                "event": event,
                "summary": meta["summary"],
                "payload": payload,
                "recorded_at": utc_now(),
                "reconciled_by_router": True,
                "router_internal_postcondition": True,
            }
        )
        changed = True
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source=source,
    )
    changed = changed or bool(wait_closure.get("changed"))
    if changed:
        append_history(
            run_state,
            "router_reconciled_internal_postcondition_event",
            {
                "event": event,
                "flag": flag,
                "source": source,
                "wait_closure": wait_closure,
                "controller_visibility": "metadata_only",
            },
        )
    return {"changed": changed, "wait_closure": wait_closure}

def _reconcile_capability_evidence_internal_postcondition(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    event = "capability_evidence_synced"
    meta = EXTERNAL_EVENTS.get(event, {})
    if not _event_is_router_internal_postcondition(event, meta):
        return {"changed": False}
    required_flag = str(meta.get("requires_flag") or "")
    if required_flag and not run_state.get("flags", {}).get(required_flag):
        return {"changed": False, "reason": "prerequisite_flag_false", "requires_flag": required_flag}
    if not _capability_sync_artifact_valid(run_root, run_state):
        payload = {
            "synced_by": "router",
            "router_internal_postcondition": True,
            "internal_materializer": meta.get("internal_materializer"),
        }
        try:
            _sync_capability_evidence(project_root, run_root, run_state, payload)
        except RouterError as exc:
            required_paths = [
                run_root / "child_skill_gate_manifest.json",
                run_root / "capabilities.json",
                run_root / "child_skill_manifest_pm_approval.json",
            ]
            blocker = _write_control_blocker(
                project_root,
                run_root,
                run_state,
                source="router_internal_postcondition_materialization",
                error_message=str(exc),
                event=event,
                payload={
                    "internal_postcondition": event,
                    "requires_flag": required_flag,
                    "required_paths": [project_relative(project_root, path) for path in required_paths],
                    "missing_paths": [
                        project_relative(project_root, path)
                        for path in required_paths
                        if not path.exists()
                    ],
                },
            )
            return {
                "changed": True,
                "blocked": True,
                "event": event,
                "blocker_id": blocker.get("blocker_id"),
            }
    payload = _capability_sync_event_payload(project_root, run_root)
    result = _record_router_internal_postcondition_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        source="router_internal_postcondition_materialized",
    )
    if result.get("changed"):
        result["event"] = event
    return result

def _reconcile_router_internal_postconditions(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    changed = False
    blocked = False
    reconciled: list[str] = []
    for event, meta in EXTERNAL_EVENTS.items():
        if not _event_is_router_internal_postcondition(event, meta):
            continue
        materializer = str(meta.get("internal_materializer") or "")
        if materializer != "capability_evidence_sync":
            continue
        result = _reconcile_capability_evidence_internal_postcondition(project_root, run_state, run_root)
        changed = changed or bool(result.get("changed"))
        blocked = blocked or bool(result.get("blocked"))
        if result.get("event"):
            reconciled.append(str(result["event"]))
    if changed:
        save_run_state(run_root, run_state)
    return {"changed": changed, "blocked": blocked, "events": reconciled}

def _next_expected_role_decision_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    internal_reconciliation = _reconcile_router_internal_postconditions(project_root, run_state, run_root)
    if internal_reconciliation.get("blocked"):
        blocker_action = _next_control_blocker_action(project_root, run_state, run_root)
        if blocker_action is not None:
            return blocker_action
    pending_groups = _pending_expected_external_event_groups(run_state, run_root)
    if not pending_groups:
        return None
    for group in pending_groups:
        group = _gate_completion_wait_group(group)
        group_events = [event for event, _meta in group]
        allowed_events = _filter_events_by_legal_route_actions(project_root, run_root, run_state, group_events)
        if not allowed_events:
            continue
        allowed_event_set = set(allowed_events)
        filtered_group = [(event, meta) for event, meta in group if event in allowed_event_set]
        roles = sorted({_event_wait_role(event, meta) for event, meta in filtered_group})
        required_flag = str(filtered_group[0][1].get("requires_flag") or "")
        role_label = roles[0] if len(roles) == 1 else ",".join(roles)
        safe_event_label = "_or_".join(allowed_events).replace("-", "_")
        route_action_wait = any(_route_action_for_event(event) for event in allowed_events)
        return _expected_role_decision_wait_action(
            project_root,
            run_state,
            run_root,
            label=f"controller_waits_for_expected_event_{safe_event_label}",
            summary=(
                f"Prerequisite {required_flag} is satisfied and no controller action is due. "
                f"Controller must wait for expected external event(s): {', '.join(allowed_events)}."
            ),
            allowed_external_events=allowed_events,
            to_role=role_label,
            payload_contract=_role_decision_payload_contract_for_events(project_root, run_root, allowed_events),
            pm_work_request_channel=not route_action_wait,
            gate_contract=_gate_contract_for_events(allowed_events),
        )
    return None
__all__ = (
    "_next_model_miss_followup_request_wait_action",
    "_next_model_miss_controlled_stop_action",
    "_expected_role_decision_wait_action",
    "_reconcile_router_internal_postconditions",
    "_next_expected_role_decision_wait_action",
)
_LOCAL_NAMES = set(globals())
