from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from flowguard import FunctionResult, Invariant, InvariantResult, Workflow


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


class PMIssuePacket:
    name = "PMIssuePacket"
    accepted_input_type = (NodeCase, HeartbeatCase)
    reads = ("packets",)
    writes = ("packets",)
    input_description = "node case selected by PM route loop"
    output_description = "PM-authored packet"
    idempotency = "Packet IDs are issued once."

    def apply(self, input_obj: NodeCase, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodeCase):
            yield FunctionResult(input_obj, state, "pm_issue_pass_through")
            return
        new_state = state if input_obj.case_id in state.packets else replace(state, packets=state.packets + (input_obj.case_id,))
        has_reminder = not input_obj.case_id.startswith("missing_reminder")
        yield FunctionResult(_packet_from_id(input_obj.case_id, has_controller_reminder=has_reminder), new_state, "pm_packet_issued")


class HeartbeatResumeLoad:
    name = "HeartbeatResumeLoad"
    accepted_input_type = (HeartbeatCase, NodePacket)
    reads = ("packets", "dispatches", "worker_results")
    writes = (
        "heartbeat_loads",
        "heartbeat_state_blocks",
        "heartbeat_ambiguous_blocks",
        "reminder_checked",
        "physical_packet_files",
        "controller_handoff_envelope_only",
        "dispatches",
        "packet_body_open_events",
        "packet_body_open_envelope_records",
        "packet_body_open_ledger_records",
        "worker_results",
        "result_envelopes",
        "result_ledger_records",
    )
    input_description = "heartbeat wakeup case"
    output_description = "resume request, pending worker result, or blocked recovery"
    idempotency = "Heartbeat state load is keyed by packet ID."

    def apply(self, input_obj: HeartbeatCase, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, HeartbeatCase):
            yield FunctionResult(input_obj, state, "heartbeat_load_pass_through")
            return
        packet_id = input_obj.case_id
        if packet_id.startswith("heartbeat_missing_state"):
            new_state = replace(state, heartbeat_state_blocks=state.heartbeat_state_blocks + (packet_id,))
            yield FunctionResult(DispatchBlocked(packet_id, "missing_current_run_state"), new_state, "heartbeat_missing_state_blocked")
            return
        if packet_id.startswith("heartbeat_ambiguous_worker_state"):
            new_state = replace(state, heartbeat_ambiguous_blocks=state.heartbeat_ambiguous_blocks + (packet_id,))
            yield FunctionResult(
                DispatchBlocked(packet_id, "ambiguous_worker_state_requires_pm_reissue"),
                new_state,
                "heartbeat_ambiguous_worker_blocked",
            )
            return
        if packet_id.startswith("heartbeat_worker_result_pending_review"):
            new_state = replace(
                state,
                heartbeat_loads=state.heartbeat_loads + (packet_id,),
                reminder_checked=state.reminder_checked + (packet_id,),
                physical_packet_files=state.physical_packet_files + (packet_id,),
                controller_handoff_envelope_only=state.controller_handoff_envelope_only + (packet_id,),
                controller_handoff_mutual_role_reminders=state.controller_handoff_mutual_role_reminders + (packet_id,),
                controller_relay_signatures=state.controller_relay_signatures + (packet_id,),
                packet_envelope_checks=state.packet_envelope_checks + (packet_id,),
                packet_body_hash_checks=state.packet_body_hash_checks + (packet_id,),
                output_contract_checks=state.output_contract_checks + (packet_id,),
                result_path_scope_checks=state.result_path_scope_checks + (packet_id,),
                dispatches=state.dispatches + (packet_id,),
                packet_body_open_events=state.packet_body_open_events + (packet_id,),
                packet_body_open_envelope_records=state.packet_body_open_envelope_records + (packet_id,),
                packet_body_open_ledger_records=state.packet_body_open_ledger_records + (packet_id,),
                worker_results=state.worker_results + (packet_id,),
                result_envelopes=state.result_envelopes + (packet_id,),
                result_ledger_records=state.result_ledger_records + (packet_id,),
            )
            yield FunctionResult(NodeResult(packet_id, "worker_a", "agent-worker_a"), new_state, "heartbeat_loaded_worker_result_for_review")
            return

        has_reminder = not packet_id.startswith("heartbeat_missing_reminder")
        new_state = state if packet_id in state.heartbeat_loads else replace(state, heartbeat_loads=state.heartbeat_loads + (packet_id,))
        yield FunctionResult(ResumeRequest(packet_id, has_controller_reminder=has_reminder), new_state, "heartbeat_state_loaded")


class ControllerAskPMOnResume:
    name = "ControllerAskPMOnResume"
    accepted_input_type = (ResumeRequest, NodePacket, NodeResult)
    reads = ("heartbeat_loads",)
    writes = ("pm_resume_requests",)
    input_description = "loaded heartbeat state requiring PM decision"
    output_description = "PM resume decision request"
    idempotency = "PM resume requests are keyed by packet ID."

    def apply(self, input_obj: ResumeRequest, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ResumeRequest):
            yield FunctionResult(input_obj, state, "heartbeat_ask_pm_pass_through")
            return
        new_state = state if input_obj.packet_id in state.pm_resume_requests else replace(
            state,
            pm_resume_requests=state.pm_resume_requests + (input_obj.packet_id,),
        )
        yield FunctionResult(input_obj, new_state, "heartbeat_resume_pm_requested")


class PMResumeDecision:
    name = "PMResumeDecision"
    accepted_input_type = (ResumeRequest, NodePacket, NodeResult)
    reads = ("pm_resume_requests",)
    writes = ("packets", "resume_packets")
    input_description = "PM decision requested by heartbeat resume"
    output_description = "PM-authored resume packet"
    idempotency = "PM resume packets are keyed by packet ID."

    def apply(self, input_obj: ResumeRequest, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ResumeRequest):
            yield FunctionResult(input_obj, state, "heartbeat_pm_decision_pass_through")
            return
        new_packets = state.packets if input_obj.packet_id in state.packets else state.packets + (input_obj.packet_id,)
        new_resume_packets = (
            state.resume_packets if input_obj.packet_id in state.resume_packets else state.resume_packets + (input_obj.packet_id,)
        )
        new_state = replace(state, packets=new_packets, resume_packets=new_resume_packets)
        label = "heartbeat_pm_packet_issued" if input_obj.has_controller_reminder else "heartbeat_pm_missing_controller_reminder"
        yield FunctionResult(
            _packet_from_id(input_obj.packet_id, has_controller_reminder=input_obj.has_controller_reminder),
            new_state,
            label,
        )


