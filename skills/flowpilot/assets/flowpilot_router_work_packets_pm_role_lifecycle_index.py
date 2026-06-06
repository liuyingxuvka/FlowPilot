"""PM role-work request index helpers."""

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
import flowpilot_closure_kernel
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


def _pm_role_work_request_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'pm_work_requests' / 'index.json'


def _empty_pm_role_work_request_index(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': PM_ROLE_WORK_REQUEST_INDEX_SCHEMA, 'run_id': run_state['run_id'], 'controller_visibility': 'packet_and_result_envelopes_only', 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'active_request_id': None, 'active_batch_id': None, 'active_request_ids': [], 'requests': [], 'written_at': utc_now(), 'updated_at': utc_now()}


def _load_pm_role_work_request_index(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = router._pm_role_work_request_index_path(run_root)
    if not path.exists():
        return router._empty_pm_role_work_request_index(run_state)
    index = read_json(path)
    if index.get('schema_version') != PM_ROLE_WORK_REQUEST_INDEX_SCHEMA:
        raise RouterError('PM role-work request index has unsupported schema')
    if not isinstance(index.get('requests'), list):
        raise RouterError('PM role-work request index requires requests list')
    index.setdefault('active_request_id', None)
    index.setdefault('active_batch_id', None)
    index.setdefault('active_request_ids', [])
    return index


def _write_pm_role_work_request_index(router: ModuleType, run_root: Path, index: dict[str, Any]) -> None:
    _bind_router(router)
    index['updated_at'] = utc_now()
    write_json(router._pm_role_work_request_index_path(run_root), index)


def _pm_role_work_request_record(router: ModuleType, index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    _bind_router(router)
    for record in index.get('requests', []):
        if isinstance(record, dict) and record.get('request_id') == request_id:
            return record
    return None


def _active_pm_role_work_request(router: ModuleType, index: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    active_id = str(index.get('active_request_id') or '').strip()
    if active_id:
        active = router._pm_role_work_request_record(index, active_id)
        if isinstance(active, dict) and flowpilot_closure_kernel.closure_blocks_progress('pm_role_work_any', active):
            return active
    for record in reversed(index.get('requests', [])):
        if isinstance(record, dict) and flowpilot_closure_kernel.closure_blocks_progress('pm_role_work_any', record):
            return record
    return None


def _active_pm_role_work_batch_records(router: ModuleType, index: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    active_ids = index.get('active_request_ids')
    if not isinstance(active_ids, list) or not active_ids:
        return []
    wanted = {str(item) for item in active_ids}
    records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_id')) in wanted and flowpilot_closure_kernel.closure_blocks_progress('pm_role_work_any', record)]
    return records


def _unresolved_pm_role_work_requests(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    index = router._load_pm_role_work_request_index(run_root, run_state)
    return [record for record in index.get('requests', []) if isinstance(record, dict) and flowpilot_closure_kernel.closure_blocks_progress('pm_role_work_any', record)]


def _pm_role_work_record_is_nonblocking(router: ModuleType, record: dict[str, Any]) -> bool:
    _bind_router(router)
    return str(record.get('request_mode') or 'blocking') in {'advisory', 'prep-only'}


def _pm_role_work_records_are_nonblocking(router: ModuleType, records: list[dict[str, Any]]) -> bool:
    _bind_router(router)
    return bool(records) and all((router._pm_role_work_record_is_nonblocking(record) for record in records))


def _pm_role_work_records_dependency_class(router: ModuleType, records: list[dict[str, Any]]) -> str:
    _bind_router(router)
    modes = sorted({str(record.get('request_mode') or 'blocking') for record in records})
    if len(modes) == 1:
        return modes[0]
    if modes and all((mode in {'advisory', 'prep-only'} for mode in modes)):
        return 'advisory_or_prep_only'
    return 'blocking'


def _unresolved_advisory_pm_role_work_records(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    index = router._load_pm_role_work_request_index(run_root, run_state)
    return [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_mode') or '') == 'advisory' and flowpilot_closure_kernel.closure_blocks_progress('pm_role_work_any', record)]


__all__ = (
    '_pm_role_work_request_index_path',
    '_empty_pm_role_work_request_index',
    '_load_pm_role_work_request_index',
    '_write_pm_role_work_request_index',
    '_pm_role_work_request_record',
    '_active_pm_role_work_request',
    '_active_pm_role_work_batch_records',
    '_unresolved_pm_role_work_requests',
    '_pm_role_work_record_is_nonblocking',
    '_pm_role_work_records_are_nonblocking',
    '_pm_role_work_records_dependency_class',
    '_unresolved_advisory_pm_role_work_records',
)

_LOCAL_NAMES = set(globals())
