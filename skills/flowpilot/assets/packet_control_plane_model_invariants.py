"""Invariant registry for the packet control-plane FlowGuard model."""

from __future__ import annotations

from flowguard import Invariant
from packet_control_plane_model_invariants_origin import *
from packet_control_plane_model_invariants_handoff import *
from packet_control_plane_model_invariants_dispatch import *
from packet_control_plane_model_invariants_resume import *

INVARIANTS = (
    Invariant(
        "no_advance_from_controller_artifact",
        "Controller-origin implementation evidence cannot advance a route.",
        no_advance_from_controller_artifact,
    ),
    Invariant(
        "advance_requires_review_pass",
        "PM advancement requires reviewer pass.",
        advance_requires_review_pass,
    ),
    Invariant(
        "review_pass_requires_role_origin_audit",
        "Reviewer pass requires a per-packet role-origin audit.",
        review_pass_requires_role_origin_audit,
    ),
    Invariant(
        "review_pass_requires_mail_chain_audit",
        "Reviewer pass requires a full packet/result mail-chain audit.",
        review_pass_requires_mail_chain_audit,
    ),
    Invariant(
        "recipient_body_open_requires_current_assignment",
        "Recipients may open packet/result bodies only after validating a current assignment signature.",
        recipient_body_open_requires_current_assignment,
    ),
    Invariant(
        "missing_or_unopened_mail_requires_pm_restart_or_repair",
        "Unopened, private, or missing-assignment mail is sent to PM for restart, repair node, or sender reissue.",
        missing_or_unopened_mail_requires_pm_restart_or_repair,
    ),
    Invariant(
        "invalid_origin_block_requires_warning",
        "Invalid role origin requires a controller warning and PM repair/reissue requirement.",
        invalid_origin_block_requires_warning,
    ),
    Invariant(
        "controller_body_boundary_blocks_never_advance",
        "Controller body reads or execution attempts cannot dispatch, review, or advance.",
        controller_body_boundary_blocks_never_advance,
    ),
    Invariant(
        "controller_handoff_body_leak_never_advances",
        "Controller handoff containing packet body content cannot dispatch, review, or advance.",
        controller_handoff_body_leak_never_advances,
    ),
    Invariant(
        "missing_mutual_role_reminder_never_advances",
        "Controller-visible packet/result handoffs without mutual role reminders cannot dispatch, review, or advance.",
        missing_mutual_role_reminder_never_advances,
    ),
    Invariant(
        "current_assignment_requires_physical_files_and_envelope_only_handoff",
        "Current assignment requires physical packet files, envelope-only handoff, and visible mutual role reminders.",
        current_assignment_requires_physical_files_and_envelope_only_handoff,
    ),
    Invariant(
        "holder_change_requires_user_status_update",
        "Every packet holder change requires a user-visible status update.",
        holder_change_requires_user_status_update,
    ),
    Invariant(
        "cockpit_missing_major_node_requires_chat_mermaid",
        "Entering a major node while Cockpit is missing requires a chat Mermaid route sign.",
        cockpit_missing_major_node_requires_chat_mermaid,
    ),
    Invariant(
        "dispatch_requires_packet_envelope_and_hash_checks",
        "Router direct dispatch requires packet envelope and packet body hash checks.",
        dispatch_requires_packet_envelope_and_hash_checks,
    ),
    Invariant(
        "dispatch_requires_output_contract_and_run_scoped_result_paths",
        "Router direct dispatch requires an output contract and run-scoped result paths.",
        dispatch_requires_output_contract_and_run_scoped_result_paths,
    ),
    Invariant(
        "packet_integrity_blocks_never_advance",
        "Wrong delivery, packet body hash mismatch, stale body, bad contract, or unsafe result path cannot advance.",
        packet_integrity_blocks_never_advance,
    ),
    Invariant(
        "review_pass_requires_result_envelope_body_and_agent_checks",
        "Reviewer quality pass requires prior Runtime/Router result envelope, body hash, and completed-agent role checks.",
        review_pass_requires_result_envelope_body_and_agent_checks,
    ),
    Invariant(
        "result_body_integrity_blocks_never_advance",
        "Result body hash mismatch or stale result body cannot advance.",
        result_body_integrity_blocks_never_advance,
    ),
    Invariant(
        "result_relay_requires_packet_open_and_result_ledger",
        "Controller may relay a result only after packet open receipts and result ledger absorption exist.",
        result_relay_requires_packet_open_and_result_ledger,
    ),
    Invariant(
        "wrong_role_completion_never_advances",
        "Wrong-role completion cannot be cosigned, relabelled, or advanced.",
        wrong_role_completion_never_advances,
    ),
    Invariant(
        "result_requires_dispatch",
        "No role result exists without router direct dispatch approval.",
        result_requires_dispatch,
    ),
    Invariant(
        "dispatch_requires_controller_reminder",
        "Router direct dispatch cannot occur unless the PM reminder to the controller is present.",
        dispatch_requires_controller_reminder,
    ),
    Invariant(
        "packet_open_blocks_never_produce_result_or_advance",
        "Packet-open failures cannot produce a result or advance.",
        packet_open_blocks_never_produce_result_or_advance,
    ),
    Invariant(
        "result_ingress_rejection_never_produces_result_or_advance",
        "Stale, duplicate, inactive-lease, or noncurrent result submissions are rejected before result allocation.",
        result_ingress_rejection_never_produces_result_or_advance,
    ),
    Invariant(
        "manual_resume_packet_requires_pm_request",
        "Manual resume cannot mint a resume packet without first asking PM.",
        manual_resume_packet_requires_pm_request,
    ),
    Invariant(
        "manual_resume_packet_requires_loaded_state",
        "Manual resume packets require loaded current-run state.",
        manual_resume_packet_requires_loaded_state,
    ),
    Invariant(
        "ambiguous_worker_state_never_advances",
        "Ambiguous worker state blocks controller execution.",
        ambiguous_worker_state_never_advances,
    ),
    Invariant(
        "missing_manual_resume_state_never_advances",
        "Missing current-run state blocks manual resume execution.",
        missing_manual_resume_state_never_advances,
    ),
)

__all__ = [
    "no_advance_from_controller_artifact",
    "advance_requires_review_pass",
    "review_pass_requires_role_origin_audit",
    "review_pass_requires_mail_chain_audit",
    "recipient_body_open_requires_current_assignment",
    "missing_or_unopened_mail_requires_pm_restart_or_repair",
    "invalid_origin_block_requires_warning",
    "controller_body_boundary_blocks_never_advance",
    "controller_handoff_body_leak_never_advances",
    "missing_mutual_role_reminder_never_advances",
    "current_assignment_requires_physical_files_and_envelope_only_handoff",
    "holder_change_requires_user_status_update",
    "cockpit_missing_major_node_requires_chat_mermaid",
    "dispatch_requires_packet_envelope_and_hash_checks",
    "dispatch_requires_output_contract_and_run_scoped_result_paths",
    "packet_integrity_blocks_never_advance",
    "review_pass_requires_result_envelope_body_and_agent_checks",
    "result_body_integrity_blocks_never_advance",
    "result_relay_requires_packet_open_and_result_ledger",
    "wrong_role_completion_never_advances",
    "result_requires_dispatch",
    "dispatch_requires_controller_reminder",
    "packet_open_blocks_never_produce_result_or_advance",
    "result_ingress_rejection_never_produces_result_or_advance",
    "manual_resume_packet_requires_pm_request",
    "manual_resume_packet_requires_loaded_state",
    "ambiguous_worker_state_never_advances",
    "missing_manual_resume_state_never_advances",
    "INVARIANTS",
]
