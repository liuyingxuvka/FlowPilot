"""startup fact checks and reviewer requirements helpers for ``flowpilot_router_startup_fact_boundary``.

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
    role_binding = read_json_if_exists(run_root / 'role_binding_ledger.json')
    role_slots = role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []
    role_keys = {slot.get('role_key') for slot in role_slots if isinstance(slot, dict)}
    live_role_slots_current = role_keys == set(RUNTIME_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'live_agent_started' and isinstance(slot.get('agent_id'), str) and bool(str(slot.get('agent_id')).strip()) and (slot.get('model_policy') == ROLE_BINDING_MODEL_POLICY) and (slot.get('reasoning_effort_policy') == ROLE_BINDING_REASONING_EFFORT_POLICY) and (slot.get('binding_open_result') == ROLE_BINDING_OPEN_RESULT) and (slot.get('opened_for_run_id') == run_state.get('run_id')) and (slot.get('opened_after_startup_answers') is True) for slot in role_slots))
    single_agent_slots_current = role_keys == set(RUNTIME_ROLE_KEYS) and all((isinstance(slot, dict) and slot.get('status') == 'single_agent_continuity_authorized' and (slot.get('agent_id') is None) and (slot.get('fallback_authorized_by_startup_answer') is True) for slot in role_slots))
    indexed_runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    scheduled_requested = router._scheduled_continuation_requested(answers)
    old_control_paths = [project_root / '.flowpilot' / 'state.json', project_root / '.flowpilot' / 'capabilities.json', project_root / '.flowpilot' / 'execution_frontier.json', project_root / '.flowpilot' / 'routes']
    boundary_context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    return {'controller_boundary_confirmed': boundary_context is not None or router._pm_reset_boundary_confirmed(run_state), 'startup_intake_record_current': startup_intake_context is not None, 'startup_intake_receipt_envelope_hash_current': bool(startup_intake_context and startup_intake_context.get('receipt_envelope_body_hash_current')), 'reviewer_live_review_uses_startup_intake_record': bool(startup_intake_context and startup_intake_context.get('reviewer_must_not_use_chat_history')), 'startup_answers_complete': required_answer_ids.issubset({key for key, value in answers.items() if value}), 'current_pointer_matches_run': current.get('current_run_id') == run_state.get('run_id') and current.get('current_run_root') == run_state.get('run_root'), 'index_points_to_run': index.get('current_run_id') == run_state.get('run_id') and any((isinstance(item, dict) and item.get('run_id') == run_state.get('run_id') for item in indexed_runs)), 'runtime_roles_slots_current': role_keys == set(RUNTIME_ROLE_KEYS), 'live_runtime_role_assistances_current_if_allowed': live_role_slots_current if answers.get('runtime_role_assistances') == 'allow' else True, 'single_agent_continuity_current_if_selected': single_agent_slots_current if answers.get('runtime_role_assistances') == 'single-agent' else True, 'continuation_mode_recorded': bool(answers.get('scheduled_continuation')), 'continuation_binding_current': continuation_binding.get('run_id') == run_state.get('run_id') and continuation_binding.get('schema_version') == 'flowpilot.continuation_binding.v1', 'scheduled_heartbeat_verified_if_requested': continuation_binding.get('heartbeat_active') is True and continuation_binding.get('route_heartbeat_interval_minutes') == 1 and bool(continuation_binding.get('host_automation_id')) and (continuation_binding.get('host_automation_verified') is True) if scheduled_requested else continuation_binding.get('mode') == 'manual_resume', 'display_surface_recorded': bool(answers.get('display_surface')), 'prior_state_quarantined': not any((path.exists() for path in old_control_paths))}

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

def _role_slots_have_host_role_binding_receipts(router: ModuleType, role_slots: list[dict[str, Any]], run_id: str) -> bool:
    _bind_router(router)
    for slot in role_slots:
        receipt = slot.get('host_role_binding_receipt') if isinstance(slot, dict) else None
        if not isinstance(receipt, dict):
            return False
        if receipt.get('source_kind') != 'host_receipt':
            return False
        if receipt.get('opened_for_run_id') != run_id:
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
    role_binding = read_json_if_exists(run_root / 'role_binding_ledger.json')
    role_slots = role_binding.get('role_slots') if isinstance(role_binding.get('role_slots'), list) else []
    continuation_binding = read_json_if_exists(router._continuation_binding_path(run_root))
    requirements: list[dict[str, Any]] = []
    if answers.get('runtime_role_assistances') == 'allow' and (not router._role_slots_have_host_role_binding_receipts(role_slots, str(run_state.get('run_id') or ''))):
        requirements.append({'id': 'live_agent_spawn_freshness', 'reason': 'Router validates role-binding shape, run ids, and requested role intelligence policy, but host binding freshness and actual model selection need a receipt or reviewer check.', 'self_attested_payload_fields': ['role_bindings[].model_policy', 'role_bindings[].reasoning_effort_policy', 'role_bindings[].binding_open_result', 'role_bindings[].opened_after_startup_answers'], 'reviewer_direct_check_required': True})
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

__all__ = (
    '_startup_fact_checks',
    '_startup_intake_record_context',
    '_role_slots_have_host_role_binding_receipts',
    '_continuation_has_host_bound_automation_receipt',
    '_startup_external_fact_requirements',
    '_startup_fact_review_ownership',
    '_validate_startup_external_fact_review',
)

_LOCAL_NAMES = set(globals())