class PacketRuntimeWrite:
    name = "PacketRuntimeWrite"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("packets",)
    writes = ("physical_packet_files", "review_blocks")
    input_description = "PM-authored packet envelope/body intent"
    output_description = "physical packet files or blocked missing runtime files"
    idempotency = "Physical packet file writes are keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "packet_runtime_pass_through")
            return
        if not input_obj.physical_files_written:
            new_state = replace(state, review_blocks=state.review_blocks + (input_obj.packet_id,))
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "missing_physical_packet_files"),
                new_state,
                "missing_physical_packet_files_blocked",
            )
            return
        new_state = state if input_obj.packet_id in state.physical_packet_files else replace(
            state,
            physical_packet_files=state.physical_packet_files + (input_obj.packet_id,),
        )
        yield FunctionResult(input_obj, new_state, "packet_physical_files_written")


class ControllerReminderCheck:
    name = "ControllerReminderCheck"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("packets",)
    writes = ("reminder_checked", "reminder_blocks")
    input_description = "PM packet with required controller reminder"
    output_description = "NodePacket or DispatchBlocked"
    idempotency = "Reminder check is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "controller_reminder_pass_through")
            return
        if not input_obj.has_controller_reminder:
            new_state = replace(state, reminder_blocks=state.reminder_blocks + (input_obj.packet_id,))
            yield FunctionResult(DispatchBlocked(input_obj.packet_id, "missing_controller_reminder"), new_state, "controller_missing_pm_reminder")
            return
        new_state = state if input_obj.packet_id in state.reminder_checked else replace(
            state, reminder_checked=state.reminder_checked + (input_obj.packet_id,)
        )
        yield FunctionResult(input_obj, new_state, "controller_reminder_checked")


class ControllerEnvelopeOnlyHandoff:
    name = "ControllerEnvelopeOnlyHandoff"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("reminder_checked",)
    writes = (
        "controller_handoff_envelope_only",
        "controller_handoff_mutual_role_reminders",
        "controller_handoff_body_leak_blocks",
        "mutual_role_reminder_blocks",
    )
    input_description = "controller-visible packet handoff"
    output_description = "NodePacket with envelope-only controller context or blocked body leak"
    idempotency = "Controller handoff isolation is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "controller_handoff_pass_through")
            return
        if input_obj.controller_handoff_contains_body_content:
            new_state = replace(
                state,
                controller_handoff_body_leak_blocks=state.controller_handoff_body_leak_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "controller_handoff_contains_packet_body"),
                new_state,
                "controller_handoff_body_content_blocked",
            )
            return
        if not input_obj.has_mutual_role_reminder:
            new_state = replace(
                state,
                mutual_role_reminder_blocks=state.mutual_role_reminder_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "missing_visible_mutual_role_reminder"),
                new_state,
                "controller_handoff_missing_mutual_role_reminder_blocked",
            )
            return
        new_state = state if input_obj.packet_id in state.controller_handoff_envelope_only else replace(
            state,
            controller_handoff_envelope_only=state.controller_handoff_envelope_only + (input_obj.packet_id,),
            controller_handoff_mutual_role_reminders=state.controller_handoff_mutual_role_reminders + (input_obj.packet_id,),
        )
        yield FunctionResult(input_obj, new_state, "controller_handoff_envelope_only")


class ControllerEnvelopeRelay:
    name = "ControllerEnvelopeRelay"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("reminder_checked",)
    writes = (
        "controller_envelope_reads",
        "controller_handoff_envelope_only",
        "controller_handoff_mutual_role_reminders",
        "controller_handoff_body_leak_blocks",
        "mutual_role_reminder_blocks",
        "controller_body_access_blocks",
        "controller_body_execution_blocks",
        "controller_return_to_sender",
        "controller_relay_signatures",
        "private_delivery_blocks",
        "pm_repair_requirements",
        "holder_changes",
        "holder_status_updates",
        "cockpit_missing_major_nodes",
        "chat_mermaid_displays",
    )
    input_description = "PM packet envelope"
    output_description = "envelope relayed after router direct-dispatch preflight or blocked controller boundary violation"
    idempotency = "Envelope relay is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "controller_envelope_pass_through")
            return
        if input_obj.controller_handoff_contains_body_content:
            new_state = replace(
                state,
                controller_handoff_body_leak_blocks=state.controller_handoff_body_leak_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "controller_handoff_contains_packet_body"),
                new_state,
                "controller_handoff_body_content_blocked",
            )
            return
        if not input_obj.has_mutual_role_reminder:
            new_state = replace(
                state,
                mutual_role_reminder_blocks=state.mutual_role_reminder_blocks + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "missing_visible_mutual_role_reminder"),
                new_state,
                "controller_relay_missing_mutual_role_reminder_blocked",
            )
            return
        if input_obj.controller_attempts_body_read:
            new_state = replace(
                state,
                controller_body_access_blocks=state.controller_body_access_blocks + (input_obj.packet_id,),
                controller_return_to_sender=state.controller_return_to_sender + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "controller_reads_packet_body"),
                new_state,
                "controller_contamination_returned_to_sender",
            )
            return
        if input_obj.controller_attempts_body_execute:
            new_state = replace(
                state,
                controller_body_execution_blocks=state.controller_body_execution_blocks + (input_obj.packet_id,),
                controller_return_to_sender=state.controller_return_to_sender + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "controller_executes_worker_body"),
                new_state,
                "controller_executes_worker_body_returned_to_sender",
            )
            return
        if input_obj.private_delivery_detected:
            new_state = replace(
                state,
                private_delivery_blocks=state.private_delivery_blocks + (input_obj.packet_id,),
                controller_return_to_sender=state.controller_return_to_sender + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "private_role_to_role_delivery_detected"),
                new_state,
                "private_delivery_returned_to_sender",
            )
            return

        envelope_reads = (
            state.controller_envelope_reads
            if input_obj.packet_id in state.controller_envelope_reads
            else state.controller_envelope_reads + (input_obj.packet_id,)
        )
        controller_relay_signatures = state.controller_relay_signatures
        if input_obj.controller_relay_signature_present and input_obj.packet_id not in controller_relay_signatures:
            controller_relay_signatures = controller_relay_signatures + (input_obj.packet_id,)
        envelope_only_handoffs = (
            state.controller_handoff_envelope_only
            if input_obj.packet_id in state.controller_handoff_envelope_only
            else state.controller_handoff_envelope_only + (input_obj.packet_id,)
        )
        mutual_role_reminders = (
            state.controller_handoff_mutual_role_reminders
            if input_obj.packet_id in state.controller_handoff_mutual_role_reminders
            else state.controller_handoff_mutual_role_reminders + (input_obj.packet_id,)
        )
        holder_changes = (
            state.holder_changes if input_obj.packet_id in state.holder_changes else state.holder_changes + (input_obj.packet_id,)
        )
        holder_status_updates = (
            state.holder_status_updates
            if input_obj.packet_id in state.holder_status_updates
            else state.holder_status_updates + (input_obj.packet_id,)
        )
        cockpit_missing = state.cockpit_missing_major_nodes
        chat_mermaid = state.chat_mermaid_displays
        label = "controller_relayed_envelope_with_holder_status_update"
        if input_obj.cockpit_missing_on_major_node:
            cockpit_missing = (
                cockpit_missing if input_obj.packet_id in cockpit_missing else cockpit_missing + (input_obj.packet_id,)
            )
            chat_mermaid = chat_mermaid if input_obj.packet_id in chat_mermaid else chat_mermaid + (input_obj.packet_id,)
            label = "major_node_chat_mermaid_displayed_when_cockpit_missing"

        new_state = replace(
            state,
            controller_envelope_reads=envelope_reads,
            controller_relay_signatures=controller_relay_signatures,
            controller_handoff_envelope_only=envelope_only_handoffs,
            controller_handoff_mutual_role_reminders=mutual_role_reminders,
            holder_changes=holder_changes,
            holder_status_updates=holder_status_updates,
            cockpit_missing_major_nodes=cockpit_missing,
            chat_mermaid_displays=chat_mermaid,
        )
        if input_obj.controller_relay_signature_present and label == "controller_relayed_envelope_with_holder_status_update":
            label = "controller_relay_signature_recorded"
        yield FunctionResult(input_obj, new_state, label)


