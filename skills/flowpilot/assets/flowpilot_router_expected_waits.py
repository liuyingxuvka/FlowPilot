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

def _event_wait_role(event: str, meta: dict[str, str]) -> str:
    del meta
    if event.startswith("pm_"):
        return "project_manager"
    if event.startswith("reviewer_") or event.startswith("current_node_reviewer_"):
        return "human_like_reviewer"
    if event.startswith("product_officer_"):
        return "product_flowguard_officer"
    if event.startswith("process_officer_"):
        return "process_flowguard_officer"
    if event.startswith("worker_"):
        return "worker_a"
    if event.startswith("host_"):
        return "host"
    if event.startswith("controller_") or event in {"capability_evidence_synced"}:
        return "controller"
    if event == "research_capability_decision_recorded":
        return "project_manager"
    return "project_manager"

def _active_node_children_status(run_root: Path | None) -> bool | None:
    if run_root is None:
        return None
    try:
        frontier = _active_frontier(run_root)
        return _active_node_has_children(run_root, frontier)
    except (OSError, KeyError, RouterError, json.JSONDecodeError, ValueError, TypeError):
        return None

def _event_applicable_for_active_node(meta: dict[str, Any], active_node_has_children: bool | None) -> bool:
    if active_node_has_children is None:
        return True
    if meta.get("requires_active_node_children") and not active_node_has_children:
        return False
    if meta.get("forbids_active_node_children") and active_node_has_children:
        return False
    return True

def _pending_expected_external_event_groups(
    run_state: dict[str, Any],
    run_root: Path | None = None,
) -> list[list[tuple[str, dict[str, Any]]]]:
    flags = run_state["flags"]
    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    ordered_requires: list[str] = []
    active_node_has_children = _active_node_children_status(run_root)
    for event, meta in EXTERNAL_EVENTS.items():
        required_flag = meta.get("requires_flag")
        if not required_flag:
            continue
        if not _event_applicable_for_active_node(meta, active_node_has_children):
            continue
        if required_flag not in grouped:
            grouped[required_flag] = []
            ordered_requires.append(required_flag)
        grouped[required_flag].append((event, meta))

    def group_already_has_terminal_outcome(group: list[tuple[str, dict[str, Any]]]) -> bool:
        recorded_events = [
            event
            for event, meta in group
            if flags.get(meta["flag"]) and _event_is_terminal_gate_outcome(event, meta)
        ]
        if not recorded_events:
            return False
        recorded_blocks = [event for event in recorded_events if event in GATE_OUTCOME_BLOCK_EVENTS]
        if recorded_blocks:
            pass_events = [
                event
                for event, meta in group
                if event in GATE_OUTCOME_PASS_CLEAR_FLAGS and not flags.get(meta["flag"])
            ]
            if pass_events:
                return False
        return True

    pending: list[list[tuple[str, dict[str, Any]]]] = []
    for required_flag in ordered_requires:
        if not flags.get(required_flag):
            continue
        if required_flag == "pm_control_blocker_repair_decision_recorded" and not isinstance(
            run_state.get("active_control_blocker"), dict
        ):
            continue
        group = grouped[required_flag]
        if group_already_has_terminal_outcome(group):
            continue
        pending.append(group)
    return pending

def _next_expected_role_decision_wait_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
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

def _pending_role_decision_staleness(run_state: dict[str, Any], pending_action: object) -> dict[str, Any] | None:
    if not isinstance(pending_action, dict) or pending_action.get("action_type") != "await_role_decision":
        return None
    allowed_events = pending_action.get("allowed_external_events")
    if not isinstance(allowed_events, list) or not allowed_events:
        return {
            "reason": "await_role_decision_missing_allowed_external_events",
            "action_type": pending_action.get("action_type"),
            "label": pending_action.get("label"),
        }
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    invalid_events: list[dict[str, Any]] = []
    normalized_events: list[str] = []
    for item in allowed_events:
        if not isinstance(item, str):
            invalid_events.append({"issue": "non_string_allowed_external_event", "event": repr(item)})
            continue
        normalized_events.append(item)
        meta = EXTERNAL_EVENTS.get(item)
        if not isinstance(meta, dict):
            invalid_events.append({"issue": "unknown_external_event", "event": item})
            continue
        required_flag = meta.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            invalid_events.append(
                {
                    "issue": "requires_flag_false",
                    "event": item,
                    "requires_flag": required_flag,
                    "current_value": flags.get(required_flag),
                }
            )
    if not invalid_events:
        return None
    return {
        "reason": "await_role_decision_allowed_event_not_currently_receivable",
        "action_type": pending_action.get("action_type"),
        "label": pending_action.get("label"),
        "allowed_external_events": normalized_events,
        "invalid_allowed_external_events": invalid_events,
    }

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
    meta = EXTERNAL_EVENTS[event]
    flag = str(meta["flag"])
    repeatable = event in {ROLE_WORK_RESULT_RETURNED_EVENT, "worker_current_node_result_returned"}
    scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        return False
    if run_state.setdefault("flags", {}).get(flag) and not repeatable:
        return False
    run_state["flags"][flag] = True
    run_state.setdefault("events", []).append(
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
        source="router_reconciled_external_event",
    )
    append_history(
        run_state,
        f"router_reconciled_{event}",
        {
            "event": event,
            "payload": payload,
            "controller_visibility": "metadata_only",
            "wait_closure": wait_closure,
        },
    )
    return True

def _try_reconcile_material_scan_body_delivery(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_body_delivery(_bound_router(), project_root, run_root, run_state)

def _try_reconcile_material_scan_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_material_scan_results(_bound_router(), project_root, run_root, run_state)

def _try_reconcile_current_node_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_current_node_results(_bound_router(), project_root, run_root, run_state)

def _try_reconcile_pm_role_work_results(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return flowpilot_router_work_packets._try_reconcile_pm_role_work_results(_bound_router(), project_root, run_root, run_state)

def _run_state_has_event(run_state: dict[str, Any], event: str) -> bool:
    return any(
        isinstance(item, dict) and item.get("event") == event
        for item in (run_state.get("events") or [])
    )

_LOCAL_NAMES = set(globals())
