"""Run-scoped Controller break-glass incident helpers.

This helper is intentionally independent from the normal Router repair loop so
Controller can record evidence when that loop is the broken surface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowpilot_controller_break_glass_core import *
from flowpilot_controller_break_glass_core import (
    _incident_closure_review,
    _patch_validation_status,
    _source_records,
    _validate_patch_finalization,
)


def record_control_plane_blocker(
    project_root: Path,
    run_root: Path,
    *,
    blocker_id: str,
    family_id: str,
    status: str,
    summary: str,
    sources: list[str],
    recovery_transaction_id: str | None = None,
    current: bool = True,
    requires_body_access: bool = False,
    classification: str = "current_repair",
) -> dict[str, Any]:
    allowed_statuses = {"open", "closed", "regression", "quarantined", "weak_evidence"}
    if status not in allowed_statuses:
        raise SystemExit(f"Invalid blocker status {status!r}; expected one of {sorted(allowed_statuses)}")
    blocker_id = safe_id(blocker_id, "blocker")
    family_id = safe_id(family_id, "family")
    ledger = load_control_plane_blocker_ledger(run_root)
    record = {
        "blocker_id": blocker_id,
        "family_id": family_id,
        "status": status,
        "classification": classification,
        "current": bool(current),
        "requires_body_access": bool(requires_body_access),
        "summary": summary,
        "sources": _source_records(project_root, sources),
        "recovery_transaction_id": safe_id(recovery_transaction_id, "recovery") if recovery_transaction_id else None,
        "recorded_at": utc_now(),
    }
    ledger["blockers"] = [item for item in ledger.get("blockers", []) if item.get("blocker_id") != blocker_id]
    ledger["blockers"].append(record)
    save_control_plane_blocker_ledger(run_root, ledger)
    return {
        "ok": True,
        "blocker": record,
        "ledger_path": project_relative(project_root, control_plane_blocker_ledger_path(run_root)),
    }


def _load_recovery_transaction(run_root: Path, transaction_id: str) -> dict[str, Any]:
    path = recovery_transaction_path(run_root, transaction_id)
    transaction = read_json(path)
    if transaction.get("schema_version") != RECOVERY_TRANSACTION_SCHEMA:
        raise SystemExit(f"Recovery transaction not found: {safe_id(transaction_id, 'recovery')}")
    return transaction


def _save_recovery_transaction(project_root: Path, run_root: Path, transaction: dict[str, Any]) -> dict[str, Any]:
    transaction["updated_at"] = utc_now()
    path = recovery_transaction_path(run_root, str(transaction["transaction_id"]))
    write_json(path, transaction)
    return {"path": project_relative(project_root, path), "hash": sha256_path(path)}


from flowpilot_controller_break_glass_recovery import (
    close_recovery_transaction,
    open_recovery_transaction,
    record_controller_reinjection,
    request_body_access,
)


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
        "related_recovery_transaction_ids": [],
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
        "validation_status": "pending" if validation else "not_required",
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


def record_patch_validation(
    project_root: Path,
    run_root: Path,
    *,
    patch_id: str,
    command: str,
    result: str,
    summary: str,
    evidence_path: str | None = None,
) -> dict[str, Any]:
    patch_id = safe_id(patch_id, "patch")
    patch_path = break_glass_root(run_root) / "patches" / f"{patch_id}.json"
    patch = read_json(patch_path)
    if patch.get("schema_version") != PATCH_SCHEMA:
        raise SystemExit(f"Patch not found: {patch_id}")
    evidence = patch.get("validation_evidence")
    if not isinstance(evidence, list):
        evidence = []
    updated = False
    for item in evidence:
        if not isinstance(item, dict):
            continue
        if str(item.get("command") or "") == command:
            item["result"] = result
            item["summary"] = summary
            item["path"] = evidence_path
            item["recorded_at"] = utc_now()
            updated = True
            break
    if not updated:
        evidence.append(
            {
                "kind": "command",
                "path": evidence_path,
                "command": command,
                "result": result,
                "summary": summary,
                "recorded_at": utc_now(),
            }
        )
    patch["validation_evidence"] = evidence
    patch["validation_status"] = _patch_validation_status(patch)
    write_json(patch_path, patch)
    index = load_index(run_root)
    for item in index.get("patches", []):
        if item.get("patch_id") == patch_id:
            item["validation_status"] = patch["validation_status"]
    save_index(run_root, index)
    return {"ok": True, "patch": patch, "patch_path": str(patch_path.relative_to(project_root))}


def finalize_patch(project_root: Path, run_root: Path, *, patch_id: str, disposition: str) -> dict[str, Any]:
    patch_id = safe_id(patch_id, "patch")
    patch_path = break_glass_root(run_root) / "patches" / f"{patch_id}.json"
    patch = read_json(patch_path)
    if patch.get("schema_version") != PATCH_SCHEMA:
        raise SystemExit(f"Patch not found: {patch_id}")
    _validate_patch_finalization(patch, disposition=disposition)
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
    patch["validation_status"] = _patch_validation_status(patch)
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
    closure_review = _incident_closure_review(run_root, incident, disposition=disposition)
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
    if disposition in INCIDENT_BLOCKED_DISPOSITIONS:
        incident["status"] = "blocked"
    elif disposition in INCIDENT_QUARANTINE_DISPOSITIONS:
        incident["status"] = "quarantined"
    incident["closed_at"] = utc_now()
    incident["final_disposition"] = disposition
    incident["closure_review"] = closure_review
    incident["patch_finalization"] = {
        "finalized_patch_count": len(finalized_patches),
        "finalized_patches": finalized_patches,
        "errors": patch_errors,
    }
    write_json(incident_path, incident)
    index = load_index(run_root)
    for item in index.get("incidents", []):
        if item.get("incident_id") == incident_id:
            item["status"] = incident["status"]
            item["final_disposition"] = disposition
            item["closure_path"] = closure_review.get("closure_path")
    save_index(run_root, index)
    return {"ok": True, "incident": incident, "incident_path": str(incident_path.relative_to(project_root))}


from flowpilot_controller_break_glass_cli import build_parser, main


if __name__ == "__main__":
    raise SystemExit(main())
