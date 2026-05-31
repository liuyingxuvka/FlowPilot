"""Card delivery and return-ledger helpers for FlowPilot router."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import card_runtime
from flowpilot_router_io import read_json_if_exists, utc_now


CARD_LEDGER_SCHEMA = card_runtime.CARD_LEDGER_SCHEMA
RETURN_EVENT_LEDGER_SCHEMA = card_runtime.RETURN_EVENT_LEDGER_SCHEMA

CARD_RETURN_EVENT_NAMES = frozenset(
    {
        "controller_card_ack",
        "pm_card_ack",
        "reviewer_card_ack",
        "worker_card_ack",
        "flowguard_operator_card_ack",
        "card_ack",
        "controller_card_bundle_ack",
        "pm_card_bundle_ack",
        "reviewer_card_bundle_ack",
        "worker_card_bundle_ack",
        "flowguard_operator_card_bundle_ack",
        "card_bundle_ack",
    }
)


def safe_delivery_component(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value).strip("_") or "item"


def card_ledger_path(run_root: Path) -> Path:
    return run_root / "card_ledger.json"


def return_event_ledger_path(run_root: Path) -> Path:
    return run_root / "return_event_ledger.json"


def empty_card_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": CARD_LEDGER_SCHEMA,
        "run_id": run_id,
        "deliveries": [],
        "read_receipts": [],
        "ack_envelopes": [],
        "updated_at": utc_now(),
    }


def empty_return_event_ledger(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": RETURN_EVENT_LEDGER_SCHEMA,
        "run_id": run_id,
        "pending_returns": [],
        "completed_returns": [],
        "updated_at": utc_now(),
    }


def read_card_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(card_ledger_path(run_root)) or empty_card_ledger(run_id)
    ledger.setdefault("schema_version", CARD_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("deliveries", [])
    ledger.setdefault("read_receipts", [])
    ledger.setdefault("ack_envelopes", [])
    return ledger


def read_return_event_ledger(run_root: Path, run_id: str) -> dict[str, Any]:
    ledger = read_json_if_exists(return_event_ledger_path(run_root)) or empty_return_event_ledger(run_id)
    ledger.setdefault("schema_version", RETURN_EVENT_LEDGER_SCHEMA)
    ledger.setdefault("run_id", run_id)
    ledger.setdefault("pending_returns", [])
    ledger.setdefault("completed_returns", [])
    return ledger


def next_card_delivery_attempt(run_root: Path, run_id: str, card_id: str) -> tuple[str, str]:
    ledger = read_card_ledger(run_root, run_id)
    deliveries = [
        item
        for item in ledger.get("deliveries", [])
        if isinstance(item, dict) and item.get("card_id") == card_id
    ]
    attempt = len(deliveries) + 1
    safe_card = safe_delivery_component(card_id)
    delivery_id = f"{safe_card}-delivery-{attempt:03d}"
    return delivery_id, f"{delivery_id}-attempt-001"


def card_return_event_for_card(card_id: str) -> str:
    if card_id.startswith("controller."):
        return "controller_card_ack"
    if card_id.startswith("pm."):
        return "pm_card_ack"
    if card_id.startswith("reviewer."):
        return "reviewer_card_ack"
    if card_id.startswith("worker."):
        return "worker_card_ack"
    if card_id.startswith("flowguard_operator."):
        return "flowguard_operator_card_ack"
    return "card_ack"


def card_bundle_return_event_for_role(role: str) -> str:
    if role == "controller":
        return "controller_card_bundle_ack"
    if role == "project_manager":
        return "pm_card_bundle_ack"
    if role == "human_like_reviewer":
        return "reviewer_card_bundle_ack"
    if role.startswith("worker"):
        return "worker_card_bundle_ack"
    if role == "flowguard_operator":
        return "flowguard_operator_card_bundle_ack"
    return "card_bundle_ack"


def is_card_return_event_name(event: str) -> bool:
    return event in CARD_RETURN_EVENT_NAMES
