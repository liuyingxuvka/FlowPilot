"""Direct router ACK token helpers for system-card delivery."""

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


OWNER_MODULE = "flowpilot_router_system_cards"



def _direct_router_ack_token_for_card(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    card_id: str,
    to_role: str,
    target_agent_id: str | None,
    card_return_event: str,
    expected_return_path: str,
    expected_receipt_path: str,
    delivery_id: str | None,
    delivery_attempt_id: str | None,
    body_hash: str | None,
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_id": card_id,
        "card_return_event": card_return_event,
        "target_role": to_role,
        "target_agent_id": target_agent_id,
        "delivery_id": delivery_id,
        "delivery_attempt_id": delivery_attempt_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_path": expected_receipt_path,
        "body_hash": body_hash,
    }


def _direct_router_ack_token_for_bundle(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    bundle_id: str,
    role: str,
    target_agent_id: str | None,
    card_return_event: str,
    card_ids: list[str],
    delivery_attempt_ids: list[str],
    expected_return_path: str,
    expected_receipt_paths: list[str],
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card_bundle",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_bundle_id": bundle_id,
        "card_ids": card_ids,
        "delivery_attempt_ids": delivery_attempt_ids,
        "card_return_event": card_return_event,
        "target_role": role,
        "target_agent_id": target_agent_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_paths": expected_receipt_paths,
    }


__all__ = (
    '_direct_router_ack_token_for_card',
    '_direct_router_ack_token_for_bundle',
)

_LOCAL_NAMES = set(globals())
