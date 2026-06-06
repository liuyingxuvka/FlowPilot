"""Coarse events repair owner helpers for the FlowPilot router.

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

def _control_blocker_repair_origin(router: ModuleType, active: dict[str, Any], *, rerun_target: str, requested_plan_kind: str, run_root: Path, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    originating_event = str(active.get('originating_event') or '')
    if requested_plan_kind == 'packet_reissue' or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS or originating_event in MATERIAL_REPAIR_OUTCOME_EVENTS:
        return 'material_dispatch'
    if rerun_target in PARENT_REPAIR_SAFE_EVENTS or originating_event in PARENT_REPAIR_SAFE_EVENTS or run_state.get('flags', {}).get('parent_backward_replay_blocked'):
        return 'parent_backward_replay'
    if rerun_target in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS or originating_event in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'current_node_result'
    try:
        if router._active_node_kind_for_event_capability(run_root) in {'parent', 'module'} and originating_event in {'pm_records_parent_segment_decision', 'pm_completes_parent_node_from_backward_replay'}:
            return 'parent_backward_replay'
    except (RouterError, OSError, ValueError, TypeError):
        pass
    return 'none'

def _repair_outcome_table(router: ModuleType, rerun_target: str, *, repair_origin: str='none') -> dict[str, dict[str, Any]]:
    _bind_router(router)
    if rerun_target == 'router_direct_material_scan_dispatch_recheck_passed':
        return {'success': {'event': 'router_direct_material_scan_dispatch_recheck_passed', 'terminal': 'complete'}, 'blocker': {'event': 'router_direct_material_scan_dispatch_recheck_blocked', 'terminal': 'blocked'}, 'protocol_blocker': {'event': 'router_protocol_blocker_material_scan_dispatch_recheck', 'terminal': 'blocked'}}
    if repair_origin == 'parent_backward_replay':
        if rerun_target not in PARENT_REPAIR_SAFE_EVENTS:
            raise RouterError('parent backward replay repair rerun_target must be a parent-safe event')
        if rerun_target in {'reviewer_blocks_parent_backward_replay', PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
            raise RouterError('parent backward replay repair rerun_target must be a success-capable parent event')
        return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': 'reviewer_blocks_parent_backward_replay', 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_PARENT_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}
    if rerun_target in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS or rerun_target == PM_PARENT_PROTOCOL_BLOCKER_EVENT:
        raise RouterError('control blocker repair rerun_target must be a success-capable follow-up event')
    return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT, 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}

def _validate_repair_outcome_table(router: ModuleType, outcome_table: dict[str, Any], *, context: str, run_root: Path, run_state: dict[str, Any], repair_origin: str) -> None:
    _bind_router(router)
    events_by_kind: dict[str, str] = {}
    for kind in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(kind)
        if not isinstance(outcome, dict):
            raise RouterError(f'{context} requires {kind} outcome row')
        event = str(outcome.get('event') or '').strip()
        if not event:
            raise RouterError(f'{context} {kind} outcome row requires event')
        events_by_kind[kind] = event
    if len(set(events_by_kind.values())) != len(events_by_kind):
        raise RouterError(f'{context} must use distinct success, blocker, and protocol-blocker events')
    for kind, event in events_by_kind.items():
        router._validated_event_capability_names([event], context=f'{context} {kind} outcome', run_root=run_root, run_state=run_state, usage='repair_outcome', repair_origin=repair_origin, outcome_kind=kind, allow_pm_repair_event=False)

def _repair_outcome_events(router: ModuleType, outcome_table: dict[str, Any]) -> list[str]:
    _bind_router(router)
    events: list[str] = []
    for name in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(name)
        if not isinstance(outcome, dict):
            continue
        event = str(outcome.get('event') or '').strip()
        if event and event not in events:
            events.append(event)
    return events

def _repair_packet_specs_from_decision(router: ModuleType, project_root: Path, run_root: Path, decision: dict[str, Any], *, rerun_target: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    _bind_router(router)
    transaction = decision.get('repair_transaction') if isinstance(decision.get('repair_transaction'), dict) else {}
    raw_packets = transaction.get('replacement_packets') or transaction.get('packets') or decision.get('replacement_packets') or decision.get('packets')
    if isinstance(raw_packets, list) and raw_packets:
        return (raw_packets, {'source': 'decision_inline', 'packet_count': len(raw_packets)})
    raw_path = transaction.get('replacement_packet_specs_path') or transaction.get('packet_reissue_spec_path') or decision.get('replacement_packet_specs_path') or decision.get('packet_reissue_spec_path')
    if not raw_path and rerun_target == 'router_direct_material_scan_dispatch_recheck_passed':
        default_path = run_root / 'material' / 'pm_material_scan_packet_specs_reissue.project_manager.json'
        if default_path.exists():
            raw_path = project_relative(project_root, default_path)
    if not raw_path:
        return ([], None)
    spec_path = resolve_project_path(project_root, str(raw_path))
    if not spec_path.exists():
        raise RouterError(f'repair transaction packet spec path is missing: {raw_path}')
    expected_hash = transaction.get('replacement_packet_specs_hash') or transaction.get('packet_reissue_spec_hash') or decision.get('replacement_packet_specs_hash') or decision.get('packet_reissue_spec_hash')
    if expected_hash and packet_runtime.sha256_file(spec_path) != str(expected_hash):
        raise RouterError('repair transaction packet spec hash mismatch')
    spec = read_json(spec_path)
    packets = spec.get('packets')
    if not isinstance(packets, list) or not packets:
        raise RouterError('repair transaction packet spec requires non-empty packets')
    return (packets, {'source': 'packet_spec_file', 'path': project_relative(project_root, spec_path), 'sha256': packet_runtime.sha256_file(spec_path), 'packet_count': len(packets)})

__all__ = (
    '_control_blocker_repair_origin',
    '_repair_outcome_table',
    '_validate_repair_outcome_table',
    '_repair_outcome_events',
    '_repair_packet_specs_from_decision',
)

_LOCAL_NAMES = set(globals())
