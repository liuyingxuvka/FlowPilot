"""File presence and top-level skill contract checks."""

from __future__ import annotations

import importlib
import importlib.util
import json

from .common import ROOT, REQUIRED_FILES, STARTUP_INTAKE_PS1_SOURCE_FILES, UTF8_BOM


def run_checks(result: dict[str, object]) -> None:
    try:
        flowguard = importlib.import_module("flowguard")
        result["checks"].append(
            {
                "name": "flowguard_import",
                "ok": True,
                "schema_version": getattr(flowguard, "SCHEMA_VERSION", "unknown"),
            }
        )
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {"name": "flowguard_import", "ok": False, "error": repr(exc)}
        )

    for relpath in REQUIRED_FILES:
        exists = (ROOT / relpath).exists()
        result["checks"].append({"name": f"file:{relpath}", "ok": exists})
        if not exists:
            result["ok"] = False

    for relpath in STARTUP_INTAKE_PS1_SOURCE_FILES:
        path = ROOT / relpath
        exists = path.exists()
        data = path.read_bytes() if exists else b""
        contains_non_ascii = any(byte >= 0x80 for byte in data)
        has_utf8_bom = data.startswith(UTF8_BOM)
        ok = exists and (not contains_non_ascii or has_utf8_bom)
        result["checks"].append(
            {
                "name": f"powershell_source_encoding:{relpath}",
                "ok": ok,
                "exists": exists,
                "contains_non_ascii": contains_non_ascii,
                "utf8_bom": has_utf8_bom,
            }
        )
        if not ok:
            result["ok"] = False

        text = path.read_text(encoding="utf-8-sig") if exists else ""
        forbidden_copy_terms = (
            "Runtime role assistance",
            "runtime role-binding coverage",
            "\u516d\u89d2\u8272\u56e2\u961f",
            "Runtime role collaboration",
            "\u8fd0\u884c\u65f6\u89d2\u8272\u534f\u4f5c",
            "Background agents",
            "\u540e\u53f0\u667a\u80fd\u4f53",
        )
        required_copy_terms = (
            "Background collaboration",
            "\u540e\u53f0\u534f\u4f5c",
            "Settings",
            "\u8bbe\u7f6e",
            "Support developer",
            "\u652f\u6301\u5f00\u53d1\u8005",
            "https://paypal.me/Yingxuliu",
        )
        forbidden_present = [term for term in forbidden_copy_terms if term in text]
        missing_required = [term for term in required_copy_terms if term not in text]
        copy_ok = exists and not forbidden_present and not missing_required
        result["checks"].append(
            {
                "name": f"startup_intake_runtime_role_copy:{relpath}",
                "ok": copy_ok,
                "forbidden_present": forbidden_present,
                "missing_required": missing_required,
            }
        )
        if not copy_ok:
            result["ok"] = False

    try:
        topology_path = ROOT / "scripts" / "flowguard_project_topology.py"
        spec = importlib.util.spec_from_file_location(
            "flowguard_project_topology_install_check",
            topology_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load {topology_path}")
        flowguard_project_topology = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(flowguard_project_topology)

        topology_result = flowguard_project_topology.check_topology(ROOT)
        result["checks"].append(
            {
                "name": "flowguard_project_topology_check",
                "ok": bool(topology_result["ok"]),
                "finding_count": len(topology_result["findings"]),
                "findings": topology_result["findings"][:20],
            }
        )
        if not topology_result["ok"]:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {"name": "flowguard_project_topology_check", "ok": False, "error": repr(exc)}
        )

    skill_path = ROOT / "skills/flowpilot/SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        has_name = "\nname: flowpilot\n" in f"\n{text}"
        result["checks"].append({"name": "skill_name:flowpilot", "ok": has_name})
        if not has_name:
            result["ok"] = False
        small_router_launcher = (
            len(text.splitlines()) < 160
            and "assets/flowpilot_new.py" in text
            and "public formal-run control surface is `assets/flowpilot_new.py` only" in text
            and "Do not read FlowPilot reference files" in text
            and "Final Route-Wide Gate Ledger" not in text
        )
        result["checks"].append(
            {"name": "flowpilot_skill_is_small_router_launcher", "ok": small_router_launcher}
        )
        if not small_router_launcher:
            result["ok"] = False
        new_entrypoint_startup = all(
            term in text
            for term in (
                "flowpilot_new.py --root <project-root> --json start",
                "native startup intake UI",
                "there is no requirement for a non-startup monitoring UI",
                "The runtime-provided current-run ledger is authority",
                "project-local active-run metadata is only UI focus/default-target metadata",
                "create or attach only the requested responsibility through an available host-supported, addressable, isolated role surface",
            )
        )
        result["checks"].append(
            {"name": "flowpilot_skill_new_entrypoint_startup_guidance", "ok": new_entrypoint_startup}
        )
        if not new_entrypoint_startup:
            result["ok"] = False

    try:
        dependencies = json.loads((ROOT / "flowpilot.dependencies.json").read_text(encoding="utf-8"))
        by_name = {item.get("name"): item for item in dependencies.get("dependencies", [])}
        required_codex_skills = {
            item.get("name")
            for item in dependencies.get("dependencies", [])
            if item.get("type") == "codex_skill" and item.get("required") is True
        }
        bootstrap_ok = (
            by_name.get("flowguard", {}).get("required") is True
            and by_name.get("flowguard", {}).get("source", {}).get("kind") == "github_python_package"
            and by_name.get("flowguard", {}).get("install", {}).get("requires_explicit_flag")
            == "--install-flowguard"
            and by_name.get("flowguard-agent-skill", {}).get("required") is True
            and by_name.get("flowguard-agent-skill", {}).get("install_name") == "flowguard"
            and required_codex_skills == {"flowpilot", "flowguard-agent-skill"}
            and "Dependency Bootstrap" in (ROOT / "skills/flowpilot/SKILL.md").read_text(encoding="utf-8")
            and (ROOT / "skills/flowpilot/DEPENDENCIES.md").exists()
        )
        result["checks"].append(
            {"name": "flowpilot_dependency_bootstrap_contract", "ok": bootstrap_ok}
        )
        if not bootstrap_ok:
            result["ok"] = False
    except Exception as exc:  # pragma: no cover - diagnostic script
        result["ok"] = False
        result["checks"].append(
            {"name": "flowpilot_dependency_bootstrap_contract", "ok": False, "error": repr(exc)}
        )

    router_path = ROOT / ("skills/flowpilot/assets/flowpilot_" "router.py")
    runtime_mode_template = ROOT / "templates/flowpilot/mode.template.json"
    router_text = router_path.read_text(encoding="utf-8") if router_path.exists() else ""
    run_modes_unsupported = (
        not runtime_mode_template.exists()
        and "DEFAULT_RUN_MODE" not in router_text
        and '"run_mode"' not in router_text
        and "'run_mode'" not in router_text
    )
    result["checks"].append(
        {
            "name": "flowpilot_run_modes_unsupported_from_runtime",
            "ok": run_modes_unsupported,
            "mode_template_exists": runtime_mode_template.exists(),
        }
    )
    if not run_modes_unsupported:
        result["ok"] = False
