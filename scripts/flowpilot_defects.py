"""Manage FlowPilot run-level defect, evidence, and pause ledgers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_paths import resolve_flowpilot_paths


DEFECT_TYPES = {
    "target_product_defect",
    "flowpilot_skill_defect",
    "process_defect",
    "evidence_defect",
    "tool_environment_defect",
}
DEFECT_STATUSES = {
    "open",
    "accepted",
    "fixing",
    "fixed_pending_recheck",
    "closed",
    "deferred",
}
DEFECT_SEVERITIES = {"blocker", "high", "medium", "low"}
EVIDENCE_STATUSES = {"valid", "invalid", "stale", "superseded"}
EVIDENCE_SOURCE_KINDS = {
    "live_project",
    "fixture",
    "synthetic",
    "historical",
    "generated_concept",
}


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:40] or "item"


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp_path.replace(path)


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def split_csv(value: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def context(root: Path) -> dict[str, Any]:
    paths = resolve_flowpilot_paths(root)
    state = read_json_if_exists(Path(paths["state_path"]))
    frontier = read_json_if_exists(Path(paths["frontier_path"]))
    run_root = Path(paths["run_root"])
    run_id = paths.get("run_id") or state.get("run_id") or run_root.name
    route_id = (
        frontier.get("active_route")
        or state.get("active_route")
        or state.get("route_id")
        or None
    )
    route_version = frontier.get("route_version") or state.get("route_version") or 0
    return {
        "paths": paths,
        "state": state,
        "frontier": frontier,
        "run_root": run_root,
        "run_id": run_id,
        "route_id": route_id,
        "route_version": route_version,
        "defect_ledger_path": run_root / "defects" / "defect_ledger.json",
        "defect_events_path": run_root / "defects" / "defect_events.jsonl",
        "evidence_ledger_path": run_root / "evidence" / "evidence_ledger.json",
        "evidence_events_path": run_root / "evidence" / "evidence_events.jsonl",
        "pause_snapshot_path": run_root / "pause_snapshot.json",
    }


def defect_counts(defects: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(defects),
        "open": 0,
        "blocker_open": 0,
        "fixed_pending_recheck": 0,
        "closed": 0,
        "deferred": 0,
    }
    for defect in defects:
        status = defect.get("status")
        if status == "open":
            counts["open"] += 1
        if status == "open" and defect.get("severity") == "blocker":
            counts["blocker_open"] += 1
        if status == "fixed_pending_recheck":
            counts["fixed_pending_recheck"] += 1
        if status == "closed":
            counts["closed"] += 1
        if status == "deferred":
            counts["deferred"] += 1
    return counts


def evidence_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(items),
        "valid": 0,
        "invalid": 0,
        "stale": 0,
        "superseded": 0,
        "fixture_only": 0,
        "live_project": 0,
    }
    for item in items:
        status = item.get("status")
        source_kind = item.get("source_kind")
        if status in counts:
            counts[status] += 1
        if source_kind == "fixture":
            counts["fixture_only"] += 1
        if source_kind == "live_project":
            counts["live_project"] += 1
    return counts


def default_defect_ledger(ctx: dict[str, Any]) -> dict[str, Any]:
    run_id = ctx["run_id"]
    return {
        "schema_version": "flowpilot.defect_ledger.v1",
        "run_id": run_id,
        "route_id": ctx["route_id"],
        "route_version": ctx["route_version"],
        "pm_owned": True,
        "status": "active",
        "purpose": "Canonical run-level ledger for product, skill, process, evidence, and tool defects discovered during the run.",
        "event_log_path": f".flowpilot/runs/{run_id}/defects/defect_events.jsonl",
        "write_policy": {
            "who_registers": "Any discovering role writes an event immediately.",
            "who_triages": "The project manager classifies severity, owner, blocker status, and route impact.",
            "who_repairs": "The assigned owner repairs or compensates according to PM triage.",
            "who_rechecks": "The same role class that owns the blocked gate rechecks fixed blockers.",
            "who_closes": "The project manager closes only after required recheck evidence is cited.",
        },
        "allowed_defect_types": sorted(DEFECT_TYPES),
        "allowed_statuses": sorted(DEFECT_STATUSES),
        "allowed_severities": sorted(DEFECT_SEVERITIES),
        "counts": defect_counts([]),
        "defects": [],
        "completion_policy": {
            "route_or_node_completion_blocked_when_blocker_open": True,
            "route_or_node_completion_blocked_when_fixed_pending_recheck": True,
            "terminal_completion_requires_blocker_open_zero": True,
            "terminal_completion_requires_fixed_pending_recheck_zero": True,
        },
    }


def default_evidence_ledger(ctx: dict[str, Any]) -> dict[str, Any]:
    run_id = ctx["run_id"]
    return {
        "schema_version": "flowpilot.evidence_ledger.v1",
        "run_id": run_id,
        "route_id": ctx["route_id"],
        "route_version": ctx["route_version"],
        "status": "active",
        "purpose": "Canonical run-level inventory of evidence credibility.",
        "event_log_path": f".flowpilot/runs/{run_id}/evidence/evidence_events.jsonl",
        "allowed_statuses": sorted(EVIDENCE_STATUSES),
        "allowed_source_kinds": sorted(EVIDENCE_SOURCE_KINDS),
        "counts": evidence_counts([]),
        "evidence_items": [],
        "completion_policy": {
            "terminal_ledger_must_account_for_invalid_stale_superseded": True,
            "fixture_only_evidence_must_be_disclosed_separately_from_live_project_evidence": True,
            "invalid_evidence_cannot_close_current_gate": True,
        },
    }


def load_or_create_defect_ledger(ctx: dict[str, Any]) -> dict[str, Any]:
    ledger = read_json_if_exists(ctx["defect_ledger_path"])
    if not ledger:
        ledger = default_defect_ledger(ctx)
    ledger["counts"] = defect_counts(ledger.get("defects", []))
    return ledger


def load_or_create_evidence_ledger(ctx: dict[str, Any]) -> dict[str, Any]:
    ledger = read_json_if_exists(ctx["evidence_ledger_path"])
    if not ledger:
        ledger = default_evidence_ledger(ctx)
    ledger["counts"] = evidence_counts(ledger.get("evidence_items", []))
    return ledger


def init_ledgers(root: Path) -> dict[str, Any]:
    ctx = context(root)
    defect_ledger = load_or_create_defect_ledger(ctx)
    evidence_ledger = load_or_create_evidence_ledger(ctx)
    write_json_atomic(ctx["defect_ledger_path"], defect_ledger)
    write_json_atomic(ctx["evidence_ledger_path"], evidence_ledger)
    return {
        "ok": True,
        "defect_ledger_path": str(ctx["defect_ledger_path"]),
        "evidence_ledger_path": str(ctx["evidence_ledger_path"]),
    }


def add_defect(args: argparse.Namespace) -> dict[str, Any]:
    if args.defect_type not in DEFECT_TYPES:
        raise ValueError(f"unknown defect type: {args.defect_type}")
    if args.severity not in DEFECT_SEVERITIES:
        raise ValueError(f"unknown severity: {args.severity}")

    ctx = context(Path(args.root))
    ledger = load_or_create_defect_ledger(ctx)
    now = utc_now()
    defect_id = args.defect_id or f"defect-{now.replace(':', '').replace('-', '')}-{slugify(args.title)}"
    defect = {
        "defect_id": defect_id,
        "title": args.title,
        "defect_type": args.defect_type,
        "severity": args.severity,
        "status": "open",
        "found_by_role": args.role,
        "found_at": now,
        "affected_gate": args.affected_gate or None,
        "affected_requirement": args.affected_requirement or None,
        "description": args.description,
        "pm_triage": {
            "triaged": False,
            "triaged_by_role": "project_manager",
            "triaged_at": None,
            "route_impact": None,
            "owner_role": args.owner_role or None,
            "recheck_role_class": args.recheck_role_class or None,
            "close_condition": args.close_condition or None,
        },
        "evidence_paths": split_csv(args.evidence),
        "repair_paths": [],
        "recheck_paths": [],
        "history": [],
    }
    event = {
        "schema_version": "flowpilot.defect_event.v1",
        "event_id": f"event-{now.replace(':', '').replace('-', '')}-{slugify(defect_id)}",
        "run_id": ctx["run_id"],
        "defect_id": defect_id,
        "recorded_at": now,
        "recorded_by_role": args.role,
        "event_type": "created",
        "from_status": None,
        "to_status": "open",
        "summary": args.title,
        "evidence_paths": split_csv(args.evidence),
        "notes": args.description,
    }
    defect["history"].append(event)
    ledger.setdefault("defects", []).append(defect)
    ledger["counts"] = defect_counts(ledger["defects"])
    write_json_atomic(ctx["defect_ledger_path"], ledger)
    append_jsonl(ctx["defect_events_path"], event)
    return {"ok": True, "defect_id": defect_id, "ledger_path": str(ctx["defect_ledger_path"])}


def update_defect(args: argparse.Namespace) -> dict[str, Any]:
    if args.status not in DEFECT_STATUSES:
        raise ValueError(f"unknown status: {args.status}")

    ctx = context(Path(args.root))
    ledger = load_or_create_defect_ledger(ctx)
    defects = ledger.get("defects", [])
    defect = next((item for item in defects if item.get("defect_id") == args.defect_id), None)
    if defect is None:
        raise KeyError(f"defect not found: {args.defect_id}")

    now = utc_now()
    old_status = defect.get("status")
    defect["status"] = args.status
    if args.owner_role or args.route_impact or args.recheck_role_class or args.close_condition:
        triage = defect.setdefault("pm_triage", {})
        triage["triaged"] = True
        triage["triaged_by_role"] = "project_manager"
        triage["triaged_at"] = now
        if args.route_impact:
            triage["route_impact"] = args.route_impact
        if args.owner_role:
            triage["owner_role"] = args.owner_role
        if args.recheck_role_class:
            triage["recheck_role_class"] = args.recheck_role_class
        if args.close_condition:
            triage["close_condition"] = args.close_condition
    if args.evidence:
        paths = split_csv(args.evidence)
        if args.status == "fixed_pending_recheck":
            defect.setdefault("repair_paths", []).extend(paths)
        elif args.status == "closed":
            defect.setdefault("recheck_paths", []).extend(paths)
        else:
            defect.setdefault("evidence_paths", []).extend(paths)

    event = {
        "schema_version": "flowpilot.defect_event.v1",
        "event_id": f"event-{now.replace(':', '').replace('-', '')}-{slugify(args.defect_id)}",
        "run_id": ctx["run_id"],
        "defect_id": args.defect_id,
        "recorded_at": now,
        "recorded_by_role": args.role,
        "event_type": args.event_type,
        "from_status": old_status,
        "to_status": args.status,
        "summary": args.summary,
        "evidence_paths": split_csv(args.evidence),
        "notes": args.notes or None,
    }
    defect.setdefault("history", []).append(event)
    ledger["counts"] = defect_counts(defects)
    write_json_atomic(ctx["defect_ledger_path"], ledger)
    append_jsonl(ctx["defect_events_path"], event)
    return {"ok": True, "defect_id": args.defect_id, "ledger_path": str(ctx["defect_ledger_path"])}


def add_evidence(args: argparse.Namespace) -> dict[str, Any]:
    if args.status not in EVIDENCE_STATUSES:
        raise ValueError(f"unknown evidence status: {args.status}")
    if args.source_kind not in EVIDENCE_SOURCE_KINDS:
        raise ValueError(f"unknown source kind: {args.source_kind}")

    ctx = context(Path(args.root))
    ledger = load_or_create_evidence_ledger(ctx)
    now = utc_now()
    evidence_id = args.evidence_id or f"evidence-{now.replace(':', '').replace('-', '')}-{slugify(args.kind)}"
    item = {
        "evidence_id": evidence_id,
        "kind": args.kind,
        "path": args.path,
        "status": args.status,
        "source_kind": args.source_kind,
        "produced_at": now,
        "created_by_role": args.role,
        "closes_gate": args.closes_gate or None,
        "validity_reason": args.reason,
        "superseded_by": args.superseded_by or None,
        "defect_ids": split_csv(args.defect_ids),
    }
    event = {
        "schema_version": "flowpilot.evidence_event.v1",
        "event_id": f"event-{now.replace(':', '').replace('-', '')}-{slugify(evidence_id)}",
        "run_id": ctx["run_id"],
        "evidence_id": evidence_id,
        "recorded_at": now,
        "recorded_by_role": args.role,
        "event_type": "registered",
        "from_status": None,
        "to_status": args.status,
        "summary": args.reason,
        "paths": [args.path],
        "notes": None,
    }
    ledger.setdefault("evidence_items", []).append(item)
    ledger["counts"] = evidence_counts(ledger["evidence_items"])
    write_json_atomic(ctx["evidence_ledger_path"], ledger)
    append_jsonl(ctx["evidence_events_path"], event)
    return {
        "ok": True,
        "evidence_id": evidence_id,
        "ledger_path": str(ctx["evidence_ledger_path"]),
    }


def build_pause_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    ctx = context(Path(args.root))
    defect_ledger = load_or_create_defect_ledger(ctx)
    evidence_ledger = load_or_create_evidence_ledger(ctx)
    open_blockers = [
        item
        for item in defect_ledger.get("defects", [])
        if item.get("severity") == "blocker" and item.get("status") == "open"
    ]
    pending_recheck = [
        item
        for item in defect_ledger.get("defects", [])
        if item.get("status") == "fixed_pending_recheck"
    ]
    invalid_or_stale = [
        item
        for item in evidence_ledger.get("evidence_items", [])
        if item.get("status") in {"invalid", "stale"}
    ]
    fixture_only = [
        item
        for item in evidence_ledger.get("evidence_items", [])
        if item.get("source_kind") == "fixture"
    ]
    snapshot = {
        "schema_version": "flowpilot.pause_snapshot.v1",
        "run_id": ctx["run_id"],
        "written_at": utc_now(),
        "pause_reason": args.reason,
        "current_route": ctx["route_id"],
        "route_version": ctx["route_version"],
        "active_node": ctx["frontier"].get("active_node") or ctx["state"].get("active_node"),
        "current_gate": ctx["frontier"].get("next_gate") or ctx["frontier"].get("current_gate"),
        "next_allowed_action": args.next_allowed_action,
        "defect_summary": {
            "defect_ledger_path": str(ctx["defect_ledger_path"]),
            "open_blockers": [item.get("defect_id") for item in open_blockers],
            "fixed_pending_recheck": [item.get("defect_id") for item in pending_recheck],
            "deferred_items": [
                item.get("defect_id")
                for item in defect_ledger.get("defects", [])
                if item.get("status") == "deferred"
            ],
        },
        "evidence_summary": {
            "evidence_ledger_path": str(ctx["evidence_ledger_path"]),
            "invalid_or_stale_evidence": [item.get("evidence_id") for item in invalid_or_stale],
            "fixture_only_evidence_to_disclose": [item.get("evidence_id") for item in fixture_only],
        },
        "lifecycle_summary": {
            "heartbeat_automation_ids": split_csv(args.heartbeat_ids),
            "codex_automation_status_checked": args.automation_checked,
            "active_background_agents": split_csv(args.active_agents),
            "closed_or_paused_background_agents": split_csv(args.closed_agents),
            "manual_resume_notice_required": args.manual_resume_notice_required,
        },
        "cleanup_boundary": {
            "temporary_artifacts_safe_to_delete": split_csv(args.safe_to_delete),
            "evidence_or_lessons_to_preserve": split_csv(args.preserve),
            "must_not_reuse_in_next_fresh_run": split_csv(args.must_not_reuse),
        },
        "human_readable_summary": args.summary,
    }
    write_json_atomic(ctx["pause_snapshot_path"], snapshot)
    return {"ok": True, "pause_snapshot_path": str(ctx["pause_snapshot_path"])}


def check_ledgers(args: argparse.Namespace) -> dict[str, Any]:
    ctx = context(Path(args.root))
    defect_ledger = load_or_create_defect_ledger(ctx)
    evidence_ledger = load_or_create_evidence_ledger(ctx)
    defect_counts_payload = defect_counts(defect_ledger.get("defects", []))
    evidence_counts_payload = evidence_counts(evidence_ledger.get("evidence_items", []))
    blockers = []
    if defect_counts_payload["blocker_open"]:
        blockers.append("open blocker defects remain")
    if defect_counts_payload["fixed_pending_recheck"]:
        blockers.append("fixed defects are still pending recheck")
    ok = not blockers
    if not args.terminal:
        ok = True
    return {
        "ok": ok,
        "terminal_mode": args.terminal,
        "blockers": blockers,
        "defect_counts": defect_counts_payload,
        "evidence_counts": evidence_counts_payload,
        "defect_ledger_path": str(ctx["defect_ledger_path"]),
        "evidence_ledger_path": str(ctx["evidence_ledger_path"]),
    }


def print_result(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Create defect and evidence ledgers if missing.")

    add = subparsers.add_parser("add-defect", help="Register a new defect.")
    add.add_argument("--defect-id", default="")
    add.add_argument("--title", required=True)
    add.add_argument("--description", required=True)
    add.add_argument("--defect-type", required=True, choices=sorted(DEFECT_TYPES))
    add.add_argument("--severity", required=True, choices=sorted(DEFECT_SEVERITIES))
    add.add_argument("--role", required=True)
    add.add_argument("--affected-gate", default="")
    add.add_argument("--affected-requirement", default="")
    add.add_argument("--owner-role", default="")
    add.add_argument("--recheck-role-class", default="")
    add.add_argument("--close-condition", default="")
    add.add_argument("--evidence", default="", help="Comma-separated evidence paths.")

    update = subparsers.add_parser("update-defect", help="Update status or PM triage.")
    update.add_argument("--defect-id", required=True)
    update.add_argument("--status", required=True, choices=sorted(DEFECT_STATUSES))
    update.add_argument("--role", required=True)
    update.add_argument("--event-type", required=True)
    update.add_argument("--summary", required=True)
    update.add_argument("--notes", default="")
    update.add_argument("--route-impact", default="")
    update.add_argument("--owner-role", default="")
    update.add_argument("--recheck-role-class", default="")
    update.add_argument("--close-condition", default="")
    update.add_argument("--evidence", default="", help="Comma-separated evidence paths.")

    evidence = subparsers.add_parser("add-evidence", help="Register evidence credibility.")
    evidence.add_argument("--evidence-id", default="")
    evidence.add_argument("--kind", required=True)
    evidence.add_argument("--path", required=True)
    evidence.add_argument("--status", required=True, choices=sorted(EVIDENCE_STATUSES))
    evidence.add_argument("--source-kind", required=True, choices=sorted(EVIDENCE_SOURCE_KINDS))
    evidence.add_argument("--role", required=True)
    evidence.add_argument("--closes-gate", default="")
    evidence.add_argument("--reason", required=True)
    evidence.add_argument("--superseded-by", default="")
    evidence.add_argument("--defect-ids", default="")

    pause = subparsers.add_parser("pause-snapshot", help="Write a controlled pause snapshot.")
    pause.add_argument("--reason", default="manual_pause")
    pause.add_argument("--next-allowed-action", default="resume_current_gate")
    pause.add_argument("--heartbeat-ids", default="")
    pause.add_argument("--automation-checked", action="store_true")
    pause.add_argument("--active-agents", default="")
    pause.add_argument("--closed-agents", default="")
    pause.add_argument("--manual-resume-notice-required", action="store_true")
    pause.add_argument("--safe-to-delete", default="")
    pause.add_argument("--preserve", default="")
    pause.add_argument("--must-not-reuse", default="")
    pause.add_argument("--summary", default="")

    check = subparsers.add_parser("check", help="Check ledgers for completion blockers.")
    check.add_argument("--terminal", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return print_result(init_ledgers(Path(args.root)))
        if args.command == "add-defect":
            return print_result(add_defect(args))
        if args.command == "update-defect":
            return print_result(update_defect(args))
        if args.command == "add-evidence":
            return print_result(add_evidence(args))
        if args.command == "pause-snapshot":
            return print_result(build_pause_snapshot(args))
        if args.command == "check":
            return print_result(check_ledgers(args))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": repr(exc)}, indent=2, sort_keys=True))
        return 1
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
