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
import flowpilot_router_self_interrogation_suggestions as _owner_child_0
import flowpilot_router_self_interrogation_records as _owner_child_1
import flowpilot_router_self_interrogation_proofs as _owner_child_2

_DEFAULT_SENTINEL = object()
_BOUND_ROUTER: ModuleType | None = None


OWNER_MODULE = "flowpilot_router_self_interrogation"

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
)


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
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

from flowpilot_router_self_interrogation_suggestions import (
    _pm_suggestion_ledger_path,
    _read_pm_suggestion_ledger,
    _pm_suggestion_ledger_status,
)

from flowpilot_router_self_interrogation_records import (
    _self_interrogation_index_path,
    _self_interrogation_issue,
    _self_interrogation_entry_path,
    _self_interrogation_final_status,
    _self_interrogation_record_issues,
    _self_interrogation_status,
    _format_self_interrogation_status_issue,
    _require_clean_self_interrogation,
    resolve_project_path,
)

from flowpilot_router_self_interrogation_proofs import (
    _evidence_path_record,
    _router_owned_check_proof_path,
    _write_router_owned_check_proof,
)

_LOCAL_NAMES = set(globals())
