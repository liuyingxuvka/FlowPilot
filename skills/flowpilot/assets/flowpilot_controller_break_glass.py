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
RECOVERY_TRANSACTION_SCHEMA = "flowpilot.recovery_supervisor_transaction.v1"
CONTROL_BLOCKER_LEDGER_SCHEMA = "flowpilot.control_plane_blocker_ledger.v1"
BODY_ACCESS_GRANT_SCHEMA = "flowpilot.recovery_supervisor_body_access_grant.v1"
CONTROLLER_REINJECTION_SCHEMA = "flowpilot.controller_reinjection.v1"


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


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


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


def control_plane_blocker_ledger_path(run_root: Path) -> Path:
    return break_glass_root(run_root) / "control_plane_blocker_ledger.json"


def recovery_transaction_path(run_root: Path, transaction_id: str) -> Path:
    return break_glass_root(run_root) / "recovery_transactions" / f"{safe_id(transaction_id, 'recovery')}.json"


def body_access_grant_path(run_root: Path, grant_id: str) -> Path:
    return break_glass_root(run_root) / "body_access_grants" / f"{safe_id(grant_id, 'grant')}.json"


def controller_reinjection_path(run_root: Path, reinjection_id: str) -> Path:
    return break_glass_root(run_root) / "controller_reinjections" / f"{safe_id(reinjection_id, 'reinject')}.json"


def load_index(run_root: Path) -> dict[str, Any]:
    index = read_json(index_path(run_root))
    if index.get("schema_version") != INDEX_SCHEMA:
        index = {
            "schema_version": INDEX_SCHEMA,
            "run_id": run_root.name,
            "incidents": [],
            "patches": [],
            "recovery_transactions": [],
            "body_access_grants": [],
            "controller_reinjections": [],
            "updated_at": utc_now(),
        }
    return index


def save_index(run_root: Path, index: dict[str, Any]) -> None:
    index["updated_at"] = utc_now()
    write_json(index_path(run_root), index)


def load_control_plane_blocker_ledger(run_root: Path) -> dict[str, Any]:
    ledger = read_json(control_plane_blocker_ledger_path(run_root))
    if ledger.get("schema_version") != CONTROL_BLOCKER_LEDGER_SCHEMA:
        ledger = {
            "schema_version": CONTROL_BLOCKER_LEDGER_SCHEMA,
            "run_id": run_root.name,
            "blockers": [],
            "updated_at": utc_now(),
        }
    return ledger


def save_control_plane_blocker_ledger(run_root: Path, ledger: dict[str, Any]) -> None:
    ledger["updated_at"] = utc_now()
    write_json(control_plane_blocker_ledger_path(run_root), ledger)


def _source_records(project_root: Path, sources: list[str], *, body_read: bool = False) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source in sources:
        path = Path(source)
        absolute = path if path.is_absolute() else project_root / path
        records.append(
            {
                "path": source,
                "hash": sha256_path(absolute),
                "controller_visible": not body_read,
                "sealed_body_content_read": body_read,
                "summary": (
                    "Recovery Supervisor scoped body source."
                    if body_read
                    else "Controller-visible control-plane source inspected."
                ),
            }
        )
    return records


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


