"""PM role-work request writer."""

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


def _pm_role_work_superseded_request_ids(payload: dict[str, Any]) -> list[str]:
    raw_values = []
    for key in ("supersedes_request_id", "replacement_for_request_id"):
        value = payload.get(key)
        if value not in (None, "", []):
            raw_values.append(value)
    for key in ("supersedes_request_ids", "supersedes_requests"):
        value = payload.get(key)
        if isinstance(value, list):
            raw_values.extend(value)
    request_ids: list[str] = []
    for value in raw_values:
        if isinstance(value, list):
            candidates = value
        else:
            candidates = [value]
        for candidate in candidates:
            request_id = str(candidate or "").strip()
            if request_id and request_id not in request_ids:
                request_ids.append(request_id)
    return request_ids


def _mark_pm_role_work_superseded_requests(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    index: dict[str, Any],
    *,
    superseded_request_ids: list[str],
    replacement_request_id: str,
    replacement_packet_id: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    _bind_router(router)
    if not superseded_request_ids:
        return ([], [])
    if replacement_request_id in superseded_request_ids:
        raise RouterError("PM role-work request cannot supersede itself")
    changed_records: list[dict[str, Any]] = []
    superseded_packet_ids: list[str] = []
    now = utc_now()
    for old_request_id in superseded_request_ids:
        old_record = router._pm_role_work_request_record(index, old_request_id)
        if not isinstance(old_record, dict):
            raise RouterError(f"PM role-work supersedes unknown request_id: {old_request_id}")
        status = str(old_record.get("status") or "").strip()
        already_superseded_by_replacement = (
            status == "superseded"
            and str(old_record.get("superseded_by_request_id") or "") == replacement_request_id
        )
        if status not in PM_ROLE_WORK_OPEN_STATUSES and not already_superseded_by_replacement:
            raise RouterError(f"PM role-work supersedes only unresolved requests: {old_request_id}")
        old_packet_id = str(old_record.get("packet_id") or "").strip()
        if old_packet_id and old_packet_id not in superseded_packet_ids:
            superseded_packet_ids.append(old_packet_id)
        old_record["status"] = "superseded"
        old_record["superseded_by_request_id"] = replacement_request_id
        old_record["replacement_request_id"] = replacement_request_id
        old_record["replacement_packet_id"] = replacement_packet_id
        old_record["superseded_at"] = old_record.get("superseded_at") or now
        old_record["active"] = False
        changed_records.append(old_record)
    active_ids = [str(item) for item in index.get("active_request_ids", []) if str(item) not in set(superseded_request_ids)]
    index["active_request_ids"] = active_ids
    if str(index.get("active_request_id") or "") in set(superseded_request_ids):
        index["active_request_id"] = active_ids[0] if active_ids else None
    if index.get("active_batch_id") and not active_ids:
        index["active_batch_id"] = None
    for old_record in changed_records:
        router._record_flowguard_operator_lifecycle_status(
            project_root,
            run_root,
            run_state,
            old_record,
            lifecycle_status="superseded",
        )
    return (changed_records, superseded_packet_ids)


def _write_pm_role_work_request(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    if not isinstance(payload, dict):
        raise RouterError('PM role-work request payload must be an object')
    raw_batch = payload.get('requests') if isinstance(payload.get('requests'), list) else payload.get('packets')
    if isinstance(raw_batch, list):
        if not raw_batch:
            raise RouterError('PM role-work request batch requires at least one request')
        batch_id = str(payload.get('batch_id') or 'pm-role-work-batch-001')
        request_ids: list[str] = []
        to_roles: list[str] = []
        for index, spec in enumerate(raw_batch, start=1):
            if not isinstance(spec, dict):
                raise RouterError('PM role-work request batch entries must be objects')
            request_id = str(spec.get('request_id') or f'{batch_id}-request-{index:03d}')
            to_role = str(spec.get('to_role') or spec.get('recipient_role') or '')
            if to_role in to_roles:
                raise RouterError('PM role-work request batch cannot assign two open packets to the same role')
            to_roles.append(to_role)
            request_ids.append(request_id)
            single_payload = {**payload, **spec, 'request_id': request_id, 'batch_id': batch_id}
            single_payload.pop('requests', None)
            single_payload.pop('packets', None)
            router._write_pm_role_work_request(project_root, run_root, run_state, single_payload)
        index_doc = router._load_pm_role_work_request_index(run_root, run_state)
        records = [record for request_id in request_ids if isinstance((record := router._pm_role_work_request_record(index_doc, request_id)), dict)]
        router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='pm_role_work', phase='pm_role_work_request', records=records, node_id=str(payload.get('node_id') or 'pm-role-work'), join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_without_reviewer_unless_packet_requires_review', pm_absorption_required=True)
        index_doc['active_batch_id'] = batch_id
        index_doc['active_request_ids'] = request_ids
        index_doc['active_request_id'] = request_ids[0] if request_ids else None
        router._write_pm_role_work_request_index(run_root, index_doc)
        run_state['pm_role_work_requests'] = {'index_path': project_relative(project_root, router._pm_role_work_request_index_path(run_root)), 'active_batch_id': batch_id, 'active_request_ids': request_ids, 'active_request_mode': payload.get('request_mode') or payload.get('mode') or 'blocking'}
        return
    if not _pm_role_work_channel_open(run_state):
        raise RouterError('PM role-work request requires an open PM decision context')
    requested_by_role = str(payload.get('requested_by_role') or payload.get('from_role') or '').strip()
    if requested_by_role != 'project_manager':
        raise RouterError('PM role-work request requires requested_by_role=project_manager')
    request_id = str(payload.get('request_id') or '').strip()
    if not request_id:
        raise RouterError('PM role-work request requires request_id')
    to_role = str(payload.get('to_role') or payload.get('recipient_role') or '').strip()
    if to_role not in PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES:
        raise RouterError('PM role-work request must target a FlowPilot role other than PM or Controller')
    request_mode = str(payload.get('request_mode') or payload.get('mode') or '').strip()
    if request_mode not in PM_ROLE_WORK_REQUEST_MODES:
        raise RouterError('PM role-work request requires request_mode=blocking, advisory, or prep-only')
    request_kind = str(payload.get('request_kind') or payload.get('kind') or '').strip()
    if request_kind not in PM_ROLE_WORK_REQUEST_KINDS:
        raise RouterError('PM role-work request has unsupported request_kind')
    output_contract = payload.get('output_contract') if isinstance(payload.get('output_contract'), dict) else {}
    output_contract_id = str(payload.get('output_contract_id') or output_contract.get('contract_id') or '').strip()
    if not output_contract_id:
        raise RouterError('PM role-work request requires output_contract_id')
    index = router._load_pm_role_work_request_index(run_root, run_state)
    existing = router._pm_role_work_request_record(index, request_id)
    if isinstance(existing, dict) and existing.get('status') in PM_ROLE_WORK_OPEN_STATUSES:
        raise RouterError(f'PM role-work request_id is already open: {request_id}')
    body_text, body_ref = router._pm_role_work_request_body_text(project_root, payload)
    _validate_pm_role_work_request_against_followup(run_state, request_id=request_id, to_role=to_role, request_kind=request_kind, output_contract_id=output_contract_id)
    process_binding = router._validate_pm_role_work_process_contract_binding(contract_id=output_contract_id, to_role=to_role, request_kind=request_kind)
    node_id = str(payload.get('node_id') or 'pm-role-work').strip() or 'pm-role-work'
    packet_id = str(payload.get('packet_id') or f'pm-role-work-{router._safe_packet_id_component(request_id)}')
    packet_type = str(process_binding['packet_type'])
    validated_packet_type = router._pm_role_work_packet_type_from_contract(run_root, contract_id=output_contract_id, to_role=to_role, request_kind=request_kind)
    if validated_packet_type != packet_type:
        raise RouterError('PM role-work packet type does not match process contract binding')
    superseded_request_ids = _pm_role_work_superseded_request_ids(payload)
    superseded_records, superseded_packet_ids = _mark_pm_role_work_superseded_requests(
        router,
        project_root,
        run_root,
        run_state,
        index,
        superseded_request_ids=superseded_request_ids,
        replacement_request_id=request_id,
        replacement_packet_id=packet_id,
    )
    selected_contract = dict(output_contract) if output_contract else router._pm_role_work_output_contract(run_root, contract_id=output_contract_id, to_role=to_role, packet_type=packet_type, node_id=node_id)
    if output_contract:
        if str(selected_contract.get('contract_id') or output_contract_id) != output_contract_id:
            raise RouterError('PM role-work output_contract.contract_id must match output_contract_id')
        supplied_task_family = str(selected_contract.get('task_family') or process_binding['task_family'])
        if supplied_task_family != process_binding['task_family']:
            raise RouterError('PM role-work output_contract.task_family must match process contract binding')
        selected_contract['contract_id'] = output_contract_id
        selected_contract.setdefault('selected_by_role', 'project_manager')
        selected_contract.setdefault('recipient_role', to_role)
        selected_contract.setdefault('node_id', node_id)
        selected_contract.setdefault('packet_type', packet_type)
    selected_contract['process_kind'] = process_binding['process_kind']
    selected_contract['task_family'] = process_binding['task_family']
    selected_contract['required_result_next_recipient'] = process_binding['required_result_next_recipient']
    selected_contract['absorbing_role'] = process_binding['absorbing_role']
    target_gate_contract = router._pm_role_work_target_gate_contract(payload)
    if target_gate_contract is not None:
        selected_contract['target_gate_contract'] = target_gate_contract
    envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=node_id, body_text=body_text, is_current_node=False, packet_type=packet_type, replacement_for=superseded_packet_ids[0] if superseded_packet_ids else None, supersedes=superseded_packet_ids or None, metadata={'source': PM_ROLE_WORK_REQUEST_EVENT, 'request_id': request_id, 'request_kind': request_kind, 'request_mode': request_mode, 'pm_role_work_request': True, 'strict_process_contract_binding': True, 'process_contract_binding': process_binding, 'supersedes_request_ids': superseded_request_ids, 'supersedes_packet_ids': superseded_packet_ids, **({'target_gate_contract': target_gate_contract} if target_gate_contract is not None else {})}, output_contract=selected_contract)
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
    record = {'schema_version': PM_ROLE_WORK_REQUEST_SCHEMA, 'request_id': request_id, 'batch_id': payload.get('batch_id'), 'requested_by_role': 'project_manager', 'to_role': to_role, 'request_mode': request_mode, 'dependency_class': request_mode, 'request_kind': request_kind, 'status': 'open', 'packet_id': packet_id, 'packet_type': packet_type, 'packet_envelope_path': envelope['body_path'].replace('packet_body.md', 'packet_envelope.json'), 'packet_body_path': envelope['body_path'], 'packet_body_hash': envelope['body_hash'], 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'output_contract_id': envelope.get('output_contract_id') or output_contract_id, 'process_kind': process_binding['process_kind'], 'process_contract_binding': process_binding, 'strict_process_contract_binding': True, 'required_result_next_recipient': process_binding['required_result_next_recipient'], 'target_gate_contract': target_gate_contract, 'controller_may_read_packet_body': False, 'body_source': body_ref, 'registered_at': utc_now(), 'supersedes_request_ids': superseded_request_ids, 'supersedes_packet_ids': superseded_packet_ids, 'replacement_for_request_id': superseded_request_ids[0] if superseded_request_ids else None, 'replacement_for_packet_id': superseded_packet_ids[0] if superseded_packet_ids else None, 'supersedes': superseded_packet_ids, 'replacement_for': superseded_packet_ids[0] if superseded_packet_ids else None}
    if isinstance(existing, dict):
        existing.update(record)
    else:
        index.setdefault('requests', []).append(record)
    for old_record in superseded_records:
        old_record["superseded_by_packet_id"] = packet_id
    index['active_request_id'] = request_id
    if not payload.get('batch_id'):
        batch_id = f'pm-role-work-batch-{router._safe_packet_id_component(request_id)}'
        record['batch_id'] = batch_id
        router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='pm_role_work', phase='pm_role_work_request', records=[record], node_id=node_id, join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_without_reviewer_unless_packet_requires_review', pm_absorption_required=True)
        index['active_batch_id'] = batch_id
        index['active_request_ids'] = [request_id]
    router._write_pm_role_work_request_index(run_root, index)
    router._record_flowguard_operator_lifecycle_request(project_root, run_root, run_state, record)
    run_state['pm_role_work_requests'] = {'index_path': project_relative(project_root, router._pm_role_work_request_index_path(run_root)), 'active_request_id': request_id, 'active_packet_id': packet_id, 'active_to_role': to_role, 'active_request_mode': request_mode}


__all__ = (
    '_write_pm_role_work_request',
)

_LOCAL_NAMES = set(globals())
