"""Compatibility facade for startup helpers split from ``flowpilot_router_startup_flow``.

The implementation lives in focused child modules. This facade preserves
the historical import path, public/private helper names, and router-binding
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


OWNER_MODULE = 'flowpilot_router_startup_intake'

import flowpilot_router_startup_intake_ui as _flowpilot_router_startup_intake_ui
from flowpilot_router_startup_intake_ui import (
    _normalize_startup_question_stop_boundary,
    _startup_intake_ui_launcher_ref,
    _startup_intake_output_dir_ref,
    _startup_intake_result_payload_contract,
    _startup_intake_ui_action_extra,
    _confirmed_startup_intake,
)
import flowpilot_router_startup_intake_validation as _flowpilot_router_startup_intake_validation
from flowpilot_router_startup_intake_validation import (
    _forbidden_startup_intake_body_fields,
    _resolve_existing_project_file,
    _same_project_file,
    _startup_intake_result_path_from_payload,
    _require_interactive_startup_intake_artifact,
    _validate_startup_intake_result_payload,
    _apply_startup_intake_result_to_bootstrap,
    _validate_startup_answer_interpretation,
    _validate_startup_answers,
    _validate_user_request,
)
import flowpilot_router_startup_intake_materialization as _flowpilot_router_startup_intake_materialization
from flowpilot_router_startup_intake_materialization import (
    _copy_startup_intake_file,
    _materialize_startup_intake_record,
    _user_request_ref_from_startup_intake,
    _build_user_intake_body_from_ref,
    _deterministic_bootstrap_seed_evidence_path,
    _flowguard_capability_snapshot_path,
    _portable_skill_search_roots,
    _flowguard_route_classification,
    _discover_flowguard_skill_routes,
    _flowguard_import_snapshot,
    _write_startup_answers_record,
    _initialize_mailbox_foundation,
    _record_startup_user_request_ref,
    _write_startup_user_intake_scaffold,
    _write_flowguard_capability_snapshot,
    _run_deterministic_startup_bootstrap_seed,
    _sync_completed_deterministic_startup_seed_to_bootstrap,
)

_CHILD_MODULES = (
    _flowpilot_router_startup_intake_ui,
    _flowpilot_router_startup_intake_validation,
    _flowpilot_router_startup_intake_materialization,
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
    *_flowpilot_router_startup_intake_ui.__all__,
    *_flowpilot_router_startup_intake_validation.__all__,
    *_flowpilot_router_startup_intake_materialization.__all__,
)

_LOCAL_NAMES = set(globals())
