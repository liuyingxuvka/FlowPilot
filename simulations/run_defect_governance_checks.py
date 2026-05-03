"""Run checks for the FlowPilot defect governance model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import defect_governance_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "defect_governance_results.json"

REQUIRED_LABELS = (
    "run_started",
    "defect_ledger_initialized",
    "evidence_ledger_initialized",
    "skill_improvement_live_report_initialized",
    "reviewer_blocker_found",
    "defect_event_logged_by_discovering_role",
    "pm_triaged_blocking_defect",
    "repair_recorded_fixed_pending_recheck",
    "same_class_recheck_passed",
    "pm_closed_rechecked_defect",
    "invalid_parallel_screenshot_seen",
    "invalid_evidence_registered",
    "evidence_status_and_source_classified",
    "replacement_evidence_linked",
    "fixture_evidence_disclosed_separately",
    "flowpilot_skill_issue_observed",
    "skill_issue_live_report_updated",
    "pause_requested",
    "heartbeat_lifecycle_reconciled_for_pause",
    "pause_snapshot_written",
    "terminal_completion_started",
    "terminal_completion_allowed",
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
