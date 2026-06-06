"""Same-role system-card bundle selection helpers."""

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


from flowpilot_router_system_cards_selection_next import _next_system_card_action
from flowpilot_router_system_cards_selection_tokens import _direct_router_ack_token_for_bundle


def _system_card_bundle_candidate_actions(project_root: Path, run_state: dict[str, Any], run_root: Path) -> list[dict[str, Any]]:
    probe_state = dict(run_state)
    probe_state["flags"] = dict(run_state.get("flags") or {})
    probe_state["manifest_check_requested"] = True
    actions: list[dict[str, Any]] = []
    target_role: str | None = None
    target_agent_id: str | None = None
    resume_tick_id: str | None = None
    for _entry in SYSTEM_CARD_SEQUENCE:
        action = _next_system_card_action(project_root, probe_state, run_root)
        if not isinstance(action, dict) or action.get("action_type") != "deliver_system_card":
            break
        if action.get("payload_contract"):
            break
        role = str(action.get("to_role") or "")
        agent_id = str(action.get("target_agent_id") or "")
        tick_id = str(action.get("resume_tick_id") or "")
        if target_role is None:
            target_role = role
            target_agent_id = agent_id
            resume_tick_id = tick_id
        elif role != target_role or agent_id != target_agent_id or tick_id != resume_tick_id:
            break
        actions.append(action)
        postcondition = action.get("postcondition")
        if not isinstance(postcondition, str) or not postcondition:
            break
        probe_state["flags"][postcondition] = True
        probe_state["manifest_check_requested"] = True
    return actions if len(actions) >= 2 else []


