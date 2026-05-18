"""PM role-work request index and officer lifecycle helpers."""

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


def _officer_request_lifecycle_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'pm_work_requests' / 'officer_request_lifecycle_index.json'


def _empty_officer_request_lifecycle_index(router: ModuleType, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA, 'run_id': run_state['run_id'], 'authority': 'pm_role_work_request_index_and_router_authorized_result_events', 'controller_visibility': 'packet_and_result_envelopes_only', 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'active_request_ids': [], 'requests': [], 'written_at': utc_now(), 'updated_at': utc_now()}


def _load_officer_request_lifecycle_index(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = router._officer_request_lifecycle_index_path(run_root)
    if not path.exists():
        return router._empty_officer_request_lifecycle_index(run_state)
    index = read_json(path)
    if index.get('schema_version') != OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA:
        raise RouterError('officer request lifecycle index has unsupported schema')
    if not isinstance(index.get('requests'), list):
        raise RouterError('officer request lifecycle index requires requests list')
    index.setdefault('active_request_ids', [])
    return index


def _officer_lifecycle_entry(router: ModuleType, index: dict[str, Any], request_id: str) -> dict[str, Any] | None:
    _bind_router(router)
    for record in index.get('requests', []):
        if isinstance(record, dict) and record.get('request_id') == request_id:
            return record
    return None


def _upsert_officer_lifecycle_entry(router: ModuleType, index: dict[str, Any], entry: dict[str, Any]) -> None:
    _bind_router(router)
    request_id = str(entry.get('request_id') or '').strip()
    existing = router._officer_lifecycle_entry(index, request_id)
    if isinstance(existing, dict):
        existing.update({key: value for key, value in entry.items() if value is not None})
    else:
        index.setdefault('requests', []).append(entry)


def _write_officer_request_lifecycle_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], index: dict[str, Any]) -> None:
    _bind_router(router)
    active_request_ids = [str(record.get('request_id')) for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_status') or '') in PM_ROLE_WORK_OPEN_STATUSES]
    index['active_request_ids'] = active_request_ids
    index['updated_at'] = utc_now()
    path = router._officer_request_lifecycle_index_path(run_root)
    write_json(path, index)
    run_state['officer_request_lifecycle'] = {'schema_version': OFFICER_REQUEST_LIFECYCLE_INDEX_SCHEMA, 'index_path': project_relative(project_root, path), 'active_request_ids': active_request_ids, 'request_count': len(index.get('requests', [])), 'updated_at': index['updated_at']}


def _record_officer_lifecycle_request(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_officer_request_record(record):
        return
    issues = flowpilot_runtime_closure.validate_officer_request_record(record)
    if issues:
        raise RouterError(f'officer request lifecycle invariant failed: {issues}')
    index = router._load_officer_request_lifecycle_index(run_root, run_state)
    entry = flowpilot_runtime_closure.officer_lifecycle_entry_from_request(record, now=utc_now())
    router._upsert_officer_lifecycle_entry(index, entry)
    router._write_officer_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_officer_lifecycle_status(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], *, lifecycle_status: str) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_officer_request_record(record):
        return
    index = router._load_officer_request_lifecycle_index(run_root, run_state)
    if router._officer_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_officer_lifecycle_entry(index, flowpilot_runtime_closure.officer_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.officer_lifecycle_status_update(record, lifecycle_status=lifecycle_status, now=utc_now())
    router._upsert_officer_lifecycle_entry(index, update)
    router._write_officer_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_officer_lifecycle_result_returned(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], result: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_officer_request_record(record):
        return
    issues = flowpilot_runtime_closure.validate_officer_result_record(record, result)
    if issues:
        raise RouterError(f'officer result lifecycle invariant failed: {issues}')
    index = router._load_officer_request_lifecycle_index(run_root, run_state)
    if router._officer_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_officer_lifecycle_entry(index, flowpilot_runtime_closure.officer_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.officer_lifecycle_result_update(record, result, now=utc_now())
    router._upsert_officer_lifecycle_entry(index, update)
    router._write_officer_request_lifecycle_index(project_root, run_root, run_state, index)


def _record_officer_lifecycle_pm_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], decision_record: dict[str, Any]) -> None:
    _bind_router(router)
    if not flowpilot_runtime_closure.is_officer_request_record(record):
        return
    index = router._load_officer_request_lifecycle_index(run_root, run_state)
    if router._officer_lifecycle_entry(index, str(record.get('request_id') or '')) is None:
        router._upsert_officer_lifecycle_entry(index, flowpilot_runtime_closure.officer_lifecycle_entry_from_request(record, now=utc_now()))
    update = flowpilot_runtime_closure.officer_lifecycle_decision_update(record, decision_record, now=utc_now())
    router._upsert_officer_lifecycle_entry(index, update)
    router._write_officer_request_lifecycle_index(project_root, run_root, run_state, index)


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
        if isinstance(active, dict) and active.get('status') in PM_ROLE_WORK_OPEN_STATUSES:
            return active
    for record in reversed(index.get('requests', [])):
        if isinstance(record, dict) and record.get('status') in PM_ROLE_WORK_OPEN_STATUSES:
            return record
    return None


def _active_pm_role_work_batch_records(router: ModuleType, index: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    active_ids = index.get('active_request_ids')
    if not isinstance(active_ids, list) or not active_ids:
        return []
    wanted = {str(item) for item in active_ids}
    records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_id')) in wanted and (record.get('status') in PM_ROLE_WORK_OPEN_STATUSES)]
    return records


def _unresolved_pm_role_work_requests(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    index = router._load_pm_role_work_request_index(run_root, run_state)
    return [record for record in index.get('requests', []) if isinstance(record, dict) and record.get('status') in PM_ROLE_WORK_OPEN_STATUSES]


def _safe_packet_id_component(router: ModuleType, value: str) -> str:
    _bind_router(router)
    safe = ''.join((ch if ch.isalnum() or ch in {'-', '_'} else '-' for ch in value)).strip('-')
    return safe[:80] or 'request'


def _pm_role_work_request_body_text(router: ModuleType, project_root: Path, payload: dict[str, Any]) -> tuple[str, dict[str, str]]:
    _bind_router(router)
    path_pairs = (('packet_body_path', 'packet_body_hash'), ('request_body_path', 'request_body_hash'), ('body_path', 'body_hash'))
    for path_key, hash_key in path_pairs:
        raw_path = payload.get(path_key)
        raw_hash = payload.get(hash_key)
        if not raw_path:
            continue
        if not raw_hash:
            raise RouterError(f'PM role-work request {path_key} requires matching {hash_key}')
        path = resolve_project_path(project_root, str(raw_path))
        if not path.exists():
            raise RouterError(f'PM role-work request body path is missing: {raw_path}')
        actual_hash = packet_runtime.sha256_file(path)
        if actual_hash != str(raw_hash):
            raise RouterError('PM role-work request body hash mismatch')
        body_text = path.read_text(encoding='utf-8')
        if not body_text.strip():
            raise RouterError('PM role-work request body file is empty')
        return (body_text, {path_key: project_relative(project_root, path), hash_key: actual_hash})
    if isinstance(payload.get('body_text'), str) and payload['body_text'].strip():
        raise RouterError('PM role-work request body must be file-backed; use packet_body_path/packet_body_hash so Controller does not receive the role-work body inline')
    raise RouterError('PM role-work request requires file-backed packet_body_path/packet_body_hash')


def _validate_pm_role_work_process_contract_binding(router: ModuleType, *, contract_id: str, to_role: str, request_kind: str) -> dict[str, Any]:
    _bind_router(router)
    foreign_current_node_contract = 'flowpilot.output_contract.worker_current_node_result.v1'
    foreign_current_node_family = 'worker.current_node'
    if contract_id in PM_ROLE_WORK_FOREIGN_CONTRACT_IDS or contract_id == foreign_current_node_contract:
        raise RouterError(f'output_contract_id {contract_id} does not match PM role-work process; {foreign_current_node_family} belongs to current-node execution, not delegated PM side work')
    process_kind = PM_ROLE_WORK_CONTRACT_PROCESS_KINDS.get(contract_id)
    if not process_kind:
        raise RouterError(f'PM role-work request output_contract_id is not allowed for PM role-work process: {contract_id}')
    binding = dict(PROCESS_CONTRACT_BINDINGS[process_kind])
    if process_kind in {'officer_model_report', 'officer_model_miss_report'} and to_role not in {'process_flowguard_officer', 'product_flowguard_officer'}:
        raise RouterError(f'output_contract_id {contract_id} is an officer process contract and must target an officer role')
    if process_kind == 'officer_model_miss_report' and request_kind != 'model_miss':
        raise RouterError('officer model-miss contract requires request_kind=model_miss')
    if process_kind == 'pm_role_work_request' and to_role not in PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES:
        raise RouterError('PM role-work process target role is not allowed')
    return {'process_kind': process_kind, 'task_family': binding['task_family'], 'contract_id': binding['contract_id'], 'packet_type': binding['packet_type'], 'required_result_next_recipient': binding['required_result_next_recipient'], 'absorbing_role': binding['absorbing_role']}


def _pm_role_work_packet_type_from_contract(router: ModuleType, run_root: Path, *, contract_id: str, to_role: str, request_kind: str) -> str:
    _bind_router(router)
    del run_root
    binding = router._validate_pm_role_work_process_contract_binding(contract_id=contract_id, to_role=to_role, request_kind=request_kind)
    return str(binding['packet_type'])


def _pm_role_work_output_contract(router: ModuleType, run_root: Path, *, contract_id: str, to_role: str, packet_type: str, node_id: str) -> dict[str, Any]:
    _bind_router(router)
    registry_path = run_root / 'runtime_kit' / 'contracts' / 'contract_index.json'
    registry = read_json_if_exists(registry_path)
    if not registry:
        registry_path = runtime_kit_source() / 'contracts' / 'contract_index.json'
        registry = read_json(registry_path)
    for contract in registry.get('contracts', []):
        if not isinstance(contract, dict) or contract.get('contract_id') != contract_id:
            continue
        roles = contract.get('recipient_roles')
        if isinstance(roles, list) and to_role not in roles:
            raise RouterError(f'output contract {contract_id} does not allow recipient role {to_role}')
        selected = dict(contract)
        selected['selected_by_role'] = 'project_manager'
        selected['recipient_role'] = to_role
        selected['node_id'] = node_id
        selected['packet_type'] = packet_type
        selected['registry_path'] = 'runtime_kit/contracts/contract_index.json'
        return selected
    raise RouterError(f'PM role-work request output_contract_id is not in the registry: {contract_id}')


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
    return [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_mode') or '') == 'advisory' and (record.get('status') in PM_ROLE_WORK_OPEN_STATUSES)]


__all__ = (
    '_pm_role_work_request_index_path',
    '_empty_pm_role_work_request_index',
    '_load_pm_role_work_request_index',
    '_write_pm_role_work_request_index',
    '_officer_request_lifecycle_index_path',
    '_empty_officer_request_lifecycle_index',
    '_load_officer_request_lifecycle_index',
    '_officer_lifecycle_entry',
    '_upsert_officer_lifecycle_entry',
    '_write_officer_request_lifecycle_index',
    '_record_officer_lifecycle_request',
    '_record_officer_lifecycle_status',
    '_record_officer_lifecycle_result_returned',
    '_record_officer_lifecycle_pm_decision',
    '_pm_role_work_request_record',
    '_active_pm_role_work_request',
    '_active_pm_role_work_batch_records',
    '_unresolved_pm_role_work_requests',
    '_safe_packet_id_component',
    '_pm_role_work_request_body_text',
    '_validate_pm_role_work_process_contract_binding',
    '_pm_role_work_packet_type_from_contract',
    '_pm_role_work_output_contract',
    '_pm_role_work_record_is_nonblocking',
    '_pm_role_work_records_are_nonblocking',
    '_pm_role_work_records_dependency_class',
    '_unresolved_advisory_pm_role_work_records',
)

_LOCAL_NAMES = set(globals())
