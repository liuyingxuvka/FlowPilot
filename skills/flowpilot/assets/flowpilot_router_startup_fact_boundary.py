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


OWNER_MODULE = 'flowpilot_router_startup_fact_boundary'

def _startup_fact_checks(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    required_answer_ids = {item['id'] for item in STARTUP_QUESTIONS}
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json')
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json')
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    role_slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    role_keys = {slot.get('role_key') for slot in role_slots if isinstance(slot, dict)}
    live_role_slots_current = role_keys == set(CREW_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'live_agent_started' and isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) and (slot.get('model_policy') == BACKGROUND_ROLE_MODEL_POLICY) and (slot.get('reasoning_effort_policy') == BACKGROUND_ROLE_REASONING_EFFORT_POLICY) and (slot.get('spawn_result') == ROLE_AGENT_SPAWN_RESULT) and (slot.get('spawned_for_run_id') == run_state.get('run_id')) and (slot.get('spawned_after_startup_answers') is True) for slot in role_slots))
    single_agent_slots_current = role_keys == set(CREW_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'single_agent_continuity_authorized' and (slot.get('agent_id') is None) and (slot.get('fallback_authorized_by_startup_answer') is True) for slot in role_slots))
    indexed_runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    scheduled_requested = router._scheduled_continuation_requested(answers)
    old_control_paths = [project_root / '.flowpilot' / 'state.json', project_root / '.flowpilot' / 'capabilities.json', project_root / '.flowpilot' / 'execution_frontier.json', project_root / '.flowpilot' / 'routes']
    boundary_context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    return {'controller_boundary_confirmed': boundary_context is not None or router._legacy_pm_reset_boundary_confirmed(run_state), 'startup_intake_record_current': startup_intake_context is not None, 'startup_intake_receipt_envelope_hash_current': bool(startup_intake_context and startup_intake_context.get('receipt_envelope_body_hash_current')), 'reviewer_live_review_uses_startup_intake_record': bool(startup_intake_context and startup_intake_context.get('reviewer_must_not_use_chat_history')), 'startup_answers_complete': required_answer_ids.issubset({key for key, value in answers.items() if value}), 'current_pointer_matches_run': current.get('current_run_id') == run_state.get('run_id') and current.get('current_run_root') == run_state.get('run_root'), 'index_points_to_run': index.get('current_run_id') == run_state.get('run_id') and any((isinstance(item, dict) and item.get('run_id') == run_state.get('run_id') for item in indexed_runs)), 'crew_slots_current': role_keys == set(CREW_ROLE_KEYS), 'live_background_agents_current_if_allowed': live_role_slots_current if answers.get('background_agents') == 'allow' else True, 'single_agent_continuity_current_if_selected': single_agent_slots_current if answers.get('background_agents') == 'single-agent' else True, 'continuation_mode_recorded': bool(answers.get('scheduled_continuation')), 'continuation_binding_current': continuation_binding.get('run_id') == run_state.get('run_id') and continuation_binding.get('schema_version') == 'flowpilot.continuation_binding.v1', 'scheduled_heartbeat_verified_if_requested': continuation_binding.get('heartbeat_active') is True and continuation_binding.get('route_heartbeat_interval_minutes') == 1 and bool(continuation_binding.get('host_automation_id')) and (continuation_binding.get('host_automation_verified') is True) if scheduled_requested else continuation_binding.get('mode') == 'manual_resume', 'display_surface_recorded': bool(answers.get('display_surface')), 'old_state_quarantined': not any((path.exists() for path in old_control_paths))}

