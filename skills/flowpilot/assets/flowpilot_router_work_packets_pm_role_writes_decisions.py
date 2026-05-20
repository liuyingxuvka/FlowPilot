"""PM role-work decision and package disposition writers."""

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


def _write_pm_formal_gate_package(
    router: ModuleType,
    project_root: Path,
    output_path: Path,
    *,
    run_state: dict[str, Any],
    batch: dict[str, Any],
    records: list[dict[str, Any]],
    batch_kind: str,
    package_label: str,
    gate_kind: str,
    decision: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    package_path = output_path.with_name(f"pm_{router._safe_packet_id_component(package_label)}_formal_gate_package.json")
    result_envelopes: list[dict[str, Any]] = []
    for record in records:
        result_rel = str(record.get('result_envelope_path') or '')
        result_hash = None
        result_envelope: dict[str, Any] = {}
        if result_rel:
            result_path = resolve_project_path(project_root, result_rel)
            if result_path.exists():
                result_hash = packet_runtime.sha256_file(result_path)
                result_envelope = packet_runtime.load_envelope(project_root, result_rel)
        packet_rel = str(record.get('packet_envelope_path') or result_envelope.get('source_packet_envelope_path') or '')
        packet_hash = None
        packet_envelope: dict[str, Any] = {}
        if packet_rel:
            packet_path = resolve_project_path(project_root, packet_rel)
            if packet_path.exists():
                packet_hash = packet_runtime.sha256_file(packet_path)
                packet_envelope = packet_runtime.load_envelope(project_root, packet_rel)
        source_output_contract_id = str(
            result_envelope.get('source_output_contract_id')
            or result_envelope.get('output_contract_id')
            or packet_envelope.get('output_contract_id')
            or packet_runtime.output_contract_id(
                packet_envelope.get('output_contract') if isinstance(packet_envelope.get('output_contract'), dict) else None
            )
            or ''
        )
        result_entry = {
            'packet_id': str(record.get('packet_id') or ''),
            'result_envelope_path': result_rel,
            'result_envelope_hash': result_hash,
        }
        if packet_rel:
            result_entry['packet_envelope_path'] = packet_rel
            result_entry['packet_envelope_hash'] = packet_hash
        if source_output_contract_id:
            result_entry['source_output_contract_id'] = source_output_contract_id
        result_envelopes.append(result_entry)
    package = {
        'schema_version': 'flowpilot.pm_formal_gate_package.v1',
        'run_id': run_state['run_id'],
        'batch_id': batch.get('batch_id'),
        'batch_kind': batch_kind,
        'package_label': package_label,
        'gate_kind': gate_kind,
        'decision': decision,
        'reviewer_readable': True,
        'reviewer_review_scope': 'pm_formal_gate_package_only',
        'reviewer_receives_raw_worker_result': False,
        'raw_worker_result_bodies_included': False,
        'packet_ids': [str(record.get('packet_id')) for record in records],
        'result_envelopes': result_envelopes,
        'source_pm_disposition_path': project_relative(project_root, output_path),
        'content_boundary': {
            'includes_pm_disposition_summary': True,
            'includes_result_envelope_paths_and_hashes': True,
            'excludes_worker_result_bodies': True,
            'sealed_body_boundary_preserved': True,
        },
        'decision_reason': payload.get('decision_reason') or payload.get('reason') or '',
        'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [],
        'created_at': utc_now(),
    }
    write_json(package_path, package)
    return {
        'formal_gate_package_schema_version': package['schema_version'],
        'formal_gate_package_path': project_relative(project_root, package_path),
        'formal_gate_package_hash': packet_runtime.sha256_file(package_path),
        'formal_gate_package_reviewer_readable': True,
        'formal_gate_package_content_boundary': package['content_boundary'],
    }


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
    formal_package = {}
    if decision == 'absorbed':
        formal_package = _write_pm_formal_gate_package(router, project_root, output_path, run_state=run_state, batch=batch, records=records, batch_kind=batch_kind, package_label=package_label, gate_kind=gate_kind, decision=decision, payload=payload)
    release_satisfied = bool(
        decision == 'absorbed'
        and formal_package.get('formal_gate_package_path')
        and formal_package.get('formal_gate_package_hash')
    )
    disposition = {'schema_version': 'flowpilot.pm_package_result_disposition.v1', 'run_id': run_state['run_id'], 'batch_id': batch.get('batch_id'), 'batch_kind': batch_kind, 'package_label': package_label, 'gate_kind': gate_kind, 'decided_by_role': 'project_manager', 'decision': decision, 'decision_reason': payload.get('decision_reason') or payload.get('reason') or '', 'packet_ids': [str(record.get('packet_id')) for record in records], 'result_envelope_paths': [str(record.get('result_envelope_path')) for record in records], 'formal_gate_package_released': release_satisfied, 'pm_reviewer_release_evidence': {'schema_version': 'flowpilot.pm_reviewer_release_evidence.v1', 'release_kind': 'absorbed_pm_package_result_disposition' if release_satisfied else 'none', 'release_satisfied': release_satisfied, 'formal_gate_package_required': decision == 'absorbed', 'formal_gate_package_path': formal_package.get('formal_gate_package_path'), 'formal_gate_package_hash': formal_package.get('formal_gate_package_hash'), 'reviewer_receives_raw_worker_result': False, 'reviewer_review_scope': 'pm_formal_gate_package_only' if release_satisfied else 'none'}, 'reviewer_receives_raw_worker_result': False, 'reviewer_review_scope': 'pm_formal_gate_package_only' if release_satisfied else 'none', 'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [], 'recorded_at': utc_now(), **formal_package, **_role_output_envelope_record(payload)}
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
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
    '_write_pm_formal_gate_package',
    '_write_pm_package_result_disposition',
)

_LOCAL_NAMES = set(globals())
