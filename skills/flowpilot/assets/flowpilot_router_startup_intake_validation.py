"""startup intake payload validation helpers for ``flowpilot_router_startup_intake``.

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


OWNER_MODULE = 'flowpilot_router_startup_intake'

def _forbidden_startup_intake_body_fields(router: ModuleType, payload: Any, prefix: str='') -> list[str]:
    _bind_router(router)
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_path = f'{prefix}.{key}' if prefix else str(key)
            if key in _FORBIDDEN_STARTUP_INTAKE_BODY_KEYS:
                found.append(key_path)
            found.extend(router._forbidden_startup_intake_body_fields(value, key_path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(router._forbidden_startup_intake_body_fields(value, f'{prefix}[{index}]'))
    return found

def _resolve_existing_project_file(router: ModuleType, project_root: Path, raw_path: Any, label: str) -> Path:
    _bind_router(router)
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise RouterError(f'startup intake {label} path is required')
    path = resolve_project_path(project_root, raw_path.strip()).resolve()
    project_relative(project_root, path)
    if not path.exists() or not path.is_file():
        raise RouterError(f'startup intake {label} file not found: {raw_path}')
    return path

def _same_project_file(router: ModuleType, project_root: Path, left: Any, right: Path) -> bool:
    _bind_router(router)
    if not isinstance(left, str) or not left.strip():
        return False
    return resolve_project_path(project_root, left).resolve() == right.resolve()

def _startup_intake_result_path_from_payload(router: ModuleType, payload: dict[str, Any]) -> str:
    _bind_router(router)
    result_ref = payload.get('startup_intake_result')
    if isinstance(result_ref, str):
        return result_ref
    if isinstance(result_ref, dict):
        result_path = result_ref.get('result_path') or result_ref.get('path')
        if isinstance(result_path, str) and result_path.strip():
            return result_path
    result_path = payload.get('result_path')
    if isinstance(result_path, str) and result_path.strip():
        return result_path
    raise RouterError('open_startup_intake_ui requires payload.startup_intake_result.result_path')

def _require_interactive_startup_intake_artifact(router: ModuleType, artifact: dict[str, Any], label: str) -> None:
    _bind_router(router)
    launch_mode = artifact.get('launch_mode')
    headless = artifact.get('headless')
    formal_allowed = artifact.get('formal_startup_allowed')
    if launch_mode != STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE or headless is not False or formal_allowed is not True:
        raise RouterError(f'formal FlowPilot startup requires the native interactive startup intake UI; {label} must declare launch_mode={STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE}, headless=false, and formal_startup_allowed=true')

def _validate_startup_intake_result_payload(router: ModuleType, project_root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    result_path = router._resolve_existing_project_file(project_root, router._startup_intake_result_path_from_payload(payload), 'result')
    result = read_json(result_path)
    if result.get('schema_version') != STARTUP_INTAKE_RESULT_SCHEMA:
        raise RouterError(f'startup intake result requires schema_version={STARTUP_INTAKE_RESULT_SCHEMA}')
    leaked = router._forbidden_startup_intake_body_fields(result)
    if leaked:
        raise RouterError(f"startup intake result contains forbidden body text fields: {', '.join(leaked)}")
    status = result.get('status')
    if status not in {'confirmed', 'cancelled'}:
        raise RouterError('startup intake result status must be confirmed or cancelled')
    router._require_interactive_startup_intake_artifact(result, 'startup intake result')
    result_rel = project_relative(project_root, result_path)
    receipt_path: Path | None = None
    receipt: dict[str, Any] | None = None
    if result.get('receipt_path'):
        receipt_path = router._resolve_existing_project_file(project_root, result.get('receipt_path'), 'receipt')
        receipt = read_json(receipt_path)
        if receipt.get('schema_version') != STARTUP_INTAKE_RECEIPT_SCHEMA:
            raise RouterError(f'startup intake receipt requires schema_version={STARTUP_INTAKE_RECEIPT_SCHEMA}')
        leaked_receipt = router._forbidden_startup_intake_body_fields(receipt)
        if leaked_receipt:
            raise RouterError(f"startup intake receipt contains forbidden body text fields: {', '.join(leaked_receipt)}")
        router._require_interactive_startup_intake_artifact(receipt, 'startup intake receipt')
    if receipt_path is None or receipt is None:
        raise RouterError('startup intake result requires receipt_path from the native interactive startup intake UI')
    if status == 'cancelled':
        return {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'status': 'cancelled', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'result_path': result_rel, 'receipt_path': project_relative(project_root, receipt_path), 'controller_visibility': result.get('controller_visibility') or 'cancel_status_only', 'body_text_included': False, 'recorded_at': result.get('recorded_at') or utc_now()}
    if result.get('body_text_included') is not False or result.get('controller_may_read_body') is not False:
        raise RouterError('startup intake confirmed result must be envelope-only for Controller')
    envelope_path = router._resolve_existing_project_file(project_root, result.get('envelope_path'), 'envelope')
    body_path = router._resolve_existing_project_file(project_root, result.get('body_path'), 'body')
    envelope = read_json(envelope_path)
    if envelope.get('schema_version') != STARTUP_INTAKE_ENVELOPE_SCHEMA:
        raise RouterError(f'startup intake envelope requires schema_version={STARTUP_INTAKE_ENVELOPE_SCHEMA}')
    router._require_interactive_startup_intake_artifact(envelope, 'startup intake envelope')
    leaked_envelope = router._forbidden_startup_intake_body_fields(envelope)
    if leaked_envelope:
        raise RouterError(f"startup intake envelope contains forbidden body text fields: {', '.join(leaked_envelope)}")
    if envelope.get('body_text_included') is not False or envelope.get('controller_may_read_body') is not False:
        raise RouterError('startup intake envelope must not expose body text to Controller')
    body_hash = result.get('body_hash')
    if not isinstance(body_hash, str) or not body_hash.strip():
        raise RouterError('startup intake confirmed result requires body_hash')
    actual_hash = packet_runtime.sha256_file(body_path)
    if actual_hash != body_hash.lower():
        raise RouterError('startup intake body hash mismatch')
    if not router._same_project_file(project_root, envelope.get('body_path'), body_path):
        raise RouterError('startup intake envelope body_path does not match result')
    if envelope.get('body_hash') != actual_hash:
        raise RouterError('startup intake envelope body_hash does not match body')
    if not router._same_project_file(project_root, envelope.get('receipt_path'), receipt_path):
        raise RouterError('startup intake envelope receipt_path does not match result')
    if receipt.get('body_hash') != actual_hash:
        raise RouterError('startup intake receipt body_hash does not match body')
    if not router._same_project_file(project_root, receipt.get('body_path'), body_path):
        raise RouterError('startup intake receipt body_path does not match result')
    startup_answers = router._validate_startup_answers({'startup_answers': result.get('startup_answers')})
    if envelope.get('startup_answers') != startup_answers or receipt.get('startup_answers') != startup_answers:
        raise RouterError('startup intake startup_answers mismatch across result, receipt, and envelope')
    return {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'status': 'confirmed', 'source': envelope.get('source') or 'native_wpf_startup_intake', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'language': result.get('language') or envelope.get('language') or receipt.get('language'), 'result_path': result_rel, 'receipt_path': project_relative(project_root, receipt_path), 'envelope_path': project_relative(project_root, envelope_path), 'body_path': project_relative(project_root, body_path), 'body_hash': actual_hash, 'startup_answers': startup_answers, 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'recorded_at': result.get('recorded_at') or utc_now()}

def _apply_startup_intake_result_to_bootstrap(router: ModuleType, project_root: Path, state: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    startup_intake = router._validate_startup_intake_result_payload(project_root, payload)
    state.setdefault('flags', {})
    state['startup_intake'] = startup_intake
    result_extra: dict[str, Any] = {'startup_intake': startup_intake}
    if startup_intake['status'] == 'cancelled':
        state['status'] = 'startup_cancelled'
        state['startup_state'] = 'startup_cancelled'
        state['pending_action'] = None
        return result_extra
    state['startup_answers'] = startup_intake['startup_answers']
    state['startup_state'] = 'answers_complete'
    state['flags']['startup_intake_result_recorded'] = True
    state['flags']['startup_intake_body_boundary_enforced'] = True
    state['flags']['startup_answers_recorded'] = True
    seed_proof = router._run_deterministic_startup_bootstrap_seed(project_root, state)
    result_extra['deterministic_bootstrap_seed'] = {'evidence_path': state.get('deterministic_bootstrap_seed_evidence_path'), 'artifact_keys': sorted((seed_proof.get('artifacts') or {}).keys())}
    return result_extra

def _validate_startup_answers(router: ModuleType, payload: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    extra_payload = sorted(set(payload) - {'startup_answers'})
    if extra_payload:
        raise RouterError(f"startup answers payload contains unsupported fields: {', '.join(extra_payload)}")
    answers = payload.get('startup_answers')
    if not isinstance(answers, dict):
        raise RouterError('startup intake result requires a startup_answers object')
    provenance = answers.get('provenance')
    if provenance != STARTUP_ANSWER_PROVENANCE:
        raise RouterError('startup answers require provenance=explicit_user_reply from the native startup intake UI')
    allowed_keys = set(STARTUP_ANSWER_ENUMS) | {'provenance'}
    extra = sorted(set(answers) - allowed_keys)
    if extra:
        raise RouterError(f"startup answers contain unsupported fields: {', '.join(extra)}")
    validated: dict[str, str] = {}
    for answer_id, allowed_values in STARTUP_ANSWER_ENUMS.items():
        value = answers.get(answer_id)
        if not isinstance(value, str) or value not in allowed_values:
            allowed = ', '.join(sorted(allowed_values))
            raise RouterError(f'startup answer {answer_id} must be one of: {allowed}')
        validated[answer_id] = value
    validated['provenance'] = provenance
    return validated

__all__ = (
    '_forbidden_startup_intake_body_fields',
    '_resolve_existing_project_file',
    '_same_project_file',
    '_startup_intake_result_path_from_payload',
    '_require_interactive_startup_intake_artifact',
    '_validate_startup_intake_result_payload',
    '_apply_startup_intake_result_to_bootstrap',
    '_validate_startup_answers',
)

_LOCAL_NAMES = set(globals())
