"""Durable wait evidence reconciliation helper."""

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
    if _BOUND_ROUTER is router:
        return
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
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER


OWNER_MODULE = "flowpilot_router_system_cards"



def _reconcile_durable_wait_evidence(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    batch_reconciliation = _refresh_all_parallel_packet_batches_from_durable_results(project_root, run_root, run_state)
    changed = bool(batch_reconciliation.get("changed"))
    direct_role_output_reconciliation = _try_reconcile_direct_role_output_event_ledger(project_root, run_root, run_state)
    changed = bool(direct_role_output_reconciliation.get("changed")) or changed
    changed = _try_reconcile_material_scan_body_delivery(project_root, run_root, run_state) or changed
    changed = _try_reconcile_material_scan_results(project_root, run_root, run_state) or changed
    changed = _try_reconcile_research_results(project_root, run_root, run_state) or changed
    changed = _try_reconcile_current_node_results(project_root, run_root, run_state) or changed
    changed = _try_reconcile_pm_role_work_results(project_root, run_root, run_state) or changed
    if changed:
        run_state["parallel_batch_reconciliation"] = batch_reconciliation
        append_history(
            run_state,
            "router_reconciled_durable_wait_evidence",
            {
                "changed": changed,
                "controller_visibility": "metadata_only",
                "batches": batch_reconciliation.get("batches"),
                "direct_role_output_reconciliation": direct_role_output_reconciliation,
            },
        )
    return {
        **batch_reconciliation,
        "changed": changed,
        "direct_role_output_reconciliation": direct_role_output_reconciliation,
    }


__all__ = (
    '_reconcile_durable_wait_evidence',
)

_LOCAL_NAMES = set(globals())
