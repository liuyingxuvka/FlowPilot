"""Replay reconciliation split from flowpilot_router_role_output_bridge_events."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_router_role_output_bridge_events as _parent
from flowpilot_runtime_gateway import GATEWAY_ROUTER_JSON, assert_runtime_gateway_write


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    _parent._bind_router(router)
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(_parent).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names or name in current:
            continue
        current[name] = value


def _package_disposition_authority_split(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    event: str,
    scoped_identity: dict[str, Any] | None,
) -> dict[str, Any] | None:
    _bind_router(router)
    if not isinstance(scoped_identity, dict):
        return None
    if scoped_identity.get("family") != "pm_package_disposition":
        return None
    if not _scoped_event_is_recorded(run_state, scoped_identity):
        return None
    if _canonical_pm_package_disposition_authority(router, project_root, run_root, event) is not None:
        return None
    scope = scoped_identity.get("scope") if isinstance(scoped_identity.get("scope"), dict) else {}
    return {
        "classification": "package_disposition_authority_split",
        "event": event,
        "dedupe_key": scoped_identity.get("dedupe_key"),
        "family": scoped_identity.get("family"),
        "scope": scope,
        "reason": "scoped event idempotency exists without canonical PM package disposition authority",
        "repair_required": True,
    }

def _record_package_disposition_authority_split(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
    *,
    split: dict[str, Any],
    source: str,
    record: dict[str, Any] | None = None,
    envelope_hash: str | None = None,
) -> dict[str, Any]:
    _bind_router(router)
    scope = split.get("scope") if isinstance(split.get("scope"), dict) else {}
    output_id = str((record or {}).get("output_id") or "")
    key = "|".join(
        str(part or "")
        for part in (
            split.get("event"),
            split.get("dedupe_key"),
            scope.get("body_hash"),
            source,
            output_id,
            envelope_hash,
        )
    )
    rows = run_state.setdefault("package_disposition_authority_splits", [])
    if not isinstance(rows, list):
        rows = []
        run_state["package_disposition_authority_splits"] = rows
    existing = next((item for item in rows if isinstance(item, dict) and item.get("split_key") == key), None)
    if isinstance(existing, dict):
        return {**existing, "already_recorded": True}
    path = run_root / "runtime" / "package_disposition_authority_splits.jsonl"
    summary = {
        "schema_version": "flowpilot.package_disposition_authority_split.v1",
        "status": "blocked_requires_explicit_repair",
        "classification": split.get("classification"),
        "event": split.get("event"),
        "dedupe_key": split.get("dedupe_key"),
        "scope": scope,
        "source": source,
        "output_id": output_id or None,
        "envelope_hash": envelope_hash,
        "split_key": key,
        "repair_required": True,
        "recorded_at": router.utc_now(),
        "split_path": router.project_relative(project_root, path),
    }
    assert_runtime_gateway_write(path, GATEWAY_ROUTER_JSON, operation="append_package_disposition_authority_split")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")
    rows.append(summary)
    return summary

def _try_reconcile_direct_role_output_event_ledger(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    run_state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    flags = run_state.setdefault("flags", {})
    changed = False
    reconciled = 0
    already_recorded = 0
    repair_owned_conflicts = 0
    stale_unowned_conflicts = 0
    package_authority_splits = 0
    skipped_invalid = 0
    skipped_not_ready = 0
    skipped_unauthorized = 0
    events: list[str] = []
    for record in _role_output_ledger_outputs(router, run_root):
        envelope = record.get("envelope")
        if not isinstance(envelope, dict):
            continue
        event = str(envelope.get("event_name") or "")
        if not event or event not in EXTERNAL_EVENTS:
            continue
        meta = EXTERNAL_EVENTS[event]
        flag = str(meta["flag"])
        required_flag = str(meta.get("requires_flag") or "")
        scoped_policy = getattr(router, "SCOPED_EVENT_IDENTITY_POLICIES", {}).get(event)
        is_package_disposition_event = (
            isinstance(scoped_policy, dict)
            and scoped_policy.get("family") == "pm_package_disposition"
        )
        required_flag_missing = bool(required_flag and not flags.get(required_flag))
        if required_flag_missing and not is_package_disposition_event:
            skipped_not_ready += 1
            continue
        if not _role_output_event_has_durable_authority(router, run_root, run_state, event):
            skipped_unauthorized += 1
            continue
        try:
            role_output_runtime.validate_envelope_runtime_receipt(project_root, envelope)
            payload = _role_output_body_payload_from_record(router, project_root, record, envelope)
        except (role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError, TypeError, ValueError):
            skipped_invalid += 1
            continue
        scoped_identity = _scoped_event_identity(project_root, run_root, run_state, event, payload)
        conflict_classification = _classify_scoped_event_conflict(run_state, scoped_identity)
        if conflict_classification.get("classification") in {
            "terminal_quarantine",
            "pm_repair_owned_stale_conflict",
            "control_blocker_owned_stale_conflict",
        }:
            repair_owned_conflicts += 1
            quarantine = _record_role_output_replay_quarantine(
                router,
                project_root,
                run_root,
                run_state,
                event=event,
                record=record,
                classification=conflict_classification,
            )
            events.append(event)
            if not quarantine.get("already_quarantined"):
                changed = True
                append_history(
                    run_state,
                    "router_skipped_repair_owned_package_disposition_conflict_replay",
                    quarantine,
                )
            continue
        stale_unowned_classification = _classify_stale_unowned_pm_package_replay(
            router,
            project_root,
            run_root,
            event,
            scoped_identity,
            conflict_classification,
        )
        if stale_unowned_classification is not None:
            stale_unowned_conflicts += 1
            quarantine = _record_role_output_replay_quarantine(
                router,
                project_root,
                run_root,
                run_state,
                event=event,
                record=record,
                classification=stale_unowned_classification,
            )
            events.append(event)
            if not quarantine.get("already_quarantined"):
                changed = True
                append_history(
                    run_state,
                    "router_skipped_stale_unowned_package_disposition_replay",
                    quarantine,
                )
            continue
        if required_flag_missing:
            skipped_not_ready += 1
            continue
        _preconsume_pending_card_return_ack_before_external_event(
            project_root,
            run_root,
            run_state,
            event=event,
        )
        if _pending_card_return_blocker_for_event(run_root, str(run_state["run_id"]), event, run_state) is not None:
            skipped_not_ready += 1
            continue
        authority_split = _package_disposition_authority_split(
            router,
            project_root,
            run_root,
            run_state,
            event,
            scoped_identity,
        )
        if authority_split is None:
            _check_scoped_event_conflict(run_state, scoped_identity)
        if _scoped_event_is_recorded(run_state, scoped_identity) or (
            flags.get(flag) and _event_allows_run_wide_flag_short_circuit(event, scoped_identity)
        ):
            if authority_split is None:
                wait_closure = _close_waiting_controller_actions_for_external_event(
                    project_root,
                    run_root,
                    run_state,
                    event=event,
                    payload=payload,
                    source="role_output_ledger_event_already_recorded",
                )
                if wait_closure.get("changed"):
                    changed = True
                    already_recorded += 1
                    events.append(event)
                continue
        try:
            recorded = _record_router_reconciled_external_event(project_root, run_root, run_state, event, payload)
        except (RouterError, role_output_runtime.RoleOutputRuntimeError, OSError, json.JSONDecodeError, TypeError, ValueError):
            if is_package_disposition_event:
                if authority_split is not None:
                    package_authority_splits += 1
                    split_record = _record_package_disposition_authority_split(
                        router,
                        project_root,
                        run_root,
                        run_state,
                        split=authority_split,
                        source="role_output_ledger",
                        record=record,
                    )
                    events.append(event)
                    if not split_record.get("already_recorded"):
                        changed = True
                        append_history(
                            run_state,
                            "router_blocked_package_disposition_authority_split_replay",
                            split_record,
                        )
                skipped_invalid += 1
                continue
            raise
        if recorded:
            changed = True
            reconciled += 1
            events.append(event)
    if changed:
        append_history(
            run_state,
            "router_reconciled_direct_role_output_event_ledger",
            {
                "reconciled": reconciled,
                "already_recorded": already_recorded,
                "repair_owned_conflicts": repair_owned_conflicts,
                "stale_unowned_conflicts": stale_unowned_conflicts,
                "package_authority_splits": package_authority_splits,
                "events": events,
                "skipped_invalid": skipped_invalid,
                "skipped_not_ready": skipped_not_ready,
                "skipped_unauthorized": skipped_unauthorized,
            },
        )
    return {
        "changed": changed,
        "reconciled": reconciled,
        "already_recorded": already_recorded,
        "repair_owned_conflicts": repair_owned_conflicts,
        "stale_unowned_conflicts": stale_unowned_conflicts,
        "package_authority_splits": package_authority_splits,
        "events": events,
        "skipped_invalid": skipped_invalid,
        "skipped_not_ready": skipped_not_ready,
        "skipped_unauthorized": skipped_unauthorized,
    }


_LOCAL_NAMES = set(globals())
