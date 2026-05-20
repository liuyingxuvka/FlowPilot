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
from flowpilot_control_plane_contracts import control_blocker_delivery_postcondition
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

def _control_blocker_wait_events(router: ModuleType, record: dict[str, Any], *, run_root: Path | None=None, run_state: dict[str, Any] | None=None) -> tuple[list[str], dict[str, Any] | None]:
    _bind_router(router)
    raw_events = record.get('allowed_resolution_events') or sorted(EXTERNAL_EVENTS)
    lane = str(record.get('handling_lane') or '')
    if lane == 'control_plane_reissue':
        _validate_control_transaction_requirements(run_root, transaction_type='control_plane_reissue', producer_role='router', required_event_usages=('wait',), required_commit_targets=('blocker_index', 'run_state', 'status_summary'), require_repair_transaction=False, outcome_policy='single_event')
    issue = router._external_event_validation_issue(raw_events)
    if issue is None:
        repair_origin = str(record.get('repair_origin') or ('control_plane_reissue' if lane == 'control_plane_reissue' else 'none'))
        return (router._validated_event_capability_names(raw_events, context='control blocker wait', run_root=run_root, run_state=run_state, usage='wait', repair_origin=repair_origin), None)
    if lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return ([PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT], {**issue, 'fallback': 'pm_must_resubmit_control_blocker_repair_decision', 'previous_allowed_resolution_events': raw_events})
    raise RouterError(str(issue.get('error') or 'control blocker wait contains invalid allowed external events'))

def _event_producer_roles(router: ModuleType, allowed_events: list[str]) -> set[str]:
    _bind_router(router)
    roles: set[str] = set()
    for event in allowed_events:
        meta = EXTERNAL_EVENTS.get(event) or {}
        roles.add(_event_wait_role(event, meta))
    return roles

def _role_set(router: ModuleType, to_role: str) -> set[str]:
    _bind_router(router)
    return {part.strip() for part in str(to_role or '').split(',') if part.strip()}

def _control_blocker_followup_target_role(router: ModuleType, allowed_events: list[str], fallback_role: str) -> str:
    _bind_router(router)
    roles = router._event_producer_roles(allowed_events)
    if not roles:
        return fallback_role
    fallback_roles = router._role_set(fallback_role)
    if roles.issubset(fallback_roles):
        return fallback_role
    return ','.join(sorted(roles))

def _validate_wait_event_producer_binding(router: ModuleType, allowed_events: list[str], *, to_role: str, context: str) -> None:
    _bind_router(router)
    producer_roles = router._event_producer_roles(allowed_events)
    target_roles = router._role_set(to_role)
    if producer_roles and (not producer_roles.issubset(target_roles)):
        raise RouterError(f'{context} waits for event producer role(s) {sorted(producer_roles)} but targets {sorted(target_roles)}')

