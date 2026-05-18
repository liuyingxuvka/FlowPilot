"""Internal router owner helpers extracted from flowpilot_router.

The public compatibility names stay in flowpilot_router. This module is bound to
that facade before moved helpers execute so legacy private helper lookups remain
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
import flowpilot_router_protocol_catalog as _owner_child_0
import flowpilot_router_route_artifacts_architecture as _owner_child_1
import flowpilot_router_route_artifacts_planning as _owner_child_2
import flowpilot_router_route_artifacts_nodes as _owner_child_3
import flowpilot_router_route_artifacts_evidence as _owner_child_4
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
    for child_module in globals().get("_OWNER_CHILD_MODULES", ()):
        if hasattr(child_module, "_bind_router"):
            child_module._bind_router(router)


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER

OWNER_MODULE = "flowpilot_router_route_artifacts"

from flowpilot_router_route_artifacts_architecture import *
from flowpilot_router_route_artifacts_planning import *
from flowpilot_router_route_artifacts_nodes import *
from flowpilot_router_route_artifacts_evidence import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
    _owner_child_4,
)

_LOCAL_NAMES = set(globals())
