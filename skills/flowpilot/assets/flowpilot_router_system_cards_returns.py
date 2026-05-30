"""Internal router owner helpers extracted from flowpilot_router.

The public router names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so private helper lookups remain
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

def _pending_return_record_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._pending_return_record_for_action(_bound_router(), run_root, run_id, action)

def _pending_bundle_return_record_for_action(run_root: Path, run_id: str, action: dict[str, Any]) -> dict[str, Any] | None:
    return flowpilot_router_card_returns._pending_bundle_return_record_for_action(_bound_router(), run_root, run_id, action)

def _apply_card_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._apply_card_return_event_check(_bound_router(), project_root, run_root, run_state, pending)

def _apply_card_bundle_return_event_check(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._apply_card_bundle_return_event_check(_bound_router(), project_root, run_root, run_state, pending)

def _try_auto_consume_pending_card_return_ack(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    pending: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_card_returns._try_auto_consume_pending_card_return_ack(_bound_router(), project_root, run_root, run_state, pending)

def _startup_pm_card_bundle_ack_record(record: dict[str, Any]) -> bool:
    return flowpilot_router_card_returns._startup_pm_card_bundle_ack_record(_bound_router(), record)

def _reconcile_card_wait_rows(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    delivery_attempt_id: str,
    expected_return_path: str,
    card_return_event: str,
    card_id: str,
    source: str,
    ack_path: str | None,
) -> int:
    return flowpilot_router_card_returns._reconcile_card_wait_rows(_bound_router(), project_root, run_root, run_state, delivery_attempt_id=delivery_attempt_id, expected_return_path=expected_return_path, card_return_event=card_return_event, card_id=card_id, source=source, ack_path=ack_path)

def _reconcile_card_bundle_wait_rows(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    bundle_id: str,
    expected_return_path: str,
    card_return_event: str,
    source: str,
    ack_path: str | None,
) -> int:
    return flowpilot_router_card_returns._reconcile_card_bundle_wait_rows(_bound_router(), project_root, run_root, run_state, bundle_id=bundle_id, expected_return_path=expected_return_path, card_return_event=card_return_event, source=source, ack_path=ack_path)

def _router_release_startup_user_intake_to_pm(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._router_release_startup_user_intake_to_pm(_bound_router(), project_root, run_root, run_state, source=source)

def _run_router_return_settlement_finalizers(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    source: str,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._run_router_return_settlement_finalizers(_bound_router(), project_root, run_root, run_state, source=source)

def _mark_card_return_pending_explicit_check(
    run_root: Path,
    run_id: str,
    action: dict[str, Any],
    *,
    reason: str,
    error: object = None,
) -> None:
    return flowpilot_router_card_returns._mark_card_return_pending_explicit_check(_bound_router(), run_root, run_id, action, reason=reason, error=error)

def _preconsume_pending_card_return_ack_before_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
) -> dict[str, Any]:
    return flowpilot_router_event_intake.preconsume_pending_card_return_ack_before_external_event(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        event=event,
    )

def _system_card_delivery_flag(card_id: object) -> str:
    return flowpilot_router_event_intake.system_card_delivery_flag(_bound_router(), card_id)

def _pending_return_card_delivery_flags(pending_return: dict[str, Any]) -> set[str]:
    return flowpilot_router_event_intake.pending_return_card_delivery_flags(_bound_router(), pending_return)

def _role_list(value: object) -> set[str]:
    return flowpilot_router_event_intake.role_list(value)

def _pending_card_return_matches_event_dependency(
    pending_return: dict[str, Any],
    event: str,
    run_state: dict[str, Any],
) -> bool:
    return flowpilot_router_event_intake.pending_card_return_matches_event_dependency(
        _bound_router(),
        pending_return,
        event,
        run_state,
    )

def _next_quarantined_role_report_path(run_root: Path, event: str) -> Path:
    return flowpilot_router_event_intake.next_quarantined_role_report_path(_bound_router(), run_root, event)

def _clear_stale_role_wait_for_quarantined_report(
    run_state: dict[str, Any],
    pending_return: dict[str, Any],
    event: str,
) -> str:
    return flowpilot_router_event_intake.clear_stale_role_wait_for_quarantined_report(
        _bound_router(),
        run_state,
        pending_return,
        event,
    )

def _quarantine_missing_ack_report_before_external_event(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None,
    envelope_hash: str | None,
    pending_return: dict[str, Any],
) -> dict[str, Any] | None:
    return flowpilot_router_event_intake.quarantine_missing_ack_report_before_external_event(
        _bound_router(),
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload,
        envelope_path=envelope_path,
        envelope_hash=envelope_hash,
        pending_return=pending_return,
    )

def _record_card_return_event_from_external_entrypoint(project_root: Path, event: str) -> dict[str, Any]:
    del project_root
    raise RouterError(
        f"{event} is a system-card ACK return event, and the unsupported record-event ACK path is disabled. "
        "The addressed role must run the card check-in command from the envelope so the ACK is submitted "
        "directly to Router with its direct Router ACK token."
    )

def _committed_card_bundle_artifact_extra(
    project_root: Path,
    record: dict[str, Any],
    *,
    relay_allowed_if_ready: bool,
) -> dict[str, Any]:
    return flowpilot_router_card_returns._committed_card_bundle_artifact_extra(_bound_router(), project_root, record, relay_allowed_if_ready=relay_allowed_if_ready)

def _auto_commit_system_card_delivery_action(
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
    action: dict[str, Any],
) -> dict[str, Any]:
    return flowpilot_router_action_handlers.auto_commit_system_card_delivery_action(
        _bound_router(),
        project_root,
        run_state,
        run_root,
        action,
    )

__all__ = (
    '_pending_return_record_for_action',
    '_pending_bundle_return_record_for_action',
    '_apply_card_return_event_check',
    '_apply_card_bundle_return_event_check',
    '_try_auto_consume_pending_card_return_ack',
    '_startup_pm_card_bundle_ack_record',
    '_reconcile_card_wait_rows',
    '_reconcile_card_bundle_wait_rows',
    '_router_release_startup_user_intake_to_pm',
    '_run_router_return_settlement_finalizers',
    '_mark_card_return_pending_explicit_check',
    '_preconsume_pending_card_return_ack_before_external_event',
    '_system_card_delivery_flag',
    '_pending_return_card_delivery_flags',
    '_role_list',
    '_pending_card_return_matches_event_dependency',
    '_next_quarantined_role_report_path',
    '_clear_stale_role_wait_for_quarantined_report',
    '_quarantine_missing_ack_report_before_external_event',
    '_record_card_return_event_from_external_entrypoint',
    '_committed_card_bundle_artifact_extra',
    '_auto_commit_system_card_delivery_action',
)

_LOCAL_NAMES = set(globals())
