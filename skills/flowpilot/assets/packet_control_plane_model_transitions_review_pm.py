"""Packet Control Plane Model Transitions Review Pm transitions."""

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

__all__ = [
    "ReviewerResultEnvelopeCheck",
    "ReviewerResult",
    "PMRepairAfterInvalidOrigin",
    "PMAdvance",
]
