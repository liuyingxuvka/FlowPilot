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

def _gate_decision_issue(router: ModuleType, field: str, message: str, owner: str='gate_owner') -> dict[str, str]:
    _bind_router(router)
    return {'field': field, 'message': message, 'owner': owner}

def _gate_decision_safe_id(router: ModuleType, raw: str) -> str:
    _bind_router(router)
    chars: list[str] = []
    for char in raw.strip().lower():
        if char.isalnum():
            chars.append(char)
        elif chars and chars[-1] != '-':
            chars.append('-')
    safe = ''.join(chars).strip('-')
    return safe[:96] or 'gate-decision'

def _gate_decision_issues(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> list[dict[str, str]]:
    _bind_router(router)
    issues: list[dict[str, str]] = []
    if not isinstance(decision, dict):
        return [router._gate_decision_issue('gate_decision', 'GateDecision must be a JSON object')]
    for field in GATE_DECISION_REQUIRED_FIELDS:
        if field not in decision or decision.get(field) in (None, ''):
            issues.append(router._gate_decision_issue(field, 'missing required GateDecision field'))
    if decision.get('gate_decision_version') != GATE_DECISION_SCHEMA:
        issues.append(router._gate_decision_issue('gate_decision_version', f'must equal {GATE_DECISION_SCHEMA}'))
    enum_specs = (('gate_kind', GATE_DECISION_ALLOWED_KINDS), ('owner_role', GATE_DECISION_ALLOWED_OWNER_ROLES), ('risk_type', GATE_DECISION_ALLOWED_RISKS), ('gate_strength', GATE_DECISION_ALLOWED_STRENGTHS), ('decision', GATE_DECISION_ALLOWED_DECISIONS), ('next_action', GATE_DECISION_ALLOWED_NEXT_ACTIONS))
    for field, allowed in enum_specs:
        if field in decision and decision.get(field) not in allowed:
            issues.append(router._gate_decision_issue(field, f'unsupported value: {decision.get(field)}'))
    leaked_overreach = sorted(GATE_DECISION_SEMANTIC_OVERREACH_FIELDS & set(decision))
    if leaked_overreach:
        issues.append(router._gate_decision_issue(','.join(leaked_overreach), 'router may record only mechanical GateDecision conformance, not semantic sufficiency', 'flowpilot_router'))
    if 'blocking' in decision and (not isinstance(decision.get('blocking'), bool)):
        issues.append(router._gate_decision_issue('blocking', 'must be a boolean'))
    required_evidence = decision.get('required_evidence')
    if not isinstance(required_evidence, list) or any((not isinstance(item, str) for item in required_evidence)):
        issues.append(router._gate_decision_issue('required_evidence', 'must be a list of strings'))
    evidence_refs = decision.get('evidence_refs')
    if not isinstance(evidence_refs, list):
        issues.append(router._gate_decision_issue('evidence_refs', 'must be a list of evidence reference objects'))
        evidence_refs = []
    reason = str(decision.get('reason') or '').strip()
    if not reason:
        issues.append(router._gate_decision_issue('reason', 'GateDecision requires a concrete reason'))
    contract_self_check = decision.get('contract_self_check')
    if contract_self_check is not None:
        if not isinstance(contract_self_check, dict):
            issues.append(router._gate_decision_issue('contract_self_check', 'must be an object when provided'))
        else:
            if contract_self_check.get('all_required_fields_present') is not True:
                issues.append(router._gate_decision_issue('contract_self_check.all_required_fields_present', 'must be true'))
            if contract_self_check.get('exact_field_names_used') is not True:
                issues.append(router._gate_decision_issue('contract_self_check.exact_field_names_used', 'must be true'))
    gate_strength = decision.get('gate_strength')
    gate_decision = decision.get('decision')
    blocking = decision.get('blocking')
    next_action = decision.get('next_action')
    if gate_decision == 'pass':
        if blocking is not False:
            issues.append(router._gate_decision_issue('blocking', 'pass decisions must not be blocking'))
        if next_action != 'continue':
            issues.append(router._gate_decision_issue('next_action', 'pass decisions must route to continue'))
        if gate_strength == 'hard' and (not evidence_refs):
            issues.append(router._gate_decision_issue('evidence_refs', 'hard pass decisions require evidence references'))
    elif gate_decision == 'block':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'block decisions must be blocking'))
    elif gate_decision in {'waive', 'skip'}:
        if blocking is not False:
            issues.append(router._gate_decision_issue('blocking', 'waive and skip decisions must not be blocking'))
        if next_action != 'continue':
            issues.append(router._gate_decision_issue('next_action', 'waive and skip decisions must route to continue'))
    elif gate_decision == 'repair_local':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'repair_local decisions must be blocking until repaired'))
        if next_action not in {'local_repair', 'reviewer_recheck', 'collect_evidence'}:
            issues.append(router._gate_decision_issue('next_action', 'repair_local requires a local repair, recheck, or evidence collection action'))
    elif gate_decision == 'mutate_route':
        if blocking is not True:
            issues.append(router._gate_decision_issue('blocking', 'mutate_route decisions must be blocking until route mutation'))
        if next_action != 'route_mutation':
            issues.append(router._gate_decision_issue('next_action', 'mutate_route decisions must route to route_mutation'))
    if gate_strength == 'advisory' and blocking is True:
        issues.append(router._gate_decision_issue('blocking', 'advisory gates cannot block'))
    if gate_strength == 'skip_with_reason' and gate_decision not in {'skip', 'waive'}:
        issues.append(router._gate_decision_issue('decision', 'skip_with_reason gates require skip or waive decision'))
    for index, evidence in enumerate(evidence_refs):
        prefix = f'evidence_refs[{index}]'
        if not isinstance(evidence, dict):
            issues.append(router._gate_decision_issue(prefix, 'evidence reference must be an object'))
            continue
        kind = evidence.get('kind')
        if kind not in GATE_DECISION_ALLOWED_EVIDENCE_KINDS:
            issues.append(router._gate_decision_issue(f'{prefix}.kind', f'unsupported evidence kind: {kind}'))
            continue
        summary = str(evidence.get('summary') or '').strip()
        if not summary:
            issues.append(router._gate_decision_issue(f'{prefix}.summary', 'evidence reference requires summary'))
        if kind == 'none':
            continue
        raw_path = str(evidence.get('path') or '').strip()
        raw_hash = str(evidence.get('hash') or '').strip()
        if not raw_path:
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'non-none evidence requires path'))
            continue
        if not raw_hash:
            issues.append(router._gate_decision_issue(f'{prefix}.hash', 'non-none evidence requires hash'))
            continue
        evidence_path = resolve_project_path(project_root, raw_path)
        try:
            project_relative(project_root, evidence_path)
        except RouterError:
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'evidence path must stay inside the project root'))
            continue
        if not evidence_path.exists() or not evidence_path.is_file():
            issues.append(router._gate_decision_issue(f'{prefix}.path', 'evidence path is missing'))
            continue
        actual_hash = packet_runtime.sha256_file(evidence_path)
        if raw_hash != actual_hash:
            issues.append(router._gate_decision_issue(f'{prefix}.hash', 'evidence hash does not match path content'))
    return issues

