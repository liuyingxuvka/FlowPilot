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

OWNER_MODULE = "flowpilot_router_system_cards"

def _direct_router_ack_token_for_card(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    card_id: str,
    to_role: str,
    target_agent_id: str | None,
    card_return_event: str,
    expected_return_path: str,
    expected_receipt_path: str,
    delivery_id: str | None,
    delivery_attempt_id: str | None,
    body_hash: str | None,
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_id": card_id,
        "card_return_event": card_return_event,
        "target_role": to_role,
        "target_agent_id": target_agent_id,
        "delivery_id": delivery_id,
        "delivery_attempt_id": delivery_attempt_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_path": expected_receipt_path,
        "body_hash": body_hash,
    }

def _direct_router_ack_token_for_bundle(
    run_state: dict[str, Any],
    run_root: Path,
    *,
    bundle_id: str,
    role: str,
    target_agent_id: str | None,
    card_return_event: str,
    card_ids: list[str],
    delivery_attempt_ids: list[str],
    expected_return_path: str,
    expected_receipt_paths: list[str],
) -> dict[str, Any]:
    frontier = read_json_if_exists(run_root / "execution_frontier.json")
    return {
        "schema_version": card_runtime.CARD_DIRECT_ROUTER_ACK_TOKEN_SCHEMA,
        "return_kind": "system_card_bundle",
        "submission_mode": "direct_to_router",
        "controller_ack_handoff_allowed": False,
        "run_id": run_state.get("run_id"),
        "route_version": frontier.get("route_version"),
        "frontier_node_id": frontier.get("active_node_id"),
        "card_bundle_id": bundle_id,
        "card_ids": card_ids,
        "delivery_attempt_ids": delivery_attempt_ids,
        "card_return_event": card_return_event,
        "target_role": role,
        "target_agent_id": target_agent_id,
        "expected_return_path": expected_return_path,
        "expected_receipt_paths": expected_receipt_paths,
    }

