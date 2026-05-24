"""Current-node work-packet relay, lease, and audit helpers for the FlowPilot router.

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
import flowpilot_router_work_packets_current_node_relay_leases as _current_node_relay_leases
import flowpilot_router_work_packets_current_node_relay_runtime_ops as _current_node_relay_runtime_ops
from flowpilot_router_work_packets_current_node_relay_leases import *
from flowpilot_router_work_packets_current_node_relay_runtime_ops import *

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
    _current_node_relay_leases._bind_router(router)
    _current_node_relay_runtime_ops._bind_router(router)

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
        audit = packet_runtime.validate_result_ready_for_recipient_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
        if not audit.get('passed'):
            raise RouterError(f"result envelope is not ready for recipient relay: {audit.get('blockers')}")
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
        audit = packet_runtime.validate_result_ready_for_recipient_relay(project_root, packet_envelope=packet_envelope, result_envelope=result, agent_role_map=agent_role_map)
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

__all__ = (
    '_relay_packet_records',
    '_active_holder_frontier_version',
    '_current_node_active_holder_lease_plan',
    '_issue_current_node_active_holder_leases',
    '_packet_active_holder_lease_plan',
    '_issue_packet_active_holder_leases',
    '_packet_runtime_relay_operations',
    '_result_runtime_relay_operations',
    '_relay_result_records',
    '_agent_role_map_from_crew_ledger',
    '_merge_agent_role_maps',
    '_validate_packet_bodies_opened_by_targets',
    '_validate_results_exist_for_packets',
    '_validate_packet_group_for_reviewer',
)

_LOCAL_NAMES = set(globals())
