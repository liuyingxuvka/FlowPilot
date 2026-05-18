"""Background artifact and plan helpers for scripts.run_test_tier."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    from .definitions import TierCommand, commands_for_tier
except ImportError:  # pragma: no cover - script execution path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from definitions import TierCommand, commands_for_tier


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_SUFFIXES = ("out", "err", "combined", "exit", "meta")
BACKGROUND_CHILD_ENTRYPOINT = ROOT / "scripts" / "run_test_tier.py"

def _safe_base(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("._")
    return safe or "test_tier_command"


def artifact_paths(log_root: Path, name: str) -> dict[str, Path]:
    base = _safe_base(name)
    return {suffix: log_root / f"{base}.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"} | {
        "meta": log_root / f"{base}.meta.json"
    }


def clear_artifacts(paths: dict[str, Path]) -> None:
    for path in paths.values():
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except PermissionError as exc:
            raise RuntimeError(
                f"background artifact is still locked by an active process: {path}"
            ) from exc


def background_supervisor_name(tier: str) -> str:
    return f"{tier}_background_supervisor"


def should_use_background_supervisor(command_count: int, max_parallel: int) -> bool:
    return max_parallel > 0 and command_count > max_parallel


def _artifact_paths_for_json(log_root: Path, name: str) -> dict[str, str]:
    return {
        key: str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
        for key, path in artifact_paths(log_root, name).items()
    }


def command_to_json(command: TierCommand, *, background_dir: Path) -> dict[str, Any]:
    return {
        "name": command.name,
        "command": list(command.command),
        "description": command.description,
        "long_running": command.long_running,
        "release_only": command.release_only,
        "background_recommended": command.background_recommended,
        "background_stage": command.background_stage,
        "background_artifacts": _artifact_paths_for_json(background_dir, command.name),
    }


def plan_for_tier(tier: str, *, background_dir: Path) -> dict[str, Any]:
    commands = commands_for_tier(tier)
    return {
        "tier": tier,
        "command_count": len(commands),
        "commands": [command_to_json(command, background_dir=background_dir) for command in commands],
        "background_dir": str(
            background_dir.relative_to(ROOT) if background_dir.is_relative_to(ROOT) else background_dir
        ),
        "background_contract": [f"<name>.{suffix}.txt" for suffix in ARTIFACT_SUFFIXES if suffix != "meta"]
        + ["<name>.meta.json"],
        "release_obligation_visible": tier not in {"release", "legacy-full"},
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: MappingLike) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


MappingLike = dict[str, Any]


def _windows_hidden_process_flags() -> int:
    if os.name != "nt":
        return 0
    return (
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )


def _windows_hidden_startupinfo() -> Any | None:
    if os.name != "nt":
        return None
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    return startupinfo


def _hidden_process_kwargs() -> dict[str, Any]:
    if os.name != "nt":
        return {}
    return {
        "creationflags": _windows_hidden_process_flags(),
        "startupinfo": _windows_hidden_startupinfo(),
    }


def _launch_background(command: TierCommand, *, log_root: Path) -> dict[str, Any]:
    log_root.mkdir(parents=True, exist_ok=True)
    paths = artifact_paths(log_root, command.name)
    clear_artifacts(paths)
    meta = {
        "name": command.name,
        "command": list(command.command),
        "cwd": str(ROOT),
        "status": "launching",
        "start_time": _utc_now(),
        "end_time": None,
        "exit_code": None,
        "proof_reused": None,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }
    _write_json(paths["meta"], meta)
    child_args = [
        sys.executable,
        str(BACKGROUND_CHILD_ENTRYPOINT),
        "--background-child",
        "--name",
        command.name,
        "--command-json",
        json.dumps(list(command.command)),
        "--background-dir",
        str(log_root),
    ]
    proc = subprocess.Popen(
        child_args,
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
        "name": command.name,
        "status": "running",
        "child_pid": proc.pid,
        "artifacts": {key: str(value) for key, value in paths.items()},
    }


def launch_background(commands: Iterable[TierCommand], *, log_root: Path) -> list[dict[str, Any]]:
    return [_launch_background(command, log_root=log_root) for command in commands]


def _read_exit_code(path: Path) -> int | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return 1


def _read_background_meta(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing_meta"
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid_meta:{type(exc).__name__}"
    if not isinstance(payload, dict):
        return None, "invalid_meta:not_object"
    return payload, None


def _artifact_has_progress(paths: MappingLike) -> bool:
    for key in ("out", "err", "combined"):
        path = paths.get(key)
        if not isinstance(path, Path) or not path.exists():
            continue
        try:
            if path.read_text(encoding="utf-8", errors="replace").strip():
                return True
        except OSError:
            continue
    return False


def _release_local_only_proof(
    *,
    command: TierCommand | None,
    tier: str,
    meta: MappingLike | None,
) -> bool:
    command_parts: list[str] = []
    if command is not None:
        command_parts.extend(command.command)
    if isinstance(meta, dict):
        meta_command = meta.get("command")
        if isinstance(meta_command, list):
            command_parts.extend(str(part) for part in meta_command)
        if meta.get("proof_scope") == "local_only" or meta.get("local_only") is True:
            return True
    command_text = " ".join(command_parts)
    return bool(
        "--skip-url-check" in command_parts
        or "--skip-url-check" in command_text
    )


def classify_background_artifact(
    log_root: Path,
    name: str,
    *,
    command: TierCommand | None = None,
    tier: str = "",
) -> dict[str, Any]:
    paths = artifact_paths(log_root, name)
    meta, meta_error = _read_background_meta(paths["meta"])
    exit_code = _read_exit_code(paths["exit"])
    progress_seen = _artifact_has_progress(paths)
    reasons: list[str] = []
    raw_status = str((meta or {}).get("status") or "")

    if meta_error:
        reasons.append(meta_error)
    if exit_code is None:
        reasons.append("missing_exit")

    if meta is not None and raw_status == "running" and exit_code is None:
        status = "running"
    elif exit_code is None and progress_seen:
        status = "progress_only"
    elif exit_code is None:
        status = "incomplete"
    elif exit_code != 0 or raw_status == "failed":
        status = "failed"
        if meta is not None and raw_status == "running":
            reasons.append("running_meta_with_exit_artifact")
    elif meta is not None and raw_status == "running":
        status = "passed"
        reasons.append("exit_zero_won_meta_update_race")
    elif meta is None:
        status = "incomplete"
    elif raw_status in {"passed", "pass"}:
        status = "passed"
    else:
        status = "incomplete"
        reasons.append(f"unexpected_meta_status:{raw_status or 'missing'}")

    local_only = _release_local_only_proof(command=command, tier=tier, meta=meta)
    if status == "passed" and local_only:
        status = "release_local_only"
        reasons.append("release_url_check_skipped_or_release_only_tier")

    return {
        "name": name,
        "status": status,
        "execution_status": "passed" if status in {"passed", "release_local_only"} else status,
        "ok": status in {"passed", "release_local_only"},
        "exit_code": exit_code,
        "meta_status": raw_status or None,
        "progress_seen": progress_seen,
        "proof_scope": "local_only" if local_only else "full",
        "reasons": reasons,
        "artifacts": {key: str(path) for key, path in paths.items()},
    }
