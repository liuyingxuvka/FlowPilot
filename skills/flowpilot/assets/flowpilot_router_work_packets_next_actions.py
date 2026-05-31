"""Coarse work packets owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
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

_MATERIAL_PM_RELAYED_STATUSES = {
    'results_relayed_to_pm',
    'pm_absorbed',
    'accepted',
    'reviewed',
    'complete',
}

_PACKET_FAMILY_RESULT_RECONCILIATION = {
    'material_scan': {
        'event': 'worker_scan_results_returned',
        'index_label': 'material scan',
        'relayed_flag': 'material_scan_packets_relayed',
        'next_recipient': 'project_manager',
    },
    'research': {
        'event': 'worker_research_report_returned',
        'index_label': 'research',
        'relayed_flag': 'research_packet_relayed',
        'required_flag': 'worker_research_report_card_delivered',
        'next_recipient': 'project_manager',
    },
}


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _as_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def _active_material_generation_progress(
    router: ModuleType,
    project_root: Path,
    run_state: dict[str, Any],
    run_root: Path,
) -> dict[str, Any]:
    _bind_router(router)
    material_index = read_json_if_exists(router._material_scan_index_path(run_root))
    if not isinstance(material_index, dict) or not material_index:
        return {'active': False}
    try:
        batch = router._active_parallel_packet_batch(run_root, 'material_scan')
    except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
        return {'active': False}
    if not isinstance(batch, dict) or not batch:
        return {'active': False}
    records = [record for record in batch.get('packets') or [] if isinstance(record, dict)]
    current_generation_id = str(material_index.get('current_generation_id') or '')
    repair_transaction_id = str(material_index.get('repair_transaction_id') or '')
    generation_ids = {
        str(record.get('packet_generation_id') or '')
        for record in records
        if record.get('packet_generation_id')
    }
    repair_ids = {
        str(record.get('repair_transaction_id') or '')
        for record in records
        if record.get('repair_transaction_id')
    }
    if not (current_generation_id or repair_transaction_id or generation_ids or repair_ids):
        return {'active': False}
    if current_generation_id and generation_ids and generation_ids != {current_generation_id}:
        return {
            'active': True,
            'current_generation_id': current_generation_id,
            'generation_mismatch': True,
            'packets_relayed': False,
            'all_results_returned': False,
            'results_relayed_to_pm': False,
            'pm_disposition_recorded': False,
        }
    summary = router._refresh_parallel_packet_batch_from_durable_results(
        project_root,
        run_root,
        run_state,
        'material_scan',
    )
    try:
        batch = router._active_parallel_packet_batch(run_root, 'material_scan') or batch
    except (RouterError, OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    records = [record for record in batch.get('packets') or [] if isinstance(record, dict)]
    counts = batch.get('counts') if isinstance(batch.get('counts'), dict) else {}
    member_status = batch.get('member_status') if isinstance(batch.get('member_status'), dict) else {}
    packet_count = max(
        len(records),
        _as_int(counts.get('registered')),
        _as_int(member_status.get('packet_count')),
        _as_int(summary.get('packet_count')),
    )
    relayed = _as_int(counts.get('relayed'))
    results_returned = max(
        _as_int(counts.get('results_returned')),
        _as_int(member_status.get('results_returned')),
        _as_int(summary.get('results_returned')),
    )
    batch_status = str(batch.get('status') or '')
    pm_disposition_recorded = isinstance(batch.get('pm_result_disposition'), dict)
    return {
        'active': True,
        'batch_id': batch.get('batch_id'),
        'current_generation_id': current_generation_id or None,
        'repair_transaction_id': repair_transaction_id or next(iter(sorted(repair_ids)), None),
        'packet_count': packet_count,
        'relayed': relayed,
        'results_returned': results_returned,
        'missing_roles': summary.get('missing_roles') or member_status.get('missing_roles') or [],
        'partial_results_returned': bool(summary.get('partial_results_returned') or member_status.get('partial_results_returned')),
        'all_results_returned': bool(summary.get('all_results_returned') or member_status.get('all_results_returned') or (packet_count > 0 and results_returned >= packet_count)),
        'packets_relayed': packet_count > 0 and relayed >= packet_count,
        'results_relayed_to_pm': batch_status in _MATERIAL_PM_RELAYED_STATUSES or pm_disposition_recorded,
        'pm_disposition_recorded': pm_disposition_recorded,
        'batch_status': batch_status,
        'summary': summary,
    }

def _next_material_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    material_progress = _active_material_generation_progress(router, project_root, run_state, run_root)
    generation_progress_active = bool(material_progress.get('active'))
    packets_relayed = bool(material_progress.get('packets_relayed')) if generation_progress_active else bool(flags.get('material_scan_packets_relayed'))
    worker_results_returned = bool(material_progress.get('all_results_returned')) if generation_progress_active else bool(flags.get('worker_scan_results_returned'))
    results_relayed_to_pm = bool(material_progress.get('results_relayed_to_pm')) if generation_progress_active else bool(flags.get('material_scan_results_relayed_to_pm'))
    pm_disposition_recorded = bool(material_progress.get('pm_disposition_recorded')) if generation_progress_active else bool(flags.get('material_scan_result_disposition_recorded'))
    if (flags.get('pm_material_packets_issued') or generation_progress_active) and (not packets_relayed):
        index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, index['packets'], packet_family='material_scan', mode='lease_on_material_scan_relay')
        runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='material_scan', postcondition='material_scan_packets_relayed', active_holder_plan=active_holder_plan)
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_material_scan_packets', actor='controller', label='material_scan_packets_relayed_after_router_direct_preflight_with_ledger_check', summary='Check the packet ledger and directly relay material scan packet envelopes to requested worker responsibilities without opening bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role='worker', extra={'postcondition': 'material_scan_packets_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_material_scan_packets', actor='controller', label='material_scan_packets_relayed_after_router_direct_preflight', summary='Directly relay material scan packet envelopes without opening bodies.', allowed_reads=[project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role='worker', extra={'postcondition': 'material_scan_packets_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
    if packets_relayed and (not worker_results_returned):
        summary = material_progress.get('summary') if generation_progress_active else None
        summary = summary if isinstance(summary, dict) else router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'material_scan')
        if summary.get('partial_results_returned'):
            missing_roles = [str(role) for role in summary.get('missing_roles') or [] if role]
            allowed_event = 'worker_scan_results_returned' if flags.get('worker_packets_delivered') else 'worker_scan_packet_bodies_delivered_after_dispatch'
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_material_scan_batch_results', summary='Controller has some material scan result envelopes and must wait only for the missing batch member(s).', allowed_external_events=[allowed_event], to_role=','.join(missing_roles) if missing_roles else 'worker', allowed_reads_extra=[project_relative(project_root, router._parallel_packet_batch_path(run_root, str(summary.get('batch_id'))))] if summary.get('batch_id') else None, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'material_scan_partial_batch_result', 'required_fields': ['packet_id', 'result_envelope_path'], 'batch_id': summary.get('batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'packet_count': summary.get('packet_count'), 'results_returned': summary.get('results_returned'), 'missing_roles': missing_roles, 'controller_visibility': 'metadata_only'}, producer_roles_override=missing_roles)
    if worker_results_returned and (not results_relayed_to_pm):
        index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='material_scan', postcondition='material_scan_results_relayed_to_pm', to_role='project_manager')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_material_scan_results_to_pm', actor='controller', label='material_scan_results_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay material scan result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'material_scan_results_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_material_scan_results_to_pm', actor='controller', label='material_scan_results_relayed_to_pm', summary='Relay material scan result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, router._material_scan_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'material_scan_results_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'runtime_relay_operations': runtime_relay_operations})
    if results_relayed_to_pm and (not pm_disposition_recorded):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_material_scan_result_disposition', summary='Controller relayed material scan results to PM and must wait for PM to record a result disposition before any reviewer sufficiency gate.', allowed_external_events=['pm_records_material_scan_result_disposition'], to_role='project_manager', payload_contract=pm_package_result_disposition_payload_contract('pm_material_scan_result_disposition'))
    return None

def _next_research_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if flags.get('research_capability_decision_recorded') and (not flags.get('research_packet_relayed')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, index['packets'], packet_family='research', mode='lease_on_research_packet_relay')
        runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='research', postcondition='research_packet_relayed', active_holder_plan=active_holder_plan)
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker_with_ledger_check', summary='Check the packet ledger and relay research packet envelope to the requested worker without opening the body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker', summary='Relay research batch packet envelopes without opening their bodies.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
    if flags.get('research_packet_relayed') and flags.get('worker_research_report_card_delivered') and (not flags.get('worker_research_report_returned')):
        summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'research')
        if summary.get('partial_results_returned'):
            missing_roles = [str(role) for role in summary.get('missing_roles') or [] if role]
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_research_batch_results', summary='Controller has some research result envelopes and must wait only for the missing batch member(s).', allowed_external_events=['worker_research_report_returned'], to_role=','.join(missing_roles) if missing_roles else 'worker', allowed_reads_extra=[project_relative(project_root, router._parallel_packet_batch_path(run_root, str(summary.get('batch_id'))))] if summary.get('batch_id') else None, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'research_partial_batch_result', 'required_fields': ['packet_id', 'result_envelope_path', 'answers_decision_question'], 'batch_id': summary.get('batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'packet_count': summary.get('packet_count'), 'results_returned': summary.get('results_returned'), 'missing_roles': missing_roles, 'controller_visibility': 'metadata_only'}, producer_roles_override=missing_roles)
    if flags.get('worker_research_report_returned') and (not flags.get('research_result_relayed_to_pm')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='research', postcondition='research_result_relayed_to_pm', to_role='project_manager')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm', summary='Relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'runtime_relay_operations': runtime_relay_operations})
    if flags.get('research_result_relayed_to_pm') and (not flags.get('research_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_research_result_disposition', summary='Controller relayed research results to PM and must wait for PM disposition before any reviewer direct-source gate.', allowed_external_events=['pm_records_research_result_disposition'], to_role='project_manager', payload_contract=pm_package_result_disposition_payload_contract('pm_research_result_disposition'))
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

def _packet_family_index_path(router: ModuleType, run_root: Path, batch_kind: str) -> Path:
    _bind_router(router)
    if batch_kind == 'material_scan':
        return router._material_scan_index_path(run_root)
    if batch_kind == 'research':
        return router._research_packet_index_path(run_root)
    raise RouterError(f'unsupported packet family result reconciliation kind: {batch_kind}')

def _reconciled_packet_family_result_payload(batch_kind: str, index: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    packets = [record for record in index.get('packets') or [] if isinstance(record, dict)]
    payload: dict[str, Any] = {
        'packet_ids': [record.get('packet_id') for record in packets],
        'batch_id': summary.get('batch_id') or index.get('batch_id'),
        'results_returned': summary.get('results_returned'),
        'reconciled_from_result_envelopes': True,
    }
    if batch_kind == 'research':
        completed_roles = sorted({str(record.get('to_role')) for record in packets if record.get('to_role')})
        payload.update({
            'completed_by_roles': completed_roles,
            'completed_by_role': ','.join(completed_roles),
            'answers_decision_question': True,
            'answers_decision_question_source': 'durable_result_envelope_returned_pm_review_required',
        })
    return payload

def _try_reconcile_packet_family_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    batch_kind: str,
) -> bool:
    _bind_router(router)
    config = _PACKET_FAMILY_RESULT_RECONCILIATION[batch_kind]
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    event = str(config['event'])
    event_flag = str(EXTERNAL_EVENTS[event]['flag'])
    if flags.get(event_flag) or not flags.get(str(config['relayed_flag'])):
        return False
    required_flag = str(config.get('required_flag') or '')
    if required_flag and not flags.get(required_flag):
        return False
    index = router._load_packet_index(_packet_family_index_path(router, run_root, batch_kind), label=str(config['index_label']))
    summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind)
    if not summary.get('all_results_returned'):
        return bool(summary.get('changed'))
    if batch_kind == 'material_scan':
        router._try_reconcile_material_scan_body_delivery(project_root, run_root, run_state)
        if not run_state['flags'].get('worker_packets_delivered'):
            return bool(summary.get('changed'))
    try:
        router._validate_results_exist_for_packets(project_root, run_state, index['packets'], next_recipient=str(config['next_recipient']))
    except (RouterError, packet_runtime.PacketRuntimeError):
        return bool(summary.get('changed'))
    payload = _reconciled_packet_family_result_payload(batch_kind, index, summary)
    if batch_kind == 'research':
        try:
            router._write_worker_research_report(project_root, run_root, run_state, payload)
        except (RouterError, packet_runtime.PacketRuntimeError):
            return bool(summary.get('changed'))
    return _record_router_reconciled_external_event(project_root, run_root, run_state, event, payload) or bool(summary.get('changed'))

def _try_reconcile_material_scan_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return _try_reconcile_packet_family_results(router, project_root, run_root, run_state, 'material_scan')

def _try_reconcile_research_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return _try_reconcile_packet_family_results(router, project_root, run_root, run_state, 'research')

__all__ = (
    '_next_material_packet_action',
    '_next_research_packet_action',
    '_try_reconcile_material_scan_body_delivery',
    '_try_reconcile_material_scan_results',
    '_try_reconcile_research_results',
)

_LOCAL_NAMES = set(globals())