def _next_system_card_bundle_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    actions = _system_card_bundle_candidate_actions(project_root, run_state, run_root)
    if len(actions) < 2:
        return None
    first = actions[0]
    role = str(first.get("to_role") or "")
    card_ids = [str(action.get("card_id") or "") for action in actions]
    if not run_state.get("manifest_check_requested"):
        return make_action(
            action_type="check_prompt_manifest",
            actor="router",
            label="router_checks_prompt_manifest",
            summary="Router checks the prompt manifest internally before exposing the next same-role system-card bundle relay.",
            allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
            allowed_writes=[project_relative(project_root, run_state_path(run_root))],
            extra={
                "next_card_id": card_ids[0],
                "bundle_candidate": True,
                "bundle_card_ids": card_ids,
                "next_recipient_role": role,
            },
        )
    first_attempt = str(first.get("delivery_attempt_id") or card_ids[0])
    last_attempt = str(actions[-1].get("delivery_attempt_id") or card_ids[-1])
    bundle_id = f"{_safe_delivery_component(first_attempt)}--to--{_safe_delivery_component(last_attempt)}"
    bundle_envelope_path = run_root / "mailbox" / "system_card_bundles" / f"{bundle_id}.json"
    expected_return_path = run_root / "mailbox" / "outbox" / "card_bundle_acks" / f"{bundle_id}.ack.json"
    expected_receipt_paths = [str(action.get("expected_receipt_path") or "") for action in actions]
    allowed_reads: list[str] = []
    for action in actions:
        for raw_path in action.get("allowed_reads") or []:
            if isinstance(raw_path, str) and raw_path and raw_path not in allowed_reads:
                allowed_reads.append(raw_path)
    cards: list[dict[str, Any]] = []
    for action in actions:
        member = {
            "card_id": action.get("card_id"),
            "label": action.get("label"),
            "postcondition": action.get("postcondition"),
            "delivery_id": action.get("delivery_id"),
            "delivery_attempt_id": action.get("delivery_attempt_id"),
            "body_path": action.get("body_path"),
            "body_hash": action.get("body_hash"),
            "manifest_path": action.get("manifest_path"),
            "manifest_hash": action.get("manifest_hash"),
            "expected_receipt_path": action.get("expected_receipt_path"),
            "card_return_event": action.get("card_return_event"),
            "delivery_context": action.get("delivery_context"),
        }
        for key in (
            "pm_context_paths",
            "pm_prior_path_context_required_for_decision",
            "controller_history_is_evidence",
        ):
            if key in action:
                member[key] = action[key]
        cards.append(member)
    card_return_event = _card_bundle_return_event_for_role(role)
    direct_ack_token = _direct_router_ack_token_for_bundle(
        run_state,
        run_root,
        bundle_id=bundle_id,
        role=role,
        target_agent_id=str(first.get("target_agent_id") or "") or None,
        card_return_event=card_return_event,
        card_ids=card_ids,
        delivery_attempt_ids=[str(action.get("delivery_attempt_id") or "") for action in actions],
        expected_return_path=project_relative(project_root, expected_return_path),
        expected_receipt_paths=expected_receipt_paths,
    )
    direct_ack_token_hash = card_runtime.stable_json_hash(direct_ack_token)
    card_checkin_instruction = _card_checkin_instruction(
        project_root,
        envelope_path=project_relative(project_root, bundle_envelope_path),
        role=role,
        agent_id=str(first.get("target_agent_id") or "") or None,
        card_return_event=card_return_event,
        bundle=True,
    )
    return make_action(
        action_type="deliver_system_card_bundle",
        actor="controller",
        label=f"same_role_system_card_bundle_delivered_{_safe_delivery_component(card_ids[0])}_to_{_safe_delivery_component(card_ids[-1])}",
        summary=(
            f"Deliver one committed system-card bundle with {len(card_ids)} cards to {role}; "
            f"the role must open it through runtime and submit {card_return_event} directly to Router."
        ),
        allowed_reads=allowed_reads,
        allowed_writes=[
            project_relative(project_root, bundle_envelope_path),
            project_relative(project_root, expected_return_path),
            project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
            project_relative(project_root, _card_ledger_path(run_root)),
            project_relative(project_root, _return_event_ledger_path(run_root)),
        ],
        card_id=card_ids[0],
        to_role=role,
        extra={
            "card_ids": card_ids,
            "postconditions": [str(action.get("postcondition") or "") for action in actions],
            "delivery_mode": "same_role_system_card_bundle_v1",
            "resource_lifecycle": "planned_internal_action",
            "artifact_committed": False,
            "relay_allowed": False,
            "apply_required": True,
            "controller_visibility": "system_card_bundle_envelope_only",
            "sealed_body_reads_allowed": False,
            "requires_read_receipt": True,
            "open_method": "open-card-bundle",
            "card_return_event": card_return_event,
            "card_checkin_instruction": card_checkin_instruction,
            "direct_router_ack_token": direct_ack_token,
            "direct_router_ack_token_hash": direct_ack_token_hash,
            "expected_return_path": project_relative(project_root, expected_return_path),
            "expected_receipt_paths": expected_receipt_paths,
            "card_bundle_id": bundle_id,
            "card_bundle_envelope_path": project_relative(project_root, bundle_envelope_path),
            "target_agent_id": first.get("target_agent_id"),
            "resume_tick_id": first.get("resume_tick_id"),
            "role_io_protocol_hash": first.get("role_io_protocol_hash"),
            "role_io_protocol_receipt_path": first.get("role_io_protocol_receipt_path"),
            "role_io_protocol_receipt_hash": first.get("role_io_protocol_receipt_hash"),
            "ack_report_required": True,
            "ack_submission_mode": "direct_to_router",
            "controller_ack_handoff_allowed": False,
            "read_receipt_is_mechanical_only": True,
            "same_role_bundle": True,
            "manifest_batch_checked": True,
            "bundle_does_not_cross_role_or_agent": True,
            "bundle_stops_before_role_output": True,
            "cards": cards,
            "planned_artifacts": {
                "card_bundle_envelope_path": project_relative(project_root, bundle_envelope_path),
                "expected_receipt_paths": expected_receipt_paths,
                "expected_return_path": project_relative(project_root, expected_return_path),
            },
        },
    )


__all__ = (
    '_system_card_bundle_candidate_actions',
    '_next_system_card_bundle_action',
)

_LOCAL_NAMES = set(globals())
