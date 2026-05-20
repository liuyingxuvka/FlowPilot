"""Dispatch gate blocker detectors."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_closure_kernel
from flowpilot_router_protocol_catalog import *

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



OWNER_MODULE = "flowpilot_router_action_factory_dispatch"


def _dispatch_gate_packet_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
    candidate_packet_ids: set[str],
) -> dict[str, Any] | None:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return None
    packet_ledger_path = run_root / "packet_ledger.json"
    packet_ledger = read_json_if_exists(packet_ledger_path)
    packets = packet_ledger.get("packets") if isinstance(packet_ledger, dict) else []
    if not isinstance(packets, list):
        return None
    for record in packets:
        if not isinstance(record, dict):
            continue
        packet_id = str(record.get("packet_id") or "").strip()
        if packet_id and packet_id in candidate_packet_ids:
            continue
        if _dispatch_gate_packet_completed_by_flow_state(record, run_state):
            continue
        holder = str(record.get("active_packet_holder") or "").strip()
        status = str(record.get("active_packet_status") or record.get("status") or "").strip()
        if holder not in target_roles or not flowpilot_closure_kernel.closure_blocks_progress("packet_holder", record):
            continue
        if _dispatch_gate_same_obligation_instruction(action, record, run_state):
            continue
        return {
            "source": "packet_ledger",
            "source_path": project_relative(project_root, packet_ledger_path),
            "reason": "target_role_holds_unfinished_packet",
            "target_role": holder,
            "packet_id": packet_id or None,
            "active_packet_status": status,
            "blocked_work_package_class": _dispatch_gate_action_work_class(action),
            "blocked_output_events": _dispatch_gate_output_events_for_action(action),
            "allowed_external_events": _dispatch_gate_wait_events_for_packet_record(record),
        }
    return None


def _dispatch_gate_pending_expected_output_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return None
    candidate_output_events = set(_dispatch_gate_output_events_for_action(action))
    for group in _pending_expected_external_event_groups(run_state, run_root):
        wait_group = _gate_completion_wait_group(group)
        group_events = [event for event, _meta in wait_group]
        allowed_events = _filter_events_by_legal_route_actions(project_root, run_root, run_state, group_events)
        if not allowed_events:
            continue
        allowed_event_set = set(allowed_events)
        filtered_group = [(event, meta) for event, meta in wait_group if event in allowed_event_set]
        roles = {_event_wait_role(event, meta) for event, meta in filtered_group}
        overlapping_roles = roles.intersection(target_roles)
        if not overlapping_roles:
            continue
        if candidate_output_events and candidate_output_events.intersection(allowed_event_set):
            continue
        target_role = sorted(overlapping_roles)[0]
        return {
            "source": "pending_expected_output",
            "source_path": project_relative(project_root, run_state_path(run_root)),
            "reason": "target_role_output_obligation_already_pending",
            "target_role": target_role,
            "blocked_work_package_class": _dispatch_gate_action_work_class(action),
            "blocked_output_events": sorted(candidate_output_events),
            "allowed_external_events": allowed_events,
        }
    return None


def _dispatch_gate_pm_role_work_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
    candidate_packet_ids: set[str],
    candidate_request_ids: set[str],
) -> dict[str, Any] | None:
    index_path = _pm_role_work_request_index_path(run_root)
    index = _load_pm_role_work_request_index(run_root, run_state)
    candidate_superseded_request_ids: set[str] = set()
    candidate_superseded_packet_ids: set[str] = set()
    action_supersedes_request_id = str(action.get("supersedes_request_id") or action.get("replacement_for_request_id") or "").strip()
    if action_supersedes_request_id:
        candidate_superseded_request_ids.add(action_supersedes_request_id)
    raw_action_supersedes_request_ids = action.get("supersedes_request_ids")
    if isinstance(raw_action_supersedes_request_ids, list):
        candidate_superseded_request_ids.update(str(item).strip() for item in raw_action_supersedes_request_ids if str(item).strip())
    action_supersedes_packet_id = str(action.get("replacement_for_packet_id") or action.get("replacement_for") or "").strip()
    if action_supersedes_packet_id:
        candidate_superseded_packet_ids.add(action_supersedes_packet_id)
    raw_action_supersedes_packet_ids = action.get("supersedes_packet_ids") or action.get("supersedes")
    if isinstance(raw_action_supersedes_packet_ids, list):
        candidate_superseded_packet_ids.update(str(item).strip() for item in raw_action_supersedes_packet_ids if str(item).strip())
    for record in index.get("requests", []):
        if not isinstance(record, dict):
            continue
        request_id = str(record.get("request_id") or "").strip()
        packet_id = str(record.get("packet_id") or "").strip()
        if (request_id and request_id in candidate_request_ids) or (packet_id and packet_id in candidate_packet_ids):
            for field in ("supersedes_request_ids", "supersedes_requests"):
                raw = record.get(field)
                if isinstance(raw, list):
                    candidate_superseded_request_ids.update(str(item).strip() for item in raw if str(item).strip())
            replacement_request_id = str(record.get("replacement_for_request_id") or record.get("supersedes_request_id") or "").strip()
            if replacement_request_id:
                candidate_superseded_request_ids.add(replacement_request_id)
            for field in ("supersedes_packet_ids", "supersedes"):
                raw = record.get(field)
                if isinstance(raw, list):
                    candidate_superseded_packet_ids.update(str(item).strip() for item in raw if str(item).strip())
            replacement_packet_id = str(record.get("replacement_for_packet_id") or record.get("replacement_for") or "").strip()
            if replacement_packet_id:
                candidate_superseded_packet_ids.add(replacement_packet_id)
    for record in index.get("requests", []):
        if not isinstance(record, dict):
            continue
        request_id = str(record.get("request_id") or "").strip()
        packet_id = str(record.get("packet_id") or "").strip()
        if (request_id and request_id in candidate_request_ids) or (packet_id and packet_id in candidate_packet_ids):
            continue
        if request_id and request_id in candidate_superseded_request_ids:
            continue
        if packet_id and packet_id in candidate_superseded_packet_ids:
            continue
        superseded_by = str(record.get("superseded_by_request_id") or record.get("replacement_request_id") or "").strip()
        if superseded_by and superseded_by in candidate_request_ids:
            continue
        status = str(record.get("status") or "").strip()
        to_role = str(record.get("to_role") or "").strip()
        target_closure = flowpilot_closure_kernel.classify_closure("pm_role_work_target", record)
        if to_role in target_roles and target_closure.blocks_progress:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "target_role_pm_role_work_unfinished",
                "target_role": to_role,
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
                "closure_classification": target_closure.classification,
                "closure_reason": target_closure.reason,
                "blocked_work_package_class": _dispatch_gate_action_work_class(action),
                "blocked_output_events": _dispatch_gate_output_events_for_action(action),
                "allowed_external_events": [ROLE_WORK_RESULT_RETURNED_EVENT],
            }
        pm_closure = flowpilot_closure_kernel.classify_closure("pm_role_work_pm", record)
        if "project_manager" in target_roles and pm_closure.blocks_progress:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "pm_role_work_result_disposition_pending",
                "target_role": "project_manager",
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
                "closure_classification": pm_closure.classification,
                "closure_reason": pm_closure.reason,
                "blocked_work_package_class": _dispatch_gate_action_work_class(action),
                "blocked_output_events": _dispatch_gate_output_events_for_action(action),
                "allowed_external_events": [PM_ROLE_WORK_RESULT_DECISION_EVENT],
            }
    return None


def _dispatch_gate_passive_wait_blocker(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    _run_router_return_settlement_finalizers(
        project_root,
        run_root,
        run_state,
        source="dispatch_recipient_gate_passive_wait_recheck",
    )
    controller_ledger = _controller_action_ledger_summary(run_root)
    passive_waits = controller_ledger.get("passive_waits") if isinstance(controller_ledger, dict) else []
    if not isinstance(passive_waits, list):
        return None
    for item in passive_waits:
        if not isinstance(item, dict):
            continue
        closure = flowpilot_closure_kernel.classify_closure("controller_passive_wait", item)
        if not closure.blocks_progress:
            continue
        target = str(item.get("waiting_for_role") or item.get("to_role") or item.get("target_role") or "").strip()
        if target not in target_roles:
            continue
        return {
            "source": "controller_action_ledger.passive_waits",
            "source_path": controller_ledger.get("path"),
            "reason": "target_role_wait_already_active",
            "target_role": target,
            "action_id": item.get("action_id"),
            "allowed_external_events": item.get("allowed_external_events") if isinstance(item.get("allowed_external_events"), list) else [],
        }
    return None


__all__ = (
    '_dispatch_gate_packet_blocker',
    '_dispatch_gate_pending_expected_output_blocker',
    '_dispatch_gate_pm_role_work_blocker',
    '_dispatch_gate_passive_wait_blocker',
)

_LOCAL_NAMES = set(globals())
