"""Terminal summary helpers for the FlowPilot router.

Receives the router facade explicitly so shared state writers and
public entrypoints keep the bound-router compatibility contract.
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


def _terminal_summary_index_entry(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json')
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    run_id = run_state.get('run_id')
    for item in runs:
        if isinstance(item, dict) and item.get('run_id') == run_id:
            return item
    return None

def _terminal_summary_written(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> bool:
    _bind_router(router)
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    if not markdown_path.exists() or not json_path.exists():
        return False
    try:
        summary_markdown = markdown_path.read_text(encoding='utf-8')
        summary_record = read_json(json_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RouterError):
        return False
    if not summary_markdown.startswith(TERMINAL_SUMMARY_ATTRIBUTION):
        return False
    if summary_record.get('schema_version') != TERMINAL_SUMMARY_SCHEMA:
        return False
    if summary_record.get('run_id') != run_state.get('run_id'):
        return False
    if summary_record.get('run_lifecycle_status') != _terminal_lifecycle_mode(run_state):
        return False
    summary_hash = _terminal_summary_hash(summary_markdown)
    if summary_record.get('summary_sha256') != summary_hash:
        return False
    if summary_record.get('flowpilot_project_url') != FLOWPILOT_PROJECT_URL:
        return False
    entry = router._terminal_summary_index_entry(project_root, run_state)
    if not isinstance(entry, dict):
        return False
    return entry.get('final_summary_path') == project_relative(project_root, markdown_path) and entry.get('final_summary_json_path') == project_relative(project_root, json_path) and (entry.get('flowpilot_project_url') == FLOWPILOT_PROJECT_URL)

def _terminal_summary_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path, *, mode: str) -> dict[str, Any]:
    _bind_router(router)
    run_root_rel = project_relative(project_root, run_root)
    markdown_rel = project_relative(project_root, _terminal_summary_markdown_path(run_root))
    json_rel = project_relative(project_root, _terminal_summary_json_path(run_root))
    index_rel = project_relative(project_root, project_root / '.flowpilot' / 'index.json')
    state_rel = project_relative(project_root, router.run_state_path(run_root))
    current_rel = project_relative(project_root, project_root / '.flowpilot' / 'current.json')
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(action_type='write_terminal_summary', actor='controller', label=f'controller_writes_terminal_summary_for_{mode}', summary='The run is terminal. Read all files under the current run root, write a short final summary with FlowPilot GitHub attribution, show the same summary to the user, then stop route work.', allowed_reads=[f'{run_root_rel}/**', lifecycle_rel, state_rel, current_rel, index_rel], allowed_writes=[markdown_rel, json_rel, index_rel, current_rel, state_rel], extra={'run_lifecycle_status': mode, 'terminal_for_route': True, 'summary_schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'summary_markdown_path': markdown_rel, 'summary_json_path': json_rel, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'required_attribution_line': TERMINAL_SUMMARY_ATTRIBUTION, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'controller_may_read_all_current_run_files': True, 'sealed_body_reads_allowed': True, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'controller_may_approve_or_reopen_gates': False, 'controller_may_create_project_evidence': False, 'final_user_report_is_completion_authority': False, 'report_after_lifecycle_terminal': True, 'requires_payload': True, 'payload_contract': _terminal_summary_payload_contract(), 'postcondition': 'terminal_summary_written', 'allowed_external_events': ['user_requests_run_stop', 'user_requests_run_cancel']})

def _validate_terminal_summary_payload(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> tuple[str, dict[str, Any]]:
    _bind_router(router)
    if not isinstance(payload, dict):
        raise RouterError('write_terminal_summary requires payload')
    summary_markdown = payload.get('summary_markdown')
    if not isinstance(summary_markdown, str) or not summary_markdown.strip():
        raise RouterError('write_terminal_summary requires non-empty payload.summary_markdown')
    if not summary_markdown.startswith(TERMINAL_SUMMARY_ATTRIBUTION):
        raise RouterError('final summary markdown must start with the FlowPilot GitHub attribution line')
    if payload.get('displayed_to_user') is not True:
        raise RouterError('write_terminal_summary requires displayed_to_user=true after showing the summary to the user')
    summary_hash = _terminal_summary_hash(summary_markdown)
    if payload.get('displayed_summary_sha256') != summary_hash:
        raise RouterError('displayed_summary_sha256 must equal sha256(summary_markdown)')
    if payload.get('read_scope_used') != TERMINAL_SUMMARY_READ_SCOPE:
        raise RouterError(f'write_terminal_summary requires read_scope_used={TERMINAL_SUMMARY_READ_SCOPE}')
    source_paths: list[str] = []
    raw_source_paths = payload.get('source_paths_reviewed')
    if raw_source_paths is not None:
        if not isinstance(raw_source_paths, list):
            raise RouterError('source_paths_reviewed must be a list when supplied')
        for raw in raw_source_paths:
            if not isinstance(raw, str) or not raw.strip():
                raise RouterError('source_paths_reviewed entries must be non-empty strings')
            source_path = resolve_project_path(project_root, raw.strip())
            if not _path_is_inside(source_path, run_root):
                raise RouterError('source_paths_reviewed may cite only files inside the current run root')
            source_paths.append(project_relative(project_root, source_path))
    written_at = utc_now()
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    final_user_report = flowpilot_runtime_closure.final_user_report_record(run_id=str(run_state.get('run_id') or ''), lifecycle_status=mode, summary_path=project_relative(project_root, markdown_path), summary_json_path=project_relative(project_root, json_path), summary_sha256=summary_hash, displayed_to_user=True, written_at=written_at)
    final_report_issues = flowpilot_runtime_closure.validate_final_user_report_record(final_user_report)
    if final_report_issues:
        raise RouterError(f'final user report invariant failed: {final_report_issues}')
    record = {'schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'run_id': run_state.get('run_id'), 'run_lifecycle_status': mode, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'attribution_line': TERMINAL_SUMMARY_ATTRIBUTION, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'controller_read_scope_authorized': True, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'controller_may_approve_or_reopen_gates': False, 'summary_markdown_path': project_relative(project_root, markdown_path), 'summary_json_path': project_relative(project_root, json_path), 'summary_sha256': summary_hash, 'displayed_to_user': True, 'displayed_summary_sha256': summary_hash, 'source_paths_reviewed': source_paths, 'final_user_report': final_user_report, 'written_at': written_at}
    return (summary_markdown, record)

def _write_terminal_summary(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> dict[str, Any]:
    _bind_router(router)
    summary_markdown, record = router._validate_terminal_summary_payload(project_root, run_root, run_state, payload, mode=mode)
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(summary_markdown, encoding='utf-8')
    write_json(json_path, record)
    now = str(record['written_at'])
    markdown_rel = project_relative(project_root, markdown_path)
    json_rel = project_relative(project_root, json_path)
    index_path = project_root / '.flowpilot' / 'index.json'
    index = read_json_if_exists(index_path) or {'schema_version': 'flowpilot.index.v1', 'runs': []}
    runs = index.setdefault('runs', [])
    run_id = run_state.get('run_id')
    entry = None
    for item in runs:
        if isinstance(item, dict) and item.get('run_id') == run_id:
            entry = item
            break
    if entry is None:
        entry = {'run_id': run_id, 'run_root': project_relative(project_root, run_root), 'created_at': run_state.get('created_at') or now}
        runs.append(entry)
    entry['status'] = mode
    entry['updated_at'] = now
    entry['final_summary_path'] = markdown_rel
    entry['final_summary_json_path'] = json_rel
    entry['final_summary_sha256'] = record['summary_sha256']
    entry['final_user_report_schema_version'] = FINAL_USER_REPORT_SCHEMA
    entry['final_user_report_is_completion_authority'] = False
    entry['flowpilot_project_url'] = FLOWPILOT_PROJECT_URL
    index['current_run_id'] = run_id
    index['updated_at'] = now
    write_json(index_path, index)
    current_path = project_root / '.flowpilot' / 'current.json'
    current = read_json_if_exists(current_path) or {}
    if current.get('current_run_id') == run_id:
        current['status'] = mode
        current['final_summary_path'] = markdown_rel
        current['final_summary_json_path'] = json_rel
        current['final_user_report_schema_version'] = FINAL_USER_REPORT_SCHEMA
        current['final_user_report_is_completion_authority'] = False
        current['flowpilot_project_url'] = FLOWPILOT_PROJECT_URL
        current['updated_at'] = now
        write_json(current_path, current)
    flags = run_state.setdefault('flags', {})
    flags['terminal_summary_card_delivered'] = True
    flags['terminal_summary_written'] = True
    run_state['terminal_summary'] = {'schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'path': markdown_rel, 'json_path': json_rel, 'sha256': record['summary_sha256'], 'displayed_to_user': True, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'written_at': now}
    run_state['final_user_report'] = record['final_user_report']
    return record

__all__ = (
    '_terminal_summary_index_entry',
    '_terminal_summary_written',
    '_terminal_summary_action',
    '_validate_terminal_summary_payload',
    '_write_terminal_summary',
)

_LOCAL_NAMES = set(globals())
