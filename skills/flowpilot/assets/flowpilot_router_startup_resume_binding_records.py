"""Resume role-binding record normalization for startup resume binding."""

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
    if _BOUND_ROUTER is router:
        return
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

def _resume_role_rehydration_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    startup_answers = run_state.get('startup_answers') if isinstance(run_state.get('startup_answers'), dict) else {}
    background_authorized = startup_answers.get('background_collaboration_authorized') is True
    contexts = router._resume_role_contexts(project_root, run_root, run_state)
    target_role_keys = [item['role_key'] for item in contexts]
    missing_memory = [item['role_key'] for item in contexts if item['role_memory_status'] != 'available']
    resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
    return {
        'role_binding_mode': 'current_run_manual_resume_rehydration',
        'role_keys': target_role_keys,
        'resume_tick_id': router._latest_resume_tick_id(run_state),
        'awaiting_role_from_packet_ledger': resume_next.get('next_recipient_role'),
        'resume_next_recipient_from_packet_ledger': resume_next,
        'role_rehydration_request': contexts,
        'background_collaboration_authorized': background_authorized,
        'background_role_agent_model_policy': {
            'model_policy': ROLE_BINDING_MODEL_POLICY,
            'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY,
            'preferred_reasoning_effort': ROLE_BINDING_PREFERRED_REASONING_EFFORT,
            'inherit_foreground_model_allowed': False,
            'applies_to': ['manual_resume_rehydration', 'missing_role_replacement'],
        },
        'memory_missing_role_keys': missing_memory,
        'role_binding_recovery_report_path': project_relative(project_root, run_root / 'continuation' / 'role_binding_recovery_report.json'),
        'ack_progress_evidence_policy': {
            'current_wait_authority': 'ack_progress_evidence_only',
            'current_waiting_role_source': 'packet_ledger.next_recipient_role',
            'unsupported_legacy_payloads_rejected': True,
        },
        'requires_payload': 'rehydrated_role_bindings',
        'payload_contract': _resume_role_rehydration_payload_contract(run_state, contexts),
        'requires_host_role_binding': False,
        'requires_host_role_rehydration': bool(target_role_keys),
        'requires_host_role_binding_for_replacements': bool(target_role_keys),
        'new_binding_required_only_for_replacements': True,
        'reuse_addressable_current_run_agents': True,
        'role_binding_open_policy': 'reuse_addressable_current_run_agent_or_open_replacement_from_memory',
        'pm_memory_rehydration_required': 'project_manager' in target_role_keys,
        'controller_visibility': 'state_and_envelopes_only',
        'sealed_body_reads_allowed': False,
        'chat_history_progress_inference_allowed': False,
    }

