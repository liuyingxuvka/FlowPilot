"""Action envelope and controller reporting policy helpers."""

from __future__ import annotations

from types import ModuleType
from typing import Any

from flowpilot_router_protocol_catalog import *

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


OWNER_MODULE = "flowpilot_router_action_factory_envelope"


def append_history(state: dict[str, Any], label: str, details: dict[str, Any] | None = None) -> None:
    history = state.setdefault("history", [])
    history.append({"at": utc_now(), "label": label, "details": details or {}})


def _controller_user_reporting_policy() -> dict[str, Any]:
    return {
        "schema_version": CONTROLLER_USER_REPORTING_POLICY_SCHEMA,
        "plain_language_required": True,
        "speak_only_when_user_value": True,
        "reminder": (
            "First decide whether this action needs a user-visible message. "
            "Quiet patrol, receipts, ledger cleanup, relay bookkeeping, and "
            "process-only asides are silent by default. If this action is "
            "mentioned to the user, explain it in plain language instead of "
            "copying internal action names or metadata."
        ),
        "silent_by_default_for": [
            "quiet_patrol_continue",
            "controller_receipts",
            "ledger_cleanup",
            "relay_bookkeeping",
            "routine_process_asides",
            "no_new_controller_work",
        ],
        "report_when": [
            "user_action_required",
            "blocker_or_recovery",
            "terminal_stop_or_completion",
            "user_relevant_wait_target_changed",
            "required_display_text",
            "explicit_user_status_request",
        ],
        "allowed_user_report_points": [
            "what_is_happening_now",
            "what_flowpilot_is_waiting_for",
            "whether_user_needs_to_act",
        ],
        "hide_internal_metadata_by_default": [
            "event_names",
            "packet_ids",
            "ledger_names",
            "hashes",
            "action_ids",
            "contract_names",
            "diagnostic_file_paths",
        ],
        "technical_details_allowed_when_user_asks": True,
        "sealed_body_boundary_unchanged": True,
    }


