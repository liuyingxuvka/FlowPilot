"""Read-only verification of completed background test-tier evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from .background import (
    _read_background_meta,
    _read_exit_code,
    artifact_paths,
    background_supervisor_name,
    classify_background_artifact,
)
from .definitions import TierCommand
from .source_fingerprint import source_fingerprint


def verify_background_tier(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
    expected_source_fingerprint: str | None = None,
) -> dict[str, Any]:
    """Verify an existing background tier without launching or rewriting it."""

    expected_source = expected_source_fingerprint or source_fingerprint()
    failures: list[str] = []
    child_reports: list[dict[str, Any]] = []
    supervisor_name = background_supervisor_name(tier)
    supervisor_paths = artifact_paths(log_root, supervisor_name)
    supervisor_present = supervisor_paths["meta"].is_file() or supervisor_paths["exit"].is_file()

    if supervisor_present:
        missing_supervisor = [
            key for key, path in supervisor_paths.items() if not path.is_file()
        ]
        if missing_supervisor:
            failures.append(
                "supervisor_missing_artifacts:" + ",".join(sorted(missing_supervisor))
            )
        meta, meta_error = _read_background_meta(supervisor_paths["meta"])
        exit_code = _read_exit_code(supervisor_paths["exit"])
        if meta_error:
            failures.append(f"supervisor_{meta_error}")
            meta = {}
        meta = meta or {}
        if meta.get("status") != "passed" or exit_code != 0:
            failures.append("supervisor_not_passed")
        if int(meta.get("command_count") or -1) != len(commands):
            failures.append("supervisor_command_count_mismatch")
        if meta.get("running"):
            failures.append("supervisor_still_running")
        if (
            str(meta.get("covered_source_fingerprint_start") or "") != expected_source
            or str(meta.get("covered_source_fingerprint_end") or "") != expected_source
            or meta.get("source_fingerprint_current") is not True
        ):
            failures.append("supervisor_source_fingerprint_stale")
        completed = meta.get("completed") if isinstance(meta.get("completed"), list) else []
        completed_names = {
            str(row.get("name") or "") for row in completed if isinstance(row, dict)
        }
        expected_names = {command.name for command in commands}
        if completed_names != expected_names:
            failures.append("supervisor_completed_command_set_mismatch")
        if any(not bool(row.get("ok")) for row in completed if isinstance(row, dict)):
            failures.append("supervisor_contains_nonpassing_child")
    elif len(commands) != 1:
        failures.append("background_supervisor_missing_for_multi_command_tier")

    expected_child_meta = {
        artifact_paths(log_root, command.name)["meta"].resolve() for command in commands
    }
    expected_child_exit = {
        artifact_paths(log_root, command.name)["exit"].resolve() for command in commands
    }
    actual_child_meta = {
        path.resolve()
        for path in log_root.glob("*.meta.json")
        if path.resolve() != supervisor_paths["meta"].resolve()
    }
    actual_child_exit = {
        path.resolve()
        for path in log_root.glob("*.exit.txt")
        if path.resolve() != supervisor_paths["exit"].resolve()
    }
    if actual_child_meta != expected_child_meta:
        failures.append("child_meta_artifact_set_mismatch")
    if actual_child_exit != expected_child_exit:
        failures.append("child_exit_artifact_set_mismatch")

    for command in commands:
        paths = artifact_paths(log_root, command.name)
        missing = [key for key, path in paths.items() if not path.is_file()]
        evidence = classify_background_artifact(
            log_root,
            command.name,
            command=command,
            tier=tier,
        )
        meta, meta_error = _read_background_meta(paths["meta"])
        row_failures: list[str] = []
        if missing:
            row_failures.append("missing_artifacts:" + ",".join(sorted(missing)))
        if meta_error:
            row_failures.append(meta_error)
        meta = meta or {}
        if list(meta.get("command") or []) != list(command.command):
            row_failures.append("command_mismatch")
        if str(meta.get("covered_source_fingerprint") or "") != expected_source:
            row_failures.append("covered_source_fingerprint_stale")
        if evidence.get("status") != "passed" or not evidence.get("ok"):
            row_failures.append(f"evidence_not_passed:{evidence.get('status')}")
        if row_failures:
            failures.extend(f"{command.name}:{reason}" for reason in row_failures)
        child_reports.append(
            {
                "name": command.name,
                "ok": not row_failures,
                "status": evidence.get("status"),
                "failures": row_failures,
                "artifacts": evidence.get("artifacts"),
            }
        )

    return {
        "ok": not failures,
        "tier": tier,
        "log_root": str(log_root),
        "source_fingerprint": expected_source,
        "supervisor_present": supervisor_present,
        "selected_count": len(commands),
        "verified_count": sum(1 for row in child_reports if row["ok"]),
        "failures": sorted(set(failures)),
        "children": child_reports,
    }


__all__ = ["verify_background_tier"]
