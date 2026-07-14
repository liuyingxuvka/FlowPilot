"""Internal router owner helpers extracted from flowpilot_router.

The public router names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so private helper lookups remain
stable while the implementation body lives outside the facade.
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
import flowpilot_router_expected_waits_actions as _owner_child_0
import flowpilot_router_expected_waits_events as _owner_child_1
import flowpilot_router_expected_waits_reconciliation as _owner_child_2

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


OWNER_MODULE = "flowpilot_router_expected_waits"

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
)


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    for child_module in _OWNER_CHILD_MODULES:
        child_module._bind_router(router)
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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

from flowpilot_router_expected_waits_actions import (
    _next_model_miss_followup_request_wait_action,
    _next_model_miss_controlled_stop_action,
    _expected_role_decision_wait_action,
    _reconcile_router_internal_postconditions,
    _next_expected_role_decision_wait_action,
)

from flowpilot_router_expected_waits_events import (
    _event_is_router_internal_postcondition,
    _event_wait_role,
    _active_node_children_status,
    _event_applicable_for_active_node,
    _pending_expected_external_event_groups,
    _pending_role_decision_staleness,
    _run_state_has_event,
)

from flowpilot_router_expected_waits_reconciliation import (
    _reconcile_pending_role_wait_from_packet_status,
    _record_router_reconciled_external_event,
    _try_reconcile_research_results,
    _try_reconcile_current_node_results,
    _try_reconcile_pm_role_work_results,
)

_LOCAL_NAMES = set(globals())
