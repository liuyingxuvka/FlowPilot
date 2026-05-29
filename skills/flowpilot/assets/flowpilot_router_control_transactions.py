"""Router skeleton owner helpers for flowpilot_router_control_transactions.

These helpers were moved out of ``flowpilot_router.py`` during the final
StructureMesh skeleton cleanup. The module is bound to the router skeleton
before execution so cross-owner transitional lookups stay explicit.
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
import flowpilot_router_action_handlers
import flowpilot_router_action_providers
import flowpilot_router_card_returns
import flowpilot_router_daemon_runtime
import flowpilot_router_event_dispatcher
import flowpilot_router_events
import flowpilot_router_resume
import flowpilot_router_startup_flow
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
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_control_transactions'

CONTROL_TRANSACTION_EVENT_USAGES = {
    "recorded_event",
    "wait",
    "rerun_target",
    "repair_outcome",
    "reconcile",
}
CONTROL_TRANSACTION_COMMIT_TARGETS = {
    "frontier",
    "run_state",
    "status_summary",
    "packet_ledger",
    "blocker_index",
    "repair_transaction",
    "repair_transaction_index",
    "route",
    "stale_evidence",
    "dispatch_index",
    "pm_package_disposition",
    "wait_closure",
    "formal_gate_package",
}
CONTROL_TRANSACTION_OUTCOME_POLICIES = {
    "single_event",
    "three_distinct_outcomes",
    "quarantine_invalid",
}
CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES = {
    True,
    False,
    "when_reviewing_packet_result",
    "when_repair_rechecks_packet_result",
    "audit_existing_only",
}
CONTROL_TRANSACTION_REPAIR_POLICIES = {
    True,
    False,
    "when_mutation_resolves_control_blocker",
    "audit_existing_only",
}

def _control_transaction_registry_path(run_root: Path | None = None) -> Path:
    if run_root is not None:
        candidate = run_root / "runtime_kit" / "control_transaction_registry.json"
        if candidate.exists():
            return candidate
    return runtime_kit_source() / "control_transaction_registry.json"

def _control_transaction_contract_registry_path(run_root: Path | None = None) -> Path:
    if run_root is not None:
        candidate = run_root / "runtime_kit" / "contracts" / "contract_index.json"
        if candidate.exists():
            return candidate
    return runtime_kit_source() / "contracts" / "contract_index.json"

def _load_control_transaction_registry(run_root: Path | None = None) -> dict[str, Any]:
    return read_json(_control_transaction_registry_path(run_root))

def _registered_output_contract_ids(run_root: Path | None = None) -> set[str]:
    registry = read_json(_control_transaction_contract_registry_path(run_root))
    return {
        str(item.get("contract_id"))
        for item in registry.get("contracts", [])
        if isinstance(item, dict) and item.get("contract_id")
    }

def _control_transaction_registry_rows(run_root: Path | None = None) -> list[dict[str, Any]]:
    registry = _load_control_transaction_registry(run_root)
    rows = registry.get("transaction_types")
    if not isinstance(rows, list):
        raise RouterError("control transaction registry requires transaction_types list")
    return [row for row in rows if isinstance(row, dict)]

def _control_transaction_registry_issues(run_root: Path | None = None) -> list[str]:
    issues: list[str] = []
    try:
        registry = _load_control_transaction_registry(run_root)
    except Exception as exc:
        return [f"control transaction registry cannot be loaded: {exc}"]

    if registry.get("schema_version") != CONTROL_TRANSACTION_REGISTRY_SCHEMA:
        issues.append("control transaction registry schema_version mismatch")
    if registry.get("authority") != "router":
        issues.append("control transaction registry authority must be router")
    if registry.get("controller_may_invent_transactions") is not False:
        issues.append("control transaction registry must forbid controller-invented transactions")

    raw_rows = registry.get("transaction_types")
    if not isinstance(raw_rows, list) or not raw_rows:
        issues.append("control transaction registry requires non-empty transaction_types list")
        return issues

    try:
        contract_ids = _registered_output_contract_ids(run_root)
    except Exception as exc:
        contract_ids = set()
        issues.append(f"control transaction registry cannot load contract index: {exc}")

    seen: set[str] = set()
    for index, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            issues.append(f"transaction_types[{index}] must be an object")
            continue
        transaction_type = str(row.get("transaction_type") or "").strip()
        context = transaction_type or f"transaction_types[{index}]"
        if not transaction_type:
            issues.append(f"{context}: transaction_type is required")
        elif transaction_type in seen:
            issues.append(f"{context}: duplicate transaction_type")
        seen.add(transaction_type)

        for field in ("producer_roles", "output_contract_ids", "router_events", "event_usages", "commit_targets"):
            if not isinstance(row.get(field), list):
                issues.append(f"{context}: {field} must be a list")

        producer_roles = row.get("producer_roles") if isinstance(row.get("producer_roles"), list) else []
        if not [role for role in producer_roles if str(role).strip()]:
            issues.append(f"{context}: producer_roles must be non-empty")

        output_contract_ids = row.get("output_contract_ids") if isinstance(row.get("output_contract_ids"), list) else []
        for contract_id in output_contract_ids:
            if str(contract_id) not in contract_ids:
                issues.append(f"{context}: output_contract_id is not registered: {contract_id}")

        router_events = row.get("router_events") if isinstance(row.get("router_events"), list) else []
        for event in router_events:
            if str(event) not in EXTERNAL_EVENTS:
                issues.append(f"{context}: router_event is not registered: {event}")

        event_usages = row.get("event_usages") if isinstance(row.get("event_usages"), list) else []
        for usage in event_usages:
            if str(usage) not in CONTROL_TRANSACTION_EVENT_USAGES:
                issues.append(f"{context}: unsupported event_usage: {usage}")

        commit_targets = row.get("commit_targets") if isinstance(row.get("commit_targets"), list) else []
        if not commit_targets:
            issues.append(f"{context}: commit_targets must be non-empty")
        for target in commit_targets:
            if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                issues.append(f"{context}: unsupported commit_target: {target}")
        optional_targets = row.get("optional_commit_targets", [])
        if optional_targets is None:
            optional_targets = []
        if not isinstance(optional_targets, list):
            issues.append(f"{context}: optional_commit_targets must be a list when present")
        else:
            for target in optional_targets:
                if str(target) not in CONTROL_TRANSACTION_COMMIT_TARGETS:
                    issues.append(f"{context}: unsupported optional_commit_target: {target}")

        if row.get("packet_authority_required") not in CONTROL_TRANSACTION_PACKET_AUTHORITY_POLICIES:
            issues.append(f"{context}: unsupported packet_authority_required policy")
        if row.get("repair_transaction_required") not in CONTROL_TRANSACTION_REPAIR_POLICIES:
            issues.append(f"{context}: unsupported repair_transaction_required policy")
        if row.get("outcome_policy") not in CONTROL_TRANSACTION_OUTCOME_POLICIES:
            issues.append(f"{context}: unsupported outcome_policy")
    return issues

def _validate_control_transaction_registry(run_root: Path | None = None) -> None:
    issues = _control_transaction_registry_issues(run_root)
    if issues:
        raise RouterError("control transaction registry invalid: " + "; ".join(issues))

def _control_transaction_row(run_root: Path | None, transaction_type: str) -> dict[str, Any]:
    _validate_control_transaction_registry(run_root)
    for row in _control_transaction_registry_rows(run_root):
        if row.get("transaction_type") == transaction_type:
            return row
    raise RouterError(f"control transaction type is not registered: {transaction_type}")

def _validate_control_transaction_requirements(
    run_root: Path | None,
    *,
    transaction_type: str,
    producer_role: str,
    output_contract_id: str | None = None,
    router_events: tuple[str, ...] = (),
    required_event_usages: tuple[str, ...] = (),
    required_commit_targets: tuple[str, ...] = (),
    require_packet_authority: bool | None = None,
    require_repair_transaction: bool | None = None,
    outcome_policy: str | None = None,
) -> dict[str, Any]:
    row = _control_transaction_row(run_root, transaction_type)
    issues: list[str] = []
    producer_roles = {str(role) for role in row.get("producer_roles", [])}
    if producer_role not in producer_roles:
        issues.append(f"producer role {producer_role} is not allowed")
    if output_contract_id:
        contract_ids = {str(contract_id) for contract_id in row.get("output_contract_ids", [])}
        if output_contract_id not in contract_ids:
            issues.append(f"output contract {output_contract_id} is not allowed")
    declared_events = {str(event) for event in row.get("router_events", [])}
    for event in router_events:
        if event not in declared_events:
            issues.append(f"router event {event} is not declared")
    declared_usages = {str(usage) for usage in row.get("event_usages", [])}
    for usage in required_event_usages:
        if usage not in declared_usages:
            issues.append(f"event usage {usage} is not declared")
    declared_targets = {str(target) for target in row.get("commit_targets", [])}
    for target in required_commit_targets:
        if target not in declared_targets:
            issues.append(f"commit target {target} is not declared")
    if require_packet_authority is True and row.get("packet_authority_required") is not True:
        issues.append("packet authority is required but not declared as unconditional")
    if require_packet_authority is False and row.get("packet_authority_required") not in {False}:
        issues.append("packet authority is declared but this transaction expected none")
    if require_repair_transaction is True and row.get("repair_transaction_required") is not True:
        issues.append("repair transaction is required but not declared as unconditional")
    if require_repair_transaction is False and row.get("repair_transaction_required") not in {False}:
        issues.append("repair transaction is declared but this transaction expected none")
    if outcome_policy and row.get("outcome_policy") != outcome_policy:
        issues.append(f"outcome policy must be {outcome_policy}")
    if issues:
        raise RouterError(
            f"control transaction registry does not authorize {transaction_type}: "
            + "; ".join(issues)
        )
    return {
        "schema_version": CONTROL_TRANSACTION_REGISTRY_SCHEMA,
        "transaction_type": transaction_type,
        "producer_role": producer_role,
        "output_contract_id": output_contract_id,
        "router_events": list(router_events),
        "event_usages": list(required_event_usages),
        "commit_targets": list(required_commit_targets),
        "packet_authority_required": row.get("packet_authority_required"),
        "repair_transaction_required": row.get("repair_transaction_required"),
        "outcome_policy": row.get("outcome_policy"),
        "registry_path": "runtime_kit/control_transaction_registry.json",
    }

_LOCAL_NAMES = set(globals())