def _repair_transaction_for_control_blocker(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    raw_path = record.get('repair_transaction_path')
    if not raw_path:
        return None
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return None
    transaction = read_json_if_exists(path)
    if transaction.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
        return None
    return transaction

def _make_operation_replay_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    replay_source = execution_plan.get('replay_source') if isinstance(execution_plan.get('replay_source'), dict) else {}
    source_action = replay_source.get('source_action') if isinstance(replay_source.get('source_action'), dict) else {}
    action_type = str(execution_plan.get('queued_action_type') or replay_source.get('action_type') or record.get('originating_action_type') or '')
    if action_type not in REPAIR_TRANSACTION_SAFE_REPLAY_ACTION_TYPES:
        raise RouterError(f"operation_replay repair transaction cannot queue action_type={action_type or 'missing'}")
    extra = {key: value for key, value in source_action.items() if key not in {'schema_version', 'action_id', 'action_type', 'actor', 'source', 'issued_by', 'label', 'summary', 'allowed_reads', 'allowed_writes', 'created_at'}}
    extra.update({'repair_transaction_id': transaction.get('transaction_id'), 'control_blocker_id': record.get('blocker_id'), 'replay_of_controller_action_id': replay_source.get('controller_action_id'), 'idempotency_key': f"repair-transaction:{transaction.get('transaction_id')}:operation-replay", 'repair_execution_plan': execution_plan})
    action = make_action(action_type=action_type, actor=str(source_action.get('actor') or 'controller'), label=f"controller_replays_{action_type}_for_{record.get('blocker_id')}", summary=f"Replay recorded operation {action_type} for repair transaction {transaction.get('transaction_id')}.", allowed_reads=list(source_action.get('allowed_reads') or [project_relative(project_root, router.run_state_path(run_root))]), allowed_writes=list(source_action.get('allowed_writes') or [project_relative(project_root, router.run_state_path(run_root))]), card_id=source_action.get('card_id'), mail_id=source_action.get('mail_id'), to_role=source_action.get('to_role'), extra=extra)
    return action

def _make_controller_repair_work_packet_action(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], transaction: dict[str, Any], execution_plan: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return make_action(action_type='controller_repair_work_packet', actor='controller', label=f"controller_executes_repair_work_packet_for_{record.get('blocker_id')}", summary=f"Execute bounded Controller repair work packet for repair transaction {transaction.get('transaction_id')} and report success evidence or a follow-up blocker.", allowed_reads=list(execution_plan.get('allowed_reads') or []), allowed_writes=list(execution_plan.get('allowed_writes') or [project_relative(project_root, router.run_state_path(run_root))]), to_role='controller', extra={'repair_transaction_id': transaction.get('transaction_id'), 'control_blocker_id': record.get('blocker_id'), 'repair_execution_plan': execution_plan, 'forbidden_actions': execution_plan.get('forbidden_actions') or [], 'success_evidence': execution_plan.get('success_evidence') or [], 'sealed_body_reads_allowed': False, 'controller_may_approve_gate': False, 'controller_may_mutate_route': False, 'controller_may_read_sealed_bodies': False, 'idempotency_key': f"repair-transaction:{transaction.get('transaction_id')}:controller-repair-work-packet"})

def _next_repair_transaction_executable_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], record: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    transaction = router._repair_transaction_for_control_blocker(project_root, run_root, record)
    if not isinstance(transaction, dict) or transaction.get('status') != 'committed':
        return None
    execution_plan = transaction.get('execution_plan')
    if not isinstance(execution_plan, dict):
        return None
    mode = str(execution_plan.get('mode') or transaction.get('plan_kind') or '')
    if mode == 'operation_replay':
        return router._make_operation_replay_action(project_root, run_root, run_state, record, transaction, execution_plan)
    if mode == 'controller_repair_work_packet':
        return router._make_controller_repair_work_packet_action(project_root, run_root, record, transaction, execution_plan)
    return None

def _next_control_blocker_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict):
        return None
    if router._resume_reentry_gate_pending(run_state) and active.get('originating_action_type') not in {'load_resume_state', 'rehydrate_role_agents'}:
        return None
    record = router._control_blocker_record(project_root, active)
    artifact_rel = str(record.get('blocker_artifact_path') or active.get('blocker_artifact_path') or '')
    if not artifact_rel:
        return None
    lane = str(record.get('handling_lane') or active.get('handling_lane') or 'pm_repair_decision_required')
    target_role = str(record.get('target_role') or active.get('target_role') or 'project_manager')
    allowed_resolution_events, event_contract_issue = router._control_blocker_wait_events(record, run_root=run_root, run_state=run_state)
    target_role = router._control_blocker_followup_target_role(allowed_resolution_events, target_role)
    router._validate_wait_event_producer_binding(allowed_resolution_events, to_role=target_role, context='control blocker wait')
    if record.get('delivery_status') != 'delivered':
        postcondition = control_blocker_delivery_postcondition(record.get('blocker_id'))
        return make_action(action_type='handle_control_blocker', actor='controller', label=f'controller_handles_{lane}_control_blocker', summary=f"Deliver router control blocker {record.get('blocker_id')} sealed repair packet envelope to {target_role}.", allowed_reads=[artifact_rel, project_relative(project_root, router.run_state_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'control_blocks' / 'control_blocker_delivery_ledger.json')], to_role=target_role, extra={'blocker_id': record.get('blocker_id'), 'blocker_artifact_path': artifact_rel, 'policy_row_id': record.get('policy_row_id'), 'blocker_family': record.get('blocker_family'), 'first_handler': record.get('first_handler'), 'direct_retry_budget': record.get('direct_retry_budget'), 'direct_retry_attempts_used': record.get('direct_retry_attempts_used'), 'direct_retry_budget_exhausted': record.get('direct_retry_budget_exhausted'), 'pm_recovery_options': record.get('pm_recovery_options') or [], 'return_policy': record.get('return_policy') or {}, 'hard_stop_conditions': record.get('hard_stop_conditions') or [], 'blocker_repair_policy_snapshot_path': record.get('blocker_repair_policy_snapshot_path'), 'sealed_repair_packet_path': record.get('sealed_repair_packet_path'), 'sealed_repair_packet_hash': record.get('sealed_repair_packet_hash'), 'handling_lane': lane, 'pm_decision_required': bool(record.get('pm_decision_required')), 'responsible_role_for_reissue': record.get('responsible_role_for_reissue'), 'repair_transaction_id': record.get('repair_transaction_id'), 'repair_outcome_table': record.get('repair_outcome_table'), 'controller_instruction': record.get('controller_instruction'), 'controller_allowed_actions': record.get('controller_allowed_actions') or [], 'controller_forbidden_actions': record.get('controller_forbidden_actions') or [], 'sealed_body_reads_allowed': False, 'controller_history_is_evidence': False, 'allowed_resolution_events': allowed_resolution_events, 'event_contract_issue': event_contract_issue, 'repair_details_visibility': 'sealed_to_target_role_not_controller', 'skill_observation_reminder': record.get('skill_observation_reminder'), 'postcondition': postcondition, 'target_work_completion_evidence_required_separately': True})
    executable_action = router._next_repair_transaction_executable_action(project_root, run_root, run_state, record)
    if executable_action is not None:
        return executable_action
    return make_action(action_type='await_role_decision', actor='controller', label='controller_waits_for_control_blocker_resolution', summary="A router control blocker has been delivered. Controller must wait for the target role's corrected event or PM recovery decision.", allowed_reads=[artifact_rel, project_relative(project_root, router.run_state_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root))], to_role=target_role, extra={'allowed_external_events': allowed_resolution_events, 'blocker_artifact_path': artifact_rel, 'policy_row_id': record.get('policy_row_id'), 'blocker_family': record.get('blocker_family'), 'first_handler': record.get('first_handler'), 'direct_retry_budget': record.get('direct_retry_budget'), 'direct_retry_attempts_used': record.get('direct_retry_attempts_used'), 'direct_retry_budget_exhausted': record.get('direct_retry_budget_exhausted'), 'pm_recovery_options': record.get('pm_recovery_options') or [], 'return_policy': record.get('return_policy') or {}, 'hard_stop_conditions': record.get('hard_stop_conditions') or [], 'target_role': target_role, 'handling_lane': lane, 'repair_transaction_id': record.get('repair_transaction_id'), 'repair_outcome_table': record.get('repair_outcome_table'), 'event_contract_issue': event_contract_issue})

