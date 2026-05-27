"""role recovery agent records helpers for ``flowpilot_router_startup_role_transactions``.

This child module is imported by the compatibility facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_role_recovery'

def _normalize_role_recovery_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _bind_router(router)
    if payload.get('background_agents_capability_status') != 'available':
        raise RouterError('role recovery requires background_agents_capability_status=available')
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        raise RouterError('role recovery requires an open role recovery transaction')
    if payload.get('recovery_transaction_id') != transaction.get('transaction_id'):
        raise RouterError('role recovery transaction id mismatch')
    trigger_source = str(transaction.get('trigger_source') or '')
    if payload.get('trigger_source') != trigger_source:
        raise RouterError('role recovery trigger_source mismatch')
    requested_scope = str(transaction.get('recovery_scope') or 'targeted')
    payload_scope = str(payload.get('recovery_scope') or requested_scope)
    if payload_scope not in {requested_scope, 'full_crew'}:
        raise RouterError('role recovery scope mismatch')
    target_roles = [str(role) for role in transaction.get('target_role_keys') or []]
    payload_targets = payload.get('target_role_keys')
    if payload_targets != target_roles:
        raise RouterError('role recovery target_role_keys mismatch')
    raw_records = payload.get('recovered_role_agents') or payload.get('role_agents')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('role recovery requires payload.recovered_role_agents list or object')
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    existing_by_role = {str(slot.get('role_key')): slot for slot in slots if isinstance(slot, dict) and slot.get('role_key') in CREW_ROLE_KEYS}
    full_crew = payload_scope == 'full_crew' or any((isinstance(raw, dict) and raw.get('recovery_result') == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT for raw in iterable))
    expected_roles = list(CREW_ROLE_KEYS) if full_crew else target_roles
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    records_by_role: dict[str, dict[str, Any]] = {}
    environment_blocked = False
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each recovered role agent record must be an object')
        role = str(raw.get('role_key') or '')
        if role not in CREW_ROLE_KEYS:
            raise RouterError(f'role recovery record has unsupported role_key: {role!r}')
        if role not in expected_roles:
            raise RouterError(f'role recovery record {role} is outside the expected recovery scope')
        if role in records_by_role:
            raise RouterError(f'duplicate role recovery record for {role}')
        result = str(raw.get('recovery_result') or '')
        if result not in ROLE_RECOVERY_RESULTS:
            raise RouterError(f'{role} requires supported recovery_result')
        restore_attempted = raw.get('restore_attempted') is True
        restore_result = str(raw.get('restore_result') or 'unknown')
        targeted_attempted = raw.get('targeted_replacement_attempted') is True
        targeted_result = str(raw.get('targeted_replacement_result') or 'not_attempted')
        old_close_failed = raw.get('old_close_failed') is True
        spawn_capacity_full = raw.get('spawn_capacity_full') is True or targeted_result == 'capacity_full'
        slot_reconciliation_attempted = raw.get('slot_reconciliation_attempted') is True
        full_recycle_attempted = raw.get('full_crew_recycle_attempted') is True
        full_recycle_result = str(raw.get('full_crew_recycle_result') or 'not_attempted')
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            agent_id = raw.get('agent_id')
            if not isinstance(agent_id, str) or not agent_id.strip():
                raise RouterError(f'{role} requires a recovered live agent_id')
            host_liveness_status = str(raw.get('host_liveness_status') or '')
            if host_liveness_status not in ROLE_AGENT_HOST_LIVENESS_STATUSES:
                raise RouterError(f'{role} requires host_liveness_status')
            if host_liveness_status != 'active':
                raise RouterError(f'{role} recovered agent requires active host liveness')
            liveness_decision = str(raw.get('liveness_decision') or '')
            if liveness_decision not in ROLE_AGENT_LIVENESS_DECISIONS:
                raise RouterError(f'{role} requires liveness_decision')
            if raw.get('model_policy') != BACKGROUND_ROLE_MODEL_POLICY:
                raise RouterError(f'{role} requires model_policy={BACKGROUND_ROLE_MODEL_POLICY}')
            if raw.get('reasoning_effort_policy') != BACKGROUND_ROLE_REASONING_EFFORT_POLICY:
                raise RouterError(f'{role} requires reasoning_effort_policy={BACKGROUND_ROLE_REASONING_EFFORT_POLICY}')
            if raw.get('rehydrated_for_run_id') != run_state['run_id']:
                raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
            if raw.get('memory_context_injected') is not True:
                raise RouterError(f'{role} recovery requires memory_context_injected=true')
            if raw.get('packet_ownership_reconciled') is not True:
                raise RouterError(f'{role} recovery requires packet_ownership_reconciled=true')
            if raw.get('role_binding_epoch_advanced') is not True:
                raise RouterError(f'{role} recovery requires role_binding_epoch_advanced=true')
        else:
            environment_blocked = True
            agent_id = None
            host_liveness_status = None
            liveness_decision = None
        if result == ROLE_AGENT_OLD_RESTORE_RESULT:
            if not restore_attempted or restore_result != 'success':
                raise RouterError(f'{role} old-agent restore result requires restore_attempted=true and restore_result=success')
            if liveness_decision != 'confirmed_existing_agent':
                raise RouterError(f'{role} old-agent restore requires confirmed_existing_agent liveness decision')
        elif result == ROLE_AGENT_TARGETED_REPLACEMENT_RESULT:
            if not restore_attempted or restore_result != 'failed':
                raise RouterError(f'{role} targeted replacement requires failed restore first')
            if not targeted_attempted or targeted_result != 'success':
                raise RouterError(f'{role} targeted replacement requires targeted_replacement_attempted=true and targeted_replacement_result=success')
            if liveness_decision != 'spawned_replacement_from_current_run_memory':
                raise RouterError(f'{role} targeted replacement requires spawned_replacement_from_current_run_memory liveness decision')
        elif result == ROLE_AGENT_FULL_CREW_RECYCLE_RESULT:
            if requested_scope == 'targeted' and (not (restore_attempted and restore_result == 'failed' and targeted_attempted and (targeted_result in {'failed', 'capacity_full'}) and slot_reconciliation_attempted)):
                raise RouterError(f'{role} full crew recycle requires targeted restore/replacement/slot reconciliation escalation')
            if not full_recycle_attempted or full_recycle_result != 'success':
                raise RouterError(f'{role} full crew recycle requires full_crew_recycle_attempted=true and full_crew_recycle_result=success')
            if liveness_decision != 'spawned_replacement_from_current_run_memory':
                raise RouterError(f'{role} full crew recycle requires spawned_replacement_from_current_run_memory liveness decision')
        elif result == ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if not full_recycle_attempted or full_recycle_result != 'failed':
                raise RouterError(f'{role} environment_blocked requires failed full crew recycle')
        if old_close_failed and spawn_capacity_full and (not full_recycle_attempted):
            raise RouterError(f'{role} capacity/full-slot conflict requires full crew recycle escalation')
        if result in {ROLE_AGENT_TARGETED_REPLACEMENT_RESULT, ROLE_AGENT_FULL_CREW_RECYCLE_RESULT}:
            if raw.get('superseded_agent_output_quarantined') is not True:
                raise RouterError(f'{role} replacement/recycle requires superseded_agent_output_quarantined=true')
        context = contexts[role]
        memory_status = context['role_memory_status']
        if result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run memory')
        elif result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        old_slot = existing_by_role.get(role) or {}
        old_agent_id = raw.get('old_agent_id') or old_slot.get('agent_id')
        records_by_role[role] = {'role_key': role, 'old_agent_id': old_agent_id, 'agent_id': agent_id, 'model_policy': BACKGROUND_ROLE_MODEL_POLICY if agent_id else None, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY if agent_id else None, 'recovery_result': result, 'restore_attempted': restore_attempted, 'restore_result': restore_result, 'targeted_replacement_attempted': targeted_attempted, 'targeted_replacement_result': targeted_result, 'old_close_failed': old_close_failed, 'spawn_capacity_full': spawn_capacity_full, 'slot_reconciliation_attempted': slot_reconciliation_attempted, 'full_crew_recycle_attempted': full_recycle_attempted, 'full_crew_recycle_result': full_recycle_result, 'host_liveness_status': host_liveness_status, 'liveness_decision': liveness_decision, 'host_liveness_verified': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and host_liveness_status == 'active', 'rehydrated_for_run_id': run_state['run_id'], 'memory_context_injected': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'packet_ownership_reconciled': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'role_binding_epoch_advanced': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT, 'superseded_agent_output_quarantined': bool(raw.get('superseded_agent_output_quarantined')), 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status == 'available', 'replacement_seeded_from_common_run_context': result != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT and memory_status != 'available', 'recorded_at': utc_now()}
    missing = [role for role in expected_roles if role not in records_by_role]
    if missing:
        raise RouterError(f"missing role recovery records: {', '.join(missing)}")
    if environment_blocked and any((record['recovery_result'] != ROLE_AGENT_ENVIRONMENT_BLOCKED_RESULT for record in records_by_role.values())):
        raise RouterError('environment-blocked role recovery report cannot mix ready and blocked role records')
    return ([records_by_role[role] for role in expected_roles], transaction)

def _role_recovery_obligation_replay_path(router: ModuleType, run_root: Path, transaction_id: str) -> Path:
    _bind_router(router)
    safe_transaction = _safe_delivery_component(transaction_id or 'role-recovery')
    return router._role_recovery_dir(run_root) / f'{safe_transaction}_obligation_replay.json'

__all__ = (
    '_normalize_role_recovery_agent_records',
    '_role_recovery_obligation_replay_path',
)

_LOCAL_NAMES = set(globals())
