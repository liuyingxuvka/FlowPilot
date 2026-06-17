"""Focused child helpers for FlowPilot router work-packet next actions."""

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

import flowpilot_router_work_packets_role_agents as _role_agents
from flowpilot_router_work_packets_role_agents import _open_current_role_agent_for_packet_plan


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
    _role_agents._bind_router(router)


def _next_research_packet_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if flags.get('research_capability_decision_recorded') and (not flags.get('research_packet_relayed')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        active_holder_plan, active_holder_allowed_writes = router._packet_active_holder_lease_plan(project_root, run_root, run_state, index['packets'], packet_family='research', mode='lease_on_research_packet_relay')
        role_binding_action = _open_current_role_agent_for_packet_plan(router, project_root, run_root, run_state, active_holder_plan, packet_family='research', next_action_type='relay_research_packet')
        if role_binding_action:
            return role_binding_action
        runtime_relay_operations = router._packet_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='research', postcondition='research_packet_relayed', active_holder_plan=active_holder_plan)
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker_with_ledger_check', summary='Check the packet ledger and relay research packet envelope to the requested worker without opening the body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_research_packet', actor='controller', label='research_packet_relayed_to_worker', summary='Relay research batch packet envelopes without opening their bodies.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json'), *active_holder_allowed_writes], to_role=','.join(sorted({str(record.get('to_role') or 'worker') for record in index['packets']})), extra={'postcondition': 'research_packet_relayed', 'controller_visibility': 'packet_envelope_only', 'sealed_body_reads_allowed': False, 'active_holder_fast_lane': active_holder_plan, 'runtime_relay_operations': runtime_relay_operations})
    if flags.get('research_packet_relayed') and flags.get('worker_research_report_card_delivered') and (not flags.get('worker_research_report_returned')):
        summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, 'research')
        if summary.get('partial_results_returned'):
            missing_roles = [str(role) for role in summary.get('missing_roles') or [] if role]
            return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_remaining_research_batch_results', summary='Controller has some research result envelopes and must wait only for the missing batch member(s).', allowed_external_events=['worker_research_report_returned'], to_role=','.join(missing_roles) if missing_roles else 'worker', allowed_reads_extra=[project_relative(project_root, router._parallel_packet_batch_path(run_root, str(summary.get('batch_id'))))] if summary.get('batch_id') else None, payload_contract={'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'name': 'research_partial_batch_result', 'required_fields': ['packet_id', 'result_envelope_path', 'answers_decision_question'], 'batch_id': summary.get('batch_id'), 'batch_join_policy': 'all_results_before_pm_absorption', 'packet_count': summary.get('packet_count'), 'results_returned': summary.get('results_returned'), 'missing_roles': missing_roles, 'controller_visibility': 'metadata_only'}, producer_roles_override=missing_roles)
    if flags.get('worker_research_report_returned') and (not flags.get('research_result_relayed_to_pm')):
        index = router._load_packet_index(router._research_packet_index_path(run_root), label='research')
        runtime_relay_operations = router._result_runtime_relay_operations(project_root, run_state, index['packets'], packet_family='research', postcondition='research_result_relayed_to_pm', to_role='project_manager')
        if not run_state.get('ledger_check_requested'):
            return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm_with_ledger_check', summary='Check the packet ledger and relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, run_root / 'packet_ledger.json'), project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, router.run_state_path(run_root)), project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'combined_ledger_check_and_relay': True, 'ledger_check_receipt_required': True, 'packet_ids': [record.get('packet_id') for record in index['packets']], 'runtime_relay_operations': runtime_relay_operations})
        return make_action(action_type='relay_research_result_to_pm', actor='controller', label='research_result_relayed_to_pm', summary='Relay research result envelope to PM without opening the result body.', allowed_reads=[project_relative(project_root, router._research_packet_index_path(run_root))], allowed_writes=[project_relative(project_root, run_root / 'packet_ledger.json')], to_role='project_manager', extra={'postcondition': 'research_result_relayed_to_pm', 'controller_visibility': 'result_envelope_only', 'sealed_body_reads_allowed': False, 'runtime_relay_operations': runtime_relay_operations})
    if flags.get('research_result_relayed_to_pm') and (not flags.get('research_result_disposition_recorded')):
        return _expected_role_decision_wait_action(project_root, run_state, run_root, label='controller_waits_for_pm_research_result_disposition', summary='Research results reached PM and Controller must wait for PM disposition before any reviewer direct-source gate.', allowed_external_events=['pm_records_research_result_disposition'], to_role='project_manager', payload_contract=pm_package_result_disposition_payload_contract('pm_research_result_disposition'))
    return None

__all__ = (
    '_next_research_packet_action',
)

_LOCAL_NAMES = set(globals())
