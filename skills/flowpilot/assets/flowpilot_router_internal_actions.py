"""Router skeleton owner helpers for flowpilot_router_internal_actions.

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


OWNER_MODULE = 'flowpilot_router_internal_actions'

def _action_is_router_internal_mechanical(action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    action_type = str(action.get("action_type") or "")
    if action_type not in ROUTER_INTERNAL_MECHANICAL_ACTION_TYPES:
        return False
    if bool(action.get("requires_user")) or bool(action.get("requires_payload")):
        return False
    if bool(action.get("requires_host_role_binding")) or bool(action.get("requires_host_automation")):
        return False
    if bool(action.get("requires_user_dialog_display_confirmation")):
        return False
    if action.get("card_id") or action.get("mail_id"):
        return False
    if bool(action.get("sealed_body_reads_allowed", False)):
        return False
    return True

def _router_internal_mechanical_identity(action: dict[str, Any]) -> dict[str, Any]:
    action_type = str(action.get("action_type") or "")
    identity = {
        "action_type": action_type,
        "label": action.get("label"),
        "next_card_id": action.get("next_card_id"),
        "next_recipient_role": action.get("next_recipient_role"),
        "bundle_card_ids": action.get("bundle_card_ids") or [],
        "next_mail_id": action.get("next_mail_id"),
        "next_mail_to_role": action.get("next_mail_to_role"),
        "postcondition": action.get("postcondition"),
        "scope_kind": action.get("scope_kind"),
        "scope_id": action.get("scope_id"),
    }
    return {key: value for key, value in identity.items() if value not in (None, "", [])}

def _append_router_internal_mechanical_record(
    run_state: dict[str, Any],
    action: dict[str, Any],
    *,
    status: str,
    side_effect_applied: bool,
    error: str | None = None,
) -> dict[str, Any]:
    identity = _router_internal_mechanical_identity(action)
    event_id = "router-internal-" + hashlib.sha256(
        json.dumps(identity, sort_keys=True).encode("utf-8")
    ).hexdigest()[:20]
    record = {
        "event_id": event_id,
        "action_type": action.get("action_type"),
        "label": action.get("label"),
        "identity": identity,
        "status": status,
        "side_effect_applied": side_effect_applied,
        "controller_row_written": False,
        "sealed_body_reads_allowed": False,
        "recorded_at": utc_now(),
    }
    if error:
        record["error"] = error
    run_state.setdefault("router_internal_mechanical_events", []).append(record)
    append_history(
        run_state,
        "router_consumed_internal_mechanical_action",
        {
            "action_type": action.get("action_type"),
            "event_id": event_id,
            "status": status,
            "side_effect_applied": side_effect_applied,
            "controller_row_written": False,
        },
    )
    return record

def _consume_router_internal_mechanical_action(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    action: dict[str, Any],
) -> dict[str, Any]:
    if not _action_is_router_internal_mechanical(action):
        raise RouterError(f"action is not Router-internal mechanical work: {action.get('action_type')}")
    action_type = str(action.get("action_type") or "")
    try:
        side_effect_applied = False
        result_extra: dict[str, Any] = {}
        if action_type == "check_prompt_manifest":
            manifest = load_manifest_from_run(run_root)
            next_card_id = str(action.get("next_card_id") or "")
            if next_card_id:
                manifest_card(manifest, next_card_id)
            for card_id in action.get("bundle_card_ids") or []:
                if isinstance(card_id, str) and card_id:
                    manifest_card(manifest, card_id)
            if not run_state.get("manifest_check_requested"):
                run_state["manifest_check_requested"] = True
                run_state["manifest_check_requests"] = int(run_state.get("manifest_check_requests", 0)) + 1
                run_state["manifest_checks"] = int(run_state.get("manifest_checks", 0)) + 1
                side_effect_applied = True
            result_extra["next_card_id"] = next_card_id or None
        elif action_type == "check_packet_ledger":
            ledger = read_json(run_root / "packet_ledger.json")
            if ledger.get("schema_version") != PACKET_LEDGER_SCHEMA:
                raise RouterError("invalid packet ledger schema")
            if not run_state.get("ledger_check_requested"):
                run_state["ledger_check_requested"] = True
                run_state["ledger_check_requests"] = int(run_state.get("ledger_check_requests", 0)) + 1
                run_state["ledger_checks"] = int(run_state.get("ledger_checks", 0)) + 1
                side_effect_applied = True
            result_extra["next_mail_id"] = action.get("next_mail_id")
        elif action_type == "write_startup_mechanical_audit":
            context = _startup_mechanical_audit_context(project_root, run_root, run_state)
            if not run_state.get("flags", {}).get("startup_mechanical_audit_written") or context is None:
                computed_checks = _startup_mechanical_checks(project_root, run_root, run_state)
                _write_startup_mechanical_audit(project_root, run_root, run_state, computed_checks)
                context = _startup_mechanical_audit_context(project_root, run_root, run_state)
                if context is None:
                    raise RouterError("startup mechanical audit was not written with a valid proof")
                run_state.setdefault("flags", {})["startup_mechanical_audit_written"] = True
                run_state["startup_mechanical_audit"] = {
                    "path": project_relative(project_root, context["audit_path"]),
                    "sha256": context["audit_hash"],
                    "proof_path": project_relative(project_root, context["proof_path"]),
                    "proof_sha256": context["proof_hash"],
                    "written_before_first_pm_work": not run_state["flags"].get("user_intake_delivered_to_pm"),
                }
                side_effect_applied = True
            result_extra["postcondition"] = "startup_mechanical_audit_written"
        else:
            raise RouterError(f"unsupported Router-internal mechanical action: {action_type}")
        run_state["pending_action"] = None
        record = _append_router_internal_mechanical_record(
            run_state,
            action,
            status="done",
            side_effect_applied=side_effect_applied,
        )
        _refresh_route_memory(project_root, run_root, run_state, trigger=f"after_router_internal_mechanical:{action_type}")
        _sync_derived_run_views(
            project_root,
            run_root,
            run_state,
            reason=f"after_router_internal_mechanical:{action_type}",
            update_display=True,
        )
        save_run_state(run_root, run_state)
        return {
            "ok": True,
            "consumed": True,
            "action_type": action_type,
            "event": record,
            "side_effect_applied": side_effect_applied,
            **result_extra,
        }
    except Exception as exc:
        _append_router_internal_mechanical_record(
            run_state,
            action,
            status="failed",
            side_effect_applied=False,
            error=str(exc),
        )
        save_run_state(run_root, run_state)
        raise

_LOCAL_NAMES = set(globals())
