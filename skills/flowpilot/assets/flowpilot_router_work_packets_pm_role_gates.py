"""PM role-work gate-mapping helpers for the FlowPilot router."""

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


__all__ = (
    '_pm_role_work_target_gate_contract',
    '_pm_role_work_gate_mapping_candidates',
    '_pm_role_work_gate_mapping_artifact_path',
    '_pm_role_work_gate_mapping_alias_specs',
    '_pm_role_work_gate_mappings_for_decision',
    '_apply_pm_role_work_gate_mappings',
    '_pm_role_work_result_decision_payload_contract',
)

_LOCAL_NAMES = set(globals())
