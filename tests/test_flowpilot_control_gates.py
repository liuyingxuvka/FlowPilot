from __future__ import annotations

import unittest

from simulations import capability_model, meta_model


class FlowPilotControlGateTests(unittest.TestCase):
    def test_meta_reviewer_cannot_start_before_pm_release(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=False,
            pm_released_reviewer_for_current_gate=False,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("PM release order", result.message)

    def test_meta_reviewer_starts_after_pm_release(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertTrue(result.ok)

    def test_meta_reviewer_requires_packet_role_origin_audit(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=False,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("role-origin audit", result.message)

    def test_meta_reviewer_requires_packet_envelope_body_audit(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=False,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("envelope/body audit", result.message)

    def test_meta_reviewer_requires_controller_mail_chain_audit(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=False,
            recipient_pre_open_relay_check_done=False,
            packet_mail_chain_audit_done=False,
            unopened_mail_pm_recovery_policy_recorded=False,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("mail-chain audit", result.message)

    def test_meta_router_hard_rejection_requires_lane_artifact(self) -> None:
        state = meta_model.State(router_hard_rejection_seen=True)

        result = meta_model.router_hard_rejection_requires_control_blocker_lane(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("control blocker artifact", result.message)

    def test_meta_router_hard_rejection_reissue_routes_to_responsible_role(self) -> None:
        state = meta_model.State(
            router_hard_rejection_seen=True,
            control_blocker_artifact_written=True,
            control_blocker_handling_lane="control_plane_reissue",
            control_blocker_delivered_to_pm=True,
        )

        result = meta_model.router_hard_rejection_requires_control_blocker_lane(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("responsible role", result.message)

    def test_meta_router_pm_repair_blocker_routes_to_pm(self) -> None:
        state = meta_model.State(
            router_hard_rejection_seen=True,
            control_blocker_artifact_written=True,
            control_blocker_handling_lane="pm_repair_decision_required",
            control_blocker_delivered_to_pm=True,
        )

        result = meta_model.router_hard_rejection_requires_control_blocker_lane(state, trace=())

        self.assertTrue(result.ok)

    def test_meta_reviewer_requires_physical_packet_runtime(self) -> None:
        state = meta_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=False,
            controller_context_body_exclusion_verified=False,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            node_human_review_context_loaded=True,
        )

        result = meta_model.pm_review_release_controls_reviewer_start(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("physical packet isolation", result.message)

    def test_meta_resume_requires_rehydration_report_before_pm(self) -> None:
        state = meta_model.State(
            heartbeat_loaded_state=True,
            heartbeat_loaded_frontier=True,
            heartbeat_loaded_crew_memory=True,
            heartbeat_restored_crew=True,
            heartbeat_rehydrated_crew=True,
            crew_rehydration_report_written=False,
            replacement_roles_seeded_from_memory=True,
            heartbeat_pm_decision_requested=True,
        )

        result = meta_model.crew_memory_rehydration_required(state, trace=())

        self.assertFalse(result.ok)
        self.assertIn("six-role memory rehydration", result.message)

    def test_capability_reviewer_cannot_start_before_pm_release(self) -> None:
        state = capability_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=False,
            pm_released_reviewer_for_current_gate=False,
            implementation_human_review_context_loaded=True,
        )

        result = capability_model.pm_review_release_controls_reviewer_start(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("PM release order", result.message)

    def test_capability_reviewer_requires_packet_role_origin_audit(self) -> None:
        state = capability_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=False,
            implementation_human_review_context_loaded=True,
        )

        result = capability_model.pm_review_release_controls_reviewer_start(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("role-origin audit", result.message)

    def test_capability_reviewer_requires_packet_envelope_body_audit(self) -> None:
        state = capability_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=False,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            implementation_human_review_context_loaded=True,
        )

        result = capability_model.pm_review_release_controls_reviewer_start(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("envelope/body audit", result.message)

    def test_capability_reviewer_requires_controller_mail_chain_audit(self) -> None:
        state = capability_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=True,
            controller_context_body_exclusion_verified=True,
            controller_relay_signature_audit_done=False,
            recipient_pre_open_relay_check_done=False,
            packet_mail_chain_audit_done=False,
            unopened_mail_pm_recovery_policy_recorded=False,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            implementation_human_review_context_loaded=True,
        )

        result = capability_model.pm_review_release_controls_reviewer_start(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("mail-chain audit", result.message)

    def test_capability_router_hard_rejection_requires_lane_artifact(self) -> None:
        state = capability_model.State(router_hard_rejection_seen=True)

        result = capability_model.router_hard_rejection_requires_control_blocker_lane(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("control blocker artifact", result.message)

    def test_capability_router_reissue_blocker_routes_to_responsible_role(self) -> None:
        state = capability_model.State(
            router_hard_rejection_seen=True,
            control_blocker_artifact_written=True,
            control_blocker_handling_lane="control_plane_reissue",
            control_blocker_delivered_to_responsible_role=True,
        )

        result = capability_model.router_hard_rejection_requires_control_blocker_lane(
            state,
            trace=(),
        )

        self.assertTrue(result.ok)

    def test_capability_router_fatal_blocker_routes_to_pm(self) -> None:
        state = capability_model.State(
            router_hard_rejection_seen=True,
            control_blocker_artifact_written=True,
            control_blocker_handling_lane="fatal_protocol_violation",
            control_blocker_delivered_to_responsible_role=True,
        )

        result = capability_model.router_hard_rejection_requires_control_blocker_lane(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("Project Manager", result.message)

    def test_capability_reviewer_requires_physical_packet_runtime(self) -> None:
        state = capability_model.State(
            pm_review_hold_instruction_written=True,
            worker_output_ready_for_review=True,
            pm_review_release_order_written=True,
            pm_released_reviewer_for_current_gate=True,
            packet_runtime_physical_files_written=False,
            controller_context_body_exclusion_verified=False,
            controller_relay_signature_audit_done=True,
            recipient_pre_open_relay_check_done=True,
            packet_mail_chain_audit_done=True,
            unopened_mail_pm_recovery_policy_recorded=True,
            packet_envelope_body_audit_done=True,
            packet_envelope_to_role_checked=True,
            packet_body_hash_verified=True,
            result_envelope_checked=True,
            result_body_hash_verified=True,
            completed_agent_id_role_verified=True,
            controller_body_boundary_verified=True,
            wrong_role_relabel_forbidden_verified=True,
            packet_role_origin_audit_done=True,
            packet_result_author_verified=True,
            packet_result_author_matches_assignment=True,
            implementation_human_review_context_loaded=True,
        )

        result = capability_model.pm_review_release_controls_reviewer_start(
            state,
            trace=(),
        )

        self.assertFalse(result.ok)
        self.assertIn("physical packet isolation", result.message)

    def test_capability_resume_requires_host_kind_evidence(self) -> None:
        state = capability_model.State(
            continuation_probe_done=True,
            continuation_host_kind_recorded=False,
            continuation_evidence_written=True,
            host_continuation_supported=False,
            manual_resume_mode_recorded=True,
        )

        self.assertFalse(capability_model._manual_resume_ready(state))


if __name__ == "__main__":
    unittest.main()
