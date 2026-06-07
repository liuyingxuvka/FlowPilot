"""Public facade for startup helpers split from ``flowpilot_router_startup_flow``.

The implementation lives in focused child modules and keeps router-binding
handoff explicit for the startup mechanical boundary.
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


OWNER_MODULE = 'flowpilot_router_startup_mechanical_boundary'

import flowpilot_router_startup_mechanical_boundary_checks as _flowpilot_router_startup_mechanical_boundary_checks
from flowpilot_router_startup_mechanical_boundary_checks import (
    _startup_mechanical_checks,
    _startup_intake_record_context,
    _startup_mechanical_required_evidence,
    _startup_mechanical_ownership,
)
import flowpilot_router_startup_mechanical_boundary_controller as _flowpilot_router_startup_mechanical_boundary_controller
from flowpilot_router_startup_mechanical_boundary_controller import (
    _controller_boundary_confirmation_path,
    _run_manifest_path,
    _controller_boundary_sources,
    _controller_boundary_constraints,
    _pm_reset_boundary_confirmed,
    _controller_boundary_confirmation_body,
    _controller_boundary_runtime_evidence_context,
    _write_controller_boundary_confirmation,
    _record_controller_boundary_confirmation_from_core_load,
    _controller_boundary_confirmation_context,
    _next_controller_boundary_confirmation_action,
)
import flowpilot_router_startup_mechanical_boundary_audit as _flowpilot_router_startup_mechanical_boundary_audit
from flowpilot_router_startup_mechanical_boundary_audit import (
    _write_startup_mechanical_audit,
    _startup_mechanical_audit_context,
    _startup_mechanical_audit_action_extra,
    _next_startup_mechanical_audit_action,
)

_CHILD_MODULES = (
    _flowpilot_router_startup_mechanical_boundary_checks,
    _flowpilot_router_startup_mechanical_boundary_controller,
    _flowpilot_router_startup_mechanical_boundary_audit,
)

def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
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
    *_flowpilot_router_startup_mechanical_boundary_checks.__all__,
    *_flowpilot_router_startup_mechanical_boundary_controller.__all__,
    *_flowpilot_router_startup_mechanical_boundary_audit.__all__,
)

_LOCAL_NAMES = set(globals())
