"""Run checks for the FlowPilot release tooling model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import release_tooling_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "release_tooling_results.json"

REQUIRED_LABELS = (
    "dependency_manifest_written",
    "installer_written",
    "flowpilot_only_release_checker_written",
    "host_capability_mapping_declared",
    "dependency_sources_checked_ready",
    "dependency_sources_checked_missing_reported",
    "flowpilot_install_checked",
    "missing_dependencies_installed_without_overwrite",
    "privacy_scan_passed",
    "validation_passed",
    "flowpilot_release_prepared",
    "flowpilot_publish_allowed",
)


def explore_safe_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial}
    labels: set[str] = set()
    edges = 0
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": state.__dict__, "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            edges += 1
            if transition.state not in seen:
                seen.add(transition.state)
                queue.append(transition.state)

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    return {
        "ok": not invariant_failures and not missing_labels,
        "state_count": len(seen),
        "edge_count": edges,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "invariant_failures": invariant_failures,
    }


def check_hazards() -> dict[str, object]:
    ok = True
    results: dict[str, object] = {}
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        detected = bool(failures)
        results[name] = {
            "detected": detected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": results}


def main() -> int:
    safe = explore_safe_graph()
    hazards = check_hazards()
    result = {
        "ok": bool(safe["ok"]) and bool(hazards["ok"]),
        "safe_graph": safe,
        "hazard_checks": hazards,
    }
    RESULTS_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
