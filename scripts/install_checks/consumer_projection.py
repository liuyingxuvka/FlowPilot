"""Build and compare the target-owned FlowPilot consumer projection."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


CONSUMER_RELEASE_SCHEMA = "consumer.skill_distribution.current"
CONSUMER_RELEASE_MANIFEST = "consumer-release.json"
CONSUMER_PROJECTION_ID = "projection:consumer-distribution"
CONSUMER_EXCLUDED_NAMES = frozenset(
    {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".mypy_cache"}
)
CONSUMER_TEXT_SUFFIXES = frozenset(
    {
        ".md",
        ".txt",
        ".json",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".py",
        ".ps1",
        ".sh",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".html",
        ".css",
        ".xml",
        ".ini",
        ".cfg",
    }
)
CONSUMER_FORBIDDEN_PATTERNS = (
    re.compile(r"(?i)(?:^|[\\/'\"`])\.skillguard(?:[\\/]|$)"),
    re.compile(r"(?i)\bskillguard(?:\.py)?\b"),
    re.compile(r"(?im)^\s*(?:from|import)\s+skillguard(?:\b|\.)"),
    re.compile(r"(?i)\bportfolio[_ -](?:receipt|reuse|evidence|graduation)\b"),
)
CONSUMER_MANIFEST_CLAIM_BOUNDARY = (
    "This manifest identifies target-owned consumer files only. It carries no "
    "author contract, receipt, router, session, cache, or execution authority."
)


def _iter_hashable_files(path: Path) -> list[Path]:
    files: list[Path] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        relative = item.relative_to(path)
        if any(part in {"__pycache__", ".git"} for part in relative.parts):
            continue
        if item.suffix in {".pyc", ".pyo"}:
            continue
        files.append(item)
    return sorted(files, key=lambda item: item.relative_to(path).as_posix())


def canonical_hash(value: Any) -> str:
    encoded = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def file_fingerprint(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def load_consumer_contract(source_path: Path) -> dict[str, Any] | None:
    contract_path = source_path / ".skillguard" / "compiled-contract.json"
    if not contract_path.is_file():
        return None
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("consumer projection contract must be an object")
    projection = payload.get("consumer_projection")
    if (
        not isinstance(projection, dict)
        or projection.get("projection_id") != CONSUMER_PROJECTION_ID
        or projection.get("release_manifest_path") != CONSUMER_RELEASE_MANIFEST
    ):
        raise ValueError("consumer projection contract is missing or unsupported")
    return payload


def consumer_source_files(
    source_path: Path,
    contract: dict[str, Any],
) -> list[dict[str, str]]:
    source = source_path.resolve()
    impact_plan = contract.get("content_impact_plan")
    if not isinstance(impact_plan, dict):
        raise ValueError("consumer projection requires a content impact plan")
    member_root = str(impact_plan.get("member_root_path", ".")).strip("/")
    source_only = {
        str(row.get("path", "")).replace("\\", "/")
        for row in impact_plan.get("inventory", [])
        if isinstance(row, dict) and row.get("install_disposition") == "source_only"
    }
    rows: list[dict[str, str]] = []
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        if any(part in CONSUMER_EXCLUDED_NAMES for part in relative.parts):
            continue
        normalized = relative.as_posix()
        if normalized == CONSUMER_RELEASE_MANIFEST:
            raise ValueError("consumer release manifest is generated, not source-owned")
        if normalized == ".skillguard" or normalized.startswith(".skillguard/"):
            continue
        inventory_path = (
            normalized
            if member_root in {"", "."}
            else f"{member_root}/{normalized}"
        )
        if inventory_path in source_only:
            continue
        if path.is_symlink():
            raise ValueError(f"consumer projection rejects symlink: {normalized}")
        if not path.is_file():
            continue
        if "skillguard" in normalized.lower():
            raise ValueError(
                f"consumer projection rejects author-control path: {normalized}"
            )
        if path.suffix.lower() in CONSUMER_TEXT_SUFFIXES or path.name == "SKILL.md":
            text = path.read_text(encoding="utf-8")
            if any(pattern.search(text) for pattern in CONSUMER_FORBIDDEN_PATTERNS):
                raise ValueError(
                    "consumer projection rejects author-control instruction: "
                    f"{normalized}"
                )
        rows.append(
            {
                "path": normalized,
                "content_hash": file_fingerprint(path),
            }
        )
    rows.sort(key=lambda row: row["path"])
    return rows


def consumer_release_manifest(source_path: Path) -> dict[str, Any] | None:
    contract = load_consumer_contract(source_path)
    if contract is None:
        return None
    files = consumer_source_files(source_path, contract)
    identity: dict[str, Any] = {
        "schema_version": CONSUMER_RELEASE_SCHEMA,
        "skill_id": str(contract.get("skill_id", "")),
        "projection_id": CONSUMER_PROJECTION_ID,
        "files": files,
        "author_control_excluded": True,
    }
    manifest = {
        **identity,
        "release_id": canonical_hash(identity),
        "claim_boundary": CONSUMER_MANIFEST_CLAIM_BOUNDARY,
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    return manifest


def compare_consumer_projection(
    source_path: Path,
    installed_path: Path,
) -> dict[str, Any] | None:
    expected = consumer_release_manifest(source_path)
    if expected is None:
        return None
    manifest_path = installed_path / CONSUMER_RELEASE_MANIFEST
    errors: list[str] = []
    try:
        actual = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        actual = {}
        errors.append("consumer release manifest is missing or invalid")
    if actual != expected:
        errors.append("consumer release identity differs from repository projection")
    expected_files = {
        str(row["path"]): str(row["content_hash"])
        for row in expected["files"]
    }
    actual_paths = {
        path.relative_to(installed_path).as_posix()
        for path in _iter_hashable_files(installed_path)
    }
    expected_paths = set(expected_files) | {CONSUMER_RELEASE_MANIFEST}
    if actual_paths != expected_paths:
        errors.append("installed consumer file inventory differs from projection")
    for relative, fingerprint in expected_files.items():
        candidate = installed_path / Path(*relative.split("/"))
        if not candidate.is_file() or file_fingerprint(candidate) != fingerprint:
            errors.append(f"installed consumer file differs: {relative}")
            break
    return {
        "current": not errors,
        "projection_id": CONSUMER_PROJECTION_ID,
        "release_id": str(actual.get("release_id", "")),
        "expected_release_id": str(expected["release_id"]),
        "author_control_excluded": (
            actual.get("author_control_excluded") is True
            and not (installed_path / ".skillguard").exists()
        ),
        "errors": errors,
    }


def copy_consumer_projection(source_path: Path, destination: Path) -> None:
    manifest = consumer_release_manifest(source_path)
    if manifest is None:
        raise ValueError("consumer projection contract is unavailable")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        for row in manifest["files"]:
            relative = Path(*str(row["path"]).split("/"))
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path / relative, target)
        (destination / CONSUMER_RELEASE_MANIFEST).write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            encoding="utf-8",
        )
    except Exception:
        shutil.rmtree(destination)
        raise
