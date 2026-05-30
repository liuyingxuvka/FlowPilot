"""startup fact report and repair writers helpers for ``flowpilot_router_startup_fact_boundary``.

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
    activation = {'schema_version': 'flowpilot.startup_activation.v1', 'run_id': run_state['run_id'], 'approved_by_role': 'project_manager', 'decision': 'approved', 'runtime_role_assistances': answers.get('runtime_role_assistances'), 'scheduled_continuation': answers.get('scheduled_continuation'), 'display_surface': answers.get('display_surface'), 'fact_report_path': project_relative(project_root, fact_report_path), 'approval_basis': approval_basis, 'approved_at': utc_now(), **_role_output_envelope_record(payload)}
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

__all__ = (
    '_write_startup_fact_report',
    '_write_startup_activation',
    '_write_startup_repair_request',
    '_write_startup_protocol_dead_end',
)

_LOCAL_NAMES = set(globals())
