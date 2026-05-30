"""Public facade for startup helpers split from ``flowpilot_router_startup_flow``.

The implementation lives in focused child modules. This facade preserves
the router import path, public/private helper names, and router-binding
handoff used by the router skeleton.
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


OWNER_MODULE = 'flowpilot_router_startup_role_recovery'

import flowpilot_router_startup_role_transactions_core as _flowpilot_router_startup_role_transactions_core
from flowpilot_router_startup_role_transactions_core import (
    _reclaim_role_recovery_postcondition_from_report,
    _current_role_binding_generation,
    _open_role_recovery_transaction,
    _role_recovery_payload_contract,
    _load_role_recovery_state,
)
import flowpilot_router_startup_role_transactions_records as _flowpilot_router_startup_role_transactions_records
from flowpilot_router_startup_role_transactions_records import (
    _normalize_role_recovery_agent_records,
    _role_recovery_obligation_replay_path,
)
import flowpilot_router_startup_role_transactions_waits as _flowpilot_router_startup_role_transactions_waits
from flowpilot_router_startup_role_transactions_waits import (
    _controller_action_entry_view,
    _controller_action_wait_roles,
    _role_recovery_action_sort_key,
    _role_recovery_pending_return_for_action,
    _role_recovery_wait_candidates,
    _mark_controller_action_done_by_role_recovery,
    _role_recovery_existing_event_for_wait,
    _settle_role_recovery_candidate_if_evidence_exists,
)
import flowpilot_router_startup_role_transactions_replay as _flowpilot_router_startup_role_transactions_replay
from flowpilot_router_startup_role_transactions_replay import (
    _role_recovery_replacement_action,
    _supersede_role_recovery_original_wait,
    _plan_role_recovery_obligation_replay,
)

_CHILD_MODULES = (
    _flowpilot_router_startup_role_transactions_core,
    _flowpilot_router_startup_role_transactions_records,
    _flowpilot_router_startup_role_transactions_waits,
    _flowpilot_router_startup_role_transactions_replay,
)

def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    _BOUND_ROUTER = router
    for module in _CHILD_MODULES:
        module._bind_router(router)
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

__all__ = (
    '_reclaim_role_recovery_postcondition_from_report',
    '_current_role_binding_generation',
    '_open_role_recovery_transaction',
    '_role_recovery_payload_contract',
    '_load_role_recovery_state',
    '_normalize_role_recovery_agent_records',
    '_role_recovery_obligation_replay_path',
    '_controller_action_entry_view',
    '_controller_action_wait_roles',
    '_role_recovery_action_sort_key',
    '_role_recovery_pending_return_for_action',
    '_role_recovery_wait_candidates',
    '_mark_controller_action_done_by_role_recovery',
    '_role_recovery_existing_event_for_wait',
    '_settle_role_recovery_candidate_if_evidence_exists',
    '_role_recovery_replacement_action',
    '_supersede_role_recovery_original_wait',
    '_plan_role_recovery_obligation_replay',
)

_LOCAL_NAMES = set(globals())
