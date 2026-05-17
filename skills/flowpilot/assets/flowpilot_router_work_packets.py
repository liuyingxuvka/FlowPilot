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

def _material_packet_body_text_from_spec(router: ModuleType, project_root: Path, spec: dict[str, Any]) -> str:
    _bind_router(router)
    body_text = spec.get('body_text')
    if isinstance(body_text, str) and body_text.strip():
        return body_text
    raw_body_path = spec.get('body_path') or spec.get('packet_body_path')
    raw_body_hash = spec.get('body_hash') or spec.get('packet_body_hash')
    if not raw_body_path or not raw_body_hash:
        raise RouterError('material scan packet requires non-empty body_text or file-backed body_path/body_hash')
    body_path = resolve_project_path(project_root, str(raw_body_path))
    if not body_path.exists():
        raise RouterError(f'material scan packet body path is missing: {raw_body_path}')
    actual_hash = hashlib.sha256(body_path.read_bytes()).hexdigest()
    if actual_hash != str(raw_body_hash):
        raise RouterError('material scan packet body hash mismatch')
    loaded_text = body_path.read_text(encoding='utf-8')
    if not loaded_text.strip():
        raise RouterError('material scan packet body file is empty')
    return loaded_text

def _write_material_scan_packets(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    packet_specs = payload.get('packets')
    if not isinstance(packet_specs, list) or not packet_specs:
        raise RouterError('material scan requires payload.packets with PM-authored packet bodies')
    records: list[dict[str, Any]] = []
    batch_id = str(payload.get('batch_id') or 'material-scan-batch-001')
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError('each material scan packet must be an object')
        packet_id = str(spec.get('packet_id') or f'material-scan-{index:03d}')
        to_role = str(spec.get('to_role') or 'worker_a')
        if to_role not in {'worker_a', 'worker_b'}:
            raise RouterError('material scan packet must target worker_a or worker_b')
        body_text = router._material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=str(spec.get('node_id') or 'material-intake'), body_text=body_text, is_current_node=False, packet_type='material_scan', metadata={'stage': 'material_scan', 'source': 'pm_issues_material_and_capability_scan_packets', **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None)
        records.append(router._packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type='material_scan'))
    router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='material_scan', phase='material_scan', records=records, node_id='material-intake', join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_before_material_sufficiency_review', pm_absorption_required=True)
    write_json(router._material_scan_index_path(run_root), {'schema_version': 'flowpilot.material_scan_packets.v1', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'batch_id': batch_id, 'batch_kind': 'material_scan', 'controller_may_read_packet_body': False, 'router_direct_dispatch_required_before_worker': True, 'reviewer_dispatch_required_before_worker': False, 'packets': records, 'written_at': utc_now()})
    router._set_pre_route_frontier_phase(run_root, str(run_state['run_id']), 'material_scan')

