"""User-level singleton supervisor for FlowPilot watchdog records.

The local project watchdog writes full evidence under the active run's
`watchdog/`
and a compact copy under the user-level global FlowPilot watchdog directory.
This supervisor reads that global index, revalidates project-local evidence,
and writes local/global supervisor decisions.

Boundary: this script is the scanner/decision helper for a Codex global
automation. It does not call the Codex app automation API by itself. When it
finds a revalidated stale heartbeat, it records the exact controller action
that the Codex global automation must perform: official `PAUSED -> ACTIVE`
heartbeat reset, followed by a later-heartbeat proof check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


RUNNING_STATUSES = {"running", "in_progress", "active"}
TERMINAL_STATUSES = {"complete", "completed", "blocked", "cancelled", "stopped"}
GLOBAL_SCHEMA_VERSION = "flowpilot-global-supervisor/v1"
GLOBAL_SUPERVISOR_AUTOMATION_NAME = "FlowPilot Global Watchdog Supervisor"
GLOBAL_SUPERVISOR_CADENCE_MINUTES = 30
GLOBAL_SUPERVISOR_AUTOMATION_RRULE = "FREQ=MINUTELY;INTERVAL=30"
GLOBAL_SUPERVISOR_PROMPT_SOURCE = "templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md"
REGISTRATION_LEASE_MINUTES = GLOBAL_SUPERVISOR_CADENCE_MINUTES * 3


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def minutes_from_now(now: datetime, minutes: int) -> str:
    return isoformat_z(now + timedelta(minutes=minutes))


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


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp_path.replace(path)


def parse_toml_string_value(line: str) -> str:
    _, _, value = line.partition("=")
    text = value.strip()
    if len(text) >= 2 and text[0] == text[-1] == '"':
        return text[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return text


def read_automation_record(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = {
        "path": str(path),
        "parse_error": None,
    }
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key in {"id", "kind", "name", "prompt", "status", "rrule"}:
                record[key] = parse_toml_string_value(line)
    except Exception as exc:
        record["parse_error"] = repr(exc)
    return record


def is_global_supervisor_automation(record: dict[str, Any]) -> bool:
    haystack = " ".join(
        str(record.get(key) or "")
        for key in ("id", "name", "prompt")
    ).lower()
    return (
        str(record.get("kind") or "").lower() == "cron"
        and (
            "flowpilot global watchdog supervisor" in haystack
            or "flowpilot_global_supervisor.py" in haystack
            or "global watchdog supervisor" in haystack
        )
    )


def codex_automation_contract(workspace: Path) -> dict[str, Any]:
    return {
        "singleton_name": GLOBAL_SUPERVISOR_AUTOMATION_NAME,
        "lookup_policy": "Inspect existing Codex cron automations first. Reuse one active singleton at the fixed 30-minute cadence; reactivate/update one paused singleton when active project registrations exist; create only when no singleton exists and at least one active registration exists. Never create duplicates.",
        "teardown_policy": "Project heartbeats refresh their own global registration lease. A route unregisters itself on pause, stop, or completion. Delete the user-level global supervisor only after rereading the registry under the singleton lock and confirming that no active, unexpired registrations remain.",
        "prompt_source": GLOBAL_SUPERVISOR_PROMPT_SOURCE,
        "automation_update_create": {
            "mode": "create",
            "kind": "cron",
            "name": GLOBAL_SUPERVISOR_AUTOMATION_NAME,
            "prompt": f"Use the task prompt from {GLOBAL_SUPERVISOR_PROMPT_SOURCE}.",
            "rrule": GLOBAL_SUPERVISOR_AUTOMATION_RRULE,
            "cwds": str(workspace.resolve()),
            "executionEnvironment": "local",
            "model": "gpt-5.2",
            "reasoningEffort": "medium",
            "status": "ACTIVE",
        },
        "important_parameter_shape": [
            "Use a string for cwds with the current Codex automation_update interface.",
            "Use kind=cron, not heartbeat, because this supervisor is user-level and not owned by one thread.",
            "Use rrule=FREQ=MINUTELY;INTERVAL=30. The global supervisor cadence is fixed, not user-configurable.",
        ],
    }


def inspect_codex_automation_singleton(
    codex_home: Path,
    workspace: Path,
    *,
    active_registration_count: int | None = None,
) -> dict[str, Any]:
    automations_dir = codex_home / "automations"
    result: dict[str, Any] = {
        "automations_dir": str(automations_dir),
        "exists": False,
        "active_count": 0,
        "paused_count": 0,
        "candidates": [],
        "recommended_action": "create" if active_registration_count != 0 else "none_needed",
        "active_registration_count": active_registration_count,
        "contract": codex_automation_contract(workspace),
    }
    if not automations_dir.exists():
        result["recommended_action"] = "create" if active_registration_count != 0 else "none_needed"
        result["reason"] = "codex_automations_dir_missing"
        return result

    candidates: list[dict[str, Any]] = []
    for automation_toml in automations_dir.glob("*/automation.toml"):
        record = read_automation_record(automation_toml)
        if is_global_supervisor_automation(record):
            candidates.append(record)

    active = [
        record for record in candidates
        if str(record.get("status") or "").upper() == "ACTIVE"
    ]
    paused = [
        record for record in candidates
        if str(record.get("status") or "").upper() == "PAUSED"
    ]
    result["exists"] = bool(candidates)
    result["active_count"] = len(active)
    result["paused_count"] = len(paused)
    result["candidates"] = candidates
    if active_registration_count == 0:
        if active:
            result["recommended_action"] = "delete_active_no_registered_projects"
            result["target_id"] = active[0].get("id")
        elif paused:
            result["recommended_action"] = "delete_paused_no_registered_projects"
            result["target_id"] = paused[0].get("id")
        else:
            result["recommended_action"] = "none_needed"
        return result

    if len(active) == 1:
        result["active_id"] = active[0].get("id")
        if str(active[0].get("rrule") or "") != GLOBAL_SUPERVISOR_AUTOMATION_RRULE:
            result["recommended_action"] = "update_active_to_fixed_30m"
            result["target_id"] = active[0].get("id")
        else:
            result["recommended_action"] = "reuse_active"
    elif len(active) > 1:
        result["recommended_action"] = "dedupe_human_review"
        result["reason"] = "multiple_active_global_supervisors"
    elif paused:
        result["recommended_action"] = "update_existing_to_active"
        result["target_id"] = paused[0].get("id")
        result["required_rrule"] = GLOBAL_SUPERVISOR_AUTOMATION_RRULE
    else:
        result["recommended_action"] = "create"
    return result


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


def load_registry(global_dir: Path) -> dict[str, Any]:
    path = global_dir / "registry.json"
    if not path.exists():
        return {"schema_version": "flowpilot-global-watchdog/v1", "projects": {}}
    try:
        payload = read_json(path)
    except Exception as exc:
        return {
            "schema_version": "flowpilot-global-watchdog/v1",
            "projects": {},
            "error": f"registry_parse_error:{exc!r}",
        }
    if not isinstance(payload.get("projects"), dict):
        payload["projects"] = {}
    return payload


def registry_project_is_active(entry: dict[str, Any], *, now: datetime) -> bool:
    if not bool(entry.get("registration_active")):
        return False
    status = str(entry.get("status") or "").lower()
    if status in TERMINAL_STATUSES or status == "paused" or bool(entry.get("manual_stop")):
        return False
    lease_expires_at = parse_time(entry.get("lease_expires_at"))
    if lease_expires_at is not None and lease_expires_at <= now:
        return False
    return True


def active_registry_projects(registry: dict[str, Any], *, now: datetime) -> list[dict[str, Any]]:
    active: list[dict[str, Any]] = []
    projects = registry.get("projects", {})
    if not isinstance(projects, dict):
        return active
    for key, entry in projects.items():
        if not isinstance(entry, dict):
            continue
        if registry_project_is_active(entry, now=now):
            active.append({"project_key": key, **entry})
    return active


def registry_lifecycle_decision(
    registry: dict[str, Any],
    codex_home: Path,
    workspace: Path,
    *,
    now: datetime,
) -> dict[str, Any]:
    active = active_registry_projects(registry, now=now)
    singleton = inspect_codex_automation_singleton(
        codex_home,
        workspace,
        active_registration_count=len(active),
    )
    return {
        "active_registration_count": len(active),
        "active_project_keys": [entry.get("project_key") for entry in active],
        "global_supervisor_required": bool(active),
        "delete_allowed": not active,
        "delete_order": (
            "Unregister the project lease first, stop project heartbeat/watchdog, "
            "then reread the global registry under the singleton lock. Delete the "
            "user-level global supervisor last only when no active, unexpired "
            "registrations remain."
        ),
        "codex_automation_singleton": singleton,
    }


def acquire_lock(global_dir: Path, *, now: datetime, max_age_seconds: int, dry_run: bool) -> tuple[bool, dict[str, Any]]:
    lock_dir = global_dir / "supervisor"
    lock_path = lock_dir / "leader.lock"
    if dry_run:
        return True, {
            "acquired": True,
            "dry_run": True,
            "path": str(lock_path),
        }
    lock_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "pid": os.getpid(),
        "started_at": isoformat_z(now),
        "lock_path": str(lock_path),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(str(lock_path), flags)
    except FileExistsError:
        try:
            existing = read_json(lock_path)
        except Exception:
            existing = {}
        started_at = parse_time(existing.get("started_at"))
        stale = started_at is None or (now - started_at).total_seconds() > max_age_seconds
        if not stale:
            return False, {
                "acquired": False,
                "path": str(lock_path),
                "reason": "singleton_already_active",
                "existing": existing,
            }
        try:
            lock_path.unlink()
        except OSError:
            return False, {
                "acquired": False,
                "path": str(lock_path),
                "reason": "stale_lock_unlink_failed",
                "existing": existing,
            }
        fd = os.open(str(lock_path), flags)
    with os.fdopen(fd, "wb") as handle:
        handle.write(encoded)
    return True, {
        "acquired": True,
        "path": str(lock_path),
        "payload": payload,
    }


def release_lock(lock: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run or not lock.get("acquired"):
        return
    path_text = lock.get("path")
    if not path_text:
        return
    path = Path(path_text)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _project_status(project_root: Path) -> dict[str, Any]:
    paths = resolve_flowpilot_paths(project_root)
    state_path = Path(paths["state_path"])
    try:
        state = read_json(state_path)
    except Exception as exc:
        return {
            "loaded": False,
            "state_path": str(state_path),
            "error": repr(exc),
            "status": "unknown",
        }
    return {
        "loaded": True,
        "layout": paths["layout"],
        "run_id": paths["run_id"],
        "run_root": str(paths["run_root"]),
        "state_path": str(state_path),
        "status": state.get("status"),
        "active_route": state.get("active_route"),
        "active_node": state.get("active_node"),
        "route_version": state.get("route_version"),
        "frontier_version": state.get("frontier_version"),
        "last_heartbeat": state.get("last_heartbeat"),
        "manual_stop": bool(
            str(state.get("status") or "").lower() in TERMINAL_STATUSES
            or str(state.get("status") or "").lower() == "paused"
        ),
    }


def update_project_registration(args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
    global_dir = Path(args.global_record_dir).expanduser().resolve() if args.global_record_dir else default_global_record_dir(codex_home)
    project_root = Path(args.root).expanduser().resolve()
    project_key = stable_project_key(project_root)
    active_request = bool(args.refresh_registration and not args.unregister_project)
    project = _project_status(project_root)
    status = str(project.get("status") or "unknown").lower()
    registration_active = (
        active_request
        and status in RUNNING_STATUSES
        and not bool(project.get("manual_stop"))
    )
    lease_expires_at = minutes_from_now(now, REGISTRATION_LEASE_MINUTES) if registration_active else isoformat_z(now)

    acquired, lock = acquire_lock(global_dir, now=now, max_age_seconds=args.max_lock_seconds, dry_run=args.dry_run)
    payload: dict[str, Any] = {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "checked_at": isoformat_z(now),
        "global_record_dir": str(global_dir),
        "project_key": project_key,
        "project_root": str(project_root),
        "action": "refresh_registration" if active_request else "unregister_project",
        "registration_active": registration_active,
        "lease_minutes": REGISTRATION_LEASE_MINUTES,
        "lease_expires_at": lease_expires_at,
        "project": project,
        "lock": lock,
    }
    if not acquired:
        payload["ok"] = False
        payload["decision"] = "singleton_already_active"
        return payload

    try:
        registry = load_registry(global_dir)
        entry = {
            **(
                registry.get("projects", {}).get(project_key, {})
                if isinstance(registry.get("projects"), dict)
                and isinstance(registry.get("projects", {}).get(project_key), dict)
                else {}
            ),
            "project_key": project_key,
            "project_root": str(project_root),
            "status": project.get("status"),
            "active_route": project.get("active_route"),
            "active_node": project.get("active_node"),
            "route_version": project.get("route_version"),
            "frontier_version": project.get("frontier_version"),
            "last_heartbeat": project.get("last_heartbeat"),
            "latest_local_watchdog": str(Path(resolve_flowpilot_paths(project_root)["watchdog_dir"]) / "latest.json"),
            "latest_global_watchdog": str(global_dir / "projects" / project_key / "latest.json"),
            "heartbeat_automation_id": args.heartbeat_automation_id or None,
            "manual_stop": bool(project.get("manual_stop")),
            "registration_active": registration_active,
            "registration_refreshed_at": isoformat_z(now),
            "lease_minutes": REGISTRATION_LEASE_MINUTES,
            "lease_expires_at": lease_expires_at,
            "global_supervisor_required": registration_active,
        }
        if registration_active:
            entry.pop("unregistered_at", None)
            entry.pop("unregister_reason", None)
        else:
            entry["unregistered_at"] = isoformat_z(now)
            entry["unregister_reason"] = args.unregister_reason or (
                "project_not_running" if active_request else "project_unregistered"
            )
        registry.setdefault("projects", {})
        registry["schema_version"] = registry.get("schema_version") or "flowpilot-global-watchdog/v1"
        registry["updated_at"] = isoformat_z(now)
        registry["projects"][project_key] = entry
        payload["entry"] = entry
        payload["global_supervisor_lifecycle"] = registry_lifecycle_decision(
            registry,
            codex_home,
            Path.cwd(),
            now=now,
        )
        payload["ok"] = True
        payload["decision"] = "registered" if registration_active else "unregistered"
        if not args.dry_run:
            write_json_atomic(global_dir / "registry.json", registry)
            event_path = global_dir / "registration" / "events.jsonl"
            event_path.parent.mkdir(parents=True, exist_ok=True)
            with event_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload
    finally:
        release_lock(lock, dry_run=args.dry_run)


def write_project_supervisor_record(
    project_root: Path,
    result: dict[str, Any],
    *,
    dry_run: bool,
    event_needed: bool,
) -> dict[str, Any]:
    record_dir = Path(resolve_flowpilot_paths(project_root)["watchdog_dir"])
    latest_path = record_dir / "global_supervisor.json"
    events_jsonl = record_dir / "global_supervisor_events.jsonl"
    write_result = {
        "written": False,
        "latest_path": str(latest_path),
        "events_jsonl": str(events_jsonl) if event_needed else None,
    }
    if not (project_root / ".flowpilot").exists():
        write_result["reason"] = "project_flowpilot_dir_missing"
        return write_result
    if dry_run:
        return write_result
    record = {**result, "local_writeback": write_result}
    write_json_atomic(latest_path, record)
    if event_needed:
        record_dir.mkdir(parents=True, exist_ok=True)
        with events_jsonl.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    write_result["written"] = True
    return write_result


def classify_project(entry: dict[str, Any], global_dir: Path, *, now: datetime) -> dict[str, Any]:
    project_root = Path(str(entry.get("project_root") or "")).expanduser()
    if not project_root.is_absolute():
        project_root = project_root.resolve()
    expected_key = stable_project_key(project_root) if str(project_root) else str(entry.get("project_key") or "unknown")
    project_key = str(entry.get("project_key") or expected_key)
    global_latest_path = Path(str(entry.get("latest_global_watchdog") or global_dir / "projects" / project_key / "latest.json"))
    local_latest_path = Path(str(entry.get("latest_local_watchdog") or project_root / ".flowpilot" / "watchdog" / "latest.json"))
    state_path = project_root / ".flowpilot" / "state.json"

    result: dict[str, Any] = {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "checked_at": isoformat_z(now),
        "project_key": project_key,
        "project_root": str(project_root),
        "global_latest_path": str(global_latest_path),
        "local_latest_path": str(local_latest_path),
        "state_path": str(state_path),
        "decision": "unknown",
        "reset_required": False,
        "controller_action_required": None,
        "controller_action": {
            "required": False,
            "kind": "none",
            "heartbeat_automation_id": entry.get("heartbeat_automation_id"),
            "method": "none",
        },
        "reason": "",
    }
    lease_expires_at = parse_time(entry.get("lease_expires_at"))
    lease_expired = lease_expires_at is not None and lease_expires_at <= now
    result["registration"] = {
        "active": bool(entry.get("registration_active")),
        "lease_expires_at": isoformat_z(lease_expires_at) if lease_expires_at else None,
        "lease_expired": lease_expired,
        "registration_refreshed_at": entry.get("registration_refreshed_at"),
    }

    if not bool(entry.get("registration_active")):
        result.update(
            decision="inactive_registration",
            reason="project registration is inactive; do not reset heartbeat",
        )
        return result

    if lease_expired:
        result.update(
            decision="expired_registration_lease",
            reason="project registration lease expired; do not reset heartbeat",
        )
        return result

    if not state_path.exists():
        result.update(
            decision="missing_project_state",
            reason="project-local active-run state.json is missing",
        )
        return result

    try:
        state = read_json(state_path)
    except Exception as exc:
        result.update(
            decision="unreadable_project_state",
            reason=f"state_parse_error:{exc!r}",
        )
        return result

    try:
        local_latest = read_json(local_latest_path) if local_latest_path.exists() else {}
    except Exception as exc:
        local_latest = {"_parse_error": repr(exc)}

    try:
        global_latest = read_json(global_latest_path) if global_latest_path.exists() else {}
    except Exception as exc:
        global_latest = {"_parse_error": repr(exc)}

    state_status = str(state.get("status") or "unknown")
    local_decision = str(local_latest.get("decision") or entry.get("last_decision") or "unknown")
    event_project = global_latest.get("project", {}) if isinstance(global_latest.get("project"), dict) else {}
    queued_generation = event_project.get("route_version")
    current_generation = state.get("route_version")
    terminal_or_manual = (
        state_status in TERMINAL_STATUSES
        or state_status == "paused"
        or bool(event_project.get("manual_stop"))
    )

    result["state"] = {
        "status": state_status,
        "active_route": state.get("active_route"),
        "active_node": state.get("active_node"),
        "route_version": current_generation,
        "last_heartbeat": state.get("last_heartbeat"),
    }
    result["local_decision"] = local_decision
    result["heartbeat_automation_id"] = (
        entry.get("heartbeat_automation_id")
        or local_latest.get("route", {}).get("heartbeat_automation_id")
        or local_latest.get("automation", {}).get("official_reset", {}).get("automation_id")
    )
    result["controller_action"]["heartbeat_automation_id"] = result["heartbeat_automation_id"]
    result["queued_route_generation"] = queued_generation
    result["global_latest_loaded"] = bool(global_latest)
    result["local_latest_loaded"] = bool(local_latest)

    if terminal_or_manual:
        result.update(
            decision="expired_terminal_or_manual_stop",
            reason="project route is terminal, paused, or manually stopped; do not reset heartbeat",
        )
        return result

    if queued_generation is not None and current_generation is not None and queued_generation != current_generation:
        result.update(
            decision="superseded_generation",
            reason="global event was for an old route generation",
        )
        return result

    if local_decision == "stale_official_reset_required" and state_status in RUNNING_STATUSES:
        result.update(
            decision="reset_required_revalidated",
            reset_required=True,
            controller_action_required="Use Codex app automation_update to PAUSE and then ACTIVATE the heartbeat automation; recovery proof is the next heartbeat.",
            controller_action={
                "required": True,
                "kind": "codex_app_automation_update",
                "heartbeat_automation_id": result.get("heartbeat_automation_id"),
                "method": "PAUSED then ACTIVE",
                "proof_required": "next_new_heartbeat",
            },
            reason="local stale watchdog evidence still matches a running project route",
        )
        return result

    if local_decision in {"stale_official_reset_invoked", "stale_official_reset_failed"}:
        result.update(
            decision="awaiting_or_failed_reset_proof",
            reason="local evidence already records reset attempt state; wait for new heartbeat or controller follow-up",
        )
        return result

    result.update(
        decision="no_reset_required",
        reason=f"local watchdog decision is {local_decision}",
    )
    return result


def run_supervisor(args: argparse.Namespace) -> dict[str, Any]:
    now = utc_now()
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
    global_dir = Path(args.global_record_dir).expanduser().resolve() if args.global_record_dir else default_global_record_dir(codex_home)
    registry = load_registry(global_dir)
    lifecycle = registry_lifecycle_decision(registry, codex_home, Path.cwd(), now=now)
    payload: dict[str, Any] = {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "checked_at": isoformat_z(now),
        "global_record_dir": str(global_dir),
        "boundary": "This user-level singleton revalidates project-local watchdog evidence and records reset requirements. It does not call Codex automation APIs directly.",
        "active_registration_count": lifecycle["active_registration_count"],
        "global_supervisor_lifecycle": lifecycle,
        "codex_automation_singleton": lifecycle["codex_automation_singleton"],
        "projects": [],
    }
    if args.status:
        payload["decision"] = "status_only"
        payload["registry"] = {
            "path": str(global_dir / "registry.json"),
            "project_count": len(registry.get("projects", {})),
            "active_registration_count": lifecycle["active_registration_count"],
            "updated_at": registry.get("updated_at"),
            "error": registry.get("error"),
        }
        return payload

    acquired, lock = acquire_lock(global_dir, now=now, max_age_seconds=args.max_lock_seconds, dry_run=args.dry_run)
    payload["lock"] = lock
    if not acquired:
        payload["decision"] = "singleton_already_active"
        payload["ok"] = True
        return payload

    try:
        projects = registry.get("projects", {})
        reset_required_count = 0
        event_count = 0
        registry_changed = False
        for entry in projects.values():
            if not isinstance(entry, dict):
                continue
            result = classify_project(entry, global_dir, now=now)
            event_needed = args.write_healthy_event or result["decision"] in {
                "inactive_registration",
                "expired_registration_lease",
                "missing_project_state",
                "unreadable_project_state",
                "expired_terminal_or_manual_stop",
                "superseded_generation",
                "reset_required_revalidated",
                "awaiting_or_failed_reset_proof",
            }
            result["local_writeback"] = write_project_supervisor_record(
                Path(str(result["project_root"])),
                result,
                dry_run=args.dry_run,
                event_needed=event_needed,
            )
            if result.get("reset_required"):
                reset_required_count += 1
            if event_needed:
                event_count += 1
            if result["decision"] in {
                "expired_registration_lease",
                "expired_terminal_or_manual_stop",
                "missing_project_state",
                "unreadable_project_state",
            } and entry.get("registration_active"):
                entry["registration_active"] = False
                entry["unregistered_at"] = isoformat_z(now)
                entry["unregister_reason"] = result["decision"]
                registry_changed = True
            payload["projects"].append(result)

        if registry_changed:
            registry["updated_at"] = isoformat_z(now)
        after_lifecycle = registry_lifecycle_decision(registry, codex_home, Path.cwd(), now=now)
        payload["ok"] = True
        payload["decision"] = "processed"
        payload["project_count"] = len(payload["projects"])
        payload["active_registration_count_after"] = after_lifecycle["active_registration_count"]
        payload["global_supervisor_lifecycle_after"] = after_lifecycle
        payload["reset_required_count"] = reset_required_count
        payload["event_count"] = event_count
        if not args.dry_run:
            if registry_changed:
                write_json_atomic(global_dir / "registry.json", registry)
            supervisor_dir = global_dir / "supervisor"
            write_json_atomic(supervisor_dir / "latest.json", payload)
            if event_count or args.write_healthy_event:
                with (supervisor_dir / "events.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
        return payload
    finally:
        release_lock(lock, dry_run=args.dry_run)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Process user-level FlowPilot watchdog records as a singleton global supervisor.")
    parser.add_argument("--root", default=".", help="Project root for registration refresh/unregister actions")
    parser.add_argument("--global-record-dir", default="", help="User-level FlowPilot watchdog record directory; defaults to CODEX_HOME/flowpilot/watchdog")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME; defaults to ~/.codex")
    parser.add_argument("--max-lock-seconds", type=int, default=600, help="Treat the singleton lock as stale after this many seconds")
    parser.add_argument("--refresh-registration", action="store_true", help="Refresh this project's global supervisor registration lease")
    parser.add_argument("--unregister-project", action="store_true", help="Mark this project's global supervisor registration inactive")
    parser.add_argument("--unregister-reason", default="", help="Reason recorded when unregistering a project")
    parser.add_argument("--heartbeat-automation-id", default="", help="Heartbeat automation id to record during registration refresh")
    parser.add_argument("--write-healthy-event", action="store_true", help="Also write event records for no-reset projects")
    parser.add_argument("--status", action="store_true", help="Show registry status without processing or acquiring the singleton lock")
    parser.add_argument("--dry-run", action="store_true", help="Do not write supervisor evidence")
    parser.add_argument("--json", action="store_true", help="Print full JSON payload")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.refresh_registration or args.unregister_project:
        payload = update_project_registration(args)
    else:
        payload = run_supervisor(args)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"{payload.get('decision')}: projects={payload.get('project_count', 0)} "
            f"reset_required={payload.get('reset_required_count', 0)}"
        )
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
