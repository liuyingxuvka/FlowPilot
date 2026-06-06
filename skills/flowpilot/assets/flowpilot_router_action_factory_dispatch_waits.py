"""Dispatch gate wait-action helpers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_protocol_catalog import *

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



OWNER_MODULE = "flowpilot_router_action_factory_dispatch"


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


__all__ = (
    '_dispatch_gate_wait_action',
    '_dispatch_gate_pending_ack_wait',
)

_LOCAL_NAMES = set(globals())
