"""Router facade for the complete black-box runtime."""

from __future__ import annotations

from typing import Any

from . import cockpit, runtime


def router_next_action(ledger: dict[str, Any]) -> runtime.RuntimeAction:
    if not ledger.get("startup_intake"):
        return runtime.RuntimeAction("open_startup_intake", "startup intake has not been recorded")
    if ledger.get("cutover_gate", {}).get("decision") == "blocked":
        return runtime.RuntimeAction("repair_cutover_gate", "cutover gate has blockers")
    return runtime.router_next_action(ledger)


def apply_router_event(ledger: dict[str, Any], event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if event_type in cockpit.ALLOWED_EVENTS:
        return cockpit.submit_cockpit_event(ledger, event_type, payload)
    raise runtime.BlackBoxRuntimeError(f"unsupported router event: {event_type}")
