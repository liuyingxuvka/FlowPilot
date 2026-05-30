"""Documentation and auxiliary skill checks for the new-only FlowPilot runtime."""

from __future__ import annotations

import json

from .common import ROOT


def run_checks(result: dict[str, object]) -> None:
    new_only_results_path = ROOT / "simulations/flowpilot_new_only_runtime_results.json"
    if new_only_results_path.exists():
        try:
            payload = json.loads(new_only_results_path.read_text(encoding="utf-8"))
            hazard_checks = payload.get("hazard_checks")
            safe_graph = payload.get("safe_graph")
            current_path_explorer = payload.get("flowguard_current_path_explorer")
            unsupported_input_rejection_explorer = payload.get(
                "flowguard_unsupported_input_rejection_explorer"
            )
            ok = (
                payload.get("ok") is True
                and isinstance(hazard_checks, dict)
                and hazard_checks.get("ok") is True
                and isinstance(safe_graph, dict)
                and safe_graph.get("ok") is True
                and isinstance(current_path_explorer, dict)
                and current_path_explorer.get("ok") is True
                and isinstance(unsupported_input_rejection_explorer, dict)
                and unsupported_input_rejection_explorer.get("ok") is True
            )
            result["checks"].append(
                {
                    "name": "flowpilot_new_only_runtime_results_valid",
                    "ok": ok,
                    "path": str(new_only_results_path.relative_to(ROOT)),
                }
            )
            if not ok:
                result["ok"] = False
        except Exception as exc:  # pragma: no cover - diagnostic script
            result["ok"] = False
            result["checks"].append(
                {
                    "name": "flowpilot_new_only_runtime_results_valid",
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
