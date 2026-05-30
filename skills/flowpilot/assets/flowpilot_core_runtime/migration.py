"""Migration and cutover helpers for the complete black-box runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import runtime


ALLOWED_DISPOSITIONS = {"reference", "negative_test", "diagnostic", "imported_read_only", "quarantined"}


def classify_old_artifact(path: Path, *, disposition: str, reason: str) -> dict[str, Any]:
    if disposition not in ALLOWED_DISPOSITIONS:
        raise runtime.BlackBoxRuntimeError(f"unsupported old artifact disposition: {disposition}")
    return {
        "path": str(path),
        "disposition": disposition,
        "reason": reason,
        "current_authority": False,
    }


def import_old_artifact(
    ledger: dict[str, Any],
    path: Path,
    *,
    disposition: str,
    reason: str,
) -> str:
    imported_id = runtime._next_id(ledger, "import")
    record = classify_old_artifact(path, disposition=disposition, reason=reason)
    record["import_id"] = imported_id
    record["created_at"] = runtime.now_iso()
    ledger.setdefault("imported_evidence", {})[imported_id] = record
    runtime._event(ledger, "old_artifact_imported", import_id=imported_id, disposition=disposition)
    return imported_id


def evaluate_cutover_gate(
    ledger: dict[str, Any],
    *,
    openspec_ok: bool,
    flowguard_ok: bool,
    tests_ok: bool,
    install_ok: bool,
    live_host_ok: bool,
    git_ok: bool,
) -> dict[str, Any]:
    blockers = []
    if not openspec_ok:
        blockers.append("openspec_not_current")
    if not flowguard_ok:
        blockers.append("flowguard_not_current")
    if not tests_ok:
        blockers.append("tests_not_current")
    if not install_ok:
        blockers.append("install_not_current")
    if not live_host_ok:
        blockers.append("live_host_not_current")
    if not git_ok:
        blockers.append("git_not_current")
    gate = {
        "decision": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "created_at": runtime.now_iso(),
        "old_runtime_authority": False,
    }
    ledger["cutover_gate"] = gate
    runtime._event(ledger, "cutover_gate_evaluated", decision=gate["decision"], blockers=blockers)
    return gate
