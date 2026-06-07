"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints stay aligned.
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
import flowpilot_material_artifact_map as material_artifact_map
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

def _commit_material_scan_repair_generation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction_id: str, packet_generation_id: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    existing_index = read_json_if_exists(router._material_scan_index_path(run_root))
    previous_batch = router._active_parallel_packet_batch(run_root, 'material_scan')
    previous_batch_id = str(previous_batch.get('batch_id') or '') if isinstance(previous_batch, dict) else ''
    superseded_packets = []
    for record in existing_index.get('packets', []) if isinstance(existing_index.get('packets'), list) else []:
        if isinstance(record, dict):
            superseded = dict(record)
            superseded['is_current_generation'] = False
            superseded['superseded_by_generation_id'] = packet_generation_id
            superseded_packets.append(superseded)
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError('each repair transaction packet spec must be an object')
        packet_id = str(spec.get('packet_id') or f'material-scan-repair-{index:03d}')
        to_role = str(spec.get('to_role') or 'worker')
        if to_role != 'worker':
            raise RouterError('material scan repair packet must target the requested worker responsibility')
        body_text = router._material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=str(spec.get('node_id') or 'material-intake'), body_text=body_text, is_current_node=False, packet_type='material_scan', metadata={'stage': 'material_scan', 'source': 'repair_transaction_commit', 'repair_transaction_id': transaction_id, 'packet_generation_id': packet_generation_id, 'replacement_for': spec.get('replacement_for'), **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None)
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
        records.append({'packet_id': packet_id, 'to_role': to_role, 'packet_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'replacement_for': spec.get('replacement_for'), 'is_current_generation': True, 'packet_envelope_path': envelope['body_path'].replace('packet_body.md', 'packet_envelope.json'), 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'result_write_target': {'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body'])}, 'output_contract_id': envelope.get('output_contract_id')})
    batch_id = f'{packet_generation_id}-batch'
    if previous_batch_id and previous_batch_id != batch_id:
        previous_batch['status'] = 'superseded'
        previous_batch['superseded_by_generation_id'] = packet_generation_id
        previous_batch['superseded_by_batch_id'] = batch_id
        previous_batch['superseded_at'] = utc_now()
        router._write_parallel_packet_batch_state(run_root, previous_batch)
    batch = router._write_parallel_packet_batch(
        project_root,
        run_root,
        run_state,
        batch_id=batch_id,
        batch_kind='material_scan',
        phase='material_scan',
        records=records,
        node_id='material-intake',
        join_policy='all_results_before_pm_absorption',
        review_policy='pm_absorbs_batch_before_material_sufficiency_review',
        pm_absorption_required=True,
        parent_batch_id=previous_batch_id or None,
    )
    material_index_path = router._material_scan_index_path(run_root)
    write_json(material_index_path, {'schema_version': 'flowpilot.material_scan_packets.v2', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'batch_id': batch_id, 'batch_kind': 'material_scan', 'parallel_batch_path': project_relative(project_root, router._parallel_packet_batch_path(run_root, batch_id)), 'active_batch_ref_path': project_relative(project_root, router._parallel_packet_batch_ref_path(run_root, 'material_scan')), 'controller_may_read_packet_body': False, 'router_direct_dispatch_required_before_worker': True, 'reviewer_dispatch_required_before_worker': False, 'current_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'packets': records, 'superseded_packets': superseded_packets, 'written_at': utc_now()})
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)
    run_state['flags']['material_scan_packets_relayed'] = False
    run_state['flags']['worker_packets_delivered'] = False
    run_state['flags']['worker_scan_results_returned'] = False
    run_state['flags']['material_scan_results_relayed_to_reviewer'] = False
    run_state['flags']['material_scan_results_relayed_to_pm'] = False
    run_state['flags']['material_scan_result_disposition_recorded'] = False
    run_state['flags']['material_scan_results_absorbed_by_pm'] = False
    run_state['flags']['material_review_sufficient'] = False
    run_state['flags']['material_review_insufficient'] = False
    run_state['active_material_generation'] = {
        'schema_version': 'flowpilot.active_material_generation.v1',
        'packet_generation_id': packet_generation_id,
        'repair_transaction_id': transaction_id,
        'batch_id': batch_id,
        'parallel_batch_path': project_relative(project_root, router._parallel_packet_batch_path(run_root, batch_id)),
        'material_index_path': project_relative(project_root, material_index_path),
        'activated_at': utc_now(),
    }
    run_state['material_review'] = None
    return {'packet_generation_id': packet_generation_id, 'packet_count': len(records), 'packets': records, 'batch_id': batch.get('batch_id'), 'parallel_batch_path': project_relative(project_root, router._parallel_packet_batch_path(run_root, batch_id)), 'previous_batch_id': previous_batch_id or None, 'superseded_packet_count': len(superseded_packets), 'dispatch_index_path': project_relative(project_root, material_index_path), 'packet_ledger_path': project_relative(project_root, run_root / 'packet_ledger.json')}

__all__ = (
    '_commit_material_scan_repair_generation',
)

_LOCAL_NAMES = set(globals())
