"""Runtime-kit backed prompt storage for FlowPilot control text."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from string import Template
from typing import Any, Mapping


PROMPT_MANIFEST_SCHEMA = "flowpilot.prompt_store_manifest.v1"
CARD_MANIFEST_SCHEMA = "flowpilot.prompt_manifest.v1"


class PromptStoreError(RuntimeError):
    """Raised when a prompt asset or prompt manifest entry is invalid."""


class PromptStore:
    """Strict prompt loader for a copied run runtime kit or repo fallback kit."""

    def __init__(self, runtime_kit_root: Path | None = None) -> None:
        self.runtime_kit_root = Path(runtime_kit_root) if runtime_kit_root is not None else runtime_kit_source()

    @classmethod
    def from_run_root(
        cls,
        run_root: Path,
        *,
        fallback_runtime_kit: Path | None = None,
    ) -> "PromptStore":
        copied = Path(run_root) / "runtime_kit"
        if copied.exists():
            return cls(copied)
        return cls(fallback_runtime_kit)

    def manifest_path(self) -> Path:
        return prompt_manifest_path(self.runtime_kit_root)

    def manifest(self) -> dict[str, Any]:
        return load_prompt_manifest(self.runtime_kit_root)

    def entry(self, prompt_id: str) -> dict[str, Any]:
        return prompt_entry(prompt_id, self.runtime_kit_root)

    def text(self, prompt_id: str) -> str:
        return load_prompt_text(prompt_id, self.runtime_kit_root)

    def render(self, prompt_id: str, variables: Mapping[str, Any] | None = None) -> str:
        return render_prompt_text(prompt_id, dict(variables or {}), self.runtime_kit_root)

    def content_hash(self, prompt_id: str) -> str:
        entry = prompt_entry(prompt_id, self.runtime_kit_root)
        return _sha256_text(_prompt_asset_path(entry, self.runtime_kit_root).read_text(encoding="utf-8"))

    def card_manifest(self) -> dict[str, Any]:
        return load_card_manifest(self.runtime_kit_root)

    def card(self, card_id: str) -> dict[str, Any]:
        return card_manifest_entry(load_card_manifest(self.runtime_kit_root), card_id)


def runtime_kit_source() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit"


def prompt_manifest_path(runtime_kit_root: Path | None = None) -> Path:
    root = Path(runtime_kit_root) if runtime_kit_root is not None else runtime_kit_source()
    return root / "prompts" / "manifest.json"


def load_prompt_manifest(runtime_kit_root: Path | None = None) -> dict[str, Any]:
    path = prompt_manifest_path(runtime_kit_root)
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptStoreError(f"prompt manifest missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptStoreError(f"prompt manifest is not valid JSON: {path}") from exc
    if manifest.get("schema_version") != PROMPT_MANIFEST_SCHEMA:
        raise PromptStoreError("prompt manifest has unsupported schema_version")
    if not isinstance(manifest.get("prompts"), list):
        raise PromptStoreError("prompt manifest requires a prompts list")
    ids: set[str] = set()
    for entry in manifest["prompts"]:
        if not isinstance(entry, dict):
            raise PromptStoreError("prompt manifest entry must be an object")
        prompt_id = str(entry.get("id") or "")
        path_value = str(entry.get("path") or "")
        sha256 = str(entry.get("sha256") or "")
        if not prompt_id or not path_value or not sha256:
            raise PromptStoreError("prompt manifest entry requires id, path, and sha256")
        if prompt_id in ids:
            raise PromptStoreError(f"duplicate prompt id: {prompt_id}")
        ids.add(prompt_id)
    return manifest


def load_card_manifest(runtime_kit_root: Path | None = None) -> dict[str, Any]:
    root = Path(runtime_kit_root) if runtime_kit_root is not None else runtime_kit_source()
    manifest_path = root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PromptStoreError(f"card manifest missing: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise PromptStoreError(f"card manifest is not valid JSON: {manifest_path}") from exc
    if manifest.get("schema_version") != CARD_MANIFEST_SCHEMA:
        raise PromptStoreError("invalid prompt manifest schema")
    return manifest


def load_card_manifest_from_run(
    run_root: Path,
    fallback_runtime_kit: Path | None = None,
) -> dict[str, Any]:
    manifest_path = Path(run_root) / "runtime_kit" / "manifest.json"
    if manifest_path.exists():
        return load_card_manifest(manifest_path.parent)
    return load_card_manifest(fallback_runtime_kit)


def card_manifest_entry(manifest: dict[str, Any], card_id: str) -> dict[str, Any]:
    cards = manifest.get("cards")
    if not isinstance(cards, list):
        raise PromptStoreError("prompt manifest cards must be a list")
    for card in cards:
        if isinstance(card, dict) and card.get("id") == card_id:
            return card
    raise PromptStoreError(f"card not found in prompt manifest: {card_id}")


def prompt_entry(prompt_id: str, runtime_kit_root: Path | None = None) -> dict[str, Any]:
    manifest = load_prompt_manifest(runtime_kit_root)
    for entry in manifest["prompts"]:
        if entry.get("id") == prompt_id:
            return dict(entry)
    raise PromptStoreError(f"unknown prompt id: {prompt_id}")


def _prompt_asset_path(entry: dict[str, Any], runtime_kit_root: Path | None = None) -> Path:
    root = Path(runtime_kit_root) if runtime_kit_root is not None else runtime_kit_source()
    path = root / str(entry["path"])
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PromptStoreError(f"prompt asset outside runtime kit: {path}") from exc
    return path


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_prompt_text(prompt_id: str, runtime_kit_root: Path | None = None) -> str:
    entry = prompt_entry(prompt_id, runtime_kit_root)
    path = _prompt_asset_path(entry, runtime_kit_root)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PromptStoreError(f"prompt asset missing: {path}") from exc
    actual_hash = _sha256_text(text)
    expected_hash = str(entry["sha256"])
    if actual_hash != expected_hash:
        raise PromptStoreError(
            f"prompt asset hash mismatch for {prompt_id}: expected {expected_hash}, got {actual_hash}"
        )
    if entry.get("strip_trailing_newline", True):
        text = text.rstrip("\n")
    return text


def render_prompt_text(
    prompt_id: str,
    variables: dict[str, Any] | None = None,
    runtime_kit_root: Path | None = None,
) -> str:
    entry = prompt_entry(prompt_id, runtime_kit_root)
    values = {key: str(value) for key, value in (variables or {}).items()}
    required = {str(item) for item in entry.get("template_variables", [])}
    missing = sorted(required.difference(values))
    if missing:
        raise PromptStoreError(f"prompt {prompt_id} missing template variables: {', '.join(missing)}")
    try:
        return Template(load_prompt_text(prompt_id, runtime_kit_root)).substitute(values)
    except KeyError as exc:
        raise PromptStoreError(f"prompt {prompt_id} contains undeclared template variable: {exc.args[0]}") from exc
