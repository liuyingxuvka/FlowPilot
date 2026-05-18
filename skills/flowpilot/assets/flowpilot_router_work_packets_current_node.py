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

__all__ = (
    '_packet_paths',
    '_active_current_node_packet_records',
    '_current_node_batch_packet_record',
    '_packet_envelope_path',
    '_result_envelope_path',
    '_current_node_packet_context',
    '_current_node_packet_records',
    '_current_node_results_complete',
    '_current_node_missing_result_roles',
    '_active_child_skill_bindings_from_plan',
    '_active_child_skill_source_paths',
    '_metadata_string_list',
    '_metadata_binding_ids',
    '_current_node_result_context',
    '_packet_envelope_path_from_record',
    '_result_envelope_path_from_packet_record',
    '_load_packet_index',
    '_ensure_barrier_bundles_ready',
    '_material_scan_index_path',
    '_research_packet_index_path',
    '_relay_packet_records',
    '_active_holder_frontier_version',
    '_current_node_active_holder_lease_plan',
    '_issue_current_node_active_holder_leases',
    '_packet_active_holder_lease_plan',
    '_issue_packet_active_holder_leases',
    '_relay_result_records',
    '_agent_role_map_from_crew_ledger',
    '_merge_agent_role_maps',
    '_validate_packet_bodies_opened_by_targets',
    '_validate_results_exist_for_packets',
    '_validate_packet_group_for_reviewer',
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
