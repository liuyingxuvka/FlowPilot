"""Packet Control Plane Model Transitions Packet Relay transitions."""

from __future__ import annotations

from dataclasses import replace

from flowguard import FunctionResult
from packet_control_plane_model_state import (
    ApprovedPacket,
    CheckedResult,
    DispatchBlocked,
    HeartbeatCase,
    NodeCase,
    NodePacket,
    NodeResult,
    PMAdvanced,
    PMRepairRequired,
    ResumeRequest,
    ReviewBlock,
    ReviewPass,
    State,
    _packet_from_id,
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
        "current_assignments",
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
                "current_assignment_missing_mutual_role_reminder_blocked",
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
        current_assignments = state.current_assignments
        if input_obj.current_assignment_present and input_obj.packet_id not in current_assignments:
            current_assignments = current_assignments + (input_obj.packet_id,)
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
        label = "current_assignment_delivered_envelope_with_holder_status_update"
        if input_obj.cockpit_missing_on_major_node:
            cockpit_missing = (
                cockpit_missing if input_obj.packet_id in cockpit_missing else cockpit_missing + (input_obj.packet_id,)
            )
            chat_mermaid = chat_mermaid if input_obj.packet_id in chat_mermaid else chat_mermaid + (input_obj.packet_id,)
            label = "major_node_chat_mermaid_displayed_when_cockpit_missing"

        new_state = replace(
            state,
            controller_envelope_reads=envelope_reads,
            current_assignments=current_assignments,
            controller_handoff_envelope_only=envelope_only_handoffs,
            controller_handoff_mutual_role_reminders=mutual_role_reminders,
            holder_changes=holder_changes,
            holder_status_updates=holder_status_updates,
            cockpit_missing_major_nodes=cockpit_missing,
            chat_mermaid_displays=chat_mermaid,
        )
        if input_obj.current_assignment_present and label == "current_assignment_delivered_envelope_with_holder_status_update":
            label = "current_assignment_recorded"
        yield FunctionResult(input_obj, new_state, label)

__all__ = [
    "PacketRuntimeWrite",
    "ControllerReminderCheck",
    "ControllerEnvelopeOnlyHandoff",
    "ControllerEnvelopeRelay",
]
