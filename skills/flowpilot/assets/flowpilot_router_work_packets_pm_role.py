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

def _pm_role_work_target_gate_contract(router: ModuleType, payload: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    raw_contract = payload.get('target_gate_contract') if isinstance(payload.get('target_gate_contract'), dict) else {}
    gate_id = str(payload.get('target_gate_id') or raw_contract.get('gate_id') or '').strip()
    if not gate_id:
        return None
    contract = _gate_contract_for_id(gate_id)
    if contract is None:
        raise RouterError(f'PM role-work target_gate_id is not registered: {gate_id}')
    for field in ('card_id', 'required_flag', 'wait_requires_flag'):
        supplied = raw_contract.get(field)
        if supplied is not None and str(supplied) != str(contract.get(field)):
            raise RouterError(f'PM role-work target_gate_contract.{field} does not match registered gate contract')
    return _public_gate_contract(contract)

def _pm_role_work_gate_mapping_candidates(router: ModuleType, decision_payload: dict[str, Any], record: dict[str, Any]) -> str:
    _bind_router(router)
    mappings = decision_payload.get('mapped_gate_events')
    request_id = str(record.get('request_id') or '')
    gate_contract = record.get('target_gate_contract') if isinstance(record.get('target_gate_contract'), dict) else {}
    gate_id = str(gate_contract.get('gate_id') or '')
    if isinstance(mappings, dict):
        for key in (request_id, gate_id):
            mapped = str(mappings.get(key) or '').strip()
            if mapped:
                return mapped
    return str(decision_payload.get('mapped_gate_event') or decision_payload.get('target_gate_event') or decision_payload.get('gate_event') or '').strip()

def _pm_role_work_gate_mapping_artifact_path(router: ModuleType, run_root: Path, gate_contract: dict[str, Any], mapped_event: str) -> Path:
    _bind_router(router)
    gate_id = str(gate_contract.get('gate_id') or 'gate')
    if gate_id == 'product_behavior_model':
        if mapped_event in set(gate_contract.get('pass_events') or []):
            return run_root / 'flowguard' / 'product_behavior_model.json'
        if mapped_event in set(gate_contract.get('block_events') or []):
            return run_root / 'flowguard' / 'product_behavior_model_block.json'
    if gate_id == 'process_route_model':
        if mapped_event in set(gate_contract.get('pass_events') or []):
            return run_root / 'flowguard' / 'process_route_model.json'
        if mapped_event in set(gate_contract.get('block_events') or []):
            return run_root / 'flowguard' / 'process_route_model_block.json'
    return run_root / 'flowguard' / f'{router._safe_packet_id_component(gate_id)}_pm_role_work_gate_mapping.json'

def _pm_role_work_gate_mapping_alias_specs(router: ModuleType, run_root: Path, gate_contract: dict[str, Any], mapped_event: str) -> list[tuple[Path, str, str]]:
    _bind_router(router)
    gate_id = str(gate_contract.get('gate_id') or 'gate')
    if gate_id == 'product_behavior_model':
        if mapped_event in set(gate_contract.get('pass_events') or []):
            return [(run_root / 'flowguard' / 'product_architecture_modelability.json', 'flowpilot.product_architecture_modelability.v1', 'product_architecture_modelability')]
        if mapped_event in set(gate_contract.get('block_events') or []):
            return [(run_root / 'flowguard' / 'product_architecture_modelability_block.json', 'flowpilot.product_architecture_modelability_block.v1', 'product_architecture_modelability_block')]
    if gate_id == 'process_route_model':
        return [(run_root / 'flowguard' / 'route_process_check.json', 'flowpilot.route_process_check.v1', 'route_process_check')]
    return []

def _pm_role_work_gate_mappings_for_decision(router: ModuleType, decision_payload: dict[str, Any], records: list[dict[str, Any]], *, decision: str) -> list[dict[str, Any]]:
    _bind_router(router)
    if decision != 'absorbed':
        return []
    mappings: list[dict[str, Any]] = []
    for record in records:
        gate_contract = record.get('target_gate_contract')
        if not isinstance(gate_contract, dict):
            continue
        mapped_event = router._pm_role_work_gate_mapping_candidates(decision_payload, record)
        allowed_events = set(gate_contract.get('pass_events') or []) | set(gate_contract.get('block_events') or [])
        if not mapped_event:
            raise RouterError('gate-targeted PM role-work absorption requires mapped_gate_event')
        if mapped_event not in allowed_events:
            raise RouterError('mapped_gate_event must be one of the target gate pass/block events')
        mappings.append({'request_id': record.get('request_id'), 'packet_id': record.get('packet_id'), 'result_envelope_path': record.get('result_envelope_path'), 'result_envelope_hash': record.get('result_envelope_hash'), 'target_gate_contract': gate_contract, 'mapped_gate_event': mapped_event})
    return mappings

def _apply_pm_role_work_gate_mappings(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, decision_path: Path, decision_record: dict[str, Any], mappings: list[dict[str, Any]]) -> None:
    _bind_router(router)
    if not mappings:
        return
    decision_hash = packet_runtime.sha256_file(decision_path)
    for mapping in mappings:
        mapped_event = str(mapping['mapped_gate_event'])
        meta = EXTERNAL_EVENTS[mapped_event]
        for clear_flag in GATE_OUTCOME_PASS_CLEAR_FLAGS.get(mapped_event, ()):
            run_state.setdefault('flags', {})[clear_flag] = False
        run_state.setdefault('flags', {})[meta['flag']] = True
        gate_contract = mapping['target_gate_contract']
        pass_events = set(gate_contract.get('pass_events') or [])
        is_pass_mapping = mapped_event in pass_events
        artifact_path = router._pm_role_work_gate_mapping_artifact_path(run_root, gate_contract, mapped_event)
        artifact = {'schema_version': 'flowpilot.pm_role_work_gate_mapping.v1', 'run_id': run_state['run_id'], 'gate_id': gate_contract.get('gate_id'), 'required_flag': gate_contract.get('required_flag'), 'reviewed_by_role': gate_contract.get('target_role'), 'passed': is_pass_mapping, 'mapped_gate_event': mapped_event, 'source_event': PM_ROLE_WORK_RESULT_DECISION_EVENT, 'pm_role_work_request_id': mapping.get('request_id'), 'packet_id': mapping.get('packet_id'), 'result_envelope_path': mapping.get('result_envelope_path'), 'result_envelope_hash': mapping.get('result_envelope_hash'), 'pm_decision_path': project_relative(project_root, decision_path), 'pm_decision_hash': decision_hash, 'sealed_result_body_read_by_controller': False, 'controller_visibility': 'result_envelope_and_pm_mapping_only', 'recorded_at': decision_record['recorded_at']}
        if gate_contract.get('gate_id') == 'process_route_model':
            if mapped_event in PROCESS_ROUTE_MODEL_PASS_EVENTS:
                artifact['process_viability_verdict'] = 'pass'
            elif mapped_event in PROCESS_ROUTE_MODEL_REPAIR_EVENTS:
                artifact['process_viability_verdict'] = 'repair_required'
            else:
                artifact['process_viability_verdict'] = 'blocked'
        write_json(artifact_path, artifact)
        for alias_path, schema_version, alias_kind in router._pm_role_work_gate_mapping_alias_specs(run_root, gate_contract, mapped_event):
            _write_compatibility_alias_artifact(project_root, artifact_path, alias_path, schema_version=schema_version, alias_kind=alias_kind)
        _sync_model_gate_alias_flags(run_state, mapped_event)
        run_state.setdefault('events', []).append({'event': mapped_event, 'summary': meta['summary'], 'payload': {'mapped_from_event': PM_ROLE_WORK_RESULT_DECISION_EVENT, 'pm_role_work_request_id': mapping.get('request_id'), 'packet_id': mapping.get('packet_id'), 'target_gate_id': gate_contract.get('gate_id'), 'gate_mapping_artifact_path': project_relative(project_root, artifact_path), 'sealed_result_body_read_by_controller': False}, 'recorded_at': decision_record['recorded_at']})

def _pm_role_work_result_decision_payload_contract(router: ModuleType, *, name: str, required_fields: list[str], allowed_values: dict[str, list[Any]], records: list[dict[str, Any]], expected_request_id: str | None=None, expected_batch_id: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    contract = {'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': name, 'required_fields': list(required_fields), 'allowed_values': dict(allowed_values)}
    if expected_request_id:
        contract['expected_request_id'] = expected_request_id
    if expected_batch_id:
        contract['expected_batch_id'] = expected_batch_id
    gate_contracts = [record.get('target_gate_contract') for record in records if isinstance(record.get('target_gate_contract'), dict)]
    if gate_contracts:
        allowed_gate_events = sorted({str(event) for gate_contract in gate_contracts for event in [*(gate_contract.get('pass_events') or []), *(gate_contract.get('block_events') or [])] if str(event)})
        if 'mapped_gate_event' not in contract['required_fields']:
            contract['required_fields'].append('mapped_gate_event')
        contract['allowed_values']['mapped_gate_event'] = allowed_gate_events
        contract['gate_targeted_role_work'] = True
        contract['target_gate_contracts'] = gate_contracts
        contract['gate_mapping_rule'] = 'Absorbing this role-work result can close the target gate only when PM maps it to one concrete target gate pass/block event.'
    return contract

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

def _next_pm_role_work_request_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    index = router._load_pm_role_work_request_index(run_root, run_state)
    batch_records = router._active_pm_role_work_batch_records(index)
    if batch_records:
        index_path = router._pm_role_work_request_index_path(run_root)
        lifecycle_index_path = router._officer_request_lifecycle_index_path(run_root)
        packet_ids = [record.get('packet_id') for record in batch_records]
        to_roles = ','.join(sorted({str(record.get('to_role') or '') for record in batch_records if record.get('to_role')}))
        if any((record.get('status') == 'open' for record in batch_records)):
            open_records = [record for record in batch_records if record.get('status') == 'open']
            active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, open_records, packet_family='pm_role_work', mode='lease_on_pm_role_work_request_relay')
            allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), *[str(record.get('packet_envelope_path')) for record in batch_records]]
            if not run_state.get('ledger_check_requested'):
                return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_batch_relayed_with_ledger_check', summary='Check the packet ledger and relay every PM role-work request packet in the active batch without opening sealed bodies.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=to_roles, extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan})
            return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_batch_relayed', summary='Relay every PM role-work request packet in the active batch without opening sealed bodies.', allowed_reads=[project_relative(project_root, index_path), *[str(record.get('packet_envelope_path')) for record in batch_records]], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=to_roles, extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan})
        if any((record.get('status') in {'packet_relayed', 'result_returned'} for record in batch_records)) and (not all((record.get('status') == 'result_returned' for record in batch_records))):
            missing_roles = [str(record.get('to_role') or record.get('request_id') or 'unknown') for record in batch_records if not resolve_project_path(project_root, str(record.get('result_envelope_path') or '')).exists()]
            action = _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_role_work_batch_results', summary='Controller has relayed the PM role-work batch and must wait for every target role to return a result envelope.', allowed_external_events=[ROLE_WORK_RESULT_RETURNED_EVENT], to_role=','.join(sorted(set(missing_roles))) if missing_roles else to_roles, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'role_work_result_returned_envelope', 'required_fields': ['request_id', 'packet_id', 'result_envelope_path'], 'batch_id': index.get('active_batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'expected_next_recipient': 'project_manager'}, producer_roles_override=missing_roles)
            if router._pm_role_work_records_are_nonblocking(batch_records):
                action['nonblocking_wait'] = True
                action['dependency_class'] = router._pm_role_work_records_dependency_class(batch_records)
            return action
        if all((record.get('status') == 'result_returned' for record in batch_records)):
            allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), *[str(record.get('result_envelope_path')) for record in batch_records]]
            if not run_state.get('ledger_check_requested'):
                return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_batch_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay every role-work result envelope in the batch back to PM without opening sealed result bodies.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path)})
            return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_batch_relayed_to_pm', summary='Relay every role-work result envelope in the batch back to PM without opening sealed result bodies.', allowed_reads=[project_relative(project_root, index_path), *[str(record.get('result_envelope_path')) for record in batch_records]], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path)})
        if all((record.get('status') == 'result_relayed_to_pm' for record in batch_records)):
            action = _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_role_work_batch_result_decision', summary='Controller relayed the full role-work result batch to PM and must wait for one PM batch disposition.', allowed_external_events=[PM_ROLE_WORK_RESULT_DECISION_EVENT], to_role='project_manager', payload_contract=router._pm_role_work_result_decision_payload_contract(name='pm_role_work_batch_result_decision', required_fields=['decided_by_role', 'batch_id', 'decision'], allowed_values={'decided_by_role': ['project_manager'], 'decision': sorted(PM_ROLE_WORK_TERMINAL_DECISIONS)}, records=batch_records, expected_batch_id=str(index.get('active_batch_id') or '')))
            if router._pm_role_work_records_are_nonblocking(batch_records):
                action['nonblocking_wait'] = True
                action['dependency_class'] = router._pm_role_work_records_dependency_class(batch_records)
            return action
    active = router._active_pm_role_work_request(index)
    if not isinstance(active, dict):
        return None
    index_path = router._pm_role_work_request_index_path(run_root)
    lifecycle_index_path = router._officer_request_lifecycle_index_path(run_root)
    packet_ids = [active.get('packet_id')]
    if active.get('status') == 'open':
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, [active], packet_family='pm_role_work', mode='lease_on_pm_role_work_request_relay')
        allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), str(active.get('packet_envelope_path'))]
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_packet_relayed_with_ledger_check', summary='Check the packet ledger and relay the PM role-work request packet without opening the sealed body.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=str(active.get('to_role') or ''), extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': packet_ids, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan})
        return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_packet_relayed', summary='Relay the PM role-work request packet without opening the sealed body.', allowed_reads=[project_relative(project_root, index_path), str(active.get('packet_envelope_path'))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=str(active.get('to_role') or ''), extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan})
    if active.get('status') == 'result_returned':
        allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), str(active.get('result_envelope_path'))]
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay the role-work result envelope back to PM without opening the sealed result body.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': packet_ids, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path)})
        return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_relayed_to_pm', summary='Relay the role-work result envelope back to PM without opening the sealed result body.', allowed_reads=[project_relative(project_root, index_path), str(active.get('result_envelope_path'))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path)})
    if active.get('status') == 'packet_relayed':
        status_packet_path = router._controller_status_packet_path_from_packet_envelope(active.get('packet_envelope_path'))
        allowed_reads = [project_relative(project_root, router.run_state_path(run_root))]
        if status_packet_path:
            allowed_reads.append(status_packet_path)
        action = _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_role_work_result_returned', summary='Controller has relayed the PM role-work packet and must wait for the target role to return its result envelope.', allowed_external_events=[ROLE_WORK_RESULT_RETURNED_EVENT], to_role=str(active.get('to_role') or ''), allowed_reads_extra=allowed_reads, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'role_work_result_returned_envelope', 'required_fields': ['request_id', 'packet_id', 'result_envelope_path'], 'expected_request_id': active.get('request_id'), 'expected_packet_id': active.get('packet_id'), 'expected_next_recipient': 'project_manager'})
        if router._pm_role_work_record_is_nonblocking(active):
            action['nonblocking_wait'] = True
            action['dependency_class'] = str(active.get('request_mode') or 'advisory')
        return action
    if active.get('status') == 'result_relayed_to_pm':
        action = _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_role_work_result_decision', summary='Controller relayed the role-work result to PM and must wait for PM to absorb, cancel, or supersede it.', allowed_external_events=[PM_ROLE_WORK_RESULT_DECISION_EVENT], to_role='project_manager', payload_contract=router._pm_role_work_result_decision_payload_contract(name='pm_role_work_result_decision', required_fields=['decided_by_role', 'request_id', 'decision'], allowed_values={'decided_by_role': ['project_manager'], 'decision': sorted(PM_ROLE_WORK_TERMINAL_DECISIONS)}, records=[active], expected_request_id=str(active.get('request_id') or '')))
        if router._pm_role_work_record_is_nonblocking(active):
            action['nonblocking_wait'] = True
            action['dependency_class'] = str(active.get('request_mode') or 'advisory')
        return action
    return None

