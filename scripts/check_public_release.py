"""FlowPilot-only public release preflight.

This script checks the FlowPilot repository and dependency manifest before a
public GitHub release. It never commits, tags, pushes, packages, uploads, or
publishes companion skill repositories.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "flowpilot.dependencies.json"

PRIVATE_PATH_PREFIXES = (
    ".flowpilot/",
    ".flowguard/",
    "kb/",
    ".codex/",
)

PRIVATE_PATH_NAMES = {
    ".env",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
}

SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"C:\\Users\\liu_y", re.IGNORECASE),
)

VALIDATION_COMMANDS = (
    [sys.executable, "simulations/run_release_tooling_checks.py"],
    [sys.executable, "scripts/check_install.py"],
    [sys.executable, "scripts/smoke_autopilot.py", "--fast"],
)


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


def load_manifest(checks: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not MANIFEST_PATH.exists():
        add_check(checks, name="manifest_exists", ok=False, path=str(MANIFEST_PATH))
        return None
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        add_check(checks, name="manifest_json", ok=False, error=repr(exc))
        return None
    add_check(checks, name="manifest_json", ok=True, path=str(MANIFEST_PATH))
    return manifest


def git_tracked_files() -> tuple[list[str], str | None]:
    git = git_command()
    if git is None:
        return [], "git executable was not found"
    completed = subprocess.run(
        [git, "ls-files", "-z"],
        cwd=ROOT,
        text=False,
        capture_output=True,
    )
    if completed.returncode != 0:
        return [], completed.stderr.decode("utf-8", errors="replace")
    raw = completed.stdout.decode("utf-8", errors="replace")
    return [item for item in raw.split("\0") if item], None


def git_status_short() -> list[str]:
    git = git_command()
    if git is None:
        return ["git executable was not found"]
    completed = subprocess.run(
        [git, "status", "--short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return [completed.stderr.strip()]
    return [line for line in completed.stdout.splitlines() if line.strip()]


def git_command() -> str | None:
    found = shutil.which("git") or shutil.which("git.cmd") or shutil.which("git.exe")
    if found:
        return found
    codex_git = Path.home() / "AppData" / "Local" / "OpenAI" / "Codex" / "bin" / "git.cmd"
    if codex_git.exists():
        return str(codex_git)
    return None


def path_has_private_component(path: str) -> bool:
    normalized = path.replace("\\", "/")
    parts = set(normalized.split("/"))
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in PRIVATE_PATH_PREFIXES):
        return True
    return bool(parts & PRIVATE_PATH_NAMES)


def scan_tracked_privacy(checks: list[dict[str, Any]]) -> None:
    tracked, error = git_tracked_files()
    if error:
        add_check(checks, name="git_ls_files", ok=False, error=error)
        return
    add_check(checks, name="git_ls_files", ok=True, count=len(tracked))

    private_paths = [path for path in tracked if path_has_private_component(path)]
    add_check(
        checks,
        name="tracked_private_paths_absent",
        ok=not private_paths,
        paths=private_paths[:50],
        count=len(private_paths),
    )

    suspicious: list[dict[str, str]] = []
    for relpath in tracked:
        path = ROOT / relpath
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                suspicious.append({"path": relpath, "pattern": pattern.pattern})
                break
    add_check(
        checks,
        name="tracked_secret_patterns_absent",
        ok=not suspicious,
        matches=suspicious[:50],
        count=len(suspicious),
    )


def source_is_complete(source: dict[str, Any]) -> bool:
    if source.get("kind") != "github":
        return True
    return bool(
        (source.get("repo") and source.get("ref") and source.get("path"))
        or source.get("url")
    )


def parse_github_source(source: dict[str, Any]) -> tuple[str, str, str]:
    repo = source.get("repo", "").strip()
    ref = source.get("ref", "").strip()
    path = source.get("path", "").strip().strip("/")
    if repo and ref and path:
        return repo, ref, path

    url = source.get("url", "").strip()
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.netloc.lower() != "github.com" or len(parts) < 5 or parts[2] != "tree":
        raise ValueError("GitHub source must provide repo/ref/path or a github.com tree URL")
    return f"{parts[0]}/{parts[1]}", parts[3], "/".join(parts[4:])


def github_skill_raw_url(source: dict[str, Any]) -> str:
    repo, ref, path = parse_github_source(source)
    quoted_path = "/".join(urllib.parse.quote(part) for part in path.split("/"))
    return f"https://raw.githubusercontent.com/{repo}/{urllib.parse.quote(ref, safe='')}/{quoted_path}/SKILL.md"


def check_url(url: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "flowpilot-release-check"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            ok = 200 <= response.status < 300
            return ok, f"HTTP {response.status}"
    except Exception as exc:  # pragma: no cover - network diagnostic
        return False, repr(exc)


def validate_manifest(
    checks: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    skip_url_check: bool,
) -> None:
    dependencies = manifest.get("dependencies")
    if not isinstance(dependencies, list):
        add_check(checks, name="manifest_dependencies_list", ok=False)
        return
    add_check(checks, name="manifest_dependencies_list", ok=True, count=len(dependencies))

    seen: set[str] = set()
    duplicates: list[str] = []
    for dependency in dependencies:
        name = dependency.get("name", "")
        if name in seen:
            duplicates.append(name)
        seen.add(name)
    add_check(checks, name="manifest_dependency_names_unique", ok=not duplicates, duplicates=duplicates)

    for dependency in dependencies:
        name = dependency.get("name", "<missing>")
        dep_type = dependency.get("type")
        if dep_type not in {"codex_skill", "python_package"}:
            add_check(checks, name=f"dependency_type:{name}", ok=False, dependency_type=dep_type)
        source = dependency.get("source", {})
        source_kind = source.get("kind")
        if source_kind == "github":
            complete = source_is_complete(source)
            missing_is_blocker = dependency.get("release_check", {}).get("missing_source_is_blocker", False)
            add_check(
                checks,
                name=f"dependency_github_source:{name}",
                ok=complete or not missing_is_blocker,
                severity="error" if missing_is_blocker else "warning",
                source=source,
            )
            if complete and not skip_url_check:
                try:
                    raw_url = github_skill_raw_url(source)
                except Exception as exc:
                    add_check(checks, name=f"dependency_url_parse:{name}", ok=False, error=repr(exc))
                    continue
                ok, detail = check_url(raw_url)
                add_check(
                    checks,
                    name=f"dependency_skill_url:{name}",
                    ok=ok,
                    url=raw_url,
                    detail=detail,
                )
        elif source_kind == "copy_from_this_repository":
            repo_path = dependency.get("repo_path", "")
            ok = bool(repo_path) and (ROOT / repo_path / "SKILL.md").exists()
            add_check(checks, name=f"dependency_repo_skill:{name}", ok=ok, path=repo_path)
        elif source_kind in {"host_builtin", "python_environment"}:
            add_check(checks, name=f"dependency_source:{name}", ok=True, source_kind=source_kind)
        else:
            add_check(checks, name=f"dependency_source:{name}", ok=False, source_kind=source_kind)

    validate_host_capabilities(checks, manifest)


def validate_host_capabilities(checks: list[dict[str, Any]], manifest: dict[str, Any]) -> None:
    capabilities = manifest.get("host_capabilities", [])
    if not isinstance(capabilities, list):
        add_check(checks, name="manifest_host_capabilities_list", ok=False)
        return
    add_check(checks, name="manifest_host_capabilities_list", ok=True, count=len(capabilities))

    ids = {capability.get("id") for capability in capabilities if isinstance(capability, dict)}
    add_check(
        checks,
        name="host_capability:raster_image_generation_declared",
        ok="raster_image_generation" in ids,
    )

    for capability in capabilities:
        if not isinstance(capability, dict):
            add_check(checks, name="host_capability_entry_object", ok=False)
            continue
        cap_id = capability.get("id", "<missing>")
        provider = capability.get("codex_default_provider", {})
        other_host_contract = capability.get("other_host_contract", {})
        markers = provider.get("accepted_markers", [])
        add_check(
            checks,
            name=f"host_capability_codex_provider:{cap_id}",
            ok=provider.get("kind") == "codex_skill" and bool(provider.get("install_name")),
            provider=provider,
        )
        add_check(
            checks,
            name=f"host_capability_other_host_contract:{cap_id}",
            ok=bool(other_host_contract.get("provider_name_is_host_specific"))
            and bool(other_host_contract.get("requirement"))
            and bool(other_host_contract.get("evidence")),
        )
        add_check(
            checks,
            name=f"host_capability_provider_markers:{cap_id}",
            ok=isinstance(markers, list) and bool(markers),
            markers=markers,
        )


def run_validation(checks: list[dict[str, Any]]) -> None:
    for command in VALIDATION_COMMANDS:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        add_check(
            checks,
            name="validation:" + " ".join(command[1:]),
            ok=completed.returncode == 0,
            returncode=completed.returncode,
            stdout_tail=completed.stdout[-4000:],
            stderr_tail=completed.stderr[-4000:],
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--skip-url-check", action="store_true", help="Skip network checks for dependency SKILL.md URLs.")
    parser.add_argument("--skip-validation", action="store_true", help="Skip repository validation commands.")
    parser.add_argument("--require-clean", action="store_true", help="Fail if git status is not clean.")
    args = parser.parse_args()

    checks: list[dict[str, Any]] = []
    manifest = load_manifest(checks)
    scan_tracked_privacy(checks)

    dirty = git_status_short()
    add_check(
        checks,
        name="git_worktree_clean",
        ok=not dirty,
        severity="error" if args.require_clean else "warning",
        dirty=dirty[:100],
        count=len(dirty),
    )

    if manifest is not None:
        validate_manifest(checks, manifest, skip_url_check=args.skip_url_check)

    if not args.skip_validation:
        run_validation(checks)

    errors = [check for check in checks if not check["ok"] and check.get("severity") != "warning"]
    warnings = [check for check in checks if not check["ok"] and check.get("severity") == "warning"]
    result = {
        "ok": not errors,
        "scope": "flowpilot_repository_only",
        "no_companion_publish_authority": True,
        "checks": checks,
        "error_count": len(errors),
        "warning_count": len(warnings),
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"FlowPilot public release check: {'ok' if result['ok'] else 'blocked'}")
        print("Scope: FlowPilot repository only; companion skills are never published by this tool.")
        print(f"Errors: {len(errors)}")
        print(f"Warnings: {len(warnings)}")
        for check in errors[:20]:
            print(f"- error {check['name']}")
        for check in warnings[:20]:
            print(f"- warning {check['name']}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
