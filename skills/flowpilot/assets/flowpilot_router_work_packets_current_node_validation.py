"""Current-node work-packet validation and next-action helpers for the FlowPilot router.

This child module is part of the ``flowpilot_router_work_packets_current_node``
facade split. It receives the router facade as an explicit runtime dependency
so shared state writers and public entrypoints remain compatible.
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
_BOUND_ROUTER: ModuleType | None = None
_CURRENT_NODE_PACKET_REQUIRED_FIELDS = ("body_path", "body_hash")
_CURRENT_NODE_PACKET_RETIRED_ALIAS_FIELDS = ("packet_body_path", "packet_body_hash")
_CURRENT_NODE_RESULT_REQUIRED_FIELDS = ("result_body_path", "result_body_hash", "next_recipient")
_CURRENT_NODE_RESULT_RETIRED_ALIAS_FIELDS = ("body_path", "body_hash", "to_role")


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

def _require_current_envelope_fields(envelope: dict[str, Any], *, label: str, required_fields: Iterable[str], unsupported_alias_fields: Iterable[str]) -> None:
    missing = [field for field in required_fields if envelope.get(field) in (None, "")]
    if missing:
        raise RouterError(f"{label} requires current envelope fields: {', '.join(missing)}")
    unsupported = [field for field in unsupported_alias_fields if field in envelope]
    if unsupported:
        raise RouterError(f"{label} uses unsupported envelope alias fields: {', '.join(unsupported)}")

def _validate_current_node_packet_envelope(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], envelope: dict[str, Any], envelope_path: Path, frontier: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if envelope.get('schema_version') != packet_runtime.PACKET_ENVELOPE_SCHEMA:
        raise RouterError('current-node packet envelope schema_version is invalid')
    _require_current_envelope_fields(
        envelope,
        label='current-node packet envelope',
        required_fields=_CURRENT_NODE_PACKET_REQUIRED_FIELDS,
        unsupported_alias_fields=_CURRENT_NODE_PACKET_RETIRED_ALIAS_FIELDS,
    )
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
    if active_bindings and envelope.get('to_role') == 'worker':
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
    if result.get('schema_version') != packet_runtime.RESULT_ENVELOPE_SCHEMA:
        raise RouterError('current-node result envelope schema_version is invalid')
    _require_current_envelope_fields(
        result,
        label='current-node result envelope',
        required_fields=_CURRENT_NODE_RESULT_REQUIRED_FIELDS,
        unsupported_alias_fields=_CURRENT_NODE_RESULT_RETIRED_ALIAS_FIELDS,
    )
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
    agent_role_map = router._agent_role_map_from_role_binding_ledger(run_root)
    audit = packet_runtime.validate_result_ready_for_recipient_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
    if not audit.get('passed'):
        raise RouterError(f"current-node result failed packet runtime audit: {audit.get('blockers')}")
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
        runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, records, packet_family='current_node', postcondition='current_node_packet_relayed', active_holder_plan=active_holder_plan)
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_current_node_packet', actor='controller', label='current_node_packet_relayed_after_router_direct_preflight_with_ledger_check', summary='Check the packet ledger and relay every current-node batch packet without opening packet bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), *relay_allowed_reads], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role')) for record in records})), extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations, **grant_extra})
        return make_action(action_type='relay_current_node_packet', actor='controller', label='current_node_packet_relayed_after_router_direct_preflight', summary='Directly relay current-node batch packet envelopes without opening their bodies.', allowed_reads=relay_allowed_reads, allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role')) for record in records})), extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations, **grant_extra})
    if flags.get('current_node_worker_result_returned') and (not flags.get('current_node_result_relayed_to_pm')):
        if not router._current_node_results_complete(project_root, run_state):
            missing_roles = router._current_node_missing_result_roles(project_root, run_state)
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_current_node_batch_results', summary='Controller must wait for every current-node batch result before relaying the batch to PM.', allowed_external_events=['worker_current_node_result_returned'], to_role=','.join(missing_roles) if missing_roles else 'worker', payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'current_node_batch_result_envelope', 'required_fields': ['packet_id', 'result_envelope_path'], 'batch_join_policy': 'all_results_before_pm_absorption'}, producer_roles_override=missing_roles)
        records = router._current_node_packet_records(project_root, run_state)
        result_paths = [router._result_envelope_path_from_packet_record(project_root, run_state, record) for record in records]
        runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, records, packet_family='current_node', postcondition='current_node_result_relayed_to_pm', to_role='project_manager')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_current_node_result_to_pm', actor='controller', label='current_node_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay the current-node worker batch result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), *[project_relative(project_root, path) for path in result_paths]], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_current_node_result_to_pm', actor='controller', label='current_node_result_relayed_to_pm', summary='Relay current-node batch result envelopes to PM without opening result bodies.', allowed_reads=[project_relative(project_root, path) for path in result_paths], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'packet_ids': [record.get('packet_id') for record in records], 'postcondition': 'current_node_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'runtime_relay_operations': runtime_relay_operations})
    if flags.get('current_node_result_relayed_to_pm') and (not flags.get('current_node_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_current_node_result_disposition', summary='Current-node worker results reached PM and Controller must wait for PM disposition before any reviewer node-completion gate.', allowed_external_events=['pm_records_current_node_result_disposition'], to_role='project_manager', payload_contract=pm_package_result_disposition_payload_contract('pm_current_node_result_disposition'))
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

def _try_reconcile_current_node_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    if not flags.get('current_node_packet_relayed'):
        return False
    summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'current_node')
    changed = bool(summary.get('changed'))
    already_recorded_packet_ids = {
        str(item.get('payload', {}).get('packet_id') or '')
        for item in run_state.get('events', [])
        if isinstance(item, dict) and item.get('event') == 'worker_current_node_result_returned' and isinstance(item.get('payload'), dict)
    }
    for record in router._current_node_packet_records(project_root, run_state):
        packet_id = str(record.get('packet_id') or '')
        if packet_id in already_recorded_packet_ids:
            continue
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if not result_exists:
            continue
        payload = {'packet_id': packet_id, 'result_envelope_path': project_relative(project_root, result_path), 'result_envelope_hash': packet_runtime.sha256_file(result_path), 'reconciled_from_result_envelope': True}
        try:
            router._validate_current_node_result_event(project_root, run_state, payload)
        except (RouterError, packet_runtime.PacketRuntimeError):
            continue
        changed = _record_router_reconciled_external_event(project_root, run_root, run_state, 'worker_current_node_result_returned', payload) or changed
    if changed:
        router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'current_node')
    return changed

__all__ = (
    '_validate_current_node_packet_envelope',
    '_validate_current_node_packet_event',
    '_validate_current_node_result_event',
    '_validate_current_node_reviewer_pass',
    '_next_current_node_packet_action',
    '_controller_status_packet_path_from_packet_envelope',
    '_role_output_status_packet_path_for_wait',
    '_try_reconcile_current_node_results',
)

_LOCAL_NAMES = set(globals())
