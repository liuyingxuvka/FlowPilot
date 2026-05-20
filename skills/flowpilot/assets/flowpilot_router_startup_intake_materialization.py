"""startup intake materialization and deterministic seed helpers for ``flowpilot_router_startup_intake``.

This child module is imported by the compatibility facade and keeps
router binding behavior explicit for the startup StructureMesh split.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
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

def _flowguard_capability_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'capability_snapshot.json'

def _portable_skill_search_roots(router: ModuleType, project_root: Path) -> list[Path]:
    _bind_router(router)
    candidates: list[Path] = []
    try:
        candidates.append(skill_root().parent)
    except Exception:
        pass
    codex_home = os.environ.get('CODEX_HOME')
    if codex_home:
        candidates.append(Path(codex_home) / 'skills')
    candidates.append(Path.home() / '.codex' / 'skills')
    candidates.append(project_root / 'skills')
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists():
            roots.append(resolved)
    return roots

def _flowguard_route_classification(skill_name: str) -> dict[str, Any]:
    name = skill_name.lower()
    if name == 'model-first-function-flow':
        return {'route_description': 'Core model-first behavior and route-selection kernel.', 'role_fit': ['project_manager', 'product_flowguard_officer', 'process_flowguard_officer'], 'model_family_fit': ['product_behavior', 'route_process', 'cross_route_coordination']}
    if 'ui' in name:
        return {'route_description': 'UI interaction behavior, visible control topology, and recovery-state modeling.', 'role_fit': ['project_manager', 'product_flowguard_officer'], 'model_family_fit': ['ui_interaction', 'product_behavior']}
    if 'development-process' in name:
        return {'route_description': 'Staged development process, validation freshness, and done-claim modeling.', 'role_fit': ['project_manager', 'process_flowguard_officer'], 'model_family_fit': ['route_process', 'validation_evidence']}
    if 'code-structure' in name or 'structure-mesh' in name:
        return {'route_description': 'Architecture, module ownership, facade, and structure-governance modeling.', 'role_fit': ['project_manager', 'product_flowguard_officer', 'process_flowguard_officer'], 'model_family_fit': ['data_state', 'route_hierarchy', 'architecture']}
    if 'model-test' in name:
        return {'route_description': 'Model obligations compared against ordinary tests and executable evidence.', 'role_fit': ['project_manager', 'process_flowguard_officer'], 'model_family_fit': ['validation_evidence', 'model_test_alignment']}
    if 'test-mesh' in name:
        return {'route_description': 'Layered test hierarchy, slow-check freshness, and evidence-mesh modeling.', 'role_fit': ['project_manager', 'process_flowguard_officer'], 'model_family_fit': ['validation_evidence', 'test_hierarchy']}
    if 'model-mesh' in name:
        return {'route_description': 'Parent/child model-family split, stale child evidence, and sibling coverage governance.', 'role_fit': ['project_manager', 'product_flowguard_officer', 'process_flowguard_officer'], 'model_family_fit': ['model_family_governance']}
    if 'model-miss' in name:
        return {'route_description': 'Post-failure model-miss review and generalized bad-case modeling.', 'role_fit': ['project_manager', 'product_flowguard_officer', 'process_flowguard_officer'], 'model_family_fit': ['failure_recovery', 'model_test_alignment']}
    return {'route_description': 'FlowGuard route available for PM-selected modeling coverage.', 'role_fit': ['project_manager', 'product_flowguard_officer', 'process_flowguard_officer'], 'model_family_fit': ['product_behavior', 'route_process']}

def _discover_flowguard_skill_routes(router: ModuleType, project_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    _bind_router(router)
    routes: list[dict[str, Any]] = []
    roots = _portable_skill_search_roots(router, project_root)
    for root in roots:
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            if not (skill_name.startswith('flowguard-') or skill_name == 'model-first-function-flow'):
                continue
            skill_md = skill_dir / 'SKILL.md'
            if not skill_md.exists():
                continue
            classification = _flowguard_route_classification(skill_name)
            routes.append({
                'skill_name': skill_name,
                'source_path': str(skill_md),
                'source_hash_sha256': hashlib.sha256(skill_md.read_bytes()).hexdigest(),
                'search_root': str(root),
                **classification,
            })
    deduped: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for route in routes:
        name = str(route.get('skill_name') or '')
        if name in seen_names:
            continue
        seen_names.add(name)
        deduped.append(route)
    return deduped, [str(root) for root in roots]

def _flowguard_import_snapshot() -> dict[str, Any]:
    try:
        import flowguard  # type: ignore
    except Exception as exc:
        return {'importable': False, 'error': f'{type(exc).__name__}: {exc}', 'python_executable': sys.executable}
    package_version = None
    try:
        package_version = importlib.metadata.version('flowguard')
    except importlib.metadata.PackageNotFoundError:
        package_version = None
    return {
        'importable': True,
        'schema_version': getattr(flowguard, 'SCHEMA_VERSION', None),
        'module_path': str(Path(getattr(flowguard, '__file__', '') or '').resolve()),
        'package_version': package_version,
        'python_executable': sys.executable,
    }

def _write_flowguard_capability_snapshot(router: ModuleType, project_root: Path, run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    path = _flowguard_capability_snapshot_path(router, run_root)
    routes, search_roots = _discover_flowguard_skill_routes(router, project_root)
    snapshot = {
        'schema_version': 'flowpilot.flowguard_capability_snapshot.v1',
        'snapshot_id': f"{state.get('run_id') or run_root.name}-flowguard-capability-snapshot",
        'run_id': state.get('run_id') or run_root.name,
        'generated_at': utc_now(),
        'generated_by_role_key': 'router',
        'policy': {
            'flowguard_is_required_foundation': True,
            'ordinary_child_skill': False,
            'pm_must_read_before_product_modeling': True,
            'mid_run_upgrade_policy': 'snapshot is fixed for this run; later FlowGuard upgrades apply to later runs',
        },
        'portable_resolution': {
            'hardcoded_user_path_required': False,
            'generator': 'flowpilot_router_startup_seed',
            'skill_root_source': str(skill_root()),
            'search_roots': search_roots,
            'resolution_rule': 'scan installed Codex skills and project-local skills on the current host at startup',
        },
        'flowguard_import': _flowguard_import_snapshot(),
        'capability_menu': [
            {'capability_id': 'flowguard_startup_capability_snapshot', 'required_before': 'pm_product_architecture'},
            {'capability_id': 'product_modeling_plan', 'owned_by': 'project_manager'},
            {'capability_id': 'product_model_family_coverage', 'owned_by': 'product_flowguard_officer'},
            {'capability_id': 'ordinary_child_skill_projection', 'owned_by': 'project_manager'},
            {'capability_id': 'process_modeling_plan', 'owned_by': 'project_manager'},
            {'capability_id': 'process_model_family_coverage', 'owned_by': 'process_flowguard_officer'},
            {'capability_id': 'model_test_alignment', 'owned_by': 'project_manager'},
            {'capability_id': 'final_modeling_coverage_ledger', 'owned_by': 'project_manager'},
        ],
        'skill_routes': routes,
        'pm_summary': {
            'must_read_before_product_modeling': True,
            'decide_model_family_count_before_product_officer_task': True,
            'ordinary_child_skills_are_selected_after_product_model_family_acceptance': True,
            'process_modeling_plan_required_before_route_activation': True,
            'final_ledger_must_close_all_model_families': True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, snapshot)
    rel_path = project_relative(project_root, path)
    state['flowguard_capability_snapshot_path'] = rel_path
    state.setdefault('flags', {})['flowguard_capability_snapshot_written'] = True
    return {'path': rel_path, 'skill_route_count': len(routes), 'search_roots': search_roots, 'flowguard_importable': snapshot['flowguard_import']['importable']}

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
)

_LOCAL_NAMES = set(globals())
