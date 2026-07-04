"""Rendering, writing, and checking for FlowGuard project topology."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from flowguard_project_topology_lib.collectors import build_report
from flowguard_project_topology_lib.common import (
    DEFAULT_JSON_PATH,
    DEFAULT_MARKDOWN_PATH,
    GENERATOR_VERSION,
    ROOT,
    _read_json,
    _rel,
)


def _first(values: Iterable[dict[str, Any]], count: int = 10) -> list[dict[str, Any]]:
    return list(values)[:count]


def render_markdown(report: Mapping[str, Any]) -> str:
    counts = report["layer_counts"]
    lines = [
        "# FlowGuard Project Topology",
        "",
        "This generated map gives agents a project-level background structure for FlowGuard-heavy work.",
        "It is orientation only; it is not validation evidence.",
        "",
        "## Summary",
        "",
        f"- Model runners: {counts['models']}",
        f"- Model-test alignment families: {counts['alignment_families']}",
        f"- Code surfaces: {counts['code_surfaces']}",
        f"- Test commands: {counts['test_commands']}",
        f"- Evidence summaries: {counts['evidence_summaries']}",
        f"- Known-bad/risk labels surfaced: {counts['known_bad_signals']}",
        "",
        "## Area Map",
        "",
        "| Area | Models | Alignment families | Code surfaces | Test commands | Known-bad labels |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for area, item in report["areas"].items():
        lines.append(
            f"| `{area}` | {item['model_count']} | {item['alignment_family_count']} | "
            f"{item['code_surface_count']} | {item['test_command_count']} | {item['known_bad_count']} |"
        )

    lines.extend(["", "## Evidence Boundaries", ""])
    lines.append(report["validation_warning"])
    lines.extend(
        [
            "",
            "Agents may use this map to choose which model, test, and code areas to inspect.",
            "Completion and readiness claims still need the owning FlowGuard checks, tests, result artifacts, install audits, and freshness evidence.",
            "",
            "## Key Evidence Summaries",
            "",
            "| Artifact | Path | OK | Decision | Confidence | Findings |",
            "| --- | --- | --- | --- | --- | ---: |",
        ]
    )
    for name, item in report["evidence_summary"].items():
        evidence = item["evidence"]
        lines.append(
            f"| `{name}` | `{item['path']}` | {evidence.get('ok')} | "
            f"`{evidence.get('decision') or ''}` | `{evidence.get('confidence') or ''}` | "
            f"{evidence.get('finding_count')} |"
        )

    lines.extend(["", "## Model Runner Samples", ""])
    for row in _first(report["models"], 25):
        known_bad = row["evidence"].get("known_bad") or []
        suffix = f"; known-bad: {', '.join(known_bad[:3])}" if known_bad else ""
        lines.append(
            f"- `{row['runner_key']}` ({row['area']}, {row['coverage_tier']}): "
            f"`{row['runner_path']}` -> `{row.get('result_path') or 'no result'}`{suffix}"
        )

    lines.extend(["", "## Alignment Families", ""])
    for row in report["model_test_alignment"]:
        lines.append(
            f"- `{row['family']}` ({row['area']}): {row['obligation_count']} obligations, "
            f"{row['test_evidence_count']} test evidence rows"
        )

    lines.extend(["", "## Maintenance Rule", ""])
    lines.append(
        "When FlowGuard models, runners, result paths, test registries, code ownership surfaces, "
        "prompt/card boundaries, or validation readiness surfaces change, rebuild and check this topology."
    )
    lines.append("")
    return "\n".join(lines)


def _required_layer_findings(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    counts = report.get("layer_counts", {})
    required = {
        "models": "model_layer_missing",
        "alignment_families": "alignment_layer_missing",
        "code_surfaces": "code_layer_missing",
        "test_commands": "test_layer_missing",
        "evidence_summaries": "evidence_layer_missing",
        "known_bad_signals": "known_bad_layer_missing",
    }
    findings: list[dict[str, Any]] = []
    for field, code in required.items():
        if int(counts.get(field) or 0) <= 0:
            findings.append({"code": code, "field": field, "message": f"required topology layer {field} is empty"})
    return findings


def check_topology(
    root: Path = ROOT,
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    markdown_path: Path = DEFAULT_MARKDOWN_PATH,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    if not json_path.exists():
        findings.append({"code": "topology_json_missing", "path": _rel(json_path, root)})
    if not markdown_path.exists():
        findings.append({"code": "topology_markdown_missing", "path": _rel(markdown_path, root)})
    payload = _read_json(json_path)
    if not isinstance(payload, Mapping):
        findings.append({"code": "topology_json_invalid", "path": _rel(json_path, root)})
        return {"ok": False, "findings": findings}
    raw_json = json_path.read_text(encoding="utf-8", errors="replace")
    if "C:\\\\Users\\\\" in raw_json or "C:/Users/" in raw_json or "C:\\Users\\" in raw_json:
        findings.append({"code": "topology_local_path_leak", "path": _rel(json_path, root)})
    if payload.get("generator_version") != GENERATOR_VERSION:
        findings.append(
            {
                "code": "topology_generator_version_mismatch",
                "expected": GENERATOR_VERSION,
                "actual": payload.get("generator_version"),
            }
        )
    if payload.get("orientation_only") is not True:
        findings.append({"code": "topology_orientation_boundary_missing"})
    findings.extend(_required_layer_findings(payload))

    for source in payload.get("sources", []):
        if not isinstance(source, Mapping):
            continue
        relpath = str(source.get("path") or "")
        current = root / relpath
        if not current.exists():
            findings.append({"code": "topology_source_missing", "path": relpath})
            continue
        stat = current.stat()
        if source.get("mtime_ns") != stat.st_mtime_ns or source.get("size") != stat.st_size:
            findings.append(
                {
                    "code": "topology_source_stale",
                    "path": relpath,
                    "expected_mtime_ns": source.get("mtime_ns"),
                    "actual_mtime_ns": stat.st_mtime_ns,
                    "expected_size": source.get("size"),
                    "actual_size": stat.st_size,
                }
            )
    return {
        "ok": not findings,
        "findings": findings,
        "json_path": _rel(json_path, root),
        "markdown_path": _rel(markdown_path, root),
        "source_count": len(payload.get("sources", [])),
        "layer_counts": payload.get("layer_counts", {}),
    }


def write_topology(
    root: Path = ROOT,
    *,
    json_path: Path = DEFAULT_JSON_PATH,
    markdown_path: Path = DEFAULT_MARKDOWN_PATH,
) -> dict[str, Any]:
    report = build_report(root)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    return report
