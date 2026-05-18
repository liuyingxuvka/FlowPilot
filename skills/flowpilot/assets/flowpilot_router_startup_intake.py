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


OWNER_MODULE = 'flowpilot_router_startup_intake'

def _normalize_startup_question_stop_boundary(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    if state.get('status') == 'startup_cancelled' or state.get('startup_state') == 'startup_cancelled':
        return False
    flags = state.setdefault('flags', {})
    if not flags.get('startup_questions_asked'):
        return False
    if flags.get('startup_answers_recorded') or state.get('startup_answers'):
        return False
    changed = False
    if not flags.get('startup_state_written_awaiting_answers'):
        flags['startup_state_written_awaiting_answers'] = True
        changed = True
    if not flags.get('dialog_stopped_for_answers'):
        flags['dialog_stopped_for_answers'] = True
        changed = True
    if state.get('startup_state') != 'awaiting_answers_stopped':
        state['startup_state'] = 'awaiting_answers_stopped'
        changed = True
    pending = state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') in {'write_startup_awaiting_answers_state', 'stop_for_startup_answers'}:
        state['pending_action'] = None
        append_history(state, 'startup_question_stop_boundary_normalized', {'cleared_pending_action': pending.get('action_type')})
        changed = True
    return changed

def _startup_intake_ui_launcher_ref(router: ModuleType, project_root: Path) -> str:
    _bind_router(router)
    launcher = Path(__file__).resolve().parent / 'ui' / 'startup_intake' / 'flowpilot_startup_intake.ps1'
    try:
        return project_relative(project_root, launcher)
    except RouterError:
        return str(launcher)

def _startup_intake_output_dir_ref(router: ModuleType, project_root: Path, state: dict[str, Any]) -> str:
    _bind_router(router)
    run_id = str(state.get('run_id') or router._create_run_id())
    output_dir = project_root / '.flowpilot' / 'bootstrap' / 'startup_intake' / run_id
    return project_relative(project_root, output_dir)

def _startup_intake_result_payload_contract(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'payload_key': 'startup_intake_result', 'required': True, 'expected_shape': {'startup_intake_result': {'result_path': '<path returned by the native startup intake UI>'}}, 'result_schema_version': STARTUP_INTAKE_RESULT_SCHEMA, 'receipt_schema_version': STARTUP_INTAKE_RECEIPT_SCHEMA, 'envelope_schema_version': STARTUP_INTAKE_ENVELOPE_SCHEMA, 'formal_launch_provenance': {'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True}, 'output_dir': router._startup_intake_output_dir_ref(project_root, state), 'controller_body_boundary': {'controller_may_read_body': False, 'body_text_must_not_be_in_payload': True, 'allowed_controller_view': 'result/envelope paths, body hash, startup answers, and status only'}}

def _startup_intake_ui_action_extra(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    launcher = router._startup_intake_ui_launcher_ref(project_root)
    output_dir = router._startup_intake_output_dir_ref(project_root, state)
    command = ['powershell', '-STA', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', launcher, '-OutputDir', output_dir]
    return {'startup_intake_ui': {'schema_version': 'flowpilot.startup_intake_ui_launcher.v1', 'launcher_path': launcher, 'output_dir': output_dir, 'command': command, 'result_path_expected': f'{output_dir}/startup_intake_result.json', 'body_text_is_never_router_payload': True, 'cancel_result_is_terminal': True, 'headless_result_is_not_formal_startup': True}, 'payload_contract': router._startup_intake_result_payload_contract(project_root, state), 'plain_instruction': "Open the native FlowPilot startup intake UI with the provided command. Formal startup must use the interactive native UI result; do not use headless auto-confirmation, scripted result synthesis, chat substitution, or direct JSON creation. After the UI closes, return to Router daemon status and the Controller action ledger before continuing. Do not paste the user's work request into chat and do not include it in the Router payload."}

def _confirmed_startup_intake(router: ModuleType, state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    intake = state.get('startup_intake')
    if isinstance(intake, dict) and intake.get('status') == 'confirmed':
        return intake
    return None

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
    state['startup_answer_interpretation'] = None
    state['startup_state'] = 'answers_complete'
    state['flags']['startup_state_written_awaiting_answers'] = True
    state['flags']['dialog_stopped_for_answers'] = True
    state['flags']['startup_answers_recorded'] = True
    seed_proof = router._run_deterministic_startup_bootstrap_seed(project_root, state)
    result_extra['deterministic_bootstrap_seed'] = {'evidence_path': state.get('deterministic_bootstrap_seed_evidence_path'), 'artifact_keys': sorted((seed_proof.get('artifacts') or {}).keys())}
    return result_extra

def _validate_startup_answer_interpretation(router: ModuleType, payload: dict[str, Any], answers: dict[str, str]) -> dict[str, Any] | None:
    _bind_router(router)
    provenance = answers.get('provenance')
    if provenance == STARTUP_ANSWER_PROVENANCE:
        if payload.get('startup_answer_interpretation') is not None:
            raise RouterError('startup_answer_interpretation is only allowed with ai_interpreted_from_explicit_user_reply provenance')
        return None
    receipt = payload.get('startup_answer_interpretation')
    if not isinstance(receipt, dict):
        raise RouterError('AI-interpreted startup answers require payload.startup_answer_interpretation receipt')
    if receipt.get('schema_version') != STARTUP_ANSWER_INTERPRETATION_SCHEMA:
        raise RouterError(f'startup_answer_interpretation requires schema_version={STARTUP_ANSWER_INTERPRETATION_SCHEMA}')
    raw_text = receipt.get('raw_user_reply_text')
    if not isinstance(raw_text, str) or not raw_text.strip():
        raise RouterError("startup_answer_interpretation.raw_user_reply_text must preserve the user's non-empty reply")
    interpreted_by = receipt.get('interpreted_by')
    if interpreted_by not in {'controller', 'bootloader'}:
        raise RouterError('startup_answer_interpretation.interpreted_by must be controller or bootloader')
    if receipt.get('interpretation_provenance') != STARTUP_ANSWER_INTERPRETATION_PROVENANCE:
        raise RouterError('startup_answer_interpretation.interpretation_provenance must match the AI-interpreted startup answer provenance')
    if receipt.get('ambiguity_status') != 'none':
        raise RouterError('ambiguous startup answers must be returned to the user instead of applied')
    interpreted_answers = receipt.get('interpreted_answers')
    if not isinstance(interpreted_answers, dict):
        raise RouterError('startup_answer_interpretation.interpreted_answers must be an object')
    expected = {key: answers[key] for key in STARTUP_ANSWER_ENUMS}
    got = {key: interpreted_answers.get(key) for key in STARTUP_ANSWER_ENUMS}
    if got != expected:
        raise RouterError('startup_answer_interpretation.interpreted_answers must match payload.startup_answers')
    allowed_keys = {'schema_version', 'raw_user_reply_text', 'interpreted_by', 'interpretation_provenance', 'ambiguity_status', 'interpreted_answers', 'reviewer_must_check_raw_reply_alignment', 'notes'}
    extra = sorted(set(receipt) - allowed_keys)
    if extra:
        raise RouterError(f"startup_answer_interpretation contains unsupported fields: {', '.join(extra)}")
    interpretation = {'schema_version': STARTUP_ANSWER_INTERPRETATION_SCHEMA, 'raw_user_reply_text': raw_text.strip(), 'interpreted_by': interpreted_by, 'interpretation_provenance': STARTUP_ANSWER_INTERPRETATION_PROVENANCE, 'ambiguity_status': 'none', 'interpreted_answers': expected, 'notes': receipt.get('notes'), 'recorded_at': utc_now()}
    if 'reviewer_must_check_raw_reply_alignment' in receipt:
        interpretation['reviewer_must_check_raw_reply_alignment'] = bool(receipt.get('reviewer_must_check_raw_reply_alignment'))
    return interpretation

def _validate_startup_answers(router: ModuleType, payload: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    answers = payload.get('startup_answers')
    if not isinstance(answers, dict):
        raise RouterError('record_startup_answers requires payload.startup_answers object')
    provenance = answers.get('provenance')
    if provenance not in {STARTUP_ANSWER_PROVENANCE, STARTUP_ANSWER_INTERPRETATION_PROVENANCE}:
        raise RouterError('startup answers require provenance=explicit_user_reply or ai_interpreted_from_explicit_user_reply')
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
    router._validate_startup_answer_interpretation(payload, validated)
    return validated

def _validate_user_request(router: ModuleType, payload: dict[str, Any]) -> dict[str, str]:
    _bind_router(router)
    request = payload.get('user_request')
    if not isinstance(request, dict):
        raise RouterError('record_user_request requires payload.user_request object')
    provenance = request.get('provenance')
    if provenance != USER_REQUEST_PROVENANCE:
        raise RouterError('user request requires provenance=explicit_user_request')
    text = request.get('text')
    if not isinstance(text, str) or not text.strip():
        raise RouterError('user_request.text must contain the exact non-empty user task')
    allowed_keys = {'text', 'provenance', 'source'}
    extra = sorted(set(request) - allowed_keys)
    if extra:
        raise RouterError(f"user request contains unsupported fields: {', '.join(extra)}")
    source = request.get('source') or 'flowpilot_activation_or_user_reply'
    if not isinstance(source, str) or not source.strip():
        raise RouterError('user_request.source must be a non-empty string when supplied')
    return {'text': text.strip(), 'provenance': USER_REQUEST_PROVENANCE, 'source': source.strip()}

def _copy_startup_intake_file(router: ModuleType, project_root: Path, run_root: Path, raw_path: str, target_name: str) -> Path:
    _bind_router(router)
    source = router._resolve_existing_project_file(project_root, raw_path, target_name)
    target_dir = run_root / 'startup_intake'
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / target_name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return target

def _materialize_startup_intake_record(router: ModuleType, project_root: Path, state: dict[str, Any], run_root: Path) -> dict[str, Any]:
    _bind_router(router)
    intake = router._confirmed_startup_intake(state)
    if intake is None:
        raise RouterError('cannot materialize startup intake record before confirmed UI intake')
    result_path = router._copy_startup_intake_file(project_root, run_root, str(intake['result_path']), 'startup_intake_result.json')
    receipt_path = router._copy_startup_intake_file(project_root, run_root, str(intake['receipt_path']), 'startup_intake_receipt.json')
    envelope_path = router._copy_startup_intake_file(project_root, run_root, str(intake['envelope_path']), 'startup_intake_envelope.json')
    body_path = router._copy_startup_intake_file(project_root, run_root, str(intake['body_path']), 'startup_intake_body.md')
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != intake.get('body_hash'):
        raise RouterError('startup intake copied body hash mismatch')
    record = {'schema_version': STARTUP_INTAKE_RECORD_SCHEMA, 'run_id': state.get('run_id'), 'status': 'confirmed', 'source': intake.get('source') or 'native_wpf_startup_intake', 'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True, 'language': intake.get('language'), 'result_path': project_relative(project_root, result_path), 'receipt_path': project_relative(project_root, receipt_path), 'envelope_path': project_relative(project_root, envelope_path), 'body_path': project_relative(project_root, body_path), 'body_hash': body_hash, 'startup_answers': intake.get('startup_answers') or {}, 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'materialized_at': utc_now()}
    record_path = run_root / 'startup_intake' / 'startup_intake_record.json'
    write_json(record_path, record)
    record['record_path'] = project_relative(project_root, record_path)
    return record

def _user_request_ref_from_startup_intake(router: ModuleType, project_root: Path, state: dict[str, Any], intake_record: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': USER_REQUEST_REF_SCHEMA, 'run_id': state.get('run_id'), 'provenance': 'startup_intake_ui', 'source': intake_record.get('source') or 'native_wpf_startup_intake', 'startup_intake_record_path': intake_record['record_path'], 'startup_intake_result_path': intake_record['result_path'], 'startup_intake_receipt_path': intake_record['receipt_path'], 'startup_intake_envelope_path': intake_record['envelope_path'], 'body_path': intake_record['body_path'], 'body_hash': intake_record['body_hash'], 'controller_visibility': 'envelope_only', 'controller_may_read_body': False, 'body_text_included': False, 'pm_may_open_body_via_packet_runtime': True, 'reviewer_live_review_source': 'startup_intake_record', 'reviewer_must_not_use_chat_history': True, 'recorded_at': utc_now()}

def _build_user_intake_body_from_ref(router: ModuleType, project_root: Path, user_request_ref: dict[str, Any], startup_answers: dict[str, Any]) -> str:
    _bind_router(router)
    body_path = router._resolve_existing_project_file(project_root, user_request_ref.get('body_path'), 'startup intake body')
    body_hash = packet_runtime.sha256_file(body_path)
    if body_hash != user_request_ref.get('body_hash'):
        raise RouterError('startup intake body hash mismatch before user_intake packet')
    metadata = {'schema_version': 'flowpilot.pm_startup_intake_context.v1', 'source': 'native_startup_intake_ui', 'startup_intake_record_path': user_request_ref.get('startup_intake_record_path'), 'startup_intake_receipt_path': user_request_ref.get('startup_intake_receipt_path'), 'startup_intake_envelope_path': user_request_ref.get('startup_intake_envelope_path'), 'body_path': user_request_ref.get('body_path'), 'body_hash': user_request_ref.get('body_hash'), 'startup_answers': startup_answers, 'controller_may_read_body': False, 'reviewer_live_review_source': 'startup_intake_record'}
    return f"# FlowPilot Startup Intake\n\nThe user's work request came from the native startup intake UI. Router holds this sealed startup packet and releases it to Project Manager after PM system-card ACK. Controller must not read this packet body.\n\n```json\n{json.dumps(metadata, indent=2, sort_keys=True)}\n```\n\n## User Work Request\n\n{body_path.read_text(encoding='utf-8-sig').strip()}\n"

def _deterministic_bootstrap_seed_evidence_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'bootstrap' / 'deterministic_bootstrap_seed_evidence.json'

def _write_startup_answers_record(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    interpretation = state.get('startup_answer_interpretation') if isinstance(state.get('startup_answer_interpretation'), dict) else None
    interpretation_path = run_root / 'startup_answer_interpretation.json'
    if interpretation:
        write_json(interpretation_path, interpretation)
    record = {'schema_version': 'flowpilot.startup_answers.v1', 'run_id': state['run_id'], 'answers': state.get('startup_answers') or {}, 'startup_answer_interpretation_path': project_relative(project_root, interpretation_path) if interpretation else None, 'recorded_at': utc_now()}
    write_json(run_root / 'startup_answers.json', record)
    return record

def _initialize_mailbox_foundation(router: ModuleType, project_root: Path, run_root: Path, run_id: str) -> dict[str, Any]:
    _bind_router(router)
    dirs = ('mailbox/system_cards', 'mailbox/inbox', 'mailbox/outbox', 'mailbox/outbox/card_acks', 'runtime_receipts/card_reads', 'runtime_receipts/role_io_protocol', 'packets')
    for rel in dirs:
        (run_root / rel).mkdir(parents=True, exist_ok=True)
    packet_ledger_path = run_root / 'packet_ledger.json'
    prompt_delivery_ledger_path = run_root / 'prompt_delivery_ledger.json'
    card_ledger_path = _card_ledger_path(run_root)
    return_event_ledger_path = _return_event_ledger_path(run_root)
    role_io_protocol_ledger_path = _role_io_protocol_ledger_path(run_root)
    write_json(packet_ledger_path, router._create_empty_packet_ledger(project_root, run_id, run_root))
    write_json(prompt_delivery_ledger_path, {'schema_version': 'flowpilot.prompt_delivery_ledger.v1', 'run_id': run_id, 'deliveries': []})
    write_json(card_ledger_path, _empty_card_ledger(run_id))
    write_json(return_event_ledger_path, _empty_return_event_ledger(run_id))
    write_json(role_io_protocol_ledger_path, _empty_role_io_protocol_ledger(run_id))
    return {'directories': [project_relative(project_root, run_root / rel) for rel in dirs], 'ledgers': [project_relative(project_root, packet_ledger_path), project_relative(project_root, prompt_delivery_ledger_path), project_relative(project_root, card_ledger_path), project_relative(project_root, return_event_ledger_path), project_relative(project_root, role_io_protocol_ledger_path)]}

def _record_startup_user_request_ref(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if router._confirmed_startup_intake(state) is not None:
        intake_record = router._materialize_startup_intake_record(project_root, state, run_root)
        user_request = router._user_request_ref_from_startup_intake(project_root, state, intake_record)
        user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'source': 'startup_intake_ui', 'user_request_ref': user_request, 'startup_intake_record': intake_record, 'controller_may_read_body': False, 'body_text_included': False, 'recorded_at': utc_now()}
        state['startup_intake'] = intake_record
        state['startup_intake_record_path'] = intake_record['record_path']
        state['user_request_ref'] = user_request
    else:
        user_request = state.get('user_request')
        if not isinstance(user_request, dict):
            raise RouterError('deterministic startup seed requires confirmed startup intake or user_request')
        user_request_record = {'schema_version': 'flowpilot.user_request.v1', 'run_id': state['run_id'], 'user_request': user_request, 'recorded_at': utc_now()}
    user_request_path = run_root / 'user_request.json'
    write_json(user_request_path, user_request_record)
    state['user_request'] = user_request
    state['user_request_path'] = project_relative(project_root, user_request_path)
    return user_request_record

def _write_startup_user_intake_scaffold(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    user_request = state.get('user_request')
    if not isinstance(user_request, dict):
        raise RouterError('cannot write deterministic user_intake scaffold before user request reference')
    if user_request.get('schema_version') == USER_REQUEST_REF_SCHEMA:
        body_text = router._build_user_intake_body_from_ref(project_root, user_request, state.get('startup_answers') or {})
        user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=body_text, startup_options=state.get('startup_answers') or {}, source='startup_intake_ui', body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, startup_intake_ref=user_request, router_owned_startup_material=True)
    else:
        user_intake = packet_runtime.create_user_intake_packet(project_root, run_id=str(state['run_id']), packet_id='user_intake', node_id='startup', body_text=json.dumps({'user_request': user_request, 'user_request_path': state.get('user_request_path'), 'startup_answers': state.get('startup_answers') or {}, 'startup_answers_path': project_relative(project_root, run_root / 'startup_answers.json'), 'startup_answer_interpretation_path': project_relative(project_root, run_root / 'startup_answer_interpretation.json') if isinstance(state.get('startup_answer_interpretation'), dict) else None}, indent=2, sort_keys=True), startup_options=state.get('startup_answers') or {}, body_visibility=packet_runtime.SEALED_BODY_VISIBILITY, router_owned_startup_material=True)
    user_intake_path = run_root / 'mailbox' / 'outbox' / 'user_intake.json'
    write_json(user_intake_path, user_intake)
    return {'path': project_relative(project_root, user_intake_path), 'body_visibility': user_intake.get('body_visibility'), 'startup_owner': 'router', 'release_condition': 'pm_system_card_bundle_ack_resolved', 'controller_may_read_body': False}

def _run_deterministic_startup_bootstrap_seed(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if not state.get('run_id') or not state.get('run_root'):
        raise RouterError('deterministic startup seed requires run shell')
    if not state.get('startup_answers'):
        raise RouterError('deterministic startup seed requires startup answers')
    run_root = project_root / str(state['run_root'])
    flags = state.setdefault('flags', {})
    evidence_path = router._deterministic_bootstrap_seed_evidence_path(run_root)
    if flags.get('deterministic_bootstrap_seed_completed') and evidence_path.exists():
        existing_proof = read_json(evidence_path)
        if existing_proof.get('schema_version') == DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA and existing_proof.get('completed') is True:
            state['deterministic_bootstrap_seed_evidence_path'] = project_relative(project_root, evidence_path)
            return existing_proof
        raise RouterError('completed deterministic startup seed has invalid evidence')
    artifacts: dict[str, Any] = {}
    if not flags.get('runtime_kit_copied'):
        _copy_runtime_kit_into_run_root(run_root)
        flags['runtime_kit_copied'] = True
    artifacts['runtime_kit'] = project_relative(project_root, run_root / 'runtime_kit')
    artifacts['startup_answers'] = project_relative(project_root, run_root / 'startup_answers.json')
    router._write_startup_answers_record(project_root, run_root, state)
    flags['placeholders_filled'] = True
    mailbox = router._initialize_mailbox_foundation(project_root, run_root, str(state['run_id']))
    artifacts['mailbox'] = mailbox
    flags['mailbox_initialized'] = True
    user_request_record = router._record_startup_user_request_ref(project_root, run_root, state)
    artifacts['user_request'] = project_relative(project_root, run_root / 'user_request.json')
    flags['user_request_recorded'] = True
    user_intake = router._write_startup_user_intake_scaffold(project_root, run_root, state)
    artifacts['user_intake'] = user_intake
    flags['user_intake_ready'] = True
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    required_flags = ('runtime_kit_copied', 'placeholders_filled', 'mailbox_initialized', 'user_request_recorded', 'user_intake_ready')
    proof = {'schema_version': DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA, 'run_id': state['run_id'], 'source': 'deterministic_bootstrap_seed', 'controller_action_row_created': False, 'pm_blocker_allowed': False, 'required_flags': {flag: bool(flags.get(flag)) for flag in required_flags}, 'artifacts': artifacts, 'user_request_record_controller_may_read_body': bool(user_request_record.get('controller_may_read_body', True)), 'completed': all((bool(flags.get(flag)) for flag in required_flags)), 'completed_at': utc_now()}
    if not proof['completed']:
        missing = [flag for flag, value in proof['required_flags'].items() if not value]
        raise RouterError(f"deterministic startup seed missing required flags: {', '.join(missing)}")
    write_json(evidence_path, proof)
    state['deterministic_bootstrap_seed_evidence_path'] = project_relative(project_root, evidence_path)
    flags['deterministic_bootstrap_seed_completed'] = True
    append_history(state, 'deterministic_startup_bootstrap_seed_completed', {'evidence_path': state['deterministic_bootstrap_seed_evidence_path'], 'artifacts': sorted(artifacts)})
    return proof

_LOCAL_NAMES = set(globals())
