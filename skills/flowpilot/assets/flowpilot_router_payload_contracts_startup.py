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


def _bound_router() -> ModuleType:
    if _BOUND_ROUTER is None:
        raise RuntimeError("router facade is not bound")
    return _BOUND_ROUTER
OWNER_MODULE = "flowpilot_router_payload_contracts"
from flowpilot_router_payload_contracts_core import _payload_contract

def _terminal_summary_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="terminal_summary_markdown_and_user_display_receipt",
        required_object="payload",
        required_fields=[
            "summary_markdown",
            "displayed_to_user",
            "displayed_summary_sha256",
            "read_scope_used",
        ],
        optional_fields=["source_paths_reviewed"],
        allowed_values={
            "displayed_to_user": [True],
            "read_scope_used": [TERMINAL_SUMMARY_READ_SCOPE],
        },
        structural_requirements=[
            f"summary_markdown must start with this exact attribution line: {TERMINAL_SUMMARY_ATTRIBUTION}",
            "displayed_summary_sha256 must equal sha256(summary_markdown)",
            "source_paths_reviewed, when supplied, may cite only files inside the current run root",
            "Controller must show this same summary text to the user before writing the Controller receipt or applying the direct terminal action",
            "The final user report is output-only and does not create completion authority",
        ],
        description=(
            "Write the final FlowPilot run summary after terminal mode is reached. "
            "This is a terminal-only read exception for all files inside the current run root."
        ),
    )
def _display_surface_receipt_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="display_surface_receipt",
        required_object="payload.display_confirmation",
        required_fields=[
            "display_confirmation.action_type",
            "display_confirmation.display_kind",
            "display_confirmation.display_text_sha256",
            "display_confirmation.provenance",
            "display_confirmation.rendered_to",
        ],
        optional_fields=["payload.display_surface_receipt"],
        allowed_values={
            "display_confirmation.provenance": [DISPLAY_CONFIRMATION_PROVENANCE],
            "display_confirmation.rendered_to": [DISPLAY_CONFIRMATION_TARGET],
            "display_surface_receipt.schema_version": [DISPLAY_SURFACE_RECEIPT_SCHEMA],
            "display_surface_receipt.actual_surface": ["chat_route_sign", "chat_route_sign_fallback", "cockpit"],
            "display_surface_receipt.host_display_surface_verified": [True],
        },
        conditional_required_fields={
            "when payload.display_surface_receipt is supplied": [
                "display_surface_receipt.schema_version",
                "display_surface_receipt.actual_surface",
            ],
            "when display_surface_receipt.actual_surface=cockpit": [
                "display_surface_receipt.host_display_surface_verified",
            ],
        },
        description=(
            "Confirm the router-provided route sign was displayed in the user dialog. If a native Cockpit or "
            "fallback display was attempted, include display_surface_receipt with the actual surface and host result."
        ),
        reviewer_check="Reviewer checks requested cockpit versus actual cockpit/fallback reality when Cockpit was requested.",
    )
