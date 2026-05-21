"""JSON and role-output hash helpers for the FlowPilot router."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _json_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256((json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")).hexdigest()


def _without_role_output_envelope(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body.pop("_role_output_envelope", None)
    return body


def _role_output_semantic_hash(path: Path) -> str | None:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    return _json_sha256(_without_role_output_envelope(raw))


def _role_output_semantic_hashes(path: Path) -> set[str]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return set()
    if not isinstance(raw, dict):
        return set()
    body = _without_role_output_envelope(raw)
    canonical_lf = json.dumps(body, indent=2, sort_keys=True) + "\n"
    variants = {canonical_lf, canonical_lf.replace("\n", "\r\n")}
    return {hashlib.sha256(variant.encode("utf-8")).hexdigest() for variant in variants}


def _role_output_hashes(path: Path) -> tuple[str, str | None]:
    raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return raw_hash, _role_output_semantic_hash(path)
