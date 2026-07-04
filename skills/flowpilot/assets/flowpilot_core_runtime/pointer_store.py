"""Current-run pointer persistence and recovery helpers.

This module owns only the .flowpilot/current.json and .flowpilot/index.json
mechanics. It deliberately keeps the pointer JSON shape owned by run_shell.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from flowpilot_router_errors import RouterError, RouterLedgerWriteInProgress
from flowpilot_router_io_json import write_json_atomic
import flowpilot_router_io_locks as router_io_locks

from . import runtime


RUN_POINTER_SCHEMA_VERSION = "black_box_flowpilot_run_shell.v1"
_UNSUPPORTED_RUN_POINTER_FIELDS = {
    "current_run_id",
    "current_run_root",
    "active_run_id",
    "active_run_root",
}


@dataclass(frozen=True)
class PointerRecoveryResult:
    ok: bool
    current: dict[str, Any] | None = None
    index: dict[str, Any] | None = None
    error_code: str = ""
    message: str = ""
    backups: tuple[Path, ...] = ()


def write_pointer_json(path: Path, payload: dict[str, Any]) -> None:
    try:
        write_json_atomic(Path(path), payload, sort_keys=True, verify=True)
    except RouterLedgerWriteInProgress:
        raise
    except (OSError, RouterError) as exc:
        raise runtime.BlackBoxRuntimeError(f"could not write FlowPilot pointer JSON {path}: {exc}") from exc


def append_index(root: Path, current: dict[str, Any]) -> None:
    flowpilot_root = Path(root).resolve() / ".flowpilot"
    index_path = flowpilot_root / "index.json"
    backups: list[Path] = []
    payload, _ = _read_json_object(index_path)
    if payload is None or not isinstance(payload.get("runs"), list):
        if index_path.exists():
            backups.append(_backup_corrupt_file(index_path))
        payload = rebuild_index_payload(root, current=current)
    runs = [item for item in payload.get("runs", []) if isinstance(item, dict) and item.get("run_id") != current["run_id"]]
    runs.append(current)
    payload["schema_version"] = RUN_POINTER_SCHEMA_VERSION
    payload["runs"] = runs
    write_pointer_json(index_path, payload)


def recover_current_pointer(root: Path) -> PointerRecoveryResult:
    resolved_root = Path(root).resolve()
    flowpilot_root = resolved_root / ".flowpilot"
    current_path = flowpilot_root / "current.json"
    index_path = flowpilot_root / "index.json"
    backups: list[Path] = []

    current_lock = _active_write_lock(current_path)
    if current_lock:
        return PointerRecoveryResult(
            False,
            error_code="pointer_write_in_progress",
            message=f"current pointer write is still in progress: {current_lock.get('classification')}",
        )

    index_payload, _ = _read_json_object(index_path)
    index_candidates = _current_candidates_from_index(resolved_root, index_payload) if index_payload else []
    run_candidates = _current_candidates_from_run_ledgers(resolved_root)

    selected = _single_unambiguous_candidate(index_candidates) or _single_unambiguous_candidate(run_candidates)
    if selected is None:
        candidate_count = len(_dedupe_candidates([*index_candidates, *run_candidates]))
        code = "ambiguous_current_recovery" if candidate_count > 1 else "current_recovery_unavailable"
        return PointerRecoveryResult(
            False,
            error_code=code,
            message=(
                "cannot recover .flowpilot/current.json because current run evidence is "
                f"{'ambiguous' if candidate_count > 1 else 'missing'}"
            ),
        )

    if current_path.exists():
        backups.append(_backup_corrupt_file(current_path))
    write_pointer_json(current_path, selected)

    index_result = recover_index_pointer(resolved_root, current=selected)
    backups.extend(index_result.backups)
    return PointerRecoveryResult(
        True,
        current=selected,
        index=index_result.index,
        backups=tuple(backups),
    )


def recover_index_pointer(root: Path, *, current: dict[str, Any]) -> PointerRecoveryResult:
    resolved_root = Path(root).resolve()
    index_path = resolved_root / ".flowpilot" / "index.json"
    backups: list[Path] = []

    index_lock = _active_write_lock(index_path)
    if index_lock:
        return PointerRecoveryResult(
            False,
            error_code="pointer_write_in_progress",
            message=f"index pointer write is still in progress: {index_lock.get('classification')}",
        )

    payload, _ = _read_json_object(index_path)
    if payload is not None and isinstance(payload.get("runs"), list):
        return PointerRecoveryResult(True, current=current, index=payload)

    if index_path.exists():
        backups.append(_backup_corrupt_file(index_path))
    payload = rebuild_index_payload(resolved_root, current=current)
    write_pointer_json(index_path, payload)
    return PointerRecoveryResult(True, current=current, index=payload, backups=tuple(backups))


def rebuild_index_payload(root: Path, *, current: dict[str, Any] | None = None) -> dict[str, Any]:
    runs = _current_candidates_from_run_ledgers(Path(root).resolve())
    if current is not None:
        runs = [item for item in runs if item.get("run_id") != current.get("run_id")]
        runs.append(current)
    return {
        "schema_version": RUN_POINTER_SCHEMA_VERSION,
        "runs": runs,
    }


def current_payload_from_ledger(
    root: Path,
    *,
    run_id: str,
    run_root: Path,
    ledger_path: Path,
    ledger: dict[str, Any],
    include_refresh_fields: bool,
) -> dict[str, Any]:
    lifecycle_state = str((ledger.get("lifecycle") or {}).get("state", ""))
    terminal_status = runtime.terminal_lifecycle_status(ledger)
    guard = ledger.get("lifecycle_guard") if isinstance(ledger.get("lifecycle_guard"), dict) else {}
    preflight = runtime.final_return_preflight(ledger, guard=guard)
    closure = ledger.get("closure") if isinstance(ledger.get("closure"), dict) else {}
    derived_status = lifecycle_state
    if terminal_status:
        derived_status = terminal_status
    elif preflight.get("allowed") is True and closure.get("decision") == "complete":
        derived_status = "terminal_complete"
    current: dict[str, Any] = {
        "schema_version": RUN_POINTER_SCHEMA_VERSION,
        "run_id": run_id,
        "run_root": str(Path(run_root).resolve()),
        "ledger_path": str(Path(ledger_path).resolve()),
        "authority": "current_run_ledger",
        "lifecycle_state": derived_status,
        "terminal_lifecycle_status": terminal_status,
        "controller_stop_allowed": bool(preflight.get("controller_stop_allowed") is True),
        "updated_at": runtime.now_iso(),
    }
    if include_refresh_fields:
        current.update(
            {
                "ledger_lifecycle_state": lifecycle_state,
                "final_return_allowed": bool(preflight.get("allowed") is True),
                "closure_decision": str(closure.get("decision", "not_attempted")),
            }
        )
    return current


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, "missing_file"
    except UnicodeDecodeError:
        return None, "invalid_utf8"
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError:
        return None, "unreadable_file"
    if not isinstance(payload, dict):
        return None, "json_not_object"
    return payload, ""


def _current_candidates_from_index(root: Path, payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return []
    candidates: list[dict[str, Any]] = []
    for item in payload["runs"]:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_current_candidate(root, item)
        if normalized is not None:
            candidates.append(normalized)
    return _dedupe_candidates(candidates)


def _current_candidates_from_run_ledgers(root: Path) -> list[dict[str, Any]]:
    runs_root = root / ".flowpilot" / "runs"
    if not runs_root.exists():
        return []
    candidates: list[dict[str, Any]] = []
    for run_root in sorted(path for path in runs_root.iterdir() if path.is_dir()):
        ledger_path = run_root / "ledger.json"
        ledger, _ = _read_json_object(ledger_path)
        if not isinstance(ledger, dict):
            continue
        run_id = str(ledger.get("run_id") or "").strip()
        if run_id != run_root.name:
            continue
        candidates.append(
            current_payload_from_ledger(
                root,
                run_id=run_id,
                run_root=run_root,
                ledger_path=ledger_path,
                ledger=ledger,
                include_refresh_fields=True,
            )
        )
    return _dedupe_candidates(candidates)


def _normalize_current_candidate(root: Path, item: dict[str, Any]) -> dict[str, Any] | None:
    if any(field in item for field in _UNSUPPORTED_RUN_POINTER_FIELDS):
        return None
    raw_run_id = item.get("run_id")
    raw_run_root = item.get("run_root")
    run_id = raw_run_id.strip() if isinstance(raw_run_id, str) else ""
    if not run_id:
        return None
    run_root = _project_path(root, str(raw_run_root or f".flowpilot/runs/{run_id}"))
    if not _is_run_root(root, run_root, run_id) or not run_root.exists():
        return None
    ledger_path = _project_path(root, str(item.get("ledger_path") or run_root / "ledger.json"))
    ledger, _ = _read_json_object(ledger_path)
    if not isinstance(ledger, dict) or str(ledger.get("run_id") or "") != run_id:
        return None
    normalized = dict(item)
    normalized["run_id"] = run_id
    normalized["run_root"] = str(run_root)
    normalized["ledger_path"] = str(ledger_path)
    return normalized


def _single_unambiguous_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    deduped = _dedupe_candidates(candidates)
    return deduped[0] if len(deduped) == 1 else None


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        run_id = str(candidate.get("run_id") or "")
        if run_id:
            by_id[run_id] = candidate
    return [by_id[run_id] for run_id in sorted(by_id)]


def _backup_corrupt_file(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.name}.corrupt-backup-{timestamp}")
    counter = 1
    while backup_path.exists():
        counter += 1
        backup_path = path.with_name(f"{path.name}.corrupt-backup-{timestamp}-{counter}")
    shutil.copy2(path, backup_path)
    return backup_path


def _active_write_lock(path: Path) -> dict[str, Any] | None:
    liveness = router_io_locks._json_write_lock_liveness(path)
    return liveness if liveness.get("active") else None


def _project_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def _is_run_root(root: Path, run_root: Path, run_id: str) -> bool:
    runs_root = (root / ".flowpilot" / "runs").resolve()
    try:
        run_root.relative_to(runs_root)
    except ValueError:
        return False
    return run_root.name == run_id
