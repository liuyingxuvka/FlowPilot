"""Pure Controller action and scheduler projection helpers for FlowPilot router."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from flowpilot_router_controller_boundary import (
    CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE,
    PASSIVE_WAIT_STATUS_ACTION_TYPES,
)


def _controller_action_id_for_action(action: dict[str, Any]) -> str:
    idempotency_key = str(action.get("idempotency_key") or "").strip()
    if idempotency_key:
        identity = {
            "idempotency_key": idempotency_key,
            "action_type": action.get("action_type"),
            "label": action.get("label"),
            "scope_kind": action.get("scope_kind"),
            "scope_id": action.get("scope_id"),
        }
        digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:20]
        return f"controller-action-{digest}"
    identity = {
        "source_action_id": action.get("action_id"),
        "action_type": action.get("action_type"),
        "label": action.get("label"),
        "card_id": action.get("card_id"),
        "card_bundle_id": action.get("card_bundle_id"),
        "mail_id": action.get("mail_id"),
        "expected_return_path": action.get("expected_return_path"),
        "allowed_external_events": action.get("allowed_external_events"),
        "created_at": action.get("created_at"),
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()[:20]
    return f"controller-action-{digest}"


def _action_is_passive_wait_status(action: dict[str, Any] | None) -> bool:
    if not isinstance(action, dict):
        return False
    action_type = str(action.get("action_type") or "")
    if action_type not in PASSIVE_WAIT_STATUS_ACTION_TYPES:
        return False
    return not bool(action.get("controller_side_effect_required"))


def _controller_action_projection_kind(action: dict[str, Any] | None) -> str:
    if _action_is_passive_wait_status(action):
        return "passive_wait_status"
    if isinstance(action, dict) and str(action.get("action_type") or "") == CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE:
        return "continuous_standby"
    return "ordinary_controller_work"


def _controller_action_is_ordinary_work_row(entry_or_action: dict[str, Any] | None) -> bool:
    if not isinstance(entry_or_action, dict):
        return False
    explicit = entry_or_action.get("ordinary_controller_work_row")
    if explicit is not None:
        return bool(explicit)
    action = entry_or_action.get("action") if isinstance(entry_or_action.get("action"), dict) else entry_or_action
    return not _action_is_passive_wait_status(action)


def _controller_action_initial_status(action: dict[str, Any]) -> str:
    if action.get("action_type") in {
        "await_card_return_event",
        "await_card_bundle_return_event",
        "await_current_scope_reconciliation",
        "await_role_decision",
        CONTINUOUS_CONTROLLER_STANDBY_ACTION_TYPE,
    }:
        return "waiting"
    return "pending"


def _controller_action_counts(actions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "pending": 0,
        "in_progress": 0,
        "done": 0,
        "blocked": 0,
        "waiting": 0,
        "skipped": 0,
        "incomplete": 0,
        "repair_pending": 0,
        "resolved": 0,
        "superseded": 0,
    }
    for item in actions:
        status = str(item.get("status") or "pending")
        counts[status] = counts.get(status, 0) + 1
    counts["total"] = len(actions)
    return counts


def _controller_action_active_work_count(counts: dict[str, int]) -> int:
    return sum(
        int(counts.get(status, 0) or 0)
        for status in ("pending", "in_progress", "blocked", "incomplete", "repair_pending")
    )


def _controller_action_summary(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "action_id": entry.get("action_id"),
        "action_type": entry.get("action_type"),
        "label": entry.get("label"),
        "summary": entry.get("summary"),
        "status": entry.get("status"),
        "to_role": entry.get("to_role"),
        "completion_class": entry.get("completion_class"),
        "controller_completion_command": entry.get("controller_completion_command"),
        "controller_completion_mode": entry.get("controller_completion_mode"),
        "router_pending_apply_required": entry.get("router_pending_apply_required"),
        "completion_source": entry.get("completion_source"),
        "satisfied_by_external_event": entry.get("satisfied_by_external_event"),
        "controller_receipt_required": entry.get("controller_receipt_required"),
        "controller_projection_kind": entry.get("controller_projection_kind"),
        "ordinary_controller_work_row": entry.get("ordinary_controller_work_row"),
        "router_reconciliation_status": entry.get("router_reconciliation_status"),
        "router_scheduler_row_id": entry.get("router_scheduler_row_id"),
        "scope_kind": entry.get("scope_kind"),
        "scope_id": entry.get("scope_id"),
        "required_deliverables": entry.get("required_deliverables") or [],
        "deliverable_status": entry.get("deliverable_status"),
        "deliverable_repair_attempts": entry.get("deliverable_repair_attempts"),
        "max_deliverable_repair_attempts": entry.get("max_deliverable_repair_attempts"),
        "repair_of_controller_action_id": entry.get("repair_of_controller_action_id"),
        "resolved_by_controller_action_id": entry.get("resolved_by_controller_action_id"),
        "action_path": entry.get("action_path"),
        "expected_receipt_path": entry.get("expected_receipt_path"),
        "updated_at": entry.get("updated_at"),
    }


def _controller_receipt_rule_for_display_action(action_type: str) -> str:
    return (
        "First paste display_text exactly into the user dialog, then write a "
        f"Controller receipt for {action_type} with this payload_template as the "
        "receipt payload. Generated files, host UI updates, and display paths do "
        "not satisfy user-dialog display evidence."
    )


def _controller_receipt_display_rule(rule: object, action_type: str) -> str:
    if isinstance(rule, str) and rule.strip():
        rewritten = rule.replace("before applying", "before writing the Controller receipt for")
        rewritten = rewritten.replace("before apply", "before writing the Controller receipt")
        rewritten = rewritten.replace("apply requires", "the Controller receipt requires")
        rewritten = rewritten.replace("applying this action", "writing the Controller receipt")
        rewritten = rewritten.replace("applying the action", "writing the Controller receipt")
        rewritten = rewritten.replace("applying action", "writing the Controller receipt")
        if "Controller receipt" in rewritten or "controller-receipt" in rewritten:
            return rewritten
    return (
        f"Paste the required display_text in the user dialog before writing the "
        f"Controller receipt for {action_type}; the receipt payload must include "
        "display_confirmation.rendered_to=user_dialog with the matching display_text_sha256."
    )


def _controller_ledger_action_view(
    action: dict[str, Any],
    *,
    action_id: str,
    receipt_path: str,
    controller_receipt_required: bool,
) -> dict[str, Any]:
    """Project a Router action into Controller action-ledger semantics."""

    view = dict(action)
    passive_wait_status = _action_is_passive_wait_status(view)
    original_apply_required = bool(view.get("apply_required", True))
    original_contract = view.get("next_step_contract") if isinstance(view.get("next_step_contract"), dict) else {}
    original_contract_apply_required = bool(original_contract.get("apply_required", original_apply_required))
    router_pending_apply_required = original_apply_required if controller_receipt_required else False
    contract_router_pending_apply_required = original_contract_apply_required if controller_receipt_required else False
    completion_command = "controller-receipt" if controller_receipt_required else "router-controlled-wait"
    completion_mode = "controller_action_ledger_receipt" if controller_receipt_required else "controller_action_ledger_wait"

    view.update(
        {
            "controller_action_id": action_id,
            "controller_receipt_path": receipt_path,
            "controller_receipt_required": controller_receipt_required,
            "controller_projection_kind": _controller_action_projection_kind(view),
            "ordinary_controller_work_row": not passive_wait_status,
            "controller_completion_command": completion_command,
            "controller_completion_mode": completion_mode,
            "controller_row_completion_source": "runtime/controller_action_ledger.json",
            "router_pending_apply_required": router_pending_apply_required,
            "apply_required": False,
        }
    )
    if "proof_required_before_apply" in view:
        view["proof_required_before_controller_receipt"] = bool(view.get("proof_required_before_apply"))
        view["proof_required_before_apply"] = False
    if "controller_must_display_text_before_apply" in view:
        view["controller_must_display_text_before_receipt"] = bool(view.get("controller_must_display_text_before_apply"))
        view["controller_must_display_text_before_apply"] = False
    if view.get("payload_template_rule"):
        view["payload_template_rule"] = _controller_receipt_rule_for_display_action(str(view.get("action_type") or "action"))
    if view.get("controller_display_rule"):
        view["controller_display_rule"] = _controller_receipt_display_rule(
            view.get("controller_display_rule"),
            str(view.get("action_type") or "action"),
        )
    if isinstance(view.get("plain_instruction"), str):
        plain = str(view["plain_instruction"])
        legacy_startup_intake_apply_instruction = (
            "After the UI closes, apply "
            "this pending action with only the returned startup_intake_result.result_path."
        )
        plain = plain.replace(
            legacy_startup_intake_apply_instruction,
            "After the UI closes, write a Controller receipt with only the returned startup_intake_result.result_path in the receipt payload.",
        )
        view["plain_instruction"] = plain
    if isinstance(view.get("spawn_policy"), str):
        view["spawn_policy"] = str(view["spawn_policy"]).replace(
            "before_applying_action",
            "before_controller_receipt",
        )
    if controller_receipt_required:
        view["controller_receipt_instruction"] = (
            "Complete this Controller ledger row by performing the requested host/controller work, "
            "then run flowpilot_router.py controller-receipt with the required receipt payload."
        )
    else:
        view["controller_receipt_instruction"] = (
            "This is a Router-controlled wait status projection, not ordinary Controller work. "
            "Do not apply it; follow Router daemon status, current_wait, and standby/patrol "
            "metadata until the matching external event or blocker path resolves it."
        )

    contract = dict(original_contract)
    contract.update(
        {
            "apply_required": False,
            "router_pending_apply_required": contract_router_pending_apply_required,
            "controller_completion_command": completion_command,
            "controller_completion_mode": completion_mode,
            "controller_receipt_required": controller_receipt_required,
        }
    )
    view["next_step_contract"] = contract
    return view


def _router_scheduler_row_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {
        "queued": 0,
        "waiting": 0,
        "receipt_done": 0,
        "reconciled": 0,
        "blocked": 0,
        "skipped": 0,
        "superseded": 0,
    }
    for row in rows:
        state = str(row.get("router_state") or "queued")
        counts[state] = counts.get(state, 0) + 1
    counts["total"] = len(rows)
    return counts


def _router_scheduler_idempotency_key(action: dict[str, Any], scope_kind: str, scope_id: str) -> str:
    action_type = str(action.get("action_type") or "")
    key_parts: dict[str, Any] = {
        "action_type": action_type,
        "scope_kind": scope_kind,
        "scope_id": scope_id,
        "label": action.get("label"),
    }
    for field in (
        "card_id",
        "card_bundle_id",
        "delivery_attempt_id",
        "mail_id",
        "expected_return_path",
        "postcondition",
        "projection_hash",
        "next_card_id",
    ):
        value = action.get(field)
        if value not in (None, "", []):
            key_parts[field] = value
    if action_type == "sync_display_plan":
        key_parts["projection_hash"] = action.get("projection_hash")
    return "router-scheduler:" + hashlib.sha256(json.dumps(key_parts, sort_keys=True).encode("utf-8")).hexdigest()[:24]


def _router_scheduler_row_id_for_action(action: dict[str, Any]) -> str:
    key = str(action.get("router_scheduler_row_id") or action.get("idempotency_key") or "").strip()
    if not key:
        key = json.dumps(
            {
                "action_type": action.get("action_type"),
                "label": action.get("label"),
                "card_id": action.get("card_id"),
                "card_bundle_id": action.get("card_bundle_id"),
                "expected_return_path": action.get("expected_return_path"),
            },
            sort_keys=True,
        )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return f"router-row-{digest}"
