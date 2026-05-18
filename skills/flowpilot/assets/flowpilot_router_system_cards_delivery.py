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

OWNER_MODULE = "flowpilot_router_system_cards"

def _commit_system_card_delivery_artifact(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending: dict[str, Any],
) -> dict[str, Any]:
    card_id = str(pending["card_id"])
    card_entry = next((entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
    if card_entry is None:
        raise RouterError(f"unknown system card in pending action: {card_id}")
    if not run_state.get("manifest_check_requested"):
        raise RouterError("system card delivery requires a current manifest check")
    manifest = load_manifest_from_run(run_root)
    card = manifest_card(manifest, card_id)
    delivery_context = pending.get("delivery_context")
    if not isinstance(delivery_context, dict):
        delivery_context = _live_card_delivery_context(project_root, run_root, run_state, card_entry, card)
    delivery = {
        "card_id": card_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "to_role": pending["to_role"],
        "path": card["path"],
        "delivery_mode": pending.get("delivery_mode") or "envelope_only_v2",
        "controller_visibility": "system_card_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": pending.get("open_method") or "open-card",
        "card_return_event": pending.get("card_return_event") or _card_return_event_for_card(card_id),
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "direct_router_ack_token": pending.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
        "expected_return_path": pending.get("expected_return_path"),
        "expected_receipt_path": pending.get("expected_receipt_path"),
        "card_envelope_path": pending.get("card_envelope_path"),
        "delivery_id": pending.get("delivery_id"),
        "delivery_attempt_id": pending.get("delivery_attempt_id"),
        "body_path": pending.get("body_path"),
        "body_hash": pending.get("body_hash"),
        "manifest_path": pending.get("manifest_path"),
        "manifest_hash": pending.get("manifest_hash"),
        "target_agent_id": pending.get("target_agent_id"),
        "resume_tick_id": pending.get("resume_tick_id"),
        "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
        "gate_contract": pending.get("gate_contract"),
        "delivery_context": delivery_context,
        "delivered_at": utc_now(),
    }
    if card_id == "reviewer.startup_fact_check":
        delivery.update(
            {
                "startup_mechanical_audit_path": pending.get("startup_mechanical_audit_path"),
                "startup_mechanical_audit_hash": pending.get("startup_mechanical_audit_hash"),
                "router_owned_check_proof_path": pending.get("router_owned_check_proof_path"),
                "router_owned_check_proof_hash": pending.get("router_owned_check_proof_hash"),
                "router_computable_checks_already_enforced": True,
                "reviewer_should_not_reprove_router_computable_checks": True,
                "reviewer_required_external_facts": pending.get("reviewer_required_external_facts") or [],
            }
        )
    envelope_path_raw = delivery.get("card_envelope_path")
    expected_return_path_raw = delivery.get("expected_return_path")
    expected_receipt_path_raw = delivery.get("expected_receipt_path")
    if not all(isinstance(item, str) and item for item in (envelope_path_raw, expected_return_path_raw, expected_receipt_path_raw)):
        raise RouterError("system card envelope delivery requires envelope, receipt, and return paths")
    envelope_path = resolve_project_path(project_root, str(envelope_path_raw))
    expected_return_path = resolve_project_path(project_root, str(expected_return_path_raw))
    expected_receipt_path = resolve_project_path(project_root, str(expected_receipt_path_raw))
    envelope = {
        "schema_version": card_runtime.CARD_ENVELOPE_SCHEMA,
        "run_id": run_state["run_id"],
        "run_root": project_relative(project_root, run_root),
        "resume_tick_id": delivery.get("resume_tick_id"),
        "envelope_id": delivery.get("delivery_attempt_id"),
        "delivery_id": delivery.get("delivery_id"),
        "delivery_attempt_id": delivery.get("delivery_attempt_id"),
        "card_id": card_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "target_role": pending["to_role"],
        "target_agent_id": delivery.get("target_agent_id"),
        "body_path": delivery.get("body_path"),
        "body_hash": delivery.get("body_hash"),
        "manifest_path": delivery.get("manifest_path"),
        "manifest_hash": delivery.get("manifest_hash"),
        "body_visibility": "target_role_runtime_only",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "controller_visibility": "system_card_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": delivery.get("open_method") or "open-card",
        "card_return_event": delivery.get("card_return_event"),
        "card_checkin_instruction": delivery.get("card_checkin_instruction"),
        "direct_router_ack_token": delivery.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
        "expected_receipt_path": project_relative(project_root, expected_receipt_path),
        "expected_return_path": project_relative(project_root, expected_return_path),
        "delivery_context": delivery_context,
        "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
        "gate_contract": delivery.get("gate_contract"),
        "delivered_at": delivery["delivered_at"],
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated_by_receipt": False,
    }
    envelope["envelope_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(envelope_path, envelope)
    ack_clearance_scope = _card_ack_clearance_scope(
        delivery_context,
        card_id=card_id,
        target_role=str(pending["to_role"]),
    )
    delivery["card_envelope_hash"] = envelope["envelope_hash"]
    delivery["resource_lifecycle"] = "committed_artifact"
    delivery["artifact_committed"] = True
    delivery["relay_allowed"] = True
    delivery["apply_required"] = False
    delivery["ack_clearance_scope"] = ack_clearance_scope
    run_state["delivered_cards"].append(delivery)
    run_state["flags"][card_entry["flag"]] = True
    run_state["manifest_check_requested"] = False
    run_state["prompt_deliveries"] = int(run_state.get("prompt_deliveries", 0)) + 1
    ledger = read_json_if_exists(run_root / "prompt_delivery_ledger.json") or {"schema_version": "flowpilot.prompt_delivery_ledger.v1", "deliveries": []}
    ledger.setdefault("deliveries", []).append(delivery)
    ledger["updated_at"] = utc_now()
    write_json(run_root / "prompt_delivery_ledger.json", ledger)
    card_ledger = _read_card_ledger(run_root, str(run_state["run_id"]))
    card_ledger.setdefault("deliveries", []).append(
        {
            "card_id": card_id,
            "delivery_id": delivery.get("delivery_id"),
            "delivery_attempt_id": delivery.get("delivery_attempt_id"),
            "to_role": pending["to_role"],
            "target_agent_id": delivery.get("target_agent_id"),
            "card_envelope_path": project_relative(project_root, envelope_path),
            "card_envelope_hash": envelope["envelope_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "body_hash": delivery.get("body_hash"),
            "manifest_hash": delivery.get("manifest_hash"),
            "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
            "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
            "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
            "gate_contract": delivery.get("gate_contract"),
            "ack_clearance_scope": ack_clearance_scope,
            "requires_read_receipt": True,
            "card_return_event": delivery.get("card_return_event"),
            "card_checkin_instruction": delivery.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "expected_return_path": project_relative(project_root, expected_return_path),
            "delivered_at": delivery["delivered_at"],
        }
    )
    card_ledger["updated_at"] = utc_now()
    write_json(_card_ledger_path(run_root), card_ledger)
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    return_ledger.setdefault("pending_returns", []).append(
        {
            "card_return_event": delivery.get("card_return_event"),
            "status": "pending",
            "card_id": card_id,
            "delivery_id": delivery.get("delivery_id"),
            "delivery_attempt_id": delivery.get("delivery_attempt_id"),
            "target_role": pending["to_role"],
            "target_agent_id": delivery.get("target_agent_id"),
            "card_envelope_path": project_relative(project_root, envelope_path),
            "card_envelope_hash": envelope["envelope_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "expected_return_path": project_relative(project_root, expected_return_path),
            "card_checkin_instruction": delivery.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
            "ack_clearance_scope": ack_clearance_scope,
            "sent_at": delivery["delivered_at"],
        }
    )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    return {
        "ok": True,
        "applied": "commit_system_card_delivery_artifact",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "artifact_exists": True,
        "artifact_hash_verified": True,
        "ledger_recorded": True,
        "return_wait_recorded": True,
        "relay_allowed": True,
        "apply_required": False,
        "card_envelope_path": project_relative(project_root, envelope_path),
        "card_checkin_instruction": delivery.get("card_checkin_instruction"),
        "expected_return_path": project_relative(project_root, expected_return_path),
        "expected_receipt_path": project_relative(project_root, expected_receipt_path),
    }

def _commit_system_card_bundle_delivery_artifact(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    pending: dict[str, Any],
) -> dict[str, Any]:
    if not run_state.get("manifest_check_requested"):
        raise RouterError("system card bundle delivery requires a current manifest check")
    cards = pending.get("cards")
    if not isinstance(cards, list) or len(cards) < 2:
        raise RouterError("system card bundle delivery requires at least two member cards")
    role = str(pending.get("to_role") or "")
    bundle_id = str(pending.get("card_bundle_id") or "")
    bundle_path_raw = str(pending.get("card_bundle_envelope_path") or "")
    expected_return_path_raw = str(pending.get("expected_return_path") or "")
    expected_receipt_paths = pending.get("expected_receipt_paths")
    if not bundle_id or not bundle_path_raw or not expected_return_path_raw:
        raise RouterError("system card bundle delivery requires bundle id, envelope path, and return path")
    if not isinstance(expected_receipt_paths, list) or len(expected_receipt_paths) != len(cards):
        raise RouterError("system card bundle delivery requires one expected receipt path per member")
    bundle_path = resolve_project_path(project_root, bundle_path_raw)
    expected_return_path = resolve_project_path(project_root, expected_return_path_raw)
    manifest = load_manifest_from_run(run_root)
    delivered_at = utc_now()
    envelope_cards: list[dict[str, Any]] = []
    deliveries: list[dict[str, Any]] = []
    ack_clearance_scopes: list[dict[str, Any]] = []
    for index, member in enumerate(cards):
        if not isinstance(member, dict):
            raise RouterError("system card bundle member must be an object")
        card_id = str(member.get("card_id") or "")
        card_entry = next((entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == card_id), None)
        if card_entry is None:
            raise RouterError(f"unknown system card in bundle: {card_id}")
        card = manifest_card(manifest, card_id)
        delivery_context = member.get("delivery_context")
        if not isinstance(delivery_context, dict):
            delivery_context = _live_card_delivery_context(project_root, run_root, run_state, card_entry, card)
        expected_receipt_path = resolve_project_path(project_root, str(expected_receipt_paths[index]))
        body_path_raw = str(member.get("body_path") or "")
        body_hash = str(member.get("body_hash") or "")
        if not body_path_raw or not body_hash:
            raise RouterError(f"system card bundle member {card_id} missing body path or hash")
        ack_clearance_scope = _card_ack_clearance_scope(
            delivery_context,
            card_id=card_id,
            target_role=role,
        )
        ack_clearance_scopes.append(ack_clearance_scope)
        envelope_card = {
            "card_id": card_id,
            "path": card["path"],
            "delivery_id": member.get("delivery_id"),
            "delivery_attempt_id": member.get("delivery_attempt_id"),
            "body_path": body_path_raw,
            "body_hash": body_hash,
            "manifest_path": member.get("manifest_path"),
            "manifest_hash": member.get("manifest_hash"),
            "expected_receipt_path": project_relative(project_root, expected_receipt_path),
            "card_return_event": member.get("card_return_event") or _card_return_event_for_card(card_id),
            "delivery_context": delivery_context,
            "ack_clearance_scope": ack_clearance_scope,
        }
        envelope_cards.append(envelope_card)
        deliveries.append(
            {
                "card_id": card_id,
                "from": "system",
                "issued_by": "router",
                "delivered_by": "controller",
                "to_role": role,
                "path": card["path"],
                "delivery_mode": "same_role_system_card_bundle_v1",
                "controller_visibility": "system_card_bundle_envelope_only",
                "sealed_body_reads_allowed": False,
                "requires_read_receipt": True,
                "open_method": "open-card-bundle",
                "card_return_event": envelope_card["card_return_event"],
                "bundle_return_event": pending.get("card_return_event"),
                "card_checkin_instruction": pending.get("card_checkin_instruction"),
                "direct_router_ack_token": pending.get("direct_router_ack_token"),
                "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
                "expected_return_path": expected_return_path_raw,
                "expected_receipt_path": project_relative(project_root, expected_receipt_path),
                "card_bundle_id": bundle_id,
                "card_bundle_envelope_path": bundle_path_raw,
                "card_envelope_path": bundle_path_raw,
                "delivery_id": member.get("delivery_id"),
                "delivery_attempt_id": member.get("delivery_attempt_id"),
                "body_path": body_path_raw,
                "body_hash": body_hash,
                "manifest_path": member.get("manifest_path"),
                "manifest_hash": member.get("manifest_hash"),
                "target_agent_id": pending.get("target_agent_id"),
                "resume_tick_id": pending.get("resume_tick_id"),
                "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
                "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
                "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
                "delivery_context": delivery_context,
                "ack_clearance_scope": ack_clearance_scope,
                "delivered_at": delivered_at,
            }
        )
        for key in (
            "pm_context_paths",
            "pm_prior_path_context_required_for_decision",
            "controller_history_is_evidence",
        ):
            if key in member:
                deliveries[-1][key] = member[key]
    envelope = {
        "schema_version": card_runtime.CARD_BUNDLE_ENVELOPE_SCHEMA,
        "run_id": run_state["run_id"],
        "run_root": project_relative(project_root, run_root),
        "resume_tick_id": pending.get("resume_tick_id"),
        "bundle_id": bundle_id,
        "from": "system",
        "issued_by": "router",
        "delivered_by": "controller",
        "target_role": role,
        "target_agent_id": pending.get("target_agent_id"),
        "cards": envelope_cards,
        "card_ids": [card["card_id"] for card in envelope_cards],
        "body_visibility": "target_role_runtime_only",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "relay_allowed": True,
        "apply_required": False,
        "controller_visibility": "system_card_bundle_envelope_only",
        "sealed_body_reads_allowed": False,
        "requires_read_receipt": True,
        "open_method": "open-card-bundle",
        "card_return_event": pending.get("card_return_event"),
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "direct_router_ack_token": pending.get("direct_router_ack_token"),
        "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
        "expected_receipt_paths": [card["expected_receipt_path"] for card in envelope_cards],
        "expected_return_path": project_relative(project_root, expected_return_path),
        "role_io_protocol_hash": pending.get("role_io_protocol_hash"),
        "role_io_protocol_receipt_path": pending.get("role_io_protocol_receipt_path"),
        "role_io_protocol_receipt_hash": pending.get("role_io_protocol_receipt_hash"),
        "delivered_at": delivered_at,
        "runtime_validates_mechanics_only": True,
        "semantic_understanding_validated_by_receipt": False,
        "same_role_bundle": True,
        "manifest_batch_checked": True,
    }
    envelope["bundle_hash"] = card_runtime.stable_json_hash(envelope)
    write_json(bundle_path, envelope)
    run_state.setdefault("delivered_cards", [])
    ledger = read_json_if_exists(run_root / "prompt_delivery_ledger.json") or {
        "schema_version": "flowpilot.prompt_delivery_ledger.v1",
        "run_id": run_state["run_id"],
        "deliveries": [],
    }
    card_ledger = _read_card_ledger(run_root, str(run_state["run_id"]))
    for delivery in deliveries:
        delivery["card_bundle_envelope_hash"] = envelope["bundle_hash"]
        delivery["card_envelope_hash"] = envelope["bundle_hash"]
        delivery["resource_lifecycle"] = "committed_artifact"
        delivery["artifact_committed"] = True
        delivery["relay_allowed"] = True
        delivery["apply_required"] = False
        run_state["delivered_cards"].append(delivery)
        card_entry = next(entry for entry in SYSTEM_CARD_SEQUENCE if entry["card_id"] == delivery["card_id"])
        run_state["flags"][card_entry["flag"]] = True
        ledger.setdefault("deliveries", []).append(delivery)
        card_ledger.setdefault("deliveries", []).append(
            {
                "card_id": delivery.get("card_id"),
                "card_bundle_id": bundle_id,
                "delivery_id": delivery.get("delivery_id"),
                "delivery_attempt_id": delivery.get("delivery_attempt_id"),
                "to_role": role,
                "target_agent_id": delivery.get("target_agent_id"),
                "card_bundle_envelope_path": bundle_path_raw,
                "card_envelope_path": bundle_path_raw,
                "card_bundle_envelope_hash": envelope["bundle_hash"],
                "card_envelope_hash": envelope["bundle_hash"],
                "resource_lifecycle": "committed_artifact",
                "artifact_committed": True,
                "relay_allowed": True,
                "apply_required": False,
                "body_hash": delivery.get("body_hash"),
                "manifest_hash": delivery.get("manifest_hash"),
                "role_io_protocol_hash": delivery.get("role_io_protocol_hash"),
                "role_io_protocol_receipt_path": delivery.get("role_io_protocol_receipt_path"),
                "role_io_protocol_receipt_hash": delivery.get("role_io_protocol_receipt_hash"),
                "ack_clearance_scope": delivery.get("ack_clearance_scope"),
                "requires_read_receipt": True,
                "card_return_event": delivery.get("card_return_event"),
                "bundle_return_event": pending.get("card_return_event"),
                "card_checkin_instruction": delivery.get("card_checkin_instruction"),
                "direct_router_ack_token_hash": delivery.get("direct_router_ack_token_hash"),
                "expected_receipt_path": delivery.get("expected_receipt_path"),
                "expected_return_path": expected_return_path_raw,
                "delivered_at": delivered_at,
            }
        )
    run_state["manifest_check_requested"] = False
    run_state["prompt_deliveries"] = int(run_state.get("prompt_deliveries", 0)) + len(deliveries)
    ledger["updated_at"] = utc_now()
    write_json(run_root / "prompt_delivery_ledger.json", ledger)
    card_ledger["updated_at"] = utc_now()
    write_json(_card_ledger_path(run_root), card_ledger)
    return_ledger = _read_return_event_ledger(run_root, str(run_state["run_id"]))
    bundle_ack_clearance_scope = {
        "schema_version": "flowpilot.system_card_ack_clearance_scope.v1",
        "return_kind": "system_card_bundle",
        "card_bundle_id": bundle_id,
        "card_ids": [delivery.get("card_id") for delivery in deliveries],
        "target_role": role,
        "member_scopes": ack_clearance_scopes,
        "required_before": [
            "gate_or_node_boundary_transition",
            "formal_work_packet_relay_to_target_role",
        ],
        "ack_is_read_receipt_only": True,
        "target_work_completion_evidence_required_separately": True,
    }
    return_ledger.setdefault("pending_returns", []).append(
        {
            "return_kind": "system_card_bundle",
            "card_return_event": pending.get("card_return_event"),
            "status": "pending",
            "card_bundle_id": bundle_id,
            "card_ids": [delivery.get("card_id") for delivery in deliveries],
            "delivery_attempt_ids": [delivery.get("delivery_attempt_id") for delivery in deliveries],
            "target_role": role,
            "target_agent_id": pending.get("target_agent_id"),
            "card_bundle_envelope_path": bundle_path_raw,
            "card_bundle_envelope_hash": envelope["bundle_hash"],
            "resource_lifecycle": "committed_artifact",
            "artifact_committed": True,
            "relay_allowed": True,
            "apply_required": False,
            "expected_receipt_paths": [delivery.get("expected_receipt_path") for delivery in deliveries],
            "expected_return_path": expected_return_path_raw,
            "card_checkin_instruction": pending.get("card_checkin_instruction"),
            "direct_router_ack_token_hash": pending.get("direct_router_ack_token_hash"),
            "ack_clearance_scope": bundle_ack_clearance_scope,
            "sent_at": delivered_at,
        }
    )
    return_ledger["updated_at"] = utc_now()
    write_json(_return_event_ledger_path(run_root), return_ledger)
    return {
        "ok": True,
        "applied": "commit_system_card_bundle_delivery_artifact",
        "resource_lifecycle": "committed_artifact",
        "artifact_committed": True,
        "artifact_exists": True,
        "artifact_hash_verified": True,
        "ledger_recorded": True,
        "return_wait_recorded": True,
        "relay_allowed": True,
        "apply_required": False,
        "card_bundle_id": bundle_id,
        "card_bundle_envelope_path": bundle_path_raw,
        "card_bundle_envelope_hash": envelope["bundle_hash"],
        "card_checkin_instruction": pending.get("card_checkin_instruction"),
        "expected_return_path": expected_return_path_raw,
        "expected_receipt_paths": [delivery.get("expected_receipt_path") for delivery in deliveries],
    }

__all__ = (
    '_commit_system_card_delivery_artifact',
    '_commit_system_card_bundle_delivery_artifact',
)

_LOCAL_NAMES = set(globals())
