"""FlowPilot lifecycle inventory for heartbeat/manual-resume continuation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


RUNNING_STATUSES = {"running", "in_progress", "active"}
TERMINAL_STATUSES = {"complete", "completed", "blocked", "cancelled", "stopped", "paused"}
SCHEMA_VERSION = "flowpilot-lifecycle/v2"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    record: dict[str, Any] = {"path": str(path), "loaded": False}
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


def automation_matches_flowpilot(record: dict[str, Any], known_ids: set[str]) -> bool:
    text = " ".join(str(record.get(key) or "") for key in ("id", "name", "prompt", "path")).lower()
    if any(known.lower() in text for known in known_ids if known):
        return True
    return "flowpilot" in text


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
        if not automation_matches_flowpilot(record, known_ids):
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


def collect_known_automation_ids(state: dict[str, Any], frontier: dict[str, Any]) -> set[str]:
    ids = set()
    for payload in (state, frontier):
        for key in ("heartbeat_automation_id", "automation_id"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                ids.add(value)
    heartbeat = frontier.get("heartbeat_launcher") if isinstance(frontier.get("heartbeat_launcher"), dict) else {}
    for key in ("automation_id", "heartbeat_automation_id"):
        value = heartbeat.get(key)
        if isinstance(value, str) and value:
            ids.add(value)
    return ids


def classify_required_actions(
    mode: str,
    state: dict[str, Any],
    frontier: dict[str, Any],
    codex: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    state_status = str(state.get("status") or "unknown").lower()
    frontier_heartbeat = frontier.get("heartbeat_launcher") if isinstance(frontier.get("heartbeat_launcher"), dict) else {}
    desired_inactive = mode in {"pause", "terminal"} or state_status in TERMINAL_STATUSES

    if desired_inactive:
        for record in codex.get("active", []):
            actions.append(
                {
                    "kind": "codex_automation_update",
                    "target": record.get("id") or record.get("path"),
                    "action": "set_status_PAUSED",
                    "reason": "route pause or terminal state requires no active FlowPilot heartbeat automation",
                }
            )
    elif mode == "restart" and not codex.get("active"):
        actions.append(
            {
                "kind": "codex_automation_update",
                "target": frontier_heartbeat.get("automation_id"),
                "action": "set_status_ACTIVE_or_create",
                "reason": "route restart requires an active stable heartbeat automation",
            }
        )

    if desired_inactive and str(frontier_heartbeat.get("status") or "").upper() == "ACTIVE":
        actions.append(
            {
                "kind": "local_frontier_writeback",
                "target": frontier.get("_path"),
                "action": "write_inactive_heartbeat_lifecycle_snapshot",
                "reason": "local execution frontier still reports active heartbeat lifecycle",
            }
        )

    return actions


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    codex_home = Path(args.codex_home or os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).resolve()
    paths = resolve_flowpilot_paths(root)
    state = read_json_if_exists(Path(paths["state_path"]))
    frontier = read_json_if_exists(Path(paths["frontier_path"]))
    known_ids = collect_known_automation_ids(state, frontier)
    codex = inspect_codex_automations(codex_home, known_ids)
    actions = classify_required_actions(args.mode, state, frontier, codex)
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": isoformat_z(utc_now()),
        "mode": args.mode,
        "root": str(root),
        "layout": paths["layout"],
        "run_id": paths["run_id"],
        "run_root": str(paths["run_root"]),
        "ok": not actions,
        "decision": "reconciled" if not actions else "actions_required",
        "boundary": (
            "This helper scans FlowPilot heartbeat/manual-resume lifecycle evidence only. "
            "Codex automations must be changed through the Codex app automation interface."
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
        },
        "codex_automations": codex,
        "required_actions": actions,
    }


def write_lifecycle_record(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    record_dir = Path(resolve_flowpilot_paths(root)["lifecycle_dir"])
    latest_path = record_dir / "latest.json"
    events_jsonl = record_dir / "events.jsonl"
    write_json_atomic(latest_path, payload)
    record_dir.mkdir(parents=True, exist_ok=True)
    with events_jsonl.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return {"written": True, "latest_path": str(latest_path), "events_jsonl": str(events_jsonl)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan FlowPilot heartbeat/manual-resume lifecycle before pause, restart, or terminal cleanup.")
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--mode", choices=("scan", "pause", "restart", "terminal"), default="scan")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME; defaults to ~/.codex")
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
        print(f"{payload['decision']}: mode={payload['mode']} actions={len(payload.get('required_actions', []))}")
        for action in payload.get("required_actions", []):
            print(f"- {action.get('kind')}: {action.get('target')} -> {action.get('action')}")
    if args.fail_on_actions and not payload.get("ok"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
