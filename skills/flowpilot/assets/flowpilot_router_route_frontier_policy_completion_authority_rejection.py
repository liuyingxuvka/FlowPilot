"""Route-authority rejection payload utilities."""

from __future__ import annotations

from typing import Any, Mapping

from flowpilot_router_protocol_external_event_data_route import ROUTE_EXTERNAL_EVENT_DATA

ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS = (
    "compatibility_action",
    "compatibility_event",
    "fallback_event",
    "fallback_route_action",
    "legacy_event",
    "legacy_route_action",
    "natural_language_route_action",
    "old_action_id",
    "old_event_name",
    "prose_route_action",
    "route_action_alias",
    "selected_path_text",
)


def route_authority_inferred_event(router: Any, rejected_action_id: str, rejected_event: str | None) -> str:
    inferred_event = str(rejected_event or "").strip()
    if inferred_event:
        return inferred_event
    event_to_action = getattr(router, "ROUTE_ACTION_POLICY_EVENT_TO_ACTION", {})
    if not isinstance(event_to_action, dict):
        return ""
    matching_events = [
        str(event)
        for event, action in event_to_action.items()
        if str(action) == str(rejected_action_id)
    ]
    return matching_events[0] if len(matching_events) == 1 else ""


def route_authority_event_requirements(
    router: Any,
    run_state: Mapping[str, Any],
    inferred_event: str,
) -> dict[str, Any]:
    event_data = getattr(router, "ROUTE_EXTERNAL_EVENT_DATA", None)
    if not isinstance(event_data, dict):
        event_data = ROUTE_EXTERNAL_EVENT_DATA
    event_row = event_data.get(inferred_event) if inferred_event else None
    if not isinstance(event_row, dict):
        return {}
    flags = run_state.get("flags") if isinstance(run_state.get("flags"), dict) else {}
    required_flag = str(event_row.get("requires_flag") or "").strip()
    missing_required_flags = []
    if required_flag and not flags.get(required_flag):
        missing_required_flags.append(required_flag)
    return {
        "requires_flag": required_flag or None,
        "missing_required_flags": missing_required_flags,
        "summary": event_row.get("summary"),
    }


def route_authority_missing_required_flags(rejection: Mapping[str, Any] | None) -> list[str]:
    event_requirements = rejection.get("event_requirements") if isinstance(rejection, Mapping) else {}
    if not isinstance(event_requirements, Mapping):
        return []
    return [str(item) for item in event_requirements.get("missing_required_flags") or []]


def unsupported_route_authority_payload_fields(payload: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(payload, Mapping):
        return []
    return sorted({field for field in ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS if field in payload})


__all__ = (
    "ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS",
    "route_authority_inferred_event",
    "route_authority_event_requirements",
    "route_authority_missing_required_flags",
    "unsupported_route_authority_payload_fields",
)
