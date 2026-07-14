"""Dispatch gate card and output-event classification helpers."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_protocol_dispatch_policy import (
    DISPATCH_RECIPIENT_GATE_ACTION_OUTPUT_EVENTS,
    DISPATCH_RECIPIENT_GATE_CONTEXT_CARD_OUTPUT_EVENTS,
)
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
                "expected_first_output_event": "pm_writes_product_function_architecture",
            }
    return None


__all__ = (
    '_dispatch_gate_card_entry',
    '_dispatch_gate_output_events_for_card_id',
    '_dispatch_gate_output_events_for_action',
    '_dispatch_gate_action_is_ack_only_prompt',
    '_dispatch_gate_action_work_class',
    '_dispatch_gate_same_obligation_instruction_context',
)

_LOCAL_NAMES = set(globals())