def open_recovery_transaction(
    project_root: Path,
    run_root: Path,
    *,
    transaction_id: str,
    incident_id: str,
    trigger_summary: str,
    failure_kind: str,
    blocker_ids: list[str],
    family_ids: list[str],
    normal_lanes: list[str],
    controller_generation_id: str,
    flowguard_obligations: list[str],
) -> dict[str, Any]:
    transaction_id = safe_id(transaction_id, "recovery")
    incident_id = safe_id(incident_id, "incident")
    transaction = {
        "schema_version": RECOVERY_TRANSACTION_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction_id,
        "status": "open",
        "identity_mode": "recovery_supervisor",
        "opened_at": utc_now(),
        "opened_by_role": "recovery_supervisor",
        "normal_controller_suspended": True,
        "controller_generation_before": controller_generation_id,
        "linked_incident_id": incident_id,
        "trigger_summary": trigger_summary,
        "control_plane_failure_kind": failure_kind,
        "blocker_ids": [safe_id(item, "blocker") for item in blocker_ids],
        "defect_family_ids": [safe_id(item, "family") for item in family_ids],
        "normal_lanes_checked": [
            {
                "lane": lane,
                "result": "unavailable_or_contradictory",
                "reason": "Recovery Supervisor opened only after ordinary lane failed to provide a legal next action.",
            }
            for lane in normal_lanes
        ],
        "flowguard_obligations": [
            {
                "kind": "command",
                "command": obligation,
                "result": "not_run",
                "proof_artifact": None,
            }
            for obligation in flowguard_obligations
        ],
        "same_family_repair": {
            "required": True,
            "evidence": [],
            "historical_blockers_reviewed": [],
        },
        "body_access_grants": [],
        "controller_reinjection": None,
        "exit_criteria": [
            "current open blockers repaired, superseded, or quarantined",
            "same-family FlowGuard proof recorded",
            "old Controller generation invalidated",
            "fresh Controller core reinjection recorded",
        ],
        "closed_at": None,
        "final_disposition": None,
    }
    tx_ref = _save_recovery_transaction(project_root, run_root, transaction)
    index = load_index(run_root)
    index["recovery_transactions"] = [
        item for item in index.get("recovery_transactions", []) if item.get("transaction_id") != transaction_id
    ]
    index["recovery_transactions"].append(
        {"transaction_id": transaction_id, "path": tx_ref["path"], "status": "open"}
    )
    save_index(run_root, index)
    return {"ok": True, "transaction": transaction, "transaction_path": tx_ref["path"]}


def request_body_access(
    project_root: Path,
    run_root: Path,
    *,
    transaction_id: str,
    grant_id: str,
    body_path: str,
    reason: str,
    unavailable_role_lanes: list[str],
    post_recovery_reviewer: str = "project_manager",
) -> dict[str, Any]:
    if not reason.strip():
        raise SystemExit("Body access grant requires a non-empty reason.")
    if not unavailable_role_lanes:
        raise SystemExit("Body access grant requires at least one unavailable or contradictory role lane.")
    transaction = _load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Body access grant requires an open recovery transaction.")
    grant_id = safe_id(grant_id, "grant")
    path = Path(body_path)
    absolute = path if path.is_absolute() else project_root / path
    grant = {
        "schema_version": BODY_ACCESS_GRANT_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction["transaction_id"],
        "grant_id": grant_id,
        "granted_at": utc_now(),
        "granted_to_identity": "recovery_supervisor",
        "normal_controller_body_access_granted": False,
        "body_path": body_path,
        "body_hash": sha256_path(absolute),
        "reason_metadata_insufficient": reason,
        "unavailable_or_contradictory_role_lanes": unavailable_role_lanes,
        "allowed_scope": "read_only_diagnosis",
        "forbidden_uses": [
            "normal_controller_context",
            "gate_approval",
            "route_mutation_approval",
            "terminal_completion",
            "target_project_implementation",
        ],
        "post_recovery_review_required": True,
        "post_recovery_reviewer": post_recovery_reviewer,
    }
    grant_path = body_access_grant_path(run_root, grant_id)
    write_json(grant_path, grant)
    grants = [item for item in transaction.get("body_access_grants", []) if item.get("grant_id") != grant_id]
    grants.append({"grant_id": grant_id, "path": project_relative(project_root, grant_path), "body_hash": grant["body_hash"]})
    transaction["body_access_grants"] = grants
    _save_recovery_transaction(project_root, run_root, transaction)
    index = load_index(run_root)
    index["body_access_grants"] = [item for item in index.get("body_access_grants", []) if item.get("grant_id") != grant_id]
    index["body_access_grants"].append(
        {"grant_id": grant_id, "transaction_id": transaction["transaction_id"], "path": project_relative(project_root, grant_path)}
    )
    save_index(run_root, index)
    return {"ok": True, "grant": grant, "grant_path": project_relative(project_root, grant_path)}


