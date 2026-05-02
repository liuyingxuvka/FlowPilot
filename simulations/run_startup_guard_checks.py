"""Run checks for the FlowPilot startup hard-gate model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import startup_guard_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "startup_guard_results.json"
REQUIRED_LABELS = (
    "startup_three_questions_asked",
    "startup_dialog_stopped_for_user_answers",
    "run_mode_answer_recorded",
    "background_agents_allowed",
    "background_agents_declined_single_agent",
    "scheduled_continuation_allowed",
    "scheduled_continuation_declined_manual",
    "explicit_startup_answers_recorded",
    "startup_banner_emitted_after_answers",
    "route_file_written",
    "canonical_state_written",
    "execution_frontier_written",
    "crew_ledger_current",
    "role_memory_packets_current",
    "live_subagents_started",
    "single_agent_role_continuity_authorized",
    "automated_continuation_ready",
    "manual_resume_ready",
    "clean_start_required_by_user",
    "clean_start_not_required",
    "old_route_cleanup_verified",
    "startup_preflight_reviewer_report_blocked",
    "pm_returns_startup_blockers_to_worker",
    "startup_worker_remediation_completed",
    "startup_preflight_reviewer_report_clean",
    "pm_start_gate_opened_from_review_report",
    "startup_activation_guard_passed",
    "route_execution_started",
    "child_skill_started",
    "imagegen_started",
    "implementation_started",
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
    results: dict[str, object] = {}
    ok = True
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
    RESULTS_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
