"""Dispatch-recipient gate helpers for router action construction.

This child module groups the gate and blocker helpers that prevent overlapping
work for the same recipient role while keeping the bound-router facade pattern.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

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


def _dispatch_gate_card_entry(card_id: str) -> dict[str, Any] | None:
    return next((entry for entry in SYSTEM_CARD_SEQUENCE if entry.get("card_id") == card_id), None)


def _dispatch_gate_output_events_for_card_id(card_id: str) -> list[str]:
    entry = _dispatch_gate_card_entry(card_id)
    if not isinstance(entry, dict):
        return []
    card_flag = str(entry.get("flag") or "")
    output_events: list[str] = []
    for event, meta in EXTERNAL_EVENTS.items():
        if meta.get("requires_flag") == card_flag:
            output_events.append(event)
    output_events.extend(DISPATCH_RECIPIENT_GATE_CONTEXT_CARD_OUTPUT_EVENTS.get(card_id, ()))
    return list(dict.fromkeys(output_events))


def _dispatch_gate_output_events_for_action(action: dict[str, Any]) -> list[str]:
    output_events: list[str] = []
    for card_id in _dispatch_gate_system_card_ids(action):
        output_events.extend(_dispatch_gate_output_events_for_card_id(card_id))
    output_events.extend(DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS.get(str(action.get("action_type") or ""), ()))
    return list(dict.fromkeys(output_events))


def _dispatch_gate_action_is_ack_only_prompt(action: dict[str, Any]) -> bool:
    if action.get("action_type") not in {"deliver_system_card", "deliver_system_card_bundle"}:
        return False
    card_ids = _dispatch_gate_system_card_ids(action)
    return bool(card_ids) and not _dispatch_gate_output_events_for_action(action)


def _dispatch_gate_action_work_class(action: dict[str, Any]) -> str:
    if _dispatch_gate_action_is_ack_only_prompt(action):
        return "ack_only_prompt"
    if action.get("action_type") in {"deliver_system_card", "deliver_system_card_bundle"}:
        return "output_bearing_work_package"
    return "work_dispatch"


def _dispatch_gate_same_obligation_instruction_context(
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    packet_ledger = read_json_if_exists(run_root / "packet_ledger.json")
    packets = packet_ledger.get("packets") if isinstance(packet_ledger, dict) else []
    if not isinstance(packets, list):
        return None
    for record in packets:
        if not isinstance(record, dict):
            continue
        holder = str(record.get("active_packet_holder") or "").strip()
        status = str(record.get("active_packet_status") or record.get("status") or "").strip()
        if holder not in target_roles or not _packet_status_allows_current_work(status):
            continue
        if _dispatch_gate_same_obligation_instruction(action, record, run_state):
            return {
                "packet_id": record.get("packet_id"),
                "active_packet_holder": holder,
                "instruction_card_id": action.get("card_id"),
                "expected_first_output_event": "pm_issues_material_and_capability_scan_packets",
            }
    return None


def _dispatch_gate_wait_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    *,
    blocked_action: dict[str, Any],
    blocker: dict[str, Any],
) -> dict[str, Any]:
    target_role = str(blocker.get("target_role") or "").strip()
    if not target_role:
        target_role = ",".join(sorted(_dispatch_gate_target_roles(blocked_action))) or "project_manager"
    allowed_events = [str(item) for item in blocker.get("allowed_external_events") or [] if str(item)]
    if not allowed_events:
        if target_role == "project_manager":
            allowed_events = [PM_ROLE_WORK_RESULT_DECISION_EVENT]
        else:
            allowed_events = [ROLE_WORK_RESULT_RETURNED_EVENT]
    source_path = str(blocker.get("source_path") or "").strip()
    allowed_reads = [project_relative(project_root, run_state_path(run_root))]
    if source_path and source_path not in allowed_reads:
        allowed_reads.append(source_path)
    payload_contract = {
        "schema_version": PAYLOAD_CONTRACT_SCHEMA,
        "name": "dispatch_recipient_gate_wait",
        "required_fields": [],
        "blocked_action_type": blocked_action.get("action_type"),
        "blocked_label": blocked_action.get("label"),
        "target_role": target_role,
        "busy_source": blocker.get("source"),
        "busy_reason": blocker.get("reason"),
        "packet_id": blocker.get("packet_id"),
        "request_id": blocker.get("request_id"),
        "blocked_work_package_class": blocker.get("blocked_work_package_class"),
        "blocked_output_events": blocker.get("blocked_output_events") or [],
        "controller_visibility": "metadata_only",
        "sealed_body_reads_allowed": False,
    }
    wait_action = _bound_router().make_action(
        action_type="await_role_decision",
        actor="controller",
        label=f"controller_waits_for_dispatch_recipient_idle_{_safe_delivery_component(target_role)}",
        summary=(
            "Controller must wait because Router blocked a new dispatch until "
            f"{target_role} finishes the prior unfinished obligation."
        ),
        allowed_reads=allowed_reads,
        allowed_writes=[project_relative(project_root, run_state_path(run_root))],
        to_role=target_role,
        extra={
            "allowed_external_events": allowed_events,
            "controller_only_mode_active": True,
            "controller_may_create_project_evidence": False,
            "expected_wait_is_not_control_blocker": True,
            "payload_contract": payload_contract,
            "dispatch_recipient_gate": {
                "schema_version": "flowpilot.dispatch_recipient_gate.v1",
                "passed": False,
                "blocked_action_type": blocked_action.get("action_type"),
                "blocked_label": blocked_action.get("label"),
                "target_role": target_role,
                "busy_source": blocker.get("source"),
                "busy_reason": blocker.get("reason"),
                "packet_id": blocker.get("packet_id"),
                "request_id": blocker.get("request_id"),
                "blocked_work_package_class": blocker.get("blocked_work_package_class"),
                "blocked_output_events": blocker.get("blocked_output_events") or [],
                "source_path": source_path or None,
                "sealed_body_reads_allowed": False,
            },
        },
    )
    wait_action["nonblocking_wait"] = False
    return wait_action


def _dispatch_gate_pending_ack_wait(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
    target_roles: set[str],
) -> dict[str, Any] | None:
    pending = [
        record
        for record in _pending_return_records(run_root, str(run_state["run_id"]))
        if str(record.get("target_role") or "") in target_roles
    ]
    if not pending:
        return None
    wait_action = _bound_router()._next_pending_card_return_action(
        project_root,
        run_state,
        run_root,
        pending,
        clearance_reason="dispatch_recipient_gate",
    )
    if wait_action is None:
        return None
    wait_action["dispatch_recipient_gate"] = {
        "schema_version": "flowpilot.dispatch_recipient_gate.v1",
        "passed": False,
        "blocked_action_type": action.get("action_type"),
        "blocked_label": action.get("label"),
        "target_roles": sorted(target_roles),
        "busy_source": "pending_return_ledger",
        "busy_reason": "target_role_ack_or_bundle_return_unresolved",
        "pending_return_count": len(pending),
        "blocked_work_package_class": _dispatch_gate_action_work_class(action),
        "blocked_output_events": _dispatch_gate_output_events_for_action(action),
        "source_path": project_relative(project_root, _return_event_ledger_path(run_root)),
        "sealed_body_reads_allowed": False,
    }
    wait_action.setdefault("next_step_contract", {})["dispatch_recipient_gate"] = wait_action["dispatch_recipient_gate"]
    return wait_action


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
        if holder not in target_roles or not _packet_status_allows_current_work(status):
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
    for record in index.get("requests", []):
        if not isinstance(record, dict):
            continue
        request_id = str(record.get("request_id") or "").strip()
        packet_id = str(record.get("packet_id") or "").strip()
        if (request_id and request_id in candidate_request_ids) or (packet_id and packet_id in candidate_packet_ids):
            continue
        status = str(record.get("status") or "").strip()
        to_role = str(record.get("to_role") or "").strip()
        if to_role in target_roles and status in PM_ROLE_WORK_TARGET_BUSY_STATUSES:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "target_role_pm_role_work_unfinished",
                "target_role": to_role,
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
                "blocked_work_package_class": _dispatch_gate_action_work_class(action),
                "blocked_output_events": _dispatch_gate_output_events_for_action(action),
                "allowed_external_events": [ROLE_WORK_RESULT_RETURNED_EVENT],
            }
        if "project_manager" in target_roles and status in PM_ROLE_WORK_PM_BUSY_STATUSES:
            return {
                "source": "pm_role_work_index",
                "source_path": project_relative(project_root, index_path),
                "reason": "pm_role_work_result_disposition_pending",
                "target_role": "project_manager",
                "packet_id": packet_id or None,
                "request_id": request_id or None,
                "pm_role_work_status": status,
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
        status = str(item.get("status") or "").strip()
        reconciled = str(item.get("router_reconciliation_status") or "").strip()
        if status in {"done", "resolved", "skipped", "superseded"} or reconciled == "reconciled":
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


def _apply_dispatch_recipient_gate(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    if action.get("action_type") not in DISPATCH_RECIPIENT_GATE_ACTION_TYPES:
        return action
    target_roles = _dispatch_gate_target_roles(action)
    if not target_roles:
        return action
    _run_router_return_settlement_finalizers(
        project_root,
        run_root,
        run_state,
        source="dispatch_recipient_gate_return_settlement",
    )
    candidate_packet_ids = _dispatch_gate_candidate_packet_ids(action)
    candidate_request_ids = _dispatch_gate_candidate_request_ids(action)
    wait_action = _dispatch_gate_pending_ack_wait(project_root, run_state, run_root, action, target_roles)
    if wait_action is not None:
        return wait_action
    blocker = _dispatch_gate_passive_wait_blocker(project_root, run_root, run_state, target_roles)
    same_obligation_instruction = _dispatch_gate_same_obligation_instruction_context(
        run_root,
        run_state,
        action,
        target_roles,
    )
    if blocker is None:
        blocker = _dispatch_gate_pending_expected_output_blocker(project_root, run_root, run_state, action, target_roles)
    if blocker is None:
        blocker = _dispatch_gate_packet_blocker(project_root, run_root, run_state, action, target_roles, candidate_packet_ids)
    if blocker is None and not _dispatch_gate_action_is_ack_only_prompt(action):
        blocker = _dispatch_gate_pm_role_work_blocker(
            project_root,
            run_root,
            run_state,
            action,
            target_roles,
            candidate_packet_ids,
            candidate_request_ids,
        )
    if blocker is None:
        action["dispatch_recipient_gate"] = {
            "schema_version": "flowpilot.dispatch_recipient_gate.v1",
            "passed": True,
            "target_roles": sorted(target_roles),
            "candidate_packet_ids": sorted(candidate_packet_ids),
            "candidate_request_ids": sorted(candidate_request_ids),
            "grouped_delivery": action.get("action_type") == "deliver_system_card_bundle",
            "same_obligation_instruction": same_obligation_instruction,
            "work_package_class": _dispatch_gate_action_work_class(action),
            "output_events": _dispatch_gate_output_events_for_action(action),
            "sealed_body_reads_allowed": False,
        }
        action.setdefault("next_step_contract", {})["dispatch_recipient_gate"] = action["dispatch_recipient_gate"]
        return action
    return _dispatch_gate_wait_action(
        project_root,
        run_state,
        run_root,
        blocked_action=action,
        blocker=blocker,
    )


__all__ = (
    "_dispatch_gate_card_entry",
    "_dispatch_gate_output_events_for_card_id",
    "_dispatch_gate_output_events_for_action",
    "_dispatch_gate_action_is_ack_only_prompt",
    "_dispatch_gate_action_work_class",
    "_dispatch_gate_same_obligation_instruction_context",
    "_dispatch_gate_wait_action",
    "_dispatch_gate_pending_ack_wait",
    "_dispatch_gate_packet_blocker",
    "_dispatch_gate_pending_expected_output_blocker",
    "_dispatch_gate_pm_role_work_blocker",
    "_dispatch_gate_passive_wait_blocker",
    "_apply_dispatch_recipient_gate",
)

_LOCAL_NAMES = set(globals())
