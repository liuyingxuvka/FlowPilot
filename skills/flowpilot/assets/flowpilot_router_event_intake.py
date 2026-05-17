"""External-event intake helpers for FlowPilot router.

This module keeps the public router entrypoint and private compatibility
function names in `flowpilot_router`, while moving the ACK preconsume and
pre-ACK quarantine mechanics out of the large facade.
"""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any


def preconsume_pending_card_return_ack_before_external_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
) -> dict[str, Any]:
    pending_returns = router._pending_return_records(run_root, str(run_state["run_id"]))
    if not pending_returns:
        return {"consumed": False, "reason": "no_pending_card_return"}
    if event in router.STARTUP_REVIEW_BEGIN_JOIN_EVENTS:
        pre_review = [record for record in pending_returns if router._pending_return_is_pre_review_startup_scope(record)]
        dependent = [
            record
            for record in pending_returns
            if pending_card_return_matches_event_dependency(router, record, event, run_state)
        ]
        candidates = pre_review + [record for record in dependent if record not in pre_review]
    else:
        candidates = [
            record
            for record in pending_returns
            if pending_card_return_matches_event_dependency(router, record, event, run_state)
        ]
    if not candidates:
        return {"consumed": False, "reason": "no_dependent_pending_card_return"}

    consumed_results: list[dict[str, Any]] = []
    for pending_return in candidates:
        action = router._next_pending_card_return_action(project_root, run_state, run_root, [pending_return])
        if not isinstance(action, dict):
            continue
        if action.get("action_type") not in {"check_card_return_event", "check_card_bundle_return_event"}:
            continue
        if not router._pending_card_return_ack_exists(project_root, action):
            continue

        auto_ack = router._try_auto_consume_pending_card_return_ack(project_root, run_root, run_state, action)
        result = auto_ack.get("result") if isinstance(auto_ack.get("result"), dict) else {}
        if auto_ack.get("consumed") and result.get("status") == "resolved":
            current_pending = run_state.get("pending_action")
            pending_action_cleared = False
            if router._pending_action_matches_card_return(current_pending, pending_return):
                run_state["pending_action"] = None
                pending_action_cleared = True
            consumed_results.append(
                {
                    "action_type": action.get("action_type"),
                    "card_return_event": action.get("card_return_event"),
                    "expected_return_path": action.get("expected_return_path"),
                    "status": result.get("status"),
                    "pending_action_cleared": pending_action_cleared,
                }
            )
            continue

        if auto_ack.get("consumed"):
            router.append_history(
                run_state,
                "router_pre_event_card_return_ack_did_not_resolve",
                {
                    "event": event,
                    "action_type": action.get("action_type"),
                    "card_return_event": action.get("card_return_event"),
                    "expected_return_path": action.get("expected_return_path"),
                    "status": result.get("status"),
                },
            )
            router.save_run_state(run_root, run_state)
            return {"consumed": False, "reason": "ack_did_not_resolve", "result": result}

        if auto_ack.get("preserve_pending"):
            return auto_ack

        router.append_history(
            run_state,
            "router_deferred_invalid_card_ack_before_external_event",
            {
                "event": event,
                "action_type": action.get("action_type"),
                "card_return_event": action.get("card_return_event"),
                "expected_return_path": action.get("expected_return_path"),
                "reason": auto_ack.get("reason"),
                "error": auto_ack.get("error"),
            },
        )
        router._mark_card_return_pending_explicit_check(
            run_root,
            str(run_state["run_id"]),
            action,
            reason=str(auto_ack.get("reason") or "ack_requires_explicit_check"),
            error=auto_ack.get("error"),
        )
        router.save_run_state(run_root, run_state)
        return auto_ack

    if consumed_results:
        router.append_history(
            run_state,
            "router_pre_consumed_card_return_ack_before_external_event",
            {
                "event": event,
                "consumed_count": len(consumed_results),
                "consumed_returns": consumed_results,
                "startup_pre_review_ack_join": event in router.STARTUP_REVIEW_BEGIN_JOIN_EVENTS,
            },
        )
        router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_pre_consumed_card_return_ack")
        router._sync_derived_run_views(
            project_root,
            run_root,
            run_state,
            reason="after_router_pre_consumed_card_return_ack",
            update_display=True,
        )
        router.save_run_state(run_root, run_state)
        return {"consumed": True, "results": consumed_results}

    return {"consumed": False, "reason": "dependent_pending_ack_file_missing"}


def system_card_delivery_flag(router: ModuleType, card_id: object) -> str:
    raw = str(card_id or "").strip()
    if not raw:
        return ""
    for entry in router.SYSTEM_CARD_SEQUENCE:
        if entry.get("card_id") == raw:
            return str(entry.get("flag") or "")
    return ""


def pending_return_card_delivery_flags(router: ModuleType, pending_return: dict[str, Any]) -> set[str]:
    flags: set[str] = set()
    if pending_return.get("return_kind") == "system_card_bundle":
        raw_card_ids = pending_return.get("card_ids")
        card_ids = raw_card_ids if isinstance(raw_card_ids, list) else []
    else:
        card_ids = [pending_return.get("card_id")]
    for card_id in card_ids:
        flag = system_card_delivery_flag(router, card_id)
        if flag:
            flags.add(flag)
    return flags


def role_list(value: object) -> set[str]:
    return {part.strip() for part in str(value or "").split(",") if part.strip()}