def record_controller_reinjection(
    project_root: Path,
    run_root: Path,
    *,
    transaction_id: str,
    reinjection_id: str,
    previous_generation_id: str,
    next_generation_id: str,
    controller_core_path: str,
    boundary_proof_path: str | None,
    proof_artifacts: list[str],
) -> dict[str, Any]:
    if previous_generation_id == next_generation_id:
        raise SystemExit("Controller reinjection requires a new generation id.")
    transaction = _load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Controller reinjection requires an open recovery transaction.")
    reinjection_id = safe_id(reinjection_id, "reinject")
    core = Path(controller_core_path)
    absolute_core = core if core.is_absolute() else project_root / core
    proof_records = _source_records(project_root, proof_artifacts)
    reinjection = {
        "schema_version": CONTROLLER_REINJECTION_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction["transaction_id"],
        "reinjection_id": reinjection_id,
        "recorded_at": utc_now(),
        "previous_controller_generation_id": previous_generation_id,
        "next_controller_generation_id": next_generation_id,
        "old_controller_generation_invalidated": True,
        "controller_core_path": controller_core_path,
        "controller_core_hash": sha256_path(absolute_core),
        "boundary_proof_path": boundary_proof_path,
        "proof_artifacts": proof_records,
        "normal_controller_restrictions_restored": {
            "sealed_body_access": False,
            "gate_approval": False,
            "route_mutation": False,
            "target_project_work": False,
        },
    }
    reinjection_path = controller_reinjection_path(run_root, reinjection_id)
    write_json(reinjection_path, reinjection)
    transaction["controller_reinjection"] = {
        "reinjection_id": reinjection_id,
        "path": project_relative(project_root, reinjection_path),
        "next_controller_generation_id": next_generation_id,
    }
    _save_recovery_transaction(project_root, run_root, transaction)
    index = load_index(run_root)
    index["controller_reinjections"] = [
        item for item in index.get("controller_reinjections", []) if item.get("reinjection_id") != reinjection_id
    ]
    index["controller_reinjections"].append(
        {"reinjection_id": reinjection_id, "transaction_id": transaction["transaction_id"], "path": project_relative(project_root, reinjection_path)}
    )
    save_index(run_root, index)
    return {"ok": True, "reinjection": reinjection, "reinjection_path": project_relative(project_root, reinjection_path)}


