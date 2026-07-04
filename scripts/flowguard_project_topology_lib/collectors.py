"""Collectors for the FlowGuard project topology map."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Mapping

from flowguard_project_topology_lib.common import (
    ALIGNMENT_RESULT_PATH,
    COVERAGE_RESULT_PATH,
    DEFAULT_JSON_PATH,
    DEFAULT_MARKDOWN_PATH,
    GENERATOR_VERSION,
    IMPORTANT_RESULT_PATHS,
    MODEL_HIERARCHY_RESULT_PATH,
    MODEL_MATURATION_RESULT_PATH,
    MODEL_MESH_RESULT_PATH,
    ROOT,
    _classify_area,
    _coverage_tier,
    _declared_result_path,
    _dedupe_sources,
    _evidence_status,
    _model_path_for_key,
    _public_command,
    _read_json,
    _read_text,
    _rel,
    _runner_key,
)


def _build_model_rows(root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    runner_paths = sorted((root / "simulations").glob("run_*checks.py"))
    rows: list[dict[str, Any]] = []
    sources: list[Path] = []
    for runner_path in runner_paths:
        text = _read_text(runner_path)
        key = _runner_key(runner_path)
        result_path = _declared_result_path(runner_path, text)
        model_path = _model_path_for_key(key, runner_path, text)
        payload = _read_json(result_path) if result_path else None
        row = {
            "runner_key": key,
            "area": _classify_area(key, runner_path.name, model_path.name if model_path else ""),
            "runner_path": _rel(runner_path, root),
            "model_path": _rel(model_path, root) if model_path else "",
            "result_path": _rel(result_path, root) if result_path else "",
            "coverage_tier": _coverage_tier(key),
            "evidence": _evidence_status(payload),
        }
        rows.append(row)
        sources.append(runner_path)
        if model_path:
            sources.append(model_path)
        if result_path and result_path.exists():
            sources.append(result_path)
    return rows, sources


def _build_alignment_rows(root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    payload = _read_json(ALIGNMENT_RESULT_PATH)
    sources: list[Path] = [ALIGNMENT_RESULT_PATH]
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, Mapping):
        return rows, sources
    for plan in payload.get("per_plan", []) if isinstance(payload.get("per_plan"), list) else []:
        plan_payload = plan.get("plan") if isinstance(plan, Mapping) else None
        test_evidence = plan_payload.get("test_evidence", []) if isinstance(plan_payload, Mapping) else []
        obligations = plan_payload.get("obligations", []) if isinstance(plan_payload, Mapping) else []
        evidence_paths = sorted(
            {
                str(evidence.get("path"))
                for evidence in test_evidence
                if isinstance(evidence, Mapping) and evidence.get("path")
            }
        )
        for relpath in evidence_paths:
            path = root / relpath
            if path.exists():
                sources.append(path)
        rows.append(
            {
                "family": str(plan.get("family") or plan.get("model_id") or ""),
                "model_id": str(plan.get("model_id") or ""),
                "area": _classify_area(str(plan.get("family") or ""), str(plan.get("model_id") or "")),
                "ok": plan.get("ok"),
                "decision": plan.get("decision"),
                "model_checks": list(plan.get("model_checks") or []),
                "obligation_count": len(obligations) if isinstance(obligations, list) else 0,
                "test_evidence_count": len(test_evidence) if isinstance(test_evidence, list) else 0,
                "test_paths": evidence_paths[:30],
                "coverage_boundary": plan.get("coverage_boundary"),
            }
        )
    return rows, sources


def _build_surface_rows(root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    payload = _read_json(ALIGNMENT_RESULT_PATH)
    sources: list[Path] = [ALIGNMENT_RESULT_PATH]
    rows: list[dict[str, Any]] = []
    if not isinstance(payload, Mapping):
        return rows, sources
    diagnostic = payload.get("full_model_test_code_diagnostic")
    if not isinstance(diagnostic, Mapping):
        return rows, sources
    for surface in diagnostic.get("surfaces", []) if isinstance(diagnostic.get("surfaces"), list) else []:
        if not isinstance(surface, Mapping):
            continue
        relpath = str(surface.get("path") or "")
        if relpath:
            path = root / relpath
            if path.exists():
                sources.append(path)
        kind = str(surface.get("kind") or "")
        rows.append(
            {
                "surface_id": str(surface.get("surface_id") or ""),
                "name": str(surface.get("name") or ""),
                "kind": kind,
                "area": _classify_area(
                    str(surface.get("surface_owner") or ""),
                    str(surface.get("name") or ""),
                    relpath,
                ),
                "path": relpath,
                "surface_owner": str(surface.get("surface_owner") or ""),
                "covered": surface.get("covered"),
                "evidence_status": surface.get("evidence_status"),
                "gap_codes": list(surface.get("gap_codes") or []),
                "release_relevance": surface.get("release_relevance"),
                "repair_types": list(surface.get("repair_types") or []),
            }
        )
    return rows, sources


def _build_test_tier_rows(root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    from scripts.test_tier.definitions import commands_for_tier, tier_names

    rows: list[dict[str, Any]] = []
    sources = sorted((root / "scripts" / "test_tier").glob("*.py"))
    for tier in tier_names():
        for command in commands_for_tier(tier):
            command_text = " ".join(command.command)
            rows.append(
                {
                    "tier": tier,
                    "name": command.name,
                    "area": _classify_area(command.name, command_text, command.description),
                    "command": _public_command(command.command, root),
                    "description": command.description,
                    "long_running": command.long_running,
                    "release_only": command.release_only,
                    "background_recommended": command.background_recommended,
                }
            )
    return rows, sources


def _build_evidence_summary(root: Path) -> tuple[dict[str, Any], list[Path]]:
    summary: dict[str, Any] = {}
    sources: list[Path] = []
    names = {
        ALIGNMENT_RESULT_PATH: "model_test_alignment",
        COVERAGE_RESULT_PATH: "coverage_sweep",
        MODEL_MATURATION_RESULT_PATH: "model_maturation",
        MODEL_MESH_RESULT_PATH: "model_mesh",
        MODEL_HIERARCHY_RESULT_PATH: "model_hierarchy",
    }
    for path in IMPORTANT_RESULT_PATHS:
        payload = _read_json(path)
        summary[names.get(path, path.stem)] = {
            "path": _rel(path, root),
            "evidence": _evidence_status(payload),
        }
        sources.append(path)
    return summary, sources


def _summarize_areas(
    model_rows: list[dict[str, Any]],
    alignment_rows: list[dict[str, Any]],
    surface_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    areas: dict[str, dict[str, Any]] = {}

    def area_row(area: str) -> dict[str, Any]:
        return areas.setdefault(
            area,
            {
                "model_count": 0,
                "alignment_family_count": 0,
                "code_surface_count": 0,
                "test_command_count": 0,
                "runner_keys": [],
                "surface_kinds": {},
                "known_bad_count": 0,
            },
        )

    for row in model_rows:
        item = area_row(str(row["area"]))
        item["model_count"] += 1
        item["runner_keys"].append(row["runner_key"])
        item["known_bad_count"] += len(row.get("evidence", {}).get("known_bad") or [])
    for row in alignment_rows:
        area_row(str(row["area"]))["alignment_family_count"] += 1
    for row in surface_rows:
        item = area_row(str(row["area"]))
        item["code_surface_count"] += 1
        kind = str(row.get("kind") or "")
        item["surface_kinds"][kind] = item["surface_kinds"].get(kind, 0) + 1
    for row in test_rows:
        area_row(str(row["area"]))["test_command_count"] += 1
    for item in areas.values():
        item["runner_keys"] = sorted(item["runner_keys"])[:40]
        item["surface_kinds"] = dict(sorted(item["surface_kinds"].items()))
    return dict(sorted(areas.items()))


def build_report(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    model_rows, model_sources = _build_model_rows(root)
    alignment_rows, alignment_sources = _build_alignment_rows(root)
    surface_rows, surface_sources = _build_surface_rows(root)
    test_rows, test_sources = _build_test_tier_rows(root)
    evidence_summary, evidence_sources = _build_evidence_summary(root)
    prompt_sources = [
        root / "skills" / "flowpilot" / "SKILL.md",
        root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "manifest.json",
        root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "prompts" / "manifest.json",
        *sorted((root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "cards").rglob("*.md")),
        *sorted((root / "skills" / "flowpilot" / "assets" / "runtime_kit" / "prompts").rglob("*.md")),
    ]
    source_records = _dedupe_sources(
        [
            *model_sources,
            *alignment_sources,
            *surface_sources,
            *test_sources,
            *evidence_sources,
            *prompt_sources,
            root / "scripts" / "flowguard_project_topology.py",
            root / "AGENTS.md",
        ],
        root,
    )
    generated_at_epoch = time.time()
    layer_counts = {
        "models": len(model_rows),
        "alignment_families": len(alignment_rows),
        "code_surfaces": len(surface_rows),
        "test_commands": len(test_rows),
        "evidence_summaries": len(evidence_summary),
        "known_bad_signals": sum(len(row.get("evidence", {}).get("known_bad") or []) for row in model_rows),
    }
    return {
        "artifact_type": "flowguard_project_topology",
        "generator_version": GENERATOR_VERSION,
        "generated_at_epoch": generated_at_epoch,
        "root": "<repo-root>",
        "orientation_only": True,
        "validation_warning": (
            "Topology guides project understanding only; it does not replace executable "
            "FlowGuard checks, tests, conformance replay, install audit, or release evidence."
        ),
        "layer_counts": layer_counts,
        "areas": _summarize_areas(model_rows, alignment_rows, surface_rows, test_rows),
        "models": model_rows,
        "model_test_alignment": alignment_rows,
        "code_surfaces": surface_rows,
        "test_commands": test_rows,
        "evidence_summary": evidence_summary,
        "sources": source_records,
    }
