"""Projection-only Cockpit/status helpers for the complete runtime."""

from __future__ import annotations

from typing import Any

from . import runtime


ALLOWED_EVENTS = {"pause", "resume", "stop", "refresh", "open_logs", "chat_fallback"}
STATE_MUTATING_KEYS = {
    "routes",
    "packets",
    "results",
    "leases",
    "flowguard_work_orders",
    "reviews",
    "validation_evidence",
    "closure",
}


def render_status(ledger: dict[str, Any]) -> dict[str, Any]:
    projection = runtime.render_console(ledger)
    projection["surface"] = "cockpit"
    projection["projection_only"] = True
    projection["sealed_bodies_visible"] = False
    projection["blockers"] = _public_blockers(ledger)
    ledger["status_projection"] = projection
    return projection


def record_display_surface_fallback(ledger: dict[str, Any], reason: str) -> dict[str, Any]:
    fallback = {
        "preferred": "cockpit",
        "active": "chat_route_sign",
        "fallback_reason": reason,
        "route_sign_required": True,
        "created_at": runtime.now_iso(),
    }
    ledger["display_surface"] = fallback
    event = submit_cockpit_event(ledger, "chat_fallback", {"reason": reason})
    return {"fallback": fallback, "event": event}


def submit_cockpit_event(ledger: dict[str, Any], event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if event_type not in ALLOWED_EVENTS:
        raise runtime.BlackBoxRuntimeError(f"unsupported Cockpit event: {event_type}")
    payload = dict(payload or {})
    direct_keys = sorted(STATE_MUTATING_KEYS.intersection(payload))
    accepted = not direct_keys
    event = {
        "cockpit_event_type": event_type,
        "accepted": accepted,
        "blocked_direct_keys": direct_keys,
        "created_at": runtime.now_iso(),
    }
    ledger.setdefault("user_events", []).append(event)
    runtime._event(ledger, "cockpit_event_submitted", **event)
    return event


def _public_blockers(ledger: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    closure = ledger.get("closure")
    if isinstance(closure, dict):
        blockers.extend(str(item) for item in closure.get("blockers", []))
    for packet in ledger.get("packets", {}).values():
        if packet.get("status") in {"result_blocked", "review_blocked"}:
            blockers.append(f"packet_blocked:{packet['packet_id']}")
    for result in ledger.get("results", {}).values():
        for blocker in result.get("mechanical_blockers", []):
            blockers.append(f"{result['result_id']}:{blocker}")
    return sorted(set(blockers))
