"""Ordinary non-sealed work-material scanning for FlowPilot material maps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import flowpilot_material_artifact_map_entries as entry_policy
import packet_runtime


ORDINARY_WORK_ARTIFACT_MAX_ENTRIES = 500
ORDINARY_WORK_ARTIFACT_SUFFIXES = {
    ".json",
    ".jsonl",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".csv",
    ".tsv",
    ".html",
    ".htm",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".pdf",
}


def _normalized_resolved_path(path: str | Path) -> str:
    try:
        return str(Path(path).resolve()).casefold()
    except (OSError, RuntimeError):
        return str(path).casefold()


def _sealed_body_paths_from_entries(project_root: Path, entries: list[dict[str, Any]]) -> set[str]:
    sealed: set[str] = set()
    for entry in entries:
        for ref in entry.get("body_refs") or []:
            if not isinstance(ref, dict):
                continue
            raw_path = str(ref.get("path") or "")
            if not raw_path:
                continue
            try:
                resolved = packet_runtime.resolve_project_path(project_root, raw_path)
            except Exception:
                resolved = Path(raw_path)
            sealed.add(_normalized_resolved_path(resolved))
    return sealed


def _looks_like_sealed_body_path(path: Path) -> bool:
    normalized = "/".join(path.parts).lower()
    name = path.name.lower()
    return (
        ".sealed" in name
        or name.endswith("_sealed.json")
        or name.endswith("_sealed.md")
        or "sealed_body" in normalized
        or "/sealed/" in normalized
    )


def _ordinary_work_artifact_entry_id(run_root: Path, path: Path) -> str:
    rel = path.relative_to(run_root).as_posix()
    safe = "".join(ch if ch.isalnum() else "-" for ch in rel.lower()).strip("-")
    return f"ordinary:{safe[:180]}"


def add_ordinary_work_artifact_entries(
    project_root: Path,
    run_root: Path,
    entries: list[dict[str, Any]],
    *,
    material_artifact_map_filename: str,
) -> None:
    sealed_paths = _sealed_body_paths_from_entries(project_root, entries)
    seen_source_paths = {
        str(path)
        for entry in entries
        for path in entry.get("source_paths") or []
        if isinstance(path, str)
    }
    count = 0
    if not run_root.exists():
        return
    for path in sorted((item for item in run_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        if count >= ORDINARY_WORK_ARTIFACT_MAX_ENTRIES:
            entries.append(
                entry_policy.make_entry(
                    entry_id="ordinary:index_truncated",
                    kind="ordinary_work_artifact_index_truncation",
                    producer_role="router",
                    owner_role="project_manager",
                    status="unresolved",
                    authority_level="navigation_only",
                    safe_summary=(
                        "Ordinary work artifact index reached its safety cap; non-sealed project/run files "
                        "remain readable even when not indexed here."
                    ),
                    metadata={"max_entries": ORDINARY_WORK_ARTIFACT_MAX_ENTRIES},
                )
            )
            return
        if path.name == material_artifact_map_filename:
            continue
        if path.suffix.lower() not in ORDINARY_WORK_ARTIFACT_SUFFIXES:
            continue
        if _looks_like_sealed_body_path(path):
            continue
        if _normalized_resolved_path(path) in sealed_paths:
            continue
        source_ref = entry_policy.safe_source_ref(project_root, path)
        if source_ref is None:
            continue
        source_path = str(source_ref.get("path") or "")
        if not source_path or source_path in seen_source_paths:
            continue
        seen_source_paths.add(source_path)
        entries.append(
            entry_policy.make_entry(
                entry_id=_ordinary_work_artifact_entry_id(run_root, path),
                kind="ordinary_work_artifact",
                producer_role="runtime_or_role",
                owner_role="shared_role_material",
                status="current",
                authority_level="ordinary_project_material",
                safe_summary=(
                    "Non-sealed project/run work material. This entry is navigation only; ordinary read access "
                    "comes from the public material policy, not from this map."
                ),
                source_refs=[source_ref],
                metadata={
                    "ordinary_file_read_allowed": True,
                    "sealed_body_boundary": "sealed packet/result/report/mail bodies require runtime authorization",
                },
            )
        )
        count += 1


__all__ = ["add_ordinary_work_artifact_entries"]
