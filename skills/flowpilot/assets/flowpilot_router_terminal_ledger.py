"""Coarse terminal ledger owner helpers for the FlowPilot router.

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

def _terminal_summary_index_entry(router: ModuleType, project_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json')
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    run_id = run_state.get('run_id')
    for item in runs:
        if isinstance(item, dict) and item.get('run_id') == run_id:
            return item
    return None

def _terminal_summary_written(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> bool:
    _bind_router(router)
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    if not markdown_path.exists() or not json_path.exists():
        return False
    try:
        summary_markdown = markdown_path.read_text(encoding='utf-8')
        summary_record = read_json(json_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, RouterError):
        return False
    if not summary_markdown.startswith(TERMINAL_SUMMARY_ATTRIBUTION):
        return False
    if summary_record.get('schema_version') != TERMINAL_SUMMARY_SCHEMA:
        return False
    if summary_record.get('run_id') != run_state.get('run_id'):
        return False
    if summary_record.get('run_lifecycle_status') != _terminal_lifecycle_mode(run_state):
        return False
    summary_hash = _terminal_summary_hash(summary_markdown)
    if summary_record.get('summary_sha256') != summary_hash:
        return False
    if summary_record.get('flowpilot_project_url') != FLOWPILOT_PROJECT_URL:
        return False
    entry = router._terminal_summary_index_entry(project_root, run_state)
    if not isinstance(entry, dict):
        return False
    return entry.get('final_summary_path') == project_relative(project_root, markdown_path) and entry.get('final_summary_json_path') == project_relative(project_root, json_path) and (entry.get('flowpilot_project_url') == FLOWPILOT_PROJECT_URL)

def _terminal_summary_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path, *, mode: str) -> dict[str, Any]:
    _bind_router(router)
    run_root_rel = project_relative(project_root, run_root)
    markdown_rel = project_relative(project_root, _terminal_summary_markdown_path(run_root))
    json_rel = project_relative(project_root, _terminal_summary_json_path(run_root))
    index_rel = project_relative(project_root, project_root / '.flowpilot' / 'index.json')
    state_rel = project_relative(project_root, router.run_state_path(run_root))
    current_rel = project_relative(project_root, project_root / '.flowpilot' / 'current.json')
    lifecycle_rel = project_relative(project_root, _lifecycle_record_path(run_root))
    return make_action(action_type='write_terminal_summary', actor='controller', label=f'controller_writes_terminal_summary_for_{mode}', summary='The run is terminal. Read all files under the current run root, write a short final summary with FlowPilot GitHub attribution, show the same summary to the user, then stop route work.', allowed_reads=[f'{run_root_rel}/**', lifecycle_rel, state_rel, current_rel, index_rel], allowed_writes=[markdown_rel, json_rel, index_rel, current_rel, state_rel], extra={'run_lifecycle_status': mode, 'terminal_for_route': True, 'summary_schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'summary_markdown_path': markdown_rel, 'summary_json_path': json_rel, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'required_attribution_line': TERMINAL_SUMMARY_ATTRIBUTION, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'controller_may_read_all_current_run_files': True, 'sealed_body_reads_allowed': True, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'controller_may_approve_or_reopen_gates': False, 'controller_may_create_project_evidence': False, 'final_user_report_is_completion_authority': False, 'report_after_lifecycle_terminal': True, 'requires_payload': True, 'payload_contract': _terminal_summary_payload_contract(), 'postcondition': 'terminal_summary_written', 'allowed_external_events': ['user_requests_run_stop', 'user_requests_run_cancel']})

def _validate_terminal_summary_payload(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> tuple[str, dict[str, Any]]:
    _bind_router(router)
    if not isinstance(payload, dict):
        raise RouterError('write_terminal_summary requires payload')
    summary_markdown = payload.get('summary_markdown')
    if not isinstance(summary_markdown, str) or not summary_markdown.strip():
        raise RouterError('write_terminal_summary requires non-empty payload.summary_markdown')
    if not summary_markdown.startswith(TERMINAL_SUMMARY_ATTRIBUTION):
        raise RouterError('final summary markdown must start with the FlowPilot GitHub attribution line')
    if payload.get('displayed_to_user') is not True:
        raise RouterError('write_terminal_summary requires displayed_to_user=true after showing the summary to the user')
    summary_hash = _terminal_summary_hash(summary_markdown)
    if payload.get('displayed_summary_sha256') != summary_hash:
        raise RouterError('displayed_summary_sha256 must equal sha256(summary_markdown)')
    if payload.get('read_scope_used') != TERMINAL_SUMMARY_READ_SCOPE:
        raise RouterError(f'write_terminal_summary requires read_scope_used={TERMINAL_SUMMARY_READ_SCOPE}')
    source_paths: list[str] = []
    raw_source_paths = payload.get('source_paths_reviewed')
    if raw_source_paths is not None:
        if not isinstance(raw_source_paths, list):
            raise RouterError('source_paths_reviewed must be a list when supplied')
        for raw in raw_source_paths:
            if not isinstance(raw, str) or not raw.strip():
                raise RouterError('source_paths_reviewed entries must be non-empty strings')
            source_path = resolve_project_path(project_root, raw.strip())
            if not _path_is_inside(source_path, run_root):
                raise RouterError('source_paths_reviewed may cite only files inside the current run root')
            source_paths.append(project_relative(project_root, source_path))
    written_at = utc_now()
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    final_user_report = flowpilot_runtime_closure.final_user_report_record(run_id=str(run_state.get('run_id') or ''), lifecycle_status=mode, summary_path=project_relative(project_root, markdown_path), summary_json_path=project_relative(project_root, json_path), summary_sha256=summary_hash, displayed_to_user=True, written_at=written_at)
    final_report_issues = flowpilot_runtime_closure.validate_final_user_report_record(final_user_report)
    if final_report_issues:
        raise RouterError(f'final user report invariant failed: {final_report_issues}')
    record = {'schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'run_id': run_state.get('run_id'), 'run_lifecycle_status': mode, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'attribution_line': TERMINAL_SUMMARY_ATTRIBUTION, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'controller_read_scope_authorized': True, 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'controller_may_approve_or_reopen_gates': False, 'summary_markdown_path': project_relative(project_root, markdown_path), 'summary_json_path': project_relative(project_root, json_path), 'summary_sha256': summary_hash, 'displayed_to_user': True, 'displayed_summary_sha256': summary_hash, 'source_paths_reviewed': source_paths, 'final_user_report': final_user_report, 'written_at': written_at}
    return (summary_markdown, record)

def _write_terminal_summary(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any] | None, *, mode: str) -> dict[str, Any]:
    _bind_router(router)
    summary_markdown, record = router._validate_terminal_summary_payload(project_root, run_root, run_state, payload, mode=mode)
    markdown_path = _terminal_summary_markdown_path(run_root)
    json_path = _terminal_summary_json_path(run_root)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(summary_markdown, encoding='utf-8')
    write_json(json_path, record)
    now = str(record['written_at'])
    markdown_rel = project_relative(project_root, markdown_path)
    json_rel = project_relative(project_root, json_path)
    index_path = project_root / '.flowpilot' / 'index.json'
    index = read_json_if_exists(index_path) or {'schema_version': 'flowpilot.index.v1', 'runs': []}
    runs = index.setdefault('runs', [])
    run_id = run_state.get('run_id')
    entry = None
    for item in runs:
        if isinstance(item, dict) and item.get('run_id') == run_id:
            entry = item
            break
    if entry is None:
        entry = {'run_id': run_id, 'run_root': project_relative(project_root, run_root), 'created_at': run_state.get('created_at') or now}
        runs.append(entry)
    entry['status'] = mode
    entry['updated_at'] = now
    entry['final_summary_path'] = markdown_rel
    entry['final_summary_json_path'] = json_rel
    entry['final_summary_sha256'] = record['summary_sha256']
    entry['final_user_report_schema_version'] = FINAL_USER_REPORT_SCHEMA
    entry['final_user_report_is_completion_authority'] = False
    entry['flowpilot_project_url'] = FLOWPILOT_PROJECT_URL
    index['current_run_id'] = run_id
    index['updated_at'] = now
    write_json(index_path, index)
    current_path = project_root / '.flowpilot' / 'current.json'
    current = read_json_if_exists(current_path) or {}
    if current.get('current_run_id') == run_id:
        current['status'] = mode
        current['final_summary_path'] = markdown_rel
        current['final_summary_json_path'] = json_rel
        current['final_user_report_schema_version'] = FINAL_USER_REPORT_SCHEMA
        current['final_user_report_is_completion_authority'] = False
        current['flowpilot_project_url'] = FLOWPILOT_PROJECT_URL
        current['updated_at'] = now
        write_json(current_path, current)
    flags = run_state.setdefault('flags', {})
    flags['terminal_summary_card_delivered'] = True
    flags['terminal_summary_written'] = True
    run_state['terminal_summary'] = {'schema_version': TERMINAL_SUMMARY_SCHEMA, 'final_user_report_schema_version': FINAL_USER_REPORT_SCHEMA, 'path': markdown_rel, 'json_path': json_rel, 'sha256': record['summary_sha256'], 'displayed_to_user': True, 'read_scope': TERMINAL_SUMMARY_READ_SCOPE, 'flowpilot_project_url': FLOWPILOT_PROJECT_URL, 'written_at': now}
    run_state['final_user_report'] = record['final_user_report']
    return record

def _terminal_closure_suite_is_closed(router: ModuleType, run_root: Path) -> bool:
    _bind_router(router)
    closure = read_json_if_exists(run_root / 'closure' / 'terminal_closure_suite.json')
    frontier = read_json_if_exists(run_root / 'execution_frontier.json')
    if not isinstance(closure, dict) or not isinstance(frontier, dict):
        return False
    return closure.get('status') == 'closed' and frontier.get('status') == 'closed'

def _root_requirement_ids(router: ModuleType, contract: dict[str, Any]) -> list[str]:
    _bind_router(router)
    ids = []
    for item in contract.get('root_requirements') or []:
        if isinstance(item, dict) and item.get('requirement_id'):
            ids.append(str(item['requirement_id']))
    return ids

def _string_list(router: ModuleType, value: Any) -> list[str]:
    _bind_router(router)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item or '').strip()]

def _route_nodes_with_requirement_trace(router: ModuleType, nodes: Any, root_requirement_ids: list[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    traced_nodes: list[dict[str, Any]] = []
    if not isinstance(nodes, list):
        return traced_nodes
    for index, item in enumerate(nodes, start=1):
        if not isinstance(item, dict):
            continue
        node = dict(item)
        node_id = str(node.get('node_id') or node.get('id') or f'node-{index:03d}')
        node.setdefault('node_id', node_id)
        node.setdefault('covers_requirement_ids', root_requirement_ids)
        node.setdefault('covers_scenario_ids', [])
        node.setdefault('source_product_capability_ids', [])
        node.setdefault('why_this_node_exists', f'Node {node_id} owns mapped FlowPilot requirements or route proof obligations.')
        node.setdefault('why_not_merged', 'PM preserves this node while it owns distinct evidence, role authority, failure isolation, recovery, or user-visible milestone value.')
        node.setdefault('why_not_split', 'PM splits this node only when a child boundary adds distinct proof, role authority, recovery, or user-visible milestone value.')
        traced_nodes.append(node)
    return traced_nodes

def _node_acceptance_traceability_issues(router: ModuleType, payload: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    trace = payload.get('requirement_traceability') if isinstance(payload.get('requirement_traceability'), dict) else {}
    if not trace:
        issues.append(_artifact_issue('requirement_traceability', 'missing node requirement traceability object', 'project_manager'))
        return issues
    for field in ('source_route_node_id', 'source_route_node_covers_requirement_ids', 'full_protocol_required_when_flowpilot_invoked', 'all_covered_requirements_must_close_or_be_triaged', 'closure_by_report_only_forbidden'):
        if trace.get(field) in (None, '', []):
            issues.append(_artifact_issue(f'requirement_traceability.{field}', 'missing required traceability field', 'project_manager'))
    if trace.get('full_protocol_required_when_flowpilot_invoked') is not True:
        issues.append(_artifact_issue('requirement_traceability.full_protocol_required_when_flowpilot_invoked', 'FlowPilot formal node plan must keep full protocol', 'project_manager'))
    if trace.get('closure_by_report_only_forbidden') is not True:
        issues.append(_artifact_issue('requirement_traceability.closure_by_report_only_forbidden', 'covered requirements cannot close by report-only evidence', 'project_manager'))
    node_requirements = payload.get('node_requirements')
    if isinstance(node_requirements, list):
        for index, item in enumerate(node_requirements, start=1):
            if isinstance(item, dict) and (not (router._string_list(item.get('source_requirement_ids')) or router._string_list(item.get('covers_root_requirement_ids')))):
                issues.append(_artifact_issue(f'node_requirements[{index}].source_requirement_ids', 'node requirement must map to source/root requirement ids', 'project_manager'))
    experiments = payload.get('experiment_plan')
    if isinstance(experiments, list):
        for index, item in enumerate(experiments, start=1):
            if isinstance(item, dict) and (not (router._string_list(item.get('covers_requirements')) or router._string_list(item.get('covers_root_requirement_ids')))):
                issues.append(_artifact_issue(f'experiment_plan[{index}].covers_requirements', 'experiment must name covered requirement ids', 'project_manager'))
    advance_gate = payload.get('advance_gate') if isinstance(payload.get('advance_gate'), dict) else {}
    if 'all_covered_requirements_closed_or_triaged' not in advance_gate:
        issues.append(_artifact_issue('advance_gate.all_covered_requirements_closed_or_triaged', 'advance gate must track covered requirement closure', 'project_manager'))
    return issues

def _requirement_trace_closure_from_root_replay(router: ModuleType, contract: dict[str, Any], root_replay: list[dict[str, Any]]) -> list[dict[str, Any]]:
    _bind_router(router)
    requirements_by_id = {str(item.get('requirement_id')): item for item in contract.get('root_requirements') or [] if isinstance(item, dict) and item.get('requirement_id')}
    closure: list[dict[str, Any]] = []
    for replay in root_replay:
        requirement_id = str(replay.get('requirement_id') or '')
        requirement = requirements_by_id.get(requirement_id, {})
        closure.append({'requirement_id': requirement_id, 'source_requirement_ids': router._string_list(requirement.get('source_requirement_ids')) or [requirement_id], 'change_status': str(requirement.get('change_status') or 'UNCHANGED'), 'status': 'resolved', 'owner_node_ids': router._string_list(replay.get('owner_node_ids')), 'covering_entry_ids': [f'root_contract:{requirement_id}'], 'evidence_paths': replay.get('evidence_paths') or [], 'direct_evidence_required': True, 'direct_evidence_checked': True, 'standard_scenario_ids': replay.get('standard_scenarios') or replay.get('standard_scenario_ids') or [], 'stale_evidence_refs': [], 'superseded_by_requirement_ids': router._string_list(requirement.get('superseded_by_requirement_ids')), 'waiver_authority': None, 'unresolved_reason': None})
    return closure

def _final_ledger_traceability_issues(router: ModuleType, payload: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    closure = payload.get('requirement_trace_closure')
    if not isinstance(closure, list) or not closure:
        issues.append(_artifact_issue('requirement_trace_closure', 'final ledger requires requirement trace closure rows', 'project_manager'))
        return issues
    for index, item in enumerate(closure, start=1):
        if not isinstance(item, dict):
            issues.append(_artifact_issue(f'requirement_trace_closure[{index}]', 'closure row must be an object', 'project_manager'))
            continue
        if not item.get('requirement_id'):
            issues.append(_artifact_issue(f'requirement_trace_closure[{index}].requirement_id', 'missing requirement id', 'project_manager'))
        if item.get('status') not in {'resolved', 'superseded', 'waived'}:
            issues.append(_artifact_issue(f'requirement_trace_closure[{index}].status', 'effective requirement must be resolved, superseded, or waived', 'project_manager'))
        if item.get('status') == 'resolved' and (not item.get('evidence_paths') or item.get('direct_evidence_checked') is not True):
            issues.append(_artifact_issue(f'requirement_trace_closure[{index}].evidence_paths', 'resolved requirement needs direct checked evidence', 'project_manager'))
        if item.get('status') == 'waived' and (not item.get('waiver_authority')):
            issues.append(_artifact_issue(f'requirement_trace_closure[{index}].waiver_authority', 'waived requirement needs waiver authority', 'project_manager'))
    counts = payload.get('counts') if isinstance(payload.get('counts'), dict) else {}
    if int(counts.get('unresolved_requirement_count', 0) or 0) != 0:
        issues.append(_artifact_issue('counts.unresolved_requirement_count', 'final ledger requires unresolved_requirement_count=0', 'project_manager'))
    integrity = payload.get('evidence_integrity') if isinstance(payload.get('evidence_integrity'), dict) else {}
    for field in ('requirement_trace_checked', 'every_effective_requirement_closure_row_present', 'requirement_direct_evidence_checked', 'requirement_waiver_authority_checked', 'requirement_stale_status_checked'):
        if integrity.get(field) is not True:
            issues.append(_artifact_issue(f'evidence_integrity.{field}', 'final ledger traceability integrity field must be true', 'project_manager'))
    return issues

def _validated_root_replay(router: ModuleType, payload: dict[str, Any], required_ids: list[str]) -> list[dict[str, Any]]:
    _bind_router(router)
    replay = payload.get('root_contract_replay')
    if not isinstance(replay, list) or not replay:
        raise RouterError('final ledger requires root_contract_replay for every frozen root requirement')
    by_id = {str(item.get('requirement_id')): item for item in replay if isinstance(item, dict)}
    missing = [req_id for req_id in required_ids if req_id not in by_id]
    if missing:
        raise RouterError(f"final ledger missing root contract replay for: {', '.join(missing)}")
    failed = [req_id for req_id in required_ids if by_id[req_id].get('status') != 'approved' or not by_id[req_id].get('evidence_paths')]
    if failed:
        raise RouterError(f"final ledger root contract replay not approved with evidence for: {', '.join(failed)}")
    return [by_id[req_id] for req_id in required_ids]

def _build_source_of_truth_final_entries(router: ModuleType, project_root: Path, run_root: Path, frontier: dict[str, Any], route: dict[str, Any], mutations: dict[str, Any], contract: dict[str, Any], root_replay: list[dict[str, Any]], child_manifest: dict[str, Any], evidence_ledger: dict[str, Any], generated_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    _bind_router(router)
    route_id = str(frontier['active_route_id'])
    route_version = int(frontier.get('route_version') or 0)
    entries: list[dict[str, Any]] = []
    for replay in root_replay:
        entries.append({'entry_id': f"root_contract:{replay['requirement_id']}", 'route_version': route_version, 'gate_family': 'root_acceptance', 'covers_requirement_ids': [str(replay['requirement_id'])], 'covers_scenario_ids': replay.get('standard_scenarios') or replay.get('standard_scenario_ids') or [], 'required_approver': 'human_like_reviewer', 'status': 'approved', 'source_of_truth_paths': replay.get('evidence_paths') or [], 'evidence_paths': replay.get('evidence_paths') or []})
    for node in router._effective_route_nodes(route, mutations):
        node_id = str(node['node_id'])
        node_root = run_root / 'routes' / route_id / 'nodes' / node_id
        entries.append({'entry_id': f'{route_id}:{node_id}', 'route_version': route_version, 'node_id': node_id, 'gate_family': 'route_node', 'covers_requirement_ids': router._string_list(node.get('covers_requirement_ids')), 'covers_scenario_ids': router._string_list(node.get('covers_scenario_ids')), 'required_approver': 'project_manager', 'status': 'approved' if node_id in (frontier.get('completed_nodes') or []) or node_id == frontier.get('active_node_id') else 'pending_review', 'source_of_truth_paths': [project_relative(project_root, path) for path in (node_root / 'node_acceptance_plan.json', node_root / 'reviews' / 'node_acceptance_plan_review.json', node_root / 'node_completion_ledger.json', node_root / 'parent_backward_replay.json', node_root / 'pm_parent_segment_decision.json') if path.exists()]})
        entries[-1]['evidence_paths'] = list(entries[-1]['source_of_truth_paths'])
    for item in mutations.get('items') or []:
        if not isinstance(item, dict):
            continue
        for node_id in router._route_mutation_superseded_nodes(item):
            entries.append({'entry_id': f'superseded:{node_id}', 'route_version': item.get('route_version', route_version), 'node_id': str(node_id), 'gate_family': 'superseded_node', 'required_approver': 'project_manager', 'status': 'superseded_explained', 'source_of_truth_paths': [project_relative(project_root, run_root / 'routes' / route_id / 'mutations.json')], 'evidence_paths': [project_relative(project_root, run_root / 'routes' / route_id / 'mutations.json')]})
    for skill in child_manifest.get('selected_skills') or []:
        if not isinstance(skill, dict):
            continue
        skill_name = str(skill.get('skill_name') or skill.get('name') or 'child_skill')
        for gate in skill.get('gates') or []:
            if not isinstance(gate, dict):
                continue
            entries.append({'entry_id': f"child_skill:{skill_name}:{gate.get('gate_id') or len(entries)}", 'route_version': route_version, 'gate_family': 'child_skill_gate', 'required_approver': gate.get('required_approver') or 'project_manager', 'status': 'approved', 'source_of_truth_paths': [project_relative(project_root, run_root / 'child_skill_gate_manifest.json')], 'evidence_paths': [project_relative(project_root, run_root / 'child_skill_gate_manifest.json')]})
    for item in evidence_ledger.get('items') or []:
        if isinstance(item, dict) and item.get('evidence_id'):
            entries.append({'entry_id': f"evidence:{item['evidence_id']}", 'route_version': route_version, 'gate_family': 'evidence_integrity', 'required_approver': 'human_like_reviewer', 'status': item.get('status') or 'current', 'source_of_truth_paths': [item.get('path')] if item.get('path') else [], 'evidence_paths': [item.get('path')] if item.get('path') else []})
    for resource in generated_ledger.get('resources') or []:
        if isinstance(resource, dict) and (resource.get('resource_id') or resource.get('path')):
            entries.append({'entry_id': f"generated_resource:{resource.get('resource_id') or resource.get('path')}", 'route_version': route_version, 'gate_family': 'generated_resource_lineage', 'required_approver': 'project_manager', 'status': resource.get('disposition') or 'resolved', 'source_of_truth_paths': [resource.get('path')] if resource.get('path') else [], 'evidence_paths': [resource.get('path')] if resource.get('path') else []})
    if not entries:
        raise RouterError('final ledger source-of-truth scan produced no entries')
    return entries

def _route_mutation_completion_issues(router: ModuleType, frontier: dict[str, Any], mutations: dict[str, Any]) -> list[str]:
    _bind_router(router)
    issues: list[str] = []
    if frontier.get('status') == 'route_mutation_pending_recheck':
        pending = frontier.get('pending_route_mutation') or {}
        candidate = pending.get('candidate_node_id') or 'unknown candidate'
        issues.append(f'route mutation pending recheck for {candidate}')
    completed = {str(item) for item in frontier.get('completed_nodes') or []}
    active_node_id = str(frontier.get('active_node_id') or '')
    for item in mutations.get('items') or []:
        if not isinstance(item, dict):
            continue
        restart_policy = item.get('repair_restart_policy') or {}
        if restart_policy.get('same_scope_replay_rerun_required') is not True:
            continue
        mutation_node_id = str(item.get('active_node_id') or '')
        if not mutation_node_id:
            issues.append(f"route mutation {item.get('route_version', 'unknown')} lacks active mutation node")
            continue
        if mutation_node_id not in completed:
            if mutation_node_id == active_node_id:
                issues.append(f'route mutation node {mutation_node_id} is active but not completed')
            else:
                issues.append(f'route mutation node {mutation_node_id} is not completed after replacement')
    return issues

def _write_final_route_wide_ledger(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose='final route-wide ledger')
    if payload.get('pm_owned', True) is not True:
        raise RouterError('final route-wide ledger must be PM-owned')
    frontier = router._active_frontier(run_root)
    route_id = str(frontier['active_route_id'])
    mutations = read_json_if_exists(run_root / 'routes' / route_id / 'mutations.json')
    mutation_issues = router._route_mutation_completion_issues(frontier, mutations)
    if mutation_issues:
        raise RouterError('final ledger requires completed route mutation replay: ' + '; '.join(mutation_issues[:5]))
    required_paths = [run_root / 'evidence' / 'evidence_ledger.json', run_root / 'generated_resource_ledger.json', run_root / 'quality' / 'quality_package.json', run_root / 'reviews' / 'evidence_quality_review.json', run_root / 'execution_frontier.json', run_root / 'root_acceptance_contract.json', run_root / 'child_skill_gate_manifest.json']
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"final ledger requires evidence quality package and review: {', '.join(missing)}")
    if not run_state['flags'].get('evidence_quality_reviewer_passed'):
        raise RouterError('final ledger requires reviewer-passed evidence quality package')
    evidence_ledger = read_json(run_root / 'evidence' / 'evidence_ledger.json')
    generated_ledger = read_json(run_root / 'generated_resource_ledger.json')
    quality_package = read_json(run_root / 'quality' / 'quality_package.json')
    contract = read_json(run_root / 'root_acceptance_contract.json')
    if contract.get('status') != 'frozen':
        raise RouterError('final ledger requires frozen root acceptance contract')
    child_manifest = read_json(run_root / 'child_skill_gate_manifest.json')
    route_version = int(frontier.get('route_version') or 0)
    node_completion_ledger_path = _active_node_completion_ledger_path(run_root, frontier)
    if not run_state['flags'].get('node_completion_ledger_updated') or not node_completion_ledger_path.exists():
        raise RouterError('final ledger requires node completion ledger')
    evidence_unresolved_count = int(evidence_ledger.get('unresolved_count', 0) or 0)
    payload_unresolved_count = int(payload.get('unresolved_count', 0) or 0)
    unresolved_count = max(evidence_unresolved_count, payload_unresolved_count)
    unresolved_resource_count = int(payload.get('unresolved_resource_count', generated_ledger.get('unresolved_resource_count', 0) or 0))
    pending_resource_count = int(generated_ledger.get('pending_resource_count', 0) or 0)
    unresolved_residual_risk_count = int(payload.get('unresolved_residual_risk_count', 0))
    stale_count = int(payload.get('stale_count', evidence_ledger.get('stale_count', 0) or 0))
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status['clean']:
        first_issue = pm_suggestion_status['issues'][0]['message'] if pm_suggestion_status['issues'] else 'unknown issue'
        raise RouterError(f'final ledger requires clean PM suggestion ledger: {first_issue}')
    self_interrogation_status = _require_clean_self_interrogation(project_root, run_root, gate_name='final route-wide ledger')
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, run_state)
    if not closure_reconciliation['clean']:
        raise RouterError('final ledger requires clean terminal closure reconciliation: ' + router._closure_reconciliation_blocker_message(closure_reconciliation))
    if unresolved_count != 0:
        raise RouterError('final ledger requires unresolved_count=0')
    if unresolved_resource_count != 0:
        raise RouterError('final ledger requires unresolved_resource_count=0')
    if pending_resource_count != 0:
        raise RouterError('final ledger requires generated resources to have terminal dispositions')
    if unresolved_residual_risk_count != 0:
        raise RouterError('final ledger requires unresolved_residual_risk_count=0')
    if stale_count != 0:
        raise RouterError('final ledger cannot include stale current evidence')
    if quality_package.get('quality_checks', {}).get('completion_report_only_allowed') is not False:
        raise RouterError('final ledger forbids completion report-only closure')
    route_path = router._active_route_path(run_root, frontier)
    route = read_json(route_path)
    root_replay = router._validated_root_replay(payload, router._root_requirement_ids(contract))
    requirement_trace_closure = router._requirement_trace_closure_from_root_replay(contract, root_replay)
    effective_requirement_count = len(requirement_trace_closure)
    resolved_requirement_count = sum((1 for item in requirement_trace_closure if item.get('status') == 'resolved'))
    superseded_requirement_count = sum((1 for item in requirement_trace_closure if item.get('status') == 'superseded'))
    waived_requirement_count = sum((1 for item in requirement_trace_closure if item.get('status') == 'waived'))
    unresolved_requirement_count = sum((1 for item in requirement_trace_closure if item.get('status') not in {'resolved', 'superseded', 'waived'}))
    entries = router._build_source_of_truth_final_entries(project_root, run_root, frontier, route, mutations, contract, root_replay, child_manifest, evidence_ledger, generated_ledger)
    entries.extend(router._closure_reconciliation_entries(project_root, closure_reconciliation, route_version=route_version))
    bad_entry_statuses = [str(entry.get('entry_id')) for entry in entries if entry.get('status') in {'pending', 'pending_review', 'blocked', 'unresolved', 'stale'}]
    if bad_entry_statuses:
        raise RouterError(f"final ledger has unresolved source-of-truth entries: {', '.join(bad_entry_statuses)}")
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_map_path = run_root / 'terminal_human_backward_replay_map.json'
    terminal_segments = [{'segment_id': str(entry['entry_id']), 'source_entry_id': str(entry['entry_id']), 'gate_family': entry.get('gate_family'), 'requirement_trace_closure_refs': entry.get('covers_requirement_ids') or [], 'status': 'not_reviewed', 'requires_pm_segment_decision': True} for entry in entries]
    gate_decision_ledger_path = run_root / 'gate_decisions' / 'gate_decision_ledger.json'
    gate_decisions = list(run_state.get('gate_decisions') or [])
    ledger = {'schema_version': 'flowpilot.final_route_wide_gate_ledger.v1', 'run_id': run_state['run_id'], 'pm_owned': True, 'status': 'clean', 'built_from_route': route_id, 'built_from_route_version': route_version, 'built_at': utc_now(), 'source_paths': {'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'active_flow': project_relative(project_root, route_path), 'node_completion_ledger': project_relative(project_root, node_completion_ledger_path), 'evidence_ledger': project_relative(project_root, run_root / 'evidence' / 'evidence_ledger.json'), 'generated_resource_ledger': project_relative(project_root, run_root / 'generated_resource_ledger.json'), 'quality_package': project_relative(project_root, run_root / 'quality' / 'quality_package.json'), 'product_function_architecture': project_relative(project_root, run_root / 'product_function_architecture.json') if (run_root / 'product_function_architecture.json').exists() else None, 'root_acceptance_contract': project_relative(project_root, run_root / 'root_acceptance_contract.json'), 'standard_scenario_pack': project_relative(project_root, run_root / 'standard_scenario_pack.json') if (run_root / 'standard_scenario_pack.json').exists() else None, 'child_skill_gate_manifest': project_relative(project_root, run_root / 'child_skill_gate_manifest.json'), 'route_mutations': project_relative(project_root, run_root / 'routes' / route_id / 'mutations.json') if (run_root / 'routes' / route_id / 'mutations.json').exists() else None, 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root)), 'gate_decision_ledger': project_relative(project_root, gate_decision_ledger_path) if gate_decision_ledger_path.exists() else None, 'pm_suggestion_ledger': project_relative(project_root, _pm_suggestion_ledger_path(run_root)) if pm_suggestion_status['exists'] else None, 'self_interrogation_index': project_relative(project_root, _self_interrogation_index_path(run_root)) if self_interrogation_status['exists'] else None, 'defect_ledger': closure_reconciliation['defect_ledger']['path'], 'crew_memory': closure_reconciliation['role_memory']['path'], 'continuation_quarantine': closure_reconciliation['continuation_quarantine']['path']}, 'prior_path_context_review': prior_review, 'current_route_scanned': True, 'effective_nodes_resolved': True, 'gate_families': {'child_skill_gates_collected': True, 'human_review_gates_collected': True, 'parent_backward_replays_collected': True, 'product_process_gates_collected': True, 'generated_resource_lineage_collected': True, 'final_completion_gates_collected': True, 'gate_decisions_collected': True, 'pm_suggestions_disposed': True, 'self_interrogation_dispositions_collected': True, 'terminal_closure_reconciliation_collected': True}, 'evidence_integrity': {'generated_resource_lineage_resolved': True, 'stale_evidence_checked': True, 'superseded_nodes_explained': True, 'standard_scenarios_replayed': bool(payload.get('standard_scenarios_replayed', True)), 'residual_risk_triage_done': True, 'unresolved_residual_risk_count_zero': True, 'blocked_items_have_pm_repair_or_stop_decision': True, 'requirement_trace_checked': True, 'every_effective_requirement_closure_row_present': True, 'requirement_direct_evidence_checked': True, 'requirement_waiver_authority_checked': True, 'requirement_stale_status_checked': True, 'self_interrogation_index_clean': True, 'defect_ledger_reconciled': closure_reconciliation['defect_ledger']['clean'], 'role_memory_reconciled': closure_reconciliation['role_memory']['clean'], 'continuation_quarantine_reconciled': closure_reconciliation['continuation_quarantine']['clean'], 'terminal_closure_reconciliation_clean': closure_reconciliation['clean']}, 'counts': {'effective_node_count': len(router._effective_route_nodes(route, mutations)), 'effective_requirement_count': effective_requirement_count, 'resolved_requirement_count': resolved_requirement_count, 'superseded_requirement_count': superseded_requirement_count, 'waived_requirement_count': waived_requirement_count, 'unresolved_requirement_count': unresolved_requirement_count, 'gate_count': len(entries), 'stale_count': stale_count, 'generated_resource_count': int(generated_ledger.get('resource_count', 0) or 0), 'pending_resource_count': pending_resource_count, 'unresolved_resource_count': unresolved_resource_count, 'unresolved_residual_risk_count': unresolved_residual_risk_count, 'unresolved_count': unresolved_count, 'gate_decision_count': len(gate_decisions), 'pm_suggestion_count': pm_suggestion_status['entry_count'], 'pm_suggestion_issue_count': pm_suggestion_status['issue_count'], 'self_interrogation_record_count': self_interrogation_status['record_count'], 'self_interrogation_issue_count': self_interrogation_status['issue_count'], 'self_interrogation_unresolved_hard_finding_count': self_interrogation_status['unresolved_hard_finding_count'], 'defect_blocker_open_count': closure_reconciliation['defect_ledger']['blocker_open_count'], 'defect_fixed_pending_recheck_count': closure_reconciliation['defect_ledger']['fixed_pending_recheck_count'], 'role_memory_file_count': closure_reconciliation['role_memory']['file_count'], 'stale_role_memory_path_count': len(closure_reconciliation['role_memory']['stale_role_memory_paths']), 'imported_artifact_authority_count': closure_reconciliation['continuation_quarantine'].get('imported_artifact_authority_count', 0)}, 'entries': entries, 'gate_decisions': gate_decisions, 'terminal_closure_reconciliation': closure_reconciliation, 'root_contract_replay': root_replay, 'requirement_trace_closure': requirement_trace_closure, 'frozen_contract_replay': {'status': 'replayed', 'root_acceptance_contract_path': project_relative(project_root, run_root / 'root_acceptance_contract.json'), 'standard_scenario_pack_path': project_relative(project_root, run_root / 'standard_scenario_pack.json'), 'requirement_count': len(root_replay), 'standard_scenarios_replayed': bool(payload.get('standard_scenarios_replayed', True))}, 'terminal_human_backward_replay': {'required': True, 'status': 'ready_for_reviewer', 'review_map_path': project_relative(project_root, terminal_map_path), 'report_only_allowed': False}, 'completion_allowed': False}
    traceability_issues = router._final_ledger_traceability_issues(ledger)
    if traceability_issues:
        raise RouterError('final ledger traceability invalid: ' + '; '.join((str(issue['message']) for issue in traceability_issues[:5])))
    write_json(final_ledger_path, ledger)
    write_json(terminal_map_path, {'schema_version': 'flowpilot.terminal_human_backward_replay_map.v1', 'run_id': run_state['run_id'], 'route_id': route_id, 'route_version': route_version, 'pm_owned': True, 'status': 'ready_for_reviewer', 'built_from_ledger_path': project_relative(project_root, final_ledger_path), 'built_at': utc_now(), 'replay_order': ['delivered_product', 'root_acceptance', 'parent_or_module_nodes', 'leaf_nodes', 'pm_segment_decisions', 'repair_restart_policy'], 'segments': terminal_segments, 'coverage': {'effective_nodes_total': len(router._effective_route_nodes(route, mutations)), 'requirement_trace_closure_total': effective_requirement_count, 'segments_total': len(terminal_segments), 'segments_reviewed': 0, 'effective_nodes_reviewed_by_human': 0, 'root_acceptance_reviewed': False, 'parent_nodes_reviewed': False, 'leaf_nodes_reviewed': False, 'every_effective_node_has_pm_segment_decision': False}, 'repair_restart_policy': {'default_restart': 'restart_from_delivered_product', 'latest_repair_invalidates_affected_segments': True, 'latest_repair_requires_ledger_rebuild': True, 'latest_repair_requires_replay_rerun': True, 'latest_repair_requires_pm_reapproval': True}, 'completion_gate': {'reviewer_passed': False, 'pm_segment_decisions_recorded': False, 'repair_restart_policy_recorded': True, 'unresolved_repair_findings': 0, 'completion_allowed': False}})

def _write_terminal_backward_replay(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('reviewed_by_role') != 'human_like_reviewer':
        raise RouterError('terminal backward replay must be reviewed_by_role=human_like_reviewer')
    if payload.get('passed') is not True:
        raise RouterError('terminal backward replay must explicitly pass')
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_map_path = run_root / 'terminal_human_backward_replay_map.json'
    if not final_ledger_path.exists() or not terminal_map_path.exists():
        raise RouterError('terminal backward replay requires final ledger and PM replay map')
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get('pm_owned') is not True or final_ledger.get('status') != 'clean':
        raise RouterError('terminal replay requires a PM-owned clean final ledger')
    if final_ledger.get('counts', {}).get('unresolved_count') != 0:
        raise RouterError('terminal replay cannot pass unless final ledger unresolved_count is zero')
    terminal_map = read_json(terminal_map_path)
    if terminal_map.get('status') != 'ready_for_reviewer':
        raise RouterError('terminal replay map must be ready_for_reviewer')
    segments = terminal_map.get('segments') if isinstance(terminal_map.get('segments'), list) else []
    required_segment_ids = [str(segment.get('segment_id')) for segment in segments if isinstance(segment, dict) and segment.get('segment_id')]
    segment_reviews = payload.get('segment_reviews')
    if not isinstance(segment_reviews, list) or not segment_reviews:
        raise RouterError('terminal backward replay requires segment_reviews for every replay-map segment')
    reviews_by_id = {str(item.get('segment_id')): item for item in segment_reviews if isinstance(item, dict) and item.get('segment_id')}
    missing_segments = [segment_id for segment_id in required_segment_ids if segment_id not in reviews_by_id]
    if missing_segments:
        raise RouterError(f"terminal backward replay missing segment reviews: {', '.join(missing_segments)}")
    failed_segments = [segment_id for segment_id in required_segment_ids if reviews_by_id[segment_id].get('reviewed_by_role') != 'human_like_reviewer' or reviews_by_id[segment_id].get('passed') is not True or reviews_by_id[segment_id].get('pm_segment_decision') != 'continue']
    if failed_segments:
        raise RouterError(f"terminal replay segments require reviewer pass and PM continue: {', '.join(failed_segments)}")
    for segment in segments:
        if isinstance(segment, dict) and segment.get('segment_id'):
            review = reviews_by_id.get(str(segment['segment_id']))
            if review:
                segment['status'] = 'passed'
                segment['review'] = review
    terminal_map['status'] = 'passed'
    terminal_map.setdefault('coverage', {})
    terminal_map['coverage'].update({'effective_nodes_reviewed_by_human': int(terminal_map['coverage'].get('effective_nodes_total', 1) or 1), 'segments_reviewed': len(required_segment_ids), 'root_acceptance_reviewed': True, 'parent_nodes_reviewed': True, 'leaf_nodes_reviewed': True, 'every_effective_node_has_pm_segment_decision': True})
    terminal_map.setdefault('completion_gate', {})
    terminal_map['completion_gate'].update({'reviewer_passed': True, 'pm_segment_decisions_recorded': True, 'repair_restart_policy_recorded': True, 'unresolved_repair_findings': 0, 'completion_allowed': True})
    terminal_map['reviewed_by_role'] = 'human_like_reviewer'
    terminal_map['reviewed_at'] = utc_now()
    write_json(terminal_map_path, terminal_map)
    final_ledger.setdefault('terminal_human_backward_replay', {})
    final_ledger['terminal_human_backward_replay'].update({'status': 'passed', 'review_map_path': project_relative(project_root, terminal_map_path), 'report_only_allowed': False, 'segments_reviewed': len(required_segment_ids)})
    final_ledger['completion_allowed'] = True
    final_ledger['terminal_replay_review_path'] = project_relative(project_root, run_root / 'reviews' / 'terminal_backward_replay.json')
    final_ledger['terminal_replay_reviewed_at'] = utc_now()
    write_json(final_ledger_path, final_ledger)
    write_json(run_root / 'reviews' / 'terminal_backward_replay.json', {'schema_version': 'flowpilot.terminal_backward_replay_review.v1', 'run_id': run_state['run_id'], 'reviewed_by_role': 'human_like_reviewer', 'passed': True, 'source_paths': {'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_human_backward_replay_map': project_relative(project_root, terminal_map_path)}, 'segment_reviews': segment_reviews, 'report_only_allowed': False, 'reviewed_at': utc_now(), **_role_output_envelope_record(payload)})
    router._write_task_completion_projection(project_root, run_root, run_state, source_event='reviewer_final_backward_replay_passed')

def _write_task_completion_projection(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], *, source_event: str) -> Path:
    _bind_router(router)
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_replay_path = run_root / 'reviews' / 'terminal_backward_replay.json'
    frontier_path = run_root / 'execution_frontier.json'
    final_ledger = read_json(final_ledger_path)
    terminal_replay = read_json(terminal_replay_path)
    frontier = read_json(frontier_path)
    if final_ledger.get('completion_allowed') is not True:
        raise RouterError('task completion projection requires completion_allowed final ledger')
    if terminal_replay.get('passed') is not True:
        raise RouterError('task completion projection requires passed terminal backward replay')
    projection_path = _task_completion_projection_path(run_root)
    write_json(projection_path, {'schema_version': 'flowpilot.task_completion_projection.v1', 'run_id': run_state['run_id'], 'task_status': 'ready_for_pm_terminal_closure', 'projection_owner': 'controller', 'completion_fact_owner': 'project_manager', 'source_event': source_event, 'derived_from': 'active_route_state_frontier_and_ledger', 'controller_may_declare_completion': False, 'ui_or_chat_is_display_only': True, 'source_paths': {'execution_frontier': project_relative(project_root, frontier_path), 'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_backward_replay': project_relative(project_root, terminal_replay_path), 'latest_node_completion_ledger': str(frontier.get('latest_node_completion_ledger_path') or '')}, 'published_at': utc_now()})
    run_state['flags']['task_completion_projection_published'] = True
    return projection_path

def _write_terminal_closure_suite(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload(project_root, payload)
    if payload.get('approved_by_role', 'project_manager') != 'project_manager':
        raise RouterError('terminal closure must be approved_by_role=project_manager')
    decision = str(payload.get('decision') or '')
    if decision not in PM_TERMINAL_CLOSURE_DECISION_ALLOWED_VALUES:
        raise RouterError('terminal closure requires decision=approve_terminal_closure')
    prior_review = router._require_pm_prior_path_context(project_root, run_root, payload, purpose='terminal closure')
    final_ledger_path = run_root / 'final_route_wide_gate_ledger.json'
    terminal_replay_path = run_root / 'reviews' / 'terminal_backward_replay.json'
    task_projection_path = _task_completion_projection_path(run_root)
    continuation_path = router._continuation_binding_path(run_root)
    required_paths = [final_ledger_path, terminal_replay_path, task_projection_path, run_root / 'execution_frontier.json', run_root / 'crew_ledger.json', continuation_path]
    missing = [project_relative(project_root, path) for path in required_paths if not path.exists()]
    if missing:
        raise RouterError(f"terminal closure missing lifecycle paths: {', '.join(missing)}")
    final_ledger = read_json(final_ledger_path)
    if final_ledger.get('completion_allowed') is not True:
        raise RouterError('terminal closure requires completion_allowed final ledger')
    replay = read_json(terminal_replay_path)
    if replay.get('passed') is not True:
        raise RouterError('terminal closure requires passed terminal backward replay')
    task_projection = read_json(task_projection_path)
    if task_projection.get('task_status') != 'ready_for_pm_terminal_closure':
        raise RouterError('terminal closure requires task completion projection')
    pm_suggestion_status = _pm_suggestion_ledger_status(run_root)
    if not pm_suggestion_status['clean']:
        first_issue = pm_suggestion_status['issues'][0]['message'] if pm_suggestion_status['issues'] else 'unknown issue'
        raise RouterError(f'terminal closure requires clean PM suggestion ledger: {first_issue}')
    self_interrogation_status = _require_clean_self_interrogation(project_root, run_root, gate_name='terminal closure')
    closure_reconciliation = router._terminal_closure_reconciliation_status(project_root, run_root, run_state)
    if not closure_reconciliation['clean']:
        raise RouterError('terminal closure requires clean reconciliation ledgers: ' + router._closure_reconciliation_blocker_message(closure_reconciliation))
    unresolved_role_work = router._unresolved_pm_role_work_requests(run_root, run_state)
    if unresolved_role_work:
        request_ids = ', '.join((str(item.get('request_id')) for item in unresolved_role_work[:5]))
        raise RouterError(f'terminal closure requires all PM role-work requests resolved first: {request_ids}')
    if not router._current_closure_state_clean(project_root, run_root):
        raise RouterError('terminal closure requires current clean evidence/resource/final ledgers')
    continuation = read_json(continuation_path)
    continuation['heartbeat_active'] = False
    continuation['closed_at'] = utc_now()
    continuation['closure_reason'] = 'terminal_completion'
    write_json(continuation_path, continuation)
    closure = {'schema_version': 'flowpilot.terminal_closure_suite.v1', 'run_id': run_state['run_id'], 'approved_by_role': 'project_manager', 'status': 'closed', 'closed_at': utc_now(), 'source_paths': {'final_route_wide_gate_ledger': project_relative(project_root, final_ledger_path), 'terminal_backward_replay': project_relative(project_root, terminal_replay_path), 'task_completion_projection': project_relative(project_root, task_projection_path), 'execution_frontier': project_relative(project_root, run_root / 'execution_frontier.json'), 'crew_ledger': project_relative(project_root, run_root / 'crew_ledger.json'), 'continuation_binding': project_relative(project_root, continuation_path), 'pm_prior_path_context': project_relative(project_root, router._pm_prior_path_context_path(run_root)), 'route_history_index': project_relative(project_root, router._route_history_index_path(run_root)), 'pm_suggestion_ledger': project_relative(project_root, _pm_suggestion_ledger_path(run_root)) if pm_suggestion_status['exists'] else None, 'self_interrogation_index': project_relative(project_root, _self_interrogation_index_path(run_root)) if self_interrogation_status['exists'] else None, 'defect_ledger': closure_reconciliation['defect_ledger']['path'], 'crew_memory': closure_reconciliation['role_memory']['path'], 'continuation_quarantine': closure_reconciliation['continuation_quarantine']['path']}, 'decision': decision, 'prior_path_context_review': prior_review, 'pm_suggestion_ledger_review': {'entry_count': pm_suggestion_status['entry_count'], 'issue_count': pm_suggestion_status['issue_count'], 'clean': pm_suggestion_status['clean']}, 'self_interrogation_review': {'record_count': self_interrogation_status['record_count'], 'issue_count': self_interrogation_status['issue_count'], 'unresolved_hard_finding_count': self_interrogation_status['unresolved_hard_finding_count'], 'clean': self_interrogation_status['clean']}, 'terminal_closure_reconciliation': closure_reconciliation, 'lifecycle': {'heartbeat_active': False, 'manual_resume_notice_required': False, 'terminal_completion_notice_recorded': True, 'crew_memory_archived': True}, 'final_report': payload.get('final_report') or {}, **_role_output_envelope_record(payload)}
    write_json(run_root / 'closure' / 'terminal_closure_suite.json', closure)
    run_state['status'] = 'closed'
    run_state['phase'] = 'terminal'
    run_state['holder'] = 'controller'
    run_state['pending_action'] = None
    run_state.setdefault('flags', {})['terminal_closure_approved'] = True
    frontier = router._active_frontier(run_root)
    frontier['status'] = 'closed'
    frontier['phase'] = 'terminal'
    frontier['terminal'] = True
    frontier['terminal_event'] = 'pm_approves_terminal_closure'
    frontier['closed_at'] = utc_now()
    frontier['source'] = 'pm_approves_terminal_closure'
    write_json(run_root / 'execution_frontier.json', frontier)
    reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode='closed', event='pm_approves_terminal_closure')
    write_json(_lifecycle_record_path(run_root), {'schema_version': 'flowpilot.run_lifecycle.v1', 'run_id': run_state.get('run_id'), 'status': 'closed', 'request_event': 'pm_approves_terminal_closure', 'reason': 'terminal_completion', 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'reconciliation': reconciliation, 'closed_at': closure['closed_at']})
    append_history(run_state, 'run_closed', {'event': 'pm_approves_terminal_closure', 'lifecycle_path': project_relative(project_root, _lifecycle_record_path(run_root))})
    _sync_current_and_index_status(project_root, run_state)
    router._write_route_state_snapshot(project_root, run_root, run_state, source_event='pm_approves_terminal_closure')

def _recover_terminal_status_from_run_authorities(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> str | None:
    _bind_router(router)
    recoverable_statuses = {'stopped_by_user', 'cancelled_by_user', 'protocol_dead_end', 'completed', 'closed'}
    run_id = str(run_state.get('run_id') or run_root.name)
    status = str(run_state.get('status') or '')
    if status in recoverable_statuses:
        return status
    current = read_json_if_exists(project_root / '.flowpilot' / 'current.json') or {}
    if str(current.get('current_run_id') or current.get('active_run_id') or '') == run_id:
        current_status = str(current.get('status') or '')
        if current_status in recoverable_statuses:
            return current_status
    index = read_json_if_exists(project_root / '.flowpilot' / 'index.json') or {}
    runs = index.get('runs') if isinstance(index.get('runs'), list) else []
    for item in runs:
        if isinstance(item, dict) and str(item.get('run_id') or '') == run_id:
            index_status = str(item.get('status') or '')
            if index_status in recoverable_statuses:
                return index_status
    lifecycle = read_json_if_exists(_lifecycle_record_path(run_root)) or {}
    lifecycle_status = str(lifecycle.get('status') or '')
    if lifecycle_status in recoverable_statuses:
        return lifecycle_status
    frontier = read_json_if_exists(run_root / 'execution_frontier.json') or {}
    frontier_status = str(frontier.get('status') or '')
    if frontier.get('terminal') is True and frontier_status in recoverable_statuses:
        return frontier_status
    return None

def _repair_legacy_material_packet_contracts(router: ModuleType, project_root: Path, run_root: Path) -> int:
    _bind_router(router)
    index_path = router._material_scan_index_path(run_root)
    index = read_json_if_exists(index_path)
    ledger_path = run_root / 'packet_ledger.json'
    ledger = read_json_if_exists(ledger_path)
    if not isinstance(index, dict) and (not isinstance(ledger, dict)):
        return 0
    run_id = str((index.get('run_id') if isinstance(index, dict) else None) or (ledger.get('run_id') if isinstance(ledger, dict) else None) or run_root.name)
    ledger_packets = ledger.get('packets') if isinstance(ledger, dict) and isinstance(ledger.get('packets'), list) else []
    ledger_by_id = {str(packet.get('packet_id')): packet for packet in ledger_packets if isinstance(packet, dict) and packet.get('packet_id')}
    records_by_id: dict[str, dict[str, Any]] = {}
    if isinstance(index, dict):
        for list_name in ('packets', 'superseded_packets'):
            for record in index.get(list_name, []) if isinstance(index.get(list_name), list) else []:
                if isinstance(record, dict) and record.get('packet_id'):
                    records_by_id[str(record['packet_id'])] = record
    for packet in ledger_packets:
        if not isinstance(packet, dict):
            continue
        packet_id = str(packet.get('packet_id') or '')
        packet_type = str(packet.get('packet_type') or packet.get('packet_envelope', {}).get('packet_type') or '')
        if packet_id and (packet_type == 'material_scan' or packet_id.startswith('material-scan')):
            records_by_id.setdefault(packet_id, {})
    changed_index = False
    changed_ledger = False
    repaired: list[dict[str, Any]] = []
    repaired_at = utc_now()
    for packet_id, record in sorted(records_by_id.items()):
        paths = packet_runtime.packet_paths(project_root, packet_id, run_id)
        ledger_record = ledger_by_id.get(packet_id, {})
        result_body_rel = str(record.get('result_body_path') or ledger_record.get('result_body_path') or project_relative(project_root, paths['result_body']))
        result_envelope_rel = str(record.get('result_envelope_path') or ledger_record.get('result_envelope_path') or project_relative(project_root, paths['result_envelope']))
        envelope_rel = str(record.get('packet_envelope_path') or ledger_record.get('packet_envelope_path') or project_relative(project_root, paths['packet_envelope']))
        envelope_path = resolve_project_path(project_root, envelope_rel)
        envelope = read_json_if_exists(envelope_path)
        if not isinstance(envelope, dict):
            continue
        envelope_changed = False
        for key, value in (('result_body_path', result_body_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_envelope_path', result_envelope_rel)):
            if envelope.get(key) != value:
                envelope[key] = value
                envelope_changed = True
        target = {'result_envelope_path': result_envelope_rel, 'result_body_path': result_body_rel}
        if envelope.get('result_write_target') != target:
            envelope['result_write_target'] = target
            envelope_changed = True
        metadata = envelope.get('metadata') if isinstance(envelope.get('metadata'), dict) else {}
        metadata_updates = {'expected_result_body_path': result_body_rel, 'expected_result_envelope_path': result_envelope_rel, 'write_target_path': result_body_rel}
        for key, value in metadata_updates.items():
            if metadata.get(key) != value:
                metadata[key] = value
                envelope_changed = True
        if metadata:
            envelope['metadata'] = metadata
        output_contract = envelope.get('output_contract') if isinstance(envelope.get('output_contract'), dict) else None
        if isinstance(output_contract, dict):
            contract = dict(output_contract)
            for key, value in metadata_updates.items():
                if contract.get(key) != value:
                    contract[key] = value
                    envelope_changed = True
            if contract != output_contract:
                envelope['output_contract'] = contract
        replacement_for = record.get('replacement_for') or metadata.get('replacement_for') or ledger_record.get('replacement_for')
        if replacement_for and (not envelope.get('replacement_for')):
            envelope['replacement_for'] = replacement_for
            envelope_changed = True
        if replacement_for and (not envelope.get('supersedes')):
            envelope['supersedes'] = [replacement_for]
            envelope_changed = True
        if envelope_changed:
            envelope['legacy_material_packet_contract_migration'] = {'schema_version': 'flowpilot.legacy_material_packet_contract_migration.v1', 'sealed_packet_body_not_read': True, 'sealed_packet_body_not_rewritten': True, 'envelope_result_write_target_backfilled': True, 'body_hash_preserved': True, 'migrated_at': repaired_at}
            write_json(envelope_path, envelope)
            repaired.append({'packet_id': packet_id, 'packet_envelope_path': project_relative(project_root, envelope_path), 'result_body_path': result_body_rel, 'result_envelope_path': result_envelope_rel, 'sealed_packet_body_not_read': True, 'sealed_packet_body_not_rewritten': True})
        if record:
            for key, value in (('packet_envelope_path', project_relative(project_root, envelope_path)), ('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if record.get(key) != value:
                    record[key] = value
                    changed_index = True
            target = {'result_envelope_path': result_envelope_rel, 'result_body_path': result_body_rel}
            if record.get('result_write_target') != target:
                record['result_write_target'] = target
                changed_index = True
        if ledger_record:
            for key, value in (('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if ledger_record.get(key) != value:
                    ledger_record[key] = value
                    changed_ledger = True
            if ledger_record.get('result_write_target') != target:
                ledger_record['result_write_target'] = target
                changed_ledger = True
            packet_envelope = ledger_record.get('packet_envelope') if isinstance(ledger_record.get('packet_envelope'), dict) else {}
            for key, value in (('result_body_path', result_body_rel), ('result_envelope_path', result_envelope_rel), ('expected_result_body_path', result_body_rel), ('write_target_path', result_body_rel)):
                if packet_envelope.get(key) != value:
                    packet_envelope[key] = value
                    changed_ledger = True
            if packet_envelope:
                ledger_record['packet_envelope'] = packet_envelope
    if changed_index and isinstance(index, dict):
        index['updated_at'] = repaired_at
        write_json(index_path, index)
    if changed_ledger and isinstance(ledger, dict):
        ledger['updated_at'] = repaired_at
        write_json(ledger_path, ledger)
    if repaired:
        write_json(run_root / 'material' / 'legacy_material_packet_migration.json', {'schema_version': 'flowpilot.legacy_material_packet_contract_migration.v1', 'run_id': run_id, 'packet_count': len(repaired), 'packets': repaired, 'sealed_packet_bodies_read': False, 'sealed_packet_bodies_rewritten': False, 'migrated_at': repaired_at})
    return len(repaired)

def reconcile_current_run(router: ModuleType, project_root: Path) -> dict[str, Any]:
    _bind_router(router)
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = router.load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError('run state is missing')
    repaired: dict[str, Any] = {'prompt_delivery_contexts': 0, 'role_output_envelope_hashes': 0, 'terminal_lifecycle': False, 'terminal_lifecycle_record_written': False, 'terminal_closure_status_recovered': False, 'terminal_status_recovered_from_authority': False, 'legacy_material_packet_contracts': 0, 'non_current_running_index_entries': 0, 'scheduled_controller_receipts': {'changed': False, 'reconciled': 0, 'blocked': 0}, 'controller_boundary_projection': {'changed': False, 'reason': 'not_run'}}
    status = str(run_state.get('status') or '')
    flags = run_state.setdefault('flags', {})
    recovered_terminal_status = router._recover_terminal_status_from_run_authorities(project_root, run_root, run_state)
    if recovered_terminal_status and status not in RUN_TERMINAL_STATUSES:
        run_state['status'] = recovered_terminal_status
        status = recovered_terminal_status
        repaired['terminal_status_recovered_from_authority'] = True
        if recovered_terminal_status == 'closed':
            flags['terminal_closure_approved'] = True
            repaired['terminal_closure_status_recovered'] = True
    if status == 'stopped_by_user':
        flags['run_stopped_by_user'] = True
    elif status == 'cancelled_by_user':
        flags['run_cancelled_by_user'] = True
    elif status not in RUN_TERMINAL_STATUSES and router._terminal_closure_suite_is_closed(run_root):
        run_state['status'] = 'closed'
        flags['terminal_closure_approved'] = True
        status = 'closed'
        repaired['terminal_closure_status_recovered'] = True
    mode = _terminal_lifecycle_mode(run_state)
    if mode:
        run_state['status'] = mode
        run_state['phase'] = 'terminal'
        run_state['holder'] = 'controller'
        run_state['pending_action'] = None
        reconciliation = _reconcile_terminal_lifecycle_authorities(project_root, run_root, run_state, mode=mode, event='reconcile_current_run')
        lifecycle_path = _lifecycle_record_path(run_root)
        if not lifecycle_path.exists():
            write_json(lifecycle_path, {'schema_version': 'flowpilot.run_lifecycle.v1', 'run_id': run_state.get('run_id'), 'status': mode, 'request_event': 'reconcile_current_run', 'reason': 'terminal_lifecycle_reconciled_from_existing_authorities', 'controller_may_continue_route_work': False, 'controller_may_spawn_new_role_work': False, 'reconciliation': reconciliation, 'reconciled_at': utc_now()})
            append_history(run_state, 'run_lifecycle_record_written_by_reconcile', {'lifecycle_path': project_relative(project_root, lifecycle_path), 'status': mode})
            repaired['terminal_lifecycle_record_written'] = True
        _sync_current_and_index_status(project_root, run_state)
        repaired['terminal_lifecycle'] = True
    repaired['prompt_delivery_contexts'] = _repair_prompt_delivery_contexts(project_root, run_root, run_state)
    repaired['role_output_envelope_hashes'] = _repair_role_output_envelope_hashes(project_root, run_root)
    repaired['legacy_material_packet_contracts'] = router._repair_legacy_material_packet_contracts(project_root, run_root)
    repaired['scheduled_controller_receipts'] = router._reconcile_scheduled_controller_action_receipts(project_root, run_root, run_state)
    repaired['controller_boundary_projection'] = _reconcile_controller_boundary_confirmation_projection(project_root, run_root, run_state, source='reconcile_current_run_projection_repair')
    router._refresh_route_memory(project_root, run_root, run_state, trigger='reconcile_current_run')
    repaired['non_current_running_index_entries'] = router._reconcile_non_current_running_index_entries(project_root, run_state)
    router._sync_derived_run_views(project_root, run_root, run_state, reason='reconcile_current_run')
    append_history(run_state, 'router_reconciled_current_run', repaired)
    router.save_run_state(run_root, run_state)
    return {'ok': True, 'run_id': run_state.get('run_id'), 'run_root': project_relative(project_root, run_root), 'repaired': repaired}


_LOCAL_NAMES = set(globals())
