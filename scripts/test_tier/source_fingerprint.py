"""Canonical source snapshots for test-tier planning and evidence provenance."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Mapping


ROOT = Path(__file__).resolve().parents[2]


def _generated_evidence_json(path: Path) -> bool:
    name = path.name
    return (
        "_results" in name
        or name.endswith(".proof.json")
        or name.endswith("_proof.json")
        or name.endswith("_summary.json")
        or name.endswith("_evidence.json")
        or name.endswith("_evidence_manifest.json")
        or name.endswith(".background_latest.json")
    )


def covered_source_files() -> Iterable[Path]:
    canonical_authorities = (
        ROOT / ".flowguard" / "behavior_commitment_ledger" / "ledger.json",
    )
    for path in canonical_authorities:
        if path.is_file():
            yield path

    roots = (
        ROOT / "skills" / "flowpilot",
        ROOT / "simulations",
        ROOT / "scripts",
        ROOT / "tests",
    )
    for base in roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            if path.suffix not in {".py", ".md", ".json"}:
                continue
            if path.suffix == ".json" and _generated_evidence_json(path):
                continue
            yield path


def canonical_source_bytes(path: Path) -> bytes:
    """Return current-contract bytes with transport-only line endings normalized."""

    data = path.read_bytes()
    if path.suffix not in {".py", ".md", ".json"}:
        return data
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"controlled text is not UTF-8: {path}") from exc
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def file_fingerprint(path: Path) -> str:
    """Hash one supported current input after canonical text normalization."""

    if not path.is_file():
        raise FileNotFoundError(path)
    return hashlib.sha256(canonical_source_bytes(path)).hexdigest()


def fingerprint_set(values: Mapping[str, str]) -> str:
    """Hash one exact path-to-content inventory."""

    digest = hashlib.sha256()
    for relative, content_fingerprint in sorted(values.items()):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content_fingerprint.encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def source_inventory() -> dict[str, str]:
    """Return the canonical governed-source inventory for audit and impact review."""

    return {
        path.relative_to(ROOT).as_posix(): file_fingerprint(path)
        for path in covered_source_files()
    }


def source_snapshot() -> dict[str, object]:
    """Return one canonical audit snapshot; it is not owner applicability authority."""

    files = source_inventory()
    return {
        "schema_version": "flowpilot.source_snapshot.v1",
        "fingerprint": fingerprint_set(files),
        "files": files,
    }


def source_fingerprint() -> str:
    """Return the canonical snapshot fingerprint retained for provenance only."""

    return str(source_snapshot()["fingerprint"])


__all__ = [
    "canonical_source_bytes",
    "covered_source_files",
    "file_fingerprint",
    "fingerprint_set",
    "source_fingerprint",
    "source_inventory",
    "source_snapshot",
]
