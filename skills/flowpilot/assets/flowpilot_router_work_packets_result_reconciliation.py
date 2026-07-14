"""Ordinary research result reconciliation for FlowPilot work packets."""

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

_PACKET_FAMILY_RESULT_RECONCILIATION = {
    'research': {
        'event': 'worker_research_report_returned',
        'index_label': 'research',
        'relayed_flag': 'research_packet_relayed',
        'required_flag': 'worker_research_report_card_delivered',
        'next_recipient': 'project_manager',
    },
}


def _packet_family_index_path(router: ModuleType, run_root: Path, batch_kind: str) -> Path:
    _bind_router(router)
    if batch_kind == 'research':
        return router._research_packet_index_path(run_root)
    raise RouterError(f'unsupported packet family result reconciliation kind: {batch_kind}')
def _reconciled_packet_family_result_payload(batch_kind: str, index: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    packets = [record for record in index.get('packets') or [] if isinstance(record, dict)]
    payload: dict[str, Any] = {
        'packet_ids': [record.get('packet_id') for record in packets],
        'batch_id': summary.get('batch_id') or index.get('batch_id'),
        'results_returned': summary.get('results_returned'),
        'reconciled_from_result_envelopes': True,
    }
    if batch_kind == 'research':
        completed_roles = sorted({str(record.get('to_role')) for record in packets if record.get('to_role')})
        payload.update({
            'completed_by_roles': completed_roles,
            'completed_by_role': ','.join(completed_roles),
            'answers_decision_question': True,
            'answers_decision_question_source': 'durable_result_envelope_returned_pm_review_required',
        })
    return payload
def _try_reconcile_packet_family_results(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    batch_kind: str,
) -> bool:
    _bind_router(router)
    config = _PACKET_FAMILY_RESULT_RECONCILIATION[batch_kind]
    flags = run_state.get('flags') if isinstance(run_state.get('flags'), dict) else {}
    event = str(config['event'])
    event_flag = str(EXTERNAL_EVENTS[event]['flag'])
    if flags.get(event_flag) or not flags.get(str(config['relayed_flag'])):
        return False
    required_flag = str(config.get('required_flag') or '')
    if required_flag and not flags.get(required_flag):
        return False
    index = router._load_packet_index(_packet_family_index_path(router, run_root, batch_kind), label=str(config['index_label']))
    summary = router._refresh_parallel_packet_batch_from_durable_results(project_root, run_root, run_state, batch_kind)
    if not summary.get('all_results_returned'):
        return bool(summary.get('changed'))
    try:
        router._validate_results_exist_for_packets(project_root, run_state, index['packets'], next_recipient=str(config['next_recipient']))
    except (RouterError, packet_runtime.PacketRuntimeError):
        return bool(summary.get('changed'))
    payload = _reconciled_packet_family_result_payload(batch_kind, index, summary)
    if batch_kind == 'research':
        try:
            router._write_worker_research_report(project_root, run_root, run_state, payload)
        except (RouterError, packet_runtime.PacketRuntimeError):
            return bool(summary.get('changed'))
    return _record_router_reconciled_external_event(project_root, run_root, run_state, event, payload) or bool(summary.get('changed'))
def _try_reconcile_research_results(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> bool:
    return _try_reconcile_packet_family_results(router, project_root, run_root, run_state, 'research')

__all__ = (
    '_try_reconcile_research_results',
)

_LOCAL_NAMES = set(globals())
