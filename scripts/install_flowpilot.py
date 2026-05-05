"""Install or check FlowPilot and its declared Codex skill dependencies."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "flowpilot.dependencies.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def codex_home(args: argparse.Namespace) -> Path:
    if args.codex_home:
        return Path(args.codex_home).expanduser()
    env_name = load_manifest().get("install_policy", {}).get("codex_home_env", "CODEX_HOME")
    if os.environ.get(env_name):
        return Path(os.environ[env_name]).expanduser()
    return Path.home() / ".codex"


def skills_root(args: argparse.Namespace) -> Path:
    if args.skills_dir:
        return Path(args.skills_dir).expanduser()
    subdir = load_manifest().get("install_policy", {}).get("skills_subdir", "skills")
    return codex_home(args) / subdir


def skill_candidates(root: Path, install_name: str) -> list[Path]:
    return [root / install_name, root / ".system" / install_name]


def installed_skill_path(root: Path, install_name: str) -> Path | None:
    for candidate in skill_candidates(root, install_name):
        if (candidate / "SKILL.md").exists():
            return candidate
    return None


def iter_hashable_files(path: Path) -> list[Path]:
    ignored_dirs = {"__pycache__", ".git"}
    files: list[Path] = []
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in ignored_dirs for part in item.relative_to(path).parts):
            continue
        if item.suffix in {".pyc", ".pyo"}:
            continue
        files.append(item)
    return sorted(files, key=lambda item: item.relative_to(path).as_posix())


def directory_digest(path: Path) -> str:
    digest = hashlib.sha256()
    for item in iter_hashable_files(path):
        relpath = item.relative_to(path).as_posix()
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def has_local_repo_source(dependency: dict[str, Any]) -> bool:
    return (
        dependency.get("type") == "codex_skill"
        and bool(dependency.get("repo_path"))
        and (
            dependency.get("source", {}).get("kind") == "copy_from_this_repository"
            or dependency.get("install", {}).get("local_sync_mode") == "copy_from_repo"
        )
    )


def check_skill(root: Path, dependency: dict[str, Any]) -> dict[str, Any]:
    install_name = dependency.get("install_name") or dependency["name"]
    path = installed_skill_path(root, install_name)
    result: dict[str, Any] = {
        "name": dependency["name"],
        "type": "codex_skill",
        "installed": path is not None,
        "path": str(path) if path else None,
        "ok": path is not None,
    }
    if not path:
        return result
    text = (path / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    for check in dependency.get("checks", []):
        if check.get("kind") == "skill_file":
            expected = check.get("contains", "")
            if expected and expected not in text:
                result["ok"] = False
                result.setdefault("errors", []).append(f"missing expected text: {expected}")
    if has_local_repo_source(dependency):
        source_path = ROOT / dependency["repo_path"]
        result["source_path"] = str(source_path)
        if source_path.exists():
            source_digest = directory_digest(source_path)
            installed_digest = directory_digest(path)
            result["source_digest"] = source_digest
            result["installed_digest"] = installed_digest
            result["source_fresh"] = source_digest == installed_digest
            if source_digest != installed_digest:
                result["ok"] = False
                result.setdefault("errors", []).append(
                    "installed skill content differs from repository source"
                )
        else:
            result["ok"] = False
            result.setdefault("errors", []).append(f"missing repository source: {source_path}")
    return result


def check_python_package(dependency: dict[str, Any]) -> dict[str, Any]:
    module_name = dependency.get("import_name") or dependency["name"]
    result: dict[str, Any] = {
        "name": dependency["name"],
        "type": "python_package",
        "module": module_name,
        "ok": False,
    }
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["error"] = repr(exc)
        return result
    result["ok"] = True
    result["path"] = getattr(module, "__file__", None)
    for check in dependency.get("checks", []):
        attribute = check.get("attribute")
        if check.get("kind") == "python_import" and attribute:
            result[attribute] = getattr(module, attribute, "unknown")
    return result


def source_is_complete(source: dict[str, Any]) -> bool:
    if source.get("kind") != "github":
        return True
    if source.get("repo") and source.get("ref") and source.get("path"):
        return True
    return bool(source.get("url"))


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
    repo = f"{parts[0]}/{parts[1]}"
    ref = parts[3]
    path = "/".join(parts[4:])
    return repo, ref, path


def download_github_skill(source: dict[str, Any], destination: Path) -> None:
    repo, ref, subpath = parse_github_source(source)
    archive_url = f"https://github.com/{repo}/archive/{urllib.parse.quote(ref, safe='')}.zip"
    with tempfile.TemporaryDirectory(prefix="flowpilot-skill-") as tmp_name:
        tmp = Path(tmp_name)
        archive_path = tmp / "source.zip"
        with urllib.request.urlopen(archive_url, timeout=30) as response:
            archive_path.write_bytes(response.read())
        extract_root = tmp / "extract"
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extract_root)
        roots = [child for child in extract_root.iterdir() if child.is_dir()]
        if not roots:
            raise FileNotFoundError("GitHub archive did not contain a repository root")
        source_path = roots[0] / subpath
        if not (source_path / "SKILL.md").exists():
            raise FileNotFoundError(f"GitHub source did not contain {subpath}/SKILL.md")
        shutil.copytree(source_path, destination)


def copy_repo_skill(dependency: dict[str, Any], destination: Path) -> None:
    source_path = ROOT / dependency["repo_path"]
    if not (source_path / "SKILL.md").exists():
        raise FileNotFoundError(f"missing repository skill source: {source_path}")
    shutil.copytree(source_path, destination)


def install_skill(
    root: Path,
    dependency: dict[str, Any],
    *,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    install_name = dependency.get("install_name") or dependency["name"]
    destination = root / install_name
    existing = installed_skill_path(root, install_name)
    result: dict[str, Any] = {
        "name": dependency["name"],
        "destination": str(destination),
        "action": "none",
        "ok": True,
    }
    if existing and not force:
        result["action"] = "skip_existing"
        result["path"] = str(existing)
        return result
    if existing and force:
        system_root = (root / ".system").resolve()
        if system_root in existing.resolve().parents or existing.resolve() == system_root:
            result["ok"] = False
            result["action"] = "refuse_force_system_skill"
            return result
        result["action"] = "overwrite_existing"
    else:
        result["action"] = "install"

    if dry_run:
        result["dry_run"] = True
        return result

    root.mkdir(parents=True, exist_ok=True)
    if existing and force:
        resolved_root = root.resolve()
        resolved_existing = existing.resolve()
        if resolved_root not in resolved_existing.parents:
            raise RuntimeError(f"refusing to remove path outside skills root: {existing}")
        shutil.rmtree(existing)

    source = dependency.get("source", {})
    mode = dependency.get("install", {}).get("mode")
    if mode == "copy_from_repo" or source.get("kind") == "copy_from_this_repository":
        copy_repo_skill(dependency, destination)
    elif mode == "github_skill" or source.get("kind") == "github":
        if not source_is_complete(source):
            result["ok"] = False
            result["action"] = "missing_github_source"
            return result
        download_github_skill(source, destination)
    else:
        result["ok"] = False
        result["action"] = "not_installable"
    return result


def is_repo_owned_skill(dependency: dict[str, Any]) -> bool:
    return has_local_repo_source(dependency)


def dependency_status(root: Path, dependency: dict[str, Any]) -> dict[str, Any]:
    if dependency.get("type") == "python_package":
        result = check_python_package(dependency)
    elif dependency.get("type") == "codex_skill":
        result = check_skill(root, dependency)
    else:
        result = {
            "name": dependency.get("name", "unknown"),
            "ok": False,
            "error": "unknown dependency type",
        }
    result["required"] = bool(dependency.get("required", True))
    result["companion"] = bool(dependency.get("companion", False))
    if not result["ok"] and not result["required"]:
        result["severity"] = "warning"
    return result


def host_capability_status(root: Path, capability: dict[str, Any]) -> dict[str, Any]:
    provider = capability.get("codex_default_provider", {})
    install_name = provider.get("install_name", "")
    result: dict[str, Any] = {
        "id": capability.get("id", "unknown"),
        "type": "host_capability",
        "provider_kind": provider.get("kind", "unknown"),
        "available": False,
        "ok": True,
        "severity": "warning",
    }
    if provider.get("kind") != "codex_skill" or not install_name:
        result["detail"] = "no Codex skill provider declared"
        return result

    candidate_paths = []
    for relpath in provider.get("skill_path_candidates", []):
        candidate_paths.append(root / relpath)
    candidate_paths.extend(skill_candidates(root, install_name))

    markers = provider.get("accepted_markers", [])
    for candidate in candidate_paths:
        skill_file = candidate / "SKILL.md"
        if not skill_file.exists():
            continue
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        if markers and not any(marker in text for marker in markers):
            continue
        result["available"] = True
        result["path"] = str(candidate)
        result["provider"] = install_name
        result["detail"] = "Codex default provider found"
        return result

    result["provider"] = install_name
    result["detail"] = "Codex default provider not found; another host may map this capability differently"
    return result


def run_check_install() -> dict[str, Any]:
    import subprocess

    completed = subprocess.run(
        [sys.executable, "scripts/check_install.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check only. This is the default.")
    parser.add_argument("--install-missing", action="store_true", help="Install missing auto-installable skills.")
    parser.add_argument("--include-optional", action="store_true", help="With --install-missing, also install optional companion skills.")
    parser.add_argument(
        "--sync-repo-owned",
        action="store_true",
        help="Refresh missing or stale repository-owned Codex skills from this checkout.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions without changing files.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing non-system skill installs.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--codex-home", default="", help="Override CODEX_HOME.")
    parser.add_argument("--skills-dir", default="", help="Override the Codex skills directory.")
    parser.add_argument("--skip-self-check", action="store_true", help="Skip scripts/check_install.py after installation.")
    args = parser.parse_args()

    manifest = load_manifest()
    root = skills_root(args)
    result: dict[str, Any] = {
        "ok": True,
        "skills_root": str(root),
        "manifest": str(MANIFEST_PATH),
        "dependencies": [],
        "host_capabilities": [],
        "install_actions": [],
    }

    for dependency in manifest.get("dependencies", []):
        status = dependency_status(root, dependency)
        result["dependencies"].append(status)
        if args.sync_repo_owned and is_repo_owned_skill(dependency):
            if status.get("ok") and status.get("source_fresh") is True:
                result["install_actions"].append(
                    {
                        "name": dependency["name"],
                        "action": "already_fresh",
                        "ok": True,
                        "path": status.get("path"),
                    }
                )
                continue
            repo_copy_dependency = {
                **dependency,
                "source": {"kind": "copy_from_this_repository"},
                "install": {
                    **dependency.get("install", {}),
                    "mode": "copy_from_repo",
                },
            }
            action = install_skill(
                root,
                repo_copy_dependency,
                dry_run=args.dry_run,
                force=True,
            )
            result["install_actions"].append(action)
            if not action.get("ok"):
                result["ok"] = False
                continue
            if not args.dry_run:
                post_status = dependency_status(root, dependency)
                result["dependencies"].append({**post_status, "after_install": True})
                if not post_status.get("ok"):
                    result["ok"] = False
            continue
        if status.get("ok"):
            continue
        required = bool(status.get("required", True))

        install_cfg = dependency.get("install", {})
        should_install = (
            args.install_missing
            and bool(install_cfg.get("auto_install_missing"))
            and (required or args.include_optional)
        )
        if not should_install:
            if required:
                result["ok"] = False
            continue
        action = install_skill(root, dependency, dry_run=args.dry_run, force=args.force)
        result["install_actions"].append(action)
        if not action.get("ok"):
            result["ok"] = False
            continue
        if not args.dry_run:
            post_status = dependency_status(root, dependency)
            result["dependencies"].append({**post_status, "after_install": True})
            if not post_status.get("ok"):
                result["ok"] = False

    for capability in manifest.get("host_capabilities", []):
        result["host_capabilities"].append(host_capability_status(root, capability))

    if (args.install_missing or args.sync_repo_owned) and not args.dry_run and not args.skip_self_check:
        result["self_check"] = run_check_install()
        if not result["self_check"]["ok"]:
            result["ok"] = False

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"FlowPilot install check: {'ok' if result['ok'] else 'needs attention'}")
        print(f"Codex skills directory: {root}")
        for item in result["dependencies"]:
            status = "ok" if item.get("ok") else "missing"
            suffix = " after install" if item.get("after_install") else ""
            print(f"- {item.get('name')}: {status}{suffix}")
        for item in result["host_capabilities"]:
            status = "available" if item.get("available") else "not mapped"
            print(f"- capability {item.get('id')}: {status}")
        for action in result["install_actions"]:
            print(f"- action {action['name']}: {action['action']}")

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
