"""Current-node work-packet path and context helpers for the FlowPilot router.

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
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if not result_exists:
            return False
        result_valid, _details = router._parallel_batch_record_result_is_valid(
            project_root,
            result_path,
            expected_next_recipient='project_manager',
        )
        if not result_valid:
            return False
    return True

def _current_node_missing_result_roles(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> list[str]:
    _bind_router(router)
    missing: list[str] = []
    for record in router._current_node_packet_records(project_root, run_state):
        result_exists, result_path = router._parallel_batch_record_result_exists(project_root, run_state, record)
        if result_exists:
            result_valid, _details = router._parallel_batch_record_result_is_valid(
                project_root,
                result_path,
                expected_next_recipient='project_manager',
            )
            if result_valid:
                continue
        else:
            missing.append(str(record.get('to_role') or record.get('packet_id') or 'unknown'))
            continue
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

def _material_scan_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'material' / 'material_scan_packets.json'

def _research_packet_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'research' / 'research_packet.json'

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
    '_material_scan_index_path',
    '_research_packet_index_path',
)

_LOCAL_NAMES = set(globals())
