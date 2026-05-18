"""Cohesive child helpers for FlowPilot route-frontier compatibility facades."""

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


__all__ = (
    '_event_markers',
    '_route_node_history',
    '_refresh_route_memory',
    '_require_pm_prior_path_context',
    '_pm_context_action_extra',
)

_LOCAL_NAMES = set(globals())
