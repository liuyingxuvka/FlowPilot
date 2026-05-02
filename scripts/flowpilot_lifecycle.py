"""FlowPilot lifecycle inventory and reconciliation helper.

This script is deliberately conservative. It scans the lifecycle authorities
that can drift apart during pause, restart, or terminal cleanup, then records a
single reconciliation snapshot and required actions. It does not call Codex app
automation APIs and it does not unregister Windows tasks by itself.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


RUNNING_STATUSES = {"running", "in_progress", "active"}
TERMINAL_STATUSES = {"complete", "completed", "blocked", "cancelled", "stopped", "paused"}
GLOBAL_SCHEMA_VERSION = "flowpilot-lifecycle/v1"


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


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_loaded": False, "_path": str(path)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_loaded": False, "_path": str(path), "_error": repr(exc)}
    if isinstance(payload, dict):
        payload["_loaded"] = True
        payload["_path"] = str(path)
        return payload
    return {"_loaded": False, "_path": str(path), "_error": "json_root_not_object"}


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
        "loaded": False,
    }
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key in {"id", "kind", "name", "prompt", "status", "rrule", "thread_id", "target_thread_id"}:
                record[key] = parse_toml_string_value(line)
        record["loaded"] = True
    except Exception as exc:
        record["error"] = repr(exc)
    return record


def _automation_matches(record: dict[str, Any], known_ids: set[str]) -> bool:
    text = " ".join(str(record.get(key) or "") for key in ("id", "name", "prompt", "path")).lower()
    if any(known.lower() in text for known in known_ids if known):
        return True
    return "flowpilot" in text or "global watchdog supervisor" in text


def _is_global_supervisor_record(record: dict[str, Any]) -> bool:
    text = " ".join(str(record.get(key) or "") for key in ("id", "name", "prompt", "path")).lower()
    return "global watchdog supervisor" in text or "flowpilot_global_supervisor.py" in text


def inspect_codex_automations(codex_home: Path, known_ids: set[str]) -> dict[str, Any]:
    automations_dir = codex_home / "automations"
    result: dict[str, Any] = {
        "authority": "codex_automations",
        "path": str(automations_dir),
        "loaded": automations_dir.exists(),
        "records": [],
        "active": [],
        "paused": [],
        "other": [],
    }
    if not automations_dir.exists():
        return result
    for automation_toml in automations_dir.glob("*/automation.toml"):
        record = read_automation_record(automation_toml)
        if not _automation_matches(record, known_ids):
            continue
        status = str(record.get("status") or "unknown").upper()
        result["records"].append(record)
        if status == "ACTIVE":
            result["active"].append(record)
        elif status == "PAUSED":
            result["paused"].append(record)
        else:
            result["other"].append(record)
    return result


def default_global_record_dir(codex_home: Path) -> Path:
    configured = (
        os.environ.get("FLOWPILOT_GLOBAL_RECORD_DIR")
        or os.environ.get("FLOWPILOT_GLOBAL_DIR")
    )
    if configured:
        return Path(configured).expanduser().resolve()
    return (codex_home / "flowpilot" / "watchdog").resolve()


def inspect_global_records(global_dir: Path, project_root: Path) -> dict[str, Any]:
    registry = read_json_if_exists(global_dir / "registry.json")
    projects = registry.get("projects") if isinstance(registry.get("projects"), dict) else {}
    normalized_root = str(project_root.resolve()).replace("\\", "/").lower()
    matches = []
    active_projects = []
    now = utc_now()
    if isinstance(projects, dict):
        for key, value in projects.items():
            if not isinstance(value, dict):
                continue
            root = str(value.get("project_root") or "").replace("\\", "/").lower()
            if root == normalized_root:
                matches.append({"project_key": key, **value})
            status = str(value.get("status") or "").lower()
            lease_expires_at = parse_time(value.get("lease_expires_at"))
            lease_expired = lease_expires_at is not None and lease_expires_at <= now
            if (
                value.get("registration_active")
                and status in RUNNING_STATUSES
                and not value.get("manual_stop")
                and not lease_expired
            ):
                active_projects.append({"project_key": key, **value})
    return {
        "authority": "global_watchdog_records",
        "path": str(global_dir),
        "registry_loaded": bool(registry.get("_loaded")),
        "matching_projects": matches,
        "active_project_count": len(active_projects),
        "active_project_keys": [item.get("project_key") for item in active_projects],
        "registry_error": registry.get("_error"),
    }


def inspect_windows_tasks() -> dict[str, Any]:
    result: dict[str, Any] = {
        "authority": "windows_task_scheduler",
        "platform": platform.system(),
        "available": False,
        "records": [],
        "error": None,
    }
    if platform.system().lower() != "windows":
        result["error"] = "not_windows"
        return result
    command = (
        "$ErrorActionPreference='Stop'; "
        "$tasks = Get-ScheduledTask | Where-Object { "
        "$_.TaskName -like '*FlowPilot*' -or $_.TaskName -like '*flowpilot*' "
        "}; "
        "$records = foreach ($task in $tasks) { "
        "$info = Get-ScheduledTaskInfo -TaskName $task.TaskName -TaskPath $task.TaskPath; "
        "[pscustomobject]@{ "
        "task_name=$task.TaskName; task_path=$task.TaskPath; state=$task.State.ToString(); "
        "enabled=$task.Settings.Enabled; hidden=$task.Settings.Hidden; "
        "last_run_time=$info.LastRunTime; next_run_time=$info.NextRunTime; "
        "last_task_result=$info.LastTaskResult; "
        "actions=@($task.Actions | ForEach-Object { ($_.Execute + ' ' + $_.Arguments).Trim() }) "
        "} "
        "}; "
        "$records | ConvertTo-Json -Depth 8"
    )
    try:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                command,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        result["error"] = repr(exc)
        return result
    if completed.returncode != 0:
        result["error"] = completed.stderr.strip() or f"powershell_exit:{completed.returncode}"
        return result
    text = completed.stdout.strip()
    result["available"] = True
    if not text:
        result["records"] = []
        return result
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        result["error"] = f"json_parse_error:{exc!r}"
        result["raw"] = text
        return result
    if isinstance(parsed, dict):
        result["records"] = [parsed]
    elif isinstance(parsed, list):
        result["records"] = parsed
    else:
        result["records"] = []
    return result


def collect_known_automation_ids(state: dict[str, Any], frontier: dict[str, Any], watchdog: dict[str, Any]) -> set[str]:
    ids = set()
    for payload in (state, frontier, watchdog):
        for key in ("heartbeat_automation_id", "watchdog_automation_id", "automation_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                ids.add(value)
    heartbeat = frontier.get("heartbeat_launcher") if isinstance(frontier.get("heartbeat_launcher"), dict) else {}
    watchdog_frontier = frontier.get("watchdog") if isinstance(frontier.get("watchdog"), dict) else {}
    watchdog_lifecycle = watchdog.get("lifecycle") if isinstance(watchdog.get("lifecycle"), dict) else {}
    watchdog_automation = watchdog.get("automation") if isinstance(watchdog.get("automation"), dict) else {}
    official_reset = watchdog_automation.get("official_reset") if isinstance(watchdog_automation.get("official_reset"), dict) else {}
    for payload in (heartbeat, watchdog_frontier, watchdog_lifecycle, official_reset):
        for key in ("automation_id", "heartbeat_automation_id", "watchdog_automation_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                ids.add(value)
    return ids


def classify_required_actions(
    mode: str,
    state: dict[str, Any],
    frontier: dict[str, Any],
    codex: dict[str, Any],
    global_records: dict[str, Any],
    windows: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    state_status = str(state.get("status") or "unknown").lower()
    frontier_heartbeat = frontier.get("heartbeat_launcher") if isinstance(frontier.get("heartbeat_launcher"), dict) else {}
    frontier_watchdog = frontier.get("watchdog") if isinstance(frontier.get("watchdog"), dict) else {}
    desired_inactive = mode in {"pause", "terminal"} or state_status in TERMINAL_STATUSES

    if desired_inactive:
        for record in codex.get("active", []):
            if _is_global_supervisor_record(record):
                if int(global_records.get("active_project_count") or 0) == 0:
                    actions.append(
                        {
                            "kind": "codex_automation_update",
                            "target": record.get("id") or record.get("path"),
                            "action": "delete_global_supervisor_last",
                            "reason": "no active FlowPilot project registrations remain after lifecycle reconciliation",
                        }
                    )
                continue
            actions.append(
                {
                    "kind": "codex_automation_update",
                    "target": record.get("id") or record.get("path"),
                    "action": "set_status_PAUSED",
                    "reason": "route pause/terminal requires no active FlowPilot heartbeat or supervisor automation",
                }
            )
    elif mode == "restart":
        if not codex.get("active"):
            actions.append(
                {
                    "kind": "codex_automation_update",
                    "target": frontier_heartbeat.get("automation_id"),
                    "action": "set_status_ACTIVE_or_create",
                    "reason": "route restart requires an active stable heartbeat automation",
                }
            )

    global_active = [
        item for item in global_records.get("matching_projects", [])
        if item.get("registration_active") or str(item.get("status") or "").lower() in RUNNING_STATUSES
    ]
    if desired_inactive and global_active:
        actions.append(
            {
                "kind": "global_record_writeback",
                "target": global_records.get("path"),
                "action": "mark_project_registration_inactive",
                "reason": "global registry still marks this route as active",
            }
        )

    windows_records = windows.get("records", [])
    if desired_inactive:
        for record in windows_records:
            actions.append(
                {
                    "kind": "windows_scheduled_task",
                    "target": record.get("task_name"),
                    "action": "unregister_or_explicitly_waive",
                    "reason": "disabled Windows FlowPilot tasks are still lifecycle residue unless explicitly retained",
                    "state": record.get("state"),
                    "enabled": record.get("enabled"),
                }
            )
    elif mode == "restart":
        disabled = [
            record for record in windows_records
            if str(record.get("state") or "").lower() == "disabled" or record.get("enabled") is False
        ]
        for record in disabled:
            actions.append(
                {
                    "kind": "windows_scheduled_task",
                    "target": record.get("task_name"),
                    "action": "unregister_then_recreate_or_enable_with_current_route",
                    "reason": "restart must not reuse stale disabled watchdog tasks blindly",
                    "state": record.get("state"),
                    "enabled": record.get("enabled"),
                }
            )

    if desired_inactive and (
        str(frontier_heartbeat.get("status") or "").upper() == "ACTIVE"
        or frontier_watchdog.get("active") is True
    ):
        actions.append(
            {
                "kind": "local_frontier_writeback",
                "target": frontier.get("_path"),
                "action": "write_inactive_lifecycle_snapshot",
                "reason": "local execution frontier still reports active heartbeat/watchdog lifecycle",
            }
        )

    return actions


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
    paths = resolve_flowpilot_paths(root)
    state = read_json_if_exists(Path(paths["state_path"]))
    frontier = read_json_if_exists(Path(paths["frontier_path"]))
    watchdog = read_json_if_exists(Path(paths["watchdog_dir"]) / "latest.json")
    known_ids = collect_known_automation_ids(state, frontier, watchdog)
    global_dir = Path(args.global_record_dir).expanduser().resolve() if args.global_record_dir else default_global_record_dir(codex_home)
    codex = inspect_codex_automations(codex_home, known_ids)
    global_records = inspect_global_records(global_dir, root)
    windows = inspect_windows_tasks() if args.include_windows_tasks else {
        "authority": "windows_task_scheduler",
        "available": False,
        "records": [],
        "error": "not_requested",
    }
    actions = classify_required_actions(args.mode, state, frontier, codex, global_records, windows)
    payload = {
        "schema_version": GLOBAL_SCHEMA_VERSION,
        "checked_at": isoformat_z(utc_now()),
        "mode": args.mode,
        "root": str(root),
        "layout": paths["layout"],
        "run_id": paths["run_id"],
        "run_root": str(paths["run_root"]),
        "ok": not actions,
        "decision": "reconciled" if not actions else "actions_required",
        "boundary": (
            "This helper scans lifecycle authorities and writes evidence only. "
            "Codex automations must be changed through the Codex app automation interface; "
            "Windows tasks must be unregistered or recreated through an explicit task helper."
        ),
        "state": {
            "path": state.get("_path"),
            "loaded": state.get("_loaded", False),
            "status": state.get("status"),
            "active_route": state.get("active_route"),
            "active_node": state.get("active_node"),
            "route_version": state.get("route_version"),
        },
        "frontier": {
            "path": frontier.get("_path"),
            "loaded": frontier.get("_loaded", False),
            "active_route": frontier.get("active_route"),
            "route_version": frontier.get("route_version"),
            "frontier_version": frontier.get("frontier_version"),
            "heartbeat_launcher": frontier.get("heartbeat_launcher"),
            "watchdog": frontier.get("watchdog"),
        },
        "watchdog": {
            "path": watchdog.get("_path"),
            "loaded": watchdog.get("_loaded", False),
            "decision": watchdog.get("decision"),
            "lifecycle": watchdog.get("lifecycle"),
            "global_record": watchdog.get("global_record"),
        },
        "codex_automations": codex,
        "global_records": global_records,
        "windows_tasks": windows,
        "required_actions": actions,
    }
    return payload


def write_lifecycle_record(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    record_dir = Path(resolve_flowpilot_paths(root)["lifecycle_dir"])
    latest_path = record_dir / "latest.json"
    events_jsonl = record_dir / "events.jsonl"
    write_json_atomic(latest_path, payload)
    record_dir.mkdir(parents=True, exist_ok=True)
    with events_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return {
        "written": True,
        "latest_path": str(latest_path),
        "events_jsonl": str(events_jsonl),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan FlowPilot lifecycle authorities before pause, restart, or terminal cleanup.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--mode", choices=("scan", "pause", "restart", "terminal"), default="scan")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME; defaults to ~/.codex")
    parser.add_argument("--global-record-dir", default="", help="Override user-level FlowPilot watchdog record directory")
    parser.add_argument("--include-windows-tasks", action="store_true", help="Scan Windows Task Scheduler for FlowPilot tasks")
    parser.add_argument("--write-record", action="store_true", help="Write active-run lifecycle/latest.json and events.jsonl")
    parser.add_argument("--fail-on-actions", action="store_true", help="Return non-zero when reconciliation actions are required")
    parser.add_argument("--json", action="store_true", help="Print full JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    payload = build_payload(args)
    if args.write_record:
        payload["record"] = write_lifecycle_record(Path(args.root).resolve(), payload)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            f"{payload['decision']}: mode={payload['mode']} "
            f"actions={len(payload.get('required_actions', []))}"
        )
        for action in payload.get("required_actions", []):
            print(f"- {action.get('kind')}: {action.get('target')} -> {action.get('action')}")
    if args.fail_on_actions and not payload.get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
