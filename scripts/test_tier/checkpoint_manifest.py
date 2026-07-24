"""Compile one passed all-tier root into current owner checkpoint evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .definitions import commands_for_tier
from .background_supervisor import supervisor_control_paths
from .evidence_v5 import load_json_object
from .source_fingerprint import source_snapshot
from .verification import verify_background_tier


def compile_owner_checkpoint_manifest(
    *,
    all_root: Path,
    schema_version: str,
    portable_path: Callable[[Path], str],
    sha256: Callable[[Path], str],
) -> dict[str, Any]:
    """Retain every independently current owner from one terminal all-tier run."""

    meta_path = all_root / "all_background_supervisor.meta.json"
    exit_path = all_root / "all_background_supervisor.exit.txt"
    if not meta_path.is_file() or not exit_path.is_file():
        raise ValueError(
            f"all background supervisor artifacts are incomplete under {all_root}"
        )
    meta_value = json.loads(meta_path.read_text(encoding="utf-8"))
    if not isinstance(meta_value, dict):
        raise ValueError("all background supervisor metadata is not an object")
    try:
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise ValueError(f"invalid exit artifact: {exit_path}") from exc
    if (
        meta_value.get("status") != "passed"
        or exit_code != 0
        or meta_value.get("timed_out") is True
        or meta_value.get("running")
    ):
        raise ValueError("all background supervisor is not a terminal pass")

    commands = commands_for_tier("all")
    verification = verify_background_tier("all", commands, log_root=all_root)
    owner_ids = {command.name for command in commands}
    supervisor_failures = [
        failure
        for failure in verification["failures"]
        if not any(failure.startswith(f"{owner_id}:") for owner_id in owner_ids)
    ]
    if supervisor_failures:
        raise ValueError(
            "all background supervisor evidence is structurally invalid: "
            + ",".join(supervisor_failures)
        )
    control_paths = supervisor_control_paths(all_root, "all")
    owner_index = load_json_object(control_paths["owner_index"])
    owner_rows = owner_index.get("owners")
    if not isinstance(owner_rows, list):
        raise ValueError("all background supervisor owner refs are missing")
    source_owners = {
        str(row.get("owner_id") or ""): row
        for row in owner_rows
        if isinstance(row, dict)
    }
    current_owner_ids = {
        str(row["name"])
        for row in verification["children"]
        if row.get("ok") is True
    }
    if not current_owner_ids:
        raise ValueError("all background supervisor has no current owner proof")
    owners = {
        owner_id: source_owners[owner_id]
        for owner_id in sorted(current_owner_ids)
    }
    rejected = {
        str(row["name"]): list(row.get("failures") or ())
        for row in verification["children"]
        if row.get("ok") is not True
    }
    snapshot = source_snapshot()
    return {
        "schema_version": schema_version,
        "manifest_kind": "flowpilot.owner_checkpoint",
        "phase": "checkpoint",
        "claim_scope": "owner_reuse_only",
        "snapshot": snapshot,
        "owners": owners,
        "rejected_owner_ids": rejected,
        "source_supervisor": {
            "tier": "all",
            "root": portable_path(all_root),
            "meta_path": portable_path(meta_path),
            "meta_sha256": sha256(meta_path),
            "exit_path": portable_path(exit_path),
            "exit_sha256": sha256(exit_path),
            "impact_plan_id": verification["impact_plan_id"],
            "impact_plan_ref": verification["impact_plan_ref"],
            "owner_index_ref": verification["owner_index_ref"],
            "source_snapshot_fingerprint": verification["snapshot_fingerprint"],
            "current_owner_count": len(owners),
            "rejected_owner_count": len(rejected),
        },
    }


__all__ = ["compile_owner_checkpoint_manifest"]
