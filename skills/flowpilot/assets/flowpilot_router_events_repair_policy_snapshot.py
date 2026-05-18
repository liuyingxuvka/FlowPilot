"""Coarse events repair owner helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`. This module owns a
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


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _control_blocker_error_code(router: ModuleType, message: str) -> str:
    _bind_router(router)
    cleaned: list[str] = []
    for char in message.lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != '_':
            cleaned.append('_')
    code = ''.join(cleaned).strip('_')
    return code[:96] or 'router_hard_rejection'

def _blocker_repair_policy_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'control_blocks' / 'blocker_repair_policy_snapshot.json'

def _blocker_repair_policy_rows(router: ModuleType) -> list[dict[str, Any]]:
    _bind_router(router)
    return [_json_safe(BLOCKER_REPAIR_POLICY_ROWS[key]) for key in sorted(BLOCKER_REPAIR_POLICY_ROWS)]

def _write_blocker_repair_policy_snapshot(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    path = router._blocker_repair_policy_snapshot_path(run_root)
    payload = {'schema_version': BLOCKER_REPAIR_POLICY_SCHEMA, 'run_id': run_state.get('run_id'), 'created_at': utc_now(), 'policy_scope': 'new_control_blockers', 'rows': router._blocker_repair_policy_rows()}
    write_json(path, payload)
    rel = project_relative(project_root, path)
    run_state['blocker_repair_policy_snapshot'] = rel
    return rel

def _control_blocker_policy_row(router: ModuleType, error_message: str, category: str) -> dict[str, Any]:
    _bind_router(router)
    lowered = error_message.lower()
    if 'self-interrogation' in lowered or 'self_interrogation' in lowered:
        return dict(BLOCKER_REPAIR_POLICY_ROWS['self_interrogation_repair'])
    if category == 'control_plane_reissue':
        return dict(BLOCKER_REPAIR_POLICY_ROWS['mechanical_control_plane_reissue'])
    if category == 'fatal_protocol_violation':
        return dict(BLOCKER_REPAIR_POLICY_ROWS['fatal_protocol_violation'])
    return dict(BLOCKER_REPAIR_POLICY_ROWS['pm_semantic_repair'])

def _control_blocker_attempt_key(router: ModuleType, *, policy_row_id: str, event: str | None, action_type: str | None, responsible_role: str) -> str:
    _bind_router(router)
    return '|'.join((policy_row_id, event or '', action_type or '', responsible_role or ''))

def _control_blocker_direct_attempts_used(router: ModuleType, run_state: dict[str, Any], attempt_key: str) -> int:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('attempt_key') != attempt_key:
        return 0
    if active.get('target_role') == 'project_manager':
        return int(active.get('direct_retry_attempts_used') or 0)
    return int(active.get('direct_retry_attempts_used') or 0) + 1

def _policy_first_handler_target(router: ModuleType, policy_row: dict[str, Any], responsible_role: str) -> str:
    _bind_router(router)
    first_handler = str(policy_row.get('first_handler') or 'project_manager')
    if first_handler == 'responsible_role':
        return responsible_role
    return first_handler

def _pm_recovery_options_from_policy(router: ModuleType, policy_row: dict[str, Any]) -> list[str]:
    _bind_router(router)
    raw = policy_row.get('pm_recovery_options')
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if str(item)]
    return list(PM_BLOCKER_RECOVERY_OPTIONS)

def _default_pm_recovery_option(router: ModuleType, active: dict[str, Any], requested_plan_kind: str) -> str:
    _bind_router(router)
    policy_row_id = str(active.get('policy_row_id') or '')
    if policy_row_id == 'fatal_protocol_violation':
        return 'evidence_quarantine'
    if policy_row_id == 'self_interrogation_repair':
        return 'record_disposition'
    if requested_plan_kind == 'route_mutation':
        return 'route_mutation'
    if requested_plan_kind == 'packet_reissue':
        return 'same_gate_repair'
    return 'same_gate_repair'

def _project_relative_if_possible(router: ModuleType, project_root: Path, path: Path) -> str:
    _bind_router(router)
    try:
        return project_relative(project_root, path)
    except RouterError:
        return str(path)

def _payload_source_paths(router: ModuleType, project_root: Path, run_root: Path, payload: dict[str, Any] | None) -> dict[str, str]:
    _bind_router(router)
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root))}
    packet_ledger = run_root / 'packet_ledger.json'
    if packet_ledger.exists():
        source_paths['packet_ledger'] = project_relative(project_root, packet_ledger)
    if not isinstance(payload, dict):
        return source_paths
    for key in ('body_path', 'report_path', 'decision_path', 'result_body_path', 'packet_envelope_path', 'result_envelope_path', 'packet_index_path', 'path'):
        raw = payload.get(key)
        if not raw:
            continue
        candidate = resolve_project_path(project_root, str(raw))
        source_paths[key] = router._project_relative_if_possible(project_root, candidate)
    return source_paths

def _control_payload_public_view(router: ModuleType, payload: dict[str, Any] | None) -> dict[str, Any]:
    _bind_router(router)
    if not isinstance(payload, dict):
        return {}
    forbidden_body_keys = {'blockers', 'checks', 'commands', 'decision', 'decision_body', 'evidence', 'findings', 'passed', 'direct_material_sources_checked', 'packet_matches_checked_sources', 'pm_ready', 'recommendations', 'repair_instructions', 'report_body', 'result_body'}
    public: dict[str, Any] = {}
    for key, value in payload.items():
        if key in forbidden_body_keys:
            public[key] = '[redacted: role body field was controller-visible]'
            continue
        if key.endswith('_path') or key.endswith('_hash') or key in {'packet_id', 'route_id', 'node_id', 'role', 'from_role', 'to_role', 'expected_role', 'completed_by_role', 'reviewed_by_role', 'controller_visibility', 'chat_response_body_allowed'}:
            public[key] = _json_safe(value)
    return public

__all__ = (
    '_control_blocker_error_code',
    '_blocker_repair_policy_snapshot_path',
    '_blocker_repair_policy_rows',
    '_write_blocker_repair_policy_snapshot',
    '_control_blocker_policy_row',
    '_control_blocker_attempt_key',
    '_control_blocker_direct_attempts_used',
    '_policy_first_handler_target',
    '_pm_recovery_options_from_policy',
    '_default_pm_recovery_option',
    '_project_relative_if_possible',
    '_payload_source_paths',
    '_control_payload_public_view',
)

_LOCAL_NAMES = set(globals())
