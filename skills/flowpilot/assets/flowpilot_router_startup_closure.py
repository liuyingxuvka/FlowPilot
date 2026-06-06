"""Startup owner helpers extracted from ``flowpilot_router_startup_flow``.

This module is part of the startup StructureMesh split. It is bound to the
router skeleton before execution so cross-owner transitional lookups stay
explicit while startup behavior is owned by smaller modules.
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


OWNER_MODULE = 'flowpilot_router_startup_closure'

def _defect_ledger_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = run_root / 'defects' / 'defect_ledger.json'
    status: dict[str, Any] = {'present': path.exists(), 'path': project_relative(project_root, path) if path.exists() else None, 'required_for_current_run': False, 'absence_is_pass_claim': False, 'blocker_open_count': 0, 'fixed_pending_recheck_count': 0, 'closed_defect_missing_recheck_count': 0, 'issue_count': 0, 'issues': [], 'clean': True}
    if not path.exists():
        return status
    ledger = read_json(path)
    issues: list[str] = []
    if ledger.get('schema_version') != 'flowpilot.defect_ledger.v1':
        issues.append('schema_version mismatch')
    counts = ledger.get('counts') if isinstance(ledger.get('counts'), dict) else {}
    defects = ledger.get('defects') if isinstance(ledger.get('defects'), list) else []
    count_blocker_open = int(counts.get('blocker_open', 0) or 0)
    count_fixed_pending = int(counts.get('fixed_pending_recheck', 0) or 0)
    scan_blocker_open = 0
    scan_fixed_pending = 0
    closed_missing_recheck = 0
    for defect in defects:
        if not isinstance(defect, dict):
            continue
        defect_status = str(defect.get('status') or '').lower()
        severity = str(defect.get('severity') or '').lower()
        if severity == 'blocker' and defect_status in {'open', 'accepted', 'fixing'}:
            scan_blocker_open += 1
        if defect_status == 'fixed_pending_recheck':
            scan_fixed_pending += 1
        pm_triage = defect.get('pm_triage') if isinstance(defect.get('pm_triage'), dict) else {}
        recheck_role = str(pm_triage.get('recheck_role_class') or '').lower()
        if defect_status == 'closed' and recheck_role not in {'', 'none'} and (not defect.get('recheck_paths')):
            closed_missing_recheck += 1
    blocker_open = max(count_blocker_open, scan_blocker_open, 0)
    fixed_pending = max(count_fixed_pending, scan_fixed_pending, 0)
    if blocker_open:
        issues.append('blocker defects remain open')
    if fixed_pending:
        issues.append('defects are fixed but pending recheck')
    if closed_missing_recheck:
        issues.append('closed defects are missing required recheck evidence')
    status.update({'required_for_current_run': True, 'blocker_open_count': blocker_open, 'fixed_pending_recheck_count': fixed_pending, 'closed_defect_missing_recheck_count': closed_missing_recheck, 'issue_count': len(issues), 'issues': issues, 'clean': not issues})
    return status

def _role_memory_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    memory_root = run_root / 'role_binding_memory'
    files = sorted(memory_root.glob('*.json')) if memory_root.exists() else []
    expected_run_id = str(run_state.get('run_id') or run_root.name)
    issues: list[str] = []
    stale_paths: list[str] = []
    role_keys_seen: set[str] = set()
    historical_authority_count = 0
    for path in files:
        memory = read_json(path)
        rel_path = project_relative(project_root, path)
        if memory.get('schema_version') != 'flowpilot.role_memory.v1':
            issues.append(f'{rel_path}: schema_version mismatch')
        role_key = str(memory.get('role_key') or path.stem)
        if role_key not in RUNTIME_ROLE_KEYS:
            issues.append(f'{rel_path}: unknown role_key')
        else:
            role_keys_seen.add(role_key)
        if str(memory.get('run_id') or '') != expected_run_id:
            stale_paths.append(rel_path)
            issues.append(f'{rel_path}: run_id does not match current run')
        identity_policy = memory.get('identity_policy') if isinstance(memory.get('identity_policy'), dict) else {}
        if identity_policy and identity_policy.get('agent_id_is_diagnostic_only') is False:
            historical_authority_count += 1
            issues.append(f'{rel_path}: agent_id is not diagnostic-only')
        last_rehydration = memory.get('last_rehydration') if isinstance(memory.get('last_rehydration'), dict) else {}
        if last_rehydration.get('historical_agent_id_reused') is True:
            historical_authority_count += 1
            issues.append(f'{rel_path}: historical agent id reused')
        if memory.get('controller_decision_authority') is True or memory.get('role_memory_used_for_completion_authority') is True:
            historical_authority_count += 1
            issues.append(f'{rel_path}: role memory claims completion authority')
    missing_roles = [role for role in RUNTIME_ROLE_KEYS if files and role not in role_keys_seen]
    return {'present': bool(files), 'path': project_relative(project_root, memory_root) if memory_root.exists() else None, 'required_for_current_run': bool(files), 'absence_is_pass_claim': False, 'file_count': len(files), 'role_count': len(role_keys_seen), 'missing_role_keys': missing_roles, 'stale_role_memory_paths': stale_paths, 'historical_agent_authority_count': historical_authority_count, 'issue_count': len(issues), 'issues': issues, 'clean': not issues}

def _continuation_quarantine_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    path = router._continuation_quarantine_path(run_root)
    status: dict[str, Any] = {'present': path.exists(), 'path': project_relative(project_root, path) if path.exists() else None, 'required_for_current_run': path.exists(), 'absence_is_pass_claim': False, 'current_pointer_matches_run': None, 'prior_run_files_are_evidence_by_default': None, 'old_agent_ids_are_current_authority': None, 'old_assets_are_current_evidence_by_default': None, 'old_agent_id_count': 0, 'old_asset_count': 0, 'issue_count': 0, 'issues': [], 'clean': True}
    if not path.exists():
        return status
    record = read_json(path)
    issues = list(flowpilot_runtime_closure.validate_continuation_quarantine_record(record))
    old_agent_ids = record.get('old_agent_ids') if isinstance(record.get('old_agent_ids'), list) else []
    old_assets = record.get('old_assets') if isinstance(record.get('old_assets'), list) else []
    imported_authority_count = 0
    for item in old_agent_ids:
        if isinstance(item, dict) and item.get('current_authority') is True:
            imported_authority_count += 1
    for item in old_assets:
        if isinstance(item, dict) and (item.get('current_evidence') is True or item.get('current_authority') is True):
            imported_authority_count += 1
    if imported_authority_count:
        issues.append('imported old artifacts still claim current authority')
    if record.get('current_pointer_matches_run') is False:
        issues.append('current pointer does not match run')
    status.update({'current_pointer_matches_run': record.get('current_pointer_matches_run'), 'prior_run_files_are_evidence_by_default': record.get('prior_run_files_are_evidence_by_default'), 'old_agent_ids_are_current_authority': record.get('old_agent_ids_are_current_authority'), 'old_assets_are_current_evidence_by_default': record.get('old_assets_are_current_evidence_by_default'), 'old_agent_id_count': len(old_agent_ids), 'old_asset_count': len(old_assets), 'imported_artifact_authority_count': imported_authority_count, 'issue_count': len(issues), 'issues': issues, 'clean': not issues})
    return status

def _terminal_closure_reconciliation_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    defect_status = router._defect_ledger_reconciliation_status(project_root, run_root)
    role_memory_status = router._role_memory_reconciliation_status(project_root, run_root, run_state)
    quarantine_status = router._continuation_quarantine_reconciliation_status(project_root, run_root)
    families = {'defect_ledger': defect_status, 'role_memory': role_memory_status, 'continuation_quarantine': quarantine_status}
    dirty = [name for name, family_status in families.items() if not bool(family_status.get('clean'))]
    return {'schema_version': 'flowpilot.terminal_closure_reconciliation.v1', 'clean': not dirty, 'dirty_families': dirty, 'defect_ledger': defect_status, 'role_memory': role_memory_status, 'continuation_quarantine': quarantine_status}

def _closure_reconciliation_blocker_message(router: ModuleType, status: dict[str, Any]) -> str:
    _bind_router(router)
    dirty = status.get('dirty_families') if isinstance(status.get('dirty_families'), list) else []
    if not dirty:
        return 'terminal closure reconciliation is dirty'
    details = []
    for family in dirty:
        family_status = status.get(str(family)) if isinstance(status.get(str(family)), dict) else {}
        issues = family_status.get('issues') if isinstance(family_status.get('issues'), list) else []
        first_issue = str(issues[0]) if issues else 'dirty'
        details.append(f'{family}: {first_issue}')
    return '; '.join(details)

def _closure_reconciliation_entries(router: ModuleType, project_root: Path, status: dict[str, Any], *, route_version: int) -> list[dict[str, Any]]:
    _bind_router(router)
    entries: list[dict[str, Any]] = []
    for family in ('defect_ledger', 'role_memory', 'continuation_quarantine'):
        family_status = status.get(family) if isinstance(status.get(family), dict) else {}
        path = family_status.get('path')
        entries.append({'entry_id': f'closure_reconciliation:{family}', 'route_version': route_version, 'gate_family': 'terminal_closure_reconciliation', 'required_approver': 'project_manager', 'status': 'approved' if family_status.get('clean') and family_status.get('present') else 'not_present' if family_status.get('clean') else 'blocked', 'source_of_truth_paths': [path] if isinstance(path, str) and path else [], 'evidence_paths': [path] if isinstance(path, str) and path else [], 'reconciliation': family_status})
    return entries

def _current_closure_state_clean(router: ModuleType, project_root: Path, run_root: Path) -> bool:
    _bind_router(router)
    evidence = read_json_if_exists(run_root / 'evidence' / 'evidence_ledger.json')
    generated = read_json_if_exists(run_root / 'generated_resource_ledger.json')
    final_ledger = read_json_if_exists(run_root / 'final_route_wide_gate_ledger.json')
    terminal = read_json_if_exists(run_root / 'reviews' / 'terminal_backward_replay.json')
    task_projection = read_json_if_exists(_task_completion_projection_path(run_root))
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    route_id = str(frontier.get('active_route_id') or 'route-001')
    mutations = read_json_if_exists(run_root / 'routes' / route_id / 'mutations.json')
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    self_interrogation_status = _self_interrogation_status(project_root, run_root)
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, {})
    return evidence.get('unresolved_count') == 0 and evidence.get('stale_count') == 0 and (generated.get('pending_resource_count') == 0) and (generated.get('unresolved_resource_count') == 0) and (final_ledger.get('completion_allowed') is True) and (final_ledger.get('counts', {}).get('unresolved_count') == 0) and (terminal.get('passed') is True) and (task_projection.get('task_status') == 'ready_for_pm_terminal_closure') and pm_suggestion_status['clean'] and self_interrogation_status['clean'] and closure_reconciliation['clean'] and (not router._route_mutation_completion_issues(frontier, mutations))

def _invalidate_route_completion_if_dirty_before_closure(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('final_backward_replay_passed'):
        return
    if flags.get('pm_closure_approved'):
        return
    if router._current_closure_state_clean(project_root, run_root):
        return
    _reset_flags(run_state, ROUTE_COMPLETION_FLAGS)
    append_history(run_state, 'route_completion_cycle_invalidated_by_dirty_closure_state', {'reason': 'completion ledgers changed after terminal backward replay and before PM closure', 'restart_from': 'pm.evidence_quality_package'})

_LOCAL_NAMES = set(globals())
