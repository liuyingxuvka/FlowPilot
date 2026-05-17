"""Path, envelope loading, and hash verification helpers for packet runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packet_runtime_schema import (
    RESULT_ENVELOPE_SCHEMA,
    PacketRuntimeError,
    sha256_file,
    validate_packet_id,
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
    resolved_run_id = current.get("current_run_id") or current.get("active_run_id") or current.get("run_id")
    raw_run_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_run_root:
        run_root = Path(str(raw_run_root))
        if not run_root.is_absolute():
            run_root = root / run_root
        return str(resolved_run_id or run_root.name), run_root
    if resolved_run_id:
        return str(resolved_run_id), flowpilot_root / "runs" / str(resolved_run_id)
    return "legacy", flowpilot_root


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
    envelope = normalize_envelope_aliases(envelope)
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
    envelope = normalize_envelope_aliases(envelope)
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
    envelope = normalize_envelope_aliases(envelope)
    if "body_path" in envelope:
        return packet_paths_from_envelope(project_root, envelope)
    if "result_body_path" in envelope:
        return packet_paths_from_result_envelope(project_root, envelope)
    raise PacketRuntimeError("envelope must contain body_path or result_body_path")


def normalize_envelope_aliases(envelope: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow-normalized packet/result envelope.

    FlowPilot's canonical packet runtime uses `body_path`/`body_hash` for work
    packets and `result_body_path`/`next_recipient` for results. Older or
    hand-authored role envelopes sometimes use more explicit aliases. Normalize
    those mechanical aliases here so the router can stay strict about role
    authority without bouncing safe field-name mismatches back to humans.
    """

    normalized = dict(envelope)
    schema = str(normalized.get("schema_version") or "")
    is_result = schema == RESULT_ENVELOPE_SCHEMA or (
        "completed_by_role" in normalized and "result_body_path" in normalized
    )
    if is_result:
        if "result_body_path" not in normalized and normalized.get("body_path"):
            normalized["result_body_path"] = normalized["body_path"]
        if "result_body_hash" not in normalized and normalized.get("body_hash"):
            normalized["result_body_hash"] = normalized["body_hash"]
        if "next_recipient" not in normalized:
            for key in ("next_holder", "to_role"):
                if normalized.get(key):
                    normalized["next_recipient"] = normalized[key]
                    break
        if "next_holder" not in normalized and normalized.get("next_recipient"):
            normalized["next_holder"] = normalized["next_recipient"]
        if "to_role" not in normalized and normalized.get("next_recipient"):
            normalized["to_role"] = normalized["next_recipient"]
        return normalized

    if "body_path" not in normalized and normalized.get("packet_body_path"):
        normalized["body_path"] = normalized["packet_body_path"]
    if "body_hash" not in normalized and normalized.get("packet_body_hash"):
        normalized["body_hash"] = normalized["packet_body_hash"]
    if "packet_body_path" not in normalized and normalized.get("body_path"):
        normalized["packet_body_path"] = normalized["body_path"]
    if "packet_body_hash" not in normalized and normalized.get("body_hash"):
        normalized["packet_body_hash"] = normalized["body_hash"]
    if "next_holder" not in normalized and normalized.get("to_role"):
        normalized["next_holder"] = normalized["to_role"]
    return normalized


def load_envelope(project_root: Path, envelope_path: str | Path) -> dict[str, Any]:
    return normalize_envelope_aliases(read_json(resolve_project_path(project_root, str(envelope_path))))


def verify_body_hash(project_root: Path, body_path: str, expected_hash: str) -> bool:
    return sha256_file(resolve_project_path(project_root, body_path)) == expected_hash