class RouterDirectDispatch:
    name = "RouterDirectDispatch"
    accepted_input_type = (NodePacket, NodeResult)
    reads = ("packets", "controller_envelope_reads")
    writes = (
        "packet_envelope_checks",
        "packet_body_hash_checks",
        "output_contract_checks",
        "result_path_scope_checks",
        "wrong_delivery_blocks",
        "packet_body_hash_blocks",
        "packet_body_hash_identity_blocks",
        "stale_packet_body_blocks",
        "output_contract_blocks",
        "result_path_scope_blocks",
        "dispatches",
        "review_blocks",
        "pm_repair_requirements",
    )
    input_description = "PM packet envelope"
    output_description = "directly dispatched packet or router preflight block"
    idempotency = "Router direct dispatch is keyed by packet ID."

    def apply(self, input_obj: NodePacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodePacket):
            yield FunctionResult(input_obj, state, "router_direct_dispatch_pass_through")
            return
        packet_envelope_checks = (
            state.packet_envelope_checks
            if input_obj.packet_id in state.packet_envelope_checks
            else state.packet_envelope_checks + (input_obj.packet_id,)
        )
        packet_body_hash_checks = (
            state.packet_body_hash_checks
            if input_obj.packet_id in state.packet_body_hash_checks
            else state.packet_body_hash_checks + (input_obj.packet_id,)
        )
        output_contract_checks = (
            state.output_contract_checks
            if input_obj.packet_id in state.output_contract_checks
            else state.output_contract_checks + (input_obj.packet_id,)
        )
        result_path_scope_checks = (
            state.result_path_scope_checks
            if input_obj.packet_id in state.result_path_scope_checks
            else state.result_path_scope_checks + (input_obj.packet_id,)
        )
        checked_state = replace(
            state,
            packet_envelope_checks=packet_envelope_checks,
            packet_body_hash_checks=packet_body_hash_checks,
            output_contract_checks=output_contract_checks,
            result_path_scope_checks=result_path_scope_checks,
        )
        if input_obj.packet_id not in state.controller_relay_signatures:
            new_state = replace(
                checked_state,
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "missing_controller_relay_signature"),
                new_state,
                "missing_controller_relay_signature_blocked",
            )
            return
        if input_obj.delivered_to_role != input_obj.to_role:
            new_state = replace(
                checked_state,
                wrong_delivery_blocks=checked_state.wrong_delivery_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "packet_delivered_to_wrong_role"),
                new_state,
                "packet_delivered_to_wrong_role_blocked",
            )
            return
        if not input_obj.body_hash_valid:
            new_state = replace(
                checked_state,
                packet_body_hash_blocks=checked_state.packet_body_hash_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "body_hash_mismatch"),
                new_state,
                "body_hash_mismatch_blocked",
            )
            return
        if not input_obj.body_hash_identity_matches_ledger:
            new_state = replace(
                checked_state,
                packet_body_hash_identity_blocks=checked_state.packet_body_hash_identity_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "packet_body_envelope_ledger_hash_identity_mismatch"),
                new_state,
                "packet_body_hash_identity_mismatch_blocked",
            )
            return
        if input_obj.body_stale_after_route_mutation:
            new_state = replace(
                checked_state,
                stale_packet_body_blocks=checked_state.stale_packet_body_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "stale_packet_body_reused_after_route_mutation"),
                new_state,
                "stale_packet_body_reused_after_route_mutation_blocked",
            )
            return
        if not input_obj.output_contract_present:
            new_state = replace(
                checked_state,
                output_contract_blocks=checked_state.output_contract_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "missing_output_contract"),
                new_state,
                "missing_output_contract_blocked",
            )
            return
        if not input_obj.output_contract_recipient_matches:
            new_state = replace(
                checked_state,
                output_contract_blocks=checked_state.output_contract_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "output_contract_recipient_mismatch"),
                new_state,
                "output_contract_recipient_mismatch_blocked",
            )
            return
        if not input_obj.result_paths_run_scoped:
            new_state = replace(
                checked_state,
                result_path_scope_blocks=checked_state.result_path_scope_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "result_path_escape"),
                new_state,
                "result_path_escape_blocked",
            )
            return
        new_state = (
            checked_state
            if input_obj.packet_id in checked_state.dispatches
            else replace(checked_state, dispatches=checked_state.dispatches + (input_obj.packet_id,))
        )
        yield FunctionResult(ApprovedPacket(input_obj.packet_id, input_obj.to_role), new_state, "router_direct_dispatch_approved")


