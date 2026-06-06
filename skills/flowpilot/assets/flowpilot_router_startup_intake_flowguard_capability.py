"""FlowGuard capability snapshot helpers for startup intake materialization."""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


_BOUND_ROUTER: ModuleType | None = None


def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get("_LOCAL_NAMES", set())
    for name, value in vars(router).items():
        if name.startswith("__") and name.endswith("__"):
            continue
        if name in local_names:
            continue
        current[name] = value


def _flowguard_capability_snapshot_path(router: ModuleType, run_root: Path) -> Path:
    _bind_router(router)
    return run_root / "flowguard" / "capability_snapshot.json"


def _portable_skill_search_roots(router: ModuleType, project_root: Path) -> list[Path]:
    _bind_router(router)
    candidates: list[Path] = []
    try:
        candidates.append(skill_root().parent)
    except Exception:
        pass
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "skills")
    candidates.append(Path.home() / ".codex" / "skills")
    candidates.append(project_root / "skills")
    roots: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.exists():
            roots.append(resolved)
    return roots


def _flowguard_route_classification(skill_name: str) -> dict[str, Any]:
    name = skill_name.lower()
    if name == "model-first-function-flow":
        return {
            "route_description": "Core model-first behavior and route-selection kernel.",
            "role_fit": ["project_manager", "flowguard_operator", "flowguard_operator"],
            "model_family_fit": ["product_behavior", "route_process", "cross_route_coordination"],
        }
    if "ui" in name:
        return {
            "route_description": "UI interaction behavior, visible control topology, and recovery-state modeling.",
            "role_fit": ["project_manager", "flowguard_operator"],
            "model_family_fit": ["ui_interaction", "product_behavior"],
        }
    if "development-process" in name:
        return {
            "route_description": "Staged development process, validation freshness, and done-claim modeling.",
            "role_fit": ["project_manager", "flowguard_operator"],
            "model_family_fit": ["route_process", "validation_evidence"],
        }
    if "code-structure" in name or "structure-mesh" in name:
        return {
            "route_description": "Architecture, module ownership, facade, and structure-governance modeling.",
            "role_fit": ["project_manager", "flowguard_operator", "flowguard_operator"],
            "model_family_fit": ["data_state", "route_hierarchy", "architecture"],
        }
    if "model-test" in name:
        return {
            "route_description": "Model obligations compared against ordinary tests and executable evidence.",
            "role_fit": ["project_manager", "flowguard_operator"],
            "model_family_fit": ["validation_evidence", "model_test_alignment"],
        }
    if "test-mesh" in name:
        return {
            "route_description": "Layered test hierarchy, slow-check freshness, and evidence-mesh modeling.",
            "role_fit": ["project_manager", "flowguard_operator"],
            "model_family_fit": ["validation_evidence", "test_hierarchy"],
        }
    if "model-mesh" in name:
        return {
            "route_description": "Parent/child model-family split, stale child evidence, and sibling coverage governance.",
            "role_fit": ["project_manager", "flowguard_operator", "flowguard_operator"],
            "model_family_fit": ["model_family_governance"],
        }
    if "model-miss" in name:
        return {
            "route_description": "Post-failure model-miss review and generalized bad-case modeling.",
            "role_fit": ["project_manager", "flowguard_operator", "flowguard_operator"],
            "model_family_fit": ["failure_recovery", "model_test_alignment"],
        }
    return {
        "route_description": "FlowGuard route available for PM-selected modeling coverage.",
        "role_fit": ["project_manager", "flowguard_operator", "flowguard_operator"],
        "model_family_fit": ["product_behavior", "route_process"],
    }


