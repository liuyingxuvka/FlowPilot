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
    "startup_answers_recorded_by_router",
    "startup_banner_emitted_after_answers",
    "run_shell_created",
    "current_pointer_written",
    "run_index_updated",
    "bootstrap_runtime_kit_copied",
    "bootstrap_placeholders_filled",
    "mailbox_initialized_from_copied_kit",
    "user_request_recorded_from_explicit_user_request",
    "user_intake_template_filled_from_raw_user_request",
    "six_roles_started_from_user_answer",
    "role_core_prompts_injected_from_copied_kit",
    "controller_core_loaded",
    "controller_role_confirmed_from_router_core",
    "controller_instructed_to_check_prompt_manifest",
    "controller_instructed_to_check_packet_ledger",
    "pm_core_card_delivered",
    "pm_phase_map_card_delivered",
    "pm_startup_intake_phase_card_delivered",
    "user_intake_delivered_to_pm",
    "pm_material_scan_phase_card_delivered",
    "pm_issues_material_and_capability_scan_packets",
    "router_direct_material_scan_dispatch_preflight_passed",
    "worker_scan_packet_bodies_delivered_after_dispatch",
    "worker_scan_results_returned",
    "reviewer_material_sufficiency_card_delivered",
    "reviewer_reports_material_sufficient",
    "reviewer_reports_research_required",
    "pm_material_absorb_or_research_card_delivered",
    "pm_absorbs_reviewed_material",
    "pm_research_package_phase_card_delivered",
    "pm_writes_bounded_research_package",
    "pm_records_research_capability_decision",
    "worker_research_report_card_delivered",
    "router_direct_research_dispatch_preflight_passed",
    "research_worker_packet_body_delivered_after_dispatch",
    "research_worker_report_returned",
    "reviewer_research_direct_source_check_card_delivered",
    "reviewer_direct_source_research_check_done",
    "reviewer_passes_research_result",
    "pm_research_absorb_or_mutate_card_delivered",
    "pm_absorbs_reviewed_research",
    "pm_material_understanding_card_delivered",
    "pm_writes_material_understanding_from_reviewed_sources",
    "pm_product_architecture_phase_card_delivered",
    "pm_writes_product_architecture_draft",
    "product_officer_product_architecture_modelability_card_delivered",
    "product_officer_product_architecture_modelability_passed",
    "reviewer_product_architecture_challenge_card_delivered",
    "reviewer_challenges_product_architecture",
    "pm_root_contract_phase_card_delivered",
    "pm_writes_root_contract_draft",
    "reviewer_root_contract_challenge_card_delivered",
    "reviewer_challenges_root_contract",
    "product_officer_root_contract_modelability_card_delivered",
    "product_officer_root_contract_modelability_passed",
    "pm_freezes_root_contract",
    "pm_dependency_policy_phase_card_delivered",
    "pm_records_dependency_policy",
    "pm_writes_capabilities_manifest",
    "pm_child_skill_selection_phase_card_delivered",
    "pm_writes_child_skill_selection",
    "pm_child_skill_gate_manifest_phase_card_delivered",
    "pm_writes_child_skill_gate_manifest",
    "reviewer_child_skill_gate_manifest_review_card_delivered",
    "reviewer_passes_child_skill_gate_manifest",
    "process_officer_child_skill_conformance_model_card_delivered",
    "process_officer_passes_child_skill_conformance_model",
    "product_officer_child_skill_product_fit_card_delivered",
    "product_officer_passes_child_skill_product_fit",
    "pm_approves_child_skill_manifest_for_route",
    "capability_evidence_synced",
    "pm_prior_path_context_phase_card_delivered",
    "controller_refreshes_route_history_context",
    "pm_reads_prior_path_context",
    "pm_route_skeleton_phase_card_delivered",
    "pm_writes_route_skeleton",
    "pm_activates_route_skeleton",
    "pm_current_node_loop_phase_card_delivered",
    "pm_node_started_event_card_delivered",
    "pm_node_acceptance_plan_phase_card_delivered",
    "controller_refreshes_route_history_context_for_node",
    "pm_reads_prior_path_context_for_node",
    "pm_writes_node_acceptance_plan_before_packet",
    "reviewer_node_acceptance_plan_review_card_delivered",
    "reviewer_passes_node_acceptance_plan",
    "pm_issues_current_node_packet",
    "router_direct_current_node_dispatch_from_reviewed_acceptance_plan",
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
    "pm_parent_backward_targets_phase_card_delivered",
    "pm_enumerates_parent_backward_targets",
    "reviewer_parent_backward_replay_card_delivered",
    "reviewer_parent_backward_replay_passed",
    "pm_parent_backward_segment_decision_card_delivered",
    "controller_refreshes_route_history_context_for_parent_segment",
    "pm_reads_prior_path_context_for_parent_segment",
    "pm_records_parent_backward_segment_decision",
    "pm_evidence_quality_package_phase_card_delivered",
    "pm_writes_evidence_quality_package",
    "reviewer_evidence_quality_review_card_delivered",
    "reviewer_passes_evidence_quality_review",
    "controller_refreshes_route_history_context_for_final_ledger",
    "pm_reads_prior_path_context_for_final_ledger",
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
        f"answers={state.startup_answers_recorded},{state.startup_answer_values_valid},"
        f"{state.startup_answer_provenance}|bootstrap={state.run_scoped_bootstrap_created},"
        f"{state.stale_top_level_bootstrap_reused}|banner={state.banner_emitted}|"
        f"visible_banner={state.startup_banner_user_visible}|"
        f"kit={state.runtime_kit_copied}|"
        f"user_request={state.user_request_recorded},{state.user_request_provenance}|"
        f"roles={state.roles_started},{state.fresh_role_agents_started}|"
        f"role_return={state.role_output_body_file_written},"
        f"{state.role_output_envelope_only_to_controller},"
        f"{state.role_output_path_hash_verified},"
        f"{state.role_chat_response_disclosed_body},"
        f"{state.controller_used_role_chat_body},"
        f"{state.controller_direct_free_text_instruction_used},"
        f"{state.controller_inspected_router_internal_hard_checks}|"
        f"ctrl={state.controller_role_confirmed}|material={state.material_review},"
        f"{state.material_accepted_by_pm},{state.research_absorbed_by_pm},"
        f"{state.material_understanding_written}|research={state.pm_research_package_written},"
        f"{state.research_capability_decision_recorded},"
        f"{state.research_dispatch_allowed},"
        f"{state.research_worker_packet_delivered},"
        f"{state.research_reviewer_passed}|"
        f"architecture={state.product_architecture_draft_written},"
        f"{state.product_architecture_modelability_passed},"
        f"{state.product_architecture_reviewer_challenged}|"
        f"contract={state.root_contract_draft_written},"
        f"{state.root_contract_modelability_passed},{state.root_contract_frozen_by_pm}|"
        f"step5={state.dependency_policy_recorded},"
        f"{state.capabilities_manifest_written},"
        f"{state.pm_child_skill_selection_written},"
        f"{state.child_skill_gate_manifest_written},"
        f"{state.child_skill_manifest_reviewer_passed},"
        f"{state.child_skill_process_officer_passed},"
        f"{state.child_skill_product_officer_passed},"
        f"{state.child_skill_manifest_pm_approved_for_route},"
        f"{state.capability_evidence_synced}|"
        f"history={state.pm_prior_path_context_card_delivered},"
        f"{state.route_history_context_refreshed},"
        f"{state.pm_prior_path_context_reviewed},"
        f"{state.route_history_context_stale}|"
        f"route={state.route_skeleton_written},{state.route_activated_by_pm}|"
        f"node_plan={state.node_acceptance_plan_written},"
        f"{state.node_acceptance_plan_reviewed}|"
        f"node={state.node_worker_result_ledger_checked},"
        f"{state.node_reviewer_reviewed_result},"
        f"{state.node_review_blocked},{state.node_completed_by_pm}|"
        f"parent={state.parent_backward_targets_enumerated},"
        f"{state.parent_backward_replay_passed},"
        f"{state.parent_pm_segment_decision_recorded}|"
        f"evidence_quality={state.pm_evidence_quality_package_card_delivered},"
        f"{state.pm_evidence_quality_package_written},"
        f"{state.reviewer_evidence_quality_review_card_delivered},"
        f"{state.evidence_quality_reviewer_passed}|"
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
