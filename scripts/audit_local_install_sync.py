"""Audit repository source, local Codex skill installs, and Cockpit source state."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import install_flowpilot


ROOT = Path(__file__).resolve().parents[1]

COCKPIT_SOURCE_FILES = [
    "flowpilot_cockpit/__init__.py",
    "flowpilot_cockpit/__main__.py",
    "flowpilot_cockpit/app.py",
    "flowpilot_cockpit/i18n.py",
    "flowpilot_cockpit/models.py",
    "flowpilot_cockpit/state_reader.py",
    "flowpilot_cockpit/styles.py",
    "tests/test_flowpilot_cockpit_i18n.py",
    "tests/test_flowpilot_cockpit_state_reader.py",
]


def add_check(
    checks: list[dict[str, Any]],
    *,
    name: str,
    ok: bool,
    severity: str = "error",
    **extra: Any,
) -> None:
    check = {"name": name, "ok": ok, "severity": severity}
    check.update(extra)
    checks.append(check)


def run_git(args: list[str]) -> tuple[int, str, str]:
    git = shutil.which("git") or shutil.which("git.cmd") or shutil.which("git.exe")
    if not git:
        codex_git = Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin" / "git.cmd"
        git = str(codex_git) if codex_git.exists() else ""
    if not git:
        return 127, "", "git executable was not found"
    completed = subprocess.run(
        [git, *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return completed.returncode, completed.stdout, completed.stderr


def tracked_files() -> tuple[set[str], str | None]:
    returncode, stdout, stderr = run_git(["ls-files"])
    if returncode != 0:
        return set(), stderr.strip() or "git ls-files failed"
    return {line.strip().replace("\\", "/") for line in stdout.splitlines() if line.strip()}, None


def parse_skill_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"(?m)^name:\s*[\"']?([^\"'\r\n]+)", text)
    return match.group(1).strip() if match else "<missing>"


def installed_skill_names(root: Path) -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = defaultdict(list)
    if not root.exists():
        return {}
    for skill_file in sorted(root.glob("**/SKILL.md")):
        relpath = skill_file.parent.relative_to(root).as_posix()
        by_name[parse_skill_name(skill_file)].append(relpath)
    return dict(by_name)


def repo_owned_dependencies(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dependency
        for dependency in manifest.get("dependencies", [])
        if install_flowpilot.is_repo_owned_skill(dependency)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME.")
    parser.add_argument("--skills-dir", default="", help="Override the Codex skills directory.")
    args = parser.parse_args()

    manifest = install_flowpilot.load_manifest()
    skills_root = install_flowpilot.skills_root(args)
    result: dict[str, Any] = {
        "ok": True,
        "repo_root": str(ROOT),
        "skills_root": str(skills_root),
        "checks": [],
        "dependencies": [],
    }
    checks: list[dict[str, Any]] = result["checks"]

    for dependency in manifest.get("dependencies", []):
        status = install_flowpilot.dependency_status(skills_root, dependency)
        result["dependencies"].append(status)
        if status.get("required", True) and not status.get("ok", False):
            result["ok"] = False
        if dependency in repo_owned_dependencies(manifest):
            fresh = bool(status.get("ok")) and status.get("source_fresh") is True
            add_check(
                checks,
                name=f"repo_owned_skill_fresh:{dependency['name']}",
                ok=fresh,
                path=status.get("path"),
                source_path=status.get("source_path"),
            )
            if not fresh:
                result["ok"] = False

    by_name = installed_skill_names(skills_root)
    duplicates = {name: paths for name, paths in by_name.items() if len(paths) > 1}
    add_check(checks, name="installed_skill_names_unique", ok=not duplicates, duplicates=duplicates)
    if duplicates:
        result["ok"] = False

    tracked, git_error = tracked_files()
    if git_error:
        add_check(checks, name="git_tracked_files_available", ok=False, error=git_error)
        result["ok"] = False
    else:
        add_check(checks, name="git_tracked_files_available", ok=True, count=len(tracked))
        missing = [path for path in COCKPIT_SOURCE_FILES if path not in tracked]
        add_check(
            checks,
            name="cockpit_source_files_tracked",
            ok=not missing,
            missing=missing,
            expected=COCKPIT_SOURCE_FILES,
        )
        if missing:
            result["ok"] = False

    cockpit_missing_on_disk = [path for path in COCKPIT_SOURCE_FILES if not (ROOT / path).exists()]
    add_check(
        checks,
        name="cockpit_source_files_exist",
        ok=not cockpit_missing_on_disk,
        missing=cockpit_missing_on_disk,
    )
    if cockpit_missing_on_disk:
        result["ok"] = False

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"FlowPilot local install sync audit: {'ok' if result['ok'] else 'needs attention'}")
        print(f"Repository: {ROOT}")
        print(f"Codex skills: {skills_root}")
        for check in checks:
            status = "ok" if check["ok"] else check["severity"]
            print(f"- {check['name']}: {status}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
