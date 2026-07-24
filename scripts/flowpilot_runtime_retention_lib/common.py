"""Shared current-contract constants and hashing helpers for retention."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORT_SCHEMA_VERSION = "flowpilot.runtime_retention_report.v2"
PLAN_SCHEMA_VERSION = "flowpilot.runtime_retention_plan.v1"
APPLY_SCHEMA_VERSION = "flowpilot.runtime_retention_apply.v1"
RUN_HEAVY_DIRECTORIES = (
    "packets",
    "results",
    "routes",
    "evidence",
    "reviews",
    "flowguard",
    "runtime",
    "role_memory",
    "role_continuity",
    "role_assignments",
    "node_acceptance_plans",
    "parent_backward_replays",
    "imports",
    "console",
    "closure",
    "lifecycle",
    "frontier",
    "preplanning",
    "route_nodes",
    "startup_intake",
)


class RetentionPlanError(RuntimeError):
    """Raised when a frozen retention plan cannot be applied safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _project_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json_result(
    path: Path,
    *,
    max_bytes: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    try:
        if max_bytes is not None and path.stat().st_size > max_bytes:
            return None, "too_large"
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return None, "missing"
    except UnicodeDecodeError:
        return None, "invalid_utf8"
    except json.JSONDecodeError:
        return None, "invalid_json"
    except OSError:
        return None, "unreadable"
    if not isinstance(value, dict):
        return None, "not_object"
    return value, ""


def _read_json(path: Path) -> dict[str, Any]:
    value, _ = _read_json_result(path)
    return value or {}

def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _tree_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    if not path.is_dir():
        raise RetentionPlanError(f"retention candidate directory is missing: {path}")
    for child in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        if child.is_symlink():
            raise RetentionPlanError(f"retention candidate contains a symlink: {child}")
        if not child.is_file():
            continue
        relative = child.relative_to(path).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(child.stat().st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(_sha256_file(child).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()
