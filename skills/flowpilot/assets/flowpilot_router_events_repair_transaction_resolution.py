"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints stay aligned.
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

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _control_blocker_allows_resolution_event(router: ModuleType, record: dict[str, Any], event: str) -> bool:
    _bind_router(router)
    if record.get('handling_lane') in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return False
    raw_events = record.get('allowed_resolution_events')
    if isinstance(raw_events, list) and raw_events:
        allowed_events = {name for item in raw_events if (name := router._control_resolution_event_name(item))}
        return event in allowed_events
    if record.get('handling_lane') == 'control_plane_reissue':
        return event == record.get('originating_event')
    return event in EXTERNAL_EVENTS

def _control_resolution_event_name(router: ModuleType, value: Any) -> str | None:
    _bind_router(router)
    if isinstance(value, dict):
        for key in ('event', 'corrected_followup_event', 'event_name'):
            name = str(value.get(key) or '').strip()
            if name:
                return router._control_resolution_event_name(name)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text in EXTERNAL_EVENTS:
        return text
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return None
    return router._control_resolution_event_name(parsed)

def _resolve_delivered_control_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, resolved_by_event: str, from_already_recorded_event: bool=False) -> dict[str, Any] | None:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('delivery_status') != 'delivered':
        return None
    record = dict(active)
    artifact_rel = str(active.get('blocker_artifact_path') or '')
    artifact_path: Path | None = None
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            record = read_json(artifact_path)
    if from_already_recorded_event:
        lane = record.get('handling_lane')
        pm_repair_recorded = lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and record.get('pm_repair_decision_status') == 'recorded'
        if lane != 'control_plane_reissue' and (not pm_repair_recorded):
            return None
    if not router._control_blocker_allows_resolution_event(record, resolved_by_event):
        return None
    if artifact_path and artifact_path.exists():
        resolved_at = utc_now()
        record['resolution_status'] = 'accepted_followup_event_recorded'
        record['resolved_by_event'] = resolved_by_event
        record['resolved_at'] = resolved_at
        write_json(artifact_path, record)
    resolved = dict(active)
    resolved['resolution_status'] = 'accepted_followup_event_recorded'
    resolved['resolved_by_event'] = resolved_by_event
    resolved['resolved_at'] = record.get('resolved_at') or utc_now()
    run_state.setdefault('resolved_control_blockers', []).append(resolved)
    run_state['active_control_blocker'] = None
    run_state['latest_control_blocker_path'] = None
    append_history(run_state, 'router_resolved_control_blocker', {'blocker_id': resolved.get('blocker_id'), 'resolved_by_event': resolved_by_event})
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    return resolved

__all__ = (
    '_control_blocker_allows_resolution_event',
    '_control_resolution_event_name',
    '_resolve_delivered_control_blocker',
)

_LOCAL_NAMES = set(globals())
