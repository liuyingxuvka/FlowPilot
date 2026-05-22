"""Full model-test-code diagnostic surface inventory for FlowPilot."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Sequence

from flowpilot_model_test_alignment_common import *
from flowpilot_model_test_alignment_source_contracts import build_source_contract_alignment_plan

def _finding_counts(findings: Sequence[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        code = str(finding["code"])
        counts[code] = counts.get(code, 0) + 1
    return dict(sorted(counts.items()))


def _finding_counts_by_field(
    findings: Sequence[dict[str, Any]],
    field_name: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for finding in findings:
        value = str(finding.get(field_name, "unknown"))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def _line_count(text: str) -> int:
    return len(text.splitlines())


def _load_module_from_path(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    old_module = sys.modules.get(module_name)
    sys.modules[module_name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old_path
        if old_module is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = old_module
    return module


def _python_summary(path: Path) -> dict[str, Any]:
    text = _read_text(path)
    rel_path = _repo_path(str(path.relative_to(ROOT)))
    summary: dict[str, Any] = {
        "path": rel_path,
        "line_count": _line_count(text),
        "top_level_functions": [],
        "top_level_classes": [],
        "local_imports": [],
        "has_main": False,
        "parse_error": "",
        "all_exports_count": 0,
    }
    try:
        tree = ast.parse(text, filename=rel_path)
    except SyntaxError as exc:
        summary["parse_error"] = str(exc)
        return summary
    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []
    all_exports_count = 0
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith(("flowpilot_", "packet_", "card_", "role_", "barrier_")):
                imports.append(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(("flowpilot_", "packet_", "card_", "role_", "barrier_")):
                    imports.append(alias.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.Tuple, ast.List)):
                        all_exports_count = len(node.value.elts)
    summary["top_level_functions"] = sorted(functions)
    summary["top_level_classes"] = sorted(classes)
    summary["local_imports"] = sorted(set(imports))
    summary["has_main"] = "main" in functions
    summary["all_exports_count"] = all_exports_count
    return summary


def _text_corpus(paths: Sequence[Path]) -> str:
    return "\n".join(_read_text(path) for path in paths if path.exists())


def _simulation_model_corpus() -> str:
    paths = [
        path
        for path in sorted((ROOT / "simulations").glob("*.py"))
        if path.name != "run_flowpilot_model_test_alignment_checks.py"
    ]
    return _text_corpus(paths)


def _test_corpus() -> str:
    return _text_corpus(sorted((ROOT / "tests").rglob("*.py")))


def _surface_mentions(text: str, rel_path: str, stem: str) -> bool:
    return rel_path in text or stem in text


def _asset_model_binding(stem: str) -> str | None:
    if stem in ASSET_MODEL_BINDING_STEMS:
        return ASSET_MODEL_BINDING_STEMS[stem]
    for prefix, binding in ASSET_MODEL_BINDING_PREFIXES.items():
        if stem.startswith(prefix):
            return binding
    return None


def _script_model_binding(stem: str) -> str | None:
    return SCRIPT_MODEL_BINDING_STEMS.get(stem)


def _surface_kind_for_asset(stem: str, summary: dict[str, Any]) -> str:
    if stem in ASSET_FACADE_MODULES:
        return "compatibility_facade"
    local_imports = summary.get("local_imports", [])
    if summary.get("all_exports_count", 0) >= 6 and len(local_imports) >= 2:
        return "compatibility_facade"
    return "owner_module"


def _surface_threshold(kind: str) -> int:
    if kind == "model_check_runner_helper":
        return SCRIPT_STRUCTURE_SPLIT_LINE_THRESHOLD
    if kind == "compatibility_facade":
        return FACADE_STRUCTURE_SPLIT_LINE_THRESHOLD
    if kind == "script_entrypoint":
        return SCRIPT_STRUCTURE_SPLIT_LINE_THRESHOLD
    return OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD


def _default_structure_split_deferral(
    *,
    kind: str,
    stem: str,
    line_count: int,
    split_threshold: int,
) -> dict[str, Any]:
    if line_count <= split_threshold:
        return {}
    if kind == "model_check_runner":
        return {
            "split_status": "deferred_split",
            "split_reason": "line_threshold_exceeded | validation_runner_public_entrypoint",
            "deferred_split_reason": (
                "validated_entrypoint_contract_current | "
                "requires_dedicated_structuremesh_target_before_runner_extraction"
            ),
            "peer_safety_status": "do_not_edit_without_claim",
            "safe_split_class": "validation_entrypoint",
            "recommended_next_action": "split_runner_after_claim_with_cli_parity_tests",
        }
    if kind == "compatibility_facade":
        safe_class = "compatibility_facade"
    elif stem.startswith(("flowpilot_router_protocol_", "flowpilot_router_facade_export_")):
        safe_class = "declarative_protocol_table"
    else:
        safe_class = "stateful_runtime_flow"
    return {
        "split_status": "deferred_split",
        "split_reason": "line_threshold_exceeded | external_contract_pinned",
        "deferred_split_reason": (
            "contract_tests_current | peer_agents_active | "
            "requires_dedicated_structuremesh_claim_before_runtime_split"
        ),
        "peer_safety_status": "do_not_edit_without_claim",
        "safe_split_class": safe_class,
        "recommended_next_action": "claim_and_split_with_contract_parity_tests",
    }


def _diagnostic_gap_codes(surface: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    if not surface.get("has_model", False):
        codes.append("missing_model")
    if not surface.get("has_code", False):
        codes.append("missing_code")
    if not surface.get("has_test", False):
        codes.append("missing_test")
    if surface.get("has_code", False) and not surface.get("has_model", False):
        codes.append("extra_code")
    if (
        surface.get("has_test", False)
        and surface.get("kind") != "test_tier"
        and not surface.get("has_external_contract", False)
    ):
        codes.append("internal_only_test")
    if surface.get("evidence_status") in STALE_EVIDENCE_STATUSES:
        codes.append("stale_evidence")
    if _needs_structure_split_gap(surface):
        codes.append("needs_structure_split")
    return [code for code in DIAGNOSTIC_GAP_CODES if code in codes]


def _needs_structure_split_gap(surface: dict[str, Any]) -> bool:
    if surface.get("line_count", 0) <= int(surface.get("split_threshold", 10**9)):
        return False
    return str(surface.get("structure_split_status") or "") != "explicitly_skipped"


def _is_explicit_structure_split_skip(surface: dict[str, Any]) -> bool:
    return str(surface.get("structure_split_status") or "") == "explicitly_skipped"


def _diagnostic_surface_owner(surface: dict[str, Any]) -> str:
    owner = surface.get("surface_owner") or surface.get("owner")
    if owner:
        return str(owner)
    kind = str(surface.get("kind", "unknown"))
    if kind == "test_tier_command":
        return f"test-tier:{surface.get('tier', 'unknown')}"
    if kind == "test_tier":
        return "test-tier"
    path = str(surface.get("path", ""))
    if path:
        stem = Path(path).stem
        if path.startswith("skills/flowpilot/assets/"):
            return stem
        if path.startswith("scripts/"):
            return f"script:{stem}"
        if path.startswith("simulations/"):
            return f"model-check:{stem}"
    return str(surface.get("name", surface.get("surface_id", "unknown")))


def _diagnostic_release_relevance(surface: dict[str, Any]) -> str:
    relevance = surface.get("release_relevance")
    if relevance:
        return str(relevance)
    kind = str(surface.get("kind", "unknown"))
    path = str(surface.get("path", ""))
    stem = Path(path).stem if path else str(surface.get("name", ""))
    if surface.get("tier") == "legacy-full" or str(surface.get("name", "")).startswith(
        ("meta_legacy", "capability_legacy")
    ):
        return "legacy_validation"
    release_scripts = {
        "audit_local_install_sync",
        "check_install",
        "check_public_release",
        "install_flowpilot",
        "run_test_tier",
    }
    if surface.get("release_only") or stem in release_scripts:
        return "release_gate"
    if kind in {"test_tier", "test_tier_command", "model_check_runner", "model_check_runner_helper"}:
        return "validation_gate"
    if kind in {"compatibility_facade", "owner_module"}:
        return "runtime_contract"
    if kind == "script_entrypoint":
        return "public_cli"
    return "maintenance"


def _diagnostic_repair_type(code: str, surface: dict[str, Any]) -> str:
    if code == "needs_structure_split" and surface.get("structure_split_status") == "deferred":
        return "defer_structure_split"
    if code == "stale_evidence" and surface.get("evidence_status") == "release_local_only":
        return "rerun_public_release_evidence"
    if code == "stale_evidence" and surface.get("evidence_status") == "failed":
        return "fix_failing_background_evidence"
    if code == "stale_evidence" and surface.get("evidence_status") in {
        "incomplete",
        "missing_final_artifacts",
        "progress_only",
        "running",
        "stale",
    }:
        return "complete_background_evidence"
    return DIAGNOSTIC_REPAIR_TYPES.get(code, "inspect_gap")


def _diagnostic_severity(code: str, surface: dict[str, Any]) -> str:
    relevance = str(surface.get("release_relevance", _diagnostic_release_relevance(surface)))
    kind = str(surface.get("kind", "unknown"))
    if code == "missing_code":
        return "critical"
    if code == "stale_evidence" and relevance in {"release_gate", "validation_gate"}:
        return "critical"
    if code == "missing_test" and relevance in {"release_gate", "validation_gate"}:
        return "high"
    if code in {"missing_model", "internal_only_test"} and kind in {
        "compatibility_facade",
        "owner_module",
        "script_entrypoint",
    }:
        return "high"
    if code == "needs_structure_split":
        return "medium"
    if code == "extra_code":
        return "low"
    return "medium"


def _diagnostic_priority_score(code: str, surface: dict[str, Any]) -> int:
    severity = _diagnostic_severity(code, surface)
    relevance = str(surface.get("release_relevance", _diagnostic_release_relevance(surface)))
    code_order = {
        "missing_code": 0,
        "stale_evidence": 1,
        "missing_test": 2,
        "internal_only_test": 3,
        "missing_model": 4,
        "needs_structure_split": 5,
        "extra_code": 6,
    }
    release_boost = {
        "release_gate": 0,
        "validation_gate": 2,
        "runtime_contract": 4,
        "public_cli": 6,
        "maintenance": 8,
        "legacy_validation": 12,
    }.get(relevance, 8)
    return (
        DIAGNOSTIC_SEVERITY_SCORE.get(severity, 99)
        + release_boost
        + code_order.get(code, 20)
    )


def _diagnostic_dedupe_key(code: str, surface: dict[str, Any]) -> str:
    owner = str(surface.get("surface_owner", _diagnostic_surface_owner(surface)))
    repair_type = _diagnostic_repair_type(code, surface)
    return f"{owner}|{repair_type}|{code}"


def _finalize_surface(surface: dict[str, Any]) -> dict[str, Any]:
    surface = dict(surface)
    surface["surface_owner"] = _diagnostic_surface_owner(surface)
    surface["release_relevance"] = _diagnostic_release_relevance(surface)
    gap_codes = _diagnostic_gap_codes(surface)
    surface["gap_codes"] = gap_codes
    surface["covered"] = not gap_codes
    surface["repair_types"] = sorted(
        {_diagnostic_repair_type(code, surface) for code in gap_codes}
    )
    surface["max_severity"] = (
        min(
            (_diagnostic_severity(code, surface) for code in gap_codes),
            key=lambda item: DIAGNOSTIC_SEVERITY_SCORE.get(item, 99),
        )
        if gap_codes
        else "none"
    )
    return surface


def _surface_findings(surface: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for code in surface["gap_codes"]:
        repair_type = _diagnostic_repair_type(code, surface)
        severity = _diagnostic_severity(code, surface)
        findings.append(
            {
                "code": code,
                "surface_id": surface["surface_id"],
                "kind": surface["kind"],
                "path": surface.get("path", ""),
                "name": surface.get("name", surface["surface_id"]),
                "surface_owner": surface["surface_owner"],
                "release_relevance": surface["release_relevance"],
                "repair_type": repair_type,
                "severity": severity,
                "dedupe_key": _diagnostic_dedupe_key(code, surface),
                "priority_score": _diagnostic_priority_score(code, surface),
                "message": _diagnostic_message(code, surface),
            }
        )
    return findings


def _actionable_summary(findings: Sequence[dict[str, Any]], *, limit: int = 40) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for finding in sorted(
        findings,
        key=lambda item: (
            int(item.get("priority_score", 999)),
            str(item.get("path", "")),
            str(item.get("surface_id", "")),
        ),
    ):
        key = str(finding["dedupe_key"])
        group = grouped.get(key)
        if group is None:
            group = {
                "dedupe_key": key,
                "severity": finding["severity"],
                "surface_owner": finding["surface_owner"],
                "release_relevance": finding["release_relevance"],
                "repair_type": finding["repair_type"],
                "primary_code": finding["code"],
                "priority_score": finding["priority_score"],
                "message": finding["message"],
                "finding_count": 0,
                "gap_codes": [],
                "surface_ids": [],
                "paths": [],
            }
            grouped[key] = group
        group["finding_count"] += 1
        if finding["code"] not in group["gap_codes"]:
            group["gap_codes"].append(finding["code"])
        if finding["surface_id"] not in group["surface_ids"]:
            group["surface_ids"].append(finding["surface_id"])
        path = finding.get("path", "")
        if path and path not in group["paths"]:
            group["paths"].append(path)
    for group in grouped.values():
        group["gap_codes"] = sorted(group["gap_codes"])
        group["surface_ids"] = group["surface_ids"][:12]
        group["paths"] = group["paths"][:8]
    return sorted(
        grouped.values(),
        key=lambda item: (
            int(item["priority_score"]),
            str(item["surface_owner"]),
            str(item["repair_type"]),
            str(item["primary_code"]),
        ),
    )[:limit]


def _diagnostic_message(code: str, surface: dict[str, Any]) -> str:
    name = surface.get("name", surface["surface_id"])
    if code == "missing_model":
        return f"{name} is not bound to an executable FlowGuard/model obligation in the current diagnostic corpus"
    if code == "missing_code":
        return f"{name} references code or command targets that are missing"
    if code == "missing_test":
        return f"{name} has no ordinary test evidence in the current diagnostic corpus"
    if code == "extra_code":
        return f"{name} exists as code without a model binding"
    if code == "internal_only_test":
        return f"{name} has tests or mentions but no source-level external contract binding"
    if code == "stale_evidence":
        status = surface.get("evidence_status", "unknown")
        return f"{name} has non-final background evidence status: {status}"
    if code == "needs_structure_split":
        return (
            f"{name} has {surface.get('line_count', 0)} lines, above the "
            f"{surface.get('split_threshold')} line diagnostic threshold"
        )
    return f"{name} has diagnostic gap {code}"


def _is_deferred_structure_finding(finding: dict[str, Any]) -> bool:
    return (
        finding.get("code") == "needs_structure_split"
        and finding.get("repair_type") == "defer_structure_split"
    )


def _command_references_exist(command: Sequence[str]) -> bool:
    for token in command:
        normalized = token.replace("\\", "/")
        if normalized.endswith(".py"):
            if not (ROOT / normalized).exists():
                return False
        if normalized.startswith(("tests.", "simulations.")):
            module_path = ROOT / (normalized.replace(".", "/") + ".py")
            package_init = ROOT / normalized.replace(".", "/") / "__init__.py"
            if not module_path.exists() and not package_init.exists():
                return False
    return True


def _command_contains_test_target(command: Sequence[str]) -> bool:
    return any(
        token.startswith("tests.")
        or token.startswith("tests/")
        or token.startswith("tests\\")
        or token.startswith("tests")
        for token in command
    )


def _command_contains_model_runner(command: Sequence[str]) -> bool:
    return any(
        token.startswith("simulations/run_") and token.endswith(".py")
        for token in command
    )


def _background_evidence_for_command(
    run_test_tier: Any,
    command: Any,
    *,
    tier: str,
) -> dict[str, Any]:
    names = BACKGROUND_COMMAND_ARTIFACT_ALIASES.get(command.name, (command.name,))
    inspected: list[dict[str, Any]] = []
    preferred: dict[str, Any] | None = None
    preferred_score = -1
    for root in BACKGROUND_ARTIFACT_ROOTS:
        for name in names:
            evidence = run_test_tier.classify_background_artifact(
                root,
                name,
                command=command,
                tier=tier,
            )
            evidence["artifact_root"] = _repo_path(str(root.relative_to(ROOT))) if root.is_relative_to(ROOT) else str(root)
            evidence["artifact_name"] = name
            inspected.append(evidence)
            status = str(evidence.get("status", ""))
            proof_scope = str(evidence.get("proof_scope", ""))
            if status == "passed" and proof_scope == "full":
                score = 4
            elif status == "passed":
                score = 3
            elif status == "release_local_only":
                score = 2
            elif status not in {"incomplete", "missing_final_artifacts"}:
                score = 1
            else:
                score = 0
            if score > preferred_score:
                preferred = evidence
                preferred_score = score
    if preferred is None:
        preferred = {
            "name": command.name,
            "status": "missing_final_artifacts",
            "execution_status": "missing_final_artifacts",
            "ok": False,
            "proof_scope": "unknown",
            "reasons": ["no_final_background_artifacts_found"],
            "artifacts": {},
        }
    return {
        "selected": preferred,
        "inspected": inspected,
    }


def _legacy_full_reclassification(command_name: str) -> dict[str, Any] | None:
    parent = LEGACY_FULL_LAYERED_PARENT.get(command_name)
    if parent is None:
        return None
    try:
        thin_parent_checks = _load_module_from_path(
            "flowpilot_alignment_thin_parent_checks",
            ROOT / "simulations" / "flowpilot_thin_parent_checks.py",
        )
    except Exception as exc:  # pragma: no cover - defensive import fallback
        return {
            "ok": False,
            "reason": "layered_full_status_unavailable",
            "error": str(exc),
            "legacy_monolith_required_for_release": True,
        }
    layered = thin_parent_checks.layered_full_status(parent)
    if not layered.get("valid"):
        return {
            "ok": False,
            "reason": str(layered.get("reason") or "layered_full_not_current"),
            "layered_full_status": layered,
            "legacy_monolith_required_for_release": True,
        }
    return {
        "ok": True,
        "reason": (
            "legacy monolithic full graph is retained as a historical "
            "compatibility oracle; current release confidence comes from the "
            "layered full parent proof"
        ),
        "layered_full_status": layered,
        "legacy_monolith_required_for_release": False,
    }


def _test_tier_command_surfaces(
    *,
    model_text: str,
    test_text: str,
) -> list[dict[str, Any]]:
    run_test_tier_path = ROOT / "scripts" / "run_test_tier.py"
    run_test_tier = _load_module_from_path(
        "flowpilot_alignment_diagnostic_run_test_tier",
        run_test_tier_path,
    )
    surfaces: list[dict[str, Any]] = []
    test_tiering_external_contract = (
        (ROOT / "simulations" / "flowpilot_test_tiering_model.py").exists()
        and TEST_TIER_COMMAND_CONTRACT_TEST_MARKER in test_text
    )
    for tier in run_test_tier.tier_names():
        commands = run_test_tier.commands_for_tier(tier)
        tier_surface = _finalize_surface(
            {
                "surface_id": f"tier:{tier}",
                "kind": "test_tier",
                "name": tier,
                "path": "scripts/run_test_tier.py",
                "has_model": tier in model_text or tier in test_text,
                "has_code": True,
                "has_test": tier in test_text,
                "has_external_contract": test_tiering_external_contract,
                "model_binding": "test_tiering_model",
                "evidence_status": "passed",
                "line_count": len(commands),
                "split_threshold": 999,
                "command_count": len(commands),
            }
        )
        surfaces.append(tier_surface)
        for command in commands:
            command_text = " ".join(command.command)
            evidence_status = "passed"
            background_evidence: dict[str, Any] | None = None
            if command.background_recommended or command.long_running:
                background_evidence = _background_evidence_for_command(
                    run_test_tier,
                    command,
                    tier=tier,
                )
                evidence_status = str(background_evidence["selected"]["status"])
                legacy_reclassification = _legacy_full_reclassification(command.name)
                if legacy_reclassification and legacy_reclassification["ok"]:
                    evidence_status = "legacy_full_reclassified"
            has_validation_target = _command_contains_test_target(command.command) or _command_contains_model_runner(command.command)
            surface = {
                "surface_id": f"tier-command:{tier}:{command.name}",
                "kind": "test_tier_command",
                "name": command.name,
                "path": "scripts/run_test_tier.py",
                "tier": tier,
                "command": list(command.command),
                "has_model": tier_surface["has_model"] or command.name in model_text or command.name in test_text,
                "has_code": _command_references_exist(command.command),
                "has_test": has_validation_target or command.name in test_text,
                "has_external_contract": tier_surface["has_external_contract"],
                "model_binding": tier_surface["model_binding"],
                "evidence_status": evidence_status,
                "line_count": 1,
                "split_threshold": 999,
                "long_running": command.long_running,
                "release_only": command.release_only,
                "background_recommended": command.background_recommended,
                "command_text": command_text,
            }
            if background_evidence is not None:
                surface["background_evidence"] = background_evidence
                surface["proof_scope"] = background_evidence["selected"].get("proof_scope", "unknown")
                legacy_reclassification = _legacy_full_reclassification(command.name)
                if legacy_reclassification is not None:
                    surface["legacy_full_reclassification"] = legacy_reclassification
            surfaces.append(_finalize_surface(surface))
    return surfaces


def _asset_surfaces(
    *,
    model_text: str,
    test_text: str,
    source_contract_paths: set[str],
) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_asset_contract_test_exists = (
        ASSET_SURFACE_CONTRACT_TEST_PATH.exists()
        and ASSET_SURFACE_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "skills" / "flowpilot" / "assets").glob("*.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        kind = _surface_kind_for_asset(stem, summary)
        surface_id = f"asset:{stem}"
        split_repair = dict(STRUCTURE_SPLIT_REPAIR_PLAN.get(stem, {}))
        split_threshold = _surface_threshold(kind)
        if not split_repair:
            split_repair = _default_structure_split_deferral(
                kind=kind,
                stem=stem,
                line_count=summary["line_count"],
                split_threshold=split_threshold,
            )
        if split_repair:
            split_repair.setdefault("recent_owner_context", list(RECENT_OWNER_MODULE_POLISH_COMMITS))
            split_repair.setdefault("structure_split_status", "deferred")
        model_binding = _asset_model_binding(stem)
        aggregate_facade_contract = aggregate_asset_contract_test_exists and kind == "compatibility_facade"
        has_external_contract = (
            rel_path in source_contract_paths
            or surface_id in FACADE_PARITY_EXTERNAL_CONTRACT_SURFACE_IDS
            or aggregate_facade_contract
        )
        has_model = bool(model_binding) or has_external_contract or _surface_mentions(model_text, rel_path, stem)
        has_test = aggregate_facade_contract or has_external_contract or _surface_mentions(test_text, rel_path, stem)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": surface_id,
                    "kind": kind,
                    "name": stem,
                    "path": rel_path,
                    "has_model": has_model,
                    "has_code": path.exists() and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": has_external_contract,
                    "model_binding": model_binding,
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": split_threshold,
                    "top_level_function_count": len(summary["top_level_functions"]),
                    "top_level_class_count": len(summary["top_level_classes"]),
                    "local_import_count": len(summary["local_imports"]),
                    "parse_error": summary["parse_error"],
                    **split_repair,
                }
            )
        )
    return surfaces


def _script_surfaces(*, model_text: str, test_text: str) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_script_contract_test_exists = (
        SCRIPT_SURFACE_CONTRACT_TEST_PATH.exists()
        and SCRIPT_SURFACE_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "scripts").glob("*.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        model_binding = _script_model_binding(stem)
        has_model = bool(model_binding) or _surface_mentions(model_text, rel_path, stem)
        has_test = aggregate_script_contract_test_exists or _surface_mentions(test_text, rel_path, stem)
        has_external_contract = aggregate_script_contract_test_exists or (stem in SCRIPT_CLI_EXTERNAL_CONTRACT_STEMS and has_test)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": f"script:{stem}",
                    "kind": "script_entrypoint",
                    "name": stem,
                    "path": rel_path,
                    "has_model": has_model,
                    "has_code": path.exists() and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": has_external_contract,
                    "model_binding": model_binding,
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": _surface_threshold("script_entrypoint"),
                    "has_main": summary["has_main"],
                    "parse_error": summary["parse_error"],
                }
            )
        )
    return surfaces


def _model_check_surfaces(*, test_text: str) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_contract_test_exists = (
        MODEL_CHECK_RUNNER_CONTRACT_TEST_PATH.exists()
        and MODEL_CHECK_RUNNER_CONTRACT_TEST_MARKER in test_text
    )
    for path in sorted((ROOT / "simulations").glob("run_*checks.py")):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        has_test = aggregate_contract_test_exists or _surface_mentions(test_text, rel_path, stem)
        split_threshold = _surface_threshold("script_entrypoint")
        split_repair = _default_structure_split_deferral(
            kind="model_check_runner",
            stem=stem,
            line_count=summary["line_count"],
            split_threshold=split_threshold,
        )
        if split_repair:
            split_repair.setdefault("structure_split_status", "deferred")
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": f"model-check:{stem}",
                    "kind": "model_check_runner",
                    "name": stem,
                    "path": rel_path,
                    "has_model": True,
                    "has_code": path.exists() and summary["has_main"] and not bool(summary["parse_error"]),
                    "has_test": has_test,
                    "has_external_contract": aggregate_contract_test_exists or stem == "run_flowpilot_model_test_alignment_checks",
                    "model_binding": "model_check_runner_contract",
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": split_threshold,
                    "has_main": summary["has_main"],
                    "parse_error": summary["parse_error"],
                    **split_repair,
                }
            )
        )
    return surfaces


def _model_check_helper_surfaces(*, test_text: str) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = []
    aggregate_contract_test_exists = (
        MODEL_CHECK_RUNNER_CONTRACT_TEST_PATH.exists()
        and MODEL_CHECK_RUNNER_CONTRACT_TEST_MARKER in test_text
    )
    helper_paths: set[Path] = set()
    for pattern in (
        "*runner_impl.py",
        "*runner_contract.py",
        "*runner_graph.py",
        "*runner_inventory.py",
        "*runner_source.py",
        "*checks_projection*.py",
    ):
        helper_paths.update((ROOT / "simulations").glob(pattern))
    for path in sorted(helper_paths):
        rel_path = _repo_path(str(path.relative_to(ROOT)))
        stem = path.stem
        summary = _python_summary(path)
        surfaces.append(
            _finalize_surface(
                {
                    "surface_id": f"model-check-helper:{stem}",
                    "kind": "model_check_runner_helper",
                    "name": stem,
                    "path": rel_path,
                    "has_model": True,
                    "has_code": path.exists() and not bool(summary["parse_error"]),
                    "has_test": aggregate_contract_test_exists or _surface_mentions(test_text, rel_path, stem),
                    "has_external_contract": aggregate_contract_test_exists,
                    "model_binding": "model_check_runner_implementation_contract",
                    "evidence_status": "passed",
                    "line_count": summary["line_count"],
                    "split_threshold": _surface_threshold("model_check_runner_helper"),
                    "top_level_function_count": len(summary["top_level_functions"]),
                    "top_level_class_count": len(summary["top_level_classes"]),
                    "local_import_count": len(summary["local_imports"]),
                    "parse_error": summary["parse_error"],
                }
            )
        )
    return surfaces


def _full_diagnostic_known_bad_cases() -> list[dict[str, Any]]:
    return [
        {
            "name": "orphan_code",
            "expected_codes": ["missing_model", "missing_test", "extra_code"],
            "surface": {
                "surface_id": "synthetic:orphan_code",
                "kind": "owner_module",
                "name": "orphan_code",
                "path": "skills/flowpilot/assets/orphan_code.py",
                "has_model": False,
                "has_code": True,
                "has_test": False,
                "has_external_contract": False,
                "evidence_status": "passed",
                "line_count": 20,
                "split_threshold": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
        {
            "name": "wrapper_only_evidence",
            "expected_codes": ["internal_only_test"],
            "surface": {
                "surface_id": "synthetic:wrapper_only",
                "kind": "compatibility_facade",
                "name": "wrapper_only",
                "path": "skills/flowpilot/assets/wrapper_only.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": False,
                "evidence_status": "passed",
                "line_count": 20,
                "split_threshold": FACADE_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
        {
            "name": "progress_only_background",
            "expected_codes": ["stale_evidence"],
            "surface": {
                "surface_id": "synthetic:progress_only",
                "kind": "test_tier_command",
                "name": "progress_only_background",
                "path": "scripts/run_test_tier.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "running",
                "line_count": 1,
                "split_threshold": 999,
            },
        },
        {
            "name": "local_only_release_proof",
            "expected_codes": ["stale_evidence"],
            "surface": {
                "surface_id": "synthetic:local_only_release",
                "kind": "test_tier_command",
                "name": "local_only_release",
                "path": "scripts/run_test_tier.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "release_local_only",
                "line_count": 1,
                "split_threshold": 999,
                "release_only": True,
            },
        },
        {
            "name": "broad_unsplit_module",
            "expected_codes": ["needs_structure_split"],
            "surface": {
                "surface_id": "synthetic:broad_module",
                "kind": "owner_module",
                "name": "broad_module",
                "path": "skills/flowpilot/assets/broad_module.py",
                "has_model": True,
                "has_code": True,
                "has_test": True,
                "has_external_contract": True,
                "evidence_status": "passed",
                "line_count": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD + 1,
                "split_threshold": OWNER_STRUCTURE_SPLIT_LINE_THRESHOLD,
            },
        },
    ]


def _full_diagnostic_known_bad_report(case: dict[str, Any]) -> dict[str, Any]:
    surface = _finalize_surface(case["surface"])
    finding_codes = sorted(surface["gap_codes"])
    expected = set(case["expected_codes"])
    return {
        "name": case["name"],
        "ok": expected.issubset(finding_codes),
        "expected_codes": sorted(expected),
        "finding_codes": finding_codes,
        "surface": surface,
    }


def build_full_model_test_code_diagnostic() -> dict[str, Any]:
    source_plan = build_source_contract_alignment_plan()
    source_contract_paths = {contract.path for contract in source_plan.code_contracts}
    model_text = _simulation_model_corpus()
    test_text = _test_corpus()
    surfaces = []
    surfaces.extend(
        _asset_surfaces(
            model_text=model_text,
            test_text=test_text,
            source_contract_paths=source_contract_paths,
        )
    )
    surfaces.extend(_script_surfaces(model_text=model_text, test_text=test_text))
    surfaces.extend(_model_check_surfaces(test_text=test_text))
    surfaces.extend(_model_check_helper_surfaces(test_text=test_text))
    surfaces.extend(_test_tier_command_surfaces(model_text=model_text, test_text=test_text))
    surfaces = sorted(surfaces, key=lambda item: (item["kind"], item["surface_id"]))
    findings: list[dict[str, Any]] = []
    for surface in surfaces:
        findings.extend(_surface_findings(surface))
    known_bad = [
        _full_diagnostic_known_bad_report(case)
        for case in _full_diagnostic_known_bad_cases()
    ]
    surface_counts: dict[str, int] = {}
    for surface in surfaces:
        kind = str(surface["kind"])
        surface_counts[kind] = surface_counts.get(kind, 0) + 1
    actionable_findings = sorted(
        findings,
        key=lambda item: (
            int(item.get("priority_score", 999)),
            str(item["path"]),
            str(item["surface_id"]),
        ),
    )
    unresolved_non_deferred_findings = [
        finding
        for finding in findings
        if not _is_deferred_structure_finding(finding)
    ]
    deferred_structure_findings = [
        finding for finding in findings if _is_deferred_structure_finding(finding)
    ]
    explicitly_skipped_structure_surfaces = [
        surface for surface in surfaces if _is_explicit_structure_split_skip(surface)
    ]
    actionable_summary = _actionable_summary(findings)
    return {
        "ok": all(item["ok"] for item in known_bad),
        "result_type": "flowpilot_full_model_test_code_diagnostic",
        "diagnostic_boundary": FULL_DIAGNOSTIC_BOUNDARY,
        "full_coverage_ok": not findings,
        "release_convergence_ok": not unresolved_non_deferred_findings,
        "surface_count": len(surfaces),
        "surface_counts": dict(sorted(surface_counts.items())),
        "covered_surface_count": sum(1 for surface in surfaces if surface["covered"]),
        "gap_surface_count": sum(1 for surface in surfaces if surface["gap_codes"]),
        "gap_counts": _finding_counts(findings),
        "unresolved_non_deferred_gap_count": len(unresolved_non_deferred_findings),
        "unresolved_non_deferred_gap_counts": _finding_counts(
            unresolved_non_deferred_findings
        ),
        "deferred_structure_split_count": len(deferred_structure_findings),
        "explicitly_skipped_structure_split_count": len(
            explicitly_skipped_structure_surfaces
        ),
        "explicitly_skipped_structure_split_surfaces": [
            {
                "surface_id": str(surface.get("surface_id") or ""),
                "path": str(surface.get("path") or ""),
                "safe_split_class": str(surface.get("safe_split_class") or ""),
                "split_reason": str(surface.get("split_reason") or ""),
                "structure_split_skip_reason": str(
                    surface.get("structure_split_skip_reason") or ""
                ),
            }
            for surface in explicitly_skipped_structure_surfaces
        ],
        "gap_counts_by_severity": _finding_counts_by_field(findings, "severity"),
        "gap_counts_by_repair_type": _finding_counts_by_field(findings, "repair_type"),
        "gap_counts_by_release_relevance": _finding_counts_by_field(findings, "release_relevance"),
        "findings": findings,
        "actionable_findings": actionable_findings[:80],
        "actionable_summary": actionable_summary,
        "surfaces": surfaces,
        "known_bad_ok": all(item["ok"] for item in known_bad),
        "known_bad_sanity_checks": known_bad,
    }
