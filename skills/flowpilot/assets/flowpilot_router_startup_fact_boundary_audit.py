"""startup mechanical audit actions and context helpers for ``flowpilot_router_startup_fact_boundary``.

This child module is imported by the public facade and keeps
router binding behavior explicit for the startup StructureMesh split.
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


OWNER_MODULE = 'flowpilot_router_startup_fact_boundary'

def _write_startup_mechanical_audit(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], computed_checks: dict[str, bool]) -> dict[str, Any]:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    proof_path = _router_owned_check_proof_path(audit_path)
    evidence_paths = [run_root / 'startup_answers.json', project_root / '.flowpilot' / 'current.json', project_root / '.flowpilot' / 'index.json', run_root / 'crew_ledger.json', router._continuation_binding_path(run_root), router.run_state_path(run_root)]
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        evidence_paths.extend([startup_intake_context['record_path'], startup_intake_context['result_path'], startup_intake_context['receipt_path'], startup_intake_context['envelope_path'], startup_intake_context['body_path']])
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        evidence_paths.append(boundary_path)
    external_requirements = router._startup_external_fact_requirements(run_root, run_state)
    review_ownership = router._startup_fact_review_ownership(computed_checks, external_requirements)
    audit = {'schema_version': STARTUP_MECHANICAL_AUDIT_SCHEMA, 'run_id': run_state['run_id'], 'check_owner': 'flowpilot_router', 'mechanical_checks': computed_checks, 'mechanical_checks_passed': all(computed_checks.values()), 'router_replacement_scope': 'mechanical_only', 'self_attested_ai_claims_accepted_as_proof': False, 'fact_review_ownership': review_ownership, 'reviewer_required_external_facts': external_requirements, 'router_owned_check_proof_path': project_relative(project_root, proof_path), 'source_paths': [_evidence_path_record(project_root, path) for path in evidence_paths], 'written_at': utc_now()}
    if not review_ownership['all_required_facts_have_owner']:
        raise RouterError('startup fact ownership map left unowned requirements')
    write_json(audit_path, audit)
    proof_record = _write_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path, source_kind='router_computed', evidence_paths=evidence_paths)
    _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    audit['router_owned_check_proof'] = {'path': proof_record['proof_path'], 'schema_version': ROUTER_OWNED_CHECK_PROOF_SCHEMA}
    return audit

def _startup_mechanical_audit_context(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    audit_path = run_root / 'startup' / 'startup_mechanical_audit.json'
    if not audit_path.exists():
        return None
    audit = read_json_if_exists(audit_path)
    if audit.get('schema_version') != STARTUP_MECHANICAL_AUDIT_SCHEMA:
        return None
    if audit.get('run_id') != run_state.get('run_id'):
        return None
    try:
        proof = _validate_router_owned_check_proof(project_root, run_root, check_name='startup_mechanical_checks', audit_path=audit_path)
    except RouterError:
        return None
    proof_path = _router_owned_check_proof_path(audit_path)
    return {'audit': audit, 'audit_path': audit_path, 'audit_hash': packet_runtime.sha256_file(audit_path), 'proof': proof, 'proof_path': proof_path, 'proof_hash': packet_runtime.sha256_file(proof_path) if proof_path.exists() else None}

def _startup_mechanical_audit_action_extra(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    context = router._startup_mechanical_audit_context(project_root, run_root, run_state)
    if context is None:
        raise RouterError('startup mechanical audit must be written before reviewer startup fact card delivery')
    display_path = run_root / 'display' / 'display_surface.json'
    if not display_path.exists():
        raise RouterError('startup display-surface status must be written before reviewer startup fact card delivery')
    return {'startup_mechanical_audit_path': project_relative(project_root, context['audit_path']), 'startup_mechanical_audit_hash': context['audit_hash'], 'router_owned_check_proof_path': project_relative(project_root, context['proof_path']), 'router_owned_check_proof_hash': context['proof_hash'], 'startup_intake_record_path': router._optional_source_path(project_root, run_root / 'startup_intake' / 'startup_intake_record.json'), 'startup_display_surface_path': project_relative(project_root, display_path), 'startup_display_surface_hash': packet_runtime.sha256_file(display_path), 'reviewer_has_direct_display_evidence': True, 'router_computable_checks_already_enforced': True, 'reviewer_should_not_reprove_router_computable_checks': True, 'reviewer_required_external_facts': context['audit'].get('reviewer_required_external_facts') or [], 'router_replacement_scope': 'mechanical_only'}

def _next_startup_mechanical_audit_action(router: ModuleType, project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    _bind_router(router)
    flags = run_state['flags']
    if not flags.get('controller_role_confirmed'):
        return None
    if flags.get('startup_mechanical_audit_written') and router._startup_mechanical_audit_context(project_root, run_root, run_state):
        return None
    if router._controller_action_open_for(run_root, action_type='write_startup_mechanical_audit', postcondition='startup_mechanical_audit_written'):
        return None
    allowed_reads = [project_relative(project_root, run_root / 'startup_answers.json'), project_relative(project_root, project_root / '.flowpilot' / 'current.json'), project_relative(project_root, project_root / '.flowpilot' / 'index.json'), project_relative(project_root, run_root / 'crew_ledger.json'), project_relative(project_root, router._continuation_binding_path(run_root)), project_relative(project_root, router.run_state_path(run_root))]
    boundary_path = router._controller_boundary_confirmation_path(run_root)
    if boundary_path.exists():
        allowed_reads.append(project_relative(project_root, boundary_path))
    startup_intake_context = router._startup_intake_record_context(project_root, run_root, run_state)
    if startup_intake_context is not None:
        allowed_reads.extend([project_relative(project_root, startup_intake_context['record_path']), project_relative(project_root, startup_intake_context['result_path']), project_relative(project_root, startup_intake_context['receipt_path']), project_relative(project_root, startup_intake_context['envelope_path'])])
    return make_action(action_type='write_startup_mechanical_audit', actor='router', label='router_writes_startup_mechanical_audit', summary='Router writes the startup mechanical audit and proof before exposing the reviewer startup fact-check card.', allowed_reads=allowed_reads, allowed_writes=[project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json'), project_relative(project_root, run_root / 'startup' / 'startup_mechanical_audit.json.proof.json'), project_relative(project_root, router.run_state_path(run_root))], extra={'postcondition': 'startup_mechanical_audit_written', 'reviewer_card_waiting_for_audit': 'reviewer.startup_fact_check', 'router_replacement_scope': 'mechanical_only'})

__all__ = (
    '_write_startup_mechanical_audit',
    '_startup_mechanical_audit_context',
    '_startup_mechanical_audit_action_extra',
    '_next_startup_mechanical_audit_action',
)

_LOCAL_NAMES = set(globals())
