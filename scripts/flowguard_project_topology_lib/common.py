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


ROOT = Path(__file__).resolve().parents[2]
GENERATOR_VERSION = "1"
PUBLIC_ROOT_LABEL = "<repo-root>"
PUBLIC_PYTHON_LABEL = "python"
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


def _public_command_arg(value: str, root: Path = ROOT) -> str:
    text = str(value)
    lower = text.lower()
    if lower.endswith(("python.exe", "python")) and (":\\" in text or ":/" in text):
        return PUBLIC_PYTHON_LABEL
    root_text = str(root.resolve())
    root_posix = root.resolve().as_posix()
    if text == root_text or text == root_posix:
        return PUBLIC_ROOT_LABEL
    if text.startswith(root_text + "\\") or text.startswith(root_text + "/"):
        suffix = text[len(root_text) + 1 :].replace("\\", "/")
        return f"{PUBLIC_ROOT_LABEL}/{suffix}"
    if text.startswith(root_posix + "/"):
        suffix = text[len(root_posix) + 1 :]
        return f"{PUBLIC_ROOT_LABEL}/{suffix}"
    return text


def _public_command(command: Iterable[str], root: Path = ROOT) -> list[str]:
    return [_public_command_arg(item, root) for item in command]


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
