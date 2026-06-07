"""Startup mechanical checks for ``flowpilot_router_startup_mechanical_boundary``.

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


OWNER_MODULE = 'flowpilot_router_startup_mechanical_boundary'

def _startup_mechanical_checks(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, bool]:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    required_answer_ids = {item['id'] for item in STARTUP_QUESTIONS}
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json')
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json')
    indexed_runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    old_control_paths = [project_root / '.flowpilot' / 'state.json', project_root / '.flowpilot' / 'capabilities.json', project_root / '.flowpilot' / 'execution_frontier.json', project_root / '.flowpilot' / 'routes']
    boundary_context = router._controller_boundary_confirmation_context(project_root, run_root, run_state)
    current_run_id = current.get('run_id')
    current_run_root = current.get('run_root')
    present_true_answers = {key for key, value in answers.items() if value}
    current_answer_ids = required_answer_ids | {'provenance'}
    unsupported_answer_ids = set(answers) - current_answer_ids
    return {
        'controller_boundary_confirmed': boundary_context is not None or router._pm_reset_boundary_confirmed(run_state),
        'startup_intake_record_current': startup_intake_context is not None,
        'startup_intake_receipt_envelope_hash_current': bool(startup_intake_context and startup_intake_context.get('receipt_envelope_body_hash_current')),
        'runtime_uses_startup_intake_record_as_sealed_input': bool(startup_intake_context and startup_intake_context.get('router_must_not_use_chat_history_for_startup_intake')),
        'startup_answers_complete': required_answer_ids.issubset(present_true_answers),
        'startup_answer_provenance_current': answers.get('provenance') == STARTUP_ANSWER_PROVENANCE,
        'startup_answers_use_current_fields_only': not unsupported_answer_ids,
        'background_collaboration_authorized': answers.get('background_collaboration_authorized') is True,
        'current_pointer_matches_run': current_run_id == run_state.get('run_id') and current_run_root == run_state.get('run_root'),
        'index_points_to_run': index.get('current_run_id') == run_state.get('run_id') and any((isinstance(item, dict) and item.get('run_id') == run_state.get('run_id') for item in indexed_runs)),
        'prior_state_quarantined': not any((path.exists() for path in old_control_paths)),
    }

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
    return {'record_path': record_path, 'record': record, 'result_path': result_path, 'receipt_path': receipt_path, 'envelope_path': envelope_path, 'body_path': body_path, 'body_hash': body_hash, 'receipt_envelope_body_hash_current': receipt_envelope_body_hash_current, 'router_must_not_use_chat_history_for_startup_intake': record.get('router_must_not_use_chat_history_for_startup_intake') is True}

def _startup_mechanical_required_evidence(router: ModuleType, run_root: Path, run_state: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    del run_root, run_state
    return []

def _startup_mechanical_ownership(router: ModuleType, computed_checks: dict[str, bool], runtime_requirements: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    runtime_requirement_ids = {str(item['id']) for item in runtime_requirements if item.get('id')}
    router_owned = sorted(computed_checks)
    pm_decision_owned = ['startup_user_answer_authenticity']
    covered = set(router_owned) | runtime_requirement_ids | set(pm_decision_owned)
    known = set(computed_checks) | runtime_requirement_ids | set(pm_decision_owned)
    unowned = sorted(known - covered)
    return {'runtime_owned_mechanical_checks': router_owned, 'runtime_required_evidence_ids': sorted(runtime_requirement_ids), 'pm_decision_owned_requirement_ids': pm_decision_owned, 'unowned_requirement_ids': unowned, 'all_required_requirements_have_owner': not unowned}

__all__ = (
    '_startup_mechanical_checks',
    '_startup_intake_record_context',
    '_startup_mechanical_required_evidence',
    '_startup_mechanical_ownership',
)

_LOCAL_NAMES = set(globals())
