"""Validate one current background tier before evidence compilation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .definitions import commands_for_tier
from .background_supervisor import supervisor_control_paths
from .evidence_v5 import load_json_object
from .verification import verify_background_tier


def _json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _supervisor_paths(root: Path, tier: str) -> tuple[Path, Path]:
    base = root / f"{tier}_background_supervisor"
    return base.with_suffix(".meta.json"), base.with_suffix(".exit.txt")


def validated_tier(root: Path, tier: str) -> dict[str, Any]:
    """Return the exact current tier evidence or reject the tier."""

    meta_path, exit_path = _supervisor_paths(root, tier)
    if not meta_path.is_file() or not exit_path.is_file():
        raise ValueError(f"{tier} background supervisor artifacts are incomplete under {root}")
    meta = _json_object(meta_path)
    try:
        exit_code = int(exit_path.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise ValueError(f"invalid exit artifact: {exit_path}") from exc
    if meta.get("status") != "passed" or exit_code != 0 or meta.get("timed_out") is True:
        raise ValueError(f"{tier} background tier is not a current pass: {meta}")
    verification = verify_background_tier(
        tier,
        commands_for_tier(tier),
        log_root=root,
    )
    if not verification["ok"]:
        raise ValueError(
            f"{tier} current owner evidence is invalid: {verification['failures']}"
        )
    control_paths = supervisor_control_paths(root, tier)
    impact_plan = load_json_object(control_paths["impact_plan"])
    owner_index = load_json_object(control_paths["owner_index"])
    owner_rows = owner_index.get("owners")
    if not isinstance(owner_rows, list):
        raise ValueError(f"{tier} owner evidence refs are missing")
    owners = {
        str(row.get("owner_id") or ""): row
        for row in owner_rows
        if isinstance(row, dict)
    }
    child_meta_paths = sorted(
        path
        for path in root.glob("*.meta.json")
        if path != meta_path and "background_supervisor" not in path.name
    )
    child_exit_paths = sorted(
        path
        for path in root.glob("*.exit.txt")
        if path != exit_path and "background_supervisor" not in path.name
    )
    return {
        "tier": tier,
        "root": root,
        "meta": meta,
        "meta_path": meta_path,
        "exit_path": exit_path,
        "child_meta_paths": child_meta_paths,
        "child_exit_paths": child_exit_paths,
        "selected_count": len(owners),
        "executed_count": int(meta.get("execute_count") or 0),
        "reused_count": int(meta.get("reuse_count") or 0),
        "owners": owners,
        "owner_index": owner_index,
        "owner_index_path": control_paths["owner_index"],
        "impact_plan_path": control_paths["impact_plan"],
        "progress_path": control_paths["progress"],
        "impact_plan": impact_plan,
        "snapshot_start": impact_plan.get("snapshot"),
        "snapshot_end": {
            "fingerprint": meta.get("snapshot_end_fingerprint"),
        },
    }
