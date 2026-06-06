"""Run checks for the FlowPilot startup Runtime/PM entry model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import startup_pm_review_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "startup_pm_review_results.json"
REQUIRED_LABELS = (
    "startup_intake_ui_completed",
    "background_collaboration_authorized_by_startup_ui",
    "startup_blocked_without_background_authorization",
    "explicit_background_authorization_recorded",
    "startup_banner_emitted_after_background_authorization",
    "run_directory_created",
    "current_pointer_written",
    "run_index_updated",
    "new_task_no_prior_import",
    "continue_previous_work_selected",
    "prior_work_import_packet_written",
    "control_state_written_under_run_root",
    "prior_control_state_quarantined",
    "route_file_written",
    "canonical_state_written",
    "execution_frontier_written",
    "startup_route_sign_displayed_in_chat",
    "background_agent_ledger_current",
    "background_collaboration_requested",
    "current_background_agents_opened",
    "background_agent_capability_unavailable_detected",
    "clean_start_required_by_user",
    "clean_start_not_required",
    "old_route_cleanup_verified",
    "startup_mechanical_audit_written_before_pm_first_round",
    "startup_mechanical_audit_delivered_to_pm",
    "runtime_completed_startup_mechanical_scope",
    "runtime_startup_entry_blocked",
    "pm_returns_startup_blockers_to_worker",
    "pm_declares_protocol_dead_end_for_unroutable_startup_block",
    "startup_worker_remediation_completed",
    "runtime_startup_entry_clean",
    "pm_independently_audited_startup_gate",
    "pm_first_round_started_after_runtime_entry",
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

