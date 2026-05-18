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

__all__ = (
    '_control_blocker_error_code',
    '_blocker_repair_policy_snapshot_path',
    '_blocker_repair_policy_rows',
    '_write_blocker_repair_policy_snapshot',
    '_control_blocker_policy_row',
    '_control_blocker_attempt_key',
    '_control_blocker_direct_attempts_used',
    '_policy_first_handler_target',
    '_pm_recovery_options_from_policy',
    '_default_pm_recovery_option',
    '_project_relative_if_possible',
    '_payload_source_paths',
    '_control_payload_public_view',
    '_infer_responsible_role',
    '_classify_control_blocker',
    '_should_materialize_control_blocker',
    '_skill_observation_reminder',
    '_validated_external_event_names',
    '_active_node_kind_for_event_capability',
    '_event_capability_issue',
    '_run_state_with_assumed_flag',
    '_validated_event_capability_names',
    '_external_event_validation_issue',
    '_control_blocker_allowed_resolution_events',
    '_control_blocker_policy',
)

_LOCAL_NAMES = set(globals())