def _discover_flowguard_skill_routes(router: ModuleType, project_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    _bind_router(router)
    routes: list[dict[str, Any]] = []
    roots = _portable_skill_search_roots(router, project_root)
    for root in roots:
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_name = skill_dir.name
            if not (skill_name.startswith("flowguard-") or skill_name == "model-first-function-flow"):
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            classification = _flowguard_route_classification(skill_name)
            routes.append(
                {
                    "skill_name": skill_name,
                    "source_path": str(skill_md),
                    "source_hash_sha256": hashlib.sha256(skill_md.read_bytes()).hexdigest(),
                    "search_root": str(root),
                    **classification,
                }
            )
    deduped: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for route in routes:
        name = str(route.get("skill_name") or "")
        if name in seen_names:
            continue
        seen_names.add(name)
        deduped.append(route)
    return deduped, [str(root) for root in roots]


def _flowguard_import_snapshot() -> dict[str, Any]:
    try:
        import flowguard  # type: ignore
    except Exception as exc:
        return {"importable": False, "error": f"{type(exc).__name__}: {exc}", "python_executable": sys.executable}
    package_version = None
    try:
        package_version = importlib.metadata.version("flowguard")
    except importlib.metadata.PackageNotFoundError:
        package_version = None
    return {
        "importable": True,
        "schema_version": getattr(flowguard, "SCHEMA_VERSION", None),
        "module_path": str(Path(getattr(flowguard, "__file__", "") or "").resolve()),
        "package_version": package_version,
        "python_executable": sys.executable,
    }


def _write_flowguard_capability_snapshot(
    router: ModuleType,
    project_root: Path,
    run_root: Path,
    state: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    path = _flowguard_capability_snapshot_path(router, run_root)
    routes, search_roots = _discover_flowguard_skill_routes(router, project_root)
    snapshot = {
        "schema_version": "flowpilot.flowguard_capability_snapshot.v1",
        "snapshot_id": f"{state.get('run_id') or run_root.name}-flowguard-capability-snapshot",
        "run_id": state.get("run_id") or run_root.name,
        "generated_at": utc_now(),
        "generated_by_role_key": "router",
        "policy": {
            "flowguard_is_required_foundation": True,
            "ordinary_child_skill": False,
            "pm_must_read_before_product_modeling": True,
            "mid_run_upgrade_policy": "snapshot is fixed for this run; later FlowGuard upgrades apply to later runs",
        },
        "portable_resolution": {
            "hardcoded_user_path_required": False,
            "generator": "flowpilot_router_startup_seed",
            "skill_root_source": str(skill_root()),
            "search_roots": search_roots,
            "resolution_rule": "scan installed Codex skills and project-local skills on the current host at startup",
        },
        "flowguard_import": _flowguard_import_snapshot(),
        "capability_menu": [
            {"capability_id": "flowguard_startup_capability_snapshot", "required_before": "pm_product_architecture"},
            {"capability_id": "product_modeling_plan", "owned_by": "project_manager"},
            {"capability_id": "product_model_family_coverage", "owned_by": "flowguard_operator"},
            {"capability_id": "ordinary_child_skill_projection", "owned_by": "project_manager"},
            {"capability_id": "process_modeling_plan", "owned_by": "project_manager"},
            {"capability_id": "process_model_family_coverage", "owned_by": "flowguard_operator"},
            {"capability_id": "model_test_alignment", "owned_by": "project_manager"},
            {"capability_id": "final_modeling_coverage_ledger", "owned_by": "project_manager"},
        ],
        "skill_routes": routes,
        "pm_summary": {
            "must_read_before_product_modeling": True,
            "decide_model_family_count_before_flowguard_operator_task": True,
            "ordinary_child_skills_are_selected_after_product_model_family_acceptance": True,
            "process_modeling_plan_required_before_route_activation": True,
            "final_ledger_must_close_all_model_families": True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, snapshot)
    rel_path = project_relative(project_root, path)
    state["flowguard_capability_snapshot_path"] = rel_path
    state.setdefault("flags", {})["flowguard_capability_snapshot_written"] = True
    return {
        "path": rel_path,
        "skill_route_count": len(routes),
        "search_roots": search_roots,
        "flowguard_importable": snapshot["flowguard_import"]["importable"],
    }


__all__ = (
    "_flowguard_capability_snapshot_path",
    "_portable_skill_search_roots",
    "_flowguard_route_classification",
    "_discover_flowguard_skill_routes",
    "_flowguard_import_snapshot",
    "_write_flowguard_capability_snapshot",
)

_LOCAL_NAMES = set(globals())
