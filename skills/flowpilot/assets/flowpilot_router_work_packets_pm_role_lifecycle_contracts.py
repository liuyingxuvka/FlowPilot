"""PM role-work packet body and process-contract helpers."""

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
    if process_kind in {'flowguard_operator_model_report', 'flowguard_operator_model_miss_report'} and to_role not in {'flowguard_operator', 'flowguard_operator'}:
        raise RouterError(f'output_contract_id {contract_id} is a FlowGuard operator process contract and must target a FlowGuard operator role')
    if process_kind == 'flowguard_operator_model_miss_report' and request_kind != 'model_miss':
        raise RouterError('FlowGuard operator model-miss contract requires request_kind=model_miss')
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


__all__ = (
    '_safe_packet_id_component',
    '_pm_role_work_request_body_text',
    '_validate_pm_role_work_process_contract_binding',
    '_pm_role_work_packet_type_from_contract',
    '_pm_role_work_output_contract',
)

_LOCAL_NAMES = set(globals())
