"""PM role-work request/result writers for the FlowPilot router."""

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
    envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=node_id, body_text=body_text, is_current_node=False, packet_type=packet_type, metadata={'source': PM_ROLE_WORK_REQUEST_EVENT, 'request_id': request_id, 'request_kind': request_kind, 'request_mode': request_mode, 'pm_role_work_request': True, 'strict_process_contract_binding': True, 'process_contract_binding': process_binding, **({'target_gate_contract': target_gate_contract} if target_gate_contract is not None else {})}, output_contract=selected_contract)
    paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
    record = {'schema_version': PM_ROLE_WORK_REQUEST_SCHEMA, 'request_id': request_id, 'batch_id': payload.get('batch_id'), 'requested_by_role': 'project_manager', 'to_role': to_role, 'request_mode': request_mode, 'dependency_class': request_mode, 'request_kind': request_kind, 'status': 'open', 'packet_id': packet_id, 'packet_type': packet_type, 'packet_envelope_path': envelope['body_path'].replace('packet_body.md', 'packet_envelope.json'), 'packet_body_path': envelope['body_path'], 'packet_body_hash': envelope['body_hash'], 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'output_contract_id': envelope.get('output_contract_id') or output_contract_id, 'process_kind': process_binding['process_kind'], 'process_contract_binding': process_binding, 'strict_process_contract_binding': True, 'required_result_next_recipient': process_binding['required_result_next_recipient'], 'target_gate_contract': target_gate_contract, 'controller_may_read_packet_body': False, 'body_source': body_ref, 'registered_at': utc_now()}
    if isinstance(existing, dict):
        existing.update(record)
    else:
        index.setdefault('requests', []).append(record)
    index['active_request_id'] = request_id
    if not payload.get('batch_id'):
        batch_id = f'pm-role-work-batch-{router._safe_packet_id_component(request_id)}'
        record['batch_id'] = batch_id
        router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='pm_role_work', phase='pm_role_work_request', records=[record], node_id=node_id, join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_without_reviewer_unless_packet_requires_review', pm_absorption_required=True)
        index['active_batch_id'] = batch_id
        index['active_request_ids'] = [request_id]
    router._write_pm_role_work_request_index(run_root, index)
    router._record_officer_lifecycle_request(project_root, run_root, run_state, record)
    run_state['pm_role_work_requests'] = {'index_path': project_relative(project_root, router._pm_role_work_request_index_path(run_root)), 'active_request_id': request_id, 'active_packet_id': packet_id, 'active_to_role': to_role, 'active_request_mode': request_mode}


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
    result['legacy_pm_role_work_result_recipient_normalization'] = True
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
    audit = packet_runtime.validate_result_ready_for_reviewer_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=router._agent_role_map_from_crew_ledger(run_root))
    if not audit.get('passed'):
        raise RouterError(f"role-work result is not ready for PM relay: {audit.get('blockers')}")
    record['status'] = 'result_returned'
    record['result_envelope_path'] = project_relative(project_root, result_path)
    record['result_envelope_hash'] = packet_runtime.sha256_file(result_path)
    record['result_body_path'] = result.get('result_body_path')
    record['result_body_hash'] = result.get('result_body_hash')
    record['result_returned_at'] = utc_now()
    index['active_request_id'] = request_id
    router._record_officer_lifecycle_result_returned(project_root, run_root, run_state, record, result)
    router._write_pm_role_work_request_index(run_root, index)
    router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'pm_role_work')


