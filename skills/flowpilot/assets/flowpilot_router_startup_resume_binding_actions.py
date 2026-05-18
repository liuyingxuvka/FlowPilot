"""Resume and startup heartbeat next-action builders."""

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
from flowpilot_router_protocol_catalog import *

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None

def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value

def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router skeleton is not bound")
    return _BOUND_ROUTER

def _next_resume_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('resume_reentry_requested'):
        return None
    if not flags.get('resume_state_loaded'):
        resume_next = router._derive_resume_next_recipient_from_packet_ledger(run_root)
        return make_action(action_type='load_resume_state', actor='controller', label='controller_loads_resume_state_before_role_rehydration', summary='Controller loads current-run state, ledgers, frontier, visible plan, and crew memory before live role rehydration.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _router_daemon_lock_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router._continuation_quarantine_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, _router_daemon_status_path(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root))], extra={'postcondition': 'resume_state_loaded', 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'wake_recorded_to_router_required': True, 'visible_plan_restore_required': True, 'role_rehydration_required_before_pm_resume_decision': True, 'continuation_quarantine_required': True, 'resume_next_recipient_from_packet_ledger': resume_next, 'router_daemon_resume_recovery': _router_daemon_resume_recovery_summary(project_root, run_root)})
    if not flags.get('resume_roles_restored'):
        active_blocker = run_state.get('active_control_blocker')
        if isinstance(active_blocker, dict) and active_blocker.get('originating_action_type') == 'rehydrate_role_agents':
            return None
        return make_action(action_type='rehydrate_role_agents', actor='controller', label='host_rehydrates_resume_roles_before_pm_decision', summary='Host restores or replaces all six live FlowPilot roles from current-run memory before PM resume decision.', allowed_reads=[project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root)), project_relative(project_root, router._display_plan_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'resume_roles_restored', **router._resume_role_rehydration_action_extra(project_root, run_root, run_state)})
    return None

def _next_role_recovery_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('role_recovery_requested'):
        return None
    transaction = router._latest_role_recovery_transaction(run_root)
    if transaction.get('schema_version') != ROLE_RECOVERY_TRANSACTION_SCHEMA:
        return None
    trigger_source = str(transaction.get('trigger_source') or '')
    if trigger_source in {'heartbeat_resume', 'manual_resume'}:
        return None
    if not flags.get('role_recovery_state_loaded'):
        return make_action(action_type='load_role_recovery_state', actor='controller', label='controller_loads_role_recovery_state_before_normal_work', summary='Controller loads current-run role recovery state before any normal route, packet, gate, wait, or control-blocker work continues.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'continuation' / 'resume_reentry.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_state_loaded', 'role_recovery_transaction': transaction, 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'recovery_priority': 'preempt_normal_work', 'normal_waits_allowed_before_recovery': False})
    if not flags.get('role_recovery_roles_restored') and (not flags.get('role_recovery_environment_blocked')):
        return make_action(action_type='recover_role_agents', actor='controller', label='host_recovers_role_agents_before_normal_work', summary='Host restores or replaces the unhealthy background role, escalating to full crew recycle when targeted recovery cannot succeed.', allowed_reads=[project_relative(project_root, router._role_recovery_latest_transaction_path(run_root)), project_relative(project_root, router._role_recovery_state_path(run_root)), project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'), project_relative(project_root, run_root / 'crew_memory'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, run_root / 'execution_frontier.json'), project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, run_root / 'prompt_delivery_ledger.json'), project_relative(project_root, router._route_history_index_path(run_root)), project_relative(project_root, router._pm_prior_path_context_path(run_root))], allowed_writes=[project_relative(project_root, router._role_recovery_report_path(run_root)), project_relative(project_root, router._role_recovery_dir(run_root)), project_relative(project_root, run_root / 'continuation' / 'crew_rehydration_report.json'), project_relative(project_root, _controller_action_ledger_path(run_root)), project_relative(project_root, _router_scheduler_ledger_path(run_root)), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'role_recovery_roles_restored', 'role_recovery_transaction': transaction, 'target_role_keys': list(transaction.get('target_role_keys') or []), 'recovery_ladder': transaction.get('recovery_ladder') or [], 'payload_contract': router._role_recovery_payload_contract(run_root, run_state, transaction), 'background_role_agent_model_policy': {'model_policy': BACKGROUND_ROLE_MODEL_POLICY, 'reasoning_effort_policy': BACKGROUND_ROLE_REASONING_EFFORT_POLICY, 'preferred_reasoning_effort': BACKGROUND_ROLE_PREFERRED_REASONING_EFFORT, 'inherit_foreground_model_allowed': False}, 'role_recovery_request': [{**router._resume_role_context(project_root, run_root, run_state, role), 'recovery_transaction_id': transaction.get('transaction_id'), 'recovery_scope': transaction.get('recovery_scope'), 'old_agent_id': _active_agent_id_for_role(run_root, role), 'restore_first_required': True, 'packet_ownership_reconciliation_required': True, 'superseded_agent_output_quarantine_required': True} for role in transaction.get('target_role_keys') or [] if role in CREW_ROLE_KEYS], 'full_crew_recycle_scope_if_escalated': list(CREW_ROLE_KEYS), 'controller_visibility': 'state_and_envelopes_only', 'sealed_body_reads_allowed': False, 'chat_history_progress_inference_allowed': False, 'normal_waits_allowed_before_recovery': False, 'mechanical_obligation_replay_after_recovery': True, 'pm_decision_required_after_recovery': False, 'pm_escalation_only_for_semantic_ambiguity': True})
    return None

def _next_startup_heartbeat_binding_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    answers = router._startup_answers_from_run(run_root)
    if not router._scheduled_continuation_requested(answers):
        return None
    if run_state['flags'].get('continuation_binding_recorded') and router._host_heartbeat_binding_ready(run_root, run_state):
        return None
    if not run_state['flags'].get('controller_core_loaded'):
        return None
    automation_id_hint = f"flowpilot-{run_state['run_id']}-heartbeat"
    automation_name = f"FlowPilot {run_state['run_id']} heartbeat"
    prompt = _startup_heartbeat_prompt(project_root, str(run_state['run_id']))
    return make_action(action_type='create_heartbeat_automation', actor='bootloader', label='host_bootstraps_startup_heartbeat_automation', summary='Create the one-minute Codex heartbeat for the current run after Controller core handoff and before startup review.', allowed_reads=['.flowpilot/current.json', project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, router._continuation_binding_path(run_root))], allowed_writes=[project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'continuation_binding_recorded', 'requires_host_automation': True, 'host_tool': 'codex_app.automation_update', 'automation_update_request': {'mode': 'create', 'kind': 'heartbeat', 'destination': 'thread', 'name': automation_name, 'prompt': prompt, 'rrule': 'FREQ=MINUTELY;INTERVAL=1', 'status': 'ACTIVE'}, 'expected_payload': {'route_heartbeat_interval_minutes': 1, 'host_automation_id': automation_id_hint, 'host_automation_verified': True, 'host_automation_proof': {'source_kind': 'host_receipt', 'run_id': run_state['run_id'], 'host_automation_id': automation_id_hint, 'route_heartbeat_interval_minutes': 1, 'heartbeat_bound_to_current_run': True}}, 'payload_contract': _heartbeat_payload_contract(run_state['run_id'], automation_id_hint), 'proof_required_before_controller_receipt': True})

__all__ = (
    '_next_resume_action',
    '_next_role_recovery_action',
    '_next_startup_heartbeat_binding_action',
)
