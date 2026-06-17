"""Route-authority snapshot and rejection helpers for route-frontier policy."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

from flowpilot_router_errors import RouterError
from flowpilot_router_route_frontier_policy_completion_authority_rejection import (
    ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS,
    route_authority_event_requirements,
    route_authority_inferred_event,
    route_authority_missing_required_flags,
    unsupported_route_authority_payload_fields,
)

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


def _route_authority_owner_for_action(policy_by_id: dict[str, dict[str, Any]], action_id: str) -> str:
    row = policy_by_id.get(str(action_id)) if isinstance(policy_by_id, dict) else None
    if not isinstance(row, dict):
        return "owner_missing"
    owner = str(row.get("owner_role") or "").strip()
    if owner:
        return owner
    roles = sorted({str(role) for role in row.get("actor_roles") or [] if str(role)})
    if len(roles) == 1:
        return roles[0]
    if roles:
        return "owner_conflict"
    return "owner_missing"


def _route_authority_required_repair_command(policy_by_id: dict[str, dict[str, Any]], action_id: str) -> str:
    row = policy_by_id.get(str(action_id)) if isinstance(policy_by_id, dict) else None
    if isinstance(row, dict):
        command = str(row.get("required_repair_command") or "").strip()
        if command:
            return command
    return f"submit_{action_id}"


def _route_authority_snapshot(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    *,
    policy_by_id: dict[str, dict[str, Any]],
    frontier: dict[str, Any],
    active_node_kind: str,
    legal_ids: list[str],
    blocking_reasons: list[str],
) -> dict[str, Any]:
    _bind_router(router)
    legal_id_set = {str(item) for item in legal_ids}
    owners = [_route_authority_owner_for_action(policy_by_id, action_id) for action_id in legal_ids]
    concrete_owners = sorted({owner for owner in owners if owner not in {"owner_missing", "owner_conflict"}})
    if any(owner == "owner_conflict" for owner in owners) or len(concrete_owners) > 1:
        current_owner = "owner_conflict"
    elif any(owner == "owner_missing" for owner in owners) or not legal_ids:
        current_owner = "owner_missing"
    else:
        current_owner = concrete_owners[0]
    legal_next_actions = []
    repair_commands: list[str] = []
    for action_id in legal_ids:
        row = policy_by_id[action_id]
        repair_command = _route_authority_required_repair_command(policy_by_id, action_id)
        repair_commands.append(repair_command)
        legal_next_actions.append(
            {
                "action_id": action_id,
                "owner_role": _route_authority_owner_for_action(policy_by_id, action_id),
                "required_repair_command": repair_command,
                "router_events": [str(item) for item in row.get("router_events") or []],
                "transaction_type": row.get("transaction_type"),
                "commit_targets": row.get("commit_targets") or [],
            }
        )
    required_repair_command = repair_commands[0] if len(set(repair_commands)) == 1 else "choose_one_legal_action_by_id"
    current_state_family = "no_legal_next_action"
    if len(legal_ids) == 1:
        current_state_family = f"route_action:{legal_ids[0]}"
    elif len(legal_ids) > 1:
        current_state_family = "route_action:multiple"
    return {
        "schema_version": "flowpilot.route_authority_snapshot.v1",
        "source": "router",
        "authority_registry_path": project_relative(project_root, router._route_action_policy_registry_path(run_root)),
        "active_route_id": str(frontier.get("active_route_id") or ""),
        "route_version": int(frontier.get("route_version") or 0),
        "active_node_id": str(frontier.get("active_node_id") or ""),
        "active_node_kind": active_node_kind,
        "current_owner": current_owner,
        "current_owner_roles": concrete_owners,
        "current_state_family": current_state_family,
        "legal_action_ids": legal_ids,
        "forbidden_action_ids": sorted(set(policy_by_id) - legal_id_set),
        "legal_next_actions": legal_next_actions,
        "required_repair_command": required_repair_command,
        "blocking_reasons": [str(item) for item in blocking_reasons if item],
        "single_authority": current_owner not in {"owner_missing", "owner_conflict"},
        "current_runtime_contract": True,
        "fallback_or_alias_translation_allowed": False,
    }


def _route_authority_rejection_payload(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    rejected_action_id: str,
    context: str,
    rejected_event: str | None,
    rejection_kind: str,
    unsupported_payload_fields: list[str] | None = None,
) -> dict[str, Any]:
    _bind_router(router)
    legal_context = router._legal_next_action_context(project_root, run_root, run_state)
    snapshot = legal_context.get("route_authority_snapshot") if isinstance(legal_context.get("route_authority_snapshot"), dict) else {}
    inferred_event = route_authority_inferred_event(router, rejected_action_id, rejected_event)
    event_requirements = route_authority_event_requirements(router, run_state, inferred_event)
    return {
        "schema_version": "flowpilot.route_authority_rejection.v1",
        "source": "router",
        "rejection_kind": rejection_kind,
        "context": context,
        "rejected_event": rejected_event,
        "inferred_rejected_event": inferred_event or None,
        "rejected_action_id": str(rejected_action_id),
        "current_owner": snapshot.get("current_owner"),
        "current_owner_roles": snapshot.get("current_owner_roles") or [],
        "current_state_family": snapshot.get("current_state_family"),
        "legal_action_ids": snapshot.get("legal_action_ids") or [],
        "forbidden_action_ids": snapshot.get("forbidden_action_ids") or [],
        "required_repair_command": snapshot.get("required_repair_command"),
        "legal_next_actions": snapshot.get("legal_next_actions") or [],
        "event_requirements": event_requirements,
        "unsupported_payload_fields": unsupported_payload_fields or [],
        "router_instruction": "Reject this package. Reissue exactly one current-contract event whose action_id is in legal_action_ids and whose owner matches current_owner.",
        "fallback_or_alias_translation_allowed": False,
    }


def _write_route_authority_rejection_blocker(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    rejected_action_id: str,
    context: str,
    rejected_event: str | None,
    rejection_kind: str,
    unsupported_payload_fields: list[str] | None = None,
) -> dict[str, Any]:
    _bind_router(router)
    rejection = router._route_authority_rejection_payload(
        project_root,
        run_root,
        run_state,
        rejected_action_id=rejected_action_id,
        context=context,
        rejected_event=rejected_event,
        rejection_kind=rejection_kind,
        unsupported_payload_fields=unsupported_payload_fields,
    )
    legal_ids = [str(item) for item in rejection.get("legal_action_ids") or []]
    reasons = ", ".join(legal_ids) or "no legal route action is currently available"
    missing_required_flags = route_authority_missing_required_flags(rejection)
    message = (
        f"{context} rejected as {rejection_kind}: route action {rejected_action_id} is not the current legal path; "
        f"legal_action_ids={reasons}; required_repair_command={rejection.get('required_repair_command')}; "
        f"missing_required_flags={missing_required_flags}"
    )
    payload = {
        "path": project_relative(project_root, router.run_state_path(run_root)),
        "role": rejection.get("current_owner") or "project_manager",
        "route_authority_rejection": rejection,
    }
    blocker = router._write_control_blocker(
        project_root,
        run_root,
        run_state,
        source="router_route_authority_rejected",
        error_message=message,
        event=rejected_event,
        action_type="route_authority_submission",
        payload=payload,
    )
    blocker["route_authority_rejection"] = rejection
    blocker["route_authority_snapshot"] = rejection
    blocker_path_value = blocker.get("blocker_artifact_path")
    if blocker_path_value:
        blocker_path = resolve_project_path(project_root, str(blocker_path_value))
        saved = read_json_if_exists(blocker_path)
        if saved:
            saved["route_authority_rejection"] = rejection
            saved["route_authority_snapshot"] = rejection
            saved["controller_visible_summary"] = "Router rejected a route-authority package. Reissue the current legal route action; do not translate aliases or fallback prose."
            write_json(blocker_path, saved)
            blocker = saved
    router._sync_control_plane_indexes(project_root, run_root, run_state)
    router.save_run_state(run_root, run_state)
    return blocker


def _reject_route_authority_submission(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    rejected_action_id: str,
    context: str,
    rejected_event: str | None = None,
    rejection_kind: str = "wrong_path",
    unsupported_payload_fields: list[str] | None = None,
) -> None:
    _bind_router(router)
    blocker = router._write_route_authority_rejection_blocker(
        project_root,
        run_root,
        run_state,
        rejected_action_id=rejected_action_id,
        context=context,
        rejected_event=rejected_event,
        rejection_kind=rejection_kind,
        unsupported_payload_fields=unsupported_payload_fields,
    )
    rejection = blocker.get("route_authority_rejection") if isinstance(blocker, dict) else None
    legal_ids = []
    repair_command = None
    if isinstance(rejection, dict):
        legal_ids = [str(item) for item in rejection.get("legal_action_ids") or []]
        repair_command = rejection.get("required_repair_command")
    missing_required_flags = route_authority_missing_required_flags(rejection)
    raise RouterError(
        f"{context} rejected by route authority; legal_action_ids={legal_ids}; "
        f"required_repair_command={repair_command}; missing_required_flags={missing_required_flags}",
        control_blocker=blocker,
    )


def _unsupported_route_authority_payload_fields(router: ModuleType, payload: dict[str, Any] | None) -> list[str]:
    _bind_router(router)
    return unsupported_route_authority_payload_fields(payload)


def _reject_unsupported_route_authority_payload(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    event: str,
    action_id: str,
    payload: dict[str, Any] | None,
) -> None:
    _bind_router(router)
    fields = router._unsupported_route_authority_payload_fields(payload)
    if not fields:
        return
    router._reject_route_authority_submission(
        project_root,
        run_root,
        run_state,
        rejected_action_id=action_id,
        context=f"external event {event}",
        rejected_event=event,
        rejection_kind="unsupported_payload_shape",
        unsupported_payload_fields=fields,
    )


__all__ = (
    "ROUTE_AUTHORITY_UNSUPPORTED_PAYLOAD_FIELDS",
    "_route_authority_owner_for_action",
    "_route_authority_required_repair_command",
    "_route_authority_snapshot",
    "_route_authority_rejection_payload",
    "_write_route_authority_rejection_blocker",
    "_reject_route_authority_submission",
    "_unsupported_route_authority_payload_fields",
    "_reject_unsupported_route_authority_payload",
)


_LOCAL_NAMES = set(globals())
