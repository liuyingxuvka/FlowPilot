"""Filesystem and runtime-kit helpers for role-output schemas."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import packet_runtime
from flowpilot_runtime_gateway import GATEWAY_ROLE_OUTPUT, assert_runtime_gateway_write
from role_output_runtime_schema_specs import (
    CONTRACT_REGISTRY_PATH,
    PROMPT_MANIFEST_SCHEMA,
    ROLE_KEYS,
    RoleOutputRuntimeError,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    assert_runtime_gateway_write(path, GATEWAY_ROLE_OUTPUT, operation="role_output_write_json")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_bytes(_json_bytes(payload))
    tmp_path.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RoleOutputRuntimeError(f"JSON root must be an object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_concrete_agent_id(agent_id: str, *, role: str) -> str:
    resolved = str(agent_id or "").strip()
    if not resolved:
        raise RoleOutputRuntimeError(f"{role} role-output runtime session requires a concrete agent_id")
    if resolved in ROLE_KEYS:
        raise RoleOutputRuntimeError("agent_id must be a concrete agent id, not a role key")
    return resolved


def _project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RoleOutputRuntimeError(f"path is outside project root: {path}") from exc


def _resolve_project_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else project_root.resolve() / path


def _run_paths(project_root: Path, run_id: str | None = None) -> tuple[str, Path]:
    resolved_run_id, run_root = packet_runtime.active_run_root(project_root, run_id)
    return str(resolved_run_id), run_root


def _registry_path(project_root: Path) -> Path:
    return project_root.resolve() / CONTRACT_REGISTRY_PATH


def load_contract_registry(project_root: Path) -> dict[str, Any]:
    path = _registry_path(project_root)
    if not path.exists():
        from role_output_runtime_schema_specs import _default_contract_registry_path

        fallback = _default_contract_registry_path()
        if fallback.exists():
            return _read_json(fallback)
        raise RoleOutputRuntimeError(f"output contract registry is missing: {_project_relative(project_root, path)}")
    return _read_json(path)


def _runtime_kit_source(project_root: Path) -> Path:
    project_runtime_kit = project_root.resolve() / "skills" / "flowpilot" / "assets" / "runtime_kit"
    if project_runtime_kit.exists():
        return project_runtime_kit
    return Path(__file__).resolve().parent / "runtime_kit"


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _run_manifest_path(project_root: Path, run_root: Path) -> Path:
    manifest_path = run_root / "runtime_kit" / "manifest.json"
    if manifest_path.exists():
        return manifest_path
    return _runtime_kit_source(project_root) / "manifest.json"


def _manifest_card(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise RoleOutputRuntimeError("prompt manifest cards must be a list")
    for card in cards:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    raise RoleOutputRuntimeError(f"card not found in prompt manifest: {card_id}")


def controller_boundary_constraints() -> dict[str, Any]:
    return {
        "relay_and_record_only": True,
        "next_step_source": "flowpilot_router.py",
        "controller_may_create_project_evidence": False,
        "controller_may_read_sealed_bodies": False,
        "controller_may_implement": False,
        "controller_may_approve_gate": False,
        "controller_may_mutate_route": False,
        "controller_may_close_node": False,
    }


def _controller_boundary_sources(project_root: Path, run_root: Path) -> dict[str, Any]:
    manifest_path = _run_manifest_path(project_root, run_root)
    manifest = _read_json(manifest_path)
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise RoleOutputRuntimeError("invalid prompt manifest schema")
    controller_core = _manifest_card(manifest, "controller.core")
    card_path = manifest_path.parent / str(controller_core["path"])
    if not card_path.exists():
        raise RoleOutputRuntimeError("controller.core card path is missing")
    policy = manifest.get("controller_policy")
    if not isinstance(policy, dict):
        raise RoleOutputRuntimeError("prompt manifest controller_policy must be an object")
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "manifest_hash": _sha256_file(manifest_path),
        "controller_core_card": controller_core,
        "controller_core_path": card_path,
        "controller_core_hash": _sha256_file(card_path),
        "controller_policy": policy,
        "controller_policy_hash": _json_sha256(policy),
    }
