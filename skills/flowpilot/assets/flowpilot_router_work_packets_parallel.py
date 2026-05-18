"""Coarse work packets owner helpers for the FlowPilot router.

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

def _parallel_packet_batch_root(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'packet_batches'

def _parallel_packet_batch_path(router: ModuleType, run_root: Path, batch_id: str) -> Path:
    _bind_router(router)
    return router._parallel_packet_batch_root(run_root) / f'{router._safe_packet_id_component(batch_id)}.json'

def _parallel_packet_batch_ref_path(router: ModuleType, run_root: Path, batch_kind: str) -> Path:
    _bind_router(router)
    return router._parallel_packet_batch_root(run_root) / f'active_{router._safe_packet_id_component(batch_kind)}.json'

def _packet_record_from_envelope(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, envelope: dict[str, Any], packet_type: str | None=None, request_id: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    packet_id = str(envelope.get('packet_id') or '').strip()
    if not packet_id:
        raise RouterError('packet envelope requires packet_id')
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
    record = {'packet_id': packet_id, 'to_role': str(envelope.get('to_role') or ''), 'packet_type': packet_type or str(envelope.get('packet_type') or ''), 'packet_envelope_path': str(envelope.get('body_path') or '').replace('packet_body.md', 'packet_envelope.json'), 'packet_body_path': envelope.get('body_path'), 'packet_body_hash': envelope.get('body_hash'), 'body_path': envelope.get('body_path'), 'body_hash': envelope.get('body_hash'), 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'result_write_target': {'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body'])}, 'output_contract_id': envelope.get('output_contract_id'), 'status': 'registered'}
    if request_id:
        record['request_id'] = request_id
    return record

def _write_parallel_packet_batch(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, batch_id: str, batch_kind: str, phase: str, records: list[dict[str, Any]], node_id: str | None=None, join_policy: str='all_results_before_review', review_policy: str='batch_review_before_pm', pm_absorption_required: bool=True, parent_batch_id: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if not batch_id:
        raise RouterError('parallel packet batch requires batch_id')
    if not records:
        raise RouterError('parallel packet batch requires at least one packet')
    packet_ids = [str(record.get('packet_id') or '').strip() for record in records]
    if any((not packet_id for packet_id in packet_ids)):
        raise RouterError('parallel packet batch packets require packet_id')
    if len(set(packet_ids)) != len(packet_ids):
        raise RouterError('parallel packet batch packet_id values must be unique')
    to_roles = [str(record.get('to_role') or '').strip() for record in records]
    if any((not role for role in to_roles)):
        raise RouterError('parallel packet batch packets require to_role')
    if len(set(to_roles)) != len(to_roles):
        raise RouterError('parallel packet batch cannot assign two open packets to the same role')
    batch_path = router._parallel_packet_batch_path(run_root, batch_id)
    existing = read_json_if_exists(batch_path)
    if existing and existing.get('status') in PARALLEL_PACKET_BATCH_OPEN_STATUSES:
        raise RouterError(f'parallel packet batch is already open: {batch_id}')
    normalized_records: list[dict[str, Any]] = []
    for record in records:
        item = dict(record)
        item['batch_id'] = batch_id
        item['batch_kind'] = batch_kind
        item.setdefault('status', 'registered')
        item.setdefault('dependency_class', 'blocking')
        record.update(item)
        normalized_records.append(item)
    batch = {'schema_version': PARALLEL_PACKET_BATCH_SCHEMA, 'run_id': run_state['run_id'], 'batch_id': batch_id, 'batch_kind': batch_kind, 'phase': phase, 'node_id': node_id, 'owner_role': 'project_manager', 'join_policy': join_policy, 'review_policy': review_policy, 'pm_absorption_required': pm_absorption_required, 'parent_batch_id': parent_batch_id, 'status': 'registered', 'controller_visibility': 'packet_and_result_envelopes_only', 'controller_may_read_packet_body': False, 'controller_may_read_result_body': False, 'packets': normalized_records, 'counts': {'registered': len(normalized_records), 'relayed': 0, 'results_returned': 0, 'reviewed': 0}, 'written_at': utc_now(), 'updated_at': utc_now()}
    write_json(batch_path, batch)
    write_json(router._parallel_packet_batch_ref_path(run_root, batch_kind), {'schema_version': PARALLEL_PACKET_BATCH_REF_SCHEMA, 'run_id': run_state['run_id'], 'batch_kind': batch_kind, 'active_batch_id': batch_id, 'batch_path': project_relative(project_root, batch_path), 'updated_at': utc_now()})
    return batch

def _load_parallel_packet_batch(router: ModuleType, run_root: Path, batch_id: str) -> dict[str, Any]:
    _bind_router(router)
    path = router._parallel_packet_batch_path(run_root, batch_id)
    if not path.exists():
        raise RouterError(f'parallel packet batch is missing: {path}')
    batch = read_json(path)
    if batch.get('schema_version') != PARALLEL_PACKET_BATCH_SCHEMA:
        raise RouterError('parallel packet batch has unsupported schema')
    if not isinstance(batch.get('packets'), list) or not batch['packets']:
        raise RouterError('parallel packet batch requires non-empty packets')
    return batch

def _active_parallel_packet_batch(router: ModuleType, run_root: Path, batch_kind: str) -> dict[str, Any] | None:
    _bind_router(router)
    ref_path = router._parallel_packet_batch_ref_path(run_root, batch_kind)
    ref = read_json_if_exists(ref_path)
    if not ref:
        return None
    batch_id = str(ref.get('active_batch_id') or '').strip()
    if not batch_id:
        return None
    return router._load_parallel_packet_batch(run_root, batch_id)

def _write_parallel_packet_batch_state(router: ModuleType, run_root: Path, batch: dict[str, Any]) -> None:
    _bind_router(router)
    batch['updated_at'] = utc_now()
    write_json(router._parallel_packet_batch_path(run_root, str(batch['batch_id'])), batch)

def _parallel_batch_record_result_exists(router: ModuleType, project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> tuple[bool, Path]:
    _bind_router(router)
    result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
    return (result_path.exists(), result_path)

def _parallel_packet_batch_member_summary(router: ModuleType, project_root: Path, run_state: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    returned_roles: list[str] = []
    missing_roles: list[str] = []
    returned_packet_ids: list[str] = []
    missing_packet_ids: list[str] = []
    packet_count = 0
    for record in batch.get('packets') or []:
        if not isinstance(record, dict):
            continue
        packet_count += 1
        packet_id = str(record.get('packet_id') or '')
        role = str(record.get('to_role') or packet_id or 'unknown')
        result_exists, _result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        status = str(record.get('status') or '')
        if result_exists or status in PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES:
            returned_roles.append(role)
            if packet_id:
                returned_packet_ids.append(packet_id)
        else:
            missing_roles.append(role)
            if packet_id:
                missing_packet_ids.append(packet_id)
    returned_roles = sorted(set(returned_roles))
    missing_roles = sorted(set(missing_roles))
    returned_packet_ids = sorted(set(returned_packet_ids))
    missing_packet_ids = sorted(set(missing_packet_ids))
    return {'batch_id': batch.get('batch_id'), 'batch_kind': batch.get('batch_kind'), 'packet_count': packet_count, 'results_returned': len(returned_packet_ids), 'missing_count': len(missing_packet_ids), 'returned_roles': returned_roles, 'missing_roles': missing_roles, 'returned_packet_ids': returned_packet_ids, 'missing_packet_ids': missing_packet_ids, 'all_results_returned': packet_count > 0 and len(returned_packet_ids) == packet_count, 'partial_results_returned': 0 < len(returned_packet_ids) < packet_count, 'controller_visibility': 'metadata_only'}

def _refresh_parallel_packet_batch_from_durable_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], batch_kind: str) -> dict[str, Any]:
    _bind_router(router)
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return {'batch_kind': batch_kind, 'active': False, 'changed': False}
    before = json.dumps(batch, sort_keys=True)
    returned = 0
    relayed = 0
    for record in batch.get('packets') or []:
        if not isinstance(record, dict):
            continue
        if str(record.get('status') or '') in {'packet_relayed', *PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES}:
            relayed += 1
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if not result_exists:
            continue
        returned += 1
        record['result_envelope_path'] = project_relative(project_root, result_path)
        record['result_envelope_hash'] = packet_runtime.sha256_file(result_path)
        if str(record.get('status') or '') not in PARALLEL_PACKET_BATCH_RESULT_RETURNED_STATUSES:
            record['status'] = 'result_returned'
        record.setdefault('result_returned_at', utc_now())
        try:
            result = packet_runtime.load_envelope(project_root, result_path)
        except (OSError, json.JSONDecodeError, packet_runtime.PacketRuntimeError):
            result = {}
        if isinstance(result, dict):
            if result.get('result_body_path'):
                record['result_body_path'] = result.get('result_body_path')
            if result.get('result_body_hash'):
                record['result_body_hash'] = result.get('result_body_hash')
    summary = router._parallel_packet_batch_member_summary(project_root, run_state, batch)
    counts = batch.setdefault('counts', {})
    counts['registered'] = summary['packet_count']
    counts['relayed'] = max(int(counts.get('relayed') or 0), relayed)
    counts['results_returned'] = summary['results_returned']
    previous_member_status = batch.get('member_status') if isinstance(batch.get('member_status'), dict) else {}
    member_status = {'schema_version': 'flowpilot.parallel_packet_batch_member_status.v1', 'controller_visibility': 'metadata_only', 'returned_roles': summary['returned_roles'], 'missing_roles': summary['missing_roles'], 'returned_packet_ids': summary['returned_packet_ids'], 'missing_packet_ids': summary['missing_packet_ids'], 'results_returned': summary['results_returned'], 'packet_count': summary['packet_count'], 'partial_results_returned': summary['partial_results_returned'], 'all_results_returned': summary['all_results_returned']}
    comparable_previous = {key: value for key, value in previous_member_status.items() if key != 'updated_at'}
    member_status['updated_at'] = previous_member_status.get('updated_at') if comparable_previous == member_status and previous_member_status.get('updated_at') else utc_now()
    batch['member_status'] = member_status
    if summary['all_results_returned'] and str(batch.get('status') or '') not in PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES:
        batch['status'] = 'results_joined'
        batch.setdefault('joined_at', utc_now())
    elif summary['partial_results_returned'] and str(batch.get('status') or '') not in PARALLEL_PACKET_BATCH_RESULT_FINAL_STATUSES:
        batch['status'] = 'partial_results_returned'
    changed = before != json.dumps(batch, sort_keys=True)
    if changed:
        router._write_parallel_packet_batch_state(run_root, batch)
    return {**summary, 'active': True, 'changed': changed, 'batch_status': batch.get('status')}

def _refresh_all_parallel_packet_batches_from_durable_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    summaries = {batch_kind: router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind) for batch_kind in ('material_scan', 'research', 'current_node', 'pm_role_work')}
    return {'schema_version': 'flowpilot.parallel_packet_batch_reconciliation.v1', 'changed': any((bool(summary.get('changed')) for summary in summaries.values())), 'batches': summaries, 'reconciled_at': utc_now()}

def _mark_parallel_batch_packets_relayed(router: ModuleType, run_root: Path, batch_kind: str) -> None:
    _bind_router(router)
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return
    for record in batch['packets']:
        if isinstance(record, dict):
            record['status'] = 'packet_relayed'
            record['relayed_at'] = utc_now()
    batch['status'] = 'packets_relayed'
    batch['counts']['relayed'] = len(batch['packets'])
    router._write_parallel_packet_batch_state(run_root, batch)

def _mark_parallel_batch_results_joined(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], batch_kind: str) -> None:
    _bind_router(router)
    router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind)

def _mark_parallel_batch_reviewed(router: ModuleType, run_root: Path, batch_kind: str, *, passed: bool, reviewed_packet_ids: list[str]) -> None:
    _bind_router(router)
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        return
    batch['status'] = 'reviewed' if passed else 'review_blocked'
    batch['review'] = {'passed': passed, 'reviewed_packet_ids': reviewed_packet_ids, 'reviewed_at': utc_now()}
    batch['counts']['reviewed'] = len(reviewed_packet_ids)
    router._write_parallel_packet_batch_state(run_root, batch)

__all__ = (
    '_parallel_packet_batch_root',
    '_parallel_packet_batch_path',
    '_parallel_packet_batch_ref_path',
    '_packet_record_from_envelope',
    '_write_parallel_packet_batch',
    '_load_parallel_packet_batch',
    '_active_parallel_packet_batch',
    '_write_parallel_packet_batch_state',
    '_parallel_batch_record_result_exists',
    '_parallel_packet_batch_member_summary',
    '_refresh_parallel_packet_batch_from_durable_results',
    '_refresh_all_parallel_packet_batches_from_durable_results',
    '_mark_parallel_batch_packets_relayed',
    '_mark_parallel_batch_results_joined',
    '_mark_parallel_batch_reviewed',
)

_LOCAL_NAMES = set(globals())
