"""PM role-work next-action and reconciliation helpers."""

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
            runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, open_records, packet_family='pm_role_work', postcondition='pm_role_work_request_packet_relayed', active_holder_plan=active_holder_plan)
            allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), *[str(record.get('packet_envelope_path')) for record in batch_records]]
            if not run_state.get('ledger_check_requested'):
                return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_batch_relayed_with_ledger_check', summary='Check the packet ledger and relay every PM role-work request packet in the active batch without opening sealed bodies.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=to_roles, extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
            return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_batch_relayed', summary='Relay every PM role-work request packet in the active batch without opening sealed bodies.', allowed_reads=[project_relative(project_root, index_path), *[str(record.get('packet_envelope_path')) for record in batch_records]], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=to_roles, extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelopes_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
        if any((record.get('status') in {'packet_relayed', 'result_returned'} for record in batch_records)) and (not all((record.get('status') == 'result_returned' for record in batch_records))):
            missing_roles = [str(record.get('to_role') or record.get('request_id') or 'unknown') for record in batch_records if not resolve_project_path(project_root, str(record.get('result_envelope_path') or '')).exists()]
            action = _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_role_work_batch_results', summary='Controller has relayed the PM role-work batch and must wait for every target role to return a result envelope.', allowed_external_events=[ROLE_WORK_RESULT_RETURNED_EVENT], to_role=','.join(sorted(set(missing_roles))) if missing_roles else to_roles, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'role_work_result_returned_envelope', 'required_fields': ['request_id', 'packet_id', 'result_envelope_path'], 'batch_id': index.get('active_batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'expected_next_recipient': 'project_manager'}, producer_roles_override=missing_roles)
            if router._pm_role_work_records_are_nonblocking(batch_records):
                action['nonblocking_wait'] = True
                action['dependency_class'] = router._pm_role_work_records_dependency_class(batch_records)
            return action
        if all((record.get('status') == 'result_returned' for record in batch_records)):
            allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), *[str(record.get('result_envelope_path')) for record in batch_records]]
            runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, batch_records, packet_family='pm_role_work', postcondition='pm_role_work_result_relayed_to_pm', to_role='project_manager')
            if not run_state.get('ledger_check_requested'):
                return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_batch_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay every role-work result envelope in the batch back to PM without opening sealed result bodies.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'runtime_relay_operations': runtime_relay_operations})
            return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_batch_relayed_to_pm', summary='Relay every role-work result envelope in the batch back to PM without opening sealed result bodies.', allowed_reads=[project_relative(project_root, index_path), *[str(record.get('result_envelope_path')) for record in batch_records]], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'batch_id': index.get('active_batch_id'), 'request_id': batch_records[0].get('request_id') if len(batch_records) == 1 else None, 'packet_id': batch_records[0].get('packet_id') if len(batch_records) == 1 else None, 'packet_ids': packet_ids, 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelopes_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'runtime_relay_operations': runtime_relay_operations})
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
        runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, [active], packet_family='pm_role_work', postcondition='pm_role_work_request_packet_relayed', active_holder_plan=active_holder_plan)
        allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), str(active.get('packet_envelope_path'))]
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_packet_relayed_with_ledger_check', summary='Check the packet ledger and relay the PM role-work request packet without opening the sealed body.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=str(active.get('to_role') or ''), extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': packet_ids, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_pm_role_work_request_packet', actor='controller', label='pm_role_work_request_packet_relayed', summary='Relay the PM role-work request packet without opening the sealed body.', allowed_reads=[project_relative(project_root, index_path), str(active.get('packet_envelope_path'))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path), *active_holder_allowed_writes], to_role=str(active.get('to_role') or ''), extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_request_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
    if active.get('status') == 'result_returned':
        allowed_reads = [project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), str(active.get('result_envelope_path'))]
        runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, [active], packet_family='pm_role_work', postcondition='pm_role_work_result_relayed_to_pm', to_role='project_manager')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay the role-work result envelope back to PM without opening the sealed result body.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': packet_ids, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_pm_role_work_result_to_pm', actor='controller', label='pm_role_work_result_relayed_to_pm', summary='Relay the role-work result envelope back to PM without opening the sealed result body.', allowed_reads=[project_relative(project_root, index_path), str(active.get('result_envelope_path'))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, index_path), project_relative(project_root, lifecycle_index_path)], to_role='project_manager', extra={'request_id': active.get('request_id'), 'packet_id': active.get('packet_id'), 'postcondition': 'pm_role_work_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'pm_work_requests': project_relative(project_root, index_path), 'officer_request_lifecycle_index': project_relative(project_root, lifecycle_index_path), 'runtime_relay_operations': runtime_relay_operations})
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
    '_next_pm_role_work_request_action',
    '_try_reconcile_pm_role_work_results',
)

_LOCAL_NAMES = set(globals())