def _startup_intake_record_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    record_path = run_root / 'startup_intake' / 'startup_intake_record.json'
    if not record_path.exists():
        return None
    record = read_json_if_exists(record_path)
    if record.get('schema_version') != STARTUP_INTAKE_RECORD_SCHEMA:
        return None
    if record.get('run_id') != run_state.get('run_id'):
        return None
    if record.get('status') != 'confirmed':
        return None
    if record.get('controller_may_read_body') is not False or record.get('body_text_included') is not False:
        return None
    try:
        body_path = router._resolve_existing_project_file(project_root, record.get('body_path'), 'startup intake record body')
        receipt_path = router._resolve_existing_project_file(project_root, record.get('receipt_path'), 'startup intake record receipt')
        envelope_path = router._resolve_existing_project_file(project_root, record.get('envelope_path'), 'startup intake record envelope')
        result_path = router._resolve_existing_project_file(project_root, record.get('result_path'), 'startup intake record result')
    except RouterError:
        return None
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != record.get('body_hash'):
        return None
    receipt = read_json_if_exists(receipt_path)
    envelope = read_json_if_exists(envelope_path)
    result = read_json_if_exists(result_path)
    receipt_envelope_body_hash_current = receipt.get('schema_version') == STARTUP_INTAKE_RECEIPT_SCHEMA and envelope.get('schema_version') == STARTUP_INTAKE_ENVELOPE_SCHEMA and (result.get('schema_version') == STARTUP_INTAKE_RESULT_SCHEMA) and (receipt.get('body_hash') == body_hash) and (envelope.get('body_hash') == body_hash) and (result.get('body_hash') == body_hash) and (receipt.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (envelope.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (result.get('launch_mode') == STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE) and (receipt.get('headless') is False) and (envelope.get('headless') is False) and (result.get('headless') is False) and (receipt.get('formal_startup_allowed') is True) and (envelope.get('formal_startup_allowed') is True) and (result.get('formal_startup_allowed') is True) and (envelope.get('controller_may_read_body') is False) and (result.get('controller_may_read_body') is False) and (envelope.get('body_text_included') is False) and (result.get('body_text_included') is False)
    return {'record_path': record_path, 'record': record, 'result_path': result_path, 'receipt_path': receipt_path, 'envelope_path': envelope_path, 'body_path': body_path, 'body_hash': body_hash, 'receipt_envelope_body_hash_current': receipt_envelope_body_hash_current, 'reviewer_must_not_use_chat_history': record.get('reviewer_must_not_use_chat_history') is True}

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

def _legacy_pm_reset_boundary_confirmed(router: ModuleType, run_state: dict[str, Any]) -> bool:
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

def _role_slots_have_host_spawn_receipts(router: ModuleType, role_slots: list[dict[str, Any]], run_id: str) -> bool:
    _bind_router(router)
    for slot in role_slots:
        receipt = slot.get('host_spawn_receipt') if isinstance(slot, dict) else None
        if not isinstance(receipt, dict):
            return False
        if receipt.get('source_kind') != 'host_receipt':
            return False
        if receipt.get('spawned_for_run_id') != run_id:
            return False
        if receipt.get('role_key') != slot.get('role_key'):
            return False
        if receipt.get('agent_id') != slot.get('agent_id'):
            return False
    return bool(role_slots)

def _continuation_has_host_bound_automation_receipt(router: ModuleType, continuation_binding: dict[str, Any], run_id: str) -> bool:
    _bind_router(router)
    proof = continuation_binding.get('host_automation_proof')
    if not isinstance(proof, dict):
        return False
    return proof.get('source_kind') == 'host_receipt' and proof.get('run_id') == run_id and (proof.get('host_automation_id') == continuation_binding.get('host_automation_id')) and (proof.get('route_heartbeat_interval_minutes') == 1) and (proof.get('heartbeat_bound_to_current_run') is True)

def _startup_external_fact_requirements(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    crew = read_json_if_exists(run_root / 'crew_ledger.json')
    role_slots = crew.get('role_slots') if isinstance(crew.get('role_slots'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    requirements: list[dict[str, Any]] = []
    if answers.get('background_agents') == 'allow' and (not router._role_slots_have_host_spawn_receipts(role_slots, str(run_state.get('run_id') or ''))):
        requirements.append({'id': 'live_agent_spawn_freshness', 'reason': 'Router validates role-slot shape, run ids, and requested background role intelligence policy, but host spawn freshness and actual model selection need a receipt or reviewer check.', 'self_attested_payload_fields': ['role_agents[].model_policy', 'role_agents[].reasoning_effort_policy', 'role_agents[].spawn_result', 'role_agents[].spawned_after_startup_answers'], 'reviewer_direct_check_required': True})
    if router._scheduled_continuation_requested(answers) and (not router._continuation_has_host_bound_automation_receipt(continuation_binding, str(run_state.get('run_id') or ''))):
        requirements.append({'id': 'heartbeat_host_automation_current_run_binding', 'reason': 'Router validates the heartbeat binding fields, but host_automation_verified=true alone is an AI/host payload claim unless backed by a host receipt.', 'self_attested_payload_fields': ['host_automation_verified', 'host_automation_id'], 'reviewer_direct_check_required': True})
    if answers.get('display_surface') == 'cockpit':
        requirements.append({'id': 'cockpit_or_display_fallback_reality', 'reason': 'Router can record selected display mode and chat fallback, but live Cockpit availability or fallback necessity requires direct review when requested.', 'self_attested_payload_fields': ['display_surface'], 'reviewer_direct_check_required': True})
    return requirements

def _startup_fact_review_ownership(router: ModuleType, computed_checks: dict[str, bool], external_requirements: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    reviewer_ids = {str(item['id']) for item in external_requirements if item.get('id')}
    router_owned = sorted(computed_checks)
    reviewer_owned = sorted(reviewer_ids)
    pm_decision_owned = ['startup_user_answer_authenticity']
    covered = set(router_owned) | set(reviewer_owned) | set(pm_decision_owned)
    known = set(computed_checks) | reviewer_ids | set(pm_decision_owned)
    unowned = sorted(known - covered)
    return {'router_owned_mechanical_checks': router_owned, 'reviewer_owned_external_fact_ids': reviewer_owned, 'pm_decision_owned_unreviewable_fact_ids': pm_decision_owned, 'unowned_fact_ids': unowned, 'all_required_facts_have_owner': not unowned}

def _write_startup_mechanical_audit(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], computed_checks: dict[str, bool]) -> dict[str, Any]:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    proof_path = _router_owned_check_proof_path(audit_path)
    evidence_paths = [run_root / 'startup_answers.json', project_root / '.flowpilot' / 'current.json', project_root / '.flowpilot' / 'index.json', run_root / 'crew_ledger.json', router._continuation_binding_path(run_root), router.run_state_path(run_root)]
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        evidence_paths.extend([startup_intake_context['record_path'], startup_intake_context['result_path'], startup_intake_context['receipt_path'], startup_intake_context['envelope_path'], startup_intake_context['body_path']])
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        evidence_paths.append(boundary_path)
    external_requirements = router._startup_external_fact_requirements(run_root, run_state)
    review_ownership = router._startup_fact_review_ownership(computed_checks, external_requirements)
    audit = {'schema_version': STARTUP_MECHANICAL_AUDIT_SCHEMA, 'run_id': run_state['run_id'], 'check_owner': 'flowpilot_router', 'mechanical_checks': computed_checks, 'mechanical_checks_passed': all(computed_checks.values()), 'router_replacement_scope': 'mechanical_only', 'self_attested_ai_claims_accepted_as_proof': False, 'fact_review_ownership': review_ownership, 'reviewer_required_external_facts': external_requirements, 'router_owned_check_proof_path': project_relative(project_root, proof_path), 'source_paths': [_evidence_path_record(project_root, path) for path in evidence_paths], 'written_at': utc_now()}
    if not review_ownership['all_required_facts_have_owner']:
        raise RouterError('startup fact ownership map left unowned requirements')
    write_json(audit_path, audit)
    proof_record = _write_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path, source_kind='router_computed', evidence_paths=evidence_paths)
    _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    audit['router_owned_check_proof'] = {'path': proof_record['proof_path'], 'schema_version': ROUTER_OWNED_CHECK_PROOF_SCHEMA}
    return audit

def _startup_mechanical_audit_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    if not audit_path.exists():
        return None
    audit = read_json_if_exists(audit_path)
    if audit.get('schema_version') != STARTUP_MECHANICAL_AUDIT_SCHEMA:
        return None
    if audit.get('run_id') != run_state.get('run_id'):
        return None
    try:
        proof = _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    except RouterError:
        return None
    proof_path = _router_owned_check_proof_path(audit_path)
    return {'audit': audit, 'audit_path': audit_path, 'audit_hash': packet_runtime.sha256_file(audit_path), 'proof': proof, 'proof_path': proof_path, 'proof_hash': packet_runtime.sha256_file(proof_path) if proof_path.exists() else None}

def _startup_mechanical_audit_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise RouterError('startup mechanical audit must be written before reviewer startup fact card delivery')
    display_path = run_root / 'display' / 'display_surface.json'
    if not display_path.exists():
        raise RouterError('startup display-surface status must be written before reviewer startup fact card delivery')
    return {'startup_mechanical_audit_path': project_relative(project_root, context['audit_path']), 'startup_mechanical_audit_hash': context['audit_hash'], 'router_owned_check_proof_path': project_relative(project_root, context['proof_path']), 'router_owned_check_proof_hash': context['proof_hash'], 'startup_intake_record_path': router._optional_source_path(project_root, run_root / 'startup_intake' / 'startup_intake_record.json'), 'startup_display_surface_path': project_relative(project_root, display_path), 'startup_display_surface_hash': packet_runtime.sha256_file(display_path), 'reviewer_has_direct_display_evidence': True, 'router_computable_checks_already_enforced': True, 'reviewer_should_not_reprove_router_computable_checks': True, 'reviewer_required_external_facts': context['audit'].get('reviewer_required_external_facts') or [], 'router_replacement_scope': 'mechanical_only'}

def _validate_startup_external_fact_review(router: ModuleType, payload: dict[str, Any], requirements: list[dict[str, Any]], *, startup_mechanical_audit_hash: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if not requirements:
        return {'reviewed_by_role': 'human_like_reviewer', 'reviewer_required_external_fact_count': 0, 'reviewer_checked_requirement_ids': [], 'self_attested_ai_claims_accepted_as_proof': False}
    review = payload.get('external_fact_review')
    if not isinstance(review, dict):
        raise RouterError('startup fact report requires external_fact_review for non-router-checkable facts')
    if review.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('external_fact_review must be reviewed_by_role=human_like_reviewer')
    if startup_mechanical_audit_hash and review.get('router_mechanical_audit_hash') is not None and (review.get('router_mechanical_audit_hash') != startup_mechanical_audit_hash):
        raise RouterError('external_fact_review must reference the current startup mechanical audit hash')
    if review.get('self_attested_ai_claims_accepted_as_proof') is not False:
        raise RouterError('external_fact_review cannot accept self-attested AI claims as proof')
    checked_ids = review.get('reviewer_checked_requirement_ids')
    if not isinstance(checked_ids, list):
        raise RouterError('external_fact_review requires reviewer_checked_requirement_ids list')
    checked = {str(item) for item in checked_ids}
    required = {str(item['id']) for item in requirements if item.get('id')}
    missing = sorted(required - checked)
    if missing:
        raise RouterError(f"external_fact_review missing required checks: {', '.join(missing)}")
    direct_paths = review.get('direct_evidence_paths_checked')
    if not isinstance(direct_paths, list) or not direct_paths:
        raise RouterError('external_fact_review requires direct_evidence_paths_checked')
    return {'reviewed_by_role': 'human_like_reviewer', 'reviewer_required_external_fact_count': len(requirements), 'reviewer_checked_requirement_ids': sorted(checked), 'direct_evidence_paths_checked': direct_paths, 'self_attested_ai_claims_accepted_as_proof': False, 'notes': review.get('notes')}

def _write_startup_fact_report(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    canonical_report_path = run_root / 'startup' / 'startup_fact_report.json'
    envelope = payload.get('_role_output_envelope')
    if isinstance(envelope, dict) and envelope.get('body_path'):
        source_path = resolve_project_path(project_root, str(envelope['body_path']))
        if source_path.resolve() == canonical_report_path.resolve():
            raise RouterError('startup fact source report_path must not be the router canonical startup_fact_report.json')
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('startup fact report must be reviewed_by_role=human_like_reviewer')
    computed_checks = router._startup_fact_checks(project_root, run_root, run_state)
    claimed_checks = payload.get('checks') if isinstance(payload.get('checks'), dict) else {}
    false_claims = [name for name, value in claimed_checks.items() if value is not True]
    passed = payload.get('passed') is True
    if passed and false_claims:
        raise RouterError(f"startup fact report contains failed checks: {', '.join(sorted(false_claims))}")
    blockers = [name for name, ok in computed_checks.items() if not ok]
    if passed and blockers:
        raise RouterError(f"startup facts are not clean: {', '.join(sorted(blockers))}")
    mechanical_context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if mechanical_context is None:
        raise RouterError('startup mechanical audit must be written before reviewer startup fact report')
    mechanical_audit = mechanical_context['audit']
    if mechanical_audit.get('mechanical_checks') != computed_checks:
        raise RouterError('startup mechanical audit is stale; rewrite it before reviewer startup fact report')
    external_fact_review = router._validate_startup_external_fact_review(payload, mechanical_audit['reviewer_required_external_facts'], startup_mechanical_audit_hash=mechanical_context['audit_hash'])
    write_json(canonical_report_path, {'schema_version': 'flowpilot.startup_fact_report.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'passed': passed, 'status': 'pass' if passed else 'findings', 'checks': computed_checks, 'reviewer_claimed_checks': claimed_checks, 'reviewer_reported_blockers': payload.get('blockers') if isinstance(payload.get('blockers'), list) else false_claims or blockers, 'startup_mechanical_audit_path': project_relative(project_root, mechanical_context['audit_path']), 'startup_mechanical_audit_hash': mechanical_context['audit_hash'], 'router_owned_check_proof_path': project_relative(project_root, mechanical_context['proof_path']), 'router_owned_check_proof_hash': mechanical_context['proof_hash'], 'reviewer_required_external_facts': mechanical_audit['reviewer_required_external_facts'], 'external_fact_review': external_fact_review, 'requires_pm_startup_decision': not passed, 'reviewer_directly_blocks_route': False, 'reported_at': utc_now(), **_role_output_envelope_record(payload)})

def _write_startup_activation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('approved_by_role') != 'project_manager':
        raise RouterError('PM startup activation requires approved_by_role=project_manager')
    if payload.get('decision') != 'approved':
        raise RouterError('PM startup activation requires decision=approved')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    fact_report_path = run_root / 'startup' / 'startup_fact_report.json'
    if not fact_report_path.exists():
        raise RouterError('PM startup activation requires reviewer startup_fact_report.json')
    clean_report = fact_report.get('passed') is True and fact_report.get('status') == 'pass'
    approval_basis = 'clean_reviewer_fact_report'
    findings_decision: dict[str, Any] | None = None
    if not clean_report:
        if fact_report.get('status') != 'findings' or fact_report.get('requires_pm_startup_decision') is not True:
            raise RouterError('PM startup activation requires a passing reviewer startup fact report or PM findings decision')
        if payload.get('accepts_startup_findings_with_reason') is not True:
            raise RouterError('PM startup activation from reviewer findings requires accepts_startup_findings_with_reason=true')
        reason = str(payload.get('startup_findings_decision_reason') or '').strip()
        if not reason:
            raise RouterError('PM startup activation from reviewer findings requires startup_findings_decision_reason')
        reviewed_report = payload.get('reviewed_report_path') or project_relative(project_root, fact_report_path)
        if resolve_project_path(project_root, str(reviewed_report)).resolve() != fact_report_path.resolve():
            raise RouterError('PM startup activation reviewed_report_path must reference startup_fact_report.json')
        decision_kind = str(payload.get('startup_findings_decision') or 'waived_with_reason')
        if decision_kind not in {'waived_with_reason', 'unreviewable_requirement_demoted', 'accepted_with_documented_risk'}:
            raise RouterError('PM startup activation startup_findings_decision is invalid')
        approval_basis = 'pm_file_backed_findings_decision'
        findings_decision = {'startup_findings_decision': decision_kind, 'startup_findings_decision_reason': reason, 'reviewed_report_path': project_relative(project_root, fact_report_path), 'reviewed_report_hash': packet_runtime.sha256_file(fact_report_path), 'reviewer_findings_accepted_by_pm': True, 'demoted_unreviewable_requirement_ids': payload.get('demoted_unreviewable_requirement_ids') if isinstance(payload.get('demoted_unreviewable_requirement_ids'), list) else []}
    answers = router._startup_answers_from_run(run_root)
    activation = {'schema_version': 'flowpilot.startup_activation.v1', 'run_id': run_state['run_id'], 'approved_by_role': 'project_manager', 'decision': 'approved', 'background_agents': answers.get('background_agents'), 'scheduled_continuation': answers.get('scheduled_continuation'), 'display_surface': answers.get('display_surface'), 'fact_report_path': project_relative(project_root, fact_report_path), 'approval_basis': approval_basis, 'approved_at': utc_now(), **_role_output_envelope_record(payload)}
    if findings_decision is not None:
        activation['pm_findings_decision'] = findings_decision
    write_json(run_root / 'startup' / 'startup_activation.json', activation)

def _write_startup_repair_request(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('decided_by_role') != 'project_manager':
        raise RouterError('startup repair request requires decided_by_role=project_manager')
    if payload.get('decision') not in {'startup_repair_requested', 'repair_requested'}:
        raise RouterError('startup repair request requires decision=startup_repair_requested')
    target = str(payload.get('target_role_or_system') or '').strip()
    allowed_targets = {'flowpilot_router', 'human_like_reviewer', 'project_manager', 'worker_a', 'worker_b'}
    if target not in allowed_targets:
        raise RouterError(f"startup repair request target_role_or_system must be one of: {', '.join(sorted(allowed_targets))}")
    repair_action = str(payload.get('repair_action') or '').strip()
    if not repair_action:
        raise RouterError('startup repair request requires repair_action')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    if fact_report.get('passed') is True:
        raise RouterError('startup repair request requires a non-passing reviewer startup fact report')
    current_blocked_report_path = run_root / 'startup' / 'startup_fact_report.json'
    if not current_blocked_report_path.exists():
        raise RouterError('startup repair request requires the current non-passing startup_fact_report.json')
    requested_blocked_report = payload.get('blocked_report_path') or project_relative(project_root, current_blocked_report_path)
    requested_blocked_report_path = resolve_project_path(project_root, str(requested_blocked_report))
    if requested_blocked_report_path.resolve() != current_blocked_report_path.resolve():
        raise RouterError('startup repair request blocked_report_path must be the current canonical startup_fact_report.json')
    blocked_report_hash = packet_runtime.sha256_file(current_blocked_report_path)
    envelope = payload.get('_role_output_envelope') if isinstance(payload.get('_role_output_envelope'), dict) else {}
    decision_hash = str(envelope.get('body_hash') or '')
    if not decision_hash:
        raise RouterError('startup repair request requires a file-backed PM decision hash')
    previous_request = run_state.get('startup_repair_request') if isinstance(run_state.get('startup_repair_request'), dict) else {}
    last_decision_hash = str(previous_request.get('decision_hash') or '')
    if last_decision_hash and decision_hash == last_decision_hash:
        raise RouterError('startup repair request repeats the previous PM decision; write a fresh PM decision for the current blocking report')
    startup_repair_cycle = int(run_state.get('startup_repair_cycle') or 0) + 1
    record = {'schema_version': 'flowpilot.startup_repair_request.v1', 'run_id': run_state['run_id'], 'startup_repair_cycle': startup_repair_cycle, 'decided_by_role': 'project_manager', 'decision': 'startup_repair_requested', 'repair_target_kind': payload.get('repair_target_kind') or ('system' if target == 'flowpilot_router' else 'role'), 'target_role_or_system': target, 'repair_action': repair_action, 'blocked_report_path': project_relative(project_root, current_blocked_report_path), 'blocked_report_hash': blocked_report_hash, 'decision_path': envelope.get('body_path'), 'decision_hash': decision_hash, 'resume_event': payload.get('resume_event') or 'reviewer_reports_startup_facts', 'resume_condition': payload.get('resume_condition') or 'targeted startup repair is complete and reviewer writes a fresh startup fact report', 'controller_may_invent_repair': False, 'recorded_at': utc_now(), **_role_output_envelope_record(payload)}
    cycle_path = run_root / 'startup' / f'startup_repair_request.cycle-{startup_repair_cycle:03d}.json'
    write_json(cycle_path, record)
    write_json(run_root / 'startup' / 'startup_repair_request.json', record)
    ledger_path = run_root / 'startup' / 'startup_repair_requests.json'
    ledger = read_json_if_exists(ledger_path)
    entries = ledger.get('entries') if isinstance(ledger.get('entries'), list) else []
    entries.append({'startup_repair_cycle': startup_repair_cycle, 'path': project_relative(project_root, cycle_path), 'blocked_report_path': record['blocked_report_path'], 'blocked_report_hash': blocked_report_hash, 'decision_path': record['decision_path'], 'decision_hash': decision_hash, 'target_role_or_system': target, 'repair_action': repair_action, 'recorded_at': record['recorded_at']})
    write_json(ledger_path, {'schema_version': 'flowpilot.startup_repair_requests.v1', 'run_id': run_state['run_id'], 'entries': entries, 'latest_cycle': startup_repair_cycle, 'updated_at': utc_now()})
    for flag in ('startup_fact_reported', 'pm_startup_activation_card_delivered', 'startup_activation_approved', 'startup_mechanical_audit_written', 'reviewer_startup_fact_check_card_delivered'):
        run_state['flags'][flag] = False
    run_state['startup_repair_cycle'] = startup_repair_cycle
    run_state['startup_repair_request'] = {'path': project_relative(project_root, run_root / 'startup' / 'startup_repair_request.json'), 'cycle_path': project_relative(project_root, cycle_path), 'ledger_path': project_relative(project_root, ledger_path), 'startup_repair_cycle': startup_repair_cycle, 'target_role_or_system': target, 'repair_action': repair_action, 'blocked_report_hash': blocked_report_hash, 'decision_hash': decision_hash, 'resume_event': record['resume_event']}

def _write_startup_protocol_dead_end(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('declared_by_role') != 'project_manager':
        raise RouterError('startup protocol dead-end requires declared_by_role=project_manager')
    if payload.get('decision') != 'protocol_dead_end':
        raise RouterError('startup protocol dead-end requires decision=protocol_dead_end')
    if payload.get('no_legal_repair_path') is not True:
        raise RouterError('startup protocol dead-end requires no_legal_repair_path=true')
    reason = str(payload.get('why_no_existing_path_applies') or '').strip()
    if not reason:
        raise RouterError('startup protocol dead-end requires why_no_existing_path_applies')
    attempted_paths = payload.get('attempted_legal_paths')
    if not isinstance(attempted_paths, list) or not attempted_paths:
        raise RouterError('startup protocol dead-end requires attempted_legal_paths')
    resume_conditions = payload.get('resume_conditions')
    if not isinstance(resume_conditions, list) or not resume_conditions:
        raise RouterError('startup protocol dead-end requires resume_conditions')
    fact_report = read_json_if_exists(run_root / 'startup' / 'startup_fact_report.json')
    if fact_report.get('passed') is True:
        raise RouterError('startup protocol dead-end requires a non-passing reviewer startup fact report')
    dead_end_path = run_root / 'lifecycle' / 'startup_protocol_dead_end.json'
    record = {'schema_version': 'flowpilot.startup_protocol_dead_end.v1', 'run_id': run_state['run_id'], 'declared_by_role': 'project_manager', 'decision': 'protocol_dead_end', 'dead_end_type': payload.get('dead_end_type') or 'startup_block_has_no_protocol_route', 'no_legal_repair_path': True, 'why_no_existing_path_applies': reason, 'attempted_legal_paths': attempted_paths, 'conceptual_repair_direction': payload.get('conceptual_repair_direction'), 'unsafe_to_continue_reason': payload.get('unsafe_to_continue_reason') or reason, 'blocked_report_path': payload.get('blocked_report_path') or project_relative(project_root, run_root / 'startup' / 'startup_fact_report.json'), 'effects': {'freeze_run': True, 'cancel_or_suspend_pending_mail': True, 'prevent_work_beyond_startup': True, 'heartbeat_should_stop': False, 'heartbeat_should_remain_for_resume_or_user_decision': True, **(payload.get('effects') if isinstance(payload.get('effects'), dict) else {})}, 'resume_conditions': resume_conditions, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'declared_at': utc_now(), **_role_output_envelope_record(payload)}
    write_json(dead_end_path, record)
    run_state['flags']['startup_pending_mail_suspended_after_dead_end'] = True
    _write_protocol_dead_end_lifecycle(project_root, run_root, run_state, dead_end_path=dead_end_path, reason=reason)

def _next_controller_boundary_confirmation_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_core_loaded'):
        return None
    if flags.get('controller_role_confirmed') and router._controller_boundary_confirmation_context(project_root, run_root, run_state) is not None:
        return None
    if router._controller_action_open_for(run_root, action_type='confirm_controller_core_boundary', postcondition='controller_role_confirmed'):
        return None
    if router._legacy_pm_reset_boundary_confirmed(run_state):
        return None
    if not flags.get('controller_boundary_recovery_requested'):
        return None
    sources = router._controller_boundary_sources(run_root)
    return make_action(action_type='confirm_controller_core_boundary', actor='controller', label='controller_role_confirmed_from_router_core', summary='Controller records a router-owned confirmation that controller.core is the active boundary authority.', allowed_reads=[project_relative(project_root, sources['manifest_path']), project_relative(project_root, sources['controller_core_path'])], allowed_writes=[project_relative(project_root, router._controller_boundary_confirmation_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'controller_role_confirmed', 'controller_boundary_confirmation_schema': CONTROLLER_BOUNDARY_CONFIRMATION_SCHEMA, 'controller_core_card_id': 'controller.core', 'runtime_output_contract': {'runtime_channel': 'role_output_runtime', 'output_type': CONTROLLER_BOUNDARY_CONFIRMATION_OUTPUT_TYPE, 'output_contract_id': CONTROLLER_BOUNDARY_CONFIRMATION_CONTRACT_ID, 'required_role': 'controller', 'controller_visibility': 'role_output_envelope_only', 'runtime_command': 'flowpilot_runtime.py submit-controller-boundary-confirmation', 'requires_runtime_receipt': True, 'controller_must_not_handwrite_deliverable': True, 'controller_may_read_sealed_bodies': False, 'controller_may_approve_gates': False, 'controller_may_mutate_route': False}, 'sealed_body_reads_allowed': False, 'controller_may_create_project_evidence': False})

def _next_startup_mechanical_audit_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_role_confirmed'):
        return None
    if flags.get('startup_mechanical_audit_written') and router._startup_mechanical_audit_context(project_root, run_root, run_state):
        return None
    if router._controller_action_open_for(run_root, action_type='write_startup_mechanical_audit', postcondition='startup_mechanical_audit_written'):
        return None
    allowed_reads = [project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, project_root / '.flowpilot' / 'current.json'), project_relative(project_root, project_root / '.flowpilot' / 'index.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))]
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        allowed_reads.append(project_relative(project_root, boundary_path))
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        allowed_reads.extend([project_relative(project_root, startup_intake_context['record_path']), project_relative(project_root, startup_intake_context['result_path']), project_relative(project_root, startup_intake_context['receipt_path']), project_relative(project_root, startup_intake_context['envelope_path'])])
    return make_action(action_type='write_startup_mechanical_audit', actor='router', label='router_writes_startup_mechanical_audit', summary='Router writes the startup mechanical audit and proof before exposing the reviewer startup fact-check card.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json'), project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json.proof.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'startup_mechanical_audit_written', 'reviewer_card_waiting_for_audit': 'reviewer.startup_fact_check', 'router_replacement_scope': 'mechanical_only'})

_LOCAL_NAMES = set(globals())
