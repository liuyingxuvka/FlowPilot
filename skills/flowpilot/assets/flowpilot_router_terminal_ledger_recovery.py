"""Terminal recovery and legacy repair helpers for the FlowPilot router.

Receives the router facade explicitly so shared state writers and
public entrypoints keep the bound-router compatibility contract.
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


def _recover_terminal_status_from_run_authorities(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str | None:
    _bind_router(router)
    recoverable_statuses = {'stopped_by_user', 'cancelled_by_user', 'protocol_dead_end', 'completed', 'closed'}
    run_id = str(run_state.get('run_id') or run_root.name)
    status = str(run_state.get('status') or '')
    if status in recoverable_statuses:
        return status
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}
    if str(current.get('current_run_id') or current.get('active_run_id') or '') == run_id:
        current_status = str(current.get('status') or '')
        if current_status in recoverable_statuses:
            return current_status
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    for item in runs:
        if isinstance(item, dict) and str(item.get('run_id') or '') == run_id:
            index_status = str(item.get('status') or '')
            if index_status in recoverable_statuses:
                return index_status
    lifecycle = read_json_if_exists(_lifecycle_record_path(run_root)) or {}
    lifecycle_status = str(lifecycle.get('status') or '')
    if lifecycle_status in recoverable_statuses:
        return lifecycle_status
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    frontier_status = str(frontier.get('status') or '')
    if frontier.get('terminal') is True and frontier_status in recoverable_statuses:
        return frontier_status
    return None

def _repair_legacy_material_packet_contracts(router: ModuleType, project_root: Path, run_root: Path) -> int:
    _bind_router(router)
    index_path = router._material_scan_index_path(run_root)
    index = read_json_if_exists(index_path)
    ledger_path = run_root / 'packet_ledger.json'
    ledger = read_json_if_exists(ledger_path)
    if not isinstance(index, dict) and (not isinstance(ledger, dict)):
        return 0
    run_id = str((index.get('run_id') if isinstance(index, dict) else None) or (ledger.get('run_id') if isinstance(ledger, dict) else None) or run_root.name)
    ledger_packets = ledger.get('packets') if isinstance(ledger, dict) and isinstance(ledger.get('packets'), list) else []
    ledger_by_id = {str(packet.get('packet_id')): packet for packet in ledger_packets if isinstance(packet, dict) and packet.get('packet_id')}
    records_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(index, dict):
        for list_name in ('packets', 'superseded_packets'):
            for record in index.get(list_name, []) if isinstance(index.get(list_name), list) else []:
                if isinstance(record, dict) and record.get('packet_id'):
                    records_by_id[str(record['packet_id'])] = record
    for packet in ledger_packets:
        if not isinstance(packet, dict):
            continue
        packet_id = str(packet.get('packet_id') or '')
        packet_type = str(packet.get('packet_type') or packet.get('packet_envelope', {}).get('packet_type') or '')
        if packet_id and (packet_type == 'material_scan' or packet_id.startswith('material-scan')):
            records_by_id.setdefault(packet_id, {})
    changed_index = False
    changed_ledger = False
    repaired: list[dict[str, Any]] = []
    repaired_at = utc_now()
    for packet_id, record in sorted(records_by_id.items()):
        paths = packet_runtime.packet_paths(project_root, packet_id, run_id)
        ledger_record = ledger_by_id.get(packet_id, {})
        result_body_rel = str(record.get('result_body_path') or ledger_record.get('result_body_path') or project_relative(project_root, paths['result_body']))
        result_envelope_rel = str(record.get('result_envelope_path') or ledger_record.get('result_envelope_path') or project_relative(project_root, paths['result_envelope']))
        envelope_rel = str(record.get('packet_envelope_path') or ledger_record.get('packet_envelope_path') or project_relative(project_root, paths['packet_envelope']))
        envelope_path = resolve_project_path(project_root, envelope_rel)
        envelope = read_json_if_exists(envelope_path)
        if not isinstance(envelope, dict):
            continue
        envelope_changed = False
        for key, value in (('result_body_path', result_body_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_envelope_path', result_envelope_rel)):
            if envelope.get(key) != value:
                envelope[key] = value
                envelope_changed = True
        target = {'result_envelope_path': result_envelope_rel, 'result_body_path': result_body_rel}
        if envelope.get('result_write_target') != target:
            envelope['result_write_target'] = target
            envelope_changed = True
        metadata = envelope.get('metadata') if isinstance(envelope.get('metadata'), dict) else {}
        metadata_updates = {'expected_result_body_path': result_body_rel, 'expected_result_envelope_path': result_envelope_rel, 'write_target_path': result_body_rel}
        for key, value in metadata_updates.items():
            if metadata.get(key) != value:
                metadata[key] = value
                envelope_changed = True
        if metadata:
            envelope['metadata'] = metadata
        output_contract = envelope.get('output_contract') if isinstance(envelope.get('output_contract'), dict) else None
        if isinstance(output_contract, dict):
            contract = dict(output_contract)
            for key, value in metadata_updates.items():
                if contract.get(key) != value:
                    contract[key] = value
                    envelope_changed = True
            if contract != output_contract:
                envelope['output_contract'] = contract
        replacement_for = record.get('replacement_for') or metadata.get('replacement_for') or ledger_record.get('replacement_for')
        if replacement_for and (not envelope.get('replacement_for')):
            envelope['replacement_for'] = replacement_for
            envelope_changed = True
        if replacement_for and (not envelope.get('supersedes')):
            envelope['supersedes'] = [replacement_for]
            envelope_changed = True
        if envelope_changed:
            envelope['legacy_material_packet_contract_migration'] = {'schema_version': 'flowpilot.legacy_material_packet_contract_migration.v1', 'sealed_packet_body_not_read': True, 'sealed_packet_body_not_rewritten': True, 'envelope_result_write_target_backfilled': True, 'body_hash_preserved': True, 'migrated_at': repaired_at}
            write_json(envelope_path, envelope)
            repaired.append({'packet_id': packet_id, 'packet_envelope_path': project_relative(project_root, envelope_path), 'result_body_path': result_body_rel, 'result_envelope_path': result_envelope_rel, 'sealed_packet_body_not_read': True, 'sealed_packet_body_not_rewritten': True})
        if record:
            for key, value in (('packet_envelope_path', project_relative(project_root, envelope_path)), ('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if record.get(key) != value:
                    record[key] = value
                    changed_index = True
            target = {'result_envelope_path': result_envelope_rel, 'result_body_path': result_body_rel}
            if record.get('result_write_target') != target:
                record['result_write_target'] = target
                changed_index = True
        if ledger_record:
            for key, value in (('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if ledger_record.get(key) != value:
                    ledger_record[key] = value
                    changed_ledger = True
            if ledger_record.get('result_write_target') != target:
                ledger_record['result_write_target'] = target
                changed_ledger = True
            packet_envelope = ledger_record.get('packet_envelope') if isinstance(ledger_record.get('packet_envelope'), dict) else {}
            for key, value in (('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if packet_envelope.get(key) != value:
                    packet_envelope[key] = value
                    changed_ledger = True
            if packet_envelope:
                ledger_record['packet_envelope'] = packet_envelope
    if changed_index and isinstance(index, dict):
        index['updated_at'] = repaired_at
        write_json(index_path, index)
    if changed_ledger and isinstance(ledger, dict):
        ledger['updated_at'] = repaired_at
        write_json(ledger_path, ledger)
    if repaired:
        write_json(run_root / 'material' / 'legacy_material_packet_migration.json', {'schema_version': 'flowpilot.legacy_material_packet_contract_migration.v1', 'run_id': run_id, 'packet_count': len(repaired), 'packets': repaired, 'sealed_packet_bodies_read': False, 'sealed_packet_bodies_rewritten': False, 'migrated_at': repaired_at})
    return len(repaired)

def reconcile_current_run(router: ModuleType, project_root: Path) -> dict[str, Any]:
    _bind_router(router)
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = router.load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError('run state is missing')
    repaired: dict[str, Any] = {'prompt_delivery_contexts': 0, 'role_output_envelope_hashes': 0, 'terminal_lifecycle': False, 'terminal_lifecycle_record_written': False, 'terminal_closure_status_recovered': False, 'terminal_status_recovered_from_authority': False, 'legacy_material_packet_contracts': 0, 'non_current_running_index_entries': 0, 'scheduled_controller_receipts': {'changed': False, 'reconciled': 0, 'blocked': 0}, 'controller_boundary_projection': {'changed': False, 'reason': 'not_run'}}
    status = str(run_state.get('status') or '')
    flags = run_state.setdefault('flags', {})
    recovered_terminal_status = router._recover_terminal_status_from_run_authorities(project_root, run_root, run_state)
    if recovered_terminal_status and status not in RUN_TERMINAL_STATUSES:
        run_state['status'] = recovered_terminal_status
        status = recovered_terminal_status
        repaired['terminal_status_recovered_from_authority'] = True
        if recovered_terminal_status == 'closed':
            flags['terminal_closure_approved'] = True
            repaired['terminal_closure_status_recovered'] = True
    if status == 'stopped_by_user':
        flags['run_stopped_by_user'] = True
    elif status == 'cancelled_by_user':
        flags['run_cancelled_by_user'] = True
    elif status not in RUN_TERMINAL_STATUSES and router._terminal_closure_suite_is_closed(run_root):
        run_state['status'] = 'closed'
        flags['terminal_closure_approved'] = True
        status = 'closed'
        repaired['terminal_closure_status_recovered'] = True
    mode = _terminal_lifecycle_mode(run_state)
    if mode:
        run_state['status'] = mode
        run_state['phase'] = 'terminal'
        run_state['holder'] = 'controller'
        run_state['pending_action'] = None
        reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event='reconcile_current_run')
        lifecycle_path = _lifecycle_record_path(run_root)
        if not lifecycle_path.exists():
            write_json(lifecycle_path, {'schema_version': 'flowpilot.run_lifecycle.v1', 'run_id': run_state.get('run_id'), 'status': mode, 'request_event': 'reconcile_current_run', 'reason': 'terminal_lifecycle_reconciled_from_existing_authorities', 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'reconciliation': reconciliation, 'reconciled_at': utc_now()})
            append_history(run_state, 'run_lifecycle_record_written_by_reconcile', {'lifecycle_path': project_relative(project_root, lifecycle_path), 'status': mode})
            repaired['terminal_lifecycle_record_written'] = True
        _sync_current_and_index_status(project_root, run_state)
        repaired['terminal_lifecycle'] = True
    repaired['prompt_delivery_contexts'] = _repair_prompt_delivery_contexts(project_root, run_root, run_state)
    repaired['role_output_envelope_hashes'] = _repair_role_output_envelope_hashes(project_root, run_root)
    repaired['legacy_material_packet_contracts'] = router._repair_legacy_material_packet_contracts(project_root, run_root)
    repaired['scheduled_controller_receipts'] = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    repaired['controller_boundary_projection'] = _reconcile_controller_boundary_confirmation_projection(project_root, run_root, run_state, source='reconcile_current_run_projection_repair')
    router._refresh_route_memory(project_root, run_root, run_state, trigger='reconcile_current_run')
    repaired['non_current_running_index_entries'] = router._reconcile_non_current_running_index_entries(project_root, run_state)
    router._sync_derived_run_views(project_root, run_root, run_state, reason='reconcile_current_run')
    append_history(run_state, 'router_reconciled_current_run', repaired)
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'repaired': repaired}

__all__ = (
    '_recover_terminal_status_from_run_authorities',
    '_repair_legacy_material_packet_contracts',
    'reconcile_current_run',
)

_LOCAL_NAMES = set(globals())
