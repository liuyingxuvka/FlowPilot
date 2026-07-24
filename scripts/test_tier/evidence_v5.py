"""Bounded current-contract artifacts for FlowPilot V5 test evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


BACKGROUND_CHILD_META_SCHEMA_VERSION = "flowpilot.background_child_meta.v2"
BACKGROUND_STREAM_INDEX_SCHEMA_VERSION = "flowpilot.background_stream_index.v1"
BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION = (
    "flowpilot.background_result_fingerprint.v2"
)
BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION = (
    "flowpilot.background_supervisor_progress.v1"
)
BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION = "flowpilot.background_supervisor_meta.v2"
BACKGROUND_OWNER_INDEX_SCHEMA_VERSION = "flowpilot.background_owner_index.v1"
COMBINED_INDEX_MAX_BYTES = 32 * 1024
FAILURE_EXCERPT_MAX_BYTES = 64 * 1024
FAILURE_EXCERPT_MAX_LINES = 200
RECENT_PROGRESS_OWNER_LIMIT = 64


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_json(value: object) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _line_count_bytes(value: bytes) -> int:
    if not value:
        return 0
    return value.count(b"\n") + (0 if value.endswith(b"\n") else 1)


def stream_descriptor(path: Path, *, path_value: str) -> dict[str, Any]:
    value = path.read_bytes()
    return {
        "path": path_value,
        "sha256": sha256_bytes(value),
        "bytes": len(value),
        "lines": _line_count_bytes(value),
    }


def background_result_fingerprint_v2(
    *,
    stdout: Mapping[str, Any],
    stderr: Mapping[str, Any],
    exit_code: int,
    status: str,
    descendant_zero_confirmed: bool,
    cleanup_reason: str,
) -> str:
    payload = {
        "schema_version": BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION,
        "stdout": {
            key: stdout[key]
            for key in ("path", "sha256", "bytes", "lines")
        },
        "stderr": {
            key: stderr[key]
            for key in ("path", "sha256", "bytes", "lines")
        },
        "exit_code": int(exit_code),
        "status": status,
        "descendant_zero_confirmed": bool(descendant_zero_confirmed),
        "cleanup_reason": cleanup_reason,
    }
    return sha256_json(payload)


def terminal_stream_index_bytes(
    *,
    name: str,
    status: str,
    exit_code: int,
    start_time: str,
    end_time: str,
    stdout: Mapping[str, Any],
    stderr: Mapping[str, Any],
    descendant_zero_confirmed: bool,
    cleanup_reason: str,
    result_fingerprint: str,
) -> bytes:
    payload = {
        "schema_version": BACKGROUND_STREAM_INDEX_SCHEMA_VERSION,
        "kind": "terminal_stream_index",
        "name": name,
        "status": status,
        "exit_code": int(exit_code),
        "start_time": start_time,
        "end_time": end_time,
        "streams": {
            "stdout": dict(stdout),
            "stderr": dict(stderr),
        },
        "cleanup": {
            "descendant_zero_confirmed": bool(descendant_zero_confirmed),
            "reason": cleanup_reason,
        },
        "result_fingerprint_schema_version": (
            BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION
        ),
        "result_fingerprint": result_fingerprint,
    }
    encoded = canonical_json_bytes(payload)
    if len(encoded) > COMBINED_INDEX_MAX_BYTES:
        raise ValueError(
            "terminal stream index exceeds "
            f"{COMBINED_INDEX_MAX_BYTES} bytes: {len(encoded)}"
        )
    return encoded


def bounded_failure_excerpt(
    streams: Sequence[tuple[str, Path]],
) -> dict[str, Any]:
    """Return a bounded tail excerpt while preserving complete stream refs."""

    candidates: list[tuple[str, str]] = []
    complete_refs: list[dict[str, Any]] = []
    total_source_lines = 0
    total_source_bytes = 0
    for stream_name, path in streams:
        if not path.is_file():
            continue
        value = path.read_bytes()
        lines = value.decode("utf-8", errors="replace").splitlines()
        total_source_lines += len(lines)
        total_source_bytes += len(value)
        complete_refs.append(
            {
                "stream": stream_name,
                "path": str(path),
                "sha256": sha256_bytes(value),
                "bytes": len(value),
                "lines": len(lines),
            }
        )
        candidates.extend((stream_name, line) for line in lines)

    selected = candidates[-FAILURE_EXCERPT_MAX_LINES:]
    while selected:
        text = "\n".join(f"[{stream}] {line}" for stream, line in selected)
        encoded = text.encode("utf-8")
        if len(encoded) <= FAILURE_EXCERPT_MAX_BYTES:
            break
        selected = selected[1:]
    else:
        text = ""
        encoded = b""
    return {
        "text": text,
        "line_count": len(selected),
        "bytes": len(encoded),
        "truncated": (
            len(selected) < total_source_lines
            or len(encoded) < total_source_bytes
        ),
        "source_line_count": total_source_lines,
        "source_bytes": total_source_bytes,
        "complete_stream_refs": complete_refs,
        "limits": {
            "lines": FAILURE_EXCERPT_MAX_LINES,
            "bytes": FAILURE_EXCERPT_MAX_BYTES,
        },
    }


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid_json:{path}:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"invalid_json_object:{path}")
    return value


def resolve_artifact_path(root: Path, path_value: str) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def path_reference(path: Path, *, root: Path) -> dict[str, Any]:
    resolved = path.resolve()
    try:
        value = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        value = str(resolved)
    return {
        "path": value,
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }


__all__ = [
    "BACKGROUND_CHILD_META_SCHEMA_VERSION",
    "BACKGROUND_OWNER_INDEX_SCHEMA_VERSION",
    "BACKGROUND_RESULT_FINGERPRINT_SCHEMA_VERSION",
    "BACKGROUND_STREAM_INDEX_SCHEMA_VERSION",
    "BACKGROUND_SUPERVISOR_PROGRESS_SCHEMA_VERSION",
    "BACKGROUND_SUPERVISOR_META_SCHEMA_VERSION",
    "COMBINED_INDEX_MAX_BYTES",
    "FAILURE_EXCERPT_MAX_BYTES",
    "FAILURE_EXCERPT_MAX_LINES",
    "RECENT_PROGRESS_OWNER_LIMIT",
    "background_result_fingerprint_v2",
    "bounded_failure_excerpt",
    "canonical_json_bytes",
    "load_json_object",
    "path_reference",
    "resolve_artifact_path",
    "sha256_bytes",
    "sha256_file",
    "sha256_json",
    "stream_descriptor",
    "terminal_stream_index_bytes",
]