def _validate_gate_decision(router: ModuleType, project_root: Path, decision: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    issues = router._gate_decision_issues(project_root, decision)
    if issues:
        first = issues[0]
        raise RouterError(f"GateDecision mechanical validation failed: {first['field']}: {first['message']}")
    return decision

def _gate_decision_record_path(router: ModuleType, run_root: Path, gate_id: str) -> Path:
    _bind_router(router)
    return run_root / 'gate_decisions' / f'{router._gate_decision_safe_id(gate_id)}.json'

def _gate_decision_summary(router: ModuleType, project_root: Path, record_path: Path, decision: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'gate_id': str(decision['gate_id']), 'gate_kind': decision['gate_kind'], 'owner_role': decision['owner_role'], 'risk_type': decision['risk_type'], 'gate_strength': decision['gate_strength'], 'decision': decision['decision'], 'blocking': decision['blocking'], 'next_action': decision['next_action'], 'decision_path': project_relative(project_root, record_path)}

def _write_gate_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> None:
    _bind_router(router)
    decision = _load_file_backed_role_payload(project_root, payload)
    router._validate_gate_decision(project_root, decision)
    gate_id = str(decision['gate_id'])
    record_path = router._gate_decision_record_path(run_root, gate_id)
    record = {'schema_version': GATE_DECISION_RECORD_SCHEMA, 'run_id': run_state['run_id'], 'recorded_at': utc_now(), 'recorded_by_event': GATE_DECISION_EVENT, 'gate_decision': decision, **_role_output_envelope_record(decision)}
    write_json(record_path, record)
    summary = router._gate_decision_summary(project_root, record_path, decision)
    decisions = run_state.setdefault('gate_decisions', [])
    if not isinstance(decisions, list):
        decisions = []
        run_state['gate_decisions'] = decisions
    decisions[:] = [item for item in decisions if item.get('gate_id') != gate_id]
    decisions.append(summary)
    ledger_path = run_root / 'gate_decisions' / 'gate_decision_ledger.json'
    write_json(ledger_path, {'schema_version': GATE_DECISION_LEDGER_SCHEMA, 'run_id': run_state['run_id'], 'updated_at': utc_now(), 'gate_decision_count': len(decisions), 'gate_decisions': decisions})

__all__ = (
    '_gate_decision_issue',
    '_gate_decision_safe_id',
    '_gate_decision_issues',
    '_validate_gate_decision',
    '_gate_decision_record_path',
    '_gate_decision_summary',
    '_write_gate_decision',
)

_LOCAL_NAMES = set(globals())
