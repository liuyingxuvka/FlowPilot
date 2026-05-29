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


OWNER_MODULE = 'flowpilot_router_startup_bootloader'

import flowpilot_router_startup_bootloader_progress as _flowpilot_router_startup_bootloader_progress
from flowpilot_router_startup_bootloader_progress import (
    _startup_bootloader_open_entries_by_action_type,
    _startup_open_entry_progress_class,
    _startup_bootloader_entry_is_nonblocking,
    _startup_bootloader_action_depends_on_role_slots,
    _next_boot_action,
    _bootstrap_startup_cancelled,
    _startup_bootloader_has_remaining_work,
    _startup_daemon_controls_bootstrap,
    _daemon_scheduled_bootloader_action,
    compute_bootloader_action,
)
import flowpilot_router_startup_bootloader_state as _flowpilot_router_startup_bootloader_state
from flowpilot_router_startup_bootloader_state import (
    _ensure_pending,
    _set_boot_flag,
    _startup_run_state_if_ready,
    _sync_startup_bootstrap_flags_to_run_state,
    _fold_stable_startup_role_flags_from_bootstrap,
)
import flowpilot_router_startup_bootloader_daemon as _flowpilot_router_startup_bootloader_daemon
from flowpilot_router_startup_bootloader_daemon import (
    _complete_startup_daemon_bootloader_row,
    _startup_daemon_schedule_bootloader_action,
)
import flowpilot_router_startup_bootloader_actions as _flowpilot_router_startup_bootloader_actions
from flowpilot_router_startup_bootloader_actions import (
    _finish_bootloader_action,
    apply_bootloader_action,
)

_CHILD_MODULES = (
    _flowpilot_router_startup_bootloader_progress,
    _flowpilot_router_startup_bootloader_state,
    _flowpilot_router_startup_bootloader_daemon,
    _flowpilot_router_startup_bootloader_actions,
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
    *_flowpilot_router_startup_bootloader_progress.__all__,
    *_flowpilot_router_startup_bootloader_state.__all__,
    *_flowpilot_router_startup_bootloader_daemon.__all__,
    *_flowpilot_router_startup_bootloader_actions.__all__,
)

_LOCAL_NAMES = set(globals())
