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
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_material_scan_result_disposition', summary='Controller relayed material scan results to PM and must wait for PM to record a result disposition before any reviewer sufficiency gate.', allowed_external_events=['pm_records_material_scan_result_disposition'], to_role='project_manager', payload_contract=pm_package_result_disposition_payload_contract('pm_material_scan_result_disposition'))
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

__all__ = (
    '_next_material_packet_action',
    '_next_research_packet_action',
    '_try_reconcile_material_scan_body_delivery',
    '_try_reconcile_material_scan_results',
)

_LOCAL_NAMES = set(globals())
