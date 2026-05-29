"""Core data, paths, and validation helpers for Controller break-glass."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_runtime_gateway import GATEWAY_BREAK_GLASS, assert_runtime_gateway_write


INCIDENT_SCHEMA = "flowpilot.controller_break_glass_incident.v1"
PATCH_SCHEMA = "flowpilot.controller_break_glass_patch.v1"
INDEX_SCHEMA = "flowpilot.controller_break_glass_index.v1"
RECOVERY_TRANSACTION_SCHEMA = "flowpilot.recovery_supervisor_transaction.v1"
CONTROL_BLOCKER_LEDGER_SCHEMA = "flowpilot.control_plane_blocker_ledger.v1"
BODY_ACCESS_GRANT_SCHEMA = "flowpilot.recovery_supervisor_body_access_grant.v1"
CONTROLLER_REINJECTION_SCHEMA = "flowpilot.controller_reinjection.v1"

PATCH_SUCCESS_DISPOSITIONS = {
    "permanent_fix_applied",
    "superseded_by_permanent_fix",
}
PATCH_NON_SUCCESS_DISPOSITIONS = {
    "rolled_back",
    "diagnostic_only_no_patch",
    "weak_evidence_quarantined",
    "blocked_requires_manual_repair",
}
PATCH_FINAL_DISPOSITIONS = PATCH_SUCCESS_DISPOSITIONS | PATCH_NON_SUCCESS_DISPOSITIONS
PATCH_VALIDATION_CLOSED_RESULTS = {
    "passed",
    "skipped_with_reason",
    "not_applicable",
}
INCIDENT_BLOCKED_DISPOSITIONS = {"blocked_requires_manual_repair"}
INCIDENT_QUARANTINE_DISPOSITIONS = {"weak_evidence_quarantined"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    assert_runtime_gateway_write(path, GATEWAY_BREAK_GLASS, operation="break_glass_write_json")
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


def _patch_validation_status(patch: dict[str, Any]) -> str:
    evidence = patch.get("validation_evidence")
    if not isinstance(evidence, list) or not evidence:
        return "not_required" if patch.get("patch_kind") == "diagnostic_only" else "pending"
    results = [str(item.get("result") or "not_run") for item in evidence if isinstance(item, dict)]
    if not results:
        return "not_required" if patch.get("patch_kind") == "diagnostic_only" else "pending"
    if any(result in {"failed", "error"} for result in results):
        return "failed"
    if any(result == "not_run" for result in results):
        return "pending"
    if all(result in PATCH_VALIDATION_CLOSED_RESULTS for result in results):
        return "closed"
    return "review_required"


def _validate_patch_finalization(patch: dict[str, Any], *, disposition: str) -> None:
    if disposition not in PATCH_FINAL_DISPOSITIONS:
        raise SystemExit(f"Unsupported break-glass patch disposition: {disposition}")
    validation_status = _patch_validation_status(patch)
    if disposition in PATCH_SUCCESS_DISPOSITIONS and validation_status != "closed":
        raise SystemExit(
            "Cannot finalize break-glass patch as repaired while validation is "
            f"{validation_status}; record validation evidence or use blocked/quarantine disposition."
        )
    if disposition == "diagnostic_only_no_patch" and patch.get("patch_kind") != "diagnostic_only":
        raise SystemExit("diagnostic_only_no_patch disposition requires a diagnostic-only patch record.")


def _closed_recovery_transactions(run_root: Path, transaction_ids: list[str]) -> list[str]:
    closed: list[str] = []
    for transaction_id in transaction_ids:
        transaction = read_json(recovery_transaction_path(run_root, transaction_id))
        if transaction.get("schema_version") == RECOVERY_TRANSACTION_SCHEMA and transaction.get("status") == "closed":
            closed.append(safe_id(str(transaction_id), "recovery"))
    return closed


def _incident_closure_review(run_root: Path, incident: dict[str, Any], *, disposition: str) -> dict[str, Any]:
    patch_ids = [str(item) for item in incident.get("related_patch_ids") or []]
    transaction_ids = [str(item) for item in incident.get("related_recovery_transaction_ids") or []]
    closed_transactions = _closed_recovery_transactions(run_root, transaction_ids)
    if closed_transactions:
        return {
            "closure_path": "closed_recovery_transaction",
            "closed_recovery_transaction_ids": closed_transactions,
        }
    if disposition in INCIDENT_BLOCKED_DISPOSITIONS:
        return {"closure_path": "blocked_disposition"}
    if disposition in INCIDENT_QUARANTINE_DISPOSITIONS:
        return {"closure_path": "weak_evidence_quarantine"}
    if not patch_ids:
        if disposition == "diagnostic_only_no_patch":
            return {"closure_path": "validated_diagnostic_closure"}
        raise SystemExit(
            "Break-glass incident closure requires a recovery transaction, "
            "validated patch, diagnostic-only disposition, quarantine, or explicit blocked disposition."
        )
    pending: list[dict[str, str]] = []
    for patch_id in patch_ids:
        patch = read_json(break_glass_root(run_root) / "patches" / f"{safe_id(patch_id, 'patch')}.json")
        status = _patch_validation_status(patch)
        if disposition in PATCH_SUCCESS_DISPOSITIONS and status != "closed":
            pending.append({"patch_id": patch_id, "validation_status": status})
    if pending:
        raise SystemExit(
            "Break-glass incident has patch validation that is not closed: "
            + ", ".join(f"{item['patch_id']}={item['validation_status']}" for item in pending)
        )
    return {"closure_path": "validated_patch_closure"}
