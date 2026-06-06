"""Router skeleton owner helpers for flowpilot_router_role_output_bridge.

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
import flowpilot_router_role_output_bridge_events as role_output_bridge_events
import flowpilot_router_startup_flow
from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write
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
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_role_output_bridge'

def _role_output_envelope_record(payload: dict[str, Any]) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if isinstance(envelope, dict):
        return {"_role_output_envelope": envelope}
    return {}

def _role_output_snapshot_name(run_root: Path, output_path: Path) -> str:
    try:
        relative = output_path.resolve().relative_to(run_root.resolve()).as_posix()
    except ValueError:
        relative = output_path.name
    return relative.replace("/", "__").replace("\\", "__")

def _role_output_envelope_record_for_mutable_artifact(
    project_root: Path,
    run_root: Path,
    output_path: Path,
    payload: dict[str, Any],
    *,
    reason: str,
) -> dict[str, Any]:
    envelope = payload.get("_role_output_envelope")
    if not isinstance(envelope, dict):
        return {}
    body_path = envelope.get("body_path")
    if not isinstance(body_path, str):
        return {"_role_output_envelope": envelope}
    source_path = resolve_project_path(project_root, body_path)
    if source_path.resolve() != output_path.resolve():
        return {"_role_output_envelope": envelope}
    snapshot_path = run_root / "role_output_snapshots" / f"{_role_output_snapshot_name(run_root, output_path)}.json"
    write_json(snapshot_path, _without_role_output_envelope(payload))
    raw_hash, semantic_hash = _role_output_hashes(snapshot_path)
    snapshot_envelope = dict(envelope)
    snapshot_envelope.update(
        {
            "body_path": project_relative(project_root, snapshot_path),
            "body_hash": semantic_hash or raw_hash,
            "body_raw_sha256": raw_hash,
            "body_semantic_sha256": semantic_hash,
            "body_snapshot_for_mutable_artifact": project_relative(project_root, output_path),
            "body_snapshot_reason": reason,
        }
    )
    return {"_role_output_envelope": snapshot_envelope}

def _role_output_body_payload_from_record(
    project_root: Path,
    record: dict[str, Any],
    envelope: dict[str, Any],
) -> dict[str, Any]:
    return role_output_bridge_events._role_output_body_payload_from_record(
        _bound_router(),
        project_root,
        record,
        envelope,
    )

def _role_output_event_has_durable_authority(run_root: Path, run_state: dict[str, Any], event: str) -> bool:
    return role_output_bridge_events._role_output_event_has_durable_authority(
        _bound_router(),
        run_root,
        run_state,
        event,
    )

def _sync_material_review_from_role_output_payload(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    payload: dict[str, Any],
) -> bool:
    return role_output_bridge_events._sync_material_review_from_role_output_payload(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        event,
        payload,
    )

def _try_reconcile_direct_role_output_event_ledger(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    return role_output_bridge_events._try_reconcile_direct_role_output_event_ledger(
        _bound_router(),
        project_root,
        run_root,
        run_state,
    )

def _role_output_ledger_outputs(run_root: Path) -> list[dict[str, Any]]:
    return role_output_bridge_events._role_output_ledger_outputs(_bound_router(), run_root)

def _repair_role_output_envelope_hashes(project_root: Path, run_root: Path) -> int:
    repaired = 0
    for path in sorted(run_root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        envelope = payload.get("_role_output_envelope")
        if not isinstance(envelope, dict):
            continue
        body_path = envelope.get("body_path")
        if not isinstance(body_path, str):
            continue
        resolved = resolve_project_path(project_root, body_path)
        if not resolved.exists():
            continue
        raw_hash, semantic_hash = _role_output_hashes(resolved)
        replay_hash = semantic_hash or raw_hash
        accepted_hashes = {raw_hash}
        accepted_hashes.update(_role_output_semantic_hashes(resolved))
        if envelope.get("body_hash") not in accepted_hashes and resolved.resolve() == path.resolve():
            payload.update(
                _role_output_envelope_record_for_mutable_artifact(
                    project_root,
                    run_root,
                    path,
                    payload,
                    reason="reconcile_mutable_artifact_role_output_hash",
                )
            )
            write_json(path, payload)
            repaired += 1
            continue
        if (
            envelope.get("body_hash") == replay_hash
            and envelope.get("body_raw_sha256") == raw_hash
            and envelope.get("body_semantic_sha256") == semantic_hash
        ):
            continue
        envelope["body_hash"] = replay_hash
        envelope["body_raw_sha256"] = raw_hash
        envelope["body_semantic_sha256"] = semantic_hash
        payload["_role_output_envelope"] = envelope
        write_json(path, payload)
        repaired += 1
    return repaired

def _reconciled_card_delivery_context(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    delivery: dict[str, Any],
    manifest: dict[str, Any],
    entries: dict[str, dict[str, str]],
) -> dict[str, Any] | None:
    card_id = str(delivery.get("card_id") or "")
    if card_id not in CARD_PHASE_BY_ID and card_id not in CARD_REQUIRED_SOURCE_PATHS:
        return None
    entry = entries.get(card_id)
    if entry is None:
        return None
    card = manifest_card(manifest, card_id)
    previous = delivery.get("delivery_context") if isinstance(delivery.get("delivery_context"), dict) else {}
    context = _live_card_delivery_context(project_root, run_root, run_state, entry, card)
    context["context_reconciled_at"] = utc_now()
    context["context_reconciled_reason"] = "current_run_state_reconciliation"
    if isinstance(previous, dict):
        context["original_current_stage"] = previous.get("current_stage")
    return context

def _repair_prompt_delivery_contexts(project_root: Path, run_root: Path, run_state: dict[str, Any]) -> int:
    manifest = load_manifest_from_run(run_root)
    entries = {entry["card_id"]: entry for entry in SYSTEM_CARD_SEQUENCE}
    repaired = 0

    def repair_list(deliveries: list[Any]) -> int:
        count = 0
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                continue
            context = _reconciled_card_delivery_context(project_root, run_root, run_state, delivery, manifest, entries)
            if context is None:
                continue
            if delivery.get("delivery_context") != context:
                delivery["delivery_context"] = context
                count += 1
        return count

    repaired += repair_list(run_state.setdefault("delivered_cards", []))
    ledger_path = run_root / "prompt_delivery_ledger.json"
    ledger = read_json_if_exists(ledger_path)
    deliveries = ledger.get("deliveries") if isinstance(ledger.get("deliveries"), list) else []
    ledger_repairs = repair_list(deliveries)
    if ledger_repairs:
        ledger["deliveries"] = deliveries
        ledger["updated_at"] = utc_now()
        write_json(ledger_path, ledger)
    return repaired + ledger_repairs

def _sync_current_and_index_status(project_root: Path, run_state: dict[str, Any]) -> None:
    now = utc_now()
    current_path = project_root / ".flowpilot" / "current.json"
    current = read_json_if_exists(current_path) or {}
    if current.get("run_id") == run_state.get("run_id"):
        current["status"] = run_state.get("status") or current.get("status")
        current["updated_at"] = now
        write_json(current_path, current)
    index_path = project_root / ".flowpilot" / "index.json"
    index = read_json_if_exists(index_path) or {}
    runs = index.get("runs") if isinstance(index.get("runs"), list) else []
    for item in runs:
        if isinstance(item, dict) and item.get("run_id") == run_state.get("run_id"):
            item["status"] = run_state.get("status") or item.get("status")
            item["updated_at"] = now
    if runs:
        index["runs"] = runs
        index["updated_at"] = now
        write_json(index_path, index)

def write_role_output_envelope(
    project_root: Path,
    *,
    output_path: str,
    body: dict[str, Any] | None = None,
    body_file: str | None = None,
    path_key: str = "report_path",
    hash_key: str = "report_hash",
    event_name: str | None = None,
    from_role: str | None = None,
    to_role: str = "controller",
) -> dict[str, Any]:
    if path_key not in {"body_path", "report_path", "decision_path", "result_body_path"}:
        raise RouterError(f"unsupported role envelope path key: {path_key}")
    if hash_key not in {"body_hash", "report_hash", "decision_hash", "result_body_hash"}:
        raise RouterError(f"unsupported role envelope hash key: {hash_key}")
    path = resolve_project_path(project_root, output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if body_file:
        source_path = resolve_project_path(project_root, body_file)
        if not source_path.exists():
            raise RouterError(f"role output body file is missing: {body_file}")
        assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="copy_role_output_body_file")
        path.write_bytes(source_path.read_bytes())
    elif body is not None:
        write_json(path, body)
    elif not path.exists():
        raise RouterError("role output envelope requires body-json, body-file, or an existing output path")
    raw_hash, semantic_hash = _role_output_hashes(path)
    body_hash = semantic_hash or raw_hash
    envelope = {
        "schema_version": ROLE_OUTPUT_ENVELOPE_SCHEMA,
        path_key: project_relative(project_root, path),
        hash_key: body_hash,
        "controller_visibility": "role_output_envelope_only",
        "chat_response_body_allowed": False,
        "from_role": from_role,
        "to_role": to_role,
    }
    if event_name:
        envelope["event_name"] = event_name
    return envelope

_LOCAL_NAMES = set(globals())
