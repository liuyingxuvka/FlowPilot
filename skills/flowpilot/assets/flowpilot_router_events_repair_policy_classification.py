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
    if 'runtime ledger write is still in progress' in lowered or 'active runtime json write lock' in lowered:
        return False
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

__all__ = (
    '_infer_responsible_role',
    '_classify_control_blocker',
    '_should_materialize_control_blocker',
    '_skill_observation_reminder',
)

_LOCAL_NAMES = set(globals())
