"""State and case definitions for the packet control-plane FlowGuard model."""

from __future__ import annotations

from dataclasses import dataclass, replace

@dataclass(frozen=True)
class NodeCase:
    case_id: str
    dispatch_expectation: str
    result_origin: str

@dataclass(frozen=True)
class HeartbeatCase:
    case_id: str

@dataclass(frozen=True)
class NodePacket:
    packet_id: str
    to_role: str = "worker_a"
    physical_files_written: bool = True
    controller_handoff_contains_body_content: bool = False
    has_controller_reminder: bool = True
    has_mutual_role_reminder: bool = True
    body_hash_valid: bool = True
    body_stale_after_route_mutation: bool = False
    controller_attempts_body_read: bool = False
    controller_attempts_body_execute: bool = False
    delivered_to_role: str = "worker_a"
    cockpit_missing_on_major_node: bool = False
    controller_relay_signature_present: bool = True
    recipient_opens_body_after_relay_check: bool = True
    recipient_open_records_envelope: bool = True
    recipient_open_records_ledger: bool = True
    body_hash_identity_matches_ledger: bool = True
    private_delivery_detected: bool = False
    output_contract_present: bool = True
    output_contract_recipient_matches: bool = True
    result_paths_run_scoped: bool = True

@dataclass(frozen=True)
class ResumeRequest:
    packet_id: str
    has_controller_reminder: bool = True

@dataclass(frozen=True)
class DispatchBlocked:
    packet_id: str
    reason: str

@dataclass(frozen=True)
class ApprovedPacket:
    packet_id: str
    expected_executor_role: str

@dataclass(frozen=True)
class NodeResult:
    packet_id: str
    completed_by_role: str
    completed_by_agent_id: str
    result_body_hash_valid: bool = True
    result_body_stale_after_route_mutation: bool = False
    result_controller_relay_signature_present: bool = True
    result_has_mutual_role_reminder: bool = True
    result_body_opened_after_relay_check: bool = True
    result_body_open_records_envelope: bool = True
    result_body_open_records_ledger: bool = True
    result_ledger_record_present: bool = True
    completed_agent_id_maps_to_role: bool = True

@dataclass(frozen=True)
class CheckedResult:
    packet_id: str
    completed_by_role: str
    completed_by_agent_id: str
    result_body_hash_valid: bool
    result_body_stale_after_route_mutation: bool

@dataclass(frozen=True)
class ReviewPass:
    packet_id: str

@dataclass(frozen=True)
class ReviewBlock:
    packet_id: str
    reason: str

@dataclass(frozen=True)
class PMRepairRequired:
    packet_id: str
    reason: str

@dataclass(frozen=True)
class PMAdvanced:
    packet_id: str

