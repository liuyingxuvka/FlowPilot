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
    from .evidence_v5 import (
        BACKGROUND_CHILD_META_SCHEMA_VERSION,
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION,
        COMBINED_INDEX_MAX_BYTES,
        background_result_fingerprint_v2,
        load_json_object,
        path_reference,
        sha256_file,
        sha256_json,
        stream_descriptor,
        terminal_stream_index_bytes,
    )
    from .impact_resolution import IMPACT_PLAN_SCHEMA_VERSION
    from .source_fingerprint import file_fingerprint, fingerprint_set
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
    from evidence_v5 import (
        BACKGROUND_CHILD_META_SCHEMA_VERSION,
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION,
        COMBINED_INDEX_MAX_BYTES,
        background_result_fingerprint_v2,
        load_json_object,
        path_reference,
        sha256_file,
        sha256_json,
        stream_descriptor,
        terminal_stream_index_bytes,
    )
    from impact_resolution import IMPACT_PLAN_SCHEMA_VERSION
    from source_fingerprint import file_fingerprint, fingerprint_set


ROOT = Path(__file__).resolve().parents[2]
DESCENDANT_SETTLEMENT_GRACE_SECONDS = 15.0


def _publish_exit(path: Path, content: bytes) -> None:
    staging = path.with_name(path.name + ".tmp")
    staging.write_bytes(content)
    staging.replace(path)


def _publish_bytes(path: Path, content: bytes) -> None:
    staging = path.with_name(path.name + ".tmp")
    staging.write_bytes(content)
    staging.replace(path)


