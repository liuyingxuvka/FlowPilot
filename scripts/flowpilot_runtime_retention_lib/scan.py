"""Read-only inventory, protection, reference, and eligibility owner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from scripts.flowpilot_runtime_retention_lib.common import (
    ROOT,
    REPORT_SCHEMA_VERSION,
    _project_relative,
    _read_json,
    _read_json_result,
)


TERMINAL_LIFECYCLE_STATUSES = {
    "stopped_by_user",
    "cancelled_by_user",
    "repair_rounds_exhausted",
}
TERMINAL_VALIDATION_STATUSES = {
    "complete",
    "completed",
    "passed",
    "failed",
    "blocked",
    "cancelled",
}
TERMINAL_PACKET_STATUSES = {
    "accepted",
    "complete",
    "completed",
    "closed",
    "superseded",
    "cancelled",
}
TERMINAL_ACTION_STATUSES = {
    "complete",
    "completed",
    "done",
    "consumed",
    "superseded",
    "cancelled",
}

REFERENCE_NAME_MARKERS = {
    "checkpoint",
    "evidence",
    "impact-plan",
    "manifest",
    "owner-index",
    "plan",
    "proof",
    "reference",
    "release",
    "report",
    "ticket",
}
REFERENCE_SUFFIXES = {".json", ".jsonl", ".md", ".toml", ".yaml", ".yml"}
MAX_REFERENCE_FILE_BYTES = 8 * 1024 * 1024

def _tree_size(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    total = 0
    count = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        count += 1
        try:
            total += child.stat().st_size
        except OSError:
            pass
    return total, count

def _parse_timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run_timestamp(run_id: str, entry: Mapping[str, Any] | None, run_dir: Path) -> datetime | None:
    for key in ("archived_at", "updated_at", "completed_at", "stopped_at", "created_at"):
        if entry:
            parsed = _parse_timestamp(entry.get(key))
            if parsed is not None:
                return parsed
    if run_dir.exists():
        try:
            return datetime.fromtimestamp(run_dir.stat().st_mtime, tz=timezone.utc)
        except OSError:
            return None
    return None


def _index_entries(index: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    entries: dict[str, dict[str, Any]] = {}
    for item in index.get("runs", []):
        if isinstance(item, dict) and item.get("run_id"):
            entries[str(item["run_id"])] = item
    return entries


def _pid_is_live(value: Any) -> bool:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            pid,
        )
        if not handle:
            # Access denied still proves that a process owns the PID.
            return ctypes.get_last_error() == 5
        exit_code = ctypes.c_ulong()
        try:
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _payload_live_pid(payload: Mapping[str, Any]) -> bool:
    for key in ("pid", "process_id", "owner_pid", "supervisor_pid", "child_pid"):
        if _pid_is_live(payload.get(key)):
            return True
    return False


def _lock_is_active(path: Path) -> bool:
    payload, error = _read_json_result(path, max_bytes=256 * 1024)
    if error:
        return True
    assert payload is not None
    status = str(payload.get("status") or "").lower()
    if status in {"released", "closed", "complete", "completed"} and not _payload_live_pid(payload):
        return False
    return True


def _active_write_lock_paths(candidate: Path) -> list[str]:
    paths: list[str] = []
    for child in candidate.rglob("*"):
        if not child.is_file():
            continue
        name = child.name.lower()
        if name.endswith(".lock") or "write-lock" in name or "write_lock" in name:
            if _lock_is_active(child):
                paths.append(child.relative_to(candidate).as_posix())
    return sorted(paths)


def _run_terminal_evidence(ledger: Mapping[str, Any], run_dir: Path) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    terminal = ledger.get("terminal_lifecycle")
    if isinstance(terminal, Mapping) and str(terminal.get("status") or "") in TERMINAL_LIFECYCLE_STATUSES:
        evidence.append("ledger.json#terminal_lifecycle")
    closure = ledger.get("closure")
    status_projection = ledger.get("status_projection")
    if (
        isinstance(closure, Mapping)
        and str(closure.get("decision") or "") == "complete"
        and isinstance(status_projection, Mapping)
        and status_projection.get("final_return_allowed") is True
    ):
        evidence.append("ledger.json#closure")
    terminal_path = run_dir / "lifecycle" / "terminal_lifecycle.json"
    terminal_file = _read_json(terminal_path)
    if str(terminal_file.get("status") or "") in TERMINAL_LIFECYCLE_STATUSES:
        evidence.append("lifecycle/terminal_lifecycle.json")
    closure_path = run_dir / "closure" / "final_closure.json"
    closure_file = _read_json(closure_path)
    if (
        str(closure_file.get("closure_decision") or closure_file.get("decision") or "") == "complete"
        and closure_file.get("final_return_allowed") is True
    ):
        evidence.append("closure/final_closure.json")
    return bool(evidence), sorted(set(evidence))


def _run_live_owner(run_dir: Path) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    for relative in (
        "runtime/router_daemon.lock",
        "runtime/router_daemon_status.json",
    ):
        path = run_dir / relative
        payload = _read_json(path)
        if payload and _payload_live_pid(payload):
            evidence.append(relative)
    return bool(evidence), evidence


def _run_open_work(ledger: Mapping[str, Any], run_dir: Path) -> tuple[bool, bool]:
    active_lease = any(
        isinstance(lease, Mapping) and str(lease.get("status") or "") == "active"
        for lease in (ledger.get("leases") or {}).values()
    ) if isinstance(ledger.get("leases"), Mapping) else False
    open_packet = False
    packets = ledger.get("packets")
    if isinstance(packets, Mapping):
        for packet in packets.values():
            if not isinstance(packet, Mapping):
                open_packet = True
                break
            status = str(packet.get("status") or "")
            if packet.get("accepted_result_id") or status in TERMINAL_PACKET_STATUSES:
                continue
            open_packet = True
            break
    open_action = False
    actions_root = run_dir / "runtime" / "controller_actions"
    if actions_root.exists():
        for path in actions_root.glob("*.json"):
            action, error = _read_json_result(path)
            if error or action is None:
                open_action = True
                break
            if str(action.get("status") or "") not in TERMINAL_ACTION_STATUSES:
                open_action = True
                break
    return active_lease, open_packet or open_action


def _validation_terminal_evidence(candidate: Path) -> tuple[bool, bool, list[str], list[str]]:
    meta_paths = sorted(candidate.rglob("*.meta.json"))
    evidence: list[str] = []
    errors: list[str] = []
    live_owner = False
    if not meta_paths:
        return False, False, evidence, ["terminal_meta_missing"]
    for meta_path in meta_paths:
        payload, error = _read_json_result(meta_path, max_bytes=1024 * 1024)
        relative = meta_path.relative_to(candidate).as_posix()
        if error or payload is None:
            errors.append(f"{relative}:{error}")
            continue
        status = str(payload.get("status") or "").lower()
        live_owner = live_owner or status in {"running", "started", "pending"} or _payload_live_pid(payload)
        if status not in TERMINAL_VALIDATION_STATUSES:
            errors.append(f"{relative}:nonterminal_status:{status or 'missing'}")
            continue
        exit_path = meta_path.with_name(meta_path.name.removesuffix(".meta.json") + ".exit.txt")
        if not exit_path.is_file():
            errors.append(f"{relative}:terminal_exit_missing")
            continue
        evidence.extend([relative, exit_path.relative_to(candidate).as_posix()])
    return not errors and bool(evidence), live_owner, sorted(evidence), errors


def _pinned(index_entry: Mapping[str, Any] | None, candidate: Path) -> bool:
    if index_entry:
        if index_entry.get("pinned") is True:
            return True
        tags = index_entry.get("tags")
        if isinstance(tags, list) and "pinned" in {str(item).lower() for item in tags}:
            return True
    return (candidate / ".retention-pin").exists()


def _reference_sources(root: Path) -> tuple[list[Path], list[str]]:
    sources: set[Path] = set()
    errors: list[str] = []
    current_path = root / ".flowpilot" / "current.json"
    if current_path.is_file():
        sources.add(current_path)
    search_roots = (
        root / ".flowpilot" / "runs",
        root / "tmp" / "test_background",
        root / "reports",
        root / "promotion-kit",
        root / ".flowguard",
    )
    for search_root in search_roots:
        if not search_root.exists():
            continue
        for path in search_root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in REFERENCE_SUFFIXES:
                continue
            lowered = path.name.lower()
            if not any(marker in lowered for marker in REFERENCE_NAME_MARKERS):
                continue
            if ".flowpilot/retention-plans/" in path.as_posix():
                continue
            try:
                if path.stat().st_size > MAX_REFERENCE_FILE_BYTES:
                    errors.append(f"reference_file_too_large:{_project_relative(root, path)}")
                    continue
            except OSError:
                errors.append(f"reference_file_unreadable:{_project_relative(root, path)}")
                continue
            sources.add(path)
    return sorted(sources), errors


def _is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _attach_references(
    root: Path,
    records: list[dict[str, Any]],
) -> list[str]:
    sources, errors = _reference_sources(root)
    token_records: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for token in {str(record["entry_id"]), str(record["path"])}:
            if token:
                token_records.setdefault(token, []).append(record)
    token_pattern = (
        re.compile(
            "|".join(
                re.escape(token)
                for token in sorted(token_records, key=len, reverse=True)
            )
        )
        if token_records
        else None
    )
    for source in sources:
        try:
            text = source.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            errors.append(f"reference_file_unreadable:{_project_relative(root, source)}")
            continue
        if token_pattern is None:
            continue
        source_label = _project_relative(root, source)
        matched_records: dict[int, dict[str, Any]] = {}
        for match in token_pattern.finditer(text):
            for record in token_records[match.group(0)]:
                matched_records[id(record)] = record
        for record in matched_records.values():
            candidate = root / record["path"]
            if not _is_within(source, candidate):
                record["referenced_by"].append(source_label)
    for record in records:
        record["referenced_by"] = sorted(set(record["referenced_by"]))
    return sorted(set(errors))


def _record_protection_reasons(
    record: Mapping[str, Any],
    *,
    global_reasons: Iterable[str],
) -> list[str]:
    reasons = list(global_reasons)
    checks = (
        ("current_run", record.get("is_current") is True),
        ("index_identity_missing", record.get("index_status") == "missing"),
        ("index_identity_inconsistent", record.get("index_status") == "inconsistent"),
        ("directory_missing", record.get("directory_exists") is not True),
        ("terminal_evidence_missing", record.get("terminal_evidence_ok") is not True),
        ("live_owner", record.get("live_owner") is True),
        ("active_lease", record.get("active_lease") is True),
        ("open_packet_or_action", record.get("open_packet_or_action") is True),
        ("write_lock", record.get("write_lock") is True),
        ("referenced", bool(record.get("referenced_by"))),
        ("pinned", record.get("pinned") is True),
        ("state_unknown", bool(record.get("state_errors"))),
        ("symlink_present", record.get("symlink_present") is True),
    )
    reasons.extend(reason for reason, active in checks if active)
    return sorted(set(reasons))


def _rank_eligible_records(
    records: list[dict[str, Any]],
    *,
    max_runs: int,
    max_age_days: int | None,
) -> None:
    eligible = [record for record in records if record["eligible"]]
    eligible.sort(key=lambda record: (record["timestamp"] or "", record["entry_id"]))
    excess_count = max(0, len(records) - max_runs)
    count_selected = {record["entry_id"] for record in eligible[:excess_count]}
    age_selected: set[str] = set()
    if max_age_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        for record in eligible:
            parsed = _parse_timestamp(record["timestamp"])
            if parsed is not None and parsed <= cutoff:
                age_selected.add(record["entry_id"])
    for rank, record in enumerate(eligible, start=1):
        record["eligibility_rank"] = rank
        if record["entry_id"] in count_selected or record["entry_id"] in age_selected:
            record["proposed_action"] = "archive"
            record["selection_reasons"] = sorted(
                [
                    reason
                    for reason, selected in (
                        ("max_runs_excess", record["entry_id"] in count_selected),
                        ("max_age_exceeded", record["entry_id"] in age_selected),
                    )
                    if selected
                ]
            )
        else:
            record["proposed_action"] = "retain"
            record["selection_reasons"] = []


def build_report(
    project_root: Path = ROOT,
    *,
    max_runs: int = 30,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    if max_runs < 0:
        raise ValueError("max_runs must be non-negative")
    if max_age_days is not None and max_age_days < 0:
        raise ValueError("max_age_days must be non-negative")
    root = project_root.resolve()
    flowpilot_root = root / ".flowpilot"
    current_path = flowpilot_root / "current.json"
    index_path = flowpilot_root / "index.json"
    runs_root = flowpilot_root / "runs"
    validation_root = root / "tmp" / "test_background"

    current, current_error = _read_json_result(current_path)
    index, index_error = _read_json_result(index_path)
    indexed = _index_entries(index or {})
    current_run_id = str((current or {}).get("run_id") or "")
    global_reasons = []
    if current_error:
        global_reasons.append(f"current_pointer_{current_error}")
    if index_error:
        global_reasons.append(f"run_index_{index_error}")

    run_dirs = (
        {path.name: path for path in runs_root.iterdir() if path.is_dir()}
        if runs_root.exists()
        else {}
    )
    records: list[dict[str, Any]] = []
    for run_id in sorted(set(run_dirs) | set(indexed)):
        run_dir = run_dirs.get(run_id, runs_root / run_id)
        index_entry = indexed.get(run_id)
        ledger, ledger_error = _read_json_result(
            run_dir / "ledger.json",
            max_bytes=8 * 1024 * 1024,
        )
        terminal_ok, terminal_refs = _run_terminal_evidence(ledger or {}, run_dir)
        live_owner, live_refs = _run_live_owner(run_dir)
        active_lease, open_work = _run_open_work(ledger or {}, run_dir)
        lock_paths = _active_write_lock_paths(run_dir) if run_dir.exists() else []
        size_bytes, file_count = _tree_size(run_dir)
        timestamp = _run_timestamp(run_id, index_entry, run_dir)
        records.append(
            {
                "kind": "run",
                "entry_id": run_id,
                "run_id": run_id,
                "path": _project_relative(root, run_dir),
                "indexed": index_entry is not None,
                "index_status": (
                    "present"
                    if index_entry is not None and run_dir.exists()
                    else "missing"
                    if index_entry is None
                    else "inconsistent"
                ),
                "directory_exists": run_dir.exists(),
                "is_current": run_id == current_run_id,
                "status": (index_entry or {}).get("status"),
                "timestamp": timestamp.isoformat() if timestamp else None,
                "bytes": size_bytes,
                "file_count": file_count,
                "terminal_evidence_ok": terminal_ok,
                "terminal_evidence_refs": terminal_refs,
                "live_owner": live_owner,
                "live_owner_refs": live_refs,
                "active_lease": active_lease,
                "open_packet_or_action": open_work,
                "write_lock": bool(lock_paths),
                "write_lock_paths": lock_paths,
                "referenced_by": [],
                "pinned": _pinned(index_entry, run_dir),
                "state_errors": [f"ledger:{ledger_error}"] if ledger_error else [],
                "symlink_present": any(path.is_symlink() for path in run_dir.rglob("*")) if run_dir.exists() else False,
            }
        )

    if validation_root.exists():
        for candidate in sorted(path for path in validation_root.iterdir() if path.is_dir()):
            terminal_ok, live_owner, terminal_refs, state_errors = _validation_terminal_evidence(candidate)
            lock_paths = _active_write_lock_paths(candidate)
            size_bytes, file_count = _tree_size(candidate)
            timestamp = _run_timestamp(candidate.name, None, candidate)
            records.append(
                {
                    "kind": "test_background",
                    "entry_id": candidate.name,
                    "run_id": None,
                    "path": _project_relative(root, candidate),
                    "indexed": None,
                    "index_status": "present" if not index_error else "inconsistent",
                    "directory_exists": True,
                    "is_current": False,
                    "status": "terminal" if terminal_ok else "unknown",
                    "timestamp": timestamp.isoformat() if timestamp else None,
                    "bytes": size_bytes,
                    "file_count": file_count,
                    "terminal_evidence_ok": terminal_ok,
                    "terminal_evidence_refs": terminal_refs,
                    "live_owner": live_owner,
                    "live_owner_refs": terminal_refs if live_owner else [],
                    "active_lease": False,
                    "open_packet_or_action": False,
                    "write_lock": bool(lock_paths),
                    "write_lock_paths": lock_paths,
                    "referenced_by": [],
                    "pinned": _pinned(None, candidate),
                    "state_errors": state_errors,
                    "symlink_present": any(path.is_symlink() for path in candidate.rglob("*")),
                }
            )

    reference_errors = _attach_references(root, records)
    global_reasons.extend(reference_errors)
    for record in records:
        record["protected_reasons"] = _record_protection_reasons(
            record,
            global_reasons=global_reasons,
        )
        record["eligible"] = not record["protected_reasons"]
        record["proposed_action"] = "protect" if record["protected_reasons"] else "retain"
        record["selection_reasons"] = []
        record["eligibility_rank"] = None

    run_records = [record for record in records if record["kind"] == "run"]
    validation_records = [record for record in records if record["kind"] == "test_background"]
    _rank_eligible_records(run_records, max_runs=max_runs, max_age_days=max_age_days)
    _rank_eligible_records(validation_records, max_runs=max_runs, max_age_days=max_age_days)
    archive_candidates = [
        record for record in records if record["proposed_action"] == "archive"
    ]
    flowpilot_bytes, flowpilot_file_count = _tree_size(flowpilot_root)
    validation_bytes, validation_file_count = _tree_size(validation_root)
    indexed_ids = set(indexed)
    run_dir_ids = set(run_dirs)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "ok": True,
        "read_only": True,
        "project_root": str(root),
        "flowpilot_root": _project_relative(root, flowpilot_root),
        "validation_root": _project_relative(root, validation_root),
        "exists": flowpilot_root.exists(),
        "current_run_id": current_run_id or None,
        "current_path_exists": current_path.exists(),
        "index_path_exists": index_path.exists(),
        "global_protection_reasons": sorted(set(global_reasons)),
        "indexed_run_count": len(indexed_ids),
        "run_directory_count": len(run_dir_ids),
        "validation_directory_count": len(validation_records),
        "total_bytes": flowpilot_bytes + validation_bytes,
        "total_files": flowpilot_file_count + validation_file_count,
        "flowpilot_bytes": flowpilot_bytes,
        "flowpilot_files": flowpilot_file_count,
        "validation_bytes": validation_bytes,
        "validation_files": validation_file_count,
        "missing_run_dirs": sorted(indexed_ids - run_dir_ids),
        "unindexed_run_dirs": sorted(run_dir_ids - indexed_ids),
        "max_runs": max_runs,
        "max_age_days": max_age_days,
        "excess_run_directory_count": max(0, len(run_records) - max_runs),
        "excess_validation_directory_count": max(0, len(validation_records) - max_runs),
        "eligible_count": sum(1 for record in records if record["eligible"]),
        "archive_candidate_count": len(archive_candidates),
        "records": records,
        "run_records": run_records,
        "validation_records": validation_records,
        "stale_candidates": archive_candidates,
        "recommendation": (
            "This command is read-only. Use the explicit plan command to freeze eligible "
            "candidates, then invoke apply with that exact plan path and SHA-256."
        ),
    }
