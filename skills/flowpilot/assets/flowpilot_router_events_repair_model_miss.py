"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
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

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _validate_model_miss_flowguard_operator_report_refs(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    refs = decision.get('flowguard_operator_report_refs')
    if not isinstance(refs, list) or not refs:
        raise RouterError('model-backed repair requires non-empty flowguard_operator_report_refs')
    checked: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise RouterError('flowguard_operator_report_refs entries must be objects')
        report_path = str(ref.get('report_path') or ref.get('path') or '').strip()
        report_hash = str(ref.get('report_hash') or ref.get('hash') or '').strip()
        if not report_path:
            raise RouterError('flowguard_operator_report_refs[].report_path is required')
        if not report_hash:
            raise RouterError('flowguard_operator_report_refs[].report_hash is required')
        path = resolve_project_path(project_root, report_path)
        if not path.exists():
            raise RouterError(f'FlowGuard operator model-miss report path does not exist: {report_path}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != report_hash:
            raise RouterError(f'FlowGuard operator model-miss report hash mismatch for {report_path}')
        report = read_json(path)
        missing = [field for field in MODEL_MISS_FLOWGUARD_OPERATOR_REPORT_REQUIRED_FIELDS if field not in report or report.get(field) is None]
        if missing:
            raise RouterError('FlowGuard operator model-miss report is missing required fields: ' + ', '.join(missing))
        if not isinstance(report.get('same_class_findings'), list):
            raise RouterError('FlowGuard operator model-miss report requires same_class_findings list')
        if not isinstance(report.get('candidate_repairs'), list) or not report.get('candidate_repairs'):
            raise RouterError('FlowGuard operator model-miss report requires non-empty candidate_repairs')
        if not isinstance(report.get('minimal_sufficient_repair_recommendation'), dict):
            raise RouterError('FlowGuard operator model-miss report requires minimal_sufficient_repair_recommendation object')
        contract_self_check = report.get('contract_self_check')
        if not isinstance(contract_self_check, dict):
            raise RouterError('FlowGuard operator model-miss report requires contract_self_check')
        if contract_self_check.get('all_required_fields_present') is not True:
            raise RouterError('FlowGuard operator model-miss report requires contract_self_check.all_required_fields_present=true')
        if contract_self_check.get('exact_field_names_used') is not True:
            raise RouterError('FlowGuard operator model-miss report requires contract_self_check.exact_field_names_used=true')
        checked.append({'index': index, 'flowguard_operator_role': ref.get('flowguard_operator_role') or report.get('reported_by_role'), 'report_path': report_path, 'report_hash': report_hash, 'same_class_finding_count': len(report.get('same_class_findings') or []), 'candidate_repair_count': len(report.get('candidate_repairs') or [])})
    return checked

def _write_model_miss_triage_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    _bind_router(router)
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get('decided_by_role') != 'project_manager':
        raise RouterError('model-miss triage decision requires decided_by_role=project_manager')
    _require_single_active_model_miss_review_block(run_state, 'model-miss triage decision')
    missing = [field for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS if field not in decision or decision.get(field) is None]
    if missing:
        raise RouterError('model-miss triage decision is missing required fields: ' + ', '.join(missing))
    decision_value = str(decision.get('decision') or '').strip()
    if decision_value not in PM_MODEL_MISS_TRIAGE_DECISION_ALLOWED_VALUES:
        raise RouterError('model-miss triage decision is not an allowed value')
    if not str(decision.get('defect_or_blocker_id') or '').strip():
        raise RouterError('model-miss triage decision requires defect_or_blocker_id')
    block_source = str(decision.get('reviewer_block_source_path') or '').strip()
    if not block_source:
        raise RouterError('model-miss triage decision requires reviewer_block_source_path')
    if not resolve_project_path(project_root, block_source).exists():
        raise RouterError('model-miss triage reviewer_block_source_path must exist')
    scope = decision.get('model_miss_scope')
    if not isinstance(scope, dict) or not str(scope.get('bug_class_definition') or '').strip():
        raise RouterError('model-miss triage decision requires model_miss_scope.bug_class_definition')
    capability = decision.get('flowguard_capability')
    if not isinstance(capability, dict) or not isinstance(capability.get('can_model_bug_class'), bool):
        raise RouterError('model-miss triage decision requires flowguard_capability.can_model_bug_class boolean')
    blockers = decision.get('blockers')
    if not isinstance(blockers, list):
        raise RouterError('model-miss triage decision requires blockers list')
    contract_self_check = decision.get('contract_self_check')
    if not isinstance(contract_self_check, dict):
        raise RouterError('model-miss triage decision requires contract_self_check')
    if contract_self_check.get('all_required_fields_present') is not True:
        raise RouterError('model-miss triage decision requires contract_self_check.all_required_fields_present=true')
    if contract_self_check.get('exact_field_names_used') is not True:
        raise RouterError('model-miss triage decision requires contract_self_check.exact_field_names_used=true')
    checked_reports: list[dict[str, Any]] = []
    if decision_value == 'proceed_with_model_backed_repair':
        if capability.get('can_model_bug_class') is not True:
            raise RouterError('model-backed repair requires flowguard_capability.can_model_bug_class=true')
        if decision.get('same_class_findings_reviewed') is not True:
            raise RouterError('model-backed repair requires same_class_findings_reviewed=true')
        if decision.get('repair_recommendation_reviewed') is not True:
            raise RouterError('model-backed repair requires repair_recommendation_reviewed=true')
        if not decision.get('candidate_repairs_considered'):
            raise RouterError('model-backed repair requires candidate_repairs_considered')
        if not isinstance(decision.get('minimal_sufficient_repair_recommendation'), dict):
            raise RouterError('model-backed repair requires minimal_sufficient_repair_recommendation object')
        if not decision.get('post_repair_model_checks_required'):
            raise RouterError('model-backed repair requires post_repair_model_checks_required')
        checked_reports = router._validate_model_miss_flowguard_operator_report_refs(project_root, decision)
    elif decision_value == 'out_of_scope_not_modelable':
        if capability.get('can_model_bug_class') is not False:
            raise RouterError('out-of-scope repair requires flowguard_capability.can_model_bug_class=false')
        if not str(capability.get('incapability_reason') or '').strip():
            raise RouterError('out-of-scope repair requires flowguard_capability.incapability_reason')
    elif decision_value in {'request_flowguard_operator_model_miss_analysis', 'needs_evidence_before_modeling', 'stop_for_user'}:
        if decision.get('same_class_findings_reviewed') is True or decision.get('repair_recommendation_reviewed') is True:
            raise RouterError('non-authorizing model-miss decision must not claim reviewed repair evidence')
    if decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        if not str(decision.get('selected_next_action') or '').strip():
            raise RouterError('repair-authorizing model-miss decision requires selected_next_action')
        if not str(decision.get('why_repair_may_start') or '').strip():
            raise RouterError('repair-authorizing model-miss decision requires why_repair_may_start')
    output = {'schema_version': 'flowpilot.pm_model_miss_triage_decision.v1', 'run_id': run_state['run_id'], 'recorded_at': utc_now(), 'decision': decision_value, 'repair_authorized': decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES, 'checked_flowguard_operator_reports': checked_reports, **{field: decision.get(field) for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS}, **_role_output_envelope_record(decision)}
    if 'flowguard_operator_report_refs' in decision:
        output['flowguard_operator_report_refs'] = decision.get('flowguard_operator_report_refs')
    if 'minimal_sufficient_repair_recommendation' in decision:
        output['minimal_sufficient_repair_recommendation'] = decision.get('minimal_sufficient_repair_recommendation')
    if 'post_repair_model_checks_required' in decision:
        output['post_repair_model_checks_required'] = decision.get('post_repair_model_checks_required')
    decisions_dir = run_root / 'defects' / 'model_miss_triage'
    safe_id = ''.join((char if char.isalnum() or char in {'-', '_'} else '-' for char in str(decision.get('defect_or_blocker_id') or 'model-miss'))).strip('-') or 'model-miss'
    decision_path = decisions_dir / f'{safe_id}.pm_model_miss_triage_decision.json'
    write_json(decision_path, output)
    run_state['model_miss_triage'] = {'decision': decision_value, 'repair_authorized': output['repair_authorized'], 'decision_path': project_relative(project_root, decision_path), 'decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'defect_or_blocker_id': decision.get('defect_or_blocker_id'), 'checked_flowguard_operator_reports': checked_reports}
    run_state['flags']['model_miss_triage_followup_request_pending'] = False
    if decision_value == 'request_flowguard_operator_model_miss_analysis':
        run_state['model_miss_triage_followup_request'] = {'schema_version': 'flowpilot.model_miss_triage_followup_request.v1', 'status': 'awaiting_pm_role_work_request', 'source_decision_path': project_relative(project_root, decision_path), 'source_decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'required_request_kind': 'model_miss', 'required_output_contract_id': 'flowpilot.output_contract.flowguard_model_miss_report.v1', 'suggested_to_roles': ['flowguard_operator'], 'required_event': PM_ROLE_WORK_REQUEST_EVENT, 'reason': 'model_miss_triage_followup_request', 'created_at': utc_now()}
        run_state['flags']['model_miss_triage_followup_request_pending'] = True
    elif decision_value == 'needs_evidence_before_modeling':
        run_state['model_miss_evidence_followup_request'] = {'schema_version': 'flowpilot.model_miss_evidence_followup_request.v1', 'status': 'awaiting_pm_role_work_request', 'source_decision_path': project_relative(project_root, decision_path), 'source_decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'required_request_kind': 'evidence', 'required_output_contract_id': None, 'suggested_to_roles': sorted(PM_ROLE_WORK_REQUEST_RECIPIENT_ROLES), 'required_event': PM_ROLE_WORK_REQUEST_EVENT, 'reason': 'model_miss_evidence_followup_request', 'created_at': utc_now()}
        run_state['flags']['model_miss_triage_followup_request_pending'] = True
    elif decision_value == 'stop_for_user':
        run_state['model_miss_triage_controlled_stop'] = {'schema_version': 'flowpilot.model_miss_triage_controlled_stop.v1', 'status': 'waiting_for_user', 'source_decision_path': project_relative(project_root, decision_path), 'source_decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'reason': 'model_miss_triage_controlled_stop', 'created_at': utc_now()}
        run_state['flags']['model_miss_triage_controlled_stop_recorded'] = True
    elif decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        run_state['model_miss_triage_followup_request'] = None
        run_state['model_miss_evidence_followup_request'] = None
        run_state['model_miss_triage_controlled_stop'] = None
    return decision_value

__all__ = (
    '_validate_model_miss_flowguard_operator_report_refs',
    '_write_model_miss_triage_decision',
)

_LOCAL_NAMES = set(globals())