def _artifact_path_value(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def _impact_plan_owner_identity(
    *,
    impact_plan_path: Path,
    impact_plan_sha256: str,
    owner_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = impact_plan_path.resolve()
    if not resolved.is_file():
        raise ValueError("impact_plan_missing")
    actual_sha256 = sha256_file(resolved)
    if actual_sha256 != impact_plan_sha256:
        raise ValueError("impact_plan_sha256_mismatch")
    plan = load_json_object(resolved)
    if plan.get("schema_version") != IMPACT_PLAN_SCHEMA_VERSION:
        raise ValueError("impact_plan_not_current")
    decisions = [
        row
        for row in plan.get("decisions") or ()
        if isinstance(row, dict) and row.get("owner_id") == owner_id
    ]
    if len(decisions) != 1:
        raise ValueError("impact_plan_owner_lookup_not_exact")
    decision = decisions[0]
    if decision.get("action") != "execute":
        raise ValueError("impact_plan_owner_not_executable")
    identity = decision.get("identity")
    if not isinstance(identity, dict):
        raise ValueError("impact_plan_owner_identity_missing")
    return plan, dict(identity)


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
    target: Any,
    flags: dict[str, bool],
) -> None:
    for line in iter(pipe.readline, ""):
        target.write(line)
        target.flush()
        if "proof_reused" in line or "proof reused" in line.lower():
            flags["proof_reused"] = True
    pipe.close()


def run_background_child(
    name: str,
    command: Sequence[str],
    *,
    log_root: Path,
    impact_plan_path: Path,
    impact_plan_sha256: str,
    owner_id: str,
    timeout_seconds: int = DEFAULT_BACKGROUND_CHILD_TIMEOUT_SECONDS,
) -> int:
    paths = artifact_paths(log_root, name)
    log_root.mkdir(parents=True, exist_ok=True)
    if name != owner_id:
        raise ValueError("background child name must equal owner id")
    impact_plan, owner_identity_value = _impact_plan_owner_identity(
        impact_plan_path=impact_plan_path,
        impact_plan_sha256=impact_plan_sha256,
        owner_id=owner_id,
    )
    impact_plan_id = str(impact_plan.get("plan_id") or "")
    if not impact_plan_id:
        raise ValueError("impact_plan_id_missing")
    expected_inputs = owner_identity_value.get("covered_input_fingerprints")
    if not isinstance(expected_inputs, dict):
        raise ValueError("impact_plan owner covered_input_fingerprints are required")

    def current_input_fingerprints() -> dict[str, str]:
        values: dict[str, str] = {}
        for relative in sorted(expected_inputs):
            path = ROOT / str(relative)
            values[str(relative)] = file_fingerprint(path)
        return values

    inputs_start = current_input_fingerprints()
    inputs_current_at_start = inputs_start == expected_inputs
    meta: dict[str, Any] = {
        "schema_version": BACKGROUND_CHILD_META_SCHEMA_VERSION,
        "name": name,
        "owner_id": owner_id,
        "command": list(command),
        "cwd": str(ROOT),
        "status": "running",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": False,
        "timeout_seconds": timeout_seconds,
        "timed_out": False,
        "impact_plan_ref": {
            **path_reference(impact_plan_path, root=ROOT),
            "plan_id": impact_plan_id,
            "owner_id": owner_id,
        },
        "owner_identity_sha256": sha256_json(owner_identity_value),
        "covered_input_fingerprint_start": fingerprint_set(inputs_start),
        "covered_input_fingerprint_end": None,
        "inputs_current": inputs_current_at_start,
        "process_launch_plan": None,
        "process_identity": None,
        "observed_descendant_count": 0,
        "observed_descendant_identities": [],
        "remaining_identity_details_before_cleanup": [],
        "cleanup_proof": None,
        "descendant_zero_confirmed": False,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    returncode = 1
    owner_process_identity: dict[str, Any] | None = None
    if not inputs_current_at_start:
        paths["err"].write_text(
            "owner inputs changed before execution started\n",
            encoding="utf-8",
        )
        paths["out"].write_text("", encoding="utf-8")
        meta.update(
            status="failed",
            exit_code=1,
            failure_reason="owner_inputs_changed_before_command",
            cleanup_proof={
                "cleanup_confirmed": True,
                "descendant_zero_confirmed": True,
                "reason": "command_not_started",
                "remaining_identities": [],
            },
            descendant_zero_confirmed=True,
        )
        flags = {"proof_reused": False}
    else:
        flags = {"proof_reused": False}
        try:
            with paths["out"].open(
                "w", encoding="utf-8", errors="replace"
            ) as out_file, paths["err"].open(
                "w", encoding="utf-8", errors="replace"
            ) as err_file:
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
                owner_process_identity = _process_identity(process.pid)
                if owner_process_identity is None:
                    raise RuntimeError(
                        "background child process identity could not be established"
                    )
                meta["process_identity"] = owner_process_identity
                _write_json(paths["meta"], meta)
                assert process.stdout is not None
                assert process.stderr is not None
                out_thread = threading.Thread(
                    target=_stream_pipe,
                    args=(process.stdout, out_file, flags),
                    daemon=True,
                )
                err_thread = threading.Thread(
                    target=_stream_pipe,
                    args=(process.stderr, err_file, flags),
                    daemon=True,
                )
                out_thread.start()
                err_thread.start()
                deadline = (
                    time.monotonic() + timeout_seconds if timeout_seconds else None
                )
                observed_descendants: dict[tuple[int, str], dict[str, Any]] = {}
                while process.poll() is None:
                    for descendant in _process_descendant_identities(
                        owner_process_identity
                    ):
                        key = (
                            int(descendant["pid"]),
                            str(descendant["start_token"]),
                        )
                        observed_descendants[key] = descendant
                    if deadline is not None and time.monotonic() >= deadline:
                        meta["timed_out"] = True
                        err_file.write(
                            "background child timed out after "
                            f"{timeout_seconds} seconds\n"
                        )
                        err_file.flush()
                        break
                    time.sleep(0.05)
                observed_values = list(observed_descendants.values())
                meta["observed_descendant_count"] = len(observed_values)
                meta["observed_descendant_identities"] = observed_values[:64]
                if meta["timed_out"]:
                    cleanup = _terminate_process_tree(owner_process_identity)
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
                        observed_values
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
                            _describe_live_identities(remaining)[:64]
                        )
                        _write_json(paths["meta"], meta)
                        cleanup_attempts = [
                            _terminate_process_tree(identity)
                            for identity in remaining
                        ]
                        remaining = _live_process_identities(remaining)
                        cleanup = {
                            "cleanup_confirmed": not remaining,
                            "descendant_zero_confirmed": not remaining,
                            "reason": (
                                "orphan_descendants_terminated"
                                if not remaining
                                else "cleanup_unconfirmed"
                            ),
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
        except Exception as exc:  # pragma: no cover - defensive reporting
            if owner_process_identity is not None:
                cleanup = _terminate_process_tree(owner_process_identity)
                meta["cleanup_proof"] = cleanup
                meta["descendant_zero_confirmed"] = (
                    cleanup.get("cleanup_confirmed") is True
                    and cleanup.get("descendant_zero_confirmed") is True
                )
            else:
                meta["cleanup_proof"] = {
                    "cleanup_confirmed": True,
                    "descendant_zero_confirmed": True,
                    "reason": "command_not_started",
                    "remaining_identities": [],
                }
                meta["descendant_zero_confirmed"] = True
            with paths["err"].open(
                "a", encoding="utf-8", errors="replace"
            ) as err_file:
                err_file.write(
                    f"background child failed before command exit: {exc}\n"
                )
            if not paths["out"].exists():
                paths["out"].write_text("", encoding="utf-8")
            returncode = 1
    inputs_end = current_input_fingerprints()
    inputs_current = inputs_end == expected_inputs
    if returncode == 0 and not inputs_current:
        returncode = 1
        message = "covered owner input changed while the background child was running\n"
        with paths["err"].open("a", encoding="utf-8", errors="replace") as err_file:
            err_file.write(message)
    exit_bytes = f"{returncode}\n".encode("utf-8")
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
    meta["covered_input_fingerprint_end"] = fingerprint_set(inputs_end)
    meta["inputs_current"] = inputs_current
    stdout = stream_descriptor(
        paths["out"],
        path_value=_artifact_path_value(paths["out"]),
    )
    stderr = stream_descriptor(
        paths["err"],
        path_value=_artifact_path_value(paths["err"]),
    )
    cleanup_reason = str((meta.get("cleanup_proof") or {}).get("reason") or "")
    result_fingerprint = background_result_fingerprint_v2(
        stdout=stdout,
        stderr=stderr,
        exit_code=returncode,
        status=str(meta["status"]),
        descendant_zero_confirmed=meta.get("descendant_zero_confirmed") is True,
        cleanup_reason=cleanup_reason,
    )
    combined_bytes = terminal_stream_index_bytes(
        name=name,
        status=str(meta["status"]),
        exit_code=returncode,
        start_time=str(meta["start_time"]),
        end_time=str(meta["end_time"]),
        stdout=stdout,
        stderr=stderr,
        descendant_zero_confirmed=meta.get("descendant_zero_confirmed") is True,
        cleanup_reason=cleanup_reason,
        result_fingerprint=result_fingerprint,
    )
    _publish_bytes(paths["combined"], combined_bytes)
    combined_ref = path_reference(paths["combined"], root=ROOT)
    meta["stream_artifacts"] = {
        "stdout": stdout,
        "stderr": stderr,
    }
    meta["combined_artifact"] = {
        **combined_ref,
        "kind": "terminal_stream_index",
        "max_bytes": COMBINED_INDEX_MAX_BYTES,
    }
    meta["combined_kind"] = "terminal_stream_index"
    meta["result_fingerprint_schema_version"] = (
        BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION
    )
    meta["result_fingerprint"] = result_fingerprint
    if meta["timed_out"]:
        meta["failure_reason"] = (
            "background_child_timeout"
            if meta.get("descendant_zero_confirmed")
            else "background_child_timeout_cleanup_unconfirmed"
        )
    elif meta.get("process_identity") and not meta.get("descendant_zero_confirmed"):
        meta["failure_reason"] = "background_child_cleanup_unconfirmed"
    elif not inputs_current:
        meta["failure_reason"] = "owner_inputs_changed_during_command"
    _write_json(paths["meta"], meta)
    _publish_exit(paths["exit"], exit_bytes)
    return returncode
