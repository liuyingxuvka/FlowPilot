"""Documentation matrix and auxiliary skill checks."""

from __future__ import annotations

import json

from .common import ROOT


def run_checks(result: dict[str, object]) -> None:
    equivalence_path = ROOT / "docs/legacy_to_router_equivalence.json"
    if equivalence_path.exists():
        try:
            equivalence = json.loads(equivalence_path.read_text(encoding="utf-8"))
            required = equivalence.get("required_legacy_obligations")
            entries = equivalence.get("entries")
            valid_statuses = set(equivalence.get("status_values", []))
            entry_ids = {
                entry.get("id")
                for entry in entries
                if isinstance(entry, dict) and isinstance(entry.get("id"), str)
            } if isinstance(entries, list) else set()
            missing_entries = [
                item
                for item in required
                if isinstance(item, str) and item not in entry_ids
            ] if isinstance(required, list) else []
            invalid_status_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("status") not in valid_statuses
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            equivalence_ok = (
                equivalence.get("schema_version") == "flowpilot.legacy_to_router_equivalence.v1"
                and isinstance(required, list)
                and bool(required)
                and isinstance(entries, list)
                and len(entries) >= len(required)
                and not missing_entries
                and not invalid_status_entries
            )
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_to_router_equivalence_valid",
                    "ok": equivalence_ok,
                    "required_count": len(required) if isinstance(required, list) else 0,
                    "entry_count": len(entries) if isinstance(entries, list) else 0,
                    "missing_entries": missing_entries,
                    "invalid_status_entries": invalid_status_entries,
                }
            )
            if not equivalence_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_to_router_equivalence_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    barrier_results_path = ROOT / "simulations/barrier_equivalence_results.json"
    if barrier_results_path.exists():
        try:
            barrier_results = json.loads(barrier_results_path.read_text(encoding="utf-8"))
            safe_graph = barrier_results.get("safe_graph")
            hazard_checks = barrier_results.get("hazard_checks")
            explorer = barrier_results.get("flowguard_explorer")
            barrier_ok = (
                barrier_results.get("ok") is True
                and isinstance(safe_graph, dict)
                and safe_graph.get("missing_obligations_at_completion") == []
                and isinstance(hazard_checks, dict)
                and hazard_checks.get("ok") is True
                and isinstance(explorer, dict)
                and explorer.get("ok") is True
            )
            result["checks"].append(
                {
                    "name": "flowpilot_barrier_equivalence_results_valid",
                    "ok": barrier_ok,
                    "barrier_count": safe_graph.get("barrier_count") if isinstance(safe_graph, dict) else 0,
                    "legacy_obligation_count": safe_graph.get("legacy_obligation_count") if isinstance(safe_graph, dict) else 0,
                }
            )
            if not barrier_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_barrier_equivalence_results_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    matrix_path = ROOT / "docs/legacy_prompt_to_cards_matrix.json"
    if matrix_path.exists():
        try:
            matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
            entries = matrix.get("entries")
            decisions = set(matrix.get("decision_values", []))
            coverages = set(matrix.get("coverage_values", []))
            entry_ids = [
                str(entry.get("id"))
                for entry in entries
                if isinstance(entry, dict) and entry.get("id")
            ] if isinstance(entries, list) else []
            duplicate_entry_ids = sorted(
                {entry_id for entry_id in entry_ids if entry_ids.count(entry_id) > 1}
            )
            invalid_decision_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("new_architecture_decision") not in decisions
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            invalid_coverage_entries = [
                str(entry.get("id") or "<unknown>")
                for entry in entries
                if isinstance(entry, dict) and entry.get("current_coverage") not in coverages
            ] if isinstance(entries, list) else ["<entries-not-list>"]
            legacy_prompt_path = ROOT / str(matrix.get("source_prompt", ""))
            legacy_sections = []
            if legacy_prompt_path.exists():
                legacy_sections = [
                    line[3:].strip()
                    for line in legacy_prompt_path.read_text(encoding="utf-8").splitlines()
                    if line.startswith("## ")
                ]
            matrix_sections = {
                str(entry.get("legacy_section"))
                for entry in entries
                if isinstance(entry, dict) and entry.get("legacy_section")
            } if isinstance(entries, list) else set()
            missing_legacy_sections = [
                section for section in legacy_sections if section not in matrix_sections
            ]
            startup_reduction = matrix.get("startup_hard_gate_reduction")
            startup_reduction_ok = isinstance(startup_reduction, dict) and all(
                isinstance(startup_reduction.get(key), list) and startup_reduction.get(key)
                for key in (
                    "keep_as_hard_checks",
                    "downgrade_to_router_invariants",
                    "defer_until_surface_exists",
                    "retire_as_old_architecture_guard",
                )
            )
            matrix_ok = (
                matrix.get("schema_version") == "flowpilot.legacy_prompt_to_cards_matrix.v1"
                and isinstance(entries, list)
                and bool(entries)
                and not duplicate_entry_ids
                and not invalid_decision_entries
                and not invalid_coverage_entries
                and not missing_legacy_sections
                and startup_reduction_ok
            )
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_prompt_to_cards_matrix_valid",
                    "ok": matrix_ok,
                    "entry_count": len(entries) if isinstance(entries, list) else 0,
                    "legacy_section_count": len(legacy_sections),
                    "missing_legacy_sections": missing_legacy_sections,
                    "duplicate_entry_ids": duplicate_entry_ids,
                    "invalid_decision_entries": invalid_decision_entries,
                    "invalid_coverage_entries": invalid_coverage_entries,
                    "startup_reduction_ok": startup_reduction_ok,
                }
            )
            if not matrix_ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_legacy_prompt_to_cards_matrix_valid",
                    "ok": False,
                    "error": repr(exc),
                }
            )

    autonomous_skill_path = ROOT / "skills/autonomous-concept-ui-redesign/SKILL.md"
    if autonomous_skill_path.exists():
        text = autonomous_skill_path.read_text(encoding="utf-8")
        has_name = "\nname: autonomous-concept-ui-redesign\n" in f"\n{text}"
        result["checks"].append(
            {"name": "skill_name:autonomous-concept-ui-redesign", "ok": has_name}
        )
        if not has_name:
            result["ok"] = False
