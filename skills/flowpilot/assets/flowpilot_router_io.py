"""Low-level time, path, and runtime JSON helpers for the FlowPilot router."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from flowpilot_router_errors import RouterError, RouterLedgerCorruptionError, RouterLedgerWriteInProgress


RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS = 5.0
RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS = 30.0
RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS = 0.02


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_kit_source() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit"


def _copy_runtime_kit_into_run_root(run_root: Path) -> None:
    source = runtime_kit_source()
    target = run_root / "runtime_kit"
    try:
        target.resolve().relative_to(run_root.resolve())
    except ValueError as exc:
        raise RouterError(f"runtime kit target outside run root: {target}") from exc
    if target.name != "runtime_kit":
        raise RouterError(f"refusing to replace unexpected runtime kit target: {target}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))


def legacy_bootstrap_state_path(project_root: Path) -> Path:
    return project_root / ".flowpilot" / "bootstrap" / "startup_state.json"


def run_bootstrap_state_path(run_root: Path) -> Path:
    return run_root / "bootstrap" / "startup_state.json"


def bootstrap_state_path(project_root: Path, state: dict[str, Any] | None = None) -> Path:
    if state and state.get("run_root"):
        return run_bootstrap_state_path(project_root / str(state["run_root"]))
    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    if raw:
        return project_root / str(raw)
    raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_root:
        candidate = run_bootstrap_state_path(project_root / str(raw_root))
        if candidate.exists():
            return candidate
    return legacy_bootstrap_state_path(project_root)


def _json_write_lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".write.lock")


def _json_write_lock_liveness(path: Path) -> dict[str, Any]:
    lock_path = _json_write_lock_path(path)
    if not lock_path.exists():
        return {
            "exists": False,
            "fresh": False,
            "stale": False,
            "path": str(lock_path),
            "age_seconds": None,
        }
    try:
        age = time.time() - lock_path.stat().st_mtime
    except OSError:
        age = None
    fresh = age is not None and age <= RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS
    return {
        "exists": True,
        "fresh": bool(fresh),
        "stale": bool(age is not None and not fresh),
        "path": str(lock_path),
        "age_seconds": age,
        "stale_after_seconds": RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS,
    }


def _raise_if_runtime_write_active(path: Path) -> None:
    write_lock = _json_write_lock_liveness(path)
    if write_lock["fresh"]:
        raise RouterLedgerWriteInProgress(path, write_lock, "fresh runtime JSON write lock")


def _wait_for_runtime_json_writer_to_settle(exc: RouterLedgerWriteInProgress) -> dict[str, Any]:
    path = exc.path
    lock_path = _json_write_lock_path(path)
    started = time.monotonic()
    poll_count = 0
    last_liveness = dict(exc.write_lock)
    while True:
        liveness = _json_write_lock_liveness(path)
        last_liveness = liveness
        if not liveness.get("fresh"):
            return {
                "path": str(path),
                "lock_path": str(lock_path),
                "waited_seconds": max(0.0, time.monotonic() - started),
                "poll_count": poll_count,
                "final_liveness": last_liveness,
            }
        poll_count += 1
        time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)


def _run_foreground_with_runtime_writer_settlement(
    operation: Callable[[], dict[str, Any]],
    *,
    command_name: str,
) -> dict[str, Any]:
    waits: list[dict[str, Any]] = []
    while True:
        try:
            result = operation()
            break
        except RouterLedgerWriteInProgress as exc:
            waits.append(_wait_for_runtime_json_writer_to_settle(exc))
    if waits:
        result = dict(result)
        result["runtime_write_settlement"] = {
            "waited": True,
            "command": command_name,
            "wait_count": len(waits),
            "waits": waits,
        }
    return result


def _is_transient_runtime_json_scan_artifact(path: Path) -> bool:
    return path.name.startswith(".tmp-") or path.name.endswith(".write.lock")


def _read_json_for_runtime_scan(path: Path) -> dict[str, Any] | None:
    if _is_transient_runtime_json_scan_artifact(path):
        return None
    try:
        _raise_if_runtime_write_active(path)
        return read_json_if_exists(path)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = _json_write_lock_liveness(path)
        if write_lock["fresh"]:
            raise RouterLedgerWriteInProgress(path, write_lock, str(exc)) from exc
        raise


def _acquire_json_write_lock(path: Path) -> Path:
    lock_path = _json_write_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
    while True:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except OSError:
                age = 0.0
            if age > RUNTIME_JSON_WRITE_LOCK_STALE_SECONDS:
                try:
                    lock_path.unlink()
                except OSError:
                    pass
                continue
            if time.monotonic() >= deadline:
                raise RouterError(f"timed out waiting for JSON write lock: {path}")
            time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "schema_version": "flowpilot.runtime_json_write_lock.v1",
                        "path": str(path),
                        "pid": os.getpid(),
                        "created_at": utc_now(),
                    },
                    sort_keys=True,
                )
                + "\n"
            )
        return lock_path


def write_json_atomic(path: Path, payload: dict[str, Any], *, sort_keys: bool = True, verify: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _acquire_json_write_lock(path)
    tmp_path = path.with_name(f".tmp-{os.getpid()}-{time.time_ns():x}.json")
    try:
        body = json.dumps(payload, indent=2, sort_keys=sort_keys) + "\n"
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        deadline = time.monotonic() + RUNTIME_JSON_WRITE_LOCK_TIMEOUT_SECONDS
        while True:
            try:
                os.replace(tmp_path, path)
                break
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(RUNTIME_JSON_WRITE_LOCK_POLL_SECONDS)
        if verify:
            read_json(path)
    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        try:
            lock_path.unlink()
        except OSError:
            pass


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_json_atomic(path, payload, sort_keys=True, verify=True)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RouterError(f"expected JSON object: {path}")
    return payload


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return read_json(path)


def read_daemon_critical_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError) as exc:
        write_lock = _json_write_lock_liveness(path)
        if write_lock["fresh"]:
            raise RouterLedgerWriteInProgress(path, write_lock, str(exc)) from exc
        raise RouterLedgerCorruptionError(path, str(exc)) from exc


def read_json_if_valid(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, RouterError):
        return {}


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def _without_role_output_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return body


def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _json_sha256(_without_role_output_envelope(raw))


def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(raw, dict):
        return set()
    body = _without_role_output_envelope(raw)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}


def _role_output_hashes(path: Path) -> tuple[str, str | None]:
    raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return raw_hash, _role_output_semantic_hash(path)


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RouterError(f"path is outside project root: {path}") from exc


def _project_root_from_run_root(run_root: Path) -> Path:
    resolved = run_root.resolve()
    if resolved.parent.name == "runs" and resolved.parent.parent.name == ".flowpilot":
        return resolved.parent.parent.parent
    return resolved.parent


def _flowpilot_runtime_entrypoint_ref(project_root: Path) -> str:
    runtime_path = Path(__file__).resolve().with_name("flowpilot_runtime.py")
    try:
        return project_relative(project_root, runtime_path)
    except RouterError:
        return str(runtime_path)
