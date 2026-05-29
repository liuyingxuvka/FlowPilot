"""Coarse event dispatcher owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
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
import flowpilot_router_role_output_bridge_events as role_output_bridge_events
import flowpilot_user_flow_diagram
import packet_runtime
import role_output_runtime
from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write
from flowpilot_prompt_store import PromptStoreError, card_manifest_entry, load_card_manifest_from_run
from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress

_DEFAULT_SENTINEL = object()
_DIRECT_EVENT_QUARANTINE_CLASSES = {
    "terminal_quarantine",
    "pm_repair_owned_stale_conflict",
    "control_blocker_owned_stale_conflict",
    "canonical_package_authority_stale_conflict",
}


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _quarantine_direct_scoped_event_conflict(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None,
    envelope_hash: str | None,
    scoped_identity: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(scoped_identity, dict):
        return None
    classification = _classify_scoped_event_conflict(run_state, scoped_identity)
    stale_unowned = role_output_bridge_events._classify_stale_unowned_pm_package_replay(
        router,
        project_root,
        run_root,
        event,
        scoped_identity,
        classification,
    )
    if stale_unowned is not None:
        classification = stale_unowned
    if classification.get("classification") not in _DIRECT_EVENT_QUARANTINE_CLASSES:
        return None

    scope = scoped_identity.get("scope") if isinstance(scoped_identity.get("scope"), dict) else {}
    payload_hash = _stable_identity_hash(payload or {})
    quarantine_key = "|".join(
        str(part or "")
        for part in (
            event,
            classification.get("classification"),
            scoped_identity.get("dedupe_key"),
            scope.get("body_hash"),
            envelope_hash,
            payload_hash,
        )
    )
    rows = run_state.setdefault("direct_event_quarantine", [])
    already_quarantined = any(
        isinstance(row, dict) and row.get("quarantine_key") == quarantine_key
        for row in rows
    )
    record = {
        "schema_version": "flowpilot.direct_event_quarantine.v1",
        "status": "quarantined_audit_only",
        "event": event,
        "classification": classification.get("classification"),
        "dedupe_key": scoped_identity.get("dedupe_key"),
        "quarantine_key": quarantine_key,
        "mismatches": classification.get("mismatches") or [],
        "owner": classification.get("owner"),
        "payload_hash": payload_hash,
        "envelope_path": envelope_path,
        "envelope_hash": envelope_hash,
        "quarantined_at": utc_now(),
    }
    if not already_quarantined:
        rows.append(record)
        path = run_root / "runtime" / "direct_event_quarantine.jsonl"
        assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="append_direct_event_quarantine")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        append_history(
            run_state,
            "router_quarantined_direct_package_disposition_conflict",
            record,
        )
        router._refresh_route_memory(project_root, run_root, run_state, trigger=f"after_direct_event_quarantine:{event}")
        router._sync_derived_run_views(project_root, run_root, run_state, reason=f"after_direct_event_quarantine:{event}")
        router.save_run_state(run_root, run_state)

    return {
        "ok": True,
        "event": event,
        "quarantined": True,
        "already_quarantined": already_quarantined,
        "classification": classification.get("classification"),
        "dedupe_key": scoped_identity.get("dedupe_key"),
        "quarantine_key": quarantine_key,
    }


_DIRECT_PACKAGE_DISPOSITION_DOMAIN_COMMITS = {
    "pm_records_material_scan_result_disposition": {
        "batch_kind": "material_scan",
        "package_label": "material_scan",
        "gate_kind": "material_sufficiency",
        "output_path": Path("material") / "pm_material_scan_result_disposition.json",
    },
    "pm_records_research_result_disposition": {
        "batch_kind": "research",
        "package_label": "research",
        "gate_kind": "research_direct_source_check",
        "output_path": Path("research") / "pm_research_result_disposition.json",
    },
    "pm_records_current_node_result_disposition": {
        "batch_kind": "current_node",
        "package_label": "current_node",
        "gate_kind": "node_completion",
        "output_path": None,
    },
}


def _direct_package_disposition_output_path(run_root: Path, event: str) -> Path:
    config = _DIRECT_PACKAGE_DISPOSITION_DOMAIN_COMMITS[event]
    if event == "pm_records_current_node_result_disposition":
        frontier = _active_frontier(run_root)
        return _active_node_root(run_root, frontier) / "reviews" / "pm_current_node_result_disposition.json"
    return run_root / str(config["output_path"])


def _repair_direct_package_disposition_authority_split(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    scoped_identity: dict[str, Any] | None,
    envelope_hash: str | None,
) -> dict[str, Any] | None:
    _bind_router(router)
    split = role_output_bridge_events._package_disposition_authority_split(
        router,
        project_root,
        run_root,
        run_state,
        event,
        scoped_identity,
    )
    if split is None:
        return None
    config = _DIRECT_PACKAGE_DISPOSITION_DOMAIN_COMMITS.get(event)
    if config is None:
        return None
    try:
        output_path = _direct_package_disposition_output_path(run_root, event)
        router._write_pm_package_result_disposition(
            project_root,
            run_root,
            run_state,
            payload or {},
            batch_kind=str(config["batch_kind"]),
            package_label=str(config["package_label"]),
            gate_kind=str(config["gate_kind"]),
            output_path=output_path,
            router_event=event,
        )
        artifact = read_json_if_exists(output_path)
        if artifact.get("schema_version") != "flowpilot.pm_package_result_disposition.v1":
            raise RouterError(f"event {event} did not commit a valid PM package disposition artifact")
    except (RouterError, role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError, TypeError, ValueError):
        split_record = role_output_bridge_events._record_package_disposition_authority_split(
            router,
            project_root,
            run_root,
            run_state,
            split=split,
            source="direct_event",
            envelope_hash=envelope_hash,
        )
        if not split_record.get("already_recorded"):
            append_history(
                run_state,
                "router_blocked_direct_package_disposition_authority_split",
                split_record,
            )
            router._refresh_route_memory(project_root, run_root, run_state, trigger=f"after_direct_package_authority_split:{event}")
            router._sync_derived_run_views(project_root, run_root, run_state, reason=f"after_direct_package_authority_split:{event}")
            router.save_run_state(run_root, run_state)
        return {
            "ok": False,
            "event": event,
            "recoverable": True,
            "blocked": True,
            "classification": split.get("classification"),
            "authority_split": True,
            "dedupe_key": split.get("dedupe_key"),
            "split_key": split_record.get("split_key"),
            "repair_required": True,
        }
    domain_commit = {
        "schema_version": "flowpilot.repaired_direct_event_domain_commit.v1",
        "event": event,
        "artifact_kind": "pm_package_result_disposition",
        "artifact_path": project_relative(project_root, output_path),
        "artifact_hash": packet_runtime.sha256_file(output_path),
        "batch_kind": config["batch_kind"],
        "source_body_hash": artifact.get("source_body_hash"),
        "decision": artifact.get("decision"),
    }
    run_state.setdefault("flags", {})[EXTERNAL_EVENTS[event]["flag"]] = True
    wait_closure = _close_waiting_controller_actions_for_external_event(
        project_root,
        run_root,
        run_state,
        event=event,
        payload=payload or {},
        source="direct_event_repaired_package_disposition_authority_split",
    )
    append_history(
        run_state,
        "router_repaired_direct_package_disposition_authority_split",
        {
            "event": event,
            "split": split,
            "domain_commit": domain_commit,
            "wait_closure": wait_closure,
        },
    )
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f"after_direct_package_authority_repair:{event}")
    router._sync_derived_run_views(project_root, run_root, run_state, reason=f"after_direct_package_authority_repair:{event}")
    router.save_run_state(run_root, run_state)
    return {
        "ok": True,
        "event": event,
        "already_recorded": True,
        "domain_commit_repaired": True,
        "classification": split.get("classification"),
        "authority_split": True,
        "dedupe_key": split.get("dedupe_key"),
        "domain_commit": domain_commit,
        "wait_closure": wait_closure,
    }




from flowpilot_router_event_dispatcher_record import _record_external_event_unchecked
_LOCAL_NAMES = set(globals())
