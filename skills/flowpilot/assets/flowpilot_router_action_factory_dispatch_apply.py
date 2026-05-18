"""Dispatch gate orchestration helper."""

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
    '_apply_dispatch_recipient_gate',
)

_LOCAL_NAMES = set(globals())
