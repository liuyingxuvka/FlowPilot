"""controller boundary confirmation records helpers for ``flowpilot_router_startup_fact_boundary``.

This child module is imported by the public facade and keeps
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


OWNER_MODULE = 'flowpilot_router_startup_fact_boundary'

def _controller_boundary_confirmation_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'startup' / 'controller_boundary_confirmation.json'

def _run_manifest_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    manifest_path = run_root / 'runtime_kit' / 'manifest.json'
    if manifest_path.exists():
        return manifest_path
    return runtime_kit_source() / 'manifest.json'

def _controller_boundary_sources(router: ModuleType, run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    manifest_path = router._run_manifest_path(run_root)
    manifest = read_json(manifest_path)
    if manifest.get('schema_version') != PROMPT_MANIFEST_SCHEMA:
        raise RouterError('invalid prompt manifest schema')
    controller_core = manifest_card(manifest, 'controller.core')
    card_path = manifest_path.parent / str(controller_core['path'])
    if not card_path.exists():
        raise RouterError('controller.core card path is missing')
    policy = manifest.get('controller_policy')
    if not isinstance(policy, dict):
        raise RouterError('prompt manifest controller_policy must be an object')
    return {'manifest': manifest, 'manifest_path': manifest_path, 'manifest_hash': packet_runtime.sha256_file(manifest_path), 'controller_core_card': controller_core, 'controller_core_path': card_path, 'controller_core_hash': packet_runtime.sha256_file(card_path), 'controller_policy': policy, 'controller_policy_hash': _json_sha256(policy)}

def _controller_boundary_constraints(router: ModuleType) -> dict[str, Any]:
    _bind_router(router)
    return role_output_runtime.controller_boundary_constraints()

def _pm_reset_boundary_confirmed(router: ModuleType, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    return bool(flags.get('controller_role_confirmed') and flags.get('pm_controller_reset_card_delivered') and flags.get('pm_controller_reset_decision_returned'))

def _controller_boundary_confirmation_body(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    del run_root
    try:
        return role_output_runtime.build_controller_boundary_confirmation_body(project_root, run_id=str(run_state['run_id']))
    except role_output_runtime.RoleOutputRuntimeError as exc:
        raise RouterError(str(exc)) from exc

def _controller_boundary_runtime_evidence_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, confirmation_path: Path, confirmation_hash: str) -> dict[str, Any] | None:
    _bind_router(router)
    del run_root
    try:
        envelope = role_output_runtime.runtime_envelope_for_body(project_root, output_type=CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, body_path=confirmation_path, body_hash=confirmation_hash, run_id=str(run_state.get('run_id') or '') or None)
        if not isinstance(envelope, dict):
            return None
        if envelope.get('output_contract_id') != CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID:
            return None
        if envelope.get('from_role') != 'controller':
            return None
        receipt = role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
    except role_output_runtime.RoleOutputRuntimeError:
        return None
    if receipt.get('role') != 'controller':
        return None
    if receipt.get('output_type') != CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE:
        return None
    return {'envelope': envelope, 'receipt': receipt}

def _write_controller_boundary_confirmation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, controller_agent_id: str | None=None, action_id: str | None=None, source_action_id: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if not run_state.get('flags', {}).get('controller_core_loaded'):
        raise RouterError('controller core must be loaded before Controller boundary confirmation')
    confirmation_path = router._controller_boundary_confirmation_path(run_root)
    try:
        envelope = role_output_runtime.submit_controller_boundary_confirmation(project_root, agent_id=controller_agent_id or CONTROLLER_RUNTIME_HELPER_AGENT_ID, run_id=str(run_state['run_id']), action_id=action_id, source_action_id=source_action_id, output_path=confirmation_path)
    except role_output_runtime.RoleOutputRuntimeError as exc:
        raise RouterError(str(exc)) from exc
    runtime_receipt = role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
    confirmation = read_json(confirmation_path)
    confirmation_hash = packet_runtime.sha256_file(confirmation_path)
    return {'path': project_relative(project_root, confirmation_path), 'sha256': confirmation_hash, 'controller_core_path': confirmation['controller_core_path'], 'controller_core_sha256': confirmation['controller_core_sha256'], 'controller_policy_sha256': confirmation['controller_policy_sha256'], 'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'role_output_envelope': envelope, 'role_output_runtime_receipt_path': runtime_receipt.get('body_path') and (envelope.get('runtime_receipt_ref') or {}).get('path'), 'role_output_runtime_receipt_hash': runtime_receipt.get('body_hash') and (envelope.get('runtime_receipt_ref') or {}).get('hash')}

def _record_controller_boundary_confirmation_from_core_load(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], action: dict[str, Any], receipt_payload: dict[str, Any] | None, *, source: str) -> dict[str, Any]:
    _bind_router(router)
    if not run_state.get('flags', {}).get('controller_core_loaded'):
        raise RouterError('Controller boundary confirmation requires loaded controller.core')
    action_id = str(action.get('controller_action_id') or action.get('action_id') or '').strip()
    source_action_id = str(action.get('action_id') or action_id or 'load_controller_core')
    context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    if context is None:
        confirmation = router._write_controller_boundary_confirmation(project_root, run_root, run_state, controller_agent_id=CONTROLLER_RUNTIME_HELPER_AGENT_ID, action_id=action_id or None, source_action_id=source_action_id)
    else:
        confirmation = {'path': project_relative(project_root, context['path']), 'sha256': context['sha256'], 'controller_core_path': context['confirmation'].get('controller_core_path'), 'controller_core_sha256': context['confirmation'].get('controller_core_sha256'), 'controller_policy_sha256': context['confirmation'].get('controller_policy_sha256'), 'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'role_output_envelope': context.get('role_output_envelope'), 'role_output_runtime_receipt_path': context.get('role_output_envelope', {}).get('runtime_receipt_ref', {}).get('path') if isinstance(context.get('role_output_envelope'), dict) else None, 'role_output_runtime_receipt_hash': context.get('role_output_envelope', {}).get('runtime_receipt_ref', {}).get('hash') if isinstance(context.get('role_output_envelope'), dict) else None}
    pending_action = dict(action)
    pending_action.setdefault('action_type', 'load_controller_core')
    pending_action.setdefault('postcondition', 'controller_role_confirmed')
    if action_id:
        pending_action.setdefault('controller_action_id', action_id)
        pending_action.setdefault('controller_receipt_path', project_relative(project_root, _controller_receipt_path(run_root, action_id)))
    applied = _sync_controller_boundary_confirmation_from_artifact(project_root, run_root, run_state, pending_action, receipt_payload or {'controller_action_completed': True, 'controller_boundary_confirmation_source': 'load_controller_core'}, source=source)
    if not applied.get('applied'):
        raise RouterError(f"Controller boundary confirmation was not reconciled during core load: {applied.get('reason')}")
    applied['controller_boundary_confirmation'] = confirmation
    applied['controller_boundary_confirmation_owned_by'] = 'load_controller_core'
    return applied

def _controller_boundary_confirmation_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    confirmation_path = router._controller_boundary_confirmation_path(run_root)
    if not confirmation_path.exists():
        return None
    confirmation = read_json_if_exists(confirmation_path)
    if confirmation.get('schema_version') != CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA:
        return None
    if confirmation.get('run_id') != run_state.get('run_id'):
        return None
    if confirmation.get('event') != 'controller_role_confirmed_from_router_core':
        return None
    if confirmation.get('confirmed_by_role') != 'controller':
        return None
    if confirmation.get('router_owned_confirmation') is not True:
        return None
    constraints = confirmation.get('boundary_constraints')
    if constraints != router._controller_boundary_constraints():
        return None
    sources = router._controller_boundary_sources(run_root)
    if confirmation.get('controller_core_sha256') != sources['controller_core_hash']:
        return None
    if confirmation.get('manifest_sha256') != sources['manifest_hash']:
        return None
    if confirmation.get('controller_policy_sha256') != sources['controller_policy_hash']:
        return None
    if confirmation.get('sealed_body_reads_allowed') is not False:
        return None
    confirmation_hash = packet_runtime.sha256_file(confirmation_path)
    runtime_context = router._controller_boundary_runtime_evidence_context(project_root, run_root, run_state, confirmation_path=confirmation_path, confirmation_hash=confirmation_hash)
    if runtime_context is None:
        return None
    return {'path': confirmation_path, 'sha256': confirmation_hash, 'confirmation': confirmation, 'role_output_envelope': runtime_context['envelope'], 'role_output_runtime_receipt': runtime_context['receipt']}

def _next_controller_boundary_confirmation_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_core_loaded'):
        return None
    if flags.get('controller_role_confirmed') and router._controller_boundary_confirmation_context(project_root, run_root, run_state) is not None:
        return None
    if router._controller_action_open_for(run_root, action_type='confirm_controller_core_boundary', postcondition='controller_role_confirmed'):
        return None
    if router._pm_reset_boundary_confirmed(run_state):
        return None
    if not flags.get('controller_boundary_recovery_requested'):
        return None
    sources = router._controller_boundary_sources(run_root)
    return make_action(action_type='confirm_controller_core_boundary', actor='controller', label='controller_role_confirmed_from_router_core', summary='Controller records a router-owned confirmation that controller.core is the active boundary authority.', allowed_reads=[project_relative(project_root, sources['manifest_path']), project_relative(project_root, sources['controller_core_path'])], allowed_writes=[project_relative(project_root, router._controller_boundary_confirmation_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'controller_role_confirmed', 'controller_boundary_confirmation_schema': CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA, 'controller_core_card_id': 'controller.core', 'runtime_output_contract': {'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'required_role': 'controller', 'controller_visibility': 'role_output_envelope_only', 'runtime_command': 'flowpilot_runtime.py submit-controller-boundary-confirmation', 'requires_runtime_receipt': True, 'controller_must_not_handwrite_deliverable': True, 'controller_may_read_sealed_bodies': False, 'controller_may_approve_gates': False, 'controller_may_mutate_route': False}, 'sealed_body_reads_allowed': False, 'controller_may_create_project_evidence': False})

__all__ = (
    '_controller_boundary_confirmation_path',
    '_run_manifest_path',
    '_controller_boundary_sources',
    '_controller_boundary_constraints',
    '_pm_reset_boundary_confirmed',
    '_controller_boundary_confirmation_body',
    '_controller_boundary_runtime_evidence_context',
    '_write_controller_boundary_confirmation',
    '_record_controller_boundary_confirmation_from_core_load',
    '_controller_boundary_confirmation_context',
    '_next_controller_boundary_confirmation_action',
)

_LOCAL_NAMES = set(globals())
