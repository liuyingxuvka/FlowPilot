"""Path, time, and runtime-kit helpers for the FlowPilot router."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flowpilot_router_errors import RouterError


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc_timestamp(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_kit_source() -> Path:
    return Path(__file__).resolve().parent / "runtime_kit"


def _copy_runtime_kit_into_run_root(run_root: Path) -> None:
    source = runtime_kit_source()
    target = run_root / "runtime_kit"
    try:
        target.resolve().relative_to(run_root.resolve())
    except ValueError as exc:
        raise RouterError(f"runtime kit target outside run root: {target}") from exc
    if target.name != "runtime_kit":
        raise RouterError(f"refusing to replace unexpected runtime kit target: {target}")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))


def legacy_bootstrap_state_path(project_root: Path) -> Path:
    return project_root / ".flowpilot" / "bootstrap" / "startup_state.json"


def run_bootstrap_state_path(run_root: Path) -> Path:
    return run_root / "bootstrap" / "startup_state.json"


def bootstrap_state_path(project_root: Path, state: dict[str, Any] | None = None) -> Path:
    if state and state.get("run_root"):
        return run_bootstrap_state_path(project_root / str(state["run_root"]))
    from flowpilot_router_io_json import read_json_if_exists

    current = read_json_if_exists(project_root / ".flowpilot" / "current.json")
    raw = current.get("startup_bootstrap_path")
    if raw:
        return project_root / str(raw)
    raw_root = current.get("current_run_root") or current.get("active_run_root") or current.get("run_root")
    if raw_root:
        candidate = run_bootstrap_state_path(project_root / str(raw_root))
        if candidate.exists():
            return candidate
    return legacy_bootstrap_state_path(project_root)


def project_relative(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise RouterError(f"path is outside project root: {path}") from exc


def _project_root_from_run_root(run_root: Path) -> Path:
    resolved = run_root.resolve()
    if resolved.parent.name == "runs" and resolved.parent.parent.name == ".flowpilot":
        return resolved.parent.parent.parent
    return resolved.parent


def _flowpilot_runtime_entrypoint_ref(project_root: Path) -> str:
    runtime_path = Path(__file__).resolve().with_name("flowpilot_runtime.py")
    try:
        return project_relative(project_root, runtime_path)
    except RouterError:
        return str(runtime_path)
