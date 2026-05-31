"""Packet Control Plane Model Transitions Issue Resume transitions."""

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
                "heartbeat_ambiguous_workerlocked",
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
                current_assignments=state.current_assignments + (packet_id,),
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
            yield FunctionResult(NodeResult(packet_id, "worker", "agent-worker"), new_state, "heartbeat_loaded_worker_result_for_review")
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

__all__ = [
    "PMIssuePacket",
    "HeartbeatResumeLoad",
    "ControllerAskPMOnResume",
    "PMResumeDecision",
]