def _next_system_card_action(project_root: Path, run_state: dict[str, Any], run_root: Path) -> dict[str, Any] | None:
    flags = run_state["flags"]
    manifest = load_manifest_from_run(run_root)
    resume_waiting_for_pm = (
        bool(flags.get("resume_reentry_requested"))
        and bool(flags.get("resume_state_loaded"))
        and bool(flags.get("resume_roles_restored"))
        and not bool(flags.get("pm_resume_recovery_decision_returned"))
    )
    resume_replayed_without_pm = _resume_mechanical_replay_completed_without_pm(run_state)
    resume_card_ids = {"controller.resume_reentry", "pm.crew_rehydration_freshness", "pm.resume_decision"}
    for entry in SYSTEM_CARD_SEQUENCE:
        if entry["card_id"] == REVIEWER_STARTUP_FACT_CARD_ID:
            blockers = _startup_pre_review_reconciliation_blockers(project_root, run_root, run_state)
            if blockers:
                if any(blocker.get("kind") == "startup_prep_cards_not_all_sent" for blocker in blockers):
                    continue
                return _current_scope_pre_review_reconciliation_action(
                    project_root,
                    run_root,
                    run_state,
                    blockers=blockers,
                    review_trigger=entry["card_id"],
                )
        if resume_replayed_without_pm and entry["card_id"] in {"pm.crew_rehydration_freshness", "pm.resume_decision"}:
            continue
        if resume_waiting_for_pm and entry["card_id"] not in resume_card_ids:
            continue
        if flags.get(entry["flag"]):
            continue
        required_flag = entry.get("requires_flag")
        if required_flag and not flags.get(required_flag):
            continue
        required_all = entry.get("requires_all_flags")
        if required_all and not all(flags.get(flag) for flag in required_all):
            continue
        required_any = entry.get("requires_any_flag")
        if required_any and not any(flags.get(flag) for flag in required_any):
            continue
        if entry.get("requires_active_node_children") and not _active_node_has_children(run_root, _active_frontier(run_root)):
            continue
        if entry["card_id"] in CURRENT_SCOPE_REVIEWER_CARD_IDS:
            blockers = _pre_review_reconciliation_blockers_for_trigger(project_root, run_root, run_state, entry["card_id"])
            if blockers:
                return _current_scope_pre_review_reconciliation_action(
                    project_root,
                    run_root,
                    run_state,
                    blockers=blockers,
                    review_trigger=entry["card_id"],
                )
        policy_action = _route_action_for_card(entry["card_id"])
        legal_context: dict[str, Any] | None = None
        if policy_action:
            legal_context = _legal_next_action_context(project_root, run_root, run_state)
            if policy_action not in {str(item) for item in legal_context.get("legal_action_ids", [])}:
                continue
        to_role = _system_card_to_role(run_root, entry)
        if entry["card_id"] in STARTUP_ASYNC_CARD_IDS and to_role in CREW_ROLE_KEYS and not _active_agent_id_for_role(run_root, to_role):
            return _current_scope_pre_review_reconciliation_action(
                project_root,
                run_root,
                run_state,
                blockers=[
                    {
                        "kind": "startup_role_slots_not_ready",
                        "target_role": to_role,
                        "card_id": entry["card_id"],
                        "reason": "startup role slots must be reconciled before role-dependent startup work",
                        "scope_kind": "startup",
                        "scope_id": "startup",
                    }
                ],
                review_trigger=entry["card_id"],
            )
        if not run_state.get("manifest_check_requested"):
            manifest_extra = {"next_card_id": entry["card_id"], "next_recipient_role": to_role}
            if legal_context is not None:
                manifest_extra["legal_next_actions"] = legal_context
            return make_action(
                action_type="check_prompt_manifest",
                actor="router",
                label="router_checks_prompt_manifest",
                summary="Router checks the prompt manifest internally before exposing the next system-card relay.",
                allowed_reads=[project_relative(project_root, run_root / "runtime_kit" / "manifest.json")],
                allowed_writes=[project_relative(project_root, run_state_path(run_root))],
                extra=manifest_extra,
            )
        card = manifest_card(manifest, entry["card_id"])
        delivery_extra = {"postcondition": entry["flag"]}
        gate_contract = _public_gate_contract(_gate_contract_for_card(entry["card_id"]))
        if gate_contract is not None:
            delivery_extra["gate_contract"] = gate_contract
        if legal_context is not None:
            delivery_extra["legal_next_actions"] = legal_context
        delivery_extra.update(_pm_context_action_extra(project_root, run_root, entry))
        pm_decision_contract = _pm_decision_payload_contract_for_card(project_root, run_root, entry["card_id"])
        if pm_decision_contract is not None:
            delivery_extra["payload_contract"] = pm_decision_contract
        if entry["card_id"] == "reviewer.startup_fact_check":
            delivery_extra.update(_startup_mechanical_audit_action_extra(project_root, run_root, run_state))
        resolved_entry = {**entry, "to_role": to_role}
        delivery_context = _live_card_delivery_context(project_root, run_root, run_state, resolved_entry, card)
        delivery_extra["delivery_context"] = delivery_context
        run_id = str(run_state["run_id"])
        delivery_id, delivery_attempt_id = _next_card_delivery_attempt(run_root, run_id, entry["card_id"])
        safe_delivery_id = _safe_delivery_component(delivery_attempt_id)
        card_body_path = run_root / "runtime_kit" / str(card["path"])
        manifest_path = run_root / "runtime_kit" / "manifest.json"
        if not manifest_path.exists():
            manifest_path = runtime_kit_source() / "manifest.json"
        card_hash = hashlib.sha256(card_body_path.read_bytes()).hexdigest()
        manifest_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        envelope_path = run_root / "mailbox" / "system_cards" / f"{safe_delivery_id}.json"
        expected_receipt_path = run_root / "runtime_receipts" / "card_reads" / f"{safe_delivery_id}.receipt.json"
        expected_return_path = run_root / "mailbox" / "outbox" / "card_acks" / f"{safe_delivery_id}.ack.json"
        card_return_event = _card_return_event_for_card(entry["card_id"])
        target_agent_id = _active_agent_id_for_role(run_root, to_role)
        card_checkin_instruction = _card_checkin_instruction(
            project_root,
            envelope_path=project_relative(project_root, envelope_path),
            role=to_role,
            agent_id=target_agent_id,
            card_return_event=card_return_event,
            bundle=False,
        )
        expected_return_rel = project_relative(project_root, expected_return_path)
        expected_receipt_rel = project_relative(project_root, expected_receipt_path)
        direct_ack_token = _direct_router_ack_token_for_card(
            run_state,
            run_root,
            card_id=entry["card_id"],
            to_role=to_role,
            target_agent_id=target_agent_id,
            card_return_event=card_return_event,
            expected_return_path=expected_return_rel,
            expected_receipt_path=expected_receipt_rel,
            delivery_id=delivery_id,
            delivery_attempt_id=delivery_attempt_id,
            body_hash=card_hash,
        )
        direct_ack_token_hash = card_runtime.stable_json_hash(direct_ack_token)
        resume_tick_id = _latest_resume_tick_id(run_state)
        role_io_receipt = _role_io_protocol_receipt_for_agent(
            run_root,
            run_id,
            role=to_role,
            agent_id=target_agent_id,
            resume_tick_id=resume_tick_id,
        )
        if target_agent_id and role_io_receipt is None:
            return make_action(
                action_type="inject_role_io_protocol",
                actor="host",
                label=f"host_injects_role_io_protocol_for_{_safe_delivery_component(to_role)}",
                summary=(
                    f"Inject FlowPilot role I/O protocol to {to_role} before delivering "
                    f"system card {entry['card_id']}."
                ),
                allowed_reads=[
                    project_relative(project_root, run_root / "crew_ledger.json"),
                    project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
                ],
                allowed_writes=[
                    project_relative(project_root, _role_io_protocol_ledger_path(run_root)),
                    project_relative(project_root, _role_io_protocol_receipt_dir(run_root)),
                    project_relative(project_root, run_state_path(run_root)),
                ],
                to_role=to_role,
                extra={
                    "target_agent_id": target_agent_id,
                    "resume_tick_id": resume_tick_id,
                    "protocol_schema_version": ROLE_IO_PROTOCOL_SCHEMA,
                    "protocol_hash": _role_io_protocol_hash(),
                    "required_before_card_id": entry["card_id"],
                    "controller_visibility": "role_io_protocol_envelope_only",
                    "ordinary_system_card_delivery": False,
                },
            )
        delivery_extra.update(
            {
                "delivery_mode": "envelope_only_v2",
                "resource_lifecycle": "planned_internal_action",
                "artifact_committed": False,
                "relay_allowed": False,
                "apply_required": True,
                "controller_visibility": "system_card_envelope_only",
                "sealed_body_reads_allowed": False,
                "requires_read_receipt": True,
                "open_method": "open-card",
                "card_return_event": card_return_event,
                "card_checkin_instruction": card_checkin_instruction,
                "direct_router_ack_token": direct_ack_token,
                "direct_router_ack_token_hash": direct_ack_token_hash,
                "expected_return_path": expected_return_rel,
                "expected_receipt_path": expected_receipt_rel,
                "card_envelope_path": project_relative(project_root, envelope_path),
                "delivery_id": delivery_id,
                "delivery_attempt_id": delivery_attempt_id,
                "body_path": project_relative(project_root, card_body_path),
                "body_hash": card_hash,
                "manifest_path": project_relative(project_root, manifest_path),
                "manifest_hash": manifest_hash,
                "target_agent_id": target_agent_id,
                "resume_tick_id": resume_tick_id,
                "role_io_protocol_hash": _role_io_protocol_hash(),
                "role_io_protocol_receipt_path": role_io_receipt.get("receipt_path") if isinstance(role_io_receipt, dict) else None,
                "role_io_protocol_receipt_hash": role_io_receipt.get("receipt_hash") if isinstance(role_io_receipt, dict) else None,
                "ack_report_required": True,
                "ack_submission_mode": "direct_to_router",
                "controller_ack_handoff_allowed": False,
                "read_receipt_is_mechanical_only": True,
                "planned_artifacts": {
                    "card_envelope_path": project_relative(project_root, envelope_path),
                    "expected_receipt_path": expected_receipt_rel,
                    "expected_return_path": expected_return_rel,
                },
            }
        )
        allowed_reads = [
            project_relative(project_root, run_root / "runtime_kit" / "manifest.json"),
        ]
        allowed_reads.extend(
            str(path)
            for path in delivery_context.get("source_paths", {}).values()
            if isinstance(path, str) and path
        )
        if entry["card_id"] == "reviewer.startup_fact_check":
            allowed_reads.extend(
                [
                    delivery_extra["startup_mechanical_audit_path"],
                    delivery_extra["router_owned_check_proof_path"],
                ]
            )
        return make_action(
            action_type="deliver_system_card",
            actor="controller",
            label=entry["label"],
            summary=f"Deliver system card envelope {entry['card_id']} to {to_role}; role must open through runtime and submit {card_return_event} directly to Router.",
            allowed_reads=allowed_reads,
            allowed_writes=[
                project_relative(project_root, envelope_path),
                project_relative(project_root, expected_return_path),
                project_relative(project_root, run_root / "prompt_delivery_ledger.json"),
                project_relative(project_root, _card_ledger_path(run_root)),
                project_relative(project_root, _return_event_ledger_path(run_root)),
            ],
            card_id=entry["card_id"],
            to_role=to_role,
            extra=delivery_extra,
        )
    return None

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

