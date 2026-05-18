"""Coarse work packets owner helpers for the FlowPilot router.

The public compatibility names stay in `flowpilot_router`. This module owns a
cohesive behavior family and receives the router facade as an explicit runtime
dependency so shared state writers and public entrypoints remain compatible.
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

_DEFAULT_SENTINEL = object()


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value
    for child_module in globals().get("_OWNER_CHILD_MODULES", ()):
        if hasattr(child_module, "_bind_router"):
            child_module._bind_router(router)

import flowpilot_router_work_packets_material as _owner_child_0
import flowpilot_router_work_packets_pm_role as _owner_child_1
import flowpilot_router_work_packets_current_node as _owner_child_2
import flowpilot_router_work_packets_parallel as _owner_child_3
import flowpilot_router_work_packets_next_actions as _owner_child_4
from flowpilot_router_work_packets_material import *
from flowpilot_router_work_packets_pm_role import *
from flowpilot_router_work_packets_current_node import *
from flowpilot_router_work_packets_parallel import *
from flowpilot_router_work_packets_next_actions import *

_OWNER_CHILD_MODULES = (
    _owner_child_0,
    _owner_child_1,
    _owner_child_2,
    _owner_child_3,
    _owner_child_4,
)

_LOCAL_NAMES = set(globals())
