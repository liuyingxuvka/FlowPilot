"""FlowGuard operator request lifecycle helpers for PM role work."""

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


def _flowguard_operator_request_lifecycle_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'pm_work_requests' / 'flowguard_operator_request_lifecycle_index.json'


def _empty_flowguard_operator_request_lifecycle_index(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': FLOWGUARD_OPERATOR_REQUEST_LIFECYCLE_INDEX_SCHEMA, 'run_id': run_state['run_id'], 'authority': 'pm_role_work_request_index_and_router_authorized_result_events', 'controller_visibility': 'packet_and_result_envelopes_only', 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'active_request_ids': [], 'requests': [], 'written_at': utc_now(), 'updated_at': utc_now()}


def _load_flowguard_operator_request_lifecycle_index(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = router._flowguard_operator_request_lifecycle_index_path(run_root)
    if not path.exists():
        return router._empty_flowguard_operator_request_lifecycle_index(run_state)
    index = read_json(path)
    if index.get('schema_version') != FLOWGUARD_OPERATOR_REQUEST_LIFECYCLE_INDEX_SCHEMA:
        raise RouterError('FlowGuard operator request lifecycle index has unsupported schema')
    if not isinstance(index.get('requests'), list):
        raise RouterError('FlowGuard operator request lifecycle index requires requests list')
    index.setdefault('active_request_ids', [])
    return index


def _flowguard_operator_lifecycle_entry(router: ModuleType, index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    _bind_router(router)
    for record in index.get('requests', []):
        if isinstance(record, dict) and record.get('request_id') == request_id:
            return record
    return None


def _upsert_flowguard_operator_lifecycle_entry(router: ModuleType, index: dict[str, Any], entry: dict[str, Any]) -> None:
    _bind_router(router)
    request_id = str(entry.get('request_id') or '').strip()
    existing = router._flowguard_operator_lifecycle_entry(index, request_id)
    if isinstance(existing, dict):
        existing.update({key: value for key, value in entry.items() if value is not None})
    else:
        index.setdefault('requests', []).append(entry)


def _write_flowguard_operator_request_lifecycle_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], index: dict[str, Any]) -> None:
    _bind_router(router)
    active_request_ids = [str(record.get('request_id')) for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_status') or '') in PM_ROLE_WORK_OPEN_STATUSES]
    index['active_request_ids'] = active_request_ids
    index['updated_at'] = utc_now()
    path = router._flowguard_operator_request_lifecycle_index_path(run_root)
    write_json(path, index)
    run_state['flowguard_operator_request_lifecycle'] = {'schema_version': FLOWGUARD_OPERATOR_REQUEST_LIFECYCLE_INDEX_SCHEMA, 'index_path': project_relative(project_root, path), 'active_request_ids': active_request_ids, 'request_count': len(index.get('requests', [])), 'updated_at': index['updated_at']}


def _record_flowguard_operator_lifecycle_request(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_flowguard_operator_request_record(record):
        return
    issues = flowpilot_runtime_closure.validate_flowguard_operator_request_record(record)
    if issues:
        raise RouterError(f'FlowGuard operator request lifecycle invariant failed: {issues}')
    index = router._load_flowguard_operator_request_lifecycle_index(run_root, run_state)
    entry = flowpilot_runtime_closure.flowguard_operator_lifecycle_entry_from_request(record, now=utc_now())
    router._upsert_flowguard_operator_lifecycle_entry(index, entry)
    router._write_flowguard_operator_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_flowguard_operator_lifecycle_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], *, lifecycle_status: str) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_flowguard_operator_request_record(record):
        return
    index = router._load_flowguard_operator_request_lifecycle_index(run_root, run_state)
    if router._flowguard_operator_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_flowguard_operator_lifecycle_entry(index, flowpilot_runtime_closure.flowguard_operator_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.flowguard_operator_lifecycle_status_update(record, lifecycle_status=lifecycle_status, now=utc_now())
    router._upsert_flowguard_operator_lifecycle_entry(index, update)
    router._write_flowguard_operator_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_flowguard_operator_lifecycle_result_returned(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], result: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_flowguard_operator_request_record(record):
        return
    issues = flowpilot_runtime_closure.validate_flowguard_operator_result_record(record, result)
    if issues:
        raise RouterError(f'FlowGuard operator result lifecycle invariant failed: {issues}')
    index = router._load_flowguard_operator_request_lifecycle_index(run_root, run_state)
    if router._flowguard_operator_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_flowguard_operator_lifecycle_entry(index, flowpilot_runtime_closure.flowguard_operator_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.flowguard_operator_lifecycle_result_update(record, result, now=utc_now())
    router._upsert_flowguard_operator_lifecycle_entry(index, update)
    router._write_flowguard_operator_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_flowguard_operator_lifecycle_pm_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], decision_record: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_flowguard_operator_request_record(record):
        return
    index = router._load_flowguard_operator_request_lifecycle_index(run_root, run_state)
    if router._flowguard_operator_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_flowguard_operator_lifecycle_entry(index, flowpilot_runtime_closure.flowguard_operator_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.flowguard_operator_lifecycle_decision_update(record, decision_record, now=utc_now())
    router._upsert_flowguard_operator_lifecycle_entry(index, update)
    router._write_flowguard_operator_request_lifecycle_index(project_root, run_root, run_state, index)


__all__ = (
    '_flowguard_operator_request_lifecycle_index_path',
    '_empty_flowguard_operator_request_lifecycle_index',
    '_load_flowguard_operator_request_lifecycle_index',
    '_flowguard_operator_lifecycle_entry',
    '_upsert_flowguard_operator_lifecycle_entry',
    '_write_flowguard_operator_request_lifecycle_index',
    '_record_flowguard_operator_lifecycle_request',
    '_record_flowguard_operator_lifecycle_status',
    '_record_flowguard_operator_lifecycle_result_returned',
    '_record_flowguard_operator_lifecycle_pm_decision',
)

_LOCAL_NAMES = set(globals())
