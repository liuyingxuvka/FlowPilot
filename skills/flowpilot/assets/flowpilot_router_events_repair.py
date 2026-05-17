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

def _control_blocker_error_code(router: ModuleType, message: str) -> str:
    _bind_router(router)
    cleaned: list[str] = []
    for char in message.lower():
        if char.isalnum():
            cleaned.append(char)
        elif cleaned and cleaned[-1] != '_':
            cleaned.append('_')
    code = ''.join(cleaned).strip('_')
    return code[:96] or 'router_hard_rejection'

def _blocker_repair_policy_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'control_blocks' / 'blocker_repair_policy_snapshot.json'

def _blocker_repair_policy_rows(router: ModuleType) -> list[dict[str, Any]]:
    _bind_router(router)
    return [_json_safe(BLOCKER_REPAIR_POLICY_ROWS[key]) for key in sorted(BLOCKER_REPAIR_POLICY_ROWS)]

def _write_blocker_repair_policy_snapshot(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    path = router._blocker_repair_policy_snapshot_path(run_root)
    payload = {'schema_version': BLOCKER_REPAIR_POLICY_SCHEMA, 'run_id': run_state.get('run_id'), 'created_at': utc_now(), 'policy_scope': 'new_control_blockers', 'rows': router._blocker_repair_policy_rows()}
    write_json(path, payload)
    rel = project_relative(project_root, path)
    run_state['blocker_repair_policy_snapshot'] = rel
    return rel

def _control_blocker_policy_row(router: ModuleType, error_message: str, category: str) -> dict[str, Any]:
    _bind_router(router)
    lowered = error_message.lower()
    if 'self-interrogation' in lowered or 'self_interrogation' in lowered:
        return dict(BLOCKER_REPAIR_POLICY_ROWS['self_interrogation_repair'])
    if category == 'control_plane_reissue':
        return dict(BLOCKER_REPAIR_POLICY_ROWS['mechanical_control_plane_reissue'])
    if category == 'fatal_protocol_violation':
        return dict(BLOCKER_REPAIR_POLICY_ROWS['fatal_protocol_violation'])
    return dict(BLOCKER_REPAIR_POLICY_ROWS['pm_semantic_repair'])

def _control_blocker_attempt_key(router: ModuleType, *, policy_row_id: str, event: str | None, action_type: str | None, responsible_role: str) -> str:
    _bind_router(router)
    return '|'.join((policy_row_id, event or '', action_type or '', responsible_role or ''))

def _control_blocker_direct_attempts_used(router: ModuleType, run_state: dict[str, Any], attempt_key: str) -> int:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('attempt_key') != attempt_key:
        return 0
    if active.get('target_role') == 'project_manager':
        return int(active.get('direct_retry_attempts_used') or 0)
    return int(active.get('direct_retry_attempts_used') or 0) + 1

def _policy_first_handler_target(router: ModuleType, policy_row: dict[str, Any], responsible_role: str) -> str:
    _bind_router(router)
    first_handler = str(policy_row.get('first_handler') or 'project_manager')
    if first_handler == 'responsible_role':
        return responsible_role
    return first_handler

def _pm_recovery_options_from_policy(router: ModuleType, policy_row: dict[str, Any]) -> list[str]:
    _bind_router(router)
    raw = policy_row.get('pm_recovery_options')
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if str(item)]
    return list(PM_BLOCKER_RECOVERY_OPTIONS)

def _default_pm_recovery_option(router: ModuleType, active: dict[str, Any], requested_plan_kind: str) -> str:
    _bind_router(router)
    policy_row_id = str(active.get('policy_row_id') or '')
    if policy_row_id == 'fatal_protocol_violation':
        return 'evidence_quarantine'
    if policy_row_id == 'self_interrogation_repair':
        return 'record_disposition'
    if requested_plan_kind == 'route_mutation':
        return 'route_mutation'
    if requested_plan_kind == 'packet_reissue':
        return 'same_gate_repair'
    return 'same_gate_repair'

def _project_relative_if_possible(router: ModuleType, project_root: Path, path: Path) -> str:
    _bind_router(router)
    try:
        return project_relative(project_root, path)
    except RouterError:
        return str(path)

def _payload_source_paths(router: ModuleType, project_root: Path, run_root: Path, payload: dict[str, Any] | None) -> dict[str, str]:
    _bind_router(router)
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root))}
    packet_ledger = run_root / 'packet_ledger.json'
    if packet_ledger.exists():
        source_paths['packet_ledger'] = project_relative(project_root, packet_ledger)
    if not isinstance(payload, dict):
        return source_paths
    for key in ('body_path', 'report_path', 'decision_path', 'result_body_path', 'packet_envelope_path', 'result_envelope_path', 'packet_index_path', 'path'):
        raw = payload.get(key)
        if not raw:
            continue
        candidate = resolve_project_path(project_root, str(raw))
        source_paths[key] = router._project_relative_if_possible(project_root, candidate)
    return source_paths

def _control_payload_public_view(router: ModuleType, payload: dict[str, Any] | None) -> dict[str, Any]:
    _bind_router(router)
    if not isinstance(payload, dict):
        return {}
    forbidden_body_keys = {'blockers', 'checks', 'commands', 'decision', 'decision_body', 'evidence', 'findings', 'passed', 'direct_material_sources_checked', 'packet_matches_checked_sources', 'pm_ready', 'recommendations', 'repair_instructions', 'report_body', 'result_body'}
    public: dict[str, Any] = {}
    for key, value in payload.items():
        if key in forbidden_body_keys:
            public[key] = '[redacted: role body field was controller-visible]'
            continue
        if key.endswith('_path') or key.endswith('_hash') or key in {'packet_id', 'route_id', 'node_id', 'role', 'from_role', 'to_role', 'expected_role', 'completed_by_role', 'reviewed_by_role', 'controller_visibility', 'chat_response_body_allowed'}:
            public[key] = _json_safe(value)
    return public

def _infer_responsible_role(router: ModuleType, event: str | None, payload: dict[str, Any] | None, message: str) -> str:
    _bind_router(router)
    if isinstance(payload, dict):
        for key in ('reviewed_by_role', 'completed_by_role', 'from_role', 'to_role', 'role', 'expected_role'):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value
    if event:
        if event.startswith('reviewer_') or 'reviewer' in event:
            return 'human_like_reviewer'
        if event.startswith('worker_') or 'worker_' in event:
            if 'worker_b' in message or 'worker-b' in message:
                return 'worker_b'
            return 'worker_a'
        if event.startswith('product_officer_'):
            return 'product_flowguard_officer'
        if event.startswith('process_officer_'):
            return 'process_flowguard_officer'
        if event.startswith('pm_'):
            return 'project_manager'
    lowered = message.lower()
    if 'product_flowguard_officer' in lowered:
        return 'product_flowguard_officer'
    if 'process_flowguard_officer' in lowered:
        return 'process_flowguard_officer'
    if 'human_like_reviewer' in lowered or 'reviewer' in lowered:
        return 'human_like_reviewer'
    if 'project_manager' in lowered or message.startswith('PM '):
        return 'project_manager'
    return 'project_manager'

