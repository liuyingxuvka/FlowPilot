"""Generate and check the FlowGuard project topology map.

The topology is an orientation artifact for mature FlowGuard projects. It
summarizes model runners, tests, code surfaces, result evidence, and known-bad
signals so agents can form project background before non-trivial work. It is
not validation evidence by itself.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_VERSION = "1"
DEFAULT_JSON_PATH = ROOT / "docs" / "flowguard_project_topology.json"
DEFAULT_MARKDOWN_PATH = ROOT / "docs" / "flowguard_project_topology.md"
ALIGNMENT_RESULT_PATH = ROOT / "simulations" / "flowpilot_model_test_alignment_results.json"
COVERAGE_RESULT_PATH = ROOT / "simulations" / "flowpilot_full_model_coverage_sweep_results.json"
MODEL_MATURATION_RESULT_PATH = ROOT / "simulations" / "flowpilot_model_maturation_results.json"
MODEL_MESH_RESULT_PATH = ROOT / "simulations" / "flowpilot_model_mesh_results.json"
MODEL_HIERARCHY_RESULT_PATH = ROOT / "simulations" / "flowpilot_model_hierarchy_results.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


AREA_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("startup", ("startup", "bootstrap", "intake")),
    ("material", ("material", "research")),
    ("packet", ("packet", "card", "ack", "work_packet", "role_work")),
    ("controller", ("controller", "receipt", "wait", "standby", "patrol")),
    ("route", ("route", "recursive", "frontier", "mutation")),
    ("review", ("reviewer", "challenge", "review")),
    ("closure", ("closure", "terminal", "final", "ledger")),
    ("model-mesh", ("model_mesh", "model_hierarchy", "maturation", "thin_parent")),
    ("model-test-alignment", ("model_test_alignment", "test_obligation", "coverage")),
    ("prompt-card", ("prompt", "card_instruction", "system_card", "runtime_kit")),
    ("install-validation", ("install", "smoke", "release", "public_release")),
    ("structure", ("structure", "facade", "split", "maintenance")),
)

IMPORTANT_RESULT_PATHS = (
    ALIGNMENT_RESULT_PATH,
    COVERAGE_RESULT_PATH,
    MODEL_MATURATION_RESULT_PATH,
    MODEL_MESH_RESULT_PATH,
    MODEL_HIERARCHY_RESULT_PATH,
)


def _rel(path: Path, root: Path = ROOT) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(_read_text(path))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        return {"__parse_error__": str(exc)}


def _source_record(path: Path, root: Path = ROOT) -> dict[str, Any]:
    try:
        stat = path.stat()
        return {
            "path": _rel(path, root),
            "exists": True,
            "mtime_ns": stat.st_mtime_ns,
            "size": stat.st_size,
        }
    except FileNotFoundError:
        return {
            "path": _rel(path, root),
            "exists": False,
            "mtime_ns": None,
            "size": None,
        }


def _dedupe_sources(paths: Iterable[Path], root: Path = ROOT) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in paths:
        try:
            rel = _rel(path, root)
        except ValueError:
            continue
        rows[rel] = _source_record(path, root)
    return [rows[key] for key in sorted(rows)]


def _runner_key(path: Path) -> str:
    name = path.stem
    if name.startswith("run_"):
        name = name[4:]
    if name.endswith("_checks"):
        name = name[:-7]
    return name


def _coverage_tier(key: str) -> str:
    try:
        from scripts import run_flowguard_coverage_sweep as sweep

        return sweep._coverage_tier(key)  # type: ignore[attr-defined]
    except Exception:
        return "unclassified_model_tier"


def _declared_result_path(path: Path, text: str) -> Path | None:
    try:
        from scripts import run_flowguard_coverage_sweep as sweep

        result = sweep._declared_result_path(path, text)  # type: ignore[attr-defined]
        if result is not None:
            return result
    except Exception:
        pass

    key = _runner_key(path)
    candidates = [
        path.parent / f"{key}_results.json",
        path.parent / f"{key}_model_only_results.json",
        path.parent / f"flowpilot_{key}_results.json",
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _model_path_for_key(key: str, runner_path: Path, text: str) -> Path | None:
    if key == "meta":
        candidate = runner_path.parent / "meta_model.py"
        return candidate if candidate.exists() else None
    if key == "capability":
        candidate = runner_path.parent / "capability_model.py"
        return candidate if candidate.exists() else None
    candidates = [
        runner_path.parent / f"{key}_model.py",
        runner_path.parent / f"flowpilot_{key}_model.py",
        runner_path.parent / f"{key}.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    model_imports = re.findall(r"import\s+([A-Za-z0-9_]+_model)\b", text)
    for module_name in model_imports:
        candidate = runner_path.parent / f"{module_name}.py"
        if candidate.exists():
            return candidate
    return None


def _classify_area(*values: str) -> str:
    haystack = " ".join(values).lower()
    for area, keywords in AREA_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return area
    return "other"


def _walk_counts(value: Any) -> dict[str, Any]:
    state_counts: list[int] = []
    edge_counts: list[int] = []
    ok_values: list[bool] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if key == "state_count" and isinstance(child, int):
                    state_counts.append(child)
                elif key == "edge_count" and isinstance(child, int):
                    edge_counts.append(child)
                elif key == "ok" and isinstance(child, bool):
                    ok_values.append(child)
                visit(child)
        elif isinstance(node, list):
            for child in node[:200]:
                visit(child)

    visit(value)
    return {
        "state_count": max(state_counts) if state_counts else None,
        "edge_count": max(edge_counts) if edge_counts else None,
        "ok": all(ok_values) if ok_values else None,
    }


def _collect_known_bad(value: Any, *, limit: int = 60) -> list[str]:
    labels: list[str] = []

    def add(label: Any) -> None:
        text = str(label)
        if text and text not in labels:
            labels.append(text)

    def visit(node: Any, path: str = "") -> None:
        if len(labels) >= limit:
            return
        if isinstance(node, Mapping):
            for key, child in node.items():
                key_text = str(key)
                lower = key_text.lower()
                child_path = f"{path}.{key_text}" if path else key_text
                if lower in {
                    "rejected_scenarios",
                    "negative_reject_labels_seen",
                    "known_bad_sanity_checks",
                } and isinstance(child, list):
                    for item in child[:limit]:
                        if isinstance(item, Mapping):
                            add(item.get("name") or item.get("scenario") or item.get("label") or child_path)
                        else:
                            add(item)
                elif "known_bad" in lower or "hazard" in lower:
                    if isinstance(child, Mapping):
                        for item_key in list(child.keys())[:limit]:
                            add(item_key)
                    elif isinstance(child, list):
                        for item in child[:limit]:
                            if isinstance(item, Mapping):
                                add(item.get("name") or item.get("scenario") or child_path)
                            else:
                                add(item)
                    else:
                        add(child_path)
                visit(child, child_path)
        elif isinstance(node, list):
            for child in node[:200]:
                visit(child, path)

    visit(value)
    return labels[:limit]


def _evidence_status(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {
            "present": False,
            "ok": None,
            "decision": "",
            "confidence": "",
            "full_coverage_ok": None,
            "release_convergence_ok": None,
            "finding_count": None,
        }
    counts = _walk_counts(payload)
    finding_count = payload.get("finding_count")
    if finding_count is None and isinstance(payload.get("findings"), list):
        finding_count = len(payload["findings"])
    return {
        "present": True,
        "ok": payload.get("ok", counts["ok"]),
        "decision": str(payload.get("decision") or payload.get("current", {}).get("decision") or ""),
        "confidence": str(payload.get("confidence") or payload.get("current", {}).get("confidence") or ""),
        "full_coverage_ok": payload.get("full_coverage_ok"),
        "release_convergence_ok": payload.get("release_convergence_ok"),
        "finding_count": finding_count,
        "state_count": counts["state_count"],
        "edge_count": counts["edge_count"],
        "known_bad": _collect_known_bad(payload),
    }


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
                    "command": command.command,
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
        "root": str(root),
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


def _path_arg(value: str, root: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        return root / path
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT))
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="write topology artifacts")
    build_parser.add_argument("--json-out", default=str(DEFAULT_JSON_PATH))
    build_parser.add_argument("--markdown-out", default=str(DEFAULT_MARKDOWN_PATH))
    build_parser.add_argument("--json", action="store_true", help="print the generated report")

    check_parser = subparsers.add_parser("check", help="check topology artifacts")
    check_parser.add_argument("--json-path", default=str(DEFAULT_JSON_PATH))
    check_parser.add_argument("--markdown-path", default=str(DEFAULT_MARKDOWN_PATH))
    check_parser.add_argument("--json", action="store_true", help="print the check report")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "build":
        report = write_topology(
            root,
            json_path=_path_arg(args.json_out, root),
            markdown_path=_path_arg(args.markdown_out, root),
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "json_path": _rel(_path_arg(args.json_out, root), root),
                        "markdown_path": _rel(_path_arg(args.markdown_out, root), root),
                        "layer_counts": report["layer_counts"],
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        return 0
    if args.command == "check":
        result = check_topology(
            root,
            json_path=_path_arg(args.json_path, root),
            markdown_path=_path_arg(args.markdown_path, root),
        )
        if args.json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