def _write_material_dispatch_block_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    checked_by_role = str(payload.get('checked_by_role') or payload.get('reviewed_by_role') or '').strip()
    if checked_by_role not in {'controller', 'router', 'human_like_reviewer'}:
        raise RouterError('material dispatch block report requires checked_by_role=controller/router or reviewed_by_role=human_like_reviewer')
    if payload.get('dispatch_allowed') is not False:
        raise RouterError('material dispatch block report requires dispatch_allowed=false')
    blockers = payload.get('blockers')
    if not isinstance(blockers, list) or not blockers:
        raise RouterError('material dispatch block report requires non-empty blockers')
    material_index_path = router._material_scan_index_path(run_root)
    if not material_index_path.exists():
        raise RouterError('material dispatch block report requires material scan packet index')
    report_path = run_root / 'material' / 'material_dispatch_block.json'
    reported_at = utc_now()
    write_json(report_path, {'schema_version': 'flowpilot.material_dispatch_block.v1', 'run_id': run_state['run_id'], 'checked_by_role': checked_by_role, 'dispatch_allowed': False, 'source_paths': [project_relative(project_root, material_index_path)], 'checks': payload.get('checks') if isinstance(payload.get('checks'), dict) else {}, 'blockers': blockers, 'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [], 'reported_at': reported_at, **_role_output_envelope_record(payload)})
    run_state['material_dispatch_block'] = {'path': project_relative(project_root, report_path), 'blockers': blockers, 'reported_at': reported_at}
    run_state['flags']['reviewer_dispatch_allowed'] = False

def _write_material_dispatch_recheck_protocol_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, event_name: str='router_protocol_blocker_material_scan_dispatch_recheck') -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    checked_by_role = str(payload.get('checked_by_role') or payload.get('reviewed_by_role') or '').strip()
    if checked_by_role not in {'controller', 'router', 'human_like_reviewer'}:
        raise RouterError('material dispatch recheck protocol blocker requires checked_by_role=controller/router or reviewed_by_role=human_like_reviewer')
    blockers = payload.get('blockers')
    if not isinstance(blockers, list) or not blockers:
        raise RouterError('material dispatch recheck protocol blocker requires non-empty blockers')
    tx_path, transaction = router._active_repair_transaction_for_event(run_root, event_name)
    if tx_path is None or transaction is None:
        raise RouterError('material dispatch protocol blocker requires an active repair transaction')
    reported_at = utc_now()
    report_path = run_root / 'control_blocks' / f"{transaction['transaction_id']}.reviewer_protocol_blocker.json"
    write_json(report_path, {'schema_version': 'flowpilot.repair_transaction_protocol_blocker.v1', 'run_id': run_state['run_id'], 'repair_transaction_id': transaction['transaction_id'], 'checked_by_role': checked_by_role, 'event_name': event_name, 'blockers': blockers, 'source_paths': payload.get('source_paths') if isinstance(payload.get('source_paths'), list) else [], 'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [], 'reported_at': reported_at, **_role_output_envelope_record(payload)})
    run_state['material_dispatch_block'] = {'path': project_relative(project_root, report_path), 'blockers': blockers, 'reported_at': reported_at, 'repair_transaction_id': transaction['transaction_id'], 'protocol_blocker': True}
    run_state['flags']['reviewer_dispatch_allowed'] = False

def _write_material_sufficiency_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, sufficient: bool) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('material sufficiency report must be reviewed_by_role=human_like_reviewer')
    if not run_state['flags'].get('material_scan_results_absorbed_by_pm'):
        raise RouterError('material sufficiency report requires PM-absorbed material result package')
    material_index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
    raw_agent_map = payload.get('agent_role_map')
    router._validate_packet_group_for_reviewer(project_root, run_state, material_index['packets'], audit_path=run_root / 'material' / 'material_packet_review_audit.json', agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None)
    if payload.get('direct_material_sources_checked') is not True:
        raise RouterError('material sufficiency report requires direct_material_sources_checked=true')
    if payload.get('packet_matches_checked_sources') is not True:
        raise RouterError('material sufficiency report requires packet_matches_checked_sources=true')
    if sufficient and payload.get('pm_ready') is not True:
        raise RouterError('sufficient material report requires pm_ready=true')
    write_json(run_root / 'material' / 'material_sufficiency_report.json', {'schema_version': 'flowpilot.material_sufficiency_report.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'sufficient': sufficient, 'direct_material_sources_checked': True, 'packet_matches_checked_sources': True, 'pm_ready': bool(payload.get('pm_ready')), 'checked_source_paths': payload.get('checked_source_paths') or [], 'blockers': payload.get('blockers') or [], 'reported_at': utc_now(), **_role_output_envelope_record(payload)})

def _write_research_package(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    decision_question = payload.get('decision_question')
    if not decision_question:
        raise RouterError('research package requires decision_question')
    packet_specs = payload.get('packets')
    if packet_specs is not None and (not isinstance(packet_specs, list) or not packet_specs):
        raise RouterError('research package packets must be a non-empty list when provided')
    package = {'schema_version': 'flowpilot.research_package.v1', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'decision_question': decision_question, 'allowed_source_types': payload.get('allowed_source_types') or [], 'host_capability_decision': payload.get('host_capability_decision') or 'local_sources_only', 'worker_owner': payload.get('worker_owner') or 'worker_a', 'batch_id': payload.get('batch_id') or 'research-batch-001', 'packets': packet_specs or [], 'reviewer_direct_check_required': True, 'stop_conditions': payload.get('stop_conditions') or [], 'written_at': utc_now(), **_role_output_envelope_record(payload)}
    write_json(run_root / 'research' / 'research_package.json', package)

def _write_research_capability_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    package_path = run_root / 'research' / 'research_package.json'
    if not package_path.exists():
        raise RouterError('research capability decision requires research_package.json')
    if payload.get('explicit_user_approval_required') is True and payload.get('explicit_user_approval_recorded') is not True:
        raise RouterError('research capability decision requires recorded user approval for gated sources')
    package = read_json(package_path)
    worker_owner = str(package.get('worker_owner') or 'worker_a')
    if worker_owner not in {'worker_a', 'worker_b'}:
        raise RouterError('research worker owner must be worker_a or worker_b')
    batch_id = str(payload.get('batch_id') or package.get('batch_id') or 'research-batch-001')
    allowed_source_types = list(package.get('allowed_source_types') or [])
    allowed_sources = payload.get('allowed_sources')
    if not isinstance(allowed_sources, list) or not allowed_sources:
        allowed_sources = allowed_source_types
    stop_conditions = list(package.get('stop_conditions') or [])
    research_body_payload = {'research_package_path': project_relative(project_root, package_path), 'decision_question': package.get('decision_question'), 'allowed_source_types': allowed_source_types, 'allowed_sources': allowed_sources, 'host_capability_decision': package.get('host_capability_decision'), 'worker_owner': worker_owner, 'reviewer_direct_check_required': bool(package.get('reviewer_direct_check_required')), 'stop_conditions': stop_conditions}
    raw_packet_specs = payload.get('packets') if isinstance(payload.get('packets'), list) else package.get('packets')
    packet_specs = raw_packet_specs if isinstance(raw_packet_specs, list) and raw_packet_specs else [{'packet_id': payload.get('packet_id') or 'research-packet-001', 'to_role': worker_owner, 'body_text': payload.get('worker_packet_body'), 'output_contract': payload.get('output_contract') if isinstance(payload.get('output_contract'), dict) else None}]
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError('each research packet spec must be an object')
        to_role = str(spec.get('to_role') or spec.get('recipient_role') or worker_owner)
        if to_role not in {'worker_a', 'worker_b', 'process_flowguard_officer', 'product_flowguard_officer'}:
            raise RouterError('research packets may target workers or FlowGuard officers only')
        packet_type = 'officer_request' if to_role in {'process_flowguard_officer', 'product_flowguard_officer'} else 'research'
        packet_id = str(spec.get('packet_id') or f'research-packet-{index:03d}')
        body_text = spec.get('body_text')
        if body_text is None:
            body_text = json.dumps({**research_body_payload, 'batch_id': batch_id, 'packet_focus': spec.get('packet_focus') or spec.get('request_kind') or 'research'}, indent=2, sort_keys=True)
        if not isinstance(body_text, str) or not body_text.strip():
            raise RouterError('research packet requires non-empty body_text')
        output_contract = spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None
        if output_contract is None and packet_type == 'officer_request':
            output_contract = router._pm_role_work_output_contract(run_root, contract_id=str(spec.get('output_contract_id') or 'flowpilot.output_contract.officer_model_report.v1'), to_role=to_role, packet_type=packet_type, node_id='research')
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id='research', body_text=body_text, is_current_node=False, packet_type=packet_type, metadata={'stage': 'research', 'source': 'research_capability_decision_recorded', 'batch_id': batch_id, 'research_package_path': project_relative(project_root, package_path), **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=output_contract)
        records.append(router._packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=packet_type))
    router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='research', phase='research', records=records, node_id='research', join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_before_research_direct_source_review', pm_absorption_required=True)
    write_json(run_root / 'research' / 'research_capability_decision.json', {'schema_version': 'flowpilot.research_capability_decision.v1', 'run_id': run_state['run_id'], 'recorded_by_role': 'project_manager', 'research_package_path': project_relative(project_root, package_path), 'decision_question': package.get('decision_question'), 'allowed_source_types': allowed_source_types, 'allowed_sources': allowed_sources, 'host_capability_decision': package.get('host_capability_decision'), 'worker_owner': worker_owner, 'batch_id': batch_id, 'reviewer_direct_check_required': bool(package.get('reviewer_direct_check_required')), 'stop_conditions': stop_conditions, 'explicit_user_approval_required': bool(payload.get('explicit_user_approval_required')), 'explicit_user_approval_recorded': bool(payload.get('explicit_user_approval_recorded')), 'worker_packet_id': records[0]['packet_id'], 'packet_ids': [record['packet_id'] for record in records], 'recorded_at': utc_now(), **_role_output_envelope_record(payload)})
    write_json(router._research_packet_index_path(run_root), {'schema_version': 'flowpilot.research_packet.v1', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'batch_id': batch_id, 'packet_id': records[0]['packet_id'], 'worker_owner': worker_owner, 'controller_may_read_packet_body': False, 'packet_envelope_path': records[0]['packet_envelope_path'], 'packet_body_path': records[0].get('packet_body_path'), 'packet_body_hash': records[0].get('packet_body_hash'), 'body_path': records[0].get('packet_body_path'), 'body_hash': records[0].get('packet_body_hash'), 'result_envelope_path': records[0]['result_envelope_path'], 'packets': records, 'written_at': utc_now()})

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

def _write_worker_research_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    if not run_state['flags'].get('research_packet_relayed'):
        raise RouterError('research report requires research packet made available to worker')
    research_index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
    router._validate_packet_bodies_opened_by_targets(project_root, run_state, research_index['packets'])
    router._validate_results_exist_for_packets(project_root, run_state, research_index['packets'], next_recipient='project_manager')
    completed_roles = sorted({str(record.get('to_role')) for record in research_index['packets'] if isinstance(record, dict)})
    if not payload.get('answers_decision_question', True):
        raise RouterError('research batch report must state whether it answers the PM decision question')
    write_json(run_root / 'research' / 'worker_research_report.json', {'schema_version': 'flowpilot.research_worker_report.v1', 'run_id': run_state['run_id'], 'batch_id': research_index.get('batch_id'), 'packet_count': len(research_index['packets']), 'completed_by_roles': completed_roles, 'completed_by_role': payload.get('completed_by_role') or ','.join(completed_roles), 'packet_ids': [record.get('packet_id') for record in research_index['packets'] if isinstance(record, dict)], 'raw_evidence_pointers': payload.get('raw_evidence_pointers') or [], 'negative_findings': payload.get('negative_findings') or [], 'contradictions': payload.get('contradictions') or [], 'confidence_boundary': payload.get('confidence_boundary') or 'worker report only; reviewer check required', 'answers_decision_question': bool(payload.get('answers_decision_question', True)), 'reported_at': utc_now()})

def _write_material_understanding(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    if payload.get('pm_owned', True) is not True:
        raise RouterError('material understanding must be PM-owned')
    if run_state['flags'].get('pm_research_requested') and (not run_state['flags'].get('research_result_absorbed_by_pm')):
        raise RouterError('PM material understanding requires reviewed research to be absorbed when research was requested')
    payload_snapshot_path = run_root / 'material' / 'pm_material_understanding_payload.json'
    write_json(payload_snapshot_path, {'schema_version': 'flowpilot.pm_material_understanding_payload.v1', 'run_id': run_state['run_id'], 'payload_body': _without_role_output_envelope(payload), 'source_role_output_envelope': _role_output_envelope_record(payload).get('_role_output_envelope'), 'written_at': utc_now()})
    write_json(run_root / 'pm_material_understanding.json', {'schema_version': 'flowpilot.pm_material_understanding.v1', 'run_id': run_state['run_id'], 'pm_owned': True, 'source_paths': {'payload_snapshot': project_relative(project_root, payload_snapshot_path)}, 'source_material_review': run_state.get('material_review'), 'research_absorbed': bool(run_state['flags'].get('research_result_absorbed_by_pm')), 'material_summary': payload.get('material_summary') or '', 'contradictions': payload.get('contradictions') or [], 'deferred_sources': payload.get('deferred_sources') or [], 'route_consequences': payload.get('route_consequences') or [], 'written_at': utc_now(), **_role_output_envelope_record(payload)})

def _packet_paths(router: ModuleType, project_root: Path, run_state: dict[str, Any], packet_id: str) -> dict[str, Any]:
    _bind_router(router)
    return packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))

def _active_current_node_packet_records(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    run_root = project_root / str(run_state['run_root'])
    frontier = router._active_frontier(run_root)
    index_path = _active_node_packet_index_path(run_root, frontier)
    if not index_path.exists():
        return []
    return router._load_packet_index(index_path, label='current-node batch')['packets']

def _current_node_batch_packet_record(router: ModuleType, project_root: Path, run_state: dict[str, Any], *, preferred_packet_id: str | None=None) -> dict[str, Any] | None:
    _bind_router(router)
    records = router._active_current_node_packet_records(project_root, run_state)
    if not records:
        return None
    candidate_ids: list[str] = []

    def add_candidate(value: Any) -> None:
        text = str(value or '').strip()
        if text and text not in candidate_ids:
            candidate_ids.append(text)
    add_candidate(preferred_packet_id)
    add_candidate(router._latest_event_payload(run_state, 'pm_registers_current_node_packet').get('packet_id'))
    add_candidate(router._latest_event_payload(run_state, 'worker_current_node_result_returned').get('packet_id'))
    run_root = project_root / str(run_state['run_root'])
    frontier = router._active_frontier(run_root)
    add_candidate(frontier.get('active_packet_id'))
    add_candidate(run_state.get('current_node_packet_id'))
    for packet_id in candidate_ids:
        matches = [record for record in records if str(record.get('packet_id') or '') == packet_id]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RouterError(f'current-node batch has duplicate packet_id: {packet_id}')
    if len(records) == 1:
        return records[0]
    return None

def _packet_envelope_path(router: ModuleType, project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    _bind_router(router)
    raw_path = payload.get('packet_envelope_path')
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get('packet_id')
    if not packet_id:
        raise RouterError('current-node packet event requires packet_id or packet_envelope_path')
    return router._packet_paths(project_root, run_state, str(packet_id))['packet_envelope']

def _result_envelope_path(router: ModuleType, project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> Path:
    _bind_router(router)
    raw_path = payload.get('result_envelope_path')
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = payload.get('packet_id') or router._latest_event_payload(run_state, 'pm_registers_current_node_packet').get('packet_id')
    if not packet_id:
        raise RouterError('current-node result event requires packet_id or result_envelope_path')
    return router._packet_paths(project_root, run_state, str(packet_id))['result_envelope']

def _current_node_packet_context(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    _bind_router(router)
    payload = router._latest_event_payload(run_state, 'pm_registers_current_node_packet')
    try:
        envelope_path = router._packet_envelope_path(project_root, run_state, payload)
    except RouterError as exc:
        if str(exc) != 'current-node packet event requires packet_id or packet_envelope_path':
            raise
        record = router._current_node_batch_packet_record(project_root, run_state)
        if record is None:
            raise
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
    if not envelope_path.exists():
        raise RouterError(f'current-node packet envelope is missing: {envelope_path}')
    envelope = packet_runtime.load_envelope(project_root, envelope_path)
    return (envelope, envelope_path)

def _current_node_packet_records(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    records = router._active_current_node_packet_records(project_root, run_state)
    if records:
        return records
    envelope, _envelope_path = router._current_node_packet_context(project_root, run_state)
    return [router._packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=str(envelope.get('packet_type') or 'work_packet'))]

def _current_node_results_complete(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    for record in router._current_node_packet_records(project_root, run_state):
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            return False
    return True

def _current_node_missing_result_roles(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> list[str]:
    _bind_router(router)
    missing: list[str] = []
    for record in router._current_node_packet_records(project_root, run_state):
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            missing.append(str(record.get('to_role') or record.get('packet_id') or 'unknown'))
    return sorted(set(missing))

def _active_child_skill_bindings_from_plan(router: ModuleType, plan: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    raw_bindings = plan.get('active_child_skill_bindings')
    if raw_bindings in (None, []):
        return []
    if not isinstance(raw_bindings, list):
        raise RouterError('node_acceptance_plan.active_child_skill_bindings must be a list')
    bindings: list[dict[str, Any]] = []
    for index, binding in enumerate(raw_bindings, start=1):
        if not isinstance(binding, dict):
            raise RouterError(f'active_child_skill_bindings[{index}] must be an object')
        if binding.get('applies_to_this_node') is False:
            continue
        if not binding.get('binding_id'):
            raise RouterError(f'active_child_skill_bindings[{index}] requires binding_id')
        if not binding.get('source_path'):
            raise RouterError(f'active_child_skill_bindings[{index}] requires source_path')
        bindings.append(binding)
    return bindings

def _active_child_skill_source_paths(router: ModuleType, bindings: list[dict[str, Any]]) -> list[str]:
    _bind_router(router)
    paths: list[str] = []
    for binding in bindings:
        source_path = binding.get('source_path')
        if source_path:
            paths.append(str(source_path))
        referenced_paths = binding.get('referenced_paths')
        if isinstance(referenced_paths, list):
            paths.extend((str(item) for item in referenced_paths if item))
    return sorted(set(paths))

def _metadata_string_list(router: ModuleType, metadata: dict[str, Any], *keys: str) -> list[str]:
    _bind_router(router)
    values: list[str] = []
    for key in keys:
        raw_value = metadata.get(key)
        if isinstance(raw_value, list):
            values.extend((str(item) for item in raw_value if item))
        elif isinstance(raw_value, str) and raw_value:
            values.append(raw_value)
    return sorted(set(values))

def _metadata_binding_ids(router: ModuleType, metadata: dict[str, Any], *keys: str) -> list[str]:
    _bind_router(router)
    ids: list[str] = []
    for key in keys:
        raw_value = metadata.get(key)
        if isinstance(raw_value, list):
            for item in raw_value:
                if isinstance(item, dict) and item.get('binding_id'):
                    ids.append(str(item['binding_id']))
                elif isinstance(item, str) and item:
                    ids.append(item)
    return sorted(set(ids))

def _current_node_result_context(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> tuple[dict[str, Any], Path]:
    _bind_router(router)
    payload = router._latest_event_payload(run_state, 'worker_current_node_result_returned')
    try:
        result_path = router._result_envelope_path(project_root, run_state, payload)
    except RouterError as exc:
        if str(exc) != 'current-node result event requires packet_id or result_envelope_path':
            raise
        record = router._current_node_batch_packet_record(project_root, run_state, preferred_packet_id=str(payload.get('packet_id') or '') or None)
        if record is None:
            raise
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
    if not result_path.exists():
        raise RouterError(f'current-node result envelope is missing: {result_path}')
    result = packet_runtime.load_envelope(project_root, result_path)
    return (result, result_path)

def _packet_envelope_path_from_record(router: ModuleType, project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    _bind_router(router)
    raw_path = record.get('packet_envelope_path')
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get('packet_id')
    if not packet_id:
        raise RouterError('packet record requires packet_id or packet_envelope_path')
    return router._packet_paths(project_root, run_state, str(packet_id))['packet_envelope']

def _result_envelope_path_from_packet_record(router: ModuleType, project_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> Path:
    _bind_router(router)
    raw_path = record.get('result_envelope_path')
    if raw_path:
        path = Path(str(raw_path))
        return path if path.is_absolute() else project_root / path
    packet_id = record.get('packet_id')
    if not packet_id:
        raise RouterError('packet record requires packet_id or result_envelope_path')
    return router._packet_paths(project_root, run_state, str(packet_id))['result_envelope']

def _load_packet_index(router: ModuleType, path: Path, *, label: str) -> dict[str, Any]:
    _bind_router(router)
    if not path.exists():
        raise RouterError(f'{label} packet index is missing: {path}')
    index = read_json(path)
    if not isinstance(index.get('packets'), list) or not index['packets']:
        raise RouterError(f'{label} packet index requires non-empty packets')
    return index

def _ensure_barrier_bundles_ready(router: ModuleType, project_root: Path, *, node_id: str | None=None) -> None:
    _bind_router(router)
    audit = packet_runtime.audit_barrier_bundles(project_root, node_id=node_id or None)
    if not audit.get('passed'):
        raise RouterError('barrier bundle audit failed before packet relay: ' + json.dumps(audit.get('blockers', []), sort_keys=True))

def _material_scan_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'material' / 'material_scan_packets.json'

def _research_packet_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'research' / 'research_packet.json'

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

def _relay_packet_records(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, controller_agent_id: str) -> list[str]:
    _bind_router(router)
    relayed_ids: list[str] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        if not envelope_path.exists():
            raise RouterError(f'packet envelope is missing: {envelope_path}')
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        audit = packet_runtime.validate_packet_ready_for_direct_relay(project_root, packet_envelope=envelope, envelope_path=envelope_path)
        if not audit.get('passed'):
            raise RouterError(f"packet envelope is not ready for direct relay: {audit.get('blockers')}")
        router._ensure_barrier_bundles_ready(project_root, node_id=str(envelope.get('node_id') or ''))
        packet_runtime.controller_relay_envelope(project_root, envelope=envelope, envelope_path=envelope_path, controller_agent_id=controller_agent_id, received_from_role=str(envelope.get('from_role') or 'project_manager'), relayed_to_role=str(envelope.get('to_role')))
        relayed_ids.append(str(envelope['packet_id']))
    return relayed_ids

def _active_holder_frontier_version(router: ModuleType, frontier: dict[str, Any]) -> int:
    _bind_router(router)
    return int(frontier.get('frontier_version') or frontier.get('route_version') or 0)

def _current_node_active_holder_lease_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], frontier: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    _bind_router(router)
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    planned: list[dict[str, Any]] = []
    allowed_writes: list[str] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_dir = envelope_path.parent
        item = {'packet_id': str(envelope.get('packet_id') or record.get('packet_id') or ''), 'holder_role': holder_role, 'target_agent_id': target_agent_id, 'route_version': route_version, 'frontier_version': frontier_version, 'packet_envelope_path': project_relative(project_root, envelope_path), 'active_holder_lease_path': project_relative(project_root, packet_dir / 'active_holder_lease.json'), 'active_holder_events_path': project_relative(project_root, packet_dir / 'active_holder_events.jsonl'), 'mode': 'lease_on_current_node_relay' if target_agent_id else 'fallback_controller_relay_no_live_agent_id'}
        planned.append(item)
        if target_agent_id:
            allowed_writes.extend([item['active_holder_lease_path'], item['active_holder_events_path']])
    return ({'mode': 'lease_on_current_node_relay', 'fallback_when_no_live_agent_id': True, 'controller_visibility': 'lease_metadata_only', 'route_version': route_version, 'frontier_version': frontier_version, 'packets': planned}, sorted(set(allowed_writes)))

def _issue_current_node_active_holder_leases(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    frontier = router._active_frontier(run_root)
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    issued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_id = str(envelope.get('packet_id') or record.get('packet_id') or '')
        if not target_agent_id:
            skipped.append({'packet_id': packet_id, 'holder_role': holder_role, 'reason': 'no_live_agent_id_available_fallback_to_controller_relay'})
            continue
        try:
            lease = packet_runtime.issue_active_holder_lease(project_root, packet_envelope=envelope, holder_role=holder_role, holder_agent_id=target_agent_id, route_version=route_version, frontier_version=frontier_version)
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f'current-node active-holder lease failed for {packet_id}: {exc}') from exc
        issued.append({'packet_id': packet_id, 'holder_role': holder_role, 'holder_agent_id': target_agent_id, 'lease_path': lease['lease_path'], 'lease_id': lease['lease_id']})
    summary = {'schema_version': 'flowpilot.current_node_active_holder_fast_lane.v1', 'mode': 'lease_on_current_node_relay', 'issued': issued, 'skipped': skipped, 'fallback_when_no_live_agent_id': True, 'recorded_at': utc_now()}
    run_state['current_node_active_holder_fast_lane'] = summary
    return summary

def _packet_active_holder_lease_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> tuple[dict[str, Any], list[str]]:
    _bind_router(router)
    try:
        frontier = router._active_frontier(run_root)
    except RouterError:
        frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    planned: list[dict[str, Any]] = []
    allowed_writes: list[str] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_dir = envelope_path.parent
        item = {'packet_id': str(envelope.get('packet_id') or record.get('packet_id') or ''), 'packet_family': packet_family, 'holder_role': holder_role, 'target_agent_id': target_agent_id, 'route_version': route_version, 'frontier_version': frontier_version, 'packet_envelope_path': project_relative(project_root, envelope_path), 'active_holder_lease_path': project_relative(project_root, packet_dir / 'active_holder_lease.json'), 'active_holder_events_path': project_relative(project_root, packet_dir / 'active_holder_events.jsonl'), 'mode': mode if target_agent_id else 'fallback_controller_relay_no_live_agent_id'}
        planned.append(item)
        if target_agent_id:
            allowed_writes.extend([item['active_holder_lease_path'], item['active_holder_events_path']])
    return ({'schema_version': 'flowpilot.packet_active_holder_fast_lane.v1', 'mode': mode, 'packet_family': packet_family, 'fallback_when_no_live_agent_id': True, 'controller_visibility': 'lease_metadata_only', 'route_version': route_version, 'frontier_version': frontier_version, 'packets': planned}, sorted(set(allowed_writes)))

def _issue_packet_active_holder_leases(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, packet_family: str, mode: str) -> dict[str, Any]:
    _bind_router(router)
    try:
        frontier = router._active_frontier(run_root)
    except RouterError:
        frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    route_version = int(frontier.get('route_version') or 0)
    frontier_version = router._active_holder_frontier_version(frontier)
    issued: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        holder_role = str(envelope.get('to_role') or record.get('to_role') or '')
        target_agent_id = _active_agent_id_for_role(run_root, holder_role)
        packet_id = str(envelope.get('packet_id') or record.get('packet_id') or '')
        if not target_agent_id:
            skipped.append({'packet_id': packet_id, 'packet_family': packet_family, 'holder_role': holder_role, 'reason': 'no_live_agent_id_available_fallback_to_controller_relay'})
            continue
        try:
            lease = packet_runtime.issue_active_holder_lease(project_root, packet_envelope=envelope, holder_role=holder_role, holder_agent_id=target_agent_id, route_version=route_version, frontier_version=frontier_version)
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f'{packet_family} active-holder lease failed for {packet_id}: {exc}') from exc
        issued.append({'packet_id': packet_id, 'packet_family': packet_family, 'holder_role': holder_role, 'holder_agent_id': target_agent_id, 'lease_path': lease['lease_path'], 'lease_id': lease['lease_id']})
    summary = {'schema_version': 'flowpilot.packet_active_holder_fast_lane.v1', 'mode': mode, 'packet_family': packet_family, 'issued': issued, 'skipped': skipped, 'fallback_when_no_live_agent_id': True, 'recorded_at': utc_now()}
    run_state.setdefault('packet_active_holder_fast_lanes', {})[packet_family] = summary
    return summary

def _relay_result_records(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, to_role: str, controller_agent_id: str) -> list[str]:
    _bind_router(router)
    relayed_ids: list[str] = []
    agent_role_map = router._agent_role_map_from_crew_ledger(project_root / str(run_state['run_root']))
    for record in records:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f'result envelope is missing: {result_path}')
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get('next_recipient') != to_role:
            raise RouterError(f'result envelope must route to {to_role}')
        if result.get('completed_by_role') == 'controller':
            raise RouterError('Controller-origin result is invalid')
        packet_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
        if not audit.get('passed'):
            raise RouterError(f"result envelope is not ready for reviewer relay: {audit.get('blockers')}")
        router._ensure_barrier_bundles_ready(project_root, node_id=str(result.get('node_id') or ''))
        packet_runtime.controller_relay_envelope(project_root, envelope=result, envelope_path=result_path, controller_agent_id=controller_agent_id, received_from_role=str(result.get('completed_by_role') or 'unknown'), relayed_to_role=to_role)
        relayed_ids.append(str(result['packet_id']))
    return relayed_ids

def _agent_role_map_from_crew_ledger(router: ModuleType, run_root: Path) -> dict[str, str] | None:
    _bind_router(router)
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    role_slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    agent_role_map: dict[str, str] = {}
    for slot in role_slots:
        if not isinstance(slot, dict):
            continue
        role_key = slot.get('role_key')
        agent_id = slot.get('agent_id')
        if isinstance(role_key, str) and isinstance(agent_id, str) and agent_id.strip():
            agent_role_map[agent_id.strip()] = role_key
    return agent_role_map or None

def _merge_agent_role_maps(router: ModuleType, primary: dict[str, str] | None, fallback: dict[str, str] | None) -> dict[str, str] | None:
    _bind_router(router)
    merged: dict[str, str] = {}
    if isinstance(fallback, dict):
        merged.update({str(key): str(value) for key, value in fallback.items()})
    if isinstance(primary, dict):
        merged.update({str(key): str(value) for key, value in primary.items()})
    return merged or None

def _validate_packet_bodies_opened_by_targets(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    _bind_router(router)
    for record in records:
        envelope_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        expected_role = envelope.get('to_role')
        if envelope.get('body_opened_by_role', {}).get('role') != expected_role:
            raise RouterError(f"packet {envelope.get('packet_id')} for role={expected_role} body was not opened by target role after Controller relay")
        try:
            packet_runtime.verify_packet_open_receipt(project_root, envelope, role=str(expected_role))
        except packet_runtime.PacketRuntimeError as exc:
            raise RouterError(f"packet {envelope.get('packet_id')} for role={expected_role} ledger open receipt is invalid: {exc}") from exc

def _validate_results_exist_for_packets(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, next_recipient: str) -> None:
    _bind_router(router)
    run_root = project_root / str(run_state['run_root'])
    agent_role_map = router._agent_role_map_from_crew_ledger(run_root)
    for record in records:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        if not result_path.exists():
            raise RouterError(f'result envelope is missing: {result_path}')
        result = packet_runtime.load_envelope(project_root, result_path)
        if result.get('next_recipient') != next_recipient:
            raise RouterError(f"result envelope for packet {result.get('packet_id')} must route to {next_recipient}")
        if result.get('completed_by_role') == 'controller':
            raise RouterError('Controller-origin result is invalid')
        packet_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        audit = packet_runtime.validate_result_ready_for_reviewer_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
        if not audit.get('passed'):
            raise RouterError(f"result envelope for packet {result.get('packet_id')} for role={audit.get('expected_role')} failed pre-relay audit: {audit.get('blockers')}")

def _validate_packet_group_for_reviewer(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]], *, audit_path: Path, agent_role_map: dict[str, str] | None=None) -> None:
    _bind_router(router)
    trusted_agent_role_map = router._agent_role_map_from_crew_ledger(project_root / str(run_state['run_root']))
    merged_agent_role_map = router._merge_agent_role_maps(trusted_agent_role_map, agent_role_map)
    audits: list[dict[str, Any]] = []
    blockers: list[str] = []
    evidence_paths: list[Path] = []
    for record in records:
        packet_path = router._packet_envelope_path_from_record(project_root, run_state, record)
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        evidence_paths.extend([packet_path, result_path])
        packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
        result_envelope = packet_runtime.load_envelope(project_root, result_path)
        audit = packet_runtime.validate_for_reviewer(project_root, packet_envelope=packet_envelope, result_envelope=result_envelope, agent_role_map=merged_agent_role_map)
        audits.append(audit)
        blockers.extend((str(blocker) for blocker in audit.get('blockers') or []))
    run_root = project_root / str(run_state['run_root'])
    proof_path = _router_owned_check_proof_path(audit_path)
    batch_ids = sorted({str(record.get('batch_id')) for record in records if isinstance(record, dict) and record.get('batch_id')})
    reviewed_packet_ids = [str(record.get('packet_id')) for record in records if isinstance(record, dict)]
    write_json(audit_path, {'schema_version': 'flowpilot.packet_group_reviewer_audit.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'router_replacement_scope': 'mechanical_only', 'self_attested_ai_claims_accepted_as_proof': False, 'router_owned_check_proof_path': project_relative(project_root, proof_path), 'batch_id': batch_ids[0] if len(batch_ids) == 1 else None, 'batch_ids': batch_ids, 'packet_count': len(records), 'reviewed_packet_ids': reviewed_packet_ids, 'overall_passed': not blockers, 'audits': audits, 'blockers': blockers, 'passed': not blockers, 'reviewed_at': utc_now()})
    _write_router_owned_check_proof(project_root, run_root, check_name='packet_group_reviewer_audit', audit_path=audit_path, source_kind='packet_runtime_hash', evidence_paths=evidence_paths)
    _validate_router_owned_check_proof(project_root, run_root, check_name='packet_group_reviewer_audit', audit_path=audit_path)
    if blockers:
        raise RouterError(f'packet group reviewer audit failed: {blockers}')

def _write_pm_research_absorption(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    reviewer_report_path = run_root / 'research' / 'research_reviewer_report.json'
    audit_path = run_root / 'research' / 'research_packet_review_audit.json'
    if not reviewer_report_path.exists():
        raise RouterError('PM can absorb research only after reviewer research report exists')
    if not audit_path.exists():
        raise RouterError('PM can absorb research only after packet-group reviewer runtime audit exists')
    audit = read_json(audit_path)
    if audit.get('passed') is not True:
        raise RouterError('PM can absorb research only after packet-group reviewer runtime audit passed')
    packet_ledger_path = run_root / 'packet_ledger.json'
    if not packet_ledger_path.exists():
        raise RouterError('PM research absorption requires packet_ledger.json')
    absorption_path = run_root / 'research' / 'pm_research_absorption.json'
    write_json(absorption_path, {'schema_version': 'flowpilot.pm_research_absorption.v1', 'run_id': run_state['run_id'], 'absorbed_by_role': 'project_manager', 'research_reviewer_report_path': project_relative(project_root, reviewer_report_path), 'research_reviewer_report_hash': hashlib.sha256(reviewer_report_path.read_bytes()).hexdigest(), 'packet_group_reviewer_audit_path': project_relative(project_root, audit_path), 'packet_group_reviewer_audit_hash': hashlib.sha256(audit_path.read_bytes()).hexdigest(), 'packet_ledger_path': project_relative(project_root, packet_ledger_path), 'packet_ledger_hash': hashlib.sha256(packet_ledger_path.read_bytes()).hexdigest(), 'packet_group_audit_passed': True, 'absorbed_at': utc_now()})

def _validate_current_node_packet_envelope(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    active_bindings = router._active_child_skill_bindings_from_plan(plan)
    active_binding_source_paths = router._active_child_skill_source_paths(active_bindings)
    active_node = frontier.get('active_node_id')
    if active_node and envelope.get('node_id') != active_node:
        raise RouterError(f"packet node_id {envelope.get('node_id')!r} does not match frontier active_node_id {active_node!r}")
    route_version = int(frontier.get('route_version') or 0)
    packet_route_version = envelope.get('metadata', {}).get('route_version')
    if packet_route_version is None:
        raise RouterError('current-node packet metadata.route_version is required')
    if int(packet_route_version) != route_version:
        raise RouterError('current-node packet route_version must match active frontier')
    if envelope.get('from_role') != 'project_manager':
        raise RouterError('current-node packet must be issued by project_manager')
    if envelope.get('to_role') == 'controller':
        raise RouterError('current-node packet cannot assign product work to Controller')
    if active_bindings and envelope.get('to_role') in {'worker_a', 'worker_b'}:
        metadata = envelope.get('metadata') if isinstance(envelope.get('metadata'), dict) else {}
        projected_ids = set(router._metadata_binding_ids(metadata, 'active_child_skill_bindings', 'child_skill_binding_projection'))
        expected_ids = {str(binding['binding_id']) for binding in active_bindings}
        if not projected_ids:
            raise RouterError('current-node worker packet requires active child skill bindings in metadata')
        missing_ids = sorted(expected_ids - projected_ids)
        if missing_ids:
            raise RouterError('current-node worker packet metadata is missing active child skill bindings: ' + ', '.join(missing_ids))
        if metadata.get('child_skill_use_instruction_written') is not True and metadata.get('active_child_skill_use_instruction_written') is not True:
            raise RouterError('current-node worker packet requires direct child-skill use instruction')
        allowed_paths = set(router._metadata_string_list(metadata, 'active_child_skill_source_paths_allowed', 'allowed_child_skill_source_paths'))
        missing_paths = sorted(set(active_binding_source_paths) - allowed_paths)
        if missing_paths:
            raise RouterError('current-node worker packet metadata is missing active child skill source paths: ' + ', '.join(missing_paths))
    if envelope.get('body_visibility') != packet_runtime.SEALED_BODY_VISIBILITY:
        raise RouterError('current-node packet body must be sealed to the target role')
    return {'schema_version': 'flowpilot.current_node_write_grant.v1', 'run_id': run_state['run_id'], 'route_id': str(frontier['active_route_id']), 'route_version': route_version, 'node_id': str(frontier['active_node_id']), 'packet_id': str(envelope['packet_id']), 'granted_to_role': str(envelope['to_role']), 'granted_by_role': 'project_manager', 'grant_scope': 'current_node_packet_body_and_result_only', 'packet_envelope_path': project_relative(project_root, envelope_path), 'packet_envelope_hash': hashlib.sha256(envelope_path.read_bytes()).hexdigest(), 'packet_body_path': str(envelope.get('body_path') or ''), 'packet_body_hash': str(envelope.get('body_hash') or ''), 'active_child_skill_bindings_declared': bool(active_bindings), 'active_child_skill_source_paths': active_binding_source_paths, 'controller_may_read_packet_body': False, 'controller_may_write_project_artifacts': False, 'issued_at': utc_now()}

def _validate_current_node_packet_event(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    if not run_state['flags'].get('node_acceptance_plan_reviewer_passed'):
        raise RouterError('current-node packet requires reviewer-passed node acceptance plan')
    frontier = router._active_frontier(run_root)
    plan_path = _active_node_acceptance_plan_path(run_root, frontier)
    if not plan_path.exists():
        raise RouterError('current-node packet requires node_acceptance_plan.json')
    plan = read_json(plan_path)
    _require_clean_self_interrogation(project_root, run_root, gate_name='current-node packet registration', scopes=('node_entry',), node_id=str(frontier['active_node_id']), route_version=int(frontier.get('route_version') or 0))
    active_node_definition = router._active_node_definition(run_root, frontier)
    if router._node_child_ids(active_node_definition):
        raise RouterError('current-node worker packet requires a leaf node; parent/module nodes must enter child subtree or parent backward replay')
    if router._node_kind(active_node_definition) not in {'leaf', 'repair'}:
        raise RouterError('current-node worker packet requires node_kind=leaf or repair')
    if not router._is_leaf_readiness_passed(active_node_definition, plan):
        raise RouterError('current-node worker packet requires leaf_readiness_gate.status=pass')
    raw_packets = payload.get('packets')
    packet_payloads = raw_packets if isinstance(raw_packets, list) and raw_packets else [payload]
    records: list[dict[str, Any]] = []
    grants: list[dict[str, Any]] = []
    batch_id = str(payload.get('batch_id') or f"{frontier['active_node_id']}-batch-001")
    for packet_payload in packet_payloads:
        if not isinstance(packet_payload, dict):
            raise RouterError('current-node batch packet specs must be objects')
        envelope_path = router._packet_envelope_path(project_root, run_state, packet_payload)
        if not envelope_path.exists():
            raise RouterError(f'current-node packet envelope is missing: {envelope_path}')
        envelope = packet_runtime.load_envelope(project_root, envelope_path)
        grants.append(router._validate_current_node_packet_envelope(project_root, run_root, run_state, envelope, envelope_path, frontier, plan))
        records.append(router._packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=str(envelope.get('packet_type') or 'work_packet')))
    router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='current_node', phase='current_node_loop', records=records, node_id=str(frontier['active_node_id']), join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_before_node_completion_review', pm_absorption_required=True)
    write_json(_active_node_packet_index_path(run_root, frontier), {'schema_version': 'flowpilot.current_node_packet_batch.v1', 'run_id': run_state['run_id'], 'batch_id': batch_id, 'route_id': str(frontier['active_route_id']), 'route_version': int(frontier.get('route_version') or 0), 'node_id': str(frontier['active_node_id']), 'controller_may_read_packet_body': False, 'packets': records, 'written_at': utc_now()})
    grant_path = _active_node_write_grant_path(run_root, frontier)
    write_json(grant_path, {'schema_version': 'flowpilot.current_node_write_grants.v1', 'run_id': run_state['run_id'], 'route_id': str(frontier['active_route_id']), 'route_version': int(frontier.get('route_version') or 0), 'node_id': str(frontier['active_node_id']), 'batch_id': batch_id, 'packet_id': str(grants[0]['packet_id']), 'granted_to_role': str(grants[0]['granted_to_role']), 'granted_by_role': 'project_manager', 'grant_scope': 'current_node_packet_body_and_result_only', 'packet_envelope_path': str(grants[0]['packet_envelope_path']), 'packet_envelope_hash': str(grants[0]['packet_envelope_hash']), 'packet_body_path': str(grants[0]['packet_body_path']), 'packet_body_hash': str(grants[0]['packet_body_hash']), 'active_child_skill_bindings_declared': bool(grants[0]['active_child_skill_bindings_declared']), 'active_child_skill_source_paths': grants[0]['active_child_skill_source_paths'], 'grants': grants, 'controller_may_read_packet_body': False, 'controller_may_write_project_artifacts': False, 'issued_at': utc_now()})
    run_state['flags']['current_node_write_grant_issued'] = True
    run_state['current_node_packet_id'] = records[0]['packet_id']
    run_state['current_node_batch_id'] = batch_id

def _validate_current_node_result_event(router: ModuleType, project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    run_root = project_root / str(run_state['run_root'])
    frontier = router._active_frontier(run_root)
    grant_path = _active_node_write_grant_path(run_root, frontier)
    if not run_state['flags'].get('current_node_write_grant_issued') or not grant_path.exists():
        raise RouterError('current-node worker result requires a current-node write grant')
    grant = read_json(grant_path)
    result_path = router._result_envelope_path(project_root, run_state, payload)
    if not result_path.exists():
        raise RouterError(f'current-node result envelope is missing: {result_path}')
    result = packet_runtime.load_envelope(project_root, result_path)
    grant_records = grant.get('grants') if isinstance(grant.get('grants'), list) else [grant]
    grant_by_packet_id = {str(item.get('packet_id')): item for item in grant_records if isinstance(item, dict)}
    result_packet_id = str(result.get('packet_id') or '')
    expected_grant = grant_by_packet_id.get(result_packet_id)
    if expected_grant is None:
        raise RouterError('current-node result packet_id does not match current-node write grant')
    if str(result.get('completed_by_role') or '') != str(expected_grant.get('granted_to_role') or ''):
        raise RouterError('wrong role: current-node result completed_by_role does not match current-node write grant')
    if result.get('next_recipient') != 'project_manager':
        raise RouterError('current-node worker result must route to project_manager')
    if result.get('completed_by_role') == 'controller':
        raise RouterError('Controller-origin current-node result is invalid')
    packet_record = router._packet_ledger_record_by_id(run_root, result_packet_id)
    if isinstance(packet_record, dict) and packet_record.get('active_holder_lease_issued'):
        if packet_record.get('fast_lane_result_mechanics_passed') is not True:
            raise RouterError('current-node result requires active-holder mechanics pass before result event')
        if packet_record.get('fast_lane_controller_notice_written') is not True:
            raise RouterError('current-node result requires Router Controller next-action notice before result event')
        notice = packet_record.get('router_next_action_notice')
        if not isinstance(notice, dict):
            raise RouterError('current-node active-holder result requires router_next_action_notice')
        if notice.get('next_action') != 'deliver_result_to_pm_for_disposition':
            raise RouterError('current-node active-holder result notice must route Controller to PM disposition')
        if notice.get('next_recipient') != 'project_manager':
            raise RouterError('current-node active-holder result notice must name project_manager as next_recipient')
    packet_path = resolve_project_path(project_root, str(expected_grant.get('packet_envelope_path') or ''))
    packet_envelope = packet_runtime.load_envelope(project_root, packet_path)
    agent_role_map = router._agent_role_map_from_crew_ledger(run_root)
    audit = packet_runtime.validate_result_ready_for_reviewer_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
    if not audit.get('passed'):
        raise RouterError(f"current-node result failed pre-relay packet runtime audit: {audit.get('blockers')}")
    router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'current_node')

def _validate_current_node_reviewer_pass(router: ModuleType, project_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('current-node reviewer pass must be reviewed_by_role=human_like_reviewer')
    if payload.get('passed') is not True:
        raise RouterError('current-node reviewer pass must explicitly pass')
    run_root = project_root / str(run_state['run_root'])
    raw_agent_map = payload.get('agent_role_map')
    payload_agent_role_map = raw_agent_map if isinstance(raw_agent_map, dict) else None
    frontier = router._active_frontier(run_root)
    audit_path = _active_node_root(run_root, frontier) / 'reviews' / 'current_node_packet_runtime_audit.json'
    records = router._current_node_packet_records(project_root, run_state)
    router._validate_packet_group_for_reviewer(project_root, run_state, records, audit_path=audit_path, agent_role_map=payload_agent_role_map)
    router._mark_parallel_batch_reviewed(run_root, 'current_node', passed=True, reviewed_packet_ids=[str(record.get('packet_id')) for record in records])

def _next_material_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if flags.get('pm_material_packets_issued') and (not flags.get('material_scan_packets_relayed')):
        index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, index['packets'], packet_family='material_scan', mode='lease_on_material_scan_relay')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_material_scan_packets', actor='controller', label='material_scan_packets_relayed_after_router_direct_preflight_with_ledger_check', summary='Check the packet ledger and directly relay material scan packet envelopes to workers without opening bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role='worker_a,worker_b', extra={'postcondition': 'material_scan_packets_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'active_holder_fast_lane': active_holder_plan})
        return make_action(action_type='relay_material_scan_packets', actor='controller', label='material_scan_packets_relayed_after_router_direct_preflight', summary='Directly relay material scan packet envelopes to workers without opening bodies.', allowed_reads=[project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role='worker_a,worker_b', extra={'postcondition': 'material_scan_packets_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan})
    if flags.get('material_scan_packets_relayed') and (not flags.get('worker_scan_results_returned')):
        summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'material_scan')
        if summary.get('partial_results_returned'):
            missing_roles = [str(role) for role in summary.get('missing_roles') or [] if role]
            allowed_event = 'worker_scan_results_returned' if flags.get('worker_packets_delivered') else 'worker_scan_packet_bodies_delivered_after_dispatch'
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_material_scan_batch_results', summary='Controller has some material scan result envelopes and must wait only for the missing batch member(s).', allowed_external_events=[allowed_event], to_role=','.join(missing_roles) if missing_roles else 'worker_a,worker_b', allowed_reads_extra=[project_relative(project_root, router._parallel_packet_batch_path(run_root, str(summary.get('batch_id'))))] if summary.get('batch_id') else None, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'material_scan_partial_batch_result', 'required_fields': ['packet_id', 'result_envelope_path'], 'batch_id': summary.get('batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'packet_count': summary.get('packet_count'), 'results_returned': summary.get('results_returned'), 'missing_roles': missing_roles, 'controller_visibility': 'metadata_only'}, producer_roles_override=missing_roles)
    if flags.get('worker_scan_results_returned') and (not flags.get('material_scan_results_relayed_to_pm')):
        index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_material_scan_results_to_pm', actor='controller', label='material_scan_results_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay material scan result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'material_scan_results_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']]})
        return make_action(action_type='relay_material_scan_results_to_pm', actor='controller', label='material_scan_results_relayed_to_pm', summary='Relay material scan result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'material_scan_results_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False})
    if flags.get('material_scan_results_relayed_to_pm') and (not flags.get('material_scan_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_material_scan_result_disposition', summary='Controller relayed material scan results to PM and must wait for PM to record a result disposition before any reviewer sufficiency gate.', allowed_external_events=['pm_records_material_scan_result_disposition'], to_role='project_manager', payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'pm_material_scan_result_disposition', 'required_fields': ['decided_by_role', 'decision'], 'allowed_values': {'decided_by_role': ['project_manager'], 'decision': sorted(PM_PACKAGE_RESULT_DECISIONS)}, 'result_body_open_required_by_role': 'project_manager'})
    return None

def _next_research_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if flags.get('research_capability_decision_recorded') and (not flags.get('research_packet_relayed')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, index['packets'], packet_family='research', mode='lease_on_research_packet_relay')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker_with_ledger_check', summary='Check the packet ledger and relay research packet envelope to worker without opening the body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker_a') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'active_holder_fast_lane': active_holder_plan})
        return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker', summary='Relay research batch packet envelopes without opening their bodies.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker_a') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan})
    if flags.get('research_packet_relayed') and flags.get('worker_research_report_card_delivered') and (not flags.get('worker_research_report_returned')):
        summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'research')
        if summary.get('partial_results_returned'):
            missing_roles = [str(role) for role in summary.get('missing_roles') or [] if role]
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_research_batch_results', summary='Controller has some research result envelopes and must wait only for the missing batch member(s).', allowed_external_events=['worker_research_report_returned'], to_role=','.join(missing_roles) if missing_roles else 'worker_a,worker_b', allowed_reads_extra=[project_relative(project_root, router._parallel_packet_batch_path(run_root, str(summary.get('batch_id'))))] if summary.get('batch_id') else None, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'research_partial_batch_result', 'required_fields': ['packet_id', 'result_envelope_path', 'answers_decision_question'], 'batch_id': summary.get('batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'packet_count': summary.get('packet_count'), 'results_returned': summary.get('results_returned'), 'missing_roles': missing_roles, 'controller_visibility': 'metadata_only'}, producer_roles_override=missing_roles)
    if flags.get('worker_research_report_returned') and (not flags.get('research_result_relayed_to_pm')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']]})
        return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm', summary='Relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False})
    if flags.get('research_result_relayed_to_pm') and (not flags.get('research_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_research_result_disposition', summary='Controller relayed research results to PM and must wait for PM disposition before any reviewer direct-source gate.', allowed_external_events=['pm_records_research_result_disposition'], to_role='project_manager', payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'pm_research_result_disposition', 'required_fields': ['decided_by_role', 'decision'], 'allowed_values': {'decided_by_role': ['project_manager'], 'decision': sorted(PM_PACKAGE_RESULT_DECISIONS)}, 'result_body_open_required_by_role': 'project_manager'})
    return None

def _next_current_node_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('current_node_packet_registered'):
        return None
    if not flags.get('current_node_packet_relayed'):
        records = router._current_node_packet_records(project_root, run_state)
        frontier = router._active_frontier(run_root)
        grant_path = _active_node_write_grant_path(run_root, frontier)
        grant_extra: dict[str, Any] = {}
        relay_allowed_reads = [project_relative(project_root, router._packet_envelope_path_from_record(project_root, run_state, record)) for record in records]
        if grant_path.exists():
            relay_allowed_reads.append(project_relative(project_root, grant_path))
            grant_extra = {'current_node_write_grant_path': project_relative(project_root, grant_path), 'current_node_write_grant_hash': hashlib.sha256(grant_path.read_bytes()).hexdigest()}
        active_holder_plan, active_holder_allowed_writes = router._current_node_active_holder_lease_plan(project_root, run_root, run_state, records, frontier)
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_current_node_packet', actor='controller', label='current_node_packet_relayed_after_router_direct_preflight_with_ledger_check', summary='Check the packet ledger and relay every current-node batch packet without opening packet bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), *relay_allowed_reads], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role')) for record in records})), extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'active_holder_fast_lane': active_holder_plan, **grant_extra})
        return make_action(action_type='relay_current_node_packet', actor='controller', label='current_node_packet_relayed_after_router_direct_preflight', summary='Directly relay current-node batch packet envelopes without opening their bodies.', allowed_reads=relay_allowed_reads, allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role')) for record in records})), extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan, **grant_extra})
    if flags.get('current_node_worker_result_returned') and (not flags.get('current_node_result_relayed_to_pm')):
        if not router._current_node_results_complete(project_root, run_state):
            missing_roles = router._current_node_missing_result_roles(project_root, run_state)
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_current_node_batch_results', summary='Controller must wait for every current-node batch result before relaying the batch to PM.', allowed_external_events=['worker_current_node_result_returned'], to_role=','.join(missing_roles) if missing_roles else 'worker_a,worker_b', payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'current_node_batch_result_envelope', 'required_fields': ['packet_id', 'result_envelope_path'], 'batch_join_policy': 'all_results_before_pm_absorption'}, producer_roles_override=missing_roles)
        records = router._current_node_packet_records(project_root, run_state)
        result_paths = [router._result_envelope_path_from_packet_record(project_root, run_state, record) for record in records]
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_current_node_result_to_pm', actor='controller', label='current_node_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay the current-node worker batch result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), *[project_relative(project_root, path) for path in result_paths]], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True})
        return make_action(action_type='relay_current_node_result_to_pm', actor='controller', label='current_node_result_relayed_to_pm', summary='Relay current-node batch result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, path) for path in result_paths], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False})
    if flags.get('current_node_result_relayed_to_pm') and (not flags.get('current_node_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_current_node_result_disposition', summary='Controller relayed current-node worker results to PM and must wait for PM disposition before any reviewer node-completion gate.', allowed_external_events=['pm_records_current_node_result_disposition'], to_role='project_manager', payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'pm_current_node_result_disposition', 'required_fields': ['decided_by_role', 'decision'], 'allowed_values': {'decided_by_role': ['project_manager'], 'decision': sorted(PM_PACKAGE_RESULT_DECISIONS)}, 'result_body_open_required_by_role': 'project_manager'})
    return None

def _controller_status_packet_path_from_packet_envelope(router: ModuleType, packet_envelope_path: object) -> str | None:
    _bind_router(router)
    raw = str(packet_envelope_path or '').replace('\\', '/')
    suffix = '/packet_envelope.json'
    if not raw.endswith(suffix):
        return None
    return raw[:-len('packet_envelope.json')] + 'controller_status_packet.json'

def _role_output_status_packet_path_for_wait(router: ModuleType, project_root: Path, run_root: Path, *, to_role: str, allowed_events: list[str], payload_contract: dict[str, Any] | None) -> str | None:
    _bind_router(router)
    if not isinstance(payload_contract, dict):
        return None
    if payload_contract.get('required_object') != 'role_output_body':
        return None
    if not to_role or ',' in to_role or to_role == 'host':
        return None
    event_name = '_or_'.join(allowed_events) if allowed_events else str(payload_contract.get('name') or '')
    path = role_output_runtime.default_role_output_status_packet_path(run_root, role=to_role, output_type=str(payload_contract.get('name') or 'role_output'), event_name=event_name)
    return project_relative(project_root, path)

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

def _try_reconcile_material_scan_body_delivery(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if flags.get('worker_packets_delivered') or not flags.get('material_scan_packets_relayed'):
        return False
    try:
        material_index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        router._validate_packet_bodies_opened_by_targets(project_root, run_state, material_index['packets'])
    except (RouterError, packet_runtime.PacketRuntimeError, OSError, json.JSONDecodeError):
        return False
    return _record_router_reconciled_external_event(project_root, run_root, run_state, 'worker_scan_packet_bodies_delivered_after_dispatch', {'packet_ids': [record.get('packet_id') for record in material_index['packets'] if isinstance(record, dict)], 'reconciled_from_packet_receipts': True})

def _try_reconcile_material_scan_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if flags.get('worker_scan_results_returned') or not flags.get('material_scan_packets_relayed'):
        return False
    material_index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
    summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'material_scan')
    if not summary.get('all_results_returned'):
        return bool(summary.get('changed'))
    router._try_reconcile_material_scan_body_delivery(project_root, run_root, run_state)
    if not run_state['flags'].get('worker_packets_delivered'):
        return bool(summary.get('changed'))
    try:
        router._validate_results_exist_for_packets(project_root, run_state, material_index['packets'], next_recipient='project_manager')
    except (RouterError, packet_runtime.PacketRuntimeError):
        return bool(summary.get('changed'))
    payload = {'packet_ids': [record.get('packet_id') for record in material_index['packets'] if isinstance(record, dict)], 'batch_id': summary.get('batch_id'), 'results_returned': summary.get('results_returned'), 'reconciled_from_result_envelopes': True}
    return _record_router_reconciled_external_event(project_root, run_root, run_state, 'worker_scan_results_returned', payload) or bool(summary.get('changed'))

def _try_reconcile_current_node_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if flags.get('current_node_worker_result_returned') or not flags.get('current_node_packet_relayed'):
        return False
    changed = False
    for record in router._current_node_packet_records(project_root, run_state):
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if not result_exists:
            continue
        payload = {'packet_id': str(record.get('packet_id') or ''), 'result_envelope_path': project_relative(project_root, result_path), 'result_envelope_hash': packet_runtime.sha256_file(result_path), 'reconciled_from_result_envelope': True}
        try:
            router._validate_current_node_result_event(project_root, run_state, payload)
        except (RouterError, packet_runtime.PacketRuntimeError):
            continue
        changed = _record_router_reconciled_external_event(project_root, run_root, run_state, 'worker_current_node_result_returned', payload) or changed
    if changed:
        router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'current_node')
    return changed

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


_LOCAL_NAMES = set(globals())
