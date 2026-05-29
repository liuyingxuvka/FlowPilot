"""startup intake materialization and deterministic seed helpers for ``flowpilot_router_startup_intake``.

This child module is imported by the public facade and keeps
router binding behavior explicit for the startup StructureMesh split.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
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
import flowpilot_router_startup_intake_flowguard_capability as _flowguard_capability
from flowpilot_router_startup_intake_flowguard_capability import *

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
    _flowguard_capability._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = 'flowpilot_router_startup_intake'

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
    record = {'schema_version': 'flowpilot.startup_answers.v1', 'run_id': state['run_id'], 'answers': state.get('startup_answers') or {}, 'recorded_at': utc_now()}
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
        raise RouterError('deterministic startup seed requires confirmed native startup intake')
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
        raise RouterError('user_intake scaffold requires native startup intake user_request_ref')
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
            snapshot_path = _flowguard_capability_snapshot_path(router, run_root)
            artifacts = existing_proof.get('artifacts') if isinstance(existing_proof.get('artifacts'), dict) else {}
            existing_proof['artifacts'] = artifacts
            required = existing_proof.get('required_flags') if isinstance(existing_proof.get('required_flags'), dict) else {}
            existing_proof['required_flags'] = required
            needs_snapshot_refresh = not snapshot_path.exists() or 'flowguard_capability_snapshot' not in artifacts
            needs_required_refresh = 'flowguard_capability_snapshot_written' not in required
            if needs_snapshot_refresh:
                snapshot = _write_flowguard_capability_snapshot(router, project_root, run_root, state)
                artifacts['flowguard_capability_snapshot'] = snapshot
                required['flowguard_capability_snapshot_written'] = True
            elif needs_required_refresh:
                required['flowguard_capability_snapshot_written'] = True
            if needs_snapshot_refresh or needs_required_refresh:
                existing_proof['completed'] = all(bool(value) for value in required.values())
                existing_proof['refreshed_at'] = utc_now()
                write_json(evidence_path, existing_proof)
            if snapshot_path.exists():
                state['flowguard_capability_snapshot_path'] = project_relative(project_root, snapshot_path)
            flags['flowguard_capability_snapshot_written'] = True
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
    snapshot = _write_flowguard_capability_snapshot(router, project_root, run_root, state)
    artifacts['flowguard_capability_snapshot'] = snapshot
    flags['flowguard_capability_snapshot_written'] = True
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    required_flags = ('runtime_kit_copied', 'placeholders_filled', 'mailbox_initialized', 'user_request_recorded', 'user_intake_ready', 'flowguard_capability_snapshot_written')
    proof = {'schema_version': DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA, 'run_id': state['run_id'], 'source': 'deterministic_bootstrap_seed', 'controller_action_row_created': False, 'pm_blocker_allowed': False, 'required_flags': {flag: bool(flags.get(flag)) for flag in required_flags}, 'artifacts': artifacts, 'user_request_record_controller_may_read_body': bool(user_request_record.get('controller_may_read_body', True)), 'completed': all((bool(flags.get(flag)) for flag in required_flags)), 'completed_at': utc_now()}
    if not proof['completed']:
        missing = [flag for flag, value in proof['required_flags'].items() if not value]
        raise RouterError(f"deterministic startup seed missing required flags: {', '.join(missing)}")
    write_json(evidence_path, proof)
    state['deterministic_bootstrap_seed_evidence_path'] = project_relative(project_root, evidence_path)
    flags['deterministic_bootstrap_seed_completed'] = True
    append_history(state, 'deterministic_startup_bootstrap_seed_completed', {'evidence_path': state['deterministic_bootstrap_seed_evidence_path'], 'artifacts': sorted(artifacts)})
    return proof

def _sync_completed_deterministic_startup_seed_to_bootstrap(router: ModuleType, project_root: Path, state: dict[str, Any], *, save: bool=False, source: str='deterministic_seed_projection') -> dict[str, Any]:
    _bind_router(router)
    if not state.get('run_id') or not state.get('run_root'):
        return {'changed': False, 'reason': 'run_shell_missing'}
    run_root = project_root / str(state['run_root'])
    evidence_path = router._deterministic_bootstrap_seed_evidence_path(run_root)
    proof = read_json_if_exists(evidence_path)
    if proof.get('schema_version') != DETERMINISTIC_BOOTSTRAP_SEED_EVIDENCE_SCHEMA or proof.get('completed') is not True:
        return {'changed': False, 'reason': 'completed_seed_evidence_missing'}
    required = proof.get('required_flags') if isinstance(proof.get('required_flags'), dict) else {}
    if not required or not all(bool(value) for value in required.values()):
        return {'changed': False, 'reason': 'completed_seed_required_flags_incomplete'}

    changed = False
    flags = state.setdefault('flags', {})
    for flag, value in required.items():
        if value and not flags.get(flag):
            flags[flag] = True
            changed = True
    if not flags.get('deterministic_bootstrap_seed_completed'):
        flags['deterministic_bootstrap_seed_completed'] = True
        changed = True
    rel_evidence = project_relative(project_root, evidence_path)
    if state.get('deterministic_bootstrap_seed_evidence_path') != rel_evidence:
        state['deterministic_bootstrap_seed_evidence_path'] = rel_evidence
        changed = True

    answers_record = read_json_if_exists(run_root / 'startup_answers.json')
    answers = answers_record.get('answers') if isinstance(answers_record.get('answers'), dict) else None
    if answers is not None and state.get('startup_answers') != answers:
        state['startup_answers'] = answers
        changed = True
    if answers is not None and state.get('startup_state') != 'answers_complete':
        state['startup_state'] = 'answers_complete'
        changed = True
    if answers is not None and not flags.get('startup_answers_recorded'):
        flags['startup_answers_recorded'] = True
        changed = True

    artifacts = proof.get('artifacts') if isinstance(proof.get('artifacts'), dict) else {}
    snapshot = artifacts.get('flowguard_capability_snapshot') if isinstance(artifacts.get('flowguard_capability_snapshot'), dict) else {}
    snapshot_path = snapshot.get('path') if isinstance(snapshot, dict) else None
    if snapshot_path and state.get('flowguard_capability_snapshot_path') != snapshot_path:
        state['flowguard_capability_snapshot_path'] = snapshot_path
        changed = True
    if changed:
        append_history(state, 'deterministic_startup_bootstrap_seed_reprojected', {'source': source, 'evidence_path': rel_evidence, 'required_flags': sorted(required)})
        if save:
            router.save_bootstrap_state(project_root, state)
    return {'changed': changed, 'evidence_path': rel_evidence, 'required_flags': sorted(required)}

__all__ = (
    '_copy_startup_intake_file',
    '_materialize_startup_intake_record',
    '_user_request_ref_from_startup_intake',
    '_build_user_intake_body_from_ref',
    '_deterministic_bootstrap_seed_evidence_path',
    '_flowguard_capability_snapshot_path',
    '_portable_skill_search_roots',
    '_flowguard_route_classification',
    '_discover_flowguard_skill_routes',
    '_flowguard_import_snapshot',
    '_write_flowguard_capability_snapshot',
    '_write_startup_answers_record',
    '_initialize_mailbox_foundation',
    '_record_startup_user_request_ref',
    '_write_startup_user_intake_scaffold',
    '_run_deterministic_startup_bootstrap_seed',
    '_sync_completed_deterministic_startup_seed_to_bootstrap',
)

_LOCAL_NAMES = set(globals())
