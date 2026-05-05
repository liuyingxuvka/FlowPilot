from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from flowguard import Explorer  # noqa: E402

import packet_control_plane_model as model  # noqa: E402


def main() -> int:
    report = Explorer(
        workflow=model.build_workflow(),
        initial_states=(model.initial_state(),),
        external_inputs=model.EXTERNAL_INPUTS,
        invariants=model.INVARIANTS,
        max_sequence_length=1,
        terminal_predicate=model.terminal_predicate,
        required_labels=(
            "pm_packet_issued",
            "packet_physical_files_written",
            "missing_physical_packet_files_blocked",
            "controller_reminder_checked",
            "controller_missing_pm_reminder",
            "controller_handoff_envelope_only",
            "controller_handoff_body_content_blocked",
            "controller_relay_signature_recorded",
            "major_node_chat_mermaid_displayed_when_cockpit_missing",
            "controller_contamination_returned_to_sender",
            "controller_executes_worker_body_returned_to_sender",
            "private_delivery_returned_to_sender",
            "missing_controller_relay_signature_blocked",
            "unopened_letter_sent_to_pm_for_restart_or_repair",
            "reviewer_dispatch_approved",
            "packet_delivered_to_wrong_role_blocked",
            "body_hash_mismatch_blocked",
            "stale_packet_body_reused_after_route_mutation_blocked",
            "worker_result_envelope",
            "controller_relayed_result_envelope_with_holder_status_update",
            "missing_result_controller_relay_signature_blocked",
            "unopened_result_letter_sent_to_pm_for_restart_or_repair",
            "result_envelope_checked",
            "review_pass_after_role_origin_audit",
            "pm_advanced",
            "controller_origin_artifact_blocked",
            "result_completed_by_wrong_role_blocked",
            "result_body_hash_mismatch_blocked",
            "stale_result_body_reused_after_route_mutation_blocked",
            "pm_repair_required_after_invalid_role_origin",
            "pm_repair_required_after_body_integrity_block",
            "reviewer_dispatch_blocked",
            "heartbeat_state_loaded",
            "heartbeat_resume_pm_requested",
            "heartbeat_pm_packet_issued",
            "heartbeat_pm_missing_controller_reminder",
            "heartbeat_loaded_worker_result_for_review",
            "heartbeat_ambiguous_worker_blocked",
            "heartbeat_missing_state_blocked",
        ),
    ).explore()
    print(report.format_text())
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