@dataclass(frozen=True)
class State:
    packets: tuple[str, ...] = ()
    heartbeat_loads: tuple[str, ...] = ()
    heartbeat_state_blocks: tuple[str, ...] = ()
    heartbeat_ambiguous_blocks: tuple[str, ...] = ()
    pm_resume_requests: tuple[str, ...] = ()
    resume_packets: tuple[str, ...] = ()
    reminder_checked: tuple[str, ...] = ()
    reminder_blocks: tuple[str, ...] = ()
    controller_envelope_reads: tuple[str, ...] = ()
    physical_packet_files: tuple[str, ...] = ()
    controller_handoff_envelope_only: tuple[str, ...] = ()
    controller_handoff_mutual_role_reminders: tuple[str, ...] = ()
    controller_handoff_body_leak_blocks: tuple[str, ...] = ()
    mutual_role_reminder_blocks: tuple[str, ...] = ()
    controller_body_access_blocks: tuple[str, ...] = ()
    controller_body_execution_blocks: tuple[str, ...] = ()
    controller_return_to_sender: tuple[str, ...] = ()
    controller_relay_signatures: tuple[str, ...] = ()
    recipient_pre_open_checks: tuple[str, ...] = ()
    packet_body_open_events: tuple[str, ...] = ()
    packet_body_open_envelope_records: tuple[str, ...] = ()
    packet_body_open_ledger_records: tuple[str, ...] = ()
    private_delivery_blocks: tuple[str, ...] = ()
    unopened_packet_blocks: tuple[str, ...] = ()
    holder_changes: tuple[str, ...] = ()
    holder_status_updates: tuple[str, ...] = ()
    cockpit_missing_major_nodes: tuple[str, ...] = ()
    chat_mermaid_displays: tuple[str, ...] = ()
    packet_envelope_checks: tuple[str, ...] = ()
    packet_body_hash_checks: tuple[str, ...] = ()
    output_contract_checks: tuple[str, ...] = ()
    result_path_scope_checks: tuple[str, ...] = ()
    wrong_delivery_blocks: tuple[str, ...] = ()
    packet_body_hash_blocks: tuple[str, ...] = ()
    packet_body_hash_identity_blocks: tuple[str, ...] = ()
    stale_packet_body_blocks: tuple[str, ...] = ()
    output_contract_blocks: tuple[str, ...] = ()
    result_path_scope_blocks: tuple[str, ...] = ()
    dispatches: tuple[str, ...] = ()
    worker_results: tuple[str, ...] = ()
    controller_artifacts: tuple[str, ...] = ()
    result_envelopes: tuple[str, ...] = ()
    result_ledger_records: tuple[str, ...] = ()
    result_ledger_blocks: tuple[str, ...] = ()
    result_controller_relay_signatures: tuple[str, ...] = ()
    result_mutual_role_reminders: tuple[str, ...] = ()
    result_mutual_role_reminder_blocks: tuple[str, ...] = ()
    result_body_open_events: tuple[str, ...] = ()
    result_body_open_envelope_records: tuple[str, ...] = ()
    result_body_open_ledger_records: tuple[str, ...] = ()
    unopened_result_blocks: tuple[str, ...] = ()
    result_envelope_checks: tuple[str, ...] = ()
    result_body_hash_checks: tuple[str, ...] = ()
    completed_agent_role_checks: tuple[str, ...] = ()
    completed_agent_id_blocks: tuple[str, ...] = ()
    result_body_hash_blocks: tuple[str, ...] = ()
    stale_result_body_blocks: tuple[str, ...] = ()
    wrong_role_completion_blocks: tuple[str, ...] = ()
    role_origin_audits: tuple[str, ...] = ()
    mail_chain_audits: tuple[str, ...] = ()
    controller_warnings: tuple[str, ...] = ()
    pm_repair_requirements: tuple[str, ...] = ()
    review_passes: tuple[str, ...] = ()
    review_blocks: tuple[str, ...] = ()
    advances: tuple[str, ...] = ()

def _packet_from_id(packet_id: str, *, has_controller_reminder: bool = True) -> NodePacket:
    to_role = "worker_a"
    delivered_to_role = "worker_b" if packet_id.startswith("wrong_delivery") else to_role
    return NodePacket(
        packet_id,
        to_role=to_role,
        physical_files_written=not packet_id.startswith("missing_physical_files"),
        controller_handoff_contains_body_content=packet_id.startswith("controller_handoff_leaks_body"),
        has_controller_reminder=has_controller_reminder,
        has_mutual_role_reminder=not packet_id.startswith("missing_mutual_reminder"),
        body_hash_valid=not packet_id.startswith("body_hash_mismatch"),
        body_stale_after_route_mutation=packet_id.startswith("stale_packet_body"),
        controller_attempts_body_read=packet_id.startswith("controller_reads_body"),
        controller_attempts_body_execute=packet_id.startswith("controller_executes_body"),
        delivered_to_role=delivered_to_role,
        cockpit_missing_on_major_node=packet_id.startswith("cockpit_missing_major"),
        controller_relay_signature_present=not packet_id.startswith("missing_controller_relay"),
        recipient_opens_body_after_relay_check=not packet_id.startswith("unopened_packet"),
        recipient_open_records_envelope=not packet_id.startswith("packet_open_ledger_only"),
        recipient_open_records_ledger=not packet_id.startswith("packet_open_envelope_only"),
        body_hash_identity_matches_ledger=not packet_id.startswith("body_hash_identity_stale"),
        private_delivery_detected=packet_id.startswith("private_delivery"),
        output_contract_present=not packet_id.startswith("missing_output_contract"),
        output_contract_recipient_matches=not packet_id.startswith("contract_recipient_mismatch"),
        result_paths_run_scoped=not packet_id.startswith("result_path_escape"),
    )

__all__ = [
    "NodeCase",
    "HeartbeatCase",
    "NodePacket",
    "ResumeRequest",
    "DispatchBlocked",
    "ApprovedPacket",
    "NodeResult",
    "CheckedResult",
    "ReviewPass",
    "ReviewBlock",
    "PMRepairRequired",
    "PMAdvanced",
    "State",
    "_packet_from_id",
]
