"""PM role-work result return helpers."""

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


def _normalize_pm_role_work_result_recipient(router: ModuleType, project_root: Path, result_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if result.get('next_recipient') == 'project_manager':
        return result
    original_recipient = result.get('next_recipient')
    result['next_recipient'] = 'project_manager'
    result['next_holder'] = 'project_manager'
    result['to_role'] = 'project_manager'
    result['recipient_normalization'] = {'schema_version': 'flowpilot.pm_role_work_result_recipient_normalization.v1', 'from': original_recipient, 'to': 'project_manager', 'reason': 'pm_role_work_result_returns_to_pm', 'controller_read_result_body': False, 'normalized_at': utc_now()}
    write_json(result_path, result)
    paths = packet_runtime.packet_paths_from_result_envelope(project_root, result)
    ledger = read_json(paths['packet_ledger'])
    records = ledger.get('packets') if isinstance(ledger.get('packets'), list) else []
    for item in records:
        if isinstance(item, dict) and item.get('packet_id') == result.get('packet_id'):
            item['result_recipient_normalized_to_pm'] = True
            item['result_recipient_normalized_at'] = result['recipient_normalization']['normalized_at']
            nested = item.get('result_envelope')
            if isinstance(nested, dict):
                nested['next_recipient'] = 'project_manager'
    ledger['updated_at'] = utc_now()
    write_json(paths['packet_ledger'], ledger)
    return result


def _validate_role_work_result_process_binding(router: ModuleType, project_root: Path, result_path: Path, *, record: dict[str, Any], packet_envelope: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    metadata = packet_envelope.get('metadata') if isinstance(packet_envelope.get('metadata'), dict) else {}
    binding = metadata.get('process_contract_binding') if isinstance(metadata.get('process_contract_binding'), dict) else {}
    strict_process_contract_binding = bool(metadata.get('strict_process_contract_binding') or record.get('strict_process_contract_binding'))
    expected_next_recipient = str(binding.get('required_result_next_recipient') or record.get('required_result_next_recipient') or 'project_manager')
    if result.get('next_recipient') == expected_next_recipient:
        return result
    if strict_process_contract_binding:
        raise RouterError('role-work result next_recipient must match process binding')
    result['pm_role_work_result_recipient_normalization'] = True
    return router._normalize_pm_role_work_result_recipient(project_root, result_path, result)


def _write_role_work_result_returned(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    if not isinstance(payload, dict):
        raise RouterError('role-work result payload must be an object')
    request_id = str(payload.get('request_id') or '').strip()
    if not request_id:
        raise RouterError('role-work result requires request_id')
    index = router._load_pm_role_work_request_index(run_root, run_state)
    record = router._pm_role_work_request_record(index, request_id)
    if not isinstance(record, dict):
        raise RouterError(f'role-work result references unknown request_id: {request_id}')
    if record.get('status') != 'packet_relayed':
        raise RouterError('role-work result requires request packet made available to worker')
    packet_id = str(payload.get('packet_id') or record.get('packet_id') or '').strip()
    if packet_id != str(record.get('packet_id') or ''):
        raise RouterError('role-work result packet_id must match request packet')
    result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
    raw_result_path = payload.get('result_envelope_path')
    if raw_result_path:
        supplied = resolve_project_path(project_root, str(raw_result_path))
        if supplied.resolve() != result_path.resolve():
            raise RouterError('role-work result_envelope_path must match request record')
    if not result_path.exists():
        raise RouterError(f'role-work result envelope is missing: {result_path}')
    result_hash = payload.get('result_envelope_hash')
    if result_hash and packet_runtime.sha256_file(result_path) != str(result_hash):
        raise RouterError('role-work result envelope hash mismatch')
    result = packet_runtime.load_envelope(project_root, result_path)
    if result.get('packet_id') != packet_id:
        raise RouterError('role-work result envelope packet_id mismatch')
    if result.get('completed_by_role') != record.get('to_role'):
        raise RouterError('role-work result was completed by the wrong role')
    packet_path = router._packet_envelope_path_from_record(project_root, run_state, record)
    packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
    result = router._validate_role_work_result_process_binding(project_root, result_path, record=record, packet_envelope=packet_envelope, result=result)
    audit = packet_runtime.validate_result_ready_for_recipient_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=router._agent_role_map_from_role_binding_ledger(run_root))
    if not audit.get('passed'):
        raise RouterError(f"role-work result is not ready for PM relay: {audit.get('blockers')}")
    record['status'] = 'result_returned'
    record['result_envelope_path'] = project_relative(project_root, result_path)
    record['result_envelope_hash'] = packet_runtime.sha256_file(result_path)
    record['result_body_path'] = result.get('result_body_path')
    record['result_body_hash'] = result.get('result_body_hash')
    record['result_returned_at'] = utc_now()
    index['active_request_id'] = request_id
    router._record_flowguard_operator_lifecycle_result_returned(project_root, run_root, run_state, record, result)
    router._write_pm_role_work_request_index(run_root, index)
    router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'pm_role_work')


__all__ = (
    '_normalize_pm_role_work_result_recipient',
    '_validate_role_work_result_process_binding',
    '_write_role_work_result_returned',
)

_LOCAL_NAMES = set(globals())
