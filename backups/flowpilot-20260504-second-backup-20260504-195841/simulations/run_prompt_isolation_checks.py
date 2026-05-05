"""Run checks for the FlowPilot prompt-isolation control-plane model."""

from __future__ import annotations

import json
from collections import deque
from pathlib import Path

import prompt_isolation_model as model


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "prompt_isolation_results.json"

REQUIRED_LABELS = (
    "bootloader_router_loaded",
    "router_computed_next_bootloader_action",
    "startup_questions_asked_from_router",
    "startup_state_written_awaiting_answers",
    "dialog_stopped_for_startup_answers",
    "startup_answers_recorded_by_router",
    "startup_banner_emitted_after_answers",
    "run_shell_created",
    "current_pointer_written",
    "run_index_updated",
    "bootstrap_runtime_kit_copied",
    "bootstrap_placeholders_filled",
    "mailbox_initialized_from_copied_kit",
    "user_intake_template_filled_from_raw_user_request",
    "six_roles_started_from_user_answer",
    "role_core_prompts_injected_from_copied_kit",
    "controller_core_loaded",
    "controller_instructed_to_check_prompt_manifest",
    "controller_instructed_to_check_packet_ledger",
    "pm_core_card_delivered",
    "pm_controller_reset_duty_card_delivered",
    "pm_phase_map_card_delivered",
    "pm_startup_intake_phase_card_delivered",
    "user_intake_delivered_to_pm",
    "pm_first_decision_resets_controller",
    "controller_role_confirmed_from_pm_reset",
    "pm_issues_material_and_capability_scan_packets",
    "reviewer_dispatch_request_card_delivered",
    "reviewer_allows_material_scan_dispatch",
    "worker_scan_packet_bodies_delivered_after_dispatch",
    "worker_scan_results_returned",
    "reviewer_worker_result_review_card_delivered",
    "reviewer_reports_material_sufficient",
    "reviewer_reports_material_insufficient",
    "pm_reviewer_report_event_card_delivered",
    "pm_issues_repair_scan_packet",
    "repair_scan_dispatched_and_result_returned",
    "reviewer_passes_repair_scan_result",
    "pm_accepts_reviewed_repair_material",
    "pm_accepts_reviewed_material",
    "pm_product_understanding_phase_card_delivered",
    "pm_writes_product_understanding_from_reviewed_material",
    "reviewer_passes_product_understanding",
    "pm_route_skeleton_phase_card_delivered",
    "pm_writes_route_draft",
    "process_officer_route_check_passed",
    "product_officer_route_check_passed",
    "reviewer_route_check_passed",
    "pm_activates_reviewed_route",
    "pm_current_node_loop_phase_card_delivered",
    "pm_node_started_event_card_delivered",
    "pm_issues_current_node_packet",
    "reviewer_allows_current_node_dispatch",
    "current_node_worker_body_delivered_after_dispatch",
    "current_node_worker_result_returned",
    "current_node_reviewer_blocks_result",
    "current_node_reviewer_passes_result",
    "pm_review_repair_phase_card_delivered",
    "pm_reviewer_blocked_event_card_delivered",
    "pm_issues_current_node_repair_packet",
    "current_node_repair_result_returned",
    "reviewer_passes_current_node_repair",
    "pm_completes_current_node_from_reviewed_result",
    "pm_final_ledger_phase_card_delivered",
    "pm_builds_final_ledger",
    "reviewer_final_backward_replay_passed",
    "pm_closure_phase_card_delivered",
    "lifecycle_reconciled",
    "heartbeat_stopped_or_manual_resume_recorded",
    "crew_archived",
    "pm_completion_decision_recorded",
    "completed",
)


def _state_id(state: model.State) -> str:
    return (
        f"status={state.status}|startup={state.startup_state}|holder={state.holder}|"
        f"phase={state.phase}|event={state.event}|"
        f"router={state.router_loaded}|questions={state.startup_questions_asked}|"
        f"answers={state.startup_answers_recorded}|banner={state.banner_emitted}|"
        f"kit={state.runtime_kit_copied}|roles={state.roles_started}|"
        f"ctrl={state.controller_role_confirmed}|material={state.material_review},"
        f"{state.material_accepted_by_pm}|product={state.product_understanding_written},"
        f"{state.product_understanding_reviewer_passed}|route={state.route_draft_written},"
        f"{state.route_activated_by_pm}|node={state.node_reviewer_reviewed_result},"
        f"{state.node_review_blocked},{state.node_completed_by_pm}|"
        f"final={state.final_ledger_built_by_pm},{state.pm_completion_decision}|"
        f"prompt={state.prompt_deliveries}/{state.manifest_check_requests}/"
        f"{state.manifest_checks}|mail={state.mail_deliveries}/"
        f"{state.ledger_check_requests}/{state.ledger_checks}|"
        f"boot={state.bootloader_actions}/{state.router_action_requests}/"
        f"{state.router_action_requested}"
    )


def explore_safe_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    seen = {initial}
    labels: set[str] = set()
    edges = 0
    invariant_failures: list[dict[str, object]] = []
    terminals = {"complete": 0, "blocked": 0}

    while queue:
        state = queue.popleft()
        if state.status in terminals:
            terminals[state.status] += 1
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for transition in model.next_safe_states(state):
            labels.add(transition.label)
            edges += 1
            if transition.state not in seen:
                seen.add(transition.state)
                queue.append(transition.state)

    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    complete_states = sum(1 for state in seen if state.status == "complete")
    return {
        "ok": not invariant_failures and not missing_labels and complete_states > 0,
        "state_count": len(seen),
        "edge_count": edges,
        "labels": sorted(labels),
        "missing_labels": missing_labels,
        "complete_state_count": complete_states,
        "terminal_counts": terminals,
        "invariant_failures": invariant_failures,
    }


def check_hazards() -> dict[str, object]:
    hazard_results: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        detected = bool(failures)
        hazard_results[name] = {
            "detected": detected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazard_results}


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