class WorkerOrControllerResult:
    name = "WorkerOrControllerResult"
    accepted_input_type = (ApprovedPacket, NodeResult)
    reads = ("dispatches",)
    writes = (
        "recipient_pre_open_checks",
        "packet_body_open_events",
        "packet_body_open_envelope_records",
        "packet_body_open_ledger_records",
        "unopened_packet_blocks",
        "worker_results",
        "controller_artifacts",
        "result_envelopes",
        "result_ledger_records",
        "review_blocks",
        "pm_repair_requirements",
    )
    input_description = "directly dispatched packet"
    output_description = "node result with origin"
    idempotency = "Node result is keyed by packet ID."

    def apply(self, input_obj: ApprovedPacket, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ApprovedPacket):
            yield FunctionResult(input_obj, state, "worker_result_pass_through")
            return
        recipient_pre_open_checks = (
            state.recipient_pre_open_checks
            if input_obj.packet_id in state.recipient_pre_open_checks
            else state.recipient_pre_open_checks + (input_obj.packet_id,)
        )
        if input_obj.packet_id.startswith("unopened_packet"):
            new_state = replace(
                state,
                recipient_pre_open_checks=recipient_pre_open_checks,
                unopened_packet_blocks=state.unopened_packet_blocks + (input_obj.packet_id,),
                review_blocks=state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "packet_body_unopened_after_controller_relay"),
                new_state,
                "unopened_letter_sent_to_pm_for_restart_or_repair",
            )
            return
        packet_body_open_events = (
            state.packet_body_open_events
            if input_obj.packet_id in state.packet_body_open_events
            else state.packet_body_open_events + (input_obj.packet_id,)
        )
        packet_body_open_envelope_records = state.packet_body_open_envelope_records
        if not input_obj.packet_id.startswith("packet_open_ledger_only") and input_obj.packet_id not in packet_body_open_envelope_records:
            packet_body_open_envelope_records = packet_body_open_envelope_records + (input_obj.packet_id,)
        packet_body_open_ledger_records = state.packet_body_open_ledger_records
        if not input_obj.packet_id.startswith("packet_open_envelope_only") and input_obj.packet_id not in packet_body_open_ledger_records:
            packet_body_open_ledger_records = packet_body_open_ledger_records + (input_obj.packet_id,)
        checked_state = replace(
            state,
            recipient_pre_open_checks=recipient_pre_open_checks,
            packet_body_open_events=packet_body_open_events,
            packet_body_open_envelope_records=packet_body_open_envelope_records,
            packet_body_open_ledger_records=packet_body_open_ledger_records,
        )
        if input_obj.packet_id.startswith("packet_open_ledger_only"):
            new_state = replace(
                checked_state,
                unopened_packet_blocks=checked_state.unopened_packet_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "packet_body_open_envelope_receipt_missing"),
                new_state,
                "packet_body_open_envelope_receipt_missing_blocked",
            )
            return
        if input_obj.packet_id.startswith("packet_open_envelope_only"):
            new_state = replace(
                checked_state,
                unopened_packet_blocks=checked_state.unopened_packet_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                DispatchBlocked(input_obj.packet_id, "packet_body_open_ledger_receipt_missing"),
                new_state,
                "packet_body_open_ledger_receipt_missing_blocked",
            )
            return
        if input_obj.packet_id.startswith("controller_origin"):
            new_state = replace(
                checked_state,
                controller_artifacts=checked_state.controller_artifacts + (input_obj.packet_id,),
                result_envelopes=checked_state.result_envelopes + (input_obj.packet_id,),
                result_ledger_records=checked_state.result_ledger_records + (input_obj.packet_id,),
            )
            yield FunctionResult(
                NodeResult(input_obj.packet_id, "controller", "agent-controller"),
                new_state,
                "controller_origin_result_envelope",
            )
            return
        completed_by_role = "worker_b" if input_obj.packet_id.startswith("result_wrong_role") else input_obj.expected_executor_role
        completed_by_agent_id = completed_by_role if input_obj.packet_id.startswith("agent_id_role_string") else f"agent-{completed_by_role}"
        result_body_hash_valid = not input_obj.packet_id.startswith("result_body_hash_mismatch")
        result_body_stale = input_obj.packet_id.startswith("stale_result_body")
        result_controller_relay_signature_present = not input_obj.packet_id.startswith("missing_result_controller_relay")
        result_has_mutual_role_reminder = not input_obj.packet_id.startswith("missing_result_mutual_reminder")
        result_body_opened_after_relay_check = not input_obj.packet_id.startswith("unopened_result")
        result_ledger_present = not input_obj.packet_id.startswith("result_without_ledger")
        result_body_open_records_envelope = not input_obj.packet_id.startswith("result_open_ledger_only")
        result_body_open_records_ledger = not input_obj.packet_id.startswith("result_open_envelope_only")
        completed_agent_id_maps_to_role = not (
            input_obj.packet_id.startswith("agent_id_role_string")
            or input_obj.packet_id.startswith("invalid_agent_id")
        )
        result_ledger_records = checked_state.result_ledger_records
        if result_ledger_present and input_obj.packet_id not in result_ledger_records:
            result_ledger_records = result_ledger_records + (input_obj.packet_id,)
        new_state = replace(
            checked_state,
            worker_results=checked_state.worker_results + (input_obj.packet_id,),
            result_envelopes=checked_state.result_envelopes + (input_obj.packet_id,),
            result_ledger_records=result_ledger_records,
        )
        yield FunctionResult(
            NodeResult(
                input_obj.packet_id,
                completed_by_role,
                completed_by_agent_id,
                result_body_hash_valid=result_body_hash_valid,
                result_body_stale_after_route_mutation=result_body_stale,
                result_controller_relay_signature_present=result_controller_relay_signature_present,
                result_has_mutual_role_reminder=result_has_mutual_role_reminder,
                result_body_opened_after_relay_check=result_body_opened_after_relay_check,
                result_body_open_records_envelope=result_body_open_records_envelope,
                result_body_open_records_ledger=result_body_open_records_ledger,
                result_ledger_record_present=result_ledger_present,
                completed_agent_id_maps_to_role=completed_agent_id_maps_to_role,
            ),
            new_state,
            "worker_result_envelope",
        )


