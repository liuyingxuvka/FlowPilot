"""Lightweight self-check for the FlowPilot skill package."""

from __future__ import annotations

import importlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "HANDOFF.md",
    "docs/project_brief.md",
    "docs/design_decisions.md",
    "docs/flowguard_preflight_findings.md",
    "docs/external_watchdog_loop_findings.md",
    "docs/stable_heartbeat_plan_frontier_findings.md",
    "docs/protocol.md",
    "docs/schema.md",
    "docs/verification.md",
    "docs/reviewer_fact_audit.md",
    "flowpilot.dependencies.json",
    "skills/flowpilot/SKILL.md",
    "skills/flowpilot/references/protocol.md",
    "skills/flowpilot/references/installation_contract.md",
    "skills/flowpilot/references/failure_modes.md",
    "templates/flowpilot/README.md",
    "templates/flowpilot/current.template.json",
    "templates/flowpilot/index.template.json",
    "templates/flowpilot/runs/run-001/run.template.json",
    "templates/flowpilot/state.template.json",
    "templates/flowpilot/crew_ledger.template.json",
    "templates/flowpilot/crew_memory/role_memory.template.json",
    "templates/flowpilot/material_intake_packet.template.json",
    "templates/flowpilot/pm_material_understanding.template.json",
    "templates/flowpilot/product_function_architecture.template.json",
    "templates/flowpilot/flowguard_modeling_request.template.json",
    "templates/flowpilot/flowguard_modeling_report.template.json",
    "templates/flowpilot/final_route_wide_gate_ledger.template.json",
    "templates/flowpilot/execution_frontier.template.json",
    "templates/flowpilot/startup_review.template.json",
    "templates/flowpilot/startup_pm_gate.template.json",
    "templates/flowpilot/mode.template.json",
    "templates/flowpilot/capabilities.template.json",
    "templates/flowpilot/contract.template.md",
    "templates/flowpilot/routes/route-001/flow.template.json",
    "templates/flowpilot/routes/route-001/flow.template.md",
    "templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json",
    "templates/flowpilot/heartbeats/hb.template.json",
    "templates/flowpilot/heartbeats/global-watchdog-supervisor.prompt.md",
    "templates/flowpilot/watchdog/watchdog.template.json",
    "templates/flowpilot/diagrams/user-flow-diagram.template.mmd",
    "templates/flowpilot/diagrams/user-flow-diagram.template.md",
    "templates/flowpilot/checkpoints/checkpoint.template.json",
    "templates/flowpilot/capabilities/capability-evidence.template.json",
    "templates/flowpilot/experiments/experiment-001/experiment.template.json",
    "templates/flowpilot/task-models/README.md",
    "examples/minimal/README.md",
    "examples/minimal/task.md",
    "simulations/meta_model.py",
    "simulations/run_meta_checks.py",
    "simulations/capability_model.py",
    "simulations/run_capability_checks.py",
    "simulations/startup_pm_review_model.py",
    "simulations/run_startup_pm_review_checks.py",
    "simulations/startup_pm_review_results.json",
    "simulations/release_tooling_model.py",
    "simulations/run_release_tooling_checks.py",
    "simulations/release_tooling_results.json",
    "scripts/install_flowpilot.py",
    "scripts/check_public_release.py",
    "scripts/flowpilot_watchdog.py",
    "scripts/flowpilot_paths.py",
    "scripts/flowpilot_global_supervisor.py",
    "scripts/flowpilot_lifecycle.py",
    "scripts/flowpilot_busy_lease.py",
    "scripts/flowpilot_run_with_busy_lease.py",
    "scripts/flowpilot_user_flow_diagram.py",
    "scripts/register_windows_watchdog_task.ps1",
    "scripts/smoke_autopilot.py",
]

JSON_FILES = [
    "flowpilot.dependencies.json",
    "simulations/release_tooling_results.json",
    "templates/flowpilot/current.template.json",
    "templates/flowpilot/index.template.json",
    "templates/flowpilot/runs/run-001/run.template.json",
    "templates/flowpilot/capabilities.template.json",
    "templates/flowpilot/mode.template.json",
    "templates/flowpilot/state.template.json",
    "templates/flowpilot/crew_ledger.template.json",
    "templates/flowpilot/crew_memory/role_memory.template.json",
    "templates/flowpilot/material_intake_packet.template.json",
    "templates/flowpilot/pm_material_understanding.template.json",
    "templates/flowpilot/product_function_architecture.template.json",
    "templates/flowpilot/flowguard_modeling_request.template.json",
    "templates/flowpilot/flowguard_modeling_report.template.json",
    "templates/flowpilot/final_route_wide_gate_ledger.template.json",
    "templates/flowpilot/execution_frontier.template.json",
    "templates/flowpilot/startup_review.template.json",
    "templates/flowpilot/startup_pm_gate.template.json",
    "templates/flowpilot/routes/route-001/flow.template.json",
    "templates/flowpilot/routes/route-001/nodes/node-001-start/node.template.json",
    "templates/flowpilot/heartbeats/hb.template.json",
    "templates/flowpilot/watchdog/watchdog.template.json",
    "templates/flowpilot/checkpoints/checkpoint.template.json",
    "templates/flowpilot/capabilities/capability-evidence.template.json",
    "templates/flowpilot/experiments/experiment-001/experiment.template.json",
]

OPTIONAL_RUNTIME_JSON_FILES = [
    ".flowpilot/current.json",
    ".flowpilot/index.json",
    ".flowpilot/runs/run-001/capabilities.json",
    ".flowpilot/runs/run-001/state.json",
    ".flowpilot/runs/run-001/execution_frontier.json",
    ".flowpilot/runs/run-001/routes/route-001/flow.json",
    ".flowpilot/capabilities.json",
    ".flowpilot/state.json",
    ".flowpilot/execution_frontier.json",
    ".flowpilot/routes/route-001/flow.json",
]


def main() -> int:
    result: dict[str, object] = {"ok": True, "checks": []}

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

    skill_path = ROOT / "skills/flowpilot/SKILL.md"
    if skill_path.exists():
        text = skill_path.read_text(encoding="utf-8")
        has_name = "\nname: flowpilot\n" in f"\n{text}"
        result["checks"].append({"name": "skill_name:flowpilot", "ok": has_name})
        if not has_name:
            result["ok"] = False

    legacy_skill_dir = ROOT / "skills/flowguard-project-autopilot"
    legacy_absent = not legacy_skill_dir.exists()
    result["checks"].append(
        {"name": "legacy_skill_dir_absent", "ok": legacy_absent}
    )
    if not legacy_absent:
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

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