def _system_card_to_role(run_root: Path, entry: dict[str, Any]) -> str:
    default_role = str(entry.get("to_role") or "")
    if entry.get("card_id") == "worker.research_report":
        index_path = _research_packet_index_path(run_root)
        if index_path.exists():
            try:
                index = _load_packet_index(index_path, label="research")
            except RouterError:
                return default_role
            packets = index.get("packets")
            if isinstance(packets, list) and packets:
                to_role = str(packets[0].get("to_role") or "").strip()
                if to_role:
                    return to_role
    return default_role

def _reconcile_durable_wait_evidence(
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    batch_reconciliation = _refresh_all_parallel_packet_batches_from_durable_results(project_root, run_root, run_state)
    changed = bool(batch_reconciliation.get("changed"))
    role_output_reconciliation = _try_reconcile_startup_fact_role_output_ledger(project_root, run_root, run_state)
    changed = bool(role_output_reconciliation.get("changed")) or changed
    changed = _try_reconcile_material_scan_body_delivery(project_root, run_root, run_state) or changed
    changed = _try_reconcile_material_scan_results(project_root, run_root, run_state) or changed
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
                "role_output_reconciliation": role_output_reconciliation,
            },
        )
    return {**batch_reconciliation, "changed": changed, "role_output_reconciliation": role_output_reconciliation}

__all__ = (
    '_direct_router_ack_token_for_card',
    '_direct_router_ack_token_for_bundle',
    '_next_system_card_action',
    '_system_card_bundle_candidate_actions',
    '_next_system_card_bundle_action',
    '_system_card_to_role',
    '_reconcile_durable_wait_evidence',
)

_LOCAL_NAMES = set(globals())