def _mark_control_blocker_delivered(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], pending: dict[str, Any]) -> None:
    _bind_router(router)
    artifact_rel = str(pending.get('blocker_artifact_path') or '')
    if not artifact_rel:
        raise RouterError('control blocker action is missing blocker_artifact_path')
    artifact_path = resolve_project_path(project_root, artifact_rel)
    record = read_json(artifact_path)
    delivered_at = utc_now()
    target_role = str(pending.get('to_role') or record.get('target_role') or 'project_manager')
    record['delivery_status'] = 'delivered'
    record['delivered_by'] = 'controller'
    record['delivered_to_role'] = target_role
    record['delivered_at'] = delivered_at
    write_json(artifact_path, record)
    active = run_state.get('active_control_blocker')
    if isinstance(active, dict) and active.get('blocker_id') == record.get('blocker_id'):
        active['delivery_status'] = 'delivered'
        active['delivered_to_role'] = target_role
        active['delivered_at'] = delivered_at
    ledger_path = run_root / 'control_blocks' / 'control_blocker_delivery_ledger.json'
    ledger = read_json_if_exists(ledger_path) or {'schema_version': 'flowpilot.control_blocker_delivery_ledger.v1', 'deliveries': []}
    ledger.setdefault('deliveries', []).append({'blocker_id': record.get('blocker_id'), 'blocker_artifact_path': artifact_rel, 'handling_lane': record.get('handling_lane'), 'sealed_repair_packet_path': record.get('sealed_repair_packet_path'), 'sealed_repair_packet_hash': record.get('sealed_repair_packet_hash'), 'delivered_by': 'controller', 'delivered_to_role': target_role, 'delivered_at': delivered_at})
    ledger['updated_at'] = delivered_at
    write_json(ledger_path, ledger)
    postcondition = str(pending.get('postcondition') or control_blocker_delivery_postcondition(record.get('blocker_id')) or '').strip()
    if postcondition:
        run_state.setdefault('flags', {})[postcondition] = True
    router._sync_control_plane_indexes(project_root, run_root, run_state)

__all__ = (
    '_control_blocker_wait_events',
    '_event_producer_roles',
    '_role_set',
    '_control_blocker_followup_target_role',
    '_validate_wait_event_producer_binding',
    '_repair_transaction_for_control_blocker',
    '_make_operation_replay_action',
    '_make_controller_repair_work_packet_action',
    '_next_repair_transaction_executable_action',
    '_next_control_blocker_action',
    '_mark_control_blocker_delivered',
)

_LOCAL_NAMES = set(globals())
