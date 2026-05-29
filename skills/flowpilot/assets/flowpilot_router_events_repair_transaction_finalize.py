"""Coarse events repair owner helpers for the FlowPilot router.

The public router names stay in `flowpilot_router`. This module owns a
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

def _clear_successful_repair_lane_state(router: ModuleType, run_state: dict[str, Any], transaction: dict[str, Any], *, event: str) -> None:
    _bind_router(router)
    rerun_target = str(transaction.get('rerun_target') or '')
    is_material_repair = event in MATERIAL_REPAIR_OUTCOME_EVENTS or rerun_target in MATERIAL_REPAIR_OUTCOME_EVENTS
    flags = run_state.get('flags')
    if isinstance(flags, dict) and is_material_repair:
        for flag in MATERIAL_REPAIR_RECHECK_FLAGS:
            flags[flag] = False
        if event == 'router_direct_material_scan_dispatch_recheck_passed':
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
    producer_role = ''
    if isinstance(payload, dict):
        producer_role = str(payload.get('from_role') or payload.get('reviewed_by_role') or payload.get('completed_by_role') or payload.get('decided_by_role') or '').strip()
    if not producer_role:
        producer_role = str((EXTERNAL_EVENTS.get(event) or {}).get('role') or '').strip()
    repair_recheck = {'outcome': outcome_kind, 'event': event, 'producer_role': producer_role or 'event_producer', 'payload_envelope_public_view': router._control_payload_public_view(payload), 'recorded_at': now}
    transaction['repair_recheck'] = repair_recheck
    transaction['reviewer_recheck'] = repair_recheck
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
    followup = router._write_control_blocker(project_root, run_root, run_state, source='repair_transaction_recheck', error_message=f"repair transaction {transaction.get('transaction_id')} ended with {repair_recheck['producer_role']} outcome {outcome_kind}; PM repair or routing decision is required before retrying dispatch.", event=event, payload=payload)
    transaction['followup_blocker_id'] = followup.get('blocker_id')
    transaction['followup_blocker_path'] = followup.get('blocker_artifact_path')
    write_json(tx_path, transaction)
    router._write_repair_transaction_index(project_root, run_root, run_state)
    return {'transaction_id': transaction.get('transaction_id'), 'outcome': outcome_kind, 'status': 'blocked', 'followup_blocker_id': followup.get('blocker_id')}

__all__ = (
    '_clear_successful_repair_lane_state',
    '_finalize_repair_transaction_outcome',
)

_LOCAL_NAMES = set(globals())
