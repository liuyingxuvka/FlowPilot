"""Coarse events repair owner helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`. This module owns a
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


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value

def _validate_model_miss_officer_report_refs(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    refs = decision.get('officer_report_refs')
    if not isinstance(refs, list) or not refs:
        raise RouterError('model-backed repair requires non-empty officer_report_refs')
    checked: list[dict[str, Any]] = []
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            raise RouterError('officer_report_refs entries must be objects')
        report_path = str(ref.get('report_path') or ref.get('path') or '').strip()
        report_hash = str(ref.get('report_hash') or ref.get('hash') or '').strip()
        if not report_path:
            raise RouterError('officer_report_refs[].report_path is required')
        if not report_hash:
            raise RouterError('officer_report_refs[].report_hash is required')
        path = resolve_project_path(project_root, report_path)
        if not path.exists():
            raise RouterError(f'officer model-miss report path does not exist: {report_path}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != report_hash:
            raise RouterError(f'officer model-miss report hash mismatch for {report_path}')
        report = read_json(path)
        missing = [field for field in MODEL_MISS_OFFICER_REPORT_REQUIRED_FIELDS if field not in report or report.get(field) is None]
        if missing:
            raise RouterError('officer model-miss report is missing required fields: ' + ', '.join(missing))
        if not isinstance(report.get('same_class_findings'), list):
            raise RouterError('officer model-miss report requires same_class_findings list')
        if not isinstance(report.get('candidate_repairs'), list) or not report.get('candidate_repairs'):
            raise RouterError('officer model-miss report requires non-empty candidate_repairs')
        if not isinstance(report.get('minimal_sufficient_repair_recommendation'), dict):
            raise RouterError('officer model-miss report requires minimal_sufficient_repair_recommendation object')
        contract_self_check = report.get('contract_self_check')
        if not isinstance(contract_self_check, dict):
            raise RouterError('officer model-miss report requires contract_self_check')
        if contract_self_check.get('all_required_fields_present') is not True:
            raise RouterError('officer model-miss report requires contract_self_check.all_required_fields_present=true')
        if contract_self_check.get('exact_field_names_used') is not True:
            raise RouterError('officer model-miss report requires contract_self_check.exact_field_names_used=true')
        checked.append({'index': index, 'officer_role': ref.get('officer_role') or report.get('reported_by_role'), 'report_path': report_path, 'report_hash': report_hash, 'same_class_finding_count': len(report.get('same_class_findings') or []), 'candidate_repair_count': len(report.get('candidate_repairs') or [])})
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
        checked_reports = router._validate_model_miss_officer_report_refs(project_root, decision)
    elif decision_value == 'out_of_scope_not_modelable':
        if capability.get('can_model_bug_class') is not False:
            raise RouterError('out-of-scope repair requires flowguard_capability.can_model_bug_class=false')
        if not str(capability.get('incapability_reason') or '').strip():
            raise RouterError('out-of-scope repair requires flowguard_capability.incapability_reason')
    elif decision_value in {'request_officer_model_miss_analysis', 'needs_evidence_before_modeling', 'stop_for_user'}:
        if decision.get('same_class_findings_reviewed') is True or decision.get('repair_recommendation_reviewed') is True:
            raise RouterError('non-authorizing model-miss decision must not claim reviewed repair evidence')
    if decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES:
        if not str(decision.get('selected_next_action') or '').strip():
            raise RouterError('repair-authorizing model-miss decision requires selected_next_action')
        if not str(decision.get('why_repair_may_start') or '').strip():
            raise RouterError('repair-authorizing model-miss decision requires why_repair_may_start')
    output = {'schema_version': 'flowpilot.pm_model_miss_triage_decision.v1', 'run_id': run_state['run_id'], 'recorded_at': utc_now(), 'decision': decision_value, 'repair_authorized': decision_value in PM_MODEL_MISS_TRIAGE_REPAIR_AUTHORIZED_VALUES, 'checked_officer_reports': checked_reports, **{field: decision.get(field) for field in PM_MODEL_MISS_TRIAGE_REQUIRED_BODY_FIELDS}, **_role_output_envelope_record(decision)}
    if 'officer_report_refs' in decision:
        output['officer_report_refs'] = decision.get('officer_report_refs')
    if 'minimal_sufficient_repair_recommendation' in decision:
        output['minimal_sufficient_repair_recommendation'] = decision.get('minimal_sufficient_repair_recommendation')
    if 'post_repair_model_checks_required' in decision:
        output['post_repair_model_checks_required'] = decision.get('post_repair_model_checks_required')
    decisions_dir = run_root / 'defects' / 'model_miss_triage'
    safe_id = ''.join((char if char.isalnum() or char in {'-', '_'} else '-' for char in str(decision.get('defect_or_blocker_id') or 'model-miss'))).strip('-') or 'model-miss'
    decision_path = decisions_dir / f'{safe_id}.pm_model_miss_triage_decision.json'
    write_json(decision_path, output)
    run_state['model_miss_triage'] = {'decision': decision_value, 'repair_authorized': output['repair_authorized'], 'decision_path': project_relative(project_root, decision_path), 'decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'defect_or_blocker_id': decision.get('defect_or_blocker_id'), 'checked_officer_reports': checked_reports}
    run_state['flags']['model_miss_triage_followup_request_pending'] = False
    if decision_value == 'request_officer_model_miss_analysis':
        run_state['model_miss_triage_followup_request'] = {'schema_version': 'flowpilot.model_miss_triage_followup_request.v1', 'status': 'awaiting_pm_role_work_request', 'source_decision_path': project_relative(project_root, decision_path), 'source_decision_hash': hashlib.sha256(decision_path.read_bytes()).hexdigest(), 'required_request_kind': 'model_miss', 'required_output_contract_id': 'flowpilot.output_contract.flowguard_model_miss_report.v1', 'suggested_to_roles': ['process_flowguard_officer', 'product_flowguard_officer'], 'required_event': PM_ROLE_WORK_REQUEST_EVENT, 'reason': 'model_miss_triage_followup_request', 'created_at': utc_now()}
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

def _repair_transaction_normalized_plan_kind(router: ModuleType, raw_plan_kind: str) -> tuple[str, str | None]:
    _bind_router(router)
    requested = raw_plan_kind.strip()
    if requested in REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES:
        return (REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES[requested], requested)
    if requested in REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS:
        return (requested, None)
    allowed = sorted(REPAIR_TRANSACTION_EXECUTABLE_PLAN_KINDS | set(REPAIR_TRANSACTION_LEGACY_PLAN_KIND_ALIASES))
    raise RouterError(f"repair_transaction.plan_kind must be one of: {', '.join(allowed)}")

def _event_already_recorded(router: ModuleType, run_state: dict[str, Any], event: str) -> bool:
    _bind_router(router)
    return any((isinstance(item, dict) and item.get('event') == event for item in run_state.get('events', [])))

def _controller_wait_entries_for_event(router: ModuleType, run_root: Path, event: str) -> list[dict[str, Any]]:
    _bind_router(router)
    matches: list[dict[str, Any]] = []
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return matches
    for path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES:
            continue
        if entry.get('action_type') != 'await_role_decision':
            continue
        if event in _controller_wait_allowed_external_events(entry):
            matches.append(entry)
    return matches

def _existing_event_producer_evidence(router: ModuleType, run_root: Path, run_state: dict[str, Any], event: str) -> dict[str, Any] | None:
    _bind_router(router)
    if router._event_already_recorded(run_state, event):
        return {'source': 'already_recorded_event', 'event': event}
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') == 'await_role_decision' and (event in {str(item) for item in pending.get('allowed_external_events') or []}):
        return {'source': 'current_pending_await_role_decision', 'event': event, 'label': pending.get('label')}
    wait_entries = router._controller_wait_entries_for_event(run_root, event)
    if wait_entries:
        return {'source': 'controller_action_wait', 'event': event, 'controller_action_ids': [entry.get('action_id') for entry in wait_entries]}
    meta = EXTERNAL_EVENTS.get(event) or {}
    required_flag = str(meta.get('requires_flag') or '')
    if required_flag and run_state.get('flags', {}).get(required_flag):
        return {'source': 'satisfied_required_flag', 'event': event, 'requires_flag': required_flag, 'producer_role': _event_wait_role(event, meta)}
    return None

def _list_field(router: ModuleType, value: Any, *, field: str, required: bool=True) -> list[str]:
    _bind_router(router)
    if value in (None, '') and (not required):
        return []
    if not isinstance(value, list) or (required and (not value)):
        raise RouterError(f'{field} must be a non-empty list')
    return [str(item) for item in value if str(item or '').strip()]

def _repair_transaction_execution_plan(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], active: dict[str, Any], request: dict[str, Any], *, requested_plan_kind: str, legacy_plan_kind: str | None, rerun_target: str, repair_origin: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    if requested_plan_kind == 'packet_reissue':
        if not packet_specs:
            raise RouterError('packet_reissue repair transaction requires replacement packets or a packet spec path')
        return {'mode': 'packet_reissue', 'validated': True, 'queued_action': False, 'existing_event_producer': None}
    if packet_specs:
        raise RouterError('repair transaction with replacement packets requires plan_kind=packet_reissue')
    if requested_plan_kind == 'await_existing_event':
        evidence = router._existing_event_producer_evidence(run_root, run_state, rerun_target)
        if evidence is None:
            if legacy_plan_kind == 'event_replay':
                raise RouterError('legacy event_replay repair transaction requires an existing producer for rerun_target')
            raise RouterError('await_existing_event repair transaction requires an existing producer for rerun_target')
        return {'mode': 'await_existing_event', 'validated': True, 'queued_action': False, 'existing_event_producer': evidence, 'legacy_plan_kind': legacy_plan_kind}
    if requested_plan_kind in {'role_reissue', 'route_mutation'}:
        target_role = str(request.get('target_role') or router._control_blocker_followup_target_role([rerun_target], 'project_manager')).strip()
        router._validate_wait_event_producer_binding([rerun_target], to_role=target_role, context=f'{requested_plan_kind} repair transaction')
        return {'mode': requested_plan_kind, 'validated': True, 'queued_action': True, 'queued_action_type': 'await_role_decision', 'target_role': target_role, 'allowed_external_events': [rerun_target]}
    if requested_plan_kind == 'operation_replay':
        operation_ref = request.get('operation_ref')
        if not isinstance(operation_ref, dict):
            raise RouterError('operation_replay repair transaction requires operation_ref object')
        action_type = str(operation_ref.get('action_type') or active.get('originating_action_type') or '').strip()
        if action_type not in REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES:
            raise RouterError(f"operation_replay repair transaction cannot replay action_type={action_type or 'missing'}")
        originating_action_id = str(operation_ref.get('controller_action_id') or active.get('originating_controller_action_id') or '').strip()
        replay_source: dict[str, Any] = {'action_type': action_type, 'controller_action_id': originating_action_id or None, 'operation_ref': operation_ref}
        if originating_action_id:
            action_entry = read_json_if_exists(_controller_action_path(run_root, originating_action_id))
            if action_entry.get('schema_version') == CONTROLLER_ACTION_SCHEMA:
                replay_source['source_action'] = action_entry.get('action')
        return {'mode': 'operation_replay', 'validated': True, 'queued_action': True, 'queued_action_type': action_type, 'operation_ref': operation_ref, 'replay_source': {key: value for key, value in replay_source.items() if value is not None}}
    if requested_plan_kind == 'controller_repair_work_packet':
        work_packet = request.get('work_packet') if isinstance(request.get('work_packet'), dict) else request
        allowed_reads = router._list_field(work_packet.get('allowed_reads'), field='controller_repair_work_packet.allowed_reads')
        allowed_writes = router._list_field(work_packet.get('allowed_writes'), field='controller_repair_work_packet.allowed_writes', required=False)
        forbidden_actions = router._list_field(work_packet.get('forbidden_actions'), field='controller_repair_work_packet.forbidden_actions')
        success_evidence = router._list_field(work_packet.get('success_evidence'), field='controller_repair_work_packet.success_evidence')
        return {'mode': 'controller_repair_work_packet', 'validated': True, 'queued_action': True, 'queued_action_type': 'controller_repair_work_packet', 'allowed_reads': allowed_reads, 'allowed_writes': allowed_writes, 'forbidden_actions': forbidden_actions, 'success_evidence': success_evidence, 'work_packet': work_packet}
    if requested_plan_kind == 'router_internal_reconcile':
        handler = str(request.get('handler') or request.get('reconcile_handler') or '').strip()
        if handler not in {'fold_mail_delivery_postcondition'}:
            raise RouterError('router_internal_reconcile repair transaction requires a supported reconcile handler')
        return {'mode': 'router_internal_reconcile', 'validated': True, 'queued_action': False, 'handler': handler}
    if requested_plan_kind == 'terminal_stop':
        reason = str(request.get('terminal_reason') or request.get('stop_reason') or '').strip()
        if not reason:
            raise RouterError('terminal_stop repair transaction requires terminal_reason')
        return {'mode': 'terminal_stop', 'validated': True, 'queued_action': False, 'terminal_reason': reason, 'repair_origin': repair_origin}
    raise RouterError(f'unsupported repair_transaction.plan_kind: {requested_plan_kind}')

def _write_control_blocker_repair_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    decision = _load_file_backed_role_payload(project_root, payload)
    if decision.get('decided_by_role') != 'project_manager':
        raise RouterError('control blocker repair decision requires decided_by_role=project_manager')
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('delivery_status') != 'delivered':
        raise RouterError('control blocker repair decision requires a delivered active control blocker')
    active_record = router._control_blocker_record(project_root, active)
    blocker_id = str(decision.get('blocker_id') or '')
    if blocker_id != active.get('blocker_id'):
        raise RouterError('control blocker repair decision must reference the active blocker_id')
    allowed_decisions = {'repair_completed', 'repair_not_required', 'resolved_by_followup_event', 'continue_after_pm_review'}
    if decision.get('decision') not in allowed_decisions:
        raise RouterError('control blocker repair decision is not an allowed PM repair decision')
    prior_path_context_review = decision.get('prior_path_context_review')
    if not isinstance(prior_path_context_review, dict) or prior_path_context_review.get('reviewed') is not True:
        raise RouterError('control blocker repair decision requires prior_path_context_review.reviewed=true')
    source_paths = prior_path_context_review.get('source_paths')
    if not isinstance(source_paths, list):
        raise RouterError('control blocker repair decision requires prior_path_context_review.source_paths list')
    repair_action = str(decision.get('repair_action') or '').strip()
    if not repair_action:
        raise RouterError('control blocker repair decision requires repair_action')
    repair_transaction_request = decision.get('repair_transaction')
    if not isinstance(repair_transaction_request, dict):
        raise RouterError('control blocker repair decision requires repair_transaction')
    raw_requested_plan_kind = str(repair_transaction_request.get('plan_kind') or '').strip()
    requested_plan_kind, legacy_plan_kind = router._repair_transaction_normalized_plan_kind(raw_requested_plan_kind)
    raw_rerun_target = decision.get('rerun_target')
    rerun_target = router._control_resolution_event_name(raw_rerun_target)
    if requested_plan_kind != 'terminal_stop':
        if not rerun_target:
            raise RouterError('control blocker repair decision rerun_target must name a registered external event')
        if rerun_target == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
            raise RouterError('control blocker repair decision rerun_target must name a corrected follow-up event, not the PM decision event')
    else:
        rerun_target = rerun_target or ''
    policy_recovery_options = active_record.get('pm_recovery_options')
    if not isinstance(policy_recovery_options, list):
        policy_recovery_options = []
    recovery_option = str(decision.get('recovery_option') or router._default_pm_recovery_option(active_record, requested_plan_kind)).strip()
    if not recovery_option:
        raise RouterError('control blocker repair decision requires recovery_option')
    if policy_recovery_options and recovery_option not in {str(item) for item in policy_recovery_options}:
        raise RouterError('control blocker repair decision recovery_option is not allowed by blocker policy')
    hard_stop_conditions = active_record.get('hard_stop_conditions')
    if not isinstance(hard_stop_conditions, list):
        hard_stop_conditions = []
    if recovery_option == 'allowed_waiver' and hard_stop_conditions:
        raise RouterError('control blocker repair decision cannot waive a blocker with hard-stop conditions')
    return_gate = str(decision.get('return_gate') or rerun_target or requested_plan_kind).strip()
    if not return_gate:
        raise RouterError('control blocker repair decision requires return_gate or rerun_target')
    control_transaction = _validate_control_transaction_requirements(run_root, transaction_type='control_blocker_repair', producer_role='project_manager', output_contract_id='flowpilot.output_contract.pm_control_blocker_repair_decision.v1', router_events=(PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT, PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT, PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT), required_event_usages=('recorded_event', 'rerun_target', 'repair_outcome'), required_commit_targets=('repair_transaction', 'blocker_index', 'run_state', 'status_summary'), require_repair_transaction=True, outcome_policy='three_distinct_outcomes')
    repair_origin = router._control_blocker_repair_origin(active, rerun_target=rerun_target or requested_plan_kind, requested_plan_kind=requested_plan_kind, run_root=run_root, run_state=run_state)
    post_decision_state = router._run_state_with_assumed_flag(run_state, 'pm_control_blocker_repair_decision_recorded')
    if requested_plan_kind != 'terminal_stop':
        rerun_target = router._validated_event_capability_names([rerun_target], context='control blocker repair decision rerun_target', run_root=run_root, run_state=post_decision_state, usage='rerun_target', repair_origin=repair_origin, allow_pm_repair_event=False)[0]
    blockers = decision.get('blockers')
    if not isinstance(blockers, list):
        raise RouterError('control blocker repair decision requires blockers list')
    contract_self_check = decision.get('contract_self_check')
    if not isinstance(contract_self_check, dict):
        raise RouterError('control blocker repair decision requires contract_self_check')
    if contract_self_check.get('all_required_fields_present') is not True:
        raise RouterError('control blocker repair decision requires contract_self_check.all_required_fields_present=true')
    if contract_self_check.get('exact_field_names_used') is not True:
        raise RouterError('control blocker repair decision requires contract_self_check.exact_field_names_used=true')
    if requested_plan_kind == 'terminal_stop':
        outcome_table = {}
        allowed_resolution_events: list[str] = []
    else:
        outcome_table = router._repair_outcome_table(rerun_target, repair_origin=repair_origin)
        router._validate_repair_outcome_table(outcome_table, context='control blocker repair outcome table', run_root=run_root, run_state=post_decision_state, repair_origin=repair_origin)
        allowed_resolution_events = router._validated_event_capability_names(router._repair_outcome_events(outcome_table), context='control blocker repair outcome table', run_root=run_root, run_state=post_decision_state, usage='wait', repair_origin=repair_origin, allow_pm_repair_event=False)
    transaction_id = router._repair_transaction_id(blocker_id)
    packet_generation_id = f'{transaction_id}-gen-001'
    packet_specs, packet_spec_source = router._repair_packet_specs_from_decision(project_root, run_root, decision, rerun_target=rerun_target)
    execution_plan = router._repair_transaction_execution_plan(project_root, run_root, post_decision_state, active, repair_transaction_request, requested_plan_kind=requested_plan_kind, legacy_plan_kind=legacy_plan_kind, rerun_target=rerun_target, repair_origin=repair_origin, packet_specs=packet_specs)
    plan_kind = requested_plan_kind
    if packet_specs and rerun_target not in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
        raise RouterError('repair transaction packet reissue is currently supported only for material scan dispatch')
    output = {'schema_version': 'flowpilot.control_blocker_repair_decision.v1', 'run_id': run_state['run_id'], 'blocker_id': blocker_id, 'decided_by_role': 'project_manager', 'decision': decision['decision'], 'repair_transaction_id': transaction_id, 'prior_path_context_review': prior_path_context_review, 'repair_action': repair_action, 'recovery_option': recovery_option, 'return_gate': return_gate, 'policy_row_id': active_record.get('policy_row_id'), 'blocker_family': active_record.get('blocker_family'), 'repair_origin': repair_origin, 'rerun_target': rerun_target, 'outcome_table': outcome_table, 'legacy_plan_kind': legacy_plan_kind, 'execution_plan': execution_plan, 'control_transaction': control_transaction, 'blockers': blockers, 'contract_self_check': contract_self_check, 'recorded_at': utc_now(), **_role_output_envelope_record(decision)}
    decision_path = run_root / 'control_blocks' / f'{blocker_id}.pm_repair_decision.json'
    write_json(decision_path, output)
    generation_commit: dict[str, Any] | None = None
    if packet_specs:
        generation_commit = router._commit_material_scan_repair_generation(project_root, run_root, run_state, transaction_id=transaction_id, packet_generation_id=packet_generation_id, packet_specs=packet_specs)
        router._set_pre_route_frontier_phase(run_root, str(run_state['run_id']), 'material_scan')
        run_state['phase'] = 'material_scan'
    transaction = {'schema_version': REPAIR_TRANSACTION_SCHEMA, 'transaction_id': transaction_id, 'run_id': run_state['run_id'], 'blocker_id': blocker_id, 'originating_event': active.get('originating_event'), 'originating_action_type': active.get('originating_action_type'), 'status': 'blocked' if requested_plan_kind == 'terminal_stop' else 'committed', 'plan_kind': plan_kind, 'legacy_plan_kind': legacy_plan_kind, 'execution_plan': execution_plan, 'packet_generation_id': packet_generation_id if generation_commit else None, 'packet_spec_source': packet_spec_source, 'generation_commit': generation_commit, 'pm_repair_decision_path': project_relative(project_root, decision_path), 'repair_origin': repair_origin, 'recovery_option': recovery_option, 'return_gate': return_gate, 'policy_row_id': active_record.get('policy_row_id'), 'rerun_target': rerun_target, 'outcome_table': outcome_table, 'control_transaction': control_transaction, 'allowed_resolution_events': allowed_resolution_events, 'opened_at': output['recorded_at'], 'committed_at': utc_now()}
    write_json(router._repair_transaction_path(run_root, transaction_id), transaction)
    active_path = resolve_project_path(project_root, str(active.get('blocker_artifact_path') or ''))
    decision_rel = project_relative(project_root, decision_path)
    decision_hash = hashlib.sha256(decision_path.read_bytes()).hexdigest()
    if active_path.exists():
        record = read_json(active_path)
        record['pm_repair_decision_status'] = 'recorded'
        record['pm_repair_decision_path'] = decision_rel
        record['pm_repair_decision_hash'] = decision_hash
        record['pm_repair_rerun_target'] = rerun_target
        record['pm_recovery_option'] = recovery_option
        record['pm_repair_return_gate'] = return_gate
        record['repair_origin'] = repair_origin
        record['repair_transaction_id'] = transaction_id
        record['repair_transaction_path'] = project_relative(project_root, router._repair_transaction_path(run_root, transaction_id))
        record['repair_outcome_table'] = outcome_table
        record['repair_transaction_plan_kind'] = plan_kind
        record['repair_transaction_legacy_plan_kind'] = legacy_plan_kind
        record['repair_transaction_execution_plan'] = execution_plan
        record['control_transaction'] = control_transaction
        record['allowed_resolution_events'] = allowed_resolution_events
        record['resolution_status'] = None
        write_json(active_path, record)
    active['pm_repair_decision_status'] = 'recorded'
    active['pm_repair_decision_path'] = decision_rel
    active['pm_repair_decision_hash'] = decision_hash
    active['pm_repair_rerun_target'] = rerun_target
    active['pm_recovery_option'] = recovery_option
    active['pm_repair_return_gate'] = return_gate
    active['repair_origin'] = repair_origin
    active['repair_transaction_id'] = transaction_id
    active['repair_transaction_path'] = project_relative(project_root, router._repair_transaction_path(run_root, transaction_id))
    active['repair_outcome_table'] = outcome_table
    active['repair_transaction_plan_kind'] = plan_kind
    active['repair_transaction_legacy_plan_kind'] = legacy_plan_kind
    active['repair_transaction_execution_plan'] = execution_plan
    active['control_transaction'] = control_transaction
    active['allowed_resolution_events'] = allowed_resolution_events
    if requested_plan_kind == 'terminal_stop':
        resolved = dict(active)
        resolved['resolution_status'] = 'repair_transaction_terminal_stop'
        resolved['resolved_at'] = utc_now()
        resolved['terminal_reason'] = execution_plan.get('terminal_reason')
        run_state.setdefault('resolved_control_blockers', []).append(resolved)
        if active_path.exists():
            terminal_record = read_json(active_path)
            terminal_record['resolution_status'] = 'repair_transaction_terminal_stop'
            terminal_record['resolved_at'] = resolved['resolved_at']
            terminal_record['terminal_reason'] = execution_plan.get('terminal_reason')
            write_json(active_path, terminal_record)
        run_state['active_control_blocker'] = None
        run_state['latest_control_blocker_path'] = None
        if recovery_option == 'protocol_dead_end':
            run_state['status'] = 'protocol_dead_end'
            run_state.setdefault('flags', {})['startup_protocol_dead_end_declared'] = True
        elif recovery_option == 'user_stop':
            run_state['status'] = 'stopped_by_user'
            run_state.setdefault('flags', {})['run_stopped_by_user'] = True
    router._sync_control_plane_indexes(project_root, run_root, run_state)

def _gate_decision_issue(router: ModuleType, field: str, message: str, owner: str='gate_owner') -> dict[str, str]:
    _bind_router(router)
    return {'field': field, 'message': message, 'owner': owner}

def _gate_decision_safe_id(router: ModuleType, raw: str) -> str:
    _bind_router(router)
    chars: list[str] = []
    for char in raw.strip().lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != '-':
            chars.append('-')
    safe = ''.join(chars).strip('-')
    return safe[:96] or 'gate-decision'

def _gate_decision_issues(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    if not isinstance(decision, dict):
        return [router._gate_decision_issue('gate_decision', 'GateDecision must be a JSON object')]
    for field in GATE_DECISION_REQUIRED_FIELDS:
        if field not in decision or decision.get(field) in (None, ''):
            issues.append(router._gate_decision_issue(field, 'missing required GateDecision field'))
    if decision.get('gate_decision_version') != GATE_DECISION_SCHEMA:
        issues.append(router._gate_decision_issue('gate_decision_version', f'must equal {GATE_DECISION_SCHEMA}'))
    enum_specs = (('gate_kind', GATE_DECISION_ALLOWED_KINDS), ('owner_role', GATE_DECISION_ALLOWED_OWNER_ROLES), ('risk_type', GATE_DECISION_ALLOWED_RISKS), ('gate_strength', GATE_DECISION_ALLOWED_STRENGTHS), ('decision', GATE_DECISION_ALLOWED_DECISIONS), ('next_action', GATE_DECISION_ALLOWED_NEXT_ACTIONS))
    for field, allowed in enum_specs:
        if field in decision and decision.get(field) not in allowed:
            issues.append(router._gate_decision_issue(field, f'unsupported value: {decision.get(field)}'))
    leaked_overreach = sorted(GATE_DECISION_SEMANTIC_OVERREACH_FIELDS & set(decision))
    if leaked_overreach:
        issues.append(router._gate_decision_issue(','.join(leaked_overreach), 'router may record only mechanical GateDecision conformance, not semantic sufficiency', 'flowpilot_router'))
    if 'blocking' in decision and (not isinstance(decision.get('blocking'), bool)):
        issues.append(router._gate_decision_issue('blocking', 'must be a boolean'))
    required_evidence = decision.get('required_evidence')
    if not isinstance(required_evidence, list) or any((not isinstance(item, str) for item in required_evidence)):
        issues.append(router._gate_decision_issue('required_evidence', 'must be a list of strings'))
    evidence_refs = decision.get('evidence_refs')
    if not isinstance(evidence_refs, list):
        issues.append(router._gate_decision_issue('evidence_refs', 'must be a list of evidence reference objects'))
        evidence_refs = []
    reason = str(decision.get('reason') or '').strip()
    if not reason:
        issues.append(router._gate_decision_issue('reason', 'GateDecision requires a concrete reason'))
    contract_self_check = decision.get('contract_self_check')
    if contract_self_check is not None:
        if not isinstance(contract_self_check, dict):
            issues.append(router._gate_decision_issue('contract_self_check', 'must be an object when provided'))
        else:
            if contract_self_check.get('all_required_fields_present') is not True:
                issues.append(router._gate_decision_issue('contract_self_check.all_required_fields_present', 'must be true'))
            if contract_self_check.get('exact_field_names_used') is not True:
                issues.append(router._gate_decision_issue('contract_self_check.exact_field_names_used', 'must be true'))
    gate_strength = decision.get('gate_strength')
    gate_decision = decision.get('decision')
    blocking = decision.get('blocking')
    next_action = decision.get('next_action')
    if gate_decision == 'pass':
        if blocking is not False:
            issues.append(router._gate_decision_issue('blocking', 'pass decisions must not be blocking'))
        if next_action != 'continue':
            issues.append(router._gate_decision_issue('next_action', 'pass decisions must route to continue'))
        if gate_strength == 'hard' and (not evidence_refs):
            issues.append(router._gate_decision_issue('evidence_refs', 'hard pass decisions require evidence references'))
    elif gate_decision == 'block':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'block decisions must be blocking'))
    elif gate_decision in {'waive', 'skip'}:
        if blocking is not False:
            issues.append(router._gate_decision_issue('blocking', 'waive and skip decisions must not be blocking'))
        if next_action != 'continue':
            issues.append(router._gate_decision_issue('next_action', 'waive and skip decisions must route to continue'))
    elif gate_decision == 'repair_local':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'repair_local decisions must be blocking until repaired'))
        if next_action not in {'local_repair', 'reviewer_recheck', 'collect_evidence'}:
            issues.append(router._gate_decision_issue('next_action', 'repair_local requires a local repair, recheck, or evidence collection action'))
    elif gate_decision == 'mutate_route':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'mutate_route decisions must be blocking until route mutation'))
        if next_action != 'route_mutation':
            issues.append(router._gate_decision_issue('next_action', 'mutate_route decisions must route to route_mutation'))
    if gate_strength == 'advisory' and blocking is True:
        issues.append(router._gate_decision_issue('blocking', 'advisory gates cannot block'))
    if gate_strength == 'skip_with_reason' and gate_decision not in {'skip', 'waive'}:
        issues.append(router._gate_decision_issue('decision', 'skip_with_reason gates require skip or waive decision'))
    for index, evidence in enumerate(evidence_refs):
        prefix = f'evidence_refs[{index}]'
        if not isinstance(evidence, dict):
            issues.append(router._gate_decision_issue(prefix, 'evidence reference must be an object'))
            continue
        kind = evidence.get('kind')
        if kind not in GATE_DECISION_ALLOWED_EVIDENCE_KINDS:
            issues.append(router._gate_decision_issue(f'{prefix}.kind', f'unsupported evidence kind: {kind}'))
            continue
        summary = str(evidence.get('summary') or '').strip()
        if not summary:
            issues.append(router._gate_decision_issue(f'{prefix}.summary', 'evidence reference requires summary'))
        if kind == 'none':
            continue
        raw_path = str(evidence.get('path') or '').strip()
        raw_hash = str(evidence.get('hash') or '').strip()
        if not raw_path:
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'non-none evidence requires path'))
            continue
        if not raw_hash:
            issues.append(router._gate_decision_issue(f'{prefix}.hash', 'non-none evidence requires hash'))
            continue
        evidence_path = resolve_project_path(project_root, raw_path)
        try:
            project_relative(project_root, evidence_path)
        except RouterError:
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'evidence path must stay inside the project root'))
            continue
        if not evidence_path.exists() or not evidence_path.is_file():
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'evidence path is missing'))
            continue
        actual_hash = packet_runtime.sha256_file(evidence_path)
        if raw_hash != actual_hash:
            issues.append(router._gate_decision_issue(f'{prefix}.hash', 'evidence hash does not match path content'))
    return issues

def _validate_gate_decision(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    issues = router._gate_decision_issues(project_root, decision)
    if issues:
        first = issues[0]
        raise RouterError(f"GateDecision mechanical validation failed: {first['field']}: {first['message']}")
    return decision

def _gate_decision_record_path(router: ModuleType, run_root: Path, gate_id: str) -> Path:
    _bind_router(router)
    return run_root / 'gate_decisions' / f'{router._gate_decision_safe_id(gate_id)}.json'

def _gate_decision_summary(router: ModuleType, project_root: Path, record_path: Path, decision: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'gate_id': str(decision['gate_id']), 'gate_kind': decision['gate_kind'], 'owner_role': decision['owner_role'], 'risk_type': decision['risk_type'], 'gate_strength': decision['gate_strength'], 'decision': decision['decision'], 'blocking': decision['blocking'], 'next_action': decision['next_action'], 'decision_path': project_relative(project_root, record_path)}

def _write_gate_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    decision = _load_file_backed_role_payload(project_root, payload)
    router._validate_gate_decision(project_root, decision)
    gate_id = str(decision['gate_id'])
    record_path = router._gate_decision_record_path(run_root, gate_id)
    record = {'schema_version': GATE_DECISION_RECORD_SCHEMA, 'run_id': run_state['run_id'], 'recorded_at': utc_now(), 'recorded_by_event': GATE_DECISION_EVENT, 'gate_decision': decision, **_role_output_envelope_record(decision)}
    write_json(record_path, record)
    summary = router._gate_decision_summary(project_root, record_path, decision)
    decisions = run_state.setdefault('gate_decisions', [])
    if not isinstance(decisions, list):
        decisions = []
        run_state['gate_decisions'] = decisions
    decisions[:] = [item for item in decisions if item.get('gate_id') != gate_id]
    decisions.append(summary)
    ledger_path = run_root / 'gate_decisions' / 'gate_decision_ledger.json'
    write_json(ledger_path, {'schema_version': GATE_DECISION_LEDGER_SCHEMA, 'run_id': run_state['run_id'], 'updated_at': utc_now(), 'gate_decision_count': len(decisions), 'gate_decisions': decisions})

__all__ = (
    '_validate_model_miss_officer_report_refs',
    '_write_model_miss_triage_decision',
    '_repair_transaction_normalized_plan_kind',
    '_event_already_recorded',
    '_controller_wait_entries_for_event',
    '_existing_event_producer_evidence',
    '_list_field',
    '_repair_transaction_execution_plan',
    '_write_control_blocker_repair_decision',
    '_gate_decision_issue',
    '_gate_decision_safe_id',
    '_gate_decision_issues',
    '_validate_gate_decision',
    '_gate_decision_record_path',
    '_gate_decision_summary',
    '_write_gate_decision',
)

_LOCAL_NAMES = set(globals())
