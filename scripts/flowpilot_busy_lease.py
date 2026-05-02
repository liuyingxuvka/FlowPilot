"""Create, inspect, and clear FlowPilot busy leases.

A busy lease tells the external watchdog that Codex is actively executing a
bounded long operation. While a matching non-expired lease is active, stale
heartbeat evidence is not treated as a wakeup failure because thread heartbeats
cannot interrupt an already-running turn.
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_state(root: Path) -> dict[str, Any]:
    return read_json(root / ".flowpilot" / "state.json")


def lease_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def start(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    path = lease_path(root, args.path)
    state = load_state(root)
    now = utc_now()
    max_minutes = args.max_minutes
    payload = {
        "schema_version": "flowpilot-busy-lease/v1",
        "lease_id": args.lease_id or f"lease-{uuid.uuid4().hex[:12]}",
        "status": "active",
        "operation": args.operation,
        "route_id": args.route or state.get("active_route"),
        "node_id": args.node or state.get("active_node"),
        "started_at": isoformat_z(now),
        "expires_at": isoformat_z(now + timedelta(minutes=max_minutes)),
        "max_minutes": max_minutes,
        "owner": args.owner,
        "reason": args.reason,
    }
    write_json(path, payload)
    return {"ok": True, "action": "start", "path": str(path), "lease": payload}


def clear(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    path = lease_path(root, args.path)
    payload = read_json(path)
    now = utc_now()
    if not payload:
        payload = {
            "schema_version": "flowpilot-busy-lease/v1",
            "lease_id": args.lease_id or "",
        }
    payload.update(
        {
            "status": "cleared",
            "cleared_at": isoformat_z(now),
            "clear_reason": args.reason,
        }
    )
    write_json(path, payload)
    return {"ok": True, "action": "clear", "path": str(path), "lease": payload}


def status(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root).resolve()
    path = lease_path(root, args.path)
    payload = read_json(path)
    return {"ok": bool(payload), "action": "status", "path": str(path), "lease": payload}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage FlowPilot busy lease evidence.")
    parser.add_argument("command", choices=("start", "clear", "status"))
    parser.add_argument("--root", default=".", help="Project root containing .flowpilot")
    parser.add_argument("--path", default=".flowpilot/busy_lease.json", help="Lease path relative to root")
    parser.add_argument("--lease-id", default="", help="Optional stable lease id")
    parser.add_argument("--operation", default="bounded FlowPilot work chunk", help="Current long operation")
    parser.add_argument("--route", default="", help="Route id; defaults to .flowpilot/state.json active_route")
    parser.add_argument("--node", default="", help="Node id; defaults to .flowpilot/state.json active_node")
    parser.add_argument("--max-minutes", type=float, default=30.0, help="Lease expiry window")
    parser.add_argument("--owner", default="flowpilot-controller")
    parser.add_argument("--reason", default="")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "start":
        payload = start(args)
    elif args.command == "clear":
        payload = clear(args)
    else:
        payload = status(args)

    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{payload['action']}: {payload['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