class ControllerResultRelay:
    name = "ControllerResultRelay"
    accepted_input_type = NodeResult
    reads = ("result_envelopes", "result_ledger_records")
    writes = (
        "result_controller_relay_signatures",
        "result_mutual_role_reminders",
        "result_mutual_role_reminder_blocks",
        "result_ledger_blocks",
        "review_blocks",
        "pm_repair_requirements",
        "holder_changes",
        "holder_status_updates",
    )
    input_description = "worker/reviewer/officer result envelope"
    output_description = "result envelope relayed by controller or left unsigned for reviewer block"
    idempotency = "Result relay signatures are keyed by packet ID."

    def apply(self, input_obj: NodeResult, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodeResult):
            yield FunctionResult(input_obj, state, "controller_result_relay_pass_through")
            return
        if input_obj.packet_id not in state.result_ledger_records:
            new_state = replace(
                state,
                result_ledger_blocks=state.result_ledger_blocks + (input_obj.packet_id,),
                review_blocks=state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_ledger_absorption_missing"),
                new_state,
                "result_without_ledger_absorption_blocked_before_reviewer_relay",
            )
            return
        if not input_obj.result_controller_relay_signature_present:
            yield FunctionResult(input_obj, state, "result_controller_relay_signature_missing")
            return
        if not input_obj.result_has_mutual_role_reminder:
            new_state = replace(
                state,
                result_mutual_role_reminder_blocks=state.result_mutual_role_reminder_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(input_obj, new_state, "result_mutual_role_reminder_missing")
            return
        relay_signatures = (
            state.result_controller_relay_signatures
            if input_obj.packet_id in state.result_controller_relay_signatures
            else state.result_controller_relay_signatures + (input_obj.packet_id,)
        )
        holder_changes = (
            state.holder_changes if input_obj.packet_id in state.holder_changes else state.holder_changes + (input_obj.packet_id,)
        )
        holder_status_updates = (
            state.holder_status_updates
            if input_obj.packet_id in state.holder_status_updates
            else state.holder_status_updates + (input_obj.packet_id,)
        )
        result_mutual_role_reminders = (
            state.result_mutual_role_reminders
            if input_obj.packet_id in state.result_mutual_role_reminders
            else state.result_mutual_role_reminders + (input_obj.packet_id,)
        )
        new_state = replace(
            state,
            result_controller_relay_signatures=relay_signatures,
            result_mutual_role_reminders=result_mutual_role_reminders,
            holder_changes=holder_changes,
            holder_status_updates=holder_status_updates,
        )
        yield FunctionResult(input_obj, new_state, "controller_relayed_result_envelope_with_holder_status_update")


class ReviewerResultEnvelopeCheck:
    name = "ReviewerResultEnvelopeCheck"
    accepted_input_type = (NodeResult, ReviewBlock)
    reads = ("result_envelopes", "result_ledger_records")
    writes = (
        "result_envelope_checks",
        "result_body_hash_checks",
        "result_body_open_events",
        "result_body_open_envelope_records",
        "result_body_open_ledger_records",
        "unopened_result_blocks",
        "completed_agent_role_checks",
        "completed_agent_id_blocks",
        "result_body_hash_blocks",
        "stale_result_body_blocks",
        "result_ledger_blocks",
        "review_blocks",
        "pm_repair_requirements",
    )
    input_description = "result envelope"
    output_description = "checked result or review block"
    idempotency = "Result envelope check is keyed by packet ID."

    def apply(self, input_obj: NodeResult, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, NodeResult):
            yield FunctionResult(input_obj, state, "result_envelope_check_pass_through")
            return
        envelope_checks = (
            state.result_envelope_checks
            if input_obj.packet_id in state.result_envelope_checks
            else state.result_envelope_checks + (input_obj.packet_id,)
        )
        body_hash_checks = (
            state.result_body_hash_checks
            if input_obj.packet_id in state.result_body_hash_checks
            else state.result_body_hash_checks + (input_obj.packet_id,)
        )
        agent_checks = (
            state.completed_agent_role_checks
            if input_obj.packet_id in state.completed_agent_role_checks
            else state.completed_agent_role_checks + (input_obj.packet_id,)
        )
        checked_state = replace(
            state,
            result_envelope_checks=envelope_checks,
            result_body_hash_checks=body_hash_checks,
            completed_agent_role_checks=agent_checks,
        )
        if input_obj.packet_id not in state.result_controller_relay_signatures:
            new_state = replace(
                checked_state,
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "missing_result_controller_relay_signature"),
                new_state,
                "missing_result_controller_relay_signature_blocked",
            )
            return
        if input_obj.packet_id not in state.result_ledger_records:
            new_state = replace(
                checked_state,
                result_ledger_blocks=checked_state.result_ledger_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_ledger_absorption_missing"),
                new_state,
                "result_ledger_absorption_missing_blocked",
            )
            return
        if not input_obj.result_body_opened_after_relay_check:
            new_state = replace(
                checked_state,
                unopened_result_blocks=checked_state.unopened_result_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_body_unopened_after_controller_relay"),
                new_state,
                "unopened_result_letter_sent_to_pm_for_restart_or_repair",
            )
            return
        result_body_open_events = (
            checked_state.result_body_open_events
            if input_obj.packet_id in checked_state.result_body_open_events
            else checked_state.result_body_open_events + (input_obj.packet_id,)
        )
        result_body_open_envelope_records = checked_state.result_body_open_envelope_records
        if input_obj.result_body_open_records_envelope and input_obj.packet_id not in result_body_open_envelope_records:
            result_body_open_envelope_records = result_body_open_envelope_records + (input_obj.packet_id,)
        result_body_open_ledger_records = checked_state.result_body_open_ledger_records
        if input_obj.result_body_open_records_ledger and input_obj.packet_id not in result_body_open_ledger_records:
            result_body_open_ledger_records = result_body_open_ledger_records + (input_obj.packet_id,)
        checked_state = replace(
            checked_state,
            result_body_open_events=result_body_open_events,
            result_body_open_envelope_records=result_body_open_envelope_records,
            result_body_open_ledger_records=result_body_open_ledger_records,
        )
        if not input_obj.result_body_open_records_envelope:
            new_state = replace(
                checked_state,
                unopened_result_blocks=checked_state.unopened_result_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_body_open_envelope_receipt_missing"),
                new_state,
                "result_body_open_envelope_receipt_missing_blocked",
            )
            return
        if not input_obj.result_body_open_records_ledger:
            new_state = replace(
                checked_state,
                unopened_result_blocks=checked_state.unopened_result_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_body_open_ledger_receipt_missing"),
                new_state,
                "result_body_open_ledger_receipt_missing_blocked",
            )
            return
        if not input_obj.completed_agent_id_maps_to_role:
            new_state = replace(
                checked_state,
                completed_agent_id_blocks=checked_state.completed_agent_id_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
                pm_repair_requirements=checked_state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "completed_agent_id_not_assigned_to_role"),
                new_state,
                "completed_agent_id_role_mapping_blocked",
            )
            return
        if not input_obj.result_body_hash_valid:
            new_state = replace(
                checked_state,
                result_body_hash_blocks=checked_state.result_body_hash_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "result_body_hash_mismatch"),
                new_state,
                "result_body_hash_mismatch_blocked",
            )
            return
        if input_obj.result_body_stale_after_route_mutation:
            new_state = replace(
                checked_state,
                stale_result_body_blocks=checked_state.stale_result_body_blocks + (input_obj.packet_id,),
                review_blocks=checked_state.review_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "stale_result_body_reused_after_route_mutation"),
                new_state,
                "stale_result_body_reused_after_route_mutation_blocked",
            )
            return
        yield FunctionResult(
            CheckedResult(
                input_obj.packet_id,
                input_obj.completed_by_role,
                input_obj.completed_by_agent_id,
                input_obj.result_body_hash_valid,
                input_obj.result_body_stale_after_route_mutation,
            ),
            checked_state,
            "result_envelope_checked",
        )