def pending_card_return_matches_event_dependency(
    router: ModuleType,
    pending_return: dict[str, Any],
    event: str,
    run_state: dict[str, Any],
) -> bool:
    expected_role = router._record_event_expected_role(event, run_state)
    target_role = str(pending_return.get("target_role") or "")
    target_roles = role_list(target_role)
    expected_roles = role_list(expected_role)
    role_matches = any(
        router._record_event_from_role_matches(event, target, expected_role)
        or router._record_event_from_role_matches(event, expected, target_role)
        for target in target_roles
        for expected in (expected_roles or {expected_role})
    )
    if not role_matches:
        return False
    required_flag = str((router.EXTERNAL_EVENTS.get(event) or {}).get("requires_flag") or "")
    if required_flag:
        return required_flag in pending_return_card_delivery_flags(router, pending_return)
    return True


def next_quarantined_role_report_path(router: ModuleType, run_root: Path, event: str) -> Path:
    quarantine_dir = run_root / "quarantined_role_reports"
    safe_event = router._safe_delivery_component(event)
    index = 1
    while True:
        candidate = quarantine_dir / f"{safe_event}-{index:04d}.json"
        if not candidate.exists():
            return candidate
        index += 1


def clear_stale_role_wait_for_quarantined_report(
    router: ModuleType,
    run_state: dict[str, Any],
    pending_return: dict[str, Any],
    event: str,
) -> str:
    pending_action = run_state.get("pending_action")
    if router._pending_action_matches_card_return(pending_action, pending_return):
        run_state["pending_action"] = None
        return "matching_card_return_wait"
    if isinstance(pending_action, dict) and pending_action.get("action_type") == "await_role_decision":
        raw_allowed = pending_action.get("allowed_external_events")
        if isinstance(raw_allowed, list) and event in raw_allowed:
            run_state["pending_action"] = None
            return "pre_ack_role_decision_wait"
    return "not_cleared"


def quarantine_missing_ack_report_before_external_event(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    payload: dict[str, Any] | None,
    envelope_path: str | None,
    envelope_hash: str | None,
    pending_return: dict[str, Any],
) -> dict[str, Any] | None:
    if not pending_card_return_matches_event_dependency(router, pending_return, event, run_state):
        return None

    quarantine_path = next_quarantined_role_report_path(router, run_root, event)
    relative_quarantine_path = router.project_relative(project_root, quarantine_path)
    expected_role = router._record_event_expected_role(event, run_state)
    report_payload = payload or {}
    payload_hash = router._stable_identity_hash(report_payload)
    record = {
        "schema_version": "flowpilot.quarantined_role_report.v1",
        "status": "quarantined_audit_only",
        "reason": "missing_valid_card_ack_before_report",
        "event": event,
        "expected_role": expected_role,
        "payload_hash": payload_hash,
        "payload": report_payload,
        "envelope_path": envelope_path,
        "envelope_hash": envelope_hash,
        "pending_return": {
            "return_kind": pending_return.get("return_kind") or "system_card",
            "card_return_event": pending_return.get("card_return_event"),
            "target_role": pending_return.get("target_role"),
            "target_agent_id": pending_return.get("target_agent_id"),
            "card_id": pending_return.get("card_id"),
            "card_ids": pending_return.get("card_ids") or [],
            "delivery_attempt_id": pending_return.get("delivery_attempt_id"),
            "delivery_attempt_ids": pending_return.get("delivery_attempt_ids") or [],
            "card_bundle_id": pending_return.get("card_bundle_id"),
            "expected_return_path": pending_return.get("expected_return_path"),
            "status": pending_return.get("status"),
        },
        "recovery": {
            "required_next_step": "same_role_opens_card_submits_ack_then_resubmits_fresh_report",
            "old_report_may_be_used_as_acceptance_evidence": False,
            "same_event_must_be_submitted_again_after_valid_ack": True,
        },
        "recorded_at": router.utc_now(),
    }
    router.write_json(quarantine_path, record)

    pending_action_cleared = clear_stale_role_wait_for_quarantined_report(router, run_state, pending_return, event)
    next_action = router._next_pending_card_return_action(project_root, run_state, run_root)
    if isinstance(next_action, dict):
        run_state["pending_action"] = next_action
    summary = {
        "event": event,
        "quarantine_path": relative_quarantine_path,
        "expected_role": expected_role,
        "pending_card_return_event": pending_return.get("card_return_event"),
        "expected_return_path": pending_return.get("expected_return_path"),
        "pending_action_cleared": pending_action_cleared,
        "next_action_type": next_action.get("action_type") if isinstance(next_action, dict) else None,
    }
    quarantined = run_state.setdefault("quarantined_role_reports", [])
    if isinstance(quarantined, list):
        quarantined.append(summary)
    router.append_history(run_state, "router_quarantined_pre_ack_role_report_for_same_role_ack_recovery", summary)
    router._refresh_route_memory(project_root, run_root, run_state, trigger="after_router_quarantined_pre_ack_role_report")
    router._sync_derived_run_views(
        project_root,
        run_root,
        run_state,
        reason="after_router_quarantined_pre_ack_role_report",
        update_display=True,
    )
    router.save_run_state(run_root, run_state)
    return {
        "ok": False,
        "event": event,
        "waiting": True,
        "recoverable": True,
        "report_quarantined": True,
        "quarantine_path": relative_quarantine_path,
        "recovery": record["recovery"],
        "next_required_action": next_action if isinstance(next_action, dict) else None,
    }
