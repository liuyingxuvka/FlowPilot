"""External watchdog for FlowPilot heartbeat continuity.

This script is designed for Windows Task Scheduler or any other external
supervisor. It detects stale `.flowpilot` heartbeat evidence and records the
official host-automation reset that FlowPilot must perform through the Codex
app automation interface.

Important boundary: this script does not edit `automation.toml` directly. The
supported reset is an official Codex app automation update that pauses and then
reactivates the active heartbeat automation. Even that reset is not proof that
Codex resumed; the next heartbeat is the proof.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None  # type: ignore[assignment]


RUNNING_STATUSES = {"running", "in_progress", "active"}
TERMINAL_STATUSES = {"complete", "completed", "blocked", "cancelled", "stopped"}
HEARTBEAT_TIME_FIELDS = (
    "created_at",
    "timestamp",
    "current_time_iso",
    "time_iso",
    "time",
)
SOURCE_TIME_FIELDS = (
    "checked_at",
    "updated_at",
    "completed_at",
    "cleared_at",
    "started_at",
    "created_at",
    "timestamp",
    "current_time_iso",
)
GLOBAL_SCHEMA_VERSION = "flowpilot-global-watchdog/v1"
GLOBAL_SUPERVISOR_CADENCE_MINUTES = 30
REGISTRATION_LEASE_MINUTES = GLOBAL_SUPERVISOR_CADENCE_MINUTES * 3


@dataclass(frozen=True)
class HeartbeatEvidence:
    heartbeat_id: str | None
    path: Path | None
    timestamp: datetime | None
    timestamp_source: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class BusyLeaseEvidence:
    path: Path
    loaded: bool
    active: bool
    valid: bool
    expired: bool
    recently_cleared: bool
    grace_active: bool
    route_matches: bool
    node_matches: bool
    reason: str
    cleared_at: datetime | None
    expires_at: datetime | None
    grace_seconds: float
    grace_remaining_seconds: float | None
    remaining_seconds: float | None
    payload: dict[str, Any]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_optional_json(path: Path) -> tuple[bool, dict[str, Any], str | None]:
    try:
        payload = read_json(path)
    except FileNotFoundError:
        return False, {}, "missing"
    except Exception as exc:
        return False, {}, repr(exc)
    return True, payload, None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        return {"_parse_error": "tomllib unavailable on this Python version"}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except Exception as exc:  # pragma: no cover - diagnostic path
        return {"_parse_error": repr(exc)}


def resolve_heartbeat_file(root: Path, heartbeat_id: str | None) -> Path | None:
    heartbeat_dir = root / ".flowpilot" / "heartbeats"
    if heartbeat_id:
        candidates = [
            heartbeat_dir / heartbeat_id,
            heartbeat_dir / f"{heartbeat_id}.json",
            heartbeat_dir / f"{heartbeat_id}.md",
        ]
        for path in candidates:
            if path.exists() and path.suffix.lower() == ".json":
                return path
    json_files = sorted(heartbeat_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return json_files[0] if json_files else None


def extract_heartbeat_time(path: Path, payload: dict[str, Any]) -> tuple[datetime | None, str]:
    for field in HEARTBEAT_TIME_FIELDS:
        parsed = parse_time(payload.get(field))
        if parsed is not None:
            return parsed, field
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc), "file_mtime"
    except OSError:
        return None, "missing"


def load_heartbeat(root: Path, heartbeat_id: str | None) -> HeartbeatEvidence:
    path = resolve_heartbeat_file(root, heartbeat_id)
    if path is None:
        return HeartbeatEvidence(heartbeat_id=heartbeat_id, path=None, timestamp=None, timestamp_source="missing", payload={})
    try:
        payload = read_json(path)
    except Exception as exc:
        return HeartbeatEvidence(
            heartbeat_id=heartbeat_id,
            path=path,
            timestamp=None,
            timestamp_source=f"json_parse_error:{exc!r}",
            payload={},
        )
    timestamp, source = extract_heartbeat_time(path, payload)
    return HeartbeatEvidence(
        heartbeat_id=str(payload.get("heartbeat_id") or heartbeat_id or path.stem),
        path=path,
        timestamp=timestamp,
        timestamp_source=source,
        payload=payload,
    )


def _first_nested(payload: dict[str, Any], paths: tuple[tuple[str, ...], ...]) -> Any:
    for path in paths:
        current: Any = payload
        for part in path:
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current.get(part)
        if current is not None:
            return current
    return None


def _source_time(path: Path, payload: dict[str, Any]) -> tuple[datetime | None, str]:
    for field in SOURCE_TIME_FIELDS:
        parsed = parse_time(payload.get(field))
        if parsed is not None:
            return parsed, field
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc), "file_mtime"
    except OSError:
        return None, "missing"


def _source_summary(
    name: str,
    path: Path | None,
    *,
    loaded: bool,
    payload: dict[str, Any],
    error: str | None,
    now: datetime,
    trusted_for_decision: bool,
) -> dict[str, Any]:
    timestamp = None
    timestamp_source = "missing"
    age_seconds = None
    if path is not None and loaded:
        timestamp, timestamp_source = _source_time(path, payload)
        if timestamp is not None:
            age_seconds = max(0.0, (now - timestamp).total_seconds())
    return {
        "name": name,
        "path": str(path) if path else None,
        "loaded": loaded,
        "error": error,
        "trusted_for_decision": trusted_for_decision,
        "diagnostic_only": not trusted_for_decision,
        "timestamp": isoformat_z(timestamp) if timestamp else None,
        "timestamp_source": timestamp_source,
        "age_seconds": None if age_seconds is None else round(age_seconds, 3),
        "status": _first_nested(
            payload,
            (
                ("status",),
                ("state", "status"),
                ("mode",),
                ("decision",),
            ),
        ),
        "active_route": _first_nested(
            payload,
            (
                ("active_route",),
                ("state", "active_route"),
                ("frontier", "active_route"),
            ),
        ),
        "active_node": _first_nested(
            payload,
            (
                ("active_node",),
                ("state", "active_node"),
                ("frontier", "active_node"),
            ),
        ),
        "route_version": _first_nested(
            payload,
            (
                ("route_version",),
                ("state", "route_version"),
                ("frontier", "route_version"),
            ),
        ),
        "frontier_version": _first_nested(
            payload,
            (
                ("frontier_version",),
                ("state", "frontier_version"),
                ("frontier", "frontier_version"),
            ),
        ),
    }


def build_source_status(
    *,
    root: Path,
    now: datetime,
    state_path: Path,
    state: dict[str, Any],
    heartbeat: HeartbeatEvidence,
    busy_lease: BusyLeaseEvidence,
    stale_seconds: float,
) -> dict[str, Any]:
    frontier_path = root / ".flowpilot" / "execution_frontier.json"
    lifecycle_path = root / ".flowpilot" / "lifecycle" / "latest.json"
    frontier_loaded, frontier_payload, frontier_error = read_optional_json(frontier_path)
    lifecycle_loaded, lifecycle_payload, lifecycle_error = read_optional_json(lifecycle_path)

    sources = {
        "state_json": _source_summary(
            "state_json",
            state_path,
            loaded=True,
            payload=state,
            error=None,
            now=now,
            trusted_for_decision=True,
        ),
        "latest_heartbeat": {
            "name": "latest_heartbeat",
            "path": str(heartbeat.path) if heartbeat.path else None,
            "loaded": heartbeat.path is not None and heartbeat.timestamp is not None,
            "error": None if heartbeat.path else "missing",
            "trusted_for_decision": True,
            "diagnostic_only": False,
            "timestamp": isoformat_z(heartbeat.timestamp) if heartbeat.timestamp else None,
            "timestamp_source": heartbeat.timestamp_source,
            "age_seconds": None if heartbeat.timestamp is None else round(max(0.0, (now - heartbeat.timestamp).total_seconds()), 3),
            "heartbeat_id": heartbeat.heartbeat_id,
        },
        "busy_lease_json": {
            "name": "busy_lease_json",
            "path": str(busy_lease.path),
            "loaded": busy_lease.loaded,
            "trusted_for_decision": True,
            "diagnostic_only": False,
            "status": busy_lease.payload.get("status") if busy_lease.loaded else None,
            "active": busy_lease.active,
            "valid": busy_lease.valid,
            "reason": busy_lease.reason,
            "route_id": busy_lease.payload.get("route_id"),
            "node_id": busy_lease.payload.get("node_id"),
            "timestamp": isoformat_z(busy_lease.expires_at) if busy_lease.expires_at else None,
            "timestamp_source": "expires_at" if busy_lease.expires_at else "missing",
            "error": None if busy_lease.loaded else "missing_or_unreadable",
        },
        "execution_frontier_json": _source_summary(
            "execution_frontier_json",
            frontier_path,
            loaded=frontier_loaded,
            payload=frontier_payload,
            error=frontier_error,
            now=now,
            trusted_for_decision=False,
        ),
        "lifecycle_latest_json": _source_summary(
            "lifecycle_latest_json",
            lifecycle_path,
            loaded=lifecycle_loaded,
            payload=lifecycle_payload,
            error=lifecycle_error,
            now=now,
            trusted_for_decision=False,
        ),
    }

    warnings: list[dict[str, Any]] = []
    state_route = state.get("active_route")
    state_node = state.get("active_node")
    state_route_version = state.get("route_version")
    state_frontier_version = state.get("frontier_version")
    if frontier_loaded:
        frontier_route = frontier_payload.get("active_route")
        frontier_node = frontier_payload.get("active_node")
        frontier_route_version = frontier_payload.get("route_version")
        frontier_version = frontier_payload.get("frontier_version")
        if state_route and frontier_route and str(state_route) != str(frontier_route):
            warnings.append(
                {
                    "kind": "route_drift",
                    "source": "execution_frontier_json",
                    "state_active_route": state_route,
                    "frontier_active_route": frontier_route,
                }
            )
        if state_node and frontier_node and str(state_node) != str(frontier_node):
            warnings.append(
                {
                    "kind": "node_drift",
                    "source": "execution_frontier_json",
                    "state_active_node": state_node,
                    "frontier_active_node": frontier_node,
                }
            )
        if state_route_version is not None and frontier_route_version is not None and state_route_version != frontier_route_version:
            warnings.append(
                {
                    "kind": "route_version_drift",
                    "source": "execution_frontier_json",
                    "state_route_version": state_route_version,
                    "frontier_route_version": frontier_route_version,
                }
            )
        if state_frontier_version is not None and frontier_version is not None and state_frontier_version != frontier_version:
            warnings.append(
                {
                    "kind": "frontier_version_drift",
                    "source": "execution_frontier_json",
                    "state_frontier_version": state_frontier_version,
                    "frontier_version": frontier_version,
                }
            )
    elif frontier_error:
        warnings.append({"kind": "source_missing", "source": "execution_frontier_json", "error": frontier_error})

    if lifecycle_loaded:
        lifecycle_state = lifecycle_payload.get("state", {}) if isinstance(lifecycle_payload.get("state"), dict) else {}
        lifecycle_route = lifecycle_state.get("active_route")
        lifecycle_status = lifecycle_state.get("status")
        if state_route and lifecycle_route and str(state_route) != str(lifecycle_route):
            warnings.append(
                {
                    "kind": "route_drift",
                    "source": "lifecycle_latest_json",
                    "state_active_route": state_route,
                    "lifecycle_active_route": lifecycle_route,
                }
            )
        if lifecycle_status and state.get("status") and str(lifecycle_status) != str(state.get("status")):
            warnings.append(
                {
                    "kind": "status_drift",
                    "source": "lifecycle_latest_json",
                    "state_status": state.get("status"),
                    "lifecycle_status": lifecycle_status,
                }
            )
    elif lifecycle_error:
        warnings.append({"kind": "source_missing", "source": "lifecycle_latest_json", "error": lifecycle_error})

    for name in ("execution_frontier_json", "lifecycle_latest_json"):
        age = sources[name].get("age_seconds")
        if isinstance(age, (int, float)) and age > stale_seconds:
            warnings.append({"kind": "diagnostic_source_stale", "source": name, "age_seconds": age})

    return {
        "schema_version": "flowpilot-watchdog-source-status/v1",
        "policy": (
            "Watchdog reset decisions trust only project-local state.json, latest heartbeat evidence, "
            "and busy_lease.json. execution_frontier.json, lifecycle/latest.json, automation metadata, "
            "and global records are diagnostic drift signals. Live subagent busy state is not a supported source."
        ),
        "trusted_for_decision": [
            "state_json",
            "latest_heartbeat",
            "busy_lease_json",
        ],
        "diagnostic_sources": [
            "execution_frontier_json",
            "lifecycle_latest_json",
            "automation_metadata",
            "global_record",
        ],
        "live_subagent_state_used": False,
        "sources": sources,
        "drift_warnings": warnings,
        "drift_warning_count": len(warnings),
    }


def _lease_expiry(payload: dict[str, Any]) -> datetime | None:
    explicit = parse_time(payload.get("expires_at"))
    if explicit is not None:
        return explicit
    started_at = parse_time(payload.get("started_at") or payload.get("created_at"))
    if started_at is None:
        return None
    raw_seconds = payload.get("max_seconds")
    if raw_seconds is None:
        raw_minutes = payload.get("max_minutes") or payload.get("lease_minutes")
        if raw_minutes is not None:
            try:
                raw_seconds = float(raw_minutes) * 60
            except (TypeError, ValueError):
                raw_seconds = None
    try:
        seconds = float(raw_seconds)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(
        started_at.timestamp() + max(0.0, seconds),
        tz=timezone.utc,
    )


def _lease_cleared_at(payload: dict[str, Any]) -> datetime | None:
    for field in ("cleared_at", "ended_at", "completed_at", "finished_at"):
        parsed = parse_time(payload.get(field))
        if parsed is not None:
            return parsed
    return None


def load_busy_lease(
    root: Path,
    lease_path_arg: str,
    *,
    now: datetime,
    active_route: Any,
    active_node: Any,
    heartbeat_timestamp: datetime | None,
    grace_seconds: float,
) -> BusyLeaseEvidence:
    path = Path(lease_path_arg)
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        return BusyLeaseEvidence(
            path=path,
            loaded=False,
            active=False,
            valid=False,
            expired=False,
            recently_cleared=False,
            grace_active=False,
            route_matches=False,
            node_matches=False,
            reason="missing",
            cleared_at=None,
            expires_at=None,
            grace_seconds=grace_seconds,
            grace_remaining_seconds=None,
            remaining_seconds=None,
            payload={},
        )
    try:
        payload = read_json(path)
    except Exception as exc:
        return BusyLeaseEvidence(
            path=path,
            loaded=False,
            active=False,
            valid=False,
            expired=False,
            recently_cleared=False,
            grace_active=False,
            route_matches=False,
            node_matches=False,
            reason=f"json_parse_error:{exc!r}",
            cleared_at=None,
            expires_at=None,
            grace_seconds=grace_seconds,
            grace_remaining_seconds=None,
            remaining_seconds=None,
            payload={},
        )

    status = str(payload.get("status") or "active").lower()
    active = status == "active"
    recently_cleared = status in {"cleared", "complete", "completed", "ended", "finished"}
    lease_route = payload.get("route_id")
    lease_node = payload.get("node_id")
    route_matches = not lease_route or not active_route or str(lease_route) == str(active_route)
    node_matches = not lease_node or not active_node or str(lease_node) == str(active_node)
    expires_at = _lease_expiry(payload)
    cleared_at = _lease_cleared_at(payload)
    if expires_at is None:
        expired = True
        remaining_seconds = None
    else:
        remaining_seconds = (expires_at - now).total_seconds()
        expired = remaining_seconds <= 0

    grace_remaining_seconds = None
    cleared_after_heartbeat = (
        cleared_at is not None
        and heartbeat_timestamp is not None
        and cleared_at >= heartbeat_timestamp
    )
    if cleared_at is not None:
        grace_remaining_seconds = grace_seconds - (now - cleared_at).total_seconds()
    grace_active = bool(
        recently_cleared
        and route_matches
        and node_matches
        and cleared_after_heartbeat
        and grace_remaining_seconds is not None
        and grace_remaining_seconds > 0
    )

    if not active:
        if grace_active:
            reason = "recently_cleared_grace"
        elif recently_cleared and not cleared_after_heartbeat:
            reason = "cleared_before_or_without_heartbeat"
        elif recently_cleared and grace_remaining_seconds is not None and grace_remaining_seconds <= 0:
            reason = "post_busy_grace_expired"
        else:
            reason = f"inactive_status:{status}"
    elif not route_matches:
        reason = "route_mismatch"
    elif not node_matches:
        reason = "node_mismatch"
    elif expires_at is None:
        reason = "missing_expiry"
    elif expired:
        reason = "expired"
    else:
        reason = "active_valid"

    return BusyLeaseEvidence(
        path=path,
        loaded=True,
        active=active,
        valid=reason == "active_valid",
        expired=expired,
        recently_cleared=recently_cleared,
        grace_active=grace_active,
        route_matches=route_matches,
        node_matches=node_matches,
        reason=reason,
        cleared_at=cleared_at,
        expires_at=expires_at,
        grace_seconds=grace_seconds,
        grace_remaining_seconds=grace_remaining_seconds,
        remaining_seconds=remaining_seconds,
        payload=payload,
    )


def automation_path(codex_home: Path, automation_id: str | None) -> Path | None:
    if not automation_id:
        return None
    path = codex_home / "automations" / automation_id / "automation.toml"
    return path if path.exists() else None


def load_automation(codex_home: Path, automation_id: str | None) -> dict[str, Any]:
    path = automation_path(codex_home, automation_id)
    if path is None:
        return {"automation_id": automation_id, "path": None, "loaded": False}
    data = read_toml(path)
    return {
        "automation_id": automation_id,
        "path": str(path),
        "loaded": True,
        "status": data.get("status"),
        "rrule": data.get("rrule"),
        "destination": data.get("destination"),
        "thread_id": data.get("thread_id") or data.get("target_thread_id"),
        "updated_at": data.get("updated_at"),
        "parse_error": data.get("_parse_error"),
    }


def last_jsonl_event_time(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        parsed = parse_time(payload.get("checked_at"))
        if parsed is not None:
            return parsed
    return None


def should_write_event(events_jsonl: Path, now: datetime, min_gap_seconds: int, force: bool) -> bool:
    if force:
        return True
    last_event_at = last_jsonl_event_time(events_jsonl)
    if last_event_at is None:
        return True
    return (now - last_event_at).total_seconds() >= min_gap_seconds


def default_global_record_dir(codex_home: Path) -> Path:
    configured = (
        os.environ.get("FLOWPILOT_GLOBAL_RECORD_DIR")
        or os.environ.get("FLOWPILOT_GLOBAL_DIR")
    )
    if configured:
        return Path(configured).expanduser().resolve()
    return (codex_home / "flowpilot" / "watchdog").resolve()


def stable_project_key(root: Path) -> str:
    normalized = str(root.resolve()).replace("\\", "/").lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _compact_checked_time(value: str) -> str:
    return value.replace(":", "").replace("-", "")


def _read_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": GLOBAL_SCHEMA_VERSION,
            "projects": {},
        }
    try:
        payload = read_json(path)
    except Exception:
        return {
            "schema_version": GLOBAL_SCHEMA_VERSION,
            "projects": {},
        }
    if not isinstance(payload.get("projects"), dict):
        payload["projects"] = {}
    payload["schema_version"] = payload.get("schema_version") or GLOBAL_SCHEMA_VERSION
    return payload


def _build_global_event(
    global_dir: Path,
    payload: dict[str, Any],
    local_record: dict[str, str | bool | None],
) -> dict[str, Any]:
    root = Path(str(payload.get("root") or ".")).resolve()
    project_key = stable_project_key(root)
    state = payload.get("state", {})
    heartbeat = payload.get("heartbeat", {})
    automation = payload.get("automation", {})
    lifecycle = payload.get("lifecycle", {})
    source_status = payload.get("source_status", {})
    decision = str(payload.get("decision") or "unknown")
    cooldown_key_material = "|".join(
        str(part or "")
        for part in (
            project_key,
            state.get("active_route"),
            state.get("active_node"),
            automation.get("official_reset", {}).get("automation_id"),
            heartbeat.get("heartbeat_id"),
            decision,
        )
    )
    cooldown_key = hashlib.sha256(cooldown_key_material.encode("utf-8")).hexdigest()[:24]
    return {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "event_type": "watchdog_poll",
        "checked_at": payload.get("checked_at"),
        "project_key": project_key,
        "project_root": str(root),
        "decision": decision,
        "ok": payload.get("ok"),
        "cooldown_key": cooldown_key,
        "local_record": {
            "latest_path": local_record.get("latest_path"),
            "event_path": local_record.get("event_path"),
            "events_jsonl": local_record.get("events_jsonl"),
        },
        "project": {
            "state_path": state.get("path"),
            "status": state.get("status"),
            "active_route": state.get("active_route"),
            "active_node": state.get("active_node"),
            "route_version": state.get("route_version"),
            "frontier_version": state.get("frontier_version"),
            "manual_stop": state.get("manual_stop"),
        },
        "heartbeat": {
            "heartbeat_id": heartbeat.get("heartbeat_id"),
            "timestamp": heartbeat.get("timestamp"),
            "timestamp_source": heartbeat.get("timestamp_source"),
            "age_seconds": heartbeat.get("age_seconds"),
            "stale": heartbeat.get("stale"),
            "age_stale": heartbeat.get("age_stale"),
        },
        "automation": {
            "heartbeat_automation_id": automation.get("official_reset", {}).get("automation_id"),
            "official_reset_required": automation.get("official_reset", {}).get("required"),
            "official_reset_attempted": automation.get("official_reset", {}).get("attempted"),
            "official_reset_ok": automation.get("official_reset", {}).get("ok"),
            "proof_required": automation.get("official_reset", {}).get("proof_required"),
        },
        "lifecycle": {
            "watchdog_automation_id": lifecycle.get("watchdog_automation_id"),
            "watchdog_automation_kind": lifecycle.get("watchdog_automation_kind"),
            "active": lifecycle.get("active"),
            "hidden_noninteractive": lifecycle.get("hidden_noninteractive"),
            "visible_window_risk": lifecycle.get("visible_window_risk"),
        },
        "source_status": {
            "trusted_for_decision": source_status.get("trusted_for_decision"),
            "diagnostic_sources": source_status.get("diagnostic_sources"),
            "drift_warning_count": source_status.get("drift_warning_count"),
            "live_subagent_state_used": source_status.get("live_subagent_state_used"),
        },
        "global_record_dir": str(global_dir),
    }


def write_global_records(
    global_dir: Path,
    payload: dict[str, Any],
    local_record: dict[str, str | bool | None],
    *,
    dry_run: bool,
    event_needed: bool,
) -> dict[str, Any]:
    root = Path(str(payload.get("root") or ".")).resolve()
    project_key = stable_project_key(root)
    event = _build_global_event(global_dir, payload, local_record)
    project_dir = global_dir / "projects" / project_key
    latest_path = project_dir / "latest.json"
    registry_path = global_dir / "registry.json"
    events_jsonl = global_dir / "events" / "events.jsonl"
    event_path = None
    if event_needed:
        event_path = (
            global_dir
            / "events"
            / f"{_compact_checked_time(str(payload.get('checked_at') or 'unknown'))}-{project_key}.json"
        )

    checked_at = parse_time(payload.get("checked_at")) or utc_now()
    status = str(payload.get("state", {}).get("status") or "").lower()
    manual_stop = bool(payload.get("state", {}).get("manual_stop"))
    registration_active = status in RUNNING_STATUSES and not manual_stop
    lease_expires_at = (
        checked_at + timedelta(minutes=REGISTRATION_LEASE_MINUTES)
        if registration_active
        else checked_at
    )
    result: dict[str, Any] = {
        "enabled": True,
        "written": False,
        "global_record_dir": str(global_dir),
        "project_key": project_key,
        "latest_path": str(latest_path),
        "registry_path": str(registry_path),
        "event_path": str(event_path) if event_path else None,
        "events_jsonl": str(events_jsonl) if event_needed else None,
        "global_supervisor_cadence_minutes": GLOBAL_SUPERVISOR_CADENCE_MINUTES,
        "registration_lease_minutes": REGISTRATION_LEASE_MINUTES,
        "registration_active": registration_active,
        "lease_expires_at": isoformat_z(lease_expires_at),
    }
    if dry_run:
        return result

    global_dir.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)
    registry = _read_registry(registry_path)
    registry["updated_at"] = payload.get("checked_at")
    registry["projects"][project_key] = {
        "project_key": project_key,
        "project_root": str(root),
        "status": payload.get("state", {}).get("status"),
        "active_route": payload.get("state", {}).get("active_route"),
        "active_node": payload.get("state", {}).get("active_node"),
        "route_version": payload.get("state", {}).get("route_version"),
        "frontier_version": payload.get("state", {}).get("frontier_version"),
        "last_heartbeat": payload.get("state", {}).get("last_heartbeat"),
        "latest_local_watchdog": local_record.get("latest_path"),
        "latest_global_watchdog": str(latest_path),
        "last_decision": payload.get("decision"),
        "last_checked_at": payload.get("checked_at"),
        "heartbeat_automation_id": payload.get("automation", {}).get("official_reset", {}).get("automation_id"),
        "manual_stop": manual_stop,
        "registration_active": registration_active,
        "registration_refreshed_at": payload.get("checked_at"),
        "lease_minutes": REGISTRATION_LEASE_MINUTES,
        "lease_expires_at": isoformat_z(lease_expires_at),
        "global_supervisor_required": registration_active,
    }
    if not registration_active:
        registry["projects"][project_key]["unregistered_at"] = payload.get("checked_at")
        registry["projects"][project_key]["unregister_reason"] = payload.get("decision")
    event["global_record"] = result
    write_json_atomic(latest_path, event)
    write_json_atomic(registry_path, registry)
    if event_path:
        event_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(event_path, event)
        with events_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    result["written"] = True
    return result


def planned_record_result(
    record_dir: Path,
    payload: dict[str, Any],
    *,
    dry_run: bool,
    event_needed: bool,
) -> dict[str, str | bool | None]:
    if dry_run:
        return {"written": False, "latest_path": None, "event_path": None, "events_jsonl": None}

    latest_path = record_dir / "latest.json"
    event_path: Path | None = None
    events_jsonl = record_dir / "events.jsonl"
    if event_needed:
        checked = payload["checked_at"].replace(":", "").replace("-", "")
        event_path = record_dir / "events" / f"watchdog-{checked}.json"
    return {
        "written": True,
        "latest_path": str(latest_path),
        "event_path": str(event_path) if event_path else None,
        "events_jsonl": str(events_jsonl) if event_needed else None,
    }


def write_records(
    payload: dict[str, Any],
    record_result: dict[str, str | bool | None],
    *,
    dry_run: bool,
    event_needed: bool,
) -> dict[str, str | bool | None]:
    if dry_run:
        return record_result

    latest_path_text = record_result.get("latest_path")
    if not latest_path_text:
        return record_result

    latest_path = Path(str(latest_path_text))
    payload_with_record = {**payload, "record": record_result}
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps(payload_with_record, indent=2, sort_keys=True), encoding="utf-8")

    event_path_text = record_result.get("event_path")
    event_path = Path(str(event_path_text)) if event_path_text else None
    events_jsonl_text = record_result.get("events_jsonl")
    events_jsonl = Path(str(events_jsonl_text)) if events_jsonl_text else None
    if event_path:
        event_path.parent.mkdir(parents=True, exist_ok=True)
        event_path.write_text(json.dumps(payload_with_record, indent=2, sort_keys=True), encoding="utf-8")
        if events_jsonl and event_needed:
            events_jsonl.parent.mkdir(parents=True, exist_ok=True)
            with events_jsonl.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload_with_record, sort_keys=True) + "\n")

    return record_result


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], bool, bool]:
    root = Path(args.root).resolve()
    now = utc_now()
    flowpilot_root = root / ".flowpilot"
    state_path = flowpilot_root / "state.json"
    if not state_path.exists():
        payload = {
            "schema_version": "flowpilot-watchdog/v1",
            "checked_at": isoformat_z(now),
            "root": str(root),
            "ok": False,
            "decision": "config_error",
            "error": ".flowpilot/state.json not found",
        }
        return payload, False, True

    state = read_json(state_path)
    active_route = state.get("active_route")
    state_status = str(state.get("status") or "unknown")
    route_path = flowpilot_root / "routes" / str(active_route) / "flow.json" if active_route else None
    route = read_json(route_path) if route_path and route_path.exists() else {}
    automation_id = args.automation_id or route.get("heartbeat_automation_id") or route.get("heartbeat_automation_name")
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
    automation_file = automation_path(codex_home, str(automation_id) if automation_id else None)
    automation_metadata = load_automation(codex_home, str(automation_id) if automation_id else None)

    heartbeat = load_heartbeat(root, state.get("last_heartbeat"))
    age_seconds = None
    if heartbeat.timestamp is not None:
        age_seconds = max(0.0, (now - heartbeat.timestamp).total_seconds())

    route_is_running = state_status in RUNNING_STATUSES
    route_is_terminal = state_status in TERMINAL_STATUSES or state_status == "paused"
    age_stale = route_is_running and (
        heartbeat.timestamp is None or age_seconds is None or age_seconds >= args.stale_minutes * 60
    )
    busy_lease_grace_seconds = max(
        0.0,
        float(args.heartbeat_interval_minutes)
        * 60.0
        * float(args.post_busy_grace_multiplier),
    )
    busy_lease = load_busy_lease(
        root,
        args.busy_lease_path,
        now=now,
        active_route=active_route,
        active_node=state.get("active_node"),
        heartbeat_timestamp=heartbeat.timestamp,
        grace_seconds=busy_lease_grace_seconds,
    )
    source_status = build_source_status(
        root=root,
        now=now,
        state_path=state_path,
        state=state,
        heartbeat=heartbeat,
        busy_lease=busy_lease,
        stale_seconds=args.stale_minutes * 60,
    )
    stale = age_stale and not (busy_lease.valid or busy_lease.grace_active)
    official_reset_attempted = bool(
        args.official_reset_attempted
        or args.official_reset_ok
        or args.official_reset_error
    )
    official_reset_result: dict[str, Any] = {
        "required": stale,
        "attempted": official_reset_attempted,
        "ok": True if args.official_reset_ok else (False if official_reset_attempted else None),
        "method": "codex_app.automation_update status=PAUSED then status=ACTIVE",
        "performed_by": "FlowPilot controller",
        "automation_id": automation_id,
        "automation_record_path": str(automation_file) if automation_file else None,
        "proof_required": "next_new_heartbeat",
    }
    if official_reset_attempted:
        official_reset_result["recorded_at"] = isoformat_z(now)
    if args.official_reset_error:
        official_reset_result["error"] = args.official_reset_error

    if route_is_terminal:
        decision = "inactive_terminal_route"
        ok = True
    elif age_stale and busy_lease.valid:
        decision = "busy_not_stale"
        ok = True
    elif age_stale and busy_lease.grace_active:
        decision = "post_busy_grace"
        ok = True
    elif stale:
        if official_reset_attempted:
            if official_reset_result.get("ok"):
                decision = "stale_official_reset_invoked"
            else:
                decision = "stale_official_reset_failed"
            ok = bool(official_reset_result.get("ok"))
        else:
            decision = "stale_official_reset_required"
            ok = False
    else:
        decision = "healthy"
        ok = True

    if decision == "stale_official_reset_required":
        recovery = {
            "kind": "official_automation_reset",
            "required_action": "Use the Codex app automation interface to set the active heartbeat automation to PAUSED, then ACTIVE.",
            "proof_required": "next_new_heartbeat",
        }
    elif decision == "stale_official_reset_invoked":
        recovery = {
            "kind": "official_automation_reset_invoked",
            "required_action": "Wait for the next heartbeat before claiming recovery.",
            "proof_required": "next_new_heartbeat",
        }
    elif decision == "stale_official_reset_failed":
        recovery = {
            "kind": "official_automation_reset_failed",
            "required_action": "Retry the official Codex app automation reset or record a concrete blocker.",
            "proof_required": "next_new_heartbeat",
        }
    elif decision == "busy_not_stale":
        recovery = {
            "kind": "suppressed_by_busy_lease",
            "required_action": "No reset while the matching busy lease is still active.",
            "proof_required": "lease_clear_or_next_new_heartbeat",
        }
    elif decision == "post_busy_grace":
        recovery = {
            "kind": "suppressed_by_post_busy_grace",
            "required_action": "No reset during the bounded post-busy grace window.",
            "proof_required": "grace_expiry_or_next_new_heartbeat",
        }
    elif decision == "config_error":
        recovery = {
            "kind": "configuration_blocker",
            "required_action": "Fix the watchdog configuration before judging heartbeat freshness.",
            "proof_required": "valid_watchdog_record",
        }
    else:
        recovery = {
            "kind": "none",
            "required_action": "No automation reset required.",
            "proof_required": "next_work_evidence_or_next_heartbeat",
        }

    payload = {
        "schema_version": "flowpilot-watchdog/v1",
        "checked_at": isoformat_z(now),
        "root": str(root),
        "threshold_minutes": args.stale_minutes,
        "ok": ok,
        "decision": decision,
        "boundary": (
            "The watchdog can detect stale FlowPilot heartbeat evidence and require an official Codex app "
            "automation reset. It suppresses reset while an active non-expired busy lease matches the "
            "current route/node, and during a bounded post-busy grace window after that lease is cleared, "
            "because Codex heartbeats cannot interrupt an already-running turn. It does not edit automation "
            "files directly, and reset is not proof of recovery until a new heartbeat appears. Reset "
            "decisions trust state.json, latest heartbeat evidence, and busy_lease.json only; frontier, "
            "lifecycle, automation, and global records are diagnostic drift signals, and live subagent busy "
            "state is not inspected."
        ),
        "source_status": source_status,
        "state": {
            "path": str(state_path),
            "status": state_status,
            "active_route": active_route,
            "active_node": state.get("active_node"),
            "last_heartbeat": state.get("last_heartbeat"),
            "next_action": state.get("next_action"),
            "route_version": state.get("route_version"),
            "frontier_version": state.get("frontier_version"),
            "plan_version": state.get("plan_version"),
            "manual_stop": bool(route_is_terminal or state_status == "paused"),
        },
        "route": {
            "path": str(route_path) if route_path else None,
            "loaded": bool(route),
            "heartbeat_automation_id": automation_id,
        },
        "lifecycle": {
            "paired_with_heartbeat": True,
            "heartbeat_automation_id": automation_id,
            "watchdog_automation_id": args.watchdog_automation_id or None,
            "watchdog_automation_kind": args.watchdog_automation_kind or None,
            "created_with_heartbeat": bool(args.watchdog_created_with_heartbeat),
            "active": bool(args.watchdog_automation_active),
            "hidden_noninteractive": bool(args.watchdog_hidden_noninteractive),
            "visible_window_risk": bool(args.watchdog_visible_window_risk),
            "stop_before_heartbeat": True,
            "terminal_shutdown_order": "write terminal state and unregister project global registration first; stop/delete project watchdog; then stop/delete heartbeat; delete user-level global supervisor last only after the registry has no active registrations",
        },
        "heartbeat": {
            "heartbeat_id": heartbeat.heartbeat_id,
            "path": str(heartbeat.path) if heartbeat.path else None,
            "timestamp": isoformat_z(heartbeat.timestamp) if heartbeat.timestamp else None,
            "timestamp_source": heartbeat.timestamp_source,
            "age_seconds": age_seconds,
            "age_minutes": None if age_seconds is None else round(age_seconds / 60, 3),
            "age_stale": age_stale,
            "stale": stale,
            "suppressed_by_busy_lease": bool(age_stale and busy_lease.valid),
            "suppressed_by_post_busy_grace": bool(age_stale and busy_lease.grace_active),
        },
        "busy_lease": {
            "path": str(busy_lease.path),
            "loaded": busy_lease.loaded,
            "active": busy_lease.active,
            "valid": busy_lease.valid,
            "expired": busy_lease.expired,
            "recently_cleared": busy_lease.recently_cleared,
            "grace_active": busy_lease.grace_active,
            "route_matches": busy_lease.route_matches,
            "node_matches": busy_lease.node_matches,
            "reason": busy_lease.reason,
            "lease_id": busy_lease.payload.get("lease_id"),
            "operation": busy_lease.payload.get("operation"),
            "route_id": busy_lease.payload.get("route_id"),
            "node_id": busy_lease.payload.get("node_id"),
            "cleared_at": isoformat_z(busy_lease.cleared_at) if busy_lease.cleared_at else None,
            "expires_at": isoformat_z(busy_lease.expires_at) if busy_lease.expires_at else None,
            "post_busy_grace_seconds": round(busy_lease.grace_seconds, 3),
            "post_busy_grace_remaining_seconds": None
            if busy_lease.grace_remaining_seconds is None
            else round(busy_lease.grace_remaining_seconds, 3),
            "remaining_seconds": None
            if busy_lease.remaining_seconds is None
            else round(busy_lease.remaining_seconds, 3),
        },
        "automation": {
            "metadata": automation_metadata,
            "official_reset": official_reset_result,
        },
        "recovery": recovery,
    }
    event_needed = (
        stale
        or bool(age_stale and busy_lease.valid)
        or bool(age_stale and busy_lease.grace_active)
        or args.write_healthy_event
        or decision == "config_error"
    )
    return payload, stale, event_needed


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect stale FlowPilot heartbeats and record official automation reset requirements.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--stale-minutes", type=float, default=float(os.environ.get("FLOWPILOT_WATCHDOG_STALE_MINUTES", "10")))
    parser.add_argument("--automation-id", default="", help="Override heartbeat automation id")
    parser.add_argument("--busy-lease-path", default=".flowpilot/busy_lease.json", help="Busy lease path relative to the project root")
    parser.add_argument("--heartbeat-interval-minutes", type=float, default=float(os.environ.get("FLOWPILOT_HEARTBEAT_INTERVAL_MINUTES", "1")), help="Expected heartbeat interval used for post-busy grace")
    parser.add_argument("--post-busy-grace-multiplier", type=float, default=float(os.environ.get("FLOWPILOT_POST_BUSY_GRACE_MULTIPLIER", "10")), help="Post-busy grace as a multiple of heartbeat interval")
    parser.add_argument("--watchdog-automation-id", default=os.environ.get("FLOWPILOT_WATCHDOG_AUTOMATION_ID", ""), help="External watchdog automation id or scheduled task name")
    parser.add_argument("--watchdog-automation-kind", default=os.environ.get("FLOWPILOT_WATCHDOG_AUTOMATION_KIND", ""), help="External watchdog automation kind, such as windows_task_scheduler")
    parser.add_argument("--watchdog-created-with-heartbeat", action="store_true", help="Record that this watchdog automation was created as the paired heartbeat watchdog")
    parser.add_argument("--watchdog-automation-active", action="store_true", help="Record that the external watchdog automation is expected to be active")
    parser.add_argument("--watchdog-hidden-noninteractive", action="store_true", help="Record that the watchdog task/action is hidden and does not open an interactive console")
    parser.add_argument("--watchdog-visible-window-risk", action="store_true", help="Record that the watchdog task/action may open a visible console window")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME; defaults to ~/.codex")
    parser.add_argument("--record-dir", default=".flowpilot/watchdog", help="Directory for watchdog latest.json and event records")
    parser.add_argument("--global-record-dir", default="", help="User-level FlowPilot watchdog record directory; defaults to CODEX_HOME/flowpilot/watchdog")
    parser.add_argument("--no-global-record", action="store_true", help="Do not write user-level global watchdog records")
    parser.add_argument("--min-event-gap-seconds", type=int, default=300, help="Minimum seconds between event JSONL records")
    parser.add_argument("--write-healthy-event", action="store_true", help="Also write event records for healthy checks")
    parser.add_argument("--official-reset-attempted", action="store_true", help="Record that FlowPilot invoked the official Codex app automation reset")
    parser.add_argument("--official-reset-ok", action="store_true", help="Record that the official automation reset call was accepted")
    parser.add_argument("--official-reset-error", default="", help="Record an error returned by the official automation reset call")
    parser.add_argument("--dry-run", action="store_true", help="Do not write watchdog evidence")
    parser.add_argument("--json", action="store_true", help="Print full JSON payload")
    parser.add_argument("--fail-on-stale", action="store_true", help="Return non-zero when stale even if evidence was written")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload, stale, event_needed = build_payload(args)

    root = Path(args.root).resolve()
    record_dir = root / args.record_dir
    events_jsonl = record_dir / "events.jsonl"
    force_event = payload.get("decision") == "config_error"
    event_allowed = event_needed and should_write_event(
        events_jsonl,
        parse_time(payload["checked_at"]) or utc_now(),
        args.min_event_gap_seconds,
        force=force_event,
    )
    record_result = planned_record_result(
        record_dir,
        payload,
        dry_run=args.dry_run,
        event_needed=event_allowed,
    )
    payload["record"] = record_result
    if args.no_global_record:
        payload["global_record"] = {"enabled": False, "written": False}
    else:
        codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
        global_dir = Path(args.global_record_dir).expanduser().resolve() if args.global_record_dir else default_global_record_dir(codex_home)
        payload["global_record"] = write_global_records(
            global_dir,
            payload,
            record_result,
            dry_run=args.dry_run,
            event_needed=event_allowed,
        )
    record_result = write_records(
        payload,
        record_result,
        dry_run=args.dry_run,
        event_needed=event_allowed,
    )
    payload["record"] = record_result

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        heartbeat = payload.get("heartbeat", {})
        print(
            f"{payload['decision']}: route={payload.get('state', {}).get('active_route')} "
            f"node={payload.get('state', {}).get('active_node')} "
            f"age_minutes={heartbeat.get('age_minutes')} stale={heartbeat.get('stale')}"
        )
        if record_result.get("latest_path"):
            print(f"record={record_result['latest_path']}")

    if payload.get("decision") == "config_error":
        return 3
    if args.fail_on_stale and stale:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
