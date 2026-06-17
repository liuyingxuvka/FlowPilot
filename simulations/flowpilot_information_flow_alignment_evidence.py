"""Information-flow alignment test-evidence catalog."""

from __future__ import annotations

from typing import Any

from flowpilot_model_test_alignment_common import EDGE, HAPPY, NEGATIVE, REPLAY, _evidence
from flowpilot_information_flow_alignment_obligations import (
    OBL_BLOCKER_PAYLOAD,
    OBL_BREAK_GLASS,
    OBL_CLOSURE_STOP,
    OBL_FLOWGUARD_EVIDENCE_CONSISTENCY,
    OBL_FORMAL_REPAIR_IDENTITY,
    OBL_RECHECK_FOLLOWUP,
    OBL_REOPEN_HISTORY,
    OBL_REQUIRED_REPAIR,
    OBL_RESUME_CURRENT,
    OBL_ROLE_ASSIGNMENT,
    OBL_ROUTE_MUTATION,
    OBL_RUNTIME_SELF_CHECK,
    OBL_STAGE_EVIDENCE_MATRIX,
    OBL_WORKER_DELTA,
)


def _test_evidence() -> tuple[Any, ...]:
    return (
        _evidence(
            "info_flow.test.pm_summary_positive",
            test_name="test_pm_repair_packet_includes_recent_role_report_summary",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_pm_repair_packet_includes_recent_role_report_summary -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
            code_contracts=(
                "info_flow.runtime.ensure_pm_repair_packet",
                "info_flow.runtime.recent_role_reports",
                "info_flow.runtime.authorized_result_reads",
            ),
        ),
        _evidence(
            "info_flow.test.pm_opened_body_validation",
            test_name="test_pm_result_disposition_requires_opened_result_body",
            path="tests/test_flowpilot_information_flow_alignment.py",
            command=(
                "python -m pytest tests/test_flowpilot_information_flow_alignment.py "
                "-k test_pm_result_disposition_requires_opened_result_body -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
            code_contracts=("info_flow.runtime.pm_opened_result_bodies",),
        ),
        _evidence(
            "info_flow.test.pm_packet_open_delivers_authorized_body",
            test_name="test_pm_repair_decision_receives_authorized_block_report_with_packet_open",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_pm_repair_decision_receives_authorized_block_report_with_packet_open -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_BLOCKER_PAYLOAD, OBL_REQUIRED_REPAIR),
            code_contracts=(
                "info_flow.runtime.authorized_result_reads",
                "info_flow.runtime.open_packet_authorized_material_delivery",
            ),
        ),
        _evidence(
            "info_flow.test.missing_pm_summary_negative",
            test_name="test_missing_pm_visible_summary_is_mechanically_reissued",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_missing_pm_visible_summary_is_mechanically_reissued -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_BLOCKER_PAYLOAD,),
            code_contracts=("info_flow.runtime.ensure_pm_repair_packet",),
        ),
        _evidence(
            "info_flow.test.worker_repair_packet_positive",
            test_name="test_reviewer_required_repair_reaches_pm_repair_packet",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_reviewer_required_repair_reaches_pm_repair_packet -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_WORKER_DELTA,),
            code_contracts=(
                "info_flow.runtime.apply_pm_repair_decision",
                "info_flow.runtime.issue_current_scope_repair_packet",
            ),
        ),
        _evidence(
            "info_flow.test.required_repair_edge",
            test_name="test_reviewer_required_repair_reaches_pm_repair_packet",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_reviewer_required_repair_reaches_pm_repair_packet -q"
            ),
            test_kind=EDGE,
            covers=(OBL_REQUIRED_REPAIR, OBL_WORKER_DELTA),
            code_contracts=(
                "info_flow.runtime.apply_pm_repair_decision",
                "info_flow.runtime.issue_current_scope_repair_packet",
            ),
        ),
        _evidence(
            "info_flow.test.pm_summary_no_fallback_negative",
            test_name="test_pm_repair_decision_summary_is_not_reason_fallback",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_pm_repair_decision_summary_is_not_reason_fallback -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_REQUIRED_REPAIR, OBL_WORKER_DELTA),
            code_contracts=("info_flow.runtime.apply_pm_repair_decision",),
        ),
        _evidence(
            "info_flow.test.followup_recheck_positive",
            test_name="test_repair_transaction_recheck_blocker_registers_followup_blocker",
            path="tests/router_runtime/control_blockers.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.control_blockers."
                "ControlBlockersRuntimeTests."
                "test_repair_transaction_recheck_blocker_registers_followup_blocker"
            ),
            test_kind=HAPPY,
            covers=(OBL_RECHECK_FOLLOWUP,),
            code_contracts=("info_flow.closure.classify_control_blocker",),
        ),
        _evidence(
            "info_flow.test.followup_protocol_edge",
            test_name="test_repair_transaction_protocol_blocker_registers_followup_blocker",
            path="tests/router_runtime/control_blockers.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.control_blockers."
                "ControlBlockersRuntimeTests."
                "test_repair_transaction_protocol_blocker_registers_followup_blocker"
            ),
            test_kind=EDGE,
            covers=(OBL_RECHECK_FOLLOWUP,),
            code_contracts=("info_flow.closure.classify_control_blocker",),
        ),
        _evidence(
            "info_flow.test.required_recheck_packet_replay",
            test_name="test_reattach_required_recheck_freshens_flowguard_then_reviewer_before_clear",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_reattach_required_recheck_freshens_flowguard_then_reviewer_before_clear -q"
            ),
            test_kind=REPLAY,
            covers=(OBL_FORMAL_REPAIR_IDENTITY, OBL_RECHECK_FOLLOWUP),
            code_contracts=(
                "info_flow.runtime.required_recheck_packet",
                "info_flow.runtime.packet_repair_blocker_id",
                "info_flow.runtime.formal_repair_identity_gate",
            ),
        ),
        _evidence(
            "info_flow.test.current_scope_repair_identity_positive",
            test_name="test_repair_packet_handoff_contract_carries_formal_blocker_identity",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_repair_packet_handoff_contract_carries_formal_blocker_identity -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_FORMAL_REPAIR_IDENTITY,),
            code_contracts=(
                "info_flow.runtime.apply_pm_repair_decision",
                "info_flow.runtime.issue_current_scope_repair_packet",
                "info_flow.runtime.packet_repair_blocker_id",
            ),
        ),
        _evidence(
            "info_flow.test.flowguard_consistency_self_check_negative",
            test_name="test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_flowguard_packet_rejects_failed_contract_self_check_without_reviewer -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_FLOWGUARD_EVIDENCE_CONSISTENCY,),
            code_contracts=("info_flow.runtime.flowguard_evidence_consistency_gate",),
        ),
        _evidence(
            "info_flow.test.flowguard_consistency_pass_to_reviewer",
            test_name="test_review_packet_rejects_generic_decision_summary_result",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_review_packet_rejects_generic_decision_summary_result -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_FLOWGUARD_EVIDENCE_CONSISTENCY,),
            code_contracts=(
                "info_flow.runtime.flowguard_evidence_consistency_gate",
                "info_flow.runtime.review_packet_requires_matching_flowguard_report",
            ),
        ),
        _evidence(
            "info_flow.test.flowguard_consistency_child_block_negative",
            test_name="test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_flowguard_packet_rejects_deleted_evidence_consistency_field_without_reviewer -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_FLOWGUARD_EVIDENCE_CONSISTENCY,),
            code_contracts=(
                "info_flow.runtime.flowguard_evidence_consistency_gate",
                "info_flow.runtime.review_packet_requires_matching_flowguard_report",
            ),
        ),
        _evidence(
            "info_flow.test.flowguard_consistency_legal_block_replay",
            test_name="test_flowguard_packet_block_with_compact_blocker_does_not_issue_reviewer",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_flowguard_packet_block_with_compact_blocker_does_not_issue_reviewer -q"
            ),
            test_kind=REPLAY,
            covers=(OBL_FLOWGUARD_EVIDENCE_CONSISTENCY,),
            code_contracts=(
                "info_flow.runtime.flowguard_evidence_consistency_gate",
                "info_flow.runtime.review_packet_requires_matching_flowguard_report",
            ),
        ),
        _evidence(
            "info_flow.test.stage_matrix_family_coverage",
            test_name="test_stage_evidence_matrix_covers_every_packet_result_family",
            path="tests/test_flowpilot_high_standard_control_flow.py",
            command=(
                "python -m unittest "
                "tests.test_flowpilot_high_standard_control_flow."
                "FlowPilotHighStandardControlFlowTests."
                "test_stage_evidence_matrix_covers_every_packet_result_family"
            ),
            test_kind=HAPPY,
            covers=(OBL_STAGE_EVIDENCE_MATRIX,),
            code_contracts=("info_flow.runtime.packet_stage_evidence_matrix",),
        ),
        _evidence(
            "info_flow.test.stage_matrix_all_package_handoffs",
            test_name="test_generated_packet_handoffs_include_stage_matrix_for_each_package_class",
            path="tests/test_flowpilot_high_standard_control_flow.py",
            command=(
                "python -m unittest "
                "tests.test_flowpilot_high_standard_control_flow."
                "FlowPilotHighStandardControlFlowTests."
                "test_generated_packet_handoffs_include_stage_matrix_for_each_package_class"
            ),
            test_kind=REPLAY,
            covers=(OBL_STAGE_EVIDENCE_MATRIX,),
            code_contracts=(
                "info_flow.runtime.build_current_handoff_contract",
                "info_flow.runtime.flowguard_subject_stage_matrix",
                "info_flow.runtime.review_subject_stage_matrix",
            ),
        ),
        _evidence(
            "info_flow.test.stage_matrix_preplanning_negative",
            test_name="test_high_standard_flowguard_packet_uses_preplanning_stage_matrix",
            path="tests/test_flowpilot_high_standard_control_flow.py",
            command=(
                "python -m unittest "
                "tests.test_flowpilot_high_standard_control_flow."
                "FlowPilotHighStandardControlFlowTests."
                "test_high_standard_flowguard_packet_uses_preplanning_stage_matrix"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_STAGE_EVIDENCE_MATRIX,),
            code_contracts=("info_flow.runtime.flowguard_subject_stage_matrix",),
        ),
        _evidence(
            "info_flow.test.runtime_self_check_receipt_positive",
            test_name="test_start_run_records_portable_runtime_self_check_receipt",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m unittest "
                "tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests."
                "test_start_run_records_portable_runtime_self_check_receipt"
            ),
            test_kind=HAPPY,
            covers=(OBL_RUNTIME_SELF_CHECK,),
            code_contracts=("info_flow.runtime.record_runtime_self_check_receipt",),
        ),
        _evidence(
            "info_flow.test.runtime_self_check_no_dev_script_negative",
            test_name="test_runtime_self_check_does_not_require_target_project_simulations",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m unittest "
                "tests.test_flowpilot_new_entrypoint.FlowPilotNewEntrypointTests."
                "test_runtime_self_check_does_not_require_target_project_simulations"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_RUNTIME_SELF_CHECK,),
            code_contracts=("info_flow.runtime.runtime_self_check_receipt",),
        ),
        _evidence(
            "info_flow.test.handoff_contract_visible_edge",
            test_name="test_packet_handoff_contract_is_visible_in_envelope_body_and_role_handoff",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_packet_handoff_contract_is_visible_in_envelope_body_and_role_handoff -q"
            ),
            test_kind=EDGE,
            covers=(OBL_FORMAL_REPAIR_IDENTITY,),
            code_contracts=("info_flow.runtime.build_current_handoff_contract",),
        ),
        _evidence(
            "info_flow.test.staged_effect_convergence_edge",
            test_name="test_staged_effect_same_family_rejects_different_formal_blocker_identity",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_staged_effect_same_family_rejects_different_formal_blocker_identity -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_FORMAL_REPAIR_IDENTITY,),
            code_contracts=("info_flow.runtime.attach_staged_effect",),
        ),
        _evidence(
            "info_flow.test.formal_repair_identity_mismatch_negative",
            test_name="test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker",
            path="tests/test_flowpilot_core_runtime.py",
            command=(
                "python -m pytest tests/test_flowpilot_core_runtime.py "
                "-k test_formal_repair_identity_mismatch_is_runtime_mechanical_blocker -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_FORMAL_REPAIR_IDENTITY,),
            code_contracts=(
                "info_flow.runtime.formal_repair_identity_gate",
                "info_flow.runtime.build_current_handoff_contract",
            ),
        ),
        _evidence(
            "info_flow.test.lifecycle_resume_on_demand_assignment_positive",
            test_name="test_manual_resume_uses_lifecycle_guard_without_heartbeat_or_role_prewarm",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m pytest tests/test_flowpilot_new_entrypoint.py "
                "-k test_manual_resume_uses_lifecycle_guard_without_heartbeat_or_role_prewarm -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_RESUME_CURRENT, OBL_ROLE_ASSIGNMENT),
            code_contracts=(
                "info_flow.new_runtime.resume_entrypoint",
                "info_flow.runtime.record_resume_request",
                "info_flow.runtime.reconcile_resume_request",
                "info_flow.new_runtime.dispatch_current_role",
                "info_flow.runtime.resolve_role_assignment",
                "info_flow.runtime.lease_agent",
            ),
        ),
        _evidence(
            "info_flow.test.plain_resume_does_not_reissue_stopped_blocker_negative",
            test_name="test_resolve_stopped_blocker_requires_explicit_user_request_before_reissue",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m pytest tests/test_flowpilot_new_entrypoint.py "
                "-k test_resolve_stopped_blocker_requires_explicit_user_request_before_reissue -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_RESUME_CURRENT,),
            code_contracts=("info_flow.new_runtime.resume_entrypoint", "info_flow.runtime.reconcile_resume_request"),
        ),
        _evidence(
            "info_flow.test.role_assignment_wrong_responsibility_negative",
            test_name="test_flowguard_operator_is_leased_through_its_own_packet",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m pytest tests/test_flowpilot_new_entrypoint.py "
                "-k test_flowguard_operator_is_leased_through_its_own_packet -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_ROLE_ASSIGNMENT,),
            code_contracts=(
                "info_flow.new_runtime.dispatch_current_role",
                "info_flow.runtime.resolve_role_assignment",
            ),
        ),
        _evidence(
            "info_flow.test.resume_fake_package_replay",
            test_name="test_resume_active_blocker_and_ambiguous_state_preempt_fake_package",
            path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
            command=(
                "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py "
                "-k test_resume_active_blocker_and_ambiguous_state_preempt_fake_package -q"
            ),
            test_kind=REPLAY,
            covers=(OBL_RESUME_CURRENT, OBL_REOPEN_HISTORY),
            code_contracts=("info_flow.runtime.reconcile_resume_request",),
        ),
        _evidence(
            "info_flow.test.historical_replay_negative",
            test_name="test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence",
            path="tests/test_flowpilot_historical_live_run_replay.py",
            command=(
                "python -m pytest tests/test_flowpilot_historical_live_run_replay.py "
                "-k test_historical_snapshot_and_background_packages_reject_stale_or_incomplete_evidence -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_REOPEN_HISTORY,),
            code_contracts=("info_flow.runtime.reconcile_resume_request",),
        ),
        _evidence(
            "info_flow.test.break_glass_incident_positive",
            test_name="test_break_glass_helper_records_incident_and_patch",
            path="tests/test_flowpilot_controller_break_glass.py",
            command=(
                "python -m pytest tests/test_flowpilot_controller_break_glass.py "
                "-k test_break_glass_helper_records_incident_and_patch -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_BREAK_GLASS,),
            code_contracts=("info_flow.break_glass.open_incident",),
        ),
        _evidence(
            "info_flow.test.break_glass_positive",
            test_name="test_recovery_supervisor_records_transaction_body_grant_and_reinjection",
            path="tests/test_flowpilot_controller_break_glass.py",
            command=(
                "python -m pytest tests/test_flowpilot_controller_break_glass.py "
                "-k test_recovery_supervisor_records_transaction_body_grant_and_reinjection -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_BREAK_GLASS,),
            code_contracts=(
                "info_flow.break_glass.record_control_plane_blocker",
                "info_flow.break_glass.open_recovery_transaction",
                "info_flow.break_glass.record_controller_reinjection",
                "info_flow.break_glass.close_recovery_transaction",
            ),
        ),
        _evidence(
            "info_flow.test.break_glass_negative",
            test_name="test_break_glass_close_rejects_unvalidated_permanent_patch",
            path="tests/test_flowpilot_controller_break_glass.py",
            command=(
                "python -m pytest tests/test_flowpilot_controller_break_glass.py "
                "-k test_break_glass_close_rejects_unvalidated_permanent_patch -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_BREAK_GLASS,),
            code_contracts=("info_flow.break_glass.close_incident",),
        ),
        _evidence(
            "info_flow.test.controller_repair_work_packet_positive",
            test_name="test_controller_repair_work_packet_queues_bounded_controller_action",
            path="tests/router_runtime/foreground_controller.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.foreground_controller."
                "ForegroundControllerRuntimeTests."
                "test_controller_repair_work_packet_queues_bounded_controller_action"
            ),
            test_kind=HAPPY,
            covers=(OBL_BREAK_GLASS, OBL_WORKER_DELTA),
            code_contracts=("info_flow.router.controller_repair_work_packet",),
        ),
        _evidence(
            "info_flow.test.route_mutation_positive",
            test_name="test_node_acceptance_plan_block_can_be_revised_on_same_node",
            path="tests/router_runtime/route_mutation_acceptance_repair.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.route_mutation_acceptance_repair."
                "RouteMutationAcceptanceRepairRuntimeTests."
                "test_node_acceptance_plan_block_can_be_revised_on_same_node"
            ),
            test_kind=HAPPY,
            covers=(OBL_ROUTE_MUTATION,),
            code_contracts=("info_flow.runtime.redesign_route_from_pm_decision",),
        ),
        _evidence(
            "info_flow.test.route_mutation_edge",
            test_name="test_parent_contract_route_mutation_new_transaction_is_not_swallowed_by_old_flag",
            path="tests/flowpilot_route_mutation_contracts.py",
            command=(
                "python -m pytest tests/flowpilot_route_mutation_contracts.py "
                "-k test_parent_contract_route_mutation_new_transaction_is_not_swallowed_by_old_flag -q"
            ),
            test_kind=EDGE,
            covers=(OBL_ROUTE_MUTATION,),
            code_contracts=("info_flow.runtime.redesign_route_from_pm_decision",),
        ),
        _evidence(
            "info_flow.test.route_mutation_stale_replay",
            test_name="test_route_mutation_stale_sibling_proof_fake_package",
            path="tests/test_flowpilot_synthetic_agent_trace_replay.py",
            command=(
                "python -m pytest tests/test_flowpilot_synthetic_agent_trace_replay.py "
                "-k test_route_mutation_stale_sibling_proof_fake_package -q"
            ),
            test_kind=REPLAY,
            covers=(OBL_ROUTE_MUTATION,),
            code_contracts=("info_flow.runtime.redesign_route_from_pm_decision",),
        ),
        _evidence(
            "info_flow.test.role_assignment_packet_specific_positive",
            test_name="test_flowguard_operator_is_leased_through_its_own_packet",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m pytest tests/test_flowpilot_new_entrypoint.py "
                "-k test_flowguard_operator_is_leased_through_its_own_packet -q"
            ),
            test_kind=HAPPY,
            covers=(OBL_ROLE_ASSIGNMENT,),
            code_contracts=(
                "info_flow.new_runtime.dispatch_current_role",
                "info_flow.runtime.resolve_role_assignment",
                "info_flow.runtime.lease_agent",
            ),
        ),
        _evidence(
            "info_flow.test.terminal_closure_negative",
            test_name="test_ack_only_and_pm_only_result_do_not_reach_terminal_closure",
            path="tests/test_flowpilot_new_entrypoint.py",
            command=(
                "python -m pytest tests/test_flowpilot_new_entrypoint.py "
                "-k test_ack_only_and_pm_only_result_do_not_reach_terminal_closure -q"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_CLOSURE_STOP,),
            code_contracts=("info_flow.closure.closure_blocks_progress",),
        ),
        _evidence(
            "info_flow.test.protocol_dead_end_terminal_negative",
            test_name="test_protocol_dead_end_terminal_family_suppresses_reopened_blocker",
            path="tests/router_runtime/control_blockers.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.control_blockers."
                "ControlBlockersRuntimeTests."
                "test_protocol_dead_end_terminal_family_suppresses_reopened_blocker"
            ),
            test_kind=NEGATIVE,
            covers=(OBL_CLOSURE_STOP,),
            code_contracts=("info_flow.closure.classify_control_blocker",),
        ),
        _evidence(
            "info_flow.test.user_stop_positive",
            test_name="test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work",
            path="tests/router_runtime/terminal.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.terminal.TerminalRuntimeTests."
                "test_user_stop_or_cancel_makes_run_terminal_and_blocks_next_work"
            ),
            test_kind=HAPPY,
            covers=(OBL_CLOSURE_STOP,),
            code_contracts=("info_flow.closure.closure_blocks_progress",),
        ),
        _evidence(
            "info_flow.test.terminal_quarantine_replay",
            test_name="test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts",
            path="tests/router_runtime/terminal.py",
            command=(
                "python -m unittest -v "
                "tests.router_runtime.terminal.TerminalRuntimeTests."
                "test_user_stop_quarantines_active_repair_and_historical_control_plane_artifacts"
            ),
            test_kind=REPLAY,
            covers=(OBL_CLOSURE_STOP,),
            code_contracts=("info_flow.closure.closure_blocks_progress",),
        ),
    )
