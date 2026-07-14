"""Canonical covered-source fingerprint for background test evidence."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable


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


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    for path in covered_source_files():
        relative = path.relative_to(ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


__all__ = ["covered_source_files", "source_fingerprint"]
