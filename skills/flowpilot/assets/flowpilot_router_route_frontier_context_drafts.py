"""Cohesive child helpers for FlowPilot route-frontier state."""

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
    for flag in ('flowguard_operator_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'flowguard_operator_route_check_passed', 'flowguard_operator_route_repair_required', 'flowguard_operator_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'flowguard_operator_product_route_check_card_delivered', 'flowguard_operator_product_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False


def _reset_route_hard_gate_approvals_for_recheck(router: ModuleType, run_state: dict[str, Any]) -> None:
    _bind_router(router)
    for flag in ('pm_route_skeleton_card_delivered', 'route_draft_written_by_pm', 'flowguard_operator_route_check_card_delivered', 'process_route_model_submitted', 'process_route_model_repair_required', 'process_route_model_blocked', 'flowguard_operator_route_check_passed', 'flowguard_operator_route_repair_required', 'flowguard_operator_route_check_blocked', 'pm_process_route_model_decision_card_delivered', 'pm_process_route_model_accepted', 'pm_process_route_model_rebuild_requested', 'flowguard_operator_product_route_check_card_delivered', 'flowguard_operator_product_route_check_passed', 'reviewer_route_check_card_delivered', 'reviewer_route_check_passed', 'route_activated_by_pm'):
        run_state.setdefault('flags', {})[flag] = False


def _product_behavior_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'product_behavior_model.json'


def _require_product_behavior_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._product_behavior_model_report_path(run_root)
    if not path.exists():
        raise RouterError('route draft requires FlowGuard operator product-scope product behavior model report')
    report = read_json(path)
    if report.get('passed') is not True:
        raise RouterError('route draft requires passed FlowGuard operator product-scope product behavior model report')
    return path


def _process_route_model_report_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / 'flowguard' / 'process_route_model.json'


def _require_process_route_model_report(router: ModuleType, project_root: Path, run_root: Path) -> Path:
    _bind_router(router)
    path = router._process_route_model_report_path(run_root)
    if not path.exists():
        raise RouterError('route activation requires process route model report')
    report = read_json(path)
    if report.get('passed') is not True or report.get('process_viability_verdict') != 'pass':
        raise RouterError('route activation requires FlowGuard operator route-scope process route model pass')
    return path


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
    '_write_route_draft',
    '_reset_route_review_after_route_draft_repair',
    '_reset_route_hard_gate_approvals_for_recheck',
    '_product_behavior_model_report_path',
    '_require_product_behavior_model_report',
    '_process_route_model_report_path',
    '_require_process_route_model_report',
    '_require_route_process_pass',
    '_supersede_active_current_node_packet_for_route_mutation',
    '_current_route_draft_path',
)

_LOCAL_NAMES = set(globals())
