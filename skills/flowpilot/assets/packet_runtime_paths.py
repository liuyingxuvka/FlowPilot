"""Path, envelope loading, and hash verification helpers for packet runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packet_runtime_schema import (
    PacketRuntimeError,
    sha256_file,
    validate_packet_id,
)


UNSUPPORTED_CURRENT_RUN_POINTER_FIELDS = (
    "current_run_id",
    "current_run_root",
    "active_run_id",
    "active_run_root",
)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PacketRuntimeError(f"JSON root must be an object: {path}")
    return payload


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise PacketRuntimeError(f"path is outside project root: {path}") from exc


def resolve_project_path(project_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root.resolve() / path


def read_json_if_exists(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return payload if isinstance(payload, dict) else {}


def active_run_root(project_root: Path, run_id: str | None = None) -> tuple[str, Path]:
    root = project_root.resolve()
    if run_id:
        return run_id, root / ".flowpilot" / "runs" / run_id
    flowpilot_root = root / ".flowpilot"
    current = read_json_if_exists(flowpilot_root / "current.json")
    unsupported_pointer_keys = [
        key for key in UNSUPPORTED_CURRENT_RUN_POINTER_FIELDS if current.get(key)
    ]
    if unsupported_pointer_keys:
        raise PacketRuntimeError(
            "packet runtime current pointer uses unsupported fields: "
            + ", ".join(unsupported_pointer_keys)
        )
    resolved_run_id = current.get("run_id")
    raw_run_root = current.get("run_root")
    if not resolved_run_id or not isinstance(resolved_run_id, str):
        raise PacketRuntimeError("packet runtime requires current pointer run_id")
    if not raw_run_root:
        raise PacketRuntimeError("packet runtime requires current pointer run_root")
    run_root = Path(str(raw_run_root))
    if not run_root.is_absolute():
        run_root = root / run_root
    try:
        run_root.resolve().relative_to((flowpilot_root / "runs").resolve())
    except ValueError as exc:
        raise PacketRuntimeError(f"packet runtime run_root is outside .flowpilot/runs: {run_root}") from exc
    if run_root.name != resolved_run_id:
        raise PacketRuntimeError(
            f"packet runtime current pointer run_id does not match run_root name: {resolved_run_id} != {run_root.name}"
        )
    return resolved_run_id, run_root


def packet_paths(project_root: Path, packet_id: str, run_id: str | None = None) -> dict[str, Any]:
    validate_packet_id(packet_id)
    resolved_run_id, run_root = active_run_root(project_root, run_id)
    packet_dir = run_root / "packets" / packet_id
    return {
        "run_id": resolved_run_id,
        "run_root": run_root,
        "packet_dir": packet_dir,
        "packet_envelope": packet_dir / "packet_envelope.json",
        "packet_body": packet_dir / "packet_body.md",
        "result_envelope": packet_dir / "result_envelope.json",
        "result_body": packet_dir / "result_body.md",
        "controller_status_packet": packet_dir / "controller_status_packet.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }


def packet_paths_from_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    envelope = dict(envelope)
    validate_packet_id(str(envelope["packet_id"]))
    packet_body = resolve_project_path(project_root, str(envelope["body_path"]))
    packet_dir = packet_body.parent
    packets_root = packet_dir.parent
    run_root = packets_root.parent if packets_root.name == "packets" else active_run_root(project_root)[1]
    return {
        "run_id": run_root.name,
        "run_root": run_root,
        "packet_dir": packet_dir,
        "packet_envelope": packet_dir / "packet_envelope.json",
        "packet_body": packet_body,
        "result_envelope": packet_dir / "result_envelope.json",
        "result_body": packet_dir / "result_body.md",
        "controller_status_packet": packet_dir / "controller_status_packet.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }


def packet_paths_from_result_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    envelope = dict(envelope)
    validate_packet_id(str(envelope["packet_id"]))
    result_body = resolve_project_path(project_root, str(envelope["result_body_path"]))
    packet_dir = result_body.parent
    packets_root = packet_dir.parent
    run_root = packets_root.parent if packets_root.name == "packets" else active_run_root(project_root)[1]
    return {
        "run_id": run_root.name,
        "run_root": run_root,
        "packet_dir": packet_dir,
        "packet_envelope": packet_dir / "packet_envelope.json",
        "packet_body": packet_dir / "packet_body.md",
        "result_envelope": packet_dir / "result_envelope.json",
        "result_body": result_body,
        "controller_status_packet": packet_dir / "controller_status_packet.json",
        "packet_ledger": run_root / "packet_ledger.json",
    }


def packet_paths_from_any_envelope(project_root: Path, envelope: dict[str, Any]) -> dict[str, Any]:
    if "body_path" in envelope:
        return packet_paths_from_envelope(project_root, envelope)
    if "result_body_path" in envelope:
        return packet_paths_from_result_envelope(project_root, envelope)
    raise PacketRuntimeError("envelope must contain body_path or result_body_path")


def load_envelope(project_root: Path, envelope_path: str | Path) -> dict[str, Any]:
    return read_json(resolve_project_path(project_root, str(envelope_path)))


def verify_body_hash(project_root: Path, body_path: str, expected_hash: str) -> bool:
    return sha256_file(resolve_project_path(project_root, body_path)) == expected_hash