def _role_slots_payload_contract() -> dict[str, Any]:
    return _payload_contract(
        name="role_slots_startup_receipt",
        required_object="payload",
        required_fields=[
            "runtime_role_assistance_capability_status",
            "role_bindings[].role_key",
            "role_bindings[].agent_id",
            "role_bindings[].model_policy",
            "role_bindings[].reasoning_effort_policy",
            "role_bindings[].binding_open_result",
            "role_bindings[].opened_for_run_id",
            "role_bindings[].opened_after_startup_answers",
        ],
        optional_fields=["role_bindings[].host_role_binding_receipt"],
        allowed_values={
            "runtime_role_assistance_capability_status": ["available"],
            "role_bindings[].model_policy": [ROLE_BINDING_MODEL_POLICY],
            "role_bindings[].reasoning_effort_policy": [ROLE_BINDING_REASONING_EFFORT_POLICY],
            "role_bindings[].binding_open_result": [ROLE_BINDING_OPEN_RESULT],
            "role_bindings[].host_role_binding_receipt.source_kind": ["host_receipt"],
        },
        conditional_required_fields={
            "when role_bindings[].host_role_binding_receipt is supplied": [
                "role_bindings[].host_role_binding_receipt.source_kind",
                "role_bindings[].host_role_binding_receipt.opened_for_run_id",
                "role_bindings[].host_role_binding_receipt.role_key",
                "role_bindings[].host_role_binding_receipt.agent_id",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate role-binding record for each role key requested by the startup action.",
            "Each live role binding must use a host-supported, addressable, isolated role surface and must be explicitly requested with the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
        ],
        description="Record fresh live host role bindings when host-supported isolated role surfaces were allowed, using the strongest available role intelligence policy.",
        reviewer_check="Reviewer checks live role-binding freshness unless each slot carries a host receipt.",
    )
def _heartbeat_payload_contract(run_id: str, automation_id_hint: str) -> dict[str, Any]:
    return _payload_contract(
        name="heartbeat_host_automation_receipt",
        required_object="payload",
        required_fields=[
            "route_heartbeat_interval_minutes",
            "host_automation_id",
            "host_automation_verified",
            "host_automation_proof.source_kind",
            "host_automation_proof.run_id",
            "host_automation_proof.host_automation_id",
            "host_automation_proof.route_heartbeat_interval_minutes",
            "host_automation_proof.heartbeat_bound_to_current_run",
        ],
        allowed_values={
            "route_heartbeat_interval_minutes": [1],
            "host_automation_verified": [True],
            "host_automation_proof.source_kind": ["host_receipt"],
            "host_automation_proof.run_id": [run_id],
            "host_automation_proof.route_heartbeat_interval_minutes": [1],
            "host_automation_proof.heartbeat_bound_to_current_run": [True],
        },
        description="Bind the one-minute host heartbeat automation to this exact current run before startup fact review.",
        reviewer_check="Reviewer checks heartbeat host binding when scheduled continuation was requested.",
    )
def _resume_role_rehydration_payload_contract(
    run_state: dict[str, Any],
    contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    del contexts
    return _payload_contract(
        name="resume_role_rehydration_receipt",
        required_object="payload",
        required_fields=[
            "runtime_role_assistance_capability_status",
            "liveness_probe_batch_id",
            "liveness_probe_mode",
            "all_liveness_probes_started_before_wait",
            "rehydrated_role_bindings[].role_key",
            "rehydrated_role_bindings[].agent_id",
            "rehydrated_role_bindings[].model_policy",
            "rehydrated_role_bindings[].reasoning_effort_policy",
            "rehydrated_role_bindings[].rehydration_result",
            "rehydrated_role_bindings[].rehydrated_for_run_id",
            "rehydrated_role_bindings[].rehydrated_after_resume_tick_id",
            "rehydrated_role_bindings[].rehydrated_after_resume_state_loaded",
            "rehydrated_role_bindings[].core_prompt_path",
            "rehydrated_role_bindings[].core_prompt_hash",
            "rehydrated_role_bindings[].host_liveness_status",
            "rehydrated_role_bindings[].liveness_decision",
            "rehydrated_role_bindings[].resume_agent_attempted",
            "rehydrated_role_bindings[].bounded_wait_result",
            "rehydrated_role_bindings[].bounded_wait_ms",
            "rehydrated_role_bindings[].liveness_probe_batch_id",
            "rehydrated_role_bindings[].liveness_probe_mode",
            "rehydrated_role_bindings[].liveness_probe_started_at",
            "rehydrated_role_bindings[].liveness_probe_completed_at",
            "rehydrated_role_bindings[].wait_agent_timeout_treated_as_active",
        ],
        allowed_values={
            "runtime_role_assistance_capability_status": ["available"],
            "liveness_probe_mode": [ROLE_BINDING_LIVENESS_PROBE_MODE],
            "all_liveness_probes_started_before_wait": [True],
            "rehydrated_role_bindings[].role_key": list(RUNTIME_ROLE_KEYS),
            "rehydrated_role_bindings[].model_policy": [ROLE_BINDING_MODEL_POLICY],
            "rehydrated_role_bindings[].reasoning_effort_policy": [ROLE_BINDING_REASONING_EFFORT_POLICY],
            "rehydrated_role_bindings[].rehydration_result": sorted(RESUME_ROLE_BINDING_RESULTS),
            "rehydrated_role_bindings[].rehydrated_for_run_id": [run_state["run_id"]],
            "rehydrated_role_bindings[].rehydrated_after_resume_state_loaded": [True],
            "rehydrated_role_bindings[].host_liveness_status": sorted(ROLE_BINDING_HOST_LIVENESS_STATUSES),
            "rehydrated_role_bindings[].liveness_decision": sorted(ROLE_BINDING_LIVENESS_DECISIONS),
            "rehydrated_role_bindings[].resume_agent_attempted": [True],
            "rehydrated_role_bindings[].bounded_wait_result": sorted(ROLE_BINDING_BOUNDED_WAIT_RESULTS),
            "rehydrated_role_bindings[].liveness_probe_mode": [ROLE_BINDING_LIVENESS_PROBE_MODE],
            "rehydrated_role_bindings[].wait_agent_timeout_treated_as_active": [False],
        },
        conditional_required_fields={
            "when role_rehydration_request[].role_memory_status=available": [
                "rehydrated_role_bindings[].memory_packet_path",
                "rehydrated_role_bindings[].memory_packet_hash",
                "rehydrated_role_bindings[].memory_seeded_from_current_run",
            ],
            "when role_rehydration_request[].role_memory_status!=available": [
                "rehydrated_role_bindings[].memory_missing_acknowledged",
                "rehydrated_role_bindings[].replacement_seeded_from_common_run_context",
            ],
            "when rehydrated_role_bindings[].role_key=project_manager": [
                "rehydrated_role_bindings[].pm_resume_context_delivered",
            ],
        },
        structural_requirements=[
            "Provide exactly one non-duplicate rehydrated role-binding record for each role key requested by the resume action.",
            "Start the requested role-binding liveness probes in one concurrent batch before waiting for individual results.",
            "Use one liveness_probe_batch_id for the top-level receipt and every role record.",
            "Each record must match the corresponding role_rehydration_request path/hash fields.",
            "Reuse active current-run role bindings after memory/context refresh; open only replacement bindings whose liveness is missing, cancelled, unknown, completed, or timeout_unknown.",
            "Each restored or replacement live role binding must use a host-supported, addressable, isolated role surface and must be bound to the strongest available host model and highest available reasoning effort; do not rely on foreground/controller model inheritance.",
            "A wait_agent timeout must be recorded as timeout_unknown and must not justify live_agent_continuity_confirmed.",
            "missing, cancelled, completed, unknown, or timeout_unknown host liveness must open a replacement from current-run memory instead of continuing to wait on the old role.",
        ],
        optional_fields=[
            "rehydrated_role_bindings[].replacement_opened_after_resume_state_loaded",
        ],
        description="Refresh or replace runtime-required FlowPilot role bindings from current-run memory before PM resume decision, reusing active bindings and opening only failed replacements.",
        reviewer_check="PM and reviewer checks use the written role_binding_recovery_report before resume decisions.",
    )
__all__ = (
    "_payload_contract",
    "_terminal_summary_payload_contract",
    "_display_surface_receipt_payload_contract",
    "_role_slots_payload_contract",
    "_heartbeat_payload_contract",
    "_resume_role_rehydration_payload_contract",
)
_LOCAL_NAMES = set(globals())