def _classify_control_blocker(router: ModuleType, message: str, *, event: str | None=None, action_type: str | None=None, source: str | None=None) -> str:
    _bind_router(router)
    del action_type
    if source == CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE:
        return 'control_plane_reissue'
    lowered = message.lower()
    fatal_markers = ('private role-to-role', 'controller relay violation', 'body was read by controller', 'body was executed by controller', 'body_was_read_by_controller', 'body_was_executed_by_controller', 'controller read', 'controller executes', 'contaminated envelope', 'leaked role body fields to controller', 'controller relay envelope hash mismatch')
    if any((marker in lowered for marker in fatal_markers)):
        return 'fatal_protocol_violation'
    if 'role output runtime envelope body hash is stale' in lowered:
        return 'control_plane_reissue'
    semantic_pm_markers = ('controller-origin', 'controller_origin_artifact', 'self-interrogation', 'self_interrogation', 'wrong role', 'wrong-role', 'result_completed_by_wrong_role', 'completed_agent_id_not_assigned_to_role', 'packet body hash mismatch', 'result body hash mismatch', 'stale', 'unresolved', 'final ledger', 'route mutation', 'parent segment', 'ambiguous', 'repair decision')
    if any((marker in lowered for marker in semantic_pm_markers)):
        return 'pm_repair_decision_required'
    mechanical_reissue_markers = ('result_body_not_opened', 'packet_body_not_opened', 'packet body was not opened by target role after controller relay', 'body was not opened by target role after controller relay', 'ledger open receipt is invalid', 'packet_ledger_missing_packet_body_open_receipt', 'packet_ledger_missing_result_absorption', 'packet_ledger_missing_result_body_open_receipt', 'result body was not opened', 'completed_agent_id_is_role_key_not_agent_id', 'role output runtime envelope claims validation but has no receipt', 'role output runtime receipt requires both path and hash', 'role output runtime receipt path is missing', 'role output runtime receipt hash mismatch', 'role output runtime envelope missing output path/hash pair', 'role output runtime envelope body hash is stale', 'missing_quality_pack_check', 'quality_pack_checks', 'self-interrogation', 'self_interrogation')
    if any((marker in lowered for marker in mechanical_reissue_markers)):
        return 'control_plane_reissue'
    pm_markers = ('reviewer pass rejected by packet audit', 'current-node result failed pre-relay packet runtime audit', 'packet group reviewer audit failed')
    if any((marker in lowered for marker in pm_markers)):
        return 'pm_repair_decision_required'
    if event in {'current_node_reviewer_passes_result', 'reviewer_reports_material_sufficient', 'reviewer_reports_material_insufficient', 'reviewer_passes_research_direct_source_check', 'reviewer_passes_route_check', 'reviewer_final_backward_replay_passed'}:
        return 'control_plane_reissue'
    reissue_markers = ('requires a file-backed body path', 'requires a body/report/decision hash', 'role body path is missing', 'role body hash mismatch', 'must be reviewed_by_role', 'must explicitly pass', 'gate report must', 'requires direct_material_sources_checked', 'requires packet_matches_checked_sources', 'requires pm_ready', 'must route to', 'requires packet_id', 'requires packet envelope', 'missing source paths')
    if any((marker in lowered for marker in reissue_markers)):
        return 'control_plane_reissue'
    return 'pm_repair_decision_required'

def _should_materialize_control_blocker(router: ModuleType, message: str, *, event: str | None=None, action_type: str | None=None, payload: dict[str, Any] | None=None) -> bool:
    _bind_router(router)
    lowered = message.lower()
    if lowered.startswith('event ') and ' requires ' in lowered:
        return False
    if "run 'next' before applying" in lowered or 'pending action is' in lowered:
        return False
    if 'requires a file-backed body path' in lowered and (not payload):
        return False
    material_markers = ('requires a file-backed body path', 'requires a body/report/decision hash', 'role body path is missing', 'role body hash mismatch', 'leaked role body fields to controller', 'must be reviewed_by_role', 'must explicitly pass', 'gate report must', 'requires direct_material_sources_checked', 'requires packet_matches_checked_sources', 'requires pm_ready', 'packet group reviewer audit failed', 'reviewer pass rejected by packet audit', 'current-node result failed pre-relay packet runtime audit', 'controller-origin', 'wrong role', 'wrong-role', 'result_completed_by_wrong_role', 'completed_agent_id', 'packet_ledger_missing_result_absorption', 'packet_ledger_missing_packet_body_open_receipt', 'packet_ledger_missing_result_body_open_receipt', 'ledger open receipt is invalid', 'packet ledger missing packet body open receipt', 'packet ledger missing result absorption', 'packet ledger missing result body open receipt', 'missing controller relay signature', 'envelope was not delivered via controller', 'controller did not sign', 'private role-to-role', 'controller relay violation', 'contaminated envelope', 'body was not opened', 'unopened', 'packet body hash mismatch', 'result body hash mismatch', 'controller relay envelope hash mismatch', 'role output runtime receipt', 'body_ref', 'runtime_receipt_ref', 'quality_pack_checks', 'self-interrogation', 'self_interrogation')
    if any((marker in lowered for marker in material_markers)):
        return True
    if action_type in {'relay_material_scan_packets', 'relay_material_scan_results_to_reviewer', 'relay_material_scan_results_to_pm', 'relay_research_packet', 'relay_research_result_to_reviewer', 'relay_research_result_to_pm', 'relay_current_node_packet', 'relay_current_node_result_to_reviewer', 'relay_current_node_result_to_pm'}:
        return True
    if isinstance(payload, dict) and any((payload.get(key) for key in ('body_path', 'body_hash', 'report_path', 'report_hash', 'decision_path', 'decision_hash', 'result_body_path', 'result_body_hash', 'body_ref', 'runtime_receipt_ref'))):
        return event is not None and (event.startswith('reviewer_') or event.startswith('process_officer_') or event.startswith('product_officer_') or (event in {'current_node_reviewer_passes_result', 'pm_resume_recovery_decision_returned', PM_MODEL_MISS_TRIAGE_DECISION_EVENT, 'pm_records_parent_segment_decision'}))
    return False

