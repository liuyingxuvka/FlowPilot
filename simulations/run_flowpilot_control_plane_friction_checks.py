"""Run checks for the FlowPilot control-plane friction model."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from flowguard import Explorer

import flowpilot_control_plane_friction_model as model
from flowpilot_control_plane_friction_checks_runner_impl import _state_id


REQUIRED_LABELS = (
    "controller_boundary_confirmed_envelope_only",
    "select_expanded_safe_flow",
    "select_optimized_transaction_flow",
    "controller_applies_stateful_postcondition_before_done_receipt",
    "controller_delivery_done_starts_target_role_wait",
    "active_holder_lease_confirms_live_agent_and_role",
    "packet_ledger_io_guard_uses_atomic_lock_and_recovery",
    "router_reclaims_valid_router_owned_artifact_before_blocker",
    "router_materializes_ready_internal_postcondition_evidence",
    "controller_display_work_soft_recorded_without_hard_gate",
    "external_keepalive_action_confirmed_with_light_marker",
    "signed_material_migration_preserves_relayed_envelope",
    "control_blocker_action_identity_bound_to_artifact",
    "control_blocker_done_receipt_applies_delivery_postcondition",
    "stale_run_state_save_preserves_cleared_wait_projection",
    "self_check_status_pass_parser_aligned",
    "material_gate_result_evidence_machine_and_authority_backed",
    "material_repair_generation_protocol_checked",
    "current_repair_target_gate_retires_old_packets",
    "new_only_result_contract_blocks_old_shapes_and_retires_old_blockers",
    "pm_writes_research_package_with_scope_fields",
    "pm_records_research_capability_decision_preserving_package_scope",
    "worker_packet_materialized_with_research_scope",
    "router_direct_material_scan_dispatch_after_packet_integrity_check",
    "packet_delivered_by_controller",
    "target_records_packet_body_open_receipt",
    "worker_result_returned_to_ledger",
    "controller_routes_result_to_pm_after_ledger_check",
    "pm_records_result_body_open_receipt",
    "pm_records_package_result_disposition",
    "pm_releases_formal_gate_package_to_reviewer",
    "optimized_card_ack_auto_consumed_with_validation",
    "optimized_relay_transaction_records_delivery_open_and_hash",
    "pending_wait_reconciled_from_packet_status",
    "role_work_result_recipient_normalized_by_packet_type",
    "model_miss_flowguard_operator_report_complete_for_pm_decision",
    "role_memory_delta_written_as_non_authority_index",
    "reviewer_writes_report_after_receipts",
    "router_accepts_reviewer_report",
    "pm_material_understanding_written_to_canonical_files",
    "product_architecture_card_delivered_with_material_context_and_fresh_views",
    "status_summary_published_from_public_state",
    "pm_writes_route_draft_with_nonempty_nodes",
    "route_process_check_card_delivered_with_route_draft_context",
    "flowguard_operator_route_scope_passes_route_check_after_nonempty_route",
    "reviewer_blocks_child_skill_gate_manifest_for_repair",
    "pm_rewrites_child_skill_gate_after_block",
    "role_event_arrives_after_valid_card_ack_before_ledger_resolved",
    "router_pre_consumes_valid_card_ack_before_role_event",
    "role_event_arrives_before_missing_card_ack",
    "router_quarantines_pre_ack_report_and_requests_same_role_ack_recovery",
    "same_role_reads_card_and_submits_valid_ack_after_quarantine",
    "same_role_resubmits_fresh_report_after_valid_ack",
    "router_consumes_gate_card_ack_and_preserves_semantic_wait",
    "reviewer_passes_repaired_child_skill_gate_and_clears_block",
    "reviewer_block_classified_as_node_local",
    "reviewer_block_classified_as_route_invalidating",
    "pm_selects_same_node_repair_for_node_local_block",
    "same_node_repair_writes_fresh_plan_or_result",
    "same_reviewer_rechecks_repair_before_continue",
    "pm_selects_route_mutation_for_route_invalidating_block",
    "route_mutation_resets_route_checks_for_reapproval",
    "controller_waits_for_role_work_with_status_packet_read",
    "target_role_updates_progress_status_via_runtime",
    "controller_waits_for_role_output_with_status_packet_read",
    "target_role_updates_role_output_progress_via_runtime",
    "role_output_event_submitted_with_file_backed_body",
    "user_stop_requested",
    "run_lifecycle_reconciled_all_authorities",
    "route_state_snapshot_refreshed_after_lifecycle_change",
    "control_plane_flow_complete",
)


HAZARD_EXPECTED_FAILURES = {
    "research_package_scope_dropped": "worker research packet was materialized after PM package scope fields were dropped",
    "material_dispatch_phase_mismatch": "material scan dispatch request had inconsistent phase, output contract, write-target, or canonical-body state",
    "material_dispatch_output_contract_mismatch": "material scan dispatch request had inconsistent phase, output contract, write-target, or canonical-body state",
    "material_dispatch_write_target_missing": "material scan dispatch request had inconsistent phase, output contract, write-target, or canonical-body state",
    "material_dispatch_duplicate_canonical_body": "material scan dispatch request had inconsistent phase, output contract, write-target, or canonical-body state",
    "material_dispatch_allowed_without_preflight": "material scan dispatch was allowed before router direct-dispatch preflight",
    "signed_material_envelope_rewritten_after_relay": "signed packet or result envelope was rewritten after Controller relay hash binding",
    "signed_material_migration_sidecar_missing": "signed envelope migration backfilled mutable projections without a sidecar record",
    "control_blocker_identity_missing_blocker_id": "control blocker Controller action identity omitted blocker artifact identity",
    "closed_controller_action_reused_for_different_identity": "closed Controller action row was reused for a different Router obligation identity",
    "pm_role_work_closed_identity_reused_for_distinct_batch": "PM role-work action identity omitted batch, request, packet, or target role",
    "pm_role_work_wait_identity_missing_request_packet_role": "PM role-work wait or result used an identity that was not scoped to batch, request, packet, and target role",
    "pm_role_work_global_postcondition_masks_open_request": "PM role-work global postcondition masked an open request-specific obligation",
    "control_blocker_done_receipt_without_delivery_postcondition": "control blocker done receipt did not apply the Router-visible delivery postcondition",
    "stale_run_state_resurrects_closed_wait_projection": "stale run-state save resurrected a closed Controller wait projection",
    "self_check_status_pass_rejected": "Contract Self-Check parser rejected status: pass even though templates allow it",
    "material_gate_result_self_check_unparseable": "material gate depended on a result body whose Contract Self-Check was not machine-parseable",
    "material_gate_result_reader_not_runtime_backed": "artifact map advertised result-body reader access that runtime relay authority did not grant",
    "pm_formal_gate_package_missing_artifact": "PM formal gate package release lacked reviewer-readable artifact path, hash, or scope",
    "reviewer_report_without_result_open_receipt": "reviewer report was accepted before delivery, packet-open, result-return, PM relay, PM disposition, formal gate package, and result-open receipts existed",
    "missing_receipt_blocker_escalated_to_pm": "missing receipt blocker was not routed as same-role reviewer control-plane reissue",
    "stopped_run_with_active_manual_resume_binding": "stopped run left manual resume binding, runtime roles, packet loop, or frontier authority active",
    "stopped_run_with_active_packet_loop": "stopped run left manual resume binding, runtime roles, packet loop, or frontier authority active",
    "stopped_run_without_terminal_frontier": "stopped run left manual resume binding, runtime roles, packet loop, or frontier authority active",
    "stale_snapshot_published_as_active": "active route_state_snapshot is stale against frontier or packet ledger",
    "product_architecture_delivery_missing_material_context": "product architecture card was delivered without PM material-understanding source paths",
    "protocol_blocker_file_unregistered": "protocol blocker file existed without router-visible blocker registration",
    "control_blocker_index_stale_after_artifact_update": "router control blocker index disagreed with control blocker artifact status",
    "display_work_hard_postcondition_gate": "display/status controller work was treated as a hard postcondition gate",
    "display_work_escalated_to_pm_repair": "display/status controller work was treated as a hard postcondition gate",
    "external_keepalive_unconfirmed": "external keepalive action lacked lightweight completion confirmation",
    "stateful_receipt_done_without_postcondition_evidence": "stateful controller receipt was marked done before Router-visible postcondition evidence existed",
    "stateful_receipt_advanced_without_postcondition_evidence": "stateful controller receipt was marked done before Router-visible postcondition evidence existed",
    "controller_delivery_receipt_treated_as_role_completion": "Controller delivery receipt was treated as target-role completion",
    "controller_delivery_receipt_missing_role_output_blocker": "Router created a missing role-output blocker from a Controller delivery receipt",
    "controller_delivery_failed_marked_done": "Controller delivery receipt was marked done without host delivery success",
    "active_holder_lease_without_host_liveness": "active holder lease was issued without concrete agent identity, host liveness, and packet-role match",
    "active_holder_lease_to_wrong_packet_role": "active holder lease was issued without concrete agent identity, host liveness, and packet-role match",
    "packet_ledger_write_without_atomic_lock": "packet ledger write path lacked atomic unique-temp, lock/CAS, or readback validation",
    "packet_ledger_corrupt_read_crashes_daemon": "packet ledger corrupt read crashed the daemon instead of producing a recoverable control blocker",
    "valid_router_owned_artifact_not_reclaimed_before_blocker": "valid Router-owned artifact/proof existed but Router did not reclaim the postcondition",
    "daemon_tick_semicomplete_receipt_escalates_before_reclaim": "valid Router-owned artifact/proof existed but Router did not reclaim the postcondition",
    "router_internal_postcondition_role_wait_dead_end": "router-owned internal postcondition was exposed as a Controller/role wait instead of materializing or blocking",
    "router_internal_postcondition_unmaterialized_after_ready_inputs": "router-owned internal postcondition had ready inputs but no materialized evidence or router-visible blocker",
    "resolved_obligation_projection_still_live": "resolved Router obligation still had a live passive wait or blocked reminder projection",
    "role_output_event_missing_file_backed_body": "role output event was accepted without a file-backed body path and verified body hash",
    "role_output_status_prepared_used_as_decision": "role output status/progress was used as role event evidence",
    "pm_repair_followup_event_unmatchable": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "pm_repair_followup_event_not_normalized": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "fatal_repair_followup_event_unmatchable": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "fatal_repair_followup_event_not_normalized": "PM repair follow-up event could not be matched by normalized router resolution logic",
    "pm_repair_reissue_specs_not_materialized": "PM repair reissue specs did not materialize into packet runtime files, ledger, and dispatch index",
    "pm_repair_success_only_gate_after_unmaterialized_reissue": "PM repair recheck allowed only success while reviewer blocker or protocol outcome was not routable",
    "reviewer_recheck_protocol_blocker_unroutable": "PM repair recheck allowed only success while reviewer blocker or protocol outcome was not routable",
    "result_submitted_repair_target_not_superseded": "result_submitted repair target was replaced without being superseded",
    "old_packet_outcome_shape_accepted": "old packet outcome shape was accepted instead of mechanically blocked",
    "newer_same_family_repair_left_old_blocker_live": "newer same-family repair path left an older active blocker live",
    "active_blocker_noncurrent_target_not_blocked": "active blocker pointed at a noncurrent packet without current-target gate",
    "blocked_pm_repair_decision_reused": "blocked PM repair decision packet was reused instead of superseded and reissued",
    "blocked_pm_repair_decision_not_reissued": "blocked PM repair decision packet did not get a fresh current packet",
    "fallback_responsibility_used": "control-plane fallback responsibility was used instead of hard blocking",
    "same_family_staged_effect_expansion_not_stopped": "same-family staged effect expansion was not stopped",
    "repair_transaction_stale_after_success": "repair transaction success left stale active repair transaction or repair recheck pending action",
    "role_decision_wait_requires_unsatisfied_flag": "await_role_decision exposed an external event whose requires_flag was false",
    "phase_card_missing_required_upstream_source": "delivered phase card was missing required upstream source paths",
    "delivered_card_phase_context_stale": "delivered card current_phase did not match its actual workflow phase",
    "terminal_snapshot_flag_mismatch": "terminal route_state_snapshot flags disagreed with terminal run status",
    "child_skill_gate_manifest_review_unsynced": "child-skill gate manifest did not sync reviewer pass status",
    "gate_pass_left_active_block": "gate pass left the matching active gate outcome block live",
    "gate_pass_cleared_wrong_block": "gate pass cleared a different gate outcome block",
    "ack_consumed_semantic_wait_lost": "card ACK consumed the mechanical wait without exposing semantic gate outcome wait",
    "pm_impersonates_reviewer_followup": "reviewer follow-up event was accepted from the PM repair target role",
    "no_legal_next_with_valid_role_output": "no-legal-next control blocker was created while a valid role output was receivable",
    "duplicate_pm_repair_created_new_blocker": "duplicate PM repair decision created a new control blocker",
    "terminal_manual_resume_binding_cleanup_unproven": "terminal continuation cleanup lacked foreground-patrol or manual-resume lifecycle proof",
    "role_output_hash_replay_mismatch": "persisted role-output envelope hashes were not replayable against body paths",
    "frontier_stale_after_product_architecture_delivery": "execution frontier remained at material_scan after product architecture delivery",
    "display_view_stale_after_product_architecture_delivery": "route snapshot or display plan remained stale after product architecture delivery",
    "status_summary_stale": "status summary was published stale against frontier or packet state",
    "status_summary_leaks_sealed_or_source_fields": "status summary exposed sealed body, evidence table, source, or hash details",
    "status_summary_hides_unresolved_blocker": "status summary hid an unresolved blocker or pending repair state",
    "controller_user_reporting_policy_missing": "Controller user reporting policy was missing",
    "router_action_user_reporting_reminder_missing": "Router action lacked Controller plain-language user reporting reminder",
    "controller_table_prompt_user_language_guidance_missing": "Controller table prompt lacked plain-language user reporting guidance",
    "controller_reporting_budget_missing": "Controller user reporting policy lacked speak/silence budget",
    "quiet_internal_progress_user_chatter": "Controller quiet internal progress was user-visible chatter",
    "routine_aside_relayed_to_user": "Controller routine process aside was relayed to user",
    "user_report_not_limited_to_meaningful_change": "Controller user report was not limited to meaningful user-facing changes",
    "controller_user_report_internal_metadata_exposed": "Controller user report exposed internal action, packet, ledger, hash, contract, or diagnostic metadata",
    "router_action_user_reporting_reminder_displayed": "Router action user reporting reminder leaked into user-visible display text",
    "status_summary_missing_progress_facts": "status summary omitted compact progress facts",
    "status_summary_progress_counts_invalid": "status summary progress facts had inconsistent node counts",
    "status_summary_progress_exposes_internal_metadata": "status summary progress facts exposed internal metadata",
    "route_process_check_on_empty_route_draft": "route process check was delivered for an empty route draft",
    "route_process_check_on_shadow_route_draft": "route process check used a shadow route draft instead of the canonical route source",
    "route_draft_repair_kept_stale_route_checks": "route draft repair left stale route-check flags active",
    "node_local_block_route_mutated_without_reason": "node-local reviewer block was escalated to route mutation without a current-node-incapability reason",
    "same_node_repair_path_unroutable": "same-node reviewer-block repair had no router-routable follow-up path",
    "route_invalidating_block_handled_as_same_node_repair": "route-invalidating reviewer block was handled as same-node repair",
    "same_node_repair_reuses_stale_blocked_evidence": "same-node repair reused stale blocked evidence as passing evidence",
    "same_node_repair_without_reviewer_recheck": "same-node repair continued without same-review-class recheck",
    "route_mutation_without_current_node_incapability_reason": "route mutation lacked why the current node cannot contain the repair",
    "route_mutation_continues_without_route_recheck": "route mutation continued without resetting and rerunning route checks",
    "multiple_active_tasks_without_explicit_active_set": "multiple active UI tasks were exposed without explicit active-set authority",
    "role_work_wait_without_status_packet_read": "role-work wait did not expose matching controller status packet",
    "role_work_status_grants_packet_dir": "role-work progress visibility grant exposed more than controller status packet",
    "role_work_status_leaks_findings": "controller-visible progress status leaked sealed body details",
    "role_work_progress_manual_write": "role progress status update bypassed packet runtime",
    "role_work_progress_nonnumeric": "role progress status was not a nonnegative numeric value",
    "progress_default_packet_only": "work-package progress was not default for all role work",
    "role_output_progress_prompt_missing": "formal role-output work lacked shared progress prompt coverage",
    "role_output_wait_without_status_packet_read": "role-output wait did not expose matching controller status packet",
    "role_output_status_grants_output_dir": "role-output progress visibility grant exposed more than controller status packet",
    "role_output_status_leaks_findings": "controller-visible role-output progress status leaked sealed body details",
    "role_output_progress_manual_write": "role-output progress status update bypassed packet runtime",
    "role_output_progress_nonnumeric": "role-output progress status was not a nonnegative numeric value",
    "progress_status_used_as_decision": "progress status was used as role decision evidence",
    "optimized_transaction_without_hash_check": "optimized relay transaction skipped delivery, receipt, result-return, role, or hash evidence",
    "optimized_ack_without_role_check": "optimized card ack consumption skipped ack validation, role check, or hash check",
    "optimized_ack_without_hash_check": "optimized card ack consumption skipped ack validation, role check, or hash check",
    "valid_card_ack_file_present_role_event_blocked": "valid card ACK file was present but role event was blocked before Router consumed the ACK",
    "valid_card_bundle_ack_file_present_role_event_blocked": "valid card ACK file was present but role event was blocked before Router consumed the ACK",
    "pre_event_ack_auto_consumed_without_validation": "pre-event card ACK consumption skipped validation or did not resolve ledger before accepting role event",
    "pre_event_invalid_ack_accepted_role_event": "pre-event ACK reconciliation accepted a role event after an invalid or incomplete ACK",
    "pre_event_incomplete_bundle_ack_accepted_role_event": "pre-event ACK reconciliation accepted a role event after an invalid or incomplete ACK",
    "pre_event_ack_cleared_role_wait_authority": "pre-event ACK reconciliation cleared the role event wait authority",
    "pre_event_ack_wrote_duplicate_completed_return": "pre-event ACK reconciliation wrote duplicate completed-return records",
    "pre_event_ack_selected_wrong_pending_return": "pre-event ACK reconciliation consumed a non-matching pending return",
    "missing_ack_report_accepted_without_ack": "missing-ACK report was accepted before the card ACK existed",
    "missing_ack_recovery_without_quarantine": "missing-ACK report recovery requested reread without quarantining the premature report",
    "quarantined_report_used_as_evidence": "quarantined pre-ACK report was used as acceptance evidence",
    "old_pre_ack_report_revived_after_ack": "old pre-ACK report was revived after ACK instead of requiring a fresh report",
    "first_missing_ack_escalated_to_pm_blocker": "first recoverable missing-ACK report escalated to a generic PM/control blocker",
    "unrelated_pending_ack_quarantined_report": "unrelated pending card return quarantined a report with no matching dependency",
    "repeated_missing_ack_recovery_not_escalated": "repeated missing-ACK recovery failure did not escalate to PM",
    "pending_wait_reconciled_from_chat": "pending wait reconciliation used chat or history instead of durable packet state",
    "pending_wait_reconciled_without_status_packet": "pending wait reconciliation skipped packet ledger, status packet, role, or hash evidence",
    "pending_wait_not_reconciled_despite_existing_result": "pending wait had durable result evidence but was not reconciled before waiting",
    "stale_wait_reissued_after_existing_result": "stale wait was reissued after durable packet result already existed",
    "partial_batch_result_count_not_refreshed": "partial batch returned result was not reflected in member returned count",
    "partial_batch_missing_role_summary_stale": "partial batch missing-role summary was stale",
    "status_summary_waits_for_completed_partial_batch_role": "status summary named a completed role instead of the remaining partial-batch role",
    "duplicate_result_reconciliation_incremented_count": "duplicate wait reconciliation incremented a packet result more than once",
    "role_work_result_routed_to_reviewer": "PM role-work result did not route back to project_manager",
    "current_node_result_routed_to_reviewer": "current-node worker result did not route back to project_manager",
    "pm_decides_from_incomplete_model_miss_report": "PM model-miss decision used an incomplete FlowGuard operator report",
    "role_memory_used_as_completion_authority": "role memory was used as approval or completion authority",
    "operation_replay_reuses_controller_action_id": "operation replay reused a closed Controller action identity",
    "operation_replay_targets_superseded_generation": "operation replay targeted a superseded material packet generation",
    "material_result_relay_replay_without_ledger_authority": "material result relay replay lacked current packet-ledger and material-index authority",
    "controller_repair_work_packet_receipt_not_folded": "controller_repair_work_packet receipt did not fold the repair transaction",
    "controller_repair_work_packet_facade_export_missing": "controller_repair_work_packet receipt helper was not exported through the Router facade",
    "pm_material_disposition_generation_blind": "PM material result disposition was not scoped to the current packet generation",
    "stale_pm_material_disposition_restored": "stale PM material disposition was restored as current-generation success",
    "material_progress_flags_not_generation_scoped": "material progress flags were not scoped to the active material generation",
    "material_next_action_uses_stale_global_flags": "material next action was derived from stale run-wide material flags instead of active batch state",
    "material_reissue_keeps_stale_progress_flags": "material packet reissue left superseded progress flags visible for the current generation",
    "stale_material_progress_flags_resurrected_by_save": "stale run-state save restored superseded material progress flags after current generation reset",
    "material_dispatch_block_stale_generation": "material dispatch protocol block referenced a superseded repair generation",
    "role_output_duplicate_not_deduped": "role-output events were not deduped by event type and body reference",
    "role_output_current_generation_short_circuited_by_global_flag": "role-output reconciliation short-circuited current-generation material event on a run-wide flag",
    "pm_package_disposition_reconciled_without_domain_commit": "role-output package disposition reconciliation recorded event progress before domain artifact commit",
    "pm_package_disposition_not_semantic_deduped": "PM package dispositions were not deduped by semantic batch identity",
    "pm_package_disposition_conflict_unchecked": "PM package disposition body_hash was not checked as conflict evidence",
    "pm_package_repair_owned_conflict_replay_not_quarantined": "repair-owned PM package disposition body_hash conflict replay was not quarantined",
    "pm_package_repair_owned_conflict_replay_lost_wait": "repair-owned PM package disposition body_hash conflict replay did not preserve the legal wait",
    "pm_package_repair_owned_conflict_replay_crashed_daemon": "repair-owned PM package disposition body_hash conflict replay crashed the daemon",
    "pm_package_repair_owned_conflict_accepted_as_success": "repair-owned PM package disposition body_hash conflict replay was accepted as a successful disposition",
    "pm_package_repair_owned_conflict_duplicate_blocker": "repair-owned PM package disposition body_hash conflict replay created a duplicate blocker",
    "pm_package_stale_unowned_conflict_replay_not_quarantined": "stale unowned PM package disposition body_hash conflict replay was not quarantined",
    "pm_package_stale_unowned_conflict_replay_reverted_canonical": "stale unowned PM package disposition body_hash conflict replay did not preserve canonical body",
    "pm_package_stale_unowned_conflict_replay_crashed_daemon": "stale unowned PM package disposition body_hash conflict replay crashed the daemon",
    "pm_package_stale_unowned_conflict_accepted_as_success": "stale unowned PM package disposition body_hash conflict replay was accepted as a successful disposition",
    "pm_package_disposition_packet_outcomes_missing": "PM package disposition did not record per-packet outcomes",
    "pm_package_authority_split_lost_wait": "recorded PM package disposition without canonical authority closed the legal wait before preserving it or repairing the canonical domain commit",
    "pm_package_authority_split_crashed_daemon": "recorded PM package disposition without canonical authority crashed the daemon",
    "pm_package_authority_split_accepted_as_success": "recorded PM package disposition without canonical authority was accepted as successful progress",
    "packet_result_author_identity_not_replayable": "packet result author identity was not replayable from the packet ledger",
    "break_glass_patch_validation_pending": "break-glass patch record remained pending validation after validation evidence existed",
    "controller_reads_sealed_body": "Controller read sealed packet/result body",
}




def _build_graph() -> dict[str, object]:
    initial = model.initial_state()
    queue: deque[model.State] = deque([initial])
    states: list[model.State] = [initial]
    index = {initial: 0}
    edges: list[list[tuple[str, int]]] = []
    labels: set[str] = set()
    invariant_failures: list[dict[str, object]] = []

    while queue:
        state = queue.popleft()
        source = index[state]
        while len(edges) <= source:
            edges.append([])
        failures = model.invariant_failures(state)
        if failures:
            invariant_failures.append({"state": _state_id(state), "failures": failures})
        for label, new_state in model.next_states(state):
            labels.add(label)
            if new_state not in index:
                index[new_state] = len(states)
                states.append(new_state)
                queue.append(new_state)
            edges[source].append((label, index[new_state]))
    return {
        "states": states,
        "edges": edges,
        "labels": labels,
        "edge_count": sum(len(outgoing) for outgoing in edges),
        "invariant_failures": invariant_failures,
    }


def _progress_report(graph: dict[str, object]) -> dict[str, object]:
    states: list[model.State] = graph["states"]
    edges: list[list[tuple[str, int]]] = graph["edges"]
    terminal = {idx for idx, state in enumerate(states) if model.is_terminal(state)}
    can_reach_terminal = set(terminal)
    changed = True
    while changed:
        changed = False
        for idx, outgoing in enumerate(edges):
            if idx not in can_reach_terminal and any(target in can_reach_terminal for _label, target in outgoing):
                can_reach_terminal.add(idx)
                changed = True
    stuck = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in terminal and not edges[idx]
    ]
    cannot_reach_terminal = [
        _state_id(state)
        for idx, state in enumerate(states)
        if idx not in can_reach_terminal
    ]
    return {
        "ok": not stuck and not cannot_reach_terminal and 0 in can_reach_terminal,
        "stuck_state_count": len(stuck),
        "stuck_state_samples": stuck[:10],
        "cannot_reach_terminal_count": len(cannot_reach_terminal),
        "cannot_reach_terminal_samples": cannot_reach_terminal[:10],
    }


def _check_hazards() -> dict[str, object]:
    hazards: dict[str, object] = {}
    ok = True
    for name, state in model.hazard_states().items():
        failures = model.invariant_failures(state)
        expected = HAZARD_EXPECTED_FAILURES[name]
        detected = any(expected in failure for failure in failures)
        hazards[name] = {
            "detected": detected,
            "expected_failure": expected,
            "failures": failures,
            "state": state.__dict__,
        }
        ok = ok and detected
    return {"ok": ok, "hazards": hazards}


def _flowguard_report() -> dict[str, object]:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=model.MAX_SEQUENCE_LENGTH,
        terminal_predicate=lambda _input, state, _trace: model.is_terminal(state),
        success_predicate=lambda state, _trace: model.is_success(state),
        required_labels=REQUIRED_LABELS,
    ).explore()
    return {
        "ok": report.ok,
        "summary": report.summary,
        "violation_count": len(report.violations),
        "dead_branch_count": len(report.dead_branches),
        "exception_branch_count": len(report.exception_branches),
        "reachability_failure_count": len(report.reachability_failures),
        "reachability_failures": [failure.message for failure in report.reachability_failures],
    }


def _scenario_metrics(graph: dict[str, object]) -> dict[str, object]:
    complete_states = [state for state in graph["states"] if model.is_success(state)]
    expanded_steps = [state.handoff_steps for state in complete_states if state.mode == "expanded"]
    optimized_steps = [state.handoff_steps for state in complete_states if state.mode == "optimized"]
    expanded = min(expanded_steps) if expanded_steps else None
    optimized = min(optimized_steps) if optimized_steps else None
    saved = None if expanded is None or optimized is None else expanded - optimized
    percent = None if not expanded or saved is None else round((saved / expanded) * 100, 2)
    return {
        "expanded_safe_flow_min_steps": expanded,
        "optimized_safe_flow_min_steps": optimized,
        "handoff_steps_saved": saved,
        "handoff_step_reduction_percent": percent,
        "optimization_passes_same_invariants": bool(expanded_steps and optimized_steps),
    }


def run_checks(*, json_out_requested: bool = False, live_root: Path | None = Path(".")) -> dict[str, object]:
    graph = _build_graph()
    labels = set(graph["labels"])
    missing_labels = sorted(set(REQUIRED_LABELS) - labels)
    safe_graph = {
        "ok": not graph["invariant_failures"] and not missing_labels,
        "state_count": len(graph["states"]),
        "edge_count": graph["edge_count"],
        "missing_labels": missing_labels,
        "invariant_failures": graph["invariant_failures"],
    }
    progress = _progress_report(graph)
    explorer = _flowguard_report()
    hazards = _check_hazards()
    metrics = _scenario_metrics(graph)
    live_run_audit = (
        model.audit_live_run(live_root)
        if live_root is not None
        else {
            "ok": True,
            "skipped": True,
            "skip_reason": "skipped_with_reason: --skip-live-audit was provided",
            "findings": [],
            "projected_invariant_failures": [],
        }
    )
    skipped_checks = {
        "production_mutation": (
            "skipped_with_reason: this model check is read-only and does not "
            "repair FlowPilot runtime artifacts"
        )
    }
    if live_run_audit.get("skipped"):
        skipped_checks["live_run_audit"] = live_run_audit.get("skip_reason")
    if not json_out_requested:
        skipped_checks["default_results_file"] = "skipped_with_reason: no --json-out path was provided"
    return {
        "ok": bool(safe_graph["ok"])
        and bool(progress["ok"])
        and bool(explorer["ok"])
        and bool(hazards["ok"])
        and bool(metrics["optimization_passes_same_invariants"])
        and bool(live_run_audit["ok"]),
        "safe_graph": safe_graph,
        "progress": progress,
        "flowguard_explorer": explorer,
        "hazard_checks": hazards,
        "scenario_metrics": metrics,
        "live_run_audit": live_run_audit,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, help="Optional path for writing the JSON result payload.")
    parser.add_argument(
        "--live-root",
        type=Path,
        default=Path("."),
        help="Project root containing .flowpilot/current.json for read-only live-run audit.",
    )
    parser.add_argument("--skip-live-audit", action="store_true", help="Run only the abstract FlowGuard model.")
    args = parser.parse_args()

    result = run_checks(
        json_out_requested=bool(args.json_out),
        live_root=None if args.skip_live_audit else args.live_root,
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

