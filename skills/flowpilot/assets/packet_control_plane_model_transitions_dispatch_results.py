"""Packet Control Plane Model Transitions Dispatch Results transitions."""

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

__all__ = [
    "RouterDirectDispatch",
    "WorkerOrControllerResult",
    "ControllerResultRelay",
]
