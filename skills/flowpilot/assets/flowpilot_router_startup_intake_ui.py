"""startup intake UI action contract helpers for ``flowpilot_router_startup_intake``.

This child module is imported by the compatibility facade and keeps
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


OWNER_MODULE = 'flowpilot_router_startup_intake'

def _normalize_startup_question_stop_boundary(router: ModuleType, state: dict[str, Any]) -> bool:
    _bind_router(router)
    if state.get('status') == 'startup_cancelled' or state.get('startup_state') == 'startup_cancelled':
        return False
    flags = state.setdefault('flags', {})
    if not flags.get('startup_questions_asked'):
        return False
    if flags.get('startup_answers_recorded') or state.get('startup_answers'):
        return False
    changed = False
    if not flags.get('startup_state_written_awaiting_answers'):
        flags['startup_state_written_awaiting_answers'] = True
        changed = True
    if not flags.get('dialog_stopped_for_answers'):
        flags['dialog_stopped_for_answers'] = True
        changed = True
    if state.get('startup_state') != 'awaiting_answers_stopped':
        state['startup_state'] = 'awaiting_answers_stopped'
        changed = True
    pending = state.get('pending_action')
    if isinstance(pending, dict) and pending.get('action_type') in {'write_startup_awaiting_answers_state', 'stop_for_startup_answers'}:
        state['pending_action'] = None
        append_history(state, 'startup_question_stop_boundary_normalized', {'cleared_pending_action': pending.get('action_type')})
        changed = True
    return changed

def _startup_intake_ui_launcher_ref(router: ModuleType, project_root: Path) -> str:
    _bind_router(router)
    launcher = Path(__file__).resolve().parent / 'ui' / 'startup_intake' / 'flowpilot_startup_intake.ps1'
    try:
        return project_relative(project_root, launcher)
    except RouterError:
        return str(launcher)

def _startup_intake_output_dir_ref(router: ModuleType, project_root: Path, state: dict[str, Any]) -> str:
    _bind_router(router)
    run_id = str(state.get('run_id') or router._create_run_id())
    output_dir = project_root / '.flowpilot' / 'bootstrap' / 'startup_intake' / run_id
    return project_relative(project_root, output_dir)

def _startup_intake_result_payload_contract(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    return {'schema_version': PAYLOAD_CONTRACT_SCHEMA, 'payload_key': 'startup_intake_result', 'required': True, 'expected_shape': {'startup_intake_result': {'result_path': '<path returned by the native startup intake UI>'}}, 'result_schema_version': STARTUP_INTAKE_RESULT_SCHEMA, 'receipt_schema_version': STARTUP_INTAKE_RECEIPT_SCHEMA, 'envelope_schema_version': STARTUP_INTAKE_ENVELOPE_SCHEMA, 'formal_launch_provenance': {'launch_mode': STARTUP_INTAKE_INTERACTIVE_LAUNCH_MODE, 'headless': False, 'formal_startup_allowed': True}, 'output_dir': router._startup_intake_output_dir_ref(project_root, state), 'controller_body_boundary': {'controller_may_read_body': False, 'body_text_must_not_be_in_payload': True, 'allowed_controller_view': 'result/envelope paths, body hash, startup answers, and status only'}}

def _startup_intake_ui_action_extra(router: ModuleType, project_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    _bind_router(router)
    launcher = router._startup_intake_ui_launcher_ref(project_root)
    output_dir = router._startup_intake_output_dir_ref(project_root, state)
    command = ['powershell', '-STA', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', launcher, '-OutputDir', output_dir]
    return {'startup_intake_ui': {'schema_version': 'flowpilot.startup_intake_ui_launcher.v1', 'launcher_path': launcher, 'output_dir': output_dir, 'command': command, 'result_path_expected': f'{output_dir}/startup_intake_result.json', 'body_text_is_never_router_payload': True, 'cancel_result_is_terminal': True, 'headless_result_is_not_formal_startup': True}, 'payload_contract': router._startup_intake_result_payload_contract(project_root, state), 'plain_instruction': "Open the native FlowPilot startup intake UI with the provided command. Formal startup must use the interactive native UI result; do not use headless auto-confirmation, scripted result synthesis, chat substitution, or direct JSON creation. After the UI closes, return to Router daemon status and the Controller action ledger before continuing. Do not paste the user's work request into chat and do not include it in the Router payload."}

def _confirmed_startup_intake(router: ModuleType, state: dict[str, Any]) -> dict[str, Any] | None:
    _bind_router(router)
    intake = state.get('startup_intake')
    if isinstance(intake, dict) and intake.get('status') == 'confirmed':
        return intake
    return None

__all__ = (
    '_normalize_startup_question_stop_boundary',
    '_startup_intake_ui_launcher_ref',
    '_startup_intake_output_dir_ref',
    '_startup_intake_result_payload_contract',
    '_startup_intake_ui_action_extra',
    '_confirmed_startup_intake',
)

_LOCAL_NAMES = set(globals())