def _try_reconcile_pm_role_work_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    index = router._load_pm_role_work_request_index(run_root, run_state)
    candidates = [{'request_id': str(record.get('request_id') or ''), 'packet_id': str(record.get('packet_id') or ''), 'result_envelope_path': str(record.get('result_envelope_path') or '')} for record in index.get('requests', []) if isinstance(record, dict) and record.get('status') == 'packet_relayed' and record.get('request_id') and record.get('packet_id') and resolve_project_path(project_root, str(record.get('result_envelope_path') or '')).exists()]
    changed = False
    for item in candidates:
        result_path = resolve_project_path(project_root, item['result_envelope_path'])
        payload = {'request_id': item['request_id'], 'packet_id': item['packet_id'], 'result_envelope_path': project_relative(project_root, result_path), 'result_envelope_hash': packet_runtime.sha256_file(result_path), 'reconciled_from_result_envelope': True}
        try:
            router._write_role_work_result_returned(project_root, run_root, run_state, payload)
        except (RouterError, packet_runtime.PacketRuntimeError):
            continue
        changed = _record_router_reconciled_external_event(project_root, run_root, run_state, ROLE_WORK_RESULT_RETURNED_EVENT, payload) or changed
    return changed

__all__ = (
    '_pm_role_work_target_gate_contract',
    '_pm_role_work_gate_mapping_candidates',
    '_pm_role_work_gate_mapping_artifact_path',
    '_pm_role_work_gate_mapping_alias_specs',
    '_pm_role_work_gate_mappings_for_decision',
    '_apply_pm_role_work_gate_mappings',
    '_pm_role_work_result_decision_payload_contract',
    '_write_pm_role_work_request',
    '_normalize_pm_role_work_result_recipient',
    '_validate_role_work_result_process_binding',
    '_write_role_work_result_returned',
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_package_result_disposition',
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
    '_next_pm_role_work_request_action',
    '_try_reconcile_pm_role_work_results',
)

_LOCAL_NAMES = set(globals())