def close_recovery_transaction(
    project_root: Path,
    run_root: Path,
    *,
    transaction_id: str,
    disposition: str,
    same_family_evidence: list[str],
) -> dict[str, Any]:
    transaction = _load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Recovery transaction is not open.")
    if not same_family_evidence:
        raise SystemExit("Recovery transaction closure requires same-family FlowGuard evidence.")
    if not transaction.get("controller_reinjection"):
        raise SystemExit("Recovery transaction closure requires Controller reinjection proof.")

    ledger = load_control_plane_blocker_ledger(run_root)
    unresolved = [
        item
        for item in ledger.get("blockers", [])
        if item.get("current")
        and item.get("recovery_transaction_id") == transaction.get("transaction_id")
        and item.get("status") == "open"
    ]
    if unresolved:
        blocker_ids = ", ".join(str(item.get("blocker_id")) for item in unresolved)
        raise SystemExit(f"Recovery transaction has unresolved current blockers: {blocker_ids}")

    evidence_records = _source_records(project_root, same_family_evidence)
    transaction["same_family_repair"]["evidence"] = evidence_records
    transaction["status"] = "closed"
    transaction["closed_at"] = utc_now()
    transaction["final_disposition"] = disposition
    transaction["normal_controller_suspended"] = False
    tx_ref = _save_recovery_transaction(project_root, run_root, transaction)
    index = load_index(run_root)
    for item in index.get("recovery_transactions", []):
        if item.get("transaction_id") == transaction.get("transaction_id"):
            item["status"] = "closed"
            item["final_disposition"] = disposition
    save_index(run_root, index)
    return {"ok": True, "transaction": transaction, "transaction_path": tx_ref["path"]}


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

    blocker_cmd = sub.add_parser("record-control-blocker")
    blocker_cmd.add_argument("--blocker-id", required=True)
    blocker_cmd.add_argument("--family-id", required=True)
    blocker_cmd.add_argument("--status", required=True)
    blocker_cmd.add_argument("--summary", required=True)
    blocker_cmd.add_argument("--source", action="append", default=[])
    blocker_cmd.add_argument("--recovery-transaction-id", default=None)
    blocker_cmd.add_argument("--historical", action="store_true")
    blocker_cmd.add_argument("--requires-body-access", action="store_true")
    blocker_cmd.add_argument("--classification", default="current_repair")

    recovery_cmd = sub.add_parser("open-recovery")
    recovery_cmd.add_argument("--transaction-id", required=True)
    recovery_cmd.add_argument("--incident-id", required=True)
    recovery_cmd.add_argument("--trigger-summary", required=True)
    recovery_cmd.add_argument("--failure-kind", required=True)
    recovery_cmd.add_argument("--blocker-id", action="append", default=[])
    recovery_cmd.add_argument("--family-id", action="append", default=[])
    recovery_cmd.add_argument("--normal-lane", action="append", default=[])
    recovery_cmd.add_argument("--controller-generation-id", required=True)
    recovery_cmd.add_argument("--flowguard-obligation", action="append", default=[])

    body_cmd = sub.add_parser("request-body-access")
    body_cmd.add_argument("--transaction-id", required=True)
    body_cmd.add_argument("--grant-id", required=True)
    body_cmd.add_argument("--body-path", required=True)
    body_cmd.add_argument("--reason", required=True)
    body_cmd.add_argument("--unavailable-role-lane", action="append", default=[])
    body_cmd.add_argument("--post-recovery-reviewer", default="project_manager")

    reinject_cmd = sub.add_parser("record-controller-reinjection")
    reinject_cmd.add_argument("--transaction-id", required=True)
    reinject_cmd.add_argument("--reinjection-id", required=True)
    reinject_cmd.add_argument("--previous-generation-id", required=True)
    reinject_cmd.add_argument("--next-generation-id", required=True)
    reinject_cmd.add_argument("--controller-core-path", required=True)
    reinject_cmd.add_argument("--boundary-proof-path", default=None)
    reinject_cmd.add_argument("--proof-artifact", action="append", default=[])

    close_recovery_cmd = sub.add_parser("close-recovery")
    close_recovery_cmd.add_argument("--transaction-id", required=True)
    close_recovery_cmd.add_argument("--disposition", required=True)
    close_recovery_cmd.add_argument("--same-family-evidence", action="append", default=[])
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
    elif args.command == "record-control-blocker":
        result = record_control_plane_blocker(
            project_root,
            run_root,
            blocker_id=args.blocker_id,
            family_id=args.family_id,
            status=args.status,
            summary=args.summary,
            sources=args.source,
            recovery_transaction_id=args.recovery_transaction_id,
            current=not args.historical,
            requires_body_access=args.requires_body_access,
            classification=args.classification,
        )
    elif args.command == "open-recovery":
        result = open_recovery_transaction(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            incident_id=args.incident_id,
            trigger_summary=args.trigger_summary,
            failure_kind=args.failure_kind,
            blocker_ids=args.blocker_id,
            family_ids=args.family_id,
            normal_lanes=args.normal_lane,
            controller_generation_id=args.controller_generation_id,
            flowguard_obligations=args.flowguard_obligation,
        )
    elif args.command == "request-body-access":
        result = request_body_access(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            grant_id=args.grant_id,
            body_path=args.body_path,
            reason=args.reason,
            unavailable_role_lanes=args.unavailable_role_lane,
            post_recovery_reviewer=args.post_recovery_reviewer,
        )
    elif args.command == "record-controller-reinjection":
        result = record_controller_reinjection(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            reinjection_id=args.reinjection_id,
            previous_generation_id=args.previous_generation_id,
            next_generation_id=args.next_generation_id,
            controller_core_path=args.controller_core_path,
            boundary_proof_path=args.boundary_proof_path,
            proof_artifacts=args.proof_artifact,
        )
    elif args.command == "close-recovery":
        result = close_recovery_transaction(
            project_root,
            run_root,
            transaction_id=args.transaction_id,
            disposition=args.disposition,
            same_family_evidence=args.same_family_evidence,
        )
    else:  # pragma: no cover
        parser.error(f"Unknown command: {args.command}")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
