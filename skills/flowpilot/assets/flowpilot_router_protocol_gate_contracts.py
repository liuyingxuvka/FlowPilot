"""Gate contract lookup tables and helpers extracted from ``flowpilot_router_protocol_catalog.py``."""

from __future__ import annotations

from typing import Any, Iterable

import flowpilot_runtime_closure
import packet_runtime
import role_output_runtime

from flowpilot_router_protocol_schemas import *
from flowpilot_router_protocol_control_repair import *
from flowpilot_router_protocol_work_contracts import *
from flowpilot_router_protocol_decision_tables import *
from flowpilot_router_protocol_boot_cards import *
from flowpilot_router_protocol_external_events import *
from flowpilot_router_protocol_gate_outcomes import *

GATE_CONTRACT_SCHEMA = "flowpilot.gate_contract.v1"

GATE_CONTRACTS: dict[str, dict[str, Any]] = {
    "product_behavior_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "product_behavior_model",
        "card_id": "product_officer.product_architecture_modelability",
        "required_flag": "product_behavior_model_submitted",
        "wait_requires_flag": "product_officer_product_architecture_card_delivered",
        "target_role": "product_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "product_officer_submits_product_behavior_model",
        ),
        "block_events": (
            "product_officer_blocks_product_behavior_model",
        ),
        "completion_rule": "pass_or_block_event_required",
        "canonical_artifact": "flowguard/product_behavior_model.json",
    },
    "process_route_model": {
        "schema_version": GATE_CONTRACT_SCHEMA,
        "gate_id": "process_route_model",
        "card_id": "process_officer.route_process_check",
        "required_flag": "process_route_model_submitted",
        "wait_requires_flag": "process_officer_route_check_card_delivered",
        "target_role": "process_flowguard_officer",
        "output_contract_id": "flowpilot.output_contract.officer_model_report.v1",
        "pass_events": (
            "process_officer_submits_process_route_model",
        ),
        "block_events": (
            "process_officer_requests_process_route_model_repair",
            "process_officer_blocks_process_route_model",
        ),
        "completion_rule": "pass_repair_or_block_event_required",
        "canonical_artifact": "flowguard/process_route_model.json",
    },
}

GATE_CONTRACTS_BY_CARD = {
    str(contract["card_id"]): gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
}

GATE_CONTRACTS_BY_EVENT = {
    event: gate_id
    for gate_id, contract in GATE_CONTRACTS.items()
    for event in (
        *contract.get("pass_events", ()),
        *contract.get("block_events", ()),
    )
}

def _public_gate_contract(contract: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(contract, dict):
        return None
    public = dict(contract)
    for key in ("pass_events", "block_events"):
        public[key] = list(public.get(key) or [])
    return public

def _gate_contract_for_id(gate_id: str | None) -> dict[str, Any] | None:
    if not gate_id:
        return None
    key = str(gate_id)
    return GATE_CONTRACTS.get(key)

def _gate_contract_for_card(card_id: str | None) -> dict[str, Any] | None:
    if not card_id:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_CARD.get(str(card_id)))

def _gate_contract_for_event(event: str | None) -> dict[str, Any] | None:
    if not event:
        return None
    return _gate_contract_for_id(GATE_CONTRACTS_BY_EVENT.get(str(event)))

def _gate_contract_for_events(events: Iterable[str]) -> dict[str, Any] | None:
    gate_ids = {
        GATE_CONTRACTS_BY_EVENT[str(event)]
        for event in events
        if str(event) in GATE_CONTRACTS_BY_EVENT
    }
    if len(gate_ids) == 1:
        return _gate_contract_for_id(next(iter(gate_ids)))
    return None

def _event_is_terminal_gate_outcome(event: str, meta: dict[str, Any]) -> bool:
    if meta.get("terminal_gate_outcome") is False:
        return False
    contract = _gate_contract_for_event(event)
    if contract is None:
        return True
    return event in set(contract.get("pass_events") or ()) | set(contract.get("block_events") or ())

def _gate_completion_wait_group(group: list[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    if not _gate_contract_for_events(event for event, _meta in group):
        return group
    terminal_group = [
        (event, meta)
        for event, meta in group
        if _event_is_terminal_gate_outcome(event, meta)
    ]
    return terminal_group or group

PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS = frozenset(
    {
        "product_officer_submits_product_behavior_model",
    }
)

PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS = frozenset(
    {
        "product_officer_blocks_product_behavior_model",
    }
)

PROCESS_ROUTE_MODEL_PASS_EVENTS = frozenset(
    {
        "process_officer_submits_process_route_model",
    }
)

PROCESS_ROUTE_MODEL_REPAIR_EVENTS = frozenset(
    {
        "process_officer_requests_process_route_model_repair",
    }
)

PROCESS_ROUTE_MODEL_BLOCK_EVENTS = frozenset(
    {
        "process_officer_blocks_process_route_model",
    }
)

__all__ = (
    'GATE_CONTRACT_SCHEMA',
    'GATE_CONTRACTS',
    'GATE_CONTRACTS_BY_CARD',
    'GATE_CONTRACTS_BY_EVENT',
    '_public_gate_contract',
    '_gate_contract_for_id',
    '_gate_contract_for_card',
    '_gate_contract_for_event',
    '_gate_contract_for_events',
    '_event_is_terminal_gate_outcome',
    '_gate_completion_wait_group',
    'PRODUCT_BEHAVIOR_MODEL_PASS_EVENTS',
    'PRODUCT_BEHAVIOR_MODEL_BLOCK_EVENTS',
    'PROCESS_ROUTE_MODEL_PASS_EVENTS',
    'PROCESS_ROUTE_MODEL_REPAIR_EVENTS',
    'PROCESS_ROUTE_MODEL_BLOCK_EVENTS',
)
