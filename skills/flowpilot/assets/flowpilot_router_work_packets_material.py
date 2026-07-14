"""Ordinary research work-packet helpers retained by the FlowPilot router.

The legacy filename remains to avoid an unrelated module rename. Dedicated
material-scan, material-sufficiency, and material-understanding writers are not
part of the current contract; evidence work uses this ordinary research path.
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
import flowpilot_material_artifact_map as material_artifact_map
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

def _write_research_package(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    decision_question = payload.get('decision_question')
    if not decision_question:
        raise RouterError('research package requires decision_question')
    packet_specs = payload.get('packets')
    if packet_specs is not None and (not isinstance(packet_specs, list) or not packet_specs):
        raise RouterError('research package packets must be a non-empty list when provided')
    package = {'schema_version': 'flowpilot.research_package.v1', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'decision_question': decision_question, 'allowed_source_types': payload.get('allowed_source_types') or [], 'host_capability_decision': payload.get('host_capability_decision') or 'local_sources_only', 'worker_owner': payload.get('worker_owner') or 'worker', 'batch_id': payload.get('batch_id') or 'research-batch-001', 'packets': packet_specs or [], 'reviewer_direct_check_required': True, 'stop_conditions': payload.get('stop_conditions') or [], 'written_at': utc_now(), **_role_output_envelope_record(payload)}
    write_json(run_root / 'research' / 'research_package.json', package)
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)

def _write_research_capability_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    package_path = run_root / 'research' / 'research_package.json'
    if not package_path.exists():
        raise RouterError('research capability decision requires research_package.json')
    if payload.get('explicit_user_approval_required') is True and payload.get('explicit_user_approval_recorded') is not True:
        raise RouterError('research capability decision requires recorded user approval for gated sources')
    package = read_json(package_path)
    worker_owner = str(package.get('worker_owner') or 'worker')
    if worker_owner != 'worker':
        raise RouterError('research worker owner must be the requested worker responsibility')
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
        if 'to_role' not in spec and 'recipient_role' in spec:
            raise RouterError('research packet spec requires to_role; recipient_role is not a current alias')
        to_role = str(spec.get('to_role') or worker_owner)
        if to_role not in {'worker', 'flowguard_operator', 'flowguard_operator'}:
            raise RouterError('research packets may target workers or FlowGuard operators only')
        packet_type = 'flowguard_operator_request' if to_role in {'flowguard_operator', 'flowguard_operator'} else 'research'
        packet_id = str(spec.get('packet_id') or f'research-packet-{index:03d}')
        body_text = spec.get('body_text')
        if body_text is None:
            body_text = json.dumps({**research_body_payload, 'batch_id': batch_id, 'packet_focus': spec.get('packet_focus') or spec.get('request_kind') or 'research'}, indent=2, sort_keys=True)
        if not isinstance(body_text, str) or not body_text.strip():
            raise RouterError('research packet requires non-empty body_text')
        output_contract = spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None
        if output_contract is None and packet_type == 'flowguard_operator_request':
            output_contract = router._pm_role_work_output_contract(run_root, contract_id=str(spec.get('output_contract_id') or 'flowpilot.output_contract.flowguard_operator_model_report.v1'), to_role=to_role, packet_type=packet_type, node_id='research')
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id='research', body_text=body_text, is_current_node=False, packet_type=packet_type, metadata={'stage': 'research', 'source': 'research_capability_decision_recorded', 'batch_id': batch_id, 'research_package_path': project_relative(project_root, package_path), **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=output_contract)
        records.append(router._packet_record_from_envelope(project_root, run_state, envelope=envelope, packet_type=packet_type))
    router._write_parallel_packet_batch(project_root, run_root, run_state, batch_id=batch_id, batch_kind='research', phase='research', records=records, node_id='research', join_policy='all_results_before_pm_absorption', review_policy='pm_absorbs_batch_before_research_direct_source_review', pm_absorption_required=True)
    write_json(run_root / 'research' / 'research_capability_decision.json', {'schema_version': 'flowpilot.research_capability_decision.v1', 'run_id': run_state['run_id'], 'recorded_by_role': 'project_manager', 'research_package_path': project_relative(project_root, package_path), 'decision_question': package.get('decision_question'), 'allowed_source_types': allowed_source_types, 'allowed_sources': allowed_sources, 'host_capability_decision': package.get('host_capability_decision'), 'worker_owner': worker_owner, 'batch_id': batch_id, 'reviewer_direct_check_required': bool(package.get('reviewer_direct_check_required')), 'stop_conditions': stop_conditions, 'explicit_user_approval_required': bool(payload.get('explicit_user_approval_required')), 'explicit_user_approval_recorded': bool(payload.get('explicit_user_approval_recorded')), 'worker_packet_id': records[0]['packet_id'], 'packet_ids': [record['packet_id'] for record in records], 'recorded_at': utc_now(), **_role_output_envelope_record(payload)})
    write_json(router._research_packet_index_path(run_root), {'schema_version': 'flowpilot.research_packet.v1', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'batch_id': batch_id, 'packet_id': records[0]['packet_id'], 'worker_owner': worker_owner, 'controller_may_read_packet_body': False, 'packet_envelope_path': records[0]['packet_envelope_path'], 'packet_body_path': records[0].get('packet_body_path'), 'packet_body_hash': records[0].get('packet_body_hash'), 'body_path': records[0].get('packet_body_path'), 'body_hash': records[0].get('packet_body_hash'), 'result_envelope_path': records[0]['result_envelope_path'], 'packets': records, 'written_at': utc_now()})
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)

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
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)

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
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)

__all__ = (
    '_write_research_package',
    '_write_research_capability_decision',
    '_write_worker_research_report',
    '_write_pm_research_absorption',
)

_LOCAL_NAMES = set(globals())