def make_action(
    *,
    action_type: str,
    actor: str,
    label: str,
    summary: str,
    source: str = "router",
    allowed_reads: list[str] | None = None,
    allowed_writes: list[str] | None = None,
    card_id: str | None = None,
    mail_id: str | None = None,
    to_role: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_reporting_policy = _controller_user_reporting_policy()
    action: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "action_id": f"{label}:{utc_now()}",
        "action_type": action_type,
        "actor": actor,
        "source": source,
        "issued_by": "router",
        "label": label,
        "summary": summary,
        "allowed_reads": allowed_reads or [],
        "allowed_writes": allowed_writes or [],
        "created_at": utc_now(),
    }
    if card_id:
        action["card_id"] = card_id
        action["from"] = "system"
        action["issued_by"] = "router"
        action["delivered_by"] = "controller"
    if mail_id:
        action["mail_id"] = mail_id
        action["delivered_by"] = "controller"
    if to_role:
        action["to_role"] = to_role
    if extra:
        action.update(extra)
    if action_type == "await_role_decision":
        action["allowed_external_events"] = _validated_external_event_names(
            action.get("allowed_external_events"),
            context=f"await_role_decision action {label}",
        )
    action.setdefault("resource_lifecycle", "pending_action")
    action.setdefault("artifact_committed", False)
    action.setdefault("relay_allowed", False)
    action.setdefault("apply_required", True)
    if action.get("requires_user_dialog_display_confirmation") and "payload_template" not in action:
        display_kind = action.get("display_kind")
        display_text_sha256 = action.get("display_text_sha256")
        if isinstance(display_kind, str) and isinstance(display_text_sha256, str):
            action["payload_template"] = {
                "display_confirmation": {
                    "action_type": action_type,
                    "display_kind": display_kind,
                    "display_text_sha256": display_text_sha256,
                    "provenance": DISPLAY_CONFIRMATION_PROVENANCE,
                    "rendered_to": DISPLAY_CONFIRMATION_TARGET,
                }
            }
            action["payload_template_rule"] = (
                "First paste display_text exactly into the user dialog, then apply "
                "the action with this payload_template. Generated files, host UI "
                "updates, and display paths do not satisfy user-dialog display evidence."
            )
    resolved_recipient = str(action.get("to_role") or actor)
    action.setdefault("why_this_role", summary)
    action["controller_user_reporting_policy"] = user_reporting_policy
    action["next_step_contract"] = {
        "schema_version": "flowpilot.next_step_contract.v1",
        "controller_has_explicit_next": True,
        "action_type": action_type,
        "recipient_role": resolved_recipient,
        "controller_may_infer_next_from_chat": False,
        "controller_may_contact_unlisted_role": False,
        "controller_may_create_project_evidence": False,
        "sealed_body_reads_allowed": bool(action.get("sealed_body_reads_allowed", False)),
        "resource_lifecycle": action.get("resource_lifecycle"),
        "artifact_committed": bool(action.get("artifact_committed", False)),
        "relay_allowed": bool(action.get("relay_allowed", False)),
        "apply_required": bool(action.get("apply_required", True)),
        "allowed_external_events": action.get("allowed_external_events", []),
        "postcondition": action.get("postcondition"),
        "controller_user_reporting_policy": user_reporting_policy,
    }
    if action.get("gate_contract") is not None:
        action["next_step_contract"]["gate_contract"] = action["gate_contract"]
    if action.get("ack_clearance_scope") is not None:
        action["next_step_contract"]["ack_clearance_scope"] = action["ack_clearance_scope"]
    if "ack_is_read_receipt_only" in action:
        action["next_step_contract"]["ack_is_read_receipt_only"] = bool(action.get("ack_is_read_receipt_only"))
    if "target_work_completion_evidence_required_separately" in action:
        action["next_step_contract"]["target_work_completion_evidence_required_separately"] = bool(
            action.get("target_work_completion_evidence_required_separately")
        )
    relay_or_wait_boundary = (
        action_type in ROUTER_READY_PREEMPTION_ACTION_TYPES
        or action_type.startswith("relay_")
        or action_type == "await_role_decision"
        or bool(action.get("relay_allowed"))
    )
    if actor == "controller" and relay_or_wait_boundary:
        policy = {
            "schema_version": "flowpilot.router_ready_preemption.v1",
            "router_ready_preempts_foreground_wait": True,
            "controller_must_scan_daemon_before_foreground_role_wait": True,
            "normal_router_progress_source": "router_daemon_status_and_controller_action_ledger",
            "allowed_router_reentry_commands": [],
            "diagnostic_router_reentry_commands": ["next", "run-until-wait"],
            "diagnostic_router_reentry_policy": (
                "diagnostic/test/explicit-repair only; not normal progress while daemon status "
                "and the Controller action ledger own the active run"
            ),
            "foreground_wait_agent_allowed": False,
            "foreground_role_chat_wait_allowed": False,
            "controlled_wait_records_allowed": [
                "await_card_return_event",
                "await_card_bundle_return_event",
                "await_role_decision",
            ],
            "liveness_wait_allowed_only_when_router_requests_recovery": True,
            "timeout_unknown_is_not_active": True,
            "sealed_body_reads_allowed": bool(action.get("sealed_body_reads_allowed", False)),
        }
        action["controller_after_relay_policy"] = policy
        action["next_step_contract"]["router_ready_preempts_foreground_wait"] = True
        action["next_step_contract"]["controller_must_scan_daemon_before_foreground_role_wait"] = True
        action["next_step_contract"]["normal_router_progress_source"] = "router_daemon_status_and_controller_action_ledger"
        action["next_step_contract"]["foreground_wait_agent_allowed"] = False
        action["next_step_contract"]["foreground_role_chat_wait_allowed"] = False
    return action


__all__ = (
    "append_history",
    "_controller_user_reporting_policy",
    "make_action",
)

_LOCAL_NAMES = set(globals())
