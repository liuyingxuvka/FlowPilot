"""Generate the FlowPilot maintainability map."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC_PATH = ROOT / "simulations" / "flowpilot_model_test_alignment_results.json"

THRESHOLDS = {
    "runtime_owner_module_lines": 450,
    "runtime_facade_lines": 700,
    "script_entry_lines": 450,
    "test_file_watch_lines": 900,
    "model_file_watch_lines": 1600,
}

RUNTIME_FACADES = (
    "skills/flowpilot/assets/flowpilot_router.py",
    "skills/flowpilot/assets/flowpilot_paths.py",
    "skills/flowpilot/assets/flowpilot_packets.py",
    "skills/flowpilot/assets/flowpilot_outputs.py",
    "skills/flowpilot/assets/flowpilot_runtime.py",
)

SCRIPT_ENTRYPOINTS = (
    "scripts/check_install.py",
    "scripts/install_flowpilot.py",
    "scripts/run_test_tier.py",
    "scripts/smoke_autopilot.py",
    "scripts/audit_local_install_sync.py",
    "scripts/run_flowguard_coverage_sweep.py",
    "scripts/flowpilot_maintenance_map.py",
)

MODEL_FACADES = (
    "simulations/capability_model.py",
    "simulations/meta_model.py",
    "simulations/flowpilot_structure_maintenance_model.py",
    "simulations/flowpilot_router_facade_split_model.py",
    "simulations/flowpilot_model_test_alignment_source_contracts.py",
)

CURRENT_MAINTENANCE_DECISIONS = (
    "Runtime owner modules are under the StructureMesh line threshold; do not split runtime again without a matching model block and external contract test.",
    "Test-tier command definitions are split into stable command-group modules while scripts/test_tier/definitions.py remains the compatibility facade.",
    "Router facade split, structure-maintenance, and source-contract alignment models keep their old import paths while large catalogs move into helper modules.",
    "Large router-runtime tests stay as watchlist items in this pass; split them only by externally visible contract family and after fixture ownership is clear.",
    "Remaining large install and defect scripts stay as watchlist items because they are behavior-bearing command surfaces, not pure catalog moves.",
)


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8", errors="replace").splitlines())


def _py_files(root: Path, relative_dir: str) -> list[Path]:
    base = root / relative_dir
    if not base.exists():
        return []
    return sorted(path for path in base.rglob("*.py") if "__pycache__" not in path.parts)


def _file_row(path: Path, root: Path, *, threshold: int | None = None) -> dict[str, Any]:
    lines = _line_count(path)
    row = {"path": _rel(path, root), "lines": lines}
    if threshold is not None:
        row["threshold"] = threshold
        row["over_threshold"] = lines > threshold
    return row


def _summarize_files(
    paths: Iterable[Path],
    root: Path,
    *,
    threshold: int | None = None,
) -> dict[str, Any]:
    rows = [_file_row(path, root, threshold=threshold) for path in paths]
    rows.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
    over_threshold = [row for row in rows if row.get("over_threshold")]
    return {
        "file_count": len(rows),
        "total_lines": sum(int(row["lines"]) for row in rows),
        "largest": rows[:20],
        "over_threshold_count": len(over_threshold),
        "over_threshold": over_threshold,
    }


def _load_diagnostic(root: Path) -> dict[str, Any]:
    path = root / "simulations" / "flowpilot_model_test_alignment_results.json"
    if not path.exists():
        return {
            "path": _rel(path, root),
            "present": False,
            "full_coverage_ok": False,
            "full_diagnostic_ok": False,
            "gap_surface_count": None,
            "covered_surface_count": None,
            "deferred_structure_split_count": None,
            "known_bad_ok": None,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    full = payload.get("full_model_test_code_diagnostic") or {}
    return {
        "path": _rel(path, root),
        "present": True,
        "alignment_ok": payload.get("alignment_ok"),
        "full_coverage_ok": payload.get("full_coverage_ok"),
        "full_diagnostic_ok": payload.get("full_diagnostic_ok"),
        "known_bad_ok": full.get("known_bad_ok"),
        "covered_surface_count": full.get("covered_surface_count"),
        "gap_surface_count": full.get("gap_surface_count"),
        "deferred_structure_split_count": full.get("deferred_structure_split_count"),
        "diagnostic_boundary": payload.get("full_diagnostic_boundary") or full.get("diagnostic_boundary"),
    }


def _load_test_tiers() -> dict[str, Any]:
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from scripts.test_tier.definitions import commands_for_tier, tier_names

    tiers: dict[str, Any] = {}
    for tier in tier_names():
        commands = commands_for_tier(tier)
        tiers[tier] = {
            "command_count": len(commands),
            "long_running_count": sum(1 for command in commands if command.long_running),
            "release_only_count": sum(1 for command in commands if command.release_only),
            "background_recommended_count": sum(1 for command in commands if command.background_recommended),
            "commands": [command.name for command in commands],
        }
    return {"tier_names": list(tier_names()), "tiers": tiers}


def build_report(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    runtime_files = _py_files(root, "skills/flowpilot/assets")
    runtime_facade_paths = [root / path for path in RUNTIME_FACADES if (root / path).exists()]
    runtime_facade_set = {path.resolve() for path in runtime_facade_paths}
    runtime_owner_paths = [
        path
        for path in runtime_files
        if path.resolve() not in runtime_facade_set and path.name.startswith("flowpilot_router_")
    ]
    script_files = _py_files(root, "scripts")
    script_entry_paths = [root / path for path in SCRIPT_ENTRYPOINTS if (root / path).exists()]
    model_files = _py_files(root, "simulations")
    test_files = _py_files(root, "tests")
    model_facade_paths = [root / path for path in MODEL_FACADES if (root / path).exists()]

    return {
        "read_only": True,
        "root": str(root),
        "thresholds": dict(THRESHOLDS),
        "categories": {
            "runtime_assets": _summarize_files(runtime_files, root),
            "simulations": _summarize_files(model_files, root, threshold=THRESHOLDS["model_file_watch_lines"]),
            "scripts": _summarize_files(script_files, root, threshold=THRESHOLDS["script_entry_lines"]),
            "tests": _summarize_files(test_files, root, threshold=THRESHOLDS["test_file_watch_lines"]),
        },
        "runtime_owner_modules": _summarize_files(
            runtime_owner_paths,
            root,
            threshold=THRESHOLDS["runtime_owner_module_lines"],
        ),
        "facades": {
            "runtime": [_file_row(path, root, threshold=THRESHOLDS["runtime_facade_lines"]) for path in runtime_facade_paths],
            "models": [_file_row(path, root, threshold=THRESHOLDS["model_file_watch_lines"]) for path in model_facade_paths],
        },
        "script_entrypoints": [
            _file_row(path, root, threshold=THRESHOLDS["script_entry_lines"]) for path in script_entry_paths
        ],
        "test_tiers": _load_test_tiers(),
        "diagnostic": _load_diagnostic(root),
        "current_maintenance_decisions": list(CURRENT_MAINTENANCE_DECISIONS),
        "recommended_next_split_rules": [
            "Split runtime only when a model block, public facade, and external contract test already agree.",
            "Prefer catalog/data extraction for oversized model files; keep old model imports as facades.",
            "Split scripts only around stable command groups or install-check manifests; preserve CLI behavior.",
            "Split tests by externally visible contract family before moving internal fixtures.",
        ],
    }


def _format_row(row: dict[str, Any]) -> str:
    marker = " over-threshold" if row.get("over_threshold") else ""
    return f"- `{row['path']}`: {row['lines']} lines{marker}"


def render_markdown(report: dict[str, Any]) -> str:
    diagnostic = report["diagnostic"]
    lines = [
        "# FlowPilot Maintenance Map",
        "",
        "This generated map records the current model-code-test maintenance surface for FlowPilot.",
        "",
        "## Summary",
        "",
        f"- Runtime asset files: {report['categories']['runtime_assets']['file_count']}",
        f"- Runtime owner modules: {report['runtime_owner_modules']['file_count']}",
        f"- Script files: {report['categories']['scripts']['file_count']}",
        f"- Model files: {report['categories']['simulations']['file_count']}",
        f"- Test files: {report['categories']['tests']['file_count']}",
        f"- Model-test-code diagnostic: full coverage={diagnostic.get('full_coverage_ok')}, "
        f"gaps={diagnostic.get('gap_surface_count')}, covered={diagnostic.get('covered_surface_count')}",
        "",
        "## Runtime Owner Modules",
        "",
        f"Threshold: {report['thresholds']['runtime_owner_module_lines']} lines.",
    ]
    if report["runtime_owner_modules"]["over_threshold"]:
        lines.extend(_format_row(row) for row in report["runtime_owner_modules"]["over_threshold"])
    else:
        lines.append("- No runtime owner module exceeds the threshold.")

    lines.extend(["", "Largest runtime owner modules:", ""])
    lines.extend(_format_row(row) for row in report["runtime_owner_modules"]["largest"][:10])

    lines.extend(["", "## Facades", "", "Runtime facades:"])
    lines.extend(_format_row(row) for row in report["facades"]["runtime"])
    lines.extend(["", "Model facades and parent models:"])
    lines.extend(_format_row(row) for row in report["facades"]["models"])

    lines.extend(["", "## Script Entrypoints", ""])
    lines.extend(_format_row(row) for row in report["script_entrypoints"])

    lines.extend(["", "## Large-File Pressure", ""])
    for category in ("simulations", "scripts", "tests"):
        summary = report["categories"][category]
        lines.append(f"### {category}")
        if summary["over_threshold"]:
            lines.extend(_format_row(row) for row in summary["over_threshold"][:20])
        else:
            lines.append("- No files exceed the watch threshold.")
        lines.append("")

    lines.extend(["## Test Tiers", ""])
    for tier, detail in report["test_tiers"]["tiers"].items():
        lines.append(
            f"- `{tier}`: {detail['command_count']} commands, "
            f"{detail['long_running_count']} long-running, "
            f"{detail['release_only_count']} release-only"
        )

    lines.extend(["", "## Split Rules", ""])
    lines.extend(["Current decisions:"])
    lines.extend(f"- {decision}" for decision in report["current_maintenance_decisions"])
    lines.extend(["", "Future rules:"])
    lines.extend(f"- {rule}" for rule in report["recommended_next_split_rules"])
    lines.append("")
    return "\n".join(lines)


def write_report(root: Path = ROOT, *, json_out: Path | None = None, markdown_out: Path | None = None) -> dict[str, Any]:
    report = build_report(root)
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if markdown_out is not None:
        markdown_out.parent.mkdir(parents=True, exist_ok=True)
        markdown_out.write_text(render_markdown(report), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print the maintenance map as JSON.")
    parser.add_argument("--json-out", type=Path, help="Write the JSON maintenance map to a file.")
    parser.add_argument("--markdown-out", type=Path, help="Write the Markdown maintenance map to a file.")
    args = parser.parse_args(argv)

    report = write_report(ROOT, json_out=args.json_out, markdown_out=args.markdown_out)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.json_out is None and args.markdown_out is None:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
