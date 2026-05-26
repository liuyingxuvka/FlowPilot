"""Coarse event dispatcher owner helpers for the FlowPilot router.

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

def _record_external_event_unchecked(router: ModuleType, project_root: Path, event: str, payload: dict[str, Any] | None=None, *, envelope_path: str | None=None, envelope_hash: str | None=None) -> dict[str, Any]:
    _bind_router(router)
    if event not in EXTERNAL_EVENTS:
        if _is_card_return_event_name(event):
            return _record_card_return_event_from_external_entrypoint(project_root, event)
        raise RouterError(f'unknown external event: {event}')
    bootstrap = router.load_bootstrap_state(project_root, create_if_missing=False)
    run_state, run_root = router.load_run_state(project_root, bootstrap)
    if run_state is None or run_root is None:
        raise RouterError('run state is missing')
    meta = EXTERNAL_EVENTS[event]
    flag = meta['flag']
    required_flag = meta.get('requires_flag')
    parent_segment_decision: str | None = None
    model_miss_triage_decision: str | None = None
    router._refresh_route_memory(project_root, run_root, run_state, trigger=f'before_external_event:{event}')
    migrated_precheck_result = flowpilot_router_events.handle_precheck_event(router, project_root, run_root, run_state, event, meta, payload)
    if migrated_precheck_result is not None:
        return migrated_precheck_result
    if event == 'controller_reports_role_no_output':
        return router._record_role_no_output_reissue(project_root, run_root, run_state, payload or {}, source_event=event)
    if event == 'controller_reports_role_liveness_fault' and router._payload_indicates_role_no_output(payload or {}):
        return router._record_role_no_output_reissue(project_root, run_root, run_state, payload or {}, source_event=event)
    if event == 'controller_reports_role_liveness_fault':
        target_role_keys = router._role_recovery_target_roles((payload or {}).get('target_role_keys') or (payload or {}).get('role_key') or (payload or {}).get('missing_role_key'))
        transaction = router._open_role_recovery_transaction(project_root, run_root, run_state, trigger_source='mid_run_liveness_fault', recovery_scope='targeted', target_role_keys=target_role_keys, fault_payload=payload or {})
        for recovery_flag in ('role_recovery_state_loaded', 'role_recovery_roles_restored', 'role_recovery_report_written', 'role_recovery_environment_blocked', 'controller_resume_card_delivered', 'pm_crew_rehydration_freshness_card_delivered', 'pm_resume_decision_card_delivered', 'pm_resume_recovery_decision_returned', 'role_recovery_obligations_scanned', 'role_recovery_obligation_replay_completed', 'role_recovery_pm_escalation_required'):
            run_state['flags'][recovery_flag] = False
        run_state['flags']['role_recovery_requested'] = True
        run_state['pending_action'] = None
        record = {'event': event, 'summary': meta['summary'], 'payload': payload or {}, 'role_recovery_transaction_id': transaction['transaction_id'], 'target_role_keys': target_role_keys, 'recorded_at': utc_now()}
        run_state['events'].append(record)
        append_history(run_state, event, {'role_recovery_transaction_id': transaction['transaction_id'], 'target_role_keys': target_role_keys, 'priority': 'preempt_normal_work'})
        router._refresh_route_memory(project_root, run_root, run_state, trigger=f'after_external_event:{event}')
        router._sync_derived_run_views(project_root, run_root, run_state, reason=f'after_external_event:{event}')
        router.save_run_state(run_root, run_state)
        return {'ok': True, 'event': event, 'role_recovery_requested': True, 'role_recovery_transaction': transaction}
    _preconsume_pending_card_return_ack_before_external_event(project_root, run_root, run_state, event=event)
    pending_card_return = _pending_card_return_blocker_for_event(run_root, str(run_state['run_id']), event, run_state)
    if pending_card_return is not None:
        recovered = _quarantine_missing_ack_report_before_external_event(project_root, run_root, run_state, event=event, payload=payload, envelope_path=envelope_path, envelope_hash=envelope_hash, pending_return=pending_card_return)
        if recovered is not None:
            return recovered
        if event in STARTUP_REVIEW_BEGIN_JOIN_EVENTS and _pending_return_is_pre_review_startup_scope(pending_card_return):
            blockers = _startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
            next_action = _current_scope_pre_review_reconciliation_action(project_root, run_root, run_state, blockers=blockers, review_trigger=event)
            if isinstance(next_action, dict):
                run_state['pending_action'] = next_action
            append_history(run_state, 'router_blocked_startup_review_for_current_scope_reconciliation', {'event': event, 'pending_card_return_event': pending_card_return.get('card_return_event'), 'pending_card_id': pending_card_return.get('card_id'), 'pending_card_ids': pending_card_return.get('card_ids') or [], 'target_role': pending_card_return.get('target_role'), 'next_action_type': next_action.get('action_type') if isinstance(next_action, dict) else None, 'common_progress_source': 'runtime/controller_action_ledger.json_and_card_pending_return_ledger'})
            router._refresh_route_memory(project_root, run_root, run_state, trigger='after_router_blocked_startup_review_for_current_scope_reconciliation')
            router._sync_derived_run_views(project_root, run_root, run_state, reason='after_router_blocked_startup_review_for_current_scope_reconciliation', update_display=True)
            router.save_run_state(run_root, run_state)
            return {'ok': False, 'event': event, 'waiting': True, 'recoverable': True, 'current_scope_reconciliation_blocked': True, 'startup_pre_review_ack_join_blocked': True, 'scope_kind': next_action.get('scope_kind') if isinstance(next_action, dict) else 'startup', 'scope_id': next_action.get('scope_id') if isinstance(next_action, dict) else 'startup', 'blockers': blockers, 'pending_card_return_event': pending_card_return.get('card_return_event'), 'pending_card_id': pending_card_return.get('card_id'), 'pending_card_ids': pending_card_return.get('card_ids') or [], 'waiting_for_role': pending_card_return.get('target_role'), 'next_required_action': next_action if isinstance(next_action, dict) else None}
        raise RouterError(f"event blocked by unresolved card return: waiting for {pending_card_return.get('card_return_event')} from {pending_card_return.get('target_role')} for card {pending_card_return.get('card_id')}; validate the expected return envelope before recording another role event")
    scoped_identity: dict[str, Any] | None = None
    payload_normalized_for_replay = False
    if _payload_requires_record_event_envelope_validation(payload, envelope_path=envelope_path, envelope_hash=envelope_hash):
        payload = _normalize_record_event_payload(project_root, run_state, event=event, payload=payload, envelope_path=envelope_path, envelope_hash=envelope_hash)
        payload_normalized_for_replay = True
        scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    if run_state['flags'].get(flag):
        if not payload_normalized_for_replay:
            payload = _normalize_record_event_payload(project_root, run_state, event=event, payload=payload, envelope_path=envelope_path, envelope_hash=envelope_hash)
            payload_normalized_for_replay = True
            scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
        _check_scoped_event_conflict(run_state, scoped_identity)
        if _scoped_event_is_recorded(run_state, scoped_identity):
            return _already_recorded_external_event_result(project_root, run_root, run_state, event=event, payload=payload, scoped_identity=scoped_identity)
        if not _external_event_flag_replay_requires_new_processing(run_root, run_state, event=event, flag=flag, payload=payload, scoped_identity=scoped_identity):
            return _already_recorded_external_event_result(project_root, run_root, run_state, event=event, payload=payload, scoped_identity=scoped_identity)
    if event in STARTUP_REVIEW_BEGIN_JOIN_EVENTS:
        blockers = _startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
        if blockers:
            next_action = _current_scope_pre_review_reconciliation_action(project_root, run_root, run_state, blockers=blockers, review_trigger=event)
            run_state['pending_action'] = next_action
            append_history(run_state, 'router_blocked_startup_review_for_current_scope_reconciliation', {'event': event, 'scope_kind': next_action.get('scope_kind'), 'scope_id': next_action.get('scope_id'), 'blocker_count': len(blockers), 'local_scope_only': True})
            router._refresh_route_memory(project_root, run_root, run_state, trigger='after_router_blocked_startup_review_for_current_scope_reconciliation')
            router._sync_derived_run_views(project_root, run_root, run_state, reason='after_router_blocked_startup_review_for_current_scope_reconciliation', update_display=True)
            router.save_run_state(run_root, run_state)
            return {'ok': False, 'event': event, 'waiting': True, 'recoverable': True, 'current_scope_reconciliation_blocked': True, 'scope_kind': next_action.get('scope_kind'), 'scope_id': next_action.get('scope_id'), 'blockers': blockers, 'next_required_action': next_action}
    if event in CURRENT_SCOPE_REVIEW_EVENTS:
        blockers = _pre_review_reconciliation_blockers_for_trigger(project_root, run_root, run_state, event)
        if blockers:
            next_action = _current_scope_pre_review_reconciliation_action(project_root, run_root, run_state, blockers=blockers, review_trigger=event)
            run_state['pending_action'] = next_action
            append_history(run_state, 'router_blocked_current_node_review_for_local_reconciliation', {'event': event, 'scope_kind': next_action.get('scope_kind'), 'scope_id': next_action.get('scope_id'), 'blocker_count': len(blockers), 'local_scope_only': True})
            router._refresh_route_memory(project_root, run_root, run_state, trigger='after_router_blocked_current_node_review_for_local_reconciliation')
            router._sync_derived_run_views(project_root, run_root, run_state, reason='after_router_blocked_current_node_review_for_local_reconciliation', update_display=True)
            router.save_run_state(run_root, run_state)
            return {'ok': False, 'event': event, 'waiting': True, 'recoverable': True, 'current_scope_reconciliation_blocked': True, 'scope_kind': next_action.get('scope_kind'), 'scope_id': next_action.get('scope_id'), 'blockers': blockers, 'next_required_action': next_action}
    if not payload_normalized_for_replay:
        payload = _normalize_record_event_payload(project_root, run_state, event=event, payload=payload, envelope_path=envelope_path, envelope_hash=envelope_hash)
        scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
    _check_scoped_event_conflict(run_state, scoped_identity)
    if _scoped_event_is_recorded(run_state, scoped_identity):
        return _already_recorded_external_event_result(project_root, run_root, run_state, event=event, payload=payload, scoped_identity=scoped_identity)
    if required_flag and (not run_state['flags'].get(required_flag)):
        raise RouterError(f'event {event} requires {required_flag}')
    _check_scoped_event_retry_budget(run_state, scoped_identity)
    if run_state['flags'].get(flag) and (not _external_event_flag_replay_requires_new_processing(run_root, run_state, event=event, flag=flag, payload=payload, scoped_identity=scoped_identity)):
        _check_scoped_event_conflict(run_state, scoped_identity)
        return _already_recorded_external_event_result(project_root, run_root, run_state, event=event, payload=payload, scoped_identity=scoped_identity)
    payload = payload or {}
    route_action = router._route_action_for_event(event)
    if route_action:
        router._require_legal_route_action(project_root, run_root, run_state, route_action, f'external event {event}')
    if flowpilot_router_events.apply_migrated_event_side_effect(router, project_root, run_root, run_state, event, payload):
        pass
    elif event == 'pm_resume_recovery_decision_returned':
        _write_pm_resume_decision(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_node_acceptance_plan':
        _write_node_acceptance_plan(project_root, run_root, run_state, payload)
    elif event == 'pm_revises_node_acceptance_plan':
        _write_pm_revised_node_acceptance_plan(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_node_acceptance_plan':
        frontier = router._active_frontier(run_root)
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=_active_node_root(run_root, frontier) / 'reviews' / 'node_acceptance_plan_review.json', schema_version='flowpilot.node_acceptance_plan_review.v1', checked_paths=[_active_node_acceptance_plan_path(run_root, frontier), run_root / 'execution_frontier.json'])
    elif event == 'reviewer_blocks_node_acceptance_plan':
        frontier = router._active_frontier(run_root)
        _write_role_block_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=_active_node_root(run_root, frontier) / 'reviews' / 'node_acceptance_plan_block.json', schema_version='flowpilot.node_acceptance_plan_block.v1', checked_paths=[_active_node_acceptance_plan_path(run_root, frontier), run_root / 'execution_frontier.json'])
        run_state['flags']['node_acceptance_plan_reviewer_passed'] = False
        run_state['flags']['node_acceptance_plan_revised_by_pm'] = False
    elif event == 'reviewer_blocks_current_node_dispatch':
        frontier = router._active_frontier(run_root)
        packet_id = str(frontier.get('active_packet_id') or run_state.get('current_node_packet_id') or '')
        checked_paths = [_active_node_acceptance_plan_path(run_root, frontier), run_root / 'execution_frontier.json']
        if packet_id:
            checked_paths.append(run_root / 'packets' / packet_id / 'packet_envelope.json')
        _write_role_block_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=_active_node_root(run_root, frontier) / 'reviews' / 'current_node_dispatch_block.json', schema_version='flowpilot.current_node_dispatch_block.v1', checked_paths=checked_paths)
        run_state['flags']['current_node_dispatch_allowed'] = False
    elif event == 'reviewer_reports_startup_facts':
        router._write_startup_fact_report(project_root, run_root, run_state, payload)
    elif event == 'pm_approves_startup_activation':
        router._write_startup_activation(project_root, run_root, run_state, payload)
    elif event == 'pm_requests_startup_repair':
        router._write_startup_repair_request(project_root, run_root, run_state, payload)
    elif event == 'pm_declares_startup_protocol_dead_end':
        router._write_startup_protocol_dead_end(project_root, run_root, run_state, payload)
    elif event == 'pm_issues_material_and_capability_scan_packets':
        router._write_material_scan_packets(project_root, run_root, run_state, payload)
    elif event == 'reviewer_blocks_material_scan_dispatch':
        router._write_material_dispatch_block_report(project_root, run_root, run_state, payload)
    elif event in {'reviewer_blocks_material_scan_dispatch_recheck', 'router_direct_material_scan_dispatch_recheck_blocked'}:
        router._write_material_dispatch_block_report(project_root, run_root, run_state, payload)
        router._finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event in {'reviewer_protocol_blocker_material_scan_dispatch_recheck', 'router_protocol_blocker_material_scan_dispatch_recheck'}:
        router._write_material_dispatch_recheck_protocol_blocker(project_root, run_root, run_state, payload, event_name=event)
        router._finalize_repair_transaction_outcome(project_root, run_root, run_state, event=event, payload=payload)
    elif event == 'worker_scan_packet_bodies_delivered_after_dispatch':
        material_index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        router._validate_packet_bodies_opened_by_targets(project_root, run_state, material_index['packets'])
    elif event == 'worker_scan_results_returned':
        material_index = router._load_packet_index(router._material_scan_index_path(run_root), label='material scan')
        router._validate_results_exist_for_packets(project_root, run_state, material_index['packets'], next_recipient='project_manager')
        router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'material_scan')
    elif event == 'pm_records_material_scan_result_disposition':
        router._write_pm_package_result_disposition(project_root, run_root, run_state, payload, batch_kind='material_scan', package_label='material_scan', gate_kind='material_sufficiency', output_path=run_root / 'material' / 'pm_material_scan_result_disposition.json', router_event=event)
    elif event == 'reviewer_reports_material_sufficient':
        router._write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=True)
        material_batch = router._active_parallel_packet_batch(run_root, 'material_scan')
        if material_batch:
            router._mark_parallel_batch_reviewed(run_root, 'material_scan', passed=True, reviewed_packet_ids=[str(record.get('packet_id')) for record in material_batch['packets'] if isinstance(record, dict)])
    elif event == 'reviewer_reports_material_insufficient':
        router._write_material_sufficiency_report(project_root, run_root, run_state, payload, sufficient=False)
        material_batch = router._active_parallel_packet_batch(run_root, 'material_scan')
        if material_batch:
            router._mark_parallel_batch_reviewed(run_root, 'material_scan', passed=False, reviewed_packet_ids=[str(record.get('packet_id')) for record in material_batch['packets'] if isinstance(record, dict)])
    elif event == 'pm_writes_research_package':
        router._write_research_package(project_root, run_root, run_state, payload)
    elif event == 'research_capability_decision_recorded':
        router._write_research_capability_decision(project_root, run_root, run_state, payload)
    elif event == PM_ROLE_WORK_REQUEST_EVENT:
        router._write_pm_role_work_request(project_root, run_root, run_state, payload)
    elif event == ROLE_WORK_RESULT_RETURNED_EVENT:
        router._write_role_work_result_returned(project_root, run_root, run_state, payload)
    elif event == PM_ROLE_WORK_RESULT_DECISION_EVENT:
        router._write_pm_role_work_result_decision(project_root, run_root, run_state, payload)
    elif event == 'worker_research_report_returned':
        router._write_worker_research_report(project_root, run_root, run_state, payload)
        router._mark_parallel_batch_results_joined(project_root, run_root, run_state, 'research')
    elif event == 'pm_records_research_result_disposition':
        router._write_pm_package_result_disposition(project_root, run_root, run_state, payload, batch_kind='research', package_label='research', gate_kind='research_direct_source_check', output_path=run_root / 'research' / 'pm_research_result_disposition.json', router_event=event)
    elif event == 'reviewer_passes_research_direct_source_check':
        research_index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        raw_agent_map = payload.get('agent_role_map')
        router._validate_packet_group_for_reviewer(project_root, run_state, research_index['packets'], audit_path=run_root / 'research' / 'research_packet_review_audit.json', agent_role_map=raw_agent_map if isinstance(raw_agent_map, dict) else None)
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'research' / 'research_reviewer_report.json', schema_version='flowpilot.research_reviewer_report.v1', checked_paths=[run_root / 'research' / 'research_package.json', run_root / 'research' / 'worker_research_report.json'])
        research_batch = router._active_parallel_packet_batch(run_root, 'research')
        if research_batch:
            router._mark_parallel_batch_reviewed(run_root, 'research', passed=True, reviewed_packet_ids=[str(record.get('packet_id')) for record in research_batch['packets'] if isinstance(record, dict)])
    elif event == 'pm_absorbs_reviewed_research':
        router._write_pm_research_absorption(project_root, run_root, run_state)
    elif event == 'pm_writes_material_understanding':
        router._write_material_understanding(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_product_function_architecture':
        _write_product_function_architecture(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_product_architecture':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'reviews' / 'product_architecture_challenge.json', schema_version='flowpilot.product_architecture_review.v1', checked_paths=[run_root / 'product_function_architecture.json', router._require_product_behavior_model_report(project_root, run_root), run_root / 'flowguard' / 'product_behavior_model_pm_decision.json'])
    elif event in {'product_officer_submits_product_behavior_model', 'product_officer_passes_product_architecture_modelability'}:
        _write_product_behavior_model_report(project_root, run_root, run_state, payload)
    elif event == 'pm_accepts_product_behavior_model':
        _write_pm_product_behavior_model_decision(project_root, run_root, run_state, payload, accepted=True)
    elif event == 'pm_requests_product_behavior_model_rebuild':
        _write_pm_product_behavior_model_decision(project_root, run_root, run_state, payload, accepted=False)
    elif event == 'pm_writes_root_acceptance_contract':
        _write_root_acceptance_contract(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_root_acceptance_contract':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'reviews' / 'root_contract_challenge.json', schema_version='flowpilot.root_contract_review.v1', checked_paths=[run_root / 'root_acceptance_contract.json', run_root / 'standard_scenario_pack.json'])
    elif event == 'product_officer_passes_root_acceptance_contract_modelability':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='product_flowguard_officer', path=run_root / 'flowguard' / 'root_contract_modelability.json', schema_version='flowpilot.root_contract_modelability.v1', checked_paths=[run_root / 'root_acceptance_contract.json', run_root / 'standard_scenario_pack.json', run_root / 'reviews' / 'root_contract_challenge.json'])
    elif event == 'pm_freezes_root_acceptance_contract':
        _freeze_root_acceptance_contract(project_root, run_root, run_state)
    elif event == 'pm_records_dependency_policy':
        _write_dependency_policy(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_capabilities_manifest':
        _write_capabilities_manifest(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_child_skill_selection':
        _write_child_skill_selection(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_child_skill_gate_manifest':
        _write_child_skill_gate_manifest(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_child_skill_gate_manifest':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'reviews' / 'child_skill_gate_manifest_review.json', schema_version='flowpilot.child_skill_gate_manifest_review.v1', checked_paths=[run_root / 'child_skill_gate_manifest.json', run_root / 'pm_child_skill_selection.json', run_root / 'capabilities.json'])
        _sync_child_skill_manifest_review_approval(project_root, run_root)
    elif event == 'process_officer_passes_child_skill_conformance_model':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='process_flowguard_officer', path=run_root / 'flowguard' / 'child_skill_conformance_model.json', schema_version='flowpilot.child_skill_conformance_model.v1', checked_paths=[run_root / 'child_skill_gate_manifest.json', run_root / 'reviews' / 'child_skill_gate_manifest_review.json'])
    elif event == 'product_officer_passes_child_skill_product_fit':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='product_flowguard_officer', path=run_root / 'flowguard' / 'child_skill_product_fit.json', schema_version='flowpilot.child_skill_product_fit.v1', checked_paths=[run_root / 'child_skill_gate_manifest.json', run_root / 'flowguard' / 'child_skill_conformance_model.json', run_root / 'product_function_architecture.json', run_root / 'root_acceptance_contract.json'])
    elif event == 'pm_approves_child_skill_manifest_for_route':
        _approve_child_skill_manifest_for_route(project_root, run_root, run_state, payload)
    elif event == 'capability_evidence_synced':
        _sync_capability_evidence(project_root, run_root, run_state, payload)
    elif event == 'pm_writes_route_draft':
        if run_state['flags'].get(flag) and (not run_state['flags'].get('route_activated_by_pm')):
            router._reset_route_review_after_route_draft_repair(run_state)
        router._write_route_draft(project_root, run_root, run_state, payload)
    elif event in {'process_officer_submits_process_route_model', 'process_officer_passes_route_check'}:
        _write_route_process_pass_report(project_root, run_root, run_state, payload)
    elif event == 'pm_accepts_process_route_model':
        _write_pm_process_route_model_decision(project_root, run_root, run_state, payload, accepted=True)
    elif event == 'pm_requests_process_route_model_rebuild':
        _write_pm_process_route_model_decision(project_root, run_root, run_state, payload, accepted=False)
    elif event in {'process_officer_requests_process_route_model_repair', 'process_officer_requires_route_repair'}:
        _write_route_process_issue_report(project_root, run_root, run_state, payload, expected_verdict='repair_required')
    elif event in {'process_officer_blocks_process_route_model', 'process_officer_blocks_route_check'}:
        _write_route_process_issue_report(project_root, run_root, run_state, payload, expected_verdict='blocked')
    elif event == 'product_officer_passes_route_check':
        _write_route_product_pass_report(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_route_check':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'reviews' / 'route_challenge.json', schema_version='flowpilot.route_review.v1', checked_paths=[router._current_route_draft_path(run_root), router._require_product_behavior_model_report(project_root, run_root), router._require_process_route_model_report(project_root, run_root), run_root / 'flowguard' / 'process_route_model_pm_decision.json'])
    elif event == 'pm_registers_current_node_packet':
        router._validate_current_node_packet_event(project_root, run_root, run_state, payload)
    elif event == 'worker_current_node_result_returned':
        router._validate_current_node_result_event(project_root, run_state, payload)
    elif event == 'pm_records_current_node_result_disposition':
        frontier = router._active_frontier(run_root)
        router._write_pm_package_result_disposition(project_root, run_root, run_state, payload, batch_kind='current_node', package_label='current_node', gate_kind='node_completion', output_path=_active_node_root(run_root, frontier) / 'reviews' / 'pm_current_node_result_disposition.json', router_event=event)
    elif event == 'current_node_reviewer_passes_result':
        router._validate_current_node_reviewer_pass(project_root, run_state, payload)
    elif event == 'pm_builds_parent_backward_targets':
        _write_parent_backward_targets(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_parent_backward_replay':
        _write_parent_backward_replay(project_root, run_root, run_state, payload)
    elif event == 'pm_records_parent_segment_decision':
        parent_segment_decision = _write_parent_segment_decision(project_root, run_root, run_state, payload)
    elif event == 'pm_completes_current_node_from_reviewed_result':
        router._mark_frontier_node_completed(project_root, run_root, run_state, payload)
    elif event == 'pm_completes_parent_node_from_backward_replay':
        router._mark_frontier_node_completed(project_root, run_root, run_state, payload, source_event='pm_completes_parent_node_from_backward_replay')
    elif event == 'pm_records_evidence_quality_package':
        _write_evidence_quality_package(project_root, run_root, run_state, payload)
    elif event == 'reviewer_passes_evidence_quality_package':
        _write_role_gate_report(project_root, run_root, run_state, payload, expected_role='human_like_reviewer', path=run_root / 'reviews' / 'evidence_quality_review.json', schema_version='flowpilot.evidence_quality_review.v1', checked_paths=[run_root / 'evidence' / 'evidence_ledger.json', run_root / 'generated_resource_ledger.json', run_root / 'quality' / 'quality_package.json'])
    elif event == 'pm_records_final_route_wide_ledger_clean':
        router._write_final_route_wide_ledger(project_root, run_root, run_state, payload)
    elif event == 'reviewer_final_backward_replay_passed':
        router._write_terminal_backward_replay(project_root, run_root, run_state, payload)
    elif event in GATE_OUTCOME_BLOCK_EVENTS:
        _write_gate_outcome_block_report(project_root, run_root, run_state, payload, event=event)
    elif event == 'pm_mutates_route_after_review_block':
        if not run_state['flags'].get('model_miss_triage_closed'):
            raise RouterError('review-block repair or route mutation requires closed model-miss triage first')
        _write_pm_review_block_repair(project_root, run_root, run_state, payload)
    elif event == PM_MODEL_MISS_TRIAGE_DECISION_EVENT:
        model_miss_triage_decision = router._write_model_miss_triage_decision(project_root, run_root, run_state, payload)
    elif event == PM_CONTROL_BLOCKER_REPAIR_DECISION_EVENT:
        router._write_control_blocker_repair_decision(project_root, run_root, run_state, payload)
    elif event == GATE_DECISION_EVENT:
        router._write_gate_decision(project_root, run_root, run_state, payload)
    elif event == 'pm_approves_terminal_closure':
        router._write_terminal_closure_suite(project_root, run_root, run_state, payload)
    elif event == 'pm_accepts_reviewed_material':
        if run_state.get('material_review') != 'sufficient':
            raise RouterError('PM can accept material only after a sufficient reviewer material report')
    elif event == 'pm_requests_research_after_material_insufficient':
        if run_state.get('material_review') != 'insufficient':
            raise RouterError('PM can request research on this path only after an insufficient reviewer material report')
    return flowpilot_router_events.finalize_external_event_record(router, project_root, run_root, run_state, event, meta, payload, flag=flag, scoped_identity=scoped_identity, model_miss_triage_decision=model_miss_triage_decision, parent_segment_decision=parent_segment_decision)


_LOCAL_NAMES = set(globals())