class ReviewerResult:
    name = "ReviewerResult"
    accepted_input_type = (CheckedResult, ReviewBlock)
    reads = ("worker_results", "controller_artifacts", "result_envelope_checks", "completed_agent_role_checks")
    writes = (
        "role_origin_audits",
        "mail_chain_audits",
        "controller_warnings",
        "pm_repair_requirements",
        "wrong_role_completion_blocks",
        "review_passes",
        "review_blocks",
    )
    input_description = "node result"
    output_description = "ReviewPass or ReviewBlock"
    idempotency = "Review result is keyed by packet ID."

    def apply(self, input_obj: CheckedResult | ReviewBlock, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, CheckedResult):
            yield FunctionResult(input_obj, state, "review_result_pass_through")
            return
        audited_state = state if input_obj.packet_id in state.role_origin_audits else replace(
            state,
            role_origin_audits=state.role_origin_audits + (input_obj.packet_id,),
        )
        audited_state = audited_state if input_obj.packet_id in audited_state.mail_chain_audits else replace(
            audited_state,
            mail_chain_audits=audited_state.mail_chain_audits + (input_obj.packet_id,),
        )
        if input_obj.completed_by_role != "worker_a":
            label = "controller_origin_artifact_blocked" if input_obj.completed_by_role == "controller" else "result_completed_by_wrong_role_blocked"
            new_state = replace(
                audited_state,
                review_blocks=audited_state.review_blocks + (input_obj.packet_id,),
                controller_warnings=audited_state.controller_warnings + (input_obj.packet_id,),
                pm_repair_requirements=audited_state.pm_repair_requirements + (input_obj.packet_id,),
                wrong_role_completion_blocks=audited_state.wrong_role_completion_blocks + (input_obj.packet_id,),
            )
            yield FunctionResult(
                ReviewBlock(input_obj.packet_id, "block_invalid_role_origin"),
                new_state,
                label,
            )
            return
        new_state = replace(audited_state, review_passes=audited_state.review_passes + (input_obj.packet_id,))
        yield FunctionResult(ReviewPass(input_obj.packet_id), new_state, "review_pass_after_role_origin_audit")


class PMRepairAfterInvalidOrigin:
    name = "PMRepairAfterInvalidOrigin"
    accepted_input_type = (ReviewBlock, ReviewPass)
    reads = ("review_blocks", "pm_repair_requirements")
    writes = ("pm_repair_requirements",)
    input_description = "review block caused by invalid role origin"
    output_description = "PM repair/reissue requirement"
    idempotency = "Repair requirement is keyed by packet ID."

    def apply(self, input_obj: ReviewBlock, state: State) -> Iterable[FunctionResult]:
        if not isinstance(input_obj, ReviewBlock):
            yield FunctionResult(input_obj, state, "pm_repair_pass_through")
            return
        if input_obj.reason != "block_invalid_role_origin":
            new_state = state if input_obj.packet_id in state.pm_repair_requirements else replace(
                state,
                pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
            )
            yield FunctionResult(
                PMRepairRequired(input_obj.packet_id, input_obj.reason),
                new_state,
                "pm_repair_required_after_body_integrity_block",
            )
            return
        new_state = state if input_obj.packet_id in state.pm_repair_requirements else replace(
            state,
            pm_repair_requirements=state.pm_repair_requirements + (input_obj.packet_id,),
        )
        yield FunctionResult(
            PMRepairRequired(input_obj.packet_id, input_obj.reason),
            new_state,
            "pm_repair_required_after_invalid_role_origin",
        )


class PMAdvance:
    name = "PMAdvance"
    accepted_input_type = ReviewPass
    reads = ("review_passes",)
    writes = ("advances",)
    input_description = "review pass"
    output_description = "PMAdvanced"
    idempotency = "Advance is keyed by packet ID."

    def apply(self, input_obj: ReviewPass, state: State) -> Iterable[FunctionResult]:
        new_state = state if input_obj.packet_id in state.advances else replace(state, advances=state.advances + (input_obj.packet_id,))
        yield FunctionResult(PMAdvanced(input_obj.packet_id), new_state, "pm_advanced")


def no_advance_from_controller_artifact(state: State, trace) -> InvariantResult:
    del trace
    bad = set(state.controller_artifacts) & set(state.advances)
    if bad:
        return InvariantResult.fail(f"controller-origin evidence advanced: {sorted(bad)!r}")
    return InvariantResult.pass_()


def advance_requires_review_pass(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.advances) - set(state.review_passes)
    if missing:
        return InvariantResult.fail(f"advance without review pass: {sorted(missing)!r}")
    return InvariantResult.pass_()


def review_pass_requires_role_origin_audit(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.review_passes) - set(state.role_origin_audits)
    if missing:
        return InvariantResult.fail(f"review pass without role-origin audit: {sorted(missing)!r}")
    return InvariantResult.pass_()


def review_pass_requires_mail_chain_audit(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.review_passes) - set(state.mail_chain_audits)
    if missing:
        return InvariantResult.fail(f"review pass without packet mail-chain audit: {sorted(missing)!r}")
    return InvariantResult.pass_()


def recipient_body_open_requires_controller_relay_signature(state: State, trace) -> InvariantResult:
    del trace
    packet_missing = set(state.packet_body_open_events) - set(state.controller_relay_signatures)
    if packet_missing:
        return InvariantResult.fail(f"packet body opened without controller relay signature: {sorted(packet_missing)!r}")
    result_missing = set(state.result_body_open_events) - set(state.result_controller_relay_signatures)
    if result_missing:
        return InvariantResult.fail(f"result body opened without controller relay signature: {sorted(result_missing)!r}")
    return InvariantResult.pass_()


def missing_or_unopened_mail_requires_pm_restart_or_repair(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.unopened_packet_blocks) | set(state.unopened_result_blocks) | set(state.private_delivery_blocks)
    missing = blocked - set(state.pm_repair_requirements)
    if missing:
        return InvariantResult.fail(f"mail-chain blocker lacked PM restart/repair requirement: {sorted(missing)!r}")
    return InvariantResult.pass_()


def invalid_origin_block_requires_warning(state: State, trace) -> InvariantResult:
    del trace
    invalid = (set(state.review_blocks) & set(state.controller_artifacts)) | set(state.wrong_role_completion_blocks)
    missing_warning = invalid - set(state.controller_warnings)
    if missing_warning:
        return InvariantResult.fail(
            f"invalid role-origin block without controller warning: {sorted(missing_warning)!r}"
        )
    missing_repair = invalid - set(state.pm_repair_requirements)
    if missing_repair:
        return InvariantResult.fail(
            f"invalid role-origin block without PM repair requirement: {sorted(missing_repair)!r}"
        )
    return InvariantResult.pass_()


