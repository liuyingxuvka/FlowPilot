"""Coarse route frontier owner helpers for the FlowPilot router.

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

def _event_markers(router: ModuleType, run_state: dict[str, Any], names: set[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    markers: list[dict[str, Any]] = []
    for event in run_state.get('events') or []:
        if not isinstance(event, dict):
            continue
        event_name = str(event.get('event') or '')
        if event_name not in names:
            continue
        markers.append({'event': event_name, 'summary': event.get('summary'), 'recorded_at': event.get('recorded_at')})
    return markers

def _route_node_history(router: ModuleType, project_root: Path, run_root: Path, route_id: str, route: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    nodes: list[dict[str, Any]] = []
    for node in router._route_nodes(route):
        node_id = str(node['node_id'])
        node_root = run_root / 'routes' / route_id / 'nodes' / node_id
        source_paths = {'node_acceptance_plan': router._optional_source_path(project_root, node_root / 'node_acceptance_plan.json'), 'node_acceptance_plan_review': router._optional_source_path(project_root, node_root / 'reviews' / 'node_acceptance_plan_review.json'), 'parent_backward_replay': router._optional_source_path(project_root, node_root / 'parent_backward_replay.json'), 'pm_parent_segment_decision': router._optional_source_path(project_root, node_root / 'pm_parent_segment_decision.json')}
        nodes.append({'node_id': node_id, 'title': node.get('title'), 'status': node.get('status') or 'unknown', 'created_by_mutation': bool(node.get('created_by_mutation')), 'superseded_by': node.get('superseded_by'), 'source_paths': {key: value for key, value in source_paths.items() if value}})
    return nodes

def _refresh_route_memory(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, trigger: str) -> None:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    route_id = str(frontier.get('active_route_id') or '')
    route_version = int(frontier.get('route_version') or 0)
    route_path = run_root / 'routes' / route_id / 'flow.json' if route_id else run_root / 'routes' / 'route-001' / 'flow.json'
    route = read_json_if_exists(route_path)
    mutations_path = run_root / 'routes' / route_id / 'mutations.json' if route_id else run_root / 'routes' / 'route-001' / 'mutations.json'
    mutations = read_json_if_exists(mutations_path)
    stale_ledger_path = run_root / 'evidence' / 'stale_evidence_ledger.json'
    stale_ledger = read_json_if_exists(stale_ledger_path)
    evidence_ledger_path = run_root / 'evidence' / 'evidence_ledger.json'
    evidence_ledger = read_json_if_exists(evidence_ledger_path)
    generated_ledger_path = run_root / 'generated_resource_ledger.json'
    generated_ledger = read_json_if_exists(generated_ledger_path)
    completed_nodes = [str(item) for item in frontier.get('completed_nodes') or []]
    mutation_items = [item for item in mutations.get('items') or [] if isinstance(item, dict)]
    superseded_nodes = sorted({str(node_id) for item in mutation_items for node_id in router._route_mutation_superseded_nodes(item)})
    stale_evidence = sorted({str(item.get('evidence_id')) for item in stale_ledger.get('items') or [] if isinstance(item, dict) and item.get('evidence_id')} | {str(evidence_id) for item in mutation_items for evidence_id in item.get('stale_evidence') or []})
    effective_nodes = [str(node.get('node_id')) for node in router._effective_route_nodes(route, mutations) if node.get('node_id')]
    route_nodes = router._route_node_history(project_root, run_root, route_id or 'route-001', route)
    reviewer_blocks = router._event_markers(run_state, {'current_node_reviewer_blocks_result', 'reviewer_blocks_current_node_dispatch', 'reviewer_blocks_node_acceptance_plan', 'reviewer_reports_material_insufficient', 'reviewer_blocks_material_scan_dispatch'})
    reviewer_passes = router._event_markers(run_state, {'reviewer_reports_material_sufficient', 'reviewer_passes_research_direct_source_check', 'reviewer_passes_node_acceptance_plan', 'current_node_reviewer_passes_result', 'reviewer_passes_parent_backward_replay', 'reviewer_passes_evidence_quality_package', 'reviewer_final_backward_replay_passed'})
    research_or_experiments = []
    for label, path in (('research_package', run_root / 'research' / 'research_package.json'), ('worker_research_report', run_root / 'research' / 'worker_research_report.json'), ('research_reviewer_report', run_root / 'research' / 'research_reviewer_report.json'), ('product_architecture_modelability', run_root / 'flowguard' / 'product_architecture_modelability.json'), ('root_contract_modelability', run_root / 'flowguard' / 'root_contract_modelability.json'), ('child_skill_conformance_model', run_root / 'flowguard' / 'child_skill_conformance_model.json'), ('child_skill_product_fit', run_root / 'flowguard' / 'child_skill_product_fit.json')):
        source_path = router._optional_source_path(project_root, path)
        if source_path:
            research_or_experiments.append({'kind': label, 'source_path': source_path})
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root)), 'execution_frontier': router._optional_source_path(project_root, run_root / 'execution_frontier.json'), 'active_route': router._optional_source_path(project_root, route_path), 'route_mutations': router._optional_source_path(project_root, mutations_path), 'packet_ledger': router._optional_source_path(project_root, run_root / 'packet_ledger.json'), 'prompt_delivery_ledger': router._optional_source_path(project_root, run_root / 'prompt_delivery_ledger.json'), 'evidence_ledger': router._optional_source_path(project_root, evidence_ledger_path), 'stale_evidence_ledger': router._optional_source_path(project_root, stale_ledger_path), 'generated_resource_ledger': router._optional_source_path(project_root, generated_ledger_path)}
    history_index = {'schema_version': ROUTE_HISTORY_INDEX_SCHEMA, 'run_id': run_state['run_id'], 'generated_by': 'controller', 'controller_decision_authority': False, 'sealed_packet_or_result_bodies_read': False, 'trigger': trigger, 'refreshed_at': utc_now(), 'frontier': {'status': frontier.get('status'), 'active_route_id': frontier.get('active_route_id'), 'active_node_id': frontier.get('active_node_id'), 'route_version': route_version, 'completed_nodes': completed_nodes, 'latest_mutation_path': frontier.get('latest_mutation_path')}, 'route': {'effective_nodes': effective_nodes, 'node_history': route_nodes, 'route_node_count': len(route_nodes)}, 'mutations': {'count': len(mutation_items), 'superseded_nodes': superseded_nodes, 'items': [{'route_version': item.get('route_version'), 'active_node_id': item.get('active_node_id'), 'reason': item.get('reason'), 'superseded_nodes': router._route_mutation_superseded_nodes(item), 'affected_sibling_nodes': item.get('affected_sibling_nodes') or [], 'replay_scope_node_id': item.get('replay_scope_node_id'), 'stale_evidence': item.get('stale_evidence') or [], 'recorded_at': item.get('recorded_at')} for item in mutation_items]}, 'evidence': {'stale_evidence': stale_evidence, 'unresolved_count': int(evidence_ledger.get('unresolved_count', 0) or 0), 'stale_count': int(evidence_ledger.get('stale_count', 0) or 0), 'generated_pending_resource_count': int(generated_ledger.get('pending_resource_count', 0) or 0), 'generated_unresolved_resource_count': int(generated_ledger.get('unresolved_resource_count', 0) or 0)}, 'review_markers': {'blocks': reviewer_blocks, 'passes': reviewer_passes}, 'research_or_experiments': research_or_experiments, 'source_paths': {key: value for key, value in source_paths.items() if value}}
    write_json(router._route_history_index_path(run_root), history_index)
    pm_context = {'schema_version': PM_PRIOR_PATH_CONTEXT_SCHEMA, 'run_id': run_state['run_id'], 'generated_by': 'controller', 'controller_decision_authority': False, 'sealed_packet_or_result_bodies_read': False, 'trigger': trigger, 'refreshed_at': history_index['refreshed_at'], 'route_position': history_index['frontier'], 'completed_nodes_considered': completed_nodes, 'effective_nodes_considered': effective_nodes, 'superseded_nodes_considered': superseded_nodes, 'stale_evidence_considered': stale_evidence, 'review_blocks_considered': reviewer_blocks, 'review_passes_considered': reviewer_passes, 'research_or_experiment_outputs_considered': research_or_experiments, 'future_route_decision_requirements': ['Before route draft, route mutation, repair-node creation, node acceptance planning, resume continuation, final ledger, or closure, PM must read this current context and cite its path.', 'PM must explain how completed, superseded, stale, blocked, and experimental history changes the next route or node decision.', 'Controller-provided history is an index of reviewed files and state only; PM must not treat it as evidence beyond the cited source paths.'], 'source_paths': {**{key: value for key, value in source_paths.items() if value}, 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root))}}
    write_json(router._pm_prior_path_context_path(run_root), pm_context)
    run_state['flags']['route_history_index_refreshed'] = True
    run_state['flags']['pm_prior_path_context_refreshed'] = True

def _require_pm_prior_path_context(router: ModuleType, project_root: Path, run_root: Path, payload: dict[str, Any], *, purpose: str) -> dict[str, Any]:
    _bind_router(router)
    context_path = router._pm_prior_path_context_path(run_root)
    history_path = router._route_history_index_path(run_root)
    if not context_path.exists() or not history_path.exists():
        raise RouterError(f'{purpose} requires refreshed route memory before PM decision')
    review = payload.get('prior_path_context_review')
    if not isinstance(review, dict):
        raise RouterError(f'{purpose} requires prior_path_context_review')
    if review.get('reviewed') is not True:
        raise RouterError(f'{purpose} requires prior_path_context_review.reviewed=true')
    if review.get('controller_summary_used_as_evidence') is True:
        raise RouterError(f'{purpose} cannot treat Controller route history as acceptance evidence')
    expected_context = project_relative(project_root, context_path)
    expected_history = project_relative(project_root, history_path)
    source_paths = [str(path) for path in review.get('source_paths') or []]
    if expected_context not in source_paths:
        raise RouterError(f'{purpose} must cite current pm_prior_path_context.json')
    if expected_history not in source_paths:
        raise RouterError(f'{purpose} must cite current route_history_index.json')
    missing = [field for field in PM_PRIOR_PATH_CONTEXT_REVIEW_REQUIRED_FIELDS if field not in review and field not in {'reviewed', 'source_paths'}]
    if missing:
        raise RouterError(f"{purpose} prior_path_context_review missing fields: {', '.join(missing)}")
    return {'reviewed': True, 'source_paths': [expected_context, expected_history], 'completed_nodes_considered': review.get('completed_nodes_considered') or [], 'superseded_nodes_considered': review.get('superseded_nodes_considered') or [], 'stale_evidence_considered': review.get('stale_evidence_considered') or [], 'prior_blocks_or_experiments_considered': review.get('prior_blocks_or_experiments_considered') or [], 'impact_on_decision': review.get('impact_on_decision'), 'controller_summary_used_as_evidence': False}

def _pm_context_action_extra(router: ModuleType, project_root: Path, run_root: Path, entry: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    if entry.get('to_role') != 'project_manager':
        return {}
    context_path = router._pm_prior_path_context_path(run_root)
    history_path = router._route_history_index_path(run_root)
    extra = {'pm_context_paths': {'pm_prior_path_context': project_relative(project_root, context_path), 'route_history_index': project_relative(project_root, history_path)}, 'pm_prior_path_context_required_for_decision': entry.get('card_id') in PM_PRIOR_CONTEXT_REQUIRED_CARD_IDS, 'controller_history_is_evidence': False}
    return extra

def _card_required_source_paths(router: ModuleType, project_root: Path, run_root: Path, card_id: str) -> dict[str, str]:
    _bind_router(router)
    source_paths: dict[str, str] = {}
    for label, relative_path in CARD_REQUIRED_SOURCE_PATHS.get(card_id, {}).items():
        path = run_root / relative_path
        if path.exists():
            source_paths[label] = project_relative(project_root, path)
    if card_id in {'process_officer.route_process_check', 'product_officer.route_product_check', 'reviewer.route_challenge'}:
        for draft_path in sorted((run_root / 'routes').glob('*/flow.draft.json')):
            source_paths[f'route_draft_{draft_path.parent.name}'] = project_relative(project_root, draft_path)
    return source_paths

def _card_delivery_phase(router: ModuleType, card_id: str, card: dict[str, Any], frontier: dict[str, Any], run_state: dict[str, Any]) -> tuple[str, str | None]:
    _bind_router(router)
    card_phase = CARD_PHASE_BY_ID.get(card_id) or card.get('phase')
    current_phase = str(card_phase or frontier.get('phase') or frontier.get('status') or run_state.get('phase') or 'unknown')
    return (current_phase, str(card_phase or '') or None)

def _live_card_delivery_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], entry: dict[str, Any], card: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    card_id = str(entry.get('card_id') or card.get('id') or '')
    current_phase, card_phase = router._card_delivery_phase(card_id, card, frontier, run_state)
    user_request_path = str(run_state.get('user_request_path') or router._optional_source_path(project_root, run_root / 'user_request.json') or '')
    startup_intake_record_path = str(run_state.get('startup_intake_record_path') or router._optional_source_path(project_root, run_root / 'startup_intake' / 'startup_intake_record.json') or '')
    source_paths = {'router_state': project_relative(project_root, router.run_state_path(run_root)), 'execution_frontier': router._optional_source_path(project_root, run_root / 'execution_frontier.json'), 'prompt_delivery_ledger': router._optional_source_path(project_root, run_root / 'prompt_delivery_ledger.json'), 'packet_ledger': router._optional_source_path(project_root, run_root / 'packet_ledger.json'), 'route_history_index': router._optional_source_path(project_root, router._route_history_index_path(run_root)), 'pm_prior_path_context': router._optional_source_path(project_root, router._pm_prior_path_context_path(run_root)), 'user_request_path': user_request_path or None, 'startup_intake_record_path': startup_intake_record_path or None}
    source_paths.update(router._card_required_source_paths(project_root, run_root, card_id))
    return {'schema_version': LIVE_CARD_CONTEXT_SCHEMA, 'run_id': str(run_state.get('run_id') or run_root.name), 'card_id': card_id, 'to_role': str(entry.get('to_role') or card.get('audience') or ''), 'current_task': {'user_request_path': user_request_path or None, 'startup_intake_record_path': startup_intake_record_path or None, 'user_intake_packet_id': 'user_intake' if (run_root / 'mailbox' / 'outbox' / 'user_intake.json').exists() else None, 'task_authority': 'startup_intake_ui_record_and_user_intake' if startup_intake_record_path else 'router_recorded_user_request_and_user_intake', 'controller_summary_is_task_authority': False, 'reviewer_live_review_source': 'startup_intake_record' if startup_intake_record_path else None}, 'current_stage': {'current_phase': current_phase, 'card_phase': card_phase, 'frontier_status': frontier.get('status'), 'current_node_id': frontier.get('active_node_id'), 'current_route_id': frontier.get('active_route_id'), 'route_version': frontier.get('route_version')}, 'source_paths': source_paths, 'role_prompt_rule': 'Treat this router delivery envelope as the live context for the current run, current task, current card, current phase, and current node/frontier. If required context is missing or stale, do not continue from memory; submit a protocol blocker through the Router-directed runtime path.'}

def _matching_controller_delivery_actions(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool) -> list[dict[str, Any]]:
    _bind_router(router)
    matches: list[dict[str, Any]] = []
    action_dir = _controller_actions_dir(run_root)
    if not action_dir.exists():
        return matches
    for path in sorted(action_dir.glob('*.json')):
        entry = read_json_if_exists(path)
        if entry.get('schema_version') != CONTROLLER_ACTION_SCHEMA:
            continue
        action = entry.get('action') if isinstance(entry.get('action'), dict) else {}
        if not _controller_delivery_action_matches_pending_return(action, record, bundle=bundle):
            continue
        receipt_path = str(entry.get('receipt_path') or entry.get('expected_receipt_path') or '')
        matches.append({'action_id': entry.get('action_id'), 'action_type': entry.get('action_type'), 'status': entry.get('status') or 'pending', 'action_path': project_relative(project_root, path), 'receipt_path': receipt_path, 'updated_at': entry.get('updated_at'), 'completed_at': entry.get('completed_at')})
    return matches

def _controller_delivery_fact_for_pending_return(router: ModuleType, project_root: Path, run_root: Path, record: dict[str, Any], *, bundle: bool, committed_extra: dict[str, Any] | None=None) -> dict[str, Any]:
    _bind_router(router)
    extra = committed_extra
    if extra is None:
        extra = _committed_card_bundle_artifact_extra(project_root, record, relay_allowed_if_ready=True) if bundle else _committed_card_artifact_extra(project_root, record, relay_allowed_if_ready=True)
    matches = router._matching_controller_delivery_actions(project_root, run_root, record, bundle=bundle)
    statuses = {str(item.get('status') or 'pending') for item in matches}
    artifact_committed = bool(extra.get('artifact_committed'))
    if not artifact_committed:
        status = 'committed_artifact_missing_or_invalid'
        target_allowed = False
        reissue_reason = 'original_committed_artifact_missing_or_invalid'
    elif 'done' in statuses:
        status = 'controller_delivery_done'
        target_allowed = True
        reissue_reason = ''
    elif 'blocked' in statuses:
        status = 'controller_delivery_blocked'
        target_allowed = False
        reissue_reason = 'controller_delivery_blocked'
    elif 'skipped' in statuses and (not statuses - {'skipped'}):
        status = 'controller_delivery_skipped'
        target_allowed = False
        reissue_reason = 'controller_delivery_skipped'
    elif matches:
        status = 'controller_delivery_unconfirmed'
        target_allowed = False
        reissue_reason = 'controller_delivery_not_marked_done'
    else:
        status = 'controller_delivery_fact_unrecorded'
        target_allowed = True
        reissue_reason = ''
    controller_read_paths: list[str] = []
    for item in matches:
        for key in ('action_path', 'receipt_path'):
            value = str(item.get(key) or '')
            if value and value not in controller_read_paths:
                controller_read_paths.append(value)
    return {'schema_version': 'flowpilot.controller_delivery_fact.v1', 'return_kind': 'system_card_bundle' if bundle else 'system_card', 'card_id': None if bundle else record.get('card_id'), 'card_bundle_id': record.get('card_bundle_id') if bundle else None, 'delivery_attempt_id': None if bundle else record.get('delivery_attempt_id'), 'delivery_attempt_ids': record.get('delivery_attempt_ids') if bundle else None, 'card_envelope_path': record.get('card_bundle_envelope_path') if bundle else record.get('card_envelope_path'), 'expected_return_path': record.get('expected_return_path'), 'artifact_committed': artifact_committed, 'artifact_exists': bool(extra.get('artifact_exists')), 'artifact_hash_verified': bool(extra.get('artifact_hash_verified')), 'matching_controller_actions': matches, 'controller_read_paths': controller_read_paths, 'controller_delivery_fact_status': status, 'controller_delivery_done': status == 'controller_delivery_done', 'controller_delivery_fact_unrecorded': status == 'controller_delivery_fact_unrecorded', 'target_role_ack_reminder_allowed': target_allowed, 'target_role_ack_reminder_blocked_until_controller_delivery_done': not target_allowed, 'controller_delivery_reissue_required': not target_allowed, 'controller_delivery_reissue_reason': reissue_reason, 'controller_must_not_remind_target_before_delivery_done': True}

def _write_route_draft(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose='route draft')
    contract_path = run_root / 'root_acceptance_contract.json'
    if not contract_path.exists():
        raise RouterError('route draft requires frozen root contract')
    contract = read_json(contract_path)
    if contract.get('status') != 'frozen':
        raise RouterError('route draft requires root contract status=frozen')
    sync_path = run_root / 'capabilities' / 'capability_sync.json'
    child_manifest_path = run_root / 'child_skill_gate_manifest.json'
    if not sync_path.exists():
        raise RouterError('route draft requires capability evidence sync')
    if not child_manifest_path.exists() or read_json(child_manifest_path).get('status') != 'approved':
        raise RouterError('route draft requires approved child-skill gate manifest')
    product_model_path = router._require_product_behavior_model_report(project_root, run_root)
    route_id = str(payload.get('route_id') or 'route-001')
    route_root = run_root / 'routes' / route_id
    draft = payload.get('route') if isinstance(payload.get('route'), dict) else {}
    route_payload = dict(payload)
    original_schema_version = route_payload.get('schema_version')
    if original_schema_version and original_schema_version != 'flowpilot.route_draft.v1':
        route_payload['pm_authored_payload_schema_version'] = original_schema_version
    route_payload['schema_version'] = 'flowpilot.route_draft.v1'
    route_payload['run_id'] = run_state['run_id']
    route_payload['route_id'] = route_id
    route_payload['route_version'] = int(payload.get('route_version') or draft.get('route_version') or 1)
    route_payload['source_root_contract'] = project_relative(project_root, contract_path)
    route_payload['source_product_behavior_model'] = project_relative(project_root, product_model_path)
    route_payload['source_product_behavior_model_hash'] = hashlib.sha256(product_model_path.read_bytes()).hexdigest()
    route_payload['prior_path_context_review'] = prior_review
    root_requirement_ids = router._root_requirement_ids(contract)
    route_payload['requirement_traceability_policy'] = {'schema_version': 'flowpilot.route_requirement_traceability.v1', 'source_root_contract': project_relative(project_root, contract_path), 'source_product_architecture': project_relative(project_root, run_root / 'product_function_architecture.json'), 'full_protocol_required_when_flowpilot_invoked': True, 'light_or_simple_profiles_forbidden': True, 'every_node_requires_requirement_or_risk_rationale': True, 'external_spec_material_advisory_until_pm_imported': True}
    route_payload['nodes'] = router._route_nodes_with_requirement_trace(draft.get('nodes') or payload.get('nodes') or [], root_requirement_ids)
    route_payload['written_by_role'] = 'project_manager'
    route_payload['written_at'] = str(payload.get('written_at') or utc_now())
    route_payload['router_preservation'] = {'schema_version': 'flowpilot.router_artifact_preservation.v1', 'canonical_source': 'pm_role_output_body', 'official_artifact_path': project_relative(project_root, route_root / 'flow.draft.json'), 'role_authored_fields_preserved': True, 'whitelist_rebuild_used': False, 'recorded_at': utc_now()}
    route_payload.update(_role_output_envelope_record(payload))
    write_json(route_root / 'flow.draft.json', route_payload)
    run_state['draft_route_visibility'] = {'route_id': route_id, 'route_version': int(route_payload['route_version']), 'draft_path': project_relative(project_root, route_root / 'flow.draft.json'), 'user_visible': False, 'reason': 'draft_routes_are_internal_until_pm_activates_reviewed_flow_json', 'recorded_at': utc_now()}

def _reset_route_review_after_route_draft_repair(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    for flag in ('process_officer_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'process_officer_route_check_passed', 'process_officer_route_repair_required', 'process_officer_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'product_officer_route_check_card_delivered', 'product_officer_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False

def _reset_route_hard_gate_approvals_for_recheck(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    for flag in ('pm_route_skeleton_card_delivered', 'route_draft_written_by_pm', 'process_officer_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'process_officer_route_check_passed', 'process_officer_route_repair_required', 'process_officer_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'product_officer_route_check_card_delivered', 'product_officer_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False

def _product_behavior_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'product_behavior_model.json'

def _product_behavior_model_compatibility_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'product_architecture_modelability.json'

def _require_product_behavior_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._product_behavior_model_report_path(run_root)
    if not path.exists():
        compatibility_path = router._product_behavior_model_compatibility_report_path(run_root)
        if compatibility_path.exists():
            path = compatibility_path
    if not path.exists():
        raise RouterError('route draft requires Product Officer product behavior model report')
    report = read_json(path)
    if report.get('passed') is not True:
        raise RouterError('route draft requires passed Product Officer product behavior model report')
    return path

def _route_process_check_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'route_process_check.json'

def _process_route_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'process_route_model.json'

def _require_process_route_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._process_route_model_report_path(run_root)
    if not path.exists():
        compatibility_path = router._route_process_check_path(run_root)
        if compatibility_path.exists():
            path = compatibility_path
    if not path.exists():
        raise RouterError('route activation requires process route model report')
    report = read_json(path)
    if report.get('passed') is not True or report.get('process_viability_verdict') != 'pass':
        raise RouterError('route activation requires Process Officer process route model pass')
    return path

def _route_product_check_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'route_product_check.json'

def _require_route_process_pass(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    return router._require_process_route_model_report(project_root, run_root)

def _supersede_active_current_node_packet_for_route_mutation(router: ModuleType, project_root: Path, run_root: Path, *, frontier: dict[str, Any], mutation_record: dict[str, Any]) -> None:
    _bind_router(router)
    ledger_path = run_root / 'packet_ledger.json'
    ledger = read_json_if_exists(ledger_path)
    packets = ledger.get('packets') if isinstance(ledger, dict) else []
    if not isinstance(packets, list):
        return
    active_packet_id = str(ledger.get('active_packet_id') or '').strip()
    active_node_id = str(frontier.get('active_node_id') or '').strip()
    if not active_packet_id and (not active_node_id):
        return
    superseded_at = utc_now()
    disposition = {'schema_version': 'flowpilot.route_mutation_packet_disposition.v1', 'status': 'superseded_by_route_mutation', 'route_id': frontier.get('active_route_id'), 'from_route_version': frontier.get('route_version'), 'candidate_route_version': mutation_record.get('route_version'), 'candidate_node_id': mutation_record.get('active_node_id'), 'topology_strategy': mutation_record.get('topology_strategy'), 'reason': mutation_record.get('reason') or 'route mutation replaces current node obligation', 'recorded_at': superseded_at}
    changed = False
    for record in packets:
        if not isinstance(record, dict):
            continue
        packet_id = str(record.get('packet_id') or '').strip()
        node_id = str(record.get('node_id') or record.get('current_node_id') or '').strip()
        status = str(record.get('active_packet_status') or record.get('status') or '').strip()
        if not router._packet_status_allows_current_work(status):
            continue
        if packet_id != active_packet_id and node_id != active_node_id:
            continue
        record['status'] = 'superseded'
        record['active_packet_status'] = 'superseded'
        record['active_packet_holder'] = 'controller'
        record['router_reconciliation_status'] = 'superseded_by_route_mutation'
        record['route_mutation_disposition'] = disposition
        changed = True
    if not changed:
        return
    ledger['active_packet_status'] = 'superseded'
    ledger['active_packet_holder'] = 'controller'
    ledger['route_mutation_packet_disposition'] = disposition
    ledger['updated_at'] = superseded_at
    write_json(ledger_path, ledger)

def _require_route_product_pass(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._route_product_check_path(run_root)
    if not path.exists():
        raise RouterError('route activation requires route_product_check.json')
    report = read_json(path)
    if report.get('passed') is not True or report.get('route_model_review_verdict') != 'pass':
        raise RouterError('route activation requires passed product-model route review')
    return path

def _current_route_draft_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    route_root = run_root / 'routes'
    candidates = sorted(route_root.glob('*/flow.draft.json')) if route_root.exists() else []
    if not candidates:
        raise RouterError('route check requires a route draft')
    if len(candidates) > 1:
        raise RouterError('route check requires an unambiguous current route draft')
    return candidates[0]

__all__ = (
    '_event_markers',
    '_route_node_history',
    '_refresh_route_memory',
    '_require_pm_prior_path_context',
    '_pm_context_action_extra',
    '_card_required_source_paths',
    '_card_delivery_phase',
    '_live_card_delivery_context',
    '_matching_controller_delivery_actions',
    '_controller_delivery_fact_for_pending_return',
    '_write_route_draft',
    '_reset_route_review_after_route_draft_repair',
    '_reset_route_hard_gate_approvals_for_recheck',
    '_product_behavior_model_report_path',
    '_product_behavior_model_compatibility_report_path',
    '_require_product_behavior_model_report',
    '_route_process_check_path',
    '_process_route_model_report_path',
    '_require_process_route_model_report',
    '_route_product_check_path',
    '_require_route_process_pass',
    '_supersede_active_current_node_packet_for_route_mutation',
    '_require_route_product_pass',
    '_current_route_draft_path',
)

_LOCAL_NAMES = set(globals())
