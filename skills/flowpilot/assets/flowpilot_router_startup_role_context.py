"""Startup owner helpers extracted from ``flowpilot_router_startup_flow``.

This module is part of the startup StructureMesh split. It is bound to the
router skeleton before execution so cross-owner transitional lookups stay
explicit while startup behavior is owned by smaller modules.
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

def _role_spawn_action_extra(router: ModuleType, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    answers = state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {}
    mode = answers.get('runtime_role_assistances')
    extra: dict[str, Any] = {'runtime_role_assistance_mode': mode, 'role_keys': list(RUNTIME_ROLE_KEYS), 'background_role_agent_model_policy': {'model_policy': ROLE_BINDING_MODEL_POLICY, 'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': ROLE_BINDING_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'applies_to': ['startup_live_role_binding', 'heartbeat_resume_rehydration', 'manual_resume_rehydration', 'missing_role_replacement']}}
    if mode == 'allow':
        extra.update({'requires_payload': 'role_bindings', 'requires_host_role_binding': True, 'role_binding_open_policy': 'open_runtime_required_role_bindings_before_controller_receipt', 'payload_contract': _role_slots_payload_contract(), 'role_spawn_request': [{'role_key': role, 'model_policy': ROLE_BINDING_MODEL_POLICY, 'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': ROLE_BINDING_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'binding_open_result': ROLE_BINDING_OPEN_RESULT, 'opened_for_run_id': state.get('run_id'), 'opened_after_startup_answers': True} for role in RUNTIME_ROLE_KEYS]})
    elif mode == 'single-agent':
        extra.update({'requires_host_role_binding': False, 'single_agent_continuity_authorized': True})
    return extra

def _normalize_role_agent_records(router: ModuleType, state: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = state.get('startup_answers') if isinstance(state.get('startup_answers'), dict) else {}
    mode = answers.get('runtime_role_assistances')
    run_id = str(state.get('run_id') or '')
    if mode == 'single-agent':
        return [{'role_key': role, 'status': 'single_agent_continuity_authorized', 'agent_id': None, 'binding_open_result': 'not_requested_single_agent_continuity', 'fallback_authorized_by_startup_answer': True, 'recorded_at': utc_now()} for role in RUNTIME_ROLE_KEYS]
    if mode != 'allow':
        raise RouterError('cannot start roles before runtime_role_assistances startup answer is recorded')
    raw_records = payload.get('role_bindings')
    if isinstance(raw_records, dict):
        iterable = list(raw_records.values())
    elif isinstance(raw_records, list):
        iterable = raw_records
    else:
        raise RouterError('start_role_slots requires payload.role_bindings list or object')
    if payload.get('runtime_role_assistance_capability_status') != 'available':
        raise RouterError('live role bindings require runtime_role_assistance_capability_status=available')
    records_by_role: dict[str, dict[str, Any]] = {}
    for raw in iterable:
        if not isinstance(raw, dict):
            raise RouterError('each role-binding record must be an object')
        role = raw.get('role_key')
        if role not in RUNTIME_ROLE_KEYS:
            raise RouterError(f'role-binding record has unsupported role_key: {role!r}')
        if role in records_by_role:
            raise RouterError(f'duplicate role-binding record for {role}')
        agent_id = raw.get('agent_id')
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise RouterError(f'{role} requires a non-empty current agent_id')
        if raw.get('model_policy') != ROLE_BINDING_MODEL_POLICY:
            raise RouterError(f'{role} requires model_policy={ROLE_BINDING_MODEL_POLICY}')
        if raw.get('reasoning_effort_policy') != ROLE_BINDING_REASONING_EFFORT_POLICY:
            raise RouterError(f'{role} requires reasoning_effort_policy={ROLE_BINDING_REASONING_EFFORT_POLICY}')
        if raw.get('binding_open_result') != ROLE_BINDING_OPEN_RESULT:
            raise RouterError(f'{role} requires binding_open_result=opened_for_current_task')
        if raw.get('opened_after_startup_answers') is not True:
            raise RouterError(f'{role} must be opened_after_startup_answers=true')
        if raw.get('opened_for_run_id') != run_id:
            raise RouterError(f'{role} must be opened_for_run_id={run_id}')
        host_role_binding_receipt = raw.get('host_role_binding_receipt')
        if host_role_binding_receipt is not None:
            if not isinstance(host_role_binding_receipt, dict):
                raise RouterError(f'{role} host_role_binding_receipt must be an object')
            if host_role_binding_receipt.get('source_kind') != 'host_receipt':
                raise RouterError(f'{role} host_role_binding_receipt requires source_kind=host_receipt')
            if host_role_binding_receipt.get('opened_for_run_id') != run_id:
                raise RouterError(f'{role} host_role_binding_receipt opened_for_run_id mismatch')
            if host_role_binding_receipt.get('role_key') != role:
                raise RouterError(f'{role} host_role_binding_receipt role_key mismatch')
            if host_role_binding_receipt.get('agent_id') != agent_id:
                raise RouterError(f'{role} host_role_binding_receipt agent_id mismatch')
        records_by_role[str(role)] = {'role_key': str(role), 'status': 'live_agent_started', 'agent_id': agent_id.strip(), 'model_policy': ROLE_BINDING_MODEL_POLICY, 'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY, 'binding_open_result': ROLE_BINDING_OPEN_RESULT, 'opened_for_run_id': run_id, 'opened_after_startup_answers': True, 'role_binding_generation': 1, 'role_binding_epoch': 1, **({'host_role_binding_receipt': host_role_binding_receipt} if isinstance(host_role_binding_receipt, dict) else {}), 'recorded_at': utc_now()}
    missing = [role for role in RUNTIME_ROLE_KEYS if role not in records_by_role]
    if missing:
        raise RouterError(f"missing live role-binding records: {', '.join(missing)}")
    return [records_by_role[role] for role in RUNTIME_ROLE_KEYS]

def _latest_resume_tick_id(router: ModuleType, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    ticks = run_state.get('heartbeat_ticks') if isinstance(run_state.get('heartbeat_ticks'), list) else []
    for tick in reversed(ticks):
        if isinstance(tick, dict) and tick.get('tick_id'):
            return str(tick['tick_id'])
    return 'manual-resume'

def _role_core_prompt_path(router: ModuleType, run_root: Path, role: str) -> Path:
    _bind_router(router)
    return run_root / 'runtime_kit' / 'cards' / 'roles' / f'{role}.md'

def _role_memory_path(router: ModuleType, run_root: Path, role: str) -> Path:
    _bind_router(router)
    return run_root / 'role_binding_memory' / f'{role}.json'

def _path_hash(router: ModuleType, path: Path) -> str | None:
    _bind_router(router)
    if not path.exists() or not path.is_file():
        return None
    return packet_runtime.sha256_file(path)

def _role_core_prompt_delivery_payload(router: ModuleType, project_root: Path, run_root: Path, run_id: str, *, source_action: str) -> dict[str, Any]:
    _bind_router(router)
    role_cards: dict[str, str] = {}
    role_card_hashes: dict[str, str] = {}
    for role in ROLE_CARD_KEYS:
        card_path = router._role_core_prompt_path(run_root, role)
        if not card_path.exists():
            raise RouterError(f'role core prompt card is missing for {role}')
        role_cards[role] = card_path.relative_to(run_root).as_posix()
        role_card_hashes[role] = packet_runtime.sha256_file(card_path)
    return {'schema_version': 'flowpilot.role_core_prompt_delivery.v1', 'run_id': run_id, 'source': 'copied_runtime_kit', 'source_action': source_action, 'delivery_mode': 'same_action_with_role_start' if source_action == 'start_role_slots' else 'recovery_action', 'role_cards': role_cards, 'role_card_hashes': role_card_hashes, 'delivered_at': utc_now()}

def _resume_role_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], role: str) -> dict[str, Any]:
    _bind_router(router)
    memory_path = router._role_memory_path(run_root, role)
    core_path = router._role_core_prompt_path(run_root, role)
    common_context = {'resume_reentry': project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'packet_ledger': project_relative(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), 'role_io_protocol_ledger': project_relative(project_root, _role_io_protocol_ledger_path(run_root)), 'role_binding_ledger': project_relative(project_root, run_root / 'role_binding_ledger.json'), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root)), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'display_plan': project_relative(project_root, router._display_plan_path(run_root))}
    context = {'role_key': role, 'required_rehydration_result': 'conditional_on_host_liveness', 'active_liveness_rehydration_result': ROLE_BINDING_CONTINUITY_RESULT, 'replacement_rehydration_result': ROLE_BINDING_REHYDRATION_RESULT, 'allowed_rehydration_results': sorted(RESUME_ROLE_BINDING_RESULTS), 'model_policy': ROLE_BINDING_MODEL_POLICY, 'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': ROLE_BINDING_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False, 'rehydrated_for_run_id': run_state['run_id'], 'rehydrated_after_resume_tick_id': router._latest_resume_tick_id(run_state), 'rehydrated_after_resume_state_loaded': True, 'replacement_opened_after_resume_state_loaded': False, 'replacement_opened_after_resume_state_loaded_required_if_replaced': True, 'core_prompt_path': project_relative(project_root, core_path), 'core_prompt_hash': router._path_hash(core_path), 'memory_packet_path': project_relative(project_root, memory_path), 'memory_packet_hash': router._path_hash(memory_path), 'role_memory_status': 'available' if memory_path.exists() else 'missing', 'common_context_paths': common_context, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False}
    if role == 'project_manager':
        context['pm_resume_context_required'] = True
        context['pm_resume_context_paths'] = {'resume_reentry': common_context['resume_reentry'], 'execution_frontier': common_context['execution_frontier'], 'packet_ledger': common_context['packet_ledger'], 'prompt_delivery_ledger': common_context['prompt_delivery_ledger'], 'role_binding_ledger': common_context['role_binding_ledger'], 'role_binding_memory': project_relative(project_root, run_root / 'role_binding_memory'), 'route_history_index': common_context['route_history_index'], 'pm_prior_path_context': common_context['pm_prior_path_context'], 'display_plan': common_context['display_plan']}
    return context

def _resume_role_contexts(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    return [router._resume_role_context(project_root, run_root, run_state, role) for role in RUNTIME_ROLE_KEYS]

def _resume_liveness_probe_batch_id(router: ModuleType, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    return f"resume-liveness-{run_state['run_id']}-{router._latest_resume_tick_id(run_state)}"

def _role_recovery_dir(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'role_recovery'

def _role_recovery_latest_transaction_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._role_recovery_dir(run_root) / 'latest_transaction.json'

def _role_recovery_state_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._role_recovery_dir(run_root) / 'state_load.json'

def _role_recovery_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'continuation' / 'role_recovery_report.json'

def _role_recovery_target_roles(router: ModuleType, raw_roles: object, *, default_all: bool=False) -> list[str]:
    _bind_router(router)
    if default_all:
        return list(RUNTIME_ROLE_KEYS)
    if isinstance(raw_roles, str):
        roles = [raw_roles]
    elif isinstance(raw_roles, list):
        roles = [str(role) for role in raw_roles]
    else:
        roles = []
    normalized: list[str] = []
    for role in roles:
        role_key = str(role).strip()
        if role_key not in RUNTIME_ROLE_KEYS:
            raise RouterError(f'role recovery target has unsupported role_key: {role_key!r}')
        if role_key not in normalized:
            normalized.append(role_key)
    if not normalized:
        raise RouterError('role recovery requires at least one target_role_key')
    return normalized

def _latest_role_recovery_transaction(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    return read_json_if_exists(router._role_recovery_latest_transaction_path(run_root))

def _role_recovery_ready_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    report_path = router._role_recovery_report_path(run_root)
    report = read_json_if_exists(report_path)
    transaction = router._latest_role_recovery_transaction(run_root)
    if report.get('schema_version') != ROLE_RECOVERY_REPORT_SCHEMA:
        return None
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        return None
    if str(report.get('run_id') or '') != str(run_state.get('run_id') or ''):
        return None
    if str(report.get('transaction_id') or '') != str(transaction.get('transaction_id') or ''):
        return None
    report_targets = [str(role) for role in report.get('target_role_keys') or []]
    transaction_targets = [str(role) for role in transaction.get('target_role_keys') or []]
    if report_targets != transaction_targets:
        return None
    if report.get('required_role_bindings_ready') is not True or report.get('environment_blocked') is True:
        return None
    runtime_roles_path = run_root / 'role_binding_ledger.json'
    role_binding = read_json_if_exists(runtime_roles_path)
    slots = role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []
    ready_agents: dict[str, str] = {}
    for slot in slots:
        if not isinstance(slot, dict):
            continue
        role = str(slot.get('role_key') or '')
        agent_id = slot.get('agent_id')
        if role in transaction_targets and str(slot.get('last_role_recovery_transaction_id') or '') != str(transaction.get('transaction_id') or ''):
            continue
        if role in RUNTIME_ROLE_KEYS and isinstance(agent_id, str) and agent_id.strip() and router._role_slot_has_current_host_liveness(slot):
            ready_agents[role] = agent_id.strip()
    missing_roles = [role for role in RUNTIME_ROLE_KEYS if role not in ready_agents]
    if missing_roles:
        return None
    return {'report': report, 'report_path': report_path, 'report_relpath': project_relative(project_root, report_path), 'runtime_roles_path': runtime_roles_path, 'runtime_roles_relpath': project_relative(project_root, runtime_roles_path), 'ready_role_keys': list(RUNTIME_ROLE_KEYS), 'ready_agents': ready_agents, 'latest_transaction': transaction, 'target_role_keys': transaction_targets}

__all__ = (
    '_role_spawn_action_extra',
    '_normalize_role_agent_records',
    '_latest_resume_tick_id',
    '_role_core_prompt_path',
    '_role_memory_path',
    '_path_hash',
    '_role_core_prompt_delivery_payload',
    '_resume_role_context',
    '_resume_role_contexts',
    '_resume_liveness_probe_batch_id',
    '_role_recovery_dir',
    '_role_recovery_latest_transaction_path',
    '_role_recovery_state_path',
    '_role_recovery_report_path',
    '_role_recovery_target_roles',
    '_latest_role_recovery_transaction',
    '_role_recovery_ready_context',
)

_LOCAL_NAMES = set(globals())
