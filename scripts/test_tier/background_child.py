"""Exact-identity background command execution for the test-tier facade."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Sequence

try:
    from .background import (
        BACKGROUND_CHILD_TIMEOUT_EXIT_CODE,
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _process_descendant_identities,
        _process_identity,
        _process_identity_is_live,
        _resolve_current_python_process_launch,
        _terminate_process_tree,
        _utc_now,
        _write_json,
        artifact_paths,
    )
    from .source_fingerprint import source_fingerprint
except ImportError:  # pragma: no cover - direct script import path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from background import (
        BACKGROUND_CHILD_TIMEOUT_EXIT_CODE,
        DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
        _hidden_process_kwargs,
        _process_descendant_identities,
        _process_identity,
        _process_identity_is_live,
        _resolve_current_python_process_launch,
        _terminate_process_tree,
        _utc_now,
        _write_json,
        artifact_paths,
    )
    from source_fingerprint import source_fingerprint


ROOT = Path(__file__).resolve().parents[2]
DESCENDANT_SETTLEMENT_GRACE_SECONDS = 15.0


def _describe_live_identities(
    identities: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    if sys.platform != "win32" or not identities:
        return []
    pids = sorted({int(identity["pid"]) for identity in identities})
    pid_literal = ",".join(str(pid) for pid in pids)
    script = (
        f"$ids=@({pid_literal});"
        "Get-CimInstance Win32_Process | "
        "Where-Object { $ids -contains [int]$_.ProcessId } | "
        "Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | "
        "ConvertTo-Json -Compress"
    )
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            **_hidden_process_kwargs(),
        )
        if completed.returncode != 0 or not completed.stdout.strip():
            return []
        payload = json.loads(completed.stdout)
        rows = payload if isinstance(payload, list) else [payload]
        return [row for row in rows if isinstance(row, dict)]
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def _live_process_identities(
    identities: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [identity for identity in identities if _process_identity_is_live(identity)]


def _wait_for_exact_descendants_to_settle(
    identities: Sequence[dict[str, Any]],
    *,
    grace_seconds: float = DESCENDANT_SETTLEMENT_GRACE_SECONDS,
) -> list[dict[str, Any]]:
    """Return exact descendants still live after one bounded settlement window."""

    remaining = _live_process_identities(identities)
    deadline = time.monotonic() + max(0.0, grace_seconds)
    while remaining and time.monotonic() < deadline:
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        remaining = _live_process_identities(remaining)
    return remaining


def _stream_pipe(
    pipe: Any,
    stream_name: str,
    target: Any,
    combined: Any,
    lock: threading.Lock,
    flags: dict[str, bool],
) -> None:
    for line in iter(pipe.readline, ""):
        target.write(line)
        target.flush()
        if "proof_reused" in line or "proof reused" in line.lower():
            flags["proof_reused"] = True
        with lock:
            combined.write(f"[{stream_name}] {line}")
            combined.flush()
    pipe.close()


def run_background_child(
    name: str,
    command: Sequence[str],
    *,
    log_root: Path,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
    source_fingerprint_value: str | None = None,
    fingerprint_fn: Callable[[], str] = source_fingerprint,
) -> int:
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    covered_source = source_fingerprint_value or fingerprint_fn()
    meta = {
        "name": name,
        "command": list(command),
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "timeout_seconds": timeout_seconds,
        "timed_out": False,
        "covered_source_fingerprint": covered_source,
        "covered_source_fingerprint_start": covered_source,
        "covered_source_fingerprint_end": None,
        "source_fingerprint_current": None,
        "process_launch_plan": None,
        "process_identity": None,
        "observed_descendant_identities": [],
        "remaining_identity_details_before_cleanup": [],
        "cleanup_proof": None,
        "descendant_zero_confirmed": False,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    flags = {"proof_reused": False}
    try:
        with paths["out"].open("w", encoding="utf-8", errors="replace") as out_file, paths[
            "err"
        ].open("w", encoding="utf-8", errors="replace") as err_file, paths["combined"].open(
            "w", encoding="utf-8", errors="replace"
        ) as combined_file:
            process_command, process_env, process_launch_plan = (
                _resolve_current_python_process_launch(command)
            )
            meta["process_launch_plan"] = process_launch_plan
            _write_json(paths["meta"], meta)
            process = subprocess.Popen(
                process_command,
                cwd=ROOT,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                **_hidden_process_kwargs(),
            )
            owner_identity = _process_identity(process.pid)
            if owner_identity is None:
                raise RuntimeError("background child process identity could not be established")
            meta["process_identity"] = owner_identity
            _write_json(paths["meta"], meta)
            assert process.stdout is not None
            assert process.stderr is not None
            lock = threading.Lock()
            out_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stdout, "stdout", out_file, combined_file, lock, flags),
                daemon=True,
            )
            err_thread = threading.Thread(
                target=_stream_pipe,
                args=(process.stderr, "stderr", err_file, combined_file, lock, flags),
                daemon=True,
            )
            out_thread.start()
            err_thread.start()
            deadline = time.monotonic() + timeout_seconds if timeout_seconds else None
            observed_descendants: dict[tuple[int, str], dict[str, Any]] = {}
            while process.poll() is None:
                for descendant in _process_descendant_identities(owner_identity):
                    key = (int(descendant["pid"]), str(descendant["start_token"]))
                    observed_descendants[key] = descendant
                if deadline is not None and time.monotonic() >= deadline:
                    meta["timed_out"] = True
                    combined_file.write(
                        f"[runner] timed out after {timeout_seconds} seconds; terminating exact process tree\n"
                    )
                    combined_file.flush()
                    err_file.write(f"background child timed out after {timeout_seconds} seconds\n")
                    err_file.flush()
                    break
                time.sleep(0.05)
            meta["observed_descendant_identities"] = list(observed_descendants.values())
            if meta["timed_out"]:
                cleanup = _terminate_process_tree(owner_identity)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    cleanup = {
                        **cleanup,
                        "cleanup_confirmed": False,
                        "descendant_zero_confirmed": False,
                        "reason": "cleanup_unconfirmed",
                    }
                returncode = BACKGROUND_CHILD_TIMEOUT_EXIT_CODE
            else:
                returncode = int(process.returncode or 0)
                remaining_at_owner_exit = _live_process_identities(
                    list(observed_descendants.values())
                )
                remaining = _wait_for_exact_descendants_to_settle(
                    remaining_at_owner_exit
                )
                cleanup = {
                    "cleanup_confirmed": not remaining,
                    "descendant_zero_confirmed": not remaining,
                    "reason": (
                        "process_tree_exited_after_bounded_settlement"
                        if remaining_at_owner_exit and not remaining
                        else (
                            "process_tree_exited"
                            if not remaining
                            else "cleanup_unconfirmed"
                        )
                    ),
                    "remaining_identities": remaining,
                }
                if remaining:
                    meta["remaining_identity_details_before_cleanup"] = (
                        _describe_live_identities(remaining)
                    )
                    _write_json(paths["meta"], meta)
                    cleanup_attempts = [_terminate_process_tree(identity) for identity in remaining]
                    remaining = _live_process_identities(remaining)
                    cleanup = {
                        "cleanup_confirmed": not remaining,
                        "descendant_zero_confirmed": not remaining,
                        "reason": "orphan_descendants_terminated" if not remaining else "cleanup_unconfirmed",
                        "remaining_identities": remaining,
                        "cleanup_attempts": cleanup_attempts,
                    }
                    if returncode == 0:
                        returncode = 1
            meta["cleanup_proof"] = cleanup
            meta["descendant_zero_confirmed"] = (
                cleanup.get("cleanup_confirmed") is True
                and cleanup.get("descendant_zero_confirmed") is True
            )
            if not meta["descendant_zero_confirmed"]:
                returncode = 1
            out_thread.join(timeout=5)
            err_thread.join(timeout=5)
    except Exception as exc:  # pragma: no cover - defensive background reporting
        paths["err"].write_text(f"background child failed before command exit: {exc}\n", encoding="utf-8")
        paths["combined"].write_text(
            f"[runner] background child failed before command exit: {exc}\n",
            encoding="utf-8",
        )
        returncode = 1
    covered_source_end = fingerprint_fn()
    source_current = covered_source == covered_source_end
    if returncode == 0 and not source_current:
        returncode = 1
        message = "covered source changed while the background child was running\n"
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write(message)
        with paths["combined"].open("a", encoding="utf-8", errors="replace") as combined_file:
            combined_file.write(f"[runner] {message}")
    paths["exit"].write_text(f"{returncode}\n", encoding="utf-8")
    meta["status"] = (
        "passed"
        if returncode == 0
        else (
            "cleanup-unconfirmed"
            if meta.get("process_identity") and not meta.get("descendant_zero_confirmed")
            else "failed"
        )
    )
    meta["end_time"] = _utc_now()
    meta["exit_code"] = returncode
    meta["proof_reused"] = flags["proof_reused"]
    meta["covered_source_fingerprint_end"] = covered_source_end
    meta["source_fingerprint_current"] = source_current
    if meta["timed_out"]:
        meta["failure_reason"] = (
            "background_child_timeout"
            if meta.get("descendant_zero_confirmed")
            else "background_child_timeout_cleanup_unconfirmed"
        )
    elif meta.get("process_identity") and not meta.get("descendant_zero_confirmed"):
        meta["failure_reason"] = "background_child_cleanup_unconfirmed"
    elif not source_current:
        meta["failure_reason"] = "covered_source_changed_during_command"
    _write_json(paths["meta"], meta)
    return returncode
