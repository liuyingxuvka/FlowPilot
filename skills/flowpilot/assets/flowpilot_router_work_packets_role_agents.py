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


def _current_role_agent_payload_contract_for_packet(run_state: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        'schema_version': 'flowpilot.current_role_agent_payload_contract.v1',
        'payload_key': 'current_role_agent_binding',
        'required_fields': [
            'runtime_role_assistance_capability_status',
            'current_role_agent_binding.role_key',
            'current_role_agent_binding.agent_id',
            'current_role_agent_binding.model_policy',
            'current_role_agent_binding.reasoning_effort_policy',
            'current_role_agent_binding.binding_open_result',
            'current_role_agent_binding.opened_for_run_id',
            'current_role_agent_binding.host_liveness_status',
            'current_role_agent_binding.liveness_decision',
        ],
        'allowed_values': {
            'runtime_role_assistance_capability_status': ['available'],
            'current_role_agent_binding.role_key': [role],
            'current_role_agent_binding.model_policy': [ROLE_BINDING_MODEL_POLICY],
            'current_role_agent_binding.reasoning_effort_policy': [ROLE_BINDING_REASONING_EFFORT_POLICY],
            'current_role_agent_binding.binding_open_result': ['opened_for_current_packet'],
            'current_role_agent_binding.opened_for_run_id': [str(run_state.get('run_id') or '')],
            'current_role_agent_binding.host_liveness_status': ['active'],
            'current_role_agent_binding.liveness_decision': ['confirmed_existing_agent'],
        },
    }
def _missing_active_holder_roles(active_holder_plan: dict[str, Any] | None) -> list[str]:
    if not isinstance(active_holder_plan, dict):
        return []
    packets = active_holder_plan.get('packets')
    if not isinstance(packets, list):
        return []
    roles: list[str] = []
    for item in packets:
        if not isinstance(item, dict):
            continue
        role = str(item.get('holder_role') or '').strip()
        if role and role in RUNTIME_ROLE_KEYS and not str(item.get('target_agent_id') or '').strip():
            roles.append(role)
    return list(dict.fromkeys(roles))
def _open_current_role_agent_for_packet_plan(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    active_holder_plan: dict[str, Any] | None,
    *,
    packet_family: str,
    next_action_type: str,
) -> dict[str, Any] | None:
    _bind_router(router)
    missing_roles = _missing_active_holder_roles(active_holder_plan)
    if not missing_roles:
        return None
    role = missing_roles[0]
    safe_role = _safe_delivery_component(role)
    packet_ids = [
        str(item.get('packet_id') or '')
        for item in active_holder_plan.get('packets', [])  # type: ignore[union-attr]
        if isinstance(item, dict) and str(item.get('holder_role') or '').strip() == role and str(item.get('packet_id') or '').strip()
    ]
    return make_action(
        action_type='open_current_role_agent',
        actor='host',
        label=f'host_opens_current_role_agent_for_{safe_role}_before_{packet_family}_packet_relay',
        summary=f'Open or attach the current-run background agent for {role} before relaying {packet_family} packets.',
        allowed_reads=[
            project_relative(project_root, router.run_state_path(run_root)),
            project_relative(project_root, run_root / 'startup_answers.json'),
            project_relative(project_root, run_root / 'runtime_kit' / 'cards' / 'roles'),
            project_relative(project_root, run_root / 'role_binding_ledger.json'),
        ],
        allowed_writes=[
            project_relative(project_root, router.run_state_path(run_root)),
            project_relative(project_root, run_root / 'role_binding_ledger.json'),
            project_relative(project_root, run_root / 'role_binding_memory' / f'{safe_role}.json'),
            project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
            project_relative(project_root, _role_io_protocol_receipt_dir(run_root)),
        ],
        to_role=role,
        extra={
            'target_role_key': role,
            'requires_host_role_binding': True,
            'requires_payload': 'current_role_agent_binding',
            'payload_contract': _current_role_agent_payload_contract_for_packet(run_state, role),
            'background_role_agent_model_policy': {
                'model_policy': ROLE_BINDING_MODEL_POLICY,
                'reasoning_effort_policy': ROLE_BINDING_REASONING_EFFORT_POLICY,
                'preferred_reasoning_effort': ROLE_BINDING_PREFERRED_REASONING_EFFORT,
                'inherit_foreground_model_allowed': False,
            },
            'role_binding_open_policy': 'open_only_current_role_for_current_packet',
            'required_before_action_type': next_action_type,
            'required_before_packet_family': packet_family,
            'required_before_packet_ids': packet_ids,
            'active_holder_fast_lane': active_holder_plan,
            'controller_visibility': 'state_and_envelopes_only',
            'sealed_body_reads_allowed': False,
            'chat_history_progress_inference_allowed': False,
        },
    )

__all__ = (
    '_current_role_agent_payload_contract_for_packet',
    '_missing_active_holder_roles',
    '_open_current_role_agent_for_packet_plan',
)

_LOCAL_NAMES = set(globals())