def controller_body_boundary_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.controller_body_access_blocks) | set(state.controller_body_execution_blocks)
    unsafe = blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if unsafe:
        return InvariantResult.fail(f"controller body boundary violation advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def controller_handoff_body_leak_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.controller_handoff_body_leak_blocks)
    unsafe = blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if unsafe:
        return InvariantResult.fail(f"controller handoff body leak advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def missing_mutual_role_reminder_never_advances(state: State, trace) -> InvariantResult:
    del trace
    packet_blocked = set(state.mutual_role_reminder_blocks)
    packet_unsafe = packet_blocked & (
        set(state.dispatches)
        | set(state.worker_results)
        | set(state.result_envelope_checks)
        | set(state.review_passes)
        | set(state.advances)
    )
    if packet_unsafe:
        return InvariantResult.fail(f"missing packet mutual-role reminder advanced: {sorted(packet_unsafe)!r}")

    result_blocked = set(state.result_mutual_role_reminder_blocks)
    result_unsafe = result_blocked & (
        set(state.result_body_open_events)
        | set(state.review_passes)
        | set(state.advances)
    )
    if result_unsafe:
        return InvariantResult.fail(f"missing result mutual-role reminder advanced: {sorted(result_unsafe)!r}")
    return InvariantResult.pass_()


def controller_relay_requires_physical_files_and_envelope_only_handoff(state: State, trace) -> InvariantResult:
    del trace
    relayed = set(state.controller_envelope_reads)
    missing_files = relayed - set(state.physical_packet_files)
    if missing_files:
        return InvariantResult.fail(f"controller relayed without physical packet files: {sorted(missing_files)!r}")
    missing_handoff = relayed - set(state.controller_handoff_envelope_only)
    if missing_handoff:
        return InvariantResult.fail(f"controller relayed without envelope-only handoff: {sorted(missing_handoff)!r}")
    missing_mutual_reminder = relayed - set(state.controller_handoff_mutual_role_reminders)
    if missing_mutual_reminder:
        return InvariantResult.fail(
            f"controller relayed without visible mutual-role reminder: {sorted(missing_mutual_reminder)!r}"
        )
    result_relayed = set(state.result_controller_relay_signatures)
    missing_result_mutual_reminder = result_relayed - set(state.result_mutual_role_reminders)
    if missing_result_mutual_reminder:
        return InvariantResult.fail(
            f"controller relayed result without visible mutual-role reminder: {sorted(missing_result_mutual_reminder)!r}"
        )
    return InvariantResult.pass_()


def holder_change_requires_user_status_update(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.holder_changes) - set(state.holder_status_updates)
    if missing:
        return InvariantResult.fail(f"holder changed without user status update: {sorted(missing)!r}")
    return InvariantResult.pass_()


def cockpit_missing_major_node_requires_chat_mermaid(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.cockpit_missing_major_nodes) - set(state.chat_mermaid_displays)
    if missing:
        return InvariantResult.fail(f"major node entered without chat Mermaid when Cockpit missing: {sorted(missing)!r}")
    return InvariantResult.pass_()


def dispatch_requires_packet_envelope_and_hash_checks(state: State, trace) -> InvariantResult:
    del trace
    missing_envelope = set(state.dispatches) - set(state.packet_envelope_checks)
    if missing_envelope:
        return InvariantResult.fail(f"dispatch without packet envelope check: {sorted(missing_envelope)!r}")
    missing_hash = set(state.dispatches) - set(state.packet_body_hash_checks)
    if missing_hash:
        return InvariantResult.fail(f"dispatch without packet body hash check: {sorted(missing_hash)!r}")
    return InvariantResult.pass_()


def dispatch_requires_output_contract_and_run_scoped_result_paths(state: State, trace) -> InvariantResult:
    del trace
    missing_contract = set(state.dispatches) - set(state.output_contract_checks)
    if missing_contract:
        return InvariantResult.fail(f"dispatch without output contract check: {sorted(missing_contract)!r}")
    missing_result_path_scope = set(state.dispatches) - set(state.result_path_scope_checks)
    if missing_result_path_scope:
        return InvariantResult.fail(f"dispatch without run-scoped result path check: {sorted(missing_result_path_scope)!r}")
    return InvariantResult.pass_()


def packet_integrity_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    missing_files = set(state.packets) - set(state.physical_packet_files)
    blocked = (
        set(state.wrong_delivery_blocks)
        | set(state.packet_body_hash_blocks)
        | set(state.packet_body_hash_identity_blocks)
        | set(state.stale_packet_body_blocks)
        | set(state.output_contract_blocks)
        | set(state.result_path_scope_blocks)
        | missing_files
    )
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"invalid packet envelope/body advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def review_pass_requires_result_envelope_body_and_agent_checks(state: State, trace) -> InvariantResult:
    del trace
    passed = set(state.review_passes)
    missing_envelope = passed - set(state.result_envelope_checks)
    if missing_envelope:
        return InvariantResult.fail(f"review pass without result envelope check: {sorted(missing_envelope)!r}")
    missing_hash = passed - set(state.result_body_hash_checks)
    if missing_hash:
        return InvariantResult.fail(f"review pass without result body hash check: {sorted(missing_hash)!r}")
    missing_agent = passed - set(state.completed_agent_role_checks)
    if missing_agent:
        return InvariantResult.fail(f"review pass without completed agent role check: {sorted(missing_agent)!r}")
    missing_packet_open_envelope = passed - set(state.packet_body_open_envelope_records)
    if missing_packet_open_envelope:
        return InvariantResult.fail(
            f"review pass without packet body-open envelope receipt: {sorted(missing_packet_open_envelope)!r}"
        )
    missing_packet_open_ledger = passed - set(state.packet_body_open_ledger_records)
    if missing_packet_open_ledger:
        return InvariantResult.fail(f"review pass without packet body-open ledger receipt: {sorted(missing_packet_open_ledger)!r}")
    missing_result_ledger = passed - set(state.result_ledger_records)
    if missing_result_ledger:
        return InvariantResult.fail(f"review pass without result ledger absorption: {sorted(missing_result_ledger)!r}")
    missing_result_open_envelope = passed - set(state.result_body_open_envelope_records)
    if missing_result_open_envelope:
        return InvariantResult.fail(
            f"review pass without result body-open envelope receipt: {sorted(missing_result_open_envelope)!r}"
        )
    missing_result_open_ledger = passed - set(state.result_body_open_ledger_records)
    if missing_result_open_ledger:
        return InvariantResult.fail(f"review pass without result body-open ledger receipt: {sorted(missing_result_open_ledger)!r}")
    blocked_agent_ids = passed & set(state.completed_agent_id_blocks)
    if blocked_agent_ids:
        return InvariantResult.fail(f"review pass with invalid completed agent id mapping: {sorted(blocked_agent_ids)!r}")
    return InvariantResult.pass_()


def result_body_integrity_blocks_never_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.result_body_hash_blocks) | set(state.stale_result_body_blocks) | set(state.result_ledger_blocks)
    unsafe = blocked & (set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"invalid result body advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def result_relay_requires_packet_open_and_result_ledger(state: State, trace) -> InvariantResult:
    del trace
    relayed = set(state.result_controller_relay_signatures)
    missing_packet_open_envelope = relayed - set(state.packet_body_open_envelope_records)
    if missing_packet_open_envelope:
        return InvariantResult.fail(
            f"result relayed without packet body-open envelope receipt: {sorted(missing_packet_open_envelope)!r}"
        )
    missing_packet_open_ledger = relayed - set(state.packet_body_open_ledger_records)
    if missing_packet_open_ledger:
        return InvariantResult.fail(f"result relayed without packet body-open ledger receipt: {sorted(missing_packet_open_ledger)!r}")
    missing_result_ledger = relayed - set(state.result_ledger_records)
    if missing_result_ledger:
        return InvariantResult.fail(f"result relayed without result ledger absorption: {sorted(missing_result_ledger)!r}")
    return InvariantResult.pass_()


def wrong_role_completion_never_advances(state: State, trace) -> InvariantResult:
    del trace
    unsafe = set(state.wrong_role_completion_blocks) & set(state.advances)
    if unsafe:
        return InvariantResult.fail(f"wrong-role completion advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def result_requires_dispatch(state: State, trace) -> InvariantResult:
    del trace
    result_ids = set(state.worker_results) | set(state.controller_artifacts)
    missing = result_ids - set(state.dispatches)
    if missing:
        return InvariantResult.fail(f"result without router direct dispatch: {sorted(missing)!r}")
    return InvariantResult.pass_()


def dispatch_requires_controller_reminder(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.dispatches) - set(state.reminder_checked)
    if missing:
        return InvariantResult.fail(f"dispatch without controller reminder check: {sorted(missing)!r}")
    return InvariantResult.pass_()


def packet_open_blocks_never_produce_result_or_advance(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.unopened_packet_blocks)
    unsafe = blocked & (set(state.worker_results) | set(state.controller_artifacts) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"packet open blocker produced result or advanced: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def heartbeat_resume_packet_requires_pm_request(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.pm_resume_requests)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without PM request: {sorted(missing)!r}")
    return InvariantResult.pass_()


def heartbeat_resume_packet_requires_loaded_state(state: State, trace) -> InvariantResult:
    del trace
    missing = set(state.resume_packets) - set(state.heartbeat_loads)
    if missing:
        return InvariantResult.fail(f"heartbeat resume packet without loaded state: {sorted(missing)!r}")
    return InvariantResult.pass_()


def ambiguous_worker_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_ambiguous_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"ambiguous worker state advanced or dispatched: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


def missing_heartbeat_state_never_advances(state: State, trace) -> InvariantResult:
    del trace
    blocked = set(state.heartbeat_state_blocks)
    unsafe = blocked & (set(state.dispatches) | set(state.worker_results) | set(state.review_passes) | set(state.advances))
    if unsafe:
        return InvariantResult.fail(f"missing heartbeat state advanced or dispatched: {sorted(unsafe)!r}")
    return InvariantResult.pass_()


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
        "recipient_body_open_requires_controller_relay_signature",
        "Recipients may open packet/result bodies only after validating a controller relay signature.",
        recipient_body_open_requires_controller_relay_signature,
    ),
    Invariant(
        "missing_or_unopened_mail_requires_pm_restart_or_repair",
        "Unopened, private, or missing-relay mail is sent to PM for restart, repair node, or sender reissue.",
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
        "controller_relay_requires_physical_files_and_envelope_only_handoff",
        "Controller relay requires physical packet files, envelope-only handoff, and visible mutual role reminders.",
        controller_relay_requires_physical_files_and_envelope_only_handoff,
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
        "Reviewer pass requires result envelope, result body hash, and completed-agent role checks.",
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
        "heartbeat_resume_packet_requires_pm_request",
        "Heartbeat cannot mint a resume packet without first asking PM.",
        heartbeat_resume_packet_requires_pm_request,
    ),
    Invariant(
        "heartbeat_resume_packet_requires_loaded_state",
        "Heartbeat resume packets require loaded current-run state.",
        heartbeat_resume_packet_requires_loaded_state,
    ),
    Invariant(
        "ambiguous_worker_state_never_advances",
        "Ambiguous worker state blocks controller execution.",
        ambiguous_worker_state_never_advances,
    ),
    Invariant(
        "missing_heartbeat_state_never_advances",
        "Missing current-run state blocks heartbeat execution.",
        missing_heartbeat_state_never_advances,
    ),
)


EXTERNAL_INPUTS = (
    NodeCase("valid_worker_packet", "pass", "worker"),
    NodeCase("cockpit_missing_major_packet", "pass", "worker"),
    NodeCase("missing_physical_files_packet", "block", "worker"),
    NodeCase("controller_handoff_leaks_body_packet", "block", "controller"),
    NodeCase("missing_mutual_reminder_packet", "block", "controller"),
    NodeCase("controller_reads_body_packet", "block", "controller"),
    NodeCase("controller_executes_body_packet", "block", "controller"),
    NodeCase("missing_controller_relay_packet", "block", "worker"),
    NodeCase("private_delivery_packet", "block", "worker"),
    NodeCase("unopened_packet", "block", "worker"),
    NodeCase("packet_open_envelope_only_packet", "block", "worker"),
    NodeCase("packet_open_ledger_only_packet", "block", "worker"),
    NodeCase("wrong_delivery_packet", "block", "worker"),
    NodeCase("body_hash_mismatch_packet", "block", "worker"),
    NodeCase("body_hash_identity_stale_packet", "block", "worker"),
    NodeCase("stale_packet_body_packet", "block", "worker"),
    NodeCase("missing_output_contract_packet", "block", "worker"),
    NodeCase("contract_recipient_mismatch_packet", "block", "worker"),
    NodeCase("result_path_escape_packet", "block", "worker"),
    NodeCase("controller_origin_packet", "pass", "controller"),
    NodeCase("result_wrong_role_packet", "block", "worker_b"),
    NodeCase("agent_id_role_string_packet", "block", "worker"),
    NodeCase("invalid_agent_id_packet", "block", "worker"),
    NodeCase("result_without_ledger_packet", "block", "worker"),
    NodeCase("missing_result_controller_relay_packet", "block", "worker"),
    NodeCase("missing_result_mutual_reminder_packet", "block", "worker"),
    NodeCase("unopened_result_packet", "block", "worker"),
    NodeCase("result_open_envelope_only_packet", "block", "worker"),
    NodeCase("result_open_ledger_only_packet", "block", "worker"),
    NodeCase("result_body_hash_mismatch_packet", "block", "worker"),
    NodeCase("stale_result_body_packet", "block", "worker"),
    NodeCase("missing_reminder_packet", "pass", "worker"),
    HeartbeatCase("heartbeat_valid_packet"),
    HeartbeatCase("heartbeat_missing_state"),
    HeartbeatCase("heartbeat_ambiguous_worker_state"),
    HeartbeatCase("heartbeat_worker_result_pending_review"),
    HeartbeatCase("heartbeat_missing_reminder"),
)


def initial_state() -> State:
    return State()


def terminal_predicate(current_output, state, trace) -> bool:
    del state, trace
    return isinstance(current_output, (PMAdvanced, PMRepairRequired, DispatchBlocked))


def build_workflow() -> Workflow:
    return Workflow(
        (
            PMIssuePacket(),
            HeartbeatResumeLoad(),
            ControllerAskPMOnResume(),
            PMResumeDecision(),
            PacketRuntimeWrite(),
            ControllerReminderCheck(),
            ControllerEnvelopeOnlyHandoff(),
            ControllerEnvelopeRelay(),
            RouterDirectDispatch(),
            WorkerOrControllerResult(),
            ControllerResultRelay(),
            ReviewerResultEnvelopeCheck(),
            ReviewerResult(),
            PMRepairAfterInvalidOrigin(),
            PMAdvance(),
        ),
        name="flowpilot_packet_control_plane",
    )