def _normalize_resume_role_agent_records(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    contexts = {item['role_key']: item for item in router._resume_role_contexts(project_root, run_root, run_state)}
    stale_memory_roles = [
        role
        for role, context in contexts.items()
        if context.get('role_memory_status') == 'stale'
    ]
    if stale_memory_roles:
        raise RouterError(
            "resume role rehydration rejects stale role memory for: "
            + ", ".join(stale_memory_roles)
        )
    role_binding = read_json_if_exists(run_root / 'role_binding_ledger.json')
    current_generation = router._current_role_binding_generation(role_binding)
    existing_slots = {str(slot.get('role_key')): slot for slot in (role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []) if isinstance(slot, dict) and slot.get('role_key') in RUNTIME_ROLE_KEYS}
    resume_tick_id = router._latest_resume_tick_id(run_state)
    startup_answers = run_state.get('startup_answers') if isinstance(run_state.get('startup_answers'), dict) else {}
    if startup_answers.get('background_collaboration_authorized') is not True:
        raise RouterError('resume role rehydration requires background_collaboration_authorized=true')
    if payload.get('runtime_role_assistance_capability_status') != 'available':
        raise RouterError('resume role rehydration requires runtime_role_assistance_capability_status=available')
    legacy_payload_keys = {
        'liveness_probe_batch_id',
        'liveness_probe_mode',
        'all_liveness_probes_started_before_wait',
        'timeout_unknown',
        'timeout_unknown_is_active',
        'bounded_wait_result',
        'host_liveness_status',
    }
    found_legacy_payload_keys = sorted(key for key in legacy_payload_keys if key in payload)
    if found_legacy_payload_keys:
        raise RouterError(f"resume role rehydration received unsupported legacy liveness fields: {', '.join(found_legacy_payload_keys)}")
    if payload.get('ack_progress_evidence_policy') != 'current_wait_authority_only':
        raise RouterError('resume role rehydration requires ack_progress_evidence_policy=current_wait_authority_only')
    if 'role_bindings' in payload:
        raise RouterError('rehydrate_role_bindings requires payload.rehydrated_role_bindings; old role_bindings aliases are unsupported')
    raw_records = payload.get('rehydrated_role_bindings')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('rehydrate_role_bindings requires payload.rehydrated_role_bindings list or object')
    replacement_requested = any(
        isinstance(raw, dict)
        and (raw.get('rehydration_result') or raw.get('binding_open_result'))
        == ROLE_BINDING_REHYDRATION_RESULT
        for raw in iterable
    )
    replacement_generation = current_generation + 1 if replacement_requested else current_generation
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each rehydrated role binding record must be an object')
        legacy_record_keys = {
            'host_liveness_status',
            'liveness_decision',
            'bounded_wait_result',
            'bounded_wait_ms',
            'liveness_probe_batch_id',
            'liveness_probe_mode',
            'liveness_probe_started_at',
            'liveness_probe_completed_at',
            'wait_agent_timeout_treated_as_active',
        }
        found_legacy_record_keys = sorted(key for key in legacy_record_keys if key in raw)
        if found_legacy_record_keys:
            raise RouterError(f"rehydrated role binding contains unsupported legacy liveness fields: {', '.join(found_legacy_record_keys)}")
        role = raw.get('role_key')
        if role not in RUNTIME_ROLE_KEYS:
            raise RouterError(f'rehydrated role record has unsupported role_key: {role!r}')
        if role not in contexts:
            raise RouterError(f'rehydrated role record was not requested for current resume: {role!r}')
        if role in records_by_role:
            raise RouterError(f'duplicate rehydrated role record for {role}')
        context = contexts[str(role)]
        old_slot = existing_slots.get(str(role)) or {}
        old_epoch = old_slot.get('role_binding_epoch')
        role_epoch = int(old_epoch) if isinstance(old_epoch, int) else 0
        old_generation = old_slot.get('role_binding_generation')
        continuity_generation = (
            int(old_generation)
            if isinstance(old_generation, int) and old_generation > 0
            else current_generation
        )
        agent_id = raw.get('agent_id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f'{role} requires a non-empty live resume agent_id')
        if raw.get('model_policy') != ROLE_BINDING_MODEL_POLICY:
            raise RouterError(f'{role} requires model_policy={ROLE_BINDING_MODEL_POLICY}')
        if raw.get('reasoning_effort_policy') != ROLE_BINDING_REASONING_EFFORT_POLICY:
            raise RouterError(f'{role} requires reasoning_effort_policy={ROLE_BINDING_REASONING_EFFORT_POLICY}')
        result = raw.get('rehydration_result') or raw.get('binding_open_result')
        if result not in RESUME_ROLE_BINDING_RESULTS:
            raise RouterError(f'{role} requires resume rehydration result')
        if raw.get('role_surface_addressable') is not True:
            raise RouterError(f'{role} requires role_surface_addressable=true')
        binding_decision = str(raw.get('current_run_binding_decision') or '')
        if binding_decision not in ROLE_BINDING_CURRENT_RUN_DECISIONS:
            raise RouterError(f'{role} requires current_run_binding_decision')
        if raw.get('resume_agent_attempted') is not True:
            raise RouterError(f'{role} requires resume_agent_attempted=true')
        if result == ROLE_BINDING_CONTINUITY_RESULT and binding_decision != 'existing_current_agent_reused':
            raise RouterError(f'{role} live continuity requires existing_current_agent_reused')
        if result == ROLE_BINDING_CONTINUITY_RESULT:
            old_agent_id = str(old_slot.get('agent_id') or '').strip()
            if not old_agent_id or agent_id.strip() != old_agent_id:
                raise RouterError(f'{role} live continuity requires the exact current role-binding agent')
        if result == ROLE_BINDING_REHYDRATION_RESULT and binding_decision != 'current_run_replacement_opened':
            raise RouterError(f'{role} replacement rehydration requires current_run_replacement_opened')
        if (
            result == ROLE_BINDING_REHYDRATION_RESULT
            and isinstance(old_slot.get('agent_id'), str)
            and agent_id.strip() == str(old_slot.get('agent_id')).strip()
        ):
            raise RouterError(f'{role} replacement rehydration requires a new role-binding agent')
        if raw.get('rehydrated_for_run_id') != run_state['run_id']:
            raise RouterError(f"{role} must be rehydrated_for_run_id={run_state['run_id']}")
        if raw.get('rehydrated_after_resume_tick_id') != resume_tick_id:
            raise RouterError(f'{role} must be rehydrated_after_resume_tick_id={resume_tick_id}')
        rehydrated_after_state_loaded = raw.get('rehydrated_after_resume_state_loaded')
        replacement_opened_after_state_loaded = raw.get('replacement_opened_after_resume_state_loaded')
        if rehydrated_after_state_loaded is not True:
            raise RouterError(f'{role} must be rehydrated_after_resume_state_loaded=true')
        if result == ROLE_BINDING_REHYDRATION_RESULT and replacement_opened_after_state_loaded is not True:
            raise RouterError(f'{role} replacement rehydration requires replacement_opened_after_resume_state_loaded=true')
        if raw.get('core_prompt_path') != context['core_prompt_path'] or raw.get('core_prompt_hash') != context['core_prompt_hash']:
            raise RouterError(f'{role} core prompt identity mismatch')
        memory_status = context['role_memory_status']
        if memory_status == 'available':
            if raw.get('memory_packet_path') != context['memory_packet_path']:
                raise RouterError(f'{role} memory packet path mismatch')
            if raw.get('memory_packet_hash') != context['memory_packet_hash']:
                raise RouterError(f'{role} memory packet hash mismatch')
            if raw.get('memory_seeded_from_current_run') is not True:
                raise RouterError(f'{role} must be seeded from current-run role memory')
        else:
            if raw.get('memory_missing_acknowledged') is not True:
                raise RouterError(f'{role} missing role memory must be acknowledged')
            if raw.get('replacement_seeded_from_common_run_context') is not True:
                raise RouterError(f'{role} replacement must be seeded from common current-run context')
        if role == 'project_manager' and raw.get('pm_resume_context_delivered') is not True:
            raise RouterError('project_manager resume rehydration requires PM context delivery')
        record_generation = (
            replacement_generation
            if result == ROLE_BINDING_REHYDRATION_RESULT
            else continuity_generation
        )
        records_by_role[str(role)] = {'role_key': str(role), 'status': 'live_agent_rehydrated', 'agent_id': agent_id.strip(), 'model_policy': ROLE_BINDING_MODEL_POLICY, 'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY, 'rehydration_result': str(result), 'role_surface_addressable': True, 'current_run_binding_decision': binding_decision, 'resume_agent_attempted': True, 'ack_progress_evidence_policy': 'current_wait_authority_only', 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': resume_tick_id, 'rehydrated_after_resume_state_loaded': True, 'replacement_opened_after_resume_state_loaded': result == ROLE_BINDING_REHYDRATION_RESULT, 'role_binding_generation': record_generation, 'role_binding_epoch': role_epoch + (1 if result == ROLE_BINDING_REHYDRATION_RESULT or agent_id.strip() != str(old_slot.get('agent_id') or '') else 0), 'superseded_agent_ids': [str(old_slot.get('agent_id'))] if result == ROLE_BINDING_REHYDRATION_RESULT and isinstance(old_slot.get('agent_id'), str) and (old_slot.get('agent_id') != agent_id.strip()) else [], 'role_memory_status': memory_status, 'memory_packet_path': context['memory_packet_path'], 'memory_packet_hash': context['memory_packet_hash'], 'core_prompt_path': context['core_prompt_path'], 'core_prompt_hash': context['core_prompt_hash'], 'memory_seeded_from_current_run': memory_status == 'available', 'replacement_seeded_from_common_run_context': memory_status != 'available', 'pm_resume_context_delivered': role == 'project_manager', 'recorded_at': utc_now()}
    expected_roles = list(contexts.keys())
    missing = [role for role in expected_roles if role not in records_by_role]
    if missing:
        raise RouterError(f"missing rehydrated live role binding records: {', '.join(missing)}")
    return [records_by_role[role] for role in expected_roles]

__all__ = (
    '_resume_role_rehydration_action_extra',
    '_normalize_resume_role_agent_records',
)
