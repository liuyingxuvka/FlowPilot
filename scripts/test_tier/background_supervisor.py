"""Bounded background-tier supervisor for the public test-tier facade."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Callable, Sequence

try:
    from .background import (
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _launch_background,
        _read_exit_code,
        _utc_now,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
    )
    from .definitions import TierCommand
    from .source_fingerprint import source_fingerprint
except ImportError:  # pragma: no cover - direct script import path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from background import (
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _launch_background,
        _read_exit_code,
        _utc_now,
        _write_json,
        artifact_paths,
        background_supervisor_name,
        classify_background_artifact,
        clear_artifacts,
    )
    from definitions import TierCommand
    from source_fingerprint import source_fingerprint


ROOT = Path(__file__).resolve().parents[2]
BACKGROUND_CHILD_ENTRYPOINT = ROOT / "scripts" / "run_test_tier.py"
BACKGROUND_SUPERVISOR_POLL_SECONDS = 2.0


def next_background_launch_index(
    pending: Sequence[TierCommand],
    running: Sequence[TierCommand],
) -> int | None:
    if not pending:
        return None
    if running:
        active_stage = min(command.background_stage for command in running)
    else:
        active_stage = min(command.background_stage for command in pending)
    active_resources = {
        command.background_exclusive_resource
        for command in running
        if command.background_exclusive_resource
    }
    for index, command in enumerate(pending):
        if (
            command.background_stage == active_stage
            and command.background_exclusive_resource not in active_resources
        ):
            return index
    return None


def launch_background_supervisor(
    tier: str,
    *,
    log_root: Path,
    max_parallel: int,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    clear_artifacts(paths)
    command = [
        sys.executable,
        str(BACKGROUND_CHILD_ENTRYPOINT),
        "--background-supervisor",
        "--tier",
        tier,
        "--background-dir",
        str(log_root),
        "--background-max-parallel",
        str(max_parallel),
        "--background-child-timeout-seconds",
        str(timeout_seconds),
    ]
    meta = {
        "name": name,
        "tier": tier,
        "command": command,
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "max_parallel": max_parallel,
        "timeout_seconds": timeout_seconds,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        **_hidden_process_kwargs(),
    )
    meta["status"] = "running"
    meta["launcher_pid"] = os.getpid()
    meta["child_pid"] = proc.pid
    _write_json(paths["meta"], meta)
    return {
        "name": name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def run_background_supervisor(
    tier: str,
    commands: Sequence[TierCommand],
    *,
    log_root: Path,
    max_parallel: int,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    launch_fn: Callable[..., dict[str, Any]] = _launch_background,
    fingerprint_fn: Callable[[], str] = source_fingerprint,
) -> int:
    name = background_supervisor_name(tier)
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    source_fingerprint_start = fingerprint_fn()
    meta: dict[str, Any] = {
        "name": name,
        "tier": tier,
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "max_parallel": max_parallel,
        "timeout_seconds": timeout_seconds,
        "command_count": len(commands),
        "covered_source_fingerprint_start": source_fingerprint_start,
        "covered_source_fingerprint_end": None,
        "source_fingerprint_current": None,
        "running": [],
        "completed": [],
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    pending = list(commands)
    running: list[TierCommand] = []
    completed: list[dict[str, Any]] = []
    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths[
            "err"
        ].open("w", encoding="utf-8", errors="replace") as err_file, paths["combined"].open(
            "w", encoding="utf-8", errors="replace"
        ) as combined_file:
            while pending or running:
                while pending and len(running) < max_parallel:
                    launch_index = next_background_launch_index(pending, running)
                    if launch_index is None:
                        break
                    command = pending.pop(launch_index)
                    launched = launch_fn(
                        command,
                        log_root=log_root,
                        timeout_seconds=timeout_seconds,
                        source_fingerprint_value=source_fingerprint_start,
                    )
                    running.append(command)
                    line = f"launched {command.name} pid={launched['child_pid']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()
                still_running: list[TierCommand] = []
                for command in running:
                    exit_code = _read_exit_code(artifact_paths(log_root, command.name)["exit"])
                    if exit_code is None:
                        still_running.append(command)
                        continue
                    evidence = classify_background_artifact(
                        log_root,
                        command.name,
                        command=command,
                        tier=tier,
                    )
                    result = {
                        "name": command.name,
                        "exit_code": exit_code,
                        "ok": bool(evidence["ok"]),
                        "evidence_status": evidence["status"],
                        "proof_scope": evidence["proof_scope"],
                        "reasons": evidence["reasons"],
                    }
                    completed.append(result)
                    line = f"completed {command.name} exit={exit_code} evidence={evidence['status']}\n"
                    out_file.write(line)
                    out_file.flush()
                    combined_file.write(f"[supervisor] {line}")
                    combined_file.flush()
                    if not result["ok"]:
                        err_file.write(line)
                        err_file.flush()
                running = still_running
                meta["running"] = [command.name for command in running]
                meta["completed"] = completed
                _write_json(paths["meta"], meta)
                if pending or running:
                    time.sleep(BACKGROUND_SUPERVISOR_POLL_SECONDS)
    except Exception as exc:
        details = traceback.format_exc()
        paths["err"].write_text(details, encoding="utf-8", errors="replace")
        paths["combined"].write_text(f"[supervisor-error] {details}", encoding="utf-8", errors="replace")
        paths["exit"].write_text("1\n", encoding="utf-8")
        meta.update(
            status="failed",
            end_time=_utc_now(),
            exit_code=1,
            error=str(exc),
            running=[command.name for command in running],
            completed=completed,
        )
        _write_json(paths["meta"], meta)
        return 1
    source_fingerprint_end = fingerprint_fn()
    source_fingerprint_current = source_fingerprint_start == source_fingerprint_end
    if not source_fingerprint_current:
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write("covered source changed while the background tier was running\n")
    ok = (
        all(item["ok"] for item in completed)
        and len(completed) == len(commands)
        and source_fingerprint_current
    )
    exit_code = 0 if ok else 1
    paths["exit"].write_text(f"{exit_code}\n", encoding="utf-8")
    meta.update(
        status="passed" if ok else "failed",
        end_time=_utc_now(),
        exit_code=exit_code,
        completed=completed,
        running=[],
        covered_source_fingerprint_end=source_fingerprint_end,
        source_fingerprint_current=source_fingerprint_current,
    )
    if not source_fingerprint_current:
        meta["failure_reason"] = "covered_source_changed_during_tier"
    _write_json(paths["meta"], meta)
    return exit_code