def _skill_observation_reminder(router: ModuleType, message: str, *, event: str | None=None, action_type: str | None=None, category: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    lowered = message.lower()
    suggested_kind = 'controller_compensation'
    if 'route' in lowered or 'frontier' in lowered:
        suggested_kind = 'router_state_gap'
    elif 'ledger' in lowered:
        suggested_kind = 'ledger_gap'
    elif 'display_plan' in lowered or 'visible plan' in lowered:
        suggested_kind = 'display_projection_gap'
    elif 'heartbeat' in lowered or 'pause' in lowered or 'resume' in lowered:
        suggested_kind = 'heartbeat_gap'
    elif 'schema' in lowered or 'field' in lowered or 'hash' in lowered or ('path' in lowered):
        suggested_kind = 'schema_gap'
    return {'schema_version': 'flowpilot.skill_observation_reminder.v1', 'should_consider_recording': True, 'reason': 'router_control_plane_exception', 'originating_event': event, 'originating_action_type': action_type, 'handling_lane': category, 'suggested_kind': suggested_kind, 'summary': message, 'write_path': '.flowpilot/runs/<run_id>/flowpilot_skill_improvement_report.json', 'record_only_if': 'This reflects a FlowPilot skill/protocol/router weakness, not ordinary project work.', 'do_not_include': ['sealed packet bodies', 'sealed result bodies', 'private role reasoning', 'secrets']}

def _validated_external_event_names(router: ModuleType, events: Any, *, context: str, allow_pm_repair_event: bool=True) -> list[str]:
    _bind_router(router)
    if not isinstance(events, list) or not events:
        raise RouterError(f'{context} requires a non-empty allowed_external_events list')
    normalized: list[str] = []
    invalid: list[str] = []
    for item in events:
        name = router._control_resolution_event_name(item)
        if not name:
            invalid.append(str(item))
            continue
        if name == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT and (not allow_pm_repair_event):
            invalid.append(name)
            continue
        if name not in EXTERNAL_EVENTS:
            invalid.append(name)
            continue
        if name not in normalized:
            normalized.append(name)
    if invalid:
        raise RouterError(f"{context} contains unregistered external event(s): {', '.join(invalid)}")
    return normalized

def _active_node_kind_for_event_capability(router: ModuleType, run_root: Path | None) -> str | None:
    _bind_router(router)
    if run_root is None:
        return None
    try:
        frontier = router._active_frontier(run_root)
        node = router._active_node_definition(run_root, frontier)
    except (OSError, KeyError, RouterError, json.JSONDecodeError, ValueError, TypeError):
        return None
    kind = router._node_kind(node)
    if router._node_child_ids(node) and kind not in {'parent', 'module'}:
        return 'parent'
    return kind or None

def _event_capability_issue(router: ModuleType, event: str, *, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, currently_receivable: bool=True) -> str | None:
    _bind_router(router)
    if event not in EXTERNAL_EVENTS:
        return 'event is not registered'
    if not currently_receivable:
        return 'event is not currently receivable'
    if usage == 'rerun_target' and event in {PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT, *CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS, PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
        return 'event cannot be used as a repair rerun target'
    active_node_kind = router._active_node_kind_for_event_capability(run_root)
    if active_node_kind in {'parent', 'module'} and event in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'event is incompatible with parent/module active node'
    if active_node_kind in {'leaf', 'repair'} and event in PARENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'event requires a parent/module active node'
    active_node_has_children = _active_node_children_status(run_root)
    meta = EXTERNAL_EVENTS.get(event) or {}
    if not _event_applicable_for_active_node(meta, active_node_has_children):
        return 'event is incompatible with active node child state'
    origin = repair_origin or 'none'
    if origin == 'parent_backward_replay' and event not in PARENT_REPAIR_SAFE_EVENTS:
        return 'parent backward replay repair cannot target this event'
    if usage == 'repair_outcome':
        if outcome_kind == 'success' and event in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS | {PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
            return 'repair success outcome cannot use a non-success event'
        if outcome_kind == 'blocker' and event not in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS | {'reviewer_blocks_parent_backward_replay', 'router_direct_material_scan_dispatch_recheck_blocked'}:
            return 'repair blocker outcome must use a blocker-capable event'
        if outcome_kind == 'protocol_blocker' and event not in {PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, PM_PARENT_PROTOCOL_BLOCKER_EVENT, 'router_protocol_blocker_material_scan_dispatch_recheck'}:
            return 'repair protocol-blocker outcome must use a protocol-blocker-capable event'
    if usage == 'wait' and origin == 'control_plane_reissue':
        return None
    required_flag = meta.get('requires_flag')
    if usage in {'wait', 'rerun_target'} and run_state is not None and required_flag and (not run_state.get('flags', {}).get(required_flag)):
        return f'event requires unsatisfied flag {required_flag}'
    return None

def _run_state_with_assumed_flag(router: ModuleType, run_state: dict[str, Any], flag: str) -> dict[str, Any]:
    _bind_router(router)
    assumed = dict(run_state)
    flags = dict(run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {})
    flags[flag] = True
    assumed['flags'] = flags
    return assumed

def _validated_event_capability_names(router: ModuleType, events: Any, *, context: str, run_root: Path | None=None, run_state: dict[str, Any] | None=None, usage: str='wait', repair_origin: str | None=None, outcome_kind: str | None=None, allow_pm_repair_event: bool=True, currently_receivable: bool=True) -> list[str]:
    _bind_router(router)
    normalized = router._validated_external_event_names(events, context=context, allow_pm_repair_event=allow_pm_repair_event)
    issues = [f'{event}: {issue}' for event in normalized if (issue := router._event_capability_issue(event, run_root=run_root, run_state=run_state, usage=usage, repair_origin=repair_origin, outcome_kind=outcome_kind, currently_receivable=currently_receivable))]
    if issues:
        raise RouterError(f"{context} contains non-executable external event(s): {', '.join(issues)}")
    return normalized

def _external_event_validation_issue(router: ModuleType, events: Any) -> dict[str, Any] | None:
    _bind_router(router)
    try:
        router._validated_external_event_names(events, context='event validation')
    except RouterError as exc:
        return {'reason': 'invalid_allowed_external_events', 'error': str(exc)}
    return None

def _control_blocker_allowed_resolution_events(router: ModuleType, category: str, event: str | None) -> list[str]:
    _bind_router(router)
    if category == 'control_plane_reissue' and event:
        return router._validated_external_event_names([event], context='control-plane reissue resolution')
    if category in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES:
        return [PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT]
    return sorted(EXTERNAL_EVENTS)

def _control_blocker_policy(router: ModuleType, category: str, *, responsible_role: str, event: str | None, policy_row: dict[str, Any], target_role: str) -> dict[str, Any]:
    _bind_router(router)
    if category == 'control_plane_reissue' and target_role != 'project_manager':
        instruction = f'Deliver the sealed repair packet envelope to `{target_role}` and request a same-role reissue of the rejected control-plane output. Controller may route the packet path, hash, policy row, and retry count only.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to the responsible role', 'quote policy_row_id, direct_retry_budget, and direct_retry_attempts_used', 'tell the responsible role to reissue the same control-plane output']
        forbidden = ['open sealed packet/result/report bodies', 'infer project status from chat history', 'ask a worker to change project substance', 'convert the router rejection into PM-owned evidence']
        pm_required = False
    elif category == 'fatal_protocol_violation':
        instruction = 'Stop normal route work and deliver this control blocker to `project_manager` for escalation. Controller may route the sealed repair packet envelope only and must not repair the route from chat.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager', 'wait for an explicit PM or user recovery decision']
        forbidden = ['open sealed packet/result/report bodies', 'contact the worker directly', 'advance, close, or mutate the route', 'treat controller-visible leaked content as evidence']
        pm_required = True
    else:
        instruction = 'Deliver the sealed repair packet envelope to `project_manager` for a repair decision. Controller must not decide whether the work is substantively acceptable and must not inspect or restate the repair details. PM must choose a policy-listed recovery option and name the gate or terminal stop that follows.'
        allowed = ['read this control blocker artifact', 'deliver sealed_repair_packet_path and sealed_repair_packet_hash to project_manager', 'quote blocker_id, error_code, handling_lane, target_role, policy_row_id, return_policy, and pm_recovery_options']
        forbidden = ['open sealed packet/result/report bodies', 'contact the worker directly about project repair', 'summarize reviewer or worker body content', 'advance route state from the rejected event']
        pm_required = True
    return {'target_role': target_role, 'pm_decision_required': pm_required, 'controller_instruction': instruction, 'controller_allowed_actions': allowed, 'controller_forbidden_actions': forbidden, 'allowed_resolution_events': router._control_blocker_allowed_resolution_events(category, event), 'policy_row_id': policy_row.get('policy_row_id'), 'blocker_family': policy_row.get('blocker_family')}

def _write_control_blocker_repair_packet(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, category: str, target_role: str, responsible_role: str, error_message: str, event: str | None, action_type: str | None, payload: dict[str, Any] | None, policy_row: dict[str, Any], policy_snapshot_path: str, direct_retry_attempts_used: int, direct_retry_budget_exhausted: bool) -> dict[str, str]:
    _bind_router(router)
    packet_path = run_root / 'control_blocks' / f'{blocker_id}.sealed_repair_packet.json'
    packet = {'schema_version': CONTROL_BLOCKER_REPAIR_PACKET_SCHEMA, 'blocker_id': blocker_id, 'run_id': run_state.get('run_id'), 'body_visibility': 'sealed_router_repair_details_for_target_role', 'target_role': target_role, 'responsible_role_for_reissue': responsible_role if category == 'control_plane_reissue' else None, 'handling_lane': category, 'policy_row_id': policy_row.get('policy_row_id'), 'blocker_family': policy_row.get('blocker_family'), 'first_handler': policy_row.get('first_handler'), 'direct_retry_budget': policy_row.get('direct_retry_budget'), 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'originating_event': event, 'originating_action_type': action_type, 'error_code': router._control_blocker_error_code(error_message), 'error_message': error_message, 'source_paths': router._payload_source_paths(project_root, run_root, payload), 'payload_envelope_public_view': router._control_payload_public_view(payload), 'controller_may_read_body': False, 'controller_may_repair_from_this_packet': False, 'target_role_repair_instruction': 'Inspect this sealed packet, fix the rejected control-plane output, and reissue the router event named in allowed_resolution_events. Do not ask Controller to infer or patch the body.', 'allowed_resolution_events': router._control_blocker_allowed_resolution_events(category, event), 'created_at': utc_now()}
    write_json(packet_path, packet)
    return {'sealed_repair_packet_path': project_relative(project_root, packet_path), 'sealed_repair_packet_hash': hashlib.sha256(packet_path.read_bytes()).hexdigest()}

def _supersede_prior_control_blockers(router: ModuleType, run_root: Path, *, blocker_id: str, category: str, event: str | None, action_type: str | None, attempt_key: str | None=None) -> None:
    _bind_router(router)
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return
    superseded_at = utc_now()
    for path in sorted(control_root.glob('*.json')):
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        if record.get('resolution_status') or record.get('blocker_id') == blocker_id:
            continue
        if attempt_key:
            if record.get('attempt_key') != attempt_key:
                continue
        else:
            if record.get('handling_lane') != category:
                continue
            if record.get('originating_event') != event or record.get('originating_action_type') != action_type:
                continue
        record['resolution_status'] = 'superseded_by_newer_control_blocker'
        record['superseded_by_blocker_id'] = blocker_id
        record['resolved_at'] = superseded_at
        record['resolution_note'] = 'A newer router rejection for the same control-plane event replaced this pending repair packet.'
        write_json(path, record)

def _nonnegative_int_or_none(router: ModuleType, value: Any) -> int | None:
    _bind_router(router)
    if value is None or value == '':
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None

def _write_control_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source: str, error_message: str, event: str | None=None, action_type: str | None=None, payload: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    base_category = router._classify_control_blocker(error_message, event=event, action_type=action_type, source=source)
    if base_category not in CONTROL_BLOCKER_LANES:
        base_category = 'pm_repair_decision_required'
    payload_view = payload if isinstance(payload, dict) else {}
    apply_result = payload_view.get('apply_result') if isinstance(payload_view.get('apply_result'), dict) else {}
    origin_controller_action_id = str(payload_view.get('controller_action_id') or payload_view.get('current_controller_action_id') or apply_result.get('controller_action_id') or '').strip() or None
    origin_router_scheduler_row_id = str(payload_view.get('router_scheduler_row_id') or apply_result.get('router_scheduler_row_id') or '').strip() or None
    origin_postcondition = str(payload_view.get('postcondition') or apply_result.get('postcondition') or '').strip() or None
    responsible_role = router._infer_responsible_role(event, payload, error_message)
    if source == CONTROLLER_POSTCONDITION_MISSING_BLOCKER_SOURCE and base_category == 'control_plane_reissue' and (responsible_role == 'project_manager'):
        responsible_role = 'controller'
    policy_row = router._control_blocker_policy_row(error_message, base_category)
    policy_row_id = str(policy_row.get('policy_row_id') or 'pm_semantic_repair')
    attempt_key = router._control_blocker_attempt_key(policy_row_id=policy_row_id, event=event, action_type=action_type, responsible_role=responsible_role)
    retry_attempt_override = router._nonnegative_int_or_none(payload_view.get('direct_retry_attempts_used'))
    if retry_attempt_override is None:
        retry_attempt_override = router._nonnegative_int_or_none(apply_result.get('direct_retry_attempts_used'))
    if retry_attempt_override is None:
        direct_retry_attempts_used = router._control_blocker_direct_attempts_used(run_state, attempt_key)
    else:
        direct_retry_attempts_used = retry_attempt_override
    retry_budget_override = router._nonnegative_int_or_none(payload_view.get('direct_retry_budget'))
    if retry_budget_override is None:
        retry_budget_override = router._nonnegative_int_or_none(apply_result.get('direct_retry_budget'))
    direct_retry_budget = retry_budget_override if retry_budget_override is not None else int(policy_row.get('direct_retry_budget') or 0)
    first_handler = str(policy_row.get('first_handler') or 'project_manager')
    direct_retry_budget_exhausted = direct_retry_attempts_used >= direct_retry_budget
    if base_category == 'fatal_protocol_violation':
        category = base_category
        target_role = 'project_manager'
    elif first_handler == 'responsible_role' and direct_retry_budget_exhausted:
        category = 'pm_repair_decision_required'
        target_role = str(policy_row.get('escalate_to') or 'project_manager')
    else:
        category = base_category
        target_role = router._policy_first_handler_target(policy_row, responsible_role)
    if target_role == 'project_manager' and category == 'control_plane_reissue':
        category = 'pm_repair_decision_required'
    policy = router._control_blocker_policy(category, responsible_role=responsible_role, event=event, policy_row=policy_row, target_role=target_role)
    policy_snapshot_path = router._write_blocker_repair_policy_snapshot(project_root, run_root, run_state)
    index = len(run_state.setdefault('control_blockers', [])) + 1
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    blocker_id = f'control-blocker-{index:04d}-{stamp}'
    artifact_path = run_root / 'control_blocks' / f'{blocker_id}.json'
    artifact_rel = project_relative(project_root, artifact_path)
    repair_packet = router._write_control_blocker_repair_packet(project_root, run_root, run_state, blocker_id=blocker_id, category=category, target_role=policy['target_role'], responsible_role=responsible_role, error_message=error_message, event=event, action_type=action_type, payload=payload, policy_row=policy_row, policy_snapshot_path=policy_snapshot_path, direct_retry_attempts_used=direct_retry_attempts_used, direct_retry_budget_exhausted=direct_retry_budget_exhausted)
    record = {'schema_version': CONTROL_BLOCKER_SCHEMA, 'blocker_id': blocker_id, 'run_id': run_state.get('run_id'), 'created_at': utc_now(), 'source': source, 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'originating_handling_lane': base_category, 'handling_lane': category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'controller_boundary': policy_row.get('controller_boundary'), 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'error_code': router._control_blocker_error_code(error_message), 'controller_visible_summary': 'Router rejected a control-plane payload. Deliver the sealed repair packet to the target role.', 'blocker_artifact_path': artifact_rel, 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'responsible_role_for_reissue': responsible_role if base_category == 'control_plane_reissue' else None, 'target_role': policy['target_role'], 'pm_decision_required': policy['pm_decision_required'], 'controller_instruction': policy['controller_instruction'], 'controller_allowed_actions': policy['controller_allowed_actions'], 'controller_forbidden_actions': policy['controller_forbidden_actions'], 'allowed_resolution_events': policy['allowed_resolution_events'], 'sealed_body_read_by_controller_allowed': False, 'controller_history_is_evidence': False, 'delivery_status': 'pending', 'skill_observation_reminder': router._skill_observation_reminder('Control-plane payload was rejected and a sealed repair packet was issued for the target role.', event=event, action_type=action_type, category=category)}
    write_json(artifact_path, record)
    router._supersede_prior_control_blockers(run_root, blocker_id=blocker_id, category=category, event=event, action_type=action_type, attempt_key=attempt_key)
    active = {'blocker_id': blocker_id, 'handling_lane': category, 'originating_handling_lane': base_category, 'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'first_handler': first_handler, 'attempt_key': attempt_key, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'escalate_to': policy_row.get('escalate_to'), 'pm_recovery_options': router._pm_recovery_options_from_policy(policy_row), 'return_policy': _json_safe(policy_row.get('return_policy') or {}), 'hard_stop_conditions': [str(item) for item in policy_row.get('hard_stop_conditions') or []], 'blocker_repair_policy_snapshot_path': policy_snapshot_path, 'blocker_artifact_path': artifact_rel, 'target_role': policy['target_role'], 'responsible_role_for_reissue': record['responsible_role_for_reissue'], 'pm_decision_required': policy['pm_decision_required'], 'delivery_status': 'pending', 'sealed_repair_packet_path': repair_packet['sealed_repair_packet_path'], 'sealed_repair_packet_hash': repair_packet['sealed_repair_packet_hash'], 'originating_event': event, 'originating_action_type': action_type, 'originating_controller_action_id': origin_controller_action_id, 'originating_router_scheduler_row_id': origin_router_scheduler_row_id, 'originating_postcondition': origin_postcondition, 'created_at': record['created_at']}
    run_state['active_control_blocker'] = active
    run_state.setdefault('blocker_repair_attempts', {})[attempt_key] = {'policy_row_id': policy_row_id, 'blocker_family': policy_row.get('blocker_family'), 'originating_event': event, 'originating_action_type': action_type, 'responsible_role': responsible_role, 'direct_retry_budget': direct_retry_budget, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'latest_blocker_id': blocker_id, 'latest_target_role': policy['target_role'], 'updated_at': record['created_at']}
    run_state['latest_control_blocker_path'] = artifact_rel
    run_state['control_blockers'].append(active)
    run_state['pending_action'] = None
    append_history(run_state, 'router_recorded_control_blocker', {'blocker_id': blocker_id, 'handling_lane': category, 'policy_row_id': policy_row_id, 'direct_retry_attempts_used': direct_retry_attempts_used, 'direct_retry_budget_exhausted': direct_retry_budget_exhausted, 'target_role': policy['target_role'], 'originating_event': event, 'originating_action_type': action_type})
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    router.save_run_state(run_root, run_state)
    return record

def _control_blocker_record(router: ModuleType, project_root: Path, active: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    raw_path = active.get('blocker_artifact_path')
    if not raw_path:
        return active
    path = resolve_project_path(project_root, str(raw_path))
    if not path.exists():
        return active
    return read_json(path)

def _control_blocker_matches_reconciled_action(router: ModuleType, record: dict[str, Any], *, action_type: str, controller_action_id: str, router_scheduler_row_id: str, postcondition: str, postcondition_satisfied: bool) -> str | None:
    _bind_router(router)
    if record.get('resolution_status'):
        return None
    originating_action_type = str(record.get('originating_action_type') or '')
    if originating_action_type and originating_action_type != action_type:
        return None
    blocker_action_id = str(record.get('originating_controller_action_id') or '')
    if blocker_action_id and controller_action_id and (blocker_action_id == controller_action_id):
        return 'matching_controller_action_id'
    blocker_row_id = str(record.get('originating_router_scheduler_row_id') or '')
    if blocker_row_id and router_scheduler_row_id and (blocker_row_id == router_scheduler_row_id):
        return 'matching_router_scheduler_row_id'
    blocker_postcondition = str(record.get('originating_postcondition') or '')
    if originating_action_type == action_type and blocker_postcondition and postcondition and (blocker_postcondition == postcondition) and postcondition_satisfied:
        return 'matching_postcondition'
    if record.get('source') == 'controller_action_receipt_missing_router_postcondition' and router._boot_action_meta(action_type) is not None and postcondition and postcondition_satisfied:
        return 'startup_bootloader_postcondition_fallback'
    return None

def _supersede_queued_control_blocker_actions(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, blocker_id: str, resolved_at: str, resolution_status: str) -> int:
    _bind_router(router)
    if not blocker_id:
        return 0
    superseded = 0
    action_dir = _controller_actions_dir(run_root)
    if action_dir.exists():
        for path in sorted(action_dir.glob('*.json')):
            entry = read_json_if_exists(path)
            if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
                continue
            if entry.get('action_type') != 'handle_control_blocker':
                continue
            if entry.get('status') in CONTROLLER_ACTION_CLOSED_STATUSES:
                continue
            action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
            if blocker_id not in {str(entry.get('blocker_id') or ''), str(action.get('blocker_id') or '')}:
                continue
            reconciliation = {'resolution_status': 'superseded_by_resolved_control_blocker', 'source_blocker_resolution_status': resolution_status, 'blocker_id': blocker_id, 'resolved_at': resolved_at}
            _update_controller_action_entry_fields(project_root, run_root, run_state, action_id=str(entry.get('action_id') or ''), status='superseded', fields={'router_reconciliation_status': 'superseded_by_resolved_control_blocker', 'router_reconciled_at': resolved_at, 'router_reconciliation': reconciliation, 'superseded_by_control_blocker_resolution': blocker_id}, router_state='superseded', reconciliation=reconciliation)
            superseded += 1
    pending = run_state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') == 'handle_control_blocker':
        if blocker_id == str(pending.get('blocker_id') or ''):
            run_state['pending_action'] = None
            append_history(run_state, 'router_cleared_pending_control_blocker_action_after_resolution', {'blocker_id': blocker_id, 'resolution_status': resolution_status})
    return superseded

def _resolve_control_blockers_for_reconciled_controller_action(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, action: dict[str, Any], entry: dict[str, Any] | None=None, reconciliation: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    action_type = str(action.get('action_type') or (entry or {}).get('action_type') or '')
    if not action_type:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    controller_action_id = str((entry or {}).get('action_id') or action.get('controller_action_id') or '')
    router_scheduler_row_id = str((entry or {}).get('router_scheduler_row_id') or action.get('router_scheduler_row_id') or '')
    postcondition = str(_pending_action_postcondition(action) or (reconciliation or {}).get('bootstrap_postcondition') or (reconciliation or {}).get('postcondition') or '')
    postcondition_satisfied = bool(postcondition and _pending_action_postcondition_satisfied(run_state, postcondition))
    control_root = run_root / 'control_blocks'
    if not control_root.exists():
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    resolved_ids: list[str] = []
    superseded_actions = 0
    resolved_at = utc_now()
    resolution_status = 'resolved_by_startup_reconciliation' if router._boot_action_meta(action_type) is not None else 'resolved_by_controller_action_reconciliation'
    for path in sorted(control_root.glob('*.json')):
        if path.name.endswith('.sealed_repair_packet.json') or path.name == 'blocker_repair_policy_snapshot.json':
            continue
        record = read_json_if_exists(path)
        if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
            continue
        match_reason = router._control_blocker_matches_reconciled_action(record, action_type=action_type, controller_action_id=controller_action_id, router_scheduler_row_id=router_scheduler_row_id, postcondition=postcondition, postcondition_satisfied=postcondition_satisfied)
        if not match_reason:
            continue
        blocker_id = str(record.get('blocker_id') or '')
        record['resolution_status'] = resolution_status
        record['resolution_reason'] = match_reason
        record['resolved_by_controller_action_id'] = controller_action_id or None
        record['resolved_by_router_scheduler_row_id'] = router_scheduler_row_id or None
        record['resolved_postcondition'] = postcondition or None
        record['resolved_at'] = resolved_at
        record['resolution_note'] = 'The originating Controller action/postcondition reconciled before this blocker needed role repair.'
        if reconciliation is not None:
            record['resolved_by_reconciliation'] = _json_safe(reconciliation)
        write_json(path, record)
        resolved_ids.append(blocker_id)
        superseded_actions += router._supersede_queued_control_blocker_actions(project_root, run_root, run_state, blocker_id=blocker_id, resolved_at=resolved_at, resolution_status=resolution_status)
    if not resolved_ids:
        return {'changed': False, 'resolved': 0, 'superseded_actions': 0}
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    append_history(run_state, 'router_resolved_control_blockers_by_controller_action_reconciliation', {'action_type': action_type, 'controller_action_id': controller_action_id, 'router_scheduler_row_id': router_scheduler_row_id, 'postcondition': postcondition, 'resolved_blocker_ids': resolved_ids, 'superseded_control_blocker_actions': superseded_actions})
    return {'changed': True, 'resolved': len(resolved_ids), 'resolved_blocker_ids': resolved_ids, 'superseded_actions': superseded_actions}

def _control_blocker_summary(router: ModuleType, record: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    fields = ('blocker_id', 'handling_lane', 'originating_handling_lane', 'policy_row_id', 'blocker_family', 'first_handler', 'attempt_key', 'direct_retry_budget', 'direct_retry_attempts_used', 'direct_retry_budget_exhausted', 'escalate_to', 'pm_recovery_options', 'return_policy', 'hard_stop_conditions', 'blocker_repair_policy_snapshot_path', 'blocker_artifact_path', 'target_role', 'responsible_role_for_reissue', 'pm_decision_required', 'delivery_status', 'sealed_repair_packet_path', 'sealed_repair_packet_hash', 'originating_event', 'originating_action_type', 'originating_controller_action_id', 'originating_router_scheduler_row_id', 'originating_postcondition', 'created_at', 'delivered_to_role', 'delivered_at', 'resolution_status', 'resolved_by_event', 'resolved_at', 'pm_repair_decision_status', 'pm_repair_decision_path', 'pm_repair_decision_hash', 'pm_repair_rerun_target', 'pm_recovery_option', 'pm_repair_return_gate', 'repair_origin', 'repair_transaction_id', 'repair_transaction_path', 'repair_outcome_table', 'allowed_resolution_events')
    return {field: record.get(field) for field in fields if field in record}

def _resume_reentry_gate_pending(router: ModuleType, run_state: dict[str, Any]) -> bool:
    _bind_router(router)
    flags = run_state.get('flags', {})
    return bool(flags.get('resume_reentry_requested')) and (not bool(flags.get('pm_resume_recovery_decision_returned')))

def _sync_protocol_blocker_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    blockers: list[dict[str, Any]] = []
    blocker_root = run_root / 'blockers'
    if blocker_root.exists():
        for path in sorted(blocker_root.glob('*.json')):
            record = read_json_if_exists(path)
            blockers.append({'path': project_relative(project_root, path), 'blocker_id': record.get('blocker_id') or path.stem, 'blocker_type': record.get('blocker_type'), 'status': record.get('status'), 'registered_at': record.get('registered_at') or utc_now()})
    run_state['protocol_blockers'] = blockers

def _sync_control_plane_indexes(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    summaries: list[dict[str, Any]] = []
    resolved: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    control_root = run_root / 'control_blocks'
    if control_root.exists():
        for path in sorted(control_root.glob('*.json')):
            record = read_json_if_exists(path)
            if record.get('schema_version') != CONTROL_BLOCKER_SCHEMA:
                continue
            summary = router._control_blocker_summary(record)
            summaries.append(summary)
            if record.get('resolution_status'):
                resolved.append(summary)
            else:
                active = summary
    run_state['control_blockers'] = summaries
    run_state['resolved_control_blockers'] = resolved
    run_state['active_control_blocker'] = active
    run_state['latest_control_blocker_path'] = active.get('blocker_artifact_path') if active else None
    router._sync_protocol_blocker_index(project_root, run_root, run_state)
    router._write_repair_transaction_index(project_root, run_root, run_state)

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
        return make_action(action_type='handle_control_blocker', actor='controller', label=f'controller_handles_{lane}_control_blocker', summary=f"Deliver router control blocker {record.get('blocker_id')} sealed repair packet envelope to {target_role}.", allowed_reads=[artifact_rel, project_relative(project_root, router.run_state_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'control_blocks' / 'control_blocker_delivery_ledger.json')], to_role=target_role, extra={'blocker_id': record.get('blocker_id'), 'blocker_artifact_path': artifact_rel, 'policy_row_id': record.get('policy_row_id'), 'blocker_family': record.get('blocker_family'), 'first_handler': record.get('first_handler'), 'direct_retry_budget': record.get('direct_retry_budget'), 'direct_retry_attempts_used': record.get('direct_retry_attempts_used'), 'direct_retry_budget_exhausted': record.get('direct_retry_budget_exhausted'), 'pm_recovery_options': record.get('pm_recovery_options') or [], 'return_policy': record.get('return_policy') or {}, 'hard_stop_conditions': record.get('hard_stop_conditions') or [], 'blocker_repair_policy_snapshot_path': record.get('blocker_repair_policy_snapshot_path'), 'sealed_repair_packet_path': record.get('sealed_repair_packet_path'), 'sealed_repair_packet_hash': record.get('sealed_repair_packet_hash'), 'handling_lane': lane, 'pm_decision_required': bool(record.get('pm_decision_required')), 'responsible_role_for_reissue': record.get('responsible_role_for_reissue'), 'repair_transaction_id': record.get('repair_transaction_id'), 'repair_outcome_table': record.get('repair_outcome_table'), 'controller_instruction': record.get('controller_instruction'), 'controller_allowed_actions': record.get('controller_allowed_actions') or [], 'controller_forbidden_actions': record.get('controller_forbidden_actions') or [], 'sealed_body_reads_allowed': False, 'controller_history_is_evidence': False, 'allowed_resolution_events': allowed_resolution_events, 'event_contract_issue': event_contract_issue, 'repair_details_visibility': 'sealed_to_target_role_not_controller', 'skill_observation_reminder': record.get('skill_observation_reminder')})
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
    router._sync_control_plane_indexes(project_root, run_root, run_state)

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

def _control_blocker_allows_resolution_event(router: ModuleType, record: dict[str, Any], event: str) -> bool:
    _bind_router(router)
    if record.get('handling_lane') in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        return False
    raw_events = record.get('allowed_resolution_events')
    if isinstance(raw_events, list) and raw_events:
        allowed_events = {name for item in raw_events if (name := router._control_resolution_event_name(item))}
        return event in allowed_events
    if record.get('handling_lane') == 'control_plane_reissue':
        return event == record.get('originating_event')
    return event in EXTERNAL_EVENTS

def _control_resolution_event_name(router: ModuleType, value: Any) -> str | None:
    _bind_router(router)
    if isinstance(value, dict):
        for key in ('event', 'corrected_followup_event', 'event_name'):
            name = str(value.get(key) or '').strip()
            if name:
                return router._control_resolution_event_name(name)
        return None
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text in EXTERNAL_EVENTS:
        return text
    parsed: Any = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            return None
    return router._control_resolution_event_name(parsed)

def _resolve_delivered_control_blocker(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, resolved_by_event: str, from_already_recorded_event: bool=False) -> dict[str, Any] | None:
    _bind_router(router)
    active = run_state.get('active_control_blocker')
    if not isinstance(active, dict) or active.get('delivery_status') != 'delivered':
        return None
    record = dict(active)
    artifact_rel = str(active.get('blocker_artifact_path') or '')
    artifact_path: Path | None = None
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            record = read_json(artifact_path)
    if from_already_recorded_event:
        lane = record.get('handling_lane')
        pm_repair_recorded = lane in PM_DECISION_REQUIRED_CONTROL_BLOCKER_LANES and record.get('pm_repair_decision_status') == 'recorded'
        if lane != 'control_plane_reissue' and (not pm_repair_recorded):
            return None
    if not router._control_blocker_allows_resolution_event(record, resolved_by_event):
        return None
    if artifact_path and artifact_path.exists():
        resolved_at = utc_now()
        record['resolution_status'] = 'accepted_followup_event_recorded'
        record['resolved_by_event'] = resolved_by_event
        record['resolved_at'] = resolved_at
        write_json(artifact_path, record)
    resolved = dict(active)
    resolved['resolution_status'] = 'accepted_followup_event_recorded'
    resolved['resolved_by_event'] = resolved_by_event
    resolved['resolved_at'] = record.get('resolved_at') or utc_now()
    run_state.setdefault('resolved_control_blockers', []).append(resolved)
    run_state['active_control_blocker'] = None
    run_state['latest_control_blocker_path'] = None
    append_history(run_state, 'router_resolved_control_blocker', {'blocker_id': resolved.get('blocker_id'), 'resolved_by_event': resolved_by_event})
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    return resolved

def _repair_transactions_root(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'control_blocks' / 'repair_transactions'

def _repair_transaction_index_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return router._repair_transactions_root(run_root) / 'repair_transaction_index.json'

def _repair_transaction_path(router: ModuleType, run_root: Path, transaction_id: str) -> Path:
    _bind_router(router)
    return router._repair_transactions_root(run_root) / f'{transaction_id}.json'

def _repair_transaction_id(router: ModuleType, blocker_id: str) -> str:
    _bind_router(router)
    safe = ''.join((ch if ch.isalnum() or ch in {'-', '_'} else '-' for ch in blocker_id)).strip('-')
    return f"repair-tx-{safe or 'control-blocker'}"

def _control_blocker_repair_origin(router: ModuleType, active: dict[str, Any], *, rerun_target: str, requested_plan_kind: str, run_root: Path, run_state: dict[str, Any]) -> str:
    _bind_router(router)
    originating_event = str(active.get('originating_event') or '')
    if requested_plan_kind == 'packet_reissue' or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS or originating_event in MATERIAL_REPAIR_OUTCOME_EVENTS or (originating_event in {'reviewer_blocks_material_scan_dispatch', 'reviewer_blocks_material_scan_dispatch_recheck'}):
        return 'material_dispatch'
    if rerun_target in PARENT_REPAIR_SAFE_EVENTS or originating_event in PARENT_REPAIR_SAFE_EVENTS or run_state.get('flags', {}).get('parent_backward_replay_blocked'):
        return 'parent_backward_replay'
    if rerun_target in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS or originating_event in LEAF_CURRENT_NODE_EVENT_CAPABILITY_EVENTS:
        return 'current_node_result'
    try:
        if router._active_node_kind_for_event_capability(run_root) in {'parent', 'module'} and originating_event in {'pm_records_parent_segment_decision', 'pm_completes_parent_node_from_backward_replay'}:
            return 'parent_backward_replay'
    except (RouterError, OSError, ValueError, TypeError):
        pass
    return 'none'

def _repair_outcome_table(router: ModuleType, rerun_target: str, *, repair_origin: str='none') -> dict[str, dict[str, Any]]:
    _bind_router(router)
    if rerun_target in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
        return {'success': {'event': 'router_direct_material_scan_dispatch_recheck_passed', 'terminal': 'complete'}, 'blocker': {'event': 'router_direct_material_scan_dispatch_recheck_blocked', 'terminal': 'blocked'}, 'protocol_blocker': {'event': 'router_protocol_blocker_material_scan_dispatch_recheck', 'terminal': 'blocked'}}
    if repair_origin == 'parent_backward_replay':
        if rerun_target not in PARENT_REPAIR_SAFE_EVENTS:
            raise RouterError('parent backward replay repair rerun_target must be a parent-safe event')
        if rerun_target in {'reviewer_blocks_parent_backward_replay', PM_PARENT_PROTOCOL_BLOCKER_EVENT}:
            raise RouterError('parent backward replay repair rerun_target must be a success-capable parent event')
        return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': 'reviewer_blocks_parent_backward_replay', 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_PARENT_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}
    if rerun_target in CONTROL_BLOCKER_REPAIR_NON_SUCCESS_EVENTS or rerun_target == PM_PARENT_PROTOCOL_BLOCKER_EVENT:
        raise RouterError('control blocker repair rerun_target must be a success-capable follow-up event')
    return {'success': {'event': rerun_target, 'terminal': 'complete'}, 'blocker': {'event': PM_CONTROL_BLOCKER_FOLLOWUP_BLOCKER_EVENT, 'terminal': 'blocked'}, 'protocol_blocker': {'event': PM_CONTROL_BLOCKER_PROTOCOL_BLOCKER_EVENT, 'terminal': 'blocked'}}

def _validate_repair_outcome_table(router: ModuleType, outcome_table: dict[str, Any], *, context: str, run_root: Path, run_state: dict[str, Any], repair_origin: str) -> None:
    _bind_router(router)
    events_by_kind: dict[str, str] = {}
    for kind in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(kind)
        if not isinstance(outcome, dict):
            raise RouterError(f'{context} requires {kind} outcome row')
        event = str(outcome.get('event') or '').strip()
        if not event:
            raise RouterError(f'{context} {kind} outcome row requires event')
        events_by_kind[kind] = event
    if len(set(events_by_kind.values())) != len(events_by_kind):
        raise RouterError(f'{context} must use distinct success, blocker, and protocol-blocker events')
    for kind, event in events_by_kind.items():
        router._validated_event_capability_names([event], context=f'{context} {kind} outcome', run_root=run_root, run_state=run_state, usage='repair_outcome', repair_origin=repair_origin, outcome_kind=kind, allow_pm_repair_event=False)

def _repair_outcome_events(router: ModuleType, outcome_table: dict[str, Any]) -> list[str]:
    _bind_router(router)
    events: list[str] = []
    for name in ('success', 'blocker', 'protocol_blocker'):
        outcome = outcome_table.get(name)
        if not isinstance(outcome, dict):
            continue
        event = str(outcome.get('event') or '').strip()
        if event and event not in events:
            events.append(event)
    return events

def _repair_packet_specs_from_decision(router: ModuleType, project_root: Path, run_root: Path, decision: dict[str, Any], *, rerun_target: str) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    _bind_router(router)
    transaction = decision.get('repair_transaction') if isinstance(decision.get('repair_transaction'), dict) else {}
    raw_packets = transaction.get('replacement_packets') or transaction.get('packets') or decision.get('replacement_packets') or decision.get('packets')
    if isinstance(raw_packets, list) and raw_packets:
        return (raw_packets, {'source': 'decision_inline', 'packet_count': len(raw_packets)})
    raw_path = transaction.get('replacement_packet_specs_path') or transaction.get('packet_reissue_spec_path') or decision.get('replacement_packet_specs_path') or decision.get('packet_reissue_spec_path')
    if not raw_path and rerun_target in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
        default_path = run_root / 'material' / 'pm_material_scan_packet_specs_reissue.project_manager.json'
        if default_path.exists():
            raw_path = project_relative(project_root, default_path)
    if not raw_path:
        return ([], None)
    spec_path = resolve_project_path(project_root, str(raw_path))
    if not spec_path.exists():
        raise RouterError(f'repair transaction packet spec path is missing: {raw_path}')
    expected_hash = transaction.get('replacement_packet_specs_hash') or transaction.get('packet_reissue_spec_hash') or decision.get('replacement_packet_specs_hash') or decision.get('packet_reissue_spec_hash')
    if expected_hash and packet_runtime.sha256_file(spec_path) != str(expected_hash):
        raise RouterError('repair transaction packet spec hash mismatch')
    spec = read_json(spec_path)
    packets = spec.get('packets')
    if not isinstance(packets, list) or not packets:
        raise RouterError('repair transaction packet spec requires non-empty packets')
    return (packets, {'source': 'packet_spec_file', 'path': project_relative(project_root, spec_path), 'sha256': packet_runtime.sha256_file(spec_path), 'packet_count': len(packets)})

def _write_repair_transaction_index(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    root = router._repair_transactions_root(run_root)
    transactions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    if root.exists():
        for path in sorted(root.glob('repair-tx-*.json')):
            record = read_json_if_exists(path)
            if record.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
                continue
            summary = {'transaction_id': record.get('transaction_id'), 'blocker_id': record.get('blocker_id'), 'status': record.get('status'), 'plan_kind': record.get('plan_kind'), 'packet_generation_id': record.get('packet_generation_id'), 'path': project_relative(project_root, path), 'outcome_table': record.get('outcome_table')}
            transactions.append(summary)
            if record.get('status') in {'opened', 'committed', 'awaiting_recheck'}:
                active = summary
    index = {'schema_version': REPAIR_TRANSACTION_INDEX_SCHEMA, 'run_id': run_state.get('run_id'), 'active_transaction': active, 'transactions': transactions, 'updated_at': utc_now()}
    write_json(router._repair_transaction_index_path(run_root), index)
    run_state['repair_transactions'] = transactions
    run_state['active_repair_transaction'] = active

def _commit_material_scan_repair_generation(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, transaction_id: str, packet_generation_id: str, packet_specs: list[dict[str, Any]]) -> dict[str, Any]:
    _bind_router(router)
    existing_index = read_json_if_exists(router._material_scan_index_path(run_root))
    superseded_packets = []
    for record in existing_index.get('packets', []) if isinstance(existing_index.get('packets'), list) else []:
        if isinstance(record, dict):
            superseded = dict(record)
            superseded['is_current_generation'] = False
            superseded['superseded_by_generation_id'] = packet_generation_id
            superseded_packets.append(superseded)
    records: list[dict[str, Any]] = []
    for index, spec in enumerate(packet_specs, start=1):
        if not isinstance(spec, dict):
            raise RouterError('each repair transaction packet spec must be an object')
        packet_id = str(spec.get('packet_id') or f'material-scan-repair-{index:03d}')
        to_role = str(spec.get('to_role') or 'worker_a')
        if to_role not in {'worker_a', 'worker_b'}:
            raise RouterError('material scan repair packet must target worker_a or worker_b')
        body_text = router._material_packet_body_text_from_spec(project_root, spec)
        envelope = packet_runtime.create_packet(project_root, run_id=str(run_state['run_id']), packet_id=packet_id, from_role='project_manager', to_role=to_role, node_id=str(spec.get('node_id') or 'material-intake'), body_text=body_text, is_current_node=False, packet_type='material_scan', metadata={'stage': 'material_scan', 'source': 'repair_transaction_commit', 'repair_transaction_id': transaction_id, 'packet_generation_id': packet_generation_id, 'replacement_for': spec.get('replacement_for'), **(spec.get('metadata') if isinstance(spec.get('metadata'), dict) else {})}, output_contract=spec.get('output_contract') if isinstance(spec.get('output_contract'), dict) else None)
        paths = packet_runtime.packet_paths(project_root, packet_id, str(run_state['run_id']))
        records.append({'packet_id': packet_id, 'to_role': to_role, 'packet_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'replacement_for': spec.get('replacement_for'), 'is_current_generation': True, 'packet_envelope_path': envelope['body_path'].replace('packet_body.md', 'packet_envelope.json'), 'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body']), 'result_write_target': {'result_envelope_path': project_relative(project_root, paths['result_envelope']), 'result_body_path': project_relative(project_root, paths['result_body'])}, 'output_contract_id': envelope.get('output_contract_id')})
    write_json(router._material_scan_index_path(run_root), {'schema_version': 'flowpilot.material_scan_packets.v2', 'run_id': run_state['run_id'], 'written_by_role': 'project_manager', 'controller_may_read_packet_body': False, 'router_direct_dispatch_required_before_worker': True, 'reviewer_dispatch_required_before_worker': False, 'current_generation_id': packet_generation_id, 'repair_transaction_id': transaction_id, 'packets': records, 'superseded_packets': superseded_packets, 'written_at': utc_now()})
    run_state['flags']['material_scan_packets_relayed'] = False
    run_state['flags']['worker_packets_delivered'] = False
    run_state['flags']['worker_scan_results_returned'] = False
    run_state['flags']['material_scan_results_relayed_to_reviewer'] = False
    run_state['flags']['material_scan_results_relayed_to_pm'] = False
    run_state['flags']['material_scan_result_disposition_recorded'] = False
    run_state['flags']['material_scan_results_absorbed_by_pm'] = False
    run_state['flags']['material_review_sufficient'] = False
    run_state['flags']['material_review_insufficient'] = False
    run_state['material_review'] = None
    return {'packet_generation_id': packet_generation_id, 'packet_count': len(records), 'packets': records, 'superseded_packet_count': len(superseded_packets), 'dispatch_index_path': project_relative(project_root, router._material_scan_index_path(run_root)), 'packet_ledger_path': project_relative(project_root, run_root / 'packet_ledger.json')}

def _active_repair_transaction_for_event(router: ModuleType, run_root: Path, event: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    _bind_router(router)
    root = router._repair_transactions_root(run_root)
    if not root.exists():
        return (None, None)
    for path in sorted(root.glob('repair-tx-*.json'), reverse=True):
        record = read_json_if_exists(path)
        if record.get('schema_version') != REPAIR_TRANSACTION_SCHEMA:
            continue
        if record.get('status') not in {'committed', 'awaiting_recheck', 'opened'}:
            continue
        if event in router._repair_outcome_events(record.get('outcome_table') if isinstance(record.get('outcome_table'), dict) else {}):
            return (path, record)
    return (None, None)

def _repair_transaction_outcome_kind(router: ModuleType, transaction: dict[str, Any], event: str) -> str | None:
    _bind_router(router)
    table = transaction.get('outcome_table')
    if not isinstance(table, dict):
        return None
    for kind in ('success', 'blocker', 'protocol_blocker'):
        outcome = table.get(kind)
        if isinstance(outcome, dict) and outcome.get('event') == event:
            return kind
    return None

def _clear_successful_repair_lane_state(router: ModuleType, run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    _bind_router(router)
    rerun_target = str(transaction.get('rerun_target') or '')
    is_material_repair = event in MATERIAL_REPAIR_OUTCOME_EVENTS or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS
    flags = run_state.get('flags')
    if isinstance(flags, dict) and is_material_repair:
        for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
            flags[flag] = False
        if event in {'router_direct_material_scan_dispatch_recheck_passed', 'reviewer_allows_material_scan_dispatch'}:
            flags['material_scan_dispatch_blocked'] = False
    if is_material_repair:
        run_state['material_dispatch_block'] = None
    pending = run_state.get('pending_action')
    if isinstance(pending, dict):
        outcome_events = set(router._repair_outcome_events(transaction.get('outcome_table') if isinstance(transaction.get('outcome_table'), dict) else {}))
        pending_events = set((str(item) for item in pending.get('allowed_external_events', []) if isinstance(item, str)))
        if pending.get('repair_transaction_id') == transaction.get('transaction_id') or (pending_events and pending_events.issubset(outcome_events)):
            run_state['pending_action'] = None

def _finalize_repair_transaction_outcome(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, event: str, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    _bind_router(router)
    tx_path, transaction = router._active_repair_transaction_for_event(run_root, event)
    if tx_path is None or transaction is None:
        return None
    outcome_kind = router._repair_transaction_outcome_kind(transaction, event)
    if not outcome_kind:
        return None
    now = utc_now()
    transaction['reviewer_recheck'] = {'outcome': outcome_kind, 'event': event, 'payload_envelope_public_view': router._control_payload_public_view(payload), 'recorded_at': now}
    if outcome_kind == 'success':
        transaction['status'] = 'complete'
        transaction['completed_at'] = now
        write_json(tx_path, transaction)
        router._clear_successful_repair_lane_state(run_state, transaction, event=event)
        router._write_repair_transaction_index(project_root, run_root, run_state)
        return {'transaction_id': transaction.get('transaction_id'), 'outcome': outcome_kind, 'status': 'complete'}
    transaction['status'] = 'blocked'
    transaction['blocked_at'] = now
    transaction['followup_blocker_required'] = True
    write_json(tx_path, transaction)
    blocker_id = str(transaction.get('blocker_id') or '')
    active = run_state.get('active_control_blocker')
    artifact_rel = str(active.get('blocker_artifact_path') or '') if isinstance(active, dict) else ''
    if artifact_rel:
        artifact_path = resolve_project_path(project_root, artifact_rel)
        if artifact_path.exists():
            blocker_record = read_json(artifact_path)
            if blocker_record.get('blocker_id') == blocker_id:
                blocker_record['resolution_status'] = f'repair_transaction_{outcome_kind}'
                blocker_record['resolved_by_event'] = event
                blocker_record['resolved_at'] = now
                blocker_record['repair_transaction_id'] = transaction.get('transaction_id')
                write_json(artifact_path, blocker_record)
    followup = router._write_control_blocker(project_root, run_root, run_state, source='repair_transaction_recheck', error_message=f"repair transaction {transaction.get('transaction_id')} ended with reviewer {outcome_kind}; PM repair or routing decision is required before retrying dispatch.", event=event, payload=payload)
    transaction['followup_blocker_id'] = followup.get('blocker_id')
    transaction['followup_blocker_path'] = followup.get('blocker_artifact_path')
    write_json(tx_path, transaction)
    router._write_repair_transaction_index(project_root, run_root, run_state)
    return {'transaction_id': transaction.get('transaction_id'), 'outcome': outcome_kind, 'status': 'blocked', 'followup_blocker_id': followup.get('blocker_id')}


_LOCAL_NAMES = set(globals())
