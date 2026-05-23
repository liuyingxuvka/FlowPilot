"""Run-scoped Controller break-glass incident helpers.

This helper is intentionally independent from the normal Router repair loop so
Controller can record evidence when that loop is the broken surface.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


INCIDENT_SCHEMA = "flowpilot.controller_break_glass_incident.v1"
PATCH_SCHEMA = "flowpilot.controller_break_glass_patch.v1"
INDEX_SCHEMA = "flowpilot.controller_break_glass_index.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_id(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return cleaned or f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def current_run_root(project_root: Path, explicit: str | None = None) -> Path:
    if explicit:
        run_root = Path(explicit)
        return run_root if run_root.is_absolute() else project_root / run_root
    current = read_json(project_root / ".flowpilot" / "current.json")
    current_root = current.get("current_run_root")
    if not current_root:
        raise SystemExit("No current run root found; pass --run-root explicitly.")
    run_root = Path(str(current_root))
    return run_root if run_root.is_absolute() else project_root / run_root


def break_glass_root(run_root: Path) -> Path:
    return run_root / "controller_break_glass"


def index_path(run_root: Path) -> Path:
    return break_glass_root(run_root) / "index.json"


def load_index(run_root: Path) -> dict[str, Any]:
    index = read_json(index_path(run_root))
    if index.get("schema_version") != INDEX_SCHEMA:
        index = {
            "schema_version": INDEX_SCHEMA,
            "run_id": run_root.name,
            "incidents": [],
            "patches": [],
            "updated_at": utc_now(),
        }
    return index


def save_index(run_root: Path, index: dict[str, Any]) -> None:
    index["updated_at"] = utc_now()
    write_json(index_path(run_root), index)


def open_incident(
    project_root: Path,
    run_root: Path,
    *,
    incident_id: str,
    trigger_summary: str,
    failure_kind: str,
    sources: list[str],
    normal_lanes: list[str],
) -> dict[str, Any]:
    incident_id = safe_id(incident_id, "incident")
    source_records = []
    for source in sources:
        path = Path(source)
        absolute = path if path.is_absolute() else project_root / path
        source_records.append(
            {
                "path": source,
                "hash": sha256_path(absolute),
                "controller_visible": True,
                "sealed_body_content_read": False,
                "summary": "Controller-visible control-plane source inspected.",
            }
        )
    incident = {
        "schema_version": INCIDENT_SCHEMA,
        "run_id": run_root.name,
        "incident_id": incident_id,
        "opened_at": utc_now(),
        "opened_by_role": "controller",
        "status": "open",
        "trigger_summary": trigger_summary,
        "control_plane_failure_kind": failure_kind,
        "normal_lanes_checked": [
            {
                "lane": lane,
                "source_path": "",
                "result": "unavailable",
                "reason": "Normal lane did not provide a legal next control-plane action.",
            }
            for lane in normal_lanes
        ],
        "sources_inspected": source_records,
        "suspected_flowpilot_defect": {
            "summary": trigger_summary,
            "candidate_root_files": [],
            "not_target_project_defect": True,
        },
        "allowed_reads": sources,
        "allowed_writes": [str(break_glass_root(run_root).relative_to(project_root))] if break_glass_root(run_root).is_relative_to(project_root) else [str(break_glass_root(run_root))],
        "forbidden_actions_acknowledged": {
            "sealed_body_access": True,
            "target_project_work": True,
            "gate_approval": True,
            "route_mutation": True,
            "acceptance_change": True,
            "publication_or_deployment": True,
            "secret_handling": True,
        },
        "validation_plan": [],
        "exit_criteria": [
            "normal FlowPilot control flow can produce a legal next action",
            "break-glass incident and any temporary patch records are written",
            "Controller returns to Router daemon status and action ledger processing",
        ],
        "related_patch_ids": [],
        "closed_at": None,
        "final_disposition": None,
    }
    incident_path = break_glass_root(run_root) / "incidents" / f"{incident_id}.json"
    write_json(incident_path, incident)
    index = load_index(run_root)
    index["incidents"] = [item for item in index.get("incidents", []) if item.get("incident_id") != incident_id]
    index["incidents"].append({"incident_id": incident_id, "path": str(incident_path.relative_to(project_root)), "status": "open"})
    save_index(run_root, index)
    return {"ok": True, "incident": incident, "incident_path": str(incident_path)}


def record_patch(
    project_root: Path,
    run_root: Path,
    *,
    incident_id: str,
    patch_id: str,
    reason: str,
    touched_paths: list[str],
    validation: list[str],
) -> dict[str, Any]:
    incident_id = safe_id(incident_id, "incident")
    patch_id = safe_id(patch_id, "patch")
    touched = []
    for item in touched_paths:
        path = Path(item)
        absolute = path if path.is_absolute() else project_root / path
        touched.append(
            {
                "path": item,
                "change_kind": "modified" if absolute.exists() else "none",
                "before_hash": None,
                "after_hash": sha256_path(absolute),
            }
        )
    patch = {
        "schema_version": PATCH_SCHEMA,
        "run_id": run_root.name,
        "incident_id": incident_id,
        "patch_id": patch_id,
        "recorded_at": utc_now(),
        "recorded_by_role": "controller",
        "patch_kind": "temporary_source_patch" if touched else "diagnostic_only",
        "temporary": True,
        "reason": reason,
        "expected_effect": "Restore a legal FlowPilot control-plane next action.",
        "touched_paths": touched,
        "forbidden_actions_preserved": {
            "sealed_body_access": True,
            "target_project_work": True,
            "gate_approval": True,
            "route_mutation": True,
            "acceptance_change": True,
        },
        "validation_evidence": [
            {"kind": "command", "path": None, "command": command, "result": "not_run", "summary": "Planned validation command."}
            for command in validation
        ],
        "rollback": {
            "required": True,
            "notes": "Use git diff for source patches or supersede with a permanent FlowPilot root fix.",
            "revert_command": None,
            "reverse_patch_path": None,
        },
        "final_disposition": None,
        "permanent_fix_needed": True,
        "flowpilot_skill_improvement_observation_id": None,
    }
    patch_path = break_glass_root(run_root) / "patches" / f"{patch_id}.json"
    write_json(patch_path, patch)
    incident_path = break_glass_root(run_root) / "incidents" / f"{incident_id}.json"
    incident = read_json(incident_path)
    if incident.get("schema_version") == INCIDENT_SCHEMA:
        related = list(incident.get("related_patch_ids") or [])
        if patch_id not in related:
            related.append(patch_id)
        incident["related_patch_ids"] = related
        write_json(incident_path, incident)
    index = load_index(run_root)
    index["patches"] = [item for item in index.get("patches", []) if item.get("patch_id") != patch_id]
    index["patches"].append({"patch_id": patch_id, "incident_id": incident_id, "path": str(patch_path.relative_to(project_root))})
    save_index(run_root, index)
    return {"ok": True, "patch": patch, "patch_path": str(patch_path)}


def finalize_patch(project_root: Path, run_root: Path, *, patch_id: str, disposition: str) -> dict[str, Any]:
    patch_id = safe_id(patch_id, "patch")
    patch_path = break_glass_root(run_root) / "patches" / f"{patch_id}.json"
    patch = read_json(patch_path)
    if patch.get("schema_version") != PATCH_SCHEMA:
        raise SystemExit(f"Patch not found: {patch_id}")
    finalized_at = utc_now()
    patch["final_disposition"] = disposition
    patch["finalized_at"] = finalized_at
    patch["temporary"] = disposition not in {
        "permanent_fix_applied",
        "superseded_by_permanent_fix",
        "rolled_back",
        "diagnostic_only_no_patch",
    }
    patch["permanent_fix_needed"] = disposition not in {
        "permanent_fix_applied",
        "superseded_by_permanent_fix",
        "rolled_back",
        "diagnostic_only_no_patch",
    }
    write_json(patch_path, patch)
    index = load_index(run_root)
    for item in index.get("patches", []):
        if item.get("patch_id") == patch_id:
            item["final_disposition"] = disposition
            item["finalized_at"] = finalized_at
    save_index(run_root, index)
    return {"ok": True, "patch": patch, "patch_path": str(patch_path.relative_to(project_root))}


def close_incident(project_root: Path, run_root: Path, *, incident_id: str, disposition: str) -> dict[str, Any]:
    incident_id = safe_id(incident_id, "incident")
    incident_path = break_glass_root(run_root) / "incidents" / f"{incident_id}.json"
    incident = read_json(incident_path)
    if incident.get("schema_version") != INCIDENT_SCHEMA:
        raise SystemExit(f"Incident not found: {incident_id}")
    finalized_patches: list[dict[str, Any]] = []
    patch_errors: list[dict[str, str]] = []
    for patch_id in incident.get("related_patch_ids") or []:
        patch_path = break_glass_root(run_root) / "patches" / f"{safe_id(str(patch_id), 'patch')}.json"
        patch = read_json(patch_path)
        if patch.get("schema_version") != PATCH_SCHEMA:
            patch_errors.append({"patch_id": str(patch_id), "error": "missing_patch_record"})
            continue
        if patch.get("final_disposition"):
            finalized_patches.append({"patch_id": str(patch_id), "final_disposition": patch.get("final_disposition"), "already_finalized": True})
            continue
        finalized = finalize_patch(project_root, run_root, patch_id=str(patch_id), disposition=disposition)
        finalized_patches.append({"patch_id": str(patch_id), "final_disposition": finalized["patch"].get("final_disposition"), "already_finalized": False})
    incident["status"] = "closed"
    incident["closed_at"] = utc_now()
    incident["final_disposition"] = disposition
    incident["patch_finalization"] = {
        "finalized_patch_count": len(finalized_patches),
        "finalized_patches": finalized_patches,
        "errors": patch_errors,
    }
    write_json(incident_path, incident)
    index = load_index(run_root)
    for item in index.get("incidents", []):
        if item.get("incident_id") == incident_id:
            item["status"] = "closed"
    save_index(run_root, index)
    return {"ok": True, "incident": incident, "incident_path": str(incident_path.relative_to(project_root))}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="Project root")
    parser.add_argument("--run-root", default=None, help="Run root, defaults to .flowpilot/current.json")
    sub = parser.add_subparsers(dest="command", required=True)

    open_cmd = sub.add_parser("open-incident")
    open_cmd.add_argument("--incident-id", required=True)
    open_cmd.add_argument("--trigger-summary", required=True)
    open_cmd.add_argument("--failure-kind", required=True)
    open_cmd.add_argument("--source", action="append", default=[])
    open_cmd.add_argument("--normal-lane", action="append", default=[])

    patch_cmd = sub.add_parser("record-patch")
    patch_cmd.add_argument("--incident-id", required=True)
    patch_cmd.add_argument("--patch-id", required=True)
    patch_cmd.add_argument("--reason", required=True)
    patch_cmd.add_argument("--touched-path", action="append", default=[])
    patch_cmd.add_argument("--validation", action="append", default=[])

    finalize_patch_cmd = sub.add_parser("finalize-patch")
    finalize_patch_cmd.add_argument("--patch-id", required=True)
    finalize_patch_cmd.add_argument("--disposition", required=True)

    close_cmd = sub.add_parser("close-incident")
    close_cmd.add_argument("--incident-id", required=True)
    close_cmd.add_argument("--disposition", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    project_root = Path(args.root).resolve()
    run_root = current_run_root(project_root, args.run_root).resolve()
    if args.command == "open-incident":
        result = open_incident(
            project_root,
            run_root,
            incident_id=args.incident_id,
            trigger_summary=args.trigger_summary,
            failure_kind=args.failure_kind,
            sources=args.source,
            normal_lanes=args.normal_lane,
        )
    elif args.command == "record-patch":
        result = record_patch(
            project_root,
            run_root,
            incident_id=args.incident_id,
            patch_id=args.patch_id,
            reason=args.reason,
            touched_paths=args.touched_path,
            validation=args.validation,
        )
    elif args.command == "finalize-patch":
        result = finalize_patch(project_root, run_root, patch_id=args.patch_id, disposition=args.disposition)
    elif args.command == "close-incident":
        result = close_incident(project_root, run_root, incident_id=args.incident_id, disposition=args.disposition)
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
