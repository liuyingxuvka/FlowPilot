"""Recovery Supervisor transaction helpers for Controller break-glass."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


def _core() -> Any:
    for name in ("flowpilot_controller_break_glass", "__main__"):
        module = sys.modules.get(name)
        if getattr(module, "RECOVERY_TRANSACTION_SCHEMA", None):
            return module
    raise RuntimeError("flowpilot_controller_break_glass core module is not loaded")


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
    core = _core()
    transaction_id = core.safe_id(transaction_id, "recovery")
    incident_id = core.safe_id(incident_id, "incident")
    transaction = {
        "schema_version": core.RECOVERY_TRANSACTION_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction_id,
        "status": "open",
        "identity_mode": "recovery_supervisor",
        "opened_at": core.utc_now(),
        "opened_by_role": "recovery_supervisor",
        "normal_controller_suspended": True,
        "controller_generation_before": controller_generation_id,
        "linked_incident_id": incident_id,
        "trigger_summary": trigger_summary,
        "control_plane_failure_kind": failure_kind,
        "blocker_ids": [core.safe_id(item, "blocker") for item in blocker_ids],
        "defect_family_ids": [core.safe_id(item, "family") for item in family_ids],
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
    tx_ref = core._save_recovery_transaction(project_root, run_root, transaction)
    index = core.load_index(run_root)
    index["recovery_transactions"] = [
        item for item in index.get("recovery_transactions", []) if item.get("transaction_id") != transaction_id
    ]
    index["recovery_transactions"].append({"transaction_id": transaction_id, "path": tx_ref["path"], "status": "open"})
    core.save_index(run_root, index)
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
    core = _core()
    if not reason.strip():
        raise SystemExit("Body access grant requires a non-empty reason.")
    if not unavailable_role_lanes:
        raise SystemExit("Body access grant requires at least one unavailable or contradictory role lane.")
    transaction = core._load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Body access grant requires an open recovery transaction.")
    grant_id = core.safe_id(grant_id, "grant")
    path = Path(body_path)
    absolute = path if path.is_absolute() else project_root / path
    grant = {
        "schema_version": core.BODY_ACCESS_GRANT_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction["transaction_id"],
        "grant_id": grant_id,
        "granted_at": core.utc_now(),
        "granted_to_identity": "recovery_supervisor",
        "normal_controller_body_access_granted": False,
        "body_path": body_path,
        "body_hash": core.sha256_path(absolute),
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
    grant_path = core.body_access_grant_path(run_root, grant_id)
    core.write_json(grant_path, grant)
    grants = [item for item in transaction.get("body_access_grants", []) if item.get("grant_id") != grant_id]
    grants.append({"grant_id": grant_id, "path": core.project_relative(project_root, grant_path), "body_hash": grant["body_hash"]})
    transaction["body_access_grants"] = grants
    core._save_recovery_transaction(project_root, run_root, transaction)
    index = core.load_index(run_root)
    index["body_access_grants"] = [item for item in index.get("body_access_grants", []) if item.get("grant_id") != grant_id]
    index["body_access_grants"].append(
        {"grant_id": grant_id, "transaction_id": transaction["transaction_id"], "path": core.project_relative(project_root, grant_path)}
    )
    core.save_index(run_root, index)
    return {"ok": True, "grant": grant, "grant_path": core.project_relative(project_root, grant_path)}


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
    core = _core()
    if previous_generation_id == next_generation_id:
        raise SystemExit("Controller reinjection requires a new generation id.")
    transaction = core._load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Controller reinjection requires an open recovery transaction.")
    reinjection_id = core.safe_id(reinjection_id, "reinject")
    core_path = Path(controller_core_path)
    absolute_core = core_path if core_path.is_absolute() else project_root / core_path
    proof_records = core._source_records(project_root, proof_artifacts)
    reinjection = {
        "schema_version": core.CONTROLLER_REINJECTION_SCHEMA,
        "run_id": run_root.name,
        "transaction_id": transaction["transaction_id"],
        "reinjection_id": reinjection_id,
        "recorded_at": core.utc_now(),
        "previous_controller_generation_id": previous_generation_id,
        "next_controller_generation_id": next_generation_id,
        "old_controller_generation_invalidated": True,
        "controller_core_path": controller_core_path,
        "controller_core_hash": core.sha256_path(absolute_core),
        "boundary_proof_path": boundary_proof_path,
        "proof_artifacts": proof_records,
        "normal_controller_restrictions_restored": {
            "sealed_body_access": False,
            "gate_approval": False,
            "route_mutation": False,
            "target_project_work": False,
        },
    }
    reinjection_path = core.controller_reinjection_path(run_root, reinjection_id)
    core.write_json(reinjection_path, reinjection)
    transaction["controller_reinjection"] = {
        "reinjection_id": reinjection_id,
        "path": core.project_relative(project_root, reinjection_path),
        "next_controller_generation_id": next_generation_id,
    }
    core._save_recovery_transaction(project_root, run_root, transaction)
    index = core.load_index(run_root)
    index["controller_reinjections"] = [
        item for item in index.get("controller_reinjections", []) if item.get("reinjection_id") != reinjection_id
    ]
    index["controller_reinjections"].append(
        {"reinjection_id": reinjection_id, "transaction_id": transaction["transaction_id"], "path": core.project_relative(project_root, reinjection_path)}
    )
    core.save_index(run_root, index)
    return {"ok": True, "reinjection": reinjection, "reinjection_path": core.project_relative(project_root, reinjection_path)}


def close_recovery_transaction(
    project_root: Path,
    run_root: Path,
    *,
    transaction_id: str,
    disposition: str,
    same_family_evidence: list[str],
) -> dict[str, Any]:
    core = _core()
    transaction = core._load_recovery_transaction(run_root, transaction_id)
    if transaction.get("status") != "open":
        raise SystemExit("Recovery transaction is not open.")
    if not same_family_evidence:
        raise SystemExit("Recovery transaction closure requires same-family FlowGuard evidence.")
    if not transaction.get("controller_reinjection"):
        raise SystemExit("Recovery transaction closure requires Controller reinjection proof.")

    ledger = core.load_control_plane_blocker_ledger(run_root)
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

    evidence_records = core._source_records(project_root, same_family_evidence)
    transaction["same_family_repair"]["evidence"] = evidence_records
    transaction["status"] = "closed"
    transaction["closed_at"] = core.utc_now()
    transaction["final_disposition"] = disposition
    transaction["normal_controller_suspended"] = False
    tx_ref = core._save_recovery_transaction(project_root, run_root, transaction)
    index = core.load_index(run_root)
    for item in index.get("recovery_transactions", []):
        if item.get("transaction_id") == transaction.get("transaction_id"):
            item["status"] = "closed"
            item["final_disposition"] = disposition
    core.save_index(run_root, index)
    return {"ok": True, "transaction": transaction, "transaction_path": tx_ref["path"]}