def _write_pm_role_work_result_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    _bind_router(router)
    decision_payload = _load_file_backed_role_payload_if_present(project_root, payload)
    request_id = str(decision_payload.get('request_id') or '').strip()
    batch_id = str(decision_payload.get('batch_id') or '').strip()
    if not request_id and (not batch_id):
        raise RouterError('PM role-work result decision requires request_id or batch_id')
    decided_by_role = str(decision_payload.get('decided_by_role') or decision_payload.get('recorded_by_role') or '').strip()
    if decided_by_role != 'project_manager':
        raise RouterError('PM role-work result decision requires decided_by_role=project_manager')
    decision = str(decision_payload.get('decision') or '').strip()
    if decision not in PM_ROLE_WORK_TERMINAL_DECISIONS:
        raise RouterError('PM role-work result decision must be absorbed, canceled, or superseded')
    index = router._load_pm_role_work_request_index(run_root, run_state)
    records: list[dict[str, Any]]
    if batch_id:
        records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('batch_id') or index.get('active_batch_id') or '') == batch_id]
        if not records:
            active_ids = {str(item) for item in index.get('active_request_ids', []) if item}
            records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_id')) in active_ids]
    else:
        record = router._pm_role_work_request_record(index, request_id)
        records = [record] if isinstance(record, dict) else []
    if not records:
        raise RouterError('PM role-work result decision references unknown request_id or batch_id')
    if decision == 'absorbed' and any((record.get('status') != 'result_relayed_to_pm' for record in records)):
        raise RouterError('PM may absorb role-work batch only after Controller relays every result to PM')
    if decision in {'canceled', 'superseded'} and any((record.get('status') not in PM_ROLE_WORK_OPEN_STATUSES for record in records)):
        raise RouterError('PM role-work result decision can cancel or supersede only unresolved requests')
    gate_mappings = router._pm_role_work_gate_mappings_for_decision(decision_payload, records, decision=decision)
    decision_record = {'schema_version': PM_ROLE_WORK_RESULT_DECISION_SCHEMA, 'request_id': request_id or records[0].get('request_id'), 'batch_id': batch_id or records[0].get('batch_id'), 'request_ids': [record.get('request_id') for record in records], 'decided_by_role': 'project_manager', 'decision': decision, 'decision_reason': decision_payload.get('decision_reason') or '', 'gate_mappings': gate_mappings, 'recorded_at': utc_now(), **_role_output_envelope_record(decision_payload)}
    decisions_dir = run_root / 'pm_work_requests' / 'decisions'
    decision_key = batch_id or request_id
    decision_path = decisions_dir / f'{router._safe_packet_id_component(decision_key)}.{decision}.json'
    write_json(decision_path, decision_record)
    for record in records:
        record['status'] = decision
        record['pm_result_decision'] = {'decision': decision, 'decision_path': project_relative(project_root, decision_path), 'decision_hash': packet_runtime.sha256_file(decision_path), 'recorded_at': decision_record['recorded_at']}
        for mapping in gate_mappings:
            if mapping.get('request_id') == record.get('request_id'):
                record['pm_result_decision']['gate_mapping'] = mapping
        router._record_officer_lifecycle_pm_decision(project_root, run_root, run_state, record, decision_record)
    if request_id and index.get('active_request_id') == request_id:
        index['active_request_id'] = None
    if batch_id and index.get('active_batch_id') == batch_id:
        index['active_batch_id'] = None
        index['active_request_ids'] = []
    router._write_pm_role_work_request_index(run_root, index)
    if batch_id and decision == 'absorbed':
        router._mark_parallel_batch_reviewed(run_root, 'pm_role_work', passed=True, reviewed_packet_ids=[str(record.get('packet_id')) for record in records])
    router._apply_pm_role_work_gate_mappings(project_root, run_root, run_state, decision_path=decision_path, decision_record=decision_record, mappings=gate_mappings)
    return decision


def _validate_result_bodies_opened_by_pm(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    _bind_router(router)
    for record in records:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        result = packet_runtime.load_envelope(project_root, result_path)
        opened = result.get('result_body_opened_by_role')
        if not (isinstance(opened, dict) and opened.get('role') == 'project_manager' and (opened.get('controller_relay_verified') is True) and (opened.get('body_hash_verified') is True)):
            raise RouterError(f"PM result disposition requires project_manager to open result body after Controller relay: {result.get('packet_id')}")


def _write_pm_package_result_disposition(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, batch_kind: str, package_label: str, gate_kind: str, output_path: Path) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get('decided_by_role') != 'project_manager':
        raise RouterError(f'{package_label} result disposition requires decided_by_role=project_manager')
    decision = str(payload.get('decision') or '').strip()
    if decision not in PM_PACKAGE_RESULT_DECISIONS:
        raise RouterError(f'{package_label} result disposition has unsupported decision')
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch or batch.get('status') != 'results_relayed_to_pm':
        raise RouterError(f'{package_label} result disposition requires results_relayed_to_pm')
    records = [record for record in batch.get('packets') or [] if isinstance(record, dict)]
    if not records:
        raise RouterError(f'{package_label} result disposition requires packet records')
    router._validate_result_bodies_opened_by_pm(project_root, run_state, records)
    disposition = {'schema_version': 'flowpilot.pm_package_result_disposition.v1', 'run_id': run_state['run_id'], 'batch_id': batch.get('batch_id'), 'batch_kind': batch_kind, 'package_label': package_label, 'gate_kind': gate_kind, 'decided_by_role': 'project_manager', 'decision': decision, 'decision_reason': payload.get('decision_reason') or payload.get('reason') or '', 'packet_ids': [str(record.get('packet_id')) for record in records], 'result_envelope_paths': [str(record.get('result_envelope_path')) for record in records], 'formal_gate_package_released': decision == 'absorbed', 'reviewer_receives_raw_worker_result': False, 'reviewer_review_scope': 'pm_formal_gate_package_only' if decision == 'absorbed' else 'none', 'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [], 'recorded_at': utc_now(), **_role_output_envelope_record(payload)}
    write_json(output_path, disposition)
    batch['pm_result_disposition'] = {'decision': decision, 'decision_path': project_relative(project_root, output_path), 'decision_hash': packet_runtime.sha256_file(output_path), 'recorded_at': disposition['recorded_at']}
    if decision == 'absorbed':
        batch['status'] = 'pm_absorbed'
        if batch_kind == 'material_scan':
            run_state['flags']['material_scan_results_absorbed_by_pm'] = True
        elif batch_kind == 'research':
            run_state['flags']['research_result_absorbed_for_review_by_pm'] = True
        elif batch_kind == 'current_node':
            run_state['flags']['current_node_result_absorbed_by_pm'] = True
    else:
        batch['status'] = decision
    router._write_parallel_packet_batch_state(run_root, batch)


__all__ = (
    '_write_pm_role_work_request',
    '_normalize_pm_role_work_result_recipient',
    '_validate_role_work_result_process_binding',
    '_write_role_work_result_returned',
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_package_result_disposition',
)

_LOCAL_NAMES = set(globals())
