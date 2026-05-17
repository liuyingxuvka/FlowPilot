"""Retired-path, backup, and result JSON checks."""

from __future__ import annotations

import json

from .common import JSON_FILES, OPTIONAL_RUNTIME_JSON_FILES, RETIRED_PATHS, ROOT


def run_checks(result: dict[str, object]) -> None:
    legacy_skill_dir = ROOT / "skills/flowguard-project-autopilot"
    legacy_absent = not legacy_skill_dir.exists()
    result["checks"].append(
        {"name": "legacy_skill_dir_absent", "ok": legacy_absent}
    )
    if not legacy_absent:
        result["ok"] = False

    for relpath in RETIRED_PATHS:
        absent = not (ROOT / relpath).exists()
        result["checks"].append({"name": f"retired_path_absent:{relpath}", "ok": absent})
        if not absent:
            result["ok"] = False

    backup_root = ROOT / "backups"
    second_backup_manifests = []
    if backup_root.exists():
        for manifest_path in backup_root.glob("flowpilot-20260504-second-backup-*/BACKUP_MANIFEST.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            label = str(manifest.get("label", ""))
            if "SECOND BACKUP" in label and "do not delete" in label.lower():
                zip_path = manifest_path.parent.with_suffix(".zip")
                second_backup_manifests.append(
                    {
                        "manifest": str(manifest_path.relative_to(ROOT)),
                        "zip": str(zip_path.relative_to(ROOT)),
                        "zip_exists": zip_path.exists(),
                    }
                )
    second_backup_ok = bool(second_backup_manifests) and all(item["zip_exists"] for item in second_backup_manifests)
    result["checks"].append(
        {
            "name": "flowpilot_second_backup_preserved",
            "ok": second_backup_ok,
            "backups": second_backup_manifests,
        }
    )
    if not second_backup_ok:
        result["ok"] = False

    for relpath in JSON_FILES:
        path = ROOT / relpath
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_ok = True
            error = None
        except Exception as exc:  # pragma: no cover - diagnostic script
            json_ok = False
            error = repr(exc)
        check = {"name": f"json:{relpath}", "ok": json_ok}
        if error:
            check["error"] = error
        result["checks"].append(check)
        if not json_ok:
            result["ok"] = False

    for relpath in OPTIONAL_RUNTIME_JSON_FILES:
        path = ROOT / relpath
        if not path.exists():
            result["checks"].append(
                {"name": f"optional_json:{relpath}", "ok": True, "present": False}
            )
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            json_ok = True
            error = None
        except Exception as exc:  # pragma: no cover - diagnostic script
            json_ok = False
            error = repr(exc)
        check = {"name": f"optional_json:{relpath}", "ok": json_ok, "present": True}
        if error:
            check["error"] = error
        result["checks"].append(check)
        if not json_ok:
            result["ok"] = False
